# main_real_ble.py - Telemetria REALE (AD8232 + temperatura) via BLE NOTIFY.
# Carica questo come main.py per il percorso "sensore reale + BLE".
import time

import config
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor
from transport_ble import BLEPeripheral

print("== PulseGuard-Baby :: REALE (AD8232) + BLE ==")
ble = BLEPeripheral()
ecg = ECGMonitor()
thermo = TempSensor()

next_sample = time.ticks_us()
last_pub = time.time()
print("In attesa di connessione dall'app...")

while True:
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    if ecg.leads_off():
        ecg.reset()
    else:
        ecg.feed(ecg.read_raw())

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
        if ble.is_connected():
            ble.send_json(reading)
            print("NOTIFY:", reading)
        last_pub = time.time()
