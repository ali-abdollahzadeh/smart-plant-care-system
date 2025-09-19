from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.assignments_repository import AssignmentRepository
from ..schemas import AssignmentCreate, AssignmentRead

router = APIRouter(prefix="/assignments", tags=["assignments"])
repo = AssignmentRepository()

@router.post("", response_model=AssignmentRead)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db)):
    with db.begin():
        return repo.create(db, user_id=payload.user_id, plant_id=payload.plant_id)
