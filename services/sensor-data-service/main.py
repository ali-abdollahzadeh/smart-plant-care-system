"""
Sensor Data Service

- Subscribes to sensor data from MQTT
- Stores sensor data in InfluxDB with proper tagging for multi-device/multi-user support
- Provides REST API for querying sensor data
- Handles data retention and aggregation
"""
import os
import threading
import logging
import yaml
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
from database.influxdb import write_point, query_data, test_connection as test_influx_connection
from database.postgres import execute_query, test_connection as test_postgres_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

mqtt_conf = config['mqtt']

# Flask app for REST API
app = Flask(__name__)

def get_plant_info(plant_id):
    """Get plant information from catalogue service"""
    try:
        catalogue_url = os.environ.get('CATALOGUE_URL', 'http://catalogue-service:5000')
        response = requests.get(f"{catalogue_url}/plants/{plant_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching plant info: {e}")
    return None

def store_sensor_data(data):
    """Store sensor data in InfluxDB with proper tagging"""
    try:
        plant_id = data.get('plant_id')
        plant_info = get_plant_info(plant_id) if plant_id else None
        
        # Prepare tags for multi-device/multi-user support
        tags = {}
        if plant_id:
            tags['plant_id'] = plant_id
        if plant_info:
            tags['user_id'] = plant_info.get('user_id', 'unknown')
            tags['plant_name'] = plant_info.get('name', 'unknown')
            tags['plant_species'] = plant_info.get('species', 'unknown')
            tags['location'] = plant_info.get('location', 'unknown')
        
        # Add device info if available
        device_id = data.get('device_id', 'unknown')
        tags['device_id'] = device_id
        
        # Prepare fields (sensor readings)
        fields = {}
        if 'temperature' in data:
            fields['temperature'] = float(data['temperature'])
        if 'humidity' in data:
            fields['humidity'] = float(data['humidity'])
        if 'soil_moisture' in data:
            fields['soil_moisture'] = float(data['soil_moisture'])
        if 'lighting' in data:
            fields['lighting'] = data['lighting']
        if 'watering' in data:
            fields['watering'] = data['watering']
        
        # Add timestamp
        timestamp = data.get('timestamp')
        if timestamp:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Write to InfluxDB using shared utility
        write_point(
            measurement='sensor_readings',
            tags=tags,
            fields=fields,
            timestamp=timestamp
        )
        
        logger.info(f"Stored sensor data for plant_id={plant_id}, device_id={device_id}")
        
    except Exception as e:
        logger.error(f"Error storing sensor data: {e}")

# MQTT client for sensor data
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {mqtt_conf['broker_url']}:{mqtt_conf.get('port', 1883)}")
        client.subscribe(mqtt_conf['publish_topic'])
        logger.info(f"Subscribed to {mqtt_conf['publish_topic']}")
    else:
        logger.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Received sensor data: {data}")
        store_sensor_data(data)
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# REST API endpoints
@app.route('/data', methods=['GET'])
def get_sensor_data():
    """Get sensor data with filtering options"""
    try:
        plant_id = request.args.get('plant_id')
        user_id = request.args.get('user_id')
        device_id = request.args.get('device_id')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = int(request.args.get('limit', 100))
        
        # Build Flux query
        query = f'''
        from(bucket: "sensor_data")
            |> range(start: {start_time or "-1h"}, stop: {end_time or "now()"})
            |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
        '''
        
        if plant_id:
            query += f'|> filter(fn: (r) => r["plant_id"] == "{plant_id}")\n'
        if user_id:
            query += f'|> filter(fn: (r) => r["user_id"] == "{user_id}")\n'
        if device_id:
            query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'
        
        query += f'|> limit(n: {limit})\n'
        
        # Execute query using shared utility
        result = query_data(query)
        
        # Format results
        data_points = []
        for table in result:
            for record in table.records:
                data_point = {
                    'time': record.get_time().isoformat(),
                    'plant_id': record.values.get('plant_id'),
                    'user_id': record.values.get('user_id'),
                    'device_id': record.values.get('device_id'),
                    'plant_name': record.values.get('plant_name'),
                    'location': record.values.get('location'),
                    'field': record.get_field(),
                    'value': record.get_value()
                }
                data_points.append(data_point)
        
        return jsonify({
            'data': data_points,
            'count': len(data_points)
        })
        
    except Exception as e:
        logger.error(f"Error querying sensor data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/data/latest', methods=['GET'])
def get_latest_data():
    """Get latest sensor data for all plants"""
    try:
        plant_id = request.args.get('plant_id')
        user_id = request.args.get('user_id')
        
        # Build query for latest data
        query = f'''
        from(bucket: "sensor_data")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
        '''
        
        if plant_id:
            query += f'|> filter(fn: (r) => r["plant_id"] == "{plant_id}")\n'
        if user_id:
            query += f'|> filter(fn: (r) => r["user_id"] == "{user_id}")\n'
        
        query += '''
            |> last()
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = query_data(query)
        
        latest_data = []
        for table in result:
            for record in table.records:
                data_point = {
                    'time': record.get_time().isoformat(),
                    'plant_id': record.values.get('plant_id'),
                    'user_id': record.values.get('user_id'),
                    'device_id': record.values.get('device_id'),
                    'plant_name': record.values.get('plant_name'),
                    'location': record.values.get('location'),
                    'temperature': record.values.get('temperature'),
                    'humidity': record.values.get('humidity'),
                    'soil_moisture': record.values.get('soil_moisture'),
                    'lighting': record.values.get('lighting'),
                    'watering': record.values.get('watering')
                }
                latest_data.append(data_point)
        
        return jsonify({
            'data': latest_data,
            'count': len(latest_data)
        })
        
    except Exception as e:
        logger.error(f"Error querying latest data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/data/aggregated', methods=['GET'])
def get_aggregated_data():
    """Get aggregated sensor data (averages, min, max)"""
    try:
        plant_id = request.args.get('plant_id')
        user_id = request.args.get('user_id')
        window = request.args.get('window', '1h')  # 1h, 1d, 7d
        
        query = f'''
        from(bucket: "sensor_data")
            |> range(start: -{window})
            |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
        '''
        
        if plant_id:
            query += f'|> filter(fn: (r) => r["plant_id"] == "{plant_id}")\n'
        if user_id:
            query += f'|> filter(fn: (r) => r["user_id"] == "{user_id}")\n'
        
        query += '''
            |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = query_data(query)
        
        aggregated_data = []
        for table in result:
            for record in table.records:
                data_point = {
                    'time': record.get_time().isoformat(),
                    'plant_id': record.values.get('plant_id'),
                    'user_id': record.values.get('user_id'),
                    'avg_temperature': record.values.get('temperature'),
                    'avg_humidity': record.values.get('humidity'),
                    'avg_soil_moisture': record.values.get('soil_moisture')
                }
                aggregated_data.append(data_point)
        
        return jsonify({
            'data': aggregated_data,
            'window': window,
            'count': len(aggregated_data)
        })
        
    except Exception as e:
        logger.error(f"Error querying aggregated data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test InfluxDB connection
        influx_ok = test_influx_connection()
        
        # Test PostgreSQL connection (for plant info)
        postgres_ok = test_postgres_connection()
        
        return jsonify({
            'status': 'healthy' if influx_ok and postgres_ok else 'unhealthy',
            'influxdb': 'connected' if influx_ok else 'disconnected',
            'postgres': 'connected' if postgres_ok else 'disconnected',
            'mqtt': 'connected' if mqtt_client.is_connected() else 'disconnected'
        }), 200 if influx_ok and postgres_ok else 500
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Start MQTT client
    try:
        mqtt_client.connect(mqtt_conf['broker_url'], mqtt_conf.get('port', 1883), 60)
        threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()
        logger.info("MQTT client started")
    except Exception as e:
        logger.error(f"Failed to start MQTT client: {e}")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5004) 