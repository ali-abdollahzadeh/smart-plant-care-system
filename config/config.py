import os
import json

# ThingSpeak API Configuration
THINGSPEAK_WRITE_API_KEY = "EPX655D74F8VR98F"  # Replace with your actual Write API Key
THINGSPEAK_READ_API_KEY = "W1OQL6BMVSJW6RWF"   # Replace with your actual Read API Key if needed
THINGSPEAK_CHANNEL_ID = "2634978"              # Replace with your actual Channel ID
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# MQTT Configuration
MQTT_BROKER = "192.168.127.239"  # Replace with your actual MQTT broker IP or hostname
MQTT_PORT = 1883                 # Standard MQTT port
MQTT_TOPIC_SENSOR = "plant/sensor"  # Topic for sensor data publishing

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
            return plants
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not parse {file_path}.")
        return {}

# Load plant configurations from the JSON file
PLANTS = load_plant_config(PLANT_CONFIG_FILE)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7105387626:AAHyiexS3gA5XPhkox16NfVRq9hAx8FxcA8"  # Replace with your actual bot token

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
    return PLANTS.get(plant_name, PLANTS.get(DEFAULT_PLANT))
