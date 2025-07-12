import requests
import logging
import datetime

# Fetch the data from the Thingspeak channel
def fetch_thingspeak_data(channel_id, read_api_key, days=7):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
    params = {
        'api_key': read_api_key,
        'results': days * 24 * 12  # 5-min intervals for 7 days
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        feeds = resp.json().get('feeds', [])
        return feeds
    except Exception as e:
        logging.error(f"ThingSpeak fetch error: {e}")
        return []

# Parse the sensor data
def parse_sensor_data(feeds):
    temps, hums, moistures = [], [], []
    for entry in feeds:
        try:
            temp = float(entry.get('field1', 'nan')) 
            hum = float(entry.get('field2', 'nan')) 
            moist = float(entry.get('field3', 'nan'))
            if not any(map(lambda x: x != x, [temp, hum, moist])):  # check for NaN
                temps.append(temp)
                hums.append(hum)
                moistures.append(moist)
        except Exception:
            continue
    return temps, hums, moistures

# Generate the weekly report
def generate_weekly_report(channel_id, read_api_key): 
    feeds = fetch_thingspeak_data(channel_id, read_api_key) 
    temps, hums, moistures = parse_sensor_data(feeds) 
    report = {}
    if temps:
        report['temperature'] = {
            'avg': round(sum(temps)/len(temps), 2),
            'min': min(temps),
            'max': max(temps)
        }
    if hums:
        report['humidity'] = {
            'avg': round(sum(hums)/len(hums), 2),
            'min': min(hums),
            'max': max(hums)
        }
    if moistures:
        report['soil_moisture'] = {
            'avg': round(sum(moistures)/len(moistures), 2),
            'min': min(moistures),
            'max': max(moistures)
        }
    report['generated_at'] = datetime.datetime.now().isoformat()
    return report
