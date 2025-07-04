import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def analyze_sensor_data(data):
    """
    Analyze sensor data to generate insights or detect anomalies.
    
    Args:
        data (dict): A dictionary containing sensor data (e.g., temperature, humidity, soil moisture).
    """
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    soil_moisture = data.get('soil_moisture')

    # Example analysis: check for critical conditions
    if temperature and temperature > 30:  # Replace with your threshold
        logging.warning(f"High temperature detected: {temperature}°C")
        # Trigger alert or action

    if humidity and humidity < 30:  # Replace with your threshold
        logging.warning(f"Low humidity detected: {humidity}%")
        # Trigger alert or action

    if soil_moisture and soil_moisture == 800:  # Assuming 800 indicates dry
        logging.warning("Soil moisture is low. Consider watering the plants.")
        # Trigger alert or action

if __name__ == "__main__":
    # Example data for testing
    example_data = {
        "temperature": 32,
        "humidity": 25,
        "soil_moisture": 800
    }

    analyze_sensor_data(example_data)
