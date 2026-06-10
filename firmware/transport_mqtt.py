# transport_mqtt.py - Pubblicazione telemetria su broker MQTT (Mosquitto).
import json
import machine
from umqtt.simple import MQTTClient

import config


class MQTTPublisher:
    def __init__(self):
        self.client = MQTTClient(config.DEVICE_ID, config.MQTT_BROKER,
                                 port=config.MQTT_PORT)

    def connect(self):
        self.client.connect()
        print("MQTT: connesso a", config.MQTT_BROKER)

    def publish(self, payload_dict):
        self.client.publish(config.TOPIC_DATA, json.dumps(payload_dict))

    def reconnect_forever(self):
        """Tenta la riconnessione finche' non riesce (backoff fisso)."""
        import time
        while True:
            try:
                self.connect()
                return
            except Exception as e:
                print("MQTT: retry connessione:", e)
                time.sleep(5)
