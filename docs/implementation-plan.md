# First-version implementation plan

## 1. Data and rule feasibility

Verify US security classification, quarterly revenue/SG&A extraction, trailing earnings, dividends, daily prices, and headquarters evidence on a small real sample. Preserve reporting dates and source provenance. Document unavailable fields and detector limitations.

## 2. Strategy engine

Implement fundamental eligibility, headquarters exclusion, volatility ranking, completed-pattern detectors, block sizing, and paper-portfolio state. Separate data adapters from strategy rules so providers can change later.

Validate with meaningful fixtures: quarterly comparisons, missing data, split handling, block boundaries, stop precedence, successive loss thresholds, fewer-than-four losers, cash limits, and duplicate daily runs. Pattern tests need positive and negative chart examples; evaluate false detections before broad scans.

## 3. Local dashboard

Build Radar, Buy-ready, Holdings, and Sell alerts with charts, source evidence, portfolio state, and decision history. Start with $200,000 cash and daily processing. Provide optional pattern feedback without requiring it for paper execution.

## 4. Evaluate the full workflow

Run the daily flow end to end. Validate paper accounting and restart behavior. Define a point-in-time five-year evaluation before drawing performance conclusions; keep current-data screening separate from historical testing.

## Later work

Research subscriptions after measuring coverage gaps. Add brokerage read access before proposing order execution. Package validated strategy tools and prompts in MCP, with appropriate per-user state and data access. Remote deployment is a later milestone.

The first bounded research/TDD/local-preview/QA cycle is implemented; see [cycle results](cycles/2026-10-10-first-cycle.md). The [second cycle](cycles/2026-10-10-cycle-2.md) adds a frozen real-chart review queue, versioned labels, locked holdout, expanded source controls and future-review evidence guards. Its actual calibration study remains unlabeled. Full-universe ingestion, real-chart accuracy, corporate-action/dividend accounting, the five-year backtest, brokerage access and MCP delivery remain later milestones.
