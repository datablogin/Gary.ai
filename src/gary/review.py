"""Blinded local annotation at the three approved review seams."""

from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
from platform import python_version
from random import Random
import re
from statistics import median
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gary.patterns import detect_patterns

_FROZEN = {
    "random_seed": 20261010, "shuffle_seed": 20261011, "window_sessions": 180,
    "target_sessions": 20, "calibration_end": "2024-12-31", "reserved_sources": ["AMGN", "SIRI"],
    "calibration_random_per_source": 2, "time_holdout_random_per_source": 1,
    "reserved_random_per_source": 3, "match_tolerance_sessions": 3, "holdout_locked": True,
    "detector_version": "causal-geometry-v1",
    "detector_parameter_hash": "d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae",
}
_KINDS = ("inverse_head_shoulders", "cup_handle", "head_shoulders_top")


def _label(queue, entry):
    if not isinstance(entry, dict) or not isinstance(entry.get("case_id"), str) or entry["case_id"] not in queue["cards"]:
        raise ValueError("unknown or locked case")
    reviewers = queue["sealed"]["config"]["reviewers"]
    if not isinstance(entry.get("reviewer_id"), str) or entry["reviewer_id"] not in reviewers:
        raise ValueError("unregistered reviewer")
    if entry.get("decision") not in ("completed", "none", "uncertain", "invalid"):
        raise ValueError("invalid label decision")
    if not isinstance(entry.get("rationale"), str) or len(entry["rationale"]) > 1000:
        raise ValueError("invalid rationale")
    events = entry.get("events")
    if not isinstance(events, list) or (entry["decision"] == "completed") != bool(events):
        raise ValueError("decision and event set disagree")
    case = queue["sealed"]["cases"][entry["case_id"]]
    normalized, seen = [], set()
    for event in events:
        if not isinstance(event, dict) or set(event) != {"kind", "completion_offset"} or event.get("kind") not in _KINDS:
            raise ValueError("invalid event kind or fields")
        offset = event["completion_offset"]
        if type(offset) is not int or not -19 <= offset <= 0 or (event["kind"], offset) in seen:
            raise ValueError("invalid, duplicate or future event offset")
        seen.add((event["kind"], offset))
        normalized.append({**event, "completion_date": case["visible_dates"][offset - 1]})
    normalized.sort(key=lambda event: (event["kind"], event["completion_offset"]))
    return {key: deepcopy(entry[key]) for key in ("case_id", "reviewer_id", "decision", "rationale")} | {
        "events": normalized, "reviewer_role": reviewers[entry["reviewer_id"]]["role"]}


def _config(config):
    if not isinstance(config, dict) or set(config) != set(_FROZEN) | {"study_id", "id_salt", "reviewers", "detector_source_file_sha256"}:
        raise ValueError("config fields do not match frozen study")
    copied = deepcopy(config)
    if isinstance(copied["reserved_sources"], list) and all(isinstance(value, str) for value in copied["reserved_sources"]):
        copied["reserved_sources"] = sorted(copied["reserved_sources"])
    if any(type(copied[key]) is not type(value) or copied[key] != value for key, value in _FROZEN.items()):
        raise ValueError("config differs from frozen study")
    if any(not isinstance(copied[key], str) or not copied[key] or len(copied[key]) > 512 for key in ("study_id", "id_salt")):
        raise ValueError("config study identity is invalid")
    if not isinstance(copied["detector_source_file_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", copied["detector_source_file_sha256"]):
        raise ValueError("config requires detector source hash")
    reviewers = copied["reviewers"]
    if not isinstance(reviewers, dict) or len(reviewers) != 2 or any(
        not isinstance(key, str) or not key or not isinstance(value, dict) or value.get("role") not in ("human", "agent")
        for key, value in reviewers.items()
    ):
        raise ValueError("config requires exactly two registered reviewer roles")
    return copied


def _sources(series):
    required = {"source_id", "symbol", "source_sha256", "fetched_at", "exchange_timezone", "price_basis", "bars", "split_dates"}
    if not isinstance(series, list) or not series:
        raise ValueError("source series must be a nonempty list")
    seen = set()
    validated = []
    for item in series:
        if not isinstance(item, dict) or not required <= set(item):
            raise ValueError("source provenance or corporate-action metadata missing")
        if any(not isinstance(item[key], str) or not item[key] for key in ("source_id", "symbol")) or item["source_id"] in seen:
            raise ValueError("source identifiers must be nonempty and unique")
        if not isinstance(item["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["source_sha256"]) or item["price_basis"] != "provider_received_ohlc":
            raise ValueError("source hash or price basis invalid")
        try:
            if datetime.fromisoformat(item["fetched_at"].replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("source fetch time needs timezone")
            ZoneInfo(item["exchange_timezone"])
            if not isinstance(item["split_dates"], list) or any(date.fromisoformat(value).isoformat() != value for value in item["split_dates"]):
                raise ValueError("source split dates invalid")
            if not isinstance(item["bars"], list) or not item["bars"]:
                raise ValueError("source bars missing")
            dates = [bar["date"] for bar in item["bars"]]
            if any(date.fromisoformat(value).isoformat() != value for value in dates):
                raise ValueError("source bars need canonical dates")
            events = detect_patterns(item["bars"], max(dates))
        except (KeyError, TypeError, AttributeError, ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("source dates or bars invalid") from error
        seen.add(item["source_id"])
        validated.append((item, events))
    return sorted(validated, key=lambda value: value[0]["source_id"])


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _card(case_id, window):
    first_close = window[0]["close"]
    volume_base = median(bar["volume"] for bar in window)
    bars = [{"offset": index - len(window) + 1,
             **{key: bar[key] / first_close * 100 for key in ("open", "high", "low", "close")},
             "volume": bar["volume"] / volume_base if volume_base else None}
            for index, bar in enumerate(window)]
    return {"case_id": case_id, "bars": bars, "target_start_offset": -19, "target_end_offset": 0,
            "price_basis": "normalized provider-received OHLC", "volume_available": bool(volume_base)}


def _case(source, end, split, config, frame_size, probability):
    start = end - 179
    window = deepcopy(source["bars"][start:end + 1])
    window_hash = _hash(window)
    case_id = _hash([config["id_salt"], source["source_id"], window_hash])[:16]
    return case_id, {
        "source_id": source["source_id"], "symbol": source["symbol"], "split": split,
        "memberships": ["random"], "start_date": window[0]["date"], "as_of": window[-1]["date"],
        "source_start_index": start, "source_end_index": end,
        "visible_dates": [bar["date"] for bar in window], "window_hash": window_hash,
        "random_frame_size": frame_size, "random_selection_probability": probability,
        "predictions": [signal for signal in detect_patterns(window, window[-1]["date"])
                        if window[-20]["date"] <= signal["completion_date"] <= window[-1]["date"]
                        and window[-20]["date"] <= signal["available_at"] <= window[-1]["date"]],
        "raw_window": window,
    }


def build_review_queue(series: list[dict], config: dict) -> dict:
    """Freeze a private study and its calibration-only anonymous cards."""
    config = _config(config)
    cards, cases, sources, exclusions = {}, {}, [], []
    rng = Random(config["random_seed"])
    for item, events in _sources(series):
        sources.append({key: deepcopy(value) for key, value in item.items() if key != "bars"})
        sources[-1]["input_bars_hash"] = _hash(item["bars"])
        endpoints = [i for i in range(179, len(item["bars"]))
                     if not any(item["bars"][i - 179]["date"] <= split <= item["bars"][i]["date"]
                                for split in item["split_dates"])]
        if item["symbol"] in config["reserved_sources"]:
            groups = [("symbol_holdout", endpoints, config["reserved_random_per_source"])]
        else:
            groups = [
                ("calibration", [i for i in endpoints if item["bars"][i]["date"] <= config["calibration_end"]],
                 config["calibration_random_per_source"]),
                ("time_holdout", [i for i in endpoints if item["bars"][i - 179]["date"] > config["calibration_end"]],
                 config["time_holdout_random_per_source"]),
            ]
        for split, frame, count in groups:
            if len(frame) < count:
                raise ValueError("source has insufficient admissible endpoint frame")
            for end in rng.sample(frame, count):
                case_id, case = _case(item, end, split, config, len(frame), count / len(frame))
                cases[case_id] = case
                if split == "calibration":
                    cards[case_id] = _card(case_id, case["raw_window"])
        index_by_date = {bar["date"]: index for index, bar in enumerate(item["bars"])}
        for event in events:
            end = index_by_date[event["completion_date"]]
            split = next((name for name, frame, _ in groups if end in frame), None)
            reason = "insufficient_context" if end < 179 else "split_intersection" if any(
                item["bars"][end - 179]["date"] <= day <= item["bars"][end]["date"]
                for day in item["split_dates"]
            ) else "temporal_embargo" if split is None else None
            if reason:
                exclusions.append({"source_id": item["source_id"], "event_id": _hash(event), "reason": reason})
                continue
            case_id, case = _case(item, end, split, config, None, None)
            if not any(predicted["kind"] == event["kind"] and predicted["completion_date"] == event["completion_date"]
                       for predicted in case["predictions"]):
                exclusions.append({"source_id": item["source_id"], "event_id": _hash(event),
                                   "reason": "not_reproduced_in_visible_context"})
                continue
            if case_id in cases:
                if "enriched" not in cases[case_id]["memberships"]:
                    cases[case_id]["memberships"].append("enriched")
            else:
                case["memberships"] = ["enriched"]
                cases[case_id] = case
            if split == "calibration":
                cards[case_id] = _card(case_id, case["raw_window"])
    order = list(cards)
    Random(config["shuffle_seed"]).shuffle(order)
    queue = {"schema_version": "pattern-review-v1", "study_id": config["study_id"],
             "cards": cards, "order": order,
             "sealed": {"config": deepcopy(config), "sources": sources, "cases": cases,
                        "runtime": {"python_version": python_version(), "sampling": "random.Random.sample/shuffle"},
                        "detector": {"version": config["detector_version"],
                                     "parameter_hash": config["detector_parameter_hash"],
                                     "source_file_sha256": config["detector_source_file_sha256"]},
                        "exclusions": exclusions, "holdout_locked": True}}
    queue["queue_hash"] = _hash(queue)
    return queue


def record_review_label(queue: dict, labels: dict, entry: dict) -> dict:
    """Record a versioned reviewer observation without trading effects."""
    latest = _history(queue, labels)
    label = _label(queue, entry)
    if type(entry.get("expected_revision")) is not int or entry["expected_revision"] < 0 or type(entry.get("revise")) is not bool:
        raise ValueError("invalid revision controls")
    label.update(revision=1, supersedes_revision=None)
    previous = latest.get((entry["case_id"], entry["reviewer_id"]))
    if previous and all(previous[key] == label[key] for key in label if key not in ("revision", "supersedes_revision")):
        return deepcopy(labels)
    if previous:
        if entry.get("revise") is not True or entry.get("expected_revision") != previous["revision"]:
            raise ValueError("conflicting label requires explicit current revision")
        label.update(revision=previous["revision"] + 1, supersedes_revision=previous["revision"])
    elif entry.get("revise") is not False or entry.get("expected_revision") != 0:
        raise ValueError("first label requires revision zero")
    return {**deepcopy(labels), "entries": [*deepcopy(labels["entries"]), label]}


def _history(queue, labels):
    try:
        if _hash({key: value for key, value in queue.items() if key != "queue_hash"}) != queue["queue_hash"]:
            raise ValueError("study queue integrity mismatch")
        _config(queue["sealed"]["config"])
        if labels["study_id"] != queue["study_id"] or labels["queue_hash"] != queue["queue_hash"] or not isinstance(labels["entries"], list):
            raise ValueError("label study mismatch")
        latest = {}
        for row in labels["entries"]:
            entry = {key: row[key] for key in ("case_id", "reviewer_id", "decision", "rationale")}
            entry["events"] = [{key: event[key] for key in ("kind", "completion_offset")} for event in row["events"]]
            normalized = _label(queue, entry)
            key = (row["case_id"], row["reviewer_id"])
            previous = latest.get(key)
            revision = previous["revision"] + 1 if previous else 1
            supersedes = previous["revision"] if previous else None
            if type(row["revision"]) is not int or row["revision"] != revision or row["supersedes_revision"] != supersedes or any(row.get(key) != value for key, value in normalized.items()):
                raise ValueError("label revision history or provenance invalid")
            latest[key] = row
        return latest
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"study or label integrity invalid: {error}") from error


def summarize_review(queue: dict, labels: dict) -> dict:
    """Return a coordinator-private calibration-only pilot report."""
    latest = _history(queue, labels)
    reviewers = queue["sealed"]["config"]["reviewers"]
    coverage = {}
    for reviewer, metadata in reviewers.items():
        rows = [row for (case_id, identity), row in latest.items() if identity == reviewer]
        coverage[reviewer] = {"labeled": len(rows), "unreviewed": len(queue["cards"]) - len(rows),
                              "role": metadata["role"],
                              **{decision: sum(row["decision"] == decision for row in rows)
                                 for decision in ("completed", "none", "uncertain", "invalid")}}
    metrics = {stratum: {kind: {"certain_cases": 0, "predicted_events": 0, "labeled_events": 0,
                              "matched_events": 0, "unmatched_prediction_events": 0,
                              "unmatched_label_events": 0, "signed_completion_errors_sessions": [],
                              "availability_delays_sessions": [], "prediction_match_fraction": None,
                              "label_match_fraction": None} for kind in _KINDS}
               for stratum in ("random", "enriched")}
    consensus = {key: 0 for key in ("certain_cases", "pending_cases", "disagreement_cases", "uncertain_cases",
                                    "invalid_cases", "agent_only_cases", "human_supported_cases")}
    for case_id in queue["order"]:
        rows = [latest[(case_id, reviewer)] for reviewer in reviewers if (case_id, reviewer) in latest]
        decisions = [row["decision"] for row in rows]
        signatures = [(row["decision"], [(event["kind"], event["completion_offset"]) for event in row["events"]]) for row in rows]
        status = "invalid_cases" if "invalid" in decisions else "uncertain_cases" if "uncertain" in decisions else (
            "pending_cases" if len(rows) < 2 else "disagreement_cases" if signatures[0] != signatures[1] else "certain_cases")
        consensus[status] += 1
        if status == "certain_cases":
            provenance = "human_supported_cases" if any(row["reviewer_role"] == "human" for row in rows) else "agent_only_cases"
            consensus[provenance] += 1
            case = queue["sealed"]["cases"][case_id]
            matching = _matching(case, rows[0]["events"])
            for stratum in case["memberships"]:
                for kind in _KINDS:
                    metrics[stratum][kind]["certain_cases"] += 1
                    for key, value in matching[kind].items():
                        if isinstance(value, list):
                            metrics[stratum][kind][key].extend(value)
                        else:
                            metrics[stratum][kind][key] += value
    for stratum in metrics.values():
        for row in stratum.values():
            row["prediction_match_fraction"] = row["matched_events"] / row["predicted_events"] if row["predicted_events"] else None
            row["label_match_fraction"] = row["matched_events"] / row["labeled_events"] if row["labeled_events"] else None
    return {
        "study_id": queue["study_id"], "queue_hash": queue["queue_hash"], "phase": "calibration",
        "holdout_locked": True, "status": "pilot_annotation", "trading_approval": False,
        "coverage": {"open_cards": len(queue["cards"]), "by_reviewer": coverage},
        "consensus": consensus,
        "recognition_agreement": metrics,
        "stratum_overlap_cases": sum(len(queue["sealed"]["cases"][key]["memberships"]) > 1 for key in queue["order"]),
        "limitations": ["Coordinator-private calibration pilot; holdout is locked.",
                        "Agent labels are not Gary's truth; no investment efficacy is evaluated.",
                        "Random/enriched strata can overlap and are not an accuracy estimate."]}


def _matching(case, labels):
    offsets = {day: index - 179 for index, day in enumerate(case["visible_dates"])}
    result = {}
    for kind in _KINDS:
        predictions = sorted([event for event in case["predictions"] if event["kind"] == kind], key=lambda event: event["completion_date"])
        observed = [event for event in labels if event["kind"] == kind]
        used, errors, delays = set(), [], []
        for label in observed:
            for index, prediction in enumerate(predictions):
                error = offsets[prediction["completion_date"]] - label["completion_offset"]
                delay = offsets[prediction["available_at"]] - label["completion_offset"]
                if index not in used and abs(error) <= 3 and delay >= 0:
                    used.add(index)
                    errors.append(error)
                    delays.append(delay)
                    break
        result[kind] = {"predicted_events": len(predictions), "labeled_events": len(observed),
                        "matched_events": len(used), "unmatched_prediction_events": len(predictions) - len(used),
                        "unmatched_label_events": len(observed) - len(used),
                        "signed_completion_errors_sessions": errors, "availability_delays_sessions": delays}
    return result
