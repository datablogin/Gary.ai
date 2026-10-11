"""Cached-input adapter and private persistence for the local review workflow."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from zoneinfo import ZoneInfo

from gary.review import build_review_queue, record_review_label, summarize_review

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STUDY = ROOT / "private" / "cycle-2"
CYCLE3 = ROOT / "private" / "cycle-3"
FIVE_YEAR_SYMBOLS = ("JNJ", "JPM", "KO")
SAMPLE = ("MU", "AMGN", "SIRI", "META", "ORCL", "TSM", "O", "ARCC")
CONTEXT_CACHE = ROOT / "private" / "holdout-context" / "sources"
PARAMETER_HASH = "d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae"


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(_json_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _source_series(cache):
    manifest = {entry["file"]: entry for entry in json.loads((cache / "artifact-manifest.json").read_text())}
    probes = json.loads((cache / "initial-probes.json").read_text())
    probes += json.loads((cache / "sample-probes.json").read_text())
    series = []
    for symbol in SAMPLE:
        filename = "yahoo-MU-chart.raw" if symbol == "MU" else f"{symbol}-chart.raw"
        raw = (cache / filename).read_bytes()
        digest = sha256(raw).hexdigest()
        if digest != manifest[filename]["sha256"] or len(raw) != manifest[filename]["bytes"]:
            raise ValueError(f"Cached source integrity failed for {symbol}")
        probe = next(p for p in probes if f"/chart/{symbol}?" in p.get("url", ""))
        data = json.loads(raw)["chart"]["result"][0]
        zone = ZoneInfo(data["meta"]["exchangeTimezoneName"])
        quote = data["indicators"]["quote"][0]
        bars = [{"date": datetime.fromtimestamp(stamp, zone).date().isoformat(),
                 **{key: quote[key][i] for key in ("open", "high", "low", "close", "volume")}}
                for i, stamp in enumerate(data["timestamp"])]
        split_dates = sorted(datetime.fromtimestamp(event["date"], zone).date().isoformat()
                             for event in data.get("events", {}).get("splits", {}).values())
        series.append({"source_id": symbol, "symbol": symbol, "source_sha256": digest,
                       "fetched_at": probe["started_at_utc"], "exchange_timezone": str(zone),
                       "price_basis": "provider_received_ohlc", "bars": bars, "split_dates": split_dates})
    return series


def build_study(cache=ROOT / "private" / "coverage", directory=DEFAULT_STUDY):
    """Build once, or reproduce the identical active study without replacing labels."""
    cache, directory = Path(cache), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    config_path = directory / "study-config.json"
    detector_hash = sha256(Path(__file__).with_name("patterns.py").read_bytes()).hexdigest()
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        config = {"study_id": "gary-pattern-pilot-20261010-v1", "id_salt": secrets.token_hex(32),
                  "random_seed": 20261010, "shuffle_seed": 20261011,
                  "window_sessions": 180, "target_sessions": 20, "calibration_end": "2024-12-31",
                  "reserved_sources": ["AMGN", "SIRI"], "calibration_random_per_source": 2,
                  "time_holdout_random_per_source": 1, "reserved_random_per_source": 3,
                  "match_tolerance_sessions": 3, "holdout_locked": True,
                  "detector_version": "causal-geometry-v1", "detector_parameter_hash": PARAMETER_HASH,
                  "detector_source_file_sha256": detector_hash,
                  "reviewers": {"gary": {"role": "human"}, "agent-qa": {"role": "agent"}}}
    if config.get("detector_source_file_sha256") != detector_hash:
        raise ValueError("Detector changed: use a separately versioned study directory")
    queue = build_review_queue(_source_series(cache), config)
    queue_path = directory / "queue.json"
    if queue_path.exists():
        previous = load_queue(directory)
        if previous["queue_hash"] != queue["queue_hash"]:
            raise ValueError("Active study differs: use a new study directory; existing labels were preserved")
    else:
        _write_json(config_path, config)
        _write_json(queue_path, queue)
    return {"status": "ready", "open_cards": len(queue["cards"]),
            "locked_cards": len(queue["sealed"]["cases"]) - len(queue["cards"]),
            "queue_hash": queue["queue_hash"], "source_count": len(SAMPLE),
            "exclusions": len(queue["sealed"]["exclusions"]), "trading_approval": False}


def load_queue(directory=DEFAULT_STUDY):
    queue = json.loads((Path(directory) / "queue.json").read_text())
    expected = queue["queue_hash"]
    unhashed = {key: value for key, value in queue.items() if key != "queue_hash"}
    if sha256(_json_bytes(unhashed)).hexdigest() != expected:
        raise ValueError("Review queue integrity failed")
    if queue["sealed"]["detector"]["source_file_sha256"] != sha256(Path(__file__).with_name("patterns.py").read_bytes()).hexdigest():
        raise ValueError("Frozen detector source changed")
    return queue


def load_labels(queue, directory=DEFAULT_STUDY):
    """Replay the authoritative journal; materialized-view loss cannot lose labels."""
    directory = Path(directory)
    labels = {"study_id": queue["study_id"], "queue_hash": queue["queue_hash"], "entries": []}
    journal = directory / "labels.journal.jsonl"
    if journal.exists():
        for line in journal.read_bytes().splitlines(keepends=True):
            if not line.endswith(b"\n"):
                break  # incomplete final write is never an acknowledged label
            record = json.loads(line)
            if record["queue_hash"] != queue["queue_hash"]:
                raise ValueError("Journal belongs to a different frozen queue")
            labels = _record_label(queue, labels, record["submission"])
    return labels


def save_label(queue, entry, directory=DEFAULT_STUDY):
    """Append and fsync before acknowledgment; retries recover a missing JSON cache."""
    directory = Path(directory)
    current = load_labels(queue, directory)
    updated = _record_label(queue, current, entry)
    journal = directory / "labels.journal.jsonl"
    if updated != current:
        directory.mkdir(parents=True, exist_ok=True)
        if journal.exists():
            data = journal.read_bytes()
            if data and not data.endswith(b"\n"):
                boundary = data.rfind(b"\n") + 1
                archive = directory / f"interrupted-journal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.raw"
                archive.write_bytes(data[boundary:])
                with journal.open("r+b") as stream:
                    stream.truncate(boundary)
        record = {"queue_hash": queue["queue_hash"], "received_at": datetime.now(timezone.utc).isoformat(),
                  "submission": deepcopy(entry)}
        with journal.open("ab") as stream:
            stream.write(_json_bytes(record) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    _write_json(directory / "labels.json", updated)
    return updated


def _record_label(queue, labels, entry):
    if "context_review" in queue["sealed"]:
        from gary.context_review import record_review_label as record_context_label
        return record_context_label(queue, labels, entry)
    return record_review_label(queue, labels, entry)


def _own_label(label):
    if label is None:
        return None
    return {key: deepcopy(label[key]) for key in ("case_id", "reviewer_id", "reviewer_role", "decision", "rationale", "revision")} | {
        "events": [{"kind": event["kind"], "completion_offset": event["completion_offset"]} for event in label["events"]]}


def reviewer_view(queue, labels, reviewer_id, case_id=None):
    """Strict whitelist: never send the private summary or another reviewer's label."""
    reviewers = queue["sealed"]["config"]["reviewers"]
    if reviewer_id not in reviewers:
        raise ValueError("Choose a registered reviewer")
    latest = {}
    for label in labels["entries"]:
        if label["reviewer_id"] == reviewer_id:
            latest[label["case_id"]] = label
    if case_id is not None:
        if case_id not in queue["cards"]:
            raise KeyError("Chart unavailable")
        view = {"card": deepcopy(queue["cards"][case_id]), "own_label": _own_label(latest.get(case_id)),
                "view_token": queue["queue_hash"]}
        if "context_review" in queue["sealed"]:
            view["overview"] = deepcopy(queue["sealed"]["context_review"]["cases"][case_id]["overview"])
        return view
    return {"reviewer_id": reviewer_id, "reviewer_role": reviewers[reviewer_id]["role"], "order": queue["order"],
            "progress": {"total": len(queue["cards"]), "labeled": len(latest)},
            "own_labels": {case: _own_label(label) for case, label in latest.items()}}


def _new_sources(cache, symbols=FIVE_YEAR_SYMBOLS):
    """Read bounded research responses without changing any retained raw source."""
    cache = Path(cache)
    rows = json.loads((cache / "artifact-manifest.json").read_text())
    manifest = {row["symbol"]: row for row in rows}
    if len(manifest) != len(rows) or set(manifest) != set(symbols):
        raise ValueError("Research source manifest identities differ")
    sources = []
    for symbol in symbols:
        row = manifest[symbol]
        if row["file"] != f"{symbol}-chart.raw" or row["status"] != 200:
            raise ValueError("Five-year source manifest is invalid")
        raw = (cache / row["file"]).read_bytes()
        if len(raw) != row["bytes"] or sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"Five-year source integrity failed for {symbol}")
        data = json.loads(raw)["chart"]["result"][0]
        if data["meta"]["symbol"] != symbol or data["meta"]["instrumentType"] != "EQUITY":
            raise ValueError("Five-year source identity/type mismatch")
        zone = ZoneInfo(data["meta"]["exchangeTimezoneName"])
        quote = data["indicators"]["quote"][0]
        stamps = data["timestamp"]
        if not isinstance(stamps, list) or not stamps or any(
            not isinstance(quote.get(key), list) or len(quote[key]) != len(stamps)
            for key in ("open", "high", "low", "close", "volume")
        ):
            raise ValueError("Five-year source arrays must have equal nonzero lengths")
        bars = [{"date": datetime.fromtimestamp(stamp, zone).date().isoformat(),
                 **{key: quote[key][i] for key in ("open", "high", "low", "close", "volume")}}
                for i, stamp in enumerate(stamps)]
        sources.append({"source_id": symbol, "symbol": symbol, "source_sha256": row["sha256"],
                        "fetched_at": row["fetched_at"], "exchange_timezone": str(zone),
                        "price_basis": "provider_received_ohlc", "bars": bars,
                        "split_dates": sorted(datetime.fromtimestamp(event["date"], zone).date().isoformat()
                                              for event in data.get("events", {}).get("splits", {}).values())})
    return sources


def _preserve_json(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("Active study/release differs; existing evidence was preserved")
    else:
        _write_json(path, value)


def load_release(directory=CYCLE3):
    """Validate every commitment before serving any released research cards."""
    from gary.evaluation import evaluate_detector
    directory = Path(directory)
    queue = load_queue(directory / "calibration")
    labels = load_labels(queue, directory / "calibration")
    release = json.loads((directory / "release.json").read_text())
    evaluate_detector(queue, labels, release, "calibration")
    return release


def cycle3_study(key, directory=CYCLE3):
    if key not in {"calibration", "holdout", "holdout-original", "five-year"}:
        raise KeyError("Chart unavailable")
    directory = Path(directory)
    if key in {"holdout", "holdout-original", "five-year"} or (directory / "release.json").exists():
        release = load_release(directory)
        if key == "holdout" and (directory / "holdout-context" / "queue.json").exists():
            study = directory / "holdout-context"
            queue = load_queue(study)
            from gary.context_review import build_review_queue as build_context_queue
            expected = build_context_queue(_new_sources(study / "sources", SAMPLE), {
                "profile": "five-year-assisted-v1", "parent_queue": release["holdout_queue"],
                "parent_release_hash": release["release_hash"]})
            if queue != expected:
                raise ValueError("Context cards differ from the preserved release/sources")
            return study, queue, False
        study = directory / ("holdout" if key == "holdout-original" else key)
        queue = load_queue(study)
        if key in {"holdout", "holdout-original"} and queue != release["holdout_queue"]:
            raise ValueError("Released holdout differs from the committed queue")
        if key == "five-year":
            original = {source["symbol"] for source in load_queue(directory / "calibration")["sealed"]["sources"]}
            if original & {source["symbol"] for source in queue["sealed"]["sources"]}:
                raise ValueError("Exploration overlaps original study sources")
            expected = build_review_queue(_new_sources(directory / "sources"), queue["sealed"]["config"])
            if queue != expected:
                raise ValueError("Five-year cards differ from the preserved sources/protocol")
        context_exposed = (directory / "holdout-context" / "exposure.json").exists()
        return study, queue, key in {"calibration", "holdout-original"} or key == "holdout" and context_exposed
    queue = load_queue(directory / key)
    if queue["schema_version"] != "pattern-review-v1" or queue["sealed"]["config"].get("profile"):
        raise ValueError("This study requires a verified cycle-3 release")
    return directory / key, queue, False


def build_cycle3(directory=CYCLE3, cache=None):
    """Freeze first, then build separate holdout and five-year review studies."""
    from gary.evaluation import freeze_evaluation
    directory = Path(directory)
    calibration = directory / "calibration"
    queue = load_queue(calibration)
    labels = load_labels(queue, calibration)
    release = freeze_evaluation(queue, labels, "causal-geometry-v1")
    _preserve_json(directory / "release.json", release)
    _preserve_json(directory / "holdout" / "queue.json", release["holdout_queue"])
    _preserve_json(directory / "holdout" / "study-config.json", release["holdout_queue"]["sealed"]["config"])
    study = directory / "five-year"
    config_path = study / "study-config.json"
    settings = json.loads(config_path.read_text()) if config_path.exists() else {
        "profile": "five-year-v1", "study_id": "gary-five-year-20261010-v1", "id_salt": secrets.token_hex(32),
        "reviewers": deepcopy(queue["sealed"]["config"]["reviewers"]), "detector_version": "causal-geometry-v1",
        "detector_parameter_hash": PARAMETER_HASH,
        "detector_source_file_sha256": sha256(Path(__file__).with_name("patterns.py").read_bytes()).hexdigest(),
        "as_of": "2026-10-09", "context_years": 5, "target_sessions": 20,
        "source_symbols": list(FIVE_YEAR_SYMBOLS), "shuffle_seed": 20261012, "holdout_locked": True}
    sources = _new_sources(cache or directory / "sources")
    original = {source["symbol"] for source in queue["sealed"]["sources"]}
    if original & {source["symbol"] for source in sources}:
        raise ValueError("Exploration overlaps original study sources")
    five_year = build_review_queue(sources, settings)
    _preserve_json(config_path, settings)
    _preserve_json(study / "queue.json", five_year)
    load_release(directory)
    return {"status": "ready", "five_year_cards": len(five_year["cards"]),
            "holdout_cards": len(release["holdout_queue"]["cards"]),
            "release_hash": release["release_hash"], "trading_approval": False}


def build_holdout_context(directory=CYCLE3, cache=CONTEXT_CACHE):
    """Add a separately bound historical view while preserving the original pass."""
    from gary.context_review import build_review_queue as build_context_queue
    directory, cache = Path(directory), Path(cache)
    release = load_release(directory)
    queue = build_context_queue(_new_sources(cache, SAMPLE), {
        "profile": "five-year-assisted-v1", "parent_queue": release["holdout_queue"],
        "parent_release_hash": release["release_hash"]})
    study = directory / "holdout-context"
    # Validate every source and view before making the new pass available.
    for filename in ["artifact-manifest.json", *(f"{symbol}-chart.raw" for symbol in SAMPLE)]:
        target = study / "sources" / filename
        raw = (cache / filename).read_bytes()
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError("Context source changed; existing evidence was preserved")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".tmp")
            with temporary.open("wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
    calibration = load_queue(directory / "calibration")
    overlap_pairs = sum(
        context["raw_window"][0]["date"] <= case["as_of"]
        and context["raw_window"][-1]["date"] >= case["start_date"]
        and queue["sealed"]["cases"][key]["source_id"] == case["source_id"]
        for key, context in queue["sealed"]["context_review"]["cases"].items()
        for case in calibration["sealed"]["cases"].values()
        if case["split"] == "calibration")
    exposure_path = study / "exposure.json"
    available_at = json.loads(exposure_path.read_text())["available_at_utc"] if exposure_path.exists() else datetime.now(timezone.utc).isoformat()
    _preserve_json(exposure_path, {
        "schema_version": "holdout-context-exposure-v1", "view_protocol": "five-year-assisted-v1",
        "queue_hash": queue["queue_hash"], "parent_release_hash": release["release_hash"],
        "available_at_utc": available_at, "original_view_read_only": True,
        "prior_calibration_overlap_pairs": overlap_pairs,
        "limitations": ["Expanded history overlaps previously exposed calibration history.",
                        "Context observations are separate from the original holdout protocol."]})
    _preserve_json(study / "queue.json", queue)
    cycle3_study("holdout", directory)
    return {"status": "ready", "context_cards": len(queue["cards"]),
            "view_protocol": "five-year-assisted-v1", "trading_approval": False}


def report_cycle3(directory=CYCLE3):
    from gary.evaluation import evaluate_detector
    directory = Path(directory)
    release = load_release(directory)
    original = load_queue(directory / "calibration")
    for phase in ("calibration", "holdout"):
        queue = original if phase == "calibration" else release["holdout_queue"]
        labels = load_labels(queue, directory / phase)
        report = evaluate_detector(original, labels, release, phase)
        _write_json(directory / f"{phase}-private-report.json", report)
        if report.get("status") != "pending_labels":
            snapshot = sha256(_json_bytes(report)).hexdigest()
            _preserve_json(directory / "reports" / f"{phase}-{snapshot}.json", report)
    if (directory / "holdout-context" / "queue.json").exists():
        from gary.context_review import summarize_review as summarize_context
        study, queue, _ = cycle3_study("holdout", directory)
        report = summarize_context(queue, load_labels(queue, study))
        report["exposure_audit"] = json.loads((study / "exposure.json").read_text())
        _write_json(study / "private-report.json", report)
        if report.get("status") != "pending_labels":
            _preserve_json(study / "reports" / f"{sha256(_json_bytes(report)).hexdigest()}.json", report)
    return {"status": "saved", "recognition_scores": "coordinator-private"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "report", "cycle3", "report-cycle3", "holdout-context"))
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--study-dir", type=Path)
    args = parser.parse_args(argv)
    directory = args.study_dir or (CYCLE3 if args.action in {"cycle3", "report-cycle3", "holdout-context"} else DEFAULT_STUDY)
    if args.action == "cycle3":
        print(json.dumps(build_cycle3(directory), indent=2))
    elif args.action == "report-cycle3":
        print(json.dumps(report_cycle3(directory), indent=2))
    elif args.action == "holdout-context":
        print(json.dumps(build_holdout_context(directory, args.cache_dir or CONTEXT_CACHE), indent=2))
    elif args.action == "build":
        print(json.dumps(build_study(args.cache_dir or ROOT / "private" / "coverage", directory), indent=2))
    else:
        queue = load_queue(directory)
        if "context_review" in queue["sealed"]:
            from gary.context_review import summarize_review as summarize_context
            result = summarize_context(queue, load_labels(queue, directory))
        else:
            result = summarize_review(queue, load_labels(queue, directory))
        _write_json(directory / "private-report.json", result)
        print("Private calibration report saved. Reviewer scores remain hidden; holdout remains locked.")


if __name__ == "__main__":
    main()
