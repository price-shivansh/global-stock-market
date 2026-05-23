"""
routers/backtesting.py — Backtest engine endpoint.
"""
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from backtest_engine import backtest_engine
from data_fetcher import data_fetcher

router = APIRouter(tags=["backtesting"])


class BacktestRequest(BaseModel):
    symbol:   str
    period:   str = "3mo"   # yfinance period string
    strategy: str = "RSI"   # RSI | MACD | RSI_MACD


@router.post("/api/backtest")
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
