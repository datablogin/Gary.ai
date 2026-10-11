# First research → TDD → local deployment → QA cycle

Date: 2026-10-10, America/Chicago. Human approved the three seams and the reviewed concrete plan. The team executed a bounded cycle; no scheduler or indefinite background loop was installed.

## Team and deliverables

- Research Dot: measured free-source coverage on eight securities, five operating examples and three exclusion controls. Durable [data report](../research/data-coverage.md).
- Pattern research/developer: primary-source definitions and license audit, then original causal geometry. [Research](../research/pattern-detection.md), [parameters](../pattern-parameters.md), [TDD evidence](pattern-tdd.md).
- Coverage developer: provider-independent snapshots, source/comparability/freshness gates, reviewed headquarters clearance and explicit access failures. [Schema](../coverage-schema.md), [TDD evidence](coverage-tdd.md).
- Coordinator/developer: paper daily execution, runtime and local preview. [TDD evidence](portfolio-tdd.md).
- Independent QA: standalone public-interface adversarial checks, integrated timestamp/prefix behavior, HTTP run/retry/reset checks. [Findings and rechecks](qa-findings.md).

Three non-author plan lenses reviewed feasibility, verifiability and scope/risk before human launch approval. Developers owned disjoint files; only the coordinator commits/pushes integrated work.

## Measured research verdict

- Eight of eight sampled five-year charts returned 1,255 complete rows; eight of eight P/E/dividend snapshots were present; five of five operating samples had vendor revenue/SG&A comparison pairs.
- SEC facts/submissions access succeeded for only one of eight sampled issuers. Seven access denials are access failures, not missing financials.
- MU's vendor latest quarter lagged a newer SEC filing. Dividend fields use different units/conventions. Broad equity labels admit excluded categories.
- Headquarters clearance was not validated for any of the five operating examples. No live sample was treated as automatically entry-cleared.
- Cached detector replay found two inverse and four top historical hypotheses, no cup hypotheses, across eight price series. These six outputs are unlabeled, not precision/recall results or current trade recommendations.

Free-access data is viable for a local prototype. Full-universe coverage, real-chart detection accuracy and strategy efficacy remain unvalidated.

## Implemented behavior and QA correction loop

The three pure interfaces evaluate explicitly evidenced snapshots, return causal completed-pattern hypotheses and execute a supplied-price paper step. The preview uses invented prices and synthetic reviewed evidence, with live coverage counts shown separately.

Independent QA found and reproduced stale report reuse, invalid volatility history, hidden gap stops with missing opens, future/absent sell completion, state limits, nonfinite sale accounting and loss of timestamp cutoff between coverage and portfolio. Each actionable defect gained an observed failing public-interface regression before correction. The coverage and portfolio cutoff fix preserves after-close timestamps instead of laundering them into a date-only clearance.

The missing-exit-price rule was corrected during plan review before coding: no state/threshold/date is consumed when required execution evidence is unavailable. Subsequent QA strengthened this to preflight every held opening price because it can affect gap stops.

## Verification evidence

`uv run pytest -q` completed with **230 passed**: coverage 138, patterns 42, portfolio 50. All tests exercise the approved interfaces. Synthetic fixtures establish conformance to frozen rules, not market accuracy. Detailed red/green commands and corrections are linked above.

QA checked all 251 synthetic decision-date prefixes independently, scaled inputs, invalid future OHLCV isolation, exclusion/missing/future/headquarters blockers, and portfolio numeric/retry behavior. The localhost HTTP path passed health, demo, run, duplicate-run, persistence, reset and external-origin rejection checks. Browser verification confirmed 300 paper shares at $22.40, $6,720 cost and $193,280 cash, with explicit synthetic/experimental labels.

Local deployment: `make preview` → http://127.0.0.1:4175. Initial state is $200,000 cash. Reset is available in the preview. Stop the foreground process with Ctrl-C. State and raw evidence remain ignored under `private/`; the preview is not a real brokerage and does not implement dividend/corporate-action total-return accounting.

## Acceptance check map

| Gate | Concrete evidence |
| --- | --- |
| Sample/source coverage | `make coverage`; data report measured matrix and ignored raw hashes |
| Classification/HQ/fundamental cutoff | `uv run pytest tests/test_coverage.py -q`; independent blocker and late-cutoff probes |
| Pattern geometry/causality | `uv run pytest tests/test_patterns.py -q`; independent all-prefix replay and unlabeled eight-symbol scan |
| Allocation/limits/stops/losses | `uv run pytest tests/test_portfolio.py -q`; independent numeric and invalid-input probes |
| Missing-price recovery/idempotency | Portfolio missing-price/retry selectors in portfolio-tdd.md; HTTP repeated run |
| Local preview | GET `/health`, GET `/api/demo`, POST `/api/run`, repeat, POST `/api/reset`; browser Holdings check |
| Persistence | Coordinator commit/push and `git ls-remote origin refs/heads/main` equality with HEAD |

## Next bounded cycle

Create a blinded real-chart labeling queue with clipped as-of charts, Gary/independent labels and a locked holdout. Review the six unlabeled hypotheses but also random non-detection windows so missed patterns can be measured. In parallel, resolve compliant SEC access and curated classification/headquarters evidence on an expanded sample. Do not tune to five-year returns while calibrating pattern recognition.

This cycle is complete when independent QA's final recheck passes and its integrated code/docs commit is verified on the remote. No investment results or live-money deployment are claimed.
