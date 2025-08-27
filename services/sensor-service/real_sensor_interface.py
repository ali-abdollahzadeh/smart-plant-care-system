import logging

try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    GPIO = None
    Adafruit_DHT = None

# Default pins (can be overridden by config)
DHT_SENSOR_TYPE = 11  # DHT11
DHT_SENSOR_PIN = 21
MOISTURE_PIN = 17

# Actuator pins (can be overridden by config)
LED_PIN = 27
WATERING_PIN = 22
led_state = False
watering_state = False

# Initialize GPIO
def initialize_gpio(dht_pin=None, moisture_pin=None):
    if GPIO is None: # if GPIO is not available, skip GPIO init
        logging.warning("RPi.GPIO not available. Skipping GPIO init.")
        return
    global DHT_SENSOR_PIN, MOISTURE_PIN 
    if dht_pin: # if dht_pin is provided, use it
        DHT_SENSOR_PIN = dht_pin
    if moisture_pin: # if moisture_pin is provided, use it
        MOISTURE_PIN = moisture_pin
    GPIO.setmode(GPIO.BCM) # set GPIO mode to BCM
    GPIO.setup(MOISTURE_PIN, GPIO.IN) # set moisture pin to input
    logging.info(f"GPIO initialized (DHT_PIN={DHT_SENSOR_PIN}, MOISTURE_PIN={MOISTURE_PIN})")

# Setup actuators
def setup_actuators(led_pin=None, watering_pin=None):
    global LED_PIN, WATERING_PIN
    if led_pin: # if led_pin is provided, use it
        LED_PIN = led_pin
    if watering_pin: # if watering_pin is provided, use it
        WATERING_PIN = watering_pin
    if GPIO is not None: # if GPIO is available, setup actuators
        GPIO.setup(LED_PIN, GPIO.OUT) # set led pin to output
        GPIO.setup(WATERING_PIN, GPIO.OUT) # set watering pin to output
        GPIO.output(LED_PIN, GPIO.LOW) # set led pin to low
        GPIO.output(WATERING_PIN, GPIO.LOW) # set watering pin to low
        logging.info(f"Actuators initialized (LED_PIN={LED_PIN}, WATERING_PIN={WATERING_PIN})")
    else:
        logging.warning("GPIO not available. Actuator simulation only.")

# Set actuator state
def set_actuator(action, value):
    global led_state, watering_state
    if action == 'led': # if action is led, set led state
        led_state = value
        if GPIO is not None: # if GPIO is available, set led state
            GPIO.output(LED_PIN, GPIO.HIGH if value else GPIO.LOW) # set led pin to high if value is True, otherwise set to low
        logging.info(f"LED set to: {'ON' if value else 'OFF'}")
    elif action == 'water': # if action is water, set watering state
        watering_state = value
        if GPIO is not None: # if GPIO is available, set watering state
            GPIO.output(WATERING_PIN, GPIO.HIGH if value else GPIO.LOW) # set watering pin to high if value is True, otherwise set to low
        logging.info(f"Watering {'STARTED' if value else 'STOPPED'}")
    else:
        logging.warning(f"Unknown actuator: {action}")

# Get actuator state 
def get_actuator_state():
    return {
        'led': led_state,
        'watering': watering_state
    }

# Read temperature and humidity
def read_temperature_humidity():
    if Adafruit_DHT is None: # if Adafruit_DHT is not available, return None
        logging.error("Adafruit_DHT not available.")
        return None, None
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, DHT_SENSOR_PIN) # read temperature and humidity
    if humidity is not None and temperature is not None: # if humidity and temperature are not None, return temperature and humidity
        return round(temperature, 2), round(humidity, 2)
    return None, None 

# Read soil moisture
def read_soil_moisture():
    if GPIO is None:
        logging.error("RPi.GPIO not available.")
        return None
    return GPIO.input(MOISTURE_PIN)
