"""
routers/technical.py — Technical analysis summary endpoint.
"""
import pandas as pd
from fastapi import APIRouter, HTTPException
from data_fetcher import data_fetcher
from indicator_engine import indicator_engine

router = APIRouter(tags=["technical-analysis"])


@router.get("/api/technical-summary/{symbol}/{interval}")
async def get_technical_summary(symbol: str, interval: str):
    """Get technical indicators summary for a symbol and interval."""
    try:
        if not symbol.startswith("^") and not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"

        period_map = {
            "5m":  "5d",
            "15m": "5d",
            "1h":  "1mo",
            "4h":  "3mo",
            "1d":  "6mo",
        }

        yf_interval = "60m" if interval in ["1h", "4h"] else interval
        period      = period_map.get(interval, "6mo")

        historical_data = await data_fetcher.get_historical_data(
            symbol, period=period, interval=yf_interval
        )
        if not historical_data:
            raise HTTPException(status_code=404, detail="Data not found")

        df = pd.DataFrame(historical_data)
        if len(df) < 50:
            raise HTTPException(status_code=400, detail="Not enough historical data")

        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        return indicator_engine.generate_technical_summary(df)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
