# Gary.ai

The domain language for developing a stock-selection and portfolio-allocation strategy for US exchange-listed equities.

## Language

**Investment universe**:
Operating-company common stocks listed on US stock exchanges, excluding ADRs, REITs, BDCs, and SPACs.

**Stock-selection strategy**:
The explicit criteria and reasoning used to choose equities from the investment universe.

**Portfolio allocation**:
The share of portfolio capital assigned to a selected equity.
_Avoid_: Stock selection (when referring to position size)

**Dedicated stock portfolio**:
The portfolio whose allocations are determined independently of the investor’s other investments.

**Share block**:
A unit of 100 shares used for position sizing; positions consist of whole blocks.

**Benchmark**:
The S&P 500 reference used to assess portfolio performance over a five-year horizon. Price-return versus total-return treatment remains unresolved.

**Analysis period**:
The five-year period used to analyze the strategy; historical versus forward-looking treatment remains unresolved.

**Intended holding period**:
The five-year period Gary intends to own a stock, subject to earlier technical exits or the purchase-price stop.

**Purchase-price stop**:
A −25% threshold measured from weighted-average purchase price that requires selling the entire position.

**Fundamental eligibility**:
The required combination of trailing P/E below 30, dividend yield above 2%, and latest-quarter revenue growth above 15% compared with the same quarter of the prior year.

**Entry timing**:
The decision about when to purchase a fundamentally eligible stock, informed by technical signals. It is distinct from security selection and position sizing.

**Technical exit**:
A decision to sell based on chart conditions. The specific conditions and their precedence relative to other exit rules remain unresolved.

**Cash allocation**:
The portion of the dedicated portfolio held as cash rather than invested in stocks.

**Radar list**:
Fundamentally eligible stocks awaiting a favorable technical entry.
_Avoid_: Holdings (for stocks not yet purchased)

**Portfolio loss tolerance**:
A −10% decline from initial capital that triggers sale of the four biggest dollar-loss contributors, with new buys permitted immediately afterward. Repeat-trigger behavior remains unresolved.

**Weighted-average purchase price (WAPP)**:
The average purchase price of the held shares weighted by the number of shares purchased at each price.

**Initial equal allocation**:
An initial target of $8,000 per position across 25 allocation slots, rounded down to whole 100-share blocks. Unused slots and rounding residuals stay in cash.

**Detected pattern**:
A chart pattern identified automatically by Gary.ai, optionally submitted to Gary for confirmation.

**Paper portfolio**:
A simulated dedicated stock portfolio starting with $200,000 in cash. Its positions and transactions are tracked independently of Gary’s actual holdings.

**Quarterly revenue growth**:
The percentage change in the latest reported quarter’s revenue compared with the same quarter of the previous year.

**Candidate priority**:
The order in which eligible entry candidates receive available allocation slots, starting with the lowest volatility. Volatility is measured over the last 12 months; the calculation convention is a provisional implementation choice.

**Management screen**:
Gary’s assessment of management through evidence of headquarters investment and significant SG&A increases. New headquarters investment is a hard exclusion; a 25% SG&A increase is considered large and requires investigation.
