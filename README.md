# 📈  Options Signal Dashboard

> A real-time, multi-asset trading dashboard with technical analysis, sentiment analysis, paper trading simulation, and Telegram news alerts — built with FastAPI + React (Vite).

---

## 🚀 Features

### 📊 Market Data & Analysis
- Real-time data for NIFTY, BANKNIFTY, SENSEX, Indian stocks, global indices, commodities, crypto, and forex via **Yahoo Finance**
- **Technical Analysis** — RSI, MACD, Bollinger Bands, EMA/SMA, ATR, ADX, Stochastic, OBV, VWAP
- **Trading Signals** — BUY / SELL / HOLD signals with confidence scoring
- **Technical Summary Page** — per-symbol multi-timeframe analysis (1m → 1D)
- **Backtesting Engine** — test strategies on historical data

### 🧠 Sentiment Analysis (Level 2)
- **Multi-Source News Pipeline** across 4 categories (🇮🇳 Indian Markets | 🌍 Global Markets | ₿ Crypto | 🛢 Commodities):
  - Ingests concurrently from **Reuters, EIA, Yahoo Finance, CoinDesk, Investing.com, OilPrice, and Google**
  - Smart fuzzy deduplication collapses identical stories across sources
- **Asset-specific sentiment scoring** — separate scores for CL=F, NG=F, GC=F, BTC-USD, NIFTY, etc.
- **Commodity market-impact logic** — geopolitical events (war, sanctions, OPEC) treated as *bullish* for oil/gas prices, not bearish
- **Weighted scoring** — source quality (Reuters/Bloomberg › CNBC › Yahoo) × recency (≤30min › older)
- **Negation handling** — detects "no supply disruption" to avoid false signals
- News history exported to per-category Excel files automatically

### 📃 Paper Trading Simulator
- Simulated capital management (default ₹1,00,000)
- Supports: NSE Stocks · Forex · Commodities (CL=F, NG=F, etc.) · Crypto
- **Auto Stop-Loss / Target hit detection** (polls every 3 seconds)
- Per-asset lot size and tick size awareness
- Open positions, trade history, realized + unrealized P&L, equity curve
- **Order History Ledger** — records all EXECUTED and REJECTED order attempts
- 🔥 **Crude Oil Mode** — one-click preset for CL=F, 5m chart

### 🔔 Telegram News Alerts & Market Assistant
- **Multi-user Subscriber System** — users can `/start` the bot to subscribe
- **Per-User Preference Filters** — toggle `/crude`, `/nifty`, `/crypto`, etc. to get only relevant alerts
- **On-Demand Market Terminal** — type `/market_overview` for an instant multi-asset snapshot
- **Asset Summaries & Latest Headlines** — `/summary_crude`, `/latest_high`, `/latest_crypto` fetch instantly from memory
- Background bot continuously notifies active subscribers of matching headlines
- Smart deduplication saves previously broadcasted headlines to `data/sent_news.json`
- **🚨 HIGH PRIORITY** flag for market-moving alerts with `/highpriority` isolation mode

### 🎨 Frontend
- Neon cyberpunk dark theme (Tailwind CSS + custom CSS)
- Pages: Market Overview · Technical Summary · Paper Trading · Backtest
- Live candlestick + area charts via Recharts
- Simulated order book, equity curve, trade history table
- Asset type badge (STOCK / COMMODITY / FOREX / CRYPTO) with live detection
- Quick preset symbol buttons + Crude Oil Mode button

---

## 🗂 Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app + all API routes
│   ├── config.py                # All settings (reads from .env)
│   ├── models.py                # Pydantic models
│   ├── data_fetcher.py          # Yahoo Finance wrapper
│   ├── technical_analysis.py   # Core indicator calculations
│   ├── indicator_engine.py     # Signal scoring + confidence
│   ├── strategy_engine.py      # Strategy definitions
│   ├── sentiment_analysis.py   # Level 2 sentiment engine
│   ├── news_history.py         # Excel news export
│   ├── paper_trade.py          # Paper trading engine
│   ├── paper_routes.py         # Paper trading API routes
│   ├── backtest_engine.py      # Backtesting logic
│   ├── market_stream.py        # WebSocket stream manager
│   ├── telegram_notifier.py    # Telegram Bot API sender
│   ├── news_alert_service.py   # News monitoring + alert loop
│   ├── .env                    # Environment variables (not committed)
│   ├── requirements.txt        # Python dependencies
│   └── data/
│       └── sent_news.json      # Deduplication store for Telegram
│
└── frontend/
    ├── src/
    │   ├── App.jsx              # Routing + layout
    │   ├── index.css            # Neon theme styles
    │   └── components/
    │       ├── PaperTradingPanel.jsx    # Full paper trading UI
    │       ├── TechnicalSummaryPage.jsx # Multi-timeframe technical view
    │       └── BacktestPanel.jsx        # Backtest runner UI
    ├── package.json
    └── vite.config.js
```

---

## ⚙️ Quick Start

### One-click start (Windows)
```bat
start-app.bat
```
Starts backend on `http://localhost:8000` and frontend on `http://localhost:3000`.

---

### Manual Start

**Backend:**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

---

## 🔑 Environment Variables (`.env`)

```env
# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_CHAT_ID=<your_chat_id>
TELEGRAM_ENABLED=true
TELEGRAM_NEWS_INTERVAL=180        # seconds between news checks
```

**How to get your Chat ID:**  
Send `/start` to your bot on Telegram, then open:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Copy the `"id"` value from the `"chat"` object.

---

## 📡 API Reference

### Market Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market-overview` | Full market snapshot with signals |
| GET | `/api/stock/{symbol}` | Single stock data |
| GET | `/api/indices` | Major Indian + global indices |
| GET | `/api/signals` | All current trading signals |
| GET | `/api/sentiment` | Market sentiment + per-asset breakdown |
| GET | `/api/news` | Latest news items |
| GET | `/api/historical/{symbol}` | OHLCV historical data |
| GET | `/api/technical-summary/{symbol}/{interval}` | Technical analysis for any symbol/timeframe |
| WS  | `/ws` | WebSocket real-time updates |

### Paper Trading
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/paper-trading/order` | Place a paper trade |
| GET | `/api/paper-trading/open-positions` | Active positions |
| GET | `/api/paper-trading/history` | Closed trades |
| GET | `/api/paper-trading/account` | Capital + P&L summary |
| POST | `/api/paper-trading/close/{id}` | Close a position manually |
| POST | `/api/paper-trading/update` | Trigger SL/target check |
| GET | `/api/paper-trading/chart/{symbol}/{interval}` | OHLCV chart data |
| GET | `/api/paper-trading/order-book/{symbol}` | Simulated order book |

### Telegram Bot Commands (Direct via Telegram)
| Command | Description |
|---------|-------------|
| `/start`, `/stop`, `/status` | Manage subscription and view active filters |
| `/global`, `/crude`, `/crypto` ... | Toggle alert categories on or off |
| `/market_overview` | Instant multi-asset sentiment snapshot |
| `/summary_crude` (etc.) | Full sentiment breakdown and latest headlines for asset |
| `/latest_high` | Top 5 most recent HIGH relevance alerts globally |

### Telegram APIs (Backend)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/test-telegram-message` | Send a connectivity test message |
| POST | `/api/test-telegram-news` | Send one Global Markets alert manually |

### News & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/news/export` | Download news history as Excel |

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Backend API framework |
| `uvicorn` | ASGI server |
| `yfinance` | Yahoo Finance market data |
| `pandas` / `numpy` | Data processing |
| `vaderSentiment` | NLP sentiment base |
| `aiohttp` | Async HTTP (news fetch + Telegram) |
| `beautifulsoup4` | RSS parsing |
| `pydantic-settings` | Config from .env |
| `openpyxl` | Excel news export |
| `react` + `vite` | Frontend framework |
| `recharts` | Charts |
| `axios` | Frontend HTTP client |
| `tailwindcss` | Styling |

---

## 📋 Supported Assets

| Class | Examples |
|-------|---------|
| NSE Stocks | RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS … |
| Indian Indices | ^NSEI (Nifty), ^NSEBANK (BankNifty), ^BSESN (Sensex) |
| Global Indices | ^GSPC, ^DJI, ^IXIC, ^N225, ^HSI, ^GDAXI, ^FTSE |
| Commodities | CL=F (WTI Oil), BZ=F (Brent), NG=F (Nat Gas), GC=F (Gold), SI=F (Silver) |
| Crypto | BTC-USD, ETH-USD, BNB-USD, SOL-USD |
| Forex | USDINR=X, EURINR=X, GBPINR=X |

---

## ⚠️ Disclaimer

Data sourced from Yahoo Finance (may be delayed 15–20 min). This dashboard is for **educational and paper trading purposes only** and does not constitute financial advice. Always conduct your own research before making investment decisions.
