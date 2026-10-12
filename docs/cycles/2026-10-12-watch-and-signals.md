# Radar, manual watch and expanded signals delivery

The user approved the initial daily rules, gap-as-observation direction, and persistent manual-watch interface on October12. This cycle adds distinct Radar and Manual watch sections to the stock desk, retaining the dated ten-stock non-buy snapshot. Each row has named checks, Why, source links and actual evidence dates. No personal tickers were seeded.

## Delivered behavior

- Radar requires complete reviewed coverage, resolved management flags and current chart evidence while awaiting a completed entry. Missing headquarters/accounting review remains outside Radar. A fresh technical exit requires stabilization/review.
- Manual add, optional note, duplicate retry, explicit market refresh and archived removal survive restart. Atomic private writes and process locks preserve membership; corrupt state errors rather than resetting it. Ticker/path/note validation runs before mutation.
- Expanded detection preserves original inverse head-and-shoulders, cup-and-handle and head-and-shoulders-top geometry, then adds first-crossing breaking-out buys and rolling-over sells. Gapping up is an inclusive2% opening observation and never creates an order alone. Only completed permitted sessions contribute. Exact half-percent channel crossings do not qualify.
- The paper daily-step interface admits breaking out under existing buy guards and exits all shares on rolling over. No real order or paper run/reset was executed.
- Background source checks retain private raw receipts, daily/chart cutoff, quote observations and separate quarterly observation dates. Old quote values cannot inherit a fresh chart receipt after a failed quote refresh. Primary quarterly links remain visible.
- Fully qualified displayed buys require current reviewed fundamentals, entry, 100-share affordability and a retained trailing-year adjusted-return volatility measure. Competing candidates rank lowest volatility first. Missing history, missing adjusted-close basis and reported splits in the volatility window block this measure.

## Verification

Root verification: `make verify` passed **659 tests** and `git diff --check`. Owned test-first records document observed failing slices and passing corrections: [expanded detector/paper](../research/2026-10-12-expanded-patterns-tdd.md) and [manual watch](../research/2026-10-12-watch-tdd.md). Tests cover threshold equality, warm-up, first crossing, causal future prefixes, simultaneous events, unchanged inputs, full-position exits, gap-only no orders, missing/stale/mismatched coverage, SG&A flags, affordability, corrupt state and competing process writes.

`uv run python scripts/check_watch_workflow.py --port 4177` passed disposable HTTP checks for empty state, invalid inputs, Host/Origin/body/query/path restrictions, notes/idempotency, restart, stock-page integration, removal/archive and corruption. It verified **858** pre-existing source/evidence files unchanged on this machine and closed both child servers. The script captures a before/after baseline for each run, allowing later legitimate human training activity.

Independent agent QA reported 149 focused tests and 39 additional synthetic/HTTP/source-response checks passing, with no outstanding actionable findings after corrections. Its split control found an unchecked split outside the last180 pattern bars but inside the volatility year; the corrected adapter now blocks volatility for that case and gives a price-basis warning. A separate synthetic merge control verified missing fresh quote metrics cannot retain old P/E/yield under current freshness, while old quarterly facts retain their dates and primary links.

After tightening adjusted-close provenance, independent QA ran30 focused synthetic controls for missing/short/null/zero/negative/nonfinite adjusted values, invalid basis/count/start/end/value metadata, valid lowest-volatility ordering, EPS-zero handling and source-link retention. It caught two further issues: lexical start-date comparison admitted malformed dates, and a failed quote check could overwrite a split warning. Both exact reproductions passed after parsing ISO dates and appending warnings. Final independent review reported no outstanding actionable findings.

Browser QA used a separate4176 server and disposable watch root. Adding AMGN displayed its current price/P/E/yield observations alongside its dated revenue failure, missing classification/management reviews, entry wait and 100-share allocation failure. Reload retained the membership/note. Explicit refresh and removal controls were checked. A separately operator-supplied **synthetic** complete-coverage packet displayed Radar with all fundamentals passed and Why naming the three eligible entry patterns. Neither test granted real security clearance or wrote actual personal membership. Browser console contained no errors/warnings; stock-page JavaScript syntax passed Node's check.

A bounded read-only AMGN source probe retrieved1254 daily bars through October12 and parsed visible quote fields. It retained bytes/receipts privately and did not add AMGN to the real watch list. The attempted key-statistics page exposed no trusted growth field, so the adapter does not infer one. This validates source-access mechanics for one ticker, not all-US coverage or reviewed financial accuracy.

The frozen original patterns.py, review.py and evaluation.py hashes match the prior commit. The dated stock-lists.json and all858 captured prior private/source files remain byte-identical. Historical studies/labels and the v1 training registry were preserved.

## Practical limits

The retained real research still has zero fully qualified buys and zero fundamentally cleared Radar names; headquarters and comparable accounting coverage remain incomplete. Manual watch is usable with those gaps explicit. Source observations cannot supply the missing reviews.

The refresh cutoff approximates completed weekday closes and fails closed on a missing expected session. Exchange holiday/early-close completeness, provider adjustment accuracy, recognition accuracy and strategy performance remain unvalidated. Persistence uses POSIX file locking; this implementation targets the existing local Mac. Refresh jobs are bounded in-process jobs; after server restart, membership and cached evidence persist, and a user can explicitly retry an interrupted check.

Historical training still evaluates v1 geometry. New signal definitions are separately stamped expanded-signals-v1; a six-pattern training corpus and fresh recognition validation are future work. Raw vendor data and personal membership are ignored locally; only implementation, synthetic tests and evidence notes are published.
