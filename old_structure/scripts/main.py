import sys
import os
import time
import logging

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import sensor_reader, cloud_integration, control_logic, mqtt_client, telegram_bot

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    """
    Main function to run the Smart Plant Care System.
    """
    # Initialize the MQTT client and connect
    mqtt_client.connect_mqtt()

    try:
        while True:
            # Read sensor data
            temperature, humidity = sensor_reader.read_temperature_humidity()
            soil_moisture = sensor_reader.read_soil_moisture()

            if temperature is not None and humidity is not None:
                # Log sensor data
                logging.info(f"Temperature: {temperature}°C, Humidity: {humidity}%, Soil Moisture: {'Dry' if soil_moisture == 1 else 'Wet'}")

                # Send data to ThingSpeak
                cloud_integration.send_to_thingspeak(temperature, humidity, 800 if soil_moisture == 1 else 200)

                # Publish data to MQTT topic
                sensor_data = {
                    "temperature": temperature,
                    "humidity": humidity,
                    "soil_moisture": 800 if soil_moisture == 1 else 200
                }
                mqtt_client.publish_data("plant/sensor", sensor_data)

                # Check conditions and act accordingly
                control_logic.check_conditions_and_act()

            else:
                logging.error("Failed to read temperature or humidity.")

            # Wait before next iteration
            time.sleep(30)  # Adjust sleep time as needed

    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
    finally:
        # Cleanup actions
        mqtt_client.stop_mqtt()
        logging.info("System shutdown complete.")

if __name__ == "__main__":
    main()
