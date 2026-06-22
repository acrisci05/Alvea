# schemas.py - Schemi Pydantic (v2) di richiesta/risposta.
#
# Pydantic è una libreria che definisce la "forma" dei dati in ingresso e uscita.
# Ogni classe qui descrive come deve essere strutturato un dato:
# - quali campi ci sono
# - che tipo ha ogni campo
# - quali sono obbligatori e quali opzionali
#
# FastAPI usa questi schemi per:
# - validare automaticamente i dati in entrata (request body)
# - serializzare i dati in uscita (response) in JSON
# - generare la documentazione automatica su /docs

from datetime import datetime
from typing import Optional       # per i campi che possono essere None
from pydantic import BaseModel    # classe base da cui ereditano tutti gli schemi


# =============================================================================
# AUTH
# =============================================================================

class CaregiverCreate(BaseModel):
    # Schema per la registrazione di un nuovo caregiver (POST /register).
    # Entrambi i campi sono obbligatori: se mancano, FastAPI risponde 422.
    username: str
    password: str  # la password in chiaro: verrà hashata prima di salvarla nel DB


class CaregiverResponse(BaseModel):
    # Schema per la risposta dopo la registrazione o il login.
    # Restituisce solo id e username: la password (anche hashata) non viene mai esposta.
    id: int
    username: str

    class Config:
        # from_attributes=True permette di creare questo schema direttamente
        # da un oggetto ORM (models.Caregiver) senza convertirlo manualmente a dict.
        from_attributes = True


class Token(BaseModel):
    # Schema per il token JWT restituito dopo il login (POST /login).
    access_token: str
    token_type: str = "bearer"  # valore fisso: il tipo standard per JWT è "bearer"


# =============================================================================
# DEVICE
# =============================================================================

class DeviceCreate(BaseModel):
    # Schema per associare una cavigliera all'account (POST /devices).
    device_id: str              # identificativo univoco della cavigliera (es. "ALVEA_04")
    baby_name: Optional[str] = None  # nome del bambino, opzionale


class DeviceResponse(BaseModel):
    # Schema per la risposta con i dati di una cavigliera.
    id: int
    device_id: str
    baby_name: Optional[str]
    owner_id: int               # id del caregiver proprietario

    class Config:
        from_attributes = True


# =============================================================================
# TELEMETRIA / LETTURE
# =============================================================================

class ReadingIn(BaseModel):
    # Schema per il payload prodotto dall'ESP32 e ricevuto via MQTT.
    # Viene usato in mqtt_ingest.py per validare ogni messaggio in arrivo.
    # Se il payload non rispetta questo schema, il messaggio viene scartato.
    device_id: str
    timestamp: Optional[float] = None      # timestamp Unix dell'ESP32 (opzionale: usiamo quello del DB)
    resp_rate: Optional[float] = None      # frequenza respiratoria in atti/min (può non essere ancora disponibile)
    bpm: float                             # battito cardiaco in BPM (obbligatorio)
    temperature: float                     # temperatura cutanea in °C (obbligatoria)
    sensor_contact: bool                   # True = fascia a contatto, False = staccata
    source: Optional[str] = None          # "sim" (simulatore) o "ad8232" (sensore reale)


class ReadingResponse(BaseModel):
    # Schema per la risposta degli endpoint GET /devices/{id}/readings e /latest.
    # Aggiunge i campi generati dal DB (id e ts) che non erano nel payload originale.
    id: int
    device_id: str
    ts: datetime                           # timestamp assegnato dal DB al momento del salvataggio
    resp_rate: Optional[float]             # frequenza respiratoria (può essere None)
    bpm: float
    temperature: float
    sensor_contact: bool
    source: Optional[str]

    class Config:
        from_attributes = True


# =============================================================================
# ALERT
# =============================================================================

class AlertResponse(BaseModel):
    # Schema per la risposta dell'endpoint GET /devices/{id}/alerts.
    # Rappresenta un singolo allarme generato dalla valutazione delle soglie.
    id: int
    device_id: str
    ts: datetime                # quando è stato generato l'alert
    kind: str                   # tipo: "bpm_low", "resp_high", "contact_lost", ...
    severity: str               # gravità: "warning", "critical", "technical"
    message: str                # testo leggibile (es. "Bradicardia critica: 55 BPM")
    value: Optional[float]      # valore numerico che ha scatenato l'alert (None per alert tecnici)

    class Config:
        from_attributes = True