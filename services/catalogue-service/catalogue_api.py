from flask import Flask, request, jsonify, abort, render_template_string, redirect, url_for
import uuid
import sqlite3
import os
import json

app = Flask(__name__)
DB_PATH = os.environ.get("CATALOGUE_DB_PATH", "/app/data/catalogue_data.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the local SQLite database
def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        config TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        config TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT,
        display_name TEXT,
        active INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS plants (
        id TEXT PRIMARY KEY,
        name TEXT,
        species TEXT,
        location TEXT,
        thresholds TEXT,
        care_info TEXT,
        user_id TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Auto import plants if the database is empty
def auto_import_plants_if_empty():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM plants')
    count = c.fetchone()[0]
    if count == 0:
        json_path = os.path.join(os.path.dirname(__file__), 'home_plants_database.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            plant_types = json.load(f)
        for pt in plant_types:
            name = pt.get('display_name', pt.get('species', 'Unknown'))
            species = pt.get('species', 'Unknown')
            location = 'Default'
            thresholds = json.dumps(pt.get('default_thresholds', {}))
            care_info = json.dumps(pt.get('care_info', {}))
            plant_id = str(uuid.uuid4())
            c.execute('INSERT INTO plants (id, name, species, location, thresholds, care_info, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (plant_id, name, species, location, thresholds, care_info, None))
        conn.commit()
    conn.close()

auto_import_plants_if_empty()

@app.route('/devices', methods=['POST'])
def register_device():
    data = request.json
    device_id = str(uuid.uuid4())
    name = data.get('name')
    type_ = data.get('type')
    config = str(data.get('config', {}))
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO devices (id, name, type, config) VALUES (?, ?, ?, ?)',
              (device_id, name, type_, config))
    conn.commit()
    conn.close()
    return jsonify({'id': device_id, 'name': name, 'type': type_, 'config': config}), 201

@app.route('/devices', methods=['GET'])
def list_devices():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM devices')
    devices = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(devices)

@app.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM devices WHERE id=?', (device_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)
    return jsonify(dict(row))

@app.route('/services', methods=['POST'])
def register_service():
    data = request.json
    service_id = str(uuid.uuid4())
    name = data.get('name')
    type_ = data.get('type')
    config = str(data.get('config', {}))
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO services (id, name, type, config) VALUES (?, ?, ?, ?)',
              (service_id, name, type_, config))
    conn.commit()
    conn.close()
    return jsonify({'id': service_id, 'name': name, 'type': type_, 'config': config}), 201

@app.route('/services', methods=['GET'])
def list_services():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM services')
    services = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(services)

@app.route('/services/<service_id>', methods=['GET'])
def get_service(service_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM services WHERE id=?', (service_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)
    return jsonify(dict(row))

@app.route('/plants', methods=['POST'])
def register_plant():
    data = request.json
    plant_id = str(uuid.uuid4())
    name = data.get('name')
    species = data.get('species')
    location = data.get('location')
    thresholds = str(data.get('thresholds', {}))
    care_info = str(data.get('care_info', {}))
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO plants (id, name, species, location, thresholds, care_info) VALUES (?, ?, ?, ?, ?, ?)',
              (plant_id, name, species, location, thresholds, care_info))
    conn.commit()
    conn.close()
    return jsonify({'id': plant_id, 'name': name, 'species': species, 'location': location, 'thresholds': thresholds, 'care_info': care_info}), 201

@app.route('/plants', methods=['GET'])
def list_plants():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM plants')
    plants = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(plants)

@app.route('/plants/<plant_id>', methods=['GET'])
def get_plant(plant_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM plants WHERE id=?', (plant_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)
    return jsonify(dict(row))

@app.route('/plants/<plant_id>', methods=['PATCH'])
def update_plant(plant_id):
    data = request.json
    fields = []
    values = []
    if 'user_id' in data:
        fields.append('user_id = ?')
        values.append(data['user_id'])
    # Optionally allow updating other fields
    for field in ['name', 'species', 'location', 'thresholds', 'care_info']:
        if field in data:
            fields.append(f'{field} = ?')
            values.append(data[field])
    if not fields:
        return jsonify({'error': 'No valid fields to update'}), 400
    values.append(plant_id)
    conn = get_db()
    c = conn.cursor()
    c.execute(f'UPDATE plants SET {", ".join(fields)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'plant_id': plant_id}), 200

@app.route('/users', methods=['POST'])
def register_user():
    data = request.json
    user_id = str(uuid.uuid4())
    username = data.get('username')
    display_name = data.get('display_name')
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO users (id, username, display_name) VALUES (?, ?, ?)',
              (user_id, username, display_name))
    conn.commit()
    conn.close()
    return jsonify({'id': user_id, 'username': username, 'display_name': display_name}), 201

@app.route('/users', methods=['GET'])
def list_users():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/users/<user_id>/activate', methods=['POST'])
def activate_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET active=1 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'user_id': user_id})

@app.route('/plants/active', methods=['GET'])
def list_active_plants():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT plants.* FROM plants JOIN users ON plants.user_id = users.id WHERE users.active=1''')
    plants = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(plants)

@app.route('/plant_types', methods=['GET'])
def get_plant_types():
    """Get available plant types from the database"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'home_plants_database.json'), 'r') as f:
            plant_types = json.load(f)
        return jsonify(plant_types)
    except Exception as e:
        logging.error(f"Error loading plant types: {e}")
        return jsonify([])

@app.route('/register_plant', methods=['GET', 'POST'])
def register_plant_form():
    """Redirect to dashboard for plant registration"""
    return redirect('http://localhost:5500/register_plant_advanced')

@app.route('/register_user', methods=['GET', 'POST'])
def register_user_form():
    """Redirect to dashboard for user registration"""
    return redirect('http://localhost:5500/register_user')

@app.route('/register_user_success')
def register_user_success():
    """Redirect to dashboard success page"""
    return redirect('http://localhost:5500/register_user')

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    try:
        # Test database connection
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM plants')
        plant_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM devices')
        device_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM services')
        service_count = c.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'counts': {
                'plants': plant_count,
                'users': user_count,
                'devices': device_count,
                'services': service_count
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
