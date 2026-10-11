# Coverage snapshot v1

The approved pure seam is `coverage_report(snapshot, as_of)`. It returns `symbol`, `as_of`, `decision_cutoff`, `eligibility` (`eligible`, `excluded`, `unknown`), `buy_allowed`, `blockers`, `normalized`, per-field `fields`, and investigation `flags`. JSON inputs and outputs are independent of a provider. This first slice evaluates explicitly validated observations; it does not extract complete SEC statements.

`as_of` is a completed-session ISO date, interpreted at 16:00 America/New_York, or an ISO timestamp with an explicit offset. The result's `as_of` is the corresponding New York date, while `decision_cutoff` preserves the actual decision instant as a New York offset timestamp. For example, `2026-10-09T22:00:00Z` returns `decision_cutoff: 2026-10-09T18:00:00-04:00`; it must not be presented as a report available at that day's close. The portfolio rejects any report cutoff after the prior signal session's 16:00 close. Publication timestamps must be no later than the cutoff. Date-only publication is usable only on a later date, conservatively preventing same-day unknown publication time from clearing entry. Every observation/evidence record has a `source` object with nonempty `url`, `available_at` (date or timestamp), and `fetched_at` (offset timestamp). Fetch time is provenance, not publication time.

The schema is frozen before the first behavior test. Example values below are synthetic fixture evidence, not real market opportunities:

```json
{
  "symbol": "DEMO",
  "classification": {
    "security_type": "operating_common",
    "exchange": "NASDAQ",
    "reviewed": true,
    "source": {"url": "synthetic://classification", "available_at": "2026-10-08", "fetched_at": "2026-10-09T19:00:00Z"}
  },
  "headquarters": {
    "state": "reviewed_no_disqualifying_evidence",
    "reviewer": "synthetic fixture",
    "lookback_start": "2025-10-09",
    "lookback_end": "2026-10-09",
    "source": {"url": "synthetic://headquarters", "available_at": "2026-10-08", "fetched_at": "2026-10-09T19:00:00Z"}
  },
  "latest_reported_period": {
    "period_start": "2026-04-01",
    "period_end": "2026-06-30",
    "verified_as_of": "2026-10-09",
    "source": {"url": "synthetic://latest-filing", "available_at": "2026-08-01T12:00:00Z", "fetched_at": "2026-10-09T19:00:00Z"}
  },
  "fundamentals": {
    "trailing_pe": {
      "value": 20,
      "valid_through": "2026-10-09",
      "source": {"url": "synthetic://quote", "available_at": "2026-10-08", "fetched_at": "2026-10-09T19:00:00Z"}
    },
    "dividend_yield": {
      "value": 3,
      "unit": "percent",
      "convention": "indicated_regular",
      "policy_reviewed": true,
      "valid_through": "2026-10-09",
      "source": {"url": "synthetic://dividend", "available_at": "2026-10-08", "fetched_at": "2026-10-09T19:00:00Z"}
    },
    "revenue": {
      "comparability_reviewed": true,
      "current": {"value": 120, "currency": "USD", "scope": "consolidated", "period_type": "quarter", "period_start": "2026-04-01", "period_end": "2026-06-30", "source": {"url": "synthetic://current", "available_at": "2026-08-01T12:00:00Z", "fetched_at": "2026-10-09T19:00:00Z"}},
      "prior_year": {"value": 100, "currency": "USD", "scope": "consolidated", "period_type": "quarter", "period_start": "2025-04-01", "period_end": "2025-06-30", "source": {"url": "synthetic://prior", "available_at": "2025-08-01T12:00:00Z", "fetched_at": "2026-10-09T19:00:00Z"}}
    },
    "sga": {
      "comparability_reviewed": true,
      "current": {"value": 11, "currency": "USD", "scope": "consolidated", "period_type": "quarter", "period_start": "2026-04-01", "period_end": "2026-06-30", "source": {"url": "synthetic://current-sga", "available_at": "2026-08-01T12:00:00Z", "fetched_at": "2026-10-09T19:00:00Z"}},
      "prior_year": {"value": 10, "currency": "USD", "scope": "consolidated", "period_type": "quarter", "period_start": "2025-04-01", "period_end": "2025-06-30", "source": {"url": "synthetic://prior-sga", "available_at": "2025-08-01T12:00:00Z", "fetched_at": "2026-10-09T19:00:00Z"}}
    }
  }
}
```

Known excluded security types are `adr`, `reit`, `bdc`, `spac`, `etf`, `fund`, `preferred`, `unit`, and `warrant`. Other/absent types remain unknown. Eligible common stocks require an independent reviewed classification and an explicitly supported US exchange (`NYSE`, `NASDAQ`, `NYSE_AMERICAN`, `NYSE_ARCA`, `CBOE_BZX`); a vendor `EQUITY` label is insufficient.

PE and yield require a caller-reviewed `valid_through` date; an expired quote is stale. The yield convention must be explicitly `trailing_cash` or `indicated_regular`, with `policy_reviewed: true`. This supports normalization without selecting a permanent convention for Gary. A percent value 3 normalizes to 0.03; a fraction value 0.03 stays 0.03. Missing/null numbers remain unavailable. Gates are strictly positive PE below 30, fractional yield above 0.02, and quarterly revenue growth above 0.15.

Financial pairs require reviewed comparability, explicit consolidated currency/scope, `period_type: quarter`, each duration 60–110 calendar days, prior-year end dates 350–380 days apart, corresponding start/end calendar months, and durations differing by no more than three days. Longer YTD observations, incompatible currency/scope, nonpositive comparison bases, future periods and extra fiscal weeks block normalization. These conservative checks can abstain on unusual fiscal periods; broader fiscal mappings need later explicit validation. `latest_reported_period` requires filing-aware verification through `as_of`; its exact start/end must match both current revenue and SG&A. It must not be a vendor guess about the latest period.

Headquarters clearance requires the explicit reviewed state, reviewer, bounded lookback dates ending on `as_of`, and dated source evidence. A lookback end after the decision date is `future`, and earlier coverage is incomplete. Latest-period `verified_as_of` likewise must equal the decision date: an earlier date is stale and a later date is future verification. Later retrieval timestamps remain provenance and are not automatically future publication. These cycle-2 guards prevent claiming a review of future information. `confirmed_investment` excludes; unknown/incomplete review blocks. The lookback start is a caller-reviewed snapshot policy, not a newly invented Gary rule. Comparable SG&A growth at or above 25% creates `sga_investigation`; it alone does not prove headquarters investment or exclude a stock.

An optional record `status` can explicitly report `access_failure`, `missing`, `stale`, `incomparable`, `future`, or `unreviewed`; such records cannot clear entry. The report preserves sources and periods in `fields`. Invalid top-level inputs/cutoffs raise `ValueError`; field-level malformed evidence is reported as a blocker. Inputs are never mutated. A complete report may still fail strategy thresholds. `buy_allowed` is true only when classification, headquarters, sources, freshness/comparability and all fundamental gates pass.

The probe CLI defaults to summaries of ignored pilot artifacts under `private/coverage`, printing statuses and counts rather than raw vendor payloads. Cached research is distinct from this normalized schema and cannot produce an automatic buy clearance. Optional live probes are bounded and record failures honestly.
