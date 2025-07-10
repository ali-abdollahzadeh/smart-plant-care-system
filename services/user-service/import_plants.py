import os
import json
import db

print("[IMPORT] Before import os")
import os
print("[IMPORT] After import os")
print("[IMPORT] Before import json")
import json
print("[IMPORT] After import json")
print("[IMPORT] Before import db")
import db
print("[IMPORT] After import db")

print("[IMPORT] Script started.")
print(f"[IMPORT] Current working directory: {os.getcwd()}")

try:
    db.ensure_db()  # Ensure tables exist
    print(f"[IMPORT] Using database file: {os.path.abspath(db.DB_PATH)}")

    # Path to the plant JSON file
    PLANT_JSON = os.path.join(os.path.dirname(__file__), '../catalogue-service/home_plants_database.json')
    print(f"[IMPORT] Plant JSON path: {os.path.abspath(PLANT_JSON)}")

    # Get or create a default user
    users = []
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM users')
        users = c.fetchall()
    print(f"[IMPORT] Found users: {users}")
    if users:
        user_id = users[0][0]
    else:
        user_id = db.add_user('default_telegram_id', 'Default User')
        print(f"[IMPORT] Created default user with id: {user_id}")

    # Load plants from JSON
    with open(PLANT_JSON, 'r') as f:
        plants = json.load(f)
    print(f"[IMPORT] Loaded {len(plants)} plants from JSON.")

    for i, plant in enumerate(plants):
        name = plant.get('display_name')
        type_ = plant.get('species')
        thresholds = json.dumps(plant.get('default_thresholds', {}))
        species = plant.get('species')
        location = 'Imported'
        db.add_plant(name, type_, thresholds, species, location, user_id)
        print(f"[IMPORT] Inserted plant {i+1}: {name}")

    print(f"Imported {len(plants)} plants to user_id {user_id}.")
except Exception as e:
    print(f"[IMPORT ERROR] {e}") 