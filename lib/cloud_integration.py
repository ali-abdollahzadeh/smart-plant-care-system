import requests
import logging
import sys
import os

# Add the relative path to the config directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))

# Import configuration settings
import config

# Configure logging
logging.basicConfig(level=logging.INFO)

def send_to_thingspeak(temperature, humidity, soil_moisture):
    """
    Sends sensor data to ThingSpeak.

    Args:
        temperature (float): Temperature value to send.
        humidity (float): Humidity value to send.
        soil_moisture (int): Soil moisture value to send.
    """
    payload = {
        'api_key': config.THINGSPEAK_WRITE_API_KEY,
        'field1': temperature,
        'field2': humidity,
        'field3': soil_moisture
    }

    try:
        response = requests.post(config.THINGSPEAK_URL, params=payload, timeout=10)  # Changed to POST for data updates
        response.raise_for_status()  # Raises HTTPError for bad responses
        logging.info(f"Data sent to ThingSpeak successfully. Response: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending data to ThingSpeak: {e}")

def read_from_thingspeak():
    """
    Reads the latest sensor data from ThingSpeak.

    Returns:
        dict: A dictionary containing temperature, humidity, and soil moisture values.
    """
    url = f"https://api.thingspeak.com/channels/{config.THINGSPEAK_CHANNEL_ID}/feeds.json"
    params = {
        'api_key': config.THINGSPEAK_READ_API_KEY,
        'results': 1  # Get only the latest result
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        feeds = data['feeds'][0]
        temperature = float(feeds['field1'])
        humidity = float(feeds['field2'])
        soil_moisture = int(feeds['field3'])
        logging.info(f"Read from ThingSpeak - Temperature: {temperature}, Humidity: {humidity}, Soil Moisture: {soil_moisture}")
        return {
            'temperature': temperature,
            'humidity': humidity,
            'soil_moisture': soil_moisture
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error reading data from ThingSpeak: {e}")
        return None

if __name__ == "__main__":
    # Test sending data
    send_to_thingspeak(25.5, 60.0, 200)

    # Test reading data
    data = read_from_thingspeak()
    if data:
        print(f"Latest data: {data}")
