"""
core/utils.py — Shared utility helpers used across multiple routers.
"""
import asyncio
from schemas.market_schemas import StockData


async def fetch_group(symbols: list, data_fetcher) -> list:
    """Fetch a list of symbols concurrently; silently drops any that fail.

    Args:
        symbols:      Iterable of ticker strings (e.g. ["^GSPC", "^DJI"]).
        data_fetcher: The singleton ``DataFetcher`` instance.

    Returns:
        A list of ``StockData`` objects for every symbol that succeeded.
    """
    tasks = [data_fetcher.get_stock_info(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, StockData)]
