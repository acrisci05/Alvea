# `secrets.py` e' ignorato da git (vedi .gitignore) per non
# pubblicare la password del Wi-Fi (e del broker MQTT) nel repository.
WIFI_SSID = ""
WIFI_PASS = ""

# Credenziali del broker MQTT (opzionali: se assenti, transport_mqtt.py usa
# i fallback di sviluppo definiti in config.py).
MQTT_BROKER = ""   # placeholder, IP di rete locale
MQTT_USER = "alvea_device"
MQTT_PASS = "secure_password"