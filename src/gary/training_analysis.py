"""Private deterministic single-human development diagnostics; no persistence."""

from copy import deepcopy
from datetime import date, datetime

from gary.context_review import _anniversary, _bars, _complete_window, _overview, _validate_queue, _view_history
from gary.evaluation import _trusted_detector, freeze_evaluation
from gary.patterns import detect_patterns
from gary.review import _KINDS, _card, _hash, _history, _label, _matching

_PROFILE = "training-five-year-v1"
_MATCH = dict(target_sessions=20, match_tolerance_sessions=3, minimum_availability_delay_sessions=0,
              match="same_kind_earliest_unused_within_three_sessions_never_early_availability")


def _training_reference(queue, reference):
    sealed = queue["sealed"]
    if (queue["schema_version"] != "pattern-training-review-v1"
            or sealed["config"]["profile"] != _PROFILE
            or not isinstance(queue["order"], list)
            or _hash({key: value for key, value in queue.items() if key != "queue_hash"}) != queue["queue_hash"]
            or len(queue["order"]) != len(set(queue["order"]))
            or set(queue["order"]) != set(queue["cards"]) or set(queue["cards"]) != set(sealed["cases"])):
        raise ValueError("training queue integrity invalid")
    trusted = _trusted_detector()
    if sealed["detector_manifest"] != trusted:
        raise ValueError("training detector differs from trusted frozen v1")
    for key, case in sealed["cases"].items():
        window, full = case["raw_window"], case["raw_context"]
        _bars(window)
        _bars(full)
        dates = [bar["date"] for bar in window]
        if (len(window) != 180 or dates != case["visible_dates"] or dates[-1] != case["as_of"]
                or _hash(window) != case["window_hash"] or _hash(full) != case["context_hash"]):
            raise ValueError("training raw180 or five-year context binding invalid")
        _complete_window(full, _anniversary(date.fromisoformat(case["as_of"])).isoformat(), case)
        predictions = [event for event in detect_patterns(window, dates[-1])
                       if dates[-20] <= event["completion_date"] <= dates[-1]
                       and dates[-20] <= event["available_at"] <= dates[-1]]
        if case["predictions"] != predictions:
            raise ValueError("training predictions do not reproduce from trusted raw180")
        card = _card(key, window) | {"overview": _overview(key, full, [])}
        if queue["cards"][key] != card:
            raise ValueError("training anonymous cards do not reproduce")
        memberships = case["memberships"]
        if (not isinstance(memberships, list) or not memberships or len(set(memberships)) != len(memberships)
                or not set(memberships) <= {"random", "enriched"}):
            raise ValueError("training sampling memberships invalid")
    expected = dict(schema_version="training-round-reference-v1", protocol=deepcopy(_MATCH),
                    detector_manifest=trusted, context_sessions=180, visual_context_years=5,
                    prediction_hash=_hash({key: case["predictions"] for key, case in sealed["cases"].items()}),
                    inputs_hash=_hash({key: _hash(case["raw_window"]) for key, case in sealed["cases"].items()}))
    expected["commitment_hash"] = _hash(expected)
    if sealed["reference"] != expected or reference != dict(kind="training_round", commitment=expected):
        raise ValueError("training reference commitment invalid")


def _training_history(queue, completed_pass):
    reviewer = queue["sealed"]["config"]["reviewer_id"]
    if not isinstance(reviewer, str) or not reviewer:
        raise ValueError("training requires an assigned human")
    if (completed_pass["study_id"] != queue["study_id"] or completed_pass["queue_hash"] != queue["queue_hash"]
            or not isinstance(completed_pass["entries"], list)):
        raise ValueError("training pass study or queue mismatch")
    adapted = dict(cards=queue["cards"], sealed=dict(config=dict(reviewers={reviewer: dict(role="human")}),
                                                  cases=queue["sealed"]["cases"]))
    latest = {}
    for row in completed_pass["entries"]:
        entry = {field: row[field] for field in ("case_id", "reviewer_id", "decision", "rationale")}
        entry["events"] = [{field: event[field] for field in ("kind", "completion_offset")} for event in row["events"]]
        normalized = _label(adapted, entry)
        previous = latest.get(row["case_id"])
        revision = previous["revision"] + 1 if previous else 1
        supersedes = previous["revision"] if previous else None
        stamps = dict(view_protocol=_PROFILE, view_token=queue["queue_hash"],
                      overview_hash=_hash(queue["cards"][row["case_id"]]["overview"]),
                      reference_hash=queue["sealed"]["reference"]["commitment_hash"],
                      detector_version=_trusted_detector()["version"], reference_detector_input_sessions=180)
        if (type(row["revision"]) is not int or row["revision"] != revision
                or type(row["reference_detector_input_sessions"]) is not int
                or row["supersedes_revision"] != supersedes
                or (supersedes is not None and type(row["supersedes_revision"]) is not int)
                or any(row.get(field) != value for field, value in (normalized | stamps).items())):
            raise ValueError("training history revision, observation or derived stamps invalid")
        latest[row["case_id"]] = row
    return latest


def _original_reference(queue, completed_pass, reference):
    if set(reference) - {"reveal_receipt"} != {"kind", "release", "parent_queue"}:
        raise ValueError("original reference fields invalid")
    release = reference["release"]
    expected = freeze_evaluation(reference["parent_queue"], release["calibration_labels"], release["candidate_version"])
    if release != expected:
        raise ValueError("original release does not reproduce against trusted parent and executables")
    context = _validate_queue(queue)
    if context["parent_queue"] != release["holdout_queue"] or context["parent_release_hash"] != release["release_hash"]:
        raise ValueError("assisted queue differs from original released parent")
    _view_history(context, completed_pass)
    if any(row["supersedes_revision"] is not None and type(row["supersedes_revision"]) is not int
           for row in completed_pass["entries"]):
        raise ValueError("original superseded revision must be an integer")
    rows = _history(queue, completed_pass)
    humans = [key for key, value in queue["sealed"]["config"]["reviewers"].items() if value["role"] == "human"]
    if len(humans) != 1 or any(row["reviewer_id"] != humans[0] for row in completed_pass["entries"]):
        raise ValueError("original diagnostic requires only the sole human pass")
    latest = {key: row for (key, identity), row in rows.items() if identity == humans[0]}
    receipt = reference.get("reveal_receipt")
    if receipt is None:
        return latest, dict(status="reveal_timing_unknown", locked_pass_hash=_hash(completed_pass),
                            revealed_at_utc=None, reveal_receipt_hash=None,
                            journal_prefix_commitment=None, independence_claim=False)
    when = datetime.fromisoformat(receipt["revealed_at_utc"].replace("Z", "+00:00"))
    if (receipt["schema_version"] != "completed-context-identity-reveal-v1"
            or receipt["queue_hash"] != queue["queue_hash"]
            or receipt["gary_pass_snapshot_sha256"] != _hash(completed_pass) or when.tzinfo is None
            or len(latest) != len(queue["order"])):
        raise ValueError("identity reveal receipt conflicts with locked human pass")
    charts = receipt["charts"]
    if (not isinstance(charts, list) or len(charts) != len(queue["order"])
            or any(type(row["chart"]) is not int or row["chart"] != index + 1
                   or row["ticker"] != queue["sealed"]["cases"][key]["symbol"]
                   or not isinstance(row["company"], str) or not row["company"]
                   for index, (row, key) in enumerate(zip(charts, queue["order"])))):
        raise ValueError("identity reveal chart ordering differs from locked queue")
    chronology = dict(status="locked_snapshot_before_identity_reveal", locked_pass_hash=_hash(completed_pass),
                      revealed_at_utc=receipt["revealed_at_utc"], reveal_receipt_hash=_hash(receipt),
                      journal_prefix_commitment=None, independence_claim=False)
    return latest, chronology


def _metrics():
    return {kind: dict(certain_cases=0, predicted_events=0, labeled_events=0, matched_events=0,
                       unmatched_prediction_events=0, unmatched_label_events=0,
                       signed_completion_errors_sessions=[], availability_delays_sessions=[],
                       prediction_match_fraction=None, label_match_fraction=None) for kind in _KINDS}


def _inventory(key, case, label):
    base = dict(case_id=key, memberships=deepcopy(case["memberships"]))
    if label["decision"] in ("uncertain", "invalid"):
        return [base | dict(category=label["decision"], scored=False)]
    offsets = {day: index - len(case["visible_dates"]) + 1 for index, day in enumerate(case["visible_dates"])}
    rows, different = [], False
    for kind in _KINDS:
        predictions = sorted([event for event in case["predictions"] if event["kind"] == kind],
                             key=lambda event: event["completion_date"])
        used = set()
        for observed in (event for event in label["events"] if event["kind"] == kind):
            for index, prediction in enumerate(predictions):
                error = offsets[prediction["completion_date"]] - observed["completion_offset"]
                delay = offsets[prediction["available_at"]] - observed["completion_offset"]
                if index not in used and abs(error) <= 3 and delay >= 0:
                    used.add(index)
                    rows.append(base | dict(category="matched", observation=deepcopy(observed),
                                            prediction=deepcopy(prediction), signed_completion_error_sessions=error,
                                            availability_delay_sessions=delay))
                    break
            else:
                rows.append(base | dict(category="unmatched_observation", observation=deepcopy(observed)))
                different = True
        for index, prediction in enumerate(predictions):
            if index not in used:
                rows.append(base | dict(category="unmatched_prediction", prediction=deepcopy(prediction)))
                different = True
    if different:
        rows.append(base | dict(category="context_policy_ambiguity", requirement_demonstrated=False,
                                reason="Five-year visual observation versus context180; disagreement alone establishes no rule defect."))
    return rows


def analyze_training_pass(queue: dict, completed_pass: dict, reference: dict) -> dict:
    """Compare a sole human's target20 observations with committed context180."""
    try:
        if reference["kind"] == "training_round":
            _training_reference(queue, reference)
            latest = _training_history(queue, completed_pass)
            chronology = dict(status="development_round", independence_claim=False)
        elif reference["kind"] == "original_release":
            latest, chronology = _original_reference(queue, completed_pass, reference)
        else:
            raise ValueError("unsupported analysis reference variant")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"training analysis integrity invalid: {error}") from error
    overall = _metrics()
    strata = {name: _metrics() for name in ("random", "enriched")}
    inventory = []
    for key in queue["order"]:
        if key not in latest:
            continue
        case, label = queue["sealed"]["cases"][key], latest[key]
        inventory.extend(_inventory(key, case, label))
        if label["decision"] in ("uncertain", "invalid"):
            continue
        matched = _matching(case, label["events"])
        for metrics in [overall, *(strata[name] for name in case["memberships"])]:
            for kind in _KINDS:
                metrics[kind]["certain_cases"] += 1
                for field, value in matched[kind].items():
                    if isinstance(value, list):
                        metrics[kind][field].extend(value)
                    else:
                        metrics[kind][field] += value
    for metrics in [overall, *strata.values()]:
        for row in metrics.values():
            row["prediction_match_fraction"] = row["matched_events"] / row["predicted_events"] if row["predicted_events"] else None
            row["label_match_fraction"] = row["matched_events"] / row["labeled_events"] if row["labeled_events"] else None
    complete = len(latest) == len(queue["order"])
    report = dict(schema_version="training-diagnostic-v1", mode="single_investor_diagnostic", status="complete" if complete else "pending",
                  queue_hash=queue["queue_hash"], pass_hash=_hash(completed_pass), reference_hash=_hash(reference),
                  reference_detector_input_sessions=180, visual_context_years=5,
                  chronology=chronology,
                  coverage=dict(total_cases=len(queue["order"]), labeled_cases=len(latest), unreviewed_cases=len(queue["order"]) - len(latest),
                                **{f"{decision}_cases": sum(row["decision"] == decision for row in latest.values())
                                   for decision in ("completed", "none", "uncertain", "invalid")}),
                  overall=overall if complete else None, by_stratum=strata if complete else None,
                  inventory=inventory if complete else None,
                  limitations=["Personal development diagnostic; no independent accuracy or investment-performance estimate.",
                               "Five-year visual observations differ from the frozen 180-session detector input.",
                               "Disagreement alone does not demonstrate a detector requirement."])
    report["report_hash"] = _hash(report)
    return deepcopy(report)
