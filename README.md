# Smart Plant Care System

Project for the course Programming for IoT Applications at Politecnico di Torino, academic year 2023-2024.

## Overview

The Smart Plant Care System is an IoT-based solution designed to automate and optimize plant care. By integrating sensors, a Raspberry Pi, and cloud services, the system continuously monitors soil moisture, humidity, and temperature to maintain optimal growing conditions. It provides real-time alerts and reports to users via a Telegram Bot and visualization dashboards like Node-RED, making plant care more efficient and user-friendly.

## Features

- **Automated Monitoring**: Continuously monitors soil moisture, humidity, and temperature using connected sensors.
- **Real-Time Alerts**: Sends alerts and notifications through a Telegram Bot based on real-time sensor data.
- **Data Visualization**: Utilizes Node-RED for real-time data visualization and ThingSpeak for storing and visualizing data.
- **Data-Driven Decisions**: Generates weekly reports and provides recommendations based on historical data to enhance plant health.
- **Scalable Design**: Connects to cloud services for data storage and analysis, allowing for scalable plant care solutions.

## Components

1. **Sensors**: 
   - Soil Moisture Sensor
   - DHT11 Sensor (Temperature and Humidity)
2. **Microcontroller**:
   - Raspberry Pi 3 B
3. **Communication Protocols**:
   - MQTT for data transmission between sensors and cloud services.
   - REST API for cloud integration with ThingSpeak.
4. **User Interface**:
   - Telegram Bot for real-time notifications and user interaction.
   - Node-RED dashboard for visualizing data.
5. **Cloud Services**:
   - ThingSpeak for storing and analyzing data.


## How to Set Up the Smart Plant Care System

### Hardware Requirements

- Raspberry Pi 3 B
- Soil Moisture Sensor
- DHT11 Sensor (Temperature and Humidity)
- LEDs for system status indication
- Breadboard and Jumper Wires

