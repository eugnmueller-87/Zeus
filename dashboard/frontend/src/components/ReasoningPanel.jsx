import React, { useState, useEffect } from 'react';

export default function ReasoningPanel({ events }) {
  const [displayed, setDisplayed] = useState('');
  const [fullText, setFullText]   = useState('');
  const [charIdx, setCharIdx]     = useState(0);

  // Grab the latest ZEUS reasoning from the most recent trade or kill
  const latestWithReason = events.find(
    e => (e.type === 'trade_placed' || e.type === 'signal_killed') && e.reasoning
  );

  useEffect(() => {
    if (!latestWithReason?.reasoning) return;
    const text = latestWithReason.reasoning;
    if (text === fullText) return;
    setFullText(text);
    setDisplayed('');
    setCharIdx(0);
  }, [latestWithReason?.reasoning]);

  useEffect(() => {
    if (charIdx >= fullText.length) return;
    const timer = setTimeout(() => {
      setDisplayed(fullText.slice(0, charIdx + 1));
      setCharIdx(c => c + 1);
    }, 18);
    return () => clearTimeout(timer);
  }, [charIdx, fullText]);

  const latestTrade = events.find(e => e.type === 'trade_placed');
  const latestKill  = events.find(e => e.type === 'signal_killed');
  const latestSignal = events.find(e => e.type === 'icarus_signal');

  return (
    <div style={styles.container}>
      <div style={styles.title}>⚡ ZEUS REASONING</div>

      {latestSignal && (
        <div style={styles.signalBox}>
          <div style={styles.signalLabel}>LATEST SIGNAL</div>
          <div style={styles.signalText}>{latestSignal.supplier}  ·  {latestSignal.category}  ·  {latestSignal.severity}</div>
          <div style={styles.headline}>{latestSignal.headline}</div>
          {latestSignal.tickers?.length > 0 && (
            <div style={styles.tickers}>
              {latestSignal.tickers.map(t => (
                <span key={t} style={styles.ticker}>{t}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={styles.reasoningBox}>
        <div style={styles.signalLabel}>DECISION REASONING</div>
        {displayed
          ? <div style={styles.reasoning}>{displayed}<span style={styles.cursor}>▋</span></div>
          : <div style={styles.empty}>No reasoning yet. Run a pipeline cycle.</div>
        }
      </div>

      <div style={styles.decisionRow}>
        {latestTrade && (
          <div style={{ ...styles.decision, borderColor: '#48bb78', background: '#1a3a28' }}>
            <span style={{ color: '#48bb78', fontWeight: 700 }}>✓ APPROVED</span>
            <span style={styles.decisionDetail}>
              {latestTrade.side?.toUpperCase()} {latestTrade.symbol}  @  €{latestTrade.fill ?? '?'}
            </span>
          </div>
        )}
        {latestKill && (
          <div style={{ ...styles.decision, borderColor: '#fc8181', background: '#2d1010' }}>
            <span style={{ color: '#fc8181', fontWeight: 700 }}>✗ REJECTED</span>
            <span style={styles.decisionDetail}>{latestKill.stage?.toUpperCase()} — {latestKill.reason}</span>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 6,
    padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 12,
  },
  title:       { fontSize: 9, color: '#4a5568', letterSpacing: 2, fontWeight: 700 },
  signalBox:   { background: '#111827', border: '1px solid #1e2d40', borderRadius: 4, padding: '8px 10px' },
  signalLabel: { fontSize: 9, color: '#4a5568', letterSpacing: 1, marginBottom: 4 },
  signalText:  { fontSize: 10, color: '#63b3ed', marginBottom: 4 },
  headline:    { fontSize: 11, color: '#a0aec0', lineHeight: 1.4 },
  tickers:     { display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' },
  ticker:      {
    fontSize: 10, padding: '1px 6px', borderRadius: 3,
    background: '#1a2d4a', border: '1px solid #2d4a6e', color: '#63b3ed',
  },
  reasoningBox: { background: '#111827', border: '1px solid #1e2d40', borderRadius: 4, padding: '8px 10px', minHeight: 80 },
  reasoning:    { fontSize: 11, color: '#68d391', lineHeight: 1.6 },
  cursor:       { animation: 'blink 1s step-end infinite', color: '#48bb78' },
  empty:        { color: '#2d3748', fontSize: 11, padding: '8px 0' },
  decisionRow:  { display: 'flex', flexDirection: 'column', gap: 6 },
  decision:     {
    display: 'flex', flexDirection: 'column', gap: 3,
    padding: '6px 10px', borderRadius: 4, border: '1px solid', fontSize: 11,
  },
  decisionDetail: { color: '#a0aec0', fontSize: 10 },
};
