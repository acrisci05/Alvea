# alerts.py - Valutazione delle soglie cliniche su una singola lettura.
#
# Regola fondamentale (dalla relazione tecnica, Sezione 5.4 — algoritmo anti-panico):
#   Se sensor_contact == False il firmware ha già azzerato i valori fisiologici.
#   Il backend NON deve valutare le soglie cliniche su quei valori (sarebbero
#   falsi positivi). Emette invece un unico allarme TECNICO "fascia staccata".
#
# Parametri valutati (dalla relazione, Sezione 5.2):
#   - Frequenza respiratoria  → soglie RESP_* in config.py
#   - SpO2                    → soglie SPO2_* in config.py
#   - Frequenza cardiaca BPM  → soglie BPM_*  in config.py
#   - Temperatura cutanea     → soglie TEMP_* in config.py
from . import config


def evaluate(reading: dict) -> list[dict]:
    """Valuta le soglie su una lettura e restituisce la lista di alert generati.

    Parametri
    ----------
    reading : dict
        Dizionario con i campi del payload firmware (es. bpm, spo2, ecc.).

    Ritorna
    -------
    list[dict]
        Lista di alert, ognuno con le chiavi: kind, severity, message, value.
        Lista vuota se tutti i parametri sono nei range di normalità.
    """
    alerts = []
    contact = reading.get("sensor_contact", True)

    # --- Controllo contatto fascia (anti-panico) ----------------------------
    # Se la fascia è staccata i valori fisiologici sono 0 (firmware azzera tutto).
    # Emetti solo l'allarme tecnico e interrompi la valutazione clinica.
    if not contact:
        alerts.append(_a(
            kind="contact_lost",
            severity="technical",
            message="Fascia non a contatto: rilevazione sospesa.",
            value=None,
        ))
        return alerts

    # --- Frequenza respiratoria (parametro chiave per asma) -----------------
    resp = reading.get("respiration_rate", 0) or 0
    if resp > 0:  # 0 = lettura non ancora valida, nessun allarme
        if resp <= config.RESP_CRIT_LOW:
            alerts.append(_a("resp_low", "critical",
                             f"Apnea/bradipnea critica: {resp} atti/min", resp))
        elif resp >= config.RESP_CRIT_HIGH:
            alerts.append(_a("resp_high", "critical",
                             f"Tachipnea critica: {resp} atti/min", resp))
        elif resp < config.RESP_WARN_LOW:
            alerts.append(_a("resp_low", "warning",
                             f"Frequenza respiratoria bassa: {resp} atti/min", resp))
        elif resp > config.RESP_WARN_HIGH:
            alerts.append(_a("resp_high", "warning",
                             f"Frequenza respiratoria alta: {resp} atti/min", resp))

    # --- SpO2 — saturazione ossigeno ----------------------------------------
    # Valori sotto 92% sono critici per un bambino asmatico (relazione Sez. 5.2).
    spo2 = reading.get("spo2", 0) or 0
    if spo2 > 0:
        if spo2 < config.SPO2_CRIT_LOW:
            alerts.append(_a("spo2_low", "critical",
                             f"Desaturazione critica: SpO2 {spo2}%", spo2))
        elif spo2 < config.SPO2_WARN_LOW:
            alerts.append(_a("spo2_low", "warning",
                             f"SpO2 sotto soglia: {spo2}%", spo2))

    # --- Frequenza cardiaca (BPM) -------------------------------------------
    bpm = reading.get("bpm", 0) or 0
    if bpm > 0:
        if bpm <= config.BPM_CRIT_LOW:
            alerts.append(_a("bpm_low", "critical",
                             f"Bradicardia critica: {bpm} BPM", bpm))
        elif bpm >= config.BPM_CRIT_HIGH:
            alerts.append(_a("bpm_high", "critical",
                             f"Tachicardia critica: {bpm} BPM", bpm))
        elif bpm < config.BPM_WARN_LOW:
            alerts.append(_a("bpm_low", "warning",
                             f"BPM sotto soglia: {bpm}", bpm))
        elif bpm > config.BPM_WARN_HIGH:
            alerts.append(_a("bpm_high", "warning",
                             f"BPM sopra soglia: {bpm}", bpm))

    # --- Temperatura cutanea ------------------------------------------------
    temp = reading.get("skin_temperature", 0) or 0
    if temp > 0:
        if temp <= config.TEMP_CRIT_LOW:
            alerts.append(_a("temp_low", "critical",
                             f"Ipotermia critica: {temp} °C", temp))
        elif temp >= config.TEMP_CRIT_HIGH:
            alerts.append(_a("temp_high", "critical",
                             f"Febbre alta: {temp} °C", temp))
        elif temp < config.TEMP_WARN_LOW:
            alerts.append(_a("temp_low", "warning",
                             f"Temperatura bassa: {temp} °C", temp))
        elif temp > config.TEMP_WARN_HIGH:
            alerts.append(_a("temp_high", "warning",
                             f"Temperatura alta: {temp} °C", temp))

    return alerts


def _a(kind: str, severity: str, message: str, value) -> dict:
    """Helper interno: costruisce un dizionario alert."""
    return {"kind": kind, "severity": severity, "message": message, "value": value}