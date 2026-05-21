"""
Mock Execution Agent — drop-in replacement for ExecutionAgent when IB Gateway
is not connected. Simulates fills with realistic slippage. Used for testing
the full ZEUS pipeline before IBKR account is approved.

Swap in via settings.json: "mock_execution": true
"""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass
from typing import Optional

import yfinance as yf

from agents.pattern import SizedSignal

logger = logging.getLogger("execution.mock")


@dataclass
class TradeResult:
    order_id: str
    symbol: str
    side: str
    fill_price: Optional[float]
    qty: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str = "submitted"


class MockExecutionAgent:
    """
    Simulates IB bracket orders using real yfinance prices + random slippage.
    Logs every simulated trade so PatternAgent can learn from mock history.
    All orders are paper — no real money involved.
    """

    ACCOUNT_EQUITY = 100_000.0   # simulated account size

    def __init__(self, slippage_bps: int = 5):
        self.slippage_bps = slippage_bps  # basis points of simulated slippage
        self._pending_orders: list[str] = []
        logger.info("[EXECUTION-MOCK] Initialized — no IB connection required.")

    def place(self, sized: SizedSignal) -> TradeResult:
        tickers = sized.affected_tickers
        if not tickers:
            logger.warning("[EXECUTION-MOCK] No tickers in signal %s — skipping.", sized.signal_id)
            return self._null_result()

        symbol = tickers[0]
        mid = self._get_price(symbol)
        if mid is None:
            logger.warning("[EXECUTION-MOCK] Could not price %s — skipping.", symbol)
            return self._null_result()

        # Apply simulated slippage
        slippage = mid * (self.slippage_bps / 10_000) * random.choice([-1, 1])
        fill_price = round(mid + slippage, 4)

        alloc = self.ACCOUNT_EQUITY * sized.position_size_pct
        qty = max(1, int(alloc / fill_price))

        stop_pct = 0.03
        target_pct = 0.06

        from agents.icarus import SignalCategory
        is_long = sized.category != SignalCategory.SUPPLIER_DISRUPTION
        side = "BUY" if is_long else "SELL"

        stop_price = round(fill_price * (1 - stop_pct if is_long else 1 + stop_pct), 4)
        limit_price = round(fill_price * (1 + target_pct if is_long else 1 - target_pct), 4)

        order_id = str(uuid.uuid4())[:8]
        self._pending_orders.append(order_id)

        logger.info(
            "[EXECUTION-MOCK] SIMULATED %s %d %s @ %.4f | SL=%.4f TP=%.4f | order_id=%s",
            side, qty, symbol, fill_price, stop_price, limit_price, order_id,
        )

        return TradeResult(
            order_id=order_id,
            symbol=symbol,
            side=side,
            fill_price=fill_price,
            qty=qty,
            stop_loss_price=stop_price,
            take_profit_price=limit_price,
            status="simulated",
        )

    def cancel_all_pending(self) -> None:
        logger.info("[EXECUTION-MOCK] Cancelled %d simulated pending orders.", len(self._pending_orders))
        self._pending_orders.clear()

    def _get_price(self, symbol: str) -> Optional[float]:
        try:
            hist = yf.Ticker(symbol).history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as exc:
            logger.warning("[EXECUTION-MOCK] Price fetch failed for %s: %s", symbol, exc)
        return None

    @staticmethod
    def _null_result() -> TradeResult:
        return TradeResult(
            order_id=str(uuid.uuid4())[:8], symbol="", side="",
            fill_price=None, qty=0, status="skipped"
        )
