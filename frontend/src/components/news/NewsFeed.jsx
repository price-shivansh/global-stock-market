import { useState, useEffect } from 'react';
import axios from 'axios';
import { Newspaper, Calendar, XCircle, Loader } from 'lucide-react';

const TOPIC_RULES = [
  { label: 'CRYPTO',    color: '#a78bfa', keywords: ['bitcoin','btc','ethereum','eth','crypto','blockchain','defi','nft','solana','bnb','altcoin'] },
  { label: 'OIL & GAS', color: '#fb923c', keywords: ['crude','oil','brent','opec','natural gas','petroleum','refinery','energy'] },
  { label: 'GOLD',      color: '#fbbf24', keywords: ['gold','silver','copper','precious metal','commodity'] },
  { label: 'GLOBAL',    color: '#38bdf8', keywords: ['fed','nasdaq','s&p','dow jones','nikkei','hang seng','ftse','wall street','us stock','global market','rate hike'] },
  { label: 'INDIA',     color: '#34d399', keywords: ['nifty','sensex','nse','bse','sebi','rbi','rupee','indian market','india stock'] },
];

function detectTopic(title) {
  const t = title.toLowerCase();
  for (const rule of TOPIC_RULES) {
    if (rule.keywords.some(k => t.includes(k))) return rule;
  }
  return { label: 'MARKET', color: 'var(--text-muted)' };
}

const SENTIMENT_STYLE = {
  BULLISH: { bg: 'var(--bull-dim)',  border: 'var(--bull-border)',  color: 'var(--bull)' },
  BEARISH: { bg: 'var(--bear-dim)',  border: 'var(--bear-border)',  color: 'var(--bear)' },
  NEUTRAL: { bg: 'var(--warn-dim)',  border: 'var(--warn-border)',  color: 'var(--warn)' },
};

/* ── News History Controls ── */
const NewsHistoryControls = () => {
  const [selectedCat, setSelectedCat] = useState('Indian Markets');
  const categories = ['Indian Markets', 'Crypto', 'Commodities', 'Global Markets'];

  const handleExport = () => window.open(`/api/news/export?category=${encodeURIComponent(selectedCat)}`, '_blank');

  const handleReset = async () => {
    if (!window.confirm(`Reset history for ${selectedCat}?`)) return;
    try {
      await axios.delete(`/api/news/history?category=${encodeURIComponent(selectedCat)}`);
      alert(`History for ${selectedCat} has been reset.`);
    } catch (e) {
      alert('Error resetting: ' + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <div style={{ padding: '8px 14px', display: 'flex', gap: '8px', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', flexWrap: 'wrap' }}>
      <span className="holo-text" style={{ fontSize: '11px' }}>History:</span>
      <select value={selectedCat} onChange={e => setSelectedCat(e.target.value)} style={{
        background: 'var(--bg-panel-alt)', border: '1px solid var(--border-subtle)',
        color: 'var(--text-primary)', fontFamily: 'Inter, sans-serif', fontSize: '12px',
        padding: '3px 6px', borderRadius: '4px', outline: 'none',
      }}>
        {categories.map(c => <option key={c} value={c}>{c}</option>)}
      </select>
      <button onClick={handleExport} className="holo-btn btn-accent" style={{ padding: '3px 10px', fontSize: '11px' }}>Download</button>
      <button onClick={handleReset} className="holo-btn" style={{ padding: '3px 10px', fontSize: '11px', borderColor: 'var(--bear-border)', color: 'var(--bear)' }}>Reset</button>
    </div>
  );
};

/* ── Main NewsFeed ── */
const TOPIC_FILTERS = ['ALL', 'CRYPTO', 'OIL & GAS', 'GOLD', 'GLOBAL', 'INDIA'];

const NewsFeed = ({ news }) => {
  const [filter, setFilter] = useState('ALL');
  const [archiveDate, setArchiveDate] = useState('');
  const [archivedNews, setArchivedNews] = useState(null);
  const [loadingArchive, setLoadingArchive] = useState(false);
  const [availableDates, setAvailableDates] = useState([]);

  // Fetch available dates on mount
  useEffect(() => {
    axios.get('/api/news/history/dates').then(res => {
      setAvailableDates(res.data.dates || []);
    }).catch(err => console.error(err));
  }, []);

  // Fetch when archiveDate changes
  useEffect(() => {
    if (!archiveDate) {
      setArchivedNews(null);
      return;
    }
    setLoadingArchive(true);
    axios.get(`/api/news/history?date=${archiveDate}`)
      .then(res => setArchivedNews(res.data.news || []))
      .catch(err => console.error(err))
      .finally(() => setLoadingArchive(false));
  }, [archiveDate]);

  const displayNews = archiveDate ? archivedNews : news;
  const hasNews = displayNews && displayNews.length > 0;

  return (
    <div className="holo-panel">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="icon-wrap"><Newspaper size={13} /></span>
          Intel Feed
          {hasNews && <span style={{ marginLeft: '4px', color: 'var(--text-muted)', fontSize: '10px' }}>({displayNews.length})</span>}
          {archiveDate ? (
            <span style={{ fontSize: '10px', background: 'var(--warn-dim)', color: 'var(--warn)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>HISTORICAL: {archiveDate}</span>
          ) : (
            <span style={{ fontSize: '10px', background: 'var(--bull-dim)', color: 'var(--bull)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>LIVE NEWS</span>
          )}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {archiveDate && (
            <button onClick={() => setArchiveDate('')} className="holo-btn" style={{ padding: '4px 8px', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <XCircle size={12} /> Live News
            </button>
          )}
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <Calendar size={13} style={{ position: 'absolute', left: '6px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input 
              type="date" 
              value={archiveDate}
              onChange={e => setArchiveDate(e.target.value)}
              style={{ padding: '2px 6px 2px 24px', fontSize: '11px', background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', borderRadius: '4px' }}
            />
          </div>
        </div>
      </div>

      <NewsHistoryControls />

      {/* Topic filter pills */}
      <div style={{ display: 'flex', gap: '6px', padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', overflowX: 'auto', flexWrap: 'nowrap' }}>
        {TOPIC_FILTERS.map(f => {
          const rule = TOPIC_RULES.find(r => r.label === f);
          const active = filter === f;
          return (
            <button key={f} onClick={() => setFilter(f)} style={{
              fontFamily: 'Inter, sans-serif', fontSize: '11px', fontWeight: active ? 600 : 400,
              padding: '4px 10px', cursor: 'pointer', whiteSpace: 'nowrap', borderRadius: '4px',
              background: active ? (rule ? `${rule.color}18` : 'var(--accent-dim)') : 'transparent',
              border: `1px solid ${active ? (rule?.color || 'var(--accent)') : 'var(--border-subtle)'}`,
              color: active ? (rule?.color || 'var(--accent)') : 'var(--text-muted)',
              transition: 'all 0.15s',
            }}>
              {f}
            </button>
          );
        })}
      </div>

      {/* News list */}
      <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
        {loadingArchive ? (
          <div style={{ padding: '24px', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <Loader size={16} className="animate-spin" style={{ color: 'var(--accent)' }}/>
            <span className="holo-text">Loading archive...</span>
          </div>
        ) : !displayNews || displayNews.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center' }}>
            <span className="holo-text">No news available for {archiveDate || 'current feed'}</span>
          </div>
        ) : (() => {
          const filtered = displayNews.filter(item => filter === 'ALL' || detectTopic(item.title).label === filter);
          if (filtered.length === 0) {
            return (
              <div style={{ padding: '24px', textAlign: 'center' }}>
                <span className="holo-text">No {filter} news yet</span>
              </div>
            );
          }
          return filtered.slice(0, 30).map((item, idx) => {
            const s = SENTIMENT_STYLE[item.sentiment] || SENTIMENT_STYLE.NEUTRAL;
            const topic = detectTopic(item.title);
            return (
              <a key={idx} href={item.url} target="_blank" rel="noopener noreferrer"
                style={{ display: 'block', padding: '11px 14px', borderBottom: '1px solid var(--border-subtle)', textDecoration: 'none', transition: 'background 0.12s' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-panel-alt)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display: 'flex', gap: '5px', marginBottom: '5px', alignItems: 'center' }}>
                  <span style={{ background: `${topic.color}18`, border: `1px solid ${topic.color}40`, color: topic.color, fontFamily: 'Inter, sans-serif', fontSize: '9px', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', padding: '1px 6px', borderRadius: '3px' }}>
                    {topic.label}
                  </span>
                  <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color, fontFamily: 'Inter, sans-serif', fontSize: '9px', fontWeight: 600, textTransform: 'uppercase', padding: '1px 6px', borderRadius: '3px' }}>
                    {item.sentiment}
                  </span>
                </div>
                <p style={{ fontFamily: 'Inter, sans-serif', fontSize: '13px', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.4, marginBottom: '5px' }}>
                  {item.title}
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="holo-text" style={{ fontSize: '10px' }}>{item.source}</span>
                  <span className="holo-text" style={{ fontSize: '10px' }}>
                    {new Date(item.published).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </a>
            );
          });
        })()}
      </div>
    </div>
  );
};

export default NewsFeed;
