"""
Indian Options Market Signal Dashboard - FastAPI Backend
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json

from config import settings
from models import (
    StockData, Signal, MarketSentiment, MarketOverview,
    WebSocketMessage, SignalType
)
from data_fetcher import data_fetcher
from sentiment_analysis import sentiment_analyzer
from technical_analysis import technical_analyzer
from news_history import get_history_path, get_history_stats, save_news_to_excel
from market_stream import stream_manager
from backtest_engine import backtest_engine
from telegram_notifier import send_telegram_message
from news_alert_service import news_alert_service

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time Indian Options Market Signal Dashboard with Technical and Sentiment Analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


# ── Lifespan: start background tasks on startup ────────────────
@app.on_event("startup")
async def _startup():
    asyncio.create_task(stream_manager.run_stream())
    asyncio.create_task(_paper_trade_auto_close_loop())
    # Start Telegram news alert loop and command polling if enabled
    if settings.TELEGRAM_ENABLED:
        asyncio.create_task(news_alert_service.run_news_alert_loop())
        from telegram_notifier import poll_commands
        asyncio.create_task(poll_commands())
        print("[Telegram] News alert background task started.")
        print("[Telegram] Command listener background task started.")
    else:
        print("[Telegram] Notifications disabled (TELEGRAM_ENABLED=false).")

async def _paper_trade_auto_close_loop():
    """Background loop to auto-close paper trades when SL/Target hit (Phase 1)"""
    from paper_trade import paper_engine
    while True:
        try:
            await paper_engine.update_positions()
        except Exception as e:
            print(f"Error in paper trade auto-close loop: {e}")
        await asyncio.sleep(3)  # Check every 3 seconds


# ── Telegram Manual Test & Status Endpoints ────────────────────────────────
@app.post("/api/test-telegram-message")
async def test_telegram_message():
    """Send a simple connectivity test message to Telegram."""
    success = await send_telegram_message(
        "✅ <b>Telegram bot connected successfully!</b>\n"
        "Your trading dashboard is online and sending notifications."
    )
    if success:
        return {"status": "ok", "message": "Test message sent to Telegram."}
    raise HTTPException(status_code=500, detail="Failed to send Telegram message. Check BOT_TOKEN and CHAT_ID.")


@app.post("/api/test-telegram-news")
async def test_telegram_news():
    """Manually run one full news check cycle (respects dedup — sends only unseen headlines)."""
    try:
        sent = await news_alert_service.check_and_notify()
        return {
            "status": "ok",
            "sent": sent,
            "message": f"{sent} new alert(s) sent." if sent else "No new headlines found (all already sent or no news).",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news-alert-status")
async def news_alert_status():
    """Return current state of the news alert loop: last cycle, dedup cache size, categories."""
    return news_alert_service.get_status()



# ── Existing API routes ─────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Indian Options Signal Dashboard API", "status": "running"}


@app.get("/api/market-overview")
async def get_market_overview():
    """Get complete market overview including ALL markets for gainers/losers"""
    try:
        # ── Fetch everything in parallel ──────────────────────────────────────
        (indices,
         indian_stocks,
         global_idx,
         sector_idx,
         commodities,
         crypto,
         forex,
         sentiment) = await asyncio.gather(
            data_fetcher.get_index_data(),
            data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS),
            _fetch_group(settings.GLOBAL_INDICES),
            _fetch_group(settings.SECTOR_INDICES),
            _fetch_group(settings.COMMODITY_SYMBOLS),
            _fetch_group(settings.CRYPTO_SYMBOLS),
            _fetch_group(settings.FOREX_SYMBOLS),
            sentiment_analyzer.get_market_sentiment(),
            return_exceptions=True
        )

        def safe_list(r):
            return r if isinstance(r, list) else []

        indian_stocks = safe_list(indian_stocks)
        global_idx    = safe_list(global_idx)
        sector_idx    = safe_list(sector_idx)
        commodities   = safe_list(commodities)
        crypto        = safe_list(crypto)
        forex         = safe_list(forex)

        # ── Tag each item with a category ─────────────────────────────────────
        CATEGORY_MAP = [
            (indian_stocks, "🇮🇳 India"),
            (global_idx,    "🌍 Global"),
            (sector_idx,    "📊 Sector"),
            (commodities,   "🏭 Commodity"),
            (crypto,        "🔷 Crypto"),
            (forex,         "💱 Forex"),
        ]

        for items, cat in CATEGORY_MAP:
            for item in items:
                item.category = cat  # attach category label dynamically

        # ── Full universe for gainers / losers / most active ──────────────────
        all_instruments = (
            indian_stocks + global_idx + sector_idx +
            commodities + crypto + forex
        )

        gainers, losers = await data_fetcher.get_top_gainers_losers(all_instruments)
        most_active     = await data_fetcher.get_most_active(all_instruments)

        # ── Signals only for Indian stocks (technical analysis needs OHLC) ─────
        signals = []
        for stock in indian_stocks:
            sym_sentiment = sentiment_analyzer.get_symbol_sentiment(
                stock.symbol, sentiment.news_items
            )
            signal = await data_fetcher.generate_signal(stock, sym_sentiment)
            signals.append(signal)
        signals.sort(key=lambda x: x.strength, reverse=True)

        return {
            "nifty":            indices.get("nifty") if isinstance(indices, dict) else None,
            "banknifty":        indices.get("banknifty") if isinstance(indices, dict) else None,
            "sensex":           indices.get("sensex") if isinstance(indices, dict) else None,
            "top_gainers":      gainers[:8],
            "top_losers":       losers[:8],
            "most_active":      most_active[:8],
            "market_sentiment": sentiment if not isinstance(sentiment, Exception) else None,
            "signals":          signals[:10],
            "all_stocks":       indian_stocks,
            "timestamp":        datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str):
    """Get detailed stock information"""
    try:
        if not symbol.startswith("^") and not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
        stock = await data_fetcher.get_stock_info(symbol)
        if stock is None:
            raise HTTPException(status_code=404, detail="Stock not found")
        sentiment = await sentiment_analyzer.get_market_sentiment()
        symbol_sentiment = sentiment_analyzer.get_symbol_sentiment(symbol, sentiment.news_items)
        signal = await data_fetcher.generate_signal(stock, symbol_sentiment)
        historical = await data_fetcher.get_historical_data(symbol, "6mo")
        return {
            "stock": stock,
            "signal": signal,
            "sentiment_score": symbol_sentiment,
            "historical": historical,
            "related_news": [n for n in sentiment.news_items if symbol.upper().replace(".NS", "") in [s.upper() for s in n.related_symbols]][:5]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/indices")
async def get_indices():
    """Get major index data"""
    try:
        indices = await data_fetcher.get_index_data()
        return indices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/technical-summary/{symbol}/{interval}")
async def get_technical_summary(symbol: str, interval: str):
    """Get technical indicators summary"""
    try:
        if not symbol.startswith("^") and not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
            
        period_map = {
            "5m": "5d",
            "15m": "5d",
            "1h": "1mo",
            "4h": "3mo",
            "1d": "6mo"
        }
        
        yf_interval = "60m" if interval in ["1h", "4h"] else interval
        period = period_map.get(interval, "6mo")
            
        historical_data = await data_fetcher.get_historical_data(symbol, period=period, interval=yf_interval)
        if not historical_data:
            raise HTTPException(status_code=404, detail="Data not found")
            
        import pandas as pd
        df = pd.DataFrame(historical_data)
        if len(df) < 50:
            raise HTTPException(status_code=400, detail="Not enough historical data")
            
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        
        from indicator_engine import indicator_engine
        summary = indicator_engine.generate_technical_summary(df)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks")
async def get_all_stocks():
    """Get all tracked stocks"""
    try:
        stocks = await data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
        return {"stocks": stocks, "count": len(stocks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals")
async def get_signals():
    """Get trading signals for all stocks"""
    try:
        stocks = await data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
        sentiment = await sentiment_analyzer.get_market_sentiment()
        signals = []
        for stock in stocks:
            symbol_sentiment = sentiment_analyzer.get_symbol_sentiment(
                stock.symbol, sentiment.news_items
            )
            signal = await data_fetcher.generate_signal(stock, symbol_sentiment)
            signals.append(signal)
        signals.sort(key=lambda x: x.strength, reverse=True)
        strong_buy  = [s for s in signals if s.signal_type == SignalType.STRONG_BUY]
        buy         = [s for s in signals if s.signal_type == SignalType.BUY]
        hold        = [s for s in signals if s.signal_type == SignalType.HOLD]
        sell        = [s for s in signals if s.signal_type == SignalType.SELL]
        strong_sell = [s for s in signals if s.signal_type == SignalType.STRONG_SELL]
        return {
            "all_signals": signals,
            "strong_buy": strong_buy,
            "buy": buy,
            "hold": hold,
            "sell": sell,
            "strong_sell": strong_sell,
            "summary": {
                "strong_buy_count": len(strong_buy),
                "buy_count": len(buy),
                "hold_count": len(hold),
                "sell_count": len(sell),
                "strong_sell_count": len(strong_sell)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentiment")
async def get_sentiment():
    """Get market sentiment analysis"""
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news")
async def get_news():
    """Get latest market news with sentiment"""
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()
        return {
            "news": sentiment.news_items,
            "overall_sentiment": sentiment.overall_sentiment,
            "sentiment_score": sentiment.sentiment_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/export")
async def export_news_excel(category: str = "General"):
    """Download the full news history as an Excel (.xlsx) file"""
    import os
    path = get_history_path(category)
    if not os.path.exists(path):
        try:
            sentiment = await sentiment_analyzer.get_market_sentiment()
        except Exception:
            pass
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"News history file for {category} not found yet. Try fetching news first via /api/news."
        )
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path)
    )


@app.get("/api/news/history")
async def get_news_history_stats(category: Optional[str] = None):
    """Get stats about the stored news history Excel file"""
    from news_history import get_history_stats, get_all_history_stats
    try:
        if category:
            stats = get_history_stats(category)
            return {"message": "Download the full history at /api/news/export?category=...", "category": category, **stats}
        else:
            stats = get_all_history_stats()
            return {"message": "Download the full history at /api/news/export?category=...", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/news/history")
async def reset_news_history(category: str):
    """Reset (delete) the news history for a given category"""
    from news_history import reset_history
    try:
        success = reset_history(category)
        if success:
            return {"message": f"Successfully reset history for {category}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to reset {category}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/historical/{symbol}")
async def get_historical(symbol: str, period: str = "6mo"):
    """Get historical price data"""
    try:
        data = await data_fetcher.get_historical_data(symbol, period)
        if data is None:
            raise HTTPException(status_code=404, detail="Data not found")
        return {"symbol": symbol, "period": period, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Helper for fetching groups of symbols ──────────────────────────────────────
async def _fetch_group(symbols: list) -> list:
    """Fetch a list of symbols concurrently, skip failures"""
    tasks = [data_fetcher.get_stock_info(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, StockData)]


# ── New Market Endpoints ───────────────────────────────────────────────────────

@app.get("/api/global-indices")
async def get_global_indices():
    """Get global market indices (S&P 500, NASDAQ, Nikkei, etc.)"""
    try:
        data = await _fetch_group(settings.GLOBAL_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sector-indices")
async def get_sector_indices():
    """Get Indian sector indices (IT, Pharma, Auto, etc.)"""
    try:
        data = await _fetch_group(settings.SECTOR_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commodities")
async def get_commodities():
    """Get commodity prices (Gold, Silver, Crude Oil, etc.)"""
    try:
        data = await _fetch_group(settings.COMMODITY_SYMBOLS)
        return {"commodities": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crypto")
async def get_crypto():
    """Get cryptocurrency prices (BTC, ETH, etc.)"""
    try:
        data = await _fetch_group(settings.CRYPTO_SYMBOLS)
        return {"crypto": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forex")
async def get_forex():
    """Get forex rates vs INR"""
    try:
        data = await _fetch_group(settings.FOREX_SYMBOLS)
        return {"forex": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/markets/all")
async def get_all_markets():
    """Get all extra market data in one shot — global, sectors, commodities, crypto, forex"""
    try:
        global_data, sector_data, commodity_data, crypto_data, forex_data = await asyncio.gather(
            _fetch_group(settings.GLOBAL_INDICES),
            _fetch_group(settings.SECTOR_INDICES),
            _fetch_group(settings.COMMODITY_SYMBOLS),
            _fetch_group(settings.CRYPTO_SYMBOLS),
            _fetch_group(settings.FOREX_SYMBOLS),
            return_exceptions=True
        )

        def safe(r):
            return r if isinstance(r, list) else []

        return {
            "global_indices": safe(global_data),
            "sector_indices": safe(sector_data),
            "commodities":    safe(commodity_data),
            "crypto":         safe(crypto_data),
            "forex":          safe(forex_data),
            "timestamp":      datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                indices = await data_fetcher.get_index_data()
                sentiment = await sentiment_analyzer.get_market_sentiment()
                await websocket.send_json({
                    "type": "market_update",
                    "data": {
                        "nifty": indices.get("nifty").dict() if indices.get("nifty") else None,
                        "banknifty": indices.get("banknifty").dict() if indices.get("banknifty") else None,
                        "sensex": indices.get("sensex").dict() if indices.get("sensex") else None,
                        "sentiment": sentiment.dict()
                    },
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"WebSocket update error: {e}")
            await asyncio.sleep(settings.DATA_REFRESH_INTERVAL)
    except WebSocketDisconnect:
        manager.disconnect(websocket)



# ════════════════════════════════════════════════════════════════════════════
# FEATURE 1 — Real-Time WebSocket Market Stream
# ════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/market")
async def ws_market(websocket: WebSocket):
    """Stream live price ticks to the client every ~2 seconds."""
    await stream_manager.connect(websocket)
    try:
        # Keep connection alive; the stream_manager broadcasts independently
        while True:
            await websocket.receive_text()   # client can send pings; we ignore them
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception:
        stream_manager.disconnect(websocket)


# ════════════════════════════════════════════════════════════════════════════
# FEATURE 2 — Paper Trading Simulator Phase 1
# ════════════════════════════════════════════════════════════════════════════

from paper_routes import router as paper_router
app.include_router(paper_router)


# ════════════════════════════════════════════════════════════════════════════
# FEATURE 3 — Backtest Engine
# ════════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    symbol:   str
    period:   str = "3mo"    # yfinance period string
    strategy: str = "RSI"    # RSI | MACD | RSI_MACD


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    """Run a historical strategy simulation and return metrics + equity curve."""
    try:
        result = await backtest_engine.run(
            symbol        = req.symbol,
            period        = req.period,
            strategy_name = req.strategy,
            data_fetcher  = data_fetcher,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
