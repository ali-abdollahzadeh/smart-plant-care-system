# Database Package

This package provides shared database utilities for the Smart Plant Care System, supporting both PostgreSQL (relational data) and InfluxDB (time-series data).

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   InfluxDB      │    │   Shared        │
│   (Relational)  │    │   (Time-series) │    │   Utilities     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Microservices │
                    │   (All Services)│
                    └─────────────────┘
```

## 📦 Package Structure

```
services/database/
├── __init__.py         # Package initialization
├── postgres.py         # PostgreSQL connection and utilities
├── influxdb.py         # InfluxDB connection and utilities
├── schema.py           # Database schema definitions
├── migrations.py       # Migration scripts and utilities
├── utils.py            # Shared utility functions
├── requirements.txt    # Package dependencies
└── README.md          # This file
```

## 🚀 Quick Start

### Installation

Add the database package to your service's requirements:

```bash
# In your service's requirements.txt
-r ../../database/requirements.txt
```

### Basic Usage

```python
# PostgreSQL usage
from database.postgres import execute_query, test_connection

# Test connection
if test_connection():
    print("PostgreSQL connected!")

# Execute query
result = execute_query("SELECT * FROM users WHERE telegram_id = %s", ['123456789'])

# InfluxDB usage
from database.influxdb import write_point, query_data

# Write sensor data
write_point(
    measurement='sensor_readings',
    tags={'plant_id': 'plant-123', 'user_id': 'user-456'},
    fields={'temperature': 24.5, 'humidity': 65.2}
)

# Query data
query = 'from(bucket: "sensor_data") |> range(start: -1h)'
result = query_data(query)
```

## 📊 Database Schema

### PostgreSQL Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | `id`, `telegram_id`, `username` |
| `plants` | Plant information | `id`, `name`, `user_id`, `thresholds` |
| `devices` | IoT devices | `id`, `name`, `type`, `user_id` |
| `services` | Microservices registry | `id`, `name`, `type`, `endpoint` |
| `user_plants` | User-plant assignments | `user_id`, `plant_id` |

### InfluxDB Measurements

| Measurement | Purpose | Key Tags |
|-------------|---------|----------|
| `sensor_readings` | Sensor data | `plant_id`, `user_id`, `device_id` |
| `actuator_events` | Actuator actions | `plant_id`, `device_id`, `actuator_type` |
| `alerts` | System alerts | `plant_id`, `user_id`, `alert_type` |

## 🔧 Configuration

### Environment Variables

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

## 📋 API Reference

### PostgreSQL Functions

#### `get_postgres_connection()`
Get a connection from the connection pool.

```python
from database.postgres import get_postgres_connection

conn = get_postgres_connection()
# Use connection...
return_postgres_connection(conn)
```

#### `execute_query(query, params=None)`
Execute a SQL query with optional parameters.

```python
from database.postgres import execute_query

# SELECT query
result = execute_query("SELECT * FROM users WHERE telegram_id = %s", ['123456789'])

# INSERT query
execute_query(
    "INSERT INTO users (telegram_id, username) VALUES (%s, %s)",
    ['123456789', 'test_user']
)
```

#### `execute_many(query, params_list)`
Execute a query with multiple parameter sets.

```python
from database.postgres import execute_many

users = [
    ('123456789', 'user1'),
    ('987654321', 'user2')
]
execute_many(
    "INSERT INTO users (telegram_id, username) VALUES (%s, %s)",
    users
)
```

#### `test_connection()`
Test PostgreSQL connection.

```python
from database.postgres import test_connection

if test_connection():
    print("PostgreSQL is connected!")
```

### InfluxDB Functions

#### `get_influxdb_client()`
Get InfluxDB client instance.

```python
from database.influxdb import get_influxdb_client

client = get_influxdb_client()
```

#### `write_point(measurement, tags=None, fields=None, timestamp=None)`
Write a single data point to InfluxDB.

```python
from database.influxdb import write_point

write_point(
    measurement='sensor_readings',
    tags={
        'plant_id': 'plant-123',
        'user_id': 'user-456',
        'device_id': 'raspberry-pi-001'
    },
    fields={
        'temperature': 24.5,
        'humidity': 65.2,
        'soil_moisture': 450
    },
    timestamp='2024-01-15T10:30:00Z'
)
```

#### `write_points(points)`
Write multiple data points to InfluxDB.

```python
from database.influxdb import write_points, Point

points = [
    Point('sensor_readings').tag('plant_id', 'plant-123').field('temperature', 24.5),
    Point('sensor_readings').tag('plant_id', 'plant-124').field('temperature', 25.0)
]
write_points(points)
```

#### `query_data(query)`
Execute a Flux query.

```python
from database.influxdb import query_data

query = '''
from(bucket: "sensor_data")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
    |> filter(fn: (r) => r["plant_id"] == "plant-123")
'''
result = query_data(query)
```

#### `test_connection()`
Test InfluxDB connection.

```python
from database.influxdb import test_connection

if test_connection():
    print("InfluxDB is connected!")
```

## 🔄 Migration

### Run Migrations

```python
from database.migrations import run_migrations

# Run all migrations
success = run_migrations()
if success:
    print("Migrations completed successfully!")
```

### Check Database Status

```python
from database.migrations import check_database_status

status = check_database_status()
print(f"PostgreSQL: {status['postgres']}")
print(f"InfluxDB: {status['influxdb']}")
```

### Get Database Info

```python
from database.migrations import get_database_info

info = get_database_info()
print(f"Users: {info['postgres']['users']}")
print(f"Plants: {info['postgres']['plants']}")
```

## 📈 Usage Examples

### User Service Integration

```python
# services/user-service/db.py
from database.postgres import execute_query

def add_user(telegram_id, name=None):
    query = """
        INSERT INTO users (telegram_id, display_name)
        VALUES (%s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
        RETURNING id
    """
    result = execute_query(query, (telegram_id, name))
    return result[0]['id'] if result else None

def get_user_by_telegram_id(telegram_id):
    query = "SELECT * FROM users WHERE telegram_id = %s"
    result = execute_query(query, (telegram_id,))
    return result[0] if result else None
```

### Sensor Data Service Integration

```python
# services/sensor-data-service/main.py
from database.influxdb import write_point

def store_sensor_data(data):
    write_point(
        measurement='sensor_readings',
        tags={
            'plant_id': data.get('plant_id'),
            'user_id': data.get('user_id'),
            'device_id': data.get('device_id')
        },
        fields={
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'soil_moisture': data.get('soil_moisture')
        }
    )
```

### Analytics Service Integration

```python
# services/analytics-service/main.py
from database.influxdb import query_data

def get_weekly_averages(plant_id):
    query = f'''
    from(bucket: "sensor_data")
        |> range(start: -7d)
        |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
        |> filter(fn: (r) => r["plant_id"] == "{plant_id}")
        |> aggregateWindow(every: 1d, fn: mean)
    '''
    return query_data(query)
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Pool Exhausted**
   - Increase pool size in `postgres.py`
   - Ensure connections are returned to pool

2. **InfluxDB Token Issues**
   - Verify token is correct
   - Check organization and bucket names

3. **PostgreSQL Connection Failures**
   - Verify database URL format
   - Check network connectivity between containers

### Debug Commands

```python
# Test connections
from database.postgres import test_connection
from database.influxdb import test_connection as test_influx

print(f"PostgreSQL: {test_connection()}")
print(f"InfluxDB: {test_influx()}")

# Check database info
from database.migrations import get_database_info
info = get_database_info()
print(info)
```

## 🔒 Security Considerations

- Use environment variables for sensitive data
- Implement connection pooling for performance
- Use parameterized queries to prevent SQL injection
- Validate all input data before database operations

## 📚 Related Documentation

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Flux Query Language](https://docs.influxdata.com/flux/) 