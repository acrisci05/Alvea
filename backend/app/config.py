# config.py - Configurazione backend via variabili d'ambiente (12-factor).
#
# Tutte le costanti vengono lette da variabili d'ambiente al momento
# dell'avvio del container; se la variabile non è impostata si usa il
# valore di default (utile per sviluppo locale senza docker-compose).
import os

# --- Database -------------------------------------------------------------
# SQLite asincrono in locale; in produzione sostituire con Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./alvea.db")

# --- Auth -----------------------------------------------------------------
# Chiave segreta usata per firmare i token JWT. DEVE essere cambiata in
# produzione (variabile d'ambiente SECRET_KEY nel docker-compose).
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIAMI_IN_PRODUZIONE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- CORS -----------------------------------------------------------------
# Origini autorizzate a chiamare l'API (app mobile Expo / dashboard web).
# Lista separata da virgole; "*" (default sviluppo) abilita tutte le origini.
# Nota: con "*" disabilitiamo allow_credentials (vedi main.py), perché la
# coppia wildcard + credenziali è vietata dalla specifica CORS. L'auth viaggia
# comunque nell'header Authorization (Bearer), non nei cookie.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- MQTT -----------------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")   # nome del container broker
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Il firmware pubblica la telemetria su:
#   alvea/devices/<device_id>/telemetry
# Usiamo il wildcard MQTT a livello singolo (+) per sottoscrivere tutti i
# device con una sola iscrizione. Il device_id viene estratto dal topic
# nel momento in cui arriva il messaggio (vedi mqtt_ingest.py).
TOPIC_DATA = os.getenv("TOPIC_DATA", "alvea/devices/+/telemetry")

# Il firmware pubblica allarmi hardware su questo topic separato
# (batteria scarica, guasto sensore persistente).
TOPIC_ALERT = os.getenv("TOPIC_ALERT", "alvea/devices/+/alerts")

# Il backend pubblica comandi verso il firmware su questo topic.
# Sostituire <device_id> con l'id reale prima di pubblicare.
TOPIC_CMD_TEMPLATE = "alvea/devices/{device_id}/commands"

# --- InfluxDB (serie temporali, opzionale) --------------------------------
INFLUX_URL     = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN   = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG     = os.getenv("INFLUX_ORG",    "alvea")
INFLUX_BUCKET  = os.getenv("INFLUX_BUCKET", "vitals")
# Disabilitato di default; abilitare con INFLUX_ENABLED=true nel .env
INFLUX_ENABLED = os.getenv("INFLUX_ENABLED", "false").lower() == "true"

# --- Soglie cliniche (dalla relazione tecnica, Sezione 5) -----------------
# Il dispositivo ha un unico sensore biomedicale (ECG AD8232): da esso si
# ricavano il battito (BPM) e, tramite EDR, la frequenza respiratoria. La
# temperatura cutanea arriva dal termistore NTC. NON esiste un sensore SpO2,
# quindi nel backend non c'è alcuna soglia/valutazione sulla saturazione.
#
# Frequenza respiratoria (atti/min) — parametro chiave per l'asma
RESP_WARN_LOW  = 14     # warning se FR < 14
RESP_WARN_HIGH = 30     # warning se FR > 30
RESP_CRIT_LOW  = 10     # critico se FR <= 10  (apnea/bradipnea)
RESP_CRIT_HIGH = 40     # critico se FR >= 40  (tachipnea severa, crisi asmatica)

# Frequenza cardiaca (BPM) — fascia scolare 6-12 anni (default prototipo)
BPM_WARN_LOW   = 70     # warning se BPM < 70
BPM_WARN_HIGH  = 130    # warning se BPM > 130
BPM_CRIT_LOW   = 60     # critico se BPM <= 60  (bradicardia)
BPM_CRIT_HIGH  = 150    # critico se BPM >= 150 (tachicardia severa)

# Temperatura cutanea (°C)
TEMP_WARN_LOW  = 36.0   # warning se temp < 36.0
TEMP_WARN_HIGH = 37.2   # warning se temp > 37.2
TEMP_CRIT_LOW  = 35.0   # critico se temp <= 35.0 (ipotermia)
TEMP_CRIT_HIGH = 38.5   # critico se temp >= 38.5 (febbre alta)

# Secondi consecutivi di sensor_contact=False prima di emettere
# l'allarme tecnico "fascia staccata" (debounce anti-panico).
CONTACT_LOST_DEBOUNCE_S = 5

# Soglie di default per-device: usate quando il medico non ha configurato
# soglie dedicate per uno specifico dispositivo (vedi modello DeviceThreshold
# e PUT /devices/{id}/thresholds). La funzione alerts.evaluate() accetta un
# dizionario con esattamente queste chiavi.
DEFAULT_THRESHOLDS = {
    "resp_warn_low":  RESP_WARN_LOW,
    "resp_warn_high": RESP_WARN_HIGH,
    "resp_crit_low":  RESP_CRIT_LOW,
    "resp_crit_high": RESP_CRIT_HIGH,
    "bpm_warn_low":   BPM_WARN_LOW,
    "bpm_warn_high":  BPM_WARN_HIGH,
    "bpm_crit_low":   BPM_CRIT_LOW,
    "bpm_crit_high":  BPM_CRIT_HIGH,
    "temp_warn_low":  TEMP_WARN_LOW,
    "temp_warn_high": TEMP_WARN_HIGH,
    "temp_crit_low":  TEMP_CRIT_LOW,
    "temp_crit_high": TEMP_CRIT_HIGH,
}
