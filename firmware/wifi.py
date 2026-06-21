# wifi.py - Connessione Wi-Fi Station resiliente per produzione.

import network
import time

WIFI_CONNECT_TIMEOUT_S = 15

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self._connect_attempt_started = None

    def is_connected(self):
        return self.wlan.isconnected()

    def rinfresca_connessione(self):
        """Gestisce la riconnessione automatica senza bloccare il codice clinico."""
        if self.wlan.isconnected():
            # Connessione attiva: resetta lo stato del tentativo.
            self._connect_attempt_started = None
            return

        status = self.wlan.status()

        if status == network.STAT_CONNECTING:
            # Tentativo in corso: controllo se il timeout è stato superato.
            if self._connect_attempt_started is None:
                self._connect_attempt_started = time.time()
            elif time.time() - self._connect_attempt_started > WIFI_CONNECT_TIMEOUT_S:
                print("Wi-Fi: tentativo di connessione in timeout, riavvio l'aggancio...")
                self.wlan.disconnect()
                self._connect_attempt_started = None
            return

        # Non connesso e non in fase di connessione: avvia un nuovo tentativo.
        print("Wi-Fi: Connessione persa. Tentativo di riaggancio...")
        self.wlan.connect(self.ssid, self.password)
        self._connect_attempt_started = time.time()