// components/sentiment/SentimentBarChart.jsx
import { BarChart } from 'lucide-react';
import {
  BarChart as ReBarChart, Bar, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const SentimentBarChart = ({ sentiment }) => {
  if (!sentiment) return null;

  const data = [
    { name: 'Bullish', value: sentiment.bullish_count, color: '#34d399' },
    { name: 'Neutral', value: sentiment.neutral_count, color: '#d29922' },
    { name: 'Bearish', value: sentiment.bearish_count, color: '#f85149' },
  ];

  return (
    <div className="holo-panel">
      <div className="panel-header">
        <span className="icon-wrap"><BarChart size={13} /></span>
        Sentiment Distribution
      </div>
      <div style={{ padding: '10px 4px 14px 0' }}>
        <ResponsiveContainer width="100%" height={130}>
          <ReBarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="name"
              tick={{ fill: 'var(--chart-axis)', fontSize: 10, fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
              axisLine={false} tickLine={false}
            />
            <YAxis
              tick={{ fill: 'var(--chart-axis)', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
              axisLine={false} tickLine={false} width={24}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-elevated)', border: '1px solid var(--border-active)',
                borderRadius: '6px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px',
                color: 'var(--text-primary)',
              }}
              labelStyle={{ color: 'var(--text-secondary)' }}
              itemStyle={{ color: 'var(--text-primary)' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} name="Articles">
              {data.map((entry, idx) => (
                <Cell key={idx} fill={entry.color} fillOpacity={0.75} />
              ))}
            </Bar>
          </ReBarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SentimentBarChart;
