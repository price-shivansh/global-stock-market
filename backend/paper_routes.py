"""
paper_routes.py — Backward-compatible shim.

All logic has been moved to routers/paper_trading.py.
This file re-exports the router so that any existing code importing
`from paper_routes import router` continues to work unchanged.
"""
from routers.paper_trading import router  # noqa: F401 — re-export

__all__ = ["router"]
