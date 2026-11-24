# -*- coding: utf-8 -*-
"""H116's level machine and trade walk on small made-up bars (no data files, no evidence store)."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))

import h107_capitulation_rebound as h107  # noqa: E402
import h116_retest_capitulation_low as h  # noqa: E402

N, K = 4000, 100          # bars; the trigger bar. The low (100.0) is made at bar K-4.
ATR = 1.0


def _fx(n=N):
    """Flat bars at 104 with a capitulation low of 100 at bar K-4 and rule A's onset at bar K."""
    t = pd.date_range("2022-01-01", periods=n, freq="15min", tz="UTC")
    c = np.full(n, 104.0)
    o, hi, lo = c.copy(), c + 0.2, c - 0.2
    lo[K - 4] = 100.0
    A = np.zeros(n, bool)
    A[K] = True
    fx = {"t": t, "o": o, "h": hi, "l": lo, "c": c, "atr1h": np.full(n, ATR), "A": A}
    return fx


def _done(fx):
    fx["low16"] = pd.Series(fx["l"]).rolling(16, min_periods=16).min().values
    return fx


def _bar(fx, j, low=None, high=None, close=None, open_=None):
    if low is not None:
        fx["l"][j] = low
    if high is not None:
        fx["h"][j] = high
    if close is not None:
        fx["c"][j] = close
    if open_ is not None:
        fx["o"][j] = open_


def _one(fx, **kw):
    levels, dup = h.machine(_done(fx), **kw)
    assert len(levels) == 1
    return levels[0]


def test_level_is_the_low_the_trigger_came_off():
    lv = _one(_fx())
    assert lv["L"] == 100.0 and lv["b"] == K - 4 and lv["k"] == K
    assert lv["state"] == "no_bounce" and lv["c1"] is None and lv["c2"] is None      # 104.2 is not 5% above 100


def test_c1_holds_the_low_and_buys_one_atr_off_the_retest_low():
    fx = _fx()
    _bar(fx, 200, high=105.5)                       # armed: 5% above L
    _bar(fx, 300, low=101.4, close=101.6)           # first touch (<= 101.5); close only 0.2 above the low
    _bar(fx, 301, low=100.6, close=101.0)           # lower retest low 100.6; close 0.4 above it
    _bar(fx, 302, low=101.0, close=101.7)           # close >= 100.6 + 1 ATR -> C1
    lv = _one(fx)
    assert lv["a"] == 200 and lv["f"] == 300 and lv["outcome"] == "HOLD"
    assert lv["c1"]["j"] == 302 and np.isclose(lv["c1"]["stop"], 100.0 - 0.5)          # the lower of L and 100.6, less 0.5 ATR
    assert lv["c2"] is None and lv["s"] is None
    _bar(fx, 400, low=99.0, close=100.5)            # a later sweep is not the first retest: still no C2
    assert _one(fx)["c2"] is None


def test_a_wick_under_the_low_gives_c2_at_once_and_c1_with_the_wick_as_stop():
    fx = _fx()
    _bar(fx, 200, high=105.5)
    _bar(fx, 300, low=99.5, close=100.3)            # touch, sweep and reclaim in one bar; 0.8 above the low: no C1 yet
    _bar(fx, 301, low=100.2, close=100.6)           # 1.1 above 99.5 -> C1
    lv = _one(fx)
    assert lv["s"] == 300 and lv["c2"]["j"] == 300 and np.isclose(lv["c2"]["stop"], 99.5 - 0.5)
    assert lv["c1"]["j"] == 301 and np.isclose(lv["c1"]["stop"], 99.5 - 0.5) and lv["outcome"] == "HOLD"


def test_a_close_below_the_low_ends_c1_and_c2_needs_the_reclaim_within_24_hours():
    fx = _fx()
    _bar(fx, 200, high=105.5)
    _bar(fx, 300, low=99.0, close=99.4)             # break
    for j in range(301, 395):
        _bar(fx, j, low=98.5, close=99.0, high=99.5)
    _bar(fx, 395, low=98.0, close=100.1, high=100.2)    # bar s+95: the last bar inside 24 hours
    lv = _one(fx)
    assert lv["outcome"] == "BREAK" and lv["broke"] == 300 and lv["c1"] is None
    assert lv["c2"]["j"] == 395 and np.isclose(lv["c2"]["stop"], 98.0 - 0.5)
    fx = _fx()
    _bar(fx, 200, high=105.5)
    _bar(fx, 300, low=99.0, close=99.4)
    for j in range(301, 396):
        _bar(fx, j, low=98.5, close=99.0, high=99.5)
    _bar(fx, 396, low=98.0, close=100.1, high=100.2)    # one bar too late
    lv = _one(fx)
    assert lv["c2"] is None and lv["c1"] is None and lv["outcome"] == "BREAK"


def test_a_level_undercut_before_the_bounce_is_dead_and_the_arming_bar_is_not_a_touch():
    fx = _fx()
    _bar(fx, 150, low=99.9)                         # undercut before any 5% bounce
    _bar(fx, 200, high=105.5)
    _bar(fx, 300, low=101.0, close=103.0)
    lv = _one(fx)
    assert lv["state"] == "undercut" and lv["f"] is None and lv["c1"] is None
    fx = _fx()
    _bar(fx, 200, high=105.5, low=101.0, close=103.0)   # arms and dips in the same bar: not a touch
    lv = _one(fx)
    assert lv["state"] == "armed_no_touch"
    _bar(fx, 201, low=101.49, close=103.0)          # inside the zone (within 1.5% of L); +1.5 ATR off the low -> C1 at once
    lv = _one(fx)
    assert lv["f"] == 201 and lv["c1"]["j"] == 201


def test_a_level_lives_30_days_and_the_same_low_makes_one_level():
    fx = _fx()
    _bar(fx, 200, high=105.5)
    last = K + 30 * 96                               # the last bar that opens within 30 days of the trigger bar
    _bar(fx, last + 1, low=101.0, close=103.0)
    assert _one(fx)["state"] == "armed_no_touch"
    _bar(fx, last, low=101.0, close=103.0)
    lv = _one(fx)
    assert lv["f"] == last and lv["c1"]["j"] == last
    fx = _fx()
    fx["A"][K + 3] = True                            # rule A fires again off the same low: no second level
    levels, dup = h.machine(_done(fx))
    assert len(levels) == 1 and dup == 1


def test_signals_do_not_change_when_later_bars_are_cut_off():
    rng = np.random.default_rng(7)
    n = 96 * 400
    t = pd.date_range("2021-01-01", periods=n, freq="15min", tz="UTC")
    step = rng.normal(0, 0.004, n)
    for k in range(96 * 45, n, 96 * 35):             # a crash of about 20% in a day, every 35 days
        step[k:k + 96] -= 0.0023
    c = 100 * np.exp(np.cumsum(step))
    o = np.concatenate([[c[0]], c[:-1]])
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
    df = pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": 1.0, "taker_buy": 0.5}, index=t)
    fund = pd.Series([0.0001], index=[t[0]])
    fx = h107.features(df, fund)
    levels, _ = h.machine(fx)
    full = h.signals_of(levels)
    assert len(levels) >= 5 and len(full) >= 3, (len(levels), len(full))
    cuts = sorted(set(s[1] for s in full)) + [int(x) for x in rng.integers(96 * 40, n, 15)]
    for j in cuts:
        g = h107.features(df.iloc[:j + 1], fund)
        got = h.signals_of(h.machine(g)[0])
        assert got == [s for s in full if s[1] <= j], j
        # and the machine told to stop at bar j on the full readings says the same
        assert h.signals_of(h.machine(fx, n=j + 1)[0]) == got, j


def _walk_fx(n=400, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    o = np.concatenate([[c[0]], c[:-1]])
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
    return {"o": o, "h": hi, "l": lo, "c": c, "atr1h": np.full(n, 0.6)}


def test_walk_with_a_swapped_stop_is_h107s_walk_and_the_bar_by_bar_walk():
    fx = _walk_fx()
    ks = np.arange(5, 200)
    a = h107.walk(fx, ks, 192)
    b = h.walk_stop(fx, ks, fx["o"][ks + 1] - h107.STOP_ATR * fx["atr1h"][ks], 192)
    assert np.allclose(a["r"], b["r"], atol=1e-12) and np.all(a["xbar"] == b["xbar"]) and np.all(a["how"] == b["how"])
    for stop_dist in (0.5, 1.3, 4.0):                # other stops: vectorised against the loop
        stops = fx["o"][ks + 1] - stop_dist
        w = h.walk_stop(fx, ks, stops, 192)
        loop = np.array([h.walk_loop_stop(fx, int(k), float(s), 192) for k, s in zip(ks, stops)])
        assert np.allclose(w["r"], loop, atol=1e-10)
        assert set(np.unique(w["how"])) <= {0, 1, 2, 3, 4}


def test_walk_by_hand_stop_then_target():
    n = 300
    c = np.full(n, 100.5)
    fx = {"o": c.copy(), "h": c + 0.1, "l": c - 0.1, "c": c.copy(), "atr1h": np.full(n, 1.0)}
    fx["o"][11] = 100.0                              # entry 100 at bar 11's open; every later bar sits at 100.5
    fx["l"][20] = 97.9                               # stop 98: stopped at 98
    w = h.walk_stop(fx, [10], [98.0], 192)
    assert w["how"][0] == 0 and np.isclose(w["r"][0], (-2.0 - h.FEE * (100 + 98)) / 2.0) and w["xbar"][0] == 20
    fx["l"][20] = 100.4
    fx["h"][30] = 102.0                              # Target 1 = 102: half out, the rest held to the 48-hour close at 100.5
    w = h.walk_stop(fx, [10], [98.0], 192)
    assert w["how"][0] == 3 and w["xbar"][0] == 10 + 192
    assert np.isclose(w["r"][0], (0.5 * 2.0 + 0.5 * 0.5 - h.FEE * (100 + 0.5 * 102 + 0.5 * 100.5)) / 2.0)
    fx["l"][40] = 99.95                              # after Target 1 the stop is the entry: the rest goes out at 100
    w = h.walk_stop(fx, [10], [98.0], 192)
    assert w["how"][0] == 1 and w["xbar"][0] == 40


def test_one_trade_at_a_time_and_a_trade_must_end_by_the_last_bar():
    fx = _fx()
    _bar(fx, 200, high=105.5)
    _bar(fx, 300, low=101.4, close=102.5)            # touch and C1 in one bar (1.1 above the low)
    fx = _done(fx)
    levels, _ = h.machine(fx)
    rows, sk = h.trades_of("BTCUSDT", fx, levels, "C1", N - 1)
    assert len(rows) == 1 and rows[0]["k"] == 300 and np.isclose(rows[0]["stop"], 99.5)
    r = rows[0]
    assert np.isclose(r["bounce_high"], 105.5) and np.isclose(r["zone_top"], 101.5)
    assert np.isclose(r["fall_pct"], (105.5 - 101.5) / 105.5 * 100)
    rows, sk = h.trades_of("BTCUSDT", fx, levels, "C1", 300 + 191)     # bar 300 + 192 does not exist: not taken
    assert rows == [] and sk["past_the_cut"] == 1
    assert h.trades_of("BTCUSDT", fx, levels, "C2", N - 1)[0] == []
