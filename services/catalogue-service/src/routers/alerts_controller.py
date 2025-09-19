from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.alert_repository import AlertRepository
from ..schemas import AlertCreate, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])
repo = AlertRepository()

@router.post("", response_model=AlertRead)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    with db.begin():
        return repo.create(db, **payload.model_dump())

@router.get("", response_model=list[AlertRead])
def list_alerts(plant_id: int | None = None, db: Session = Depends(get_db)):
    return repo.list_by_plant(db, plant_id=plant_id)
