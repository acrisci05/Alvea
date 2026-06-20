# alerts.py - Valutazione delle soglie cliniche su una lettura.
#
# Regola d'oro (dalla documentazione): se la fascia e' staccata
# (sensor_contact == False) NON si emettono allarmi fisiologici (i valori sono
# 0 e sarebbero falsi positivi). Si emette invece un allarme TECNICO.

# Importa il modulo config dove sono definite tutte le soglie numeriche
# (es. BPM_CRIT_LOW = 60). Usando config evitiamo numeri "magici" sparsi nel codice.
from . import config


def evaluate(reading: dict):
    """Restituisce una lista di alert (dict) per una singola lettura.

    reading: {"bpm","temperature","sensor_contact",...}
    alert:   {"kind","severity","message","value"}
    """

    # Lista vuota che verrà riempita con gli alert trovati.
    # Se alla fine è ancora vuota, significa che tutto è nella norma.
    alerts = []

    # Legge il flag di contatto dalla lettura.
    # Se la chiave non esiste, assume True (fascia a contatto) per sicurezza.
    contact = reading.get("sensor_contact", True)

    # === CONTROLLO CONTATTO FASCIA ===
    # Se la fascia è staccata dalla pelle, i valori di BPM/resp/temp
    # sarebbero 0 o casuali — valutarli genererebbe falsi allarmi.
    # Quindi emettiamo solo un allarme TECNICO e usciamo subito dalla funzione.
    if not contact:
        alerts.append({
            "kind": "contact_lost",        # tipo di allarme: fascia staccata
            "severity": "technical",       # gravità: tecnica (non clinica)
            "message": "Fascia non a contatto: rilevazione sospesa.",
            "value": None,                 # nessun valore numerico associato
        })
        return alerts  # esci subito: non valutare i parametri fisiologici

    # === ESTRAZIONE VALORI ===
    # Legge i tre parametri dalla lettura.
    # "or 0" gestisce il caso in cui il valore sia None invece di un numero:
    # None or 0 → 0, così i confronti numerici sotto non vanno in errore.
    bpm  = reading.get("bpm", 0) or 0           # battito cardiaco (BPM)
    temp = reading.get("temperature", 0) or 0   # temperatura cutanea (°C)
    resp = reading.get("resp_rate", 0) or 0     # frequenza respiratoria (atti/min)

    # === VALUTAZIONE FREQUENZA RESPIRATORIA ===
    # Controlla solo se resp > 0: un valore zero significa che il sensore
    # non ha ancora prodotto una stima valida, quindi si ignora.
    if resp > 0:
        if resp <= config.RESP_CRIT_LOW:
            # Bradipnea critica: respira troppo lentamente (sotto 10 atti/min)
            alerts.append(_a("resp_low", "critical", f"Bradipnea critica: {resp} atti/min", resp))
        elif resp >= config.RESP_CRIT_HIGH:
            # Tachipnea critica: respira troppo velocemente (sopra 40 atti/min)
            alerts.append(_a("resp_high", "critical", f"Tachipnea critica: {resp} atti/min", resp))
        elif resp < config.RESP_WARN_LOW:
            # Respirazione bassa ma non ancora critica (sotto 14 atti/min)
            alerts.append(_a("resp_low", "warning", f"Frequenza respiratoria bassa: {resp} atti/min", resp))
        elif resp > config.RESP_WARN_HIGH:
            # Respirazione alta ma non ancora critica (sopra 30 atti/min)
            alerts.append(_a("resp_high", "warning", f"Frequenza respiratoria alta: {resp} atti/min", resp))

    # === VALUTAZIONE BATTITO CARDIACO ===
    if bpm <= 0:
        # Valore non valido (0 o negativo): sensore non ancora pronto, si ignora
        pass
    elif bpm <= config.BPM_CRIT_LOW:
        # Bradicardia critica: battito troppo basso (sotto o uguale a 60 BPM)
        alerts.append(_a("bpm_low", "critical", f"Bradicardia critica: {bpm} BPM", bpm))
    elif bpm >= config.BPM_CRIT_HIGH:
        # Tachicardia critica: battito troppo alto (uguale o sopra 150 BPM)
        alerts.append(_a("bpm_high", "critical", f"Tachicardia critica: {bpm} BPM", bpm))
    elif bpm < config.BPM_WARN_LOW:
        # Battito basso ma non ancora critico (sotto 70 BPM)
        alerts.append(_a("bpm_low", "warning", f"BPM sotto soglia: {bpm}", bpm))
    elif bpm > config.BPM_WARN_HIGH:
        # Battito alto ma non ancora critico (sopra 130 BPM)
        alerts.append(_a("bpm_high", "warning", f"BPM sopra soglia: {bpm}", bpm))

    # === VALUTAZIONE TEMPERATURA ===
    if temp <= 0:
        # Valore non valido: sensore non pronto o stub non configurato, si ignora
        pass
    elif temp <= config.TEMP_CRIT_LOW:
        # Ipotermia critica: temperatura troppo bassa (sotto o uguale a 35.0 °C)
        alerts.append(_a("temp_low", "critical", f"Ipotermia critica: {temp} C", temp))
    elif temp >= config.TEMP_CRIT_HIGH:
        # Febbre alta critica: temperatura troppo alta (uguale o sopra 38.5 °C)
        alerts.append(_a("temp_high", "critical", f"Febbre alta: {temp} C", temp))
    elif temp < config.TEMP_WARN_LOW:
        # Temperatura bassa ma non critica (sotto 36.0 °C)
        alerts.append(_a("temp_low", "warning", f"Temperatura bassa: {temp} C", temp))
    elif temp > config.TEMP_WARN_HIGH:
        # Temperatura alta ma non critica (sopra 37.2 °C)
        alerts.append(_a("temp_high", "warning", f"Temperatura alta: {temp} C", temp))

    # Restituisce la lista degli alert trovati.
    # Può essere vuota (tutto ok) o contenere uno o più alert.
    return alerts


def _a(kind, severity, message, value):
    # Funzione di utilità privata (il _ iniziale indica che è interna al modulo).
    # Costruisce il dizionario standard di un alert invece di riscriverlo ogni volta.
    # kind     → tipo di anomalia (es. "bpm_low", "temp_high")
    # severity → gravità ("warning", "critical", "technical")
    # message  → testo leggibile dall'utente
    # value    → valore numerico che ha scatenato l'alert
    return {"kind": kind, "severity": severity, "message": message, "value": value}