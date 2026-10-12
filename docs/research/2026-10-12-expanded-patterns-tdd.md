# Expanded signals TDD

The user-approved seams under test are `gary.patterns_v2.detect_patterns(bars, as_of)` and `gary.portfolio.step_portfolio(state, market, as_of)`. The October 12 watch-and-signals contract supplies the thresholds and direction policy. Tests use explicit synthetic bars and public calls; no internal collaborators are mocked. The frozen v1 detector is the reference for preserving existing geometry and evidence.

Warm-up follows the confirmed contract literally: breaking out requires 21 prior bars (22 including the candidate), and rolling over requires 51 prior bars (52 including the candidate). This intentionally preserves the stated sufficiency even though a pair of 50-session averages alone could be calculated from 51 total bars. Gapping up requires two bars.

## Observed RED / GREEN cycles

Commands ran with the existing local environment, without dependency installation. Each implementation slice below first failed through its public seam, then passed after the minimal behavior change.

| Slice | RED command suffix after `.venv/bin/python -m pytest` | Observed RED | GREEN |
| --- | --- | --- | --- |
| Preserve all three existing geometries and evidence, with expanded stamp | `tests/test_patterns_v2.py -q` | Missing `gary.patterns_v2` module | 3 passed |
| Completed breakout excluding current high; volume is evidence | `tests/test_patterns_v2.py -q -k completed_breakout` | No breakout event | 4 detector tests passed |
| Breakout first crossing versus corresponding previous channel | `tests/test_patterns_v2.py -q -k breakout_continuation` | Duplicate continuation event | 5 detector tests passed |
| Strict half-percent close confirmation | `tests/test_patterns_v2.py -q -k exact_half_percent` | Exact 100.5 close on 100 resistance emitted | 6 detector tests passed |
| Completed rollover, prior lows and 50-session average evidence | `tests/test_patterns_v2.py -q -k completed_rollover` | No rollover event | 7 detector tests passed |
| Falling average required; rising/flat average excludes | `tests/test_patterns_v2.py -q -k without_falling` | Rising-average breakdown emitted | 8 detector tests passed |
| Rollover first crossing versus corresponding previous channel | `tests/test_patterns_v2.py -q -k rollover_continuation` | Duplicate continuation event | 9 detector tests passed |
| Exact 2% opening gap is a completed observation after reversal | `tests/test_patterns_v2.py -q -k exact_two_percent` | No gap observation | 10 detector tests passed |
| Combined event chronology | `tests/test_patterns_v2.py -q -k completion_order` | Earlier gap followed later breakout in reverse date order | 11 detector tests passed |
| Breakout is an admissible next-session paper entry | `tests/test_portfolio.py -q -k confirmed_breakout` | Empty orders | 1 selected test passed |
| Rollover exits every share, without same-cycle repurchase | `tests/test_portfolio.py -q -k completed_rollover` | Empty orders | 63 combined detector/paper tests passed |
| Flat decimal-price SMA must remain flat | `tests/test_patterns_v2.py -q -k decimal_prices` | Equal averages (49 closes at 1.7 and one at 0.1; exact mean 1.668) emitted a rollover because sums depended on term order | 139 targeted detector/legacy/paper tests passed |

The breakout boundary uses Decimal comparisons of the supplied numeric values' strings. This honors strict decimal price thresholds without introducing a tolerance. The two SMA values use `statistics.mean`, avoiding the observed sum-order artifact. Gap comparisons are inclusive at 2%.

The gap slice revealed an overly broad earlier test assertion: the rising-average fixture legitimately had a gap on a different day. That test now asserts absence of `rolling_over`, allowing the independently approved observation. The first paper-buy test initially assumed a `reasons` field in buy orders; inspection of the existing public result corrected that assertion to its unchanged order schema.

Supplemental public-seam controls passed without further implementation changes: 22/52/2-bar warm-up boundaries, completed-session availability, future-prefix invariance (including invalid future OHLCV), unchanged inputs, exact breakdown boundary, a sub-2% gap, same-session gap plus breakout, invalid permitted data, actual detector-to-paper entry/exit, and existing fundamental/timing/volatility/allocation guards. A gap-only observation with passing fundamentals produces neither a buy nor a technical exit, tested with affordable 100-share blocks and with an existing 300-share holding.

Final targeted command:

```text
.venv/bin/python -m pytest tests/test_patterns_v2.py tests/test_patterns.py tests/test_portfolio.py -q
139 passed in 0.09s
```

## Stamps and preservation

Exported `VERSION`: `expanded-signals-v1`.

Exported `PARAMETER_HASH`: `ac066c5ba8db00a9b5613cda1313152a10ebfbb671cc476a65d06fae8152afc4`.

The parameter manifest includes the frozen v1 source SHA along with its version, plus the confirmed channel, warm-up, average, gap and availability settings. Existing geometry events are obtained through the original public detector and receive only the new version/hash stamp.

SHA-256 before and after implementation:

| Frozen file | SHA-256 |
| --- | --- |
| `src/gary/patterns.py` | `76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a` |
| `src/gary/review.py` | `aec0b6a02a80da2fd46cbe1a2b58b87382e31f6fd108b9071cfa017042fd3d19` |
| `src/gary/evaluation.py` | `1f2b9d04aec3af8a39731af2d2d6d9f1c6cb522b3313b9570a1cd3f7290a9757` |

Only the five assigned files were edited. Portfolio implementation changes are limited to admitting `breaking_out` and recognizing `rolling_over`; selection, allocation and stop behavior retain their existing implementation.

## Limits

All added controls use synthetic prices and explicit context. No real data, historical studies, review labels, paper run/reset or real order was changed or generated. These tests establish implementation behavior, not recognition accuracy or investment performance. The application adapter and UI integration are handled separately by the parent task. Historical recognition and the legacy demo continue to call v1.
