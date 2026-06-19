# main_sim_ble.py - Telemetria SIMULATA inviata via BLE NOTIFY.

import time
import config
from sensor_sim import SimSensor
from transport_ble import BLEPeripheral

print("== AsthmaGuard TEST-RIG :: SIMULATORE BLE ASINCRONO ==")
ble = BLEPeripheral()
sensor = SimSensor()

last_pub = time.time()

while True:
    if time.time() - last_pub >= config.DEFAULT_PUBLISH_PERIOD_S:
        last_pub = time.time()
        
        reading = sensor.read()
        
        if ble.is_connected():
            reading["device_status"] = "SYSTEM_OK"
            if ble.send_json(reading):
                print("[SIM BLE NOTIFY]:", reading)
        else:
            reading["device_status"] = "WARN_BLE_DISCONNECTED"
            print("[SIM BLE STANDBY]:", reading)
            
    time.sleep_ms(10)