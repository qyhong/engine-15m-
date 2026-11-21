# -*- coding: utf-8 -*-
"""The challenger shadow books (engine15/shadows.py), checked on planted bars. No network.

    py -3 -m pytest tests/test_shadows.py -q
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

LONG, SHORT = [0.1, 0.6, 0.3], [0.1, 0.3, 0.6]


# ------------------------------------------------------------------ planted inputs
def bars(n, price=100.0, wick=0.5):
    o = np.full(n, price)
    return {"open": o.copy(), "high": o + wick, "low": o - wick, "close": o.copy()}


def aux_for(n, atr15=1.0, atr1h=2.0, mas=None):
    aux = {"atr15": np.full(n, float(atr15)), "atr1h": np.full(n, float(atr1h)),
           "sw_lo": np.full(n, np.nan), "sw_hi": np.full(n, np.nan),
           "fib": dict((tf, {"dir": np.zeros(n), "broken": np.zeros(n), "0.5": np.full(n, np.nan),
                             "0.618": np.full(n, np.nan)}) for tf in shadows.PB_FIB_TFS),
           "ma": dict(("%s %s" % (tf, m), np.full(n, np.nan)) for tf in shadows.PB_MA_TFS for m in shadows.PB_MAS),
           "targets": pd.DataFrame(index=range(n))}
    for k, v in (mas or {}).items():
        aux["ma"][k][:] = v
    return aux


def go(px, odds, rule, aux=None, lo=1, hi=None, unit=2.0, cfg=None, state=None, **kw):
    n = len(px["close"])
    od = np.tile(np.asarray(odds, float), (n, 1)) if np.ndim(odds) == 1 else np.asarray(odds, float)
    return shadows.run(px, od, np.zeros(n, bool), np.zeros(n), np.full(n, float(unit)), cfg or CFG, lo,
                       hi or n, state=state, rule=rule, aux=aux or aux_for(n),
                       times_ms=np.arange(n, dtype="int64") * 900000, row_of=lambda k: pd.Series(dtype=float), **kw)


def random_inputs(n=900, seed=3):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.003, n)) * c
    px = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
    odds = rng.dirichlet(np.ones(3) * 25, size=n)
    odds[:5] = np.nan                                            # still learning at the start: WAIT
    unit = c * 0.004
    shock = rng.rand(n) < 0.05
    tide = rng.uniform(-1, 1, n)
    bias = rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.2, 0.6, 0.2])
    guard = rng.rand(n) < 0.03
    aux = aux_for(n, atr15=0.0, atr1h=0.0)
    aux["atr15"], aux["atr1h"] = c * 0.003, c * 0.006
    aux["sw_lo"], aux["sw_hi"] = c * (1 - rng.uniform(0, 0.01, n)), c * (1 + rng.uniform(0, 0.01, n))
    for tf in shadows.PB_FIB_TFS:
        aux["fib"][tf]["dir"] = rng.choice([-1.0, 0.0, 1.0], size=n)
        aux["fib"][tf]["0.5"] = c * (1 + rng.normal(0, 0.006, n))
        aux["fib"][tf]["0.618"] = c * (1 + rng.normal(0, 0.008, n))
    for k in aux["ma"]:
        aux["ma"][k] = c * (1 + rng.normal(0, 0.008, n))
    aux["targets"] = pd.DataFrame({"reach_24h_med_pct": rng.uniform(0.5, 2.0, n)})
    return px, odds, unit, shock, tide, bias, guard, aux


def run_random(rule, inp, lo=1, hi=None, state=None, cfg=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    return shadows.run(px, odds, shock, tide, unit, cfg or CFG, lo, hi or n, state=state, bias=bias, guard=guard,
                       rule=rule, aux=aux, times_ms=np.arange(n, dtype="int64") * 900000,
                       row_of=lambda k: aux["targets"].iloc[k])


COMPARE = ["i_out", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty", "pnl_usd", "fees_usd"]


# ------------------------------------------------------------------ the main book is untouched
def test_run_book_is_unchanged_on_a_fixed_slice():
    """backtest.run_book itself, pinned: the same trades as when the challengers were added."""
    px, odds, unit, shock, tide, bias, guard, _ = random_inputs()
    b = backtest.run_book(px, odds, shock, tide, unit, CFG, 1, len(odds), bias=bias, guard=guard)
    tr = b["trades"]
    closed = tr[tr.why_out != "OPEN"]
    assert len(closed) == PINNED["trades"]
    assert round(float(closed.pnl_usd.sum()), 6) == PINNED["pnl_usd"]
    assert round(b["state"]["eq"], 6) == PINNED["eq"]
    assert int((closed.why_out == "STOP").sum()) == PINNED["stops"]


PINNED = {"trades": 257, "pnl_usd": -4980.8954, "eq": 5019.1046, "stops": 93}    # v5 run_book, 11 Nov 2026


def test_shadow_engine_without_rules_is_run_book_exactly():
    inp = random_inputs()
    px, odds, unit, shock, tide, bias, guard, _ = inp
    n = len(odds)
    ref = backtest.run_book(px, odds, shock, tide, unit, CFG, 1, n, bias=bias, guard=guard)
    mine = run_random({}, inp)
    closed = ref["trades"][ref["trades"].why_out != "OPEN"].reset_index(drop=True)
    assert len(closed) > 20
    pd.testing.assert_frame_equal(closed[COMPARE], mine["trades"][COMPARE], check_dtype=False, rtol=0, atol=0)
    assert np.array_equal(ref["equity"][1:], mine["equity"][1:])
    assert np.array_equal(ref["held"], mine["held"])
    for k in ("pos", "idle", "qty", "entry", "stop", "eq", "why_in", "pending", "fees"):
        assert ref["state"][k] == mine["state"][k], k
    # and resumed across a cut, both ways
    a = backtest.run_book(px, odds, shock, tide, unit, CFG, 1, 500, bias=bias, guard=guard)
    b = backtest.run_book(px, odds, shock, tide, unit, CFG, 500, n, state=a["state"], bias=bias, guard=guard)
    m1 = run_random({}, inp, hi=500)
    m2 = run_random({}, inp, lo=500, state=m1["state"])
    assert b["state"]["eq"] == m2["state"]["eq"] == ref["state"]["eq"]


# ------------------------------------------------------------------ no look-ahead, every challenger
@pytest.mark.parametrize("name", list(shadows.CHALLENGERS))
def test_no_challenger_reads_the_future(name):
    """Scramble everything after bar k: every session up to k (equity, side held, trades closed by k)
    must come out exactly the same."""
    rule = shadows.CHALLENGERS[name]["rule"]
    cfg = dict(CFG, **shadows.CHALLENGERS[name]["cfg"])
    inp = random_inputs(seed=11)
    whole = run_random(rule, inp, cfg=cfg)
    for k in (300, 611, 850):
        rng = np.random.RandomState(k)
        px, odds, unit, shock, tide, bias, guard, aux = [_copy(x) for x in inp]
        f = slice(k + 1, None)
        m = len(odds) - k - 1
        for key in px:
            px[key][f] = px[key][f] * rng.uniform(0.9, 1.1, m)
        odds[f] = rng.dirichlet(np.ones(3), size=m)
        unit[f], tide[f], bias[f] = unit[f] * 3, -tide[f], -bias[f]
        shock[f], guard[f] = ~shock[f], ~guard[f]
        for key in ("atr15", "atr1h", "sw_lo", "sw_hi"):
            aux[key][f] = aux[key][f] * rng.uniform(0.5, 1.5, m)
        for tf in aux["fib"]:
            for key in aux["fib"][tf]:
                aux["fib"][tf][key][f] = -aux["fib"][tf][key][f] if key == "dir" else aux["fib"][tf][key][f] * 0.99
        for key in aux["ma"]:
            aux["ma"][key][f] = aux["ma"][key][f] * 1.01
        aux["targets"].iloc[k + 1:] = 9.0
        cut = run_random(rule, (px, odds, unit, shock, tide, bias, guard, aux), cfg=cfg)
        assert np.array_equal(whole["equity"][1:k + 1], cut["equity"][1:k + 1]), (name, k)
        assert np.array_equal(whole["held"][:k + 1], cut["held"][:k + 1]), (name, k)
        w, c = whole["trades"], cut["trades"]
        pd.testing.assert_frame_equal(w[w.i_out <= k].reset_index(drop=True), c[c.i_out <= k].reset_index(drop=True))


def _copy(x):
    if isinstance(x, dict):
        return dict((k, _copy(v)) for k, v in x.items())
    if isinstance(x, pd.DataFrame):
        return x.copy()
    return np.array(x, copy=True)


@pytest.mark.parametrize("name", list(shadows.CHALLENGERS))
def test_every_challenger_resumes_exactly(name):
    rule = shadows.CHALLENGERS[name]["rule"]
    cfg = dict(CFG, **shadows.CHALLENGERS[name]["cfg"])
    inp = random_inputs(seed=5)
    whole = run_random(rule, inp, cfg=cfg)
    for cut in (237, 640):
        a = run_random(rule, inp, hi=cut, cfg=cfg)
        b = run_random(rule, inp, lo=cut, state=a["state"], cfg=cfg)
        joined = pd.concat([a["trades"], b["trades"]], ignore_index=True)
        cols = [c for c in shadows.TRADE_COLS if c not in ("i_in",)]
        pd.testing.assert_frame_equal(whole["trades"][cols], joined[cols])
        assert np.array_equal(whole["equity"][cut:], b["equity"][cut:])
        assert whole["state"]["eq"] == b["state"]["eq"]


# ------------------------------------------------------------------ b_targets
def _targets_row(k):
    return pd.Series({"reach_24h_med_pct": np.nan})               # no reach, no Fib leg: 1.5R and 2R-style targets


def test_targets_half_at_t1_rest_at_t2():
    px = up_after(bars(20), 5)                                   # entry 100 at bar 2, stop 96 (R = 4)
    px["high"][5] = 106.5                                        # Target 1 = 106 (1.5R)
    px["high"][7] = 109.5                                        # Target 2 = 100 + max(2R, 1.5 x 6) = 109
    b = _go_t(px)
    t = b["trades"].iloc[0]
    assert t.why_out == "T1+T2" and t.p_in == 100.0 and t.i_out == 7
    assert t.target_1 == pytest.approx(106.0) and t.target_2 == pytest.approx(109.0)
    fees = 0.001 * 50 * (100 + 106) + 0.001 * 50 * (100 + 109)
    assert t.pnl_usd == pytest.approx(50 * 6 + 50 * 9 - fees)
    assert t.fees_usd == pytest.approx(fees)
    assert t.p_out == pytest.approx(107.5)
    assert t.r_mult == pytest.approx(t.pnl_usd / 400.0)


def up_after(px, k, price=105.0):
    """From bar k on, the market trades around `price` (above the entry, so break-even is not touched)."""
    for key, d in (("open", 0.0), ("close", 0.0), ("high", 0.5), ("low", -0.5)):
        px[key][k:] = price + d
    return px


def _go_t(px, **kw):
    n = len(px["close"])
    od = np.tile(np.asarray(LONG, float), (n, 1))
    return shadows.run(px, od, np.zeros(n, bool), np.zeros(n), np.full(n, 2.0), CFG, 1, n, rule={"targets": True},
                       aux=aux_for(n), times_ms=np.arange(n, dtype="int64") * 900000, row_of=_targets_row, **kw)


def test_targets_break_even_stop_after_t1():
    px = up_after(bars(20), 5)
    px["high"][5] = 106.5                                        # Target 1
    px["low"][8] = 99.0                                          # back through the entry: stopped at break-even
    t = _go_t(px)["trades"].iloc[0]
    assert t.why_out == "T1+STOP_BE" and t.i_out == 8
    assert t.pnl_usd == pytest.approx(50 * 6 - 0.001 * 50 * 206 - 0.001 * 50 * 200)


def test_stop_comes_before_a_target_in_the_same_bar():
    px = bars(20)
    px["high"][5], px["low"][5] = 107.0, 95.0                    # stop 96 and Target 1 in one bar
    t = _go_t(px)["trades"].iloc[0]
    assert t.why_out == "STOP" and t.p_out == 96.0 and t.i_out == 5


def test_break_even_is_live_only_from_the_next_bar():
    px = up_after(bars(20), 3)
    px["high"][2] = 106.5                                        # Target 1 in the entry bar itself (low 99.5 < entry)
    b = _go_t(px)
    assert b["state"]["t1_hit"] and b["state"]["pos"] == 1 and b["state"]["stop"] == 100.0


# ------------------------------------------------------------------ b_trail
def test_trail_after_one_r():
    px = bars(20)                                                # entry 100, stop 96, R = 4; ATR15 = 1
    px["high"][5], px["close"][5] = 104.5, 104.0                 # 1R reached: trail = max(104 - 2, swing 101) = 102
    px["open"][6] = 104.0
    px["low"][6] = 101.5                                         # through 102
    aux = aux_for(20)
    aux["sw_lo"][:] = 101.0
    b = go(px, LONG, {"trail": True}, aux=aux)
    t = b["trades"].iloc[0]
    assert t.why_out == "TRAIL" and t.p_out == 102.0 and t.i_out == 6


def test_trail_uses_the_tighter_of_swing_and_atr():
    px = bars(20)
    px["high"][5], px["close"][5] = 104.5, 104.0
    aux = aux_for(20)
    aux["sw_lo"][:] = 103.0                                      # the swing is tighter than 104 - 2
    b = go(px, LONG, {"trail": True}, aux=aux, hi=6)
    assert b["state"]["stop"] == 103.0 and b["state"]["trail_on"]


def test_trail_waits_for_one_r():
    px = bars(20)
    px["high"][5], px["close"][5] = 103.5, 103.0                 # under 1R: the first stop stays
    b = go(px, LONG, {"trail": True}, hi=6)
    assert b["state"]["stop"] == 96.0 and not b["state"]["trail_on"]


# ------------------------------------------------------------------ h3_flip_limit
def _flip_odds(n, k):
    od = np.tile(np.asarray(LONG, float), (n, 1))
    od[k:] = SHORT                                               # the flip is decided at the close of bar k
    return od


def test_flip_limit_filled():
    n, k = 20, 6
    px = bars(n, wick=0.4)                                       # limit = open 100 + 0.25 x ATR15 2 = 100.5
    px["high"][k + 2] = 100.6                                    # trades through on the second bar
    b = go(px, _flip_odds(n, k), {"flip_limit": True}, aux=aux_for(n, atr15=2.0))
    t = b["trades"].iloc[0]
    assert t.side == 1 and t.why_out == "FLIP_LMT" and t.p_out == pytest.approx(100.5) and t.i_out == k + 2
    assert b["state"]["pos"] == -1 and b["state"]["entry"] == 100.0       # the new side entered at market


def test_flip_limit_not_filled_then_market():
    n, k = 20, 6
    px = bars(n, wick=0.5)                                       # high 100.5 only touches: never fills
    px["open"][k + 5] = 99.0                                     # the market exit after 4 bars, at this open
    px["high"][k + 5], px["low"][k + 5] = 99.5, 98.5
    b = go(px, _flip_odds(n, k), {"flip_limit": True}, aux=aux_for(n, atr15=2.0))
    t = b["trades"].iloc[0]
    assert t.why_out == "FLIP_MKT" and t.p_out == 99.0 and t.i_out == k + 5


def test_flip_limit_stop_still_live():
    n, k = 20, 6
    px = bars(n)
    px["low"][k + 2] = 95.0                                      # the old long's stop (96) while its limit rests
    b = go(px, _flip_odds(n, k), {"flip_limit": True}, aux=aux_for(n, atr15=2.0))
    t = b["trades"].iloc[0]
    assert t.why_out == "STOP" and t.p_out == 96.0 and t.i_out == k + 2


# ------------------------------------------------------------------ a_pullback
def test_pullback_limit_filled():
    px = bars(20)                                                # decision at bar 1's close; 15m EMA 20 at 99
    px["low"][3] = 98.9
    b = go(px, LONG, {"pullback": True}, aux=aux_for(20, mas={"15m ema20": 99.0}))
    st = b["state"]
    assert st["pos"] == 1 and st["entry"] == 99.0 and st["why_in"] == policy.ENTER + "_LMT"
    assert st["stop"] == 95.0 and b["held"][2] == 0 and b["held"][3] == 1


def test_pullback_not_filled_then_market_and_never_idle():
    px = bars(20)                                                # lows 99.5 never trade through 99
    od = np.tile(np.asarray([0.34, 0.33, 0.33], float), (20, 1))  # no edge: the mandate forces after 4 idle bars
    b = go(px, od, {"pullback": True}, aux=aux_for(20, mas={"15m ema20": 99.0}), hi=16, cfg=dict(CFG, htf_bias=False))
    st = b["state"]
    # idle at bars 1-4, FORCED at bar 5's close, the limit rests bars 6-13, market at bar 14's open
    assert st["pos"] == 1 and st["why_in"] == policy.FORCED + "_MKT" and b["held"][13] == 0 and b["held"][14] == 1
    assert st["idle"] == 0


def test_pullback_ignores_levels_beyond_one_atr():
    px = bars(20)
    b = go(px, LONG, {"pullback": True}, aux=aux_for(20, mas={"15m ema20": 97.0}), hi=4)   # 3 away, ATR(1h) = 2
    assert b["state"]["pos"] == 1 and b["state"]["why_in"] == policy.ENTER and b["held"][2] == 1


def test_pullback_uses_only_a_fib_leg_running_the_trade_way():
    n = 20
    aux = aux_for(n)
    aux["fib"]["1h"]["dir"][:] = -1.0                            # a down-leg: no long entry from it
    aux["fib"]["1h"]["0.5"][:] = 99.2
    assert shadows.pullback_limit(aux, 1, 1, 100.0) is None
    aux["fib"]["1h"]["dir"][:] = 1.0
    assert shadows.pullback_limit(aux, 1, 1, 100.0) == (99.2, "Fib 1h 0.5")
    aux["fib"]["1h"]["broken"][:] = 1.0                          # retraced beyond 0.786: no longer a zone
    assert shadows.pullback_limit(aux, 1, 1, 100.0) is None


# ------------------------------------------------------------------ the forward step: two calls = one long call
def fake_prep(n=700, seed=9):
    px, odds, unit, shock, tide, bias, guard, aux = random_inputs(n=n, seed=seed)
    times = pd.date_range("2026-11-01", periods=n, freq="15min", tz="UTC")
    ev = pd.DataFrame({"shock": shock, "tide": tide, "atr1h": unit / CFG["barrier_atr"], "atr15": aux["atr15"],
                       "htf_bias": bias, "release_soon": guard, "sw_lo_15m": aux["sw_lo"], "sw_hi_15m": aux["sw_hi"],
                       "fib_1h_dir": aux["fib"]["1h"]["dir"], "fib_1h_broken": aux["fib"]["1h"]["broken"],
                       "fib_1h_r500_px": aux["fib"]["1h"]["0.5"], "fib_1h_entry_px": aux["fib"]["1h"]["0.618"],
                       "ma_15m_ema20_px": aux["ma"]["15m ema20"], "reach_24h_med_pct": aux["targets"]["reach_24h_med_pct"]},
                      index=times)
    return {"cfg": dict(CFG), "times": times, "px": {"BTCUSDT": px}, "odds": {"BTCUSDT": odds}, "ev": {"BTCUSDT": ev}}


def test_two_steps_equal_one_long_step(tmp_path):
    prep = fake_prep()
    one = {"version": 1, "groups": {}, "books": {}}
    two = {"version": 1, "groups": {}, "books": {}}
    _v, c_one = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, one, start_lo=100)
    _v, c_a = shadows.advance(prep, "crypto", ["BTCUSDT"], 420, two, start_lo=100)
    view, c_b = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, two)
    assert one["books"] == two["books"]
    for name in shadows.CHALLENGERS:
        key = (name, "BTCUSDT")
        parts = [x[key] for x in (c_a, c_b) if key in x]
        joined = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=shadows.TRADE_COLS)
        cols = [c for c in shadows.TRADE_COLS if c != "i_in"]
        if key in c_one:
            pd.testing.assert_frame_equal(c_one[key][cols].reset_index(drop=True), joined[cols], check_dtype=False)
        else:
            assert not len(joined)
    assert set(view["books"]) == set(shadows.CHALLENGERS) | set(shadows.FOLLOWERS)
    # through the files: state written atomically, trades journaled, a third step with nothing new is a no-op
    path = str(tmp_path / "shadow_state.json")
    shadows.save_state(two, path)
    again = shadows.load_state(path)
    assert again["books"] == two["books"]
    view2 = shadows.step(prep, "crypto", ["BTCUSDT"], 700, path=path, out_dir=str(tmp_path), log=lambda *_: None)
    assert shadows.load_state(path)["books"] == two["books"]
    board = shadows.scoreboard({"crypto": view2})
    assert [r["book"] for r in board["rows"]] == list(shadows.CHALLENGERS) + list(shadows.FOLLOWERS)
    assert board["buy_and_hold"]["assets"] == 1


def test_journal_and_page_view(tmp_path):
    prep = fake_prep()
    path = str(tmp_path / "s.json")
    st = {"version": 1, "groups": {}, "books": {}}
    shadows.advance(prep, "crypto", ["BTCUSDT"], 101, st, start_lo=100)
    shadows.save_state(st, path)
    shadows.step(prep, "crypto", ["BTCUSDT"], 700, path=path, out_dir=str(tmp_path), log=lambda *_: None)
    files = [f for f in os.listdir(tmp_path) if f.startswith("shadow_trades_")]
    assert files
    d = pd.read_csv(tmp_path / files[0])
    assert {"time_in", "time_out", "pnl_usd", "r_mult"} <= set(d.columns)
    v = shadows.asset_view(shadows.load_state(path)["books"]["main"]["BTCUSDT"])
    assert v["status"] in ("LONG", "SHORT", "FLAT") and "equity" in v


def test_page_block_merges_every_market():
    from engine15 import export
    prep = fake_prep()
    views = {}
    for g in ("crypto", "fx"):
        st = {"version": 1, "groups": {}, "books": {}}
        views[g], _ = shadows.advance(prep, g, ["BTCUSDT"], 700, st, start_lo=100)
    views["fx"]["assets"] = {"USDJPY": views["fx"]["assets"].pop("BTCUSDT")}
    for b in views["fx"]["books"].values():
        b["assets"] = {"USDJPY": b["assets"].pop("BTCUSDT")}
    learn = {"right": 1, "wrong": 1, "neither": 0, "edge_calls": 0, "edge_right": 0}
    frag = lambda g, a, v: {"assets": {a: {}}, "shadows": v, "learning": {"trust": {}, "last_7_days": learn,   # noqa: E731
                                                                           "last_30_days": learn}}
    page = export.merge({"crypto": frag("crypto", "BTCUSDT", views["crypto"]), "fx": frag("fx", "USDJPY", views["fx"])},
                        ["crypto", "metals", "fx", "index"])
    blk = page["shadows"]
    assert set(blk["books"]["main"]["assets"]) == {"BTCUSDT", "USDJPY"}
    row = [r for r in blk["scoreboard"]["rows"] if r["book"] == "b_trail"][0]
    assert row["assets"] == 2 and row["equity"] == pytest.approx(sum(
        v["books"]["b_trail"]["assets"][a]["equity"] for v in views.values() for a in v["assets"]))
    assert blk["scoreboard"]["buy_and_hold"]["assets"] == 2
    assert len(json.dumps(blk)) < 30000


def test_yardstick_decides_only_at_4h_closes():
    import numpy as np
    from engine15 import shadows, labels
    from engine15.config import CFG
    n = 64
    t0 = 1794268800000                                           # a UTC midnight bar open
    times_ms = np.array([t0 + i * 900000 for i in range(n)], dtype="int64")
    c = 100.0 + np.cumsum(np.full(n, 0.01))
    px = {"open": c, "high": c + 0.05, "low": c - 0.05, "close": c}
    odds = np.tile([0.2, 0.6, 0.2], (n, 1))                     # a strong UP edge every session
    odds[:, labels.NEITHER], odds[:, labels.UP], odds[:, labels.DOWN] = 0.2, 0.6, 0.2
    r = shadows.run(px, odds, np.zeros(n, bool), np.zeros(n), np.full(n, 0.5), dict(CFG), 1, n,
                    rule={"every_ms": 4 * 3600000}, times_ms=times_ms)
    first_long = int(np.argmax(r["held"] == 1))
    # the first 4h close is the bar opening at 03:45 (index 15): the fill is at the next open (index 16)
    assert first_long == 16


def test_h5_odds_shape():
    import numpy as np, pandas as pd
    from engine15 import shadows, model
    V = len(model.VOICE_NAMES); n = 5
    probs = np.full((n, V, 3), 1 / 3.0)
    k = list(model.VOICE_NAMES).index("strategies")
    probs[:, k] = [0.2, 0.2, 0.6]                                # strategies leans DOWN
    X = np.ones((n, max(max(c) for c in model._COLS.values() if c) + 1))
    ev = pd.DataFrame({"ms_1h": [1.0] * n, "ms_4h": [1.0] * n})  # structure up on 1h and 4h: against it
    prep = {"times": pd.RangeIndex(n), "probs": {"A": probs}, "trust": np.full((n, V), 1.0 / V), "X": {"A": X},
            "ev": {"A": ev}, "odds": {"A": model.mix(probs, np.full((n, V), 1.0 / V))}}
    o = shadows.h5_odds(prep, "A")
    assert o.shape == (n, 3) and (o[:, 2] < prep["odds"]["A"][:, 2]).all()   # less DOWN once damped


# ------------------------------------------------------------------ H36: moving-average trails, break-even after Target 1
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research"))
import exit_study  # noqa: E402

EMA15 = {"ma_trail": "15m ema20", "ma_arm": "entry"}


def _ma_aux(n, ma):
    aux = aux_for(n)
    aux["ma"]["15m ema20"] = np.asarray(ma, float) if np.ndim(ma) else np.full(n, float(ma))
    return aux


def _go_r(px, rule, aux=None, hi=None, odds=LONG):
    """A book with planted targets (Target 1 = 1.5R = 106 for a long from 100 with its stop at 96)."""
    n = len(px["close"])
    od = np.tile(np.asarray(odds, float), (n, 1))
    return shadows.run(px, od, np.zeros(n, bool), np.zeros(n), np.full(n, 2.0), CFG, 1, hi or n, rule=rule,
                       aux=aux or aux_for(n), times_ms=np.arange(n, dtype="int64") * 900000, row_of=_targets_row)


def test_ma_trail_exit_at_the_next_open():
    px = bars(20)                                                # long from bar 2's open at 100, stop 96
    px["close"][6], px["low"][6] = 98.8, 98.5                    # bar 6 CLOSES under the EMA (99)
    px["open"][7] = 98.7
    b = go(px, LONG, EMA15, aux=_ma_aux(20, 99.0))
    t = b["trades"].iloc[0]
    assert t.why_out == "TRAIL_MA" and t.i_out == 7 and t.p_out == 98.7 and t.p_in == 100.0
    assert b["held"][7] == 0 and b["held"][8] == 1               # flat after it; the normal rules re-enter


def test_ma_trail_a_wick_through_is_not_an_exit():
    px = bars(20)
    px["low"][6] = 98.0                                          # trades under the EMA but closes above it
    b = go(px, LONG, EMA15, aux=_ma_aux(20, 99.0))
    assert not len(b["trades"]) and b["state"]["pos"] == 1


def test_ma_trail_reads_only_bars_up_to_the_close():
    """The MA of bar t+1 (unknown at t's close) cannot cause an exit decided at t."""
    px = bars(20)
    ma = np.full(20, 99.0)
    ma[7:] = 100.5                                               # above the closes only from bar 7
    t = go(px, LONG, EMA15, aux=_ma_aux(20, ma))["trades"].iloc[0]
    assert t.i_out == 8 and t.why_out == "TRAIL_MA"              # decided at bar 7's close, filled at bar 8's open
    cut = go(px, LONG, EMA15, aux=_ma_aux(20, ma), hi=8)
    assert cut["state"]["pos"] == 1 and cut["state"]["pending"][0] == "TRAIL_MA"
    early = go(px, LONG, EMA15, aux=_ma_aux(20, ma), hi=7)       # through bar 6: nothing decided yet
    assert early["state"]["pos"] == 1 and early["state"]["pending"] is None


def test_ma_trail_never_loosens():
    px = bars(20)
    ma = np.full(20, 99.0)
    ma[5], ma[6:] = 99.8, 98.0                                   # the average rises to 99.8, then falls away
    px["close"][7], px["low"][7] = 99.5, 99.4                    # above today's average, below the ratchet
    b = go(px, LONG, EMA15, aux=_ma_aux(20, ma), hi=7)
    assert b["state"]["trail_px"] == pytest.approx(99.8) and b["state"]["ma_on"]
    t = go(px, LONG, EMA15, aux=_ma_aux(20, ma))["trades"].iloc[0]
    assert t.why_out == "TRAIL_MA" and t.i_out == 8


def test_ma_trail_short_side():
    px = bars(20)
    px["close"][6], px["high"][6] = 101.2, 101.5                 # a short closes ABOVE its EMA (101)
    px["open"][7] = 101.3
    t = go(px, SHORT, EMA15, aux=_ma_aux(20, 101.0))["trades"].iloc[0]
    assert t.side == -1 and t.why_out == "TRAIL_MA" and t.i_out == 7 and t.p_out == 101.3


def test_fixed_stop_still_honoured_under_an_ma_trail():
    px = bars(20)
    px["low"][6], px["close"][6] = 95.5, 98.0                    # through the 96 stop inside the bar
    t = go(px, LONG, EMA15, aux=_ma_aux(20, 99.0))["trades"].iloc[0]
    assert t.why_out == "STOP" and t.p_out == 96.0 and t.i_out == 6


def test_ma_trail_looser_than_the_stop_does_not_act():
    px = bars(20)
    b = go(px, LONG, EMA15, aux=_ma_aux(20, 90.0), hi=8)         # the average far under the 96 stop
    assert b["state"]["pos"] == 1 and not len(b["trades"])
    assert b["state"]["stop"] == 96.0                            # the protective stop itself never moves


def test_ma_trail_armed_only_after_one_r():
    px = bars(20)                                                # closes of 100 under an average at 101: not armed
    rule = {"ma_trail": "15m ema20", "ma_arm": "1r"}
    b = go(px, LONG, rule, aux=_ma_aux(20, 101.0), hi=5)
    assert b["state"]["pos"] == 1 and not b["state"]["ma_on"] and b["state"]["trail_px"] is None
    px["high"][5] = 104.5                                        # 1R (4) in favour: armed at bar 5's close
    t = go(px, LONG, rule, aux=_ma_aux(20, 101.0))["trades"].iloc[0]
    assert t.why_out == "TRAIL_MA" and t.i_out == 6


def test_ma_trail_armed_after_target_1():
    px = bars(20)
    rule = {"ma_trail": "15m ema20", "ma_arm": "t1"}
    b = _go_r(px, rule, aux=_ma_aux(20, 101.0), hi=6)
    assert b["state"]["pos"] == 1 and not b["state"]["ma_on"] and b["state"]["t1"] == pytest.approx(106.0)
    px["high"][5] = 106.5                                        # Target 1 trades in bar 5: armed at its close
    t = _go_r(px, rule, aux=_ma_aux(20, 101.0))["trades"].iloc[0]
    assert t.why_out == "TRAIL_MA" and t.i_out == 6


def test_break_even_after_target_1_only():
    px = up_after(bars(20), 5)
    px["high"][5] = 106.5                                        # Target 1 (1.5R = 106)
    px["low"][8] = 99.0                                          # back through the entry
    t = _go_r(px, {"be_t1": True})["trades"].iloc[0]
    assert t.why_out == "STOP_BE" and t.i_out == 8 and t.p_out == 100.0 and t.qty == pytest.approx(100.0)
    assert t.pnl_usd == pytest.approx(-0.001 * 100 * 200)        # the whole position out at entry: fees only
    v = _go_r(px, {"be_t1": True}, hi=6)["state"]
    assert v["stop"] == 100.0 and v["t1_hit"]
    view = shadows.asset_view(dict(v, mark=105.0))
    assert view["stop"] == 100.0 and view["stop_basis"].startswith("break-even") and view["target_1"] == 106.0
    before = shadows.asset_view(dict(_go_r(px, {"be_t1": True}, hi=5)["state"], mark=100.0))
    assert before["stop"] == 96.0 and before["stop_basis"].startswith("the entry stop")


def test_break_even_live_only_from_the_next_bar():
    px = up_after(bars(20), 3)
    px["high"][2] = 106.5                                        # Target 1 inside the entry bar (its low 99.5 < entry)
    b = _go_r(px, {"be_t1": True})
    assert b["state"]["pos"] == 1 and b["state"]["stop"] == 100.0 and not len(b["trades"])


def test_break_even_stop_comes_before_target_in_one_bar():
    px = bars(20)
    px["high"][5], px["low"][5] = 107.0, 95.0                    # the 96 stop and Target 1 in one bar
    t = _go_r(px, {"be_t1": True})["trades"].iloc[0]
    assert t.why_out == "STOP" and t.p_out == 96.0 and t.i_out == 5


def test_half_at_target_1_then_trail():
    px = up_after(bars(20), 5)
    px["high"][5] = 106.5                                        # half off at 106
    px["close"][9], px["low"][9] = 103.5, 103.4                  # then a close under the average (104)
    px["open"][10] = 103.6
    rule = {"ma_trail": "15m ema20", "ma_arm": "t1", "half_t1": True}
    t = _go_r(px, rule, aux=_ma_aux(20, 104.0))["trades"].iloc[0]
    assert t.why_out == "T1+TRAIL_MA" and t.i_out == 10 and t.qty == pytest.approx(100.0)
    fees = 0.001 * 50 * (100 + 106) + 0.001 * 50 * (100 + 103.6)
    assert t.pnl_usd == pytest.approx(50 * 6 + 50 * 3.6 - fees)


def test_page_view_exposes_the_trail():
    px = bars(20)
    b = go(px, LONG, EMA15, aux=_ma_aux(20, 99.0), hi=6)
    v = shadows.asset_view(dict(b["state"], mark=100.0))
    assert v["trail_basis"] == "EMA20 on 15m" and v["trail_armed"] and v["trail_price"] == 99.0
    assert v["trail_arm"] == "from entry" and v["stop"] == 96.0
    assert shadows.ma_basis("1h sma20") == "SMA20 on 1h"


def test_the_frozen_grid_is_fifteen_variants():
    assert len(exit_study.VARIANTS) == 15 and len(set(k for k, _ in exit_study.VARIANTS)) == 15
    grid = [r for _k, r in exit_study.VARIANTS]
    for name, spec in shadows.CHALLENGERS.items():
        r = dict((k, v) for k, v in spec["rule"].items() if k in ("ma_trail", "ma_arm", "be_t1", "half_t1"))
        if r:                                                    # every H36 shadow book is a frozen grid variant, unchanged
            assert spec["rule"] in grid, name


@pytest.mark.parametrize("name", [k for k, _ in exit_study.VARIANTS])
def test_no_h36_variant_reads_the_future(name):
    rule = dict(exit_study.VARIANTS)[name]
    inp = random_inputs(seed=17)
    whole = run_random(rule, inp)
    assert len(whole["trades"]) > 10
    for k in (333, 702):
        rng = np.random.RandomState(k)
        px, odds, unit, shock, tide, bias, guard, aux = [_copy(x) for x in inp]
        f = slice(k + 1, None)
        m = len(odds) - k - 1
        for key in px:
            px[key][f] = px[key][f] * rng.uniform(0.9, 1.1, m)
        odds[f] = rng.dirichlet(np.ones(3), size=m)
        unit[f], tide[f], bias[f] = unit[f] * 3, -tide[f], -bias[f]
        for key in aux["ma"]:
            aux["ma"][key][f] = aux["ma"][key][f] * rng.uniform(0.95, 1.05, m)
        aux["targets"].iloc[k + 1:] = 9.0
        cut = run_random(rule, (px, odds, unit, shock, tide, bias, guard, aux))
        assert np.array_equal(whole["equity"][1:k + 1], cut["equity"][1:k + 1]), (name, k)
        w, c = whole["trades"], cut["trades"]
        pd.testing.assert_frame_equal(w[w.i_out <= k].reset_index(drop=True), c[c.i_out <= k].reset_index(drop=True))


@pytest.mark.parametrize("name", [k for k, _ in exit_study.VARIANTS])
def test_every_h36_variant_resumes_exactly(name):
    rule = dict(exit_study.VARIANTS)[name]
    inp = random_inputs(seed=23)
    whole = run_random(rule, inp)
    for cut in (241, 655):
        a = run_random(rule, inp, hi=cut)
        b = run_random(rule, inp, lo=cut, state=json.loads(json.dumps(a["state"])))
        joined = pd.concat([a["trades"], b["trades"]], ignore_index=True)
        cols = [c for c in shadows.TRADE_COLS if c not in ("i_in",)]
        pd.testing.assert_frame_equal(whole["trades"][cols], joined[cols])
        assert whole["state"]["eq"] == b["state"]["eq"]


def test_h36_trail_exits_fill_at_the_next_open_on_random_bars():
    inp = random_inputs(seed=29)
    px = inp[0]
    for name in ("ema20_15m_1r", "sma20_1h_entry", "half_ema20_1h_t1"):
        tr = run_random(dict(exit_study.VARIANTS)[name], inp)["trades"]
        assert tr.why_out.str.endswith("TRAIL_MA").any(), name
        for _, t in tr[tr.why_out == "TRAIL_MA"].iterrows():       # (a "T1+TRAIL_MA" p_out averages both fills)
            assert t.p_out == px["open"][int(t.i_out)]


def test_exits_ma_trail_step_is_pure_and_ratchets():
    """engine15/exits.py, the function a v5.2 main book would share: state in, state out."""
    from engine15 import exits
    nan = float("nan")
    # long from 100, stop 96: not armed under 1R, armed at 1R, level ratchets up, never down, exit on a close under it
    assert exits.ma_trail_step(1, 100.0, 96.0, 96.0, False, None, "1r", False, 103.0, 99.0, 102.0, 101.0) == (False, None, False)
    st = exits.ma_trail_step(1, 100.0, 96.0, 96.0, False, None, "1r", False, 104.0, 99.0, 103.0, 101.0)
    assert st == (True, 101.0, False)
    st = exits.ma_trail_step(1, 100.0, 96.0, 96.0, st[0], st[1], "1r", False, 104.0, 102.0, 103.0, 102.5)
    assert st == (True, 102.5, False)
    st = exits.ma_trail_step(1, 100.0, 96.0, 96.0, st[0], st[1], "1r", False, 103.0, 101.0, 102.0, 99.0)
    assert st == (True, 102.5, True)                             # the average fell; the level did not
    assert exits.ma_trail_step(1, 100.0, 96.0, 96.0, True, 102.5, "1r", False, 103, 102, 103.0, nan) == (True, 102.5, False)
    # short: mirror image; a level beyond the stop does not act
    assert exits.ma_trail_step(-1, 100.0, 104.0, 104.0, False, None, "entry", False, 101, 99, 100.5, 100.2) == (True, 100.2, True)
    assert exits.ma_trail_step(-1, 100.0, 104.0, 104.0, True, None, "entry", False, 101, 99, 100.5, 105.0) == (True, 105.0, False)
    assert exits.ma_trail_step(1, 100.0, 96.0, 96.0, False, None, "t1", True, 100, 99, 99.0, 99.5)[0] is True
    assert exits.be_stop(1, 100.0, 96.0) == 100.0 and exits.be_stop(1, 100.0, 101.0) == 101.0
    assert exits.be_stop(-1, 100.0, 104.0) == 100.0 and exits.reached(-1, 101, 97, 97.5)


@pytest.mark.parametrize("name", ["ema20_15m_1r", "sma20_1h_entry", "be_ema20_1h_1r", "be_t1"])
def test_trail_from_history_matches_the_book(name):
    """The v5.2 migration helper rebuilds an open trade's trail exactly as the book that held it from entry."""
    from engine15 import exits
    rule = dict(exit_study.VARIANTS)[name]
    inp = random_inputs(seed=31)
    px, aux = inp[0], inp[7]
    for hi in (150, 400, 777):
        st = run_random(rule, inp, hi=hi)["state"]
        if not st["pos"] or st["pending"]:
            continue
        i_in = int(np.searchsorted(np.arange(len(px["close"])) * 900000, st["t_in_ms"]))
        key = rule.get("ma_trail")
        r = exits.trail_from_history(st["pos"], st["entry"], st["stop0"], st["t1"], rule.get("ma_arm") if key else None,
                                     px["high"], px["low"], px["close"], aux["ma"][key] if key else None,
                                     i_in, hi - 1, be_t1=bool(rule.get("be_t1")))
        assert r["exit_row"] is None
        assert r["stop"] == st["stop"] and r["t1_hit"] == st["t1_hit"]
        if key:
            assert r["armed"] == st["ma_on"] and r["level"] == st["trail_px"]


def test_a_book_added_later_starts_flat_and_is_compared_over_its_own_time():
    """A new challenger (the H36 books on the live loop's restart) joins a running group: it starts flat at the
    next session, the older books are untouched, and the scoreboard compares it with main since it started."""
    prep = fake_prep()
    st = {"version": 1, "groups": {}, "books": {}}
    shadows.advance(prep, "crypto", ["BTCUSDT"], 420, st, start_lo=100)
    ref = json.loads(json.dumps(st))
    main_then = st["books"]["main"]["BTCUSDT"]["equity_marked"]
    st["books"].pop("b_be_t1")                                   # as if it did not exist before this restart
    view, _ = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, st)
    full, _ = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, ref)
    assert st["books"]["main"] == ref["books"]["main"]           # the others go on exactly as before
    ls = st["late_starts"]["b_be_t1"]["BTCUSDT"]
    assert ls["main_eq"] == main_then
    alone = shadows.run_challenger("b_be_t1", prep, "BTCUSDT", 420, 700)
    assert st["books"]["b_be_t1"]["BTCUSDT"]["eq"] == alone["state"]["eq"]
    board = shadows.scoreboard({"crypto": view})
    row = [r for r in board["rows"] if r["book"] == "b_be_t1"][0]
    main_now = view["books"]["main"]["assets"]["BTCUSDT"]["equity"]
    assert row["since_utc"] == ls["utc"]
    assert row["vs_main_usd"] == pytest.approx(row["pnl_usd"] - (main_now - ls["main_eq"]), abs=0.02)
    assert "since_utc" not in [r for r in board["rows"] if r["book"] == "b_trail"][0]


# ------------------------------------------------------------------ held_share (20 Nov 2026)
def test_the_view_publishes_the_share_still_held():
    px = up_after(bars(20), 5)                                   # entry 100 at bar 2, Target 1 = 106, Target 2 = 109
    def upto(hi):
        n = len(px["close"])
        return shadows.run(px, np.tile(np.asarray(LONG, float), (n, 1)), np.zeros(n, bool), np.zeros(n), np.full(n, 2.0),
                           CFG, 1, hi, rule={"targets": True}, aux=aux_for(n),
                           times_ms=np.arange(n, dtype="int64") * 900000, row_of=_targets_row)["state"]

    before = upto(5)
    assert shadows.held_share(before) == 1.0 and shadows.asset_view(dict(before, mark=105.0))["held_share"] == 1.0
    px["high"][5] = 106.5                                        # Target 1 trades: half is closed
    after = upto(7)
    assert after["t1_hit"] and after["qty"] == pytest.approx(after["qty0"] * shadows.PART)
    assert shadows.held_share(after) == 0.5 and shadows.asset_view(dict(after, mark=106.0))["held_share"] == 0.5
    px["high"][7] = 109.5                                        # Target 2: flat, nothing held, nothing published
    flat = upto(8)
    assert flat["pos"] == 0 and shadows.held_share(flat) is None and "held_share" not in shadows.asset_view(flat)
    for bad in (None, {}, {"pos": 1, "qty": 1.0}, {"pos": 1, "qty": 2.0, "qty0": 1.0}, {"pos": 1, "qty": 0.0, "qty0": 1.0},
                {"pos": 1, "qty": "1", "qty0": 1.0}, {"pos": 0, "qty": 1.0, "qty0": 1.0}):
        assert shadows.held_share(bad) is None


def test_one_constant_for_the_share_closed_at_target_1():
    from engine15 import exits, signals, vault_feed
    assert shadows.PART == signals.PART == vault_feed.REDUCE_FRACTION == exits.PART == 0.5
    for mod, name in ((shadows, "shadows.py"), (signals, "signals.py"), (vault_feed, "vault_feed.py")):
        with open(os.path.join(os.path.dirname(shadows.__file__), name), encoding="utf-8") as fh:
            src = fh.read()
        assert "= exits.PART" in src and "PART = 0.5" not in src and "REDUCE_FRACTION = 0.5" not in src, name
