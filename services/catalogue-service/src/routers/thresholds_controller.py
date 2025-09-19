# services/catalogue-service/src/routers/thresholds_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.threshold_repository import ThresholdRepository
from ..schemas import ThresholdCreate, ThresholdRead

router = APIRouter(prefix="/thresholds", tags=["thresholds"])
repo = ThresholdRepository()

@router.post("", response_model=ThresholdRead)
def create_threshold(payload: ThresholdCreate, db: Session = Depends(get_db)):
    with db.begin():
        return repo.create(db, **payload.model_dump())

@router.get("", response_model=list[ThresholdRead])
def list_thresholds(
    plant_id: int | None = None,
    plant_type: str | None = None,
    db: Session = Depends(get_db),
):
    return repo.list(db, plant_id=plant_id, plant_type=plant_type)
