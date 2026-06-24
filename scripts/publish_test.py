#!/usr/bin/env python3
"""publish_test.py - Simulatore di telemetria Alvea dal PC.

Pubblica letture simulate su MQTT esattamente come farebbe l'ESP32 di produzione, 
per testare la pipeline (Node-RED -> InfluxDB -> Grafana -> App) senza l'hardware fisico.

Uso:
    pip install paho-mqtt
    python publish_test.py                                      # nominale, 1 Hz
    python publish_test.py --scenario asthma_attack             # test allarme asma
    python publish_test.py --scenario hardware_fault            # test disconnessione sensore
"""
import argparse
import json
import random
import time

import paho.mqtt.client as mqtt

DEVICE_ID = "ALVEA_ASTHMA_ANKLE_01"
TOPIC = f"alvea/devices/{DEVICE_ID}/telemetry"

def make_reading(scenario):
    """Genera un dizionario payload JSON identico a quello dell'ESP32 reale."""
    contact = True
    status = "SYSTEM_OK"
    
    # 1. SCENARIO: Sensore staccato o guasto hardware
    if scenario == "hardware_fault":
        contact = False
        status = "ERR_ECG_LEADS_OFF"
        bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0
        
    # 2. SCENARIO: Attacco d'asma (Tachipnea + Tachicardia)
    elif scenario == "asthma_attack":
        bpm = round(random.uniform(115.0, 130.0), 1)         # Battito accelerato
        skin_temp = round(random.uniform(31.5, 33.5), 1)
        resp_rate = round(random.uniform(40.0, 50.0), 1)     # Respiro affannoso (Tachipnea)
        
    # 3. SCENARIO: Febbre (Temperatura cutanea periferica elevata)
    elif scenario == "fever":
        bpm = round(random.uniform(110.0, 120.0), 1)
        skin_temp = round(random.uniform(35.5, 37.0), 1)     # Cute periferica molto calda
        resp_rate = round(random.uniform(25.0, 32.0), 1)
        
    # 4. SCENARIO: Nominale (Bambino a riposo/sano)
    else:
        # Drop accidentale del sensore (5% di probabilita' nella vita reale)
        if random.random() < 0.05:
            contact = False
            status = "ERR_ECG_LEADS_OFF"
            bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0
        else:
            bpm = round(random.uniform(90.0, 110.0), 1)
            skin_temp = round(random.uniform(31.0, 34.0), 1) # Range cutaneo normale caviglia
            resp_rate = round(random.uniform(20.0, 30.0), 1)

    return {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "bpm": bpm,
        "respiration_rate": resp_rate,
        "skin_temperature": skin_temp,
        "sensor_contact": contact,
        "device_status": status,
        "source": "sim-pc-script",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost", help="IP del broker MQTT (es. 192.168.1.50)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--rate", type=float, default=1.0, help="Frequenza di invio (messaggi al secondo)")
    ap.add_argument("--scenario", choices=["nominal", "asthma_attack", "fever", "hardware_fault"], default="nominal")
    
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
