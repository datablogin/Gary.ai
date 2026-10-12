"""Retained-source adapter and durable localhost Train more journal.

The journal owns requests, allocations and labels. JSON views and immutable
snapshot sidecars can be reproduced after cache loss; raw sources stay private.
"""

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from zoneinfo import ZoneInfo

from gary import training
from gary.patterns import _PARAMETER_HASH, _VERSION
from gary.review import _hash
from gary.review_preview import ROOT, _json_bytes, _write_json

DEFAULT_TRAINING = ROOT / "private" / "training"
_V1_SHA = "76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a"
_V1_PARAMETERS = "d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae"
_FROZEN_SOURCES = {
    "review.py": "aec0b6a02a80da2fd46cbe1a2b58b87382e31f6fd108b9071cfa017042fd3d19",
    "evaluation.py": "1f2b9d04aec3af8a39731af2d2d6d9f1c6cb522b3313b9570a1cd3f7290a9757",
}
_CACHE = {}


def registry():
    """Only the reviewed executable is supported; HTTP never selects modules."""
    received = sha256(Path(__file__).with_name("patterns.py").read_bytes()).hexdigest()
    if received != _V1_SHA or _VERSION != "causal-geometry-v1" or _PARAMETER_HASH != _V1_PARAMETERS:
        raise ValueError("Trusted research detector changed")
    if any(sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != expected for name, expected in _FROZEN_SOURCES.items()):
        raise ValueError("Trusted recognition protocol executable changed")
    return {"causal-geometry-v1": dict(version=_VERSION, source_file_sha256=received, parameter_hash=_PARAMETER_HASH)}


def _file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _preserve(path, value):
    if path.exists():
        if _json_bytes(json.loads(path.read_text())) != _json_bytes(value):
            raise ValueError("Immutable training evidence differs")
    else:
        _write_json(path, value)


@contextmanager
def _lock(directory, create=False):
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".lock"
    if not create and not path.exists():
        raise ValueError("Training lock evidence missing")
    with path.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _source_from_receipt(row):
    raw = Path(row["raw_path"]).read_bytes()
    metadata = json.loads(Path(row["metadata_path"]).read_text())
    if row["source_id"] != metadata["source_id"]:
        raise ValueError("Source receipt identity mismatch")
    if row["format"] == "yahoo-chart-v1":
        data = json.loads(raw)["chart"]["result"][0]
        if data["meta"]["symbol"] != metadata["symbol"] or data["meta"]["instrumentType"] != "EQUITY":
            raise ValueError("Retained provider identity mismatch")
        zone = ZoneInfo(data["meta"]["exchangeTimezoneName"])
        if str(zone) != metadata["exchange_timezone"]:
            raise ValueError("Retained provider timezone mismatch")
        stamps, quotes = data["timestamp"], data["indicators"]["quote"][0]
        if not stamps or any(len(quotes[key]) != len(stamps) for key in ("open", "high", "low", "close", "volume")):
            raise ValueError("Retained provider arrays incomplete")
        bars = [{"date": datetime.fromtimestamp(stamp, zone).date().isoformat(),
                 **{key: quotes[key][i] for key in ("open", "high", "low", "close", "volume")}}
                for i, stamp in enumerate(stamps)]
        splits = sorted(datetime.fromtimestamp(e["date"], zone).date().isoformat()
                        for e in data.get("events", {}).get("splits", {}).values())
        if splits != metadata["split_dates"]:
            raise ValueError("Retained provider split metadata mismatch")
    elif row["format"] == "synthetic-ohlcv-v1":
        data = json.loads(raw)
        if data["symbol"] != metadata["symbol"] or data["exchange_timezone"] != metadata["exchange_timezone"] or data["split_dates"] != metadata["split_dates"]:
            raise ValueError("Synthetic receipt identity mismatch")
        bars = data["bars"]
    else:
        raise ValueError("Unsupported retained-source adapter")
    return metadata | {"bars": bars, "source_sha256": sha256(raw).hexdigest()}


def _verify_bootstrap(bootstrap):
    try:
        manifest = registry()["causal-geometry-v1"]
        if (bootstrap["schema_version"] != "training-store-bootstrap-v1"
                or set(bootstrap) != {"schema_version", "catalog", "config", "receipts", "source_receipts"}
                or bootstrap["config"]["detector_manifest"] != manifest
                or bootstrap["catalog"]["schema_version"] != "training-catalog-v1"):
            raise ValueError("Training bootstrap schema or registry invalid")
        receipts = bootstrap["receipts"]
        if not isinstance(receipts, list) or not receipts or any(
                set(r) != {"path", "received_sha256"} or _file_hash(r["path"]) != r["received_sha256"] for r in receipts):
            raise ValueError("Retained source or exposure receipt changed/missing")
        paths = {r["path"]: r["received_sha256"] for r in receipts}
        for r in bootstrap["catalog"]["exposure"].get("evidence", []):
            if paths.get(r["path"]) != r["received_sha256"]:
                raise ValueError("Exposure receipt lacks retained bootstrap anchor")
        expected = []
        for row in bootstrap["source_receipts"]:
            if row["raw_path"] not in paths or row["metadata_path"] not in paths:
                raise ValueError("Source receipts lack independent retained anchors")
            source = _source_from_receipt(row)
            if source["alias_evidence"]["receipt_sha256"] not in paths.values() or source["classification"]["evidence_sha256"] not in paths.values():
                raise ValueError("Reviewed source lineage/classification proof lacks retained bytes")
            expected.append(source)
        if _hash(sorted(expected, key=lambda s: s["source_id"])) != _hash(bootstrap["catalog"]["sources"]):
            raise ValueError("Training source catalog differs from retained bytes")
        return manifest
    except (AttributeError, IndexError, KeyError, OSError, TypeError, ValueError) as error:
        raise ValueError(f"Training evidence verification failed: {error}") from error


def prepare_store(directory, catalog, config, source_receipts, receipts):
    """Operator-only immutable import; source/proof paths cannot come from HTTP."""
    directory = Path(directory)
    catalog = deepcopy(catalog)
    catalog["sources"] = sorted(catalog["sources"], key=lambda s: s["source_id"])
    bootstrap = dict(schema_version="training-store-bootstrap-v1", catalog=catalog, config=deepcopy(config),
                     receipts=deepcopy(receipts), source_receipts=deepcopy(source_receipts))
    _verify_bootstrap(bootstrap)
    history = dict(schema_version="training-history-v1", exposure=deepcopy(catalog["exposure"]), rounds=[], requests={})
    training.request_training_round(catalog, history, dict(request_id="operator-preflight", config=config))
    with _lock(directory, create=True):
        _preserve(directory / "bootstrap.json", bootstrap)
        journal = directory / "events.journal.jsonl"
        header = dict(schema_version="training-journal-v1", bootstrap_hash=_hash(bootstrap))
        if not journal.exists():
            with journal.open("xb") as handle:
                handle.write(_json_bytes(header) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        elif json.loads(journal.read_bytes().splitlines()[0]) != header:
            raise ValueError("Existing journal belongs to different bootstrap")
    _CACHE.pop(str(directory.resolve()), None)
    return dict(status="prepared", source_count=len(catalog["sources"]))


def _diagnostic_projection(report):
    if report is None:
        return None
    return {key: deepcopy(report[key]) for key in ("schema_version", "mode", "status", "report_hash", "pass_hash",
        "reference_detector_input_sessions", "visual_context_years", "chronology", "coverage", "overall", "by_stratum", "limitations")}


def _own_label(row):
    if row is None:
        return None
    return {key: deepcopy(row[key]) for key in ("case_id", "reviewer_id", "reviewer_role", "decision", "rationale", "revision")} | {
        "events": [{"kind": e["kind"], "completion_offset": e["completion_offset"]} for e in row["events"]]}


class TrainingStore:
    def __init__(self, directory=DEFAULT_TRAINING, reviewer_id="gary"):
        self.directory = Path(directory)
        self.reviewer_id = reviewer_id

    def _read(self):
        try:
            return self._reconstruct()
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Training journal/evidence could not be verified: {error}") from error

    def _reconstruct(self):
        bootstrap = json.loads((self.directory / "bootstrap.json").read_text())
        _verify_bootstrap(bootstrap)
        if bootstrap["config"]["reviewer_id"] != self.reviewer_id:
            raise PermissionError("Assigned training reviewer only")
        raw = (self.directory / "events.journal.jsonl").read_bytes()
        fingerprint = _hash([bootstrap, sha256(raw).hexdigest()])
        cached = _CACHE.get(str(self.directory.resolve()))
        if cached and cached[0] == fingerprint:
            self._verify_sidecars(cached[1]["history"])
            return deepcopy(cached[1])
        chunks = raw.splitlines(keepends=True)
        if not chunks or not chunks[0].endswith(b"\n") or json.loads(chunks[0]) != dict(schema_version="training-journal-v1", bootstrap_hash=_hash(bootstrap)):
            raise ValueError("Training journal bootstrap commitment invalid")
        history = dict(schema_version="training-history-v1", exposure=deepcopy(bootstrap["catalog"]["exposure"]), rounds=[], requests={})
        previous, count, valid_bytes = _hash(json.loads(chunks[0])), 0, len(chunks[0])
        for chunk in chunks[1:]:
            if not chunk.endswith(b"\n"):
                break
            event = json.loads(chunk)
            if (set(event) != {"schema_version", "sequence", "previous_hash", "before_hash", "after_hash", "operation", "recorded_at_utc", "event_hash"}
                    or datetime.fromisoformat(event["recorded_at_utc"]).tzinfo is None
                    or event["schema_version"] != "training-transaction-v1" or type(event["sequence"]) is not int
                    or event["sequence"] != count + 1 or event["previous_hash"] != previous
                    or event["before_hash"] != _hash(history)
                    or event["event_hash"] != _hash({k: v for k, v in event.items() if k != "event_hash"})):
                raise ValueError("Training transaction commitment invalid")
            history, _ = self._apply(bootstrap, history, event["operation"])
            if event["after_hash"] != _hash(history):
                raise ValueError("Training transaction fails retained-source reconstruction")
            previous, count, valid_bytes = event["event_hash"], count + 1, valid_bytes + len(chunk)
        result = dict(bootstrap=bootstrap, history=history, previous=previous, count=count, valid_bytes=valid_bytes, raw=raw)
        self._verify_sidecars(history)
        _CACHE[str(self.directory.resolve())] = (fingerprint, deepcopy(result))
        return result

    def _apply(self, bootstrap, history, operation):
        if operation["kind"] == "request" and set(operation) == {"kind", "request_id"}:
            catalog = bootstrap["catalog"] | {"exposure": deepcopy(history["exposure"])}
            transition = training.request_training_round(catalog, history, dict(request_id=operation["request_id"], config=bootstrap["config"]))
            return transition["history"], transition
        if operation["kind"] == "label" and set(operation) == {"kind", "round_id", "entry"}:
            result = deepcopy(history)
            selected = next((r for r in result["rounds"] if r["round_id"] == operation["round_id"]), None)
            if selected is None:
                raise KeyError("Round unavailable")
            submitted = operation["entry"]
            if submitted.get("reviewer_id") != self.reviewer_id:
                raise PermissionError("Assigned training reviewer only")
            selected["labels"] = training.record_review_label(selected["queue"], selected["labels"], submitted)
            summary = training.summarize_review(selected["queue"], selected["labels"])
            selected.update(status=summary["status"], snapshots=summary["snapshots"])
            return result, summary
        raise ValueError("Unsupported training transaction")

    def _verify_sidecars(self, history):
        expected = {}
        for r in history["rounds"]:
            expected["queues/" + r["queue"]["queue_hash"] + ".json"] = r["queue"]
            for snapshot in r["snapshots"]:
                expected["passes/" + snapshot["pass_hash"] + ".json"] = snapshot["completed_pass"]
                report = snapshot["diagnostic"]
                expected["reports/" + report["report_hash"] + ".json"] = report
        for folder in ("queues", "passes", "reports"):
            for path in (self.directory / folder).glob("*.json"):
                key = str(path.relative_to(self.directory))
                if key not in expected or _json_bytes(json.loads(path.read_text())) != _json_bytes(expected[key]):
                    raise ValueError("Retained completed evidence conflicts with authoritative journal")

    def _append(self, state, operation, after):
        journal = self.directory / "events.journal.jsonl"
        if state["valid_bytes"] < len(state["raw"]):
            archive = self.directory / "interrupted" / (secrets.token_hex(16) + ".raw")
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(state["raw"][state["valid_bytes"]:])
            with journal.open("r+b") as handle:
                handle.truncate(state["valid_bytes"])
                handle.flush()
                os.fsync(handle.fileno())
        if _hash(after) != _hash(state["history"]):
            event = dict(schema_version="training-transaction-v1", sequence=state["count"] + 1,
                         previous_hash=state["previous"], before_hash=_hash(state["history"]), after_hash=_hash(after),
                         operation=deepcopy(operation), recorded_at_utc=datetime.now(timezone.utc).isoformat())
            event["event_hash"] = _hash(event)
            with journal.open("ab") as handle:
                handle.write(_json_bytes(event) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        _CACHE.pop(str(self.directory.resolve()), None)
        self._materialize(after)

    def _materialize(self, history):
        _write_json(self.directory / "history.json", history)
        for round_record in history["rounds"]:
            queue = round_record["queue"]
            _preserve(self.directory / "queues" / (queue["queue_hash"] + ".json"), queue)
            for snapshot in round_record["snapshots"]:
                _preserve(self.directory / "passes" / (snapshot["pass_hash"] + ".json"), snapshot["completed_pass"])
                report = snapshot["diagnostic"]
                _preserve(self.directory / "reports" / (report["report_hash"] + ".json"), report)

    def request_round(self, request_id):
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 512:
            raise ValueError("A bounded request id is required")
        with _lock(self.directory):
            state = self._read()
            after, transition = self._apply(state["bootstrap"], state["history"], dict(kind="request", request_id=request_id))
            self._append(state, dict(kind="request", request_id=request_id), after)
        return self.hub(transition["round_id"]) | {"outcome": transition["status"]}

    def save_label(self, round_id, entry):
        with _lock(self.directory):
            state = self._read()
            # This entire path is read-only until exact token/observation validation succeeds.
            operation = dict(kind="label", round_id=round_id, entry=deepcopy(entry))
            after, _ = self._apply(state["bootstrap"], state["history"], operation)
            self._append(state, operation, after)
        return self.hub(round_id)

    def card(self, round_id, case_id):
        with _lock(self.directory):
            state = self._read()
            selected = next((r for r in state["history"]["rounds"] if r["round_id"] == round_id), None)
            if selected is None or case_id not in selected["queue"]["cards"]:
                raise KeyError("Chart unavailable")
            summary = training.summarize_review(selected["queue"], selected["labels"])
            card = deepcopy(selected["queue"]["cards"][case_id])
            overview = card.pop("overview")
            return dict(card=card, overview=overview, own_label=_own_label(summary["own_labels"].get(case_id)),
                        view_token=selected["queue"]["queue_hash"])

    def _hub(self, state, round_id=None):
        history = state["history"]
        selected = next((r for r in history["rounds"] if r["round_id"] == round_id), None) if round_id else next(
            (r for r in reversed(history["rounds"]) if r["status"] in {"ready", "labeling"}), history["rounds"][-1] if history["rounds"] else None)
        if round_id and selected is None:
            raise KeyError("Round unavailable")
        summaries = [(row, training.summarize_review(row["queue"], row["labels"])) for row in history["rounds"]]
        result = dict(reviewer_id=self.reviewer_id, detector_version="causal-geometry-v1", status="idle", message="", round=None,
            data_prepared=True,
            history=[dict(round_id=r["round_id"], status=r["status"], progress=s["progress"], snapshot_count=len(r["snapshots"])) for r, s in summaries],
            baseline_diagnostic=_diagnostic_projection(diagnostics(self.directory)) if (self.directory / "diagnostics/current-pass.inputs.json").exists() or (self.directory / "preservation-baseline.json").exists() else None)
        if selected:
            summary = next(s for r, s in summaries if r["round_id"] == selected["round_id"])
            result.update(status=selected["status"], round=dict(round_id=selected["round_id"], status=selected["status"],
                order=selected["queue"]["order"], progress=summary["progress"], own_labels={k: _own_label(v) for k, v in summary["own_labels"].items()},
                diagnostic=_diagnostic_projection(summary["diagnostic"]), snapshot_count=len(selected["snapshots"])))
        # Data availability belongs to the hub even while a completed round is selected.
        if history["requests"] and list(history["requests"].values())[-1]["outcome"] == "needs_data":
            result.update(status="needs_data", message="No admitted unused targets remain. Additional reviewed source data are needed.")
        elif not state["bootstrap"]["catalog"]["sources"] or state["bootstrap"]["catalog"]["exposure"].get("complete") is not True:
            result.update(status="needs_data", message="Reviewed source and complete exposure evidence are needed.")
        return result

    def hub(self, round_id=None):
        if not (self.directory / "bootstrap.json").exists():
            if round_id:
                raise KeyError("Round unavailable")
            return dict(reviewer_id=self.reviewer_id, status="needs_data", history=[], round=None,
                        data_prepared=False,
                        message="Prepare retained training data before requesting a round.", detector_version="causal-geometry-v1", baseline_diagnostic=None)
        with _lock(self.directory):
            return self._hub(self._read(), round_id)


def prepare_cached(directory=DEFAULT_TRAINING):
    """Review the retained pilot and conservatively reserve every prior case."""
    from gary.review_preview import _new_sources, SAMPLE
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    baseline_path = DEFAULT_TRAINING / "preservation-baseline.json"
    if not baseline_path.exists():
        proof = directory / "inputs/missing-cache.json"
        _preserve(proof, dict(schema_version="training-missing-cache-v1", reason="Retained pilot/provenance is unavailable"))
        evidence = [dict(path=str(proof.resolve()), received_sha256=_file_hash(proof))]
        ledger = dict(schema_version="training-exposure-v1", complete=False, evidence=evidence, aliases={}, targets=[], views=[], reservations=[])
        catalog = dict(schema_version="training-catalog-v1", sources=[], exposure=ledger)
        config = dict(profile="training-five-year-v1", reviewer_id="gary", random_seed=20261012, shuffle_seed=20261013,
                      id_salt="missing-data", detector_manifest=registry()["causal-geometry-v1"])
        prepare_store(directory, catalog, config, [], evidence)
        return dict(status="needs_data", reason="Retained source and exposure evidence required")
    baseline = json.loads(baseline_path.read_text())["files"]
    if any(not (ROOT / p).exists() or _file_hash(ROOT / p) != digest for p, digest in baseline.items()):
        raise ValueError("Preservation baseline changed; existing evidence must be reconciled before import")
    sec_path = ROOT / "private/coverage/sec-tickers.raw"
    directory_data = json.loads(sec_path.read_text())
    fields = directory_data["fields"]
    identities = {row[fields.index("ticker")]: row for row in directory_data["data"]}
    canonical = lambda symbol: "cik:" + str(identities[symbol][fields.index("cik")]).zfill(10)
    queue_paths = [ROOT / p for p in baseline if p.endswith("/queue.json")]
    aliases, targets, views, reservations = {}, [], [], []
    for path in queue_paths:
        queue = json.loads(path.read_text())
        for key, case in queue["sealed"]["cases"].items():
            identity = canonical(case["symbol"])
            for alias in (case["symbol"], case["source_id"]):
                if alias in aliases and aliases[alias] != identity:
                    raise ValueError("Legacy alias lineage conflicts")
                aliases[alias] = identity
            raw = case["raw_window"]
            context = queue["sealed"].get("context_review", {}).get("cases", {}).get(key, {}).get("raw_window", raw)
            provenance = str(path.relative_to(ROOT)) + ":" + key
            targets.append(dict(canonical_id=identity, start=raw[-20]["date"], end=case["as_of"],
                                case_fingerprint=_hash(dict(canonical_id=identity, as_of=case["as_of"], window_hash=_hash(raw[-180:]))), provenance=provenance))
            views.append(dict(canonical_id=identity, start=context[0]["date"], end=case["as_of"], provenance=provenance))
            if case["symbol"] in queue["sealed"]["config"].get("reserved_sources", []):
                reservations.append(dict(canonical_id=identity, start=raw[0]["date"], end=case["as_of"], active=False,
                                         provenance=provenance + ":historical_exposed_release_role_preserved"))
    cache = ROOT / "private/cycle-3/holdout-context/sources"
    retained = _new_sources(cache, SAMPLE)
    retained += _new_sources(ROOT / "private/cycle-3/sources")
    for source in retained:
        identity = canonical(source["symbol"])
        aliases[source["symbol"]] = identity
        aliases[source["source_id"]] = identity
        views.append(dict(canonical_id=identity, start=source["bars"][0]["date"], end=source["bars"][-1]["date"],
                          provenance="retained_development_source:" + source["source_sha256"]))
    # Runtime anchors are immutable research inputs. Paper state and screenshots
    # remain in the cycle preservation check, not the live data admission gate.
    anchors = [ROOT / p for p in baseline if p.endswith("/queue.json") or p.endswith("/release.json") or p.endswith("/exposure.json")
               or "/completed-passes/" in p or "/identity-reveals/" in p or "/sources/" in p and p.endswith((".json", ".raw"))]
    classification_path = ROOT / "docs/research/data-coverage.md"
    anchors += [sec_path, classification_path, ROOT / "private/coverage/nasdaq-listed.raw", ROOT / "private/coverage/nasdaq-other.raw"]
    receipts = [dict(path=str(p.resolve()), received_sha256=_file_hash(p)) for p in sorted(set(anchors))]
    ledger = dict(schema_version="training-exposure-v1", complete=True, evidence=deepcopy(receipts), aliases=aliases,
                  targets=sorted({_hash(r): r for r in targets}.values(), key=_hash),
                  views=sorted({_hash(r): r for r in views}.values(), key=_hash),
                  reservations=sorted({_hash(r): r for r in reservations}.values(), key=_hash))
    sources, source_receipts = [], []
    # This bounded pilot has existing reviewed classification evidence. No new
    # issuer or vendor EQUITY label is automatically granted that review.
    reviewed = {"MU", "AMGN", "META", "ORCL"}
    for source in retained:
        if source["symbol"] not in reviewed:
            continue
        source = deepcopy(source)
        symbol = source["symbol"]
        exchange = identities[symbol][fields.index("exchange")].upper()
        source.update(canonical_id=canonical(symbol), aliases=sorted({source["source_id"], symbol}),
            alias_evidence=dict(reviewed=True, receipt_sha256=_file_hash(sec_path), provenance="Retained SEC identity directory and legacy same-symbol source receipts"),
            classification=dict(reviewed=True, security_type="operating_common", exchange=exchange,
                evidence_sha256=_file_hash(classification_path), provenance="Reviewed operating-common pilot: retained Nasdaq listing and prior issuer research; no fundamental buy clearance"),
            cutoffs=sorted({b["date"] for b in source["bars"][1258::42]} | {source["bars"][-1]["date"]}))
        metadata_path = directory / "sources" / (symbol + ".metadata.json")
        _preserve(metadata_path, {k: v for k, v in source.items() if k not in {"bars", "source_sha256"}})
        receipts.append(dict(path=str(metadata_path.resolve()), received_sha256=_file_hash(metadata_path)))
        source_receipts.append(dict(source_id=source["source_id"], format="yahoo-chart-v1", raw_path=str((cache / (symbol + "-chart.raw")).resolve()),
                                    metadata_path=str(metadata_path.resolve())))
        sources.append(source)
    catalog = dict(schema_version="training-catalog-v1", sources=sorted(sources, key=lambda s: s["source_id"]), exposure=ledger)
    if (directory / "bootstrap.json").exists():
        config = json.loads((directory / "bootstrap.json").read_text())["config"]
    else:
        config = dict(profile="training-five-year-v1", reviewer_id="gary", random_seed=20261012, shuffle_seed=20261013,
                      id_salt=secrets.token_hex(32), detector_manifest=registry()["causal-geometry-v1"])
    return prepare_store(directory, catalog, config, source_receipts, receipts)


def diagnostics(directory=DEFAULT_TRAINING):
    """Reproduce the earlier receipt-bound report without interpreting new labels."""
    from gary.training_analysis import analyze_training_pass
    from gary.review_preview import cycle3_study, load_release, CYCLE3
    folder = Path(directory) / "diagnostics"
    inputs = json.loads((folder / "current-pass.inputs.json").read_text())
    _, queue, _ = cycle3_study("holdout")
    if _hash(inputs["queue"]) != _hash(queue) or _hash(inputs["reference"]["release"]) != _hash(load_release()):
        raise ValueError("Diagnostic retained queue or release changed")
    fingerprint = _hash(inputs["completed_pass"])
    original = CYCLE3 / "holdout-context"
    passed = json.loads((original / "completed-passes" / ("gary-" + fingerprint + ".json")).read_text())
    receipt = json.loads((original / "identity-reveals" / ("gary-" + fingerprint + ".json")).read_text())
    if _hash(passed) != fingerprint or _hash(receipt) != _hash(inputs["reference"]["reveal_receipt"]):
        raise ValueError("Diagnostic locked snapshot or actual reveal receipt changed")
    report = analyze_training_pass(inputs["queue"], inputs["completed_pass"], inputs["reference"])
    if _hash(report) != _hash(json.loads((folder / "current-pass.json").read_text())):
        raise ValueError("Immutable diagnostic does not reproduce")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "import", "diagnostics"))
    parser.add_argument("--training-dir", type=Path, default=DEFAULT_TRAINING)
    parser.add_argument("--bundle", type=Path, help="operator-owned JSON catalog/config/retained receipt bundle")
    args = parser.parse_args(argv)
    if args.action == "diagnostics":
        report = diagnostics(args.training_dir)
        result = dict(status="verified", mode=report["mode"], report_hash=report["report_hash"])
    elif args.action == "import":
        if args.bundle is None:
            parser.error("import requires --bundle")
        bundle = json.loads(args.bundle.read_text())
        result = prepare_store(args.training_dir, bundle["catalog"], bundle["config"], bundle["source_receipts"], bundle["receipts"])
    else:
        result = prepare_cached(args.training_dir)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
