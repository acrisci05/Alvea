// Indirizzo del backend FastAPI.
// IMPORTANTE: su device fisico NON usare "localhost" (punta al telefono).
// Usa l'IP del PC nella rete locale, es. "http://192.168.1.50:8000".
export const API_URL = "http://192.168.1.50:8000";
export const WS_URL = API_URL.replace("http", "ws") + "/ws/live";
export const DEVICE_ID = "PULSEGUARD_BABY_04";
