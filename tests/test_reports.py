from engine15 import reports


def test_weekly_question_prefers_a_wrong_call():
    rep = {"recent_surprises": [
        {"asset": "ETHUSDT", "move_atr": -15.0, "move_pct": -4.9, "direction": "DOWN", "horizon_bars": 16,
         "start_utc": "2026-11-08 18:45 UTC", "engine_side": "SHORT", "engine_verdict": "right side"},
        {"asset": "BTCUSDT", "move_atr": 7.0, "move_pct": 3.1, "direction": "UP", "horizon_bars": 4,
         "start_utc": "2026-11-09 14:30 UTC", "engine_side": "SHORT", "engine_verdict": "WRONG side"}]}
    q = reports.weekly_question(rep)
    assert q["asset"] == "BTCUSDT" and "BTC rising +3.10% in 1 hour" in q["text"] and "short" in q["text"]
    assert reports.weekly_question({"recent_surprises": []}) is None


def test_daily_runs_once_a_day(monkeypatch):
    calls = []
    monkeypatch.setattr(reports, "_spawn", lambda days, log: calls.append(days) or True)
    monkeypatch.setattr(reports, "_read", lambda stem: None)
    st = {}
    reports.daily(st, log=lambda *_: None)
    reports.daily(st, log=lambda *_: None)
    assert calls.count(1) == 1 and "report_day" in st


def test_stats_verdicts():
    s = reports._stats([])
    assert s["trades"] == 0
    s = reports._stats([10.0] * 5)
    assert s["verdict"].startswith("too few")
    s = reports._stats([10.0 + (i % 3) for i in range(40)])
    assert s["verdict"].startswith("ahead") and s["range90_usd"][0] > 0
    s = reports._stats([-10.0 - (i % 3) for i in range(40)])
    assert s["verdict"].startswith("behind")


def test_portfolio_readout():
    from engine15 import export
    p = export.portfolio({"A": {"trade": {"status": "LONG", "notional_usd": 60000, "equity_marked": 10000, "risk_to_stop_usd": 200}},
                          "B": {"trade": {"status": "SHORT", "notional_usd": 10000, "equity_marked": 10000, "risk_to_stop_usd": 250}}})
    assert p["net_usd"] == 50000 and p["gross_x_equity"] == 3.5 and p["risk_to_all_stops_pct"] == 2.25
