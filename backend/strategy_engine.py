"""
strategy_engine.py — Signal Generation for Backtesting
Produces a BUY (1) / SELL (-1) / HOLD (0) integer Series for each strategy.
Uses only indicator_engine so there is no duplicated indicator logic.
"""
import pandas as pd
import numpy as np
from indicator_engine import indicator_engine


class StrategyEngine:
    """
    Generates a signal Series aligned to the OHLCV DataFrame index.
    Supported strategies: "RSI", "MACD", "RSI_MACD"
    """

    # ── RSI Strategy ─────────────────────────────────────────────────────────
    def rsi_strategy(
        self,
        close: pd.Series,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> pd.Series:
        """
        BUY  when RSI crosses above oversold threshold
        SELL when RSI crosses below overbought threshold
        """
        rsi = indicator_engine.rsi(close)

        signal = pd.Series(0, index=close.index, dtype=int)
        # Crossovers: compare current vs previous bar
        signal[rsi.shift(1) < oversold   and rsi >= oversold] = 0   # placeholder
        # Vectorised crossovers
        signal[(rsi.shift(1) < oversold)  & (rsi >= oversold)]  =  1   # BUY entry
        signal[(rsi.shift(1) > overbought) & (rsi <= overbought)] = -1   # SELL entry
        return signal.fillna(0).astype(int)

    # ── MACD Strategy ────────────────────────────────────────────────────────
    def macd_strategy(self, close: pd.Series) -> pd.Series:
        """
        BUY  when MACD line crosses above signal line
        SELL when MACD line crosses below signal line
        """
        macd_line, sig_line, _ = indicator_engine.macd(close)

        signal = pd.Series(0, index=close.index, dtype=int)
        signal[(macd_line.shift(1) < sig_line.shift(1)) & (macd_line >= sig_line)] =  1
        signal[(macd_line.shift(1) > sig_line.shift(1)) & (macd_line <= sig_line)] = -1
        return signal.fillna(0).astype(int)

    # ── RSI + MACD Combined Strategy ─────────────────────────────────────────
    def rsi_macd_strategy(
        self,
        close: pd.Series,
        oversold: float = 35.0,
        overbought: float = 65.0,
    ) -> pd.Series:
        """
        BUY  only when both RSI is oversold AND MACD is bullish crossover
        SELL only when both RSI is overbought AND MACD is bearish crossover
        Higher precision, fewer trades.
        """
        rsi_sig  = self.rsi_strategy(close, oversold, overbought)
        macd_sig = self.macd_strategy(close)

        signal = pd.Series(0, index=close.index, dtype=int)
        signal[(rsi_sig ==  1) & (macd_sig ==  1)] =  1
        signal[(rsi_sig == -1) & (macd_sig == -1)] = -1
        return signal.fillna(0).astype(int)

    # ── Dispatcher ───────────────────────────────────────────────────────────
    def generate_signals(self, close: pd.Series, strategy: str) -> pd.Series:
        strategy = strategy.upper()
        if strategy == "RSI":
            return self.rsi_strategy(close)
        elif strategy == "MACD":
            return self.macd_strategy(close)
        elif strategy in ("RSI_MACD", "RSI+MACD"):
            return self.rsi_macd_strategy(close)
        else:
            raise ValueError(f"Unknown strategy: {strategy}. Choose RSI | MACD | RSI_MACD")


# ── Module-level singleton ───────────────────────────────────────────────────
strategy_engine = StrategyEngine()
