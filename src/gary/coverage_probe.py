"""Summarize the private pilot or run bounded, opt-in personal price probes.

This CLI reports retrieval evidence, never automatic investment clearance.
It does not print or redistribute complete provider price datasets.
"""

import argparse
import json
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SAMPLE = ("MU", "AMGN", "SIRI", "META", "ORCL", "TSM", "O", "ARCC")
OPERATING_SAMPLE = SAMPLE[:5]
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "private" / "coverage"
MAX_BYTES = 8 * 1024 * 1024


def _numeric(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        return False


def _load_records(directory, filename, failures):
    try:
        records = json.loads((directory / filename).read_text())
        if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
            raise ValueError("expected a list of probe records")
        return records
    except (OSError, ValueError) as error:
        failures.append({"artifact": filename, "status": "unavailable", "reason": str(error)})
        return []


def _http_summary(records, url_fragment, denominator):
    matches = {record["url"]: record for record in records if url_fragment in record.get("url", "")}
    return {
        "expected_sample": denominator,
        "observed_attempts": len(matches),
        "http_200": sum(record.get("status") == 200 and not record.get("error") for record in matches.values()),
        "failed": sum(record.get("status") != 200 or bool(record.get("error")) for record in matches.values()),
    }


def _quarter_pair_present(record, field):
    quarters = record.get("quarters", [])
    values = record.get(field, {})
    if not quarters or not isinstance(values, dict):
        return False
    latest = max(quarters)
    try:
        prior = str(int(latest[:4]) - 1) + latest[4:]
    except (ValueError, TypeError):
        return False
    return _numeric(values.get(latest)) and _numeric(values.get(prior))


def cached_summary(directory=DEFAULT_CACHE):
    """Return only measured statuses, field presence and provenance summaries."""
    directory = Path(directory)
    failures = []
    probes = _load_records(directory, "initial-probes.json", failures)
    probes += _load_records(directory, "sample-probes.json", failures)
    retries = _load_records(directory, "sec-retries.json", failures)
    charts = _load_records(directory, "chart-summary.json", failures)
    info = _load_records(directory, "yfinance-info-probes.json", failures)
    quarters = _load_records(directory, "yfinance-quarterly-probes.json", failures)
    info_by_symbol = {record["symbol"]: record for record in info if record.get("symbol") in SAMPLE}
    quarters_by_symbol = {record["symbol"]: record for record in quarters if record.get("symbol") in OPERATING_SAMPLE}
    result = {
        "mode": "cached_pilot",
        "status": "partial" if failures else "available",
        "sample": list(SAMPLE),
        "operating_sample": list(OPERATING_SAMPLE),
        "buy_allowed": False,
        "limitations": [
            "Purposive sample; no all-universe or delisting coverage claim.",
            "Presence and HTTP access do not establish freshness, comparability or economic correctness.",
            "No sampled company has validated automatic headquarters clearance.",
            "MU vendor quarter lags the filing-aware latest reported quarter; see data-coverage.md.",
            "Dividend convention/share basis, price adjustment and exchange calendars need separate review.",
            "Cached artifacts are pilot evidence, not normalized coverage snapshots or automatic candidate clearance.",
        ],
        "artifact_failures": failures,
        "http_access": {
            "companyfacts": _http_summary(probes, "/api/xbrl/companyfacts/", 8),
            "submissions": _http_summary(probes, "/submissions/", 8),
            "daily_charts": _http_summary(probes, "/finance/chart/", 8),
            "listing_files": _http_summary(probes, "/dynamic/SymDir/", 2),
        },
        "field_presence": {},
        "chart_structure": [
            {key: record.get(key) for key in ("symbol", "rows", "first_date", "last_date", "complete_ohlcv_adj_rows", "recent_12mo_complete_rows", "duplicate_timestamps", "ohlc_invariant_bad_rows")}
            for record in charts if record.get("symbol") in SAMPLE
        ],
        "source_probes": [
            {"url": record.get("url"), "fetched_at": record.get("started_at_utc"), "http_status": record.get("status"), "error": record.get("error")}
            for record in probes
        ],
        "bounded_retry_failures": [
            {"url": record.get("url"), "fetched_at": record.get("started_at_utc"), "error": record.get("error")}
            for record in retries
        ],
        "quote_snapshots": [
            {"symbol": symbol, "fetched_at": record.get("started_at_utc"), "adapter_version": record.get("yfinance_version")}
            for symbol, record in info_by_symbol.items()
        ],
        "vendor_quarters": [
            {"symbol": symbol, "fetched_at": record.get("started_at_utc"), "latest_vendor_label": max(record.get("quarters") or [""]), "verified_latest_reported": False}
            for symbol, record in quarters_by_symbol.items()
        ],
    }
    for field in ("trailingPE", "dividendYield", "trailingAnnualDividendYield"):
        result["field_presence"][field] = {
            "expected_sample": 8,
            "observed_symbols": len(info_by_symbol),
            "present": sum(_numeric(record.get("observed", {}).get(field)) for record in info_by_symbol.values()),
        }
    for field in ("Total Revenue", "Selling General And Administration"):
        result["field_presence"][field] = {
            "expected_operating_sample": 5,
            "observed_symbols": len(quarters_by_symbol),
            "vendor_prior_year_pair_present": sum(_quarter_pair_present(record, field) for record in quarters_by_symbol.values()),
            "latest_reported_verified": False,
        }
    return result


def _live_chart(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?" + urlencode({"range": "5y", "interval": "1d", "events": "div,splits"})
    started = datetime.now(timezone.utc).isoformat()
    result = {"symbol": symbol, "source_url": url, "fetched_at": started, "buy_allowed": False}
    try:
        request = Request(url, headers={"User-Agent": "Gary.ai/0.1 personal-research"})
        with urlopen(request, timeout=10) as response:
            result["http_status"] = response.status
            payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("response exceeds the bounded 8 MiB payload limit")
        data = json.loads(payload)
        chart = data["chart"]["result"][0]
        timestamps = chart.get("timestamp", [])
        quotes = chart["indicators"]["quote"][0]
        complete = sum(
            all(index < len(quotes.get(key, [])) and _numeric(quotes[key][index]) for key in ("open", "high", "low", "close", "volume"))
            for index in range(len(timestamps))
        )
        cache = DEFAULT_CACHE / "live"
        cache.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{symbol}-chart.raw"
        (cache / filename).write_bytes(payload)
        result.update({"status": "retrieved" if timestamps else "missing", "daily_rows": len(timestamps), "complete_ohlcv_rows": complete, "raw_cache": str(cache / filename), "classification": "unknown", "fundamentals": "unreviewed"})
    except HTTPError as error:
        result.update({"status": "access_failure", "http_status": error.code, "reason": str(error)})
    except (URLError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        result.update({"status": "unavailable", "reason": str(error)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help="read-only cached pilot directory")
    parser.add_argument("--live", action="store_true", help="opt in to at most eight Yahoo personal-research chart requests; no retries")
    parser.add_argument("--symbols", default="MU", help="comma-separated symbols from the named pilot sample, for --live")
    args = parser.parse_args(argv)
    if args.live:
        symbols = list(dict.fromkeys(args.symbols.split(",")))
        if not symbols or len(symbols) > 8 or any(symbol not in SAMPLE for symbol in symbols):
            parser.error("live symbols must be 1–8 distinct members of " + ", ".join(SAMPLE))
        result = {"mode": "bounded_live_prices", "attempted": len(symbols), "probes": [_live_chart(symbol) for symbol in symbols], "buy_allowed": False, "scope": "Price retrieval only; no classification/fundamental/headquarters clearance."}
    else:
        result = cached_summary(args.cache_dir)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
