# main_real_ble.py - Firmware ALTERNATIVO via BLE (demo/test locale).

import time
import json
import machine
import config
from transport_ble import BLEPeripheral
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor
from sensor_ppg import PPGMonitor
from sensor_battery import BatteryMonitor
from alerts import AlertManager
import resp_hrv

print("=== ALVEA: AVVIO ARCHITETTURA BLE (modalita' alternativa/demo) ===")

# --- VARIABILE DI CONFIGURAZIONE DINAMICA ---
# Aggiornabile a runtime dal medico tramite scrittura BLE sulla characteristic di comando
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

# Associazione paziente-dispositivo
current_patient_id = config.DEFAULT_PATIENT_ID

def ble_command_callback(payload):
    """Gestione dei comandi/configurazioni scritti dall'app del medico via BLE."""
    global current_publish_period, current_patient_id

    print("\n[COMANDO BLE RICEVUTO]")
    try:
        data = json.loads(payload.decode('utf-8'))
        print("Contenuto:", data)

        if "publish_period_s" in data:
            nuovo_periodo = int(data["publish_period_s"])
            if nuovo_periodo > 0:
                current_publish_period = nuovo_periodo
                print(f"-> [OK] Frequenza di invio telemetria aggiornata a {current_publish_period} secondi.")

        if "patient_id" in data:
            nuovo_patient_id = data["patient_id"]
            current_patient_id = nuovo_patient_id if nuovo_patient_id else None
            print(f"-> [OK] Device associato al paziente: {current_patient_id}")

    except Exception as e:
        print("-> [ERRORE] Parsing del comando BLE fallito:", e)

# Inizializzazione BLE
ble = BLEPeripheral(command_callback=ble_command_callback)

# Gestore alert locali via BLE
alert_mgr = AlertManager(ble, transport_kind="ble")

# Inizializzazione Sensori Reali
ecg = ECGMonitor()
thermo = TempSensor()
ppg = PPGMonitor()
battery = BatteryMonitor()

# Variabili di Timing
next_sample = time.ticks_us()
last_pub = time.time()
ppg_sample_divider = 0

print("Attesa connessione App Mobile...")

while True:
    # 1. TIMING DETERMINISTICO (250 Hz)
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    # 2. ELABORAZIONE MEDICA (ECG a 250Hz, PPG a 50Hz)
    contact_ecg = not ecg.leads_off()
    if contact_ecg:
        ecg.feed(ecg.read_raw())
    else:
        ecg.reset()

    ppg_sample_divider += 1
    if ppg_sample_divider >= 5:
        ppg_sample_divider = 0
        green_raw = ppg.read_raw()
        ppg.feed(green_raw)

    # 3. TRASMISSIONE TELEMETRIA CRONOMETRATA (default 1 Hz, configurabile dal medico)
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()

        contact_ppg = ppg.is_skin_on()
        temp_val = thermo.read()

        # Diagnostica Hardware
        if not contact_ecg:
            status_string = "ERR_ECG_LEADS_OFF"
        elif temp_val is None:
            status_string = "ERR_TEMP_SENSOR_FAULT"
        elif not contact_ppg:
            status_string = "WARN_PPG_NO_CONTACT"
        elif not ble.is_connected():
            status_string = "WARN_BLE_DISCONNECTED"
        elif current_patient_id is None:
            status_string = "WARN_PATIENT_NOT_ASSIGNED"
        else:
            status_string = "SYSTEM_OK"

        bpm = ecg.compute_bpm() if contact_ecg else 0
        final_temp = temp_val if temp_val is not None else 0.0

        if contact_ecg:
            rr_history = ecg.get_rr_history()
            resp_rate, hrv_sdnn = resp_hrv.compute_metrics(rr_history)
        else:
            resp_rate, hrv_sdnn = 0.0, None

        alert_mgr.check_fault(
            "ecg_leads_off", not contact_ecg,
            "bpm", "Elettrodi ECG scollegati / non a contatto rilevato",
            gravita="WARNING", patient_id=current_patient_id,
        )
        alert_mgr.check_fault(
            "ppg_no_contact", not contact_ppg,
            "bpm_ppg", "Sensore PPG (luce verde) non a contatto con la pelle",
            gravita="WARNING", patient_id=current_patient_id,
        )
        alert_mgr.check_fault(
            "temp_sensor_fault", temp_val is None,
            "skin_temperature", "Guasto o lettura non disponibile dal sensore di temperatura",
            gravita="CRITICAL", patient_id=current_patient_id,
        )

        # Alert clinici basati su soglie
        alert_mgr.check_resp_rate(resp_rate, patient_id=current_patient_id)
        alert_mgr.check_hrv(hrv_sdnn, patient_id=current_patient_id)

        # Batteria bassa del dispositivo
        battery_pct = battery.read_percent()
        alert_mgr.check_battery(battery_pct, patient_id=current_patient_id)

        reading = {
            "device_id": config.DEVICE_ID,
            "patient_id": current_patient_id,
            "timestamp": time.time(),
            "bpm": float(bpm),
            "skin_temperature": float(final_temp),
            "hrv_sdnn": float(hrv_sdnn) if hrv_sdnn is not None else None,
            "respiration_rate": float(resp_rate),
            "battery_pct": float(battery_pct) if battery_pct is not None else None,
            "sensor_contact": contact_ecg,
            "device_status": status_string,
            "source": "production_ble"
        }

        if ble.is_connected():
            ble.send_json(reading)
            print("[BLE TX]:", reading)