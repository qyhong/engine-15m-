# -*- coding: utf-8 -*-
"""Half at Target 1 on the main book (think15-v5.2.6, CFG["half_t1"]): planted bars, no network.

The rule (backtest.run_book): in the bar that trades through Target 1 half the position is closed AT Target 1,
the stop of the rest goes to the entry (live from the next bar), and the rest leaves at that stop or on a flip.
The trade is booked once, when the rest closes ("T1+<why>"). A trade already past its Target 1 when the rule
began has its half closed at the next open ("T1_LATE"). Off unless be_t1 AND half_t1 are exactly True.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, exits, labels, live  # noqa: E402
from engine15.config import CFG  # noqa: E402

HALF = dict(CFG, step_aside=False, be_t1=True, half_t1=True)
BE = dict(CFG, step_aside=False, be_t1=True)
OFF = dict(CFG, step_aside=False)
FEE = CFG["cost_side"]


def _odds(n, side):
    o = np.full((n, 3), 0.2)
    o[:, labels.UP if side == 1 else labels.DOWN] = 0.6
    return o


def _px(rows):
    a = np.array(rows, dtype=float)
    return {"open": a[:, 0].copy(), "high": a[:, 1].copy(), "low": a[:, 2].copy(), "close": a[:, 3].copy()}


def _run(px, side, cfg, lo=1, hi=None, state=None):
    n = len(px["close"])
    z = np.zeros(n)
    return backtest.run_book(px, _odds(n, side), z.astype(bool), z, np.full(n, 0.5), cfg, lo, hi or n, state=state,
                             t1_of=lambda i, s, entry, stop: entry + s * 1.0)


# long: filled at bar 2's open (100.0), 100 units ($10,000 at 1x), stop 99.0, Target 1 101.0
LONG = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
        (100, 101.5, 99.5, 101.2),          # bar 3: Target 1 trades -> half out at 101.0, the stop of the rest to 100.0
        (101.2, 101.3, 100.5, 100.6),
        (100.6, 100.7, 99.8, 100.2),        # bar 5: back through the entry -> the rest out at 100.0
        (100.2, 100.3, 100.1, 100.2), (100.2, 100.3, 100.1, 100.2)]
SHORT = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
         (100, 100.5, 98.5, 98.8), (98.8, 99.5, 98.7, 99.4), (99.4, 100.2, 99.3, 99.8),
         (99.8, 99.9, 99.7, 99.8), (99.8, 99.9, 99.7, 99.8)]


def _closed(b):
    t = b["trades"]
    return t[t.why_out != "OPEN"]


def test_half_is_closed_at_target_1_and_the_rest_at_the_entry():
    b = _run(_px(LONG), 1, HALF)
    half_net = 50 * 1.0 - FEE * 50 * (100 + 101)                  # 50 units, +1.00 each, fees on both sides
    rest_net = 0.0 - FEE * 50 * (100 + 100)
    assert len(b["parts"]) == 1
    i, price, q, pnl, tag = b["parts"][0]
    assert (i, price, q, tag) == (3, 101.0, 50.0, "T1") and abs(pnl - half_net) < 1e-9
    assert b["stop"][3] == 100.0 and b["held"][4] == 1            # the rest is still held, its stop at the entry
    assert abs(b["equity"][3] - (10000 + half_net + 50 * (101.2 - 100))) < 1e-9     # banked half + the rest marked
    c = _closed(b)
    assert len(c) == 1                                             # ONE row for the whole trade
    r = c.iloc[0]
    assert r.why_out == "T1+STOP_BE" and r.i_out == 5 and r.qty == 100.0 and abs(r.p_out - 100.5) < 1e-9
    assert abs(r.pnl_usd - (half_net + rest_net)) < 1e-9 and abs(r.fees_usd - FEE * 50 * 401) < 1e-9
    assert abs(r.equity - (10000 + half_net + rest_net)) < 1e-9 and r.pnl_usd > 0     # a profit kept, where be_t1 alone keeps none


def test_short_is_the_mirror():
    b = _run(_px(SHORT), -1, HALF)
    assert b["parts"][0][:3] == (3, 99.0, 50.0) and b["parts"][0][3] > 0
    r = _closed(b).iloc[0]
    assert r.why_out == "T1+STOP_BE" and abs(r.p_out - 99.5) < 1e-9 and r.pnl_usd > 0


def test_state_while_the_rest_runs_and_the_next_trade():
    px = _px(LONG)
    st = _run(px, 1, HALF, hi=5)["state"]                          # bars 1 .. 4: half closed, the rest open
    assert st["pos"] == 1 and st["qty"] == 50.0 and st["stop"] == 100.0 and st["stop0"] == 99.0 and st["t1_hit"] is True
    assert st["half_t1"] is True and st["half_due"] is False and st["part"]["q"] == 50.0 and st["part"]["tag"] == "T1"
    end = _run(px, 1, HALF)["state"]                               # re-entered at bar 6: a fresh full position
    assert end["pos"] == 1 and end["part"] is None and end["t1_hit"] is False and abs(end["qty"] * 100.2 - end["eq"]) < 1e-6


def test_step_by_step_with_saved_state_equals_one_run():
    for rows, side in ((LONG, 1), (SHORT, -1)):
        px = _px(rows)
        whole = _run(px, side, HALF)
        state, closed, parts = None, [], []
        for i in range(1, len(rows)):
            b = _run(px, side, HALF, lo=i, hi=i + 1, state=state)
            state = json.loads(json.dumps(b["state"]))             # the live engine keeps the state as JSON
            closed.append(_closed(b))
            parts += b["parts"]
        closed, w = pd.concat(closed), _closed(whole)
        assert list(closed.why_out) == list(w.why_out) and np.allclose(closed.p_out, w.p_out)
        assert np.allclose(closed.pnl_usd, w.pnl_usd) and np.allclose(closed.qty, w.qty)
        assert [p[:3] for p in parts] == [p[:3] for p in whole["parts"]]
        for k in ("pos", "qty", "entry", "stop", "eq", "fees"):
            assert abs(state[k] - whole["state"][k]) < 1e-9, k


def test_off_unless_both_switches_are_exactly_true():
    px = _px(LONG)
    be = _run(px, 1, BE)
    assert be["parts"] == [] and "part" not in be["state"] and _closed(be).why_out.iloc[0] == "STOP_BE"
    ref = _run(px, 1, OFF)
    for cfg in (dict(OFF, half_t1=True), dict(OFF, half_t1=True, be_t1=("SPX",)), dict(BE, half_t1=("SPX",))):
        b = _run(px, 1, cfg)
        want = be if cfg.get("be_t1") is True else ref             # a LIST never switches a rule on
        assert b["parts"] == [] and np.allclose(b["equity"], want["equity"], equal_nan=True)
        assert b["state"] == want["state"]


def test_summary_counts_a_split_trade_as_one_stop():
    px = _px(LONG)
    b = _run(px, 1, HALF)
    s = backtest.summarize(b, pd.date_range("2026-11-10", periods=len(LONG), freq="15min", tz="UTC"), 1, len(LONG), 2 * FEE)
    assert s["trades"] == 1 and s["stops"] == 1 and s["flips"] == 0 and s["win_rate_pct"] == 100.0


def _times(n):
    return pd.date_range("2026-11-10", periods=n, freq="15min", tz="UTC")


def test_a_trade_already_past_target_1_gets_its_half_at_the_next_open():
    px, times = _px(SHORT), _times(len(SHORT))
    old = {"pos": -1, "idle": 0, "qty": 100.0, "entry": 100.0, "stop": 101.0, "eq": 10000.0, "why_in": "FORCED",
           "pending": None, "fees": 0.0, "target_1": 99.0, "t_in_ms": int(times[2].timestamp() * 1000)}
    new = live.adopt_be_t1(old, px, times, 5, half=True)          # bar 3 traded Target 1 before the rule existed
    assert new["t1_hit"] is True and new["stop"] == 100.0 and new["half_due"] is True and new["half_t1"] is True
    assert live.adopt_be_t1(new, px, times, 5, half=True) is new and old["stop"] == 101.0     # once only; `old` untouched
    b = _run(px, -1, HALF, lo=5, hi=6, state=new)                  # bar 5 opens at 99.4: half out there, not at 99.0
    i, price, q, pnl, tag = b["parts"][0]
    assert (i, price, q, tag) == (5, 99.4, 50.0, "T1_LATE") and abs(pnl - (50 * 0.6 - FEE * 50 * 199.4)) < 1e-9
    st = b["state"]                                                # bar 5's high (100.2) then took the rest at the entry
    assert st["pos"] == 0 or st["qty"] == 50.0
    r = _closed(b).iloc[0]
    assert r.why_out == "T1_LATE+STOP_BE" and r.qty == 100.0 and abs(r.p_out - 99.7) < 1e-9


def test_adoption_leaves_other_cases_alone():
    px, times = _px(SHORT), _times(len(SHORT))
    base = {"pos": -1, "qty": 100.0, "entry": 100.0, "stop": 101.0, "eq": 10000.0, "target_1": 97.0,
            "t_in_ms": int(times[2].timestamp() * 1000)}
    not_yet = live.adopt_be_t1(base, px, times, 5, half=True)     # Target 1 (97.0) has not traded
    assert not_yet["t1_hit"] is False and not_yet["half_due"] is False and not_yet["stop"] == 101.0
    b = _run(px, -1, HALF, lo=5, hi=6, state=dict(not_yet, idle=0, why_in="FORCED", pending=None, fees=0.0))
    assert b["parts"] == []                                        # nothing owed, nothing closed
    usdjpy = {"pos": 1, "qty": 10.0, "entry": 100.0, "stop": 100.0, "eq": 10000.0, "t1": 101.0, "t1_hit": True}
    assert live.adopt_be_t1(usdjpy, px, times, 5) is usdjpy       # a be_t1-only market (half=False): unchanged
    done = dict(usdjpy, part={"q": 5.0, "qpx": 505.0, "pnl": 4.0, "fees": 1.0, "tag": "T1"})
    assert live.adopt_be_t1(done, px, times, 5, half=True)["half_due"] is False     # a half already closed is not closed twice


def test_the_page_shows_the_half():
    part = {"q": 50.0, "qpx": 5050.0, "pnl": 39.95, "fees": 10.05, "tag": "T1"}
    st = {"pos": 1, "qty": 50.0, "entry": 100.0, "stop": 100.0, "eq": 10039.95, "why_in": "FORCED", "pending": None,
          "be_t1": True, "half_t1": True, "t1_hit": True, "part": part, "half_due": False, "target_1": 101.0,
          "target_2": 102.0, "t_in_ms": None}
    now = pd.Timestamp("2026-11-20 15:00", tz="UTC")
    t = live.open_trade("SPX", st, 100.5, now, live.asset_cfg("SPX", CFG))
    assert t["t1_half_closed"] is True and t["t1_half_price"] == 101.0 and t["t1_half_usd"] == 39.95
    assert t["quantity"] == 50.0 and t["realized_usd"] == 39.95 and t["stop_price"] == 100.0
    due = live.open_trade("SPX", dict(st, part=None, half_due=True, qty=100.0, eq=10000.0), 100.5, now,
                          live.asset_cfg("SPX", CFG))
    assert due["t1_half_closed"] is False and "next open" in due["t1_half"]
    other = live.open_trade("USDJPY", dict(st, half_t1=False, part=None), 100.5, now, live.asset_cfg("USDJPY", CFG))
    assert "t1_half" not in other and exits.PART == 0.5
