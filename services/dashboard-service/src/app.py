from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import requests
import json
import paho.mqtt.client as mqtt
import threading
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'smart-plant-dashboard-secret'

# Configuration
CATALOGUE_URL = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "smartplant")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Global data storage
latest_sensor_data = {}
plants_data = {}
users_data = {}
thresholds_data = {}
alerts_data = {}

# MQTT Client
mqtt_client = mqtt.Client()
mqtt_connected = False

def on_mqtt_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("Dashboard connected to MQTT")
        client.subscribe("smartplant/+/telemetry")
    else:
        print(f"Failed to connect to MQTT: {rc}")

def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        plant_id = str(data.get('plant_id', ''))
        sensor = data.get('sensor', '')
        value = data.get('value', 0)
        timestamp = data.get('ts', datetime.now().isoformat())
        
        if plant_id not in latest_sensor_data:
            latest_sensor_data[plant_id] = {}
        
        latest_sensor_data[plant_id][sensor] = {
            'value': value,
            'timestamp': timestamp
        }
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def setup_mqtt():
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()

def refresh_data():
    """Refresh data from catalogue service"""
    global plants_data, users_data, thresholds_data, alerts_data
    
    try:
        # Get plants
        response = requests.get(f"{CATALOGUE_URL}/plants", timeout=5)
        if response.status_code == 200:
            plants_data = {p['id']: p for p in response.json()}
        
        # Get users
        response = requests.get(f"{CATALOGUE_URL}/users", timeout=5)
        if response.status_code == 200:
            users_data = {u['id']: u for u in response.json()}
        
        # Get thresholds
        response = requests.get(f"{CATALOGUE_URL}/thresholds", timeout=5)
        if response.status_code == 200:
            thresholds_data = {t['id']: t for t in response.json()}
        
        # Get recent alerts
        response = requests.get(f"{CATALOGUE_URL}/alerts", timeout=5)
        if response.status_code == 200:
            alerts_data = {a['id']: a for a in response.json()}
            
    except Exception as e:
        print(f"Error refreshing data: {e}")

def data_refresh_loop():
    """Background thread to refresh data periodically"""
    while True:
        refresh_data()
        time.sleep(30)  # Refresh every 30 seconds

@app.route('/')
def index():
    return render_template('index.html', 
                         plants=plants_data,
                         users=users_data,
                         sensor_data=latest_sensor_data,
                         thresholds=thresholds_data,
                         alerts=alerts_data)

@app.route('/plants')
def plants():
    return render_template('plants.html', plants=plants_data)

@app.route('/plants/new', methods=['GET', 'POST'])
def new_plant():
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'type': request.form['type']
        }
        try:
            response = requests.post(f"{CATALOGUE_URL}/plants", json=data, timeout=5)
            if response.status_code == 200:
                flash('Plant created successfully!', 'success')
                refresh_data()
                return redirect(url_for('plants'))
            else:
                flash('Failed to create plant', 'error')
        except Exception as e:
            flash(f'Error creating plant: {e}', 'error')
    
    return render_template('new_plant.html')

@app.route('/users')
def users():
    return render_template('users.html', users=users_data)

@app.route('/thresholds')
def thresholds():
    return render_template('thresholds.html', 
                         thresholds=thresholds_data,
                         plants=plants_data)

@app.route('/thresholds/new', methods=['GET', 'POST'])
def new_threshold():
    if request.method == 'POST':
        data = {
            'plant_id': int(request.form['plant_id']),
            'sensor': request.form['sensor'],
            'min_val': float(request.form['min_val']) if request.form['min_val'] else None,
            'max_val': float(request.form['max_val']) if request.form['max_val'] else None,
            'hysteresis': float(request.form['hysteresis']) if request.form['hysteresis'] else 0.0
        }
        try:
            response = requests.post(f"{CATALOGUE_URL}/thresholds", json=data, timeout=5)
            if response.status_code == 200:
                flash('Threshold created successfully!', 'success')
                refresh_data()
                return redirect(url_for('thresholds'))
            else:
                flash('Failed to create threshold', 'error')
        except Exception as e:
            flash(f'Error creating threshold: {e}', 'error')
    
    return render_template('new_threshold.html', plants=plants_data)

@app.route('/alerts')
def alerts():
    return render_template('alerts.html', alerts=alerts_data, plants=plants_data)

@app.route('/api/sensor_data/<plant_id>')
def api_sensor_data(plant_id):
    """API endpoint for real-time sensor data"""
    return jsonify(latest_sensor_data.get(plant_id, {}))

@app.route('/api/water_plant', methods=['POST'])
def api_water_plant():
    """API endpoint to water a plant"""
    data = request.get_json()
    plant_id = data.get('plant_id', '1')
    amount = data.get('amount', 200)
    
    # Publish MQTT command
    topic = f"smartplant/{plant_id}/actuators/water/set"
    payload = {
        "device": "water",
        "amount": amount,
        "note": "manual_dashboard"
    }
    
    if mqtt_connected:
        mqtt_client.publish(topic, json.dumps(payload))
        return jsonify({"status": "success", "message": f"Watering command sent for plant {plant_id}"})
    else:
        return jsonify({"status": "error", "message": "MQTT not connected"}), 500

@app.route('/api/assign_user', methods=['POST'])
def api_assign_user():
    """API endpoint to assign user to plant"""
    data = request.get_json()
    try:
        response = requests.post(f"{CATALOGUE_URL}/assignments", json=data, timeout=5)
        if response.status_code == 200:
            refresh_data()
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to assign user"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start background threads
    setup_mqtt()
    threading.Thread(target=data_refresh_loop, daemon=True).start()
    
    # Initial data refresh
    refresh_data()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
