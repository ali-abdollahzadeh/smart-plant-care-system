import Adafruit_DHT
import time
import requests
import RPi.GPIO as GPIO
import logging
import sys
import os

# Add the relative path to the config directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))

# Import configuration settings
import config

# Configure logging
logging.basicConfig(level=logging.INFO)

# Sensor settings
sensor = Adafruit_DHT.DHT11
dht_pin = 21  # GPIO pin for DHT11

# Soil moisture sensor settings
moisture_pin = 17  # GPIO pin for the soil moisture sensor

# Initialize GPIO
def initialize_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(moisture_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def read_soil_moisture():
    """Reads soil moisture level."""
    return GPIO.input(moisture_pin)

def read_temperature_humidity():
    """Reads temperature and humidity from DHT11 sensor."""
    humidity, temperature = Adafruit_DHT.read_retry(sensor, dht_pin)
    return temperature, humidity

def send_to_thingspeak(temperature, humidity, soil_moisture):
    """Sends sensor data to ThingSpeak."""
    payload = {
        'api_key': config.THINGSPEAK_WRITE_API_KEY,
        'field1': temperature,
        'field2': humidity,
        'field3': soil_moisture
    }
    try:
        response = requests.get(config.THINGSPEAK_URL, params=payload, timeout=10)
        logging.info(f"Data sent to ThingSpeak: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send data to ThingSpeak: {e}")

def main():
    """Main function to read sensors and send data."""
    initialize_gpio()

    try:
        while True:
            # Read sensor data
            temperature, humidity = read_temperature_humidity()
            moisture = read_soil_moisture()
            soil_moisture_value = 800 if moisture == 1 else 200

            if humidity is not None and temperature is not None:
                logging.info(f'Temp={temperature}*C  Humidity={humidity}%  Soil Moisture={soil_moisture_value}')
                send_to_thingspeak(temperature, humidity, soil_moisture_value)
            else:
                logging.warning('Failed to get DHT11 reading. Try again!')

            time.sleep(config.DATA_SEND_INTERVAL)  # Configurable interval from config.py

    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup done.")

if __name__ == "__main__":
    main()
