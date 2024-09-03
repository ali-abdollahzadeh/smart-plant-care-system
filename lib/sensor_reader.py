import RPi.GPIO as GPIO
import Adafruit_DHT
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

# GPIO pin definitions
DHT_SENSOR_PIN = 21  # GPIO pin for DHT11 sensor (temperature and humidity)
MOISTURE_PIN = 17    # GPIO pin for soil moisture sensor

# Initialize the type of sensor for temperature and humidity
DHT_SENSOR_TYPE = Adafruit_DHT.DHT11

def initialize_gpio():
    """
    Initialize GPIO settings for the sensors.
    Sets the GPIO mode and defines input pins.
    """
    GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
    GPIO.setup(MOISTURE_PIN, GPIO.IN)  # Set soil moisture pin as input
    logging.info("GPIO initialized.")

def read_temperature_humidity():
    """
    Reads temperature and humidity from the DHT11 sensor.
    
    Returns:
        tuple: Temperature (°C) and humidity (%) as float values, or (None, None) if read fails.
    """
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, DHT_SENSOR_PIN)
        if humidity is not None and temperature is not None:
            logging.info(f"Temperature: {temperature}°C, Humidity: {humidity}%")
            return temperature, humidity
        else:
            logging.warning("Failed to get reading from DHT sensor.")
            return None, None
    except Exception as e:
        logging.error(f"Error reading temperature and humidity: {e}")
        return None, None

def read_soil_moisture():
    """
    Reads soil moisture level from the digital soil moisture sensor.
    
    Returns:
        int: 0 if wet, 1 if dry (assuming typical digital soil moisture sensor behavior).
    """
    try:
        moisture_level = GPIO.input(MOISTURE_PIN)
        logging.info(f"Soil moisture level: {'Dry' if moisture_level == 1 else 'Wet'}")
        return moisture_level
    except Exception as e:
        logging.error(f"Error reading soil moisture: {e}")
        return None

if __name__ == "__main__":
    try:
        # Initialize GPIO settings
        initialize_gpio()

        # Continuously read sensor data for testing purposes
        while True:
            temperature, humidity = read_temperature_humidity()
            soil_moisture = read_soil_moisture()
            
            if temperature is not None and humidity is not None:
                print(f"Temperature: {temperature}°C, Humidity: {humidity}%")
            
            if soil_moisture is not None:
                print(f"Soil Moisture Level: {'Dry' if soil_moisture == 1 else 'Wet'}")
            
            time.sleep(10)  # Wait for 10 seconds before next reading

    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()  # Clean up GPIO settings before exiting
        logging.info("GPIO cleanup done.")