"""
core/config.py — Re-exports the application settings object.

Prefer importing from here inside routers/services so the dependency on
the top-level config.py is explicit and easily swappable.
"""
from config import settings  # noqa: F401 — re-export

__all__ = ["settings"]
