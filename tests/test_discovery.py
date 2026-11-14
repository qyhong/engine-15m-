# -*- coding: utf-8 -*-
"""Discovery tools (research/discovery_lib.py, state_map.py, surprises.py) on planted data.

    py -3 -m pytest tests/test_discovery.py -q
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import discovery_lib as L  # noqa: E402
import surprises as S  # noqa: E402

from engine15 import labels  # noqa: E402


def bars(n=12000, seed=1, start="2022-01-01"):
    rng = np.random.RandomState(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    opn = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                         "close": close, "volume": vol, "taker_buy": vol * rng.uniform(0.3, 0.7, n)},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def test_states_never_read_the_future():
    """Cut the data at bar k: every reading and state for bars <= k must stay exactly the same."""
    df = bars()
    funding = pd.Series(np.random.RandomState(4).normal(0, 1e-4, 200),
                        index=pd.date_range("2022-01-01", periods=200, freq="8h", tz="UTC"))
    events = np.array([pd.Timestamp("2022-02-10 13:30", tz="UTC").value // 10 ** 6,
                       pd.Timestamp("2022-03-10 13:30", tz="UTC").value // 10 ** 6], dtype="int64")
    full = L.readings(df, funding=funding, events_ms=events)
    half = np.zeros(len(df), dtype=bool)
    half[3000:7000] = True
    thr = L.fit_thresholds(full, half)
    st_full = L.states(full, thr)
    for cut in (4001, 7777, 9999, 11003):
        part = L.readings(df.iloc[:cut], funding=funding, events_ms=events)
        assert np.allclose(full.iloc[:cut].values, part.values, atol=1e-6, equal_nan=True), \
            "a reading changed when the future was cut at %d" % cut
        st_part = L.states(part, thr)
        assert (st_full.iloc[:cut].values == st_part.values).all(), "a state changed when cut at %d" % cut


def test_higher_timeframes_only_once_closed():
    """Change only the last 15m bar of a 4h bar: the 4h trend must not change on any earlier row."""
    df = bars(n=6000, seed=3)
    base = L.readings(df)
    df2 = df.copy()
    k = 5000 + (16 - (5000 % 16)) - 1           # the last 15m bar of some 4h bar
    df2.iloc[k, df2.columns.get_loc("close")] *= 1.05
    df2.iloc[k, df2.columns.get_loc("high")] = max(df2.iloc[k]["high"], df2.iloc[k]["close"])
    alt = L.readings(df2)
    assert np.allclose(base["trend4h"].values[:k], alt["trend4h"].values[:k], equal_nan=True)
    assert np.allclose(base["atr1h"].values[:k], alt["atr1h"].values[:k], equal_nan=True)


def test_outcomes_start_at_next_open():
    df = bars(n=300, seed=5)
    out = L.outcomes(df, np.full(len(df), 1.0))
    o, c = df["open"].values, df["close"].values
    t = 100
    assert np.isclose(out["f1"].values[t], (c[t + 1] / o[t + 1] - 1) * 100, atol=1e-4)
    assert np.isclose(out["f16"].values[t], (c[t + 16] / o[t + 1] - 1) * 100, atol=1e-4)
    assert np.isnan(out["f16"].values[-1]) and out["y96"].values[-1] == labels.UNKNOWN


def test_sessions():
    hours = np.array([0, 6, 7, 11, 12, 15, 16, 21, 22, 23, 10], dtype=float)
    dows = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 6], dtype=float)
    s = L.session_code(hours, dows)
    names = [L.SESSIONS[x] for x in s]
    assert names == ["Asia", "Asia", "London", "London", "London+NY overlap", "London+NY overlap",
                     "New York", "New York", "Asia", "Asia", "weekend"]


def test_group_stats_match_a_plain_groupby():
    rng = np.random.RandomState(7)
    n = 5000
    codes = rng.randint(-1, 4, n)
    y = rng.normal(0, 1, n)
    y[rng.rand(n) < 0.05] = np.nan
    pos = np.arange(n)
    cnt, neff, s, ss, up, dn = L.group_stats(codes, 4, y, pos, 16)
    mean, t = L.finish(cnt, neff, s, ss)
    med = L.group_medians(codes, 4, y)
    frame = pd.DataFrame({"c": codes, "y": y, "b": pos // 16}).dropna()
    frame = frame[frame.c >= 0]
    g = frame.groupby("c")
    assert (cnt == g.size().values).all()
    assert np.allclose(mean, g.y.mean().values)
    assert np.allclose(med, g.y.median().values)
    assert (up == g.y.apply(lambda v: (v > 0).sum()).values).all()
    assert (neff == g.b.nunique().values).all()
    assert (neff <= cnt).all()


def test_combo_codes_round_trip():
    st = {"vol": np.array([0, 2, 1, -1], dtype=np.int8), "session": np.array([4, 0, 3, 1], dtype=np.int8)}
    code, k = L.combo_codes(st, ("vol", "session"))
    assert k == 15 and code[3] == -1
    assert L.decode(("vol", "session"), int(code[0])) == [("vol", "quiet"), ("session", "weekend")]
    assert L.decode(("vol", "session"), int(code[2])) == [("vol", "normal"), ("session", "New York")]


def test_decluster_keeps_the_biggest_bar_of_each_move():
    m = np.zeros(200)
    m[50:54] = [3.0, 5.0, 4.0, 3.5]          # one move: keep bar 51
    m[120] = -6.0                            # another, far away
    keep = S.decluster(m, 2.5, 16, np.ones(200, dtype=bool))
    assert list(keep) == [51, 120]


def test_lift_table_counts():
    x = np.zeros(1000, dtype=bool)
    x[::10] = True                           # base rate 10%
    ok = np.ones(1000, dtype=bool)
    ev = np.arange(0, 400, 10)               # every surprise has the flag
    t = S.lift_table({"f": ("t", x, ok)}, {"H1": np.ones(1000, dtype=bool)}, {"H1": ev})
    r = t["f"]["H1"]
    assert r["k"] == 40 and r["n"] == 40 and abs(r["lift"] - 10.0) < 1e-9 and r["z"] > 5
