# Coverage seam TDD evidence

Schema: [coverage-schema.md](../coverage-schema.md), frozen before tests. All fixtures are synthetic. The sole tested seam is `coverage_report(snapshot, as_of)`. Numeric examples are worked independently: 120/100 gives 20% revenue growth; 11/10 gives 10% SG&A growth; 3 percentage points is fractional yield 0.03. Network calls are excluded from pytest.

Each command below is prefixed by `uv run pytest tests/test_coverage.py::` and suffixed by ` -q`.

| Behavior / exact selector | Observed red | Observed green |
| --- | --- | --- |
| `test_complete_curated_snapshot_reports_sources_and_passes_gates` | 1 failed: callable stub raised `NotImplementedError` | 1 passed |
| `test_classification_never_admits_excluded_or_unreviewed_securities` | 12 failed: every excluded/unknown control incorrectly eligible | 12 passed |
| Unavailable-evidence slice: `test_missing_required_evidence_blocks_without_inventing_values tests/test_coverage.py::test_provider_failures_remain_distinct_and_cannot_clear_entry` (also `--tb=short`) | 13 failed: absent and failed observations raised `KeyError` | 13 passed |
| `test_future_and_same_day_unknown_publication_block_every_evidence_gate` (also `--tb=short`) | 21 failed: future and same-day date-only evidence cleared entry | 21 passed |
| `test_source_without_valid_provenance_cannot_supply_clearance` (also `--tb=short`) | 4 failed, 2 passed: missing URL/fetch timestamp cleared entry | 6 passed |
| `test_missing_and_nonfinite_numbers_never_become_normalized_positives` (also `--tb=short`) | 20 failed: null/type errors and nonfinite/bool values were accepted | 20 passed |
| `test_quarter_growth_requires_real_comparable_prior_year_periods` (also `--tb=short`) | 20 failed: YTD/future/incompatible periods and nonpositive bases accepted (zero base raised division error) | 20 passed |
| `test_latest_filing_evidence_blocks_vendor_lag_and_unverified_periods` (also `--tb=short`) | 3 failed: latest period mismatch/old verification/future latest period cleared entry | 3 passed |
| `test_expired_or_unreviewed_quote_validity_cannot_clear_entry` (also `--tb=short`) | 6 failed: expired/absent/invalid quote validity cleared entry | 6 passed |
| `test_dividend_yield_requires_explicit_reviewed_units_and_convention` (also `--tb=short`) | 3 failed, 1 passed: unknown unit/convention and unreviewed policy normalized | 4 passed |
| `test_complete_data_still_must_pass_strict_fundamental_thresholds` (also `--tb=short`) | 7 failed: threshold boundary/nonpositive gates ignored | 7 passed |
| `test_headquarters_requires_positive_bounded_review_and_excludes_confirmed_investment` (also `--tb=short`) | 5 failed: unknown/incomplete review and confirmed investment cleared entry | 5 passed |
| `test_large_sga_growth_is_investigation_evidence_not_headquarters_proof` (also `--tb=short`) | 2 failed, 1 passed: 25%/100% SG&A investigation flag missing | 3 passed |
| `test_invalid_top_level_inputs_raise_explicit_value_error` (also `--tb=short`) | After repairing an initially misplaced test assertion: 5 failed, 1 passed; invalid input produced inconsistent exception/no error | 6 passed |
| `test_malformed_field_evidence_returns_blockers_instead_of_crashing` (also `--tb=short`) | 7 failed: malformed dictionaries/type metadata/huge number caused exceptions or unknown status | 7 passed |
| `test_overflowing_growth_is_unavailable_instead_of_infinite` (also `--tb=short`) | 2 failed: infinite normalized growth cleared entry | 2 passed |
| Independent integrated QA regression: `test_report_preserves_actual_decision_cutoff_for_portfolio_timing` (also `--tb=short`) | 2 failed: report lost the timestamp and had no `decision_cutoff` | 2 passed; exact decision instant is retained for the portfolio's close-time gate |

Final coverage suite: `uv run pytest tests/test_coverage.py -q` → **138 passed**. No network calls run in pytest. `git diff --check` passed.

CLI verification (separate from the three approved test seams):

- `uv run python -m gary.coverage_probe > private/coverage/current-cli-summary.json` reproduced the cached pilot: daily charts 8/8; SEC companyfacts and submissions 1/8 each; trailing PE/dividend fields 8/8; vendor quarterly revenue/SG&A pairs 5/5. It explicitly reports no verified latest-quarter clearance and `buy_allowed: false`, preserving fetch timestamps, source URLs and exact HTTP failures.
- `uv run python -m gary.coverage_probe --cache-dir /tmp/gary-no-cached-pilot` reported partial/unavailable cached artifacts and zero observed attempts, with no invented successful retrievals.
- `uv run python -m gary.coverage_probe --live --symbols UNKNOWN` exited 2 with an argument error before any network access.
- `uv run python -m gary.coverage_probe --live --symbols MU` made one request, no retries, at 2026-10-11T01:00:13.941952+00:00 (October 10 locally), received HTTP 200 and summarized 1,255 daily rows / 1,255 complete OHLCV rows. It retained `classification: unknown`, `fundamentals: unreviewed`, and `buy_allowed: false`. The response is ignored under `private/coverage/live/`; no raw Yahoo price dataset is committed or printed.

This validates curated-snapshot normalization and a bounded paper-prototype data workflow. It does not validate complete SEC extraction, all-universe coverage, headquarters clearance for the live sample, or economic correctness of vendor fields.
