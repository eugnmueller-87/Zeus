# Icarus — Signal Intelligence Skills

## Mission
Icarus is the eyes of ZEUS. Its job is to extract the most tradeable, time-sensitive signals from the Hermes intelligence stream and discard noise. A missed real signal is a missed opportunity. A false positive wastes the entire pipeline's resources and risks capital.

## Signal Triage — What Matters
Priority 1 — CRITICAL signals (Hermes urgency=HIGH + is_significant=True):
These must never be skipped. They represent confirmed, material events that will move prices.
Examples: a top-10 global supplier halting production, a major regulatory ban, an unexpected bankruptcy.

Priority 2 — Supply chain and regulatory signals:
These have the clearest directional implication and are ZEUS's primary edge. Prioritise these.

Priority 3 — Earnings surprises:
High impact but binary. Flag the signal but note that ZEUS should wait 30-60 minutes after release.

De-prioritise:
- RESEARCH_PAPER type: rarely moves markets in the short term
- ACQUISITION rumours without official confirmation: very noisy
- Signals older than 4 hours: the edge is likely gone

## Understanding Hermes Signal Quality
Hermes crawls 590+ suppliers and classifies signals using Claude Haiku. The classification is reliable but not perfect.
Cross-check: if a signal's headline contradicts its signal_type, trust the headline over the type.
Example: headline says "NVIDIA reports record revenue" but signal_type = SUPPLY_CHAIN → override to EARNINGS_SURPRISE.

## Ticker Extraction Quality
The supplier-to-ticker mapping is static. Gaps will exist for:
- Smaller European suppliers not in the map
- Subsidiaries (e.g. "Infineon Technologies" maps to IFX on XETRA, not a US ticker)
- Conglomerates where the affected division is not separately listed

When a ticker cannot be mapped, pass the signal to ZEUS anyway with an empty tickers list.
ZEUS's LLM reasoning step can often identify the relevant ticker from the supplier name and headline.

## Deduplication
Hermes assigns stable MD5 IDs to each item. The seen-set prevents duplicate processing across poll cycles.
Edge case: Hermes may re-classify the same event as a new signal type if new information arrives.
Rule: if the same headline appears with a different signal_type within 6 hours, process it — the reclassification itself is informative.

## Timing Intelligence
Signals published before market open (before 09:00 CET for XETRA, before 15:30 CET for US) have the highest value — the market has not yet reacted.
Signals published mid-session (09:00-15:00 CET) have moderate value — European markets are live.
Signals published after US close (after 22:00 CET) have high next-day value — flag for the next morning's pipeline run.
Include published_at timestamp prominently in the signal so ZEUS can factor timing into its reasoning.

## Feed Health Monitoring
If Hermes /briefing returns 0 signals for 3 consecutive cycles, this is likely a Hermes outage, not a quiet market.
In this case: health() should return DEGRADED, not HEALTHY.
Log the anomaly so the Watchdog can alert.
