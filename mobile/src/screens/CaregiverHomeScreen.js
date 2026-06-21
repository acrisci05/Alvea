// src/screens/CaregiverHomeScreen.js
import React from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable } from 'react-native';
import { useTelemetry } from '../context/TelemetryContext';
import { useAuth } from '../context/AuthContext';
import VitalCard from '../components/VitalCard';
import StatusPill from '../components/StatusPill';
import VitalsChart from '../components/VitalsChart';
import { colors, fonts, radius, cardShadow } from '../theme/tokens';
import { THRESHOLDS, AGE_BANDS } from '../config';

export default function CaregiverHomeScreen() {
  const { caregiverDevice, deriveStatusInfo } = useTelemetry();
  const { session } = useAuth();

  if (!caregiverDevice) return null;

  const device = caregiverDevice;
  const statusInfo = deriveStatusInfo(device);
  const band = AGE_BANDS[device.ageBand] || AGE_BANDS.prescolare;
  const lastReading = device.history[0];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.connRow}>
        <View style={styles.dot} />
        <Text style={styles.connText}>
          Connesso · canale realtime (simulato) · pubblicazione ogni {device.publishPeriod}s
        </Text>
      </View>

      <View style={styles.card}>
        <View style={styles.cardTop}>
          <View>
            <Text style={styles.patientName}>{device.name}</Text>
            <Text style={styles.deviceId}>
              device_id: {device.deviceId} · patient_id: {device.patientId}
            </Text>
            <Text style={styles.ageBandLine}>
              Fascia d'età: {band.label} ({band.rangeLabel}) · range nominale FR {band.frNominal} · BPM {band.bpmNominal}
            </Text>
          </View>
          <StatusPill level={statusInfo.level} label={statusInfo.label} />
        </View>

        <View style={styles.vitalsGrid}>
          <VitalCard
            label="Frequenza respiratoria"
            value={device.state.fr}
            unit="atti/min"
            thresholds={THRESHOLDS.fr}
            rangeNote={`soglia: ${THRESHOLDS.fr.warnLow}–${THRESHOLDS.fr.warnHigh} · critico ≤${THRESHOLDS.fr.critLow} / ≥${THRESHOLDS.fr.critHigh}`}
            contact={device.state.contact}
          />
          <VitalCard
            label="Frequenza cardiaca"
            value={device.state.bpm}
            unit="bpm"
            thresholds={THRESHOLDS.bpm}
            rangeNote={`soglia: ${THRESHOLDS.bpm.warnLow}–${THRESHOLDS.bpm.warnHigh} · critico ≤${THRESHOLDS.bpm.critLow} / ≥${THRESHOLDS.bpm.critHigh}`}
            contact={device.state.contact}
          />
          <VitalCard
            label="SpO₂"
            value={device.state.spo2}
            unit="%"
            thresholds={{ warnLow: THRESHOLDS.spo2Min, warnHigh: 1000, critLow: -1, critHigh: 1000 }}
            rangeNote={`soglia di allerta clinica: <${THRESHOLDS.spo2Min}%`}
            contact={device.state.contact}
          />
          <VitalCard
            label="Temperatura cutanea"
            value={device.state.temp}
            unit="°C"
            thresholds={THRESHOLDS.temp}
            rangeNote={`soglia: ${THRESHOLDS.temp.warnLow}–${THRESHOLDS.temp.warnHigh} · critico ≤${THRESHOLDS.temp.critLow} / ≥${THRESHOLDS.temp.critHigh}`}
            contact={device.state.contact}
          />
        </View>

        <VitalsChart history={device.history} />

        <View style={styles.footerRow}>
          <Text style={styles.footerItem}>🔋 batteria: <Text style={styles.footerMono}>{device.state.battery.toFixed(0)}%</Text></Text>
          <Text style={styles.footerItem}>contatto: <Text style={styles.footerMono}>{device.state.contact ? 'OK' : 'ASSENTE'}</Text></Text>
          <Text style={styles.footerItem}>
            aggiornato: <Text style={styles.footerMono}>
              {lastReading ? lastReading.t.toLocaleTimeString('it-IT') : '--:--:--'}
            </Text>
          </Text>
        </View>
      </View>

      <Text style={styles.disclaimer}>
        Prototipo didattico (Academy Medical Wearable Devices 2025/2026). Non è un dispositivo
        medico certificato: soglie e classificazioni hanno finalità esclusivamente accademiche.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy },
  content: { padding: 18, paddingBottom: 40 },
  connRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 14 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.sage },
  connText: { fontFamily: fonts.mono, fontSize: 11, color: colors.textDim, flex: 1 },
  card: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 18, ...cardShadow,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, marginBottom: 16 },
  patientName: { fontFamily: fonts.display, fontSize: 19, color: colors.ivory, fontWeight: '600' },
  deviceId: { fontFamily: fonts.mono, fontSize: 11.5, color: colors.textDim, marginTop: 3 },
  ageBandLine: { fontFamily: fonts.mono, fontSize: 10.5, color: colors.textDim, marginTop: 3, maxWidth: 230 },
  vitalsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  footerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginTop: 14 },
  footerItem: { fontSize: 12, color: colors.textDim, fontFamily: fonts.body },
  footerMono: { fontFamily: fonts.mono, color: colors.ivory },
  disclaimer: {
    fontSize: 11, color: colors.textDim, marginTop: 20, lineHeight: 16,
    borderLeftWidth: 2, borderLeftColor: colors.amber, paddingLeft: 10,
  },
});
