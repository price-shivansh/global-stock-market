import os
import logging
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sentiment_analysis import sentiment_analyzer
from news_history import get_history_path, get_history_stats, save_news_to_excel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sentiment"])


@router.get("/api/sentiment")
async def get_sentiment():
    """Get market sentiment analysis."""
    logger.info("Request started: /api/sentiment")
    try:
        return await sentiment_analyzer.get_market_sentiment()
    except Exception as e:
        logger.exception("Detailed error in /api/sentiment")
        traceback.print_exc()
        return {
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "news_items": [],
            "error": str(e)
        }


@router.get("/api/news")
async def get_news():
    """Get latest market news with sentiment."""
    logger.info("Request started: /api/news")
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()
        return {
            "news":               sentiment.news_items if hasattr(sentiment, "news_items") else [],
            "overall_sentiment":  sentiment.overall_sentiment if hasattr(sentiment, "overall_sentiment") else "NEUTRAL",
            "sentiment_score":    sentiment.sentiment_score if hasattr(sentiment, "sentiment_score") else 0.0,
        }
    except Exception as e:
        logger.exception("Detailed error in /api/news")
        traceback.print_exc()
        return {
            "news": [],
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "error": str(e)
        }


@router.get("/api/news/export")
async def export_news_excel(category: str = "General"):
    """Download the full news history as an Excel (.xlsx) file."""
    try:
        path = get_history_path(category)
        if not os.path.exists(path):
            try:
                await sentiment_analyzer.get_market_sentiment()
            except Exception:
                pass
        if not os.path.exists(path):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"News history file for {category} not found yet. "
                    "Try fetching news first via /api/news."
                ),
            )
        return FileResponse(
            path=path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(path),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Detailed error in /api/news/export for {category}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/news/history")
async def get_news_history_stats(category: Optional[str] = None, date: Optional[str] = None):
    """Get stats about the stored news history Excel file or retrieved archived daily news."""
    logger.info(f"Request started: /api/news/history with category={category}, date={date}")
    try:
        from services.news_archive import news_archive_service
        if date:
            items = news_archive_service.get_by_date(date)
            return {"news": items}
            
        from news_history import get_all_history_stats, get_history_stats
        if category:
            stats = get_history_stats(category)
            return {
                "message":  "Download the full history at /api/news/export?category=...",
                "category": category,
                **stats,
            }
        stats = get_all_history_stats()
        return {
            "message": "Download the full history at /api/news/export?category=...",
            "stats":   stats,
        }
    except Exception as e:
        logger.exception("Detailed error in /api/news/history")
        traceback.print_exc()
        return {"error": str(e)}


@router.get("/api/news/history/dates")
async def get_news_history_dates():
    """Returns a list of all available archive dates (YYYY-MM-DD)."""
    logger.info("Request started: /api/news/history/dates")
    try:
        from services.news_archive import news_archive_service
        dates = news_archive_service.get_available_dates()
        return {"dates": dates}
    except Exception as e:
        logger.exception("Detailed error in /api/news/history/dates")
        traceback.print_exc()
        return {"dates": [], "error": str(e)}

@router.get("/api/news/history/range")
async def get_news_history_range(start: str, end: str):
    """Returns combined archived news from all files in the given date range."""
    logger.info(f"Request started: /api/news/history/range from {start} to {end}")
    try:
        from services.news_archive import news_archive_service
        items = news_archive_service.get_by_date_range(start, end)
        return {"news": items}
    except Exception as e:
        logger.exception(f"Detailed error in /api/news/history/range from {start} to {end}")
        traceback.print_exc()
        return {"news": [], "error": str(e)}


@router.delete("/api/news/history")
async def reset_news_history(category: str):
    """Reset (delete) the news history for a given category."""
    from news_history import reset_history
    try:
        success = reset_history(category)
        if success:
            return {"message": f"Successfully reset history for {category}"}
        raise HTTPException(status_code=500, detail=f"Failed to reset {category}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Detailed error in reset_news_history for {category}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
