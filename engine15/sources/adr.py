# -*- coding: utf-8 -*-
"""adr -- the daily range budget ("eagle view" of the daily ATR on 15m) and 15m range breaks with momentum.

Owner, 16 Nov 2026: "see any pattern or any technical indicator can identify if the price range broke with momentum on
the average range ... With a confluence of eagle view of daily ATR on 15 minutes" -> hypothesis H44
(research/HYPOTHESES.md; study research/rangebreak_study.py). Reading-only card for every market.

  adr   Daily range budget and range breaks
        adr_used      today's high - low so far / the daily ATR(14) of the last CLOSED day; 0 = one full daily ATR
                      used, -1 = none used, +1 = twice (clipped)
        adr_room_up   room left upward in daily ATRs: 1 - (close - today's low) / daily ATR (clipped -1..+1)
        adr_room_dn   room left downward: 1 - (today's high - close) / daily ATR (clipped -1..+1)
        adr_pos       where the close sits in today's range: -1 = at the low, +1 = at the high
        adr_break     a 15m range break with momentum (H44's registered definition): a close beyond the high / low of
                      the previous BOX bars on a bar whose true range is >= MOM_K x ATR(14, 15m) as of the bar before;
                      +1 up / -1 down at the break, fading to 0 over FADE bars
        adr_bar       the last bar's true range in 15m ATRs (as of the bar before): log2, clipped -1..+1 (+1 = twice)

THE ONE RULE (tests/test_sources_adr.py): row i uses only what was known at the close of 15m bar i. The daily ATR is
computed on UTC daily bars and reaches a 15m row through data.htf_on_15 (closed days only), the value at each UTC day's first bar
(the last day closed before today began) is held for the whole day, so it changes only on the first bar after a
daily close. Nothing is fetched. It does not
vote; no reading is claimed to predict (H44 is a history test of exactly this reading).
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

BAR_MS, DAY_MS = 900000, 86400000
ATR_N = 14                 # Wilder ATR(14) on both the 15m and the daily bars
BOX = 24                   # the range: the previous 24 bars (6 hours)  [H44 V1 / V8 definition]
MOM_K = 1.5                # momentum: the break bar's true range >= 1.5 x ATR(14, 15m) of the bar before
ROOM_LEFT, EXHAUSTED = 0.65, 1.0   # H44 buckets on the share of the daily ATR used at the break
FADE = 8                   # a break fades to nothing in 8 bars (2 hours), as ltf.py's events
OR_BARS = 4                # the opening range: the first 4 bars of the UTC day on file (study use)

GROUPS = OrderedDict([("adr", ("Daily range budget and range breaks",
                               ["adr_used", "adr_room_up", "adr_room_dn", "adr_pos", "adr_break", "adr_bar"]))])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = ["adr_close", "adr_datr_px", "adr_atr15_px", "adr_day_high_px", "adr_day_low_px", "adr_used_x",
       "adr_room_up_x", "adr_room_dn_x", "adr_pos_pct", "adr_bar_x", "adr_box_high_px", "adr_box_low_px",
       "adr_break_dir", "adr_break_bars", "adr_break_used_x", "adr_break_close_px", "adr_break_atr15_px"]


def update(log=print):
    """Nothing to fetch: computed from the asset's own bars."""
    return {}


def _sh(x, d=1):
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if d < len(x):
        out[d:] = x[:len(x) - d]
    return out


def _ohlc_daily(b):
    agg = b.resample("1D", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def _clean(bars):
    b = bars[["open", "high", "low", "close"]].astype(float)
    if not b.index.is_monotonic_increasing or b.index.has_duplicates:
        b = b[~b.index.duplicated(keep="last")].sort_index()
    return b


def readings(bars, box=BOX):
    """15m bars -> dict of arrays on the bars' own rows, each known at the close of its row.

    o h l c ms, atr15 (incl. this bar), atr15_prev, tr, bar_x (tr / atr15_prev), datr (the last closed UTC day's ATR,
    held for the whole of today), day_high / day_low (today so far, this bar included), used, room_up, room_dn,
    pos, box_hi / box_lo (previous `box` bars), pdh / pdl (prior UTC day, known at the previous bar's close),
    or_hi / or_lo / or_count (the day's first OR_BARS bars; or_count = bars of the day so far, 1-based)."""
    b = _clean(bars)
    o, h, l, c = (b[k].values.astype(float) for k in ("open", "high", "low", "close"))
    ms = _data.to_ms(b.index)
    R = {"index": b.index, "n": len(c), "o": o, "h": h, "l": l, "c": c, "ms": ms}
    tr = _ind.true_range(b).values.astype(float)
    atr = _ind.atr_wilder(b, ATR_N).values.astype(float)
    R["tr"], R["atr15"], R["atr15_prev"] = tr, atr, _sh(atr)
    with np.errstate(divide="ignore", invalid="ignore"):
        R["bar_x"] = np.where(R["atr15_prev"] > 0, tr / R["atr15_prev"], np.nan)
    day = ms // DAY_MS
    g = pd.DataFrame({"h": h, "l": l}).groupby(day)
    dh, dl = g["h"].cummax().values, g["l"].cummin().values
    R["day_high"], R["day_low"] = dh, dl
    R["or_count"] = pd.Series(day).groupby(day).cumcount().values + 1
    first = R["or_count"] <= OR_BARS
    go = pd.DataFrame({"h": np.where(first, h, -np.inf), "l": np.where(first, l, np.inf)}).groupby(day)
    ohi, olo = go["h"].cummax().values, go["l"].cummin().values
    known = R["or_count"] >= OR_BARS
    R["or_hi"], R["or_lo"] = np.where(known, ohi, np.nan), np.where(known, olo, np.nan)
    if len(b):
        d1 = _ohlc_daily(b)
        dfr = pd.DataFrame({"atr": _ind.atr_wilder(d1, ATR_N), "high": d1["high"], "low": d1["low"]}, index=d1.index)
        on = _data.htf_on_15(b, "1D", dfr)
        # the value at the day's FIRST bar (the last day closed before today began), held for the whole UTC day
        first_of_day = on.groupby(day).transform("first")
        R["datr"] = first_of_day["atr"].values.astype(float)
        R["pdh"], R["pdl"] = first_of_day["high"].values.astype(float), first_of_day["low"].values.astype(float)
    else:
        R["datr"] = R["pdh"] = R["pdl"] = np.full(0, np.nan)
    datr = R["datr"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = np.isfinite(datr) & (datr > 0)
        R["used"] = np.where(ok, (dh - dl) / datr, np.nan)
        R["room_up"] = np.where(ok, 1.0 - (c - dl) / datr, np.nan)
        R["room_dn"] = np.where(ok, 1.0 - (dh - c) / datr, np.nan)
        span = dh - dl
        R["pos"] = np.where(span > 0, (c - dl) / np.where(span > 0, span, 1.0), 0.5)
    hs, ls = pd.Series(h), pd.Series(l)
    R["box_hi"] = _sh(hs.rolling(box, min_periods=box).max().values)
    R["box_lo"] = _sh(ls.rolling(box, min_periods=box).min().values)
    return R


def breaks(R, kind="box", k=MOM_K):
    """-> int array: +1 = a range break up with momentum at this bar's close, -1 = down, 0 = none.
    kind: 'box' (R's box_hi / box_lo), 'pday' (prior UTC day, first close beyond), 'or' (opening range, first close
    beyond, from the bar after the range is complete)."""
    c, cp = R["c"], _sh(R["c"])
    with np.errstate(invalid="ignore"):
        mom = R["bar_x"] >= k
        if kind == "box":
            up, dn = c > R["box_hi"], c < R["box_lo"]
        elif kind == "pday":
            up = (c > R["pdh"]) & (cp <= R["pdh"])
            dn = (c < R["pdl"]) & (cp >= R["pdl"])
        elif kind == "or":
            after = R["or_count"] > OR_BARS
            up = after & (c > R["or_hi"]) & (cp <= R["or_hi"])
            dn = after & (c < R["or_lo"]) & (cp >= R["or_lo"])
        else:
            raise ValueError(kind)
    return np.where(mom & up, 1, np.where(mom & dn, -1, 0)).astype(int)


def _since(event):
    """bars since the last True (0 on the event bar) and the row of that event (-1 = none yet)."""
    n = len(event)
    last = np.where(event, np.arange(n), -1)
    last = np.maximum.accumulate(last) if n else last
    age = np.where(last >= 0, np.arange(n) - last, np.nan)
    return age, last


def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    out = pd.DataFrame(index=index15)
    errors = {}
    for f in FEATURES + RAW:
        out[f] = np.nan
    try:
        b = _data.load(asset) if bars is None else bars
        b = _clean(b)
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    if b is not None and len(b):
        try:
            R = readings(b)
            br = breaks(R, "box", MOM_K)
            age, last = _since(br != 0)
            lk = np.maximum(last, 0)
            have = last >= 0
            bdir = np.where(have, br[lk], np.nan).astype(float)
            raw = pd.DataFrame({
                "adr_close": R["c"], "adr_datr_px": R["datr"], "adr_atr15_px": R["atr15"],
                "adr_day_high_px": R["day_high"], "adr_day_low_px": R["day_low"], "adr_used_x": R["used"],
                "adr_room_up_x": R["room_up"], "adr_room_dn_x": R["room_dn"], "adr_pos_pct": 100.0 * R["pos"],
                "adr_bar_x": R["bar_x"], "adr_box_high_px": R["box_hi"], "adr_box_low_px": R["box_lo"],
                "adr_break_dir": bdir, "adr_break_bars": age,
                "adr_break_used_x": np.where(have, R["used"][lk], np.nan),
                "adr_break_close_px": np.where(have, R["c"][lk], np.nan),
                "adr_break_atr15_px": np.where(have, R["atr15"][lk], np.nan)}, index=b.index)
            raw = raw.reindex(index15)
            for col in RAW:
                out[col] = raw[col].values
            with np.errstate(divide="ignore", invalid="ignore"):
                out["adr_used"] = (out["adr_used_x"] - 1.0).values
                out["adr_room_up"] = out["adr_room_up_x"].values
                out["adr_room_dn"] = out["adr_room_dn_x"].values
                pos = out["adr_pos_pct"].values / 100.0
                out["adr_pos"] = np.where(np.isfinite(out["adr_used_x"].values), 2.0 * pos - 1.0, np.nan)
                fade = np.clip(1.0 - out["adr_break_bars"].values / float(FADE), 0.0, 1.0)
                out["adr_break"] = np.nan_to_num(out["adr_break_dir"].values) * np.nan_to_num(fade)
                bx = out["adr_bar_x"].values
                out["adr_bar"] = np.where(bx > 0, np.log2(np.where(bx > 0, bx, 1.0)), np.nan)
        except Exception as ex:
            errors["adr"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
    out[FEATURES] = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-1.0, 1.0)
    out.attrs["errors"] = errors
    return out


def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _px(v):
    a = abs(v)
    return "{:,.0f}".format(v) if a >= 10000 else "{:,.1f}".format(v) if a >= 1000 else \
        "{:,.2f}".format(v) if a >= 100 else "{:,.3f}".format(v) if a >= 1 else "{:,.5f}".format(v)


def bucket(used):
    if used is None or used != used:
        return "no read"
    return "room left" if used < ROOM_LEFT else ("exhausted" if used >= EXHAUSTED else "middle")


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what is read; forecasts nothing."""
    title = GROUPS["adr"][0]
    datr, c = _num(row, "adr_datr_px"), _num(row, "adr_close")
    if datr is None or c is None or c <= 0:
        return OrderedDict([(title, "Daily range budget: no read (fewer than 14 closed days on file).")])
    used, up, dn = _num(row, "adr_used_x"), _num(row, "adr_room_up_x"), _num(row, "adr_room_dn_x")
    pos, bx = _num(row, "adr_pos_pct"), _num(row, "adr_bar_x")
    s = "Daily ATR(14) %s (%.2f%% of price); today has used %.0f%% of it (%s)" % (
        _px(datr), 100.0 * datr / c, 100.0 * (used or 0.0), bucket(used))
    if up is not None and dn is not None:
        s += "; room left %.2f daily ATR up, %.2f down" % (up, dn)
    if pos is not None:
        s += "; the close is %.0f%% of the way up today's range" % pos
    if bx is not None:
        s += "; the last bar spanned %.1fx the 15m ATR" % bx
    d, age = _num(row, "adr_break_dir"), _num(row, "adr_break_bars")
    if d is not None and age is not None and age < FADE:
        bu = _num(row, "adr_break_used_x")
        when = "on this bar" if age == 0 else ("%d bar%s ago" % (int(age), "" if age == 1 else "s"))
        s += ". Range break with momentum %s the %d-bar %s %s, when the day had used %.0f%% of its ATR (%s)" % (
            "UP above" if d > 0 else "DOWN below", BOX, "high" if d > 0 else "low", when, 100.0 * (bu or 0.0), bucket(bu))
    else:
        s += ". No range break with momentum in the last %d bars" % FADE
    return OrderedDict([(title, s + ".")])
