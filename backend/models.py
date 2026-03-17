"""
Data models for the Stock Signal Application
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SignalType(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class SentimentType(str, Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"

class TechnicalIndicators(BaseModel):
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    obv: Optional[float] = None
    volume_sma: Optional[float] = None

class StockData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    prev_close: float
    timestamp: datetime
    indicators: Optional[TechnicalIndicators] = None
    category: Optional[str] = None  # market category tag e.g. "🇮🇳 India", "🔷 Crypto"

class Signal(BaseModel):
    symbol: str
    signal_type: SignalType
    strength: float  # 0-100
    reasons: List[str]
    technical_score: float
    sentiment_score: float
    timestamp: datetime

class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published: datetime
    sentiment: SentimentType
    sentiment_score: float
    related_symbols: List[str]
    category: str = "General"
    source_weight: float = 1.0

class MarketSentiment(BaseModel):
    overall_sentiment: SentimentType
    sentiment_score: float  # -1 to 1
    bullish_count: int
    bearish_count: int
    neutral_count: int
    news_items: List[NewsItem]
    last_updated: datetime
    asset_sentiments: Optional[Dict[str, Any]] = None  # Level 2: per-asset scores

class OptionsData(BaseModel):
    symbol: str
    expiry: str
    strike: float
    option_type: str  # CE or PE
    ltp: float
    change: float
    volume: int
    oi: int
    iv: Optional[float] = None

class OptionsChain(BaseModel):
    symbol: str
    spot_price: float
    expiry_dates: List[str]
    pcr: float  # Put-Call Ratio
    max_pain: float
    calls: List[OptionsData]
    puts: List[OptionsData]
    timestamp: datetime

class MarketOverview(BaseModel):
    nifty: StockData
    banknifty: StockData
    sensex: StockData
    top_gainers: List[StockData]
    top_losers: List[StockData]
    most_active: List[StockData]
    market_sentiment: MarketSentiment
    signals: List[Signal]
    timestamp: datetime

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime

# ── PAPER TRADING PHASE 1 MODELS ──────────────────────────────────────────────

class AssetType(str, Enum):
    STOCK = "stock"
    FOREX = "forex"
    COMMODITY = "commodity"
    CRYPTO = "crypto"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"

class OrderStatus(str, Enum):
    EXECUTED = "executed"
    REJECTED = "rejected"

class PaperOrderRequest(BaseModel):
    symbol: str
    asset_type: AssetType
    side: OrderSide
    quantity: float
    stop_loss: float
    target: float
    timeframe: Optional[str] = "1d"

class PaperPosition(BaseModel):
    id: str
    symbol: str
    asset_type: AssetType
    side: OrderSide
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float
    target: float
    pnl: float
    pnl_percent: float
    status: PositionStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    close_reason: Optional[str] = None
    timeframe: Optional[str] = "1d"

class PaperAccount(BaseModel):
    initial_capital: float
    available_capital: float
    realized_pnl: float
    unrealized_pnl: float
    total_equity: float

class TradeHistoryItem(BaseModel):
    id: str
    symbol: str
    asset_type: AssetType
    side: OrderSide
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    opened_at: datetime
    closed_at: datetime
    close_reason: str

class OrderLogItem(BaseModel):
    id: str
    symbol: str
    asset_type: AssetType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    status: OrderStatus
    message: str
    placed_at: datetime
    timeframe: Optional[str] = "1d"
