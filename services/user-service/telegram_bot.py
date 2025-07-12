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
from db import add_user, get_user_by_telegram_id, get_plants_for_user, get_all_plants, assign_plant_to_user

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
        # First try to get all users
        resp = requests.get(f"{CATALOGUE_API_URL}/users", timeout=5)
        if resp.status_code != 200:
            logging.error(f"[CATALOGUE] Failed to get users: {resp.status_code} {resp.text}")
        else:
            users = resp.json()
            for user in users:
                if user.get('username') == lookup_username:
                    logging.info(f"[CATALOGUE] Found existing user: {user}")
                    return user['id']
        
        # If not found, create user in catalogue-service
        payload = {
            'username': lookup_username,
            'display_name': display_name or lookup_username
        }
        logging.info(f"[CATALOGUE] Creating new user with payload: {payload}")
        resp = requests.post(f"{CATALOGUE_API_URL}/users", json=payload, timeout=5)
        
        if resp.status_code == 201:
            user = resp.json()
            logging.info(f"[CATALOGUE] Successfully created user: {user}")
            return user['id']
        else:
            logging.error(f"[CATALOGUE] Failed to create user: {resp.status_code} {resp.text}")
    except requests.exceptions.Timeout:
        logging.error(f"[CATALOGUE] Timeout connecting to catalogue service")
    except requests.exceptions.ConnectionError:
        logging.error(f"[CATALOGUE] Failed to connect to catalogue service")
    except Exception as e:
        logging.error(f"[CATALOGUE] Unexpected error: {str(e)}")
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
        logging.info(f"[NOTIFY] Found users in local DB: {users}")
        # Get all plants with user assignments
        c.execute('SELECT id, user_id FROM plants WHERE user_id IS NOT NULL')
        plant_assignments = c.fetchall()
        logging.info(f"[NOTIFY] Found plant assignments in local DB: {plant_assignments}")
        for plant_id, user_id in plant_assignments:
            user_id_str = str(user_id)
            if user_id_str in users:
                telegram_id = users[user_id_str]
                try:
                    user_plant_assignments[int(telegram_id)] = plant_id
                    logging.info(f"[NOTIFY] Added assignment: telegram_id={telegram_id}, plant_id={plant_id}")
                except Exception as e:
                    logging.warning(f"[NOTIFY] Skipping user_id={user_id} with invalid telegram_id={telegram_id}: {e}")
            else:
                logging.warning(f"[NOTIFY] User {user_id} not found in users table")
    logging.info(f"[NOTIFY] Loaded user_plant_assignments from DB: {user_plant_assignments}")

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
            with userdb.get_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT telegram_id FROM users WHERE name = ? OR telegram_id = ?', 
                         (display_name, catalogue_user.get('username', '')))
                existing_user = c.fetchone()
                if existing_user:
                    telegram_id = existing_user[0]
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
                local_user_id = user_row[0]
                logging.info(f"[SYNC] User already exists in local DB: telegram_id={telegram_id}, local_id={local_user_id}")
            
            # Find plants assigned to this user in catalogue
            user_plants = [p for p in catalogue_plants if str(p.get('user_id')) == str(catalogue_user['id'])]
            logging.info(f"[SYNC] User {catalogue_user['id']} has {len(user_plants)} plants in catalogue")
            
            for plant in user_plants:
                # Check if plant exists in local DB
                with userdb.get_connection() as conn:
                    c = conn.cursor()
                    c.execute('SELECT id FROM plants WHERE name = ? AND species = ?', (plant['name'], plant['species']))
                    existing_plant = c.fetchone()
                    
                    if existing_plant:
                        plant_id = existing_plant[0]
                        # Update assignment
                        assign_plant_to_user(local_user_id, plant_id)
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
        user_id = request.form.get('user_id')  # This is catalogue-service user_id
        plant_id = request.form.get('plant_id')  # This is catalogue-service plant_id
        # Assign plant by updating user_id in catalogue-service
        try:
            update_resp = requests.patch(f"{CATALOGUE_API_URL}/plants/{plant_id}", json={"user_id": user_id})
            if update_resp.status_code == 200:
                # Find the local database user_id for this catalogue user_id
                catalogue_user = None
                for u in users:
                    if str(u['id']) == str(user_id):
                        catalogue_user = u
                        break
                
                if catalogue_user:
                    # Try to find the actual telegram chat ID from local DB
                    telegram_id = None
                    display_name = catalogue_user.get('display_name', 'Unknown')
                    
                    # First try to find by display name in local DB
                    import db as userdb
                    with userdb.get_connection() as conn:
                        c = conn.cursor()
                        c.execute('SELECT telegram_id FROM users WHERE name = ? OR telegram_id = ?', 
                                 (display_name, catalogue_user.get('username', '')))
                        existing_user = c.fetchone()
                        if existing_user:
                            telegram_id = existing_user[0]
                            logging.info(f"[ASSIGN] Found existing user with telegram_id: {telegram_id}")
                    
                    # If not found, use the catalogue username as fallback
                    if not telegram_id:
                        telegram_id = catalogue_user.get('username') or str(catalogue_user.get('id'))
                        logging.info(f"[ASSIGN] Using catalogue username as telegram_id: {telegram_id}")
                    
                    # Ensure user exists in local DB
                    user_row = get_user_by_telegram_id(telegram_id)
                    if not user_row:
                        local_user_id = add_user(telegram_id, display_name)
                        logging.info(f"[ASSIGN] Added user to local DB: telegram_id={telegram_id}, local_id={local_user_id}")
                    else:
                        local_user_id = user_row[0]
                        logging.info(f"[ASSIGN] User exists in local DB: telegram_id={telegram_id}, local_id={local_user_id}")
                    
                    # Find the plant in catalogue and add/update in local DB
                    catalogue_plant = None
                    for p in plants:
                        if str(p['id']) == str(plant_id):
                            catalogue_plant = p
                            break
                    
                    if catalogue_plant:
                        # Check if plant exists in local DB
                        with userdb.get_connection() as conn:
                            c = conn.cursor()
                            c.execute('SELECT id FROM plants WHERE name = ? AND species = ?', (catalogue_plant['name'], catalogue_plant['species']))
                            existing_plant = c.fetchone()
                            
                            if existing_plant:
                                local_plant_id = existing_plant[0]
                                # Update assignment
                                assign_plant_to_user(local_user_id, local_plant_id)
                                logging.info(f"[ASSIGN] Updated assignment: local_user_id={local_user_id}, local_plant_id={local_plant_id}")
                            else:
                                # Add plant to local DB
                                local_plant_id = userdb.add_plant(
                                    catalogue_plant['name'], 
                                    catalogue_plant.get('type', 'unknown'), 
                                    str(catalogue_plant.get('thresholds', {})), 
                                    catalogue_plant.get('species'), 
                                    catalogue_plant.get('location'), 
                                    local_user_id
                                )
                                logging.info(f"[ASSIGN] Added plant to local DB: plant_id={local_plant_id}, assigned to local_user_id={local_user_id}")
                        
                        # Update user_plant_assignments for notifications
                        try:
                            # Try to convert telegram_id to int if it's a number
                            if telegram_id.isdigit():
                                telegram_id_int = int(telegram_id)
                                user_plant_assignments[telegram_id_int] = local_plant_id
                                logging.info(f"[ASSIGN] Updated user_plant_assignments: telegram_id={telegram_id_int}, plant_id={local_plant_id}")
                            else:
                                logging.warning(f"[ASSIGN] Cannot convert telegram_id '{telegram_id}' to int, skipping user_plant_assignments update")
                        except Exception as e:
                            logging.error(f"[ASSIGN] Failed to update user_plant_assignments: {e}")
                
                msg = '<p style="color:green">Plant assigned successfully!</p>'
                # If you have a mapping from DB user_id to Telegram user_id, use it here:
                telegram_user_id = get_telegram_user_id_for_db_user(local_user_id if 'local_user_id' in locals() else None)
                if telegram_user_id:
                    try:
                        import asyncio
                        app = ApplicationBuilder().token(bot_token).build()
                        plant_name = catalogue_plant.get('name', 'Unknown Plant') if 'catalogue_plant' in locals() else 'a plant'
                        notification_message = (
                            f"🎉 <b>New Plant Assigned!</b>\n\n"
                            f"🌱 <b>{plant_name}</b> has been assigned to you!\n\n"
                            f"📋 <b>What you can do:</b>\n"
                            f"• Use /plants to view your plants\n"
                            f"• Use /status to get plant data\n"
                            f"• Click on plants to control them\n\n"
                            f"💡 <b>Tip:</b> Use /plants anytime to see your assigned plants."
                        )
                        asyncio.run(app.bot.send_message(
                            chat_id=telegram_user_id, 
                            text=notification_message,
                            parse_mode='HTML'
                        ))
                    except Exception as e:
                        logging.error(f"Failed to notify user {telegram_user_id}: {e}")
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
#
##
### Add this logic: After a plant is assigned to user send message automatically
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
    
    # Then handle local database registration
    user_row = get_user_by_telegram_id(telegram_id)
    if not user_row:
        user_id = add_user(telegram_id, name)
        if user_id:
            logging.info(f"[LOCAL] Registered new user: telegram_id={telegram_id}, name={name}, user_id={user_id}, catalogue_id={catalogue_user_id}")
        else:
            logging.error(f"[LOCAL] Failed to add user to local database: telegram_id={telegram_id}, name={name}")
            await update.message.reply_text("❌ Error completing registration. Please try again later.")
            return
    else:
        user_id = user_row[0]
        logging.info(f"[LOCAL] Found existing user: telegram_id={telegram_id}, name={name}, user_id={user_id}, catalogue_id={catalogue_user_id}")
    
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
    
    user_id = user_row[0]
    user_plants = get_plants_for_user(user_id)
    
    if not user_plants:
        await update.message.reply_text("🌱 You don't have any plants assigned yet. Use /plants to check for new assignments.")
        return
    
    # Show status for all plants
    status_message = "📊 <b>Plant Status Overview:</b>\n\n"
    
    for plant in user_plants:
        plant_id = plant[0]
        plant_name = plant[1]
        plant_species = plant[4] or "Unknown"
        
        # Get sensor data for this plant
        try:
            base_url = rest_api_url.split('?')[0]
            url = f"{base_url}?plant_id={plant_id}"
            data_resp = requests.get(url, timeout=5)
            
            if data_resp.status_code == 200:
                data = data_resp.json()
                if isinstance(data, list) and data:
                    data = data[-1]  # Get latest reading
                
                if isinstance(data, dict):
                    temp = data.get("temperature") or data.get("field1", "N/A")
                    humidity = data.get("humidity") or data.get("field2", "N/A")
                    soil = data.get("soil_moisture") or data.get("field3", "N/A")
                    
                    status_message += f"🌱 <b>{plant_name}</b> ({plant_species})\n"
                    status_message += f"   🌡️ Temp: {temp}°C\n"
                    status_message += f"   💧 Humidity: {humidity}%\n"
                    status_message += f"   🌱 Soil: {soil}\n\n"
                else:
                    status_message += f"🌱 <b>{plant_name}</b> ({plant_species})\n"
                    status_message += f"   ❌ No sensor data available\n\n"
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

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show weekly plant health report"""
    telegram_id = str(update.effective_chat.id)
    user_row = get_user_by_telegram_id(telegram_id)
    
    if not user_row:
        await update.message.reply_text("❌ You're not registered. Please use /start first.")
        return
    
    user_id = user_row[0]
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

def start_bot():
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plants", plants_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))
    app.add_handler(CallbackQueryHandler(handle_plant_select, pattern="^plant_"))
    app.add_handler(CallbackQueryHandler(handle_action, pattern="^(toggle_light_|water_|back_to_grid)"))
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
