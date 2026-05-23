"""
core/ — Shared application infrastructure (config, utilities).
"""
from .config import settings
from .utils import fetch_group

__all__ = ["settings", "fetch_group"]
