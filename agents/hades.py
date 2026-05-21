"""
Agent 2 — Hades Risk Filter
Every signal passes through Hades before reaching trading logic.
OFAC hits, ESG violations, compliance flags → signal killed or downgraded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from agents.icarus import RawSignal, SignalCategory, Severity

logger = logging.getLogger("hades")


@dataclass
class FilteredSignal:
    """A RawSignal that has passed Hades compliance checks."""
    original: RawSignal
    compliance_score: float        # 0.0 (risky) → 1.0 (clean)
    esg_flag: bool = False
    ofac_flag: bool = False
    downgraded: bool = False       # severity was reduced but not killed
    notes: list[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []

    # Convenience passthrough properties
    @property
    def signal_id(self) -> str:
        return self.original.signal_id

    @property
    def affected_tickers(self) -> list[str]:
        return self.original.affected_tickers

    @property
    def category(self) -> SignalCategory:
        return self.original.category

    @property
    def severity(self) -> Severity:
        return self.original.severity

    @property
    def headline(self) -> str:
        return self.original.headline


# ---------------------------------------------------------------------------
# Static blocklists — replace / extend with live OFAC API calls in production
# ---------------------------------------------------------------------------
_OFAC_ENTITY_BLOCKLIST: set[str] = {
    # Placeholder — populate from OFAC SDN list
    "RUSAL", "SBERBANK", "ROSNEFT",
}

_ESG_SECTOR_BLOCKLIST: set[str] = {
    # Sectors you want to avoid for ESG reasons
    "tobacco", "weapons", "cluster munition", "coal",
}

# Tickers known to be high-risk / sanctioned — static examples
_BLOCKED_TICKERS: set[str] = set()


class HadesAgent:
    """
    Compliance firewall. Returns FilteredSignal on pass, None on kill.
    All decisions are logged for audit.
    """

    def __init__(
        self,
        ofac_blocklist: set[str] | None = None,
        esg_blocklist: set[str] | None = None,
        blocked_tickers: set[str] | None = None,
    ):
        self._ofac = ofac_blocklist or _OFAC_ENTITY_BLOCKLIST
        self._esg = esg_blocklist or _ESG_SECTOR_BLOCKLIST
        self._tickers = blocked_tickers or _BLOCKED_TICKERS

    def filter(self, signal: RawSignal) -> Optional[FilteredSignal]:
        notes: list[str] = []
        ofac_hit = self._check_ofac(signal, notes)
        esg_hit = self._check_esg(signal, notes)
        ticker_blocked = self._check_tickers(signal, notes)

        if ofac_hit or ticker_blocked:
            logger.warning(
                "[HADES] KILL signal_id=%s — %s", signal.signal_id, "; ".join(notes)
            )
            return None  # hard kill

        compliance_score = 1.0
        downgraded = False

        if esg_hit:
            compliance_score = 0.4
            downgraded = True
            notes.append("ESG flag: severity downgraded")
            logger.info("[HADES] DOWNGRADE signal_id=%s — ESG concern.", signal.signal_id)

        logger.info(
            "[HADES] PASS signal_id=%s compliance_score=%.2f",
            signal.signal_id,
            compliance_score,
        )
        return FilteredSignal(
            original=signal,
            compliance_score=compliance_score,
            esg_flag=esg_hit,
            ofac_flag=ofac_hit,
            downgraded=downgraded,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Check methods
    # ------------------------------------------------------------------

    def _check_ofac(self, signal: RawSignal, notes: list[str]) -> bool:
        text_upper = signal.raw_text.upper()
        for entity in self._ofac:
            if entity.upper() in text_upper:
                notes.append(f"OFAC entity match: {entity}")
                return True
        return False

    def _check_esg(self, signal: RawSignal, notes: list[str]) -> bool:
        text_lower = signal.raw_text.lower()
        for sector in self._esg:
            if sector in text_lower:
                notes.append(f"ESG sector flag: {sector}")
                return True
        return False

    def _check_tickers(self, signal: RawSignal, notes: list[str]) -> bool:
        blocked = [t for t in signal.affected_tickers if t in self._tickers]
        if blocked:
            notes.append(f"Blocked tickers: {blocked}")
            return True
        return False
