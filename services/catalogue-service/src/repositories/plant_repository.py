from sqlalchemy.orm import Session
from ..models import Plant

class PlantRepository:
    def create(self, db: Session, name: str, type: str | None):
        p = Plant(name=name, type=type)
        db.add(p); db.flush()
        return p

    def list(self, db: Session):
        return db.query(Plant).all()

    def get(self, db: Session, plant_id: int):
        return db.get(Plant, plant_id)
