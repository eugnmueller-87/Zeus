# Apollo — Research & Knowledge Intelligence Skills

## Mission
Apollo is ZEUS's librarian, researcher, and self-improvement engine. Where other agents act on signals, Apollo builds the intelligence that makes those agents smarter over time. Apollo's work is not time-critical — it runs daily — but its cumulative effect is what separates a learning system from a static one. Without Apollo, ZEUS knows only what it was built knowing. With Apollo, ZEUS gets smarter every week.

## arXiv q-fin Paper Ingestion
The arXiv Quantitative Finance section (https://arxiv.org/archive/q-fin) is the primary source of academic research relevant to ZEUS.

Categories to monitor:
- q-fin.TR (Trading and Market Microstructure) — most relevant for signal execution
- q-fin.PM (Portfolio Management) — Kelly criterion implementations, position sizing
- q-fin.ST (Statistical Finance) — regime detection, volatility modeling
- q-fin.RM (Risk Management) — drawdown theory, tail risk

Ingestion strategy:
- Fetch the 5 most recent papers per category per daily cycle
- Ingest title + abstract into the shared KB under source="arxiv:{category}"
- Full paper text is too large — abstract captures the key contribution
- Skip papers that are pure theory with no practical implications for trading

Key papers already worth seeding (one-time):
- Hamilton (1989): "A New Approach to the Economic Analysis of Nonstationary Time Series" — the original regime-switching (HMM) paper. Directly relevant to TrendAgent.
- Kelly (1956): "A New Interpretation of Information Rate" — the original Kelly Criterion. Directly relevant to PatternAgent.
- Lo (2004): "The Adaptive Markets Hypothesis" — explains why past win rates degrade over time. Relevant to PatternAgent's overfitting caution.
- Ang & Bekaert (2002): "Regime Switches in Interest Rates" — practical regime detection in practice.

## Ticker Map Maintenance
The supplier→ticker map is ZEUS's trading universe. A signal about "Infineon Technologies" is worthless if Icarus cannot resolve it to a tradeable symbol.

Apollo owns this map. Rules:
- Map lives in data/ticker_map.json — persistent, version-controlled
- Apollo adds new entries when Hermes signals reference unmapped suppliers
- Apollo uses yfinance symbol search as the resolution mechanism
- European tickers take priority for XETRA-listed companies (e.g. IFX.DE over IFNNY)
- Apollo does NOT remove entries — even stale tickers are kept for audit

Coverage gaps to resolve proactively:
- German Mittelstand suppliers (often privately held — mark as "unlisted" explicitly)
- Asian suppliers (Korean, Japanese, Taiwanese exchanges — use ADR tickers where available)
- Subsidiary names (e.g. "Google DeepMind" → GOOGL, "Microsoft Research" → MSFT)

Validation: quarterly, Apollo should verify all tickers in the map still trade by running yfinance.info() on a sample.

## Hermes Earnings Enrichment
Hermes crawls 590+ suppliers. EARNINGS signals are particularly valuable for ZEUS because:
- Earnings surprises have the clearest directional implication
- The first 30-60 minutes after an earnings release is the highest-alpha window
- Historical earnings data per company teaches ZEUS seasonal patterns

Apollo's job: for each company in the core trading universe, query Hermes for EARNINGS signals and store structured summaries in the shared KB. This means when ZEUS sees an NVIDIA earnings signal, the KB already has context from prior NVIDIA earnings cycles.

Core universe for earnings tracking:
NVIDIA, TSMC, SAP, Siemens, ASML, Intel, AMD, Qualcomm, BASF, Deutsche Telekom

## Self-Improvement Loop
This is Apollo's highest-value function. It closes the feedback loop between ZEUS's decisions and ZEUS's future behaviour.

Process:
1. Query the decisions ChromaDB collection for recent traces (minimum 10 for statistical validity)
2. Calculate win rates broken down by: signal category, market regime, VIX band
3. Identify systematic biases:
   - Categories with high approval rate but low win rate → ZEUS is overconfident here
   - Categories with low approval rate but high win rate when approved → ZEUS is underconfident
   - Regimes where all trades lose → suppress trading in those contexts
4. Write dated insights to zeus_skills.md so the next KB seed cycle picks them up
5. The next time ZEUS queries the KB before a trade, these insights appear as context

Frequency: run after every 50 new traces, or daily — whichever comes first.

Interpretation guidelines for win rate data:
- n < 10: ignore, statistical noise
- n 10–30: note the trend but don't make hard rules
- n 30+: strong signal, worth adding to zeus_skills.md as a rule
- Win rate < 40%: flag as systematic underperformance, reduce default size for this context
- Win rate > 70%: flag as high-confidence context, allow slightly larger sizing

## SEC EDGAR Integration (Phase 2)
SEC 8-K filings (material events) are the ground truth for corporate events.
EDGAR EFTS search allows full-text queries.

When to activate:
- Phase 1: use Hermes signals only (Hermes already reads SEC filings)
- Phase 2: direct EDGAR integration for events Hermes misses (small-cap, obscure filers)
- API: https://efts.sec.gov/LATEST/search-index?q={query}&forms=8-K

## Data Quality and Deduplication
Apollo must not spam the KB with duplicate content — ChromaDB is persistent but not infinitely scalable.

Deduplication rules:
- arXiv papers: use the arxiv ID (from the atom feed URL) as the document ID
- Hermes earnings: use signal_id + company name as the composite key
- Self-improvement insights: one block per day per date stamp — no duplicates

Apollo checks for existing document IDs before inserting. If already present, skip.

## Apollo's Own Learning
Apollo improves its research targeting over time:
- Track which KB entries are most frequently retrieved during ZEUS LLM reasoning
- Papers that are retrieved often → expand coverage in that area
- Papers retrieved never → that category is not relevant to ZEUS's signal mix

This feedback requires a future enhancement: ChromaDB query logging. Phase 2.

## Error Tolerance
Apollo runs on a daily schedule. All failures must be logged but never halt the pipeline.

Priority of recovery:
1. If arXiv is down → skip, retry tomorrow. The KB does not degrade overnight.
2. If Hermes is down → skip earnings ingestion. Pipeline still runs on existing KB.
3. If yfinance lookup fails → leave supplier unmapped. Icarus will pass signal with empty tickers.
4. If self-improvement analysis has < 10 samples → skip silently. Not a failure.

Apollo health is DEGRADED only if it has not successfully completed a cycle in > 48 hours.
