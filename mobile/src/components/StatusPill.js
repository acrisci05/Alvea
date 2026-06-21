// src/components/StatusPill.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, fonts, radius } from '../theme/tokens';

const PALETTES = {
  ok: { bg: colors.sageDim, text: colors.sageText },
  warning: { bg: colors.amberDim, text: colors.amberText },
  critical: { bg: colors.brickDim, text: colors.brickText },
};

export default function StatusPill({ level = 'ok', label }) {
  const palette = PALETTES[level] || PALETTES.ok;
  return (
    <View style={[styles.pill, { backgroundColor: palette.bg }]}>
      <Text style={[styles.text, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: radius.pill,
  },
  text: {
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: '600',
    letterSpacing: 0.4,
  },
});
