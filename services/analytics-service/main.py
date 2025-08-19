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
from flask import Flask, jsonify, request
from report_generator.report_generator import generate_weekly_report
from sensor_control.control_center import ControlCenter
from database.influxdb import test_connection as test_influx_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Load config
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']
thresholds = config['sensor_thresholds']

# Auto-register service in catalogue
CATALOGUE_URL = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000/services')
try:
    reg_payload = {
        "name": "Analytics Service",
        "type": "analytics",
        "config": {"report_endpoint": "/report/weekly"} # Available in http://catalogue-service:5003/report/weekly
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
    days = int(request.args.get('days', 7))
    plant_id = request.args.get('plant_id')
    report = generate_weekly_report(days=days, plant_id=plant_id)
    return jsonify(report)

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    influx_ok = test_influx_connection()
    return jsonify({
        'status': 'healthy' if influx_ok else 'unhealthy',
        'influxdb': 'connected' if influx_ok else 'disconnected',
        'control_center': 'running'
    }), 200 if influx_ok else 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
