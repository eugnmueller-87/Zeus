# Pantheon OS — Autonomous Trading Orchestrator

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Paper%20Trading-orange?style=flat)
![Broker](https://img.shields.io/badge/Broker-Interactive%20Brokers-red?style=flat)
![Scheduling](https://img.shields.io/badge/Scheduling-n8n-EA4B71?style=flat&logo=n8n&logoColor=white)
![Alerts](https://img.shields.io/badge/Alerts-Telegram-26A5E4?style=flat&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![ChromaDB](https://img.shields.io/badge/KB-ChromaDB-FF6B35?style=flat)
![Redis](https://img.shields.io/badge/Bridge-Upstash%20Redis-DC382D?style=flat&logo=redis&logoColor=white)

> **8-agent autonomous trading system for German markets. Eight gods, one mission. ZEUS is the supreme orchestrator — all agents report to it. Zero babysitting once deployed.**

---

![Pantheon Agent Lineup](screenshots/Screenshot%202026-05-22%20215144.png)

---

## Architecture

```
  Hermes (live Railway API — 590+ suppliers)
        ↓
  [1] Icarus  — Signal Watcher
        ↓  RawSignal
  [2] Hades   — Compliance Filter      ← OFAC · EU sanctions · ESG · LkSG
        ↓  FilteredSignal (or KILL)
  [3] Artemis — Macro Context          ← VIX · S&P500 regime · sector ETFs
        ↓  MacroContext (or SUPPRESS)
  [4] Pythia  — Pattern & Sizing       ← SQLite hit rates → Kelly-sized positions
        ↓  SizedSignal (or SKIP)
  [5] ZEUS    — LLM Reasoning          ← Claude Haiku · ChromaDB KB · past decisions
        ↓  approved / resized / rejected
  [6] Ares    — Trade Execution        ← IBKR bracket order (entry + SL + TP)
        ↓  TradeResult
  [7] Argus   — Portfolio Monitor      ← drawdown kill switch · Telegram alerts
        ↓  outcome → Pythia + KB (feedback loop)

  [Apollo] — Daily research cycle (runs parallel, not in signal path)
     ├── arXiv q-fin paper ingestion → ChromaDB
     ├── Hermes earnings enrichment → ChromaDB
     ├── Ticker map maintenance → data/ticker_map.json
     └── Self-improvement loop → analyses traces → updates zeus_skills.md

  Upstash Redis bridge → SpendLens (procurement intelligence platform)
     ├── zeus:macro:latest          — live market regime
     ├── zeus:decisions:recent      — ZEUS trade decisions as Icarus signals
     └── zeus:supplier_risk:{slug}  — Hades compliance per vendor
```

**ZEUS** owns the entire pipeline. No agent communicates with another directly. Only `zeus.py` imports from `agents/*`. All agents import from `core.types` only — no spaghetti.

---

## Agents

| # | Agent | Mythology | Role |
|---|---|---|---|
| 1 | **Icarus** | Flies closest to the sun — first to see market signals | Monitors the live Hermes API (590+ suppliers). Classifies events by category and severity. Deduplicates across poll cycles. |
| 2 | **Hades** | Lord of the underworld — judges who passes | Compliance firewall. OFAC, EU sanctions (BaFin/Reg 833/2014), ESG sector flags, LkSG violations → hard kill or severity downgrade. Full audit trail. |
| 3 | **Artemis** | Goddess of the hunt — tracks conditions, picks the moment | Fetches VIX, S&P 500 1-month return, and 6 sector ETFs. Classifies market regime (bull/bear/sideways). Suppresses signals that conflict with macro environment. 15-min cache. |
| 4 | **Pythia** | Oracle of Delphi — reads patterns, predicts outcomes | Learning agent. Every signal → outcome in SQLite. Derives position size from historical hit rates per `{category}×{regime}×{VIX band}`. Kelly-inspired sizing (capped at 5%). |
| 5 | **Ares** | God of decisive action — executes the strike | Places bracket orders on Interactive Brokers via `ib_insync`. Entry + 3% stop-loss + 6% take-profit. XETRA-aware. Paper port 7497 / live port 7496. |
| 6 | **Argus** | Hundred-eyed giant — watches everything, never sleeps | Tracks portfolio equity and drawdown in real time. Emergency halt + Telegram alert if drawdown ≥ 8%. Backfills closed-trade P&L into Pythia and ChromaDB. |
| 7 | **Apollo** | God of knowledge and truth — the librarian | Runs daily: ingests arXiv q-fin papers, crawls Hermes for earnings transcripts, maintains the live supplier→ticker map, runs the self-improvement loop. |

---

## The Knowledge Layer

ZEUS learns from every trade. Three stores work together:

| Store | What lives here | Used by |
|---|---|---|
| **ChromaDB** (`data/chroma`) | Curated trading knowledge, macro playbooks, signal guides, academic papers (arXiv), decision traces with outcomes | ZEUS LLM reasoning step |
| **SQLite** (`data/trade_log.db`) | Raw signal → outcome records for statistical hit-rate tracking | Pattern Learner |
| **`data/ticker_map.json`** | Live supplier → ticker symbol map, expanded by Apollo each cycle | Icarus (signal enrichment) |

Each agent also has a private skills file (`knowledge/agents/{name}_skills.md`) loaded at startup — domain expertise the agent queries before acting.

---

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| Orchestration | `zeus.py` (plain Python) | Full control, no framework overhead, clean audit trail |
| Signal source | Hermes (Railway) | Live market intelligence for 590+ procurement suppliers |
| Scheduling | n8n | Visual webhook scheduler, no Python dependency, easy to extend |
| Market data | yfinance | Free, reliable for VIX + SPY + sector ETFs |
| Knowledge base | ChromaDB | Local persistent vector store, no infrastructure required |
| Trade memory | SQLite | Zero-config, sufficient for Phase 1 hit-rate stats |
| LLM reasoning | Claude Haiku (Anthropic) | ~$0.001/call, fast, structured JSON output |
| Execution | Interactive Brokers (`ib_insync`) | EU-regulated, German residents supported, full Python API |
| Alerts | Telegram Bot API | Instant mobile alerts for halts and trades |
| Intelligence bridge | Upstash Redis | Shared with SpendLens — ZEUS writes `zeus:*` keys |
| Infrastructure | Docker Compose | n8n container, persistent volumes |

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in:

```env
ANTHROPIC_API_KEY=sk-ant-...
HERMES_API_KEY=
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### 3. Start n8n

```bash
docker compose up -d
# n8n available at http://localhost:5678
# Import config/n8n_workflow.json
```

### 4. Run the smoke test (no IB Gateway or API keys needed)

```bash
python test_pipeline.py
```

### 5. Start the webhook server

```bash
python main.py
# ZEUS listens on http://localhost:8080
```

### 6. Switch to live paper trading

Set `"mock_execution": false` in `config/settings.json`, start IB Gateway on port 7497, then restart ZEUS.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/run` | Trigger one pipeline cycle (Icarus → Monitor) |
| `POST` | `/run/research` | Trigger Apollo's daily research cycle |
| `POST` | `/halt` | Emergency halt — cancels pending orders |
| `POST` | `/resume` | Resume after halt |
| `GET` | `/status` | Portfolio equity, drawdown, circuit breaker states |
| `GET` | `/health` | Liveness check |
| `GET` | `/agents` | Watchdog health report for all 7 agents |

---

## Pipeline Kill Switches

| Trigger | Action |
|---|---|
| Portfolio drawdown ≥ 8% | Emergency halt + Telegram alert |
| OFAC / EU sanctions match | Signal killed at Hades, logged for audit |
| ESG / LkSG flag | Signal severity downgraded |
| VIX ≥ 35 | All signals suppressed |
| Bear regime + high VIX | Positive signals suppressed |
| Agent failure (3 restarts) | Watchdog alert + graceful degradation via circuit breaker |
| `POST /halt` | Manual halt via n8n or direct API call |

---

## Project Structure

```
ZEUS/
├── main.py                      # Webhook server + standalone mode
├── test_pipeline.py             # Smoke test (no IB or API keys required)
├── requirements.txt
├── docker-compose.yml           # n8n
├── agents/
│   ├── zeus.py                  # Supreme orchestrator — owns the pipeline
│   ├── icarus.py                # Signal watcher — Hermes API
│   ├── hades.py                 # Compliance filter — OFAC, ESG, EU sanctions
│   ├── artemis.py               # Macro context — VIX, regime, sector momentum
│   ├── pythia.py                # Pattern learning — Kelly-sized positions
│   ├── ares.py                  # Trade execution — IBKR live/paper
│   ├── ares_mock.py             # Mock execution — no IB needed
│   ├── argus.py                 # Portfolio monitor — drawdown kill switch
│   └── apollo.py                # Research — KB seeding + self-improvement
├── core/
│   ├── types.py                 # Single source of truth for all data contracts
│   ├── knowledge_base.py        # ChromaDB wrapper (shared KB)
│   ├── agent_knowledge.py       # Per-agent private skills KB
│   ├── circuit_breaker.py       # Per-agent fault isolation
│   ├── watchdog.py              # Agent health daemon + auto-restart
│   ├── redis_bridge.py          # ZEUS → SpendLens intelligence feed
│   └── logging_setup.py
├── knowledge/
│   ├── trading_fundamentals.md  # R/R rules, Kelly, entry timing
│   ├── macro_playbooks.md       # Bull/bear/sideways/high-vol playbooks
│   ├── signal_interpretation.md # Per signal type: trade logic, direction
│   ├── risk_management.md       # Three laws, drawdown levels, stop placement
│   ├── sector_dynamics.md       # Tech/Energy/Financials/Healthcare characteristics
│   └── agents/
│       ├── icarus_skills.md
│       ├── hades_skills.md
│       ├── artemis_skills.md
│       ├── pythia_skills.md
│       ├── ares_skills.md
│       ├── argus_skills.md
│       ├── zeus_skills.md
│       └── apollo_skills.md
├── config/
│   ├── settings.json            # Runtime config (paper/live, drawdown limits)
│   └── n8n_workflow.json        # Importable n8n workflow
└── data/
    ├── chroma/                  # ChromaDB persistent store
    ├── trade_log.db             # SQLite trade history
    └── ticker_map.json          # Live supplier → ticker map (maintained by Apollo)
```

---

## SpendLens Integration

ZEUS writes live intelligence to a shared Upstash Redis instance, readable by [SpendLens](https://github.com/eugnmueller-87/PROCUREMENT) — a procurement intelligence platform that tracks vendor spend and risk.

```
ZEUS pipeline run
  → Hades assesses supplier      → zeus:supplier_risk:{slug}
  → Trend classifies macro       → zeus:macro:latest
  → ZEUS approves/rejects trade  → zeus:decision:{trace_id}
                                    zeus:decisions:recent (last 50)

SpendLens reads via HermesClient:
  GET /api/zeus/macro             — live market regime for category strategy
  GET /api/zeus/decisions         — ZEUS trade decisions on Icarus AI screen
  GET /api/suppliers/{name}/zeus-risk  — Hades compliance per vendor
```

---

## Executive Dashboard

Real-time trading UI — Bloomberg-style dark terminal. Streams pipeline events via WebSocket.

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ PANTHEON OS  [LIVE] ● PAPER    Equity: €52,340  DD: 1.2%   │
├─────────────┬──────────────────────────────┬────────────────────┤
│  PIPELINE   │  EQUITY CURVE  ~~~^~~~^~~~   │  PORTFOLIO         │
│  ICARUS 🦅● │                              │  Drawdown ████░ 8% │
│     ↓       ├──────────────────────────────┤  Circuit Breakers  │
│  HADES  ⚖️● │  LIVE FEED                   ├────────────────────┤
│     ↓       │  20:14 TRADE SAP BUY ✓       │ ⚡ ZEUS REASONING  │
│  ARTEMIS 🌙●│  20:13 KILL Hades:OFAC       │ "Macro regime      │
│     ↓       │  20:12 SIGNAL Infineon       │  supports energy   │
│  PYTHIA 🔮● │  20:11 TRADE RWE  BUY ✓      │  long. 68% hit     │
│     ↓       │                              │  rate. Approved."  │
│  ZEUS   ⚡● │                              │                    │
│     ↓       │                              │                    │
│  ARES   ⚔️● │                              │                    │
│     ↓       │                              │                    │
│  ARGUS  👁️● │                              │                    │
│  ────────── │                              │                    │
│  APOLLO 📚● │                              │                    │
└─────────────┴──────────────────────────────┴────────────────────┘
```

**Start locally:**
```powershell
pip install -r requirements.txt
cd dashboard\frontend && npm install && cd ..\..
.\dashboard\start_dev.ps1
# Dashboard → http://localhost:3000
```

**Deploy with Docker:**
```bash
docker compose up -d dashboard-backend dashboard-frontend
```

---

## Roadmap

- [x] 8-agent pipeline (Icarus → Hades → Artemis → Pythia → ZEUS → Ares → Argus + Apollo)
- [x] ChromaDB knowledge base with curated trading fundamentals
- [x] Per-agent private skills knowledge bases
- [x] Circuit breakers + Watchdog daemon (zero-outage design)
- [x] Claude Haiku LLM reasoning step in ZEUS
- [x] Mock execution layer for pre-IBKR testing
- [x] n8n webhook integration + Docker Compose
- [x] Upstash Redis bridge → SpendLens intelligence feed
- [x] Apollo daily research cycle (arXiv, Hermes earnings, ticker map, self-improvement)
- [x] Executive dashboard — Bloomberg-style real-time UI (React + FastAPI WebSocket)
- [ ] Iris agent — Icarus signal triage split (separate fetch from interpretation)
- [ ] OpenBB swap in Artemis (DAX + EURO STOXX 50 coverage)
- [ ] IBKR account live — switch `mock_execution: false`
- [ ] Phase 2 — Redis Streams async event bus between agents
- [ ] Phase 3 — Crypto layer via Binance EU

---

## Notes

- **Germany-based**: Alpaca does not support German residents. Interactive Brokers (IBKR) is the execution layer — EU-regulated, German tax-compliant (Abgeltungsteuer), paper trading available for free.
- **Paper trading by default**: `"paper_trading": true` and `"mock_execution": true` in settings. No real money at risk until explicitly opted in.
- **Pattern learning needs data**: The Pattern agent requires ~10 historical trades per context key (`{category}×{regime}×{VIX band}`) before learned hit rates replace default sizing. Run paper trading for 4–6 weeks before the learning layer becomes meaningful.
- **Apollo seeds the KB**: On first run, Apollo initialises `data/ticker_map.json` with 40+ pre-mapped suppliers. Daily cycles expand this automatically from live Hermes signals.
- **No framework overhead**: Orchestration is plain Python in `zeus.py`. No LangGraph, no LangChain. Every stage is visible, debuggable, and testable in isolation.

---

*Built by [Eugen Mueller](https://github.com/eugnmueller-87) — Procurement Leader → AI Engineer*
