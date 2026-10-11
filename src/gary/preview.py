"""Local, synthetic-only preview of the three approved seams."""

import argparse
import json
import os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import stdev
from threading import Lock

from gary.coverage import coverage_report
from gary.patterns import detect_patterns
from gary.portfolio import step_portfolio

STATIC = Path(__file__).with_name("static")
STATE_PATH = Path.cwd() / "private" / "paper-preview-state.json"
LOCK = Lock()


def _initial_state():
    return {"cash": 200000.0, "positions": {}, "initial_capital": 200000.0,
            "next_loss_threshold": 180000.0, "processed_dates": []}


def _read_state():
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else _initial_state()


def _save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, STATE_PATH)


def _demo(state):
    bars = json.loads((STATIC / "demo-bars.json").read_text())["bars"]
    snapshot = json.loads((STATIC / "demo-snapshot.json").read_text())
    signal_date = bars[-1]["date"]
    execution_date = "2026-10-12"
    coverage = coverage_report(snapshot, signal_date)
    signals = detect_patterns(bars, signal_date)
    fresh = [s for s in signals if s["available_at"] == signal_date and s["direction"] == "buy"]
    returns = [bars[i]["close"] / bars[i-1]["close"] - 1 for i in range(1, len(bars))]
    candidates = [{"symbol": snapshot["symbol"], "coverage": coverage, "signal": fresh[-1],
                   "volatility": {"value": stdev(returns), "start": bars[0]["date"],
                                  "end": signal_date, "return_count": len(returns)}}] if fresh else []
    market = {"signal_date": signal_date, "execution_date": execution_date,
              "execution_price_basis": "unadjusted", "closes": {"SYNTH-A": bars[-1]["close"]},
              "opens": {"SYNTH-A": 22.4}, "candidates": candidates, "sell_signals": []}
    result = step_portfolio(state, market, execution_date)
    return {"mode": "synthetic_paper_demo", "experimental_detector": True,
            "signal_date": signal_date, "execution_date": execution_date,
            "coverage": coverage, "signals": signals, "bars": bars, "state": state,
            "proposed_step": result,
            "research": {"price_samples": "8/8", "sec_access": "1/8", "hq_clearances": "0/5",
                         "real_chart_accuracy": "Unmeasured"}}


class Handler(BaseHTTPRequestHandler):
    def _respond(self, data, status=200, content_type="application/json"):
        body = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            if self.path == "/":
                self._respond((STATIC / "index.html").read_bytes(), content_type="text/html; charset=utf-8")
            elif self.path == "/api/demo":
                with LOCK:
                    self._respond(_demo(_read_state()))
            elif self.path == "/health":
                self._respond({"status": "ok", "mode": "synthetic_paper_demo"})
            else:
                self._respond({"error": "not found"}, 404)
        except (ValueError, KeyError, OSError) as exc:
            self._respond({"error": str(exc)}, 400)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}",
                                      f"http://localhost:{self.server.server_port}"}:
            self._respond({"error": "local origin required"}, 403)
            return
        try:
            with LOCK:
                if self.path == "/api/reset":
                    _save_state(_initial_state())
                    self._respond(_demo(_initial_state()))
                elif self.path == "/api/run":
                    demo = _demo(_read_state())
                    _save_state(demo["proposed_step"]["state"])
                    demo["state"] = demo["proposed_step"]["state"]
                    self._respond(demo)
                else:
                    self._respond({"error": "not found"}, 404)
        except (ValueError, KeyError, OSError) as exc:
            self._respond({"error": str(exc)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4175)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Gary.ai synthetic paper preview: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
