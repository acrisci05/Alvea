# config.py - Configurazione backend via variabili d'ambiente (12-factor).
import os

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./alvea.db")

# --- Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIAMI_IN_PRODUZIONE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- CORS ---
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- MQTT ---
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_DATA = os.getenv("TOPIC_DATA", "alvea/devices/+/telemetry")
TOPIC_ALERT = os.getenv("TOPIC_ALERT", "alvea/devices/+/alerts")
TOPIC_CMD_TEMPLATE = "alvea/devices/{device_id}/commands"
DEFAULT_DEVICE_ID = os.getenv("DEFAULT_DEVICE_ID", "ALVEA_04")

# --- InfluxDB (serie temporali, opzionale) ---
INFLUX_URL     = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN   = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG     = os.getenv("INFLUX_ORG",    "alvea")
INFLUX_BUCKET  = os.getenv("INFLUX_BUCKET", "vitals")
INFLUX_ENABLED = os.getenv("INFLUX_ENABLED", "false").lower() == "true"

# --- Soglie cliniche (Fasce di Fleming) ---
# Implementazione del range 1°-99° centile in base all'età (mesi).
# I valori limite della tabella costituiscono le soglie critiche. Le soglie 
# di warning sono state ricavate stringendo l'intervallo per l'allerta precoce.
# La temperatura cutanea è fissata a 36.0-37.2°C per la normalità.

FLEMING_THRESHOLDS = {
    "0-3m": {
        "resp_warn_low": 28, "resp_warn_high": 60, "resp_crit_low": 25, "resp_crit_high": 66,
        "bpm_warn_low": 100, "bpm_warn_high": 170, "bpm_crit_low": 90,  "bpm_crit_high": 181,
        "temp_warn_low": 36.0, "temp_warn_high": 37.2, "temp_crit_low": 35.0, "temp_crit_high": 38.5,
    },
    "3-6m": {
        "resp_warn_low": 27, "resp_warn_high": 58, "resp_crit_low": 24, "resp_crit_high": 64,
        "bpm_warn_low": 110, "bpm_warn_high": 165, "bpm_crit_low": 104, "bpm_crit_high": 175,
        "temp_warn_low": 36.0, "temp_warn_high": 37.2, "temp_crit_low": 35.0, "temp_crit_high": 38.5,
    },
    "6-9m": {
        "resp_warn_low": 26, "resp_warn_high": 55, "resp_crit_low": 23, "resp_crit_high": 61,
        "bpm_warn_low": 105, "bpm_warn_high": 160, "bpm_crit_low": 98,  "bpm_crit_high": 168,
        "temp_warn_low": 36.0, "temp_warn_high": 37.2, "temp_crit_low": 35.0, "temp_crit_high": 38.5,
    },
    "9-12m": {
        "resp_warn_low": 25, "resp_warn_high": 52, "resp_crit_low": 22, "resp_crit_high": 58,
        "bpm_warn_low": 100, "bpm_warn_high": 150, "bpm_crit_low": 93,  "bpm_crit_high": 161,
        "temp_warn_low": 36.0, "temp_warn_high": 37.2, "temp_crit_low": 35.0, "temp_crit_high": 38.5,
    },
    "fallback": {
        # Banda di tolleranza di massima ampiezza (es. pazienti > 1 anno o età non specificata)
        "resp_warn_low": 14, "resp_warn_high": 60, "resp_crit_low": 11, "resp_crit_high": 66,
        "bpm_warn_low": 50,  "bpm_warn_high": 170, "bpm_crit_low": 43,  "bpm_crit_high": 181,
        "temp_warn_low": 36.0, "temp_warn_high": 37.2, "temp_crit_low": 35.0, "temp_crit_high": 38.5,
    }
}

CONTACT_LOST_DEBOUNCE_S = 5
