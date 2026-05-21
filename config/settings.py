"""
Load ZEUS runtime settings from config/settings.json.
Provides typed defaults so the system runs out of the box.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS: dict[str, Any] = {
    "paper_trading": True,
    "mock_execution": True,
    "max_drawdown_pct": 0.08,
    "max_open_positions": 10,
    "poll_interval_seconds": 900,
    "webhook_port": 8080,
    "hermes_feeds": [],
    "ib_host": "127.0.0.1",
    "ib_paper_port": 7497,
    "ib_live_port": 7496,
}


def load_settings() -> dict[str, Any]:
    if _SETTINGS_FILE.exists():
        with open(_SETTINGS_FILE, encoding="utf-8") as f:
            user = json.load(f)
        return {**_DEFAULTS, **user}
    return dict(_DEFAULTS)
