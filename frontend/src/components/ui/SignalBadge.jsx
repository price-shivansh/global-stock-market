// components/ui/SignalBadge.jsx
const SIGNAL_CONFIG = {
  STRONG_BUY:  { cls: 'badge-strong-buy badge-base',  label: '▲▲ Strong Buy' },
  BUY:         { cls: 'badge-buy badge-base',          label: '▲ Buy' },
  HOLD:        { cls: 'badge-hold badge-base',         label: '◆ Hold' },
  SELL:        { cls: 'badge-sell badge-base',         label: '▼ Sell' },
  STRONG_SELL: { cls: 'badge-strong-sell badge-base',  label: '▼▼ Strong Sell' },
};

const SignalBadge = ({ signal }) => {
  const cfg = SIGNAL_CONFIG[signal] || SIGNAL_CONFIG.HOLD;
  return <span className={cfg.cls}>{cfg.label}</span>;
};

export default SignalBadge;
