"""
routers/mobile_routes.py - Mobile-specific API endpoints.

Thin wrappers around existing backend services used by the web dashboard.
Returns simplified, mobile-friendly JSON payloads.

Registered in main.py with prefix="/api/mobile", so paths here are
relative to that prefix:
  /news                  -> GET /api/mobile/news
  /news/history          -> GET /api/mobile/news/history?date=YYYY-MM-DD
  /news/history/dates    -> GET /api/mobile/news/history/dates
  /sentiment             -> GET /api/mobile/sentiment
  /market-overview       -> GET /api/mobile/market-overview

Services reused (no logic duplicated):
  - sentiment_analyzer.get_market_sentiment()   (news + overall sentiment)
  - services.news_archive.news_archive_service  (historical news by date)
  - data_fetcher.get_index_data()               (nifty / banknifty / sensex)
  - data_fetcher.get_multiple_stocks()          (gainers/losers)
  - data_fetcher.get_top_gainers_losers()       (sorted top movers)
"""
import hashlib
from fastapi import APIRouter, HTTPException

from sentiment_analysis import sentiment_analyzer
from data_fetcher import data_fetcher
from config import settings


# -- Shared helpers ------------------------------------------------------------

def _compute_relevance(title: str, source: str, category: str) -> str:
    """
    Reuse the same relevance logic already used by telegram_helpers.py.
    Returns 'HIGH', 'MEDIUM', or 'LOW'.
    """
    analysis_text = f"{title} {source} {category}"
    if sentiment_analyzer.is_commodity_news(analysis_text):
        asset_key = "COMMODITY_MARKET"
    elif any(kw in analysis_text.lower() for kw in ['nifty', 'sensex', 'nse', 'bse', 'rbi', 'sebi']):
        asset_key = "NIFTY"
    elif any(kw in analysis_text.lower() for kw in ['bitcoin', 'crypto', 'btc', 'ethereum']):
        asset_key = "BITCOIN"
    else:
        asset_key = "GLOBAL_MACRO"
    return sentiment_analyzer.calculate_trading_relevance(analysis_text, asset_key)


def _build_summary(title: str, source: str, category: str, sentiment_str: str, score: float) -> str:
    """
    Build a concise, Telegram-style summary string from available structured fields.
    The news pipeline stores headlines only (no article body), so we construct
    a contextual summary the same way telegram_helpers.py formats alert bodies.
    """
    sign = "+" if score >= 0 else "-"
    score_str = f"{sign}{abs(score):.2f}"
    sent_upper = str(sentiment_str).upper().replace("SENTIMENTTYPE.", "")
    return (
        f"{title}\n\n"
        f"Source: {source} | {category}\n"
        f"Sentiment signal: {sent_upper} ({score_str})"
    )

router = APIRouter(tags=["mobile"])


# -- Formatters ----------------------------------------------------------------

def _format_news_item_obj(item, index=None):
    """
    Format a NewsItem *object* (from sentiment_analyzer) into a compact dict.
    NewsItem has attributes: title, source, url, published, sentiment,
    sentiment_score, related_symbols, category, source_weight.
    """
    title_bytes = item.title.encode("utf-8")
    item_id = hashlib.md5(title_bytes).hexdigest()[:8]
    if index is not None:
        item_id = f"{item_id}-{index}"

    # sentiment may be a SentimentType enum -- convert to plain string
    sentiment_val = item.sentiment
    if hasattr(sentiment_val, "value"):
        sentiment_val = sentiment_val.value

    score = round(getattr(item, "sentiment_score", 0.0), 3)
    relevance = _compute_relevance(item.title, item.source, item.category)
    summary = _build_summary(item.title, item.source, item.category, str(sentiment_val), score)

    return {
        "id": item_id,
        "title": item.title,
        "source": item.source,
        "published_at": (
            item.published.isoformat()
            if hasattr(item.published, "isoformat")
            else str(item.published)
        ),
        "category": item.category,
        "sentiment": str(sentiment_val),
        "sentiment_score": score,
        "relevance": relevance,
        "related_symbol": item.related_symbols[0] if item.related_symbols else None,
        "all_symbols": list(item.related_symbols) if item.related_symbols else [],
        "priority": item.source_weight,
        "url": item.url,
        "summary": summary,
    }


def _format_news_item_dict(item: dict, index=None):
    """
    Format a news *dict* returned by news_archive_service.get_by_date().
    Keys: title, source, url, published, sentiment, sentiment_score,
          category, related_symbols.
    """
    title = item.get("title", "")
    title_bytes = title.encode("utf-8")
    item_id = hashlib.md5(title_bytes).hexdigest()[:8]
    if index is not None:
        item_id = f"{item_id}-{index}"

    related = item.get("related_symbols", [])
    related_symbol = related[0] if isinstance(related, list) and related else None

    source = item.get("source", "")
    category = item.get("category", "")
    sentiment_str = str(item.get("sentiment", "NEUTRAL")).replace("SentimentType.", "")
    score = float(item.get("sentiment_score", 0.0)) if item.get("sentiment_score") else 0.0
    relevance = _compute_relevance(title, source, category)
    summary = _build_summary(title, source, category, sentiment_str, score)

    return {
        "id": item_id,
        "title": title,
        "source": source,
        "published_at": str(item.get("published", "")),
        "category": category,
        "sentiment": sentiment_str,
        "sentiment_score": round(score, 3),
        "relevance": relevance,
        "related_symbol": related_symbol,
        "all_symbols": item.get("related_symbols", []) if isinstance(item.get("related_symbols"), list) else [],
        "priority": 1.0,
        "url": item.get("url", ""),
        "summary": summary,
    }


# -- Routes --------------------------------------------------------------------

@router.get("/news")
async def get_mobile_news():
    """
    Latest live news feed, simplified for mobile.
    Reuses: sentiment_analyzer.get_market_sentiment() -> .news_items (NewsItem objects)
    """
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()
        formatted = [
            _format_news_item_obj(item, i)
            for i, item in enumerate(sentiment.news_items)
        ]
        return {"news": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/history")
async def get_mobile_news_history(date: str):
    """
    Archived news for a given date (YYYY-MM-DD), simplified for mobile.
    Reuses: services.news_archive.news_archive_service.get_by_date()
    NOTE: archive returns plain dicts, not NewsItem objects.
    """
    try:
        from services.news_archive import news_archive_service
        items = news_archive_service.get_by_date(date)
        formatted = [
            _format_news_item_dict(item, i)
            for i, item in enumerate(items)
        ]
        return {"news": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/history/dates")
async def get_mobile_news_history_dates():
    """
    Available archive dates for the mobile date picker.
    Reuses: services.news_archive.news_archive_service.get_available_dates()
    """
    try:
        from services.news_archive import news_archive_service
        dates = news_archive_service.get_available_dates()
        return {"dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment")
async def get_mobile_sentiment():
    """
    Simplified overall sentiment summary.
    Reuses: sentiment_analyzer.get_market_sentiment()
    """
    try:
        sentiment = await sentiment_analyzer.get_market_sentiment()

        total = sentiment.bullish_count + sentiment.bearish_count + sentiment.neutral_count
        if total == 0:
            total = 1  # prevent division-by-zero

        # overall_sentiment may be a SentimentType enum
        overall = sentiment.overall_sentiment
        if hasattr(overall, "value"):
            overall = overall.value

        return {
            "overall_sentiment": str(overall),
            "score": sentiment.sentiment_score,
            "bullish_percent": round((sentiment.bullish_count / total) * 100, 1),
            "bearish_percent": round((sentiment.bearish_count / total) * 100, 1),
            "neutral_percent": round((sentiment.neutral_count / total) * 100, 1),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-overview")
async def get_mobile_market_overview():
    """
    Simplified market overview: Nifty/BankNifty/Sensex + top gainers/losers.
    Reuses:
      - data_fetcher.get_index_data()
      - data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
      - data_fetcher.get_top_gainers_losers()
    """
    try:
        indices = await data_fetcher.get_index_data()
        indian_stocks = await data_fetcher.get_multiple_stocks(settings.STOCK_SYMBOLS)
        gainers, losers = await data_fetcher.get_top_gainers_losers(indian_stocks)

        def _slim(s):
            if s is None:
                return None
            return {
                "symbol": s.symbol,
                "name": s.name,
                "price": s.price,
                "change_percent": s.change_percent,
                "change": s.change,
            }

        nifty_obj = indices.get("nifty") if isinstance(indices, dict) else None
        banknifty_obj = indices.get("banknifty") if isinstance(indices, dict) else None
        sensex_obj = indices.get("sensex") if isinstance(indices, dict) else None

        return {
            "nifty": _slim(nifty_obj),
            "banknifty": _slim(banknifty_obj),
            "sensex": _slim(sensex_obj),
            "top_gainers": [_slim(s) for s in gainers[:5]],
            "top_losers": [_slim(s) for s in losers[:5]],
            "timestamp": (
                nifty_obj.timestamp.isoformat()
                if nifty_obj and hasattr(nifty_obj, "timestamp") and nifty_obj.timestamp
                else None
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
