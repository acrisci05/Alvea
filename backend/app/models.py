# models.py - Modelli ORM. Schema dati persistente di PulseGuard-Baby.
#
# Caregiver 1--N Device 1--N Reading
#                       Device 1--N Alert
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Caregiver(Base):
    """Genitore/operatore che usa l'app."""
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    devices = relationship("Device", back_populates="owner")


class Device(Base):
    """La fascia indossabile associata a un neonato."""
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)  # es. PULSEGUARD_BABY_04
    baby_name = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("caregivers.id"))
    owner = relationship("Caregiver", back_populates="devices")
    readings = relationship("Reading", back_populates="device")
    alerts = relationship("Alert", back_populates="device")


class Reading(Base):
    """Singola lettura di telemetria (1 Hz)."""
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    bpm = Column(Float)
    temperature = Column(Float)
    sensor_contact = Column(Boolean)
    source = Column(String, nullable=True)         # "sim" | "ad8232"
    device = relationship("Device", back_populates="readings")


class Alert(Base):
    """Allarme generato dalla valutazione delle soglie."""
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    kind = Column(String)          # "bpm_high" | "bpm_low" | "temp_high" | ...
    severity = Column(String)      # "warning" | "critical" | "technical"
    message = Column(String)
    value = Column(Float, nullable=True)
    device = relationship("Device", back_populates="alerts")
