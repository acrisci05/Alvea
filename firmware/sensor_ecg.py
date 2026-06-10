# sensor_ecg.py - Acquisizione ECG reale da sensore AD8232 + stima del BPM.
#
# L'algoritmo di rilevazione del battito e' quello tarato nella Fase 1 del
# progetto (vedi ecg_raw.py, modalita' "bpm"): derivata quadrata + soglia
# adattiva + periodo refrattario + mediana degli intervalli RR. E' ispirato
# all'algoritmo Pan-Tompkins (band-pass, derivata, squaring, soglia adattiva).
#
# Differenza rispetto a ecg_raw.py: qui la logica e' incapsulata in una classe
# NON bloccante. Il main loop possiede il timing di campionamento a 250 Hz e,
# per ogni campione, chiama feed(); una volta al secondo chiama compute_bpm().
import time
import machine

import config

# --- Cablaggio (Fase 1) ----------------------------------------------------
PIN_ECG       = 34   # OUTPUT AD8232 -> ADC1_CH6 (input-only, ok con WiFi attivo)
PIN_LO_PLUS   = 32   # LO+ leads-off
PIN_LO_MINUS  = 33   # LO- leads-off
LEADS_OFF_ACTIVE_HIGH = True   # alcuni cloni hanno logica invertita: metti False

# --- Parametri algoritmo (tarati in Fase 1) --------------------------------
SAMPLE_RATE_HZ      = 250
SAMPLE_PERIOD_US    = 1_000_000 // SAMPLE_RATE_HZ
BPM_WINDOW_S        = 6
REFRACTORY_MS       = 350      # max ~170 BPM, blocca doppio conteggio onda T
THRESHOLD_FACTOR    = 0.55     # k della soglia adattiva su derivata^2
MIN_PEAKS_IN_WINDOW = 4
MAX_PEAKS_IN_WINDOW = 18
PHYSIO_BPM_MIN      = 40
PHYSIO_BPM_MAX      = 180


def _median(lst):
    s = sorted(lst)
    n = len(s)
    if n == 0:
        return 0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


class ECGMonitor:
    """Wrapper hardware AD8232 + stima BPM non bloccante."""

    def __init__(self):
        self.adc = machine.ADC(machine.Pin(PIN_ECG))
        self.adc.atten(machine.ADC.ATTN_11DB)     # range ~0-3.3V
        self.adc.width(machine.ADC.WIDTH_12BIT)   # letture 0-4095
        self.lo_plus = machine.Pin(PIN_LO_PLUS, machine.Pin.IN)
        self.lo_minus = machine.Pin(PIN_LO_MINUS, machine.Pin.IN)

        self._deriv_sq = []      # ring buffer derivata^2 (2s)
        self._deriv_win = SAMPLE_RATE_HZ * 2
        self._peak_times = []    # istanti (ms) dei picchi nella finestra
        self._last_peak_ms = 0
        self._threshold = 0
        self._prev_v = 0
        self._i = 0

    # --- stato elettrodi ---------------------------------------------------
    def leads_off(self):
        if LEADS_OFF_ACTIVE_HIGH:
            return self.lo_plus.value() == 1 or self.lo_minus.value() == 1
        return self.lo_plus.value() == 0 or self.lo_minus.value() == 0

    def read_raw(self):
        return self.adc.read()

    def reset(self):
        self._deriv_sq = []
        self._peak_times = []
        self._last_peak_ms = 0
        self._prev_v = 0
        self._i = 0

    # --- da chiamare una volta per campione (250 Hz) -----------------------
    def feed(self, v):
        d = v - self._prev_v
        self._prev_v = v
        d_sq = d * d

        self._deriv_sq.append(d_sq)
        if len(self._deriv_sq) > self._deriv_win:
            self._deriv_sq.pop(0)

        # soglia adattiva ricalcolata ~10 Hz
        if self._i % 25 == 0 and len(self._deriv_sq) >= SAMPLE_RATE_HZ:
            mx = max(self._deriv_sq)
            mean = sum(self._deriv_sq) // len(self._deriv_sq)
            self._threshold = mean + int((mx - mean) * THRESHOLD_FACTOR)

        # picco: max locale stretto sopra soglia + refrattario
        if len(self._deriv_sq) >= 3 and self._threshold > 0:
            a, b, c = self._deriv_sq[-3], self._deriv_sq[-2], self._deriv_sq[-1]
            if b > self._threshold and b > a and b > c:
                now_ms = time.ticks_ms()
                if time.ticks_diff(now_ms, self._last_peak_ms) > REFRACTORY_MS:
                    self._peak_times.append(now_ms)
                    self._last_peak_ms = now_ms

        # pulizia finestra picchi (~ogni 50 campioni)
        if self._i % 50 == 0 and self._peak_times:
            cutoff = time.ticks_add(time.ticks_ms(), -BPM_WINDOW_S * 1000)
            self._peak_times = [t for t in self._peak_times
                                if time.ticks_diff(t, cutoff) > 0]
        self._i += 1

    # --- da chiamare ~1 volta al secondo -----------------------------------
    def compute_bpm(self):
        n = len(self._peak_times)
        if not (MIN_PEAKS_IN_WINDOW <= n <= MAX_PEAKS_IN_WINDOW):
            return 0
        rr = []
        for k in range(1, n):
            d = time.ticks_diff(self._peak_times[k], self._peak_times[k - 1])
            if 333 <= d <= 1500:           # 40-180 BPM fisiologici
                rr.append(d)
        if len(rr) < 3:
            return 0
        rr_med = _median(rr)
        if rr_med <= 0:
            return 0
        bpm = 60000 // rr_med
        if not (PHYSIO_BPM_MIN <= bpm <= PHYSIO_BPM_MAX):
            return 0
        return bpm
