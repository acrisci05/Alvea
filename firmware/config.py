# config.py - Configurazione centrale del firmware AsthmaGuard
# VERSIONE DI PRODUZIONE: Predisposto per sicurezza e configurazione remota (Punto 8)
#
# NOTA SUL TRASPORTO RICHIESTO DAL REGOLAMENTO ACADEMY:
# Il documento dei requisiti generali impone esplicitamente:
#   "Se il progetto prevede l'uso della maglietta, i dati sono trasmessi via
#    MQTT dalla esp32." (Requisito 1)
# La pipeline ufficiale e VINCOLANTE per la consegna e':
#   ESP32 --MQTT--> Backend (Node-Red/Python) --> InfluxDB --> Grafana
# I file main_real_ble.py / main_sim_ble.py NON fanno parte del percorso dati
# richiesto e vanno considerati una modalita' alternativa/demo opzionale
# (utile ad es. per test locali senza rete Wi-Fi), da NON usare come pipeline
# principale in fase di consegna/relazione.

# --- IDENTITA' DISPOSITIVO -------------------------------------------------
DEVICE_ID = "PULSEGUARD_ASTHMA_ANKLE_01"

# --- RETE / MQTT (Configurazione Sicura) -----------------------------------
# In produzione si usano broker remoti in cloud (es. AWS IoT, flespi, o server aziendale)
MQTT_BROKER = "192.168.1.50" 
MQTT_PORT   = 1883           # In produzione reale passa a 8883 (TLS)

# Le credenziali MQTT vere vanno in secrets.py (NON versionato), seguendo lo
# stesso schema usato per le credenziali Wi-Fi. Qui restano solo dei
# fallback di sviluppo per non rompere l'esecuzione se secrets.py non
# definisce queste variabili.
MQTT_USER = "asthma_device"      # Fallback di sviluppo (Punto 10)
MQTT_PASS = "secure_password"    # Fallback di sviluppo - SOVRASCRIVERE in secrets.py

TOPIC_DATA  = f"asthmaguard/devices/{DEVICE_ID}/telemetry"
TOPIC_CMD   = f"asthmaguard/devices/{DEVICE_ID}/commands"  # Topic in ascolto per le configurazioni del medico
TOPIC_ALERT = f"asthmaguard/devices/{DEVICE_ID}/alerts"

# --- BLE -------------------------------------------------------------------
BLE_NAME         = "AsthmaGuard-A01"
BLE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BLE_CHAR_UUID     = "abcdef01-1234-5678-1234-56789abcdef0"  # Telemetria (NOTIFY, device -> app)
BLE_CHAR_CMD_UUID = "abcdef02-1234-5678-1234-56789abcdef0"  # Comandi/config (WRITE, app -> device, Punto 8)

# --- PARAMETRI DINAMICI (Modificabili dal Medico - Punto 8) ----------------
# Questi parametri in produzione verrebbero letti da un file config.json in Flash.
# Li dichiariamo qui come valori di DEFAULT (Fallback).
DEFAULT_PUBLISH_PERIOD_S = 1      # Frequenza di invio telemetria di base (default/fallback)
DEFAULT_ALARM_SPO2_MIN   = 92.0   # Soglia di allerta saturazione (Asma)
DEFAULT_ALARM_RESP_MAX   = 40.0   # Soglia tachipnea (Asma pediatrico)

# AGGIUNTA (Requisito 8 - "associazione paziente-dispositivo"): il
# documento dei requisiti elenca esplicitamente questo parametro tra
# quelli configurabili dal medico. Il firmware da solo non puo' sapere
# a quale paziente e' associato (l'associazione "vera" e canonica vive
# nel DB del backend, tabella device<->patient), ma deve comunque:
#  1. poter ricevere via comando (MQTT/BLE) un patient_id assegnato dal
#     medico/backend, per poterlo riportare in telemetria;
#  2. avere un default sicuro (None = "non assegnato") che si traduca in
#     un device_status dedicato, cosi' backend/Grafana possono segnalare
#     subito un device non ancora associato a nessun paziente.
DEFAULT_PATIENT_ID = None

# Soglia di batteria scarica (Requisito 2 - "batteria bassa del
# dispositivo" tra gli esempi di condizione anomala). Il valore e'
# espresso in percentuale. Va usato da un eventuale modulo di lettura
# della batteria (non incluso: dipende dal circuito di alimentazione
# usato sull'hardware reale, es. partitore ADC su un pin libero).
DEFAULT_ALARM_BATTERY_MIN_PCT = 15.0

# Numero di letture consecutive di un guasto hardware (sensore non a
# contatto / sensore guasto) dopo le quali il device pubblica un alert
# dedicato su TOPIC_ALERT, invece di limitarsi a riportare lo
# device_status nella sola telemetria periodica. Evita di generare un
# alert per ogni singolo glitch transitorio (es. un contatto che salta
# per una singola lettura).
ALERT_FAULT_STREAK_THRESHOLD = 5

# --- VALORI FISIOLOGICI NOMINALI (Esclusivamente per il Test-Rig / Simulatore) ---
BPM_SIM_MIN  = 90.0
BPM_SIM_MAX  = 110.0
TEMP_SKIN_SIM_MIN = 31.0
TEMP_SKIN_SIM_MAX = 34.0
SPO2_SIM_MIN = 95.0
SPO2_SIM_MAX = 99.0
RESP_RATE_SIM_MIN = 20.0     
RESP_RATE_SIM_MAX = 30.0

CONTACT_DROP_PROB = 0.05