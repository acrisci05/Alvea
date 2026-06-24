# alerts.py - Valutazione delle soglie cliniche su una lettura (asma pediatrico).
#
# Regola d'oro: se il sensore è staccato (sensor_contact == False) o il
# dispositivo segnala un errore (device_status != SYSTEM_OK) NON si emettono
# allarmi fisiologici (i valori sono 0 e sarebbero falsi positivi): si emette
# invece un allarme TECNICO.
from . import config


def evaluate(reading: dict, thresholds: dict | None = None):
    """Restituisce una lista di alert (dict) per una singola lettura.

    reading:    {"respiration_rate","bpm","skin_temperature",
                 "sensor_contact","device_status",...}
    thresholds: dizionario con le chiavi delle soglie (vedi
                config.DEFAULT_THRESHOLDS). Se None usa le soglie di default;
                il medico può configurare soglie per-device (DeviceThreshold).
    alert:      {"parameter","kind","severity","message","value"}
    """
    th = thresholds or config.DEFAULT_THRESHOLDS
    alerts = []
    contact = reading.get("sensor_contact", True)
    status = reading.get("device_status", "SYSTEM_OK") or "SYSTEM_OK"

    if not contact or status != "SYSTEM_OK":
        # Allarme tecnico: la valutazione fisiologica viene saltata.
        alerts.append({
            "parameter": "contact",
            "kind": "contact_lost",
            "severity": "technical",
            "message": f"Sensore non a contatto o errore dispositivo ({status}).",
            "value": None,
        })
        return alerts

    resp = reading.get("respiration_rate", 0) or 0
    bpm = reading.get("bpm", 0) or 0
    skin = reading.get("skin_temperature", 0) or 0

    # --- Frequenza respiratoria / tachipnea --- (più alta è peggio)
    if resp > 0:
        if resp >= th["resp_crit_high"]:
            alerts.append(_a("respiration_rate", "resp_high", "critical", f"Tachipnea critica: {resp} atti/min", resp))
        elif resp > th["resp_warn_high"]:
            alerts.append(_a("respiration_rate", "resp_high", "warning", f"Frequenza respiratoria alta: {resp} atti/min", resp))

    # --- BPM --- (0 = lettura non valida)
    if bpm > 0:
        if bpm <= th["bpm_crit_low"]:
            alerts.append(_a("bpm", "bpm_low", "critical", f"Bradicardia critica: {bpm} BPM", bpm))
        elif bpm >= th["bpm_crit_high"]:
            alerts.append(_a("bpm", "bpm_high", "critical", f"Tachicardia critica: {bpm} BPM", bpm))
        elif bpm < th["bpm_warn_low"]:
            alerts.append(_a("bpm", "bpm_low", "warning", f"BPM sotto soglia: {bpm}", bpm))
        elif bpm > th["bpm_warn_high"]:
            alerts.append(_a("bpm", "bpm_high", "warning", f"BPM sopra soglia: {bpm}", bpm))

    # --- Temperatura cutanea / febbre --- (valori alti = peggio)
    if skin > 0:
        if skin >= th["skin_temp_crit_high"]:
            alerts.append(_a("skin_temperature", "temp_high", "critical", f"Temperatura cutanea molto alta: {skin} C", skin))
        elif skin > th["skin_temp_warn_high"]:
            alerts.append(_a("skin_temperature", "temp_high", "warning", f"Temperatura cutanea alta: {skin} C", skin))

    return alerts


def _a(parameter, kind, severity, message, value):
    return {"parameter": parameter, "kind": kind, "severity": severity,
            "message": message, "value": value}
