"""
explanation_engine.py — Structured Narrative Generator
Produces supporting_factors, weakening_factors, invalidation_conditions,
regime_context, and the main AI summary paragraph.
Replaces the old summary_engine.py for v3 responses (summary_engine.py preserved for v2).
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExplanationEngine:
    """
    Converts all engine outputs into structured, human-readable explanations.
    Every bullet point traces to a specific rule or indicator value.
    """

    def generate(
        self,
        bias: str,
        confidence_breakdown: Dict[str, Any],
        regime: str,
        structure: str,
        alignment: str,
        alignment_description: str,
        indicator_signals: Dict[str, Any],
        ta_details: List[Dict[str, Any]],
        ta_summary: Dict[str, Any],
        tf_data: Dict[str, Any],
        news_score_100: float,
        relevant_news: List[Any],
        risk_events: Dict[str, Any],
        trade_state: str,
        current_price: float,
        ema50_value: Optional[float] = None,
    ) -> Dict[str, Any]:

        ai_summary         = self._build_ai_summary(
            bias, confidence_breakdown["total"], regime, alignment, trade_state
        )
        regime_context     = self._regime_context(regime, structure, alignment_description)
        supporting_factors = self._supporting_factors(
            bias, indicator_signals, ta_details, tf_data, news_score_100, regime
        )
        weakening_factors  = self._weakening_factors(
            bias, indicator_signals, ta_details, alignment, regime, confidence_breakdown
        )
        invalidation       = self._invalidation_conditions(
            bias, current_price, ema50_value, ta_details, structure
        )
        news_drivers       = self._news_drivers(relevant_news)
        risk_warnings      = self._risk_warnings(
            risk_events, regime, indicator_signals, alignment
        )
        conf_explanation   = confidence_breakdown.get("explanation", "")

        return {
            "ai_summary":             ai_summary,
            "regime_context":         regime_context,
            "supporting_factors":     supporting_factors,
            "weakening_factors":      weakening_factors,
            "invalidation_conditions": invalidation,
            "news_drivers":           news_drivers,
            "risk_warnings":          risk_warnings,
            "confidence_explanation": conf_explanation,
        }

    # ── AI Summary paragraph ─────────────────────────────────────────────────

    def _build_ai_summary(
        self, bias: str, confidence: float, regime: str, alignment: str, trade_state: str
    ) -> str:
        regime_adj = {
            "STRONG_TREND": "strongly trending",
            "WEAK_TREND":   "weakly trending",
            "RANGING":      "range-bound",
            "VOLATILE":     "highly volatile",
            "NEWS_DRIVEN":  "news-driven",
        }.get(regime, "indeterminate")

        alignment_adj = {
            "STRONG_BULL":   "with all timeframes bullish",
            "STRONG_BEAR":   "with all timeframes bearish",
            "PULLBACK_BULL": "in a healthy bullish pullback",
            "PULLBACK_BEAR": "in a bearish relief rally",
            "TRANSITION":    "undergoing a potential trend transition",
            "WEAK_BULL":     "with fading bullish momentum",
            "WEAK_BEAR":     "with fading bearish momentum",
            "MIXED":         "with conflicting multi-timeframe signals",
        }.get(alignment, "")

        state_suffix = {
            "TRADE":    "Conditions support a directional trade.",
            "WAIT":     "Monitor for confirmation before committing capital.",
            "NO_TRADE": "Trade entry is NOT recommended at this time.",
        }.get(trade_state, "")

        return (
            f"The market exhibits a {bias} bias with {confidence:.1f}% confidence in a "
            f"{regime_adj} environment {alignment_adj}. {state_suffix}"
        )

    # ── Regime context ───────────────────────────────────────────────────────

    def _regime_context(self, regime: str, structure: str, alignment_desc: str) -> str:
        regime_text = {
            "STRONG_TREND": (
                "The market is in a STRONG_TREND phase. EMAs are stacked and aligned, "
                "momentum is consistent. Trend-following strategies (MACD, EMA) carry "
                "the highest reliability right now."
            ),
            "WEAK_TREND": (
                "The market is in a WEAK_TREND phase. A directional bias exists but "
                "momentum is decelerating. Reduce position size and tighten stops."
            ),
            "RANGING": (
                "The market is range-bound with no dominant directional bias. "
                "Mean-reversion strategies (RSI, Bollinger Bands) are preferred. "
                "Avoid breakout-style momentum entries."
            ),
            "VOLATILE": (
                "The market is in a VOLATILE state — ATR is significantly elevated. "
                "Signals are less reliable and stop-loss distances must widen. "
                "Reduce size or avoid trading until volatility normalises."
            ),
            "NEWS_DRIVEN": (
                "Recent price action is driven by news flow rather than pure technicals. "
                "Wait for the initial news-driven move to complete before entering. "
                "News sentiment carries extra weight in this environment."
            ),
        }.get(regime, "Market regime is unclear.")

        return f"{regime_text} Price structure: {structure.replace('_', ' ').title()}. {alignment_desc}"

    # ── Supporting factors ───────────────────────────────────────────────────

    def _supporting_factors(
        self,
        bias: str,
        signals: Dict[str, Any],
        ta_details: List[Dict[str, Any]],
        tf_data: Dict[str, Any],
        news_score: float,
        regime: str,
    ) -> List[str]:
        factors: List[str] = []
        target_sig = "BUY" if bias == "Bullish" else "SELL"

        for d in ta_details:
            name = d.get("name", "")
            sig  = d.get("signal", "NEUTRAL")
            val  = d.get("value")
            if sig != target_sig:
                continue

            if name == "MACD":
                arrow = "above" if sig == "BUY" else "below"
                factors.append(f"MACD is {arrow} the signal line, confirming {bias.lower()} momentum.")
            elif "RSI" in name and val is not None:
                factors.append(f"RSI at {val:.1f} supports a {bias.lower()} move ({sig} zone).")
            elif "EMA" in name:
                rel = "above" if sig == "BUY" else "below"
                factors.append(f"Price is {rel} {name}, confirming the prevailing trend.")
            elif name == "Momentum(10)" and val is not None:
                factors.append(f"10-period momentum is {'positive' if sig == 'BUY' else 'negative'} ({val:+.2f}).")
            elif name == "Bollinger Bands":
                if sig == "BUY":
                    factors.append("Price is near the lower Bollinger Band — oversold territory supports a bounce.")
                else:
                    factors.append("Price is near the upper Bollinger Band — overbought territory supports a pullback.")

        # Timeframe alignment support
        align = tf_data.get("alignment", "MIXED")
        if align in ("STRONG_BULL", "STRONG_BEAR"):
            factors.append(f"All three timeframes (4H/1H/15m) are aligned {bias.lower()}.")
        elif align in ("PULLBACK_BULL", "PULLBACK_BEAR"):
            factors.append("Higher timeframes confirm the primary trend direction.")

        # News support
        if bias == "Bullish" and news_score >= 60:
            factors.append(f"News sentiment is supportive ({news_score:.0f}/100 score).")
        elif bias == "Bearish" and news_score <= 40:
            factors.append(f"News sentiment aligns with bearish bias ({news_score:.0f}/100 score).")

        return factors[:5] if factors else ["No strong confirming factors identified."]

    # ── Weakening factors ─────────────────────────────────────────────────────

    def _weakening_factors(
        self,
        bias: str,
        signals: Dict[str, Any],
        ta_details: List[Dict[str, Any]],
        alignment: str,
        regime: str,
        confidence_breakdown: Dict[str, Any],
    ) -> List[str]:
        factors: List[str] = []

        rsi = signals.get("rsi_value")
        if bias == "Bullish" and rsi is not None and rsi > 65:
            factors.append(f"RSI at {rsi:.1f} is approaching overbought — upside momentum may be fading.")
        elif bias == "Bearish" and rsi is not None and rsi < 35:
            factors.append(f"RSI at {rsi:.1f} is approaching oversold — downside pressure may be exhausting.")

        if alignment in ("WEAK_BULL", "WEAK_BEAR"):
            factors.append("1H momentum is weakening relative to 4H trend — setup conviction is lower.")
        elif alignment in ("PULLBACK_BULL", "PULLBACK_BEAR"):
            factors.append("15m timeframe is counter-trend — entry timing requires caution.")
        elif alignment == "TRANSITION":
            factors.append("4H and 1H are in disagreement — trend transition risk is elevated.")

        if regime == "VOLATILE":
            factors.append("Elevated ATR means price swings are wider — stop placement is harder.")
        elif regime == "RANGING":
            factors.append("Range-bound conditions reduce momentum indicator reliability.")

        # Penalty-based weakeners
        for p in confidence_breakdown.get("penalties", []):
            if p.get("points", 0) < -4:
                factors.append(p["reason"])

        news_conf = confidence_breakdown.get("components", {}).get("sentiment", 50.0)
        tech_conf = confidence_breakdown.get("components", {}).get("technical", 50.0)
        if abs(tech_conf - news_conf) > 30:
            factors.append(
                f"Technical ({tech_conf:.0f}) and sentiment ({news_conf:.0f}) scores diverge significantly."
            )

        return factors[:4] if factors else ["No significant weakening factors detected."]

    # ── Invalidation conditions ───────────────────────────────────────────────

    def _invalidation_conditions(
        self,
        bias: str,
        current_price: float,
        ema50_value: Optional[float],
        ta_details: List[Dict[str, Any]],
        structure: str,
    ) -> List[str]:
        conditions: List[str] = []

        if bias == "Bullish":
            if ema50_value:
                conditions.append(
                    f"A daily close below EMA50 ({ema50_value:.2f}) would invalidate the bullish thesis."
                )
            conditions.append("A bearish MACD crossover on the 4H chart would signal momentum reversal.")
            if structure == "HIGHER_HIGHS":
                conditions.append("Formation of a lower high would break the current bullish structure.")

        elif bias == "Bearish":
            if ema50_value:
                conditions.append(
                    f"A daily close above EMA50 ({ema50_value:.2f}) would invalidate the bearish thesis."
                )
            conditions.append("A bullish MACD crossover on the 4H chart would signal momentum reversal.")
            if structure == "LOWER_LOWS":
                conditions.append("Formation of a higher low would break the current bearish structure.")

        else:  # Neutral
            conditions.append(
                f"A decisive break above recent resistance or below recent support "
                f"(current price {current_price:.2f}) will determine the next directional move."
            )

        return conditions

    # ── News drivers ──────────────────────────────────────────────────────────

    def _news_drivers(self, relevant_news: List[Any]) -> List[str]:
        drivers: List[str] = []
        pos, neg = [], []

        for item in relevant_news:
            score = getattr(item, "sentiment_score", 0)
            title = getattr(item, "title", "")
            if score > 0.1:
                pos.append((score, title))
            elif score < -0.1:
                neg.append((score, title))

        pos.sort(key=lambda x: x[0], reverse=True)
        neg.sort(key=lambda x: x[0])

        for _, t in pos[:2]:
            drivers.append(f"+ {t}")
        for _, t in neg[:2]:
            drivers.append(f"- {t}")

        return drivers if drivers else ["No directional news drivers identified."]

    # ── Risk warnings ─────────────────────────────────────────────────────────

    def _risk_warnings(
        self,
        risk_events: Dict[str, Any],
        regime: str,
        signals: Dict[str, Any],
        alignment: str,
    ) -> List[str]:
        warnings: List[str] = []

        for ev in risk_events.get("events", []):
            mins = ev["minutes_away"]
            name = ev["event"]
            impact = ev["impact"]
            if mins <= 0:
                warnings.append(f"ACTIVE EVENT: {name} is currently in progress ({impact} impact).")
            elif mins <= 60:
                warnings.append(f"WARNING: {name} in {mins} min ({impact} impact). {ev['advisory']}")
            else:
                warnings.append(f"CAUTION: {name} in {mins} min ({impact} impact).")

        if regime == "VOLATILE":
            warnings.append("Elevated volatility — widen stops and reduce position size.")

        rsi = signals.get("rsi_value")
        if rsi and rsi > 75:
            warnings.append(f"RSI at {rsi:.1f} — extreme overbought. High reversal risk.")
        elif rsi and rsi < 25:
            warnings.append(f"RSI at {rsi:.1f} — extreme oversold. High bounce risk.")

        if alignment == "MIXED":
            warnings.append("Multi-timeframe signals are completely conflicting. Do not open new positions.")

        return warnings if warnings else ["No significant risk warnings at this time."]


explanation_engine = ExplanationEngine()
