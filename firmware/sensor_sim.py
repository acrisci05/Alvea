# sensor_sim.py - Sorgente dati SIMULATA per PulseGuard-Baby.
#
# Genera una lettura fisiologica plausibile attorno allo stato nominale,
# replicando la logica del main.py originale del progetto. Espone la stessa
# interfaccia di sensor_real.py (metodo .read() -> dict) cosi' che il resto
# del firmware non sappia, ne' debba sapere, quale sorgente e' attiva.
import time
import random

import config


class SimSensor:
    """Sensore simulato. .read() restituisce un dizionario con lo schema
    canonico della telemetria PulseGuard-Baby."""

    def __init__(self):
        self._contact = True

    def read(self):
        # Aderenza fascia: 95% a contatto, 5% si stacca (allarme tecnico)
        self._contact = random.random() > config.CONTACT_DROP_PROB

        if self._contact:
            bpm = round(random.uniform(config.BPM_SIM_MIN, config.BPM_SIM_MAX), 1)
            temperature = round(random.uniform(config.TEMP_SIM_MIN, config.TEMP_SIM_MAX), 1)
        else:
            # Fascia staccata: i valori crollano. Node-RED/Backend distinguono
            # questo "falso allarme" guardando sensor_contact, non i valori.
            bpm = 0.0
            temperature = 0.0
            print("[WARNING] Fascia non a contatto! Avviso tecnico.")

        return {
            "device_id": config.DEVICE_ID,
            "timestamp": time.time(),
            "bpm": bpm,
            "temperature": temperature,
            "sensor_contact": self._contact,
            "source": "sim",
        }
