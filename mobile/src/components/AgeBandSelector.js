// src/components/AgeBandSelector.js
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, fonts, radius } from '../theme/tokens';
import { AGE_BANDS } from '../config';

export default function AgeBandSelector({ value, onChange }) {
  return (
    <View style={styles.row}>
      {Object.values(AGE_BANDS).map((band) => {
        const selected = value === band.key;
        return (
          <Pressable
            key={band.key}
            onPress={() => onChange(band.key)}
            style={[styles.option, selected && styles.optionSelected]}
          >
            <Text style={styles.title}>{band.label}</Text>
            <Text style={[styles.sub, selected && styles.subSelected]}>
              {band.rangeLabel}{'\n'}FR {band.frNominal} · BPM {band.bpmNominal}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  option: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.navy,
    borderRadius: radius.sm,
    padding: 12,
  },
  optionSelected: {
    borderColor: colors.sage,
    backgroundColor: colors.sageDim,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 14.5,
    color: colors.ivory,
    fontWeight: '600',
    marginBottom: 3,
  },
  sub: {
    fontFamily: fonts.mono,
    fontSize: 10.5,
    color: colors.textDim,
    lineHeight: 15,
  },
  subSelected: {
    color: 'rgba(31,110,92,0.85)',
  },
});
