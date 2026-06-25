#!/usr/bin/env python3
"""publish_test.py - Simulatore di telemetria Alvea dal PC.

Pubblica letture simulate su MQTT esattamente come farebbe l'ESP32 di produzione, 
per testare la pipeline (Node-RED -> InfluxDB -> Grafana -> App) senza l'hardware fisico.

NOTA: il dispositivo ha un solo sensore biomedicale, l'ECG (AD8232). Da
esso si derivano BPM e, via EDR, la frequenza respiratoria. Non esiste
alcun sensore SpO2/PPG: questo script non genera né invia un campo
"spo2", per restare fedele al payload reale del firmware (vedi
main_real_mqtt.py / sensor_sim.py).

Uso:
    pip install paho-mqtt
    python publish_test.py                                      # nominale, 1 Hz
    python publish_test.py --scenario asthma_attack             # test allarme asma (tachipnea)
    python publish_test.py --scenario hardware_fault            # test disconnessione sensore
"""
import argparse
import json
import random
import time

import paho.mqtt.client as mqtt

DEVICE_ID = "ALVEA_04"
TOPIC = f"alvea/devices/{DEVICE_ID}/telemetry"   # topic corretto firmware

def make_reading(scenario):
    """Genera un dizionario payload JSON identico a quello dell'ESP32 reale."""
    contact = True
    battery = round(random.uniform(60.0, 90.0), 1)

    # 1. SCENARIO: Sensore staccato o guasto hardware
    if scenario == "hardware_fault":
        contact = False
        bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0

    # 2. SCENARIO: Attacco d'asma (Tachipnea + Tachicardia lieve).
    #    È l'unico alert clinico per soglia generato realmente dal firmware
    #    (firmware/alerts.py: check_resp_rate, soglia
    #    config.DEFAULT_ALARM_RESP_MAX = 40.0, gravità CRITICAL).
    elif scenario == "asthma_attack":
        bpm = round(random.uniform(115.0, 130.0), 1)
        skin_temp = round(random.uniform(31.5, 33.5), 1)
        resp_rate = round(random.uniform(40.0, 50.0), 1)

    # 3. SCENARIO: Nominale (Bambino a riposo/sano)
    else:
        if random.random() < 0.05:
            contact = False
            bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0
        else:
            bpm = round(random.uniform(90.0, 110.0), 1)
            skin_temp = round(random.uniform(31.0, 34.0), 1)
            resp_rate = round(random.uniform(20.0, 30.0), 1)

    # device_status: stesse stringhe usate dal firmware reale (vedi
    # main_real_mqtt.py), così il backend/app che lo interpreta si
    # comporta esattamente come con un device vero.
    if not contact:
        status = "ERR_ECG_LEADS_OFF"
    else:
        status = "SYSTEM_OK"

    return {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "bpm": bpm,
        "skin_temperature": skin_temp,    # allineato al firmware
        "respiration_rate": resp_rate,    # allineato al firmware
        "battery_pct": battery,
        "sensor_contact": contact,
        "patient_id": "p_0001",
        "device_status": status,
        "source": "sim-pc-script",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost", help="IP del broker MQTT")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--rate", type=float, default=1.0, help="Frequenza di invio (messaggi al secondo)")
    ap.add_argument("--scenario", choices=["nominal", "asthma_attack", "hardware_fault"], default="nominal")
    args = ap.parse_args()

    client = mqtt.Client()
    
    try:
        client.connect(args.host, args.port, 60)
    except ConnectionRefusedError:
        print(f"[ERRORE] Impossibile connettersi al broker MQTT su {args.host}:{args.port}")
        print("Assicurati che il container Mosquitto sia in esecuzione!")
        return

    client.loop_start()
    print(f"=== Alvea PC Simulator ===")
    print(f"Broker: {args.host}:{args.port}")
    print(f"Topic:  {TOPIC}")
    print(f"Scenario Clinico: {args.scenario.upper()}")
    print("Premi Ctrl+C per fermare l'invio...\n")
    
    try:
        while True:
            payload = make_reading(args.scenario)
            client.publish(TOPIC, json.dumps(payload))
            print(f"TX: {json.dumps(payload, indent=2)}")
            time.sleep(1.0 / args.rate)
    except KeyboardInterrupt:
        print("\nSimulazione terminata.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()