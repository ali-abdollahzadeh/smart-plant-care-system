import logging
import RPi.GPIO as GPIO
import sys
import os
import time
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)

# Import sensor functions
try:
    from lib.sensor_reader import read_temperature_humidity, read_soil_moisture
except ImportError:
    from sensor_reader import read_temperature_humidity, read_soil_moisture

# --- Catalogue Integration ---
def get_plant_config(plant_id):
    try:
        r = requests.get("http://localhost:5000/plants")
        if r.status_code == 200:
            plants = r.json()
            return plants.get(plant_id, None)
    except Exception as e:
        logging.error(f"Failed to load plant config from catalogue: {e}")
    return None

# --- Actuator simulation ---
def control_water_pump(action):
    if action == 'on':
        logging.info("Simulated: Water pump turned ON.")
    elif action == 'off':
        logging.info("Simulated: Water pump turned OFF.")
    else:
        logging.error("Invalid action for water pump control.")

def control_light(action):
    if action == 'on':
        logging.info("Simulated: Light turned ON.")
    elif action == 'off':
        logging.info("Simulated: Light turned OFF.")
    else:
        logging.error("Invalid action for light control.")

def check_conditions_and_act(plant_id="Plant1"):
    temperature, humidity = read_temperature_humidity()
    soil_moisture = read_soil_moisture()

    plant_config = get_plant_config(plant_id)
    if plant_config is None:
        logging.error(f"Plant configuration for '{plant_id}' not found.")
        return

    logging.info(f"Plant: {plant_config['name']} | Temp: {temperature}, Humidity: {humidity}, Moisture: {soil_moisture}")

    # Soil Moisture Check
    if soil_moisture == 1:  # Dry
        control_water_pump('on')
    else:
        control_water_pump('off')

    # Threshold Checks
    if temperature is not None and humidity is not None:
        if temperature > plant_config['temperature_threshold']:
            logging.warning(f"Temperature too high: {temperature} > {plant_config['temperature_threshold']}")
        if humidity < plant_config['humidity_threshold']:
            logging.warning(f"Humidity too low: {humidity} < {plant_config['humidity_threshold']}")

if __name__ == "__main__":
    try:
        GPIO.setmode(GPIO.BCM)
        while True:
            check_conditions_and_act("Plant1")
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup done.")
