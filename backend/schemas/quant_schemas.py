from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TradeZone(BaseModel):
    min: float
    max: float

class TradePlan(BaseModel):
    entry_zone: Optional[TradeZone] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

class Explanation(BaseModel):
    summary: str
    technical_details: List[str]
    sentiment_details: List[str]

class QuantDecision(BaseModel):
    symbol: str
    timestamp: datetime
    bias: str  # Bullish | Bearish | Neutral
    confidence_score: float  # 0-100
    technical_score: float  # 0-100
    sentiment_score: float  # 0-100
    trade_plan: TradePlan
    explanation: Explanation

class AIQuantSummary(BaseModel):
    symbol: str
    bias: str
    confidence_score: float
    technical_score: float
    news_score: float
    ai_summary: str
    technical_explanation: List[str]
    news_drivers: List[str]
    warnings: List[str]
    trade_outlook: TradePlan

# ── v3 Intelligence Engine Schemas ───────────────────────────────────────────

class RiskEvent(BaseModel):
    event: str
    minutes_away: int
    impact: str            # HIGH | MEDIUM | LOW
    penalty: float
    advisory: str

class RegimeInfo(BaseModel):
    label: str             # STRONG_TREND | WEAK_TREND | RANGING | VOLATILE | NEWS_DRIVEN
    structure: str         # HIGHER_HIGHS | LOWER_LOWS | CONSOLIDATION | etc.
    atr_pct: float
    description: str

class TimeframeBar(BaseModel):
    bias: str              # Bullish | Bearish | Neutral
    score: float           # 0–100

class TimeframeAlignment(BaseModel):
    tf_4h: TimeframeBar
    tf_1h: TimeframeBar
    tf_15m: TimeframeBar
    alignment: str         # STRONG_BULL | PULLBACK_BULL | TRANSITION | MIXED | etc.
    alignment_description: str
    alignment_score: float # 0–100

class ConfidenceComponent(BaseModel):
    technical: float
    sentiment: float
    timeframe_alignment: float
    regime: float

class RiskPenalty(BaseModel):
    reason: str
    points: float

class ConfidenceBreakdown(BaseModel):
    total: float
    components: ConfidenceComponent
    applied_regime: str
    regime_modifiers: dict
    raw_before_penalty: float
    penalties: List[RiskPenalty]
    explanation: str

class ExplanationBlock(BaseModel):
    ai_summary: str
    regime_context: str
    supporting_factors: List[str]
    weakening_factors: List[str]
    invalidation_conditions: List[str]
    news_drivers: List[str]
    risk_warnings: List[str]
    confidence_explanation: str

class QuantSummaryV3(BaseModel):
    """Full v3 response — the primary endpoint output."""
    symbol: str
    timestamp: datetime
    bias: str              # Bullish | Bearish | Neutral
    trade_state: str       # TRADE | WAIT | NO_TRADE
    trade_state_reasons: List[str]
    confidence: ConfidenceBreakdown
    regime: RegimeInfo
    timeframes: TimeframeAlignment
    explanation: ExplanationBlock
    risk_events: List[RiskEvent]
    trade_outlook: TradePlan

# ── Adaptive Intelligence System Schemas ─────────────────────────────────────

class PredictionSnapshot(BaseModel):
    """A single prediction stored to memory before the outcome is known."""
    id: Optional[int] = None
    symbol: str
    timestamp: datetime
    bias: str
    confidence_score: float
    technical_score: float
    news_score: float
    rsi_value: Optional[float] = None
    macd_signal: Optional[str] = None
    ema_trend: Optional[str] = None
    momentum_signal: Optional[str] = None
    bb_signal: Optional[str] = None
    market_regime: Optional[str] = None
    atr_pct: Optional[float] = None
    price_at_prediction: float
    active_setups: List[str] = []

class OutcomeRecord(BaseModel):
    """Actual price outcome evaluated after a prediction horizon."""
    id: Optional[int] = None
    prediction_id: int
    horizon: str             # 15m | 1h | 4h
    price_at_outcome: float
    price_change_pct: float
    outcome: str             # CORRECT | INCORRECT | NEUTRAL
    evaluated_at: datetime

class SetupStats(BaseModel):
    """Aggregated performance for a named setup pattern."""
    setup_name: str
    symbol: str
    total_predictions: int
    correct_count: int
    incorrect_count: int
    neutral_count: int
    win_rate: float          # 0.0–1.0
    avg_return_pct: float
    last_updated: Optional[datetime] = None

class AdaptiveWeight(BaseModel):
    """A single adaptive weight stored in the DB."""
    weight_key: str
    symbol: str              # GLOBAL or specific symbol
    value: float
    default_value: float
    last_updated: Optional[datetime] = None

class WeightHistory(BaseModel):
    """Log entry for every weight change made by the optimizer."""
    id: Optional[int] = None
    weight_key: str
    symbol: str
    old_value: float
    new_value: float
    reason: str
    changed_at: datetime

# ── API Response Schemas ──────────────────────────────────────────────────────

class MemoryResponse(BaseModel):
    symbol: str
    total_stored: int
    predictions: List[PredictionSnapshot]

class OutcomesResponse(BaseModel):
    symbol: str
    outcomes: List[OutcomeRecord]

class PerformanceResponse(BaseModel):
    symbol: str
    setups: List[SetupStats]
    overall_win_rate: float
    total_evaluated: int

class WeightsResponse(BaseModel):
    weights: List[AdaptiveWeight]
    recent_changes: List[WeightHistory]

