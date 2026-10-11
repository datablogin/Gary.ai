# Holdout long-context scorecard

Outcome: all available historical holdout cards gain an honestly bounded five-year overview and unchanged 180-session detail, with separately attributed observations.

| Gate | Evidence |
| --- | --- |
| Context | Per-case open-left five-calendar-year interval, no future bars, minimum1200/start<=7days, exact frozen last180 reconciliation or anonymous study-unavailable status |
| Preservation | Original release, detector/review/evaluator bytes, old queues/journals and paper hashes unchanged |
| Provenance | New queue hash binds parent release plus overview; context label marker/hash and required exact view token; no old observations imported |
| Integrity | Runtime reconstruction from retained raw source manifest; immutable rebuild; tampering and source drift rejected |
| Projection | Indexed OHLCV/relative offsets only; no source/date/prediction/other-label leak; splits anonymous |
| Scoring | Context phase explicit; partial recognition null; noncertain exclusions; no original same-view accuracy claim |
| Workflow | Historical-end overview plus original detail; save/retry/revision/reload at assigned identity; old view read-only; stale/missing token rejected before write |
| Delivery | Public-seam red/green evidence, original311 tests green, independent QA/browser, pushed clean main |

Run `uv run pytest tests/test_context_review.py -q`, `make verify`, and `uv run python scripts/check_holdout_context.py`. Hash-only baseline: private/holdout-context/original-hashes.json; source evidence: private/holdout-context/sources/validation-summary.json. Record isolated HTTP and browser QA outcomes in completion evidence.
