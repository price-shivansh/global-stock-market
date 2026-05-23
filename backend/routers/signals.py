"""
routers/signals.py — Trading signal endpoints.
"""
from fastapi import APIRouter, HTTPException
from config import settings
from data_fetcher import data_fetcher
from sentiment_analysis import sentiment_analyzer
from schemas.market_schemas import SignalType

router = APIRouter(tags=["signals"])


@router.get("/api/signals")
async def get_signals():
    """Get trading signals for all tracked stocks."""
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
            "strong_buy":  strong_buy,
            "buy":         buy,
            "hold":        hold,
            "sell":        sell,
            "strong_sell": strong_sell,
            "summary": {
                "strong_buy_count":  len(strong_buy),
                "buy_count":         len(buy),
                "hold_count":        len(hold),
                "sell_count":        len(sell),
                "strong_sell_count": len(strong_sell),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
