# Independent first-cycle QA

Scope: the three approved public seams and the local synthetic preview. QA did not edit implementation or developer tests. This is behavior validation, not real-chart accuracy or investment-performance evidence.

## Portfolio initial pass

Command: `uv run pytest tests/test_portfolio.py -q`.

Observed: **32 passed**. The additional probes below called `step_portfolio` directly with independently constructed synthetic records. They do not depend on private portfolio helpers or developer fixture functions.

| Finding | Observed public result | Required behavior | Initial status |
| --- | --- | --- | --- |
| Expired coverage clearance | A candidate with `coverage.as_of=2025-10-09` bought 400 shares at $20 for signal date 2026-10-09. | A gate report evaluated for an old cutoff cannot establish current freshness. | Blocking; sent to coordinator |
| Missing held-position open loses retry | Holding 100 shares at WAPP $100, cash $190,000, prior close $100, and no open committed the date. Retry with open $70 returned `already_processed` and kept the position. NaN/infinite opens also committed; null/string opens raised `TypeError`. | Unknown or invalid opens cannot finalize a day before the gap-stop decision; preserve retryability. | Blocking; sent to coordinator |
| Impossible volatility evidence | A one-day start/end window claiming 250 daily returns, an infinite return count, and boolean volatility each admitted a buy. | Require plausible trailing-year evidence, finite integer return count, and numeric nonboolean volatility. | Blocking; sent to coordinator |
| Invalid starting position count | Starting with 26 valid held blocks returned `committed` with 26 positions. | Reject invalid state exceeding the 25-position limit without mutating it. | Blocking; sent to coordinator |
| Future completion date | A buy signal with completion date 2026-10-12 but availability 2026-10-09 admitted an order for signal date 2026-10-09. | Completion must be valid and no later than availability or the decision cutoff. | Blocking; sent to coordinator |
| Finite arithmetic overflow | A technical exit of 100 shares at finite price `1e308` committed cash `inf`. | Validate derived accounting values before committing financial state. | Advisory; sent to coordinator |

The independent threshold checks passed: exactly $180,000 prior-close equity triggered four equal-loss sales and advanced the threshold to $162,000; different share counts ranked by dollar loss; fewer than four losing holdings left a profitable holding untouched.

### Reproduction base

Run from the repository with `uv run python`; use this base and the modifications in the findings table:

```python
from gary.portfolio import step_portfolio

state = {
    "cash": 200000.0, "positions": {}, "initial_capital": 200000.0,
    "next_loss_threshold": 180000.0, "processed_dates": [],
}
candidate = {
    "symbol": "SYNTH",
    "coverage": {
        "symbol": "SYNTH", "as_of": "2026-10-09",
        "decision_cutoff": "2026-10-09T16:00:00-04:00",
        "eligibility": "eligible", "buy_allowed": True, "blockers": [],
    },
    "signal": {
        "kind": "inverse_head_shoulders", "direction": "buy",
        "status": "completed", "available_at": "2026-10-09",
        "completion_date": "2026-10-09",
    },
    "volatility": {
        "value": 0.2, "start": "2025-10-09", "end": "2026-10-09",
        "return_count": 250,
    },
}
market = {
    "signal_date": "2026-10-09", "execution_date": "2026-10-12",
    "execution_price_basis": "unadjusted", "closes": {},
    "opens": {"SYNTH": 20}, "candidates": [candidate], "sell_signals": [],
}
print(step_portfolio(state, market, "2026-10-12"))
```

## Rechecks and integrated preview

After coordinator fixes, `uv run pytest tests/test_portfolio.py -q` reported **45 passed**. Independent re-execution of 13 exact/adjoining probes confirmed all six initial findings resolved: invalid entry evidence produces no orders; absent/null/string/NaN/infinite held opens defer without changing state and a same-date $70-open retry sells the entire position; too many positions and overflowing valuations/proceeds raise `ValueError` without mutating input.

One additional causal exit defect remained on that recheck: `sell_signals` with `completion_date=2026-10-12`, or with no completion date, still triggered a technical sale despite signal cutoff 2026-10-09. Reproduction: cash $190,000; held `SYNTH` shares 100/WAPP $100; close/open $100; signal kind `head_shoulders_top`, status `completed`, direction `sell`, availability 2026-10-09. Observed sell 100 at $100 for `technical_exit`. This was sent to the coordinator as blocking; valid stop/loss exits should remain independent of rejected technical evidence.

The coordinator added sell-signal completion validation; the subsequent integrated suite reported **224 passed**. Initial findings above are historical observations; a recorded independent recheck establishes their resolution.

## Integrated seam and HTTP checks

Commands: `uv run pytest -q`; direct public-seam probes via `uv run python`; HTTP requests to `http://127.0.0.1:4175` via Python's standard-library `urllib.request`.

Independent public-seam results:

- The curated synthetic coverage snapshot passed with PE 20, normalized yield 0.03, revenue growth approximately 0.20 and SG&A growth approximately 0.10.
- After-close publication timestamps blocked classification, headquarters, latest-period and current-revenue evidence at the ordinary session cutoff. YTD revenue, a REIT classification and unknown headquarters clearance also blocked entry.
- For every one of the **251** synthetic bar dates, full-history input evaluated at that date exactly matched physically truncated input. Every emitted pivot confirmation was no later than its signal availability. Invalid future OHLCV did not change permitted signals. Price scales 0.01 and 100 preserved pattern identity/completion dates.

The following HTTP sequence passed; these commands reproduce the endpoint sequence:

```bash
curl -fsS http://127.0.0.1:4175/health
curl -fsS -X POST http://127.0.0.1:4175/api/reset
curl -fsS http://127.0.0.1:4175/api/demo
curl -fsS -X POST http://127.0.0.1:4175/api/run
curl -fsS -X POST http://127.0.0.1:4175/api/run
curl -fsS http://127.0.0.1:4175/api/demo
curl -sS -i -X POST -H 'Origin: https://example.invalid' http://127.0.0.1:4175/api/reset
curl -sS -i http://127.0.0.1:4175/api/run
curl -fsS -X POST http://127.0.0.1:4175/api/reset
```

Observed: health identified `synthetic_paper_demo`; reset produced $200,000 cash with no positions; run bought 300 `SYNTH-A` shares at $22.40, leaving $193,280 cash; repeated run returned `already_processed`, no orders and identical financial state. GET retained the persisted result. The saved ignored `private/paper-preview-state.json` exactly matched each committed/reset state. An external-origin reset returned 403 without changing state. GET `/api/run` returned 404. Final reset left $200,000, zero positions and no processed dates for the coordinator's visual check.

Source separation passed: the API identified its experimental synthetic mode, its normalized report covered `SYNTH-A` with synthetic source URLs, and research counts remained separate (`0/5` live headquarters clearances, real-chart accuracy `Unmeasured`). The static page likewise labels invented prices and separates the live pilot counts. QA did not independently assess the rendered page; the coordinator owns visual verification.

### Integrated cutoff finding

**Initially blocking; resolved on independent recheck:** coverage accepted an explicit after-close cutoff but returned only its New York date. Portfolio therefore mistook that report for the 16:00 completed-session decision snapshot.

Reproduction using the product's synthetic snapshot and bars: set `fundamentals.revenue.current.source.available_at` to `2026-10-09T21:00:00Z` (17:00 New York), then call `coverage_report(snapshot, "2026-10-09T22:00:00Z")`. Observed `buy_allowed: true` and `as_of: "2026-10-09"`. Feeding that report with the ordinary October 9 completed pattern and trailing-year volatility to `step_portfolio` admitted 300 shares at $22.40 on October 12. The frozen trading cutoff excludes that publication from the October 9 session decision. Preserve and validate the actual coverage cutoff across the seam, or restrict tradeable clearance to the completed-session cutoff.

After the fix, that exact report retained `decision_cutoff: "2026-10-09T18:00:00-04:00"` and the portfolio returned **no orders**. A control with publication at 15:00 and the ordinary 16:00 cutoff still admitted 300 shares at $22.40, confirming the rejection was caused by late decision timing rather than missing fixture fields.

## Final verdict

**PASS for the bounded synthetic paper cycle. No unresolved blocking QA findings.**

Final command `uv run pytest -q` reported **230 passed**. With the final required `decision_cutoff` present and a valid baseline demonstrably able to buy, all 13 original standalone probes passed again. Both missing/future sell-completion cases passed, and the actual after-close coverage-to-portfolio reproduction passed as described above.

The restarted preview at `http://127.0.0.1:4175` passed final health, demo, run, repeat, persisted-GET and reset checks. The API preserved the 16:00 cutoff, still separated experimental synthetic entries from measured live research, bought the expected 300 shares at $22.40 with $193,280 cash, prevented duplicate orders, and reset the persisted ignored state to $200,000/no positions/no processed dates. QA left that reset state in place.

Limits: this verifies public behavior and HTTP integration for the documented first cycle. It establishes neither real-chart recognition accuracy nor historical total-return accounting, investment efficacy, or whole-universe coverage. The coordinator separately verifies the rendered UI and final commit/persistence evidence.
