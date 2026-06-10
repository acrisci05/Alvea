# config.py - Configurazione backend via variabili d'ambiente (12-factor).
import os

# --- Database -------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pulseguard.db")

# --- Auth -----------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIAMI_IN_PRODUZIONE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- MQTT -----------------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_DATA = os.getenv("TOPIC_DATA", "pulseguard/baby/data")
TOPIC_ALERT = os.getenv("TOPIC_ALERT", "pulseguard/baby/alerts")

# --- InfluxDB (opzionale: scrittura serie temporali) ----------------------
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "pulseguard")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vitals")
INFLUX_ENABLED = os.getenv("INFLUX_ENABLED", "false").lower() == "true"

# --- Soglie cliniche (didattiche) -----------------------------------------
# Coerenti con la documentazione: BPM nominale 100-140, Temp 36.0-37.2.
BPM_WARN_LOW   = 100
BPM_WARN_HIGH  = 140
BPM_CRIT_LOW   = 80
BPM_CRIT_HIGH  = 170

TEMP_WARN_LOW  = 36.0
TEMP_WARN_HIGH = 37.2
TEMP_CRIT_LOW  = 35.0
TEMP_CRIT_HIGH = 38.5

# Secondi di fascia staccata prima di emettere l'allarme tecnico (debounce)
CONTACT_LOST_DEBOUNCE_S = 5
