from flask import Flask, request, jsonify, abort, render_template_string, redirect, url_for
import uuid
import os
import json
import logging
from database.postgres import execute_query, test_connection

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_real_dict_rows(data):
    """Convert RealDictRow objects to regular dictionaries"""
    if isinstance(data, list):
        return [dict(row) for row in data]
    elif hasattr(data, '__dict__'):
        return dict(data)
    else:
        return data

def init_db():
    """Initialize database schema - now handled by migrations"""
    try:
        if test_connection():
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection failed")
            return False
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

# Initialize database on startup
init_db()

# Device endpoints
@app.route('/devices', methods=['POST'])
def register_device():
    """Register a new device"""
    try:
        data = request.json
        device_id = str(uuid.uuid4())
        name = data.get('name')
        type_ = data.get('type')
        config = json.dumps(data.get('config', {}))
        user_id = data.get('user_id')
        
        query = """
            INSERT INTO devices (id, name, type, config, user_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (device_id, name, type_, config, user_id))
        
        if result:
            logger.info(f"Registered device: {name} with ID {device_id}")
            return jsonify({
                'id': device_id, 
                'name': name, 
                'type': type_, 
                'config': data.get('config', {})
            }), 201
        else:
            return jsonify({'error': 'Failed to register device'}), 500
            
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/devices', methods=['GET'])
def list_devices():
    """List all devices"""
    try:
        query = """
            SELECT d.*, u.display_name as user_name
            FROM devices d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.active = TRUE
            ORDER BY d.created_at DESC
        """
        devices = execute_query(query)
        
        # Convert RealDictRow objects to regular dictionaries
        devices = convert_real_dict_rows(devices)
        
        # Convert JSONB config back to dict
        for device in devices:
            if device['config']:
                device['config'] = json.loads(device['config'])
        
        return jsonify(devices)
        
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """Get a specific device"""
    try:
        query = """
            SELECT d.*, u.display_name as user_name
            FROM devices d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.id = %s AND d.active = TRUE
        """
        result = execute_query(query, (device_id,))
        
        if result:
            device = convert_real_dict_rows(result[0])
            if device['config']:
                device['config'] = json.loads(device['config'])
            return jsonify(device)
        else:
            abort(404)
            
    except Exception as e:
        logger.error(f"Failed to get device: {e}")
        return jsonify({'error': str(e)}), 500

# Service endpoints
@app.route('/services', methods=['POST'])
def register_service():
    """Register a new service"""
    try:
        data = request.json
        service_id = str(uuid.uuid4())
        name = data.get('name')
        type_ = data.get('type')
        config = json.dumps(data.get('config', {}))
        endpoint = data.get('endpoint')
        
        query = """
            INSERT INTO services (id, name, type, config, endpoint)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (service_id, name, type_, config, endpoint))
        
        if result:
            logger.info(f"Registered service: {name} with ID {service_id}")
            return jsonify({
                'id': service_id, 
                'name': name, 
                'type': type_, 
                'config': data.get('config', {}),
                'endpoint': endpoint
            }), 201
        else:
            return jsonify({'error': 'Failed to register service'}), 500
            
    except Exception as e:
        logger.error(f"Service registration failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/services', methods=['GET'])
def list_services():
    """List all services"""
    try:
        query = """
            SELECT * FROM services 
            WHERE active = TRUE
            ORDER BY created_at DESC
        """
        services = execute_query(query)
        
        # Convert RealDictRow objects to regular dictionaries
        services = convert_real_dict_rows(services)
        
        # Convert JSONB config back to dict
        for service in services:
            if service['config']:
                service['config'] = json.loads(service['config'])
        
        return jsonify(services)
        
    except Exception as e:
        logger.error(f"Failed to list services: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/services/<service_id>', methods=['GET'])
def get_service(service_id):
    """Get a specific service"""
    try:
        query = "SELECT * FROM services WHERE id = %s AND active = TRUE"
        result = execute_query(query, (service_id,))
        
        if result:
            service = convert_real_dict_rows(result[0])
            if service['config']:
                service['config'] = json.loads(service['config'])
            return jsonify(service)
        else:
            abort(404)
            
    except Exception as e:
        logger.error(f"Failed to get service: {e}")
        return jsonify({'error': str(e)}), 500

# Plant endpoints
@app.route('/plants', methods=['POST'])
def register_plant():
    """Register a new plant (no assignment here)"""
    try:
        data = request.json or {}

        # Reject any attempt to assign via this endpoint
        if 'user_id' in data and data['user_id']:
            return jsonify({
                'error': "User assignment is not allowed in this endpoint. "
                         "Register the plant first, then assign via a dedicated assignment endpoint."
            }), 400

        plant_id = str(uuid.uuid4())
        name = data.get('name')
        species = data.get('species')
        location = data.get('location')
        thresholds = json.dumps(data.get('thresholds', {}))
        care_info = json.dumps(data.get('care_info', {}))

        query = """
            INSERT INTO plants (id, name, species, location, thresholds, care_info)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (plant_id, name, species, location, thresholds, care_info))

        if result:
            logger.info(f"Registered plant: {name} with ID {plant_id}")
            return jsonify({
                'id': plant_id,
                'name': name,
                'species': species,
                'location': location,
                'thresholds': data.get('thresholds', {}),
                'care_info': data.get('care_info', {})
            }), 201
        else:
            return jsonify({'error': 'Failed to register plant'}), 500

    except Exception as e:
        logger.error(f"Plant registration failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plants', methods=['GET'])
def list_plants():
    """List all plants"""
    try:
        query = """
            SELECT 
                p.*,
                up.user_id AS user_id,
                u.display_name AS user_name
            FROM plants p
            LEFT JOIN user_plants up ON p.id = up.plant_id
            LEFT JOIN users u ON up.user_id = u.id
            WHERE p.active = TRUE
            ORDER BY p.created_at DESC
        """
        plants = execute_query(query)
        
        # Convert RealDictRow objects to regular dictionaries
        plants = convert_real_dict_rows(plants)
        
        # Convert JSONB fields back to dict
        for plant in plants:
            if plant['thresholds']:
                if isinstance(plant['thresholds'], str):
                    plant['thresholds'] = json.loads(plant['thresholds'])
            if plant['care_info']:
                if isinstance(plant['care_info'], str):
                    plant['care_info'] = json.loads(plant['care_info'])
        
        return jsonify(plants)
        
    except Exception as e:
        logger.error(f"Failed to list plants: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plants/active', methods=['GET'])
def list_active_plants():
    """List all active plants with user assignments"""
    try:
        query = """
            SELECT 
                p.*,
                up.user_id AS user_id,
                u.display_name AS user_name
            FROM plants p
            LEFT JOIN user_plants up ON p.id = up.plant_id
            LEFT JOIN users u ON up.user_id = u.id
            WHERE p.active = TRUE
            ORDER BY p.created_at DESC
        """
        plants = execute_query(query)
        
        # Convert RealDictRow objects to regular dictionaries
        plants = convert_real_dict_rows(plants)
        
        # Convert JSONB fields back to dict
        for plant in plants:
            if plant['thresholds']:
                if isinstance(plant['thresholds'], str):
                    plant['thresholds'] = json.loads(plant['thresholds'])
            if plant['care_info']:
                if isinstance(plant['care_info'], str):
                    plant['care_info'] = json.loads(plant['care_info'])
        
        return jsonify(plants)
        
    except Exception as e:
        logger.error(f"Failed to list active plants: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plants/<plant_id>', methods=['GET'])
def get_plant(plant_id):
    """Get a specific plant"""
    try:
        query = """
            SELECT 
                p.*,
                up.user_id AS user_id,           -- keep API field stable for clients
                u.display_name AS user_name
            FROM plants p
            LEFT JOIN user_plants up ON p.id = up.plant_id
            LEFT JOIN users u       ON up.user_id = u.id
            WHERE p.id = %s AND p.active = TRUE
        """
        result = execute_query(query, (plant_id,))
        
        if result:
            plant = convert_real_dict_rows(result[0])
            if plant['thresholds']:
                if isinstance(plant['thresholds'], str):
                    plant['thresholds'] = json.loads(plant['thresholds'])
            if plant['care_info']:
                if isinstance(plant['care_info'], str):
                    plant['care_info'] = json.loads(plant['care_info'])
            return jsonify(plant)
        else:
            abort(404)
            
    except Exception as e:
        logger.error(f"Failed to get plant: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plants/<plant_id>', methods=['PATCH'])
def update_plant(plant_id):
    """Update a plant (no assignment here)"""
    try:
        data = request.json or {}

        # Reject any attempt to assign via this endpoint
        if 'user_id' in data:
            return jsonify({
                'error': "User assignment updates are not allowed in this endpoint. "
                         "Use a dedicated assignment endpoint to manage user↔plant relationships."
            }), 400

        # Build dynamic update query for plant fields only
        set_clauses = []
        params = []

        for key, value in data.items():
            if key in ['thresholds', 'care_info'] and value is not None:
                set_clauses.append(f"{key} = %s")
                params.append(json.dumps(value))
            elif key in ['name', 'species', 'location', 'active'] and value is not None:
                set_clauses.append(f"{key} = %s")
                params.append(value)
            # ignore other fields silently

        if set_clauses:
            set_clauses.append("updated_at = NOW()")
            params.append(plant_id)
            query = f"""
                UPDATE plants
                SET {', '.join(set_clauses)}
                WHERE id = %s AND active = TRUE
            """
            result = execute_query(query, params)
            if result == 0:
                return jsonify({'error': 'Plant not found'}), 404

        logger.info(f"Updated plant: {plant_id}")
        return jsonify({'message': 'Plant updated successfully'}), 200

    except Exception as e:
        logger.error(f"Failed to update plant: {e}")
        return jsonify({'error': str(e)}), 500

# User endpoints
@app.route('/users', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.json
        user_id = str(uuid.uuid4())
        username = data.get('username')
        display_name = data.get('display_name')
        telegram_id = data.get('telegram_id')
        email = data.get('email')
        
        query = """
            INSERT INTO users (id, username, display_name, telegram_id, email)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (user_id, username, display_name, telegram_id, email))
        
        if result:
            logger.info(f"Registered user: {username} with ID {user_id}")
            return jsonify({
                'id': user_id,
                'username': username,
                'display_name': display_name,
                'telegram_id': telegram_id,
                'email': email
            }), 201
        else:
            return jsonify({'error': 'Failed to register user'}), 500
            
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def list_users():
    """List all users"""
    try:
        query = "SELECT * FROM users ORDER BY created_at DESC"
        users = execute_query(query)
        
        # Convert RealDictRow objects to regular dictionaries
        users = convert_real_dict_rows(users)
        
        return jsonify(users)
        
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users/<user_id>/activate', methods=['POST'])
def activate_user(user_id):
    """Activate a user (placeholder for future functionality)"""
    try:
        # For now, just return success
        # In the future, you might want to add an 'active' field to users table
        logger.info(f"User activation requested for: {user_id}")
        return jsonify({'message': 'User activated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Failed to activate user: {e}")
        return jsonify({'error': str(e)}), 500

# User-Plant assignment endpoints
@app.route('/user_plants', methods=['POST'])
def assign_user_to_plant():
    """Explicitly assign a plant to a user"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        plant_id = data.get('plant_id')
        if not user_id or not plant_id:
            return jsonify({'error': 'user_id and plant_id are required'}), 400

        # Ensure both exist
        user_exists = execute_query("SELECT 1 FROM users WHERE id = %s", (user_id,))
        plant_exists = execute_query("SELECT 1 FROM plants WHERE id = %s AND active = TRUE", (plant_id,))
        if not user_exists:
            return jsonify({'error': 'User not found'}), 404
        if not plant_exists:
            return jsonify({'error': 'Plant not found or inactive'}), 404

        # One owner per plant: drop existing then insert
        execute_query("DELETE FROM user_plants WHERE plant_id = %s", (plant_id,))
        execute_query("""
            INSERT INTO user_plants (user_id, plant_id, assigned_at)
            VALUES (%s, %s, NOW())
        """, (user_id, plant_id))

        # Ensure a per-user device exists for this plant
        try:
            # Build a friendly device name
            plant_row = execute_query("SELECT name, species FROM plants WHERE id = %s", (plant_id,))
            plant_name = plant_row[0]['name'] if plant_row else 'Plant'
            plant_species = plant_row[0].get('species') if plant_row else None
            device_name = f"{plant_name} sensor"
            device_type = 'sensor'
            device_config = json.dumps({
                'plant_id': plant_id,
                'plant_species': plant_species,
                'capabilities': ['temperature', 'humidity', 'soil_moisture']
            })

            # Upsert-like behavior: if a device with same user_id and plant_id exists, skip
            exists = execute_query(
                "SELECT id FROM devices WHERE user_id = %s AND plant_id = %s",
                (user_id, plant_id)
            )
            if not exists:
                execute_query(
                    """
                    INSERT INTO devices (name, type, config, user_id, plant_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (device_name, device_type, device_config, user_id, plant_id)
                )
        except Exception as e:
            logger.warning(f"Failed to create per-user device for plant {plant_id}: {e}")

        # Publish MQTT assignment notification
        try:
            import paho.mqtt.client as mqtt
            import time
            
            # Get plant and user details for notification
            plant_details = execute_query("SELECT name, species FROM plants WHERE id = %s", (plant_id,))
            user_details = execute_query("SELECT username, telegram_id FROM users WHERE id = %s", (user_id,))
            
            if plant_details and user_details:
                plant_name = plant_details[0]['name']
                user_telegram_id = user_details[0].get('telegram_id')
                
                assignment_msg = {
                    "type": "plant_assigned",
                    "plant_id": plant_id,
                    "user_id": user_id,
                    "plant_name": plant_name,
                    "telegram_id": user_telegram_id,
                    "timestamp": time.time()
                }
                
                # Publish to MQTT
                client = mqtt.Client()
                client.connect("mqtt-broker", 1883, 60)
                client.publish("plant/assignments", json.dumps(assignment_msg))
                client.disconnect()
                
                logger.info(f"Published assignment notification for plant {plant_id} to user {user_id}")
        except Exception as e:
            logger.warning(f"Could not publish MQTT assignment notification: {e}")

        return jsonify({'message': 'Assigned', 'plant_id': plant_id, 'user_id': user_id}), 201
    except Exception as e:
        logger.error(f"Assignment failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/user_plants/<plant_id>', methods=['DELETE'])
def unassign_plant(plant_id):
    """Remove any assignment for a plant"""
    try:
        execute_query("DELETE FROM user_plants WHERE plant_id = %s", (plant_id,))
        return '', 204
    except Exception as e:
        logger.error(f"Unassign failed: {e}")
        return jsonify({'error': str(e)}), 500

# Health check endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    try:
        # Test database connection
        if not test_connection():
            return jsonify({
                'status': 'unhealthy',
                'error': 'Database connection failed'
            }), 500
        
        # Get counts
        counts = {}
        
        # Plant count
        plant_result = execute_query("SELECT COUNT(*) as count FROM plants WHERE active = TRUE")
        plant_result = convert_real_dict_rows(plant_result)
        counts['plants'] = plant_result[0]['count'] if plant_result else 0
        
        # User count
        user_result = execute_query("SELECT COUNT(*) as count FROM users")
        user_result = convert_real_dict_rows(user_result)
        counts['users'] = user_result[0]['count'] if user_result else 0
        
        # Device count
        device_result = execute_query("SELECT COUNT(*) as count FROM devices WHERE active = TRUE")
        device_result = convert_real_dict_rows(device_result)
        counts['devices'] = device_result[0]['count'] if device_result else 0
        
        # Service count
        service_result = execute_query("SELECT COUNT(*) as count FROM services WHERE active = TRUE")
        service_result = convert_real_dict_rows(service_result)
        counts['services'] = service_result[0]['count'] if service_result else 0
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'counts': counts
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Web form routes (keeping existing functionality)
@app.route('/register_plant', methods=['GET', 'POST'])
def register_plant_form():
    """Plant registration form"""
    if request.method == 'POST':
        # Handle form submission
        name = request.form.get('name')
        species = request.form.get('species')
        location = request.form.get('location')
        
        if name:
            try:
                plant_data = {
                    'name': name,
                    'species': species,
                    'location': location,
                    'thresholds': {
                        'temperature': {'min': 18, 'max': 30},
                        'humidity': {'min': 40, 'max': 80},
                        'soil_moisture': {'min': 300, 'max': 800}
                    }
                }
                
                response = register_plant()
                if response[1] == 201:
                    return "Plant registered successfully!"
                else:
                    return "Failed to register plant"
            except Exception as e:
                return f"Error: {str(e)}"
    
    # GET request - show form
    form_html = '''
    <h2>Register New Plant</h2>
    <form method="POST">
        <label>Name: <input type="text" name="name" required></label><br>
        <label>Species: <input type="text" name="species"></label><br>
        <label>Location: <input type="text" name="location"></label><br>
        <input type="submit" value="Register Plant">
    </form>
    '''
    return form_html

@app.route('/register_user', methods=['GET', 'POST'])
def register_user_form():
    """User registration form"""
    if request.method == 'POST':
        # Handle form submission
        username = request.form.get('username')
        display_name = request.form.get('display_name')
        
        if username:
            try:
                user_data = {
                    'username': username,
                    'display_name': display_name
                }
                
                response = register_user()
                if response[1] == 201:
                    return "User registered successfully!"
                else:
                    return "Failed to register user"
            except Exception as e:
                return f"Error: {str(e)}"
    
    # GET request - show form
    form_html = '''
    <h2>Register New User</h2>
    <form method="POST">
        <label>Username: <input type="text" name="username" required></label><br>
        <label>Display Name: <input type="text" name="display_name"></label><br>
        <input type="submit" value="Register User">
    </form>
    '''
    return form_html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
