# Portfolio TDD evidence — 2026-10-10

Public seam: `step_portfolio(state, market, as_of)`. Python 3.11 / pytest 8.4.2. Developer: coordinator. Each row below records a command actually run first with the new behavior failing, then after the minimum implementation passed. Parametrized cases exercise variants of the same observable behavior; no private functions are tested.

Use `uv run pytest tests/test_portfolio.py::<selector> -q` for each selector below. The integration suite was rerun after changes.

| Selector | Observed red | Subsequent green |
| --- | --- | --- |
| `test_buys_whole_blocks_within_eight_thousand_dollars` | 1 failed: callable raised NotImplementedError | 1 passed; 300 at $26, $192,200 cash |
| `test_blocked_evidence_cannot_create_a_buy` | 1 failed: blocked HQ evidence still bought | passed, no order |
| `test_incomplete_or_unavailable_candidates_cannot_create_a_buy` | 8 failed: unknown/future/missing evidence still bought | 8 passed |
| `test_lowest_volatility_gets_the_last_available_slot` | 1 failed: HIGH and LOW both bought beyond slot limit | passed, only LOW bought |
| `test_purchase_stop_fills_entire_position_at_next_open_without_rebuy` | 1 failed: no required sale | passed, entire position sold at $28 |
| `test_other_mandatory_exits_sell_the_whole_position` | 2 failed: gap/technical exits retained shares | 2 passed |
| `test_portfolio_threshold_sells_four_largest_dollar_losers` | 1 failed: no sales | passed, four losers, $130,100 cash and $162,000 next threshold |
| `test_missing_required_price_defers_atomically_and_can_retry` | 3 failed: KeyError / incomplete exit behavior | 3 passed, unchanged state and successful retry |
| `test_same_day_retry_cannot_repeat_orders_or_consume_another_threshold` | 1 failed: duplicate processed-date entry | passed, no repeat orders/state changes |
| `test_unfillable_candidate_is_skipped_without_spending_cash` | 4 failed, 1 already passed: invalid candidate prices | 5 passed |
| `test_invalid_execution_context_raises_without_mutating_state` | 6 failed: invalid dates, adjusted fills and invalid state accepted | 6 passed |
| `test_qa_causal_gate_evidence_cannot_create_orders` | 3 failed: old report/future or absent completion bought | 3 passed |
| `test_qa_unknown_open_cannot_consume_day_before_gap_stop` | 4 failed: invalid opens committed or raised TypeError | 4 passed, deferred and retryable |
| `test_qa_invalid_volatility_history_cannot_create_order` | 4 failed: short history, infinite count, boolean or impossible metadata admitted | 4 passed |
| `test_qa_invalid_financial_state_is_not_committed` | 2 failed: >25 positions and infinite sale cash committed | 2 passed |
| `test_qa_missing_or_future_sell_completion_does_not_exit` | 2 failed: invalid completed-sell evidence liquidated | 2 passed |
| `test_qa_report_cutoff_must_not_include_after_close_evidence` | 3 failed: late/missing/naive cutoff bought; first correction still errored on null | 3 passed after explicit cutoff validation |

Two additional characterization checks passed against already implemented behavior: the next $162K loss event with fewer than four losers, and a minimum 100-share block exceeding $8K. They are regression checks, not claimed new red→green cycles.

Final local portfolio result at this checkpoint: **50 passed**. Independent QA originated the `test_qa_*` failures and rechecked its standalone cases; see qa-findings.md. The initial missing-price test helper accidentally shared the open/close dictionaries; it was corrected to copy them separately so missing execution prices and missing marks are distinct cases.

## Numeric and timing defaults made concrete

- Coverage report must be recomputed for the prior signal date, not accepted merely because it is older.
- New pattern events must be available on that signal date, with completion no later than availability.
- Trailing volatility metadata uses a 330–366-day window, at least 200 integer returns and a plausible maximum bounded by weekday observations. This is conservative metadata screening, not verification of exchange holidays or the underlying prices.
- All held opening prices must be known before consuming an execution date, because an absent opening price can hide a gap stop.
- Required exit prices preflight atomically; same-date retry remains available on deferral.

These enforce the experimental paper contract; they do not implement a real broker, dividend ledger or corporate-action total-return system.
