import logging
import sys
import os
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import mqtt_client

# Configure logging
logging.basicConfig(level=logging.INFO)

def on_test_message(client, userdata, message):
    logging.info(f"Test message received: {message.payload.decode()} on topic {message.topic}")

if __name__ == "__main__":
    # Configure the MQTT client for testing
    mqtt_client.client.on_message = on_test_message
    mqtt_client.connect_mqtt()
    
    try:
        # Subscribe to a test topic
        test_topic = "test/topic"
        mqtt_client.subscribe_topic(test_topic)
        logging.info(f"Subscribed to test topic: {test_topic}")

        # Publish a test message
        test_message = {"temperature": 25, "humidity": 50, "soil_moisture": 200}
        mqtt_client.publish_data(test_topic, test_message)
        logging.info(f"Published test message to topic: {test_topic}")

        # Keep the script running to listen for incoming test messages
        while True:
            pass

    except KeyboardInterrupt:
        logging.info("Test MQTT client stopped by user.")
    finally:
        mqtt_client.stop_mqtt()
        logging.info("Shutdown complete.")
