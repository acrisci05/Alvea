# sensor_ecg.py - Acquisizione ECG reale da sensore AD8232, stima del BPM ed
# estrazione degli intervalli RR grezzi.
#
# Gli intervalli RR della finestra estesa (get_rr_history) sono la base
# dati da cui il modulo resp_edr.py deriva la Frequenza Respiratoria
# (tecnica EDR, ECG-Derived Respiration, basata sull'Aritmia Sinusale
# Respiratoria). La finestra breve (BPM_WINDOW_S, 6s, get_rr_intervals)
# resta dedicata al solo BPM istantaneo, perche' troppo corta per stimare
# in modo stabile un respiro a 15-30 atti/min.

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

# --- Finestra estesa per EDR (Frequenza Respiratoria) ---
# Il respiro (15-30 atti/min) richiede diversi cicli respiratori per
# essere stimato in modo stabile: una finestra di 6s (quella usata per
# il BPM istantaneo) e' troppo corta. Si usa quindi una finestra dedicata,
# piu' ampia, alimentata in parallelo dagli stessi picchi R rilevati.
RR_HISTORY_S = 30

# Dimensionamento statico: nel caso peggiore (tachicardia sostenuta a
# 180 bpm, RR minimo plausibile 333ms) si arriva a ~91 intervalli RR in
# 30s. Il margine va oltre il minimo teorico per assorbire jitter di
# campionamento senza che il ring buffer risulti "sempre pieno al limite".
MAX_RR_HISTORY = (PHYSIO_BPM_MAX * RR_HISTORY_S) // 60 + 10

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

        # Ring buffer statico separato per la finestra estesa (RR_HISTORY_S) usata dall'EDR.
        # Memorizza direttamente gli intervalli RR (ms),
        # non i timestamp dei picchi, perche' a quella finestra interessa
        # solo la sequenza di RR, non il singolo istante del picco.
        self._rr_hist = [0] * MAX_RR_HISTORY
        self._rr_hist_ptr = 0
        self._rr_hist_count = 0
        self._last_rr_peak_ms = None  # timestamp dell'ultimo picco usato per calcolare un RR

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
        # Il contatto si e' perso (es. elettrodi scollegati): la sequenza
        # di RR successiva non e' fisiologicamente continua rispetto alla
        # precedente, quindi la finestra estesa EDR viene azzerata per
        # non mescolare RR pre/post interruzione.
        self._rr_hist_ptr = 0
        self._rr_hist_count = 0
        self._last_rr_peak_ms = None

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

                    # Alimentazione della finestra estesa RR (EDR):
                    # calcoliamo l'RR rispetto al picco precedente e lo
                    # scriviamo nel ring buffer statico, senza riallocare
                    # memoria (stesso pattern del buffer derivativo sopra).
                    if self._last_rr_peak_ms is not None:
                        rr = time.ticks_diff(now_ms, self._last_rr_peak_ms)
                        if 333 <= rr <= 1500:
                            self._rr_hist[self._rr_hist_ptr] = rr
                            self._rr_hist_ptr += 1
                            if self._rr_hist_ptr >= MAX_RR_HISTORY:
                                self._rr_hist_ptr = 0
                            if self._rr_hist_count < MAX_RR_HISTORY:
                                self._rr_hist_count += 1
                    self._last_rr_peak_ms = now_ms

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

    def get_rr_intervals(self):
        """Restituisce la lista degli intervalli RR (in ms) validi nella
        finestra BREVE (BPM_WINDOW_S, 6s), usata per il BPM istantaneo.
        """
        n = self._peak_count
        if n < 2:
            return []

        rr = []
        for k in range(1, n):
            d = time.ticks_diff(self._peak_times[k], self._peak_times[k - 1])
            if 333 <= d <= 1500:
                rr.append(d)
        return rr

    def get_rr_history(self):
        """Restituisce la lista degli intervalli RR (in ms) della finestra
        ESTESA (RR_HISTORY_S, default 30s), in ordine cronologico.

        E' la base dati da cui resp_edr.py deriva l'EDR (Frequenza
        Respiratoria), perche' questa metrica necessita di piu' cicli
        respiratori per essere stabile, a differenza del BPM istantaneo
        che usa get_rr_intervals().
        """
        if self._rr_hist_count == 0:
            return []
        if self._rr_hist_count < MAX_RR_HISTORY:
            # Buffer non ancora pieno: i dati validi sono semplicemente i
            # primi _rr_hist_count elementi scritti in ordine.
            return self._rr_hist[:self._rr_hist_count]
        # Buffer pieno e circolare: l'ordine cronologico riparte dal
        # puntatore di scrittura corrente (il piu' vecchio).
        return self._rr_hist[self._rr_hist_ptr:] + self._rr_hist[:self._rr_hist_ptr]

    def compute_bpm(self):
        n = self._peak_count
        if not (MIN_PEAKS_IN_WINDOW <= n <= MAX_PEAKS_IN_WINDOW):
            return 0

        rr = self.get_rr_intervals()
        if len(rr) < 3:
            return 0
            
        rr_med = _median(rr)
        if rr_med <= 0:
            return 0
            
        bpm = 60000 // rr_med
        if not (PHYSIO_BPM_MIN <= bpm <= PHYSIO_BPM_MAX):
            return 0
        return bpm