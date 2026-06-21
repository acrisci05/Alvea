# sensor_battery.py - Lettura percentuale batteria via partitore resistivo
# su ADC (Requisito 1 - "eventuale stato del dispositivo"; Requisito 2/7 -
# "batteria bassa del dispositivo" tra gli esempi espliciti di condizione
# anomala da segnalare).
#
# AGGIUNTO (Code Review): nessuno dei main_*.py leggeva mai la batteria,
# pur essendo gia' presente in alerts.py il metodo AlertManager.check_battery()
# e in config.py la soglia DEFAULT_ALARM_BATTERY_MIN_PCT. Il Requisito 7
# cita esplicitamente "batteria bassa del dispositivo" come esempio di
# condizione anomala: senza questo modulo il requisito non era
# dimostrabile su nessuna delle 4 pipeline (reale o simulata).
#
# CABLAGGIO DI RIFERIMENTO (da verificare/adattare all'hardware reale):
# Batteria LiPo 1S (3.0V-4.2V) -> partitore resistivo 2:1 (es. due
# resistenze da 100k) -> pin ADC libero. Il partitore e' necessario
# perche' l'ADC dell'ESP32 con attenuazione 11dB legge correttamente solo
# tensioni fino a ~3.3V, mentre una LiPo carica supera questa soglia.
#
# Se il progetto non prevede un partitore hardware dedicato (es. si usa
# un modulo di alimentazione con pin "BAT" gia' condizionato, o non si
# dispone di un canale ADC libero), e' possibile in alternativa:
#  - leggere la batteria via I2C da un fuel gauge dedicato (es. MAX17048),
#  - oppure, in assenza di qualunque hardware di monitoraggio batteria,
#    disabilitare questo modulo (vedi BATTERY_MONITORING_ENABLED) e
#    documentare la scelta nella relazione, lasciando comunque la soglia
#    e l'alert pronti per un'eventuale estensione futura.

import machine

# Pin ADC dedicato alla lettura della batteria. Libero rispetto a ECG
# (32/33/34), PPG (36/39) e TEMP (4 per DS18B20, 35 per NTC).
PIN_BATTERY = 25

# Imposta a False se l'hardware reale non dispone di un partitore di
# tensione per la batteria: in tal caso check() restituisce sempre None
# e l'AlertManager semplicemente non generera' mai l'alert di batteria
# scarica (nessun crash, nessun falso allarme).
BATTERY_MONITORING_ENABLED = True

# Rapporto del partitore resistivo (Vbat = Vletto * RATIO). Con due
# resistenze uguali (es. 100k+100k) il rapporto e' 2.0. Da ricalibrare
# sul cablaggio reale.
DIVIDER_RATIO = 2.0

# Tensione LiPo 1S: 3.0V (scarica) - 4.2V (carica), curva di scarica non
# lineare. Per semplicita' usiamo un'interpolazione lineare: e' una
# stima indicativa, non una misura di precisione (non serve fuel-gauge
# per generare un alert di soglia bassa).
VBAT_EMPTY = 3.0
VBAT_FULL = 4.2

# Numero di letture su cui mediare, per attenuare il rumore tipico di un
# ADC a 12 bit non isolato (lo stesso problema gia' osservato e
# documentato per i sensori PPG/ECG).
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
        """Restituisce la percentuale stimata di batteria (0-100) oppure
        None se il monitoraggio e' disabilitato o l'hardware non e'
        disponibile (in tal caso l'AlertManager non generera' alert)."""
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
