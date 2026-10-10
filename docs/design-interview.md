# Design interview

This records agreed scope and unresolved decisions; it is not an approved implementation specification.

## Project and delivery

- Name: Gary.ai; public GitHub repository under datablogin.
- Formalize Gary’s existing strategy for one experienced investor, without an explanatory or support workflow.
- Initial deliverable: local dashboard with Radar, Buy-ready, Holdings, and Sell alerts; daily refresh and dated source evidence. Brokerage API integration comes later.
- Gary will not supply current holdings; model portfolio versus newly tracked positions remains unresolved.
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
- Equal initial allocation: $8,000 per slot across 25 slots. Block-rounding, minimum-block feasibility, and unused-slot cash treatment were recommended but not explicitly settled.
- Whole 100-share blocks only.
- Long-only, no margin, cash permitted.
- Sell the entire position after a 25% decline from weighted-average purchase price (WAPP).
- At a 10% decline from initial capital: pause new buys and start removing stocks contributing most to the decline. Loss-contribution metric, liquidation amount, and buy-resumption rule remain unresolved.

## Evaluation intent

- Maximize return relative to volatility with a Sharpe-based objective.
- Five-year analysis period; historical versus forward-looking treatment remains unresolved.
- Benchmark: S&P 500; return convention and comparison criterion remain unresolved.
- Equal initial sizing is agreed; Sharpe-driven sizing optimization has not been authorized.

## Open decisions

- Portfolio loss-contributor ranking, reduction amount, and buy-resumption rule.
- Cash treatment, block rounding, candidate ranking, concentration limits, and replacement/rebalancing rules.
- Revenue-growth comparison basis and rules for deteriorating fundamentals.
- Exact technical confirmation, chart timeframe, and additional technical filters.
- Data source, model portfolio versus new position tracking, and initial holdings state.
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

## Latest clarifications pending

- User described revenue growth as “Quarter over quarter, so year over year.” Adjacent-quarter growth and same-quarter year-over-year growth are distinct; the denominator must be clarified.
- Gary.ai must automatically detect completed chart patterns and may ask Gary to confirm detected patterns. Daily chart timeframe was recommended but not explicitly confirmed.
- Real portfolio stop and loss-contribution monitoring requires positions and purchase prices. Without current holdings, the initial portfolio representation must be settled.
