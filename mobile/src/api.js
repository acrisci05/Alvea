import { API_URL, DEMO_MODE, PUSH_API_URL } from "./config";


// --- Dati simulati per la demo ---
const MOCK_DELAY = 800;
const delay = (ms) => new Promise((res) => setTimeout(res, ms));

// Device id allineato al firmware (config.DEVICE_ID in config.py: "ALVEA_04")
const MOCK_DEVICE_ID = "ALVEA_04";

const MOCK_LOGIN_RESPONSE = {
  access_token: "demo-token-alvea-2024",
  device_id: MOCK_DEVICE_ID,
  // In DEMO_MODE simuliamo un accesso da medico, così la demo mostra anche le
  // funzionalità riservate al medico (dashboard Grafana, configurazione device).
  role: "medico",
};

// Campi e nomi allineati al payload reale del device (vedi "reading" in
// main_real_mqtt.py/main_real_ble.py: device_id, patient_id, timestamp,
// bpm, skin_temperature, respiration_rate, battery_pct, sensor_contact,
// device_status, source). L'unico sensore biomedicale è l'ECG, da cui
// derivano bpm e, via EDR, la frequenza respiratoria.
const MOCK_LATEST = {
  device_id: MOCK_DEVICE_ID,
  patient_id: "demo-patient",
  sensor_contact: true,
  bpm: 102,
  respiration_rate: 28,
  skin_temperature: 36.6,
  battery_pct: 86.0,
  device_status: "SYSTEM_OK",
  source: "demo_mode",
  timestamp: new Date().toISOString(),
};

const MOCK_HISTORY = Array.from({ length: 10 }, (_, i) => ({
  device_id: MOCK_DEVICE_ID,
  patient_id: "demo-patient",
  sensor_contact: true,
  bpm: 90 + Math.floor(Math.random() * 20),
  respiration_rate: 24 + Math.floor(Math.random() * 8),
  skin_temperature: parseFloat((36.3 + Math.random() * 0.6).toFixed(1)),
  battery_pct: parseFloat((86 - i * 0.3).toFixed(1)),
  device_status: "SYSTEM_OK",
  source: "demo_mode",
  timestamp: new Date(Date.now() - i * 60000).toISOString(),
}));

// Schema allineato a alerts.py (_build_alert): gravita (WARNING/CRITICAL/
// INFO) + descrizione + parametro, non severity/message "all'inglese". I
// nomi vengono comunque normalizzati da normalizeAlert() in MonitorScreen,
// ma è bene che anche i dati di demo somiglino a un vero alert del device.
const MOCK_ALERTS = [
  {
    device_id: MOCK_DEVICE_ID,
    parametro: "respiration_rate",
    gravita: "CRITICAL",
    descrizione: "Tachipnea rilevata, frequenza respiratoria elevata (44.0 atti/min)",
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
  },
  {
    device_id: MOCK_DEVICE_ID,
    parametro: "battery",
    gravita: "WARNING",
    descrizione: "Batteria scarica rilevata (12%)",
    timestamp: new Date(Date.now() - 20 * 60000).toISOString(),
  },
];

// --- Helper fetch con timeout per il backend reale ---
const fetchWithTimeout = (url, options = {}, timeoutMs = 8000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(id)
  );
};

// --- Funzioni API ---

export const loginUser = async (username, password) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    return MOCK_LOGIN_RESPONSE;
  }
  try {
    const bodyForm = new URLSearchParams({ username, password }).toString();
    const response = await fetchWithTimeout(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: bodyForm,
    });
    if (!response.ok) throw new Error("Credenziali non valide");
    return await response.json();
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error("Server non raggiungibile. Controlla l'IP e la rete.");
    throw e;
  }
};

export const registerUser = async (username, password, patientInfo = {}) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    return {
      message: "Registrazione simulata completata.",
      patient: patientInfo,
    };
  }
  try {
    const response = await fetchWithTimeout(`${API_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, ...patientInfo }),
    });
    if (!response.ok) throw new Error("Impossibile completare la registrazione");
    return await response.json();
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error("Server non raggiungibile. Controlla l'IP e la rete.");
    throw e;
  }
};

export const fetchLatestReading = async (token, deviceId) => {
  if (DEMO_MODE) {
    await delay(500);
    return {
      ...MOCK_LATEST,
      bpm: 90 + Math.floor(Math.random() * 20),
      respiration_rate: 24 + Math.floor(Math.random() * 8),
      skin_temperature: parseFloat((36.3 + Math.random() * 0.5).toFixed(1)),
      timestamp: new Date().toISOString(),
    };
  }
  const response = await fetchWithTimeout(
    `${API_URL}/devices/${deviceId}/latest`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!response.ok) throw new Error("Nessun dato disponibile");
  return await response.json();
};

export const fetchSensorHistory = async (token, deviceId, limit = 20) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    return MOCK_HISTORY.slice(0, limit);
  }
  try {
    const response = await fetchWithTimeout(
      `${API_URL}/devices/${deviceId}/history?limit=${limit}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
};

export const fetchAlertHistory = async (token, deviceId, limit = 20) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    return MOCK_ALERTS.slice(0, limit);
  }
  try {
    const response = await fetchWithTimeout(
      `${API_URL}/devices/${deviceId}/alerts?limit=${limit}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
};

// --- Configurazione dispositivo da parte del medico (Punto 8 dei requisiti) ---
// Il firmware (vedi main_real_mqtt.py/main_real_ble.py, mqtt_callback/
// ble_command_callback) accetta comandi JSON con due chiavi opzionali:
//   - publish_period_s: frequenza di invio della telemetria (secondi);
//   - patient_id: associazione/rimozione paziente-dispositivo.
// Lato MQTT il comando va pubblicato dal backend sul topic
// "alvea/devices/<device_id>/commands" (config.TOPIC_CMD): l'app non parla
// MQTT direttamente, quindi passa da un endpoint REST che il backend
// Node-RED/Python dovrà esporre e che si occuperà di fare il publish reale.
export const sendDeviceCommand = async (token, deviceId, command = {}) => {
  if (DEMO_MODE) {
    await delay(400);
    console.log(
      "[DEMO_MODE] Comando non inviato realmente al device:",
      command
    );
    return { message: "Invio comando simulato (DEMO_MODE).", command };
  }
  try {
    const response = await fetchWithTimeout(
      `${API_URL}/devices/${deviceId}/commands`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(command),
      }
    );
    if (!response.ok) throw new Error("Invio del comando al dispositivo non riuscito");
    return await response.json();
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error("Server non raggiungibile. Controlla l'IP e la rete.");
    throw e;
  }
};

// --- Notifiche push (Punto 7 dei requisiti: gestione alert) ---
// Registra sul backend l'Expo Push Token del dispositivo, associandolo
// all'utente/paziente autenticato (token Bearer) e al device monitorato.
// Il backend (vedi push_backend_example/) lo userà per inviare una push
// reale quando rileva un alert critico, anche con l'app in background o
// chiusa — cosa che le sole notifiche locali (Notifications.js) non
// possono fare. Segue lo stesso pattern di /register-token visto
// nell'esempio dell'academy (app_con_notifica), adattato al contratto
// con autenticazione già usato dalle altre funzioni di questo file.
export const registerPushToken = async (token, deviceId, expoPushToken) => {
  if (DEMO_MODE) {
    await delay(300);
    console.log(
      "[DEMO_MODE] Push token non inviato realmente al backend:",
      expoPushToken
    );
    return { message: "Registrazione token simulata (DEMO_MODE)." };
  }
  try {
    const response = await fetchWithTimeout(`${PUSH_API_URL}/register-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        token: expoPushToken,
        device_id: deviceId,
      }),
    });
    if (!response.ok) throw new Error("Registrazione token push non riuscita");
    return await response.json();
  } catch (e) {
    // Non blocchiamo l'app se il backend push non è raggiungibile: le
    // notifiche locali (Notifications.js) restano comunque attive.
    console.warn("Impossibile registrare il push token:", e.message);
    return null;
  }
};
