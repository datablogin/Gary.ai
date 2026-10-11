# Pattern detector TDD evidence

2026-10-10. Approved seam: `detect_patterns(bars, as_of)`. Parameter contract was written before the first test. All fixtures are synthetic; these results establish specified behavior, not real-chart precision, recall, or trading efficacy. No detector library code was copied.

| Behavior / command selector (`uv run pytest tests/test_patterns.py::<selector> -q`) | Observed red | Observed green |
| --- | --- | --- |
| `test_invalid_permitted_ohlc_raises_instead_of_returning_no_pattern` | 1 failed: expected `ValueError` was not raised by callable stub | 1 passed after permitted OHLCV validation |
| `test_duplicate_permitted_session_is_rejected` | 1 failed: duplicate date did not raise | 1 passed after prefix date ordering validation |
| `test_completed_inverse_returns_causal_neckline_evidence` | 1 failed: returned no signals | 1 passed after causal inverse five-pivot/neckline replay |
| `test_inverse_rejects_unequal_shoulders_near_miss` | 1 failed: asymmetric shoulders produced a signal | 1 passed after shoulder similarity guard |
| `test_completed_top_returns_sell_after_neckline_breakdown` | 1 failed: returned no top signal | 1 passed after top orientation and downside crossing |
| `test_short_inverse_shape_is_not_a_multiweek_pattern` | 1 failed: 15-session shape emitted | 1 passed after 20-session duration floor |
| `test_inverse_requires_a_preceding_decline` | 1 failed: preceding rise admitted | 1 passed after signed prior-trend guard; initial test drawing lacked a left pivot and was corrected before this red |
| `test_head_must_stand_out_from_shoulders` | 1 failed: head separation below 10% of depth emitted | 1 passed after separation guard |
| `test_head_shoulders_rejects_extreme_time_asymmetry` | 1 failed: 1:3 time spans emitted | 1 passed after time-ratio guard |
| `test_head_shoulders_rejects_steep_neckline` | 1 failed: 6/23 neckline-depth change emitted | 1 passed after neckline-slope guard |
| `test_new_low_invalidates_uncompleted_inverse` | 1 failed: old candidate survived new low | 1 passed after causal invalidation |
| `test_old_uncompleted_inverse_expires_before_late_crossing` | 1 failed: old candidate emitted after 30-session validity | 1 passed after expiry |
| `test_completed_cup_returns_handle_and_volume_evidence` | 1 failed: returned no cup | 1 passed after confirmed cup/handle detection; subsequent full-suite regression exposed missing handle-depth guard |
| `test_cup_rejects_deep_handle_near_miss` | 1 failed: 50% handle retracement emitted | 1 passed after one-third maximum; the full suite also recovered to 14 passed |
| `test_single_v_is_not_a_rounded_cup` | 1 failed: single V emitted | 1 passed after sustained-bottom requirement |
| `test_cup_rejects_dissimilar_rims` | 1 failed: unequal rims emitted | 1 passed after rim-depth similarity guard |
| `test_cup_bottom_must_be_central` | 1 failed: bottom in first quarter emitted | 1 passed after central-time requirement |
| `test_cup_duration_outside_contract_is_rejected` | 2 failed: 15- and 140-session cups emitted | 2 passed after duration bounds |
| `test_cup_depth_outside_contract_is_rejected` | 2 failed: 4% and 50% cups emitted | 2 passed after depth bounds |
| `test_non_list_bars_raise_public_validation_error` | 1 failed: leaked `TypeError` instead of public validation error | 1 passed after list validation |
| `test_inclusive_shoulder_boundary_survives_price_rescaling` | 1 failed: 0.003 price rescaling rejected an inclusive 25% shoulder boundary | 1 passed after relative floating-point boundary tolerance |

## Additional verification

Public-seam verification controls were added after those capabilities existed; they passed on their first runs and are not represented as additional red/green development cycles. They cover all three uncompleted shapes, the top's unequal-shoulder near miss, a breakout before right-shoulder confirmation, malformed future OHLCV ignored at the cutoff, appended-future/prefix invariance, scale invariance for all three shapes, intraday-only breakout rejection and unchanged caller inputs.

Final command at developer handoff: `uv run pytest tests/test_patterns.py -q` → **42 passed**. Independent QA has not yet reported at this handoff. The rule hash includes every numeric window/geometry threshold, pivot field, plateau policy and floating-point tolerance; geometry is `causal-geometry-v1`.

## Bounded cached real-data scan

Ran the public detector through `as_of=2026-10-09` on the eight cached five-year Yahoo chart responses from the coverage pilot. Each contained 1,255 bars, 10,040 input bars total. Detector traversal took **0.05515 seconds** on this execution host; that excludes downloading and is not a full-universe throughput claim.

| Symbol | Inverse H&S | Cup/handle | H&S top |
| --- | ---: | ---: | ---: |
| MU | 0 | 0 | 0 |
| AMGN | 0 | 0 | 0 |
| SIRI | 0 | 0 | 0 |
| META | 0 | 0 | 1 |
| ORCL | 1 | 0 | 1 |
| TSM | 0 | 0 | 1 |
| O | 1 | 0 | 0 |
| ARCC | 0 | 0 | 1 |
| Total | 2 | 0 | 4 |

These six events are **unlabeled historical hypotheses**. They are not current trade opportunities, passing fundamental candidates, recognition precision/recall, or evidence of efficacy. TSM, O and ARCC are exclusion controls, not eligible investments. Zero cup detections cannot distinguish strict/insensitive geometry from absent qualifying shapes without independent labels.

Price basis: cached Yahoo provider OHLC/Close; this scan did not use Adj Close or apply dividend adjustment. Corporate-action/price-adjustment and exchange-calendar reconciliation were not validated. Current downloaded historical prices can include later corrections, so this is not point-in-time market-data proof. Source hashes and private event evidence are retained in ignored `private/pattern-scan.json`; only counts are included here. Source acquisition/coverage limits are in [data research](../research/data-coverage.md).
