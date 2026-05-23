// components/market/IndexCard.jsx
import { ChevronUp, ChevronDown } from 'lucide-react';

const IndexCard = ({ data, name }) => {
  if (!data) return (
    <div className="holo-panel p-4" style={{ minHeight: '90px' }}>
      <div className="holo-skeleton" style={{ height: '11px', width: '80px', marginBottom: '10px' }} />
      <div className="holo-skeleton" style={{ height: '26px', width: '120px', marginBottom: '8px' }} />
      <div className="holo-skeleton" style={{ height: '11px', width: '70px' }} />
    </div>
  );

  const isPositive = data.change >= 0;
  const priceColor = isPositive ? 'var(--bull)' : 'var(--bear)';

  return (
    <div
      className="holo-panel p-4 transition-colors"
      style={{ borderLeft: `3px solid ${priceColor}` }}
    >
      <p style={{
        fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
        textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px',
      }}>{name}</p>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <p className="holo-value" style={{ fontSize: '22px', color: priceColor }}>
          {data.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </p>
        <div style={{
          padding: '4px',
          background: isPositive ? 'var(--bull-dim)' : 'var(--bear-dim)',
          borderRadius: '4px',
        }}>
          {isPositive
            ? <ChevronUp size={16} style={{ color: 'var(--bull)' }} />
            : <ChevronDown size={16} style={{ color: 'var(--bear)' }} />}
        </div>
      </div>

      <div className="holo-text" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px', color: priceColor }}>
        <span>{isPositive ? '+' : ''}{data.change?.toFixed(2)}</span>
        <span style={{ color: 'var(--text-muted)' }}>|</span>
        <span>{isPositive ? '+' : ''}{data.change_percent?.toFixed(2)}%</span>
      </div>
    </div>
  );
};

export default IndexCard;
