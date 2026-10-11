"""Experimental daily-chart recognition from explicit, as-of bar inputs."""

from datetime import date
from hashlib import sha256
import json
from math import isclose, isfinite
from statistics import median

_PARAMETERS = {
    "pivot_left": 3, "pivot_right": 3, "pivot_field": "close", "plateaus": "strict_no_pivot",
    "breakout_buffer": 0.005, "geometry_relative_tolerance": 1e-12,
    "prior_trend_sessions": 20, "hs_duration_min": 20, "hs_duration_max": 126,
    "shoulder_difference_depth_max": 0.25, "head_separation_depth_min": 0.1,
    "hs_time_ratio_min": 0.5, "hs_time_ratio_max": 2,
    "neckline_change_depth_max": 0.25, "hs_expiry_sessions": 30,
    "cup_duration_min": 20, "cup_duration_max": 126,
    "cup_depth_price_min": 0.05, "cup_depth_price_max": 0.4,
    "rim_difference_depth_max": 0.1,
    "cup_bottom_time_min": 1 / 3, "cup_bottom_time_max": 2 / 3,
    "rounded_bottom_sessions_min": 5, "rounded_bottom_depth_band": 0.2,
    "handle_sessions_min": 5, "handle_sessions_max": 20,
    "handle_retracement_depth_max": 1 / 3, "volume_context_sessions": 20,
}
_VERSION = "causal-geometry-v1"
_PARAMETER_HASH = sha256(json.dumps(_PARAMETERS, sort_keys=True).encode()).hexdigest()


def _within(value, lower, upper):
    """Inclusive ratio limits with only floating-point boundary tolerance."""
    tolerance = _PARAMETERS["geometry_relative_tolerance"]
    return (value >= lower or isclose(value, lower, rel_tol=tolerance, abs_tol=0)) and (
        value <= upper or isclose(value, upper, rel_tol=tolerance, abs_tol=0)
    )


def _prefix(bars, as_of):
    if not isinstance(bars, list):
        raise ValueError("bars must be a list")
    try:
        cutoff = date.fromisoformat(as_of)
    except (TypeError, ValueError) as error:
        raise ValueError("as_of must be an ISO date") from error
    result = []
    for bar in bars:
        try:
            bar_date = date.fromisoformat(bar["date"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("bar date must be an ISO date") from error
        if bar_date > cutoff:
            continue
        if result and bar_date <= date.fromisoformat(result[-1]["date"]):
            raise ValueError("permitted bar dates must be increasing and unique")
        values = []
        for key in ("open", "high", "low", "close", "volume"):
            value = bar.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("OHLCV must be finite numbers")
            values.append(value)
        opening, high, low, close, volume = values
        if low <= 0 or not low <= opening <= high or not low <= close <= high or volume < 0:
            raise ValueError("OHLCV relationships are invalid")
        result.append(bar)
    return result


def _confirmed_pivot(bars, session):
    index = session - 3
    if index < 3:
        return None
    value = bars[index]["close"]
    neighbors = [bars[i]["close"] for i in range(index - 3, index + 4) if i != index]
    orientation = "high" if all(value > item for item in neighbors) else (
        "low" if all(value < item for item in neighbors) else None
    )
    if orientation is None:
        return None
    return {"index": index, "price": value, "orientation": orientation,
            "date": bars[index]["date"], "confirmed_on": bars[session]["date"]}


def _head_shoulders(pivots, bars):
    if len(pivots) != 5:
        return None
    orientation = [p["orientation"] for p in pivots]
    if orientation == ["low", "high", "low", "high", "low"]:
        polarity, kind, direction = 1, "inverse_head_shoulders", "buy"
    elif orientation == ["high", "low", "high", "low", "high"]:
        polarity, kind, direction = -1, "head_shoulders_top", "sell"
    else:
        return None
    left, first_neck, head, second_neck, right = pivots
    duration = right["index"] - left["index"]
    if not _PARAMETERS["hs_duration_min"] <= duration <= _PARAMETERS["hs_duration_max"]:
        return None
    if left["index"] < 20:
        return None
    prior_return = left["price"] / bars[left["index"] - 20]["close"] - 1
    if polarity * prior_return >= 0:
        return None
    if any(polarity * (shoulder["price"] - head["price"]) <= 0 for shoulder in (left, right)):
        return None
    slope = (second_neck["price"] - first_neck["price"]) / (second_neck["index"] - first_neck["index"])
    origin = first_neck["price"] - slope * first_neck["index"]
    depth = polarity * (origin + slope * head["index"] - head["price"])
    if depth <= 0:
        return None
    shoulder_difference = abs(left["price"] - right["price"]) / depth
    if not _within(shoulder_difference, 0, 0.25):
        return None
    head_separation = min(polarity * (shoulder["price"] - head["price"]) / depth for shoulder in (left, right))
    if not _within(head_separation, 0.1, float("inf")):
        return None
    time_ratio = (head["index"] - left["index"]) / (right["index"] - head["index"])
    if not _within(time_ratio, 0.5, 2):
        return None
    neckline_change = abs(second_neck["price"] - first_neck["price"]) / depth
    if not _within(neckline_change, 0, 0.25):
        return None
    return {"kind": kind, "direction": direction, "polarity": polarity, "pivots": tuple(pivots),
            "slope": slope, "origin": origin,
            "checks": {"pattern_depth": depth, "duration_sessions": duration,
                       "prior_20_session_return": prior_return,
                       "head_separation_depth_ratio": head_separation,
                       "shoulder_difference_depth_ratio": shoulder_difference,
                       "shoulder_time_ratio": time_ratio,
                       "neckline_change_depth_ratio": neckline_change}}


def _event(candidate, bars, session, boundary):
    roles = candidate.get("roles", ("left_shoulder", "neckline_left", "head", "neckline_right", "right_shoulder"))
    return {
        "kind": candidate["kind"], "direction": candidate["direction"], "status": "completed",
        "completion_date": bars[session]["date"], "available_at": bars[session]["date"],
        "breakout_level": boundary,
        "pivots": [{"role": role, "date": pivot["date"], "price": pivot["price"],
                    "confirmed_on": pivot["confirmed_on"]}
                   for role, pivot in zip(roles, candidate["pivots"])],
        "checks": candidate["checks"], "detector_version": _VERSION,
        "parameter_hash": _PARAMETER_HASH,
        "window_start": candidate["pivots"][0]["date"], "window_end": bars[session]["date"],
    }


def _cup(pivots, bars):
    if len(pivots) != 3 or [p["orientation"] for p in pivots] != ["high", "low", "high"]:
        return None
    left, bottom, right = pivots
    if left["index"] < 20:
        return None
    prior_return = left["price"] / bars[left["index"] - 20]["close"] - 1
    if prior_return <= 0:
        return None
    depth = min(left["price"], right["price"]) - bottom["price"]
    depth_fraction = depth / min(left["price"], right["price"])
    if not _within(depth_fraction, 0.05, 0.4):
        return None
    rounded_sessions = sum(bar["close"] <= bottom["price"] + depth * 0.2
                           for bar in bars[left["index"]:right["index"] + 1])
    if rounded_sessions < 5:
        return None
    rim_difference = abs(left["price"] - right["price"]) / depth
    if not _within(rim_difference, 0, 0.1):
        return None
    duration = right["index"] - left["index"]
    bottom_location = (bottom["index"] - left["index"]) / duration
    if not 20 <= duration <= 126 or not _within(bottom_location, 1 / 3, 2 / 3):
        return None
    return {"kind": "cup_handle", "direction": "buy", "pivots": tuple(pivots),
            "checks": {"pattern_depth": depth, "prior_20_session_return": prior_return,
                       "cup_depth_price_fraction": depth_fraction,
                       "rounded_bottom_sessions": rounded_sessions,
                       "rim_difference_depth_ratio": rim_difference,
                       "duration_sessions": duration, "bottom_time_fraction": bottom_location}}


def _complete_cup(candidate, bars, session, confirmed_lows):
    left, bottom, right = candidate["pivots"]
    handle_sessions = session - right["index"] - 1
    if not 5 <= handle_sessions <= 20:
        return None
    handle = bars[right["index"] + 1:session]
    low = min((pivot for pivot in confirmed_lows if right["index"] < pivot["index"] < session),
              key=lambda item: item["price"], default=None)
    if low is None or low["price"] != min(bar["close"] for bar in handle):
        return None
    retracement = (right["price"] - low["price"]) / (right["price"] - bottom["price"])
    if retracement <= 0 or not _within(retracement, 0, 1 / 3):
        return None
    if bars[session - 1]["close"] <= low["price"]:
        return None
    boundary = max(left["price"], right["price"], *(bar["close"] for bar in handle))
    if bars[session]["close"] <= boundary * 1.005:
        return None
    previous_volume = median(bar["volume"] for bar in bars[session - 20:session])
    complete = {**candidate, "pivots": (*candidate["pivots"], low),
                "roles": ("left_rim", "cup_bottom", "right_rim", "handle_low"),
                "checks": {**candidate["checks"], "handle_sessions": handle_sessions,
                           "handle_retracement_depth_ratio": retracement,
                           "breakout_volume_ratio": bars[session]["volume"] / previous_volume if previous_volume else None}}
    return _event(complete, bars, session, boundary)


def detect_patterns(bars: list[dict], as_of: str) -> list[dict]:
    """Return completed pattern hypotheses and evidence through ``as_of``."""
    permitted = _prefix(bars, as_of)
    pivots, candidates, signals, confirmed_lows = [], {}, [], []
    seen = set()
    for session in range(len(permitted)):
        pivot = _confirmed_pivot(permitted, session)
        if pivot:
            if pivot["orientation"] == "low":
                confirmed_lows.append(pivot)
            if pivots and pivots[-1]["orientation"] == pivot["orientation"]:
                previous = pivots[-1]
                more_extreme = pivot["price"] > previous["price"] if pivot["orientation"] == "high" else pivot["price"] < previous["price"]
                if more_extreme:
                    pivots[-1] = pivot
            else:
                pivots.append(pivot)
            for candidate in (_head_shoulders(pivots[-5:], permitted), _cup(pivots[-3:], permitted)):
                if candidate:
                    key = (candidate["kind"], *(p["index"] for p in candidate["pivots"]))
                    if key not in seen:
                        seen.add(key)
                        candidates[key] = candidate
        for key, candidate in list(candidates.items()):
            if candidate["kind"] == "cup_handle":
                if session - candidate["pivots"][-1]["index"] - 1 > 20:
                    del candidates[key]
                    continue
                signal = _complete_cup(candidate, permitted, session, confirmed_lows)
                if signal:
                    signals.append(signal)
                    del candidates[key]
                continue
            if session - candidate["pivots"][-1]["index"] > 30:
                del candidates[key]
                continue
            polarity = candidate["polarity"]
            head = candidate["pivots"][2]
            if polarity * (permitted[session]["close"] - head["price"]) < 0:
                del candidates[key]
                continue
            boundary = candidate["origin"] + candidate["slope"] * session
            previous_boundary = candidate["origin"] + candidate["slope"] * (session - 1)
            multiplier = 1 + polarity * _PARAMETERS["breakout_buffer"]
            if session and polarity * (permitted[session]["close"] - boundary * multiplier) > 0 and polarity * (permitted[session - 1]["close"] - previous_boundary * multiplier) <= 0:
                signals.append(_event(candidate, permitted, session, boundary))
                del candidates[key]
    return signals
