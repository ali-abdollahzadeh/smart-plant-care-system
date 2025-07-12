# Cloud Adapter Service

The Cloud Adapter Service bridges the Smart Plant Care System with cloud platforms, primarily ThingSpeak, for data storage, visualization, and external integrations. It forwards sensor data to the cloud and provides REST APIs for data retrieval.

## 🎯 Purpose

- **Cloud Integration**: Forward sensor data to ThingSpeak for storage and visualization
- **Data Bridging**: Convert MQTT messages to cloud API calls
- **REST API**: Provide endpoints for accessing sensor data
- **Historical Data**: Enable retrieval of historical sensor readings
- **External Integrations**: Support third-party applications and dashboards

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT          │    │   MQTT to       │    │   ThingSpeak    │
│   Subscriber    │    │   ThingSpeak    │    │   Cloud         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Cloud         │
                    │   Adapter       │
                    │   Service       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   REST API      │
                    │   (Port 5001)   │
                    └─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up cloud-adapter-service
```

### Running Locally
```bash
cd services/cloud-adapter-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **REST API**: http://localhost:5001
- **Latest Data**: http://localhost:5001/data
- **ThingSpeak Data**: http://localhost:5001/thingspeak_data

## 📋 API Endpoints

### Data Access

#### Get Latest Sensor Data
```http
GET /data?plant_id=plant-uuid
```

**Response:**
```json
{
  "temperature": 24.5,
  "humidity": 65.2,
  "soil_moisture": 450,
  "timestamp": "2024-01-15T10:30:00Z",
  "plant_id": "plant-uuid"
}
```

#### Get ThingSpeak Historical Data
```http
GET /thingspeak_data?days=7
```

**Response:**
```json
{
  "channel": {
    "id": 2634978,
    "name": "Smart Plant Care",
    "description": "Plant monitoring data"
  },
  "feeds": [
    {
      "created_at": "2024-01-15T10:30:00Z",
      "field1": "24.5",
      "field2": "65.2",
      "field3": "450"
    }
  ]
}
```

#### Get Data by Time Range
```http
GET /data?start=2024-01-08&end=2024-01-15
```

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to global configuration file
- `CATALOGUE_URL`: URL for catalogue service registration

### ThingSpeak Configuration
```yaml
thingspeak:
  channel_id: "2634978"
  write_api_key: "EPX655D74F8VR98F"
  read_api_key: "W1OQL6BMVSJW6RWF"
  update_url: "https://api.thingspeak.com/update"
```

### MQTT Configuration
```yaml
mqtt:
  broker_url: "mqtt-broker"
  port: 1883
  publish_topic: "plant/sensor"
```

## 📊 Data Flow

### MQTT to ThingSpeak Bridge
1. **Subscribe**: Service subscribes to `plant/sensor` topic
2. **Parse**: Extract sensor data from MQTT message
3. **Transform**: Convert to ThingSpeak format
4. **Forward**: Send to ThingSpeak via HTTP POST
5. **Log**: Record successful transmission

### Data Format Mapping
```
MQTT Format → ThingSpeak Format
temperature → field1
humidity → field2
soil_moisture → field3
timestamp → created_at
```

## 📈 Usage Examples

### Get Latest Sensor Data
```python
import requests

# Get latest data for specific plant
response = requests.get("http://localhost:5001/data?plant_id=plant-uuid")
data = response.json()

print(f"Temperature: {data['temperature']}°C")
print(f"Humidity: {data['humidity']}%")
print(f"Soil Moisture: {data['soil_moisture']}")
```

### Retrieve Historical Data
```python
import requests
from datetime import datetime, timedelta

# Get last 7 days of data
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

params = {
    'start': start_date.strftime('%Y-%m-%d'),
    'end': end_date.strftime('%Y-%m-%d')
}

response = requests.get("http://localhost:5001/data", params=params)
historical_data = response.json()

for reading in historical_data['feeds']:
    print(f"Time: {reading['created_at']}")
    print(f"Temperature: {reading['field1']}°C")
```

### Monitor ThingSpeak Integration
```python
import requests

# Check ThingSpeak data
response = requests.get("http://localhost:5001/thingspeak_data?days=1")
thingspeak_data = response.json()

print(f"Channel: {thingspeak_data['channel']['name']}")
print(f"Total readings: {len(thingspeak_data['feeds'])}")
```

## 🔍 Monitoring

### Available Endpoints
- **Latest Data**: http://localhost:5001/data
- **ThingSpeak Data**: http://localhost:5001/thingspeak_data

### MQTT Topics
- **Subscribe**: `plant/sensor` (sensor data)
- **Bridge**: Forwards to ThingSpeak

### Logs
```bash
# View service logs
docker-compose logs cloud-adapter-service

# Follow logs in real-time
docker-compose logs -f cloud-adapter-service
```

## 🛠️ Development

### Adding New Cloud Platforms
1. Create new bridge class (e.g., `MqttToNewPlatformBridge`)
2. Implement data transformation methods
3. Add configuration settings
4. Update main.py to use new bridge

### Custom Data Transformations
```python
# Example: Custom data transformation
def transform_to_custom_format(mqtt_data):
    return {
        'sensor_id': mqtt_data.get('plant_id'),
        'readings': {
            'temp': mqtt_data.get('temperature'),
            'hum': mqtt_data.get('humidity'),
            'moist': mqtt_data.get('soil_moisture')
        },
        'timestamp': mqtt_data.get('timestamp')
    }
```

### Extending REST API
```python
# Example: Add custom endpoint
@app.route('/data/aggregated', methods=['GET'])
def get_aggregated_data():
    days = request.args.get('days', 7, type=int)
    
    # Get historical data
    response = requests.get(f"http://localhost:5001/data?days={days}")
    data = response.json()
    
    # Calculate aggregates
    temps = [float(feed['field1']) for feed in data['feeds']]
    avg_temp = sum(temps) / len(temps)
    
    return jsonify({
        'average_temperature': avg_temp,
        'total_readings': len(data['feeds'])
    })
```

## 📊 Data Formats

### MQTT Input Format
```json
{
  "temperature": 24.5,
  "humidity": 65.2,
  "soil_moisture": 450,
  "timestamp": "2024-01-15T10:30:00Z",
  "plant_id": "plant-uuid"
}
```

### ThingSpeak Output Format
```
POST https://api.thingspeak.com/update
Content-Type: application/x-www-form-urlencoded

api_key=EPX655D74F8VR98F&field1=24.5&field2=65.2&field3=450
```

### REST API Response Format
```json
{
  "temperature": 24.5,
  "humidity": 65.2,
  "soil_moisture": 450,
  "timestamp": "2024-01-15T10:30:00Z",
  "plant_id": "plant-uuid",
  "source": "thingspeak"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **ThingSpeak Connection Fails**
   - Verify API keys are correct
   - Check network connectivity
   - Verify channel ID exists
   - Check API rate limits

2. **MQTT Data Not Forwarding**
   - Check MQTT broker connection
   - Verify topic subscription
   - Review data format
   - Check service logs

3. **REST API Not Responding**
   - Verify Flask app is running
   - Check port 5001 is accessible
   - Review endpoint configurations
   - Check service logs

4. **Data Transformation Errors**
   - Verify MQTT data format
   - Check ThingSpeak field mappings
   - Review transformation logic
   - Test with sample data

### Debug Commands
```bash
# Test ThingSpeak connection
curl -X POST "https://api.thingspeak.com/update" \
  -d "api_key=YOUR_API_KEY&field1=25.0&field2=60.0&field3=500"

# Check MQTT messages
mosquitto_sub -h localhost -t "plant/sensor" -v

# Test REST API
curl http://localhost:5001/data

# Check service status
docker-compose logs cloud-adapter-service
```

### Performance Monitoring
```bash
# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5001/data

# Check service resource usage
docker stats cloud-adapter-service

# Monitor ThingSpeak API calls
grep "thingspeak" docker-compose logs cloud-adapter-service
```

## 📚 Related Services

- **Sensor Service**: Provides sensor data via MQTT
- **Analytics Service**: Accesses historical data for analysis
- **User Service**: May access cloud data for notifications
- **Catalogue Service**: Registers service and retrieves configurations 