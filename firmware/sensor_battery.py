# sensor_battery.py - Lettura percentuale batteria via partitore resistivo
# su ADC

import machine

# Pin ADC dedicato alla lettura della batteria.
PIN_BATTERY = 25
BATTERY_MONITORING_ENABLED = True

# Rapporto del partitore resistivo (Vbat = Vletto * RATIO)
DIVIDER_RATIO = 2.0

# Tensione LiPo 1S: 3.0V (scarica) - 4.2V (carica), curva di scarica non lineare.
VBAT_EMPTY = 3.0
VBAT_FULL = 4.2

# Numero di letture su cui mediare, per attenuare il rumore tipico di un
# ADC a 12 bit non isolato
N_SAMPLES = 8

class BatteryMonitor:
    """Wrapper per la lettura della percentuale di batteria residua."""

    def __init__(self):
        self._hardware_ok = False
        if BATTERY_MONITORING_ENABLED:
            try:
                self._adc = machine.ADC(machine.Pin(PIN_BATTERY))
                self._adc.atten(machine.ADC.ATTN_11DB)
                self._adc.width(machine.ADC.WIDTH_12BIT)
                self._hardware_ok = True
            except Exception as e:
                print("[HARDWARE ERROR] Errore inizializzazione ADC batteria:", e)
                self._hardware_ok = False

    def read_percent(self):
        """Restituisce la percentuale stimata di batteria (0-100) oppure None se il monitoraggio e' disabilitato
        o l'hardware non e'disponibile (in tal caso l'AlertManager non generera' alert)."""
        if not self._hardware_ok:
            return None

        try:
            total = 0
            for _ in range(N_SAMPLES):
                total += self._adc.read()
            raw_avg = total / N_SAMPLES

            # raw a 12 bit (0-4095) -> tensione sul pin (0-3.3V) -> Vbat reale
            v_pin = (raw_avg / 4095.0) * 3.3
            v_bat = v_pin * DIVIDER_RATIO

            pct = (v_bat - VBAT_EMPTY) / (VBAT_FULL - VBAT_EMPTY) * 100.0
            if pct < 0.0:
                pct = 0.0
            if pct > 100.0:
                pct = 100.0
            return pct
        except Exception as e:
            print("[BATTERY SENSOR ERROR]", e)
            return None