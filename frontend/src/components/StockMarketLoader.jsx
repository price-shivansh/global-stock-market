import React, { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';
import './StockMarketLoader.css';

const LOADING_STEPS = [
  "Connecting to market feeds...",
  "Scanning live signals...",
  "Initializing technical indicators...",
  "Preparing sentiment engine...",
  "Loading dashboard..."
];

const MOCK_TICKERS = [
  { name: 'NIFTY 50', price: '21,456.65', change: '+124.50', up: true },
  { name: 'BANKNIFTY', price: '47,835.20', change: '-45.15', up: false },
  { name: 'SENSEX', price: '71,483.75', change: '+325.80', up: true },
  { name: 'BTC-USD', price: '$43,512.00', change: '+1.2%', up: true },
  { name: 'CRUDE OIL', price: '$74.25', change: '-0.8%', up: false },
  { name: 'GOLD', price: '$2,035.10', change: '+0.5%', up: true },
];

// Replicate tickers for seamless infinite scroll
const SCROLL_TICKERS = [...MOCK_TICKERS, ...MOCK_TICKERS, ...MOCK_TICKERS];

// Generate realistic looking candlestick data
const generateCandles = () => {
  const candles = [];
  let currentPrice = 100;
  for (let i = 0; i < 30; i++) {
    const isUp = Math.random() > 0.45;
    const bodySize = Math.random() * 15 + 5;
    const upperWick = Math.random() * 10;
    const lowerWick = Math.random() * 10;
    
    const change = isUp ? (Math.random() * 5 + 2) : -(Math.random() * 5 + 2);
    const open = currentPrice;
    const close = currentPrice + change;
    const high = Math.max(open, close) + upperWick;
    const low = Math.min(open, close) - lowerWick;
    
    currentPrice = close;
    
    candles.push({ isUp, open, close, high, low });
  }
  
  // Normalize heights to fit in a 100px container
  const minLow = Math.min(...candles.map(c => c.low));
  const maxHigh = Math.max(...candles.map(c => c.high));
  const range = maxHigh - minLow || 1;
  
  return candles.map(c => ({
    ...c,
    openPct: ((c.open - minLow) / range) * 100,
    closePct: ((c.close - minLow) / range) * 100,
    highPct: ((c.high - minLow) / range) * 100,
    lowPct: ((c.low - minLow) / range) * 100,
    bodyBottom: ((Math.min(c.open, c.close) - minLow) / range) * 100,
    bodyHeight: ((Math.abs(c.open - c.close)) / range) * 100,
  }));
};

const StockMarketLoader = ({ onDone }) => {
  const [visible, setVisible] = useState(true);
  const [fading, setFading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [candles, setCandles] = useState([]);

  useEffect(() => {
    setCandles(generateCandles());
  }, []);

  useEffect(() => {
    // Animate text sub-steps
    const stepTimer = setInterval(() => {
      setStepIndex(prev => Math.min(prev + 1, LOADING_STEPS.length - 1));
    }, 900);

    // Fade out logic 
    const t1 = setTimeout(() => setFading(true), 4200);
    const t2 = setTimeout(() => { setVisible(false); onDone?.(); }, 5000);

    return () => { 
      clearInterval(stepTimer);
      clearTimeout(t1); 
      clearTimeout(t2); 
    };
  }, [onDone]);

  if (!visible) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'var(--bg-base)',
      display: 'flex', flexDirection: 'column',
      opacity: fading ? 0 : 1, transition: 'opacity 0.8s ease',
      pointerEvents: fading ? 'none' : 'all', overflow: 'hidden',
    }}>
      
      {/* Background Graphic pulse */}
      <div className="sml-pulse-bg" />

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        
        {/* Animated Candlestick Chart */}
        <div style={{
          position: 'relative', width: '320px', height: '140px',
          borderBottom: '1px solid var(--border-subtle)',
          borderLeft: '1px solid var(--border-subtle)',
          display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
          padding: '0 4px 0 8px', marginBottom: '40px'
        }}>
          {candles.map((candle, i) => {
            const color = candle.isUp ? 'var(--bull)' : 'var(--bear)';
            return (
              <div key={i} style={{
                position: 'relative', width: '6px', height: '100%',
                display: 'flex', justifyContent: 'center',
                animation: `smlFadeUpIn 0.5s ease-out ${i * 0.05}s both`
              }}>
                {/* Wick */}
                <div style={{
                  position: 'absolute', width: '1px', background: color,
                  bottom: `${candle.lowPct}%`, height: `${candle.highPct - candle.lowPct}%`,
                  opacity: 0.7
                }} />
                {/* Body */}
                <div style={{
                  position: 'absolute', width: '100%', background: color,
                  bottom: `${candle.bodyBottom}%`, height: `${Math.max(candle.bodyHeight, 1)}%`,
                  boxShadow: `0 0 6px ${color}40`,
                  borderRadius: '1px'
                }} />
              </div>
            );
          })}
          
          {/* Glowing Line Overlay */}
          <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none' }}>
            <polyline 
              fill="none" 
              stroke="var(--accent)" 
              strokeWidth="2"
              strokeDasharray="1000"
              strokeDashoffset="1000"
              className="sml-draw-line"
              points={candles.map((c, i) => `${8 + i * (308 / (candles.length - 1 || 1))},${140 - (c.closePct / 100 * 140)}`).join(' ')}
            />
          </svg>
        </div>

        {/* Loading Text */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', marginBottom: '12px' }}>
            <Activity className="animate-spin" size={20} color="var(--accent)" style={{ animationDuration: '3s' }} />
            <h1 style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: '24px', letterSpacing: '0.05em', color: 'var(--text-primary)', margin: 0 }}>
              Options <span style={{ color: 'var(--bear)' }}>Signal</span> Dashboard
            </h1>
          </div>
          
          <div style={{ height: '20px', overflow: 'hidden', position: 'relative' }}>
            {LOADING_STEPS.map((step, idx) => (
              <p key={idx} style={{ 
                fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', 
                color: 'var(--text-secondary)', margin: 0,
                position: 'absolute', width: '100%',
                opacity: stepIndex === idx ? 1 : 0,
                transform: `translateY(${stepIndex === idx ? 0 : (idx < stepIndex ? '-20px' : '20px')})`,
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
              }}>
                {step}
              </p>
            ))}
          </div>

          <div style={{ height: '2px', width: '200px', margin: '20px auto 0', background: 'var(--bg-panel-alt)', position: 'relative', overflow: 'hidden', borderRadius: '2px' }}>
            <div className="sml-progress-fill" />
          </div>
        </div>
      </div>

      {/* Scrolling Ticker Strip */}
      <div style={{ 
        width: '100%', background: 'var(--bg-panel)',
        borderTop: '1px solid var(--border-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '12px 0', overflow: 'hidden', display: 'flex',
        position: 'absolute', bottom: '10%',
        boxShadow: '0 0 20px rgba(0,0,0,0.5)'
      }}>
        <div className="sml-ticker-track">
          {SCROLL_TICKERS.map((ticker, idx) => {
            const color = ticker.up ? 'var(--bull)' : 'var(--bear)';
            return (
              <div key={idx} style={{ 
                display: 'flex', alignItems: 'center', gap: '8px', 
                padding: '0 24px', borderRight: '1px solid var(--border-subtle)',
                whiteSpace: 'nowrap'
              }}>
                <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>{ticker.name}</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: 'var(--text-secondary)' }}>{ticker.price}</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color, display: 'flex', alignItems: 'center' }}>
                  {ticker.up ? '▲' : '▼'} {ticker.change}
                </span>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
};

export default StockMarketLoader;
