# resp_edr.py - Frequenza Respiratoria via EDR (ECG-Derived Respiration).
#
# Principio fisiologico: il respiro modula leggermente la frequenza
# cardiaca (Aritmia Sinusale Respiratoria: il cuore accelera in
# inspirazione e decelera in espirazione). Filtrando la serie degli
# intervalli RR dell'ECG con un passa-basso e contando gli attraversamenti
# della propria media mobile si stima il numero di atti respiratori al
# minuto (filtro IIR + zero-crossing), senza richiedere alcun sensore
# ottico dedicato.

MIN_RR_FOR_EDR = 10    # numero minimo di RR per tentare la stima del respiro

EDR_FILTER_ALPHA = 0.2   # costante del filtro IIR passa-basso sulla serie RR
PHYSIO_RESP_MIN = 8.0    # limiti fisiologici plausibili (atti/min) per scartare stime spurie
# Il limite superiore e' volutamente piu' alto della soglia di alert
# clinico (DEFAULT_ALARM_RESP_MAX = 40): una tachipnea
# severa in eta' pediatrica (crisi d'asma avanzata) puo' superare
# abbondantemente i 40 atti/min, e l'algoritmo non deve scartare come
# "non plausibile" proprio la stima piu' critica da rilevare.
PHYSIO_RESP_MAX = 60.0

def compute_edr_resp_rate(rr_list):
    """Stima la Frequenza Respiratoria (atti/min) dalla modulazione della
    serie degli intervalli RR (EDR - ECG-Derived Respiration).
    """
    n = len(rr_list)
    if n < MIN_RR_FOR_EDR:
        return 0.0

    # Durata reale della finestra (somma degli RR, da ms a secondi): necessaria per convertire i "cicli per campione RR" in atti/min
    window_s = sum(rr_list) / 1000.0
    if window_s <= 0:
        return 0.0

    y_prev = rr_list[0]
    filtered = [0.0] * n
    s = 0.0
    for i in range(n):
        y = EDR_FILTER_ALPHA * rr_list[i] + (1.0 - EDR_FILTER_ALPHA) * y_prev
        filtered[i] = y
        y_prev = y
        s += y

    mean_filtered = s / n

    crossings = 0
    for i in range(1, n):
        if filtered[i - 1] < mean_filtered and filtered[i] >= mean_filtered:
            crossings += 1

    resp_rate = crossings * (60.0 / window_s)

    if not (PHYSIO_RESP_MIN <= resp_rate <= PHYSIO_RESP_MAX):
        return 0.0
    return round(resp_rate, 1)