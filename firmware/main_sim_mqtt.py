# main_sim_mqtt.py - Telemetria SIMULATA pubblicata via MQTT (stack Docker).
# Carica questo come main.py per il percorso "simulazione + MQTT".
import time
import machine

import config
import wifi
from sensor_sim import SimSensor
from transport_mqtt import MQTTPublisher

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("Crea secrets.py da secrets_example.py")

print("== PulseGuard-Baby :: SIM + MQTT ==")
if not wifi.connetti_wifi(SSID, PSW):
    machine.reset()

mqtt = MQTTPublisher()
mqtt.reconnect_forever()

sensor = SimSensor()
print("Monitoraggio attivo (1 Hz)...")
while True:
    try:
        reading = sensor.read()
        mqtt.publish(reading)
        print("TX:", reading)
        time.sleep(config.PUBLISH_PERIOD_S)
    except Exception as e:
        print("Loop error:", e)
        mqtt.reconnect_forever()
