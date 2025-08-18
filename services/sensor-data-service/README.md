# Sensor Data Service

The Sensor Data Service is a specialized microservice designed to handle time-series sensor data from multiple devices and users. It stores sensor readings in InfluxDB with proper tagging for efficient querying and provides REST APIs for data retrieval and aggregation.

## 🎯 Purpose

- **Time-Series Data Storage**: Store sensor data in InfluxDB with proper tagging
- **Multi-Device Support**: Handle data from multiple sensor devices
- **Multi-User Support**: Separate data by user with proper access control
- **Data Querying**: Provide REST APIs for retrieving sensor data
- **Data Aggregation**: Support time-based data aggregation and analysis
- **Real-time Processing**: Subscribe to MQTT sensor data in real-time

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Multiple      │    │   MQTT Broker   │    │   Sensor Data   │
│   Sensor        │───▶│   (Mosquitto)   │───▶│   Service       │
│   Devices       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   InfluxDB      │
                    │   (Time-series) │
                    │   Storage       │
                    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   REST API      │
                    │   (Data Query)  │
                    └─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up sensor-data-service
```

### Running Locally
```bash
cd services/sensor-data-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **REST API**: http://localhost:5004
- **Health Check**: http://localhost:5004/health

## 📋 API Endpoints

### Get Sensor Data
```http
GET /data?plant_id=plant-uuid&user_id=user-uuid&device_id=device-uuid&start_time=-1h&end_time=now()&limit=100
```

**Query Parameters:**
- `plant_id`: Filter by specific plant
- `user_id`: Filter by specific user
- `device_id`: Filter by specific device
- `start_time`: Start time (e.g., "-1h", "-7d", "2024-01-01T00:00:00Z")
- `end_time`: End time (default: "now()")
- `limit`: Maximum number of records (default: 100)

**Response:**
```json
{
  "data": [
    {
      "time": "2024-01-15T10:30:00Z",
      "plant_id": "plant-uuid",
      "user_id": "user-uuid",
      "device_id": "device-uuid",
      "plant_name": "Monstera",
      "location": "living_room",
      "field": "temperature",
      "value": 24.5
    }
  ],
  "count": 1
}
```

### Get Latest Data
```http
GET /data/latest?plant_id=plant-uuid&user_id=user-uuid
```

**Response:**
```json
{
  "data": [
    {
      "time": "2024-01-15T10:30:00Z",
      "plant_id": "plant-uuid",
      "user_id": "user-uuid",
      "device_id": "device-uuid",
      "plant_name": "Monstera",
      "location": "living_room",
      "temperature": 24.5,
      "humidity": 65.2,
      "soil_moisture": 450,
      "lighting": "ON",
      "watering": false
    }
  ],
  "count": 1
}
```

### Get Aggregated Data
```http
GET /data/aggregated?plant_id=plant-uuid&user_id=user-uuid&window=1d
```

**Query Parameters:**
- `plant_id`: Filter by specific plant
- `user_id`: Filter by specific user
- `window`: Time window for aggregation (1h, 1d, 7d, 30d)

**Response:**
```json
{
  "data": [
    {
      "time": "2024-01-15T10:00:00Z",
      "plant_id": "plant-uuid",
      "user_id": "user-uuid",
      "avg_temperature": 24.2,
      "avg_humidity": 65.8,
      "avg_soil_moisture": 445
    }
  ],
  "window": "1d",
  "count": 24
}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "influxdb": "connected",
  "mqtt": "connected"
}
```

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to configuration file
- `INFLUXDB_URL`: InfluxDB server URL
- `INFLUXDB_TOKEN`: InfluxDB authentication token
- `INFLUXDB_ORG`: InfluxDB organization
- `INFLUXDB_BUCKET`: InfluxDB bucket name
- `CATALOGUE_URL`: Catalogue service URL

### MQTT Configuration
```yaml
mqtt:
  broker_url: "mqtt-broker"
  port: 1883
  publish_topic: "plant/sensor"
```

### InfluxDB Configuration
```yaml
influxdb:
  url: "http://influxdb:8086"
  org: "smart_plant_care"
  bucket: "sensor_data"
  retention_policy: "30d"
```

## 📊 Data Structure

### InfluxDB Data Points
Each sensor reading is stored as a data point with:

**Tags (for filtering and indexing):**
- `plant_id`: Unique plant identifier
- `user_id`: User who owns the plant
- `device_id`: Sensor device identifier
- `plant_name`: Human-readable plant name
- `plant_species`: Plant species
- `location`: Plant location

**Fields (sensor values):**
- `temperature`: Temperature in Celsius
- `humidity`: Humidity percentage
- `soil_moisture`: Soil moisture value
- `lighting`: Lighting status (ON/OFF)
- `watering`: Watering status (true/false)

**Timestamp:**
- Automatic timestamp for each reading

### Example Data Point
```python
Point("sensor_readings")
    .tag("plant_id", "plant-uuid-123")
    .tag("user_id", "user-uuid-456")
    .tag("device_id", "raspberry-pi-001")
    .tag("plant_name", "Monstera Deliciosa")
    .tag("location", "living_room")
    .field("temperature", 24.5)
    .field("humidity", 65.2)
    .field("soil_moisture", 450)
    .field("lighting", "ON")
    .field("watering", False)
    .time("2024-01-15T10:30:00Z")
```

## 📈 Usage Examples

### Get Data for Specific User
```python
import requests

# Get all sensor data for a specific user
response = requests.get("http://localhost:5004/data", params={
    'user_id': 'user-uuid-456',
    'start_time': '-7d',
    'limit': 1000
})

data = response.json()
for point in data['data']:
    print(f"Plant: {point['plant_name']}, Temp: {point['value']}°C")
```

### Get Latest Data for All Plants
```python
import requests

# Get latest readings for all plants
response = requests.get("http://localhost:5004/data/latest")
data = response.json()

for plant in data['data']:
    print(f"{plant['plant_name']}: {plant['temperature']}°C, {plant['humidity']}%")
```

### Get Aggregated Data for Analytics
```python
import requests

# Get daily averages for the last week
response = requests.get("http://localhost:5004/data/aggregated", params={
    'plant_id': 'plant-uuid-123',
    'window': '7d'
})

data = response.json()
for day in data['data']:
    print(f"Date: {day['time']}, Avg Temp: {day['avg_temperature']}°C")
```

### Monitor Multiple Devices
```python
import requests

# Get data from specific device
response = requests.get("http://localhost:5004/data", params={
    'device_id': 'raspberry-pi-001',
    'start_time': '-1h'
})

data = response.json()
print(f"Device readings: {data['count']} points")
```

## 🔍 Monitoring

### Available Endpoints
- **Sensor Data**: http://localhost:5004/data
- **Latest Data**: http://localhost:5004/data/latest
- **Aggregated Data**: http://localhost:5004/data/aggregated
- **Health Check**: http://localhost:5004/health

### MQTT Topics
- **Subscribe**: `plant/sensor` (sensor data)

### Logs
```bash
# View service logs
docker-compose logs sensor-data-service

# Follow logs in real-time
docker-compose logs -f sensor-data-service
```

## 🛠️ Development

### Adding New Sensor Types
1. Update the `store_sensor_data()` function to handle new sensor fields
2. Add new fields to the InfluxDB data point
3. Update API response formatting

### Custom Data Queries
```python
# Example: Custom Flux query
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
    |> range(start: -1d)
    |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
    |> filter(fn: (r) => r["plant_id"] == "plant-uuid")
    |> filter(fn: (r) => r["_field"] == "temperature")
    |> mean()
'''

result = query_api.query(query=query, org=INFLUXDB_ORG)
```

### Data Retention Policies
```python
# Example: Set up data retention
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
buckets_api = client.buckets_api()

# Create bucket with 30-day retention
buckets_api.create_bucket(
    bucket_name="sensor_data",
    org=INFLUXDB_ORG,
    retention_rules=[{"every_seconds": 30 * 24 * 60 * 60}]  # 30 days
)
```

## 🐛 Troubleshooting

### Common Issues

1. **InfluxDB Connection Fails**
   - Verify InfluxDB is running
   - Check authentication token
   - Verify organization and bucket exist

2. **MQTT Data Not Stored**
   - Check MQTT connection
   - Verify topic subscription
   - Review data format

3. **Query Performance Issues**
   - Add proper tags for filtering
   - Use time ranges to limit data
   - Consider data aggregation

4. **Memory Usage High**
   - Implement data retention policies
   - Use downsampling for historical data
   - Monitor query limits

### Debug Commands
```bash
# Test InfluxDB connection
curl -H "Authorization: Token your_token" http://localhost:8086/health

# Check MQTT messages
mosquitto_sub -h localhost -t "plant/sensor" -v

# Test REST API
curl "http://localhost:5004/data?limit=10"

# Check service status
curl http://localhost:5004/health
```

## 📚 Related Services

- **Sensor Service**: Publishes sensor data via MQTT
- **Analytics Service**: Queries sensor data for analysis
- **User Service**: Accesses user-specific sensor data
- **Catalogue Service**: Provides plant and user metadata
- **Cloud Adapter**: May forward data to external platforms

## 🔄 Migration from ThingSpeak

### Why InfluxDB over ThingSpeak?

1. **Multi-Device Support**: Handle unlimited devices
2. **Multi-User Support**: Separate data by user
3. **Better Performance**: Optimized for time-series data
4. **Flexible Queries**: Powerful Flux query language
5. **Data Retention**: Configurable retention policies
6. **No Rate Limits**: No external API limitations
7. **Offline Operation**: Works without internet

### Migration Steps
1. Set up InfluxDB container
2. Deploy sensor-data-service
3. Update sensor devices to include device_id
4. Migrate existing data (if needed)
5. Update other services to use new API
6. Keep ThingSpeak for external dashboards (optional) 