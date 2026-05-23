import React, { useState, useEffect } from 'react';
import { Globe, Clock, Power, PlayCircle } from 'lucide-react';

const MARKETS = [
  { id: 'TSE', name: 'Tokyo (TSE)', region: 'Japan', openTime: '05:30', closeTime: '11:30' },
  { id: 'HKEX', name: 'Hong Kong (HKEX)', region: 'Hong Kong', openTime: '07:00', closeTime: '13:30' },
  { id: 'NSE', name: 'NSE', region: 'India', openTime: '09:15', closeTime: '15:30' },
  { id: 'BSE', name: 'BSE', region: 'India', openTime: '09:15', closeTime: '15:30' },
  { id: 'LSE', name: 'London (LSE)', region: 'UK', openTime: '13:30', closeTime: '22:00' },
  { id: 'NYSE', name: 'NYSE', region: 'US', openTime: '19:00', closeTime: '01:30' },
  { id: 'NASDAQ', name: 'NASDAQ', region: 'US', openTime: '19:00', closeTime: '01:30' },
];

function parseTime(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + m;
}

function formatIST(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hours = h % 12 || 12;
  return `${hours}:${m.toString().padStart(2, '0')} ${ampm} IST`;
}

function getISTCurrentMinutes() {
  const now = new Date();
  const utcMs = now.getTime() + (now.getTimezoneOffset() * 60000);
  const istDate = new Date(utcMs + (5.5 * 3600000));
  return istDate.getHours() * 60 + istDate.getMinutes();
}

function getMarketStates() {
  const currentMin = getISTCurrentMinutes();
  
  const openMarkets = [];
  const nextOpenings = [];
  const nextClosings = [];

  MARKETS.forEach(m => {
    const o = parseTime(m.openTime);
    const c = parseTime(m.closeTime);
    
    let isOpen = false;
    if (o < c) isOpen = currentMin >= o && currentMin < c;
    else isOpen = currentMin >= o || currentMin < c;

    if (isOpen) {
      openMarkets.push({ ...m });
      let minsToClose;
      if (o < c) minsToClose = c - currentMin;
      else minsToClose = currentMin >= o ? (1440 - currentMin) + c : c - currentMin;
      
      nextClosings.push({ ...m, minsToClose, timeStr: m.closeTime });
    } else {
      let minsToOpen;
      if (o < c) minsToOpen = currentMin < o ? o - currentMin : (1440 - currentMin) + o;
      else minsToOpen = o - currentMin; // since closed and cross-day, currentMin must be between c and o
      
      nextOpenings.push({ ...m, minsToOpen, timeStr: m.openTime });
    }
  });

  return {
    openMarkets,
    nextOpenings: nextOpenings.sort((a, b) => a.minsToOpen - b.minsToOpen).slice(0, 3),
    nextClosings: nextClosings.sort((a, b) => a.minsToClose - b.minsToClose).slice(0, 3),
  };
}

export default function GlobalMarketSessions() {
  const [states, setStates] = useState(getMarketStates());

  useEffect(() => {
    // Update every 30 seconds to keep times accurate
    const timer = setInterval(() => setStates(getMarketStates()), 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(1, 1fr)', gap: '16px' }}>
      
      {/* Desktop splits into 3 columns automatically via media query styling if needed, but we can just use inline grid rules for modern standards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        
        {/* Currently Open Block */}
        <div className="holo-panel">
          <div className="panel-header" style={{ borderBottomColor: 'var(--bull-border)' }}>
            <span className="icon-wrap" style={{ color: 'var(--bull)' }}><Power size={13} /></span>
            Currently Open
          </div>
          <div style={{ padding: '8px 0' }}>
            {states.openMarkets.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                All markets are currently closed.
              </div>
            ) : (
              states.openMarkets.map(m => (
                <div key={m.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <div>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{m.name}</span>
                    <div className="holo-text" style={{ fontSize: '10px', marginTop: '2px' }}>{m.region}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--bull)', filter: 'drop-shadow(0 0 3px var(--bull))' }} />
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--bull)', textTransform: 'uppercase' }}>Live</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Next Openings Block */}
        <div className="holo-panel">
          <div className="panel-header" style={{ borderBottomColor: 'rgba(56, 189, 248, 0.3)' }}>
            <span className="icon-wrap" style={{ color: '#38bdf8' }}><PlayCircle size={13} /></span>
            Next Openings
          </div>
          <div style={{ padding: '8px 0' }}>
            {states.nextOpenings.map(m => (
              <div key={m.id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)',
              }}>
                <div>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{m.name}</span>
                  <div className="holo-text" style={{ fontSize: '10px', marginTop: '2px' }}>
                    Closes {formatIST(m.closeTime)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '12px', fontWeight: 500, color: '#38bdf8' }}>
                    Opens {formatIST(m.timeStr)}
                  </div>
                  <div className="holo-text" style={{ fontSize: '10px', opacity: 0.8, color: 'var(--text-secondary)' }}>
                    in {Math.floor(m.minsToOpen / 60)}h {m.minsToOpen % 60}m
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Next Closings Block */}
        <div className="holo-panel">
          <div className="panel-header" style={{ borderBottomColor: 'var(--warn-border)' }}>
            <span className="icon-wrap" style={{ color: 'var(--warn)' }}><Clock size={13} /></span>
            Closing Soon
          </div>
          <div style={{ padding: '8px 0' }}>
            {states.nextClosings.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No markets are currently open.
              </div>
            ) : (
              states.nextClosings.map(m => (
                <div key={m.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <div>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{m.name}</span>
                    <div className="holo-text" style={{ fontSize: '10px', marginTop: '2px' }}>
                      Opened {formatIST(m.openTime)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--warn)' }}>
                      Closes {formatIST(m.timeStr)}
                    </div>
                    <div className="holo-text" style={{ fontSize: '10px', opacity: 0.8, color: m.minsToClose < 60 ? 'var(--bear)' : 'var(--text-secondary)' }}>
                      in {Math.floor(m.minsToClose / 60)}h {m.minsToClose % 60}m
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
