# ZEUS — Autonomous Trading Orchestrator

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Paper%20Trading-orange?style=flat)
![Broker](https://img.shields.io/badge/Broker-Interactive%20Brokers-red?style=flat)
![Scheduling](https://img.shields.io/badge/Scheduling-n8n-EA4B71?style=flat&logo=n8n&logoColor=white)
![Alerts](https://img.shields.io/badge/Alerts-Telegram-26A5E4?style=flat&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)

> **6-agent autonomous trading system for German markets. ZEUS is the supreme orchestrator — all agents report to it. Zero babysitting once deployed.**

---

## Architecture

```
Hermes RSS feeds
      ↓
 [1] Icarus — Signal Watcher
      ↓  structured RawSignal
 [2] Hades — Compliance Filter        ← OFAC · ESG · blocked tickers
      ↓  FilteredSignal (or KILL)
 [3] Trend Analyzer                   ← VIX · market regime · sector momentum
      ↓  MacroContext (or SUPPRESS)
 [4] Pattern Learner                  ← SQLite hit rates → Kelly-sized positions
      ↓  SizedSignal (or SKIP)
 [5] Execution Agent                  ← IBKR bracket order (entry + SL + TP)
      ↓  TradeResult
 [6] Monitor                          ← drawdown kill switch · Telegram alerts
      ↓  outcome → Pattern Learner (feedback loop)
```

**ZEUS** owns the entire pipeline. No agent communicates with another directly — all routing goes through ZEUS.

---

## Agents

| # | Agent | Role |
|---|---|---|
| 1 | **Icarus** | Monitors RSS feeds (Hermes). Classifies events by category and severity. Emits structured signals. |
| 2 | **Hades** | Compliance firewall. OFAC sanctions, ESG sector flags, blocked tickers → hard kill or severity downgrade. |
| 3 | **Trend** | Pulls macro context via yfinance: VIX level, S&P 500 regime (bull/bear/sideways), sector ETF momentum. Suppresses signals that are valid in isolation but wrong for current macro. |
| 4 | **Pattern** | Learning agent. Stores every signal → trade → outcome in SQLite. Derives position size from historical hit rates per (signal category × market regime × VIX band). Kelly-inspired sizing. |
| 5 | **Execution** | Places bracket orders on Interactive Brokers via `ib_insync`. Entry + stop-loss (3%) + take-profit (6%). Paper port 7497 / live port 7496. |
| 6 | **Monitor** | Tracks portfolio equity and drawdown in real time. Fires emergency halt + Telegram alert if max drawdown is breached. Feeds closed-trade outcomes back to Pattern. |

---

## Tech Stack

| Component | Tool |
|---|---|
| Orchestration | ZEUS (custom) |
| Scheduling | n8n (webhook trigger every 15 min) |
| Market data | yfinance |
| Execution | Interactive Brokers API (`ib_insync`) |
| Trade memory | SQLite → ChromaDB (Phase 2) |
| Agent reasoning | LangGraph (Phase 2) |
| Event bus | Redis Streams (Phase 2) |
| Alerts | Telegram Bot API |
| Infrastructure | Docker Compose |

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start n8n

```bash
docker compose up -d
# n8n available at http://localhost:5678
# Import config/n8n_workflow.json
```

### 3. Configure

Edit `config/settings.json`:

```json
{
  "paper_trading": true,
  "mock_execution": true,
  "max_drawdown_pct": 0.08,
  "hermes_feeds": ["https://your-rss-feed-url"],
  "telegram_bot_token": "your_token",
  "telegram_chat_id": "your_chat_id"
}
```

### 4. Run the smoke test (no IB Gateway needed)

```bash
python test_pipeline.py
```

### 5. Start the webhook server

```bash
python main.py
# ZEUS listens on http://localhost:8080
# n8n → POST /run   triggers a pipeline cycle
# n8n → GET  /status returns portfolio state
```

### 6. Switch to live paper trading (requires IBKR account)

Set `"mock_execution": false` in `settings.json`, start IB Gateway on port 7497, then restart ZEUS.

---

## Pipeline Kill Switches

| Trigger | Action |
|---|---|
| Portfolio drawdown ≥ 8% | Emergency halt + Telegram alert |
| OFAC entity match | Signal killed at Hades |
| ESG sector flag | Signal severity downgraded |
| VIX ≥ 35 | All signals suppressed |
| Bear regime + high VIX | Positive signals suppressed |
| `POST /halt` | Manual halt via n8n |

---

## Roadmap

- [x] Phase 1 — Core pipeline (Icarus → Hades → Trend → Pattern → Execution → Monitor)
- [x] Mock execution layer for pre-IBKR testing
- [x] n8n webhook integration + Docker Compose
- [ ] Phase 2 — Redis Streams event bus between agents
- [ ] Phase 2 — LangGraph reasoning layer for Pattern + Trend agents
- [ ] Phase 2 — ChromaDB semantic trade memory
- [ ] Phase 3 — Crypto layer via Binance EU

---

## Project Structure

```
ZEUS/
├── main.py                   # Entry point — webhook server + standalone mode
├── test_pipeline.py          # Smoke test (no IB required)
├── requirements.txt
├── docker-compose.yml        # n8n
├── agents/
│   ├── zeus.py               # Supreme orchestrator
│   ├── icarus.py             # RSS signal watcher
│   ├── hades.py              # Compliance filter
│   ├── trend.py              # Macro context analyzer
│   ├── pattern.py            # Learning + position sizing
│   ├── execution.py          # IBKR live/paper execution
│   └── execution_mock.py     # Mock execution (no IB needed)
├── config/
│   ├── settings.json         # Runtime config
│   └── n8n_workflow.json     # Importable n8n workflow
└── core/
    └── logging_setup.py
```

---

## Notes

- **Germany-based**: Alpaca does not support German residents. Interactive Brokers (IBKR) is the execution layer — EU-regulated, full Python API, paper trading available for free.
- **Paper trading by default**: `"paper_trading": true` and `"mock_execution": true` in settings. No real money at risk until explicitly opted in.
- **Pattern learning needs data**: The Pattern agent requires ~10 historical trades per context key (signal category × regime × VIX band) before learned hit rates replace default sizing. Run paper trading for 4–6 weeks before the learning layer becomes meaningful.

---

*Built by [Eugen Mueller](https://github.com/eugnmueller-87) — Procurement Leader → AI Engineer*
