# `secrets.py` e' ignorato da git (vedi .gitignore) per non
# pubblicare la password del Wi-Fi (e del broker MQTT) nel repository.
WIFI_SSID = "Wind3 HUB-F06589_EXT"
WIFI_PASS = "5ldlcegis32i1v9q"


# Credenziali del broker MQTT (opzionali: se assenti, transport_mqtt.py usa
# i fallback di sviluppo definiti in config.py).
MQTT_BROKER = "192.168.1.50"   # placeholder, IP di rete locale
MQTT_USER = "alvea_device"
MQTT_PASS = "secure_password"