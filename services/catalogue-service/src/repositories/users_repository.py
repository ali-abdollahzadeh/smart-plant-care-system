from typing import Optional
from sqlalchemy.orm import Session
from ..models import User

class UserRepository:
    def get_by_chat_id(self, db: Session, chat_id: str) -> Optional[User]:
        return db.query(User).filter(User.chat_id == chat_id).first()

    def create(self, db: Session, name: str, chat_id: Optional[str]) -> User:
        user = User(name=name, chat_id=chat_id)
        db.add(user)
        db.flush()
        return user

    def list(self, db: Session, limit: int = 100, offset: int = 0):
        return db.query(User).offset(offset).limit(limit).all()
