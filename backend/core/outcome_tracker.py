"""
outcome_tracker.py — Background Prediction Outcome Evaluator
Runs as a persistent asyncio task every 5 minutes.
For each unfulfilled prediction horizon it fetches the current price,
computes actual move vs prediction, determines correctness, and stores the result.
After every batch it triggers performance recalculation and confidence optimization.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Evaluation horizons in seconds → label
HORIZONS = {
    900:   "15m",
    3600:  "1h",
    14400: "4h",
}

# ATR-based correctness threshold:
# A prediction is CORRECT if the move exceeds 0.25 × ATR (minimum 0.3% floor)
ATR_FACTOR      = 0.25
MIN_MOVE_PCT    = 0.30   # 0.30% minimum move to be decisive


class OutcomeTracker:
    """
    Autonomous background evaluator for open predictions.
    Lifecycle: started once at FastAPI startup, runs indefinitely.
    """

    def __init__(self, poll_interval: int = 300):
        self._poll_interval = poll_interval   # seconds between evaluation runs
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="outcome_tracker")
        logger.info("[OutcomeTracker] Background evaluation task started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[OutcomeTracker] Stopped.")

    async def _loop(self):
        """Main polling loop — runs while backend is alive."""
        # Initial delay so backend fully starts before first run
        await asyncio.sleep(30)
        while self._running:
            try:
                await self.run_evaluation_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[OutcomeTracker] Evaluation cycle failed: {e}", exc_info=True)
            await asyncio.sleep(self._poll_interval)

    async def run_evaluation_batch(self) -> int:
        """
        Evaluate all pending predictions across all horizons.
        Returns the total number of outcomes recorded this batch.
        """
        from core.memory_engine import memory_engine
        from core.performance_tracker import performance_tracker
        from core.confidence_optimizer import confidence_optimizer
        from data_fetcher import data_fetcher

        total_recorded = 0
        symbols_touched: set = set()

        for horizon_sec, horizon_label in HORIZONS.items():
            pending = memory_engine.get_pending_evaluations(horizon_sec)
            if not pending:
                continue

            logger.info(
                f"[OutcomeTracker] Evaluating {len(pending)} predictions "
                f"for horizon={horizon_label}"
            )

            # Group by symbol to minimise yfinance calls
            by_symbol: dict = {}
            for p in pending:
                by_symbol.setdefault(p["symbol"], []).append(p)

            for symbol, preds in by_symbol.items():
                # Fetch live price once per symbol
                current_price = await self._fetch_current_price(symbol, data_fetcher)
                if current_price is None:
                    logger.warning(f"[OutcomeTracker] Could not fetch price for {symbol}")
                    continue

                for pred in preds:
                    try:
                        outcome_record = self._evaluate(pred, current_price, horizon_label)
                        memory_engine.store_outcome(outcome_record)
                        total_recorded += 1
                        symbols_touched.add(symbol)
                    except Exception as e:
                        logger.warning(
                            f"[OutcomeTracker] Failed to evaluate prediction "
                            f"id={pred.get('id')}: {e}"
                        )

        # After recording outcomes, update stats and optimize weights
        for sym in symbols_touched:
            try:
                performance_tracker.recalculate_all(sym, "1h")
                confidence_optimizer.run_optimization_cycle(sym)
            except Exception as e:
                logger.warning(f"[OutcomeTracker] Post-eval update failed for {sym}: {e}")

        if total_recorded:
            logger.info(f"[OutcomeTracker] Batch complete — {total_recorded} outcomes recorded.")
        return total_recorded

    # ── Price fetcher ──────────────────────────────────────────────────────────

    async def _fetch_current_price(self, symbol: str, data_fetcher) -> Optional[float]:
        """
        Fetch the latest close price for a symbol using the existing data_fetcher.
        We use 5-day 1h interval to get recent data quickly.
        """
        try:
            df = await data_fetcher.fetch_stock_data(symbol, period="5d", interval="1h")
            if df is not None and not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"[OutcomeTracker] Price fetch error for {symbol}: {e}")
        return None

    # ── Outcome evaluation ─────────────────────────────────────────────────────

    def _evaluate(
        self,
        prediction: dict,
        current_price: float,
        horizon_label: str,
    ) -> dict:
        """
        Determine whether a prediction was correct.
        Uses ATR-based threshold with a percentage floor.
        """
        entry_price = prediction.get("price_at_prediction", 0)
        if entry_price == 0:
            raise ValueError("price_at_prediction is zero")

        price_change_pct = ((current_price - entry_price) / entry_price) * 100.0

        # Determine the significance threshold
        # atr_pct stored as percentage of price (e.g. 1.5 means 1.5%)
        atr_pct = prediction.get("atr_pct") or 1.0
        threshold_pct = max(MIN_MOVE_PCT, atr_pct * ATR_FACTOR)

        bias = prediction.get("bias", "Neutral")

        if bias == "Bullish":
            if price_change_pct >= threshold_pct:
                outcome = "CORRECT"
            elif price_change_pct <= -threshold_pct:
                outcome = "INCORRECT"
            else:
                outcome = "NEUTRAL"
        elif bias == "Bearish":
            if price_change_pct <= -threshold_pct:
                outcome = "CORRECT"
            elif price_change_pct >= threshold_pct:
                outcome = "INCORRECT"
            else:
                outcome = "NEUTRAL"
        else:
            # Neutral prediction — only INCORRECT if a decisive move happened
            if abs(price_change_pct) >= threshold_pct:
                outcome = "INCORRECT"
            else:
                outcome = "CORRECT"

        return {
            "prediction_id":   prediction["id"],
            "horizon":         horizon_label,
            "price_at_outcome": round(current_price, 4),
            "price_change_pct": round(price_change_pct, 4),
            "outcome":         outcome,
            "evaluated_at":    datetime.now(timezone.utc).isoformat(),
        }


# Module-level singleton
outcome_tracker = OutcomeTracker(poll_interval=300)
