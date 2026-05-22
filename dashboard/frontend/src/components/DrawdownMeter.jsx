import React from 'react';

export default function DrawdownMeter({ status, events }) {
  const drawdown = status?.drawdown_pct ?? 0;
  const limit    = 8;
  const pct      = Math.min(drawdown / limit, 1);

  const barColor =
    drawdown < 3 ? '#48bb78' :
    drawdown < 6 ? '#f6e05e' : '#fc8181';

  // Build a mini equity history from status_update events
  const statusEvents = events
    .filter(e => e.type === 'status_update' && e.equity)
    .slice(0, 30)
    .reverse();

  const trades = events.filter(e => e.type === 'trade_placed');
  const winCount = 0; // would need outcome data — placeholder

  return (
    <div style={styles.container}>
      <div style={styles.title}>PORTFOLIO</div>

      <div style={styles.row}>
        <div style={styles.block}>
          <div style={styles.label}>EQUITY</div>
          <div style={styles.bigValue}>
            €{Number(status?.equity ?? 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
          </div>
        </div>
        <div style={styles.block}>
          <div style={styles.label}>OPEN POSITIONS</div>
          <div style={{ ...styles.bigValue, color: '#63b3ed' }}>{status?.open_positions ?? 0}</div>
        </div>
        <div style={styles.block}>
          <div style={styles.label}>TRADES THIS SESSION</div>
          <div style={{ ...styles.bigValue, color: '#68d391' }}>{trades.length}</div>
        </div>
      </div>

      <div style={styles.meterSection}>
        <div style={styles.meterHeader}>
          <span style={styles.label}>DRAWDOWN</span>
          <span style={{ color: barColor, fontSize: 14, fontWeight: 700 }}>{drawdown.toFixed(2)}%</span>
          <span style={styles.label}>/ {limit}% limit</span>
        </div>
        <div style={styles.meterTrack}>
          <div style={{ ...styles.meterFill, width: `${pct * 100}%`, background: barColor }} />
          {/* Danger zone marker at 8% */}
          <div style={styles.limitLine} title="8% kill switch" />
        </div>
        <div style={styles.meterLabels}>
          <span>0%</span>
          <span style={{ color: '#fc8181' }}>▲ HALT</span>
          <span>{limit}%</span>
        </div>
      </div>

      <div style={styles.circuitSection}>
        <div style={styles.label} style={{ ...styles.label, marginBottom: 6 }}>CIRCUIT BREAKERS</div>
        <div style={styles.cbGrid}>
          {status?.circuit_breakers
            ? Object.entries(status.circuit_breakers).map(([agent, state]) => (
                <CircuitBadge key={agent} agent={agent} state={state} />
              ))
            : <span style={{ color: '#2d3748', fontSize: 11 }}>—</span>
          }
        </div>
      </div>
    </div>
  );
}

function CircuitBadge({ agent, state }) {
  const colors = { closed: '#48bb78', open: '#fc8181', half_open: '#f6e05e' };
  const color  = colors[state?.toLowerCase?.()] || '#718096';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      <span style={{ fontSize: 10, color: '#718096' }}>{agent}</span>
    </div>
  );
}

const styles = {
  container: {
    background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 6,
    padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 14,
  },
  title: { fontSize: 9, color: '#4a5568', letterSpacing: 2, fontWeight: 700 },
  row:   { display: 'flex', gap: 24 },
  block: {},
  label: { fontSize: 9, color: '#4a5568', letterSpacing: 1, marginBottom: 3 },
  bigValue: { fontSize: 20, fontWeight: 700, color: '#e2e8f0', fontVariantNumeric: 'tabular-nums' },

  meterSection: { display: 'flex', flexDirection: 'column', gap: 5 },
  meterHeader:  { display: 'flex', alignItems: 'baseline', gap: 8 },
  meterTrack:   {
    height: 10, background: '#1a2236', borderRadius: 5, position: 'relative', overflow: 'visible',
  },
  meterFill: { height: '100%', borderRadius: 5, transition: 'width 0.8s ease, background 0.5s' },
  limitLine: {
    position: 'absolute', right: 0, top: -3, bottom: -3,
    width: 2, background: '#fc818188', borderRadius: 1,
  },
  meterLabels: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 9, color: '#4a5568',
  },

  circuitSection: {},
  cbGrid: { display: 'flex', flexWrap: 'wrap', gap: '6px 16px' },
};
