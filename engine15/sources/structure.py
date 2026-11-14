# -*- coding: utf-8 -*-
"""structure -- read the market's structure, then name the setup it offers.

WHY (owner, 10 Nov 2026): "The important baseline and foundation is to equip the thought
process of the trading and accuracy in reading market structure and lead to high probability
trade setup and directional call."

THE STRUCTURE READER. On four timeframes (15m, 1h, 4h, 1d) the market is read from its
CONFIRMED swing points: a swing high is a bar whose high is the highest of the K bars either
side of it, and it is known only K bars later (never earlier). The last two swing highs and
the last two swing lows give the state:
    UPTREND    higher high AND higher low
    DOWNTREND  lower high AND lower low
    RANGE      anything else
and the last swing high and low are the two prices that matter: a close above the last swing
high is a BREAK UP, a close below the last swing low is a BREAK DOWN.

THE SETUP LIBRARY. Six named setups, each an exact rule on that structure, each either long
or short, evaluated at every 15-minute close. A setup FIRES on the first bar its rule is met.
    1 Trend pullback     the 4h trend is up, the 1h has pulled back 20-80% into its last
                         leg, and the 15m breaks up again -> long (mirror for short)
    2 Breakout           a 15m close through the last 1h swing high while the 1h and 4h are
                         not in a downtrend -> long (mirror)
    3 Breakout retest    after a break up, price comes back to the broken level, holds it and
                         closes up -> long (mirror)
    4 Failed breakout    after a break up, price closes back below the broken level -> short
                         (the trap; mirror)
    5 Range fade         4h and 1h are both ranging, price is in the bottom fifth of the 1h
                         range and the 15m breaks up -> long (top fifth, breaks down -> short)
    6 Trend failure      the 1h is in an uptrend and a 15m close breaks its last higher low
                         -> short (mirror: a downtrend's last lower high breaks -> long)
How often each setup was followed by the move it called is measured by
research/setup_stats.py and kept in research/setup_stats.json; that number, with its count,
is what "probability" means here. It describes the past and is not a promise.

Interface of engine15/sources: GROUPS, update, features, describe, facts.
"""
import json
import os
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data
from .. import indicators as ind
from ..config import ROOT

# ------------------------------------------------------------------ constants (declared once)
SWING_K = {"15m": 5, "1h": 3, "4h": 3, "1d": 2}     # bars either side that make a swing; conventional fractal sizes
PULLBACK_ZONE = (0.2, 0.8)       # a pullback has retraced 20% to 80% of the last 1h leg
RANGE_EDGE = 0.2                 # "the bottom / top fifth" of the 1h range
RETEST_BARS = 32                 # a retest must come within 8 hours of the break
RETEST_TOUCH_ATR = 0.3           # ... and reach within 0.3 x ATR(1h) of the broken level
TRAP_BARS = 12                   # a failed breakout is back inside within 3 hours
TRAP_MARGIN_ATR = 0.1            # ... by at least 0.1 x ATR(1h)
HOLD_BARS = 8                    # a fired setup stays "active" as a reading for 2 hours
SETUPS = ("pullback", "breakout", "retest", "trap", "rangefade", "failure")
SETUP_NAMES = {"pullback": "Trend pullback", "breakout": "Breakout", "retest": "Breakout retest",
               "trap": "Failed breakout", "rangefade": "Range fade", "failure": "Trend failure"}
STATS_JSON = os.path.join(ROOT, "research", "setup_stats.json")
STATE_WORDS = {1: "uptrend", -1: "downtrend", 0: "range"}

GROUPS = OrderedDict([
    ("structure", ("Market structure", ["ms_15m", "ms_1h", "ms_4h", "ms_1d", "ms_pos_1h", "ms_pos_4h", "ms_agree"])),
    ("setups", ("Trade setups", ["su_" + s for s in SETUPS])),
])


def update(log=print):
    return {}


def swings(high, low, k):
    """Confirmed swing structure of one timeframe. -> state (+1/0/-1), last swing high, last
    swing low, each as known at the CLOSE of every bar (a swing at bar j is used from j + k)."""
    n = len(high)
    win = 2 * k + 1
    ph = high == pd.Series(high).rolling(win, center=True).max().values
    pl = low == pd.Series(low).rolling(win, center=True).min().values
    state, last_hi, last_lo = np.zeros(n), np.full(n, np.nan), np.full(n, np.nan)
    h1 = h2 = l1 = l2 = np.nan
    for i in range(n):
        j = i - k
        if j >= k:                                   # the window around j is complete only now
            if ph[j]:
                h1, h2 = h2, high[j]
            if pl[j]:
                l1, l2 = l2, low[j]
        if h1 == h1 and l1 == l1:
            state[i] = 1.0 if (h2 > h1 and l2 > l1) else -1.0 if (h2 < h1 and l2 < l1) else 0.0
        last_hi[i], last_lo[i] = h2, l2
    return state, last_hi, last_lo


def _tf(df15, rule, k):
    """One higher timeframe's structure, joined onto the 15m rows without look-ahead."""
    bars = df15.resample(rule, label="left", closed="left").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    st, hi, lo = swings(bars["high"].values, bars["low"].values, k)
    out = pd.DataFrame({"state": st, "hi": hi, "lo": lo}, index=bars.index)
    return data.htf_on_15(df15, rule, out)


def features(index15, asset, bars=None):
    df = bars if bars is not None else data.load(asset)
    c, o, h, l = (df[x].values for x in ("close", "open", "high", "low"))
    n = len(c)
    out = pd.DataFrame(index=df.index)
    st15, hi15, lo15 = swings(h, l, SWING_K["15m"])
    out["ms_15m"], out["sw_hi_15m"], out["sw_lo_15m"] = st15, hi15, lo15
    for tf, rule in (("1h", "1h"), ("4h", "4h"), ("1d", "1D")):
        t = _tf(df, rule, SWING_K[tf])
        out["ms_" + tf] = t["state"].fillna(0.0).values
        out["sw_hi_" + tf], out["sw_lo_" + tf] = t["hi"].values, t["lo"].values
    h1 = df.resample("1h", label="left", closed="left").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    atr = data.htf_on_15(df, "1h", ind.atr_wilder(h1)).values
    for tf in ("1h", "4h"):
        span = out["sw_hi_" + tf] - out["sw_lo_" + tf]
        pos = (df["close"] - out["sw_lo_" + tf]) / span.where(span > 0)
        out["pos_" + tf] = pos                                   # 0 = at the last swing low, 1 = at the last swing high
        out["ms_pos_" + tf] = (2.0 * pos - 1.0).clip(-2, 2).fillna(0.0)
    out["ms_agree"] = out[["ms_15m", "ms_1h", "ms_4h", "ms_1d"]].mean(axis=1)

    # ---- breaks: the first 15m close beyond a level
    prev_c = np.concatenate([[np.nan], c[:-1]])

    def first_cross(level, up):
        """This bar closed beyond the level and the bar before had not (against the SAME level,
        so a level that merely moves past the price is not a break)."""
        with np.errstate(invalid="ignore"):
            return ((c > level) & (prev_c <= level)) if up else ((c < level) & (prev_c >= level))

    hi1, lo1 = out["sw_hi_1h"].values, out["sw_lo_1h"].values
    up15, dn15 = first_cross(hi15, True), first_cross(lo15, False)
    up1h, dn1h = first_cross(hi1, True), first_cross(lo1, False)
    s1, s4 = out["ms_1h"].values, out["ms_4h"].values
    p1 = out["pos_1h"].values
    ev = dict((s, np.zeros(n)) for s in SETUPS)
    inz = (p1 >= PULLBACK_ZONE[0]) & (p1 <= PULLBACK_ZONE[1])
    ev["pullback"][(s4 == 1) & (s1 >= 0) & inz & up15] = 1
    ev["pullback"][(s4 == -1) & (s1 <= 0) & inz & dn15] = -1
    ev["breakout"][up1h & (s1 >= 0) & (s4 >= 0)] = 1
    ev["breakout"][dn1h & (s1 <= 0) & (s4 <= 0)] = -1
    ev["rangefade"][(s4 == 0) & (s1 == 0) & (p1 < RANGE_EDGE) & up15] = 1
    ev["rangefade"][(s4 == 0) & (s1 == 0) & (p1 > 1 - RANGE_EDGE) & dn15] = -1
    ev["failure"][(s1 == 1) & dn1h] = -1
    ev["failure"][(s1 == -1) & up1h] = 1
    # retest and failed breakout follow a break of a 1h level
    lvl, side, age, tested = np.nan, 0, 0, False
    for i in range(n):
        if up1h[i] or dn1h[i]:
            lvl, side, age, tested = (hi1[i] if up1h[i] else lo1[i]), (1 if up1h[i] else -1), 0, False
            continue
        if side == 0 or not (atr[i] > 0):
            continue
        age += 1
        if side == 1:
            if age <= TRAP_BARS and c[i] < lvl - TRAP_MARGIN_ATR * atr[i]:
                ev["trap"][i], side = -1, 0
            elif not tested and age <= RETEST_BARS and l[i] <= lvl + RETEST_TOUCH_ATR * atr[i] and c[i] > lvl and c[i] > o[i]:
                ev["retest"][i], tested = 1, True
        else:
            if age <= TRAP_BARS and c[i] > lvl + TRAP_MARGIN_ATR * atr[i]:
                ev["trap"][i], side = 1, 0
            elif not tested and age <= RETEST_BARS and h[i] >= lvl - RETEST_TOUCH_ATR * atr[i] and c[i] < lvl and c[i] < o[i]:
                ev["retest"][i], tested = -1, True
        if age > RETEST_BARS:
            side = 0
    for s in SETUPS:
        e = pd.Series(ev[s], index=df.index)
        out["ev_" + s] = e                                          # the firing bar only (for grading)
        held = e.replace(0.0, np.nan).ffill(limit=HOLD_BARS - 1).fillna(0.0)
        out["su_" + s] = held                                       # the reading: active for HOLD_BARS
    return out.reindex(index15).assign(**dict((f, lambda d, f=f: d[f].fillna(0.0)) for g in GROUPS.values() for f in g[1]))


def _stats():
    try:
        with open(STATS_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _px(v):
    return "n/a" if v != v else ("{:,.0f}" if abs(v) >= 10000 else "{:,.2f}").format(v)


def active_setups(row):
    """[(setup key, +1 / -1)] for the setups whose reading is active on this row."""
    return [(s, int(row["su_" + s])) for s in SETUPS if row.get("su_" + s, 0) != 0]


def describe(row, asset):
    words = ", ".join("%s %s" % (tf, STATE_WORDS[int(row["ms_" + tf])]) for tf in ("1d", "4h", "1h", "15m"))
    act = active_setups(row)
    names = ", ".join("%s (%s)" % (SETUP_NAMES[s], "long" if d > 0 else "short") for s, d in act) or "no named setup"
    return {"Market structure": "Structure: %s." % words, "Trade setups": "Active now: %s." % names}


def facts(row, asset):
    st = _stats().get(asset, {})
    rows = [[tf, "%s (last swing high %s, low %s)" % (STATE_WORDS[int(row["ms_" + tf])].capitalize(),
                                                     _px(row["sw_hi_" + tf]), _px(row["sw_lo_" + tf]))]
            for tf in ("1d", "4h", "1h", "15m")]
    p = row["pos_1h"]
    rows.append(["Place in the last 1h leg", "n/a" if p != p else "%.0f%% of the way from its low to its high" % (p * 100)])
    setups = []
    for s, d in active_setups(row):
        side = "long" if d > 0 else "short"
        rec = (st.get(s) or {}).get(side)
        hist = "no graded history yet" if not rec else "in history right %.1f%% of %s times (%.1f%% / %.1f%% in the two halves)" % (
            rec["hit"], format(rec["n"], ","), rec["hit_first_half"], rec["hit_second_half"])
        setups.append([SETUP_NAMES[s] + ", " + side, hist])
    if not setups:
        setups = [["Active setup", "none: no named setup is present"]]
    return {"Market structure": rows, "Trade setups": setups}
