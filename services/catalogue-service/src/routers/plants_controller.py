from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.plant_repository import PlantRepository
from ..schemas import PlantCreate, PlantRead

router = APIRouter(prefix="/plants", tags=["plants"])
repo = PlantRepository()

@router.post("", response_model=PlantRead)
def create_plant(payload: PlantCreate, db: Session = Depends(get_db)):
    with db.begin():
        return repo.create(db, name=payload.name, type=payload.type)

@router.get("", response_model=list[PlantRead])
def list_plants(db: Session = Depends(get_db)):
    return repo.list(db)

@router.get("/{plant_id}", response_model=PlantRead)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    p = repo.get(db, plant_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plant not found")
    return p
