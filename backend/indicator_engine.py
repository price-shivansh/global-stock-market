"""
indicator_engine.py — Series-level Technical Indicator Engine
Wraps TechnicalAnalyzer to return full Pandas Series (not just last value),
which strategy_engine needs to generate signal arrays over historic data.
"""
import pandas as pd
import numpy as np
from technical_analysis import TechnicalAnalyzer


class IndicatorEngine:
    """
    Thin façade over TechnicalAnalyzer that returns a full-length
    Series instead of the scalar snapshot used by the live signal system.
    """

    def __init__(self) -> None:
        self._ta = TechnicalAnalyzer()

    # ── RSI ─────────────────────────────────────────────────────────────────

    def rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        return self._ta.calculate_rsi(close, period)

    # ── MACD ────────────────────────────────────────────────────────────────

    def macd(self, close: pd.Series):
        """Returns (macd_line, signal_line, histogram)."""
        return self._ta.calculate_macd(close)

    # ── Bollinger Bands ──────────────────────────────────────────────────────

    def bollinger(self, close: pd.Series):
        """Returns (upper, middle, lower)."""
        return self._ta.calculate_bollinger_bands(close)

    # ── Moving Averages ──────────────────────────────────────────────────────

    def sma(self, close: pd.Series, period: int) -> pd.Series:
        return self._ta.calculate_sma(close, period)

    def ema(self, close: pd.Series, period: int) -> pd.Series:
        return self._ta.calculate_ema(close, period)

    def generate_technical_summary(self, df: pd.DataFrame) -> dict:
        close = df['Close']
        
        # Calculate indicators
        rsi_series = self.rsi(close, 14)
        macd_line, signal_line, _ = self.macd(close)
        sma_10 = self.sma(close, 10)
        sma_20 = self.sma(close, 20)
        sma_30 = self.sma(close, 30)
        sma_50 = self.sma(close, 50)
        ema_10 = self.ema(close, 10)
        ema_20 = self.ema(close, 20)
        ema_30 = self.ema(close, 30)
        momentum = close - close.shift(10)
        bb_upper, bb_middle, bb_lower = self.bollinger(close)
        
        # Get latest values
        current_price = close.iloc[-1]
        
        def safe_get(series):
            return series.iloc[-1] if not series.empty and not pd.isna(series.iloc[-1]) else None
            
        rsi_val = safe_get(rsi_series)
        macd_val = safe_get(macd_line)
        macd_sig = safe_get(signal_line)
        sma10_val = safe_get(sma_10)
        sma20_val = safe_get(sma_20)
        sma30_val = safe_get(sma_30)
        sma50_val = safe_get(sma_50)
        ema10_val = safe_get(ema_10)
        ema20_val = safe_get(ema_20)
        ema30_val = safe_get(ema_30)
        mom_val = safe_get(momentum)
        bb_up_val = safe_get(bb_upper)
        bb_low_val = safe_get(bb_lower)
        
        total_buy = 0
        total_sell = 0
        total_neutral = 0
        
        def get_rsi_signal(v):
            if v is None: return "NEUTRAL"
            if v < 30: return "BUY"
            if v > 70: return "SELL"
            return "NEUTRAL"
            
        def get_macd_signal(m, s):
            if m is None or s is None: return "NEUTRAL"
            if m > s: return "BUY"
            if m < s: return "SELL"
            return "NEUTRAL"
            
        def get_ma_signal(p, ma):
            if ma is None: return "NEUTRAL"
            if p > ma: return "BUY"
            if p < ma: return "SELL"
            return "NEUTRAL"
            
        def get_mom_signal(m):
            if m is None: return "NEUTRAL"
            if m > 0: return "BUY"
            if m < 0: return "SELL"
            return "NEUTRAL"
            
        def get_bb_signal(p, lower, upper):
            if lower is None or upper is None: return "NEUTRAL"
            if p < lower: return "BUY"
            if p > upper: return "SELL"
            return "NEUTRAL"
            
        details = []
        
        def add_detail(name, val, sig):
            nonlocal total_buy, total_sell, total_neutral
            # Formatting values for frontend presentation
            f_val = round(val, 2) if val is not None else "N/A"
            details.append({"name": name, "value": f_val, "signal": sig})
            if sig == "BUY": total_buy += 1
            elif sig == "SELL": total_sell += 1
            else: total_neutral += 1

        add_detail("RSI(14)", rsi_val, get_rsi_signal(rsi_val))
        add_detail("MACD", macd_val, get_macd_signal(macd_val, macd_sig))
        add_detail("Momentum(10)", mom_val, get_mom_signal(mom_val))
        add_detail("Bollinger Bands", current_price, get_bb_signal(current_price, bb_low_val, bb_up_val))
        
        add_detail("SMA(10)", sma10_val, get_ma_signal(current_price, sma10_val))
        add_detail("SMA(20)", sma20_val, get_ma_signal(current_price, sma20_val))
        add_detail("SMA(30)", sma30_val, get_ma_signal(current_price, sma30_val))
        add_detail("SMA(50)", sma50_val, get_ma_signal(current_price, sma50_val))
        
        add_detail("EMA(10)", ema10_val, get_ma_signal(current_price, ema10_val))
        add_detail("EMA(20)", ema20_val, get_ma_signal(current_price, ema20_val))
        add_detail("EMA(30)", ema30_val, get_ma_signal(current_price, ema30_val))
        
        if total_sell >= total_buy * 2:
            overall = "STRONG_SELL"
        elif total_buy >= total_sell * 2:
            overall = "STRONG_BUY"
        elif total_sell > total_buy:
            overall = "SELL"
        elif total_buy > total_sell:
            overall = "BUY"
        else:
            overall = "NEUTRAL"
            
        total = total_buy + total_sell + total_neutral
        if total == 0:
            confidence = 0
        else:
            confidence = abs(total_buy - total_sell) / total * 100
            
        return {
            "overall": overall,
            "confidence": round(confidence, 1),
            "buy": total_buy,
            "sell": total_sell,
            "neutral": total_neutral,
            "oscillators": {
                "buy": sum(1 for d in details[:4] if d['signal'] == 'BUY'),
                "sell": sum(1 for d in details[:4] if d['signal'] == 'SELL'),
                "neutral": sum(1 for d in details[:4] if d['signal'] == 'NEUTRAL')
            },
            "moving_averages": {
                "buy": sum(1 for d in details[4:] if d['signal'] == 'BUY'),
                "sell": sum(1 for d in details[4:] if d['signal'] == 'SELL'),
                "neutral": sum(1 for d in details[4:] if d['signal'] == 'NEUTRAL')
            },
            "details": details
        }


# ── Module-level singleton ───────────────────────────────────────────────────
indicator_engine = IndicatorEngine()
