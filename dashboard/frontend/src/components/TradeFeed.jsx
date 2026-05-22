import React from 'react';

const TYPE_CONFIG = {
  trade_placed:     { label: 'TRADE',    color: '#48bb78', bg: '#1a3a28' },
  signal_killed:    { label: 'KILL',     color: '#fc8181', bg: '#2d1010' },
  icarus_signal:    { label: 'SIGNAL',   color: '#63b3ed', bg: '#0d1f36' },
  pipeline_start:   { label: 'START',    color: '#4a5568', bg: '#0d1117' },
  pipeline_complete:{ label: 'DONE',     color: '#68d391', bg: '#0d1117' },
  halt:             { label: 'HALT',     color: '#fc8181', bg: '#2d1010' },
  resume:           { label: 'RESUME',   color: '#48bb78', bg: '#1a3a28' },
  error:            { label: 'ERROR',    color: '#fc8181', bg: '#2d1010' },
  status_update:    null,
  agent_health:     null,
};

export default function TradeFeed({ events }) {
  const visible = events.filter(e => TYPE_CONFIG[e.type] !== null);

  return (
    <div style={styles.container}>
      <div style={styles.title}>LIVE FEED</div>
      <div style={styles.feed}>
        {visible.length === 0 && (
          <div style={styles.empty}>Waiting for signals…</div>
        )}
        {visible.map(evt => (
          <FeedRow key={evt.id} event={evt} />
        ))}
      </div>
    </div>
  );
}

function FeedRow({ event }) {
  const cfg = TYPE_CONFIG[event.type] || { label: event.type, color: '#718096', bg: '#0d1117' };
  const time = new Date(event.timestamp).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <div style={{ ...styles.row, background: cfg.bg, borderColor: cfg.color + '33' }}>
      <span style={styles.time}>{time}</span>
      <span style={{ ...styles.badge, color: cfg.color, borderColor: cfg.color + '55' }}>{cfg.label}</span>
      <span style={styles.text}>{formatEvent(event)}</span>
    </div>
  );
}

function formatEvent(evt) {
  switch (evt.type) {
    case 'trade_placed':
      return `${evt.side?.toUpperCase()} ${evt.symbol}  €${evt.fill ?? '—'}  [${(evt.confidence * 100)?.toFixed(0)}% conf, ${(evt.size_pct * 100)?.toFixed(1)}%]`;
    case 'signal_killed':
      return `${evt.supplier ?? ''}  killed at ${evt.stage?.toUpperCase()} — ${evt.reason}`;
    case 'icarus_signal':
      return `${evt.supplier}  ${evt.category}  ${evt.severity}  ${evt.headline?.slice(0, 80)}`;
    case 'pipeline_start':
      return 'Pipeline cycle started';
    case 'pipeline_complete':
      return `Done — ${evt.runs} run(s), ${evt.trades} trade(s), ${evt.kills} kill(s)`;
    case 'halt':
    case 'resume':
      return evt.message;
    case 'error':
      return `Error: ${evt.message}`;
    default:
      return JSON.stringify(evt).slice(0, 120);
  }
}

const styles = {
  container: {
    background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 6,
    padding: '14px 12px', display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0,
  },
  title: { fontSize: 9, color: '#4a5568', letterSpacing: 2, marginBottom: 10, fontWeight: 700 },
  feed: { display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto', flex: 1 },
  empty: { color: '#2d3748', fontSize: 12, textAlign: 'center', padding: 24 },
  row: {
    display: 'flex', alignItems: 'baseline', gap: 8,
    padding: '5px 8px', borderRadius: 3, border: '1px solid',
    fontSize: 11, lineHeight: 1.4,
  },
  time:  { color: '#4a5568', flexShrink: 0, fontSize: 10, fontVariantNumeric: 'tabular-nums' },
  badge: { flexShrink: 0, fontSize: 9, border: '1px solid', borderRadius: 2, padding: '0 4px', letterSpacing: 0.5 },
  text:  { color: '#a0aec0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
};
