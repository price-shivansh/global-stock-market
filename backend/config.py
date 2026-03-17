"""
Configuration settings for the Stock Signal Application
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Options Signal Dashboard"
    DEBUG: bool = True
    
    # Indian Market Indices
    NIFTY_SYMBOL: str = "^NSEI"
    BANKNIFTY_SYMBOL: str = "^NSEBANK"
    SENSEX_SYMBOL: str = "^BSESN"
    
    # Indian Sector Indices
    SECTOR_INDICES: List[str] = [
        "^CNXIT",    # NIFTY IT
        "^CNXPHARMA", # NIFTY Pharma
        "^CNXAUTO",  # NIFTY Auto
        "^CNXFMCG",  # NIFTY FMCG
        "^CNXMETAL", # NIFTY Metal
        "^CNXREALTY", # NIFTY Realty
        "^CNXINFRA",  # NIFTY Infra
        "^CNXENERGY", # NIFTY Energy
    ]

    # Global Indices
    GLOBAL_INDICES: List[str] = [
        "^GSPC",   # S&P 500
        "^DJI",    # Dow Jones
        "^IXIC",   # NASDAQ
        "^N225",   # Nikkei 225
        "^HSI",    # Hang Seng
        "^GDAXI",  # DAX
        "^FTSE",   # FTSE 100
        "^FCHI",   # CAC 40
    ]

    # Commodities
    COMMODITY_SYMBOLS: List[str] = [
        "GC=F",    # Gold Futures
        "SI=F",    # Silver Futures
        "CL=F",    # Crude Oil WTI
        "BZ=F",    # Brent Crude
        "NG=F",    # Natural Gas
        "HG=F",    # Copper
    ]

    # Crypto
    CRYPTO_SYMBOLS: List[str] = [
        "BTC-USD",  # Bitcoin
        "ETH-USD",  # Ethereum
        "BNB-USD",  # BNB
        "SOL-USD",  # Solana
    ]

    # Forex (USD based)
    FOREX_SYMBOLS: List[str] = [
        "USDINR=X",  # USD/INR
        "EURINR=X",  # EUR/INR
        "GBPINR=X",  # GBP/INR
        "JPYINR=X",  # JPY/INR
    ]
    
    # Popular Indian Stocks for Options
    STOCK_SYMBOLS: List[str] = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
        "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "TATAPOWER.NS"
    ]
    
    INDEX_SYMBOLS: List[str] = ["^NSEI", "^NSEBANK", "^BSESN"]
    
    # Technical Analysis Settings
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: int = 70
    RSI_OVERSOLD: int = 30
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    BB_PERIOD: int = 20
    BB_STD: int = 2
    SMA_SHORT: int = 20
    SMA_LONG: int = 50
    EMA_SHORT: int = 12
    EMA_LONG: int = 26
    
    # Sentiment Analysis Settings
    NEWS_REFRESH_INTERVAL: int = 300  # 5 minutes
    SENTIMENT_THRESHOLD_BULLISH: float = 0.2
    SENTIMENT_THRESHOLD_BEARISH: float = -0.2
    
    # WebSocket Settings
    WS_HEARTBEAT_INTERVAL: int = 30
    DATA_REFRESH_INTERVAL: int = 60  # 1 minute for Yahoo Finance

    # ── Telegram Bot Settings ─────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_NEWS_INTERVAL: int = 180   # seconds between news checks (default 3 min)

    class Config:
        env_file = str(__import__('pathlib').Path(__file__).parent / ".env")
        env_file_encoding = "utf-8"

settings = Settings()
