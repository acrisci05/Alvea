# schemas.py - Schemi Pydantic (v2) di richiesta/risposta.
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


# --- Auth ---
class CaregiverCreate(BaseModel):
    username: str
    password: str
    # Ruolo opzionale in fase di registrazione (default: caregiver).
    role: Literal["caregiver", "medico"] = "caregiver"

class CaregiverResponse(BaseModel):
    id: int
    username: str
    role: str
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
    owner_id: Optional[int]
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
    device_id: str           # paziente
    ts: datetime             # timestamp
    parameter: Optional[str] # parametro: bpm | temperature | contact
    kind: str
    severity: str            # livello di gravità
    message: str             # descrizione
    value: Optional[float]
    class Config:
        from_attributes = True


# --- Soglie cliniche per-device (configurabili dal medico) ---
class ThresholdConfig(BaseModel):
    bpm_warn_low: int
    bpm_warn_high: int
    bpm_crit_low: int
    bpm_crit_high: int
    temp_warn_low: float
    temp_warn_high: float
    temp_crit_low: float
    temp_crit_high: float

class ThresholdResponse(ThresholdConfig):
    device_id: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    class Config:
        from_attributes = True


# --- Scheda paziente / anamnesi ---
class PatientRecordUpdate(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    weight_kg: Optional[float] = None
    blood_type: Optional[str] = None
    pathologies: Optional[str] = None
    medications: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None

class PatientRecordResponse(PatientRecordUpdate):
    device_id: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    class Config:
        from_attributes = True


# --- Audit log ---
class AuditLogResponse(BaseModel):
    id: int
    ts: datetime
    username: Optional[str]
    role: Optional[str]
    action: str
    resource: Optional[str]
    detail: Optional[str]
    ip: Optional[str]
    class Config:
        from_attributes = True
