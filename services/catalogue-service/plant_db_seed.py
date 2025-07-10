import requests

PLANTS = [
    {
        "name": "Aloe Vera",
        "species": "Aloe vera",
        "location": "Living Room Window",
        "thresholds": {
            "temperature": {"min": 15, "max": 30},
            "humidity": {"min": 20, "max": 60},
            "soil_moisture": {"min": 300, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Every 2-3 weeks",
            "light": "Bright, indirect sunlight",
            "notes": "Allow soil to dry between waterings."
        }
    },
    {
        "name": "Snake Plant",
        "species": "Sansevieria trifasciata",
        "location": "Bedroom Corner",
        "thresholds": {
            "temperature": {"min": 13, "max": 29},
            "humidity": {"min": 30, "max": 50},
            "soil_moisture": {"min": 250, "max": 600}
        },
        "care_info": {
            "watering_frequency": "Every 2-6 weeks",
            "light": "Low to bright, indirect light",
            "notes": "Tolerates low light and infrequent watering."
        }
    },
    {
        "name": "Peace Lily",
        "species": "Spathiphyllum",
        "location": "Office Desk",
        "thresholds": {
            "temperature": {"min": 18, "max": 27},
            "humidity": {"min": 40, "max": 70},
            "soil_moisture": {"min": 400, "max": 800}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Low to medium, indirect light",
            "notes": "Keep soil consistently moist but not soggy."
        }
    },
    {
        "name": "Spider Plant",
        "species": "Chlorophytum comosum",
        "location": "Kitchen Shelf",
        "thresholds": {
            "temperature": {"min": 13, "max": 27},
            "humidity": {"min": 35, "max": 60},
            "soil_moisture": {"min": 350, "max": 750}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Allow top inch of soil to dry out between waterings."
        }
    }
]

CATALOGUE_URL = "http://localhost:5000/plants"

def seed_plants():
    for plant in PLANTS:
        resp = requests.post(CATALOGUE_URL, json=plant)
        if resp.status_code == 201:
            print(f"Added: {plant['name']} ({plant['species']}) at {plant['location']}")
        else:
            print(f"Failed to add {plant['name']}: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    seed_plants() 