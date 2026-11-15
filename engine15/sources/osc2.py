# -*- coding: utf-8 -*-
"""osc2 -- card pipeline batch 2 (owner's go, 15 Nov 2026): five reading-only cards from the asset's own bars.

  psar      Parabolic SAR (15m to daily)          Wilder PSAR (step 0.02, max 0.2) direction on 15m, 1h, 4h, 1d
                                                  (+1 up / -1 down), how many agree; raw: SAR level, distance from
                                                  the close in ATR(14) of that timeframe, bars since the last flip
  mfi       Money Flow Index (15m to daily)       MFI(14) on each timeframe, scaled (mfi - 50) / 50; >= 80
                                                  overbought, <= 20 oversold. Needs volume (see NO_VOLUME)
  vprofile  Volume profile (session and 7 days)   volume at price from 15m bars over the UTC day so far and the
                                                  trailing 7 days: point of control, 70% value area; where the close
                                                  sits against the value area and how far from the POC (daily ATRs)
  heikin    Heikin-Ashi trend (15m to 4h)         HA candle colour, length of the current colour run, and the
                                                  "strong" candle (no wick on the side opposite its colour)
  aroon     Aroon and Vortex (1h to daily)        Aroon(25) up / down / oscillator and Vortex(14) VI+ minus VI-

THE ONE RULE (tests/test_sources_osc2.py): row i uses only what was known at the close of 15m bar i. A higher
timeframe's value reaches a 15m row only once that higher bar has closed (data.htf_on_15). Nothing is fetched:
update() does nothing. No card votes until the owner's card rating promotes it; no reading is claimed to predict.

Volume: USDJPY's live feed carries no volume (always 0 since the Yahoo join, docs/EXTDATA.md), so its MFI and volume
profile are "no read" on every row. For any asset a window is read only if at least half its bars carry volume > 0.
Gold, silver and the S&P change volume source at the data join (Dukascopy quoted size before, Yahoo after).
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind

TFS4 = (("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D"))
TFS_HA = TFS4[:3]
TFS_AR = TFS4[1:]
NO_VOLUME = ("USDJPY",)                     # live feed has no volume: never read MFI / volume profile here

PSAR_STEP, PSAR_MAX = 0.02, 0.2
ATR_N = 14
MFI_N = 14
OB, OS = 80.0, 20.0
VOL_SHARE = 0.5                             # a window is read only if >= this share of its bars has volume > 0
VP_BIN_ATR = 0.1                            # profile bin = 0.1 x ATR(14) of the last closed daily bar
VP_KMAX = 200                               # at most this many bins (wider bins if the range needs more)
VP_VALUE = 0.70                             # value area = 70% of the window's volume
VP_MIN_DAY, VP_MIN_7D = 4, 96               # bars needed before a profile is read
VP_CHUNK = 1024
HA_RUN_CAP = 10
AROON_N, VORTEX_N = 25, 14
VTX_SCALE = 0.5                             # feature = clip((VI+ - VI-) / 0.5, -1, 1)

GROUPS = OrderedDict([
    ("psar", ("Parabolic SAR (15m to daily)",
              ["psar_15m", "psar_1h", "psar_4h", "psar_1d", "psar_agree"])),
    ("mfi", ("Money Flow Index (15m to daily)", ["mfi_15m", "mfi_1h", "mfi_4h", "mfi_1d"])),
    ("vprofile", ("Volume profile (session and 7 days)", ["vpf_pos_day", "vpf_poc_day", "vpf_pos_7d", "vpf_poc_7d"])),
    ("heikin", ("Heikin-Ashi trend (15m to 4h)",
                ["ha_col_%s" % t for t, _ in TFS_HA] + ["ha_run_%s" % t for t, _ in TFS_HA]
                + ["ha_strong_%s" % t for t, _ in TFS_HA])),
    ("aroon", ("Aroon and Vortex (1h to daily)",
               ["aro_up_%s" % t for t, _ in TFS_AR] + ["aro_dn_%s" % t for t, _ in TFS_AR]
               + ["aro_osc_%s" % t for t, _ in TFS_AR] + ["vtx_%s" % t for t, _ in TFS_AR])),
])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = (["psar_lvl_%s" % t for t, _ in TFS4] + ["psar_dist_%s" % t for t, _ in TFS4]
       + ["psar_since_%s" % t for t, _ in TFS4]
       + ["mfi_raw_%s" % t for t, _ in TFS4]
       + ["vpf_%s_%s" % (k, w) for w in ("day", "7d") for k in ("poc_px", "vah_px", "val_px", "poc_atr")]
       + ["ha_runlen_%s" % t for t, _ in TFS_HA]
       + ["aro_up_raw_%s" % t for t, _ in TFS_AR] + ["aro_dn_raw_%s" % t for t, _ in TFS_AR]
       + ["vtx_plus_%s" % t for t, _ in TFS_AR] + ["vtx_minus_%s" % t for t, _ in TFS_AR])


def update(log=print):
    """Nothing to fetch: all five cards are computed from the asset's own bars."""
    return {}


# ----------------------------------------------------------------------------------------------- bar helpers
def _resample(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    agg["volume"] = b["volume"].resample(rule, label="left", closed="left").sum(min_count=1)
    return agg.dropna(subset=["close"])


def _on15(b, rule, frame):
    """A frame on the bars of `rule` (None = the 15m bars themselves) -> the same columns on b's 15m index."""
    out = frame if rule is None else _data.htf_on_15(b, rule, frame)
    return out.reindex(b.index)


def _vol_ok(v, n):
    """True where at least VOL_SHARE of the last n bars carry volume > 0 (NaN counts as none)."""
    pos = (np.nan_to_num(np.asarray(v, dtype=float), nan=0.0) > 0).astype(float)
    return pd.Series(pos).rolling(n, min_periods=n).mean().values >= VOL_SHARE


# ----------------------------------------------------------------------------------------------- Parabolic SAR
def psar(df, step=PSAR_STEP, mx=PSAR_MAX):
    """Wilder's Parabolic SAR -> (sar level as charts draw it under / over each bar, direction +1/-1 (0 = none),
    bars since the last flip (NaN before the first)). Seeded on the first two bars; nothing looks ahead."""
    h, l, c = (df[k].values.astype(float).tolist() for k in ("high", "low", "close"))
    n = len(c)
    sar, dr, since = np.full(n, np.nan), np.zeros(n), np.full(n, np.nan)
    if n < 2:
        return sar, dr, since
    up = c[1] >= c[0]
    ep = max(h[0], h[1]) if up else min(l[0], l[1])
    s = min(l[0], l[1]) if up else max(h[0], h[1])
    af, flip = step, -1
    sar[1], dr[1] = s, (1.0 if up else -1.0)
    for i in range(2, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, l[i - 1], l[i - 2])
            if l[i] < s:
                up, s, ep, af, flip = False, ep, l[i], step, i
            elif h[i] > ep:
                ep, af = h[i], min(af + step, mx)
        else:
            s = max(s, h[i - 1], h[i - 2])
            if h[i] > s:
                up, s, ep, af, flip = True, ep, h[i], step, i
            elif l[i] < ep:
                ep, af = l[i], min(af + step, mx)
        sar[i] = s
        dr[i] = 1.0 if up else -1.0
        if flip >= 0:
            since[i] = float(i - flip)
    return sar, dr, since


def _psar_frame(hb):
    sar, dr, since = psar(hb)
    atr = _ind.atr_wilder(hb, ATR_N).values
    dist = (hb["close"].values - sar) / np.where(atr > 0, atr, np.nan)
    return pd.DataFrame({"dir": np.where(dr != 0, dr, np.nan), "lvl": sar, "dist": dist, "since": since}, index=hb.index)


# ----------------------------------------------------------------------------------------------- Money Flow Index
def mfi(df, n=MFI_N):
    """MFI(n) in 0..100 (NaN = no read: too few bars, or fewer than half of the last n+1 bars carry volume)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    v = df["volume"].astype(float)
    mf = tp * v.fillna(0.0)
    d = tp.diff()
    pos = mf.where(d > 0, 0.0).rolling(n, min_periods=n).sum()
    neg = mf.where(d < 0, 0.0).rolling(n, min_periods=n).sum()
    out = 100.0 - 100.0 / (1.0 + pos / neg.replace(0.0, np.nan))
    out = out.where(~((neg == 0) & (pos > 0)), 100.0)
    out[d.isna()] = np.nan
    ok = _vol_ok(v.values, n + 1) & ((pos + neg) > 0).values
    return out.where(ok).clip(0.0, 100.0)


# ----------------------------------------------------------------------------------------------- volume profile
def _profiles(tp, v, start, width, min_bars):
    """Volume-at-price for each row i over bars start[i]..i (typical price, bins of width[i] anchored at the window's
    lowest typical price). -> (poc, vah, val) price arrays, NaN = no read. Row arithmetic never depends on the chunk."""
    n = len(tp)
    poc, vah, val = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    pos = (v > 0).astype(np.int64)
    cpos = np.concatenate([[0], np.cumsum(pos)])
    rows = np.arange(n)
    length = rows - start + 1
    okrow = (length >= min_bars) & np.isfinite(width) & (width > 0)
    okrow &= (cpos[rows + 1] - cpos[start]) >= VOL_SHARE * length
    todo = rows[okrow]
    K = VP_KMAX
    for c0 in range(0, len(todo), VP_CHUNK):
        rr = todo[c0:c0 + VP_CHUNK]
        R = len(rr)
        L = length[rr]
        W = int(L.max())
        offs = np.arange(W)
        mask = offs[None, :] < L[:, None]
        idx = np.where(mask, start[rr][:, None] + offs[None, :], rr[:, None])
        T = tp[idx]
        V = np.where(mask, v[idx], 0.0)
        lo = np.where(mask, T, np.inf).min(axis=1)
        hi = np.where(mask, T, -np.inf).max(axis=1)
        w = np.maximum(width[rr], (hi - lo) / (K - 1))
        nb = np.floor((hi - lo) / w).astype(np.int64) + 1
        k = np.clip(np.floor((T - lo[:, None]) / w[:, None]).astype(np.int64), 0, K - 1)
        flat = (np.arange(R)[:, None] * K + k)[mask]
        hist = np.bincount(flat, weights=V[mask], minlength=R * K).reshape(R, K)
        total = hist.sum(axis=1)
        good = total > 0
        p = hist.argmax(axis=1)
        a = np.arange(R)
        lo_k, hi_k = p.copy(), p.copy()
        acc = hist[a, p].copy()
        target = VP_VALUE * total
        for _ in range(K):
            act = (acc < target) & good
            if not act.any():
                break
            up_ok = hi_k + 1 < nb
            dn_ok = lo_k > 0
            above = np.where(up_ok, hist[a, np.minimum(hi_k + 1, K - 1)], -1.0)
            below = np.where(dn_ok, hist[a, np.maximum(lo_k - 1, 0)], -1.0)
            go_up = act & (above >= below) & up_ok
            go_dn = act & ~go_up & dn_ok
            hi_k = np.where(go_up, hi_k + 1, hi_k)
            lo_k = np.where(go_dn, lo_k - 1, lo_k)
            acc = acc + np.where(go_up, np.maximum(above, 0.0), 0.0) + np.where(go_dn, np.maximum(below, 0.0), 0.0)
            if not (go_up | go_dn).any():
                break
        poc[rr] = np.where(good, lo + (p + 0.5) * w, np.nan)
        val[rr] = np.where(good, lo + lo_k * w, np.nan)
        vah[rr] = np.where(good, lo + (hi_k + 1) * w, np.nan)
    return poc, vah, val


def _vprofile_frame(b):
    """-> frame on b's index with the day-so-far and 7-day profile readings."""
    idx = b.index
    out = pd.DataFrame(index=idx)
    d1 = _resample(b, "1D")
    atr_d = _on15(b, "1D", pd.DataFrame({"atr": _ind.atr_wilder(d1, ATR_N)}, index=d1.index))["atr"].values
    h, l, c = b["high"].values, b["low"].values, b["close"].values
    tp = (h + l + c) / 3.0
    v = np.nan_to_num(b["volume"].values.astype(float), nan=0.0)
    i8 = _data.to_ms(idx)                                               # one unit for all (pandas may mix ms / us)
    day_start = np.searchsorted(i8, _data.to_ms(idx.normalize()), side="left")
    wk_start = np.searchsorted(i8, i8 - 7 * 86400000, side="right")
    for tag, start, need in (("day", day_start, VP_MIN_DAY), ("7d", wk_start, VP_MIN_7D)):
        poc, vah, val = _profiles(tp, v, start, VP_BIN_ATR * atr_d, need)
        dist = (c - poc) / np.where(atr_d > 0, atr_d, np.nan)
        span = np.where(vah > val, vah - val, np.nan)
        inside = (c - val) / span - 0.5
        pos = np.where(c > vah, 1.0, np.where(c < val, -1.0, inside))
        pos = np.where(np.isfinite(poc), pos, np.nan)
        out["vpf_poc_px_" + tag], out["vpf_vah_px_" + tag], out["vpf_val_px_" + tag] = poc, vah, val
        out["vpf_poc_atr_" + tag] = dist
        out["vpf_pos_" + tag] = np.clip(pos, -1.0, 1.0)
        out["vpf_poc_" + tag] = np.clip(dist / 2.0, -1.0, 1.0)
    return out


# ----------------------------------------------------------------------------------------------- Heikin-Ashi
def heikin_ashi(df):
    """-> frame: HA open/high/low/close, colour (+1 green, -1 red; ha_close == ha_open counts red), run length of the
    current colour, strong (+1 green with no lower wick, -1 red with no upper wick, 0 otherwise)."""
    o, h, l, c = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    hc = (o + h + l + c) / 4.0
    hcl = hc.tolist()
    ho = [0.0] * len(hc)
    if len(hc):
        ho[0] = (o[0] + c[0]) / 2.0
        for i in range(1, len(hc)):
            ho[i] = (ho[i - 1] + hcl[i - 1]) / 2.0
    ho = np.array(ho)
    hh, hl = np.maximum(h, np.maximum(ho, hc)), np.minimum(l, np.minimum(ho, hc))
    col = np.where(hc > ho, 1.0, -1.0)
    chg = np.concatenate([[True], col[1:] != col[:-1]]) if len(col) else np.zeros(0, bool)
    grp_start = np.maximum.accumulate(np.where(chg, np.arange(len(col)), 0)) if len(col) else np.zeros(0, int)
    run = (np.arange(len(col)) - grp_start + 1).astype(float)
    strong = np.where((col > 0) & (hl >= ho), 1.0, np.where((col < 0) & (hh <= ho), -1.0, 0.0))
    return pd.DataFrame({"ha_open": ho, "ha_high": hh, "ha_low": hl, "ha_close": hc, "col": col, "run": run,
                         "strong": strong}, index=df.index)


# ----------------------------------------------------------------------------------------------- Aroon, Vortex
def aroon(df, n=AROON_N):
    """Aroon(n) -> (up, down) in 0..100 over the last n+1 bars (ties: the most recent extreme)."""
    h, l = df["high"].values.astype(float), df["low"].values.astype(float)
    up, dn = np.full(len(h), np.nan), np.full(len(h), np.nan)
    if len(h) > n:
        from numpy.lib.stride_tricks import sliding_window_view as swv
        hw, lw = swv(h, n + 1)[:, ::-1], swv(l, n + 1)[:, ::-1]
        up[n:] = 100.0 * (n - hw.argmax(axis=1)) / n
        dn[n:] = 100.0 * (n - lw.argmin(axis=1)) / n
    return up, dn


def vortex(df, n=VORTEX_N):
    """Vortex(n) -> (VI+, VI-)."""
    h, l = df["high"].astype(float), df["low"].astype(float)
    vp = (h - l.shift(1)).abs().rolling(n, min_periods=n).sum()
    vm = (l - h.shift(1)).abs().rolling(n, min_periods=n).sum()
    tr = _ind.true_range(df).where(df["close"].shift(1).notna()).rolling(n, min_periods=n).sum()
    tr = tr.replace(0.0, np.nan)
    return (vp / tr).values, (vm / tr).values


# ----------------------------------------------------------------------------------------------- features
def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    out = pd.DataFrame(index=index15)
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
        agree = np.zeros(len(b))
        for tag, rule in TFS4:                                          # Parabolic SAR and MFI, 15m to daily
            hb = frames[tag]
            try:
                on = _on15(b, rule, _psar_frame(hb))
                agree += on["dir"].fillna(0.0).values
                put(pd.DataFrame({"psar_" + tag: on["dir"], "psar_lvl_" + tag: on["lvl"],
                                  "psar_dist_" + tag: on["dist"], "psar_since_" + tag: on["since"]}, index=b.index))
            except Exception as ex:
                errors["psar_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
            try:
                on = _on15(b, rule, pd.DataFrame({"m": mfi(hb)}, index=hb.index))
                put(pd.DataFrame({"mfi_raw_" + tag: on["m"], "mfi_" + tag: (on["m"] - 50.0) / 50.0}, index=b.index))
            except Exception as ex:
                errors["mfi_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        put(pd.DataFrame({"psar_agree": agree / 4.0}, index=b.index))
        try:
            put(_vprofile_frame(b))
        except Exception as ex:
            errors["vprofile"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        for tag, rule in TFS_HA:                                        # Heikin-Ashi, 15m to 4h
            try:
                ha = heikin_ashi(frames[tag])
                on = _on15(b, rule, ha[["col", "run", "strong"]])
                put(pd.DataFrame({"ha_col_" + tag: on["col"], "ha_runlen_" + tag: on["run"],
                                  "ha_run_" + tag: on["col"] * np.minimum(on["run"], HA_RUN_CAP) / HA_RUN_CAP,
                                  "ha_strong_" + tag: on["strong"]}, index=b.index))
            except Exception as ex:
                errors["ha_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        for tag, rule in TFS_AR:                                        # Aroon and Vortex, 1h to daily
            try:
                hb = frames[tag]
                up, dn = aroon(hb)
                vp, vm = vortex(hb)
                on = _on15(b, rules[tag], pd.DataFrame({"up": up, "dn": dn, "vp": vp, "vm": vm}, index=hb.index))
                put(pd.DataFrame({"aro_up_raw_" + tag: on["up"], "aro_dn_raw_" + tag: on["dn"],
                                  "aro_up_" + tag: (on["up"] - 50.0) / 50.0, "aro_dn_" + tag: (on["dn"] - 50.0) / 50.0,
                                  "aro_osc_" + tag: (on["up"] - on["dn"]) / 100.0,
                                  "vtx_plus_" + tag: on["vp"], "vtx_minus_" + tag: on["vm"],
                                  "vtx_" + tag: (on["vp"] - on["vm"]) / VTX_SCALE}, index=b.index))
            except Exception as ex:
                errors["aroon_" + tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
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


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what is read; forecasts nothing."""
    say = OrderedDict()
    bits, ups, downs = [], 0, 0
    for tag, _ in TFS4:
        dr, lvl = _num(row, "psar_" + tag), _num(row, "psar_lvl_" + tag)
        if not dr or lvl is None:
            bits.append("%s no read" % tag)
            continue
        ups, downs = ups + (dr > 0), downs + (dr < 0)
        dist, since = _num(row, "psar_dist_" + tag), _num(row, "psar_since_" + tag)
        extra = "" if dist is None else (", %.1f ATR %s price" % (abs(dist), "below" if dist >= 0 else "above"))
        extra += "" if since is None else (", flipped %d bar%s ago" % (since, "" if since == 1 else "s"))
        bits.append("%s %s (SAR %.5g%s)" % (tag, "UP" if dr > 0 else "DOWN", lvl, extra))
    say[GROUPS["psar"][0]] = "Parabolic SAR %d up / %d down: %s." % (ups, downs, "; ".join(bits))

    bits = []
    for tag, _ in TFS4:
        m = _num(row, "mfi_raw_" + tag)
        if m is None:
            bits.append("%s no read" % tag)
            continue
        zone = " overbought" if m >= OB else (" oversold" if m <= OS else "")
        bits.append("%s %.0f%s" % (tag, m, zone))
    if all(_num(row, "mfi_raw_" + t) is None for t, _ in TFS4):
        say[GROUPS["mfi"][0]] = "Money Flow Index (14): %s." % _no_volume_note(asset)
    else:
        say[GROUPS["mfi"][0]] = "Money Flow Index (14): %s." % "; ".join(bits)

    bits = []
    for tag, name in (("day", "today so far"), ("7d", "last 7 days")):
        poc, vah, val = (_num(row, "vpf_%s_px_%s" % (k, tag)) for k in ("poc", "vah", "val"))
        if poc is None or vah is None or val is None:
            bits.append("%s no read" % name)
            continue
        p = _num(row, "vpf_pos_" + tag)
        where = ("above the value area" if p is not None and p >= 1.0 else
                 "below the value area" if p is not None and p <= -1.0 else "inside the value area")
        d = _num(row, "vpf_poc_atr_" + tag)
        dtxt = "" if d is None else (", %.1f daily ATR %s the POC" % (abs(d), "above" if d >= 0 else "below"))
        bits.append("%s POC %.5g, value area %.5g-%.5g, price %s%s" % (name, poc, val, vah, where, dtxt))
    if all(_num(row, "vpf_poc_px_" + t) is None for t in ("day", "7d")):
        say[GROUPS["vprofile"][0]] = "Volume profile: %s." % _no_volume_note(asset)
    else:
        say[GROUPS["vprofile"][0]] = "Volume profile: %s." % "; ".join(bits)

    bits = []
    for tag, _ in TFS_HA:
        col, run = _num(row, "ha_col_" + tag), _num(row, "ha_runlen_" + tag)
        if not col or run is None:
            bits.append("%s no read" % tag)
            continue
        st = _num(row, "ha_strong_" + tag)
        strong = (", strong (no lower wick)" if st and st > 0 else ", strong (no upper wick)" if st and st < 0 else "")
        bits.append("%s %s for %d bar%s%s" % (tag, "green" if col > 0 else "red", run, "" if run == 1 else "s", strong))
    say[GROUPS["heikin"][0]] = "Heikin-Ashi candles: %s." % "; ".join(bits)

    bits = []
    for tag, _ in TFS_AR:
        up, dn = _num(row, "aro_up_raw_" + tag), _num(row, "aro_dn_raw_" + tag)
        vp, vm = _num(row, "vtx_plus_" + tag), _num(row, "vtx_minus_" + tag)
        parts = []
        if up is not None and dn is not None:
            parts.append("Aroon up %.0f / down %.0f" % (up, dn))
        if vp is not None and vm is not None:
            parts.append("VI+ %.2f vs VI- %.2f" % (vp, vm))
        bits.append("%s %s" % (tag, ", ".join(parts) if parts else "no read"))
    say[GROUPS["aroon"][0]] = "Aroon (25) and Vortex (14): %s." % "; ".join(bits)
    return say
