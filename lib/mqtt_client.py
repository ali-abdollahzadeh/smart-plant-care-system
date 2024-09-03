import paho.mqtt.client as mqtt
import logging
import json
import sys
import os

# Add the relative path to the config directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))

# Import configuration settings
import config

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize MQTT client
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    """Callback function when the client connects to the MQTT broker."""
    if rc == 0:
        logging.info("Connected to MQTT Broker successfully.")
        client.subscribe(config.MQTT_SUBSCRIBE_TOPIC)
        logging.info(f"Subscribed to topic: {config.MQTT_SUBSCRIBE_TOPIC}")
    else:
        logging.error(f"Failed to connect to MQTT Broker. Return code: {rc}")

def on_publish(client, userdata, mid):
    """Callback function when a message is published."""
    logging.info(f"Data published successfully with message ID: {mid}")

def on_message(client, userdata, msg):
    """Callback function when a message is received from the subscribed topic."""
    logging.info(f"Message received from topic {msg.topic}: {msg.payload.decode()}")

# Assign callback functions
client.on_connect = on_connect
client.on_publish = on_publish
client.on_message = on_message

def connect_mqtt():
    """Connects to the MQTT broker using settings from the config file."""
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.loop_start()
        logging.info("MQTT client started and connected.")
    except Exception as e:
        logging.error(f"Failed to connect to MQTT Broker: {e}")

def publish_data(topic, payload):
    """
    Publishes sensor data to the specified MQTT topic.
    
    Args:
        topic (str): The MQTT topic to publish to.
        payload (dict): The data payload to publish.
    """
    sensor_json = json.dumps(payload)
    result = client.publish(topic, sensor_json)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logging.info(f"Published to MQTT: {sensor_json} to topic {topic}")
    else:
        logging.error(f"Failed to publish data to MQTT: {sensor_json}")

def subscribe_topic(topic):
    """
    Subscribes to the specified MQTT topic.
    
    Args:
        topic (str): The MQTT topic to subscribe to.
    """
    try:
        client.subscribe(topic)
        logging.info(f"Subscribed to topic: {topic}")
    except Exception as e:
        logging.error(f"Failed to subscribe to topic {topic}: {e}")

def stop_mqtt():
    """Stops the MQTT client network loop and disconnects from the broker."""
    client.loop_stop()
    client.disconnect()
    logging.info("MQTT client stopped and disconnected.")
