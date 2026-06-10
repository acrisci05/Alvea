# main_real_mqtt.py - Telemetria REALE (AD8232 + temperatura) via MQTT.
# Carica questo come main.py per il percorso "sensore reale + MQTT".
#
# Il main loop possiede il timing a 250 Hz; una volta al secondo compone e
# pubblica lo STESSO payload del simulatore. Cosi' backend/Node-RED/Grafana
# non cambiano passando da sim a reale.
import time
import machine

import config
import wifi
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor
from transport_mqtt import MQTTPublisher

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("Crea secrets.py da secrets_example.py")

print("== PulseGuard-Baby :: REALE (AD8232) + MQTT ==")
if not wifi.connetti_wifi(SSID, PSW):
    machine.reset()

mqtt = MQTTPublisher()
mqtt.reconnect_forever()

ecg = ECGMonitor()
thermo = TempSensor()

next_sample = time.ticks_us()
last_pub = time.time()
print("Monitoraggio attivo (ECG 250 Hz, telemetria 1 Hz)...")

while True:
    # --- timing di campionamento (busy-wait, come in Fase 1) ---
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    if ecg.leads_off():
        ecg.reset()                  # ripartiamo puliti quando si riattacca
    else:
        ecg.feed(ecg.read_raw())

    # --- pubblicazione 1 Hz ---
    if time.time() - last_pub >= config.PUBLISH_PERIOD_S:
        contact = not ecg.leads_off()
        bpm = ecg.compute_bpm() if contact else 0
        temp = thermo.read() if contact else 0.0
        reading = {
            "device_id": config.DEVICE_ID,
            "timestamp": time.time(),
            "bpm": float(bpm),
            "temperature": float(temp),
            "sensor_contact": contact,
            "source": "ad8232",
        }
        try:
            mqtt.publish(reading)
            print("TX:", reading)
        except Exception as e:
            print("MQTT publish error:", e)
            mqtt.reconnect_forever()
        last_pub = time.time()
