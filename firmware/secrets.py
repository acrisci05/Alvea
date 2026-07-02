# `secrets.py` e' ignorato da git (vedi .gitignore) per non
# pubblicare la password del Wi-Fi (e del broker MQTT) nel repository.

WIFI_SSID = "NOME_DELLA_TUA_RETE_WIFI"
WIFI_PASS = "password_wifi"

# Credenziali del broker MQTT (opzionali: se assenti, transport_mqtt.py usa
# i fallback di sviluppo definiti in config.py).
MQTT_BROKER = "192.168.1.50"   # IP del PC/server che ospita lo stack Docker
MQTT_USER = "alvea_device"
MQTT_PASS = "secure_password"