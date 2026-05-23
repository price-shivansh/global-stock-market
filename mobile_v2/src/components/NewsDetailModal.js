import React from 'react';
import {
  Modal,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Linking,
  StatusBar,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../constants/theme';

// ── Helpers ──────────────────────────────────────────────────────────────────

const sentimentColor = (s) => {
  const v = (s || '').toLowerCase();
  if (v === 'bullish') return COLORS.primary;
  if (v === 'bearish') return COLORS.danger;
  return COLORS.neutral;
};

const sentimentEmoji = (s) => {
  const v = (s || '').toLowerCase();
  if (v === 'bullish') return '🟢';
  if (v === 'bearish') return '🔴';
  return '⚪';
};

const relevanceColor = (r) => {
  if (r === 'HIGH') return COLORS.danger;
  if (r === 'MEDIUM') return COLORS.warning;
  return COLORS.neutral;
};

const relevanceEmoji = (r) => {
  if (r === 'HIGH') return '🚨';
  if (r === 'MEDIUM') return '📌';
  return '📎';
};

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString([], {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
};

// ── Sub-components ────────────────────────────────────────────────────────────

const MetaRow = ({ label, value, valueStyle }) => (
  <View style={metaStyles.row}>
    <Text style={metaStyles.label}>{label}</Text>
    <Text style={[metaStyles.value, valueStyle]} numberOfLines={2}>{value || '—'}</Text>
  </View>
);

const metaStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(48,54,61,0.5)',
  },
  label: {
    color: COLORS.textMuted,
    fontSize: SIZES.sm,
    fontFamily: FONTS.mono,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    flex: 0.38,
  },
  value: {
    color: COLORS.text,
    fontSize: SIZES.sm,
    fontFamily: FONTS.regular,
    flex: 0.6,
    textAlign: 'right',
  },
});

// ── Main component ────────────────────────────────────────────────────────────

const NewsDetailModal = ({ visible, item, onClose }) => {
  if (!item) return null;

  const sColor = sentimentColor(item.sentiment);
  const rColor = relevanceColor(item.relevance);

  const handleReadMore = async () => {
    if (item.url) {
      try {
        await Linking.openURL(item.url);
      } catch (err) {
        console.error("Could not open URL:", err);
      }
    }
  };

  const scoreStr = item.sentiment_score !== undefined
    ? `${item.sentiment_score >= 0 ? '+' : ''}${Number(item.sentiment_score).toFixed(2)}`
    : null;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <StatusBar backgroundColor="rgba(0,0,0,0.7)" />

      {/* Backdrop */}
      <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={onClose} />

      {/* Sheet */}
      <View style={styles.sheet}>
        {/* Handle bar */}
        <View style={styles.handle} />

        {/* Header row */}
        <View style={styles.sheetHeader}>
          <View style={styles.sourceRow}>
            <Text style={styles.sourceLabel}>{item.source || 'News'}</Text>
            {item.relevance && (
              <View style={[styles.relevancePill, { borderColor: rColor }]}>
                <Text style={[styles.relevanceText, { color: rColor }]}>
                  {relevanceEmoji(item.relevance)} {item.relevance}
                </Text>
              </View>
            )}
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
            <Text style={styles.closeBtnText}>✕</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >

          {/* Headline */}
          <Text style={styles.headline}>{item.title}</Text>

          {/* Sentiment banner */}
          <View style={[styles.sentimentBanner, { borderColor: sColor }]}>
            <Text style={[styles.sentimentBannerText, { color: sColor }]}>
              {sentimentEmoji(item.sentiment)}  {(item.sentiment || 'NEUTRAL').toUpperCase()}
              {scoreStr ? `  ·  ${scoreStr}` : ''}
            </Text>
          </View>

          {/* Summary block */}
          {item.summary ? (
            <View style={styles.summaryBlock}>
              <Text style={styles.summaryLabel}>SUMMARY</Text>
              <Text style={styles.summaryText}>{item.summary}</Text>
            </View>
          ) : null}

          {/* Meta grid */}
          <View style={styles.metaBlock}>
            <MetaRow label="Category" value={item.category} />
            <MetaRow
              label="Asset"
              value={item.related_symbol || (item.all_symbols?.join(', ')) || '—'}
              valueStyle={{ color: COLORS.accent }}
            />
            <MetaRow label="Source" value={item.source} />
            <MetaRow
              label="Published"
              value={formatDate(item.published_at)}
              valueStyle={{ color: COLORS.textMuted }}
            />
          </View>

          {/* Divider */}
          <View style={styles.divider} />

          {/* Read full article button */}
          {item.url ? (
            <TouchableOpacity style={styles.readBtn} onPress={handleReadMore} activeOpacity={0.85}>
              <Text style={styles.readBtnText}>Read Full Article  →</Text>
            </TouchableOpacity>
          ) : (
            <View style={[styles.readBtn, { opacity: 0.3 }]}>
              <Text style={styles.readBtnText}>No Source URL Available</Text>
            </View>
          )}

          <View style={{ height: 32 }} />
        </ScrollView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.65)',
  },
  sheet: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    backgroundColor: COLORS.cardBackground,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderTopWidth: 1,
    borderColor: COLORS.border,
    maxHeight: '88%',
    // Cyber glow
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.18,
    shadowRadius: 16,
    elevation: 24,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: COLORS.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: 12,
    marginBottom: 4,
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: SIZES.md,
    paddingVertical: SIZES.sm,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  sourceLabel: {
    color: COLORS.accent,
    fontFamily: FONTS.bold,
    fontSize: SIZES.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  relevancePill: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  relevanceText: {
    fontSize: SIZES.xs,
    fontFamily: FONTS.mono,
    textTransform: 'uppercase',
  },
  closeBtn: {
    padding: 4,
  },
  closeBtnText: {
    color: COLORS.textMuted,
    fontSize: SIZES.md,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: SIZES.md,
    paddingTop: SIZES.md,
  },
  headline: {
    color: COLORS.text,
    fontFamily: FONTS.bold,
    fontSize: SIZES.md + 3,
    lineHeight: 26,
    marginBottom: SIZES.md,
  },
  sentimentBanner: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: SIZES.md,
    paddingVertical: 10,
    marginBottom: SIZES.md,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  sentimentBannerText: {
    fontFamily: FONTS.bold,
    fontSize: SIZES.sm + 1,
    letterSpacing: 0.5,
  },
  summaryBlock: {
    backgroundColor: 'rgba(0,255,136,0.04)',
    borderLeftWidth: 3,
    borderLeftColor: COLORS.primary,
    borderRadius: 4,
    padding: SIZES.md,
    marginBottom: SIZES.md,
  },
  summaryLabel: {
    color: COLORS.primary,
    fontFamily: FONTS.mono,
    fontSize: SIZES.xs,
    letterSpacing: 1,
    marginBottom: 6,
  },
  summaryText: {
    color: COLORS.text,
    fontSize: SIZES.sm + 1,
    lineHeight: 20,
    fontFamily: FONTS.regular,
  },
  metaBlock: {
    marginBottom: SIZES.md,
  },
  divider: {
    height: 1,
    backgroundColor: COLORS.border,
    marginVertical: SIZES.md,
  },
  readBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    ...SHADOWS.cyber,
  },
  readBtnText: {
    color: '#0d1117',
    fontFamily: FONTS.bold,
    fontSize: SIZES.md,
    letterSpacing: 0.5,
  },
});

export default NewsDetailModal;
