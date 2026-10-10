# Design interview

## Settled scope

- Project name: Gary.ai.
- GitHub repository: public, under datablogin.
- Investment universe: operating-company common stocks listed on US stock exchanges.
- Starting knowledge: deep familiarity with US equity fundamentals.
- Purpose: formalize Gary’s existing strategy and determine allocations.
- Initial user: one experienced investor; no explanatory or support workflow required.
- Portfolio boundary: a dedicated stock portfolio, independent of other investments.
- Position sizing: whole blocks of 100 shares.
- Objective: most return per unit of risk, described as approximately Sharpe-ratio based; exact metric remains unresolved.
- Evaluation horizon: five years.
- Benchmark: S&P 500.
- Stop-loss threshold: −25%; reference price, execution behavior, and scope remain unresolved.
- Design method: grilling with documentation, using grilling and domain-modeling.
- Longer-term intent: expose the resulting workflow through an MCP server for others.

## Open decisions

- Gary’s existing screening, valuation, selection, sizing, and exit rules.
- Exact risk-adjusted objective and the role of benchmark-relative performance.
- Five-year horizon as evaluation period versus required holding period.
- Stop-loss reference price, position versus portfolio scope, and trigger behavior.
- Portfolio capital, cash policy, and exposure constraints.
- ADR eligibility and the operating-company boundary.
- Evidence sources and evaluation methodology.
- Session artifacts, data privacy, and eventual MCP delivery model.

This records scope agreed during the interview; it is not an approved implementation specification.
