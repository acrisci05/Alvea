# main_sim_ble.py - Telemetria SIMULATA via BLE NOTIFY (demo/test locale).
#
# NOTA: vedi main_real_ble.py - questo path NON e' la pipeline ufficiale
# richiesta dal regolamento (che impone MQTT per la maglietta). Usare
# main_sim_mqtt.py per i test end-to-end con InfluxDB/Grafana.
#
# FIX (Code Review): non veniva registrata alcuna command_callback sulla
# BLEPeripheral, quindi anche qui il Requisito 8 ("Configurazione da
# parte del medico") non era dimostrabile in modalita' simulata.
# Aggiunta la stessa logica gia' presente in main_real_ble.py.

import time
import json
import config
from sensor_sim import SimSensor
from transport_ble import BLEPeripheral
from alerts import AlertManager

print("== AsthmaGuard TEST-RIG :: SIMULATORE BLE ASINCRONO (modalita' alternativa/demo) ==")

# --- VARIABILE DI CONFIGURAZIONE DINAMICA (Punto 8) ---
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

# AGGIUNTA (Requisito 8 - associazione paziente-dispositivo)
current_patient_id = config.DEFAULT_PATIENT_ID


def ble_command_callback(payload):
    """Gestisce i comandi/configurazioni scritti dall'app del medico via BLE
    (stessa logica di main_real_ble.py, qui applicata anche al simulatore)."""
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

        # AGGIUNTA (Requisito 7 - "batteria bassa del dispositivo")
        alert_mgr.check_battery(reading["battery_pct"], patient_id=current_patient_id)
        
        if ble.is_connected():
            reading["device_status"] = "SYSTEM_OK" if current_patient_id else "WARN_PATIENT_NOT_ASSIGNED"
            if ble.send_json(reading):
                print("[SIM BLE NOTIFY]:", reading)
        else:
            reading["device_status"] = "WARN_BLE_DISCONNECTED"
            print("[SIM BLE STANDBY]:", reading)
            
    time.sleep_ms(10)