"""Synthetic recognition evaluation through the two confirmed public boundaries."""

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from gary.review import build_review_queue, record_review_label
from test_review import config, empty_labels, entry, source, source_with_inverse


def study():
    queue = build_review_queue([source(), source("AMGN")], config())
    labels = complete_passes(queue)
    return queue, labels


def complete_passes(queue, decision="none", events=None):
    labels = empty_labels(queue)
    for reviewer in queue["sealed"]["config"]["reviewers"]:
        for key in queue["order"]:
            submission = entry(queue, reviewer, decision=decision, events=events or [])
            submission["case_id"] = key
            labels = record_review_label(queue, labels, submission)
    return labels


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def test_complete_calibration_freezes_deterministic_holdout_without_mutating_inputs():
    from gary.evaluation import freeze_evaluation

    queue, labels = study()
    before = deepcopy((queue, labels))
    release = freeze_evaluation(queue, labels)
    assert freeze_evaluation(queue, labels) == release
    assert (queue, labels) == before
    assert release["parent_queue_hash"] == queue["queue_hash"]
    assert release["calibration_labels"] == labels
    assert release["calibration_labels_hash"] == digest(labels)
    assert release["baseline_version"] == release["candidate_version"] == "causal-geometry-v1"
    assert set(release["evaluator_manifest"]) == {"review_source_file_sha256", "evaluation_source_file_sha256", "protocol_hash"}
    held = release["holdout_queue"]
    assert len(held["cards"]) == 4
    assert set(held["cards"]).isdisjoint(queue["cards"])
    assert {case["split"] for case in held["sealed"]["cases"].values()} == {"time_holdout", "symbol_holdout"}
    assert held["sealed"]["config"]["profile"] == "released-holdout-v1"
    assert held["sealed"]["config"]["holdout_locked"] is False
    assert all(len(card["bars"]) == 180 for card in held["cards"].values())


@pytest.mark.parametrize("change", ["incomplete", "wrong_version", "exploration", "no_calibration"])
def test_freeze_refuses_incomplete_or_unsupported_calibration(change):
    from gary.evaluation import freeze_evaluation
    from test_review import five_year_config, five_year_sources

    queue, labels = study()
    version = "causal-geometry-v1"
    if change == "incomplete":
        labels["entries"].pop()
    elif change == "wrong_version":
        version = "unvalidated-v2"
    elif change == "exploration":
        queue = build_review_queue(five_year_sources(), five_year_config())
        labels = complete_passes(queue)
    else:
        queue = build_review_queue([source("AMGN")], config())
        labels = empty_labels(queue)
    before = deepcopy((queue, labels))
    with pytest.raises(ValueError):
        freeze_evaluation(queue, labels, version)
    assert (queue, labels) == before


def test_released_holdout_accepts_own_labels_but_rejects_original_calibration_ids():
    from gary.evaluation import freeze_evaluation

    queue, calibration = study()
    held = freeze_evaluation(queue, calibration)["holdout_queue"]
    submitted = entry(held, decision="none", events=[])
    labels = record_review_label(held, empty_labels(held), submitted)
    assert labels["entries"][0]["revision"] == 1
    assert record_review_label(held, labels, submitted) == labels
    submitted["case_id"] = queue["order"][0]
    with pytest.raises(ValueError, match="locked|unknown"):
        record_review_label(held, labels, submitted)


def test_partial_holdout_reports_progress_with_null_recognition_until_two_full_passes():
    from gary.evaluation import evaluate_detector, freeze_evaluation

    queue, calibration = study()
    release = freeze_evaluation(queue, calibration)
    held, labels = release["holdout_queue"], empty_labels(release["holdout_queue"])
    for key in held["order"]:
        submitted = entry(held, decision="none", events=[])
        submitted["case_id"] = key
        labels = record_review_label(held, labels, submitted)
    before = deepcopy((queue, labels, release))
    report = evaluate_detector(queue, labels, release, "holdout")
    assert report["status"] == "pending_labels" and report["recognition_agreement"] is None
    assert report["coverage"]["by_reviewer"]["observer-a"]["unreviewed"] == 0
    assert report["coverage"]["by_reviewer"]["observer-b"]["unreviewed"] == 4
    assert report["label_snapshot_hash"] == digest(labels)
    assert report["phase"] == "holdout" and report["trading_approval"] is False
    assert report["evaluated_version"] == "causal-geometry-v1"
    assert (queue, labels, release) == before


@pytest.mark.parametrize("change", ["detector_manifest", "prediction", "context", "visible_dates", "source_identity", "case_id"])
def test_freeze_rejects_forged_original_evidence_even_with_recomputed_queue_hash(change):
    from gary.evaluation import freeze_evaluation

    queue, labels = study()
    key = next(key for key, case in queue["sealed"]["cases"].items() if case["split"] == "time_holdout")
    case = queue["sealed"]["cases"][key]
    if change == "detector_manifest":
        queue["sealed"]["config"]["detector_source_file_sha256"] = "0" * 64
        queue["sealed"]["detector"]["source_file_sha256"] = "0" * 64
    elif change == "prediction":
        case["predictions"] = [{"kind": "inverse_head_shoulders", "completion_date": case["as_of"], "available_at": case["as_of"]}]
    elif change == "context":
        case["raw_window"][0]["close"] += 0.05
        case["window_hash"] = digest(case["raw_window"])
    elif change == "visible_dates":
        case["visible_dates"][0] = "1900-01-01"
    elif change == "source_identity":
        case["source_id"] = "undeclared-source"
    else:
        queue["sealed"]["cases"]["f" * 16] = queue["sealed"]["cases"].pop(key)
    queue["queue_hash"] = digest({key: value for key, value in queue.items() if key != "queue_hash"})
    labels["queue_hash"] = queue["queue_hash"]
    before = deepcopy((queue, labels))
    with pytest.raises(ValueError, match="integrity|manifest|context|source"):
        freeze_evaluation(queue, labels)
    assert (queue, labels) == before


@pytest.mark.parametrize("change", ["parent", "release", "calibration_case", "wrong_split"])
def test_released_profile_rejects_forged_provenance_or_calibration_cards(change):
    from gary.evaluation import freeze_evaluation
    from gary.review import summarize_review

    queue, labels = study()
    held = freeze_evaluation(queue, labels)["holdout_queue"]
    if change == "parent":
        held["sealed"]["config"]["parent_queue_hash"] = "b" * 64
    elif change == "release":
        held["sealed"]["config"]["release_id"] = "b" * 64
    elif change == "calibration_case":
        key = queue["order"][0]
        held["sealed"]["cases"][key] = deepcopy(queue["sealed"]["cases"][key])
        held["cards"][key] = deepcopy(queue["cards"][key])
        held["order"].append(key)
    else:
        key = next(key for key, case in held["sealed"]["cases"].items() if case["split"] == "time_holdout")
        held["sealed"]["cases"][key]["split"] = "symbol_holdout"
    held["queue_hash"] = digest({key: value for key, value in held.items() if key != "queue_hash"})
    with pytest.raises(ValueError, match="integrity"):
        summarize_review(held, empty_labels(held))


def rehash_release(release):
    release["release_id"] = digest({key: value for key, value in release.items() if key not in {"release_id", "holdout_queue", "release_hash"}})
    held = release["holdout_queue"]
    held["study_id"] = "gary-holdout-" + release["release_id"]
    held["sealed"]["config"].update(study_id=held["study_id"], release_id=release["release_id"])
    held["sealed"]["release_id"] = release["release_id"]
    held["queue_hash"] = digest({key: value for key, value in held.items() if key != "queue_hash"})
    release["release_hash"] = digest({key: value for key, value in release.items() if key != "release_hash"})


@pytest.mark.parametrize("change", ["predictions", "context_commitment", "derived_context", "calibration_history", "evaluator", "matching"])
def test_evaluation_rejects_recomputed_release_commitments_that_disagree_with_parent_or_trusted_sources(change):
    from gary.evaluation import evaluate_detector, freeze_evaluation

    queue, calibration = study()
    release = freeze_evaluation(queue, calibration)
    held = release["holdout_queue"]
    key = held["order"][0]
    if change == "predictions":
        release["holdout_predictions"][key] = [{"kind": "cup_handle"}]
    elif change == "context_commitment":
        release["holdout_contexts"][key]["window_hash"] = "b" * 64
    elif change == "derived_context":
        # Build internally consistent, proportionally identical cards from altered
        # raw prices. All local hashes/projections are valid, but the parent differs.
        case = held["sealed"]["cases"].pop(key)
        for bar in case["raw_window"]:
            for field in ("open", "high", "low", "close"):
                bar[field] *= 2
        case["window_hash"] = digest(case["raw_window"])
        new_key = digest([held["sealed"]["config"]["id_salt"], case["source_id"], case["window_hash"]])[:16]
        held["sealed"]["cases"][new_key] = case
        held["cards"][new_key] = held["cards"].pop(key)
        held["cards"][new_key]["case_id"] = new_key
        held["order"] = [new_key if value == key else value for value in held["order"]]
        release["holdout_predictions"][new_key] = release["holdout_predictions"].pop(key)
        release["holdout_contexts"][new_key] = release["holdout_contexts"].pop(key)
        release["holdout_contexts"][new_key]["window_hash"] = case["window_hash"]
    elif change == "calibration_history":
        release["calibration_labels"]["entries"][0]["rationale"] = "Changed after freeze"
    elif change == "evaluator":
        release["evaluator_manifest"]["review_source_file_sha256"] = "b" * 64
    else:
        release["matching_policy"]["match_tolerance_sessions"] = 100
    rehash_release(release)
    labels = empty_labels(held)
    with pytest.raises(ValueError, match="release|snapshot|integrity|manifest"):
        evaluate_detector(queue, labels, release, "holdout")


def test_complete_holdout_reports_separate_time_symbol_and_random_enriched_event_counts():
    from gary.evaluation import evaluate_detector, freeze_evaluation

    quiet = build_review_queue([source(), source("AMGN")], config())
    end = next(case["source_end_index"] for case in quiet["sealed"]["cases"].values() if case["split"] == "time_holdout")
    item = source()
    drawing = source_with_inverse()["bars"][330:401]
    for offset, bar in enumerate(drawing):
        item["bars"][end - 70 + offset].update({key: value for key, value in bar.items() if key != "date"})
    queue = build_review_queue([item, source("AMGN")], config())
    release = freeze_evaluation(queue, complete_passes(queue))
    held, labels = release["holdout_queue"], empty_labels(release["holdout_queue"])
    for reviewer in held["sealed"]["config"]["reviewers"]:
        for key in held["order"]:
            case = held["sealed"]["cases"][key]
            events = [{"kind": "inverse_head_shoulders", "completion_offset": 0}] if case["source_end_index"] == end and case["split"] == "time_holdout" else []
            submitted = entry(held, reviewer, decision="completed" if events else "none", events=events)
            submitted["case_id"] = key
            labels = record_review_label(held, labels, submitted)
    report = evaluate_detector(queue, labels, release, "holdout")
    assert report["status"] == "evaluated"
    metrics = report["recognition_agreement"]
    assert set(metrics) == {"time_holdout", "symbol_holdout"}
    for stratum in ("random", "enriched"):
        row = metrics["time_holdout"][stratum]["inverse_head_shoulders"]
        assert (row["predicted_events"], row["labeled_events"], row["matched_events"]) == (1, 1, 1)
        assert row["signed_completion_errors_sessions"] == [0]
    assert metrics["symbol_holdout"]["random"]["inverse_head_shoulders"]["certain_cases"] == 3
    assert metrics["symbol_holdout"]["random"]["cup_handle"]["prediction_match_fraction"] is None
    assert report["stratum_overlap_cases"] == 1


def test_released_summary_identifies_holdout_and_hides_partial_recognition():
    from gary.evaluation import freeze_evaluation
    from gary.review import summarize_review

    queue, calibration = study()
    held = freeze_evaluation(queue, calibration)["holdout_queue"]
    report = summarize_review(held, empty_labels(held))
    assert report["phase"] == "holdout" and report["holdout_locked"] is False
    assert report["recognition_agreement"] is None and report["status"] == "pending_labels"


@pytest.mark.parametrize("change", ["missing_calibration_card", "duplicate_order", "time_boundary", "reserved_split", "exploration_overlap"])
def test_freeze_requires_original_complete_case_partition_and_disjoint_exploration_sources(change):
    from gary.evaluation import freeze_evaluation

    queue, labels = study()
    if change == "missing_calibration_card":
        key = queue["order"].pop()
        del queue["cards"][key]
        labels["entries"] = [row for row in labels["entries"] if row["case_id"] != key]
    elif change == "duplicate_order":
        queue["order"].append(queue["order"][0])
    elif change == "time_boundary":
        queue["sealed"]["cases"][queue["order"][0]]["split"] = "time_holdout"
    elif change == "reserved_split":
        case = next(case for case in queue["sealed"]["cases"].values() if case["split"] == "symbol_holdout")
        case["split"] = "time_holdout"
    else:
        queue = build_review_queue([source("JPM"), source("AMGN")], config())
        labels = complete_passes(queue)
    queue["queue_hash"] = digest({key: value for key, value in queue.items() if key != "queue_hash"})
    labels["queue_hash"] = queue["queue_hash"]
    with pytest.raises(ValueError, match="integrity|partition|source"):
        freeze_evaluation(queue, labels)
