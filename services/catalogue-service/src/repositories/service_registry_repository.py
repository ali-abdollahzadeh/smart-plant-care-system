from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import Service

class ServiceRegistryRepository:
    def register(self, db: Session, payload: dict) -> Service:
        instance_id = payload["instance_id"]
        s = db.query(Service).filter(Service.instance_id == instance_id).first()
        if s:
            # update on re-register
            for k, v in payload.items():
                if hasattr(s, k):
                    setattr(s, k, v)
        else:
            s = Service(**payload)
            db.add(s)
        s.last_seen = datetime.now(timezone.utc)
        s.status = "healthy"
        db.flush()
        return s

    def heartbeat(self, db: Session, instance_id: str, status: str) -> Service | None:
        s = db.query(Service).filter(Service.instance_id == instance_id).first()
        if not s:
            return None
        s.status = status
        s.last_seen = datetime.now(timezone.utc)
        db.flush()
        return s

    def list(self, db: Session, name: str | None = None, status: str | None = None):
        q = db.query(Service)
        if name:
            q = q.filter(Service.name == name)
        if status:
            q = q.filter(Service.status == status)
        return q.order_by(Service.last_seen.desc()).all()

    def delete(self, db: Session, instance_id: str) -> bool:
        s = db.query(Service).filter(Service.instance_id == instance_id).first()
        if not s:
            return False
        db.delete(s); db.flush()
        return True
