import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))
import config

bot = telepot.Bot(config.TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

DEFAULT_PLANT = config.DEFAULT_PLANT

# --- Catalogue Integration ---
def get_plants_from_catalogue():
    try:
        r = requests.get("http://localhost:5000/plants")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logging.error(f"Error fetching plant config from catalogue: {e}")
    return {}

def get_thingspeak_data():
    url = f"https://api.thingspeak.com/channels/{config.THINGSPEAK_CHANNEL_ID}/feeds.json?api_key={config.THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        last_entry = data['feeds'][0]
        temp = float(last_entry['field1'])
        hum = float(last_entry['field2'])
        moisture = int(last_entry['field3'])
        return temp, hum, moisture
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from ThingSpeak: {e}")
        return None, None, None

def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text'].strip().lower()

    if command == '/select_plant':
        plants = get_plants_from_catalogue()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=plant, callback_data=f'select_{plant}')] for plant in plants.keys()
        ])
        bot.sendMessage(chat_id, "Select a plant:", reply_markup=keyboard)

    elif command == '/status':
        temp, hum, moisture = get_thingspeak_data()
        if temp is None or hum is None or moisture is None:
            bot.sendMessage(chat_id, "Failed to retrieve status data.")
            return

        plants = get_plants_from_catalogue()
        plant_config = plants.get(DEFAULT_PLANT, None)
        if plant_config is None:
            bot.sendMessage(chat_id, "Plant configuration not found.")
            return

        status_message = (
            f"Status for {plant_config['name']}:\n"
            f"Temperature: {temp}°C (Threshold: {plant_config['temperature_threshold']}°C)\n"
            f"Humidity: {hum}% (Threshold: {plant_config['humidity_threshold']}%)\n"
            f"Soil Moisture: {moisture} (Threshold: {plant_config['moisture_threshold']})"
        )
        bot.sendMessage(chat_id, status_message)

    else:
        bot.sendMessage(chat_id, "Unknown command. Type /help to see available commands.")

def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    chat_id = msg['message']['chat']['id']
    if query_data.startswith('select_'):
        plant_name = query_data.split('_')[1]
        plants = get_plants_from_catalogue()
        if plant_name in plants:
            global DEFAULT_PLANT
            DEFAULT_PLANT = plant_name
            bot.sendMessage(chat_id, f"Selected plant: {plants[plant_name]['name']}")
        else:
            bot.sendMessage(chat_id, "Plant not found. Please try again.")

MessageLoop(bot, {'chat': handle, 'callback_query': on_callback_query}).run_as_thread()
logging.info("Bot is listening for commands...")

while True:
    pass
