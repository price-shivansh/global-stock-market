import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { COLORS, SHADOWS, SIZES, FONTS } from '../constants/theme';

const NewsCard = ({ item, onPress }) => {
  // item shape (from /api/mobile/news and /api/mobile/news/history):
  // { id, title, source, published_at, category, sentiment, sentiment_score,
  //   relevance, related_symbol, all_symbols, priority, url, summary }

  let sentimentColor = COLORS.textMuted;
  if (item.sentiment?.toLowerCase() === 'bullish') {
    sentimentColor = COLORS.primary;
  } else if (item.sentiment?.toLowerCase() === 'bearish') {
    sentimentColor = COLORS.danger;
  }



  const formattedDate = item.published_at 
    ? new Date(item.published_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
    : '';

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.header}>
        <Text style={styles.source}>{item.source || 'News'}</Text>
        <Text style={styles.date}>{formattedDate}</Text>
      </View>
      
      <Text style={styles.title} numberOfLines={3}>{item.title}</Text>
      
      <View style={styles.footer}>
        <View style={styles.pillContainer}>
          {item.category && (
            <View style={styles.categoryPill}>
              <Text style={styles.categoryText}>{item.category}</Text>
            </View>
          )}
          {item.related_symbol && item.related_symbol !== "N/A" && (
            <View style={[styles.categoryPill, { borderColor: COLORS.accent }]}>
              <Text style={[styles.categoryText, { color: COLORS.accent }]}>{item.related_symbol}</Text>
            </View>
          )}
        </View>

        {item.sentiment && item.sentiment !== 'Unknown' && (
          <Text style={[styles.sentiment, { color: sentimentColor }]}>
            {item.sentiment.toUpperCase()}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.cardBackground,
    borderRadius: 12,
    padding: SIZES.md,
    marginVertical: 8,
    marginHorizontal: SIZES.md,
    borderWidth: 1,
    borderColor: COLORS.border,
    ...SHADOWS.cyber,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.xs,
  },
  source: {
    fontFamily: FONTS.bold,
    color: COLORS.accent,
    fontSize: SIZES.sm,
    textTransform: 'uppercase',
  },
  date: {
    color: COLORS.textMuted,
    fontSize: SIZES.sm - 2,
  },
  title: {
    fontFamily: FONTS.bold,
    fontSize: SIZES.md + 2,
    color: COLORS.text,
    lineHeight: 22,
    marginBottom: SIZES.md,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pillContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  categoryPill: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  categoryText: {
    color: COLORS.textMuted,
    fontSize: SIZES.sm - 2,
    textTransform: 'uppercase',
  },
  sentiment: {
    fontFamily: FONTS.bold,
    fontSize: SIZES.sm,
  },
});

export default NewsCard;
