# main_sim_ble.py - Telemetria SIMULATA via BLE NOTIFY (demo/test locale).

import time
import json
import config
from sensor_sim import SimSensor
from transport_ble import BLEPeripheral
from alerts import AlertManager
import shell_log

print("== ALVEA TEST-RIG :: SIMULATORE BLE ASINCRONO (modalita' alternativa/demo) ==")

# --- VARIABILE DI CONFIGURAZIONE DINAMICA ---
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S
current_patient_id = config.DEFAULT_PATIENT_ID


def ble_command_callback(payload):
    """Gestione dei comandi/configurazioni scritti dall'app del medico via BLE. """
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
        if "resp_rate_max" in data:
            try:
                alert_mgr.update_thresholds(resp_max=float(data["resp_rate_max"]))
                print("-> [OK] Soglia frequenza respiratoria aggiornata.")
            except (ValueError, TypeError):
                print("-> [ERRORE] Valore resp_rate_max non valido.")
        if "battery_min_pct" in data:
            try:
                alert_mgr.update_thresholds(battery_min=float(data["battery_min_pct"]))
                print("-> [OK] Soglia batteria minima aggiornata.")
            except (ValueError, TypeError):
                print("-> [ERRORE] Valore battery_min_pct non valido.")

    except Exception as e:
        print("-> [ERRORE] Parsing del comando BLE fallito:", e)



ble = BLEPeripheral(command_callback=ble_command_callback)
alert_mgr = AlertManager(ble, transport_kind="ble")
sensor = SimSensor()
last_pub = time.time()


while True:
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()
        
        reading = sensor.read()
        reading["patient_id"] = current_patient_id

        alert_mgr.check_fault(
            "sim_sensor_contact_lost", not reading["sensor_contact"],
            "sensor_contact", "Simulazione: caduta di contatto del sensore rilevata",
            gravita="WARNING", patient_id=current_patient_id,
        )

        alert_mgr.check_battery(reading["battery_pct"], patient_id=current_patient_id)
        alert_mgr.check_resp_rate(reading["respiration_rate"] if reading["sensor_contact"] else None, patient_id=current_patient_id)
        
        if ble.is_connected():
            reading["device_status"] = "SYSTEM_OK" if current_patient_id else "WARN_PATIENT_NOT_ASSIGNED"
            shell_log.log_reading(reading, reading["device_status"])
            if ble.send_json(reading):
                print("[SIM BLE NOTIFY]:", reading)
        else:
            reading["device_status"] = "WARN_BLE_DISCONNECTED"
            shell_log.log_reading(reading, reading["device_status"])
            print("[SIM BLE STANDBY]:", reading)
            
    time.sleep_ms(10)