"""Independently check the assisted view; mutate only a temporary study copy.

The real study is used only for source/presentation validation and byte hashes.
No primary judgment or detector answer is interpreted or printed. All invented
labels, retries, revisions, recovery and rollback probes use disposable copies.
The source collector is never invoked and no network market-data request occurs.
"""

import argparse
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path
import select
import shutil
from statistics import median
import subprocess
import sys
import tempfile
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from gary.context_review import build_review_queue, record_review_label, summarize_review
from gary.review_preview import (
    CYCLE3, ROOT, build_holdout_context, cycle3_study, load_release, reviewer_view,
)


PROTOCOL = "five-year-assisted-v1"
BAR_FIELDS = {"offset", "open", "high", "low", "close", "volume"}
CARD_FIELDS = {"case_id", "bars", "target_start_offset", "target_end_offset",
               "price_basis", "volume_available"}
LABEL_FIELDS = {"case_id", "reviewer_id", "reviewer_role", "decision", "rationale",
                "revision", "events"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_digest(path):
    return sha256(path.read_bytes()).hexdigest() if path.exists() else None


def original_guard():
    baseline = json.loads((ROOT / "private/holdout-context/original-hashes.json").read_text())
    require(len(baseline) == 44, "Original preservation baseline must contain 44 files")
    require(all(file_digest(ROOT / filename) == expected for filename, expected in baseline.items()),
            "Original artifact byte hash changed")
    return len(baseline)


def retained_sources(cache):
    """Decode retained raw bytes independently of the production source adapter."""
    rows = json.loads((cache / "artifact-manifest.json").read_text())
    require(len(rows) == 8 and len({row["symbol"] for row in rows}) == 8,
            "Retained context source manifest must contain eight distinct sources")
    sources = []
    for row in rows:
        require(row["file"] == f'{row["symbol"]}-chart.raw' and row["status"] == 200,
                "Unexpected retained source manifest entry")
        raw = (cache / row["file"]).read_bytes()
        require(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"],
                "Retained raw source hash or length changed")
        data = json.loads(raw)["chart"]["result"][0]
        require(data["meta"]["symbol"] == row["symbol"] and data["meta"]["instrumentType"] == "EQUITY",
                "Retained raw source identity/type mismatch")
        zone = ZoneInfo(data["meta"]["exchangeTimezoneName"])
        stamps = data["timestamp"]
        quote = data["indicators"]["quote"][0]
        arrays = [quote[field] for field in ("open", "high", "low", "close", "volume")]
        arrays.append(data["indicators"]["adjclose"][0]["adjclose"])
        require(stamps and all(len(array) == len(stamps) for array in arrays),
                "Retained raw source arrays are incomplete")
        require(all(type(stamp) in (int, float) and isfinite(stamp) for stamp in stamps)
                and all(a < b for a, b in zip(stamps, stamps[1:])),
                "Retained raw timestamps are invalid or unordered")
        bars = [{"date": datetime.fromtimestamp(stamp, zone).date().isoformat(),
                 **{field: quote[field][index] for field in ("open", "high", "low", "close", "volume")}}
                for index, stamp in enumerate(stamps)]
        require(all(a["date"] < b["date"] for a, b in zip(bars, bars[1:])),
                "Retained raw session dates are unordered or repeated")
        for bar in bars:
            values = [bar[field] for field in ("open", "high", "low", "close", "volume")]
            require(all(type(value) in (int, float) and isfinite(value) for value in values),
                    "Retained raw source contains nonnumeric OHLCV")
            opening, high, low, close, volume = values
            require(0 < low <= opening <= high and low <= close <= high and volume >= 0,
                    "Retained raw OHLCV is invalid")
        fetched = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
        require(fetched.tzinfo is not None and bars[-1]["date"] <= fetched.astimezone(zone).date().isoformat(),
                "Retained raw source has a future session")
        sources.append(dict(source_id=row["symbol"], symbol=row["symbol"], source_sha256=row["sha256"],
                            fetched_at=row["fetched_at"], exchange_timezone=str(zone),
                            price_basis="provider_received_ohlc", bars=bars,
                            split_dates=sorted(datetime.fromtimestamp(event["date"], zone).date().isoformat()
                                               for event in data.get("events", {}).get("splits", {}).values())))
    return sources


def empty_labels(queue):
    return dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[])


def projection_check(view, *, overview=True):
    expected = {"card", "own_label", "view_token"} | ({"overview"} if overview else set())
    require(set(view) == expected, "Card projection has fields outside the public whitelist")
    require(set(view["card"]) == CARD_FIELDS, "Detail card has fields outside the anonymous whitelist")
    if overview:
        require(set(view["overview"]) == CARD_FIELDS | {"split_offsets"},
                "Overview has fields outside the anonymous whitelist")
    for card in [view["card"]] + ([view["overview"]] if overview else []):
        require(all(set(bar) == BAR_FIELDS for bar in card["bars"]),
                "Projected bars have fields outside normalized relative offsets/OHLCV")
        require(card["bars"][0]["close"] == 100 and card["bars"][-1]["offset"] == 0,
                "Projected chart has an incorrect index base or endpoint")
        require([bar["offset"] for bar in card["bars"]] == list(range(1 - len(card["bars"]), 1)),
                "Projected offsets are discontinuous")
        require(card["target_start_offset"] == -19 and card["target_end_offset"] == 0,
                "Projected final-20 target changed")
    if view["own_label"] is not None:
        label = view["own_label"]
        require(set(label) == LABEL_FIELDS and all(set(event) == {"kind", "completion_offset"}
                                                 for event in label["events"]),
                "Own-label projection contains private fields")


def actual_view_check(directory):
    release = load_release(directory)
    study, queue, readonly = cycle3_study("holdout", directory)
    require(study == directory / "holdout-context" and readonly is False,
            "Holdout alias did not select the separate assisted view")
    parent = release["holdout_queue"]
    sources = retained_sources(study / "sources")
    settings = dict(profile=PROTOCOL, parent_queue=parent, parent_release_hash=release["release_hash"])
    before = digest((sources, settings))
    expected = build_review_queue(sources, settings)
    require(expected == queue and build_review_queue(sources, settings) == expected,
            "Actual assisted queue differs from release/source reconstruction")
    require(digest((sources, settings)) == before, "Queue reconstruction mutated its inputs")
    require(len(queue["cards"]) == 13 and queue["cards"] == parent["cards"] and queue["order"] == parent["order"],
            "Original 13-card detail presentation or order changed")
    restored = deepcopy(queue)
    context = restored["sealed"].pop("context_review")
    restored["queue_hash"] = parent["queue_hash"]
    require(restored == parent and context["parent_queue"] == parent
            and context["parent_release_hash"] == release["release_hash"],
            "Original released queue payload or parent commitments changed")
    require(context["protocol"] == PROTOCOL and queue["queue_hash"] != parent["queue_hash"],
            "Additional view is not separately bound")
    by_source = {item["source_id"]: item for item in sources}
    split_cases = 0
    counts = []
    labels = empty_labels(queue)
    public = reviewer_view(queue, labels, "gary")
    require(set(public) == {"reviewer_id", "reviewer_role", "order", "progress", "own_labels"}
            and public["own_labels"] == {} and public["progress"] == {"total": 13, "labeled": 0},
            "Queue projection contains private fields or inherited observations")
    for key in queue["order"]:
        # Only source identity, dates and OHLCV are inspected from private cases.
        case = parent["sealed"]["cases"][key]
        cutoff = date.fromisoformat(case["as_of"])
        start = cutoff.replace(year=cutoff.year - 5,
                               day=28 if cutoff.month == 2 and cutoff.day == 29 else cutoff.day)
        item = by_source[case["source_id"]]
        window = [bar for bar in item["bars"] if start.isoformat() < bar["date"] <= cutoff.isoformat()]
        retained = context["cases"][key]
        require(retained["raw_window"] == window and retained["requested_start"] == start.isoformat()
                and retained["window_hash"] == digest(window),
                "Actual context is not the exact open-left historical prefix")
        require(1254 <= len(window) <= 1259 and (date.fromisoformat(window[0]["date"]) - start).days <= 7
                and window[-1]["date"] == cutoff.isoformat(), "Actual context coverage changed")
        require(window[-180:] == case["raw_window"]
                and [bar["date"] for bar in window[-180:]] == case["visible_dates"],
                "Actual final 180 sessions differ from the released detector input")
        view = reviewer_view(queue, labels, "gary", key)
        projection_check(view)
        require(view["view_token"] == queue["queue_hash"] and view["card"] == parent["cards"][key]
                and view["overview"] == retained["overview"] and view["own_label"] is None,
                "Actual card binding or anonymous projection changed")
        price_base, volume_base = window[0]["close"], median(bar["volume"] for bar in window)
        require(all(isclose(shown[field], raw[field] / price_base * 100, rel_tol=1e-12)
                    for shown, raw in zip(view["overview"]["bars"], window)
                    for field in ("open", "high", "low", "close")), "Overview price normalization changed")
        require(all(isclose(shown["volume"], raw["volume"] / volume_base, rel_tol=1e-12)
                    for shown, raw in zip(view["overview"]["bars"], window)),
                "Overview volume normalization changed")
        offsets = sorted({next(index - len(window) + 1 for index, bar in enumerate(window)
                               if bar["date"] >= event)
                          for event in item["split_dates"] if window[0]["date"] <= event <= window[-1]["date"]})
        require(view["overview"]["split_offsets"] == offsets, "Anonymous reported-split marker offsets changed")
        split_cases += bool(offsets)
        counts.append(len(window))
    require(split_cases == 3 and min(counts) == 1254 and max(counts) == 1259,
            "Actual aggregate context/split evidence changed")
    original, preserved, original_readonly = cycle3_study("holdout-original", directory)
    require(original == directory / "holdout" and preserved == parent and original_readonly,
            "Preserved original holdout is not read-only")
    return queue, {"context_cards": len(counts), "context_sessions_min": min(counts),
                   "context_sessions_max": max(counts), "split_marker_cases": split_cases,
                   "release_source_reconstruction": True, "normalized_anonymous_projection": True,
                   "exact_original_detail_and_last_180": True}


def submission(queue, reviewer="gary", *, revision=0, revise=False, decision="none"):
    return dict(case_id=queue["order"][0], reviewer_id=reviewer, decision=decision, events=[],
                rationale="Disposable protocol probe; no real chart judgment", expected_revision=revision,
                revise=revise, view_token=queue["queue_hash"])


def snapshot_files(directory):
    return {str(path.relative_to(directory)): file_digest(path)
            for path in directory.rglob("*") if path.is_file()}


def synthetic_seam_check():
    # The existing synthetic fixture constructs a valid parent for the already
    # confirmed queue/label/summary seams; no real label artifact is loaded.
    sys.path.insert(0, str(ROOT / "tests"))
    from test_context_review import study as synthetic_study
    sources, settings = synthetic_study()
    queue = build_review_queue(sources, settings)
    labels = empty_labels(queue)
    reviewers = list(queue["sealed"]["config"]["reviewers"])
    first = submission(queue, reviewers[0])
    first.update(view_protocol="forged-client-value", overview_hash="0" * 64)
    before = digest((queue, labels, first))
    recorded = record_review_label(queue, labels, first)
    require(digest((queue, labels, first)) == before, "Label seam mutated its inputs")
    require(recorded["entries"][0]["view_protocol"] == PROTOCOL
            and recorded["entries"][0]["overview_hash"] == digest(
                queue["sealed"]["context_review"]["cases"][first["case_id"]]["overview"]),
            "Label provenance was accepted from the client instead of derived from the view")
    require(record_review_label(queue, recorded, first) == recorded, "Public seam retry duplicated the label")
    report = summarize_review(queue, recorded)
    require(report["phase"] == "holdout_context" and report["original_holdout_comparable"] is False
            and report["status"] == "pending_labels" and report["recognition_agreement"] is None
            and report["consensus"] is None, "Partial context summary exposes or conflates recognition")
    for reviewer in reviewers:
        for key in queue["order"]:
            entry = submission(queue, reviewer)
            entry["case_id"] = key
            labels = record_review_label(queue, labels, entry)
    report = summarize_review(queue, labels)
    require(report["phase"] == "holdout_context" and report["original_holdout_comparable"] is False
            and report["recognition_agreement"] is not None, "Complete synthetic summary has incorrect view interpretation")
    other = record_review_label(queue, empty_labels(queue), submission(queue, reviewers[1]))
    require(reviewer_view(queue, other, reviewers[0])["own_labels"] == {}
            and reviewer_view(queue, other, reviewers[0], queue["order"][0])["own_label"] is None,
            "Another reviewer observation leaked")
    require(report["reference_detector_input_sessions"] == 180,
            "Context summary changed the frozen reference detector input")
    return {"synthetic_public_seams": True, "partial_metrics_withheld": True,
            "queue_derived_label_provenance": True, "other_reviewer_hidden": True}


def tamper_check(directory):
    queue_path = directory / "holdout-context/queue.json"
    release_path = directory / "release.json"
    original_queue, original_release = queue_path.read_bytes(), release_path.read_bytes()
    try:
        queue = json.loads(original_queue)
        key = queue["order"][0]
        context = queue["sealed"]["context_review"]["cases"][key]
        for field in ("open", "high", "low", "close"):
            context["raw_window"][0][field] *= 1.01
        context["window_hash"] = digest(context["raw_window"])
        base = context["raw_window"][0]["close"]
        for shown, raw in zip(context["overview"]["bars"], context["raw_window"]):
            for field in ("open", "high", "low", "close"):
                shown[field] = raw[field] / base * 100
        queue["queue_hash"] = digest({field: value for field, value in queue.items() if field != "queue_hash"})
        # Internal consistency alone is insufficient: the runtime must retain
        # the external release/raw-source reconstruction anchor.
        summarize_review(queue, empty_labels(queue))
        queue_path.write_text(json.dumps(queue))
        try:
            cycle3_study("holdout", directory)
        except ValueError:
            pass
        else:
            raise ValueError("Coherent context raw/projection/hash tampering bypassed retained-source reconstruction")
        queue_path.write_bytes(original_queue)
        for field in ("review_source_file_sha256", "protocol_hash"):
            release = json.loads(original_release)
            release["evaluator_manifest"][field] = "0" * 64
            release["release_hash"] = digest({key: value for key, value in release.items() if key != "release_hash"})
            release_path.write_text(json.dumps(release))
            try:
                cycle3_study("holdout", directory)
            except ValueError:
                pass
            else:
                raise ValueError("Altered frozen release source/protocol anchor was accepted")
            release_path.write_bytes(original_release)
        return {"coherent_context_tamper_rejected": True, "frozen_release_anchor_tamper_rejected": True}
    finally:
        queue_path.write_bytes(original_queue)
        release_path.write_bytes(original_release)


def http_probe(directory, queue, port):
    """Launch the production HTTP entrypoint against a disposable study copy."""
    base = f"http://127.0.0.1:{port}"
    original_journal = directory / "holdout/labels.journal.jsonl"
    study = directory / "holdout-context"
    for filename in ("labels.json", "labels.journal.jsonl"):
        path = study / filename
        if path.exists():
            path.unlink()  # exclusively the TemporaryDirectory copy
    process = None
    durations = []

    def request(path, entry=None, *, headers=None):
        supplied = {"Origin": base, **(headers or {})}
        raw = None if entry is None else json.dumps(entry).encode()
        if raw is not None:
            supplied["Content-Type"] = "application/json"
        req = Request(base + path, data=raw, headers=supplied, method="GET" if entry is None else "POST")
        started = perf_counter()
        try:
            with urlopen(req, timeout=45) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())
        finally:
            durations.append(perf_counter() - started)

    def start():
        child = subprocess.Popen([sys.executable, "-m", "gary.preview", "--port", str(port),
                                  "--reviewer", "gary", "--cycle-3", "--cycle-3-dir", str(directory)],
                                 cwd=directory.parent, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            ready, _, _ = select.select([child.stdout], [], [], 15)
            require(ready and child.stdout.readline().decode().strip().endswith(base)
                    and child.poll() is None, "Isolated HTTP child failed to bind its port")
            require(request("/health")[0] == 200, "Isolated HTTP child did not become ready")
            return child
        except BaseException:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            child.stdout.close()
            raise

    def journals():
        return file_digest(original_journal), file_digest(study / "labels.journal.jsonl"), file_digest(study / "labels.json")

    def reject_tokens():
        for token in (None, "0" * 64, queue["sealed"]["context_review"]["parent_queue"]["queue_hash"]):
            entry = submission(queue)
            if token is None:
                entry.pop("view_token")
            else:
                entry["view_token"] = token
            before = journals()
            require(request(route, entry)[0] == 400 and journals() == before,
                    "Missing/wrong/original-view token changed label persistence")

    route = "/api/review/label?study=holdout"
    key = queue["order"][0]
    card_route = "/api/review/card?" + urlencode(dict(study="holdout", id=key))
    try:
        process = start()
        status, initial = request(card_route)
        require(status == 200 and initial["view_token"] == queue["queue_hash"] and initial["own_label"] is None,
                "HTTP card did not expose the separately bound anonymous context")
        require(set(initial) == {"card", "overview", "own_label", "view_token", "study_key", "read_only", "studies", "view_profile"},
                "HTTP card response leaks a nonpublic field")
        projection_check({field: initial[field] for field in ("card", "overview", "own_label", "view_token")})
        reject_tokens()
        for path, entry, headers, status in (
            (route, submission(queue, "agent-qa"), None, 403),
            (route + "&reviewer=agent-qa", submission(queue), None, 403),
            (route, submission(queue), {"Origin": "https://foreign.example"}, 403),
            (route, submission(queue), {"Host": "foreign.example"}, 403),
            ("/api/review/label?study=holdout-original", submission(queue), None, 403),
        ):
            before = journals()
            require(request(path, entry, headers=headers)[0] == status and journals() == before,
                    "Foreign reviewer/origin/host or original-view write was not rejected without writes")
        for path in ("/api/review/report", "/api/review/summary", "/api/review/queue", "/private/cycle-3/release.json",
                     "/api/review?study=holdout-context", "/api/review?study=../holdout-context"):
            require(request(path)[0] == 404, "A private/unregistered HTTP route was exposed")
        status, saved = request(route, submission(queue))
        require(status == 200 and saved["own_label"]["revision"] == 1, "Valid token-bound HTTP save failed")
        first = journals()
        require(request(route, submission(queue))[0] == 200 and journals() == first,
                "Identical HTTP retry changed the journal/materialized label")
        before = journals()
        require(request(route, submission(queue, decision="uncertain"))[0] == 400 and journals() == before,
                "Conflicting HTTP save lacked explicit revision protection")
        status, revised = request(route, submission(queue, revision=1, revise=True, decision="uncertain"))
        require(status == 200 and revised["own_label"]["revision"] == 2, "Explicit HTTP revision failed")
        (study / "labels.json").unlink()
        status, recovered = request(card_route)
        require(status == 200 and recovered["own_label"] == revised["own_label"], "Journal failed to recover materialized-view loss")
        with (study / "labels.journal.jsonl").open("ab") as stream:
            stream.write(b'{"interrupted":')
        process.terminate()
        process.wait(timeout=5)
        process.stdout.close()
        process = start()
        status, recovered = request(card_route)
        require(status == 200 and recovered["own_label"] == revised["own_label"],
                "Restart failed to ignore an incomplete unacknowledged journal tail")
        reject_tokens()  # rejection must not repair a partial journal or recreate a lost cache
        status, third = request(route, submission(queue, revision=2, revise=True, decision="invalid"))
        require(status == 200 and third["own_label"]["revision"] == 3
                and (study / "labels.journal.jsonl").read_bytes().endswith(b"\n")
                and len(list(study.glob("interrupted-journal-*.raw"))) == 1,
                "Next valid save failed to archive the interrupted tail and preserve revision history")
        require(file_digest(original_journal) == first[0], "Isolated protocol probes modified the preserved original journal")
        # Removing the context view after exposure must never reopen the old pass.
        (study / "queue.json").rename(study / "queue.saved.json")
        status, fallback = request("/api/review?study=holdout")
        require(status == 200 and fallback["read_only"] is True,
                "Context view loss did not preserve original read-only metadata")
        before = journals()
        require(request("/api/review/label?study=holdout", submission(queue))[0] in (400, 403, 503)
                and journals() == before, "Context rollback/view loss reopened the original holdout for writes")
        return {"http_token_rejection_without_writes": True, "http_save_retry_revision": True,
                "journal_loss_partial_tail_restart": True, "private_routes_and_origin_reviewer_boundaries": True,
                "original_readonly_after_view_loss": True, "http_requests": len(durations),
                "max_http_request_seconds": round(max(durations), 3)}
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        if process is not None:
            process.stdout.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=CYCLE3, help="cycle-3 study root; never modified")
    parser.add_argument("--port", type=int, default=4176, help="isolated local HTTP probe port")
    args = parser.parse_args(argv)
    directory = args.study_dir.resolve()
    preserved = original_guard()
    actual_before = snapshot_files(directory / "holdout-context")
    queue, results = actual_view_check(directory)
    results.update(synthetic_seam_check())
    with tempfile.TemporaryDirectory(prefix="gary-context-qa-") as temporary:
        copied = Path(temporary) / "cycle-3"
        shutil.copytree(directory, copied)
        before = snapshot_files(copied)
        build_holdout_context(copied, copied / "holdout-context/sources")
        require(snapshot_files(copied) == before, "Same-input rebuild changed existing study/label bytes")
        results["immutable_same_input_rebuild"] = True
        results.update(tamper_check(copied))
        results.update(http_probe(copied, queue, args.port))
    require(snapshot_files(directory / "holdout-context") == actual_before,
            "Actual context study/source/label bytes changed during read-only QA")
    require(original_guard() == preserved, "Original baseline changed during QA")
    print(json.dumps({"status": "passed", "original_files_unchanged": preserved,
                      "actual_study_read_only_during_qa": True,
                      "primary_labels_or_predictions_interpreted": False, **results}, indent=2))


if __name__ == "__main__":
    main()
