# schemas.py - Schemi Pydantic (v2) di richiesta/risposta.
#
# Ogni classe definisce la forma dei dati in ingresso (payload ricevuti)
# o in uscita (response mandate all'app). Pydantic valida automaticamente
# i tipi e genera errori HTTP 422 se il payload non è conforme.
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ===================== AUTH =====================

class CaregiverCreate(BaseModel):
    """Dati richiesti per registrare un nuovo account caregiver."""
    username: str
    password: str

class CaregiverResponse(BaseModel):
    """Dati restituiti dopo la registrazione o il login."""
    id: int
    username: str
    class Config:
        from_attributes = True  # permette la creazione da un ORM model SQLAlchemy

class Token(BaseModel):
    """Token JWT restituito dopo il login."""
    access_token: str
    token_type: str = "bearer"


# ===================== DEVICE =====================

class DeviceCreate(BaseModel):
    """Payload per associare una cavigliera all'account caregiver."""
    device_id: str          # es. "ALVEA_04" — identificativo univoco del firmware
    baby_name: Optional[str] = None  # nome del bambino (opzionale, per l'UI)

class DeviceResponse(BaseModel):
    """Device restituito nelle liste e nei dettagli."""
    id: int
    device_id: str
    baby_name: Optional[str]
    owner_id: int
    class Config:
        from_attributes = True


# ===================== TELEMETRIA =====================

class ReadingIn(BaseModel):
    """Payload JSON canonico prodotto dall'ESP32 (simulatore o sensore reale).

    Tutti i campi corrispondono esattamente ai campi pubblicati dal firmware
    su alvea/devices/<device_id>/telemetry. I campi Optional hanno None come
    default perché il firmware può ometterli in alcune condizioni (es.
    battery_pct=None se l'ADC della batteria è guasto).
    """
    device_id: str
    patient_id: Optional[str] = None       # associazione paziente-dispositivo
    timestamp: Optional[float] = None      # Unix epoch (secondi); se None si usa now()
    bpm: float                             # frequenza cardiaca (BPM)
    skin_temperature: float                # temperatura cutanea periferica (°C)
    spo2: float                            # saturazione ossigeno periferico (%)
    respiration_rate: float                # frequenza respiratoria (atti/min)
    battery_pct: Optional[float] = None   # carica batteria (%); None se sensore guasto
    sensor_contact: bool                   # True solo se ECG e PPG sono entrambi a contatto
    device_status: Optional[str] = None   # es. "SYSTEM_OK", "ERR_ECG_LEADS_OFF"
    source: Optional[str] = None          # "sim" | "production_firmware"

class ReadingResponse(BaseModel):
    """Lettura restituita dagli endpoint REST e dal canale realtime.

    Espone tutti i parametri vitali in modo che l'app possa visualizzarli
    senza dover fare ulteriori chiamate.
    """
    id: int
    device_id: str
    patient_id: Optional[str]
    ts: datetime                           # timestamp salvato nel DB (UTC)
    bpm: float
    skin_temperature: float
    spo2: float
    respiration_rate: float
    battery_pct: Optional[float]
    sensor_contact: bool
    device_status: Optional[str]
    source: Optional[str]
    class Config:
        from_attributes = True


# ===================== ALERT =====================

class AlertResponse(BaseModel):
    """Allarme clinico o tecnico restituito dagli endpoint REST."""
    id: int
    device_id: str
    ts: datetime
    kind: str       # es. "bpm_high", "spo2_low", "resp_low", "contact_lost"
    severity: str   # "warning" | "critical" | "technical"
    message: str    # messaggio leggibile
    value: Optional[float]  # valore che ha scatenato l'allarme
    class Config:
        from_attributes = True


# ===================== COMANDI DEVICE =====================

class DeviceCommand(BaseModel):
    """Payload per inviare un comando di configurazione alla cavigliera.

    Il backend pubblica questo JSON sul topic MQTT
    alvea/devices/<device_id>/commands, che il firmware ascolta per
    aggiornare la propria configurazione senza riavvio.
    """
    publish_period_s: Optional[int] = None   # nuova frequenza di invio (secondi)
    patient_id: Optional[str] = None         # associa/disassocia il paziente