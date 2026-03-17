"""
market_stream.py — Real-Time WebSocket Market Streamer
Manages active WebSocket connections and broadcasts live price ticks.
Price data is fetched from yfinance every 2s; when rate-limited,
a ±0.15% simulated tick is applied to keep the stream alive.
"""
import asyncio
import random
import json
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from config import settings

logger = logging.getLogger(__name__)

# ── Symbols to stream (rotated so yfinance isn't hammered) ──────────────────
STREAM_SYMBOLS = [
    "^NSEI", "^NSEBANK", "^BSESN",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
    "INFY.NS", "ICICIBANK.NS", "BTC-USD", "GC=F",
]

TICK_INTERVAL = 2.0   # seconds between broadcast cycles
FETCH_BATCH   = 3      # fetch this many symbols per cycle (rest are simulated)


class StreamManager:
    """
    Maintains the set of active WebSocket subscribers and
    runs the background streaming loop.
    """

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._last_prices: Dict[str, float] = {}   # cache for simulation fallback
        self._running = False

    # ── Connection management ─────────────────────────────────────────────────

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        """Send JSON payload to all connected clients, dropping dead connections."""
        dead: Set[WebSocket] = set()
        message = json.dumps(payload)
        for ws in self._connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections.discard(ws)

    # ── Streaming loop ────────────────────────────────────────────────────────

    async def run_stream(self) -> None:
        """
        Background task: rotate through STREAM_SYMBOLS and broadcast ticks.
        Fetches FETCH_BATCH real quotes per cycle; simulates the rest.
        """
        # Import here to avoid circular imports at module load time
        from data_fetcher import data_fetcher

        self._running = True
        symbol_index = 0
        logger.info("Market stream started.")

        while self._running:
            if not self._connections:
                await asyncio.sleep(TICK_INTERVAL)
                continue

            # Pick the next batch of symbols to fetch
            batch = STREAM_SYMBOLS[symbol_index: symbol_index + FETCH_BATCH]
            symbol_index = (symbol_index + FETCH_BATCH) % len(STREAM_SYMBOLS)

            for symbol in batch:
                tick = await self._get_tick(data_fetcher, symbol)
                if tick:
                    await self.broadcast(tick)

            await asyncio.sleep(TICK_INTERVAL)

    async def _get_tick(self, data_fetcher, symbol: str) -> Optional[dict]:
        """Return a price tick for `symbol`, falling back to simulation."""
        try:
            stock = await data_fetcher.get_stock_info(symbol)
            if stock:
                self._last_prices[symbol] = stock.price
                return {
                    "symbol":    symbol,
                    "name":      stock.name,
                    "price":     stock.price,
                    "change":    round(stock.change, 2),
                    "change_pct": round(stock.change_percent, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "simulated": False,
                }
        except Exception as exc:
            logger.debug("yfinance error for %s: %s — using simulation", symbol, exc)

        # ── Simulation fallback ───────────────────────────────────────────────
        last = self._last_prices.get(symbol)
        if last is None:
            return None

        noise     = random.uniform(-0.0015, 0.0015)
        new_price = round(last * (1 + noise), 2)
        self._last_prices[symbol] = new_price
        change    = round(new_price - last, 2)
        return {
            "symbol":    symbol,
            "name":      symbol,
            "price":     new_price,
            "change":    change,
            "change_pct": round((change / last) * 100, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

    def stop(self) -> None:
        self._running = False


# ── Module-level singleton ───────────────────────────────────────────────────
stream_manager = StreamManager()
