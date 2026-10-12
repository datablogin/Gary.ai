"""Synthetic behavior checks at the four approved pure training seams."""

from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path

import pytest

from gary import training


MANIFEST = dict(version="causal-geometry-v1",
                parameter_hash="d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae",
                source_file_sha256="76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def synthetic_source(number=0, predicted=False, cutoff="2025-04-11"):
    """Retained synthetic five-year series; no real identity or judgment."""
    end = date.fromisoformat(cutoff)
    start = end.replace(year=end.year - 5, day=28 if end.month == 2 and end.day == 29 else end.day)
    bars, day = [], start
    while day <= end:
        if day.weekday() < 5 or day in (start, end):
            bars.append(dict(date=day.isoformat(), open=120, high=121, low=119, close=120, volume=1000))
        day += timedelta(days=1)
    if predicted:
        drawn = json.loads((Path(__file__).parent / "fixtures/pattern-inverse.json").read_text())["bars"]
        for index, bar in enumerate(drawn):
            bars[-len(drawn) + index].update({key: value for key, value in bar.items() if key != "date"})
    identity = f"synthetic-issuer-{number}"
    source_id, symbol = f"synthetic-source-{number}", f"SYNTHETIC{number}"
    return dict(source_id=source_id, symbol=symbol, canonical_id=identity, aliases=[source_id, symbol],
                alias_evidence=dict(reviewed=True, receipt_sha256="a" * 64, provenance="synthetic lineage receipt"),
                classification=dict(reviewed=True, security_type="operating_common", exchange="NASDAQ",
                                    evidence_sha256="b" * 64, provenance="synthetic classification receipt"),
                source_sha256="c" * 64, fetched_at="2026-10-12T12:00:00+00:00",
                exchange_timezone="America/New_York", price_basis="provider_received_ohlc",
                split_dates=[], bars=bars, cutoffs=[cutoff])


def exposure(sources):
    return dict(schema_version="training-exposure-v1", complete=True,
                evidence=[dict(path="synthetic/legacy-receipt.json", received_sha256="d" * 64)],
                aliases={alias: item["canonical_id"] for item in sources for alias in item["aliases"]},
                targets=[], views=[], reservations=[])


def config(sources):
    return dict(profile="training-five-year-v1", reviewer_id="gary", random_seed=20261010,
                shuffle_seed=20261011, id_salt="synthetic-training", detector_manifest=deepcopy(MANIFEST),
                exposure=exposure(sources))


def empty_labels(queue):
    return dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[])


def entry(queue, case_id=None, decision="none", revision=0, revise=False):
    return dict(case_id=case_id or queue["order"][0], reviewer_id="gary", decision=decision,
                rationale="Synthetic engineering control.", events=[], expected_revision=revision,
                revise=revise, view_token=queue["queue_hash"])


def round_fixture(count=2):
    """Concrete A3 create/resume fixture through the approved request seam."""
    sources = [synthetic_source(number) for number in range(count)]
    settings = config(sources)
    catalog = dict(schema_version="training-catalog-v1", sources=sources, exposure=settings["exposure"])
    history = dict(schema_version="training-history-v1", exposure=deepcopy(settings["exposure"]), rounds=[], requests={})
    request = dict(request_id="synthetic-click-1", config={key: value for key, value in settings.items() if key != "exposure"})
    return catalog, history, request


def acknowledge_label(history, round_id, submitted):
    """Adapter recipe, composed exclusively from the approved label/summary seams."""
    result = deepcopy(history)
    round_record = next(row for row in result["rounds"] if row["round_id"] == round_id)
    round_record["labels"] = training.record_review_label(round_record["queue"], round_record["labels"], submitted)
    summary = training.summarize_review(round_record["queue"], round_record["labels"])
    round_record.update(status=summary["status"], snapshots=summary["snapshots"])
    return result


def test_builder_freezes_anonymous_five_year_view_and_separate_raw180_reference():
    sources = [synthetic_source(predicted=True)]
    settings = config(sources)
    before = deepcopy((sources, settings))
    queue = training.build_review_queue(sources, settings)
    key = queue["order"][0]
    case = queue["sealed"]["cases"][key]
    assert queue["schema_version"] == "pattern-training-review-v1"
    assert len(case["raw_window"]) == 180 and len(case["raw_context"]) == 1305
    assert case["raw_window"] == case["raw_context"][-180:]
    assert case["memberships"] == ["random", "enriched"]
    assert set(queue["cards"][key]) == {"case_id", "bars", "target_start_offset", "target_end_offset",
                                        "price_basis", "volume_available", "overview"}
    assert queue["sealed"]["reference"]["context_sessions"] == 180
    assert queue["queue_hash"] == digest({name: value for name, value in queue.items() if name != "queue_hash"})
    assert (sources, settings) == before
    assert training.build_review_queue(sources, settings) == queue


@pytest.mark.parametrize("missing", ["exposure", "complete", "evidence", "aliases"])
def test_missing_legacy_exposure_evidence_never_allocates_a_round(missing):
    sources = [synthetic_source()]
    settings = config(sources)
    if missing == "exposure":
        del settings["exposure"]
    elif missing == "complete":
        settings["exposure"]["complete"] = False
    elif missing == "evidence":
        settings["exposure"]["evidence"] = []
    else:
        settings["exposure"]["aliases"] = {}
    queue = training.build_review_queue(sources, settings)
    assert queue["order"] == [] and queue["sealed"]["exclusions"]


@pytest.mark.parametrize("field,value", [("classification", None), ("alias_evidence", None),
                                         ("source_sha256", "bad"), ("exchange_timezone", "bad"),
                                         ("fetched_at", "2026-10-12T12:00:00"),
                                         ("price_basis", "adjusted"), ("aliases", [])])
def test_unverified_sources_are_excluded_without_financial_clearance(field, value):
    sources = [synthetic_source()]
    sources[0][field] = value
    queue = training.build_review_queue(sources, config(sources))
    assert queue["order"] == [] and queue["sealed"]["exclusions"]


@pytest.mark.parametrize("field,value", [("profile", "legacy"), ("reviewer_id", ""), ("random_seed", True),
                                         ("shuffle_seed", 1.0), ("id_salt", ""),
                                         ("detector_manifest", MANIFEST | {"parameter_hash": "0" * 64}),
                                         ("max_cases", 99)])
def test_only_frozen_training_config_and_trusted_v1_are_allowed(field, value):
    sources = [synthetic_source()]
    settings = config(sources) | {field: value}
    with pytest.raises(ValueError):
        training.build_review_queue(sources, settings)


@pytest.mark.parametrize("sessions,gap,accepted", [(1199, 1, False), (1200, 1, True),
                                                 (1200, 7, True), (1200, 8, False)])
def test_five_year_context_requires_literal_session_count_and_start_gap(sessions, gap, accepted):
    source = synthetic_source()
    start = date(2020, 4, 11) + timedelta(days=gap)
    remaining = [bar for bar in source["bars"] if bar["date"] > start.isoformat()]
    first = dict(date=start.isoformat(), open=120, high=121, low=119, close=120, volume=1000)
    source["bars"] = [source["bars"][0], first, *remaining[-(sessions - 1):]]
    queue = training.build_review_queue([source], config([source]))
    assert bool(queue["order"]) is accepted


def test_leap_anniversary_is_open_left_and_later_retained_bars_never_enter_case():
    source = synthetic_source(cutoff="2024-02-29")
    source["bars"].append(dict(date="2024-03-01", open=1, high=2, low=1, close=2, volume=1))
    queue = training.build_review_queue([source], config([source]))
    case = queue["sealed"]["cases"][queue["order"][0]]
    assert case["requested_start"] == "2019-02-28"
    assert case["raw_context"][0]["date"] == "2019-03-01" and case["as_of"] == "2024-02-29"
    assert case["raw_window"][-1]["date"] == "2024-02-29"


@pytest.mark.parametrize("change", ["finite", "boolean", "ohlc", "volume", "duplicate", "ordered",
                                    "split", "endpoint", "future", "duplicate_cutoff"])
def test_malformed_full_sources_or_uncompleted_cutoffs_are_excluded(change):
    source = synthetic_source()
    if change == "finite":
        source["bars"][0]["close"] = float("inf")
    elif change == "boolean":
        source["bars"][0]["volume"] = True
    elif change == "ohlc":
        source["bars"][0]["low"] = 122
    elif change == "volume":
        source["bars"][0]["volume"] = -1
    elif change == "duplicate":
        source["bars"].insert(1, deepcopy(source["bars"][0]))
    elif change == "ordered":
        source["bars"].reverse()
    elif change == "split":
        source["split_dates"] = ["2021-04-12"]
    elif change == "endpoint":
        source["bars"].pop()
    elif change == "future":
        source["cutoffs"] = ["2027-01-01"]
    else:
        source["cutoffs"].append(source["cutoffs"][0])
    queue = training.build_review_queue([source], config([source]))
    assert queue["order"] == [] and queue["sealed"]["exclusions"]


@pytest.mark.parametrize("blocked", ["target", "alias_target", "exact_window", "reserved_source", "reserved_interval"])
def test_prior_targets_exact_windows_and_active_validation_reservations_block_admission(blocked):
    source = synthetic_source()
    settings = config([source])
    row = dict(canonical_id=source["canonical_id"], start="2025-04-11", end="2025-04-11",
               provenance="synthetic prior queue receipt")
    if blocked in {"target", "alias_target", "exact_window"}:
        row["case_fingerprint"] = "e" * 64
        if blocked == "alias_target":
            row["canonical_id"] = source["symbol"]
        elif blocked == "exact_window":
            prior = training.build_review_queue([source], settings)
            row.update(start="2010-01-01", end="2010-01-02",
                       case_fingerprint=prior["sealed"]["cases"][prior["order"][0]]["window_hash"])
        settings["exposure"]["targets"].append(row)
    else:
        row["active"] = True
        if blocked == "reserved_source":
            row.update(start="2030-01-01", end="2030-01-02")
        else:
            settings["exposure"]["aliases"]["other-source"] = "other-issuer"
            row["canonical_id"] = "other-issuer"
        settings["exposure"]["reservations"].append(row)
    queue = training.build_review_queue([source], settings)
    assert queue["order"] == [] and queue["sealed"]["exclusions"]


def test_broader_prior_view_overlap_is_recorded_as_development_exposure():
    source = synthetic_source()
    settings = config([source])
    settings["exposure"]["views"] = [dict(canonical_id=source["symbol"], start="2021-01-01", end="2022-01-01",
                                          provenance="synthetic displayed prior overview")]
    queue = training.build_review_queue([source], settings)
    case = queue["sealed"]["cases"][queue["order"][0]]
    assert case["prior_view_overlap"] == settings["exposure"]["views"]
    assert case["development_only"] is True


def test_sampling_is_bounded_reproducible_and_records_actual_explicit_frames():
    sources = [synthetic_source(number, predicted=number < 8) for number in range(16)]
    queue = training.build_review_queue(sources, config(sources))
    cases = queue["sealed"]["cases"].values()
    assert 6 <= len(queue["order"]) <= 12
    assert sum("random" in case["memberships"] for case in cases) == 6
    assert sum("enriched" in case["memberships"] for case in cases) == 6
    frame = queue["sealed"]["sampling_frames"]
    assert frame["random"]["size"] == 16 and frame["enriched"]["size"] == 8
    assert frame["random"]["candidates"][0]["as_of"] == "2025-04-11"
    assert training.build_review_queue(list(reversed(sources)), config(sources)) == queue


def test_canonical_alias_duplicate_windows_enter_sampling_frame_once():
    original = synthetic_source(predicted=True)
    alias = deepcopy(original)
    alias.update(source_id="synthetic-source-alias", symbol="SYNTHETIC_ALIAS",
                 aliases=["synthetic-source-alias", "SYNTHETIC_ALIAS"])
    sources = [original, alias]
    queue = training.build_review_queue(sources, config(sources))
    assert len(queue["order"]) == 1
    assert queue["sealed"]["sampling_frames"]["random"]["size"] == 1
    assert queue["sealed"]["sampling_frames"]["enriched"]["size"] == 1


def test_a_batch_contains_distinct_target_intervals_for_each_canonical_issuer():
    source = synthetic_source()
    source["cutoffs"] = ["2025-04-10", "2025-04-11"]
    queue = training.build_review_queue([source], config([source]))
    assert len(queue["order"]) == 1
    assert queue["sealed"]["sampling_frames"]["random"]["size"] == 2
    assert any(row["reason"] == "overlapping target in this batch" for row in queue["sealed"]["exclusions"])


def test_one_human_save_derives_stamps_and_identical_retry_preserves_history():
    sources = [synthetic_source()]
    queue = training.build_review_queue(sources, config(sources))
    labels, submitted = empty_labels(queue), entry(queue)
    before = deepcopy((queue, labels, submitted))
    saved = training.record_review_label(queue, labels, submitted)
    row = saved["entries"][0]
    assert row["revision"] == 1 and row["supersedes_revision"] is None and row["reviewer_role"] == "human"
    assert row["view_token"] == queue["queue_hash"] and row["view_protocol"] == "training-five-year-v1"
    assert row["reference_hash"] == queue["sealed"]["reference"]["commitment_hash"]
    assert row["overview_hash"] == digest(queue["cards"][row["case_id"]]["overview"])
    assert row["detector_version"] == "causal-geometry-v1" and row["reference_detector_input_sessions"] == 180
    assert training.record_review_label(queue, saved, submitted) == saved
    assert (queue, labels, submitted) == before


@pytest.mark.parametrize("token", [None, "old-token"])
def test_missing_or_stale_view_token_fails_before_any_history_validation(token):
    sources = [synthetic_source()]
    queue = training.build_review_queue(sources, config(sources))
    submitted = entry(queue)
    if token is None:
        del submitted["view_token"]
    else:
        submitted["view_token"] = token
    labels = {"entries": "corrupt unacknowledged materialization"}
    with pytest.raises(ValueError, match="exact current view token"):
        training.record_review_label(queue, labels, submitted)


def test_changed_label_requires_explicit_current_revision_and_preserves_superseded_row():
    sources = [synthetic_source()]
    queue = training.build_review_queue(sources, config(sources))
    saved = training.record_review_label(queue, empty_labels(queue), entry(queue))
    changed = entry(queue, decision="uncertain")
    with pytest.raises(ValueError):
        training.record_review_label(queue, saved, changed)
    with pytest.raises(ValueError):
        training.record_review_label(queue, saved, changed | {"revise": True, "expected_revision": 0})
    revised = training.record_review_label(queue, saved, changed | {"revise": True, "expected_revision": 1})
    assert revised["entries"][0] == saved["entries"][0]
    assert revised["entries"][1]["revision"] == 2 and revised["entries"][1]["supersedes_revision"] == 1
    assert training.record_review_label(queue, revised, changed | {"revise": True, "expected_revision": 1}) == revised


def test_incomplete_single_human_summary_exposes_only_progress_and_own_labels():
    sources = [synthetic_source(0), synthetic_source(1)]
    queue = training.build_review_queue(sources, config(sources))
    blank = training.summarize_review(queue, empty_labels(queue))
    assert blank["status"] == "ready" and blank["progress"] == dict(total=2, labeled=0, unreviewed=2)
    assert blank["diagnostic"] is None and blank["completed_pass"] is None and blank["snapshots"] == []
    saved = training.record_review_label(queue, empty_labels(queue), entry(queue))
    partial = training.summarize_review(queue, saved)
    assert partial["status"] == "labeling" and partial["progress"] == dict(total=2, labeled=1, unreviewed=1)
    assert partial["diagnostic"] is None and partial["pass_hash"] is None
    assert partial["own_labels"] == {queue["order"][0]: saved["entries"][0]}


def test_completion_and_explicit_revision_return_separate_immutable_development_snapshots():
    sources = [synthetic_source(predicted=True)]
    queue = training.build_review_queue(sources, config(sources))
    saved = training.record_review_label(queue, empty_labels(queue), entry(queue))
    first = training.summarize_review(queue, saved)
    assert first["status"] == "complete" and first["completed_pass"] == saved and first["pass_hash"] == digest(saved)
    assert first["diagnostic"]["mode"] == "single_investor_diagnostic"
    assert first["diagnostic"]["reference_detector_input_sessions"] == 180
    assert first["snapshots"][0]["supersedes_pass_hash"] is None
    revised = training.record_review_label(queue, saved, entry(queue, decision="uncertain", revision=1, revise=True))
    second = training.summarize_review(queue, revised)
    assert len(second["snapshots"]) == 2 and second["snapshots"][0] == first["snapshots"][0]
    assert second["snapshots"][1]["supersedes_pass_hash"] == first["pass_hash"]
    assert second["pass_hash"] != first["pass_hash"] and training.summarize_review(queue, saved) == first


@pytest.mark.parametrize("change", ["study", "token", "owner", "role", "revision", "supersedes", "input_stamp", "extra"])
def test_acknowledged_history_is_validated_even_before_completion(change):
    sources = [synthetic_source(0), synthetic_source(1)]
    queue = training.build_review_queue(sources, config(sources))
    saved = training.record_review_label(queue, empty_labels(queue), entry(queue))
    if change == "study":
        saved["study_id"] = "other"
    else:
        field, value = {"token": ("view_token", "old"), "owner": ("reviewer_id", "other"),
                        "role": ("reviewer_role", "agent"), "revision": ("revision", True),
                        "supersedes": ("supersedes_revision", False),
                        "input_stamp": ("reference_detector_input_sessions", 180.0), "extra": ("extra", "injected")}[change]
        saved["entries"][0][field] = value
    with pytest.raises(ValueError):
        training.summarize_review(queue, saved)
    with pytest.raises(ValueError):
        training.record_review_label(queue, saved, entry(queue, case_id=queue["order"][1]))


@pytest.mark.parametrize("change", ["prediction", "context", "card", "manifest", "protocol", "order", "frame", "identity"])
def test_rehashed_queue_changes_cannot_bypass_reconstruction_before_labeling(change):
    sources = [synthetic_source(predicted=True)]
    queue = training.build_review_queue(sources, config(sources))
    key = queue["order"][0]
    case = queue["sealed"]["cases"][key]
    if change == "prediction":
        case["predictions"] = []
    elif change == "context":
        case["raw_context"][0]["close"] += 0.1
    elif change == "card":
        queue["cards"][key]["bars"][0]["close"] += 1
    elif change == "manifest":
        queue["sealed"]["detector_manifest"]["source_file_sha256"] = "0" * 64
    elif change == "protocol":
        queue["sealed"]["reference"]["protocol"]["match_tolerance_sessions"] = 4
    elif change == "order":
        queue["order"] = {key: None}
    elif change == "frame":
        queue["sealed"]["sampling_frames"]["random"]["size"] = True
    else:
        case["canonical_id"] = "other"
    queue["sealed"]["reference"]["prediction_hash"] = digest({name: row["predictions"] for name, row in queue["sealed"]["cases"].items()})
    queue["sealed"]["reference"]["commitment_hash"] = digest({name: value for name, value in queue["sealed"]["reference"].items() if name != "commitment_hash"})
    queue["queue_hash"] = digest({name: value for name, value in queue.items() if name != "queue_hash"})
    with pytest.raises(ValueError):
        training.summarize_review(queue, empty_labels(queue))


def test_request_creates_one_committed_round_and_retries_or_new_clicks_resume_it():
    catalog, history, request = round_fixture()
    before = deepcopy((catalog, history, request))
    created = training.request_training_round(catalog, history, request)
    assert created["status"] == "created" and created["round"]["status"] == "ready"
    assert len(created["history"]["rounds"]) == 1 and len(created["history"]["exposure"]["targets"]) == 2
    assert created["round"]["queue"]["sealed"]["config"]["exposure"] == history["exposure"]
    assert training.request_training_round(catalog, created["history"], request) == created
    resumed = training.request_training_round(catalog, created["history"], request | {"request_id": "synthetic-click-2"})
    assert resumed["status"] == "resumed" and resumed["round_id"] == created["round_id"]
    assert resumed["history"]["rounds"] == created["history"]["rounds"]
    assert resumed["history"]["exposure"] == created["history"]["exposure"]
    assert (catalog, history, request) == before


def test_reusing_request_id_with_changed_payload_conflicts_before_transition():
    catalog, history, request = round_fixture()
    created = training.request_training_round(catalog, history, request)
    before = deepcopy(created["history"])
    changed = request | {"config": request["config"] | {"random_seed": 17}}
    with pytest.raises(ValueError, match="request id"):
        training.request_training_round(catalog, created["history"], changed)
    assert created["history"] == before


@pytest.mark.parametrize("missing", ["source", "catalog_exposure", "history_exposure", "classification"])
def test_missing_data_returns_stable_non_round_outcome(missing):
    catalog, history, request = round_fixture(1)
    if missing == "source":
        catalog["sources"] = []
    elif missing == "catalog_exposure":
        catalog["exposure"]["complete"] = False
    elif missing == "history_exposure":
        history["exposure"] = None
    else:
        del catalog["sources"][0]["classification"]
    result = training.request_training_round(catalog, history, request)
    assert result["status"] == "needs_data" and result["round"] is None and result["round_id"] is None
    assert result["history"]["rounds"] == [] and result["history"]["exposure"] == history["exposure"]
    assert result["exclusions"]
    assert training.request_training_round(catalog, result["history"], request) == result


def test_allocation_requires_catalog_exposure_to_equal_authoritative_history():
    catalog, history, request = round_fixture()
    catalog["exposure"]["views"].append(dict(canonical_id="synthetic-issuer-0", start="2021-01-01", end="2022-01-01",
                                              provenance="synthetic catalog-only receipt"))
    with pytest.raises(ValueError, match="catalog exposure"):
        training.request_training_round(catalog, history, request)


def test_create_resume_label_complete_new_request_retains_prior_round_and_snapshots():
    catalog, history, request = round_fixture(8)
    created = training.request_training_round(catalog, history, request)
    first_queue, first_id = created["round"]["queue"], created["round_id"]
    history = acknowledge_label(created["history"], first_id, entry(first_queue))
    resumed = training.request_training_round(catalog, history, request | {"request_id": "synthetic-labeling-click"})
    assert resumed["status"] == "resumed" and resumed["round"]["status"] == "labeling"
    for key in first_queue["order"][1:]:
        history = acknowledge_label(history, first_id, entry(first_queue, case_id=key))
    original = deepcopy(history["rounds"][0])
    assert original["status"] == "complete" and len(original["snapshots"]) == 1
    next_catalog = catalog | {"exposure": deepcopy(history["exposure"])}
    next_round = training.request_training_round(next_catalog, history, request | {"request_id": "synthetic-next-click"})
    assert next_round["status"] == "created" and next_round["round_id"] != first_id
    assert len(next_round["history"]["rounds"]) == 2 and next_round["history"]["rounds"][0] == original
    assert len(next_round["round"]["queue"]["order"]) == 2
    old_retry = training.request_training_round(next_catalog, next_round["history"], request)
    assert old_retry["round"] == original and old_retry["history"] == next_round["history"]


@pytest.mark.parametrize("change", ["exposure", "status", "second_active", "catalog_hash", "catalog_source",
                                    "queue", "snapshots", "request_hash", "round_id"])
def test_durable_history_reconstructs_allocation_labels_and_snapshots_before_resume(change):
    catalog, history, request = round_fixture(1)
    created = training.request_training_round(catalog, history, request)
    saved = created["history"]
    row = saved["rounds"][0]
    if change == "exposure":
        saved["exposure"]["targets"] = []
    elif change == "status":
        row["status"] = "complete"
    elif change == "second_active":
        saved["rounds"].append(deepcopy(row))
    elif change == "catalog_hash":
        row["allocation"]["catalog_hash"] = "0" * 64
    elif change == "catalog_source":
        row["allocation"]["catalog"]["sources"][0]["bars"][-1]["close"] += 0.1
        row["allocation"]["catalog_hash"] = digest(row["allocation"]["catalog"])
        row["allocation"]["sources_hash"] = digest(row["allocation"]["catalog"]["sources"])
    elif change == "queue":
        row["queue"]["sealed"]["cases"][row["queue"]["order"][0]]["target_start"] = "2010-01-01"
        row["queue"]["queue_hash"] = digest({name: value for name, value in row["queue"].items() if name != "queue_hash"})
        row["labels"]["queue_hash"] = row["queue"]["queue_hash"]
    elif change == "snapshots":
        row["snapshots"] = [{"pass_hash": "0" * 64}]
    elif change == "request_hash":
        saved["requests"][request["request_id"]]["payload_hash"] = "0" * 64
    else:
        row["round_id"] = "other"
        saved["requests"][request["request_id"]]["round_id"] = "other"
    with pytest.raises(ValueError):
        training.request_training_round(catalog, saved, request | {"request_id": "synthetic-resume"})


@pytest.mark.parametrize("fetched,accepted", [("2025-04-11T19:59:00+00:00", False),
                                              ("2025-04-11T20:00:00+00:00", True),
                                              ("2025-04-11T01:00:00+00:00", False),
                                              ("2025-04-12T01:00:00+00:00", True)])
def test_explicit_cutoff_must_be_complete_in_recorded_exchange_timezone(fetched, accepted):
    source = synthetic_source()
    source["fetched_at"] = fetched
    queue = training.build_review_queue([source], config([source]))
    assert bool(queue["order"]) is accepted


@pytest.mark.parametrize("series", [None, {}, (), [], [None], [7], ["source"], [{"source_id": 4}]])
def test_malformed_series_containers_or_rows_return_admission_exclusions(series):
    source = synthetic_source()
    queue = training.build_review_queue(series, config([source]))
    assert queue["order"] == [] and queue["sealed"]["exclusions"]
    assert training.summarize_review(queue, empty_labels(queue))["progress"]["total"] == 0


def test_case_commits_retained_source_lineage_classification_and_full_input_fingerprints():
    source = synthetic_source()
    queue = training.build_review_queue([source], config([source]))
    receipt = queue["sealed"]["source_receipts"][source["source_id"]]
    assert receipt["source_sha256"] == source["source_sha256"]
    assert receipt["input_bars_hash"] == digest(source["bars"])
    assert receipt["source_payload_hash"] == digest(source)
    assert receipt["classification_hash"] == digest(source["classification"])
    assert receipt["alias_evidence_hash"] == digest(source["alias_evidence"])
    assert queue["sealed"]["cases"][queue["order"][0]]["source_receipt"] == receipt


def test_conflicting_duplicate_source_ids_are_excluded_together():
    first, second = synthetic_source(0), synthetic_source(1)
    second["source_id"] = first["source_id"]
    second["aliases"] = [first["source_id"], second["symbol"]]
    queue = training.build_review_queue([first, second], config([first, second]))
    assert queue["order"] == []
    assert any(row["reason"] == "duplicate source identifier" for row in queue["sealed"]["exclusions"])


def test_callers_cannot_submit_generated_label_stamps_or_unknown_fields():
    sources = [synthetic_source()]
    queue = training.build_review_queue(sources, config(sources))
    with pytest.raises(ValueError):
        training.record_review_label(queue, empty_labels(queue), entry(queue) | {"reference_hash": "0" * 64})


@pytest.mark.parametrize("missing", ["sources", "exposure"])
def test_incomplete_catalog_fields_return_needs_data(missing):
    catalog, history, request = round_fixture(1)
    del catalog[missing]
    assert training.request_training_round(catalog, history, request)["status"] == "needs_data"


@pytest.mark.parametrize("catalog", [None, [], {"schema_version": "legacy", "sources": [], "exposure": None}])
def test_malformed_catalog_contract_is_rejected(catalog):
    _, history, request = round_fixture(1)
    with pytest.raises(ValueError):
        training.request_training_round(catalog, history, request)


@pytest.mark.parametrize("field,value", [("fetched_at", None), ("exchange_timezone", None), ("cutoffs", ["0001-01-01"])])
def test_malformed_source_time_metadata_is_an_admission_exclusion(field, value):
    source = synthetic_source()
    source[field] = value
    queue = training.build_review_queue([source], config([source]))
    assert queue["order"] == [] and queue["sealed"]["exclusions"]


def test_recorded_request_exclusions_cannot_diverge_from_its_committed_round():
    catalog, history, request = round_fixture(1)
    created = training.request_training_round(catalog, history, request)
    created["history"]["requests"][request["request_id"]]["exclusions"] = [{"reason": "injected"}]
    with pytest.raises(ValueError):
        training.request_training_round(catalog, created["history"], request)


def test_nonterminal_alias_map_cannot_bypass_a_previously_exposed_canonical_target():
    source = synthetic_source()
    settings = config([source])
    true_identity = source["canonical_id"]
    source["canonical_id"] = "canonical-alias"
    settings["exposure"]["aliases"] = {alias: "canonical-alias" for alias in source["aliases"]}
    settings["exposure"]["aliases"]["canonical-alias"] = true_identity
    settings["exposure"]["targets"].append(dict(canonical_id=true_identity, start="2025-04-11", end="2025-04-11",
                                               case_fingerprint="e" * 64, provenance="synthetic prior target receipt"))
    queue = training.build_review_queue([source], settings)
    assert queue["order"] == [] and queue["sealed"]["exclusions"]
