import asyncio
import aiohttp
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# ── Source Weights ────────────────────────────────────────────────────────────

def get_source_weight(source_name: str, category: str = "", asset_key: str = "") -> float:
    """Return a reliability multiplier for a given news source."""
    s = str(source_name).lower()
    
    # Highest tier - official or highly reputed
    if 'eia' in s or 'opec' in s:
        return 2.0
    if 'reuters' in s:
        return 1.6
        
    # High tier - specialized financial / energy / crypto
    if 'coindesk' in s or 'cointelegraph' in s:
        return 1.3
    if 'yahoo' in s:
        return 1.3
    if 'oilprice' in s or 'world oil' in s:
        return 1.25
    if 'investing.com' in s or 'investing' in s:
        return 1.2
    
    # Mid tier - Indian specifics
    if any(x in s for x in ['moneycontrol', 'economic times', 'et markets', 'mint', 'livemint', 'business standard']):
        return 1.15
        
    # Standard fallback / aggregators
    if 'google' in s or 'unknown' in s or not s:
        return 1.0
        
    return 1.0


# ── Generic RSS Fetcher Helper ───────────────────────────────────────────────

async def fetch_rss_feed(url: str, source_name: str, category: str, asset_hint: str = "", limit: int = 15) -> List[Dict]:
    """Generic async RSS fetcher returning normalized dicts."""
    items = []
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'xml')
                    
                    found = soup.find_all('item')[:limit]
                    for item in found:
                        title = item.title.text if item.title else ""
                        link = item.link.text if item.link else ""
                        pub_tag = item.pubDate or item.date
                        pub = pub_tag.text if pub_tag else ""
                        
                        # Sometimes source is provided in RSS
                        src_str = item.source.text if getattr(item, 'source', None) else source_name
                        
                        try:
                            # Try common RSS datetime formats
                            published = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
                        except Exception:
                            try:
                                # Backup format without seconds
                                published = datetime.strptime(pub, "%a, %d %b %Y %H:%M %Z")
                            except Exception:
                                published = datetime.now()
                                
                        items.append({
                            "title": title.strip(),
                            "url": link.strip(),
                            "source": src_str.strip(),
                            "published": published,
                            "category": category,
                            "asset_hint": asset_hint,
                            "source_weight": get_source_weight(src_str, category, asset_hint)
                        })
                else:
                    logger.debug(f"[Fetch] {source_name} returned HTTP {response.status}")
    except Exception as e:
        logger.debug(f"[Fetch] {source_name} feed error: {e}")
        
    return items


# ── Specific Source Fetchers ────────────────────────────────────────────────

async def fetch_google_news(query: str, category: str, asset_hint: str = "") -> List[Dict]:
    """Fetch using Google News RSS search directly."""
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
    return await fetch_rss_feed(url, "Google News", category, asset_hint, limit=15)


async def fetch_yahoo_finance_news(category: str, asset_hint: str = "US_EQUITIES") -> List[Dict]:
    """Fetch top market news from Yahoo Finance RSS."""
    url = "https://finance.yahoo.com/news/rssindex"
    return await fetch_rss_feed(url, "Yahoo Finance", category, asset_hint, limit=10)


async def fetch_oilprice_news(category: str = "Commodities", asset_hint: str = "CRUDE_OIL") -> List[Dict]:
    """Fetch top oil headlines from OilPrice generic feed (if available) or fallback to simple HTML parsing."""
    # Often standard RSS feeds from specialized sites are reliable. 
    # Try generic rss feed. If unavailable we gracefully fail instead of brittle html scraping.
    # OilPrice has an RSS feed: https://oilprice.com/rss/main
    url = "https://oilprice.com/rss/main"
    items = await fetch_rss_feed(url, "OilPrice", category, asset_hint, limit=10)
    
    # If standard feed fails or changes, we want an async fallback
    if not items:
        try:
            url_html = "https://oilprice.com/Energy/Crude-Oil/"
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url_html) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        articles = soup.select('div.categoryArticle')[:5]
                        for article in articles:
                            a_tag = article.find('a', class_='categoryArticle__title')
                            title = a_tag.text.strip() if a_tag else ""
                            link = a_tag['href'] if a_tag else ""
                            if title and link:
                                items.append({
                                    "title": title,
                                    "url": link,
                                    "source": "OilPrice",
                                    "published": datetime.now(), # rough approx
                                    "category": category,
                                    "asset_hint": asset_hint,
                                    "source_weight": get_source_weight("OilPrice")
                                })
        except Exception as e:
            logger.debug(f"[Fetch] OilPrice HTML fallback failed: {e}")
            
    return items


async def fetch_coindesk_news(category: str = "Crypto", asset_hint: str = "CRYPTO_MARKET") -> List[Dict]:
    """Fetch from CoinDesk RSS."""
    # CoinDesk provides a known RSS
    url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    return await fetch_rss_feed(url, "CoinDesk", category, asset_hint, limit=10)


async def fetch_investing_news(category: str, asset_hint: str = "") -> List[Dict]:
    """Fetch from investing.com top news RSS."""
    # Investing.com offers localized feeds, this is standard top news
    url = "https://www.investing.com/rss/news_25.rss"
    return await fetch_rss_feed(url, "Investing.com", category, asset_hint, limit=10)


async def fetch_reuters_market_news(category: str, asset_hint: str = "") -> List[Dict]:
    """Fetch from a public proxy or standard Reuters RSS."""
    # Since reuters official RSS is heavily gated now, use a common aggregator / fallback proxy, or just skip if fail.
    # Using generic Google news query filtered by site:reuters.com as a much more stable proxy for "Reuters" news.
    query = "market news site:reuters.com"
    if asset_hint == "CRUDE_OIL":
        query = "oil price site:reuters.com"
    elif asset_hint == "CRYPTO_MARKET":
        query = "bitcoin crypto site:reuters.com"

    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
    # Label source deliberately to trigger reuters weights
    return await fetch_rss_feed(url, "Reuters via Google", category, asset_hint, limit=5)


async def fetch_eia_energy_news(category: str = "Commodities", asset_hint: str = "NATURAL_GAS") -> List[Dict]:
    """Fetch natural gas / crude reporting from EIA."""
    # EIA has few official feeds. For NatGas, Google site search is most stable.
    query = "natural gas storage site:eia.gov"
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
    return await fetch_rss_feed(url, "EIA", category, asset_hint, limit=3)
