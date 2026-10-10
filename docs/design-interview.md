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
- Design portfolio capital: $200,000.
- Maximum holdings: 25 positions.
- Objective: maximize return relative to volatility using a Sharpe-based approach; precise calculation and benchmark comparison remain unresolved.
- Analysis period and intended holding period: both five years; early-exit exceptions remain to be specified.
- Benchmark: S&P 500.
- Stop-loss threshold: −25% from purchase price; treatment of multiple purchases and execution behavior remain unresolved.
- Design method: grilling with documentation, using grilling and domain-modeling.
- Longer-term intent: expose the resulting workflow through an MCP server for others.

## Open decisions

- Gary’s existing screening, valuation, selection, sizing, and exit rules.
- Exact risk-adjusted objective and the role of benchmark-relative performance.
- Five-year holding expectation versus target, growth, technical, and stop-loss exits.
- Stop-loss trigger action, treatment of additions, and execution behavior.
- Allocation method, cash policy, concentration, sector exposure, and leverage constraints.
- ADR eligibility and the operating-company boundary.
- Evidence sources and evaluation methodology.
- Session artifacts, data privacy, and eventual MCP delivery model.

This records scope agreed during the interview; it is not an approved implementation specification.

## Gary’s examples (user-reported judgments)

These examples describe Gary’s reasoning. They are not verified current financial data or recommendations.

- Micron: buy based on low P/E, consistent earnings, solid growth, and a dividend.
- Amgen: buy based on P/E below 30, dividend yield above 2%, and growth above 15%; growth metric and period are unresolved.
- SIRI: sell after reaching a target and no longer showing growth.
- Meta: hold because it appears underpriced, but the opportunity does not justify more capital.
- Oracle: sell because of a technology-related concern and a poor chart; meaning of the technology concern is unresolved.
- Technical inputs: relative strength and momentum, including the 200-day moving average, used alongside fundamentals.

The examples suggest a combined fundamental and technical approach. Whether each input is a hard gate, a preference, or an override has not been settled.

## Additional settled rules

- Fundamental requirements: P/E below 30, dividend yield above 2%, and historical revenue growth above 15%. P/E basis and revenue-growth measurement period remain unresolved.
- Fundamentals determine security selection and take precedence over technicals.
- Technicals determine entry timing, not security selection or allocation size. Inputs include moving averages, relative strength, support (floors), and resistance (tops); exact rules remain unresolved.
- Exits are mostly technical; exact triggers and precedence relative to the purchase-price stop remain unresolved.
- Oracle’s rejection reflects insufficient fundamentals and reliance on a technology-superiority thesis outside Gary’s confidence. This is not a blanket technology-sector exclusion.
- Allocation depends on risk tolerance and portfolio size; the risk tolerance and sizing method remain unresolved.
- Exclude ADRs, REITs, BDCs, and SPACs.
- Portfolio is long-only and may hold cash. Borrowing and leverage have not been explicitly settled.

## Current interview frontier

- P/E basis, historical revenue-growth window, and fundamental review frequency.
- Exact entry and exit technical rules, plus the operational meaning of fundamental precedence.
- Risk tolerance, concentration limits, and conversion to 100-share blocks.
- Mandatory versus discretionary stop action and purchase-price reference for additions.
- Distinction between five-year holding intent and technical exits.
- Historical evaluation window versus forward-looking objective, benchmark conventions, evidence sources, and workflow outputs.
