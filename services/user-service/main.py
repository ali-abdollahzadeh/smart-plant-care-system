import os
import threading
import logging
import yaml
import requests
import paho.mqtt.client as mqtt
from db import init_db, ensure_db
from bot.telegram_bot import start_bot


# Initialize database before importing telegram_bot
init_db()
ensure_db()

from bot.telegram_bot import start_bot
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
    # Import dashboard after database initialization
    from dashboard.dashboard import app
    
if __name__ == "__main__":
    # ...
    # MQTT listener can stay daemon
    threading.Thread(target=start_mqtt_listener, name="mqtt-listener", daemon=True).start()

    # Telegram bot MUST NOT be daemon
    threading.Thread(target=start_bot, name="telegram-bot", daemon=False).start()

    # Run Flask in the main thread; no reloader to avoid a second process
    app.run(host='0.0.0.0', port=5500, debug=False, use_reloader=False)
