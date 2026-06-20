# alerts.py - Generazione e invio di alert locali rilevati dal device.
#
# AGGIUNTA (Code Review): nessuno dei main_*.py pubblicava mai su
# TOPIC_ALERT (definito in config.py ma mai usato). Il Requisito 1
# ("eventuale stato del dispositivo o qualita' del dato") e il Requisito 7
# ("il sistema deve generare alert quando vengono rilevate condizioni
# critiche o anomale", con esempi espliciti "assenza di dati" e "batteria
# bassa del dispositivo") riguardano anche condizioni che SOLO il firmware
# puo' rilevare in modo affidabile (es. un sensore fisicamente guasto in
# modo persistente, batteria scarica). Il backend puo' rilevare soglie sui
# valori clinici (bpm/spo2/...), ma non puo' distinguere da solo "il
# device non manda piu' un certo parametro perche' il sensore e' guasto"
# da "il device e' offline": serve un canale dedicato lato firmware.
#
# Questo modulo NON duplica la logica di soglie cliniche (di competenza
# del backend, Membro 2/Requisito 7 "Gestione alert - Core"): qui si
# generano solo alert di tipo "device/hardware", con un formato dati
# compatibile con quanto richiesto al Punto 7 dei requisiti (paziente,
# parametro, descrizione, livello di gravita', timestamp).

import time
import config


class AlertManager:
    """Tiene traccia delle condizioni di guasto persistenti e pubblica un
    alert (una sola volta per transizione, non ad ogni ciclo) quando una
    condizione supera la soglia di persistenza configurata."""

    def __init__(self, transport, transport_kind="mqtt"):
        """
        transport: istanza di MQTTPublisher o BLEPeripheral, gia' inizializzata
        transport_kind: "mqtt" o "ble", per scegliere come inviare l'alert
        """
        self.transport = transport
        self.transport_kind = transport_kind
        self._fault_streaks = {}   # nome condizione -> contatore letture consecutive
        self._active_alerts = set()  # condizioni per cui l'alert e' gia' stato inviato

    def _build_alert(self, parametro, descrizione, gravita, patient_id=None):
        return {
            "device_id": config.DEVICE_ID,
            "patient_id": patient_id,
            "parametro": parametro,
            "descrizione": descrizione,
            "gravita": gravita,        # es. "WARNING", "CRITICAL"
            "timestamp": time.time(),
        }

    def _send(self, alert_dict):
        if self.transport_kind == "mqtt":
            if getattr(self.transport, "is_connected", False):
                try:
                    self.transport.client.publish(
                        config.TOPIC_ALERT,
                        __import__("json").dumps(alert_dict)
                    )
                    print("[ALERT MQTT TX]:", alert_dict)
                    return True
                except Exception as e:
                    print("[ALERT] Invio MQTT fallito:", e)
                    return False
            else:
                print("[ALERT LOCALE - rete assente]:", alert_dict)
                return False
        elif self.transport_kind == "ble":
            if self.transport.is_connected():
                # Riusa lo stesso canale NOTIFY della telemetria: l'app
                # mobile deve distinguere i due messaggi tramite il campo
                # "parametro"/"gravita'" assente nei record di telemetria.
                ok = self.transport.send_json(alert_dict)
                if ok:
                    print("[ALERT BLE TX]:", alert_dict)
                return ok
            else:
                print("[ALERT LOCALE - BLE non connesso]:", alert_dict)
                return False
        return False

    def check_fault(self, condition_name, is_faulty, parametro, descrizione, gravita="WARNING", patient_id=None):
        """Da chiamare ad ogni ciclo di telemetria con lo stato corrente
        (vero/falso) di una condizione di guasto. Pubblica un alert solo
        alla transizione "diventa persistente" e un altro alla
        risoluzione, evitando di floodare il broker."""
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
                self._send(self._build_alert(
                    parametro,
                    descrizione.replace("rilevato", "risolto") + " (RISOLTO)",
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
        )
