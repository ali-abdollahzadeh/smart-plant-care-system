import paho.mqtt.client as mqtt
import logging
import json
import time

# Global in-memory store for latest data per plant_id
latest_data = {}

class MqttSubscriber:
    def __init__(self, broker, port, subscribe_topic):
        self.broker = broker
        self.port = port
        self.subscribe_topic = subscribe_topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            client.subscribe(self.subscribe_topic)
            logging.info(f"Subscribed to {self.subscribe_topic}")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            # Store latest data by plant_id
            plant_id = data.get('plant_id')
            logging.info(f"Received MQTT message for plant_id: {plant_id} | Data: {data}")
            if plant_id:
                latest_data[plant_id] = data
                logging.info(f"Updated latest_data for plant_id: {plant_id}")
        except Exception as e:
            logging.error(f"Error handling MQTT message: {e}")

    def start(self):
        while True:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_forever()
            except Exception as e:
                logging.error(f"MQTT connection error: {e}")
                time.sleep(5)
