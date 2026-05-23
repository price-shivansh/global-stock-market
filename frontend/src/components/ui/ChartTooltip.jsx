// components/ui/ChartTooltip.jsx
const ChartTooltip = ({ active, payload, label, symbol }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border-active)',
      borderRadius: '6px',
      padding: '8px 12px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '11px',
    }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || 'var(--accent)' }}>
          {p.name}: {p.value?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </p>
      ))}
    </div>
  );
};

export default ChartTooltip;
