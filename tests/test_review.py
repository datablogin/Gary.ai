"""Synthetic controls at the three user-approved review interfaces."""

from datetime import date, timedelta
import json
from pathlib import Path
import pytest

from gary.patterns import detect_patterns

from gary.review import build_review_queue, record_review_label, summarize_review


def config():
    return {
        "study_id": "synthetic-review", "id_salt": "private-test-salt",
        "random_seed": 20261010, "shuffle_seed": 20261011,
        "window_sessions": 180, "target_sessions": 20,
        "calibration_end": "2024-12-31", "reserved_sources": ["AMGN", "SIRI"],
        "calibration_random_per_source": 2, "time_holdout_random_per_source": 1,
        "reserved_random_per_source": 3, "match_tolerance_sessions": 3,
        "holdout_locked": True, "detector_version": "causal-geometry-v1",
        "detector_parameter_hash": "d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae",
        "detector_source_file_sha256": "76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a",
        "reviewers": {"observer-a": {"role": "agent"}, "observer-b": {"role": "agent"}},
    }


def source(symbol="MU", count=900):
    bars, day = [], date(2023, 1, 2)
    while len(bars) < count:
        if day.weekday() < 5:
            close = 100 + len(bars) / 100
            bars.append(dict(date=day.isoformat(), open=close, high=close + 1,
                             low=close - 1, close=close, volume=1000))
        day += timedelta(days=1)
    return dict(source_id=f"synthetic-{symbol}", symbol=symbol, source_sha256="a" * 64,
                fetched_at="2026-10-10T20:00:00Z", exchange_timezone="America/New_York",
                price_basis="provider_received_ohlc", bars=bars, split_dates=[])


def source_with_inverse():
    item = source()
    drawn = json.loads((Path(__file__).parent / "fixtures" / "pattern-inverse.json").read_text())["bars"]
    for offset, bar in enumerate(drawn):
        item["bars"][330 + offset].update({key: value for key, value in bar.items() if key != "date"})
    return item


def test_queue_opens_two_normalized_fixed_length_random_calibration_cards():
    queue = build_review_queue([source()], config())
    assert len(queue.get("cards", {})) == 2
    for card in queue["cards"].values():
        assert len(card["bars"]) == 180
        assert card["bars"][0]["offset"] == -179
        assert card["bars"][-1]["offset"] == 0
        assert card["bars"][0]["close"] == 100
        assert card["bars"][0]["volume"] == 1
        assert card["target_start_offset"] == -19


def test_reserved_sources_and_full_context_time_holdout_stay_sealed():
    queue = build_review_queue([source(), source("AMGN")], config())
    cases = queue["sealed"]["cases"]
    assert len(queue["cards"]) == 2
    assert sum(case["split"] == "symbol_holdout" for case in cases.values()) == 3
    assert sum(case["split"] == "time_holdout" for case in cases.values()) == 1
    for case_id, case in cases.items():
        if case["split"] != "calibration":
            assert case_id not in queue["cards"] and case_id not in queue["order"]
        if case["split"] == "time_holdout":
            assert case["start_date"] > "2024-12-31"


def test_known_split_intersections_are_never_open_or_locked_cases():
    item = source()
    original = build_review_queue([item], config())
    chosen = next(case for case in original["sealed"]["cases"].values() if case["split"] == "calibration")
    split_date = chosen["visible_dates"][-1]
    item["split_dates"] = [split_date]
    queue = build_review_queue([item], config())
    assert all(not case["start_date"] <= split_date <= case["as_of"]
               for case in queue["sealed"]["cases"].values())


def test_enrichment_retains_predictions_from_exact_visible_context():
    item = source_with_inverse()
    queue = build_review_queue([item], config())
    enriched = [case for case in queue["sealed"]["cases"].values() if "enriched" in case["memberships"]]
    assert len(enriched) == 1
    case = enriched[0]
    assert case["as_of"] == item["bars"][400]["date"]
    visible_predictions = [signal for signal in detect_patterns(case["raw_window"], case["as_of"])
                           if signal["completion_date"] >= case["visible_dates"][-20]]
    assert case["predictions"] == visible_predictions
    assert case["predictions"][0]["kind"] == "inverse_head_shoulders"


def test_unsupported_window_change_fails_instead_of_mislabeling_cards():
    settings = config()
    settings["window_sessions"] = 181
    with pytest.raises(ValueError, match="config"):
        build_review_queue([source()], settings)


def test_absent_corporate_action_metadata_has_explicit_error():
    item = source()
    del item["split_dates"]
    with pytest.raises(ValueError, match="source"):
        build_review_queue([item], config())


def empty_labels(queue):
    return dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[])


def entry(queue, reviewer="observer-a", decision="completed", events=None):
    return dict(case_id=queue["order"][0], reviewer_id=reviewer, decision=decision,
                events=events if events is not None else [dict(kind="inverse_head_shoulders", completion_offset=-1)],
                rationale="Independent synthetic annotation", expected_revision=0, revise=False)


def test_completed_label_records_private_date_role_and_revision_without_mutation():
    queue = build_review_queue([source()], config())
    previous = empty_labels(queue)
    submitted = entry(queue)
    result = record_review_label(queue, previous, submitted)
    assert len(result.get("entries", [])) == 1
    label = result["entries"][0]
    assert label["revision"] == 1 and label["supersedes_revision"] is None
    assert label["reviewer_role"] == "agent"
    assert label["events"][0]["completion_date"] == queue["sealed"]["cases"][submitted["case_id"]]["visible_dates"][-2]
    assert previous["entries"] == [] and "completion_date" not in submitted["events"][0]


def test_identical_label_retry_is_idempotent():
    queue = build_review_queue([source()], config())
    submitted = entry(queue)
    labels = record_review_label(queue, empty_labels(queue), submitted)
    assert record_review_label(queue, labels, submitted) == labels


def test_conflicting_label_needs_explicit_current_revision_and_keeps_trail():
    queue = build_review_queue([source()], config())
    first = record_review_label(queue, empty_labels(queue), entry(queue))
    changed = entry(queue, decision="none", events=[])
    with pytest.raises(ValueError, match="revision"):
        record_review_label(queue, first, changed)
    changed.update(revise=True, expected_revision=1)
    second = record_review_label(queue, first, changed)
    assert len(second["entries"]) == 2
    assert second["entries"][-1]["revision"] == 2
    assert second["entries"][-1]["supersedes_revision"] == 1
    assert first["entries"][0]["decision"] == "completed"


@pytest.mark.parametrize("change", ["holdout", "reviewer", "future", "decision"])
def test_label_validation_blocks_ineligible_or_ambiguous_submission(change):
    queue = build_review_queue([source()], config())
    submitted = entry(queue)
    if change == "holdout":
        submitted["case_id"] = next(key for key, case in queue["sealed"]["cases"].items() if case["split"] != "calibration")
    elif change == "reviewer":
        submitted["reviewer_id"] = "unregistered"
    elif change == "future":
        submitted["events"][0]["completion_offset"] = 1
    else:
        submitted["decision"] = "uncertain"
    previous = empty_labels(queue)
    with pytest.raises(ValueError):
        record_review_label(queue, previous, submitted)
    assert previous["entries"] == []


def test_changed_queue_or_wrong_label_study_is_rejected():
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    labels["queue_hash"] = "b" * 64
    with pytest.raises(ValueError, match="study"):
        record_review_label(queue, labels, entry(queue))


def test_unreviewed_cards_are_pending_with_no_recognition_denominator():
    queue = build_review_queue([source()], config())
    report = summarize_review(queue, empty_labels(queue))
    assert report.get("consensus", {}).get("pending_cases") == 2
    assert report["consensus"]["certain_cases"] == 0
    assert report["holdout_locked"] is True and report["trading_approval"] is False
    assert report["coverage"]["by_reviewer"]["observer-a"]["unreviewed"] == 2
    assert all(row["certain_cases"] == 0 for stratum in report["recognition_agreement"].values() for row in stratum.values())


def test_two_exact_none_labels_create_one_agent_consensus_case():
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        labels = record_review_label(queue, labels, entry(queue, reviewer, decision="none", events=[]))
    report = summarize_review(queue, labels)
    assert report["consensus"]["certain_cases"] == 1
    assert report["consensus"]["agent_only_cases"] == 1
    assert report["consensus"]["pending_cases"] == 1
    assert report["recognition_agreement"]["random"]["cup_handle"]["certain_cases"] == 1
    assert report["recognition_agreement"]["random"]["cup_handle"]["prediction_match_fraction"] is None


def test_consensus_detected_event_matches_once_in_its_own_stratum():
    queue = build_review_queue([source_with_inverse()], config())
    case_id = next(key for key, case in queue["sealed"]["cases"].items() if "enriched" in case["memberships"])
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        submitted = entry(queue, reviewer, events=[dict(kind="inverse_head_shoulders", completion_offset=0)])
        submitted["case_id"] = case_id
        labels = record_review_label(queue, labels, submitted)
    report = summarize_review(queue, labels)
    matched = report["recognition_agreement"]["enriched"]["inverse_head_shoulders"]
    assert (matched["predicted_events"], matched["labeled_events"], matched["matched_events"]) == (1, 1, 1)
    assert matched["signed_completion_errors_sessions"] == [0]
    assert matched["availability_delays_sessions"] == [0]
    assert report["recognition_agreement"]["random"]["inverse_head_shoulders"]["matched_events"] == 0


def test_detector_cannot_match_an_independently_later_completion():
    item = source_with_inverse()
    # Move the drawing so one seeded random card ends two sessions after its breakout.
    quiet = build_review_queue([source()], config())
    random_end = quiet["sealed"]["cases"][quiet["order"][0]]["source_end_index"]
    drawing = [dict(bar) for bar in item["bars"][330:401]]
    shifted = source()
    for index, bar in enumerate(drawing):
        shifted["bars"][random_end - 72 + index].update({key: value for key, value in bar.items() if key != "date"})
    queue = build_review_queue([shifted], config())
    case_id = next(key for key, case in queue["sealed"]["cases"].items() if case["source_end_index"] == random_end)
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        submitted = entry(queue, reviewer, events=[dict(kind="inverse_head_shoulders", completion_offset=0)])
        submitted["case_id"] = case_id
        labels = record_review_label(queue, labels, submitted)
    row = summarize_review(queue, labels)["recognition_agreement"]["random"]["inverse_head_shoulders"]
    assert row["predicted_events"] == 1
    assert row["matched_events"] == 0 and row["unmatched_prediction_events"] == 1


@pytest.mark.parametrize("field,value", [("case_id", []), ("reviewer_id", {})])
def test_nonstring_submission_identity_has_public_validation_error(field, value):
    queue = build_review_queue([source()], config())
    submitted = entry(queue)
    submitted[field] = value
    with pytest.raises(ValueError):
        record_review_label(queue, empty_labels(queue), submitted)


def test_all_source_dates_are_validated_even_beyond_last_listed_date():
    item = source()
    item["bars"][0]["date"] = "2099-01-01"
    with pytest.raises(ValueError, match="source"):
        build_review_queue([item], config())


def test_malformed_reserved_source_config_uses_public_error():
    settings = config()
    settings["reserved_sources"] = [None, "AMGN"]
    with pytest.raises(ValueError, match="config"):
        build_review_queue([source()], settings)


def test_queue_is_deterministic_across_source_order_and_leaves_inputs_unchanged():
    from copy import deepcopy
    inputs, settings = [source(), source("AMGN")], config()
    original = deepcopy(inputs), deepcopy(settings)
    first = build_review_queue(inputs, settings)
    assert build_review_queue(list(reversed(inputs)), settings) == first
    assert inputs == original[0] and settings == original[1]


def test_open_payload_has_no_source_prediction_or_calendar_metadata():
    queue = build_review_queue([source_with_inverse()], config())
    for key, card in queue["cards"].items():
        assert set(card) == {"case_id", "bars", "target_start_offset", "target_end_offset", "price_basis", "volume_available"}
        assert all(set(bar) == {"offset", "open", "high", "low", "close", "volume"} for bar in card["bars"])
        assert queue["sealed"]["cases"][key]["as_of"] <= "2024-12-31"


@pytest.mark.parametrize("decision", ["uncertain", "invalid"])
def test_non_certain_reviews_never_enter_recognition_counts(decision):
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        labels = record_review_label(queue, labels, entry(queue, reviewer, decision=decision, events=[]))
    report = summarize_review(queue, labels)
    assert report["consensus"]["certain_cases"] == 0
    assert report["consensus"][f"{decision}_cases"] == 1
    assert all(row["certain_cases"] == 0 for stratum in report["recognition_agreement"].values() for row in stratum.values())


def test_even_one_session_of_review_disagreement_is_unscored():
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    for reviewer, offset in [("observer-a", -1), ("observer-b", 0)]:
        labels = record_review_label(queue, labels, entry(queue, reviewer, events=[dict(kind="inverse_head_shoulders", completion_offset=offset)]))
    report = summarize_review(queue, labels)
    assert report["consensus"]["disagreement_cases"] == 1
    assert report["consensus"]["certain_cases"] == 0


def test_one_prediction_cannot_match_two_independent_consensus_events():
    queue = build_review_queue([source_with_inverse()], config())
    key = next(key for key, case in queue["sealed"]["cases"].items() if "enriched" in case["memberships"])
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        submitted = entry(queue, reviewer, events=[dict(kind="inverse_head_shoulders", completion_offset=offset) for offset in [-1, 0]])
        submitted["case_id"] = key
        labels = record_review_label(queue, labels, submitted)
    matched = summarize_review(queue, labels)["recognition_agreement"]["enriched"]["inverse_head_shoulders"]
    assert matched["predicted_events"] == 1 and matched["labeled_events"] == 2
    assert matched["matched_events"] == 1 and matched["unmatched_label_events"] == 1
    assert matched["signed_completion_errors_sessions"] == [1]


def test_latest_revision_can_remove_consensus_without_erasing_provenance():
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        labels = record_review_label(queue, labels, entry(queue, reviewer, decision="none", events=[]))
    changed = entry(queue, decision="uncertain", events=[])
    changed.update(revise=True, expected_revision=1)
    labels = record_review_label(queue, labels, changed)
    report = summarize_review(queue, labels)
    assert len(labels["entries"]) == 3 and report["consensus"]["certain_cases"] == 0
    assert report["consensus"]["uncertain_cases"] == 1


def test_changed_frozen_queue_is_rejected_without_label_mutation():
    queue = build_review_queue([source()], config())
    labels = empty_labels(queue)
    queue["sealed"]["cases"][queue["order"][0]]["memberships"].append("enriched")
    with pytest.raises(ValueError, match="integrity"):
        record_review_label(queue, labels, entry(queue))
    assert labels["entries"] == []


def test_zero_volume_has_unknown_display_ratio():
    item = source()
    for bar in item["bars"]:
        bar["volume"] = 0
    queue = build_review_queue([item], config())
    assert all(card["volume_available"] is False and all(bar["volume"] is None for bar in card["bars"])
               for card in queue["cards"].values())


def test_random_enriched_duplicate_is_one_card_with_explicit_overlap_count():
    item = source()
    quiet = build_review_queue([item], config())
    end = quiet["sealed"]["cases"][quiet["order"][0]]["source_end_index"]
    drawing = json.loads((Path(__file__).parent / "fixtures" / "pattern-inverse.json").read_text())["bars"]
    for offset, bar in enumerate(drawing):
        item["bars"][end - 70 + offset].update({key: value for key, value in bar.items() if key != "date"})
    queue = build_review_queue([item], config())
    assert len(queue["cards"]) == 2
    assert sum(case["memberships"] == ["random", "enriched"] for case in queue["sealed"]["cases"].values()) == 1
    assert summarize_review(queue, empty_labels(queue)).get("stratum_overlap_cases") == 1


def five_year_config():
    return {
        "profile": "five-year-v1", "study_id": "synthetic-five-year", "id_salt": "context-test-salt",
        "reviewers": config()["reviewers"], "detector_version": config()["detector_version"],
        "detector_parameter_hash": config()["detector_parameter_hash"],
        "detector_source_file_sha256": config()["detector_source_file_sha256"],
        "as_of": "2026-10-09", "context_years": 5, "target_sessions": 20,
        "source_symbols": ["JNJ", "JPM", "KO"], "shuffle_seed": 20261012, "holdout_locked": True,
    }


def five_year_sources():
    items = []
    for symbol in ("JNJ", "JPM", "KO"):
        item = source(symbol, 1305)
        day, bars = date(2021, 10, 11), []
        while day <= date(2026, 10, 9):
            if day.weekday() < 5:
                close = 100 + len(bars) / 100
                bars.append(dict(date=day.isoformat(), open=close, high=close + 1,
                                 low=close - 1, close=close, volume=1000))
            day += timedelta(days=1)
        item["bars"] = bars
        items.append(item)
    return items


def test_five_year_profile_has_three_full_anonymous_daily_contexts():
    queue = build_review_queue(five_year_sources(), five_year_config())
    assert queue["schema_version"] == "pattern-review-five-year-v1"
    assert len(queue["cards"]) == 3
    for key, card in queue["cards"].items():
        assert len(card["bars"]) == 1305
        assert card["bars"][0]["offset"] == -1304
        assert card["bars"][-1]["offset"] == 0
        assert card["bars"][0]["close"] == 100
        assert set(card) == {"case_id", "bars", "target_start_offset", "target_end_offset", "price_basis", "volume_available"}
        assert queue["sealed"]["cases"][key]["requested_start"] == "2021-10-09"


@pytest.mark.parametrize("change", ["short", "late_start", "split", "original_source", "missing_cutoff", "unsupported_config"])
def test_five_year_profile_refuses_incomplete_or_ineligible_context(change):
    items, settings = five_year_sources(), five_year_config()
    if change == "short":
        items[0]["bars"] = items[0]["bars"][-1199:]
    elif change == "late_start":
        items[0]["bars"] = items[0]["bars"][6:]
    elif change == "split":
        items[0]["split_dates"] = [items[0]["bars"][0]["date"]]
    elif change == "original_source":
        items[0]["symbol"] = "MU"
    elif change == "missing_cutoff":
        items[0]["bars"].pop()
    else:
        settings["context_years"] = 4
    with pytest.raises(ValueError):
        build_review_queue(items, settings)


def test_five_year_labels_match_final_event_with_dynamic_offsets_and_exploration_status():
    items = five_year_sources()
    drawing = json.loads((Path(__file__).parent / "fixtures" / "pattern-inverse.json").read_text())["bars"]
    for offset, bar in enumerate(drawing):
        items[0]["bars"][-len(drawing) + offset].update({key: value for key, value in bar.items() if key != "date"})
    queue = build_review_queue(items, five_year_config())
    key = next(key for key, case in queue["sealed"]["cases"].items() if case["symbol"] == "JNJ")
    labels = empty_labels(queue)
    for reviewer in ("observer-a", "observer-b"):
        submitted = entry(queue, reviewer, events=[dict(kind="inverse_head_shoulders", completion_offset=0)])
        submitted["case_id"] = key
        labels = record_review_label(queue, labels, submitted)
    report = summarize_review(queue, labels)
    assert report["recognition_agreement"]["random"]["inverse_head_shoulders"]["matched_events"] == 1
    assert report["phase"] == "exploration" and report["sampling"] == "convenience"
    assert labels["entries"][0]["events"][0]["completion_date"] == "2026-10-09"


@pytest.mark.parametrize("seam", ["label", "summary"])
def test_five_year_public_card_tampering_is_rejected_even_with_recomputed_hash(seam):
    from hashlib import sha256

    queue = build_review_queue(five_year_sources(), five_year_config())
    queue["cards"][queue["order"][0]]["bars"][0]["close"] = 101
    queue["queue_hash"] = sha256(json.dumps({key: value for key, value in queue.items() if key != "queue_hash"},
                                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    labels = empty_labels(queue)
    with pytest.raises(ValueError, match="integrity"):
        if seam == "label":
            record_review_label(queue, labels, entry(queue, decision="none", events=[]))
        else:
            summarize_review(queue, labels)
    assert labels["entries"] == []


@pytest.mark.parametrize("change", ["dates", "predictions", "missing_card", "schema", "detector", "lock"])
def test_new_profile_summary_validates_private_context_and_structure_before_first_label(change):
    from hashlib import sha256

    queue = build_review_queue(five_year_sources(), five_year_config())
    key = queue["order"][0]
    if change == "dates":
        queue["sealed"]["cases"][key]["visible_dates"][0] = "1900-01-01"
    elif change == "predictions":
        queue["sealed"]["cases"][key]["predictions"] = [{"kind": "cup_handle"}]
    elif change == "missing_card":
        del queue["cards"][key]
    elif change == "schema":
        queue["schema_version"] = "pattern-review-v1"
    elif change == "detector":
        queue["sealed"]["detector"]["source_file_sha256"] = "b" * 64
    else:
        queue["sealed"]["holdout_locked"] = False
    queue["queue_hash"] = sha256(json.dumps({key: value for key, value in queue.items() if key != "queue_hash"},
                                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    with pytest.raises(ValueError, match="integrity"):
        summarize_review(queue, empty_labels(queue))


def test_five_year_profile_cannot_omit_a_declared_source_after_rehashing():
    from hashlib import sha256

    queue = build_review_queue(five_year_sources(), five_year_config())
    key = queue["order"].pop()
    del queue["cards"][key]
    del queue["sealed"]["cases"][key]
    queue["queue_hash"] = sha256(json.dumps({key: value for key, value in queue.items() if key != "queue_hash"},
                                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    with pytest.raises(ValueError, match="integrity"):
        summarize_review(queue, empty_labels(queue))
