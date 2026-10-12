"""Confirmed daily channel signals alongside the frozen v1 geometry."""

from decimal import Decimal
from hashlib import sha256
import json
from statistics import mean, median

from gary.patterns import _prefix, detect_patterns as detect_original


VERSION = "expanded-signals-v1"
_PARAMETERS = {
    "geometry_version": "causal-geometry-v1",
    "geometry_source_sha256": "76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a",
    "channel_sessions": 20,
    "breakout_multiplier": 1.005,
    "breakdown_multiplier": 0.995,
    "breakout_prior_sessions_min": 21,
    "rollover_prior_sessions_min": 51,
    "rollover_sma_sessions": 50,
    "gap_multiplier": 1.02,
    "gap_direction": "observation",
    "availability": "completed_session_close",
}
PARAMETER_HASH = sha256(json.dumps(_PARAMETERS, sort_keys=True).encode()).hexdigest()


def detect_patterns(bars: list[dict], as_of: str) -> list[dict]:
    """Return completed signals using only permitted daily bars through ``as_of``."""
    permitted = _prefix(bars, as_of)
    signals = [{**event, "detector_version": VERSION, "parameter_hash": PARAMETER_HASH}
               for event in detect_original(permitted, as_of)]
    for session in range(21, len(permitted)):
        window = permitted[session - 20:session]
        reference = max(window, key=lambda bar: bar["high"])
        threshold = Decimal(str(reference["high"])) * Decimal("1.005")
        previous_level = max(bar["high"] for bar in permitted[session - 21:session - 1])
        previous_threshold = Decimal(str(previous_level)) * Decimal("1.005")
        if (Decimal(str(permitted[session]["close"])) > threshold
                and Decimal(str(permitted[session - 1]["close"])) <= previous_threshold):
            prior_volume = median(bar["volume"] for bar in window)
            signals.append({
                "kind": "breaking_out", "direction": "buy", "status": "completed",
                "completion_date": permitted[session]["date"],
                "available_at": permitted[session]["date"],
                "breakout_level": reference["high"],
                "pivots": [{"role": "prior_20_high", "date": reference["date"],
                            "price": reference["high"], "confirmed_on": window[-1]["date"]}],
                "checks": {"close_threshold": float(threshold),
                           "previous_close_threshold": float(previous_threshold),
                           "previous_close": permitted[session - 1]["close"],
                           "breakout_volume_ratio": permitted[session]["volume"] / prior_volume if prior_volume else None},
                "window_start": window[0]["date"], "window_end": permitted[session]["date"],
                "detector_version": VERSION, "parameter_hash": PARAMETER_HASH,
            })
    for session in range(51, len(permitted)):
        window = permitted[session - 20:session]
        reference = min(window, key=lambda bar: bar["low"])
        threshold = Decimal(str(reference["low"])) * Decimal("0.995")
        previous_level = min(bar["low"] for bar in permitted[session - 21:session - 1])
        previous_threshold = Decimal(str(previous_level)) * Decimal("0.995")
        previous_average = mean(bar["close"] for bar in permitted[session - 50:session])
        latest_average = mean(bar["close"] for bar in permitted[session - 49:session + 1])
        if (Decimal(str(permitted[session]["close"])) < threshold
                and Decimal(str(permitted[session - 1]["close"])) >= previous_threshold
                and latest_average < previous_average):
            signals.append({
                "kind": "rolling_over", "direction": "sell", "status": "completed",
                "completion_date": permitted[session]["date"],
                "available_at": permitted[session]["date"],
                "breakout_level": reference["low"],
                "pivots": [{"role": "prior_20_low", "date": reference["date"],
                            "price": reference["low"], "confirmed_on": window[-1]["date"]}],
                "checks": {"close_threshold": float(threshold),
                           "previous_close_threshold": float(previous_threshold),
                           "previous_close": permitted[session - 1]["close"],
                           "previous_50_close_average": previous_average,
                           "latest_50_close_average": latest_average},
                "window_start": permitted[session - 50]["date"],
                "window_end": permitted[session]["date"],
                "detector_version": VERSION, "parameter_hash": PARAMETER_HASH,
            })
    for session in range(1, len(permitted)):
        previous = permitted[session - 1]
        current = permitted[session]
        previous_close = Decimal(str(previous["close"]))
        opening = Decimal(str(current["open"]))
        if opening >= previous_close * Decimal("1.02"):
            signals.append({
                "kind": "gapping_up", "direction": "observation", "status": "completed",
                "completion_date": current["date"], "available_at": current["date"],
                "breakout_level": previous["close"],
                "pivots": [{"role": "previous_close", "date": previous["date"],
                            "price": previous["close"], "confirmed_on": previous["date"]}],
                "checks": {"opening_gap_fraction": float(opening / previous_close - 1)},
                "window_start": previous["date"], "window_end": current["date"],
                "detector_version": VERSION, "parameter_hash": PARAMETER_HASH,
            })
    return sorted(signals, key=lambda signal: signal["available_at"])
