# config.py - Configurazione centrale del firmware PulseGuard-Baby
# Questo file e' l'unica fonte di verita' per parametri condivisi da TUTTE le
# modalita' (simulatore / sensore reale, MQTT / BLE). Modifica qui, non altrove.

# --- IDENTITA' DISPOSITIVO -------------------------------------------------
DEVICE_ID = "PULSEGUARD_BABY_04"     # ID richiesto dalla documentazione

# --- RETE / MQTT -----------------------------------------------------------
# Sostituisci con l'IP locale reale del PC che ospita lo stack Docker
MQTT_BROKER = "192.168.1.50"
MQTT_PORT   = 1883
TOPIC_DATA  = "pulseguard/baby/data"     # telemetria fisiologica
TOPIC_ALERT = "pulseguard/baby/alerts"   # (riservato: alert pubblicati lato server)

# --- BLE -------------------------------------------------------------------
BLE_NAME         = "PulseGuard-Baby"
BLE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BLE_CHAR_UUID    = "abcdef01-1234-5678-1234-56789abcdef0"

# --- CAMPIONAMENTO TELEMETRIA ---------------------------------------------
PUBLISH_PERIOD_S = 1                  # 1 Hz: vincolo di campionamento del progetto

# --- VALORI FISIOLOGICI NOMINALI (per il SIMULATORE) ----------------------
# Coerenti con la documentazione: BPM nominale 120 (range 100-140),
# temperatura nominale 36.5 (range 36.0-37.2).
BPM_SIM_MIN  = 115.0
BPM_SIM_MAX  = 125.0
TEMP_SIM_MIN = 36.3
TEMP_SIM_MAX = 36.9
CONTACT_DROP_PROB = 0.05              # 5% di probabilita' che la fascia si stacchi
