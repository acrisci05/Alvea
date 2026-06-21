// src/screens/MedicoPatientDetailScreen.js
import React, { useState } from 'react';
import { View, Text, ScrollView, Pressable, TextInput, StyleSheet } from 'react-native';
import { useTelemetry } from '../context/TelemetryContext';
import VitalCard from '../components/VitalCard';
import StatusPill from '../components/StatusPill';
import VitalsChart from '../components/VitalsChart';
import AlertItem from '../components/AlertItem';
import { colors, fonts, radius, cardShadow } from '../theme/tokens';
import { THRESHOLDS } from '../config';

const TABS = [
  { key: 'overview', label: 'Stato paziente' },
  { key: 'alerts', label: 'Allerte' },
  { key: 'config', label: 'Configurazione' },
  { key: 'anamnesi', label: 'Anamnesi' },
];

export default function MedicoPatientDetailScreen({ route }) {
  const { deviceKey } = route.params;
  const { devices, deriveStatusInfo, updateDeviceConfig } = useTelemetry();
  const device = devices[deviceKey];
  const [activeTab, setActiveTab] = useState('overview');

  const [periodInput, setPeriodInput] = useState(String(device?.publishPeriod || 1));
  const [patientIdInput, setPatientIdInput] = useState(device?.patientId || '');
  const [log, setLog] = useState([]);

  if (!device) return null;

  const statusInfo = deriveStatusInfo(device);

  async function handleSendCommand() {
    const period = Math.max(1, parseInt(periodInput, 10) || 1);
    await updateDeviceConfig(deviceKey, { publishPeriodS: period, patientId: patientIdInput || null });
    const time = new Date().toLocaleTimeString('it-IT');
    setLog((prev) => [
      `[${time}] PUBLISH ${device.deviceId}/commands → {"publish_period_s": ${period}, "patient_id": "${patientIdInput || ''}"}`,
      ...prev,
    ].slice(0, 10));
  }

  return (
    <View style={styles.screen}>
      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <Pressable key={tab.key} onPress={() => setActiveTab(tab.key)} style={styles.tabBtn}>
            <Text style={[styles.tabLabel, activeTab === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
            {activeTab === tab.key && <View style={styles.tabIndicator} />}
          </Pressable>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {activeTab === 'overview' && (
          <Overview device={device} statusInfo={statusInfo} />
        )}

        {activeTab === 'alerts' && (
          <View>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Allerte — {device.name}</Text>
              <View style={styles.countBadge}><Text style={styles.countText}>{device.alerts.length}</Text></View>
            </View>
            {device.alerts.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyText}>Nessuna allerta registrata per questo paziente.</Text>
              </View>
            ) : (
              device.alerts.map((a, idx) => <AlertItem key={idx} alert={a} />)
            )}
          </View>
        )}

        {activeTab === 'config' && (
          <ConfigPanel
            device={device}
            periodInput={periodInput}
            setPeriodInput={setPeriodInput}
            patientIdInput={patientIdInput}
            setPatientIdInput={setPatientIdInput}
            onSend={handleSendCommand}
            log={log}
          />
        )}

        {activeTab === 'anamnesi' && <Anamnesi device={device} />}
      </ScrollView>
    </View>
  );
}

function Overview({ device, statusInfo }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View>
          <Text style={styles.patientName}>{device.name}</Text>
          <Text style={styles.deviceId}>device_id: {device.deviceId} · patient_id: {device.patientId}</Text>
        </View>
        <StatusPill level={statusInfo.level} label={statusInfo.label} />
      </View>

      <View style={styles.vitalsGrid}>
        <VitalCard label="Frequenza respiratoria" value={device.state.fr} unit="atti/min" thresholds={THRESHOLDS.fr} rangeNote={`soglia attiva: ${THRESHOLDS.fr.warnLow}–${THRESHOLDS.fr.warnHigh}`} contact={device.state.contact} />
        <VitalCard label="Frequenza cardiaca" value={device.state.bpm} unit="bpm" thresholds={THRESHOLDS.bpm} rangeNote={`soglia attiva: ${THRESHOLDS.bpm.warnLow}–${THRESHOLDS.bpm.warnHigh}`} contact={device.state.contact} />
        <VitalCard label="SpO₂" value={device.state.spo2} unit="%" thresholds={{ warnLow: THRESHOLDS.spo2Min, warnHigh: 1000, critLow: -1, critHigh: 1000 }} rangeNote={`soglia: <${THRESHOLDS.spo2Min}%`} contact={device.state.contact} />
        <VitalCard label="Temperatura cutanea" value={device.state.temp} unit="°C" thresholds={THRESHOLDS.temp} rangeNote={`soglia: ${THRESHOLDS.temp.warnLow}–${THRESHOLDS.temp.warnHigh}`} contact={device.state.contact} />
      </View>

      <VitalsChart history={device.history} />
    </View>
  );
}

function ConfigPanel({ device, periodInput, setPeriodInput, patientIdInput, setPatientIdInput, onSend, log }) {
  return (
    <View style={styles.card}>
      <Text style={styles.configIntro}>
        Configurazione remota inviata via topic MQTT alvea/devices/{device.deviceId}/commands,
        secondo quanto effettivamente implementato in main_real_mqtt.py: frequenza di pubblicazione
        e associazione paziente–dispositivo.
      </Text>

      <Text style={styles.fieldLabel}>Frequenza di pubblicazione (s)</Text>
      <TextInput
        style={styles.input}
        value={periodInput}
        onChangeText={setPeriodInput}
        keyboardType="numeric"
      />
      <Text style={styles.fieldNote}>Corrisponde al campo publish_period_s del comando. Default firmware: 1s.</Text>

      <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Associazione patient_id</Text>
      <TextInput
        style={styles.input}
        value={patientIdInput}
        onChangeText={setPatientIdInput}
      />
      <Text style={styles.fieldNote}>Se vuoto, il device riporta WARN_PATIENT_NOT_ASSIGNED.</Text>

      <Pressable style={styles.submitBtn} onPress={onSend}>
        <Text style={styles.submitText}>Invia configurazione al device</Text>
      </Pressable>

      <View style={styles.logBox}>
        {log.length === 0 ? (
          <Text style={styles.logLine}>// log comandi MQTT (topic commands) — simulato localmente</Text>
        ) : (
          log.map((line, idx) => <Text key={idx} style={styles.logLine}>{line}</Text>)
        )}
      </View>
    </View>
  );
}

function Anamnesi({ device }) {
  const rows = [
    ['Paziente', device.name],
    ['Classificazione asma', device.profile.asma],
    ['Allergie', device.profile.allergie],
    ['Terapia in corso', device.profile.terapia],
    ['Medico responsabile', device.profile.medico],
    ['Note cliniche', device.profile.note],
    ['Device associato', `${device.deviceId} (patient_id: ${device.patientId})`],
  ];
  return (
    <View style={styles.card}>
      <Text style={styles.configIntro}>
        Modulo progettato nella Relazione Tecnica (Sez. 4.2): scheda anamnestica che accoppia
        device_id e profilo clinico del bambino. Dati dimostrativi.
      </Text>
      {rows.map(([label, value]) => (
        <View key={label} style={styles.anamnesiRow}>
          <Text style={styles.anamnesiLabel}>{label}</Text>
          <Text style={styles.anamnesiValue}>{value}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy },
  tabBar: {
    flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: colors.line,
    paddingHorizontal: 10,
  },
  tabBtn: { paddingVertical: 12, paddingHorizontal: 10, alignItems: 'center' },
  tabLabel: { fontFamily: fonts.bodySemibold, fontSize: 12.5, color: colors.textDim },
  tabLabelActive: { color: colors.ivory },
  tabIndicator: { height: 2, backgroundColor: colors.dust, marginTop: 6, width: '100%', borderRadius: 1 },
  content: { padding: 18, paddingBottom: 40 },
  card: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 18, ...cardShadow,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, marginBottom: 16 },
  patientName: { fontFamily: fonts.display, fontSize: 18, color: colors.ivory, fontWeight: '600' },
  deviceId: { fontFamily: fonts.mono, fontSize: 11.5, color: colors.textDim, marginTop: 3 },
  vitalsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  sectionTitle: { fontFamily: fonts.display, fontSize: 17, color: colors.ivory, fontWeight: '600' },
  countBadge: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: 999, paddingHorizontal: 9, paddingVertical: 2,
  },
  countText: { fontFamily: fonts.mono, fontSize: 11, color: colors.textDim },
  empty: {
    borderWidth: 1, borderColor: colors.line, borderStyle: 'dashed',
    borderRadius: 10, padding: 24, alignItems: 'center',
  },
  emptyText: { color: colors.textDim, fontSize: 13, textAlign: 'center' },
  configIntro: { fontSize: 12.5, color: colors.textDim, lineHeight: 18, marginBottom: 16 },
  fieldLabel: {
    fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5,
    color: colors.textDim, fontFamily: fonts.bodySemibold, marginBottom: 7,
  },
  input: {
    backgroundColor: colors.navy, borderWidth: 1, borderColor: colors.line,
    borderRadius: 9, color: colors.ivory, fontFamily: fonts.mono,
    fontSize: 13, paddingHorizontal: 13, paddingVertical: 10,
  },
  fieldNote: { fontSize: 10.5, color: colors.textDim, marginTop: 6, lineHeight: 15 },
  submitBtn: {
    backgroundColor: colors.ivory, borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', marginTop: 18,
  },
  submitText: { color: colors.navy, fontFamily: fonts.bodySemibold, fontSize: 13.5, fontWeight: '700' },
  logBox: {
    marginTop: 14, backgroundColor: colors.navy, borderWidth: 1, borderColor: colors.line,
    borderRadius: 8, padding: 10, maxHeight: 110,
  },
  logLine: { fontFamily: fonts.mono, fontSize: 10.5, color: colors.textDim, marginBottom: 4 },
  anamnesiRow: { paddingVertical: 9, borderBottomWidth: 1, borderBottomColor: colors.line },
  anamnesiLabel: { fontSize: 10.5, color: colors.textDim, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 3 },
  anamnesiValue: { fontSize: 13, color: colors.ivory, fontFamily: fonts.body, lineHeight: 18 },
});
