# sensor_sim.py - Sorgente dati SIMULATA (HIL Testing per produzione).
# Ottimizzato: zero allocazioni dinamiche nel loop principale.

import time
import random
import config

class SimSensor:
    def __init__(self):
        self._contact = True
        
        # PRODUZIONE: Pre-allocazione della struttura dati
        # FIX (Code Review): "device_status" e "patient_id" venivano
        # aggiunti al dizionario solo a runtime nei vari main_*.py. In
        # Python questo non causa un errore (i dict sono dinamici), ma
        # contraddice la filosofia "zero allocazioni/struttura fissa"
        # dichiarata in questo stesso file, e lascia il payload privo di
        # quei campi se letto prima del primo invio. Pre-allocati qui.
        self._payload = {
            "device_id": config.DEVICE_ID,
            "patient_id": None,
            "timestamp": 0,
            "bpm": 0.0,
            "skin_temperature": 0.0,
            "spo2": 0.0,
            "respiration_rate": 0.0,
            "sensor_contact": True,
            "device_status": "INIT",
            "source": "sim_test_rig"
        }

    def read(self):
        """Aggiorna i valori del dizionario pre-esistente senza riallocare memoria."""
        self._contact = random.random() > config.CONTACT_DROP_PROB

        self._payload["timestamp"] = time.time()
        self._payload["sensor_contact"] = self._contact

        if self._contact:
            self._payload["bpm"] = round(random.uniform(config.BPM_SIM_MIN, config.BPM_SIM_MAX), 1)
            self._payload["skin_temperature"] = round(random.uniform(config.TEMP_SKIN_SIM_MIN, config.TEMP_SKIN_SIM_MAX), 1)
            self._payload["spo2"] = round(random.uniform(config.SPO2_SIM_MIN, config.SPO2_SIM_MAX), 1)
            self._payload["respiration_rate"] = round(random.uniform(config.RESP_RATE_SIM_MIN, config.RESP_RATE_SIM_MAX), 1)
        else:
            self._payload["bpm"] = 0.0
            self._payload["skin_temperature"] = 0.0
            self._payload["spo2"] = 0.0
            self._payload["respiration_rate"] = 0.0
            print("[SIM WARNING] Caduta di contatto simulata!")

        # Restituisce un riferimento al dizionario in memoria
        return self._payload