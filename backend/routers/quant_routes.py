from fastapi import APIRouter, HTTPException, Query
from core.quant_engine import quant_engine
from schemas.quant_schemas import (
    QuantDecision, AIQuantSummary, QuantSummaryV3,
    MemoryResponse, OutcomesResponse, PerformanceResponse, WeightsResponse,
    PredictionSnapshot, OutcomeRecord, AdaptiveWeight, WeightHistory, SetupStats,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/api/quant", tags=["Quant Decision Engine"])

# ── Existing endpoints ─────────────────────────────────────────────────────────

@router.get("/analyze", response_model=QuantDecision)
async def analyze_symbol(symbol: str = Query(..., description="e.g. RELIANCE.NS")):
    """Analyze a symbol and return a QuantDecision (v2)."""
    try:
        return await quant_engine.analyze_symbol(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/summary", response_model=AIQuantSummary)
async def get_ai_summary(symbol: str = Query(..., description="e.g. CL=F")):
    """
    Generate an AI-style market summary (v2 schema).
    Internally uses the v3 engine; stores prediction snapshot.
    """
    try:
        return await quant_engine.generate_ai_summary(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/v3", response_model=QuantSummaryV3)
async def get_summary_v3(symbol: str = Query(..., description="e.g. CL=F")):
    """
    Full v3 intelligence summary.
    Returns regime detection, multi-timeframe alignment, decomposed confidence,
    NO_TRADE/WAIT/TRADE decision with reasons, structured explanation, and risk events.
    """
    try:
        return await quant_engine.generate_full_summary(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# ── Adaptive Intelligence Analytics endpoints ─────────────────────────────────

@router.get("/memory", response_model=MemoryResponse)
async def get_memory(
    symbol: str = Query(..., description="Symbol to retrieve prediction history for"),
    limit:  int = Query(20,  ge=1, le=100, description="Number of snapshots to return"),
):
    """Return stored prediction snapshots for a symbol."""
    try:
        from core.memory_engine import memory_engine
        raw = memory_engine.get_predictions(symbol, limit=limit)
        total = memory_engine.count_predictions(symbol)
        snapshots = []
        for r in raw:
            try:
                snapshots.append(PredictionSnapshot(
                    id=r.get("id"),
                    symbol=r.get("symbol", symbol),
                    timestamp=r.get("timestamp", datetime.now(timezone.utc)),
                    bias=r.get("bias", "Neutral"),
                    confidence_score=r.get("confidence_score", 50.0),
                    technical_score=r.get("technical_score", 50.0),
                    news_score=r.get("news_score", 50.0),
                    rsi_value=r.get("rsi_value"),
                    macd_signal=r.get("macd_signal"),
                    ema_trend=r.get("ema_trend"),
                    momentum_signal=r.get("momentum_signal"),
                    bb_signal=r.get("bb_signal"),
                    market_regime=r.get("market_regime"),
                    atr_pct=r.get("atr_pct"),
                    price_at_prediction=r.get("price_at_prediction", 0.0),
                    active_setups=r.get("active_setups", []),
                ))
            except Exception:
                continue
        return MemoryResponse(symbol=symbol, total_stored=total, predictions=snapshots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outcomes", response_model=OutcomesResponse)
async def get_outcomes(
    symbol: str = Query(..., description="Symbol to retrieve outcomes for"),
    limit:  int = Query(50,  ge=1, le=200),
):
    """Return evaluated prediction outcomes for a symbol."""
    try:
        from core.memory_engine import memory_engine
        raw = memory_engine.get_outcomes(symbol, limit=limit)
        records = []
        for r in raw:
            try:
                records.append(OutcomeRecord(
                    id=r.get("id"),
                    prediction_id=r["prediction_id"],
                    horizon=r["horizon"],
                    price_at_outcome=r["price_at_outcome"],
                    price_change_pct=r["price_change_pct"],
                    outcome=r["outcome"],
                    evaluated_at=r["evaluated_at"],
                ))
            except Exception:
                continue
        return OutcomesResponse(symbol=symbol, outcomes=records)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    symbol: str = Query(..., description="Symbol to get setup performance for"),
):
    """Return per-setup win-rates and overall performance statistics."""
    try:
        from core.performance_tracker import performance_tracker
        data = performance_tracker.get_performance_summary(symbol)
        setups = []
        for s in data.get("setups", []):
            try:
                setups.append(SetupStats(
                    setup_name=s["setup_name"],
                    symbol=s["symbol"],
                    total_predictions=s["total_predictions"],
                    correct_count=s["correct_count"],
                    incorrect_count=s["incorrect_count"],
                    neutral_count=s.get("neutral_count", 0),
                    win_rate=s["win_rate"],
                    avg_return_pct=s["avg_return_pct"],
                    last_updated=s.get("last_updated"),
                ))
            except Exception:
                continue
        return PerformanceResponse(
            symbol=symbol,
            setups=setups,
            overall_win_rate=data.get("overall_win_rate", 0.0),
            total_evaluated=data.get("total_evaluated", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weights", response_model=WeightsResponse)
async def get_weights():
    """Return current adaptive weights vs. defaults, and recent change history."""
    try:
        from core.memory_engine import memory_engine
        raw_weights  = memory_engine.get_all_weights()
        raw_history  = memory_engine.get_weight_history(limit=20)
        weights = [
            AdaptiveWeight(
                weight_key=w["weight_key"],
                symbol=w["symbol"],
                value=w["value"],
                default_value=w["default_value"],
                last_updated=w.get("last_updated"),
            )
            for w in raw_weights
        ]
        history = [
            WeightHistory(
                id=h.get("id"),
                weight_key=h["weight_key"],
                symbol=h["symbol"],
                old_value=h["old_value"],
                new_value=h["new_value"],
                reason=h["reason"],
                changed_at=h["changed_at"],
            )
            for h in raw_history
        ]
        return WeightsResponse(weights=weights, recent_changes=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", status_code=202)
async def trigger_evaluation():
    """
    Manually trigger an outcome evaluation cycle (useful for testing).
    Returns immediately; evaluation runs in background.
    """
    import asyncio
    from core.outcome_tracker import outcome_tracker
    asyncio.create_task(outcome_tracker.run_evaluation_batch())
    return {"message": "Evaluation batch triggered in background."}

