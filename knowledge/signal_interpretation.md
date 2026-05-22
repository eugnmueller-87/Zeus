# Signal Interpretation Guide — From Hermes Event to Trade Decision

## Supply Chain Disruption Signals
Source: Hermes SUPPLY_CHAIN type. Examples: factory fire, port strike, raw material shortage, key supplier bankruptcy.

Primary implication: downstream manufacturers face cost increases and production delays.
Secondary implication: the disrupted supplier's stock often recovers after panic; the downstream buyers face sustained impact.

Trade logic:
- SHORT the downstream buyer (e.g. TSMC disruption → SHORT fabless chip designers who depend on TSMC)
- The disrupted company itself: often a buy-the-dip if disruption is temporary (fire, weather) but a sell if structural (bankruptcy, regulatory ban)
- Timing: act within 2 hours of signal. After 4 hours, market has priced most of it.
- Duration: hold 2-5 days. Supply chain disruptions play out over days, not hours.

Confidence modifier: HIGH if disruption affects top-3 global supplier. MEDIUM if regional. LOW if single-factory.

## Positive News Signals
Source: Hermes POSITIVE_NEWS (partnerships, product launches, funding rounds, acquisitions).

Primary implication: bullish for the named company. Market often overreacts on announcement day then consolidates.

Trade logic:
- LONG on the named company if signal breaks before market open or in pre-market.
- If signal breaks mid-session after stock has already moved 5%+, skip — edge is gone.
- Partnership signals: long both companies if both are liquid.
- Funding rounds (private companies): check if any publicly listed competitors benefit or are threatened.

Confidence modifier: HIGH if tier-1 partner named. MEDIUM if general announcement. LOW if press release only.

## Earnings Surprise Signals
Source: Hermes EARNINGS type. Beat or miss vs analyst consensus.

Primary implication: immediate 3-15% price move in the direction of the surprise. The size of the move depends on how much the market expected it (implied vol before earnings).

Trade logic:
- Earnings signals are high-risk/high-reward. The move happens in minutes.
- Post-earnings drift: after a beat, stocks often continue trending up for 1-3 days as analysts revise targets. This is the tradeable window.
- After a miss, stocks often rebound partially within 24-48h if the underlying business is healthy. "Buy the guidance, not the results."
- ZEUS should enter 30-60 minutes after earnings release, not immediately, to avoid the initial whipsaw.

Confidence modifier: HIGH if surprise > 15% vs consensus. MEDIUM if 5-15%. LOW if < 5%.

## Regulatory Action Signals
Source: Hermes REGULATORY type. SEC investigation, antitrust action, FDA rejection, BAFIN fine, LkSG violation.

Primary implication: immediate negative for the targeted company. Duration depends on severity.

Trade logic:
- SHORT the targeted company immediately on regulatory signal.
- Investigation ≠ conviction. Investigations can drag for years. Take profit within 1-3 days.
- Fines that are quantifiable and smaller than feared → buy-the-dip after initial sell-off.
- Antitrust action threatening core business → sustained short.
- European regulatory action (BAFIN, EU Commission) often has longer timeframes than US SEC.

Confidence modifier: HIGH if criminal referral or trading halt. MEDIUM if formal investigation. LOW if inquiry or subpoena only.

## Pricing Change Signals
Source: Hermes PRICING_CHANGE type. Supplier raising prices, commodity spikes.

Primary implication: margin compression for buyers, margin expansion for the price-raiser.

Trade logic:
- SHORT the companies that buy from the price-raising supplier (margin squeeze).
- LONG the supplier if they are publicly listed (margin expansion).
- Check: can buyers pass on the cost? If yes, impact is muted. If no, SHORT is stronger.
- Energy price spikes: short airlines, logistics, consumer discretionary. Long energy producers.

## Acquisition Signals
Source: Hermes ACQUISITION type.

Trade logic:
- Target company: buy immediately if the deal price is not yet reflected in the stock (typical in leaks/rumours).
- Acquirer company: often sells off on announcement (dilution, premium paid). Short-term short opportunity.
- Deal spread trading: long target at current price, short acquirer. Captures the spread until deal closes.
- Risk: deal falls apart → target stock crashes. Only trade acquisition signals when regulatory approval is likely.
