"""
Telegram Notifier — handles multi-user subscriptions and broadcasts via Telegram Bot API using aiohttp.
"""
import aiohttp
import asyncio
import logging
import json
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

# ── API Endpoints ─────────────────────────────────────────────────────────────
TELEGRAM_SEND_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_UPDATES_API = "https://api.telegram.org/bot{token}/getUpdates"


# ── Settings & Default Filters ────────────────────────────────────────────────
DEFAULT_FILTERS = {
    "global": True,
    "crude": True,
    "gas": True,
    "crypto": True,
    "nifty": True,
    "highpriority_only": False
}


# ── Subscriber Manager ────────────────────────────────────────────────────────
class TelegramSubscriberManager:
    """Manages persistent storage of Telegram chat IDs and their filter preferences."""
    def __init__(self):
        self.file_path = Path(__file__).parent / "data" / "telegram_subscribers.json"
        self.subscribers = {}
        self.load_subscribers()
        self._migrate_legacy_id()

    def load_subscribers(self) -> None:
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    subs = data.get("subscribers", {})
                    # Migrate old list format to dict format
                    if isinstance(subs, list):
                        logger.info("[Telegram] Migrated legacy subscriber list to preference-based format.")
                        self.subscribers = {str(chat_id): {"is_active": True, "filters": dict(DEFAULT_FILTERS)} for chat_id in subs}
                        self.save_subscribers()
                    else:
                        self.subscribers = subs
        except Exception as e:
            logger.warning(f"[Telegram] Failed to load subscribers: {e}. Starting fresh.")
            self.subscribers = {}

    def save_subscribers(self) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"subscribers": self.subscribers}, f, indent=2)
        except Exception as e:
            logger.error(f"[Telegram] Failed to save subscribers: {e}")

    def _migrate_legacy_id(self) -> None:
        """Add legacy .env CHAT_ID with default filters if file was empty."""
        if not self.subscribers:
            legacy_id = getattr(settings, 'TELEGRAM_CHAT_ID', '').strip()
            if legacy_id and legacy_id.lstrip('-').isdigit():
                self.subscribers[str(legacy_id)] = {"is_active": True, "filters": dict(DEFAULT_FILTERS)}
                self.save_subscribers()
                logger.info(f"[Telegram] Added legacy TELEGRAM_CHAT_ID ({legacy_id}) as initial subscriber.")

    def update_user_status(self, chat_id: int, is_active: bool) -> bool:
        """Return True if status was changed, False if already in desired state."""
        cid = str(chat_id)
        if cid not in self.subscribers:
            if not is_active:
                return False
            self.subscribers[cid] = {"is_active": True, "filters": dict(DEFAULT_FILTERS)}
            self.save_subscribers()
            return True
        else:
            if self.subscribers[cid].get("is_active") == is_active:
                return False
            self.subscribers[cid]["is_active"] = is_active
            self.save_subscribers()
            return True

    def toggle_filter(self, chat_id: int, filter_key: str) -> bool:
        """Toggles a filter and returns the new boolean value."""
        cid = str(chat_id)
        if cid not in self.subscribers:
            self.subscribers[cid] = {"is_active": True, "filters": dict(DEFAULT_FILTERS)}
        
        current = self.subscribers[cid]["filters"].get(filter_key, False)
        new_val = not current
        self.subscribers[cid]["filters"][filter_key] = new_val
        self.save_subscribers()
        return new_val

    def get_user_prefs(self, chat_id: int) -> dict:
        return self.subscribers.get(str(chat_id))

    def get_all_active(self) -> dict:
        return {cid: prefs for cid, prefs in self.subscribers.items() if prefs.get("is_active", False)}


subscriber_manager = TelegramSubscriberManager()


# ── Filter Logic ─────────────────────────────────────────────────────────────

def should_send_to_user(asset_key: str, category: str, relevance: str, filters: dict) -> bool:
    """Return True if the news matches the user's filter preferences."""
    if filters.get("highpriority_only", False) and relevance != "HIGH":
        return False
        
    if filters.get("global", False) and (category == "Global Markets" or asset_key in ("US_EQUITIES", "GLOBAL_MACRO")):
        return True
    if filters.get("crude", False) and asset_key in ("CRUDE_OIL", "BRENT_CRUDE"):
        return True
    if filters.get("gas", False) and asset_key == "NATURAL_GAS":
        return True
    if filters.get("crypto", False) and (category == "Crypto" or asset_key in ("BITCOIN", "ETHEREUM", "CRYPTO_MARKET")):
        return True
    if filters.get("nifty", False) and (category == "Indian Markets" or asset_key in ("NIFTY", "BANKNIFTY", "INDIAN_EQUITIES")):
        return True
        
    return False

def format_filter_status(prefs: dict) -> str:
    """Format filter preferences for display."""
    filters = prefs.get("filters", {})
    return (
        f"🌍 Global: {'ON' if filters.get('global') else 'OFF'}\n"
        f"🛢 Crude Oil: {'ON' if filters.get('crude') else 'OFF'}\n"
        f"🔥 Natural Gas: {'ON' if filters.get('gas') else 'OFF'}\n"
        f"₿ Crypto: {'ON' if filters.get('crypto') else 'OFF'}\n"
        f"📈 Nifty / Indian Markets: {'ON' if filters.get('nifty') else 'OFF'}\n"
        f"🚨 High Priority Only: {'ON' if filters.get('highpriority_only') else 'OFF'}"
    )


# ── Core Messaging ────────────────────────────────────────────────────────────

async def send_message(chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
    """Send message to a specific chat ID."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        return False

    url = TELEGRAM_SEND_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"[Telegram] Send failed to {chat_id} — HTTP {resp.status}: {body}")
                    return False
                return True
    except Exception as e:
        logger.error(f"[Telegram] Error sending to {chat_id}: {e}")
        return False


async def send_telegram_message(message: str, asset_key: str = "", category: str = "", relevance: str = "") -> bool:
    """
    Broadcasts the message to all active subscribers who match the filter criteria.
    """
    if not getattr(settings, 'TELEGRAM_ENABLED', False):
        logger.debug("[Telegram] Notifications disabled — skipping broadcast.")
        return False

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        return False

    active_subs = subscriber_manager.get_all_active()
    if not active_subs:
        logger.warning("[Telegram] No active subscribers — skipping broadcast.")
        return False

    tasks = []
    for chat_id, prefs in active_subs.items():
        if asset_key and category and relevance:
            if not should_send_to_user(asset_key, category, relevance, prefs.get("filters", {})):
                continue
        tasks.append(send_message(chat_id, message))

    if not tasks:
        logger.debug("[Telegram] Message skipped for all active subscribers (filtered out).")
        return True  # Handled successfully, just no matches

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if r is True)
    
    if success_count > 0:
        logger.info(f"[Telegram] Broadcast successful to {success_count}/{len(tasks)} target(s).")
        return True
    
    logger.error("[Telegram] Broadcast failed for all targeted subscribers.")
    return False


# ── Command Polling Loop ─────────────────────────────────────────────────────

async def handle_update(update: dict):
    """Process incoming /start, /stop, /status, filter commands, and on-demand queries."""
    try:
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip().lower()

        if not chat_id or not text:
            return

        if text == "/start":
            changed = subscriber_manager.update_user_status(chat_id, True)
            prefs = subscriber_manager.get_user_prefs(chat_id)
            if changed:
                msg = (
                    "✅ <b>You are now subscribed to Market News Alerts.</b>\n\n"
                    "By default, you will receive all alerts. Use /filters to customize what you receive.\n\n"
                    "<i>Use /stop to unsubscribe entirely.</i>\n\n"
                    "💡 Tap /help to see all available on-demand market commands."
                )
            else:
                msg = "ℹ️ You are already actively subscribed.\n\n" + format_filter_status(prefs)
            await send_message(str(chat_id), msg)

        elif text == "/stop":
            changed = subscriber_manager.update_user_status(chat_id, False)
            if changed:
                msg = (
                    "🛑 <b>You have been unsubscribed from market alerts.</b>\n\n"
                    "Your preferences have been saved. Send /start anytime to subscribe again."
                )
            else:
                msg = "ℹ️ You are not currently active."
            await send_message(str(chat_id), msg)

        elif text in ("/status", "/filters"):
            prefs = subscriber_manager.get_user_prefs(chat_id)
            is_active = prefs.get("is_active", False) if prefs else False
            
            if not is_active:
                msg = "📡 <b>Status: INACTIVE</b>\n\nYou are not subscribed.\nSend /start to begin receiving alerts."
            else:
                status_block = format_filter_status(prefs)
                msg = (
                    "📡 <b>Status: ACTIVE</b>\n\n"
                    "⚙️ <b>Your Alert Preferences:</b>\n"
                    f"{status_block}\n\n"
                    "<b>Use these commands to toggle:</b>\n"
                    "/global\n/crude\n/gas\n/crypto\n/nifty\n/highpriority"
                )
            await send_message(str(chat_id), msg)

        # ── Toggle Commands ──
        elif text == "/global":
            new_val = subscriber_manager.toggle_filter(chat_id, "global")
            await send_message(str(chat_id), f"🌍 Global market alerts: {'ON' if new_val else 'OFF'}")
        elif text == "/crude":
            new_val = subscriber_manager.toggle_filter(chat_id, "crude")
            await send_message(str(chat_id), f"🛢 Crude oil alerts: {'ON' if new_val else 'OFF'}")
        elif text == "/gas":
            new_val = subscriber_manager.toggle_filter(chat_id, "gas")
            await send_message(str(chat_id), f"🔥 Natural gas alerts: {'ON' if new_val else 'OFF'}")
        elif text == "/crypto":
            new_val = subscriber_manager.toggle_filter(chat_id, "crypto")
            await send_message(str(chat_id), f"₿ Crypto alerts: {'ON' if new_val else 'OFF'}")
        elif text == "/nifty":
            new_val = subscriber_manager.toggle_filter(chat_id, "nifty")
            await send_message(str(chat_id), f"📈 Nifty / Indian market alerts: {'ON' if new_val else 'OFF'}")
        elif text == "/highpriority":
            new_val = subscriber_manager.toggle_filter(chat_id, "highpriority_only")
            if new_val:
                msg = "🚨 High-priority-only mode: ON\n\nYou will now receive ONLY market-moving alerts."
            else:
                msg = "🚨 High-priority-only mode: OFF\n\nYou will receive ALL alerts allowed by your filters."
            await send_message(str(chat_id), msg)
            
        # ── On-Demand Commands ──
        elif text == "/help":
            msg = (
                "🤖 <b>Market Bot Commands</b>\n\n"
                "<b>Overview</b>\n"
                "/market_overview - Full market snapshot\n\n"
                "<b>Summaries</b>\n"
                "/summary_crude - Crude oil sentiment summary\n"
                "/summary_gas - Natural gas sentiment summary\n"
                "/summary_crypto - Crypto / Bitcoin summary\n"
                "/summary_nifty - NIFTY / Indian market summary\n"
                "/summary_global - Global / US market summary\n\n"
                "<b>Latest Headlines</b>\n"
                "/latest_high - Latest HIGH priority alerts\n"
                "/latest_crude - Latest crude oil headlines\n"
                "/latest_gas - Latest natural gas headlines\n"
                "/latest_crypto - Latest crypto headlines\n"
                "/latest_nifty - Latest NIFTY / Indian market headlines\n\n"
                "<b>Preferences</b>\n"
                "/status or /filters - View alert filters\n"
                "/global, /crude, /gas, /crypto, /nifty, /highpriority"
            )
            await send_message(str(chat_id), msg)
            
        elif text == "/market_overview":
            import telegram_helpers as th
            ms, _ = await th.get_current_market_state()
            if not ms.news_items:
                await send_message(str(chat_id), "⏳ Market data is warming up.\nPlease try again in 1–2 minutes.")
            else:
                msg = th.build_market_overview(ms)
                await send_message(str(chat_id), msg)
                
        elif text.startswith("/summary_"):
            import telegram_helpers as th
            ms, _ = await th.get_current_market_state()
            if not ms.news_items:
                await send_message(str(chat_id), "⏳ Market data is warming up.\nPlease try again in 1–2 minutes.")
                return
                
            sym_map = {
                "crude": ("CL=F", "CRUDE OIL SUMMARY", "🛢"),
                "gas": ("NG=F", "NATURAL GAS SUMMARY", "🔥"),
                "crypto": ("BTC-USD", "CRYPTO MARKET SUMMARY", "₿"),
                "nifty": ("^NSEI", "NIFTY / INDIAN MARKET SUMMARY", "📈"),
                "global": ("GLOBAL", "GLOBAL MARKET SUMMARY", "🌍")
            }
            target = text.split("_")[1]
            if target in sym_map:
                sym, title, emoji = sym_map[target]
                msg = th.build_asset_summary(ms, sym, title, emoji)
                await send_message(str(chat_id), msg)

        elif text.startswith("/latest_"):
            import telegram_helpers as th
            ms, items = await th.get_current_market_state()
            if not items:
                await send_message(str(chat_id), "⏳ Market data is warming up.\nPlease try again in 1–2 minutes.")
                return
                
            if text == "/latest_high":
                latest = th.get_top_headlines(items, limit=5, high_priority_only=True)
                msg = th.format_latest_headlines_block("🚨 LATEST HIGH-PRIORITY ALERTS", latest)
                await send_message(str(chat_id), msg)
            else:
                target = text.split("_")[1]
                sym_map = {
                    "crude": ("CL=F", "🛢 LATEST CRUDE OIL HEADLINES"),
                    "gas": ("NG=F", "🔥 LATEST NATURAL GAS HEADLINES"),
                    "crypto": ("BTC-USD", "₿ LATEST CRYPTO HEADLINES"),
                    "nifty": ("^NSEI", "📈 LATEST NIFTY HEADLINES"),
                    "global": ("GLOBAL", "🌍 LATEST GLOBAL HEADLINES")
                }
                if target in sym_map:
                    sym, title = sym_map[target]
                    filtered = th.filter_news_for_asset(items, sym)
                    latest = th.get_top_headlines(filtered, limit=5, high_priority_only=False)
                    msg = th.format_latest_headlines_block(title, latest)
                    await send_message(str(chat_id), msg)

    except Exception as e:
        logger.error(f"[Telegram] Error handling update: {e}")


async def poll_commands():
    """Background polling loop listening for user /commands."""
    if not getattr(settings, 'TELEGRAM_ENABLED', False):
        return

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        return

    url = TELEGRAM_UPDATES_API.format(token=token)
    offset = 0
    poll_interval = 3.0

    logger.info("[Telegram] Command polling loop started.")

    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                # Use long polling (timeout=30) so we only return when data exists
                payload = {"offset": offset, "timeout": 30}
                async with session.get(url, params=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        updates = data.get("result", [])
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            offset = max(offset, update_id + 1)
                            await handle_update(update)
                    elif resp.status in (401, 404):
                        logger.error("[Telegram] Invalid bot token. Polling stopped.")
                        break
                    else:
                        logger.warning(f"[Telegram] Poll HTTP {resp.status}")
                
            except asyncio.TimeoutError:
                pass # expected with long polling
            except Exception as e:
                logger.debug(f"[Telegram] Polling error: {e}")
                await asyncio.sleep(5)  # back off on network error
                
            await asyncio.sleep(poll_interval)
