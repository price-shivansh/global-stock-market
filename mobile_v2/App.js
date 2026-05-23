import React from 'react';
import { SafeAreaView, StatusBar, StyleSheet, Text, View } from 'react-native';
import HomeScreen from './src/screens/HomeScreen';
import { COLORS, FONTS, SIZES } from './src/constants/theme';

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.background} />
      
      {/* Top Banner / Header */}
      <View style={styles.appHeader}>
        <Text style={styles.appTitle}>QUANT TERMINAL<Text style={styles.version}> v2</Text></Text>
      </View>

      <HomeScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  appHeader: {
    paddingTop: 16,
    paddingBottom: 16,
    paddingHorizontal: SIZES.md,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
    backgroundColor: COLORS.cardBackground,
  },
  appTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
    fontFamily: FONTS.mono,
  },
  version: {
    color: COLORS.primary,
    fontSize: 14,
  },
});
