import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowLeft } from 'lucide-react';

const API_BASE = '/api';

const HoloCorners = () => (
    <>
        <span className="holo-corner tl" />
        <span className="holo-corner tr" />
        <span className="holo-corner bl" />
        <span className="holo-corner br" />
    </>
);

const TechnicalSummaryPage = () => {
    const navigate = useNavigate();
    const [symbol, setSymbol] = useState("RELIANCE.NS");
    const [inputSymbol, setInputSymbol] = useState("");
    const [interval, setInterval] = useState("1d");

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const res = await axios.get(`${API_BASE}/technical-summary/${symbol}/${interval}`);
            setData(res.data);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'FAILED TO FETCH TECHNICAL SUMMARY');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [symbol, interval]);

    // Auto Refresh
    useEffect(() => {
        const timer = window.setInterval(() => {
            fetchData();
        }, 60000); // refresh every 60s

        return () => clearInterval(timer);
    }, [symbol, interval]);

    const handleSearch = () => {
        if (!inputSymbol) return;

        let formatted = inputSymbol.toUpperCase();
        if (!formatted.includes(".")) {
            formatted += ".NS";
        }
        setSymbol(formatted);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') handleSearch();
    };

    const getColor = (sig) => {
        if (sig === 'BUY' || sig === 'STRONG_BUY') return '#00ff88';
        if (sig === 'SELL' || sig === 'STRONG_SELL') return '#ff2244';
        return '#ffaa00';
    };

    const getOverallBadge = (sig) => {
        const labels = {
            STRONG_BUY: '▲▲ STRONG BUY',
            BUY: '▲ BUY',
            SELL: '▼ SELL',
            STRONG_SELL: '▼▼ STRONG SELL',
            NEUTRAL: '◆ NEUTRAL',
        };
        return labels[sig] || sig;
    };

    return (
        <div style={{ minHeight: '100vh', background: '#020c1b', position: 'relative', overflowX: 'hidden' }}>
            <header style={{ background: 'linear-gradient(180deg, rgba(0,8,20,0.98) 0%, rgba(2,12,27,0.95) 100%)', borderBottom: '1px solid rgba(0,255,136,0.15)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(20px)' }}>
                <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '14px 16px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <button
                        onClick={() => navigate('/')}
                        style={{ fontFamily: 'Orbitron', fontSize: '0.65rem', padding: '8px 16px', cursor: 'pointer', border: '1px solid rgba(0,255,136,0.3)', background: 'transparent', color: '#00ff88', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s', letterSpacing: '0.15em' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.1)'; e.currentTarget.style.boxShadow = '0 0 10px rgba(0,255,136,0.2)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.boxShadow = 'none' }}
                    >
                        <ArrowLeft size={14} /> BACK
                    </button>
                    <div style={{ width: '1px', height: '32px', background: 'rgba(0,255,136,0.15)' }} />
                    <div className="flex items-center gap-3">
                        <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,100,255,0.1))', border: '1px solid rgba(0,255,136,0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Activity size={18} style={{ color: '#00ff88' }} />
                        </div>
                        <div>
                            <h1 style={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '1.1rem', letterSpacing: '0.15em', color: '#00ff88', textShadow: '0 0 10px rgba(0,255,136,0.5)', margin: 0 }}>TECHNICAL SUMMARY</h1>
                            <p style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.4)', letterSpacing: '0.2em', margin: 0, marginTop: '2px' }}>LIVE ANALYSIS</p>
                        </div>
                    </div>
                </div>
            </header>

            <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 16px' }}>

                {/* SEARCH AND TIMEFRAME CONTROLS */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    {/* Search */}
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <input
                            type="text"
                            placeholder="SYMBOL (e.g. RELIANCE)"
                            value={inputSymbol}
                            onChange={(e) => setInputSymbol(e.target.value)}
                            onKeyDown={handleKeyDown}
                            style={{
                                background: 'rgba(0,0,0,0.5)',
                                border: '1px solid rgba(0,255,136,0.3)',
                                color: '#00ff88',
                                fontFamily: 'Share Tech Mono',
                                padding: '8px 16px',
                                outline: 'none',
                                letterSpacing: '0.1em'
                            }}
                        />
                        <button
                            onClick={handleSearch}
                            style={{
                                background: 'rgba(0,255,136,0.1)',
                                border: '1px solid rgba(0,255,136,0.5)',
                                color: '#00ff88',
                                fontFamily: 'Orbitron',
                                fontSize: '0.7rem',
                                padding: '8px 20px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                letterSpacing: '0.1em'
                            }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.2)'; e.currentTarget.style.boxShadow = '0 0 10px rgba(0,255,136,0.3)' }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.1)'; e.currentTarget.style.boxShadow = 'none' }}
                        >
                            SEARCH
                        </button>
                    </div>

                    {/* Timeframe Selector */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {['5m', '15m', '1h', '4h', '1d'].map((t) => (
                            <button
                                key={t}
                                onClick={() => setInterval(t)}
                                style={{
                                    fontFamily: 'Orbitron',
                                    fontSize: '0.7rem',
                                    letterSpacing: '0.1em',
                                    padding: '8px 16px',
                                    cursor: 'pointer',
                                    background: interval === t ? 'rgba(0,255,136,0.15)' : 'transparent',
                                    border: `1px solid ${interval === t ? 'rgba(0,255,136,0.8)' : 'rgba(0,255,136,0.2)'}`,
                                    color: interval === t ? '#00ff88' : 'rgba(0,255,136,0.5)',
                                    textShadow: interval === t ? '0 0 8px rgba(0,255,136,0.5)' : 'none',
                                    transition: 'all 0.2s',
                                }}
                            >
                                {t.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                {loading ? (
                    <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ fontFamily: 'Share Tech Mono', color: '#00ff88', fontSize: '1.2rem', animation: 'arcPulse 1.5s infinite' }}>LOADING ANALYSIS...</div>
                    </div>
                ) : error || !data ? (
                    <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ fontFamily: 'Share Tech Mono', color: '#ff2244', fontSize: '1.2rem' }}>{error || 'DATA UNAVAILABLE'}</div>
                    </div>
                ) : (
                    <>
                        {/* OVERALL SIGNAL */}
                        <div className="holo-panel text-center mb-8" style={{ padding: '40px 20px', position: 'relative' }}>
                            <HoloCorners />

                            <h2 style={{ fontFamily: 'Orbitron', fontSize: '1.2rem', color: '#00ff88', letterSpacing: '0.15em', marginBottom: '8px', textShadow: '0 0 10px rgba(0,255,136,0.3)' }}>
                                {symbol}
                            </h2>
                            <h3 style={{ fontFamily: 'Orbitron', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', letterSpacing: '0.2em', marginBottom: '20px' }}>
                                INTERVAL: {interval.toUpperCase()}
                            </h3>

                            <div className="holo-value" style={{ fontSize: '3.5rem', color: getColor(data.overall), textShadow: `0 0 20px ${getColor(data.overall)}`, letterSpacing: '0.05em' }}>
                                {getOverallBadge(data.overall)}
                            </div>

                            <div style={{
                                fontFamily: 'Share Tech Mono', fontSize: '1.1rem', marginTop: '16px', letterSpacing: '0.1em',
                                color: data.confidence >= 70 ? getColor(data.overall) : data.confidence >= 40 ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.4)',
                                textShadow: data.confidence >= 70 ? `0 0 10px ${getColor(data.overall)}` : 'none'
                            }}>
                                CONFIDENCE: {data.confidence}%
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', marginTop: '30px' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '2.5rem', color: '#ff2244', fontFamily: 'Orbitron', textShadow: '0 0 10px #ff2244' }}>{data.sell}</div>
                                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.8rem', color: 'rgba(255,34,68,0.7)', letterSpacing: '0.1em' }}>SELL</div>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '2.5rem', color: '#ffaa00', fontFamily: 'Orbitron', textShadow: '0 0 10px #ffaa00' }}>{data.neutral}</div>
                                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.8rem', color: 'rgba(255,170,0,0.7)', letterSpacing: '0.1em' }}>NEUTRAL</div>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '2.5rem', color: '#00ff88', fontFamily: 'Orbitron', textShadow: '0 0 10px #00ff88' }}>{data.buy}</div>
                                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.8rem', color: 'rgba(0,255,136,0.7)', letterSpacing: '0.1em' }}>BUY</div>
                                </div>
                            </div>
                        </div>

                        {/* SUMMARY GRIDS */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                            {/* OSCILLATORS START */}
                            <div className="holo-panel" style={{ padding: '24px', position: 'relative' }}>
                                <HoloCorners />
                                <h3 style={{ fontFamily: 'Orbitron', fontSize: '1rem', color: '#00eeff', letterSpacing: '0.1em', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <Activity size={18} /> OSCILLATORS
                                </h3>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid rgba(0,255,136,0.1)' }}>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#ff2244', fontFamily: 'Orbitron' }}>{data.oscillators.sell}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(255,34,68,0.7)' }}>SELL</div>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#ffaa00', fontFamily: 'Orbitron' }}>{data.oscillators.neutral}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(255,170,0,0.7)' }}>NEUTRAL</div>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#00ff88', fontFamily: 'Orbitron' }}>{data.oscillators.buy}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.7)' }}>BUY</div>
                                    </div>
                                </div>
                                <table className="w-full text-left" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.85rem' }}>
                                    <tbody>
                                        {data.details.slice(0, 4).map((d, i) => (
                                            <tr key={i} style={{ borderBottom: i !== 3 ? '1px solid rgba(0,255,136,0.1)' : 'none' }}>
                                                <td style={{ padding: '12px 0', color: 'rgba(255,255,255,0.7)' }}>{d.name}</td>
                                                <td style={{ padding: '12px 0', textAlign: 'right', color: 'rgba(0,255,136,0.5)' }}>{d.value}</td>
                                                <td style={{ padding: '12px 0', textAlign: 'right', color: getColor(d.signal) }}>{d.signal}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* MOVING AVERAGES START */}
                            <div className="holo-panel" style={{ padding: '24px', position: 'relative' }}>
                                <HoloCorners />
                                <h3 style={{ fontFamily: 'Orbitron', fontSize: '1rem', color: '#aa00ff', letterSpacing: '0.1em', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    MOVING AVERAGES
                                </h3>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid rgba(0,255,136,0.1)' }}>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#ff2244', fontFamily: 'Orbitron' }}>{data.moving_averages.sell}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(255,34,68,0.7)' }}>SELL</div>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#ffaa00', fontFamily: 'Orbitron' }}>{data.moving_averages.neutral}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(255,170,0,0.7)' }}>NEUTRAL</div>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.5rem', color: '#00ff88', fontFamily: 'Orbitron' }}>{data.moving_averages.buy}</div>
                                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.7)' }}>BUY</div>
                                    </div>
                                </div>
                                <table className="w-full text-left" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.85rem' }}>
                                    <tbody>
                                        {data.details.slice(4).map((d, i, arr) => (
                                            <tr key={i} style={{ borderBottom: i !== arr.length - 1 ? '1px solid rgba(0,255,136,0.1)' : 'none' }}>
                                                <td style={{ padding: '12px 0', color: 'rgba(255,255,255,0.7)' }}>{d.name}</td>
                                                <td style={{ padding: '12px 0', textAlign: 'right', color: 'rgba(0,255,136,0.5)' }}>{d.value}</td>
                                                <td style={{ padding: '12px 0', textAlign: 'right', color: getColor(d.signal) }}>{d.signal}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </>
                )}
            </main>
        </div>
    );
};

export default TechnicalSummaryPage;
