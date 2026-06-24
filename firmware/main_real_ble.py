# main_real_ble.py - Firmware di Produzione BLE ad Alta Affidabilita'.

import time
import json
import machine
import config
from transport_ble import BLEPeripheral
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor

print("=== ALVEA PRO: AVVIO ARCHITETTURA BLE ===")

# --- VARIABILE DI CONFIGURAZIONE DINAMICA (Punto 8) ---
# Aggiornabile a runtime dal medico tramite scrittura BLE sulla characteristic
# di comando (vedi ble_command_callback piu' sotto). Stesso schema usato in
# main_real_mqtt.py per garantire parita' funzionale tra i due trasporti.
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S


def ble_command_callback(payload):
    """Gestisce i comandi/configurazioni scritti dall'app del medico via BLE."""
    global current_publish_period

    print("\n[COMANDO BLE RICEVUTO]")
    try:
        data = json.loads(payload.decode('utf-8'))
        print("Contenuto:", data)

        if "publish_period_s" in data:
            nuovo_periodo = int(data["publish_period_s"])
            if nuovo_periodo > 0:
                current_publish_period = nuovo_periodo
                print(f"-> [OK] Frequenza di invio telemetria aggiornata a {current_publish_period} secondi.")

        # [Aggiungere qui in futuro l'ascolto per altre configurazioni, es. soglie di alert locali]

    except Exception as e:
        print("-> [ERRORE] Parsing del comando BLE fallito:", e)


# Inizializzazione BLE (con callback comandi per il Punto 8)
ble = BLEPeripheral(command_callback=ble_command_callback)

# Inizializzazione Sensori Reali
ecg = ECGMonitor()
thermo = TempSensor()

# Variabili di Timing
next_sample = time.ticks_us()
last_pub = time.time()

print("Attesa connessione App Mobile...")

while True:
    # 1. TIMING DETERMINISTICO (250 Hz)
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    # 2. ELABORAZIONE MEDICA (ECG a 250 Hz: BPM + respiro via EDR)
    contact_ecg = not ecg.leads_off()
    if contact_ecg:
        ecg.feed(ecg.read_raw())
    else:
        ecg.reset()

    # 3. TRASMISSIONE TELEMETRIA CRONOMETRATA (default 1 Hz, configurabile dal medico)
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()

        temp_val = thermo.read()

        # Diagnostica Hardware
        if not contact_ecg:
            status_string = "ERR_ECG_LEADS_OFF"
        elif temp_val is None:
            status_string = "ERR_TEMP_SENSOR_FAULT"
        elif not ble.is_connected():
            status_string = "WARN_BLE_DISCONNECTED"
        else:
            status_string = "SYSTEM_OK"

        bpm = ecg.compute_bpm() if contact_ecg else 0
        resp_rate = ecg.compute_resp_rate() if contact_ecg else 0.0
        final_temp = temp_val if temp_val is not None else 0.0

        reading = {
            "device_id": config.DEVICE_ID,
            "timestamp": time.time(),
            "bpm": float(bpm),
            "respiration_rate": float(resp_rate),
            "skin_temperature": float(final_temp),
            "sensor_contact": contact_ecg,
            "device_status": status_string,
            "source": "production_ble"
        }

        if ble.is_connected():
            ble.send_json(reading)
            print("[BLE TX]:", reading)
