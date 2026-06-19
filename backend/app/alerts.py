# alerts.py - Valutazione delle soglie cliniche su una lettura.
#
# Regola d'oro (dalla documentazione): se la fascia e' staccata
# (sensor_contact == False) NON si emettono allarmi fisiologici (i valori sono
# 0 e sarebbero falsi positivi). Si emette invece un allarme TECNICO.
from . import config


def evaluate(reading: dict, thresholds: dict | None = None):
    """Restituisce una lista di alert (dict) per una singola lettura.

    reading:    {"bpm","temperature","sensor_contact",...}
    thresholds: dizionario con le 8 chiavi delle soglie (vedi
                config.DEFAULT_THRESHOLDS). Se None usa le soglie di default;
                il medico puo' configurare soglie per-device (DeviceThreshold).
    alert:      {"parameter","kind","severity","message","value"}
    """
    th = thresholds or config.DEFAULT_THRESHOLDS
    alerts = []
    contact = reading.get("sensor_contact", True)

    if not contact:
        # Allarme tecnico: la valutazione fisiologica viene saltata.
        alerts.append({
            "parameter": "contact",
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
    elif bpm <= th["bpm_crit_low"]:
        alerts.append(_a("bpm", "bpm_low", "critical", f"Bradicardia critica: {bpm} BPM", bpm))
    elif bpm >= th["bpm_crit_high"]:
        alerts.append(_a("bpm", "bpm_high", "critical", f"Tachicardia critica: {bpm} BPM", bpm))
    elif bpm < th["bpm_warn_low"]:
        alerts.append(_a("bpm", "bpm_low", "warning", f"BPM sotto soglia: {bpm}", bpm))
    elif bpm > th["bpm_warn_high"]:
        alerts.append(_a("bpm", "bpm_high", "warning", f"BPM sopra soglia: {bpm}", bpm))

    # --- Temperatura --- (0 = lettura non ancora valida: niente allarme)
    if temp <= 0:
        pass
    elif temp <= th["temp_crit_low"]:
        alerts.append(_a("temperature", "temp_low", "critical", f"Ipotermia critica: {temp} C", temp))
    elif temp >= th["temp_crit_high"]:
        alerts.append(_a("temperature", "temp_high", "critical", f"Febbre alta: {temp} C", temp))
    elif temp < th["temp_warn_low"]:
        alerts.append(_a("temperature", "temp_low", "warning", f"Temperatura bassa: {temp} C", temp))
    elif temp > th["temp_warn_high"]:
        alerts.append(_a("temperature", "temp_high", "warning", f"Temperatura alta: {temp} C", temp))

    return alerts


def _a(parameter, kind, severity, message, value):
    return {"parameter": parameter, "kind": kind, "severity": severity,
            "message": message, "value": value}
