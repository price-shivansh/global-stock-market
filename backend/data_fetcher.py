"""
Data Fetcher Module - Fetches stock data from Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

from models import StockData, Signal, SignalType, TechnicalIndicators
from technical_analysis import technical_analyzer
from sentiment_analysis import sentiment_analyzer
from config import settings

class DataFetcher:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.data_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        self.cache_duration = timedelta(seconds=settings.DATA_REFRESH_INTERVAL)
        
        self.symbol_names = {
            # Indian Indices
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "NIFTY BANK",
            "^BSESN": "SENSEX",
            # Indian Sector Indices
            "^CNXIT": "NIFTY IT",
            "^CNXPHARMA": "NIFTY Pharma",
            "^CNXAUTO": "NIFTY Auto",
            "^CNXFMCG": "NIFTY FMCG",
            "^CNXMETAL": "NIFTY Metal",
            "^CNXREALTY": "NIFTY Realty",
            "^CNXINFRA": "NIFTY Infra",
            "^CNXENERGY": "NIFTY Energy",
            # Global Indices
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones",
            "^IXIC": "NASDAQ",
            "^N225": "Nikkei 225",
            "^HSI": "Hang Seng",
            "^GDAXI": "DAX",
            "^FTSE": "FTSE 100",
            "^FCHI": "CAC 40",
            # Commodities
            "GC=F": "Gold",
            "SI=F": "Silver",
            "CL=F": "Crude Oil WTI",
            "BZ=F": "Brent Crude",
            "NG=F": "Natural Gas",
            "HG=F": "Copper",
            # Crypto
            "BTC-USD": "Bitcoin",
            "ETH-USD": "Ethereum",
            "BNB-USD": "BNB",
            "SOL-USD": "Solana",
            # Forex
            "USDINR=X": "USD/INR",
            "EURINR=X": "EUR/INR",
            "GBPINR=X": "GBP/INR",
            "JPYINR=X": "JPY/INR",
            # Indian Stocks
            "RELIANCE.NS": "Reliance Industries",
            "TCS.NS": "TCS",
            "HDFCBANK.NS": "HDFC Bank",
            "INFY.NS": "Infosys",
            "ICICIBANK.NS": "ICICI Bank",
            "HINDUNILVR.NS": "Hindustan Unilever",
            "SBIN.NS": "State Bank of India",
            "BHARTIARTL.NS": "Bharti Airtel",
            "ITC.NS": "ITC",
            "KOTAKBANK.NS": "Kotak Mahindra Bank",
            "LT.NS": "Larsen & Toubro",
            "AXISBANK.NS": "Axis Bank",
            "ASIANPAINT.NS": "Asian Paints",
            "MARUTI.NS": "Maruti Suzuki",
            "TITAN.NS": "Titan Company",
            "BAJFINANCE.NS": "Bajaj Finance",
            "WIPRO.NS": "Wipro",
            "ULTRACEMCO.NS": "UltraTech Cement",
            "NESTLEIND.NS": "Nestle India",
            "TATAPOWER.NS": "Tata Power"
        }
    
    def _fetch_stock_data_sync(self, symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Synchronously fetch stock data"""
        import traceback
        try:
            print(f"[yfinance] Fetching {symbol} (period={period}, interval={interval})")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df is None or df.empty:
                print(f"[yfinance] Warning: DataFrame is empty or None for {symbol}")
                return None
            return df
        except Exception as e:
            print(f"[yfinance] Error fetching {symbol}: {e}")
            traceback.print_exc()
            return None
    
    async def fetch_stock_data(self, symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch stock data asynchronously"""
        cache_key = f"{symbol}_{period}_{interval}"
        if cache_key in self.data_cache:
            df, timestamp = self.data_cache[cache_key]
            if datetime.now() - timestamp < self.cache_duration:
                return df
        
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(self.executor, self._fetch_stock_data_sync, symbol, period, interval)
        
        if df is not None:
            self.data_cache[cache_key] = (df, datetime.now())
        
        return df
    
    async def get_stock_info(self, symbol: str) -> Optional[StockData]:
        """Get current stock info with technical indicators"""
        df = await self.fetch_stock_data(symbol)
        
        if df is None or df.empty:
            return None
        
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
            
            price = float(latest['Close'])
            prev_close = float(prev['Close'])
            change = price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close else 0
            
            indicators = technical_analyzer.calculate_all_indicators(df)
            
            return StockData(
                symbol=symbol,
                name=self.symbol_names.get(symbol, symbol),
                price=round(price, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                volume=int(latest['Volume']),
                high=round(float(latest['High']), 2),
                low=round(float(latest['Low']), 2),
                open=round(float(latest['Open']), 2),
                prev_close=round(prev_close, 2),
                timestamp=datetime.now(),
                indicators=indicators
            )
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            return None
    
    async def get_multiple_stocks(self, symbols: List[str]) -> List[StockData]:
        """Fetch multiple stocks concurrently"""
        tasks = [self.get_stock_info(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stocks = []
        for result in results:
            if isinstance(result, StockData):
                stocks.append(result)
        
        return stocks
    
    async def get_index_data(self) -> Dict[str, Optional[StockData]]:
        """Get data for major indices"""
        indices = {
            "nifty": settings.NIFTY_SYMBOL,
            "banknifty": settings.BANKNIFTY_SYMBOL,
            "sensex": settings.SENSEX_SYMBOL
        }
        
        result = {}
        for key, symbol in indices.items():
            result[key] = await self.get_stock_info(symbol)
        
        return result
    
    async def get_top_gainers_losers(self, stocks: List[StockData]) -> Tuple[List[StockData], List[StockData]]:
        """Get top gainers and losers"""
        sorted_stocks = sorted(stocks, key=lambda x: x.change_percent, reverse=True)
        
        gainers = [s for s in sorted_stocks if s.change_percent > 0][:5]
        losers = [s for s in sorted_stocks if s.change_percent < 0][-5:][::-1]
        
        return gainers, losers
    
    async def get_most_active(self, stocks: List[StockData]) -> List[StockData]:
        """Get most active stocks by volume"""
        return sorted(stocks, key=lambda x: x.volume, reverse=True)[:5]
    
    async def generate_signal(self, stock: StockData, sentiment_score: float) -> Signal:
        """Generate combined signal for a stock"""
        if stock.indicators is None:
            technical_score = 0
            reasons = ["Insufficient data for technical analysis"]
        else:
            technical_score, reasons = technical_analyzer.generate_technical_signal(
                stock.indicators, stock.price
            )
        
        sentiment_normalized = sentiment_score * 100
        combined_score = (technical_score * 0.6) + (sentiment_normalized * 0.4)
        
        if sentiment_score > 0.2:
            reasons.append(f"Bullish news sentiment ({sentiment_score:.2f})")
        elif sentiment_score < -0.2:
            reasons.append(f"Bearish news sentiment ({sentiment_score:.2f})")
        else:
            reasons.append("Neutral news sentiment")
        
        signal_type = technical_analyzer.get_signal_type(combined_score)
        
        return Signal(
            symbol=stock.symbol,
            signal_type=signal_type,
            strength=abs(combined_score),
            reasons=reasons,
            technical_score=technical_score,
            sentiment_score=sentiment_normalized,
            timestamp=datetime.now()
        )
    
    async def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> Optional[List[Dict]]:
        """Get historical price data for charting"""
        df = await self.fetch_stock_data(symbol, period, interval)
        
        if df is None or df.empty:
            return None
        
        data = []
        for index, row in df.iterrows():
            data.append({
                "date": index.strftime("%Y-%m-%d"),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
        
        return data


data_fetcher = DataFetcher()
