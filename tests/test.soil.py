import RPi.GPIO as GPIO
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# GPIO pin definitions
MOISTURE_PIN = 17  # GPIO pin for digital output from YL-69 sensor
RELAY_PIN = 27     # GPIO pin to control relay

def initialize_gpio():
    """
    Initialize GPIO settings for the sensor and relay.
    """
    GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
    GPIO.setup(MOISTURE_PIN, GPIO.IN)  # Set YL-69 digital pin as input
    GPIO.setup(RELAY_PIN, GPIO.OUT)    # Set relay pin as output
    GPIO.output(RELAY_PIN, GPIO.LOW)   # Ensure relay is off initially
    logging.info("GPIO initialized.")

def check_soil_moisture():
    """
    Check the soil moisture level.
    
    Returns:
        bool: True if soil is dry, False if soil is wet.
    """
    return GPIO.input(MOISTURE_PIN) == GPIO.HIGH

def water_plants():
    """
    Activate the relay to water plants.
    """
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn on the relay
    logging.info("Watering plants... Relay ON.")
    time.sleep(5)  # Water for 5 seconds (adjust as needed)
    GPIO.output(RELAY_PIN, GPIO.LOW)   # Turn off the relay
    logging.info("Watering complete. Relay OFF.")

if __name__ == "__main__":
    try:
        # Initialize GPIO settings
        initialize_gpio()

        # Main loop to check soil moisture and water plants if necessary
        while True:
            if check_soil_moisture():
                logging.info("Soil is dry.")
                print("Soil is dry. Watering plants.")
                water_plants()
            else:
                logging.info("Soil is wet.")
                print("Soil is wet. No watering needed.")
            
            time.sleep(10)  # Wait before checking again

    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        GPIO.cleanup()  # Clean up GPIO settings before exiting
        logging.info("GPIO cleanup done.")
