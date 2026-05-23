export const COLORS = {
  background: '#0d1117',
  cardBackground: '#161b22',
  text: '#c9d1d9',
  textMuted: '#8b949e',
  primary: '#00ff88',
  primaryDark: '#00cc6a',
  secondary: '#ff3366',
  border: '#30363d',
  accent: '#58a6ff',
  danger: '#ff3366',
  success: '#2ea043',
  warning: '#e3b341',
  neutral: '#6e7681',
};

export const SIZES = {
  xs: 10,
  sm: 12,
  md: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
};

export const FONTS = {
  regular: 'System', // We use basic System for clean look without installing extra fonts in Phase 1
  bold: 'System',
  mono: 'Menlo',
};

export const SHADOWS = {
  cyber: {
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 10,
    elevation: 5,
  },
};
