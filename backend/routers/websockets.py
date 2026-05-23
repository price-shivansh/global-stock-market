"""
routers/websockets.py — WebSocket endpoints.

Provides:
  /ws         — legacy market update stream (60-second polling)
  /ws/market  — real-time price tick stream via market_stream manager
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import settings
from data_fetcher import data_fetcher
from sentiment_analysis import sentiment_analyzer
from market_stream import stream_manager

router = APIRouter(tags=["websockets"])


# ── Simple connection manager for the legacy /ws endpoint ─────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# ── WebSocket routes ───────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Legacy market update stream — pushes index + sentiment every DATA_REFRESH_INTERVAL seconds."""
    await manager.connect(websocket)
    try:
        while True:
            try:
                indices   = await data_fetcher.get_index_data()
                sentiment = await sentiment_analyzer.get_market_sentiment()
                await websocket.send_json({
                    "type": "market_update",
                    "data": {
                        "nifty":     indices.get("nifty").dict()     if indices.get("nifty")     else None,
                        "banknifty": indices.get("banknifty").dict() if indices.get("banknifty") else None,
                        "sensex":    indices.get("sensex").dict()    if indices.get("sensex")    else None,
                        "sentiment": sentiment.dict(),
                    },
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"WebSocket update error: {e}")
            await asyncio.sleep(settings.DATA_REFRESH_INTERVAL)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/market")
async def ws_market(websocket: WebSocket):
    """Stream live price ticks to the client every ~2 seconds via stream_manager."""
    await stream_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # client can send pings; we ignore them
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception:
        stream_manager.disconnect(websocket)
