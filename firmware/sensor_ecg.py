# sensor_ecg.py - Acquisizione ECG reale da sensore AD8232 + stima del BPM.

import time
import machine
import config

# --- Cablaggio ---
PIN_ECG       = 34   
PIN_LO_PLUS   = 32   
PIN_LO_MINUS  = 33   
LEADS_OFF_ACTIVE_HIGH = True   

# --- Parametri algoritmo ---
SAMPLE_RATE_HZ      = 250
SAMPLE_PERIOD_US    = 1_000_000 // SAMPLE_RATE_HZ
BPM_WINDOW_S        = 6
REFRACTORY_MS       = 350      
THRESHOLD_FACTOR    = 0.55     
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
    """Wrapper hardware AD8232 con Ring Buffer statico privo di allocazioni dinamiche."""

    def __init__(self):
        self.adc = machine.ADC(machine.Pin(PIN_ECG))
        self.adc.atten(machine.ADC.ATTN_11DB)     
        self.adc.width(machine.ADC.WIDTH_12BIT)   
        self.lo_plus = machine.Pin(PIN_LO_PLUS, machine.Pin.IN)
        self.lo_minus = machine.Pin(PIN_LO_MINUS, machine.Pin.IN)
        
        self._deriv_win = SAMPLE_RATE_HZ * 2
        self._deriv_sq = [0] * self._deriv_win  
        self._deriv_ptr = 0 # Indice di scrittura corrente
        self._buffer_filled = False

        # Array statico per i picchi (massimo teorico nella finestra)
        self._peak_times = [0] * MAX_PEAKS_IN_WINDOW
        self._peak_count = 0
        
        self._last_peak_ms = 0
        self._threshold = 0
        self._prev_v = 0
        self._i = 0

    def leads_off(self):
        if LEADS_OFF_ACTIVE_HIGH:
            return self.lo_plus.value() == 1 or self.lo_minus.value() == 1
        return self.lo_plus.value() == 0 or self.lo_minus.value() == 0

    def read_raw(self):
        return self.adc.read()

    def reset(self):
        self._deriv_sq = [0] * self._deriv_win
        self._deriv_ptr = 0
        self._buffer_filled = False
        self._peak_count = 0
        self._last_peak_ms = 0
        self._prev_v = 0
        self._i = 0

    def feed(self, v):
        """Alimenta l'algoritmo (250 Hz) senza generare spazzatura in memoria."""
        d = v - self._prev_v
        self._prev_v = v
        d_sq = d * d

        # Scrittura nel Ring Buffer statico
        self._deriv_sq[self._deriv_ptr] = d_sq
        
        # Recuperiamo gli ultimi 3 elementi storici mappando l'indice circolare
        idx_c = self._deriv_ptr
        idx_b = (self._deriv_ptr - 1) % self._deriv_win
        idx_a = (self._deriv_ptr - 2) % self._deriv_win
        
        a, b, c = self._deriv_sq[idx_a], self._deriv_sq[idx_b], self._deriv_sq[idx_c]

        # Avanzamento del puntatore circolare
        self._deriv_ptr += 1
        if self._deriv_ptr >= self._deriv_win:
            self._deriv_ptr = 0
            self._buffer_filled = True

        # Ricalcolo soglia adattiva (~10 Hz)
        if self._i % 25 == 0 and (self._buffer_filled or self._deriv_ptr >= SAMPLE_RATE_HZ):
            valid_n = self._deriv_win if self._buffer_filled else self._deriv_ptr
            valid_slice = self._deriv_sq[:valid_n] if not self._buffer_filled else self._deriv_sq
            mx = max(valid_slice)
            mean = sum(valid_slice) // valid_n
            self._threshold = mean + int((mx - mean) * THRESHOLD_FACTOR)

        # Analisi del picco locale
        if self._threshold > 0:
            if b > self._threshold and b > a and b > c:
                now_ms = time.ticks_ms()
                if time.ticks_diff(now_ms, self._last_peak_ms) > REFRACTORY_MS:
                    # Registrazione del picco nel buffer circolare dei picchi
                    if self._peak_count < MAX_PEAKS_IN_WINDOW:
                        self._peak_times[self._peak_count] = now_ms
                        self._peak_count += 1
                    else:
                        # Se il buffer e' pieno, scala gli elementi (operazione rara, solo sui picchi)
                        for k in range(1, MAX_PEAKS_IN_WINDOW):
                            self._peak_times[k-1] = self._peak_times[k]
                        self._peak_times[MAX_PEAKS_IN_WINDOW-1] = now_ms
                    self._last_peak_ms = now_ms

        # Pulizia temporale dei picchi obsoleti fuori dalla finestra di 6 secondi
        if self._i % 50 == 0 and self._peak_count > 0:
            cutoff = time.ticks_add(time.ticks_ms(), -BPM_WINDOW_S * 1000)
            valid_peaks = 0
            for k in range(self._peak_count):
                if time.ticks_diff(self._peak_times[k], cutoff) > 0:
                    self._peak_times[valid_peaks] = self._peak_times[k]
                    valid_peaks += 1
            self._peak_count = valid_peaks

        self._i += 1

    def compute_bpm(self):
        n = self._peak_count
        if not (MIN_PEAKS_IN_WINDOW <= n <= MAX_PEAKS_IN_WINDOW):
            return 0
        
        # Calcolo intervalli RR (memorizzazione temporanea ristretta)
        rr = []
        for k in range(1, n):
            d = time.ticks_diff(self._peak_times[k], self._peak_times[k - 1])
            if 333 <= d <= 1500:
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