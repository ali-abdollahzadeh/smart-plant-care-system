# Sensor Service

The Sensor Service is responsible for collecting sensor data from physical or simulated sensors and controlling actuators (watering systems, LEDs) based on commands from other services or user input.

## 🎯 Purpose

- **Sensor Data Collection**: Read temperature, humidity, and soil moisture data
- **Actuator Control**: Control watering systems, LEDs, and other actuators
- **MQTT Publishing**: Publish sensor data to MQTT topics for other services
- **REST API**: Provide HTTP endpoints for manual actuator control
- **Simulation Mode**: Support simulated sensors for testing and development

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Physical      │    │   Simulated     │    │   REST API      │
│   Sensors       │    │   Sensors       │    │   (Port 5002)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Sensor        │
                    │   Service       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MQTT Broker   │
                    │   (plant/sensor)│
                    └─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up sensor-service
```

### Running Locally
```bash
cd services/sensor-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **REST API**: http://localhost:5002
- **Actuator Control**: http://localhost:5002/actuator

## 📋 API Endpoints

### Actuator Control

#### Control Actuator
```http
POST /actuator
Content-Type: application/json

{
  "action": "water",
  "value": 1,
  "plant_id": "plant-uuid"
}
```

**Actions Available:**
- `water`: Control watering system (0 = off, 1 = on)
- `led`: Control LED indicator (0 = off, 1 = on)
- `fan`: Control ventilation fan (0 = off, 1 = on)

#### Get Actuator Status
```http
GET /actuator?plant_id=plant-uuid
```

**Response:**
```json
{
  "water": 0,
  "led": 1,
  "fan": 0
}
```

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to global configuration file
- `PLANT_ID`: Specific plant ID for this sensor device
- `SIM_MODE`: Enable simulation mode (true/false)

### Sensor Thresholds
```yaml
sensor_thresholds:
  temperature:
    min: 15  # Celsius
    max: 35
  humidity:
    min: 30  # Percent
    max: 80
  soil_moisture:
    min: 300  # ADC value
    max: 800
```

## 📊 Data Format

### Sensor Data (MQTT Topic: `plant/sensor`)
```json
{
  "temperature": 24.5,
  "humidity": 65.2,
  "soil_moisture": 450,
  "timestamp": "2024-01-15T10:30:00Z",
  "plant_id": "plant-uuid"
}
```

### Actuator Commands (MQTT Topic: `plant/command`)
```json
{
  "action": "water",
  "value": 1,
  "plant_id": "plant-uuid"
}
```

## 🔄 Modes of Operation

### Simulation Mode
- **Purpose**: Testing and development without physical hardware
- **Features**: 
  - Simulated sensor readings within configured thresholds
  - Virtual actuator control
  - Multiple plant simulation support
- **Enable**: Set `simulation.enabled: true` in config

### Real Hardware Mode
- **Purpose**: Production deployment with physical sensors
- **Hardware**: Raspberry Pi with GPIO sensors
- **Features**:
  - Real sensor readings
  - Physical actuator control
  - GPIO pin management

## 📈 Usage Examples

### Control Watering System
```python
import requests

# Turn on watering for specific plant
command = {
    "action": "water",
    "value": 1,
    "plant_id": "plant-uuid"
}

response = requests.post("http://localhost:5002/actuator", json=command)
print(f"Actuator state: {response.json()['state']}")
```

### Get Current Actuator Status
```python
import requests

# Get status for specific plant
response = requests.get("http://localhost:5002/actuator?plant_id=plant-uuid")
status = response.json()
print(f"Water: {status['water']}, LED: {status['led']}, Fan: {status['fan']}")
```

### Monitor MQTT Data
```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"Temperature: {data['temperature']}°C")
    print(f"Humidity: {data['humidity']}%")
    print(f"Soil Moisture: {data['soil_moisture']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("plant/sensor")
client.loop_forever()
```

## 🔍 Monitoring

### Available Endpoints
- **Actuator Status**: http://localhost:5002/actuator
- **Control Actuator**: POST http://localhost:5002/actuator

### MQTT Topics
- **Publish**: `plant/sensor` (sensor data)
- **Subscribe**: `plant/command` (actuator commands)

### Logs
```bash
# View service logs
docker-compose logs sensor-service

# Follow logs in real-time
docker-compose logs -f sensor-service
```

## 🛠️ Development

### Adding New Sensors
1. Update `real_sensor_interface.py` for physical sensors
2. Update `simulator.py` for simulated sensors
3. Add new sensor types to data format
4. Update configuration thresholds

### Adding New Actuators
1. Add actuator control functions
2. Update actuator state management
3. Add new actions to API endpoints
4. Update MQTT command handling

### Hardware Integration
```python
# Example GPIO setup
import RPi.GPIO as GPIO

def setup_actuators():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(WATER_PIN, GPIO.OUT)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(FAN_PIN, GPIO.OUT)

def set_actuator(action, value):
    if action == "water":
        GPIO.output(WATER_PIN, GPIO.HIGH if value else GPIO.LOW)
    elif action == "led":
        GPIO.output(LED_PIN, GPIO.HIGH if value else GPIO.LOW)
```

## 🐛 Troubleshooting

### Common Issues

1. **Sensor Readings Not Updating**
   - Check MQTT connection
   - Verify sensor hardware connections
   - Check simulation mode settings

2. **Actuator Not Responding**
   - Verify GPIO pin assignments
   - Check hardware connections
   - Test with REST API directly

3. **MQTT Connection Issues**
   - Check broker URL and port
   - Verify network connectivity
   - Check topic permissions

4. **Simulation Mode Problems**
   - Verify configuration settings
   - Check plant ID assignments
   - Restart service to reinitialize

### Debug Commands
```bash
# Check MQTT messages
mosquitto_sub -h localhost -t "plant/sensor" -v

# Test actuator control
curl -X POST http://localhost:5002/actuator \
  -H "Content-Type: application/json" \
  -d '{"action":"water","value":1}'

# Check service status
curl http://localhost:5002/actuator
```

## 📚 Related Services

- **Analytics Service**: Receives sensor data and sends control commands
- **Cloud Adapter**: Forwards sensor data to cloud storage
- **User Service**: Receives user commands via Telegram
- **Catalogue Service**: Registers device and retrieves plant configurations 