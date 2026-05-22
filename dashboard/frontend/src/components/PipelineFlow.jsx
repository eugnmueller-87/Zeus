import React, { useState, useEffect } from 'react';

const AGENTS = [
  { id: 'icarus',  label: 'ICARUS',  sub: 'Signal Watcher',   icon: '🦅' },
  { id: 'hades',   label: 'HADES',   sub: 'Compliance Filter', icon: '⚖️' },
  { id: 'artemis', label: 'ARTEMIS', sub: 'Macro Context',     icon: '🌙' },
  { id: 'pythia',  label: 'PYTHIA',  sub: 'Pattern & Sizing',  icon: '🔮' },
  { id: 'zeus',    label: 'ZEUS',    sub: 'LLM Reasoning',     icon: '⚡' },
  { id: 'ares',    label: 'ARES',    sub: 'Trade Execution',   icon: '⚔️' },
  { id: 'argus',   label: 'ARGUS',   sub: 'Portfolio Monitor', icon: '👁️' },
];

const EVENT_TO_STAGE = {
  icarus_signal:    'icarus',
  signal_killed:    null,
  trade_placed:     'ares',
  pipeline_start:   null,
  pipeline_complete: null,
};

export default function PipelineFlow({ events, agents }) {
  const [activeStage, setActiveStage] = useState(null);
  const [killStage, setKillStage]     = useState(null);

  useEffect(() => {
    if (!events.length) return;
    const latest = events[0];
    if (latest.type === 'icarus_signal') {
      setActiveStage('icarus'); setKillStage(null);
    } else if (latest.type === 'signal_killed') {
      setActiveStage(null); setKillStage(latest.stage?.replace('trend', 'artemis').replace('pattern', 'pythia'));
    } else if (latest.type === 'trade_placed') {
      setActiveStage('ares'); setKillStage(null);
    } else if (latest.type === 'pipeline_complete') {
      setTimeout(() => setActiveStage(null), 2000);
    }
  }, [events]);

  // Map watchdog reports to per-agent status
  const agentStatus = {};
  agents.forEach(a => { agentStatus[a.name] = a.status; });

  const getNodeStyle = (agentId) => {
    const wsStatus = agentStatus[agentId];
    if (killStage === agentId) return { ...styles.node, ...styles.nodeKill };
    if (activeStage === agentId) return { ...styles.node, ...styles.nodeActive };
    if (wsStatus === 'healthy') return { ...styles.node, ...styles.nodeHealthy };
    if (wsStatus === 'failed')  return { ...styles.node, ...styles.nodeFailed };
    return styles.node;
  };

  return (
    <div style={styles.container}>
      <div style={styles.title}>PIPELINE</div>
      {AGENTS.map((agent, i) => (
        <React.Fragment key={agent.id}>
          <div style={getNodeStyle(agent.id)}>
            <span style={styles.icon}>{agent.icon}</span>
            <div>
              <div style={styles.agentName}>{agent.label}</div>
              <div style={styles.agentSub}>{agent.sub}</div>
            </div>
            <StatusDot status={agentStatus[agent.id] || 'unknown'} />
          </div>
          {i < AGENTS.length - 1 && (
            <div style={styles.arrow}>↓</div>
          )}
        </React.Fragment>
      ))}

      {/* Apollo separate — research cycle, not in signal path */}
      <div style={styles.apolloDivider} />
      <div style={{ ...styles.node, ...styles.nodeApollo }}>
        <span style={styles.icon}>📚</span>
        <div>
          <div style={styles.agentName}>APOLLO</div>
          <div style={styles.agentSub}>Research (daily)</div>
        </div>
        <StatusDot status={agentStatus['apollo'] || 'unknown'} />
      </div>
    </div>
  );
}

function StatusDot({ status }) {
  const colors = { healthy: '#48bb78', failed: '#fc8181', degraded: '#f6e05e', unknown: '#4a5568' };
  return (
    <div style={{ width: 8, height: 8, borderRadius: '50%', background: colors[status] || colors.unknown, marginLeft: 'auto', flexShrink: 0 }} />
  );
}

const styles = {
  container: {
    background: '#0d1117', border: '1px solid #1e2d40',
    borderRadius: 6, padding: '14px 12px',
    display: 'flex', flexDirection: 'column', gap: 0, minWidth: 200,
  },
  title: { fontSize: 9, color: '#4a5568', letterSpacing: 2, marginBottom: 12, fontWeight: 700 },
  node: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '7px 10px', borderRadius: 4, border: '1px solid #1e2d40',
    background: '#111827', cursor: 'default',
    transition: 'all 0.3s ease',
  },
  nodeActive: { borderColor: '#63b3ed', background: '#1a2d4a', boxShadow: '0 0 8px #63b3ed44' },
  nodeHealthy: { borderColor: '#1a3a28' },
  nodeFailed:  { borderColor: '#742a2a', background: '#1a0f0f' },
  nodeKill:    { borderColor: '#fc8181', background: '#2d1010', boxShadow: '0 0 8px #fc818144' },
  nodeApollo:  { borderColor: '#44337a', background: '#1a1030', marginTop: 4 },
  icon:        { fontSize: 14, flexShrink: 0 },
  agentName:   { fontSize: 11, fontWeight: 700, color: '#e2e8f0', letterSpacing: 0.5 },
  agentSub:    { fontSize: 9, color: '#4a5568', marginTop: 1 },
  arrow:       { textAlign: 'center', color: '#2d3748', fontSize: 12, lineHeight: '10px', margin: '1px 0' },
  apolloDivider: { borderTop: '1px dashed #1e2d40', margin: '10px 0 6px' },
};
