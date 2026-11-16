# -*- coding: utf-8 -*-
"""H45 daily-break study: the signal function never reads the future, the event is the registered one, and the
minimal simulator keeps the playbook frame (next open, stop first, gaps at the open, per-trade time exit)."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import dailybreak_study as db  # noqa: E402
from engine15 import data  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 80, seed=7, gaps=False):
    rng = np.random.RandomState(seed)
    ret = rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if gaps:                                                       # a market that shuts: keep 13:30-20:00 UTC
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 810) & (m < 1200)]
    return df


def test_signals_never_read_the_future():
    for gaps in (False, True):
        df = bars(gaps=gaps)
        n = len(df)
        full_R = adr.readings(df, box=db.BOX)
        for v, var in db.ALL.items():
            full = db.sig_key(db.signals(full_R, var))
            assert full, (v, gaps)
            for cut in (int(n * 0.5) + 3, int(n * 0.8) + 11, n - 2):
                part = db.sig_key(db.signals(adr.readings(df.iloc[:cut], box=db.BOX), var))
                assert part == [x for x in full if x[0] < cut], (v, gaps, cut)


def test_event_is_first_close_beyond_by_hand():
    df = bars()
    R = adr.readings(df, box=db.BOX)
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    day = R["ms"] // db.DAY_MS
    for level in ("pday", "roll24"):
        ev = db.daily_breaks(R, level, False)
        evm = db.daily_breaks(R, level, True)
        seen = {}
        for i in range(len(df)):
            if level == "pday":
                prev = np.flatnonzero(day == day[i] - 1)
                hi, lo = (h[prev].max(), l[prev].min()) if len(prev) else (np.nan, np.nan)
            else:
                hi, lo = (h[i - 96:i].max(), l[i - 96:i].min()) if i >= 96 else (np.nan, np.nan)
            want = 0
            if c[i] > hi and not seen.get((day[i], 1)):
                want, seen[(day[i], 1)] = 1, True
            elif c[i] < lo and not seen.get((day[i], -1)):
                want, seen[(day[i], -1)] = -1, True
            assert ev[i] == want, (level, i)
            mom = R["tr"][i] >= 1.5 * R["atr15"][i - 1] if i else False
            assert evm[i] == (want if mom else 0), (level, i)


def test_filter_and_twin():
    df = bars()
    R = adr.readings(df, box=db.BOX)
    for v in db.VARIANTS:
        room = db.signals(R, db.ALL[v])
        none = db.signals(R, db.ALL[db.TWIN_OF[v]])
        assert all(s["used"] < 0.65 for s in room)
        assert set(s["i_dec"] for s in room) <= set(s["i_dec"] for s in none)
    mom = set(s["i_dec"] for s in db.signals(R, db.ALL["D1n"]))
    every = set(s["i_dec"] for s in db.signals(R, db.ALL["D3n"]))
    assert mom <= every and len(mom) < len(every)


def _R(o, h, l, c, start="2025-03-03 22:00"):
    idx = pd.date_range(start, periods=len(o), freq="15min", tz="UTC")
    ms = np.asarray(data.to_ms(idx), dtype=np.int64)
    return {"n": len(o), "o": np.array(o, float), "h": np.array(h, float), "l": np.array(l, float),
            "c": np.array(c, float), "ms": ms}


def _sig(i, side=1, datr=10.0, level=100.0, room=108.0):
    return {"i_dec": i, "side": side, "level": level, "datr": datr, "used": 0.3, "room_px": room, "close": 101.0, "bar_x": 2.0}


def test_simulator_frame():
    var = dict(db.VARIANTS["D1"])                    # S1 (0.5 dATR = 5), Troom, day end
    # bars from 22:00: 8 bars to 00:00 next day. Break at bar 0, entry bar 1 open 101 -> stop 96, target 108.
    o = [100, 101, 101, 101, 101, 101, 101, 101, 102, 102]
    h = [101, 102, 102, 102, 102, 102, 102, 102, 103, 103]
    l = [99, 100, 100, 100, 100, 100, 100, 100, 101, 101]
    c = [101, 101, 101, 101, 101, 101, 101, 101, 102, 102]
    t = db.simulate(_R(o, h, l, c), [_sig(0)], var, 0.0)[0]
    assert t["why_out"] == "TIME" and t["exit"] == 102 and t["exit_bar"] == 8      # next UTC day's first open
    # stop and target in one bar -> stop first
    h2, l2 = list(h), list(l)
    h2[3], l2[3] = 110, 95
    t = db.simulate(_R(o, h2, l2, c), [_sig(0)], var, 0.0)[0]
    assert t["why_out"] == "STOP" and t["exit"] == 96.0
    # an open beyond the stop fills at that open
    o3, h3, l3 = list(o), list(h), list(l)
    o3[4], h3[4], l3[4] = 94, 95, 93
    t = db.simulate(_R(o3, h3, l3, c), [_sig(0)], var, 0.0)[0]
    assert t["why_out"] == "STOP" and t["exit"] == 94
    # target reached
    h4 = list(h)
    h4[5] = 109
    t = db.simulate(_R(o, h4, l, c), [_sig(0)], var, 0.0)[0]
    assert t["why_out"] == "TARGET" and t["exit"] == 108.0
    # room nearer than 0.25 dATR -> target entry + 2.5
    t = db.simulate(_R(o, h4, l, c), [_sig(0, room=102.0)], var, 0.0)[0]
    assert t["target"] == 103.5
    # break on the day's last bar: entry would be the next day -> no trade
    assert db.simulate(_R(o, h, l, c), [_sig(7)], var, 0.0) == []
    # one position at a time: a second signal while the first is open is skipped
    tr = db.simulate(_R(o, h, l, c), [_sig(0), _sig(2)], var, 0.0)
    assert len(tr) == 1
    # S2 stop and 72 h exit
    var4 = dict(db.VARIANTS["D4"])
    t = db.simulate(_R(o, h, l, c), [_sig(0, level=100.0)], var4, 0.0)[0]
    assert t["stop"] == 97.5 and t["target"] == 111.0 and t["status"] == "OPEN"
