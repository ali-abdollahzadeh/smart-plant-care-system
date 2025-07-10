import telepot
import logging
import requests
import json
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import config
from .user_manager import UserManager

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and user manager
bot = telepot.Bot(config.TELEGRAM_BOT_TOKEN)
user_manager = UserManager()

def handle(msg):
    """Handle incoming messages from users."""
    chat_id = msg['chat']['id']
    user_id = str(msg['from']['id'])
    username = msg['from'].get('username', '')
    command = msg['text'].strip().lower()

    # Create or get user
    user = user_manager.get_user(user_id)
    if not user:
        user_id = user_manager.create_user(user_id, username)
        user = user_manager.get_user(user_id)

    if command == '/start':
        welcome_message = (
            "Welcome to the Smart Plant Care System! 🌱\n\n"
            "Available commands:\n"
            "/add_plant - Add a new plant\n"
            "/my_plants - View your plants\n"
            "/status - Check plant status\n"
            "/alerts - View alerts\n"
            "/settings - Configure settings\n"
            "/help - Show this help message"
        )
        bot.sendMessage(chat_id, welcome_message)

    elif command == '/add_plant':
        # Create inline keyboard with plant types
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=plant_type, callback_data=f'add_{plant_type}')]
            for plant_type in config.PLANTS.keys()
        ])
        bot.sendMessage(chat_id, "Select plant type:", reply_markup=keyboard)

    elif command == '/my_plants':
        plants = user_manager.get_user_plants(user['user_id'])
        if not plants:
            bot.sendMessage(chat_id, "You haven't added any plants yet. Use /add_plant to add one!")
            return

        message = "Your Plants:\n\n"
        for plant in plants:
            message += f"🌱 {plant['name']} ({plant['type']})\n"
            message += f"Added: {plant['created_at']}\n\n"

        bot.sendMessage(chat_id, message)

    elif command == '/status':
        plants = user_manager.get_user_plants(user['user_id'])
        if not plants:
            bot.sendMessage(chat_id, "You haven't added any plants yet. Use /add_plant to add one!")
            return

        for plant in plants:
            # Get latest sensor data
            data = user_manager.get_plant_data(plant['plant_id'], limit=1)
            if not data:
                bot.sendMessage(chat_id, f"No data available for {plant['name']}")
                continue

            latest = data[0]
            settings = plant['settings']
            
            status_message = (
                f"Status for {plant['name']}:\n"
                f"Temperature: {latest['temperature']}°C (Threshold: {settings.get('temperature_threshold', 'N/A')}°C)\n"
                f"Humidity: {latest['humidity']}% (Threshold: {settings.get('humidity_threshold', 'N/A')}%)\n"
                f"Soil Moisture: {latest['soil_moisture']} (Threshold: {settings.get('moisture_threshold', 'N/A')})\n"
                f"Last Updated: {latest['timestamp']}"
            )
            bot.sendMessage(chat_id, status_message)

    elif command == '/alerts':
        alerts = user_manager.get_user_alerts(user['user_id'], status='active')
        if not alerts:
            bot.sendMessage(chat_id, "No active alerts.")
            return

        message = "Active Alerts:\n\n"
        for alert in alerts:
            message += f"⚠️ {alert['message']}\n"
            message += f"Type: {alert['type']}\n"
            message += f"Time: {alert['timestamp']}\n\n"

        bot.sendMessage(chat_id, message)

    elif command == '/settings':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Notification Settings", callback_data='settings_notifications')],
            [InlineKeyboardButton(text="Plant Settings", callback_data='settings_plants')],
            [InlineKeyboardButton(text="System Settings", callback_data='settings_system')]
        ])
        bot.sendMessage(chat_id, "Select settings to configure:", reply_markup=keyboard)

    elif command == '/help':
        help_message = (
            "Smart Plant Care System Help:\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/add_plant - Add a new plant\n"
            "/my_plants - View your plants\n"
            "/status - Check plant status\n"
            "/alerts - View alerts\n"
            "/settings - Configure settings\n"
            "/help - Show this help message\n\n"
            "For more information, visit our documentation."
        )
        bot.sendMessage(chat_id, help_message)

def on_callback_query(msg):
    """Handle callback queries from inline keyboards."""
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    chat_id = msg['message']['chat']['id']
    user_id = str(from_id)

    # Get user
    user = user_manager.get_user(user_id)
    if not user:
        user_id = user_manager.create_user(user_id, msg['from'].get('username', ''))

    if query_data.startswith('add_'):
        plant_type = query_data.split('_')[1]
        if plant_type in config.PLANTS:
            # Get default settings for plant type
            default_settings = config.PLANTS[plant_type]
            
            # Add plant for user
            plant_id = user_manager.add_plant(
                user['user_id'],
                f"My {plant_type}",
                plant_type,
                default_settings
            )
            
            bot.sendMessage(chat_id, f"Added new {plant_type} to your plants!")
        else:
            bot.sendMessage(chat_id, "Invalid plant type selected.")

    elif query_data.startswith('settings_'):
        setting_type = query_data.split('_')[1]
        if setting_type == 'notifications':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Enable All", callback_data='notify_enable_all')],
                [InlineKeyboardButton(text="Disable All", callback_data='notify_disable_all')],
                [InlineKeyboardButton(text="Customize", callback_data='notify_customize')]
            ])
            bot.sendMessage(chat_id, "Configure notification settings:", reply_markup=keyboard)
        elif setting_type == 'plants':
            plants = user_manager.get_user_plants(user['user_id'])
            if not plants:
                bot.sendMessage(chat_id, "You haven't added any plants yet.")
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=plant['name'], callback_data=f'plant_settings_{plant["plant_id"]}')]
                for plant in plants
            ])
            bot.sendMessage(chat_id, "Select a plant to configure:", reply_markup=keyboard)
        elif setting_type == 'system':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Language", callback_data='system_language')],
                [InlineKeyboardButton(text="Time Zone", callback_data='system_timezone')],
                [InlineKeyboardButton(text="Units", callback_data='system_units')]
            ])
            bot.sendMessage(chat_id, "Configure system settings:", reply_markup=keyboard)

    elif query_data.startswith('plant_settings_'):
        plant_id = int(query_data.split('_')[2])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Temperature Threshold", callback_data=f'threshold_temp_{plant_id}')],
            [InlineKeyboardButton(text="Humidity Threshold", callback_data=f'threshold_hum_{plant_id}')],
            [InlineKeyboardButton(text="Moisture Threshold", callback_data=f'threshold_moist_{plant_id}')]
        ])
        bot.sendMessage(chat_id, "Select threshold to configure:", reply_markup=keyboard)

# Start the bot
bot.message_loop({'chat': handle, 'callback_query': on_callback_query})
