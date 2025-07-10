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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config')))
# Now try importing modules with updated sys.path
try:
    from lib.sensor_reader import read_temperature_humidity, read_soil_moisture
    import config
except ModuleNotFoundError:
    # Fallback for standalone execution
    from sensor_reader import read_temperature_humidity, read_soil_moisture
    import config

# Define GPIO pins for actuators and sensors
MOISTURE_PIN = 17  # Example GPIO pin for soil moisture sensor

# Initialize GPIO for actuators and sensors
def initialize_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MOISTURE_PIN, GPIO.IN)  # Ensure moisture sensor pin is set up as input

# Simulated function for controlling water pump
def control_water_pump(action):
    if action == 'on':
        logging.info("Simulated: Water pump turned ON.")
    elif action == 'off':
        logging.info("Simulated: Water pump turned OFF.")
    else:
        logging.error("Invalid action for water pump control.")

# Simulated function for controlling light
def control_light(action):
    if action == 'on':
        logging.info("Simulated: Light turned ON.")
    elif action == 'off':
        logging.info("Simulated: Light turned OFF.")
    else:
        logging.error("Invalid action for light control.")

def check_conditions_and_act():
    temperature, humidity = read_temperature_humidity()
    soil_moisture = read_soil_moisture()  # This should now work correctly with proper GPIO setup

    if soil_moisture == 1:  # Assuming 1 means dry
        logging.info("Soil is dry. Simulating activation of water pump.")
        control_water_pump('on')
    else:
        logging.info("Soil is wet. Simulating deactivation of water pump.")
        control_water_pump('off')
    
    # Get plant configuration
    plant_config = config.get_plant_config(config.DEFAULT_PLANT)
    print(f"Plant configuration loaded: {plant_config}")  # Test print

    if temperature is not None and humidity is not None:
        if temperature > plant_config['temperature_threshold']:
            logging.warning(f"Temperature is too high: {temperature}°C.")
        if humidity < plant_config['humidity_threshold']:
            logging.warning(f"Humidity is too low: {humidity}%.")

if __name__ == "__main__":
    initialize_gpio()  # Ensure GPIO is initialized before running control loop
    try:
        while True:
            check_conditions_and_act()
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup done.")
