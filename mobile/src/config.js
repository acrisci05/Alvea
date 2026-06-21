// src/config.js
//
// Configurazione centrale dell'app Alvea (caregiver + medico).
// Le soglie e le costanti qui definite sono SPECULARI a quelle realmente
// implementate nel firmware (firmware/config.py) e nel backend descritto
// nella Relazione Tecnica, Sez. 5.2 ("Soglie effettivamente implementate").
//
// Non modificare questi valori per "migliorare" la demo: rappresentano
// l'unica fonte di verità condivisa tra firmware, backend e app, esattamente
// come previsto dall'architettura del progetto.

export const DEVICE_DEFAULTS = {
  DEVICE_ID: 'ALVEA_04',
  DEFAULT_PUBLISH_PERIOD_S: 1,
  DEFAULT_ALARM_SPO2_MIN: 92.0,
  DEFAULT_ALARM_RESP_MAX: 40.0,
  DEFAULT_ALARM_BATTERY_MIN_PCT: 15.0,
  ALERT_FAULT_STREAK_THRESHOLD: 5, // letture consecutive prima di emettere un alert (alerts.py)
};

// Soglie statiche realmente implementate (Relazione, Sez. 5.2).
// La parametrizzazione dinamica per fascia d'eta' resta "Progettata"
// (Relazione, Sez. 6 / Tabella 5) e non altera queste soglie di
// warning/critico, che sono quelle effettivamente valutate dal backend.
export const THRESHOLDS = {
  fr: { warnLow: 14, warnHigh: 30, critLow: 10, critHigh: 40 },
  bpm: { warnLow: 70, warnHigh: 130, critLow: 60, critHigh: 150 },
  temp: { warnLow: 36.0, warnHigh: 37.2, critLow: 35.0, critHigh: 38.5 },
  spo2Min: 92.0,
  batteryMinPct: 15.0,
};

// Matrice fisiologica nominale per fascia d'eta' (Relazione, Tabella 3 — design).
// Mostrata in app come riferimento informativo: NON sostituisce le soglie
// di warning/critico sopra, che restano statiche nel prototipo attuale.
export const AGE_BANDS = {
  prescolare: {
    key: 'prescolare',
    label: 'Prescolare',
    rangeLabel: '1–5 anni',
    frNominal: '20–30 atti/min',
    bpmNominal: '80–140 BPM',
    bradipnea: '<16/min',
    tachipnea: '>40/min',
    bradicardia: '<70 BPM',
    tachicardia: '>150 BPM',
  },
  scolare: {
    key: 'scolare',
    label: 'Scolare',
    rangeLabel: '6–12 anni',
    frNominal: '16–24 atti/min',
    bpmNominal: '70–120 BPM',
    bradipnea: '<12/min',
    tachipnea: '>30/min',
    bradicardia: '<60 BPM',
    tachicardia: '>130 BPM',
  },
};

// Stati del campo device_status cosi' come pubblicati dal firmware
// (main_real_mqtt.py / main_sim_mqtt.py) nel payload di telemetria.
export const DEVICE_STATUS = {
  OK: 'SYSTEM_OK',
  ERR_ECG_LEADS_OFF: 'ERR_ECG_LEADS_OFF',
  ERR_PPG_NO_CONTACT: 'ERR_PPG_NO_CONTACT',
  ERR_TEMP_SENSOR_FAULT: 'ERR_TEMP_SENSOR_FAULT',
  WARN_NETWORK_DISCONNECTED: 'WARN_NETWORK_DISCONNECTED',
  WARN_PATIENT_NOT_ASSIGNED: 'WARN_PATIENT_NOT_ASSIGNED',
  INIT: 'INIT',
};

// Topic MQTT reali usati dal firmware (vedi firmware/config.py).
// L'app non si connette direttamente al broker (come da architettura:
// "nessun client interroga direttamente InfluxDB o il broker MQTT" —
// Relazione, Sez. 3.2): li riportiamo solo come riferimento/documentazione
// e per costruire i payload dei comandi inviati via backend.
export const mqttTopics = (deviceId) => ({
  telemetry: `alvea/devices/${deviceId}/telemetry`,
  alerts: `alvea/devices/${deviceId}/alerts`,
  commands: `alvea/devices/${deviceId}/commands`,
});

// Endpoint REST del backend FastAPI realmente previsti (Relazione, Tabella 2).
// BACKEND_BASE_URL e' l'unico valore da modificare per puntare a un backend
// reale: di default l'app gira in modalita' simulata (vedi services/dataSource.js).
export const BACKEND_BASE_URL = 'http://192.168.1.50:8000';
export const WS_LIVE_URL = BACKEND_BASE_URL.replace('http', 'ws') + '/ws/live';

// Endpoint coerenti con la Tabella 2 della Relazione.
export const ENDPOINTS = {
  register: '/register',
  login: '/login',
  devices: '/devices',
  deviceLatest: (id) => `/devices/${id}/latest`,
  deviceReadings: (id) => `/devices/${id}/readings`,
  deviceAlerts: (id) => `/devices/${id}/alerts`,
  wsLive: '/ws/live',
  sseLive: '/sse/live',
};

// Flag globale di modalita' dati: 'simulated' (default, nessuna infrastruttura
// richiesta) oppure 'backend' (richiede un backend FastAPI + broker reali in
// esecuzione sulla rete locale, secondo l'architettura Docker della Relazione).
export const DATA_SOURCE_MODE = 'simulated';
