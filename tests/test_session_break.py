# -*- coding: utf-8 -*-
"""H48 session-break study: session ranges are complete before their event window, the event function never reads
the future (truncation on 24h and cash-hours bars), the event is the registered one (checked by hand), and the generic
outcome equals H46's for the 72 h case."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import session_break_study as sb  # noqa: E402
import confluence_study as cs  # noqa: E402
from engine15 import data, extdata  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 70, seed=11, cash=False, start="2025-02-10"):
    rng = np.random.RandomState(seed)
    ret = rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if cash:                                                   # the NYSE cash session, DST-aware (spans March DST)
        df = df[extdata.open_mask("SPX", df.index)]
    return df


def test_events_never_read_the_future():
    for cash in (False, True):
        df = bars(cash=cash)
        n = len(df)
        full_R = adr.readings(df, box=96)
        for v, var in sb.VARIANTS.items():
            if (var["kind"] == "or") != cash and var["kind"] != "daily":
                continue
            for tz in ((None, sb.LONDON) if v in sb.LOCAL_CHECK else (None,)):
                full = sb.event_key(full_R, var, tz)
                assert full, (v, cash, tz)
                for cut in (int(n * 0.4) + 5, int(n * 0.7) + 13, n - 3):
                    part = sb.event_key(adr.readings(df.iloc[:cut], box=96), var, tz)
                    assert part == [x for x in full if x[0] < cut], (v, cash, tz, cut)


def _by_hand(df, var, R):
    """Recompute the events from scratch, bar by bar, with only bars up to i."""
    ms = R["ms"]
    out = np.zeros(len(df), int)
    seen = set()
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    for i in range(len(df)):
        day = ms[i] // sb.DAY_MS
        sameday = np.flatnonzero((ms[:i + 1] // sb.DAY_MS) == day)
        if var["kind"] == "or":
            first = ms[sameday[0]]
            loc = extdata._local(pd.DatetimeIndex([pd.Timestamp(first, unit="ms", tz="UTC")]), sb.NY)[0]
            if loc.hour * 60 + loc.minute != 570:
                continue
            mins = (ms[sameday] - first) // 60000
        else:
            mins = (ms[sameday] % sb.DAY_MS) // 60000
        m_i = mins[-1]
        if not (var["window"][0] <= m_i < var["window"][1]):
            continue
        rr = sameday[(mins >= var["range"][0]) & (mins < var["range"][1])]
        if len(rr) < var["need"]:
            continue
        assert ms[rr].max() + sb.BAR_MS <= ms[i]          # the range closed before the event bar opened
        hi, lo = h[rr].max(), l[rr].min()
        if c[i] > hi and (day, 1) not in seen:
            out[i] = 1
            seen.add((day, 1))
        elif c[i] < lo and (day, -1) not in seen:
            out[i] = -1
            seen.add((day, -1))
    return out


def test_event_by_hand_and_windows():
    for cash, vids in ((False, ("B1", "B2", "B3")), (True, ("B4", "B5"))):
        df = bars(n=96 * 25, cash=cash)
        R = adr.readings(df, box=96)
        for v in vids:
            var = sb.VARIANTS[v]
            d, hi, lo, cnt = sb.session_events(R, var)
            want = _by_hand(df, var, R)
            assert (d == want).all(), v
            mins, _ = sb.clock(R, var)
            for i in np.flatnonzero(d != 0):
                assert var["window"][0] <= mins[i] < var["window"][1]
                assert cnt[i] >= var["need"]
            assert (d != 0).sum() > 5, v


def test_or_anchors_on_the_cash_open():
    df = bars(n=96 * 60, cash=True, start="2025-02-24")          # US DST starts 9 March 2025
    R = adr.readings(df, box=96)
    mins, day = sb.clock(R, sb.VARIANTS["B4"])
    idx = df.index
    zero = idx[mins == 0]
    assert set(zero[zero < "2025-03-08"].strftime("%H:%M")) == {"14:30"}
    assert set(zero[zero > "2025-03-10"].strftime("%H:%M")) == {"13:30"}


def test_outcome_matches_h46_for_72h():
    df = bars(n=96 * 20)
    R = adr.readings(df, box=96)
    var = sb.VARIANTS["A1"]
    d = sb.event_dirs(R, var)
    k = 0
    for i in np.flatnonzero(d != 0):
        D = R["datr"][i]
        if not (D == D and D > 0) or i + 1 >= R["n"]:
            continue
        a = cs.outcome(R, i, int(d[i]), float(D))
        b = sb.outcome_window(R, i, int(d[i]), float(D), sb.x_end_of(R, var, i), 0.5, "open")
        if a is None:
            assert b is None
            continue
        for key in ("e", "entry", "stop", "target", "hit", "ambiguous", "why", "exit", "exit_bar"):
            assert a[key] == b[key], (i, key)
        k += 1
    assert k > 5


def _R(o, h, l, c, start="2025-03-04 20:00"):
    idx = pd.date_range(start, periods=len(o), freq="15min", tz="UTC")
    return {"n": len(o), "o": np.array(o, float), "h": np.array(h, float), "l": np.array(l, float),
            "c": np.array(c, float), "ms": np.asarray(data.to_ms(idx), dtype=np.int64), "index": idx}


def test_outcome_same_day_frame():
    var = sb.VARIANTS["B2"]
    # 20:00 start: bars 0..15 are the 4 h to midnight; break at bar 0, entry bar 1 open 100, D = 10 -> +/- 5
    o = [100] * 18
    h = [101] * 18
    l = [99] * 18
    c = [100] * 15 + [101, 100, 100]
    R = _R(o, h, l, c)
    r = sb.outcome(R, var, 0, 1, 10.0)
    assert r["hit"] is None and r["why"] == "TIME" and r["exit"] == 101 and r["exit_bar"] == 15
    h2, l2 = list(h), list(l)
    h2[4], l2[4] = 106, 94                                     # both in one bar -> miss
    r = sb.outcome(_R(o, h2, l2, c), var, 0, 1, 10.0)
    assert r["hit"] == 0 and r["ambiguous"] and r["exit"] == 95.0
    h3 = list(h)
    h3[16] = 120                                               # next UTC day: outside the window
    assert sb.outcome(_R(o, h3, l, c), var, 0, 1, 10.0)["hit"] is None
    h4 = list(h)
    h4[6] = 103                                                # +0.25 D reached: secondary hit
    assert sb.outcome(_R(o, h4, l, c), var, 0, 1, 10.0, X=0.25)["hit"] == 1
    assert sb.outcome(_R(o, h, l, c), var, 15, 1, 10.0) is None  # entry would be the next UTC day


def test_trades_one_at_a_time_and_time_close_busy():
    var = sb.VARIANTS["B2"]
    o, h, l = [100] * 18, [101] * 18, [99] * 18
    c = [100] * 18
    R = _R(o, h, l, c)
    evs = []
    for i in (0, 3, 15):
        r = sb.outcome(R, var, i, 1, 10.0)
        if r is None:
            continue
        ev = {"i": i, "side": 1, "asset": "X", "half": "second", "entry_ms": int(R["ms"][r["e"]])}
        ev.update(r)
        evs.append(ev)
    tr = sb.trades_of(evs, 0.0)
    assert len(tr) == 1 and tr[0]["why_out"] == "TIME"
