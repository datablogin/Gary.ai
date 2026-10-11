"""Pure, evidence-aware evaluation of curated coverage snapshots."""

from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
from math import isfinite
from zoneinfo import ZoneInfo

EXCLUDED_TYPES = {"adr", "reit", "bdc", "spac", "etf", "fund", "preferred", "unit", "warrant"}
US_EXCHANGES = {"NYSE", "NASDAQ", "NYSE_AMERICAN", "NYSE_ARCA", "CBOE_BZX"}
NEW_YORK = ZoneInfo("America/New_York")


def _cutoff(as_of):
    if not isinstance(as_of, str):
        raise ValueError("as_of requires an ISO date or offset timestamp")
    if len(as_of) == 10:
        return datetime.combine(date.fromisoformat(as_of), time(16), NEW_YORK)
    cutoff = datetime.fromisoformat(as_of)
    if cutoff.tzinfo is None:
        raise ValueError("as_of timestamps require an explicit offset")
    return cutoff.astimezone(NEW_YORK)


def _availability(record, cutoff):
    if not isinstance(record, dict):
        return "missing"
    if record.get("status", "available") != "available":
        status = record["status"]
        return status if status in ("access_failure", "missing", "stale", "incomparable", "future", "unreviewed") else "unreviewed"
    if "current" in record or "prior_year" in record:
        statuses = [_availability(record.get(key), cutoff) for key in ("current", "prior_year")]
        return next((status for status in statuses if status != "available"), "available")
    try:
        source = record["source"]
        if not isinstance(source, dict):
            return "unreviewed"
        if not isinstance(source.get("url"), str) or not source["url"].strip():
            return "unreviewed"
        fetched = datetime.fromisoformat(source["fetched_at"])
        if fetched.tzinfo is None:
            return "unreviewed"
        published = source["available_at"]
        if len(published) == 10:
            return "future" if date.fromisoformat(published) >= cutoff.date() else "available"
        timestamp = datetime.fromisoformat(published)
        if timestamp.tzinfo is None:
            return "unreviewed"
        return "future" if timestamp > cutoff else "available"
    except (KeyError, TypeError, ValueError):
        return "unreviewed"


def _number_status(value):
    if value is None:
        return "missing"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "incomparable"
    try:
        if not isfinite(value):
            return "incomparable"
    except OverflowError:
        return "incomparable"
    return "available"


def _quarter_status(pair, cutoff):
    if pair.get("comparability_reviewed") is not True:
        return "unreviewed"
    try:
        current, prior = pair["current"], pair["prior_year"]
        dates = [(date.fromisoformat(record["period_start"]), date.fromisoformat(record["period_end"])) for record in (current, prior)]
        if any(end > cutoff.date() for _, end in dates):
            return "future"
        lengths = [(end - start).days + 1 for start, end in dates]
        if any(record.get("period_type") != "quarter" for record in (current, prior)) or any(not 60 <= length <= 110 for length in lengths):
            return "incomparable"
        if current.get("scope") != "consolidated" or prior.get("scope") != "consolidated" or not current.get("currency") or current.get("currency") != prior.get("currency"):
            return "incomparable"
        if prior["value"] <= 0 or abs(lengths[0] - lengths[1]) > 3:
            return "incomparable"
        if not 350 <= (dates[0][1] - dates[1][1]).days <= 380:
            return "incomparable"
        if any(dates[0][i].month != dates[1][i].month for i in (0, 1)):
            return "incomparable"
        return "available"
    except (KeyError, TypeError, ValueError):
        return "incomparable"


def _latest_status(record, cutoff):
    try:
        start = date.fromisoformat(record["period_start"])
        end = date.fromisoformat(record["period_end"])
        if end > cutoff.date():
            return "future"
        if start > end:
            return "incomparable"
        if date.fromisoformat(record["verified_as_of"]) < cutoff.date():
            return "stale"
        return "available"
    except (KeyError, TypeError, ValueError):
        return "unreviewed"


def _quote_status(record, cutoff):
    try:
        return "stale" if date.fromisoformat(record["valid_through"]) < cutoff.date() else "available"
    except (KeyError, TypeError, ValueError):
        return "unreviewed"


def _headquarters_status(record, cutoff):
    if record.get("state") == "confirmed_investment":
        return "available"
    if record.get("state") != "reviewed_no_disqualifying_evidence" or not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        return "unreviewed"
    try:
        start, end = date.fromisoformat(record["lookback_start"]), date.fromisoformat(record["lookback_end"])
        return "available" if start <= cutoff.date() <= end else "unreviewed"
    except (KeyError, TypeError, ValueError):
        return "unreviewed"


def coverage_report(snapshot: dict, as_of: str) -> dict:
    """Evaluate the documented coverage snapshot at a completed-session cutoff."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("symbol"), str) or not snapshot["symbol"].strip():
        raise ValueError("snapshot requires a nonempty symbol")
    cutoff = _cutoff(as_of)
    fundamentals = snapshot.get("fundamentals", {})
    if not isinstance(fundamentals, dict):
        fundamentals = {}
    evidence = {key: fundamentals.get(key) for key in ("trailing_pe", "dividend_yield", "revenue", "sga")}
    evidence.update({key: snapshot.get(key) for key in ("classification", "headquarters", "latest_reported_period")})
    fields = {
        key: {"status": _availability(value, cutoff), "evidence": deepcopy(value)}
        for key, value in evidence.items()
    }
    classification = snapshot.get("classification") or {}
    if fields["classification"]["status"] == "available" and any(not isinstance(classification.get(key), str) for key in ("security_type", "exchange")):
        fields["classification"]["status"] = "unreviewed"
    for key in ("trailing_pe", "dividend_yield", "revenue", "sga"):
        if fields[key]["status"] == "available":
            record = fundamentals[key]
            records = [record.get(side, {}) for side in ("current", "prior_year")] if key in ("revenue", "sga") else [record]
            statuses = [_number_status(observation.get("value")) for observation in records]
            fields[key]["status"] = next((status for status in statuses if status != "available"), "available")
        if key in ("trailing_pe", "dividend_yield") and fields[key]["status"] == "available":
            fields[key]["status"] = _quote_status(fundamentals[key], cutoff)
        if key in ("revenue", "sga") and fields[key]["status"] == "available":
            fields[key]["status"] = _quarter_status(fundamentals[key], cutoff)
    if fields["dividend_yield"]["status"] == "available":
        dividend = fundamentals["dividend_yield"]
        if dividend.get("unit") not in ("percent", "fraction"):
            fields["dividend_yield"]["status"] = "incomparable"
        elif dividend.get("policy_reviewed") is not True or dividend.get("convention") not in ("trailing_cash", "indicated_regular"):
            fields["dividend_yield"]["status"] = "unreviewed"
    if fields["latest_reported_period"]["status"] == "available":
        fields["latest_reported_period"]["status"] = _latest_status(snapshot["latest_reported_period"], cutoff)
    for key in ("revenue", "sga"):
        if fields[key]["status"] == "available":
            if fields["latest_reported_period"]["status"] != "available":
                fields[key]["status"] = "unreviewed"
            else:
                latest = snapshot["latest_reported_period"]
                current = fundamentals[key]["current"]
                if any(current[period] != latest[period] for period in ("period_start", "period_end")):
                    fields[key]["status"] = "stale"
    if fields["headquarters"]["status"] == "available":
        fields["headquarters"]["status"] = _headquarters_status(snapshot["headquarters"], cutoff)
    blockers = [f"{key}:{field['status']}" for key, field in fields.items() if field["status"] != "available"]
    classification = snapshot.get("classification") or {}
    eligibility = "unknown"
    if fields["classification"]["status"] == "available" and classification.get("security_type") in EXCLUDED_TYPES:
        eligibility = "excluded"
    elif fields["classification"]["status"] == "available" and classification.get("security_type") == "operating_common" and classification.get("reviewed") is True and classification.get("exchange") in US_EXCHANGES:
        eligibility = "eligible"
    if eligibility != "eligible":
        blockers.append(f"classification:{eligibility}")
    if fields["headquarters"]["status"] == "available" and snapshot["headquarters"].get("state") == "confirmed_investment":
        eligibility = "excluded"
        blockers.append("headquarters:confirmed_investment")
    normalized = {key: None for key in ("trailing_pe", "dividend_yield", "revenue_growth", "sga_growth")}
    if fields["trailing_pe"]["status"] == "available":
        normalized["trailing_pe"] = fundamentals["trailing_pe"]["value"]
    if fields["dividend_yield"]["status"] == "available":
        dividend = fundamentals["dividend_yield"]
        normalized["dividend_yield"] = dividend["value"] / 100 if dividend["unit"] == "percent" else dividend["value"]
    for key in ("revenue", "sga"):
        if fields[key]["status"] == "available":
            pair = fundamentals[key]
            growth = pair["current"]["value"] / pair["prior_year"]["value"] - 1
            if isfinite(growth):
                normalized[f"{key}_growth"] = growth
            else:
                fields[key]["status"] = "incomparable"
                blockers.append(f"{key}:incomparable")
    if normalized["trailing_pe"] is not None and not 0 < normalized["trailing_pe"] < 30:
        blockers.append("gate:trailing_pe")
    if normalized["dividend_yield"] is not None and normalized["dividend_yield"] <= 0.02:
        blockers.append("gate:dividend_yield")
    if normalized["revenue_growth"] is not None:
        pair = fundamentals["revenue"]
        growth = Decimal(str(pair["current"]["value"])) / Decimal(str(pair["prior_year"]["value"])) - 1
        if growth <= Decimal("0.15"):
            blockers.append("gate:revenue_growth")
    flags = []
    if normalized["sga_growth"] is not None:
        pair = fundamentals["sga"]
        growth = Decimal(str(pair["current"]["value"])) / Decimal(str(pair["prior_year"]["value"])) - 1
        if growth >= Decimal("0.25"):
            flags.append("sga_investigation")
    return {
        "symbol": snapshot["symbol"],
        "as_of": cutoff.date().isoformat(),
        "decision_cutoff": cutoff.isoformat(),
        "eligibility": eligibility,
        "buy_allowed": not blockers,
        "blockers": blockers,
        "flags": flags,
        "normalized": normalized,
        "fields": fields,
    }
