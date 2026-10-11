# Design interview

This records agreed scope and unresolved decisions; it is not an approved implementation specification.

## Project and delivery

- Name: Gary.ai; public GitHub repository under datablogin.
- Formalize Gary’s existing strategy for one experienced investor, without an explanatory or support workflow.
- Initial deliverable: local dashboard with Radar, Buy-ready, Holdings, and Sell alerts; daily refresh and dated source evidence. Brokerage API integration comes later.
- Gary will not supply current holdings. Start a paper portfolio with $200,000 entirely in cash; track simulated positions and exits.
- Longer-term intent: expose the workflow through an MCP server for others.
- Design method: grilling with documentation, using grilling and domain-modeling.

## Universe and fundamentals

- Operating-company common stocks listed on US stock exchanges.
- Exclude ADRs, REITs, BDCs, and SPACs.
- Mandatory gates: trailing P/E below 30, dividend yield above 2%, historical revenue growth above 15%.
- Revenue growth compares the latest reported quarter with the same quarter one year earlier (for example Q1 2026 versus Q1 2025).
- Fundamentals determine eligibility and trump technicals.
- Oracle’s rejection reflects insufficient fundamentals and a technology-superiority thesis outside Gary’s confidence, not a blanket technology-sector exclusion.

## Technical workflow

- Eligible stocks with weak charts wait on the radar list.
- Daily-chart entry setups: completed inverse head and shoulders or cup and handle. Gary.ai detects patterns automatically and may execute paper buys without Gary’s confirmation. Technical-sell confirmation remains to be explicitly settled.
- Exit setup: completed head and shoulders top.
- Other named inputs: moving averages, relative strength, support, resistance; their operational role remains unresolved.
- Technicals determine entry timing and most exits, not selection or sizing.
- Intended holding period: five years; sell earlier when a technical exit appears.

## Portfolio and allocation

- Dedicated stock portfolio independent of other investments.
- Initial capital: $200,000; maximum 25 positions.
- Equal initial allocation: $8,000 per slot across 25 slots. Buy the largest whole multiple of 100 shares costing no more than $8,000, retain residual and unused-slot capital in cash, and skip stocks whose 100-share minimum exceeds $8,000.
- Whole 100-share blocks only.
- Long-only, no margin, cash permitted.
- Sell the entire position after a 25% decline from weighted-average purchase price (WAPP).
- At a 10% decline from initial capital: sell the four biggest losers by dollar contribution to losses, then permit new buys immediately. Repeat-trigger behavior and treatment of fewer than four losing positions remain unresolved.

## Evaluation intent

- Maximize return relative to volatility with a Sharpe-based objective.
- Five-year analysis period; historical versus forward-looking treatment remains unresolved.
- Benchmark: S&P 500; return convention and comparison criterion remain unresolved.
- Equal initial sizing is agreed; Sharpe-driven sizing optimization has not been authorized.

## Open decisions

- Portfolio loss-contributor ranking, reduction amount, and buy-resumption rule.
- Cash treatment, block rounding, candidate ranking, concentration limits, and replacement/rebalancing rules.
- Rules for deteriorating fundamentals.
- Exact technical confirmation, optional human confirmation policy, and additional technical filters.
- Data source and paper-trade execution assumptions.
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

## Remaining operational decisions

- Portfolio threshold event/rearm behavior and fewer-than-four-losers handling.
- Technical-sell automation and optional confirmation display.
- Volatility calculation and management/headquarters filter specification.
- Free-access market-data selection and paper-trade execution convention.
- Evaluation conventions and detailed detector validation will need a concrete specification before implementation.

## Latest decisions

- Candidate priority: lowest volatility first; volatility definition remains unresolved.
- Management consideration: avoid companies that invested in a new headquarters, with a large SG&A increase named as a signal. Measurement, evidence requirements, and gate versus flag behavior remain unresolved.
- Data approach: start with open-source/free-access sources; research paid subscriptions later. Provider, licensing, freshness, and completeness remain to be assessed.
- Autonomous execution is for the simulated paper portfolio. Brokerage integration remains deferred.

## Interview close

Gary requested a summary and transition to next steps. Further interview rounds are deferred; unresolved implementation details will use explicitly labeled provisional defaults.

- After the first portfolio loss event, sell again after another 10% loss; denominator remains a provisional implementation choice.
- Rank candidates by volatility over the last 12 months.
- New headquarters investment is a hard exclusion. A 25% SG&A increase is considered large; SG&A alone is not proof of headquarters investment.
- Technical paper sells execute autonomously.

See strategy-v1.md for the consolidated specification and implementation-plan.md for the build sequence.
