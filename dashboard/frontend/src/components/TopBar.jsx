import React from 'react';

const COLORS = {
  RUNNING: '#48bb78',
  HALTED:  '#fc8181',
  SHUTDOWN: '#718096',
};

export default function TopBar({ status, connected, onRunCycle, onHalt, onResume }) {
  const pipelineStatus = status?.pipeline_status || 'UNKNOWN';
  const dot = connected ? '#48bb78' : '#fc8181';

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <span style={styles.logo}>⚡ PANTHEON OS</span>
        <span style={{ ...styles.badge, background: status?.paper_trading ? '#2d3748' : '#742a2a' }}>
          {status?.paper_trading ? 'PAPER TRADING' : 'LIVE TRADING'}
        </span>
        <span style={{ ...styles.dot, background: dot }} />
        <span style={{ color: dot, fontSize: 11 }}>{connected ? 'CONNECTED' : 'RECONNECTING…'}</span>
      </div>

      <div style={styles.center}>
        <Metric label="EQUITY" value={status ? `€${Number(status.equity || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}` : '—'} />
        <Metric label="DRAWDOWN" value={status ? `${status.drawdown_pct?.toFixed(2)}%` : '—'}
          valueStyle={{ color: (status?.drawdown_pct || 0) > 5 ? '#fc8181' : '#48bb78' }} />
        <Metric label="OPEN POS" value={status?.open_positions ?? '—'} />
        <Metric label="STATUS" value={pipelineStatus}
          valueStyle={{ color: COLORS[pipelineStatus] || '#a0aec0' }} />
      </div>

      <div style={styles.right}>
        <button style={styles.btn} onClick={onRunCycle}>▶ RUN CYCLE</button>
        {pipelineStatus === 'RUNNING'
          ? <button style={{ ...styles.btn, background: '#742a2a', borderColor: '#fc8181' }} onClick={onHalt}>■ HALT</button>
          : <button style={{ ...styles.btn, background: '#1a4731', borderColor: '#48bb78' }} onClick={onResume}>▶ RESUME</button>
        }
      </div>
    </div>
  );
}

function Metric({ label, value, valueStyle = {} }) {
  return (
    <div style={styles.metric}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={{ ...styles.metricValue, ...valueStyle }}>{value}</div>
    </div>
  );
}

const styles = {
  bar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '10px 20px', background: '#0d1117',
    borderBottom: '1px solid #1e2d40',
    position: 'sticky', top: 0, zIndex: 100,
  },
  left:  { display: 'flex', alignItems: 'center', gap: 14 },
  center: { display: 'flex', gap: 28 },
  right: { display: 'flex', gap: 8 },
  logo:  { fontSize: 18, fontWeight: 700, color: '#63b3ed', letterSpacing: 2 },
  badge: { fontSize: 10, padding: '2px 8px', borderRadius: 3, color: '#a0aec0', border: '1px solid #2d3748' },
  dot:   { width: 8, height: 8, borderRadius: '50%', display: 'inline-block' },
  metric: { textAlign: 'center' },
  metricLabel: { fontSize: 9, color: '#4a5568', letterSpacing: 1, marginBottom: 2 },
  metricValue: { fontSize: 15, fontWeight: 700, color: '#e2e8f0' },
  btn: {
    fontSize: 11, padding: '6px 14px', cursor: 'pointer',
    background: '#1a2236', border: '1px solid #2d4a6e',
    color: '#63b3ed', borderRadius: 3, letterSpacing: 1, fontFamily: 'inherit',
  },
};
