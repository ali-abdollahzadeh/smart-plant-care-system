import logging
import sys
import os
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import mqtt_client 


# Configure logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        logging.info("Starting MQTT client...")
        mqtt_client.connect_mqtt()
        mqtt_client.subscribe_topic("plant/sensor")  # Example subscription, replace with actual topic as needed

        # Keep the script running to listen for incoming messages
        while True:
            pass

    except KeyboardInterrupt:
        logging.info("MQTT client stopped by user.")
    finally:
        mqtt_client.stop_mqtt()
        logging.info("Shutdown complete.")
