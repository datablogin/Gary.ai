# Approved seams: first-cycle contracts

The user approved the three public interfaces on 2026-10-10. These contracts are a proposed concrete form for the reviewed first-cycle plan, not an authorization to trade real money.

## Coverage report

`coverage_report(snapshot: dict, as_of: str) -> dict`

Snapshot carries `symbol`, `security_type`, `exchange`, independently evidenced eligibility/classification, dated source references, and reported fundamental observations. Observations include both period dates and availability/filing dates. Report exposes availability, blockers, normalized values, eligibility (`eligible`, `excluded`, `unknown`), and source evidence. The data developer can refine schema from actual research but must document it before the first test.

The caller can distinguish access failure, missing field, unsupported security, stale data, and future information. Never fill missing fundamental values with zero. Separate data completeness from strategy thresholds; a stock with complete data can still fail Gary’s gates.

## Pattern recognition

`detect_patterns(bars: list[dict], as_of: str) -> list[dict]`

Bar keys: ISO `date`, numeric `open`, `high`, `low`, `close`, and `volume`. Bars must have increasing unique dates and internally consistent finite OHLCV values. Only the as-of prefix affects signals. Future bars cannot change previously available signals.

Signal includes `kind`, `direction`, `completion_date`, `available_at`, `breakout_level`, `pivots` (date, price, confirmation date), `checks`, and detector version. Pattern kinds are `inverse_head_shoulders`, `cup_handle`, and `head_shoulders_top`. Completed signals are evidence-backed hypotheses, not calibrated probabilities. The detector developer documents parameter choices and pattern geometry before the first fixture.

## Paper daily step

`step_portfolio(state: dict, market: dict, as_of: str) -> dict`

State: cash, positions keyed by symbol (shares and WAPP), initial capital, next portfolio loss threshold, processed execution dates. Market snapshot: current execution date, prior signal date, prior closing marks, current-session execution prices, and candidates/signals known by the prior signal date. Only explicitly supplied valid prices can fill orders. Pattern/fundamental decisions are known before execution; missing prices leave an order unfilled with a reason.

Candidate records must include symbol, the coverage report's `buy_allowed` result and blockers, a completed buy-pattern signal with `available_at` no later than the prior signal date, and a finite nonnegative volatility observation measured over trailing 12 months and ending no later than the signal date. `buy_allowed` can be true only if supported security eligibility, all three fundamental gates, freshness/comparability checks and reviewed headquarters clearance pass. A price-only pattern can never supply that clearance. The engine filters out any failed/missing evidence and then ranks admissible candidates by volatility ascending, breaking ties by symbol. The coverage module owns eligibility/gates; the portfolio module owns ranking and allocation. Execution prices are unadjusted current-session fill prices and must be identified separately from adjusted-return volatility inputs.

The volatility observation must carry start/end dates and at least 200 finite daily returns in the trailing calendar year (a provisional adequacy floor, not a trading rule supplied by Gary). Pattern and fundamental availability refer to the completed prior session. Date-only financial publication evidence is conservatively usable from the following session; same-day unknown publication time cannot pass an earlier signal cutoff.

Result: updated state, ordered paper orders, and audit events. A same-date retry returns unchanged financial state and no duplicate orders. Maximum 25 positions; a new slot spends no more than $8,000 on 100-share blocks. Stop/technical exits take precedence over entry, no same-cycle repurchase. Portfolio loss response selects up to four current negative dollar-loss contributors and consumes the threshold once; next threshold is 90% of the consumed threshold. A multi-threshold gap provisionally consumes one threshold per daily cycle and exposes the next threshold, rather than repeatedly selling/rebuying during one execution step. State must not mutate on invalid inputs.

Freeze valuation/selection before filling: prior-close equity determines the portfolio threshold, and prior-close unrealized dollar losses rank the four positions. Purchase-price stops use prior-close prices; a next-open gap below the stop also requires an exit at that supplied open. Combine the four selected losers with mandatory stops/technical exits, deduplicating each position into one sell order. Select no profitable position solely to reach four. Then execute all sells before considering entries.

Preflight required exits atomically. If any held position lacks a valid prior-close mark, or any required exit lacks a valid execution price, return `status: deferred` with unchanged state, no orders, no consumed threshold and no processed date. The same date remains retryable when complete prices arrive; entries are deferred with exits. This first cycle has no pending-order ledger. A missing buy execution price merely skips that candidate. QA must reproduce both a missing-price stop and a missing-price portfolio-loss event.

The first engine is a paper replay with explicit prices. Data ingestion, corporate-action accounting, dividends and production-ready brokerage execution are separate later work; its current outputs must not be called a total-return backtest.

The first preview uses clearly labeled synthetic data. None of the live sample is claimed to have automatic headquarters clearance. Live-probe summaries can be viewed alongside the demo but cannot automatically fund demo entries.

## TDD evidence

Each seam's developer records one observed failure and subsequent pass per behavior in `docs/cycles/2026-10-10-first-cycle.md` via the coordinator. Numeric expected outcomes are independently worked examples. Synthetic chart fixtures are hand-labeled shape controls and must be identified as synthetic. Real-chart labeling and efficacy remain separate gates.
