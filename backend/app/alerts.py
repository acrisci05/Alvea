# alerts.py - Valutazione delle soglie cliniche su una lettura.
#
# Regola d'oro (dalla documentazione): se la fascia e' staccata
# (sensor_contact == False) NON si emettono allarmi fisiologici (i valori sono
# 0 e sarebbero falsi positivi). Si emette invece un allarme TECNICO.
from . import config


def evaluate(reading: dict):
    """Restituisce una lista di alert (dict) per una singola lettura.

    reading: {"bpm","temperature","sensor_contact",...}
    alert:   {"kind","severity","message","value"}
    """
    alerts = []
    contact = reading.get("sensor_contact", True)

    if not contact:
        # Allarme tecnico: la valutazione fisiologica viene saltata.
        alerts.append({
            "kind": "contact_lost",
            "severity": "technical",
            "message": "Fascia non a contatto: rilevazione sospesa.",
            "value": None,
        })
        return alerts

    bpm = reading.get("bpm", 0) or 0
    temp = reading.get("temperature", 0) or 0

    # --- BPM --- (0 = lettura non ancora valida: niente allarme)
    if bpm <= 0:
        pass
    elif bpm <= config.BPM_CRIT_LOW:
        alerts.append(_a("bpm_low", "critical", f"Bradicardia critica: {bpm} BPM", bpm))
    elif bpm >= config.BPM_CRIT_HIGH:
        alerts.append(_a("bpm_high", "critical", f"Tachicardia critica: {bpm} BPM", bpm))
    elif bpm < config.BPM_WARN_LOW:
        alerts.append(_a("bpm_low", "warning", f"BPM sotto soglia: {bpm}", bpm))
    elif bpm > config.BPM_WARN_HIGH:
        alerts.append(_a("bpm_high", "warning", f"BPM sopra soglia: {bpm}", bpm))

    # --- Temperatura --- (0 = lettura non ancora valida: niente allarme)
    if temp <= 0:
        pass
    elif temp <= config.TEMP_CRIT_LOW:
        alerts.append(_a("temp_low", "critical", f"Ipotermia critica: {temp} C", temp))
    elif temp >= config.TEMP_CRIT_HIGH:
        alerts.append(_a("temp_high", "critical", f"Febbre alta: {temp} C", temp))
    elif temp < config.TEMP_WARN_LOW:
        alerts.append(_a("temp_low", "warning", f"Temperatura bassa: {temp} C", temp))
    elif temp > config.TEMP_WARN_HIGH:
        alerts.append(_a("temp_high", "warning", f"Temperatura alta: {temp} C", temp))

    return alerts


def _a(kind, severity, message, value):
    return {"kind": kind, "severity": severity, "message": message, "value": value}
