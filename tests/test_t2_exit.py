# -*- coding: utf-8 -*-
"""The rest at Target 2 on the main book (think15-v5.2.7, CFG["t2_exit"]): planted bars, no network.

The rule (backtest.run_book): half at Target 1 (v5.2.6), the stop of the rest to the entry (v5.2.5), and, new, the rest
closed AT Target 2 in the bar that trades it ("T2"). Owner, 20 Nov 2026, for USDJPY: "Sell at target". With the three
switches on, the main book exits as the Setups book does (shadows.run under b_targets). Off unless be_t1, half_t1 and
t2_exit are exactly True and both planners are given.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, labels, live, reports, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

T2 = dict(CFG, step_aside=False, be_t1=True, half_t1=True, t2_exit=True)
HALF = dict(CFG, step_aside=False, be_t1=True, half_t1=True)
FEE = CFG["cost_side"]


def _odds(n, side):
    o = np.full((n, 3), 0.2)
    o[:, labels.UP if side == 1 else labels.DOWN] = 0.6
    return o


def _px(rows):
    a = np.array(rows, dtype=float)
    return {"open": a[:, 0].copy(), "high": a[:, 1].copy(), "low": a[:, 2].copy(), "close": a[:, 3].copy()}


def _run(px, side, cfg, lo=1, hi=None, state=None, t2_of="plan"):
    n = len(px["close"])
    z = np.zeros(n)
    if t2_of == "plan":
        t2_of = lambda i, s, entry, stop: entry + s * 2.0         # Target 2 = two stop distances away
    return backtest.run_book(px, _odds(n, side), z.astype(bool), z, np.full(n, 0.5), cfg, lo, hi or n, state=state,
                             t1_of=lambda i, s, entry, stop: entry + s * 1.0, t2_of=t2_of)


def _closed(b):
    t = b["trades"]
    return t[t.why_out != "OPEN"]


# long: filled at bar 2's open (100.0), 100 units, stop 99.0, Target 1 101.0, Target 2 102.0
LONG = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
        (100, 101.5, 99.5, 101.2),          # bar 3: Target 1 -> half out at 101.0, the stop of the rest to 100.0
        (101.2, 101.6, 100.9, 101.5),
        (101.5, 102.3, 101.4, 102.1),       # bar 5: Target 2 -> the rest out at 102.0
        (102.1, 102.2, 102.0, 102.1), (102.1, 102.2, 102.0, 102.1), (102.1, 102.2, 102.0, 102.1),
        (102.1, 102.2, 102.0, 102.1), (102.1, 102.2, 102.0, 102.1), (102.1, 102.2, 102.0, 102.1)]
SHORT = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
         (100, 100.5, 98.5, 98.8), (98.8, 99.1, 98.4, 98.5), (98.5, 98.6, 97.7, 97.9),
         (97.9, 98.0, 97.8, 97.9), (97.9, 98.0, 97.8, 97.9), (97.9, 98.0, 97.8, 97.9), (97.9, 98.0, 97.8, 97.9)]


def test_half_at_target_1_then_the_rest_at_target_2():
    b = _run(_px(LONG), 1, T2)
    c = _closed(b)
    first = c[c.i_in == 2]
    assert list(first.why_out) == ["T1", "T2"] and list(first.i_out) == [3, 5] and list(first.p_out) == [101.0, 102.0]
    assert list(first.qty) == [50.0, 50.0]
    half = 50 * 1.0 - FEE * 50 * (100 + 101)
    rest = 50 * 2.0 - FEE * 50 * (100 + 102)
    assert abs(first.pnl_usd.iloc[0] - half) < 1e-9 and abs(first.pnl_usd.iloc[1] - rest) < 1e-9
    assert abs(first.equity.iloc[1] - (10000 + half + rest)) < 1e-9
    # flat after Target 2; the decision at that same close starts from flat (here the odds lean 40 points up, so it
    # enters again at the next open: a NEW trade with its own entry, stop and targets)
    assert b["held"][5] == 1 and b["state"]["pos"] == 1 and b["state"]["entry"] == 102.1
    assert abs(b["state"]["t1"] - 103.1) < 1e-9 and abs(b["state"]["t2"] - 104.1) < 1e-9 and b["state"]["t1_hit"] is False
    assert reports.per_entry([((r.i_in, r.side), r.pnl_usd) for r in first.itertuples()]) == [half + rest]


def test_short_is_the_mirror():
    c = _closed(_run(_px(SHORT), -1, T2))
    first = c[c.i_in == 2]
    assert list(first.why_out) == ["T1", "T2"] and list(first.p_out) == [99.0, 98.0] and list(first.i_out) == [3, 5]


def test_both_targets_in_one_bar():
    rows = list(LONG)
    rows[3] = (100, 102.4, 99.5, 102.2)                           # Target 1 and Target 2 in the same bar
    first = _closed(_run(_px(rows), 1, T2))
    first = first[first.i_in == 2]
    assert list(first.why_out) == ["T1", "T2"] and list(first.i_out) == [3, 3] and list(first.p_out) == [101.0, 102.0]


def test_the_stop_comes_before_the_targets_in_one_bar():
    rows = list(LONG)
    rows[3] = (100, 102.4, 98.9, 99.2)                            # the stop (99.0) and both targets in one bar
    first = _closed(_run(_px(rows), 1, T2))
    first = first[first.i_in == 2]
    assert list(first.why_out) == ["STOP"] and first.p_out.iloc[0] == 99.0 and first.qty.iloc[0] == 100.0


def test_back_to_the_entry_after_target_1_is_still_the_entry_stop():
    rows = list(LONG)
    rows[5] = (101.5, 101.6, 99.8, 100.2)                         # never reaches Target 2; back through the entry
    first = _closed(_run(_px(rows), 1, T2))
    first = first[first.i_in == 2]
    assert list(first.why_out) == ["T1", "STOP_BE"] and list(first.p_out) == [101.0, 100.0]


def test_target_2_before_target_1_is_impossible_and_no_target_2_means_the_rest_runs():
    b = _run(_px(LONG), 1, T2, t2_of=lambda i, s, entry, stop: None)    # the plan has no Target 2
    first = _closed(b)
    first = first[first.i_in == 2]
    assert list(first.why_out) == ["T1"] and b["state"]["pos"] == 1 and b["state"]["t2"] is None


def test_off_unless_all_three_switches_and_the_planner():
    px = _px(LONG)
    ref = _run(px, 1, HALF, t2_of=None)                           # v5.2.6: half at Target 1, the rest runs
    assert list(_closed(ref).why_out) == ["T1"] and "t2" not in ref["state"] and "t2_exit" not in ref["state"]
    for cfg, t2_of in ((HALF, "plan"), (T2, None), (dict(T2, half_t1=False), "plan"), (dict(T2, be_t1=False), "plan"),
                       (dict(T2, t2_exit=("USDJPY",)), "plan")):   # a list of markets must never switch it on
        b = _run(px, 1, cfg, t2_of=t2_of)
        assert "T2" not in set(b["trades"].why_out), cfg.get("t2_exit")
    same = _run(px, 1, HALF, t2_of="plan")
    assert np.allclose(same["equity"], ref["equity"], equal_nan=True) and same["state"] == ref["state"]


def test_step_by_step_with_saved_state_equals_one_run():
    for rows, side in ((LONG, 1), (SHORT, -1)):
        px, n = _px(rows), len(rows)
        whole = _run(px, side, T2)
        state, closed = None, []
        for i in range(1, n):
            b = _run(px, side, T2, lo=i, hi=i + 1, state=state)
            state = json.loads(json.dumps(b["state"]))
            closed.append(_closed(b))
        closed, w = pd.concat(closed), _closed(whole)
        assert list(closed.why_out) == list(w.why_out) and np.allclose(closed.p_out, w.p_out)
        assert np.allclose(closed.pnl_usd, w.pnl_usd) and np.allclose(closed.qty, w.qty)
        for k in ("pos", "qty", "entry", "eq", "fees", "t1", "t2", "t1_hit"):
            a, b_ = state[k], whole["state"][k]
            assert a == b_ or abs(a - b_) < 1e-9, k


def test_the_main_book_now_exits_as_the_setups_book_does():
    """With the three switches on, run_book and shadows.run under b_targets end with the same equity on random bars:
    the same entries, the half at Target 1, the stop to the entry, the rest at Target 2."""
    rng = np.random.RandomState(11)
    n = 700
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.003, n)) * c
    px = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
    odds = rng.dirichlet(np.ones(3) * 25, size=n)
    odds[:5] = np.nan
    unit, shock, tide = c * 0.004, rng.rand(n) < 0.05, rng.uniform(-1, 1, n)
    bias, guard = rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.2, 0.6, 0.2]), rng.rand(n) < 0.03
    reach = pd.DataFrame({"reach_24h_med_pct": rng.uniform(0.5, 2.0, n)})
    cfg = dict(CFG, be_t1=True, half_t1=True, t2_exit=True)
    plan = lambda k, i, s, entry, stop: live.plan_targets(int(s), float(entry), float(stop), reach.iloc[i - 1]).get(k)
    main = backtest.run_book(px, odds, shock, tide, unit, cfg, 1, n, bias=bias, guard=guard,
                             t1_of=lambda *a: plan("target_1", *a), t2_of=lambda *a: plan("target_2", *a))
    book = shadows.run(px, odds, shock, tide, unit, CFG, 1, n, bias=bias, guard=guard, rule={"targets": True},
                       times_ms=np.arange(n, dtype="int64") * 900000, row_of=lambda k: reach.iloc[k])
    m = main["trades"][main["trades"].why_out != "OPEN"]
    s = book["trades"]
    assert len(s) > 40 and {"T1", "T2", "STOP", "STOP_BE"} <= set(m.why_out)
    assert abs(main["state"]["eq"] - book["state"]["eq"]) < 1e-6          # to the cent and beyond, trade for trade:
    per = reports.per_entry([((r.i_in, r.side), r.pnl_usd) for r in m.itertuples()])
    assert len(per) == len(s) and np.allclose(per, s.pnl_usd.values, atol=1e-6)


def test_a_running_trade_gets_its_planned_target_2():
    px = _px(LONG)
    times = pd.date_range("2026-11-20", periods=len(LONG), freq="15min", tz="UTC")
    old = {"pos": 1, "idle": 0, "qty": 100.0, "entry": 100.0, "stop": 99.0, "eq": 10000.0, "why_in": "FORCED",
           "pending": None, "fees": 0.0, "be_t1": True, "t1": 101.0, "t1_hit": False, "stop0": 99.0,
           "target_1": 101.0, "target_2": 102.0, "t_in_ms": int(times[2].timestamp() * 1000)}
    new = live.adopt_be_t1(old, px, times, 3, half=True, t2=True)   # the USDJPY long of 20 Nov: under be_t1 already
    assert new is not old and "t2" not in old
    assert new["t2"] == 102.0 and new["t2_exit"] is True and new["half_t1"] is True and new["half_due"] is False
    assert live.adopt_be_t1(new, px, times, 3, half=True, t2=True) is new       # once only
    c = _closed(_run(px, 1, T2, lo=3, state=new))
    assert list(c.why_out)[:2] == ["T1", "T2"] and list(c.p_out)[:2] == [101.0, 102.0]
    no_plan = live.adopt_be_t1(dict(old, target_2=None), px, times, 3, half=True, t2=True)
    assert no_plan["t2"] is None and no_plan["t2_exit"] is True    # no Target 2 planned: the rest runs


def test_only_usdjpy_sells_the_rest_at_target_2():
    assert CFG["t2_exit"] == ("USDJPY",) and CFG["half_t1"] == ("SPX", "USDJPY") and CFG["be_t1"] == ("USDJPY", "SPX")
    assert CFG["version"] == "think15-v5.2.9" and CFG["idle_max"] == 4          # the mandate is unchanged (v5.2.8: trail)
    u, s = live.asset_cfg("USDJPY", CFG), live.asset_cfg("SPX", CFG)
    assert (u["be_t1"], u["half_t1"], u["t2_exit"]) == (True, True, True)
    assert (s["be_t1"], s["half_t1"], s["t2_exit"]) == (True, True, False)
    for a in ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT"):
        x = live.asset_cfg(a, CFG)
        assert (x["be_t1"], x["half_t1"], x["t2_exit"]) == (False, False, False)


def test_the_page_says_what_the_book_does_at_its_targets():
    st = {"pos": 1, "qty": 100.0, "entry": 100.0, "stop": 99.0, "eq": 10000.0, "why_in": "FORCED", "pending": None,
          "be_t1": True, "half_t1": True, "t2_exit": True, "t1_hit": False, "part": None, "half_due": False,
          "target_1": 101.0, "target_2": 102.0, "t_in_ms": None}
    now = pd.Timestamp("2026-11-20 15:00", tz="UTC")
    t = live.open_trade("USDJPY", st, 100.5, now, live.asset_cfg("USDJPY", CFG))
    assert t["targets_traded"] == "half at Target 1, the rest at Target 2" and t["t1_half_closed"] is False
    spx = live.open_trade("SPX", dict(st, t2_exit=False), 100.5, now, live.asset_cfg("SPX", CFG))
    assert "the rest runs" in spx["targets_traded"]
    btc = live.open_trade("BTCUSDT", dict(st, be_t1=False, half_t1=False, t2_exit=False), 100.5, now,
                          live.asset_cfg("BTCUSDT", CFG))
    assert "targets_traded" not in btc
