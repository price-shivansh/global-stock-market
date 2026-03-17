"""
Technical Analysis Module
Calculates various technical indicators and generates signals
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from models import TechnicalIndicators, Signal, SignalType
from config import settings
from datetime import datetime

class TechnicalAnalyzer:
    def __init__(self):
        self.rsi_period = settings.RSI_PERIOD
        self.rsi_overbought = settings.RSI_OVERBOUGHT
        self.rsi_oversold = settings.RSI_OVERSOLD
        self.macd_fast = settings.MACD_FAST
        self.macd_slow = settings.MACD_SLOW
        self.macd_signal = settings.MACD_SIGNAL
        self.bb_period = settings.BB_PERIOD
        self.bb_std = settings.BB_STD
    
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index"""
        if period is None:
            period = self.rsi_period
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd - signal
        
        return macd, signal, histogram
    
    def calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=self.bb_period).mean()
        std = prices.rolling(window=self.bb_period).std()
        
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        
        return upper, middle, lower
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On-Balance Volume"""
        obv = [0]
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i-1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=close.index)
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate all technical indicators for a dataframe"""
        if len(df) < 50:  # Need minimum data points
            return TechnicalIndicators()
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # RSI
        rsi = self.calculate_rsi(close)
        
        # MACD
        macd, macd_signal, macd_hist = self.calculate_macd(close)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(close)
        
        # Moving Averages
        sma_20 = self.calculate_sma(close, 20)
        sma_50 = self.calculate_sma(close, 50)
        ema_12 = self.calculate_ema(close, 12)
        ema_26 = self.calculate_ema(close, 26)
        
        # ATR
        atr = self.calculate_atr(high, low, close)
        
        # OBV
        obv = self.calculate_obv(close, volume)
        
        # Volume SMA
        volume_sma = self.calculate_sma(volume, 20)
        
        return TechnicalIndicators(
            rsi=round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else None,
            macd=round(macd.iloc[-1], 4) if not pd.isna(macd.iloc[-1]) else None,
            macd_signal=round(macd_signal.iloc[-1], 4) if not pd.isna(macd_signal.iloc[-1]) else None,
            macd_histogram=round(macd_hist.iloc[-1], 4) if not pd.isna(macd_hist.iloc[-1]) else None,
            sma_20=round(sma_20.iloc[-1], 2) if not pd.isna(sma_20.iloc[-1]) else None,
            sma_50=round(sma_50.iloc[-1], 2) if not pd.isna(sma_50.iloc[-1]) else None,
            ema_12=round(ema_12.iloc[-1], 2) if not pd.isna(ema_12.iloc[-1]) else None,
            ema_26=round(ema_26.iloc[-1], 2) if not pd.isna(ema_26.iloc[-1]) else None,
            bb_upper=round(bb_upper.iloc[-1], 2) if not pd.isna(bb_upper.iloc[-1]) else None,
            bb_middle=round(bb_middle.iloc[-1], 2) if not pd.isna(bb_middle.iloc[-1]) else None,
            bb_lower=round(bb_lower.iloc[-1], 2) if not pd.isna(bb_lower.iloc[-1]) else None,
            atr=round(atr.iloc[-1], 2) if not pd.isna(atr.iloc[-1]) else None,
            obv=round(obv.iloc[-1], 0) if not pd.isna(obv.iloc[-1]) else None,
            volume_sma=round(volume_sma.iloc[-1], 0) if not pd.isna(volume_sma.iloc[-1]) else None
        )
    
    def generate_technical_signal(self, indicators: TechnicalIndicators, current_price: float) -> Tuple[float, List[str]]:
        """
        Generate technical signal score from -100 to 100
        Positive = Bullish, Negative = Bearish
        Returns (score, list of reasons)
        """
        score = 0
        reasons = []
        
        if indicators.rsi is not None:
            if indicators.rsi < self.rsi_oversold:
                score += 20
                reasons.append(f"RSI oversold ({indicators.rsi:.1f})")
            elif indicators.rsi > self.rsi_overbought:
                score -= 20
                reasons.append(f"RSI overbought ({indicators.rsi:.1f})")
            elif indicators.rsi < 45:
                score += 10
                reasons.append(f"RSI bullish zone ({indicators.rsi:.1f})")
            elif indicators.rsi > 55:
                score -= 10
                reasons.append(f"RSI bearish zone ({indicators.rsi:.1f})")
        
        if indicators.macd is not None and indicators.macd_signal is not None:
            if indicators.macd > indicators.macd_signal:
                score += 15
                reasons.append("MACD bullish crossover")
            else:
                score -= 15
                reasons.append("MACD bearish crossover")
            
            if indicators.macd_histogram is not None:
                if indicators.macd_histogram > 0 and indicators.macd_histogram > 0:
                    score += 5
                    reasons.append("MACD histogram positive")
                elif indicators.macd_histogram < 0:
                    score -= 5
                    reasons.append("MACD histogram negative")
        
        if indicators.sma_20 is not None and indicators.sma_50 is not None:
            if indicators.sma_20 > indicators.sma_50:
                score += 15
                reasons.append("Short-term SMA above long-term (Golden Cross trend)")
            else:
                score -= 15
                reasons.append("Short-term SMA below long-term (Death Cross trend)")
        
        if indicators.bb_upper is not None and indicators.bb_lower is not None:
            if current_price < indicators.bb_lower:
                score += 15
                reasons.append("Price below lower Bollinger Band (oversold)")
            elif current_price > indicators.bb_upper:
                score -= 15
                reasons.append("Price above upper Bollinger Band (overbought)")
        
        if indicators.ema_12 is not None and indicators.ema_26 is not None:
            if indicators.ema_12 > indicators.ema_26:
                score += 10
                reasons.append("EMA 12 above EMA 26 (bullish)")
            else:
                score -= 10
                reasons.append("EMA 12 below EMA 26 (bearish)")
        
        if indicators.obv is not None and indicators.volume_sma is not None:
            # Volume confirmation - simplified check
            pass
        
        # Clamp score between -100 and 100
        score = max(-100, min(100, score))
        
        return score, reasons
    
    def get_signal_type(self, combined_score: float) -> SignalType:
        """Convert combined score to signal type"""
        if combined_score >= 60:
            return SignalType.STRONG_BUY
        elif combined_score >= 25:
            return SignalType.BUY
        elif combined_score <= -60:
            return SignalType.STRONG_SELL
        elif combined_score <= -25:
            return SignalType.SELL
        else:
            return SignalType.HOLD


# Global analyzer instance
technical_analyzer = TechnicalAnalyzer()
