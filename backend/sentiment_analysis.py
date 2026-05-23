"""
Sentiment Analysis Module — Level 2
Provides per-asset market-impact sentiment with weighted scoring.
Supports: Indian stocks/indices, Commodities, Forex, Crypto.
"""
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from models import NewsItem, MarketSentiment, SentimentType
from config import settings
from news_history import save_news_to_excel
from services.news_archive import news_archive_service


# Assets for which we auto-compute sentiment in get_market_sentiment()
TRACKED_ASSETS = ["CL=F", "BZ=F", "NG=F", "GC=F", "USDINR=X", "BTC-USD", "^NSEI", "^NSEBANK"]

# Simple negation words used for negation-proximity checking
NEGATION_WORDS = ["no", "not", "unlikely", "avoids", "eases", "resolved",
                  "reduces", "did not", "fails to", "cease", "ends", "stopped"]


class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.news_cache: Dict[str, List[NewsItem]] = {}
        self.cache_timestamp: Optional[datetime] = None

        # ── Indian Market Keywords ──────────────────────────────────────────────
        self.indian_market_keywords = [
            'nifty', 'sensex', 'nse', 'bse', 'indian market', 'india stock',
            'reliance', 'tcs', 'hdfc', 'infosys', 'icici', 'sbi', 'bharti',
            'kotak', 'axis bank', 'maruti', 'bajaj', 'titan', 'wipro',
            'options', 'futures', 'derivative', 'fii', 'dii', 'sebi',
            'rbi', 'rupee', 'inr', 'indian economy',
        ]

        # ── Generic Financial Sentiment (stocks / crypto) ───────────────────────
        self.financial_positive = [
            'bullish', 'rally', 'surge', 'gain', 'profit', 'growth', 'upgrade',
            'outperform', 'buy', 'accumulate', 'breakout', 'all-time high',
            'record high', 'strong', 'positive', 'beat estimates', 'exceeded',
            'moon', 'adoption', 'halving', 'institutional', 'etf approved',
            'gold rally', 'oil rally',
        ]
        self.financial_negative = [
            'bearish', 'crash', 'plunge', 'loss', 'decline', 'downgrade',
            'underperform', 'sell', 'breakdown', 'correction', 'weak',
            'negative', 'miss estimates', 'fell short',
            'hack', 'scam', 'ban', 'regulatory crackdown', 'exchange collapse',
            'supply glut', 'demand slump', 'recession fears',
            # 'warning' and 'crisis' removed — context-dependent for commodities
        ]

        # ── Commodity Detection Keywords ────────────────────────────────────────
        # Strong / direct energy context anchors (needed for geopolitical triggers)
        self._energy_context = [
            'opec', 'pipeline', 'tanker', 'refinery', 'supply', 'export',
            'middle east', 'oil route', 'gas flow', 'crude', 'oilfield',
            'oil production', 'brent', 'wti', 'barrel', 'petroleum',
            'lng terminal', 'gas export', 'straits', 'oil field',
        ]

        self.crude_oil_keywords = [
            'crude oil', 'crude', 'oil', 'wti', 'brent', 'opec', 'opec+',
            'refinery', 'pipeline', 'barrel', 'oil market', 'petroleum',
            'oil price', 'oil supply', 'oil demand', 'middle east oil',
        ]
        self.natural_gas_keywords = [
            'natural gas', 'lng', 'henry hub', 'gas futures', 'gas storage',
            'gas inventory', 'natgas', ' ng ', 'gas price', 'gas market',
            'gas demand', 'gas supply',
        ]
        self.gold_keywords = [
            'gold', 'silver', 'bullion', 'precious metals', 'xau', 'xag',
        ]

        # ── Crude Oil Market-Impact Keywords ────────────────────────────────────
        # STRONG direct triggers — count always
        self._oil_strong_bullish = [
            'supply cut', 'opec cut', 'opec+ cut', 'production cut', 'output cut',
            'export disruption', 'pipeline outage', 'refinery outage', 'refinery fire',
            'inventory draw', 'stockpile draw', 'crude draw', 'surprise draw',
            'demand surge', 'hurricane', 'supply disruption',
            'red sea', 'strait of hormuz', 'houthi', 'iran sanctions', 'russia sanctions',
        ]
        self._oil_strong_bearish = [
            'supply increase', 'opec hike', 'production increase', 'output boost',
            'oversupply', 'inventory build', 'stockpile build', 'crude build',
            'demand slowdown', 'weak china demand', 'china demand falls',
            'recession fears', 'ceasefire', 'peace deal',
            'production recovery', 'output recovery', 'shale boom',
        ]
        # GEOPOLITICAL — only counted bullish when strong energy context present
        self._oil_geo_triggers = [
            'war', 'conflict', 'attack', 'sanctions', 'crisis', 'tension',
            'disruption', 'outage', 'missile', 'drone attack', 'tanker attack',
            'geopolitical risk', 'geopolitical tension', 'output drop', 'production outage',
            'shipping disruption', 'middle east tensions', 'war risk', 'iran tensions',
        ]

        # ── Natural Gas Market-Impact Keywords ──────────────────────────────────
        self.gas_bullish_keywords = [
            'cold wave', 'colder forecast', 'freeze', 'polar vortex',
            'heat wave', 'hot weather', 'demand surge', 'summer demand',
            'storage draw', 'inventory draw', 'supply draw', 'gas draw',
            'production outage', 'pipeline disruption', 'supply disruption',
            'lng demand', 'export demand', 'storm disruption', 'freeze-off',
            'hurricane', 'winter storm', 'cold snap',
        ]
        self.gas_bearish_keywords = [
            'storage build', 'inventory build', 'gas build',
            'mild weather', 'warmer forecast', 'warm winter',
            'oversupply', 'production increase', 'output increase',
            'weak demand', 'lng demand weak', 'demand falls',
            'storage surplus', 'record storage',
        ]

        # ── Gold Market-Impact Keywords ──────────────────────────────────────────
        self.gold_bullish_keywords = [
            'safe haven', 'central bank buying', 'geopolitical risk',
            'inflation hedge', 'dollar weakness', 'dollar falls', 'usd drops',
            'war', 'crisis', 'uncertainty', 'rate cut', 'fed dovish',
        ]
        self.gold_bearish_keywords = [
            'dollar strength', 'dollar rises', 'rising yields', 'yield surge',
            'hawkish fed', 'rate hike', 'risk-on', 'equity rally',
        ]

        # ── Symbol → keyword mapping for extract_related_symbols() ───────────────
        self._symbol_keyword_map: Dict[str, List[str]] = {
            "CL=F":      ['crude oil', 'wti', 'oil futures', 'oil price', 'oil market'],
            "BZ=F":      ['brent', 'brent crude'],
            "NG=F":      ['natural gas', 'lng', 'henry hub', 'natgas', 'gas storage'],
            "GC=F":      ['gold', 'bullion', 'precious metals', 'xau'],
            "USDINR=X":  ['rupee', 'inr', 'usd/inr', 'dollar rupee'],
            "EURUSD=X":  ['euro dollar', 'eur/usd', 'euro'],
            "BTC-USD":   ['bitcoin', 'btc'],
            "ETH-USD":   ['ethereum', 'eth'],
            "^NSEI":     ['nifty'],
            "^NSEBANK":  ['banknifty', 'bank nifty'],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # CORE SENTIMENT SCORERS
    # ══════════════════════════════════════════════════════════════════════════

    def analyze_text(self, text: str) -> float:
        """Generic VADER + financial keyword sentiment (stocks / crypto)."""
        scores = self.vader.polarity_scores(text)
        compound = scores['compound']
        t = text.lower()
        pos = sum(1 for w in self.financial_positive if w in t)
        neg = sum(1 for w in self.financial_negative if w in t)
        compound = max(-1.0, min(1.0, compound + (pos - neg) * 0.1))
        return compound

    # ── Commodity Detection ───────────────────────────────────────────────────

    def is_crude_oil_news(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.crude_oil_keywords)

    def is_natural_gas_news(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.natural_gas_keywords)

    def is_gold_news(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.gold_keywords)

    def is_commodity_news(self, text: str) -> bool:
        return self.is_crude_oil_news(text) or self.is_natural_gas_news(text) or self.is_gold_news(text)

    # ── Negation Helper ───────────────────────────────────────────────────────

    def has_negation_near(self, text: str, keyword: str) -> bool:
        """
        Return True if a negation word appears within ~6 words before 'keyword'
        in the text.  Lightweight rule-based — no NLP required.
        """
        t = text.lower()
        idx = t.find(keyword.lower())
        if idx == -1:
            return False
        # Pull the 50 characters before the keyword as the proximity window
        window = t[max(0, idx - 60): idx]
        return any(neg in window for neg in NEGATION_WORDS)

    # ── Commodity Market-Impact Analyzer ─────────────────────────────────────

    def analyze_commodity_market_impact(self, text: str) -> float:
        """
        Score commodity news by PRICE IMPACT, not emotional tone.
        Geopolitical triggers are only counted bullish for oil/gas when strong
        energy context keywords are also present (prevents false signals).
        """
        t = text.lower()
        bullish_count = 0
        bearish_count = 0

        if self.is_crude_oil_news(t):
            # Strong direct triggers
            for kw in self._oil_strong_bullish:
                if kw in t and not self.has_negation_near(t, kw):
                    bullish_count += 1
            for kw in self._oil_strong_bearish:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish_count += 1

            # Geopolitical triggers — only count if energy context anchor present
            has_energy_ctx = any(ctx in t for ctx in self._energy_context)
            if has_energy_ctx:
                for kw in self._oil_geo_triggers:
                    if kw in t and not self.has_negation_near(t, kw):
                        bullish_count += 1

        elif self.is_natural_gas_news(t):
            for kw in self.gas_bullish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bullish_count += 1
            for kw in self.gas_bearish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish_count += 1

        elif self.is_gold_news(t):
            for kw in self.gold_bullish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bullish_count += 1
            for kw in self.gold_bearish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish_count += 1

        else:
            return self.analyze_text(text)

        if bullish_count == 0 and bearish_count == 0:
            # No commodity-specific signal — muted VADER fallback
            return self.vader.polarity_scores(text)['compound'] * 0.3

        return max(-1.0, min(1.0, (bullish_count - bearish_count) * 0.25))

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 1 — ASSET CLASSIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def classify_primary_asset(
        self,
        text: str,
        category: str = "",
        related_symbols: list | None = None,
    ) -> str:
        """
        Return a normalised asset key string.
        Priority: related_symbols → title keywords → category fallback.
        """
        # ── Priority 1: tagged symbols ────────────────────────────────────────
        _sym_map = {
            "CL=F":     "CRUDE_OIL",
            "BZ=F":     "BRENT_CRUDE",
            "NG=F":     "NATURAL_GAS",
            "GC=F":     "GOLD",
            "SI=F":     "SILVER",
            "HG=F":     "COMMODITY_MARKET",
            "BTC-USD":  "BITCOIN",
            "ETH-USD":  "ETHEREUM",
            "BNB-USD":  "CRYPTO_MARKET",
            "SOL-USD":  "CRYPTO_MARKET",
            "^NSEI":    "NIFTY",
            "^NSEBANK": "BANKNIFTY",
            "^BSESN":   "INDIAN_EQUITIES",
            "^GSPC":    "US_EQUITIES",
            "^DJI":     "US_EQUITIES",
            "^IXIC":    "US_EQUITIES",
            "^N225":    "GLOBAL_MACRO",
            "^HSI":     "GLOBAL_MACRO",
            "^GDAXI":   "GLOBAL_MACRO",
            "^FTSE":    "GLOBAL_MACRO",
            "USDINR=X": "FOREX",
        }
        for sym in (related_symbols or []):
            if sym in _sym_map:
                return _sym_map[sym]

        # ── Priority 2: title keyword scan ───────────────────────────────────
        t = text.lower()

        # Crude Oil (very aggressive — many oil headline styles)
        _crude_kw = [
            'crude oil', 'oil prices', 'oil futures', 'oil surges', 'oil jumps',
            'oil rises', 'oil climbs', 'oil gains', 'oil falls', 'oil drops',
            'oil market', 'oil supply', 'oil demand', 'oil output', 'oil exports',
            'wti', 'brent crude', 'barrel', 'barrels', 'opec', 'opec+',
            'refinery', 'petroleum', 'kharg', 'iran oil', 'saudi oil',
            'strait of hormuz', 'red sea shipping', 'tanker attack',
        ]
        if any(kw in t for kw in _crude_kw):
            # Disambiguate: brent → BRENT_CRUDE
            if 'brent' in t and 'crude' not in t and 'oil' not in t:
                return "BRENT_CRUDE"
            return "CRUDE_OIL"

        _natgas_kw = [
            'natural gas', 'natgas', 'henry hub', 'gas futures', 'gas storage',
            'gas inventory', 'gas prices', 'gas market', 'freeze-off',
            'pipeline gas', 'lng', 'gas demand', 'gas supply', 'gas draw',
            'gas build', 'cold snap', 'polar vortex',
        ]
        if any(kw in t for kw in _natgas_kw):
            return "NATURAL_GAS"

        _gold_kw = ['gold price', 'gold market', 'gold futures', 'gold surges',
                    'gold falls', 'bullion', 'xau', 'precious metals', 'precious metal']
        if any(kw in t for kw in _gold_kw):
            return "GOLD"

        if 'silver' in t or 'xag' in t:
            return "SILVER"

        _btc_kw = ['bitcoin', ' btc ', 'btc-', 'spot bitcoin', 'btc etf',
                   'bitcoin etf', 'satoshi', 'crypto currency bitcoin']
        if any(kw in t for kw in _btc_kw):
            return "BITCOIN"

        _eth_kw = ['ethereum', ' eth ', 'ether ', 'eth etf', 'ethereum etf']
        if any(kw in t for kw in _eth_kw):
            return "ETHEREUM"

        _crypto_kw = ['crypto', 'cryptocurrency', 'altcoin', 'defi', 'nft',
                      'blockchain', 'binance', 'coinbase', 'exchange hack']
        if any(kw in t for kw in _crypto_kw):
            return "CRYPTO_MARKET"

        _banknifty_kw = ['banknifty', 'bank nifty', 'banking index', 'nifty bank']
        if any(kw in t for kw in _banknifty_kw):
            return "BANKNIFTY"

        _nifty_kw = ['nifty', 'sensex', 'nse stocks', 'bse stocks',
                     'sebi', 'dalal street', 'indian index']
        if any(kw in t for kw in _nifty_kw):
            return "NIFTY"

        _indian_kw = ['indian market', 'india stock', 'rbi', 'inr', 'rupee',
                      'reliance', 'tcs', 'hdfc', 'infosys']
        if any(kw in t for kw in _indian_kw):
            return "INDIAN_EQUITIES"

        _us_kw = ['dow jones', 'dow ', 's&p 500', 'nasdaq', 'wall street',
                  'us stocks', 'us equities', 'index futures', 'market futures',
                  'futures up', 'futures down', 'fomc', 'federal reserve',
                  'cpi report', 'pce', 'payrolls', 'us market']
        if any(kw in t for kw in _us_kw):
            return "US_EQUITIES"

        _global_kw = ['ftse', 'dax', 'cac 40', 'nikkei', 'hang seng',
                      'global stocks', 'european stock', 'global market',
                      'world market', 'asian market', 'global economy']
        if any(kw in t for kw in _global_kw):
            return "GLOBAL_MACRO"

        # ── Priority 3: category fallback ─────────────────────────────────────
        return {
            "Global Markets":  "GLOBAL_MACRO",
            "Indian Markets":  "INDIAN_EQUITIES",
            "Crypto":          "CRYPTO_MARKET",
            "Commodities":     "COMMODITY_MARKET",
        }.get(category, "GLOBAL_MACRO")

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 2 — MARKET-IMPACT SENTIMENT (per asset)
    # ══════════════════════════════════════════════════════════════════════════

    def analyze_market_impact(self, text: str, asset_key: str) -> float:
        """
        Return price-impact score −1.0 … +1.0 for the classified asset.
        Rule-based for energy/gold; VADER-blended for equities/crypto.
        """
        t = text.lower()

        if asset_key in ("CRUDE_OIL", "BRENT_CRUDE"):
            bullish, bearish = 0, 0
            _oil_bullish = [
                'supply cut', 'opec cut', 'opec+ cut', 'production cut', 'output cut',
                'sanctions', 'iran sanctions', 'russia sanctions',
                'middle east tension', 'mideast tension', 'war risk', 'conflict',
                'attack', 'missile', 'drone strike', 'tanker attack',
                'kharg', 'strait of hormuz', 'red sea disruption', 'red sea',
                'pipeline outage', 'refinery outage', 'export disruption',
                'shipping disruption', 'inventory draw', 'crude draw', 'stockpile draw',
                'surprise draw', 'hurricane', 'production outage', 'output drop',
                'geopolitical risk', 'supply disruption', 'tensions escalate',
                'escalation', 'infrastructure attack', 'oil surge', 'oil jumps',
                'oil rises', 'oil climbs', 'oil gains', 'oil up',
            ]
            _oil_bearish = [
                'production increase', 'opec hike', 'output boost', 'oversupply',
                'inventory build', 'crude build', 'stockpile build', 'demand slowdown',
                'recession fears', 'weak china demand', 'china demand falls',
                'exports rise', 'ceasefire', 'peace deal', 'supply resumes',
                'refinery restart', 'production recovery', 'oil falls', 'oil drops',
                'oil plunges', 'oil slides', 'oil eases', 'oil retreats',
            ]
            has_energy_ctx = any(c in t for c in self._energy_context)
            for kw in _oil_bullish:
                if kw in t and not self.has_negation_near(t, kw):
                    # geopolitical risk words need energy context to be bull
                    if kw in ('conflict', 'attack', 'missile', 'drone strike', 'war risk'):
                        if has_energy_ctx:
                            bullish += 1
                    else:
                        bullish += 1
            for kw in _oil_bearish:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish += 1
            if bullish == 0 and bearish == 0:
                return self.vader.polarity_scores(text)['compound'] * 0.25
            return max(-1.0, min(1.0, (bullish - bearish) * 0.25))

        if asset_key == "NATURAL_GAS":
            bullish, bearish = 0, 0
            for kw in self.gas_bullish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bullish += 1
            for kw in self.gas_bearish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish += 1
            if bullish == 0 and bearish == 0:
                return self.vader.polarity_scores(text)['compound'] * 0.25
            return max(-1.0, min(1.0, (bullish - bearish) * 0.25))

        if asset_key in ("GOLD", "SILVER"):
            bullish, bearish = 0, 0
            for kw in self.gold_bullish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bullish += 1
            for kw in self.gold_bearish_keywords:
                if kw in t and not self.has_negation_near(t, kw):
                    bearish += 1
            if bullish == 0 and bearish == 0:
                return self.vader.polarity_scores(text)['compound'] * 0.25
            return max(-1.0, min(1.0, (bullish - bearish) * 0.25))

        if asset_key == "BITCOIN":
            _btc_bullish = [
                'etf approval', 'etf inflows', 'spot btc etf', 'institutional buying',
                'adoption', 'treasury buy', 'reserve asset', 'halving',
                'accumulation', 'whale buys', 'exchange reserves fall',
                'bullish breakout', 'bitcoin surges', 'btc surges', 'bitcoin rallies',
            ]
            _btc_bearish = [
                'etf outflows', 'sec crackdown', 'ban', 'regulatory crackdown',
                'exchange hack', 'exchange collapse', 'whale selloff',
                'forced selling', 'bearish breakdown', 'bitcoin falls', 'btc falls',
                'bitcoin plunges', 'btc plunges',
            ]
            bullish, bearish = 0, 0
            for kw in _btc_bullish:
                if kw in t:
                    bullish += 1
            for kw in _btc_bearish:
                if kw in t:
                    bearish += 1
            if bullish == 0 and bearish == 0:
                return self.vader.polarity_scores(text)['compound'] * 0.4
            return max(-1.0, min(1.0, (bullish - bearish) * 0.3))

        if asset_key in ("US_EQUITIES", "GLOBAL_MACRO"):
            _bull = ['futures rise', 'futures up', 'dow up', 's&p 500 gains',
                     'nasdaq rallies', 'fed dovish', 'soft inflation', 'rate cut hopes',
                     'beat estimates', 'strong earnings', 'risk-on', 'market rallies',
                     'stocks gain', 'shares rise']
            _bear = ['futures fall', 'futures down', 'selloff', 'recession fears',
                     'hawkish fed', 'rising yields', 'weak earnings', 'miss estimates',
                     'inflation shock', 'market tumbles', 'stocks fall', 'shares drop']
            bullish, bearish = 0, 0
            for kw in _bull:
                if kw in t:
                    bullish += 1
            for kw in _bear:
                if kw in t:
                    bearish += 1
            vader_score = self.vader.polarity_scores(text)['compound']
            if bullish == 0 and bearish == 0:
                return vader_score
            return max(-1.0, min(1.0, vader_score * 0.5 + (bullish - bearish) * 0.2))

        # Default: VADER
        return self.vader.polarity_scores(text)['compound']

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 3 — TRADING RELEVANCE
    # ══════════════════════════════════════════════════════════════════════════

    # Patterns that indicate LOW relevance personal/crime stories
    _LOW_RELEVANCE_PATTERNS: list = [
        'filmed husband', 'filmed wife', 'stole bitcoin', 'bitcoin theft',
        'bitcoin heist', 'password stolen', 'account hacked', 'wallet stolen',
        'bitcoin scam', 'crypto scam', 'ponzi', 'fraud victim',
        'personal loss', 'couple bitcoin', 'man arrested', 'woman arrested',
        'charged with', 'pleaded guilty', 'sentenced to', 'prison for bitcoin',
        'drug dealer', 'money laundering arrest', 'illicit', 'smuggling',
        'celebrity', 'divorce bitcoin', 'nft art', 'nft sale',
    ]

    def calculate_trading_relevance(self, text: str, asset_key: str) -> str:
        """
        Return 'HIGH', 'MEDIUM', or 'LOW' trading relevance for the headline.
        Uses asset-specific rule sets. Crime/personal stories are always LOW.
        """
        t = text.lower()

        # ── Universal LOW override: personal/crime stories ────────────────────
        if any(p in t for p in self._LOW_RELEVANCE_PATTERNS):
            return "LOW"

        # ── Asset-specific HIGH rules ─────────────────────────────────────────
        if asset_key in ("CRUDE_OIL", "BRENT_CRUDE"):
            _high_kw = [
                'opec', 'opec+', 'sanctions', 'iran', 'strait of hormuz',
                'red sea', 'kharg', 'tanker', 'pipeline outage', 'refinery outage',
                'export disruption', 'inventory draw', 'stockpile draw',
                'missile', 'drone attack', 'war', 'production cut',
                'production increase', 'crude inventories', 'eia crude',
                'supply disruption', 'oil surges', 'oil plunges',
                'oil up', 'oil down', 'oil price', 'oil falls',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key == "NATURAL_GAS":
            _high_kw = [
                'storage report', 'eia gas', 'freeze-off', 'cold wave',
                'colder forecast', 'lng exports', 'pipeline disruption',
                'gas storage', 'inventory draw', 'inventory build',
                'gas draw', 'gas build', 'polar vortex', 'gas surges',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key in ("GOLD", "SILVER"):
            _high_kw = [
                'fed', 'yields', 'dollar', 'central bank buying', 'war',
                'safe haven', 'inflation', 'rate cut', 'rate hike', 'fomc',
                'gold surges', 'gold plunges', 'gold up', 'gold down',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key == "BITCOIN":
            _high_kw = [
                'etf', 'sec', 'inflows', 'outflows', 'exchange hack',
                'exchange collapse', 'binance', 'coinbase regulation',
                'halving', 'institutional', 'regulation', 'reserve',
                'treasury buy', 'bitcoin surges', 'bitcoin plunges',
                'btc surges', 'btc falls', 'bitcoin banned', 'spot etf',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key == "ETHEREUM":
            _high_kw = ['etf', 'sec', 'regulation', 'ethereum upgrade',
                        'eth surges', 'eth falls', 'staking', 'layer 2']
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key in ("NIFTY", "BANKNIFTY", "INDIAN_EQUITIES"):
            _high_kw = [
                'rbi', 'sebi', 'budget', 'gdp', 'cpi', 'inflation',
                'rate cut', 'rate hike', 'nifty falls', 'nifty surges',
                'sensex falls', 'sensex surges', 'fii', 'dii',
                'circuit breaker', 'market crash', 'market rally',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        if asset_key in ("US_EQUITIES", "GLOBAL_MACRO"):
            _high_kw = [
                'fed', 'cpi', 'pce', 'payrolls', 'fomc', 'rate cuts',
                'rate hikes', 'futures', 'dow', 's&p 500', 'nasdaq',
                'earnings', 'recession fears', 'gdp', 'unemployment',
                'inflation data', 'market selloff', 'market rally',
            ]
            if any(kw in t for kw in _high_kw):
                return "HIGH"
            return "MEDIUM"

        # Generic fallback
        _macro_kw = ['gdp', 'inflation', 'recession', 'central bank',
                     'rate decision', 'market crash', 'market rally']
        if any(kw in t for kw in _macro_kw):
            return "MEDIUM"
        return "LOW"


    def get_source_weight(self, source: str) -> float:
        """Quality multiplier by news source. Delegates to news_sources module."""
        from news_sources import get_source_weight as fetcher_get_source_weight
        return fetcher_get_source_weight(source)

    def get_recency_weight(self, published: datetime) -> float:
        """Recency multiplier — newer news counts more."""
        try:
            now = datetime.now()
            # Normalize to naive if tz-aware
            if published.tzinfo is not None:
                now = datetime.now(timezone.utc)
            age = now - published
            minutes = age.total_seconds() / 60
            if minutes <= 30:
                return 1.5
            if minutes <= 120:
                return 1.3
            if minutes <= 360:
                return 1.15
            if minutes <= 1440:
                return 1.0
            return 0.85
        except Exception:
            return 1.0

    def get_sentiment_type(self, score: float) -> SentimentType:
        """Convert numeric score to SentimentType enum."""
        if score >= settings.SENTIMENT_THRESHOLD_BULLISH:
            return SentimentType.BULLISH
        elif score <= settings.SENTIMENT_THRESHOLD_BEARISH:
            return SentimentType.BEARISH
        return SentimentType.NEUTRAL

    def get_weighted_sentiment(self, news_items: List[NewsItem]) -> float:
        """
        Compute weighted average sentiment using source quality and recency.
        Falls back to simple average if weights are all zero.
        """
        if not news_items:
            return 0.0
        weighted_sum = 0.0
        weight_total = 0.0
        for n in news_items:
            w = self.get_source_weight(n.source) * self.get_recency_weight(n.published)
            weighted_sum += n.sentiment_score * w
            weight_total += w
        return weighted_sum / weight_total if weight_total else 0.0

    def is_news_relevant_to_symbol(self, symbol: str, news_item: NewsItem) -> bool:
        """
        Check if a NewsItem is relevant to a specific symbol via:
        1. related_symbols tag (fast path)
        2. keyword match in title
        3. category match for index symbols
        """
        sym_up = symbol.upper()

        # Fast path: tagged during extraction
        if sym_up in [s.upper() for s in news_item.related_symbols]:
            return True

        title_lower = news_item.title.lower()

        # Keyword fallback
        kws = self._symbol_keyword_map.get(symbol, [])
        if any(kw in title_lower for kw in kws):
            return True

        # Category-based fallback for broad indices
        if symbol in ("^NSEI", "^NSEBANK") and news_item.category == "Indian Markets":
            return True
        if symbol in ("BTC-USD", "ETH-USD") and news_item.category == "Crypto":
            return True
        if symbol in ("CL=F", "BZ=F", "NG=F", "GC=F") and news_item.category == "Commodities":
            return True

        return False

    def get_asset_sentiment(self, symbol: str, news_items: List[NewsItem]) -> Dict[str, Any]:
        """
        Return a full sentiment summary for a specific asset symbol.
        Uses weighted scoring and the is_news_relevant_to_symbol relevance filter.
        """
        relevant = [n for n in news_items if self.is_news_relevant_to_symbol(symbol, n)]

        if not relevant:
            return {
                "symbol": symbol,
                "sentiment_score": 0.0,
                "sentiment_type": SentimentType.NEUTRAL.value,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "relevant_news_count": 0,
            }

        score = self.get_weighted_sentiment(relevant)
        stype = self.get_sentiment_type(score)
        return {
            "symbol": symbol,
            "sentiment_score": round(score, 3),
            "sentiment_type": stype.value,
            "bullish_count": sum(1 for n in relevant if n.sentiment == SentimentType.BULLISH),
            "bearish_count": sum(1 for n in relevant if n.sentiment == SentimentType.BEARISH),
            "neutral_count": sum(1 for n in relevant if n.sentiment == SentimentType.NEUTRAL),
            "relevant_news_count": len(relevant),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # SYMBOL EXTRACTION (LEVEL 2 — commodities, forex, crypto, indices)
    # ══════════════════════════════════════════════════════════════════════════

    def extract_related_symbols(self, text: str) -> List[str]:
        """
        Extract all relevant symbols from headline text.
        Supports Indian stocks, commodity futures, forex pairs, crypto, indices.
        """
        symbols: List[str] = []
        t = text.lower()
        t_up = text.upper()

        # Indian blue-chip stocks (regex)
        for pattern in [
            r'\b(RELIANCE|TCS|INFY|HDFCBANK|ICICIBANK|SBIN|BHARTIARTL|ITC|KOTAKBANK)\b',
            r'\b(LT|AXISBANK|ASIANPAINT|MARUTI|TITAN|BAJFINANCE|WIPRO|TATAMOTORS)\b',
        ]:
            symbols.extend(re.findall(pattern, t_up))

        # Commodities
        if any(kw in t for kw in ['crude oil', 'wti', 'oil futures', 'oil price', 'oil market', 'cl=f']):
            symbols.append('CL=F')
        if any(kw in t for kw in ['brent crude', 'brent', 'bz=f']):
            symbols.append('BZ=F')
        if any(kw in t for kw in ['natural gas', 'lng', 'henry hub', 'natgas', 'gas storage', 'ng=f']):
            symbols.append('NG=F')
        if any(kw in t for kw in ['gold', 'bullion', 'precious metals', 'xau', 'gc=f']):
            symbols.append('GC=F')
        if any(kw in t for kw in ['silver', 'xag']):
            symbols.append('SI=F')

        # Forex
        if any(kw in t for kw in ['rupee', 'inr', 'usd/inr', 'dollar rupee']):
            symbols.append('USDINR=X')
        if any(kw in t for kw in ['euro dollar', 'eur/usd', 'eurusd']):
            symbols.append('EURUSD=X')
        if any(kw in t for kw in ['gbp', 'pound']):
            symbols.append('GBPUSD=X')

        # Crypto
        if any(kw in t for kw in ['bitcoin', ' btc']):
            symbols.append('BTC-USD')
        if any(kw in t for kw in ['ethereum', ' eth ']):
            symbols.append('ETH-USD')

        # Indices
        if 'banknifty' in t or 'bank nifty' in t:
            symbols.append('^NSEBANK')
        if 'nifty' in t:
            symbols.append('^NSEI')
        if 'sensex' in t:
            symbols.append('^BSESN')

        return list(set(symbols))

    # ══════════════════════════════════════════════════════════════════════════
    # NEWS FETCH
    # ══════════════════════════════════════════════════════════════════════════

    async def fetch_google_news(self, query: str = "indian stock market") -> List[Dict]:
        """Fetch news from Google News RSS."""
        news_items = []
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'xml')
                        for item in soup.find_all('item')[:20]:
                            title  = item.title.text  if item.title  else ""
                            link   = item.link.text   if item.link   else ""
                            pub    = item.pubDate.text if item.pubDate else ""
                            source = item.source.text if item.source else "Unknown"
                            try:
                                from email.utils import parsedate_to_datetime
                                published = parsedate_to_datetime(pub)
                                if published.tzinfo is None:
                                    published = published.replace(tzinfo=timezone.utc)
                            except Exception:
                                published = datetime.now(timezone.utc)
                            news_items.append({'title': title, 'url': link,
                                               'source': source, 'published': published})
        except Exception as e:
            print(f"Error fetching news: {e}")
        return news_items

    async def fetch_market_news(self) -> List[NewsItem]:
        """Fetch, analyze, and cache all market news using the multi-source pipeline."""
        if (self.cache_timestamp and
                datetime.now(timezone.utc) - self.cache_timestamp < timedelta(seconds=settings.NEWS_REFRESH_INTERVAL)):
            return list(self.news_cache.values())[0] if self.news_cache else []

        from news_pipeline import build_news_pipeline
        raw_items = await build_news_pipeline()

        all_news: List[NewsItem] = []

        for item in raw_items:
            analysis_text = f"{item['title']} {item['source']} {item['category']}"

            # Route: commodity-aware market impact vs generic VADER
            if self.is_commodity_news(analysis_text):
                sentiment_score = self.analyze_commodity_market_impact(analysis_text)
            else:
                sentiment_score = self.analyze_text(analysis_text)

            sentiment_type   = self.get_sentiment_type(sentiment_score)
            related_symbols  = self.extract_related_symbols(item['title'])
            
            # Incorporate the specific asset hint from the fetching pipeline
            if item.get('asset_hint') and item['asset_hint'] not in related_symbols:
                related_symbols.append(item['asset_hint'])

            # ── Timestamp resolution ──────────────────────────────────────────
            # published=None means the RSS feed had no parseable pubDate.
            # We use first_seen_at as the stable fallback — it was captured
            # ONCE at fetch time and never mutates, so the displayed time will
            # stop drifting after the first poll cycle that sees this article.
            published_dt = item.get('published')
            if published_dt is None:
                first_seen = item.get('first_seen_at')
                if first_seen is not None:
                    published_dt = first_seen
                else:
                    # Absolute last resort: should never happen if news_sources.py
                    # correctly sets first_seen_at. Log a warning so we can catch it.
                    import logging as _log
                    _log.getLogger(__name__).warning(
                        "[SentimentAnalyzer] Item has neither published nor first_seen_at: %s",
                        item.get('title', '')[:60]
                    )
                    published_dt = datetime.now(timezone.utc)

            all_news.append(NewsItem(
                title=item['title'],
                source=item['source'],
                url=item['url'],
                published=published_dt,
                sentiment=sentiment_type,
                sentiment_score=round(sentiment_score, 3),
                related_symbols=related_symbols,
                category=item['category'],
                source_weight=item.get('source_weight', 1.0)
            ))

        # Pipeline is already sorted and deduped
        self.news_cache['market'] = all_news[:60]
        self.cache_timestamp = datetime.now(timezone.utc)

        try:
            save_news_to_excel(all_news[:60])
        except Exception as e:
            print(f"[news_history] Could not save to Excel: {e}")

        try:
            news_archive_service.archive_news(all_news[:60])
        except Exception as e:
            print(f"[news_archive] Could not save to daily archive: {e}")

        return all_news[:60]

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    async def get_market_sentiment(self) -> MarketSentiment:
        """
        Overall market sentiment (backward-compatible) PLUS per-asset breakdown.
        The asset_sentiments dict is keyed by symbol (e.g. 'CL=F', '^NSEI').
        """
        news_items = await self.fetch_market_news()

        if not news_items:
            return MarketSentiment(
                overall_sentiment=SentimentType.NEUTRAL,
                sentiment_score=0.0,
                bullish_count=0, bearish_count=0, neutral_count=0,
                news_items=[], last_updated=datetime.now(timezone.utc),
                asset_sentiments={},
            )

        # Weighted global score
        avg_score = self.get_weighted_sentiment(news_items)

        bullish_count = sum(1 for n in news_items if n.sentiment == SentimentType.BULLISH)
        bearish_count = sum(1 for n in news_items if n.sentiment == SentimentType.BEARISH)
        neutral_count = sum(1 for n in news_items if n.sentiment == SentimentType.NEUTRAL)

        # Per-asset scores for all tracked assets
        asset_sentiments = {sym: self.get_asset_sentiment(sym, news_items)
                            for sym in TRACKED_ASSETS}

        return MarketSentiment(
            overall_sentiment=self.get_sentiment_type(avg_score),
            sentiment_score=round(avg_score, 3),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            news_items=news_items,
            last_updated=datetime.now(timezone.utc),
            asset_sentiments=asset_sentiments,
        )

    def get_symbol_sentiment(self, symbol: str, news_items: List[NewsItem]) -> float:
        """
        Backward-compatible float return.
        Internally uses weighted scoring and relevance filtering.
        For full breakdown use get_asset_sentiment() instead.
        """
        result = self.get_asset_sentiment(symbol, news_items)
        return result["sentiment_score"]


sentiment_analyzer = SentimentAnalyzer()
