import os, json, logging, signal, threading, uuid
import requests
import paho.mqtt.client as mqtt
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from fastapi import FastAPI, Request
import uvicorn
import time

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        allowed_ids = os.getenv("ALLOWED_CHAT_IDS", "")
        self.allowed_ids = [int(x) for x in allowed_ids.split(",") if x] if allowed_ids else []
        self.catalogue_url = os.getenv("CATALOGUE_URL", "http://catalogue-service:8000")
        mqtt_host = os.getenv("MQTT_HOST", "mqtt-broker")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        # Latest sensor readings
        self.latest = {}  # {plant_id: {sensor: {"value": ..., "ts": ...}}}
        # Load plant info
        self.plant_names = {}
        try:
            res = requests.get(f"{self.catalogue_url}/plants", timeout=5)
            plants = res.json() if res.status_code == 200 else []
            for p in plants:
                self.plant_names[p['id']] = p['name']
        except Exception as e:
            logging.error(f"Could not load plants: {e}")
        # Load initial thresholds
        self.thresholds = {}
        try:
            res = requests.get(f"{self.catalogue_url}/thresholds?plant_id=1", timeout=5)
            thr_list = res.json() if res.status_code == 200 else []
            for t in thr_list:
                sensor = t['sensor']
                self.thresholds[sensor] = t
        except Exception as e:
            logging.error(f"Could not load thresholds: {e}")
        # MQTT client for telemetry subscribe and command publish
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
        self.mqtt_client.loop_start()
        # Service registry registration
        self.instance_id = str(uuid.uuid4())
        self.running = True
        self._register_service()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # Webhook server for receiving notifications
        self.webhook_app = FastAPI()
        self._setup_webhook_routes()
        threading.Thread(target=self._run_webhook_server, daemon=True).start()
        
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ---------- small HTML escaper to keep UI safe ----------
    @staticmethod
    def _h(text):
        s = "" if text is None else str(text)
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _register_service(self):
        data = {
            "name": "telegram-service",
            "version": "1.0.0",
            "instance_id": self.instance_id,
            "host": "telegram-service",
            "port": 0,
            "health_url": "N/A",
            "capabilities": ["telegram_bot", "notify_alerts", "publish_commands"],
            "topics_pub": [f"smartplant/1/actuators/water/set"],
            "topics_sub": [f"smartplant/+/telemetry"]
        }
        url = f"{self.catalogue_url}/services/register"
        for _ in range(5):
            try:
                res = requests.post(url, json=data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info("Registered telegram-service with catalogue")
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
        logging.info("TelegramService MQTT connected")
        client.subscribe("smartplant/+/telemetry")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception:
            return
        plant_id = str(payload.get("plant_id", ""))
        sensor = payload.get("sensor")
        value = payload.get("value")
        ts = payload.get("ts")
        if plant_id not in self.latest:
            self.latest[plant_id] = {}
        # If timestamp missing, use now
        if not ts:
            from datetime import datetime
            ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.latest[plant_id][sensor] = {"value": value, "ts": ts}

    def _setup_webhook_routes(self):
        """Setup webhook routes for receiving notifications"""
        @self.webhook_app.post("/webhook/alert")
        async def webhook_alert(request: Request):
            try:
                data = await request.json()
                plant_id = data.get("plant_id")
                sensor = data.get("sensor")
                value = data.get("value")
                severity = data.get("severity", "warning")
                
                # Send notification to all allowed users (currently logs only)
                await self._send_alert_notification(plant_id, sensor, value, severity)
                return {"status": "success"}
            except Exception as e:
                logging.error(f"Webhook alert error: {e}")
                return {"status": "error", "message": str(e)}

    async def _send_alert_notification(self, plant_id, sensor, value, severity):
        """Send alert notification to Telegram users (currently logs to INFO)"""
        try:
            # Get plant name
            try:
                plant_name = self.plant_names.get(int(plant_id), f"Plant {plant_id}")
            except Exception:
                plant_name = f"Plant {plant_id}"
            
            # Pretty message (HTML-safe)
            emoji = "🌡️" if sensor == "temperature" else "💧" if sensor == "humidity" else "🌱"
            severity_tag = "🚨 CRITICAL" if severity == "critical" else "⚠️ WARNING"
            message = (
                f"<b>{severity_tag}</b>\n\n"
                f"{emoji} <b>{self._h(sensor).replace('_',' ').title()}</b>: <code>{self._h(value)}</code>\n"
                f"🌱 <b>Plant</b>: <code>{self._h(plant_name)}</code>\n"
                f"⚠️ <b>Severity</b>: <code>{self._h(severity.title())}</code>\n\n"
                f"Check your plant's condition and take appropriate action."
            )
            # Currently we log (your original logic)
            for chat_id in self.allowed_ids:
                try:
                    logging.info(f"[Alert to {chat_id}] {message}")
                except Exception as e:
                    logging.error(f"Failed to send alert to chat {chat_id}: {e}")
                    
        except Exception as e:
            logging.error(f"Failed to send alert notification: {e}")

    def _run_webhook_server(self):
        """Run the webhook server in a separate thread"""
        try:
            uvicorn.run(self.webhook_app, host="0.0.0.0", port=8001, log_level="info")
        except Exception as e:
            logging.error(f"Webhook server error: {e}")

    def run(self):
        if not self.bot_token:
            logging.error("No Telegram bot token provided. Exiting.")
            return
        application = ApplicationBuilder().token(self.bot_token).build()

        # --------- Global error handler (logs cleanly) ---------
        async def on_error(update: object, context):
            logging.exception("Handler error: %s", getattr(context, "error", None))
        application.add_error_handler(on_error)
        # -------------------------------------------------------

        # Define command handlers (using closure to access self)
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            
            # Create or get user
            chat_id = str(update.effective_chat.id)
            user_name = update.effective_user.first_name or "User"
            try:
                user_data = {"name": user_name, "chat_id": chat_id}
                res = requests.post(f"{self.catalogue_url}/users", json=user_data, timeout=5)
                if res.status_code in (200, 201):
                    logging.info(f"User created/retrieved: {user_name} (chat_id: {chat_id})")
                else:
                    logging.warning(f"Failed to create user: {res.status_code}")
            except Exception as e:
                logging.warning(f"Error creating user: {e}")
            
            msg = (
                "<b>🌿 Smart Plant Care</b>\n\n"
                "Welcome! Use these commands:\n"
                "/status — Show plant status\n"
                "/latest — Latest sensor readings\n"
                " /thresholds — View alert thresholds\n"
                "/set_threshold &lt;sensor&gt; &lt;min&gt; [max] — Update threshold\n"
                "/water &lt;amount_ml&gt; — Water the plant\n"
                "/light &lt;amount_percent&gt; — Control light intensity\n"
                "/help — Show this help"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            plant_id = "1"
            # Safe plant name
            try:
                plant_name_raw = self.plant_names.get(int(plant_id), f"Plant {plant_id}")
            except Exception:
                plant_name_raw = f"Plant {plant_id}"
            plant_name = self._h(plant_name_raw)

            if plant_id not in self.latest or not self.latest[plant_id]:
                await update.message.reply_text(
                    f"🌱 <b>{plant_name}</b>\nNo data available yet.",
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                return

            lines = []
            for sensor, latest in self.latest.get(plant_id, {}).items():
                val = latest.get("value")
                unit = ""
                icon = "🌡️" if sensor == "temperature" else "💧" if sensor == "humidity" else "📟"
                if sensor == "temperature":
                    unit = "°C"
                elif sensor == "humidity":
                    unit = "%"
                status_tag = ""
                thr = self.thresholds.get(sensor)
                fval = None
                try:
                    fval = float(val)
                except Exception:
                    pass
                if thr and fval is not None:
                    min_val = thr.get("min_val"); max_val = thr.get("max_val")
                    if min_val is not None and fval < float(min_val):
                        status_tag = " 🔻 <i>LOW</i>"
                    elif max_val is not None and fval > float(max_val):
                        status_tag = " 🔺 <i>HIGH</i>"
                    else:
                        status_tag = " ✅ <i>OK</i>"

                lines.append(
                    f"{icon} <b>{self._h(sensor).title()}</b>: "
                    f"<code>{self._h(val)}</code>{self._h(unit)}{status_tag}"
                )

            text = f"🌱 <b>{plant_name}</b> — <u>Status</u>\n" + "\n".join(lines)
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            plant_id = "1"
            readings = self.latest.get(plant_id, {})
            if not readings:
                await update.message.reply_text("No sensor readings yet.", parse_mode=ParseMode.HTML)
                return

            lines = []
            for sensor, latest in readings.items():
                lines.append(
                    f"• <b>{self._h(sensor).title()}</b>: "
                    f"<code>{self._h(latest.get('value'))}</code> "
                    f"<i>(at {self._h(latest.get('ts'))})</i>"
                )

            alert_msg = "No recent alerts."
            try:
                res = requests.get(f"{self.catalogue_url}/alerts?plant_id={plant_id}", timeout=5)
                alerts = res.json() if res.status_code == 200 else []
                if alerts:
                    a0 = alerts[0]
                    alert_msg = (
                        f"Last alert: <b>{self._h(a0.get('sensor'))}</b> "
                        f"<i>at {self._h(a0.get('ts'))}</i>"
                    )
            except Exception:
                pass

            text = "<b>🕒 Latest readings</b>\n" + "\n".join(lines) + "\n\n" + alert_msg
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        async def thresholds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            if not self.thresholds:
                await update.message.reply_text("No thresholds set.", parse_mode=ParseMode.HTML)
                return

            lines = []
            for sensor, thr in self.thresholds.items():
                min_val = thr.get("min_val"); max_val = thr.get("max_val")
                parts = []
                if min_val is not None:
                    parts.append(f"min=<code>{self._h(min_val)}</code>")
                if max_val is not None:
                    parts.append(f"max=<code>{self._h(max_val)}</code>")
                if not parts:
                    parts.append("No threshold")
                lines.append(f"• <b>{self._h(sensor).title()}</b>: " + ", ".join(parts))

            await update.message.reply_text(
                "<b>📏 Thresholds</b>\n" + "\n".join(lines),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        async def set_threshold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            text = update.message.text.strip()
            parts = text.split()
            if len(parts) < 3:
                await update.message.reply_text(
                    "Usage: <code>/set_threshold &lt;sensor&gt; &lt;min&gt; [max]</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            _, sensor, min_str, *rest = parts
            try:
                min_val = float(min_str)
            except:
                await update.message.reply_text("Invalid <b>min</b> value.", parse_mode=ParseMode.HTML)
                return
            max_val = None
            if rest:
                try:
                    max_val = float(rest[0])
                except:
                    await update.message.reply_text("Invalid <b>max</b> value.", parse_mode=ParseMode.HTML)
                    return
            data = {"plant_id": 1, "sensor": sensor, "min_val": min_val}
            if max_val is not None:
                data["max_val"] = max_val
            try:
                res = requests.post(f"{self.catalogue_url}/thresholds", json=data, timeout=5)
                if res.status_code == 200:
                    new_thr = res.json()
                    self.thresholds[sensor] = new_thr
                    reply = f"✅ Threshold for <b>{self._h(sensor)}</b> updated."
                else:
                    reply = "❌ Failed to update threshold."
            except Exception as e:
                reply = f"❌ Error: <code>{self._h(e)}</code>"
            await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

        async def water_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            text = update.message.text.strip()
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "Usage: <code>/water &lt;amount_ml&gt;</code>",
                    parse_mode=ParseMode.HTML
                )
                return
            try:
                amount = float(parts[1])
            except:
                await update.message.reply_text("Invalid <b>amount</b>.", parse_mode=ParseMode.HTML)
                return
            topic = f"smartplant/1/actuators/water/set"
            payload = {"device": "water", "amount": amount, "note": "manual"}
            try:
                self.mqtt_client.publish(topic, json.dumps(payload))
                reply = f"💧 Watering <b>{self._h(amount)}</b> ml initiated."
            except Exception as e:
                reply = f"❌ Failed to send water command: <code>{self._h(e)}</code>"
            await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

        async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.allowed_ids and update.effective_chat.id not in self.allowed_ids:
                return
            text = update.message.text.strip()
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "Usage: <code>/light &lt;amount_percent&gt;</code>",
                    parse_mode=ParseMode.HTML
                )
                return
            try:
                amount = float(parts[1])
            except:
                await update.message.reply_text("Invalid <b>amount</b>.", parse_mode=ParseMode.HTML)
                return
            topic = f"smartplant/1/actuators/light/set"
            payload = {"device": "light", "amount": amount, "note": "manual"}
            try:
                self.mqtt_client.publish(topic, json.dumps(payload))
                reply = f"💡 Light <b>{self._h(amount)}</b>% initiated."
            except Exception as e:
                reply = f"❌ Failed to send light command: <code>{self._h(e)}</code>"
            await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await start_command(update, context)

        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("latest", latest_command))
        application.add_handler(CommandHandler("thresholds", thresholds_command))
        application.add_handler(CommandHandler("set_threshold", set_threshold_command))
        application.add_handler(CommandHandler("water", water_command))
        application.add_handler(CommandHandler("light", light_command))
        application.add_handler(CommandHandler("help", help_command))

        # Run the bot
        application.run_polling()

    def _handle_signal(self, signum, frame):
        logging.info("TelegramService shutting down")
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
    service = TelegramService()
    service.run()
