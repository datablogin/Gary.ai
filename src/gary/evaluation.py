"""Frozen original-context recognition evaluation; no trading or persistence effects."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from random import Random

from gary.patterns import _PARAMETER_HASH, _VERSION
from gary.review import _KINDS, _card, _hash, _history, _matching, _validate_context, summarize_review

_PROTOCOL = {
    "schema": "recognition-evaluation-v1", "context_sessions": 180, "target_sessions": 20,
    "consensus": "two_registered_latest_certain_exact_decision_and_event_sets",
    "match": "same_kind_earliest_unused_within_three_sessions_never_early_availability",
    "reporting": "time_or_symbol_holdout_then_random_or_enriched_no_individual_scores",
    "partial_holdout": "coverage_only_until_both_complete_passes",
}
_MATCHING_POLICY = {"target_sessions": 20, "match_tolerance_sessions": 3,
                    "minimum_availability_delay_sessions": 0, "consensus": _PROTOCOL["consensus"]}


def _evaluator_manifest():
    directory = Path(__file__).parent
    return {"review_source_file_sha256": sha256((directory / "review.py").read_bytes()).hexdigest(),
            "evaluation_source_file_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "protocol_hash": _hash(_PROTOCOL)}


def _trusted_detector():
    return {"version": _VERSION, "parameter_hash": _PARAMETER_HASH,
            "source_file_sha256": sha256(Path(__file__).with_name("patterns.py").read_bytes()).hexdigest()}


def freeze_evaluation(queue: dict, calibration_labels: dict, detector_version="causal-geometry-v1") -> dict:
    """Commit the original study and calibration snapshot before holdout release."""
    latest = _history(queue, calibration_labels)
    if detector_version != "causal-geometry-v1" or queue["schema_version"] != "pattern-review-v1" or queue["sealed"]["config"].get("profile") or not queue["order"]:
        raise ValueError("release requires original calibration and the supported frozen detector")
    reviewers = queue["sealed"]["config"]["reviewers"]
    if any((key, reviewer) not in latest for key in queue["order"] for reviewer in reviewers):
        raise ValueError("complete both calibration passes before release")
    trusted = _trusted_detector()
    if queue["sealed"]["detector"] != trusted or queue["sealed"]["config"]["detector_source_file_sha256"] != trusted["source_file_sha256"]:
        raise ValueError("detector manifest differs from trusted source and parameters")
    try:
        config = queue["sealed"]["config"]
        calibration_cases = {key for key, case in queue["sealed"]["cases"].items() if case["split"] == "calibration"}
        if set(queue["cards"]) != calibration_cases or set(queue["order"]) != calibration_cases or len(queue["order"]) != len(calibration_cases) or queue["study_id"] != config["study_id"] or queue["sealed"]["holdout_locked"] is not True:
            raise ValueError("original calibration partition integrity mismatch")
        if any(item["symbol"] in {"JNJ", "JPM", "KO"} for item in queue["sealed"]["sources"]):
            raise ValueError("original sources overlap the separate five-year exploration")
        for key, case in queue["sealed"]["cases"].items():
            if len(case["raw_window"]) != 180:
                raise ValueError("release requires original 180-session contexts")
            _validate_context(queue, key, case)
            if case["split"] not in ("calibration", "time_holdout", "symbol_holdout") or (case["split"] == "symbol_holdout") != (case["symbol"] in config["reserved_sources"]) or case["split"] == "calibration" and case["as_of"] > config["calibration_end"] or case["split"] == "time_holdout" and case["start_date"] <= config["calibration_end"]:
                raise ValueError("original source/time partition integrity mismatch")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"original context integrity invalid: {error}") from error
    cases = {key: deepcopy(case) for key, case in queue["sealed"]["cases"].items() if case["split"] != "calibration"}
    detector = deepcopy(queue["sealed"]["detector"])
    release = {
        "schema_version": "pattern-evaluation-release-v1", "parent_study_id": queue["study_id"],
        "parent_queue_hash": queue["queue_hash"], "calibration_labels": deepcopy(calibration_labels),
        "calibration_labels_hash": _hash(calibration_labels), "detector_manifest": detector,
        "evaluator_manifest": _evaluator_manifest(), "baseline_version": detector["version"],
        "candidate_version": detector_version, "matching_policy": deepcopy(_MATCHING_POLICY),
        "sources": deepcopy(queue["sealed"]["sources"]),
        "holdout_predictions": {key: deepcopy(case["predictions"]) for key, case in cases.items()},
        "holdout_contexts": {key: {"window_hash": case["window_hash"],
                                  "visible_dates_hash": _hash(case["visible_dates"])} for key, case in cases.items()},
        "exposure_audit": {"original_context_sessions": 180, "five_year_source_symbols": ["JNJ", "JPM", "KO"],
                           "five_year_after_freeze": True, "five_year_source_overlap": False,
                           "limitations": ["Earlier developer exposure prevents a pristine financial-holdout claim.",
                                           "New-source contexts are exploration and cannot tune this frozen version."]},
    }
    release["release_id"] = _hash(release)
    config = deepcopy(queue["sealed"]["config"])
    config.update(profile="released-holdout-v1", parent_queue_hash=queue["queue_hash"],
                  release_id=release["release_id"], holdout_locked=False,
                  study_id="gary-holdout-" + release["release_id"])
    order = sorted(cases)
    Random(config["shuffle_seed"]).shuffle(order)
    held = {"schema_version": "pattern-review-released-holdout-v1", "study_id": config["study_id"],
            "cards": {key: _card(key, case["raw_window"]) for key, case in cases.items()}, "order": order,
            "sealed": {"config": config, "sources": deepcopy(queue["sealed"]["sources"]), "cases": cases,
                       "detector": detector, "runtime": deepcopy(queue["sealed"]["runtime"]),
                       "exclusions": deepcopy(queue["sealed"]["exclusions"]), "holdout_locked": False,
                       "parent_queue_hash": queue["queue_hash"], "release_id": release["release_id"]}}
    held["queue_hash"] = _hash(held)
    release["holdout_queue"] = held
    release["release_hash"] = _hash(release)
    return release


def evaluate_detector(queue: dict, labels: dict, release: dict, phase: str) -> dict:
    """Report frozen recognition evidence; incomplete holdout passes expose coverage only."""
    if phase not in ("calibration", "holdout"):
        raise ValueError("evaluation phase must be calibration or holdout")
    try:
        expected = freeze_evaluation(queue, release["calibration_labels"], release["candidate_version"])
        if release != expected:
            raise ValueError("release commitments differ from parent evidence or trusted manifests")
        if phase == "calibration" and labels != release["calibration_labels"]:
            raise ValueError("calibration snapshot differs from the frozen release")
    except (AttributeError, IndexError, KeyError, OSError, TypeError, ValueError) as error:
        raise ValueError(f"release integrity invalid: {error}") from error
    active = queue if phase == "calibration" else release["holdout_queue"]
    report = summarize_review(active, labels)
    report.update(phase=phase, status="evaluated", holdout_locked=phase == "calibration",
                  parent_queue_hash=queue["queue_hash"], release_id=release["release_id"],
                  release_hash=release["release_hash"], calibration_labels_hash=release["calibration_labels_hash"],
                  label_snapshot_hash=_hash(labels), evaluated_version=release["candidate_version"],
                  detector_manifest=deepcopy(release["detector_manifest"]),
                  evaluator_manifest=deepcopy(release["evaluator_manifest"]))
    if phase == "holdout" and any(row["unreviewed"] for row in report["coverage"]["by_reviewer"].values()):
        report.update(status="pending_labels", recognition_agreement=None, consensus=None)
    elif phase == "holdout":
        report["recognition_agreement"] = _holdout_metrics(active, labels)
    report["limitations"] = ["Retrospective small recognition pilot; no investment efficacy or universe accuracy estimate.",
                             "Human-supported and agent-only observations retain distinct provenance.",
                             "Random/enriched strata can overlap; enrichment was selected by frozen v1.",
                             "Holdout feedback cannot tune the evaluated version; later candidates need fresh evaluation data."]
    return report


def _holdout_metrics(queue, labels):
    latest = _history(queue, labels)
    reviewers = queue["sealed"]["config"]["reviewers"]
    metrics = {split: {stratum: {kind: {
        "certain_cases": 0, "predicted_events": 0, "labeled_events": 0, "matched_events": 0,
        "unmatched_prediction_events": 0, "unmatched_label_events": 0,
        "signed_completion_errors_sessions": [], "availability_delays_sessions": [],
        "prediction_match_fraction": None, "label_match_fraction": None,
    } for kind in _KINDS} for stratum in ("random", "enriched")} for split in ("time_holdout", "symbol_holdout")}
    for key in queue["order"]:
        rows = [latest[(key, reviewer)] for reviewer in reviewers]
        if rows[0]["decision"] not in ("completed", "none") or rows[0]["decision"] != rows[1]["decision"] or rows[0]["events"] != rows[1]["events"]:
            continue
        case = queue["sealed"]["cases"][key]
        matched = _matching(case, rows[0]["events"])
        for stratum in case["memberships"]:
            for kind in _KINDS:
                row = metrics[case["split"]][stratum][kind]
                row["certain_cases"] += 1
                for field, value in matched[kind].items():
                    if isinstance(value, list):
                        row[field].extend(value)
                    else:
                        row[field] += value
    for split in metrics.values():
        for stratum in split.values():
            for row in stratum.values():
                row["prediction_match_fraction"] = row["matched_events"] / row["predicted_events"] if row["predicted_events"] else None
                row["label_match_fraction"] = row["matched_events"] / row["labeled_events"] if row["labeled_events"] else None
    return metrics
