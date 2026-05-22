import React from 'react';
import useWebSocket from './hooks/useWebSocket';
import TopBar from './components/TopBar';
import PipelineFlow from './components/PipelineFlow';
import TradeFeed from './components/TradeFeed';
import DrawdownMeter from './components/DrawdownMeter';
import ReasoningPanel from './components/ReasoningPanel';
import EquityChart from './components/EquityChart';

export default function App() {
  const { events, status, agents, connected, send } = useWebSocket();

  return (
    <div style={styles.app}>
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
      `}</style>

      <TopBar
        status={status}
        connected={connected}
        onRunCycle={() => send('run_pipeline')}
        onHalt={() => send('halt')}
        onResume={() => send('resume')}
      />

      <div style={styles.body}>
        {/* Left column — pipeline flow */}
        <div style={styles.colLeft}>
          <PipelineFlow events={events} agents={agents} />
        </div>

        {/* Center column — feed + equity */}
        <div style={styles.colCenter}>
          <EquityChart events={events} />
          <TradeFeed events={events} />
        </div>

        {/* Right column — portfolio + reasoning */}
        <div style={styles.colRight}>
          <DrawdownMeter status={status} events={events} />
          <ReasoningPanel events={events} />
        </div>
      </div>

      <div style={styles.footer}>
        PANTHEON OS  ·  Claude Haiku · ChromaDB · IBKR · n8n  ·  {new Date().getFullYear()}
      </div>
    </div>
  );
}

const styles = {
  app: {
    display: 'flex', flexDirection: 'column',
    height: '100vh', overflow: 'hidden',
    background: '#080c16',
  },
  body: {
    display: 'grid',
    gridTemplateColumns: '220px 1fr 320px',
    gap: 10, padding: 10,
    flex: 1, minHeight: 0, overflow: 'hidden',
  },
  colLeft: {
    overflow: 'auto',
  },
  colCenter: {
    display: 'flex', flexDirection: 'column', gap: 10,
    overflow: 'hidden', minHeight: 0,
  },
  colRight: {
    display: 'flex', flexDirection: 'column', gap: 10,
    overflow: 'auto',
  },
  footer: {
    textAlign: 'center', fontSize: 9, color: '#2d3748',
    padding: '6px 0', borderTop: '1px solid #1e2d40', letterSpacing: 2,
  },
};
