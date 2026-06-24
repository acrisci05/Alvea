# config.py - Configurazione centrale del firmware Alvea
# VERSIONE DI PRODUZIONE: Predisposto per sicurezza e configurazione remota (Punto 8)

# --- IDENTITA' DISPOSITIVO -------------------------------------------------
DEVICE_ID = "ALVEA_ASTHMA_ANKLE_01"

# --- RETE / MQTT (Configurazione Sicura) -----------------------------------
# In produzione si usano broker remoti in cloud (es. AWS IoT, flespi, o server aziendale)
MQTT_BROKER = "192.168.1.50" 
MQTT_PORT   = 1883           # In produzione reale passa a 8883 (TLS)
MQTT_USER   = "asthma_device" # Placeholder per autenticazione (Punto 10)
MQTT_PASS   = "secure_password"

TOPIC_DATA  = f"alvea/devices/{DEVICE_ID}/telemetry"
TOPIC_CMD   = f"alvea/devices/{DEVICE_ID}/commands"  # Topic in ascolto per le configurazioni del medico
TOPIC_ALERT = f"alvea/devices/{DEVICE_ID}/alerts"

# --- BLE -------------------------------------------------------------------
BLE_NAME         = "Alvea-A01"
BLE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BLE_CHAR_UUID     = "abcdef01-1234-5678-1234-56789abcdef0"  # Telemetria (NOTIFY, device -> app)
BLE_CHAR_CMD_UUID = "abcdef02-1234-5678-1234-56789abcdef0"  # Comandi/config (WRITE, app -> device, Punto 8)

# --- PARAMETRI DINAMICI (Modificabili dal Medico - Punto 8) ----------------
# Questi parametri in produzione verrebbero letti da un file config.json in Flash.
# Li dichiariamo qui come valori di DEFAULT (Fallback).
DEFAULT_PUBLISH_PERIOD_S = 1      # Frequenza di invio telemetria di base (default/fallback)
DEFAULT_ALARM_RESP_MAX   = 40.0   # Soglia tachipnea (Asma pediatrico)

# --- VALORI FISIOLOGICI NOMINALI (Esclusivamente per il Test-Rig / Simulatore) ---
BPM_SIM_MIN  = 90.0
BPM_SIM_MAX  = 110.0
TEMP_SKIN_SIM_MIN = 31.0
TEMP_SKIN_SIM_MAX = 34.0
RESP_RATE_SIM_MIN = 20.0
RESP_RATE_SIM_MAX = 30.0

CONTACT_DROP_PROB = 0.05
