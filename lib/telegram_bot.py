import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import sys
import os
import logging

# Add the relative path to the config directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))

# Now import the config module
import config

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup Telegram bot with the token from config
bot = telepot.Bot(config.TELEGRAM_BOT_TOKEN)

# Placeholder functions for commands
def turn_on_light():
    return "Lights have been turned on."

def turn_off_light():
    return "Lights have been turned off."

def check_temperature():
    temp, _, _ = get_thingspeak_data()
    if temp is not None:
        return f"Current temperature: {temp}°C"
    else:
        return "Failed to retrieve temperature data."

def check_humidity():
    _, hum, _ = get_thingspeak_data()
    if hum is not None:
        return f"Current humidity: {hum}%"
    else:
        return "Failed to retrieve humidity data."

def check_moisture():
    _, _, moisture = get_thingspeak_data()
    if moisture is not None:
        return f"Current soil moisture: {moisture}"
    else:
        return "Failed to retrieve soil moisture data."

# Function to fetch data from ThingSpeak with error handling
def get_thingspeak_data():
    url = f"https://api.thingspeak.com/channels/{config.THINGSPEAK_CHANNEL_ID}/feeds.json?api_key={config.THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx
        data = response.json()
        last_entry = data['feeds'][0]
        temp = float(last_entry['field1'])
        hum = float(last_entry['field2'])
        moisture = int(last_entry['field3'])
        return temp, hum, moisture
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from ThingSpeak: {e}")
        return None, None, None  # Return None values on error

# Main message handler function
def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text'].strip().lower()

    if command == '/select_plant':
        # Create inline keyboard with available plants
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=plant, callback_data=f'select_{plant}')] for plant in config.PLANTS.keys()
        ])
        bot.sendMessage(chat_id, "Select a plant:", reply_markup=keyboard)

    elif command == '/turn_on_light':
        bot.sendMessage(chat_id, turn_on_light())

    elif command == '/turn_off_light':
        bot.sendMessage(chat_id, turn_off_light())

    elif command == '/check_temperature':
        bot.sendMessage(chat_id, check_temperature())

    elif command == '/check_humidity':
        bot.sendMessage(chat_id, check_humidity())

    elif command == '/check_moisture':
        bot.sendMessage(chat_id, check_moisture())

    elif command == '/status':
        temp, hum, moisture = get_thingspeak_data()
        if temp is None or hum is None or moisture is None:
            bot.sendMessage(chat_id, "Failed to retrieve status data.")
            return
        plant_config = config.get_plant_config(config.DEFAULT_PLANT)
        status_message = (
            f"Status for {plant_config['name']}:\n"
            f"Temperature: {temp}°C (Threshold: {plant_config['temperature_threshold']}°C)\n"
            f"Humidity: {hum}% (Threshold: {plant_config['humidity_threshold']}%)\n"
            f"Soil Moisture: {moisture} (Threshold: {plant_config['moisture_threshold']})"
        )
        bot.sendMessage(chat_id, status_message)

    elif command.startswith('/set_temperature_alert'):
        try:
            parts = command.split()
            if len(parts) > 1:
                temp_threshold = float(parts[1])
                plant_config = config.get_plant_config(config.DEFAULT_PLANT)
                plant_config['temperature_threshold'] = temp_threshold
                bot.sendMessage(chat_id, f"Temperature alert threshold set to {temp_threshold}°C for {plant_config['name']}.")
            else:
                raise ValueError("No value provided")
        except (IndexError, ValueError) as e:
            logging.error(f"Error setting temperature alert: {e}")
            bot.sendMessage(chat_id, "Usage: /set_temperature_alert [value]")

    elif command.startswith('/set_humidity_alert'):
        try:
            parts = command.split()
            if len(parts) > 1:
                hum_threshold = float(parts[1])
                plant_config = config.get_plant_config(config.DEFAULT_PLANT)
                plant_config['humidity_threshold'] = hum_threshold
                bot.sendMessage(chat_id, f"Humidity alert threshold set to {hum_threshold}% for {plant_config['name']}.")
            else:
                raise ValueError("No value provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /set_humidity_alert [value]")

    elif command.startswith('/set_moisture_alert'):
        try:
            parts = command.split()
            if len(parts) > 1:
                moisture_threshold = int(parts[1])
                plant_config = config.get_plant_config(config.DEFAULT_PLANT)
                plant_config['moisture_threshold'] = moisture_threshold
                bot.sendMessage(chat_id, f"Soil moisture alert threshold set to {moisture_threshold} for {plant_config['name']}.")
            else:
                raise ValueError("No value provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /set_moisture_alert [value]")

    elif command == '/stop':
        bot.sendMessage(chat_id, stop_all_automated_actions())

    elif command.startswith('/configure_device'):
        try:
            parts = command.split()
            if len(parts) > 1:
                device_name = parts[1]
                bot.sendMessage(chat_id, configure_device(device_name))
            else:
                raise ValueError("No device name provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /configure_device [device_name]")

    elif command.startswith('/remove_device'):
        try:
            parts = command.split()
            if len(parts) > 1:
                device_name = parts[1]
                bot.sendMessage(chat_id, remove_device(device_name))
            else:
                raise ValueError("No device name provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /remove_device [device_name]")

    elif command.startswith('/set_timezone'):
        try:
            parts = command.split()
            if len(parts) > 1:
                timezone = parts[1]
                bot.sendMessage(chat_id, set_timezone(timezone))
            else:
                raise ValueError("No timezone provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /set_timezone [timezone]")

    elif command.startswith('/schedule_watering'):
        try:
            parts = command.split()
            if len(parts) > 1:
                schedule = parts[1]
                bot.sendMessage(chat_id, schedule_watering(schedule))
            else:
                raise ValueError("No schedule provided")
        except (IndexError, ValueError):
            bot.sendMessage(chat_id, "Usage: /schedule_watering [schedule]")

    elif command == '/about':
        bot.sendMessage(chat_id, "This bot manages the Smart Plant Care System using IoT technology.")

    elif command == '/help':
        help_text = (
            "Here are the commands you can use:\n"
            "/select_plant - Choose the plant profile using the options provided\n"
            "/turn_on_light - Turn on the lights in the plant care area\n"
            "/turn_off_light - Turn off the lights in the plant care area\n"
            "/check_temperature - Get the current temperature reading\n"
            "/check_humidity - Get the current humidity level\n"
            "/check_moisture - Get the current soil moisture level\n"
            "/set_temperature_alert [value] - Set a temperature threshold for alerts\n"
            "/set_humidity_alert [value] - Set a humidity level threshold for alerts\n"
            "/set_moisture_alert [value] - Set a moisture level threshold for alerts\n"
            "/status - Get a summary of current status\n"
            "/stop - Temporarily stop all automated actions\n"
            "/configure_device [device_name] - Configure a new smart device\n"
            "/remove_device [device_name] - Remove a configured smart device\n"
            "/set_timezone [timezone] - Set the timezone for scheduling\n"
            "/schedule_watering [schedule] - Set up a watering schedule\n"
            "/about - Information about this bot\n"
            "/help - Show a list of all commands\n"
        )
        bot.sendMessage(chat_id, help_text)

    else:
        bot.sendMessage(chat_id, "Unknown command. Type /help to see available commands.")

# Function to handle callback queries
def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    chat_id = msg['message']['chat']['id']

    if query_data.startswith('select_'):
        plant_name = query_data.split('_')[1]
        if plant_name in config.PLANTS:
            config.DEFAULT_PLANT = plant_name
            bot.sendMessage(chat_id, f"Selected plant: {config.PLANTS[plant_name]['name']}")
        else:
            bot.sendMessage(chat_id, "Plant not found. Please try again.")

# Start the bot
MessageLoop(bot, {'chat': handle, 'callback_query': on_callback_query}).run_as_thread()
logging.info("Bot is listening for commands...")

# Keep the program running
while True:
    pass
