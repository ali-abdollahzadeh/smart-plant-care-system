import os, json, time, signal, logging, uuid
import paho.mqtt.client as mqtt
import requests
from influxdb_client import InfluxDBClient, QueryApi

class RulesEngine:
    def __init__(self):
        # Track alert state per (plant_id, sensor) for hysteresis
        self.states = {}

    def evaluate(self, plant_id: str, sensor: str, value: float, thresholds: list[dict]):
        # Ensure state record exists
        key = (plant_id, sensor)
        if key not in self.states:
            self.states[key] = {"low": False, "high": False}
        state = self.states[key]
        for t in thresholds:
            min_val = t.get("min_val")
            max_val = t.get("max_val")
            hyst = t.get("hysteresis") or 0.0
            # Low threshold check
            if min_val is not None:
                if value < min_val and not state["low"]:
                    state["low"] = True
                    state["high"] = False
                    return True, "warning"
                # Reset low alert state when value rises above min + hysteresis
                if state["low"] and value > (min_val + hyst):
                    state["low"] = False
            # High threshold check
            if max_val is not None:
                if value > max_val and not state["high"]:
                    state["high"] = True
                    state["low"] = False
                    return True, "warning"
                if state["high"] and value < (max_val - hyst):
                    state["high"] = False
        return False, "warning"

class AnalyticsService:
    def __init__(self):
        self.broker_host = os.getenv("MQTT_HOST", "mqtt-broker")
        self.broker_port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic_in = os.getenv("TOPIC_TELEMETRY", "smartplant/+/telemetry")
        self.catalogue_url = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")
        
        # InfluxDB configuration
        influx_url = os.getenv("INFLUX_URL", "http://influxdb:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN", "my-token")
        self.influx_org = os.getenv("INFLUX_ORG", "smartplant")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "telemetry")
        
        # Initialize InfluxDB client
        self.influx_client = InfluxDBClient(url=influx_url, token=self.influx_token, org=self.influx_org)
        self.query_api = self.influx_client.query_api()
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
        self.rules_engine = RulesEngine()
        self.instance_id = str(uuid.uuid4())
        self.running = True
        self._register_service()
        import threading
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _register_service(self):
        data = {
            "name": "analytics-service",
            "version": "1.0.0",
            "instance_id": self.instance_id,
            "host": "analytics-service",
            "port": 0,
            "health_url": "N/A",
            "capabilities": ["rules_engine", "publishing_commands"],
            "topics_pub": ["smartplant/{plant_id}/actuators/water/set"],
            "topics_sub": [self.topic_in]
        }
        url = f"{self.catalogue_url}/services/register"
        for _ in range(5):
            try:
                res = requests.post(url, json=data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info("Registered analytics-service with catalogue")
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
        logging.info(f"AnalyticsService connected to MQTT (rc={rc})")
        client.subscribe(self.topic_in)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            logging.error(f"Failed to parse telemetry: {e}")
            return
        plant_id = str(payload.get("plant_id", ""))
        sensor = str(payload.get("sensor", ""))
        value = payload.get("value", None)
        try:
            value = float(value)
        except:
            return
        # Fetch thresholds for this plant
        thresholds = []
        try:
            res = requests.get(f"{self.catalogue_url}/thresholds?plant_id={plant_id}", timeout=5)
            if res.status_code == 200:
                thresholds = res.json()
                # Filter to relevant sensor
                thresholds = [t for t in thresholds if t.get("sensor") == sensor]
        except Exception as e:
            logging.warning(f"Could not fetch thresholds: {e}")
            return
        if not thresholds:
            return  # no threshold defined for this sensor
        # Evaluate rules (hysteresis applied)
        is_alert, severity = self.rules_engine.evaluate(plant_id, sensor, value, thresholds)
        if is_alert:
            thr = thresholds[0]
            min_val = thr.get("min_val"); max_val = thr.get("max_val")
            trigger_low = False; trigger_high = False
            if min_val is not None and value < (min_val if min_val is not None else float('inf')):
                trigger_low = True
            if max_val is not None and value > (max_val if max_val is not None else float('-inf')):
                trigger_high = True
            # Auto-actuation: water if low soil moisture triggered
            if trigger_low and sensor == "soil_moisture":
                cmd_topic = f"smartplant/{plant_id}/actuators/water/set"
                cmd_payload = {"device": "water", "amount": 200, "note": "auto"}
                client.publish(cmd_topic, json.dumps(cmd_payload))
                logging.info(f"Published auto water command for plant {plant_id}")
            # Log alert to catalogue
            alert_data = {
                "plant_id": int(plant_id) if plant_id else None,
                "sensor": sensor,
                "value": value,
                "severity": severity,
                "note": "auto"
            }
            try:
                res = requests.post(f"{self.catalogue_url}/alerts", json=alert_data, timeout=5)
                if res.status_code in (200, 201):
                    # Send webhook notification to telegram service
                    self._send_webhook_notification(plant_id, sensor, value, severity, alert_data)
            except Exception as e:
                logging.warning(f"Failed to log alert: {e}")

    def _send_webhook_notification(self, plant_id, sensor, value, severity, alert_data):
        """Send webhook notification to telegram service"""
        try:
            webhook_url = f"{self.catalogue_url}/webhooks/alert"
            webhook_data = {
                "plant_id": plant_id,
                "sensor": sensor,
                "value": value,
                "severity": severity,
                "alert_data": alert_data
            }
            requests.post(webhook_url, json=webhook_data, timeout=5)
            logging.info(f"Sent webhook notification for plant {plant_id}")
        except Exception as e:
            logging.warning(f"Failed to send webhook notification: {e}")

    def query_historical_data(self, plant_id, sensor, hours=24):
        """Query historical sensor data from InfluxDB"""
        try:
            query = f'''
            from(bucket: "{self.influx_bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r["_measurement"] == "telemetry")
            |> filter(fn: (r) => r["plant_id"] == "{plant_id}")
            |> filter(fn: (r) => r["sensor"] == "{sensor}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(query, org=self.influx_org)
            data_points = []
            
            for table in result:
                for record in table.records:
                    data_points.append({
                        "time": record.get_time().isoformat(),
                        "value": record.get_value()
                    })
            
            return data_points
        except Exception as e:
            logging.warning(f"Failed to query historical data: {e}")
            return []

    def get_plant_statistics(self, plant_id, hours=24):
        """Get statistical summary for a plant"""
        try:
            sensors = ["temperature", "humidity", "soil_moisture"]
            stats = {}
            
            for sensor in sensors:
                data = self.query_historical_data(plant_id, sensor, hours)
                if data:
                    values = [point["value"] for point in data]
                    stats[sensor] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "count": len(values)
                    }
                else:
                    stats[sensor] = {"min": None, "max": None, "avg": None, "count": 0}
            
            return stats
        except Exception as e:
            logging.warning(f"Failed to get plant statistics: {e}")
            return {}

    def run(self):
        self.mqtt_client.loop_start()
        while self.running:
            time.sleep(1)

    def _handle_signal(self, signum, frame):
        logging.info("AnalyticsService shutting down")
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
    service = AnalyticsService()
    service.run()
