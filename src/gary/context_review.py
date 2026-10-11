"""Five-year-assisted holdout observations around a preserved released queue.

The additional representation changes the review protocol, never the frozen
detector inputs. Persistence must also rebuild from the trusted release and raw
sources: an embedded snapshot alone is not an external authenticity anchor.
"""

from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
from math import isfinite
import re
from statistics import median
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gary import review

_PROTOCOL = "five-year-assisted-v1"


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _empty(queue):
    return dict(study_id=queue["study_id"], queue_hash=queue["queue_hash"], entries=[])


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _parent(config):
    try:
        if not isinstance(config, dict) or set(config) != {"profile", "parent_queue", "parent_release_hash"} or config["profile"] != _PROTOCOL:
            raise ValueError("context config fields or protocol invalid")
        if not _digest(config["parent_release_hash"]):
            raise ValueError("context parent release hash invalid")
        parent = config["parent_queue"]
        if parent["sealed"]["config"].get("profile") != "released-holdout-v1" or "context_review" in parent["sealed"]:
            raise ValueError("context requires original released holdout parent")
        review.summarize_review(parent, _empty(parent))
        return parent
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"context parent integrity invalid: {error}") from error


def _anniversary(cutoff):
    return cutoff.replace(year=cutoff.year - 5, day=28 if cutoff.month == 2 and cutoff.day == 29 else cutoff.day)


def _bars(bars):
    if not isinstance(bars, list) or not bars:
        raise ValueError("source bars must be a nonempty list")
    previous = None
    for bar in bars:
        day = bar["date"]
        if date.fromisoformat(day).isoformat() != day or previous is not None and day <= previous:
            raise ValueError("source dates must be canonical, ordered and unique")
        values = [bar[field] for field in ("open", "high", "low", "close", "volume")]
        if any(type(value) not in (int, float) or not isfinite(value) for value in values):
            raise ValueError("source OHLCV must be finite numbers")
        opening, high, low, close, volume = values
        if low <= 0 or not low <= opening <= high or not low <= close <= high or volume < 0:
            raise ValueError("source OHLCV relationships invalid")
        previous = day


def _source_metadata(item):
    required = {"source_id", "symbol", "source_sha256", "fetched_at", "exchange_timezone", "price_basis", "split_dates"}
    if not isinstance(item, dict) or not required <= set(item):
        raise ValueError("source provenance or split metadata missing")
    if any(not isinstance(item[field], str) or not item[field] for field in ("source_id", "symbol")):
        raise ValueError("source identity invalid")
    if not _digest(item["source_sha256"]) or item["price_basis"] != "provider_received_ohlc":
        raise ValueError("source hash or price basis invalid")
    if datetime.fromisoformat(item["fetched_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("source fetch time requires timezone")
    ZoneInfo(item["exchange_timezone"])
    if not isinstance(item["split_dates"], list) or any(date.fromisoformat(day).isoformat() != day for day in item["split_dates"]):
        raise ValueError("source split dates must be canonical")


def _sources(series, parent):
    try:
        if not isinstance(series, list) or not series:
            raise ValueError("source series must be a nonempty list")
        by_source = {}
        identities = {item["source_id"]: item["symbol"] for item in parent["sealed"]["sources"]}
        for item in series:
            _source_metadata(item)
            if item["source_id"] in by_source or identities.get(item["source_id"]) != item["symbol"]:
                raise ValueError("source identities must match parent uniquely")
            _bars(item["bars"])
            by_source[item["source_id"]] = item
        if set(by_source) != set(identities):
            raise ValueError("source identities differ from parent")
        return by_source
    except (AttributeError, KeyError, TypeError, ValueError, ZoneInfoNotFoundError, OverflowError) as error:
        raise ValueError(f"context source integrity invalid: {error}") from error


def _overview(key, window, splits):
    price_base = window[0]["close"]
    volume_base = median(bar["volume"] for bar in window)
    bars = [{"offset": index - len(window) + 1,
             **{field: bar[field] / price_base * 100 for field in ("open", "high", "low", "close")},
             "volume": bar["volume"] / volume_base if volume_base else None}
            for index, bar in enumerate(window)]
    requested = _anniversary(date.fromisoformat(window[-1]["date"])).isoformat()
    split_offsets = sorted({next(index - len(window) + 1 for index, bar in enumerate(window) if bar["date"] >= split)
                            for split in splits if requested < split <= window[-1]["date"]})
    return dict(case_id=key, bars=bars, target_start_offset=-19, target_end_offset=0,
                price_basis="normalized provider-received OHLC", volume_available=bool(volume_base),
                split_offsets=split_offsets)


def _complete_window(window, requested, original):
    if (len(window) < 1200 or window[-1]["date"] != original["as_of"]
            or not 0 < (date.fromisoformat(window[0]["date"]) - date.fromisoformat(requested)).days <= 7
            or any(not requested < bar["date"] <= original["as_of"] for bar in window)):
        raise ValueError("source lacks complete historical five-year context")
    if _hash(window[-180:]) != _hash(original["raw_window"]):
        raise ValueError("context final 180 sessions do not reconcile with original")


def build_review_queue(series: list[dict], config: dict) -> dict:
    """Bind historical five-year overviews to a validated released holdout."""
    parent = _parent(config)
    by_source = _sources(series, parent)
    contexts = {}
    for key, case in parent["sealed"]["cases"].items():
        item = by_source[case["source_id"]]
        requested = _anniversary(date.fromisoformat(case["as_of"])).isoformat()
        window = deepcopy([bar for bar in item["bars"] if requested < bar["date"] <= case["as_of"]])
        if item["bars"][0]["date"] >= requested:
            raise ValueError("source must span before the historical context anniversary")
        _complete_window(window, requested, case)
        contexts[key] = dict(raw_window=window, requested_start=requested, window_hash=_hash(window),
                             overview=_overview(key, window, item["split_dates"]))
    queue = deepcopy(parent)
    queue["sealed"]["context_review"] = dict(
        protocol=_PROTOCOL, parent_queue=deepcopy(parent), parent_release_hash=config["parent_release_hash"],
        sources=[{**{key: deepcopy(value) for key, value in item.items() if key != "bars"},
                  "input_bars_hash": _hash(item["bars"])} for item in sorted(series, key=lambda item: item["source_id"])],
        cases=contexts)
    queue["queue_hash"] = _hash({key: value for key, value in queue.items() if key != "queue_hash"})
    return queue


def _validate_queue(queue):
    try:
        if _hash({key: value for key, value in queue.items() if key != "queue_hash"}) != queue["queue_hash"]:
            raise ValueError("context queue hash integrity mismatch")
        context = queue["sealed"]["context_review"]
        if not isinstance(context, dict) or set(context) != {"protocol", "parent_queue", "parent_release_hash", "sources", "cases"}:
            raise ValueError("context metadata integrity mismatch")
        parent = _parent(dict(profile=context["protocol"], parent_queue=context["parent_queue"],
                              parent_release_hash=context["parent_release_hash"]))
        original = deepcopy(queue)
        del original["sealed"]["context_review"]
        original["queue_hash"] = parent["queue_hash"]
        if _hash(original) != _hash(parent):
            raise ValueError("context must preserve the exact released parent content")
        if not isinstance(context["sources"], list):
            raise ValueError("context source metadata invalid")
        identities = {item["source_id"]: item["symbol"] for item in parent["sealed"]["sources"]}
        sources = {}
        for item in context["sources"]:
            _source_metadata(item)
            if (item["source_id"] in sources or identities.get(item["source_id"]) != item["symbol"]
                    or not _digest(item["input_bars_hash"]) or "bars" in item):
                raise ValueError("context source metadata integrity mismatch")
            sources[item["source_id"]] = item
        if set(sources) != set(identities) or set(context["cases"]) != set(parent["sealed"]["cases"]):
            raise ValueError("context source or case partition integrity mismatch")
        for key, case in context["cases"].items():
            if not isinstance(case, dict) or set(case) != {"raw_window", "requested_start", "window_hash", "overview"}:
                raise ValueError("context case metadata integrity mismatch")
            original_case = parent["sealed"]["cases"][key]
            requested = _anniversary(date.fromisoformat(original_case["as_of"])).isoformat()
            window = case["raw_window"]
            _bars(window)
            _complete_window(window, requested, original_case)
            if case["requested_start"] != requested or case["window_hash"] != _hash(window):
                raise ValueError("context date or raw hash integrity mismatch")
            if _hash(case["overview"]) != _hash(_overview(key, window, sources[original_case["source_id"]]["split_dates"])):
                raise ValueError("context anonymous overview normalization integrity mismatch")
        return context
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZoneInfoNotFoundError, OverflowError) as error:
        raise ValueError(f"context integrity invalid: {error}") from error


def _view_history(context, labels):
    try:
        if not isinstance(labels["entries"], list):
            raise ValueError("context view history must be a list")
        for row in labels["entries"]:
            overview = context["cases"][row["case_id"]]["overview"]
            if row.get("view_protocol") != _PROTOCOL or row.get("overview_hash") != _hash(overview):
                raise ValueError("label view provenance does not match context overview")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"context view provenance invalid: {error}") from error


def record_review_label(queue: dict, labels: dict, entry: dict) -> dict:
    """Record the existing decision contract with queue-derived view provenance."""
    if not isinstance(entry, dict) or entry.get("view_token") != queue.get("queue_hash"):
        raise ValueError("context label requires the exact current view token")
    context = _validate_queue(queue)
    _view_history(context, labels)
    result = review.record_review_label(queue, labels, entry)
    for row in result["entries"][len(labels["entries"]):]:
        row.update(view_protocol=_PROTOCOL,
                   overview_hash=_hash(queue["sealed"]["context_review"]["cases"][row["case_id"]]["overview"]))
    return result


def summarize_review(queue: dict, labels: dict) -> dict:
    """Report this changed-view protocol with frozen 180-session reference inputs."""
    context = _validate_queue(queue)
    _view_history(context, labels)
    report = review.summarize_review(queue, labels)
    report.update(phase="holdout_context", view_protocol=_PROTOCOL,
                  original_holdout_comparable=False, reference_detector_input_sessions=180)
    report["limitations"][0] = "Coordinator-private five-year-assisted holdout; both context passes must complete before recognition reporting."
    report["limitations"].extend([
        "Additional history can overlap previously exposed calibration history and unblind historical review evidence.",
        "Context labels belong to a changed visual protocol and cannot be scored as original same-view holdout observations.",
        "Retrospective provider-received prices have unverified adjustment provenance; known split markers do not verify adjustment correctness.",
    ])
    return report
