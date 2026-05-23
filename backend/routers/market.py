"""
routers/market.py — Market data endpoints.

Covers: market overview, individual stocks, indices, historical data,
global indices, sector indices, commodities, crypto, and forex.
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from config import settings
from data_fetcher import data_fetcher
from sentiment_analysis import sentiment_analyzer
from core.utils import fetch_group

router = APIRouter(tags=["market"])


# ── Helper ────────────────────────────────────────────────────────────────────

async def _fetch_group(symbols: list) -> list:
    """Thin wrapper kept for backward-compat inside this module."""
    return await fetch_group(symbols, data_fetcher)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def root():
    return {"message": "Indian Options Signal Dashboard API", "status": "running"}


@router.get("/api/market-overview")
async def get_market_overview():
    """Get complete market overview including ALL markets for gainers/losers."""
    try:
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
            return_exceptions=True,
        )

        def safe_list(r):
            return r if isinstance(r, list) else []

        indian_stocks = safe_list(indian_stocks)
        global_idx    = safe_list(global_idx)
        sector_idx    = safe_list(sector_idx)
        commodities   = safe_list(commodities)
        crypto        = safe_list(crypto)
        forex         = safe_list(forex)

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
                item.category = cat

        all_instruments = (
            indian_stocks + global_idx + sector_idx +
            commodities + crypto + forex
        )

        gainers, losers = await data_fetcher.get_top_gainers_losers(all_instruments)
        most_active     = await data_fetcher.get_most_active(all_instruments)

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
            "timestamp":        datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str):
    """Get detailed stock information."""
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
            "related_news": [
                n for n in sentiment.news_items
                if symbol.upper().replace(".NS", "") in [s.upper() for s in n.related_symbols]
            ][:5],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/indices")
async def get_indices():
    """Get major index data."""
    try:
        return await data_fetcher.get_index_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/stocks")
async def get_all_stocks():
    """Get all tracked stocks."""
    try:
        stocks = await data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
        return {"stocks": stocks, "count": len(stocks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/historical/{symbol}")
async def get_historical(symbol: str, period: str = "6mo"):
    """Get historical price data."""
    try:
        data = await data_fetcher.get_historical_data(symbol, period)
        if data is None:
            raise HTTPException(status_code=404, detail="Data not found")
        return {"symbol": symbol, "period": period, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/global-indices")
async def get_global_indices():
    """Get global market indices (S&P 500, NASDAQ, Nikkei, etc.)."""
    try:
        data = await _fetch_group(settings.GLOBAL_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sector-indices")
async def get_sector_indices():
    """Get Indian sector indices (IT, Pharma, Auto, etc.)."""
    try:
        data = await _fetch_group(settings.SECTOR_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/commodities")
async def get_commodities():
    """Get commodity prices (Gold, Silver, Crude Oil, etc.)."""
    try:
        data = await _fetch_group(settings.COMMODITY_SYMBOLS)
        return {"commodities": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/crypto")
async def get_crypto():
    """Get cryptocurrency prices (BTC, ETH, etc.)."""
    try:
        data = await _fetch_group(settings.CRYPTO_SYMBOLS)
        return {"crypto": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/forex")
async def get_forex():
    """Get forex rates vs INR."""
    try:
        data = await _fetch_group(settings.FOREX_SYMBOLS)
        return {"forex": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/markets/all")
async def get_all_markets():
    """Get all extra market data in one shot — global, sectors, commodities, crypto, forex."""
    try:
        global_data, sector_data, commodity_data, crypto_data, forex_data = await asyncio.gather(
            _fetch_group(settings.GLOBAL_INDICES),
            _fetch_group(settings.SECTOR_INDICES),
            _fetch_group(settings.COMMODITY_SYMBOLS),
            _fetch_group(settings.CRYPTO_SYMBOLS),
            _fetch_group(settings.FOREX_SYMBOLS),
            return_exceptions=True,
        )

        def safe(r):
            return r if isinstance(r, list) else []

        return {
            "global_indices": safe(global_data),
            "sector_indices": safe(sector_data),
            "commodities":    safe(commodity_data),
            "crypto":         safe(crypto_data),
            "forex":          safe(forex_data),
            "timestamp":      datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
