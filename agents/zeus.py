"""
ZEUS — Supreme Orchestrator Agent

Responsibilities:
  1. Own the pipeline — every agent is a child, no agent talks to another
  2. Query the Knowledge Base before making the final trade decision
  3. Run an LLM reasoning step (Claude) to evaluate the signal holistically
  4. Write a full DecisionTrace to the KB for every signal processed
  5. Manage circuit breakers — degrade gracefully if any agent fails
  6. Start and monitor the Watchdog for zero-outage operation

Import rule: zeus.py is the ONLY file allowed to import from agents/*.
All other agents import from core.types only.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import anthropic

from core.types import (
    AgentHealth, DecisionTrace, FilteredSignal, HealthReport,
    MacroContext, MarketRegime, PipelineStatus, RawSignal,
    SizedSignal, TradeResult,
)
from core.knowledge_base import KnowledgeBase
from core.circuit_breaker import CircuitBreaker
from core.watchdog import Watchdog
from core.redis_bridge import RedisBridge

from agents.icarus import IcarusAgent
from agents.hades import HadesAgent
from agents.trend import TrendAgent
from agents.pattern import PatternAgent
from agents.execution import ExecutionAgent
from agents.execution_mock import MockExecutionAgent
from agents.monitor import MonitorAgent
from agents.apollo import ApolloAgent

logger = logging.getLogger("zeus")


@dataclass
class ZeusConfig:
    max_portfolio_drawdown_pct: float = 0.08
    max_open_positions:         int   = 10
    paper_trading:              bool  = True
    mock_execution:             bool  = True
    min_zeus_confidence:        float = 0.55   # ZEUS won't trade below this even if Pattern says go
    use_llm_reasoning:          bool  = True   # set False to skip Claude call (faster, less cost)


@dataclass
class PipelineRun:
    """Full audit trail for one signal moving through the pipeline."""
    run_id:          str
    started_at:      datetime
    raw_signal:      Optional[RawSignal]      = None
    filtered_signal: Optional[FilteredSignal] = None
    macro_context:   Optional[MacroContext]   = None
    sized_signal:    Optional[SizedSignal]    = None
    trade_result:    Optional[TradeResult]    = None
    trace:           Optional[DecisionTrace]  = None
    killed_at_stage: Optional[str]            = None
    kill_reason:     Optional[str]            = None

    def kill(self, stage: str, reason: str) -> "PipelineRun":
        self.killed_at_stage = stage
        self.kill_reason = reason
        logger.info("[ZEUS] Signal killed at %s — %s", stage, reason)
        return self


class ZeusOrchestrator:
    """
    ZEUS owns the full pipeline.
    Circuit breakers protect every agent call.
    Watchdog runs as a background daemon.
    LLM reasoning runs before final trade approval.
    All decisions are written to the Knowledge Base.
    """

    def __init__(self, config: ZeusConfig | None = None):
        self.config = config or ZeusConfig()
        self.status = PipelineStatus.RUNNING

        # Core infrastructure
        self.kb      = KnowledgeBase()
        self.cb      = CircuitBreaker(failure_threshold=3, window_seconds=300, reset_timeout=120)
        self.watchdog = Watchdog(alert_fn=self._send_alert)

        # Agents — ZEUS holds the only references
        self.icarus    = IcarusAgent()
        self.hades     = HadesAgent()
        self.trend     = TrendAgent()
        self.pattern   = PatternAgent()
        self.execution = MockExecutionAgent() if self.config.mock_execution else ExecutionAgent(paper=self.config.paper_trading)
        self.monitor   = MonitorAgent(
            max_drawdown_pct=self.config.max_portfolio_drawdown_pct,
            on_kill=self._emergency_halt,
            alert_fn=self._send_alert,
        )
        self.apollo    = ApolloAgent(knowledge_base=self.kb)   # injected with shared KB

        # LLM client for reasoning step
        self._claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        self.bridge  = RedisBridge()   # SpendLens intelligence feed

        self._register_watchdog()
        self.watchdog.start()

        logger.info(
            "[ZEUS] Initialised — paper=%s mock=%s llm_reasoning=%s",
            self.config.paper_trading, self.config.mock_execution, self.config.use_llm_reasoning,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> list[PipelineRun]:
        if self.status != PipelineStatus.RUNNING:
            logger.warning("[ZEUS] Pipeline is %s — skipping run.", self.status.value)
            return []

        raw_signals = self.cb.call(
            "icarus",
            fn=self.icarus.fetch,
            fallback=[],
        )
        logger.info("[ZEUS] Icarus returned %d signal(s).", len(raw_signals))

        runs: list[PipelineRun] = []
        for sig in raw_signals:
            run = self._process_signal(sig)
            runs.append(run)

        self.cb.call("monitor", fn=self.monitor.refresh, fallback=None)
        return runs

    def run_research_cycle(self) -> dict:
        """Trigger Apollo's daily research cycle — ingest literature, update tickers, self-improve."""
        return self.cb.call("apollo", fn=self.apollo.run_research_cycle, fallback={"error": "circuit open"})

    def halt(self, reason: str = "manual") -> None:
        self.status = PipelineStatus.HALTED
        try:
            self.execution.cancel_all_pending()
        except Exception:
            pass
        self._send_alert(f"ZEUS HALTED — {reason}")
        logger.critical("[ZEUS] HALT — %s", reason)

    def resume(self) -> None:
        if self.status == PipelineStatus.SHUTDOWN:
            raise RuntimeError("Cannot resume a shutdown ZEUS instance.")
        self.status = PipelineStatus.RUNNING
        logger.info("[ZEUS] Resumed.")

    def health(self) -> AgentHealth:
        if self.status == PipelineStatus.RUNNING:
            return AgentHealth.HEALTHY
        if self.status == PipelineStatus.HALTED:
            return AgentHealth.FAILED
        return AgentHealth.DEGRADED

    def get_health_reports(self) -> list[HealthReport]:
        return self.watchdog.poll_now()

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _process_signal(self, raw: RawSignal) -> PipelineRun:
        run_id = str(uuid.uuid4())[:12]
        run    = PipelineRun(run_id=run_id, started_at=datetime.now(timezone.utc), raw_signal=raw)
        trace  = self._init_trace(run_id, raw)

        # Stage 1 — Hades compliance
        filtered: Optional[FilteredSignal] = self.cb.call(
            "hades",
            fn=lambda: self.hades.filter(raw),
            fallback=None,
        )
        trace.hades_passed = filtered is not None
        if filtered is None:
            trace.hades_notes = ["Hades killed or circuit open"]
            trace.kill_reason = "compliance block or Hades circuit open"
            trace.killed_at_stage = "hades"
            self._write_trace(trace)
            return run.kill("hades", trace.kill_reason)
        trace.hades_notes = filtered.notes
        run.filtered_signal = filtered
        self.bridge.push_supplier_risk(filtered)   # → SpendLens vendor risk

        # Stage 2 — Trend macro context
        macro: MacroContext = self.cb.call(
            "trend",
            fn=lambda: self.trend.analyze(filtered),
            fallback=MacroContext(
                fetched_at=datetime.now(timezone.utc),
                regime=MarketRegime.UNKNOWN,
                vix=20.0,
                sp500_1m_return=0.0,
                suppress=False,
            ),
        )
        trace.trend_regime     = macro.regime.value if hasattr(macro.regime, "value") else str(macro.regime)
        trace.trend_vix        = macro.vix
        trace.trend_suppressed = macro.suppress
        if macro.suppress:
            trace.killed_at_stage = "trend"
            trace.kill_reason     = macro.suppress_reason or "macro suppression"
            self._write_trace(trace)
            return run.kill("trend", trace.kill_reason)
        run.macro_context = macro
        self.bridge.push_macro(macro)              # → SpendLens category strategy

        # Stage 3 — Pattern sizing
        sized: SizedSignal = self.cb.call(
            "pattern",
            fn=lambda: self.pattern.size(filtered, macro),
            fallback=SizedSignal(
                original=filtered, macro=macro,
                confidence=0.5, position_size_pct=0.01,
                skip=False,
            ),
        )
        trace.pattern_confidence = sized.confidence
        trace.pattern_size_pct   = sized.position_size_pct
        if sized.skip:
            trace.killed_at_stage = "pattern"
            trace.kill_reason     = sized.skip_reason or "low confidence"
            self._write_trace(trace)
            return run.kill("pattern", trace.kill_reason)
        run.sized_signal = sized

        # Stage 4 — ZEUS LLM reasoning + KB query (the final judge)
        approved, reasoning, override_size = self._zeus_evaluate(sized, macro, trace)
        trace.zeus_reasoning = reasoning
        trace.zeus_approved  = approved
        if override_size is not None:
            trace.zeus_override        = True
            trace.zeus_override_reason = f"ZEUS resized from {sized.position_size_pct:.3f} to {override_size:.3f}"
            sized.position_size_pct    = override_size

        if not approved:
            trace.killed_at_stage = "zeus"
            trace.kill_reason     = "ZEUS LLM reasoning rejected trade"
            self._write_trace(trace)
            return run.kill("zeus", trace.kill_reason)

        # Stage 5 — Portfolio headroom check
        if self.monitor.open_position_count() >= self.config.max_open_positions:
            trace.killed_at_stage = "zeus"
            trace.kill_reason     = "max open positions reached"
            self._write_trace(trace)
            return run.kill("zeus", trace.kill_reason)

        # Stage 6 — Execute
        result: TradeResult = self.cb.call(
            "execution",
            fn=lambda: self.execution.place(sized),
            fallback=TradeResult(
                order_id="failed", symbol="", side="", fill_price=None, qty=0, status="circuit_open"
            ),
        )
        run.trade_result = result

        trace.trade_placed = result.status not in ("circuit_open", "skipped", "error")
        trace.symbol       = result.symbol
        trace.side         = result.side
        trace.fill_price   = result.fill_price

        # Feed outcome back to Pattern + KB
        self.cb.call("pattern", fn=lambda: self.pattern.record_trade(sized, result), fallback=None)
        self._write_trace(trace)
        run.trace = trace

        logger.info(
            "[ZEUS] Trade placed — %s %s @ %s | order_id=%s | confidence=%.2f",
            result.side, result.symbol, result.fill_price, result.order_id, sized.confidence,
        )
        return run

    # ------------------------------------------------------------------
    # ZEUS LLM reasoning — the final judge
    # ------------------------------------------------------------------

    def _zeus_evaluate(
        self,
        sized: SizedSignal,
        macro: MacroContext,
        trace: DecisionTrace,
    ) -> tuple[bool, str, Optional[float]]:
        """
        Query the KB for relevant knowledge + similar past decisions,
        then ask Claude to make the final trade approval call.
        Returns (approved, reasoning_text, override_position_size_or_None).
        """
        if not self.config.use_llm_reasoning:
            return sized.confidence >= self.config.min_zeus_confidence, "LLM reasoning disabled.", None

        # Build KB context
        kb_query = (
            f"{sized.category.value} signal in {macro.regime} market, "
            f"VIX {macro.vix:.1f}, supplier {sized.supplier}"
        )
        knowledge_chunks  = self.kb.query_knowledge(kb_query, n_results=4)
        past_decisions    = self.kb.query_similar_decisions(kb_query, n_results=3)
        outcome_stats     = self.kb.query_outcomes_by_context(sized.category.value, trace.trend_regime)

        kb_context = "\n\n".join([
            "--- TRADING KNOWLEDGE ---",
            *knowledge_chunks,
            "--- SIMILAR PAST DECISIONS ---",
            *past_decisions,
            f"--- HISTORICAL OUTCOMES FOR THIS CONTEXT ---\n{outcome_stats}",
        ]) if knowledge_chunks or past_decisions else "No KB context available yet."

        prompt = f"""You are ZEUS, the supreme trading orchestrator. You must make the final decision on whether to place this trade.

SIGNAL
Headline:  {sized.headline}
Supplier:  {sized.supplier}
Category:  {sized.category.value}
Severity:  {sized.severity.value}
Tickers:   {sized.affected_tickers}

PIPELINE ASSESSMENT
Hades compliance score: {sized.original.compliance_score:.2f} | Notes: {'; '.join(sized.original.notes)}
Market regime: {macro.regime} | VIX: {macro.vix:.1f} | SP500 1m return: {macro.sp500_1m_return*100:.1f}%
Sector momentum: {macro.sector_momentum}
Pattern confidence: {sized.confidence:.2f} | Proposed position size: {sized.position_size_pct*100:.2f}%

KNOWLEDGE BASE CONTEXT
{kb_context}

YOUR TASK
1. Evaluate whether this trade should be approved, rejected, or resized.
2. Consider: does the KB knowledge support this signal type in this macro environment?
3. Consider: what do similar past decisions tell us?
4. Be conservative — a missed trade is better than a bad trade.

Respond in this exact JSON format:
{{
  "approved": true or false,
  "confidence": 0.0 to 1.0,
  "position_size_override": null or a decimal (e.g. 0.02 for 2%),
  "reasoning": "2-3 sentence explanation of your decision"
}}"""

        try:
            response = self._claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            import json, re
            # Extract JSON block even if Claude adds markdown fences
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in Claude response")
            data = json.loads(match.group())
            approved      = bool(data.get("approved", False))
            reasoning     = data.get("reasoning", "")
            override      = data.get("position_size_override")
            override_size = float(override) if override is not None else None

            # Hard floor: never trade below min confidence
            if data.get("confidence", 1.0) < self.config.min_zeus_confidence:
                approved  = False
                reasoning += f" (ZEUS confidence {data.get('confidence'):.2f} below floor {self.config.min_zeus_confidence:.2f})"

            logger.info(
                "[ZEUS] LLM decision — approved=%s confidence=%.2f override_size=%s",
                approved, data.get("confidence", 0), override_size,
            )
            return approved, reasoning, override_size

        except Exception as exc:
            logger.error("[ZEUS] LLM reasoning failed: %s — defaulting to Pattern score.", exc)
            fallback_approved = sized.confidence >= self.config.min_zeus_confidence
            return fallback_approved, f"LLM call failed ({exc}). Used Pattern confidence fallback.", None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _init_trace(self, run_id: str, raw: RawSignal) -> DecisionTrace:
        return DecisionTrace(
            trace_id    = run_id,
            signal_id   = raw.signal_id,
            timestamp   = datetime.now(timezone.utc),
            headline    = raw.headline,
            supplier    = raw.supplier,
            category    = raw.category.value,
            severity    = raw.severity.name,
            hades_passed = False,
        )

    def _write_trace(self, trace: DecisionTrace) -> None:
        try:
            self.kb.store_decision(trace)
        except Exception as exc:
            logger.warning("[ZEUS] Failed to write trace to KB: %s", exc)
        self.bridge.push_decision(trace)           # → SpendLens Icarus AI feed

    def _emergency_halt(self, reason: str) -> None:
        self.halt(reason=f"drawdown kill — {reason}")

    def _send_alert(self, message: str) -> None:
        try:
            self.monitor.send_alert(message)
        except Exception:
            logger.warning("[ZEUS] Alert delivery failed: %s", message)

    def _register_watchdog(self) -> None:
        self.watchdog.register("zeus",      self.health)
        self.watchdog.register("icarus",    self.icarus.health)
        self.watchdog.register("hades",     self.hades.health)
        self.watchdog.register("trend",     self.trend.health)
        self.watchdog.register("pattern",   self.pattern.health)
        self.watchdog.register("execution", self.execution.health)
        self.watchdog.register("monitor",   self.monitor.health)
        self.watchdog.register("apollo",    self.apollo.health)
