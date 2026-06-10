# wifi.py - Connessione Wi-Fi locale per l'ESP32 (modalita' Station)
import network
import time

import config

def connetti_wifi(ssid, password, timeout_s=10):
    """Connette l'ESP32 alla rete Wi-Fi domestica (WPA2/WPA3).

    Restituisce True se connesso, False altrimenti. Non solleva eccezioni:
    il chiamante decide cosa fare in caso di fallimento (es. reset).
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Ricerca rete in corso:", ssid)
        wlan.connect(ssid, password)
        tentativi = 0
        while not wlan.isconnected() and tentativi < timeout_s:
            print("Tentativo di connessione...")
            time.sleep(1)
            tentativi += 1

    if wlan.isconnected():
        cfg = wlan.ifconfig()
        print("\n--- Connessione Wi-Fi stabilita ---")
        print("IP ESP32 :", cfg[0])
        print("Gateway  :", cfg[2])
        print("-----------------------------------\n")
        return True

    print("\n[ERRORE] Connessione Wi-Fi fallita. Controlla SSID/Password.")
    return False
