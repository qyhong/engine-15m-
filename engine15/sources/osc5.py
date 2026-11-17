# -*- coding: utf-8 -*-
"""osc5 -- card pipeline batch 4: five reading-only cards from the asset's own bars.

  fisher   Fisher Transform (15m to 4h)              Ehlers: x = 0.66 x ((median - lowest median) / (highest - lowest
                                                     median over 9 bars) - 0.5) + 0.67 x previous x, held inside
                                                     +/-0.999; Fisher = 0.5 x ln((1 + x) / (1 - x)) + 0.5 x previous
                                                     Fisher; trigger = Fisher one bar earlier. Feature Fisher / 4,
                                                     which side of the trigger it is on, and an extreme flag beyond +/-2.5
  ultosc   Ultimate Oscillator (15m, 1h, daily)      Larry Williams: buying pressure = close - min(low, prior close),
                                                     true range = max(high, prior close) - min(low, prior close);
                                                     UO = 100 x (4 x avg7 + 2 x avg14 + avg28) / 7; feature
                                                     (UO - 50) / 25; above 70 overbought, below 30 oversold
  trix     TRIX (1h to daily)                        one-bar % change of the triple EMA(15) of the close, with its
                                                     EMA(9) signal line; feature = TRIX in ATR(14) of that timeframe
                                                     per bar / 0.2, which side of the signal it is on, and its sign
  linreg   Linear-regression channel (1h to daily)   least-squares line through the last 50 closes: slope (raw: % of
                                                     price per bar; feature: ATRs per bar / 0.2), R-squared (how
                                                     straight the move is), and where the close sits inside the
                                                     +/-2 standard-error channel (-1 bottom .. +1 top)
  mass     Mass Index (1h to daily)                  Dorsey: EMA9 of (high - low) over the EMA9 of that EMA9, summed
                                                     over 25 bars; feature (MI - 25) / 3; the "reversal bulge" is MI
                                                     rising above 27 and then falling back below 26.5, signed against
                                                     the EMA9 slope of the close on that bar, fading over 10 bars

THE ONE RULE (tests/test_sources_osc5.py): row i uses only what was known at the close of 15m bar i. A higher
timeframe's value reaches a 15m row only once that higher bar has closed (data.htf_on_15). Nothing is fetched:
update() does nothing. No card votes until the owner's card rating promotes it; no reading is claimed to predict.
None of the five needs volume, so every market reads all five.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

TFS4 = (("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D"))
TFS_FISH = TFS4[:3]                             # 15m, 1h, 4h
TFS_UO = (TFS4[0], TFS4[1], TFS4[3])            # 15m, 1h, 1d
TFS_HTF = TFS4[1:]                              # 1h, 4h, 1d

FISH_N, FISH_SCALE, FISH_EXT = 9, 4.0, 2.5
UO_N, UO_W, UO_OB, UO_OS, UO_SCALE = (7, 14, 28), (4.0, 2.0, 1.0), 70.0, 30.0, 25.0
TRIX_N, TRIX_SIG, TRIX_SCALE = 15, 9, 0.2       # feature = TRIX in ATRs per bar / 0.2, clipped
ATR_N = 14
LRC_N, LRC_K, LRC_SLOPE_SCALE = 50, 2.0, 0.2    # channel = line +/- 2 standard errors; slope feature = ATRs per bar / 0.2
MASS_EMA, MASS_SUM, MASS_SET, MASS_TRIGGER = 9, 25, 27.0, 26.5
MASS_MID, MASS_SCALE, MASS_HOLD = 25.0, 3.0, 10

GROUPS = OrderedDict([
    ("fisher", ("Fisher Transform (15m to 4h)",
                ["fish_%s" % t for t, _ in TFS_FISH] + ["fishx_%s" % t for t, _ in TFS_FISH]
                + ["fishext_%s" % t for t, _ in TFS_FISH])),
    ("ultosc", ("Ultimate Oscillator (15m, 1h, daily)",
                ["uo_%s" % t for t, _ in TFS_UO] + ["uoz_%s" % t for t, _ in TFS_UO])),
    ("trix", ("TRIX (1h to daily)",
              ["trix_%s" % t for t, _ in TFS_HTF] + ["trixx_%s" % t for t, _ in TFS_HTF]
              + ["trixz_%s" % t for t, _ in TFS_HTF])),
    ("linreg", ("Linear-regression channel (1h to daily)",
                ["lrc_slope_%s" % t for t, _ in TFS_HTF] + ["lrc_r2_%s" % t for t, _ in TFS_HTF]
                + ["lrc_pos_%s" % t for t, _ in TFS_HTF])),
    ("mass", ("Mass Index (1h to daily)",
              ["mass_%s" % t for t, _ in TFS_HTF] + ["massb_%s" % t for t, _ in TFS_HTF])),
])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = (["fish_raw_%s" % t for t, _ in TFS_FISH] + ["fish_trig_%s" % t for t, _ in TFS_FISH]
       + ["fishx_age_%s" % t for t, _ in TFS_FISH]
       + ["uo_raw_%s" % t for t, _ in TFS_UO]
       + ["trix_raw_%s" % t for t, _ in TFS_HTF] + ["trix_sig_%s" % t for t, _ in TFS_HTF]
       + ["trix_atr_%s" % t for t, _ in TFS_HTF] + ["trixx_age_%s" % t for t, _ in TFS_HTF]
       + ["lrc_slope_raw_%s" % t for t, _ in TFS_HTF] + ["lrc_slope_atr_%s" % t for t, _ in TFS_HTF]
       + ["lrc_pos_raw_%s" % t for t, _ in TFS_HTF] + ["lrc_mid_%s" % t for t, _ in TFS_HTF]
       + ["lrc_se_%s" % t for t, _ in TFS_HTF]
       + ["mass_raw_%s" % t for t, _ in TFS_HTF] + ["mass_trend_%s" % t for t, _ in TFS_HTF]
       + ["massb_age_%s" % t for t, _ in TFS_HTF] + ["massb_trend_%s" % t for t, _ in TFS_HTF])


def update(log=print):
    """Nothing to fetch: all five cards are computed from the asset's own bars."""
    return {}


# ----------------------------------------------------------------------------------------------- bar helpers
def _resample(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def _on15(b, rule, frame):
    """A frame on the bars of `rule` (None = the 15m bars themselves) -> the same columns on b's 15m index."""
    out = frame if rule is None else _data.htf_on_15(b, rule, frame)
    return out.reindex(b.index)


def _since(ev):
    """Bars since the last True in a boolean array (0 on that bar), NaN before the first."""
    ev = np.asarray(ev, dtype=bool)
    i = np.arange(len(ev))
    last = np.maximum.accumulate(np.where(ev, i, -1)) if len(ev) else np.zeros(0, int)
    return np.where(last >= 0, i - last, np.nan).astype(float)


def _fade(age, hold):
    """Age in bars -> 1 on the event bar fading linearly to 0 after `hold` bars (NaN age -> 0)."""
    w = 1.0 - np.asarray(age, dtype=float) / (hold + 1.0)
    return np.where(np.isfinite(w) & (w > 0), w, 0.0)


def _ema(x, n):
    """EMA(n), alpha = 2 / (n + 1), seeded with the plain mean of the first n values after any leading NaNs
    (NaN until then). Chains cleanly: EMA of an EMA starts n - 1 bars after the inner one."""
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    ok = np.flatnonzero(np.isfinite(v))
    if len(ok) and len(v) - ok[0] >= n:
        f = ok[0]
        tail = np.concatenate([[v[f:f + n].mean()], v[f + n:]])
        out[f + n - 1:] = pd.Series(tail).ewm(alpha=2.0 / (n + 1.0), adjust=False).mean().values
    return out


def _side_and_age(a, b):
    """-> (side, age): side = +1 where a > b, -1 where a < b (a tie keeps the previous side; NaN before either
    exists); age = bars since the side last flipped (0 on the bar of the cross, NaN before the first cross)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    side = pd.Series(np.where(np.isfinite(d) & (d != 0), np.sign(d), np.nan)).ffill()
    side = side.where(np.isfinite(d)).values
    prev = np.concatenate([[np.nan], side[:-1]])
    flip = np.isfinite(side) & np.isfinite(prev) & (side != prev)
    return side, np.where(np.isfinite(side), _since(flip), np.nan)


# ----------------------------------------------------------------------------------------------- Fisher Transform
def fisher(df, n=FISH_N):
    """Ehlers' Fisher Transform of the median price over n bars -> frame: fisher, trigger (Fisher one bar earlier).
    NaN until n bars exist; a flat window counts as the middle of the range."""
    med = ((df["high"] + df["low"]) / 2.0).astype(float)
    hh = med.rolling(n, min_periods=n).max().values
    ll = med.rolling(n, min_periods=n).min().values
    m = med.values
    out = np.full(len(m), np.nan)
    x = f = 0.0
    for i in range(len(m)):
        if not (np.isfinite(hh[i]) and np.isfinite(m[i])):
            continue
        rng = hh[i] - ll[i]
        pos = (m[i] - ll[i]) / rng - 0.5 if rng > 0 else 0.0
        x = min(max(0.66 * pos + 0.67 * x, -0.999), 0.999)
        f = 0.5 * np.log((1.0 + x) / (1.0 - x)) + 0.5 * f
        out[i] = f
    fs = pd.Series(out, index=df.index)
    return pd.DataFrame({"fisher": fs, "trigger": fs.shift(1)}, index=df.index)


# ----------------------------------------------------------------------------------------------- Ultimate Oscillator
def ultimate_oscillator(df, periods=UO_N, weights=UO_W):
    """Larry Williams' Ultimate Oscillator in 0..100 (NaN until the longest window exists or when it is flat)."""
    pc = df["close"].shift(1)
    lo = np.minimum(df["low"], pc)
    bp = df["close"] - lo
    tr = np.maximum(df["high"], pc) - lo
    tot = 0.0
    for n, w in zip(periods, weights):
        den = tr.rolling(n, min_periods=n).sum()
        tot = tot + w * bp.rolling(n, min_periods=n).sum() / den.where(den > 0)
    return (100.0 * tot / sum(weights)).clip(0.0, 100.0)


# ----------------------------------------------------------------------------------------------- TRIX
def trix(df, n=TRIX_N, sig=TRIX_SIG):
    """-> frame: trix (one-bar % change of the triple EMA(n) of the close), signal (EMA(sig) of it), atr (TRIX in
    ATR(14) units per bar: the change of the triple EMA over ATR)."""
    c = df["close"].astype(float)
    e3 = pd.Series(_ema(_ema(_ema(c.values, n), n), n), index=df.index)
    chg = e3 - e3.shift(1)
    t = 100.0 * chg / e3.shift(1).where(e3.shift(1) > 0)
    atr = _ind.atr_wilder(df, ATR_N)
    return pd.DataFrame({"trix": t, "signal": _ema(t.values, sig), "atr": chg / atr.where(atr > 0)}, index=df.index)


# ----------------------------------------------------------------------------------------------- regression channel
def linreg_channel(df, n=LRC_N, k=LRC_K):
    """Least-squares line through the last n closes -> frame: slope_pct (% of the close per bar), slope_atr (ATR(14)
    per bar), r2, mid (the line's value on the last bar), se (standard error of the fit, sqrt(SSE / (n - 2))),
    pos ((close - mid) / (k x se): -1 = lower channel line, +1 = upper; not clipped). NaN until n bars exist; a
    perfectly flat window has r2 0 and no position."""
    c = df["close"].values.astype(float)
    N = len(c)
    out = {key: np.full(N, np.nan) for key in ("slope_pct", "slope_atr", "r2", "mid", "se", "pos")}
    if N >= n:
        w = np.lib.stride_tricks.sliding_window_view(c, n)
        xd = np.arange(n) - (n - 1) / 2.0
        mean = w.mean(axis=1)
        slope = (w * xd).sum(axis=1) / (xd ** 2).sum()
        fit = mean[:, None] + slope[:, None] * xd[None, :]
        sse = ((w - fit) ** 2).sum(axis=1)
        sst = ((w - mean[:, None]) ** 2).sum(axis=1)
        last = c[n - 1:]
        mid = fit[:, -1]
        se = np.sqrt(sse / (n - 2.0))
        tiny = 1e-12 * np.maximum(1.0, np.abs(mean))
        atr = _ind.atr_wilder(df, ATR_N).values[n - 1:]
        with np.errstate(invalid="ignore", divide="ignore"):
            out["slope_pct"][n - 1:] = np.where(last > 0, 100.0 * slope / last, np.nan)
            out["slope_atr"][n - 1:] = np.where(atr > 0, slope / atr, np.nan)
            out["r2"][n - 1:] = np.where(sst > tiny ** 2 * n, np.clip(1.0 - sse / sst, 0.0, 1.0), 0.0)
            out["pos"][n - 1:] = np.where(se > tiny, (last - mid) / (k * se), np.nan)
        out["mid"][n - 1:] = mid
        out["se"][n - 1:] = se
    return pd.DataFrame(out, index=df.index)


# ----------------------------------------------------------------------------------------------- Mass Index
def mass_index(df, n=MASS_EMA, m=MASS_SUM):
    """Dorsey's Mass Index: sum over m bars of EMA(n) of (high - low) over the EMA(n) of that EMA."""
    e1 = _ema((df["high"] - df["low"]).values.astype(float), n)
    e2 = _ema(e1, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(e2 > 0, e1 / e2, np.nan)
    return pd.Series(ratio, index=df.index).rolling(m, min_periods=m).sum()


def mass_bulge(mi, set_at=MASS_SET, trigger=MASS_TRIGGER):
    """Bool array: the reversal bulge completes on the bar where the Mass Index falls below `trigger` after having
    been above `set_at` since it was last below `trigger`."""
    v = np.asarray(mi, dtype=float)
    ev = np.zeros(len(v), dtype=bool)
    armed = False
    for i in range(len(v)):
        if not np.isfinite(v[i]):
            continue
        if v[i] > set_at:
            armed = True
        elif v[i] < trigger:
            ev[i], armed = armed, False
    return ev


def mass_frame(df):
    """-> frame: mi, trend (sign of the one-bar change of EMA9 of the close), age (bars since the last bulge
    completed, NaN = none within MASS_HOLD bars), btrend (the trend sign on the bar the bulge completed)."""
    mi = mass_index(df)
    ema = _ema(df["close"].values.astype(float), MASS_EMA)
    trend = np.sign(ema - np.concatenate([[np.nan], ema[:-1]]))
    ev = mass_bulge(mi.values)
    age = _since(ev)
    at = pd.Series(np.where(ev, trend, np.nan)).ffill().values
    live = age <= MASS_HOLD
    return pd.DataFrame({"mi": mi.values, "trend": trend, "age": np.where(live, age, np.nan),
                         "btrend": np.where(live, at, np.nan)}, index=df.index)


# ----------------------------------------------------------------------------------------------- features
def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    errors = {}
    try:
        b = _data.load(asset) if bars is None else bars
        b = b[["open", "high", "low", "close"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    cols = {f: np.full(len(index15), np.nan) for f in FEATURES + RAW}

    def put(part):
        part = part.reindex(index15)
        for col in part.columns:
            cols[col] = part[col].values.astype(float)

    def err(name, ex):
        errors[name] = "%s: %s" % (type(ex).__name__, str(ex)[:160])

    if b is not None and len(b):
        frames = {tag: (b if rule is None else _resample(b, rule)) for tag, rule in TFS4}
        for tag, rule in TFS_FISH:                                      # Fisher Transform, 15m to 4h
            try:
                fr = fisher(frames[tag])
                fr["side"], fr["age"] = _side_and_age(fr["fisher"].values, fr["trigger"].values)
                on = _on15(b, rule, fr)
                f = on["fisher"]
                ext = np.where(f > FISH_EXT, 1.0, np.where(f < -FISH_EXT, -1.0, 0.0))
                put(pd.DataFrame({"fish_raw_" + tag: f, "fish_trig_" + tag: on["trigger"], "fishx_age_" + tag: on["age"],
                                  "fish_" + tag: f / FISH_SCALE, "fishx_" + tag: on["side"],
                                  "fishext_" + tag: np.where(f.notna(), ext, np.nan)}, index=b.index))
            except Exception as ex:
                err("fisher_" + tag, ex)
        for tag, rule in TFS_UO:                                        # Ultimate Oscillator, 15m, 1h, daily
            try:
                on = _on15(b, rule, pd.DataFrame({"u": ultimate_oscillator(frames[tag])}, index=frames[tag].index))
                u = on["u"]
                zone = np.where(u > UO_OB, 1.0, np.where(u < UO_OS, -1.0, 0.0))
                put(pd.DataFrame({"uo_raw_" + tag: u, "uo_" + tag: (u - 50.0) / UO_SCALE,
                                  "uoz_" + tag: np.where(u.notna(), zone, np.nan)}, index=b.index))
            except Exception as ex:
                err("ultosc_" + tag, ex)
        for tag, rule in TFS_HTF:                                       # TRIX, regression channel, Mass Index
            hb = frames[tag]
            try:
                fr = trix(hb)
                fr["side"], fr["age"] = _side_and_age(fr["trix"].values, fr["signal"].values)
                on = _on15(b, rule, fr)
                put(pd.DataFrame({"trix_raw_" + tag: on["trix"], "trix_sig_" + tag: on["signal"],
                                  "trix_atr_" + tag: on["atr"], "trixx_age_" + tag: on["age"],
                                  "trix_" + tag: on["atr"] / TRIX_SCALE, "trixx_" + tag: on["side"],
                                  "trixz_" + tag: np.sign(on["trix"])}, index=b.index))
            except Exception as ex:
                err("trix_" + tag, ex)
            try:
                on = _on15(b, rule, linreg_channel(hb))
                put(pd.DataFrame({"lrc_slope_raw_" + tag: on["slope_pct"], "lrc_slope_atr_" + tag: on["slope_atr"],
                                  "lrc_pos_raw_" + tag: on["pos"], "lrc_mid_" + tag: on["mid"], "lrc_se_" + tag: on["se"],
                                  "lrc_slope_" + tag: on["slope_atr"] / LRC_SLOPE_SCALE, "lrc_r2_" + tag: on["r2"],
                                  "lrc_pos_" + tag: on["pos"]}, index=b.index))
            except Exception as ex:
                err("linreg_" + tag, ex)
            try:
                on = _on15(b, rule, mass_frame(hb))
                put(pd.DataFrame({"mass_raw_" + tag: on["mi"], "mass_trend_" + tag: on["trend"],
                                  "massb_age_" + tag: on["age"], "massb_trend_" + tag: on["btrend"],
                                  "mass_" + tag: (on["mi"] - MASS_MID) / MASS_SCALE,
                                  "massb_" + tag: -on["btrend"].fillna(0.0) * _fade(on["age"].values, MASS_HOLD)},
                                 index=b.index))
            except Exception as ex:
                err("mass_" + tag, ex)
    out = pd.DataFrame(cols, index=index15)[FEATURES + RAW]
    out[FEATURES] = out[FEATURES].astype(float).fillna(0.0).clip(-1.0, 1.0)
    out.attrs["errors"] = errors
    return out


# ----------------------------------------------------------------------------------------------- describe
def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _plural(n, word="bar"):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def _ago(n):
    return "on the last closed bar" if n == 0 else "%s ago" % _plural(n)


def _cross(side, age, line):
    """'above its trigger (crossed up 3 bars ago)' from a side (+1/-1) and the age of the last cross."""
    if side is None or side == 0:
        return "level with its %s" % line
    txt = "%s its %s" % ("above" if side > 0 else "below", line)
    if age is not None:
        txt += " (crossed %s %s)" % ("up" if side > 0 else "down", _ago(int(age)))
    return txt


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what is read; forecasts nothing."""
    say = OrderedDict()
    bits = []
    for tag, _ in TFS_FISH:
        f = _num(row, "fish_raw_" + tag)
        if f is None:
            bits.append("%s no read" % tag)
            continue
        ext = (", extreme high (above +%g)" % FISH_EXT if f > FISH_EXT else
               ", extreme low (below -%g)" % FISH_EXT if f < -FISH_EXT else "")
        bits.append("%s %+.2f %s%s" % (tag, f, _cross(_num(row, "fishx_" + tag), _num(row, "fishx_age_" + tag),
                                                      "trigger"), ext))
    say[GROUPS["fisher"][0]] = "Fisher Transform (%d): %s." % (FISH_N, "; ".join(bits))

    bits = []
    for tag, _ in TFS_UO:
        u = _num(row, "uo_raw_" + tag)
        if u is None:
            bits.append("%s no read" % tag)
            continue
        zone = (" overbought (above %g)" % UO_OB if u > UO_OB else " oversold (below %g)" % UO_OS if u < UO_OS else
                " (buying pressure ahead)" if u > 50 else " (selling pressure ahead)" if u < 50 else "")
        bits.append("%s %.0f%s" % (tag, u, zone))
    say[GROUPS["ultosc"][0]] = "Ultimate Oscillator (%d/%d/%d): %s." % (UO_N + ("; ".join(bits),))

    bits = []
    for tag, _ in TFS_HTF:
        t = _num(row, "trix_raw_" + tag)
        if t is None:
            bits.append("%s no read" % tag)
            continue
        zero = "above zero" if t > 0 else ("below zero" if t < 0 else "at zero")
        if _num(row, "trix_sig_" + tag) is None:
            bits.append("%s %+.3f%% (%s)" % (tag, t, zero))
        else:
            bits.append("%s %+.3f%% (%s), %s" % (tag, t, zero, _cross(_num(row, "trixx_" + tag),
                                                                     _num(row, "trixx_age_" + tag), "signal line")))
    say[GROUPS["trix"][0]] = "TRIX (%d, signal %d), %% per bar: %s." % (TRIX_N, TRIX_SIG, "; ".join(bits))

    bits = []
    for tag, _ in TFS_HTF:
        s, r2 = _num(row, "lrc_slope_raw_" + tag), _num(row, "lrc_r2_" + tag)
        if s is None or _num(row, "lrc_mid_" + tag) is None:
            bits.append("%s no read" % tag)
            continue
        way = "rising" if s > 0 else ("falling" if s < 0 else "flat")
        straight = "a straight move" if r2 >= 0.7 else ("a loose trend" if r2 >= 0.3 else "no clear line")
        p = _num(row, "lrc_pos_raw_" + tag)
        if p is None:
            where = "close on the line"
        elif p > 1.0:
            where = "close above the upper channel line"
        elif p < -1.0:
            where = "close below the lower channel line"
        else:
            where = "close %.0f%% of the way from the middle to the %s line" % (abs(p) * 100.0, "upper" if p >= 0 else "lower")
        bits.append("%s %s %+.3f%% per bar, R-squared %.2f (%s), %s" % (tag, way, s, r2, straight, where))
    say[GROUPS["linreg"][0]] = ("Linear-regression channel (%d bars, +/-%g standard errors): %s."
                                % (LRC_N, LRC_K, "; ".join(bits)))

    bits = []
    for tag, _ in TFS_HTF:
        m = _num(row, "mass_raw_" + tag)
        if m is None:
            bits.append("%s no read" % tag)
            continue
        age, bt, tr = _num(row, "massb_age_" + tag), _num(row, "massb_trend_" + tag), _num(row, "mass_trend_" + tag)
        if age is not None:
            was = "an up-move" if (bt or 0) > 0 else ("a down-move" if (bt or 0) < 0 else "a flat market")
            txt = "reversal bulge completed %s during %s" % (_ago(int(age)), was)
        elif m > MASS_SET:
            txt = "above %g, bulge forming, EMA%d %s" % (MASS_SET, MASS_EMA,
                                                        "rising" if (tr or 0) > 0 else "falling" if (tr or 0) < 0 else "flat")
        else:
            txt = "no bulge"
        bits.append("%s %.1f, %s" % (tag, m, txt))
    say[GROUPS["mass"][0]] = ("Mass Index (%d/%d; bulge = above %g then back below %g): %s."
                              % (MASS_EMA, MASS_SUM, MASS_SET, MASS_TRIGGER, "; ".join(bits)))
    return say
