"""
paper_trade.py — In-Memory Paper Trading Simulator
Phase 1 implementation for stocks, forex, and commodities.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import asyncio
from models import (
    AssetType, OrderSide, PositionStatus, OrderStatus, 
    PaperOrderRequest, PaperPosition, PaperAccount, TradeHistoryItem,
    OrderLogItem
)
from data_fetcher import data_fetcher

logger = logging.getLogger(__name__)

# Metadata dictionary for supported assets Phase 1
SUPPORTED_ASSETS = {
    # Indian Stocks
    "RELIANCE.NS": {"asset_type": AssetType.STOCK, "multiplier": 1},
    "TCS.NS": {"asset_type": AssetType.STOCK, "multiplier": 1},
    "INFY.NS": {"asset_type": AssetType.STOCK, "multiplier": 1},
    # Commodities
    "CL=F": {"asset_type": AssetType.COMMODITY, "multiplier": 1},
    "BZ=F": {"asset_type": AssetType.COMMODITY, "multiplier": 1},
    "NG=F": {"asset_type": AssetType.COMMODITY, "multiplier": 1},
    "GC=F": {"asset_type": AssetType.COMMODITY, "multiplier": 1},
    # Forex
    "USDINR=X": {"asset_type": AssetType.FOREX, "multiplier": 1},
    "EURUSD=X": {"asset_type": AssetType.FOREX, "multiplier": 1},
    "GBPUSD=X": {"asset_type": AssetType.FOREX, "multiplier": 1},
    "USDJPY=X": {"asset_type": AssetType.FOREX, "multiplier": 1},
}

async def get_latest_price(symbol: str) -> float:
    """Fetch latest price using existing data_fetcher."""
    try:
        data = await data_fetcher.get_historical_data(symbol, period="5d", interval="1m")
        if data and len(data) > 0:
             return data[-1]["close"]
        # Fallback to get_stock_info
        stock_info = await data_fetcher.get_stock_info(symbol)
        if stock_info and stock_info.price > 0:
             return stock_info.price
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
    raise ValueError(f"Could not fetch valid price for {symbol}")

class PaperTradingEngine:
    def __init__(self):
        self.initial_capital = 100000.0
        self.available_capital = 100000.0
        self.open_positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[TradeHistoryItem] = []
        self.order_history: List[OrderLogItem] = []
        self._lock = asyncio.Lock()
    
    def calculate_position_pnl(self, position: PaperPosition, current_price: float) -> Tuple[float, float]:
        if position.side == OrderSide.BUY:
            pnl = (current_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - current_price) * position.quantity
        
        cost_basis = position.entry_price * position.quantity
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        return pnl, pnl_percent

    async def place_order(self, req: PaperOrderRequest) -> PaperPosition:
        async with self._lock:
            # We will generate an ID early so we can log it
            order_id = str(uuid.uuid4())[:8]
            
            try:
                # Validate Quantity & Logic
                if req.quantity <= 0:
                    raise ValueError("Quantity must be greater than 0")
                if req.stop_loss <= 0 or req.target <= 0:
                    raise ValueError("Stop loss and target must be positive")
                
                current_price = await get_latest_price(req.symbol)
                
                if req.side == OrderSide.BUY:
                    if req.stop_loss >= current_price:
                        raise ValueError(f"BUY order: Stop loss ({req.stop_loss:.2f}) must be below entry ({current_price:.2f})")
                    if req.target <= current_price:
                        raise ValueError(f"BUY order: Target ({req.target:.2f}) must be above entry ({current_price:.2f})")
                else:
                    if req.stop_loss <= current_price:
                        raise ValueError(f"SELL order: Stop loss ({req.stop_loss:.2f}) must be above entry ({current_price:.2f})")
                    if req.target >= current_price:
                        raise ValueError(f"SELL order: Target ({req.target:.2f}) must be below entry ({current_price:.2f})")
                
                # Capital check
                required_capital = current_price * req.quantity
                if required_capital > self.available_capital:
                    raise ValueError(f"Insufficient capital. Required: {required_capital:,.2f}, Available: {self.available_capital:,.2f}")
                
            except ValueError as e:
                # Log rejected order
                self.order_history.append(OrderLogItem(
                    id=order_id, symbol=req.symbol, asset_type=req.asset_type,
                    side=req.side, quantity=req.quantity, price=None,
                    status=OrderStatus.REJECTED, message=str(e),
                    placed_at=datetime.now(timezone.utc), timeframe=req.timeframe
                ))
                raise e
            
            # Execute
            self.available_capital -= required_capital
            
            # Log executed order
            self.order_history.append(OrderLogItem(
                id=order_id, symbol=req.symbol, asset_type=req.asset_type,
                side=req.side, quantity=req.quantity, price=current_price,
                status=OrderStatus.EXECUTED, message="Order executed successfully",
                placed_at=datetime.now(timezone.utc), timeframe=req.timeframe
            ))
            
            pos = PaperPosition(
                id=order_id,
                symbol=req.symbol,
                asset_type=req.asset_type,
                side=req.side,
                quantity=req.quantity,
                entry_price=current_price,
                current_price=current_price,
                stop_loss=req.stop_loss,
                target=req.target,
                pnl=0.0,
                pnl_percent=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                timeframe=req.timeframe
            )
            
            self.open_positions[pos.id] = pos
            return pos
            
    async def update_positions(self) -> None:
        async with self._lock:
            if not self.open_positions:
                return
            
            # Group by symbol to minimize fetches
            symbols = list(set(pos.symbol for pos in self.open_positions.values()))
            
            # Fetch prices concurrently
            async def safe_fetch(sym: str):
                try:
                    return sym, await get_latest_price(sym)
                except:
                    return sym, None
            
            results = await asyncio.gather(*(safe_fetch(s) for s in symbols))
            price_map = {sym: price for sym, price in results if price is not None}
            
            to_close = []
            
            for pid, pos in self.open_positions.items():
                current_price = price_map.get(pos.symbol)
                if not current_price:
                     continue
                
                pos.current_price = current_price
                pnl, pnl_pct = self.calculate_position_pnl(pos, current_price)
                pos.pnl = pnl
                pos.pnl_percent = pnl_pct
                
                hit = False
                reason = ""
                if pos.side == OrderSide.BUY:
                    if current_price <= pos.stop_loss:
                         hit, reason = True, "SL HIT"
                    elif current_price >= pos.target:
                         hit, reason = True, "TARGET HIT"
                else:
                    if current_price >= pos.stop_loss:
                         hit, reason = True, "SL HIT"
                    elif current_price <= pos.target:
                         hit, reason = True, "TARGET HIT"
                         
                if hit:
                    to_close.append((pid, reason))
                    
            # Auto-close triggered positions
            for pid, reason in to_close:
                 self._close_position_internal(pid, reason)
                 
    async def close_position(self, position_id: str, reason: str = "MANUAL") -> TradeHistoryItem:
        async with self._lock:
             if position_id not in self.open_positions:
                 raise ValueError(f"Position {position_id} not found")
             
             # Fetch absolute latest price for manual close
             pos = self.open_positions[position_id]
             current_price = await get_latest_price(pos.symbol)
             pos.current_price = current_price
             pnl, pnl_pct = self.calculate_position_pnl(pos, current_price)
             pos.pnl = pnl
             pos.pnl_percent = pnl_pct
             
             return self._close_position_internal(position_id, reason)
             
    def _close_position_internal(self, position_id: str, reason: str) -> TradeHistoryItem:
         pos = self.open_positions.pop(position_id)
         
         # Release capital
         cost_basis = pos.entry_price * pos.quantity
         self.available_capital += (cost_basis + pos.pnl)
         
         pos.status = PositionStatus.CLOSED
         pos.closed_at = datetime.now(timezone.utc)
         pos.exit_price = pos.current_price
         pos.close_reason = reason
         
         history_item = TradeHistoryItem(
             id=pos.id,
             symbol=pos.symbol,
             asset_type=pos.asset_type,
             side=pos.side,
             quantity=pos.quantity,
             entry_price=pos.entry_price,
             exit_price=pos.exit_price,
             pnl=pos.pnl,
             pnl_percent=pos.pnl_percent,
             opened_at=pos.opened_at,
             closed_at=pos.closed_at,
             close_reason=reason
         )
         self.trade_history.append(history_item)
         return history_item

    def get_open_positions(self) -> List[PaperPosition]:
        # Return sorted by newest
        return sorted(list(self.open_positions.values()), key=lambda x: x.opened_at, reverse=True)

    def get_trade_history(self) -> List[TradeHistoryItem]:
        return sorted(self.trade_history, key=lambda x: x.closed_at, reverse=True)
        
    def get_order_history(self) -> List[OrderLogItem]:
         return sorted(self.order_history, key=lambda x: x.placed_at, reverse=True)
         
    def get_account_summary(self) -> PaperAccount:
        unrealized_pnl = sum(pos.pnl for pos in self.open_positions.values())
        realized_pnl = sum(item.pnl for item in self.trade_history)
        total_equity = self.available_capital + unrealized_pnl
        
        return PaperAccount(
             initial_capital=self.initial_capital,
             available_capital=self.available_capital,
             realized_pnl=realized_pnl,
             unrealized_pnl=unrealized_pnl,
             total_equity=total_equity
        )

# Global singleton
paper_engine = PaperTradingEngine()
