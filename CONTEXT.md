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
The five-year period Gary intends to own a stock, subject to exit exceptions that remain to be defined.

**Purchase-price stop**:
A −25% stop-loss threshold measured from the purchase price. The reference for multiple purchases and the triggered action remain unresolved.

**Fundamental eligibility**:
The required combination of P/E below 30, dividend yield above 2%, and historical revenue growth above 15%. The P/E basis and growth window remain unresolved.

**Entry timing**:
The decision about when to purchase a fundamentally eligible stock, informed by technical signals. It is distinct from security selection and position sizing.

**Technical exit**:
A decision to sell based on chart conditions. The specific conditions and their precedence relative to other exit rules remain unresolved.

**Cash allocation**:
The portion of the dedicated portfolio held as cash rather than invested in stocks.
