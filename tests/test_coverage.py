"""Public behavior checks for the approved coverage-report seam."""

from copy import deepcopy

import pytest

from gary.coverage import coverage_report


def source(label, available_at="2026-10-08"):
    return {
        "url": f"synthetic://{label}",
        "available_at": available_at,
        "fetched_at": "2026-10-09T19:00:00Z",
    }


def quarter(value, year, label):
    return {
        "value": value,
        "currency": "USD",
        "scope": "consolidated",
        "period_type": "quarter",
        "period_start": f"{year}-04-01",
        "period_end": f"{year}-06-30",
        "source": source(label, f"{year}-08-01T12:00:00Z"),
    }


@pytest.fixture
def complete_snapshot():
    return {
        "symbol": "DEMO",
        "classification": {
            "security_type": "operating_common",
            "exchange": "NASDAQ",
            "reviewed": True,
            "source": source("classification"),
        },
        "headquarters": {
            "state": "reviewed_no_disqualifying_evidence",
            "reviewer": "synthetic fixture",
            "lookback_start": "2025-10-09",
            "lookback_end": "2026-10-09",
            "source": source("headquarters"),
        },
        "latest_reported_period": {
            "period_start": "2026-04-01",
            "period_end": "2026-06-30",
            "verified_as_of": "2026-10-09",
            "source": source("latest-filing", "2026-08-01T12:00:00Z"),
        },
        "fundamentals": {
            "trailing_pe": {
                "value": 20,
                "valid_through": "2026-10-09",
                "source": source("quote"),
            },
            "dividend_yield": {
                "value": 3,
                "unit": "percent",
                "convention": "indicated_regular",
                "policy_reviewed": True,
                "valid_through": "2026-10-09",
                "source": source("dividend"),
            },
            "revenue": {
                "comparability_reviewed": True,
                "current": quarter(120, 2026, "current-revenue"),
                "prior_year": quarter(100, 2025, "prior-revenue"),
            },
            "sga": {
                "comparability_reviewed": True,
                "current": quarter(11, 2026, "current-sga"),
                "prior_year": quarter(10, 2025, "prior-sga"),
            },
        },
    }


def test_complete_curated_snapshot_reports_sources_and_passes_gates(complete_snapshot):
    original = deepcopy(complete_snapshot)
    report = coverage_report(complete_snapshot, "2026-10-09")

    assert report["symbol"] == "DEMO"
    assert report["as_of"] == "2026-10-09"
    assert report["eligibility"] == "eligible"
    assert report["buy_allowed"] is True
    assert report["blockers"] == []
    assert report["normalized"] == pytest.approx(
        {"trailing_pe": 20, "dividend_yield": 0.03, "revenue_growth": 0.20, "sga_growth": 0.10}
    )
    assert report["fields"]["revenue"]["evidence"]["current"]["source"]["url"] == "synthetic://current-revenue"
    assert complete_snapshot == original


@pytest.mark.parametrize(("snapshot", "as_of"), [(None, "2026-10-09"), ([], "2026-10-09"), ({}, "2026-10-09"), ({"symbol": ""}, "2026-10-09"), ({"symbol": "DEMO"}, None), ({"symbol": "DEMO"}, "2026-10-09T19:00:00")])
def test_invalid_top_level_inputs_raise_explicit_value_error(snapshot, as_of):
    with pytest.raises(ValueError):
        coverage_report(snapshot, as_of)


@pytest.mark.parametrize(
    ("changes", "eligibility"),
    [
        ({"security_type": kind}, "excluded")
        for kind in ("adr", "reit", "bdc", "spac", "etf", "fund", "preferred", "unit", "warrant")
    ]
    + [
        ({"security_type": "EQUITY"}, "unknown"),
        ({"reviewed": False}, "unknown"),
        ({"exchange": "LSE"}, "unknown"),
    ],
)
def test_classification_never_admits_excluded_or_unreviewed_securities(complete_snapshot, changes, eligibility):
    complete_snapshot["classification"].update(changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["eligibility"] == eligibility
    assert report["buy_allowed"] is False
    assert report["blockers"]


@pytest.mark.parametrize("field", ["classification", "headquarters", "latest_reported_period", "trailing_pe", "dividend_yield", "revenue", "sga"])
def test_missing_required_evidence_blocks_without_inventing_values(complete_snapshot, field):
    container = complete_snapshot if field in complete_snapshot else complete_snapshot["fundamentals"]
    del container[field]
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] == "missing"
    assert f"{field}:missing" in report["blockers"]
    if field == "trailing_pe":
        assert report["normalized"]["trailing_pe"] is None


@pytest.mark.parametrize("status", ["access_failure", "missing", "stale", "incomparable", "future", "unreviewed"])
def test_provider_failures_remain_distinct_and_cannot_clear_entry(complete_snapshot, status):
    complete_snapshot["fundamentals"]["trailing_pe"] = {"status": status, "source": source("failed-quote")}
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"]["trailing_pe"]["status"] == status
    assert report["normalized"]["trailing_pe"] is None


@pytest.mark.parametrize("field", ["classification", "headquarters", "latest_reported_period", "trailing_pe", "dividend_yield", "revenue", "sga"])
@pytest.mark.parametrize("publication", ["2026-10-09", "2026-10-09T20:01:00Z", "2026-10-10T12:00:00Z"])
def test_future_and_same_day_unknown_publication_block_every_evidence_gate(complete_snapshot, field, publication):
    record = complete_snapshot.get(field, complete_snapshot["fundamentals"].get(field))
    if field in ("revenue", "sga"):
        record = record["current"]
    record["source"]["available_at"] = publication
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] == "future"
    assert f"{field}:future" in report["blockers"]
    if field == "revenue":
        assert report["normalized"]["revenue_growth"] is None


@pytest.mark.parametrize("source_changes", [{"url": ""}, {"url": None}, {"fetched_at": None}, {"fetched_at": "2026-10-09"}, {"available_at": "not-a-date"}, {"available_at": "2026-10-09T19:00:00"}])
def test_source_without_valid_provenance_cannot_supply_clearance(complete_snapshot, source_changes):
    complete_snapshot["classification"]["source"].update(source_changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["eligibility"] == "unknown"
    assert report["fields"]["classification"]["status"] == "unreviewed"


@pytest.mark.parametrize("field", ["trailing_pe", "dividend_yield", "revenue", "sga"])
@pytest.mark.parametrize("value", [None, True, "20", float("nan"), float("inf")])
def test_missing_and_nonfinite_numbers_never_become_normalized_positives(complete_snapshot, field, value):
    observation = complete_snapshot["fundamentals"][field]
    if field in ("revenue", "sga"):
        observation = observation["current"]
    observation["value"] = value
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] in ("missing", "incomparable")
    normalized_key = f"{field}_growth" if field in ("revenue", "sga") else field
    assert report["normalized"][normalized_key] is None


@pytest.mark.parametrize("field", ["revenue", "sga"])
@pytest.mark.parametrize(
    ("side", "changes", "status"),
    [
        ("current", {"period_type": "ytd"}, "incomparable"),
        ("current", {"period_start": "2026-01-01"}, "incomparable"),
        ("current", {"period_end": "2026-10-31"}, "future"),
        ("current", {"period_start": "2026-03-25"}, "incomparable"),
        ("prior_year", {"period_end": "2025-05-31"}, "incomparable"),
        ("prior_year", {"value": 0}, "incomparable"),
        ("prior_year", {"value": -100}, "incomparable"),
        ("prior_year", {"currency": "EUR"}, "incomparable"),
        ("prior_year", {"scope": "segment"}, "incomparable"),
        (None, {"comparability_reviewed": False}, "unreviewed"),
    ],
)
def test_quarter_growth_requires_real_comparable_prior_year_periods(complete_snapshot, field, side, changes, status):
    pair = complete_snapshot["fundamentals"][field]
    (pair[side] if side else pair).update(changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] == status
    assert report["normalized"][f"{field}_growth"] is None


@pytest.mark.parametrize(
    ("changes", "latest_status", "financial_status"),
    [
        ({"period_start": "2026-07-01", "period_end": "2026-09-30"}, "available", "stale"),
        ({"verified_as_of": "2026-10-08"}, "stale", "unreviewed"),
        ({"period_end": "2026-12-31"}, "future", "unreviewed"),
    ],
)
def test_latest_filing_evidence_blocks_vendor_lag_and_unverified_periods(complete_snapshot, changes, latest_status, financial_status):
    complete_snapshot["latest_reported_period"].update(changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"]["latest_reported_period"]["status"] == latest_status
    assert report["fields"]["revenue"]["status"] == financial_status
    assert report["normalized"]["revenue_growth"] is None


@pytest.mark.parametrize("field", ["trailing_pe", "dividend_yield"])
@pytest.mark.parametrize(("valid_through", "status"), [("2026-10-08", "stale"), (None, "unreviewed"), ("not-a-date", "unreviewed")])
def test_expired_or_unreviewed_quote_validity_cannot_clear_entry(complete_snapshot, field, valid_through, status):
    complete_snapshot["fundamentals"][field]["valid_through"] = valid_through
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] == status
    assert report["normalized"][field] is None


@pytest.mark.parametrize(
    ("changes", "status", "expected"),
    [
        ({"value": 0.03, "unit": "fraction"}, "available", 0.03),
        ({"unit": "ratio"}, "incomparable", None),
        ({"policy_reviewed": False}, "unreviewed", None),
        ({"convention": "unknown"}, "unreviewed", None),
    ],
)
def test_dividend_yield_requires_explicit_reviewed_units_and_convention(complete_snapshot, changes, status, expected):
    complete_snapshot["fundamentals"]["dividend_yield"].update(changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["fields"]["dividend_yield"]["status"] == status
    assert report["normalized"]["dividend_yield"] == expected
    assert report["buy_allowed"] is (status == "available")


@pytest.mark.parametrize(
    ("field", "value", "gate"),
    [("trailing_pe", 0, "trailing_pe"), ("trailing_pe", -5, "trailing_pe"), ("trailing_pe", 30, "trailing_pe"), ("dividend_yield", 2, "dividend_yield"), ("dividend_yield", 0, "dividend_yield"), ("revenue", 115, "revenue_growth"), ("revenue", 100, "revenue_growth")],
)
def test_complete_data_still_must_pass_strict_fundamental_thresholds(complete_snapshot, field, value, gate):
    observation = complete_snapshot["fundamentals"][field]
    if field == "revenue":
        observation = observation["current"]
    observation["value"] = value
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["eligibility"] == "eligible"
    assert report["fields"][field]["status"] == "available"
    assert report["buy_allowed"] is False
    assert f"gate:{gate}" in report["blockers"]


@pytest.mark.parametrize(
    ("changes", "eligibility", "status"),
    [
        ({"state": "unknown"}, "eligible", "unreviewed"),
        ({"state": "confirmed_investment"}, "excluded", "available"),
        ({"reviewer": ""}, "eligible", "unreviewed"),
        ({"lookback_start": "2026-10-10"}, "eligible", "unreviewed"),
        ({"lookback_end": "2026-10-08"}, "eligible", "unreviewed"),
    ],
)
def test_headquarters_requires_positive_bounded_review_and_excludes_confirmed_investment(complete_snapshot, changes, eligibility, status):
    complete_snapshot["headquarters"].update(changes)
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["eligibility"] == eligibility
    assert report["fields"]["headquarters"]["status"] == status
    assert any(blocker.startswith("headquarters:") for blocker in report["blockers"])


@pytest.mark.parametrize(("current_sga", "investigate"), [(11, False), (12.5, True), (20, True)])
def test_large_sga_growth_is_investigation_evidence_not_headquarters_proof(complete_snapshot, current_sga, investigate):
    complete_snapshot["fundamentals"]["sga"]["current"]["value"] = current_sga
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert ("sga_investigation" in report["flags"]) is investigate
    assert report["eligibility"] == "eligible"
    assert report["buy_allowed"] is True


@pytest.mark.parametrize(
    ("path", "value", "field"),
    [
        (("classification", "source"), None, "classification"),
        (("classification", "source"), [], "classification"),
        (("classification", "security_type"), [], "classification"),
        (("classification", "exchange"), [], "classification"),
        (("classification", "status"), "optimistic", "classification"),
        (("fundamentals", "trailing_pe", "value"), 10**400, "trailing_pe"),
        (("fundamentals",), None, "revenue"),
    ],
)
def test_malformed_field_evidence_returns_blockers_instead_of_crashing(complete_snapshot, path, value, field):
    target = complete_snapshot
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] in ("missing", "unreviewed", "incomparable")


@pytest.mark.parametrize("field", ["revenue", "sga"])
def test_overflowing_growth_is_unavailable_instead_of_infinite(complete_snapshot, field):
    complete_snapshot["fundamentals"][field]["current"]["value"] = 1e308
    complete_snapshot["fundamentals"][field]["prior_year"]["value"] = 1e-308
    report = coverage_report(complete_snapshot, "2026-10-09")
    assert report["buy_allowed"] is False
    assert report["fields"][field]["status"] == "incomparable"
    assert report["normalized"][f"{field}_growth"] is None


@pytest.mark.parametrize(("as_of", "expected_cutoff"), [("2026-10-09", "2026-10-09T16:00:00-04:00"), ("2026-10-09T22:00:00Z", "2026-10-09T18:00:00-04:00")])
def test_report_preserves_actual_decision_cutoff_for_portfolio_timing(complete_snapshot, as_of, expected_cutoff):
    if "T" in as_of:
        complete_snapshot["fundamentals"]["revenue"]["current"]["source"]["available_at"] = "2026-10-09T21:00:00Z"
    report = coverage_report(complete_snapshot, as_of)
    assert report["buy_allowed"] is True
    assert report["as_of"] == "2026-10-09"
    assert report["decision_cutoff"] == expected_cutoff


def test_latest_period_verification_after_decision_is_future(complete_snapshot):
    complete_snapshot["latest_reported_period"]["verified_as_of"] = "2026-10-10"
    original = deepcopy(complete_snapshot)

    report = coverage_report(complete_snapshot, "2026-10-09")

    assert report["buy_allowed"] is False
    assert report["fields"]["latest_reported_period"]["status"] == "future"
    assert "latest_reported_period:future" in report["blockers"]
    assert report["normalized"]["revenue_growth"] is None
    assert report["fields"]["latest_reported_period"]["evidence"]["source"] == original["latest_reported_period"]["source"]
    assert complete_snapshot == original


def test_headquarters_clearance_reviewing_future_dates_is_future(complete_snapshot):
    complete_snapshot["headquarters"]["lookback_end"] = "2026-10-10"
    original = deepcopy(complete_snapshot)

    report = coverage_report(complete_snapshot, "2026-10-09")

    assert report["buy_allowed"] is False
    assert report["fields"]["headquarters"]["status"] == "future"
    assert "headquarters:future" in report["blockers"]
    assert report["fields"]["headquarters"]["evidence"]["source"] == original["headquarters"]["source"]
    assert complete_snapshot == original
