"""
test_v3_engine.py — Smoke test for Quant Intelligence Engine v3
Run from backend/: python test_v3_engine.py
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=== QUANT v3 INTELLIGENCE ENGINE SMOKE TEST ===")

    # 1. Risk Engine
    print("\n[1/6] RiskEngine...")
    from core.risk_engine import risk_engine
    r = risk_engine.get_risk_events("CL=F")
    ev_count = len(r["events"])
    penalty  = r["total_penalty"]
    print(f"  PASS: {ev_count} events found, total_penalty={penalty}")

    # 2. Market Context
    print("\n[2/6] MarketContext...")
    from data_fetcher import data_fetcher
    from core.market_context import market_context
    from indicator_engine import indicator_engine

    df = await data_fetcher.fetch_stock_data("CL=F", period="3mo", interval="1d")
    assert df is not None and not df.empty, "Failed to fetch CL=F data"
    ta = indicator_engine.generate_technical_summary(df)

    signals = {
        "ema_trend": "ABOVE", "momentum_signal": "BUY",
        "rsi_value": 52.0, "macd_signal": "BUY", "bb_signal": "NEUTRAL"
    }
    regime_data = market_context.classify_regime(df, signals, 60.0, 70.0, "CL=F")
    print(f"  PASS: regime={regime_data['label']}, structure={regime_data['structure']}, atr_pct={regime_data['atr_pct']}")
    print(f"        desc: {regime_data['description'][:80]}")

    # 3. Timeframe Engine
    print("\n[3/6] TimeframeEngine...")
    from core.timeframe_engine import timeframe_engine
    tf_data = await timeframe_engine.analyze("CL=F")
    print(f"  PASS: alignment={tf_data['alignment']}, score={tf_data['alignment_score']}")
    b4h  = tf_data["tf_4h"]["bias"]
    b1h  = tf_data["tf_1h"]["bias"]
    b15m = tf_data["tf_15m"]["bias"]
    print(f"        4H={b4h} | 1H={b1h} | 15m={b15m}")
    print(f"        {tf_data['alignment_description'][:80]}")

    # 4. Confidence Engine
    print("\n[4/6] ConfidenceEngine...")
    from core.confidence_engine import confidence_engine
    from core.memory_engine import memory_engine

    weights = {k: memory_engine.get_weight(k, "GLOBAL")
               for k in ["RSI_MULTIPLIER", "MACD_MULTIPLIER", "EMA_MULTIPLIER",
                          "MOMENTUM_MULTIPLIER", "BB_MULTIPLIER"]}
    conf_data = confidence_engine.compute(
        indicator_signals=signals,
        news_score_100=60.0,
        alignment_score=tf_data["alignment_score"],
        regime=regime_data["label"],
        risk_events=r,
        adaptive_weights=weights,
        ta_summary=ta,
    )
    print(f"  PASS: total={conf_data['total']}, raw_before_penalty={conf_data['raw_before_penalty']}")
    comps = conf_data["components"]
    print(f"        technical={comps['technical']} | sentiment={comps['sentiment']} | alignment={comps['timeframe_alignment']} | regime={comps['regime']}")
    penalties = conf_data["penalties"]
    print(f"        penalties ({len(penalties)}): {[p['reason'][:40] for p in penalties]}")

    # 5. Trade Filter
    print("\n[5/6] TradeFilter...")
    from core.trade_filter import trade_filter
    state, reasons = trade_filter.evaluate(
        bias="Bullish",
        confidence_breakdown=conf_data,
        regime=regime_data["label"],
        alignment=tf_data["alignment"],
        structure=regime_data["structure"],
        risk_events=r,
        indicator_signals=signals,
        ta_summary=ta,
    )
    print(f"  PASS: trade_state={state}")
    for reason in reasons[:3]:
        print(f"        - {reason[:90]}")

    # 6. Full v3 pipeline
    print("\n[6/6] generate_full_summary (v3) for CL=F...")
    from core.quant_engine import quant_engine
    v3 = await quant_engine.generate_full_summary("CL=F")
    print(f"  PASS: bias={v3.bias}, trade_state={v3.trade_state}, confidence={v3.confidence.total}")
    print(f"  PASS: regime={v3.regime.label}, structure={v3.regime.structure}")
    print(f"  PASS: alignment={v3.timeframes.alignment}")
    print(f"  PASS: supporting_factors ({len(v3.explanation.supporting_factors)}):")
    for f in v3.explanation.supporting_factors[:2]:
        print(f"        - {f[:80]}")
    print(f"  PASS: weakening_factors ({len(v3.explanation.weakening_factors)}):")
    for f in v3.explanation.weakening_factors[:2]:
        print(f"        - {f[:80]}")
    print(f"  PASS: invalidation_conditions ({len(v3.explanation.invalidation_conditions)}):")
    for c in v3.explanation.invalidation_conditions[:2]:
        print(f"        - {c[:80]}")
    print(f"  PASS: risk_events={len(v3.risk_events)}")
    print(f"  PASS: ai_summary: {v3.explanation.ai_summary}")
    print(f"  PASS: regime_context: {v3.explanation.regime_context[:100]}")
    print(f"  PASS: confidence_explanation: {v3.explanation.confidence_explanation[:100]}")

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
