# -*- coding: utf-8 -*-
"""ltf -- three decision cards of lower-timeframe tools, computed from the coin's own 15m bars.

  intraday  Intraday levels (VWAP and opening range)   daily and weekly VWAP, the first hour's range, today's range
  trendq    Trend quality and squeeze                  ADX, Bollinger/Keltner squeeze, Supertrend, swing structure,
                                                       MACD, RSI, relative volume
  candles   Candle size and realistic targets          average candle body and range on 15m / 1h / 4h / 1d, the
                                                       share of a normal day already travelled, and REALISTIC REACH:
                                                       how far price has typically travelled in 1, 4 and 24 hours

Nothing is fetched and nothing is stored: `update` returns {} and `features` reads only the bars.

THE ONE RULE (tests/test_sources_ltf.py::test_no_lookahead): row i uses only bars that had closed
by the close of 15m bar i (its open + 15 minutes).

    15m indicators            rolling / recursive, backward only
    1h, 4h, 1d indicators     computed on resampled bars, handed over by data.htf_on_15: a higher bar
                              reaches a 15m row only once that higher bar has CLOSED
    session VWAP, day range   cumulative inside the session, so only the session's bars up to row i
    opening range             unknown (NaN) until the bar that closes the first hour of the UTC day
    confirmed swing           a swing at bar j needs SWING_K bars after it: it appears at row j + SWING_K
    reach ratio of bar t      needs the N bars after t: it enters the rolling window at row t + N

Windows count BARS (as engine15/indicators.py and levels.py do), sessions and the hour of day are
read from the clock. Features are dimensionless, clipped, 0.0 = no read; the readable columns (RAW)
are prices, percentages and counts and may be NaN. A price distance shown to the owner is always a
percentage applied to the bar's close (`ltf_close`).

Docs: docs/SOURCES_ltf.md. No reading here is claimed to predict anything.
"""
import math
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

# =====================================================================================
# THE ONE CONSTANT BLOCK. Conventional values, declared once, none tuned against outcomes.
# =====================================================================================
BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
WEEK_MS = 7 * DAY_MS
MONDAY0_MS = 4 * DAY_MS           # 5 Jan 1970 00:00 UTC was a Monday: weeks are counted from it
ATR_N = 14                        # the engine's yardstick everywhere: Wilder ATR(14) of the 1-hour chart
LOG_CLIP = 3.0                    # ratios are read in doublings (log2) and clipped at 3 = eight times / one eighth
# ---- intraday
OR_MS = HOUR_MS                   # the opening range is the first hour of the UTC day
VWAP_BAND_MIN_BARS = 4            # bands of a session are read once it is an hour old (one bar has no spread)
VWAP_D_UNIT = 1.0                 # daily VWAP distance: 1 hourly ATR = 1.0
VWAP_W_UNIT = math.sqrt(7.0)      # weekly: sqrt(7) hourly ATRs = 1.0 (a week is 7 sessions; drift grows as sqrt(time))
DIST_CLIP = 3.0                   # both distances are clipped at 3 units
# ---- trendq
ADX_N = 14                        # Wilder's ADX / +DI / -DI length
ADX_TREND = 25.0                  # the textbook line between "no trend" and "trend": the feature's zero
BB_N, BB_K = 20, 2.0              # Bollinger bands: 20-bar average, 2 standard deviations
BBW_RANK_BARS, BBW_RANK_MIN = 2880, 672    # band width is ranked against its last 30 days (7 days to start)
KC_N, KC_K = 20, 1.5              # Keltner channels as the TTM squeeze uses them: 20-bar average +/- 1.5 mean true range
ST_N, ST_K = 10, 3.0              # Supertrend: ATR(10), 3 ATRs
SWING_K = 5                       # a swing is the extreme of 5 bars each side, so it is known 5 bars (75 min) late
EVENT_FADE = 8                    # a break of structure, squeeze release or Supertrend flip fades to nothing in 8 bars
MACD_FAST, MACD_SLOW, MACD_SIG = 12, 26, 9
RSI_N = 14
RVOL_DAYS, RVOL_MIN_DAYS = 20, 10  # the last hour's volume against the same hour of the previous 20 days (10 to start)
# ---- candles
AVG_15M, AVG_1H, AVG_4H, AVG_1D = 96, 48, 30, 14   # candles averaged per timeframe: 1 day, 2 days, 5 days, 2 weeks
EXPAND_FAST = 8                   # "recent" candles = the last 8 (2 hours), set against the last 96
REACH_HORIZONS = OrderedDict([("1h", 4), ("4h", 16), ("24h", 96)])   # horizons in 15m bars
REACH_WIN, REACH_MIN = 2160, 720  # reach ratios are sampled hourly: the last 90 days of them, 30 days to start
REACH_Q = 0.80                    # a "large move": the 80th percentile of the reach ratios
REACH_REL_BARS, REACH_REL_MIN = 8640, 2880   # the 24h reach is set against its own 90-day median (30 days to start)
# =====================================================================================

GROUPS = OrderedDict([
    ("intraday", ("Intraday levels (VWAP and opening range)",
                  ["id_vwap_d", "id_vwap_w", "id_band", "id_or", "id_day_pos"])),
    ("trendq", ("Trend quality and squeeze",
                ["tq_adx_15m", "tq_di_15m", "tq_adx_1h", "tq_di_1h", "tq_bbw", "tq_squeeze", "tq_sq_release",
                 "tq_st_15m", "tq_st_1h", "tq_st_flip", "tq_struct", "tq_bos",
                 "tq_macd_15m", "tq_macd_rise_15m", "tq_macd_1h", "tq_macd_rise_1h",
                 "tq_rsi_15m", "tq_rsi_1h", "tq_rvol"])),
    ("candles", ("Candle size and realistic targets",
                 ["cs_used", "cs_body", "cs_body_share", "cs_expand", "cs_reach_rel"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
REACH_COLS = ["reach_%s_%s_pct" % (h, s) for h in REACH_HORIZONS for s in ("med", "p80")]
# readable columns for the journal (NaN = no read)
RAW = ["ltf_close", "ltf_atr1h",                                    # the bar's close; ATR(14) of the 1-hour chart, in price
       # intraday: prices, and the close's distance from each VWAP in %
       "id_vwap_d_px", "id_vwap_d_sd_px", "id_vwap_d_pct", "id_vwap_w_px", "id_vwap_w_pct",
       "id_or_high_px", "id_or_low_px", "id_day_high_px", "id_day_low_px",
       # trendq: indicator values as charted, counts of bars, swing prices
       "tq_adx15", "tq_plus_di15", "tq_minus_di15", "tq_adx1h", "tq_plus_di1h", "tq_minus_di1h",
       "tq_bb_width_pct", "tq_bb_width_rank",                       # band width in % of price; its percentile (0-100) of 30 days
       "tq_sq_bars_on", "tq_sq_bars_since", "tq_sq_dir",            # bars in a squeeze; bars since it released, and which way
       "tq_st_bars_15m", "tq_st_hours_1h",                          # bars / hours since Supertrend last flipped
       "tq_swing_hi_px", "tq_swing_hi_prev_px", "tq_swing_lo_px", "tq_swing_lo_prev_px",
       "tq_bos_bars", "tq_bos_dir",                                 # bars since the last break of structure, and which way
       "tq_rsi15", "tq_rsi1h", "tq_rvol_x",                         # RSI 0-100; last hour's volume as a multiple of usual
       # candles: average body / range per candle in % of price; today's range; the last candle
       "cs_body15_pct", "cs_range15_pct", "cs_body1h_pct", "cs_range1h_pct", "cs_body4h_pct", "cs_range4h_pct",
       "cs_body1d_pct", "cs_adr_pct", "cs_today_range_pct", "cs_used_x",
       "cs_last_body_x", "cs_last_body_share", "cs_expand_x"] + REACH_COLS

_CARD_RAW = OrderedDict([("intraday", [c for c in RAW if c.startswith("id_")]),
                         ("trendq", [c for c in RAW if c.startswith("tq_")]),
                         ("candles", [c for c in RAW if c.startswith("cs_") or c.startswith("reach_")])])


def update(log=print):
    """Nothing to fetch: every reading comes from the 15m bars the engine already keeps."""
    return {}


# ------------------------------------------------------------------ small causal helpers
def _hbars(b, rule):
    """15m bars -> higher-timeframe bars keyed by OPEN time (data.resample's convention, without the
    order-flow column). Read only through data.htf_on_15, which hands a bar over once it has CLOSED."""
    agg = b.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return agg.dropna(subset=["close"])


def _on15(b, rule, values):
    """THE NO-LOOKAHEAD JOIN of a higher-timeframe frame onto the 15m rows (data.htf_on_15)."""
    return _data.htf_on_15(b, rule, values)


def _wilder(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _clip(x, lim):
    return np.clip(x, -lim, lim)


def _log2(ratio):
    """A positive ratio in doublings, clipped; zero -> the lower clip; NaN stays NaN."""
    r = np.asarray(ratio, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log2(np.where(r > 0, r, np.nan))
    out = np.where(r == 0, -LOG_CLIP, out)
    return _clip(out, LOG_CLIP)


def _since(flag):
    """-> (bars since the last True, NaN before the first; the row of that last True, -1 before)."""
    n = len(flag)
    rows = np.arange(n)
    last = np.maximum.accumulate(np.where(flag, rows, -1))
    age = (rows - last).astype(float)
    age[last < 0] = np.nan
    return age, last


def _fade(direction, age):
    """An event read: its direction, fading linearly to nothing over EVENT_FADE bars."""
    with np.errstate(invalid="ignore"):
        w = np.clip(1.0 - age / float(EVENT_FADE), 0.0, 1.0)
    return np.where(np.isfinite(age), direction * w, 0.0)


def _ffill(x):
    return pd.Series(x).ffill().values


def adx(df, n=ADX_N):
    """Wilder's ADX with +DI and -DI on any bar frame -> frame adx / plus / minus (0-100)."""
    up, dn = df["high"].diff(), -df["low"].diff()
    plus = up.where((up > dn) & (up > 0), 0.0)
    minus = dn.where((dn > up) & (dn > 0), 0.0)
    atr = _wilder(_ind.true_range(df), n)
    atr = atr.where(atr > 0)
    pdi, mdi = 100.0 * _wilder(plus, n) / atr, 100.0 * _wilder(minus, n) / atr
    tot = pdi + mdi
    dx = (100.0 * (pdi - mdi).abs() / tot.where(tot > 0)).where(tot > 0, 0.0).where(tot.notna())
    return pd.DataFrame({"adx": _wilder(dx, n), "plus": pdi, "minus": mdi})


def supertrend(df, n=ST_N, mult=ST_K):
    """Supertrend(n, mult) as charting packages draw it -> (direction +1 up / -1 down / 0 before the
    ATR exists, bars since the direction last flipped or NaN before the first flip)."""
    h, l = df["high"].values.astype(float), df["low"].values.astype(float)
    close = df["close"].values.astype(float).tolist()
    atr = _ind.atr_wilder(df, n).values
    mid = (h + l) / 2.0
    ub, lb, mid = (mid + mult * atr).tolist(), (mid - mult * atr).tolist(), mid.tolist()
    size = len(close)
    direction, since = [0.0] * size, [float("nan")] * size
    fu = fl = None
    cur, flip = 0, -1
    for i in range(size):
        u, lo = ub[i], lb[i]
        if u != u:
            continue
        if fu is None:                                               # the first bar with an ATR: no flip yet
            fu, fl, cur = u, lo, (1 if close[i] >= mid[i] else -1)
        else:
            pc = close[i - 1]
            fu = u if (u < fu or pc > fu) else fu                    # the upper band only ratchets down, the lower up
            fl = lo if (lo > fl or pc < fl) else fl
            if cur < 0 and close[i] > fu:
                cur, flip = 1, i
            elif cur > 0 and close[i] < fl:
                cur, flip = -1, i
        direction[i] = float(cur)
        if flip >= 0:
            since[i] = float(i - flip)
    return np.array(direction), np.array(since)


def macd_hist(close):
    line = _ema(close, MACD_FAST) - _ema(close, MACD_SLOW)
    return line - _ema(line, MACD_SIG)


def swings(high, low, k=SWING_K):
    """Confirmed swings, levels.py's definition: a swing high is >= the k highs before it and > the
    k highs after it. -> (rows of swing highs, rows of swing lows). A swing at row j may be USED
    only from row j + k on; the callers below place it there."""
    h, l = pd.Series(high), pd.Series(low)
    left_max = h.shift(1).rolling(k).max().values
    left_min = l.shift(1).rolling(k).min().values
    right_max = pd.Series(high[::-1]).shift(1).rolling(k).max().values[::-1]   # the k bars AFTER the swing
    right_min = pd.Series(low[::-1]).shift(1).rolling(k).min().values[::-1]
    with np.errstate(invalid="ignore"):
        return (np.flatnonzero((high >= left_max) & (high > right_max)),
                np.flatnonzero((low <= left_min) & (low < right_min)))


def _last_two(rows, price, k, n):
    """Swings at `rows` -> for every bar, the price of the last and of the one-before-last swing
    that had been CONFIRMED by then (each appears k bars after its own bar)."""
    last, prev = np.full(n, np.nan), np.full(n, np.nan)
    known = rows + k
    keep = known < n
    rows, known = rows[keep], known[keep]
    last[known] = price[rows]
    prev[known[1:]] = price[rows[:-1]]
    return _ffill(last), _ffill(prev) if len(rows) > 1 else prev


def forward_reach(high, low, close, n_bars):
    """For every bar t: the largest move in either direction within the NEXT n_bars bars, in price
    (NaN where fewer than n_bars bars follow). Known only at bar t + n_bars."""
    fmax = pd.Series(high[::-1]).shift(1).rolling(n_bars).max().values[::-1]
    fmin = pd.Series(low[::-1]).shift(1).rolling(n_bars).min().values[::-1]
    return np.maximum(fmax - close, close - fmin)


# ------------------------------------------------------------------ the shared read of the bars
class _Bars(object):
    def __init__(self, bars):
        b = bars[["open", "high", "low", "close", "volume"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
        self.b = b
        self.n = len(b)
        self.ms = _data.to_ms(b.index)
        self.o, self.h, self.l, self.c, self.v = (b[x].values.astype(float) for x in ("open", "high", "low", "close", "volume"))
        self.h1 = _hbars(b, "1h")
        self.atr1h = _on15(b, "1h", _ind.atr_wilder(self.h1, ATR_N)).values.astype(float)
        self.atr_ok = np.isfinite(self.atr1h) & (self.atr1h > 0)
        self.day = self.ms // DAY_MS
        self.day_open = pd.Series(self.o).groupby(self.day).transform("first").values    # the day's first bar: already closed
        g = pd.DataFrame({"h": self.h, "l": self.l}).groupby(self.day)
        self.day_high, self.day_low = g["h"].cummax().values, g["l"].cummin().values     # so far, this row included


def _session_vwap(x, key):
    """Volume-weighted average of the typical price, cumulative inside each session (`key` names the
    session of every row), with its volume-weighted standard deviation. -> (vwap, sd, bars so far)."""
    tp = (x.h + x.l + x.c) / 3.0
    k = pd.Series(key)
    ref = pd.Series(tp).groupby(key).transform("first").values       # measured from the session's first bar: exact sums
    d = tp - ref
    g = pd.DataFrame({"v": x.v, "dv": d * x.v, "ddv": d * d * x.v}).groupby(key)
    cum = g.cumsum()
    count = k.groupby(key).cumcount().values + 1
    cv = cum["v"].values
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(cv > 0, cum["dv"].values / cv, np.nan)
        var = np.where(cv > 0, cum["ddv"].values / cv, np.nan) - mean * mean
    return ref + mean, np.sqrt(np.maximum(var, 0.0)), count


# ------------------------------------------------------------------ card 1: intraday levels
def _intraday(x, out):
    c, atr = x.c, np.where(x.atr_ok, x.atr1h, np.nan)
    vwap_d, sd_d, count = _session_vwap(x, x.day)                    # anchored 00:00 UTC
    vwap_w, _sd, _n = _session_vwap(x, (x.ms - MONDAY0_MS) // WEEK_MS)   # anchored Monday 00:00 UTC
    with np.errstate(divide="ignore", invalid="ignore"):
        out["id_vwap_d"] = _clip((c - vwap_d) / (VWAP_D_UNIT * atr), DIST_CLIP)
        out["id_vwap_w"] = _clip((c - vwap_w) / (VWAP_W_UNIT * atr), DIST_CLIP)
        z = np.where((sd_d > 0) & (count >= VWAP_BAND_MIN_BARS), (c - vwap_d) / sd_d, np.nan)
        out["id_band"] = np.sign(z) * np.minimum(np.floor(np.abs(z)), 2.0) / 2.0     # zones -2..+2 -> -1..+1
        out["id_vwap_d_pct"] = 100.0 * (c - vwap_d) / vwap_d
        out["id_vwap_w_pct"] = 100.0 * (c - vwap_w) / vwap_w
    out["id_vwap_d_px"], out["id_vwap_d_sd_px"], out["id_vwap_w_px"] = vwap_d, sd_d, vwap_w

    tod = x.ms % DAY_MS
    first = tod < OR_MS                                              # bars of the first hour
    g = pd.DataFrame({"h": np.where(first, x.h, -np.inf), "l": np.where(first, x.l, np.inf)}).groupby(x.day)
    or_hi, or_lo = g["h"].cummax().values, g["l"].cummin().values    # running, so never a later bar
    known = (tod + BAR_MS >= OR_MS) & np.isfinite(or_hi) & np.isfinite(or_lo)   # this bar closes the first hour, or is later
    or_hi, or_lo = np.where(known, or_hi, np.nan), np.where(known, or_lo, np.nan)
    with np.errstate(invalid="ignore"):
        out["id_or"] = np.where(c > or_hi, 1.0, np.where(c < or_lo, -1.0, 0.0))
        span = x.day_high - x.day_low
        out["id_day_pos"] = np.where(span > 0, 2.0 * (c - x.day_low) / np.where(span > 0, span, 1.0) - 1.0, 0.0)
    out["id_or_high_px"], out["id_or_low_px"] = or_hi, or_lo
    out["id_day_high_px"], out["id_day_low_px"] = x.day_high, x.day_low


# ------------------------------------------------------------------ card 2: trend quality and squeeze
def _tf_reads(df):
    """The readings taken the same way on any timeframe's bars -> frame on that frame's index."""
    a = adx(df, ADX_N)
    st_dir, st_since = supertrend(df, ST_N, ST_K)
    hist = macd_hist(df["close"])
    r = _ind.rsi(df["close"], RSI_N)
    r = r.where(np.arange(len(r)) >= RSI_N)                          # Wilder's RSI needs its 14 changes
    return pd.DataFrame({"adx": a["adx"], "plus": a["plus"], "minus": a["minus"], "st": st_dir, "st_since": st_since,
                         "macd": np.sign(hist), "macd_rise": np.sign(hist - hist.shift(1)), "rsi": r}, index=df.index)


def _trendq(x, out):
    b, c, n = x.b, x.c, x.n
    for tag, f in (("15m", _tf_reads(b)), ("1h", _on15(b, "1h", _tf_reads(x.h1)))):
        short = tag.replace("m", "")                                 # raw column tags: 15, 1h
        a, p, m = (f[k].values.astype(float) for k in ("adx", "plus", "minus"))
        with np.errstate(divide="ignore", invalid="ignore"):
            out["tq_adx_" + tag] = np.clip((a - ADX_TREND) / ADX_TREND, -1.0, 3.0)   # 0 = at the trend line, 1 = ADX 50
            out["tq_di_" + tag] = np.where(p + m > 0, (p - m) / (p + m), np.nan)     # which side leads, -1..+1
        out["tq_adx" + short], out["tq_plus_di" + short], out["tq_minus_di" + short] = a, p, m
        out["tq_st_" + tag] = f["st"].values.astype(float)
        out["tq_macd_" + tag] = f["macd"].values.astype(float)
        out["tq_macd_rise_" + tag] = f["macd_rise"].values.astype(float)
        rsi = f["rsi"].values.astype(float)
        out["tq_rsi_" + tag] = (rsi - 50.0) / 50.0
        out["tq_rsi" + short] = rsi
        if tag == "15m":
            out["tq_st_bars_15m"] = f["st_since"].values.astype(float)
            out["tq_st_flip"] = _fade(out["tq_st_15m"], out["tq_st_bars_15m"])     # a fresh 15m flip, fading
        else:
            out["tq_st_hours_1h"] = f["st_since"].values.astype(float)             # 1h bars = hours

    # ---- Bollinger width and the Keltner squeeze
    close = b["close"]
    mid = close.rolling(BB_N).mean()
    sd = close.rolling(BB_N).std(ddof=0)
    width = (2.0 * BB_K * sd / mid.where(mid > 0))
    rank = width.rolling(BBW_RANK_BARS, min_periods=BBW_RANK_MIN).rank(pct=True)
    out["tq_bbw"] = 2.0 * rank.values - 1.0                           # -1 = the tightest of 30 days, +1 = the widest
    out["tq_bb_width_pct"], out["tq_bb_width_rank"] = 100.0 * width.values, 100.0 * rank.values
    kc = KC_K * _ind.true_range(b).rolling(KC_N).mean()
    valid = (sd.notna() & kc.notna() & mid.notna()).values
    on = valid & ((BB_K * sd).values < kc.values)                     # same midline, so: both Bollinger bands inside Keltner
    prev_on = np.concatenate([[False], on[:-1]])
    released = prev_on & ~on & valid
    age, last = _since(released)
    rel_dir = np.where(last >= 0, np.sign(c - mid.values)[np.maximum(last, 0)], np.nan)   # side of the average at the release
    age, rel_dir = np.where(on, np.nan, age), np.where(on, np.nan, rel_dir)                 # a new squeeze replaces the old release
    _off_age, last_off = _since(~on)
    out["tq_squeeze"] = np.where(valid, on.astype(float), np.nan)
    out["tq_sq_release"] = _fade(np.nan_to_num(rel_dir), age)
    out["tq_sq_bars_on"] = np.where(on, (np.arange(n) - last_off).astype(float), np.where(valid, 0.0, np.nan))
    out["tq_sq_bars_since"], out["tq_sq_dir"] = age, rel_dir

    # ---- market structure from confirmed swings
    hi_rows, lo_rows = swings(x.h, x.l, SWING_K)
    hi, hi_prev = _last_two(hi_rows, x.h, SWING_K, n)
    lo, lo_prev = _last_two(lo_rows, x.l, SWING_K, n)
    with np.errstate(invalid="ignore"):
        have = np.isfinite(hi) & np.isfinite(hi_prev) & np.isfinite(lo) & np.isfinite(lo_prev)
        out["tq_struct"] = np.where(have & (hi > hi_prev) & (lo > lo_prev), 1.0,
                                    np.where(have & (hi < hi_prev) & (lo < lo_prev), -1.0, 0.0))
        above, below = c > hi, c < lo                                 # a CLOSE beyond the last confirmed swing
    event = ((above & ~np.concatenate([[False], above[:-1]])).astype(float)
             - (below & ~np.concatenate([[False], below[:-1]])).astype(float))
    age, last = _since(event != 0)
    bos_dir = np.where(last >= 0, event[np.maximum(last, 0)], np.nan)
    out["tq_bos"] = _fade(np.nan_to_num(bos_dir), age)
    out["tq_bos_bars"], out["tq_bos_dir"] = age, bos_dir
    out["tq_swing_hi_px"], out["tq_swing_hi_prev_px"], out["tq_swing_lo_px"], out["tq_swing_lo_prev_px"] = hi, hi_prev, lo, lo_prev

    # ---- relative volume: the last hour against the same clock hour of the previous days (on a gapless clock)
    pos = (x.ms - x.ms[0]) // BAR_MS
    if ((x.ms - x.ms[0]) % BAR_MS).any():
        raise ValueError("bars are not on the 15-minute grid")
    grid = np.full(int(pos[-1]) + 1, np.nan)
    grid[pos] = x.v
    v4 = pd.Series(grid).rolling(4, min_periods=4).sum().values       # the hour ending at this bar's close
    total, count = np.zeros(len(grid)), np.zeros(len(grid))
    for d in range(1, RVOL_DAYS + 1):
        k = 96 * d
        if k >= len(grid):
            break
        past = v4[:-k]
        ok = np.isfinite(past)
        total[k:] += np.where(ok, past, 0.0)
        count[k:] += ok
    with np.errstate(divide="ignore", invalid="ignore"):
        usual = np.where(count >= RVOL_MIN_DAYS, total / np.where(count > 0, count, 1.0), np.nan)
        rvol = np.where(usual > 0, v4 / usual, np.nan)[pos]
    out["tq_rvol"] = _log2(rvol)                                      # +1 = twice the usual volume for this hour
    out["tq_rvol_x"] = rvol


# ------------------------------------------------------------------ card 3: candle size and realistic targets
def _sizes(df, window):
    """Average candle body and range over the last `window` candles, each as a % of its own open."""
    o = df["open"].where(df["open"] > 0)
    body, rng = 100.0 * (df["close"] - df["open"]).abs() / o, 100.0 * (df["high"] - df["low"]) / o
    return pd.DataFrame({"body": body.rolling(window).mean(), "range": rng.rolling(window).mean()}, index=df.index)


def _candles(x, out):
    b, c, n = x.b, x.c, x.n
    s15 = _sizes(b, AVG_15M)
    out["cs_body15_pct"], out["cs_range15_pct"] = s15["body"].values, s15["range"].values
    for tag, rule, window in (("1h", "1h", AVG_1H), ("4h", "4h", AVG_4H), ("1d", "1D", AVG_1D)):
        s = _on15(b, rule, _sizes(x.h1 if rule == "1h" else _hbars(b, rule), window))
        out["cs_body%s_pct" % tag] = s["body"].values.astype(float)
        out["cs_adr_pct" if tag == "1d" else "cs_range%s_pct" % tag] = s["range"].values.astype(float)

    adr = out["cs_adr_pct"]                                           # average daily range of the last 14 CLOSED days
    with np.errstate(divide="ignore", invalid="ignore"):
        today = np.where(x.day_open > 0, 100.0 * (x.day_high - x.day_low) / x.day_open, np.nan)
        used = np.where(adr > 0, today / adr, np.nan)
        out["cs_today_range_pct"], out["cs_used_x"] = today, used
        out["cs_used"] = np.clip(used - 1.0, -1.0, 2.0)               # 0 = exactly one average day travelled

        body = np.where(x.o > 0, 100.0 * np.abs(c - x.o) / x.o, np.nan)
        rng = x.h - x.l
        avg = out["cs_body15_pct"]
        mult = np.where(avg > 0, body / avg, np.nan)
        share = np.where(rng > 0, np.abs(c - x.o) / np.where(rng > 0, rng, 1.0), np.nan)
        fast = pd.Series(body).rolling(EXPAND_FAST).mean().values
        expand = np.where(avg > 0, fast / avg, np.nan)
    out["cs_last_body_x"], out["cs_last_body_share"], out["cs_expand_x"] = mult, share, expand
    out["cs_body"] = _log2(mult)                                      # +1 = a body twice the average
    out["cs_body_share"] = 2.0 * share - 1.0                          # +1 = all body, -1 = all wick
    out["cs_expand"] = _log2(expand)                                  # + = candles growing, - = shrinking

    # ---- realistic reach: forward moves in hourly ATRs, used only once they are history
    atr = np.where(x.atr_ok, x.atr1h, np.nan)
    sample = np.flatnonzero(x.ms % HOUR_MS == HOUR_MS - BAR_MS)       # one bar an hour: the one that closes on the hour
    rows = np.arange(n)
    for tag, n_bars in REACH_HORIZONS.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = pd.Series((forward_reach(x.h, x.l, c, n_bars) / atr)[sample])
        roll = ratio.rolling(REACH_WIN, min_periods=REACH_MIN)
        known = sample + n_bars                                       # the row at which each sampled ratio became history
        k = np.searchsorted(known, rows, side="right") - 1            # the newest ratio known at each row
        for stat, series in (("med", roll.median()), ("p80", roll.quantile(REACH_Q))):
            v = series.values
            got = np.where(k >= 0, v[np.maximum(k, 0)], np.nan) if len(v) else np.full(n, np.nan)
            with np.errstate(divide="ignore", invalid="ignore"):
                out["reach_%s_%s_pct" % (tag, stat)] = np.where(c > 0, 100.0 * got * atr / c, np.nan)
    now = pd.Series(out["reach_24h_med_pct"])
    norm = now.rolling(REACH_REL_BARS, min_periods=REACH_REL_MIN).median().values
    with np.errstate(divide="ignore", invalid="ignore"):
        out["cs_reach_rel"] = _log2(np.where(norm > 0, now.values / norm, np.nan))   # + = travelling more than its 90-day usual


_CARDS = OrderedDict([("intraday", _intraday), ("trendq", _trendq), ("candles", _candles)])


def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature named in GROUPS as a float
    (0.0 = no read, never NaN) plus the readable RAW columns (NaN = no read).

    bars: the asset's 15m frame (data.load(asset) when None). Every reading is made on the bars and
    then handed to the index row with the same open time; an index row without a bar is "no read".
    A card that cannot be built is left at "no read"; the reason is in .attrs["errors"]."""
    index15 = pd.DatetimeIndex(index15)
    names = FEATURES + RAW
    at_col = dict((c, j) for j, c in enumerate(names))
    block = np.full((len(index15), len(names)), np.nan, order="F")   # one column after another, filled in place
    errors = {}
    try:
        if bars is None:
            bars = _data.load(asset)
        x = _Bars(bars) if len(bars) else None
    except Exception as e:
        x, errors["bars"] = None, "%s: %s" % (type(e).__name__, str(e)[:160])
    if x is not None and len(index15):
        want = _data.to_ms(index15)
        at = np.minimum(np.searchsorted(x.ms, want), x.n - 1)
        hit = x.ms[at] == want                                       # the bar with this row's own open time, or nothing
        at = at[hit]

        def hand_over(card):
            for col, values in card.items():
                block[hit, at_col[col]] = np.asarray(values, dtype=float)[at]

        hand_over({"ltf_close": x.c, "ltf_atr1h": np.where(x.atr_ok, x.atr1h, np.nan)})
        for name, fn in _CARDS.items():
            card = {}
            try:
                fn(x, card)
                hand_over(card)
            except Exception as e:                                   # a card that breaks is "no read", not a crash
                errors[name] = "%s: %s" % (type(e).__name__, str(e)[:160])
                for col in GROUPS[name][1] + _CARD_RAW[name]:
                    block[:, at_col[col]] = np.nan
            del card
    feats = block[:, :len(FEATURES)]
    feats[~np.isfinite(feats)] = 0.0                                 # no read
    out = pd.DataFrame(block, index=index15, columns=names, copy=False)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _px(v):
    """A price level."""
    if v is None:
        return "n/a"
    return ("{:,.0f}" if abs(v) >= 10000 else "{:,.2f}" if abs(v) >= 1 else "{:.5f}").format(v)


def _usd(v):
    """A price distance."""
    if v is None:
        return "n/a"
    a = abs(v)
    return "$" + ("{:,.0f}" if a >= 100 else "{:,.1f}" if a >= 10 else "{:,.2f}" if a >= 0.1 else "{:.4f}").format(a)


def _pc(v):
    return "n/a" if v is None else ("%.2f%%" if abs(v) < 10 else "%.1f%%") % v


def _pct_px(pct, close, form="%s / %s"):
    """'0.24% / $177': a percentage and what it is in price at this close."""
    if pct is None:
        return "n/a"
    return _pc(pct) if close is None else form % (_pc(pct), _usd(pct / 100.0 * close))


def _side(pct):
    return "n/a" if pct is None else "%s %s" % (_pc(abs(pct)), "above" if pct >= 0 else "below")


def _bars_words(nb):
    nb = int(round(nb))
    return "%d bar%s" % (nb, "" if nb == 1 else "s")


def _intraday_read(row):
    r = dict((k, _num(row, k)) for k in ["ltf_close"] + _CARD_RAW["intraday"])
    c, hi, lo = r["ltf_close"], r["id_or_high_px"], r["id_or_low_px"]
    r["or_state"] = None if c is None or hi is None or lo is None else (
        "above" if c > hi else "below" if c < lo else "inside")
    dh, dl = r["id_day_high_px"], r["id_day_low_px"]
    r["day_pos"] = None if c is None or dh is None or dl is None or dh <= dl else 100.0 * (c - dl) / (dh - dl)
    return r


def _trendq_read(row):
    r = dict((k, _num(row, k)) for k in _CARD_RAW["trendq"])
    for tag in ("15m", "1h"):
        for k in ("tq_st_", "tq_macd_", "tq_macd_rise_"):
            r[k + tag] = _num(row, k + tag) or 0.0
    r["struct"], r["squeeze"] = _num(row, "tq_struct") or 0.0, _num(row, "tq_squeeze") or 0.0
    hi, hp, lo, lp = (r[k] for k in ("tq_swing_hi_px", "tq_swing_hi_prev_px", "tq_swing_lo_px", "tq_swing_lo_prev_px"))
    if None in (hi, hp, lo, lp):
        r["struct_words"] = None
    elif r["struct"] > 0:
        r["struct_words"] = "higher highs and higher lows"
    elif r["struct"] < 0:
        r["struct_words"] = "lower highs and lower lows"
    elif hi > hp and lo < lp:
        r["struct_words"] = "mixed: a higher high but a lower low (widening)"
    elif hi < hp and lo > lp:
        r["struct_words"] = "mixed: a lower high but a higher low (narrowing)"
    else:
        r["struct_words"] = "mixed"
    return r


def _adx_words(a, p, m):
    if a is None:
        return "n/a"
    lead = "" if p is None or m is None or p == m else " (%s lead)" % ("buyers" if p > m else "sellers")
    return "%.0f%s" % (a, lead)


def _squeeze_words(r, short=False):
    rank = r["tq_bb_width_rank"]
    tail = "" if rank is None or short else "; band width is wider than %.0f%% of the last 30 days" % rank
    if r["tq_bb_width_pct"] is None:
        return "n/a"
    if r["squeeze"] > 0:
        return "ON for %s%s%s" % (_bars_words(r["tq_sq_bars_on"] or 1),
                                  "" if short else " (Bollinger bands inside Keltner channels)", tail)
    since, way = r["tq_sq_bars_since"], r["tq_sq_dir"]
    if since is None:
        return "off%s" % tail
    return "off, the last one released %s%s ago%s" % (
        "" if not way else ("upward " if way > 0 else "downward "), _bars_words(since), tail)


def _st_words(side, age, unit):
    if not side:
        return "n/a"
    word = "up" if side > 0 else "down"
    return word if age is None else "%s for %d %s" % (word, int(round(age)), unit)


def _macd_words(sign, rise):
    if not sign:
        return "n/a"
    return "%s zero and %s" % ("above" if sign > 0 else "below", "rising" if rise > 0 else "falling" if rise < 0 else "flat")


def _candles_read(row):
    return dict((k, _num(row, k)) for k in ["ltf_close"] + _CARD_RAW["candles"])


def _travel(r, stat):
    c = r["ltf_close"]
    bits = []
    for tag in REACH_HORIZONS:
        v = r["reach_%s_%s_pct" % (tag, stat)]
        if v is None:
            return None
        bits.append("%s %s (%s)" % (tag, _pc(v), _usd(v / 100.0 * c)) if c is not None else "%s %s" % (tag, _pc(v)))
    return ", ".join(bits)


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    coin, say = asset.replace("USDT", ""), OrderedDict()

    r = _intraday_read(row)
    title = GROUPS["intraday"][0]
    if r["ltf_close"] is None or r["id_vwap_d_px"] is None:
        say[title] = "No read: no closed %s bar for this session." % coin
    else:
        s = "%s closed at %s, %s today's VWAP (%s)" % (coin, _px(r["ltf_close"]), _side(r["id_vwap_d_pct"]), _px(r["id_vwap_d_px"]))
        if r["id_vwap_w_px"] is not None:
            s += " and %s this week's VWAP (%s)" % (_side(r["id_vwap_w_pct"]), _px(r["id_vwap_w_px"]))
        if r["or_state"] is None:
            s += "; the first hour's range is not known yet"
        else:
            s += "; it is %s the first hour's range (%s to %s)" % (r["or_state"], _px(r["id_or_low_px"]), _px(r["id_or_high_px"]))
        if r["day_pos"] is not None:
            s += " and %.0f%% of the way up today's range (%s to %s)" % (r["day_pos"], _px(r["id_day_low_px"]), _px(r["id_day_high_px"]))
        say[title] = s + "."

    r = _trendq_read(row)
    title = GROUPS["trendq"][0]
    if r["tq_adx15"] is None and r["tq_rsi15"] is None:
        say[title] = "No read: not enough closed %s bars for the trend tools." % coin
    else:
        bits = ["ADX is %s on 15m and %s on 1h (25 and above is usually called a trend)" % (
            _adx_words(r["tq_adx15"], r["tq_plus_di15"], r["tq_minus_di15"]),
            _adx_words(r["tq_adx1h"], r["tq_plus_di1h"], r["tq_minus_di1h"]))]
        bits.append("Supertrend is %s on 15m and %s on 1h" % (
            _st_words(r["tq_st_15m"], None, ""), _st_words(r["tq_st_1h"], None, "")))
        if r["struct_words"]:
            bits.append("the 15m swings show %s" % r["struct_words"])
        if r["tq_bb_width_pct"] is not None:
            bits.append("the volatility squeeze is %s" % _squeeze_words(r, short=True))
        if r["tq_rsi15"] is not None:
            bits.append("RSI %.0f on 15m%s" % (r["tq_rsi15"], "" if r["tq_rsi1h"] is None else " and %.0f on 1h" % r["tq_rsi1h"]))
        if r["tq_rvol_x"] is not None:
            bits.append("the last hour traded %.1fx its usual volume for this hour of day" % r["tq_rvol_x"])
        say[title] = "%s: %s." % (coin, "; ".join(bits))

    r = _candles_read(row)
    title = GROUPS["candles"][0]
    c = r["ltf_close"]
    if c is None or r["cs_body15_pct"] is None:
        say[title] = "No read: not enough closed %s bars to average candle sizes." % coin
    else:
        s = "An average %s 15m candle has a body of %s and spans %s high to low" % (
            coin, _pct_px(r["cs_body15_pct"], c, "%s (%s)"), _pct_px(r["cs_range15_pct"], c, "%s (%s)"))
        if r["cs_adr_pct"] is not None:
            s += "; an average day spans %s" % _pct_px(r["cs_adr_pct"], c, "%s (%s)")
            if r["cs_used_x"] is not None:
                s += " and today has covered %.0f%% of that" % (100.0 * r["cs_used_x"])
        med = _travel(r, "med")
        if med:
            s += "; over the last 90 days, scaled to today's volatility, price typically travelled %s in either direction" % med
        say[title] = s + "."
    return say


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: prices, percentages and counts
    a person can read (never a scaled model number). Four to six rows a card."""
    out = OrderedDict()

    r = _intraday_read(row)
    c = r["ltf_close"]
    band = "n/a"
    if r["id_vwap_d_px"] is not None and r["id_vwap_d_sd_px"]:
        v, sd = r["id_vwap_d_px"], r["id_vwap_d_sd_px"]
        band = "1 sd: %s to %s; 2 sd: %s to %s" % (_px(v - sd), _px(v + sd), _px(v - 2 * sd), _px(v + 2 * sd))
    out[GROUPS["intraday"][0]] = [
        ["Daily VWAP (from 00:00 UTC)", "n/a" if r["id_vwap_d_px"] is None else
         "%s (price is %s)" % (_px(r["id_vwap_d_px"]), _side(r["id_vwap_d_pct"]))],
        ["Daily VWAP bands", band],
        ["Weekly VWAP (from Monday 00:00 UTC)", "n/a" if r["id_vwap_w_px"] is None else
         "%s (price is %s)" % (_px(r["id_vwap_w_px"]), _side(r["id_vwap_w_pct"]))],
        ["Opening range (first hour, UTC)", "not known until 01:00 UTC" if r["or_state"] is None else
         "%s to %s; price is %s it" % (_px(r["id_or_low_px"]), _px(r["id_or_high_px"]), r["or_state"])],
        ["Today's high / low so far", "n/a" if r["id_day_high_px"] is None else "%s / %s%s" % (
            _px(r["id_day_high_px"]), _px(r["id_day_low_px"]),
            "" if r["day_pos"] is None else " (price is %.0f%% of the way up)" % r["day_pos"])],
    ]

    r = _trendq_read(row)
    structure = r["struct_words"] or "not enough confirmed swings yet"
    if r["struct_words"]:
        structure += " (highs %s then %s; lows %s then %s)" % (
            _px(r["tq_swing_hi_prev_px"]), _px(r["tq_swing_hi_px"]), _px(r["tq_swing_lo_prev_px"]), _px(r["tq_swing_lo_px"]))
        if r["tq_bos_bars"] is not None and r["tq_bos_bars"] < EVENT_FADE and r["tq_bos_dir"]:
            structure += "; a close broke %s the swing %s of the time %s ago" % (
                "above" if r["tq_bos_dir"] > 0 else "below", "high" if r["tq_bos_dir"] > 0 else "low", _bars_words(r["tq_bos_bars"]))
    out[GROUPS["trendq"][0]] = [
        ["ADX 15m / 1h (25+ = trend)", "%s / %s" % (_adx_words(r["tq_adx15"], r["tq_plus_di15"], r["tq_minus_di15"]),
                                                   _adx_words(r["tq_adx1h"], r["tq_plus_di1h"], r["tq_minus_di1h"]))],
        ["Squeeze (15m)", _squeeze_words(r)],
        ["Supertrend 15m / 1h", "%s / %s" % (_st_words(r["tq_st_15m"], r["tq_st_bars_15m"], "bars"),
                                            _st_words(r["tq_st_1h"], r["tq_st_hours_1h"], "hours"))],
        ["Structure (15m swings)", structure],
        ["RSI 15m / 1h", "%s / %s (MACD histogram: 15m %s, 1h %s)" % (
            "n/a" if r["tq_rsi15"] is None else "%.0f" % r["tq_rsi15"], "n/a" if r["tq_rsi1h"] is None else "%.0f" % r["tq_rsi1h"],
            _macd_words(r["tq_macd_15m"], r["tq_macd_rise_15m"]), _macd_words(r["tq_macd_1h"], r["tq_macd_rise_1h"]))],
        ["Volume, last hour", "n/a" if r["tq_rvol_x"] is None else "%.1fx usual for this hour of day" % r["tq_rvol_x"]],
    ]

    r = _candles_read(row)
    c = r["ltf_close"]
    last = "n/a"
    if r["cs_last_body_x"] is not None:
        last = "body %.1fx the average" % r["cs_last_body_x"]
        if r["cs_last_body_share"] is not None:
            last += ", %.0f%% body / %.0f%% wick" % (100.0 * r["cs_last_body_share"], 100.0 * (1.0 - r["cs_last_body_share"]))
        if r["cs_expand_x"] is not None:
            last += "; last %d candles %.1fx the usual size (%s)" % (
                EXPAND_FAST, r["cs_expand_x"], "expanding" if r["cs_expand_x"] > 1 else "contracting")
    med, big = _travel(r, "med"), _travel(r, "p80")
    out[GROUPS["candles"][0]] = [
        ["Average 15m candle (last %d)" % AVG_15M, "n/a" if r["cs_body15_pct"] is None else
         "%s body, %s range" % (_pct_px(r["cs_body15_pct"], c), _pct_px(r["cs_range15_pct"], c))],
        ["Average range, 1h / 4h candle", "%s (1h), %s (4h)" % (_pct_px(r["cs_range1h_pct"], c), _pct_px(r["cs_range4h_pct"], c))],
        ["Average daily range (%d days)" % AVG_1D, _pct_px(r["cs_adr_pct"], c)],
        ["Range used today", "n/a" if r["cs_used_x"] is None else "%.0f%% of an average day (today so far: %s)" % (
            100.0 * r["cs_used_x"], _pct_px(r["cs_today_range_pct"], c))],
        ["Last 15m candle", last],
        ["Typical travel", "not enough history yet" if not med else
         "%s%s" % (med, "" if not big else "; large moves reach %s" % big)],
    ]
    return out
