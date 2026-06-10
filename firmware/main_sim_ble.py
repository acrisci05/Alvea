# main_sim_ble.py - Telemetria SIMULATA inviata via BLE NOTIFY all'app mobile.
# Carica questo come main.py per il percorso "simulazione + BLE".
import time

import config
from sensor_sim import SimSensor
from transport_ble import BLEPeripheral

print("== PulseGuard-Baby :: SIM + BLE ==")
ble = BLEPeripheral()
sensor = SimSensor()

print("In attesa di connessione dall'app...")
while True:
    if ble.is_connected():
        reading = sensor.read()
        if ble.send_json(reading):
            print("NOTIFY:", reading)
    time.sleep(config.PUBLISH_PERIOD_S)
