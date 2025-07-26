import os
import threading
import logging
import yaml
import requests
import paho.mqtt.client as mqtt
from db import init_db, ensure_db

# Initialize database before importing telegram_bot
init_db()
ensure_db()

from bot.telegram_bot import start_bot
from dashboard.dashboard import app  # import the dashboard Flask app
from bot.notifier import send_alert

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']

# Auto-register service in catalogue
CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/services')
try:
    reg_payload = {
        "name": "User Service",
        "type": "user",
        "config": {"bot": "telegram"}
    }
    resp = requests.post(CATALOGUE_URL, json=reg_payload, timeout=5)
    if resp.status_code == 201:
        logging.info(f"Service registered in catalogue: {resp.json()}")
    else:
        logging.warning(f"Service registration failed: {resp.status_code} {resp.text}")
except Exception as e:
    logging.error(f"Could not register service in catalogue: {e}")

# MQTT alert handler
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Connected to MQTT broker at {mqtt_conf['broker_url']}:{mqtt_conf.get('port', 1883)}")
        client.subscribe(mqtt_conf['subscribe_topic'])
        logging.info(f"Subscribed to {mqtt_conf['subscribe_topic']}")
    else:
        logging.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    try:
        alert = msg.payload.decode()
        send_alert(f"🚨 Alert: {alert}")
    except Exception as e:
        logging.error(f"Error processing MQTT alert: {e}")

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(mqtt_conf['broker_url'], mqtt_conf.get('port', 1883), 60)
            client.loop_forever()
        except Exception as e:
            logging.error(f"MQTT connection error: {e}")

if __name__ == '__main__':
    threading.Thread(target=start_mqtt_listener, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5500), daemon=True).start()
    start_bot()  # Run the Telegram bot in the main thread
