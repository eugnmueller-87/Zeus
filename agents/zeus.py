"""
ZEUS — Supreme Orchestrator Agent
All agents report here. ZEUS controls the full pipeline lifecycle,
routes signals between agents, enforces kill switches, and owns final
trade approval before execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from agents.icarus import IcarusAgent, RawSignal
from agents.hades import HadesAgent, FilteredSignal
from agents.trend import TrendAgent, MacroContext
from agents.pattern import PatternAgent, SizedSignal
from agents.execution import ExecutionAgent, TradeResult
from agents.execution_mock import MockExecutionAgent
from agents.monitor import MonitorAgent

logger = logging.getLogger("zeus")


class PipelineStatus(Enum):
    RUNNING = "running"
    HALTED = "halted"       # triggered by drawdown kill switch
    PAUSED = "paused"       # manual pause
    SHUTDOWN = "shutdown"


@dataclass
class ZeusConfig:
    max_portfolio_drawdown_pct: float = 0.08   # 8% → halt all trading
    max_open_positions: int = 10
    paper_trading: bool = True                 # always start in paper mode
    mock_execution: bool = False               # True → use MockExecutionAgent (no IB needed)


@dataclass
class PipelineRun:
    """Audit trail for one signal moving through the full pipeline."""
    run_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    raw_signal: Optional[RawSignal] = None
    filtered_signal: Optional[FilteredSignal] = None
    macro_context: Optional[MacroContext] = None
    sized_signal: Optional[SizedSignal] = None
    trade_result: Optional[TradeResult] = None
    killed_at_stage: Optional[str] = None
    kill_reason: Optional[str] = None

    def killed(self, stage: str, reason: str) -> "PipelineRun":
        self.killed_at_stage = stage
        self.kill_reason = reason
        logger.info("[ZEUS] Pipeline killed at %s — %s", stage, reason)
        return self


class ZeusOrchestrator:
    """
    ZEUS owns the pipeline. Every agent is a child node.
    No agent communicates with another without ZEUS routing the message.
    """

    def __init__(self, config: ZeusConfig | None = None):
        self.config = config or ZeusConfig()
        self.status = PipelineStatus.RUNNING

        # Instantiate all agents — ZEUS holds the only references
        self.icarus = IcarusAgent()
        self.hades = HadesAgent()
        self.trend = TrendAgent()
        self.pattern = PatternAgent()
        if self.config.mock_execution:
            self.execution = MockExecutionAgent()
        else:
            self.execution = ExecutionAgent(paper=self.config.paper_trading)
        self.monitor = MonitorAgent(
            max_drawdown_pct=self.config.max_portfolio_drawdown_pct,
            on_kill=self._emergency_halt,
        )

        logger.info(
            "[ZEUS] Initialized — paper_trading=%s mock_execution=%s max_drawdown=%.1f%%",
            self.config.paper_trading,
            self.config.mock_execution,
            self.config.max_portfolio_drawdown_pct * 100,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> list[PipelineRun]:
        """
        Fetch new signals from Icarus and route each through the full
        pipeline. Returns one PipelineRun per signal processed.
        """
        if self.status != PipelineStatus.RUNNING:
            logger.warning("[ZEUS] Pipeline is %s — skipping run.", self.status.value)
            return []

        raw_signals = self.icarus.fetch()
        logger.info("[ZEUS] Icarus returned %d signal(s).", len(raw_signals))

        runs: list[PipelineRun] = []
        for sig in raw_signals:
            run = self._process_signal(sig)
            runs.append(run)

        # After processing, ask Monitor to refresh portfolio state
        self.monitor.refresh()
        return runs

    def halt(self, reason: str = "manual") -> None:
        self.status = PipelineStatus.HALTED
        self.execution.cancel_all_pending()
        logger.critical("[ZEUS] HALT — reason: %s", reason)

    def resume(self) -> None:
        if self.status == PipelineStatus.SHUTDOWN:
            raise RuntimeError("Cannot resume a shutdown ZEUS instance.")
        self.status = PipelineStatus.RUNNING
        logger.info("[ZEUS] Resumed.")

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _process_signal(self, raw: RawSignal) -> PipelineRun:
        run = PipelineRun(run_id=raw.signal_id, raw_signal=raw)

        # Stage 1 — Hades compliance filter
        filtered = self.hades.filter(raw)
        if filtered is None:
            return run.killed("hades", "compliance / OFAC / ESG block")
        run.filtered_signal = filtered

        # Stage 2 — Trend / macro context
        macro = self.trend.analyze(filtered)
        if macro.suppress:
            return run.killed("trend", macro.suppress_reason or "macro context unfavorable")
        run.macro_context = macro

        # Stage 3 — Pattern learner sizes the position
        sized = self.pattern.size(filtered, macro)
        if sized.skip:
            return run.killed("pattern", "low historical confidence score")
        run.sized_signal = sized

        # Stage 4 — Check portfolio headroom
        if not self._portfolio_allows(sized):
            return run.killed("zeus", "max open positions reached")

        # Stage 5 — Execute
        result = self.execution.place(sized)
        run.trade_result = result
        self.pattern.record_trade(sized, result)   # feed outcome back to learner

        logger.info(
            "[ZEUS] Trade placed — %s %s @ %s | order_id=%s",
            result.side, result.symbol, result.fill_price, result.order_id,
        )
        return run

    def _portfolio_allows(self, sized: SizedSignal) -> bool:
        open_count = self.monitor.open_position_count()
        return open_count < self.config.max_open_positions

    def _emergency_halt(self, reason: str) -> None:
        """Called by MonitorAgent when drawdown limit is breached."""
        self.halt(reason=f"emergency halt — {reason}")
