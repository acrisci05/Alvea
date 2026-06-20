# ntp_time.py - Sincronizzazione RTC via NTP per ottenere Unix timestamp reali.
#
# PROBLEMA RISOLTO: su MicroPython/ESP32, time.time() di default conta i
# secondi dall'epoca MicroPython (2000-01-01), NON dall'epoca Unix
# (1970-01-01). Se l'RTC non viene sincronizzato via NTP, ogni record
# scritto su InfluxDB avra' un timestamp sbagliato di ~30 anni, rompendo
# silenziosamente tutte le query temporali e i grafici Grafana.
#
# Questo modulo va chiamato UNA VOLTA dopo la connessione Wi-Fi, prima di
# iniziare a pubblicare telemetria.

import time

try:
    import ntptime
except ImportError:
    ntptime = None


def sync_time(max_retries=3, retry_delay_s=2):
    """Sincronizza l'RTC interno con un server NTP.

    Ritorna True se la sincronizzazione e' riuscita, False altrimenti.
    In caso di fallimento il chiamante puo' decidere se continuare
    comunque (segnalando un device_status di tipo WARN) o riprovare.
    """
    if ntptime is None:
        print("[NTP] Modulo ntptime non disponibile su questo firmware.")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            ntptime.settime()  # imposta l'RTC in UTC
            now = time.time()
            print("[NTP] Sincronizzazione riuscita. Unix time corrente:", now)
            return True
        except Exception as e:
            print(f"[NTP] Tentativo {attempt}/{max_retries} fallito:", e)
            time.sleep(retry_delay_s)

    print("[NTP] ATTENZIONE: impossibile sincronizzare l'ora. "
          "I timestamp potrebbero essere errati (epoca MicroPython, non Unix).")
    return False
