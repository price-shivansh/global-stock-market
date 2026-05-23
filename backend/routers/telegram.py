"""
routers/telegram.py — Telegram bot test and status endpoints.
"""
from fastapi import APIRouter, HTTPException
from telegram_notifier import send_telegram_message
from news_alert_service import news_alert_service

router = APIRouter(tags=["telegram"])


@router.post("/api/test-telegram-message")
async def test_telegram_message():
    """Send a simple connectivity test message to Telegram."""
    success = await send_telegram_message(
        "✅ <b>Telegram bot connected successfully!</b>\n"
        "Your trading dashboard is online and sending notifications."
    )
    if success:
        return {"status": "ok", "message": "Test message sent to Telegram."}
    raise HTTPException(
        status_code=500,
        detail="Failed to send Telegram message. Check BOT_TOKEN and CHAT_ID.",
    )


@router.post("/api/test-telegram-news")
async def test_telegram_news():
    """Manually run one full news check cycle (respects dedup — sends only unseen headlines)."""
    try:
        sent = await news_alert_service.check_and_notify()
        return {
            "status":  "ok",
            "sent":    sent,
            "message": (
                f"{sent} new alert(s) sent."
                if sent
                else "No new headlines found (all already sent or no news)."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/news-alert-status")
async def news_alert_status():
    """Return current state of the news alert loop: last cycle, dedup cache size, categories."""
    return news_alert_service.get_status()
