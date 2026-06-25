import * as Notifications from "expo-notifications";
import Constants from "expo-constants";


// Configura il comportamento delle notifiche quando l'app è in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// Controlla se siamo su un dispositivo fisico (le notifiche push non funzionano
// su simulatore/web — questo evita errori silenziosi durante la demo)
function isPhysicalDevice() {
  return Constants.isDevice === true;
}

// Richiede il permesso all'utente e restituisce lo stato finale
export async function registerForPushNotifications() {
  if (!isPhysicalDevice()) {
    console.warn(
      "Le notifiche push funzionano solo su dispositivo fisico. " +
      "Su simulatore o web le notifiche locali verranno comunque tentate."
    );
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.warn("Permesso notifiche non concesso.");
    return null;
  }

  return finalStatus;
}

// Invia una notifica locale immediata per un alert clinico.
// Accetta sia lo schema gia' normalizzato da MonitorScreen (severity/message)
// sia, in via defensive, lo schema originale del firmware (gravita/
// descrizione: vedi alerts.py), così la funzione resta sicura anche se
// richiamata altrove con un alert non ancora normalizzato.
//
// Il firmware invia anche alert con gravita "INFO" quando una condizione
// precedentemente segnalata si risolve (vedi alerts.py: check_fault,
// ramo "else"). Per questi non ha senso un titolo "EMERGENZA"/
// "Attenzione": sarebbe fuorviante notificare come allarme la notizia
// che un parametro e' rientrato nella norma.
export async function sendAlertNotification(alert) {
  const rawSeverity = alert.severity ?? alert.gravita ?? "attenzione";
  const normalizedSeverity = String(rawSeverity).toLowerCase();
  const isCritical =
    normalizedSeverity === "critico" || normalizedSeverity === "critical";
  const isInfo = normalizedSeverity === "info";
  const body = alert.message ?? alert.descrizione ?? "Anomalia rilevata";

  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: isInfo
          ? "Aggiornamento — Alvea"
          : isCritical
          ? "EMERGENZA — Alvea"
          : " Attenzione — Alvea",
        body,
        sound: !isInfo,
        priority: isCritical
          ? Notifications.AndroidNotificationPriority.MAX
          : isInfo
          ? Notifications.AndroidNotificationPriority.DEFAULT
          : Notifications.AndroidNotificationPriority.HIGH,
      },
      trigger: null, // Notifica immediata
    });
  } catch (e) {
    // Non blocchiamo l'app se la notifica fallisce (es. su web/simulatore)
    console.warn("Invio notifica fallito:", e.message);
  }
}

// --- Push notifications reali (Expo Push Token + backend) ---
//
// Quanto sopra (sendAlertNotification) copre solo il caso "app aperta in
// foreground": è una notifica locale, generata e mostrata dal telefono
// stesso quando arriva un alert via WebSocket. Non funziona se l'app è in
// background o chiusa.
//
// Per coprire anche quel caso (Punto 7 dei requisiti: alert visibili
// anche fuori dall'app — vedi incontro_realtime_grafana.pdf, sezione
// "Push Notifications / Fuori dall'App") seguiamo lo stesso pattern visto
// nell'esempio dell'academy (app_con_notifica/codice_notify/app/App.js):
// 1. richiediamo il permesso notifiche;
// 2. generiamo un Expo Push Token legato al projectId EAS dell'app;
// 3. lo inviamo al backend, che lo userà per inviare push reali tramite
//    il servizio Expo Push (a sua volta basato su FCM/APNs) quando rileva
//    un alert critico sul paziente associato.
//
// Questa funzione NON sostituisce registerForPushNotifications() sopra:
// va chiamata in aggiunta, una volta che l'utente è autenticato (serve
// token + deviceId per registrare il push token lato backend).
export async function registerExpoPushTokenOnBackend(token, deviceId) {
  if (!isPhysicalDevice()) {
    console.warn(
      "Expo Push Token non generato: i push token reali richiedono un " +
      "dispositivo fisico (su simulatore/web restano attive solo le " +
      "notifiche locali)."
    );
    return null;
  }

  try {
    // Riusa expo-constants già importato in questo file (vedi import in
    // testa al file) per leggere il projectId configurato in app.json.
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;

    if (!projectId) {
      console.warn(
        "projectId EAS non trovato in app.json (extra.eas.projectId): " +
        "necessario per generare un Expo Push Token. Vedi app_con_notifica " +
        "dell'academy per un esempio di configurazione."
      );
      return null;
    }

    const { data: expoPushToken } = await Notifications.getExpoPushTokenAsync({
      projectId,
    });

    if (!expoPushToken) return null;

    // Import "lazy" per evitare una dipendenza circolare tra api.js e
    // Notifications.js (api.js non importa nulla da questo file).
    const { registerPushToken } = require("./api");
    await registerPushToken(token, deviceId, expoPushToken);

    return expoPushToken;
  } catch (e) {
    // Non blocchiamo l'app: senza push token reale restano comunque
    // attive le notifiche locali quando l'app è in foreground.
    console.warn("Generazione/registrazione Expo Push Token fallita:", e.message);
    return null;
  }
}
