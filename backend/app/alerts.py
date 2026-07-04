# alerts.py - Valutazione delle soglie cliniche su una singola lettura.
#
#   Se sensor_contact == False il firmware ha già azzerato i valori fisiologici.
#   Il backend NON deve valutare le soglie cliniche su quei valori (sarebbero
#   falsi positivi). Emette invece un unico allarme TECNICO "fascia staccata".
#
# Parametri valutati:
#   - Frequenza respiratoria  → soglie resp_* (da EDR)
#   - Frequenza cardiaca BPM  → soglie bpm_*
#   - Temperatura cutanea     → soglie temp_*
#
# Le soglie arrivano come dizionario (chiavi di config.DEFAULT_THRESHOLDS): di
# default sono quelle globali, ma il medico può configurarne di dedicate per
# device (DeviceThreshold).
from . import config


def evaluate(reading: dict, thresholds: dict | None = None) -> list[dict]:
    """Valuta le soglie su una lettura e restituisce la lista di alert generati.

    Parametri
    ----------
    reading : dict
        Dizionario con i campi del payload firmware (es. bpm, respiration_rate).
    thresholds : dict | None
        Soglie cliniche da applicare. Se None, usa config.DEFAULT_THRESHOLDS.

    Ritorna
    -------
    list[dict]
        Lista di alert, ognuno con le chiavi: parameter, kind, severity,
        message, value. Lista vuota se tutti i parametri sono nella norma.
    """
    th = thresholds or config.DEFAULT_THRESHOLDS
    alerts = []
    contact = reading.get("sensor_contact", True)

    # --- Controllo contatto fascia (antipanico) ----------------------------
    # Se la fascia è staccata i valori fisiologici sono 0 (azzerati dal firmware).
    # Viene emesso solo l'allarme tecnico e interrotta la valutazione clinica.
    if not contact:
        alerts.append(_a(
            parameter="contact",
            kind="contact_lost",
            severity="technical",
            message="Fascia non a contatto: rilevazione sospesa.",
            value=None,
        ))
        return alerts

    # --- Frequenza respiratoria (derivante dalla tecnica EDR) ---
    resp = reading.get("respiration_rate", 0) or 0
    if resp > 0:  # 0 = lettura non ancora valida, nessun allarme
        if resp <= th["resp_crit_low"]:
            alerts.append(_a("respiration_rate", "resp_low", "critical",
                             f"Apnea/bradipnea critica: {resp} atti/min", resp))
        elif resp >= th["resp_crit_high"]:
            alerts.append(_a("respiration_rate", "resp_high", "critical",
                             f"Tachipnea critica: {resp} atti/min", resp))
        elif resp < th["resp_warn_low"]:
            alerts.append(_a("respiration_rate", "resp_low", "warning",
                             f"Frequenza respiratoria bassa: {resp} atti/min", resp))
        elif resp > th["resp_warn_high"]:
            alerts.append(_a("respiration_rate", "resp_high", "warning",
                             f"Frequenza respiratoria alta: {resp} atti/min", resp))

    # --- Frequenza cardiaca (BPM) ---
    bpm = reading.get("bpm", 0) or 0
    if bpm > 0:
        if bpm <= th["bpm_crit_low"]:
            alerts.append(_a("bpm", "bpm_low", "critical",
                             f"Bradicardia critica: {bpm} BPM", bpm))
        elif bpm >= th["bpm_crit_high"]:
            alerts.append(_a("bpm", "bpm_high", "critical",
                             f"Tachicardia critica: {bpm} BPM", bpm))
        elif bpm < th["bpm_warn_low"]:
            alerts.append(_a("bpm", "bpm_low", "warning",
                             f"BPM sotto soglia: {bpm}", bpm))
        elif bpm > th["bpm_warn_high"]:
            alerts.append(_a("bpm", "bpm_high", "warning",
                             f"BPM sopra soglia: {bpm}", bpm))

    # --- Temperatura cutanea ---
    temp = reading.get("skin_temperature", 0) or 0
    if temp > 0:
        if temp <= th["temp_crit_low"]:
            alerts.append(_a("skin_temperature", "temp_low", "critical",
                             f"Ipotermia critica: {temp} °C", temp))
        elif temp >= th["temp_crit_high"]:
            alerts.append(_a("skin_temperature", "temp_high", "critical",
                             f"Febbre alta: {temp} °C", temp))
        elif temp < th["temp_warn_low"]:
            alerts.append(_a("skin_temperature", "temp_low", "warning",
                             f"Temperatura bassa: {temp} °C", temp))
        elif temp > th["temp_warn_high"]:
            alerts.append(_a("skin_temperature", "temp_high", "warning",
                             f"Temperatura alta: {temp} °C", temp))

    return alerts


def _a(parameter: str, kind: str, severity: str, message: str, value) -> dict:
    """Helper interno: costruisce un dizionario alert."""
    return {"parameter": parameter, "kind": kind, "severity": severity,
            "message": message, "value": value}
