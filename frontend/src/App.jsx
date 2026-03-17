import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import TechnicalSummaryPage from './components/TechnicalSummaryPage';
import {
  TrendingUp, TrendingDown, Activity, BarChart2,
  Newspaper, AlertTriangle, RefreshCw, ChevronUp, ChevronDown,
  Zap, PieChart, X, BarChart, LineChart as LineIcon, Globe, Cpu, DollarSign, Bitcoin, ArrowLeftRight,
  Radio, FlaskConical
} from 'lucide-react';
import { useMarketStream } from './hooks/useMarketStream';
import PaperTradingPanel from './components/PaperTradingPanel';
import BacktestPanel from './components/BacktestPanel';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart as ReBarChart, Bar, Cell,
  ComposedChart, Line, Legend
} from 'recharts';
const getApiBase = () => {
  const url = import.meta.env.VITE_API_URL;
  if (!url) return '/api';
  const cleanUrl = url.endsWith('/') ? url.slice(0, -1) : url;
  const protocol = cleanUrl.startsWith('http') ? '' : 'https://';
  return `${protocol}${cleanUrl}/api`;
};

const API_BASE = getApiBase();

/* ── Currency prefix by symbol type ── */
function getCurrencyPrefix(sym) {
  if (!sym) return '₹';
  if (sym.includes('-USD') || sym.includes('=X')) return '$'; // crypto & forex
  if (sym.includes('=F')) return '$';                          // commodities futures
  if (sym.startsWith('^')) return '';                          // indices (no prefix)
  return '₹';                                                  // Indian stocks .NS
}

function fmtPrice(value, sym, opts = {}) {
  const prefix = getCurrencyPrefix(sym);
  const locale = prefix === '₹' ? 'en-IN' : 'en-US';
  return prefix + Number(value).toLocaleString(locale, { maximumFractionDigits: 2, ...opts });
}

/* ── Holographic corner decorator ── */
const HoloCorners = () => (
  <>
    <span className="holo-corner tl" />
    <span className="holo-corner tr" />
    <span className="holo-corner bl" />
    <span className="holo-corner br" />
  </>
);

/* ── Custom Tooltip for charts ── */
const HoloTooltip = ({ active, payload, label, symbol }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: 'rgba(2,12,27,0.97)',
      border: '1px solid rgba(0,255,136,0.3)',
      padding: '8px 12px',
      fontFamily: 'Share Tech Mono',
      fontSize: '0.7rem',
    }}>
      <p style={{ color: 'rgba(0,255,136,0.5)', marginBottom: '4px' }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || '#00ff88' }}>
          {p.name}: {fmtPrice(p.value, symbol)}
        </p>
      ))}
    </div>
  );
};

/* ── Signal Badge ── */
const SignalBadge = ({ signal }) => {
  const cls = {
    STRONG_BUY: 'badge-strong-buy',
    BUY: 'badge-buy',
    HOLD: 'badge-hold',
    SELL: 'badge-sell',
    STRONG_SELL: 'badge-strong-sell',
  };
  const labels = {
    STRONG_BUY: '▲▲ STRONG BUY',
    BUY: '▲ BUY',
    HOLD: '◆ HOLD',
    SELL: '▼ SELL',
    STRONG_SELL: '▼▼ STRONG SELL',
  };
  return <span className={cls[signal] || 'badge-hold'}>{labels[signal] || signal}</span>;
};

/* ── Index Card ── */
const IndexCard = ({ data, name }) => {
  if (!data) return (
    <div className="holo-panel p-4 min-h-[96px] relative">
      <HoloCorners />
      <div className="holo-skeleton h-3 w-24 mb-3 rounded" />
      <div className="holo-skeleton h-7 w-32 mb-2 rounded" />
      <div className="holo-skeleton h-3 w-20 rounded" />
    </div>
  );
  const isPositive = data.change >= 0;
  return (
    <div className={`holo-panel p-4 relative transition-all duration-300 ${isPositive ? 'positive-glow' : 'negative-glow'}`}>
      <HoloCorners />
      <div className="scan-sweep" />
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs tracking-widest mb-1" style={{ fontFamily: 'Orbitron', color: 'rgba(0,255,136,0.5)' }}>{name}</p>
          <p className="holo-value text-2xl" style={{ color: isPositive ? '#00ff88' : '#ff2244', textShadow: isPositive ? '0 0 12px rgba(0,255,136,0.6)' : '0 0 12px rgba(255,34,68,0.6)' }}>
            {data.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </p>
        </div>
        <div style={{
          padding: '6px', borderRadius: '2px',
          background: isPositive ? 'rgba(0,255,136,0.08)' : 'rgba(255,34,68,0.08)',
          border: `1px solid ${isPositive ? 'rgba(0,255,136,0.3)' : 'rgba(255,34,68,0.3)'}`,
        }}>
          {isPositive
            ? <ChevronUp size={18} style={{ color: '#00ff88', filter: 'drop-shadow(0 0 6px #00ff88)' }} />
            : <ChevronDown size={18} style={{ color: '#ff2244', filter: 'drop-shadow(0 0 6px #ff2244)' }} />
          }
        </div>
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs" style={{ fontFamily: 'Share Tech Mono', color: isPositive ? '#00ff88' : '#ff2244' }}>
        <span>{isPositive ? '+' : ''}{data.change?.toFixed(2)}</span>
        <span style={{ color: 'rgba(0,255,136,0.4)' }}>|</span>
        <span>{isPositive ? '+' : ''}{data.change_percent?.toFixed(2)}%</span>
      </div>
    </div>
  );
};

/* ── Index Mini Chart ── */
const IndexMiniChart = ({ symbol, name, color = '#00ff88' }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sym = symbol.startsWith('^') ? symbol : symbol;
    axios.get(`${API_BASE}/historical/${encodeURIComponent(sym)}?period=3mo`)
      .then(r => {
        // downsample to ~60 points
        const data = r.data?.data || [];
        const step = Math.max(1, Math.floor(data.length / 60));
        setChartData(data.filter((_, i) => i % step === 0));
      })
      .catch(() => setChartData([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  const min = chartData ? Math.min(...chartData.map(d => d.low)) * 0.998 : 0;
  const max = chartData ? Math.max(...chartData.map(d => d.high)) * 1.002 : 0;
  const isUp = chartData && chartData.length > 1
    ? chartData[chartData.length - 1].close >= chartData[0].close
    : true;
  const lineColor = isUp ? '#00ff88' : '#ff2244';

  return (
    <div className="holo-panel relative overflow-hidden" style={{ minHeight: '220px' }}>
      <HoloCorners />
      <div className="panel-header">
        <span style={{ color: lineColor, filter: `drop-shadow(0 0 4px ${lineColor})` }}><LineIcon size={14} /></span>
        {name} <span style={{ color: 'rgba(0,255,136,0.4)', fontSize: '0.55rem' }}>3M</span>
      </div>
      <div style={{ padding: '8px 4px 12px 0' }}>
        {loading ? (
          <div style={{ height: '140px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.4)' }}>LOADING DATA...</span>
          </div>
        ) : !chartData?.length ? (
          <div style={{ height: '140px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(255,34,68,0.5)' }}>NO DATA</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`grad-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,255,136,0.06)" />
              <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
              <YAxis domain={[min, max]} tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }} axisLine={false} tickLine={false} width={60}
                tickFormatter={v => { const p = getCurrencyPrefix(symbol); return p + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(0)); }} />
              <Tooltip content={<HoloTooltip symbol={symbol} />} />
              <Area type="monotone" dataKey="close" stroke={lineColor} strokeWidth={1.5}
                fill={`url(#grad-${symbol})`} dot={false} name="Close"
                style={{ filter: `drop-shadow(0 0 3px ${lineColor})` }} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

/* ── Stock Chart Modal ── */
const StockChartModal = ({ symbol, name, onClose }) => {
  const [chartData, setChartData] = useState(null);
  const [period, setPeriod] = useState('6mo');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback((p) => {
    setLoading(true);
    axios.get(`${API_BASE}/historical/${encodeURIComponent(symbol)}?period=${p}`)
      .then(r => setChartData(r.data?.data || []))
      .catch(() => setChartData([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => { fetchData(period); }, [fetchData, period]);

  const isUp = chartData && chartData.length > 1
    ? chartData[chartData.length - 1].close >= chartData[0].close
    : true;
  const lineColor = isUp ? '#00ff88' : '#ff2244';
  const min = chartData ? Math.min(...chartData.map(d => d.low)) * 0.997 : 0;
  const max = chartData ? Math.max(...chartData.map(d => d.high)) * 1.003 : 0;

  const periods = ['1mo', '3mo', '6mo', '1y'];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '16px',
    }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="holo-panel relative" style={{ width: '100%', maxWidth: '900px', padding: '0' }}>
        <HoloCorners />

        {/* Modal Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: '1px solid rgba(0,255,136,0.15)',
          padding: '14px 20px',
        }}>
          <div>
            <h2 style={{ fontFamily: 'Orbitron', fontSize: '0.9rem', color: '#00ff88', textShadow: '0 0 10px rgba(0,255,136,0.5)', letterSpacing: '0.15em' }}>
              {name || symbol}
            </h2>
            <p style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.4)', marginTop: '2px' }}>{symbol}</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Period selector */}
            <div className="flex gap-1">
              {periods.map(p => (
                <button key={p} onClick={() => setPeriod(p)} style={{
                  fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.1em',
                  padding: '4px 10px',
                  background: period === p ? 'rgba(0,255,136,0.15)' : 'transparent',
                  border: `1px solid ${period === p ? 'rgba(0,255,136,0.5)' : 'rgba(0,255,136,0.15)'}`,
                  color: period === p ? '#00ff88' : 'rgba(0,255,136,0.4)',
                  cursor: 'pointer',
                  textShadow: period === p ? '0 0 6px rgba(0,255,136,0.5)' : 'none',
                  transition: 'all 0.2s',
                  clip_path: 'polygon(4px 0%, 100% 0%, calc(100% - 4px) 100%, 0% 100%)',
                }}>
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
            <button onClick={onClose} style={{
              background: 'rgba(255,34,68,0.1)',
              border: '1px solid rgba(255,34,68,0.3)',
              color: '#ff2244', cursor: 'pointer', padding: '4px',
              display: 'flex', alignItems: 'center',
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,34,68,0.2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,34,68,0.1)'}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Chart content */}
        <div style={{ padding: '16px 8px 16px 0' }}>
          {loading ? (
            <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: 'rgba(0,255,136,0.5)' }}>
                ◆ LOADING CHART DATA...
              </span>
            </div>
          ) : !chartData?.length ? (
            <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: 'rgba(255,34,68,0.5)' }}>
                ⚠ NO DATA AVAILABLE
              </span>
            </div>
          ) : (
            <>
              {/* Summary stats */}
              <div className="grid grid-cols-4 gap-3 mb-4 px-4">
                {[
                  { label: 'OPEN', value: chartData[0]?.open },
                  { label: 'HIGH', value: Math.max(...chartData.map(d => d.high)) },
                  { label: 'LOW', value: Math.min(...chartData.map(d => d.low)) },
                  { label: 'LAST', value: chartData[chartData.length - 1]?.close },
                ].map(({ label, value }) => (
                  <div key={label} style={{
                    background: 'rgba(0,255,136,0.03)',
                    border: '1px solid rgba(0,255,136,0.12)',
                    padding: '8px 10px', textAlign: 'center',
                  }}>
                    <div style={{ fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.2em', color: 'rgba(0,255,136,0.4)', marginBottom: '4px' }}>{label}</div>
                    <div className="holo-value" style={{ fontSize: '0.85rem', color: lineColor }}>
                      {fmtPrice(value, symbol)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Main OHLC composed chart */}
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="modalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={lineColor} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,255,136,0.06)" />
                  <XAxis dataKey="date"
                    tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }}
                    axisLine={false} tickLine={false}
                    tickFormatter={d => d?.slice(5)}
                    interval={Math.floor(chartData.length / 6)}
                  />
                  <YAxis yAxisId="price" domain={[min, max]}
                    tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }}
                    axisLine={false} tickLine={false} width={65}
                    tickFormatter={v => { const p = getCurrencyPrefix(symbol); return p + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(2)); }}
                  />
                  <YAxis yAxisId="volume" orientation="right" hide />
                  <Tooltip content={<HoloTooltip symbol={symbol} />} />
                  <Bar yAxisId="volume" dataKey="volume" fill="rgba(0,255,136,0.06)"
                    stroke="rgba(0,255,136,0.1)" name="Volume" radius={[1, 1, 0, 0]} />
                  <Area yAxisId="price" type="monotone" dataKey="close"
                    stroke={lineColor} strokeWidth={2}
                    fill="url(#modalGrad)" dot={false} name="Close"
                    style={{ filter: `drop-shadow(0 0 4px ${lineColor})` }}
                  />
                  <Line yAxisId="price" type="monotone" dataKey="high"
                    stroke="rgba(0,255,136,0.2)" strokeWidth={1} dot={false} name="High" strokeDasharray="3 3" />
                  <Line yAxisId="price" type="monotone" dataKey="low"
                    stroke="rgba(255,34,68,0.2)" strokeWidth={1} dot={false} name="Low" strokeDasharray="3 3" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

/* ── Sentiment Bar Chart ── */
const SentimentBarChart = ({ sentiment }) => {
  if (!sentiment) return null;

  const data = [
    { name: 'BULLISH', value: sentiment.bullish_count, color: '#00ff88' },
    { name: 'NEUTRAL', value: sentiment.neutral_count, color: '#ffaa00' },
    { name: 'BEARISH', value: sentiment.bearish_count, color: '#ff2244' },
  ];

  return (
    <div className="holo-panel relative overflow-hidden">
      <HoloCorners />
      <div className="panel-header">
        <span className="icon-wrap"><BarChart size={14} /></span>
        SENTIMENT DISTRIBUTION
      </div>
      <div style={{ padding: '12px 4px 16px 0' }}>
        <ResponsiveContainer width="100%" height={140}>
          <ReBarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,255,136,0.06)" vertical={false} />
            <XAxis dataKey="name"
              tick={{ fill: 'rgba(0,255,136,0.5)', fontSize: 9, fontFamily: 'Orbitron', letterSpacing: '0.1em' }}
              axisLine={false} tickLine={false}
            />
            <YAxis tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }}
              axisLine={false} tickLine={false} width={25} />
            <Tooltip
              contentStyle={{ background: 'rgba(2,12,27,0.97)', border: '1px solid rgba(0,255,136,0.3)', fontFamily: 'Share Tech Mono', fontSize: '0.7rem' }}
              labelStyle={{ color: 'rgba(0,255,136,0.5)' }}
              itemStyle={{ color: '#00ff88' }}
            />
            <Bar dataKey="value" radius={[2, 2, 0, 0]} name="Articles">
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.color} fillOpacity={0.7}
                  style={{ filter: `drop-shadow(0 0 4px ${entry.color})` }} />
              ))}
            </Bar>
          </ReBarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

/* ── Sentiment Indicator ── */
const SentimentIndicator = ({ sentiment }) => {
  if (!sentiment) return null;
  const isBullish = sentiment.overall_sentiment === 'BULLISH';
  const isBearish = sentiment.overall_sentiment === 'BEARISH';
  const sentimentPercent = Math.min(100, Math.max(0, ((sentiment.sentiment_score + 1) / 2) * 100));
  const sentimentColor = isBullish ? '#00ff88' : isBearish ? '#ff2244' : '#ffaa00';

  return (
    <div className="holo-panel relative overflow-hidden">
      <HoloCorners />
      <div className="panel-header">
        <span className="icon-wrap"><PieChart size={14} /></span>
        MARKET SENTIMENT
      </div>
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <span style={{ fontFamily: 'Share Tech Mono', color: 'rgba(0,255,136,0.5)', fontSize: '0.75rem' }}>
            SCORE: {sentiment.sentiment_score?.toFixed(3)}
          </span>
          <span className="holo-value text-sm" style={{ color: sentimentColor, textShadow: `0 0 12px ${sentimentColor}` }}>
            ◆ {sentiment.overall_sentiment}
          </span>
        </div>
        <div className="sentiment-bar mb-1 rounded-none overflow-hidden" style={{ position: 'relative' }}>
          <div style={{
            position: 'absolute', left: `${sentimentPercent}%`, top: '-3px',
            width: '2px', height: '11px', background: '#fff',
            boxShadow: '0 0 6px #fff', transform: 'translateX(-50%)', transition: 'left 0.8s ease'
          }} />
        </div>
        <div className="flex justify-between text-xs mb-4" style={{ fontFamily: 'Share Tech Mono', color: 'rgba(255,255,255,0.3)' }}>
          <span style={{ color: 'rgba(255,34,68,0.7)' }}>BEAR</span>
          <span style={{ color: 'rgba(255,170,0,0.7)' }}>NEUTRAL</span>
          <span style={{ color: 'rgba(0,255,136,0.7)' }}>BULL</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            { label: 'BEARISH', value: sentiment.bearish_count, color: '#ff2244', bg: 'rgba(255,34,68,0.06)', border: 'rgba(255,34,68,0.25)' },
            { label: 'NEUTRAL', value: sentiment.neutral_count, color: '#ffaa00', bg: 'rgba(255,170,0,0.06)', border: 'rgba(255,170,0,0.25)' },
            { label: 'BULLISH', value: sentiment.bullish_count, color: '#00ff88', bg: 'rgba(0,255,136,0.06)', border: 'rgba(0,255,136,0.25)' },
          ].map(({ label, value, color, bg, border }) => (
            <div key={label} style={{ background: bg, border: `1px solid ${border}`, borderRadius: '2px', padding: '8px 4px' }}>
              <div className="holo-value text-lg" style={{ color, textShadow: `0 0 8px ${color}` }}>{value}</div>
              <div style={{ fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.15em', color: 'rgba(255,255,255,0.4)', marginTop: '2px' }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ── Stock Table (clickable rows for chart modal) ── */
const CATEGORY_COLORS = {
  '🇮🇳 India': '#00ff88',
  '🌍 Global': '#00eeff',
  '📊 Sector': '#88ffcc',
  '🏭 Commodity': '#ffaa00',
  '🔷 Crypto': '#cc88ff',
  '💱 Forex': '#ff8844',
};

function fmtVolume(vol, sym) {
  if (!vol || vol <= 0) return '—';
  if (sym?.endsWith('.NS')) return (vol / 100000).toFixed(1) + 'L';
  if (vol >= 1e9) return (vol / 1e9).toFixed(2) + 'B';
  if (vol >= 1e6) return (vol / 1e6).toFixed(2) + 'M';
  if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
  return vol.toString();
}

const StockTable = ({ stocks, title, icon: Icon, accentColor = '#00ff88', onStockClick }) => {
  if (!stocks || stocks.length === 0) return null;
  return (
    <div className="holo-panel relative overflow-hidden">
      <HoloCorners />
      <div className="panel-header">
        <span style={{ color: accentColor, filter: `drop-shadow(0 0 4px ${accentColor})` }}><Icon size={14} /></span>
        {title}
        <span style={{ marginLeft: '6px', fontFamily: 'Share Tech Mono', fontSize: '0.55rem', color: 'rgba(0,255,136,0.35)' }}>
          ({stocks.length})
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full holo-table">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-right">Price</th>
              <th className="px-4 py-2 text-right">Change</th>
              <th className="px-4 py-2 text-right">Vol</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock, idx) => {
              const up = stock.change >= 0;
              const c = up ? '#00ff88' : '#ff2244';
              const cat = stock.category;
              const catColor = cat ? (CATEGORY_COLORS[cat] || '#aaa') : '#aaa';
              return (
                <tr key={idx}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onStockClick && onStockClick(stock)}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.03)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  title="Click to view chart"
                >
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      {cat && (
                        <span style={{
                          fontFamily: 'Orbitron', fontSize: '0.42rem', letterSpacing: '0.08em',
                          padding: '1px 5px', whiteSpace: 'nowrap',
                          background: `${catColor}15`,
                          border: `1px solid ${catColor}40`,
                          color: catColor,
                        }}>{cat}</span>
                      )}
                    </div>
                    <div style={{ fontFamily: 'Rajdhani', fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>{stock.name}</div>
                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.4)' }}>
                      {stock.symbol} <span style={{ color: 'rgba(0,255,136,0.2)', fontSize: '0.5rem' }}>↗ CHART</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className="holo-value" style={{ fontSize: '0.88rem', color: c }}>
                      {fmtPrice(stock.price, stock.symbol)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.72rem', color: c }}>
                    <div>{up ? '+' : ''}{stock.change?.toFixed(2)}</div>
                    <div style={{ opacity: 0.75 }}>{up ? '+' : ''}{stock.change_percent?.toFixed(2)}%</div>
                  </td>
                  <td className="px-4 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.68rem', color: 'rgba(0,255,136,0.45)' }}>
                    {fmtVolume(stock.volume, stock.symbol)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};


/* ── Signals Panel ── */
const SignalsPanel = ({ signals, onStockClick }) => {
  if (!signals || signals.length === 0) return null;
  return (
    <div className="holo-panel relative overflow-hidden">
      <HoloCorners />
      <div className="panel-header">
        <span className="icon-wrap"><Zap size={14} /></span>
        SIGNAL MATRIX
      </div>
      <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
        {signals.map((signal, idx) => (
          <div key={idx}
            style={{ padding: '12px 16px', borderBottom: '1px solid rgba(0,255,136,0.06)', cursor: 'pointer', transition: 'background 0.2s' }}
            onClick={() => onStockClick && onStockClick({ symbol: signal.symbol, name: signal.symbol.replace('.NS', '') })}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.03)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <span style={{ fontFamily: 'Orbitron', fontWeight: 600, color: '#fff', fontSize: '0.8rem' }}>
                  {signal.symbol.replace('.NS', '')}
                </span>
                <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.4)', marginTop: '2px' }}>
                  STR: {signal.strength?.toFixed(1)}% <span style={{ color: 'rgba(0,255,136,0.25)' }}>↗ CHART</span>
                </div>
              </div>
              <SignalBadge signal={signal.signal_type} />
            </div>
            <div className="space-y-1">
              {signal.reasons?.slice(0, 2).map((reason, ridx) => (
                <div key={ridx} style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.45)', display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <span style={{ color: '#ff2244', fontSize: '0.5rem' }}>◆</span>
                  {reason}
                </div>
              ))}
            </div>
            <div className="flex gap-4 mt-2" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem' }}>
              <span>Tech: <span style={{ color: signal.technical_score >= 0 ? '#00ff88' : '#ff2244' }}>{signal.technical_score?.toFixed(0)}</span></span>
              <span>Sent: <span style={{ color: signal.sentiment_score >= 0 ? '#00ff88' : '#ff2244' }}>{signal.sentiment_score?.toFixed(0)}</span></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── News Feed ── */
const TOPIC_RULES = [
  { label: 'CRYPTO', color: '#cc88ff', keywords: ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 'defi', 'nft', 'solana', 'bnb', 'altcoin'] },
  { label: 'OIL & GAS', color: '#ff8844', keywords: ['crude', 'oil', 'brent', 'opec', 'natural gas', 'petroleum', 'refinery', 'energy'] },
  { label: 'GOLD', color: '#ffdd44', keywords: ['gold', 'silver', 'copper', 'precious metal', 'commodity'] },
  { label: 'GLOBAL', color: '#00eeff', keywords: ['fed', 'nasdaq', 's&p', 'dow jones', 'nikkei', 'hang seng', 'ftse', 'wall street', 'us stock', 'global market', 'rate hike'] },
  { label: 'INDIA', color: '#00ff88', keywords: ['nifty', 'sensex', 'nse', 'bse', 'sebi', 'rbi', 'rupee', 'indian market', 'india stock'] },
];

function detectTopic(title) {
  const t = title.toLowerCase();
  for (const rule of TOPIC_RULES) {
    if (rule.keywords.some(k => t.includes(k))) return rule;
  }
  return { label: 'MARKET', color: '#aaaaaa' };
}

const NewsHistoryControls = () => {
  const [selectedCat, setSelectedCat] = useState('Indian Markets');
  const categories = ['Indian Markets', 'Crypto', 'Commodities', 'Global Markets'];

  const handleExport = () => {
    window.open(`/api/news/export?category=${encodeURIComponent(selectedCat)}`, '_blank');
  };

  const handleReset = async () => {
    if (!window.confirm(`Reset history for ${selectedCat}?`)) return;
    try {
      await axios.delete(`/api/news/history?category=${encodeURIComponent(selectedCat)}`);
      alert(`History for ${selectedCat} has been reset.`);
    } catch (e) {
      alert('Error resetting history: ' + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <div style={{ padding: '8px 12px', display: 'flex', gap: '8px', alignItems: 'center', borderBottom: '1px solid rgba(0,255,136,0.08)', flexWrap: 'wrap' }}>
      <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.5)' }}>HISTORY LOGS:</span>
      <select value={selectedCat} onChange={e => setSelectedCat(e.target.value)} style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(0,255,136,0.2)', color: '#00ff88', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', padding: '2px 4px', outline: 'none' }}>
        {categories.map(c => <option key={c} value={c}>{c}</option>)}
      </select>
      <button onClick={handleExport} style={{ cursor: 'pointer', background: 'rgba(0,255,136,0.1)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', padding: '2px 8px', transition: 'all 0.2s' }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.2)'}
        onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,255,136,0.1)'}
      >DOWNLOAD DB</button>
      <button onClick={handleReset} style={{ cursor: 'pointer', background: 'rgba(255,34,68,0.1)', border: '1px solid rgba(255,34,68,0.4)', color: '#ff2244', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', padding: '2px 8px', transition: 'all 0.2s' }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,34,68,0.2)'}
        onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,34,68,0.1)'}
      >RESET DB</button>
    </div>
  );
};

const NewsFeed = ({ news }) => {
  const [filter, setFilter] = useState('ALL');
  if (!news || news.length === 0) return null;

  const badgeStyle = {
    BULLISH: { bg: 'rgba(0,255,136,0.1)', border: 'rgba(0,255,136,0.3)', color: '#00ff88' },
    BEARISH: { bg: 'rgba(255,34,68,0.1)', border: 'rgba(255,34,68,0.3)', color: '#ff2244' },
    NEUTRAL: { bg: 'rgba(255,170,0,0.08)', border: 'rgba(255,170,0,0.3)', color: '#ffaa00' },
  };

  const topicFilters = ['ALL', 'CRYPTO', 'OIL & GAS', 'GOLD', 'GLOBAL', 'INDIA'];

  const filteredNews = news.filter(item => {
    if (filter === 'ALL') return true;
    return detectTopic(item.title).label === filter;
  });

  return (
    <div className="holo-panel relative overflow-hidden">
      <HoloCorners />
      <div className="panel-header">
        <span className="icon-wrap"><Newspaper size={14} /></span>
        INTEL FEED <span style={{ color: 'rgba(0,255,136,0.4)', fontSize: '0.55rem', marginLeft: '6px' }}>({filteredNews.length})</span>
      </div>

      <NewsHistoryControls />

      {/* Topic filter pills */}
      <div style={{ display: 'flex', gap: '4px', padding: '8px 12px', borderBottom: '1px solid rgba(0,255,136,0.08)', overflowX: 'auto', flexWrap: 'nowrap' }}>
        {topicFilters.map(f => {
          const rule = TOPIC_RULES.find(r => r.label === f);
          const active = filter === f;
          const col = rule?.color || '#00ff88';
          return (
            <button key={f} onClick={() => setFilter(f)} style={{
              fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.1em',
              padding: '3px 8px', cursor: 'pointer', whiteSpace: 'nowrap',
              background: active ? `${col}18` : 'transparent',
              border: `1px solid ${active ? col : 'rgba(0,255,136,0.15)'}`,
              color: active ? col : 'rgba(0,255,136,0.35)',
              textShadow: active ? `0 0 6px ${col}` : 'none',
              transition: 'all 0.2s',
            }}>
              {f}
            </button>
          );
        })}
      </div>

      <div style={{ maxHeight: '550px', overflowY: 'auto' }}>
        {filteredNews.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(255,34,68,0.5)' }}>
            NO {filter} NEWS YET
          </div>
        ) : filteredNews.slice(0, 30).map((item, idx) => {
          const s = badgeStyle[item.sentiment] || badgeStyle.NEUTRAL;
          const topic = detectTopic(item.title);
          return (
            <a key={idx} href={item.url} target="_blank" rel="noopener noreferrer"
              style={{ display: 'block', padding: '10px 14px', borderBottom: '1px solid rgba(0,255,136,0.05)', textDecoration: 'none', transition: 'background 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.03)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              {/* Topic + Sentiment badges */}
              <div style={{ display: 'flex', gap: '4px', marginBottom: '5px', alignItems: 'center' }}>
                <span style={{ background: `${topic.color}15`, border: `1px solid ${topic.color}50`, color: topic.color, fontFamily: 'Orbitron', fontSize: '0.48rem', letterSpacing: '0.1em', padding: '1px 5px' }}>
                  {topic.label}
                </span>
                <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color, fontFamily: 'Orbitron', fontSize: '0.48rem', letterSpacing: '0.1em', padding: '1px 5px' }}>
                  {item.sentiment}
                </span>
              </div>
              <p className="line-clamp-2" style={{ fontFamily: 'Rajdhani', fontSize: '0.85rem', color: 'rgba(255,255,255,0.85)', lineHeight: '1.3' }}>{item.title}</p>
              <div className="flex justify-between mt-1" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.3)' }}>
                <span>{item.source}</span>
                <span>{new Date(item.published).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
};


/* ── Markets Panel ── */
const MARKET_TABS = [
  { key: 'global_indices', label: 'GLOBAL', icon: Globe, color: '#00eeff' },
  { key: 'sector_indices', label: 'SECTORS', icon: BarChart2, color: '#00ff88' },
  { key: 'commodities', label: 'COMMODITIES', icon: DollarSign, color: '#ffaa00' },
  { key: 'crypto', label: 'CRYPTO', icon: Cpu, color: '#cc88ff' },
  { key: 'forex', label: 'FOREX', icon: ArrowLeftRight, color: '#ff8844' },
];

const MarketsPanel = ({ marketsData, loading, onStockClick }) => {
  const [activeTab, setActiveTab] = useState('global_indices');
  const tab = MARKET_TABS.find(t => t.key === activeTab);
  const items = marketsData?.[activeTab] || [];

  const formatPrice = (price, sym) => {
    if (!price) return '—';
    if (sym?.includes('-USD') || sym?.includes('=X')) return price.toLocaleString('en-US', { maximumFractionDigits: 4 });
    if (sym?.includes('=F')) return price.toLocaleString('en-US', { maximumFractionDigits: 2 });
    return '₹' + price.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  };

  return (
    <div className="holo-panel relative overflow-hidden" style={{ marginBottom: '28px' }}>
      <HoloCorners />
      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(0,255,136,0.12)', overflowX: 'auto' }}>
        {MARKET_TABS.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
            fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: '0.15em',
            padding: '12px 18px', cursor: 'pointer', whiteSpace: 'nowrap',
            background: activeTab === t.key ? `rgba(${t.color === '#00eeff' ? '0,238,255' : t.color === '#ffaa00' ? '255,170,0' : t.color === '#cc88ff' ? '204,136,255' : t.color === '#ff8844' ? '255,136,68' : '0,255,136'},0.08)` : 'transparent',
            borderBottom: activeTab === t.key ? `2px solid ${t.color}` : '2px solid transparent',
            color: activeTab === t.key ? t.color : 'rgba(0,255,136,0.35)',
            textShadow: activeTab === t.key ? `0 0 8px ${t.color}` : 'none',
            transition: 'all 0.2s', border: 'none', display: 'flex', alignItems: 'center', gap: '6px',
          }}>
            <t.icon size={12} />{t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ padding: '32px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(0,255,136,0.4)' }}>◆ LOADING DATA...</div>
      ) : items.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(255,34,68,0.5)' }}>⚠ NO DATA AVAILABLE</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full holo-table">
            <thead><tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-right">Price</th>
              <th className="px-4 py-2 text-right">Change</th>
              <th className="px-4 py-2 text-right">Change %</th>
              <th className="px-4 py-2 text-right">Volume</th>
            </tr></thead>
            <tbody>
              {items.map((item, i) => {
                const up = item.change >= 0;
                const c = up ? '#00ff88' : '#ff2244';
                return (
                  <tr key={i} style={{ cursor: 'pointer' }}
                    onClick={() => onStockClick && onStockClick(item)}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.04)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td className="px-4 py-3">
                      <div style={{ fontFamily: 'Rajdhani', fontWeight: 600, color: '#fff' }}>{item.name}</div>
                      <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: tab.color, opacity: 0.5 }}>{item.symbol}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="holo-value" style={{ color: c }}>{formatPrice(item.price, item.symbol)}</span>
                    </td>
                    <td className="px-4 py-3 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: c }}>
                      {up ? '+' : ''}{item.change?.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: c }}>
                      {up ? '+' : ''}{item.change_percent?.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(0,255,136,0.45)' }}>
                      {item.volume > 0 ? (item.volume / 1e6).toFixed(2) + 'M' : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

/* ── Arc Reactor Welcome Splash ── */
const ArcReactorRing = ({ size, speed, reverse, color, segments = 0, thickness = 1, opacity = 0.6 }) => {
  const dots = Array.from({ length: segments });
  return (
    <div style={{
      position: 'absolute',
      width: size, height: size,
      borderRadius: '50%',
      border: `${thickness}px solid ${color}`,
      opacity,
      animation: `cornerSpin ${speed}s linear infinite ${reverse ? 'reverse' : ''}`,
      boxShadow: `0 0 8px ${color}40, inset 0 0 8px ${color}20`,
    }}>
      {dots.map((_, i) => (
        <div key={i} style={{
          position: 'absolute',
          width: '6px', height: '6px',
          borderRadius: '50%',
          background: color,
          boxShadow: `0 0 8px ${color}, 0 0 16px ${color}`,
          top: '50%', left: '50%',
          transform: `rotate(${i * (360 / segments)}deg) translateX(${parseInt(size) / 2}px) translateY(-50%)`,
        }} />
      ))}
    </div>
  );
};

const WelcomeSplash = ({ onDone }) => {
  const [visible, setVisible] = useState(true);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFading(true), 4200);
    const doneTimer = setTimeout(() => { setVisible(false); onDone?.(); }, 5000);
    return () => { clearTimeout(fadeTimer); clearTimeout(doneTimer); };
  }, [onDone]);

  if (!visible) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'radial-gradient(ellipse at center, rgba(0,12,30,0.99) 0%, rgba(0,4,12,1) 100%)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      opacity: fading ? 0 : 1,
      transition: 'opacity 0.8s ease',
      pointerEvents: fading ? 'none' : 'all',
      overflow: 'hidden',
    }}>

      {/* ── Scanline overlay ── */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.012) 2px, rgba(0,255,136,0.012) 4px)',
      }} />

      {/* ── Arc Reactor ── */}
      <div style={{ position: 'relative', width: '340px', height: '340px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>

        {/* Outer ambient glow */}
        <div style={{
          position: 'absolute', width: '420px', height: '420px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,255,136,0.06) 0%, transparent 65%)',
          animation: 'arcPulse 2s ease-in-out infinite',
        }} />

        {/* Ring 1 — outermost, slow, green segments */}
        <ArcReactorRing size="320px" speed={12} color="#00ff88" segments={8} thickness={1} opacity={0.5} />

        {/* Ring 2 — red dashed, reverse */}
        <ArcReactorRing size="280px" speed={8} reverse color="#ff2244" segments={0} thickness={1} opacity={0.4} />

        {/* Ring 3 — cyan fast */}
        <ArcReactorRing size="240px" speed={5} color="#00eeff" segments={6} thickness={1.5} opacity={0.55} />

        {/* Ring 4 — green medium reverse */}
        <ArcReactorRing size="200px" speed={9} reverse color="#00ff88" segments={0} thickness={2} opacity={0.35} />

        {/* Ring 5 — bright red fast with dots */}
        <ArcReactorRing size="158px" speed={3} color="#ff2244" segments={4} thickness={1.5} opacity={0.6} />

        {/* Ring 6 — innermost cyan slow reverse */}
        <ArcReactorRing size="120px" speed={15} reverse color="#00eeff" segments={0} thickness={1} opacity={0.45} />

        {/* ── Inner geometric hex/triangle pattern ── */}
        <div style={{
          position: 'absolute', width: '90px', height: '90px',
          borderRadius: '50%',
          border: '2px solid rgba(0,255,136,0.5)',
          boxShadow: '0 0 20px rgba(0,255,136,0.4), inset 0 0 20px rgba(0,255,136,0.2)',
          animation: 'cornerSpin 6s linear infinite',
        }}>
          {/* Triangle inside */}
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{
              width: 0, height: 0,
              borderLeft: '18px solid transparent',
              borderRight: '18px solid transparent',
              borderBottom: '32px solid rgba(0,255,136,0.6)',
              filter: 'drop-shadow(0 0 8px #00ff88)',
              animation: 'cornerSpin 4s linear infinite reverse',
            }} />
          </div>
        </div>

        {/* ── Center core pulsing orb ── */}
        <div style={{
          position: 'absolute', width: '50px', height: '50px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,255,255,0.95) 0%, rgba(0,255,136,0.8) 40%, rgba(0,200,255,0.4) 70%, transparent 100%)',
          boxShadow: '0 0 20px #fff, 0 0 40px #00ff88, 0 0 80px rgba(0,255,136,0.5)',
          animation: 'arcPulse 1.4s ease-in-out infinite',
        }} />
      </div>

      {/* ── Text content below reactor ── */}
      <div style={{ position: 'relative', textAlign: 'center', marginTop: '28px', padding: '0 24px', maxWidth: '560px' }}>

        <p style={{
          fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: '0.4em',
          color: 'rgba(0,255,136,0.5)', marginBottom: '14px',
          animation: 'arcBlink 1.5s step-end infinite',
        }}>◆ INITIALISING SYSTEM ◆</p>

        <h1 style={{
          fontFamily: 'Orbitron', fontWeight: 800,
          fontSize: 'clamp(1.1rem, 3.5vw, 1.7rem)',
          lineHeight: 1.25, letterSpacing: '0.05em',
          color: '#fff',
          textShadow: '0 0 20px rgba(0,255,136,0.4), 0 0 60px rgba(0,255,136,0.15)',
          marginBottom: '10px',
        }}>
          Welcome to{' '}
          <span style={{ color: '#00ff88', textShadow: '0 0 12px #00ff88, 0 0 30px rgba(0,255,136,0.5)' }}>
            Stock Market!
          </span>
        </h1>

        <p style={{
          fontFamily: 'Share Tech Mono',
          fontSize: 'clamp(0.8rem, 2.2vw, 1.05rem)',
          color: '#ff2244',
          textShadow: '0 0 10px rgba(255,34,68,0.6), 0 0 30px rgba(255,34,68,0.25)',
          letterSpacing: '0.035em',
          lineHeight: 1.5,
        }}>
          &ldquo;where you pay for every mistake.&rdquo;
        </p>

        {/* Progress bar */}
        <div style={{
          height: '2px', width: '220px', margin: '24px auto 0',
          background: 'rgba(0,255,136,0.08)',
          position: 'relative', overflow: 'hidden',
          border: '1px solid rgba(0,255,136,0.12)',
        }}>
          <div style={{
            position: 'absolute', inset: 0,
            background: 'linear-gradient(90deg, #ff2244, #ffaa00 50%, #00ff88)',
            animation: 'splashProgress 4.2s linear forwards',
            boxShadow: '0 0 10px #00ff88',
          }} />
        </div>
        <p style={{
          fontFamily: 'Share Tech Mono', fontSize: '0.5rem',
          color: 'rgba(0,255,136,0.28)', marginTop: '6px',
          letterSpacing: '0.22em', animation: 'arcBlink 1.2s step-end infinite',
        }}>
          LOADING MARKET DATA...
        </p>
      </div>
    </div>
  );
};


/* ── Arc Reactor Background Decor ── */
const ArcDecor = () => (
  <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1, overflow: 'hidden' }}>
    <div style={{ position: 'absolute', top: '-200px', right: '-200px', width: '500px', height: '500px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,34,68,0.04) 0%, transparent 70%)', border: '1px solid rgba(255,34,68,0.08)', animation: 'cornerSpin 30s linear infinite' }} />
    <div style={{ position: 'absolute', bottom: '-150px', left: '-150px', width: '400px', height: '400px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,255,136,0.05) 0%, transparent 70%)', border: '1px solid rgba(0,255,136,0.07)', animation: 'cornerSpin 25s linear infinite reverse' }} />
    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '800px', height: '800px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,255,136,0.015) 0%, transparent 60%)' }} />
  </div>
);

/* ══════════════════════════════════════════
   MAIN APP
═══════════════════════════════════════════ */
function App() {
  const navigate = useNavigate();
  const [marketData, setMarketData] = useState(null);
  const [marketsData, setMarketsData] = useState(null);
  const [marketsLoading, setMarketsLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [showSplash, setShowSplash] = useState(true);

  // ── Feature 1: Live WebSocket stream ──────────────────────────────────────
  const [liveStreamOn, setLiveStreamOn] = useState(false);
  const { liveData, connected } = useMarketStream(liveStreamOn);

  // ── Page routing ──────────────────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState('dashboard'); // 'dashboard' | 'paper-trading'

  // ── Theme (dark / light) ──────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => localStorage.getItem('dashTheme') || 'dark');
  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('dashTheme', theme);
  }, [theme]);
  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const fetchMarketData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/market-overview`);
      setMarketData(response.data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err.message || 'SYSTEM ERROR — FAILED TO FETCH MARKET DATA');
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
    const interval = setInterval(fetchMarketData, 60000);
    const marketsInterval = setInterval(fetchMarketsData, 120000);
    return () => { clearInterval(interval); clearInterval(marketsInterval); };
  }, [fetchMarketData, fetchMarketsData]);

  const handleStockClick = (stock) => setSelectedStock(stock);
  const handleCloseModal = () => setSelectedStock(null);

  return (
    <div style={{ minHeight: '100vh', background: '#020c1b', position: 'relative' }}>
      <ArcDecor />

      {/* ══ PAPER TRADING PAGE ══════════════════════════════════════════════ */}
      {currentPage === 'paper-trading' && (
        <div style={{ position: 'relative', zIndex: 2 }}>
          {/* Sticky header */}
          <header style={{ background: 'linear-gradient(180deg, rgba(0,8,20,0.98) 0%, rgba(2,12,27,0.95) 100%)', borderBottom: '1px solid rgba(0,255,136,0.15)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(20px)' }}>
            <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '14px 16px' }}>
              <div className="flex items-center gap-6">
                {/* Back arrow */}
                <button
                  onClick={() => setCurrentPage('dashboard')}
                  style={{
                    fontFamily: 'Orbitron', fontSize: '0.65rem', letterSpacing: '0.15em',
                    padding: '8px 16px', cursor: 'pointer',
                    border: '1px solid rgba(0,255,136,0.3)', background: 'transparent',
                    color: '#00ff88', display: 'flex', alignItems: 'center', gap: '8px',
                    transition: 'all 0.2s', flexShrink: 0
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.1)'; e.currentTarget.style.boxShadow = '0 0 10px rgba(0,255,136,0.2)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.boxShadow = 'none'; }}
                >
                  <span style={{ fontSize: '0.8rem' }}>←</span> BACK
                </button>

                {/* Separator */}
                <div style={{ width: '1px', height: '32px', background: 'rgba(0,255,136,0.15)' }} />

                {/* Title */}
                <div className="flex items-center gap-3">
                  <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, rgba(255,34,68,0.2), rgba(0,255,136,0.1))', border: '1px solid rgba(0,255,136,0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: '1rem' }}>📋</span>
                  </div>
                  <div>
                    <h1 style={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '1.1rem', letterSpacing: '0.15em', color: '#00ff88', textShadow: '0 0 10px rgba(0,255,136,0.5)', margin: 0, lineHeight: 1.2 }}>
                      PAPER <span style={{ color: '#ff2244', textShadow: '0 0 10px rgba(255,34,68,0.5)' }}>TRADING</span> SIMULATOR
                    </h1>
                    <p style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.4)', letterSpacing: '0.2em', margin: 0, marginTop: '2px' }}>
                      ◆ SIMULATED TRADES · NO REAL MONEY ◆
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="header-line" />
          </header>

          {/* Panel */}
          <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '28px 16px', position: 'relative', zIndex: 2 }}>
            <PaperTradingPanel />
          </main>

          <footer style={{ borderTop: '1px solid rgba(0,255,136,0.08)', padding: '14px', marginTop: '40px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.2)', letterSpacing: '0.1em' }}>
            SIMULATION ONLY · NOT FINANCIAL ADVICE
          </footer>
        </div>
      )}

      {/* ══ DASHBOARD PAGE ══════════════════════════════════════════════════ */}
      {currentPage === 'dashboard' && <>

        {/* Welcome Splash */}
        {showSplash && <WelcomeSplash onDone={() => setShowSplash(false)} />}

        {/* Stock Chart Modal */}
        {selectedStock && (
          <StockChartModal
            symbol={selectedStock.symbol}
            name={selectedStock.name}
            onClose={handleCloseModal}
          />
        )}

        {/* ── Header ── */}
        <header style={{ background: 'linear-gradient(180deg, rgba(0,8,20,0.98) 0%, rgba(2,12,27,0.95) 100%)', borderBottom: '1px solid rgba(0,255,136,0.15)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(20px)' }}>
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '14px 16px' }}>
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <div style={{ width: '44px', height: '44px', background: 'linear-gradient(135deg, rgba(255,34,68,0.2), rgba(0,255,136,0.1))', border: '1px solid rgba(0,255,136,0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 15px rgba(0,255,136,0.15)' }}>
                  <BarChart2 size={22} style={{ color: '#00ff88', filter: 'drop-shadow(0 0 6px #00ff88)' }} />
                </div>
                <div>
                  <h1 style={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '1rem', letterSpacing: '0.15em', color: '#00ff88', textShadow: '0 0 10px rgba(0,255,136,0.5)' }}>
                    OPTIONS <span style={{ color: '#ff2244', textShadow: '0 0 10px rgba(255,34,68,0.5)' }}>SIGNAL</span> DASHBOARD
                  </h1>
                  <p style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.4)', letterSpacing: '0.2em' }}>
                    ◆ REAL-TIME TECHNICAL &amp; SENTIMENT ANALYSIS ◆
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: loading ? '#ffaa00' : '#00ff88', boxShadow: `0 0 8px ${loading ? '#ffaa00' : '#00ff88'}`, display: 'inline-block' }} />
                  <span style={{ color: loading ? '#ffaa00' : 'rgba(0,255,136,0.6)' }}>{loading ? 'SYNCING...' : 'LIVE'}</span>
                </div>
                {lastUpdate && <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>{lastUpdate.toLocaleTimeString('en-IN')}</span>}
                {/* TECHNICAL SUMMARY button */}
                <button
                  onClick={() => navigate('/technical-summary')}
                  style={{
                    fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: '0.12em',
                    padding: '7px 14px', cursor: 'pointer',
                    border: '1px solid rgba(0,170,255,0.3)',
                    background: 'transparent',
                    color: 'rgba(0,170,255,0.6)',
                    display: 'flex', alignItems: 'center', gap: '6px', transition: 'all 0.25s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,170,255,0.08)'; e.currentTarget.style.color = '#00aaff'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(0,170,255,0.6)'; }}
                >
                  ⚡ TECHNICAL SUMMARY
                </button>
                {/* PAPER TRADE button */}
                <button
                  onClick={() => setCurrentPage('paper-trading')}
                  style={{
                    fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: '0.12em',
                    padding: '7px 14px', cursor: 'pointer',
                    border: '1px solid rgba(0,255,136,0.3)',
                    background: 'transparent',
                    color: 'rgba(0,255,136,0.6)',
                    display: 'flex', alignItems: 'center', gap: '6px', transition: 'all 0.25s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.08)'; e.currentTarget.style.color = '#00ff88'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(0,255,136,0.6)'; }}
                >
                  📋 PAPER TRADE
                </button>

                {/* GO LIVE button */}
                <button
                  onClick={() => setLiveStreamOn(v => !v)}
                  style={{
                    fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: '0.12em',
                    padding: '7px 14px', cursor: 'pointer',
                    border: `1px solid ${liveStreamOn ? (connected ? '#ff2244' : '#ffaa00') : 'rgba(0,255,136,0.3)'}`,
                    background: liveStreamOn ? (connected ? 'rgba(255,34,68,0.12)' : 'rgba(255,170,0,0.1)') : 'transparent',
                    color: liveStreamOn ? (connected ? '#ff2244' : '#ffaa00') : 'rgba(0,255,136,0.6)',
                    display: 'flex', alignItems: 'center', gap: '6px', transition: 'all 0.25s',
                  }}
                >
                  <Radio size={11} style={{ animation: liveStreamOn && connected ? 'arcPulse 1s ease-in-out infinite' : 'none' }} />
                  {liveStreamOn ? (connected ? '● LIVE' : 'CONNECTING…') : 'GO LIVE'}
                </button>

                {/* Theme Toggle */}
                <button onClick={toggleTheme} className="theme-toggle-btn" title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
                  {theme === 'dark' ? '☀' : '🌙'}
                  {theme === 'dark' ? 'LIGHT' : 'DARK'}
                </button>

                {/* REFRESH button */}
                <button onClick={fetchMarketData} disabled={loading} className="holo-btn flex items-center gap-2">
                  <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                  REFRESH
                </button>
              </div>
            </div>
          </div>
          <div className="header-line" />
        </header>

        {/* ── Main Content ── */}
        <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 16px', position: 'relative', zIndex: 2 }}>

          {error && (
            <div style={{ marginBottom: '24px', padding: '12px 16px', background: 'rgba(255,34,68,0.06)', border: '1px solid rgba(255,34,68,0.3)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={16} style={{ color: '#ff2244', flexShrink: 0 }} />
              <span style={{ fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: '#ff2244' }}>⚠ {error}</span>
            </div>
          )}

          {/* ── Index Cards ── */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.25em', color: 'rgba(0,255,136,0.35)', marginBottom: '10px' }}>◆ MARKET INDICES ◆</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <IndexCard data={marketData?.nifty} name="NIFTY 50" />
              <IndexCard data={marketData?.banknifty} name="NIFTY BANK" />
              <IndexCard data={marketData?.sensex} name="SENSEX" />
            </div>
          </div>

          {/* ── Index Charts ── */}
          <div style={{ marginBottom: '28px' }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.25em', color: 'rgba(0,255,136,0.35)', marginBottom: '10px' }}>◆ INDEX CHARTS — 3 MONTH VIEW ◆</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <IndexMiniChart symbol="^NSEI" name="NIFTY 50" />
              <IndexMiniChart symbol="^NSEBANK" name="NIFTY BANK" />
              <IndexMiniChart symbol="^BSESN" name="SENSEX" />
            </div>
          </div>

          {/* ── Markets Section ── */}
          <div style={{ marginBottom: '28px' }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.25em', color: 'rgba(0,255,136,0.35)', marginBottom: '10px' }}>◆ WORLD MARKETS ◆</div>
            <MarketsPanel marketsData={marketsData} loading={marketsLoading} onStockClick={handleStockClick} />
          </div>

          {/* ── Main Grid ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2/3 */}
            <div className="lg:col-span-2 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <StockTable stocks={marketData?.top_gainers} title="TOP GAINERS" icon={TrendingUp} accentColor="#00ff88" onStockClick={handleStockClick} />
                <StockTable stocks={marketData?.top_losers} title="TOP LOSERS" icon={TrendingDown} accentColor="#ff2244" onStockClick={handleStockClick} />
              </div>
              <StockTable stocks={marketData?.most_active} title="MOST ACTIVE" icon={Activity} accentColor="#ffaa00" onStockClick={handleStockClick} />
            </div>

            {/* Right 1/3 */}
            <div className="space-y-6">
              <SentimentIndicator sentiment={marketData?.market_sentiment} />
              <SentimentBarChart sentiment={marketData?.market_sentiment} />
              <SignalsPanel signals={marketData?.signals} onStockClick={handleStockClick} />
            </div>
          </div>

          {/* ── Intel Feed (full width) ── */}
          <div style={{ marginTop: '28px' }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.25em', color: 'rgba(0,255,136,0.35)', marginBottom: '10px' }}>◆ INTEL FEED ◆</div>
            <NewsFeed news={marketData?.market_sentiment?.news_items} />
          </div>

          {/* ── Backtest Section ── */}
          <div style={{ marginTop: '36px' }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.25em', color: 'rgba(0,255,136,0.35)', marginBottom: '14px' }}>◆ BACKTEST ◆</div>
            <BacktestPanel />
          </div>
        </main>

        {/* ── Footer ── */}
        <footer style={{ borderTop: '1px solid rgba(0,255,136,0.08)', padding: '16px', marginTop: '40px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.25)', letterSpacing: '0.1em', position: 'relative', zIndex: 2 }}>
          <p>DATA SOURCE: YAHOO FINANCE ◆ DELAY: 15-20 MIN ◆ FOR EDUCATIONAL USE ONLY</p>
          <p style={{ marginTop: '4px', color: 'rgba(255,34,68,0.25)' }}>NOT FINANCIAL ADVICE</p>
        </footer>
      </>}
    </div>
  );
}

const AppWrapper = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/technical-summary" element={<TechnicalSummaryPage />} />
    </Routes>
  </BrowserRouter>
);

export default AppWrapper;
