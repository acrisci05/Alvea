#!/usr/bin/env python3
"""publish_test.py - Simulatore di telemetria Alvea dal PC.

Pubblica letture simulate su MQTT esattamente come farebbe l'ESP32 di produzione, 
per testare la pipeline (Node-RED -> InfluxDB -> Grafana -> App) senza l'hardware fisico.

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
TOPIC = f"alvea/devices/{DEVICE_ID}/telemetry" 

# Stato persistente tra una chiamata e l'altra (valori correnti del "paziente simulato")
_state = {"bpm": 100.0, "skin_temp": 36.6, "resp": 25.0}

def _walk(current, target_min, target_max, step):
    """Sposta 'current' di un piccolo passo casuale, restando nel range."""
    current += random.uniform(-step, step)
    return max(target_min, min(target_max, current))

def make_reading(scenario):
    """Genera un dizionario payload JSON identico a quello dell'ESP32 reale,
    con valori che evolvono gradualmente invece di saltare a caso ogni secondo."""
    contact = True
    battery = round(random.uniform(60.0, 90.0), 1)

    # 1. SCENARIO: Sensore staccato o guasto hardware
    if scenario == "hardware_fault":
        contact = False
        bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0

    # 2. SCENARIO: Attacco d'asma (Tachipnea + Tachicardia lieve).
    #    Sale gradualmente verso i valori di crisi invece di partire già alto.
    elif scenario == "asthma_attack":
        _state["bpm"] = _walk(_state["bpm"], 120.0, 140.0, 2.0)
        _state["skin_temp"] = _walk(_state["skin_temp"], 36.3, 37.0, 0.2)
        _state["resp"] = _walk(_state["resp"], 64.0, 74.0, 1.5)
        bpm = round(_state["bpm"], 1)
        skin_temp = round(_state["skin_temp"], 1)
        resp_rate = round(_state["resp"], 1)

    # 3. SCENARIO: Nominale (Bambino a riposo/sano)
    else:
        if random.random() < 0.02:  # contatto perso più raro, non ad ogni tick
            contact = False
            bpm, skin_temp, resp_rate = 0.0, 0.0, 0.0
        else:
            _state["bpm"] = _walk(_state["bpm"], 90.0, 110.0, 1.5)
            _state["skin_temp"] = _walk(_state["skin_temp"], 36.3, 37.0, 0.15)
            _state["resp"] = _walk(_state["resp"], 20.0, 30.0, 0.8)
            bpm = round(_state["bpm"], 1)
            skin_temp = round(_state["skin_temp"], 1)
            resp_rate = round(_state["resp"], 1)

    # device_status: stringhe coerenti a quelle del firmware
    status = "SYSTEM_OK" if contact else "ERR_ECG_LEADS_OFF"

    return {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "bpm": bpm,
        "skin_temperature": skin_temp,
        "respiration_rate": resp_rate,
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
