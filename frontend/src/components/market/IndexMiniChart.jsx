// components/market/IndexMiniChart.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart as LineIcon } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';
import ChartTooltip from '../ui/ChartTooltip';

const getApiBase = () => {
  const url = import.meta.env.VITE_API_URL;
  if (!url) return '/api';
  const clean = url.endsWith('/') ? url.slice(0, -1) : url;
  return `${clean.startsWith('http') ? '' : 'https://'}${clean}/api`;
};
const API_BASE = getApiBase();

const IndexMiniChart = ({ symbol, name }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/historical/${encodeURIComponent(symbol)}?period=3mo`)
      .then(r => {
        const data = r.data?.data || [];
        const step = Math.max(1, Math.floor(data.length / 60));
        setChartData(data.filter((_, i) => i % step === 0));
      })
      .catch(() => setChartData([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  const isUp = chartData?.length > 1
    ? chartData[chartData.length - 1].close >= chartData[0].close
    : true;
  const lineColor = isUp ? 'var(--bull)' : 'var(--bear)';
  const min = chartData ? Math.min(...chartData.map(d => d.low)) * 0.998 : 0;
  const max = chartData ? Math.max(...chartData.map(d => d.high)) * 1.002 : 0;

  return (
    <div className="holo-panel" style={{ minHeight: '200px' }}>
      <div className="panel-header">
        <span className="icon-wrap"><LineIcon size={13} /></span>
        {name}
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '10px' }}>3M</span>
      </div>
      <div style={{ padding: '8px 4px 12px 0' }}>
        {loading ? (
          <div style={{ height: '130px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="holo-text">Loading…</span>
          </div>
        ) : !chartData?.length ? (
          <div style={{ height: '130px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="holo-text" style={{ color: 'var(--bear)' }}>No data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={130}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`grad-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={isUp ? '#34d399' : '#f85149'} stopOpacity={0.18} />
                  <stop offset="95%" stopColor={isUp ? '#34d399' : '#f85149'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
              <YAxis
                domain={[min, max]}
                tick={{ fill: 'var(--chart-axis)', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
                axisLine={false} tickLine={false} width={55}
                tickFormatter={v => v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(0)}
              />
              <Tooltip content={<ChartTooltip symbol={symbol} />} />
              <Area
                type="monotone" dataKey="close"
                stroke={isUp ? '#34d399' : '#f85149'} strokeWidth={1.5}
                fill={`url(#grad-${symbol})`} dot={false} name="Close"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default IndexMiniChart;
