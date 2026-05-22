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
