from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Path to config file
CATALOGUE_FILE = os.path.join(os.path.dirname(__file__), '../config/plants.json')

# Load catalogue from file
def load_catalogue():
    if os.path.exists(CATALOGUE_FILE):
        with open(CATALOGUE_FILE, 'r') as f:
            return json.load(f)
    else:
        return {"devices": [], "services": []}

# Save catalogue to file
def save_catalogue(data):
    with open(CATALOGUE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ---------------------------
#         ROUTES
# ---------------------------

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Catalogue Service is running ✅"})

@app.route('/register/device', methods=['POST'])
def register_device():
    new_device = request.json
    catalogue = load_catalogue()
    catalogue['devices'].append(new_device)
    save_catalogue(catalogue)
    return jsonify({"message": "Device registered successfully!"}), 201

@app.route('/register/service', methods=['POST'])
def register_service():
    new_service = request.json
    catalogue = load_catalogue()
    catalogue['services'].append(new_service)
    save_catalogue(catalogue)
    return jsonify({"message": "Service registered successfully!"}), 201

@app.route('/device/<name>', methods=['GET'])
def get_device(name):
    catalogue = load_catalogue()
    for d in catalogue['devices']:
        if d['name'] == name:
            return jsonify(d)
    return jsonify({"error": "Device not found"}), 404

@app.route('/service/<name>', methods=['GET'])
def get_service(name):
    catalogue = load_catalogue()
    for s in catalogue['services']:
        if s['name'] == name:
            return jsonify(s)
    return jsonify({"error": "Service not found"}), 404

@app.route('/devices', methods=['GET'])
def get_all_devices():
    return jsonify(load_catalogue().get("devices", []))

@app.route('/services', methods=['GET'])
def get_all_services():
    return jsonify(load_catalogue().get("services", []))

@app.route('/all', methods=['GET'])
def get_all():
    return jsonify(load_catalogue())

# ---------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
