"""
core/redis_bridge.py — ZEUS → SpendLens intelligence bridge via Upstash Redis.

ZEUS writes four data streams to the shared Upstash Redis instance:

  zeus:macro:latest              — current market regime snapshot (JSON)
  zeus:decision:{trace_id}       — full DecisionTrace per signal (JSON, TTL 7d)
  zeus:decisions:recent          — list of last 50 trace_ids (for SpendLens feed)
  zeus:supplier_risk:{slug}      — Hades compliance result per supplier (JSON, TTL 7d)

SpendLens reads these via its existing HermesClient connection to the same Redis.
Keys use the zeus: namespace so they never collide with hermes: keys.

All writes are fire-and-forget: if Redis is unavailable the pipeline continues.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from core.types import DecisionTrace, FilteredSignal, MacroContext

logger = logging.getLogger("redis_bridge")

_MACRO_KEY          = "zeus:macro:latest"
_DECISIONS_LIST_KEY = "zeus:decisions:recent"
_DECISION_TTL       = 60 * 60 * 24 * 7   # 7 days
_SUPPLIER_TTL       = 60 * 60 * 24 * 7   # 7 days
_MAX_RECENT         = 50


class RedisBridge:
    """
    Writes ZEUS intelligence to Upstash Redis so SpendLens can read it.
    Uses the same upstash_redis client as SpendLens's HermesClient.
    """

    def __init__(
        self,
        url:   Optional[str] = None,
        token: Optional[str] = None,
    ):
        self._url   = url   or os.getenv("UPSTASH_REDIS_REST_URL", "")
        self._token = token or os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self._r     = None
        self._enabled = bool(self._url and self._token)
        if not self._enabled:
            logger.warning("[REDIS-BRIDGE] Upstash credentials missing — bridge disabled.")
        else:
            self._connect()

    # ------------------------------------------------------------------
    # Public write API — called by ZEUS after each pipeline stage
    # ------------------------------------------------------------------

    def push_macro(self, macro: MacroContext) -> None:
        """Write the latest macro snapshot. SpendLens reads this for category strategy context."""
        if not self._enabled:
            return
        payload = {
            "regime":          macro.regime.value if hasattr(macro.regime, "value") else str(macro.regime),
            "vix":             round(macro.vix, 2),
            "sp500_1m_pct":    round(macro.sp500_1m_return * 100, 2),
            "sector_momentum": macro.sector_momentum,
            "updated_at":      datetime.now(timezone.utc).isoformat(),
            "source":          "zeus",
        }
        self._set(_MACRO_KEY, payload)
        logger.debug("[REDIS-BRIDGE] Macro snapshot pushed.")

    def push_decision(self, trace: DecisionTrace) -> None:
        """Write a ZEUS DecisionTrace. SpendLens Icarus AI screen shows ZEUS thinking."""
        if not self._enabled:
            return
        key = f"zeus:decision:{trace.trace_id}"
        payload = {
            "trace_id":          trace.trace_id,
            "signal_id":         trace.signal_id,
            "timestamp":         trace.timestamp.isoformat(),
            "headline":          trace.headline,
            "supplier":          trace.supplier,
            "category":          trace.category,
            "severity":          trace.severity,
            "hades_passed":      trace.hades_passed,
            "hades_notes":       trace.hades_notes,
            "trend_regime":      trace.trend_regime,
            "trend_vix":         trace.trend_vix,
            "pattern_confidence": trace.pattern_confidence,
            "zeus_reasoning":    trace.zeus_reasoning,
            "zeus_approved":     trace.zeus_approved,
            "trade_placed":      trace.trade_placed,
            "symbol":            trace.symbol,
            "side":              trace.side,
            "fill_price":        trace.fill_price,
            "pnl_pct":           trace.pnl_pct,
            "killed_at_stage":   trace.killed_at_stage,
            "kill_reason":       trace.kill_reason,
            "source":            "zeus",
        }
        self._set(key, payload, ttl=_DECISION_TTL)
        # Prepend to recent list, trim to max
        try:
            self._r.lpush(_DECISIONS_LIST_KEY, trace.trace_id)
            self._r.ltrim(_DECISIONS_LIST_KEY, 0, _MAX_RECENT - 1)
        except Exception as exc:
            logger.warning("[REDIS-BRIDGE] decisions list update failed: %s", exc)
        logger.debug("[REDIS-BRIDGE] Decision trace pushed: %s", trace.trace_id)

    def push_supplier_risk(self, signal: FilteredSignal) -> None:
        """
        Write Hades compliance result for a supplier.
        SpendLens reads this to enrich vendor risk profiles.
        """
        if not self._enabled or not signal.supplier:
            return
        slug = signal.supplier.lower().strip().replace(" ", "_").replace("-", "_")
        key  = f"zeus:supplier_risk:{slug}"
        payload = {
            "supplier":          signal.supplier,
            "slug":              slug,
            "compliance_score":  signal.compliance_score,
            "ofac_flag":         signal.ofac_flag,
            "esg_flag":          signal.esg_flag,
            "downgraded":        signal.downgraded,
            "hades_notes":       signal.notes,
            "risk_level":        self._compliance_to_risk(signal.compliance_score, signal.ofac_flag, signal.esg_flag),
            "assessed_at":       datetime.now(timezone.utc).isoformat(),
            "source":            "zeus_hades",
        }
        self._set(key, payload, ttl=_SUPPLIER_TTL)
        logger.debug("[REDIS-BRIDGE] Supplier risk pushed: %s", slug)

    def update_decision_outcome(self, trace_id: str, pnl_pct: float) -> None:
        """Backfill P&L into a stored decision when Monitor closes a trade."""
        if not self._enabled:
            return
        key = f"zeus:decision:{trace_id}"
        try:
            raw = self._r.get(key)
            if raw:
                data = json.loads(raw)
                data["pnl_pct"] = pnl_pct
                data["outcome_updated_at"] = datetime.now(timezone.utc).isoformat()
                self._set(key, data, ttl=_DECISION_TTL)
        except Exception as exc:
            logger.warning("[REDIS-BRIDGE] outcome backfill failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        try:
            from upstash_redis import Redis
            self._r = Redis(url=self._url, token=self._token)
            logger.info("[REDIS-BRIDGE] Connected to Upstash Redis.")
        except Exception as exc:
            logger.warning("[REDIS-BRIDGE] Connection failed: %s", exc)
            self._enabled = False

    def _set(self, key: str, data: dict, ttl: Optional[int] = None) -> None:
        try:
            payload = json.dumps(data, default=str)
            if ttl:
                self._r.setex(key, ttl, payload)
            else:
                self._r.set(key, payload)
        except Exception as exc:
            logger.warning("[REDIS-BRIDGE] write failed for %s: %s", key, exc)

    @staticmethod
    def _compliance_to_risk(score: float, ofac: bool, esg: bool) -> str:
        if ofac:   return "CRITICAL"
        if score < 0.5: return "HIGH"
        if esg:    return "MEDIUM"
        if score < 0.8: return "MEDIUM"
        return "LOW"
