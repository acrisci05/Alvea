# main_real_mqtt.py - Firmware di Produzione ad Alta Affidabilita' (Bidirezionale).

import time
import machine
import json
import config
from wifi import WiFiManager
from transport_mqtt import MQTTPublisher
from sensor_ecg import ECGMonitor, SAMPLE_PERIOD_US
from sensor_temp import TempSensor
from sensor_ppg import PPGMonitor
from sensor_battery import BatteryMonitor
from alerts import AlertManager
import ntp_time

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("File secrets.py mancante o corrotto.")

print("=== ASTHMAGUARD PRO: AVVIO ARCHITETTURA DI PRODUZIONE ===")

# --- VARIABILI DI CONFIGURAZIONE DINAMICA (Punto 8) ---
# Invece di usare una costante bloccata, usiamo una variabile aggiornabile.
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

# AGGIUNTA (Requisito 8 - "associazione paziente-dispositivo"): id del
# paziente attualmente assegnato a questo device. None = non assegnato.
current_patient_id = config.DEFAULT_PATIENT_ID

def mqtt_callback(topic, msg):
    """Gestisce i comandi in ingresso dal backend (es. dal Medico)."""
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

        # AGGIUNTA (Requisito 8 - associazione paziente-dispositivo): il
        # medico/backend puo' assegnare (o rimuovere, con None/"") questo
        # device a un paziente. Il valore viene poi incluso in ogni
        # record di telemetria, cosi' il backend non deve fare affidamento
        # solo su una tabella statica device_id->patient_id lato server.
        if "patient_id" in payload:
            nuovo_patient_id = payload["patient_id"]
            current_patient_id = nuovo_patient_id if nuovo_patient_id else None
            print(f"-> [OK] Device associato al paziente: {current_patient_id}")

        # [Aggiungere qui in futuro l'ascolto per altre configurazioni, es. soglie di alert locali]
        
    except Exception as e:
        print("-> [ERRORE] Parsing del comando MQTT fallito:", e)


# --- INIZIALIZZAZIONE RETE (BLOCCANTE SOLO ALL'AVVIO) ----------------------
# A differenza del loop principale (che non deve mai bloccarsi), all'avvio e'
# accettabile e necessario attendere la prima connessione Wi-Fi, perche':
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

# --- SINCRONIZZAZIONE OROLOGIO (FONDAMENTALE PER INFLUXDB) -----------------
# BUGFIX CRITICO: senza questa chiamata, time.time() su ESP32 MicroPython
# restituisce secondi dall'epoca MicroPython (2000-01-01) e non dall'epoca
# Unix (1970-01-01). Ogni timestamp scritto su InfluxDB risulterebbe
# spostato di ~30 anni, rendendo inutilizzabili tutte le query/grafici.
if wifi_mga.is_connected():
    ntp_time.sync_time()
else:
    print("[NTP] Saltata sincronizzazione: nessuna connessione Wi-Fi disponibile.")

# Inizializzazione Rete e MQTT (Passiamo la callback creata sopra)
mqtt = MQTTPublisher(message_callback=mqtt_callback)

# AGGIUNTA: gestore alert locali (sensore guasto persistente, batteria
# scarica). Vedi alerts.py per il razionale.
alert_mgr = AlertManager(mqtt, transport_kind="mqtt")

# Inizializzazione Sensori Reali
ecg = ECGMonitor()
thermo = TempSensor()
ppg = PPGMonitor()
battery = BatteryMonitor()

next_sample = time.ticks_us()
last_pub = time.time()
ppg_sample_divider = 0

# NOTA (Code Review - limite noto, non risolto in questa patch):
# il blocco "TIMING DETERMINISTICO (250 Hz)" qui sotto convive, nello
# stesso loop, con operazioni di rete potenzialmente bloccanti
# (wifi_mga.rinfresca_connessione(), mqtt.check_connection() ->
# client.connect(), mqtt.check_messages(), mqtt.publish()). Se una di
# queste chiamate impiega piu' del periodo di campionamento (4 ms), il
# busy-wait sottostante non recupera il ritardo accumulato: si rischia
# jitter/perdita di campioni ECG durante riconnessioni di rete lente.
# Una soluzione strutturale (rete su un secondo core / task asincrono,
# socket con timeout breve, ecc.) richiede modifiche piu' ampie e
# test su hardware reale: non inclusa in questa patch, da valutare.

while True:
    # ------------------------------------------------------------------
    # 1. TIMING DETERMINISTICO (250 Hz)
    # ------------------------------------------------------------------
    while time.ticks_diff(time.ticks_us(), next_sample) < 0:
        pass
    next_sample = time.ticks_add(next_sample, SAMPLE_PERIOD_US)

    # ------------------------------------------------------------------
    # 2. ELABORAZIONE MEDICA
    # ------------------------------------------------------------------
    contact_ecg = not ecg.leads_off()
    if contact_ecg:
        ecg.feed(ecg.read_raw())
    else:
        ecg.reset()

    ppg_sample_divider += 1
    if ppg_sample_divider >= 5:
        ppg_sample_divider = 0
        red_raw, ir_raw = ppg.read_raw()
        ppg.feed(red_raw, ir_raw)

    # ------------------------------------------------------------------
    # 3. MACCHINA A STATI DI RETE E ASCOLTO COMANDI
    # ------------------------------------------------------------------
    wifi_mga.rinfresca_connessione()
    if wifi_mga.is_connected():
        if mqtt.check_connection():
            # Se siamo connessi, l'ESP32 "ascolta" se ci sono messaggi dal server
            mqtt.check_messages()
    else:
        mqtt.is_connected = False

    # ------------------------------------------------------------------
    # 4. TRASMISSIONE TELEMETRIA CRONOMETRATA
    # ------------------------------------------------------------------
    # Ora utilizza `current_publish_period` modificabile dal medico!
    if time.time() - last_pub >= current_publish_period:
        last_pub = time.time()
        
        contact_ppg = ppg.is_skin_on()
        temp_val = thermo.read()
        
        if not contact_ecg:
            status_string = "ERR_ECG_LEADS_OFF"
        elif not contact_ppg:
            status_string = "ERR_PPG_NO_CONTACT"
        elif temp_val is None:
            status_string = "ERR_TEMP_SENSOR_FAULT"
        elif not mqtt.is_connected:
            status_string = "WARN_NETWORK_DISCONNECTED"
        elif current_patient_id is None:
            status_string = "WARN_PATIENT_NOT_ASSIGNED"
        else:
            status_string = "SYSTEM_OK"

        bpm = ecg.compute_bpm() if contact_ecg else 0
        spo2, resp_rate = ppg.compute_metrics() if contact_ppg else (0.0, 0.0)
        final_temp = temp_val if temp_val is not None else 0.0

        # AGGIUNTA (Requisito 7 - alert "assenza di dati"/guasto sensore,
        # Requisito 1 - "stato del dispositivo"): segnala su TOPIC_ALERT
        # le condizioni di guasto hardware solo quando sono persistenti
        # (vedi ALERT_FAULT_STREAK_THRESHOLD in config.py), per non
        # floodare il broker per ogni singolo glitch transitorio.
        alert_mgr.check_fault(
            "ecg_leads_off", not contact_ecg,
            "bpm", "Elettrodi ECG scollegati / non a contatto rilevato",
            gravita="WARNING", patient_id=current_patient_id,
        )
        alert_mgr.check_fault(
            "ppg_no_contact", not contact_ppg,
            "spo2", "Sensore PPG non a contatto con la pelle",
            gravita="WARNING", patient_id=current_patient_id,
        )
        alert_mgr.check_fault(
            "temp_sensor_fault", temp_val is None,
            "skin_temperature", "Guasto o lettura non disponibile dal sensore di temperatura",
            gravita="CRITICAL", patient_id=current_patient_id,
        )

        # AGGIUNTA (Requisito 7 - "batteria bassa del dispositivo", uno
        # degli esempi espliciti di condizione anomala nel documento dei
        # requisiti). battery_pct e' None se il monitoraggio batteria e'
        # disabilitato o l'hardware non e' disponibile: in tal caso
        # check_battery() non genera alcun alert (vedi sensor_battery.py).
        battery_pct = battery.read_percent()
        alert_mgr.check_battery(battery_pct, patient_id=current_patient_id)

        # NOTA SUL FORMATO (Requisito 1 - "tipo di parametro misurato"):
        # qui inviamo un singolo record multi-parametro per timestamp (un
        # "campionamento" del paziente), non un record per parametro. E'
        # una scelta di design lecita e comune (riduce il numero di
        # pubblicazioni MQTT), ma va documentata nella relazione: il
        # backend/Node-Red dovra' fare il fan-out dei singoli campi (bpm,
        # spo2, ...) come misure/field separati in InfluxDB.
        reading = {
            "device_id": config.DEVICE_ID,
            "patient_id": current_patient_id,
            "timestamp": time.time(),
            "bpm": float(bpm),
            "skin_temperature": float(final_temp),
            "spo2": float(spo2),
            "respiration_rate": float(resp_rate),
            "battery_pct": float(battery_pct) if battery_pct is not None else None,
            "sensor_contact": (contact_ecg and contact_ppg),
            "device_status": status_string,
            "source": "production_firmware"
        }
        
        if mqtt.is_connected:
            mqtt.publish(reading)
        else:
            print("[LOCAL MONITORING ONLY]:", reading)