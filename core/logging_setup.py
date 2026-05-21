"""Structured logging configuration for ZEUS."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("logs")


def configure_logging(level: int = logging.INFO) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_DIR / "zeus.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
    ]
    logging.basicConfig(level=level, format=fmt, handlers=handlers)
