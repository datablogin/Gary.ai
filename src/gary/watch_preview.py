"""Local source adapter for the approved manual-watch interface.

Provider observations never create reviewed fundamental coverage. Raw receipts,
personal membership and operator-reviewed snapshots stay under the fixed private
directory. Refresh jobs do not hold the preview's training/review write lock.
"""

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from math import isfinite
import os
from pathlib import Path
import re
from statistics import stdev
import tempfile
from threading import Lock, Thread
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from gary.patterns_v2 import VERSION, PARAMETER_HASH, detect_patterns
from gary.watch import ManualWatchStore


DEFAULT_WATCH = Path.cwd() / "private" / "watch"
RETAINED_MARKET = Path.cwd() / "private" / "equity-lists" / "2026-10-12"
STATIC = Path(__file__).with_name("static")
NEW_YORK = ZoneInfo("America/New_York")
RULES = [
    {"name": "Breaking out", "direction": "Buy", "rule": "First daily close more than 0.5% above the prior 20-session high."},
    {"name": "Rolling over", "direction": "Sell", "rule": "First daily close more than 0.5% below the prior 20-session low while the 50-day average falls."},
    {"name": "Gapping up", "direction": "Observe", "rule": "Open at least 2% above the previous close. Still requires a completed buy pattern."},
]


def _finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
    except OverflowError:
        return False


def _completed_cutoff():
    now = datetime.now(NEW_YORK)
    cutoff = now.date()
    if now.time() < time(16):
        cutoff -= timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= timedelta(days=1)
    return cutoff.isoformat()


def _atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary = output.name
            os.fchmod(output.fileno(), 0o600)
            json.dump(value, output, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def _quote_observations(raw, price):
    parser = _VisibleText()
    parser.feed(raw.decode("utf-8"))
    fields = {}
    for label in ("PE Ratio (TTM)", "EPS (TTM)", "Forward Dividend & Yield"):
        if label in parser.parts:
            index = parser.parts.index(label) + 1
            if index < len(parser.parts):
                fields[label] = parser.parts[index]
    def number(label):
        value = fields.get(label, "").replace(",", "")
        match = re.match(r"^(-?\d+(?:\.\d+)?)(?:\s|$)", value)
        result = float(match[1]) if match else None
        return result if _finite(result) else None
    eps = number("EPS (TTM)")
    rate = number("Forward Dividend & Yield")
    observations = {}
    # The visible forward yield may use a different live quote. Use the
    # retained completed close, and still require dividend-policy review.
    if eps is not None and eps != 0:
        observations["trailing_pe"] = price / eps
    elif eps is None and number("PE Ratio (TTM)") is not None:
        observations["trailing_pe"] = number("PE Ratio (TTM)")
    if rate is not None and rate >= 0:
        observations["dividend_yield"] = rate / price
    return observations, fields


def _chart_record(raw, symbol, as_of):
    data = json.loads(raw)
    result = data["chart"]["result"]
    if not isinstance(result, list) or len(result) != 1:
        raise ValueError("Provider returned no unique daily chart")
    chart = result[0]
    meta = chart["meta"]
    if meta.get("symbol") != symbol:
        raise ValueError("Provider ticker differs from requested ticker; alias review required")
    if meta.get("currency") != "USD" or meta.get("instrumentType") != "EQUITY":
        raise ValueError("Provider chart is not a USD equity; classification review required")
    timestamps, quotes = chart["timestamp"], chart["indicators"]["quote"][0]
    adjusted_series = chart["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    adjusted_closes = {}
    bars = []
    for index, stamp in enumerate(timestamps):
        day = datetime.fromtimestamp(stamp, NEW_YORK).date().isoformat()
        if day > as_of:
            continue
        bar = {"date": day, **{key: quotes[key][index] for key in ("open", "high", "low", "close", "volume")}}
        if any(not _finite(bar[key]) for key in ("open", "high", "low", "close", "volume")):
            raise ValueError("Incomplete OHLCV history; source review required")
        bars.append(bar)
        adjusted_closes[day] = adjusted_series[index] if index < len(adjusted_series) else None
    if len(bars) < 180:
        raise ValueError("Fewer than 180 completed sessions; source review required")
    signals = detect_patterns(bars, as_of)  # validates permitted OHLCV order/relationships
    split_dates = [datetime.fromtimestamp(event["date"], NEW_YORK).date().isoformat()
                   for event in chart.get("events", {}).get("splits", {}).values()]
    recent_splits = [day for day in split_dates if bars[-180]["date"] <= day <= as_of]
    last_year = datetime.fromisoformat(as_of).date() - timedelta(days=365)
    year_bars = [bar for bar in bars if datetime.fromisoformat(bar["date"]).date() >= last_year]
    adjusted_year = [adjusted_closes[bar["date"]] for bar in year_bars]
    returns = [adjusted_year[index] / adjusted_year[index - 1] - 1 for index in range(1, len(adjusted_year))] if all(
        _finite(value) and value > 0 for value in adjusted_year) else []
    if not all(_finite(value) for value in returns):
        raise ValueError("Adjusted return series contains nonfinite values; price-basis review required")
    full_year = year_bars and year_bars[0]["date"] <= (datetime.fromisoformat(as_of).date() - timedelta(days=330)).isoformat()
    year_splits = [day for day in split_dates if last_year.isoformat() <= day <= as_of]
    volatility = stdev(returns) * 252 ** 0.5 if len(returns) >= 200 and full_year and not year_splits else None
    return {"company": meta.get("longName") or meta.get("shortName") or symbol,
            "price": bars[-1]["close"], "chart_cutoff": bars[-1]["date"], "bar_count": len(bars),
            "signals": None if recent_splits else [event for event in signals if event["available_at"] == bars[-1]["date"]],
            "source_warning": "Reported split in the pattern or volatility window requires price-basis review." if recent_splits or year_splits else None,
            "annualized_volatility": volatility, "volatility_return_count": len(returns),
            "volatility_basis": "provider_split_dividend_adjusted_close",
            "volatility_start": year_bars[0]["date"] if year_bars else None,
            "volatility_end": bars[-1]["date"],
            "detector_version": VERSION, "parameter_hash": PARAMETER_HASH}


class WatchDesk:
    """Serve fast local views and bounded, explicitly requested source refreshes."""

    def __init__(self, directory=DEFAULT_WATCH, retained=RETAINED_MARKET):
        self.directory = Path(directory)
        self.retained = Path(retained)
        self.jobs = {}
        self.lock = Lock()
        self.source_lock = Lock()  # one bounded provider job at a time

    def _catalog(self):
        catalog = {}
        path = self.retained / "market-summary.json"
        if path.exists():
            for record in json.loads(path.read_text()):
                symbol = record["symbol"]
                observations = {}
                if _finite(record.get("pe_at_completed_close")):
                    observations["trailing_pe"] = record["pe_at_completed_close"]
                field = record.get("quote_fields", {}).get("Forward Dividend & Yield", "")
                match = re.match(r"^(\d+(?:\.\d+)?)\s", field.replace(",", ""))
                if match and _finite(record.get("price")) and record["price"] > 0:
                    observations["dividend_yield"] = float(match[1]) / record["price"]
                catalog[symbol] = {"company": record.get("name"), "observations": observations,
                                   "observation_dates": {key: record.get("price_date") for key in observations},
                                   "price": record.get("price"), "chart_cutoff": record.get("price_date"),
                                   "checked_at": record.get("fetched_at"), "sources": [
                                       {"label": "Cached market observation", "url": f"https://finance.yahoo.com/quote/{quote(symbol)}/"}],
                                   "observation_note": "Retained October12 research observations; no reviewed management or accounting clearance."}
        snapshot = json.loads((STATIC / "stock-lists.json").read_text())
        for record in snapshot["sell_list"]:
            item = catalog.setdefault(record["symbol"], {})
            item.update({"company": record["company"], "price": record["price"], "chart_cutoff": record["price_date"],
                         "checked_at": record["market_checked_at"], "sources": record["sources"]})
            item.setdefault("observations", {}).update({key: record[key] for key in ("trailing_pe", "dividend_yield", "revenue_growth")})
            item["observation_dates"] = {"trailing_pe": record["price_date"], "dividend_yield": record["price_date"],
                                         "revenue_growth": snapshot["reviewed_as_of"]}
            item["observation_note"] = f"Quarterly results: {record['period']}, reported {record['reported_at']}; latest-period and management clearance still require review."
        cache = self.directory / "cache"
        if cache.exists():
            for path in sorted(cache.glob("*.json")):
                record = json.loads(path.read_text())
                symbol = path.stem
                item = catalog.setdefault(symbol, {})
                # A failed/new quote must not inherit old P/E/yield under a
                # fresh chart receipt. Primary quarter observations retain
                # their own review date and original links.
                observations = {key: value for key, value in item.get("observations", {}).items()
                                if key in {"revenue_growth", "sga_growth"}}
                observations.update(record.get("observations", {}))
                dates = {key: value for key, value in item.get("observation_dates", {}).items()
                         if key in observations}
                dates.update(record.get("observation_dates", {}))
                sources = item.get("sources", []) + record.get("sources", [])
                previous_note = item.get("observation_note")
                item.update(record)
                item["observations"] = observations
                item["observation_dates"] = dates
                item["sources"] = list({source["url"]: source for source in sources}.values())
                if previous_note and previous_note != record.get("observation_note"):
                    item["observation_note"] = previous_note + " " + record.get("observation_note", "")
        reviewed = self.directory / "reviewed"
        if reviewed.exists():
            for path in sorted(reviewed.glob("*.json")):
                record = json.loads(path.read_text())
                if not isinstance(record, dict) or set(record) - {"coverage_snapshot", "sga_investigation_resolved", "sources"}:
                    raise ValueError("Operator-reviewed watch packet has an unsupported envelope")
                item = catalog.setdefault(path.stem, {})
                sources = item.get("sources", []) + record.get("sources", [])
                item.update(record)
                item["sources"] = list({source["url"]: source for source in sources}.values())
        return catalog

    def view(self):
        as_of = _completed_cutoff()
        try:
            catalog = self._catalog()
        except (AttributeError, KeyError, TypeError, ValueError, OSError, OverflowError) as error:
            raise ValueError("Stock evidence could not be verified; check the local source/review packet. Membership is preserved.") from error
        result = ManualWatchStore(self.directory, catalog).view(as_of)
        with self.lock:
            jobs = deepcopy(self.jobs)
        for row in result["manual_list"] + result["radar_list"] + result["buy_ready_list"]:
            record = catalog.get(row["symbol"], {})
            row["refresh"] = jobs.get(row["symbol"])
            row["observation_note"] = record.get("observation_note")
            row["source_warning"] = record.get("source_warning")
            row["annualized_volatility"] = record.get("annualized_volatility")
            count = record.get("volatility_return_count")
            try:
                start = date.fromisoformat(record.get("volatility_start"))
                cutoff = date.fromisoformat(as_of)
                full_year = cutoff - timedelta(days=366) <= start <= cutoff - timedelta(days=330)
            except (TypeError, ValueError):
                full_year = False
            volatility_ready = (_finite(row["annualized_volatility"]) and row["annualized_volatility"] >= 0
                                and isinstance(count, int) and not isinstance(count, bool) and count >= 200
                                and record.get("volatility_basis") == "provider_split_dividend_adjusted_close"
                                and record.get("volatility_end") == as_of and full_year)
            if row["status"] == "buy_ready" and not volatility_ready:
                row["status"] = "needs_review"
                row["why"] += " A retained trailing-year volatility measure with at least 200 returns is still required for candidate priority."
        # Candidate priority is the approved lowest trailing-year volatility.
        # A stock with no retained 200-return measure cannot fill the Buy List.
        result["buy_ready_list"] = [row for row in result["buy_ready_list"] if row["status"] == "buy_ready"]
        result["buy_ready_list"].sort(key=lambda row: (row["annualized_volatility"], row["symbol"]))
        result.update({"detector_version": VERSION, "parameter_hash": PARAMETER_HASH, "pattern_rules": RULES,
                       "freshness_policy": "Completed daily closes only. Weekday cutoff approximation; exchange holidays and provider adjustments require review. A stale/missing chart cannot clear an entry.",
                       "jobs": jobs})
        return result

    def add(self, symbol, note=""):
        ManualWatchStore(self.directory, {}).add(symbol, note)
        normalized = symbol.strip().upper().replace(".", "-")
        try:
            self.refresh(normalized)
        except ValueError as error:
            # Membership was saved. A saturated source queue must not disguise
            # that successful add as a failed persistence operation.
            with self.lock:
                self.jobs[normalized] = {"status": "deferred", "message": str(error) + "; use Refresh checks later."}
        return self.view()

    def remove(self, symbol):
        ManualWatchStore(self.directory, {}).remove(symbol)
        return self.view()

    def refresh(self, symbol):
        # Validate via the approved interface, without changing membership.
        view = ManualWatchStore(self.directory, {}).view(_completed_cutoff())
        normalized = symbol.strip().upper().replace(".", "-") if isinstance(symbol, str) else None
        if normalized not in {row["symbol"] for row in view["manual_list"]}:
            raise ValueError("Add the ticker to your manual watch list before refreshing")
        with self.lock:
            if self.jobs.get(normalized, {}).get("status") in {"queued", "running"}:
                return
            if sum(job["status"] in {"queued", "running"} for job in self.jobs.values()) >= 20:
                raise ValueError("Twenty source refreshes are already queued; wait before adding another")
            self.jobs[normalized] = {"status": "queued", "message": "Waiting for a bounded source check."}
        Thread(target=self._refresh_job, args=(normalized,), daemon=True).start()

    def _receive(self, symbol, kind, url):
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10) as response:
            if response.geturl() != url:
                raise ValueError("Provider redirected the requested source; alias/source review required")
            raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("Provider response exceeds the bounded receipt size")
        received = datetime.now(timezone.utc).isoformat()
        digest = sha256(raw).hexdigest()
        root = self.directory / "receipts" / symbol
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination = root / (digest + "." + kind)
        # Content-addressed receipts cannot replace another response's bytes.
        with destination.open("xb") if not destination.exists() else destination.open("rb") as output:
            if output.writable():
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
        destination.chmod(0o600)
        receipt = {"url": url, "received_at": received, "sha256": digest}
        _atomic_json(root / (digest + ".receipt.json"), receipt)
        return raw, receipt

    def _refresh_job(self, symbol):
        with self.source_lock:
            with self.lock:
                self.jobs[symbol] = {"status": "running", "message": "Checking completed daily bars and visible quote observations."}
            try:
                as_of = _completed_cutoff()
                chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?range=5y&interval=1d&events=div%2Csplits"
                raw, chart_receipt = self._receive(symbol, "chart", chart_url)
                record = _chart_record(raw, symbol, as_of)
                record["checked_at"] = chart_receipt["received_at"]
                record["sources"] = [{"label": "Daily market data", "url": f"https://finance.yahoo.com/quote/{quote(symbol)}/history/"}]
                record["receipts"] = {"chart": chart_receipt}
                quote_url = f"https://finance.yahoo.com/quote/{quote(symbol)}/"
                try:
                    raw, receipt = self._receive(symbol, "quote", quote_url)
                    record["observations"], record["quote_fields"] = _quote_observations(raw, record["price"])
                    if not record["observations"]:
                        raise ValueError("Visible quote metrics are unavailable; no numerical proximity inferred")
                    record["observation_dates"] = {key: record["chart_cutoff"] for key in record["observations"]}
                    record["sources"].append({"label": "Quote observations", "url": quote_url})
                    record["receipts"]["quote"] = receipt
                except (OSError, ValueError, UnicodeError) as error:
                    record["observations"] = {}
                    warning = "Daily chart retained; quote check failed: " + str(error)
                    record["source_warning"] = (record.get("source_warning") + " " if record.get("source_warning") else "") + warning
                record["observation_note"] = "Quote observations use the completed close. Dividend convention, latest comparable quarter, classification and headquarters evidence still require review."
                _atomic_json(self.directory / "cache" / (symbol + ".json"), record)
                job = {"status": "completed", "message": f"Daily chart through {record['chart_cutoff']}. Observations do not grant fundamental clearance.",
                       "checked_at": record["checked_at"]}
            except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
                job = {"status": "failed", "message": "Source check failed; retained evidence kept. " + str(error),
                       "checked_at": datetime.now(timezone.utc).isoformat()}
            with self.lock:
                self.jobs[symbol] = job
