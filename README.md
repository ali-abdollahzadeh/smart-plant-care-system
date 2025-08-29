# Smart Plant Care System

A microservices-based IoT system for automated plant monitoring and care using Raspberry Pi sensors, MQTT communication, and cloud integration.

## 🏗️ System Architecture

The system consists of 5 microservices that work together to provide comprehensive plant care automation:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sensor        │    │   Analytics     │    │   Cloud         │
│   Service       │    │   Service       │    │   Adapter       │
│   (Port 5002)   │    │   (Port 5003)   │    │   (Port 5001)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MQTT Broker   │
                    │   (Port 1883)   │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐    ┌─────────────────┐
                    │   Catalogue     │    │   User          │
                    │   Service       │    │   Service       │
                    │   (Port 5000)   │    │   (Port 5500)   │
                    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for local development)

### Running the System

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart-plant-care-system
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the services**
   - Catalogue Service: http://localhost:5000
   - Cloud Adapter: http://localhost:5001
   - Sensor Service: http://localhost:5002
   - Analytics Service: http://localhost:5003
   - User Service: http://localhost:5500
   - Node-RED Dashboard: http://localhost:1880/ui

## 📋 Service Overview

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| [Catalogue Service](services/catalogue-service/README.md) | 5000 | Device/Service Registry & Plant Database | ✅ Active |
| [Sensor Service](services/sensor-service/README.md) | 5002 | Sensor Data Collection & Actuator Control | ✅ Active |
| [Analytics Service](services/analytics-service/README.md) | 5003 | Data Analysis & Automated Control | ✅ Active |
| [Cloud Adapter Service](services/cloud-adapter-service/README.md) | 5001 | Cloud Integration (ThingSpeak) | ✅ Active |
| [User Service](services/user-service/README.md) | 5500 | Telegram Bot & User Notifications | ✅ Active |

## 🔧 Configuration

The system uses a centralized configuration file at `shared/config/global_config.yaml`:

- **MQTT Settings**: Broker URL, topics, and data format
- **Sensor Thresholds**: Temperature, humidity, and soil moisture limits
- **Cloud Integration**: ThingSpeak API keys and channel settings
- **Telegram Bot**: Bot token for user notifications
- **Simulation Mode**: Enable/disable simulated sensors

## 📊 Data Flow

1. **Sensor Data Collection**: Sensor Service reads data from physical/simulated sensors
2. **MQTT Publishing**: Data is published to `plant/sensor` topic
3. **Analytics Processing**: Analytics Service analyzes data and sends control commands
4. **Cloud Integration**: Cloud Adapter forwards data to ThingSpeak
5. **User Notifications**: User Service sends alerts via Telegram
6. **Dashboard**: Node-RED provides real-time visualization

## 🛠️ Development

### Local Development Setup

1. **Install dependencies for each service**
   ```bash
   cd services/[service-name]
   pip install -r requirements.txt
   ```

2. **Run individual services**
   ```bash
   python main.py
   ```

3. **Run with Docker**
   ```bash
   docker-compose up [service-name]
   ```

### Adding New Services

1. Create service directory in `services/`
2. Add Dockerfile and requirements.txt
3. Update docker-compose.yml
4. Register service in catalogue
5. Update this README

## 📈 Monitoring

- **MQTT Topics**:
  - `plant/sensor`: Sensor data
  - `plant/command`: Actuator commands
  - `plant/commands`: General commands

- **Available Endpoints**:
  - **Catalogue Service**: http://localhost:5000/health (health check), http://localhost:5000/plants (list plants)
  - **Sensor Service**: http://localhost:5002/actuator (actuator status)
  - **Analytics Service**: http://localhost:5003/health (health check), http://localhost:5003/report/weekly (weekly reports)
  - **Cloud Adapter**: http://localhost:5001/data (latest sensor data)
  - **User Service**: POST http://localhost:5500/notify (send notifications)

- **Web Forms**:
  - **Plant Registration**: http://localhost:5000/register_plant
  - **User Registration**: http://localhost:5000/register_user
  - **Plant Assignment**: http://localhost:5500/assign_plant


## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

