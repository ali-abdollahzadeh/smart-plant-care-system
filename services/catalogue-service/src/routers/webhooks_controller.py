from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.alert_repository import AlertRepository
from ..repositories.users_repository import UserRepository
import logging

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
alert_repo = AlertRepository()
user_repo = UserRepository()

@router.post("/alert")
def webhook_alert(payload: dict, db: Session = Depends(get_db)):
    """Webhook endpoint for alert notifications"""
    try:
        plant_id = payload.get("plant_id")
        sensor = payload.get("sensor")
        value = payload.get("value")
        severity = payload.get("severity", "warning")
        
        # Get users assigned to this plant
        assignments = db.query(Assignment).filter(Assignment.plant_id == plant_id).all()
        
        for assignment in assignments:
            user = user_repo.get(db, assignment.user_id)
            if user and user.chat_id:
                # Send notification to Telegram
                send_telegram_notification(user.chat_id, plant_id, sensor, value, severity)
        
        return {"status": "success", "message": "Alert notifications sent"}
        
    except Exception as e:
        logging.error(f"Webhook alert error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def send_telegram_notification(chat_id, plant_id, sensor, value, severity):
    """Send notification to Telegram user"""
    try:
        # Get plant name
        plant_name = f"Plant {plant_id}"  # Default name
        
        # Format message
        emoji = "🌡️" if sensor == "temperature" else "💧" if sensor == "humidity" else "🌱"
        severity_emoji = "⚠️" if severity == "warning" else "🚨"
        
        message = f"""
{severity_emoji} *Plant Alert*

{emoji} **{sensor.replace('_', ' ').title()}**: {value}
🌱 **Plant**: {plant_name}
⚠️ **Severity**: {severity.title()}

Check your plant's condition and take appropriate action.
        """.strip()
        
        # Send to telegram service (this would be implemented in telegram service)
        # For now, just log the notification
        logging.info(f"Telegram notification for chat {chat_id}: {message}")
        
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")

# Import Assignment model
from ..models import Assignment
