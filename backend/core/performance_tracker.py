"""
performance_tracker.py — Setup Win-Rate Aggregator
Reads raw outcomes from memory_engine and computes per-setup statistics.
Called by outcome_tracker after each successful outcome evaluation batch.
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Aggregates per-symbol, per-setup success statistics from stored outcomes.
    Results are written back to the setup_stats table via memory_engine.
    """

    def recalculate_all(self, symbol: str, horizon: str = "1h") -> List[Dict[str, Any]]:
        """
        Recalculate setup stats for every setup that has been active
        for the given symbol at the specified evaluation horizon.
        Returns a list of stats dicts that were upserted.
        """
        # Lazy import to avoid circular dependency
        from core.memory_engine import memory_engine

        raw_outcomes = memory_engine.get_raw_outcomes_for_symbol(symbol, horizon)
        if not raw_outcomes:
            logger.debug(f"[PerformanceTracker] No outcomes yet for {symbol}@{horizon}")
            return []

        # Aggregate per setup
        setup_buckets: Dict[str, Dict[str, Any]] = {}

        for row in raw_outcomes:
            setups = row.get("active_setups", [])
            if isinstance(setups, str):
                try:
                    setups = json.loads(setups)
                except Exception:
                    setups = []

            price_chg = row.get("price_change_pct", 0.0) or 0.0
            outcome   = row.get("outcome", "NEUTRAL")

            for setup_name in setups:
                if setup_name not in setup_buckets:
                    setup_buckets[setup_name] = {
                        "correct": 0,
                        "incorrect": 0,
                        "neutral": 0,
                        "returns": []
                    }
                b = setup_buckets[setup_name]
                if outcome == "CORRECT":
                    b["correct"] += 1
                elif outcome == "INCORRECT":
                    b["incorrect"] += 1
                else:
                    b["neutral"] += 1
                b["returns"].append(price_chg)

        # Build stats records and persist
        now_iso = datetime.now(timezone.utc).isoformat()
        results = []

        for setup_name, b in setup_buckets.items():
            total = b["correct"] + b["incorrect"] + b["neutral"]
            decisive = b["correct"] + b["incorrect"]
            win_rate = (b["correct"] / decisive) if decisive > 0 else 0.0
            avg_ret  = (sum(b["returns"]) / len(b["returns"])) if b["returns"] else 0.0

            stats = {
                "setup_name":       setup_name,
                "symbol":           symbol,
                "total_predictions": total,
                "correct_count":    b["correct"],
                "incorrect_count":  b["incorrect"],
                "neutral_count":    b["neutral"],
                "win_rate":         round(win_rate, 4),
                "avg_return_pct":   round(avg_ret, 4),
                "last_updated":     now_iso,
            }
            memory_engine.upsert_setup_stats(stats)
            results.append(stats)

        logger.info(
            f"[PerformanceTracker] Recalculated {len(results)} setups for {symbol}@{horizon}"
        )
        return results

    def get_performance_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Return a structured summary suitable for the API response.
        """
        from core.memory_engine import memory_engine

        setup_stats = memory_engine.get_setup_stats(symbol)

        total_evaluated = sum(
            s.get("correct_count", 0) + s.get("incorrect_count", 0)
            for s in setup_stats
        )
        if not setup_stats or total_evaluated == 0:
            return {
                "symbol": symbol,
                "setups": [],
                "overall_win_rate": 0.0,
                "total_evaluated": 0,
            }

        total_correct = sum(s.get("correct_count", 0) for s in setup_stats)
        total_decisive = sum(
            s.get("correct_count", 0) + s.get("incorrect_count", 0)
            for s in setup_stats
        )
        overall_wr = (total_correct / total_decisive) if total_decisive > 0 else 0.0

        return {
            "symbol": symbol,
            "setups": setup_stats,
            "overall_win_rate": round(overall_wr, 4),
            "total_evaluated": total_decisive,
        }


performance_tracker = PerformanceTracker()
