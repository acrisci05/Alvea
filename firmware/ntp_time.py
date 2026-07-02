# ntp_time.py - Sincronizzazione RTC via NTP per ottenere Unix timestamp reali.
#
# Questo modulo va chiamato una volta dopo la connessione Wi-Fi, prima di
# iniziare a pubblicare telemetria.

import time

try:
    import ntptime
except ImportError:
    ntptime = None


def sync_time(max_retries=3, retry_delay_s=2):
    """Sincronizza l'RTC interno con un server NTP.
    Ritorna True se la sincronizzazione e' riuscita, False altrimenti. In caso di fallimento il chiamante puo' decidere
    se continuare comunque (segnalando un device_status di tipo WARN) o riprovare.
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


# Secondi tra 1970-01-01 (epoca Unix) e 2000-01-01 (epoca MicroPython su ESP32).
UNIX_EPOCH_OFFSET = 946684800


def unix_time():
    """Ora corrente come timestamp Unix (secondi dal 1970), convertendo
    l'epoca MicroPython dell'RTC ESP32 in epoca Unix."""
    return time.time() + UNIX_EPOCH_OFFSET
