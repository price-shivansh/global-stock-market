import pytz
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Any
from models import NewsItem, MarketSentiment
from sentiment_analysis import sentiment_analyzer

# ── 1. State Retrieval Helper ────────────────────────────────────────────────

async def get_current_market_state() -> Tuple[MarketSentiment, List[NewsItem]]:
    """
    Retrieves current market state gracefully using purely cached data if possible.
    If the cache is empty, it makes a single fetch as a fallback.
    Returns: (market_sentiment, news_items_list)
    """
    # Attempt to grab cached sentiment
    # For a purely cached approach, we can check if news_cache has data
    if "market" in sentiment_analyzer.news_cache and sentiment_analyzer.cache_timestamp:
        news_items = sentiment_analyzer.news_cache["market"]
        # re-compute high-level MarketSentiment quickly from cached items
        avg_score = sentiment_analyzer.get_weighted_sentiment(news_items)
        bull_count = sum(1 for n in news_items if n.sentiment.value == "BULLISH")
        bear_count = sum(1 for n in news_items if n.sentiment.value == "BEARISH")
        neut_count = sum(1 for n in news_items if n.sentiment.value == "NEUTRAL")
        
        # Avoid circular import, TRACKED_ASSETS from sentiment_analysis
        from sentiment_analysis import TRACKED_ASSETS
        asset_sentiments = {sym: sentiment_analyzer.get_asset_sentiment(sym, news_items)
                            for sym in TRACKED_ASSETS}
                            
        from models import SentimentType, MarketSentiment
        ms = MarketSentiment(
            overall_sentiment=sentiment_analyzer.get_sentiment_type(avg_score),
            sentiment_score=round(avg_score, 3),
            bullish_count=bull_count,
            bearish_count=bear_count,
            neutral_count=neut_count,
            news_items=news_items,
            last_updated=sentiment_analyzer.cache_timestamp,
            asset_sentiments=asset_sentiments
        )
        return ms, news_items
    else:
        # Cache is empty, attempt one fetch
        ms = await sentiment_analyzer.get_market_sentiment()
        return ms, ms.news_items


# ── 2. Formatting Helpers ────────────────────────────────────────────────────

def format_sentiment_label(sentiment_score: float) -> str:
    from models import SentimentType
    if sentiment_score >= 0.15:
        return f"🟢 <b>BULLISH</b> (+{abs(sentiment_score):.2f})"
    elif sentiment_score <= -0.15:
        return f"🔴 <b>BEARISH</b> (-{abs(sentiment_score):.2f})"
    else:
        # use sign for neutral too appropriately 
        sign = "+" if sentiment_score >= 0 else "-"
        return f"⚪ <b>NEUTRAL</b> ({sign}{abs(sentiment_score):.2f})"

def format_sentiment_label_simple(sentiment: str) -> str:
    if sentiment.upper() == "BULLISH": return "🟢 <b>BULLISH</b>"
    if sentiment.upper() == "BEARISH": return "🔴 <b>BEARISH</b>"
    return "⚪ <b>NEUTRAL</b>"

def format_asset_emoji(asset_key: str) -> str:
    key = asset_key.upper()
    if key in ("CRUDE_OIL", "BRENT_CRUDE", "CL=F", "BZ=F"): return "🛢"
    if key in ("NATURAL_GAS", "NG=F"): return "🔥"
    if key in ("BITCOIN", "ETHEREUM", "CRYPTO_MARKET", "BTC-USD", "ETH-USD"): return "₿"
    if key in ("GOLD", "GC=F"): return "🥇"
    if key in ("NIFTY", "BANKNIFTY", "INDIAN_EQUITIES", "^NSEI", "^NSEBANK"): return "📈"
    if key in ("US_EQUITIES", "GLOBAL_MACRO", "GLOBAL", "Global Markets"): return "🌍"
    return "📊"

def get_ist_time(dt: datetime) -> str:
    """Format a datetime to IST clearly."""
    try:
        if dt.tzinfo is None:
            # Assume local server time, convert to UTC then IST
            dt = dt.replace(tzinfo=timezone.utc)
        ist = pytz.timezone('Asia/Kolkata')
        dt_ist = dt.astimezone(ist)
        return dt_ist.strftime("%I:%M %p IST")
    except Exception:
        # Fallback to local representation
        return dt.strftime("%I:%M %p Local")

def filter_news_for_asset(news_items: List[NewsItem], target: str) -> List[NewsItem]:
    """Filter news matching an asset symbol exactly OR a general asset key/category."""
    matched = []
    target_up = target.upper()
    
    for n in news_items:
        rels = [r.upper() for r in n.related_symbols]
        cat = n.category.upper()
        
        # Match symbol
        if target_up in rels:
            matched.append(n)
            continue
            
        # Match categories based on target loosely
        if target_up in ("CL=F", "BZ=F", "CRUDE_OIL") and ("CRUDE_OIL" in rels or "BRENT_CRUDE" in rels):
            matched.append(n)
        elif target_up in ("NG=F", "NATURAL_GAS") and "NATURAL_GAS" in rels:
            matched.append(n)
        elif target_up in ("BTC-USD", "ETH-USD", "CRYPTO_MARKET", "CRYPTO") and (cat == "CRYPTO" or "CRYPTO_MARKET" in rels or "BITCOIN" in rels):
            matched.append(n)
        elif target_up in ("^NSEI", "^NSEBANK", "NIFTY", "INDIAN_EQUITIES") and (cat == "INDIAN MARKETS" or "NIFTY" in rels or "INDIAN_EQUITIES" in rels):
            matched.append(n)
        elif target_up in ("US_EQUITIES", "GLOBAL_MACRO", "GLOBAL") and (cat == "GLOBAL MARKETS" or "US_EQUITIES" in rels or "GLOBAL_MACRO" in rels):
            matched.append(n)
            
    return matched

def get_top_headlines(news_items: List[NewsItem], limit: int = 3, high_priority_only: bool = False) -> List[NewsItem]:
    """Sort items by publish time optionally filtering by high relevance."""
    # Assuming sentiment_analyzer handles relevance directly or we approximate high impact via sentiment
    def is_high(n: NewsItem) -> bool:
        from sentiment_analysis import sentiment_analyzer
        analysis_text = f"{n.title} {n.source} {n.category}"
        if sentiment_analyzer.is_commodity_news(analysis_text):
            return sentiment_analyzer.calculate_trading_relevance(analysis_text, "COMMODITY_MARKET") == "HIGH"
        else:
            return sentiment_analyzer.calculate_trading_relevance(analysis_text, "GLOBAL_MACRO") == "HIGH"
            
    items = news_items
    if high_priority_only:
        items = [n for n in items if is_high(n)]
        
    # Sort newest
    items.sort(key=lambda x: x.published, reverse=True)
    return items[:limit]


# ── 3. View Builders ─────────────────────────────────────────────────────────

def build_market_overview(ms: MarketSentiment) -> str:
    """Builds the compact /market_overview response."""
    lines = ["🌍 <b>MARKET OVERVIEW</b>", ""]
    
    assets = ms.asset_sentiments or {}
    
    # Extract
    g_score = sentiment_analyzer.get_weighted_sentiment(filter_news_for_asset(ms.news_items, "GLOBAL"))
    lines.append(f"🌍 Global: {format_sentiment_label(g_score)}")
    
    cl_score = assets.get("CL=F", {}).get("sentiment_score", 0.0)
    lines.append(f"🛢 Crude Oil: {format_sentiment_label(cl_score)}")
    
    ng_score = assets.get("NG=F", {}).get("sentiment_score", 0.0)
    lines.append(f"🔥 Natural Gas: {format_sentiment_label(ng_score)}")
    
    btc_score = assets.get("BTC-USD", {}).get("sentiment_score", 0.0)
    lines.append(f"₿ Bitcoin: {format_sentiment_label(btc_score)}")
    
    nifty_score = assets.get("^NSEI", {}).get("sentiment_score", 0.0)
    lines.append(f"📈 NIFTY: {format_sentiment_label(nifty_score)}")
    
    lines.append("\n🚨 <b>Top High-Priority Headlines</b>")
    high_items = get_top_headlines(ms.news_items, limit=3, high_priority_only=True)
    if high_items:
        for i, h in enumerate(high_items, 1):
            short_title = h.title[:75] + "..." if len(h.title) > 75 else h.title
            lines.append(f"{i}. {short_title}")
    else:
        lines.append("<i>No recent high priority alerts.</i>")
        
    lines.append(f"\n⏰ Updated: {get_ist_time(ms.last_updated)}")
    return "\n".join(lines)


def build_asset_summary(ms: MarketSentiment, symbol: str, title: str, emoji: str) -> str:
    """Builds summary for a specific asset (Crude, Gas, Crypto, Nifty)."""
    if symbol == "GLOBAL":
        items = filter_news_for_asset(ms.news_items, "GLOBAL")
        score = sentiment_analyzer.get_weighted_sentiment(items)
        bull = sum(1 for n in items if n.sentiment.value == "BULLISH")
        bear = sum(1 for n in items if n.sentiment.value == "BEARISH")
        neut = sum(1 for n in items if n.sentiment.value == "NEUTRAL")
        rel_len = len(items)
    else:
        assets = ms.asset_sentiments or {}
        asset_info = assets.get(symbol, {})
        score = asset_info.get("sentiment_score", 0.0)
        bull = asset_info.get("bullish_count", 0)
        bear = asset_info.get("bearish_count", 0)
        neut = asset_info.get("neutral_count", 0)
        rel_len = asset_info.get("relevant_news_count", 0)
        items = filter_news_for_asset(ms.news_items, symbol)
        
    lines = [f"{emoji} <b>{title}</b>\n"]
    lines.append(f"📊 Sentiment: {format_sentiment_label(score)}")
    lines.append(f"🟢 Bullish: {bull}")
    lines.append(f"🔴 Bearish: {bear}")
    lines.append(f"⚪ Neutral: {neut}")
    lines.append(f"📰 Relevant Headlines: {rel_len}\n")
    
    lines.append("<b>Top Headlines</b>")
    top_items = get_top_headlines(items, limit=3, high_priority_only=False)
    if top_items:
        for i, h in enumerate(top_items, 1):
             short_title = h.title[:75] + "..." if len(h.title) > 75 else h.title
             lines.append(f"{i}. {short_title}")
    else:
        lines.append("<i>No recent headlines.</i>")
        
    lines.append(f"\n⏰ Updated: {get_ist_time(ms.last_updated)}")
    return "\n".join(lines)


def format_latest_headlines_block(title: str, items: List[NewsItem]) -> str:
    """Builds latest headlines list for /latest_* commands."""
    lines = [f"<b>{title}</b>\n"]
    if not items:
        lines.append("<i>No recent headlines found.</i>")
    else:
        # Re-use relevance logic from sentiment_analyzer to attach HIGH/MEDIUM label
        from sentiment_analysis import sentiment_analyzer
        for i, h in enumerate(items, 1):
            short_title = h.title[:90] + "..." if len(h.title) > 90 else h.title
            sent_label = format_sentiment_label_simple(h.sentiment.value)
            
            analysis_text = f"{h.title} {h.source} {h.category}"
            if sentiment_analyzer.is_commodity_news(analysis_text):
                rel = sentiment_analyzer.calculate_trading_relevance(analysis_text, "COMMODITY_MARKET")
            else:
                rel = sentiment_analyzer.calculate_trading_relevance(analysis_text, "GLOBAL_MACRO")
                
            # If dealing with high_priority_only list, we know rel is HIGH. Otherwise output dynamic.
            emoji = "🚨" if rel == "HIGH" else "📌"
            
            lines.append(f"{i}. {sent_label} | {rel}")
            lines.append(f"{emoji} {short_title}")
            lines.append(f"<i>Source: {h.source}</i>\n")
            
    return "\n".join(lines)
