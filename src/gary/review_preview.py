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
SAMPLE = ("MU", "AMGN", "SIRI", "META", "ORCL", "TSM", "O", "ARCC")
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
            labels = record_review_label(queue, labels, record["submission"])
    return labels


def save_label(queue, entry, directory=DEFAULT_STUDY):
    """Append and fsync before acknowledgment; retries recover a missing JSON cache."""
    directory = Path(directory)
    current = load_labels(queue, directory)
    updated = record_review_label(queue, current, entry)
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
        return {"card": deepcopy(queue["cards"][case_id]), "own_label": _own_label(latest.get(case_id))}
    return {"reviewer_id": reviewer_id, "reviewer_role": reviewers[reviewer_id]["role"], "order": queue["order"],
            "progress": {"total": len(queue["cards"]), "labeled": len(latest)},
            "own_labels": {case: _own_label(label) for case, label in latest.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "report"))
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "private" / "coverage")
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    args = parser.parse_args(argv)
    if args.action == "build":
        print(json.dumps(build_study(args.cache_dir, args.study_dir), indent=2))
    else:
        queue = load_queue(args.study_dir)
        result = summarize_review(queue, load_labels(queue, args.study_dir))
        _write_json(args.study_dir / "private-report.json", result)
        print("Private calibration report saved. Reviewer scores remain hidden; holdout remains locked.")


if __name__ == "__main__":
    main()
