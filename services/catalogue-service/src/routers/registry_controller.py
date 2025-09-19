from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..repositories.service_registry_repository import ServiceRegistryRepository
from ..schemas import ServiceRegister, ServiceHeartbeat, ServiceRead

router = APIRouter(prefix="/services", tags=["services"])
repo = ServiceRegistryRepository()

@router.post("/register", response_model=ServiceRead)
def register_service(payload: ServiceRegister, db: Session = Depends(get_db)):
    with db.begin():
        s = repo.register(db, payload.model_dump())
        return s

@router.post("/heartbeat")
def heartbeat(payload: ServiceHeartbeat, db: Session = Depends(get_db)):
    with db.begin():
        s = repo.heartbeat(db, instance_id=payload.instance_id, status=payload.status)
        if not s:
            raise HTTPException(status_code=404, detail="Service not found")
    return {"ok": True}

@router.get("", response_model=list[ServiceRead])
def list_services(name: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    return repo.list(db, name=name, status=status)

@router.delete("/{instance_id}")
def deregister(instance_id: str, db: Session = Depends(get_db)):
    with db.begin():
        ok = repo.delete(db, instance_id=instance_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Service not found")
    return {"deleted": True}
