import random
import math
import time

class SensorSimulator:
    def __init__(self, temp_range=(18, 32), hum_range=(35, 75), moist_range=(350, 750), seed=None):
        self.temp_min, self.temp_max = temp_range
        self.hum_min, self.hum_max = hum_range
        self.moist_min, self.moist_max = moist_range
        self.t = 0
        self.led_state = False
        self.watering_state = False
        if seed is not None:
            random.seed(seed)

    def set_actuator(self, action, value):
        if action == 'led':
            if value == 'toggle':
                self.led_state = not self.led_state
            else:
                self.led_state = value
            print(f"[SIM] LED set to: {'ON' if self.led_state else 'OFF'}")
        elif action == 'water':
            self.watering_state = value
            if value:
                self._last_watered = self.t
            print(f"[SIM] Watering {'STARTED' if value else 'STOPPED'}")
        else:
            print(f"[SIM] Unknown actuator: {action}")
        print(f"[SIM] set_actuator called: action={action}, value={value}, led_state={self.led_state}, watering_state={self.watering_state}")

    def get_actuator_state(self):
        return {
            'led': self.led_state,
            'watering': self.watering_state
        }

    def generate_temperature(self):
        base = (self.temp_max + self.temp_min) / 2
        amplitude = (self.temp_max - self.temp_min) / 2
        temp = base + amplitude * math.sin(self.t / 20.0) + random.uniform(-1, 1)
        # LED increases temp
        if self.led_state:
            temp += 2
        # Watering slightly decreases temp
        if getattr(self, '_last_watered', None) and self.t - self._last_watered < 3:
            temp -= 1
        return round(temp, 2)

    def generate_humidity(self):
        base = (self.hum_max + self.hum_min) / 2
        amplitude = (self.hum_max - self.hum_min) / 2
        hum = base - amplitude * math.sin(self.t / 20.0) + random.uniform(-2, 2)
        return round(hum, 2)

    def generate_soil_moisture(self):
        moist = self.moist_max - (self.t % 100) * ((self.moist_max - self.moist_min) / 100)
        moist += random.uniform(-10, 10)
        # Watering increases moisture
        if getattr(self, 'watering_state', False):
            moist = self.moist_max
        elif getattr(self, '_last_watered', None) and self.t - self._last_watered < 3:
            moist = self.moist_max - 10 * (self.t - self._last_watered)
        return int(max(self.moist_min, min(self.moist_max, moist)))

    def generate_lighting(self):
        return 'ON' if self.led_state else 'OFF'

    def next(self):
        self.t += 1
        return {
            "temperature": self.generate_temperature(),
            "humidity": self.generate_humidity(),
            "soil_moisture": self.generate_soil_moisture(),
            "lighting": self.generate_lighting(),
            "watering": self.watering_state
        }
