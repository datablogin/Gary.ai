"""Private manual membership with evidence-derived stock assessments."""

from datetime import date, datetime, time, timezone
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
from math import isfinite
import os
from pathlib import Path
import re
import tempfile

from gary.coverage import coverage_report, NEW_YORK
from gary.patterns_v2 import VERSION, PARAMETER_HASH


CHECK_KEYS = ("classification", "pe", "yield", "quarterly_revenue", "management", "entry", "allocation")
NUMERIC_RULES = {
    "pe": ("trailing_pe", lambda value: 0 < value < 30, "P/E must be positive and below 30"),
    "yield": ("dividend_yield", lambda value: value > 0.02, "Dividend yield must exceed 2%"),
    "quarterly_revenue": ("revenue_growth", lambda value: value > 0.15, "Quarterly revenue growth must exceed 15%"),
}
SIGNAL_DIRECTIONS = {"breaking_out": "buy", "inverse_head_shoulders": "buy", "cup_handle": "buy",
                     "rolling_over": "sell", "head_shoulders_top": "sell", "gapping_up": "observation"}


def _finite(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        return False


def _display_value(field, value):
    return f"{value:.2f}" if field == "trailing_pe" else f"{value:.2%}"


def _valid_event(event, as_of):
    try:
        if not isinstance(event, dict) or event.get("kind") not in SIGNAL_DIRECTIONS:
            return False
        if event.get("direction") != SIGNAL_DIRECTIONS[event["kind"]] or event.get("status") != "completed":
            return False
        if event.get("detector_version") != VERSION or event.get("parameter_hash") != PARAMETER_HASH:
            return False
        available = date.fromisoformat(event["available_at"])
        if event["completion_date"] != event["available_at"] or event["window_end"] != event["available_at"]:
            return False
        if not date.fromisoformat(event["window_start"]) <= available <= date.fromisoformat(as_of):
            return False
        if not _finite(event.get("breakout_level")) or event["breakout_level"] <= 0:
            return False
        pivots, checks = event["pivots"], event["checks"]
        if not isinstance(pivots, list) or not pivots or not isinstance(checks, dict) or not checks:
            return False
        if any(not _finite(value) and not (key == "breakout_volume_ratio" and value is None) for key, value in checks.items()):
            return False
        for pivot in pivots:
            if not isinstance(pivot, dict) or not isinstance(pivot.get("role"), str) or not pivot["role"].strip():
                return False
            if not _finite(pivot.get("price")) or pivot["price"] <= 0:
                return False
            if not date.fromisoformat(pivot["date"]) <= date.fromisoformat(pivot["confirmed_on"]) <= available:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _refresh_status(record, as_of):
    if record.get("chart_cutoff") is None or record.get("checked_at") is None:
        return "missing"
    try:
        chart_date = date.fromisoformat(record["chart_cutoff"])
        cutoff_date = date.fromisoformat(as_of)
        checked = datetime.fromisoformat(record["checked_at"])
        if checked.tzinfo is None or chart_date > cutoff_date:
            return "unreviewed"
        if chart_date < cutoff_date or checked < datetime.combine(cutoff_date, time(16), NEW_YORK):
            return "stale"
        return "pass"
    except (TypeError, ValueError):
        return "unreviewed"


def _assessment(symbol, record, as_of):
    record = record if isinstance(record, dict) else {}
    checks = {key: {"status": "missing", "value": None, "message": f"Missing {key} evidence."} for key in CHECK_KEYS}
    observations = record.get("observations")
    observations = observations if isinstance(observations, dict) else {}
    for key, (field, predicate, message) in NUMERIC_RULES.items():
        value = observations.get(field)
        if _finite(value):
            passed = predicate(value)
            checks[key] = {"status": "observed_pass" if passed else "observed_fail", "value": value,
                           "message": f"Observed {_display_value(field, value)}; {message}. {'Threshold met' if passed else 'Failed rule'}; reviewed coverage is missing."}
        elif field in observations and value is not None:
            checks[key] = {"status": "unreviewed", "value": None,
                           "message": f"Invalid {field} observation; require a finite numeric value and reviewed evidence."}
    sga = observations.get("sga_growth")
    if _finite(sga):
        checks["management"] = {"status": "unreviewed", "value": sga,
                                "message": f"Observed SG&A growth {_display_value('sga_growth', sga)}. Headquarters and comparable SG&A evidence require review." +
                                (" SG&A growth at or above 25% requires investigation." if sga >= 0.25 else " Observed SG&A growth is below 25%.")}
    elif "sga_growth" in observations and sga is not None:
        checks["management"] = {"status": "unreviewed", "value": None,
                                "message": "Invalid SG&A observation; require finite numeric and headquarters evidence."}
    report = None
    snapshot = record.get("coverage_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("symbol") == symbol:
        try:
            report = coverage_report(snapshot, as_of)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            pass
    if report is not None:
        fields, normalized = report["fields"], report["normalized"]
        for key, (field, predicate, message) in NUMERIC_RULES.items():
            evidence_field = {"trailing_pe": "trailing_pe", "dividend_yield": "dividend_yield", "revenue_growth": "revenue"}[field]
            status = fields[evidence_field]["status"]
            value = normalized[field]
            if status != "available" and _finite(observations.get(field)):
                checks[key]["message"] += f" Coverage evidence is {status}."
                continue
            check_status = "pass" if status == "available" else (status if status in ("missing", "stale", "unreviewed") else "unreviewed")
            if status == "available" and f"gate:{field}" in report["blockers"]:
                check_status = "fail"
            checks[key] = {"status": check_status, "value": value,
                           "message": f"{message}. " + (f"Reviewed value {_display_value(field, value)}. " if value is not None else "") +
                           f"Evidence: {status}; {'failed rule' if check_status == 'fail' else check_status}."}
        classification = "excluded" if "classification:excluded" in report["blockers"] else "unknown" if "classification:unknown" in report["blockers"] else "eligible"
        class_status = fields["classification"]["status"]
        checks["classification"] = {"status": "pass" if classification == "eligible" and class_status == "available" else (
            "fail" if classification == "excluded" else class_status if class_status in ("missing", "stale") else "unreviewed"),
            "value": classification, "message": f"Operating-company US common-stock classification: {classification}; evidence {class_status}."}
        management_fields = [fields[key]["status"] for key in ("headquarters", "sga")]
        management_status = next((status for status in ("stale", "missing", "unreviewed") if status in management_fields),
                                 "pass" if all(status == "available" for status in management_fields) else "unreviewed")
        management_message = "Headquarters review and comparable quarterly SG&A evidence: " + ", ".join(management_fields) + "."
        if "headquarters:confirmed_investment" in report["blockers"]:
            management_status = "fail"
            management_message += " Confirmed new headquarters investment fails the management screen."
        if "sga_investigation" in report["flags"] and record.get("sga_investigation_resolved") is not True:
            management_status = "fail"
            management_message += " SG&A growth at or above 25% requires investigation before clearance."
        management_value = normalized["sga_growth"]
        if management_value is None and _finite(sga):
            management_value = sga
            management_message += f" Observed SG&A growth {_display_value('sga_growth', sga)} is unreviewed." + (
                " Growth at or above 25% requires investigation." if sga >= 0.25 else " Observed growth is below 25%.")
        checks["management"] = {"status": management_status, "value": management_value, "message": management_message}
    if "coverage_snapshot" in record and report is None:
        for key in ("classification", "management"):
            checks[key] = {"status": "unreviewed", "value": None,
                           "message": "Coverage snapshot is invalid or belongs to a different ticker; review required."}
    current_chart = record.get("chart_cutoff") == as_of
    refresh_status = _refresh_status(record, as_of)
    signals = record.get("signals")
    valid_signals = isinstance(signals, list) and all(_valid_event(event, as_of) for event in signals)
    fresh_entries = [event for event in signals if event["direction"] == "buy" and event["available_at"] == as_of] if valid_signals else []
    fresh_exits = [event for event in signals if event["direction"] == "sell" and event["available_at"] == as_of] if valid_signals else []
    if isinstance(signals, list) and not valid_signals:
        checks["entry"] = {"status": "unreviewed", "value": None,
                           "message": "Technical signal evidence is incomplete, invalid or mismatched; review required."}
    elif current_chart and valid_signals:
        checks["entry"] = {"status": "pass" if fresh_entries else "fail",
                           "value": [event["kind"] for event in fresh_entries],
                           "message": "Completed eligible entry: " + ", ".join(event["kind"] for event in fresh_entries) + "." if fresh_entries else "Awaiting a completed inverse head-and-shoulders, cup-and-handle, or breaking-out entry."}
        if not fresh_entries and any(event["direction"] == "observation" and event["available_at"] == as_of for event in signals):
            checks["entry"]["message"] += " Gapping-up observations provide context and never clear an entry."
    if record and refresh_status != "pass":
        checks["entry"] = {"status": refresh_status, "value": None,
                           "message": f"Chart/refresh evidence is {refresh_status}; require the completed evaluation session and an offset refresh receipt at or after its close."}
    elif fresh_exits:
        checks["entry"] = {"status": "fail", "value": [event["kind"] for event in fresh_exits],
                           "message": "Current technical exit " + ", ".join(event["kind"] for event in fresh_exits) +
                           " blocks entry; wait for stabilization and review."}
    price = record.get("price")
    if _finite(price) and price > 0:
        cost = price * 100
        checks["allocation"] = {"status": "pass" if cost <= 8000 else "fail", "value": cost if _finite(cost) else None,
                                "message": ("A 100-share block costs $" + f"{cost:,.2f}" if _finite(cost) else "A 100-share block cost exceeds the finite supported range") + " against the $8,000 allocation budget."}
    if refresh_status != "pass":
        for key in (*NUMERIC_RULES, "management", "allocation"):
            check = checks[key]
            if check["status"] in ("observed_pass", "observed_fail") or (key == "allocation" and check["value"] is not None):
                check["status"] = refresh_status
                check["message"] += f" Observation freshness is {refresh_status}; it cannot establish current clearance."
    observation_dates = record.get("observation_dates", {})
    for key, field in [(key, rule[0]) for key, rule in NUMERIC_RULES.items()] + [("management", "sga_growth")]:
        check = checks[key]
        evidence_field = {"trailing_pe": "trailing_pe", "dividend_yield": "dividend_yield",
                          "revenue_growth": "revenue", "sga_growth": "sga"}[field]
        observational = _finite(observations.get(field)) and (report is None or report["fields"][evidence_field]["status"] != "available")
        if not observational or (isinstance(observation_dates, dict) and field not in observation_dates):
            continue
        observed_date = observation_dates.get(field) if isinstance(observation_dates, dict) else None
        try:
            observed_day = date.fromisoformat(observed_date)
            date_status = "stale" if observed_day < date.fromisoformat(as_of) else "unreviewed" if observed_day > date.fromisoformat(as_of) else "pass"
        except (TypeError, ValueError):
            date_status = "unreviewed"
        if date_status != "pass":
            check["status"] = date_status
            check["message"] += f" Observation date {observed_date!s} is {date_status}; chart refresh does not update this evidence."
    status = "needs_review" if record else "needs_data"
    if report is not None and (report["eligibility"] == "excluded" or any(checks[key]["status"] == "fail" for key in ("pe", "yield", "quarterly_revenue"))):
        status = "filtered_out"
    elif report is not None and report["buy_allowed"] and checks["management"]["status"] == "pass" and refresh_status == "pass" and valid_signals and not fresh_exits:
        status = ("buy_ready" if checks["allocation"]["status"] == "pass" else "allocation_blocked") if fresh_entries else "radar"
    return {"symbol": symbol, "company": record.get("company"),
            "status": status, "checks": checks,
            "why": " ".join(check["message"] for check in checks.values() if check["status"] != "pass") or checks["entry"]["message"],
            "sources": deepcopy(record.get("sources", [])), "chart_cutoff": record.get("chart_cutoff"),
            "checked_at": record.get("checked_at")}


def _symbol(symbol):
    if not isinstance(symbol, str):
        raise ValueError("ticker must be a string")
    normalized = symbol.strip().upper().replace(".", "-")
    if len(normalized) > 10 or re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?", normalized) is None:
        raise ValueError("ticker must be at most 10 letters/digits with one optional class delimiter")
    return normalized


class ManualWatchStore:
    """Keep personal membership separate from the caller's assessment catalog."""

    def __init__(self, directory, catalog):
        self.directory = Path(directory)
        self.catalog = catalog

    def _read(self):
        path = self.directory / "membership.json"
        if not path.exists():
            return {"schema_version": "manual-watch-state-v1", "entries": [], "archive": []}
        try:
            state = json.loads(path.read_text())
            if not isinstance(state, dict) or state.get("schema_version") != "manual-watch-state-v1":
                raise ValueError("invalid state schema")
            for key in ("entries", "archive"):
                records = state[key]
                if not isinstance(records, list):
                    raise ValueError("invalid state records")
                seen = set()
                for record in records:
                    if not isinstance(record, dict) or _symbol(record["symbol"]) != record["symbol"]:
                        raise ValueError("invalid stored ticker")
                    if not isinstance(record["note"], str) or len(record["note"]) > 500:
                        raise ValueError("invalid stored note")
                    for timestamp in ("added_at", "removed_at") if key == "archive" else ("added_at",):
                        if datetime.fromisoformat(record[timestamp]).tzinfo is None:
                            raise ValueError("invalid stored timestamp")
                    if key == "entries" and record["symbol"] in seen:
                        raise ValueError("duplicate membership")
                    seen.add(record["symbol"])
            return state
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Corrupt manual watch state; restore reviewed membership before continuing") from error

    @contextmanager
    def _locked(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        descriptor = os.open(self.directory / "membership.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _write(self, state):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.directory, prefix=".membership-", delete=False) as output:
                temporary = output.name
                os.fchmod(output.fileno(), 0o600)
                json.dump(state, output, allow_nan=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.directory / "membership.json")
            temporary = None
            directory_descriptor = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if temporary is not None:
                os.unlink(temporary)

    def add(self, symbol, note=""):
        symbol = _symbol(symbol)
        if not isinstance(note, str) or len(note) > 500:
            raise ValueError("note must be a string of at most 500 characters")
        with self._locked():
            state = self._read()
            entries = state["entries"]
            existing = next((entry for entry in entries if entry["symbol"] == symbol), None)
            if existing is None:
                entries.append({"symbol": symbol, "note": note,
                                "added_at": datetime.now(timezone.utc).isoformat()})
            elif note:
                existing["note"] = note
            self._write(state)

    def remove(self, symbol):
        symbol = _symbol(symbol)
        if not self.directory.exists():
            return
        with self._locked():
            state = self._read()
            existing = next((entry for entry in state["entries"] if entry["symbol"] == symbol), None)
            if existing is not None:
                state["entries"].remove(existing)
                state["archive"].append({**existing, "removed_at": datetime.now(timezone.utc).isoformat()})
                self._write(state)

    def view(self, as_of):
        try:
            if not isinstance(as_of, str) or date.fromisoformat(as_of).isoformat() != as_of:
                raise ValueError("as_of requires a completed-session ISO date")
        except (TypeError, ValueError) as error:
            raise ValueError("as_of requires a completed-session ISO date") from error
        entries = []
        if self.directory.exists():
            with self._locked():
                entries = self._read()["entries"]
        assessments = {symbol: _assessment(symbol, record, as_of) for symbol, record in self.catalog.items()}
        return {"schema_version": "manual-watch-view-v1", "as_of": as_of,
                "manual_list": [{**deepcopy(assessments.get(entry["symbol"], _assessment(entry["symbol"], None, as_of))), **entry}
                                for entry in entries],
                "radar_list": [deepcopy(entry) for entry in assessments.values() if entry["status"] == "radar"],
                "buy_ready_list": [deepcopy(entry) for entry in assessments.values() if entry["status"] == "buy_ready"]}
