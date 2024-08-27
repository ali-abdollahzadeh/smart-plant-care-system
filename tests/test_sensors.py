import logging
import sys
import os
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import sensor_reader
# Configure logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        logging.info("Testing sensor readings...")
        while True:
            temperature, humidity = sensor_reader.read_temperature_humidity()
            soil_moisture = sensor_reader.read_soil_moisture()

            logging.info(f"Temperature: {temperature}°C, Humidity: {humidity}%, Soil Moisture: {'Dry' if soil_moisture == 1 else 'Wet'}")
            time.sleep(5)  # Adjust the delay for testing purposes

    except KeyboardInterrupt:
        logging.info("Sensor test stopped by user.")
    finally:
        logging.info("Test completed.")
