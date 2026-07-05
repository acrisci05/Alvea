import * as SecureStore from "expo-secure-store";
import { API_URL, DEMO_MODE, PUSH_API_URL, DEMO_ACCOUNTS_KEY } from "./config";

// --- Dati simulati per la demo ---
const MOCK_DELAY = 800;
const delay = (ms) => new Promise((res) => setTimeout(res, ms));

const readDemoAccounts = async () => {
  try {
    const raw = await SecureStore.getItemAsync(DEMO_ACCOUNTS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    console.warn("Impossibile leggere gli account demo:", e);
    return {};
  }
};

const writeDemoAccounts = async (accounts) => {
  try {
    await SecureStore.setItemAsync(DEMO_ACCOUNTS_KEY, JSON.stringify(accounts));
  } catch (e) {
    console.warn("Impossibile salvare gli account demo:", e);
  }
};

// Device id allineato al firmware
const MOCK_DEVICE_ID = "ALVEA_04";

const MOCK_LOGIN_RESPONSE = {
  access_token: "demo-token-alvea-2024",
  device_id: MOCK_DEVICE_ID,
};

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

// Schema allineato a alerts.py (_build_alert): i campi sono gravita
// (WARNING/CRITICAL/INFO), descrizione e parametro..
// I nomi vengono comunque normalizzati da normalizeAlert() in MonitorScreen,
// così l'app visualizza gli alert in modo uniforme.

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

// Funzione di supporto per fetch con timeout (backend reale).
const fetchWithTimeout = (url, options = {}, timeoutMs = 8000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(id)
  );
};

// Funzioni API

export const loginUser = async (username, password) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    // In demo le credenziali sono verificate contro gli account registrati,
    // così ogni account resta distinto e il login carica i dati corretti.
    const accounts = await readDemoAccounts();
    const account = accounts[username];
    if (!account || account.password !== password)
      throw new Error("Credenziali non valide");
    return {
      ...MOCK_LOGIN_RESPONSE,
      device_id: account.device_id || MOCK_DEVICE_ID,
      username,
      patientInfo: account.patientInfo || null,
    };
  }
  try {
    const bodyForm = new URLSearchParams({ username, password }).toString();
    const response = await fetchWithTimeout(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: bodyForm,
    });
    if (!response.ok) throw new Error("Credenziali non valide");
    const data = await response.json();
    // Restituiamo anche lo username, così l'app può conservare i dati
    // anagrafici separatamente per ciascun account.
    return { ...data, username: data.username || username };
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error("Server non raggiungibile. Controlla l'IP e la rete.");
    throw e;
  }
};

export const registerUser = async (username, password, patientInfo = {}) => {
  if (DEMO_MODE) {
    await delay(MOCK_DELAY);
    // Salviamo l'account nel registro locale. Se l'username esiste già lo
    // segnaliamo, invece di sovrascriverlo.
    const accounts = await readDemoAccounts();
    if (accounts[username])
      throw new Error("Username già registrato. Scegline un altro.");
    accounts[username] = { password, device_id: MOCK_DEVICE_ID, patientInfo };
    await writeDemoAccounts(accounts);
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

// Registrazione del token Expo per le notifiche push

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