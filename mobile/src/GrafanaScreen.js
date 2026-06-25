import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, Linking } from "react-native";
import { WebView } from "react-native-webview";
import { SafeAreaView } from "react-native-safe-area-context";
import { GRAFANA_URL } from "./config";
import styles from "./style";

// Schermata "Dashboard Grafana" per il medico (Punto 6 dei requisiti
// funzionali generali): mostra la dashboard Grafana del paziente
// direttamente dentro l'app tramite WebView, così il medico non deve
// uscire da Alvea per consultare grafici storici, stato del paziente e
// alert. Resta una schermata separata da MonitorScreen (che mostra invece
// i dati "live" e gli ultimi alert): MonitorScreen è il pannello rapido,
// questa è l'approfondimento storico/grafico — coerente con la
// separazione vista nei requisiti tra "Punto 3 - App mobile" (dati
// real-time, storico, notifiche) e "Punto 6 - Dashboard Grafana" (grafici
// storici dettagliati, vista clinica completa).
//
// Nota: GRAFANA_URL punta al server Grafana del progetto (vedi config.js).
// Grafana deve essere raggiungibile in rete dal telefono (stessa LAN o
// reverse proxy) e la dashboard può usare la modalità "kiosk" per
// nascondere i menu di amministrazione, mostrando solo i pannelli.
export default function GrafanaScreen({ onBack }) {
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  function openInBrowser() {
    Linking.openURL(GRAFANA_URL).catch(() =>
      console.warn("Impossibile apire Grafana nel browser esterno")
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.monitorHeader}>
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={onBack} activeOpacity={0.7} style={styles.logoutBtn}>
            <Text style={styles.logoutText}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.header}>Dashboard</Text>
          {/* Spaziatore per centrare visivamente il titolo rispetto alla
              freccia indietro a sinistra */}
          <View style={{ width: 32 }} />
        </View>
        <Text style={styles.status}>Grafici storici e stato clinico — Grafana</Text>
      </View>

      {hasError ? (
        <View style={[styles.card, { alignItems: "center" }]}>
          <Text style={styles.label}>Dashboard non raggiungibile</Text>
          <Text style={[styles.muted, { paddingHorizontal: 0, marginTop: 8, textAlign: "center" }]}>
            Verifica che il server Grafana sia attivo e raggiungibile in
            rete, oppure provala nel browser.
          </Text>
          <TouchableOpacity style={[styles.btn, { marginTop: 16, alignSelf: "stretch" }]} onPress={() => { setHasError(false); setLoading(true); }}>
            <Text style={styles.btnText}>Riprova</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkBtn} onPress={openInBrowser}>
            <Text style={styles.link}>Apri nel browser</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={{ flex: 1 }}>
          {loading && (
            <View
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1,
              }}
            >
              <ActivityIndicator size="large" color="#3A506B" />
              <Text style={[styles.muted, { marginTop: 12 }]}>Caricamento dashboard…</Text>
            </View>
          )}
          <WebView
            source={{ uri: GRAFANA_URL }}
            style={{ flex: 1, backgroundColor: "transparent" }}
            onLoadEnd={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setHasError(true);
            }}
            onHttpError={() => {
              setLoading(false);
              setHasError(true);
            }}
            startInLoadingState={false}
            // La dashboard Grafana gestisce i propri filtri (paziente,
            // parametro, intervallo) tramite le variabili di template
            // della dashboard stessa: lasciamo che lo zoom/scroll nativo
            // della pagina web funzioni normalmente.
            javaScriptEnabled
            domStorageEnabled
          />
        </View>
      )}
    </SafeAreaView>
  );
}
