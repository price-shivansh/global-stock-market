"""
News Alert Service — monitors market news categories and sends Telegram notifications.
Version 2: Multi-category + TTL-based deduplication (headlines expire after TTL_HOURS).
"""
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from pathlib import Path

from sentiment_analysis import sentiment_analyzer
from telegram_notifier import send_telegram_message
from config import settings

logger = logging.getLogger(__name__)

# ── Persistence path ──────────────────────────────────────────────────────────
_DATA_DIR  = Path(__file__).parent / "data"
_SENT_FILE = _DATA_DIR / "sent_news.json"

# ── Tunables ─────────────────────────────────────────────────────────────────
_MAX_STORED_HEADLINES = 500     # cap JSON file growth
_MAX_ALERTS_PER_CYCLE = 5       # max Telegram messages per check cycle
_DEDUP_TTL_HOURS      = 12      # headlines expire from dedup after this many hours

# Categories to monitor (add/remove as needed)
_WATCHED_CATEGORIES = [
    "Global Markets",
    "Indian Markets",
    "Commodities",
    "Crypto",
]


class NewsAlertService:
    """
    Checks multiple news categories on a configurable interval and sends
    unseen headlines to Telegram. Uses TTL-based deduplication — headlines
    expire after _DEDUP_TTL_HOURS so they won't be silently blocked forever.
    """

    # ── Symbol → label map ────────────────────────────────────────────────────
    _SYMBOL_LABELS: dict = {
        "CL=F":     "🛢 CRUDE OIL",
        "BZ=F":     "🛢 BRENT CRUDE",
        "NG=F":     "🔥 NATURAL GAS",
        "GC=F":     "🪙 GOLD",
        "SI=F":     "🥈 SILVER",
        "HG=F":     "🪨 COPPER",
        "BTC-USD":  "₿ BITCOIN",
        "ETH-USD":  "⟠ ETHEREUM",
        "BNB-USD":  "🟡 BNB",
        "SOL-USD":  "☀ SOLANA",
        "^NSEI":    "📈 NIFTY",
        "^NSEBANK": "🏦 BANKNIFTY",
        "^BSESN":   "📈 SENSEX",
        "^GSPC":    "🇺🇸 S&P 500",
        "^DJI":     "🇺🇸 DOW JONES",
        "^IXIC":    "🇺🇸 NASDAQ",
        "^N225":    "🇯🇵 NIKKEI",
        "^HSI":     "🇭🇰 HANG SENG",
        "^GDAXI":   "🇩🇪 DAX",
        "^FTSE":    "🇬🇧 FTSE 100",
        "^FCHI":    "🇫🇷 CAC 40",
        "USDINR=X": "💱 USD/INR",
        "EURUSD=X": "💶 EUR/USD",
        "GBPUSD=X": "🇬🇧 GBP/USD",
    }

    _TITLE_ASSET_MAP: list = [
        (["crude oil", "oil prices", "oil futures", "wti", "brent oil", "opec", "oil market", "oil price"], "🛢 CRUDE OIL"),
        (["natural gas", "lng", "henry hub", "natgas", "gas storage"],                                       "🔥 NATURAL GAS"),
        (["gold price", "gold market", "bullion", "precious metal", "xau"],                                  "🪙 GOLD"),
        (["silver", "xag"],                                                                                   "🥈 SILVER"),
        (["bitcoin", " btc "],                                                                                "₿ BITCOIN"),
        (["ethereum", " eth "],                                                                               "⟠ ETHEREUM"),
        (["banknifty", "bank nifty"],                                                                        "🏦 BANKNIFTY"),
        (["nifty", "sensex", "nse stocks", "bse stocks"],                                                   "📈 NIFTY"),
        (["dow jones", "dow ", "s&p 500", "nasdaq", "wall street", "us stocks", "fomc", "federal reserve",
          "cpi", "us equities", "us market", "fed "],                                                       "🇺🇸 US EQUITIES"),
        (["ftse", "dax", "cac", "nikkei", "hang seng", "global stocks", "european stock"],                 "🌐 GLOBAL EQUITIES"),
    ]

    _HIGH_PRIORITY_SYMBOLS: set = {"CL=F", "BZ=F", "NG=F", "GC=F", "^NSEI", "^NSEBANK", "BTC-USD", "ETH-USD"}
    _HIGH_PRIORITY_KEYWORDS: list = [
        "crude oil", "wti", "brent", "opec", "natural gas", "natgas", "lng",
        "gold", "bitcoin", "btc", "ethereum", "eth", "nifty", "banknifty",
    ]

    def __init__(self):
        # sent_headlines: dict of {title: ISO-timestamp-string}
        self.sent_headlines: Dict[str, str] = self.load_sent_headlines()
        self._purge_expired()
        logger.info(f"[NewsAlert] Loaded {len(self.sent_headlines)} active (non-expired) headline(s).")
        self.last_cycle_time: datetime | None = None
        self.last_cycle_sent: int = 0
        self.total_sent: int = 0

    # ── TTL-based Persistence ─────────────────────────────────────────────────

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_expired(self, ts_str: str) -> bool:
        try:
            sent_at = datetime.fromisoformat(ts_str)
            return (self._now_utc() - sent_at) > timedelta(hours=_DEDUP_TTL_HOURS)
        except Exception:
            return True  # corrupt timestamp → treat as expired

    def _purge_expired(self) -> int:
        """Remove headlines that have exceeded the TTL. Returns count removed."""
        before = len(self.sent_headlines)
        self.sent_headlines = {
            title: ts for title, ts in self.sent_headlines.items()
            if not self._is_expired(ts)
        }
        removed = before - len(self.sent_headlines)
        if removed:
            logger.info(f"[NewsAlert] Purged {removed} expired headline(s) from dedup cache.")
        return removed

    def load_sent_headlines(self) -> Dict[str, str]:
        """Load sent_news.json. Supports both old list format and new dict format."""
        try:
            if _SENT_FILE.exists():
                with open(_SENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # Migrate old format: treat all as sent 100 hours ago (will all expire)
                    old_ts = (self._now_utc() - timedelta(hours=100)).isoformat()
                    logger.info("[NewsAlert] Migrating old list-format sent_news.json to TTL format.")
                    return {title: old_ts for title in data}
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"[NewsAlert] Could not load sent_news.json: {e}")
        return {}

    def save_sent_headlines(self) -> None:
        """Persist sent headlines dict to JSON, capped at _MAX_STORED_HEADLINES."""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            # Keep only the most recent entries if over limit
            if len(self.sent_headlines) > _MAX_STORED_HEADLINES:
                sorted_items = sorted(self.sent_headlines.items(), key=lambda x: x[1], reverse=True)
                self.sent_headlines = dict(sorted_items[:_MAX_STORED_HEADLINES])
            with open(_SENT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.sent_headlines, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[NewsAlert] Could not save sent_news.json: {e}")

    def is_already_sent(self, title: str) -> bool:
        """Return True if this title was sent within the TTL window."""
        if title not in self.sent_headlines:
            return False
        return not self._is_expired(self.sent_headlines[title])

    # ── Label Helpers ─────────────────────────────────────────────────────────

    def get_category_label(self, category: str) -> str:
        return {
            "Global Markets":  "🌍 GLOBAL MARKETS",
            "Indian Markets":  "🇮🇳 INDIAN MARKETS",
            "Crypto":          "₿ CRYPTO",
            "Commodities":     "🛢 COMMODITIES",
        }.get(category, "📰 MARKET NEWS")

    def get_asset_display_name(self, asset_key: str) -> str:
        return {
            "CRUDE_OIL":        "🛢 CRUDE OIL",
            "BRENT_CRUDE":      "🛢 BRENT CRUDE",
            "NATURAL_GAS":      "🔥 NATURAL GAS",
            "GOLD":             "🪙 GOLD",
            "SILVER":           "🥈 SILVER",
            "BITCOIN":          "₿ BITCOIN",
            "ETHEREUM":         "⟠ ETHEREUM",
            "NIFTY":            "📈 NIFTY",
            "BANKNIFTY":        "🏦 BANKNIFTY",
            "INDIAN_EQUITIES":  "🇮🇳 INDIAN EQUITIES",
            "US_EQUITIES":      "🇺🇸 US EQUITIES",
            "CRYPTO_MARKET":    "₿ DIGITAL ASSETS",
            "COMMODITY_MARKET": "🛢 COMMODITY MARKET",
            "GLOBAL_MACRO":     "🌐 MACRO / EQUITIES",
            "FOREX":            "💱 FOREX",
        }.get(asset_key, f"📰 {asset_key}")

    # ── Message Formatter ─────────────────────────────────────────────────────

    def format_news_message(self, item) -> str:
        # 1. Asset Classification
        asset_key = sentiment_analyzer.classify_primary_asset(
            text=item.title,
            category=getattr(item, 'category', ''),
            related_symbols=getattr(item, 'related_symbols', [])
        )

        # 2. Market Impact Analysis
        impact_score = sentiment_analyzer.analyze_market_impact(item.title, asset_key)
        if impact_score >= 0.15:
            impact_type = "BULLISH"
        elif impact_score <= -0.15:
            impact_type = "BEARISH"
        else:
            impact_type = "NEUTRAL"

        # 3. Trading Relevance
        relevance = sentiment_analyzer.calculate_trading_relevance(item.title, asset_key)

        sentiment_emoji = {
            "BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"
        }.get(impact_type, "➡️")

        try:
            time_str = item.published.strftime("%d %b %Y  %H:%M UTC")
        except Exception:
            time_str = "—"

        cat_label   = self.get_category_label(getattr(item, 'category', ''))
        asset_label = self.get_asset_display_name(asset_key)
        
        # HIGH PRIORITY only if relevance == HIGH
        high_prio = (relevance == "HIGH")

        lines = []
        if high_prio:
            lines.append("🚨 <b>HIGH PRIORITY</b>")
            lines.append("")
        
        lines.append(f"<b>{cat_label}  |  {asset_label}</b>")
        lines.append(f"🎯 <b>Relevance:</b> {relevance}")
        lines.append("")
        lines.append(f"📰 <b>{item.title}</b>")
        lines.append("")
        lines.append(f"🔹 <b>Source:</b> {item.source}")
        lines.append(f"{sentiment_emoji} <b>Sentiment:</b> {impact_type} ({impact_score:+.2f})")
        lines.append(f"🕒 <b>Time:</b> {time_str}")
        lines.append("")
        lines.append(f'<a href="{item.url}">📖 Read full article</a>')
        return "\n".join(lines), asset_key, relevance


    # ── Core Check Cycle ──────────────────────────────────────────────────────

    async def check_and_notify(self) -> int:
        """
        Fetch market news, filter to watched categories, send unseen headlines.
        Returns the number of alerts sent this cycle.
        """
        try:
            news_items = await sentiment_analyzer.fetch_market_news()
        except Exception as e:
            logger.error(f"[NewsAlert] Failed to fetch news: {e}")
            return 0

        # Purge expired entries before checking
        self._purge_expired()

        # Filter to watched categories, newest first
        filtered = [
            n for n in news_items
            if getattr(n, 'category', '') in _WATCHED_CATEGORIES
        ]
        filtered.sort(key=lambda x: x.published, reverse=True)

        sent_count = 0
        newly_sent: Dict[str, str] = {}

        for item in filtered:
            if sent_count >= _MAX_ALERTS_PER_CYCLE:
                break
            if self.is_already_sent(item.title):
                continue

            message, asset_key, relevance = self.format_news_message(item)
            category = getattr(item, 'category', '')
            
            # Pass metadata to telegram_notifier for per-user filter routing
            success = await send_telegram_message(message, asset_key, category, relevance)
            
            if success:
                newly_sent[item.title] = self._now_utc().isoformat()
                sent_count += 1
                logger.info(f"[NewsAlert] Sent: {item.title[:60]}…")
                await asyncio.sleep(0.5)

        if newly_sent:
            self.sent_headlines.update(newly_sent)
            self.save_sent_headlines()

        self.last_cycle_time = self._now_utc()
        self.last_cycle_sent = sent_count
        self.total_sent += sent_count
        logger.info(f"[NewsAlert] Cycle complete — {sent_count} new alert(s) sent. "
                    f"Active dedup cache: {len(self.sent_headlines)} headline(s).")
        return sent_count

    def get_status(self) -> dict:
        """Return a status summary for the /api/news-alert-status endpoint."""
        self._purge_expired()
        return {
            "enabled": getattr(settings, 'TELEGRAM_ENABLED', False),
            "watched_categories": _WATCHED_CATEGORIES,
            "dedup_ttl_hours": _DEDUP_TTL_HOURS,
            "interval_seconds": getattr(settings, 'TELEGRAM_NEWS_INTERVAL', 180),
            "active_dedup_entries": len(self.sent_headlines),
            "last_cycle_time": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "last_cycle_sent": self.last_cycle_sent,
            "total_sent_this_session": self.total_sent,
        }

    # ── Background Loop ───────────────────────────────────────────────────────

    async def run_news_alert_loop(self) -> None:
        interval = getattr(settings, 'TELEGRAM_NEWS_INTERVAL', 180)
        logger.info(f"[NewsAlert] Background loop started — "
                    f"categories={_WATCHED_CATEGORIES}, interval={interval}s, TTL={_DEDUP_TTL_HOURS}h")
        while True:
            try:
                await self.check_and_notify()
            except Exception as e:
                logger.error(f"[NewsAlert] Unhandled error in alert loop: {e}")
            await asyncio.sleep(interval)


# ── Singleton ─────────────────────────────────────────────────────────────────
news_alert_service = NewsAlertService()
