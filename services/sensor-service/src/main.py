import os, json, time, signal, logging, uuid
import paho.mqtt.client as mqtt
import requests
from sensors import MQTTPublisher, RealSensorReader
from simulator import ComplexSimulator

class SensorService:
    def __init__(self):
        # Config from env
        self.plant_id = os.getenv("PLANT_ID", "1")
        self.mode = os.getenv("MODE", "auto").lower()
        self.interval = int(os.getenv("INTERVAL", "5"))
        mqtt_host = os.getenv("MQTT_HOST", "mqtt-broker")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.catalogue_url = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")
        # Determine mode (auto -> use real if possible, else simulate)
        dht_pin = os.getenv("DHT_PIN")
        dht_model = os.getenv("DHT_MODEL", "DHT22")
        use_real = False
        if self.mode == "real":
            use_real = True
        elif self.mode == "simulate":
            use_real = False
        else:  # auto
            if dht_pin and RealSensorReader:  # if sensor libs loaded and pin provided
                use_real = True
            else:
                use_real = False
        # Instantiate sensor source
        if use_real:
            try:
                pin = int(dht_pin) if dht_pin else None
            except:
                pin = None
            self.reader = RealSensorReader(plant_id=self.plant_id, dht_pin=pin, dht_model=dht_model)
            self.mode = "real"
            logging.info("SensorService in REAL mode")
        else:
            self.reader = ComplexSimulator(plant_id=self.plant_id)
            self.mode = "simulate"
            logging.info("SensorService in SIMULATE mode")
        # MQTT publisher for telemetry
        self.publisher = MQTTPublisher(mqtt_host, mqtt_port)
        self.publisher.connect()
        # MQTT subscriber for actuator commands
        self.cmd_client = mqtt.Client()
        self.cmd_client.on_connect = self._on_connect
        self.cmd_client.on_message = self._on_message
        self.cmd_client.connect(mqtt_host, mqtt_port, 60)
        # Service registry info
        self.instance_id = str(uuid.uuid4())
        self.running = True
        # Register service with catalogue
        self._register_service()
        # Start heartbeat thread
        import threading
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _register_service(self):
        data = {
            "name": "sensor-service",
            "version": "1.0.0",
            "instance_id": self.instance_id,
            "host": "sensor-service",
            "port": 0,
            "health_url": "N/A",
            "capabilities": ["sensing", "publishing_telemetry", "receiving_commands"],
            "topics_pub": [f"smartplant/{self.plant_id}/telemetry"],
            "topics_sub": [f"smartplant/{self.plant_id}/actuators/+/set"]
        }
        url = f"{self.catalogue_url}/services/register"
        for _ in range(5):
            try:
                res = requests.post(url, json=data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info("Registered service with catalogue")
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
        logging.info(f"Command MQTT connected (rc={rc})")
        # Subscribe to actuator command topic for this plant
        cmd_topic = f"smartplant/{self.plant_id}/actuators/+/set"
        client.subscribe(cmd_topic)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            logging.warning(f"Invalid command payload: {e}")
            return
        device = payload.get("device")
        amount = payload.get("amount")
        logging.info(f"Received command for device {device}: {payload}")
        # Only handle watering commands in simulate mode
        if self.mode != "real" and device == "water":
            try:
                amt = float(amount) if amount is not None else 0.0
            except:
                amt = 0.0
            if hasattr(self.reader, 'water'):
                logging.info(f"Applying water: {amt}ml to simulated soil")
                self.reader.water(amt)
        # (Real mode: no action or hardware integration could be added here)

    def run(self):
        # Start command subscriber loop
        self.cmd_client.loop_start()
        telemetry_topic = f"smartplant/{self.plant_id}/telemetry"
        try:
            while self.running:
                # Read sensor values and publish
                if self.mode == "simulate":
                    temp = self.reader.read_temperature()
                    hum = self.reader.read_humidity()
                    soil = self.reader.read_soil_moisture()
                else:  # real
                    temp = getattr(self.reader, "read_temperature", lambda: None)()
                    hum = getattr(self.reader, "read_humidity", lambda: None)()
                    soil = getattr(self.reader, "read_soil_moisture", lambda: None)()
                ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                if temp is not None:
                    data = {"plant_id": self.plant_id, "sensor": "temperature", "value": temp, "ts": ts}
                    self.publisher.client.publish(telemetry_topic, json.dumps(data))
                if hum is not None:
                    data = {"plant_id": self.plant_id, "sensor": "humidity", "value": hum, "ts": ts}
                    self.publisher.client.publish(telemetry_topic, json.dumps(data))
                if soil is not None:
                    data = {"plant_id": self.plant_id, "sensor": "soil_moisture", "value": soil, "ts": ts}
                    self.publisher.client.publish(telemetry_topic, json.dumps(data))
                time.sleep(self.interval)
        finally:
            # Graceful shutdown if loop exits
            self._shutdown()

    def _handle_signal(self, signum, frame):
        logging.info("Shutdown signal received")
        self.running = False

    def _shutdown(self):
        # Deregister service
        try:
            requests.delete(f"{self.catalogue_url}/services/{self.instance_id}", timeout=5)
        except Exception as e:
            logging.warning(f"Service deregistration failed: {e}")
        # Stop MQTT clients
        try:
            self.cmd_client.loop_stop()
            self.cmd_client.disconnect()
        except Exception:
            pass
        try:
            self.publisher.client.disconnect()
        except Exception:
            pass
        logging.info("SensorService shut down")

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    service = SensorService()
    service.run()
