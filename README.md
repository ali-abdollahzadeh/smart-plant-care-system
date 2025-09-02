# Smart Plant Care System

A microservices-based IoT system for automated plant monitoring and care using Raspberry Pi sensors, MQTT communication, and cloud integration.

## 🏗️ System Architecture

The system consists of 11 Docker containers working together to provide comprehensive plant care automation:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sensor        │    │   Sensor Data   │    │   Analytics     │    │   Cloud         │
│   Service       │    │   Service       │    │   Service       │    │   Adapter       │
│   (Port 5002)   │    │   (Port 5004)   │    │   (Port 5003)   │    │   (Port 5001)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┼───────────────────────┘
                                 │                       │
                    ┌─────────────────┐                  │
                    │   MQTT Broker   │                  │
                    │   (Port 1883)   │                  │
                    └─────────────────┘                  │
                                 │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User          │    │   Catalogue     │    │   PostgreSQL    │    │   InfluxDB      │
│   Service       │    │   Service       │    │   (Port 5432)   │    │   (Port 8086)   │
│   (Port 5500)   │    │   (Port 5000)   │    │   Relational    │    │   Time-Series   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Node-RED      │
                    │   Dashboard     │
                    │   (Port 1880)   │
                    └─────────────────┘
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

   - Catalogue Service: <http://localhost:5000>
   - Cloud Adapter: <http://localhost:5001>
   - Sensor Service: <http://localhost:5002>
   - Analytics Service: <http://localhost:5003>
   - Sensor Data Service: <http://localhost:5004>
   - User Service: <http://localhost:5500>
   - User Dashboard: <http://localhost:5500>
   - Node-RED Editor: <http://localhost:1880>
   - Node-RED Dashboard: <http://localhost:1880/ui>
   - PostgreSQL: <http://localhost:5432>
   - InfluxDB: <http://localhost:8086>

## 📋 Service Overview

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| [Catalogue Service](services/catalogue-service/README.md) | 5000 | Device/Service Registry & Plant Database | ✅ Active |
| [Cloud Adapter Service](services/cloud-adapter-service/README.md) | 5001 | Cloud Integration (ThingSpeak, Node-RED) | ✅ Active |
| [Sensor Service](services/sensor-service/README.md) | 5002 | Sensor Data Collection & Actuator Control | ✅ Active |
| [Analytics Service](services/analytics-service/README.md) | 5003→5000 | Data Analysis & Automated Control | ✅ Active |
| [Sensor Data Service](services/sensor-data-service/README.md) | 5004 | MQTT Data Processing & Storage | ✅ Active |
| [User Service](services/user-service/README.md) | 5500 | Telegram Bot & Web Dashboard | ✅ Active |
| Database Init | - | PostgreSQL & InfluxDB Schema Setup | 🔧 Init Only |
| MQTT Broker | 1883 | Message Queue for IoT Communication | ✅ Active |
| PostgreSQL | 5432 | Relational Database (Users, Plants, Devices) | ✅ Active |
| InfluxDB | 8086 | Time-Series Database (Sensor Data) | ✅ Active |
| Node-RED | 1880 | Visual Dashboard & Data Flows | ✅ Active |

## 🔧 Configuration

Each service has its own configuration file located at `services/<service-name>/config.yaml`:

- **MQTT Settings**: Broker URL (mqtt-broker:1883), topics, and data format
- **Sensor Thresholds**: Temperature (15-35°C), humidity (30-80%), soil moisture (300-800)
- **Database Connections**: PostgreSQL for relational data, InfluxDB for time-series data
- **Service URLs**: Inter-service communication endpoints
- **Simulation Mode**: Enable/disable simulated sensors (default: enabled)
- **Cloud Integration**: ThingSpeak API configuration (when enabled)
- **Telegram Bot**: Bot token configuration for user notifications

## 📊 Data Flow

1. **Database Initialization**: Database-init service sets up PostgreSQL schemas and InfluxDB buckets
2. **Plant Registration**: Users register plants via Catalogue Service (stored in PostgreSQL)
3. **Sensor Data Collection**: Sensor Service reads data from 19 simulated plant species
4. **MQTT Publishing**: Sensor data published to `plant/sensor` topic via MQTT Broker
5. **Data Processing**: Sensor-Data Service processes MQTT messages and stores in InfluxDB
6. **Analytics & Control**: Analytics Service analyzes data and publishes commands to `plant/command`
7. **Automated Actions**: Sensor Service receives commands and controls actuators (water pumps, fans)
8. **Cloud Integration**: Cloud Adapter forwards data to external services (ThingSpeak, Node-RED)
9. **User Notifications**: User Service monitors thresholds and sends Telegram alerts
10. **Dashboard Visualization**: Node-RED provides real-time monitoring and control interface

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
  - `plant/sensor`: Sensor data from all 19 plant species
  - `plant/command`: Individual actuator commands (automated control)
  - `plant/commands`: Broadcast commands for multiple devices

- **Service Health Endpoints**:
  - **Catalogue Service**: <http://localhost:5000/health>
  - **Sensor Data Service**: <http://localhost:5004/health>
  - **Analytics Service**: <http://localhost:5003/health>
  - **User Dashboard**: <http://localhost:5500/health>

- **Data API Endpoints**:
  - **Plant Database**: <http://localhost:5000/plants> (all plants), <http://localhost:5000/plants/active> (active plants)
  - **Sensor Data**: <http://localhost:5004/data> (historical), <http://localhost:5004/data/latest> (current readings)
  - **Actuator Status**: <http://localhost:5002/actuator> (GET/POST for control)
  - **Analytics Reports**: <http://localhost:5003/report/weekly> (weekly plant care reports)
  - **Cloud Data**: <http://localhost:5001/data> (latest data for external services)

- **Web Dashboard Forms**:
  - **User Registration**: <http://localhost:5500/register_user>
  - **Plant Registration**: <http://localhost:5500/register_plant> (basic), <http://localhost:5500/register_plant_advanced> (detailed)
  - **Plant Assignment**: <http://localhost:5500/assign_plant> (assign plants to users)
  - **Plant Status Monitor**: <http://localhost:5500/plant_status> (real-time status dashboard)

- **Visual Monitoring**:
  - **Node-RED Dashboard**: <http://localhost:1880> (visual flows, real-time charts, control panels)


## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

