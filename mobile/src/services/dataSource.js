// src/services/dataSource.js
//
// Punto unico di accesso ai dati di telemetria: nasconde a screens/contesti
// se la fonte sia il simulatore locale o un backend FastAPI reale, in base
// a DATA_SOURCE_MODE (src/config.js). Cambiare quel singolo flag e fornire
// BACKEND_BASE_URL e' sufficiente per passare dalla demo standalone a un
// ecosistema Alvea realmente in esecuzione (Docker stack + firmware reale).

import { DATA_SOURCE_MODE } from '../config';
import * as api from './api';

export const isSimulated = DATA_SOURCE_MODE === 'simulated';

/**
 * Invia un comando di riconfigurazione al device. In modalita' simulata
 * aggiorna solo lo stato locale (gestito dal chiamante); in modalita'
 * 'backend' lo propaga realmente via POST /devices/{id}/commands -> MQTT.
 */
export async function sendCommand(deviceId, params, token) {
  if (isSimulated) {
    // Nessuna chiamata di rete: il chiamante aggiorna lo stato del device
    // simulato direttamente (vedi context/TelemetryContext.js).
    return Promise.resolve({ ok: true, simulated: true, params });
  }
  return api.sendDeviceCommand(deviceId, params, token);
}

export async function fetchHistory(deviceId, limit, token) {
  if (isSimulated) {
    return Promise.resolve([]); // lo storico simulato vive in TelemetryContext
  }
  return api.getReadingsHistory(deviceId, limit, token);
}

export async function fetchAlerts(deviceId, token) {
  if (isSimulated) {
    return Promise.resolve([]);
  }
  return api.getDeviceAlerts(deviceId, token);
}

export { api };
