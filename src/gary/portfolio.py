"""Pure paper execution at the approved daily-step seam."""

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from math import isfinite
from zoneinfo import ZoneInfo


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0


def _technical_exit(signal, signal_date):
    try:
        return (signal.get("kind") in {"head_shoulders_top", "rolling_over"} and signal.get("status") == "completed"
                and signal.get("direction") == "sell" and signal.get("available_at") == signal_date
                and date.fromisoformat(signal["completion_date"]) <= date.fromisoformat(signal_date))
    except (KeyError, TypeError, ValueError):
        return False


def _admissible(item, signal_date):
    coverage = item.get("coverage", {})
    signal = item.get("signal", {})
    volatility = item.get("volatility", {})
    try:
        cutoff = date.fromisoformat(signal_date)
        value = volatility["value"]
        count = volatility["return_count"]
        start = date.fromisoformat(volatility["start"])
        if not isinstance(coverage.get("decision_cutoff"), str):
            return False
        report_cutoff = datetime.fromisoformat(coverage["decision_cutoff"].replace("Z", "+00:00"))
        session_close = datetime.combine(cutoff, time(16), ZoneInfo("America/New_York"))
        weekdays = sum((start + timedelta(days=i)).weekday() < 5 for i in range((cutoff - start).days + 1))
        return (
            coverage.get("buy_allowed") is True and not coverage.get("blockers")
            and coverage.get("eligibility") == "eligible"
            and coverage.get("symbol") == item.get("symbol")
            and date.fromisoformat(coverage["as_of"]) == cutoff
            and report_cutoff.tzinfo is not None and report_cutoff <= session_close
            and signal.get("direction") == "buy" and signal.get("status") == "completed"
            and signal.get("kind") in {"inverse_head_shoulders", "cup_handle", "breaking_out"}
            and signal.get("available_at") == signal_date
            and date.fromisoformat(signal["completion_date"]) <= cutoff
            and isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0
            and isinstance(count, int) and not isinstance(count, bool) and 200 <= count < weekdays
            and date.fromisoformat(volatility["end"]) == cutoff
            and cutoff - timedelta(days=366) <= start <= cutoff - timedelta(days=330)
        )
    except (KeyError, TypeError, ValueError):
        return False


def step_portfolio(state, market, as_of):
    try:
        execution = date.fromisoformat(as_of)
        if (market["execution_date"] != as_of or date.fromisoformat(market["signal_date"]) >= execution
                or market.get("execution_price_basis") != "unadjusted"):
            raise ValueError("invalid execution date or price basis")
        if (not isinstance(state["cash"], (int, float)) or not isfinite(state["cash"]) or state["cash"] < 0
                or not _positive(state["initial_capital"]) or not _positive(state["next_loss_threshold"])):
            raise ValueError("invalid portfolio cash or capital")
        if any(date.fromisoformat(day) > execution for day in state["processed_dates"]):
            raise ValueError("cannot execute before a processed date")
        if len(state["positions"]) > 25:
            raise ValueError("portfolio exceeds 25 positions")
        for position in state["positions"].values():
            shares = position["shares"]
            if (not isinstance(shares, int) or isinstance(shares, bool) or shares <= 0
                    or shares % 100 or not _positive(position["wapp"])):
                raise ValueError("invalid share block or WAPP")
    except (KeyError, TypeError) as exc:
        raise ValueError("incomplete execution context") from exc
    result = deepcopy(state)
    if as_of in result["processed_dates"]:
        return {"status": "already_processed", "state": result, "orders": [], "events": []}
    orders = []
    events = []
    sold = set()
    if any(not _positive(market["closes"].get(symbol)) for symbol in result["positions"]):
        return {"status": "deferred", "state": deepcopy(state), "orders": [], "events": [{"kind": "missing_mark"}]}
    if any(not _positive(market["opens"].get(symbol)) for symbol in result["positions"]):
        return {"status": "deferred", "state": deepcopy(state), "orders": [], "events": [{"kind": "missing_held_open"}]}
    losses = {symbol: position["shares"] * (market["closes"][symbol] - position["wapp"])
              for symbol, position in result["positions"].items()}
    equity = result["cash"] + sum(position["shares"] * market["closes"][symbol]
                                 for symbol, position in result["positions"].items())
    if not isfinite(equity) or any(not isfinite(value) for value in losses.values()):
        raise ValueError("nonfinite portfolio valuation")
    threshold_exits = set()
    if equity <= result["next_loss_threshold"]:
        threshold_exits = set(sorted((s for s in losses if losses[s] < 0), key=lambda s: (losses[s], s))[:4])
        events.append({"kind": "portfolio_loss", "equity": equity, "threshold": result["next_loss_threshold"]})
        result["next_loss_threshold"] *= 0.9
    technical_exits = {signal.get("symbol") for signal in market.get("sell_signals", [])
                       if _technical_exit(signal, market["signal_date"])}
    exits = {}
    for symbol in sorted(result["positions"], key=lambda s: (losses[s], s)):
        position = result["positions"][symbol]
        reasons = []
        if (market["closes"][symbol] <= position["wapp"] * 0.75
                or market["opens"].get(symbol, float("inf")) <= position["wapp"] * 0.75):
            reasons.append("purchase_stop")
        if symbol in technical_exits:
            reasons.append("technical_exit")
        if symbol in threshold_exits:
            reasons.append("portfolio_loss")
        if reasons:
            if not _positive(market["opens"].get(symbol)):
                return {"status": "deferred", "state": deepcopy(state), "orders": [],
                        "events": [{"kind": "missing_exit_price", "symbol": symbol}]}
            exits[symbol] = reasons
    for symbol, reasons in exits.items():
        position = result["positions"].pop(symbol)
        price = float(market["opens"][symbol])
        if not isfinite(result["cash"] + position["shares"] * price):
            raise ValueError("nonfinite sale proceeds")
        result["cash"] += position["shares"] * price
        orders.append({"symbol": symbol, "side": "sell", "shares": position["shares"],
                       "price": price, "reasons": reasons})
        sold.add(symbol)
    candidates = sorted((item for item in market["candidates"] if _admissible(item, market["signal_date"])),
                        key=lambda item: (item["volatility"]["value"], item["symbol"]))
    for item in candidates:
        symbol = item["symbol"]
        if symbol in sold or symbol in result["positions"] or len(result["positions"]) >= 25:
            continue
        price = market["opens"].get(symbol)
        if not _positive(price):
            events.append({"kind": "missing_buy_price", "symbol": symbol})
            continue
        shares = int(min(8000, result["cash"]) // (100 * price)) * 100
        if shares:
            result["positions"][symbol] = {"shares": shares, "wapp": float(price)}
            result["cash"] -= shares * price
            orders.append({"symbol": symbol, "side": "buy", "shares": shares, "price": price})
    result["processed_dates"].append(as_of)
    return {"status": "committed", "state": result, "orders": orders, "events": events}
