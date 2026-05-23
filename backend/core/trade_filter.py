"""
trade_filter.py — NO_TRADE / WAIT / TRADE Decision Engine
Single-responsibility: given all analysis outputs, determine whether to act.
Every decision comes with explicit, human-readable reasons.
"""
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

TRADE    = "TRADE"
WAIT     = "WAIT"
NO_TRADE = "NO_TRADE"

# Thresholds
NO_TRADE_CONFIDENCE_FLOOR  = 45.0
WAIT_CONFIDENCE_FLOOR      = 58.0
HIGH_IMPACT_EVENT_WINDOW_M = 60    # minutes: block new trades this close to event
PENALTY_NO_TRADE_THRESHOLD = -15.0  # total penalties this severe → no trade


class TradeFilter:
    """
    Evaluates all engine outputs and returns a trade state with reasons.
    Rules are checked in priority order; first applicable rule wins the label,
    but ALL reasons are collected and returned for full transparency.
    """

    def evaluate(
        self,
        bias: str,
        confidence_breakdown: Dict[str, Any],
        regime: str,
        alignment: str,
        structure: str,
        risk_events: Dict[str, Any],
        indicator_signals: Dict[str, Any],
        ta_summary: Dict[str, Any],
    ) -> Tuple[str, List[str]]:
        """
        Returns (trade_state, reasons_list).
        trade_state: TRADE | WAIT | NO_TRADE
        reasons_list: human-readable explanations
        """
        final_conf     = confidence_breakdown.get("total", 50.0)
        raw_conf       = confidence_breakdown.get("raw_before_penalty", 50.0)
        penalties      = confidence_breakdown.get("penalties", [])
        total_penalty  = sum(p.get("points", 0) for p in penalties)

        no_trade_reasons: List[str] = []
        wait_reasons:     List[str] = []

        # ── NO_TRADE rules ────────────────────────────────────────────────────

        # Rule NT-1: Confidence below floor
        if final_conf < NO_TRADE_CONFIDENCE_FLOOR:
            no_trade_reasons.append(
                f"Confidence ({final_conf:.1f}) is below the minimum threshold "
                f"({NO_TRADE_CONFIDENCE_FLOOR}). Setup lacks conviction."
            )

        # Rule NT-2: Timeframes completely mixed
        if alignment == "MIXED":
            no_trade_reasons.append(
                "Timeframe alignment is MIXED — all three timeframes (4H/1H/15m) "
                "are pointing in different directions. No coherent trend to trade."
            )

        # Rule NT-3: Volatile regime + insufficient confidence
        if regime == "VOLATILE" and final_conf < 60.0:
            no_trade_reasons.append(
                f"Market is in a VOLATILE regime with confidence only {final_conf:.1f}. "
                "Elevated risk requires ≥60% confidence to proceed."
            )

        # Rule NT-4: Severe combined penalty
        if total_penalty <= PENALTY_NO_TRADE_THRESHOLD:
            no_trade_reasons.append(
                f"Combined risk penalties ({total_penalty:+.0f} pts) exceed the "
                f"safety threshold ({PENALTY_NO_TRADE_THRESHOLD}). Too many risks active simultaneously."
            )

        # Rule NT-5: High-impact event imminent
        nearest_min = risk_events.get("nearest_event_minutes")
        has_high    = risk_events.get("has_high_impact", False)
        if has_high and nearest_min is not None and nearest_min <= HIGH_IMPACT_EVENT_WINDOW_M:
            no_trade_reasons.append(
                f"High-impact market event in {nearest_min} minutes. "
                "Position opening blocked until event window clears."
            )

        # Rule NT-6: Overbought at resistance (bullish entry attempt at extreme)
        rsi = indicator_signals.get("rsi_value")
        if (bias == "Bullish"
                and rsi is not None
                and rsi > 75
                and structure == "RESISTANCE_REJECT"):
            no_trade_reasons.append(
                f"RSI at {rsi:.1f} (extremely overbought) with price rejecting resistance. "
                "Entry here carries very high reversal risk."
            )

        # Rule NT-7: Oversold at support in bearish setup
        if (bias == "Bearish"
                and rsi is not None
                and rsi < 25
                and structure == "SUPPORT_HOLD"):
            no_trade_reasons.append(
                f"RSI at {rsi:.1f} (extremely oversold) with price holding support. "
                "Short entry here carries very high bounce risk."
            )

        # Rule NT-8: TA/News divergence on news-driven regime with weak news
        news_conf = confidence_breakdown.get("components", {}).get("sentiment", 50.0)
        if regime == "NEWS_DRIVEN" and news_conf < 40.0:
            no_trade_reasons.append(
                "Regime is NEWS_DRIVEN but news sentiment score is bearish/weak. "
                "Cannot determine direction while news and technicals diverge."
            )

        # ── If any NO_TRADE rule triggered → return immediately ───────────────
        if no_trade_reasons:
            return NO_TRADE, no_trade_reasons

        # ── WAIT rules ────────────────────────────────────────────────────────

        # Rule W-1: Confidence in wait zone
        if final_conf < WAIT_CONFIDENCE_FLOOR:
            wait_reasons.append(
                f"Confidence ({final_conf:.1f}) is below the preferred entry threshold "
                f"({WAIT_CONFIDENCE_FLOOR}). Monitor for confirmation before committing."
            )

        # Rule W-2: Pullback in progress — wait for completion
        if alignment in ("PULLBACK_BULL", "PULLBACK_BEAR"):
            direction = "bullish" if alignment == "PULLBACK_BULL" else "bearish"
            wait_reasons.append(
                f"Market is in a {direction} pullback ({alignment}). "
                "Wait for the short-term corrective move to complete before entering."
            )

        # Rule W-3: Weak trend
        if regime == "WEAK_TREND":
            wait_reasons.append(
                "Market is in a WEAK_TREND — momentum is fading. "
                "Trend may continue or reverse; wait for re-confirmation."
            )

        # Rule W-4: Consolidation — breakout pending
        if structure == "CONSOLIDATION":
            wait_reasons.append(
                "Price is in tight CONSOLIDATION. "
                "Wait for a decisive breakout with volume before entering."
            )

        # Rule W-5: Transition phase between timeframes
        if alignment == "TRANSITION":
            wait_reasons.append(
                "4H and 1H timeframes are in disagreement (TRANSITION). "
                "Trend change may be forming — wait for higher timeframe clarity."
            )

        # Rule W-6: Regime = NEWS_DRIVEN with moderate confidence
        if regime == "NEWS_DRIVEN" and final_conf < 65.0:
            wait_reasons.append(
                "Regime is NEWS_DRIVEN with moderate confidence. "
                "Wait for news volatility to settle before committing."
            )

        if wait_reasons:
            return WAIT, wait_reasons

        # ── TRADE ─────────────────────────────────────────────────────────────
        return TRADE, [
            f"Setup quality is sufficient: confidence {final_conf:.1f}, "
            f"regime {regime}, alignment {alignment}."
        ]


trade_filter = TradeFilter()
