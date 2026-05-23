"""
quant_engine.py — Orchestrator for the Quant Intelligence Engine v3
Coordinates all analysis modules and produces both v2 (AIQuantSummary)
and v3 (QuantSummaryV3) responses.

v3 pipeline:
  data_fetcher → indicator_engine → market_context → timeframe_engine
  → risk_engine → confidence_engine → trade_filter → explanation_engine
  → memory_engine (snapshot store)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
import pandas as pd
from typing import Dict, Any, Optional

from data_fetcher import data_fetcher
from indicator_engine import indicator_engine
from sentiment_analysis import sentiment_analyzer
from news_pipeline import build_news_pipeline
from schemas.quant_schemas import (
    QuantDecision, TradePlan, TradeZone, Explanation,
    AIQuantSummary, QuantSummaryV3,
    RegimeInfo, TimeframeAlignment, TimeframeBar,
    ConfidenceBreakdown, ConfidenceComponent, RiskPenalty,
    ExplanationBlock, RiskEvent,
)
from schemas.market_schemas import NewsItem
from core.summary_engine import summary_engine          # v2 compatibility
from core.memory_engine import memory_engine
from core.pattern_tracker import pattern_tracker
from core.confidence_optimizer import confidence_optimizer  # adaptive weight nudger
from core.market_context import market_context
from core.timeframe_engine import timeframe_engine
from core.risk_engine import risk_engine
from core.confidence_engine import confidence_engine
from core.trade_filter import trade_filter
from core.explanation_engine import explanation_engine

logger = logging.getLogger(__name__)


class QuantEngine:

    def __init__(self):
        self._last_news_fetch: Optional[datetime] = None
        self._news_cache: list = []
        self._news_cache_ttl = 300    # 5 minutes

    # ── Shared helpers ────────────────────────────────────────────────────────

    async def _get_recent_news(self) -> list:
        now = datetime.now(timezone.utc)
        if (not self._last_news_fetch
                or (now - self._last_news_fetch).total_seconds() > self._news_cache_ttl):
            logger.info("[QuantEngine] Fetching fresh news for sentiment analysis")
            raw_news = await build_news_pipeline()
            news_items = []
            for n in raw_news:
                try:
                    score = (
                        sentiment_analyzer.analyze_text(n.get("title", ""))
                        + sentiment_analyzer.analyze_text(n.get("summary", ""))
                    )
                    stype = sentiment_analyzer.get_sentiment_type(score)
                    item  = NewsItem(
                        title=n.get("title", ""),
                        source=n.get("source", "Unknown"),
                        url=n.get("url", ""),
                        published=n.get("published", now),
                        sentiment=stype,
                        sentiment_score=score,
                        related_symbols=sentiment_analyzer.extract_related_symbols(n.get("title", "")),
                        category=n.get("category", "General"),
                        source_weight=n.get("source_weight", 1.0),
                    )
                    news_items.append(item)
                except Exception as e:
                    logger.warning(f"Failed to parse news item: {e}")
            self._news_cache        = news_items
            self._last_news_fetch   = now
        return self._news_cache

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high_low   = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close  = (df["Low"]  - df["Close"].shift()).abs()
        tr  = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr) if not pd.isna(atr) else float(df["High"].iloc[-1] - df["Low"].iloc[-1])

    def _extract_ema50(self, df: pd.DataFrame) -> Optional[float]:
        try:
            ema50 = df["Close"].ewm(span=50, adjust=False).mean()
            return round(float(ema50.iloc[-1]), 4)
        except Exception:
            return None

    def _build_trade_plan(self, bias: str, current_price: float, atr: float) -> TradePlan:
        plan = TradePlan()
        if bias == "Bullish":
            denom = current_price - (current_price - 1.5 * atr)
            plan.entry_zone        = TradeZone(min=current_price * 0.998, max=current_price * 1.002)
            plan.stop_loss         = round(current_price - 1.5 * atr, 2)
            plan.target_1          = round(current_price + 2.0 * atr, 2)
            plan.target_2          = round(current_price + 4.0 * atr, 2)
            plan.risk_reward_ratio = round((2.0 * atr) / (1.5 * atr), 2) if denom > 0 else None
        elif bias == "Bearish":
            plan.entry_zone        = TradeZone(min=current_price * 0.998, max=current_price * 1.002)
            plan.stop_loss         = round(current_price + 1.5 * atr, 2)
            plan.target_1          = round(current_price - 2.0 * atr, 2)
            plan.target_2          = round(current_price - 4.0 * atr, 2)
            plan.risk_reward_ratio = round((2.0 * atr) / (1.5 * atr), 2)
        return plan

    # ── v2 endpoint (preserved for backwards compatibility) ───────────────────

    async def analyze_symbol(self, symbol: str) -> QuantDecision:
        df = await data_fetcher.fetch_stock_data(symbol, period="3mo", interval="1d")
        if df is None or df.empty:
            raise ValueError(f"Could not fetch historical data for {symbol}")

        news_items        = await self._get_recent_news()
        sentiment_summary = sentiment_analyzer.get_asset_sentiment(symbol, news_items)
        raw_sent          = sentiment_summary.get("sentiment_score", 0.0)
        sentiment_score_100 = (raw_sent + 1.0) / 2.0 * 100.0

        ta_summary  = indicator_engine.generate_technical_summary(df)
        total_sigs  = ta_summary["buy"] + ta_summary["sell"] + ta_summary["neutral"]
        net         = ta_summary["buy"] - ta_summary["sell"]
        ta_score_100 = ((net / total_sigs + 1.0) / 2.0 * 100.0) if total_sigs else 50.0
        confidence   = ta_score_100 * 0.70 + sentiment_score_100 * 0.30

        bias = "Bullish" if confidence >= 60 else ("Bearish" if confidence <= 40 else "Neutral")
        current_price = float(df["Close"].iloc[-1])
        atr           = self._calculate_atr(df)
        trade_plan    = self._build_trade_plan(bias, current_price, atr)

        tech_bullets = [
            f"{d['name']} indicates a {d['signal']} signal (Value: {d['value']})."
            for d in ta_summary.get("details", []) if d["signal"] != "NEUTRAL"
        ] or ["Indicators are mostly neutral."]

        rel_news = sentiment_summary.get("relevant_news_count", 0)
        sent_bullets = (
            [
                f"Analyzed {rel_news} recent news articles.",
                f"Overall sentiment is {sentiment_summary.get('sentiment_type')} "
                f"(Score: {sentiment_score_100:.1f}/100).",
            ]
            if rel_news > 0
            else ["No highly relevant recent news found."]
        )

        return QuantDecision(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            bias=bias,
            confidence_score=round(confidence, 1),
            technical_score=round(ta_score_100, 1),
            sentiment_score=round(sentiment_score_100, 1),
            trade_plan=trade_plan,
            explanation=Explanation(
                summary=f"The model exhibits a {bias} bias ({confidence:.1f}% confidence).",
                technical_details=tech_bullets[:4],
                sentiment_details=sent_bullets,
            ),
        )

    # ── v3 primary endpoint ───────────────────────────────────────────────────

    async def generate_full_summary(self, symbol: str) -> QuantSummaryV3:
        """
        Full v3 pipeline:
        Fetch → TA → Sentiment → Regime → Timeframes → Risk →
        Confidence → TradeFilter → Explanation → MemoryStore
        """
        now = datetime.now(timezone.utc)

        # ── 1. Fetch daily data ───────────────────────────────────────────────
        df = await data_fetcher.fetch_stock_data(symbol, period="3mo", interval="1d")
        if df is None or df.empty:
            raise ValueError(f"No price data available for {symbol}")

        current_price = float(df["Close"].iloc[-1])
        atr           = self._calculate_atr(df)
        atr_pct       = round((atr / current_price) * 100.0, 4) if current_price else 1.0
        ema50         = self._extract_ema50(df)

        # ── 2. Technical indicators ───────────────────────────────────────────
        ta_summary        = indicator_engine.generate_technical_summary(df)
        indicator_signals = pattern_tracker.extract_indicator_signals(ta_summary.get("details", []))

        # ── 3. News + sentiment ───────────────────────────────────────────────
        news_items    = await self._get_recent_news()
        relevant_news = [n for n in news_items if sentiment_analyzer.is_news_relevant_to_symbol(symbol, n)]
        sent_summary  = sentiment_analyzer.get_asset_sentiment(symbol, news_items)
        news_score_100 = (sent_summary.get("sentiment_score", 0.0) + 1.0) / 2.0 * 100.0

        # ── 4. Market regime + structure ──────────────────────────────────────
        total_sigs  = ta_summary["buy"] + ta_summary["sell"] + ta_summary["neutral"]
        ta_score_100 = (
            ((ta_summary["buy"] - ta_summary["sell"]) / total_sigs + 1.0) / 2.0 * 100.0
            if total_sigs else 50.0
        )
        regime_data = market_context.classify_regime(
            df=df,
            indicator_signals=indicator_signals,
            news_score=news_score_100,
            technical_score=ta_score_100,
            symbol=symbol,
        )
        regime    = regime_data["label"]
        structure = regime_data["structure"]

        # ── 5. Multi-timeframe alignment ──────────────────────────────────────
        tf_data = await timeframe_engine.analyze(symbol)
        alignment       = tf_data["alignment"]
        alignment_score = tf_data["alignment_score"]
        alignment_desc  = tf_data["alignment_description"]

        # ── 6. Risk events ────────────────────────────────────────────────────
        risk_data = risk_engine.get_risk_events(symbol, now)

        # ── 7. Adaptive weights from memory ───────────────────────────────────
        adaptive_weights = {
            k: memory_engine.get_weight(k, "GLOBAL")
            for k in ["RSI_MULTIPLIER", "MACD_MULTIPLIER", "EMA_MULTIPLIER",
                      "MOMENTUM_MULTIPLIER", "BB_MULTIPLIER"]
        }

        # ── 8. Decomposed confidence ──────────────────────────────────────────
        conf_data = confidence_engine.compute(
            indicator_signals = indicator_signals,
            news_score_100    = news_score_100,
            alignment_score   = alignment_score,
            regime            = regime,
            risk_events       = risk_data,
            adaptive_weights  = adaptive_weights,
            ta_summary        = ta_summary,
        )
        final_confidence = conf_data["total"]

        # ── 9. Bias from final confidence ────────────────────────────────────
        if final_confidence >= 60.0:
            bias = "Bullish"
        elif final_confidence <= 40.0:
            bias = "Bearish"
        else:
            bias = "Neutral"

        # ── 10. Trade state ────────────────────────────────────────────────────
        trade_state, ts_reasons = trade_filter.evaluate(
            bias                  = bias,
            confidence_breakdown  = conf_data,
            regime                = regime,
            alignment             = alignment,
            structure             = structure,
            risk_events           = risk_data,
            indicator_signals     = indicator_signals,
            ta_summary            = ta_summary,
        )

        # ── 11. Trade plan ────────────────────────────────────────────────────
        trade_plan = self._build_trade_plan(bias, current_price, atr)

        # ── 12. Explanation ────────────────────────────────────────────────────
        explanation_data = explanation_engine.generate(
            bias                  = bias,
            confidence_breakdown  = conf_data,
            regime                = regime,
            structure             = structure,
            alignment             = alignment,
            alignment_description = alignment_desc,
            indicator_signals     = indicator_signals,
            ta_details            = ta_summary.get("details", []),
            ta_summary            = ta_summary,
            tf_data               = tf_data,
            news_score_100        = news_score_100,
            relevant_news         = relevant_news,
            risk_events           = risk_data,
            trade_state           = trade_state,
            current_price         = current_price,
            ema50_value           = ema50,
        )

        # ── 13. Store prediction snapshot ─────────────────────────────────────
        active_setups = pattern_tracker.detect_setups({
            "symbol": symbol, "bias": bias,
            "confidence_score": final_confidence,
            "technical_score": round(ta_score_100, 1),
            "news_score": round(news_score_100, 1),
            "market_regime": regime, "atr_pct": atr_pct,
            **indicator_signals,
        })
        snapshot_row = {
            "symbol":             symbol,
            "timestamp":          now.isoformat(),
            "bias":               bias,
            "confidence_score":   final_confidence,
            "technical_score":    round(ta_score_100, 1),
            "news_score":         round(news_score_100, 1),
            "market_regime":      regime,
            "atr_pct":            atr_pct,
            "price_at_prediction": round(current_price, 4),
            "active_setups":      json.dumps(active_setups),
            **indicator_signals,
        }
        pred_id = memory_engine.store_prediction(snapshot_row)
        logger.info(f"[QuantEngine-v3] Stored prediction id={pred_id} for {symbol} — {bias} / {trade_state}")

        # ── 14. Assemble QuantSummaryV3 ───────────────────────────────────────
        return QuantSummaryV3(
            symbol      = symbol,
            timestamp   = now,
            bias        = bias,
            trade_state = trade_state,
            trade_state_reasons = ts_reasons,

            confidence  = ConfidenceBreakdown(
                total             = conf_data["total"],
                components        = ConfidenceComponent(
                    technical           = conf_data["components"]["technical"],
                    sentiment           = conf_data["components"]["sentiment"],
                    timeframe_alignment = conf_data["components"]["timeframe_alignment"],
                    regime              = conf_data["components"]["regime"],
                ),
                applied_regime    = conf_data["applied_regime"],
                regime_modifiers  = conf_data["regime_modifiers"],
                raw_before_penalty= conf_data["raw_before_penalty"],
                penalties         = [
                    RiskPenalty(reason=p["reason"], points=p["points"])
                    for p in conf_data["penalties"]
                ],
                explanation       = conf_data["explanation"],
            ),

            regime      = RegimeInfo(
                label       = regime_data["label"],
                structure   = regime_data["structure"],
                atr_pct     = regime_data["atr_pct"],
                description = regime_data["description"],
            ),

            timeframes  = TimeframeAlignment(
                tf_4h   = TimeframeBar(**tf_data["tf_4h"]),
                tf_1h   = TimeframeBar(**tf_data["tf_1h"]),
                tf_15m  = TimeframeBar(**tf_data["tf_15m"]),
                alignment             = tf_data["alignment"],
                alignment_description = tf_data["alignment_description"],
                alignment_score       = tf_data["alignment_score"],
            ),

            explanation = ExplanationBlock(
                ai_summary              = explanation_data["ai_summary"],
                regime_context          = explanation_data["regime_context"],
                supporting_factors      = explanation_data["supporting_factors"],
                weakening_factors       = explanation_data["weakening_factors"],
                invalidation_conditions = explanation_data["invalidation_conditions"],
                news_drivers            = explanation_data["news_drivers"],
                risk_warnings           = explanation_data["risk_warnings"],
                confidence_explanation  = explanation_data["confidence_explanation"],
            ),

            risk_events = [
                RiskEvent(
                    event       = e["event"],
                    minutes_away= e["minutes_away"],
                    impact      = e["impact"],
                    penalty     = e["penalty"],
                    advisory    = e["advisory"],
                )
                for e in risk_data["events"]
            ],

            trade_outlook = trade_plan,
        )

    # ── v2 shim: generate_ai_summary calls the new engine and converts ────────

    async def generate_ai_summary(self, symbol: str) -> AIQuantSummary:
        """
        v2 compatibility shim. Delegates to generate_full_summary() and
        converts the v3 response back to the AIQuantSummary schema.
        """
        v3 = await self.generate_full_summary(symbol)
        return AIQuantSummary(
            symbol               = v3.symbol,
            bias                 = v3.bias,
            confidence_score     = v3.confidence.total,
            technical_score      = v3.confidence.components.technical,
            news_score           = v3.confidence.components.sentiment,
            ai_summary           = v3.explanation.ai_summary,
            technical_explanation= v3.explanation.supporting_factors,
            news_drivers         = v3.explanation.news_drivers,
            warnings             = v3.explanation.risk_warnings,
            trade_outlook        = v3.trade_outlook,
        )


quant_engine = QuantEngine()
