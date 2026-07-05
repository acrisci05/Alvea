export const API_URL = "http://192.168.1.50:8000";
export const getWsUrl = (token) =>
  API_URL.replace("http", "ws") + `/ws/live?token=${token}`;

// true per la demo senza backend; false quando il server reale è attivo.
export const DEMO_MODE = true;

// I dati vengono salvati per utente con patientInfoKeyFor(username):
// altrimenti, registrando più account sullo stesso dispositivo, i dati
// dell'uno sovrascriverebbero quelli dell'altro.
export const PATIENT_INFO_KEY = "alvea_patient_info";

// I nomi delle chiavi di SecureStore possono contenere solo lettere, numeri e
// i caratteri ".", "-", "_"
const sanitizeKeyPart = (value) =>
  String(value || "").trim().toLowerCase().replace(/[^a-z0-9._-]/g, "_");

// Chiave dei dati anagrafici del singolo account. Garantisce che ogni utente registrato mantenga i
// propri dati, anche con più registrazioni sullo stesso telefono.
export const patientInfoKeyFor = (username) =>
  `${PATIENT_INFO_KEY}_${sanitizeKeyPart(username)}`;

// Registro locale degli account creati in DEMO_MODE (username -> password/
// device). In demo non c'è un vero backend che ricordi chi si è
// registrato: senza questo, il login accetterebbe qualsiasi credenziale e non
// riuscirebbe a distinguere un account dall'altro.
export const DEMO_ACCOUNTS_KEY = "alvea_demo_accounts";


// Endpoint per la registrazione del token delle notifiche push
export const PUSH_API_URL = API_URL;