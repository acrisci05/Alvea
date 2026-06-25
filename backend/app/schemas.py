# schemas.py - Schemi Pydantic per validazione I/O (request/response FastAPI
# e validazione del payload MQTT in ingresso).
#
# NOTA: questo file era assente nell'archivio caricato ed è stato
# ricostruito sulla base di:
#   - tutti i riferimenti a "schemas.XYZ" presenti in main.py e crud.py
#   - il payload reale pubblicato dal firmware su .../telemetry
#     (vedi main_real_mqtt.py, main_sim_mqtt.py, sensor_sim.py)
#   - i campi del modello ORM in models.py (allineati al firmware)
#
# Se lo schemas.py originale del progetto differisce nei dettagli (es.
# validatori aggiuntivi, vincoli di lunghezza sullo username), va
# confrontato e riconciliato con questa versione.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ===================== CAREGIVER / AUTH =====================

class CaregiverCreate(BaseModel):
    """Payload di POST /register."""
    username: str
    password: str


class CaregiverResponse(BaseModel):
    """Risposta di POST /register (la password hashata non viene mai esposta)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    """Risposta di POST /login."""
    access_token: str
    token_type: str = "bearer"


# ===================== DEVICE =====================

class DeviceCreate(BaseModel):
    """Payload di POST /devices: registra/rivendica una cavigliera."""
    device_id: str
    baby_name: Optional[str] = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    baby_name: Optional[str] = None
    owner_id: Optional[int] = None


class DeviceCommand(BaseModel):
    """Payload di POST /devices/{id}/command.

    Campi allineati a quanto il firmware accetta in mqtt_callback /
    mqtt_command_callback (main_real_mqtt.py / main_sim_mqtt.py):
      - publish_period_s: nuova frequenza di invio telemetria (secondi)
      - patient_id: assegna (o rimuove, passando None) il paziente al device
    Tutti i campi sono opzionali: il backend invia solo quelli effettivamente
    impostati (vedi filtro `if v is not None` in main.py).
    """
    publish_period_s: Optional[int] = None
    patient_id: Optional[str] = None


# ===================== READING =====================

class ReadingIn(BaseModel):
    """Valida il payload di telemetria pubblicato dal firmware su
    alvea/devices/<device_id>/telemetry.

    Campi e tipi presi direttamente dal dizionario costruito in
    main_real_mqtt.py / sensor_sim.py:
      device_id, patient_id, timestamp, bpm, skin_temperature,
      respiration_rate, battery_pct, sensor_contact, device_status, source.
    """
    device_id: str
    patient_id: Optional[str] = None
    timestamp: Optional[float] = None
    bpm: float = 0.0
    skin_temperature: float = 0.0
    respiration_rate: float = 0.0
    # battery_pct può essere None se l'ADC della batteria è guasto
    battery_pct: Optional[float] = None
    # spo2 non è ancora prodotto dal firmware attuale (né main_real_mqtt.py
    # né sensor_sim.py lo includono nel payload): lo manteniamo opzionale
    # qui e in alerts.py/models.py per quando verrà aggiunto, senza che
    # la validazione del payload odierno fallisca.
    spo2: Optional[float] = None
    sensor_contact: bool = True
    device_status: Optional[str] = None
    source: Optional[str] = None


class ReadingResponse(BaseModel):
    """Risposta per GET /devices/{id}/readings e /latest."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    patient_id: Optional[str] = None
    ts: datetime
    bpm: Optional[float] = None
    skin_temperature: Optional[float] = None
    respiration_rate: Optional[float] = None
    spo2: Optional[float] = None
    battery_pct: Optional[float] = None
    sensor_contact: Optional[bool] = None
    device_status: Optional[str] = None
    source: Optional[str] = None


# ===================== ALERT =====================

class AlertResponse(BaseModel):
    """Risposta per GET /devices/{id}/alerts."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    ts: datetime
    kind: str
    severity: str
    message: str
    value: Optional[float] = None
