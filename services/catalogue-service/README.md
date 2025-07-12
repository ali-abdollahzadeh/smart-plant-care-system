# Catalogue Service

The Catalogue Service serves as the central registry and database for the Smart Plant Care System. It manages plants, users, devices, and services, providing a unified API for system-wide data management.

## 🎯 Purpose

- **Device Registry**: Register and track IoT devices (sensors, actuators)
- **Service Registry**: Register and discover microservices
- **Plant Database**: Store plant information, care requirements, and user assignments
- **User Management**: Manage user accounts and plant assignments
- **Web Interface**: Provide web forms for easy data entry

## 🏗️ Architecture

```
┌─────────────────┐
│   Web Forms     │  ← User-friendly registration forms
└─────────────────┘
         │
┌─────────────────┐
│   REST API      │  ← Service endpoints
└─────────────────┘
         │
┌─────────────────┐
│   SQLite DB     │  ← Local data storage
└─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up catalogue-service
```

### Running Locally
```bash
cd services/catalogue-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **API**: http://localhost:5000
- **Web Forms**: http://localhost:5000/register_plant

## 📋 API Endpoints

### Devices Management

#### Register Device
```http
POST /devices
Content-Type: application/json

{
  "name": "Raspberry Pi Sensor",
  "type": "sensor",
  "config": {
    "location": "living_room",
    "capabilities": ["temperature", "humidity", "soil_moisture"]
  }
}
```

#### List Devices
```http
GET /devices
```

#### Get Device
```http
GET /devices/{device_id}
```

### Services Management

#### Register Service
```http
POST /services
Content-Type: application/json

{
  "name": "Analytics Service",
  "type": "analytics",
  "config": {
    "endpoint": "/report/weekly",
    "capabilities": ["data_analysis", "automated_control"]
  }
}
```

#### List Services
```http
GET /services
```

#### Get Service
```http
GET /services/{service_id}
```

### Plants Management

#### Register Plant
```http
POST /plants
Content-Type: application/json

{
  "name": "Monstera Deliciosa",
  "species": "Monstera",
  "location": "living_room",
  "thresholds": {
    "temperature": {"min": 18, "max": 30},
    "humidity": {"min": 40, "max": 80},
    "soil_moisture": {"min": 300, "max": 800}
  },
  "care_info": {
    "watering_frequency": "weekly",
    "light_requirements": "indirect_bright"
  }
}
```

#### List Plants
```http
GET /plants
```

#### Get Plant
```http
GET /plants/{plant_id}
```

#### Update Plant
```http
PATCH /plants/{plant_id}
Content-Type: application/json

{
  "user_id": "user-uuid",
  "location": "kitchen"
}
```

#### List Active Plants
```http
GET /plants/active
```

### Users Management

#### Register User
```http
POST /users
Content-Type: application/json

{
  "username": "john_doe",
  "display_name": "John Doe"
}
```

#### List Users
```http
GET /users
```

#### Activate User
```http
POST /users/{user_id}/activate
```

## 🌐 Web Forms

### Plant Registration Form
- **URL**: http://localhost:5000/register_plant
- **Method**: GET (form) / POST (submit)
- **Features**: Dropdown selection from predefined plant database

### User Registration Form
- **URL**: http://localhost:5000/register_user
- **Method**: GET (form) / POST (submit)
- **Features**: Simple user registration with username and display name

## 📊 Database Schema

### Devices Table
```sql
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    config TEXT
);
```

### Services Table
```sql
CREATE TABLE services (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    config TEXT
);
```

### Plants Table
```sql
CREATE TABLE plants (
    id TEXT PRIMARY KEY,
    name TEXT,
    species TEXT,
    location TEXT,
    thresholds TEXT,
    care_info TEXT,
    user_id TEXT
);
```

### Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT,
    display_name TEXT,
    active INTEGER DEFAULT 0
);
```

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to global configuration file
- `CATALOGUE_DB_PATH`: SQLite database file path

### Auto-Import Features
- **Plant Database**: Automatically imports plant types from `home_plants_database.json`
- **Service Registration**: Services auto-register on startup
- **Device Registration**: Devices auto-register on startup

## 📈 Usage Examples

### Register a New Plant
```python
import requests

plant_data = {
    "name": "Snake Plant",
    "species": "Sansevieria",
    "location": "bedroom",
    "thresholds": {
        "temperature": {"min": 15, "max": 30},
        "humidity": {"min": 30, "max": 70},
        "soil_moisture": {"min": 200, "max": 600}
    }
}

response = requests.post("http://localhost:5000/plants", json=plant_data)
plant_id = response.json()["id"]
```

### Assign Plant to User
```python
import requests

# First register a user
user_data = {"username": "alice", "display_name": "Alice Smith"}
user_response = requests.post("http://localhost:5000/users", json=user_data)
user_id = user_response.json()["id"]

# Activate the user
requests.post(f"http://localhost:5000/users/{user_id}/activate")

# Assign plant to user
plant_update = {"user_id": user_id}
requests.patch(f"http://localhost:5000/plants/{plant_id}", json=plant_update)
```

### Get All Active Plants
```python
import requests

response = requests.get("http://localhost:5000/plants/active")
active_plants = response.json()
print(f"Found {len(active_plants)} active plants")
```

## 🔍 Monitoring

### Available Endpoints
- **Health Check**: http://localhost:5000/health
- **List Plants**: http://localhost:5000/plants
- **List Devices**: http://localhost:5000/devices
- **List Services**: http://localhost:5000/services
- **List Users**: http://localhost:5000/users
- **Active Plants**: http://localhost:5000/plants/active

### Web Forms
- **Plant Registration**: http://localhost:5000/register_plant
- **User Registration**: http://localhost:5000/register_user

### Database Status
- Database file: `/app/catalogue_data.db`
- Auto-backup: Configure volume mounts for persistence

## 🛠️ Development

### Adding New Plant Types
1. Edit `home_plants_database.json`
2. Add new plant species with care requirements
3. Restart service to auto-import

### Extending API
1. Add new endpoints in `catalogue_api.py`
2. Update database schema if needed
3. Add corresponding web forms

## 🐛 Troubleshooting

### Common Issues

1. **Service Registration Fails**
   - Check network connectivity
   - Verify service is running
   - Check logs: `docker-compose logs catalogue-service`

2. **Database Errors**
   - Check file permissions
   - Verify volume mounts
   - Restart service to reinitialize

3. **Web Forms Not Loading**
   - Check port 5000 is accessible
   - Verify Flask app is running
   - Check browser console for errors

### Logs
```bash
# View service logs
docker-compose logs catalogue-service

# Follow logs in real-time
docker-compose logs -f catalogue-service
```

## 📚 Related Services

- **Sensor Service**: Registers devices and retrieves plant configurations
- **Analytics Service**: Registers itself and accesses plant thresholds
- **User Service**: Manages user accounts and notifications
- **Cloud Adapter**: Accesses plant data for cloud integration 