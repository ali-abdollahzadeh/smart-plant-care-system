import json
import os
from typing import Optional

import paho.mqtt.client as mqtt

# Try to import hardware sensor libraries (for real mode)
try:
    import Adafruit_DHT  # for DHT11/DHT22 sensors (temp/humidity)
except Exception:
    Adafruit_DHT = None

try:
    import RPi.GPIO as GPIO  # for analog or other sensors (on Raspberry Pi)
except Exception:
    GPIO = None

class MQTTPublisher:
    """Handles MQTT connection and publishing JSON payloads."""
    def __init__(self, broker_host="mqtt-broker", broker_port=1883, client_id=None):
        self.client = mqtt.Client(client_id=client_id)
        self.broker_host = broker_host
        self.broker_port = int(broker_port)

    def connect(self):
        self.client.connect(self.broker_host, self.broker_port, 60)

    def publish(self, topic: str, payload: dict):
        self.client.publish(topic, json.dumps(payload))

class RealSensorReader:
    """
    Real sensor reader for hardware (if connected).
    - Supports DHT temperature/humidity on a GPIO pin.
    - Hook for soil moisture via ADC (to be implemented for actual hardware).
    """
    def __init__(self, plant_id: str = "1", dht_pin: Optional[int] = None, dht_model: str = "DHT22", soil_channel: Optional[int] = None):
        self.plant_id = plant_id
        self.dht_pin = dht_pin
        self.dht_model = dht_model

    def read_temperature(self) -> Optional[float]:
        if Adafruit_DHT and self.dht_pin is not None:
            sensor = Adafruit_DHT.DHT22 if self.dht_model.upper() == "DHT22" else Adafruit_DHT.DHT11
            humidity, temperature = Adafruit_DHT.read_retry(sensor, self.dht_pin)
            return round(temperature, 1) if temperature is not None else None
        return None

    def read_humidity(self) -> Optional[float]:
        if Adafruit_DHT and self.dht_pin is not None:
            sensor = Adafruit_DHT.DHT22 if self.dht_model.upper() == "DHT22" else Adafruit_DHT.DHT11
            humidity, temperature = Adafruit_DHT.read_retry(sensor, self.dht_pin)
            return round(humidity, 1) if humidity is not None else None
        return None

    def read_soil_moisture(self) -> Optional[float]:
        """
        Hook for soil moisture via ADC (analog-to-digital converter).
        Implementation depends on hardware (e.g., using MCP3008 ADC via GPIO).
        """
        # Not implemented: return None or integrate hardware ADC reading here.
        return None
