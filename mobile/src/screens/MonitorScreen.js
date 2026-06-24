import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { WS_URL, DEVICE_ID } from "../config";
import { getLatest, registerPushToken } from "../api";
import { registerForPushNotificationsAsync, presentLocalAlert } from "../notifications";

const MAX_HISTORY = 30;
const GREEN = "#5BC0BE", AMBER = "#F9A826", RED = "#E71D36", GREY = "#888";

// Mini-grafico a barre senza librerie esterne: andamento di un parametro.
function Sparkline({ data, color }) {
  if (!data || data.length < 2) {
    return <Text style={styles.sparkMuted}>Raccolta dati in corso…</Text>;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  return (
    <View style={styles.spark}>
      {data.map((v, i) => {
        const h = 6 + Math.round(((v - min) / range) * 46);
        return <View key={i} style={[styles.sparkBar, { height: h, backgroundColor: color }]} />;
      })}
    </View>
  );
}

function Metric({ label, value, unit, color }) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.big, { color }]}>
        {value}
        <Text style={styles.unit}> {unit}</Text>
      </Text>
    </View>
  );
}

// Schermata di monitoraggio live (asma pediatrico). Parametri: respiro (EDR da
// ECG), battito (ECG), temperatura cutanea (NTC). WebSocket + fallback REST;
// notifica locale all'arrivo di un allarme.
export default function MonitorScreen({ token, onLogout }) {
  const [reading, setReading] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [respHistory, setRespHistory] = useState([]);
  const [connected, setConnected] = useState(false);
  const connectedRef = useRef(false);
  const lastNotifRef = useRef({});

  useEffect(() => {
    (async () => {
      const expoToken = await registerForPushNotificationsAsync();
      if (expoToken) registerPushToken(token, expoToken);
    })();
  }, [token]);

  function maybeNotify(a) {
    if (!a || a.severity === "technical") return;
    const now = Date.now();
    const prev = lastNotifRef.current[a.kind] || 0;
    if (now - prev < 30000) return; // anti-spam: 1 notifica/tipo ogni 30s
    lastNotifRef.current[a.kind] = now;
    presentLocalAlert(`Alvea — ${String(a.severity).toUpperCase()}`, a.message);
  }

  function pushReading(m) {
    setReading(m);
    if (typeof m.respiration_rate === "number" && m.respiration_rate > 0) {
      setRespHistory((prev) => [...prev, m.respiration_rate].slice(-MAX_HISTORY));
    }
    if (m.alerts && m.alerts.length) {
      setAlerts((prev) => [...m.alerts, ...prev].slice(0, 20));
      m.alerts.forEach(maybeNotify);
    }
  }

  useEffect(() => {
    let ws;
    try {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => { connectedRef.current = true; setConnected(true); };
      ws.onclose = () => { connectedRef.current = false; setConnected(false); };
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === "reading" && m.device_id === DEVICE_ID) pushReading(m);
      };
    } catch (e) {}
    const poll = setInterval(async () => {
      if (connectedRef.current) return;
      try { pushReading({ ...(await getLatest(token, DEVICE_ID)), type: "reading" }); } catch {}
    }, 3000);
    return () => { if (ws) ws.close(); clearInterval(poll); };
  }, [token]);

  const ok = reading && reading.sensor_contact && (reading.device_status ?? "SYSTEM_OK") === "SYSTEM_OK";
  const v = (x) => (typeof x === "number" ? x : "--");
  const resp = reading?.respiration_rate, bpm = reading?.bpm, skin = reading?.skin_temperature;

  const respColor = !ok ? GREY : resp >= 40 ? RED : resp > 30 ? AMBER : GREEN;
  const bpmColor = !ok ? GREY : bpm >= 160 || (bpm > 0 && bpm <= 50) ? RED : bpm > 120 || (bpm > 0 && bpm < 60) ? AMBER : GREEN;
  const tempColor = !ok ? GREY : skin >= 38 ? RED : skin > 35 ? AMBER : GREEN;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <View style={styles.topbar}>
        <Text style={styles.header}>Alvea</Text>
        <TouchableOpacity onPress={onLogout} hitSlop={10}>
          <Text style={styles.logout}>Esci</Text>
        </TouchableOpacity>
      </View>
      <Text style={styles.status}>
        {connected ? "● live" : "○ in attesa dati"} — {DEVICE_ID}
      </Text>

      {reading && !ok && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>
            ⚠ Sensore non a contatto{reading.device_status && reading.device_status !== "SYSTEM_OK" ? ` (${reading.device_status})` : ""}
          </Text>
        </View>
      )}

      <View style={styles.grid}>
        <Metric label="Respiro" value={v(resp)} unit="att/min" color={respColor} />
        <Metric label="Battito" value={v(bpm)} unit="BPM" color={bpmColor} />
        <Metric label="Temp. cutanea" value={v(skin)} unit="°C" color={tempColor} />
      </View>

      <View style={[styles.card, styles.cardWide]}>
        <Text style={styles.label}>Andamento respiro</Text>
        <Sparkline data={respHistory} color={respColor === GREY ? GREEN : respColor} />
      </View>

      <Text style={styles.section}>Allarmi recenti</Text>
      {alerts.length === 0 ? (
        <Text style={styles.muted}>Nessun allarme.</Text>
      ) : (
        alerts.map((a, i) => (
          <View key={i} style={[styles.alert, a.severity === "critical" && styles.alertCrit]}>
            <Text style={styles.alertKind}>
              {(a.parameter ? a.parameter.toUpperCase() + " · " : "") + String(a.severity).toUpperCase()}
            </Text>
            <Text style={styles.alertMsg}>{a.message}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B132B" },
  topbar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  header: { color: "#fff", fontSize: 26, fontWeight: "800" },
  logout: { color: "#5BC0BE", fontWeight: "700" },
  status: { color: "#9bb", marginBottom: 16 },
  banner: { backgroundColor: "#E71D36", padding: 12, borderRadius: 10, marginBottom: 14 },
  bannerText: { color: "#fff", fontWeight: "700", textAlign: "center" },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" },
  card: { backgroundColor: "#1C2541", borderRadius: 16, padding: 18, marginBottom: 12, width: "48%" },
  cardWide: { width: "100%" },
  label: { color: "#9bb", fontSize: 13 },
  big: { fontSize: 34, fontWeight: "800", marginTop: 6 },
  unit: { fontSize: 13, color: "#9bb", fontWeight: "600" },
  spark: { flexDirection: "row", alignItems: "flex-end", height: 56, marginTop: 12, gap: 2 },
  sparkBar: { flex: 1, borderRadius: 2, opacity: 0.85 },
  sparkMuted: { color: "#6b8", marginTop: 12, fontSize: 12 },
  section: { color: "#fff", fontSize: 18, fontWeight: "700", marginTop: 10, marginBottom: 8 },
  muted: { color: "#8da" },
  alert: { backgroundColor: "#1C2541", borderLeftWidth: 4, borderLeftColor: "#F9A826",
           padding: 12, borderRadius: 8, marginBottom: 8 },
  alertCrit: { borderLeftColor: "#E71D36" },
  alertKind: { color: "#F9A826", fontWeight: "700", fontSize: 12 },
  alertMsg: { color: "#fff", marginTop: 2 },
});
