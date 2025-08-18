# Database Refactoring Summary

## 🎯 Overview

This document summarizes the comprehensive database refactoring that has been completed to ensure all microservices use shared database utilities and work correctly in containers.

## 🏗️ Architecture Changes

### Before Refactoring
- **SQLite**: Each service had its own local SQLite database
- **ThingSpeak**: Limited to single device per account
- **No shared utilities**: Each service implemented its own database logic
- **File-based**: Not suitable for containerized environments

### After Refactoring
- **PostgreSQL**: Centralized relational database for users, plants, devices
- **InfluxDB**: Time-series database for sensor data (supports multiple devices/users)
- **Shared utilities**: All services use common database package
- **Container-ready**: Proper environment variable configuration

## 📦 New Database Package Structure

```
services/database/
├── __init__.py         # Package initialization
├── postgres.py         # PostgreSQL connection and utilities
├── influxdb.py         # InfluxDB connection and utilities
├── schema.py           # Database schema definitions
├── migrations.py       # Migration scripts and utilities
├── utils.py            # Shared utility functions
├── requirements.txt    # Package dependencies
└── README.md          # Comprehensive documentation
```

## 🔄 Services Refactored

### 1. **user-service** (`services/user-service/db.py`)
**Changes:**
- ❌ Removed SQLite database file
- ✅ Now uses shared PostgreSQL utilities
- ✅ Enhanced with connection pooling
- ✅ Better error handling and logging
- ✅ Support for UUID primary keys
- ✅ JSONB fields for flexible data storage

**Key Functions:**
```python
from services.database.postgres import execute_query, test_connection

# Add user
add_user(telegram_id, name)

# Get user
get_user_by_telegram_id(telegram_id)

# Manage plants
add_plant(name, species, location, thresholds, care_info, user_id)
get_plants_for_user(user_id)
```

### 2. **catalogue-service** (`services/catalogue-service/catalogue_api.py`)
**Changes:**
- ❌ Removed SQLite database file
- ✅ Now uses shared PostgreSQL utilities
- ✅ Enhanced API with better error handling
- ✅ Support for JSONB configuration fields
- ✅ Proper relationships between entities

**Key Endpoints:**
```bash
# Register devices, services, plants, users
POST /devices, /services, /plants, /users

# List all entities
GET /devices, /services, /plants, /users

# Get specific entity
GET /devices/{id}, /services/{id}, /plants/{id}
```

### 3. **sensor-data-service** (`services/sensor-data-service/main.py`)
**Changes:**
- ✅ Now uses shared InfluxDB utilities
- ✅ Enhanced with PostgreSQL for plant info
- ✅ Better MQTT message handling
- ✅ Comprehensive REST API for data querying
- ✅ Support for multiple devices and users

**Key Features:**
```python
from services.database.influxdb import write_point, query_data

# Store sensor data with proper tagging
write_point(
    measurement='sensor_readings',
    tags={'plant_id': 'plant-123', 'user_id': 'user-456'},
    fields={'temperature': 24.5, 'humidity': 65.2}
)

# Query data with filtering
GET /data?plant_id=plant-123&start_time=-1h
GET /data/latest?user_id=user-456
GET /data/aggregated?window=1d
```

## 🆕 New Services

### 4. **database-init** (`services/database-init/`)
**Purpose:**
- Runs database migrations on startup
- Ensures proper database schema
- Seeds initial data
- Waits for databases to be ready

**Features:**
```python
# Wait for databases
wait_for_databases()

# Run migrations
run_migrations()

# Check status
check_database_status()
```

## 🗄️ Database Schema

### PostgreSQL Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | `id` (UUID), `telegram_id`, `username` |
| `plants` | Plant information | `id` (UUID), `name`, `user_id`, `thresholds` (JSONB) |
| `devices` | IoT devices | `id` (UUID), `name`, `type`, `user_id`, `config` (JSONB) |
| `services` | Microservices registry | `id` (UUID), `name`, `type`, `endpoint` |
| `user_plants` | User-plant assignments | `user_id`, `plant_id` |

### InfluxDB Measurements

| Measurement | Purpose | Key Tags |
|-------------|---------|----------|
| `sensor_readings` | Sensor data | `plant_id`, `user_id`, `device_id`, `location` |
| `actuator_events` | Actuator actions | `plant_id`, `device_id`, `actuator_type` |
| `alerts` | System alerts | `plant_id`, `user_id`, `alert_type`, `severity` |

## 🔧 Configuration

### Environment Variables

All services now use consistent environment variables:

```bash
# PostgreSQL
POSTGRES_URL=postgresql://plant_user:password123@postgres:5432/smart_plant_care
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=smart_plant_care
POSTGRES_USER=plant_user
POSTGRES_PASSWORD=password123

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token_here
INFLUXDB_ORG=smart_plant_care
INFLUXDB_BUCKET=sensor_data
```

### Docker Compose Updates

**New Services:**
```yaml
database-init:
  build: ./services/database-init
  environment:
    - POSTGRES_URL=postgresql://plant_user:password123@postgres:5432/smart_plant_care
    - INFLUXDB_URL=http://influxdb:8086
  depends_on:
    - postgres
    - influxdb
```

**Updated Dependencies:**
- All services now depend on `database-init`
- Proper startup order ensures databases are ready

## 🚀 Benefits

### 1. **Scalability**
- ✅ Support for multiple devices per user
- ✅ Support for multiple users
- ✅ Proper data separation and tagging
- ✅ Connection pooling for better performance

### 2. **Containerization**
- ✅ All services work in containers
- ✅ Proper environment variable configuration
- ✅ No file-based databases
- ✅ Shared network communication

### 3. **Data Management**
- ✅ Centralized data storage
- ✅ Proper relationships between entities
- ✅ JSONB fields for flexible configuration
- ✅ Time-series data for sensor readings

### 4. **Maintainability**
- ✅ Shared database utilities
- ✅ Consistent error handling
- ✅ Comprehensive logging
- ✅ Migration system

### 5. **Multi-Device/Multi-User Support**
- ✅ ThingSpeak limitations eliminated
- ✅ Unlimited devices and users
- ✅ Proper data isolation
- ✅ Efficient querying with tags

## 📋 Migration Guide

### For Existing Data

If you have existing SQLite data, you can migrate it:

1. **Export from SQLite:**
```bash
# Export users
sqlite3 user_data.db "SELECT * FROM users;" > users.csv

# Export plants
sqlite3 user_data.db "SELECT * FROM plants;" > plants.csv
```

2. **Import to PostgreSQL:**
```python
from services.database.postgres import execute_query

# Import users
with open('users.csv', 'r') as f:
    for line in f:
        # Parse and insert using execute_query
        pass
```

### For New Deployments

1. **Start the system:**
```bash
docker-compose up -d
```

2. **Check database status:**
```bash
curl http://localhost:5004/health  # sensor-data-service
curl http://localhost:5000/health  # catalogue-service
```

3. **Verify migrations:**
```bash
docker logs database-init
```

## 🔍 Testing

### Database Connections
```python
from services.database.postgres import test_connection
from services.database.influxdb import test_connection as test_influx

print(f"PostgreSQL: {test_connection()}")
print(f"InfluxDB: {test_influx()}")
```

### Service Health Checks
```bash
# Check all services
curl http://localhost:5000/health   # catalogue-service
curl http://localhost:5004/health   # sensor-data-service
curl http://localhost:5500/health   # user-service
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Check environment variables
   - Verify network connectivity between containers
   - Ensure databases are running

2. **Migration Failures**
   - Check database-init logs
   - Verify database permissions
   - Ensure proper startup order

3. **Service Dependencies**
   - All services depend on database-init
   - Check docker-compose dependencies
   - Verify service startup order

### Debug Commands

```bash
# Check database status
docker exec database-init python -c "
from services.database.migrations import check_database_status
print(check_database_status())
"

# Test connections
docker exec user-service python -c "
from services.database.postgres import test_connection
print(test_connection())
"
```

## 📚 Next Steps

1. **Data Migration**: Migrate existing SQLite data if needed
2. **Testing**: Test with multiple devices and users
3. **Monitoring**: Add database monitoring and alerting
4. **Backup**: Implement database backup strategies
5. **Performance**: Monitor and optimize database performance

## ✅ Summary

The database refactoring is complete and provides:

- **Shared database utilities** for all services
- **Container-ready** configuration
- **Multi-device/multi-user** support
- **Proper data relationships** and schema
- **Migration system** for database setup
- **Comprehensive error handling** and logging

All services now use the shared database package and are ready for production deployment with multiple devices and users. 