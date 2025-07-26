import paho.mqtt.client as mqtt
import logging
import json
import time
import requests
import os

CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/plants')
USER_SERVICE_NOTIFY_URL = os.environ.get('USER_SERVICE_NOTIFY_URL', 'http://user-service:5002/notify')

# This class is used to monitor the plants and send commands to the user service
class ControlCenter:
    def __init__(self, broker, port, subscribe_topic, command_topic, thresholds):
        self.broker = broker
        self.port = port
        self.subscribe_topic = subscribe_topic
        self.command_topic = command_topic
        self.default_thresholds = thresholds
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.last_alert = None


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            client.subscribe(self.subscribe_topic)
            logging.info(f"Subscribed to {self.subscribe_topic}")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")

    # Get the thresholds for a plant from the catalogue service
    def get_plant_thresholds(self, plant_id):
        try:
            resp = requests.get(f"{CATALOGUE_URL}/{plant_id}", timeout=3) # Available in http://catalogue-service:5000/plants/{plant_id}
            if resp.status_code == 200:
                plant = resp.json()
                import ast
                thresholds = ast.literal_eval(plant.get('thresholds', '{}'))
                return thresholds if thresholds else self.default_thresholds
        except Exception as e:
            logging.error(f"Error fetching thresholds for plant {plant_id}: {e}")
        return self.default_thresholds

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode()) 
            plant_id = data.get('plant_id')
            thresholds = self.get_plant_thresholds(plant_id) if plant_id else self.default_thresholds
            alerts = []
            plant_name = None
            plant_location = None
            if plant_id:
                try:
                    plant_resp = requests.get(f"{CATALOGUE_URL}/{plant_id}", timeout=3)
                    if plant_resp.status_code == 200:
                        plant = plant_resp.json()
                        plant_name = plant.get('name')
                        plant_location = plant.get('location')
                except Exception:
                    pass
            # Check if the temperature is out of range
            if 'temperature' in data:
                t = data['temperature'] 
                if t < thresholds['temperature']['min'] or t > thresholds['temperature']['max']: 
                    alerts.append(f"Temperature out of range: {t}")
            # Check if the humidity is out of range
            if 'humidity' in data:
                h = data['humidity']
                if h < thresholds['humidity']['min'] or h > thresholds['humidity']['max']:
                    alerts.append(f"Humidity out of range: {h}")
            # Check if the soil moisture is too low
            if 'soil_moisture' in data:
                m = data['soil_moisture']
                if m < thresholds['soil_moisture']['min']:
                    alerts.append(f"Soil moisture too low: {m}")
                    self.send_command({'action': 'water', 'value': True, 'plant_id': plant_id})
            if alerts:
                logging.warning(f"[Plant {plant_id}] " + "; ".join(alerts))
                self.last_alert = time.time()
                # Send notification to user service
                if plant_name and plant_location:
                    try:
                        requests.post(USER_SERVICE_NOTIFY_URL, json={
                            'plant_name': plant_name,
                            'location': plant_location,
                            'problem': "; ".join(alerts)
                        }, timeout=2)
                    except Exception as e:
                        logging.error(f"Failed to notify user service: {e}")
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    def send_command(self, command):
        try:
            msg = json.dumps(command)
            self.client.publish(self.command_topic, msg)
            logging.info(f"Sent command: {msg}")
        except Exception as e:
            logging.error(f"Failed to send command: {e}")

    def start_monitoring(self):
        while True:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_forever()
            except Exception as e:
                logging.error(f"MQTT connection error: {e}")
                time.sleep(5)
