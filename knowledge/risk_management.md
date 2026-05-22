# Risk Management Rules

## The Three Laws of Trading Survival
1. Never risk more than 2% of total portfolio on a single trade.
2. Never let total open risk exceed 20% of portfolio at any time.
3. Never add to a losing position. Cut losers; let winners run.

Violating any of these three rules is the primary cause of account blowups. These are not guidelines — they are hard constraints enforced by ZEUS at the portfolio level.

## Drawdown Management
Maximum drawdown limit: 8%. If total portfolio drops 8% from peak equity, ZEUS halts all trading immediately.

Why 8%: at 2% risk per trade, an 8% drawdown means roughly 4 consecutive maximum losses — a statistically rare but possible bad streak. At this point, the system needs human review before resuming.

Drawdown levels and actions:
- 0-4%: normal operation, no change
- 4-6%: reduce all new position sizes by 25%
- 6-8%: reduce all new position sizes by 50%, only CRITICAL severity signals
- 8%+: HALT. No new trades. Alert sent. Manual resume required.

## Correlation Risk
Do not hold 3+ positions in the same sector simultaneously. If AAPL, MSFT, and NVDA are all long at the same time, a tech sector sell-off hits all three. This is a 6% drawdown from a single market event.

ZEUS should check: if the new signal's ticker is in the same sector as 2+ existing open positions, reduce position size by 50% or skip.

## Stop-Loss Placement
Default: 3% from entry. This represents 0.06% of total portfolio per trade (3% stop × 2% position size).

Volatility-adjusted stops:
- VIX < 15: tighten stop to 2% (market is calm, moves are predictable)
- VIX 15-25: standard 3% stop
- VIX 25-35: widen stop to 4% (avoid being stopped out by normal volatility)
- VIX > 35: do not trade (all signals suppressed)

Never use mental stops. The stop-loss bracket order is placed at execution — it is not optional.

## Take-Profit Strategy
Default: 6% from entry (2:1 R/R). This is a hard bracket order placed at execution.

Trailing stops (future enhancement): once a position reaches +3% (1:1), move stop to break-even. This creates a risk-free trade. ZEUS v2 should implement this.

Partial profit-taking: at +4% profit, close 50% of position and let the remainder run to the 6% target. This locks in profit while preserving upside. Implementation: Phase 2.

## Time-Based Exits
If a trade has not moved significantly within 3 trading days, re-evaluate:
- Is the thesis still valid? Check Hermes for updates on the same supplier/event.
- If no new confirmation signal: close the position. Time is a risk factor.
- Holding a flat trade occupies capital that could be deployed on new signals.

## Leverage
ZEUS does not use leverage in Phase 1. All trades are fully funded from portfolio equity.
Leverage may be considered in Phase 3 only for the highest-confidence signals with proven track record.

## Currency Risk (German/EU Context)
IBKR accounts in Germany are denominated in EUR. US stocks are in USD.
EUR/USD fluctuations create currency risk on all US positions.
Rule: for positions held > 5 days, consider whether EUR/USD trend is a tailwind or headwind.
If EUR is strengthening (bad for USD-denominated assets), favour EU-listed stocks over US.
