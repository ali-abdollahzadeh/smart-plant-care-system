import csv
import os
import logging
import time

# SIMULATION MODE
SIMULATION_MODE = True
SIMULATED_CSV = os.path.join(os.path.dirname(__file__), "../scripts/simulated_sensor_data.csv")

# If not simulating, use GPIO and Adafruit
if not SIMULATION_MODE:
    import RPi.GPIO as GPIO
    import Adafruit_DHT

    DHT_SENSOR_TYPE = Adafruit_DHT.DHT11
    DHT_SENSOR_PIN = 21
    MOISTURE_PIN = 17

    def initialize_gpio():
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOISTURE_PIN, GPIO.IN)
        logging.info("GPIO initialized.")

    def read_temperature_humidity():
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, DHT_SENSOR_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 2), round(humidity, 2)
        return None, None

    def read_soil_moisture():
        return GPIO.input(MOISTURE_PIN)

else:
    def initialize_gpio():
        logging.info("SIMULATION MODE: No GPIO to initialize.")

    def _read_last_csv_row():
        try:
            with open(SIMULATED_CSV, "r") as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1].strip().split(",")
                    return {
                        "timestamp": last_line[0],
                        "moisture": float(last_line[1]),
                        "temperature": float(last_line[2]),
                        "light": float(last_line[3])
                    }
        except Exception as e:
            logging.error(f"Simulation data read error: {e}")
        return None

    def read_temperature_humidity():
        row = _read_last_csv_row()
        if row:
            return row["temperature"], 50.0  # Fake humidity for now
        return None, None

    def read_soil_moisture():
        row = _read_last_csv_row()
        if row:
            return 1 if row["moisture"] > 30 else 0
        return 0
