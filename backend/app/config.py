# config.py - Configurazione backend via variabili d'ambiente (12-factor).
#
# Il principio "12-factor" dice che la configurazione non va scritta
# direttamente nel codice, ma letta dall'ambiente (variabili d'ambiente).
# Così lo stesso codice gira in sviluppo, test e produzione cambiando
# solo le variabili, senza toccare una riga di Python.

# os è il modulo standard Python per leggere le variabili d'ambiente
import os

# --- Database -------------------------------------------------------------

# URL di connessione al database.
# os.getenv("DATABASE_URL", "...") significa:
#   - se esiste la variabile d'ambiente DATABASE_URL → usala
#   - altrimenti → usa il valore di default (SQLite locale)
# SQLite è un database in un singolo file, perfetto per sviluppo e prototipo.
# "aiosqlite" è la versione asincrona, compatibile con FastAPI async.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pulseguard.db")

# --- Auth -----------------------------------------------------------------

# Chiave segreta usata per firmare i token JWT.
# In produzione DEVE essere una stringa lunga e casuale (es. 64 caratteri).
# Il default "CAMBIAMI_IN_PRODUZIONE" è un promemoria esplicito.
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIAMI_IN_PRODUZIONE")

# Algoritmo crittografico per la firma JWT.
# HS256 = HMAC con SHA-256: veloce e sufficiente per questo uso.
# Non legge da variabile d'ambiente perché non ha senso cambiarlo a runtime.
ALGORITHM = "HS256"

# Durata del token JWT in minuti. Dopo questo tempo l'utente deve rifare il login.
# Default: 60 minuti (1 ora).
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- MQTT -----------------------------------------------------------------

# Indirizzo del broker MQTT a cui connettersi.
# "mosquitto" è il nome del container Docker del broker nella rete interna.
# In sviluppo locale si può sovrascrivere con "localhost".
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")

# Porta del broker MQTT. 1883 è la porta standard non cifrata.
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Topic MQTT su cui l'ESP32 pubblica i dati di telemetria.
# Il backend si sottoscrive a questo topic per ricevere le letture.
TOPIC_DATA = os.getenv("TOPIC_DATA", "alvea/monitor/data")

# Topic MQTT su cui il backend pubblica gli alert generati.
TOPIC_ALERT = os.getenv("TOPIC_ALERT", "alvea/monitor/alerts")

# --- InfluxDB (opzionale: scrittura serie temporali) ----------------------

# URL del server InfluxDB per la scrittura delle serie temporali.
# "influxdb" è il nome del container Docker nella rete interna.
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")

# Token di autenticazione per InfluxDB (generato al setup del container).
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")

# Organizzazione e bucket InfluxDB dove vengono scritti i dati.
INFLUX_ORG = os.getenv("INFLUX_ORG", "alvea")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vitals")

# Flag che abilita/disabilita la scrittura su InfluxDB.
# Di default è disabilitata (false): il percorso principale è Node-RED → InfluxDB.
# Si attiva solo se si vuole bypassare Node-RED e scrivere direttamente dal backend.
# os.getenv restituisce una stringa, quindi confrontiamo con "true" dopo .lower().
INFLUX_ENABLED = os.getenv("INFLUX_ENABLED", "false").lower() == "true"

# --- Soglie cliniche (didattiche) -----------------------------------------
# Questi valori determinano quando viene generato un alert.
# Sono allineati alle linee guida WHO/GINA descritte nella relazione.
# Struttura: ogni parametro ha due livelli → warning (attenzione) e critical (urgente).

# Battito cardiaco (BPM)
# warning: sotto 70 o sopra 130 BPM → situazione da monitorare
# critical: sotto 60 o sopra 150 BPM → intervento urgente
BPM_WARN_LOW   = 70
BPM_WARN_HIGH  = 130
BPM_CRIT_LOW   = 60
BPM_CRIT_HIGH  = 150

# Frequenza respiratoria (atti al minuto)
# warning: sotto 14 o sopra 30 atti/min → possibile inizio di crisi
# critical: sotto 10 o sopra 40 atti/min → distress respiratorio severo
RESP_WARN_LOW  = 14
RESP_WARN_HIGH = 30
RESP_CRIT_LOW  = 10
RESP_CRIT_HIGH = 40

# Temperatura cutanea (°C)
# warning: sotto 36.0 o sopra 37.2 °C → da tenere sotto controllo
# critical: sotto 35.0 °C (ipotermia) o sopra 38.5 °C (febbre alta)
TEMP_WARN_LOW  = 36.0
TEMP_WARN_HIGH = 37.2
TEMP_CRIT_LOW  = 35.0
TEMP_CRIT_HIGH = 38.5

# Secondi consecutivi di fascia staccata prima di emettere l'allarme tecnico.
# Il debounce evita falsi allarmi per micro-distacchi momentanei (es. movimento).
# Dopo 5 secondi continui senza contatto → allarme tecnico reale.
CONTACT_LOST_DEBOUNCE_S = 5