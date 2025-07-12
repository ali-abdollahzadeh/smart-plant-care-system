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

@app.route('/register_plant', methods=['GET', 'POST'])
def register_plant_form():
    # Load plant types from home_plants_database.json
    with open(os.path.join(os.path.dirname(__file__), 'home_plants_database.json'), 'r') as f:
        plant_types = json.load(f)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = [dict(row) for row in c.fetchall()]
    c.execute('SELECT * FROM plants')
    plants = [dict(row) for row in c.fetchall()]
    conn.close()
    user_map = {u['id']: u for u in users}
    # Map user_id to list of plants
    user_plants = {}
    for p in plants:
        if p['user_id']:
            user_plants.setdefault(p['user_id'], []).append(p)
    if request.method == 'POST':
        plant_type_idx = int(request.form.get('plant_type_idx'))
        plant_type = plant_types[plant_type_idx]
        name = plant_type['display_name']
        species = plant_type['species']
        location = request.form.get('location')
        user_id = request.form.get('user_id')
        thresholds = plant_type['default_thresholds']
        care_info = plant_type['care_info']
        plant_id = str(uuid.uuid4())
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO plants (id, name, species, location, thresholds, care_info, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (plant_id, name, species, location, str(thresholds), str(care_info), user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('register_plant_success'))
    # Render form and user-plant table
    return render_template_string('''
        <h2>Register a New Plant</h2>
        <form method="post" id="plantForm">
            <label>Plant Type:
                <select name="plant_type_idx" id="plant_type_idx" required onchange="fillDetails()">
                    <option value="">Select a plant type</option>
                    {% for pt in plant_types %}
                        <option value="{{loop.index0}}">{{pt['display_name']}}</option>
                    {% endfor %}
                </select>
            </label><br>
            <label>Location: <input name="location" required></label><br>
            <label>User:
                <select name="user_id" required>
                    <option value="">Select a user</option>
                    {% for user in users %}
                        <option value="{{user['id']}}">{{user['display_name'] or user['username']}}</option>
                    {% endfor %}
                </select>
            </label><br>
            <div id="details"></div>
            <button type="submit">Register Plant</button>
        </form>
        <p><a href="/register_user">Register a new user</a></p>
        <h3>Users and Their Plants</h3>
        <table border="1" cellpadding="4">
            <tr><th>User</th><th>Plant Name</th><th>Species</th><th>Location</th></tr>
            {% for user in users %}
                {% set plants = user_plants.get(user['id'], []) %}
                {% if plants %}
                    {% for plant in plants %}
                        <tr>
                            <td>{{user['display_name'] or user['username']}}</td>
                            <td>{{plant['name']}}</td>
                            <td>{{plant['species']}}</td>
                            <td>{{plant['location']}}</td>
                        </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td>{{user['display_name'] or user['username']}}</td>
                        <td colspan="3"><i>No plants assigned</i></td>
                    </tr>
                {% endif %}
            {% endfor %}
        </table>
        <script>
        const plantTypes = {{ plant_types|tojson }};
        function fillDetails() {
            const idx = document.getElementById('plant_type_idx').value;
            let html = '';
            if (idx !== '') {
                const pt = plantTypes[idx];
                html += `<b>Species:</b> ${pt.species}<br>`;
                html += `<b>Temperature:</b> ${pt.default_thresholds.temperature.min}–${pt.default_thresholds.temperature.max} °C<br>`;
                html += `<b>Humidity:</b> ${pt.default_thresholds.humidity.min}–${pt.default_thresholds.humidity.max} %<br>`;
                html += `<b>Soil Moisture:</b> ${pt.default_thresholds.soil_moisture.min}–${pt.default_thresholds.soil_moisture.max}<br>`;
                html += `<b>Watering:</b> ${pt.care_info.watering_frequency}<br>`;
                html += `<b>Light:</b> ${pt.care_info.light}<br>`;
                html += `<b>Notes:</b> ${pt.care_info.notes}<br>`;
            }
            document.getElementById('details').innerHTML = html;
        }
        </script>
    ''', plant_types=plant_types, users=users, user_plants=user_plants)

@app.route('/register_user', methods=['GET', 'POST'])
def register_user_form():
    if request.method == 'POST':
        username = request.form.get('username')
        display_name = request.form.get('display_name')
        user_id = str(uuid.uuid4())
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO users (id, username, display_name) VALUES (?, ?, ?)',
                  (user_id, username, display_name))
        conn.commit()
        conn.close()
        return redirect(url_for('register_user_success'))
    return render_template_string('''
        <h2>Register a New User</h2>
        <form method="post">
            <label>Username: <input name="username" required></label><br>
            <label>Display Name: <input name="display_name"></label><br>
            <button type="submit">Register User</button>
        </form>
    ''')

@app.route('/register_user_success')
def register_user_success():
    return '<h3>User registered successfully!</h3><a href="/register_user">Register another</a> | <a href="/register_plant">Register a plant</a>'

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
