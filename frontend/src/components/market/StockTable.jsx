// components/market/StockTable.jsx
import { TrendingUp } from 'lucide-react';

const CATEGORY_COLORS = {
  '🇮🇳 India':    'var(--bull)',
  '🌍 Global':    '#38bdf8',
  '📊 Sector':    '#6ee7b7',
  '🏭 Commodity': 'var(--warn)',
  '🔷 Crypto':    '#a78bfa',
  '💱 Forex':     '#fb923c',
};

function getCurrencyPrefix(sym) {
  if (!sym) return '₹';
  if (sym.includes('-USD') || sym.includes('=X') || sym.includes('=F')) return '$';
  if (sym.startsWith('^')) return '';
  return '₹';
}

function fmtVolume(vol, sym) {
  if (!vol || vol <= 0) return '—';
  if (sym?.endsWith('.NS')) return (vol / 100000).toFixed(1) + 'L';
  if (vol >= 1e9) return (vol / 1e9).toFixed(2) + 'B';
  if (vol >= 1e6) return (vol / 1e6).toFixed(2) + 'M';
  if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
  return vol.toString();
}

const StockTable = ({ stocks, title, icon: Icon = TrendingUp, accentColor = 'var(--bull)', onStockClick }) => {
  if (!stocks || stocks.length === 0) return null;
  return (
    <div className="holo-panel">
      <div className="panel-header">
        <span className="icon-wrap" style={{ color: accentColor }}><Icon size={13} /></span>
        {title}
        <span style={{ marginLeft: '4px', color: 'var(--text-muted)', fontSize: '10px' }}>({stocks.length})</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="holo-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Name</th>
              <th style={{ textAlign: 'right' }}>Price</th>
              <th style={{ textAlign: 'right' }}>Change</th>
              <th style={{ textAlign: 'right' }}>Vol</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock, idx) => {
              const up = stock.change >= 0;
              const clr = up ? 'var(--bull)' : 'var(--bear)';
              const cat = stock.category;
              const catClr = cat ? (CATEGORY_COLORS[cat] || 'var(--text-muted)') : null;
              const prefix = getCurrencyPrefix(stock.symbol);
              return (
                <tr key={idx}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onStockClick?.(stock)}
                  title="Click to view chart"
                >
                  <td>
                    {cat && (
                      <span style={{
                        display: 'inline-block', marginBottom: '3px',
                        fontSize: '9px', fontWeight: 600, letterSpacing: '0.04em',
                        textTransform: 'uppercase', padding: '1px 5px', borderRadius: '3px',
                        background: `${catClr}18`, border: `1px solid ${catClr}38`, color: catClr,
                      }}>{cat}</span>
                    )}
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '13px' }}>{stock.name}</div>
                    <div className="holo-text" style={{ fontSize: '10px', marginTop: '1px' }}>
                      {stock.symbol} <span style={{ color: 'var(--text-muted)', fontSize: '9px' }}>↗</span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="holo-value" style={{ color: clr, fontSize: '13px' }}>
                      {prefix}{Number(stock.price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div className="holo-value" style={{ color: clr, fontSize: '12px' }}>
                      {up ? '+' : ''}{stock.change?.toFixed(2)}
                    </div>
                    <div className="holo-text" style={{ color: clr, fontSize: '10px' }}>
                      {up ? '+' : ''}{stock.change_percent?.toFixed(2)}%
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="holo-text">{fmtVolume(stock.volume, stock.symbol)}</span>
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

export default StockTable;
