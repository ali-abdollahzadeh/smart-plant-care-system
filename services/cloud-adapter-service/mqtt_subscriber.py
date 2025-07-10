import paho.mqtt.client as mqtt
import requests
import logging
import json
import time

# Global in-memory store for latest data per plant_id
latest_data = {}

class MqttToThingSpeakBridge:
    def __init__(self, broker, port, subscribe_topic, thingspeak_url, write_api_key):
        self.broker = broker
        self.port = port
        self.subscribe_topic = subscribe_topic
        self.thingspeak_url = thingspeak_url
        self.write_api_key = write_api_key
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
            # Forward to ThingSpeak as before
            payload = {
                'api_key': self.write_api_key,
                'field1': data.get('temperature'),
                'field2': data.get('humidity'),
                'field3': data.get('soil_moisture')
            }
            resp = requests.post(self.thingspeak_url, data=payload, timeout=5)
            if resp.status_code == 200:
                logging.info(f"Forwarded to ThingSpeak: {payload}")
            else:
                logging.error(f"ThingSpeak error {resp.status_code}: {resp.text}")
        except Exception as e:
            logging.error(f"Error forwarding to ThingSpeak: {e}")

    def start(self):
        while True:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_forever()
            except Exception as e:
                logging.error(f"MQTT connection error: {e}")
                time.sleep(5)
