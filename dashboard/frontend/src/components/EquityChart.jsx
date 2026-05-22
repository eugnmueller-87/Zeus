import React, { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function EquityChart({ events }) {
  const data = useMemo(() => {
    const statusEvents = events
      .filter(e => e.type === 'status_update' && e.equity != null)
      .reverse()
      .slice(-60);

    if (statusEvents.length === 0) return [];

    return statusEvents.map(e => ({
      time:   new Date(e.timestamp).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
      equity: Number(e.equity),
    }));
  }, [events]);

  const startEquity = data[0]?.equity;

  if (data.length < 2) {
    return (
      <div style={styles.container}>
        <div style={styles.title}>EQUITY CURVE</div>
        <div style={styles.empty}>Collecting data… (updates every 5s)</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.title}>EQUITY CURVE</div>
      <ResponsiveContainer width="100%" height={120}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#63b3ed" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#63b3ed" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#4a5568' }} axisLine={false} tickLine={false} />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fontSize: 9, fill: '#4a5568' }}
            axisLine={false} tickLine={false}
            tickFormatter={v => `€${(v/1000).toFixed(0)}k`}
            width={42}
          />
          <Tooltip
            contentStyle={{ background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 4, fontSize: 11 }}
            itemStyle={{ color: '#63b3ed' }}
            formatter={(v) => [`€${Number(v).toLocaleString('de-DE')}`, 'Equity']}
          />
          {startEquity && (
            <ReferenceLine y={startEquity} stroke="#2d3748" strokeDasharray="3 3" />
          )}
          <Area
            type="monotone" dataKey="equity"
            stroke="#63b3ed" strokeWidth={2}
            fill="url(#equityGrad)"
            dot={false} activeDot={{ r: 3, fill: '#63b3ed' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  container: {
    background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 6,
    padding: '14px 12px',
  },
  title: { fontSize: 9, color: '#4a5568', letterSpacing: 2, marginBottom: 10, fontWeight: 700 },
  empty: { color: '#2d3748', fontSize: 11, textAlign: 'center', padding: 28 },
};
