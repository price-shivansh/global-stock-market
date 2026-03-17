/**
 * BacktestPanel.jsx
 * Strategy backtester UI: select stock, period, strategy → view metrics + equity curve.
 */
import { useState } from 'react';
import axios from 'axios';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from 'recharts';

const API = '/api';

const HoloCorners = () => (
    <>
        <span className="holo-corner tl" />
        <span className="holo-corner tr" />
        <span className="holo-corner bl" />
        <span className="holo-corner br" />
    </>
);

const STOCK_OPTIONS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'LT.NS', 'AXISBANK.NS',
    'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS', 'BAJFINANCE.NS', 'WIPRO.NS',
    '^NSEI', '^NSEBANK', 'BTC-USD', 'GC=F', 'CL=F',
];

const PERIODS = ['3mo', '6mo', '1y', '2y'];
const STRATEGIES = [
    { value: 'RSI', label: 'RSI Strategy' },
    { value: 'MACD', label: 'MACD Strategy' },
    { value: 'RSI_MACD', label: 'RSI + MACD Combined' },
];

const selectStyle = {
    background: 'rgba(0,255,136,0.04)',
    border: '1px solid rgba(0,255,136,0.2)',
    color: '#fff',
    fontFamily: 'Share Tech Mono',
    fontSize: '0.8rem',
    padding: '8px 10px',
    width: '100%',
    outline: 'none',
    borderRadius: '2px',
};

const labelStyle = {
    fontFamily: 'Orbitron',
    fontSize: '0.5rem',
    letterSpacing: '0.15em',
    color: 'rgba(0,255,136,0.5)',
    marginBottom: '4px',
};

const StatCard = ({ label, value, color = '#00ff88', suffix = '' }) => (
    <div style={{
        background: 'rgba(0,255,136,0.03)',
        border: `1px solid ${color}22`,
        padding: '14px',
        textAlign: 'center',
    }}>
        <div style={{
            fontFamily: 'Orbitron', fontSize: '0.48rem', letterSpacing: '0.2em',
            color: 'rgba(255,255,255,0.35)', marginBottom: '8px'
        }}>{label}</div>
        <div style={{
            fontFamily: 'Orbitron', fontWeight: 800, fontSize: '1.4rem',
            color, textShadow: `0 0 12px ${color}`
        }}>
            {value}{suffix}
        </div>
    </div>
);

const HoloTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div style={{
            background: 'rgba(2,12,27,0.97)', border: '1px solid rgba(0,255,136,0.3)',
            padding: '8px 12px', fontFamily: 'Share Tech Mono', fontSize: '0.7rem'
        }}>
            <p style={{ color: 'rgba(0,255,136,0.5)', marginBottom: '4px' }}>{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color || '#00ff88' }}>
                    {p.name}: ₹{Number(p.value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </p>
            ))}
        </div>
    );
};

export default function BacktestPanel() {
    const [symbol, setSymbol] = useState('RELIANCE.NS');
    const [period, setPeriod] = useState('3mo');
    const [strategy, setStrategy] = useState('RSI');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    const handleRun = async () => {
        setLoading(true);
        setError('');
        setResult(null);
        try {
            const res = await axios.post(`${API}/backtest`, { symbol, period, strategy });
            setResult(res.data);
        } catch (e) {
            setError(e.response?.data?.detail || 'Backtest failed. Try a different symbol or period.');
        } finally {
            setLoading(false);
        }
    };

    const netColor = result ? (result.net_return_pct >= 0 ? '#00ff88' : '#ff2244') : '#00ff88';
    const winColor = result ? (result.win_rate >= 50 ? '#00ff88' : '#ffaa00') : '#00ff88';

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* ── Config Form ── */}
            <div className="holo-panel relative">
                <HoloCorners />
                <div className="panel-header">🧪 BACKTEST CONFIGURATION</div>
                <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '12px', alignItems: 'end' }}>

                    <div>
                        <div style={labelStyle}>SYMBOL</div>
                        <select value={symbol} onChange={e => setSymbol(e.target.value)} style={selectStyle}>
                            {STOCK_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>

                    <div>
                        <div style={labelStyle}>PERIOD</div>
                        <select value={period} onChange={e => setPeriod(e.target.value)} style={selectStyle}>
                            {PERIODS.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
                        </select>
                    </div>

                    <div>
                        <div style={labelStyle}>STRATEGY</div>
                        <select value={strategy} onChange={e => setStrategy(e.target.value)} style={selectStyle}>
                            {STRATEGIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                    </div>

                    <button onClick={handleRun} disabled={loading} className="holo-btn"
                        style={{ whiteSpace: 'nowrap', fontSize: '0.65rem' }}>
                        {loading ? '⏳ RUNNING...' : '▶ RUN BACKTEST'}
                    </button>
                </div>
            </div>

            {/* ── Error ── */}
            {error && (
                <div style={{
                    padding: '12px 16px', background: 'rgba(255,34,68,0.08)',
                    border: '1px solid rgba(255,34,68,0.3)', fontFamily: 'Share Tech Mono',
                    fontSize: '0.75rem', color: '#ff2244'
                }}>
                    ⚠ {error}
                </div>
            )}

            {/* ── Loading ── */}
            {loading && (
                <div style={{
                    textAlign: 'center', padding: '40px',
                    fontFamily: 'Orbitron', fontSize: '0.7rem', color: 'rgba(0,255,136,0.5)',
                    letterSpacing: '0.3em', animation: 'arcBlink 1s step-end infinite'
                }}>
                    ◆ SIMULATING {result?.total_trades ?? '...'} TRADES ◆
                </div>
            )}

            {/* ── Results ── */}
            {result && !loading && (
                <>
                    {/* Header */}
                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.4)' }}>
                        {result.symbol} · {result.strategy} · {result.period.toUpperCase()} · Capital ₹1,00,000
                    </div>

                    {/* Stat Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px' }}>
                        <StatCard label="WIN RATE" value={result.win_rate?.toFixed(1)} suffix="%" color={winColor} />
                        <StatCard label="TOTAL TRADES" value={result.total_trades} color="#00eeff" />
                        <StatCard label="MAX DRAWDOWN" value={result.max_drawdown_pct?.toFixed(2)} suffix="%" color="#ffaa00" />
                        <StatCard label="NET RETURN" value={result.net_return_pct >= 0 ? '+' + result.net_return_pct?.toFixed(2) : result.net_return_pct?.toFixed(2)} suffix="%" color={netColor} />
                    </div>

                    {/* Equity Curve */}
                    <div className="holo-panel relative overflow-hidden">
                        <HoloCorners />
                        <div className="panel-header">📈 EQUITY CURVE</div>
                        <div style={{ padding: '8px 4px 16px 0' }}>
                            <ResponsiveContainer width="100%" height={280}>
                                <AreaChart data={result.equity_curve}
                                    margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={netColor} stopOpacity={0.25} />
                                            <stop offset="95%" stopColor={netColor} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,255,136,0.06)" />
                                    <XAxis dataKey="date"
                                        tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }}
                                        axisLine={false} tickLine={false}
                                        tickFormatter={d => d?.slice(5)}
                                        interval={Math.floor((result.equity_curve.length || 1) / 6)}
                                    />
                                    <YAxis
                                        tick={{ fill: 'rgba(0,255,136,0.4)', fontSize: 9, fontFamily: 'Share Tech Mono' }}
                                        axisLine={false} tickLine={false} width={70}
                                        tickFormatter={v => '₹' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v)}
                                    />
                                    <Tooltip content={<HoloTooltip />} />
                                    <Area type="monotone" dataKey="equity" name="Equity"
                                        stroke={netColor} strokeWidth={2}
                                        fill="url(#equityGrad)" dot={false}
                                        style={{ filter: `drop-shadow(0 0 4px ${netColor})` }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Trade Log */}
                    {result.trade_log?.length > 0 && (
                        <div className="holo-panel relative overflow-hidden">
                            <HoloCorners />
                            <div className="panel-header">📋 TRADE LOG ({result.trade_log.length})</div>
                            <div className="overflow-x-auto" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                <table className="w-full holo-table">
                                    <thead>
                                        <tr>
                                            {['#', 'Entry', 'Exit', 'PnL', 'Result', 'Date'].map(h => (
                                                <th key={h} className="px-3 py-2 text-right first:text-left">{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.trade_log.map((t, i) => (
                                            <tr key={i}>
                                                <td className="px-3 py-2" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>{i + 1}</td>
                                                <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.entry?.toFixed(2)}</td>
                                                <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.exit?.toFixed(2)}</td>
                                                <td className="px-3 py-2 text-right" style={{ fontFamily: 'Orbitron', fontWeight: 700, fontSize: '0.75rem', color: t.win ? '#00ff88' : '#ff2244' }}>
                                                    {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)}
                                                </td>
                                                <td className="px-3 py-2 text-right">
                                                    <span style={{
                                                        fontFamily: 'Orbitron', fontSize: '0.5rem', padding: '2px 6px',
                                                        background: t.win ? 'rgba(0,255,136,0.1)' : 'rgba(255,34,68,0.1)',
                                                        border: `1px solid ${t.win ? 'rgba(0,255,136,0.3)' : 'rgba(255,34,68,0.3)'}`,
                                                        color: t.win ? '#00ff88' : '#ff2244'
                                                    }}>
                                                        {t.win ? 'WIN' : 'LOSS'}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>{t.date}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
