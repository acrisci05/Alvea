# transport_mqtt.py - Pubblicazione resiliente e sottoscrizione comandi.

import json
import time
from umqtt.simple import MQTTClient
import config

try:
    import secrets
    _MQTT_BROKER = getattr(secrets, "MQTT_BROKER", config.MQTT_BROKER)
    _MQTT_USER = getattr(secrets, "MQTT_USER", config.MQTT_USER)
    _MQTT_PASS = getattr(secrets, "MQTT_PASS", config.MQTT_PASS)
    
except ImportError:
    _MQTT_BROKER = config.MQTT_BROKER
    _MQTT_USER = config.MQTT_USER
    _MQTT_PASS = config.MQTT_PASS


class MQTTPublisher:
    def __init__(self, message_callback=None):
        self.client = MQTTClient(
            config.DEVICE_ID,
            _MQTT_BROKER,
            port=config.MQTT_PORT,
            user=_MQTT_USER,
            password=_MQTT_PASS,
        )
        self.is_connected = False
        self._last_reconnect_attempt = 0
        self._reconnect_interval = 5 
        
        # Imposta la funzione da eseguire quando arriva un messaggio
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
            print("MQTT: Connessione al broker fallita:", e)
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

    def publish_to(self, topic, payload_dict):
        """Invia un dizionario come JSON su un topic arbitrario, se connesso.
        Centralizza la logica di invio/gestione errori: sia publish()
        (telemetria su TOPIC_DATA) sia AlertManager (alert su TOPIC_ALERT,
        vedi alerts.py) passano da qui, invece di duplicare il try/except
        e l'aggiornamento di is_connected in piu' punti del firmware.
        """
        if not self.is_connected:
            return False
        try:
            self.client.publish(topic, json.dumps(payload_dict))
            return True
        except Exception as e:
            print("MQTT: Errore di invio, disconnessione rilevata su topic", topic, ":", e)
            self.is_connected = False
            return False

    def publish(self, payload_dict):
        """Invia il dato di telemetria sul topic dati standard."""
        return self.publish_to(config.TOPIC_DATA, payload_dict)