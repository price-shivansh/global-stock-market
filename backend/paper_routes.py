"""
paper_routes.py — API endpoints for Paper Trading Phase 1.
"""
from fastapi import APIRouter, HTTPException
from typing import List
import random
from models import PaperOrderRequest, PaperPosition, PaperAccount, TradeHistoryItem, OrderLogItem
from paper_trade import paper_engine
from data_fetcher import data_fetcher

router = APIRouter(prefix="/api/paper-trading", tags=["paper-trading"])

@router.post("/order", response_model=PaperPosition)
async def place_order(req: PaperOrderRequest):
    try:
        return await paper_engine.place_order(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/open-positions", response_model=List[PaperPosition])
async def get_open_positions():
    return paper_engine.get_open_positions()

@router.get("/history", response_model=List[TradeHistoryItem])
async def get_trade_history():
    return paper_engine.get_trade_history()

@router.get("/orders", response_model=List[OrderLogItem])
async def get_order_history():
    return paper_engine.get_order_history()

@router.get("/account", response_model=PaperAccount)
async def get_account_summary():
    return paper_engine.get_account_summary()

@router.post("/close/{position_id}", response_model=TradeHistoryItem)
async def close_position(position_id: str):
    try:
        return await paper_engine.close_position(position_id, reason="MANUAL")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_positions():
    try:
        await paper_engine.update_positions()
        return {
            "open_positions": paper_engine.get_open_positions(),
            "account": paper_engine.get_account_summary()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart/{symbol}/{interval}")
async def get_chart(symbol: str, interval: str):
    """Reuse existing datafetcher logic to query historical chart data."""
    period_map = {
        "1m": "1d",
        "3m": "5d",
        "5m": "5d",
        "15m": "5d",
        "1h": "1mo",
        "1d": "6mo"
    }
    period = period_map.get(interval, "5d")
    
    try:
        # yfinance valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        yf_interval = "5m" if interval == "3m" else interval 
        data = await data_fetcher.get_historical_data(symbol, period=period, interval=yf_interval)
        if not data:
            raise HTTPException(status_code=404, detail="Data not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/order-book/{symbol}")
async def get_mock_order_book(symbol: str):
    try:
        from paper_trade import get_latest_price
        lp = await get_latest_price(symbol)
        
        spread = lp * 0.0005
        tick = 0.5 if lp > 1000 else 0.05
        
        asks = []
        ask_price = lp + spread
        for _ in range(8):
            asks.append({
                "price": round(ask_price, 2),
                "size": random.randint(10, 500)
            })
            ask_price += tick + (random.random() * tick * 2)
            
        bids = []
        bid_price = lp - spread
        for _ in range(8):
            bids.append({
                "price": round(bid_price, 2),
                "size": random.randint(10, 500)
            })
            bid_price -= tick + (random.random() * tick * 2)
            
        return {
            "symbol": symbol,
            "current_price": round(lp, 2),
            "asks": asks[::-1], # Highest asks first
            "bids": bids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
