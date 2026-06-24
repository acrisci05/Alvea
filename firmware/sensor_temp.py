# sensor_temp.py - Temperatura cutanea da termistore NTC di precisione.
#
# Il sensore è un NTC (Negative Temperature Coefficient) letto su un ingresso
# ADC tramite partitore di tensione. La conversione resistenza->temperatura usa
# l'equazione di Steinhart-Hart semplificata (Beta). Gestisce nativamente i
# guasti (cortocircuito / circuito aperto) restituendo None senza bloccare il
# firmware, per garantire la qualità del dato (device_status).

import math
import machine

# --- Cablaggio e partitore ---
PIN_NTC    = 35          # ingresso analogico (ADC1) dedicato all'NTC
R_SERIES   = 10_000.0    # resistenza fissa del partitore (ohm)
ADC_MAX    = 4095.0      # fondo scala ADC a 12 bit

# --- Parametri del termistore (NTC 10k tipico) ---
R0   = 10_000.0          # resistenza nominale a T0 (ohm)
T0_K = 298.15            # 25 °C in kelvin
BETA = 3950.0            # coefficiente Beta (dal datasheet del componente)


class TempSensor:
    """Lettura della temperatura cutanea da termistore NTC di precisione."""

    def __init__(self):
        self._hardware_ok = False
        try:
            self._adc = machine.ADC(machine.Pin(PIN_NTC))
            self._adc.atten(machine.ADC.ATTN_11DB)     # fondo scala ~3.3 V
            self._adc.width(machine.ADC.WIDTH_12BIT)
            self._hardware_ok = True
        except Exception as e:
            print("[HARDWARE ERROR] Inizializzazione NTC fallita:", e)
            self._hardware_ok = False

    def read(self):
        """Restituisce la temperatura cutanea in °C (1 decimale) o None se guasto."""
        if not self._hardware_ok:
            return None
        try:
            raw = self._adc.read()
            # Cortocircuito (0) o circuito aperto (fondo scala): dato non valido.
            if raw <= 0 or raw >= ADC_MAX:
                return None

            # Partitore: 3V3 -- R_SERIES -- [ADC] -- NTC -- GND
            # raw/ADC_MAX = R_ntc / (R_SERIES + R_ntc)  ->  R_ntc = R_SERIES * raw/(ADC_MAX-raw)
            r_ntc = R_SERIES * (raw / (ADC_MAX - raw))

            # Equazione Beta: 1/T = 1/T0 + (1/BETA) * ln(R/R0)
            inv_t = (1.0 / T0_K) + (1.0 / BETA) * math.log(r_ntc / R0)
            temp_c = (1.0 / inv_t) - 273.15
            return round(temp_c, 1)
        except Exception:
            return None
