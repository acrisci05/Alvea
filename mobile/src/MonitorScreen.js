import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  Modal,
  TextInput,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as SecureStore from "expo-secure-store";
import { getWsUrl, PATIENT_INFO_KEY, patientInfoKeyFor } from "./config";
import { fetchLatestReading, fetchSensorHistory, fetchAlertHistory } from "./api";
import styles, { colors } from "./style";
import {
  registerForPushNotifications,
  registerExpoPushTokenOnBackend,
  sendAlertNotification,
} from "./Notifications";

// --- Soglie cliniche pediatriche, calibrate sull'età del bambino ---
// Battito e respiro variano molto con l'età; la temperatura no.
// I valori sono i centili 1° e 99° delle tabelle evidence-based di Fleming
// et al. (Lancet 2011, "Normal ranges of heart rate and respiratory rate in
// children from birth to 18 years", Web Table 4 e 5): un valore fuori
// dall'intervallo 1°-99° centile è considerato anomalo. Il primo anno è
// suddiviso in sotto-fasce, dove battito e respiro cambiano più rapidamente;
// dopo l'anno le fasce sono più ampie e i loro estremi sono l'inviluppo
// (minimo dei 1° centili, massimo dei 99°) delle sotto-fasce di Fleming
// comprese, così da non generare falsi allarmi. Restano soglie indicative:
// non sostituiscono quelle che il pediatra può impostare per il singolo bambino.
function referenceRanges(patientInfo) {
  const hasAge = patientInfo && Number.isFinite(patientInfo.age_years);
  const months = hasAge
    ? patientInfo.age_years * 12 + (patientInfo.age_months || 0)
    : null;
  // La temperatura misurata è cutanea, tipicamente inferiore a quella interna.
  // Il valore di riferimento clinico comunemente accettato per la temperatura
  // interna è di circa 36,5-37,5 °C; qui si adotta una banda leggermente più
  // bassa e stretta, coerente con la misura sulla pelle. Non dipende dall'età.
  const temp = { min: 36.0, max: 37.2 };

  if (months === null)
    return { bpm: { min: 43, max: 181 }, resp: { min: 11, max: 66 }, temp, band: "—" };
  // --- Primo anno: sotto-fasce (Fleming, centili 1°-99°) ---
  if (months < 3)
    return { bpm: { min: 90, max: 181 }, resp: { min: 25, max: 66 }, temp, band: "0-3 mesi" };
  if (months < 6)
    return { bpm: { min: 104, max: 175 }, resp: { min: 24, max: 64 }, temp, band: "3-6 mesi" };
  if (months < 9)
    return { bpm: { min: 98, max: 168 }, resp: { min: 23, max: 61 }, temp, band: "6-9 mesi" };
  if (months < 12)
    return { bpm: { min: 93, max: 161 }, resp: { min: 22, max: 58 }, temp, band: "9-12 mesi" };
  // --- Dopo l'anno: fasce ampie (inviluppo delle sotto-fasce di Fleming) ---
  if (months < 24)
    return { bpm: { min: 82, max: 156 }, resp: { min: 19, max: 53 }, temp, band: "1-2 anni" };
  if (months < 72)
    return { bpm: { min: 65, max: 142 }, resp: { min: 17, max: 38 }, temp, band: "2-5 anni" };
  if (months < 144)
    return { bpm: { min: 52, max: 123 }, resp: { min: 14, max: 27 }, temp, band: "6-11 anni" };
  return { bpm: { min: 43, max: 108 }, resp: { min: 11, max: 23 }, temp, band: "12-18 anni" };
}

const BATTERY_LOW_PCT = 15.0;

// Finestra di verifica: un allarme "scatta" solo se la condizione anomala
// persiste per almeno questo tempo. Riduce i falsi allarmi (movimenti,
// sensore che perde contatto un istante) e gli allarmismi ingiustificati.
const ALARM_CONFIRM_MS = 20000;

// Se non arrivano nuove letture da più di questo tempo, il segnale è
// considerato assente (fascia scollegata / persa): si mostra un avviso
// non allarmante, non un allarme.
const STALE_MS = 15000;

// Tabella mostrata nella pagina "Valori normali per età". Le fasce e i valori
// coincidono con referenceRanges() (centili 1°-99° di Fleming 2011). Il campo
// band serve a evidenziare la fascia del bambino attualmente registrato.
const AGE_BANDS_INFO = [
  { band: "0-3 mesi", age: "0 - 3 mesi", bpm: "90-181", resp: "25-66" },
  { band: "3-6 mesi", age: "3 - 6 mesi", bpm: "104-175", resp: "24-64" },
  { band: "6-9 mesi", age: "6 - 9 mesi", bpm: "98-168", resp: "23-61" },
  { band: "9-12 mesi", age: "9 - 12 mesi", bpm: "93-161", resp: "22-58" },
  { band: "1-2 anni", age: "1 - 2 anni", bpm: "82-156", resp: "19-53" },
  { band: "2-5 anni", age: "2 - 5 anni", bpm: "65-142", resp: "17-38" },
  { band: "6-11 anni", age: "6 - 11 anni", bpm: "52-123", resp: "14-27" },
  { band: "12-18 anni", age: "12 - 18 anni", bpm: "43-108", resp: "11-23" },
];

// Backoff esponenziale per la riconnessione WebSocket.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

// Il firmware usa time.time() (timestamp Unix in SECONDI); Date() di JS si
// aspetta i MILLISECONDI. Questa funzione distingue i due casi (e gestisce
// anche le stringhe ISO dei dati di demo).
function toDate(timestamp) {
  if (typeof timestamp === "number") {
    return timestamp < 1e12 ? new Date(timestamp * 1000) : new Date(timestamp);
  }
  if (typeof timestamp === "string") {
    // Le datetime del backend arrivano come str(datetime), es. "2026-07-05
    // 13:39:00.123456": spazio al posto della 'T' e microsecondi a 6 cifre,
    // un formato che alcuni motori JS (Hermes su React Native) non riescono a
    // interpretare e che darebbe "Invalid date". Lo normalizziamo in ISO con
    // millisecondi a 3 cifre; le stringhe già ISO restano invariate.
    const iso = timestamp.replace(" ", "T").replace(/(\.\d{3})\d+$/, "$1");
    return new Date(iso);
  }
  return new Date(timestamp);
}

// Il momento di una lettura/alert può arrivare come "ts" (datetime del backend,
// sia via REST sia via WebSocket) oppure come "timestamp" (payload del firmware
// e dati di demo). Restituisce il primo campo disponibile, così la stessa riga
// funziona con qualunque sorgente.
function tsOf(x) {
  return x?.ts ?? x?.timestamp;
}

// Il firmware (alerts.py: _build_alert) pubblica alert con i campi "gravita"
// e "descrizione"; i dati di demo usano "severity"/"message". Normalizziamo
// qui in un unico formato. "INFO" = condizione precedentemente segnalata e
// ora RISOLTA.
function normalizeAlert(a) {
  const rawSeverity = a.severity ?? a.gravita ?? "attenzione";
  const severity = String(rawSeverity).toLowerCase();
  const isCriticalSeverity = severity === "critico" || severity === "critical";
  const isInfoSeverity = severity === "info";
  return {
    ...a,
    severity: isCriticalSeverity ? "critico" : isInfoSeverity ? "info" : "attenzione",
    message: a.message ?? a.descrizione ?? "Anomalia rilevata",
  };
}

// Traduce i codici di stato tecnici del firmware in testo leggibile.
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

// Etichetta leggibile del sesso salvato ("M"/"F").
function sexLabel(sex) {
  if (sex === "M") return "Maschio";
  if (sex === "F") return "Femmina";
  return "--";
}

// Etichetta leggibile dell'età: mostra solo le parti che servono
// (es. "3 anni e 4 mesi", "4 mesi", "3 anni") 
function formatAge(years, months) {
  const y = Number.isFinite(years) ? years : 0;
  const m = Number.isFinite(months) ? months : 0;
  if (y === 0 && m === 0) return "Meno di un mese";
  const parts = [];
  if (y > 0) parts.push(`${y} ${y === 1 ? "anno" : "anni"}`);
  if (m > 0) parts.push(`${m} ${m === 1 ? "mese" : "mesi"}`);
  return parts.join(" e ");
}

export default function MonitorScreen({ token, deviceId, username, onLogout }) {
  const [reading, setReading] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [connected, setConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [patientInfo, setPatientInfo] = useState(null);
  // Scheda attualmente visibile: "home" | "alerts" | "profile".
  const [tab, setTab] = useState("home");
  // Allarmi arrivati e non ancora visualizzati (per l'indicatore sulla scheda).
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  // Margini di sicurezza del dispositivo (notch, barra gesti/home indicator).
  const insets = useSafeAreaInsets();
  // Apertura delle due pagine informative (range per età / primo soccorso).
  const [infoOpen, setInfoOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  // Spiegazione della verifica in corso (mostrata dal tasto info quando la
  // Home è nello stato "Verifica in corso").
  const [verifyOpen, setVerifyOpen] = useState(false);
  // Modifica del profilo del bambino.
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editYears, setEditYears] = useState(0);
  const [editMonths, setEditMonths] = useState(0);
  const [editSex, setEditSex] = useState("");
  // Allarme confermato solo dopo la finestra di verifica (vedi sotto).
  const [alarmConfirmed, setAlarmConfirmed] = useState(false);
  const abnormalSinceRef = useRef(null);
  // Segnale assente (nessuna lettura recente).
  const [signalLost, setSignalLost] = useState(false);
  const lastReadingAtRef = useRef(null);

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const isMountedRef = useRef(true);
  // Riferimento sempre aggiornato alla scheda attiva: serve dentro il
  // callback del WebSocket, che altrimenti "vedrebbe" un valore obsoleto.
  const tabRef = useRef(tab);

  // Tiene allineato tabRef e azzera i non letti quando si apre "Allarmi".
  useEffect(() => {
    tabRef.current = tab;
    if (tab === "alerts") setUnreadAlerts(0);
  }, [tab]);

  // Carica storico letture + storico allarmi dal backend (REST).
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

  // Aggiunge una lettura in tempo reale in cima allo storico (max 20 righe),
  // evitando di duplicare la riga se ha lo stesso timestamp della prima.
  const addReadingToHistory = useCallback((m) => {
    const t = tsOf(m);
    if (!m || !t) return;
    setHistory((prev) => {
      if (prev.length > 0 && tsOf(prev[0]) === t) return prev;
      return [m, ...prev].slice(0, 20);
    });
  }, []);

  // All'avvio: registra le notifiche push, carica lo storico e i dati paziente.
  useEffect(() => {
    registerForPushNotifications().then((status) => {
      if (status === "granted") registerExpoPushTokenOnBackend(token, deviceId);
    });
    loadHistory();
    // Carichiamo i dati anagrafici DELL'ACCOUNT loggato. Se non li troviamo
    // sotto la chiave per-utente (es. account creato con una versione
    // precedente), proviamo la vecchia chiave globale come ripiego.
    (async () => {
      try {
        let raw = username
          ? await SecureStore.getItemAsync(patientInfoKeyFor(username))
          : null;
        if (!raw) raw = await SecureStore.getItemAsync(PATIENT_INFO_KEY);
        if (raw) setPatientInfo(JSON.parse(raw));
      } catch (e) {
        console.warn("Impossibile leggere i dati anagrafici:", e);
      }
    })();
  }, [loadHistory, username]);

  // Connessione WebSocket in tempo reale con riconnessione automatica (backoff).
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
            addReadingToHistory(m);
            if (m.alerts && m.alerts.length > 0) {
              const normalized = m.alerts.map(normalizeAlert);
              setAlerts((prev) => [...normalized, ...prev].slice(0, 20));
              normalized.forEach((a) => sendAlertNotification(a));
              // Se l'utente non è sulla scheda Allarmi, segnala i nuovi
              // arrivi con l'indicatore.
              if (tabRef.current !== "alerts") {
                setUnreadAlerts((n) => n + normalized.length);
              }
            }
          } else if (m.type === "alert" && m.device_id === deviceId) {
            // Alert hardware/locale inoltrato dal backend (batteria scarica,
            // guasto sensore, leads-off persistente): arriva come messaggio a
            // sé, non incluso in una lettura. Senza questo ramo comparirebbe
            // solo al successivo refresh REST e non in tempo reale.
            const normalized = normalizeAlert(m);
            setAlerts((prev) => [normalized, ...prev].slice(0, 20));
            sendAlertNotification(normalized);
            if (tabRef.current !== "alerts") {
              setUnreadAlerts((n) => n + 1);
            }
          }
        } catch (parseError) {
          console.warn("Messaggio WebSocket non valido:", parseError);
        }
      };

      // Gli errori di connessione sono gestiti in onclose (che avvia la
      // riconnessione); qui si sopprime solo il log di default.
      ws.onerror = () => {};

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setConnected(false);
        const attempt = reconnectAttemptRef.current;
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, attempt) + Math.random() * 500,
          RECONNECT_MAX_MS
        );
        reconnectAttemptRef.current = attempt + 1;
        reconnectTimerRef.current = setTimeout(connectWebSocket, delay);
      };
    } catch (e) {
      console.error("Connessione WebSocket fallita:", e);
    }
  }, [token, deviceId, addReadingToHistory]);

  // Avvia il WebSocket e un polling REST di fallback (ogni 5s) attivo quando
  // il WebSocket non è disponibile.
  useEffect(() => {
    isMountedRef.current = true;
    connectWebSocket();

    const poll = setInterval(async () => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        try {
          const r = await fetchLatestReading(token, deviceId);
          if (isMountedRef.current) {
            setReading(r);
            addReadingToHistory(r);
          }
        } catch (_e) {}
      }
    }, 5000);

    return () => {
      isMountedRef.current = false;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      clearInterval(poll);
    };
  }, [connectWebSocket, token, deviceId, addReadingToHistory]);

  // Ogni nuova lettura azzera il timer del "segnale assente".
  useEffect(() => {
    if (reading) {
      lastReadingAtRef.current = Date.now();
      setSignalLost(false);
    }
  }, [reading]);

  // Controlla periodicamente se le letture si sono fermate da troppo tempo.
  useEffect(() => {
    const id = setInterval(() => {
      if (lastReadingAtRef.current && Date.now() - lastReadingAtRef.current > STALE_MS) {
        setSignalLost(true);
      }
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const handleLogoutPress = () => {
    Alert.alert("Esci", "Vuoi davvero uscire? Il monitoraggio verrà interrotto.", [
      { text: "Annulla", style: "cancel" },
      { text: "Esci", style: "destructive", onPress: onLogout },
    ]);
  };

  // Apre il form di modifica precompilato con i dati attuali del bambino.
  const openEditProfile = () => {
    setEditName(patientInfo?.patient_name || "");
    setEditYears(patientInfo?.age_years ?? 0);
    setEditMonths(patientInfo?.age_months ?? 0);
    setEditSex(patientInfo?.sex || "");
    setEditOpen(true);
  };

  const changeEditYears = (d) => setEditYears((v) => Math.min(18, Math.max(0, v + d)));
  const changeEditMonths = (d) => setEditMonths((v) => Math.min(11, Math.max(0, v + d)));

  // Salva le modifiche: aggiorna lo stato e li conserva localmente. Gli
  // intervalli per età si ricalcolano da soli al prossimo render.
  const saveProfile = async () => {
    if (!editName.trim())
      return Alert.alert("Attenzione", "Inserisci il nome del paziente");
    if (!editSex)
      return Alert.alert("Attenzione", "Seleziona il sesso del bambino");
    const updated = {
      ...(patientInfo || {}),
      patient_name: editName.trim(),
      age_years: editYears,
      age_months: editMonths,
      sex: editSex,
    };
    setPatientInfo(updated);
    try {
      const key = username ? patientInfoKeyFor(username) : PATIENT_INFO_KEY;
      await SecureStore.setItemAsync(key, JSON.stringify(updated));
    } catch (e) {
      console.warn("Impossibile salvare i dati anagrafici:", e);
    }
    setEditOpen(false);
  };

  // --- Valori correnti ---
  const contact = reading?.sensor_contact;
  const resp = reading?.respiration_rate ?? reading?.respiration ?? reading?.rr ?? "--";
  const temp = reading?.skin_temperature ?? reading?.temperature ?? "--";
  const bpm = reading?.bpm ?? "--";
  const batteryPct = reading?.battery_pct ?? null;

  // Intervalli di riferimento calibrati sull'età del bambino registrato.
  const ranges = referenceRanges(patientInfo);

  const isEmergency = contact && typeof resp === "number" && resp > ranges.resp.max;
  const isBatteryLow = typeof batteryPct === "number" && batteryPct < BATTERY_LOW_PCT;

  const outOfRange = (v, r) => typeof v === "number" && (v < r.min || v > r.max);
  const anyOut =
    contact &&
    (outOfRange(bpm, ranges.bpm) ||
      outOfRange(resp, ranges.resp) ||
      outOfRange(temp, ranges.temp));

  const valueColor = (v, r) =>
    !contact ? colors.valueMuted : outOfRange(v, r) ? colors.valueBad : colors.valueGood;
  const respColor = valueColor(resp, ranges.resp);
  const tempColor = valueColor(temp, ranges.temp);
  const bpmColor = valueColor(bpm, ranges.bpm);

  // --- Finestra di verifica (anti falsi allarmi) ---
  // Un valore fuori intervallo diventa allarme confermato solo se persiste
  // per ALARM_CONFIRM_MS. Durante l'attesa la Home mostra "Verifica in corso".
  const rawAbnormal = isEmergency || anyOut;
  useEffect(() => {
    if (!reading || !rawAbnormal) {
      abnormalSinceRef.current = null;
      setAlarmConfirmed(false);
      return;
    }
    if (abnormalSinceRef.current == null) abnormalSinceRef.current = Date.now();
    const remaining = ALARM_CONFIRM_MS - (Date.now() - abnormalSinceRef.current);
    if (remaining <= 0) {
      setAlarmConfirmed(true);
      return;
    }
    setAlarmConfirmed(false);
    const t = setTimeout(() => setAlarmConfirmed(true), remaining);
    return () => clearTimeout(t);
  }, [reading, rawAbnormal]);
  // Anomalia in corso ma non ancora confermata (dentro i 20 secondi).
  const pendingAlarm = rawAbnormal && !alarmConfirmed;

  const isCritical = (severity) => severity === "critico" || severity === "critical";
  const isInfo = (severity) => severity === "info";

  // Stato riassuntivo mostrato nel banner in cima alla Home 
  let homeStatus;
  if (!contact && reading) {
    homeStatus = {
      title: "Sensore non a contatto",
      sub: "Rilevamento momentaneamente interrotto",
      bg: colors.neutralBg, border: colors.neutralBorder, dot: colors.neutralDot, color: colors.neutralText,
    };
  } else if (signalLost) {
    homeStatus = {
      title: "Segnale assente",
      sub: "Rilevamento interrotto: controlla che la fascia sia indossata e ben collegata",
      bg: colors.neutralBg, border: colors.neutralBorder, dot: colors.neutralDotAlt, color: colors.neutralTextAlt,
    };
  } else if (pendingAlarm) {
    homeStatus = {
      title: "Verifica in corso",
      sub: "Controllo dei valori prima di segnalare",
      bg: colors.infoBg, border: colors.infoBorder, dot: colors.infoDot, color: colors.info,
    };
  } else if (isEmergency) {
    homeStatus = {
      title: "Attenzione",
      sub: `Frequenza respiratoria elevata (${resp} atti/min)`,
      bg: colors.dangerBg, border: colors.dangerBorder, dot: colors.dangerDot, color: colors.danger,
    };
  } else if (anyOut) {
    homeStatus = {
      title: "Attenzione",
      sub: "Alcuni parametri sono fuori dall'intervallo per l'età",
      bg: colors.warningBg, border: colors.warningBorder, dot: colors.warningDot, color: colors.warning,
    };
  } else if (isBatteryLow) {
    homeStatus = {
      title: "Batteria scarica",
      sub: `Livello ${batteryPct}% \u2014 sostituire presto`,
      bg: colors.warningBg, border: colors.warningBorder, dot: colors.warningDot, color: colors.warning,
    };
  } else if (reading) {
    homeStatus = {
      title: "Tutto regolare",
      sub: "Parametri nella norma per l'età",
      bg: colors.successBg, border: colors.successBorder, dot: colors.successDot, color: colors.success,
    };
  } else {
    homeStatus = {
      title: "In attesa dei dati",
      sub: "Connessione al dispositivo in corso",
      bg: colors.neutralBg, border: colors.neutralBorder, dot: colors.neutralDot, color: colors.neutralText,
    };
  }

  // Etichetta Normale / Fuori norma per la card della frequenza cardiaca.
  const bpmIsOut = outOfRange(bpm, ranges.bpm);
  const showBpmChip = contact && typeof bpm === "number";

  // ====================== SCHEDA: HOME (monitoraggio) ======================
  const HomeTab = (
    <ScrollView
      style={styles.flexFill}
      contentContainerStyle={styles.tabContent}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Intestazione con chip di stato connessione */}
      <View style={styles.headerRow}>
        <Text style={styles.header}>Alvea</Text>
        <View style={[styles.connChip, connected ? styles.connChipOn : styles.connChipOff]}>
          <View
            style={[styles.connDot, { backgroundColor: connected ? colors.connOn : colors.connOff }]}
          />
          <Text style={[styles.connChipText, { color: connected ? colors.connOnText : colors.connOffText }]}>
            {connected ? "Attivo" : "Non connesso"}
          </Text>
        </View>
      </View>

      {/* Banner di stato riassuntivo, con tasto info sui range per età */}
      <View style={[styles.statusHero, { backgroundColor: homeStatus.bg, borderColor: homeStatus.border }]}>
        <View style={[styles.statusHeroDot, { backgroundColor: homeStatus.dot }]} />
        <View style={styles.flexFill}>
          <Text style={[styles.statusHeroTitle, { color: homeStatus.color }]}>{homeStatus.title}</Text>
          <Text style={styles.statusHeroSub}>{homeStatus.sub}</Text>
        </View>
        {!signalLost && (
          <TouchableOpacity
            style={styles.infoBtn}
            onPress={() => (pendingAlarm ? setVerifyOpen(true) : setInfoOpen(true))}
            activeOpacity={0.7}
            accessibilityLabel={
              pendingAlarm
                ? "Cosa significa verifica in corso"
                : "Informazioni sui valori normali per età"
            }
          >
            <Text style={[styles.infoBtnText, { color: homeStatus.color }]}>i</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Card principale: frequenza cardiaca */}
      <View style={styles.card}>
        <View style={styles.metricHeadRow}>
          <Text style={styles.label}>Frequenza Cardiaca</Text>
          {showBpmChip && (
            <View style={[styles.metricChip, bpmIsOut ? styles.metricChipBad : styles.metricChipGood]}>
              <Text style={[styles.metricChipText, { color: bpmIsOut ? colors.danger : colors.success }]}>
                {bpmIsOut ? "Fuori norma" : "Normale"}
              </Text>
            </View>
          )}
        </View>
        <Text style={[styles.big, { color: bpmColor }]}>
          {bpm} <Text style={styles.unit}>bpm</Text>
        </Text>
        <Text style={styles.rangeHint}>
          {`Intervallo per l'età: ${ranges.bpm.min}\u2013${ranges.bpm.max} bpm${
            ranges.band !== "\u2014" ? "  \u2022  " + ranges.band : ""
          }`}
        </Text>
      </View>

      {/* Card affiancate: respiratoria e temperatura */}
      <View style={styles.halfRow}>
        <View style={styles.halfCard}>
          <Text style={styles.halfLabel}>Frequenza respiratoria</Text>
          <Text style={[styles.halfBig, { color: respColor }]}>
            {resp} <Text style={styles.halfUnit}>atti/min</Text>
          </Text>
          <Text style={styles.halfRange}>
            {`${ranges.resp.min}\u2013${ranges.resp.max}`}
          </Text>
        </View>
        <View style={styles.halfCard}>
          <Text style={styles.halfLabel}>Temperatura</Text>
          <Text style={[styles.halfBig, { color: tempColor }]}>
            {temp} <Text style={styles.halfUnit}>°C</Text>
          </Text>
          <Text style={styles.halfRange}>
            {`${ranges.temp.min}\u2013${ranges.temp.max}`}
          </Text>
        </View>
      </View>

      {batteryPct !== null && (
        <Text
          style={[
            styles.rangeHint,
            styles.batteryLine,
            isBatteryLow && { color: colors.valueBad, fontWeight: "700" },
          ]}
        >
          {"Batteria dispositivo: "}
          {batteryPct}%
          {reading?.device_status ? "  \u2022  " + formatDeviceStatus(reading.device_status) : ""}
        </Text>
      )}

      {/* Storico letture come mini-tabella */}
      <Text style={styles.section}>Storico Letture</Text>
      {history.length === 0 ? (
        <Text style={styles.muted}>Nessuno storico disponibile.</Text>
      ) : (
        <View style={styles.histCard}>
          <View style={styles.histHeadRow}>
            <Text style={[styles.histHead, styles.histTimeCol]}>Ora</Text>
            <Text style={[styles.histHead, styles.histRight]}>bpm</Text>
            <Text style={[styles.histHead, styles.histRight]}>atti/min</Text>
            <Text style={[styles.histHead, styles.histRight]}>°C</Text>
          </View>
          {history.slice(0, 10).map((h, i, arr) => (
            <View
              key={i}
              style={[styles.histRow, i === arr.length - 1 && styles.histRowLast]}
            >
              <Text style={[styles.histTime, styles.histTimeCol]}>
                {toDate(tsOf(h)).toLocaleTimeString("it-IT")}
              </Text>
              <Text style={[styles.histVal, styles.histRight]}>{h.bpm ?? "--"}</Text>
              <Text style={[styles.histVal, styles.histRight]}>
                {h.respiration_rate ?? h.respiration ?? h.rr ?? "--"}
              </Text>
              <Text style={[styles.histVal, styles.histRight]}>
                {h.skin_temperature ?? h.temperature ?? "--"}
              </Text>
            </View>
          ))}
        </View>
      )}

    </ScrollView>
  );

  // ====================== SCHEDA: ALLARMI ======================
  const severityColor = (severity) =>
    isCritical(severity) ? colors.danger : isInfo(severity) ? colors.success : colors.warning;
  const severityLabel = (severity) =>
    isInfo(severity) ? "Risolto" : isCritical(severity) ? "Critico" : "Attenzione";

  const AlertsTab = (
    <ScrollView
      style={styles.flexFill}
      contentContainerStyle={styles.tabContent}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.headerRow}>
        <Text style={styles.header}>Allarmi</Text>
      </View>
      <Text style={styles.status}>Cronologia delle anomalie rilevate</Text>

      {/* Guida di primo soccorso per i genitori */}
      <TouchableOpacity
        style={styles.guideBtn}
        onPress={() => setGuideOpen(true)}
        activeOpacity={0.8}
      >
        <View style={styles.flexFill}>
          <Text style={styles.guideBtnTitle}>Guida di primo soccorso</Text>
          <Text style={styles.guideBtnSub}>Cosa fare subito quando scatta un allarme</Text>
        </View>
        <Text style={styles.guideBtnArrow}>{"\u203A"}</Text>
      </TouchableOpacity>

      {alerts.length === 0 ? (
        <Text style={styles.muted}>Nessuna anomalia rilevata.</Text>
      ) : (
        alerts.map((a, i) => (
          <View key={i} style={styles.alert}>
            <Text style={[styles.alertKind, { color: severityColor(a.severity) }]}>
              {severityLabel(a.severity)}
            </Text>
            <Text style={styles.alertMsg}>{a.message}</Text>
            {tsOf(a) && (
              <Text style={styles.alertTime}>{toDate(tsOf(a)).toLocaleString("it-IT")}</Text>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );

  // ====================== SCHEDA: PROFILO ======================
  // Iniziale del nome per l'avatar (fallback "?" se manca il nome).
  const avatarInitial =
    ((patientInfo?.patient_name || "").trim().charAt(0) || "?").toUpperCase();

  const ProfileTab = (
    <ScrollView style={styles.flexFill} contentContainerStyle={styles.tabContentProfile}>
      <View style={styles.headerRow}>
        <Text style={styles.header}>Profilo</Text>
      </View>

      {/* Cerchio con l'iniziale e, sotto, il nome del paziente */}
      <View style={styles.profileAvatarWrap}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{avatarInitial}</Text>
        </View>
        <Text style={styles.profileName}>
          {patientInfo?.patient_name ? patientInfo.patient_name : "Paziente"}
        </Text>
      </View>

      {/* Dati anagrafici del paziente */}
      <Text style={styles.softSection}>Paziente</Text>
      <View style={styles.softCard}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Età</Text>
          <Text style={styles.infoValue}>
            {patientInfo ? formatAge(patientInfo.age_years, patientInfo.age_months) : "--"}
          </Text>
        </View>
        <View style={[styles.infoRow, styles.infoRowLast]}>
          <Text style={styles.infoLabel}>Sesso</Text>
          <Text style={styles.infoValue}>
            {patientInfo ? sexLabel(patientInfo.sex) : "--"}
          </Text>
        </View>
      </View>

      {/* Dispositivo e stato monitoraggio */}
      <Text style={styles.softSection}>Dispositivo</Text>
      <View style={styles.softCard}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Identificativo</Text>
          <Text style={styles.infoValue}>{deviceId}</Text>
        </View>
        <View style={[styles.infoRow, styles.infoRowLast]}>
          <Text style={styles.infoLabel}>Connessione</Text>
          <View style={styles.statusDotRow}>
            <View
              style={[
                styles.statusDot,
                { backgroundColor: connected ? colors.connOnAlt : colors.neutralBorder },
              ]}
            />
            <Text style={styles.infoValue}>{connected ? "Attivo" : "Non connesso"}</Text>
          </View>
        </View>
      </View>

      {/* Modifica del profilo del bambino (es. quando cambia l'età) */}
      <TouchableOpacity style={styles.editBtn} onPress={openEditProfile} activeOpacity={0.8}>
        <Text style={styles.editBtnText}>Modifica profilo</Text>
      </TouchableOpacity>

      {/* Uscita: pulsante delicato con contorno morbido */}
      <TouchableOpacity
        style={styles.logoutSoftBtn}
        onPress={handleLogoutPress}
        activeOpacity={0.8}
      >
        <Text style={styles.logoutSoftText}>Esci</Text>
      </TouchableOpacity>
      <Text style={styles.logoutCaption}>Il monitoraggio verrà interrotto</Text>
    </ScrollView>
  );

  // ====================== LAYOUT: contenuto + barra schede ======================
  return (
    <SafeAreaView style={styles.container} edges={["top", "left", "right"]}>
      {tab === "home" && HomeTab}
      {tab === "alerts" && AlertsTab}
      {tab === "profile" && ProfileTab}

      <View style={[styles.bottomNav, { paddingBottom: insets.bottom + 8 }]}>
        <TouchableOpacity style={styles.navItem} onPress={() => setTab("home")} activeOpacity={0.7}>
          <Ionicons
            name={tab === "home" ? "home" : "home-outline"}
            size={22}
            color={tab === "home" ? colors.navActive : colors.navInactive}
            style={styles.navIconVector}
          />
          <View style={[styles.navIndicator, tab === "home" && styles.navIndicatorActive]} />
          <Text style={[styles.navText, tab === "home" && styles.navTextActive]}>Home</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navItem} onPress={() => setTab("alerts")} activeOpacity={0.7}>
          <Ionicons
            name={tab === "alerts" ? "notifications" : "notifications-outline"}
            size={22}
            color={tab === "alerts" ? colors.navActive : colors.navInactive}
            style={styles.navIconVector}
          />
          <View style={[styles.navIndicator, tab === "alerts" && styles.navIndicatorActive]} />
          <View style={styles.navLabelWrap}>
            <Text style={[styles.navText, tab === "alerts" && styles.navTextActive]}>Allarmi</Text>
            {unreadAlerts > 0 && <View style={styles.navBadge} />}
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navItem} onPress={() => setTab("profile")} activeOpacity={0.7}>
          <Ionicons
            name={tab === "profile" ? "person" : "person-outline"}
            size={22}
            color={tab === "profile" ? colors.navActive : colors.navInactive}
            style={styles.navIconVector}
          />
          <View style={[styles.navIndicator, tab === "profile" && styles.navIndicatorActive]} />
          <Text style={[styles.navText, tab === "profile" && styles.navTextActive]}>Profilo</Text>
        </TouchableOpacity>
      </View>

      {/* ===== Pagina: valori normali per fascia d'età ===== */}
      <Modal
        visible={infoOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setInfoOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Valori normali per età</Text>
            <Text style={styles.modalIntro}>
              Gli intervalli di frequenza cardiaca e respiratoria considerati normali cambiano
              con l'età del bambino. La fascia del paziente registrato è evidenziata.
            </Text>

            <View style={styles.bandHeadRow}>
              <Text style={[styles.bandHead, styles.bandHeadName]}>Fascia</Text>
              <Text style={[styles.bandHead, styles.bandHeadVal]}>FC (bpm)</Text>
              <Text style={[styles.bandHead, styles.bandHeadVal]}>FR (atti/min)</Text>
            </View>

            <ScrollView style={styles.modalScroll}>
              {AGE_BANDS_INFO.map((b) => {
                const active = b.band === ranges.band;
                return (
                  <View key={b.band} style={[styles.bandRow, active && styles.bandRowActive]}>
                    <Text style={styles.bandName}>{b.age}</Text>
                    <Text style={styles.bandVal}>{b.bpm}</Text>
                    <Text style={styles.bandVal}>{b.resp}</Text>
                  </View>
                );
              })}
              <Text style={styles.tempNote}>
                La temperatura cutanea non dipende dall'età: l'intervallo di riferimento è
                36,0–37,2 °C per tutte le fasce.
              </Text>
              <Text style={styles.guideDisclaimer}>
                Valori di riferimento indicativi: centili 1°–99° di Fleming et al.
                (Lancet, 2011). Non sostituiscono le soglie che il pediatra può
                indicare per il singolo bambino.
              </Text>
            </ScrollView>

            <TouchableOpacity style={styles.modalBtn} onPress={() => setInfoOpen(false)}>
              <Text style={styles.modalBtnText}>Ho capito</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ===== Pagina: guida di primo soccorso ===== */}
      {/*
        Le indicazioni di questa guida sono coerenti con fonti pediatriche
        autorevoli, consultate per la stesura dei contenuti:
          - Ospedale Pediatrico Bambino Gesù, "Segni di sofferenza respiratoria
            nei bambini" (segnali di allarme respiratori, cianosi):
            https://www.ospedalebambinogesu.it/segni-di-sofferenza-respiratoria-nei-bambini-89815/
          - Società Italiana di Pediatria (SIP), "Gestione dell'attacco acuto di
            asma in età pediatrica" (posizione seduta, broncodilatatore prescritto):
            https://www.area-pediatrica.it/archivio/2808/articoli/28396/
          - NICE NG143, "Fever in under 5s: assessment and initial management"
            (gestione della febbre):
            https://www.nice.org.uk/guidance/NG143
          - NHS, "High temperature (fever) in children" (indicazioni pratiche
            sulla febbre per i genitori):
            https://www.nhs.uk/symptoms/fever-in-children/
      */}
      <Modal
        visible={guideOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setGuideOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Cosa fare se scatta un allarme</Text>
            <Text style={styles.modalIntro}>
              Passi generali per i genitori. In caso di dubbio o di peggioramento, contatta
              subito il pediatra o il 112.
            </Text>

            <ScrollView style={styles.modalScroll}>
              <View style={styles.guideSection}>
                <Text style={styles.guideSectionTitle}>Per prima cosa</Text>
                {[
                  "Mantieni la calma e avvicinati al bambino.",
                  "Osserva respiro, colore della pelle (labbra/viso) e se risponde agli stimoli.",
                  "Controlla il sensore: se non è ben posizionato può dare un falso allarme. Riposizionalo e verifica se i valori rientrano.",
                ].map((s, i) => (
                  <View key={i} style={styles.guideStepRow}>
                    <Text style={styles.guideBullet}>{"\u2022"}</Text>
                    <Text style={styles.guideStep}>{s}</Text>
                  </View>
                ))}
              </View>

              <View style={styles.guideSection}>
                <Text style={styles.guideSectionTitle}>Respiro molto veloce o affannoso</Text>
                {[
                  "Metti il bambino seduto o semi-seduto e allenta i vestiti stretti.",
                  "Arieggia la stanza e cerca di tranquillizzarlo: il pianto accelera il respiro.",
                  "Se ha una terapia per l'asma prescritta, somministrala come indicato dal pediatra.",
                ].map((s, i) => (
                  <View key={i} style={styles.guideStepRow}>
                    <Text style={styles.guideBullet}>{"\u2022"}</Text>
                    <Text style={styles.guideStep}>{s}</Text>
                  </View>
                ))}
              </View>

              <View style={styles.guideSection}>
                <Text style={styles.guideSectionTitle}>Febbre / temperatura elevata</Text>
                {[
                  "Non coprire troppo il bambino; mantieni l'ambiente fresco.",
                  "Se è sveglio, offri liquidi a piccoli sorsi.",
                  "Per gli antipiretici segui dosi e modalità indicate dal pediatra.",
                ].map((s, i) => (
                  <View key={i} style={styles.guideStepRow}>
                    <Text style={styles.guideBullet}>{"\u2022"}</Text>
                    <Text style={styles.guideStep}>{s}</Text>
                  </View>
                ))}
              </View>

              <View style={styles.guideSection}>
                <Text style={styles.guideSectionTitle}>Frequenza cardiaca anomala</Text>
                {[
                  "Fai riposare il bambino: movimento e pianto alzano il battito.",
                  "Se il valore resta anomalo a riposo, o compaiono pallore, svenimento o dolore, contatta il medico.",
                ].map((s, i) => (
                  <View key={i} style={styles.guideStepRow}>
                    <Text style={styles.guideBullet}>{"\u2022"}</Text>
                    <Text style={styles.guideStep}>{s}</Text>
                  </View>
                ))}
              </View>

              <View style={styles.guideEmergency}>
                <Text style={styles.guideEmergencyTitle}>Chiama subito il 112 se</Text>
                <Text style={styles.guideEmergencyText}>
                  Il bambino fatica molto a respirare o smette di respirare, diventa bluastro o
                  molto pallido, è floscio o non si sveglia, oppure ha convulsioni.
                </Text>
              </View>

              <Text style={styles.guideDisclaimer}>
                Questa guida ha scopo informativo e non sostituisce il parere medico. In ogni
                situazione di dubbio contatta il pediatra o i servizi di emergenza.
              </Text>
            </ScrollView>

            <TouchableOpacity style={styles.modalBtn} onPress={() => setGuideOpen(false)}>
              <Text style={styles.modalBtnText}>Chiudi</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ===== Spiegazione della verifica in corso ===== */}
      <Modal
        visible={verifyOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setVerifyOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Verifica in corso</Text>
            <Text style={styles.modalIntro}>
              Un valore è momentaneamente fuori dall'intervallo normale per l'età. Prima di
              segnalare un allarme, l'app effettua una breve verifica.
            </Text>

            <View style={styles.guideSection}>
              <Text style={styles.guideSectionTitle}>Perché</Text>
              <View style={styles.guideStepRow}>
                <Text style={styles.guideBullet}>{"\u2022"}</Text>
                <Text style={styles.guideStep}>
                  Movimenti del bambino o un contatto imperfetto del sensore possono causare
                  letture anomale per pochi istanti.
                </Text>
              </View>
              <View style={styles.guideStepRow}>
                <Text style={styles.guideBullet}>{"\u2022"}</Text>
                <Text style={styles.guideStep}>
                  Attendere evita falsi allarmi e inutili preoccupazioni.
                </Text>
              </View>
            </View>

            <View style={styles.guideSection}>
              <Text style={styles.guideSectionTitle}>In cosa consiste</Text>
              <View style={styles.guideStepRow}>
                <Text style={styles.guideBullet}>{"\u2022"}</Text>
                <Text style={styles.guideStep}>
                  L'app controlla il valore per circa 20 secondi. Il monitoraggio continua
                  normalmente durante l'attesa.
                </Text>
              </View>
              <View style={styles.guideStepRow}>
                <Text style={styles.guideBullet}>{"\u2022"}</Text>
                <Text style={styles.guideStep}>
                  Se l'anomalia persiste per tutto questo tempo, viene segnalata come allarme;
                  se i valori rientrano prima, non compare alcun allarme.
                </Text>
              </View>
            </View>

            <TouchableOpacity style={styles.modalBtn} onPress={() => setVerifyOpen(false)}>
              <Text style={styles.modalBtnText}>Ho capito</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ===== Modifica profilo del bambino ===== */}
      <Modal
        visible={editOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setEditOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Modifica profilo</Text>
            <Text style={styles.modalIntro}>
              Aggiorna i dati del bambino, ad esempio quando cambia l'età.
            </Text>

            <ScrollView style={styles.modalScroll} keyboardShouldPersistTaps="handled">
              <Text style={styles.fieldLabel}>Nome del paziente</Text>
              <TextInput
                style={styles.input}
                placeholder="Nome del paziente"
                placeholderTextColor={colors.placeholder}
                value={editName}
                onChangeText={setEditName}
              />

              <Text style={styles.fieldLabel}>Età del bambino</Text>
              <View style={styles.stepperRow}>
                <Text style={styles.stepperLabel}>Anni</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity
                    style={[styles.stepBtn, editYears === 0 && styles.stepBtnDisabled]}
                    onPress={() => changeEditYears(-1)}
                    disabled={editYears === 0}
                  >
                    <Text style={styles.stepBtnText}>-</Text>
                  </TouchableOpacity>
                  <Text style={styles.stepValue}>{editYears}</Text>
                  <TouchableOpacity
                    style={[styles.stepBtn, editYears === 18 && styles.stepBtnDisabled]}
                    onPress={() => changeEditYears(1)}
                    disabled={editYears === 18}
                  >
                    <Text style={styles.stepBtnText}>+</Text>
                  </TouchableOpacity>
                </View>
              </View>
              <View style={styles.stepperRow}>
                <Text style={styles.stepperLabel}>Mesi</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity
                    style={[styles.stepBtn, editMonths === 0 && styles.stepBtnDisabled]}
                    onPress={() => changeEditMonths(-1)}
                    disabled={editMonths === 0}
                  >
                    <Text style={styles.stepBtnText}>-</Text>
                  </TouchableOpacity>
                  <Text style={styles.stepValue}>{editMonths}</Text>
                  <TouchableOpacity
                    style={[styles.stepBtn, editMonths === 11 && styles.stepBtnDisabled]}
                    onPress={() => changeEditMonths(1)}
                    disabled={editMonths === 11}
                  >
                    <Text style={styles.stepBtnText}>+</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <Text style={styles.fieldLabel}>Sesso</Text>
              <View style={styles.sexRow}>
                <TouchableOpacity
                  style={[styles.sexOption, editSex === "M" && styles.sexOptionActive]}
                  onPress={() => setEditSex("M")}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.sexOptionText, editSex === "M" && styles.sexOptionTextActive]}>
                    Maschio
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.sexOption, editSex === "F" && styles.sexOptionActive]}
                  onPress={() => setEditSex("F")}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.sexOptionText, editSex === "F" && styles.sexOptionTextActive]}>
                    Femmina
                  </Text>
                </TouchableOpacity>
              </View>
            </ScrollView>

            <View style={styles.modalBtnRow}>
              <TouchableOpacity style={styles.modalGhostBtn} onPress={() => setEditOpen(false)}>
                <Text style={styles.modalGhostText}>Annulla</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnHalf]}
                onPress={saveProfile}
              >
                <Text style={styles.modalBtnText}>Salva</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}