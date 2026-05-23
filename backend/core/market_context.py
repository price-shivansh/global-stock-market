"""
market_context.py — Enhanced Market Regime + Price Structure Detection
Classifies market into 5 regimes and 6 price structures using indicator snapshots
and OHLCV data. Fully deterministic and explainable.
"""
import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ── Regime labels ─────────────────────────────────────────────────────────────
STRONG_TREND  = "STRONG_TREND"
WEAK_TREND    = "WEAK_TREND"
RANGING       = "RANGING"
VOLATILE      = "VOLATILE"
NEWS_DRIVEN   = "NEWS_DRIVEN"

# ── Structure labels ──────────────────────────────────────────────────────────
HIGHER_HIGHS     = "HIGHER_HIGHS"
LOWER_LOWS       = "LOWER_LOWS"
SUPPORT_HOLD     = "SUPPORT_HOLD"
RESISTANCE_REJECT = "RESISTANCE_REJECT"
BREAKOUT         = "BREAKOUT"
CONSOLIDATION    = "CONSOLIDATION"
UNDEFINED        = "UNDEFINED"

# ── ATR volatility thresholds by asset class ──────────────────────────────────
# Commodities tolerate higher ATR before being flagged VOLATILE
ATR_VOLATILE_THRESHOLDS = {
    "commodity": 2.0,   # CL=F, NG=F, GC=F
    "index":     1.2,   # ^NSEI, ^NSEBANK, ^GSPC
    "crypto":    4.0,   # BTC-USD, ETH-USD
    "stock":     1.8,   # individual equities
    "default":   2.0,
}

# Symbol → asset class
SYMBOL_CLASS = {
    "CL=F":     "commodity", "BZ=F": "commodity",
    "NG=F":     "commodity", "GC=F": "commodity", "SI=F": "commodity",
    "^NSEI":    "index",     "^NSEBANK": "index",  "^BSESN": "index",
    "^GSPC":    "index",     "^DJI":     "index",  "^IXIC":  "index",
    "BTC-USD":  "crypto",    "ETH-USD":  "crypto",
}


class MarketContext:
    """
    Computes market regime and price structure from OHLCV data + indicator signals.
    All logic is rule-based and fully deterministic.
    """

    def classify_regime(
        self,
        df: pd.DataFrame,
        indicator_signals: Dict[str, Any],
        news_score: float,
        technical_score: float,
        symbol: str = "",
    ) -> Dict[str, Any]:
        """
        Returns a dict with regime label, structure label, atr_pct, and description.
        """
        atr_pct   = self._calc_atr_pct(df)
        regime    = self._detect_regime(df, indicator_signals, news_score, technical_score, atr_pct, symbol)
        structure = self._detect_structure(df)
        description = self._describe_regime(regime, structure, atr_pct)

        return {
            "label":       regime,
            "structure":   structure,
            "atr_pct":     round(atr_pct, 3),
            "description": description,
        }

    # ── ATR % calculation ─────────────────────────────────────────────────────

    def _calc_atr_pct(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR as percentage of current price — asset-agnostic volatility proxy."""
        try:
            high_low   = df["High"] - df["Low"]
            high_close = (df["High"] - df["Close"].shift()).abs()
            low_close  = (df["Low"]  - df["Close"].shift()).abs()
            tr  = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(period).mean().iloc[-1]
            price = float(df["Close"].iloc[-1])
            return (atr / price) * 100.0 if price > 0 else 1.0
        except Exception:
            return 1.0

    # ── Regime detection ──────────────────────────────────────────────────────

    def _detect_regime(
        self,
        df: pd.DataFrame,
        signals: Dict[str, Any],
        news_score: float,
        technical_score: float,
        atr_pct: float,
        symbol: str,
    ) -> str:
        asset_class  = SYMBOL_CLASS.get(symbol, "default")
        atr_threshold = ATR_VOLATILE_THRESHOLDS.get(asset_class, 2.0)

        ema_trend       = signals.get("ema_trend", "MIXED")
        momentum_signal = signals.get("momentum_signal", "NEUTRAL")
        rsi_value       = signals.get("rsi_value") or 50.0

        # Rule 1: NEWS_DRIVEN — large TA/News divergence AND elevated ATR
        if abs(technical_score - news_score) > 35 and atr_pct > atr_threshold * 0.7:
            return NEWS_DRIVEN

        # Rule 2: VOLATILE — ATR spike
        if atr_pct > atr_threshold:
            return VOLATILE

        # Rule 3: STRONG_TREND — aligned EMA + momentum + RSI not extreme
        ema_aligned   = ema_trend in ("ABOVE", "BELOW")
        momentum_live = momentum_signal in ("BUY", "SELL")
        rsi_mid_range = 35 < rsi_value < 72

        if ema_aligned and momentum_live and rsi_mid_range:
            # Check EMA slope is sustained over last 5 candles
            if self._has_sustained_slope(df):
                return STRONG_TREND
            return WEAK_TREND

        # Rule 4: WEAK_TREND — EMA partially aligned but momentum fading
        if ema_trend == "MIXED" and momentum_signal in ("BUY", "SELL"):
            return WEAK_TREND

        # Rule 5: RANGING — flat EMAs, neutral momentum
        return RANGING

    def _has_sustained_slope(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """Return True if EMA20 has been consistently sloping for `lookback` candles."""
        try:
            close = df["Close"]
            ema20 = close.ewm(span=20, adjust=False).mean()
            slope_window = ema20.iloc[-lookback:]
            diffs = slope_window.diff().dropna()
            pos = (diffs > 0).sum()
            neg = (diffs < 0).sum()
            return pos >= lookback - 1 or neg >= lookback - 1
        except Exception:
            return False

    # ── Price structure detection ─────────────────────────────────────────────

    def _detect_structure(self, df: pd.DataFrame) -> str:
        """Classify recent price structure from OHLCV data."""
        try:
            if len(df) < 10:
                return UNDEFINED

            close  = df["Close"].values
            high   = df["High"].values
            low    = df["Low"].values
            recent = close[-10:]

            # CONSOLIDATION: tiny range in last 5 candles
            r5 = recent[-5:]
            spread_pct = (r5.max() - r5.min()) / r5.mean() * 100
            if spread_pct < 0.5:
                return CONSOLIDATION

            # Find local highs and lows (simple 3-bar pivot)
            local_highs = [high[i] for i in range(1, len(high)-1)
                           if high[i] > high[i-1] and high[i] > high[i+1]]
            local_lows  = [low[i]  for i in range(1, len(low)-1)
                           if low[i]  < low[i-1]  and low[i]  < low[i+1]]

            # HIGHER_HIGHS / LOWER_LOWS from last 3 pivots
            if len(local_highs) >= 3:
                last3h = local_highs[-3:]
                if last3h[0] < last3h[1] < last3h[2]:
                    return HIGHER_HIGHS

            if len(local_lows) >= 3:
                last3l = local_lows[-3:]
                if last3l[0] > last3l[1] > last3l[2]:
                    return LOWER_LOWS

            # BREAKOUT: latest close > prior swing high by > 0.5%
            if len(local_highs) >= 2:
                prior_high = local_highs[-2]
                if close[-1] > prior_high * 1.005:
                    return BREAKOUT

            # SUPPORT_HOLD: price bounced from a recent local low (< 0.5% away)
            if local_lows:
                nearest_low = min(local_lows, key=lambda x: abs(close[-1] - x))
                if abs(close[-1] - nearest_low) / close[-1] < 0.005:
                    return SUPPORT_HOLD

            # RESISTANCE_REJECT: price near prior high but closed below
            if local_highs:
                nearest_high = min(local_highs, key=lambda x: abs(close[-1] - x))
                if abs(close[-1] - nearest_high) / close[-1] < 0.005 and close[-1] < nearest_high:
                    return RESISTANCE_REJECT

            return UNDEFINED

        except Exception as e:
            logger.debug(f"[MarketContext] Structure detection failed: {e}")
            return UNDEFINED

    # ── Regime descriptions ───────────────────────────────────────────────────

    _REGIME_DESCRIPTIONS = {
        STRONG_TREND:  "Market is in a sustained directional trend with aligned momentum and EMAs.",
        WEAK_TREND:    "Trend is present but momentum is fading — watch for continuation or reversal.",
        RANGING:       "Market is in a consolidating, range-bound phase with no clear directional bias.",
        VOLATILE:      "Elevated volatility detected. Price action is erratic; risk is heightened.",
        NEWS_DRIVEN:   "Price action diverges from technicals, suggesting a news-driven move. Wait for stabilisation.",
    }

    def _describe_regime(self, regime: str, structure: str, atr_pct: float) -> str:
        base = self._REGIME_DESCRIPTIONS.get(regime, "Regime unclear.")
        structure_note = {
            HIGHER_HIGHS:      " Price forming higher highs — bullish structure confirmed.",
            LOWER_LOWS:        " Price forming lower lows — bearish structure confirmed.",
            CONSOLIDATION:     " Price is tightly consolidated — breakout imminent.",
            BREAKOUT:          " Recent breakout above prior swing high detected.",
            SUPPORT_HOLD:      " Price holding at support — potential bounce zone.",
            RESISTANCE_REJECT: " Price rejected at resistance — potential reversal zone.",
            UNDEFINED:         "",
        }.get(structure, "")
        return base + structure_note


market_context = MarketContext()
