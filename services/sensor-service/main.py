"""
Sensor Service

- Publishes sensor data to MQTT topic (plant/sensor)
- Subscribes to actuator command topic (plant/command) for actuator control (LED, watering)
- Exposes REST API on port 5002 for manual actuator control (POST/GET /actuator)
- Integrates with Telegram bot for user commands
- Supports both simulation and real hardware modes
"""
import os
import sys
import time
import yaml
import logging
import requests
from publisher import MQTTPublisher
from simulator import SensorSimulator
from real_sensor_interface import initialize_gpio, read_temperature_humidity, read_soil_moisture
import threading
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import traceback

def log_uncaught_exceptions(exctype, value, tb):
    print("UNCAUGHT EXCEPTION:", file=sys.stderr)
    traceback.print_exception(exctype, value, tb)

sys.excepthook = log_uncaught_exceptions

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Load config
CONFIG_PATH = os.environ.get("CONFIG_PATH", "../shared/config/global_config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']
sim_conf = config.get('simulation', {})
thresholds = config.get('sensor_thresholds', {})

CATALOGUE_PLANTS_URL = os.environ.get('CATALOGUE_PLANTS_URL', 'http://catalogue-service:5000/plants')
CATALOGUE_ACTIVE_PLANTS_URL = os.environ.get('CATALOGUE_ACTIVE_PLANTS_URL', 'http://catalogue-service:5000/plants/active')

SIM_MODE = sim_conf.get('enabled', False)
PUBLISH_TOPIC = mqtt_conf['publish_topic']
COMMAND_TOPIC = mqtt_conf.get('command_topic', 'plant/command')

# Flask app for actuator control
app = Flask(__name__)

# Actuator state and interface
if SIM_MODE:
    sim = SensorSimulator(
        temp_range=(thresholds['temperature']['min'], thresholds['temperature']['max']),
        hum_range=(thresholds['humidity']['min'], thresholds['humidity']['max']),
        moist_range=(thresholds['soil_moisture']['min'], thresholds['soil_moisture']['max'])
    )
    # Per-plant simulators and actuator state
    simulators = {}
    actuator_states = {}
    def set_actuator(action, value, plant_id=None):
        logging.info(f"set_actuator called: action={action}, value={value}, plant_id={plant_id}, simulators={list(simulators.keys())}")
        if plant_id and plant_id in simulators:
            simulators[plant_id].set_actuator(action, value)
            actuator_states[plant_id] = simulators[plant_id].get_actuator_state()
        else:
            sim.set_actuator(action, value)
    def get_actuator_state(plant_id=None):
        if plant_id and plant_id in simulators:
            return simulators[plant_id].get_actuator_state()
        return sim.get_actuator_state()
else:
    initialize_gpio()
    from real_sensor_interface import setup_actuators, set_actuator, get_actuator_state
    setup_actuators()

def handle_command(command):
    action = command.get('action')
    value = command.get('value')
    set_actuator(action, value)

# MQTT command subscription
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Sensor Service connected to MQTT broker for commands.")
        client.subscribe(COMMAND_TOPIC)
        logging.info(f"Subscribed to command topic: {COMMAND_TOPIC}")
    else:
        logging.error(f"Failed to connect to MQTT broker for commands: {rc}")

def on_message(client, userdata, msg):
    try:
        command = yaml.safe_load(msg.payload.decode())
        logging.info(f"Received actuator command: {command}")
        handle_command(command)
    except Exception as e:
        logging.error(f"Error processing actuator command: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_conf['broker_url'], mqtt_conf.get('port', 1883), 60)
threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()

# Flask REST API for actuator control
@app.route('/actuator', methods=['POST'])
def actuator_control():
    command = request.json
    plant_id = command.get('plant_id')
    if not command or 'action' not in command or 'value' not in command:
        return jsonify({'error': 'Invalid command'}), 400
    set_actuator(command['action'], command['value'], plant_id)
    # Immediately publish new sensor data for this plant
    if SIM_MODE and plant_id and plant_id in simulators:
        sim = simulators[plant_id]
        data = sim.next()
        data['plant_id'] = plant_id
        logging.info(f"Immediate publish after actuator: {data}")
        publisher.publish(PUBLISH_TOPIC, data)
    return jsonify({'status': 'ok', 'state': get_actuator_state(plant_id)})

@app.route('/actuator', methods=['GET'])
def actuator_status():
    plant_id = request.args.get('plant_id')
    return jsonify(get_actuator_state(plant_id))

def run_flask():
    app.run(host='0.0.0.0', port=5002)

threading.Thread(target=run_flask, daemon=True).start()

# Get plant_id from environment or config
PLANT_ID = os.environ.get('PLANT_ID', config.get('plant_id', None))

# Auto-register device in catalogue
CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/devices')
try:
    reg_payload = {
        "name": "Simulated Sensor Device" if SIM_MODE else "Raspberry Pi Sensor Device",
        "type": "sensor",
        "config": {"mode": "simulation" if SIM_MODE else "real", "plant_id": PLANT_ID}
    }
    resp = requests.post(CATALOGUE_URL, json=reg_payload, timeout=5)
    if resp.status_code == 201:
        logging.info(f"Device registered in catalogue: {resp.json()}")
    else:
        logging.warning(f"Service registration failed: {resp.status_code} {resp.text}")
except Exception as e:
    logging.error(f"Could not register device in catalogue: {e}")

publisher = MQTTPublisher(mqtt_conf['broker_url'], mqtt_conf.get('port', 1883))
publisher.connect()
logging.info(f"Sensor data publisher connecting to MQTT broker at {mqtt_conf['broker_url']}:{mqtt_conf.get('port', 1883)}")

# Function to start simulation for a plant
def start_plant_simulation(plant):
    plant_id = plant['id']
    thresholds = eval(plant['thresholds']) if isinstance(plant['thresholds'], str) else plant['thresholds']
    sim = SensorSimulator(
        temp_range=(thresholds['temperature']['min'], thresholds['temperature']['max']),
        hum_range=(thresholds['humidity']['min'], thresholds['humidity']['max']),
        moist_range=(thresholds['soil_moisture']['min'], thresholds['soil_moisture']['max'])
    )
    simulators[plant_id] = sim
    actuator_states[plant_id] = sim.get_actuator_state() # Initialize actuator state for new plant
    def loop():
        while True:
            data = sim.next()
            data['plant_id'] = plant_id
            logging.info(f"Publishing sensor data for plant_id={plant_id}: {data}")
            publisher.publish(PUBLISH_TOPIC, data)
            time.sleep(30)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

# Function to poll catalogue and start simulation for new plants
# Only start new threads for new plants, and never crash if catalogue is unavailable

def poll_and_simulate_all_plants():
    known_ids = set()
    while True:
        try:
            logging.info("Polling catalogue for plants...")
            try:
                resp = requests.get(CATALOGUE_PLANTS_URL, timeout=5)
                logging.info(f"Catalogue response status: {resp.status_code}")
                logging.info(f"Raw /plants response: {resp.text[:500]}")
            except Exception as e:
                logging.error(f"Failed to connect to catalogue-service: {e}")
                time.sleep(10)
                continue
            try:
                plants = resp.json()
                logging.info(f"Catalogue returned {len(plants)} plants: {plants}")
            except Exception as e:
                logging.error(f"Failed to parse catalogue response as JSON: {e}, text: {resp.text}")
                plants = []
            if not plants:
                logging.warning("No plants found in catalogue. No simulation will start.")
            for plant in plants:
                if plant['id'] not in known_ids:
                    logging.info(f"Starting simulation for plant_id: {plant['id']}")
                    start_plant_simulation(plant)
                    known_ids.add(plant['id'])
            logging.info(f"Currently simulating plant_ids: {list(known_ids)}")
        except Exception as e:
            logging.error(f"FATAL error in poll_and_simulate_all_plants: {e}\n{traceback.format_exc()}")
            break
    logging.critical("poll_and_simulate_all_plants thread exited unexpectedly!")

if SIM_MODE:
    t = threading.Thread(target=poll_and_simulate_all_plants)
    t.daemon = False  # Ensure the thread is non-daemon
    t.start()
