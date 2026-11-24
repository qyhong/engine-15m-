# -*- coding: utf-8 -*-
"""The pure read-outs of H114 (research/h114_usdjpy_stop.py): no history is loaded.

    py -3 -m pytest tests/test_h114.py -q
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h114_usdjpy_stop as h  # noqa: E402
from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs  # noqa: E402


def _trade(i_in, i_out, side, p_in, stop0, why="STOP"):
    row = dict((c, np.nan) for c in shadows.TRADE_COLS)
    row.update(i_in=i_in, i_out=i_out, side=side, p_in=p_in, stop0=stop0, why_out=why, why_in="FORCED", pnl_usd=-1.0,
               r_mult=-1.0, fees_usd=0.1, qty=1.0)
    return row


def test_fall_is_measured_inside_the_period_from_its_base():
    assert abs(h.fall_pct([110, 99, 120], 100) - (99 / 110 - 1) * 100) < 1e-9
    assert abs(h.fall_pct([90, 95], 100) + 10.0) < 1e-9            # the base is the first peak
    assert h.fall_pct([101, 102], 100) == 0.0
    assert abs(h.fall_pct([np.nan, 50], 100) + 50.0) < 1e-9


def test_ratio_and_the_registered_guard():
    cur = {"net_pct": 10.0, "fall_pct": -20.0}
    assert abs(h.ratio(cur) - 0.5) < 1e-12
    assert h.leg(cur, {"net_pct": 12.0, "fall_pct": -20.0}) == {"holds": True, "by": "ratio", "bare_ratio_higher": True}
    assert h.leg(cur, {"net_pct": 12.0, "fall_pct": -30.0})["holds"] is False
    # both lose: the same loss with a deeper fall has a "higher" ratio and must NOT count
    lose = {"net_pct": -10.0, "fall_pct": -20.0}
    assert h.ratio({"net_pct": -10.0, "fall_pct": -40.0}) > h.ratio(lose)
    assert h.leg(lose, {"net_pct": -10.0, "fall_pct": -40.0})["holds"] is False
    assert h.leg(lose, {"net_pct": -5.0, "fall_pct": -40.0})["holds"] is False      # lost less, fell deeper
    assert h.leg(lose, {"net_pct": -5.0, "fall_pct": -20.0})["holds"] is True       # lost less, not deeper
    # the guard is not always the harder test: a smaller loss with a shallower fall can have a LOWER bare ratio
    g = h.leg({"net_pct": -19.9, "fall_pct": -53.1}, {"net_pct": -17.5, "fall_pct": -46.2})
    assert g["holds"] is True and g["bare_ratio_higher"] is False
    assert h.leg(lose, {"net_pct": 1.0, "fall_pct": -50.0})["holds"] is True        # a gain against a loss


def test_verdict_needs_every_leg_and_the_total():
    def per(net, fall, usd):
        return {"net_pct": net, "fall_pct": fall, "net_usd": usd, "sum_r": net}
    cur = dict((p, per(5.0, -10.0, 500.0)) for p in h.PERIODS)
    good = dict((p, per(8.0, -10.0, 800.0)) for p in h.PERIODS)
    assert h.verdict(cur, good)["passes"] is True
    one_bad = dict(good, holdout=per(4.0, -10.0, 400.0))
    assert h.verdict(cur, one_bad)["passes"] is False
    low_total = dict(good, all=per(8.0, -10.0, 400.0))
    assert h.verdict(cur, low_total)["passes"] is False
    assert h.leave_out(cur)["proposal"] is False
    assert h.leave_out(dict((p, per(-1.0, -10.0, -1.0)) for p in h.PERIODS))["proposal"] is True
    assert h.leave_out(dict(cur, h1=per(-1.0, -10.0, -1.0)))["proposal"] is False


def test_stop_reversals_counts_back_and_further():
    n = 400
    high, low = np.full(n, 100.2), np.full(n, 99.8)
    tr = pd.DataFrame([_trade(10, 20, 1, 101.0, 100.0),            # long: back at 101 at bar 50
                       _trade(100, 110, 1, 101.0, 100.0),          # long: a further stop distance (99.0) at bar 150
                       _trade(200, 210, -1, 99.0, 100.0),          # short: neither
                       _trade(300, 350, 1, 101.0, 100.0),          # too close to the end: not judged
                       _trade(5, 8, 1, 101.0, 100.0, why="T1+STOP_BE")])
    high[50], low[150] = 101.0, 99.0
    high[20] = 105.0                                               # the exit bar itself is not counted
    s = h.stop_reversals(tr, high, low, 0, n, look=96)
    assert (s["stopouts"], s["judged"], s["back"], s["further"], s["both"], s["neither"]) == (4, 3, 1, 1, 0, 1)
    assert s["back_rows"] == [(10, 50, 1, 101.0, 100.0)]
    assert h.stop_reversals(tr, high, low, 0, 100, look=96)["stopouts"] == 1      # by entry bar
    # read-out 5: a 3.0 stop from the same entry sits at 99.5, a 4.0 stop at 99.0; the low on the way was 99.8
    assert h.sat_through(s["back_rows"], high, low, 2.0, 3.0) == {"of": 1, "kept": 1, "kept_pct": 100.0}
    low[30] = 99.4
    assert h.sat_through(s["back_rows"], high, low, 2.0, 3.0)["kept"] == 0
    assert h.sat_through(s["back_rows"], high, low, 2.0, 4.0)["kept"] == 1


def test_a_wider_stop_through_cfg_keeps_the_2pct_size_and_the_engine_book():
    px, odds, unit, shock, tide, bias, guard, aux = random_inputs(n=3000, seed=11)
    n = len(px["close"])
    tms = np.arange(n, dtype="int64") * 900000
    tgt = aux["targets"]
    row_of = lambda k: tgt.iloc[k]                                 # noqa: E731
    rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
    base = dict(shadows.asset_cfg("USDJPY", dict(CFG)))
    books, cfgs = {}, {}
    for name, units in h.BOOKS:
        cfgs[name] = dict(base, stop_units=units)
        books[name] = shadows.run(px, odds, shock, tide, unit, cfgs[name], 1, n, bias=bias, guard=guard, rule=rule, aux=aux,
                                  times_ms=tms, row_of=row_of)
    ref = shadows.run(px, odds, shock, tide, unit, base, 1, n, bias=bias, guard=guard, rule=rule, aux=aux, times_ms=tms,
                      row_of=row_of)
    assert len(ref["trades"]) == len(books["s2"]["trades"]) and np.allclose(ref["equity"][1:], books["s2"]["equity"][1:])
    for name, units in h.BOOKS:
        t = books[name]["trades"]
        assert len(t) > 20
        dist = (t.p_in - t.stop0).abs().values
        assert np.allclose(dist, units * unit[t.i_in.values - 1])                 # the stop is `units` barriers away
        z = h.sizing(t, cfgs[name])
        assert z["at_floor_pct"] == 0.0 and z["at_cap_pct"] == 0.0
        # sized by the 2% rule: the loss at the stop is 2% of the equity at the entry (equity before = after - pnl)
        assert np.allclose(t.risk_usd.values, 0.02 * (t.equity.values - t.pnl_usd.values), rtol=1e-9)
        assert h.target_facts(t, tgt)["not_reproduced"] == 0
    res = h.analyse(books, cfgs, px, 1, n, {"mid": 1000, "holdout": 2000, "forward": 2800}, tgt)
    for name, _u in h.BOOKS:
        p = res["books"][name]["periods"]
        assert p["h1"]["trades"] + p["h2"]["trades"] == p["all"]["trades"]
        assert p["mid"]["trades"] + p["holdout"]["trades"] == p["h2"]["trades"]
        assert abs(p["h1"]["net_usd"] + p["h2"]["net_usd"] - p["all"]["net_usd"]) < 1e-6
        assert abs(p["all"]["net_usd"] - (books[name]["equity"][n - 1] - shadows.START_EQUITY)) < 1e-9
    assert set(res["verdict"]) == {"s3", "s4"} and res["passes"] == res["verdict"]["s3"]["passes"]
    assert set(res["books"]["s2"]["stops"]["all"]["sat_through"]) == {"s3", "s4"}
