"""
schemas/paper_trading_schemas.py — Pydantic models for the Paper Trading simulator.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


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
