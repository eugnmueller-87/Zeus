"""
Agent 5 — Execution Agent
Places trades via Interactive Brokers (ib_insync) for German residents.
Supports paper trading mode. Handles entry, stop-loss, take-profit automatically.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from agents.pattern import SizedSignal

logger = logging.getLogger("execution")


@dataclass
class TradeResult:
    order_id: str
    symbol: str
    side: str                   # "BUY" | "SELL"
    fill_price: Optional[float]
    qty: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    pnl_pct: Optional[float] = None   # populated later by MonitorAgent
    status: str = "submitted"


class ExecutionAgent:
    """
    Wraps Interactive Brokers via ib_insync.
    Paper mode → connects to IB paper trading port (7497).
    Live mode  → connects to IB live port (7496). Requires explicit opt-in.
    """

    IB_PAPER_PORT = 7497
    IB_LIVE_PORT = 7496

    def __init__(self, paper: bool = True, host: str = "127.0.0.1"):
        self.paper = paper
        self.host = host
        self.port = self.IB_PAPER_PORT if paper else self.IB_LIVE_PORT
        self._ib = None          # ib_insync.IB instance, connected lazily
        self._pending_orders: list[str] = []

        mode = "PAPER" if paper else "LIVE"
        logger.info("[EXECUTION] Initialized in %s mode — port %d", mode, self.port)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place(self, sized: SizedSignal) -> TradeResult:
        """
        Place a bracket order (entry + stop-loss + take-profit) for each
        ticker in the signal. Returns the first result for single-ticker
        signals, raises if tickers list is empty.
        """
        tickers = sized.affected_tickers
        if not tickers:
            logger.warning("[EXECUTION] No tickers in signal %s — skipping.", sized.signal_id)
            return self._null_result()

        symbol = tickers[0]  # primary ticker
        ib = self._get_connection()

        try:
            result = self._place_bracket(ib, symbol, sized)
            self._pending_orders.append(result.order_id)
            return result
        except Exception as exc:
            logger.error("[EXECUTION] Order failed for %s: %s", symbol, exc)
            return self._error_result(symbol, exc)

    def cancel_all_pending(self) -> None:
        """Called by ZEUS on halt to cancel open orders."""
        ib = self._get_connection()
        try:
            from ib_insync import IB
            open_trades = ib.openTrades()
            for trade in open_trades:
                ib.cancelOrder(trade.order)
            logger.warning("[EXECUTION] Cancelled %d open order(s).", len(open_trades))
        except Exception as exc:
            logger.error("[EXECUTION] cancel_all_pending failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _place_bracket(self, ib, symbol: str, sized: SizedSignal) -> TradeResult:
        from ib_insync import Stock, MarketOrder, LimitOrder, StopOrder, util

        contract = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(contract)

        # Fetch current price to compute qty and bracket levels
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(1)
        mid = ticker.midpoint() or ticker.last or ticker.close
        ib.cancelMktData(contract)

        if not mid or mid <= 0:
            raise ValueError(f"Could not get price for {symbol}")

        # Position sizing: % of account equity
        account_val = self._get_account_value(ib)
        alloc = account_val * sized.position_size_pct
        qty = max(1, int(alloc / mid))

        stop_pct = 0.03       # 3% stop-loss
        target_pct = 0.06     # 6% take-profit (2:1 R/R)

        from agents.icarus import SignalCategory
        is_long = sized.category != SignalCategory.SUPPLIER_DISRUPTION

        if is_long:
            side = "BUY"
            stop_price = round(mid * (1 - stop_pct), 2)
            limit_price = round(mid * (1 + target_pct), 2)
        else:
            side = "SELL"
            stop_price = round(mid * (1 + stop_pct), 2)
            limit_price = round(mid * (1 - target_pct), 2)

        bracket = ib.bracketOrder(side, qty, mid, limit_price, stop_price)
        for o in bracket:
            ib.placeOrder(contract, o)

        parent_id = str(bracket[0].orderId)
        logger.info(
            "[EXECUTION] %s %d %s @ ~%.2f | SL=%.2f TP=%.2f | order_id=%s",
            side, qty, symbol, mid, stop_price, limit_price, parent_id,
        )
        return TradeResult(
            order_id=parent_id,
            symbol=symbol,
            side=side,
            fill_price=mid,
            qty=qty,
            stop_loss_price=stop_price,
            take_profit_price=limit_price,
        )

    def _get_account_value(self, ib) -> float:
        try:
            account_vals = ib.accountValues()
            for av in account_vals:
                if av.tag == "NetLiquidation" and av.currency == "BASE":
                    return float(av.value)
        except Exception:
            pass
        return 100_000.0  # fallback for paper accounts

    def _get_connection(self):
        if self._ib is None or not self._ib.isConnected():
            try:
                from ib_insync import IB
                self._ib = IB()
                self._ib.connect(self.host, self.port, clientId=1)
                logger.info("[EXECUTION] Connected to IB %s:%d", self.host, self.port)
            except Exception as exc:
                logger.error("[EXECUTION] IB connection failed: %s", exc)
                raise
        return self._ib

    @staticmethod
    def _null_result() -> TradeResult:
        return TradeResult(
            order_id=str(uuid.uuid4()), symbol="", side="", fill_price=None, qty=0, status="skipped"
        )

    @staticmethod
    def _error_result(symbol: str, exc: Exception) -> TradeResult:
        return TradeResult(
            order_id=str(uuid.uuid4()), symbol=symbol, side="", fill_price=None, qty=0,
            status=f"error: {exc}"
        )
