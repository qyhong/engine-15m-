# -*- coding: utf-8 -*-
"""mavg -- moving averages as a trader reads them: three decision cards from the asset's own 15m bars.

Owner, 11 Nov 2026: "Adding moving average reading also. Using simple and exponential on 5, 10, 20,
50 and 200", a moving-average ribbon "to assist engine directional trade", and "sometimes support
and resistance can be in moving average structure rather than just a horizontal line".

  mavg     Moving averages (SMA and EMA 5-200)        on 15m, 1h, 4h, 1d: the ten averages' prices, the
                                                      close's distance from each, how many price is above,
                                                      the stack order (and the pair that breaks it), the
                                                      slope of the 20/50/200, and six crosses with their
                                                      age and price (EMA 5/10, 10/20, 20/50, golden/death
                                                      cross SMA 50/200, price through the EMA 20 / SMA 200)
  ribbon   Moving-average ribbon                      on 15m and 1h: EMAs 8, 13, 21, 34, 55 (in order up /
                                                      down / tangled, width, widening or compressing, last
                                                      full re-order) and the Guppy short group (3-15) against
                                                      the long group (30-60)
  mavg_sr  Moving averages as support and resistance  on 15m, 1h, 4h, 1d: nearest average below / above price,
                                                      whether one is being tested on this bar, the last test
                                                      (held or broke) and each average's respect record

WHAT IS NEW HERE. indicators.trend_score (the "Timeframe strength" card) already folds EMA/SMA 5-200
position, stack and slope into one -1..+1 number per timeframe. These cards keep the parts that number
hides: the actual average prices, distances, crosses, the ribbon's shape and the averages as levels.

THE ONE RULE. Row i uses only bars that had CLOSED by the close of 15m bar i. 15m readings are rolling or
recursive, backward only. 1h / 4h / 1d readings are computed on resampled bars (data.resample's convention:
keyed by OPEN time) and handed to a 15m row only once that higher bar has CLOSED, exactly as
data.htf_on_15 does (the same "last bar closed by my close" lookup, done once per timeframe as row
positions). tests/test_mavg.py cuts the future off and checks every column.

UNITS. "ATR" is Wilder's ATR(14) of the SAME timeframe as the reading (a 4h distance is in 4h ATRs).
EMAs are indicators.ema_seeded (seeded with the SMA of the first N closes, reported after 2 x N bars, as
the trend map does); SMAs are indicators.sma. Features are dimensionless, about [-1, 1], 0.0 = no read;
readable columns (RAW) are prices, ATRs, counts and ages in bars of their own timeframe, NaN = no read.
The whole frame (31 features, 217 readable columns) is float32, to keep it small: about 35 MB a year of
15m rows; evidence.matrix turns the features into float64 as it does for every source.

No reading here is claimed to predict anything. Docs: docs/SOURCES_mavg.md.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

# =====================================================================================
# THE ONE CONSTANT BLOCK. Conventional values, declared once, none tuned against outcomes.
# =====================================================================================
BAR_MS = 900000
TFS = OrderedDict([("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D")])   # tag -> pandas rule
PERIOD_MS = {"1h": 3600000, "4h": 14400000, "1D": 86400000}
ATR_N = 14
# ---- mavg
LENGTHS = (5, 10, 20, 50, 200)
FAMS = ("sma", "ema")
AVGS = [(f, n) for f in FAMS for n in LENGTHS]          # an average's id is its position here (0-9)
SLOPE_LENGTHS = (20, 50, 200)                            # slopes kept for these (the 5 and 10 move with every bar)
SLOPE_BARS = 3                                           # slope = change over the timeframe's last 3 bars, in ATR
CROSSES = OrderedDict([                                  # name -> (fast, slow); None = the close itself
    ("e5_10", (("ema", 5), ("ema", 10))),
    ("e10_20", (("ema", 10), ("ema", 20))),
    ("e20_50", (("ema", 20), ("ema", 50))),
    ("s50_200", (("sma", 50), ("sma", 200))),            # golden cross (up) / death cross (down)
    ("p_e20", (None, ("ema", 20))),
    ("p_s200", (None, ("sma", 200))),
])
CROSS_W = {"e5_10": 1.0, "e10_20": 1.0, "e20_50": 2.0, "s50_200": 3.0, "p_e20": 1.0, "p_s200": 2.0}
CROSS_FADE = 12                                          # a cross fades to nothing over 12 bars of its timeframe
D200_SCALE = 4.0                                         # distance from the 200 SMA: tanh(ATRs / 4)
SLOPE_SCALE = 0.5                                        # slope of the 50: tanh(ATRs per 3 bars / 0.5)
MIN_AVGS = 5                                             # "above k of n" needs at least 5 averages that exist
# ---- ribbon
RIBBON = (8, 13, 21, 34, 55)                             # Fibonacci lengths
GMMA_SHORT = (3, 5, 8, 10, 12, 15)                       # Guppy multiple moving average, short (traders') group
GMMA_LONG = (30, 35, 40, 45, 50, 60)                     # ... and long (investors') group
RB_TFS = ("15m", "1h")
RB_CHG_BARS = 4                                          # widening / compressing = width change over 4 bars
RB_WIDTH_SCALE = 3.0                                     # tanh(width in ATR / 3)
RB_EXP_SCALE = 0.5                                       # tanh(width change in ATR / 0.5)
RB_STEADY = 0.05                                         # |width change| below 0.05 ATR reads "steady"
GMMA_SCALE = 2.0                                         # tanh(separation in ATR / 2)
# ---- mavg_sr
SR_CANDS = [("ema", 20), ("sma", 20), ("ema", 50), ("sma", 50), ("ema", 200), ("sma", 200)]   # rising priority
TOUCH_ATR = 0.25                                         # a test: the bar's low (high) within 0.25 ATR of the average
FAR_ATR = 0.5                                            # ... counted only after a close at least 0.5 ATR away
RESPECT_N = {"15m": 20, "1h": 20, "4h": 12, "1d": 10}    # the respect record covers the last N counted tests
MIN_TESTS = 3                                            # a hold rate needs 3 tests on record
ROOM_CAP = 3.0                                           # room to the nearest average, capped at 3 ATR
CONFL_ATR = 0.25                                         # confluence: within 0.25 of the 1-HOUR ATR (fib.py's rule)
DECIMALS = {"BTCUSDT": 0, "ETHUSDT": 2, "XAUUSD": 2, "XAGUSD": 3, "USDJPY": 3, "SPX": 2}
# =====================================================================================

GROUPS = OrderedDict([
    ("mavg", ("Moving averages (SMA and EMA 5-200)",
              ["ma_share_1h", "ma_share_4h", "ma_share_1d", "ma_stack_1h", "ma_stack_4h", "ma_stack_1d",
               "ma_cross_1h", "ma_cross_4h", "ma_cross_1d", "ma_d200_4h", "ma_d200_1d",
               "ma_slope50_4h", "ma_slope50_1d"])),
    ("ribbon", ("Moving-average ribbon",
                ["rb_order_15m", "rb_order_1h", "rb_width_15m", "rb_width_1h", "rb_expand_15m", "rb_expand_1h",
                 "rb_pos_15m", "rb_pos_1h", "rb_gmma_15m", "rb_gmma_1h"])),
    ("mavg_sr", ("Moving averages as support and resistance",
                 ["mas_room_1h", "mas_room_4h", "mas_test_15m", "mas_test_1h", "mas_test_4h",
                  "mas_hold_15m", "mas_hold_1h", "mas_hold_4h"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]


def _key(f, n):
    return "%s%d" % (f, n)


_RAW = OrderedDict([("mavg", ["ma_close"]), ("ribbon", []), ("mavg_sr", [])])
for _tf in TFS:
    _RAW["mavg"] += ["ma_%s_atr" % _tf] + ["ma_%s_%s_px" % (_tf, _key(f, n)) for f, n in AVGS]
    _RAW["mavg"] += ["ma_%s_%s_slope" % (_tf, _key(f, n)) for f, n in AVGS if n in SLOPE_LENGTHS]
    _RAW["mavg"] += ["ma_%s_x_%s_%s" % (_tf, x, s) for x in CROSSES for s in ("age", "px")]
    _RAW["mavg_sr"] += ["mas_%s_%s" % (_tf, s) for s in ("touch_id", "touch_side", "touch_held",
                                                          "last_id", "last_side", "last_held", "last_age")]
    _RAW["mavg_sr"] += ["mas_%s_%s_%s" % (_tf, _key(f, n), s) for f, n in SR_CANDS for s in ("held", "tests")]
for _tf in RB_TFS:
    _RAW["ribbon"] += ["rb_%s_e%d_px" % (_tf, n) for n in RIBBON]
    _RAW["ribbon"] += ["rb_%s_%s" % (_tf, s) for s in ("width", "wchg", "reorder_age", "reorder_dir",
                                                        "gmma_sep", "gmma_overlap", "gmma_x_age")]
RAW = [c for cols in _RAW.values() for c in cols]
"""Readable columns. ma_{tf}_{sma|ema}{n}_px: the averages; ma_{tf}_atr: that timeframe's ATR(14);
ma_{tf}_{avg}_slope: change over 3 bars in ATR; ma_{tf}_x_{cross}_age / _px: bars since the cross and
the price there (its direction is today's order of the two lines). rb_{tf}_e{n}_px: ribbon lines;
width in ATR, wchg = width change over 4 bars; reorder = the last bar the five lines became fully
ordered (+1 up / -1 down); gmma_sep: short-group mean minus long-group mean in ATR; overlap 1 = the
groups are interwoven. mas_{tf}_touch_*: the average tested on this bar (id = position in AVGS, side
+1 = from above / support, held 1 = closed back on its side); mas_{tf}_last_*: the last COUNTED test;
mas_{tf}_{avg}_held / _tests: its record over the last RESPECT_N counted tests."""


def update(log=print):
    """Nothing to fetch: every reading comes from the 15m bars the engine already keeps."""
    return {}


# ------------------------------------------------------------------ small causal helpers
def _hbars(b, rule):
    """15m bars -> higher-timeframe bars keyed by OPEN time (data.resample's convention, OHLC only)."""
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def closed_positions(ms15, tf_open_ms, rule):
    """For every 15m bar (open times ms15): the position of the last `rule` bar that had CLOSED by the
    15m bar's own close, -1 if none. The same lookup as data.htf_on_15 (tests check it)."""
    closed_at = np.asarray(tf_open_ms, dtype="int64") + PERIOD_MS[rule]
    return np.searchsorted(closed_at, np.asarray(ms15, dtype="int64") + BAR_MS, side="right") - 1


def _shift(x, k=1):
    out = np.empty_like(x)
    out[:k] = np.nan
    out[k:] = x[:-k]
    return out


def _since(flag):
    """-> (bars since the last True, NaN before the first; row of that last True, -1 before)."""
    rows = np.arange(len(flag))
    last = np.maximum.accumulate(np.where(flag, rows, -1)) if len(flag) else rows
    age = (rows - last).astype(float)
    age[last < 0] = np.nan
    return age, last


def _last_before(flag):
    """Row of the last True strictly before each row, -1 if none."""
    rows = np.arange(len(flag))
    last = np.maximum.accumulate(np.where(flag, rows, -1))
    out = np.empty_like(last)
    out[0] = -1
    out[1:] = last[:-1]
    return out


def _gather(values, rows):
    """values[rows] with -1 -> NaN."""
    v = np.asarray(values, dtype=float)
    return np.where(rows >= 0, v[np.maximum(rows, 0)], np.nan)


def _ratio(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.isfinite(b) & (b > 0), a / np.where(b > 0, b, 1.0), np.nan)


def ma_tests(high, low, close, avg, atr, touch_atr=TOUCH_ATR, far_atr=FAR_ATR):
    """Tests of one average on one timeframe's bars. A bar TOUCHES the average from above when the
    previous close was above it and the bar's low came within touch_atr ATR of it (or through it);
    from below, the mirror. It HELD when the bar closed back on its side (or on the line), else it
    broke. A touch is COUNTED as a test only if some close at least far_atr ATR from the average came
    after the previous touch (so hugging the line is one test, not many). Equivalently: the last far
    close before the bar is later than the last touch before it.
    -> (touch, side +1 from above / -1 from below / 0, held, counted test), all on the bar's own close."""
    pc, pa = _shift(close), _shift(avg)
    with np.errstate(invalid="ignore"):
        sup = (pc > pa) & (low <= avg + touch_atr * atr)
        res = (pc < pa) & (high >= avg - touch_atr * atr)
        touch = sup | res
        held = touch & np.where(sup, close >= avg, close <= avg)
        far = np.abs(close - avg) >= far_atr * atr
    test = touch & (_last_before(far) > _last_before(touch))
    return touch, sup.astype(float) - res.astype(float), held, test


def respect(test, held, n):
    """Over the last n COUNTED tests up to each bar: (held, tests)."""
    k = np.cumsum(test)
    cum = np.concatenate([[0], np.cumsum(held[test].astype(float))])
    lo = np.maximum(k - n, 0)
    return cum[k] - cum[lo], np.minimum(k, n).astype(float)


# ------------------------------------------------------------------ one timeframe's shared inputs
class _TF(object):
    def __init__(self, df):
        self.df = df
        self.n = len(df)
        self.c, self.h, self.l = (df[x].values.astype(float) for x in ("close", "high", "low"))
        atr = _ind.atr_wilder(df, ATR_N).values.astype(float)
        self.atr = np.where(np.isfinite(atr) & (atr > 0), atr, np.nan)
        close = df["close"].astype(float)
        self.avg = {}
        for f, n in AVGS:
            s = _ind.sma(close, n) if f == "sma" else _ind.ema_seeded(close, n)
            self.avg[(f, n)] = s.values.astype(float)
        self.close = close


# ------------------------------------------------------------------ card 1: the averages
def _card_mavg(tf, x, put, feat):
    c, atr = x.c, x.atr
    put("ma_%s_atr" % tf, atr)
    above, below, have = np.zeros(x.n), np.zeros(x.n), np.zeros(x.n)
    for f, n in AVGS:
        a = x.avg[(f, n)]
        put("ma_%s_%s_px" % (tf, _key(f, n)), a)
        with np.errstate(invalid="ignore"):
            above += c > a
            below += c < a
        have += np.isfinite(a)
        if n in SLOPE_LENGTHS:
            put("ma_%s_%s_slope" % (tf, _key(f, n)), _ratio(a - _shift(a, SLOPE_BARS), atr))
    with np.errstate(divide="ignore", invalid="ignore"):
        feat("ma_share_" + tf, np.where(have >= MIN_AVGS, (above - below) / np.maximum(have, 1), np.nan))
    fam_scores = []
    for f in FAMS:
        score, ok = np.zeros(x.n), np.ones(x.n, dtype=bool)
        for a, b in zip(LENGTHS[:-1], LENGTHS[1:]):
            va, vb = x.avg[(f, a)], x.avg[(f, b)]
            ok &= np.isfinite(va) & np.isfinite(vb)
            score += np.sign(np.nan_to_num(va - vb))
        fam_scores.append(np.where(ok, score / 4.0, np.nan))
    both = np.vstack(fam_scores)
    cnt = np.isfinite(both).sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        feat("ma_stack_" + tf, np.where(cnt > 0, np.nansum(both, axis=0) / np.maximum(cnt, 1), np.nan))

    sig, wsum = np.zeros(x.n), 0.0
    for name, (fast, slow) in CROSSES.items():
        fv = c if fast is None else x.avg[fast]
        sv = x.avg[slow]
        pf, ps = _shift(fv), _shift(sv)
        with np.errstate(invalid="ignore"):
            up = (fv > sv) & (pf <= ps)
            dn = (fv < sv) & (pf >= ps)
        age, last = _since(up | dn)
        at_px = sv if fast is None else 0.5 * (fv + sv)
        put("ma_%s_x_%s_age" % (tf, name), age)
        put("ma_%s_x_%s_px" % (tf, name), _gather(at_px, last))
        direction = _gather(up.astype(float) - dn.astype(float), last)
        with np.errstate(invalid="ignore"):
            fade = np.clip(1.0 - age / float(CROSS_FADE), 0.0, 1.0)
        sig += CROSS_W[name] * np.where(np.isfinite(age), direction * fade, 0.0)
        wsum += CROSS_W[name]
    feat("ma_cross_" + tf, np.clip(sig / wsum, -1.0, 1.0))
    feat("ma_d200_" + tf, np.tanh(_ratio(c - x.avg[("sma", 200)], atr) / D200_SCALE))
    s50 = [_ratio(x.avg[(f, 50)] - _shift(x.avg[(f, 50)], SLOPE_BARS), atr) for f in FAMS]
    feat("ma_slope50_" + tf, np.tanh(0.5 * (s50[0] + s50[1]) / SLOPE_SCALE))


# ------------------------------------------------------------------ card 2: the ribbon
def _card_ribbon(tf, x, put, feat):
    if tf not in RB_TFS:
        return
    c, atr = x.c, x.atr
    lines = np.vstack([_ind.ema_seeded(x.close, n).values.astype(float) for n in RIBBON])
    for n, v in zip(RIBBON, lines):
        put("rb_%s_e%d_px" % (tf, n), v)
    ok = np.isfinite(lines).all(axis=0)
    with np.errstate(invalid="ignore"):
        d = np.diff(lines, axis=0)                         # each line minus the one before (longer minus shorter)
        ups, dns = (d < 0).sum(axis=0), (d > 0).sum(axis=0)
    order = np.where(ok, (ups - dns) / 4.0, np.nan)
    state = np.where(ok, np.where(ups == 4, 1.0, np.where(dns == 4, -1.0, 0.0)), np.nan)
    top = np.where(ok, lines.max(axis=0), np.nan)
    bot = np.where(ok, lines.min(axis=0), np.nan)
    width = _ratio(top - bot, atr)
    wchg = width - _shift(width, RB_CHG_BARS)
    dirn = np.sign(lines[0] - lines[-1])
    put("rb_%s_width" % tf, width)
    put("rb_%s_wchg" % tf, wchg)
    feat("rb_order_" + tf, order)
    feat("rb_width_" + tf, dirn * np.tanh(width / RB_WIDTH_SCALE))
    feat("rb_expand_" + tf, dirn * np.tanh(wchg / RB_EXP_SCALE))
    with np.errstate(divide="ignore", invalid="ignore"):
        span = top - bot
        pos = np.where(span > 0, 2.0 * (c - bot) / np.where(span > 0, span, 1.0) - 1.0, 0.0)
    feat("rb_pos_" + tf, np.where(ok, np.clip(pos, -2.0, 2.0) / 2.0, np.nan))
    prev = _shift(state)
    with np.errstate(invalid="ignore"):
        ev = np.isfinite(prev) & (state != 0) & (state != prev)
    age, last = _since(ev)
    put("rb_%s_reorder_age" % tf, age)
    put("rb_%s_reorder_dir" % tf, _gather(state, last))

    del lines, d, top, bot, pos, span
    groups = []
    for lengths in (GMMA_SHORT, GMMA_LONG):                    # running mean / min / max: no stack of twelve lines
        tot, lo, hi = np.zeros(x.n), np.full(x.n, np.inf), np.full(x.n, -np.inf)
        for n in lengths:
            v = _ind.ema_seeded(x.close, n).values.astype(float)
            tot += v
            lo, hi = np.fmin(lo, v), np.fmax(hi, v)
        groups.append((tot / len(lengths), lo, hi))            # NaN anywhere in the group -> NaN mean
    (s_mean, s_lo, s_hi), (l_mean, l_lo, l_hi) = groups
    gok = np.isfinite(s_mean) & np.isfinite(l_mean)
    gap = np.where(gok, s_mean - l_mean, np.nan)
    sep = _ratio(gap, atr)
    with np.errstate(invalid="ignore"):
        overlap = np.where(gok, ((s_lo < l_hi) & (s_hi > l_lo)).astype(float), np.nan)
        pg = _shift(gap)
        gx = ((gap > 0) & (pg <= 0)) | ((gap < 0) & (pg >= 0))
    put("rb_%s_gmma_sep" % tf, sep)
    put("rb_%s_gmma_overlap" % tf, overlap)
    put("rb_%s_gmma_x_age" % tf, _since(gx)[0])
    feat("rb_gmma_" + tf, np.tanh(sep / GMMA_SCALE))


# ------------------------------------------------------------------ card 3: averages as support and resistance
def _card_sr(tf, x, put, feat):
    c, atr, n = x.c, x.atr, x.n
    rows = np.arange(n)
    ids = [AVGS.index(s_) for s_ in SR_CANDS]
    best_score, t_id = np.zeros(n), np.full(n, np.nan)          # the average touched on this bar (running pick)
    t_side, t_held, t_hn, t_tn = np.zeros(n), np.zeros(n, dtype=bool), np.zeros(n), np.zeros(n)
    last_row, l_id = np.full(n, -1), np.full(n, np.nan)          # the last COUNTED test (running pick)
    l_side, l_held = np.full(n, np.nan), np.full(n, np.nan)
    sup_px, res_px = np.full(n, np.nan), np.full(n, np.nan)
    for k, (f, ln) in enumerate(SR_CANDS):
        a = x.avg[(f, ln)]
        touch, side, held, test = ma_tests(x.h, x.l, c, a, atr)
        hn, tn = respect(test, held, RESPECT_N[tf])
        fin = np.isfinite(a)
        put("mas_%s_%s_held" % (tf, _key(f, ln)), np.where(fin, hn, np.nan))
        put("mas_%s_%s_tests" % (tf, _key(f, ln)), np.where(fin, tn, np.nan))
        score = np.where(touch, 100.0 * held + k + 1, 0.0)       # a touch that held first, then the longer average
        better = score > best_score
        best_score[better], t_id[better], t_side[better], t_held[better] = score[better], ids[k], side[better], held[better]
        t_hn[better], t_tn[better] = hn[better], tn[better]
        lr = np.maximum.accumulate(np.where(test, rows, -1))
        newer = (lr >= 0) & (lr >= last_row)
        last_row[newer], l_id[newer] = lr[newer], ids[k]
        l_side[newer], l_held[newer] = side[lr[newer]], held[lr[newer]]
        with np.errstate(invalid="ignore"):
            below, above = a < c, a > c
            sup_px = np.where(below & ~(sup_px >= a), a, sup_px)
            res_px = np.where(above & ~(res_px <= a), a, res_px)
        del touch, side, held, test, hn, tn, score, better, lr, newer
    has = np.isfinite(t_id)
    put("mas_%s_touch_id" % tf, t_id)
    put("mas_%s_touch_side" % tf, np.where(has, t_side, np.nan))
    put("mas_%s_touch_held" % tf, np.where(has, t_held.astype(float), np.nan))
    put("mas_%s_last_id" % tf, l_id)
    put("mas_%s_last_side" % tf, l_side)
    put("mas_%s_last_held" % tf, l_held)
    put("mas_%s_last_age" % tf, np.where(last_row >= 0, (rows - last_row).astype(float), np.nan))

    e20, e50 = x.avg[("ema", 20)], x.avg[("ema", 50)]
    with np.errstate(invalid="ignore"):
        rising = e50 - _shift(e50, SLOPE_BARS)
        up, down = (e20 > e50) & (rising > 0), (e20 < e50) & (rising < 0)
        holding = has & t_held
        feat("mas_test_" + tf, np.where(holding & (t_side > 0) & up, 1.0, np.where(holding & (t_side < 0) & down, -1.0, 0.0)))
        rate = np.where(t_tn >= MIN_TESTS, t_hn / np.maximum(t_tn, 1.0) - 0.5, 0.0)
        feat("mas_hold_" + tf, np.where(holding, t_side * rate, 0.0))
        d_sup = np.minimum(np.nan_to_num(_ratio(c - sup_px, atr), nan=ROOM_CAP), ROOM_CAP)
        d_res = np.minimum(np.nan_to_num(_ratio(res_px - c, atr), nan=ROOM_CAP), ROOM_CAP)
        any_avg = np.isfinite(atr) & (np.isfinite(sup_px) | np.isfinite(res_px))
    feat("mas_room_" + tf, np.where(any_avg, (d_res - d_sup) / ROOM_CAP, np.nan))


_CARDS = OrderedDict([("mavg", _card_mavg), ("ribbon", _card_ribbon), ("mavg_sr", _card_sr)])


# ------------------------------------------------------------------ features
def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature in GROUPS (0.0 = no read, never NaN)
    and the readable RAW columns (NaN = no read), all float32 to keep the frame small. bars: the asset's 15m frame
    (data.load(asset) when None). Readings are made on the bars, then handed to the index row with the
    same open time; an index row without a bar is "no read". A card that cannot be built is "no read";
    the reason is in .attrs["errors"]."""
    index15 = pd.DatetimeIndex(index15)
    m = len(index15)
    fcol = dict((c_, j) for j, c_ in enumerate(FEATURES))
    rcol = dict((c_, j) for j, c_ in enumerate(RAW))
    block = np.full((m, len(FEATURES) + len(RAW)), np.nan, dtype=np.float32, order="F")   # one float32 block, no copies
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
        R[hit, rcol["ma_close"]] = b["close"].values[at]
        for tf, rule in TFS.items():
            try:
                df = b if rule is None else _hbars(b, rule)
                if not len(df):
                    continue
                sel = at if rule is None else closed_positions(ms, _data.to_ms(df.index), rule)[at]
                x = _TF(df)
            except Exception as ex:                                # pragma: no cover
                errors[tf] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
                continue

            def put(name, arr, _sel=sel):
                R[hit, rcol[name]] = _gather(arr, _sel)

            def feat(name, arr, _sel=sel):
                j = fcol.get(name)
                if j is not None:
                    F[hit, j] = _gather(arr, _sel)

            for card, fn in _CARDS.items():
                if card in errors:
                    continue
                try:
                    fn(tf, x, put, feat)
                except Exception as ex:                            # a card that breaks is "no read", not a crash
                    errors[card] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
            del x
        for card in _CARDS:
            if card in errors:
                F[:, [fcol[c_] for c_ in GROUPS[card][1]]] = np.nan
                R[:, [rcol[c_] for c_ in _RAW[card]]] = np.nan
    F[~np.isfinite(F)] = 0.0
    out = pd.DataFrame(block, index=index15, columns=FEATURES + RAW, copy=False)
    out.attrs["errors"] = errors
    return out


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


def _nm(f, n):
    return "%s %d" % (f.upper(), n)


def _nm200(f, n):
    """'the 200 SMA' style for the long averages, 'the EMA 20' for the rest."""
    return "the %d %s" % (n, f.upper()) if n == 200 else "the %s" % _nm(f, n)


def _bars(k):
    k = int(round(k))
    return "%d bar%s" % (k, "" if k == 1 else "s")


def _ago(k):
    """'6 bars ago', or 'on the last closed bar' for 0."""
    return "on the last closed bar" if int(round(k)) == 0 else _bars(k) + " ago"


def _tf_read(row, tf):
    """The averages of one timeframe as numbers a person can read."""
    r = {"tf": tf, "c": _num(row, "ma_close"), "atr": _num(row, "ma_%s_atr" % tf)}
    r["px"] = dict(((f, n), _num(row, "ma_%s_%s_px" % (tf, _key(f, n)))) for f, n in AVGS)
    c = r["c"]
    have = [v for v in r["px"].values() if v is not None]
    r["n"] = len(have)
    r["above"] = None if c is None or len(have) < MIN_AVGS else sum(1 for v in have if c > v)
    r["stacks"] = {}
    for f in FAMS:
        vals = [r["px"][(f, n)] for n in LENGTHS]
        if None in vals:
            r["stacks"][f] = None
            continue
        bull = [(a, b_) for (a, va), (b_, vb) in zip(zip(LENGTHS, vals), zip(LENGTHS[1:], vals[1:])) if va > vb]
        bear = [(a, b_) for (a, va), (b_, vb) in zip(zip(LENGTHS, vals), zip(LENGTHS[1:], vals[1:])) if va < vb]
        if len(bull) == 4:
            r["stacks"][f] = ("fully bullish", [])
        elif len(bear) == 4:
            r["stacks"][f] = ("fully bearish", [])
        else:
            pairs = list(zip(LENGTHS[:-1], LENGTHS[1:]))
            if len(bull) >= len(bear):
                breaks = [("%s %d under %d" % (f.upper(), a, b_)) for a, b_ in pairs if (a, b_) not in bull]
            else:
                breaks = [("%s %d over %d" % (f.upper(), a, b_)) for a, b_ in pairs if (a, b_) not in bear]
            r["stacks"][f] = ("mixed", breaks)
    r["crosses"] = OrderedDict()
    for name, (fast, slow) in CROSSES.items():
        age, px = _num(row, "ma_%s_x_%s_age" % (tf, name)), _num(row, "ma_%s_x_%s_px" % (tf, name))
        fv = c if fast is None else r["px"][fast]
        sv = r["px"][slow]
        way = None if fv is None or sv is None or fv == sv else ("up" if fv > sv else "down")
        r["crosses"][name] = None if age is None or way is None else (age, px, way)
    return r


def _stack_words(r):
    s, e = r["stacks"].get("sma"), r["stacks"].get("ema")
    if s is None and e is None:
        return "stack not known yet"
    if s is not None and e is not None and s[0] == e[0] and s[0] != "mixed":
        return "both stacks %s" % s[0]
    bits = []
    for f, st in (("EMA", e), ("SMA", s)):
        if st is None:
            continue
        bits.append("%s stack %s%s" % (f, st[0], "" if not st[1] else " (%s)" % ", ".join(st[1][:2])))
    return ", ".join(bits)


def _cross_words(name, cr, asset, tf=""):
    age, px, way = cr
    pre = (tf + " ") if tf else ""
    if name == "s50_200":
        what = "%s%s (SMA 50 %s 200)" % (pre, "golden cross" if way == "up" else "death cross", "over" if way == "up" else "under")
        return "%s %s at %s" % (what, _ago(age), _px(px, asset))
    if name.startswith("p_"):
        f, n = CROSSES[name][1]
        return "%sprice crossed %s %s %s at %s" % (pre, "above" if way == "up" else "below", _nm200(f, n), _ago(age), _px(px, asset))
    (f1, n1), (f2, n2) = CROSSES[name]
    return "%s%s %d/%d crossed %s %s at %s" % (pre, f1.upper(), n1, n2, way, _ago(age), _px(px, asset))


def _dist(c, v, atr):
    """(percent, ATRs) of the close from a level; None where unknown."""
    if c is None or v is None or not v:
        return None, None
    return 100.0 * (c - v) / v, (None if not atr else (c - v) / atr)


def _dist_words(c, v, atr, asset, label):
    pct, xa = _dist(c, v, atr)
    if pct is None:
        return "%s n/a" % label
    side = "above" if c >= v else "below"
    amt = ("%.1f ATR (%.2f%%)" % (abs(xa), abs(pct))) if xa is not None else "%.2f%%" % abs(pct)
    return "%s %s %s (%s)" % (amt, side, label, _px(v, asset))


def _mavg_segment(r, asset):
    if r["above"] is None:
        return "%s: not enough closed bars yet" % r["tf"]
    bits = ["price above %d of %d averages" % (r["above"], r["n"]), _stack_words(r)]
    young = [(cr[0], name, cr) for name, cr in r["crosses"].items() if cr and name in ("e10_20", "e20_50", "s50_200", "p_s200")]
    if young:
        _a, name, cr = min(young)
        bits.append(_cross_words(name, cr, asset))
    s200 = r["px"][("sma", 200)]
    if s200 is not None:
        bits.append(_dist_words(r["c"], s200, r["atr"], asset, "the 200 SMA"))
    return "%s: %s" % (r["tf"], ", ".join(bits))


def _ribbon_read(row, tf):
    r = {"tf": tf, "c": _num(row, "ma_close"), "atr": _num(row, "ma_%s_atr" % tf)}
    r["lines"] = [_num(row, "rb_%s_e%d_px" % (tf, n)) for n in RIBBON]
    for k in ("width", "wchg", "reorder_age", "reorder_dir", "gmma_sep", "gmma_overlap", "gmma_x_age"):
        r[k] = _num(row, "rb_%s_%s" % (tf, k))
    ln = r["lines"]
    if None in ln:
        r["state"] = None
    else:
        d = np.diff(ln)
        r["state"] = "up" if (d < 0).all() else "down" if (d > 0).all() else "tangled"
    r["above"] = None if r["c"] is None or None in ln else sum(1 for v in ln if r["c"] > v)
    return r


def _ribbon_words(r):
    if r["state"] is None or r["width"] is None:
        return "%s ribbon not formed yet" % r["tf"]
    s = "%s ribbon" % r["tf"]
    if r["state"] == "tangled":
        s += " tangled"
    else:
        s += " in order %s" % r["state"]
        if r["reorder_age"] is not None and r["reorder_dir"] == (1.0 if r["state"] == "up" else -1.0):
            s += " for %s" % _bars(r["reorder_age"])
    w = r["wchg"]
    s += ", %s" % ("steady" if w is None or abs(w) < RB_STEADY else "widening" if w > 0 else "compressing")
    s += ", %.1f ATR wide" % r["width"]
    a = r["above"]
    s += "; price %s" % ("above all five lines" if a == 5 else "below all five lines" if a == 0 else "above %d of 5 lines" % a)
    if r["gmma_sep"] is not None:
        sep = r["gmma_sep"]
        s += "; Guppy short group %.1f ATR %s the long group" % (abs(sep), "above" if sep >= 0 else "below")
        if r["gmma_overlap"]:
            s += " but the groups are interwoven (crossing)"
        elif r["gmma_x_age"] is not None:
            s += ", apart since they crossed %s ago" % _bars(r["gmma_x_age"])
    return s


def _sr_read(row, tf):
    r = {"tf": tf, "c": _num(row, "ma_close"), "atr": _num(row, "ma_%s_atr" % tf)}
    px = dict(((f, n), _num(row, "ma_%s_%s_px" % (tf, _key(f, n)))) for f, n in SR_CANDS)
    c = r["c"]
    below = [(v, k) for k, v in px.items() if v is not None and c is not None and v < c]
    above = [(v, k) for k, v in px.items() if v is not None and c is not None and v > c]
    r["sup"] = max(below) if below else None
    r["res"] = min(above) if above else None
    r["px"] = px
    for k in ("touch_id", "touch_side", "touch_held", "last_id", "last_side", "last_held", "last_age"):
        r[k] = _num(row, "mas_%s_%s" % (tf, k))
    r["rec"] = dict(((f, n), (_num(row, "mas_%s_%s_held" % (tf, _key(f, n))), _num(row, "mas_%s_%s_tests" % (tf, _key(f, n)))))
                    for f, n in SR_CANDS)
    return r


def _avg_of(idv):
    return None if idv is None else AVGS[int(idv)]


def _record_words(rec):
    h, t = rec
    if not t:
        return "no earlier counted tests on record"
    return "it held %d of its last %d tests" % (int(h), int(t))


def confluence(row, price, asset, skip=None):
    """Levels within CONFL_ATR of the 1-hour ATR from `price`, read from the evidence row when present:
    support / resistance (levels.py), Fibonacci levels (fib.py) and the other timeframes' averages.
    -> list of (words, price), nearest first."""
    atr = _num(row, "ma_1h_atr")
    if price is None or not atr:
        return []
    near = []

    def consider(label, v):
        if v is not None and abs(v - price) <= CONFL_ATR * atr:
            near.append((abs(v - price), label, v))

    for col, label in (("sup_px", "a horizontal support"), ("res_px", "a horizontal resistance"),
                       ("pd_high", "the prior-day high"), ("pd_low", "the prior-day low"), ("pd_close", "the prior-day close"),
                       ("pw_high", "the prior-week high"), ("pw_low", "the prior-week low"), ("round_px", "the round number")):
        consider(label, _num(row, col))
    seen = set()
    for tf in ("1h", "4h", "1d"):
        if not _num(row, "fib_%s_dir" % tf):
            continue
        for col, name in (("r236_px", "0.236"), ("r382_px", "0.382"), ("r500_px", "0.5"), ("entry_px", "0.618"),
                          ("inval_px", "0.786"), ("t1_px", "1.272"), ("t2_px", "1.618")):
            v = _num(row, "fib_%s_%s" % (tf, col))
            if v is not None and (name, round(v, 8)) not in seen:
                seen.add((name, round(v, 8)))
                consider("the %s %s Fib" % (tf, name), v)
    for tf in TFS:
        for f, n in SR_CANDS:
            if skip == (tf, f, n):
                continue
            consider("the %s %s" % (tf, _nm(f, n)), _num(row, "ma_%s_%s_px" % (tf, _key(f, n))))
    near.sort()
    return [(label, v) for _d, label, v in near]


def _confl_words(items, asset, limit=3):
    if not items:
        return ""
    words = ["%s (%s)" % (label, _px(v, asset)) for label, v in items[:limit]]
    s = "it sits with " + (words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1])
    if len(items) >= 2:
        s += " (%d levels stacked within %.2f ATR)" % (len(items) + 1, CONFL_ATR)
    return s


def _sr_test_words(r, row, asset):
    """'1h: testing the EMA 50 (74,020) from above; it held 7 of its last 9 tests; it sits with ...'"""
    fa = _avg_of(r["touch_id"])
    if fa is None:
        return None
    v = r["px"].get(fa)
    tag = r["tf"] if r["tf"] in ("15m", "1h") else "%s (last closed bar)" % r["tf"]
    if r["touch_held"]:
        s = "%s: testing %s (%s) from %s" % (tag, _nm200(*fa), _px(v, asset), "above" if r["touch_side"] > 0 else "below")
    else:
        s = "%s: closed through %s (%s), %s" % (tag, _nm200(*fa), _px(v, asset), "downward" if r["touch_side"] > 0 else "upward")
    s += "; " + _record_words(r["rec"][fa])
    cw = _confl_words(confluence(row, v, asset, skip=(r["tf"],) + fa), asset)
    return s + ("; " + cw if cw else "")


def _near_words(r, asset):
    bits = []
    for key, word in (("sup", "support"), ("res", "resistance")):
        if r[key] is None:
            bits.append("no average %s price" % ("below" if key == "sup" else "above"))
            continue
        v, fa = r[key]
        pct, xa = _dist(r["c"], v, r["atr"])
        bits.append("%s %s at %s (%s%.2f%% %s)" % (word, _nm(*fa), _px(v, asset), "" if xa is None else "%.1f ATR, " % abs(xa),
                                                  abs(pct), "below" if key == "sup" else "above"))
    return "%s %s" % (r["tf"], ", ".join(bits))


def _last_test_words(r):
    fa = _avg_of(r["last_id"])
    if fa is None or r["last_age"] is None:
        return "no counted test yet"
    return "%s %s from %s %s" % (_nm(*fa), "held" if r["last_held"] else "broke",
                                  "above" if r["last_side"] > 0 else "below", _ago(r["last_age"]))


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    coin, say = asset.replace("USDT", ""), OrderedDict()

    segs = [_tf_read(row, tf) for tf in ("1h", "4h", "1d")]
    title = GROUPS["mavg"][0]
    if all(s["above"] is None for s in segs):
        say[title] = "No read: not enough closed %s bars for the averages." % coin
    else:
        say[title] = "; ".join(_mavg_segment(s, asset) for s in segs) + "."

    title = GROUPS["ribbon"][0]
    r1, r15 = _ribbon_read(row, "1h"), _ribbon_read(row, "15m")
    if r1["state"] is None and r15["state"] is None:
        say[title] = "No read: the %s ribbon has not formed yet." % coin
    else:
        s = _ribbon_words(r1)
        if r15["state"] is not None:
            s += "; %s ribbon %s, %.1f ATR wide" % ("15m", "tangled" if r15["state"] == "tangled" else "in order " + r15["state"],
                                                   r15["width"] or 0.0)
        say[title] = s + "."

    title = GROUPS["mavg_sr"][0]
    reads = [_sr_read(row, tf) for tf in TFS]
    if all(r["sup"] is None and r["res"] is None for r in reads):
        say[title] = "No read: not enough closed %s bars for the averages." % coin
    else:
        tests = [w for w in (_sr_test_words(r, row, asset) for r in reversed(reads)) if w]
        near = [_near_words(r, asset) for r in reads if r["tf"] in ("1h", "4h") and (r["sup"] or r["res"])]
        if tests:
            s = tests[0]
            if len(tests) > 1:
                s += "; also " + "; ".join(t.split("; ")[0] for t in tests[1:3])
            if near:
                s += "; nearest averages: " + near[0]
        else:
            s = "No average is being tested on this bar; nearest averages: " + "; ".join(near)
            lt = reads[1]
            s += "; last 1h test: " + _last_test_words(lt)
        say[title] = s + "."
    return say


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: prices, distances, counts and ages
    a person can read (never a scaled model number). Four to six rows a card."""
    out = OrderedDict()
    rows = []
    for tf in TFS:
        r = _tf_read(row, tf)
        if r["above"] is None:
            rows.append([tf, "not enough closed bars yet"])
            continue
        v = "above %d of %d; %s; %s; %s" % (
            r["above"], r["n"], _stack_words(r),
            _dist_words(r["c"], r["px"][("sma", 50)], r["atr"], asset, "the 50 SMA"),
            _dist_words(r["c"], r["px"][("sma", 200)], r["atr"], asset, "the 200 SMA"))
        sl = _num(row, "ma_%s_ema50_slope" % tf)
        if sl is not None:
            v += "; EMA 50 %s %.2f ATR over %d bars" % ("rising" if sl > 0 else "falling", abs(sl), SLOPE_BARS)
        rows.append([tf, v])
    r4 = _tf_read(row, "4h")
    if r4["above"] is not None:
        rows.append(["Average prices, 4h", "SMA 5/10/20/50/200: %s; EMA: %s" % (
            " / ".join(_px(r4["px"][("sma", n)], asset) for n in LENGTHS),
            " / ".join(_px(r4["px"][("ema", n)], asset) for n in LENGTHS))])
    cr = []
    for tf in ("1h", "4h", "1d"):
        r = _tf_read(row, tf)
        for name in ("e20_50", "s50_200"):
            if r["crosses"].get(name):
                cr.append(_cross_words(name, r["crosses"][name], asset, tf))
    rows.append(["Crosses", "; ".join(cr) if cr else "none on record yet"])
    out[GROUPS["mavg"][0]] = rows[:6] if len(rows) <= 6 else rows[:4] + rows[-2:]

    rows = []
    for tf in ("1h", "15m"):
        r = _ribbon_read(row, tf)
        if r["state"] is None:
            rows.append(["%s ribbon (EMA 8-55)" % tf, "not formed yet"])
            continue
        v = _ribbon_words(r).split("; Guppy")[0]
        v += "; lines %s" % " / ".join(_px(x, asset) for x in r["lines"])
        if r["wchg"] is not None:
            v += "; width %+.2f ATR over %d bars" % (r["wchg"], RB_CHG_BARS)
        rows.append(["%s ribbon (EMA 8-55)" % tf, v])
    for tf in ("1h", "15m"):
        r = _ribbon_read(row, tf)
        if r["gmma_sep"] is None:
            rows.append(["Guppy %s" % tf, "not formed yet"])
            continue
        sep = r["gmma_sep"]
        v = "short group (EMA 3-15) %.1f ATR %s the long group (EMA 30-60)" % (abs(sep), "above" if sep >= 0 else "below")
        v += "; groups %s" % ("interwoven (crossing)" if r["gmma_overlap"] else "apart")
        if r["gmma_x_age"] is not None:
            v += "; the group averages last crossed %s ago" % _bars(r["gmma_x_age"])
        rows.append(["Guppy %s" % tf, v])
    out[GROUPS["ribbon"][0]] = rows

    rows = []
    reads = [_sr_read(row, tf) for tf in TFS]
    for r in reads:
        if r["sup"] is None and r["res"] is None:
            rows.append([r["tf"], "not enough closed bars yet"])
            continue
        v = _near_words(r, asset)[len(r["tf"]) + 1:]
        tw = _sr_test_words(r, row, asset)
        v += "; " + (tw.split(": ", 1)[1] if tw else "nothing tested on the last closed bar")
        v += "; last counted test: " + _last_test_words(r)
        rows.append([r["tf"], v])
    for r in (reads[1], reads[2]):
        recs = []
        for fa in (("ema", 20), ("ema", 50), ("sma", 50), ("sma", 200)):
            h, t = r["rec"][fa]
            if t:
                recs.append("%s held %d of %d" % (_nm(*fa), int(h), int(t)))
        rows.append(["Respect record, %s (last %d tests)" % (r["tf"], RESPECT_N[r["tf"]]), "; ".join(recs) if recs else "no tests yet"])
    out[GROUPS["mavg_sr"][0]] = rows
    return out
