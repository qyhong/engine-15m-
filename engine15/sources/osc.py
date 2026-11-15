# -*- coding: utf-8 -*-
"""osc -- two oscillator cards the owner asked for by name, on 15m, 1h, 4h and daily bars of the asset itself.

Owner, 15 Nov 2026: "there is a technical indicator called SUPER, have we include stochRSI? include those cards into
the reading also" -> their own cards, reading-only to start (think15-v5.1.2).

  supertrend  Supertrend (15m to daily)   Supertrend(ATR 10, x3) direction on each timeframe (+1 up / -1 down), how
                                          many of the four agree, bars since each last flipped, and the band level
  stochrsi    StochRSI (15m to daily)     StochRSI %K (RSI 14, stochastic 14, smoothed 3) on each timeframe, scaled to
                                          -1..+1 (0 = 50), with overbought (>= 80) / oversold (<= 20) flags

THE ONE RULE (tests/test_sources_osc.py): row i uses only what was known at the close of 15m bar i. A higher
timeframe's value reaches a 15m row only once that higher bar has closed (data.htf_on_15). Nothing is fetched:
update() does nothing. Neither card votes until the owner's card rating promotes it; no reading is claimed to predict.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind
from .ltf import supertrend as _supertrend, ST_N, ST_K

TFS = (("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D"))
OB, OS = 80.0, 20.0

GROUPS = OrderedDict([
    ("supertrend", ("Supertrend (15m to daily)", ["os_st_15m", "os_st_1h", "os_st_4h", "os_st_1d", "os_st_agree"])),
    ("stochrsi", ("StochRSI (15m to daily)", ["os_k_15m", "os_k_1h", "os_k_4h", "os_k_1d"])),
])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = (["os_st_band_%s" % t for t, _ in TFS] + ["os_st_since_%s" % t for t, _ in TFS]
       + ["os_k_raw_%s" % t for t, _ in TFS])


def update(log=print):
    """Nothing to fetch: both cards are computed from the asset's own bars."""
    return {}


def _ohlc_resample(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def _st_frame(df):
    """-> frame on df's index: direction, bars since the last flip, and the active band (the trailing line)."""
    direction, since = _supertrend(df, ST_N, ST_K)
    h, l, c = df["high"].values.astype(float), df["low"].values.astype(float), df["close"].values.astype(float)
    atr = _ind.atr_wilder(df, ST_N).values
    mid = (h + l) / 2.0
    ub, lb = mid + ST_K * atr, mid - ST_K * atr
    band = np.full(len(c), np.nan)                                   # the ratcheted band the direction is measured on
    fu = fl = None
    for i in range(len(c)):
        if ub[i] != ub[i]:
            continue
        if fu is None:
            fu, fl = ub[i], lb[i]
        else:
            fu = ub[i] if (ub[i] < fu or c[i - 1] > fu) else fu
            fl = lb[i] if (lb[i] > fl or c[i - 1] < fl) else fl
        band[i] = fl if direction[i] > 0 else (fu if direction[i] < 0 else np.nan)
    return pd.DataFrame({"dir": direction, "since": since, "band": band}, index=df.index)


def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    out = pd.DataFrame(index=index15)
    errors = {}
    try:
        b = _data.load(asset) if bars is None else bars
        b = b[["open", "high", "low", "close"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    for f in FEATURES + RAW:
        out[f] = np.nan
    if b is not None and len(b):
        agree = np.zeros(len(b))
        for tag, rule in TFS:
            try:
                hb = b if rule is None else _ohlc_resample(b, rule)
                st = _st_frame(hb)
                k = _ind.stoch_rsi_k(hb["close"])
                frame = pd.DataFrame({"dir": st["dir"], "since": st["since"], "band": st["band"], "k": k}, index=hb.index)
                on15 = frame if rule is None else _data.htf_on_15(b, rule, frame)
                on15 = on15.reindex(b.index)
                d = on15["dir"].astype(float)
                agree += d.fillna(0.0).values
                part = pd.DataFrame({"os_st_%s" % tag: d, "os_st_since_%s" % tag: on15["since"],
                                     "os_st_band_%s" % tag: on15["band"], "os_k_raw_%s" % tag: on15["k"],
                                     "os_k_%s" % tag: (on15["k"] - 50.0) / 50.0}, index=b.index)
                part = part.reindex(index15)
                for col in part.columns:
                    out[col] = part[col].values
            except Exception as ex:
                errors[tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        out["os_st_agree"] = pd.Series(agree / 4.0, index=b.index).reindex(index15).values
    out[FEATURES] = out[FEATURES].astype(float).fillna(0.0).clip(-1.0, 1.0)
    out.attrs["errors"] = errors
    return out


def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what is read; forecasts nothing."""
    say = OrderedDict()
    bits, ups, downs = [], 0, 0
    for tag, _ in TFS:
        d, since = _num(row, "os_st_band_" + tag), _num(row, "os_st_since_" + tag)
        dr = _num(row, "os_st_" + tag)
        if d is None or not dr:
            bits.append("%s no read" % tag)
            continue
        ups, downs = ups + (dr > 0), downs + (dr < 0)
        age = "" if since is None else (", flipped %d bar%s ago" % (since, "" if since == 1 else "s"))
        bits.append("%s %s (line %.5g%s)" % (tag, "UP" if dr > 0 else "DOWN", d, age))
    say[GROUPS["supertrend"][0]] = "Supertrend %d up / %d down: %s." % (ups, downs, "; ".join(bits))
    bits = []
    for tag, _ in TFS:
        k = _num(row, "os_k_raw_" + tag)
        if k is None:
            bits.append("%s no read" % tag)
            continue
        zone = " overbought" if k >= OB else (" oversold" if k <= OS else "")
        bits.append("%s %.0f%s" % (tag, k, zone))
    say[GROUPS["stochrsi"][0]] = "StochRSI %%K: %s." % "; ".join(bits)
    return say
