import React, { useState, useEffect, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl, Text, TouchableOpacity } from 'react-native';
import { COLORS, SIZES, FONTS } from '../constants/theme';
import { CATEGORIES } from '../constants/categories';

import NewsCard from '../components/NewsCard';
import CategoryFilter from '../components/CategoryFilter';
import SentimentBadge from '../components/SentimentBadge';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import DatePickerModal from '../components/DatePickerModal';
import NewsDetailModal from '../components/NewsDetailModal';

import { 
  fetchNews, 
  fetchHistoricalNews, 
  fetchSentimentSummary, 
  fetchAvailableDates 
} from '../api/newsService';

const HomeScreen = () => {
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  // States
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // History mode 
  const [isHistoryMode, setIsHistoryMode] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [dateModalVisible, setDateModalVisible] = useState(false);

  // Detail modal
  const [selectedItem, setSelectedItem] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const handleCardPress = (item) => {
    setSelectedItem(item);
    setDetailVisible(true);
  };

  const loadData = useCallback(async () => {
    try {
      setError(null);
      // Fetch sentiment summary only for live mode for now, or keep existing if history doesn't have it
      if (!isHistoryMode) {
        const sentimentData = await fetchSentimentSummary();
        setSentiment(sentimentData);
      }
      
      let newsData;
      if (isHistoryMode && selectedDate) {
        const payload = await fetchHistoricalNews(selectedDate);
        newsData = payload.news || [];
      } else {
        const payload = await fetchNews();
        newsData = payload.news || [];
      }
      
      setNews(newsData);
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [isHistoryMode, selectedDate]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleOpenDatePicker = async () => {
    try {
      const datesPayload = await fetchAvailableDates();
      setAvailableDates(datesPayload.dates || []);
      setDateModalVisible(true);
    } catch (err) {
      console.error('Failed to load history dates', err);
    }
  };

  const resetToLive = () => {
    setIsHistoryMode(false);
    setSelectedDate(null);
  };

  // Filter logic
  const filteredNews = React.useMemo(() => {
    if (selectedCategory === 'All') return news;
    return news.filter(item => 
      item.category?.toLowerCase() === selectedCategory.toLowerCase()
    );
  }, [news, selectedCategory]);

  if (loading) {
    return (
      <View style={styles.container}>
        <LoadingState />
      </View>
    );
  }

  if (error && !refreshing) {
    return (
      <View style={styles.container}>
        <ErrorState message={error} onRetry={loadData} />
      </View>
    );
  }

  const renderHeader = () => (
    <View style={styles.headerSection}>
      {!isHistoryMode && sentiment && (
        <SentimentBadge data={sentiment} />
      )}
      
      <View style={styles.historyBar}>
        {isHistoryMode ? (
          <View style={styles.historyActiveBar}>
            <Text style={styles.historyText}>ARCHIVES: {selectedDate}</Text>
            <TouchableOpacity onPress={resetToLive} style={styles.liveButton}>
              <Text style={styles.liveButtonText}>BACK TO LIVE</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableOpacity onPress={handleOpenDatePicker} style={styles.archiveButton}>
            <Text style={styles.archiveButtonText}>BROWSE ARCHIVES</Text>
          </TouchableOpacity>
        )}
      </View>
      
      <CategoryFilter 
        categories={CATEGORIES}
        selectedCategory={selectedCategory}
        onSelect={setSelectedCategory}
      />
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={filteredNews}
        keyExtractor={(item, index) => item.id || `news-${index}`}
        renderItem={({ item }) => <NewsCard item={item} onPress={() => handleCardPress(item)} />}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No news found for this category.</Text>
          </View>
        }
        refreshControl={
          <RefreshControl 
            refreshing={refreshing} 
            onRefresh={handleRefresh} 
            tintColor={COLORS.primary}
          />
        }
        contentContainerStyle={{ paddingBottom: SIZES.xxl }}
      />
      
      <DatePickerModal
        visible={dateModalVisible}
        dates={availableDates}
        onClose={() => setDateModalVisible(false)}
        onSelectDate={(date) => {
          setIsHistoryMode(true);
          setSelectedDate(date);
          setDateModalVisible(false);
        }}
      />

      <NewsDetailModal
        visible={detailVisible}
        item={selectedItem}
        onClose={() => setDetailVisible(false)}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  headerSection: {
    paddingTop: SIZES.md,
    paddingBottom: SIZES.sm,
  },
  historyBar: {
    paddingHorizontal: SIZES.md,
    marginVertical: SIZES.xs,
  },
  archiveButton: {
    padding: SIZES.sm,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
  },
  archiveButtonText: {
    color: COLORS.primary,
    fontFamily: FONTS.mono,
    fontSize: SIZES.sm,
  },
  historyActiveBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255,51,102,0.1)',
    padding: SIZES.sm,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.danger,
  },
  historyText: {
    color: COLORS.danger,
    fontFamily: FONTS.mono,
    fontSize: SIZES.sm,
  },
  liveButton: {
    backgroundColor: COLORS.danger,
    paddingHorizontal: SIZES.sm,
    paddingVertical: 4,
    borderRadius: 4,
  },
  liveButtonText: {
    color: '#fff',
    fontFamily: FONTS.bold,
    fontSize: SIZES.xs,
  },
  emptyContainer: {
    padding: SIZES.xl,
    alignItems: 'center',
  },
  emptyText: {
    color: COLORS.textMuted,
    fontFamily: FONTS.regular,
  },
});

export default HomeScreen;
