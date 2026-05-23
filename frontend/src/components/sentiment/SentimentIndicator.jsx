// components/sentiment/SentimentIndicator.jsx
import { PieChart } from 'lucide-react';

const SentimentIndicator = ({ sentiment }) => {
  if (!sentiment) return null;
  const isBullish = sentiment.overall_sentiment === 'BULLISH';
  const isBearish = sentiment.overall_sentiment === 'BEARISH';
  const pct = Math.min(100, Math.max(0, ((sentiment.sentiment_score + 1) / 2) * 100));
  const color = isBullish ? 'var(--bull)' : isBearish ? 'var(--bear)' : 'var(--warn)';

  return (
    <div className="holo-panel">
      <div className="panel-header">
        <span className="icon-wrap"><PieChart size={13} /></span>
        Market Sentiment
      </div>
      <div style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span className="holo-text">Score: {sentiment.sentiment_score?.toFixed(3)}</span>
          <span className="holo-value" style={{ fontSize: '13px', color }}>{sentiment.overall_sentiment}</span>
        </div>

        {/* Sentiment bar */}
        <div className="sentiment-bar" style={{ marginBottom: '6px', position: 'relative' }}>
          <div style={{
            position: 'absolute', left: `${pct}%`, top: '-4px',
            width: '2px', height: '14px', background: 'var(--text-primary)',
            transform: 'translateX(-50%)', transition: 'left 0.8s ease',
            borderRadius: '1px',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px' }}>
          <span className="holo-text" style={{ fontSize: '10px', color: 'var(--bear)' }}>Bear</span>
          <span className="holo-text" style={{ fontSize: '10px', color: 'var(--warn)' }}>Neutral</span>
          <span className="holo-text" style={{ fontSize: '10px', color: 'var(--bull)' }}>Bull</span>
        </div>

        {/* Count pills */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
          {[
            { label: 'Bearish', value: sentiment.bearish_count, color: 'var(--bear)', dim: 'var(--bear-dim)', border: 'var(--bear-border)' },
            { label: 'Neutral', value: sentiment.neutral_count, color: 'var(--warn)', dim: 'var(--warn-dim)', border: 'var(--warn-border)' },
            { label: 'Bullish', value: sentiment.bullish_count, color: 'var(--bull)', dim: 'var(--bull-dim)', border: 'var(--bull-border)' },
          ].map(({ label, value, color, dim, border }) => (
            <div key={label} style={{
              background: dim, border: `1px solid ${border}`,
              borderRadius: '6px', padding: '8px 4px', textAlign: 'center',
            }}>
              <div className="holo-value" style={{ fontSize: '18px', color }}>{value}</div>
              <div style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginTop: '2px' }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SentimentIndicator;
