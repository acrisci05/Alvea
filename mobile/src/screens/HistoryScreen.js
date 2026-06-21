// src/screens/HistoryScreen.js
import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useTelemetry } from '../context/TelemetryContext';
import { colors, fonts } from '../theme/tokens';

function formatTime(date) {
  return date ? date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--';
}

export default function HistoryScreen() {
  const { caregiverDevice } = useTelemetry();
  if (!caregiverDevice) return null;

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>Storico letture</Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{caregiverDevice.history.length}</Text>
        </View>
      </View>

      <View style={styles.tableHead}>
        <Text style={[styles.th, styles.colTime]}>ora</Text>
        <Text style={[styles.th, styles.colVal]}>FR</Text>
        <Text style={[styles.th, styles.colVal]}>BPM</Text>
        <Text style={[styles.th, styles.colVal]}>SpO₂</Text>
        <Text style={[styles.th, styles.colVal]}>temp.</Text>
        <Text style={[styles.th, styles.colStatus]}>stato</Text>
      </View>

      <FlatList
        data={caregiverDevice.history}
        keyExtractor={(item, idx) => `${idx}-${item.t?.getTime?.() || idx}`}
        contentContainerStyle={{ paddingBottom: 40 }}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={[styles.td, styles.colTime]}>{formatTime(item.t)}</Text>
            <Text style={[styles.td, styles.colVal]}>{item.fr ? item.fr.toFixed(0) : '—'}</Text>
            <Text style={[styles.td, styles.colVal]}>{item.bpm ? item.bpm.toFixed(0) : '—'}</Text>
            <Text style={[styles.td, styles.colVal]}>{item.spo2 ? item.spo2.toFixed(0) : '—'}</Text>
            <Text style={[styles.td, styles.colVal]}>{item.temp ? item.temp.toFixed(1) : '—'}</Text>
            <Text style={[styles.td, styles.colStatus]} numberOfLines={1}>{item.status}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy, padding: 18 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 14 },
  title: { fontFamily: fonts.display, fontSize: 19, color: colors.ivory, fontWeight: '600' },
  countBadge: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: 999, paddingHorizontal: 9, paddingVertical: 2,
  },
  countText: { fontFamily: fonts.mono, fontSize: 11, color: colors.textDim },
  tableHead: {
    flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: colors.line, paddingBottom: 8, marginBottom: 4,
  },
  th: {
    fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.4,
    color: colors.textDim, fontFamily: fonts.bodySemibold,
  },
  row: {
    flexDirection: 'row', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  td: { fontFamily: fonts.mono, fontSize: 12, color: 'rgba(26,36,51,0.82)' },
  colTime: { width: 78 },
  colVal: { width: 50 },
  colStatus: { flex: 1 },
});
