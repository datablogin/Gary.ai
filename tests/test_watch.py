"""Public behavior checks for persistent manual membership and derived Radar."""

import json
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import date, timedelta

from gary.watch import ManualWatchStore

import pytest

from test_coverage import complete_snapshot
from gary.patterns_v2 import detect_patterns
from gary.coverage import coverage_report


def reviewed_record(snapshot):
    return {"company": "Synthetic reviewed company", "coverage_snapshot": snapshot,
            "chart_cutoff": "2026-10-09", "checked_at": "2026-10-09T20:00:00Z",
            "signals": [], "price": 40,
            "sources": [{"label": "Synthetic filings", "url": "synthetic://filings"}]}


def fresh_breakout():
    bars = [{"date": (date(2026, 9, 18) + timedelta(days=index)).isoformat(),
             "open": 95, "high": 100, "low": 90, "close": 95, "volume": 100}
            for index in range(22)]
    bars[-1].update(open=96, high=110, low=95, close=105)
    return next(event for event in detect_patterns(bars, "2026-10-09") if event["kind"] == "breaking_out")


def fresh_rollover():
    bars = [{"date": (date(2026, 10, 9) - timedelta(days=51 - index)).isoformat(),
             "open": 95, "high": 100, "low": 90, "close": 95, "volume": 100}
            for index in range(52)]
    bars[-1].update(open=90, high=95, low=80, close=85)
    return next(event for event in detect_patterns(bars, "2026-10-09") if event["kind"] == "rolling_over")


def test_manual_membership_and_note_survive_restart_with_missing_data(tmp_path):
    directory = tmp_path / "private-watch"
    store = ManualWatchStore(directory, {})
    store.add(" brk.b ", "Wait for quarterly evidence")

    view = ManualWatchStore(directory, {}).view("2026-10-09")

    assert view["schema_version"] == "manual-watch-view-v1"
    assert view["as_of"] == "2026-10-09"
    assert view["radar_list"] == view["buy_ready_list"] == []
    entry = view["manual_list"][0]
    assert entry["symbol"] == "BRK-B"
    assert entry["note"] == "Wait for quarterly evidence"
    assert entry["added_at"]
    assert entry["status"] == "needs_data"
    assert set(entry["checks"]) == {"classification", "pe", "yield", "quarterly_revenue", "management", "entry", "allocation"}
    assert all(check["status"] == "missing" for check in entry["checks"].values())
    assert "missing" in entry["why"].lower()


def test_current_technical_exit_blocks_entry_and_requires_stabilization(tmp_path, complete_snapshot):
    record = reviewed_record(complete_snapshot)
    record["signals"] = [fresh_breakout(), fresh_rollover()]
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    entry = view["manual_list"][0]
    assert entry["status"] == "needs_review"
    assert entry["checks"]["entry"]["status"] == "fail"
    assert "rolling_over" in entry["why"] and "stabil" in entry["why"].lower()


def test_repeated_add_preserves_membership_date_and_blank_retry_keeps_note(tmp_path):
    store = ManualWatchStore(tmp_path / "watch", {})
    store.add("DEMO", "Initial note")
    added_at = store.view("2026-10-09")["manual_list"][0]["added_at"]
    store.add("demo", "Updated note")
    store.add("DEMO")

    entries = ManualWatchStore(tmp_path / "watch", {}).view("2026-10-09")["manual_list"]

    assert len(entries) == 1
    assert entries[0]["note"] == "Updated note"
    assert entries[0]["added_at"] == added_at


@pytest.mark.parametrize("symbol", ["", " ", "../DEMO", "https://demo", "^GSPC", "DEMO/A", "A-B-C", "123", "ABCDEF12345", None])
def test_invalid_ticker_is_rejected_before_creating_private_files(tmp_path, symbol):
    directory = tmp_path / "watch"
    store = ManualWatchStore(directory, {})

    with pytest.raises(ValueError):
        store.add(symbol)

    assert not directory.exists()


def test_removal_survives_restart_and_archives_note_without_erasing_evidence(tmp_path):
    directory = tmp_path / "watch"
    store = ManualWatchStore(directory, {})
    store.add("DEMO", "Retain this reasoning")
    store.remove("demo")
    store.remove("DEMO")

    assert ManualWatchStore(directory, {}).view("2026-10-09")["manual_list"] == []
    # The persisted file is the external storage boundary, not an internal collaborator.
    persisted = json.loads(next(directory.glob("*.json")).read_text())
    assert persisted["archive"][0]["symbol"] == "DEMO"
    assert persisted["archive"][0]["note"] == "Retain this reasoning"
    assert persisted["archive"][0]["removed_at"]
    assert len(persisted["archive"]) == 1


@pytest.mark.parametrize("note", ["x" * 501, None, 123])
def test_invalid_note_is_rejected_before_creating_private_files(tmp_path, note):
    directory = tmp_path / "watch"

    with pytest.raises(ValueError):
        ManualWatchStore(directory, {}).add("DEMO", note)

    assert not directory.exists()


@pytest.mark.parametrize("corruption", ["broken JSON", "[]", '{"schema_version":"manual-watch-state-v1","entries":[],"archive":"lost"}'])
def test_corrupt_state_fails_loudly_without_empty_reset_or_rewrite(tmp_path, corruption):
    directory = tmp_path / "watch"
    store = ManualWatchStore(directory, {})
    store.add("DEMO")
    persisted = next(directory.glob("*.json"))
    persisted.write_text(corruption)

    for action in (lambda: store.view("2026-10-09"), lambda: store.add("OTHER"), lambda: store.remove("DEMO")):
        with pytest.raises(ValueError, match="[Cc]orrupt"):
            action()
        assert persisted.read_text() == corruption


def _add_synthetic_symbol(arguments):
    directory, symbol = arguments
    ManualWatchStore(directory, {}).add(symbol, "Synthetic process test")


def test_competing_processes_preserve_all_memberships_in_private_files(tmp_path):
    directory = tmp_path / "watch"
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(_add_synthetic_symbol, [(directory, f"DEMO{i}") for i in range(24)]))

    entries = ManualWatchStore(directory, {}).view("2026-10-09")["manual_list"]

    assert {entry["symbol"] for entry in entries} == {f"DEMO{i}" for i in range(24)}
    assert directory.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in directory.iterdir())


def test_vendor_proximity_explains_failed_rules_without_reviewed_clearance(tmp_path):
    catalog = {"DEMO": {"company": "Synthetic company",
                        "observations": {"trailing_pe": 31, "dividend_yield": 0.03,
                                         "revenue_growth": 0.10, "sga_growth": 0.30},
                        "chart_cutoff": "2026-10-09", "checked_at": "2026-10-09T20:00:00Z",
                        "sources": [{"label": "Synthetic quote", "url": "synthetic://quote"}]}}
    original = deepcopy(catalog)
    store = ManualWatchStore(tmp_path / "watch", catalog)
    store.add("DEMO")

    view = store.view("2026-10-09")

    entry = view["manual_list"][0]
    assert entry["status"] == "needs_review"
    assert entry["checks"]["pe"]["status"] == "observed_fail"
    assert entry["checks"]["yield"]["status"] == "observed_pass"
    assert entry["checks"]["quarterly_revenue"]["status"] == "observed_fail"
    assert entry["checks"]["management"]["status"] != "pass"
    assert "30" in entry["why"] and "15%" in entry["why"] and "25%" in entry["why"]
    assert entry["company"] == "Synthetic company"
    assert entry["sources"] == catalog["DEMO"]["sources"]
    assert view["radar_list"] == view["buy_ready_list"] == []
    assert catalog == original


def test_fresh_expanded_entry_with_current_price_and_reviewed_coverage_is_buy_ready(tmp_path, complete_snapshot):
    record = reviewed_record(complete_snapshot)
    record["signals"] = [fresh_breakout()]
    catalog = {"DEMO": record}
    original = deepcopy(catalog)
    store = ManualWatchStore(tmp_path / "watch", catalog)
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["radar_list"] == []
    assert [entry["symbol"] for entry in view["buy_ready_list"]] == ["DEMO"]
    assert view["manual_list"][0]["status"] == "buy_ready"
    assert all(check["status"] == "pass" for check in view["buy_ready_list"][0]["checks"].values())
    assert "breaking_out" in view["buy_ready_list"][0]["why"]
    assert catalog == original


def test_radar_is_derived_from_current_complete_catalog_and_can_overlap_manual(tmp_path, complete_snapshot):
    catalog = {"DEMO": reviewed_record(complete_snapshot)}
    original = deepcopy(catalog)
    store = ManualWatchStore(tmp_path / "watch", catalog)

    derived = store.view("2026-10-09")
    store.add("DEMO", "Wait for entry")
    view = store.view("2026-10-09")

    assert derived["manual_list"] == []
    assert [entry["symbol"] for entry in derived["radar_list"]] == ["DEMO"]
    assert view["buy_ready_list"] == []
    entry = view["manual_list"][0]
    assert entry["status"] == "radar"
    assert entry["checks"]["entry"]["status"] == "fail"
    assert all(entry["checks"][key]["status"] == "pass" for key in ("classification", "pe", "yield", "quarterly_revenue", "management", "allocation"))
    assert "entry" in entry["why"].lower()
    assert "note" not in view["radar_list"][0]
    assert catalog == original


def test_entry_selection_remains_visible_when_100_share_block_exceeds_budget(tmp_path, complete_snapshot):
    record = reviewed_record(complete_snapshot)
    record.update(signals=[fresh_breakout()], price=81)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    entry = view["manual_list"][0]
    assert entry["status"] == "allocation_blocked"
    assert entry["checks"]["entry"]["status"] == "pass"
    assert entry["checks"]["allocation"]["status"] == "fail"
    assert entry["checks"]["allocation"]["value"] == 8100
    assert "$8,000" in entry["why"]


@pytest.mark.parametrize(("field", "value"), [
    ("detector_version", "unknown"), ("parameter_hash", "invented"),
    ("completion_date", "2026-10-08"), ("window_end", "2026-10-08"),
    ("window_start", "2026-10-10"), ("breakout_level", None),
    ("pivots", []), ("checks", {}), ("status", "optimistic"),
])
def test_incomplete_or_mismatched_expanded_signal_requires_review(tmp_path, complete_snapshot, field, value):
    event = fresh_breakout()
    event[field] = value
    record = reviewed_record(complete_snapshot)
    record["signals"] = [event]
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    assert view["manual_list"][0]["status"] == "needs_review"
    assert view["manual_list"][0]["checks"]["entry"]["status"] == "unreviewed"
    assert "signal" in view["manual_list"][0]["why"].lower()


@pytest.mark.parametrize("checked_at", [None, "2026-10-09T20:00:00", "2026-10-08T20:00:00Z", "2026-10-09T19:00:00Z", "invalid"])
def test_missing_or_old_refresh_receipt_cannot_clear_current_entry(tmp_path, complete_snapshot, checked_at):
    record = reviewed_record(complete_snapshot)
    record.update(signals=[fresh_breakout()], checked_at=checked_at)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    assert view["manual_list"][0]["status"] == "needs_review"
    assert view["manual_list"][0]["checks"]["entry"]["status"] in {"missing", "stale", "unreviewed"}
    assert "refresh" in view["manual_list"][0]["why"].lower()


def test_old_vendor_observations_retain_values_and_failed_rule_with_stale_warning(tmp_path):
    catalog = {"DEMO": {"observations": {"trailing_pe": 31, "dividend_yield": 0.03,
                                         "revenue_growth": 0.10, "sga_growth": 0.30},
                        "chart_cutoff": "2026-10-08", "checked_at": "2026-10-08T20:00:00Z",
                        "price": 40, "signals": []}}
    store = ManualWatchStore(tmp_path / "watch", catalog)
    store.add("DEMO")

    view = store.view("2026-10-09")

    entry = view["manual_list"][0]
    assert entry["checks"]["pe"]["status"] == "stale"
    assert entry["checks"]["pe"]["value"] == 31
    assert entry["checks"]["allocation"]["status"] == "stale"
    assert "failed rule" in entry["why"].lower() and "stale" in entry["why"].lower()
    assert view["radar_list"] == view["buy_ready_list"] == []


def test_gap_observation_is_radar_context_and_never_an_eligible_entry(tmp_path, complete_snapshot):
    bars = [{"date": "2026-10-08", "open": 100, "high": 100, "low": 100, "close": 100, "volume": 100},
            {"date": "2026-10-09", "open": 102, "high": 103, "low": 101, "close": 102, "volume": 100}]
    record = reviewed_record(complete_snapshot)
    record["signals"] = detect_patterns(bars, "2026-10-09")
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})

    view = store.view("2026-10-09")

    assert view["buy_ready_list"] == []
    entry = view["radar_list"][0]
    assert entry["checks"]["entry"]["status"] == "fail"
    assert "observation" in entry["why"].lower()


def test_partial_coverage_retains_vendor_proximity_without_concealing_missing_reviews(tmp_path):
    record = {"coverage_snapshot": {"symbol": "DEMO"},
              "observations": {"trailing_pe": 31, "dividend_yield": 0.03,
                               "revenue_growth": 0.20, "sga_growth": 0.30},
              "chart_cutoff": "2026-10-09", "checked_at": "2026-10-09T20:00:00Z"}
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO", "Membership survives incomplete review")

    view = store.view("2026-10-09")

    entry = view["manual_list"][0]
    assert entry["checks"]["pe"]["status"] == "observed_fail"
    assert entry["checks"]["pe"]["value"] == 31
    assert entry["checks"]["yield"]["status"] == "observed_pass"
    assert entry["checks"]["management"]["status"] != "pass"
    assert "25%" in entry["why"] and "missing" in entry["why"].lower()
    assert entry["note"] == "Membership survives incomplete review"
    assert view["radar_list"] == view["buy_ready_list"] == []


def test_unresolved_sga_investigation_blocks_radar_until_explicit_review_resolution(tmp_path, complete_snapshot):
    complete_snapshot["fundamentals"]["sga"]["current"]["value"] = 12.5
    record = reviewed_record(complete_snapshot)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    blocked = store.view("2026-10-09")
    record["sga_investigation_resolved"] = True
    resolved = store.view("2026-10-09")

    assert blocked["radar_list"] == blocked["buy_ready_list"] == []
    assert blocked["manual_list"][0]["checks"]["management"]["status"] == "fail"
    assert "25%" in blocked["manual_list"][0]["why"]
    assert [entry["symbol"] for entry in resolved["radar_list"]] == ["DEMO"]


@pytest.mark.parametrize(("field", "value", "check", "status"), [
    ("classification", None, "classification", "missing"),
    ("classification", {"status": "unreviewed"}, "classification", "unreviewed"),
    ("headquarters", {"status": "stale"}, "management", "stale"),
    ("headquarters", {"state": "confirmed_investment", "source": {"url": "synthetic://hq", "available_at": "2026-10-08", "fetched_at": "2026-10-09T20:00:00Z"}}, "management", "fail"),
    ("latest_reported_period", None, "quarterly_revenue", "unreviewed"),
])
def test_incomplete_or_failed_review_never_populates_radar_or_buy_ready(tmp_path, complete_snapshot, field, value, check, status):
    complete_snapshot[field] = value
    record = reviewed_record(complete_snapshot)
    record["signals"] = [fresh_breakout()]
    original = deepcopy(record)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO", "Preserve membership")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    assert view["manual_list"][0]["checks"][check]["status"] == status
    assert view["manual_list"][0]["note"] == "Preserve membership"
    assert record == original


@pytest.mark.parametrize(("observed_date", "expected_status"), [("2026-10-08", "stale"), ("2026-10-10", "unreviewed"), ("bad date", "unreviewed")])
def test_refreshing_chart_does_not_upgrade_older_individually_dated_observations(tmp_path, observed_date, expected_status):
    record = {"observations": {"trailing_pe": 20, "dividend_yield": 0.03,
                               "revenue_growth": 0.20, "sga_growth": 0.30},
              "observation_dates": {"revenue_growth": observed_date, "sga_growth": observed_date},
              "chart_cutoff": "2026-10-09", "checked_at": "2026-10-09T20:00:00Z"}
    original = deepcopy(record)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    entry = store.view("2026-10-09")["manual_list"][0]

    assert entry["checks"]["pe"]["status"] == "observed_pass"
    assert entry["checks"]["quarterly_revenue"]["status"] == expected_status
    assert entry["checks"]["quarterly_revenue"]["value"] == 0.20
    assert entry["checks"]["management"]["status"] == expected_status
    assert observed_date in entry["why"] and expected_status in entry["why"]
    assert record == original


def test_observation_dates_do_not_replace_complete_reviewed_coverage(tmp_path, complete_snapshot):
    record = reviewed_record(complete_snapshot)
    record.update(observations={"revenue_growth": 0.20}, observation_dates={"revenue_growth": "2026-10-08"})

    view = ManualWatchStore(tmp_path / "watch", {"DEMO": record}).view("2026-10-09")

    assert view["radar_list"][0]["checks"]["quarterly_revenue"]["status"] == "pass"


@pytest.mark.parametrize("value", [True, "20", float("nan"), float("inf")])
def test_invalid_vendor_numbers_are_explicitly_unreviewed_and_json_safe(tmp_path, value):
    record = {"observations": {"trailing_pe": value},
              "chart_cutoff": "2026-10-09", "checked_at": "2026-10-09T20:00:00Z"}
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    check = view["manual_list"][0]["checks"]["pe"]
    assert check["status"] == "unreviewed"
    assert check["value"] is None
    assert "invalid" in check["message"].lower()
    json.dumps(view, allow_nan=False)


def test_extreme_finite_price_does_not_emit_infinite_allocation_cost(tmp_path, complete_snapshot):
    record = reviewed_record(complete_snapshot)
    record.update(price=1e308, signals=[fresh_breakout()])
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["buy_ready_list"] == view["radar_list"] == []
    assert view["manual_list"][0]["checks"]["allocation"]["status"] == "fail"
    json.dumps(view, allow_nan=False)


@pytest.mark.parametrize("as_of", [None, "20261009", "2026-10-09T20:00:00Z", "invalid"])
def test_invalid_evaluation_date_rejects_without_creating_or_resetting_membership(tmp_path, as_of):
    directory = tmp_path / "watch"
    store = ManualWatchStore(directory, {})

    with pytest.raises(ValueError):
        store.view(as_of)

    assert not directory.exists()


def test_headquarters_exclusion_does_not_mislabel_reviewed_security_classification(tmp_path, complete_snapshot):
    complete_snapshot["headquarters"]["state"] = "confirmed_investment"
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": reviewed_record(complete_snapshot)})
    store.add("DEMO")

    entry = store.view("2026-10-09")["manual_list"][0]

    assert entry["checks"]["classification"]["status"] == "pass"
    assert entry["checks"]["management"]["status"] == "fail"
    assert entry["status"] == "filtered_out"


def test_exact_revenue_threshold_uses_coverage_gate_despite_float_rounding(tmp_path, complete_snapshot):
    complete_snapshot["fundamentals"]["revenue"]["prior_year"]["value"] = 3
    complete_snapshot["fundamentals"]["revenue"]["current"]["value"] = 3.45
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": reviewed_record(complete_snapshot)})
    store.add("DEMO")

    view = store.view("2026-10-09")

    assert view["manual_list"][0]["checks"]["quarterly_revenue"]["status"] == "fail"
    assert view["manual_list"][0]["status"] == "filtered_out"
    assert view["radar_list"] == view["buy_ready_list"] == []


@pytest.mark.parametrize("kind", ["boolean", "hand_report", "mismatched", "malformed"])
def test_untrusted_coverage_inputs_never_clear_or_reset_manual_membership(tmp_path, complete_snapshot, kind):
    snapshot = deepcopy(complete_snapshot)
    if kind == "boolean":
        snapshot = True
    elif kind == "hand_report":
        snapshot = coverage_report(snapshot, "2026-10-09")
    elif kind == "mismatched":
        snapshot["symbol"] = "OTHER"
    else:
        snapshot["classification"] = ["invalid security response"]
    record = reviewed_record(snapshot)
    record.update(signals=[fresh_breakout()], passed=True, buy_allowed=True)
    original = deepcopy(record)
    store = ManualWatchStore(tmp_path / "watch", {"DEMO": record})
    store.add("DEMO", "Preserve my note")

    view = store.view("2026-10-09")

    assert view["radar_list"] == view["buy_ready_list"] == []
    assert view["manual_list"][0]["checks"]["classification"]["status"] != "pass"
    assert view["manual_list"][0]["note"] == "Preserve my note"
    assert record == original
