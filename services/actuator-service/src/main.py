import os, json, time, signal, logging, uuid
import paho.mqtt.client as mqtt
import requests

class ActuatorService:
    def __init__(self):
        self.broker_host = os.getenv("MQTT_HOST", "mqtt-broker")
        self.broker_port = int(os.getenv("MQTT_PORT", "1883"))
        self.catalogue_url = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")
        
        # MQTT client for receiving commands
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        # Service registry
        self.instance_id = str(uuid.uuid4())
        self.running = True
        self._register_service()
        
        # Start heartbeat
        import threading
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _register_service(self):
        data = {
            "name": "actuator-service",
            "version": "1.0.0",
            "instance_id": self.instance_id,
            "host": "actuator-service",
            "port": 0,
            "health_url": "N/A",
            "capabilities": ["actuator_control", "hardware_interface"],
            "topics_pub": ["smartplant/+/actuators/+/status"],
            "topics_sub": ["smartplant/+/actuators/+/set"]
        }
        url = f"{self.catalogue_url}/services/register"
        for _ in range(5):
            try:
                res = requests.post(url, json=data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info("Registered actuator-service with catalogue")
                    break
            except Exception as e:
                logging.warning(f"Register service failed (retrying): {e}")
                time.sleep(2)

    def _heartbeat_loop(self):
        url = f"{self.catalogue_url}/services/heartbeat"
        while self.running:
            hb = {"instance_id": self.instance_id, "status": "healthy", "ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
            try:
                requests.post(url, json=hb, timeout=5)
            except Exception as e:
                logging.warning(f"Heartbeat failed: {e}")
            time.sleep(30)

    def _on_connect(self, client, userdata, flags, rc):
        logging.info(f"ActuatorService connected to MQTT (rc={rc})")
        # Subscribe to all actuator command topics
        client.subscribe("smartplant/+/actuators/+/set")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            logging.warning(f"Invalid command payload: {e}")
            return
        
        # Extract topic information
        topic_parts = msg.topic.split('/')
        if len(topic_parts) >= 4:
            try:
                plant_id = topic_parts[1]
                actuator_type = topic_parts[3]
                
                device = payload.get("device")
                amount = payload.get("amount", 0)
                note = payload.get("note", "")
                
                logging.info(f"Received {actuator_type} command for plant {plant_id}: {payload}")
                
                # Process the command
                success = self._process_actuator_command(plant_id, actuator_type, device, amount, note)
                
                # Publish status
                status_topic = f"smartplant/{plant_id}/actuators/{actuator_type}/status"
                status_payload = {
                    "device": device,
                    "amount": amount,
                    "status": "success" if success else "failed",
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    "note": note
                }
                client.publish(status_topic, json.dumps(status_payload))
                
            except Exception as e:
                logging.error(f"Error processing actuator command: {e}")

    def _process_actuator_command(self, plant_id, actuator_type, device, amount, note):
        """Process actuator command - simulate hardware control"""
        try:
            if actuator_type == "water" and device == "water":
                # Simulate watering
                logging.info(f"Watering plant {plant_id} with {amount}ml of water")
                # In a real implementation, this would control actual hardware
                # For now, we just simulate the action
                time.sleep(1)  # Simulate watering time
                return True
            elif actuator_type == "light" and device == "light":
                # Simulate light control
                logging.info(f"Controlling light for plant {plant_id}: {amount}% brightness")
                time.sleep(0.5)  # Simulate light control time
                return True
                
            else:
                logging.warning(f"Unknown actuator type: {actuator_type} or device: {device}")
                return False
                
        except Exception as e:
            logging.error(f"Error processing {actuator_type} command: {e}")
            return False

    def run(self):
        # Connect to MQTT broker with retry
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            try:
                self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
                self.mqtt_client.loop_start()
                logging.info("ActuatorService MQTT connection established")
                break
            except Exception as e:
                retry_count += 1
                logging.warning(f"Failed to connect to MQTT broker (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    logging.error("Max MQTT connection retries exceeded. Exiting.")
                    return
        
        # Main loop
        while self.running:
            time.sleep(1)

    def _handle_signal(self, signum, frame):
        logging.info("ActuatorService shutting down")
        self.running = False
        try:
            requests.delete(f"{self.catalogue_url}/services/{self.instance_id}", timeout=5)
        except Exception as e:
            logging.warning(f"Deregister failed: {e}")
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    service = ActuatorService()
    service.run()
