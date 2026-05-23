// components/market/StockChartModal.jsx
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { X } from 'lucide-react';
import {
  ComposedChart, Area, Bar, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import ChartTooltip from '../ui/ChartTooltip';
import QuantDashboard from '../quant/QuantDashboard';

const getApiBase = () => {
  const url = import.meta.env.VITE_API_URL;
  if (!url) return '/api';
  const clean = url.endsWith('/') ? url.slice(0, -1) : url;
  return `${clean.startsWith('http') ? '' : 'https://'}${clean}/api`;
};
const API_BASE = getApiBase();

const PERIODS = ['1mo', '3mo', '6mo', '1y'];

const StockChartModal = ({ symbol, name, onClose }) => {
  const [chartData, setChartData] = useState(null);
  const [period, setPeriod]   = useState('6mo');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(p => {
    setLoading(true);
    axios.get(`${API_BASE}/historical/${encodeURIComponent(symbol)}?period=${p}`)
      .then(r => setChartData(r.data?.data || []))
      .catch(() => setChartData([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => { fetchData(period); }, [fetchData, period]);

  const isUp = chartData?.length > 1
    ? chartData[chartData.length - 1].close >= chartData[0].close
    : true;
  const lineColor = isUp ? '#34d399' : '#f85149';
  const min = chartData ? Math.min(...chartData.map(d => d.low))  * 0.997 : 0;
  const max = chartData ? Math.max(...chartData.map(d => d.high)) * 1.003 : 0;

  useEffect(() => {
    // Lock body scroll when modal is open
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, []);

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.70)',
        backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '16px',
      }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div 
        className="holo-panel relative" 
        style={{ 
          width: 'min(1100px, 95vw)', 
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          padding: 0 // Remove padding here, add to internal sections
        }}
      >

        {/* Header - Fixed */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0
        }}>
          <div>
            <h2 style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)' }}>
              {name || symbol}
            </h2>
            <p className="holo-text" style={{ marginTop: '2px' }}>{symbol}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {PERIODS.map(p => (
              <button key={p} onClick={() => setPeriod(p)} className={`holo-btn ${period === p ? 'btn-accent' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}>
                {p.toUpperCase()}
              </button>
            ))}
            <button onClick={onClose} className="holo-btn" style={{ padding: '5px 8px', color: 'var(--bear)', borderColor: 'var(--bear-border)' }}>
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Content Body - Scrollable */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '16px 20px 24px 20px',
          // Custom scrollbar styling to match theme
          scrollbarWidth: 'thin',
          scrollbarColor: 'var(--chart-axis) transparent'
        }}>
          {loading ? (
            <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="holo-text">Loading chart data…</span>
            </div>
          ) : !chartData?.length ? (
            <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="holo-text" style={{ color: 'var(--bear)' }}>No data available</span>
            </div>
          ) : (
            <>
              {/* Summary stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '10px', marginBottom: '16px' }}>
                {[
                  { label: 'Open',  value: chartData[0]?.open },
                  { label: 'High',  value: Math.max(...chartData.map(d => d.high)) },
                  { label: 'Low',   value: Math.min(...chartData.map(d => d.low)) },
                  { label: 'Close', value: chartData[chartData.length - 1]?.close },
                ].map(({ label, value }) => (
                  <div key={label} style={{
                    background: 'var(--bg-panel-alt)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px', padding: '10px 12px', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</div>
                    <div className="holo-value" style={{ fontSize: '14px', color: lineColor }}>
                      {value?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </div>
                  </div>
                ))}
              </div>

              {/* OHLC Composed Chart */}
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="modalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={lineColor} stopOpacity={0.18} />
                      <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="date"
                    tick={{ fill: 'var(--chart-axis)', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
                    axisLine={false} tickLine={false}
                    tickFormatter={d => d?.slice(5)}
                    interval={Math.floor((chartData?.length || 1) / 6)}
                  />
                  <YAxis yAxisId="price" domain={[min, max]}
                    tick={{ fill: 'var(--chart-axis)', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
                    axisLine={false} tickLine={false} width={60}
                    tickFormatter={v => v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(2)}
                  />
                  <YAxis yAxisId="volume" orientation="right" hide />
                  <Tooltip content={<ChartTooltip symbol={symbol} />} />
                  <Bar yAxisId="volume" dataKey="volume" fill="rgba(52,211,153,0.08)" stroke="rgba(52,211,153,0.15)" radius={[2,2,0,0]} name="Volume" />
                  <Area yAxisId="price" type="monotone" dataKey="close"
                    stroke={lineColor} strokeWidth={2}
                    fill="url(#modalGrad)" dot={false} name="Close"
                  />
                  <Line yAxisId="price" type="monotone" dataKey="high" stroke="rgba(52,211,153,0.25)" strokeWidth={1} dot={false} name="High" strokeDasharray="3 3" />
                  <Line yAxisId="price" type="monotone" dataKey="low"  stroke="rgba(248,81,73,0.25)"  strokeWidth={1} dot={false} name="Low"  strokeDasharray="3 3" />
                </ComposedChart>
              </ResponsiveContainer>

              {/* Quant Decision Engine Dashboard */}
              <div style={{ marginTop: '24px' }}>
                <QuantDashboard symbol={symbol} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StockChartModal;
