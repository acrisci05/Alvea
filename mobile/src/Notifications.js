import * as Notifications from "expo-notifications";
import Constants from "expo-constants";

// Comportamento delle notifiche quando l'app è in primo piano (foreground).
// A partire da Expo SDK 53 il campo `shouldShowAlert` è deprecato: al suo
// posto vanno specificati `shouldShowBanner` (banner in alto) e
// `shouldShowList` (comparsa nel centro notifiche). Vengono impostati
// entrambi, così l'avviso resta visibile anche con l'applicazione aperta.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// Richiede all'utente il permesso di ricevere notifiche e restituisce lo
// stato finale: la stringa "granted" se il permesso è concesso, altrimenti
// null.
export async function registerForPushNotifications() {
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

// Invia una notifica locale immediata per un alert clinico. Oltre alle
// gravità "WARNING" e "CRITICAL", il firmware può emettere alert con gravità
// "INFO" quando una condizione precedentemente segnalata rientra nella norma
// (condizione risolta).
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
          : "Attenzione — Alvea",
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
    // L'eventuale errore non deve interrompere l'esecuzione dell'app.
    console.warn("Invio notifica fallito:", e.message);
  }
}

// Registra sul backend il token push del dispositivo, così che gli alert
// siano recapitati anche con l'app chiusa o in background. Il flusso è:
//   1. genera un Expo Push Token legato al projectId EAS dell'applicazione;
//   2. lo invia al backend, che lo utilizzerà per inviare notifiche push
//      reali tramite il servizio Expo Push (a sua volta basato su FCM/APNs)
//      quando rileva un alert critico sul paziente associato.
//
// La generazione del token richiede un dispositivo fisico: su simulatore o su
// web `getExpoPushTokenAsync` non è supportata e solleva un'eccezione. In quel
// caso l'errore viene gestito senza interrompere l'app, che continua a
// utilizzare le sole notifiche locali (attive quando è in primo piano).
export async function registerExpoPushTokenOnBackend(token, deviceId) {
  try {
    // Il projectId EAS è necessario per generare un Expo Push Token.
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;

    if (!projectId) {
      console.warn(
        "projectId EAS non trovato in app.json (extra.eas.projectId): " +
        "necessario per generare un Expo Push Token."
      );
      return null;
    }

    const { data: expoPushToken } = await Notifications.getExpoPushTokenAsync({
      projectId,
    });

    if (!expoPushToken) return null;

    // Import differito per evitare una dipendenza circolare tra api.js e
    // Notifications.js.
    const { registerPushToken } = require("./api");
    await registerPushToken(token, deviceId, expoPushToken);

    return expoPushToken;
  } catch (e) {
    // Nessun blocco dell'app: in assenza di un push token reale restano
    // attive le notifiche locali quando l'app è in primo piano.
    console.warn(
      "Generazione/registrazione Expo Push Token fallita:",
      e.message
    );
    return null;
  }
}