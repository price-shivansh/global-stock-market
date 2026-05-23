"""
timeframe_engine.py — Multi-Timeframe Alignment Intelligence
Fetches 4H, 1H, and 15m data independently and computes per-timeframe bias,
then classifies the alignment into one of 7 named states.
Uses an in-process TTL cache to avoid redundant yfinance calls.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Alignment labels ──────────────────────────────────────────────────────────
STRONG_BULL   = "STRONG_BULL"    # 4H Bull, 1H Bull, 15m Bull
STRONG_BEAR   = "STRONG_BEAR"    # 4H Bear, 1H Bear, 15m Bear
PULLBACK_BULL = "PULLBACK_BULL"  # 4H Bull, 1H Bull, 15m Bear
PULLBACK_BEAR = "PULLBACK_BEAR"  # 4H Bear, 1H Bear, 15m Bull
TRANSITION    = "TRANSITION"     # 4H one direction, 1H flipping opposite
WEAK_BULL     = "WEAK_BULL"      # 4H Bull, 1H neutral/mixed, 15m anything
WEAK_BEAR     = "WEAK_BEAR"      # 4H Bear, 1H neutral/mixed, 15m anything
MIXED         = "MIXED"          # Cannot determine clear picture

# Score lookup for alignment labels → 0–100
ALIGNMENT_SCORES = {
    STRONG_BULL:   90,
    STRONG_BEAR:   90,
    PULLBACK_BULL: 70,
    PULLBACK_BEAR: 70,
    WEAK_BULL:     55,
    WEAK_BEAR:     55,
    TRANSITION:    35,
    MIXED:         20,
}

ALIGNMENT_DESCRIPTIONS = {
    STRONG_BULL:   "All three timeframes (4H/1H/15m) are bullish — strong trend alignment.",
    STRONG_BEAR:   "All three timeframes (4H/1H/15m) are bearish — strong trend alignment.",
    PULLBACK_BULL: "4H and 1H are bullish, 15m is pulling back — typical healthy retracement. Ideal long entry zone.",
    PULLBACK_BEAR: "4H and 1H are bearish, 15m is bouncing — relief rally in a downtrend. Ideal short entry zone.",
    WEAK_BULL:     "4H is bullish but 1H momentum is weakening. Proceed with reduced size.",
    WEAK_BEAR:     "4H is bearish but 1H momentum is weakening. Proceed with reduced size.",
    TRANSITION:    "4H and 1H timeframes disagree — trend change may be in progress. Avoid new positions.",
    MIXED:         "Timeframes show no coherent direction. Do not trade.",
}


class TimeframeTTLCache:
    """Simple per-key TTL cache to avoid redundant data fetches."""

    def __init__(self):
        self._store: Dict[str, Tuple[Any, datetime]] = {}

    def get(self, key: str, ttl_seconds: int) -> Optional[Any]:
        if key in self._store:
            data, ts = self._store[key]
            if (datetime.now(timezone.utc) - ts).total_seconds() < ttl_seconds:
                return data
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, datetime.now(timezone.utc))

    def clear(self) -> None:
        self._store.clear()


_cache = TimeframeTTLCache()

# TTL per timeframe interval
_TTL = {
    "4h":  900,   # 15 min cache for 4H data
    "1h":  300,   # 5 min cache for 1H data
    "15m": 120,   # 2 min cache for 15m data
}

# yfinance params per label
_YF_PARAMS = {
    "4h":  ("60d", "4h"),
    "1h":  ("30d", "1h"),
    "15m": ("7d",  "15m"),
}


class TimeframeEngine:
    """
    Computes individual bias per timeframe and classifies multi-TF alignment.
    """

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch and analyze 4H, 1H, and 15m timeframes for `symbol`.
        Returns full alignment context dict.
        """
        from data_fetcher import data_fetcher
        from indicator_engine import indicator_engine

        results: Dict[str, Any] = {}
        for label, (period, interval) in _YF_PARAMS.items():
            cache_key = f"{symbol}_{label}"
            df = _cache.get(cache_key, _TTL[label])
            if df is None:
                try:
                    df = await data_fetcher.fetch_stock_data(symbol, period=period, interval=interval)
                    if df is not None and not df.empty:
                        _cache.set(cache_key, df)
                except Exception as e:
                    logger.warning(f"[TimeframeEngine] Failed to fetch {symbol} {label}: {e}")
                    df = None

            if df is not None and not df.empty:
                ta = indicator_engine.generate_technical_summary(df)
                bias, score = self._bias_from_ta(ta)
                results[label] = {"bias": bias, "score": score, "ta": ta}
            else:
                results[label] = {"bias": "Neutral", "score": 50.0, "ta": {}}

        alignment, description, score = self._classify_alignment(
            results["4h"]["bias"],
            results["1h"]["bias"],
            results["15m"]["bias"],
        )

        return {
            "tf_4h":  {"bias": results["4h"]["bias"],  "score": results["4h"]["score"]},
            "tf_1h":  {"bias": results["1h"]["bias"],  "score": results["1h"]["score"]},
            "tf_15m": {"bias": results["15m"]["bias"], "score": results["15m"]["score"]},
            "alignment":             alignment,
            "alignment_description": description,
            "alignment_score":       float(score),
        }

    # ── Bias derivation ───────────────────────────────────────────────────────

    def _bias_from_ta(self, ta: dict) -> Tuple[str, float]:
        """Derive directional bias and 0–100 score from a ta_summary dict."""
        buy  = ta.get("buy",  0)
        sell = ta.get("sell", 0)
        neu  = ta.get("neutral", 0)
        total = buy + sell + neu

        if total == 0:
            return "Neutral", 50.0

        net = buy - sell
        score = ((net / total) + 1.0) / 2.0 * 100.0

        if score >= 60.0:
            bias = "Bullish"
        elif score <= 40.0:
            bias = "Bearish"
        else:
            bias = "Neutral"

        return bias, round(score, 1)

    # ── Alignment classification ───────────────────────────────────────────────

    def _classify_alignment(
        self,
        bias_4h:  str,
        bias_1h:  str,
        bias_15m: str,
    ) -> Tuple[str, str, int]:
        """Returns (alignment_label, description, score)."""

        # Perfect alignment
        if bias_4h == "Bullish" and bias_1h == "Bullish" and bias_15m == "Bullish":
            return STRONG_BULL, ALIGNMENT_DESCRIPTIONS[STRONG_BULL], ALIGNMENT_SCORES[STRONG_BULL]

        if bias_4h == "Bearish" and bias_1h == "Bearish" and bias_15m == "Bearish":
            return STRONG_BEAR, ALIGNMENT_DESCRIPTIONS[STRONG_BEAR], ALIGNMENT_SCORES[STRONG_BEAR]

        # Pullback patterns
        if bias_4h == "Bullish" and bias_1h == "Bullish" and bias_15m == "Bearish":
            return PULLBACK_BULL, ALIGNMENT_DESCRIPTIONS[PULLBACK_BULL], ALIGNMENT_SCORES[PULLBACK_BULL]

        if bias_4h == "Bearish" and bias_1h == "Bearish" and bias_15m == "Bullish":
            return PULLBACK_BEAR, ALIGNMENT_DESCRIPTIONS[PULLBACK_BEAR], ALIGNMENT_SCORES[PULLBACK_BEAR]

        # Transition — higher timeframes disagree
        if bias_4h != bias_1h and bias_4h != "Neutral" and bias_1h != "Neutral":
            return TRANSITION, ALIGNMENT_DESCRIPTIONS[TRANSITION], ALIGNMENT_SCORES[TRANSITION]

        # Weak trends — 4H has direction but 1H is neutral
        if bias_4h == "Bullish" and bias_1h == "Neutral":
            return WEAK_BULL, ALIGNMENT_DESCRIPTIONS[WEAK_BULL], ALIGNMENT_SCORES[WEAK_BULL]

        if bias_4h == "Bearish" and bias_1h == "Neutral":
            return WEAK_BEAR, ALIGNMENT_DESCRIPTIONS[WEAK_BEAR], ALIGNMENT_SCORES[WEAK_BEAR]

        # Fallthrough
        return MIXED, ALIGNMENT_DESCRIPTIONS[MIXED], ALIGNMENT_SCORES[MIXED]


timeframe_engine = TimeframeEngine()
