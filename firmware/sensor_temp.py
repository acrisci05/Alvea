# sensor_temp.py - Lettura temperatura corporea.
#
# Il percorso ECG reale (AD8232) fornisce il BPM ma non la temperatura: serve
# un sensore dedicato. Qui supportiamo due opzioni comuni; scegli con TEMP_MODE.
#
#   - "ds18b20": sensore digitale 1-Wire (consigliato, preciso, semplice).
#   - "ntc":     termistore analogico su ADC (economico, richiede taratura).
#
# Finche' non monti l'hardware, lascia TEMP_MODE = "stub": restituisce un valore
# nominale costante cosi' il resto del sistema gira lo stesso.
import time

TEMP_MODE = "stub"     # "stub" | "ds18b20" | "ntc"

# Pin di esempio (cambia secondo il tuo cablaggio)
PIN_DS18B20 = 4
PIN_NTC     = 35       # ADC1, input-only


class TempSensor:
    def __init__(self):
        self.mode = TEMP_MODE
        if self.mode == "ds18b20":
            import onewire, ds18x20
            from machine import Pin
            self._bus = ds18x20.DS18X20(onewire.OneWire(Pin(PIN_DS18B20)))
            self._roms = self._bus.scan()
        elif self.mode == "ntc":
            import machine
            self._adc = machine.ADC(machine.Pin(PIN_NTC))
            self._adc.atten(machine.ADC.ATTN_11DB)
            self._adc.width(machine.ADC.WIDTH_12BIT)

    def read(self):
        if self.mode == "ds18b20":
            if not self._roms:
                return 0.0
            self._bus.convert_temp()
            time.sleep_ms(750)                 # tempo di conversione DS18B20
            return round(self._bus.read_temp(self._roms[0]), 1)

        if self.mode == "ntc":
            # Taratura indicativa: da adattare al tuo termistore (Beta, R25...).
            raw = self._adc.read()
            # Placeholder lineare: NON usare in produzione senza taratura reale.
            return round(35.0 + (raw / 4095.0) * 4.0, 1)

        # stub: temperatura nominale costante
        return 36.5
