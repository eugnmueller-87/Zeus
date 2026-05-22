"""
Agent 1 — Icarus Signal Watcher
Pulls classified signals directly from Hermes (live on Railway).
No RSS parsing — Hermes already crawls 590+ suppliers across 17 categories
and classifies every signal via Claude Haiku. Icarus just translates.

Hermes base URL: https://hermes-agent-production-114e.up.railway.app
Auth: x-api-key header (HERMES_API_KEY env var)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import requests

logger = logging.getLogger("icarus")

HERMES_BASE_URL = "https://hermes-agent-production-114e.up.railway.app"


class SignalCategory(Enum):
    SUPPLIER_DISRUPTION = "supplier_disruption"
    POSITIVE_NEWS = "positive_news"
    EARNINGS_SURPRISE = "earnings_surprise"
    REGULATORY_ACTION = "regulatory_action"
    MACRO_SHIFT = "macro_shift"
    NEUTRAL = "neutral"


class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RawSignal:
    signal_id: str
    source_url: str
    headline: str
    summary: str
    published_at: datetime
    category: SignalCategory
    severity: Severity
    affected_tickers: list[str] = field(default_factory=list)
    raw_text: str = ""
    supplier: str = ""          # Hermes supplier name (e.g. "NVIDIA")
    hermes_signal_type: str = ""


# Maps Hermes 11 signal types → ZEUS SignalCategory
_HERMES_TYPE_MAP: dict[str, SignalCategory] = {
    "SUPPLY_CHAIN":     SignalCategory.SUPPLIER_DISRUPTION,
    "REGULATORY":       SignalCategory.REGULATORY_ACTION,
    "EARNINGS":         SignalCategory.EARNINGS_SURPRISE,
    "PRICING_CHANGE":   SignalCategory.SUPPLIER_DISRUPTION,
    "LAYOFFS_HIRING":   SignalCategory.MACRO_SHIFT,
    "ACQUISITION":      SignalCategory.POSITIVE_NEWS,
    "FUNDING":          SignalCategory.POSITIVE_NEWS,
    "PRODUCT_RELEASE":  SignalCategory.POSITIVE_NEWS,
    "PARTNERSHIP":      SignalCategory.POSITIVE_NEWS,
    "RESEARCH_PAPER":   SignalCategory.NEUTRAL,
    "OTHER":            SignalCategory.NEUTRAL,
}

# Hermes urgency → ZEUS Severity
_URGENCY_MAP: dict[str, Severity] = {
    "HIGH":   Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW":    Severity.LOW,
}

# Hermes supplier name → likely stock ticker (expand as needed)
_SUPPLIER_TICKER_MAP: dict[str, str] = {
    "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT",
    "Amazon": "AMZN", "Tesla": "TSLA", "Intel": "INTC",
    "TSMC": "TSM", "Samsung": "SSNLF", "Qualcomm": "QCOM",
    "BASF": "BASFY", "Siemens": "SIEGY", "SAP": "SAP",
    "Deutsche Telekom": "DTEGY", "Volkswagen": "VWAGY",
    "BMW": "BMWYY", "Mercedes-Benz": "MBGYY",
}


def _map_signal(item: dict) -> Optional[RawSignal]:
    """Convert one Hermes item dict into a RawSignal. Returns None for neutral/noise."""
    signal_type = item.get("signal_type", "OTHER")
    category = _HERMES_TYPE_MAP.get(signal_type, SignalCategory.NEUTRAL)
    if category == SignalCategory.NEUTRAL:
        return None

    urgency = item.get("urgency", "LOW")
    severity = _URGENCY_MAP.get(urgency, Severity.LOW)

    # Bump to CRITICAL if Hermes marked it significant + HIGH urgency
    if item.get("is_significant") and urgency == "HIGH":
        severity = Severity.CRITICAL

    supplier = item.get("supplier", "")
    ticker = _SUPPLIER_TICKER_MAP.get(supplier)
    tickers = [ticker] if ticker else []

    try:
        published_at = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
    except Exception:
        published_at = datetime.utcnow()

    return RawSignal(
        signal_id=item.get("id", ""),
        source_url=item.get("url", ""),
        headline=item.get("title", ""),
        summary=item.get("summary", ""),
        published_at=published_at,
        category=category,
        severity=severity,
        affected_tickers=tickers,
        raw_text=f"{item.get('title', '')} {item.get('summary', '')}",
        supplier=supplier,
        hermes_signal_type=signal_type,
    )


class IcarusAgent:
    """
    Fetches pre-classified signals from Hermes via HTTP.
    Uses /briefing for top cross-supplier signals each cycle.
    Deduplicates by signal ID across poll cycles.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = HERMES_BASE_URL):
        self._api_key = api_key or os.getenv("HERMES_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._seen: set[str] = set()

        if not self._api_key:
            logger.warning("[ICARUS] HERMES_API_KEY not set — requests will be rejected.")

    @property
    def _headers(self) -> dict:
        return {"x-api-key": self._api_key}

    def fetch(self) -> list[RawSignal]:
        """Main poll — returns new significant signals from Hermes /briefing."""
        signals: list[RawSignal] = []
        try:
            signals = self._fetch_briefing()
        except Exception as exc:
            logger.error("[ICARUS] Hermes /briefing failed: %s", exc)

        logger.info("[ICARUS] %d new signal(s) from Hermes.", len(signals))
        return signals

    def fetch_company(self, company: str) -> list[RawSignal]:
        """On-demand pull for a specific supplier by name."""
        try:
            resp = requests.get(
                f"{self._base_url}/query/{company}",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return self._parse_items(items)
        except Exception as exc:
            logger.error("[ICARUS] Hermes /query/%s failed: %s", company, exc)
            return []

    def search(self, query: str) -> list[RawSignal]:
        """Semantic search across all Hermes signals."""
        try:
            resp = requests.get(
                f"{self._base_url}/search",
                headers=self._headers,
                params={"q": query},
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("results", [])
            return self._parse_items(items)
        except Exception as exc:
            logger.error("[ICARUS] Hermes /search failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_briefing(self) -> list[RawSignal]:
        resp = requests.get(
            f"{self._base_url}/briefing",
            headers=self._headers,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        # /briefing returns {"signals": [...]} or {"items": [...]}
        items = data.get("signals", data.get("items", []))
        return self._parse_items(items)

    def _parse_items(self, items: list[dict]) -> list[RawSignal]:
        results: list[RawSignal] = []
        for item in items:
            sid = item.get("id", "")
            if sid in self._seen:
                continue
            self._seen.add(sid)

            sig = _map_signal(item)
            if sig is not None:
                results.append(sig)
        return results
