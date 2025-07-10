import requests
import logging

def post_data(thingspeak_url, write_api_key, temperature, humidity, soil_moisture):
    payload = {
        'api_key': write_api_key,
        'field1': temperature,
        'field2': humidity,
        'field3': soil_moisture
    }
    try:
        resp = requests.post(thingspeak_url, data=payload, timeout=5)
        resp.raise_for_status()
        logging.info(f"Posted to ThingSpeak: {payload}")
        return True
    except Exception as e:
        logging.error(f"ThingSpeak post error: {e}")
        return False

def get_data(channel_id, read_api_key, results=100):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
    params = {'api_key': read_api_key, 'results': results}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get('feeds', [])
    except Exception as e:
        logging.error(f"ThingSpeak get error: {e}")
        return []
