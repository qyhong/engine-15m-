# -*- coding: utf-8 -*-
"""osc4 -- card pipeline batch 3 (owner's go, 16 Nov 2026): five reading-only cards from the asset's own bars.

  willr    Williams %R (15m to daily)                %R(14) = -100 x (highest high - close) / (highest high - lowest low)
                                                     on 15m, 1h, 4h, 1d; feature (%R + 50) / 50; above -20 overbought,
                                                     below -80 oversold
  cmf      Chaikin money flow and OBV (1h to daily)  CMF(20) on 1h, 4h, 1d (feature CMF / 0.25, clipped) and an OBV
                                                     divergence flag: the close makes a new 20-bar closing high (low)
                                                     that OBV does not; feature fades over 5 bars. Needs volume
  elder    Elder-Ray (1h to daily)                   bull power = high - EMA13, bear power = low - EMA13, in ATR(14) of
                                                     that timeframe (feature / 2, clipped), and the EMA13 slope sign
  pivots   Pivot points (daily and weekly)           classic P, R1-R3, S1-S3 and Camarilla H3/H4/L3/L4 from the prior
                                                     completed UTC day and prior completed week (Monday 00:00 UTC);
                                                     price against P, which classic zone it is in, where it sits on
                                                     the Camarilla scale, and the nearest level above / below in daily ATRs
  rsidiv   RSI divergence (15m to 4h)                regular divergence between the last two confirmed swing highs (lows)
                                                     of price and RSI(14) at those bars; a swing is confirmed SWING_K = 3
                                                     bars after it (3 bars each side), so the signal appears only then;
                                                     age in bars of that timeframe; feature fades over 20 bars

THE ONE RULE (tests/test_sources_osc4.py): row i uses only what was known at the close of 15m bar i. A higher
timeframe's value reaches a 15m row only once that higher bar has closed (data.htf_on_15). The weekly pivots are
computed on weekly bars and handed over through data.htf_on_15 as a bar that closes at the next Monday 00:00 UTC.
Nothing is fetched: update() does nothing. No card votes until the owner's card rating promotes it; no reading is
claimed to predict.

Volume: USDJPY's live feed carries no volume, so the CMF / OBV card is "no read" on every row there (as osc2 does for
MFI). For any asset a window is read only if at least half its bars carry volume > 0.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

TFS4 = (("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D"))
TFS_HTF = TFS4[1:]                              # 1h, 4h, 1d
TFS_DIV = TFS4[:3]                              # 15m, 1h, 4h
NO_VOLUME = ("USDJPY",)
VOL_SHARE = 0.5

WR_N, WR_OB, WR_OS = 14, -20.0, -80.0
CMF_N, CMF_SCALE = 20, 0.25
OBV_N, OBV_HOLD = 20, 5                         # new 20-bar closing high/low; the flag fades over 5 bars
EMA_N, ATR_N = 13, 14
ELDER_SCALE = 2.0                               # feature = power in ATRs / 2, clipped
RSI_N, SWING_K, DIV_MAX_GAP, DIV_HOLD = 14, 3, 60, 20
MIN_DAY_BARS, MIN_WEEK_BARS = 16, 64            # a thinner UTC day / week is skipped: the one before it stays in use
CLASSIC = ("s3", "s2", "s1", "p", "r1", "r2", "r3")
CAMARILLA = ("l4", "l3", "h3", "h4")
LEVELS = CLASSIC + CAMARILLA
LEVEL_NAME = {"p": "P", "r1": "R1", "r2": "R2", "r3": "R3", "s1": "S1", "s2": "S2", "s3": "S3",
              "h3": "H3", "h4": "H4", "l3": "L3", "l4": "L4"}
ZONES = ("below S3", "S3-S2", "S2-S1", "S1-P", "P-R1", "R1-R2", "R2-R3", "above R3")
PIV_TAGS = (("day", "daily"), ("wk", "weekly"))

GROUPS = OrderedDict([
    ("willr", ("Williams %R (15m to daily)", ["wr_%s" % t for t, _ in TFS4])),
    ("cmf", ("Chaikin money flow and OBV (1h to daily)",
             ["cmf_%s" % t for t, _ in TFS_HTF] + ["obvdiv_%s" % t for t, _ in TFS_HTF])),
    ("elder", ("Elder-Ray (1h to daily)",
               ["eld_bull_%s" % t for t, _ in TFS_HTF] + ["eld_bear_%s" % t for t, _ in TFS_HTF]
               + ["eld_slope_%s" % t for t, _ in TFS_HTF])),
    ("pivots", ("Pivot points (daily and weekly)",
                ["pvt_%s_%s" % (k, w) for w, _ in PIV_TAGS for k in ("pos", "zone", "cam")])),
    ("rsidiv", ("RSI divergence (15m to 4h)", ["rdiv_%s" % t for t, _ in TFS_DIV])),
])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = (["wr_raw_%s" % t for t, _ in TFS4]
       + ["cmf_raw_%s" % t for t, _ in TFS_HTF] + ["obvdiv_bull_age_%s" % t for t, _ in TFS_HTF]
       + ["obvdiv_bear_age_%s" % t for t, _ in TFS_HTF]
       + ["eld_bull_raw_%s" % t for t, _ in TFS_HTF] + ["eld_bear_raw_%s" % t for t, _ in TFS_HTF]
       + ["eld_ema_%s" % t for t, _ in TFS_HTF]
       + ["pvt_%s_%s" % (k, w) for w, _ in PIV_TAGS for k in LEVELS]
       + ["pvt_%s_%s" % (k, w) for w, _ in PIV_TAGS for k in ("above_px", "above_atr", "below_px", "below_atr")]
       + ["pvt_atr_d"]
       + ["rdiv_bull_age_%s" % t for t, _ in TFS_DIV] + ["rdiv_bear_age_%s" % t for t, _ in TFS_DIV]
       + ["rdiv_rsi_%s" % t for t, _ in TFS_DIV])


def update(log=print):
    """Nothing to fetch: all five cards are computed from the asset's own bars."""
    return {}


# ----------------------------------------------------------------------------------------------- bar helpers
def _resample(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    agg["volume"] = b["volume"].resample(rule, label="left", closed="left").sum(min_count=1)
    agg["nbars"] = b["close"].resample(rule, label="left", closed="left").count()
    return agg.dropna(subset=["close"])


def _on15(b, rule, frame):
    """A frame on the bars of `rule` (None = the 15m bars themselves) -> the same columns on b's 15m index."""
    out = frame if rule is None else _data.htf_on_15(b, rule, frame)
    return out.reindex(b.index)


def _vol_ok(v, n):
    """True where at least VOL_SHARE of the last n bars carry volume > 0 (NaN counts as none)."""
    pos = (np.nan_to_num(np.asarray(v, dtype=float), nan=0.0) > 0).astype(float)
    return pd.Series(pos).rolling(n, min_periods=n).mean().values >= VOL_SHARE


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


# ----------------------------------------------------------------------------------------------- Williams %R
def williams_r(df, n=WR_N):
    """%R(n) in -100..0 over the last n bars (NaN until n bars exist or when the window is flat)."""
    hh = df["high"].rolling(n, min_periods=n).max()
    ll = df["low"].rolling(n, min_periods=n).min()
    rng = (hh - ll).where(hh > ll)
    return (-100.0 * (hh - df["close"]) / rng).clip(-100.0, 0.0)


# ----------------------------------------------------------------------------------------------- CMF, OBV
def cmf(df, n=CMF_N):
    """Chaikin money flow(n) in -1..1: sum of ((C-L) - (H-C)) / (H-L) x volume over sum of volume (a bar with
    H == L adds volume but no flow). NaN when fewer than half the window's bars carry volume."""
    h, l, c = df["high"], df["low"], df["close"]
    v = df["volume"].astype(float).fillna(0.0)
    rng = h - l
    mult = (((c - l) - (h - c)) / rng.where(rng > 0)).fillna(0.0)
    num = (mult * v).rolling(n, min_periods=n).sum()
    den = v.rolling(n, min_periods=n).sum()
    out = num / den.where(den > 0)
    return out.where(_vol_ok(df["volume"].values, n)).clip(-1.0, 1.0)


def obv(df):
    """On-balance volume from the first bar (missing volume counts 0); only its changes are read."""
    v = df["volume"].astype(float).fillna(0.0)
    return (np.sign(df["close"].diff()).fillna(0.0) * v).cumsum()


def obv_divergence(df, n=OBV_N):
    """-> (bearish, bullish) bool arrays: the close makes a new n-bar closing high (low) -- above (below) every one
    of the previous n-1 closes -- and OBV does not make its own new n-bar high (low) on that bar."""
    c, o = df["close"].astype(float), obv(df)
    ok = _vol_ok(df["volume"].values, n)
    c_hi, c_lo = c.shift(1).rolling(n - 1, min_periods=n - 1).max(), c.shift(1).rolling(n - 1, min_periods=n - 1).min()
    o_hi, o_lo = o.shift(1).rolling(n - 1, min_periods=n - 1).max(), o.shift(1).rolling(n - 1, min_periods=n - 1).min()
    bear = ((c > c_hi) & ~(o > o_hi)).values & ok
    bull = ((c < c_lo) & ~(o < o_lo)).values & ok
    return bear, bull


# ----------------------------------------------------------------------------------------------- Elder-Ray
def elder_ray(df, n=EMA_N):
    """-> frame: ema13, bull/bear power (high/low - EMA13) in ATR(14) units, EMA slope sign (+1/-1/0)."""
    ema = _ind.ema_seeded(df["close"].astype(float), n)
    atr = _ind.atr_wilder(df, ATR_N)
    atr = atr.where(atr > 0)
    slope = np.sign(ema - ema.shift(1))
    return pd.DataFrame({"ema": ema, "bull": (df["high"] - ema) / atr, "bear": (df["low"] - ema) / atr,
                         "slope": slope}, index=df.index)


# ----------------------------------------------------------------------------------------------- pivots
def pivot_levels(h, l, c):
    """Classic floor pivots and Camarilla H3/H4/L3/L4 from one period's high, low, close (scalars or arrays)."""
    p = (h + l + c) / 3.0
    r = h - l
    return OrderedDict([
        ("s3", l - 2.0 * (h - p)), ("s2", p - r), ("s1", 2.0 * p - h), ("p", p),
        ("r1", 2.0 * p - l), ("r2", p + r), ("r3", h + 2.0 * (p - l)),
        ("l4", c - 1.1 * r / 2.0), ("l3", c - 1.1 * r / 4.0), ("h3", c + 1.1 * r / 4.0), ("h4", c + 1.1 * r / 2.0),
    ])


def _week_bars(b):
    """Weekly OHLC + bar count, weeks starting Monday 00:00 UTC, keyed by the week's start."""
    day = b.index.normalize()
    start = day - pd.to_timedelta(b.index.weekday.values.astype("int64"), unit="D")
    start = pd.DatetimeIndex(start).as_unit(b.index.unit)
    g = b.groupby(start)
    wk = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(),
                       "nbars": g["close"].count()})
    return wk.dropna(subset=["close"])


def _pivot_frame(hb, min_bars):
    """Levels from each period's own H/L/C (thin periods carry the previous period's levels), keyed like hb."""
    lv = pivot_levels(hb["high"], hb["low"], hb["close"])
    out = pd.DataFrame(lv, index=hb.index)
    out["cl"] = hb["close"]
    out["rng"] = hb["high"] - hb["low"]
    out[hb["nbars"].values < min_bars] = np.nan
    return out.ffill()


def _pivots_on15(b, d1):
    """-> frame on b's index with all pivot readings."""
    out = pd.DataFrame(index=b.index)
    atr_d = _on15(b, "1D", pd.DataFrame({"a": _ind.atr_wilder(d1, ATR_N)}, index=d1.index))["a"].values
    atr_d = np.where(atr_d > 0, atr_d, np.nan)
    out["pvt_atr_d"] = atr_d
    c = b["close"].values
    day = _on15(b, "1D", _pivot_frame(d1, MIN_DAY_BARS))
    wkf = _pivot_frame(_week_bars(b), MIN_WEEK_BARS)
    wkf.index = wkf.index + pd.Timedelta(days=6)          # the week's last day: as a 1D bar it closes next Monday 00:00
    week = _on15(b, "1D", wkf)
    for tag, f in (("day", day), ("wk", week)):
        L = np.column_stack([f[k].values for k in LEVELS])
        for j, k in enumerate(LEVELS):
            out["pvt_%s_%s" % (k, tag)] = L[:, j]
        good = np.isfinite(L).all(axis=1)
        with np.errstate(invalid="ignore"):
            up = np.where(L > c[:, None], L - c[:, None], np.inf).min(axis=1)
            dn = np.where(L <= c[:, None], c[:, None] - L, np.inf).min(axis=1)
            up = np.where(good & np.isfinite(up), up, np.nan)
            dn = np.where(good & np.isfinite(dn), dn, np.nan)
            out["pvt_above_px_" + tag], out["pvt_below_px_" + tag] = c + up, c - dn
            out["pvt_above_atr_" + tag], out["pvt_below_atr_" + tag] = up / atr_d, dn / atr_d
            p = f["p"].values
            cls = np.column_stack([f[k].values for k in CLASSIC])
            zone = ((cls <= c[:, None]).sum(axis=1) - 3.5) / 3.5
            half = 1.1 * f["rng"].values / 2.0
            cam = (c - f["cl"].values) / np.where(half > 0, half, np.nan)
        out["pvt_pos_" + tag] = np.where(good, np.clip((c - p) / atr_d / 2.0, -1.0, 1.0), np.nan)
        out["pvt_zone_" + tag] = np.where(good, zone, np.nan)
        out["pvt_cam_" + tag] = np.where(good, np.clip(cam, -1.0, 1.0), np.nan)
    return out


# ----------------------------------------------------------------------------------------------- RSI divergence
def _swings(x, k, high):
    """Bool array: bar j is a swing high (low) -- above (below) each of the k bars before it and at least (most) each
    of the k bars after it. Bar j's flag uses bars up to j + k, so it is read only from bar j + k on."""
    s = pd.Series(np.asarray(x, dtype=float))
    if not high:
        s = -s
    left = s.shift(1).rolling(k, min_periods=k).max()
    right = s[::-1].shift(1).rolling(k, min_periods=k).max()[::-1]
    return ((s > left) & (s >= right)).values


def rsi_divergence(df, k=SWING_K, n=RSI_N, max_gap=DIV_MAX_GAP):
    """-> frame on df's index: rsi, bull_age / bear_age (bars since the divergence was confirmed, NaN = none active
    within DIV_HOLD bars). Regular bearish: the last two confirmed swing highs have price higher, RSI lower;
    bullish: the last two confirmed swing lows have price lower, RSI higher; the two swings at most max_gap bars apart.
    A swing at bar j is confirmed at bar j + k; nothing before that bar sees it."""
    r = _ind.rsi(df["close"].astype(float), n).values.copy()
    r[:n] = np.nan
    N = len(r)
    out = {"rsi": r}
    i = np.arange(N)
    for name, col, high in (("bear", "high", True), ("bull", "low", False)):
        px = df[col].values.astype(float)
        sw = np.flatnonzero(_swings(px, k, high) & np.isfinite(r))
        conf = sw + k
        m = np.searchsorted(conf, i, side="right")             # swings confirmed by bar i
        age = np.full(N, np.nan)
        has = m >= 2
        if has.any():
            j2 = sw[np.maximum(m - 1, 0)]
            j1 = sw[np.maximum(m - 2, 0)]
            if high:
                div = (px[j2] > px[j1]) & (r[j2] < r[j1])
            else:
                div = (px[j2] < px[j1]) & (r[j2] > r[j1])
            a = i - conf[np.maximum(m - 1, 0)]
            act = has & div & ((j2 - j1) <= max_gap) & (a <= DIV_HOLD)
            age = np.where(act, a, np.nan).astype(float)
        out[name + "_age"] = age
    return pd.DataFrame(out, index=df.index)


# ----------------------------------------------------------------------------------------------- features
def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    errors = {}
    try:
        b = _data.load(asset) if bars is None else bars
        b = b.copy()
        if "volume" not in b.columns:
            b["volume"] = np.nan
        b = b[["open", "high", "low", "close", "volume"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
        if str(asset).upper() in NO_VOLUME:
            b["volume"] = np.nan
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    cols = {f: np.full(len(index15), np.nan) for f in FEATURES + RAW}

    def put(part):
        part = part.reindex(index15)
        for col in part.columns:
            cols[col] = part[col].values.astype(float)

    if b is not None and len(b):
        frames = {tag: (b if rule is None else _resample(b, rule)) for tag, rule in TFS4}
        rules = dict(TFS4)
        for tag, rule in TFS4:                                          # Williams %R, 15m to daily
            try:
                on = _on15(b, rule, pd.DataFrame({"w": williams_r(frames[tag])}, index=frames[tag].index))
                put(pd.DataFrame({"wr_raw_" + tag: on["w"], "wr_" + tag: (on["w"] + 50.0) / 50.0}, index=b.index))
            except Exception as ex:
                errors["willr_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        for tag, rule in TFS_HTF:                                       # CMF / OBV and Elder-Ray, 1h to daily
            hb = frames[tag]
            try:
                bear, bull = obv_divergence(hb)
                ba, ua = _since(bear), _since(bull)
                fr = pd.DataFrame({"cmf": cmf(hb).values, "ua": np.where(ua <= OBV_HOLD, ua, np.nan),
                                   "ba": np.where(ba <= OBV_HOLD, ba, np.nan)}, index=hb.index)
                on = _on15(b, rule, fr)
                put(pd.DataFrame({"cmf_raw_" + tag: on["cmf"], "cmf_" + tag: on["cmf"] / CMF_SCALE,
                                  "obvdiv_bull_age_" + tag: on["ua"], "obvdiv_bear_age_" + tag: on["ba"],
                                  "obvdiv_" + tag: _fade(on["ua"].values, OBV_HOLD) - _fade(on["ba"].values, OBV_HOLD)},
                                 index=b.index))
            except Exception as ex:
                errors["cmf_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
            try:
                on = _on15(b, rule, elder_ray(hb))
                put(pd.DataFrame({"eld_bull_raw_" + tag: on["bull"], "eld_bear_raw_" + tag: on["bear"],
                                  "eld_ema_" + tag: on["ema"], "eld_bull_" + tag: on["bull"] / ELDER_SCALE,
                                  "eld_bear_" + tag: on["bear"] / ELDER_SCALE, "eld_slope_" + tag: on["slope"]},
                                 index=b.index))
            except Exception as ex:
                errors["elder_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        try:
            put(_pivots_on15(b, frames["1d"]))
        except Exception as ex:
            errors["pivots"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        for tag, rule in TFS_DIV:                                       # RSI divergence, 15m to 4h
            try:
                on = _on15(b, rules[tag], rsi_divergence(frames[tag]))
                put(pd.DataFrame({"rdiv_rsi_" + tag: on["rsi"], "rdiv_bull_age_" + tag: on["bull_age"],
                                  "rdiv_bear_age_" + tag: on["bear_age"],
                                  "rdiv_" + tag: _fade(on["bull_age"].values, DIV_HOLD)
                                  - _fade(on["bear_age"].values, DIV_HOLD)}, index=b.index))
            except Exception as ex:
                errors["rsidiv_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
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


def _no_volume_note(asset):
    if str(asset).upper() in NO_VOLUME:
        return "no read, %s's price feed carries no usable volume" % asset
    return "no read, not enough bars with volume"


def _plural(n, word="bar"):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def _ago(n):
    return "on the last closed bar" if n == 0 else "%s ago" % _plural(n)


def _level_name(row, tag, px):
    if px is None:
        return None
    for k in LEVELS:
        v = _num(row, "pvt_%s_%s" % (k, tag))
        if v is not None and np.isclose(v, px, rtol=0.0, atol=1e-9 * max(1.0, abs(px))):
            return LEVEL_NAME[k]
    return None


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what is read; forecasts nothing."""
    say = OrderedDict()
    bits = []
    for tag, _ in TFS4:
        w = _num(row, "wr_raw_" + tag)
        if w is None:
            bits.append("%s no read" % tag)
            continue
        zone = " overbought (above -20)" if w > WR_OB else (" oversold (below -80)" if w < WR_OS else "")
        bits.append("%s %.0f%s" % (tag, w, zone))
    say[GROUPS["willr"][0]] = "Williams %%R (14): %s." % "; ".join(bits)

    if all(_num(row, "cmf_raw_" + t) is None for t, _ in TFS_HTF):
        say[GROUPS["cmf"][0]] = "Chaikin money flow (20) and OBV: %s." % _no_volume_note(asset)
    else:
        bits = []
        for tag, _ in TFS_HTF:
            m = _num(row, "cmf_raw_" + tag)
            if m is None:
                bits.append("%s no read" % tag)
                continue
            ua, ba = _num(row, "obvdiv_bull_age_" + tag), _num(row, "obvdiv_bear_age_" + tag)
            div = []
            if ba is not None:
                div.append("new %d-bar closing high not confirmed by OBV %s" % (OBV_N, _ago(ba)))
            if ua is not None:
                div.append("new %d-bar closing low not confirmed by OBV %s" % (OBV_N, _ago(ua)))
            flow = "buying" if m > 0.05 else ("selling" if m < -0.05 else "neutral")
            bits.append("%s CMF %+.2f (%s)%s" % (tag, m, flow, (", " + " and ".join(div)) if div else ", no OBV divergence"))
        say[GROUPS["cmf"][0]] = "Chaikin money flow (20) and OBV: %s." % "; ".join(bits)

    bits = []
    for tag, _ in TFS_HTF:
        bu, be, sl = _num(row, "eld_bull_raw_" + tag), _num(row, "eld_bear_raw_" + tag), _num(row, "eld_slope_" + tag)
        if bu is None or be is None:
            bits.append("%s no read" % tag)
            continue
        slope = "" if sl is None else (", EMA13 rising" if sl > 0 else ", EMA13 falling" if sl < 0 else ", EMA13 flat")
        bits.append("%s bull power %+.2f ATR, bear power %+.2f ATR%s" % (tag, bu, be, slope))
    say[GROUPS["elder"][0]] = "Elder-Ray (EMA13, ATR14 units): %s." % "; ".join(bits)

    bits = []
    for tag, name in PIV_TAGS:
        pp = _num(row, "pvt_p_" + tag)                      # the pivot level itself (raw)
        z = _num(row, "pvt_zone_" + tag)
        if pp is None or z is None:
            bits.append("%s no read" % name)
            continue
        zone = ZONES[int(round(z * 3.5 + 3.5))]
        side = "above" if z >= 0 else "below"
        cam = _num(row, "pvt_cam_" + tag)
        camtxt = ""
        if cam is not None:
            camtxt = (", Camarilla at or above H4" if cam >= 1.0 else ", Camarilla between H3 and H4" if cam >= 0.5 else
                      ", Camarilla at or below L4" if cam <= -1.0 else ", Camarilla between L4 and L3" if cam <= -0.5 else
                      ", Camarilla inside L3-H3")
        near = []
        for way in ("above", "below"):
            px, at = _num(row, "pvt_%s_px_%s" % (way, tag)), _num(row, "pvt_%s_atr_%s" % (way, tag))
            nm = _level_name(row, tag, px)
            if px is None or nm is None:
                near.append("nothing %s" % way)
            else:
                near.append("%s %s %.5g%s" % (way, nm, px, "" if at is None else " (%.2f daily ATR)" % at))
        bits.append("%s P %.5g with price %s it in %s%s, nearest %s" % (name, pp, side, zone, camtxt, " and ".join(near)))
    say[GROUPS["pivots"][0]] = "Pivot points: %s." % "; ".join(bits)

    bits = []
    for tag, _ in TFS_DIV:
        r = _num(row, "rdiv_rsi_" + tag)
        if r is None:
            bits.append("%s no read" % tag)
            continue
        ua, ba = _num(row, "rdiv_bull_age_" + tag), _num(row, "rdiv_bear_age_" + tag)
        div = []
        if ba is not None:
            div.append("bearish divergence (higher price high, lower RSI high) confirmed %s" % _ago(ba))
        if ua is not None:
            div.append("bullish divergence (lower price low, higher RSI low) confirmed %s" % _ago(ua))
        bits.append("%s RSI %.0f, %s" % (tag, r, " and ".join(div) if div else "no divergence"))
    say[GROUPS["rsidiv"][0]] = ("RSI (14) divergence, swings confirmed %d bars after: %s." % (SWING_K, "; ".join(bits)))
    return say
