# Historical holdout: five-year context data

Research date: October 11, 2026, America/Chicago. All eight authorized Yahoo requests returned HTTP 200 between `2026-10-11T15:11:41.960354+00:00` and `2026-10-11T15:11:44.299842+00:00`. Each response contains 2,514 daily rows from October 10, 2016 through October 9, 2026. This supports five-calendar-year returned history for all 13 original holdout endpoints, whose aggregate range is October 28, 2022 through October 7, 2026.

The requests followed [coverage_probe.py](../../src/gary/coverage_probe.py)'s Yahoo endpoint and `Gary.ai/0.1 personal-research` header, with `range=10y`, `interval=1d`, `events=div,splits`, a ten-second timeout and a 2 MiB per-response limit. Exactly one request was made per symbol; redirects and retries were disabled. No SEC, subscription or fundamentals requests were made.

| Primary Yahoo source | HTTP | Payload bytes |
| --- | ---: | ---: |
| [MU](https://query1.finance.yahoo.com/v8/finance/chart/MU?range=10y&interval=1d&events=div%2Csplits) | 200 | 272,358 |
| [AMGN](https://query1.finance.yahoo.com/v8/finance/chart/AMGN?range=10y&interval=1d&events=div%2Csplits) | 200 | 273,311 |
| [SIRI](https://query1.finance.yahoo.com/v8/finance/chart/SIRI?range=10y&interval=1d&events=div%2Csplits) | 200 | 258,391 |
| [META](https://query1.finance.yahoo.com/v8/finance/chart/META?range=10y&interval=1d&events=div%2Csplits) | 200 | 270,735 |
| [ORCL](https://query1.finance.yahoo.com/v8/finance/chart/ORCL?range=10y&interval=1d&events=div%2Csplits) | 200 | 274,189 |
| [TSM](https://query1.finance.yahoo.com/v8/finance/chart/TSM?range=10y&interval=1d&events=div%2Csplits) | 200 | 272,558 |
| [O](https://query1.finance.yahoo.com/v8/finance/chart/O?range=10y&interval=1d&events=div%2Csplits) | 200 | 279,094 |
| [ARCC](https://query1.finance.yahoo.com/v8/finance/chart/ARCC?range=10y&interval=1d&events=div%2Csplits) | 200 | 277,556 |

All eight sources pass full-array validation: timestamp, five OHLCV arrays and adjusted-close array lengths agree; dates and timestamps are strictly increasing and unique; every OHLCV value is finite; prices are positive, open/close lie within low/high, and volume is nonnegative. There are zero incomplete rows, invalid OHLCV rows or post-fetch session dates. Source identity, provider instrument type and exchange timezone were checked. Dates use the returned `America/New_York` timezone, following [_source_series](../../src/gary/review_preview.py).

For each original case, context uses `(as_of minus five calendar years, as_of]`, clamping a February 29 anniversary to February 28. All 13 sources span their case's full requested interval and reach the exact endpoint. Context counts range from 1,254 to 1,259 returned sessions: four cases have 1,254, three have 1,255, three have 1,256, one has 1,258 and two have 1,259. Exchange-calendar completeness was not independently reconciled.

For **13/13 cases**, every date and open/high/low/close/volume value in the final 180 context bars equals the immutable original `raw_window`, and those dates equal `visible_dates`. There are **zero mismatches**. No stitching, scaling, rounded comparison or adjusted-close substitution was used. The original recognition input and label protocol remain governed by [review.py](../../src/gary/review.py), [evaluation.py](../../src/gary/evaluation.py) and the [cycle 3 protocol](2026-10-10-cycle-3-protocol.md); longer display context does not authorize recomputing the frozen detector's answers.

Yahoo returned two split events across the eight responses: SIRI, September 10, 2024, ratio `1:10`; O, November 15, 2021, ratio `1032:1000`. Three longer case contexts intersect returned split metadata. These are provider-reported events, with no corporate-action adjustment certification. Empty split lists do not establish complete action coverage. These snapshots are retrospective downloads, with the [existing provider/point-in-time limitations](data-coverage.md).

Ignored evidence is under `private/holdout-context/sources/`: eight unchanged raw responses, `chart-probes.json`, `artifact-manifest.json` with SHA-256 and byte counts, `cases-validation.json`, and `validation-summary.json`. Case-specific source/cutoff mappings and comparisons remain private. The input projection used only `symbol`, `as_of`, `raw_window` and `visible_dates` from the original release's `holdout_queue`; predictions, scores and primary-label artifacts were not inspected. Frozen `review.py`, `evaluation.py` and `patterns.py` hashes were unchanged before/after this collection. No product/test edits, commits or pushes were made by this research task.
