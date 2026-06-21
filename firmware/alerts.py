# alerts.py - Generazione e invio di alert locali rilevati dal device.
#
# Questo modulo ha il compito di generare alert di tipo "device/hardware", con un formato dati
# compatibile con quanto richiesto

import time
import json
import config


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
            "timestamp": time.time(),
        }

    def _send(self, alert_dict):
        if self.transport_kind == "mqtt":
            if getattr(self.transport, "is_connected", False):
                try:
                    self.transport.client.publish(
                        config.TOPIC_ALERT,
                        json.dumps(alert_dict)
                    )
                    print("[ALERT MQTT TX]:", alert_dict)
                    return True
                except Exception as e:
                    print("[ALERT] Invio MQTT fallito:", e)
                    self.transport.is_connected = False
                    return False
            else:
                print("[ALERT LOCALE - rete assente]:", alert_dict)
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
        """Da chiamare ad ogni ciclo di telemetria con lo stato corrente
        (vero/falso) di una condizione di guasto. Pubblica un alert solo
        alla transizione "diventa persistente" e un altro alla
        risoluzione, evitando di floodare il broker.
        """
        if is_faulty:
            self._fault_streaks[condition_name] = self._fault_streaks.get(condition_name, 0) + 1
            if (self._fault_streaks[condition_name] >= config.ALERT_FAULT_STREAK_THRESHOLD
                    and condition_name not in self._active_alerts):
                self._active_alerts.add(condition_name)
                self._send(self._build_alert(parametro, descrizione, gravita, patient_id))
        else:
            self._fault_streaks[condition_name] = 0
            if condition_name in self._active_alerts:
                self._active_alerts.discard(condition_name)
                testo_risolto = descrizione_risolto or (
                    descrizione.replace("rilevato", "risolto") + " (RISOLTO)"
                )
                self._send(self._build_alert(
                    parametro,
                    testo_risolto,
                    "INFO",
                    patient_id,
                ))

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