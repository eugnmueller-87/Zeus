"""
Shared pytest fixtures and configuration for ZEUS quality gate.

Isolation rules:
  - No network calls in any test (mock yfinance, mock Redis)
  - No real filesystem paths (use tmp_path fixture)
  - No ANTHROPIC_API_KEY, HERMES_API_KEY, or Upstash credentials needed
  - Tests must pass cold (no data/chroma or data/trade_log.db on disk)
"""

import os
import pytest

# Block any accidental real API calls during tests
os.environ.setdefault("ANTHROPIC_API_KEY",        "test-key-not-real")
os.environ.setdefault("HERMES_API_KEY",            "test-key-not-real")
os.environ.setdefault("UPSTASH_REDIS_REST_URL",    "https://mock-redis.upstash.io")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN",  "mock-token")
