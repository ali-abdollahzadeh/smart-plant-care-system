import paho.mqtt.client as mqtt
import logging
import json
import time

class MQTTPublisher:
    def __init__(self, broker, port=1883, client_id=None):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"sensor-pub-{int(time.time())}"
        self.client = mqtt.Client(self.client_id)
        self.connected = False
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.warning("Disconnected from MQTT broker.")

    def connect(self):
        while not self.connected:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                time.sleep(1)
            except Exception as e:
                logging.error(f"MQTT connection error: {e}")
                time.sleep(5)

    def publish(self, topic, payload):
        if not self.connected:
            logging.warning("Not connected to MQTT. Attempting reconnect...")
            self.connect()
        try:
            msg = json.dumps(payload)
            result = self.client.publish(topic, msg)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"Published to {topic}: {msg}")
            else:
                logging.error(f"Failed to publish to {topic}: {msg}")
        except Exception as e:
            logging.error(f"Publish error: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        logging.info("MQTT publisher disconnected.")
