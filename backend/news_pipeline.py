import asyncio
import logging
import re
from typing import List, Dict
from datetime import datetime, timedelta
from news_sources import (
    fetch_google_news,
    fetch_yahoo_finance_news,
    fetch_oilprice_news,
    fetch_coindesk_news,
    fetch_investing_news,
    fetch_reuters_market_news,
    fetch_eia_energy_news
)

logger = logging.getLogger(__name__)

# ── Deduplication Logic ──────────────────────────────────────────────────────

def _normalize_title(title: str) -> str:
    """Normalize title for fuzzy deduplication."""
    t = title.lower()
    # Remove common site suffixes like " - Yahoo Finance", "| Reuters"
    t = re.sub(r'\s*[-|]\s*.*$', '', t)
    # Remove all non-alphanumeric except spaces
    t = re.sub(r'[^a-z0-9\s]', '', t)
    # Collapse multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def deduplicate_news_items(items: List[Dict]) -> List[Dict]:
    """
    Remove duplicated headlines based on normalized titles.
    If duplicates exist, keep the one with the highest source_weight.
    """
    unique_items: Dict[str, Dict] = {}
    
    for item in items:
        # Require essential fields
        if not item.get("title") or not item.get("url"):
            continue
            
        norm_title = _normalize_title(item["title"])
        if not norm_title:
            continue
            
        # 1. Exact / near-exact match deduplication
        if norm_title in unique_items:
            existing_weight = unique_items[norm_title].get("source_weight", 1.0)
            new_weight = item.get("source_weight", 1.0)
            
            if new_weight > existing_weight:
                unique_items[norm_title] = item
            elif new_weight == existing_weight:
                if item.get("published", datetime.min) > unique_items[norm_title].get("published", datetime.min):
                    unique_items[norm_title] = item
        else:
            # 2. Substring match deduplication against existing items
            is_dup = False
            for existing_title, existing_item in list(unique_items.items()):
                if len(norm_title) > 20 and len(existing_title) > 20:
                    if norm_title in existing_title or existing_title in norm_title:
                        is_dup = True
                        e_weight = existing_item.get("source_weight", 1.0)
                        n_weight = item.get("source_weight", 1.0)
                        
                        if n_weight > e_weight:
                            # Replace existing with new better source
                            del unique_items[existing_title]
                            unique_items[norm_title] = item
                        elif n_weight == e_weight and len(norm_title) > len(existing_title):
                            # Keep the longer, more descriptive title if weights tie
                            del unique_items[existing_title]
                            unique_items[norm_title] = item
                        break
            
            if not is_dup:
                unique_items[norm_title] = item
                
    return list(unique_items.values())


# ── Full Pipeline Fetch ──────────────────────────────────────────────────────

async def build_news_pipeline() -> List[Dict]:
    """
    Stage 1: Fire off multiple async source fetchers.
    Stage 2: Flatten all results into a single list.
    Stage 3: Deduplicate (keeping highest quality source).
    """
    logger.info("[Pipeline] Starting multi-source news fetch...")
    
    # Define tasks covering the 4 main categories
    tasks = [
        # Global Markets
        fetch_google_news("global market outlook fed rates", "Global Markets"),
        fetch_yahoo_finance_news("Global Markets"),
        fetch_reuters_market_news("Global Markets"),
        fetch_investing_news("Global Markets"),
        
        # Commodities (Crude, Nat Gas, Gold)
        fetch_google_news("crude oil price news today", "Commodities", asset_hint="CRUDE_OIL"),
        fetch_google_news("natural gas market", "Commodities", asset_hint="NATURAL_GAS"),
        fetch_google_news("gold silver commodity market", "Commodities", asset_hint="GC=F"),
        fetch_oilprice_news("Commodities", asset_hint="CRUDE_OIL"),
        fetch_eia_energy_news("Commodities", asset_hint="NATURAL_GAS"),
        fetch_reuters_market_news("Commodities", asset_hint="CRUDE_OIL"),
        
        # Crypto
        fetch_google_news("bitcoin cryptocurrency news", "Crypto", asset_hint="CRYPTO_MARKET"),
        fetch_coindesk_news("Crypto", asset_hint="CRYPTO_MARKET"),
        fetch_reuters_market_news("Crypto", asset_hint="CRYPTO_MARKET"),
        
        # Indian Markets
        fetch_google_news("indian stock market news nifty", "Indian Markets", asset_hint="INDIAN_EQUITIES"),
        fetch_google_news("NSE BSE trading", "Indian Markets", asset_hint="INDIAN_EQUITIES"),
    ]
    
    # Execute all concurrently. Fail gracefully if one crashes.
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    flattened: List[Dict] = []
    
    # Combine results
    for res in results:
        if isinstance(res, list):
            flattened.extend(res)
        elif isinstance(res, Exception):
            logger.error(f"[Pipeline] Fetch sub-task failed: {res}")
            
    # Deduplicate matching stories, preferring highest source weight
    deduped = deduplicate_news_items(flattened)
    
    # Sort by publish time descending
    deduped.sort(key=lambda x: x.get("published", datetime.min), reverse=True)
    
    logger.info(f"[Pipeline] Fetch complete. Raw: {len(flattened)}, Deduped: {len(deduped)}")
    return deduped
