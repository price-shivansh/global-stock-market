// components/signals/SignalsPanel.jsx
import SignalBadge from '../ui/SignalBadge';
import { Zap } from 'lucide-react';

const SignalsPanel = ({ signals, onStockClick }) => {
  if (!signals || signals.length === 0) return null;
  return (
    <div className="holo-panel">
      <div className="panel-header">
        <span className="icon-wrap"><Zap size={13} /></span>
        Signal Matrix
      </div>
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {signals.map((signal, idx) => (
          <div key={idx}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              cursor: 'pointer',
              transition: 'background 0.12s',
            }}
            onClick={() => onStockClick?.({ symbol: signal.symbol, name: signal.symbol.replace('.NS', '') })}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-panel-alt)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
              <div>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13px' }}>
                  {signal.symbol.replace('.NS', '')}
                </span>
                <div className="holo-text" style={{ marginTop: '2px', fontSize: '10px' }}>
                  Strength: {signal.strength?.toFixed(1)}%
                </div>
              </div>
              <SignalBadge signal={signal.signal_type} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {signal.reasons?.slice(0, 2).map((reason, ridx) => (
                <div key={ridx} className="holo-text" style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '11px' }}>
                  <span style={{ color: 'var(--bear)', fontSize: '8px' }}>◆</span>
                  {reason}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '16px', marginTop: '6px' }}>
              <span className="holo-text" style={{ fontSize: '11px' }}>
                Tech: <span style={{ color: signal.technical_score >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                  {signal.technical_score?.toFixed(0)}
                </span>
              </span>
              <span className="holo-text" style={{ fontSize: '11px' }}>
                Sent: <span style={{ color: signal.sentiment_score >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                  {signal.sentiment_score?.toFixed(0)}
                </span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SignalsPanel;
