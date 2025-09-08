# Node-RED Dashboard

Node-RED is the visualization dashboard and automation flow engine for the Smart Plant Care System, providing real-time data monitoring, device control, and workflow orchestration.

## 🎯 Main Features

- **Real-time Monitoring**: Visualize all plant sensor data (temperature, humidity, soil moisture, etc.)
- **Device Control**: Remotely control actuators like pumps and fans via the dashboard
- **Automation Flows**: Customize automation rules (e.g., threshold alerts, auto-watering)
- **Data Integration**: Seamless integration with MQTT, InfluxDB, and microservices
- **Alert Notifications**: Send alerts via Node-RED flows to Telegram, email, etc.

## 🏗️ Architecture

```
┌──────────────┐
│ Node-RED    │
│ Dashboard   │
│ (1880/1880/ui)
└─────┬────────┘
      │
┌─────▼────────┐
│ MQTT Broker  │ ← Sensor/actuator data stream
└─────┬────────┘
      │
┌─────▼────────┐
│ Microservices│ ← Data/control flow
└──────────────┘
```

## 🚀 Quick Start

### Docker

```bash
docker-compose up nodered
```

### Local Access

- **Editor**: http://localhost:1880
- **Dashboard**: http://localhost:1880/ui

## 📋 Main Dashboard Pages

- **Real-time Overview**: Curves and status for all plant sensors
- **Plant Details**: Historical data, thresholds, and alerts for a single plant
- **Device Control**: Manual/automatic control of pumps, fans, etc.
- **Alert Center**: Alerts triggered by abnormal thresholds
- **System Logs**: Logs of service interactions and automation flows

## 🔧 Configuration

- **MQTT Broker**: `mqtt-broker:1883`
- **InfluxDB**: For historical data visualization
- **Microservice APIs**: Interact with catalogue, user, sensor-data, etc. via HTTP
- **Flow File**: `flows.json` (Node-RED flow definitions, auto-loaded with container)

## 🛠️ Development & Extension

1. Visit http://localhost:1880 to access the Node-RED editor
2. Drag and configure MQTT, database, HTTP request nodes, etc.
3. Deploy to auto-save flows to `flows.json`
4. Import/export flows for backup and migration

## 🐛 Common Issues

- **Dashboard not accessible**: Ensure the container is running and port is not occupied
- **Data not updating**: Check MQTT connection and InfluxDB query configuration
- **Flows lost**: Make sure `flows.json` is persistently mounted
- **Permission issues**: Configure firewall and authentication for external access

## 📚 Related Documentation

- [Node-RED Documentation](https://nodered.org/docs/)
- [Dashboard Node Docs](https://flows.nodered.org/node/node-red-dashboard)
- [MQTT Node Docs](https://flows.nodered.org/node/node-red-contrib-mqtt-broker)
- [InfluxDB Node Docs](https://flows.nodered.org/node/node-red-contrib-influxdb)

---

> **File Structure**  
> nodered/  
> ├── Dockerfile  
> ├── flows.json  
> └── README.md (this file)