# main_real_mqtt.py - Firmware di Produzione ad Alta Affidabilita' (Bidirezionale).
#
# Architettura sensoristica: ECG (AD8232) come unica fonte di BPM e
# Frequenza Respiratoria derivata dagli intervalli RR
# dell'ECG (EDR - ECG-Derived Respiration), tramite il modulo resp_edr.py.

import time
import machine
import json
import config
from wifi import WiFiManager
from transport_mqtt import MQTTPublisher
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor
from sensor_battery import BatteryMonitor
from alerts import AlertManager
import resp_edr
import ntp_time
from ntp_time import unix_now
import shell_log

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("File secrets.py mancante o corrotto.")

print("ALVEA: AVVIO ARCHITETTURA DI PRODUZIONE")

# --- VARIABILI DI CONFIGURAZIONE DINAMICA ---
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

# id del paziente attualmente assegnato a questo device. None = non assegnato.
current_patient_id = config.DEFAULT_PATIENT_ID

def mqtt_callback(topic, msg):
    """Gestione dei comandi in ingresso dal backend"""
    global current_publish_period, current_patient_id
    
    print(f"\n[COMANDO RICEVUTO] Sul topic: {topic.decode('utf-8')}")
    try:
        # Decodifica il messaggio JSON arrivato dal server
        payload = json.loads(msg.decode('utf-8'))
        print("Contenuto:", payload)
        
        # Controlla se il medico ha richiesto di cambiare la frequenza di campionamento/invio
        if "publish_period_s" in payload:
            nuovo_periodo = int(payload["publish_period_s"])
            if nuovo_periodo > 0:
                current_publish_period = nuovo_periodo
                print(f"-> [OK] Frequenza di invio telemetria aggiornata a {current_publish_period} secondi.")

        # il medico/backend puo' assegnare (o rimuovere, con None/"") questo device a un paziente.
        # Il valore viene poi incluso in ogni record di telemetria
        if "patient_id" in payload:
            nuovo_patient_id = payload["patient_id"]
            current_patient_id = nuovo_patient_id if nuovo_patient_id else None
            print(f"-> [OK] Device associato al paziente: {current_patient_id}")
        
    except Exception as e:
        print("-> [ERRORE] Parsing del comando MQTT fallito:", e)


# --- INIZIALIZZAZIONE RETE (BLOCCANTE SOLO ALL'AVVIO) ---

# All'avvio e' necessario attendere la prima connessione Wi-Fi, perche':
#  1. serve per sincronizzare l'RTC via NTP (timestamp Unix corretti);
#  2. evita di iniziare a generare dati "ERR/WARN" inutili nei primi secondi.
wifi_mga = WiFiManager(SSID, PSW)
print("Wi-Fi: connessione iniziale in corso...")
_wifi_wait_start = time.time()
while not wifi_mga.is_connected():
    wifi_mga.rinfresca_connessione()
    time.sleep(0.5)
    if time.time() - _wifi_wait_start > 20:
        print("Wi-Fi: timeout iniziale, procedo comunque (riconnessione in background).")
        break

# --- SINCRONIZZAZIONE OROLOGIO ---
if wifi_mga.is_connected():
    ntp_time.sync_time()
    try:
        _ip = wifi_mga.wlan.ifconfig()[0]
        print("[RETE] IP ESP32:", _ip, "| Broker MQTT:", config.MQTT_BROKER, "porta", config.MQTT_PORT)
    except Exception as _e:
        print("[RETE] Impossibile leggere ifconfig:", _e)
else:
    print("[NTP] Saltata sincronizzazione: nessuna connessione Wi-Fi disponibile.")

# Inizializzazione Rete e MQTT (Passiamo la callback creata sopra)
mqtt = MQTTPublisher(message_callback=mqtt_callback)
alert_mgr = AlertManager(mqtt, transport_kind="mqtt")

# Inizializzazione Sensori Reali
ecg = ECGMonitor()
thermo = TempSensor()
battery = BatteryMonitor()

next_sample = time.ticks_us()
last_pub = time.time()

while True:

    # 1. TIMING DETERMINISTICO (250 Hz)
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    # 2. ELABORAZIONE MEDICA
    contact_ecg = not ecg.leads_off()
    if contact_ecg:
        ecg.feed(ecg.read_raw())
    else:
        ecg.reset()
            
    # 3. MACCHINA A STATI DI RETE E ASCOLTO COMANDI
    wifi_mga.rinfresca_connessione()
    if wifi_mga.is_connected():
        if mqtt.check_connection():
            # Se siamo connessi, l'ESP32 "ascolta" se ci sono messaggi dal server
            mqtt.check_messages()
    else:
        mqtt.is_connected = False

    # 4. TRASMISSIONE TELEMETRIA CRONOMETRATA
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()

        temp_val = thermo.read()

        if not contact_ecg:
            # Senza contatto ECG non sono disponibili BPM e EDR (respiro): condizione bloccante primaria dell'architettura
            status_string = "ERR_ECG_LEADS_OFF"
        elif temp_val is None:
            status_string = "ERR_TEMP_SENSOR_FAULT"
        elif not mqtt.is_connected:
            status_string = "WARN_NETWORK_DISCONNECTED"
        elif current_patient_id is None:
            status_string = "WARN_PATIENT_NOT_ASSIGNED"
        else:
            status_string = "SYSTEM_OK"

        bpm = ecg.compute_bpm() if contact_ecg else 0
        final_temp = temp_val if temp_val is not None else 0.0

        # EDR (Frequenza Respiratoria): derivata dagli intervalli RR
        # dell'ECG sulla finestra estesa. Disponibile solo se il contatto ECG è presente.
        if contact_ecg:
            rr_history = ecg.get_rr_history()
            resp_rate = resp_edr.compute_edr_resp_rate(rr_history)
        else:
            resp_rate = 0.0

        alert_mgr.check_fault(
            "ecg_leads_off", not contact_ecg,
            "bpm", "Elettrodi ECG scollegati / non a contatto rilevato",
            gravita="WARNING", patient_id=current_patient_id,
        )
        alert_mgr.check_fault(
            "temp_sensor_fault", temp_val is None,
            "skin_temperature", "Guasto o lettura non disponibile dal sensore di temperatura",
            gravita="CRITICAL", patient_id=current_patient_id,
        )

        # Alert clinico basato su soglia
        alert_mgr.check_resp_rate(resp_rate, patient_id=current_patient_id)

        battery_pct = battery.read_percent()
        alert_mgr.check_battery(battery_pct, patient_id=current_patient_id)

        reading = {
            "device_id": config.DEVICE_ID,
            "patient_id": current_patient_id,
            "timestamp": unix_now(),
            "bpm": float(bpm),
            "skin_temperature": float(final_temp),
            "respiration_rate": float(resp_rate),
            "battery_pct": float(battery_pct) if battery_pct is not None else None,
            "sensor_contact": contact_ecg,
            "device_status": status_string,
            "source": "production_firmware"
        }

        # Riga compatta leggibile in Shell (Thonny)
        shell_log.log_reading(reading, status_string)

        if mqtt.is_connected:
            mqtt.publish(reading)
        else:
            print("[LOCAL MONITORING ONLY]:", reading)