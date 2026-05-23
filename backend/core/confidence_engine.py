"""
confidence_engine.py — Decomposed Regime-Adaptive Confidence Scoring
Replaces the single blended number with a fully explainable scoring breakdown.
Regime modifies component weights. Risk events apply penalties. All bounded.
"""
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# ── Regime → weight profiles ──────────────────────────────────────────────────
# Each profile: (ta_weight, news_weight, alignment_weight, regime_confidence_base)
# Weights should sum to ~1.0 across ta + news + alignment (regime is additive modifier)

REGIME_PROFILES: Dict[str, Dict[str, float]] = {
    "STRONG_TREND": {
        "ta_weight":        0.60,   # Trend → technicals king
        "news_weight":      0.15,
        "alignment_weight": 0.25,
        "regime_base":      80.0,   # Starting regime confidence
    },
    "WEAK_TREND": {
        "ta_weight":        0.50,
        "news_weight":      0.20,
        "alignment_weight": 0.30,
        "regime_base":      60.0,
    },
    "RANGING": {
        "ta_weight":        0.45,   # Range → RSI/BB mean-reversion more useful
        "news_weight":      0.30,
        "alignment_weight": 0.25,
        "regime_base":      55.0,
    },
    "VOLATILE": {
        "ta_weight":        0.40,   # All signals less reliable
        "news_weight":      0.35,
        "alignment_weight": 0.25,
        "regime_base":      45.0,   # Penalise volatile regimes
    },
    "NEWS_DRIVEN": {
        "ta_weight":        0.25,   # News is driving — trust it more
        "news_weight":      0.55,
        "alignment_weight": 0.20,
        "regime_base":      50.0,
    },
}

DEFAULT_PROFILE = REGIME_PROFILES["RANGING"]

# Regime-driven multiplier on the total TA vote score
REGIME_TA_SCALE: Dict[str, float] = {
    "STRONG_TREND": 1.10,
    "WEAK_TREND":   0.90,
    "RANGING":      1.00,
    "VOLATILE":     0.80,
    "NEWS_DRIVEN":  0.70,
}


class ConfidenceEngine:
    """
    Produces a ConfidenceBreakdown dict suitable for the v3 response schema.
    """

    def compute(
        self,
        indicator_signals: Dict[str, Any],
        news_score_100: float,
        alignment_score: float,
        regime: str,
        risk_events: Dict[str, Any],
        adaptive_weights: Dict[str, float],   # from memory_engine (RSI_MULTIPLIER, etc.)
        ta_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute the full decomposed confidence breakdown.
        Returns a dict matching the ConfidenceBreakdown schema.
        """
        profile   = REGIME_PROFILES.get(regime, DEFAULT_PROFILE)
        ta_scale  = REGIME_TA_SCALE.get(regime, 1.0)

        # ── Component 1: Technical Confidence ─────────────────────────────────
        technical_confidence = self._compute_technical_confidence(
            indicator_signals, adaptive_weights, ta_summary
        ) * ta_scale
        technical_confidence = round(min(100.0, max(0.0, technical_confidence)), 1)

        # ── Component 2: Sentiment Confidence ─────────────────────────────────
        sentiment_confidence = round(news_score_100, 1)

        # ── Component 3: Timeframe Alignment Score ─────────────────────────────
        tf_confidence = round(alignment_score, 1)

        # ── Component 4: Regime Confidence ────────────────────────────────────
        regime_confidence = round(profile["regime_base"], 1)

        # ── Weighted base score ────────────────────────────────────────────────
        ta_w  = profile["ta_weight"]
        nw_w  = profile["news_weight"]
        al_w  = profile["alignment_weight"]

        # Regime confidence contributes a fixed additive boost/penalty
        # normalised so strong regimes contribute +5 and weak -5
        regime_boost = (regime_confidence - 55.0) / 5.0  # -5 to +5

        raw_score = (
            technical_confidence * ta_w
            + sentiment_confidence * nw_w
            + tf_confidence       * al_w
            + regime_boost
        )
        raw_score = round(min(100.0, max(0.0, raw_score)), 1)

        # ── Risk penalties ────────────────────────────────────────────────────
        penalties = self._compute_risk_penalties(
            indicator_signals, regime, risk_events, ta_summary
        )
        total_penalty = sum(p["points"] for p in penalties)

        # ── Final confidence ──────────────────────────────────────────────────
        final = round(min(100.0, max(0.0, raw_score + total_penalty)), 1)

        # ── Explanation string ────────────────────────────────────────────────
        explanation = self._build_explanation(
            raw_score, final, total_penalty, penalties,
            technical_confidence, sentiment_confidence, regime
        )

        return {
            "total":         final,
            "components": {
                "technical":           technical_confidence,
                "sentiment":           sentiment_confidence,
                "timeframe_alignment": tf_confidence,
                "regime":              regime_confidence,
            },
            "applied_regime": regime,
            "regime_modifiers": {
                "ta_weight":        ta_w,
                "news_weight":      nw_w,
                "alignment_weight": al_w,
                "ta_scale":         ta_scale,
            },
            "raw_before_penalty": raw_score,
            "penalties":     penalties,
            "explanation":   explanation,
        }

    # ── Technical confidence ──────────────────────────────────────────────────

    def _compute_technical_confidence(
        self,
        signals: Dict[str, Any],
        weights: Dict[str, float],
        ta_summary: Dict[str, Any],
    ) -> float:
        """
        Vote-based technical score using adaptive per-indicator multipliers.
        Returns 0–100.
        """
        rsi_m  = weights.get("RSI_MULTIPLIER",      1.0)
        macd_m = weights.get("MACD_MULTIPLIER",     1.0)
        ema_m  = weights.get("EMA_MULTIPLIER",      1.0)
        mom_m  = weights.get("MOMENTUM_MULTIPLIER", 1.0)
        bb_m   = weights.get("BB_MULTIPLIER",       1.0)

        votes: List[Tuple[str, float]] = []

        rsi = signals.get("rsi_value")
        if rsi is not None:
            if rsi < 35:
                votes.append(("BUY",  rsi_m))
            elif rsi > 65:
                votes.append(("SELL", rsi_m))

        if signals.get("macd_signal") in ("BUY", "SELL"):
            votes.append((signals["macd_signal"], macd_m))

        ema_trend = signals.get("ema_trend", "MIXED")
        if ema_trend == "ABOVE":
            votes.append(("BUY",  ema_m))
        elif ema_trend == "BELOW":
            votes.append(("SELL", ema_m))

        if signals.get("momentum_signal") in ("BUY", "SELL"):
            votes.append((signals["momentum_signal"], mom_m))

        if signals.get("bb_signal") in ("BUY", "SELL"):
            votes.append((signals["bb_signal"], bb_m))

        buy_w  = sum(w for s, w in votes if s == "BUY")
        sell_w = sum(w for s, w in votes if s == "SELL")
        total  = buy_w + sell_w

        if total == 0:
            # No decisive votes — use raw indicator ratio from ta_summary
            buy  = ta_summary.get("buy",  0)
            sell = ta_summary.get("sell", 0)
            neu  = ta_summary.get("neutral", 0)
            tot  = buy + sell + neu
            if tot == 0:
                return 50.0
            return ((buy - sell) / tot + 1.0) / 2.0 * 100.0

        return (buy_w / total) * 100.0

    # ── Risk penalties ────────────────────────────────────────────────────────

    def _compute_risk_penalties(
        self,
        signals: Dict[str, Any],
        regime: str,
        risk_events: Dict[str, Any],
        ta_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        penalties = []

        def add(reason: str, pts: float):
            penalties.append({"reason": reason, "points": round(pts, 1)})

        # P1: High-impact event close
        event_penalty = risk_events.get("total_penalty", 0.0)
        if event_penalty < 0:
            add(f"Scheduled market event risk (see risk_events)", event_penalty)

        # P2: Overbought RSI in bullish setup
        rsi = signals.get("rsi_value")
        if rsi is not None and rsi > 72:
            add(f"RSI at {rsi:.1f} — overbought; pullback risk increases", -5.0)
        elif rsi is not None and rsi < 28:
            add(f"RSI at {rsi:.1f} — oversold; potential exhaustion of selling", -3.0)

        # P3: Volatile regime penalty
        if regime == "VOLATILE":
            add("Market in VOLATILE regime — all signals less reliable", -5.0)

        # P4: TA / News divergence
        buy = ta_summary.get("buy", 0)
        sell = ta_summary.get("sell", 0)
        if abs(buy - sell) < 2:
            add("Technical signals evenly split — low conviction setup", -4.0)

        # Total cap at -25
        total_pts = sum(p["points"] for p in penalties)
        if total_pts < -25:
            scale = -25 / total_pts
            penalties = [{"reason": p["reason"], "points": round(p["points"] * scale, 1)} for p in penalties]

        return penalties

    # ── Explanation builder ───────────────────────────────────────────────────

    def _build_explanation(
        self,
        raw: float,
        final: float,
        total_penalty: float,
        penalties: List[Dict],
        tech_conf: float,
        news_conf: float,
        regime: str,
    ) -> str:
        parts = [
            f"Raw score before penalties: {raw:.1f}.",
            f"Technical confidence: {tech_conf:.1f} | Sentiment confidence: {news_conf:.1f}.",
            f"Regime '{regime}' weighting applied.",
        ]
        if total_penalty < 0 and penalties:
            items = "; ".join(f"{p['reason']} ({p['points']:+.0f})" for p in penalties)
            parts.append(f"Penalties applied: {items}.")
            parts.append(f"Final confidence: {final:.1f} (reduced from {raw:.1f}).")
        else:
            parts.append(f"No penalties applied. Final confidence: {final:.1f}.")
        return " ".join(parts)


confidence_engine = ConfidenceEngine()
