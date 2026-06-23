# config.py - Configurazione centrale del firmware Alvea
# VERSIONE DI PRODUZIONE: Predisposto per sicurezza e configurazione remota
#
# Architettura sensoristica: ECG (AD8232) come unica fonte di BPM e
# Frequenza Respiratoria (tramite EDR, vedi resp_edr.py). Niente PPG,
# niente SpO2, niente HRV: scelte di progetto motivate da tempi stretti e
# dalla volonta' di concentrare l'impegno implementativo su un'unica
# pipeline ben fatta. Il rilevamento dell'aderenza cutanea si basa sui
# soli pin leads-off dell'AD8232 (GPIO32/33).

# --- IDENTITA' DISPOSITIVO ---
DEVICE_ID = "ALVEA_04"

# --- RETE / MQTT (Configurazione Sicura) ---
MQTT_BROKER = "192.168.1.50" 
MQTT_PORT   = 1883        

# Le credenziali MQTT riportate sono solo dei fallback di sviluppo per non rompere l'esecuzione se secrets.py non
# definisce queste variabili.
MQTT_USER = "alvea_device"    
MQTT_PASS = "secure_password"  
TOPIC_DATA  = f"alvea/devices/{DEVICE_ID}/telemetry"
TOPIC_CMD   = f"alvea/devices/{DEVICE_ID}/commands"  # Topic in ascolto per le configurazioni del medico
TOPIC_ALERT = f"alvea/devices/{DEVICE_ID}/alerts"

# --- BLE ---
BLE_NAME         = "Alvea-04"
BLE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BLE_CHAR_UUID     = "abcdef01-1234-5678-1234-56789abcdef0"  # Telemetria (NOTIFY, device -> app)
BLE_CHAR_CMD_UUID = "abcdef02-1234-5678-1234-56789abcdef0"  # Comandi/config (WRITE, app -> device, Punto 8)

# --- PARAMETRI DINAMICI (Modificabili dal Medico) ---
# Li dichiariamo qui come valori di DEFAULT (Fallback).

DEFAULT_PUBLISH_PERIOD_S = 1      # Frequenza di invio telemetria di base (default/fallback)
DEFAULT_ALARM_RESP_MAX   = 40.0   # Soglia tachipnea (Asma pediatrico), su Frequenza Respiratoria EDR
DEFAULT_PATIENT_ID = None

# Soglia di batteria scarica espressa in percentuale
DEFAULT_ALARM_BATTERY_MIN_PCT = 15.0

# Numero di letture consecutive di un guasto hardware (sensore non a
# contatto / sensore guasto) dopo le quali il device pubblica un alert
# dedicato su TOPIC_ALERT, invece di limitarsi a riportare il
# device_status nella sola telemetria periodica. Evita di generare un
# alert per ogni singolo glitch transitorio (es. un contatto che salta
# per una singola lettura).
ALERT_FAULT_STREAK_THRESHOLD = 5

# --- VALORI FISIOLOGICI NOMINALI (Esclusivi per il Simulatore) ---
BPM_SIM_MIN  = 90.0
BPM_SIM_MAX  = 110.0
TEMP_SKIN_SIM_MIN = 31.0
TEMP_SKIN_SIM_MAX = 34.0
RESP_RATE_SIM_MIN = 20.0     
RESP_RATE_SIM_MAX = 30.0

CONTACT_DROP_PROB = 0.05

# --- SIMULAZIONE BATTERIA (Esclusivamente per il Simulatore) ---
BATTERY_SIM_START = 100.0
BATTERY_SIM_DRAIN_PER_TICK = 0.5