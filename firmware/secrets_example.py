# secrets_example.py - TEMPLATE delle credenziali locali.
#
# Copia questo file in `secrets.py` e compila i valori. `secrets.py` e'
# ignorato da git (vedi .gitignore) per non pubblicare le password.

# --- Wi-Fi (obbligatorio) ---
WIFI_SSID = "NOME_RETE_WIFI"
WIFI_PASS = "PASSWORD_WIFI"

# --- Broker MQTT (consigliato) ---
# IP del PC che ospita lo stack Docker (Mosquitto). Se definito qui, ha la
# precedenza sul valore in config.py. Trova l'IP con `ipconfig` (Windows) o
# `ip addr` (Linux/macOS).
MQTT_BROKER = "192.168.1.50"   # <-- SOSTITUISCI con l'IP reale del tuo PC
MQTT_PORT   = 1883

# Credenziali broker (opzionali: il broker del prototipo accetta accesso
# anonimo, vedi docker-stack/mosquitto/config/mosquitto.conf).
MQTT_USER = "alvea_device"
MQTT_PASS = "secure_password"