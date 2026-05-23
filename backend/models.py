"""
models.py — Backward-compatible re-export shim.

All model definitions now live in schemas/. This file re-exports every symbol
so that any existing code doing `from models import X` continues to work
without modification.
"""
# ruff: noqa: F401  (re-exports are intentional)
from schemas.market_schemas import (
    SignalType,
    SentimentType,
    TechnicalIndicators,
    StockData,
    Signal,
    NewsItem,
    MarketSentiment,
    OptionsData,
    OptionsChain,
    MarketOverview,
    WebSocketMessage,
)
from schemas.paper_trading_schemas import (
    AssetType,
    OrderSide,
    PositionStatus,
    OrderStatus,
    PaperOrderRequest,
    PaperPosition,
    PaperAccount,
    TradeHistoryItem,
    OrderLogItem,
)

__all__ = [
    # Market / signal models
    "SignalType", "SentimentType", "TechnicalIndicators",
    "StockData", "Signal", "NewsItem", "MarketSentiment",
    "OptionsData", "OptionsChain", "MarketOverview", "WebSocketMessage",
    # Paper-trading models
    "AssetType", "OrderSide", "PositionStatus", "OrderStatus",
    "PaperOrderRequest", "PaperPosition", "PaperAccount",
    "TradeHistoryItem", "OrderLogItem",
]
