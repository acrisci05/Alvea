# main_sim_mqtt.py - Telemetria SIMULATA via MQTT (Logica asincrona di produzione).

import time
import machine
import config
from wifi import WiFiManager
from transport_mqtt import MQTTPublisher
from sensor_sim import SimSensor

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("File secrets.py mancante.")

print("== AsthmaGuard TEST-RIG :: SIMULATORE MQTT ASINCRONO ==")

wifi_mga = WiFiManager(SSID, PSW)
mqtt = MQTTPublisher()
sensor = SimSensor()

last_pub = time.time()

while True:
    # Gestione della rete in background senza bloccare il loop
    wifi_mga.rinfresca_connessione()
    if wifi_mga.is_connected():
        mqtt.check_connection()
    else:
        mqtt.is_connected = False

    # Invio temporizzato ad 1 Hz
    if time.time() - last_pub >= config.DEFAULT_PUBLISH_PERIOD_S:
        last_pub = time.time()
        
        reading = sensor.read()
        
        # Inietta lo stato di rete nel pacchetto diagnostico
        if not mqtt.is_connected:
            reading["device_status"] = "WARN_NETWORK_DISCONNECTED"
            print("[SIM LOCAL]:", reading)
        else:
            reading["device_status"] = "SYSTEM_OK"
            mqtt.publish(reading)
            print("[SIM TX]:", reading)
            
    # Un piccolissimo sleep per allentare la CPU quando simula (risparmio energetico)
    time.sleep_ms(10)