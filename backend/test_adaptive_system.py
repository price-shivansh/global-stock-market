"""
test_adaptive_system.py — End-to-end smoke test for the Adaptive Intelligence System.
Run from backend/ directory: python test_adaptive_system.py
"""
import asyncio
import json
from datetime import datetime, timezone

async def main():
    print("=" * 60)
    print("ADAPTIVE INTELLIGENCE SYSTEM — SMOKE TEST")
    print("=" * 60)

    # ── 1. Memory Engine ──────────────────────────────────────────────────────
    print("\n[1/5] Testing MemoryEngine …")
    from core.memory_engine import memory_engine

    dummy = {
        "symbol":            "CL=F",
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "bias":              "Bullish",
        "confidence_score":  72.5,
        "technical_score":   80.0,
        "news_score":        55.0,
        "rsi_value":         48.2,
        "macd_signal":       "BUY",
        "ema_trend":         "ABOVE",
        "momentum_signal":   "BUY",
        "bb_signal":         "NEUTRAL",
        "market_regime":     "TRENDING",
        "atr_pct":           1.4,
        "price_at_prediction": 105.50,
        "active_setups":     json.dumps(["MACD_BULL_CROSS", "EMA_BULL_STACK"]),
    }
    pred_id = memory_engine.store_prediction(dummy)
    print(f"   ✓ Stored prediction id={pred_id}")

    retrieved = memory_engine.get_predictions("CL=F", limit=5)
    assert len(retrieved) > 0, "No predictions retrieved"
    print(f"   ✓ Retrieved {len(retrieved)} prediction(s)")

    # ── 2. Pattern Tracker ────────────────────────────────────────────────────
    print("\n[2/5] Testing PatternTracker …")
    from core.pattern_tracker import pattern_tracker

    signals = pattern_tracker.extract_indicator_signals([
        {"name": "RSI(14)",      "signal": "BUY",  "value": 28.5},
        {"name": "MACD",         "signal": "BUY",  "value": 0.5},
        {"name": "Momentum(10)", "signal": "BUY",  "value": 3.2},
        {"name": "Bollinger Bands","signal":"NEUTRAL","value": 100.0},
        {"name": "EMA(20)",      "signal": "BUY",  "value": 99.0},
        {"name": "EMA(50)",      "signal": "BUY",  "value": 98.0},
    ])
    print(f"   ✓ Extracted signals: {signals}")

    snapshot = {
        "symbol": "CL=F", "bias": "Bullish", "confidence_score": 78.0,
        "technical_score": 85.0, "news_score": 60.0, "atr_pct": 1.5,
        **signals
    }
    setups = pattern_tracker.detect_setups(snapshot)
    print(f"   ✓ Active setups detected: {setups}")
    assert len(setups) > 0, "No setups detected"

    regime = pattern_tracker.classify_regime("ABOVE", "BUY", 1.5, 78.0)
    print(f"   ✓ Market regime: {regime}")

    # ── 3. Confidence Optimizer ───────────────────────────────────────────────
    print("\n[3/5] Testing ConfidenceOptimizer …")
    from core.confidence_optimizer import confidence_optimizer

    conf = confidence_optimizer.get_weighted_confidence(
        technical_score=85.0,
        news_score=60.0,
        indicator_signals=signals,
    )
    print(f"   ✓ Adaptive confidence score: {conf:.1f}")
    assert 0 <= conf <= 100, "Confidence out of range"

    # ── 4. Outcome Evaluation (manual) ────────────────────────────────────────
    print("\n[4/5] Testing OutcomeTracker (manual single evaluation) …")
    from core.outcome_tracker import outcome_tracker

    fake_pred = {
        "id": pred_id,
        "bias": "Bullish",
        "price_at_prediction": 105.50,
        "atr_pct": 1.4,
    }
    outcome = outcome_tracker._evaluate(fake_pred, current_price=107.50, horizon_label="1h")
    print(f"   ✓ Evaluated outcome: {outcome}")
    assert outcome["outcome"] in ("CORRECT", "INCORRECT", "NEUTRAL")

    # ── 5. Full generate_ai_summary ───────────────────────────────────────────
    print("\n[5/5] Testing full generate_ai_summary for CL=F …")
    from core.quant_engine import quant_engine
    summary = await quant_engine.generate_ai_summary("CL=F")
    print(f"   ✓ Bias: {summary.bias} | Confidence: {summary.confidence_score}")
    print(f"   ✓ Summary: {summary.ai_summary[:100]}…")
    print(f"   ✓ Warnings: {summary.warnings}")

    total_preds = memory_engine.count_predictions("CL=F")
    print(f"   ✓ Total predictions stored for CL=F: {total_preds}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
