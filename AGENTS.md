# Pantheon OS — The 8 Gods, Plain English

---

## How the Agents Talk to Each Other

One strict rule: **no agent ever talks directly to another agent.** Only ZEUS is allowed to call them. Think of it like a company where every employee reports to the CEO — nobody goes around them.

### The Signal Pipeline (runs every 15 minutes, triggered by n8n)

```
  Hermes API (590+ suppliers, live market intelligence)
       │
       ▼
  🦅 ICARUS ──────── fetches raw signals, enriches with ticker symbols
       │
       │  RawSignal { headline, supplier, category, severity, tickers }
       ▼
  ⚖️  HADES ──────── compliance check against OFAC / ESG / EU sanctions
       │
       │  FilteredSignal { compliance_score, notes }   ← KILL here if sanctioned
       ▼
  🌙 ARTEMIS ─────── pulls VIX + S&P500 + sector ETFs, classifies regime
       │
       │  MacroContext { regime, vix, suppress }        ← SUPPRESS here if VIX ≥ 35
       ▼
  🔮 PYTHIA ──────── looks up historical win rate for this exact context
       │
       │  SizedSignal { confidence, position_size_pct } ← SKIP if confidence too low
       ▼
  ⚡ ZEUS ─────────── queries KB + asks Claude AI: approve / reject / resize?
       │
       │  Decision { approved, reasoning, override_size }  ← REJECT if not convinced
       ▼
  ⚔️  ARES ───────── places bracket order on Interactive Brokers
       │
       │  TradeResult { symbol, side, fill_price, order_id }
       ▼
  👁️  ARGUS ──────── monitors portfolio, checks drawdown, backfills P&L to Pythia
```

### The Daily Research Cycle (runs once per day, independent)

```
  📚 APOLLO ── runs parallel, never blocks the signal pipeline
       ├── arXiv q-fin papers ──────────────► ChromaDB knowledge base
       ├── Hermes earnings transcripts ──────► ChromaDB knowledge base
       ├── New suppliers from signals ───────► ticker_map.json (Apollo maps them)
       └── ZEUS past decisions + outcomes ──► zeus_skills.md (self-improvement)
```

### What Gets Passed Between Stages

| From → To | What's handed over | Can it be killed? |
|---|---|---|
| Icarus → Hades | Raw signal (headline, supplier, tickers) | No — always goes to Hades |
| Hades → Artemis | Filtered signal + compliance score | Yes — OFAC/sanctions = hard kill |
| Artemis → Pythia | Macro context (VIX, regime) | Yes — extreme VIX or bear market = suppress |
| Pythia → ZEUS | Sized signal (confidence %, position size) | Yes — low confidence = skip |
| ZEUS → Ares | Approved trade (with optional resize) | Yes — Claude rejects it = no trade |
| Ares → Argus | Trade result (fill price, order ID) | No — Argus always monitors |
| Argus → Pythia | Closed trade P&L (feedback loop) | No — always feeds back |

### The Golden Rule

> **ZEUS is the only file allowed to import from `agents/`.**
> All agents import from `core/types` only — no agent knows another agent exists.
> This means any agent can be replaced, upgraded, or turned off without breaking anything else.

### Circuit Breakers

Every agent call is wrapped in a circuit breaker. If an agent fails 3 times in 5 minutes, the breaker opens and ZEUS uses a safe fallback instead of crashing the whole pipeline. The Watchdog daemon checks all agents every 30 seconds and auto-restarts failed ones.

---

---

## ⚡ ZEUS — The Boss
Runs the whole show. Every other agent reports to ZEUS. Nothing happens without its approval. It reads the knowledge base, asks Claude AI "should we trade this?", and makes the final call.

---

## 🦅 Icarus — The Scout
Watches the Hermes API 24/7 for market-moving news across 590+ suppliers. Spots things like "NVIDIA has a chip shortage" or "SAP just beat earnings." Hands the signal to the next agent.

---

## ⚖️ Hades — The Bouncer
Before anything goes further, Hades checks: is this company on the OFAC sanctions list? Any ESG violations? EU sanctions? If yes — hard kill, no trade, full audit log. Nobody gets past Hades dirty.

---

## 🌙 Artemis — The Weather Check
Looks at the macro environment before every trade. What's the VIX (fear index)? Is the market in bull, bear, or sideways mode? If VIX is above 35 or we're in a bear market — she suppresses the signal. Wrong weather, no trade.

---

## 🔮 Pythia — The Statistician
Learns from every trade ever made. Calculates: "historically, when we got a supply disruption signal in a bull market with medium VIX, we won 68% of the time." Uses that to size the position — more confidence, bigger bet. Capped at 5% of portfolio.

---

## ⚔️ Ares — The Trigger
The only agent that touches real money. Places the bracket order on Interactive Brokers: entry price + 3% stop-loss + 6% take-profit. 2:1 reward-to-risk on every trade, no exceptions.

---

## 👁️ Argus — The Guardian
Watches the portfolio every cycle. If total drawdown hits 8% — emergency halt, cancel all orders, send Telegram alert. Also tracks every closed trade's P&L and feeds the results back to Pythia so it keeps learning.

---

## 📚 Apollo — The Librarian
Runs daily in the background. Ingests arXiv trading research papers, pulls earnings transcripts from Hermes, keeps the supplier→ticker map fresh, and reads ZEUS's own past decisions to find patterns and improve its own strategy playbook.

---

## Signal Conviction Rating System

Every signal that enters the pipeline gets scored. This is how we separate **"act now"** from **"ignore"** — using the same framework professional quant funds use.

### The 5-Tier Conviction Scale

| Tier | Label | What it means | Position size |
|------|-------|---------------|---------------|
| 🔴 **1** | **STRONG LONG** | All factors aligned, high confidence | Full size (2x base) |
| 🟠 **2** | **MODERATE LONG** | Most factors aligned, some uncertainty | Half size (1x base) |
| ⚪ **3** | **NEUTRAL** | Mixed signals — no edge | No trade |
| 🔵 **4** | **MODERATE SHORT** | Factors lean negative | Reduced / hedge only |
| 🟣 **5** | **STRONG SHORT** | Strong negative signal | Avoid / full short |

The score is not a gut feeling. It is a **composite number [0–100]** built from weighted factors, where each factor's weight is determined by its historical predictive power (Information Coefficient, or IC).

---

### The 10 Signal Quality Factors (ranked by predictive power)

These are the factors that academic research and professional quant funds have proven actually work. We build these into Pythia.

| Rank | Factor | What it measures | Why it works |
|------|--------|-----------------|--------------|
| 1 | **Options implied sentiment** | Put/call skew + volatility | Smart money bets here first — options market leads price |
| 2 | **Earnings surprise magnitude** | How much EPS beat/missed vs. consensus | Drift after surprise is one of the most robust effects in finance |
| 3 | **Earnings revision direction** | Analysts raising or cutting estimates | Analysts are slow — revisions cluster and momentum follows |
| 4 | **12-month price momentum** | Stock return vs. peers, last 12 months | Winners keep winning for ~6-12 months (Jegadeesh & Titman) |
| 5 | **Short interest ratio** | Days-to-cover for shorts | Rising price + high short interest = squeeze setup |
| 6 | **Volume anomaly** | Unusual volume vs. 20-day average | Big volume before price moves = informed buying |
| 7 | **NLP earnings call sentiment** | Positive/negative language in transcripts | Forward-looking language predicts next quarter |
| 8 | **Sector ETF momentum** | Is the whole sector moving? | Rising tide — individual stocks follow sector direction |
| 9 | **Quality score** | Profitability + low debt + earnings stability | High-quality companies outperform over all regimes |
| 10 | **ECB / Bund yield delta** | *(DAX-specific)* Rate movement direction | 80%+ of DAX revenues are international — ECB moves the market |

---

### DAX / German Market — What's Different

German stocks don't behave like US stocks. Three things matter more here:

1. **Macro beats earnings.** Only 18% of DAX revenue is Germany-domestic. ECB rate decisions, EUR/USD, and German Bund yields move the index more than individual earnings beats. Watch: **ECB meetings, Ifo Business Climate, Flash PMI, ZEW Sentiment.**

2. **Sector composition is different.** DAX = ~20% Financials, ~18% Autos, ~15% Chemicals/Industrials. Autos are driven by China PMI. Chemicals by energy prices. Know your sector before trading.

3. **EUR/USD is a tax on exporters.** Rising EUR = headwind for Volkswagen, BASF, Siemens. Always factor the EUR/USD trend when trading German exporters.

---

### Where This Lives in the Pipeline

**Pythia owns the conviction score.** There is no separate Rating Agent — the IC-weighted scoring and the position sizing are the same calculation. Separating them would just add latency with no benefit.

Pythia's upgrade path:
- Today: simple hit-rate stats from SQLite → confidence → position size
- Next: IC registry (rolling 63-day predictive power per factor) → composite score [0–100] → 5-tier discretization → position size multiplier (0.25x / 0.5x / 1.0x / 1.5x / 2.0x)

---

### Reference Repositories (built by professionals, not tutorials)

These are the best open-source implementations to learn from and extract knowledge into Apollo's KB:

| Repo | What to take from it |
|------|---------------------|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | 5-tier conviction output, Bull/Bear researcher debate pattern, full agent prompts |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Market Forecaster + Trade Strategist prompt engineering |
| [FinMem](https://github.com/pipiku915/FinMem-LLM-StockTrading) | Layered memory (short/medium/long-term) — maps directly to Pythia's pattern memory |
| [AgenticTrading](https://github.com/Open-Finance-Lab/AgenticTrading) | Agent orchestration patterns for real-time composition |
| [arXiv:2409.06289](https://arxiv.org/pdf/2409.06289) | LLM-generated alpha factors + IC-based pruning (53% return on SSE50) |
