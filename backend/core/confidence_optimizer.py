"""
confidence_optimizer.py — Adaptive Weight Nudger
Reads setup performance stats and slowly adjusts indicator/weight multipliers.
All changes are bounded, logged, and fully deterministic.
"""
import logging
from typing import Dict, Any
from core.memory_engine import memory_engine, DEFAULT_WEIGHTS, WEIGHT_BOUNDS

logger = logging.getLogger(__name__)

# ── Optimizer constants ───────────────────────────────────────────────────────

# Minimum number of evaluated outcomes before we trust the win-rate
MIN_SAMPLE_SIZE = 10

# Nudge step sizes (per optimization cycle)
LARGE_NUDGE = 0.02   # applied when sample >= MIN_SAMPLE_SIZE
SMALL_NUDGE = 0.01   # applied for 5 <= sample < MIN_SAMPLE_SIZE

# Win-rate thresholds
WIN_THRESHOLD  = 0.65   # above this → boost weight
LOSE_THRESHOLD = 0.40   # below this → reduce weight

# Which indicators each setup type most strongly drives
SETUP_TO_WEIGHT_MAP: Dict[str, str] = {
    "RSI_OVERSOLD_BULL":    "RSI_MULTIPLIER",
    "RSI_OVERBOUGHT_BEAR":  "RSI_MULTIPLIER",
    "RSI_NEUTRAL_ZONE":     "RSI_MULTIPLIER",
    "MACD_BULL_CROSS":      "MACD_MULTIPLIER",
    "MACD_BEAR_CROSS":      "MACD_MULTIPLIER",
    "EMA_BULL_STACK":       "EMA_MULTIPLIER",
    "EMA_BEAR_STACK":       "EMA_MULTIPLIER",
    "BB_OVERSOLD_BULL":     "BB_MULTIPLIER",
    "BB_OVERBOUGHT_BEAR":   "BB_MULTIPLIER",
    # Momentum affects momentum multiplier
    "MACD_BULL_CROSS":      "MOMENTUM_MULTIPLIER",   # intentional dual-mapping
}


class ConfidenceOptimizer:
    """
    Single-responsibility optimizer: iterate through all setup stats,
    determine if any weight deserves a nudge, and apply it via memory_engine.
    """

    def run_optimization_cycle(self, symbol: str = "GLOBAL") -> Dict[str, Any]:
        """
        Run one optimization pass.
        Returns a summary of changes made this cycle.
        """
        setup_stats = memory_engine.get_setup_stats(symbol if symbol != "GLOBAL" else "GLOBAL")
        if not setup_stats:
            logger.debug("[ConfidenceOptimizer] No setup stats available — skipping cycle.")
            return {"changes_made": 0, "reason": "no stats available"}

        changes: list = []

        for s in setup_stats:
            setup_name     = s["setup_name"]
            total          = s.get("total_predictions", 0)
            correct        = s.get("correct_count", 0)
            incorrect      = s.get("incorrect_count", 0)
            decisive       = correct + incorrect
            win_rate       = s.get("win_rate", 0.5)

            if decisive < 5:
                # Not enough data — skip entirely
                continue

            nudge_size = LARGE_NUDGE if decisive >= MIN_SAMPLE_SIZE else SMALL_NUDGE

            # Determine which weight key this setup feeds
            weight_key = SETUP_TO_WEIGHT_MAP.get(setup_name)
            if not weight_key:
                continue  # No weight mapping for this setup type

            current = memory_engine.get_weight(weight_key, "GLOBAL")

            if win_rate >= WIN_THRESHOLD:
                new_value = current + nudge_size
                reason = (
                    f"Setup '{setup_name}' has win_rate={win_rate:.2f} "
                    f"({correct}/{decisive} correct) — boosting {weight_key}"
                )
                memory_engine.set_weight(weight_key, new_value, reason, "GLOBAL")
                changes.append({"key": weight_key, "old": current, "new": min(WEIGHT_BOUNDS[weight_key][1], new_value), "direction": "UP"})

            elif win_rate <= LOSE_THRESHOLD:
                new_value = current - nudge_size
                reason = (
                    f"Setup '{setup_name}' has win_rate={win_rate:.2f} "
                    f"({correct}/{decisive} correct) — reducing {weight_key}"
                )
                memory_engine.set_weight(weight_key, new_value, reason, "GLOBAL")
                changes.append({"key": weight_key, "old": current, "new": max(WEIGHT_BOUNDS[weight_key][0], new_value), "direction": "DOWN"})

        # ── Also adjust global TA/News weight balance ─────────────────────────
        self._adapt_ta_news_balance(symbol)

        return {"changes_made": len(changes), "changes": changes}

    def _adapt_ta_news_balance(self, symbol: str) -> None:
        """
        Gradually shift the TA/News split based on which side has been more
        predictive recently.
        """
        from core.memory_engine import memory_engine

        raw_outcomes = memory_engine.get_raw_outcomes_for_symbol(
            symbol if symbol != "GLOBAL" else "CL=F", "1h"
        )
        if len(raw_outcomes) < MIN_SAMPLE_SIZE:
            return

        # Compare accuracy of "technical only" vs "news-driven" predictions
        # Technical-only: news_score near 50 (45–55), technical decisive
        ta_correct = 0; ta_total = 0
        news_correct = 0; news_total = 0

        for row in raw_outcomes[-50:]:   # last 50 outcomes only
            try:
                # We don't have ts/news scores stored in outcomes table, skip
                # This analysis runs on the joined set via raw_outcomes which
                # only has active_setups, bias, price_change_pct, outcome.
                active = row.get("active_setups", [])
                if isinstance(active, str):
                    import json
                    active = json.loads(active)
                outcome = row.get("outcome", "NEUTRAL")
                if "TA_NEWS_CONVERGE_BULL" in active or "TA_NEWS_CONVERGE_BEAR" in active:
                    # News heavily involved
                    news_total += 1
                    if outcome == "CORRECT":
                        news_correct += 1
                elif "EMA_BULL_STACK" in active or "EMA_BEAR_STACK" in active or "MACD_BULL_CROSS" in active:
                    # Technical-led prediction
                    ta_total += 1
                    if outcome == "CORRECT":
                        ta_correct += 1
            except Exception:
                continue

        if ta_total < 5 or news_total < 5:
            return

        ta_wr   = ta_correct / ta_total
        news_wr = news_correct / news_total

        current_ta = memory_engine.get_weight("TA_WEIGHT", "GLOBAL")

        if ta_wr - news_wr > 0.10:
            # Technical significantly outperforming → shift towards TA
            new_ta = current_ta + SMALL_NUDGE
            reason = f"TA win-rate ({ta_wr:.2f}) > News win-rate ({news_wr:.2f}) — shifting TA_WEIGHT up"
            memory_engine.set_weight("TA_WEIGHT",  new_ta, reason, "GLOBAL")
            memory_engine.set_weight("NEWS_WEIGHT", 1.0 - new_ta, reason, "GLOBAL")

        elif news_wr - ta_wr > 0.10:
            # News significantly outperforming → shift towards News
            new_ta = current_ta - SMALL_NUDGE
            reason = f"News win-rate ({news_wr:.2f}) > TA win-rate ({ta_wr:.2f}) — shifting TA_WEIGHT down"
            memory_engine.set_weight("TA_WEIGHT",  new_ta, reason, "GLOBAL")
            memory_engine.set_weight("NEWS_WEIGHT", 1.0 - new_ta, reason, "GLOBAL")

    def get_weighted_confidence(
        self,
        technical_score: float,
        news_score: float,
        indicator_signals: Dict[str, Any],
    ) -> float:
        """
        Compute the adaptive confidence score using current weights.
        indicator_signals is the dict from pattern_tracker.extract_indicator_signals().
        """
        ta_w    = memory_engine.get_weight("TA_WEIGHT",    "GLOBAL")
        news_w  = memory_engine.get_weight("NEWS_WEIGHT",  "GLOBAL")

        rsi_m   = memory_engine.get_weight("RSI_MULTIPLIER",      "GLOBAL")
        macd_m  = memory_engine.get_weight("MACD_MULTIPLIER",     "GLOBAL")
        ema_m   = memory_engine.get_weight("EMA_MULTIPLIER",      "GLOBAL")
        mom_m   = memory_engine.get_weight("MOMENTUM_MULTIPLIER", "GLOBAL")
        bb_m    = memory_engine.get_weight("BB_MULTIPLIER",       "GLOBAL")

        # Each active BUY/SELL signal contributes a weighted vote
        # We re-score from the raw signals rather than using the pre-scored value
        # so that multipliers actually shift the balance
        votes: list = []

        if indicator_signals.get("rsi_value") is not None:
            rsi = indicator_signals["rsi_value"]
            if rsi < 35:
                votes.append(("BUY",  rsi_m))
            elif rsi > 65:
                votes.append(("SELL", rsi_m))

        if indicator_signals.get("macd_signal") in ("BUY", "SELL"):
            votes.append((indicator_signals["macd_signal"], macd_m))

        if indicator_signals.get("ema_trend") == "ABOVE":
            votes.append(("BUY",  ema_m))
        elif indicator_signals.get("ema_trend") == "BELOW":
            votes.append(("SELL", ema_m))

        if indicator_signals.get("momentum_signal") in ("BUY", "SELL"):
            votes.append((indicator_signals["momentum_signal"], mom_m))

        if indicator_signals.get("bb_signal") in ("BUY", "SELL"):
            votes.append((indicator_signals["bb_signal"], bb_m))

        # Score: sum of buy weights vs total weight
        buy_weight  = sum(w for sig, w in votes if sig == "BUY")
        sell_weight = sum(w for sig, w in votes if sig == "SELL")
        total_w     = buy_weight + sell_weight

        if total_w == 0:
            adaptive_ta_score = 50.0
        else:
            adaptive_ta_score = (buy_weight / total_w) * 100.0

        # Blend with news
        confidence = (adaptive_ta_score * ta_w) + (news_score * news_w)
        return round(min(100.0, max(0.0, confidence)), 1)


confidence_optimizer = ConfidenceOptimizer()
