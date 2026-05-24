import asyncio
import logging
import traceback
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, HTTPException
from config import settings
from data_fetcher import data_fetcher
from sentiment_analysis import sentiment_analyzer
from core.utils import fetch_group

logger = logging.getLogger(__name__)
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
    logger.info("Request started: /api/market-overview")
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

        # Log any exceptions gathered
        gathered_results = [
            ("indices", indices),
            ("indian_stocks", indian_stocks),
            ("global_idx", global_idx),
            ("sector_idx", sector_idx),
            ("commodities", commodities),
            ("crypto", crypto),
            ("forex", forex),
            ("sentiment", sentiment)
        ]
        for name, r in gathered_results:
            if isinstance(r, Exception):
                logger.error(f"Gathered exception in {name}: {str(r)}")
                traceback.print_exception(type(r), r, r.__traceback__)

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
                if hasattr(item, "category"):
                    item.category = cat

        all_instruments = (
            indian_stocks + global_idx + sector_idx +
            commodities + crypto + forex
        )

        gainers, losers = await data_fetcher.get_top_gainers_losers(all_instruments)
        most_active     = await data_fetcher.get_most_active(all_instruments)

        news_items = []
        if not isinstance(sentiment, Exception) and hasattr(sentiment, "news_items"):
            news_items = sentiment.news_items

        signals = []
        for stock in indian_stocks:
            try:
                sym_sentiment = sentiment_analyzer.get_symbol_sentiment(
                    stock.symbol, news_items
                )
                signal = await data_fetcher.generate_signal(stock, sym_sentiment)
                signals.append(signal)
            except Exception as sig_err:
                logger.error(f"Failed to generate signal for {stock.symbol}: {sig_err}")

        signals.sort(key=lambda x: getattr(x, "strength", 0.0), reverse=True)

        nifty_data = indices.get("nifty") if (isinstance(indices, dict) and "nifty" in indices) else None
        banknifty_data = indices.get("banknifty") if (isinstance(indices, dict) and "banknifty" in indices) else None
        sensex_data = indices.get("sensex") if (isinstance(indices, dict) and "sensex" in indices) else None

        return {
            "nifty":            nifty_data,
            "banknifty":        banknifty_data,
            "sensex":           sensex_data,
            "top_gainers":      gainers[:8],
            "top_losers":       losers[:8],
            "most_active":      most_active[:8],
            "market_sentiment": sentiment if not isinstance(sentiment, Exception) else None,
            "signals":          signals[:10],
            "all_stocks":       indian_stocks,
            "timestamp":        datetime.now().isoformat(),
        }
    except Exception as e:
        logger.exception("Detailed error in /api/market-overview")
        traceback.print_exc()
        return {
            "top_gainers": [],
            "top_losers": [],
            "most_active": [],
            "signals": [],
            "all_stocks": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str):
    """Get detailed stock information."""
    try:
        decoded_symbol = urllib.parse.unquote(symbol)
        if not decoded_symbol.startswith("^") and not decoded_symbol.endswith(".NS"):
            decoded_symbol = f"{decoded_symbol}.NS"
        stock = await data_fetcher.get_stock_info(decoded_symbol)
        if stock is None:
            raise HTTPException(status_code=404, detail=f"Stock {decoded_symbol} not found")
        sentiment = await sentiment_analyzer.get_market_sentiment()
        news_items = []
        if sentiment and not isinstance(sentiment, Exception) and hasattr(sentiment, "news_items"):
            news_items = sentiment.news_items
        symbol_sentiment = sentiment_analyzer.get_symbol_sentiment(decoded_symbol, news_items)
        signal = await data_fetcher.generate_signal(stock, symbol_sentiment)
        historical = await data_fetcher.get_historical_data(decoded_symbol, "6mo")
        return {
            "stock": stock,
            "signal": signal,
            "sentiment_score": symbol_sentiment,
            "historical": historical,
            "related_news": [
                n for n in news_items
                if decoded_symbol.upper().replace(".NS", "") in [s.upper() for s in n.related_symbols]
            ][:5],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Detailed error in /api/stock/{symbol}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/indices")
async def get_indices():
    """Get major index data."""
    try:
        return await data_fetcher.get_index_data()
    except Exception as e:
        logger.exception("Detailed error in /api/indices")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/stocks")
async def get_all_stocks():
    """Get all tracked stocks."""
    try:
        stocks = await data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
        return {"stocks": stocks, "count": len(stocks)}
    except Exception as e:
        logger.exception("Detailed error in /api/stocks")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/historical/{symbol}")
async def get_historical(symbol: str, period: str = "6mo"):
    """Get historical price data."""
    logger.info(f"Request started: /api/historical/{symbol} with period={period}")
    try:
        decoded_symbol = urllib.parse.unquote(symbol)
        logger.info(f"Normalized symbol: {symbol} -> {decoded_symbol}")
        data = await data_fetcher.get_historical_data(decoded_symbol, period)
        if data is None:
            logger.warning(f"No historical data found for symbol: {decoded_symbol}")
            return {"symbol": decoded_symbol, "period": period, "data": [], "warning": "Data not found or fetch failed"}
        return {"symbol": decoded_symbol, "period": period, "data": data}
    except Exception as e:
        logger.exception(f"Detailed error in /api/historical/{symbol}: {str(e)}")
        traceback.print_exc()
        return {"symbol": symbol, "period": period, "data": [], "error": str(e)}


@router.get("/api/global-indices")
async def get_global_indices():
    """Get global market indices (S&P 500, NASDAQ, Nikkei, etc.)."""
    try:
        data = await _fetch_group(settings.GLOBAL_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        logger.exception("Detailed error in /api/global-indices")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sector-indices")
async def get_sector_indices():
    """Get Indian sector indices (IT, Pharma, Auto, etc.)."""
    try:
        data = await _fetch_group(settings.SECTOR_INDICES)
        return {"indices": data, "count": len(data)}
    except Exception as e:
        logger.exception("Detailed error in /api/sector-indices")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/commodities")
async def get_commodities():
    """Get commodity prices (Gold, Silver, Crude Oil, etc.)."""
    try:
        data = await _fetch_group(settings.COMMODITY_SYMBOLS)
        return {"commodities": data, "count": len(data)}
    except Exception as e:
        logger.exception("Detailed error in /api/commodities")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/crypto")
async def get_crypto():
    """Get cryptocurrency prices (BTC, ETH, etc.)."""
    try:
        data = await _fetch_group(settings.CRYPTO_SYMBOLS)
        return {"crypto": data, "count": len(data)}
    except Exception as e:
        logger.exception("Detailed error in /api/crypto")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/forex")
async def get_forex():
    """Get forex rates vs INR."""
    try:
        data = await _fetch_group(settings.FOREX_SYMBOLS)
        return {"forex": data, "count": len(data)}
    except Exception as e:
        logger.exception("Detailed error in /api/forex")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/markets/all")
async def get_all_markets():
    """Get all extra market data in one shot — global, sectors, commodities, crypto, forex."""
    logger.info("Request started: /api/markets/all")
    try:
        global_data, sector_data, commodity_data, crypto_data, forex_data = await asyncio.gather(
            _fetch_group(settings.GLOBAL_INDICES),
            _fetch_group(settings.SECTOR_INDICES),
            _fetch_group(settings.COMMODITY_SYMBOLS),
            _fetch_group(settings.CRYPTO_SYMBOLS),
            _fetch_group(settings.FOREX_SYMBOLS),
            return_exceptions=True,
        )

        # Log any exceptions gathered
        gathered_results = [
            ("global_data", global_data),
            ("sector_data", sector_data),
            ("commodity_data", commodity_data),
            ("crypto_data", crypto_data),
            ("forex_data", forex_data)
        ]
        for name, r in gathered_results:
            if isinstance(r, Exception):
                logger.error(f"Gathered exception in {name}: {str(r)}")
                traceback.print_exception(type(r), r, r.__traceback__)

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
        logger.exception("Detailed error in /api/markets/all")
        traceback.print_exc()
        return {
            "global_indices": [],
            "sector_indices": [],
            "commodities": [],
            "crypto": [],
            "forex": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
