# sensor_ppg.py - Acquisizione PPG da sensore analogico a singolo canale (luce verde).
#
# Ruolo del PPG verde in questa architettura:
#  - rilevamento del contatto pelle (is_skin_on), tramite soglia sul
#    livello DC del canale verde;
#  - secondo canale per il rilevamento del battito (BPM via picchi),
#    indipendente dall'ECG, utile come cross-check.


import time
import machine
import config

# --- Parametro Sensore Analogico (ADC) - Singolo canale, luce verde ---
PIN_PPG_GREEN = 4

PPG_SAMPLE_RATE_HZ = 50
PPG_SAMPLE_PERIOD_US = 1_000_000 // PPG_SAMPLE_RATE_HZ

# BUFFER: 4 secondi, sufficiente per rilevare alcuni cicli cardiaci
# (40-180 bpm => periodo 0.33-1.5s) per la stima del BPM via picchi.
BUFFER_SIZE = PPG_SAMPLE_RATE_HZ * 4

# Soglia sul canale verde per determinare se il sensore aderisce alla pelle.
# L'ADC a 12-bit dell'ESP32 legge valori da 0 a 4095.
GREEN_CONTACT_THRESHOLD = 1000

# Refrattarieta' tra due picchi del battito (evita doppi conteggi sullo
# stesso battito), analoga a quella usata per l'ECG.
PEAK_REFRACTORY_MS = 350
MAX_PEAKS_IN_WINDOW = 12  # fino a ~180 bpm su una finestra di 4s


class PPGMonitor:
    """Wrapper per sensore ottico PPG a singolo canale (luce verde).

    Fornisce rilevamento del contatto pelle e una stima del BPM via
    analisi dei picchi sul canale verde, da usare come ridondanza
    rispetto al BPM derivato dall'ECG.
    """

    def __init__(self):
        self.adc_green = machine.ADC(machine.Pin(PIN_PPG_GREEN))
        self.adc_green.atten(machine.ADC.ATTN_11DB)   # Range 0 - 3.3V
        self.adc_green.width(machine.ADC.WIDTH_12BIT)  # Risoluzione 0-4095

        self._green_buffer = [0] * BUFFER_SIZE
        self._buf_ptr = 0
        self._buf_filled = False

        self._last_green_val = 0

        # Stato per il rilevamento dei picchi (battito) sul canale verde.
        self._prev_v = 0
        self._threshold = 0
        self._peak_times = [0] * MAX_PEAKS_IN_WINDOW
        self._peak_count = 0
        self._last_peak_ms = 0
        self._i = 0

    def is_skin_on(self):
        """Controlla se il dispositivo e' a contatto con la pelle, in base
        al livello DC (riflessione) del canale verde."""
        return self._last_green_val > GREEN_CONTACT_THRESHOLD

    def read_raw(self):
        """Lettura dal convertitore Analogico-Digitale (ADC) del canale verde."""
        return self.adc_green.read()

    def feed(self, green_val):
        """Alimenta il buffer circolare statico a frequenza costante (50 Hz)
        e aggiorna il rilevamento dei picchi per la stima del BPM."""
        self._last_green_val = green_val

        self._green_buffer[self._buf_ptr] = green_val
        self._buf_ptr += 1
        if self._buf_ptr >= BUFFER_SIZE:
            self._buf_ptr = 0
            self._buf_filled = True

        # Soglia adattiva semplice (ricalcolata ogni ~0.5s) sul buffer corrente
        if self._i % 25 == 0:
            valid_n = BUFFER_SIZE if self._buf_filled else max(self._buf_ptr, 1)
            valid_slice = self._green_buffer if self._buf_filled else self._green_buffer[:valid_n]
            mx = max(valid_slice)
            mn = min(valid_slice)
            self._threshold = mn + int((mx - mn) * 0.6)

        # Rilevamento del picco locale (il battito riduce la riflessione
        # del canale verde: il picco e' un massimo locale del segnale AC).
        if self._threshold > 0 and green_val > self._threshold:
            now_ms = time.ticks_ms()
            if time.ticks_diff(now_ms, self._last_peak_ms) > PEAK_REFRACTORY_MS:
                if self._peak_count < MAX_PEAKS_IN_WINDOW:
                    self._peak_times[self._peak_count] = now_ms
                    self._peak_count += 1
                else:
                    for k in range(1, MAX_PEAKS_IN_WINDOW):
                        self._peak_times[k - 1] = self._peak_times[k]
                    self._peak_times[MAX_PEAKS_IN_WINDOW - 1] = now_ms
                self._last_peak_ms = now_ms

        # Pulizia temporale dei picchi obsoleti (finestra di 4s)
        if self._i % 25 == 0 and self._peak_count > 0:
            window_ms = (BUFFER_SIZE * 1000) // PPG_SAMPLE_RATE_HZ
            cutoff = time.ticks_add(time.ticks_ms(), -window_ms)
            valid_peaks = 0
            for k in range(self._peak_count):
                if time.ticks_diff(self._peak_times[k], cutoff) > 0:
                    self._peak_times[valid_peaks] = self._peak_times[k]
                    valid_peaks += 1
            self._peak_count = valid_peaks

        self._i += 1

    def compute_bpm(self):
        """Stima il BPM dai picchi rilevati sul canale verde nella finestra corrente. Ritorna 0 se la stima non e' affidabile"""
        n = self._peak_count
        if n < 3:
            return 0

        rr = []
        for k in range(1, n):
            d = time.ticks_diff(self._peak_times[k], self._peak_times[k - 1])
            if 333 <= d <= 1500:
                rr.append(d)

        if len(rr) < 2:
            return 0

        rr_sorted = sorted(rr)
        m = len(rr_sorted)
        rr_med = rr_sorted[m // 2] if m % 2 == 1 else (rr_sorted[m // 2 - 1] + rr_sorted[m // 2]) // 2

        if rr_med <= 0:
            return 0
        bpm = 60000 // rr_med
        if not (40 <= bpm <= 180):
            return 0
        return bpm
