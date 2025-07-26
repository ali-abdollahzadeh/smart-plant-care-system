import os
import logging
import yaml
import requests
import json
import ast
from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import init_db, ensure_db, get_connection, add_user, get_user_by_telegram_id

# Initialize database
init_db()
ensure_db()

app = Flask(__name__, template_folder='templates', static_folder='static')

# Load config
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Configuration
CATALOGUE_API_URL = os.environ.get('CATALOGUE_API_URL', 'http://catalogue-service:5000')
SENSOR_API_URL = os.environ.get('SENSOR_API_URL', 'http://sensor-service:5500')

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        # Get statistics
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            user_count = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM plants')
            plant_count = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM plants WHERE active = 1')
            active_plants = c.fetchone()[0]
        
        # Get alerts count (placeholder for now)
        alerts_count = 0
        
        return render_template('dashboard.html', 
                             user_count=user_count,
                             plant_count=plant_count,
                             active_plants=active_plants,
                             alerts_count=alerts_count)
    except Exception as e:
        logging.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', 
                             user_count=0,
                             plant_count=0,
                             active_plants=0,
                             alerts_count=0)

@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    """Register a new user"""
    message = None
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            display_name = request.form.get('display_name')
            telegram_id = request.form.get('telegram_id')
            
            # Add user to local database
            user_id = add_user(telegram_id or username, display_name or username)
            
            # Also register in catalogue service
            try:
                catalogue_payload = {
                    "username": username,
                    "display_name": display_name or username
                }
                resp = requests.post(f"{CATALOGUE_API_URL}/users", json=catalogue_payload, timeout=5)
                if resp.status_code == 201:
                    logging.info(f"User registered in catalogue: {resp.json()}")
                else:
                    logging.warning(f"Catalogue registration failed: {resp.status_code}")
            except Exception as e:
                logging.error(f"Could not register user in catalogue: {e}")
            
            message = f"User '{display_name or username}' registered successfully!"
            
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            message = f"Error registering user: {str(e)}"
    
    return render_template('register_user.html', message=message)

@app.route('/register_plant', methods=['GET', 'POST'])
def register_plant():
    """Register a new plant"""
    message = None
    
    try:
        # Fetch users from DB
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id, name, telegram_id FROM users')
            users = c.fetchall()
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        users = []
    
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            name = request.form.get('name')
            type_ = request.form.get('type')
            species = request.form.get('species')
            location = request.form.get('location')
            thresholds = request.form.get('thresholds')
            
            # Parse thresholds
            try:
                thresholds_dict = ast.literal_eval(thresholds)
            except Exception:
                thresholds_dict = json.loads(thresholds)
            
            # Register plant in local database
            from telegram_bot import register_plant_for_user
            register_plant_for_user(user_id, name, type_, str(thresholds_dict), species, location)
            
            # Also register in catalogue service
            try:
                catalogue_payload = {
                    "name": name,
                    "species": species,
                    "location": location,
                    "thresholds": thresholds_dict,
                    "user_id": user_id
                }
                resp = requests.post(f"{CATALOGUE_API_URL}/plants", json=catalogue_payload, timeout=5)
                if resp.status_code == 201:
                    logging.info(f"Plant registered in catalogue: {resp.json()}")
                else:
                    logging.warning(f"Catalogue registration failed: {resp.status_code}")
            except Exception as e:
                logging.error(f"Could not register plant in catalogue: {e}")
            
            message = f"Plant '{name}' registered successfully!"
            
        except Exception as e:
            logging.error(f"Error registering plant: {e}")
            message = f"Error registering plant: {str(e)}"
    
    return render_template('register_plant.html', users=users, message=message)

@app.route('/register_plant_advanced', methods=['GET', 'POST'])
def register_plant_advanced():
    """Register a new plant using the plant database"""
    message = None
    
    try:
        # Load plant types from catalogue service
        plant_types_resp = requests.get(f"{CATALOGUE_API_URL}/plant_types", timeout=5)
        if plant_types_resp.status_code == 200:
            plant_types = plant_types_resp.json()
        else:
            # Fallback to local plant database if available
            try:
                with open('home_plants_database.json', 'r') as f:
                    plant_types = json.load(f)
            except FileNotFoundError:
                plant_types = []
    except Exception as e:
        logging.error(f"Error loading plant types: {e}")
        plant_types = []
    
    try:
        # Fetch users from catalogue service
        users_resp = requests.get(f"{CATALOGUE_API_URL}/users", timeout=5)
        users = users_resp.json() if users_resp.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        users = []
    
    try:
        # Fetch existing plants from catalogue service
        plants_resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        plants = plants_resp.json() if plants_resp.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching plants: {e}")
        plants = []
    
    if request.method == 'POST':
        try:
            plant_type_idx = int(request.form.get('plant_type_idx'))
            plant_type = plant_types[plant_type_idx]
            name = plant_type['display_name']
            species = plant_type['species']
            location = request.form.get('location')
            user_id = request.form.get('user_id')
            thresholds = plant_type['default_thresholds']
            care_info = plant_type['care_info']
            
            # Register plant in catalogue service
            catalogue_payload = {
                "name": name,
                "species": species,
                "location": location,
                "thresholds": thresholds,
                "care_info": care_info,
                "user_id": user_id
            }
            resp = requests.post(f"{CATALOGUE_API_URL}/plants", json=catalogue_payload, timeout=5)
            
            if resp.status_code == 201:
                # Also register in local database
                try:
                    from telegram_bot import register_plant_for_user
                    register_plant_for_user(user_id, name, "database", str(thresholds), species, location)
                except Exception as e:
                    logging.error(f"Could not register plant in local DB: {e}")
                
                message = f"Plant '{name}' registered successfully!"
            else:
                message = f"Failed to register plant: {resp.status_code}"
                
        except Exception as e:
            logging.error(f"Error registering plant: {e}")
            message = f"Error registering plant: {str(e)}"
    
    return render_template('register_plant_advanced.html', 
                         plant_types=plant_types, 
                         users=users, 
                         plants=plants, 
                         message=message)

@app.route('/assign_plant', methods=['GET', 'POST'])
def assign_plant():
    """Assign a plant to a user"""
    message = None
    error = None
    
    try:
        # Fetch users from catalogue-service
        users_resp = requests.get(f"{CATALOGUE_API_URL}/users", timeout=5)
        users = users_resp.json() if users_resp.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching users from catalogue: {e}")
        users = []
    
    try:
        # Fetch plants from catalogue-service
        plants_resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        plants = plants_resp.json() if plants_resp.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching plants from catalogue: {e}")
        plants = []
    
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            plant_id = request.form.get('plant_id')
            
            # Assign plant by updating user_id in catalogue-service
            update_resp = requests.patch(f"{CATALOGUE_API_URL}/plants/{plant_id}", 
                                       json={"user_id": user_id}, timeout=5)
            
            if update_resp.status_code == 200:
                message = "Plant assigned successfully!"
            else:
                error = f"Failed to assign plant: {update_resp.status_code}"
                
        except Exception as e:
            logging.error(f"Error assigning plant: {e}")
            error = f"Error assigning plant: {str(e)}"
    
    return render_template('assign_plant.html', users=users, plants=plants, message=message, error=error)

@app.route('/plant_status')
def plant_status():
    """Show plant status and sensor data"""
    try:
        # Fetch plants from catalogue-service
        plants_resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        plants = plants_resp.json() if plants_resp.status_code == 200 else []
        
        # Fetch sensor data for each plant
        for plant in plants:
            try:
                # Get sensor data from sensor service
                sensor_resp = requests.get(f"{SENSOR_API_URL}/sensor_data/{plant['id']}", timeout=5)
                if sensor_resp.status_code == 200:
                    plant['sensor_data'] = sensor_resp.json()
                else:
                    plant['sensor_data'] = None
            except Exception as e:
                logging.error(f"Error fetching sensor data for plant {plant['id']}: {e}")
                plant['sensor_data'] = None
            
            # Determine plant status based on sensor data and thresholds
            if plant.get('sensor_data') and plant.get('thresholds'):
                try:
                    thresholds = plant['thresholds'] if isinstance(plant['thresholds'], dict) else json.loads(plant['thresholds'])
                    sensor_data = plant['sensor_data']
                    
                    # Simple status determination
                    if (sensor_data.get('temperature', 0) < thresholds.get('temperature', {}).get('min', 0) or
                        sensor_data.get('temperature', 0) > thresholds.get('temperature', {}).get('max', 100) or
                        sensor_data.get('humidity', 0) < thresholds.get('humidity', {}).get('min', 0) or
                        sensor_data.get('humidity', 0) > thresholds.get('humidity', {}).get('max', 100)):
                        plant['status'] = 'alert'
                    elif (sensor_data.get('temperature', 0) < thresholds.get('temperature', {}).get('min', 0) + 2 or
                          sensor_data.get('temperature', 0) > thresholds.get('temperature', {}).get('max', 100) - 2):
                        plant['status'] = 'warning'
                    else:
                        plant['status'] = 'healthy'
                except Exception as e:
                    logging.error(f"Error determining plant status: {e}")
                    plant['status'] = 'unknown'
            else:
                plant['status'] = 'unknown'
            
            # Get owner name
            if plant.get('user_id'):
                try:
                    user_resp = requests.get(f"{CATALOGUE_API_URL}/users/{plant['user_id']}", timeout=5)
                    if user_resp.status_code == 200:
                        user_data = user_resp.json()
                        plant['owner_name'] = user_data.get('display_name') or user_data.get('username', 'Unknown')
                    else:
                        plant['owner_name'] = 'Unknown'
                except Exception as e:
                    logging.error(f"Error fetching user data: {e}")
                    plant['owner_name'] = 'Unknown'
            else:
                plant['owner_name'] = 'Unassigned'
        
    except Exception as e:
        logging.error(f"Error loading plant status: {e}")
        plants = []
    
    return render_template('plant_status.html', plants=plants)

@app.route('/actuator', methods=['POST'])
def actuator_control():
    """Control actuators (water, LED)"""
    try:
        data = request.get_json()
        action = data.get('action')
        plant_id = data.get('plant_id')
        
        if not action or not plant_id:
            return jsonify({'success': False, 'message': 'Missing action or plant_id'})
        
        # Forward request to sensor service
        sensor_resp = requests.post(f"{SENSOR_API_URL}/actuator", 
                                   json={'action': action, 'plant_id': plant_id}, 
                                   timeout=5)
        
        if sensor_resp.status_code == 200:
            return jsonify({'success': True, 'message': f'{action} action completed'})
        else:
            return jsonify({'success': False, 'message': f'Sensor service error: {sensor_resp.status_code}'})
            
    except Exception as e:
        logging.error(f"Error controlling actuator: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'user-service-dashboard'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug=True) 