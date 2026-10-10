# Design interview

This records agreed scope and unresolved decisions; it is not an approved implementation specification.

## Project and delivery

- Name: Gary.ai; public GitHub repository under datablogin.
- Formalize Gary’s existing strategy for one experienced investor, without an explanatory or support workflow.
- Initial deliverable: a list for manual review; brokerage API integration comes later.
- Longer-term intent: expose the workflow through an MCP server for others.
- Design method: grilling with documentation, using grilling and domain-modeling.

## Universe and fundamentals

- Operating-company common stocks listed on US stock exchanges.
- Exclude ADRs, REITs, BDCs, and SPACs.
- Mandatory gates: trailing P/E below 30, dividend yield above 2%, historical revenue growth above 15%.
- Revenue growth uses the last quarter; the comparison basis remains unresolved.
- Fundamentals determine eligibility and trump technicals.
- Oracle’s rejection reflects insufficient fundamentals and a technology-superiority thesis outside Gary’s confidence, not a blanket technology-sector exclusion.

## Technical workflow

- Eligible stocks with weak charts wait on the radar list.
- Entry setups: completed inverse head and shoulders or cup and handle.
- Exit setup: completed head and shoulders top.
- Other named inputs: moving averages, relative strength, support, resistance; their operational role remains unresolved.
- Technicals determine entry timing and most exits, not selection or sizing.
- Intended holding period: five years; sell earlier when a technical exit appears.

## Portfolio and allocation

- Dedicated stock portfolio independent of other investments.
- Initial capital: $200,000; maximum 25 positions.
- Equal allocation to start; denominator and block-rounding policy remain unresolved.
- Whole 100-share blocks only.
- Long-only, no margin, cash permitted.
- Sell the entire position after a 25% decline from weighted-average purchase price (WAPP).
- Portfolio loss tolerance: 10% from initial capital; resulting action remains unresolved.

## Evaluation intent

- Maximize return relative to volatility with a Sharpe-based objective.
- Five-year analysis period; historical versus forward-looking treatment remains unresolved.
- Benchmark: S&P 500; return convention and comparison criterion remain unresolved.
- Equal initial sizing is agreed; Sharpe-driven sizing optimization has not been authorized.

## Open decisions

- Action at the portfolio loss threshold.
- Equal allocation denominator, cash treatment, rounding, candidate ranking, and concentration limits.
- Revenue-growth comparison basis and rules for deteriorating fundamentals.
- Exact technical confirmation, chart timeframe, and additional technical filters.
- First-list format, data source, refresh cadence, and holdings inputs.
- Sharpe evaluation method and benchmark conventions.
- Later brokerage and MCP delivery details, deferred beyond the first list.

## Gary’s examples (user-reported judgments)

These examples describe Gary’s reasoning. They are not verified current financial data or recommendations.

- Micron: buy based on low P/E, consistent earnings, solid growth, and a dividend.
- Amgen: buy based on P/E below 30, dividend yield above 2%, and growth above 15%.
- SIRI: sell after reaching a target and no longer showing growth.
- Meta: hold because it appears underpriced, but the opportunity does not justify more capital.
- Oracle: sell because of a technology-related concern and a poor chart.
- Technical inputs: relative strength and momentum, including the 200-day moving average, used alongside fundamentals.

