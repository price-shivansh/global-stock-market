import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../constants/theme';

const SentimentBadge = ({ data }) => {
  if (!data) return null;

  const { overall_sentiment, score, bullish_percent, bearish_percent, neutral_percent } = data;

  let mainColor = COLORS.neutral;
  if (overall_sentiment?.toLowerCase().includes('bullish') || score > 0.1) {
    mainColor = COLORS.primary;
  } else if (overall_sentiment?.toLowerCase().includes('bearish') || score < -0.1) {
    mainColor = COLORS.danger;
  } else {
    mainColor = COLORS.accent;
  }

  return (
    <View style={[styles.container, { borderColor: mainColor }]}>
      <Text style={[styles.title, { color: mainColor }]}>
        MARKET MOOD: {overall_sentiment ? overall_sentiment.toUpperCase() : 'UNKNOWN'}
      </Text>
      
      <View style={styles.barContainer}>
        <View style={[styles.barSegment, { backgroundColor: COLORS.primary, flex: bullish_percent || 0 }]} />
        <View style={[styles.barSegment, { backgroundColor: COLORS.neutral, flex: neutral_percent || 0 }]} />
        <View style={[styles.barSegment, { backgroundColor: COLORS.danger, flex: bearish_percent || 0 }]} />
      </View>
      
      <View style={styles.labelRow}>
        <Text style={styles.label}>BULL {bullish_percent}%</Text>
        <Text style={styles.label}>NEUTRAL {neutral_percent}%</Text>
        <Text style={styles.label}>BEAR {bearish_percent}%</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: SIZES.md,
    padding: SIZES.md,
    borderRadius: 8,
    backgroundColor: COLORS.cardBackground,
    borderWidth: 1,
    ...SHADOWS.cyber,
  },
  title: {
    fontFamily: FONTS.bold,
    fontSize: SIZES.sm,
    textAlign: 'center',
    marginBottom: SIZES.md,
    letterSpacing: 1,
  },
  barContainer: {
    flexDirection: 'row',
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: SIZES.sm,
    backgroundColor: COLORS.border,
  },
  barSegment: {
    height: '100%',
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    color: COLORS.textMuted,
    fontSize: SIZES.xs,
    fontFamily: FONTS.mono,
  },
});

export default SentimentBadge;
