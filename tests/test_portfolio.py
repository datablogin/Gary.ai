from gary.portfolio import step_portfolio
import pytest


def state():
    return {"cash": 200000.0, "positions": {}, "initial_capital": 200000.0,
            "next_loss_threshold": 180000.0, "processed_dates": []}


def candidate(symbol="SYNTH", volatility=0.2):
    return {"symbol": symbol,
            "coverage": {"symbol": symbol, "as_of": "2026-10-09", "eligibility": "eligible",
                         "decision_cutoff": "2026-10-09T20:00:00Z", "buy_allowed": True, "blockers": []},
            "signal": {"kind": "inverse_head_shoulders", "direction": "buy", "status": "completed",
                       "available_at": "2026-10-09", "completion_date": "2026-10-09"},
            "volatility": {"value": volatility, "start": "2025-10-09", "end": "2026-10-09",
                           "return_count": 250}}


def market(candidates=None, opens=None, closes=None):
    from copy import deepcopy
    return {"signal_date": "2026-10-09", "execution_date": "2026-10-12",
            "execution_price_basis": "unadjusted", "closes": deepcopy(closes or {}), "opens": deepcopy(opens or {}),
            "candidates": candidates or [], "sell_signals": []}


def test_buys_whole_blocks_within_eight_thousand_dollars():
    result = step_portfolio(state(), market([candidate()], {"SYNTH": 26}), "2026-10-12")
    assert result["state"]["positions"]["SYNTH"] == {"shares": 300, "wapp": 26.0}
    assert result["state"]["cash"] == 192200.0


def test_confirmed_breakout_buys_whole_blocks_at_the_next_session_open():
    item = candidate()
    item["signal"]["kind"] = "breaking_out"
    result = step_portfolio(state(), market([item], {"SYNTH": 26}), "2026-10-12")
    assert result["orders"] == [{"symbol": "SYNTH", "side": "buy", "shares": 300, "price": 26.0}]
    assert result["state"]["positions"] == {"SYNTH": {"shares": 300, "wapp": 26.0}}
    assert result["state"]["cash"] == 192200.0


def test_blocked_evidence_cannot_create_a_buy():
    item = candidate()
    item["coverage"]["buy_allowed"] = False
    item["coverage"]["blockers"] = ["headquarters_unreviewed"]
    result = step_portfolio(state(), market([item], {"SYNTH": 26}), "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["cash"] == 200000.0


@pytest.mark.parametrize("change", ["unknown", "future_coverage", "wrong_symbol", "future_signal", "old_signal", "short_volatility", "future_volatility", "absent_signal"])
def test_incomplete_or_unavailable_candidates_cannot_create_a_buy(change):
    item = candidate()
    if change == "unknown": item["coverage"]["eligibility"] = "unknown"
    if change == "future_coverage": item["coverage"]["as_of"] = "2026-10-12"
    if change == "wrong_symbol": item["coverage"]["symbol"] = "OTHER"
    if change == "future_signal": item["signal"]["available_at"] = "2026-10-12"
    if change == "old_signal": item["signal"]["available_at"] = "2026-09-01"
    if change == "short_volatility": item["volatility"]["return_count"] = 100
    if change == "future_volatility": item["volatility"]["end"] = "2026-10-12"
    if change == "absent_signal": item.pop("signal")
    assert step_portfolio(state(), market([item], {"SYNTH": 26}), "2026-10-12")["orders"] == []


def test_lowest_volatility_gets_the_last_available_slot():
    portfolio = state()
    portfolio["positions"] = {f"HELD{i}": {"shares": 100, "wapp": 10} for i in range(24)}
    prices = {symbol: 10 for symbol in portfolio["positions"]}
    result = step_portfolio(portfolio,
                            market([candidate("HIGH", 0.5), candidate("LOW", 0.1)],
                                   {**prices, "HIGH": 20, "LOW": 20}, prices), "2026-10-12")
    assert [order["symbol"] for order in result["orders"]] == ["LOW"]


def test_purchase_stop_fills_entire_position_at_next_open_without_rebuy():
    portfolio = state()
    portfolio["cash"] = 196000
    portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 40}}
    result = step_portfolio(portfolio, market([candidate()], {"SYNTH": 28}, {"SYNTH": 30}), "2026-10-12")
    assert result["orders"] == [{"symbol": "SYNTH", "side": "sell", "shares": 100,
                                "price": 28.0, "reasons": ["purchase_stop"]}]
    assert result["state"]["cash"] == 198800
    assert result["state"]["positions"] == {}


@pytest.mark.parametrize("reason", ["open_gap", "technical_exit"])
def test_other_mandatory_exits_sell_the_whole_position(reason):
    portfolio = state()
    portfolio["cash"] = 196000
    portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 40}}
    prices = market(opens={"SYNTH": 28 if reason == "open_gap" else 42}, closes={"SYNTH": 40})
    if reason == "technical_exit":
        prices["sell_signals"] = [{"symbol": "SYNTH", "kind": "head_shoulders_top",
                                   "direction": "sell", "status": "completed", "available_at": "2026-10-09",
                                   "completion_date": "2026-10-09"}]
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["state"]["positions"] == {}
    assert result["orders"][0]["side"] == "sell"


def test_completed_rollover_sells_all_blocks_at_the_next_open_without_rebuy():
    portfolio = state()
    portfolio["cash"] = 188000
    portfolio["positions"] = {"SYNTH": {"shares": 300, "wapp": 40}}
    item = candidate()
    item["signal"]["kind"] = "breaking_out"
    prices = market([item], opens={"SYNTH": 41}, closes={"SYNTH": 40})
    prices["sell_signals"] = [{"symbol": "SYNTH", "kind": "rolling_over", "direction": "sell",
                               "status": "completed", "available_at": "2026-10-09",
                               "completion_date": "2026-10-09"}]
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["orders"] == [{"symbol": "SYNTH", "side": "sell", "shares": 300,
                                 "price": 41.0, "reasons": ["technical_exit"]}]
    assert result["state"]["positions"] == {}
    assert result["state"]["cash"] == 200300


def losing_portfolio():
    portfolio = state()
    portfolio["cash"] = 100000
    portfolio["positions"] = {f"LOSS{i}": {"shares": 100, "wapp": 100} for i in range(10)}
    prices = {f"LOSS{i}": 75.1 + i / 10 for i in range(10)}
    return portfolio, market(opens=prices, closes=prices)


def test_portfolio_threshold_sells_four_largest_dollar_losers():
    portfolio, prices = losing_portfolio()
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert [order["symbol"] for order in result["orders"]] == ["LOSS0", "LOSS1", "LOSS2", "LOSS3"]
    assert result["state"]["cash"] == pytest.approx(130100)
    assert result["state"]["next_loss_threshold"] == 162000


@pytest.mark.parametrize("case", ["threshold", "stop", "missing_mark"])
def test_missing_required_price_defers_atomically_and_can_retry(case):
    from copy import deepcopy
    if case == "threshold":
        portfolio, complete = losing_portfolio()
        symbol = "LOSS3"
    else:
        portfolio = state()
        portfolio["cash"] = 196000
        portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 40}}
        complete = market(opens={"SYNTH": 28}, closes={"SYNTH": 30})
        symbol = "SYNTH"
    incomplete = deepcopy(complete)
    incomplete["closes" if case == "missing_mark" else "opens"].pop(symbol)
    saved = deepcopy(portfolio)
    result = step_portfolio(portfolio, incomplete, "2026-10-12")
    assert result["status"] == "deferred"
    assert result["state"] == saved and portfolio == saved
    assert result["orders"] == []
    assert step_portfolio(result["state"], complete, "2026-10-12")["orders"]


def test_same_day_retry_cannot_repeat_orders_or_consume_another_threshold():
    portfolio, prices = losing_portfolio()
    first = step_portfolio(portfolio, prices, "2026-10-12")
    second = step_portfolio(first["state"], prices, "2026-10-12")
    assert second["state"] == first["state"]
    assert second["orders"] == []


@pytest.mark.parametrize("bad_price", [None, -1, 0, float("nan"), float("inf")])
def test_unfillable_candidate_is_skipped_without_spending_cash(bad_price):
    result = step_portfolio(state(), market([candidate()], {"SYNTH": bad_price}), "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["cash"] == 200000


@pytest.mark.parametrize("bad", ["future_signal_date", "wrong_execution_date", "adjusted_fills", "negative_cash", "fractional_shares", "old_execution"])
def test_invalid_execution_context_raises_without_mutating_state(bad):
    from copy import deepcopy
    portfolio, prices = losing_portfolio()
    if bad == "future_signal_date": prices["signal_date"] = "2026-10-13"
    if bad == "wrong_execution_date": prices["execution_date"] = "2026-10-14"
    if bad == "adjusted_fills": prices["execution_price_basis"] = "adjusted"
    if bad == "negative_cash": portfolio["cash"] = -1
    if bad == "fractional_shares": portfolio["positions"]["LOSS0"]["shares"] = 100.5
    if bad == "old_execution": portfolio["processed_dates"] = ["2026-10-13"]
    saved = deepcopy(portfolio)
    with pytest.raises(ValueError):
        step_portfolio(portfolio, prices, "2026-10-12")
    assert portfolio == saved


def test_later_loss_event_uses_next_threshold_once_with_fewer_than_four_losers():
    portfolio = state()
    portfolio["cash"] = 155000
    portfolio["next_loss_threshold"] = 162000
    portfolio["positions"] = {"LOSER": {"shares": 100, "wapp": 100}}
    prices = market(opens={"LOSER": 50}, closes={"LOSER": 50})
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["state"]["next_loss_threshold"] == 145800
    assert len(result["orders"]) == 1
    assert result["orders"][0]["reasons"] == ["purchase_stop", "portfolio_loss"]


def test_minimum_block_exceeding_budget_leaves_cash():
    result = step_portfolio(state(), market([candidate()], {"SYNTH": 81}), "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["cash"] == 200000


@pytest.mark.parametrize("case", ["expired_coverage", "future_completion", "missing_completion"])
def test_qa_causal_gate_evidence_cannot_create_orders(case):
    item = candidate()
    if case == "expired_coverage": item["coverage"]["as_of"] = "2025-10-09"
    if case == "future_completion": item["signal"]["completion_date"] = "2026-10-12"
    if case == "missing_completion": item["signal"].pop("completion_date")
    assert step_portfolio(state(), market([item], {"SYNTH": 20}), "2026-10-12")["orders"] == []


@pytest.mark.parametrize("bad_open", [None, "bad", float("nan"), float("inf")])
def test_qa_unknown_open_cannot_consume_day_before_gap_stop(bad_open):
    portfolio = state()
    portfolio["cash"] = 190000
    portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 100}}
    result = step_portfolio(portfolio, market(opens={"SYNTH": bad_open}, closes={"SYNTH": 100}), "2026-10-12")
    assert result["status"] == "deferred"
    assert result["state"] == portfolio
    retry = step_portfolio(result["state"], market(opens={"SYNTH": 70}, closes={"SYNTH": 100}), "2026-10-12")
    assert retry["orders"][0]["reasons"] == ["purchase_stop"]


@pytest.mark.parametrize("bad", ["short_window", "infinite_count", "boolean_volatility", "impossible_daily_count"])
def test_qa_invalid_volatility_history_cannot_create_order(bad):
    item = candidate()
    if bad == "short_window": item["volatility"]["start"] = "2026-10-08"
    if bad == "infinite_count": item["volatility"]["return_count"] = float("inf")
    if bad == "boolean_volatility": item["volatility"]["value"] = False
    if bad == "impossible_daily_count": item["volatility"]["return_count"] = 1000
    assert step_portfolio(state(), market([item], {"SYNTH": 20}), "2026-10-12")["orders"] == []


@pytest.mark.parametrize("case", ["too_many_positions", "overflow_fill"])
def test_qa_invalid_financial_state_is_not_committed(case):
    portfolio = state()
    if case == "too_many_positions":
        portfolio["positions"] = {f"HELD{i}": {"shares": 100, "wapp": 10} for i in range(26)}
        marks = {symbol: 10 for symbol in portfolio["positions"]}
        prices = market(opens=marks, closes=marks)
    else:
        portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 100}}
        prices = market(opens={"SYNTH": 1e308}, closes={"SYNTH": 100})
        prices["sell_signals"] = [{"symbol": "SYNTH", "kind": "head_shoulders_top", "direction": "sell",
                                   "status": "completed", "available_at": "2026-10-09", "completion_date": "2026-10-09"}]
    with pytest.raises(ValueError):
        step_portfolio(portfolio, prices, "2026-10-12")


@pytest.mark.parametrize("completion", [None, "2026-10-12"])
def test_qa_missing_or_future_sell_completion_does_not_exit(completion):
    portfolio = state()
    portfolio["positions"] = {"SYNTH": {"shares": 100, "wapp": 100}}
    prices = market(opens={"SYNTH": 100}, closes={"SYNTH": 100})
    prices["sell_signals"] = [{"symbol": "SYNTH", "kind": "head_shoulders_top", "direction": "sell",
                               "status": "completed", "available_at": "2026-10-09", "completion_date": completion}]
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["positions"] == portfolio["positions"]


@pytest.mark.parametrize("cutoff", [None, "2026-10-09T22:00:00Z", "2026-10-09T16:00:00"])
def test_qa_report_cutoff_must_not_include_after_close_evidence(cutoff):
    item = candidate()
    item["coverage"]["decision_cutoff"] = cutoff
    assert step_portfolio(state(), market([item], {"SYNTH": 20}), "2026-10-12")["orders"] == []


def expanded_synthetic_bars(count, current_prices):
    """Explicit synthetic chart ending at the existing market's signal date."""
    from datetime import date, timedelta
    dates = []
    day = date(2026, 10, 9)
    while len(dates) < count:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day -= timedelta(days=1)
    bars = [{"date": day, "open": 40, "high": 40, "low": 39, "close": 40, "volume": 1000}
            for day in reversed(dates)]
    bars[-1].update(current_prices)
    return bars


def test_detector_breakout_with_passing_fundamentals_can_enter_the_paper_seam():
    from gary.patterns_v2 import detect_patterns
    bars = expanded_synthetic_bars(22, {"high": 41, "close": 40.21})
    item = candidate()
    item["signal"] = detect_patterns(bars, "2026-10-09")[0]
    result = step_portfolio(state(), market([item], {"SYNTH": 41}), "2026-10-12")
    assert result["orders"] == [{"symbol": "SYNTH", "side": "buy", "shares": 100, "price": 41}]
    assert result["state"]["cash"] == 195900


def test_detector_gap_with_passing_fundamentals_never_buys_or_exits_a_holding():
    from gary.patterns_v2 import detect_patterns
    bars = expanded_synthetic_bars(2, {"open": 40.8, "high": 41, "low": 40, "close": 40.3})
    gap = detect_patterns(bars, "2026-10-09")[0]
    assert (gap["kind"], gap["direction"]) == ("gapping_up", "observation")
    item = candidate()
    item["signal"] = gap
    prices = market([item], {"SYNTH": 41}, {"SYNTH": 40.3})
    prices["sell_signals"] = [{**gap, "symbol": "SYNTH"}]
    result = step_portfolio(state(), prices, "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["cash"] == 200000

    held = state()
    held["cash"] = 188000
    held["positions"] = {"SYNTH": {"shares": 300, "wapp": 40}}
    result = step_portfolio(held, prices, "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["positions"] == {"SYNTH": {"shares": 300, "wapp": 40}}
    assert result["state"]["cash"] == 188000


def test_detector_rollover_exits_the_whole_position_through_the_paper_seam():
    from gary.patterns_v2 import detect_patterns
    bars = expanded_synthetic_bars(52, {"low": 38, "close": 38.8})
    signal = detect_patterns(bars, "2026-10-09")[0]
    portfolio = state()
    portfolio["cash"] = 188000
    portfolio["positions"] = {"SYNTH": {"shares": 300, "wapp": 40}}
    prices = market(opens={"SYNTH": 38.5}, closes={"SYNTH": 38.8})
    prices["sell_signals"] = [{**signal, "symbol": "SYNTH"}]
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["orders"] == [{"symbol": "SYNTH", "side": "sell", "shares": 300,
                                 "price": 38.5, "reasons": ["technical_exit"]}]
    assert result["state"]["cash"] == 199550


@pytest.mark.parametrize("failure", ["blocked", "unknown", "future_coverage", "future_signal",
                                      "incomplete", "wrong_direction", "short_history", "too_expensive"])
def test_breakout_does_not_bypass_existing_buy_gates(failure):
    item = candidate()
    item["signal"]["kind"] = "breaking_out"
    if failure == "blocked":
        item["coverage"].update(buy_allowed=False, blockers=["headquarters_unreviewed"])
    if failure == "unknown": item["coverage"]["eligibility"] = "unknown"
    if failure == "future_coverage": item["coverage"]["as_of"] = "2026-10-12"
    if failure == "future_signal": item["signal"]["available_at"] = "2026-10-12"
    if failure == "incomplete": item["signal"]["status"] = "forming"
    if failure == "wrong_direction": item["signal"]["direction"] = "observation"
    if failure == "short_history": item["volatility"]["return_count"] = 100
    price = 81 if failure == "too_expensive" else 26
    result = step_portfolio(state(), market([item], {"SYNTH": price}), "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["cash"] == 200000


@pytest.mark.parametrize("failure", ["future_availability", "old_availability", "future_completion",
                                      "missing_completion", "incomplete", "wrong_direction"])
def test_unavailable_or_incomplete_rollover_does_not_exit(failure):
    portfolio = state()
    portfolio["cash"] = 188000
    portfolio["positions"] = {"SYNTH": {"shares": 300, "wapp": 40}}
    signal = {"symbol": "SYNTH", "kind": "rolling_over", "direction": "sell", "status": "completed",
              "available_at": "2026-10-09", "completion_date": "2026-10-09"}
    if failure == "future_availability": signal["available_at"] = "2026-10-12"
    if failure == "old_availability": signal["available_at"] = "2026-10-08"
    if failure == "future_completion": signal["completion_date"] = "2026-10-12"
    if failure == "missing_completion": signal.pop("completion_date")
    if failure == "incomplete": signal["status"] = "forming"
    if failure == "wrong_direction": signal["direction"] = "observation"
    prices = market(opens={"SYNTH": 41}, closes={"SYNTH": 40})
    prices["sell_signals"] = [signal]
    result = step_portfolio(portfolio, prices, "2026-10-12")
    assert result["orders"] == []
    assert result["state"]["positions"] == portfolio["positions"]
