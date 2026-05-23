"""
routers/sentiment.py — Sentiment analysis and news endpoints.
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sentiment_analysis import sentiment_analyzer
from news_history import get_history_path, get_history_stats, save_news_to_excel

router = APIRouter(tags=["sentiment"])


@router.get("/api/sentiment")
async def get_sentiment():
    """Get market sentiment analysis."""
    try:
        return await sentiment_analyzer.get_market_sentiment()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/news")
async def get_news():
    """Get latest market news with sentiment."""
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()
        return {
            "news":               sentiment.news_items,
            "overall_sentiment":  sentiment.overall_sentiment,
            "sentiment_score":    sentiment.sentiment_score,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/news/export")
async def export_news_excel(category: str = "General"):
    """Download the full news history as an Excel (.xlsx) file."""
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


@router.get("/api/news/history")
async def get_news_history_stats(category: Optional[str] = None, date: Optional[str] = None):
    """Get stats about the stored news history Excel file or retrieved archived daily news."""
    from services.news_archive import news_archive_service
    if date:
        items = news_archive_service.get_by_date(date)
        return {"news": items}
        
    from news_history import get_all_history_stats, get_history_stats
    try:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/news/history/dates")
async def get_news_history_dates():
    """Returns a list of all available archive dates (YYYY-MM-DD)."""
    from services.news_archive import news_archive_service
    dates = news_archive_service.get_available_dates()
    return {"dates": dates}

@router.get("/api/news/history/range")
async def get_news_history_range(start: str, end: str):
    """Returns combined archived news from all files in the given date range."""
    from services.news_archive import news_archive_service
    items = news_archive_service.get_by_date_range(start, end)
    return {"news": items}


@router.delete("/api/news/history")
async def reset_news_history(category: str):
    """Reset (delete) the news history for a given category."""
    from news_history import reset_history
    try:
        success = reset_history(category)
        if success:
            return {"message": f"Successfully reset history for {category}"}
        raise HTTPException(status_code=500, detail=f"Failed to reset {category}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
