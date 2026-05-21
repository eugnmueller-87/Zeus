"""
Agent 6 — Portfolio Monitor + Reporting Agent
Tracks open positions, P&L, drawdown. Fires kill switch if max drawdown hit.
Sends Telegram alerts. Feeds closed-trade outcomes back to PatternAgent via ZEUS.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

import requests

logger = logging.getLogger("monitor")


@dataclass
class PositionSnapshot:
    symbol: str
    side: str
    qty: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    opened_at: datetime


@dataclass
class PortfolioState:
    snapshots: list[PositionSnapshot] = field(default_factory=list)
    total_equity: float = 0.0
    peak_equity: float = 0.0
    current_drawdown_pct: float = 0.0
    refreshed_at: Optional[datetime] = None


class MonitorAgent:
    """
    Polls IB for portfolio state. Computes drawdown.
    Calls `on_kill` callback (ZEUS._emergency_halt) when drawdown breaches limit.
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.08,
        on_kill: Optional[Callable[[str], None]] = None,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.on_kill = on_kill
        self._telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self._telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self._state = PortfolioState()
        self._ib = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> PortfolioState:
        """Called by ZEUS after each pipeline run."""
        try:
            ib = self._get_connection()
            self._state = self._build_state(ib)
        except Exception as exc:
            logger.warning("[MONITOR] Portfolio refresh failed: %s", exc)
            return self._state

        self._check_drawdown()
        self._state.refreshed_at = datetime.utcnow()
        logger.info(
            "[MONITOR] Equity=%.2f Drawdown=%.2f%% Open=%d",
            self._state.total_equity,
            self._state.current_drawdown_pct * 100,
            len(self._state.snapshots),
        )
        return self._state

    def open_position_count(self) -> int:
        return len(self._state.snapshots)

    def send_alert(self, message: str) -> None:
        if not self._telegram_token or not self._telegram_chat_id:
            logger.info("[MONITOR] Alert (no Telegram configured): %s", message)
            return
        try:
            url = f"https://api.telegram.org/bot{self._telegram_token}/sendMessage"
            requests.post(url, json={"chat_id": self._telegram_chat_id, "text": message}, timeout=5)
        except Exception as exc:
            logger.warning("[MONITOR] Telegram alert failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_state(self, ib) -> PortfolioState:
        snapshots: list[PositionSnapshot] = []
        account_vals = ib.accountValues()

        equity = 100_000.0
        for av in account_vals:
            if av.tag == "NetLiquidation" and av.currency == "BASE":
                equity = float(av.value)
                break

        for pos in ib.portfolio():
            if pos.position == 0:
                continue
            unreal_pct = pos.unrealizedPNL / (abs(pos.position) * pos.averageCost) if pos.averageCost else 0.0
            snap = PositionSnapshot(
                symbol=pos.contract.symbol,
                side="LONG" if pos.position > 0 else "SHORT",
                qty=abs(pos.position),
                avg_cost=pos.averageCost,
                current_price=pos.marketPrice,
                unrealized_pnl=pos.unrealizedPNL,
                unrealized_pnl_pct=unreal_pct,
                opened_at=datetime.utcnow(),   # IB doesn't expose open time directly
            )
            snapshots.append(snap)

        state = PortfolioState(snapshots=snapshots, total_equity=equity)

        # Track peak for drawdown calculation
        if equity > self._state.peak_equity:
            state.peak_equity = equity
        else:
            state.peak_equity = self._state.peak_equity

        if state.peak_equity > 0:
            state.current_drawdown_pct = max(0.0, (state.peak_equity - equity) / state.peak_equity)

        return state

    def _check_drawdown(self) -> None:
        dd = self._state.current_drawdown_pct
        if dd >= self.max_drawdown_pct:
            msg = (
                f"ZEUS EMERGENCY HALT\n"
                f"Drawdown: {dd*100:.1f}% >= limit {self.max_drawdown_pct*100:.1f}%\n"
                f"All trading suspended. Manual review required."
            )
            logger.critical("[MONITOR] %s", msg)
            self.send_alert(msg)
            if self.on_kill:
                self.on_kill(f"drawdown {dd*100:.1f}%")

    def _get_connection(self):
        if self._ib is None or not self._ib.isConnected():
            from ib_insync import IB
            self._ib = IB()
            self._ib.connect("127.0.0.1", 7497, clientId=2)  # separate client ID from ExecutionAgent
        return self._ib
