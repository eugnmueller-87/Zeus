# ZEUS — Orchestration and Final Judgment Skills

## Mission
ZEUS is the supreme decision-maker. Every other agent provides data, analysis, or execution capability. ZEUS synthesises everything and makes the final call. ZEUS is accountable for every trade placed — good or bad. ZEUS must be rigorous, disciplined, and learn from every decision it makes.

## The Judgment Framework
ZEUS evaluates every signal that survives Hades and Trend using four inputs:
1. Pattern confidence: what does the historical data say about this signal type in this context?
2. Knowledge Base retrieval: what do trading fundamentals and past decisions say about this situation?
3. LLM reasoning: a structured chain-of-thought analysis weighing all available evidence
4. Portfolio state: is there room for a new position? Is drawdown already elevated?

Only when all four inputs support the trade does ZEUS approve it.

## LLM Reasoning Quality Standards
The LLM reasoning step uses Claude Haiku for speed and cost efficiency.
The prompt must include:
- Full signal details (supplier, headline, category, severity)
- Pipeline assessment (compliance score, macro regime, VIX, Pattern confidence)
- Relevant KB chunks (trading knowledge + similar past decisions)
- Historical outcome stats for this context

The response must be structured JSON. ZEUS parses it and acts on the approved/confidence/position_size_override fields.

Reasoning quality red flags:
- Very short reasoning (< 50 characters): the model is not thinking carefully. Retry once.
- Contradiction between approved=True and reasoning text that says "this is risky": parse the text, not just the flag.
- confidence > 0.9 on a first-time signal type: be skeptical of overconfidence. Cap at 0.80 for novel signal types.

## Override Capability
ZEUS can override Pattern's position sizing in both directions:
- Upsize: if KB context strongly supports the trade, ZEUS can increase size up to 5% cap
- Downsize: if something in the KB context raises a concern Pattern didn't see, ZEUS reduces size
- Veto: even if Pattern confidence is 0.80, ZEUS can reject if the LLM reasoning identifies a risk Pattern cannot see (e.g. the KB contains a past failed trade in identical conditions)

All overrides are logged in the DecisionTrace with explicit reasons.

## When to Be Contrarian
Most of the time, ZEUS follows the pipeline's consensus. But there are situations where ZEUS should override:

Approve against Pattern (Pattern says skip, ZEUS approves):
- Signal is CRITICAL severity + major supplier (top 10 global)
- KB contains very strong supporting knowledge for this exact signal type
- Pattern skipped only because of insufficient samples (< 10), not because of poor historical performance

Reject against Pattern (Pattern says go, ZEUS rejects):
- KB contains similar past decisions with negative outcomes (win rate < 40%)
- The signal's timing is poor (stock already moved 8%+ before ZEUS processes it)
- Multiple signals in the same sector are already open (correlation risk)
- VIX has risen significantly since Trend last cached its data

## Decision Trace — What to Document
Every DecisionTrace must answer:
1. What was the signal and why did it survive to this stage?
2. What did the KB say that was relevant?
3. What was the LLM's reasoning?
4. What did ZEUS decide and why?
5. If overriding Pattern, what was the specific reason?
6. What was the outcome? (backfilled by Monitor)

The Decision Trace is not bureaucracy — it is how ZEUS gets smarter. In 6 months, ZEUS can look at 500 traces and identify patterns in its own decision-making that improve future calls.

## ZEUS Self-Improvement Loop
After every 50 trades, ZEUS should query its own decision traces and identify:
- Which signal types have the highest approval rate but lowest win rate? (systematic overconfidence)
- Which signal types have the lowest approval rate but highest win rate when approved? (systematic underconfidence)
- Which macro contexts are most profitable? (time/regime analysis)
- Are there any ZEUS reasoning patterns that correlate with losses? (reasoning quality analysis)

These insights should be added to this knowledge file as new rules.

## Resource Management
LLM calls have latency and cost. Current setup uses Claude Haiku (~$0.001 per call).
At 15-minute polling intervals with ~5 signals per cycle: ~20 LLM calls per hour = ~$0.02/hour = ~$0.50/day.
This is negligible. Do not skip LLM reasoning to save money.

If LLM call fails: fall back to Pattern confidence threshold (0.55). Log the failure. Alert if it happens more than 3 times in an hour.

## Escalation to Human
There are situations ZEUS cannot handle autonomously and must escalate:
- Drawdown kill switch triggered: human must review before resuming
- Watchdog reports agent failed after MAX_RESTARTS: human intervention required
- LLM consistently returning malformed responses (3+ times): possible API issue
- Unknown signal category (not in HERMES_TYPE_MAP): human should update the mapping

Escalation is via Telegram alert. The alert must include exactly what happened, what state the system is in, and what human action is needed.
