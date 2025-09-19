from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Assignment

class AssignmentRepository:
    def create(self, db: Session, user_id: int, plant_id: int) -> Assignment:
        a = Assignment(user_id=user_id, plant_id=plant_id)
        db.add(a)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            a = db.query(Assignment).filter_by(user_id=user_id, plant_id=plant_id).first()
        return a

    def list_for_user(self, db: Session, user_id: int):
        return db.query(Assignment).filter_by(user_id=user_id).all()
