"""
Agent 3 — Trend Analyzer
Pulls macro context: sector momentum, market regime (bull/bear/sideways), VIX.
Suppresses signals that are valid in isolation but wrong for current macro.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import yfinance as yf

from agents.hades import FilteredSignal

logger = logging.getLogger("trend")


class MarketRegime(str):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


@dataclass
class MacroContext:
    fetched_at: datetime
    regime: str
    vix: float
    sp500_1m_return: float          # S&P 500 1-month return
    sector_momentum: dict[str, float] = field(default_factory=dict)
    suppress: bool = False
    suppress_reason: Optional[str] = None

    @property
    def is_high_volatility(self) -> bool:
        return self.vix > 25.0

    @property
    def is_bear(self) -> bool:
        return self.regime == MarketRegime.BEAR


# VIX thresholds
_VIX_HIGH = 25.0
_VIX_EXTREME = 35.0

# S&P 1-month return thresholds
_BULL_THRESHOLD = 0.02    # +2% → bull
_BEAR_THRESHOLD = -0.03   # -3% → bear


class TrendAgent:
    """
    Fetches market regime data and decides whether a signal should be
    suppressed based on current macro context.
    """

    def __init__(self, cache_ttl_seconds: int = 900):
        self._cache_ttl = cache_ttl_seconds
        self._cached_context: Optional[MacroContext] = None
        self._cache_time: Optional[datetime] = None

    def analyze(self, signal: FilteredSignal) -> MacroContext:
        ctx = self._get_context()
        ctx = self._apply_suppression_logic(ctx, signal)
        return ctx

    # ------------------------------------------------------------------
    # Macro data fetching
    # ------------------------------------------------------------------

    def _get_context(self) -> MacroContext:
        now = datetime.utcnow()
        if self._cached_context and self._cache_time:
            age = (now - self._cache_time).total_seconds()
            if age < self._cache_ttl:
                return self._cached_context

        ctx = self._fetch_macro()
        self._cached_context = ctx
        self._cache_time = now
        return ctx

    def _fetch_macro(self) -> MacroContext:
        vix = self._fetch_vix()
        sp500_return = self._fetch_sp500_return()
        regime = self._classify_regime(sp500_return, vix)
        sector_mom = self._fetch_sector_momentum()

        logger.info(
            "[TREND] Macro snapshot: regime=%s VIX=%.2f SP500_1m=%.2f%%",
            regime, vix, sp500_return * 100,
        )
        return MacroContext(
            fetched_at=datetime.utcnow(),
            regime=regime,
            vix=vix,
            sp500_1m_return=sp500_return,
            sector_momentum=sector_mom,
        )

    def _fetch_vix(self) -> float:
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as exc:
            logger.warning("[TREND] VIX fetch failed: %s", exc)
        return 20.0  # neutral fallback

    def _fetch_sp500_return(self) -> float:
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1mo")
            if len(hist) >= 2:
                start = float(hist["Close"].iloc[0])
                end = float(hist["Close"].iloc[-1])
                return (end - start) / start
        except Exception as exc:
            logger.warning("[TREND] SPY fetch failed: %s", exc)
        return 0.0

    def _fetch_sector_momentum(self) -> dict[str, float]:
        """1-month return for major sector ETFs."""
        sector_etfs = {
            "tech": "XLK", "energy": "XLE", "financials": "XLF",
            "healthcare": "XLV", "industrials": "XLI", "materials": "XLB",
        }
        result: dict[str, float] = {}
        for name, ticker in sector_etfs.items():
            try:
                hist = yf.Ticker(ticker).history(period="1mo")
                if len(hist) >= 2:
                    ret = (float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[0])) / float(hist["Close"].iloc[0])
                    result[name] = round(ret, 4)
            except Exception:
                result[name] = 0.0
        return result

    @staticmethod
    def _classify_regime(sp500_return: float, vix: float) -> str:
        if vix >= _VIX_EXTREME:
            return MarketRegime.BEAR
        if sp500_return >= _BULL_THRESHOLD:
            return MarketRegime.BULL
        if sp500_return <= _BEAR_THRESHOLD:
            return MarketRegime.BEAR
        return MarketRegime.SIDEWAYS

    # ------------------------------------------------------------------
    # Suppression logic
    # ------------------------------------------------------------------

    def _apply_suppression_logic(
        self, ctx: MacroContext, signal: FilteredSignal
    ) -> MacroContext:
        from agents.icarus import SignalCategory

        # Suppress bullish signals in a bear market with high VIX
        if signal.category == SignalCategory.POSITIVE_NEWS:
            if ctx.is_bear and ctx.is_high_volatility:
                ctx.suppress = True
                ctx.suppress_reason = f"Bear regime + VIX={ctx.vix:.1f}: suppressing positive signal"
                return ctx

        # Suppress all signals in extreme volatility (VIX > 35)
        if ctx.vix >= _VIX_EXTREME:
            ctx.suppress = True
            ctx.suppress_reason = f"Extreme VIX={ctx.vix:.1f}: all signals suppressed"
            return ctx

        return ctx
