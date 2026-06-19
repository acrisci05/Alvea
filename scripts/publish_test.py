#!/usr/bin/env python3
"""publish_test.py - Simulatore di telemetria Alvea dal PC.

Pubblica letture simulate su MQTT esattamente come farebbe l'ESP32, per testare
tutta la pipeline (Node-RED -> InfluxDB -> Grafana e il backend) senza hardware.

Uso:
    pip install paho-mqtt
    python publish_test.py                 # broker localhost, 1 Hz
    python publish_test.py --host 192.168.1.50 --rate 2 --scenario tachi
"""
import argparse
import json
import random
import time

import paho.mqtt.client as mqtt

TOPIC = "alvea/data"
DEVICE_ID = "ALVEA_04"


def make_reading(scenario):
    contact = random.random() > 0.05
    if not contact:
        bpm, temp = 0.0, 0.0
    elif scenario == "tachi":          # tachicardia (test allarme)
        bpm = round(random.uniform(165, 180), 1)
        temp = round(random.uniform(36.3, 36.9), 1)
    elif scenario == "fever":          # febbre (test allarme)
        bpm = round(random.uniform(120, 140), 1)
        temp = round(random.uniform(38.5, 39.2), 1)
    else:                              # nominale
        bpm = round(random.uniform(115, 125), 1)
        temp = round(random.uniform(36.3, 36.9), 1)
    return {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "bpm": bpm,
        "temperature": temp,
        "sensor_contact": contact,
        "source": "sim-pc",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--rate", type=float, default=1.0, help="messaggi al secondo")
    ap.add_argument("--scenario", choices=["nominal", "tachi", "fever"], default="nominal")
    args = ap.parse_args()

    client = mqtt.Client()
    client.connect(args.host, args.port, 60)
    client.loop_start()
    print(f"Pubblico su {args.host}:{args.port} topic '{TOPIC}' scenario={args.scenario}")
    try:
        while True:
            r = make_reading(args.scenario)
            client.publish(TOPIC, json.dumps(r))
            print("TX:", r)
            time.sleep(1.0 / args.rate)
    except KeyboardInterrupt:
        print("\nStop.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
