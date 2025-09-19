# services/catalogue-service/src/repositories/threshold_repository.py
from sqlalchemy.orm import Session
from ..models import Threshold

class ThresholdRepository:
    def create(self, db: Session, **kwargs) -> Threshold:
        t = Threshold(**kwargs)
        db.add(t)
        db.flush()  # ensures ID is populated before returning
        return t

    def list(
        self,
        db: Session,
        plant_id: int | None = None,
        plant_type: str | None = None,
    ) -> list[Threshold]:
        q = db.query(Threshold)
        if plant_id is not None:
            q = q.filter(Threshold.plant_id == plant_id)
        if plant_type is not None:
            q = q.filter(Threshold.plant_type == plant_type)
        return q.all()
