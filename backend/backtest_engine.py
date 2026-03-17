"""
backtest_engine.py — Historical Strategy Simulator
Runs a strategy over OHLCV data and returns trade-level metrics
plus an equity curve for charting.
"""
import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from strategy_engine import strategy_engine

logger = logging.getLogger(__name__)


class BacktestResult:
    """Structured backtest output."""
    def __init__(
        self,
        symbol: str,
        strategy: str,
        period: str,
        total_trades: int,
        win_rate: float,
        net_return_pct: float,
        max_drawdown_pct: float,
        equity_curve: List[Dict],
        trade_log: List[Dict],
    ) -> None:
        self.symbol          = symbol
        self.strategy        = strategy
        self.period          = period
        self.total_trades    = total_trades
        self.win_rate        = win_rate
        self.net_return_pct  = net_return_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.equity_curve    = equity_curve
        self.trade_log       = trade_log

    def to_dict(self) -> dict:
        return {
            "symbol":           self.symbol,
            "strategy":         self.strategy,
            "period":           self.period,
            "total_trades":     self.total_trades,
            "win_rate":         round(self.win_rate, 1),
            "net_return_pct":   round(self.net_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "equity_curve":     self.equity_curve,
            "trade_log":        self.trade_log,
        }


class BacktestEngine:
    """
    Pure stateless backtest runner.
    Each call to run() is independent — no global state.
    """

    def __init__(self, initial_capital: float = 100_000.0) -> None:
        self.initial_capital = initial_capital

    async def run(
        self,
        symbol: str,
        period: str,
        strategy_name: str,
        data_fetcher,
    ) -> BacktestResult:
        """
        Fetch OHLCV, generate signals, simulate trades, compute metrics.
        Returns a BacktestResult with full equity curve.
        """
        # ── 1. Fetch historical data ─────────────────────────────────────────
        raw = await data_fetcher.get_historical_data(symbol, period)
        if not raw or len(raw) < 60:
            raise ValueError(f"Not enough data for {symbol} ({len(raw or [])} bars)")

        df = pd.DataFrame(raw)
        df["date"]  = pd.to_datetime(df["date"])
        df          = df.set_index("date").sort_index()
        close       = df["close"]

        # ── 2. Generate signals ──────────────────────────────────────────────
        signals = strategy_engine.generate_signals(close, strategy_name)

        # ── 3. Simulate trades ───────────────────────────────────────────────
        equity      = self.initial_capital
        position    = 0.0          # shares held (0 = flat)
        entry_price = 0.0
        trade_log: List[Dict] = []
        equity_curve: List[Dict] = []

        peak_equity = equity

        for date, sig in signals.items():
            price = float(close.loc[date])

            # ── Open long ────────────────────────────────────────────────────
            if sig == 1 and position == 0:
                shares    = equity / price
                position  = shares
                entry_price = price

            # ── Close long ───────────────────────────────────────────────────
            elif sig == -1 and position > 0:
                exit_equity = position * price
                pnl         = exit_equity - (position * entry_price)
                trade_log.append({
                    "entry":  round(entry_price, 2),
                    "exit":   round(price, 2),
                    "pnl":    round(pnl, 2),
                    "win":    pnl > 0,
                    "date":   str(date.date()),
                })
                equity   = exit_equity
                position = 0.0

            # ── Track equity ─────────────────────────────────────────────────
            current_equity = equity if position == 0 else position * price
            peak_equity    = max(peak_equity, current_equity)
            drawdown       = (peak_equity - current_equity) / peak_equity * 100

            equity_curve.append({
                "date":     str(date.date()),
                "equity":   round(current_equity, 2),
                "drawdown": round(drawdown, 2),
            })

        # ── Close any open position at last price ────────────────────────────
        if position > 0:
            last_price  = float(close.iloc[-1])
            pnl         = position * (last_price - entry_price)
            trade_log.append({
                "entry":  round(entry_price, 2),
                "exit":   round(last_price, 2),
                "pnl":    round(pnl, 2),
                "win":    pnl > 0,
                "date":   str(close.index[-1].date()),
            })
            equity = position * last_price

        # ── 4. Compute metrics ───────────────────────────────────────────────
        total_trades    = len(trade_log)
        wins            = sum(1 for t in trade_log if t["win"])
        win_rate        = (wins / total_trades * 100) if total_trades > 0 else 0.0
        net_return_pct  = ((equity - self.initial_capital) / self.initial_capital) * 100
        max_drawdown    = max((p["drawdown"] for p in equity_curve), default=0.0)

        logger.info(
            "Backtest %s/%s/%s: %d trades, %.1f%% win rate, %.2f%% return",
            symbol, strategy_name, period, total_trades, win_rate, net_return_pct
        )

        return BacktestResult(
            symbol          = symbol,
            strategy        = strategy_name.upper(),
            period          = period,
            total_trades    = total_trades,
            win_rate        = win_rate,
            net_return_pct  = net_return_pct,
            max_drawdown_pct = max_drawdown,
            equity_curve    = equity_curve,
            trade_log       = trade_log,
        )


# ── Module-level instance ────────────────────────────────────────────────────
backtest_engine = BacktestEngine(initial_capital=100_000.0)
