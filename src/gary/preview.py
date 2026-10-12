"""Local, synthetic-only preview of the three approved seams."""

import argparse
import json
import os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import stdev
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from gary.coverage import coverage_report
from gary.patterns import detect_patterns
from gary.portfolio import step_portfolio
from gary.review_preview import CYCLE3, DEFAULT_STUDY, cycle3_study, load_labels, load_queue, reviewer_view, save_label
from gary.training_preview import DEFAULT_TRAINING, TrainingStore
from gary.watch_preview import DEFAULT_WATCH, WatchDesk

STATIC = Path(__file__).with_name("static")
STATE_PATH = Path.cwd() / "private" / "paper-preview-state.json"
LOCK = Lock()
REVIEW_DIRECTORY = DEFAULT_STUDY
REVIEWER_ID = "gary"
CYCLE3_DIRECTORY = None
TRAINING_DIRECTORY = DEFAULT_TRAINING
WATCH_DESK = WatchDesk()

STUDIES = [{"key": "five-year", "title": "Five-year exploration"},
           {"key": "holdout", "title": "Frozen holdout"},
           {"key": "calibration", "title": "Completed calibration"}]


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
    def _review_context(self, query):
        params = parse_qs(query)
        reviewer = params.get("reviewer", [REVIEWER_ID])[0]
        if reviewer != REVIEWER_ID:
            raise PermissionError("Assigned reviewer only")
        if CYCLE3_DIRECTORY is not None:
            key = params.get("study", ["five-year"])[0]
            if key not in {"calibration", "holdout", "holdout-original", "five-year"}:
                raise KeyError("Chart unavailable")
            try:
                directory, queue, readonly = cycle3_study(key, CYCLE3_DIRECTORY)
            except FileNotFoundError:
                raise
            except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
                raise ValueError("Study evidence could not be verified; ask the coordinator to check local artifacts") from exc
            context_available = (CYCLE3_DIRECTORY / "holdout-context" / "queue.json").exists()
            context_exposed = context_available or (CYCLE3_DIRECTORY / "holdout-context" / "exposure.json").exists()
            studies = [{**row, "title": "Holdout · five-year context"} if row["key"] == "holdout" and context_available else row
                       for row in STUDIES]
            if context_exposed:
                studies.append({"key": "holdout-original", "title": "Original holdout · preserved"})
            return directory, queue, {"study_key": key, "read_only": readonly, "studies": studies,
                                      "view_profile": "five-year-assisted-v1" if "context_review" in queue["sealed"] else "original"}
        if params.get("study", ["calibration"])[0] != "calibration":
            raise KeyError("Chart unavailable")
        queue = load_queue(REVIEW_DIRECTORY)
        if queue["schema_version"] != "pattern-review-v1" or queue["sealed"]["config"].get("profile"):
            raise ValueError("This study requires a verified cycle-3 release")
        return REVIEW_DIRECTORY, queue, {
            "study_key": "calibration", "read_only": False,
            "studies": [{"key": "calibration", "title": "Calibration"}]}

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
            route = urlsplit(self.path)
            if route.path.startswith(("/review", "/api/review", "/learn", "/api/training", "/stocks", "/api/stock-lists", "/api/watch")) and not self._local_host():
                self._respond({"error": "local host required"}, 403)
                return
            if route.path == "/learn":
                self._respond((STATIC / "training.html").read_bytes(), content_type="text/html; charset=utf-8")
            elif route.path == "/stocks":
                self._respond((STATIC / "stocks.html").read_bytes(), content_type="text/html; charset=utf-8")
            elif route.path == "/api/stock-lists":
                if route.query:
                    raise ValueError("Unsupported stock-list lookup")
                self._respond(json.loads((STATIC / "stock-lists.json").read_text()) | {"watch": WATCH_DESK.view()})
            elif route.path == "/api/watch":
                if route.query:
                    raise ValueError("Unsupported watch lookup")
                self._respond(WATCH_DESK.view())
            elif route.path in {"/api/training", "/api/training/card"}:
                params = parse_qs(route.query)
                if params.get("reviewer", [REVIEWER_ID])[0] != REVIEWER_ID:
                    raise PermissionError("Assigned reviewer only")
                if set(params) - {"round_id", "reviewer", "case_id"}:
                    raise ValueError("Unsupported training lookup")
                with LOCK:
                    store = TrainingStore(TRAINING_DIRECTORY, REVIEWER_ID)
                    if route.path.endswith("/card"):
                        if not params.get("round_id") or not params.get("case_id"):
                            raise ValueError("Select a round and chart")
                        self._respond(store.card(params["round_id"][0], params["case_id"][0]))
                    else:
                        if "case_id" in params:
                            raise ValueError("Unsupported training lookup")
                        self._respond(store.hub(params.get("round_id", [None])[0]))
            elif route.path == "/review":
                self._respond((STATIC / "review.html").read_bytes(), content_type="text/html; charset=utf-8")
            elif route.path in {"/api/review", "/api/review/card"}:
                query = parse_qs(route.query)
                case = query.get("id", [None])[0] if route.path.endswith("/card") else None
                if route.path.endswith("/card") and case is None:
                    raise ValueError("Select a chart")
                with LOCK:
                    directory, queue, metadata = self._review_context(route.query)
                    self._respond(reviewer_view(queue, load_labels(queue, directory), REVIEWER_ID, case) | metadata)
            elif self.path == "/":
                self._respond((STATIC / "index.html").read_bytes(), content_type="text/html; charset=utf-8")
            elif self.path == "/api/demo":
                with LOCK:
                    self._respond(_demo(_read_state()))
            elif self.path == "/health":
                self._respond({"status": "ok", "mode": "synthetic_paper_demo"})
            else:
                self._respond({"error": "not found"}, 404)
        except PermissionError as exc:
            self._respond({"error": str(exc)}, 403)
        except KeyError:
            self._respond({"error": "Chart unavailable"}, 404)
        except FileNotFoundError:
            self._respond({"error": "No local chart study is available yet"}, 503)
        except (ValueError, OSError) as exc:
            self._respond({"error": str(exc)}, 400)

    def _local_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}",
                                             f"localhost:{self.server.server_port}"}

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self._local_host() or origin and origin not in {f"http://127.0.0.1:{self.server.server_port}",
                                                              f"http://localhost:{self.server.server_port}"}:
            self._respond({"error": "local origin required"}, 403)
            return
        try:
            with LOCK:
                route = urlsplit(self.path)
                if route.path in {"/api/watch/add", "/api/watch/remove", "/api/watch/refresh"}:
                    if route.query:
                        raise ValueError("Unsupported watch mutation lookup")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16384 or self.headers.get_content_type() != "application/json":
                        raise ValueError("A bounded JSON watch request is required")
                    entry = json.loads(self.rfile.read(length))
                    fields = ({"symbol"}, {"symbol", "note"}) if route.path.endswith("/add") else ({"symbol"},)
                    if not isinstance(entry, dict) or set(entry) not in fields:
                        raise ValueError("Only the declared ticker and optional note fields are accepted")
                    if route.path.endswith("/add"):
                        self._respond(WATCH_DESK.add(entry["symbol"], entry.get("note", "")))
                    elif route.path.endswith("/remove"):
                        self._respond(WATCH_DESK.remove(entry["symbol"]))
                    else:
                        WATCH_DESK.refresh(entry["symbol"])
                        self._respond(WATCH_DESK.view())
                elif route.path in {"/api/training/round", "/api/training/label"}:
                    if route.query:
                        raise ValueError("Unsupported training mutation lookup")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16384 or self.headers.get_content_type() != "application/json":
                        raise ValueError("A bounded JSON training request is required")
                    entry = json.loads(self.rfile.read(length))
                    store = TrainingStore(TRAINING_DIRECTORY, REVIEWER_ID)
                    if route.path.endswith("/round"):
                        if not isinstance(entry, dict) or set(entry) != {"request_id"}:
                            raise ValueError("Only a request id is accepted")
                        self._respond(store.request_round(entry["request_id"]))
                    else:
                        if not isinstance(entry, dict) or set(entry) != {"round_id", "case_id", "reviewer_id", "decision", "rationale", "events", "expected_revision", "revise", "view_token"}:
                            raise ValueError("A bounded training label envelope is required")
                        if entry["reviewer_id"] != REVIEWER_ID:
                            raise PermissionError("Assigned reviewer only")
                        round_id = entry.pop("round_id")
                        self._respond(store.save_label(round_id, entry))
                elif route.path == "/api/review/label":
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16384 or self.headers.get_content_type() != "application/json":
                        raise ValueError("A bounded JSON label is required")
                    entry = json.loads(self.rfile.read(length))
                    if not isinstance(entry, dict):
                        raise ValueError("A label object is required")
                    if entry.get("reviewer_id") != REVIEWER_ID:
                        self._respond({"error": "Assigned reviewer only"}, 403)
                        return
                    directory, queue, metadata = self._review_context(route.query)
                    if metadata["read_only"]:
                        raise PermissionError("This original review pass is preserved and read-only")
                    if metadata.get("view_profile") == "five-year-assisted-v1" and entry.get("view_token") != queue["queue_hash"]:
                        raise ValueError("This chart view has changed. Reload it before saving your judgment.")
                    labels = save_label(queue, entry, directory)
                    self._respond(reviewer_view(queue, labels, entry["reviewer_id"], entry["case_id"]) | metadata)
                elif self.path == "/api/reset":
                    _save_state(_initial_state())
                    self._respond(_demo(_initial_state()))
                elif self.path == "/api/run":
                    demo = _demo(_read_state())
                    _save_state(demo["proposed_step"]["state"])
                    demo["state"] = demo["proposed_step"]["state"]
                    self._respond(demo)
                else:
                    self._respond({"error": "not found"}, 404)
        except PermissionError as exc:
            self._respond({"error": str(exc)}, 403)
        except FileNotFoundError:
            self._respond({"error": "No released local chart study is available yet"}, 503)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            self._respond({"error": str(exc)}, 400)


def main():
    global REVIEW_DIRECTORY, REVIEWER_ID, CYCLE3_DIRECTORY, TRAINING_DIRECTORY, WATCH_DESK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4175)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--reviewer", default="gary", help="bind the review server to one declared reviewer")
    parser.add_argument("--cycle-3", action="store_true", help="serve released holdout and five-year studies")
    parser.add_argument("--cycle-3-dir", type=Path, default=CYCLE3)
    parser.add_argument("--training-dir", type=Path, default=DEFAULT_TRAINING)
    parser.add_argument("--watch-dir", type=Path, default=DEFAULT_WATCH, help="operator-only private watch directory")
    args = parser.parse_args()
    REVIEW_DIRECTORY = args.study_dir
    REVIEWER_ID = args.reviewer
    CYCLE3_DIRECTORY = args.cycle_3_dir if args.cycle_3 else None
    TRAINING_DIRECTORY = args.training_dir
    WATCH_DESK = WatchDesk(args.watch_dir)
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
