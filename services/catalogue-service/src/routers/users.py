from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.users_repository import UserRepository
from ..schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])
repo = UserRepository()

@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    with db.begin():
        if payload.chat_id:
            existing = repo.get_by_chat_id(db, payload.chat_id)
            if existing:
                return existing
        return repo.create(db, name=payload.name, chat_id=payload.chat_id)

@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return repo.list(db)
