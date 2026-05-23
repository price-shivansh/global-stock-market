"""
main.py — Application entry point.

Initialises the FastAPI app, registers all routers, and starts background
tasks on startup.  All route-level logic lives in the routers/ package.

Entry point (unchanged for Render / local dev):
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

# ── Router imports ─────────────────────────────────────────────────────────────
from routers.market        import router as market_router
from routers.signals       import router as signals_router
from routers.sentiment     import router as sentiment_router
from routers.technical     import router as technical_router
from routers.telegram      import router as telegram_router
from routers.backtesting   import router as backtesting_router
from routers.paper_trading import router as paper_trading_router
from routers.websockets    import router as websockets_router
from routers.mobile_routes import router as mobile_router
from routers.quant_routes  import router as quant_router

# ── App initialisation ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time Indian Options Market Signal Dashboard with Technical and Sentiment Analysis",
    version="1.0.0",
)

# ── CORS middleware ────────────────────────────────────────────────────────────
cors_origins = [settings.FRONTEND_URL] if hasattr(settings, "FRONTEND_URL") else ["http://localhost:5173", "http://localhost:3000"]
if getattr(settings, "ALLOW_MOBILE_CORS", True) or settings.DEBUG:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────────
app.include_router(market_router)
app.include_router(signals_router)
app.include_router(sentiment_router)
app.include_router(technical_router)
app.include_router(telegram_router)
app.include_router(backtesting_router)
app.include_router(paper_trading_router)
app.include_router(websockets_router)
app.include_router(quant_router)

if getattr(settings, "MOBILE_APP_API_ENABLED", True):
    app.include_router(mobile_router, prefix="/api/mobile")

# ── System Endpoints ───────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "ok"}


# ── Startup background tasks ───────────────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    from market_stream import stream_manager
    asyncio.create_task(stream_manager.run_stream())
    asyncio.create_task(_paper_trade_auto_close_loop())

    # ── Adaptive Intelligence System ────────────────────────────────────────────
    from core.outcome_tracker import outcome_tracker
    outcome_tracker.start()
    print("[AdaptiveAI] Outcome tracker background task started (evaluates every 5 min).")

    if settings.TELEGRAM_ENABLED:
        from news_alert_service import news_alert_service
        from telegram_notifier import poll_commands
        asyncio.create_task(news_alert_service.run_news_alert_loop())
        asyncio.create_task(poll_commands())
        print("[Telegram] News alert background task started.")
        print("[Telegram] Command listener background task started.")
    else:
        print("[Telegram] Notifications disabled (TELEGRAM_ENABLED=false).")


async def _paper_trade_auto_close_loop():
    """Background loop: auto-close paper trades when SL / Target is hit."""
    from paper_trade import paper_engine
    while True:
        try:
            await paper_engine.update_positions()
        except Exception as e:
            print(f"Error in paper trade auto-close loop: {e}")
        await asyncio.sleep(3)  # check every 3 seconds


# ── Local development entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
