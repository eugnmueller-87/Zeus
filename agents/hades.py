"""
Agent 2 — Hades Risk Filter
Compliance firewall. Imports only from core.types — never from other agents.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.types import AgentHealth, FilteredSignal, RawSignal, SignalCategory
from core.agent_knowledge import AgentKnowledgeBase

logger = logging.getLogger("hades")

_OFAC_BLOCKLIST: set[str] = {"RUSAL", "SBERBANK", "ROSNEFT"}
_ESG_BLOCKLIST:  set[str] = {"tobacco", "weapons", "cluster munition", "coal"}
_BLOCKED_TICKERS: set[str] = set()


class HadesAgent:
    def __init__(
        self,
        ofac_blocklist:    set[str] | None = None,
        esg_blocklist:     set[str] | None = None,
        blocked_tickers:   set[str] | None = None,
    ):
        self._ofac    = ofac_blocklist  or _OFAC_BLOCKLIST
        self._esg     = esg_blocklist   or _ESG_BLOCKLIST
        self._tickers = blocked_tickers or _BLOCKED_TICKERS
        self.kb = AgentKnowledgeBase("hades")

    def health(self) -> AgentHealth:
        return AgentHealth.HEALTHY

    def filter(self, signal: RawSignal) -> Optional[FilteredSignal]:
        notes: list[str] = []
        ofac_hit    = self._check_ofac(signal, notes)
        esg_hit     = self._check_esg(signal, notes)
        ticker_hit  = self._check_tickers(signal, notes)

        if ofac_hit or ticker_hit:
            logger.warning("[HADES] KILL %s — %s", signal.signal_id, "; ".join(notes))
            return None

        compliance_score = 1.0
        downgraded = False
        if esg_hit:
            compliance_score = 0.4
            downgraded = True
            notes.append("ESG flag: severity downgraded")

        logger.info("[HADES] PASS %s compliance=%.2f", signal.signal_id, compliance_score)
        return FilteredSignal(
            original=signal,
            compliance_score=compliance_score,
            esg_flag=esg_hit,
            ofac_flag=ofac_hit,
            downgraded=downgraded,
            notes=notes,
        )

    def _check_ofac(self, signal: RawSignal, notes: list[str]) -> bool:
        text = signal.raw_text.upper()
        for entity in self._ofac:
            if entity.upper() in text:
                notes.append(f"OFAC match: {entity}")
                return True
        return False

    def _check_esg(self, signal: RawSignal, notes: list[str]) -> bool:
        text = signal.raw_text.lower()
        for sector in self._esg:
            if sector in text:
                notes.append(f"ESG sector: {sector}")
                return True
        return False

    def _check_tickers(self, signal: RawSignal, notes: list[str]) -> bool:
        blocked = [t for t in signal.affected_tickers if t in self._tickers]
        if blocked:
            notes.append(f"Blocked tickers: {blocked}")
            return True
        return False
