"""Synthetic five-year assistance at the three approved review seams."""

from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json

import pytest

from gary import context_review
from gary.evaluation import freeze_evaluation
from gary.review import build_review_queue as original_queue
from test_evaluation import complete_passes
from test_review import config, empty_labels, entry, source


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def study(originals=None):
    originals = originals or [source(), source("AMGN")]
    calibration = original_queue(originals, config())
    release = freeze_evaluation(calibration, complete_passes(calibration))
    items = deepcopy(originals)
    for item in items:
        day, prefix = date(2016, 1, 1), []
        while day < date.fromisoformat(item["bars"][0]["date"]):
            if day.weekday() < 5:
                prefix.append(dict(date=day.isoformat(), open=50, high=51, low=49,
                                   close=50, volume=2000))
            day += timedelta(days=1)
        item["bars"] = prefix + item["bars"]
        item["source_sha256"] = "b" * 64
    settings = dict(profile="five-year-assisted-v1", parent_queue=release["holdout_queue"],
                    parent_release_hash=release["release_hash"])
    return items, settings


def context_queue():
    return context_review.build_review_queue(*study())


def submission(queue, reviewer="observer-a", decision="none", events=None):
    return entry(queue, reviewer, decision=decision, events=events or []) | {"view_token": queue["queue_hash"]}


def test_assisted_queue_preserves_the_released_view_and_adds_historical_anonymous_context():
    items, settings = study()
    before = deepcopy((items, settings))
    parent = settings["parent_queue"]
    queue = context_review.build_review_queue(items, settings)
    restored = deepcopy(queue)
    context = restored["sealed"].pop("context_review")
    restored["queue_hash"] = parent["queue_hash"]
    assert restored == parent and (items, settings) == before
    assert context["parent_queue"] == parent
    assert context["parent_release_hash"] == settings["parent_release_hash"]
    assert queue["queue_hash"] != parent["queue_hash"]
    assert context_review.build_review_queue(items, settings) == queue
    for key, case in parent["sealed"]["cases"].items():
        full = context["cases"][key]
        card = full["overview"]
        assert len(full["raw_window"]) >= 1200
        assert full["raw_window"][-180:] == case["raw_window"]
        assert full["raw_window"][-1]["date"] == case["as_of"]
        assert full["raw_window"][0]["date"] > full["requested_start"]
        assert card["bars"][0]["close"] == 100
        assert card["bars"][-1]["offset"] == 0
        assert card["bars"][0]["offset"] == 1 - len(full["raw_window"])
        assert set(card) == {"case_id", "bars", "target_start_offset", "target_end_offset",
                             "price_basis", "volume_available", "split_offsets"}


@pytest.mark.parametrize("change", ["profile", "release_hash", "extra_config", "unreleased", "parent_tamper"])
def test_context_build_requires_a_valid_released_parent_and_explicit_protocol(change):
    items, settings = study()
    if change == "profile":
        settings["profile"] = "five-year-v1"
    elif change == "release_hash":
        settings["parent_release_hash"] = "invalid"
    elif change == "extra_config":
        settings["context_years"] = 4
    elif change == "unreleased":
        settings["parent_queue"] = original_queue([source()], config())
    else:
        settings["parent_queue"]["cards"][settings["parent_queue"]["order"][0]]["bars"][0]["close"] += 1
    with pytest.raises(ValueError):
        context_review.build_review_queue(items, settings)


@pytest.mark.parametrize("change", ["empty", "duplicate_source", "source_id", "symbol", "extra_source",
                                    "source_hash", "fetch_time", "timezone", "split_dates", "missing_splits",
                                    "unordered", "duplicate_date", "noncanonical", "boolean", "nan",
                                    "negative_volume", "invalid_ohlc", "future_invalid"])
def test_entire_retained_sources_require_matching_identities_and_valid_provenance_and_bars(change):
    items, settings = study()
    item = items[0]
    if change == "empty":
        items = []
    elif change == "duplicate_source":
        items.append(deepcopy(item))
    elif change == "source_id":
        item["source_id"] = "other-source"
    elif change == "symbol":
        item["symbol"] = "OTHER"
    elif change == "extra_source":
        items.append(source("OTHER"))
    elif change == "source_hash":
        item["source_sha256"] = "bad"
    elif change == "fetch_time":
        item["fetched_at"] = "2026-10-10T20:00:00"
    elif change == "timezone":
        item["exchange_timezone"] = "not/a-zone"
    elif change == "split_dates":
        item["split_dates"] = ["20180101"]
    elif change == "missing_splits":
        del item["split_dates"]
    elif change == "unordered":
        item["bars"][0], item["bars"][1] = item["bars"][1], item["bars"][0]
    elif change == "duplicate_date":
        item["bars"][1]["date"] = item["bars"][0]["date"]
    elif change == "noncanonical":
        item["bars"][0]["date"] = "20160101"
    elif change == "boolean":
        item["bars"][0]["volume"] = True
    elif change == "nan":
        item["bars"][0]["close"] = float("nan")
    elif change == "negative_volume":
        item["bars"][0]["volume"] = -1
    elif change == "invalid_ohlc":
        item["bars"][0]["high"] = 48
    else:
        item["bars"][-1]["volume"] = -1
    with pytest.raises(ValueError, match="source"):
        context_review.build_review_queue(items, settings)


@pytest.mark.parametrize("change", ["short", "late_start", "no_prior_history", "missing_cutoff", "tail_mismatch", "tail_numeric_type"])
def test_context_build_refuses_incomplete_or_unreconciled_historical_windows(change):
    items, settings = study()
    case = min(settings["parent_queue"]["sealed"]["cases"].values(), key=lambda case: case["as_of"])
    item = next(item for item in items if item["source_id"] == case["source_id"])
    cutoff = date.fromisoformat(case["as_of"])
    requested = cutoff.replace(year=cutoff.year - 5)
    if change == "short":
        index = next(index for index, bar in enumerate(item["bars"]) if bar["date"] == case["as_of"])
        item["bars"] = item["bars"][index - 1198:]
    elif change == "late_start":
        boundary = (requested + timedelta(days=8)).isoformat()
        item["bars"] = [bar for bar in item["bars"] if bar["date"] <= requested.isoformat() or bar["date"] >= boundary]
    elif change == "no_prior_history":
        item["bars"] = [bar for bar in item["bars"] if bar["date"] >= requested.isoformat()]
    elif change == "missing_cutoff":
        item["bars"] = [bar for bar in item["bars"] if bar["date"] != case["as_of"]]
    elif change == "tail_mismatch":
        bar = next(bar for bar in item["bars"] if bar["date"] == case["as_of"])
        bar["open"] += 0.1
    else:
        bar = next(bar for bar in item["bars"] if bar["date"] == case["as_of"])
        bar["volume"] = float(bar["volume"])
    with pytest.raises(ValueError, match="context|reconcil"):
        context_review.build_review_queue(items, settings)


def test_bound_context_observation_has_server_generated_provenance_and_preserves_retry_revision_history():
    queue = context_queue()
    before = empty_labels(queue)
    submitted = submission(queue) | {"view_protocol": "caller-forgery", "overview_hash": "caller-forgery"}
    labels = context_review.record_review_label(queue, before, submitted)
    row = labels["entries"][0]
    overview = queue["sealed"]["context_review"]["cases"][submitted["case_id"]]["overview"]
    assert row["view_protocol"] == "five-year-assisted-v1"
    assert row["overview_hash"] == digest(overview)
    assert before["entries"] == [] and row["revision"] == 1
    assert context_review.record_review_label(queue, labels, submitted) == labels
    changed = submission(queue, decision="uncertain")
    with pytest.raises(ValueError, match="revision"):
        context_review.record_review_label(queue, labels, changed)
    changed.update(revise=True, expected_revision=1)
    revised = context_review.record_review_label(queue, labels, changed)
    assert revised["entries"][:-1] == labels["entries"]
    assert revised["entries"][-1]["revision"] == 2
    assert revised["entries"][-1]["supersedes_revision"] == 1
    assert revised["entries"][-1]["overview_hash"] == row["overview_hash"]


@pytest.mark.parametrize("token", [None, "old-view", "parent-view"])
def test_missing_or_stale_view_binding_is_rejected_before_a_label_is_written(token):
    queue = context_queue()
    submitted = submission(queue)
    if token is None:
        del submitted["view_token"]
    else:
        submitted["view_token"] = (queue["sealed"]["context_review"]["parent_queue"]["queue_hash"]
                                   if token == "parent-view" else token)
    labels = empty_labels(queue)
    before = deepcopy(labels)
    with pytest.raises(ValueError, match="view|token"):
        context_review.record_review_label(queue, labels, submitted)
    assert labels == before


def test_open_left_anniversary_february_clamp_and_first_session_split_marker():
    item = source("AMGN")
    day, bars = date(2023, 1, 2), []
    while day <= date(2024, 3, 4):
        if day.weekday() < 5:
            bars.append(dict(date=day.isoformat(), open=100, high=101, low=99, close=100, volume=1000))
        day += timedelta(days=1)
    item["bars"] = bars[-182:]
    items, settings = study([source(), item])
    full_source = next(item for item in items if item["symbol"] == "AMGN")
    full_source["split_dates"] = ["2019-03-02"]
    queue = context_review.build_review_queue(items, settings)
    cases = {case["as_of"]: queue["sealed"]["context_review"]["cases"][key]
             for key, case in queue["sealed"]["cases"].items() if case["symbol"] == "AMGN"}
    assert cases["2024-02-29"]["requested_start"] == "2019-02-28"
    assert cases["2024-02-29"]["raw_window"][0]["date"] == "2019-03-01"
    march = cases["2024-03-01"]
    assert march["requested_start"] == "2019-03-01"
    assert march["raw_window"][0]["date"] == "2019-03-04"
    assert march["overview"]["split_offsets"] == [1 - len(march["raw_window"])]


def test_context_summary_identifies_changed_evidence_and_withholds_recognition_until_both_passes_finish():
    queue = context_queue()
    labels = empty_labels(queue)
    report = context_review.summarize_review(queue, labels)
    assert report["phase"] == "holdout_context"
    assert report["view_protocol"] == "five-year-assisted-v1"
    assert report["original_holdout_comparable"] is False
    assert report["reference_detector_input_sessions"] == 180
    assert report["recognition_agreement"] is None and report["consensus"] is None
    assert report["status"] == "pending_labels"
    for key in queue["order"]:
        submitted = submission(queue) | {"case_id": key}
        labels = context_review.record_review_label(queue, labels, submitted)
    partial = context_review.summarize_review(queue, labels)
    assert partial["recognition_agreement"] is None and partial["consensus"] is None
    assert partial["coverage"]["by_reviewer"]["observer-a"]["unreviewed"] == 0
    assert partial["coverage"]["by_reviewer"]["observer-b"]["unreviewed"] == 4
    for key in queue["order"]:
        labels = context_review.record_review_label(queue, labels, submission(queue, "observer-b") | {"case_id": key})
    full = context_review.summarize_review(queue, labels)
    assert full["consensus"]["certain_cases"] == 4
    assert full["recognition_agreement"]["random"]["cup_handle"]["certain_cases"] == 4
    assert any("overlap" in limitation.lower() for limitation in full["limitations"])
    assert any("retrospective" in limitation.lower() for limitation in full["limitations"])
    assert any("provider" in limitation.lower() for limitation in full["limitations"])


@pytest.mark.parametrize("change", ["outer_hash", "overview", "overview_type", "raw_hash", "raw_bar", "requested_start",
                                    "split_offsets", "parent_snapshot", "original_detail", "missing_context",
                                    "protocol", "release_hash", "source_identity", "source_hash", "original_numeric_type"])
@pytest.mark.parametrize("seam", ["label", "summary"])
def test_context_integrity_is_checked_before_observation_or_summary_even_after_an_outer_rehash(change, seam):
    queue = context_queue()
    key = queue["order"][0]
    context = queue["sealed"]["context_review"]
    case = context["cases"][key]
    if change == "outer_hash":
        queue["queue_hash"] = "a" * 64
    elif change == "overview":
        case["overview"]["bars"][0]["close"] = 101
    elif change == "overview_type":
        case["overview"]["bars"][-1]["volume"] = True
    elif change == "raw_hash":
        case["window_hash"] = "a" * 64
    elif change == "raw_bar":
        case["raw_window"][0]["volume"] = -1
        case["window_hash"] = digest(case["raw_window"])
    elif change == "requested_start":
        case["requested_start"] = "1900-01-01"
    elif change == "split_offsets":
        case["overview"]["split_offsets"] = [0]
    elif change == "parent_snapshot":
        context["parent_queue"]["cards"][key]["bars"][0]["close"] = 101
    elif change == "original_detail":
        queue["sealed"]["exclusions"].append({"invented": True})
    elif change == "missing_context":
        del context["cases"][key]
    elif change == "protocol":
        context["protocol"] = "old-view"
    elif change == "release_hash":
        context["parent_release_hash"] = "bad"
    elif change == "source_identity":
        context["sources"][0]["symbol"] = "OTHER"
    elif change == "original_numeric_type":
        queue["cards"][key]["bars"][0]["volume"] = True
    else:
        context["sources"][0]["input_bars_hash"] = "bad"
    if change != "outer_hash":
        queue["queue_hash"] = digest({key: value for key, value in queue.items() if key != "queue_hash"})
    labels = empty_labels(queue)
    with pytest.raises(ValueError, match="integrity|context|source|parent"):
        if seam == "label":
            context_review.record_review_label(queue, labels, submission(queue))
        else:
            context_review.summarize_review(queue, labels)
    assert labels["entries"] == []


@pytest.mark.parametrize("change", ["missing", "protocol", "overview_hash"])
@pytest.mark.parametrize("seam", ["label", "summary"])
def test_every_prior_revision_must_belong_to_this_context_view(change, seam):
    queue = context_queue()
    labels = context_review.record_review_label(queue, empty_labels(queue), submission(queue))
    revised = submission(queue, decision="uncertain") | {"revise": True, "expected_revision": 1}
    labels = context_review.record_review_label(queue, labels, revised)
    if change == "missing":
        del labels["entries"][0]["view_protocol"]
    elif change == "protocol":
        labels["entries"][0]["view_protocol"] = "original-180"
    else:
        labels["entries"][0]["overview_hash"] = "a" * 64
    before = deepcopy(labels)
    with pytest.raises(ValueError, match="view|provenance"):
        if seam == "label":
            context_review.record_review_label(queue, labels, submission(queue, "observer-b"))
        else:
            context_review.summarize_review(queue, labels)
    assert labels == before


@pytest.mark.parametrize("zero_volume", [False, True])
def test_overview_uses_its_own_median_volume_or_marks_it_unavailable(zero_volume):
    originals = [source(), source("AMGN")]
    if zero_volume:
        for item in originals:
            for bar in item["bars"]:
                bar["volume"] = 0
    items, settings = study(originals)
    if zero_volume:
        for item in items:
            for bar in item["bars"]:
                bar["volume"] = 0
    queue = context_review.build_review_queue(items, settings)
    key = min(queue["sealed"]["cases"], key=lambda key: queue["sealed"]["cases"][key]["as_of"])
    overview = queue["sealed"]["context_review"]["cases"][key]["overview"]
    if zero_volume:
        assert overview["volume_available"] is False
        assert all(bar["volume"] is None for bar in overview["bars"])
    else:
        assert overview["volume_available"] is True
        assert overview["bars"][0]["volume"] == 1.0
        assert overview["bars"][-1]["volume"] == 0.5
        assert queue["cards"][key]["bars"][-1]["volume"] == 1.0


def test_complete_context_summary_keeps_uncertain_invalid_and_disputed_cases_out_of_agreement():
    queue = context_queue()
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        for index, key in enumerate(queue["order"]):
            decision = ("none", "uncertain", "invalid", "none" if reviewer == "observer-a" else "completed")[index]
            events = [dict(kind="cup_handle", completion_offset=0)] if decision == "completed" else []
            submitted = submission(queue, reviewer, decision, events) | {"case_id": key}
            labels = context_review.record_review_label(queue, labels, submitted)
    report = context_review.summarize_review(queue, labels)
    assert report["consensus"]["certain_cases"] == 1
    assert report["consensus"]["uncertain_cases"] == 1
    assert report["consensus"]["invalid_cases"] == 1
    assert report["consensus"]["disagreement_cases"] == 1
    assert report["recognition_agreement"]["random"]["cup_handle"]["certain_cases"] == 1
    assert report["recognition_agreement"]["random"]["cup_handle"]["labeled_events"] == 0
