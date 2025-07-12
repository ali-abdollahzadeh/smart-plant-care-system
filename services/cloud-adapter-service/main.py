import os
import threading
import logging
import yaml
import requests
from flask import Flask
from mqtt_subscriber import MqttToThingSpeakBridge
import rest_adapter


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

CONFIG_PATH = os.environ.get("CONFIG_PATH", "../shared/config/global_config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']
thingspeak_conf = config['thingspeak']

# Auto-register service in catalogue
CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/services')
try:
    reg_payload = {
        "name": "Cloud Adapter Service",
        "type": "cloud-adapter",
        "config": {"data_endpoint": "/data"}
    }
    resp = requests.post(CATALOGUE_URL, json=reg_payload, timeout=5)
    if resp.status_code == 201:
        logging.info(f"Service registered in catalogue: {resp.json()}")
    else:
        logging.warning(f"Service registration failed: {resp.status_code} {resp.text}")
except Exception as e:
    logging.error(f"Could not register service in catalogue: {e}")

bridge = MqttToThingSpeakBridge(
    broker=mqtt_conf['broker_url'],
    port=mqtt_conf.get('port', 1883),
    subscribe_topic=mqtt_conf['publish_topic'],
    thingspeak_url=thingspeak_conf['update_url'],
    write_api_key=thingspeak_conf['write_api_key']
)

app = rest_adapter.app

if __name__ == '__main__':
    # Start MQTT subscriber in a background thread
    threading.Thread(target=bridge.start, daemon=True).start()
    # Start Flask app
    app.run(host='0.0.0.0', port=5001)
