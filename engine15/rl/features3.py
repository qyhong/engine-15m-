# -*- coding: utf-8 -*-
"""features3 -- Phase 3 observations on 15m bars: Phase 2's point-in-time features plus higher-timeframe
context, the frozen momentum signal, a volatility regime and time of day / week.

Same rule as features.py: the row for bar t (keyed by its open time) uses only what is known at bar t's
CLOSE. Higher-timeframe values are computed on resampled bars and joined with engine15.data.htf_on_15,
the engine's no-look-ahead join (a 15m row sees only higher bars that had closed by its own close).
tests/rl/test_phase3_features.py runs the truncation check (features.lookahead_report) on every column.

Added columns (on top of features.build with the Phase 2 windows):
  trend_1h, trend_4h, trend_1d   log return over the last N CLOSED higher bars (1h: 24 = one day,
                                 4h: 42 = one week, 1d: 30 = one month)
  px_sma_1h, px_sma_4h, px_sma_1d   log(15m close / mean of the last N closed higher-bar closes)
  mom_signal                     the frozen daily momentum benchmark's target at this bar (+1 / -1 / 0)
  vol_regime                     log(rv_96 / rv_2880): today's vol against the last 30 days
  rv_1d_30                       std of the last 30 closed daily log returns
  tod_sin, tod_cos, dow_sin, dow_cos   time of day / day of week of the bar's CLOSE (known in advance)
Funding (rate, change, hours to the next settlement) is already in the Phase 1 set; free data only.
"""
import numpy as np
import pandas as pd

from . import benchmarks, features, store

INTERVAL_MS = 900000
HTF = (("1h", 24), ("4h", 42), ("1D", 30))
NAMES = {"1h": "1h", "4h": "4h", "1D": "1d"}


def _htf_frame(bars):
    b = bars[["open", "high", "low", "close", "volume"]].copy()
    b["taker_buy"] = bars["taker_buy"] if "taker_buy" in bars else 0.0
    return b


def htf_context(bars, htf=HTF):
    """-> dict of arrays on the 15m index (closed higher bars only)."""
    from .. import data as edata
    b = _htf_frame(bars)
    lc15 = np.log(bars["close"].astype(float)).values
    out = {}
    for rule, n in htf:
        h = edata.resample(b, rule)
        lc = np.log(h["close"].astype(float))
        trend = lc - lc.shift(n)
        sma = h["close"].astype(float).rolling(n, min_periods=n).mean()
        nm = NAMES[rule]
        out["trend_" + nm] = edata.htf_on_15(b, rule, trend).values
        out["px_sma_" + nm] = lc15 - np.log(edata.htf_on_15(b, rule, sma).values)
        if rule == "1D":
            dr = lc.diff()
            out["rv_1d_30"] = edata.htf_on_15(b, rule, dr.rolling(30, min_periods=30).std()).values
    return out


def time_features(index, interval_ms=INTERVAL_MS):
    close_ms = store.to_ms(index) + interval_ms
    day = (close_ms % 86400000) / 86400000.0
    week = ((close_ms // 86400000 + 3) % 7 + day) / 7.0           # 1970-01-01 was a Thursday -> Monday = 0
    return {"tod_sin": np.sin(2 * np.pi * day), "tod_cos": np.cos(2 * np.pi * day),
            "dow_sin": np.sin(2 * np.pi * week), "dow_cos": np.cos(2 * np.pi * week)}


def build(bars, funding=None, fcfg=None, interval_ms=INTERVAL_MS):
    """Phase 2 features (fcfg) + the Phase 3 context columns. -> DataFrame (NaN where not yet defined)."""
    fcfg = dict(fcfg or {"return_windows": [1, 4, 16, 96, 672, 2880], "vol_windows": [16, 96, 672],
                         "momentum_windows": [16, 96, 672, 2880], "volume_z_window": 672, "daily_closed": True})
    extra = fcfg.pop("phase3", {}) if "phase3" in fcfg else {}
    df = features.build(bars, funding, fcfg, interval_ms)
    lr = np.log(bars["close"].astype(float)).diff()
    rv_long = lr.rolling(2880, min_periods=2880).std()
    rv96 = df["rv_96"] if "rv_96" in df else lr.rolling(96, min_periods=96).std()
    add = {}
    if extra.get("htf", True):
        add.update(htf_context(bars))
    if extra.get("momentum_signal", True):
        add["mom_signal"] = benchmarks.momentum(bars["close"], 30, True, interval_ms).values
    add["vol_regime"] = np.log(rv96 / rv_long).values
    if extra.get("time", True):
        add.update(time_features(bars.index, interval_ms))
    for k, v in add.items():
        df[k] = np.asarray(v, dtype=float)
    return df.replace([np.inf, -np.inf], np.nan)
