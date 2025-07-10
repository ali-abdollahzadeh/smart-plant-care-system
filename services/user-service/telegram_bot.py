"""
Telegram Bot for Smart Plant System

Commands:
- /status: Get latest plant data
- /recommend: Get care recommendations
- /water: Start watering (actuator control)
- /led_on: Turn LED ON (actuator control)
- /led_off: Turn LED OFF (actuator control)
- /actuator_status: Get current actuator state

Actuator commands interact with the sensor service REST API (port 5500).
"""
import logging
import requests
import os
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, request, jsonify
import threading
import time
import db
from telegram.error import BadRequest
from db import add_user, get_user_by_telegram_id, get_plants_for_user, get_all_plants

CONFIG_PATH = os.environ.get("CONFIG_PATH", "../shared/config/global_config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

bot_token = config['telegram']['bot_token']
rest_api_url = os.environ.get('REST_API_URL', 'http://cloud-adapter-service:5001/data?results=1')
SENSOR_API_URL = os.environ.get('SENSOR_API_URL', 'http://sensor-service:5002/actuator')
CATALOGUE_API_URL = os.environ.get('CATALOGUE_API_URL', 'http://catalogue-service:5000')

# Helper: get or create user in catalogue for a Telegram chat_id
def get_or_create_user(chat_id, username=None, display_name=None):
    # Use Telegram username for lookup/creation
    lookup_username = username or str(chat_id)
    try:
        resp = requests.get(f"{CATALOGUE_API_URL}/users")
        users = resp.json()
        for user in users:
            if user.get('username') == lookup_username:
                return user['id']
    except Exception:
        pass
    # If not found, create user in catalogue-service
    payload = {
        'username': lookup_username,
        'display_name': display_name or lookup_username
    }
    try:
        resp = requests.post(f"{CATALOGUE_API_URL}/users", json=payload)
        if resp.status_code == 201:
            user = resp.json()
            return user['id']
    except Exception:
        pass
    return None

def get_user_id_for_chat(chat_id, username=None, display_name=None):
    return get_or_create_user(chat_id, username, display_name)

def register_plant_for_user(user_id, name, type_, thresholds, species=None, location=None):
    plant_id = db.add_plant(name, type_, thresholds, species, location, user_id)
    # Notify user via Telegram
    telegram_user_id = get_telegram_user_id_for_db_user(user_id)
    if telegram_user_id:
        import asyncio
        from telegram.ext import ApplicationBuilder
        app = ApplicationBuilder().token(bot_token).build()
        async def send_plant_registered():
            try:
                await app.bot.send_message(chat_id=telegram_user_id, text=f"🌱 A new plant '{name}' has been registered for you!")
            except Exception as e:
                logging.error(f"Failed to notify user {telegram_user_id} about new plant: {e}")
        asyncio.run(send_plant_registered())
    return plant_id

logging.basicConfig(level=logging.INFO)
user_chat_ids = set()

app = Flask(__name__)

# Mapping: telegram_user_id -> plant_id
user_plant_assignments = {}
# Mapping: (telegram_user_id, plant_id) -> last_data
last_sent_data = {}

# Add at the top of the file
last_plant_detail_msg = {}
plant_last_status = {}  # (plant_id) -> last_status_str

# Function to poll data and push updates
# Ensure 'application' is a global instance
application = ApplicationBuilder().token(bot_token).build()

def poll_and_push_sensor_data():
    logging.info("[NOTIFY] poll_and_push_sensor_data thread started")
    while True:
        logging.info(f"[NOTIFY] user_plant_assignments: {user_plant_assignments}")
        for telegram_user_id, plant_id in list(user_plant_assignments.items()):
            try:
                resp = requests.get(f"{SENSOR_API_URL.replace('/actuator','/data')}?plant_id={plant_id}", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    key = (telegram_user_id, plant_id)
                    # --- Status change notification logic ---
                    plant, _ = get_plant_detail(plant_id)
                    status_str = get_plant_status(plant, data)
                    last_status = plant_last_status.get(plant_id)
                    def is_problem(status):
                        return status and 'Problem' in status
                    if last_status != status_str:
                        logging.info(f"[NOTIFY] Status change detected for plant_id={plant_id}, user={telegram_user_id}: '{last_status}' -> '{status_str}'")
                        plant_last_status[plant_id] = status_str
                        if last_status is not None:
                            if is_problem(status_str) and not is_problem(last_status):
                                logging.info(f"[NOTIFY] Sending warning to user {telegram_user_id} for plant '{plant.get('name','')}' with status: {status_str}")
                                import asyncio
                                try:
                                    logging.info(f"[NOTIFY] About to send WARNING message to user {telegram_user_id}")
                                    asyncio.run(application.bot.send_message(chat_id=telegram_user_id, text=f"⚠️ Warning for your plant '{plant.get('name','')}': {status_str}"))
                                    logging.info(f"[NOTIFY] Warning message sent to user {telegram_user_id}")
                                except Exception as e:
                                    logging.error(f"[NOTIFY] Failed to send warning to user {telegram_user_id}: {e}")
                            elif not is_problem(status_str) and is_problem(last_status):
                                logging.info(f"[NOTIFY] Sending OK to user {telegram_user_id} for plant '{plant.get('name','')}'")
                                import asyncio
                                try:
                                    logging.info(f"[NOTIFY] About to send OK message to user {telegram_user_id}")
                                    asyncio.run(application.bot.send_message(chat_id=telegram_user_id, text=f"✅ All clear for your plant '{plant.get('name','')}'. Status: OK"))
                                    logging.info(f"[NOTIFY] OK message sent to user {telegram_user_id}")
                                except Exception as e:
                                    logging.error(f"[NOTIFY] Failed to send OK to user {telegram_user_id}: {e}")
                    # --- End status change notification logic ---
                    # Always send sensor data every 10 seconds
                    text = f"🌱 Plant {plant_id} update:\n" + "\n".join(f"{k}: {v}" for k, v in data.items())
                    try:
                        logging.info(f"[NOTIFY] About to send SENSOR DATA to user {telegram_user_id} for plant {plant_id}")
                        application.bot.send_message(chat_id=telegram_user_id, text=text)
                        logging.info(f"[NOTIFY] Sensor data message sent to user {telegram_user_id}")
                    except Exception as e:
                        logging.error(f"[NOTIFY] Failed to send sensor data to user {telegram_user_id}: {e}")
            except Exception as e:
                logging.error(f"[NOTIFY] Error polling/sending data for user {telegram_user_id}, plant {plant_id}: {e}")
        time.sleep(10)  # Poll every 10 seconds

# Auto-populate user_plant_assignments from DB on startup
def load_user_plant_assignments():
    import db as userdb
    with userdb.get_connection() as conn:
        c = conn.cursor()
        # Get all users with their telegram_id
        c.execute('SELECT id, telegram_id FROM users')
        users = {str(row[0]): row[1] for row in c.fetchall() if row[1]}
        # Get all plants with user assignments
        c.execute('SELECT id, user_id FROM plants WHERE user_id IS NOT NULL')
        for plant_id, user_id in c.fetchall():
            user_id_str = str(user_id)
            if user_id_str in users:
                telegram_id = users[user_id_str]
                try:
                    user_plant_assignments[int(telegram_id)] = plant_id
                except Exception:
                    logging.warning(f"[NOTIFY] Skipping user_id={user_id} with invalid telegram_id={telegram_id}")
    logging.info(f"[NOTIFY] Loaded user_plant_assignments from DB: {user_plant_assignments}")

# Call this before starting the polling thread
load_user_plant_assignments()

# Start polling thread at startup (ensure this is at the top level, not inside any function)
threading.Thread(target=poll_and_push_sensor_data, daemon=True).start()

# When a plant is assigned to a user, update user_plant_assignments
# Example: in your assignment handler or after assignment API call
# user_plant_assignments[telegram_user_id] = plant_id

def notify_user(message):
    import asyncio
    from telegram.ext import ApplicationBuilder
    app = ApplicationBuilder().token(bot_token).build()
    async def send_all():
        for chat_id in user_chat_ids:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logging.error(f"Failed to notify user {chat_id}: {e}")
    asyncio.run(send_all())

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    plant_name = data.get('plant_name')
    location = data.get('location')
    problem = data.get('problem')
    message = f"⚠️ {plant_name} at {location}: {problem}"
    threading.Thread(target=notify_user, args=(message,)).start()
    return jsonify({'status': 'ok'})

@app.route('/register_plant', methods=['GET', 'POST'])
def register_plant_web():
    import ast
    users = []
    # Fetch users from DB
    import db as userdb
    with userdb.get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, telegram_id FROM users')
        users = c.fetchall()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        name = request.form.get('name')
        type_ = request.form.get('type')
        species = request.form.get('species')
        location = request.form.get('location')
        thresholds = request.form.get('thresholds')
        # Accept thresholds as a Python dict string or JSON
        try:
            thresholds_dict = ast.literal_eval(thresholds)
        except Exception:
            import json
            thresholds_dict = json.loads(thresholds)
        register_plant_for_user(user_id, name, type_, str(thresholds_dict), species, location)
        return '<h3>Plant registered successfully!</h3><a href="/register_plant">Register another</a>'
    # Render form
    return '''
        <h2>Register a New Plant</h2>
        <form method="post">
            <label>User:
                <select name="user_id" required>
                    <option value="">Select a user</option>
                    {users}
                </select>
            </label><br>
            <label>Plant Name: <input name="name" required></label><br>
            <label>Type: <input name="type"></label><br>
            <label>Species: <input name="species"></label><br>
            <label>Location: <input name="location"></label><br>
            <label>Thresholds (Python dict or JSON): <input name="thresholds" value="{{'temperature': {'min': 18, 'max': 30}, 'humidity': {'min': 40, 'max': 80}, 'soil_moisture': {'min': 350, 'max': 750}}}" required size="80"></label><br>
            <button type="submit">Register Plant</button>
        </form>
    '''.replace('{users}', '\n'.join([f'<option value="{u[0]}">{u[1] or u[2]}</option>' for u in users]))

@app.route('/assign_plant', methods=['GET', 'POST'])
def assign_plant():
    # Fetch users from catalogue-service
    try:
        users_resp = requests.get(f"{CATALOGUE_API_URL}/users")
        users = users_resp.json()
    except Exception as e:
        users = []
    # Fetch plants from catalogue-service
    try:
        resp = requests.get(f"{CATALOGUE_API_URL}/plants")
        plants = resp.json()
    except Exception as e:
        plants = []
    msg = ''
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        plant_id = request.form.get('plant_id')
        # Assign plant by updating user_id in catalogue-service
        try:
            update_resp = requests.patch(f"{CATALOGUE_API_URL}/plants/{plant_id}", json={"user_id": user_id})
            if update_resp.status_code == 200:
                msg = '<p style="color:green">Plant assigned successfully!</p>'
                # If you have a mapping from DB user_id to Telegram user_id, use it here:
                telegram_user_id = get_telegram_user_id_for_db_user(user_id)  # You must implement this lookup
                if telegram_user_id:
                    user_plant_assignments[telegram_user_id] = plant_id
                    logging.info(f"[NOTIFY] Assigned plant {plant_id} to user {user_id} (telegram_user_id={telegram_user_id})")
            else:
                msg = f'<p style="color:red">Failed to assign plant: {update_resp.status_code} {update_resp.text}</p>'
        except Exception as e:
            msg = f'<p style="color:red">Error assigning plant: {e}</p>'
    # Map user_id to list of plants
    user_plants = {}
    for p in plants:
        if p.get('user_id'):
            user_plants.setdefault(p['user_id'], []).append(p)
    # Render form and user-plant table
    return f'''
        <h2>Assign Plant to User</h2>
        {msg}
        <form method="post">
            <label>User:
                <select name="user_id" required>
                    <option value="">Select a user</option>
                    {''.join([f'<option value="{u["id"]}">{u.get("display_name") or u.get("username")}</option>' for u in users])}
                </select>
            </label><br>
            <label>Plant:
                <select name="plant_id" required>
                    <option value="">Select a plant</option>
                    {''.join([f'<option value="{p["id"]}">{p["name"]} ({p["species"]}) - {p["location"]} [Assigned to: {p.get("user_id", "None")}]</option>' for p in plants])}
                </select>
            </label><br>
            <button type="submit">Assign Plant</button>
        </form>
        <h3>Users and Their Plants</h3>
        <table border="1" cellpadding="4">
            <tr><th>User</th><th>Plant Name</th><th>Species</th><th>Location</th></tr>
            {''.join([
                ''.join([
                    f'<tr><td>{u.get("display_name") or u.get("username")}</td><td>{p["name"]}</td><td>{p["species"]}</td><td>{p["location"]}</td></tr>'
                    for p in user_plants.get(u["id"], [])
                ]) or f'<tr><td>{u.get("display_name") or u.get("username")}</td><td colspan="3"><i>No plants assigned</i></td></tr>'
                for u in users
            ])}
        </table>
    '''

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_chat.id)
    name = update.effective_user.full_name or update.effective_user.username or telegram_id
    # Register user in DB if not exists
    user_row = get_user_by_telegram_id(telegram_id)
    if not user_row:
        user_id = add_user(telegram_id, name)
        logging.info(f"[NOTIFY] Registered new user: telegram_id={telegram_id}, name={name}, user_id={user_id}")
    else:
        user_id = user_row[0]
        logging.info(f"[NOTIFY] Existing user: telegram_id={telegram_id}, name={name}, user_id={user_id}")
    user_chat_ids.add(update.effective_chat.id)
    # Auto-assign a plant if user has none
    user_plants = get_plants_for_user(user_id)
    if not user_plants:
        all_plants = get_all_plants()
        for plant in all_plants:
            if not plant[6]:  # plant[6] is user_id
                # Assign this plant to the user
                from db import assign_plant_to_user
                assign_plant_to_user(user_id, plant[0])
                logging.info(f"[NOTIFY] Auto-assigned plant {plant[0]} to user {user_id} (telegram_id={telegram_id})")
                break
    # Ask user if they want to join
    join_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Join Smart Plant System")]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(
        "Welcome to Smart Plant Bot!\n\nWould you like to join and manage your plants?",
        reply_markup=join_keyboard
    )
    return

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Join Smart Plant System":
        user_id = get_or_create_user(update.effective_chat.id, update.effective_user.username, update.effective_user.full_name)
        await update.message.reply_text(
            "You have joined the Smart Plant System!\n\nIf you have plants assigned, they will appear below. If not, please wait for an admin to assign a plant to you.",
            reply_markup=None
        )
        await show_plant_grid(update, context)
    else:
        await update.message.reply_text("Send /start to begin.")

async def show_plant_grid(update, context):
    chat_id = update.effective_chat.id
    user_id = get_user_id_for_chat(chat_id, update.effective_user.username, update.effective_user.full_name)
    try:
        resp = requests.get(f"{CATALOGUE_API_URL}/plants")
        all_plants = resp.json()
        plants = [p for p in all_plants if p.get('user_id') == user_id]
    except Exception as e:
        logging.error(f"Failed to fetch plants from catalogue-service: {e}")
        plants = []
    if not plants:
        await update.message.reply_text("You have no plants assigned yet. Please wait for an admin to assign a plant to you.")
        return
    # Group plants by location
    locations = {}
    for p in plants:
        loc = p.get('location') or 'Default'
        locations.setdefault(loc, []).append({'id': p['id'], 'name': p['name'], 'species': p['species']})
    keyboard = []
    for loc, plist in locations.items():
        row = [InlineKeyboardButton(f"{p['name']} ({p['species']})", callback_data=f"plant_{p['id']}") for p in plist]
        keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if getattr(update, 'message', None):
        await update.message.reply_text("Select a plant by location:", reply_markup=reply_markup)
    elif getattr(update, 'callback_query', None):
        await update.callback_query.message.reply_text("Select a plant by location:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Select a plant by location:", reply_markup=reply_markup)

async def handle_plant_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plant_id = query.data.replace("plant_", "")
    await show_plant_detail(update, context, plant_id)

def get_plant_detail(plant_id):
    import time
    try:
        resp = requests.get(f"{CATALOGUE_API_URL}/plants/{plant_id}")
        try:
            plant = resp.json()
        except Exception as e:
            logging.error(f"Failed to decode plant detail JSON: {e}. Response: {resp.text}")
            plant = {}
    except Exception as e:
        logging.error(f"Failed to fetch plant detail: {e}")
        plant = {}
    # Fetch latest sensor data for this plant
    sensor_data = {"temperature": "-", "humidity": "-", "soil_moisture": "-", "lighting": "-"}
    try:
        base_url = rest_api_url.split('?')[0]
        url = f"{base_url}?plant_id={plant_id}"
        logging.info(f"Requesting sensor data from: {url}")
        data_resp = requests.get(url)
        logging.info(f"Sensor data response: {data_resp.status_code} {data_resp.text}")
        if data_resp.status_code == 200:
            data = data_resp.json()
            if isinstance(data, list) and data:
                data = data[-1]
            if isinstance(data, dict):
                sensor_data = {
                    "temperature": data.get("temperature") or data.get("field1", "-"),
                    "humidity": data.get("humidity") or data.get("field2", "-"),
                    "soil_moisture": data.get("soil_moisture") or data.get("field3", "-"),
                    "lighting": data.get("lighting", "-")
                }
        else:
            # Try to find a plant_id with data and auto-assign it
            logging.warning(f"No data for plant_id {plant_id}, searching for available plant with data...")
            all_data_resp = requests.get(base_url)
            if all_data_resp.status_code == 200:
                all_data = all_data_resp.json()
                if isinstance(all_data, list) and all_data:
                    # Try each plant_id until we find one with data
                    for entry in all_data:
                        alt_plant_id = entry.get("plant_id")
                        if not alt_plant_id:
                            continue
                        alt_url = f"{base_url}?plant_id={alt_plant_id}"
                        alt_resp = requests.get(alt_url)
                        if alt_resp.status_code == 200:
                            alt_data = alt_resp.json()
                            if isinstance(alt_data, dict):
                                sensor_data = {
                                    "temperature": alt_data.get("temperature") or alt_data.get("field1", "-"),
                                    "humidity": alt_data.get("humidity") or alt_data.get("field2", "-"),
                                    "soil_moisture": alt_data.get("soil_moisture") or alt_data.get("field3", "-"),
                                    "lighting": alt_data.get("lighting", "-")
                                }
                                # Optionally update the user's assigned plant in the catalogue-service
                                try:
                                    requests.patch(f"{CATALOGUE_API_URL}/plants/{alt_plant_id}", json={"user_id": plant.get("user_id")})
                                except Exception as e:
                                    logging.error(f"Failed to auto-assign plant: {e}")
                                break
    except Exception as e:
        logging.error(f"Failed to fetch sensor data: {e}")
    return plant, sensor_data

async def show_plant_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, plant_id):
    plant, sensor_data = get_plant_detail(plant_id)
    # Fetch actuator state for accurate watering/lighting
    try:
        actuator_resp = requests.get(f"{SENSOR_API_URL}?plant_id={plant_id}", timeout=5)
        if actuator_resp.status_code == 200:
            actuator_state = actuator_resp.json()
            watering_state = actuator_state.get("watering", False)
            lighting_state = actuator_state.get("led", False)
        else:
            watering_state = sensor_data.get("watering", False)
            lighting_state = sensor_data.get("lighting", "OFF") == "ON"
    except Exception as e:
        logging.error(f"Exception fetching actuator state for plant detail: {e}")
        watering_state = sensor_data.get("watering", False)
        lighting_state = sensor_data.get("lighting", "OFF") == "ON"
    msg = (
        f"🌱 <b>{plant['name']}</b> ({plant['species']})\n"
        f"Location: {plant['location']}\n"
        f"<b>Status:</b> {get_plant_status(plant, sensor_data)}\n"
        f"<b>Temperature:</b> {sensor_data['temperature']} °C\n"
        f"<b>Humidity:</b> {sensor_data['humidity']} %\n"
        f"<b>Soil Moisture:</b> {sensor_data['soil_moisture']}\n"
        f"<b>Lighting:</b> {'ON' if lighting_state else 'OFF'}\n"
        f"<b>Watering:</b> {'ON' if watering_state else 'OFF'}\n"
    )
    keyboard = [
        [InlineKeyboardButton("💡 Toggle Light", callback_data=f"toggle_light_{plant_id}"),
         InlineKeyboardButton("💧 Water", callback_data=f"water_{plant_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_grid")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Only update if content changed
    global last_plant_detail_msg
    if last_plant_detail_msg.get(plant_id) == msg:
        return
    last_plant_detail_msg[plant_id] = msg
    try:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass  # Ignore harmless error
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=reply_markup, parse_mode='HTML')
            print(f"Telegram editMessageText error: {e}")

def get_plant_status(plant, sensor_data):
    # Compare sensor_data to plant thresholds
    import ast
    try:
        thresholds = ast.literal_eval(plant.get('thresholds', '{}'))
    except Exception:
        thresholds = {}
    problems = []
    try:
        t = float(sensor_data['temperature'])
        if 'temperature' in thresholds and (t < thresholds['temperature']['min'] or t > thresholds['temperature']['max']):
            problems.append('Temperature')
    except Exception:
        pass
    try:
        h = float(sensor_data['humidity'])
        if 'humidity' in thresholds and (h < thresholds['humidity']['min'] or h > thresholds['humidity']['max']):
            problems.append('Humidity')
    except Exception:
        pass
    try:
        m = float(sensor_data['soil_moisture'])
        if 'soil_moisture' in thresholds and m < thresholds['soil_moisture']['min']:
            problems.append('Soil Moisture')
    except Exception:
        pass
    # Lighting logic (simulate for now)
    if sensor_data.get('lighting') == 'OFF':
        problems.append('Lighting')
    if not problems:
        return '✅ OK'
    return '⚠️ Problem: ' + ', '.join(problems)

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "back_to_grid":
        await show_plant_grid(update, context)
        return
    if data.startswith("toggle_light_"):
        plant_id = data.replace("toggle_light_", "")
        payload = {"action": "led", "value": "toggle", "plant_id": plant_id}
        logging.info(f"Sending actuator POST to {SENSOR_API_URL} with payload: {payload}")
        try:
            resp = requests.post(SENSOR_API_URL, json=payload, timeout=5)
            logging.info(f"Actuator response: {resp.status_code} {resp.text}")
            if resp.status_code != 200:
                await query.edit_message_text(f"Failed to toggle light: {resp.text}")
                return
        except Exception as e:
            logging.error(f"Exception sending actuator POST: {e}")
            await query.edit_message_text(f"Failed to toggle light: {e}")
            return
        await show_plant_detail(update, context, plant_id)
        return
    if data.startswith("water_"):
        plant_id = data.replace("water_", "")
        # Fetch current watering state from actuator endpoint
        try:
            actuator_resp = requests.get(f"{SENSOR_API_URL}?plant_id={plant_id}", timeout=5)
            if actuator_resp.status_code == 200:
                actuator_state = actuator_resp.json()
                current = actuator_state.get("watering", False)
            else:
                current = False
        except Exception as e:
            logging.error(f"Exception fetching current watering state from actuator: {e}")
            current = False
        new_value = not current
        payload = {"action": "water", "value": new_value, "plant_id": plant_id}
        logging.info(f"Sending actuator POST to {SENSOR_API_URL} with payload: {payload}")
        try:
            resp = requests.post(SENSOR_API_URL, json=payload, timeout=5)
            logging.info(f"Actuator response: {resp.status_code} {resp.text}")
            if resp.status_code != 200:
                await query.edit_message_text(f"Failed to water plant: {resp.text}")
                return
        except Exception as e:
            logging.error(f"Exception sending actuator POST: {e}")
            await query.edit_message_text(f"Failed to water plant: {e}")
            return
        # Only update the plant detail (no extra confirmation message)
        await show_plant_detail(update, context, plant_id)
        return

def start_bot():
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), join_handler))
    app.add_handler(CallbackQueryHandler(handle_plant_select, pattern="^plant_"))
    app.add_handler(CallbackQueryHandler(handle_action, pattern="^(toggle_light_|water_|back_to_grid)"))
    logging.info("Telegram bot started.")
    app.run_polling()

if __name__ == "__main__":
    db.ensure_db()
    threading.Thread(target=start_bot).start()
    app.run(host='0.0.0.0', port=5500)

def get_telegram_user_id_for_db_user(user_id):
    # Look up telegram_id from DB for a given user_id
    import db as userdb
    with userdb.get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT telegram_id FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        if row:
            return int(row[0])
    return None
