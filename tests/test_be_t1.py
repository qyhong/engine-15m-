# -*- coding: utf-8 -*-
"""Break-even after Target 1 on the main book (think15-v5.2.5, CFG["be_t1"]): planted bars, no network.

The rule (backtest.run_book, exits.be_stop): once a bar trades through the trade's Target 1 the stop moves to the
entry price, live from the NEXT bar, never looser; a stop-out there is "STOP_BE". Off unless cfg["be_t1"] is true
and a Target 1 planner is passed, so every other market's book is exactly what it was.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, labels, live  # noqa: E402
from engine15.config import CFG  # noqa: E402

BE = dict(CFG, step_aside=False, be_t1=True)
OFF = dict(CFG, step_aside=False)


def _odds(n, side):
    o = np.full((n, 3), 0.2)
    o[:, labels.UP if side == 1 else labels.DOWN] = 0.6           # an edge for `side` on every bar
    return o


def _px(rows):
    a = np.array(rows, dtype=float)
    return {"open": a[:, 0].copy(), "high": a[:, 1].copy(), "low": a[:, 2].copy(), "close": a[:, 3].copy()}


def _run(px, side, cfg, t1_of="plan", lo=1, hi=None, state=None):
    n = len(px["close"])
    z = np.zeros(n)
    if t1_of == "plan":
        t1_of = lambda i, s, entry, stop: entry + s * 1.0         # Target 1 = one stop distance away (unit 0.5 x 2)
    return backtest.run_book(px, _odds(n, side), z.astype(bool), z, np.full(n, 0.5), cfg, lo, hi or n, state=state,
                             t1_of=t1_of)


# long: decided at bar 1's close, filled at bar 2's open (100.0), stop 99.0, Target 1 101.0
LONG = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
        (100, 101.5, 99.5, 101.2),          # bar 3: Target 1 trades; the low is under the entry but the stop is still 99
        (101.2, 101.3, 100.5, 100.6),       # bar 4: above the entry
        (100.6, 100.7, 99.8, 100.2),        # bar 5: back through the entry -> out at 100.0
        (100.2, 100.3, 100.1, 100.2), (100.2, 100.3, 100.1, 100.2)]
SHORT = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
         (100, 100.5, 98.5, 98.8), (98.8, 99.5, 98.7, 99.4), (99.4, 100.2, 99.3, 99.8),
         (99.8, 99.9, 99.7, 99.8), (99.8, 99.9, 99.7, 99.8)]


def _closed(b):
    t = b["trades"]
    return t[t.why_out != "OPEN"]


def test_long_stop_moves_to_entry_after_target_1_from_the_next_bar():
    px = _px(LONG)
    b, ref = _run(px, 1, BE), _run(px, 1, OFF)
    assert b["held"][2] == 1 and b["stop"][2] == 99.0             # the entry stop
    assert b["stop"][3] == 100.0 and b["held"][4] == 1            # moved at bar 3's close; bar 3's own low (99.5) did not stop it
    c = _closed(b)
    assert len(c) == 1 and c.why_out.iloc[0] == "STOP_BE" and c.i_out.iloc[0] == 5 and c.p_out.iloc[0] == 100.0
    assert abs(c.pnl_usd.iloc[0] + c.fees_usd.iloc[0]) < 1e-9     # out at the entry: the trade costs its fees, nothing else
    assert len(_closed(ref)) == 0 and ref["stop"][5] == 99.0 and ref["held"][7] == 1    # the old rule is still holding


def test_short_is_the_mirror():
    b = _run(_px(SHORT), -1, BE)
    c = _closed(b)
    assert b["stop"][2] == 101.0 and b["stop"][3] == 100.0
    assert len(c) == 1 and c.why_out.iloc[0] == "STOP_BE" and c.i_out.iloc[0] == 5 and c.p_out.iloc[0] == 100.0


def test_a_gap_through_the_entry_fills_at_the_open():
    rows = list(LONG)
    rows[5] = (99.6, 99.9, 99.5, 99.7)                            # opens under the entry
    c = _closed(_run(_px(rows), 1, BE))
    assert c.why_out.iloc[0] == "STOP_BE" and c.p_out.iloc[0] == 99.6


def test_plain_stop_before_target_1_is_unchanged():
    rows = [(100, 100.1, 99.9, 100)] * 3 + [(100, 100.2, 98.9, 99.2)] + [(99.2, 99.3, 99.1, 99.2)] * 3
    c = _closed(_run(_px(rows), 1, BE))
    assert c.why_out.iloc[0] == "STOP" and c.p_out.iloc[0] == 99.0


def test_off_unless_both_the_switch_and_a_planner_are_given():
    px = _px(LONG)
    ref = _run(px, 1, OFF, t1_of=None)
    for cfg, t1_of in ((BE, None), (OFF, "plan")):
        b = _run(px, 1, cfg, t1_of=t1_of)
        assert np.array_equal(b["held"], ref["held"]) and np.allclose(b["equity"], ref["equity"], equal_nan=True)
        assert np.allclose(b["stop"], ref["stop"], equal_nan=True) and b["state"] == ref["state"]
    assert "t1" not in ref["state"] and "be_t1" not in ref["state"]          # other markets' saved state is what it was


def test_a_trade_without_a_target_keeps_its_entry_stop():
    b = _run(_px(LONG), 1, BE, t1_of=lambda i, s, entry, stop: None)
    assert len(_closed(b)) == 0 and b["stop"][5] == 99.0 and b["state"]["t1"] is None


def test_the_next_trade_starts_with_its_own_entry_stop():
    b = _run(_px(LONG), 1, BE)
    st = b["state"]                                               # re-entered at bar 6's open (100.2) after the stop-out
    assert st["pos"] == 1 and st["entry"] == 100.2 and abs(st["stop"] - 99.2) < 1e-9
    assert abs(st["t1"] - 101.2) < 1e-9 and st["t1_hit"] is False and abs(st["stop0"] - 99.2) < 1e-9


def test_step_by_step_with_saved_state_equals_one_run():
    """The live engine advances one bar at a time and keeps the state as JSON."""
    for rows, side in ((LONG, 1), (SHORT, -1)):
        px = _px(rows)
        n = len(rows)
        whole = _run(px, side, BE)
        state, closed = None, []
        for i in range(1, n):
            b = _run(px, side, BE, lo=i, hi=i + 1, state=state)
            state = json.loads(json.dumps(b["state"]))
            closed.append(_closed(b))
        closed = pd.concat(closed)
        w = _closed(whole)
        assert list(closed.why_out) == list(w.why_out) and np.allclose(closed.p_out, w.p_out)
        assert np.allclose(closed.pnl_usd, w.pnl_usd)
        for k in ("pos", "qty", "entry", "stop", "eq", "t1", "t1_hit", "stop0", "fees"):
            assert state[k] == whole["state"][k] or abs(state[k] - whole["state"][k]) < 1e-9, k


def _times(n):
    return pd.date_range("2026-11-10", periods=n, freq="15min", tz="UTC")


def test_a_running_trade_is_adopted_and_its_stop_moves_now():
    px, times = _px(LONG), _times(len(LONG))
    old = {"pos": 1, "idle": 0, "qty": 10.0, "entry": 100.0, "stop": 99.0, "eq": 10000.0, "why_in": "FORCED",
           "pending": None, "fees": 0.0, "target_1": 101.0, "t_in_ms": int(times[2].timestamp() * 1000)}
    new = live.adopt_be_t1(old, px, times, 5)                     # bars 2 .. 4 are in the journal; bar 3 traded Target 1
    assert new is not old and old["stop"] == 99.0                 # the caller's state is not changed
    assert new["t1_hit"] is True and new["stop"] == 100.0 and new["stop0"] == 99.0 and new["t1"] == 101.0
    assert live.adopt_be_t1(new, px, times, 5) is new             # once only
    b = _run(px, 1, BE, lo=5, state=new)                          # the moved stop is live from the next bar
    c = _closed(b)
    assert c.why_out.iloc[0] == "STOP_BE" and c.p_out.iloc[0] == 100.0 and c.i_out.iloc[0] == 5


def test_a_running_trade_that_has_not_reached_target_1_keeps_its_stop():
    px, times = _px(LONG), _times(len(LONG))
    old = {"pos": 1, "qty": 10.0, "entry": 100.0, "stop": 99.0, "eq": 10000.0, "target_1": 103.0,
           "t_in_ms": int(times[2].timestamp() * 1000)}
    new = live.adopt_be_t1(old, px, times, 5)
    assert new["t1_hit"] is False and new["stop"] == 99.0 and new["t1"] == 103.0
    short = dict(old, pos=-1, stop=101.0, target_1=99.6)          # a short: bar 3's low (99.5) traded 99.6
    s = live.adopt_be_t1(short, px, times, 5)
    assert s["t1_hit"] is True and s["stop"] == 100.0
    assert live.adopt_be_t1({"pos": 0, "eq": 10000.0}, px, times, 5) == {"pos": 0, "eq": 10000.0}
    assert live.adopt_be_t1(None, px, times, 5) is None
    no_target = live.adopt_be_t1(dict(old, target_1=None), px, times, 5)
    assert no_target["t1_hit"] is False and no_target["stop"] == 99.0


def test_only_usdjpy_and_the_sp500_are_under_the_rule():
    assert CFG["be_t1"] == ("USDJPY", "SPX") and CFG["half_t1"] == ("SPX", "USDJPY")     # v5.2.7: USDJPY sells at targets
    assert live.asset_cfg("USDJPY", CFG)["be_t1"] is True and live.asset_cfg("USDJPY", CFG)["half_t1"] is True
    assert live.asset_cfg("SPX", CFG)["be_t1"] is True and live.asset_cfg("SPX", CFG)["half_t1"] is True
    for a in ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT"):
        assert live.asset_cfg(a, CFG)["be_t1"] is False and live.asset_cfg(a, CFG)["half_t1"] is False


def test_the_page_says_where_the_stop_stands():
    st = {"pos": 1, "qty": 10.0, "entry": 100.0, "stop": 100.0, "eq": 10000.0, "why_in": "FORCED", "pending": None,
          "be_t1": True, "t1_hit": True, "target_1": 101.0, "target_2": 102.0, "t_in_ms": None}
    t = live.open_trade("USDJPY", st, 100.5, pd.Timestamp("2026-11-19 21:00", tz="UTC"), live.asset_cfg("USDJPY", CFG))
    assert t["stop_price"] == 100.0 and t["risk_to_stop_usd"] == 0.0 and "entry price" in t["stop_basis"]
    assert "target_1_r" not in t and t["target_1_price"] == 101.0           # no R when the stop is the entry
    other = live.open_trade("BTCUSDT", dict(st, be_t1=False, stop=99.0), 100.5,
                            pd.Timestamp("2026-11-19 21:00", tz="UTC"), live.asset_cfg("BTCUSDT", CFG))
    assert other["stop_basis"] is None
