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

try:
    import secrets
    SSID, PSW = secrets.WIFI_SSID, secrets.WIFI_PASS
except ImportError:
    raise RuntimeError("File secrets.py mancante o corrotto.")

print("=== ASTHMAGUARD PRO: AVVIO ARCHITETTURA DI PRODUZIONE ===")

# --- VARIABILI DI CONFIGURAZIONE DINAMICA (Punto 8) ---
# Invece di usare una costante bloccata, usiamo una variabile aggiornabile.
current_publish_period = config.DEFAULT_PUBLISH_PERIOD_S

def mqtt_callback(topic, msg):
    """Gestisce i comandi in ingresso dal backend (es. dal Medico)."""
    global current_publish_period
    
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
                
        # [Aggiungere qui in futuro l'ascolto per altre configurazioni, es. soglie di alert locali]
        
    except Exception as e:
        print("-> [ERRORE] Parsing del comando MQTT fallito:", e)


# Inizializzazione Rete e MQTT (Passiamo la callback creata sopra)
wifi_mga = WiFiManager(SSID, PSW)
mqtt = MQTTPublisher(message_callback=mqtt_callback)

# Inizializzazione Sensori Reali
ecg = ECGMonitor()
thermo = TempSensor()
ppg = PPGMonitor()

next_sample = time.ticks_us()
last_pub = time.time()
ppg_sample_divider = 0

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
        else:
            status_string = "SYSTEM_OK"

        bpm = ecg.compute_bpm() if contact_ecg else 0
        spo2, resp_rate = ppg.compute_metrics() if contact_ppg else (0.0, 0.0)
        final_temp = temp_val if temp_val is not None else 0.0

        reading = {
            "device_id": config.DEVICE_ID,
            "timestamp": time.time(),
            "bpm": float(bpm),
            "skin_temperature": float(final_temp),
            "spo2": float(spo2),
            "respiration_rate": float(resp_rate),
            "sensor_contact": (contact_ecg and contact_ppg),
            "device_status": status_string,
            "source": "production_firmware"
        }
        
        if mqtt.is_connected:
            mqtt.publish(reading)
        else:
            print("[LOCAL MONITORING ONLY]:", reading)