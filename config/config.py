import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# ThingSpeak API Configuration
THINGSPEAK_WRITE_API_KEY = os.getenv("THINGSPEAK_WRITE_API_KEY", "EPX655D74F8VR98F")  # Replace with environment variable
THINGSPEAK_READ_API_KEY = os.getenv("THINGSPEAK_READ_API_KEY", "W1OQL6BMVSJW6RWF")    # Replace with environment variable
THINGSPEAK_CHANNEL_ID = "2634978"               # Replace with your actual Channel ID
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# MQTT Configuration
MQTT_BROKER = "192.168.122.239"  # Replace with your actual MQTT broker IP or hostname
MQTT_PORT = 1883                 # Standard MQTT port
MQTT_TOPIC_SENSOR = "plant/sensor"  # Topic for sensor data publishing
MQTT_SUBSCRIBE_TOPIC = "plant/commands"  # Topic for commands or other incoming messages


# Load Plant Profiles from JSON
# Dynamically construct the path to plants.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
PLANT_CONFIG_FILE = os.path.join(BASE_DIR, "plants.json")
DEFAULT_PLANT = "Plant1"

def load_plant_config(file_path):
    """Loads plant configuration from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            plants = json.load(f)
            logging.info("Plant configurations loaded successfully.")
            return plants
    except FileNotFoundError:
        logging.error(f"Error: {file_path} not found.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error: Could not parse {file_path}.")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading plant configurations: {e}")
        return {}

# Load plant configurations from the JSON file
PLANTS = load_plant_config(PLANT_CONFIG_FILE)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7105387626:AAHyiexS3gA5XPhkox16NfVRq9hAx8FxcA8")  # Use environment variable

# Simulation Settings (if needed)
SIMULATE_TEMPERATURE = True
SIMULATE_HUMIDITY = True
SIMULATE_SOIL_MOISTURE = True

# Watering Schedule Configuration
WATERING_SCHEDULE = "07:00,19:00"  # Example: Water at 7 AM and 7 PM

# Timezone Configuration
TIMEZONE = "UTC"

# Device Configuration
DEVICES_CONFIGURED = []

# Function to Get Plant Configurations
def get_plant_config(plant_name):
    """Retrieve the configuration for a specific plant."""
    if plant_name in PLANTS:
        return PLANTS[plant_name]
    else:
        logging.warning(f"Plant configuration for {plant_name} not found. Using default configuration.")
        return PLANTS.get(DEFAULT_PLANT, {})

if __name__ == "__main__":
    # Test loading configurations and retrieving a specific plant configuration
    print(get_plant_config(DEFAULT_PLANT))
