import json
import requests

# Import the plants from the home_plants_database.json file
PLANTS_FILE = 'home_plants_database.json'
API_URL = 'http://localhost:5000/plants'

with open(PLANTS_FILE, 'r', encoding='utf-8') as f:
    plants = json.load(f)

for idx, plant in enumerate(plants, 1):
    payload = {
        'name': plant.get('display_name', plant.get('species', f'Plant {idx}')),
        'species': plant.get('species', f'Unknown Species {idx}'),
        'thresholds': json.dumps(plant.get('default_thresholds', {})),
        'location': 'Default',
        'user_id': None  # You can set this to a real user_id if needed
    }
    try:
        resp = requests.post(API_URL, json=payload)
        if resp.status_code == 201:
            print(f"Imported: {payload['name']}")
        else:
            print(f"Failed to import {payload['name']}: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Error importing {payload['name']}: {e}") 