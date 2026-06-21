// src/services/api.js
//
// Client per il backend FastAPI REALE descritto nella Relazione Tecnica
// (Tabella 2: autenticazione JWT, CRUD device, storico letture/alert,
// realtime via WebSocket). Usato solo quando DATA_SOURCE_MODE === 'backend'
// in src/config.js.
//
// Per impostazione predefinita l'app NON usa questo modulo (vedi
// services/simulator.js + context/TelemetryContext.js): e' qui pronto e
// coerente con l'architettura del progetto per quando backend, broker
// MQTT e stack Docker (Relazione, Sez. 3) saranno raggiungibili in rete.

import { BACKEND_BASE_URL, WS_LIVE_URL, ENDPOINTS } from '../config';

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BACKEND_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Richiesta ${method} ${path} fallita (${res.status}): ${text}`);
  }
  const contentType = res.headers.get('content-type') || '';
  return contentType.includes('application/json') ? res.json() : res.text();
}

/** POST /register — registrazione di un account caregiver. */
export function registerCaregiver({ name, email, password }) {
  return request(ENDPOINTS.register, {
    method: 'POST',
    body: { name, email, password },
  });
}

/** POST /login — OAuth2 password flow, ritorna un token JWT. */
export function loginCaregiver({ email, password }) {
  return request(ENDPOINTS.login, {
    method: 'POST',
    body: { username: email, password },
  });
}

/** POST /devices — associa una cavigliera (device_id) al caregiver autenticato. */
export function registerDevice({ deviceId, patientId, ageBand }, token) {
  return request(ENDPOINTS.devices, {
    method: 'POST',
    body: { device_id: deviceId, patient_id: patientId, age_band: ageBand },
    token,
  });
}

/** GET /devices — elenco dei device di proprieta' del caregiver. */
export function listDevices(token) {
  return request(ENDPOINTS.devices, { token });
}

/** GET /devices/{id}/latest — ultima lettura di telemetria del device. */
export function getLatestReading(deviceId, token) {
  return request(ENDPOINTS.deviceLatest(deviceId), { token });
}

/** GET /devices/{id}/readings?limit=N — storico delle ultime letture. */
export function getReadingsHistory(deviceId, limit = 50, token) {
  return request(`${ENDPOINTS.deviceReadings(deviceId)}?limit=${limit}`, { token });
}

/** GET /devices/{id}/alerts — storico degli allarmi generati per il device. */
export function getDeviceAlerts(deviceId, token) {
  return request(ENDPOINTS.deviceAlerts(deviceId), { token });
}

/**
 * Apre il canale WebSocket realtime /ws/live (Relazione, Tabella 2).
 * onMessage riceve il payload di telemetria gia' parsato (stesso schema
 * JSON canonico pubblicato dal firmware su alvea/devices/<id>/telemetry).
 * Ritorna una funzione di cleanup da chiamare per chiudere la connessione.
 */
export function subscribeLiveTelemetry({ token, onMessage, onError }) {
  const url = token ? `${WS_LIVE_URL}?token=${token}` : WS_LIVE_URL;
  const socket = new WebSocket(url);

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      onMessage?.(payload);
    } catch (err) {
      onError?.(err);
    }
  };
  socket.onerror = (event) => {
    onError?.(event);
  };

  return () => {
    socket.close();
  };
}

/**
 * Invia un comando di configurazione al device tramite il backend, che lo
 * propaga sul topic MQTT alvea/devices/<device_id>/commands (vedi
 * firmware/main_real_mqtt.py — mqtt_callback). Endpoint amministrativo
 * POST /medical/thresholds e rotte di configurazione device sono
 * "Progettate" nella Relazione (Sez. 6): qui il path e' predisposto secondo
 * lo stesso schema REST del resto della Tabella 2.
 */
export function sendDeviceCommand(deviceId, { publishPeriodS, patientId }, token) {
  return request(`/devices/${deviceId}/commands`, {
    method: 'POST',
    body: {
      publish_period_s: publishPeriodS,
      patient_id: patientId,
    },
    token,
  });
}
