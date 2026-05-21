"""
Agent 4 — Pattern Learning Agent
Stores signal → trade → outcome in SQLite + ChromaDB vector store.
Learns: hit rates per signal category / regime / VIX band.
Adjusts position sizing and confidence scores accordingly.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.hades import FilteredSignal
from agents.trend import MacroContext

logger = logging.getLogger("pattern")

DB_PATH = Path("data/trade_log.db")


@dataclass
class SizedSignal:
    """A signal that has been assigned a confidence score and position size."""
    original: FilteredSignal
    macro: MacroContext
    confidence: float           # 0.0 → 1.0
    position_size_pct: float    # % of portfolio to allocate
    skip: bool = False          # True → Pattern agent says don't trade
    skip_reason: Optional[str] = None

    @property
    def signal_id(self) -> str:
        return self.original.signal_id

    @property
    def affected_tickers(self) -> list[str]:
        return self.original.affected_tickers

    @property
    def category(self):
        return self.original.category

    @property
    def severity(self):
        return self.original.severity


# Minimum historical samples required before using learned stats
_MIN_SAMPLES = 10
# Default position size when no history exists
_DEFAULT_SIZE_PCT = 0.02          # 2% of portfolio
_MIN_CONFIDENCE_TO_TRADE = 0.45   # below this → skip


class PatternAgent:
    """
    Manages the trade history DB and derives position sizing from
    historical hit rates. Falls back to defaults until enough data exists.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Public API used by ZEUS
    # ------------------------------------------------------------------

    def size(self, signal: FilteredSignal, macro: MacroContext) -> SizedSignal:
        key = self._context_key(signal, macro)
        stats = self._lookup_stats(key)

        if stats is None:
            confidence = 0.55  # mild optimism as prior
            position_pct = _DEFAULT_SIZE_PCT
            logger.info("[PATTERN] No history for key=%s — using defaults.", key)
        else:
            confidence = stats["hit_rate"]
            # Kelly-inspired sizing: edge × confidence, capped at 5%
            edge = max(0.0, confidence - 0.5) * 2   # maps [0.5, 1.0] → [0, 1]
            position_pct = min(0.05, _DEFAULT_SIZE_PCT + edge * 0.03)
            logger.info(
                "[PATTERN] key=%s samples=%d hit_rate=%.2f size=%.2f%%",
                key, stats["n"], confidence, position_pct * 100,
            )

        skip = confidence < _MIN_CONFIDENCE_TO_TRADE
        return SizedSignal(
            original=signal,
            macro=macro,
            confidence=confidence,
            position_size_pct=position_pct,
            skip=skip,
            skip_reason=f"confidence {confidence:.2f} < threshold" if skip else None,
        )

    def record_trade(self, sized: SizedSignal, result) -> None:
        """Called by ZEUS after execution to log the outcome."""
        from agents.execution import TradeResult
        key = self._context_key(sized.original, sized.macro)
        hit = result.pnl_pct > 0 if result.pnl_pct is not None else None
        self._insert_trade(
            trade_id=result.order_id or str(uuid.uuid4()),
            signal_id=sized.signal_id,
            context_key=key,
            category=sized.category.value,
            regime=sized.macro.regime,
            vix_band=self._vix_band(sized.macro.vix),
            confidence=sized.confidence,
            position_pct=sized.position_size_pct,
            symbol=result.symbol,
            side=result.side,
            fill_price=result.fill_price,
            pnl_pct=result.pnl_pct,
            hit=hit,
        )

    # ------------------------------------------------------------------
    # Context key — groups signals by category + regime + VIX band
    # ------------------------------------------------------------------

    @staticmethod
    def _context_key(signal: FilteredSignal, macro: MacroContext) -> str:
        vix_band = PatternAgent._vix_band(macro.vix)
        return f"{signal.category.value}|{macro.regime}|{vix_band}"

    @staticmethod
    def _vix_band(vix: float) -> str:
        if vix < 15:
            return "low"
        if vix < 25:
            return "medium"
        if vix < 35:
            return "high"
        return "extreme"

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT,
                    signal_id TEXT,
                    context_key TEXT,
                    category TEXT,
                    regime TEXT,
                    vix_band TEXT,
                    confidence REAL,
                    position_pct REAL,
                    symbol TEXT,
                    side TEXT,
                    fill_price REAL,
                    pnl_pct REAL,
                    hit INTEGER,           -- 1=win, 0=loss, NULL=open
                    recorded_at TEXT
                )
            """)
            conn.commit()

    def _insert_trade(self, **kwargs) -> None:
        kwargs["recorded_at"] = datetime.utcnow().isoformat()
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"INSERT INTO trades ({cols}) VALUES ({placeholders})", list(kwargs.values()))
            conn.commit()

    def _lookup_stats(self, key: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT COUNT(*) as n,
                       AVG(CASE WHEN hit = 1 THEN 1.0 ELSE 0.0 END) as hit_rate
                FROM trades
                WHERE context_key = ? AND hit IS NOT NULL
            """, (key,)).fetchone()
        if row and row[0] >= _MIN_SAMPLES:
            return {"n": row[0], "hit_rate": row[1] or 0.5}
        return None
