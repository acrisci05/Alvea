import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { WS_URL, DEVICE_ID } from "../config";
import { getLatest } from "../api";

// Schermata di monitoraggio live. Si connette al WebSocket del backend e
// aggiorna BPM/temperatura/stato fascia in tempo reale. Fallback: polling REST.
export default function MonitorScreen({ token }) {
  const [reading, setReading] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let ws;
    try {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === "reading" && m.device_id === DEVICE_ID) {
          setReading(m);
          if (m.alerts && m.alerts.length) {
            setAlerts((prev) => [...m.alerts, ...prev].slice(0, 20));
          }
        }
      };
    } catch (e) {
      // fallback polling
    }
    // Polling di sicurezza ogni 3s (se il WS non porta dati)
    const poll = setInterval(async () => {
      try {
        const r = await getLatest(token, DEVICE_ID);
        if (!connected) setReading({ ...r, type: "reading" });
      } catch {}
    }, 3000);
    return () => { if (ws) ws.close(); clearInterval(poll); };
  }, [token]);

  const contact = reading?.sensor_contact;
  const bpm = reading?.bpm ?? "--";
  const temp = reading?.temperature ?? "--";
  const bpmColor = !contact ? "#888" : bpm > 140 || (bpm > 0 && bpm < 100) ? "#E71D36" : "#5BC0BE";
  const tempColor = !contact ? "#888" : temp > 37.2 || (temp > 0 && temp < 36) ? "#E71D36" : "#5BC0BE";

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <Text style={styles.header}>PulseGuard·Baby</Text>
      <Text style={styles.status}>
        {connected ? "● live" : "○ in attesa dati"} — {DEVICE_ID}
      </Text>

      {!contact && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>⚠ Fascia non a contatto</Text>
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.label}>Battito cardiaco</Text>
        <Text style={[styles.big, { color: bpmColor }]}>{bpm} <Text style={styles.unit}>BPM</Text></Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Temperatura</Text>
        <Text style={[styles.big, { color: tempColor }]}>{temp} <Text style={styles.unit}>°C</Text></Text>
      </View>

      <Text style={styles.section}>Allarmi recenti</Text>
      {alerts.length === 0 ? (
        <Text style={styles.muted}>Nessun allarme.</Text>
      ) : (
        alerts.map((a, i) => (
          <View key={i} style={[styles.alert, a.severity === "critical" && styles.alertCrit]}>
            <Text style={styles.alertKind}>{a.severity.toUpperCase()}</Text>
            <Text style={styles.alertMsg}>{a.message}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B132B" },
  header: { color: "#fff", fontSize: 26, fontWeight: "800" },
  status: { color: "#9bb", marginBottom: 16 },
  banner: { backgroundColor: "#E71D36", padding: 12, borderRadius: 10, marginBottom: 14 },
  bannerText: { color: "#fff", fontWeight: "700", textAlign: "center" },
  card: { backgroundColor: "#1C2541", borderRadius: 16, padding: 22, marginBottom: 14 },
  label: { color: "#9bb", fontSize: 14 },
  big: { fontSize: 52, fontWeight: "800", marginTop: 4 },
  unit: { fontSize: 20, color: "#9bb" },
  section: { color: "#fff", fontSize: 18, fontWeight: "700", marginTop: 10, marginBottom: 8 },
  muted: { color: "#8da" },
  alert: { backgroundColor: "#1C2541", borderLeftWidth: 4, borderLeftColor: "#F9A826",
           padding: 12, borderRadius: 8, marginBottom: 8 },
  alertCrit: { borderLeftColor: "#E71D36" },
  alertKind: { color: "#F9A826", fontWeight: "700", fontSize: 12 },
  alertMsg: { color: "#fff", marginTop: 2 },
});
