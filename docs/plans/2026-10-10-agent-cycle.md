---
status: reviewed
---

# Gary.ai first agent cycle

## Objective and authorization

Validate free-data coverage and the feasibility of daily-chart pattern detection, then demonstrate one bounded research → TDD → local deployment → independent QA cycle. The user requested a team of agents and explicitly approved these public test seams on 2026-10-10:

1. Coverage report for a symbol and as-of snapshot.
2. Pattern detector returning signals and evidence from daily bars.
3. Paper-portfolio daily step returning orders and state.

Strategy: [v1 specification](../strategy-v1.md). Evidence: [data research](../research/data-coverage.md), [pattern research](../research/pattern-detection.md). Acceptance: [scorecard](../scorecards/2026-10-10-agent-cycle.md). Assignment briefs: [prompt pack](../prompts/2026-10-10-agent-cycle.md).

Concrete proposed contracts: [agent-cycle-contracts.md](../agent-cycle-contracts.md). These preserve the three user-approved seams.

## First-cycle scope

Deliver a reproducible sample coverage report, a conservative pattern recognizer, a paper daily-step engine, a runnable local preview, and a durable record of failing/passing tests and QA findings. Do not claim all-universe coverage, proven pattern accuracy, a valid five-year backtest, or trading efficacy from a sample or synthetic fixtures.

Start with Python 3.11+ and pytest; keep strategy computation independent of network access. Use JSON snapshots at the approved seams. Live probe scripts produce ignored raw inputs and share only permitted summarized research evidence. Data adapter/schema choices must follow research, not silently substitute Yahoo metadata for SEC values.

## Proposed public contracts

- `coverage_report(snapshot, as_of)`: returns symbol, checked time, per-field availability/provenance, normalized fundamentals, security eligibility (`eligible`, `excluded`, `unknown`), and explicit blockers. Missing/ambiguous security classification or future-dated data must block autonomous entry.
- `detect_patterns(bars, as_of)`: accepts ordered daily OHLCV records; returns completed buy/sell signals with pattern kind, completion date, breakout/neckline evidence, and causally confirmed pivots. Never use bars after `as_of`. Malformed bars produce an explicit error. Heuristic geometry remains experimental.
- `step_portfolio(state, market, as_of)`: returns paper orders, resulting cash/positions, next loss threshold, and audit events. Enforces $8K blocks, 25 positions, WAPP stops, four-largest-dollar-losers response, successive thresholds, and cycle idempotency. Execution uses explicitly provided next-session price data; no fictional fills at past signal closes.

The exact JSON schemas will be captured before tests. Required interfaces are approved; provisional strategy defaults remain as marked in v1.

## Phases and file ownership

1. **Research and plan review** — research agents own `docs/research/data-coverage.md` and `docs/research/pattern-detection.md`; coordinator owns plan/scorecard/briefs. Three independent reviewers assess feasibility, verification, and scope/risk. Persist reviewed artifacts before implementation. Human confirmation is required to launch the concrete plan under review-plan.
2. **Runtime and schema foundation, then coverage slice** — coordinator creates package/runtime setup and freezes shared schemas before seam development. Coverage developer owns `src/gary/coverage.py`, `tests/test_coverage.py`, bounded live-probe tooling. One behavior test, observed failure, minimal implementation, pass; repeat. Report actual sample counts and exact retrieval failures.
3. **Detector slice** — developer owns `src/gary/patterns.py`, `tests/test_patterns.py`, explicit fixtures and detector metadata. Cover all three requested shapes, non-pattern controls, uncompleted shapes, and prefix invariance. Recognition tests do not authorize performance claims or unrestricted automatic trading.
4. **Portfolio integration** — coordinator owns `src/gary/portfolio.py`, `tests/test_portfolio.py`, candidate volatility ranking and preview entry point. Require the coverage gate result and dated completed signal before entry, then rank by trailing-12-month volatility. Red → green vertical slices against public state/order behavior; independently worked numeric examples.
5. **Local deployment and QA** — coordinator starts a local-only preview; an independent QA agent exercises public contracts and end-to-end flow, including duplicate processing, malformed/missing data and stop/threshold interactions. Developers fix actionable failures using a failing regression first; QA rechecks changed cases. Publish a cycle report with exact commit and commands.

Agents do not commit each other's work. Shared-file changes are coordinator-owned. No deployment of unreviewed code to external hosting; local preview is the first deployment target.

The initial preview uses visibly synthetic fixtures; measured coverage research appears separately. The live sample has not cleared headquarters evidence, so it cannot legitimately generate autonomous buys. Prototype detector geometry and paper execution are exercised without representing synthetic records as real market opportunities.

## Validation commands (to be created with implementation)

- `uv run pytest -q`: deterministic behavior suite.
- `uv run python -m gary.coverage_probe`: bounded live sample coverage; records measurement time and failed probes without turning unavailable inputs into positives.
- `uv run python -m gary.preview`: local-only demo/preview.
- `git diff --check`: document/code whitespace checks.

If research changes the contracts/commands, update this plan and record why before launch.

## Rollback and limits

Initial code has no real-money or brokerage access. Preview binds to localhost. Stop the local process to end deployment; discard ignored paper state or restore a saved fixture to reset the experiment. Credentials/data/state remain ignored and outside committed reports. No scheduler or endless agent loop is created by this request: this is one bounded cycle with reusable briefs for subsequent cycles.

## Known unresolved quality gates

- Real chart recognition needs independently labeled positive and negative samples and held-out evaluation. Synthetic tests alone can establish geometry behavior, not field precision.
- Evidence of no recent headquarters investment is not established by a missing keyword or missing SG&A field.
- Dollar-loss contributors, repeated threshold semantics, and next-open execution must be deterministic and visible; multi-threshold gaps need a documented policy.
- Future public MCP distribution needs independently verified data rights and per-user state.
- A provider quarter being present does not establish that it is the latest reported quarter. Compare against filing-aware period evidence; mismatches visibly block entry.
- Core paper replay does not yet implement dividend/corporate-action total-return accounting. Its output is a behavior demonstration, not a five-year performance result.

## Review (2026-10-10)

Verdict: **SHIP**, three independent non-author lenses, no remaining blockers. Scope reviewer reused the idle pattern-research agent because the session reached its agent-thread limit; it did not author the coordinator's plan.

| Lens | Finding and resolution |
| --- | --- |
| Feasibility | SHIP. Moved runtime/schema setup ahead of TDD, froze integration ownership and made preview fixtures visibly synthetic. |
| Verifiability | SHIP after revision. Added coverage/headquarters gate results, completed dated signal, adequate dated 12-month volatility and ranking to the entry contract/scorecard. Numeric report pairs and 32 private evidence hashes independently checked. |
| Scope/risk | SHIP after revision. Required-exit price failures now atomically defer unchanged state/date/threshold, with same-date retry. Valuation, loss ranking, stop gaps and duplicate exit precedence are explicit. |

Next step: human launch approval of this concrete bounded cycle. Three public seams were already approved; no tests or implementation have been written during shaping/review.
