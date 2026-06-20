# main_sim_mqtt.py - Telemetria SIMULATA via MQTT (Logica asincrona di produzione).
#
# FIX (Code Review): a differenza di main_real_mqtt.py, questo file non
# registrava alcuna callback comandi e non chiamava mai
# mqtt.check_messages(): il Requisito 8 ("Configurazione da parte del
# medico") non era quindi dimostrabile/testabile usando la pipeline
# simulata (l'unica eseguibile senza hardware reale). Aggiunta la stessa
# logica gia' presente in main_real_mqtt.py per allineare i due percorsi.

import time
import machine
import json
import config
from wifi import WiFiManager
from transport_mqtt import MQTTPublisher
from sensor_sim import SimSensor
from alerts import AlertManager
import ntp_time

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("File secrets.py mancante.")

print("== AsthmaGuard TEST-RIG :: SIMULATORE MQTT ASINCRONO ==")

# --- VARIABILE DI CONFIGURAZIONE DINAMICA (Punto 8) ---
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

# AGGIUNTA (Requisito 8 - associazione paziente-dispositivo)
current_patient_id = config.DEFAULT_PATIENT_ID


def mqtt_command_callback(topic, msg):
    """Gestisce i comandi in ingresso dal backend (es. dal Medico), anche
    in modalita' simulata: stessa logica di main_real_mqtt.py."""
    global current_publish_period, current_patient_id

    print(f"\n[COMANDO RICEVUTO] Sul topic: {topic.decode('utf-8')}")
    try:
        payload = json.loads(msg.decode('utf-8'))
        print("Contenuto:", payload)

        if "publish_period_s" in payload:
            nuovo_periodo = int(payload["publish_period_s"])
            if nuovo_periodo > 0:
                current_publish_period = nuovo_periodo
                print(f"-> [OK] Frequenza di invio telemetria aggiornata a {current_publish_period} secondi.")

        if "patient_id" in payload:
            nuovo_patient_id = payload["patient_id"]
            current_patient_id = nuovo_patient_id if nuovo_patient_id else None
            print(f"-> [OK] Device associato al paziente: {current_patient_id}")

    except Exception as e:
        print("-> [ERRORE] Parsing del comando MQTT fallito:", e)


wifi_mga = WiFiManager(SSID, PSW)

# --- ATTESA INIZIALE WI-FI + SYNC NTP --------------------------------------
# Stesso bug critico del firmware reale: senza sync NTP, time.time() su
# ESP32 MicroPython non e' un Unix timestamp valido e InfluxDB scrivera'
# i punti con una data sbagliata di ~30 anni.
print("Wi-Fi: connessione iniziale in corso...")
_wifi_wait_start = time.time()
while not wifi_mga.is_connected():
    wifi_mga.rinfresca_connessione()
    time.sleep(0.5)
    if time.time() - _wifi_wait_start > 20:
        print("Wi-Fi: timeout iniziale, procedo comunque (riconnessione in background).")
        break

if wifi_mga.is_connected():
    ntp_time.sync_time()
else:
    print("[NTP] Saltata sincronizzazione: nessuna connessione Wi-Fi disponibile.")

mqtt = MQTTPublisher(message_callback=mqtt_command_callback)
alert_mgr = AlertManager(mqtt, transport_kind="mqtt")
sensor = SimSensor()

last_pub = time.time()

while True:
    # Gestione della rete in background senza bloccare il loop
    wifi_mga.rinfresca_connessione()
    if wifi_mga.is_connected():
        if mqtt.check_connection():
            # Ascolta eventuali comandi di configurazione dal backend/medico
            mqtt.check_messages()
    else:
        mqtt.is_connected = False

    # Invio temporizzato (ora usa current_publish_period, configurabile dal medico)
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()
        
        reading = sensor.read()
        reading["patient_id"] = current_patient_id

        # AGGIUNTA (Requisito 7 - alert "assenza di dati"/guasto sensore):
        # anche in modalita' simulata, una caduta di contatto persistente
        # (CONTACT_DROP_PROB in config.py) genera un alert dedicato su
        # TOPIC_ALERT, per poter dimostrare il flusso end-to-end degli
        # alert hardware senza richiedere l'hardware reale.
        alert_mgr.check_fault(
            "sim_sensor_contact_lost", not reading["sensor_contact"],
            "sensor_contact", "Simulazione: caduta di contatto del sensore rilevata",
            gravita="WARNING", patient_id=current_patient_id,
        )

        # Inietta lo stato di rete nel pacchetto diagnostico
        if not mqtt.is_connected:
            reading["device_status"] = "WARN_NETWORK_DISCONNECTED"
            print("[SIM LOCAL]:", reading)
        elif current_patient_id is None:
            reading["device_status"] = "WARN_PATIENT_NOT_ASSIGNED"
            mqtt.publish(reading)
            print("[SIM TX]:", reading)
        else:
            reading["device_status"] = "SYSTEM_OK"
            mqtt.publish(reading)
            print("[SIM TX]:", reading)
            
    # Un piccolissimo sleep per allentare la CPU quando simula (risparmio energetico)
    time.sleep_ms(10)