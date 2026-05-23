"""
pattern_tracker.py — Named Setup Detection
Converts raw indicator snapshots into named, traceable setup patterns.
Every setup name is the unit the learning system learns about.
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# ── Setup registry ────────────────────────────────────────────────────────────
#
# Each entry: (setup_name, detection_function)
# Detection functions take the snapshot dict and return bool.
# Order matters: more specific setups are checked first.

_SETUP_REGISTRY: List[tuple] = []

def _setup(name: str):
    """Decorator: registers a function as a named setup detector."""
    def decorator(fn):
        _SETUP_REGISTRY.append((name, fn))
        return fn
    return decorator


# ── RSI-based setups ──────────────────────────────────────────────────────────

@_setup("RSI_OVERSOLD_BULL")
def _rsi_oversold_bull(s: dict) -> bool:
    rsi = s.get("rsi_value")
    return rsi is not None and rsi < 35 and s.get("bias") == "Bullish"

@_setup("RSI_OVERBOUGHT_BEAR")
def _rsi_overbought_bear(s: dict) -> bool:
    rsi = s.get("rsi_value")
    return rsi is not None and rsi > 65 and s.get("bias") == "Bearish"

@_setup("RSI_NEUTRAL_ZONE")
def _rsi_neutral(s: dict) -> bool:
    rsi = s.get("rsi_value")
    return rsi is not None and 40 <= rsi <= 60

# ── MACD-based setups ─────────────────────────────────────────────────────────

@_setup("MACD_BULL_CROSS")
def _macd_bull(s: dict) -> bool:
    return (s.get("macd_signal") == "BUY"
            and s.get("momentum_signal") == "BUY"
            and s.get("bias") == "Bullish")

@_setup("MACD_BEAR_CROSS")
def _macd_bear(s: dict) -> bool:
    return (s.get("macd_signal") == "SELL"
            and s.get("momentum_signal") == "SELL"
            and s.get("bias") == "Bearish")

# ── EMA trend-based setups ────────────────────────────────────────────────────

@_setup("EMA_BULL_STACK")
def _ema_bull_stack(s: dict) -> bool:
    return s.get("ema_trend") == "ABOVE" and s.get("bias") == "Bullish"

@_setup("EMA_BEAR_STACK")
def _ema_bear_stack(s: dict) -> bool:
    return s.get("ema_trend") == "BELOW" and s.get("bias") == "Bearish"

# ── Confidence-level setups ───────────────────────────────────────────────────

@_setup("HIGH_CONF_BULL")
def _high_conf_bull(s: dict) -> bool:
    return s.get("confidence_score", 0) > 75 and s.get("bias") == "Bullish"

@_setup("HIGH_CONF_BEAR")
def _high_conf_bear(s: dict) -> bool:
    return s.get("confidence_score", 0) > 75 and s.get("bias") == "Bearish"

@_setup("LOW_CONF_NEUTRAL")
def _low_conf(s: dict) -> bool:
    c = s.get("confidence_score", 50)
    return 40 <= c <= 60

# ── TA + News convergence setups ─────────────────────────────────────────────

@_setup("TA_NEWS_CONVERGE_BULL")
def _converge_bull(s: dict) -> bool:
    return s.get("technical_score", 0) > 65 and s.get("news_score", 0) > 60

@_setup("TA_NEWS_CONVERGE_BEAR")
def _converge_bear(s: dict) -> bool:
    return s.get("technical_score", 0) < 35 and s.get("news_score", 0) < 40

@_setup("TA_NEWS_DIVERGE")
def _diverge(s: dict) -> bool:
    return abs(s.get("technical_score", 50) - s.get("news_score", 50)) > 35

# ── Volatility / regime setups ────────────────────────────────────────────────

@_setup("VOLATILE_REGIME")
def _volatile(s: dict) -> bool:
    atr = s.get("atr_pct")
    return atr is not None and atr > 2.0

@_setup("TRENDING_REGIME")
def _trending(s: dict) -> bool:
    return s.get("market_regime") == "TRENDING"

@_setup("RANGING_MARKET")
def _ranging(s: dict) -> bool:
    return s.get("market_regime") == "RANGING"

# ── BB-based setups ───────────────────────────────────────────────────────────

@_setup("BB_OVERSOLD_BULL")
def _bb_oversold(s: dict) -> bool:
    return s.get("bb_signal") == "BUY" and s.get("bias") == "Bullish"

@_setup("BB_OVERBOUGHT_BEAR")
def _bb_overbought(s: dict) -> bool:
    return s.get("bb_signal") == "SELL" and s.get("bias") == "Bearish"


# ── Market regime classifier ──────────────────────────────────────────────────

def classify_market_regime(
    ema_trend: Optional[str],
    momentum_signal: Optional[str],
    atr_pct: Optional[float],
    confidence_score: float,
) -> str:
    """
    Returns one of: TRENDING | RANGING | VOLATILE
    Simple, deterministic rule cascade.
    """
    if atr_pct is not None and atr_pct > 2.0:
        return "VOLATILE"
    if ema_trend in ("ABOVE", "BELOW") and momentum_signal in ("BUY", "SELL"):
        return "TRENDING"
    return "RANGING"


# ── Main public interface ─────────────────────────────────────────────────────

class PatternTracker:

    def detect_setups(self, snapshot: dict) -> List[str]:
        """
        Run all registered setup detectors against the snapshot dict.
        Returns a list of active setup names.
        """
        active: List[str] = []
        for name, fn in _SETUP_REGISTRY:
            try:
                if fn(snapshot):
                    active.append(name)
            except Exception as e:
                logger.warning(f"[PatternTracker] Error in setup '{name}': {e}")
        return active

    def classify_regime(
        self,
        ema_trend: Optional[str],
        momentum_signal: Optional[str],
        atr_pct: Optional[float],
        confidence_score: float,
    ) -> str:
        return classify_market_regime(ema_trend, momentum_signal, atr_pct, confidence_score)

    def extract_indicator_signals(self, ta_details: list) -> Dict[str, Any]:
        """
        Extract named signal fields from the raw ta_details list
        (output of indicator_engine.generate_technical_summary).
        Returns a flat dict of individual indicator states.
        """
        result = {
            "rsi_value": None,
            "macd_signal": "NEUTRAL",
            "ema_trend": "MIXED",
            "momentum_signal": "NEUTRAL",
            "bb_signal": "NEUTRAL",
        }
        ema_signals = []

        for d in ta_details:
            name = d.get("name", "")
            sig = d.get("signal", "NEUTRAL")
            val = d.get("value")

            if name == "RSI(14)":
                result["rsi_value"] = val
            elif name == "MACD":
                result["macd_signal"] = sig
            elif name == "Momentum(10)":
                result["momentum_signal"] = sig
            elif name == "Bollinger Bands":
                result["bb_signal"] = sig
            elif "EMA" in name:
                ema_signals.append(sig)

        # Derive EMA trend: ABOVE if all EMA signals are BUY, BELOW if all SELL
        if ema_signals:
            if all(s == "BUY" for s in ema_signals):
                result["ema_trend"] = "ABOVE"
            elif all(s == "SELL" for s in ema_signals):
                result["ema_trend"] = "BELOW"
            else:
                result["ema_trend"] = "MIXED"

        return result


pattern_tracker = PatternTracker()
