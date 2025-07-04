smart-plant-care-system/arezou_test/test_catalogue.py
import requests
import json

BASE_URL = "http://localhost:5000"  # Adjust if running on a remote Pi

# Test device registration
device = {
    "name": "dht11_test",
    "type": "temp_humidity",
    "location": "test_lab",
    "pin": 4
}

r = requests.post(f"{BASE_URL}/register/device", json=device)
print("Register Device:", r.status_code, r.json())

# Test service registration
service = {
    "name": "test_mqtt_temp",
    "protocol": "MQTT",
    "topic": "test/temperature"
}

r = requests.post(f"{BASE_URL}/register/service", json=service)
print("Register Service:", r.status_code, r.json())

# Fetch the registered device
r = requests.get(f"{BASE_URL}/device/dht11_test")
print("Get Device:", r.status_code, r.json())

# Fetch all devices
r = requests.get(f"{BASE_URL}/devices")
print("All Devices:", r.status_code, r.json())

# Check if catalogue is alive
r = requests.get(f"{BASE_URL}/status")
print("Status:", r.status_code, r.json())
