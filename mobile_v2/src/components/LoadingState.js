import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { COLORS, FONTS, SIZES } from '../constants/theme';

const LoadingState = ({ message = "LOADING DATA..." }) => {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={COLORS.primary} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SIZES.xl,
  },
  text: {
    marginTop: SIZES.md,
    color: COLORS.primary,
    fontFamily: FONTS.mono,
    fontSize: SIZES.sm,
    letterSpacing: 2,
  },
});

export default LoadingState;
