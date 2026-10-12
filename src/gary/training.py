"""Pure single-human training rounds; retained-source authentication is adapter-owned."""

from copy import deepcopy
from datetime import date, datetime, time
from random import Random
import re
from zoneinfo import ZoneInfo

from gary.context_review import _anniversary, _bars, _complete_window, _overview, _source_metadata
from gary.patterns import detect_patterns
from gary.review import _card, _hash, _label
from gary.training_analysis import analyze_training_pass

_PROFILE = "training-five-year-v1"
_DETECTOR = dict(version="causal-geometry-v1",
                 parameter_hash="d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae",
                 source_file_sha256="76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a")
_MATCH = dict(target_sessions=20, match_tolerance_sessions=3, minimum_availability_delay_sessions=0,
              match="same_kind_earliest_unused_within_three_sessions_never_early_availability")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _config(config):
    required = {"profile", "reviewer_id", "random_seed", "shuffle_seed", "id_salt", "detector_manifest"}
    if (not isinstance(config, dict) or set(config) - {"exposure"} != required
            or config["profile"] != _PROFILE
            or any(not _text(config[field]) or len(config[field]) > 512 for field in ("reviewer_id", "id_salt"))
            or any(type(config[field]) is not int for field in ("random_seed", "shuffle_seed"))
            or config["detector_manifest"] != _DETECTOR):
        raise ValueError("training config differs from frozen profile, identity or v1 manifest")
    return deepcopy(config)


def _exposure(ledger):
    if (not isinstance(ledger, dict) or ledger.get("schema_version") != "training-exposure-v1"
            or ledger.get("complete") is not True or not isinstance(ledger.get("evidence"), list)
            or not ledger["evidence"] or any(not isinstance(row, dict) or not _text(row.get("path"))
                                            or not _digest(row.get("received_sha256")) for row in ledger["evidence"])
            or not isinstance(ledger.get("aliases"), dict)
            or any(not _text(alias) or not _text(identity) for alias, identity in ledger["aliases"].items())
            or any(identity in ledger["aliases"] and ledger["aliases"][identity] != identity
                   for identity in ledger["aliases"].values())
            or any(not isinstance(ledger.get(field), list) for field in ("targets", "views", "reservations"))):
        raise ValueError("missing or incomplete legacy exposure evidence")
    for field in ("targets", "views", "reservations"):
        for row in ledger[field]:
            if (not isinstance(row, dict) or not _text(row.get("canonical_id"))
                    or not _text(row.get("provenance"))
                    or any(not isinstance(row.get(edge), str) or date.fromisoformat(row[edge]).isoformat() != row[edge]
                           for edge in ("start", "end")) or row["start"] > row["end"]
                    or field == "targets" and not _digest(row.get("case_fingerprint"))
                    or field == "reservations" and type(row.get("active")) is not bool):
                raise ValueError("incomplete legacy interval evidence")
            _identity(ledger, row["canonical_id"])
    return ledger


def _identity(ledger, identity):
    if identity in ledger["aliases"]:
        return ledger["aliases"][identity]
    if identity in set(ledger["aliases"].values()):
        return identity
    raise ValueError("unknown legacy canonical lineage")


def _overlap(start, end, row):
    return start <= row["end"] and row["start"] <= end


def _source(source, ledger):
    _source_metadata(source)
    if not _text(source.get("canonical_id")):
        raise ValueError("missing canonical issuer")
    aliases = source.get("aliases")
    if (not isinstance(aliases, list) or not aliases or any(not _text(alias) for alias in aliases)
            or len(set(aliases)) != len(aliases) or not {source["source_id"], source["symbol"]} <= set(aliases)
            or any(ledger["aliases"].get(alias) != source["canonical_id"] for alias in aliases)):
        raise ValueError("missing or conflicting alias evidence")
    lineage = source.get("alias_evidence")
    if (not isinstance(lineage, dict) or lineage.get("reviewed") is not True
            or not _digest(lineage.get("receipt_sha256")) or not _text(lineage.get("provenance"))):
        raise ValueError("missing reviewed alias lineage")
    classification = source.get("classification")
    if (not isinstance(classification, dict) or classification.get("reviewed") is not True
            or classification.get("security_type") != "operating_common"
            or classification.get("exchange") not in {"NASDAQ", "NYSE", "NYSE_AMERICAN", "NYSE_ARCA", "CBOE_BZX"}
            or not _digest(classification.get("evidence_sha256")) or not _text(classification.get("provenance"))):
        raise ValueError("missing reviewed operating-common classification")
    _bars(source["bars"])
    cutoffs = source.get("cutoffs")
    dates = {bar["date"] for bar in source["bars"]}
    fetched = datetime.fromisoformat(source["fetched_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(source["exchange_timezone"]))
    fetched_day = fetched.date().isoformat()
    if (not isinstance(cutoffs, list) or not cutoffs or any(not isinstance(day, str) for day in cutoffs)
            or sorted(set(cutoffs)) != cutoffs
            or any(date.fromisoformat(day).isoformat() != day or day not in dates or day > fetched_day
                   or day == fetched_day and fetched.time() < time(16) for day in cutoffs)):
        raise ValueError("explicit ordered unique completed cutoffs required")


def build_review_queue(series: list[dict], config: dict) -> dict:
    """Commit a bounded anonymous batch with exact180 reference and full5y view."""
    config = _config(config)
    candidates, cards, cases, exclusions, sources, admission = [], {}, {}, [], [], []
    receipts = {}
    if not isinstance(series, list):
        admission.append(dict(source_id=None, reason="source series must be a list"))
        series = []
    if any(not isinstance(item, dict) for item in series):
        admission.append(dict(source_id=None, reason="source rows must be objects"))
        series = [item for item in series if isinstance(item, dict)]
    try:
        ledger = _exposure(config.get("exposure"))
    except ValueError as error:
        ledger = None
        exclusions.append(dict(reason=str(error)))
    for source in sorted(series, key=lambda item: str(item.get("source_id", ""))):
        if ledger is None:
            continue
        if sum(item.get("source_id") == source.get("source_id") for item in series) > 1:
            admission.append(dict(source_id=source.get("source_id"), reason="duplicate source identifier"))
            continue
        try:
            _source(source, ledger)
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as error:
            admission.append(dict(source_id=source.get("source_id"), reason=str(error)))
            continue
        sources.append(deepcopy(source))
        receipt = dict(source_sha256=source["source_sha256"], source_payload_hash=_hash(source),
                       input_bars_hash=_hash(source["bars"]), classification_hash=_hash(source["classification"]),
                       alias_evidence_hash=_hash(source["alias_evidence"]))
        receipts[source["source_id"]] = receipt
        for cutoff in source["cutoffs"]:
            requested = _anniversary(date.fromisoformat(cutoff)).isoformat()
            full = deepcopy([bar for bar in source["bars"] if requested < bar["date"] <= cutoff])
            window = full[-180:]
            try:
                _complete_window(full, requested, dict(as_of=cutoff, raw_window=window))
                if any(requested < split <= cutoff for split in source["split_dates"]):
                    raise ValueError("reported split in full five-year view")
            except (IndexError, ValueError) as error:
                exclusions.append(dict(source_id=source["source_id"], as_of=cutoff, reason=str(error)))
                continue
            dates = [bar["date"] for bar in window]
            fingerprint = _hash(dict(canonical_id=source["canonical_id"], as_of=cutoff, window_hash=_hash(window)))
            target_start = dates[-20]
            prior_targets = [row for row in ledger["targets"]
                             if _identity(ledger, row["canonical_id"]) == source["canonical_id"]]
            if any(_overlap(target_start, cutoff, row) or row["case_fingerprint"] in {fingerprint, _hash(window), _hash(full)}
                   for row in prior_targets):
                exclusions.append(dict(source_id=source["source_id"], as_of=cutoff, reason="previously exposed target or exact window"))
                continue
            if any(row["active"] and (_identity(ledger, row["canonical_id"]) == source["canonical_id"]
                                      or _overlap(full[0]["date"], cutoff, row)) for row in ledger["reservations"]):
                exclusions.append(dict(source_id=source["source_id"], as_of=cutoff, reason="active future-validation reservation"))
                continue
            key = _hash([config["id_salt"], source["canonical_id"], cutoff, _hash(window)])[:16]
            predictions = [event for event in detect_patterns(window, cutoff)
                           if dates[-20] <= event["completion_date"] <= cutoff
                           and dates[-20] <= event["available_at"] <= cutoff]
            candidates.append((key, dict(source_id=source["source_id"], symbol=source["symbol"],
                                         canonical_id=source["canonical_id"], as_of=cutoff,
                                         source_receipt=deepcopy(receipt),
                                         case_fingerprint=fingerprint, target_start=target_start, target_end=cutoff,
                                         prior_view_overlap=deepcopy([row for row in ledger["views"]
                                             if _identity(ledger, row["canonical_id"]) == source["canonical_id"]
                                             and _overlap(full[0]["date"], cutoff, row)]), development_only=True,
                                         requested_start=requested, raw_window=window, raw_context=full,
                                         visible_dates=dates, window_hash=_hash(window), context_hash=_hash(full),
                                         predictions=predictions, memberships=[])))
    if not sources:
        exclusions.append(dict(reason="no admitted retained sources"))
    unique = {}
    for key, case in candidates:
        if key in unique:
            exclusions.append(dict(source_id=case["source_id"], as_of=case["as_of"], reason="duplicate canonical window"))
        else:
            unique[key] = case
    candidates = list(unique.items())
    enriched = [(key, case) for key, case in candidates if case["predictions"]]
    selected, selections = {}, {}
    for name, frame in (("random", candidates), ("enriched", enriched)):
        keys = set()
        for key, case in Random(config["random_seed"]).sample(frame, len(frame)):
            if len(keys) == 6:
                break
            if key not in selected and any(case["canonical_id"] == other["canonical_id"]
                    and _overlap(case["target_start"], case["target_end"], dict(start=other["target_start"], end=other["target_end"]))
                    for other in selected.values()):
                exclusion = dict(source_id=case["source_id"], as_of=case["as_of"], reason="overlapping target in this batch")
                if exclusion not in exclusions:
                    exclusions.append(exclusion)
                continue
            selected[key] = case
            keys.add(key)
        selections[name] = keys
    random_keys, enriched_keys = selections["random"], selections["enriched"]
    frames = {name: dict(size=len(frame), candidates=[dict(case_id=key, canonical_id=case["canonical_id"],
                                                         source_id=case["source_id"], as_of=case["as_of"],
                                                         case_fingerprint=case["case_fingerprint"])
                                                     for key, case in frame])
              for name, frame in (("random", candidates), ("enriched", enriched))}
    for key, case in candidates:
        case["memberships"] = [name for name, keys in (("random", random_keys), ("enriched", enriched_keys)) if key in keys]
        if case["memberships"]:
            cases[key] = case
            cards[key] = _card(key, case["raw_window"]) | {"overview": _overview(key, case["raw_context"], [])}
    reference = dict(schema_version="training-round-reference-v1", protocol=deepcopy(_MATCH),
                     detector_manifest=deepcopy(_DETECTOR), context_sessions=180, visual_context_years=5,
                     prediction_hash=_hash({key: case["predictions"] for key, case in cases.items()}),
                     inputs_hash=_hash({key: _hash(case["raw_window"]) for key, case in cases.items()}))
    reference["commitment_hash"] = _hash(reference)
    order = list(cards)
    Random(config["shuffle_seed"]).shuffle(order)
    exclusions = sorted([*admission, *exclusions], key=_hash)
    queue = dict(schema_version="pattern-training-review-v1", study_id=_hash([config, sources, exclusions])[:24],
                 order=order, cards=cards,
                 sealed=dict(config=deepcopy(config), sources=sources, source_receipts=receipts, cases=cases,
                             detector_manifest=deepcopy(_DETECTOR), reference=reference, exclusions=exclusions,
                             sampling_frames=frames, admission_exclusions=admission))
    queue["queue_hash"] = _hash(queue)
    return queue


def record_review_label(queue: dict, labels: dict, entry: dict) -> dict:
    """Append a sole-human observation with queue-generated provenance."""
    if (not isinstance(queue, dict) or not _digest(queue.get("queue_hash")) or not isinstance(entry, dict)
            or entry.get("view_token") != queue["queue_hash"]):
        raise ValueError("training label requires the exact current view token")
    if set(entry) != {"case_id", "reviewer_id", "decision", "rationale", "events", "expected_revision", "revise", "view_token"}:
        raise ValueError("training label fields invalid; stamps are server-generated")
    if type(entry.get("expected_revision")) is not int or entry["expected_revision"] < 0 or type(entry.get("revise")) is not bool:
        raise ValueError("invalid revision controls")
    latest = _history(queue, labels)
    row = _observation(queue, entry)
    previous = latest.get(row["case_id"])
    if previous and all(previous.get(field) == value for field, value in row.items()):
        return deepcopy(labels)
    row.update(revision=1, supersedes_revision=None)
    if previous:
        if entry["revise"] is not True or entry["expected_revision"] != previous["revision"]:
            raise ValueError("conflicting label requires explicit current revision")
        row.update(revision=previous["revision"] + 1, supersedes_revision=previous["revision"])
    elif entry["revise"] is not False or entry["expected_revision"] != 0:
        raise ValueError("first label requires revision zero")
    return {**deepcopy(labels), "entries": [*deepcopy(labels["entries"]), row]}


def _observation(queue, entry):
    reviewer = queue["sealed"]["config"]["reviewer_id"]
    adapted = dict(cards=queue["cards"], sealed=dict(cases=queue["sealed"]["cases"],
                   config=dict(reviewers={reviewer: dict(role="human")})))
    row = _label(adapted, entry)
    return row | dict(view_protocol=_PROFILE, view_token=queue["queue_hash"],
                      overview_hash=_hash(queue["cards"][row["case_id"]]["overview"]),
                      reference_hash=queue["sealed"]["reference"]["commitment_hash"],
                      detector_version=_DETECTOR["version"], reference_detector_input_sessions=180)


def _history(queue, labels):
    try:
        _validate_queue(queue)
        if (not isinstance(labels, dict) or set(labels) != {"study_id", "queue_hash", "entries"}
                or labels["study_id"] != queue["study_id"] or labels["queue_hash"] != queue["queue_hash"]
                or not isinstance(labels["entries"], list)):
            raise ValueError("training label study or fields mismatch")
        latest = {}
        for row in labels["entries"]:
            entry = {field: row[field] for field in ("case_id", "reviewer_id", "decision", "rationale")}
            entry["events"] = [{field: event[field] for field in ("kind", "completion_offset")} for event in row["events"]]
            expected = _observation(queue, entry)
            previous = latest.get(row["case_id"])
            expected.update(revision=previous["revision"] + 1 if previous else 1,
                            supersedes_revision=previous["revision"] if previous else None)
            if _hash(row) != _hash(expected):
                raise ValueError("training history revision or generated provenance invalid")
            latest[row["case_id"]] = deepcopy(row)
        return latest
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"training label integrity invalid: {error}") from error


def _validate_queue(queue):
    try:
        expected = build_review_queue(queue["sealed"]["sources"], queue["sealed"]["config"])
        admission = queue["sealed"]["admission_exclusions"]
        if (not isinstance(admission, list) or any(not isinstance(row, dict) or set(row) != {"source_id", "reason"}
                                                  or not _text(row["reason"]) for row in admission)):
            raise ValueError("training source admission evidence invalid")
        expected["sealed"]["admission_exclusions"] = deepcopy(admission)
        expected["sealed"]["exclusions"] = sorted([*admission, *expected["sealed"]["exclusions"]], key=_hash)
        expected["study_id"] = _hash([expected["sealed"]["config"], expected["sealed"]["sources"], expected["sealed"]["exclusions"]])[:24]
        expected["queue_hash"] = _hash({key: value for key, value in expected.items() if key != "queue_hash"})
        if _hash(queue) != _hash(expected):
            raise ValueError("training queue does not reconstruct from source inputs and frozen protocol")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"training queue integrity invalid: {error}") from error


def summarize_review(queue: dict, labels: dict) -> dict:
    """Expose progress; seal personal diagnostics only for a complete human pass."""
    latest = _history(queue, labels)
    total, labeled = len(queue["order"]), len(latest)
    result = dict(status="labeling" if labeled else "ready", progress=dict(total=total, labeled=labeled, unreviewed=total - labeled),
                own_labels=latest, completed_pass=None, pass_hash=None, diagnostic=None, snapshots=[])
    if total and labeled == total:
        seen = set()
        for index, row in enumerate(labels["entries"]):
            seen.add(row["case_id"])
            if len(seen) == total:
                completed = {**deepcopy(labels), "entries": deepcopy(labels["entries"][:index + 1])}
                report = analyze_training_pass(queue, completed, dict(kind="training_round", commitment=queue["sealed"]["reference"]))
                result["snapshots"].append(dict(pass_hash=_hash(completed), completed_pass=completed, diagnostic=report,
                    supersedes_pass_hash=result["snapshots"][-1]["pass_hash"] if result["snapshots"] else None))
        snapshot = result["snapshots"][-1]
        result.update(status="complete", completed_pass=deepcopy(snapshot["completed_pass"]),
                      pass_hash=snapshot["pass_hash"], diagnostic=deepcopy(snapshot["diagnostic"]))
    return result


def _allocate_exposure(ledger, round_record):
    result = deepcopy(ledger)
    queue = round_record["queue"]
    provenance = f"training-round:{round_record['round_id']}:{queue['queue_hash']}"
    for key in queue["order"]:
        case = queue["sealed"]["cases"][key]
        result["targets"].append(dict(canonical_id=case["canonical_id"], start=case["target_start"], end=case["target_end"],
                                      case_fingerprint=case["case_fingerprint"], provenance=provenance))
        result["views"].append(dict(canonical_id=case["canonical_id"], start=case["raw_context"][0]["date"],
                                    end=case["as_of"], provenance=provenance))
    return result


def _request(request):
    if (not isinstance(request, dict) or set(request) != {"request_id", "config"}
            or not _text(request["request_id"]) or len(request["request_id"]) > 512):
        raise ValueError("training request id or fields invalid")
    _config(request["config"])


def _validate_history(history):
    try:
        if (not isinstance(history, dict) or set(history) != {"schema_version", "exposure", "rounds", "requests"}
                or history["schema_version"] != "training-history-v1" or not isinstance(history["rounds"], list)
                or not isinstance(history["requests"], dict)):
            raise ValueError("training history fields invalid")
        requests = history["requests"]
        round_ids = [row["round_id"] for row in history["rounds"]]
        if len(set(round_ids)) != len(round_ids):
            raise ValueError("duplicate training rounds")
        for key, row in requests.items():
            if not isinstance(row, dict) or set(row) != {"payload_hash", "round_id", "outcome", "request", "exclusions"}:
                raise ValueError("training request receipt fields invalid")
            _request(row["request"])
            if (row["request"]["request_id"] != key or row["payload_hash"] != _hash(row["request"])
                    or row["outcome"] not in {"created", "resumed", "needs_data"}
                    or not isinstance(row["exclusions"], list)
                    or (row["outcome"] == "needs_data") != (row["round_id"] is None)
                    or row["round_id"] is not None and row["round_id"] not in round_ids):
                raise ValueError("training request receipt integrity invalid")
        if not history["rounds"]:
            return
        ledger = deepcopy(history["rounds"][0]["queue"]["sealed"]["config"]["exposure"])
        _exposure(ledger)
        for index, row in enumerate(history["rounds"]):
            if not isinstance(row, dict) or set(row) != {"round_id", "status", "queue", "labels", "snapshots", "allocation"}:
                raise ValueError("training round fields invalid")
            creators = [item["request"] for item in requests.values()
                        if item["round_id"] == row["round_id"] and item["outcome"] == "created"]
            if len(creators) != 1:
                raise ValueError("training round lacks exactly one creating request")
            creating = creators[0]
            allocation = row["allocation"]
            catalog = allocation["catalog"]
            if (set(allocation) != {"catalog", "catalog_hash", "sources_hash", "exposure_hash"}
                    or catalog["schema_version"] != "training-catalog-v1"
                    or set(catalog) != {"schema_version", "sources", "exposure"}
                    or allocation["catalog_hash"] != _hash(catalog)
                    or allocation["sources_hash"] != _hash(catalog["sources"])
                    or allocation["exposure_hash"] != _hash(ledger) or _hash(catalog["exposure"]) != _hash(ledger)):
                raise ValueError("training catalog or exposure allocation commitment invalid")
            expected = build_review_queue(catalog["sources"], creating["config"] | {"exposure": ledger})
            if (not expected["order"] or _hash(row["queue"]) != _hash(expected)
                    or row["round_id"] != _hash([creating["request_id"], expected["queue_hash"]])[:24]):
                raise ValueError("training round allocation does not reconstruct")
            summary = summarize_review(row["queue"], row["labels"])
            if (row["status"] != summary["status"] or _hash(row["snapshots"]) != _hash(summary["snapshots"])
                    or index < len(history["rounds"]) - 1 and row["status"] != "complete"):
                raise ValueError("training status, completed snapshots or one-active-round integrity invalid")
            ledger = _allocate_exposure(ledger, row)
        if _hash(ledger) != _hash(history["exposure"]):
            raise ValueError("training exposure does not reconstruct from allocated rounds")
        by_id = {row["round_id"]: row for row in history["rounds"]}
        if any(item["round_id"] is not None and _hash(item["exclusions"]) != _hash(by_id[item["round_id"]]["queue"]["sealed"]["exclusions"])
               for item in requests.values()):
            raise ValueError("training request exclusions differ from its round commitment")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"training durable history integrity invalid: {error}") from error


def request_training_round(catalog: dict, history: dict, request: dict) -> dict:
    """Create or resume one pure round; the adapter persists the entire transition."""
    _request(request)
    _validate_history(history)
    if (not isinstance(catalog, dict) or catalog.get("schema_version") != "training-catalog-v1"
            or set(catalog) - {"sources", "exposure"} != {"schema_version"}):
        raise ValueError("training catalog schema or fields invalid")
    result = deepcopy(history)
    request_id = request["request_id"]
    prior = result["requests"].get(request_id)
    if prior and prior["payload_hash"] != _hash(request):
        raise ValueError("conflicting reuse of training request id")
    active = next((row for row in result["rounds"] if row["status"] in {"ready", "labeling"}), None)
    if prior:
        round_record = next((row for row in result["rounds"] if row["round_id"] == prior["round_id"]), None)
        status = prior["outcome"]
        exclusions = prior["exclusions"]
    elif active:
        round_record, status = active, "resumed"
        exclusions = active["queue"]["sealed"]["exclusions"]
    else:
        try:
            _exposure(catalog.get("exposure"))
            _exposure(result.get("exposure"))
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            queue, exclusions = None, [dict(reason=str(error))]
        else:
            if _hash(catalog["exposure"]) != _hash(result["exposure"]):
                raise ValueError("catalog exposure differs from authoritative history exposure")
            if "exposure" in request["config"] and _hash(request["config"]["exposure"]) != _hash(result["exposure"]):
                raise ValueError("request exposure differs from authoritative history exposure")
            queue = build_review_queue(catalog.get("sources"), request["config"] | {"exposure": catalog["exposure"]})
            exclusions = queue["sealed"]["exclusions"]
        round_record, status = None, "needs_data"
        if queue is not None and queue["order"]:
            round_id = _hash([request_id, queue["queue_hash"]])[:24]
            round_record = dict(round_id=round_id, status="ready", queue=queue,
                                labels=dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[]), snapshots=[],
                                allocation=dict(catalog=deepcopy(catalog), catalog_hash=_hash(catalog),
                                                sources_hash=_hash(catalog["sources"]), exposure_hash=_hash(catalog["exposure"])))
            result["rounds"].append(round_record)
            result["exposure"] = _allocate_exposure(result["exposure"], round_record)
            status = "created"
        elif not exclusions:
            exclusions = [dict(reason="no admitted distinct training targets")]
    round_id = round_record["round_id"] if round_record else None
    result["requests"][request_id] = dict(payload_hash=_hash(request), round_id=round_id, outcome=status,
                                          request=deepcopy(request), exclusions=deepcopy(exclusions))
    return dict(status=status, round_id=round_id, round=deepcopy(round_record), history=result, exclusions=deepcopy(exclusions))
