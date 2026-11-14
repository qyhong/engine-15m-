# -*- coding: utf-8 -*-
"""trendtools -- three classic trend tools as READING cards, from the asset's own 15m bars.

Owner, 11 Nov 2026: Ichimoku, the Hull moving average and KAMA, "adding them as reading and studies,
unless it is helpful on direction prediction". They are ordinary voices; whether a voice votes is set
in config, and these start as readings only.

  ichimoku  Ichimoku cloud                         1h and 4h, standard 9 / 26 / 52
  hull      Hull moving average                    15m and 1h, lengths 9, 21, 55
  kama      Kaufman adaptive average (KAMA)        15m, 1h and 4h, efficiency ratio 10, fast 2, slow 30

ICHIMOKU WITHOUT LOOK-AHEAD. The cloud is drawn 26 bars to the right of the bar that computes it. So
the cloud that applies NOW (the one under today's candle on a chart) is the one computed 26 bars ago:
span A now = (Tenkan + Kijun) / 2 of 26 bars ago, span B now = (52-bar high + low) / 2 of 26 bars ago.
The cloud being computed at this close is the one drawn 26 bars AHEAD ("the cloud ahead"); it is
known now and shown as such. The lagging line (Chikou) is today's close drawn 26 bars back, so it is
read as: this close against the close of 26 bars ago. Nothing reads a future bar.

HULL. HMA(n) = WMA(2 x WMA(close, n // 2) - WMA(close, n), floor(sqrt(n))), WMA = linearly weighted
(TradingView's ta.hma with floor). A Hull line turns quickly; its turns are its main use.

KAMA. ER = |close - close 10 bars ago| / sum of the 10 absolute bar-to-bar changes (0 = chop, 1 = a
straight line); smoothing sc = (ER x (2/3 - 2/31) + 2/31)^2; KAMA = KAMA_prev + sc x (close - KAMA_prev),
seeded with the close of the first bar that has an ER. It flattens in chop by design, so its slope
labels the market "flat" or "trending".

THE ONE RULE. Higher timeframes reach a 15m row only once their bar has CLOSED (mavg.closed_positions,
the data.htf_on_15 lookup). tests/test_trendtools.py cuts the future off and checks every column.

UNITS. ATR = Wilder ATR(14) of the same timeframe. Features about [-1, 1], 0.0 = no read; readable
columns are prices, ATRs, ratios and ages in bars of their own timeframe (float32, NaN = no read).
No reading here is claimed to predict anything. Docs: docs/SOURCES_trendtools.md.
"""
import math
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind
from .mavg import (BAR_MS, DECIMALS, _ago, _bars, _gather, _hbars, _num, _px, _ratio, _shift,  # noqa: F401
                   _since, closed_positions)

# =====================================================================================
# THE ONE CONSTANT BLOCK. Conventional values, declared once, none tuned against outcomes.
# =====================================================================================
TFS = OrderedDict([("15m", None), ("1h", "1h"), ("4h", "4h")])
ATR_N = 14
ICH_TFS = ("1h", "4h")
TENKAN, KIJUN, SPAN_B, DISPLACE = 9, 26, 52, 26
HULL_TFS = ("15m", "1h")
HULL_LENGTHS = (9, 21, 55)
KAMA_TFS = ("15m", "1h", "4h")
KAMA_ER, KAMA_FAST, KAMA_SLOW = 10, 2, 30
KAMA_SLOPE_BARS = 3
KAMA_FLAT_ATR = 0.15             # KAMA moving less than 0.15 ATR over 3 bars = flat
EVENT_FADE = 8                   # a fresh Hull turn / cross fades to nothing over 8 bars
SCALE_KIJUN = 2.0                # tanh(ATRs / 2)
SCALE_CLOUD = 2.0
SCALE_LAG = 3.0
SCALE_TK = 1.0
SCALE_KAMA_POS = 2.0
SCALE_KAMA_SLOPE = 0.5
# =====================================================================================

GROUPS = OrderedDict([
    ("ichimoku", ("Ichimoku cloud",
                  ["ich_pos_1h", "ich_pos_4h", "ich_tk_1h", "ich_tk_4h", "ich_kijun_1h", "ich_kijun_4h",
                   "ich_cloud_1h", "ich_cloud_4h", "ich_lag_1h", "ich_lag_4h"])),
    ("hull", ("Hull moving average",
              ["hull_dir_15m", "hull_dir_1h", "hull_pos_15m", "hull_pos_1h", "hull_turn_15m", "hull_turn_1h",
               "hull_x_15m", "hull_x_1h"])),
    ("kama", ("Kaufman adaptive average (KAMA)",
              ["kama_er_15m", "kama_er_1h", "kama_er_4h", "kama_pos_15m", "kama_pos_1h", "kama_pos_4h",
               "kama_slope_15m", "kama_slope_1h", "kama_slope_4h"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
_RAW = OrderedDict([("shared", ["tt_close"] + ["tt_%s_atr" % t for t in TFS]), ("ichimoku", []), ("hull", []), ("kama", [])])
for _tf in ICH_TFS:
    _RAW["ichimoku"] += ["ich_%s_%s" % (_tf, s) for s in ("tenkan_px", "kijun_px", "span_a_px", "span_b_px",
                                                          "ahead_a_px", "ahead_b_px", "lag_ref_px", "tk_x_age", "tk_x_px")]
for _tf in HULL_TFS:
    for _n in HULL_LENGTHS:
        _RAW["hull"] += ["hull_%s_%d_%s" % (_tf, _n, s) for s in ("px", "slope", "turn_age")]
    _RAW["hull"] += ["hull_%s_x_age" % _tf, "hull_%s_x_px" % _tf]
for _tf in KAMA_TFS:
    _RAW["kama"] += ["kama_%s_%s" % (_tf, s) for s in ("px", "er", "slope", "state")]
RAW = [c for cols in _RAW.values() for c in cols]
"""ich_{tf}_tenkan/kijun_px; span_a/b_px = the cloud under the current bar (computed 26 bars ago);
ahead_a/b_px = the cloud computed now, drawn 26 bars ahead; lag_ref_px = the close 26 bars ago (what the
lagging line is compared with); tk_x_age / _px = bars since Tenkan crossed Kijun and the price there.
hull_{tf}_{n}_px / slope (change over 1 bar, in ATR) / turn_age (bars since the slope changed sign);
hull_{tf}_x_* = the 9/21 cross. kama_{tf}_px, er (0-1), slope (over 3 bars, in ATR), state (+1 trending
up, -1 trending down, 0 flat)."""


def update(log=print):
    """Nothing to fetch: every reading comes from the 15m bars the engine already keeps."""
    return {}


# ------------------------------------------------------------------ the tools, on any timeframe's bars
def wma(x, k):
    """Linearly weighted moving average (weights 1..k, the newest k), backward only; NaN until k values
    after the first finite one (a NaN prefix is allowed, nothing else)."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    fin = np.flatnonzero(np.isfinite(x))
    if not len(fin):
        return out
    f = fin[0]
    y = x[f:]
    if len(y) >= k:
        w = np.arange(k, 0, -1, dtype=float)                       # newest value weight k
        out[f + k - 1:] = np.convolve(y, w, mode="valid") / (k * (k + 1) / 2.0)
    return out


def hma(close, n):
    """Hull moving average of length n."""
    c = np.asarray(close, dtype=float)
    return wma(2.0 * wma(c, n // 2) - wma(c, n), int(math.floor(math.sqrt(n))))


def kama(close, er_n=KAMA_ER, fast=KAMA_FAST, slow=KAMA_SLOW):
    """-> (KAMA, efficiency ratio) of a close array, backward only."""
    c = np.asarray(close, dtype=float)
    n = len(c)
    er = np.full(n, np.nan)
    if n > er_n:
        change = np.abs(c[er_n:] - c[:-er_n])
        noise = pd.Series(np.abs(np.diff(c))).rolling(er_n).sum().values[er_n - 1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            er[er_n:] = np.where(noise > 0, change / np.where(noise > 0, noise, 1.0), 0.0)
    fs, ss = 2.0 / (fast + 1.0), 2.0 / (slow + 1.0)
    sc = ((er * (fs - ss) + ss) ** 2).tolist()
    cl = c.tolist()
    out = [float("nan")] * n
    k = float("nan")
    for i in range(er_n, n):
        s = sc[i]
        if k != k:
            k = cl[i]                                              # seed: the first close with an ER
        elif s == s:
            k = k + s * (cl[i] - k)
        out[i] = k
    return np.array(out), er


def ichimoku(df):
    """-> dict of arrays on df's rows, every value known at that bar's close."""
    h, l = df["high"], df["low"]
    mid = lambda n: ((h.rolling(n).max() + l.rolling(n).min()) / 2.0).values   # noqa: E731
    tenkan, kijun = mid(TENKAN), mid(KIJUN)
    a_raw, b_raw = (tenkan + kijun) / 2.0, mid(SPAN_B)
    return {"tenkan": tenkan, "kijun": kijun, "ahead_a": a_raw, "ahead_b": b_raw,
            "span_a": _shift(a_raw, DISPLACE), "span_b": _shift(b_raw, DISPLACE),
            "lag_ref": _shift(df["close"].values.astype(float), DISPLACE)}


def _cross(fast, slow):
    pf, ps = _shift(fast), _shift(slow)
    with np.errstate(invalid="ignore"):
        up = (fast > slow) & (pf <= ps)
        dn = (fast < slow) & (pf >= ps)
    age, last = _since(up | dn)
    return age, last, _gather(up.astype(float) - dn.astype(float), last)


def _fade(direction, age):
    with np.errstate(invalid="ignore"):
        w = np.clip(1.0 - age / float(EVENT_FADE), 0.0, 1.0)
    return np.where(np.isfinite(age), direction * w, 0.0)


def _sq(v, scale):
    return np.tanh(v / scale)


# ------------------------------------------------------------------ cards
def _card_ichimoku(tf, df, c, atr, put, feat):
    if tf not in ICH_TFS:
        return
    ic = ichimoku(df)
    for k in ("tenkan", "kijun", "span_a", "span_b", "ahead_a", "ahead_b", "lag_ref"):
        put("ich_%s_%s_px" % (tf, k), ic[k])
    age, last, direction = _cross(ic["tenkan"], ic["kijun"])
    put("ich_%s_tk_x_age" % tf, age)
    put("ich_%s_tk_x_px" % tf, _gather(0.5 * (ic["tenkan"] + ic["kijun"]), last))
    a, b = ic["span_a"], ic["span_b"]
    top, bot = np.fmax(a, b), np.fmin(a, b)
    ok = np.isfinite(a) & np.isfinite(b)
    with np.errstate(divide="ignore", invalid="ignore"):
        inside = np.where(top > bot, (2.0 * (c - bot) / np.where(top > bot, top - bot, 1.0) - 1.0) * 0.5, 0.0)
        pos = np.where(c > top, 1.0, np.where(c < bot, -1.0, inside))
    feat("ich_pos_" + tf, np.where(ok, pos, np.nan))
    feat("ich_tk_" + tf, _sq(_ratio(ic["tenkan"] - ic["kijun"], atr), SCALE_TK))
    feat("ich_kijun_" + tf, _sq(_ratio(c - ic["kijun"], atr), SCALE_KIJUN))
    feat("ich_cloud_" + tf, _sq(_ratio(a - b, atr), SCALE_CLOUD))
    feat("ich_lag_" + tf, _sq(_ratio(c - ic["lag_ref"], atr), SCALE_LAG))


def _card_hull(tf, df, c, atr, put, feat):
    if tf not in HULL_TFS:
        return
    lines, dirs, pos = {}, [], []
    for n in HULL_LENGTHS:
        v = hma(c, n)
        lines[n] = v
        d = v - _shift(v)
        sgn = np.sign(d)
        prev = _shift(sgn)
        with np.errstate(invalid="ignore"):
            turn = np.isfinite(prev) & (sgn != 0) & (prev != 0) & (sgn != prev)
        age, last = _since(turn)
        put("hull_%s_%d_px" % (tf, n), v)
        put("hull_%s_%d_slope" % (tf, n), _ratio(d, atr))
        put("hull_%s_%d_turn_age" % (tf, n), age)
        dirs.append(sgn)
        with np.errstate(invalid="ignore"):
            pos.append(np.sign(c - v))
        if n == 21:
            feat("hull_turn_" + tf, _fade(np.nan_to_num(sgn), age))
    feat("hull_dir_" + tf, np.mean(np.vstack(dirs), axis=0))       # NaN while any line is unformed -> no read
    feat("hull_pos_" + tf, np.mean(np.vstack(pos), axis=0))
    age, last, direction = _cross(lines[9], lines[21])
    put("hull_%s_x_age" % tf, age)
    put("hull_%s_x_px" % tf, _gather(0.5 * (lines[9] + lines[21]), last))
    feat("hull_x_" + tf, _fade(np.nan_to_num(direction), age))


def _card_kama(tf, df, c, atr, put, feat):
    if tf not in KAMA_TFS:
        return
    k, er = kama(c)
    slope = _ratio(k - _shift(k, KAMA_SLOPE_BARS), atr)
    with np.errstate(invalid="ignore"):
        state = np.where(np.isfinite(slope), np.where(np.abs(slope) < KAMA_FLAT_ATR, 0.0, np.sign(slope)), np.nan)
        signed_er = er * np.sign(c - _shift(c, KAMA_ER))
    put("kama_%s_px" % tf, k)
    put("kama_%s_er" % tf, er)
    put("kama_%s_slope" % tf, slope)
    put("kama_%s_state" % tf, state)
    feat("kama_er_" + tf, signed_er)
    feat("kama_pos_" + tf, _sq(_ratio(c - k, atr), SCALE_KAMA_POS))
    feat("kama_slope_" + tf, _sq(slope, SCALE_KAMA_SLOPE))


_CARDS = OrderedDict([("ichimoku", _card_ichimoku), ("hull", _card_hull), ("kama", _card_kama)])


def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): the features in GROUPS (0.0 = no read, never NaN)
    and the readable RAW columns (NaN = no read), float32. bars: the asset's 15m frame (data.load(asset)
    when None). An index row without a bar is "no read"; a card that breaks is "no read" and its
    reason is in .attrs["errors"]."""
    index15 = pd.DatetimeIndex(index15)
    m = len(index15)
    fcol = dict((c_, j) for j, c_ in enumerate(FEATURES))
    rcol = dict((c_, j) for j, c_ in enumerate(RAW))
    block = np.full((m, len(FEATURES) + len(RAW)), np.nan, dtype=np.float32, order="F")
    F, R = block[:, :len(FEATURES)], block[:, len(FEATURES):]
    errors = {}
    try:
        b = _data.load(asset) if bars is None else bars
        b = b[["open", "high", "low", "close"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    if b is not None and len(b) and m:
        ms = _data.to_ms(b.index)
        want = _data.to_ms(index15)
        at = np.minimum(np.searchsorted(ms, want), len(ms) - 1)
        hit = ms[at] == want
        at = at[hit]
        R[hit, rcol["tt_close"]] = b["close"].values[at]
        for tf, rule in TFS.items():
            df = b if rule is None else _hbars(b, rule)
            if not len(df):
                continue
            sel = at if rule is None else closed_positions(ms, _data.to_ms(df.index), rule)[at]
            c = df["close"].values.astype(float)
            atr = _ind.atr_wilder(df, ATR_N).values.astype(float)
            atr = np.where(np.isfinite(atr) & (atr > 0), atr, np.nan)
            R[hit, rcol["tt_%s_atr" % tf]] = _gather(atr, sel)

            def put(name, arr, _sel=sel):
                R[hit, rcol[name]] = _gather(arr, _sel)

            def feat(name, arr, _sel=sel):
                F[hit, fcol[name]] = _gather(arr, _sel)

            for card, fn in _CARDS.items():
                if card in errors:
                    continue
                try:
                    fn(tf, df, c, atr, put, feat)
                except Exception as ex:                            # a card that breaks is "no read", not a crash
                    errors[card] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        for card in _CARDS:
            if card in errors:
                F[:, [fcol[c_] for c_ in GROUPS[card][1]]] = np.nan
                R[:, [rcol[c_] for c_ in _RAW[card]]] = np.nan
    F[~np.isfinite(F)] = 0.0
    out = pd.DataFrame(block, index=index15, columns=FEATURES + RAW, copy=False)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _atrs(v):
    return "%.1f ATR" % abs(v)


def _ich_read(row, tf):
    r = dict((k, _num(row, "ich_%s_%s" % (tf, k))) for k in ("tenkan_px", "kijun_px", "span_a_px", "span_b_px",
                                                               "ahead_a_px", "ahead_b_px", "lag_ref_px", "tk_x_age", "tk_x_px"))
    r["c"], r["atr"], r["tf"] = _num(row, "tt_close"), _num(row, "tt_%s_atr" % tf), tf
    return r


def _ich_words(r, asset, short=False):
    px = lambda v: _px(v, asset)                                    # noqa: E731
    c, a, b, atr = r["c"], r["span_a_px"], r["span_b_px"], r["atr"]
    if None in (c, a, b, r["kijun_px"], r["tenkan_px"]) or not atr:
        return "%s: not enough closed bars for the cloud yet" % r["tf"]
    top, bot = max(a, b), min(a, b)
    if c > top:
        where = "price above the cloud, %s over its top (%s)" % (_atrs((c - top) / atr), px(top))
    elif c < bot:
        where = "price below the cloud, %s under its bottom (%s)" % (_atrs((bot - c) / atr), px(bot))
    else:
        where = "price inside the cloud (%s to %s)" % (px(bot), px(top))
    s = "%s: %s; the cloud is %s, %s thick" % (r["tf"], where, "green (span A over B)" if a >= b else "red (span A under B)",
                                              _atrs((top - bot) / atr))
    tk = "Tenkan %s Kijun" % ("above" if r["tenkan_px"] >= r["kijun_px"] else "below")
    if r["tk_x_age"] is not None and r["tk_x_px"] is not None:
        tk += " (crossed %s at %s)" % (_ago(r["tk_x_age"]), px(r["tk_x_px"]))
    s += "; %s; price %s %s the Kijun (%s)" % (tk, _atrs((c - r["kijun_px"]) / atr), "above" if c >= r["kijun_px"] else "below",
                                             px(r["kijun_px"]))
    if short:
        return s
    if r["lag_ref_px"] is not None:
        s += "; lagging line %s price 26 bars back (%s)" % ("above" if c > r["lag_ref_px"] else "below", px(r["lag_ref_px"]))
    if r["ahead_a_px"] is not None and r["ahead_b_px"] is not None:
        s += "; the cloud ahead is %s" % ("green" if r["ahead_a_px"] >= r["ahead_b_px"] else "red")
    return s


def _hull_read(row, tf):
    r = {"tf": tf, "c": _num(row, "tt_close"), "atr": _num(row, "tt_%s_atr" % tf)}
    for n in HULL_LENGTHS:
        for k in ("px", "slope", "turn_age"):
            r["%d_%s" % (n, k)] = _num(row, "hull_%s_%d_%s" % (tf, n, k))
    r["x_age"], r["x_px"] = _num(row, "hull_%s_x_age" % tf), _num(row, "hull_%s_x_px" % tf)
    return r


def _hull_words(r, asset):
    if r["c"] is None or any(r["%d_px" % n] is None for n in HULL_LENGTHS):
        return "%s: not enough closed bars for the Hull lines yet" % r["tf"]
    bits = []
    for n in HULL_LENGTHS:
        v, sl, age = r["%d_px" % n], r["%d_slope" % n], r["%d_turn_age" % n]
        way = "flat" if not sl else "rising" if sl > 0 else "falling"
        w = "HMA %d %s (%s, price %s)" % (n, way, _px(v, asset), "above" if r["c"] > v else "below")
        if age is not None and sl:
            w = w[:-1] + ", turned %s %s)" % ("up" if sl > 0 else "down", _ago(age))
        bits.append(w)
    s = "%s: %s" % (r["tf"], "; ".join(bits))
    if r["x_age"] is not None:
        up = r["9_px"] > r["21_px"]
        s += "; HMA 9 crossed %s HMA 21 %s at %s" % ("above" if up else "below", _ago(r["x_age"]), _px(r["x_px"], asset))
    return s


def _kama_read(row, tf):
    r = {"tf": tf, "c": _num(row, "tt_close"), "atr": _num(row, "tt_%s_atr" % tf)}
    for k in ("px", "er", "slope", "state"):
        r[k] = _num(row, "kama_%s_%s" % (tf, k))
    return r


def _kama_words(r, asset):
    if r["px"] is None or r["er"] is None or r["c"] is None or not r["atr"]:
        return "%s: not enough closed bars for KAMA yet" % r["tf"]
    st = r["state"]
    label = "flat (no trend)" if st == 0 else "trending up" if st and st > 0 else "trending down" if st else "n/a"
    er = r["er"]
    chop = "choppy" if er < 0.3 else "mixed" if er < 0.6 else "efficient"
    return "%s: %s, efficiency ratio %.2f (%s); KAMA %s, price %s %s it" % (
        r["tf"], label, er, chop, _px(r["px"], asset), _atrs((r["c"] - r["px"]) / r["atr"]), "above" if r["c"] >= r["px"] else "below")


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    coin, say = asset.replace("USDT", ""), OrderedDict()
    r1, r4 = _ich_read(row, "1h"), _ich_read(row, "4h")
    title = GROUPS["ichimoku"][0]
    if r1["kijun_px"] is None and r4["kijun_px"] is None:
        say[title] = "No read: not enough closed %s bars for the Ichimoku cloud." % coin
    else:
        say[title] = _ich_words(r4, asset, short=True) + "; " + _ich_words(r1, asset, short=True) + "."
    title = GROUPS["hull"][0]
    h1, h15 = _hull_read(row, "1h"), _hull_read(row, "15m")
    if h1["9_px"] is None and h15["9_px"] is None:
        say[title] = "No read: not enough closed %s bars for the Hull lines." % coin
    else:
        say[title] = _hull_words(h1, asset) + "; " + _hull_words(h15, asset) + "."
    title = GROUPS["kama"][0]
    ks = [_kama_read(row, tf) for tf in ("4h", "1h", "15m")]
    if all(k["px"] is None for k in ks):
        say[title] = "No read: not enough closed %s bars for KAMA." % coin
    else:
        say[title] = "; ".join(_kama_words(k, asset) for k in ks) + "."
    return say


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: readable prices, ATRs and ages."""
    out = OrderedDict()
    px = lambda v: _px(v, asset)                                    # noqa: E731
    rows = []
    for tf in ("1h", "4h"):
        r = _ich_read(row, tf)
        rows.append(["%s cloud" % tf, _ich_words(r, asset).split(": ", 1)[1]])
        if r["tenkan_px"] is not None:
            rows.append(["%s lines" % tf, "Tenkan %s, Kijun %s, cloud now %s / %s, cloud ahead %s / %s" % (
                px(r["tenkan_px"]), px(r["kijun_px"]), px(r["span_a_px"]), px(r["span_b_px"]),
                px(r["ahead_a_px"]), px(r["ahead_b_px"]))])
    out[GROUPS["ichimoku"][0]] = rows
    rows = []
    for tf in ("15m", "1h"):
        r = _hull_read(row, tf)
        for n in HULL_LENGTHS:
            v, sl, age = r["%d_px" % n], r["%d_slope" % n], r["%d_turn_age" % n]
            if v is None or r["c"] is None:
                continue
            txt = "%s, %s; price %s it" % (px(v), "flat" if not sl else ("rising" if sl > 0 else "falling"), "above" if r["c"] > v else "below")
            if age is not None:
                txt += "; last turn %s" % _ago(age)
            if n == 21 and r["x_age"] is not None:
                txt += "; 9/21 cross %s at %s" % (_ago(r["x_age"]), px(r["x_px"]))
            if n in (9, 21) or tf == "1h":
                rows.append(["%s HMA %d" % (tf, n), txt])
    out[GROUPS["hull"][0]] = rows[:6] if rows else [["Hull", "not enough closed bars yet"]]
    rows = []
    for tf in ("15m", "1h", "4h"):
        r = _kama_read(row, tf)
        rows.append(["%s KAMA" % tf, _kama_words(r, asset).split(": ", 1)[1]])
        if r["slope"] is not None and tf == "4h":
            rows.append(["4h KAMA slope", "%+.2f ATR over %d bars (flat below %.2f)" % (r["slope"], KAMA_SLOPE_BARS, KAMA_FLAT_ATR)])
    rows.append(["Efficiency ratio", "0 = pure chop, 1 = a straight line; read over the last %d bars of each timeframe" % KAMA_ER])
    out[GROUPS["kama"][0]] = rows
    return out
