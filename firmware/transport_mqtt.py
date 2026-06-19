# transport_mqtt.py - Pubblicazione resiliente e sottoscrizione comandi.

import json
import time
from umqtt.simple import MQTTClient
import config

class MQTTPublisher:
    def __init__(self, message_callback=None):
        self.client = MQTTClient(config.DEVICE_ID, config.MQTT_BROKER, port=config.MQTT_PORT)
        self.is_connected = False
        self._last_reconnect_attempt = 0
        self._reconnect_interval = 5 
        
        # Imposta la funzione da eseguire quando arriva un messaggio (Requisito 8)
        if message_callback:
            self.client.set_callback(message_callback)

    def connect(self):
        try:
            self.client.connect()
            self.is_connected = True
            print("MQTT: Connesso con successo al broker.")
            
            # Sottoscrizione al topic dei comandi non appena connesso
            self.client.subscribe(config.TOPIC_CMD)
            print("MQTT: In ascolto su", config.TOPIC_CMD)
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def check_connection(self):
        """Macchina a stati per la gestione della rete."""
        if self.is_connected:
            return True
            
        now = time.time()
        if now - self._last_reconnect_attempt >= self._reconnect_interval:
            self._last_reconnect_attempt = now
            print("MQTT: Tentativo di riconnessione in background...")
            return self.connect()
        return False

    def check_messages(self):
        """Metodo non bloccante per leggere i messaggi in arrivo dal backend."""
        if self.is_connected:
            try:
                # Controlla la posta: se c'e' un messaggio, lancia la callback
                self.client.check_msg()
            except Exception as e:
                print("MQTT: Errore durante la ricezione messaggi:", e)
                self.is_connected = False

    def publish(self, payload_dict):
        """Invia il dato se connesso."""
        if not self.is_connected:
            return False
        try:
            self.client.publish(config.TOPIC_DATA, json.dumps(payload_dict))
            return True
        except Exception as e:
            print("MQTT: Errore di invio spontaneo, disconnessione rilevata.")
            self.is_connected = False
            return False