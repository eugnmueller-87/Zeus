"""
Full pipeline smoke test — no IB Gateway required.
Injects a fake RawSignal and runs it through Hades → Trend → Pattern → MockExecution.
Run with: python test_pipeline.py
"""

from __future__ import annotations

import logging
from datetime import datetime

from core.logging_setup import configure_logging
configure_logging(logging.DEBUG)

from agents.icarus import RawSignal, SignalCategory, Severity
from agents.hades import HadesAgent
from agents.trend import TrendAgent
from agents.pattern import PatternAgent
from agents.execution_mock import MockExecutionAgent

logger = logging.getLogger("test")


def make_test_signal(category: SignalCategory, tickers: list[str]) -> RawSignal:
    return RawSignal(
        signal_id="test-001",
        source_url="https://example.com/feed",
        headline=f"Test signal: {category.value}",
        summary="Simulated event for pipeline smoke test.",
        published_at=datetime.utcnow(),
        category=category,
        severity=Severity.HIGH,
        affected_tickers=tickers,
        raw_text=f"Test signal {category.value} affecting {' '.join(tickers)}",
    )


def run_test():
    print("\n" + "="*60)
    print("  ZEUS Pipeline Smoke Test")
    print("="*60 + "\n")

    hades = HadesAgent()
    trend = TrendAgent()
    pattern = PatternAgent()
    execution = MockExecutionAgent()

    # --- Test 1: Clean positive signal (should pass all stages) ---
    print("[TEST 1] Positive signal on AAPL — expect: PASS all stages\n")
    raw = make_test_signal(SignalCategory.POSITIVE_NEWS, ["AAPL"])

    filtered = hades.filter(raw)
    if filtered is None:
        print("  FAIL: Hades killed a clean signal.")
        return
    print(f"  Hades PASS — compliance_score={filtered.compliance_score:.2f}")

    macro = trend.analyze(filtered)
    if macro.suppress:
        print(f"  Trend SUPPRESSED — {macro.suppress_reason}")
    else:
        print(f"  Trend PASS — regime={macro.regime} VIX={macro.vix:.1f}")

    sized = pattern.size(filtered, macro)
    print(f"  Pattern — confidence={sized.confidence:.2f} size={sized.position_size_pct*100:.2f}% skip={sized.skip}")

    if not sized.skip:
        result = execution.place(sized)
        print(f"  Execution — {result.side} {result.symbol} @ {result.fill_price} | order_id={result.order_id}")
        pattern.record_trade(sized, result)

    # --- Test 2: OFAC-blocked signal ---
    print("\n[TEST 2] Signal mentioning RUSAL — expect: Hades KILL\n")
    raw2 = RawSignal(
        signal_id="test-002",
        source_url="https://example.com/feed",
        headline="RUSAL announces production expansion",
        summary="RUSAL expands aluminium output.",
        published_at=datetime.utcnow(),
        category=SignalCategory.POSITIVE_NEWS,
        severity=Severity.MEDIUM,
        affected_tickers=["RUAL"],
        raw_text="RUSAL announces record aluminium production in Q1",
    )
    result2 = hades.filter(raw2)
    print(f"  Hades result: {'KILL (correct)' if result2 is None else 'PASS (unexpected)'}")

    # --- Test 3: Supplier disruption (short signal) ---
    print("\n[TEST 3] Supplier disruption on TSMC — expect: short trade\n")
    raw3 = make_test_signal(SignalCategory.SUPPLIER_DISRUPTION, ["TSM"])
    filtered3 = hades.filter(raw3)
    if filtered3:
        macro3 = trend.analyze(filtered3)
        sized3 = pattern.size(filtered3, macro3)
        if not sized3.skip and not macro3.suppress:
            result3 = execution.place(sized3)
            print(f"  Execution — {result3.side} {result3.symbol} @ {result3.fill_price}")

    print("\n" + "="*60)
    print("  Smoke test complete. Check logs above for details.")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_test()
