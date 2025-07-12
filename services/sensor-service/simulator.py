import random
import math
import time

class SensorSimulator:
    def __init__(self, temp_range=(18, 32), hum_range=(35, 75), moist_range=(350, 750), seed=None): # Default values for the sensor
        self.temp_min, self.temp_max = temp_range
        self.hum_min, self.hum_max = hum_range
        self.moist_min, self.moist_max = moist_range
        self.t = 0
        self.led_state = False
        self.watering_state = False
        self._current_moisture = random.randint(self.moist_min + 50, self.moist_max - 50)
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
        base = (self.temp_max + self.temp_min) / 2 # Base temperature
        amplitude = (self.temp_max - self.temp_min) / 2 # Amplitude of the sinusoidal function
        temp = base + amplitude * math.sin(self.t / 20.0) + random.uniform(-1, 1) # Sinusoidal function to simulate temperature variations
        # LED increases temp
        if self.led_state:
            temp += 2 # Increase temperature by 2 degrees
        # Watering slightly decreases temp
        if getattr(self, '_last_watered', None) and self.t - self._last_watered < 3: # Watering for 3 seconds
            temp -= 1 # Decrease temperature by 1 degree
        return round(temp, 2)

    def generate_humidity(self): 
        base = (self.hum_max + self.hum_min) / 2
        amplitude = (self.hum_max - self.hum_min) / 2
        hum = base - amplitude * math.sin(self.t / 20.0) + random.uniform(-2, 2) #
        return round(hum, 2) 

    def generate_soil_moisture(self): 
        # Moisture decays or rises gradually
        if self.watering_state:
            self._current_moisture += 12  # simulate water soaking in
        else:
            self._current_moisture -= 5  # simulate evaporation

        # Clamp within bounds
        self._current_moisture = max(self.moist_min, min(self.moist_max, self._current_moisture))

        # Add small noise
        return int(self._current_moisture + random.uniform(-5, 5))


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
