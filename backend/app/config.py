# config.py - Configurazione backend via variabili d'ambiente (12-factor).
import os

# --- Database -------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./alvea.db")

# --- Auth -----------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIAMI_IN_PRODUZIONE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- CORS -----------------------------------------------------------------
# Origini autorizzate (app mobile / dashboard). Lista separata da virgole;
# "*" (default) abilita tutte le origini in sviluppo locale. Con "*" le
# credenziali via cookie restano disattivate (l'auth usa header Bearer).
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- MQTT -----------------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
# Il firmware/simulatore pubblica su alvea/devices/<DEVICE_ID>/telemetry:
# il backend si sottoscrive con la wildcard MQTT '+'.
TOPIC_DATA = os.getenv("TOPIC_DATA", "alvea/devices/+/telemetry")
TOPIC_ALERT = os.getenv("TOPIC_ALERT", "alvea/alerts")

# --- InfluxDB (opzionale: scrittura serie temporali) ----------------------
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "alvea")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vitals")
INFLUX_ENABLED = os.getenv("INFLUX_ENABLED", "false").lower() == "true"

# --- Soglie cliniche (didattiche, asma pediatrico) ------------------------
# Frequenza respiratoria (EDR): più alta è peggio (tachipnea). BPM:
# tachicardia/bradicardia. Temperatura cutanea (caviglia): valori alti = febbre.
RESP_WARN_HIGH  = 30.0   # atti/min
RESP_CRIT_HIGH  = 40.0
BPM_WARN_LOW    = 60
BPM_WARN_HIGH   = 120
BPM_CRIT_LOW    = 50
BPM_CRIT_HIGH   = 160
SKIN_TEMP_WARN_HIGH = 35.0   # °C
SKIN_TEMP_CRIT_HIGH = 38.0

# Secondi di sensore staccato prima di emettere l'allarme tecnico (debounce)
CONTACT_LOST_DEBOUNCE_S = 5

# Soglie di default: usate quando un device non ha una configurazione dedicata
# impostata dal medico (vedi modello DeviceThreshold). La valutazione degli
# alert (alerts.evaluate) accetta un dizionario con queste stesse chiavi.
DEFAULT_THRESHOLDS = {
    "resp_warn_high": RESP_WARN_HIGH,
    "resp_crit_high": RESP_CRIT_HIGH,
    "bpm_warn_low":   BPM_WARN_LOW,
    "bpm_warn_high":  BPM_WARN_HIGH,
    "bpm_crit_low":   BPM_CRIT_LOW,
    "bpm_crit_high":  BPM_CRIT_HIGH,
    "skin_temp_warn_high": SKIN_TEMP_WARN_HIGH,
    "skin_temp_crit_high": SKIN_TEMP_CRIT_HIGH,
}
