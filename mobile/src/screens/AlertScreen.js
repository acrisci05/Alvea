// src/screens/AlertsScreen.js
import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useTelemetry } from '../context/TelemetryContext';
import AlertItem from '../components/AlertItem';
import { colors, fonts } from '../theme/tokens';

export default function AlertsScreen() {
  const { caregiverDevice } = useTelemetry();
  if (!caregiverDevice) return null;

  // Il caregiver visualizza WARNING/CRITICAL; gli INFO di risoluzione sono
  // filtrati per chiarezza (restano comunque visibili nello storico medico).
  const visibleAlerts = caregiverDevice.alerts.filter((a) => a.gravita !== 'INFO');

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>Notifiche di allerta</Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{visibleAlerts.length}</Text>
        </View>
      </View>

      <FlatList
        data={visibleAlerts}
        keyExtractor={(item, idx) => `${item.parametro}-${idx}-${item.t?.getTime?.() || idx}`}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => <AlertItem alert={item} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>Nessuna allerta attiva. Monitoraggio silenzioso in corso.</Text>
          </View>
        }
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
  listContent: { paddingBottom: 40 },
  empty: {
    borderWidth: 1, borderColor: colors.line, borderStyle: 'dashed',
    borderRadius: 10, padding: 24, alignItems: 'center', marginTop: 8,
  },
  emptyText: { color: colors.textDim, fontSize: 13, textAlign: 'center' },
});
