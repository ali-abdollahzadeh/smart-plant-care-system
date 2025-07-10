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

def initialize_gpio(dht_pin=None, moisture_pin=None):
    if GPIO is None:
        logging.warning("RPi.GPIO not available. Skipping GPIO init.")
        return
    global DHT_SENSOR_PIN, MOISTURE_PIN
    if dht_pin:
        DHT_SENSOR_PIN = dht_pin
    if moisture_pin:
        MOISTURE_PIN = moisture_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MOISTURE_PIN, GPIO.IN)
    logging.info(f"GPIO initialized (DHT_PIN={DHT_SENSOR_PIN}, MOISTURE_PIN={MOISTURE_PIN})")

def setup_actuators(led_pin=None, watering_pin=None):
    global LED_PIN, WATERING_PIN
    if led_pin:
        LED_PIN = led_pin
    if watering_pin:
        WATERING_PIN = watering_pin
    if GPIO is not None:
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.setup(WATERING_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(WATERING_PIN, GPIO.LOW)
        logging.info(f"Actuators initialized (LED_PIN={LED_PIN}, WATERING_PIN={WATERING_PIN})")
    else:
        logging.warning("GPIO not available. Actuator simulation only.")

def set_actuator(action, value):
    global led_state, watering_state
    if action == 'led':
        led_state = value
        if GPIO is not None:
            GPIO.output(LED_PIN, GPIO.HIGH if value else GPIO.LOW)
        logging.info(f"LED set to: {'ON' if value else 'OFF'}")
    elif action == 'water':
        watering_state = value
        if GPIO is not None:
            GPIO.output(WATERING_PIN, GPIO.HIGH if value else GPIO.LOW)
        logging.info(f"Watering {'STARTED' if value else 'STOPPED'}")
    else:
        logging.warning(f"Unknown actuator: {action}")

def get_actuator_state():
    return {
        'led': led_state,
        'watering': watering_state
    }

def read_temperature_humidity():
    if Adafruit_DHT is None:
        logging.error("Adafruit_DHT not available.")
        return None, None
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, DHT_SENSOR_PIN)
    if humidity is not None and temperature is not None:
        return round(temperature, 2), round(humidity, 2)
    return None, None

def read_soil_moisture():
    if GPIO is None:
        logging.error("RPi.GPIO not available.")
        return None
    return GPIO.input(MOISTURE_PIN)
