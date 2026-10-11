# Gary.ai strategy v1

## Agreed mandate

Formalize Gary’s existing strategy for a single experienced investor. Begin with a local daily dashboard and autonomous paper portfolio; brokerage integration and a distributable MCP come later.

Start with $200,000 cash. Long-only, no margin, at most 25 positions. Only US exchange-listed operating-company common stocks; exclude ADRs, REITs, BDCs, and SPACs.

## Selection and entry

All fundamental gates must pass: positive trailing P/E below 30, dividend yield above 2%, and latest reported quarterly revenue growth above 15% versus the same quarter one year earlier. Positive P/E is a provisional guard against negative earnings being treated as cheap.

A new headquarters investment is a hard exclusion. A 25% SG&A increase is a large increase and merits investigation; it does not by itself establish headquarters spending. The headquarters lookback period and treatment of inconclusive evidence require future validation.

Fundamentally eligible stocks with weak charts remain on Radar. Automatically detect completed inverse head-and-shoulders and cup-and-handle patterns on daily charts. Completed entries may trigger paper buys without confirmation. Show the detected pattern and allow Gary to provide feedback.

Rank competing entry candidates by lowest volatility over the last 12 months. Technicals determine timing, not allocation size. Moving averages, relative strength, support, and resistance are context until their additional gating rules are validated.

## Allocation

Each slot targets $8,000. Purchase the largest multiple of 100 shares costing no more than that budget. Skip candidates whose 100-share block exceeds the budget. Retain rounding residuals and unused slots in cash. Do not exceed available cash or 25 positions.

## Exits and portfolio response

Sell the entire position at a 25% decline from weighted-average purchase price or a completed head-and-shoulders top. Technical exits are automatic and may occur before the intended five-year holding period.

At the initial 10% portfolio loss, sell the four biggest dollar-loss contributors. If fewer than four losing positions exist, provisionally sell those available. New buys are allowed after the sales. Repeat after another 10% portfolio loss.

## Provisional defaults requiring evaluation

These defaults make a first implementation reviewable; they are not additional claims about Gary’s existing practice.

- Successive loss thresholds: $180,000, $162,000, $145,800, and so on, each 10% below the prior threshold. Persist consumed thresholds so a refresh cannot repeatedly trigger the same event. This interprets “another 10%” multiplicatively rather than as another $20,000.
- Rank current losing positions by unrealized dollar loss. Do not select profitable positions solely to fill four sales.
- No immediate repurchase of a stock sold during the same daily cycle.
- Volatility: standard deviation of split/dividend-adjusted daily returns over the trailing 12 months; require adequate history rather than guessing missing values.
- SG&A comparison: latest quarter versus the same quarter last year. Flag missing, incomparable, or zero/negative-base values for review.
- Missing essential evidence blocks autonomous entry and appears visibly on Radar.
- Technical completion uses daily closing-price breakout/breakdown confirmation; detailed geometric detector thresholds need documented validation.
- Paper signals use information available at that time, with fills at the next available trading-session open. Stop gaps use the available execution price, not a guaranteed threshold fill.
- No automatic top-ups or rebalancing initially. Fundamental deterioration produces a review alert pending a settled exit rule.

## Evaluation and dashboard

Radar, Buy-ready, Holdings, and Sell alerts, with daily refresh, source timestamps, evidence, and an auditable decision/transaction history. Track cash, realized/unrealized returns, dividends, and equity value.

Five-year analysis and intended holding horizon; compare portfolio total returns and Sharpe with the S&P 500. Exact risk-free series, benchmark data, trading costs, and historical universe must be specified before reporting a validated backtest. No performance has been demonstrated.

## Data direction

Start with free-access data and open-source tooling. Candidate sources: SEC filings for fundamentals and headquarters evidence, and yfinance for personal research market data. These are provisional sources, not validated coverage guarantees.

- SEC APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- yfinance scope and terms: https://github.com/ranaroussi/yfinance/blob/main/README.md

Data-provider rights and reliability must be reassessed for sharing through MCP.
