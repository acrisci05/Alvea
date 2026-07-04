import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  Platform,
  TextInput,
  Modal,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import * as SecureStore from "expo-secure-store";
import { getWsUrl, PATIENT_INFO_KEY, SHOW_GRAFANA_TAB } from "./config";
import { fetchLatestReading, fetchSensorHistory, fetchAlertHistory, sendDeviceCommand } from "./api";
import styles from "./style";
import {
  registerForPushNotifications,
  registerExpoPushTokenOnBackend,
  sendAlertNotification,
} from "./Notifications";
import GrafanaScreen from "./GrafanaScreen";

// --- Soglie cliniche per neonati/lattanti ---
// Allineate al firmware (config.py + alerts.py): l'unico alert clinico
// "su soglia" generato dal device è la tachipnea. L'unico sensore
// biomedicale è l'ECG, da cui derivano bpm e, via EDR, la frequenza
// respiratoria (vedi sensor_ecg.py e resp_edr.py). Il device non genera
// alcun alert basato su una soglia di temperatura alta (sensor_temp.py
// legge il valore ma alerts.py non lo confronta con nessuna soglia:
// l'unico alert di temperatura è "guasto sensore", non "febbre").
//
// Intervalli "nominali" mostrati nelle card sono quindi puramente
// informativi/orientativi (servono al genitore per leggere il numero),
// non alert clinici autonomi: l'unico vero allarme clinico per soglia è
// la tachipnea, qui RESP_MAX, identica a DEFAULT_ALARM_RESP_MAX in
// config.py.
const RESP_MIN = 20;
const RESP_MAX = 40;          // = config.DEFAULT_ALARM_RESP_MAX (tachipnea/asma pediatrico)
const TEMP_MIN = 36.0;
const TEMP_MAX = 37.2;
const BPM_MIN = 60;
const BPM_MAX = 180;

// Soglia di batteria scarica, allineata a config.DEFAULT_ALARM_BATTERY_MIN_PCT
// (alerts.py: check_battery). Il firmware genera un vero alert WARNING su
// questa soglia: la mostriamo con lo stesso peso visivo delle altre
// condizioni di guasto, invece che come semplice numero passivo.
const BATTERY_LOW_PCT = 15.0;

// Il firmware (vedi main_real_*.py / sensor_sim.py) usa time.time(), che
// produce un timestamp Unix in SECONDI (es. 1782115200.5). Il costruttore
// Date() di JavaScript si aspetta invece i MILLISECONDI: passare il valore
// del firmware cosi' com'e' produrrebbe sempre una data nel 1970. I dati di
// demo, invece, usano gia' stringhe ISO (new Date().toISOString()), che
// Date() interpreta correttamente. Questa funzione distingue i due casi.
function toDate(timestamp) {
  if (typeof timestamp === "number") {
    // Timestamp Unix in secondi (tipico di time.time() in Python/MicroPython):
    // un valore "ragionevole" in millisecondi sarebbe enormemente più
    // grande (13 cifre vs 10), quindi un numero sotto questa soglia è
    // quasi certamente espresso in secondi.
    return timestamp < 1e12 ? new Date(timestamp * 1000) : new Date(timestamp);
  }
  return new Date(timestamp);
}

// Il firmware (alerts.py: _build_alert) pubblica alert con i campi
// "gravita" (WARNING/CRITICAL/INFO) e "descrizione", non "severity"/
// "message" come nei dati di demo. Normalizziamo qui un'unica volta,
// così il resto del componente e le notifiche locali lavorano sempre su
// un formato coerente, indipendentemente da quale dei due schemi arriva
// dal backend.
//
// Il firmware invia "INFO" quando una condizione di guasto/soglia
// precedentemente segnalata RIENTRA (vedi alerts.py: check_fault, ramo
// "else" — testo con suffisso "(RISOLTO)"). Va distinto sia da WARNING
// che da CRITICAL: schiacciarlo su "attenzione" farebbe apparire ogni
// risoluzione come un nuovo problema invece che come buona notizia.
function normalizeAlert(a) {
  const rawSeverity = a.severity ?? a.gravita ?? "attenzione";
  const severity = String(rawSeverity).toLowerCase();
  const isCriticalSeverity =
    severity === "critico" || severity === "critical";
  const isInfoSeverity = severity === "info";
  return {
    ...a,
    severity: isCriticalSeverity
      ? "critico"
      : isInfoSeverity
      ? "info"
      : "attenzione",
    message: a.message ?? a.descrizione ?? "Anomalia rilevata",
  };
}

// Il firmware (vedi main_real_*.py) riporta lo stato del dispositivo come
// codice tecnico (es. "ERR_ECG_LEADS_OFF", "WARN_NETWORK_DISCONNECTED").
// Per un paziente/caregiver (Punto 3 dei requisiti: "stato del dispositivo,
// se disponibile") mostriamo una traduzione leggibile invece della
// stringa grezza; se il codice non è tra quelli noti, mostriamo comunque
// l'originale come fallback, per non perdere informazione.
const DEVICE_STATUS_LABELS = {
  SYSTEM_OK: "Tutto regolare",
  ERR_ECG_LEADS_OFF: "Elettrodi ECG non a contatto",
  ERR_TEMP_SENSOR_FAULT: "Sensore di temperatura guasto",
  WARN_NETWORK_DISCONNECTED: "Dispositivo offline (rete assente)",
  WARN_BLE_DISCONNECTED: "Dispositivo non connesso (Bluetooth)",
  WARN_PATIENT_NOT_ASSIGNED: "Dispositivo non associato a un paziente",
};

function formatDeviceStatus(status) {
  if (!status) return "";
  return DEVICE_STATUS_LABELS[status] ?? status;
}

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export default function MonitorScreen({ token, deviceId, role, onLogout }) {
  // Distinzione lato genitore / lato medico (Punto 4 dei requisiti): le
  // funzionalità riservate al medico (dashboard Grafana e configurazione del
  // device) vengono mostrate solo se l'utente ha effettuato l'accesso come
  // medico. SHOW_GRAFANA_TAB resta un override di sviluppo (vedi config.js).
  const isMedico = role === "medico";
  const showMedicoTools = isMedico || SHOW_GRAFANA_TAB;

  const [reading, setReading] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [connected, setConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  // Dati anagrafici minimi del paziente (Punto 9 dei requisiti: scheda
  // paziente, parzialmente visibile al paziente stesso). Salvati in
  // SecureStore al momento della registrazione (vedi LoginScreen.js).
  const [patientInfo, setPatientInfo] = useState(null);
  // Naviga verso la dashboard Grafana (Punto 6 dei requisiti) senza
  // introdurre una libreria di navigazione: MonitorScreen resta la
  // schermata "live", GrafanaScreen si apre sopra di essa e torna
  // indietro con onBack.
  const [showGrafana, setShowGrafana] = useState(false);

  // Modal di configurazione (Punto 8 dei requisiti: "Il medico deve poter
  // configurare almeno alcuni parametri del sistema", es. "frequenza di
  // campionamento o invio dati"). L'azione è riservata al medico: il pulsante
  // che apre questa modale è mostrato solo quando showMedicoTools è vero.
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [publishPeriodInput, setPublishPeriodInput] = useState("");
  const [sendingCommand, setSendingCommand] = useState(false);

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const isMountedRef = useRef(true);

  const loadHistory = useCallback(async () => {
    try {
      const [histData, alertData] = await Promise.all([
        fetchSensorHistory(token, deviceId, 20),
        fetchAlertHistory(token, deviceId, 20),
      ]);
      setHistory(histData);
      setAlerts(alertData.map(normalizeAlert));
    } catch (e) {
      console.error("Errore caricamento storico:", e);
    }
  }, [token, deviceId]);

  useEffect(() => {
    registerForPushNotifications().then((status) => {
      // Solo se l'utente ha concesso il permesso generiamo e registriamo
      // il vero Expo Push Token sul backend: senza permesso non avrebbe
      // senso provare a generarne uno (vedi Notifications.js).
      if (status === "granted") {
        registerExpoPushTokenOnBackend(token, deviceId);
      }
    });
    loadHistory();

    // Recupera i dati anagrafici del paziente, se presenti (potrebbero
    // non esserci se l'account è stato creato prima di questa funzionalità,
    // o se il login avviene su un device diverso da quello di registrazione).
    SecureStore.getItemAsync(PATIENT_INFO_KEY)
      .then((raw) => {
        if (raw) setPatientInfo(JSON.parse(raw));
      })
      .catch((e) => console.warn("Impossibile leggere i dati anagrafici:", e));
  }, [loadHistory]);

  // Connessione WebSocket con exponential backoff
  const connectWebSocket = useCallback(() => {
    if (!isMountedRef.current) return;

    try {
      const ws = new WebSocket(getWsUrl(token));
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setConnected(true);
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (m.type === "reading" && m.device_id === deviceId) {
            setReading(m);
            if (m.alerts && m.alerts.length > 0) {
              const normalizedAlerts = m.alerts.map(normalizeAlert);
              setAlerts((prev) => [...normalizedAlerts, ...prev].slice(0, 20));
              normalizedAlerts.forEach((a) => sendAlertNotification(a));
            }
          }
        } catch (parseError) {
          console.warn("Messaggio WebSocket non valido:", parseError);
        }
      };

      ws.onerror = () => {
        // onclose viene sempre chiamato dopo onerror, gestiamo tutto lì
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setConnected(false);

        const attempt = reconnectAttemptRef.current;
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, attempt) + Math.random() * 500,
          RECONNECT_MAX_MS
        );
        reconnectAttemptRef.current = attempt + 1;

        console.log(
          `WebSocket chiuso. Riconnessione in ${Math.round(delay)}ms (tentativo ${attempt + 1})`
        );
        reconnectTimerRef.current = setTimeout(connectWebSocket, delay);
      };
    } catch (e) {
      console.error("Connessione WebSocket fallita:", e);
    }
  }, [token, deviceId]);

  useEffect(() => {
    isMountedRef.current = true;
    connectWebSocket();

    // Polling REST di fallback se WebSocket non è connesso
    const poll = setInterval(async () => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        try {
          const r = await fetchLatestReading(token, deviceId);
          if (isMountedRef.current) setReading(r);
        } catch (_e) {
          // Fallback silenzioso
        }
      }
    }, 5000);

    return () => {
      isMountedRef.current = false;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      clearInterval(poll);
    };
  }, [connectWebSocket, token, deviceId]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  // Invia al device, tramite il backend, il comando di cambio frequenza
  // di campionamento/invio (Punto 8 dei requisiti). Il firmware accetta
  // la chiave "publish_period_s" sia via MQTT (TOPIC_CMD) sia via BLE
  // (characteristic di comando) — vedi main_real_mqtt.py/main_real_ble.py.
  const handleSendPublishPeriod = async () => {
    const seconds = parseInt(publishPeriodInput, 10);
    if (!Number.isFinite(seconds) || seconds <= 0) {
      Alert.alert(
        "Valore non valido",
        "Inserisci un numero intero di secondi maggiore di zero."
      );
      return;
    }
    setSendingCommand(true);
    try {
      await sendDeviceCommand(token, deviceId, { publish_period_s: seconds });
      setShowConfigModal(false);
      setPublishPeriodInput("");
      Alert.alert(
        "Comando inviato",
        `Il dispositivo invierà i dati ogni ${seconds} secondi.`
      );
    } catch (e) {
      Alert.alert("Errore", e.message || "Invio del comando non riuscito.");
    } finally {
      setSendingCommand(false);
    }
  };

  // Chiede conferma prima di fare logout
  const handleLogoutPress = () => {
    Alert.alert(
      "Esci",
      "Vuoi davvero uscire? Il monitoraggio verrà interrotto.",
      [
        { text: "Annulla", style: "cancel" },
        { text: "Esci", style: "destructive", onPress: onLogout },
      ]
    );
  };

  // --- Lettura valori correnti ---
  // Il firmware (vedi main_real_*.py / sensor_sim.py) invia bpm,
  // respiration_rate, skin_temperature, battery_pct: manteniamo i vecchi
  // nomi come fallback (??) per non rompere eventuali backend di transizione,
  // ma i campi del contratto reale del dispositivo vengono letti per primi.
  const contact = reading?.sensor_contact;
  const resp = reading?.respiration_rate ?? reading?.respiration ?? reading?.rr ?? "--";
  const temp = reading?.skin_temperature ?? reading?.temperature ?? "--";
  const bpm = reading?.bpm ?? "--";
  const batteryPct = reading?.battery_pct ?? null;

  // --- Stato clinico corrente ---
  // Tachipnea (frequenza respiratoria SOPRA soglia): è l'unico alert
  // clinico per soglia generato dal firmware (alerts.py: check_resp_rate,
  // gravità CRITICAL) — coerente con l'uso clinico del dispositivo
  // (asma pediatrico, non apnea). Non esiste invece nessuna soglia minima
  // lato firmware: una respirazione bassa o assente si manifesta solo
  // come perdita di contatto ECG (sensor_contact === false), già coperta
  // dal banner "Sensore non a contatto" più sotto.
  const isEmergency =
    contact && typeof resp === "number" && resp > RESP_MAX;

  // Batteria scarica: vero alert WARNING lato firmware (alerts.py:
  // check_battery, soglia config.DEFAULT_ALARM_BATTERY_MIN_PCT).
  const isBatteryLow =
    typeof batteryPct === "number" && batteryPct < BATTERY_LOW_PCT;

  // Colori: grigio se sensore staccato, rosso se fuori soglia nominale, verde se ok
  const respColor = !contact
    ? "#A0AAB2"
    : typeof resp === "number" && (resp < RESP_MIN || resp > RESP_MAX)
    ? "#E57373"
    : "#66BB6A";

  const tempColor = !contact
    ? "#A0AAB2"
    : typeof temp === "number" && (temp > TEMP_MAX || temp < TEMP_MIN)
    ? "#E57373"
    : "#66BB6A";

  const bpmColor = !contact
    ? "#A0AAB2"
    : typeof bpm === "number" && (bpm < BPM_MIN || bpm > BPM_MAX)
    ? "#E57373"
    : "#66BB6A";

  const isCritical = (severity) =>
    severity === "critico" || severity === "critical";

  // "info" = condizione precedentemente segnalata e ora RISOLTA (vedi
  // alerts.py del firmware, ramo "else" di check_fault). Va mostrata in
  // modo visivamente distinto da un nuovo problema.
  const isInfo = (severity) => severity === "info";

  // Dashboard Grafana (Punto 6 dei requisiti): schermata separata che
  // sostituisce temporaneamente il contenuto di MonitorScreen. Il tasto
  // "‹" della WebView riporta qui, ai dati live.
  if (showGrafana) {
    return <GrafanaScreen onBack={() => setShowGrafana(false)} />;
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header con titolo e pulsante logout esplicito */}
      <View style={styles.monitorHeader}>
        <View style={styles.headerRow}>
          <Text style={styles.header}>Alvea</Text>
          <View style={{ flexDirection: "row", alignItems: "center" }}>
            {showMedicoTools && (
              <TouchableOpacity
                onPress={() => setShowConfigModal(true)}
                activeOpacity={0.7}
                style={[styles.logoutBtn, { marginRight: 4 }]}
              >
                <Text style={[styles.logoutText, { fontSize: 22 }]}>⚙️</Text>
              </TouchableOpacity>
            )}
            {showMedicoTools && (
              <TouchableOpacity
                onPress={() => setShowGrafana(true)}
                activeOpacity={0.7}
                style={[styles.logoutBtn, { marginRight: 4 }]}
              >
                <Text style={[styles.logoutText, { fontSize: 22 }]}>📊</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              onPress={handleLogoutPress}
              activeOpacity={0.7}
              style={styles.logoutBtn}
            >
              <Text style={styles.logoutText}>‹</Text>
            </TouchableOpacity>
          </View>
        </View>
        <Text style={styles.status}>
          {connected
            ? "● Monitoraggio Attivo"
            : reconnectAttemptRef.current > 0
            ? `○ Riconnessione in corso... (${reconnectAttemptRef.current})`
            : "○ In attesa di connessione..."}
          {" — "}
          {deviceId}
        </Text>
        {patientInfo && (
          <Text style={styles.status}>
            👤 {patientInfo.patient_name}
            {"  •  "}
            {patientInfo.age_years} anni, {patientInfo.age_months} mesi
          </Text>
        )}
      </View>

      {/* Banner EMERGENZA — Tachipnea (frequenza respiratoria sopra soglia,
          unico alert clinico per soglia generato dal firmware: vedi
          alerts.py check_resp_rate, gravità CRITICAL). */}
      {isEmergency && (
        <View style={styles.bannerEmergency}>
          <Text style={styles.bannerEmergencyText}>
            🚨 EMERGENZA — Tachipnea, frequenza respiratoria elevata ({resp} atti/min)
          </Text>
        </View>
      )}

      {/* Banner BATTERIA SCARICA (alert WARNING lato firmware: vedi
          alerts.py check_battery, soglia config.DEFAULT_ALARM_BATTERY_MIN_PCT). */}
      {isBatteryLow && !isEmergency && (
        <View style={styles.bannerFever}>
          <Text style={styles.bannerFeverText}>
            🔋 Batteria del dispositivo scarica ({batteryPct}%)
          </Text>
        </View>
      )}

      {/* Banner SENSORE STACCATO */}
      {!contact && reading && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>
            ⚠ Rilevamento interrotto: Sensore non a contatto
          </Text>
        </View>
      )}

      <ScrollView
        contentContainerStyle={{ paddingBottom: 30 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Card Frequenza Cardiaca */}
        <View style={styles.card}>
          <Text style={styles.label}>Frequenza Cardiaca</Text>
          <Text style={[styles.big, { color: bpmColor }]}>
            {bpm} <Text style={styles.unit}>bpm</Text>
          </Text>
          <Text style={styles.rangeHint}>
            Intervallo nominale: {BPM_MIN}–{BPM_MAX} bpm
          </Text>
        </View>

        {/* Card Frequenza Respiratoria */}
        <View style={styles.card}>
          <Text style={styles.label}>Frequenza Respiratoria</Text>
          <Text style={[styles.big, { color: respColor }]}>
            {resp} <Text style={styles.unit}>Atti/min</Text>
          </Text>
          <Text style={styles.rangeHint}>
            Intervallo nominale: {RESP_MIN}–{RESP_MAX} atti/min
          </Text>
        </View>

        {/* Card Temperatura Corporea */}
        <View style={styles.card}>
          <Text style={styles.label}>Temperatura Corporea</Text>
          <Text style={[styles.big, { color: tempColor }]}>
            {temp} <Text style={styles.unit}>°C</Text>
          </Text>
          <Text style={styles.rangeHint}>
            Intervallo nominale: {TEMP_MIN}–{TEMP_MAX} °C
          </Text>
        </View>

        {/* Stato del dispositivo: batteria (Requisito 3 - "stato del
            dispositivo, se disponibile"). Colore rosso quando sotto la
            soglia del firmware (BATTERY_LOW_PCT), come le altre card
            fuori range — coerente col vero alert WARNING lato device. */}
        {batteryPct !== null && (
          <Text style={[styles.rangeHint, isBatteryLow && { color: "#E57373", fontWeight: "700" }]}>
            🔋 Batteria dispositivo: {batteryPct}%
            {reading?.device_status
              ? `  •  ${formatDeviceStatus(reading.device_status)}`
              : ""}
          </Text>
        )}

        {/* Storico Letture */}
        <Text style={styles.section}>Storico Letture</Text>
        {history.length === 0 ? (
          <Text style={styles.muted}>Nessuno storico disponibile.</Text>
        ) : (
          history.map((h, i) => (
            <View key={i} style={styles.historyRow}>
              <Text style={styles.historyTime}>
                {toDate(h.timestamp).toLocaleTimeString("it-IT")}
              </Text>
              <Text style={styles.historyValSmall}>
                {h.bpm ?? "--"} bpm
              </Text>
              <Text style={styles.historyValSmall}>
                {h.respiration_rate ?? h.respiration ?? h.rr ?? "--"} atti/min
              </Text>
              <Text style={styles.historyValSmall}>
                {h.skin_temperature ?? h.temperature ?? "--"} °C
              </Text>
              <Text style={styles.historyValSmall}>
                {h.battery_pct ?? "--"}% batt.
              </Text>
            </View>
          ))
        )}

        {/* Allarmi Recenti */}
        <Text style={styles.section}>Allarmi Recenti</Text>
        {alerts.length === 0 ? (
          <Text style={styles.muted}>Nessuna anomalia rilevata.</Text>
        ) : (
          alerts.map((a, i) => (
            <View
              key={i}
              style={[
                styles.alert,
                isCritical(a.severity) && styles.alertCrit,
                isInfo(a.severity) && styles.alertInfo,
              ]}
            >
              <Text style={styles.alertKind}>
                {isInfo(a.severity) ? "RISOLTO" : a.severity.toUpperCase()}
              </Text>
              <Text style={styles.alertMsg}>{a.message}</Text>
              {a.timestamp && (
                <Text style={styles.alertTime}>
                  {toDate(a.timestamp).toLocaleString("it-IT")}
                </Text>
              )}
            </View>
          ))
        )}
      </ScrollView>

      {/* Modal di configurazione (Punto 8 dei requisiti): permette di
          impostare la frequenza di invio della telemetria. Il comando
          viene inoltrato dal backend al device via MQTT/BLE (vedi
          sendDeviceCommand in api.js e mqtt_callback/ble_command_callback
          nel firmware). */}
      <Modal
        visible={showConfigModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowConfigModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.label}>Frequenza di invio dati</Text>
            <Text style={[styles.muted, { paddingHorizontal: 0, marginTop: 6, marginBottom: 14 }]}>
              Imposta ogni quanti secondi il dispositivo deve inviare la
              telemetria (es. 1 = un dato al secondo).
            </Text>
            <TextInput
              style={styles.input}
              placeholder="Secondi (es. 1)"
              placeholderTextColor="#A0AAB2"
              keyboardType="number-pad"
              value={publishPeriodInput}
              onChangeText={setPublishPeriodInput}
            />
            <TouchableOpacity
              style={styles.btn}
              disabled={sendingCommand}
              onPress={handleSendPublishPeriod}
            >
              <Text style={styles.btnText}>
                {sendingCommand ? "Invio in corso..." : "Invia al dispositivo"}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.linkBtn}
              disabled={sendingCommand}
              onPress={() => {
                setShowConfigModal(false);
                setPublishPeriodInput("");
              }}
            >
              <Text style={styles.link}>Annulla</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}
