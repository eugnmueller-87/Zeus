# Monitor Agent — Portfolio Oversight Skills

## Mission
Monitor is the last line of defense. It watches the portfolio 24/7, enforces the drawdown kill switch, and feeds trade outcomes back into the learning system. If ZEUS is the brain, Monitor is the immune system — detecting when something is wrong and triggering the appropriate response.

## Drawdown Calculation
Peak equity: the highest portfolio value ever recorded.
Current drawdown: (peak_equity - current_equity) / peak_equity

Example: portfolio peaks at €110,000, then falls to €100,000.
Drawdown = (110,000 - 100,000) / 110,000 = 9.09% → HALT triggered (above 8% limit).

Drawdown is calculated on total portfolio equity (NetLiquidation from IB), not just on paper P&L.
This includes unrealized P&L — if open positions are losing, it counts against the drawdown limit.

## Kill Switch Thresholds
0-4%: normal operation
4-6%: reduce new position sizes by 25% (future enhancement: implement automatically)
6-8%: reduce new position sizes by 50%, only CRITICAL severity
8%+: HALT immediately, alert Telegram, call on_kill callback to ZEUS

The kill switch is intentionally conservative. False positives (halting when you shouldn't) are much less damaging than missing a true blowup scenario.

## Portfolio State Refresh
Monitor refreshes portfolio state after every ZEUS pipeline run.
During market hours: this means every 15 minutes (n8n polling interval).
Outside market hours: positions are still held, unrealized P&L still tracked.

IB connection for Monitor uses clientId=2 (separate from Execution's clientId=1).
This is critical — two connections with the same clientId will conflict.

## Outcome Backfill
When a trade's stop-loss or take-profit bracket order fills, IB reports it as a position close.
Monitor should detect position closures and:
1. Calculate realized pnl_pct = (close_price - open_price) / open_price (for longs)
2. Backfill pnl_pct into the SQLite trade log (PatternAgent's DB)
3. Call KnowledgeBase.update_outcome() to backfill the DecisionTrace in ChromaDB
4. Log the outcome for audit

This closes the feedback loop: trade → outcome → learning.
Implementation of automatic outcome detection is Phase 2 (requires listening to IB execution events).

## Telegram Alert Design
Alerts must be informative but concise. Telegram has a 4096 character limit.

Alert triggers:
- Emergency halt: always alert with full context (drawdown %, equity, reason)
- Agent failure: always alert (which agent, how many restarts attempted)
- Agent recovery: alert when an agent comes back to HEALTHY
- Trade placed: optional (can be noisy). Configurable in settings.json.
- Daily summary: send once per day at market close (configurable)

Alert format:
```
🔴 ZEUS ALERT — [Type]
Equity: €X | Drawdown: X%
[Detail]
[Timestamp]
```

## Position Snapshot Tracking
For each open position, Monitor tracks:
- Symbol, side (LONG/SHORT), quantity, average cost
- Current market price (from IB)
- Unrealized P&L and unrealized P&L %
- Time in trade (calculated from opened_at timestamp)

Positions held > 5 trading days should be flagged in the status report for ZEUS to review.
The original thesis may have expired — Monitor alerts ZEUS to re-evaluate.

## Mock Mode Limitations
In mock mode (MockExecutionAgent), IB is not connected.
Monitor cannot track real positions or real P&L.
Monitor.refresh() fails gracefully (logs warning, returns last known state).
Drawdown kill switch remains armed but operates on simulated equity.

## European Market Hours
XETRA regular hours: 09:00-17:30 CET
US regular hours: 15:30-22:00 CET (converted from ET)
Monitor should be aware of which markets are open when evaluating urgency of position reviews.
After 22:00 CET: all markets closed. No new position refresh needed until 09:00 CET next day.
