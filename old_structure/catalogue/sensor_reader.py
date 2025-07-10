import RPi.GPIO as GPIO
import Adafruit_DHT
import logging
import time
import requests

logging.basicConfig(level=logging.INFO)

DHT_SENSOR_TYPE = Adafruit_DHT.DHT11

# -------------------- CATALOGUE CONNECTION --------------------

def get_sensor_pin(sensor_name):
    try:
        r = requests.get(f"http://localhost:5000/device/{sensor_name}")
        if r.status_code == 200:
            return int(r.json().get("pin"))
    except Exception as e:
        logging.error(f"Error fetching pin from catalogue for {sensor_name}: {e}")
    return None

# -------------------- GPIO SETUP --------------------

def initialize_gpio():
    GPIO.setmode(GPIO.BCM)

    moisture_pin = get_sensor_pin("soil_1")
    if moisture_pin is not None:
        GPIO.setup(moisture_pin, GPIO.IN)
        logging.info("GPIO initialized with soil moisture sensor on pin %d.", moisture_pin)
    else:
        logging.warning("Soil moisture pin not found in catalogue.")

# -------------------- SENSOR FUNCTIONS --------------------

def read_temperature_humidity():
    dht_pin = get_sensor_pin("dht11_1")
    if dht_pin is None:
        logging.warning("DHT11 pin not found in catalogue.")
        return None, None
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, dht_pin)
        if humidity is not None and temperature is not None:
            logging.info(f"Temperature: {temperature} °C, Humidity: {humidity}%")
            return temperature, humidity
        else:
            logging.warning("Failed to get reading from DHT sensor.")
            return None, None
    except Exception as e:
        logging.error(f"Error reading temperature and humidity: {e}")
        return None, None

def read_soil_moisture():
    moisture_pin = get_sensor_pin("soil_1")
    if moisture_pin is None:
        logging.warning("Soil moisture pin not found in catalogue.")
        return None
    try:
        moisture_level = GPIO.input(moisture_pin)
        logging.info(f"Soil moisture level: {'Dry' if moisture_level == 1 else 'Wet'}")
        return moisture_level
    except Exception as e:
        logging.error(f"Error reading soil moisture: {e}")
        return None

# -------------------- TEST RUN --------------------

if __name__ == "__main__":
    try:
        initialize_gpio()

        while True:
            temperature, humidity = read_temperature_humidity()
            soil_moisture = read_soil_moisture()

            if temperature is not None and humidity is not None:
                print(f"Temperature: {temperature}°C, Humidity: {humidity}%")

            if soil_moisture is not None:
                print(f"Soil Moisture Level: {'Dry' if soil_moisture == 1 else 'Wet'}")

            time.sleep(10)

    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup done.")