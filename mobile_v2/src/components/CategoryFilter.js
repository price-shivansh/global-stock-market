import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { COLORS, SIZES, FONTS } from '../constants/theme';

const CategoryFilter = ({ categories, selectedCategory, onSelect }) => {
  return (
    <View style={styles.container}>
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {categories.map((cat, idx) => {
          const isSelected = selectedCategory === cat;
          return (
            <TouchableOpacity 
              key={idx} 
              style={[styles.pill, isSelected && styles.pillSelected]}
              onPress={() => onSelect(cat)}
              activeOpacity={0.7}
            >
              <Text style={[styles.text, isSelected && styles.textSelected]}>
                {cat}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: SIZES.sm,
  },
  scrollContent: {
    paddingHorizontal: SIZES.md,
    gap: 10,
  },
  pill: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: COLORS.cardBackground,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  pillSelected: {
    backgroundColor: 'rgba(0, 204, 106, 0.1)', // Muted primary for background
    borderColor: COLORS.primary,
  },
  text: {
    color: COLORS.textMuted,
    fontFamily: FONTS.regular,
    fontSize: SIZES.sm,
  },
  textSelected: {
    color: COLORS.primary,
    fontFamily: FONTS.bold,
  },
});

export default CategoryFilter;
