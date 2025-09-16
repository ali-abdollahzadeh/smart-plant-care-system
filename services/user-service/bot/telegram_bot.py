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
from db import add_user, get_user_by_telegram_id, get_plants_for_user, get_all_plants, assign_plant_to_user, update_user, execute_query
import paho.mqtt.client as mqtt
import json

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

bot_token = config['telegram']['bot_token']
rest_api_url = os.environ.get('REST_API_URL', 'http://sensor-data-service:5004/data/latest')
SENSOR_API_URL = os.environ.get('SENSOR_API_URL', 'http://sensor-service:5002/actuator')
CATALOGUE_API_URL = os.environ.get('CATALOGUE_API_URL', 'http://catalogue-service:5000')
USER_SERVICE_PORT = int(os.environ.get("USER_SERVICE_PORT", "5600"))

# MQTT configuration
MQTT_BROKER = config['mqtt']['broker_url']
MQTT_PORT = config['mqtt']['port']


# Helper: get or create user in catalogue for a Telegram chat_id
def get_or_create_user(chat_id, username=None, display_name=None):
    chat_id_str = str(chat_id)
    try:
        # 1) find by telegram_id first (authoritative)
        resp = requests.get(f"{CATALOGUE_API_URL}/users", timeout=5)
        if resp.status_code == 200:
            for u in resp.json():
                if (u.get("telegram_id") or "") == chat_id_str:
                    logging.info(f"[CATALOGUE] Found by telegram_id: {u}")
                    return u["id"]

        # 2) fallback: find by username if present
        lookup_username = username or chat_id_str
        if resp.status_code == 200:
            for u in resp.json():
                if (u.get("username") or "") == lookup_username:
                    # PATCH user to add telegram_id so it’s linked from now on
                    try:
                        requests.post(f"{CATALOGUE_API_URL}/users/{u['id']}/activate", timeout=5)
                    except Exception:
                        pass
                    logging.info(f"[CATALOGUE] Found by username: {u}")
                    return u["id"]

        # 3) create with telegram_id
        payload = {
            "username": lookup_username,
            "display_name": display_name or lookup_username,
            "telegram_id": chat_id_str,
            "email": None
        }
        logging.info(f"[CATALOGUE] Creating user: {payload}")
        create = requests.post(f"{CATALOGUE_API_URL}/users", json=payload, timeout=5)
        if create.status_code == 201:
            return create.json()["id"]
        logging.error(f"[CATALOGUE] Create failed: {create.status_code} {create.text}")
    except Exception as e:
        logging.error(f"[CATALOGUE] get_or_create_user error: {e}")
    return None


def get_or_create_local_user(telegram_id, username=None, display_name=None):
    """Get or create user in local database with proper telegram_id handling"""
    try:
        # First try to find existing user by telegram_id
        user_row = get_user_by_telegram_id(telegram_id)
        if user_row:
            logging.info(f"[LOCAL] Found existing user by telegram_id: {user_row}")
            return user_row["id"]
        
        # If not found by telegram_id, try to find by username
        if username:
            # Query to find user by username
            query = "SELECT * FROM users WHERE username = %s"
            result = execute_query(query, (username,))
            if result:
                user_row = result[0]
                # Update this user with the telegram_id
                update_user(user_row["id"], telegram_id=telegram_id, display_name=display_name)
                logging.info(f"[LOCAL] Updated existing user with telegram_id: {user_row['id']}")
                return user_row["id"]
        
        # If still not found, create new user
        user_id = add_user(telegram_id, display_name or username or telegram_id)
        if user_id:
            logging.info(f"[LOCAL] Created new user: telegram_id={telegram_id}, user_id={user_id}")
            return user_id
        else:
            logging.error(f"[LOCAL] Failed to create user: telegram_id={telegram_id}")
            return None
            
    except Exception as e:
        logging.error(f"[LOCAL] Error in get_or_create_local_user: {e}")
        return None

def get_user_id_for_chat(chat_id, username=None, display_name=None):
    return get_or_create_user(chat_id, username, display_name)

def register_plant_for_user(user_id, name, type_, thresholds, species=None, location=None):
    plant_id = db.add_plant(name, type_, thresholds, species, location, user_id)
    # Notify user via Telegram
    telegram_user_id = get_telegram_user_id_for_db_user(user_id)
    if telegram_user_id:
        # schedule send on the running bot loop
        tg_app.create_task(
            tg_app.bot.send_message(
                chat_id=telegram_user_id,
                text=f"🌱 A new plant '{name}' has been registered for you!"
            )
        )
    return plant_id

logging.basicConfig(level=logging.INFO)
user_chat_ids = set()

app = Flask(__name__)

# Mapping: telegram_user_id -> plant_id
user_plant_assignments = {}

# MQTT client for assignment notifications
mqtt_client = None
# Mapping: (telegram_user_id, plant_id) -> last_data
last_sent_data = {}

# Add at the top of the file
last_plant_detail_msg = {}
plant_last_status = {}  # (plant_id) -> last_status_str

def fetch_latest_flat_readings(plant_id, timeout=5):
    """
    Returns a dict like:
      {"temperature": 23.1, "humidity": 62.5, "soil_moisture": 580, "lighting": "OFF"}
    by aggregating the latest row per field from sensor-data-service.
    """
    try:
        base_url = rest_api_url.split('?')[0]
        resp = requests.get(base_url, params={"plant_id": plant_id}, timeout=timeout)
        if resp.status_code != 200:
            logging.warning(f"[SENSOR] status={resp.status_code} for plant {plant_id}")
            return {}

        payload = resp.json()
        data_list = payload.get("data", []) if isinstance(payload, dict) else []

        if not data_list:
            return {}

        # Handle pivoted format from /data/latest: dict with direct fields
        if isinstance(data_list[0], dict) and (
            'temperature' in data_list[0] or 'humidity' in data_list[0] or 'soil_moisture' in data_list[0]
        ):
            row = data_list[0]
            return {
                'temperature': row.get('temperature'),
                'humidity': row.get('humidity'),
                'soil_moisture': row.get('soil_moisture'),
                'lighting': row.get('lighting'),
                'watering': row.get('watering')
            }

        # Handle field/value/time format (fallback)
        latest = {}
        for row in data_list:
            f = row.get('field')
            t = row.get('time')
            v = row.get('value')
            if not f:
                continue
            if f not in latest or (t and t > latest[f].get('time', '')):
                latest[f] = {'value': v, 'time': t}
        flat = {k: v['value'] for k, v in latest.items()}
        return flat
    except Exception as e:
        logging.error(f"[SENSOR] fetch_latest_flat_readings error for {plant_id}: {e}")
        return {}


# Single global Telegram Application
tg_app = ApplicationBuilder().token(bot_token).build()

# Function to poll data and push updates
def poll_and_push_sensor_data():
    logging.info("[NOTIFY] poll_and_push_sensor_data thread started")
    last_assignments_snapshot = {}
    while True:
        # Periodically refresh assignments from catalogue
        try:
            prev = dict(user_plant_assignments)
            load_user_plant_assignments()
            # Detect new assignments and notify once
            for tg_id, plant_id in user_plant_assignments.items():
                if tg_id not in prev or prev.get(tg_id) != plant_id:
                    try:
                        import asyncio
                        plant, _ = get_plant_detail(plant_id)
                        plant_name = plant.get('name', plant_id)
                        asyncio.run(tg_app.bot.send_message(chat_id=tg_id, text=f"🌱 You have been assigned: {plant_name}"))
                    except Exception as e:
                        logging.error(f"[NOTIFY] Failed to send assignment message to {tg_id}: {e}")
            last_assignments_snapshot = dict(user_plant_assignments)
        except Exception as e:
            logging.error(f"[NOTIFY] Failed refreshing assignments: {e}")

        logging.info(f"[NOTIFY] user_plant_assignments: {user_plant_assignments}")
        for telegram_user_id, plant_id in list(user_plant_assignments.items()):
            try:
                resp = requests.get(f"{rest_api_url}", params={"plant_id": plant_id}, timeout=5)
                if resp.status_code == 200:
                    payload = resp.json()
                    # Support pivoted format
                    data = {}
                    if isinstance(payload, dict) and payload.get('data'):
                        first = payload['data'][0]
                        if isinstance(first, dict) and ('temperature' in first or 'humidity' in first):
                            data = first
                        else:
                            data = first if isinstance(first, dict) else {}
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
                                    asyncio.run(tg_app.bot.send_message(chat_id=telegram_user_id, text=f"⚠️ Warning for your plant '{plant.get('name','')}': {status_str}"))
                                    logging.info(f"[NOTIFY] Warning message sent to user {telegram_user_id}")
                                except Exception as e:
                                    logging.error(f"[NOTIFY] Failed to send warning to user {telegram_user_id}: {e}")
                            elif not is_problem(status_str) and is_problem(last_status):
                                logging.info(f"[NOTIFY] Sending OK to user {telegram_user_id} for plant '{plant.get('name','')}'")
                                import asyncio
                                try:
                                    logging.info(f"[NOTIFY] About to send OK message to user {telegram_user_id}")
                                    asyncio.run(tg_app.bot.send_message(chat_id=telegram_user_id, text=f"✅ All clear for your plant '{plant.get('name','')}'. Status: OK"))
                                    logging.info(f"[NOTIFY] OK message sent to user {telegram_user_id}")
                                except Exception as e:
                                    logging.error(f"[NOTIFY] Failed to send OK to user {telegram_user_id}: {e}")
                    # --- End status change notification logic ---
                    # Always send sensor data every 10 seconds
                    text = (
                        f"🌱 Plant {plant_id} update:\n"
                        f"🌡️ Temp: {data.get('temperature', '-')}\n"
                        f"💧 Humidity: {data.get('humidity', '-')}\n"
                        f"🌱 Soil: {data.get('soil_moisture', '-')}\n"
                    )
                    try:
                        logging.info(f"[NOTIFY] About to send SENSOR DATA to user {telegram_user_id} for plant {plant_id}")
                        import asyncio
                        tg_app.create_task(tg_app.bot.send_message(chat_id=telegram_user_id, text=text))
                        logging.info(f"[NOTIFY] Sensor data message sent to user {telegram_user_id}")
                    except Exception as e:
                        logging.error(f"[NOTIFY] Failed to send sensor data to user {telegram_user_id}: {e}")
            except Exception as e:
                logging.error(f"[NOTIFY] Error polling/sending data for user {telegram_user_id}, plant {plant_id}: {e}")
        time.sleep(10)  # Poll every 10 seconds

# Auto-populate user_plant_assignments from DB on startup
def load_user_plant_assignments():
    """
    Build user_plant_assignments from catalogue-service + local users table.
    Avoids querying a non-existent plants.user_id column in the local DB.
    """
    import db as userdb
    global user_plant_assignments
    try:
        # map local user_id (UUID) -> telegram_id
        users_result = userdb.execute_query('SELECT id, telegram_id FROM users')
        id_to_telegram = {str(row['id']): str(row['telegram_id']) for row in users_result if row.get('telegram_id')}
        logging.info(f"[NOTIFY] Found users in local DB: {id_to_telegram}")

        # pull plants from catalogue (they carry catalogue user_id)
        resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if resp.status_code != 200:
            logging.error(f"[NOTIFY] Failed to fetch plants from catalogue: {resp.status_code} {resp.text}")
            return

        catalogue_plants = resp.json()
        user_plant_assignments.clear()

        for p in catalogue_plants:
            owner = p.get('user_id')  # catalogue user_id (UUID)
            if owner and str(owner) in id_to_telegram:
                tg_id_str = id_to_telegram[str(owner)]
                try:
                    user_plant_assignments[int(tg_id_str)] = p['id']
                    logging.info(f"[NOTIFY] Added assignment from catalogue: telegram_id={tg_id_str}, plant_id={p['id']}")
                except Exception as e:
                    logging.warning(f"[NOTIFY] Skipping mapping telegram_id={tg_id_str} -> plant_id={p.get('id')}: {e}")

        logging.info(f"[NOTIFY] Loaded user_plant_assignments from catalogue: {user_plant_assignments}")

    except Exception as e:
        logging.error(f"[NOTIFY] Error loading user plant assignments: {e}")

def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    if rc == 0:
        logging.info("Connected to MQTT broker")
        client.subscribe("plant/assignments")
        logging.info("Subscribed to plant/assignments topic")
    else:
        logging.error(f"Failed to connect to MQTT broker: {rc}")

def on_mqtt_message(client, userdata, msg):
    """MQTT message callback for assignment notifications"""
    try:
        data = json.loads(msg.payload.decode())
        if data.get("type") == "plant_assigned":
            plant_id = data.get("plant_id")
            telegram_id = data.get("telegram_id")
            plant_name = data.get("plant_name")
            
            if telegram_id and plant_name:
                # Send assignment notification
                asyncio.run(send_assignment_notification(telegram_id, plant_name, plant_id))
                logging.info(f"Sent assignment notification to {telegram_id} for plant {plant_name}")
    except Exception as e:
        logging.error(f"Error processing MQTT assignment message: {e}")

async def send_assignment_notification(telegram_id, plant_name, plant_id):
    """Send plant assignment notification via Telegram"""
    try:
        message = f"🌱 **Plant Assigned!**\n\n"
        message += f"**Plant:** {plant_name}\n"
        message += f"**Plant ID:** `{plant_id}`\n\n"
        message += "Use /plants to view your plants and /status to check sensor data!"
        
        await tg_app.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Failed to send assignment notification to {telegram_id}: {e}")

def start_mqtt_subscriber():
    """Start MQTT subscriber for assignment notifications"""
    global mqtt_client
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        logging.error(f"MQTT subscriber error: {e}")
        time.sleep(5)
        start_mqtt_subscriber()  # Retry

# Sync assignments from catalogue-service to local DB
def sync_assignments_from_catalogue():
    try:
        # Get all users from catalogue-service
        users_resp = requests.get(f"{CATALOGUE_API_URL}/users", timeout=5)
        if users_resp.status_code != 200:
            logging.error(f"[SYNC] Failed to get users from catalogue: {users_resp.status_code}")
            return
        catalogue_users = users_resp.json()
        logging.info(f"[SYNC] Found {len(catalogue_users)} users in catalogue")
        
        # Get all plants from catalogue-service
        plants_resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if plants_resp.status_code != 200:
            logging.error(f"[SYNC] Failed to get plants from catalogue: {plants_resp.status_code}")
            return
        catalogue_plants = plants_resp.json()
        logging.info(f"[SYNC] Found {len(catalogue_plants)} plants in catalogue")
        
        # For each user in catalogue, ensure they exist in local DB
        for catalogue_user in catalogue_users:
            # Try to find the actual telegram chat ID from local DB
            telegram_id = None
            display_name = catalogue_user.get('display_name', 'Unknown')
            
            # First try to find by username in local DB
            import db as userdb
            existing_user_result = userdb.execute_query(
                'SELECT telegram_id FROM users WHERE display_name = %s OR telegram_id = %s', 
                (display_name, catalogue_user.get('username', ''))
            )
            if existing_user_result:
                telegram_id = existing_user_result[0]['telegram_id']
                logging.info(f"[SYNC] Found existing user with telegram_id: {telegram_id}")
            
            # If not found, use the catalogue username as fallback
            if not telegram_id:
                telegram_id = catalogue_user.get('username') or str(catalogue_user.get('id'))
                logging.info(f"[SYNC] Using catalogue username as telegram_id: {telegram_id}")
            
            # Check if user exists in local DB
            user_row = get_user_by_telegram_id(telegram_id)
            if not user_row:
                # Add user to local DB
                local_user_id = add_user(telegram_id, display_name)
                logging.info(f"[SYNC] Added user to local DB: telegram_id={telegram_id}, local_id={local_user_id}")
            else:
                local_user_id = user_row["id"]
                logging.info(f"[SYNC] User already exists in local DB: telegram_id={telegram_id}, local_id={local_user_id}")
            
            # Find plants assigned to this user in catalogue
            user_plants = [p for p in catalogue_plants if str(p.get('user_id')) == str(catalogue_user['id'])]
            logging.info(f"[SYNC] User {catalogue_user['id']} has {len(user_plants)} plants in catalogue")
            
            for plant in user_plants:
                # Check if plant exists in local DB
                existing_plant_result = userdb.execute_query(
                    'SELECT id FROM plants WHERE name = %s AND species = %s', 
                    (plant['name'], plant['species'])
                )
                
                if existing_plant_result:
                    plant_id = existing_plant_result[0]['id']
                    # Update assignment
                    logging.info(f"[SYNC] Updated assignment: local_user_id={local_user_id}, plant_id={plant_id}")
                else:
                    # Add plant to local DB
                    plant_id = userdb.add_plant(
                        plant['name'], 
                        plant.get('type', 'unknown'), 
                        str(plant.get('thresholds', {})), 
                        plant.get('species'), 
                        plant.get('location'), 
                        local_user_id
                    )
                    logging.info(f"[SYNC] Added plant to local DB: plant_id={plant_id}, assigned to local_user_id={local_user_id}")
        
        logging.info(f"[SYNC] Completed syncing assignments from catalogue")
        
    except Exception as e:
        logging.error(f"[SYNC] Error syncing from catalogue: {e}")

# Call this before starting the polling thread
sync_assignments_from_catalogue()
load_user_plant_assignments()



    # Fan-out to all users
def notify_user(message):
    for chat_id in list(user_chat_ids):
        tg_app.create_task(tg_app.bot.send_message(chat_id=chat_id, text=message))


@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    plant_name = data.get('plant_name')
    location = data.get('location')
    problem = data.get('problem')
    message = f"⚠️ {plant_name} at {location}: {problem}"
    threading.Thread(target=notify_user, args=(message,)).start()
    return jsonify({'status': 'ok'})
#
##
### After a plant is assigned to user send message automatically
##
#
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_chat.id)
    name = update.effective_user.full_name or update.effective_user.username or telegram_id
    
    # First try to register in catalogue service
    catalogue_user_id = get_or_create_user(update.effective_chat.id, update.effective_user.username, update.effective_user.full_name)
    if catalogue_user_id is None:
        logging.error(f"[CATALOGUE] Failed to register user in catalogue service: telegram_id={telegram_id}, name={name}")
        await update.message.reply_text("❌ Error registering with the system. Please try again later.")
        return
    
    # Get or create local user with proper telegram_id handling
    user_id = get_or_create_local_user(telegram_id, update.effective_user.username, name)
    if not user_id:
        await update.message.reply_text("❌ Error completing registration. Please try again later.")
        return
    
    # Auto-assign any plants from catalogue to this telegram user
    try:
        # Get all plants assigned to the catalogue user
        catalogue_plants_resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if catalogue_plants_resp.status_code == 200:
            all_plants = catalogue_plants_resp.json()
            catalogue_plants = [p for p in all_plants if str(p.get('user_id')) == str(catalogue_user_id)]
            
            # Assign these plants to the local user with telegram_id
            for plant in catalogue_plants:
                plant_id = plant['id']
                assign_plant_to_user(plant_id, user_id)
                logging.info(f"[AUTO-ASSIGN] Assigned plant {plant_id} to telegram user {user_id}")
            
            if catalogue_plants:
                logging.info(f"[AUTO-ASSIGN] Auto-assigned {len(catalogue_plants)} plants to telegram user")
                
    except Exception as e:
        logging.error(f"[AUTO-ASSIGN] Failed to auto-assign plants: {e}")
    
    user_chat_ids.add(update.effective_chat.id)
    
    # Check if user has plants assigned
    user_plants = get_plants_for_user(user_id)
    
    if user_plants:
        # User has plants - show them immediately
        await update.message.reply_text(
            f"🌱 Welcome back, {name}!\n\nYou have {len(user_plants)} plant(s) assigned to you. Here they are:"
        )
        await show_plant_grid(update, context)
    else:
        # No plants assigned - show welcome and available commands
        welcome_message = (
            f"🌱 Welcome to Smart Plant Care System, {name}!\n\n"
            "You don't have any plants assigned yet. Here's what you can do:\n\n"
            "📋 <b>Available Commands:</b>\n"
            "• /plants - View your assigned plants\n"
            "• /status - Get latest plant data\n"
            "• /help - Show this help message\n\n"
            "⏳ <b>Next Steps:</b>\n"
            "An admin will assign plants to you soon. You'll receive a notification when plants are assigned!\n\n"
            "💡 <b>Tip:</b> Use /plants anytime to check if you have new plants assigned."
        )
        
        # Create a nice keyboard with available commands
        keyboard = [
            [KeyboardButton("🌱 My Plants"), KeyboardButton("📊 Status")],
            [KeyboardButton("❓ Help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')
    
    return

async def plants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show user's plants"""
    await show_plant_grid(update, context)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show system status"""
    telegram_id = str(update.effective_chat.id)
    user_row = get_user_by_telegram_id(telegram_id)
    
    if not user_row:
        await update.message.reply_text("❌ You're not registered. Please use /start first.")
        return
    
    user_id = user_row["id"]
    user_plants = get_plants_for_user(user_id)
    
    if not user_plants:
        await update.message.reply_text("🌱 You don't have any plants assigned yet. Use /plants to check for new assignments.")
        return
    
    # Show status for all plants
    status_message = "📊 <b>Plant Status Overview:</b>\n\n"
    
    for plant in user_plants:
        plant_id = plant['id']
        plant_name = plant['name']
        plant_species = plant.get('species') or "Unknown"
        
        # Get sensor data for this plant
        try:
            flat = fetch_latest_flat_readings(plant_id, timeout=5)
            if flat:
                temp = flat.get("temperature", "N/A")
                humidity = flat.get("humidity", "N/A")
                soil = flat.get("soil_moisture", "N/A")

                status_message += f"🌱 <b>{plant_name}</b> ({plant_species})\n"
                status_message += f"   🌡️ Temp: {temp}°C\n"
                status_message += f"   💧 Humidity: {humidity}%\n"
                status_message += f"   🌱 Soil: {soil}\n\n"
            else:
                status_message += f"🌱 <b>{plant_name}</b> ({plant_species})\n"
                status_message += f"   ❌ No sensor data available\n\n"
        except Exception as e:
            status_message += f"🌱 <b>{plant_name}</b> ({plant_species})\n"
            status_message += f"   ❌ Error fetching data\n\n"

    await update.message.reply_text(status_message, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show help"""
    help_message = (
        "🌱 <b>Smart Plant Care System - Help</b>\n\n"
        "📋 <b>Available Commands:</b>\n"
        "• /start - Start the bot and register\n"
        "• /plants - View your assigned plants\n"
        "• /status - Get latest plant data\n"
        "• /report - Get weekly plant health report\n"
        "• /available - View available plants to assign\n"
        "• /assign - Assign a plant to yourself\n"
        "• /help - Show this help message\n\n"
        "🎯 <b>How to use:</b>\n"
        "1. Use /start to register with the system\n"
        "2. Wait for an admin to assign plants to you\n"
        "3. Use /plants to view your plants\n"
        "4. Click on a plant to see detailed controls\n"
        "5. Use /status to get quick overview\n"
        "6. Use /report for weekly health trends\n\n"
        "💡 <b>Features:</b>\n"
        "• Real-time sensor data\n"
        "• Remote watering control\n"
        "• LED lighting control\n"
        "• Plant health monitoring\n"
        "• Weekly health reports\n"
        "• Automatic notifications\n\n"
        "🆘 <b>Need help?</b>\n"
        "Contact an admin if you have issues."
    )
    
    keyboard = [
        [KeyboardButton("🌱 My Plants"), KeyboardButton("📊 Status")],
        [KeyboardButton("📈 Report"), KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(help_message, reply_markup=reply_markup, parse_mode='HTML')

async def available_plants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available plants that can be assigned"""
    try:
        # Get all plants from catalogue
        resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if resp.status_code != 200:
            await update.message.reply_text("❌ Failed to fetch available plants")
            return
        
        plants = resp.json()
        available_plants = [p for p in plants if not p.get('user_id')]  # Unassigned plants
        
        if not available_plants:
            await update.message.reply_text("🌱 No available plants to assign right now.")
            return
        
        message = "🌱 **Available Plants to Assign:**\n\n"
        keyboard = []
        
        for plant in available_plants[:10]:  # Limit to 10 plants
            plant_id = plant['id']
            plant_name = plant.get('name', 'Unnamed Plant')
            species = plant.get('species', 'Unknown Species')
            
            message += f"**{plant_name}** ({species})\n"
            message += f"ID: `{plant_id}`\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"Assign {plant_name}",
                callback_data=f"assign_{plant_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logging.error(f"Error in available_plants_command: {e}")
        await update.message.reply_text("❌ Error fetching available plants")

async def assign_plant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Assign a plant to the current user"""
    try:
        chat_id = update.effective_chat.id
        user_id = get_or_create_user(chat_id, update.effective_user.username)
        
        if not user_id:
            await update.message.reply_text("❌ Failed to get or create user")
            return
        
        # Get available plants
        resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if resp.status_code != 200:
            await update.message.reply_text("❌ Failed to fetch plants")
            return
        
        plants = resp.json()
        available_plants = [p for p in plants if not p.get('user_id')]
        
        if not available_plants:
            await update.message.reply_text("🌱 No available plants to assign right now.")
            return
        
        # Show first available plant for assignment
        plant = available_plants[0]
        plant_id = plant['id']
        plant_name = plant.get('name', 'Unnamed Plant')
        
        # Assign the plant
        assign_resp = requests.post(f"{CATALOGUE_API_URL}/user_plants", json={
            'user_id': user_id,
            'plant_id': plant_id
        }, timeout=5)
        
        if assign_resp.status_code == 201:
            await update.message.reply_text(
                f"✅ **Plant Assigned!**\n\n"
                f"**Plant:** {plant_name}\n"
                f"**Plant ID:** `{plant_id}`\n\n"
                f"Use /plants to view your plants!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Failed to assign plant: {assign_resp.text}")
            
    except Exception as e:
        logging.error(f"Error in assign_plant_command: {e}")
        await update.message.reply_text("❌ Error assigning plant")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show weekly plant health report"""
    telegram_id = str(update.effective_chat.id)
    user_row = get_user_by_telegram_id(telegram_id)
    
    if not user_row:
        await update.message.reply_text("❌ You're not registered. Please use /start first.")
        return
    
    user_id = user_row["id"]
    user_plants = get_plants_for_user(user_id)
    
    if not user_plants:
        await update.message.reply_text("🌱 You don't have any plants assigned yet. Use /plants to check for new assignments.")
        return
    
    # Show loading message
    loading_msg = await update.message.reply_text("📊 Generating weekly report... Please wait.")
    
    try:
        # Fetch weekly report from analytics service
        analytics_url = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5000')
        report_url = f"{analytics_url}/report/weekly"
        
        resp = requests.get(report_url, timeout=10)
        if resp.status_code == 200:
            report_data = resp.json()
            
            # Create a nice report message
            report_message = "📈 <b>Weekly Plant Health Report</b>\n\n"
            report_message += f"📅 Generated: {report_data.get('generated_at', 'Unknown')}\n\n"
            
            # Temperature section
            if 'temperature' in report_data:
                temp = report_data['temperature']
                report_message += "🌡️ <b>Temperature Trends:</b>\n"
                report_message += f"   • Average: {temp.get('avg', 'N/A')}°C\n"
                report_message += f"   • Range: {temp.get('min', 'N/A')}°C - {temp.get('max', 'N/A')}°C\n\n"
            
            # Humidity section
            if 'humidity' in report_data:
                hum = report_data['humidity']
                report_message += "💧 <b>Humidity Trends:</b>\n"
                report_message += f"   • Average: {hum.get('avg', 'N/A')}%\n"
                report_message += f"   • Range: {hum.get('min', 'N/A')}% - {hum.get('max', 'N/A')}%\n\n"
            
            # Soil moisture section
            if 'soil_moisture' in report_data:
                soil = report_data['soil_moisture']
                report_message += "🌱 <b>Soil Moisture Trends:</b>\n"
                report_message += f"   • Average: {soil.get('avg', 'N/A')}\n"
                report_message += f"   • Range: {soil.get('min', 'N/A')} - {soil.get('max', 'N/A')}\n\n"
            
            # Health assessment
            report_message += "🏥 <b>Health Assessment:</b>\n"
            
            # Simple health assessment based on thresholds
            health_score = 0
            total_checks = 0
            
            if 'temperature' in report_data:
                temp_avg = report_data['temperature'].get('avg', 0)
                if 18 <= temp_avg <= 30:
                    health_score += 1
                total_checks += 1
            
            if 'humidity' in report_data:
                hum_avg = report_data['humidity'].get('avg', 0)
                if 40 <= hum_avg <= 80:
                    health_score += 1
                total_checks += 1
            
            if 'soil_moisture' in report_data:
                soil_avg = report_data['soil_moisture'].get('avg', 0)
                if soil_avg >= 350:
                    health_score += 1
                total_checks += 1
            
            if total_checks > 0:
                health_percentage = (health_score / total_checks) * 100
                if health_percentage >= 80:
                    report_message += "   ✅ Excellent plant health\n"
                elif health_percentage >= 60:
                    report_message += "   ⚠️ Good plant health\n"
                else:
                    report_message += "   ❌ Needs attention\n"
            else:
                report_message += "   ❓ Insufficient data\n"
            
            report_message += "\n💡 <b>Recommendations:</b>\n"
            report_message += "• Check individual plant details with /plants\n"
            report_message += "• Use /status for current readings\n"
            report_message += "• Monitor for any alerts\n"
            
            # Update the loading message with the report
            await loading_msg.edit_text(report_message, parse_mode='HTML')
            
        else:
            await loading_msg.edit_text("❌ Failed to generate report. Please try again later.")
            
    except Exception as e:
        logging.error(f"Error generating report: {e}")
        await loading_msg.edit_text("❌ Error generating report. Please try again later.")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text button presses"""
    text = update.message.text
    
    if text == "🌱 My Plants":
        await show_plant_grid(update, context)
    elif text == "📊 Status":
        await status_command(update, context)
    elif text == "📈 Report":
        await report_command(update, context)
    elif text == "❓ Help":
        await help_command(update, context)
    else:
        await update.message.reply_text("Use the buttons below or type /help for available commands.")

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Redirect to plants command
    await show_plant_grid(update, context)

async def show_plant_grid(update, context):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    display_name = update.effective_user.full_name
    
    # Get user ID from catalogue service
    catalogue_user_id = get_or_create_user(chat_id, username, display_name)
    if catalogue_user_id is None:
        logging.error(f"[CATALOGUE] Failed to get/create user for plant grid: chat_id={chat_id}")
        await update.message.reply_text("❌ Error accessing your plants. Please try again later.")
        return
    
    try:
        # Fetch plants from catalogue service using catalogue_user_id
        resp = requests.get(f"{CATALOGUE_API_URL}/plants", timeout=5)
        if resp.status_code != 200:
            logging.error(f"[CATALOGUE] Failed to fetch plants: {resp.status_code} {resp.text}")
            await update.message.reply_text("❌ Error fetching your plants. Please try again later or contact support.")
            return
            
        all_plants = resp.json()
        plants = [p for p in all_plants if str(p.get('user_id')) == str(catalogue_user_id)]
        logging.info(f"[CATALOGUE] Found {len(plants)} plants for user {catalogue_user_id}")
        
    except Exception as e:
        logging.error(f"[CATALOGUE] Failed to fetch plants from catalogue-service: {e}")
        await update.message.reply_text("❌ Error fetching your plants. Please try again later or contact support.")
        return
        
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
    
    message = "Your Plants by Location:\n"
    for loc, plist in locations.items():
        message += f"\n📍 {loc}:\n"
        for p in plist:
            message += f"  • {p['name']} ({p['species']})\n"
    
    if getattr(update, 'message', None):
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif getattr(update, 'callback_query', None):
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)

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
        flat = fetch_latest_flat_readings(plant_id, timeout=5)
        if flat:
            sensor_data = {
                "temperature": flat.get("temperature", "-"),
                "humidity": flat.get("humidity", "-"),
                "soil_moisture": flat.get("soil_moisture", "-"),
                "lighting": flat.get("lighting", "-"),
            }
    except Exception as e:
        logging.error(f"Failed to fetch sensor data: {e}")

    return plant, sensor_data

async def show_plant_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, plant_id):
    plant, sensor_data = get_plant_detail(plant_id)
    if not plant or not plant.get('name'):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Could not find plant details. Please go back and select another plant.")
        return
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
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ An error occurred displaying plant details. Please try again.")

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

async def handle_assign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plant assignment callback buttons"""
    query = update.callback_query
    await query.answer()
    
    try:
        plant_id = query.data.replace("assign_", "")
        chat_id = update.effective_chat.id
        user_id = get_or_create_user(chat_id, update.effective_user.username)
        
        if not user_id:
            await query.edit_message_text("❌ Failed to get or create user")
            return
        
        # Assign the plant
        assign_resp = requests.post(f"{CATALOGUE_API_URL}/user_plants", json={
            'user_id': user_id,
            'plant_id': plant_id
        }, timeout=5)
        
        if assign_resp.status_code == 201:
            # Get plant details for confirmation
            plant_resp = requests.get(f"{CATALOGUE_API_URL}/plants/{plant_id}", timeout=5)
            plant_name = "Unknown Plant"
            if plant_resp.status_code == 200:
                plant_data = plant_resp.json()
                plant_name = plant_data.get('name', 'Unknown Plant')
            
            await query.edit_message_text(
                f"✅ **Plant Assigned!**\n\n"
                f"**Plant:** {plant_name}\n"
                f"**Plant ID:** `{plant_id}`\n\n"
                f"Use /plants to view your plants!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"❌ Failed to assign plant: {assign_resp.text}")
            
    except Exception as e:
        logging.error(f"Error in handle_assign_callback: {e}")
        await query.edit_message_text("❌ Error assigning plant")

def start_bot():
    import asyncio

    # Ensure this thread has an event loop
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Make sure no webhook is set (polling conflicts with webhook)
    try:
        asyncio.get_event_loop().run_until_complete(
            tg_app.bot.delete_webhook(drop_pending_updates=True)
        )
    except Exception as e:
        logging.warning(f"delete_webhook failed (continuing): {e}")


    # 2) Register handlers exactly once
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("plants", plants_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("report", report_command))
    tg_app.add_handler(CommandHandler("help", help_command))
    tg_app.add_handler(CommandHandler("available", available_plants_command))
    tg_app.add_handler(CommandHandler("assign", assign_plant_command))
    tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))
    tg_app.add_handler(CallbackQueryHandler(handle_plant_select, pattern="^plant_"))
    tg_app.add_handler(CallbackQueryHandler(handle_action, pattern="^(toggle_light_|water_|back_to_grid)"))
    tg_app.add_handler(CallbackQueryHandler(handle_assign_callback, pattern="^assign_"))

    tg_app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,  # running in a thread: avoid installing signal handlers
    )


if __name__ == "__main__":
    db.ensure_db()

    # Single-instance lock (Linux)
    try:
        import fcntl, sys
        _bot_lock = open('/tmp/telegram_bot.lock', 'w')
        fcntl.flock(_bot_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        logging.error("Another Telegram bot instance is already running in this container. Exiting.")
        sys.exit(0)

    # Optional: only run the bot in this service if env says so
    if os.environ.get("RUN_TELEGRAM_BOT", "1") == "1":
        threading.Thread(target=start_bot, daemon=True).start()

    threading.Thread(target=poll_and_push_sensor_data, daemon=True).start()
    threading.Thread(target=start_mqtt_subscriber, daemon=True).start()

    app.run(host='0.0.0.0', port=USER_SERVICE_PORT, debug=False, use_reloader=False)


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
