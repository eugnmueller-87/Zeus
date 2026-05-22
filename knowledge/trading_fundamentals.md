# Trading Fundamentals

## Price Action Basics
Price moves in trends, ranges, and reversals. The primary job of a trading system is to identify which state the market is in and act accordingly. Trading with the trend dramatically improves win rates. Counter-trend trades require much higher conviction and tighter risk management.

Key principle: the trend is your friend until it ends. Do not fight momentum. A signal that confirms the existing trend is worth more than one that contradicts it.

## Risk-to-Reward (R/R)
Never take a trade with less than 1.5:1 reward-to-risk. ZEUS defaults to 2:1 (6% take-profit, 3% stop-loss). This means even a 40% win rate produces net profit over time.

Formula: Expected Value = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
At 2:1 R/R and 50% win rate: EV = (0.5 × 2) - (0.5 × 1) = +0.5 per unit risked. Positive.
At 2:1 R/R and 40% win rate: EV = (0.4 × 2) - (0.6 × 1) = +0.2. Still positive.
At 1:1 R/R and 50% win rate: EV = 0. Break even before commissions. Never acceptable.

## Position Sizing
The single biggest determinant of long-term survival is position sizing. Oversizing kills accounts that would otherwise be profitable.

Kelly Criterion: f = (bp - q) / b where b = odds, p = win probability, q = 1-p.
Use half-Kelly in practice. Full Kelly is mathematically optimal but psychologically brutal.

ZEUS default: 2% per trade. Max 5% on highest-confidence signals. Never exceed 5% on a single position.

With 10 open positions at 2% each, total exposure is 20% of portfolio. This is healthy diversification.

## Entry Timing
Enter on confirmation, not anticipation. A supply chain disruption signal is only actionable once the market has not yet priced it in. Check: has the stock already moved 5%+ on this news? If yes, the edge is gone.

Best entry: first 30-90 minutes after news breaks, before institutional desks fully react.
Worst entry: chasing after a 10%+ gap up or gap down — you are buying someone else's exit.

## Stop-Loss Discipline
A stop-loss is not optional. It is the definition of your maximum acceptable loss per trade. ZEUS sets stops at 3% below entry for longs, 3% above for shorts.

Never move a stop-loss further away from entry to "give it more room." This destroys your R/R and is the most common retail trader mistake. If the thesis is wrong, get out.

## Market Hours (European Context)
XETRA opens 09:00 CET. US pre-market begins 15:00 CET. US regular session 15:30–22:00 CET.
Most volume and cleanest price action occurs in the first 90 minutes and last 60 minutes of each session.
Avoid trading in the 12:00–14:00 CET window (low liquidity, erratic moves).
