/**
 * PaperTradingPanel.jsx
 * Layout:
 *   ┌─────────────────┬────────────────────────────────────────┐
 *   │  NEW ORDER form │  PRICE CHART                           │
 *   │                 │  [1M][3M][6M][1Y][2Y]  [LINE][CANDLES]│
 *   └─────────────────┴────────────────────────────────────────┘
 *   ┌──────────────────────────────────────────────────────────┐
 *   │  OPEN / CLOSED POSITIONS (full width)                    │
 *   └──────────────────────────────────────────────────────────┘
 *
 * Candlestick implementation:
 *   Uses Bar with a custom CandleShape that ignores Recharts' own y/height
 *   and instead computes pixel positions from background + a pre-computed
 *   domain that exactly matches the YAxis domain prop.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';
import {
    AreaChart, Area, ComposedChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import LightweightChart from './ui/LightweightChart';
import QuantPanelMock from './quant/QuantPanelMock';

const API = '/api';

// ── Asset type detection ──────────────────────────────────────────────────────
const getAssetType = (sym) => {
    if (!sym) return 'STOCK';
    if (sym.includes('=F')) return 'COMMODITY';
    if (sym.includes('=X')) return 'FOREX';
    if (sym.includes('-USD')) return 'CRYPTO';
    if (sym.startsWith('^')) return 'INDEX';
    return 'STOCK';
};
const ASSET_COLORS = { STOCK: '#00ff88', COMMODITY: '#ffaa00', FOREX: '#00eeff', CRYPTO: '#aa44ff', INDEX: '#ff66aa' };

// ── Quick Preset Groups ────────────────────────────────────────────────────────
const PRESET_GROUPS = [
    { label: 'STOCKS', items: [{ sym: 'RELIANCE.NS', label: 'RELIANCE' }, { sym: '^NSEI', label: 'NIFTY' }, { sym: '^NSEBANK', label: 'BNKN' }] },
    { label: 'COMMOD', items: [{ sym: 'CL=F', label: '🔥 CL=F' }, { sym: 'BZ=F', label: 'BZ=F' }, { sym: 'NG=F', label: 'NG=F' }, { sym: 'GC=F', label: 'GC=F' }] },
    { label: 'FOREX',  items: [{ sym: 'USDINR=X', label: 'USD/INR' }] },
];

// ── Toast component ───────────────────────────────────────────────────────────
const TOAST_STYLES = { SUCCESS: '#00ff88', ERROR: '#ff2244', INFO: '#00eeff', WARN: '#ffaa00' };
function ToastList({ toasts }) {
    return (
        <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '8px', pointerEvents: 'none' }}>
            {toasts.map(t => (
                <div key={t.id} style={{
                    background: 'rgba(2,12,27,0.97)', border: `1px solid ${TOAST_STYLES[t.type] || '#00ff88'}`,
                    padding: '10px 16px', fontFamily: 'Share Tech Mono', fontSize: '0.75rem',
                    color: TOAST_STYLES[t.type] || '#00ff88', boxShadow: `0 0 16px ${TOAST_STYLES[t.type]}33`,
                    minWidth: '260px', animation: 'fadeIn 0.2s ease'
                }}>
                    {t.message}
                </div>
            ))}
        </div>
    );
}

// ── Corner decoration ─────────────────────────────────────────────────────────
const HoloCorners = () => (
    <>
        <span className="holo-corner tl" />
        <span className="holo-corner tr" />
        <span className="holo-corner bl" />
        <span className="holo-corner br" />
    </>
);

// ── Symbol list ───────────────────────────────────────────────────────────────
const ALL_SYMBOLS = [
    // Indian Stocks
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS',
    'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS',
    'BAJFINANCE.NS', 'WIPRO.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'TATAPOWER.NS',
    // Indian Indices
    '^NSEI', '^NSEBANK', '^BSESN',
    // Indian Sector Indices
    '^CNXIT', '^CNXPHARMA', '^CNXAUTO', '^CNXFMCG', '^CNXMETAL', '^CNXREALTY', '^CNXINFRA', '^CNXENERGY',
    // Global Indices
    '^GSPC', '^DJI', '^IXIC', '^N225', '^HSI', '^GDAXI', '^FTSE', '^FCHI',
    // Commodities
    'GC=F', 'SI=F', 'CL=F', 'BZ=F', 'NG=F', 'HG=F',
    // Crypto
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD',
    // Forex
    'USDINR=X', 'EURINR=X', 'GBPINR=X', 'JPYINR=X'
];

const TIMEFRAMES = [
    { label: '1m', value: '1m' }, { label: '3m', value: '3m' },
    { label: '5m', value: '5m' }, { label: '15m', value: '15m' },
    { label: '1H', value: '1h' }, { label: '1D', value: '1d' },
];

// ── Base styles ───────────────────────────────────────────────────────────────
const labelStyle = {
    fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.15em',
    color: 'rgba(0,255,136,0.5)', marginBottom: '4px',
};
const inputBase = {
    background: 'rgba(0,255,136,0.04)', border: '1px solid rgba(0,255,136,0.2)',
    color: '#fff', fontFamily: 'Share Tech Mono', fontSize: '0.8rem',
    padding: '8px 10px', width: '100%', outline: 'none', borderRadius: '2px',
    boxSizing: 'border-box',
};

// ── Pill button ───────────────────────────────────────────────────────────────
const PillBtn = ({ active, onClick, children, color = '#00ff88' }) => (
    <button onClick={onClick} style={{
        fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.12em',
        padding: '4px 10px', cursor: 'pointer',
        border: `1px solid ${active ? color : 'rgba(255,255,255,0.12)'}`,
        background: active ? `${color}1a` : 'transparent',
        color: active ? color : 'rgba(255,255,255,0.35)',
        transition: 'all 0.15s',
    }}>
        {children}
    </button>
);

// ── Searchable symbol picker ──────────────────────────────────────────────────
function SymbolSearch({ value, onChange }) {
    const [query, setQuery] = useState(value);
    const [open, setOpen] = useState(false);
    const [focused, setFocused] = useState(false);
    const wrapRef = useRef(null);

    useEffect(() => { setQuery(value); }, [value]);

    useEffect(() => {
        const h = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, []);

    const filtered = ALL_SYMBOLS.filter(s => s.toLowerCase().includes(query.toLowerCase())).slice(0, 12);
    const select = (sym) => { setQuery(sym); onChange(sym); setOpen(false); };

    return (
        <div ref={wrapRef} style={{ position: 'relative', zIndex: 50 }}>
            <input
                value={query}
                onChange={e => { setQuery(e.target.value); setOpen(true); }}
                onFocus={() => { setFocused(true); setOpen(true); }}
                onBlur={() => setFocused(false)}
                placeholder="Search symbol…"
                autoComplete="off" spellCheck={false}
                style={{
                    ...inputBase,
                    border: `1px solid ${focused ? 'rgba(0,255,136,0.5)' : 'rgba(0,255,136,0.2)'}`,
                    boxShadow: focused ? '0 0 8px rgba(0,255,136,0.1)' : 'none',
                }}
            />
            {open && filtered.length > 0 && (
                <ul style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 999,
                    background: '#030f1e', border: '1px solid rgba(0,255,136,0.25)',
                    borderTop: 'none', maxHeight: '180px', overflowY: 'auto',
                    listStyle: 'none', margin: 0, padding: 0,
                }}>
                    {filtered.map(sym => (
                        <li key={sym} onMouseDown={() => select(sym)} style={{
                            padding: '7px 10px', fontFamily: 'Share Tech Mono', fontSize: '0.75rem',
                            color: sym === value ? '#00ff88' : 'rgba(255,255,255,0.75)',
                            background: sym === value ? 'rgba(0,255,136,0.06)' : 'transparent',
                            cursor: 'pointer', borderBottom: '1px solid rgba(0,255,136,0.05)',
                        }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.1)'; e.currentTarget.style.color = '#00ff88'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = sym === value ? 'rgba(0,255,136,0.06)' : 'transparent'; e.currentTarget.style.color = sym === value ? '#00ff88' : 'rgba(255,255,255,0.75)'; }}
                        >
                            {sym}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

// ── Candlestick shape factory ─────────────────────────────────────────────────
/**
 * makeCandleShape(yLo, yHi) → returns a Recharts custom bar shape.
 *
 * We compute pixel positions ourselves from the chart area's `background` prop
 * (which gives us the exact plotArea y-offset and height) combined with the
 * pre-computed domain [yLo, yHi] that we also set on <YAxis domain>.
 * This guarantees pixel accuracy without relying on yAxis.scale.
 */
function makeCandleShape(yLo, yHi) {
    return function CandleShape(props) {
        const { x, width, payload, background } = props;
        if (!payload || !background || !background.height) return null;

        const { open, high, low, close } = payload;
        if (open == null || high == null || low == null || close == null) return null;

        const isUp = close >= open;
        const stroke = isUp ? '#00ff88' : '#ff2244';
        const fill = isUp ? 'rgba(0,255,136,0.5)' : 'rgba(255,34,68,0.5)';

        // Map a price value → pixel y inside the plot area
        const range = yHi - yLo || 1;
        const top = background.y;
        const bottom = background.y + background.height;
        const toY = (v) => top + (1 - (v - yLo) / range) * background.height;

        const yHigh = toY(high);
        const yLow = toY(low);
        const yOpen = toY(open);
        const yClose = toY(close);

        // Clamp to chart bounds
        const bodyTop = Math.max(Math.min(yOpen, yClose), top);
        const bodyBottom = Math.min(Math.max(yOpen, yClose), bottom);
        const bodyH = Math.max(bodyBottom - bodyTop, 1);

        const cx = x + width / 2;
        const bw = Math.max(width * 0.65, 1.5);

        return (
            <g>
                {/* Upper wick: high → body top */}
                <line x1={cx} y1={Math.max(yHigh, top)} x2={cx} y2={bodyTop} stroke={stroke} strokeWidth={1} />
                {/* Lower wick: body bottom → low */}
                <line x1={cx} y1={bodyBottom} x2={cx} y2={Math.min(yLow, bottom)} stroke={stroke} strokeWidth={1} />
                {/* Candle body */}
                <rect x={cx - bw / 2} y={bodyTop} width={bw} height={bodyH}
                    fill={fill} stroke={stroke} strokeWidth={1} />
            </g>
        );
    };
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
const HoloTooltip = ({ active, payload, label, chartType }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div style={{ background: 'rgba(2,12,27,0.97)', border: '1px solid rgba(0,255,136,0.3)', padding: '10px 14px', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', lineHeight: 1.9 }}>
            <p style={{ color: 'rgba(0,255,136,0.4)', marginBottom: '4px' }}>{label}</p>
            {chartType === 'candle' ? (
                <>
                    <p style={{ color: '#888' }}>O: <span style={{ color: '#fff' }}>{d?.open?.toFixed(2)}</span></p>
                    <p style={{ color: '#888' }}>H: <span style={{ color: '#00ff88' }}>{d?.high?.toFixed(2)}</span></p>
                    <p style={{ color: '#888' }}>L: <span style={{ color: '#ff2244' }}>{d?.low?.toFixed(2)}</span></p>
                    <p style={{ color: '#888' }}>C: <span style={{ color: '#fff' }}>{d?.close?.toFixed(2)}</span></p>
                </>
            ) : (
                <p style={{ color: '#00ff88' }}>{d?.close?.toFixed(2)}</p>
            )}
        </div>
    );
};

const pnlColor = (v) => v == null ? 'rgba(0,255,136,0.5)' : v >= 0 ? '#00ff88' : '#ff2244';

// ── Order Book (Simulated Level 2) ──────────────────────────────────────────
const SimulatedOrderBook = ({ symbol }) => {
    const [book, setBook] = useState({ asks: [], bids: [], currentPrice: 0 });

    // Fetch simulated order book depth using Phase 1 Backend API
    useEffect(() => {
        if (!symbol) return;
        let mounted = true;

        const fetchBook = async () => {
            try {
                const res = await axios.get(`/api/paper-trading/order-book/${encodeURIComponent(symbol)}`);
                if (!mounted) return;
                
                const data = res.data;
                const asks = data.asks.map(a => ({ ...a, total: 0 }));
                const bids = data.bids.map(b => ({ ...b, total: 0 }));
                
                let askTot = 0;
                for (let i = asks.length - 1; i >= 0; i--) { askTot += asks[i].size; asks[i].total = askTot; }
                let bidTot = 0;
                for (let i = 0; i < bids.length; i++) { bidTot += bids[i].size; bids[i].total = bidTot; }
                
                setBook({ asks, bids, currentPrice: data.current_price });
            } catch (e) {
                // Wait quietly
            }
        };

        fetchBook();
        const t = setInterval(fetchBook, 3000); // Poll every 3 seconds
        return () => {
            mounted = false;
            clearInterval(t);
        };
    }, [symbol]);

    if (!book.currentPrice || !book.bids.length) return (
        <div style={{ padding: '32px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.3)' }}>WAITING FOR PRICE...</div>
    );

    const maxVol = Math.max(
        book.asks[0]?.total || 1,
        book.bids[book.bids.length - 1]?.total || 1
    ) * 1.2;

    const rowStyle = {
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
        fontFamily: 'Share Tech Mono', fontSize: '0.65rem', padding: '3px 6px',
        position: 'relative', minHeight: '18px'
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '6px', borderBottom: '1px solid rgba(0,255,136,0.1)', fontFamily: 'Orbitron', fontSize: '0.5rem', color: 'rgba(0,255,136,0.4)', letterSpacing: '0.1em' }}>
                <div>PRICE</div><div style={{ textAlign: 'right' }}>SIZE</div><div style={{ textAlign: 'right' }}>TOTAL</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, justifyContent: 'space-between' }}>
                {/* Asks (Sell Orders - Red) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', marginTop: '4px' }}>
                    {book.asks.map((a, i) => (
                        <div key={`ask-${i}`} style={rowStyle}>
                            <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: `${(a.total / maxVol) * 100}%`, background: 'rgba(255,34,68,0.1)', zIndex: 0 }} />
                            <div style={{ zIndex: 1, color: '#ff2244' }}>{a.price.toFixed(2)}</div>
                            <div style={{ zIndex: 1, textAlign: 'right', color: '#fff' }}>{a.size}</div>
                            <div style={{ zIndex: 1, textAlign: 'right', color: 'rgba(255,255,255,0.4)' }}>{a.total}</div>
                        </div>
                    ))}
                </div>

                {/* Spread / Current Price */}
                <div style={{
                    padding: '8px 0', margin: '4px 0', textAlign: 'center',
                    borderTop: '1px dashed rgba(0,255,136,0.2)', borderBottom: '1px dashed rgba(0,255,136,0.2)',
                    background: 'rgba(0,0,0,0.3)'
                }}>
                    <span className="holo-value" style={{ fontSize: '1rem', color: '#fff', textShadow: '0 0 10px rgba(0,255,136,0.5)' }}>
                        {book.currentPrice.toFixed(2)}
                    </span>
                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.5rem', color: 'rgba(0,255,136,0.4)', marginTop: '2px' }}>SPREAD: {(book.asks[book.asks.length - 1].price - book.bids[0].price).toFixed(2)}</div>
                </div>

                {/* Bids (Buy Orders - Green) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', marginBottom: '4px' }}>
                    {book.bids.map((b, i) => (
                        <div key={`bid-${i}`} style={rowStyle}>
                            <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: `${(b.total / maxVol) * 100}%`, background: 'rgba(0,255,136,0.08)', zIndex: 0 }} />
                            <div style={{ zIndex: 1, color: '#00ff88' }}>{b.price.toFixed(2)}</div>
                            <div style={{ zIndex: 1, textAlign: 'right', color: '#fff' }}>{b.size}</div>
                            <div style={{ zIndex: 1, textAlign: 'right', color: 'rgba(255,255,255,0.4)' }}>{b.total}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};


// ─────────────────────────────────────────────────────────────────────────────
export default function PaperTradingPanel() {

    // ── form ─────────────────────────────────────────────────────────────────
    const [symbol, setSymbol] = useState('RELIANCE.NS');
    const [direction, setDirection] = useState('BUY');
    const [quantity, setQuantity] = useState(10);
    const [stopLoss, setStopLoss] = useState('');
    const [target, setTarget] = useState('');
    const [placing, setPlacing] = useState(false);
    const [placeErr, setPlaceErr] = useState('');

    // ── Toast system ──────────────────────────────────────────────────────────
    const [toasts, setToasts] = useState([]);
    const toast = (message, type = 'SUCCESS') => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    };

    // ── Live LTP ──────────────────────────────────────────────────────────────
    const [ltp, setLtp] = useState(null);

    // ── positions & account ───────────────────────────────────────────────────
    const [positions, setPositions] = useState({ open: [], closed: [], orders: [] });
    const [initialBalance, setInitialBalance] = useState(100000);
    const [balance, setBalance] = useState(100000); // Available Capital
    const [realizedPnl, setRealizedPnl] = useState(0);
    const [unrealizedPnl, setUnrealizedPnl] = useState(0);
    const [totalEquity, setTotalEquity] = useState(100000);
    const [equityHistory, setEquityHistory] = useState([]);

    // ── chart ─────────────────────────────────────────────────────────────────
    const [chartData, setChartData] = useState([]);
    const [chartLoading, setChartLoading] = useState(false);
    const [chartSymbol, setChartSymbol] = useState('RELIANCE.NS');
    const [timeframe, setTimeframe] = useState('15m');
    const [chartType, setChartType] = useState('line');

    // ── Fetch chart ───────────────────────────────────────────────────────────
    const fetchChart = useCallback(async (sym, interval) => {
        setChartLoading(true);
        setChartData([]);
        try {
            const res = await axios.get(`${API}/paper-trading/chart/${encodeURIComponent(sym)}/${interval}`);
            const raw = Array.isArray(res.data) ? res.data : (res.data?.data ?? []);
            setChartData(raw);
            setChartSymbol(sym);
        } catch { setChartData([]); }
        finally { setChartLoading(false); }
    }, []);

    // Initial load + update LTP from chart data
    useEffect(() => { fetchChart('RELIANCE.NS', '15m'); }, []); // eslint-disable-line

    // Keep LTP in sync with latest chart close price
    useEffect(() => {
        if (chartData.length > 0) {
            setLtp(chartData[chartData.length - 1]?.close ?? null);
        }
    }, [chartData]);

    // Timeframe change
    const handleTimeframeChange = (tf) => {
        setTimeframe(tf);
        fetchChart(symbol, tf);
    };

    const handleSymbolSelect = (sym) => { setSymbol(sym); fetchChart(sym, timeframe); };

    // ── Crude Oil Mode ────────────────────────────────────────────────────────
    const handleCrudeOilMode = () => {
        setSymbol('CL=F');
        setQuantity(10);
        setTimeframe('5m');
        fetchChart('CL=F', '5m');
        toast('🔥 Crude Oil Mode activated — CL=F, 5m', 'WARN');
    };

    // ── Preset quick-select ───────────────────────────────────────────────────
    const handlePreset = (sym) => {
        setSymbol(sym);
        fetchChart(sym, timeframe);
    };

    // ── PnL polling (Phase 1) ──────────────────────────────────────────────────
    const fetchPositions = useCallback(async () => {
        try {
            const [oRes, cRes, aRes, ordRes] = await Promise.all([
                axios.get(`${API}/paper-trading/open-positions`),
                axios.get(`${API}/paper-trading/history`),
                axios.get(`${API}/paper-trading/account`),
                axios.get(`${API}/paper-trading/orders`)
            ]);
            setPositions({ open: oRes.data, closed: cRes.data, orders: ordRes.data });
            
            const acc = aRes.data;
            setInitialBalance(acc.initial_capital);
            setBalance(acc.available_capital);
            setRealizedPnl(acc.realized_pnl);
            setUnrealizedPnl(acc.unrealized_pnl);
            setTotalEquity(acc.total_equity);
            
            // Reconstruct a simplified equity history from API
            setEquityHistory(prev => {
                // Ensure recent state changes push points
                const next = [...prev, { time: new Date().toISOString(), equity: acc.total_equity }];
                return next.slice(-80);
            });
        } catch (e) { console.error('Error fetching positions', e); }
    }, []);

    useEffect(() => {
        fetchPositions();
        const id = setInterval(fetchPositions, 3000);
        return () => clearInterval(id);
    }, [fetchPositions]);

    // ── Trade actions (Phase 1) ────────────────────────────────────────────────
    const handlePlace = async () => {
        setPlaceErr('');
        const qty = Number(quantity);
        const sl  = Number(stopLoss);
        const tgt = Number(target);
        const price = ltp || currentPrice;

        if (!symbol)         { setPlaceErr('Symbol is required.'); return; }
        if (qty <= 0)        { setPlaceErr('Quantity must be > 0.'); return; }
        if (!stopLoss || !target) { setPlaceErr('Stop Loss and Target are required.'); return; }
        if (sl <= 0 || tgt <= 0) { setPlaceErr('SL and Target must be positive.'); return; }
        if (balance <= 0)    { setPlaceErr('Simulation Account Blown.'); return; }

        // Directional SL / Target validation
        if (price > 0) {
            if (direction === 'BUY') {
                if (sl >= price) { setPlaceErr('BUY: Stop Loss must be BELOW current price.'); return; }
                if (tgt <= price) { setPlaceErr('BUY: Target must be ABOVE current price.'); return; }
            } else {
                if (sl <= price) { setPlaceErr('SELL: Stop Loss must be ABOVE current price.'); return; }
                if (tgt >= price) { setPlaceErr('SELL: Target must be BELOW current price.'); return; }
            }
        }

        setPlacing(true);
        const assetStr = getAssetType(symbol).toLowerCase();
        const asset_type = assetStr === 'index' ? 'stock' : assetStr;

        try {
            await axios.post(`${API}/paper-trading/order`, {
                symbol, asset_type,
                side: direction.toLowerCase(),
                quantity: qty,
                stop_loss: sl,
                target: tgt,
                timeframe
            });
            setStopLoss(''); setTarget('');
            fetchPositions();
            toast(`✅ ${direction} ${qty}× ${symbol} placed!`, 'SUCCESS');
        } catch (e) {
            const msg = e.response?.data?.detail || 'Error placing trade.';
            setPlaceErr(msg);
            toast(`⚠ ${msg}`, 'ERROR');
        } finally { setPlacing(false); }
    };

    const handleClose = async (id) => {
        try { await axios.post(`${API}/paper-trading/close/${id}`); fetchPositions(); toast('Position closed manually.', 'INFO'); } catch { }
    };

    // ── Chart derived data ────────────────────────────────────────────────────
    // For candlesticks: cap at 180 bars so candles are wide enough to see
    const displayData = useMemo(() =>
        chartType === 'candle' ? chartData.slice(-180) : chartData
        , [chartData, chartType]);

    // Pre-compute domain for candlestick mode — MUST match <YAxis domain>
    const { yLo, yHi } = useMemo(() => {
        if (!displayData.length) return { yLo: 0, yHi: 1 };
        const lows = displayData.map(d => d.low ?? d.close ?? 0);
        const highs = displayData.map(d => d.high ?? d.close ?? 1);
        const rawLo = Math.min(...lows);
        const rawHi = Math.max(...highs);
        const pad = (rawHi - rawLo) * 0.04;
        return { yLo: rawLo - pad, yHi: rawHi + pad };
    }, [displayData]);

    // Memoise the custom shape so it doesn't re-create on every render
    const CandleShape = useMemo(() => makeCandleShape(yLo, yHi), [yLo, yHi]);

    // Line chart colour based on net direction
    const firstClose = chartData[0]?.close;
    const lastClose = chartData[chartData.length - 1]?.close;
    const lineColor = (firstClose && lastClose && lastClose >= firstClose) ? '#00ff88' : '#ff2244';

    const tickInterval = Math.max(Math.floor(displayData.length / 6), 1);
    const tickFmt = (d) => d?.slice(5) ?? '';
    const priceFmt = (v) => v >= 1000 ? (v / 1000).toFixed(1) + 'k' : String(v);

    // ── Risk Calculator ───────────────────────────────────────────────────────
    const currentPrice = chartData[chartData.length - 1]?.close || 0;
    const riskAmount = stopLoss && !isNaN(stopLoss) ? Math.abs(currentPrice - Number(stopLoss)) * quantity : 0;
    const riskPercent = balance > 0 ? (riskAmount / balance) * 100 : 0;
    const expectedRiskColor = riskPercent > 3 ? '#ff2244' : 'rgba(0,255,136,0.5)';

    // ─────────────────────────────────────────────────────────────────────────
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <ToastList toasts={toasts} />

            {/* ── TOP ROW ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 22%) minmax(0, 1fr) minmax(260px, 22%)', gap: '16px', alignItems: 'start' }}>

                {/* New Order Form */}
                <div className="holo-panel relative" style={{ padding: 0 }}>
                    <HoloCorners />
                    <div className="panel-header">📋 NEW ORDER</div>
                    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>

                        {/* 🔥 Crude Oil Mode */}
                        <button onClick={handleCrudeOilMode} style={{
                            width: '100%', padding: '7px', fontFamily: 'Orbitron', fontSize: '0.55rem',
                            letterSpacing: '0.12em', cursor: 'pointer', border: '1px solid rgba(255,170,0,0.5)',
                            background: 'rgba(255,170,0,0.08)', color: '#ffaa00', transition: 'all 0.2s',
                        }}>🔥 CRUDE OIL MODE</button>

                        {/* Preset Buttons */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {PRESET_GROUPS.map(grp => (
                                <div key={grp.label} style={{ display: 'flex', gap: '4px', alignItems: 'center', flexWrap: 'wrap' }}>
                                    <span style={{ fontFamily: 'Orbitron', fontSize: '0.45rem', color: 'rgba(0,255,136,0.3)', letterSpacing: '0.1em', minWidth: '50px' }}>{grp.label}</span>
                                    {grp.items.map(({ sym, label }) => (
                                        <button key={sym} onClick={() => handlePreset(sym)} style={{
                                            fontFamily: 'Share Tech Mono', fontSize: '0.65rem', padding: '3px 7px',
                                            cursor: 'pointer', background: symbol === sym ? 'rgba(0,255,136,0.12)' : 'transparent',
                                            border: `1px solid ${symbol === sym ? '#00ff88' : 'rgba(255,255,255,0.12)'}`,
                                            color: symbol === sym ? '#00ff88' : 'rgba(255,255,255,0.5)', transition: 'all 0.15s',
                                        }}>{label}</button>
                                    ))}
                                </div>
                            ))}
                        </div>

                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <div style={labelStyle}>SYMBOL</div>
                                {/* Asset Type Badge */}
                                <span style={{
                                    fontFamily: 'Orbitron', fontSize: '0.45rem', letterSpacing: '0.12em',
                                    padding: '2px 6px', border: `1px solid ${ASSET_COLORS[getAssetType(symbol)]}55`,
                                    background: `${ASSET_COLORS[getAssetType(symbol)]}11`,
                                    color: ASSET_COLORS[getAssetType(symbol)],
                                }}>{getAssetType(symbol)}</span>
                            </div>
                            <SymbolSearch value={symbol} onChange={handleSymbolSelect} />
                        </div>

                        <div>
                            <div style={labelStyle}>DIRECTION</div>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {['BUY', 'SELL'].map(d => (
                                    <button key={d} onClick={() => setDirection(d)} style={{
                                        flex: 1, padding: '8px', fontFamily: 'Orbitron', fontSize: '0.65rem', letterSpacing: '0.15em',
                                        cursor: 'pointer', border: '1px solid', transition: 'all 0.2s',
                                        borderColor: direction === d ? (d === 'BUY' ? '#00ff88' : '#ff2244') : 'rgba(255,255,255,0.1)',
                                        background: direction === d ? (d === 'BUY' ? 'rgba(0,255,136,0.12)' : 'rgba(255,34,68,0.12)') : 'transparent',
                                        color: direction === d ? (d === 'BUY' ? '#00ff88' : '#ff2244') : 'rgba(255,255,255,0.4)',
                                    }}>
                                        {d === 'BUY' ? '▲ BUY' : '▼ SELL'}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div style={labelStyle}>QUANTITY</div>
                            <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} min="1" style={inputBase} />
                        </div>
                        <div>
                            <div style={labelStyle}>STOP LOSS</div>
                            <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)} placeholder="Price" style={inputBase} />
                        </div>
                        <div>
                            <div style={labelStyle}>TARGET</div>
                            <input type="number" value={target} onChange={e => setTarget(e.target.value)} placeholder="Price" style={inputBase} />
                        </div>

                        {placeErr && <p style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: '#ff2244' }}>⚠ {placeErr}</p>}

                        {/* Risk Calculator */}
                        {currentPrice > 0 && stopLoss && !isNaN(stopLoss) && (
                            <div style={{ marginTop: '8px', padding: '8px 10px', background: riskPercent > 3 ? 'rgba(255,34,68,0.1)' : 'rgba(0,255,136,0.05)', border: `1px solid ${riskPercent > 3 ? 'rgba(255,34,68,0.3)' : 'rgba(0,255,136,0.2)'}`, borderRadius: '4px' }}>
                                <div style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: expectedRiskColor, display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Risking: ₹{riskAmount.toFixed(2)}</span>
                                    <span>({riskPercent.toFixed(1)}% of capital)</span>
                                </div>
                                {riskPercent > 3 && (
                                    <div style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', color: '#ff2244', marginTop: '4px', letterSpacing: '0.05em' }}>
                                        ⚠ HIGH RISK WARNING (&gt;3%)
                                    </div>
                                )}
                            </div>
                        )}

                        <button onClick={handlePlace} disabled={placing || balance <= 0} className="holo-btn" style={{ width: '100%', marginTop: '4px', fontSize: '0.65rem' }}>
                            {balance <= 0 ? 'ACCOUNT BLOWN' : placing ? '⏳ PLACING...' : '⚡ EXECUTE TRADE'}
                        </button>
                    </div>
                </div>

                {/* Center Column */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* Chart Panel */}
                    <div className="holo-panel relative overflow-hidden" style={{ minHeight: '520px' }}>
                        <HoloCorners />

                    {/* Header row */}
                    <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                        <span style={{ flexShrink: 0, fontFamily: 'Orbitron', fontSize: '0.6rem' }}>
                            📈 {chartSymbol}
                            {ltp != null && (
                                <span style={{ marginLeft: '10px', fontFamily: 'Share Tech Mono', fontSize: '0.75rem', color: lineColor, fontWeight: 700 }}>
                                    {ltp.toFixed(ltp >= 100 ? 2 : 4)}
                                </span>
                            )}
                            <span style={{ marginLeft: '8px', fontFamily: 'Orbitron', fontSize: '0.45rem', padding: '2px 5px', border: `1px solid ${ASSET_COLORS[getAssetType(chartSymbol)]}55`, color: ASSET_COLORS[getAssetType(chartSymbol)] }}>{getAssetType(chartSymbol)}</span>
                            {chartLoading && (
                                <span style={{ marginLeft: '10px', fontSize: '0.5rem', color: '#ffaa00', animation: 'arcBlink 1s step-end infinite' }}>LOADING…</span>
                            )}
                        </span>

                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                            {/* Refresh Button */}
                            <button
                                onClick={() => fetchChart(symbol, timeframe)}
                                disabled={chartLoading}
                                title="Refresh Chart"
                                style={{
                                    background: 'transparent', border: 'none', color: chartLoading ? 'rgba(0,255,136,0.3)' : '#00ff88',
                                    cursor: chartLoading ? 'not-allowed' : 'pointer', padding: '4px', display: 'flex', alignItems: 'center',
                                    transition: 'transform 0.2s', transform: chartLoading ? 'rotate(180deg)' : 'none'
                                }}
                            >
                                ⟳
                            </button>

                            <div style={{ width: '1px', height: '14px', background: 'rgba(0,255,136,0.15)', margin: '0 4px' }} />

                            {/* Timeframe */}
                            <div style={{ display: 'flex', gap: '3px' }}>
                                {TIMEFRAMES.map(tf => (
                                    <PillBtn key={tf.value} active={timeframe === tf.value} onClick={() => handleTimeframeChange(tf.value)}>
                                        {tf.label}
                                    </PillBtn>
                                ))}
                            </div>

                            <div style={{ width: '1px', height: '14px', background: 'rgba(0,255,136,0.15)' }} />

                            {/* Chart type */}
                            <div style={{ display: 'flex', gap: '3px' }}>
                                <PillBtn active={chartType === 'line'} onClick={() => setChartType('line')}>LINE</PillBtn>
                                <PillBtn active={chartType === 'candle'} onClick={() => setChartType('candle')} color="#00eeff">CANDLES</PillBtn>
                            </div>
                        </div>
                    </div>

                    {/* Empty state */}
                    {displayData.length === 0 && !chartLoading && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '290px', fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(0,255,136,0.2)', letterSpacing: '0.2em' }}>
                            SELECT A SYMBOL TO VIEW CHART
                        </div>
                    )}

                    {/* Charts */}
                    {displayData.length > 0 && (
                        <div style={{ padding: '8px 4px 12px 0' }}>
                            <LightweightChart data={displayData} type={chartType} height={450} />
                        </div>
                    )}
                </div>

                {/* Quant Decision Engine Panel */}
                <QuantPanelMock 
                    symbol={chartSymbol} 
                    onApplyPlan={(plan) => {
                        setDirection(plan.direction);
                        setStopLoss(plan.stopLoss.toString());
                        setTarget(plan.target.toString());
                        if (plan.symbol) setSymbol(plan.symbol);
                    }} 
                />
            </div>

            {/* Simulated Order Book Panel */}
            <div className="holo-panel relative overflow-hidden" style={{ minHeight: '520px' }}>
                    <HoloCorners />
                    <div className="panel-header">📚 MOCK ORDER BOOK</div>
                    <SimulatedOrderBook symbol={symbol} />
                </div>
            </div>

            {/* ── OPEN POSITIONS & LIVE PNL ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', alignItems: 'start' }}>
                <div className="holo-panel relative overflow-hidden">
                    <HoloCorners />
                    <div className="panel-header">🟢 OPEN POSITIONS ({positions.open.length})</div>
                    <div className="overflow-x-auto">
                        {positions.open.length === 0 ? (
                            <div style={{ padding: '28px', textAlign: 'center', fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: 'rgba(0,255,136,0.2)' }}>
                                No open positions
                            </div>
                        ) : (
                            <table className="w-full holo-table">
                                <thead>
                                    <tr>{['ID', 'Symbol', 'Dir', 'Qty', 'Entry', 'Current', 'PnL', 'R:R', 'SL', 'Target', 'Action'].map(h =>
                                        <th key={h} className="px-3 py-2 text-right first:text-left">{h}</th>
                                    )}</tr>
                                </thead>
                                <tbody>
                                    {positions.open.map(t => (
                                        <tr key={t.id}>
                                            <td className="px-3 py-2" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>{t.id}</td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Rajdhani', fontWeight: 600 }}>{t.symbol}</td>
                                            <td className="px-3 py-2 text-right" style={{ color: t.side === 'buy' ? '#00ff88' : '#ff2244', fontFamily: 'Orbitron', fontSize: '0.55rem' }}>
                                                {t.side === 'buy' ? '▲ BUY' : '▼ SELL'}
                                            </td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.quantity}</td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.entry_price?.toFixed(2)}</td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.current_price?.toFixed(2) ?? '—'}</td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Orbitron', fontSize: '0.75rem', fontWeight: 700, color: pnlColor(t.pnl) }}>
                                                {t.pnl != null ? (t.pnl >= 0 ? '+' : '') + t.pnl.toFixed(2) : '—'}
                                            </td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', color: pnlColor(t.pnl_percent) }}>
                                                {t.pnl_percent != null ? t.pnl_percent.toFixed(2) + '%' : '—'}
                                            </td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: '#ff2244' }}>{t.stop_loss}</td>
                                            <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.7rem', color: '#00ff88' }}>{t.target}</td>
                                            <td className="px-3 py-2 text-right">
                                                <button onClick={() => handleClose(t.id)} style={{
                                                    fontFamily: 'Orbitron', fontSize: '0.5rem', letterSpacing: '0.1em', padding: '3px 8px',
                                                    cursor: 'pointer', background: 'rgba(255,34,68,0.12)', border: '1px solid rgba(255,34,68,0.4)', color: '#ff2244',
                                                }}>CLOSE</button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>

                {/* Live PnL / Equity Panel */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div className="holo-panel relative overflow-hidden">
                        <HoloCorners />
                        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>💰 SIMULATED CAPITAL</span>
                            <span style={{ color: totalEquity >= initialBalance ? '#00ff88' : '#ff2244' }}>₹{totalEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                        
                        {/* Capital Breakdown */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', padding: '12px', background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid rgba(0,255,136,0.1)', fontFamily: 'Share Tech Mono', fontSize: '0.7rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fff' }}>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Initial Capital:</span>
                                <span>{initialBalance.toLocaleString()}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fff' }}>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Available Margin:</span>
                                <span>{balance.toLocaleString()}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: pnlColor(realizedPnl) }}>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Realized P&L:</span>
                                <span>{realizedPnl >= 0 ? '+' : ''}{realizedPnl.toLocaleString()}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: pnlColor(unrealizedPnl), fontWeight: 700 }}>
                                <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 400 }}>Unrealized P&L:</span>
                                <span>{unrealizedPnl >= 0 ? '+' : ''}{unrealizedPnl.toLocaleString()}</span>
                            </div>
                        </div>

                        {/* Equity Curve Chart */}
                        <div style={{ height: '90px', marginTop: '10px' }}>
                            {equityHistory.length > 1 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={equityHistory}>
                                        <defs>
                                            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor={totalEquity >= initialBalance ? '#00ff88' : '#ff2244'} stopOpacity={0.3} />
                                                <stop offset="95%" stopColor={totalEquity >= initialBalance ? '#00ff88' : '#ff2244'} stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <Tooltip
                                            contentStyle={{ background: 'rgba(2,12,27,0.95)', border: '1px solid rgba(0,255,136,0.3)', fontFamily: 'Share Tech Mono', fontSize: '0.65rem' }}
                                            itemStyle={{ color: '#fff' }}
                                            formatter={(val) => ['₹' + Number(val).toLocaleString(), 'Equity']}
                                            labelFormatter={() => ''}
                                        />
                                        <Area type="stepAfter" dataKey="equity" stroke={totalEquity >= initialBalance ? '#00ff88' : '#ff2244'} fill="url(#eqGrad)" strokeWidth={1.5} isAnimationActive={false} />
                                    </AreaChart>
                                </ResponsiveContainer>
                            ) : (
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontFamily: 'Share Tech Mono', fontSize: '0.65rem', color: 'rgba(0,255,136,0.2)' }}>
                                    NO TRADE HISTORY
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Active Trade Cards */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '200px', overflowY: 'auto', paddingRight: '4px' }}>
                        {positions.open.map(t => {
                            const isProfit = t.pnl >= 0;
                            const glowClass = isProfit ? 'pnl-flash-profit' : 'pnl-flash-loss';
                            const pnlStr = (isProfit ? '+' : '') + (t.pnl?.toFixed(2) || '0.00');

                            return (
                                <div key={`card-${t.id}`} className={glowClass} style={{
                                    border: `1px solid ${isProfit ? 'rgba(0,255,136,0.3)' : 'rgba(255,34,68,0.3)'}`,
                                    borderRadius: '4px', padding: '10px 12px', background: 'rgba(0,0,0,0.2)'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                        <span style={{ fontFamily: 'Rajdhani', fontWeight: 700, fontSize: '0.8rem', color: '#fff' }}>{t.symbol} <span style={{ fontFamily: 'Orbitron', fontSize: '0.55rem', color: t.side === 'buy' ? '#00ff88' : '#ff2244' }}>{t.side.toUpperCase()}</span></span>
                                        <span style={{ fontFamily: 'Orbitron', fontSize: '0.8rem', fontWeight: 800, color: pnlColor(t.pnl) }}>{pnlStr}</span>
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontFamily: 'Share Tech Mono', fontSize: '0.65rem' }}>
                                        <div>Entry: <span style={{ color: '#fff' }}>{t.entry_price?.toFixed(2)}</span></div>
                                        <div>Curr: <span style={{ color: '#fff' }}>{t.current_price?.toFixed(2) ?? '—'}</span></div>
                                        <div>Return: <span style={{ color: pnlColor(t.pnl_percent) }}>{t.pnl_percent?.toFixed(2)}%</span></div>
                                    </div>
                                    {/* Distance bars */}
                                    {t.current_price && (
                                        <div style={{ marginTop: '8px', display: 'flex', gap: '1px', height: '3px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                                            {t.side === 'buy' ? (
                                                <div style={{ width: `${Math.max(0, Math.min(100, ((t.current_price - t.stop_loss) / (t.target - t.stop_loss)) * 100))}%`, background: '#00ff88' }} />
                                            ) : (
                                                <div style={{ width: `${Math.max(0, Math.min(100, ((t.stop_loss - t.current_price) / (t.stop_loss - t.target)) * 100))}%`, background: '#00ff88' }} />
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* ── CLOSED POSITIONS (TRADE HISTORY) ── */}
            {positions.closed.length > 0 && (
                <div className="holo-panel relative overflow-hidden">
                    <HoloCorners />
                    <div className="panel-header">🔒 TRADE HISTORY LOG ({positions.closed.length})</div>
                    <div className="overflow-x-auto">
                        <table className="w-full holo-table">
                            <thead>
                                <tr>{['UID', 'Symbol', 'Dir', 'Entry', 'Exit', 'Result', 'PnL', 'Closed At'].map(h =>
                                    <th key={h} className="px-3 py-2 text-right first:text-left">{h}</th>
                                )}</tr>
                            </thead>
                            <tbody>
                                {positions.closed.map(t => (
                                    <tr key={t.id}>
                                        <td className="px-3 py-2" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>{t.id}</td>
                                        <td className="px-3 py-2 text-right" style={{ fontFamily: 'Rajdhani', fontWeight: 600 }}>{t.symbol}</td>
                                        <td className="px-3 py-2 text-right" style={{ color: t.side === 'buy' ? '#00ff88' : '#ff2244', fontFamily: 'Orbitron', fontSize: '0.55rem' }}>{t.side.toUpperCase()}</td>
                                        <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.entry_price?.toFixed(2)}</td>
                                        <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono' }}>{t.exit_price?.toFixed(2)}</td>
                                        <td className="px-3 py-2 text-right" style={{
                                            fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.1em',
                                            color: t.close_reason === 'TARGET HIT' ? '#00ff88' : t.close_reason === 'SL HIT' ? '#ff2244' : 'rgba(255,255,255,0.4)'
                                        }}>
                                            {t.close_reason || 'MANUAL'}
                                        </td>
                                        <td className="px-3 py-2 text-right" style={{ fontFamily: 'Orbitron', fontSize: '0.75rem', fontWeight: 700, color: pnlColor(t.pnl) }}>
                                            {t.pnl != null ? (t.pnl >= 0 ? '+' : '') + t.pnl.toFixed(2) : '—'}
                                        </td>
                                        <td className="px-3 py-2 text-right" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,255,136,0.35)' }}>
                                            {t.closed_at ? new Date(t.closed_at).toLocaleTimeString('en-IN') : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
            
            {/* ── ORDER HISTORY (LEDGER LOG) ── */}
            {positions.orders && positions.orders.length > 0 && (
                <div className="holo-panel relative overflow-hidden" style={{ borderColor: 'rgba(0,238,255,0.3)' }}>
                    <HoloCorners />
                    <div className="panel-header" style={{ borderBottomColor: 'rgba(0,238,255,0.1)' }}>
                        <span style={{ color: '#00eeff' }}>📝 ORDER HISTORY LEDGER</span> ({positions.orders.length})
                    </div>
                    <div className="overflow-x-auto" style={{ maxHeight: '350px' }}>
                        <table className="w-full holo-table">
                            <thead style={{ position: 'sticky', top: 0, background: '#020c1b', zIndex: 10 }}>
                                <tr>{['Order ID', 'Placed At', 'Symbol', 'Dir', 'Qty', 'Price', 'Status', 'Message'].map(h =>
                                    <th key={h} className="px-3 py-2 text-left" style={{ color: '#00eeff' }}>{h}</th>
                                )}</tr>
                            </thead>
                            <tbody>
                                {positions.orders.map(o => (
                                    <tr key={`${o.id}-${o.placed_at}`} style={{ borderBottom: '1px solid rgba(0,238,255,0.05)' }}>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(0,238,255,0.4)' }}>{o.id}</td>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.65rem' }}>
                                            {o.placed_at ? new Date(o.placed_at).toLocaleTimeString('en-IN', { hour12: false }) : '—'}
                                        </td>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Rajdhani', fontWeight: 600 }}>{o.symbol}</td>
                                        <td className="px-3 py-2 text-left" style={{ color: o.side === 'buy' ? '#00ff88' : '#ff2244', fontFamily: 'Orbitron', fontSize: '0.55rem' }}>{o.side.toUpperCase()}</td>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Share Tech Mono' }}>{o.quantity}</td>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Share Tech Mono' }}>{o.price?.toFixed(2) ?? '—'}</td>
                                        <td className="px-3 py-2 text-left" style={{
                                            fontFamily: 'Orbitron', fontSize: '0.55rem', letterSpacing: '0.1em',
                                            color: o.status === 'executed' ? '#00ff88' : '#ff2244'
                                        }}>
                                            {o.status.toUpperCase()}
                                        </td>
                                        <td className="px-3 py-2 text-left" style={{ fontFamily: 'Share Tech Mono', fontSize: '0.6rem', color: 'rgba(255,255,255,0.6)' }}>
                                            {o.message}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
