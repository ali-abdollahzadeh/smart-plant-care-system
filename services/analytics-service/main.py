"""
Analytics Service

- Subscribes to sensor data topic (plant/sensor)
- Publishes actuator commands to command_topic (plant/command) for automated control
- Generates weekly reports
"""
import os
import threading
import logging
import yaml
import requests
from flask import Flask, jsonify
from report_generator import generate_weekly_report
from control_center import ControlCenter

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Load config
CONFIG_PATH = os.environ.get("CONFIG_PATH", "../shared/config/global_config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']
thingspeak_conf = config['thingspeak']
thresholds = config['sensor_thresholds']

# Auto-register service in catalogue
CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/services')
try:
    reg_payload = {
        "name": "Analytics Service",
        "type": "analytics",
        "config": {"report_endpoint": "/report/weekly"}
    }
    resp = requests.post(CATALOGUE_URL, json=reg_payload, timeout=5)
    if resp.status_code == 201:
        logging.info(f"Service registered in catalogue: {resp.json()}")
    else:
        logging.warning(f"Service registration failed: {resp.status_code} {resp.text}")
except Exception as e:
    logging.error(f"Could not register service in catalogue: {e}")

# Start control center in a thread
COMMAND_TOPIC = mqtt_conf.get('command_topic', 'plant/command')
control = ControlCenter(
    broker=mqtt_conf['broker_url'],
    port=mqtt_conf.get('port', 1883),
    subscribe_topic=mqtt_conf['publish_topic'],
    command_topic=COMMAND_TOPIC,
    thresholds=thresholds
)
threading.Thread(target=control.start_monitoring, daemon=True).start()

# Flask app for report endpoint
app = Flask(__name__)

@app.route('/report/weekly', methods=['GET'])
def weekly_report():
    report = generate_weekly_report(
        channel_id=thingspeak_conf['channel_id'],
        read_api_key=thingspeak_conf['read_api_key']
    )
    return jsonify(report)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
