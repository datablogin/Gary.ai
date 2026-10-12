"""Synthetic controls at the user-approved expanded detector seam."""

import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from gary.patterns import detect_patterns as detect_original
from gary.patterns_v2 import detect_patterns


def daily_bars(count, close=100, high=100, low=99):
    """Explicit synthetic daily prices; dates are increasing weekdays."""
    bars = []
    day = date(2026, 7, 1)
    while len(bars) < count:
        if day.weekday() < 5:
            bars.append({"date": day.isoformat(), "open": close, "high": high,
                         "low": low, "close": close, "volume": 1000})
        day += timedelta(days=1)
    return bars


@pytest.mark.parametrize("name", ["inverse", "top", "cup"])
def test_expanded_detector_preserves_existing_geometry_and_evidence(name):
    fixture = json.loads((Path(__file__).parent / "fixtures" / f"pattern-{name}.json").read_text())
    assert fixture["synthetic"] is True
    original = detect_original(fixture["bars"], "2025-04-10")
    expanded = detect_patterns(fixture["bars"], "2025-04-10")
    retained = [event for event in expanded if event["kind"] == original[0]["kind"]]
    assert [{key: value for key, value in event.items() if key not in {"detector_version", "parameter_hash"}}
            for event in retained] == [
        {key: value for key, value in event.items() if key not in {"detector_version", "parameter_hash"}}
        for event in original
    ]
    assert retained[0]["detector_version"] == "expanded-signals-v1"
    assert retained[0]["parameter_hash"] != original[0]["parameter_hash"]


def test_completed_breakout_uses_previous_twenty_highs_excluding_current_high():
    bars = daily_bars(22)
    bars[-1].update(high=140, close=100.51, volume=1)
    signals = detect_patterns(bars, bars[-1]["date"])
    assert len(signals) == 1
    signal = signals[0]
    assert (signal["kind"], signal["direction"], signal["status"]) == (
        "breaking_out", "buy", "completed"
    )
    assert signal["completion_date"] == signal["available_at"] == bars[-1]["date"]
    assert signal["breakout_level"] == 100
    assert signal["pivots"][0]["role"] == "prior_20_high"
    assert signal["pivots"][0]["price"] == 100
    assert signal["window_start"] == bars[1]["date"]
    assert signal["window_end"] == bars[-1]["date"]
    assert signal["checks"]["close_threshold"] == pytest.approx(100.5)
    assert signal["checks"]["breakout_volume_ratio"] == 0.001


def test_breakout_continuation_does_not_repeat_the_first_crossing():
    bars = daily_bars(23)
    bars[21].update(open=100, high=101, low=100, close=101)
    bars[22].update(open=101, high=102, low=101, close=102)
    signals = detect_patterns(bars, bars[-1]["date"])
    assert [(signal["kind"], signal["completion_date"]) for signal in signals] == [
        ("breaking_out", bars[21]["date"])
    ]


def test_exact_half_percent_breakout_and_intraday_crossing_are_not_close_confirmation():
    bars = daily_bars(22)
    bars[-1].update(high=120, close=100.5)
    assert detect_patterns(bars, bars[-1]["date"]) == []
    bars[-1]["close"] = 100.49
    assert detect_patterns(bars, bars[-1]["date"]) == []


def test_completed_rollover_uses_previous_lows_and_reports_falling_fifty_day_average():
    bars = daily_bars(52)
    bars[-1].update(high=120, low=80, close=98.49)
    signals = detect_patterns(bars, bars[-1]["date"])
    assert len(signals) == 1
    signal = signals[0]
    assert (signal["kind"], signal["direction"], signal["status"]) == (
        "rolling_over", "sell", "completed"
    )
    assert signal["completion_date"] == signal["available_at"] == bars[-1]["date"]
    assert signal["breakout_level"] == 99
    assert signal["pivots"][0]["role"] == "prior_20_low"
    assert signal["pivots"][0]["price"] == 99
    assert signal["window_start"] == bars[1]["date"]
    assert signal["checks"]["close_threshold"] == 98.505
    assert signal["checks"]["previous_50_close_average"] == 100
    assert signal["checks"]["latest_50_close_average"] == pytest.approx(99.9698)


def test_breakdown_without_falling_fifty_day_average_is_not_a_rollover():
    bars = daily_bars(52)
    bars[1].update(open=90, high=90, low=89, close=90)
    bars[-1].update(low=98, close=98.49)
    assert [signal for signal in detect_patterns(bars, bars[-1]["date"])
            if signal["kind"] == "rolling_over"] == []

    flat_average = daily_bars(52, close=102, high=102, low=101)
    flat_average[1].update(open=100, high=100, low=99, close=100)
    flat_average[-1].update(low=99, close=100)
    assert [signal for signal in detect_patterns(flat_average, flat_average[-1]["date"])
            if signal["kind"] == "rolling_over"] == []


def test_rollover_continuation_does_not_repeat_the_first_crossing():
    bars = daily_bars(53)
    bars[51].update(open=100, high=100, low=98, close=98)
    bars[52].update(open=98, high=98, low=97, close=97)
    assert [(signal["kind"], signal["completion_date"])
            for signal in detect_patterns(bars, bars[-1]["date"])] == [
        ("rolling_over", bars[51]["date"])
    ]


def test_exact_two_percent_opening_gap_is_observation_even_after_intraday_reversal():
    bars = daily_bars(2)
    bars[-1].update(open=102, high=105, low=90, close=95)
    signals = detect_patterns(bars, bars[-1]["date"])
    assert len(signals) == 1
    signal = signals[0]
    assert (signal["kind"], signal["direction"], signal["status"]) == (
        "gapping_up", "observation", "completed"
    )
    assert signal["completion_date"] == signal["available_at"] == bars[-1]["date"]
    assert signal["breakout_level"] == 100
    assert signal["pivots"] == [{"role": "previous_close", "date": bars[0]["date"],
                                "price": 100, "confirmed_on": bars[0]["date"]}]
    assert signal["checks"]["opening_gap_fraction"] == 0.02
    assert signal["window_start"] == bars[0]["date"]
    assert signal["window_end"] == bars[-1]["date"]


def test_expanded_signals_are_returned_in_completion_order():
    bars = daily_bars(22)
    bars[1].update(open=102, high=102)
    bars[-1].update(high=103, close=103)
    assert [(signal["kind"], signal["completion_date"])
            for signal in detect_patterns(bars, bars[-1]["date"])] == [
        ("gapping_up", bars[1]["date"]), ("breaking_out", bars[-1]["date"])
    ]


@pytest.mark.parametrize("kind, count, prices", [
    ("breaking_out", 22, {"high": 101, "close": 100.51}),
    ("rolling_over", 52, {"low": 98, "close": 98.49}),
    ("gapping_up", 2, {"open": 102, "high": 103, "close": 101}),
])
def test_new_signal_is_unavailable_until_its_completed_session(kind, count, prices):
    bars = daily_bars(count)
    bars[-1].update(prices)
    assert detect_patterns(bars, bars[-2]["date"]) == []
    assert [signal["kind"] for signal in detect_patterns(bars, bars[-1]["date"])] == [kind]


@pytest.mark.parametrize("count, prices", [
    (22, {"high": 101, "close": 100.51}),
    (52, {"low": 98, "close": 98.49}),
    (2, {"open": 102, "high": 103, "close": 101}),
])
def test_future_bars_cannot_rewrite_new_signals_or_affect_earlier_validation(count, prices):
    bars = daily_bars(count)
    bars[-1].update(prices)
    cutoff = bars[-1]["date"]
    saved = deepcopy(bars)
    expected = detect_patterns(bars, cutoff)
    extended = [*bars, *daily_bars(count + 3)[count:]]
    later = detect_patterns(extended, extended[-1]["date"])
    assert [signal for signal in later if signal["available_at"] <= cutoff] == expected
    extended[-1].update(open=None, high=float("nan"), close="invalid", volume=-1)
    assert detect_patterns(extended, cutoff) == expected
    assert bars == saved


@pytest.mark.parametrize("count, prices, excluded_kind", [
    (21, {"high": 101, "close": 100.51}, "breaking_out"),
    (51, {"low": 98, "close": 98.49}, "rolling_over"),
    (1, {"open": 102, "high": 103}, "gapping_up"),
])
def test_short_histories_do_not_establish_unavailable_crossing_state(count, prices, excluded_kind):
    bars = daily_bars(count)
    bars[-1].update(prices)
    assert [signal for signal in detect_patterns(bars, bars[-1]["date"])
            if signal["kind"] == excluded_kind] == []


def test_exact_half_percent_breakdown_is_not_a_rollover():
    bars = daily_bars(52)
    bars[-1].update(low=98, close=98.505)
    assert detect_patterns(bars, bars[-1]["date"]) == []


def test_opening_gap_below_two_percent_is_not_an_observation():
    bars = daily_bars(2)
    bars[-1].update(open=101.99, high=105, close=100)
    assert detect_patterns(bars, bars[-1]["date"]) == []


def test_gap_observation_and_breakout_can_coexist_at_the_same_close():
    bars = daily_bars(22)
    bars[-1].update(open=102, high=103, close=103)
    assert [(signal["kind"], signal["direction"])
            for signal in detect_patterns(bars, bars[-1]["date"])] == [
        ("breaking_out", "buy"), ("gapping_up", "observation")
    ]


@pytest.mark.parametrize("bad", ["duplicate", "relationship", "nonfinite", "negative_volume"])
def test_invalid_permitted_bars_raise_at_the_expanded_public_seam(bad):
    bars = daily_bars(22)
    if bad == "duplicate": bars[-1]["date"] = bars[-2]["date"]
    if bad == "relationship": bars[-1]["close"] = 200
    if bad == "nonfinite": bars[-1]["volume"] = float("nan")
    if bad == "negative_volume": bars[-1]["volume"] = -1
    with pytest.raises(ValueError):
        detect_patterns(bars, bars[-1]["date"])


def test_decimal_prices_with_a_flat_fifty_day_average_do_not_create_a_rollover():
    bars = daily_bars(52, close=1.7, high=1.7, low=1.53)
    bars[1].update(open=0.1, high=0.1, low=0.09, close=0.1)
    bars[-1].update(low=0.09, close=0.1)
    # Each 50-session average contains 49 closes of 1.7 and one of 0.1: 1.668.
    assert [signal for signal in detect_patterns(bars, bars[-1]["date"])
            if signal["kind"] == "rolling_over"] == []
