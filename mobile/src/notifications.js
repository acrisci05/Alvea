// notifications.js - Gestione notifiche push/locali (expo-notifications).
//
// Basato sull'esempio del corso (registrazione token + handler). È reso
// "robusto": se manca il projectId EAS o i permessi, NON solleva eccezioni e
// l'app continua a funzionare usando solo le notifiche LOCALI (che scattano
// all'arrivo di un allarme dal WebSocket).
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";

// Mostra banner + suono anche quando l'app è in primo piano.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const ANDROID_CHANNEL = "alerts";

async function ensureAndroidChannel() {
  if (Platform.OS !== "android") return;
  await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL, {
    name: "Allarmi Alvea",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#E71D36",
    sound: "default",
  });
}

// Chiede i permessi e (se possibile) restituisce l'Expo push token, altrimenti
// null. Il token serve al backend per inviare notifiche push remote.
export async function registerForPushNotificationsAsync() {
  try {
    await ensureAndroidChannel();

    const current = await Notifications.getPermissionsAsync();
    let status = current.status;
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return null;

    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;
    // Senza un projectId EAS valido restiamo in modalità "solo locali".
    if (!projectId || projectId === "REPLACE_WITH_YOUR_EAS_PROJECT_ID") {
      return null;
    }

    const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
    return tokenData.data;
  } catch (e) {
    console.warn("[notifications] registrazione fallita:", e?.message || e);
    return null;
  }
}

// Mostra subito una notifica locale (funziona anche senza push remote).
export async function presentLocalAlert(title, body) {
  try {
    await Notifications.scheduleNotificationAsync({
      content: { title, body, sound: "default" },
      trigger: null,
    });
  } catch (e) {
    console.warn("[notifications] notifica locale fallita:", e?.message || e);
  }
}
