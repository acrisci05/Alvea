# alerts.py - Generazione e invio di alert locali rilevati dal device.
# Questo modulo ha il compito di generare alert sia di tipo "device/hardware" (guasti/assenza di contatto dei sensori, batteria scarica) sia l'alert
# clinico basato su soglia per la frequenza respiratoria (via EDR), con un formato dati compatibile con quanto richiesto

import time
import json
import config
from ntp_time import unix_now


class AlertManager:
    """Tiene traccia delle condizioni di guasto persistenti e pubblica un
    alert (una sola volta per transizione) quando una
    condizione supera la soglia di persistenza configurata."""

    def __init__(self, transport, transport_kind="mqtt"):
        self.transport = transport
        self.transport_kind = transport_kind
        self._fault_streaks = {}     # nome condizione -> contatore letture consecutive
        self._active_alerts = set()  # condizioni per cui l'alert e' gia' stato inviato

    def _build_alert(self, parametro, descrizione, gravita, patient_id=None):
        return {
            "device_id": config.DEVICE_ID,
            "patient_id": patient_id,
            "parametro": parametro,
            "descrizione": descrizione,
            "gravita": gravita,  
            "timestamp": unix_now(),
        }

    def _send(self, alert_dict):
        if self.transport_kind == "mqtt":
            # Riusa la logica di invio/gestione errori di MQTTPublisher
            # (publish_to) accedendo direttamente a transport.client.publish
            if self.transport.publish_to(config.TOPIC_ALERT, alert_dict):
                print("[ALERT MQTT TX]:", alert_dict)
                return True
            print("[ALERT LOCALE - rete assente o invio fallito]:", alert_dict)
            return False
        elif self.transport_kind == "ble":
            if self.transport.is_connected():
                ok = self.transport.send_json(alert_dict)
                if ok:
                    print("[ALERT BLE TX]:", alert_dict)
                return ok
            else:
                print("[ALERT LOCALE - BLE non connesso]:", alert_dict)
                return False
        return False

    def check_fault(self, condition_name, is_faulty, parametro, descrizione, gravita="WARNING",
                     patient_id=None, descrizione_risolto=None):
        """Da chiamare ad ogni ciclo di telemetria con lo stato corrente (vero/falso) di una condizione di guasto.
        Pubblica un alert solo
        alla transizione "diventa persistente" e un altro alla risoluzione.
        """
        if is_faulty:
            self._fault_streaks[condition_name] = self._fault_streaks.get(condition_name, 0) + 1
            if (self._fault_streaks[condition_name] >= config.ALERT_FAULT_STREAK_THRESHOLD
                    and condition_name not in self._active_alerts):
                # Segniamo la condizione come "attiva" solo se l'invio e' andato a buon fine
                if self._send(self._build_alert(parametro, descrizione, gravita, patient_id)):
                    self._active_alerts.add(condition_name)
        else:
            self._fault_streaks[condition_name] = 0
            if condition_name in self._active_alerts:
                testo_risolto = descrizione_risolto or (
                    descrizione.replace("rilevato", "risolto") + " (RISOLTO)"
                )
                # Rimozione della condizione da _active_alerts solo se è stata notificata la risoluzione
                if self._send(self._build_alert(
                    parametro,
                    testo_risolto,
                    "INFO",
                    patient_id,
                )):
                    self._active_alerts.discard(condition_name)

    def check_battery(self, battery_pct, patient_id=None):
        """Da chiamare se/quando e' disponibile una lettura di batteria."""
        if battery_pct is None:
            return
        is_low = battery_pct < config.DEFAULT_ALARM_BATTERY_MIN_PCT
        self.check_fault(
            "battery_low",
            is_low,
            "battery",
            f"Batteria scarica rilevata ({battery_pct:.0f}%)",
            gravita="WARNING",
            patient_id=patient_id,
            descrizione_risolto="Batteria non piu' sotto soglia critica (RISOLTO)",
        )

    def check_resp_rate(self, resp_rate, patient_id=None):
        """Alert clinico: tachipnea, frequenza respiratoria sopra la
        soglia configurata (Asma pediatrico). Da chiamare solo quando il
        contatto ECG e' presente"""
        if resp_rate is None or resp_rate <= 0.0:
            return
        is_high = resp_rate > config.DEFAULT_ALARM_RESP_MAX
        self.check_fault(
            "resp_rate_high",
            is_high,
            "respiration_rate",
            f"Tachipnea rilevata, frequenza respiratoria elevata ({resp_rate:.1f} atti/min)",
            gravita="CRITICAL",
            patient_id=patient_id,
            descrizione_risolto="Frequenza respiratoria rientrata nella soglia (RISOLTO)",
        )