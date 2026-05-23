import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { COLORS, FONTS, SIZES } from '../constants/theme';

const ErrorState = ({ message = "Connection Error", onRetry }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>⚠️</Text>
      <Text style={styles.title}>SYSTEM FAILURE</Text>
      <Text style={styles.message}>{message}</Text>
      
      {onRetry && (
        <TouchableOpacity style={styles.button} onPress={onRetry} activeOpacity={0.8}>
          <Text style={styles.buttonText}>REBOOT CONNECTION</Text>
        </TouchableOpacity>
      )}
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
  icon: {
    fontSize: 48,
    marginBottom: SIZES.md,
  },
  title: {
    color: COLORS.danger,
    fontFamily: FONTS.bold,
    fontSize: SIZES.lg,
    marginBottom: SIZES.sm,
    letterSpacing: 1,
  },
  message: {
    color: COLORS.textMuted,
    textAlign: 'center',
    marginBottom: SIZES.xl,
  },
  button: {
    backgroundColor: 'rgba(255, 51, 102, 0.1)',
    borderColor: COLORS.danger,
    borderWidth: 1,
    paddingHorizontal: SIZES.lg,
    paddingVertical: SIZES.md,
    borderRadius: 4,
  },
  buttonText: {
    color: COLORS.danger,
    fontFamily: FONTS.mono,
    fontSize: SIZES.sm,
    letterSpacing: 1,
  },
});

export default ErrorState;
