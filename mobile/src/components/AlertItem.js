// src/components/AlertItem.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, fonts, severityPalette } from '../theme/tokens';

function formatTime(date) {
  if (!date) return '--:--:--';
  const d = date instanceof Date ? date : new Date(date);
  return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function AlertItem({ alert }) {
  const palette = severityPalette(alert.gravita);
  return (
    <View style={[styles.item, { borderLeftColor: palette.accent }]}>
      <View style={styles.main}>
        <Text style={styles.desc}>{alert.descrizione}</Text>
        <Text style={styles.meta}>
          {alert.parametro} · {formatTime(alert.t)}
        </Text>
      </View>
      <View style={[styles.tag, { backgroundColor: palette.bg }]}>
        <Text style={[styles.tagText, { color: palette.text }]}>{alert.gravita}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  item: {
    backgroundColor: colors.navySoft,
    borderWidth: 1,
    borderColor: colors.line,
    borderLeftWidth: 3,
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 8,
  },
  main: { flex: 1 },
  desc: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.ivory,
    marginBottom: 3,
  },
  meta: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textDim,
  },
  tag: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  tagText: {
    fontFamily: fonts.mono,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
});
