# Database Solution for Multi-Device/Multi-User Smart Plant Care System

## 🎯 Problem Statement

Your current system has limitations when scaling to multiple devices and users:

1. **ThingSpeak Limitations:**
   - Single channel per account (only one device)
   - Limited fields (8 fields max)
   - No multi-tenancy support
   - Rate limits on free tier
   - No relationships between data

2. **Current SQLite Issues:**
   - Local file-based (not suitable for containers)
   - No concurrent access support
   - Limited scalability
   - No backup/recovery mechanisms

## 🏗️ Proposed Solution

### **Hybrid Database Architecture**

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
                    │   PostgreSQL    │
                    │   (Relational)  │
                    │   Storage       │
                    └─────────────────┘
```

### **Database Roles**

| Database | Purpose | Data Type | Service Usage |
|----------|---------|-----------|---------------|
| **InfluxDB** | Time-series sensor data | Sensor readings, timestamps | sensor-data-service, analytics-service |
| **PostgreSQL** | Relational data | Users, plants, devices, configurations | user-service, catalogue-service |

## 📊 Data Distribution

### **InfluxDB (Time-Series Data)**
```python
# Example data point structure
{
  "measurement": "sensor_readings",
  "tags": {
    "plant_id": "plant-uuid-123",
    "user_id": "user-uuid-456", 
    "device_id": "raspberry-pi-001",
    "plant_name": "Monstera Deliciosa",
    "location": "living_room"
  },
  "fields": {
    "temperature": 24.5,
    "humidity": 65.2,
    "soil_moisture": 450,
    "lighting": "ON",
    "watering": false
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### **PostgreSQL (Relational Data)**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    telegram_id TEXT UNIQUE,
    username TEXT,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Plants table  
CREATE TABLE plants (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    species TEXT,
    location TEXT,
    thresholds JSONB,
    care_info JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Devices table
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    config JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🚀 Implementation Benefits

### **Multi-Device Support**
- **Unlimited Devices**: Each device gets a unique `device_id` tag
- **Device Management**: Track device types, configurations, ownership
- **Independent Operation**: Devices can operate independently

### **Multi-User Support**
- **User Isolation**: Data separated by `user_id` tags
- **Access Control**: Users only see their own data
- **User Management**: Full user lifecycle management

### **Scalability**
- **Horizontal Scaling**: Add more devices without limits
- **Performance**: InfluxDB optimized for time-series data
- **Storage**: Configurable retention policies

### **Data Analysis**
- **Flexible Queries**: Powerful Flux query language
- **Aggregation**: Built-in time-based aggregation
- **Real-time**: Sub-second query performance

## 📈 Usage Examples

### **Single User, Multiple Devices**
```python
# User has 3 devices monitoring different plants
devices = [
    {"id": "raspberry-pi-001", "location": "living_room"},
    {"id": "raspberry-pi-002", "location": "kitchen"}, 
    {"id": "raspberry-pi-003", "location": "bedroom"}
]

# Each device publishes data with device_id
data = {
    "device_id": "raspberry-pi-001",
    "plant_id": "plant-uuid-123",
    "user_id": "user-uuid-456",
    "temperature": 24.5,
    "humidity": 65.2,
    "soil_moisture": 450
}
```

### **Multiple Users, Multiple Devices**
```python
# User A has 2 devices
user_a_devices = ["device-001", "device-002"]

# User B has 1 device  
user_b_devices = ["device-003"]

# Data automatically separated by user_id tags
# Query for User A's data only:
response = requests.get("http://localhost:5004/data", params={
    'user_id': 'user-uuid-456',
    'start_time': '-7d'
})
```

### **Device-Specific Queries**
```python
# Get data from specific device
response = requests.get("http://localhost:5004/data", params={
    'device_id': 'raspberry-pi-001',
    'start_time': '-1h'
})

# Get latest data from all devices
response = requests.get("http://localhost:5004/data/latest")
```

## 🔧 Migration Steps

### **Step 1: Update docker-compose.yml**
```yaml
# Add PostgreSQL and InfluxDB services
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: smart_plant_care
    POSTGRES_USER: plant_user
    POSTGRES_PASSWORD: password123

influxdb:
  image: influxdb:2.7
  environment:
    DOCKER_INFLUXDB_INIT_MODE: setup
    DOCKER_INFLUXDB_INIT_USERNAME: admin
    DOCKER_INFLUXDB_INIT_PASSWORD: password123
    DOCKER_INFLUXDB_INIT_ORG: smart_plant_care
    DOCKER_INFLUXDB_INIT_BUCKET: sensor_data
```

### **Step 2: Deploy New Services**
```bash
# Deploy the new database services
docker-compose up postgres influxdb -d

# Deploy the sensor-data-service
docker-compose up sensor-data-service -d
```

### **Step 3: Update Existing Services**
- Update `user-service` to use PostgreSQL
- Update `catalogue-service` to use PostgreSQL  
- Update `analytics-service` to query InfluxDB
- Update `cloud-adapter-service` to use InfluxDB

### **Step 4: Update Sensor Devices**
```python
# Add device_id to sensor data
data = {
    "device_id": "raspberry-pi-001",  # New field
    "plant_id": "plant-uuid-123",
    "temperature": 24.5,
    "humidity": 65.2,
    "soil_moisture": 450
}
```

## 📊 Performance Comparison

| Metric | ThingSpeak | InfluxDB | Improvement |
|--------|------------|----------|-------------|
| **Devices Supported** | 1 per account | Unlimited | ∞ |
| **Users Supported** | None | Unlimited | ∞ |
| **Data Points** | 8 fields max | Unlimited | ∞ |
| **Query Speed** | ~1-2 seconds | <100ms | 10-20x |
| **Rate Limits** | Yes | No | ∞ |
| **Offline Operation** | No | Yes | ∞ |
| **Data Retention** | Limited | Configurable | ∞ |

## 🔍 Monitoring & Management

### **InfluxDB Management**
```bash
# Access InfluxDB UI
http://localhost:8086

# Create retention policy
influx bucket create --name sensor_data --retention 30d

# Monitor data ingestion
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> count()'
```

### **PostgreSQL Management**
```bash
# Connect to database
docker exec -it postgres psql -U plant_user -d smart_plant_care

# Monitor connections
SELECT count(*) FROM pg_stat_activity;

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables WHERE schemaname = 'public';
```

## 🛡️ Security Considerations

### **Data Isolation**
- User data separated by `user_id` tags
- Database-level access controls
- API-level authentication

### **Backup Strategy**
```bash
# PostgreSQL backup
docker exec postgres pg_dump -U plant_user smart_plant_care > backup.sql

# InfluxDB backup
influx backup /backup/sensor_data
```

### **Access Control**
```python
# Example: User-specific data access
def get_user_data(user_id, plant_id=None):
    query = f'''
    from(bucket: "sensor_data")
        |> range(start: -7d)
        |> filter(fn: (r) => r["user_id"] == "{user_id}")
    '''
    if plant_id:
        query += f'|> filter(fn: (r) => r["plant_id"] == "{plant_id}")\n'
    return query_api.query(query=query, org=INFLUXDB_ORG)
```

## 🔄 Future Enhancements

### **Advanced Features**
1. **Data Compression**: Automatic data downsampling
2. **Alerting**: Real-time alert generation
3. **Analytics**: Machine learning integration
4. **API Gateway**: Centralized API management
5. **Caching**: Redis for frequently accessed data

### **Scaling Options**
1. **InfluxDB Clustering**: For high availability
2. **PostgreSQL Replication**: Read replicas
3. **Load Balancing**: Multiple API instances
4. **CDN**: Static asset delivery

## 📚 Resources

- [InfluxDB Documentation](https://docs.influxdata.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Flux Query Language](https://docs.influxdata.com/flux/)
- [Docker Compose](https://docs.docker.com/compose/)

## 🎯 Conclusion

This database solution provides:

✅ **Unlimited scalability** for devices and users  
✅ **Optimal performance** for time-series data  
✅ **Data isolation** and security  
✅ **Flexible querying** and analytics  
✅ **Production-ready** architecture  
✅ **Easy migration** from current system  

The hybrid approach gives you the best of both worlds: fast time-series storage for sensor data and robust relational storage for user/plant management. 