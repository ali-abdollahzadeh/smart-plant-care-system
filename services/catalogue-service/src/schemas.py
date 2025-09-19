from pydantic import BaseModel, Field
from typing import Optional, List

class _Config(BaseModel):
    model_config = dict(from_attributes=True)

# Plants
class PlantCreate(BaseModel):
    name: str
    type: Optional[str] = None

class PlantRead(_Config):
    id: int
    name: str
    type: Optional[str] = None

# Thresholds
class ThresholdCreate(BaseModel):
    plant_id: Optional[int] = None
    plant_type: Optional[str] = None
    sensor: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    hysteresis: Optional[float] = 0.0

class ThresholdRead(_Config):
    id: int
    plant_id: Optional[int] = None
    plant_type: Optional[str] = None
    sensor: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    hysteresis: Optional[float] = 0.0

# Alerts
class AlertCreate(BaseModel):
    plant_id: int
    sensor: str
    value: float
    severity: Optional[str] = "warning"
    note: Optional[str] = None

class AlertRead(_Config):
    id: int
    plant_id: int
    sensor: str
    value: float
    severity: str
    note: Optional[str] = None

# Service registry
class ServiceRegister(BaseModel):
    name: str
    version: str
    instance_id: str
    host: str
    port: int
    health_url: str
    capabilities: List[str]
    topics_pub: Optional[List[str]] = None
    topics_sub: Optional[List[str]] = None

class ServiceHeartbeat(BaseModel):
    instance_id: str
    status: str
    ts: str  # RFC3339 string

class ServiceRead(_Config):
    id: int
    name: str
    version: str
    instance_id: str
    host: str
    port: int
    health_url: str
    capabilities: list | None = None
    topics_pub: list | None = None
    topics_sub: list | None = None
    status: str

# Users & Assignments
class UserCreate(BaseModel):
    name: str
    chat_id: Optional[str] = None

class UserRead(_Config):
    id: int
    name: str
    chat_id: Optional[str] = None

class AssignmentCreate(BaseModel):
    user_id: int
    plant_id: int

class AssignmentRead(_Config):
    id: int
    user_id: int
    plant_id: int
