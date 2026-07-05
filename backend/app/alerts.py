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
# Le soglie arrivano come dizionario: di default sono quelle dinamiche 
# basate sull'età di Fleming (config.FLEMING_THRESHOLDS), ma il medico può 
# configurarne di dedicate per device (DeviceThreshold).

from . import config

# --- FIX: stato di persistenza per il debounce del contatto (per device) ---
# evaluate() viene richiamata una volta per ogni lettura in arrivo
# (mqtt_ingest.py, ~1 Hz): senza un contatore persistente tra le chiamate,
# ogni singola lettura con sensor_contact=False genererebbe un nuovo alert
# tecnico "contact_lost" (un record ogni secondo per l'intera durata del
# distacco), invece del singolo alert alla transizione descritto in tesi
# (debounce di config.CONTACT_LOST_DEBOUNCE_S letture consecutive, § 2.5 e
# § 2.7.2) e già correttamente implementato nel flow Node-RED equivalente
# (nodo "Soglie + Line Protocol", contatore "lost" in context).
_contact_lost_streaks: dict[str, int] = {}


def evaluate(reading: dict, thresholds: dict | None = None) -> list[dict]:
    """Valuta le soglie su una lettura e restituisce la lista di alert generati.

    Parametri
    ----------
    reading : dict
        Dizionario con i campi del payload firmware (es. bpm, respiration_rate).
    thresholds : dict | None
        Soglie cliniche da applicare. Se None, usa il fallback di config.FLEMING_THRESHOLDS.

    Ritorna
    -------
    list[dict]
        Lista di alert, ognuno con le chiavi: parameter, kind, severity,
        message, value. Lista vuota se tutti i parametri sono nella norma.
    """
    # Usa le soglie passate (gia' filtrate per età nel CRUD) o il fallback generale
    th = thresholds or config.FLEMING_THRESHOLDS["fallback"]
    alerts = []
    contact = reading.get("sensor_contact", True)
    device_id = reading.get("device_id")

    # --- Controllo contatto fascia (antipanico) ----------------------------
    # Se la fascia è staccata i valori fisiologici sono 0 (azzerati dal firmware).
    # Viene emesso solo l'allarme tecnico e interrotta la valutazione clinica.
    if not contact:
        # FIX: incrementa il contatore di persistenza del device e genera
        # l'alert tecnico solo al raggiungimento esatto della soglia di
        # debounce (config.CONTACT_LOST_DEBOUNCE_S), cosi' come gia' fatto
        # dal flow Node-RED. Da quel punto in poi il contatore continua a
        # crescere ma non coincide piu' con la soglia, quindi l'alert non
        # viene ripetuto ad ogni lettura successiva finche' il contatto non
        # torna (vedi ramo sotto, che azzera il contatore).
        streak = _contact_lost_streaks.get(device_id, 0) + 1
        _contact_lost_streaks[device_id] = streak
        if streak == config.CONTACT_LOST_DEBOUNCE_S:
            alerts.append(_a(
                parameter="contact",
                kind="contact_lost",
                severity="technical",
                message="Fascia non a contatto: rilevazione sospesa.",
                value=None,
            ))
        return alerts

    # FIX: il contatto e' presente: azzera il contatore di persistenza del
    # distacco, cosi' che una futura perdita di contatto debba di nuovo
    # accumulare CONTACT_LOST_DEBOUNCE_S letture prima di generare un alert.
    _contact_lost_streaks[device_id] = 0

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
