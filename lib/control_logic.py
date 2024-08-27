import logging
import RPi.GPIO as GPIO
import sys
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add the parent directory to the Python path for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now try importing modules with updated sys.path
try:
    from lib.sensor_reader import read_temperature_humidity, read_soil_moisture
    import config
except ModuleNotFoundError:
    # Fallback for standalone execution
    from sensor_reader import read_temperature_humidity, read_soil_moisture
    import config

# Define GPIO pins for actuators
WATER_PUMP_PIN = 18  # Example GPIO pin for water pump
LIGHT_PIN = 23       # Example GPIO pin for light

# Initialize GPIO for actuators
def initialize_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(WATER_PUMP_PIN, GPIO.OUT)
    GPIO.setup(LIGHT_PIN, GPIO.OUT)

def control_water_pump(action):
    if action == 'on':
        GPIO.output(WATER_PUMP_PIN, GPIO.HIGH)
        logging.info("Water pump turned ON.")
    elif action == 'off':
        GPIO.output(WATER_PUMP_PIN, GPIO.LOW)
        logging.info("Water pump turned OFF.")
    else:
        logging.error("Invalid action for water pump control.")

def control_light(action):
    if action == 'on':
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
        logging.info("Light turned ON.")
    elif action == 'off':
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        logging.info("Light turned OFF.")
    else:
        logging.error("Invalid action for light control.")

def check_conditions_and_act():
    temperature, humidity = read_temperature_humidity()
    soil_moisture = read_soil_moisture()

    if soil_moisture == 1:  # Assuming 1 means dry
        logging.info("Soil is dry. Activating water pump.")
        control_water_pump('on')
    else:
        logging.info("Soil is wet. Deactivating water pump.")
        control_water_pump('off')

    plant_config = config.get_plant_config(config.DEFAULT_PLANT)
    
    if temperature is not None and humidity is not None:
        if temperature > plant_config['temperature_threshold']:
            logging.warning(f"Temperature is too high: {temperature}°C.")
        if humidity < plant_config['humidity_threshold']:
            logging.warning(f"Humidity is too low: {humidity}%.")

if __name__ == "__main__":
    initialize_gpio()
    try:
        while True:
            check_conditions_and_act()
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup done.")
