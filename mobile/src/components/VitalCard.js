// src/components/VitalCard.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, fonts } from '../theme/tokens';
import { classify } from '../services/simulator';

const LEVEL_COLOR = {
  ok: colors.sageText,
  warning: colors.amberText,
  critical: colors.brickText,
};

export default function VitalCard({ label, value, unit, thresholds, rangeNote, contact = true }) {
  const level = contact && value !== null && value !== undefined
    ? classify(value, thresholds)
    : null;
  const valueColor = level ? LEVEL_COLOR[level] : colors.ivory;
  const displayValue = contact && value !== null && value !== undefined
    ? (Number.isInteger(value) ? value : value.toFixed(1))
    : '—';

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.valueRow}>
        <Text style={[styles.value, { color: valueColor }]}>{displayValue}</Text>
        <Text style={styles.unit}>{unit}</Text>
      </View>
      {rangeNote ? <Text style={styles.range}>{rangeNote}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: '47%',
    backgroundColor: colors.navy,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
  },
  label: {
    fontSize: 10.5,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    color: colors.textDim,
    fontFamily: fonts.bodySemibold,
    marginBottom: 8,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
  },
  value: {
    fontSize: 28,
    fontFamily: fonts.display,
    fontWeight: '600',
  },
  unit: {
    fontSize: 12,
    color: colors.textDim,
    fontFamily: fonts.body,
  },
  range: {
    fontSize: 9.5,
    color: colors.textDim,
    fontFamily: fonts.mono,
    marginTop: 6,
  },
});
