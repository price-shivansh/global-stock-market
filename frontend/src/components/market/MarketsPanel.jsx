// components/market/MarketsPanel.jsx
import { useState } from 'react';
import { Globe, BarChart2, DollarSign, Cpu, ArrowLeftRight } from 'lucide-react';

const MARKET_TABS = [
  { key: 'global_indices', label: 'Global',      icon: Globe,          color: '#38bdf8' },
  { key: 'sector_indices', label: 'Sectors',     icon: BarChart2,      color: 'var(--bull)' },
  { key: 'commodities',    label: 'Commodities', icon: DollarSign,     color: 'var(--warn)' },
  { key: 'crypto',         label: 'Crypto',      icon: Cpu,            color: '#a78bfa' },
  { key: 'forex',          label: 'Forex',       icon: ArrowLeftRight, color: '#fb923c' },
];

function formatPrice(price, sym) {
  if (!price) return '—';
  if (sym?.includes('-USD') || sym?.includes('=X')) return price.toLocaleString('en-US', { maximumFractionDigits: 4 });
  if (sym?.includes('=F')) return '$' + price.toLocaleString('en-US', { maximumFractionDigits: 2 });
  if (sym?.startsWith('^')) return price.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return '₹' + price.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

const MarketsPanel = ({ marketsData, loading, onStockClick }) => {
  const [activeTab, setActiveTab] = useState('global_indices');
  const tab   = MARKET_TABS.find(t => t.key === activeTab);
  const items = marketsData?.[activeTab] || [];

  return (
    <div className="holo-panel">
      {/* Tab bar */}
      <div className="tab-bar">
        {MARKET_TABS.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`tab-btn ${activeTab === t.key ? 'active' : ''}`}
            style={activeTab === t.key ? { color: t.color, borderBottomColor: t.color } : {}}
          >
            <t.icon size={12} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <span className="holo-text">Loading data…</span>
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <span className="holo-text" style={{ color: 'var(--bear)' }}>No data available</span>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="holo-table">
            <thead><tr>
              <th style={{ textAlign: 'left' }}>Name</th>
              <th style={{ textAlign: 'right' }}>Price</th>
              <th style={{ textAlign: 'right' }}>Change</th>
              <th style={{ textAlign: 'right' }}>Change %</th>
              <th style={{ textAlign: 'right' }}>Volume</th>
            </tr></thead>
            <tbody>
              {items.map((item, i) => {
                const up  = item.change >= 0;
                const clr = up ? 'var(--bull)' : 'var(--bear)';
                return (
                  <tr key={i} style={{ cursor: 'pointer' }}
                    onClick={() => onStockClick?.(item)}>
                    <td>
                      <div style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '13px' }}>{item.name}</div>
                      <div className="holo-text" style={{ fontSize: '10px', color: tab.color, opacity: 0.7 }}>{item.symbol}</div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="holo-value" style={{ color: clr }}>{formatPrice(item.price, item.symbol)}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="holo-value" style={{ color: clr, fontSize: '12px' }}>
                        {up ? '+' : ''}{item.change?.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="holo-value" style={{ color: clr, fontSize: '12px' }}>
                        {up ? '+' : ''}{item.change_percent?.toFixed(2)}%
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="holo-text">
                        {item.volume > 0 ? (item.volume / 1e6).toFixed(2) + 'M' : '—'}
                      </span>
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

export default MarketsPanel;
