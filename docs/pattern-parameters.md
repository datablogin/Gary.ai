# Detector v1 parameter contract

Frozen before the first behavior test on 2026-10-10. Interface: `detect_patterns(bars, as_of)` returns completed historical events through the permitted date; invalid permitted data raises `ValueError`. Later-dated OHLCV does not affect the result. Dates must be ISO calendar dates; permitted bars must be strictly increasing and unique. OHLC must be positive finite numbers, within low/high, with nonnegative finite volume. Booleans are not prices. Inputs are not mutated.

These are provisional engineering definitions, not calibrated probabilities, Gary's exact visual judgment, or empirical accuracy claims. The source definitions and separate real-chart validation protocol are in [research](research/pattern-detection.md). Fixtures and initial preview are synthetic. No market calendar is inferred: the caller supplies completed consecutive trading-session bars and consistently split-adjusted OHLC.

## Head-and-shoulders

- Close-based extrema: 3 strictly lower/higher neighboring closes on each side; confirmation is 3 sessions after the pivot. Equal-close plateaus are not pivots in v1. Adjacent extrema of the same orientation retain the more extreme candidate; emitted events are immutable.
- Five alternating pivots: trough/peak/trough/peak/trough for inverse, peak/trough/peak/trough/peak for top. First-to-last duration 20–126 sessions inclusive. Left-shoulder/head and head/right-shoulder duration ratio 0.5–2 inclusive.
- Neckline is the line between the intervening pivots, using session indexes. Depth is the distance between head and neckline at the head date, positive. Shoulders differ by no more than 25% of depth; head lies beyond each shoulder by at least 10% of depth; neckline anchors differ by no more than 25% of depth.
- Prior 20-session close return ending at the left shoulder must be negative for inverse and positive for top. No minimum magnitude. The prior trend is a provisional recognition context rule, independent of Gary's fundamental gates.
- Completion needs a new close above inverse neckline × 1.005, or below top neckline × 0.995. The previous close must be on the opposite side of its own date's buffered neckline. All pivots must already be confirmed. No retroactive completion. Candidate expires more than 30 sessions after right shoulder; a new close beyond the head invalidates an uncompleted candidate.

## Cup-and-handle

- A confirmed high, confirmed low and confirmed high identify left rim, bottom and right rim. Cup duration 20–126 sessions inclusive; bottom lies in the middle third. Prior 20-session return ending at left rim must be positive.
- Cup depth is lower rim minus bottom close, 5–40% of lower rim. Rims differ by no more than 10% of depth. At least 5 cup sessions lie within bottom + 20% of depth. This explicit sustained-bottom check distinguishes the v1 bowl definition from a single V; it is not a universal definition of roundedness.
- Handle must last 5–20 sessions after right rim and before breakout, have a confirmed low, positive retracement no greater than one third of right-rim-to-bottom rise, and a recovering close above its low before breakout. A new low below the permitted handle band invalidates that cup candidate.
- Completion needs a new close above 1.005 × maximum(left rim, right rim, pre-breakout handle closes). The breakout session is excluded from resistance calculation. The previous close must not already exceed that same boundary. No event before right rim and handle-low confirmation.
- Volume is evidence only: completion volume / median volume over the 20 preceding sessions, or null if the median is zero. No required volume ratio is added to Gary's entry policy.

## Event evidence and invariants

Signals contain `kind`, `direction`, `status="completed"`, `completion_date`, `available_at`, `breakout_level` (unbuffered boundary), `pivots` (`role`, `date`, `price`, `confirmed_on`), `checks`, `detector_version`, `parameter_hash`, `window_start`, and `window_end`. Confirmation and completion availability use completed-session dates. `available_at` equals the completion date for the causal replay. Historical events stay unchanged when later bars arrive. A shape emits at most once; geometrically distinct shapes can emit on the same date, so the portfolio must still deduplicate orders by symbol.

All proportional comparisons are scale invariant. Boundary checks use a small floating-point relative tolerance for geometric ratios, not a relaxed breakout threshold. Volume ratios are not probabilities. Network fetching, security classification, fundamentals, exchange calendars, adjustment audits, and fills belong outside this pure detector.
