"""Synthetic personal diagnostics at the approved analysis seam."""

from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path

import pytest

from gary import context_review
from gary.context_review import _overview
from gary.evaluation import _trusted_detector, freeze_evaluation
from gary.patterns import detect_patterns
from gary.review import _card
from gary.training_analysis import analyze_training_pass
from test_evaluation import complete_passes
from test_review import config, empty_labels, source


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def rehash(queue):
    cases = queue["sealed"]["cases"]
    reference = queue["sealed"]["reference"]
    reference["prediction_hash"] = digest({key: case["predictions"] for key, case in cases.items()})
    reference["inputs_hash"] = digest({key: digest(case["raw_window"]) for key, case in cases.items()})
    reference["commitment_hash"] = digest({key: value for key, value in reference.items() if key != "commitment_hash"})
    queue["queue_hash"] = digest({key: value for key, value in queue.items() if key != "queue_hash"})


def training_queue(predicted=True, memberships=None, trailing=1):
    cutoff = date(2025, 4, 11) + timedelta(days=trailing - 1)
    day, full = cutoff.replace(year=2020) + timedelta(days=1), []
    while day <= cutoff:
        if day.weekday() < 5:
            full.append(dict(date=day.isoformat(), open=120, high=121, low=119, close=120, volume=1000))
        day += timedelta(days=1)
    if predicted:
        drawn = json.loads((Path(__file__).parent / "fixtures" / "pattern-inverse.json").read_text())["bars"]
        for index, bar in enumerate(drawn):
            full[-len(drawn) - trailing + index].update({key: value for key, value in bar.items() if key != "date"})
        for bar in full[-trailing:] if trailing else []:
            bar.update(open=112, high=113, low=111, close=112)
    window, key = full[-180:], "synthetic-case"
    dates = [bar["date"] for bar in window]
    case = dict(source_id="synthetic-source", symbol="SYNTHETIC", canonical_id="synthetic-issuer",
                raw_window=window, raw_context=full, window_hash=digest(window), context_hash=digest(full),
                visible_dates=dates, as_of=dates[-1], memberships=memberships or ["random"],
                predictions=[event for event in detect_patterns(window, dates[-1])
                             if dates[-20] <= event["completion_date"] <= dates[-1]
                             and dates[-20] <= event["available_at"] <= dates[-1]])
    queue = dict(schema_version="pattern-training-review-v1", study_id="synthetic-training", order=[key],
                 cards={key: _card(key, window) | {"overview": _overview(key, full, [])}},
                 sealed=dict(config=dict(profile="training-five-year-v1", reviewer_id="gary"),
                             detector_manifest=_trusted_detector(), cases={key: case},
                             reference=dict(schema_version="training-round-reference-v1",
                                            protocol=dict(target_sessions=20, match_tolerance_sessions=3,
                                                          minimum_availability_delay_sessions=0,
                                                          match="same_kind_earliest_unused_within_three_sessions_never_early_availability"),
                                            detector_manifest=_trusted_detector(), context_sessions=180,
                                            visual_context_years=5)))
    rehash(queue)
    return queue


def labels(queue, decision="completed", offsets=(-4,)):
    key = queue["order"][0]
    dates = queue["sealed"]["cases"][key]["visible_dates"]
    events = [dict(kind="inverse_head_shoulders", completion_offset=offset, completion_date=dates[offset - 1])
              for offset in offsets] if decision == "completed" else []
    row = dict(case_id=key, reviewer_id="gary", reviewer_role="human", decision=decision,
               rationale="Synthetic seam control.", events=events, revision=1, supersedes_revision=None,
               view_protocol="training-five-year-v1", view_token=queue["queue_hash"],
               overview_hash=digest(queue["cards"][key]["overview"]),
               reference_hash=queue["sealed"]["reference"]["commitment_hash"],
               detector_version="causal-geometry-v1", reference_detector_input_sessions=180)
    return dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[row])


def reference(queue):
    return dict(kind="training_round", commitment=deepcopy(queue["sealed"]["reference"]))


def test_personal_diagnostic_matches_at_inclusive_three_session_boundary():
    queue = training_queue()
    completed = labels(queue)
    before = deepcopy((queue, completed))
    report = analyze_training_pass(queue, completed, reference(queue))
    result = report["overall"]["inverse_head_shoulders"]
    assert (result["matched_events"], result["signed_completion_errors_sessions"], result["availability_delays_sessions"]) == (1, [3], [3])
    assert report["mode"] == "single_investor_diagnostic" and report["status"] == "complete"
    assert report["reference_detector_input_sessions"] == 180 and report["visual_context_years"] == 5
    assert (queue, completed) == before and analyze_training_pass(queue, completed, reference(queue)) == report
    assert report["report_hash"] == digest({key: value for key, value in report.items() if key != "report_hash"})


@pytest.mark.parametrize("decision", ["uncertain", "invalid"])
def test_uncertain_or_invalid_case_is_wholly_unscored_with_null_fractions(decision):
    queue = training_queue()
    report = analyze_training_pass(queue, labels(queue, decision=decision), reference(queue))
    assert report["coverage"][f"{decision}_cases"] == 1
    assert all(row["certain_cases"] == row["predicted_events"] == row["unmatched_prediction_events"] == 0
               and row["prediction_match_fraction"] is None and row["label_match_fraction"] is None
               for row in report["overall"].values())


@pytest.mark.parametrize("trailing,offset", [(0, -4), (1, 0)])
def test_four_session_error_or_early_availability_cannot_match(trailing, offset):
    queue = training_queue(trailing=trailing)
    result = analyze_training_pass(queue, labels(queue, offsets=(offset,)), reference(queue))["overall"]["inverse_head_shoulders"]
    assert (result["predicted_events"], result["labeled_events"], result["matched_events"],
            result["unmatched_prediction_events"], result["unmatched_label_events"]) == (1, 1, 0, 1, 1)


def test_overlapping_sampling_memberships_count_once_overall_and_once_per_stratum():
    queue = training_queue(memberships=["random", "enriched"])
    report = analyze_training_pass(queue, labels(queue), reference(queue))
    rows = [report["overall"]["inverse_head_shoulders"], *(item["inverse_head_shoulders"] for item in report["by_stratum"].values())]
    assert all((row["certain_cases"], row["predicted_events"], row["matched_events"]) == (1, 1, 1) for row in rows)


@pytest.mark.parametrize("change", ["prediction", "input", "version", "parameters", "source", "commitment", "queue"])
def test_training_reference_reproduces_raw180_predictions_and_trusted_manifest(change):
    queue = training_queue()
    case = queue["sealed"]["cases"][queue["order"][0]]
    if change == "prediction":
        case["predictions"] = []
        rehash(queue)
    elif change == "input":
        case["raw_window"][-1]["close"] += 0.1
        case["window_hash"] = digest(case["raw_window"])
        rehash(queue)
    elif change in ("version", "parameters", "source"):
        field = {"version": "version", "parameters": "parameter_hash", "source": "source_file_sha256"}[change]
        queue["sealed"]["detector_manifest"][field] = "forged"
        queue["sealed"]["reference"]["detector_manifest"][field] = "forged"
        rehash(queue)
    elif change == "commitment":
        queue["sealed"]["reference"]["context_sessions"] = 1200
        rehash(queue)
    else:
        queue["queue_hash"] = "0" * 64
    with pytest.raises(ValueError):
        analyze_training_pass(queue, labels(queue), reference(queue))


@pytest.mark.parametrize("change", ["owner", "role", "study", "token", "overview", "reference", "version",
                                    "input_stamp", "revision", "supersedes", "date", "duplicate", "decision"])
def test_single_human_history_requires_derived_view_and_reference_stamps(change):
    queue = training_queue()
    completed = labels(queue)
    row = completed["entries"][0]
    if change == "study":
        completed["study_id"] = "other-study"
    elif change == "duplicate":
        row["events"].append(deepcopy(row["events"][0]))
    elif change == "date":
        row["events"][0]["completion_date"] = "2025-01-01"
    else:
        field, value = {"owner": ("reviewer_id", "other-human"), "role": ("reviewer_role", "agent"),
                        "token": ("view_token", "old-token"), "overview": ("overview_hash", "forged"),
                        "reference": ("reference_hash", "forged"), "version": ("detector_version", "v2"),
                        "input_stamp": ("reference_detector_input_sessions", 1200),
                        "revision": ("revision", 2), "supersedes": ("supersedes_revision", 1),
                        "decision": ("decision", "none")}[change]
        row[field] = value
    with pytest.raises(ValueError):
        analyze_training_pass(queue, completed, reference(queue))


def test_pending_human_pass_has_coverage_without_comparison_or_inventory():
    queue = training_queue()
    incomplete = dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[])
    report = analyze_training_pass(queue, incomplete, reference(queue))
    assert report["status"] == "pending" and report["coverage"]["unreviewed_cases"] == 1
    assert report["overall"] is None and report["by_stratum"] is None and report["inventory"] is None


def test_inventory_explains_one_to_one_differences_without_inventing_rule_defects():
    queue = training_queue()
    completed = labels(queue, offsets=(-4, -3))
    report = analyze_training_pass(queue, completed, reference(queue))
    result = report["overall"]["inverse_head_shoulders"]
    assert (result["predicted_events"], result["labeled_events"], result["matched_events"], result["unmatched_label_events"]) == (1, 2, 1, 1)
    assert [item["category"] for item in report["inventory"]] == ["matched", "unmatched_observation", "context_policy_ambiguity"]
    assert report["inventory"][0]["observation"]["completion_offset"] == -4
    assert not any(item["category"] == "demonstrated_requirement" for item in report["inventory"])


def original_inputs():
    from gary.review import build_review_queue

    settings = config()
    settings["reviewers"] = {"gary": dict(role="human"), "synthetic-agent": dict(role="agent")}
    items = [source(), source("AMGN")]
    parent = build_review_queue(items, settings)
    release = freeze_evaluation(parent, complete_passes(parent))
    for item in items:
        day, prefix = date(2016, 1, 1), []
        while day.isoformat() < item["bars"][0]["date"]:
            if day.weekday() < 5:
                prefix.append(dict(date=day.isoformat(), open=100, high=101, low=99, close=100, volume=1000))
            day += timedelta(days=1)
        item["bars"] = prefix + item["bars"]
    queue = context_review.build_review_queue(items, dict(profile="five-year-assisted-v1",
                                                         parent_queue=release["holdout_queue"],
                                                         parent_release_hash=release["release_hash"]))
    completed = empty_labels(queue)
    for key in queue["order"]:
        submitted = dict(case_id=key, reviewer_id="gary", decision="none", rationale="Synthetic control.",
                         events=[], expected_revision=0, revise=False, view_token=queue["queue_hash"])
        completed = context_review.record_review_label(queue, completed, submitted)
    receipt = dict(schema_version="completed-context-identity-reveal-v1", queue_hash=queue["queue_hash"],
                   gary_pass_snapshot_sha256=digest(completed), revealed_at_utc="2026-10-11T17:00:00+00:00",
                   charts=[dict(chart=index + 1, ticker=queue["sealed"]["cases"][key]["symbol"],
                                company="Synthetic company") for index, key in enumerate(queue["order"])])
    return queue, completed, dict(kind="original_release", release=release, parent_queue=parent, reveal_receipt=receipt)


def test_original_release_reproduces_parent_and_binds_completed_pass_to_reveal_receipt():
    queue, completed, released = original_inputs()
    before = deepcopy((queue, completed, released))
    report = analyze_training_pass(queue, completed, released)
    assert report["status"] == "complete" and report["pass_hash"] == digest(completed)
    assert report["chronology"]["status"] == "locked_snapshot_before_identity_reveal"
    assert report["chronology"]["reveal_receipt_hash"] == digest(released["reveal_receipt"])
    assert report["chronology"]["journal_prefix_commitment"] is None
    assert report["chronology"]["independence_claim"] is False and (queue, completed, released) == before


@pytest.mark.parametrize("missing", [False, True])
def test_original_release_without_receipt_reports_unknown_reveal_timing(missing):
    queue, completed, released = original_inputs()
    if missing:
        del released["reveal_receipt"]
    else:
        released["reveal_receipt"] = None
    report = analyze_training_pass(queue, completed, released)
    assert report["status"] == "complete"
    assert report["chronology"] == dict(status="reveal_timing_unknown", locked_pass_hash=digest(completed),
                                       revealed_at_utc=None, reveal_receipt_hash=None,
                                       journal_prefix_commitment=None, independence_claim=False)


@pytest.mark.parametrize("change", ["source", "parameters", "evaluator", "prediction", "protocol"])
def test_original_release_rejects_coherently_rehashed_untrusted_commitments(change):
    queue, completed, released = original_inputs()
    release = released["release"]
    if change in ("source", "parameters"):
        field = "source_file_sha256" if change == "source" else "parameter_hash"
        release["detector_manifest"][field] = "0" * 64
    elif change == "evaluator":
        release["evaluator_manifest"]["review_source_file_sha256"] = "0" * 64
    elif change == "prediction":
        release["holdout_predictions"][queue["order"][0]].append(
            dict(kind="cup_handle", completion_date="2025-01-01", available_at="2025-01-01"))
    else:
        release["matching_policy"]["match_tolerance_sessions"] = 4
    release["release_hash"] = digest({key: value for key, value in release.items() if key != "release_hash"})
    queue["sealed"]["context_review"]["parent_release_hash"] = release["release_hash"]
    queue["queue_hash"] = digest({key: value for key, value in queue.items() if key != "queue_hash"})
    completed["queue_hash"] = queue["queue_hash"]
    released["reveal_receipt"]["queue_hash"] = queue["queue_hash"]
    released["reveal_receipt"]["gary_pass_snapshot_sha256"] = digest(completed)
    with pytest.raises(ValueError):
        analyze_training_pass(queue, completed, released)


@pytest.mark.parametrize("change", ["schema", "queue", "pass", "naive_time", "invalid_time",
                                    "missing_time", "chart_order", "chart_type", "ticker", "company", "missing_chart"])
def test_present_conflicting_reveal_evidence_fails_instead_of_becoming_unknown(change):
    queue, completed, released = original_inputs()
    receipt = released["reveal_receipt"]
    if change in ("schema", "queue", "pass", "naive_time", "invalid_time"):
        field, value = {"schema": ("schema_version", "other-schema"), "queue": ("queue_hash", "0" * 64),
                        "pass": ("gary_pass_snapshot_sha256", "0" * 64),
                        "naive_time": ("revealed_at_utc", "2026-10-11T17:00:00"),
                        "invalid_time": ("revealed_at_utc", "not-a-timestamp")}[change]
        receipt[field] = value
    elif change == "missing_time":
        del receipt["revealed_at_utc"]
    elif change == "missing_chart":
        receipt["charts"].pop()
    else:
        field, value = {"chart_order": ("chart", 2), "chart_type": ("chart", True),
                        "ticker": ("ticker", "OTHER"), "company": ("company", "")}[change]
        receipt["charts"][0][field] = value
    with pytest.raises(ValueError):
        analyze_training_pass(queue, completed, released)


def test_later_original_revision_cannot_replace_the_receipt_bound_report():
    queue, completed, released = original_inputs()
    original = analyze_training_pass(queue, completed, released)
    revised = context_review.record_review_label(queue, completed,
        dict(case_id=queue["order"][0], reviewer_id="gary", decision="uncertain", rationale="Synthetic revision.",
             events=[], expected_revision=1, revise=True, view_token=queue["queue_hash"]))
    with pytest.raises(ValueError):
        analyze_training_pass(queue, revised, released)
    development = analyze_training_pass(queue, revised, released | {"reveal_receipt": None})
    assert development["chronology"]["status"] == "reveal_timing_unknown"
    assert development["pass_hash"] != original["pass_hash"] and development["report_hash"] != original["report_hash"]
    assert analyze_training_pass(queue, completed, released) == original


def test_original_revision_history_rejects_boolean_superseded_revision():
    queue, completed, released = original_inputs()
    revised = context_review.record_review_label(queue, completed,
        dict(case_id=queue["order"][0], reviewer_id="gary", decision="uncertain", rationale="Synthetic revision.",
             events=[], expected_revision=1, revise=True, view_token=queue["queue_hash"]))
    revised["entries"][-1]["supersedes_revision"] = True
    with pytest.raises(ValueError):
        analyze_training_pass(queue, revised, released | {"reveal_receipt": None})


def test_original_missing_chronology_preserves_coverage_only_for_an_incomplete_pass():
    queue, completed, released = original_inputs()
    completed["entries"].pop()
    report = analyze_training_pass(queue, completed, released | {"reveal_receipt": None})
    assert report["status"] == "pending" and report["coverage"]["unreviewed_cases"] == 1
    assert report["chronology"]["status"] == "reveal_timing_unknown"
    assert report["overall"] is None and report["by_stratum"] is None and report["inventory"] is None


def test_training_history_input_session_stamp_requires_an_integer():
    queue = training_queue()
    completed = labels(queue)
    completed["entries"][0]["reference_detector_input_sessions"] = 180.0
    with pytest.raises(ValueError):
        analyze_training_pass(queue, completed, reference(queue))


def test_training_case_order_requires_a_list_even_when_hashes_are_coherent():
    queue = training_queue()
    completed = labels(queue)
    queue["order"] = {key: None for key in queue["order"]}
    rehash(queue)
    completed["queue_hash"] = queue["queue_hash"]
    completed["entries"][0]["view_token"] = queue["queue_hash"]
    with pytest.raises(ValueError):
        analyze_training_pass(queue, completed, reference(queue))
