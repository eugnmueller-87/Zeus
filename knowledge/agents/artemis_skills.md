# Trend Analyzer — Macro Intelligence Skills

## Mission
Trend's job is to prevent ZEUS from making technically valid trades in the wrong macro environment. A supply chain disruption is a great short signal — unless the entire market is already in a panic sell-off and everything is already priced in. Context is everything.

## VIX Interpretation
VIX (CBOE Volatility Index) measures the 30-day implied volatility of the S&P 500. It is the single most important macro indicator for trade sizing and signal suppression.

VIX < 12: Complacency. Market is extremely calm. Often precedes volatility spikes. Good time to be positioned but watch for sudden reversals.
VIX 12-20: Normal market. Healthy volatility. All signals valid.
VIX 20-25: Elevated concern. Reduce size by 25%. Markets are nervous — moves are larger.
VIX 25-35: High fear. Reduce size by 50%. Only CRITICAL signals. Stops wider.
VIX > 35: Extreme fear / crisis. ALL SIGNALS SUPPRESSED. Cash is the position.

The VIX is mean-reverting. Spikes above 35 almost always retrace. Do not buy VIX spikes; wait for VIX to start declining before re-entering positions.

## Market Regime Classification
Bull market (S&P 500 +2% over 1 month, VIX < 20):
- Positive bias. Trend-following works. Buy signals have high hit rates.
- Supply chain disruptions: buyable dips if temporary.
- Strategy: go with the trend, use upper range of position sizing.

Bear market (S&P 500 -3% over 1 month OR VIX > 35):
- Negative bias. Counter-trend rallies are sold. Short signals are strong.
- Suppress all positive news signals — the market will fade them.
- Strategy: favour shorts, tight stops, lower size, preserve capital.

Sideways market (VIX 15-25, S&P flat ±2%):
- Range-bound. Mean reversion works better than trend following.
- Both directions viable at range extremes.
- Strategy: only high-conviction signals, default sizing.

## Sector Momentum Analysis
Sector ETF 1-month returns provide crucial context.

Tailwind: signal direction aligns with sector momentum → confidence +15%
Headwind: signal direction opposes sector momentum → require confidence > 0.70, reduce size 30%

Example: NVIDIA supply chain disruption (short tech) when XLK is down -5% for the month = strong tailwind. High conviction.
Example: NVIDIA positive news (long tech) when XLK is down -8% = strong headwind. Skip unless confidence > 0.75.

Key sectors to monitor:
- XLK (Technology): most important for ZEUS — Hermes heavily monitors tech suppliers
- XLE (Energy): commodity price sensitive, geopolitically driven
- XLF (Financials): rate sensitive
- XLV (Healthcare): defensive, low correlation
- XLI (Industrials): supply chain heavy, critical for German industrial signals
- XLB (Materials): commodity prices, relevant for raw material supply chain signals

## Caching Strategy
Macro data is fetched from yfinance. Cache for 15 minutes (900 seconds) to avoid excessive API calls.
During high-volatility periods (VIX > 30), reduce cache TTL to 5 minutes — regime can shift quickly.
If yfinance fails, do NOT use stale data older than 30 minutes. Fall back to neutral regime (SIDEWAYS, VIX=20).

## Leading vs Lagging Indicators
VIX is a leading indicator — it rises before markets fall.
S&P 500 return is a lagging indicator — it confirms what has happened.
Use VIX as the primary trigger for suppression decisions.
Use S&P return to confirm the regime (bull/bear/sideways).

## European Market Context
XETRA (German stock exchange) opens before US markets. European signals may have already moved European stocks before US markets open.
When analyzing sector momentum, also consider DAX performance (not just SPY) for German industrial signals.
Future enhancement: add DAX (^GDAXI) and EURO STOXX 50 (^STOXX50E) to the macro context fetch.
