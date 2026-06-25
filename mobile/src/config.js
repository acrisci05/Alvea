export const API_URL = "http://192.168.1.50:8000";

export const getWsUrl = (token) =>
  API_URL.replace("http", "ws") + `/ws/live?token=${token}`;

// Metti true per la demo senza backend, false quando il server è attivo
export const DEMO_MODE = true;

// Chiave SecureStore per i dati anagrafici minimi del paziente (Punto 9
// dei requisiti: scheda paziente), salvati da LoginScreen al momento della
// registrazione e letti da MonitorScreen per mostrarli all'utente.
export const PATIENT_INFO_KEY = "alvea_patient_info";

// --- Dashboard medico in Grafana (Punto 6 dei requisiti) ---
// URL del singolo pannello/dashboard Grafana da mostrare in app tramite
// WebView (vedi GrafanaScreen.js). Si usa la modalità kiosk di Grafana
// (?kiosk) per nascondere menu e sidebar, mostrando solo i grafici, ed
// eventualmente variabili di template (es. &var-device_id=...) per
// filtrare per paziente/dispositivo come richiesto al Punto 6.
// Da sostituire con l'URL reale del proprio server Grafana (incontro
// "Real-Time Ecosystem": Grafana esposto su porta 3000) una volta
// disponibile, idealmente con un utente Grafana di tipo "Viewer" dedicato
// ai medici (solo lettura, nessuna modifica alle dashboard).
export const GRAFANA_URL =
  "http://192.168.1.50:3000/d/alvea-monitor/alvea-monitoraggio-paziente?orgId=1&kiosk";

// Alcuni progetti distinguono un ruolo "medico" da uno "paziente" (Punto 4
// dei requisiti). In DEMO_MODE, senza un vero backend che restituisca il
// ruolo dell'utente autenticato, questo flag decide se mostrare la voce
// "Dashboard Grafana" in MonitorScreen. Con backend reale, sostituire con
// il ruolo ricevuto da loginUser() (es. { access_token, device_id, role }).
export const SHOW_GRAFANA_TAB = true;

// --- Notifiche push (Punto 7 dei requisiti: gestione alert) ---
// Endpoint del backend che riceve l'Expo Push Token del dispositivo e che
// invia le notifiche push quando il backend rileva un alert (vedi il
// modulo di esempio in push_backend_example/, da integrare nel backend
// Node-RED + Python del progetto). Lasciare uguale a API_URL se il
// backend espone questi endpoint sullo stesso servizio delle altre API
// REST, oppure puntare a un servizio dedicato.
export const PUSH_API_URL = API_URL;