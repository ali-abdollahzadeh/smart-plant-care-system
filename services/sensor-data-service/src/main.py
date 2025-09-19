import os, json, math, signal, logging, uuid, time   # add time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
import requests
from datetime import datetime

class SensorDataService:
    def __init__(self):
        self.broker_host = os.getenv("MQTT_HOST", "mqtt-broker")
        self.broker_port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic = os.getenv("TOPIC", "smartplant/+/telemetry")

        influx_url = os.getenv("INFLUX_URL", "http://influxdb:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN", "my-token")
        self.influx_org = os.getenv("INFLUX_ORG", "smartplant")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "telemetry")

        self.catalogue_url = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")

        self.influx_client = InfluxDBClient(url=influx_url, token=self.influx_token, org=self.influx_org)
        # use synchronous write API so we can pass precision explicitly per point
        self.write_api = self.influx_client.write_api()

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, 60)

        self.instance_id = str(uuid.uuid4())
        self.running = True
        self._register_service()

        import threading
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _register_service(self):
        data = {
            "name": "sensor-data-service",
            "version": "1.0.0",
            "instance_id": self.instance_id,
            "host": "sensor-data-service",
            "port": 0,
            "health_url": "N/A",
            "capabilities": ["influx_writer"],
            "topics_pub": [],
            "topics_sub": [self.topic]
        }
        url = f"{self.catalogue_url}/services/register"
        for _ in range(5):
            try:
                res = requests.post(url, json=data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info("Registered sensor-data-service with catalogue")
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
        logging.info(f"SensorDataService connected to MQTT (rc={rc})")
        client.subscribe(self.topic)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            logging.error(f"Failed to parse telemetry JSON: {e}")
            return

        plant_id = str(payload.get("plant_id", ""))
        sensor = str(payload.get("sensor", ""))
        value = payload.get("value", None)

        if sensor not in ["temperature", "humidity", "soil_moisture"]:
            return
        try:
            value = float(value)
        except:
            logging.warning("Non-numeric sensor value received, skipping")
            return
        if not math.isfinite(value):
            logging.warning("Infinite/NaN value received, skipping")
            return

        ts_str = payload.get("ts")
        if ts_str:
            try:
                # Accepts 'YYYY-MM-DDTHH:MM:SSZ' or offset-naive; convert to UTC naive
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                dt = datetime.utcnow()
        else:
            dt = datetime.utcnow()

        point = (
            Point("telemetry")
            .tag("plant_id", plant_id)
            .tag("sensor", sensor)
            .field("value", value)
            .time(dt, WritePrecision.S)
        )
        try:
            self.write_api.write(bucket=self.influx_bucket, org=self.influx_org, record=point)
        except Exception as e:
            logging.warning(f"Failed to write to InfluxDB: {e}")

    def run(self):
        self.client.loop_start()
        # Keep running until signaled to stop
        while self.running:
            time.sleep(1)

    def _handle_signal(self, signum, frame):
        logging.info("SensorDataService shutting down")
        self.running = False
        try:
            requests.delete(f"{self.catalogue_url}/services/{self.instance_id}", timeout=5)
        except Exception as e:
            logging.warning(f"Deregister failed: {e}")
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    service = SensorDataService()
    service.run()
