"""
Agent 1 — Icarus Signal Watcher
Monitors Hermes RSS feeds, classifies events, emits structured RawSignal objects.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import feedparser

logger = logging.getLogger("icarus")


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


# Keywords used for naive classification — replace with LLM call for production
_DISRUPTION_KEYWORDS = {"recall", "shortage", "strike", "disruption", "halt", "ban", "sanction"}
_POSITIVE_KEYWORDS = {"record", "beat", "expansion", "partnership", "breakthrough", "approval"}
_REGULATORY_KEYWORDS = {"sec", "fine", "investigation", "lawsuit", "fdic", "bafin", "antitrust"}


def _classify(text: str) -> tuple[SignalCategory, Severity]:
    lower = text.lower()
    if any(k in lower for k in _DISRUPTION_KEYWORDS):
        return SignalCategory.SUPPLIER_DISRUPTION, Severity.HIGH
    if any(k in lower for k in _REGULATORY_KEYWORDS):
        return SignalCategory.REGULATORY_ACTION, Severity.MEDIUM
    if any(k in lower for k in _POSITIVE_KEYWORDS):
        return SignalCategory.POSITIVE_NEWS, Severity.MEDIUM
    return SignalCategory.NEUTRAL, Severity.LOW


def _extract_tickers(text: str) -> list[str]:
    """
    Naive all-caps word extraction as a ticker hint.
    Replace with NER model or financial NLP for production accuracy.
    """
    import re
    candidates = re.findall(r"\b[A-Z]{2,5}\b", text)
    # Filter out common non-ticker caps words
    stopwords = {"CEO", "CFO", "USA", "EUR", "USD", "GDP", "ETF", "IPO", "SEC", "FDA", "NATO"}
    return [c for c in candidates if c not in stopwords]


def _entry_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class IcarusAgent:
    """
    Pulls RSS feeds and converts entries into RawSignal objects.
    Tracks seen entry IDs to avoid duplicate signals across poll cycles.
    """

    def __init__(self, feed_urls: list[str] | None = None):
        self.feed_urls: list[str] = feed_urls or []
        self._seen: set[str] = set()

    def add_feed(self, url: str) -> None:
        if url not in self.feed_urls:
            self.feed_urls.append(url)

    def fetch(self) -> list[RawSignal]:
        signals: list[RawSignal] = []
        for url in self.feed_urls:
            try:
                signals.extend(self._parse_feed(url))
            except Exception as exc:
                logger.warning("[ICARUS] Failed to parse feed %s: %s", url, exc)
        logger.info("[ICARUS] Fetched %d new signal(s) across %d feed(s).", len(signals), len(self.feed_urls))
        return signals

    def _parse_feed(self, url: str) -> list[RawSignal]:
        feed = feedparser.parse(url)
        results: list[RawSignal] = []
        for entry in feed.entries:
            eid = _entry_id(url, entry.get("title", ""))
            if eid in self._seen:
                continue
            self._seen.add(eid)

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            full_text = f"{title} {summary}"

            category, severity = _classify(full_text)
            if category == SignalCategory.NEUTRAL:
                continue  # skip noise

            published_str = entry.get("published", "")
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except Exception:
                published_at = datetime.utcnow()

            sig = RawSignal(
                signal_id=eid,
                source_url=url,
                headline=title,
                summary=summary,
                published_at=published_at,
                category=category,
                severity=severity,
                affected_tickers=_extract_tickers(full_text),
                raw_text=full_text,
            )
            results.append(sig)
        return results
