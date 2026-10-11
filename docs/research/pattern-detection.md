# Automatic daily-chart pattern detection

Research date: 2026-10-10. Scope: inverse head-and-shoulders and cup-and-handle entries, head-and-shoulders top exits, using the agreed [strategy](../strategy-v1.md).

## Finding and recommendation

The requested recognizers are feasible as small, deterministic programs that return their pivot points, neckline/resistance, completion date, and rule checks. Implement a conservative causal baseline using Python's standard library. Keep an optional numerical-library adapter behind the same interface if research later justifies it.

This research validates the definitions and implementation approach. It does **not** establish recognition accuracy on real charts or the strategy's returns. No Gary.ai recognizer or labeled chart corpus existed when this report was prepared, and no detector experiment was run for this report. The first development cycle can establish conformance to an explicit rule specification; real-chart validation remains a separate deliverable.

## Source findings

- A head-and-shoulders top has three peaks, a higher middle peak, roughly comparable shoulders, and two intervening troughs defining a neckline. Completion requires a neckline break. The inverse pattern reverses the geometry. This supports separating a forming shape from an executable completion event. [Fidelity chart-pattern presentation, slides 27–28](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/learning-center/Idenitfying-Chart-Patterns.pdf).
- A cup-and-handle follows an advance, has a rounded cup and a shallower handle, and completes with a resistance breakout. Fidelity describes approximately one to six months for the cup and one to four weeks for the handle, handle retracement usually no greater than one third of the cup's advance, and increased breakout volume. Its presentation also distinguishes a rounded cup from a V bottom and requires a break above both lips. These are useful definition anchors; they do not supply Gary.ai's exact algorithm. [Fidelity cup guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/cup-with-handle), [Fidelity presentation, slide 29](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/learning-center/Idenitfying-Chart-Patterns.pdf).
- Lo, Mamaysky, and Wang demonstrate systematic pattern recognition using nonparametric kernel regression and report some incremental information in conditional returns. Their definitions, samples, and statistical result do not validate Gary's entry gates, executions, or portfolio Sharpe. [Authors' NBER paper landing page](https://www.nber.org/papers/w7613).
- Research findings are not uniformly favorable: Osler's New York Fed equity study reports unprofitable head-and-shoulders trading in its studied setting. This is evidence to test efficacy separately, not an estimate for Gary.ai. [New York Fed Staff Report 42](https://www.newyorkfed.org/research/staff_reports/sr42.html).

## Open-source candidates and reuse decision

| Candidate | Verified capability or issue | Decision |
| --- | --- | --- |
| Standard-library local extrema and geometry | Small enough to implement against the visible contract and test dates explicitly. This is our proposed implementation, not an existing validated detector. | Preferred first cycle; own the rules and evidence. |
| SciPy `find_peaks` | Supplies neighbor comparisons, distance, prominence, width, and plateau properties. It does not supply the requested financial patterns. Prominence searches both sides of a peak, so full-series results need explicit availability treatment. SciPy's license is BSD-3-Clause. | Optional research primitive, not a required dependency or a ready-made trading signal. |
| TA-Lib | Official pattern catalogue lists candlestick `CDL*` functions; no requested multiweek head-and-shoulders or cup-and-handle function is listed. | Useful later for indicator context; does not solve this task. |
| `TradingPatternScanner` | Basic head-and-shoulders function uses next-row data through `shift(-1)` and short rolling comparisons rather than five-pivot geometry and neckline completion. Upstream license is CC BY-NC-SA 4.0. README accuracy figures describe synthetic evaluation. | Do not copy or adopt as a distributable dependency; its labels and reported accuracy are insufficient for this contract. |

Sources: [SciPy peak API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html), [SciPy prominence API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html), [SciPy license](https://github.com/scipy/scipy/blob/main/LICENSE.txt), [TA-Lib function catalogue](https://ta-lib.org/functions/), [TradingPatternScanner source](https://raw.githubusercontent.com/white07S/TradingPatternScanner/main/tradingpatterns/tradingpatterns.py), [upstream license](https://raw.githubusercontent.com/white07S/TradingPatternScanner/main/LICENSE.md), [upstream README](https://github.com/white07S/TradingPatternScanner).

Interpretation: permitting a noncommercial research copy would not make this a suitable dependency for Gary.ai's intended reusable MCP. A new implementation from the public shape definitions also avoids inheriting historical-row labels with unknown execution timing. No upstream detector code was copied.

## Proposed public contract

```text
detect_patterns(daily_bars, as_of) -> signals/evidence

daily_bars: list of {date, open, high, low, close, volume}
as_of: last completed trading-session date permitted as input

signal/evidence:
  kind: inverse_head_shoulders | cup_handle | head_shoulders_top
  direction: buy | sell
  status: completed | forming | ambiguous | invalid_data
  completion_date: session of qualifying close, or null
  available_at: session when all required observations became known
  breakout_level: evaluated neckline/resistance at completion, or null
  pivots: [{role, date, price, confirmed_on}]
  window_start, window_end
  checks: {rule_name: observed_value, limit, pass/fail/unknown}
  warnings, detector_version, parameter_hash, input_snapshot_id
```

The core may return completed events only in its first slice, with failures represented in a batch result. Whichever structure the plan chooses, callers must distinguish **no pattern** from **invalid/missing data**. `available_at` must never exceed `as_of`; completion cannot cause an earlier fill than availability. The adapter owns price-source identity, fetch time, session calendar, snapshot hash, and adjustment policy; the pure core owns shape evidence. Add source metadata to serialized results at that boundary rather than fetching data from inside this function.

Default geometry uses consistently split-adjusted OHLC, without mixing adjusted close with unadjusted highs/lows. Total-return adjustment is a separate policy for portfolio volatility and performance. Retain raw and adjusted source snapshots so corrections are reviewable. These are proposed data-contract choices; verify provider adjustment behavior in the coverage work.

Reject duplicate/out-of-order dates, nonfinite/nonpositive prices, impossible OHLC relationships, negative volume, missing required sessions, and incomplete current-session bars. Do not fill price gaps with invented bars. Missing volume makes a volume check unknown; missing price bars or unknown corporate-action treatment blocks completion. Decide the maximum permitted gap explicitly in the data adapter.

## Minimal causal recognition approach

### Pivot availability

At session `t`, inspect only bars through `t`. A pivot at `i` may be confirmed at `i + r` after observing `r` right-hand sessions; record both dates. Start with `r = 3` and three left-hand sessions. This is delayed confirmation, not permission to attribute a tradable event to the earlier pivot date.

Freeze each confirmed pivot with its input snapshot and parameters. Preserve alternating high/low swings, using deterministic rules for adjacent pivots of the same type and flat ties. A later higher high can supersede an **unconsumed candidate**, but cannot erase a previously emitted event. Replay the same causal state transitions in both live and historical evaluation.

Avoid centered smoothing over the entire historical series and ZigZag-style retrospective redraws. A centered local comparison is usable only when its right-hand observations are already available and the output retains its confirmation delay. Global peak prominence, smoothing, or distance selection can also change old labels as future data arrives; freezing availability is essential. This implementation warning follows from the documented two-sided peak/prominence operations, not from a measured Gary.ai failure. [SciPy peak API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html), [SciPy prominence API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html).

### Head-and-shoulders geometry and completion

Match five chronological alternating pivots. A top is peak–trough–higher peak–trough–peak; the inverse is trough–peak–lower trough–peak–trough. Require meaningful head separation, similar shoulder levels, reasonable spacing, and a neckline whose slope is bounded relative to pattern depth. Calculate the neckline as a line through the two intervening pivots using trading-session indexes.

Confirm the right shoulder before issuing the signal. Freeze the neckline and anchors. Require the first daily close crossing below the top neckline or above the inverse neckline by the configured buffer, with the previous close on the other side. If an apparent crossing predates required pivot availability, do not backdate it. The conservative baseline should require a new eligible crossing rather than pretend a historical fill occurred.

Prior trend is evidence for a reversal: record a preceding rise for a top and decline for an inverse. Keep moving averages and relative strength as chart context unless the strategy explicitly adds them as entry gates. Volume expansion is supporting evidence, not yet a mandatory Gary rule.

### Cup-and-handle geometry and completion

Require a prior advance, two comparable rim prices, a sufficiently long cup, a central low, and sustained occupancy near its bottom. Reject a V that touches its low for only one or two sessions. Use explicit duration, depth, time-to-bottom, rim similarity, and rounding checks rather than a single goodness-of-fit score. A quadratic fit alone can mistake a V or arbitrary dip for a cup.

After the right rim, require a bounded handle with a real pullback and recovery. Keep its low in the upper portion of the cup and limit its retracement relative to the cup's rise. Complete only after the handle and a new daily close above the maximum of both rims and the handle's earlier highs, plus the breakout buffer. The comparison must exclude the breakout day's own high; otherwise it can become impossible or self-referential.

Record breakout volume divided by the median of the preceding 20 sessions, excluding the completion day. This makes the volume context inspectable. A ratio threshold is a research parameter, not a rule Gary has supplied. The first conservative paper implementation may report volume confirmation without making it an extra trading gate.

### Provisional parameters to freeze before the first TDD slice

The numbers below are proposed engineering defaults and sensitivity ranges. They are **not** validated values, investment recommendations, or claims that Gary uses them. Exact boundary behavior belongs in the frozen test contract.

| Rule | Starting point | Bounded research range |
| --- | --- | --- |
| Left/right pivot sessions | 3 / 3 | 2–5 each |
| H&S first-to-last pivot duration | 20–126 sessions | 15–160 |
| Shoulder price difference | At most 25% of head-to-neckline depth | 15–35% |
| Head beyond each shoulder | At least 10% of head-to-neckline depth | 10–25% |
| Left/right time-span ratio | 0.5–2 | 0.4–2.5 |
| Neckline anchor price difference | At most 25% of pattern depth | 15–40% |
| Breakout buffer | 0.5% of boundary price | 0–1%; test raw crossing separately |
| Cup duration | 20–126 sessions | 20–160 |
| Cup depth / rim price | 5–40% | 5–45% |
| Rim difference | At most 10% of cup depth | 5–20% |
| Cup low location | Middle third of cup duration | Middle 40% |
| Sustained rounded bottom | At least 5 sessions within bottom 20% of cup depth | 3–10 sessions, 15–30% depth band |
| Handle duration | 5–20 sessions | 5–30 |
| Handle retracement / cup rise | Positive, at most one third | Test 20–33% maximum |
| Prior cup advance | Positive return over 20 sessions before left rim | Report magnitude; test 5–15% threshold only as a separate hypothesis |
| Volume confirmation context | Breakout volume / prior 20-session median | Research 1.2–2.0; no initial mandatory ratio |

Do not tune all combinations to maximize historical returns. Start with one frozen specification, inspect errors, and compare a few preregistered alternatives on a separate calibration set. For ambiguous overlapping or opposing patterns, emit the ambiguity and suppress a new buy; deterministic exit precedence belongs in the portfolio contract. Consolidate overlapping same-direction detections into one event with alternate evidence. Event identity combines security, kind, anchor dates, completion/availability date, and detector version so daily refreshes cannot create repeated orders.

## Validation protocol

### Layer 1: implementation recognition tests

Synthetic regression fixtures verify the agreed geometry, not market accuracy. Begin with a clear positive and near-miss negative for every pattern. Include incomplete patterns, equal-price ties, shoulder inequality, steep necklines, wrong head orientation, excessive handle depth, insufficient cup duration, V bottoms, no prior cup rise, neckline touches, intraday-only crossings, and failed breakout recrosses.

Add causal invariants: no event before confirmation; future appended bars cannot create or alter previously emitted events when replayed as of the same date; truncated and full-history inputs filtered to the same `as_of` agree; multiplying all prices by a positive constant preserves relative geometry; a split-normalized series does not create a spurious pattern; invalid data is never silently treated as a no-pattern result. Include a signal on the final available bar and a breakout that occurs before the right shoulder is confirmed.

### Layer 2: real-chart recognition study

Create a fixed, versioned cohort of eligible US operating-company common stocks and session windows before viewing detector outputs. Include quiet trends, noisy ranges, earnings gaps, splits, high/low volatility, near misses, and examples from different sectors. Do not select only surviving winners or only shapes the program already found.

Annotators see charts clipped at the candidate decision date, with future prices, symbol, realized return, and detector labels hidden. They record pattern type, anchors, completion date, and `uncertain`. Have Gary and an independent reviewer label a subset; preserve disagreements rather than forcing a convenient truth. Gary's feedback is useful for strategy alignment, but developer-generated labels alone are not an independent validation set.

Separate an earlier calibration period from a later locked holdout, and embargo overlapping price windows across the boundary. Hold out some securities as well. Use an independently labeled random-window sample to estimate missed patterns; a candidate-only sample can estimate precision but cannot estimate recall. Also sample predicted positives for a realistic false-positive review workload and preserve sampling probabilities if combining the two samples.

Report per-pattern precision, recall, count, uncertainty interval, completion-date error, detection delay, abstention rate, and agreement between annotators. Match events by preregistered anchor/date tolerances and deduplicate overlapping windows. Report false detections per 1,000 security-sessions in addition to class metrics. There is no evidence yet to claim a numerical accuracy target has been reached. Keep the engine marked experimental until the locked sample is scored and its error report is reviewed.

### Layer 3: trading efficacy

Recognition quality and profitable investing are different endpoints. Only after data and labels pass their gates, compare Gary's complete strategy with the same fundamentals/allocation policy without pattern timing. Use available-at fundamentals, a historical universe, next-session execution, dividends, costs, gaps, delistings, and all portfolio-loss rules. Keep return/Sharpe tests separate from geometry calibration; examine turnover, coverage, cash drag, and drawdowns. A synthetic chart test cannot substantiate the five-year Sharpe objective.

## What can be validated in the first cycle

| Claim | Current status | Next evidence |
| --- | --- | --- |
| Definitions can be made explicit | Supported by primary source definitions | Freeze the first parameter contract |
| Open-source tooling supplies a suitable ready-made detector | Not established; inspected candidates are inadequate for this contract | Build a minimal original deterministic baseline |
| Causal timing and requested geometry are implemented correctly | Not yet tested | Red/green tests plus independent QA and prefix replay |
| Detector agrees with Gary on real charts | Unknown | Blinded, date-clipped labels and held-out evaluation |
| Detector improves portfolio Sharpe or losses | Unknown | Point-in-time portfolio comparison after recognition study |

Recommended first deliverable: a tested pure detector with evidence, a visible experimental-status label, and a reproducible real-chart labeling queue. This moves implementation forward without claiming the empirical results are already known.
