"""
Cloud Adapter Service

    Reads config from CONFIG_PATH (default: config.yaml)
    Exposes REST API via rest_adapter (served on 0.0.0.0:5001), e.g., /data
    Acts as a proxy to sensor-data-service for external cloud integrations
    Auto-registers with Catalogue at CATALOGUE_URL as type "cloud-adapter"
    Environment:
        CONFIG_PATH: path to YAML config (default: config.yaml)
        CATALOGUE_URL: service registry URL (default: http://catalogue-service:5000/services)
        SENSOR_DATA_SERVICE_URL: sensor data service URL (default: http://sensor-data-service:5004)
    Logging: INFO level to stdout
"""

import os
import logging
import yaml
import requests
import rest_adapter


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

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

app = rest_adapter.app

if __name__ == '__main__':
    # Start Flask app - no MQTT needed, just proxy to sensor-data-service
    logging.info("Starting Cloud Adapter Service as proxy to sensor-data-service")
    app.run(host='0.0.0.0', port=5001)
