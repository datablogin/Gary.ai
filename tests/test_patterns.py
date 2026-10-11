"""Synthetic recognition controls at the approved public detector seam."""

import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from gary.patterns import detect_patterns


def fixture_bars(name):
    fixture = json.loads((Path(__file__).parent / "fixtures" / f"pattern-{name}.json").read_text())
    assert fixture["synthetic"] is True
    return fixture["bars"]


def redraw(bars, anchors):
    """Draw independently selected synthetic close anchors, not detector labels."""
    copied = [dict(bar) for bar in bars]
    for (left, first), (right, last) in zip(anchors, anchors[1:]):
        for index in range(left, right + 1):
            value = first + (last - first) * (index - left) / (right - left)
            copied[index].update(open=value, high=value + 0.1, low=value - 0.1, close=value)
    return copied


def extend_sessions(bars, count):
    copied = [dict(bar) for bar in bars]
    day = date.fromisoformat(copied[-1]["date"])
    while len(copied) < count:
        day += timedelta(days=1)
        if day.weekday() < 5:
            copied.append({**copied[-1], "date": day.isoformat()})
    return copied


def test_invalid_permitted_ohlc_raises_instead_of_returning_no_pattern():
    bars = [dict(date="2026-01-02", open=10, high=9, low=8, close=10, volume=100)]
    with pytest.raises(ValueError, match="OHLC"):
        detect_patterns(bars, "2026-01-02")


def test_duplicate_permitted_session_is_rejected():
    bar = dict(date="2026-01-02", open=10, high=11, low=9, close=10, volume=100)
    with pytest.raises(ValueError, match="increasing"):
        detect_patterns([bar, dict(bar)], "2026-01-02")


def test_completed_inverse_returns_causal_neckline_evidence():
    signals = detect_patterns(fixture_bars("inverse"), "2025-04-10")
    assert len(signals) == 1
    signal = signals[0]
    assert (signal["kind"], signal["direction"], signal["status"]) == (
        "inverse_head_shoulders", "buy", "completed"
    )
    assert signal["completion_date"] == signal["available_at"] == "2025-04-10"
    assert signal["breakout_level"] == pytest.approx(110)
    assert signal["pivots"][-1] == dict(
        role="right_shoulder", date="2025-03-27", price=100, confirmed_on="2025-04-01"
    )


def test_inverse_rejects_unequal_shoulders_near_miss():
    bars = redraw(fixture_bars("inverse"), [(52, 110), (60, 107), (69, 110), (70, 111)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_completed_top_returns_sell_after_neckline_breakdown():
    signals = detect_patterns(fixture_bars("top"), "2025-04-10")
    assert len(signals) == 1
    assert signals[0]["kind"] == "head_shoulders_top"
    assert signals[0]["direction"] == "sell"
    assert signals[0]["completion_date"] == "2025-04-10"
    assert signals[0]["breakout_level"] == pytest.approx(110)
    assert signals[0]["pivots"][2]["price"] == 130


def test_short_inverse_shape_is_not_a_multiweek_pattern():
    bars = redraw(fixture_bars("inverse"), [
        (0, 120), (20, 100), (23, 110), (27, 90), (31, 110),
        (35, 100), (39, 110), (40, 111), (70, 115)
    ])
    assert detect_patterns(bars, bars[40]["date"]) == []


def test_inverse_requires_a_preceding_decline():
    bars = redraw(fixture_bars("inverse"), [(0, 80), (16, 104), (20, 100)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_head_must_stand_out_from_shoulders():
    bars = redraw(fixture_bars("inverse"), [(28, 110), (40, 99), (52, 110)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_head_shoulders_rejects_extreme_time_asymmetry():
    bars = redraw(fixture_bars("inverse"), [
        (0, 120), (20, 100), (24, 110), (30, 90), (52, 110),
        (60, 100), (69, 110), (70, 111)
    ])
    assert detect_patterns(bars, "2025-04-10") == []


def test_head_shoulders_rejects_steep_neckline():
    bars = redraw(fixture_bars("inverse"), [(40, 90), (52, 116), (60, 100), (69, 120), (70, 122)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_new_low_invalidates_uncompleted_inverse():
    bars = redraw(fixture_bars("inverse"), [(60, 100), (64, 105), (65, 85), (69, 110), (70, 111)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_old_uncompleted_inverse_expires_before_late_crossing():
    bars = redraw(extend_sessions(fixture_bars("inverse"), 102), [(60, 100), (101, 111)])
    assert detect_patterns(bars, bars[-1]["date"]) == []


def test_completed_cup_returns_handle_and_volume_evidence():
    signals = detect_patterns(fixture_bars("cup"), "2025-04-10")
    assert len(signals) == 1
    signal = signals[0]
    assert signal["kind"] == "cup_handle" and signal["direction"] == "buy"
    assert signal["completion_date"] == signal["available_at"] == "2025-04-10"
    assert signal["breakout_level"] == pytest.approx(100)
    assert signal["pivots"][-1] == dict(
        role="handle_low", date="2025-04-03", price=95, confirmed_on="2025-04-08"
    )
    assert signal["checks"]["breakout_volume_ratio"] == 2


def test_cup_rejects_deep_handle_near_miss():
    bars = redraw(fixture_bars("cup"), [(60, 100), (65, 90), (69, 99), (70, 101)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_single_v_is_not_a_rounded_cup():
    bars = redraw(fixture_bars("cup"), [(20, 100), (38, 90), (40, 80), (42, 90), (60, 100)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_cup_rejects_dissimilar_rims():
    bars = redraw(fixture_bars("cup"), [(40, 80), (60, 103), (65, 98), (69, 102), (70, 104)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_cup_bottom_must_be_central():
    bars = redraw(fixture_bars("cup"), [(20, 100), (26, 82), (30, 80), (34, 82), (60, 100)])
    assert detect_patterns(bars, "2025-04-10") == []


@pytest.mark.parametrize("length,anchors,end", [
    (71, [(0, 80), (20, 100), (24, 82), (27, 80), (30, 82), (35, 100),
          (40, 95), (44, 99), (45, 101), (70, 110)], 45),
    (171, [(0, 80), (20, 100), (80, 82), (90, 80), (100, 82), (160, 100),
           (165, 95), (169, 99), (170, 101)], 170),
])
def test_cup_duration_outside_contract_is_rejected(length, anchors, end):
    bars = redraw(extend_sessions(fixture_bars("cup"), length), anchors)
    assert detect_patterns(bars, bars[end]["date"]) == []


@pytest.mark.parametrize("depth", [4, 50])
def test_cup_depth_outside_contract_is_rejected(depth):
    bars = fixture_bars("cup")
    for index in range(20, 61):
        value = 100 - (100 - bars[index]["close"]) * depth / 20
        bars[index].update(open=value, high=value + 0.1, low=value - 0.1, close=value)
    bars = redraw(bars, [(60, 100), (65, 100 - depth / 4), (69, 100 - depth / 20), (70, 101)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_non_list_bars_raise_public_validation_error():
    with pytest.raises(ValueError, match="list"):
        detect_patterns(None, "2025-04-10")


@pytest.mark.parametrize("name", ["inverse", "top", "cup"])
def test_uncompleted_shape_never_emits(name):
    bars = fixture_bars(name)
    assert detect_patterns(bars, "2025-04-09") == []


def test_top_rejects_unequal_shoulders_near_miss():
    bars = redraw(fixture_bars("top"), [(52, 110), (60, 113), (69, 110), (70, 109)])
    assert detect_patterns(bars, "2025-04-10") == []


def test_breakout_before_right_shoulder_confirmation_is_not_backdated():
    bars = redraw(fixture_bars("inverse"), [(60, 100), (61, 110), (62, 111), (70, 119)])
    assert detect_patterns(bars, "2025-04-10") == []


@pytest.mark.parametrize("name", ["inverse", "top", "cup"])
def test_future_ohlcv_is_ignored_before_validation(name):
    bars = fixture_bars(name)
    expected = detect_patterns(bars, "2025-04-10")
    future = {"date": "2026-04-10", "open": None, "high": float("nan")}
    assert detect_patterns([*bars, future], "2025-04-10") == expected


@pytest.mark.parametrize("name", ["inverse", "top", "cup"])
def test_appended_future_cannot_rewrite_available_events(name):
    bars = fixture_bars(name)
    expected = detect_patterns(bars, "2025-04-10")
    extended = redraw(extend_sessions(bars, 101), [(70, bars[-1]["close"]), (80, 140), (90, 80), (100, 150)])
    complete = detect_patterns(extended, extended[-1]["date"])
    assert [event for event in complete if event["available_at"] <= "2025-04-10"] == expected
    assert detect_patterns(extended, "2025-04-10") == expected


@pytest.mark.parametrize("name", ["inverse", "top", "cup"])
@pytest.mark.parametrize("factor", [0.1, 4])
def test_pattern_identity_is_price_scale_invariant(name, factor):
    bars = fixture_bars(name)
    expected = detect_patterns(bars, "2025-04-10")[0]
    scaled = [{**bar, **{key: bar[key] * factor for key in ("open", "high", "low", "close")}}
              for bar in bars]
    actual = detect_patterns(scaled, "2025-04-10")[0]
    assert (actual["kind"], actual["completion_date"], actual["available_at"]) == (
        expected["kind"], expected["completion_date"], expected["available_at"]
    )
    assert actual["breakout_level"] == pytest.approx(expected["breakout_level"] * factor)


def test_intraday_breakout_without_close_confirmation_never_emits():
    bars = redraw(fixture_bars("inverse"), [(69, 110), (70, 110)])
    bars[-1]["high"] = 200
    assert detect_patterns(bars, "2025-04-10") == []


def test_detector_does_not_mutate_inputs():
    bars = fixture_bars("cup")
    original = deepcopy(bars)
    detect_patterns(bars, "2025-04-10")
    assert bars == original


def test_inclusive_shoulder_boundary_survives_price_rescaling():
    bars = redraw(fixture_bars("inverse"), [(52, 110), (60, 105), (69, 110), (70, 111)])
    scaled = [{**bar, **{key: bar[key] * 0.003 for key in ("open", "high", "low", "close")}}
              for bar in bars]
    assert len(detect_patterns(scaled, "2025-04-10")) == 1
