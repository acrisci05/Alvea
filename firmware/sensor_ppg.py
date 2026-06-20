# sensor_ppg.py - Acquisizione PPG da sensore analogico via ADC.
#
# IMPLEMENTAZIONE IN PRODUZIONE: Include filtro IIR Passa-Basso
# per la purificazione del segnale e calcolo accurato del Respiro.
#
# FIX (Code Review): i pin ADC erano in conflitto con altri sensori:
#   - PIN_PPG_RED era 34, identico a PIN_ECG (sensor_ecg.py) -> le due
#     letture analogiche (elettrodo ECG e fotodiodo PPG rosso) finivano
#     sullo stesso GPIO fisico, corrompendo entrambi i segnali.
#   - PIN_PPG_IR era 35, identico a PIN_NTC (sensor_temp.py) -> conflitto
#     latente se in futuro si passa a TEMP_MODE = "ntc".
# Sono stati spostati su GPIO36 (SVP/ADC1_CH0) e GPIO39 (SVN/ADC1_CH3),
# entrambi input-only e liberi rispetto a ECG (32/33/34) e TEMP (4/35).
# Verifica comunque sempre la corrispondenza con il cablaggio reale.
#
# FIX (Code Review): i buffer circolari erano implementati con liste
# Python fatte crescere via append()/pop(0). pop(0) su una lista e'
# un'operazione O(n) (deve riallineare tutti gli elementi), eseguita qui
# a 50 Hz su una finestra di 500 campioni: costosa e in contraddizione
# con la filosofia "zero allocazioni dinamiche" gia' adottata in
# sensor_ecg.py. Sono stati sostituiti con due array a dimensione fissa
# pre-allocati, scritti tramite indice circolare (stesso pattern del
# Ring Buffer usato per l'ECG).

import time
import machine
import config

# --- Parametri Sensore Analogico (ADC) ---
# Sostituisci questi pin con quelli effettivamente cablati sul tuo hardware
PIN_PPG_RED = 36
PIN_PPG_IR  = 39

PPG_SAMPLE_RATE_HZ = 50
PPG_SAMPLE_PERIOD_US = 1_000_000 // PPG_SAMPLE_RATE_HZ

# BUFFER: 10 secondi. Per il respiro (15-30 atti/min).
BUFFER_SIZE = PPG_SAMPLE_RATE_HZ * 10  

# Soglia Infrarosso per determinare se il sensore aderisce alla pelle.
# L'ADC a 12-bit dell'ESP32 legge valori da 0 a 4095. 
# 1000 è un valore di base per indicare la presenza di riflessione cutanea.
IR_CONTACT_THRESHOLD = 1000 

class PPGMonitor:
    """Wrapper per sensore ottico PPG analogico con calcolo SpO2 e Respiro."""

    def __init__(self):
        # Inizializzazione ADC per il canale Rosso
        self.adc_red = machine.ADC(machine.Pin(PIN_PPG_RED))
        self.adc_red.atten(machine.ADC.ATTN_11DB)   # Range 0 - 3.3V
        self.adc_red.width(machine.ADC.WIDTH_12BIT) # Risoluzione 0-4095
        
        # Inizializzazione ADC per il canale Infrarosso
        self.adc_ir = machine.ADC(machine.Pin(PIN_PPG_IR))
        self.adc_ir.atten(machine.ADC.ATTN_11DB)
        self.adc_ir.width(machine.ADC.WIDTH_12BIT)

        # PRODUZIONE: buffer circolari pre-allocati a dimensione fissa
        # (nessuna allocazione/deallocazione nel loop a 50 Hz).
        self._red_buffer = [0] * BUFFER_SIZE
        self._ir_buffer = [0] * BUFFER_SIZE
        self._buf_ptr = 0
        self._buf_filled = False

        self._last_ir_val = 0

    def is_skin_on(self):
        """Controlla se il dispositivo e' a contatto con la pelle."""
        return self._last_ir_val > IR_CONTACT_THRESHOLD

    def read_raw(self):
        """Lettura dai convertitori Analogico-Digitale (ADC)."""
        red_val = self.adc_red.read()
        ir_val = self.adc_ir.read()
        return red_val, ir_val

    def feed(self, red_val, ir_val):
        """Alimenta il buffer circolare statico a frequenza costante (50 Hz)."""
        self._last_ir_val = ir_val

        self._red_buffer[self._buf_ptr] = red_val
        self._ir_buffer[self._buf_ptr] = ir_val

        self._buf_ptr += 1
        if self._buf_ptr >= BUFFER_SIZE:
            self._buf_ptr = 0
            self._buf_filled = True

    def compute_metrics(self):
        """
        Elabora il buffer per restituire SpO2 e Frequenza Respiratoria filtrata.
        Da chiamare a ~1 Hz.
        """
        if not self._buf_filled:
            return 0.0, 0.0  # Buffer in riempimento

        # -------------------------------------------------------------
        # 1. Calcolo SpO2 (Ratio of Ratios)
        # -------------------------------------------------------------
        # Su un buffer circolare pieno, max/min/sum non dipendono
        # dall'ordine temporale: si puo' lavorare direttamente sugli
        # array cosi' come sono, senza ricostruirli in ordine.
        dc_red = sum(self._red_buffer) / BUFFER_SIZE
        dc_ir = sum(self._ir_buffer) / BUFFER_SIZE

        ac_red = max(self._red_buffer) - min(self._red_buffer)
        ac_ir = max(self._ir_buffer) - min(self._ir_buffer)

        if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
            return 0.0, 0.0

        ratio = (ac_red / dc_red) / (ac_ir / dc_ir)
        spo2 = 104.0 - (17.0 * ratio)
        if spo2 > 100.0: spo2 = 100.0
        if spo2 < 0.0: spo2 = 0.0

        # -------------------------------------------------------------
        # 2. Calcolo Frequenza Respiratoria (Filtro IIR Passa-Basso)
        # -------------------------------------------------------------
        # Qui l'ORDINE temporale conta (rilevazione di attraversamenti),
        # quindi ricostruiamo la sequenza cronologica a partire dal
        # puntatore circolare. Questa ricostruzione alloca una lista,
        # ma avviene solo qui, a ~1 Hz, non nel percorso a 50 Hz di feed().
        ordered_ir = self._ir_buffer[self._buf_ptr:] + self._ir_buffer[:self._buf_ptr]

        alpha = 0.05
        y_prev = ordered_ir[0]
        filtered_ir = [0.0] * BUFFER_SIZE
        s = 0.0
        for i in range(BUFFER_SIZE):
            y = alpha * ordered_ir[i] + (1.0 - alpha) * y_prev
            filtered_ir[i] = y
            y_prev = y
            s += y

        dc_filtered = s / BUFFER_SIZE

        crossings = 0
        for i in range(1, BUFFER_SIZE):
            if (filtered_ir[i-1] < dc_filtered) and (filtered_ir[i] >= dc_filtered):
                crossings += 1

        window_seconds = BUFFER_SIZE / PPG_SAMPLE_RATE_HZ
        resp_rate = crossings * (60.0 / window_seconds)

        return round(spo2, 1), round(resp_rate, 1)
