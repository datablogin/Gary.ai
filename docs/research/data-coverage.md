# Free-data coverage pilot

Research date: October 10, 2026, America/Chicago. Actual HTTP probes ran October 11, 2026, 00:41–00:43 UTC, which is October 10 locally. These are observations at that time, not claims about future availability or investment attractiveness.

## Decision

Free-access sources support a local research prototype. They do **not yet support unattended screening of the entire eligible universe or a validated five-year backtest**. Develop a source-independent coverage report first, and make absent, stale, incomparable, and unreviewed evidence visible blockers to autonomous entry.

Use Nasdaq's symbol files for candidate discovery, SEC submissions/companyfacts for filing-aware financial evidence, and a replaceable Yahoo/yfinance adapter for personal research prices. Keep issuer and filing review as an explicit source of classification and headquarters evidence. The strongest observed problems are latest-quarter freshness, dividend units, and incomplete security classification.

## Measured sample and denominators

Purposive sample: five companies from Gary's interview (MU, AMGN, SIRI, META, ORCL) and three exclusion controls (TSM: depositary share; O: REIT; ARCC: BDC). No SPAC was probed. Eight familiar surviving tickers cannot establish universe-wide coverage, historical delisting coverage, or reliability under load.

| Capability | Measured result | Interpretation |
|---|---|---|
| SEC ticker/exchange lookup | 8/8 sample symbols found in one HTTP-200 directory response | Identity candidate only; not a security-type classifier |
| Nasdaq listing lookup | 8/8 found across two HTTP-200 symbol files | Listing and security-name evidence; exclusions still need additional evidence |
| Yahoo five-year daily bars | 8/8 responses; 1,255 complete OHLCV plus adjusted-close rows per symbol | 2021-10-11 through 2026-10-09; structural validation only |
| Yahoo trailing calendar 12 months | 8/8; 251 complete bars per symbol | Window starts 2025-10-10; there are 250 within-window close-to-close returns, or 251 if the preceding close is supplied |
| Yahoo current trailing P/E and dividend fields | 8/8 through yfinance 1.7.0 | Snapshot fields present; units and economic meaning require normalization |
| Yahoo quarterly revenue and SG&A comparison pair | 5/5 operating-company samples | At least the latest **vendor** quarter and its prior-year pair exist; MU vendor latest is stale |
| SEC companyfacts API access | 1/8: MU succeeded; seven other CIKs returned HTTP 403 | Access validation incomplete; denial is not proof those companies lack facts |
| SEC submissions API access | 1/8: MU succeeded; seven others returned HTTP 403 | Same limitation |
| Manual identification of three exclusions | 3/3 with issuer/filing evidence below | No automated general classifier validated |
| Automated headquarters clearance | 0/5 operating samples validated | A search returning nothing cannot establish the absence of an investment |

All eight chart responses have zero duplicate timestamps and zero tested OHLC/positive-price/nonnegative-volume invariant failures. Each row has finite open, high, low, close, volume, and adjusted close. All report USD and the broad type `EQUITY`, including all three excluded controls. An exchange calendar reconciliation, independent price reconciliation, and adjustment accuracy audit were **not performed**. Coverage counts describe retrieval, not economic correctness.

Private probe logs and vendor payloads are in `private/coverage/` (Git-ignored). Public documentation intentionally does not redistribute full Yahoo datasets.

## Current field observations

The table reports received fields, not recommendations. `dividendYield` is observed in percentage points; `trailingAnnualDividendYield` is a fraction. They also describe different yield conventions and must not be substituted without a policy.

| Symbol | Yahoo trailing P/E | Yahoo dividendYield (%) | Yahoo trailingAnnualDividendYield (fraction) | Latest vendor revenue quarter | SEC direct facts/submissions |
|---|---:|---:|---:|---|---|
| MU | 13.84367 | 0.06 | 0.00054545107 | 2026-05-31; stale versus SEC annual filing | 200 / 200 |
| AMGN | 25.768322 | 2.43 | 0.024052622 | 2026-06-30 | 403 / 403 |
| SIRI | 10.604 | 4.07 | 0.041017853 | 2026-06-30 | 403 / 403 |
| META | 27.078747 | 0.29 | 0.0029130655 | 2026-06-30 | 403 / 403 |
| ORCL | 22.163008 | 1.41 | 0.014793993 | 2026-08-31 | 403 / 403 |
| TSM | 32.94404 | 0.83 | 0.0567698 | Not probed | 403 / 403 |
| O | 39.260868 | 6.01 | 0.059719402 | Not probed | 403 / 403 |
| ARCC | 13.850745 | 10.34 | 0.10245464 | Not probed | 403 / 403 |

AMGN's indicated annual dividend field 10.08 divided by the received price 414.87 is approximately 2.43%, corroborating the percentage-unit interpretation. TSM's trailing annual dividend amount is 26 while its indicated dividend amount is 3.77 and quote currency USD; that discrepancy needs currency/share-basis investigation and is another reason not to treat every Yahoo field as interchangeable. TSM is already excluded by security type. Observations come from the cached first-party Yahoo responses requested by [yfinance's quote adapter](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/quote.py).

Proposed dividend policy for review: choose one documented convention (trailing cash distributions over 12 months, or indicated regular annual dividends), store numerator, denominator, currency, share basis, and effective time, and compare the normalized fractional yield to `0.02`. Gary has not yet selected between trailing and indicated yield. Do not infer absence of a dividend from a null response.

## Quarterly financial coverage and the freshness failure

Below are the received vendor values in USD millions. Growth is `(current / prior_year - 1) * 100`, computed without intermediate rounding. These are vendor comparison pairs, not a validated entire-universe screen.

| Symbol | Vendor quarter / prior-year quarter | Revenue pair | Revenue growth | SG&A pair | SG&A growth |
|---|---|---:|---:|---:|---:|
| MU | 2026-05-31 / 2025-05-31 | 41,456 / 9,301 | 345.7155% | 407 / 318 | 27.9874% |
| AMGN | 2026-06-30 / 2025-06-30 | 10,054 / 9,179 | 9.5326% | 1,745 / 1,691 | 3.1934% |
| SIRI | 2026-06-30 / 2025-06-30 | 2,160 / 2,138 | 1.0290% | 324 / 351 | −7.6923% |
| META | 2026-06-30 / 2025-06-30 | 60,801 / 47,516 | 27.9590% | 9,040 / 5,642 | 60.2269% |
| ORCL | 2026-08-31 / 2025-08-31 | 19,345 / 14,926 | 29.6061% | 2,187 / 2,439 | −10.3321% |

Primary releases corroborate AMGN's revenue and SG&A pairs ([August 4 release](https://investors.amgen.com/news-releases/news-release-details/amgen-reports-second-quarter-2026-financial-results/)); SIRI's revenue pair and separate sales/marketing plus general/administrative components ([July 30 filing exhibit](https://investor.siriusxm.com/sec-filings/all-sec-filings/content/0000908937-26-000020/siriq22026earningsrelease.htm)); META's revenue pair and marketing/sales plus general/administrative components ([July 29 release](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/)); and ORCL's revenue pair ([Q1 fiscal 2027 release](https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Q1-Results-Driven-by-Triple-Digit-Growth-in-Cloud-Infrastructure-Revenues/default.aspx)). This limited corroboration is not a reconciled point-in-time adapter. ORCL's SG&A pair was not separately reconciled to its issuer release in this pilot.

**MU demonstrates why “five quarters returned” is insufficient.** [SEC submissions](https://data.sec.gov/submissions/CIK0000723125.json) shows a 10-K, accession `0000723125-26-000023`, filed 2026-10-09 and accepted 2026-10-09T16:21:00Z, reporting the year ended 2026-09-03. Yahoo's quarterly table still stops at its label 2026-05-31. The corresponding SEC Q3 actual end is 2026-05-28, not that vendor month-end label.

The [MU companyfacts response](https://data.sec.gov/api/xbrl/companyfacts/CIK0000723125.json) contains standard-tag annual and nine-month facts sufficient to reconstruct the newly reported fourth quarter, subject to validation:

- Revenue: FY2026 133,188 minus nine-month 78,959 = 54,229 million; FY2025 37,378 minus nine-month 26,063 = 11,315 million.
- SG&A: FY2026 1,947 minus nine-month 1,088 = 859 million; FY2025 1,205 minus nine-month 891 = 314 million.
- The 2026 derived period runs 2026-05-29 to 2026-09-03, while its prior-year counterpart runs 2025-05-30 to 2025-08-28. The extra fiscal week needs an explicit comparability flag. Do not silently equate fiscal and calendar quarters.

The current standard revenue tag is `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; current SG&A is `us-gaap:SellingGeneralAndAdministrativeExpense`, both USD. MU also has older `Revenues` and `SalesRevenueNet` tags with no recent rows: blindly selecting the first tag present would return old evidence. A dated, entity-specific semantic mapping must select the correct consolidated revenue measure.

### Required SEC normalization behavior

SEC's APIs expose entity-wide standard taxonomy facts; custom tags and dimensional facts may require original filing extraction. The API does not guarantee a complete standardized quarterly income statement for every issuer. Submissions provide filing metadata; financial periods may differ from calendar quarters. [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

Implement these as decisions, not heuristics that always produce a number:

1. Resolve security identity and CIK before selecting facts. A CIK identifies the filing entity, not a particular listed share class. Preserve symbol changes and corporate actions; multiple share classes can share a CIK.
2. Retain `start`, `end`, `unit`, taxonomy/concept, accession, form, `filed`, fiscal year/period, and linked acceptance time. `fy`/`fp` can describe the **filing**, including its prior-year comparative facts; never use them alone to date the fact.
3. Prefer an explicit three-month consolidated fact. Do not confuse a three-, six-, or nine-month value sharing the same `end`. Derive a quarter from compatible YTD differences only when currency, concept, entity scope, fiscal-year boundaries, and restatement basis agree. For Q4, validate FY minus nine months and retain both inputs and their availability times.
4. Resolve amendments and duplicate disclosures by accession and availability. Historical runs select evidence available on or before the decision time, not a later amended number. Use acceptance time when available; if only a filing date is known, a conservative end-of-date availability policy must be explicit.
5. For SG&A, allow a verified consolidated combined tag or documented components (e.g. marketing/sales plus G&A). Do not confuse G&A alone, total operating expense, or segment expense with combined SG&A. Missing standard tags may require issuer-specific mapping; do not substitute zero.
6. Require positive comparable denominators for growth. Report missing, zero/negative base, changed accounting scope, unit differences, and extra fiscal weeks. A threshold breach is an investigation flag; it does not prove headquarters spending.
7. Validate latest **reported** financial period against filing metadata or dated issuer releases before permitting a buy. A stale vendor table remains stale even if it contains valid prior-year pairs.

## Classification and headquarters evidence

[Nasdaq symbol definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs) describe security names, exchange, test issue and ETF fields. The fetched files have creation timestamp `1009202621:31`. They identify the five interview securities as common stock, ARCC as a closed-end fund, O as common stock, and TSM by issuer name without depositary-share wording. A classifier using only “common stock” or `ETF=N` would incorrectly admit O or miss TSM's exclusion.

- TSM: the issuer says its NYSE TSM security is American Depositary Shares. Exclude. [TSMC FAQ](https://investor.tsmc.com/english/faq).
- O: its issuer-hosted 2024 10-K explicitly identifies its REIT structure. Exclude. [Realty Income 10-K](https://www.realtyincome.com/sites/realty-income/files/2025-02/O-%2012.31.24%2010K%20Document%20Final.pdf).
- ARCC: its SEC registration statement identifies its BDC election. Exclude; the linked statement was found through SEC's indexed primary-source extract, but a subsequent full-page fetch failed. [ARCC registration statement](https://www.sec.gov/Archives/edgar/data/1287750/000110465925000820/arcc-20250102xn2.htm).

MU's submission metadata says `entityType=operating` and SIC 3674; that alone cannot classify all exclusions. Foreign issuer status is not synonymous with an ADR, nor is real-estate industry synonymous with REIT. Use filing/issuer evidence with an effective date. Unknown security type blocks entry. Add explicit SPAC/shell, preferred, unit, warrant, ETF, and other fund controls in the next coverage study.

Keep Gary's 100-share unit as a strategy constraint. It is not an exchange round-lot assumption: the received Nasdaq directory reports 40 for MU, AMGN, META and TSM, and 100 for the other controls.

Headquarters investment has no validated universal field in this source stack. SG&A growth is an alert, while a headquarters investment might also appear in leases, property/capital commitments, or narrative disclosures. Do not use an unchanged headquarters address or SG&A below 25% as clearance.

Oracle provides a useful positive evidence case: Nashville's October 3, 2024 official statement reports the planned future Oracle headquarters and associated campus investment. Oracle's current office page still labels Austin as world headquarters, demonstrating that an address lookup misses planned commitments. [Nashville statement, PDF page 120](https://www.nashville.gov/sites/default/files/2024-10/TNNashville06b-POS.pdf), [Oracle offices](https://www.oracle.com/corporate/contact/field-offices/).

Proposed evidence states: `confirmed_investment` (exclude), `reviewed_no_disqualifying_evidence` (requires bounded sources, reviewer and lookback), `unknown` (block). Gary has not specified the lookback or whether announced commitments, leases, renovations, and completed buildings all qualify. Preserve those unresolved decisions; do not grant automatic clearance to this sample.

## Prices, adjustments, and historical limits

Fetch daily bars with explicit `auto_adjust=False`, `actions=True`, date bounds, regular session only, and pinned adapter version. Store provider close, adjusted close, dividend/split events, exchange timezone, fetch time, and adjustment policy. yfinance's `auto_adjust` multiplies open/high/low by `Adj Close / Close` and replaces close with adjusted close; defaults must not silently decide execution prices. [Adjustment implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/utils.py), [history implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py).

Use a consistent adjusted-return series for the agreed volatility ranking. Keep corporate-action-aware price bars separate for pattern geometry and actual market prices separate for paper fills, marks, WAPP and stops. Yahoo historical OHLC can already reflect splits; `auto_adjust=False` does **not** guarantee original pre-split trade prices. A split must transform held share count and WAPP together without creating profit or triggering a false stop. SIRI's returned 1:10 event on 2024-09-10 is a real-data fixture candidate; O includes a 1032:1000 event on 2021-11-15, so avoid assuming every event is a simple integer split.

Do not book dividends both through adjusted-close appreciation and a cash ledger. The chart event timestamp alone is not a verified dividend payment date. Future paper accounting needs ex-date entitlement and payment timing. Adjustment data downloaded today can reflect later corporate actions or corrections; store daily snapshots going forward, and do not claim point-in-time historical market/fundamental evidence from current `.info` fields.

Five-year charts for surviving securities are insufficient for a historical strategy backtest. That requires a dated universe including delistings, point-in-time classifications/fundamentals, benchmark total-return data, risk-free series, corporate-action accounting, and realistic fill/cost conventions. None were validated here.

## Minimal adapter proposal and fail-closed contract

| Adapter | Responsibility | Initial limitation |
|---|---|---|
| Listing adapter | Nasdaq listing snapshots; SEC ticker/CIK cross-check; security identifiers | Current universe only; classification is separate |
| Market adapter | Yahoo through pinned yfinance for daily prices/actions; auditable snapshot | Personal research; no availability guarantee |
| Filing adapter | SEC submissions + companyfacts + explicit original-filing fallback | Seven sampled CIKs blocked in this run; custom mappings needed |
| Issuer evidence adapter | Dated primary releases, classification, headquarters references | Curated evidence initially; no universal automated clearance |
| Coverage service | `coverage_report(symbol, as_of, snapshot)` evaluates evidence and returns reasons | Pure normalization independent of live fetch and strategy decisions |

The coverage seam should report per-field `available`, `missing`, `stale`, `incomparable`, `future`, or `unreviewed`; source/filing identifiers; actual measurement periods; provider fetch time; publication/acceptance time; currency/share basis; and denominator. Essential failures block autonomous entry but preserve the symbol and reason on Radar. A network error must not become “no dividend,” zero volatility, zero SG&A, or no headquarters investment. Portfolio exits requiring prices need a separate missing-price handling policy; no fabricated fills.

Proposed release gates: all named controls produce explicit classification/evidence results; latest-quarter mismatch and dividend-unit fixtures block or normalize correctly; raw and adjusted price series remain distinguishable; stale/missing responses cannot create orders; no-lookahead checks use availability timestamps. Expand the sample and reconcile against original filings before making full-universe claims.

## Access and distribution

Initial MU SEC requests succeeded using a demonstration contact header; that is not a deployment contact or proof a production fetcher is configured correctly. Subsequent project-identified requests received 403 for seven CIKs. One bounded retry of AMGN companyfacts was denied, after which retries stopped. The browser research tool also could not open that AMGN API URL. Configure a genuine operator contact, cache, and conservative rate limit before revalidating. Do not interpret 403 as empty financial data or attempt to defeat access restrictions. SEC asks for efficient downloads and limits aggregate access to ten requests per second. [SEC developer resources](https://www.sec.gov/about/developer-resources).

yfinance's Apache software license applies to the **library**, not to permission to redistribute Yahoo's data. Its authors describe the underlying Yahoo API as personal-use and direct users to Yahoo's terms. Thus the proposed adapter is for this single-user local research prototype; public GitHub code or an MCP transport does not grant data redistribution rights. The eventual MCP needs user-owned provider access or a provider agreement allowing the intended use. This pilot did not conduct a legal rights review. [yfinance README and terms links](https://github.com/ranaroussi/yfinance/blob/main/README.md).

## Reproduction

The exact requested chart URL was `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?range=5y&interval=1d&events=div%2Csplits`. Substitute the eight symbols above. Each raw response and fetch record was retained privately. SEC URLs are `https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK:010d}.json` and `https://data.sec.gov/submissions/CIK{CIK:010d}.json`; tested CIKs respectively are 723125, 318154, 908937, 1326801, 1341439, 1046179, 726728, and 1287750. Discovery URLs: [SEC exchange directory](https://www.sec.gov/files/company_tickers_exchange.json), [Nasdaq-listed file](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt), [other-listed file](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt).

The yfinance probes ran in an isolated uv temporary environment, with no repository environment/configuration edits:

```bash
uv run --no-project --with yfinance==1.7.0 python - <<'PY'
import yfinance as yf
for symbol in ['MU', 'AMGN', 'SIRI', 'META', 'ORCL', 'TSM', 'O', 'ARCC']:
    info = yf.Ticker(symbol).get_info()
    print(symbol, {key: info.get(key) for key in [
        'trailingPE', 'trailingEps', 'dividendYield', 'dividendRate',
        'trailingAnnualDividendYield', 'trailingAnnualDividendRate',
        'regularMarketPrice', 'currency', 'quoteType']})
for symbol in ['MU', 'AMGN', 'SIRI', 'META', 'ORCL']:
    print(symbol, yf.Ticker(symbol).quarterly_income_stmt)
PY
```

Private evidence index: `initial-probes.json`, `sample-probes.json`, `sec-retries.json`, `chart-summary.json`, `yfinance-info-probes.json`, `yfinance-quarterly-probes.json`, raw responses/CSV tables, and `artifact-manifest.json` with SHA-256 hashes. Re-running will fetch a new snapshot and can legitimately return different results. This report is the durable record of this pilot; no application or tests were written by the data research member.
