# sensor_ecg.py - Acquisizione ECG reale da sensore AD8232 + stima del BPM.
# VERSIONE DI PRODUZIONE: Allocazione di memoria statica (Zero Garbage Collector)

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

# --- EDR (ECG-Derived Respiration) ---
# Il respiro modula lentamente la linea di base dell'ECG (baseline wandering).
# Sotto-campioniamo l'ECG a 25 Hz e isoliamo la componente respiratoria con un
# filtro IIR passa-basso, poi contiamo gli attraversamenti dello zero.
EDR_DIVIDER   = 10                          # 250 Hz / 10 = 25 Hz
EDR_WINDOW_S  = 12
EDR_BUF_SIZE  = (SAMPLE_RATE_HZ // EDR_DIVIDER) * EDR_WINDOW_S
EDR_ALPHA     = 0.1                         # taglio ~0.5 Hz: tiene solo il respiro
PHYSIO_RESP_MIN = 5
PHYSIO_RESP_MAX = 60

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

        # PRODUZIONE: Buffer circolare pre-allocato a dimensione fissa
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

        # EDR: buffer del segnale sotto-campionato per la stima del respiro
        self._edr_buf = []
        self._edr_div = 0

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
        self._edr_buf = []
        self._edr_div = 0

    def feed(self, v):
        """Alimenta l'algoritmo (250 Hz) senza generare spazzatura in memoria."""
        # --- EDR: accumulo sotto-campionato (25 Hz) per la stima del respiro ---
        self._edr_div += 1
        if self._edr_div >= EDR_DIVIDER:
            self._edr_div = 0
            self._edr_buf.append(v)
            if len(self._edr_buf) > EDR_BUF_SIZE:
                self._edr_buf.pop(0)

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
            mx = max(self._deriv_sq)
            mean = sum(self._deriv_sq) // self._deriv_win
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

    def compute_resp_rate(self):
        """Stima la frequenza respiratoria (atti/min) dall'ECG via EDR.

        Filtra la linea di base sotto-campionata con un IIR passa-basso e conta
        gli attraversamenti (rising) della media: ogni attraversamento = 1 ciclo
        respiratorio. Da chiamare a ~1 Hz.
        """
        if len(self._edr_buf) < EDR_BUF_SIZE:
            return 0.0  # finestra in riempimento

        # Filtro IIR passa-basso: isola l'onda respiratoria sopprimendo il QRS
        filtered = []
        y_prev = self._edr_buf[0]
        for x in self._edr_buf:
            y = EDR_ALPHA * x + (1.0 - EDR_ALPHA) * y_prev
            filtered.append(y)
            y_prev = y

        baseline = sum(filtered) / len(filtered)

        crossings = 0
        for k in range(1, len(filtered)):
            if (filtered[k - 1] < baseline) and (filtered[k] >= baseline):
                crossings += 1

        resp = crossings * (60.0 / EDR_WINDOW_S)
        if not (PHYSIO_RESP_MIN <= resp <= PHYSIO_RESP_MAX):
            return 0.0
        return round(resp, 1)
