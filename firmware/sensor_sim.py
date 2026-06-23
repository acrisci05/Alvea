# sensor_sim.py - Sorgente dati SIMULATA (HIL Testing per produzione).

import time
import random
import config

class SimSensor:
    def __init__(self):
        self._contact = True
        self._payload = {
            "device_id": config.DEVICE_ID,
            "patient_id": None,
            "timestamp": 0,
            "bpm": 0.0,
            "skin_temperature": 0.0,
            "respiration_rate": 0.0,
            "battery_pct": config.BATTERY_SIM_START,
            "sensor_contact": True,
            "device_status": "INIT",
            "source": "sim_test_rig"
        }
        
        # Stato interno della scarica simulata (separato dal payload per
        # poter resettare facilmente la batteria senza toccare il dict
        # esposto al chiamante prima del primo read()).
        self._battery_pct = config.BATTERY_SIM_START

    def read(self):
        """Aggiorna i valori del dizionario pre-esistente senza riallocare memoria."""
        self._contact = random.random() > config.CONTACT_DROP_PROB

        self._payload["timestamp"] = time.time()
        self._payload["sensor_contact"] = self._contact

        # Scarica simulata della batteria (lineare, ciclica): permette di
        # dimostrare l'alert di batteria scarica senza attendere ore reali.
        # Quando si esaurisce, si "ricarica" istantaneamente (rollover),
        # cosi' la demo puo' girare indefinitamente.
        self._battery_pct -= config.BATTERY_SIM_DRAIN_PER_TICK
        if self._battery_pct < 0.0:
            self._battery_pct = config.BATTERY_SIM_START
        self._payload["battery_pct"] = round(self._battery_pct, 1)

        if self._contact:
            self._payload["bpm"] = round(random.uniform(config.BPM_SIM_MIN, config.BPM_SIM_MAX), 1)
            self._payload["skin_temperature"] = round(random.uniform(config.TEMP_SKIN_SIM_MIN, config.TEMP_SKIN_SIM_MAX), 1)
            self._payload["respiration_rate"] = round(random.uniform(config.RESP_RATE_SIM_MIN, config.RESP_RATE_SIM_MAX), 1)
        else:
            self._payload["bpm"] = 0.0
            self._payload["skin_temperature"] = 0.0
            self._payload["respiration_rate"] = 0.0
            print("[SIM WARNING] Caduta di contatto simulata!")

        # Restituisce un riferimento al dizionario in memoria
        return self._payload