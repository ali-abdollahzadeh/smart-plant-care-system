import csv
import random
import time
from datetime import datetime
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(BASE_DIR, "simulated_sensor_data.csv")
num_entries = 100  # Set to None to run indefinitely
interval_seconds = 5

# Value ranges
MOISTURE_RANGE = (20, 80)         # in %
TEMPERATURE_RANGE = (15, 35)      # in Celsius
LIGHT_RANGE = (200, 1000)         # in lux

def generate_sensor_data():
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "moisture": round(random.uniform(*MOISTURE_RANGE), 2),
        "temperature": round(random.uniform(*TEMPERATURE_RANGE), 2),
        "light": round(random.uniform(*LIGHT_RANGE), 2)
    }

def main():
    with open(output_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "moisture", "temperature", "light"])
        writer.writeheader()

        count = 0
        while num_entries is None or count < num_entries:
            data = generate_sensor_data()
            writer.writerow(data)
            print(f"Generated: {data}")
            file.flush()
            time.sleep(interval_seconds)
            count += 1

if __name__ == "__main__":
    main()
