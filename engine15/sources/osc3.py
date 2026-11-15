# -*- coding: utf-8 -*-
"""osc3 -- the Commodity Channel Index card, on 15m, 1h, 4h and daily bars of the asset itself.

Owner, 15 Nov 2026: "For commodities like metal. Should include CCI technical indicator also" -> its own card for every
market (CCI was built for commodities but reads any price series), reading-only to start (think15-v5.2.1).

  cci   CCI (15m to daily)   CCI(20) = (typical price - its 20-bar average) / (0.015 x the 20-bar mean absolute
                             deviation), typical price = (high + low + close) / 3. Feature = CCI / 200 clipped to -1..+1;
                             readings above +100 / below -100 are the usual overbought / oversold lines; plus whether it
                             crossed +100 or -100 on the last bar of that timeframe.

THE ONE RULE (tests/test_sources_osc3.py): row i uses only what was known at the close of 15m bar i; a higher timeframe
reaches a 15m row only once its bar has closed (data.htf_on_15). Nothing is fetched. It does not vote until the owner's
card rating promotes it; no reading is claimed to predict.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data

TFS = (("15m", None), ("1h", "1h"), ("4h", "4h"), ("1d", "1D"))
N, K = 20, 0.015
LINE = 100.0

GROUPS = OrderedDict([("cci", ("CCI (15m to daily)", ["cci_15m", "cci_1h", "cci_4h", "cci_1d"]))])
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = ["cci_raw_%s" % t for t, _ in TFS] + ["cci_cross_%s" % t for t, _ in TFS]


def update(log=print):
    """Nothing to fetch: computed from the asset's own bars."""
    return {}


def _ohlc_resample(b, rule):
    agg = b.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def cci(df, n=N, k=K):
    """CCI(n) on a bar frame -> Series (NaN until n bars exist; 0 when the window is flat)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    ma = tp.rolling(n, min_periods=n).mean()
    md = tp.rolling(n, min_periods=n).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
    out = (tp - ma) / (k * md)
    return out.where(md > 0, 0.0).where(ma.notna())


def _cross(x):
    """+1 = crossed up through +100 or -100 on this bar, -1 = crossed down through either, 0 = neither."""
    prev = x.shift(1)
    up = ((prev <= LINE) & (x > LINE)) | ((prev <= -LINE) & (x > -LINE))
    dn = ((prev >= LINE) & (x < LINE)) | ((prev >= -LINE) & (x < -LINE))
    return up.astype(float) - dn.astype(float)


def features(index15, asset, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    out = pd.DataFrame(index=index15)
    errors = {}
    for f in FEATURES + RAW:
        out[f] = np.nan
    try:
        b = _data.load(asset) if bars is None else bars
        b = b[["open", "high", "low", "close"]].astype(float)
        if not b.index.is_monotonic_increasing or b.index.has_duplicates:
            b = b[~b.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        b, errors["bars"] = None, "%s: %s" % (type(ex).__name__, str(ex)[:160])
    if b is not None and len(b):
        for tag, rule in TFS:
            try:
                hb = b if rule is None else _ohlc_resample(b, rule)
                c = cci(hb)
                frame = pd.DataFrame({"v": c, "x": _cross(c).where(c.notna())}, index=hb.index)
                on15 = frame if rule is None else _data.htf_on_15(b, rule, frame)
                on15 = on15.reindex(b.index).reindex(index15)
                out["cci_raw_" + tag] = on15["v"].values
                out["cci_cross_" + tag] = on15["x"].values
                out["cci_" + tag] = (on15["v"] / 200.0).values
            except Exception as ex:
                errors[tag] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
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
    bits = []
    for tag, _ in TFS:
        v = _num(row, "cci_raw_" + tag)
        if v is None:
            bits.append("%s no read" % tag)
            continue
        zone = " overbought (above +100)" if v > LINE else (" oversold (below -100)" if v < -LINE else "")
        x = _num(row, "cci_cross_" + tag)
        cr = "" if not x else (", just crossed up" if x > 0 else ", just crossed down")
        bits.append("%s %+.0f%s%s" % (tag, v, zone, cr))
    return OrderedDict([(GROUPS["cci"][0], "CCI (20): %s." % "; ".join(bits))])
