# -*- coding: utf-8 -*-
"""H49 exhaustion-fade study: the event function never reads the future, the running extreme and the share of the
daily ATR used come only from bars up to the event bar, the confirmation event is decided at the confirmation bar,
and the day-end outcome / fade trade keep the registered frame."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import exhaustion_study as ex  # noqa: E402
import session_break_study as sb  # noqa: E402
from engine15 import data  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 80, seed=11, gaps=False):
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


def _R(df):
    return adr.readings(df, box=96)


def test_events_never_read_the_future():
    for gaps in (False, True):
        df = bars(n=96 * (300 if gaps else 80), gaps=gaps)          # cash hours: more days for the rarer variants
        n = len(df)
        full_R = _R(df)
        for v, var in ex.VARIANTS.items():
            full = ex.event_key(ex.events(full_R, var))
            assert full, (v, gaps)
            for cut in (int(n * 0.5) + 3, int(n * 0.8) + 11, n - 2, n - 1):
                part = ex.event_key(ex.events(_R(df.iloc[:cut]), var))
                assert part == [x for x in full if x[0] < cut], (v, gaps, cut)


def test_event_by_hand():
    df = bars()
    R = _R(df)
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    day = R["ms"] // ex.DAY_MS
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[np.nan, c[:-1]]), np.abs(l - np.r_[np.nan, c[:-1]])))
    for v in ("X1", "X2", "X3", "X5"):
        var = ex.VARIANTS[v]
        got = dict((e["i"], e) for e in ex.events(R, var))
        seen = set()
        for i in range(1, len(df)):
            today = np.flatnonzero((day == day[i]) & (np.arange(len(df)) <= i))   # bars up to the event bar only
            dh, dl = h[today].max(), l[today].min()
            D = R["datr"][i]
            used = (dh - dl) / D if D > 0 else np.nan
            assert abs(used - R["used"][i]) < 1e-9 or not np.isfinite(D)
            earlier = today[today < i]
            if var["level"] == "run":
                if not len(earlier):
                    up = dn = False
                else:
                    up, dn = c[i] > h[earlier].max(), c[i] < l[earlier].min()
            else:
                prev = np.flatnonzero(day == day[i] - 1)
                if not len(prev):
                    up = dn = False
                else:
                    pdh, pdl = h[prev].max(), l[prev].min()
                    up = c[i] > pdh and c[i - 1] <= pdh
                    dn = c[i] < pdl and c[i - 1] >= pdl
            weak = tr[i] < var["K"] * R["atr15"][i - 1]
            ok = np.isfinite(used) and used >= var["U"] and weak
            want = 0
            if ok and up and (day[i], 1) not in seen:
                want = 1
                seen.add((day[i], 1))
            elif ok and dn and (day[i], -1) not in seen:
                want = -1
                seen.add((day[i], -1))
            assert (got[i]["side"] if i in got else 0) == want, (v, i)
            if want:
                assert got[i]["ext"] == (dh if want > 0 else dl)


def test_confirmation_decided_at_the_next_bar():
    df = bars()
    R = _R(df)
    base = ex.VARIANTS["X1"]
    conf = ex.VARIANTS["X4"]
    up, dn = ex.qualifying(R, base)
    day = R["ms"] // ex.DAY_MS
    c = R["c"]
    evs = ex.events(R, conf)
    assert evs
    for e in evs:
        i, p = e["i"], e["push"]
        assert p == i - 1 and day[p] == day[i]
        assert (up[p] and c[i] < c[p]) if e["side"] > 0 else (dn[p] and c[i] > c[p])
        assert e["used"] == R["used"][p]
    # every event of X4 is the first confirmed push of its day per direction
    keys = [(day[e["i"]], e["side"]) for e in evs]
    assert len(keys) == len(set(keys))


def _Rm(o, h, l, c, start="2025-03-03 22:00"):
    idx = pd.date_range(start, periods=len(o), freq="15min", tz="UTC")
    ms = np.asarray(data.to_ms(idx), dtype=np.int64)
    return {"n": len(o), "o": np.array(o, float), "h": np.array(h, float), "l": np.array(l, float),
            "c": np.array(c, float), "ms": ms}


def _ev(i=0, side=1, datr=10.0, ext=102.0, a15=2.0, mid=96.0):
    return {"i": i, "side": side, "datr": datr, "ext": ext, "a15": a15, "mid": mid}


def test_trade_and_outcome_frame():
    var = ex.VARIANTS["X1"]                               # stop ext + 0.25 ATR15 = 102.5, target entry - 5
    # bars from 22:00: 8 bars to the end of the day, then the next day. Up push at bar 0 -> fade SHORT at bar 1 open 101.
    o = [100, 101, 101, 101, 101, 101, 101, 101, 99, 99]
    h = [102, 102, 102, 102, 102, 102, 102, 102, 100, 100]
    l = [99, 100, 100, 100, 100, 100, 100, 100, 98, 98]
    c = [101, 101, 101, 101, 101, 101, 101, 100.5, 99, 99]
    R = _Rm(o, h, l, c)
    t = ex.trade(R, _ev(), var, 0.0)
    assert t["side"] == -1 and t["stop"] == 102.5 and t["target"] == 96.0
    assert t["why_out"] == "TIME" and t["exit"] == 100.5 and t["busy"] == 7        # close of the day's last bar
    assert abs(t["pnl_usd"] - 0.5 / 101 * 10000) < 1e-6
    # stop and target in one bar -> stop first
    h2, l2 = list(h), list(l)
    h2[3], l2[3] = 103, 95
    t = ex.trade(_Rm(o, h2, l2, c), _ev(), var, 0.0)
    assert t["why_out"] == "STOP" and t["exit"] == 102.5
    # an open beyond the stop fills at that open
    o3, h3 = list(o), list(h)
    o3[4], h3[4] = 104, 105
    t = ex.trade(_Rm(o3, h3, l, c), _ev(), var, 0.0)
    assert t["why_out"] == "STOP" and t["exit"] == 104
    # target reached
    l4 = list(l)
    l4[5] = 95.5
    t = ex.trade(_Rm(o, h, l4, c), _ev(), var, 0.0)
    assert t["why_out"] == "TARGET" and t["exit"] == 96.0
    # entry opening beyond the stop is not taken
    o5 = list(o)
    o5[1] = 103
    assert "skip" in ex.trade(_Rm(o5, h, l, c), _ev(), var, 0.0)
    # midpoint target with its floor (X7: stop ext + 0.25 D = 104.5)
    t = ex.trade(R, _ev(mid=100.0), ex.VARIANTS["X7"], 0.0)
    assert t["stop"] == 104.5 and t["target"] == 101 - 2.5                    # midpoint 100 nearer than 2.5 -> floor
    t = ex.trade(R, _ev(mid=95.0), ex.VARIANTS["X7"], 0.0)
    assert t["target"] == 95.0
    # an entry bar in the next UTC day -> no trade
    assert ex.trade(R, _ev(i=7), var, 0.0) is None
    # the day-end fade outcome uses only the event's day: a down move to 96 tomorrow is not a hit
    l6 = list(l)
    l6[8] = 90
    od = sb.outcome_window(_Rm(o, h, l6, c), 0, -1, 10.0, ex.day_end(_Rm(o, h, l6, c), 0), ex.X, "close")
    assert od["hit"] is None
    l7 = list(l)
    l7[6] = 95.9
    od = sb.outcome_window(_Rm(o, h, l7, c), 0, -1, 10.0, ex.day_end(_Rm(o, h, l7, c), 0), ex.X, "close")
    assert od["hit"] == 1


def test_one_position_per_market():
    t1 = {"why_out": "TIME", "busy": 7}
    evs = [{"i": 0, "asset": "A", "half": "first", "trade": t1},
           {"i": 5, "asset": "A", "half": "first", "trade": {"why_out": "STOP", "busy": 9}},
           {"i": 8, "asset": "A", "half": "first", "trade": {"why_out": "STOP", "busy": 10}},
           {"i": 12, "asset": "A", "half": "first", "trade": {"skip": "gap beyond stop"}}]
    got = ex.trades_of(evs)
    assert [g["busy"] for g in got] == [7, 10]
