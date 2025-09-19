from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Index,
    func, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .db import Base

# Users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    chat_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    assignments = relationship("Assignment", back_populates="user", cascade="all, delete-orphan")

# Plants
class Plant(Base):
    __tablename__ = "plants"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    thresholds = relationship("Threshold", back_populates="plant", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="plant", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="plant", cascade="all, delete-orphan")

# Assignments (user ↔ plant)
class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="assignments")
    plant = relationship("Plant", back_populates="assignments")

# Thresholds
class Threshold(Base):
    __tablename__ = "thresholds"
    id = Column(Integer, primary_key=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=True)
    plant_type = Column(String, nullable=True)
    sensor = Column(String, nullable=False)
    min_val = Column(Float, nullable=True)
    max_val = Column(Float, nullable=True)
    hysteresis = Column(Float, nullable=True, server_default=text("0.0"))
    plant = relationship("Plant", back_populates="thresholds")

Index("ix_thresholds_sensor", Threshold.sensor)

# Alerts
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    sensor = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    severity = Column(String, nullable=False, server_default=text("'warning'"))
    ts = Column(DateTime(timezone=True), server_default=text("now()"))
    note = Column(Text, nullable=True)
    plant = relationship("Plant", back_populates="alerts")

Index("ix_alerts_plant_ts", Alert.plant_id, Alert.ts.desc())

# Service Registry
class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    instance_id = Column(String, unique=True, nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    health_url = Column(String, nullable=False)
    capabilities = Column(JSONB, nullable=True)
    topics_pub = Column(JSONB, nullable=True)
    topics_sub = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, server_default=text("'healthy'"))
    last_seen = Column(DateTime(timezone=True), server_default=text("now()"))

Index("ix_services_name", Service.name)
Index("ix_services_last_seen", Service.last_seen)
