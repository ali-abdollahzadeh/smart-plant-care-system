# Analytics Service

The Analytics Service provides intelligent data analysis and automated control for the Smart Plant Care System. It monitors sensor data, analyzes trends, triggers automated actions, and generates comprehensive reports.

## 🎯 Purpose

- **Data Analysis**: Monitor sensor data for threshold violations and trends
- **Automated Control**: Send actuator commands based on analysis results
- **Report Generation**: Create weekly plant care reports with recommendations
- **Threshold Management**: Apply plant-specific thresholds for personalized care
- **Trend Analysis**: Identify patterns in plant health and environmental conditions

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT          │    │   Control       │    │   Report        │
│   Subscriber    │    │   Center        │    │   Generator     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Analytics     │
                    │   Service       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MQTT Broker   │
                    │   (plant/command)│
                    └─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up analytics-service
```

### Running Locally
```bash
cd services/analytics-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **REST API**: http://localhost:5003
- **Weekly Reports**: http://localhost:5003/report/weekly

## 📋 API Endpoints

### Report Generation

#### Generate Weekly Report
```http
GET /report/weekly
```

**Response:**
```json
{
  "period": "2024-01-08 to 2024-01-15",
  "summary": {
    "total_readings": 1008,
    "average_temperature": 24.5,
    "average_humidity": 65.2,
    "average_soil_moisture": 450
  },
  "alerts": [
    {
      "type": "low_soil_moisture",
      "timestamp": "2024-01-12T14:30:00Z",
      "severity": "warning"
    }
  ],
  "recommendations": [
    "Consider increasing watering frequency",
    "Monitor temperature during peak hours"
  ],
  "trends": {
    "temperature": "stable",
    "humidity": "decreasing",
    "soil_moisture": "decreasing"
  }
}
```

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to global configuration file
- `CATALOGUE_URL`: URL for catalogue service registration

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

### ThingSpeak Integration
```yaml
thingspeak:
  channel_id: "2634978"
  read_api_key: "W1OQL6BMVSJW6RWF"
```

## 📊 Data Analysis

### Threshold Monitoring
The service continuously monitors sensor data against configured thresholds:

- **Temperature**: Optimal range 15-35°C
- **Humidity**: Optimal range 30-80%
- **Soil Moisture**: Optimal range 300-800 (ADC values)

### Automated Actions
When thresholds are violated, the service automatically:

1. **Low Soil Moisture**: Triggers watering system
2. **High Temperature**: Activates ventilation fan
3. **Low Humidity**: Sends alert to user
4. **Critical Conditions**: Immediate notification via MQTT

### Trend Analysis
- **Short-term**: Hourly and daily patterns
- **Medium-term**: Weekly trends and seasonal changes
- **Long-term**: Monthly and seasonal analysis

## 📈 Usage Examples

### Generate Weekly Report
```python
import requests

# Get weekly report (only available endpoint)
response = requests.get("http://localhost:5003/report/weekly")
report = response.json()

print(f"Period: {report['period']}")
print(f"Average Temperature: {report['summary']['average_temperature']}°C")
print(f"Alerts: {len(report['alerts'])}")
print(f"Recommendations: {report['recommendations']}")
```

### Monitor MQTT Commands
```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    command = json.loads(msg.payload.decode())
    print(f"Automated command: {command['action']} = {command['value']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("plant/command")
client.loop_forever()
```

### Custom Analysis
```python
import requests

# Get weekly report (only available endpoint)
response = requests.get("http://localhost:5003/report/weekly")
report = response.json()

print(f"Period: {report['period']}")
print(f"Average Temperature: {report['summary']['average_temperature']}°C")
print(f"Alerts: {len(report['alerts'])}")
print(f"Recommendations: {report['recommendations']}")
```

## 🔍 Monitoring

### Available Endpoints
- **Health Check**: http://localhost:5003/health
- **Weekly Reports**: http://localhost:5003/report/weekly

### MQTT Topics
- **Subscribe**: `plant/sensor` (sensor data)
- **Publish**: `plant/command` (actuator commands)

### Logs
```bash
# View service logs
docker-compose logs analytics-service

# Follow logs in real-time
docker-compose logs -f analytics-service
```

## 🛠️ Development

### Adding New Analysis Types
1. Update `control_center.py` for new analysis logic
2. Add new threshold types in configuration
3. Update report generation in `report_generator.py`
4. Add new automated actions

### Custom Report Formats
```python
# Example: Add custom report endpoint
@app.route('/report/custom', methods=['POST'])
def custom_report():
    data = request.json
    time_range = data.get('time_range', '7d')
    metrics = data.get('metrics', ['temperature', 'humidity'])
    
    # Generate custom analysis
    report = generate_custom_report(time_range, metrics)
    return jsonify(report)
```

### Extending Control Logic
```python
# Example: Add new control rule
def check_soil_moisture(data):
    if data['soil_moisture'] < thresholds['soil_moisture']['min']:
        return {
            'action': 'water',
            'value': 1,
            'reason': 'Low soil moisture detected'
        }
    return None
```

## 📊 Report Types

### Weekly Summary Report
- **Period**: 7-day analysis
- **Metrics**: Temperature, humidity, soil moisture averages
- **Alerts**: Threshold violations and anomalies
- **Recommendations**: Care suggestions based on data

### Trend Analysis Report
- **Short-term**: Daily patterns and hourly variations
- **Medium-term**: Weekly trends and seasonal changes
- **Long-term**: Monthly and seasonal analysis

### Alert Report
- **Critical**: Immediate action required
- **Warning**: Monitor closely
- **Info**: Normal variations

## 🐛 Troubleshooting

### Common Issues

1. **No Reports Generated**
   - Check ThingSpeak API key
   - Verify channel ID
   - Check network connectivity

2. **Automated Commands Not Working**
   - Verify MQTT connection
   - Check actuator service status
   - Review threshold configurations

3. **Data Analysis Errors**
   - Check sensor data format
   - Verify threshold configurations
   - Review log files for errors

4. **ThingSpeak Integration Issues**
   - Verify API keys
   - Check channel permissions
   - Test API connectivity

### Debug Commands
```bash
# Test report generation
curl http://localhost:5003/report/weekly

# Check MQTT commands
mosquitto_sub -h localhost -t "plant/command" -v

# Monitor sensor data
mosquitto_sub -h localhost -t "plant/sensor" -v
```

### Performance Monitoring
```bash
# Check service resource usage
docker stats analytics-service

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5003/report/weekly
```

## 📚 Related Services

- **Sensor Service**: Provides sensor data for analysis
- **Catalogue Service**: Retrieves plant configurations and thresholds
- **User Service**: Receives alerts and notifications
- **Cloud Adapter**: Accesses historical data from ThingSpeak 