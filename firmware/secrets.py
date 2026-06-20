# secrets_example.py - COPIA questo file in `secrets.py` e inserisci le tue
# credenziali. `secrets.py` e' ignorato da git (vedi .gitignore) per non
# pubblicare la password del Wi-Fi (e del broker MQTT) nel repository.
WIFI_SSID = "IL_NOME_DEL_TUO_WIFI"
WIFI_PASS = "LA_PASSWORD_DEL_TUO_WIFI"

# Credenziali del broker MQTT (opzionali: se assenti, transport_mqtt.py usa
# i fallback di sviluppo definiti in config.py). In produzione vanno SEMPRE
# impostate qui e MAI lasciate in config.py.
MQTT_USER = "asthma_device"
MQTT_PASS = "secure_password"