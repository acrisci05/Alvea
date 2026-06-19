# wifi.py - Connessione Wi-Fi Station resiliente per produzione.

import network
import time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    def is_connected(self):
        return self.wlan.isconnected()

    def rinfresca_connessione(self):
        """Gestisce la riconnessione automatica senza bloccare il codice clinico."""
        if not self.wlan.isconnected():
            if not self.wlan.status() == network.STAT_CONNECTING:
                print("Wi-Fi: Connessione persa. Tentativo di riaggancio...")
                self.wlan.connect(self.ssid, self.password)
        else:
            # Ottimizzazione energetica: disabilita il power saving solo se necessario per latenza
            pass