from sqlalchemy.orm import Session
from datetime import datetime
from ..repositories.service_registry_repository import ServiceRegistryRepository

class ServiceRegistry:
    def __init__(self, db: Session):
        self.repo = ServiceRegistryRepository(db)

    def register_service(self, service_data: dict):
        return self.repo.register(service_data)

    def heartbeat(self, instance_id: str, status: str, ts: datetime):
        return self.repo.update_heartbeat(instance_id, status, ts)

    def list_services(self, name: str = None, status: str = None):
        return self.repo.list_services(name, status)

    def deregister(self, instance_id: str):
        return self.repo.delete(instance_id)
