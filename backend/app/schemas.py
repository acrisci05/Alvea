# schemas.py - Schemi Pydantic per validazione I/O (request/response FastAPI
# e validazione del payload MQTT in ingresso).
#
# Gli schemi qui definiti descrivono il "contratto" dati tra:
#   - app mobile  <-> backend (login, letture, alert, comandi, push);
#   - firmware    <-> backend (payload di telemetria ReadingIn);
#   - medico      <-> backend (configurazione soglie, scheda paziente).

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, model_validator


# ===================== CAREGIVER / AUTH =====================

class CaregiverCreate(BaseModel):
    """Payload di POST /register.

    Il ruolo è opzionale (default "caregiver"): l'auto-registrazione di un
    medico è ammessa solo a scopo didattico. L'app può inviare anche dei dati
    anagrafici del paziente insieme alla registrazione: campi extra non
    dichiarati qui vengono ignorati da Pydantic senza errori.
    """
    username: str
    password: str
    role: Literal["caregiver", "medico"] = "caregiver"

    # Dati anagrafici minimi del paziente, inviati dall'app in fase di
    # registrazione (LoginScreen → registerUser). Usati per creare la scheda
    # paziente e per l'auto-assegnazione del paziente al dispositivo.
    patient_name: Optional[str] = None
    age_years: Optional[int] = None
    age_months: Optional[int] = None


class CaregiverResponse(BaseModel):
    """Risposta di POST /register e GET /me (la password hashata non si espone)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str

    # Valorizzati da POST /register: l'id paziente generato e assegnato in
    # automatico e il dispositivo associato. None per GET /me.
    patient_id: Optional[str] = None
    device_id: Optional[str] = None


class Token(BaseModel):
    """Risposta di POST /login.

    Oltre al token JWT, restituiamo il ruolo e il device_id principale
    dell'utente: l'app mobile li usa subito dopo il login per scegliere la
    schermata (paziente/medico) e per sapere quale device interrogare
    (vedi loginUser()/config.js nell'app, che si aspetta
    { access_token, device_id, role }).
    """
    access_token: str
    token_type: str = "bearer"
    role: str = "caregiver"
    device_id: Optional[str] = None


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
    """Payload di POST /devices/{id}/commands.

    Campi allineati a quanto il firmware accetta in mqtt_callback /
    ble_command_callback (main_real_mqtt.py / main_real_ble.py):
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
    sensor_contact: bool = True
    device_status: Optional[str] = None
    source: Optional[str] = None


class ReadingResponse(BaseModel):
    """Risposta per GET /devices/{id}/history e /latest."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    patient_id: Optional[str] = None
    ts: datetime
    bpm: Optional[float] = None
    skin_temperature: Optional[float] = None
    respiration_rate: Optional[float] = None
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
    parameter: Optional[str] = None
    kind: str
    severity: str
    message: str
    value: Optional[float] = None


# ===================== SOGLIE CLINICHE (config. dal medico) =====================

class ThresholdConfig(BaseModel):
    """Soglie cliniche per-device impostabili dal medico (PUT .../thresholds).

    Il validatore controlla la coerenza degli ordinamenti per evitare di
    salvare soglie senza senso (es. soglia critica più permissiva della warning).
    """
    resp_warn_low: float
    resp_warn_high: float
    resp_crit_low: float
    resp_crit_high: float
    bpm_warn_low: int
    bpm_warn_high: int
    bpm_crit_low: int
    bpm_crit_high: int
    temp_warn_low: float
    temp_warn_high: float
    temp_crit_low: float
    temp_crit_high: float

    @model_validator(mode="after")
    def _check_order(self):
        # Per ogni parametro: crit_low <= warn_low <= warn_high <= crit_high.
        for p in ("resp", "bpm", "temp"):
            cl = getattr(self, f"{p}_crit_low")
            wl = getattr(self, f"{p}_warn_low")
            wh = getattr(self, f"{p}_warn_high")
            ch = getattr(self, f"{p}_crit_high")
            if not (cl <= wl <= wh <= ch):
                raise ValueError(
                    f"Soglie '{p}' incoerenti: atteso crit_low <= warn_low <= warn_high <= crit_high"
                )
        return self


class ThresholdResponse(ThresholdConfig):
    device_id: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ===================== SCHEDA PAZIENTE / ANAMNESI =====================

class PatientRecordUpdate(BaseModel):
    """Payload di PUT /devices/{id}/patient (tutti i campi opzionali)."""
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
    model_config = ConfigDict(from_attributes=True)


# ===================== NOTIFICHE PUSH =====================

class PushTokenIn(BaseModel):
    """Payload di POST /register-token (inviato dall'app, vedi api.js).

    L'app invia l'Expo push token e il device monitorato; il backend lo
    associa all'utente autenticato (Bearer) per le notifiche sugli alert critici.
    """
    token: str
    device_id: Optional[str] = None


# ===================== AUDIT LOG =====================

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    username: Optional[str] = None
    role: Optional[str] = None
    action: str
    resource: Optional[str] = None
    detail: Optional[str] = None
    ip: Optional[str] = None
