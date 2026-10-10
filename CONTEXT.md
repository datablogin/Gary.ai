# Gary.ai

The domain language for developing a stock-selection and portfolio-allocation strategy for US exchange-listed equities.

## Language

**Investment universe**:
Operating-company common stocks listed on US stock exchanges eligible for consideration. Treatment of ADRs and the boundary of an operating company remain to be clarified.

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
