from sqlalchemy.orm import Session
from ..models import Alert

class AlertRepository:
    def create(self, db: Session, **kwargs):
        a = Alert(**kwargs)
        db.add(a); db.flush()
        return a

    def list_by_plant(self, db: Session, plant_id: int | None):
        q = db.query(Alert)
        if plant_id is not None:
            q = q.filter(Alert.plant_id == plant_id)
        return q.order_by(Alert.ts.desc()).all()
