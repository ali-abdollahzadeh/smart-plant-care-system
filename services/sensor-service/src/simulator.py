import math
import random
import time

class ComplexSimulator:
    """
    Stateful simulator with realistic dynamics:
    - Temperature follows a daily sine wave + noise.
    - Humidity inversely correlates with temp + random drift.
    - Soil moisture decays over time, increases on 'watering' events.
    """
    def __init__(self, plant_id: str = "1"):
        self.plant_id = plant_id
        self._start = time.time()
        self.soil = 600.0  # initial soil moisture (0-1023 scale)
        self.last_water_ts = 0.0

    # --- internal helpers ---
    def _day_fraction(self) -> float:
        # Fraction of day (0.0 to 1.0) based on elapsed time
        return ((time.time() - self._start) % 86400) / 86400.0

    # --- sensor simulation ---
    def read_temperature(self) -> float:
        frac = self._day_fraction()
        base = 24 + 6 * math.sin(2 * math.pi * frac)  # ~18°C to 30°C daily cycle
        noise = random.uniform(-0.7, 0.7)
        return round(base + noise, 1)

    def read_humidity(self) -> float:
        # Humidity inversely related to temperature plus some random variation
        temp = self.read_temperature()
        base_hum = max(30.0, 80 - (temp - 20))  # humidity % inversely proportional to temp
        drift = random.uniform(-1.0, 1.0)
        return round(min(100.0, base_hum + drift), 1)

    def read_soil_moisture(self) -> float:
        # Soil moisture decays gradually over time, with occasional small increases (condensation)
        decay = random.uniform(0.5, 1.2)
        self.soil = max(150.0, self.soil - decay)  # moisture cannot drop below ~150 (very dry)
        if random.random() < 0.02:  # occasional slight increase due to environment
            self.soil = min(950.0, self.soil + random.uniform(5, 20))
        return round(self.soil, 0)

    def water(self, amount: float = 200.0):
        """Simulate a watering event raising soil moisture."""
        self.soil = min(950.0, self.soil + amount)
