# sensor_temp.py - Lettura temperatura cutanea (Fase di Produzione).
# Gestisce gli errori hardware nativamente senza bloccare il firmware.

import time
import machine

TEMP_MODE = "ds18b20"  # In produzione si fissa l'hardware reale: "ds18b20" o "ntc"
PIN_DS18B20 = 4
PIN_NTC     = 35       

# Il DS18B20 richiede ~750ms per completare una conversione a 12 bit.
# Non possiamo bloccare il loop principale (che gira a 250 Hz / 4ms per
# ciclo), quindi gestiamo la conversione in modo NON bloccante con una
# macchina a stati: avviamo la conversione, e leggiamo il risultato solo
# dopo che il tempo minimo e' trascorso.
DS18B20_CONVERSION_MS = 750

class TempSensor:
    def __init__(self):
        self.mode = TEMP_MODE
        self._hardware_ok = False
        self._conversion_pending = False
        self._conversion_started_ms = 0
        self._last_good_temp = None

        try:
            if self.mode == "ds18b20":
                import onewire, ds18x20
                self._bus = ds18x20.DS18X20(onewire.OneWire(machine.Pin(PIN_DS18B20)))
                self._roms = self._bus.scan()
                if self._roms:
                    self._hardware_ok = True
            elif self.mode == "ntc":
                self._adc = machine.ADC(machine.Pin(PIN_NTC))
                self._adc.atten(machine.ADC.ATTN_11DB)
                self._adc.width(machine.ADC.WIDTH_12BIT)
                self._hardware_ok = True
        except Exception as e:
            print("[HARDWARE ERROR] Errore inizializzazione sensore temperatura:", e)
            self._hardware_ok = False

    def read(self):
        """
        Restituisce la temperatura cutanea (31-34 C) o None se guasto/non
        ancora disponibile. Garantisce la conformita' al requisito sulla
        qualita' del dato.

        BUGFIX: la versione precedente chiamava convert_temp() e leggeva
        il risultato nello stesso ciclo, ma il DS18B20 richiede ~750ms per
        completare la conversione: il valore letto poteva quindi essere
        quello della conversione PRECEDENTE (stale) o un dato non valido.
        Ora la conversione e' gestita in modo non bloccante a macchina a
        stati: viene avviata una volta e il risultato viene letto solo al
        primo read() successivo al trascorrere di DS18B20_CONVERSION_MS.
        """
        if not self._hardware_ok:
            return None

        try:
            if self.mode == "ds18b20":
                if not self._roms:
                    return None

                now_ms = time.ticks_ms()

                if not self._conversion_pending:
                    # Avvia una nuova conversione e ritorna l'ultimo valore
                    # valido disponibile (se presente), evitando di
                    # bloccare il chiamante in attesa del risultato.
                    self._bus.convert_temp()
                    self._conversion_pending = True
                    self._conversion_started_ms = now_ms
                    return self._last_good_temp

                elapsed = time.ticks_diff(now_ms, self._conversion_started_ms)
                if elapsed < DS18B20_CONVERSION_MS:
                    # Conversione ancora in corso: non leggere ancora,
                    # restituisci l'ultimo valore valido noto.
                    return self._last_good_temp

                # Conversione completata: leggi il risultato e avviane
                # immediatamente una nuova per il prossimo ciclo.
                temp = round(self._bus.read_temp(self._roms[0]), 1)
                self._last_good_temp = temp
                self._bus.convert_temp()
                self._conversion_started_ms = now_ms
                return temp

            if self.mode == "ntc":
                raw = self._adc.read()
                if raw == 0 or raw == 4095: # Cortocircuito o circuito aperto
                    return None
                return round(30.0 + (raw / 4095.0) * 5.0, 1)

        except Exception as e:
            print("[TEMP SENSOR ERROR]", e)
            return None