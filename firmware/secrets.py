# `secrets.py` e' ignorato da git (vedi .gitignore) per non
# pubblicare la password del Wi-Fi (e del broker MQTT) nel repository.
WIFI_SSID = "IL_NOME_DEL_TUO_WIFI"
WIFI_PASS = "LA_PASSWORD_DEL_TUO_WIFI"

# Credenziali del broker MQTT (opzionali: se assenti, transport_mqtt.py usa
# i fallback di sviluppo definiti in config.py).
MQTT_USER = "alvea_device"
MQTT_PASS = "secure_password"