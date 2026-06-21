// src/screens/MedicoPatientListScreen.js
import React from 'react';
import { View, Text, FlatList, Pressable, StyleSheet } from 'react-native';
import { useTelemetry } from '../context/TelemetryContext';
import { colors, fonts, radius, severityPalette, cardShadow } from '../theme/tokens';

export default function MedicoPatientListScreen({ navigation }) {
  const { deviceList, deriveStatusInfo } = useTelemetry();

  return (
    <View style={styles.screen}>
      <View style={styles.connRow}>
        <View style={styles.dot} />
        <Text style={styles.connText}>
          Backend FastAPI · profilo Medico Pneumologo/Pediatra · query storiche pre-filtrate
        </Text>
      </View>

      <View style={styles.header}>
        <Text style={styles.title}>Pazienti assegnati</Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{deviceList.length}</Text>
        </View>
      </View>

      <FlatList
        data={deviceList}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        renderItem={({ item }) => {
          const statusInfo = deriveStatusInfo(item);
          const palette = severityPalette(statusInfo.level === 'ok' ? 'INFO' : statusInfo.level.toUpperCase());
          return (
            <Pressable
              style={styles.card}
              onPress={() => navigation.navigate('MedicoPatientDetail', { deviceKey: item.id })}
            >
              <View style={[styles.badge, { backgroundColor: palette.accent }]} />
              <View style={styles.cardTop}>
                <View>
                  <Text style={styles.name}>{item.name}</Text>
                  <Text style={styles.sub}>{item.deviceId} · patient_id {item.patientId}</Text>
                </View>
              </View>
              <View style={styles.miniVitals}>
                <MiniVital label="FR" value={item.state.contact ? item.state.fr.toFixed(0) : '—'} />
                <MiniVital label="BPM" value={item.state.contact ? item.state.bpm.toFixed(0) : '—'} />
                <MiniVital label="SpO₂" value={item.state.contact ? item.state.spo2.toFixed(0) : '—'} />
              </View>
            </Pressable>
          );
        }}
      />
    </View>
  );
}

function MiniVital({ label, value }) {
  return (
    <View style={styles.miniVitalItem}>
      <Text style={styles.miniLabel}>{label}</Text>
      <Text style={styles.miniValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy, padding: 18 },
  connRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 16 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.sage },
  connText: { fontFamily: fonts.mono, fontSize: 10.5, color: colors.textDim, flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  title: { fontFamily: fonts.display, fontSize: 19, color: colors.ivory, fontWeight: '600' },
  countBadge: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: 999, paddingHorizontal: 9, paddingVertical: 2,
  },
  countText: { fontFamily: fonts.mono, fontSize: 11, color: colors.textDim },
  card: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 16, marginBottom: 12, position: 'relative', ...cardShadow,
  },
  badge: { position: 'absolute', top: 14, right: 14, width: 9, height: 9, borderRadius: 5 },
  cardTop: { marginBottom: 10 },
  name: { fontFamily: fonts.display, fontSize: 16.5, color: colors.ivory, fontWeight: '600' },
  sub: { fontFamily: fonts.mono, fontSize: 11, color: colors.textDim, marginTop: 2 },
  miniVitals: { flexDirection: 'row', gap: 18 },
  miniVitalItem: {},
  miniLabel: { fontSize: 10.5, color: colors.textDim },
  miniValue: { fontFamily: fonts.mono, fontSize: 14, color: colors.ivory, marginTop: 2 },
});
