"""
ZEUS — Main Entry Point

Two run modes:
  1. n8n webhook server (default) — n8n triggers ZEUS via HTTP POST
  2. Standalone loop — python main.py --standalone (for local testing)

n8n calls POST /run  → ZEUS executes one pipeline cycle
n8n calls POST /halt → ZEUS halts trading immediately
n8n calls GET  /status → returns portfolio state as JSON
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from agents.zeus import ZeusOrchestrator, ZeusConfig
from core.logging_setup import configure_logging
from config.settings import load_settings

logger = logging.getLogger("main")


def build_zeus() -> ZeusOrchestrator:
    settings = load_settings()
    config = ZeusConfig(
        max_portfolio_drawdown_pct=settings.get("max_drawdown_pct", 0.08),
        max_open_positions=settings.get("max_open_positions", 10),
        paper_trading=settings.get("paper_trading", True),
        mock_execution=settings.get("mock_execution", True),
    )
    zeus = ZeusOrchestrator(config)

    # Point Icarus at the live Hermes instance
    import os
    zeus.icarus._base_url = settings.get("hermes_base_url", "https://hermes-agent-production-114e.up.railway.app")
    if not zeus.icarus._api_key:
        zeus.icarus._api_key = os.getenv("HERMES_API_KEY", "")

    return zeus


# ---------------------------------------------------------------------------
# n8n Webhook Server
# ---------------------------------------------------------------------------

_zeus: ZeusOrchestrator | None = None


class ZeusHandler(BaseHTTPRequestHandler):
    """
    Minimal HTTP server so n8n can trigger ZEUS pipeline runs.

    n8n workflow example:
      Trigger (Cron every 15min) → HTTP Request node → POST http://localhost:8080/run
    """

    def log_message(self, format, *args):
        logger.debug("HTTP %s", format % args)

    def do_GET(self):
        if self.path == "/status":
            self._handle_status()
        elif self.path == "/health":
            self._json_response(200, {"status": "ok"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/run":
            self._handle_run()
        elif self.path == "/halt":
            self._handle_halt()
        else:
            self._json_response(404, {"error": "not found"})

    def _handle_run(self):
        global _zeus
        try:
            runs = _zeus.run_once()
            summary = [
                {
                    "run_id": r.run_id,
                    "killed_at": r.killed_at_stage,
                    "kill_reason": r.kill_reason,
                    "trade": {
                        "symbol": r.trade_result.symbol,
                        "side": r.trade_result.side,
                        "order_id": r.trade_result.order_id,
                    } if r.trade_result else None,
                }
                for r in runs
            ]
            self._json_response(200, {"pipeline_runs": summary, "count": len(runs)})
        except Exception as exc:
            logger.exception("[MAIN] /run failed")
            self._json_response(500, {"error": str(exc)})

    def _handle_halt(self):
        global _zeus
        _zeus.halt(reason="n8n manual halt")
        self._json_response(200, {"status": "halted"})

    def _handle_status(self):
        global _zeus
        state = _zeus.monitor._state
        self._json_response(200, {
            "pipeline_status": _zeus.status.value,
            "open_positions": _zeus.monitor.open_position_count(),
            "equity": state.total_equity,
            "drawdown_pct": round(state.current_drawdown_pct * 100, 2),
            "paper_trading": _zeus.config.paper_trading,
        })

    def _json_response(self, code: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)


def run_webhook_server(host: str = "0.0.0.0", port: int = 8080):
    global _zeus
    _zeus = build_zeus()
    server = HTTPServer((host, port), ZeusHandler)
    logger.info("[MAIN] ZEUS webhook server listening on %s:%d", host, port)
    logger.info("[MAIN] n8n → POST http://localhost:%d/run  to trigger a pipeline cycle", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[MAIN] Shutting down.")


# ---------------------------------------------------------------------------
# Standalone loop (for local testing without n8n)
# ---------------------------------------------------------------------------

def run_standalone(interval_seconds: int = 900):
    zeus = build_zeus()
    logger.info("[MAIN] Standalone mode — polling every %ds", interval_seconds)
    while True:
        try:
            runs = zeus.run_once()
            logger.info("[MAIN] Cycle complete — %d pipeline run(s).", len(runs))
        except Exception as exc:
            logger.exception("[MAIN] Cycle error: %s", exc)
        time.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    configure_logging()
    parser = argparse.ArgumentParser(description="ZEUS Trading Orchestrator")
    parser.add_argument("--standalone", action="store_true", help="Run polling loop instead of webhook server")
    parser.add_argument("--interval", type=int, default=900, help="Polling interval in seconds (standalone mode)")
    parser.add_argument("--port", type=int, default=8080, help="Webhook server port")
    args = parser.parse_args()

    if args.standalone:
        run_standalone(interval_seconds=args.interval)
    else:
        run_webhook_server(port=args.port)
