from flask import Flask, jsonify, request
import os
import yaml
import logging
from thingspeak_client import get_data
from mqtt_subscriber import latest_data

app = Flask(__name__)

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

thingspeak_conf = config['thingspeak']

@app.route('/data', methods=['GET'])
def get_latest_data():
    plant_id = request.args.get('plant_id')
    logging.info(f"/data requested for plant_id: {plant_id}")
    logging.info(f"Current latest_data keys: {list(latest_data.keys())}")
    try:
        if plant_id:
            data = latest_data.get(plant_id)
            if data:
                return jsonify(data)
            else:
                logging.error(f"No data for plant_id {plant_id}")
                return jsonify({'error': 'No data for this plant_id'}), 404
        # If no plant_id, return all in-memory latest_data
        return jsonify(latest_data)
    except Exception as e:
        logging.error(f"Exception in /data endpoint: {e}")
        return jsonify({'error': str(e)}), 500

# (Optional) Add a new endpoint for ThingSpeak history
@app.route('/thingspeak_data', methods=['GET'])
def get_thingspeak_data():
    results = int(request.args.get('results', 100))
    feeds = get_data(
        channel_id=thingspeak_conf['channel_id'],
        read_api_key=thingspeak_conf['read_api_key'],
        results=results
    )
    return jsonify(feeds)
