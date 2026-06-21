// src/components/VitalsChart.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Rect } from 'react-native-svg';
import { colors, fonts } from '../theme/tokens';
import { THRESHOLDS } from '../config';

const W = 600;
const H = 140;
const FR_RANGE = [0, 50];
const BPM_RANGE = [40, 170];

function yFor(value, range) {
  return H - ((value - range[0]) / (range[1] - range[0])) * H;
}

function pathFor(values, range) {
  if (values.length < 2) return '';
  const stepX = W / (values.length - 1);
  return values
    .map((v, i) => {
      const x = i * stepX;
      const y = Math.max(2, Math.min(H - 2, yFor(v, range)));
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

export default function VitalsChart({ history }) {
  const data = history.slice(0, 60).slice().reverse();
  const frVals = data.map((d) => d.fr || 0);
  const bpmVals = data.map((d) => d.bpm || 0);

  const critHighY = yFor(THRESHOLDS.fr.critHigh, FR_RANGE);
  const warnHighY = yFor(THRESHOLDS.fr.warnHigh, FR_RANGE);
  const warnLowY = yFor(THRESHOLDS.fr.warnLow, FR_RANGE);
  const critLowY = yFor(THRESHOLDS.fr.critLow, FR_RANGE);

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={styles.title}>Andamento ultimi 60s</Text>
        <View style={styles.legend}>
          <LegendDot color={colors.dust} label="FR (atti/min)" />
          <LegendDot color={colors.pink} label="BPM" />
        </View>
      </View>

      {data.length >= 2 ? (
        <Svg width="100%" height={140} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          <Rect x={0} y={critHighY} width={W} height={Math.max(0, warnHighY - critHighY)} fill={colors.brick} opacity={0.08} />
          <Rect x={0} y={warnHighY} width={W} height={Math.max(0, warnLowY - warnHighY)} fill={colors.sage} opacity={0.06} />
          <Rect x={0} y={warnLowY} width={W} height={Math.max(0, critLowY - warnLowY)} fill={colors.amber} opacity={0.08} />
          <Rect x={0} y={critLowY} width={W} height={Math.max(0, H - critLowY)} fill={colors.brick} opacity={0.08} />
          <Path d={pathFor(bpmVals, BPM_RANGE)} fill="none" stroke={colors.pink} strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
          <Path d={pathFor(frVals, FR_RANGE)} fill="none" stroke={colors.dust} strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round" />
        </Svg>
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Raccolta dati in corso…</Text>
        </View>
      )}
    </View>
  );
}

function LegendDot({ color, label }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 18,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.navy,
    padding: 14,
  },
  head: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
    flexWrap: 'wrap',
    gap: 6,
  },
  title: {
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: colors.textDim,
    fontFamily: fonts.bodySemibold,
  },
  legend: {
    flexDirection: 'row',
    gap: 12,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 2,
  },
  legendText: {
    fontSize: 10.5,
    color: colors.textDim,
    fontFamily: fonts.mono,
  },
  placeholder: {
    height: 140,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    color: colors.textDim,
    fontFamily: fonts.mono,
    fontSize: 12,
  },
});
