# -*- coding: utf-8 -*-
"""The Setups book's early entry (think15-v5.2.9, CFG["early_entry"]; owner, 22 Nov 2026: "Cut the 15-minute delay"):
a new entry from flat is booked at the close that decides it, at that close's price. No network.

    py -3 -m pytest tests/test_early_entry.py -q
"""
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import live, policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import COMPARE, random_inputs  # noqa: E402

RULE = shadows.CHALLENGERS["b_targets"]["rule"]
OLD = {"targets": True}
BAR = CFG["bar_ms"]


def run(inp, rule, cfg, lo=1, hi=None, state=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    return shadows.run(px, odds, shock, tide, unit, cfg, lo, hi or n, state=state, bias=bias, guard=guard, rule=rule,
                       aux=aux, times_ms=np.arange(n, dtype="int64") * BAR, row_of=lambda k: aux["targets"].iloc[k])


def btc():
    return shadows.asset_cfg("BTCUSDT", dict(CFG))


def test_the_switch_is_the_rule_and_the_market_together():
    assert RULE == {"targets": True, "early": True} and CFG["early_entry"] == ("BTCUSDT", "ETHUSDT")
    for a in CFG["early_entry"]:
        assert shadows.asset_cfg(a, dict(CFG))["early_fill"] is True and live.asset_cfg(a, dict(CFG))["early_fill"] is True
        assert a not in CFG["fill_delay"]
    for a in ("XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"):
        assert shadows.asset_cfg(a, dict(CFG))["early_fill"] is False and live.asset_cfg(a, dict(CFG))["early_fill"] is False
    only = [k for k, v in shadows.CHALLENGERS.items() if v["rule"].get("early")]
    # no other book of run() asks for it, except the H67 shadow b_trend30 (b_targets plus the trend filter)
    assert only == ["b_targets", "b_trend30"]


@pytest.mark.parametrize("seed", [3, 11, 17])
def test_where_the_next_open_is_the_close_the_early_book_is_the_old_book(seed):
    # random_inputs: every bar opens at the close before it, so the entry price is the same number either way
    inp = random_inputs(seed=seed)
    old, new = run(inp, OLD, btc()), run(inp, RULE, btc())
    assert len(old["trades"]) > 30 and len(old["trades"]) == len(new["trades"])
    for c in COMPARE + ["i_in", "t_in_ms", "t_out_ms", "stop0", "target_1", "target_2"]:
        a, b = old["trades"][c].values, new["trades"][c].values
        assert (a == b).all() if a.dtype.kind in "OU" else np.allclose(a.astype(float), b.astype(float), equal_nan=True), c
    assert np.allclose(old["equity"][1:], new["equity"][1:]) and (old["held"] == new["held"]).all()
    words = set(old["trades"].why_in)
    assert policy.FORCED in words and policy.ENTER in words and policy.FLIP in words


def test_the_position_is_in_the_state_at_the_close_that_decides_it():
    inp = random_inputs(seed=3)
    px = inp[0]
    n = len(px["close"])
    so = sn = None
    seen = 0
    for i in range(1, n):
        o, w = run(inp, OLD, btc(), i, i + 1, so), run(inp, RULE, btc(), i, i + 1, sn)
        so, sn = json.loads(json.dumps(o["state"])), json.loads(json.dumps(w["state"]))
        if so["pending"] and so["pos"] == 0 and so["pending"][0] in (policy.ENTER, policy.FORCED):
            seen += 1
            side = int(so["pending"][1])
            assert sn["pos"] == side and sn["pending"] is None    # the old book waits a bar; the new one holds it now
            assert sn["entry"] == px["close"][i] and sn["t_in_ms"] == i * BAR + BAR and sn["why_in"] == so["pending"][0]
            assert sn["t1"] is not None and sn["stop0"] == sn["stop"] and side * (sn["entry"] - sn["stop"]) > 0
            v = shadows.asset_view(dict(sn, mark=px["close"][i]))
            assert v["status"] == {1: "LONG", -1: "SHORT"}[side] and v["unrealized_usd"] == 0.0
        elif so["pending"]:                                       # a flip (or a step aside): the same wait in both
            assert sn["pending"] == so["pending"] and sn["pos"] == so["pos"]
        else:
            for k in ("pos", "entry", "stop", "t1", "t2", "t1_hit", "idle"):
                assert sn[k] == so[k], (i, k)
        assert abs(sn["eq"] - so["eq"]) < 1e-9
    assert seen > 20


def test_bar_by_bar_is_the_whole_run():
    inp = random_inputs(seed=11)
    n = len(inp[0]["close"])
    whole = run(inp, RULE, btc())
    st, rows = None, []
    for i in range(1, n):
        b = run(inp, RULE, btc(), i, i + 1, st)
        st = json.loads(json.dumps(b["state"]))
        rows += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
    assert len(rows) == len(whole["trades"])
    for a, b in zip(rows, whole["trades"].itertuples()):
        assert a.t_in_ms == b.t_in_ms and a.t_out_ms == b.t_out_ms and a.side == b.side and a.why_out == b.why_out
        assert abs(a.p_in - b.p_in) < 1e-12 and abs(a.pnl_usd - b.pnl_usd) < 1e-9
    assert abs(st["eq"] - whole["state"]["eq"]) < 1e-9 and st["pos"] == whole["state"]["pos"]


def test_the_entry_price_is_the_deciding_close_when_the_next_bar_opens_elsewhere():
    inp = list(random_inputs(seed=3))
    px = dict(inp[0])
    px["open"] = px["open"] * 1.0005                              # every bar now opens 0.05% above the close before it
    px["high"] = np.maximum(px["high"], px["open"])
    inp[0] = px
    new = run(tuple(inp), RULE, btc())
    old = run(tuple(inp), OLD, btc())
    first_n, first_o = new["trades"].iloc[0], old["trades"].iloc[0]
    i = int(first_n.i_in)
    assert first_n.i_in == first_o.i_in and first_n.t_in_ms == first_o.t_in_ms == i * BAR
    assert first_n.p_in == px["close"][i - 1] and first_o.p_in == px["open"][i] and first_n.p_in != first_o.p_in
    assert first_n.stop0 == first_n.p_in - first_n.side * CFG["stop_units"] * inp[2][i - 1]


def test_no_early_entry_without_the_markets_flag_or_with_a_delayed_fill():
    inp = list(random_inputs(seed=3))
    px = dict(inp[0])
    px["open"] = px["open"] * 1.0005
    px["high"] = np.maximum(px["high"], px["open"])
    inp[0] = px
    inp = tuple(inp)
    old = run(inp, OLD, btc())
    # a cfg that did not come through asset_cfg; another market's cfg; a flag that is truthy but not True; the list alone
    for cfg in (dict(CFG), shadows.asset_cfg("USDJPY", dict(CFG)), dict(CFG, early_fill=1), dict(CFG, early_entry=("BTCUSDT",))):
        got = run(inp, RULE, cfg)
        if cfg.get("leverage_cap", 1.0) == 1.0:
            assert (got["trades"].p_in.values == old["trades"].p_in.values).all()
        assert (got["trades"].p_in.values == px["open"][got["trades"].i_in.values.astype(int)]).all()   # every fill at an open
    late = run(inp, RULE, dict(btc(), fill_delay_bars=1))
    assert (late["trades"].p_in.values == px["open"][late["trades"].i_in.values.astype(int)]).all()


def test_a_decision_at_the_last_bar_opens_the_position_without_the_next_bar():
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    st = None
    for i in range(1, n):
        b = run(inp, RULE, btc(), i, i + 1, st)                    # every call ends at its own last bar
        st = json.loads(json.dumps(b["state"]))
    assert st["pos"] in (-1, 0, 1)


# ---------------------------------------------------------------- the points of the independent review (22 Nov 2026)
def test_a_pending_entry_saved_by_the_old_rule_fills_at_the_next_open_once():
    # the engine is restarted on a state the old code saved: a pending ENTER must fill at the next open, not again
    inp = list(random_inputs(seed=3))
    px = dict(inp[0])
    px["open"] = px["open"] * 1.0005
    px["high"] = np.maximum(px["high"], px["open"])
    inp[0] = px
    inp = tuple(inp)
    n = len(px["close"])
    st, k = None, None
    for i in range(1, n):
        b = run(inp, OLD, btc(), i, i + 1, st)
        st = json.loads(json.dumps(b["state"]))
        if st["pending"] and st["pos"] == 0 and st["pending"][0] in (policy.ENTER, policy.FORCED):
            k = i
            break
    assert k is not None
    nxt = run(inp, RULE, btc(), k + 1, k + 2, st)["state"]          # the new rule takes over at the next bar
    side = int(st["pending"][1])
    assert nxt["entry"] == px["open"][k + 1] or nxt["pos"] != side   # filled at that open (or already stopped in the bar)
    both = run(inp, RULE, btc(), k + 1, n, st)
    first = both["trades"].iloc[0]
    assert first.p_in == px["open"][k + 1] and first.t_in_ms == (k + 1) * BAR and first.side == side
    assert (both["trades"].t_in_ms.values[1:] > first.t_in_ms).all()   # one entry there, not two


def test_the_first_bar_after_an_early_entry_stops_at_its_open_when_it_gaps_through_the_stop():
    inp = list(random_inputs(seed=3))
    base = run(tuple(inp), RULE, btc())
    t = base["trades"].iloc[0]
    i = int(t.i_in)                                                # the first bar the trade is held in
    px = dict((k, v.copy()) for k, v in inp[0].items())
    gap = t.stop0 - t.side * 0.5                                   # that bar opens beyond the stop
    px["open"][i] = gap
    px["high"][i], px["low"][i] = max(px["high"][i], gap), min(px["low"][i], gap)
    inp[0] = px
    got = run(tuple(inp), RULE, btc())["trades"].iloc[0]
    assert got.p_in == t.p_in == px["close"][i - 1] and got.i_in == i and got.i_out == i
    assert got.why_out == "STOP" and got.p_out == gap and got.t_in_ms == got.t_out_ms   # in at the close, out at the open


def test_a_step_of_several_bars_is_the_bars_one_at_a_time():
    # the catch-up after a restart: several bars in one call, a deciding bar sometimes the last of the call
    inp = random_inputs(seed=17)
    n = len(inp[0]["close"])
    one, st = [], None
    for i in range(1, n):
        b = run(inp, RULE, btc(), i, i + 1, st)
        st = json.loads(json.dumps(b["state"]))
        one += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
    many, st2 = [], None
    for lo in range(1, n, 7):
        b = run(inp, RULE, btc(), lo, min(lo + 7, n), st2)
        st2 = json.loads(json.dumps(b["state"]))
        many += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
    assert len(one) == len(many) > 30
    for a, b in zip(one, many):
        assert (a.t_in_ms, a.t_out_ms, a.side, a.why_in, a.why_out) == (b.t_in_ms, b.t_out_ms, b.side, b.why_in, b.why_out)
        assert abs(a.p_in - b.p_in) < 1e-12 and abs(a.pnl_usd - b.pnl_usd) < 1e-9
    for k in ("pos", "entry", "stop", "t_in_ms", "t1", "t2", "t1_hit", "idle", "pending"):
        assert st[k] == st2[k], k


def test_an_exit_and_a_new_entry_can_share_one_close():
    # a trade stopped (or at Target 2) inside a bar and a new one decided at that bar's close: the state goes from one
    # setup straight to the next, with no flat step between (the feed then closes the old one before it posts the new)
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    st, seen, same_side = None, 0, 0
    for i in range(1, n):
        b = run(inp, RULE, btc(), i, i + 1, st)
        new = json.loads(json.dumps(b["state"]))
        closed = [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
        if st and st["pos"] and closed and new["pos"] and new["t_in_ms"] == i * BAR + BAR and closed[-1].why_in != "x":
            if closed[-1].why_out.split("+")[-1] in ("STOP", "STOP_BE", "T2"):
                seen += 1
                same_side += int(new["pos"] == st["pos"])
                assert new["t_in_ms"] != st["t_in_ms"] and new["entry"] == inp[0]["close"][i]
                # the OLD setup's row is written in this step (a flip that filled and was stopped inside this same
                # bar can add a second row: a setup no step ever showed, as before v5.2.9)
                assert any(t.t_in_ms == st["t_in_ms"] for t in closed)
        st = new
    assert seen >= 3 and same_side >= 1


def test_the_signal_is_issued_in_the_entry_bar_and_the_preview_no_longer_fires_for_these_entries():
    from engine15 import signals, signals_early
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    st = None
    for i in range(1, n):
        prev = st
        st = json.loads(json.dumps(run(inp, RULE, btc(), i, i + 1, st)["state"]))
        if st["pos"] and st["t_in_ms"] == i * BAR + BAR and (not prev or not prev["pos"]):
            break
    view = shadows.asset_view(dict(st, mark=inp[0]["close"][i]))
    assert signals_early.pending_entry(view) is None                # S2 keyed on a pending order: there is none now
    now_ms = st["t_in_ms"] + 150000                                 # the Telegram unit reads the page 2.5 minutes later
    sig, why = signals.build_signal("BTCUSDT", view, now_ms)
    assert why is None and sig["f_ms"] == st["t_in_ms"] == sig["a_ms"]      # bar A is the entry bar itself
    assert sig["follow"]["last_bar_ms"] == st["t_in_ms"] - BAR and sig["valid_until_ms"] == st["t_in_ms"] + 5 * BAR
    assert sig["entry"] == float(view["entry"]) and sig["follow"]["state"] == signals.WAITING

