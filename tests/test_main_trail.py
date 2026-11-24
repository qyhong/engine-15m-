# -*- coding: utf-8 -*-
"""The trailing stop on the main book (think15-v5.2.8, CFG["trail_stop"], CFG["trail_wait_signal"]). No network.

The rule (backtest.run_book, exits.trail_step): once a trade has gone one entry-stop distance in favour, the stop is
the tighter of the last confirmed 15m swing and 2 x ATR(15m) behind the close, live from the next bar, never looser
("TRAIL"). It is the B trail shadow book's exit on the main book's own trades. With trail_wait, a "TRAIL" exit
switches the forced entry off until one side clears the entry bar. Owner, 21 Nov 2026: "Update minds 15 with tight
trailing stop"; "Six markets"; "Wait for a signal".

    py -3 -m pytest tests/test_main_trail.py -q
"""
import copy
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import backtest, exits, labels, live, policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import COMPARE, random_inputs, run_random  # noqa: E402

TRAIL = dict(CFG, trail_stop=True)                               # the trail, the mandate as it was (the B trail book)
WAIT = dict(TRAIL, trail_wait=True)                              # the trail, no forced entry after a trail exit
SIX = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT")


def _book(cfg, inp, lo=1, hi=None, state=None, aux="own"):
    px, odds, unit, shock, tide, bias, guard, a = inp
    return backtest.run_book(px, odds, shock, tide, unit, cfg, lo, hi or len(odds), state=state, bias=bias, guard=guard,
                             trail_aux=a if aux == "own" else aux)


def _closed(b):
    t = b["trades"]
    return t[t.why_out != "OPEN"].reset_index(drop=True)


# ------------------------------------------------------------------ the rule is the B trail shadow book's
def test_main_book_with_the_trail_is_the_b_trail_shadow_book():
    for seed in (3, 11):
        inp = random_inputs(seed=seed)
        ref = run_random({"trail": True}, inp)                   # shadows.run, the book that has run it forward
        b = _book(TRAIL, inp)
        closed = _closed(b)
        assert int((closed.why_out == "TRAIL").sum()) > 10
        pd.testing.assert_frame_equal(closed[COMPARE], ref["trades"][COMPARE], check_dtype=False, rtol=0, atol=0)
        assert np.array_equal(b["equity"][1:], ref["equity"][1:]) and np.array_equal(b["held"], ref["held"])
        assert b["state"]["eq"] == ref["state"]["eq"] and b["state"]["pos"] == ref["state"]["pos"]


def test_off_unless_exactly_true_and_given_its_arrays():
    inp = random_inputs()
    plain = _book(CFG, inp, aux=None)
    for cfg, aux in ((CFG, "own"),                               # the raw CFG holds the LIST of markets: never "on"
                     (dict(CFG, trail_stop=SIX), "own"), (dict(CFG, trail_stop=1), "own"), (TRAIL, None),
                     (dict(TRAIL, be_t1=True), "own")):          # never together with the Target 1 rules (no planner: off)
        b = _book(cfg, inp, aux=aux) if cfg.get("be_t1") is not True else backtest.run_book(
            inp[0], inp[1], inp[3], inp[4], inp[2], cfg, 1, len(inp[1]), bias=inp[5], guard=inp[6],
            t1_of=lambda i, s, entry, stop: None, trail_aux=inp[7])
        pd.testing.assert_frame_equal(b["trades"], plain["trades"])
        assert "trail_stop" not in b["state"] and "wait_signal" not in b["state"]
    assert isinstance(CFG["trail_stop"], tuple) and CFG.get("trail_stop") is not True


def test_one_bar_of_the_rule():
    # long from 100, entry stop 99 (R = 1): not armed below 1R; armed by a HIGH at 1R; then the tighter of swing and ATR
    assert exits.trail_step(1, 100.0, 99.0, 99.0, False, 100.9, 100.0, 100.5, 0.2, 99.5) == (False, 99.0)
    assert exits.trail_step(1, 100.0, 99.0, 99.0, False, 101.0, 100.0, 100.6, 0.2, 99.5) == (True, 100.6 - 0.4)
    assert exits.trail_step(1, 100.0, 99.0, 99.0, True, 101.0, 100.0, 100.6, 0.2, 100.4) == (True, 100.4)   # the swing
    assert exits.trail_step(1, 100.0, 100.5, 99.0, True, 101.0, 100.0, 100.6, 0.2, 100.3)[1] == 100.5      # never looser
    assert exits.trail_step(1, 100.0, 99.0, 99.0, True, 101.0, 100.0, 100.6, 0.2, 100.9)[1] == 100.6 - 0.4  # wrong side
    assert exits.trail_step(-1, 100.0, 101.0, 101.0, False, 100.0, 99.0, 99.4, 0.2, 99.5) == (True, 99.5)   # short
    assert exits.trail_step(1, 100.0, 99.0, float("nan"), False, 105.0, 100.0, 104.0, 0.2, 99.5) == (False, 99.0)
    assert (shadows.TRAIL_ARM_R, shadows.TRAIL_ATR) == (exits.TRAIL_ARM_R, exits.TRAIL_ATR) == (1.0, 2.0)


# ------------------------------------------------------------------ planted bars: the exit and what follows it
def _px(rows):
    a = np.array(rows, dtype=float)
    return {"open": a[:, 0].copy(), "high": a[:, 1].copy(), "low": a[:, 2].copy(), "close": a[:, 3].copy()}


def _odds(n, strong=()):
    """No edge anywhere (0.3 / 0.3) except the bars in `strong`: {bar: +1 / -1} leans 40 points that way."""
    o = np.full((n, 3), 0.3)
    for k, side in dict(strong).items():
        o[k] = 0.2
        o[k, labels.UP if side == 1 else labels.DOWN] = 0.6
    return o


QUIET = (100.8, 100.9, 100.7, 100.8)
# long filled at bar 2's open (100.0); unit 0.5 x stop_units 2 = entry stop 99.0 (R = 1.0)
WIN = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
       (100, 101.5, 99.9, 101.2),           # bar 3: 1.5R high arms the trail; stop = 101.2 - 2 x 0.2 = 100.8
       (101.2, 101.3, 100.7, 100.8)] + [QUIET] * 14     # bar 4: the low trades 100.8 -> "TRAIL" at 100.8
LOSS = [(100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100), (100, 100.1, 99.9, 100),
        (100, 100.2, 98.9, 99.0)] + [(99.0, 99.1, 98.95, 99.0)] * 12       # bar 3: the entry stop, before any trail


def _run(rows, cfg, strong, lo=1, hi=None, state=None):
    px = _px(rows)
    n = len(rows)
    z = np.zeros(n)
    aux = {"atr15": np.full(n, 0.2), "sw_lo": np.full(n, np.nan), "sw_hi": np.full(n, np.nan)}
    return backtest.run_book(px, _odds(n, strong), z.astype(bool), z, np.full(n, 0.5), dict(cfg, htf_bias=False), lo,
                             hi or n, state=state, trail_aux=aux)


def test_the_trail_closes_the_trade_in_profit():
    b = _run(WIN, TRAIL, {1: 1})
    first = _closed(b).iloc[0]
    assert (first.i_in, first.i_out, first.why_out, first.p_in, first.p_out) == (2, 4, "TRAIL", 100.0, 100.8)
    assert b["stop"][2] == 99.0 and abs(b["stop"][3] - 100.8) < 1e-12        # set at bar 3's close, live in bar 4
    assert first.pnl_usd > 0


def test_with_the_mandate_the_book_is_forced_back_in_after_four_sessions():
    b = _run(WIN, TRAIL, {1: 1})
    assert list(b["held"][4:10]) == [1, 0, 0, 0, 0, 1]           # flat bars 5-8, FORCED at bar 8's close, in at bar 9
    assert _closed(b).why_in.iloc[0] == policy.ENTER and b["state"]["why_in"] == policy.FORCED


def test_wait_for_a_signal_no_forced_entry_after_a_trail_exit():
    b = _run(WIN, WAIT, {1: 1})
    assert len(_closed(b)) == 1 and b["state"]["pos"] == 0 and not b["held"][5:].any()
    assert b["state"]["wait_signal"] is True and b["state"]["trail_wait"] is True
    assert list(b["reason"][8:]) == ["wait_for_signal_after_trail"] * (len(WIN) - 8)   # where the mandate would force
    assert backtest.ACTIONS[int(b["act"][10])] == policy.IDLE and b["state"]["idle"] == len(WIN) - 4
    # a signal ends the wait: one side clears the entry bar at bar 12's close -> in at bar 13's open
    c = _run(WIN, WAIT, {1: 1, 12: -1})
    assert c["state"]["pos"] == -1 and c["state"]["i_in"] == 13 and c["state"]["why_in"] == policy.ENTER
    assert c["state"]["wait_signal"] is False and c["state"]["trail_on"] is False
    assert not c["held"][5:13].any() and c["held"][13] == -1


def test_a_stop_out_at_the_entry_stop_keeps_the_mandate():
    b = _run(LOSS, WAIT, {1: 1})
    first = _closed(b).iloc[0]
    assert (first.i_out, first.why_out, first.p_out) == (3, "STOP", 99.0)
    assert b["state"]["pos"] != 0 and b["state"]["why_in"] == policy.FORCED and b["state"]["wait_signal"] is False
    assert list(b["held"][3:9]) == [1, 0, 0, 0, 0, 1]


def test_a_long_wait_does_not_overflow_the_idle_array():
    rows = WIN + [QUIET] * 300
    b = _run(rows, WAIT, {1: 1})
    assert b["state"]["idle"] == len(rows) - 4 and int(b["idle"][-1]) == 127 and b["state"]["pos"] == 0


# ------------------------------------------------------------------ the live engine advances one step at a time
def test_resumes_exactly_across_any_cut():
    inp = random_inputs(seed=7)
    n = len(inp[1])
    whole = _book(WAIT, inp)
    assert int((_closed(whole).why_out == "TRAIL").sum()) > 5
    assert "wait_for_signal_after_trail" in set(whole["reason"][1:])
    waits = [i for i in range(2, n - 1) if whole["reason"][i] == "wait_for_signal_after_trail"]
    opens = [i for i in range(2, n - 1) if whole["held"][i] != 0]
    for cut in (waits[0] + 1, waits[len(waits) // 2], opens[len(opens) // 3], opens[-1], 450):
        a = _book(WAIT, inp, hi=cut)
        b = _book(WAIT, inp, lo=cut, state=copy.deepcopy(a["state"]))
        assert b["state"] == dict(whole["state"], entered_here=b["state"]["entered_here"], i_in=b["state"]["i_in"]), cut
        assert np.array_equal(b["equity"][cut:], whole["equity"][cut:]), cut
    # one bar at a time, as the live step does
    st = None
    for i in range(1, 200):
        st = _book(WAIT, inp, lo=i, hi=i + 1, state=st)["state"]
    ref = _book(WAIT, inp, hi=200)["state"]
    assert st["eq"] == ref["eq"] and st["pos"] == ref["pos"] and st["stop"] == ref["stop"]
    assert st["wait_signal"] == ref["wait_signal"] and st["trail_on"] == ref["trail_on"]


def test_a_trade_already_running_comes_under_the_rule_at_the_first_step():
    # the live books of 21 Nov: trades opened before the rule, far past 1R, a state with no trail keys
    rows = WIN[:4] + [(101.4, 101.6, 101.3, 101.5)] * 3     # lows stay above the trailed stop (101.1)
    old = _run(rows, dict(CFG), {1: 1}, hi=5)["state"]           # the book as v5.2.7 left it: long, entry stop 99.0
    assert old["pos"] == 1 and old["stop"] == 99.0 and "stop0" not in old and "trail_on" not in old
    b = _run(rows, WAIT, {1: 1}, lo=5, state=old)
    st = b["state"]
    assert st["trail_on"] is True and st["stop0"] == 99.0 and abs(st["stop"] - (101.5 - 0.4)) < 1e-12
    assert st["pos"] == 1 and st["entry"] == 100.0 and st["qty"] == old["qty"]       # the trade itself is untouched


# ------------------------------------------------------------------ which markets, and what the page says
def test_six_markets_trail_and_the_two_target_markets_do_not():
    assert CFG["trail_stop"] == SIX and CFG["trail_wait_signal"] == SIX
    assert not set(CFG["trail_stop"]) & set(CFG["be_t1"]) and set(CFG["trail_wait_signal"]) <= set(CFG["trail_stop"])
    for a in SIX:
        c = live.asset_cfg(a, CFG)
        assert c["trail_stop"] is True and c["trail_wait"] is True and c["be_t1"] is False
    for a in ("USDJPY", "SPX"):
        c = live.asset_cfg(a, CFG)
        assert c["trail_stop"] is False and c["trail_wait"] is False and c["be_t1"] is True
    assert CFG["version"] == "think15-v5.2.10" and CFG["idle_max"] == 4


def test_the_page_says_where_the_stop_stands_and_what_it_locks():
    now = pd.Timestamp("2026-11-21 03:00", tz="UTC")
    st = {"pos": -1, "qty": 2.0, "entry": 100.0, "stop": 96.0, "eq": 10000.0, "why_in": "FORCED", "pending": None,
          "trail_stop": True, "trail_on": True, "trail_wait": True, "stop0": 102.0, "target_1": 97.0, "t_in_ms": None}
    t = live.open_trade("BTCUSDT", st, 95.0, now, live.asset_cfg("BTCUSDT", CFG))
    assert t["stop_price"] == 96.0 and t["stop_locks_usd"] == 8.0 and t["risk_to_stop_usd"] == 0.0
    assert t["stop_basis"].startswith("trailing") and t["trail_on"] is True and t["targets_traded"].startswith("no")
    assert t["target_1_r"] == 1.5                                # R on the ENTRY stop (2.0 away), not the trailed one
    assert "no forced entry" in t["after_trail_exit"]
    early = live.open_trade("BTCUSDT", dict(st, trail_on=False, stop=102.0), 99.5, now, live.asset_cfg("BTCUSDT", CFG))
    assert early["stop_basis"].startswith("the entry stop") and early["stop_locks_usd"] is None
    assert early["risk_to_stop_usd"] == 4.0
    flat = live.open_trade("BTCUSDT", {"pos": 0, "idle": 37, "eq": 10000.0, "pending": None, "wait_signal": True}, 95.0,
                           now, live.asset_cfg("BTCUSDT", CFG))
    assert flat["status"] == "FLAT" and flat["wait_signal"] is True and "no forced entry" in flat["waiting_for"]
    plain = live.open_trade("BTCUSDT", {"pos": 0, "idle": 2, "eq": 10000.0, "pending": None}, 95.0, now,
                            live.asset_cfg("BTCUSDT", CFG))
    assert "wait_signal" not in plain and plain["idle_sessions"] == 2
    other = live.open_trade("USDJPY", dict(st, trail_stop=False, stop=102.0), 99.5, now, live.asset_cfg("USDJPY", CFG))
    assert other["stop_basis"] is None and "stop_locks_usd" not in other and other["risk_to_stop_usd"] == 4.0


def test_a_stop_beyond_the_entry_is_no_risk_in_the_total_risk_cap(monkeypatch):
    monkeypatch.setitem(CFG, "risk_cap_pct", 6.0)
    every = [a for _g, assets in live.universes() for a in assets]
    books = dict((a, {"eq": 10000.0, "pos": 0}) for a in every)
    base = live.risk_budget("ETHUSDT", {"books": books})
    books["BTCUSDT"] = {"eq": 10000.0, "pos": -1, "qty": 2.0, "entry": 100.0, "stop": 102.0}     # the entry stop: $4 at risk
    assert abs(base - live.risk_budget("ETHUSDT", {"books": books}) - 4.0) < 1e-9
    books["BTCUSDT"]["stop"] = 96.0                               # trailed past the entry: a stop-out loses nothing
    assert live.risk_budget("ETHUSDT", {"books": books}) == base
    books["BTCUSDT"] = {"eq": 10000.0, "pos": 1, "qty": 2.0, "entry": 100.0, "stop": 98.0}
    assert abs(base - live.risk_budget("ETHUSDT", {"books": books}) - 4.0) < 1e-9
