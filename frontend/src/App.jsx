import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Activity, BarChart2,
  AlertTriangle, RefreshCw, Radio, Sun, Moon
} from 'lucide-react';
import { useMarketStream } from './hooks/useMarketStream';

/* ── Page components ── */
import TechnicalSummaryPage from './components/TechnicalSummaryPage';
import PaperTradingPanel    from './components/PaperTradingPanel';
import BacktestPanel        from './components/BacktestPanel';

/* ── Extracted UI components ── */
import IndexCard            from './components/market/IndexCard';
import IndexMiniChart       from './components/market/IndexMiniChart';
import StockChartModal      from './components/market/StockChartModal';
import StockTable           from './components/market/StockTable';
import MarketsPanel         from './components/market/MarketsPanel';
import SignalsPanel         from './components/signals/SignalsPanel';
import SentimentIndicator   from './components/sentiment/SentimentIndicator';
import SentimentBarChart    from './components/sentiment/SentimentBarChart';
import NewsFeed             from './components/news/NewsFeed';
import GlobalMarketSessions from './components/GlobalMarketSessions';

/* ── Welcome Splash ── */
import StockMarketLoader from './components/StockMarketLoader';

/* ── API base ── */
const getApiBase = () => {
  const url = import.meta.env.VITE_API_URL;
  if (!url) return '/api';
  const clean = url.endsWith('/') ? url.slice(0, -1) : url;
  return `${clean.startsWith('http') ? '' : 'https://'}${clean}/api`;
};
const API_BASE = getApiBase();

/* ══════════════════════════════════════════
   SECTION LABEL helper
══════════════════════════════════════════ */
const SectionLabel = ({ children }) => (
  <div style={{
    fontSize: '11px', fontWeight: 600, letterSpacing: '0.07em',
    textTransform: 'uppercase', color: 'var(--text-muted)',
    marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px',
  }}>
    <span style={{ display: 'inline-block', width: '3px', height: '12px', background: 'var(--accent)', borderRadius: '2px', flexShrink: 0 }} />
    {children}
  </div>
);

/* ══════════════════════════════════════════
   SHARED HEADER
══════════════════════════════════════════ */
const Header = ({ children }) => (
  <header style={{
    background: 'var(--bg-panel)',
    borderBottom: '1px solid var(--border-subtle)',
    position: 'sticky', top: 0, zIndex: 100,
    backdropFilter: 'blur(12px)',
  }}>
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 20px' }}>
      {children}
    </div>
  </header>
);

/* ══════════════════════════════════════════
   MAIN APP
══════════════════════════════════════════ */
function App() {
  const navigate = useNavigate();
  const [marketData,     setMarketData]     = useState(null);
  const [marketsData,    setMarketsData]    = useState(null);
  const [marketsLoading, setMarketsLoading] = useState(true);
  const [loading,        setLoading]        = useState(true);
  const [error,          setError]          = useState(null);
  const [lastUpdate,     setLastUpdate]     = useState(null);
  const [selectedStock,  setSelectedStock]  = useState(null);
  const [showSplash,     setShowSplash]     = useState(true);
  const [currentPage,    setCurrentPage]    = useState('dashboard');

  /* Live WebSocket stream */
  const [liveStreamOn, setLiveStreamOn] = useState(false);
  const { connected } = useMarketStream(liveStreamOn);

  /* Theme */
  const [theme, setTheme] = useState(() => localStorage.getItem('dashTheme') || 'dark');
  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('dashTheme', theme);
  }, [theme]);
  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  /* Data fetching */
  const fetchMarketData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/market-overview`);
      setMarketData(res.data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch market data');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchMarketsData = useCallback(async () => {
    try {
      setMarketsLoading(true);
      const res = await axios.get(`${API_BASE}/markets/all`);
      setMarketsData(res.data);
    } catch (err) {
      console.error('Markets fetch error:', err);
    } finally {
      setMarketsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarketData();
    fetchMarketsData();
    const i1 = setInterval(fetchMarketData,  60000);
    const i2 = setInterval(fetchMarketsData, 120000);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, [fetchMarketData, fetchMarketsData]);

  const handleStockClick = stock => setSelectedStock(stock);
  const handleCloseModal = ()    => setSelectedStock(null);

  /* ── NAV BUTTON helper ── */
  const NavBtn = ({ children, onClick, active }) => (
    <button onClick={onClick} style={{
      fontFamily: 'Inter, sans-serif', fontSize: '13px', fontWeight: 500,
      padding: '6px 14px', cursor: 'pointer', borderRadius: '6px',
      border: active ? '1px solid var(--accent-border)' : '1px solid transparent',
      background: active ? 'var(--accent-dim)' : 'transparent',
      color: active ? 'var(--accent)' : 'var(--text-secondary)',
      display: 'flex', alignItems: 'center', gap: '6px',
      transition: 'all 0.15s',
    }}
      onMouseEnter={e => { if (!active) { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'var(--bg-panel-alt)'; } }}
      onMouseLeave={e => { if (!active) { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.background = 'transparent'; } }}
    >{children}</button>
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>

      {/* ══ PAPER TRADING PAGE ══════════════════════════════════════════════ */}
      {currentPage === 'paper-trading' && (
        <>
          <Header>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', height: '56px' }}>
              <NavBtn onClick={() => setCurrentPage('dashboard')}>← Back</NavBtn>
              <div style={{ width: '1px', height: '24px', background: 'var(--border-subtle)' }} />
              <span style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: '16px', color: 'var(--text-primary)' }}>
                📋 Paper Trading Simulator
              </span>
              <span className="holo-text" style={{ fontSize: '11px' }}>Simulated trades · No real money</span>
            </div>
          </Header>
          <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '28px 20px' }}>
            <PaperTradingPanel />
          </main>
          <footer style={{ borderTop: '1px solid var(--border-subtle)', padding: '14px 20px', marginTop: '40px', textAlign: 'center' }}>
            <span className="holo-text" style={{ fontSize: '11px' }}>Simulation only · Not financial advice</span>
          </footer>
        </>
      )}

      {/* ══ DASHBOARD PAGE ══════════════════════════════════════════════════ */}
      {currentPage === 'dashboard' && <>

        {showSplash && <StockMarketLoader onDone={() => setShowSplash(false)} />}
        {selectedStock && <StockChartModal symbol={selectedStock.symbol} name={selectedStock.name} onClose={handleCloseModal} />}

        {/* ── Header ── */}
        <Header>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '56px' }}>
            {/* Brand */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '32px', height: '32px', background: 'var(--accent-dim)', border: '1px solid var(--accent-border)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <BarChart2 size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div>
                <h1 className="holo-title" style={{ fontSize: '14px', letterSpacing: '0.08em' }}>
                  Options <span style={{ color: 'var(--bear)' }}>Signal</span> Dashboard
                </h1>
                <p className="holo-text" style={{ fontSize: '10px', marginTop: '1px' }}>Real-time Technical &amp; Sentiment Analysis</p>
              </div>
            </div>

            {/* Nav + controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {/* Live dot */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '0 8px' }}>
                <span style={{
                  width: '6px', height: '6px', borderRadius: '50%', display: 'inline-block',
                  background: loading ? 'var(--warn)' : 'var(--bull)',
                  boxShadow: `0 0 6px ${loading ? 'var(--warn)' : 'var(--bull)'}`,
                }} />
                <span className="holo-text" style={{ fontSize: '11px' }}>{loading ? 'Syncing…' : 'Live'}</span>
              </div>
              {lastUpdate && <span className="holo-text" style={{ fontSize: '11px', paddingRight: '8px' }}>{lastUpdate.toLocaleTimeString('en-IN')}</span>}

              <NavBtn onClick={() => navigate('/technical-summary')}>⚡ Technical</NavBtn>
              <NavBtn onClick={() => setCurrentPage('paper-trading')}>📋 Paper Trade</NavBtn>

              {/* GO LIVE */}
              <button onClick={() => setLiveStreamOn(v => !v)} style={{
                fontFamily: 'Inter, sans-serif', fontSize: '12px', fontWeight: 500,
                padding: '6px 12px', cursor: 'pointer', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '5px',
                border: `1px solid ${liveStreamOn ? (connected ? 'var(--bear-border)' : 'var(--warn-border)') : 'var(--border-active)'}`,
                background: liveStreamOn ? (connected ? 'var(--bear-dim)' : 'var(--warn-dim)') : 'transparent',
                color:  liveStreamOn ? (connected ? 'var(--bear)' : 'var(--warn)') : 'var(--text-secondary)',
                transition: 'all 0.15s',
              }}>
                <Radio size={11} />
                {liveStreamOn ? (connected ? '● Live' : 'Connecting…') : 'Go Live'}
              </button>

              {/* Theme toggle */}
              <button onClick={toggleTheme} className="theme-toggle-btn" title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
                <div className="theme-toggle-icon">
                  {theme === 'dark' ? <Sun size={13} color="var(--accent)" /> : <Moon size={13} color="var(--text-primary)" />}
                </div>
                <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
              </button>

              {/* Refresh */}
              <button onClick={fetchMarketData} disabled={loading} className="holo-btn btn-accent" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
          </div>
        </Header>

        {/* ── Main Content ── */}
        <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 20px' }}>

          {error && (
            <div style={{ marginBottom: '20px', padding: '10px 14px', background: 'var(--bear-dim)', border: '1px solid var(--bear-border)', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={15} style={{ color: 'var(--bear)', flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: 'var(--bear)' }}>{error}</span>
            </div>
          )}

          {/* ── Index Cards ── */}
          <section style={{ marginBottom: '24px' }}>
            <SectionLabel>Market Indices</SectionLabel>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              <IndexCard data={marketData?.nifty}      name="NIFTY 50" />
              <IndexCard data={marketData?.banknifty}  name="NIFTY BANK" />
              <IndexCard data={marketData?.sensex}     name="SENSEX" />
            </div>
          </section>

          {/* ── Index Charts ── */}
          <section style={{ marginBottom: '28px' }}>
            <SectionLabel>Index Charts — 3 Month</SectionLabel>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              <IndexMiniChart symbol="^NSEI"   name="NIFTY 50" />
              <IndexMiniChart symbol="^NSEBANK" name="NIFTY BANK" />
              <IndexMiniChart symbol="^BSESN"  name="SENSEX" />
            </div>
          </section>

          {/* ── Global Market Sessions ── */}
          <section style={{ marginBottom: '28px' }}>
            <SectionLabel>Global Market Sessions (IST)</SectionLabel>
            <GlobalMarketSessions />
          </section>

          {/* ── World Markets ── */}
          <section style={{ marginBottom: '28px' }}>
            <SectionLabel>World Markets</SectionLabel>
            <MarketsPanel marketsData={marketsData} loading={marketsLoading} onStockClick={handleStockClick} />
          </section>

          {/* ── Main Grid — Gainers / Signals / Sentiment ── */}
          <section style={{ marginBottom: '28px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
              {/* Left col */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <StockTable stocks={marketData?.top_gainers}  title="Top Gainers"  icon={TrendingUp}   accentColor="var(--bull)" onStockClick={handleStockClick} />
                <StockTable stocks={marketData?.top_losers}   title="Top Losers"   icon={TrendingDown} accentColor="var(--bear)" onStockClick={handleStockClick} />
              </div>
              {/* Mid col */}
              <StockTable stocks={marketData?.most_active} title="Most Active" icon={Activity} accentColor="var(--warn)" onStockClick={handleStockClick} />
              {/* Right col */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <SentimentIndicator sentiment={marketData?.market_sentiment} />
                <SentimentBarChart  sentiment={marketData?.market_sentiment} />
                <SignalsPanel       signals={marketData?.signals}            onStockClick={handleStockClick} />
              </div>
            </div>
          </section>

          {/* ── Intel Feed ── */}
          <section style={{ marginBottom: '28px' }}>
            <SectionLabel>Intel Feed</SectionLabel>
            <NewsFeed news={marketData?.market_sentiment?.news_items} />
          </section>

          {/* ── Backtest ── */}
          <section>
            <SectionLabel>Strategy Backtester</SectionLabel>
            <BacktestPanel />
          </section>
        </main>

        {/* ── Footer ── */}
        <footer style={{ borderTop: '1px solid var(--border-subtle)', padding: '16px 20px', marginTop: '40px', textAlign: 'center' }}>
          <p className="holo-text" style={{ fontSize: '11px' }}>Data: Yahoo Finance · Delay: 15–20 min · Educational use only</p>
          <p className="holo-text" style={{ fontSize: '10px', marginTop: '4px', color: 'var(--bear)', opacity: 0.5 }}>Not financial advice</p>
        </footer>
      </>}
    </div>
  );
}

const AppWrapper = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/"                   element={<App />} />
      <Route path="/technical-summary"  element={<TechnicalSummaryPage />} />
    </Routes>
  </BrowserRouter>
);

export default AppWrapper;
