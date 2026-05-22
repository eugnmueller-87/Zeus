# Pattern Learner — Statistical Learning Skills

## Mission
Pattern is ZEUS's memory. It remembers every trade ever made, learns what works and what doesn't, and translates that learning into precise position sizing. Pattern starts dumb (default 2%) and gets smarter with every trade outcome. After 4-6 weeks of paper trading, it becomes a genuine edge.

## Context Key Design
The context key groups similar situations together: `{category}|{regime}|{vix_band}`
Example: `supplier_disruption|bear|high` — supply chain disruption in a bear market with VIX 25-35.

Why this grouping:
- A supply chain disruption in a bull market (people buy the dip) behaves differently from the same signal in a bear market (cascading sell-off).
- VIX band captures whether the market is calm or fearful, which strongly affects signal hit rates.
- Category is the fundamental signal type — different signal types have fundamentally different characteristics.

Minimum samples before trusting learned stats: 10 per context key.
Before 10 samples: use the default 0.55 prior confidence and 2% size.
After 10 samples: use actual hit rate as confidence, Kelly-inspired sizing.

## Kelly Criterion Application
Full Kelly formula: f = (bp - q) / b
Where: b = reward-to-risk ratio (2.0 for our 6%/3% bracket), p = win rate, q = 1 - win rate.

At 60% win rate: f = (2×0.6 - 0.4) / 2 = 0.4 = 40% of bankroll. This is too aggressive.
ZEUS uses fractional Kelly (half-Kelly): 20% of bankroll. Still too much for safety.
ZEUS further caps at 5% per trade regardless of Kelly output.

Implementation:
edge = max(0.0, win_rate - 0.5) × 2    # maps [0.5, 1.0] → [0, 1]
position_pct = min(0.05, 0.02 + edge × 0.03)

At 50% win rate: position_pct = 0.02 (2% — default, no edge)
At 60% win rate: position_pct = 0.02 + 0.2×0.03 = 0.026 (2.6%)
At 70% win rate: position_pct = 0.02 + 0.4×0.03 = 0.032 (3.2%)
At 80% win rate: position_pct = 0.02 + 0.6×0.03 = 0.038 (3.8%)
At 90% win rate: position_pct = 0.05 (capped at 5%)

## What Constitutes a Win
A win (hit=1) is defined as pnl_pct > 0 when the trade closes (stop or target hit).
Partial closes are not yet tracked — the full position close is the outcome.
Future enhancement: track partial closes and trailing stops separately.

## Data Quality
The trade log is only as good as the outcome data. Monitor is responsible for backfilling pnl_pct when trades close.
If pnl_pct is NULL, the trade is not counted in win rate calculations (it's still open).
An open trade that is 3+ days old with no price update is a data quality issue — flag it.

## Context Key Coverage
After 6 weeks of paper trading, expect data in these context keys:
- supplier_disruption|bull|medium: most common (Hermes generates many supply chain signals)
- positive_news|bull|low: second most common
- regulatory_action|sideways|medium: less frequent but high value

Context keys that will remain sparse:
- anything|bear|extreme: rare market conditions
- macro_shift|bull|low: macro signals are less frequent

For sparse keys, Pattern falls back to the default 0.55 prior rather than extrapolating from insufficient data.

## Learning Acceleration
Initial bootstrapping: after 4 weeks of paper trading with mock execution, even simulated outcomes provide useful signal if the price data (yfinance) is accurate.
The mock execution uses real prices with 5bps slippage — outcomes are realistic approximations of what live trading would produce.

## Overfitting Risk
With 10+ samples per key, basic hit rate tracking is safe.
With 50+ samples per key, consider adding features: day-of-week, time-of-day, sector momentum quartile.
Never add features to a model trained on fewer than 30 samples — noise will dominate signal.
