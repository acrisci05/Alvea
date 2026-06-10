# schemas.py - Schemi Pydantic (v2) di richiesta/risposta.
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# --- Auth ---
class CaregiverCreate(BaseModel):
    username: str
    password: str

class CaregiverResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Device ---
class DeviceCreate(BaseModel):
    device_id: str
    baby_name: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    baby_name: Optional[str]
    owner_id: int
    class Config:
        from_attributes = True


# --- Telemetria / Letture ---
class ReadingIn(BaseModel):
    """Payload prodotto dall'ESP32 (sim o reale)."""
    device_id: str
    timestamp: Optional[float] = None
    bpm: float
    temperature: float
    sensor_contact: bool
    source: Optional[str] = None

class ReadingResponse(BaseModel):
    id: int
    device_id: str
    ts: datetime
    bpm: float
    temperature: float
    sensor_contact: bool
    source: Optional[str]
    class Config:
        from_attributes = True


# --- Alert ---
class AlertResponse(BaseModel):
    id: int
    device_id: str
    ts: datetime
    kind: str
    severity: str
    message: str
    value: Optional[float]
    class Config:
        from_attributes = True
