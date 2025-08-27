from flask import Flask, jsonify, request
import os
import yaml
import logging
import requests

app = Flask(__name__)

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Use sensor-data-service as the single source of truth
SENSOR_DATA_SERVICE_URL = os.environ.get('SENSOR_DATA_SERVICE_URL', 'http://sensor-data-service:5004')

logging.getLogger(__name__)

@app.route('/data', methods=['GET'])
def get_latest_data():
    """Proxy requests to sensor-data-service for latest data from InfluxDB"""
    plant_id = request.args.get('plant_id')
    logging.info(f"/data requested for plant_id: {plant_id}")
    
    try:
        # Forward request to sensor-data-service /data/latest endpoint
        params = {'plant_id': plant_id} if plant_id else {}
        resp = requests.get(f"{SENSOR_DATA_SERVICE_URL}/data/latest", params=params, timeout=5)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            logging.error(f"Sensor-data-service error: {resp.status_code} {resp.text}")
            return jsonify({'error': 'Failed to fetch data from sensor-data-service'}), resp.status_code
            
    except Exception as e:
        logging.error(f"Exception in /data endpoint: {e}")
        return jsonify({'error': str(e)}), 500