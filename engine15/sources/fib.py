# -*- coding: utf-8 -*-
"""fib -- Fibonacci retracement and extension of the last confirmed impulse leg, on 1h, 4h and 1d.

WHY (owner, 11 Nov 2026): "include fibonacci retracement skill into the AI engine to help it plan
entry and exit". It serves charter tasks A (timing an entry on a pullback inside a larger move) and
B (exits: a realistic target and an invalidation price).

THE LEG. On each timeframe the swings are structure.py's CONFIRMED swings (a swing high is the
highest high of the K bars either side of it, known only K bars later; K from structure.SWING_K).
The impulse leg is kept as a small state machine over those swings, in the order they are confirmed:
    up-leg (origin = a swing low, end = a swing high)
      a higher swing high confirms      -> the leg extends: end = that high; if a swing low was
                                           confirmed since the old end (the pullback low that held),
                                           the leg is redrawn from it (the newest impulse)
      a lower swing high confirms       -> ignored (a lower high inside the pullback)
      a swing low ABOVE the origin      -> remembered as the pullback low; the leg stands
      a swing low BELOW the origin      -> the leg is broken: a new down-leg from the old end to it
    down-leg: the mirror.
So the leg flips only on a confirmed break of its origin; a pullback that holds keeps the leg.

THE LEVELS of a leg from origin O to end E (both directions, one formula):
    level(r) = E - r * (E - O)
    retracements r = 0.236, 0.382, 0.5, 0.618, 0.786       (0 = at the end, 1 = back at the origin)
    extensions   1.272 and 1.618 = level(-0.272), level(-0.618) = O + 1.272 (E - O) ...
                 i.e. beyond the leg end in the leg's direction: the targets
    depth = (E - close) / (E - O): 0 at the leg end, 1 fully retraced, < 0 past the end, > 1 past the origin
    golden zone: depth 0.5 to 0.618. Invalidation: beyond the 0.786 (the leg origin is the hard one).
    Plan: entry at the 0.618, stop beyond the 0.786, targets at the 1.272 and the 1.618;
    reward/risk NOW = distance to the 1.272 / distance to the 0.786.
    Realistic? The 1.272's distance is set against the 24h "realistic reach" of ltf.py (the median
    move in either direction within 24 hours over the last 90 days, scaled to today's ATR).

THE ONE RULE. A row may use only what was known at that 15m close: swings appear K bars after they
form, every higher timeframe reaches a 15m row through data.htf_on_15 (only once that bar CLOSED),
the deepest retracement is a running maximum, and reach ratios enter only once their 24h has passed.
tests/test_fib.py cuts the future off and checks every column.

No reading here is claimed to predict anything. Interface of engine15/sources: GROUPS, update,
features, describe, facts. Docs: docs/SOURCES_fib.md.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind
from .structure import SWING_K as _STRUCT_K

try:                                     # realistic reach (ltf.py); without it the room reading is "no read"
    from . import ltf as _ltf
except Exception:                        # pragma: no cover
    _ltf = None

# =====================================================================================
# THE ONE CONSTANT BLOCK. Conventional values, declared once, none tuned against outcomes.
# =====================================================================================
TFS = OrderedDict([("1h", "1h"), ("4h", "4h"), ("1d", "1D")])   # timeframe tag -> pandas rule
SWING_K = dict((t, _STRUCT_K[t]) for t in TFS)                  # 1h 3, 4h 3, 1d 2: the same swings as structure.py
RETR = (0.236, 0.382, 0.5, 0.618, 0.786)
EXT = (1.272, 1.618)
GOLDEN = (0.5, 0.618)
NEAR_ATR = 0.25                  # "at a level" / "levels coincide": within a quarter of the 1h ATR
ATR_N = 14                       # the engine's yardstick: Wilder ATR(14) of the 1-hour chart
BAR_MS, HOUR_MS = 900000, 3600000
REACH_BARS = 96                  # realistic reach horizon: 24 hours of 15m bars
# =====================================================================================

# every level as r in level(r) = E - r (E - O): retracements, then the extensions
LEVELS = [(r, "%g" % r) for r in RETR] + [(1.0 - x, "%g" % x) for x in EXT]
LVL_COLS = ["r236_px", "r382_px", "r500_px", "entry_px", "inval_px", "t1_px", "t2_px"]   # same order as LEVELS
LVL_NAMES = dict(zip(LVL_COLS, [n for _r, n in LEVELS]))

GROUPS = OrderedDict([
    ("fib", ("Fibonacci retracement",
             ["fib_gz_1h", "fib_gz_4h", "fib_depth_1h", "fib_depth_4h", "fib_conf", "fib_room_1h", "fib_rr_1h"])),
])
FEATURES = list(GROUPS["fib"][1])
_PER_TF = ["dir", "origin_px", "end_px", "end_age_h", "depth", "maxdepth", "gz", "broken"] + LVL_COLS + \
          ["near_lvl", "near_atr", "rr", "t1_pct", "t1_reach_x"]
RAW = ["fib_close_px", "fib_atr1h_px", "fib_reach24_pct", "fib_reach24_p80_pct", "fib_conf_n",
       "fib_cluster_px", "fib_cluster_atr"] + ["fib_%s_%s" % (t, c) for t in TFS for c in _PER_TF]

DECIMALS = {"BTCUSDT": 0, "ETHUSDT": 2, "XAUUSD": 2, "XAGUSD": 3, "USDJPY": 3, "SPX": 2}


def update(log=print):
    """Nothing to fetch: every reading comes from the 15m bars the engine already keeps."""
    return {}


# ------------------------------------------------------------------ the leg, on one timeframe
def legs(high, low, close, k):
    """Impulse leg of one timeframe's bars as known at the CLOSE of every bar.
    -> (direction +1/-1/0, origin price, end price, origin bar, end bar); bars are positions, -1 = none.
    A swing at bar j (structure.swings' definition) is used from bar j + k on."""
    high, low, close = (np.asarray(x, dtype=float) for x in (high, low, close))
    n = len(high)
    win = 2 * k + 1
    with np.errstate(invalid="ignore"):
        ph = high == pd.Series(high).rolling(win, center=True).max().values
        pl = low == pd.Series(low).rolling(win, center=True).min().values
    ph[:k], pl[:k] = False, False                                  # structure.swings uses a swing only once j >= k
    js = np.flatnonzero(ph | pl)
    out_dir, out_o, out_e = np.zeros(n), np.full(n, np.nan), np.full(n, np.nan)
    out_oj, out_ej = np.full(n, -1.0), np.full(n, -1.0)
    if not len(js):
        return out_dir, out_o, out_e, out_oj, out_ej
    ev_i, ev_state = [], []
    d, o, e, oj, ej = 0, np.nan, np.nan, -1, -1
    pull, pullj = np.nan, -1                                       # extreme of the counter-move since the end
    last_lo, last_loj, last_hi, last_hij = np.nan, -1, np.nan, -1
    for j in js:
        if j + k >= n:
            break
        evs = []
        if ph[j] and pl[j]:                                        # an outside bar: which extreme came first?
            evs = [("L", low[j]), ("H", high[j])] if close[j] >= 0.5 * (high[j] + low[j]) else [("H", high[j]), ("L", low[j])]
        elif ph[j]:
            evs = [("H", high[j])]
        else:
            evs = [("L", low[j])]
        for kind, p in evs:
            if kind == "H":
                if d == 1:
                    if p > e:
                        if pullj >= 0:
                            o, oj = pull, pullj
                        e, ej, pull, pullj = p, j, np.nan, -1
                elif d == -1:
                    if p > o:                                      # the down-leg's origin is broken
                        d, o, oj, e, ej, pull, pullj = 1, e, ej, p, j, np.nan, -1
                    elif pullj < 0 or p > pull:
                        pull, pullj = p, j
                elif last_loj >= 0:
                    d, o, oj, e, ej = 1, last_lo, last_loj, p, j
                last_hi, last_hij = p, j
            else:
                if d == -1:
                    if p < e:
                        if pullj >= 0:
                            o, oj = pull, pullj
                        e, ej, pull, pullj = p, j, np.nan, -1
                elif d == 1:
                    if p < o:                                      # the up-leg's origin is broken
                        d, o, oj, e, ej, pull, pullj = -1, e, ej, p, j, np.nan, -1
                    elif pullj < 0 or p < pull:
                        pull, pullj = p, j
                elif last_hij >= 0:
                    d, o, oj, e, ej = -1, last_hi, last_hij, p, j
                last_lo, last_loj = p, j
        ev_i.append(j + k)
        ev_state.append((d, o, e, oj, ej))
    if not ev_i:
        return out_dir, out_o, out_e, out_oj, out_ej
    ev_i = np.asarray(ev_i)
    st = np.asarray(ev_state, dtype=float)
    at = np.searchsorted(ev_i, np.arange(n), side="right") - 1    # the newest confirmation at or before each bar
    ok = at >= 0
    for arr, col in ((out_dir, 0), (out_o, 1), (out_e, 2), (out_oj, 3), (out_ej, 4)):
        arr[ok] = st[at[ok], col]
    return out_dir, out_o, out_e, out_oj, out_ej


def _hbars(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def _tf_leg(b, rule, k):
    """One timeframe's leg on the 15m rows, through the no-look-ahead join. -> dict of arrays."""
    hb = _hbars(b, rule)
    d, o, e, oj, ej = legs(hb["high"].values, hb["low"].values, hb["close"].values, k)
    ms = _data.to_ms(hb.index).astype(float)
    end_ms = np.where(ej >= 0, ms[np.maximum(ej, 0).astype(int)], np.nan)
    frame = pd.DataFrame({"dir": d, "o": o, "e": e, "end_ms": end_ms}, index=hb.index)
    j = _data.htf_on_15(b, rule, frame)
    return dict((c, j[c].values.astype(float)) for c in frame.columns)


def _reach24(b, h, l, c, atr):
    """ltf.py's realistic reach over 24 hours (median and 80th percentile), in % of the close."""
    n = len(c)
    nan = np.full(n, np.nan)
    if _ltf is None or n == 0:
        return nan, nan.copy()
    ms = _data.to_ms(b.index)
    sample = np.flatnonzero(ms % HOUR_MS == HOUR_MS - BAR_MS)    # one bar an hour, as ltf samples
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = pd.Series((_ltf.forward_reach(h, l, c, REACH_BARS) / atr)[sample])
    roll = ratio.rolling(_ltf.REACH_WIN, min_periods=_ltf.REACH_MIN)
    known = sample + REACH_BARS                                   # a ratio is history only once its 24h passed
    k = np.searchsorted(known, np.arange(n), side="right") - 1
    res = []
    for series in (roll.median(), roll.quantile(_ltf.REACH_Q)):
        v = series.values
        got = np.where(k >= 0, v[np.maximum(k, 0)], np.nan) if len(v) else nan.copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            res.append(np.where(c > 0, 100.0 * got * atr / c, np.nan))
    return res[0], res[1]


# ------------------------------------------------------------------ features
def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): the features named in GROUPS (0.0 = no read,
    never NaN) and the readable RAW columns (NaN = no read). bars: the asset's 15m frame
    (data.load(asset) when None). Readings are made on the bars, then handed to the index rows
    with the same open time; an index row without a bar is "no read"."""
    index15 = pd.DatetimeIndex(index15)
    names = FEATURES + RAW
    col = dict((c_, j) for j, c_ in enumerate(names))
    block = np.full((len(index15), len(names)), np.nan, order="F")
    errors = {}
    try:
        b = _data.load(asset) if bars is None else bars
        b = b[["open", "high", "low", "close"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    if b is not None and len(b) and len(index15):
        try:
            cols = _compute(b)
            ms = _data.to_ms(b.index)
            want = _data.to_ms(index15)
            at = np.minimum(np.searchsorted(ms, want), len(ms) - 1)
            hit = ms[at] == want
            at = at[hit]
            for name, values in cols.items():
                block[hit, col[name]] = values[at]
        except Exception as ex:                                    # a reading that breaks is "no read", not a crash
            errors["fib"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
            block[:] = np.nan
    feats = block[:, :len(FEATURES)]
    feats[~np.isfinite(feats)] = 0.0
    out = pd.DataFrame(block, index=index15, columns=names, copy=False)
    out.attrs["errors"] = errors
    return out


def _zone_weight(depth):
    """1 inside the golden zone, 0.5 in the 0.382-0.5 or 0.618-0.786 band either side, else 0."""
    with np.errstate(invalid="ignore"):
        gz = (depth >= GOLDEN[0]) & (depth <= GOLDEN[1])
        side = ((depth >= RETR[1]) & (depth < GOLDEN[0])) | ((depth > GOLDEN[1]) & (depth <= RETR[4]))
    return np.where(gz, 1.0, np.where(side, 0.5, 0.0)), gz


def _compute(b):
    """Every column of the module on the bars' own rows. -> {name: array}."""
    h, l, c = b["high"].values, b["low"].values, b["close"].values
    n = len(c)
    out = {}
    h1 = _hbars(b, "1h")
    tr = pd.concat([h1["high"] - h1["low"], (h1["high"] - h1["close"].shift(1)).abs(),
                    (h1["low"] - h1["close"].shift(1)).abs()], axis=1).max(axis=1)
    atr = _data.htf_on_15(b, "1h", tr.ewm(alpha=1.0 / ATR_N, adjust=False, min_periods=ATR_N).mean()).values.astype(float)
    atr = np.where(np.isfinite(atr) & (atr > 0), atr, np.nan)
    out["fib_close_px"], out["fib_atr1h_px"] = c.astype(float), atr
    reach, reach80 = _reach24(b, h, l, c, atr)
    out["fib_reach24_pct"], out["fib_reach24_p80_pct"] = reach, reach80
    my_close = (_data.to_ms(b.index) + BAR_MS).astype(float)

    lv = {}                                                        # tf -> [(level array, kind +1 retracement / -1 extension)]
    dirs, seen = {}, []
    for tf, rule in TFS.items():
        g = _tf_leg(b, rule, SWING_K[tf])
        d, o, e = g["dir"], g["o"], g["e"]
        same = np.zeros(n, dtype=bool)                             # the same leg as a lower timeframe's: not new confluence
        for so, se in seen:
            same |= (o == so) & (e == se)
        seen.append((o, e))
        with np.errstate(invalid="ignore", divide="ignore"):
            span = e - o
            valid = np.isfinite(d) & (d != 0) & np.isfinite(span) & (span * np.nan_to_num(d) > 0)
            d = np.where(valid, d, 0.0)
            span = np.where(valid, span, np.nan)
            depth = (e - c) / span
        # deepest retracement since this leg became known (a running maximum: never a later bar)
        key = np.where(valid, 0.0, np.nan)
        change = np.ones(n, dtype=bool)
        change[1:] = ~((o[1:] == o[:-1]) & (e[1:] == e[:-1]))
        leg_id = np.cumsum(change)
        maxdepth = pd.Series(depth).groupby(leg_id).cummax().values + key
        with np.errstate(invalid="ignore"):
            broken = np.where(valid, (maxdepth > RETR[4]).astype(float), np.nan)
        weight, gz = _zone_weight(depth)
        p = "fib_%s_" % tf
        out[p + "dir"] = d
        out[p + "origin_px"], out[p + "end_px"] = np.where(valid, o, np.nan), np.where(valid, e, np.nan)
        out[p + "end_age_h"] = np.where(valid, (my_close - g["end_ms"]) / HOUR_MS, np.nan)
        out[p + "depth"], out[p + "maxdepth"] = depth, maxdepth
        out[p + "gz"] = np.where(valid, (gz & (broken == 0)).astype(float), np.nan)
        out[p + "broken"] = broken
        levels = []
        best, best_r = np.full(n, np.inf), np.full(n, np.nan)
        for (r, _name), cname in zip(LEVELS, LVL_COLS):
            px = e - r * span
            out[p + cname] = px
            levels.append((np.where(same, np.nan, px), 1.0 if r > 0 else -1.0))
            with np.errstate(invalid="ignore"):
                dist = np.abs(c - px) / atr
                closer = dist < best
            best = np.where(closer, dist, best)
            best_r = np.where(closer, 1.0 - r if r < 0 else r, best_r)
        out[p + "near_atr"] = np.where(np.isfinite(best), best, np.nan)
        out[p + "near_lvl"] = np.where(np.isfinite(best), best_r, np.nan)
        t1, inval = out[p + "t1_px"], out[p + "inval_px"]
        with np.errstate(invalid="ignore", divide="ignore"):
            reward, risk = (t1 - c) * d, (c - inval) * d
            out[p + "rr"] = np.where(valid & (risk > 0), np.maximum(reward, 0.0) / risk, np.nan)
            out[p + "t1_pct"] = np.where(valid & (c > 0), 100.0 * reward / c, np.nan)
            out[p + "t1_reach_x"] = out[p + "t1_pct"] / reach
        lv[tf], dirs[tf] = levels, d
        if tf in ("1h", "4h"):
            out["fib_gz_" + tf] = d * np.where(broken == 0, weight, 0.0)
            out["fib_depth_" + tf] = d * np.clip(depth, -1.0, 1.5) / 1.5

    # ---- confluence: levels at the price, and the nearest place where two timeframes' levels coincide
    conf_n, conf_s = np.zeros(n), np.zeros(n)
    for tf, levels in lv.items():
        for px, kind in levels:
            with np.errstate(invalid="ignore"):
                at = np.abs(c - px) <= NEAR_ATR * atr
            conf_n += at
            conf_s += np.where(at, kind * dirs[tf], 0.0)           # a retracement under an up-leg supports (+), a target caps (-)
    ok = np.isfinite(atr)
    out["fib_conf_n"] = np.where(ok, conf_n, np.nan)
    out["fib_conf"] = np.clip(conf_s / 3.0, -1.0, 1.0)
    best, best_mid = np.full(n, np.inf), np.full(n, np.nan)
    tfl = list(lv)
    for a in range(len(tfl)):
        for z in range(a + 1, len(tfl)):
            for pa, _ka in lv[tfl[a]]:
                for pz, _kz in lv[tfl[z]]:
                    with np.errstate(invalid="ignore"):
                        mid = 0.5 * (pa + pz)
                        dist = np.abs(mid - c)
                        hitp = (np.abs(pa - pz) <= NEAR_ATR * atr) & (dist < best)
                    best = np.where(hitp, dist, best)
                    best_mid = np.where(hitp, mid, best_mid)
    out["fib_cluster_px"] = best_mid
    with np.errstate(invalid="ignore", divide="ignore"):
        out["fib_cluster_atr"] = (best_mid - c) / atr                # + = above the price

    # ---- plan readings of the 1h leg as features
    d1 = out["fib_1h_dir"]
    with np.errstate(invalid="ignore", divide="ignore"):
        x = out["fib_1h_t1_reach_x"]
        out["fib_room_1h"] = np.where(np.isfinite(x), d1 * np.clip(x, -1.0, 2.0) / 2.0, 0.0)
        rr = out["fib_1h_rr"]
        lr = np.where(rr > 0, np.log2(np.where(rr > 0, rr, 1.0)), -2.0)
        out["fib_rr_1h"] = np.where(np.isfinite(rr), d1 * np.clip(lr, -2.0, 2.0) / 2.0, 0.0)
    return dict((k_, np.asarray(v, dtype=float)) for k_, v in out.items())


# ------------------------------------------------------------------ plain English
def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _px(v, asset):
    if v is None:
        return "n/a"
    dec = DECIMALS.get(asset)
    if dec is None:
        a = abs(v)
        dec = 0 if a >= 10000 else 2 if a >= 100 else 3 if a >= 1 else 5
    return "{:,.{d}f}".format(v, d=dec)


def _leg(row, tf):
    """The readable columns of one timeframe's leg, or None when there is no leg."""
    p = "fib_%s_" % tf
    r = dict((c_, _num(row, p + c_)) for c_ in _PER_TF)
    if not r["dir"] or r["origin_px"] is None or r["end_px"] is None or r["depth"] is None:
        return None
    r["close"], r["atr"] = _num(row, "fib_close_px"), _num(row, "fib_atr1h_px")
    r["reach"], r["reach80"] = _num(row, "fib_reach24_pct"), _num(row, "fib_reach24_p80_pct")
    return r


def _where(r, asset, short=False):
    """Where the close sits in the leg, in words."""
    d, up = r["depth"], r["dir"] > 0
    px = lambda v: _px(v, asset)                                    # noqa: E731
    lo_gz, hi_gz = sorted([r["entry_px"], r["r500_px"]])
    if d < 0:
        s, tag = "past the leg end, in extension (%.2f of the leg beyond it)" % (-d), "past the leg end"
    elif d > 1:
        s, tag = "past the leg origin: the leg is broken and is redrawn once a new swing confirms", "past the leg origin"
    elif r["broken"]:
        s = "at the %.2f retracement, after the 0.786 was broken (leg invalidated; deepest %.2f)" % (d, r["maxdepth"])
        tag = "at the %.2f retracement, 0.786 broken" % d
    elif GOLDEN[0] <= d <= GOLDEN[1]:
        s = "at the %.2f retracement, inside the golden zone %s-%s" % (d, px(lo_gz), px(hi_gz))
        tag = "at the %.2f retracement, in the golden zone" % d
    elif d < RETR[0]:
        s, tag = "at the %.2f retracement, near the leg end (no real pullback yet)" % d, "at the %.2f retracement" % d
    elif d < GOLDEN[0]:
        s = "at the %.2f retracement, a shallow pullback %s the golden zone %s-%s" % (
            d, "above" if up else "below", px(lo_gz), px(hi_gz))
        tag = "at the %.2f retracement" % d
    else:
        s = "at the %.2f retracement, %s the golden zone and %s the 0.786" % (
            d, "below" if up else "above", "above" if up else "below")
        tag = "at the %.2f retracement" % d
    return tag if short else s


def _reach_words(r):
    x, t1 = r["t1_reach_x"], r["t1_pct"]
    if t1 is None:
        return None
    if t1 <= 0:
        return "the 1.272 is already behind price"
    if x is None or r["reach"] is None:
        return "the 1.272 is %.2f%% away (no realistic-reach read yet)" % t1
    if t1 <= r["reach"]:
        verdict = "realistic within a day"
    elif r["reach80"] is not None and t1 <= r["reach80"]:
        verdict = "a stretch for one day (a large day travels %.2f%%)" % r["reach80"]
    else:
        verdict = "not realistic within a day (beyond even a large day's %.2f%%)" % (r["reach80"] or r["reach"])
    return "the 1.272 is %.2f%% away, %.1fx a typical day's travel (%.2f%%): %s" % (t1, x, r["reach"], verdict)


def _tf_sentence(r, tf, asset):
    px = lambda v: _px(v, asset)                                    # noqa: E731
    up = r["dir"] > 0
    s = "%s %s-leg %s -> %s; price %s is %s; invalid %s %s (0.786, origin %s); targets %s (1.272) and %s (1.618)" % (
        tf, "up" if up else "down", px(r["origin_px"]), px(r["end_px"]), px(r["close"]), _where(r, asset),
        "below" if up else "above", px(r["inval_px"]), px(r["origin_px"]), px(r["t1_px"]), px(r["t2_px"]))
    return s


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    title = GROUPS["fib"][0]
    r1, r4 = _leg(row, "1h"), _leg(row, "4h")
    if r1 is None and r4 is None:
        return {title: "No read: no confirmed 1h or 4h swing leg yet."}
    bits = []
    main = r1 or r4
    bits.append(_tf_sentence(main, "1h" if r1 else "4h", asset))
    if main["rr"] is not None:
        bits.append("entered now %s, reward/risk to the 1.272 would be %.1f to 1" % (
            "long" if main["dir"] > 0 else "short", main["rr"]))
    rw = _reach_words(main)
    if rw:
        bits.append(rw)
    if r1 is not None and r4 is not None and _same_as(row, "4h"):
        bits.append("the 4h chart's last leg is the same leg")
    elif r1 is not None and r4 is not None:
        bits.append("the 4h %s-leg (%s -> %s) has price %s" % (
            "up" if r4["dir"] > 0 else "down", _px(r4["origin_px"], asset), _px(r4["end_px"], asset), _where(r4, asset, short=True)))
    n = _num(row, "fib_conf_n")
    if n:
        bits.append("%d fib level%s within %.2f ATR of price" % (n, "" if n == 1 else "s", NEAR_ATR))
    return {title: "; ".join(bits) + "."}


def _same_as(row, tf):
    """The lower timeframe whose leg is the very same leg as this one's (same origin and end), or None."""
    o, e = _num(row, "fib_%s_origin_px" % tf), _num(row, "fib_%s_end_px" % tf)
    for lower in TFS:
        if lower == tf:
            return None
        if o is not None and o == _num(row, "fib_%s_origin_px" % lower) and e == _num(row, "fib_%s_end_px" % lower):
            return lower
    return None


def _cluster_words(row, asset):
    cp, ca, atr = _num(row, "fib_cluster_px"), _num(row, "fib_cluster_atr"), _num(row, "fib_atr1h_px")
    if cp is None or atr is None:
        return "no two different legs' levels coincide"
    names = []
    for tf in TFS:
        if _same_as(row, tf):
            continue
        for cname in LVL_COLS:
            v = _num(row, "fib_%s_%s" % (tf, cname))
            if v is not None and abs(v - cp) <= NEAR_ATR * atr * 1.0001:
                names.append("%s %s" % (tf, LVL_NAMES[cname]))
    return "%s (%s), %.1f ATR %s price" % (_px(cp, asset), " + ".join(names), abs(ca or 0.0), "above" if (ca or 0) > 0 else "below")


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: prices, ratios and percentages a
    person can read (never a scaled model number)."""
    title = GROUPS["fib"][0]
    px = lambda v: _px(v, asset)                                    # noqa: E731
    rows = []
    r1 = _leg(row, "1h")
    if r1 is None:
        rows.append(["1h leg", "no confirmed 1h swing leg yet"])
    else:
        up = r1["dir"] > 0
        age = "" if r1["end_age_h"] is None else ", leg end %.0f h ago" % r1["end_age_h"]
        rows.append(["1h leg", "%s %s -> %s%s" % ("up" if up else "down", px(r1["origin_px"]), px(r1["end_px"]), age)])
        near = "" if r1["near_lvl"] is None else "; nearest level %g at %.2f ATR" % (r1["near_lvl"], r1["near_atr"])
        rows.append(["Where price is (1h)", "%s %s%s" % (px(r1["close"]), _where(r1, asset), near)])
        rows.append(["Levels (1h)", "0.236 %s, 0.382 %s, 0.5 %s, 0.618 %s, 0.786 %s" % (
            px(r1["r236_px"]), px(r1["r382_px"]), px(r1["r500_px"]), px(r1["entry_px"]), px(r1["inval_px"]))])
        rows.append(["Pullback entry / invalidation (1h)", "entry at the 0.618 %s; invalid %s %s (0.786); leg origin %s" % (
            px(r1["entry_px"]), "below" if up else "above", px(r1["inval_px"]), px(r1["origin_px"]))])
        rw = _reach_words(r1)
        rows.append(["Targets (1h)", "%s (1.272) and %s (1.618)%s" % (px(r1["t1_px"]), px(r1["t2_px"]), "; " + rw if rw else "")])
        rows.append(["Reward / risk now (1h)", "n/a: price is beyond the 0.786" if r1["rr"] is None else
                     "%.1f to 1, %s to the 1.272 with the stop beyond the 0.786" % (r1["rr"], "long" if up else "short")])
    for tf in ("4h", "1d"):
        r = _leg(row, tf)
        if r is None:
            rows.append(["%s leg" % tf, "no confirmed %s swing leg yet" % tf])
            continue
        if _same_as(row, tf):
            rows.append(["%s leg" % tf, "the same leg as the %s (%s -> %s)" % (
                _same_as(row, tf), px(r["origin_px"]), px(r["end_px"]))])
            continue
        up = r["dir"] > 0
        rows.append(["%s leg" % tf, "%s %s -> %s; price %s; golden zone %s-%s, invalid %s %s, targets %s / %s" % (
            "up" if up else "down", px(r["origin_px"]), px(r["end_px"]), _where(r, asset, short=True),
            *[px(v) for v in sorted([r["entry_px"], r["r500_px"]])], "below" if up else "above", px(r["inval_px"]),
            px(r["t1_px"]), px(r["t2_px"]))])
    n = _num(row, "fib_conf_n")
    rows.append(["Confluence", "%s fib level%s within %.2f ATR of price; nearest cluster of two legs' levels: %s" % (
        "no" if not n else "%d" % n, "" if n == 1 else "s", NEAR_ATR, _cluster_words(row, asset))])
    return {title: rows}
