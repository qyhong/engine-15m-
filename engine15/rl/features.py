# -*- coding: utf-8 -*-
"""features -- point-in-time features on 15m perpetual bars.

THE RULE: the feature row for bar t (keyed by its open time) uses only what was known at
bar t's CLOSE. Concretely:
  * price/volume features are trailing windows ending at bar t (rolling, shift >= 0 only);
  * a funding rate counts from its settlement time (data.settlement_ms) on: bar t sees the
    last settlement at or before its close;
  * time-to-next-funding is projected from PAST settlements only (last one + last interval);
  * the higher-timeframe feature (last closed UTC day) goes through engine15.data.htf_on_15,
    the engine's no-look-ahead join.
Windows count bars, not clock time; the few exchange gaps make a window span a little more time.
tests/rl/test_lookahead.py checks that truncating the data at t never changes the rows up to t.
"""
import numpy as np
import pandas as pd

from . import store

INTERVAL_MS = 900000


def _funding_cols(index, funding, interval_ms=INTERVAL_MS):
    """-> (rate, change, hours_to_next) arrays on the bar index, point-in-time."""
    n = len(index)
    rate = np.full(n, np.nan)
    chg = np.full(n, np.nan)
    to_next = np.full(n, np.nan)
    if funding is None or not len(funding):
        return rate, chg, to_next
    f = pd.DataFrame({"settle": np.asarray(funding["settle_ms"], dtype="int64"),
                      "rate": np.asarray(funding["rate"], dtype=float)})
    f = f.drop_duplicates("settle", keep="last").sort_values("settle")
    s, r = f["settle"].values, f["rate"].values
    close_ms = store.to_ms(index) + interval_ms
    k = np.searchsorted(s, close_ms, side="right") - 1          # last settlement at or before the bar's close
    ok = k >= 0
    rate[ok] = r[k[ok]]
    ok2 = k >= 1
    chg[ok2] = r[k[ok2]] - r[k[ok2] - 1]
    nxt = s[k[ok2]] + (s[k[ok2]] - s[k[ok2] - 1])               # projected from the last interval seen
    to_next[ok2] = np.maximum(nxt - close_ms[ok2], 0) / 3600000.0
    return rate, chg, to_next


def _daily_closed(bars):
    """Last CLOSED UTC day's log return on the 15m index (engine15.data.htf_on_15)."""
    from .. import data as edata
    b = bars[["open", "high", "low", "close", "volume"]].copy()
    b["taker_buy"] = bars["taker_buy"] if "taker_buy" in bars else 0.0
    d = edata.resample(b, "1D")
    vals = np.log(d["close"] / d["open"])
    return edata.htf_on_15(b, "1D", vals).values


def build(bars, funding=None, fcfg=None, interval_ms=INTERVAL_MS):
    """bars (open/high/low/close/volume[, taker_buy]) + funding (rate, settle_ms) -> feature frame."""
    fcfg = fcfg or {"return_windows": [1, 4, 16, 96], "vol_windows": [16, 96, 672],
                    "momentum_windows": [16, 96, 672], "volume_z_window": 672, "daily_closed": True}
    close = bars["close"].astype(float)
    lc = np.log(close)
    lr = lc.diff()
    out = {}
    for k in fcfg["return_windows"]:
        out["ret_%d" % k] = lc - lc.shift(k)
    for w in fcfg["vol_windows"]:
        out["rv_%d" % w] = lr.rolling(w, min_periods=w).std()
    for w in fcfg["momentum_windows"]:
        sd = lr.rolling(w, min_periods=w).std()
        out["mom_%d" % w] = (lc - lc.shift(w)) / (sd * np.sqrt(w))
    rate, chg, to_next = _funding_cols(bars.index, funding, interval_ms)
    out["funding_rate"] = rate
    out["funding_change"] = chg
    out["hours_to_funding"] = to_next
    lv = np.log1p(bars["volume"].astype(float))
    w = fcfg["volume_z_window"]
    out["volume_z"] = (lv - lv.rolling(w, min_periods=w).mean()) / lv.rolling(w, min_periods=w).std()
    if fcfg.get("daily_closed"):
        out["ret_1d_closed"] = _daily_closed(bars)
    df = pd.DataFrame(out, index=bars.index)
    return df.replace([np.inf, -np.inf], np.nan)


def lookahead_report(builder, bars, funding, cuts, atol=1e-12, rtol=1e-9):
    """Recompute features on data truncated at each cut; -> {cut: [columns whose rows <= cut changed]}.
    An empty list everywhere means the builder is point-in-time on these cuts."""
    full = builder(bars, funding)
    out = {}
    for cut in cuts:
        part_bars = bars.iloc[:cut]
        t_close = int(store.to_ms(part_bars.index[-1:])[0]) + INTERVAL_MS
        part_f = funding[np.asarray(funding["settle_ms"]) <= t_close] if funding is not None and len(funding) else funding
        part = builder(part_bars, part_f)
        a, b = full.iloc[:cut], part
        bad = []
        for c in full.columns:
            x, y = a[c].values.astype(float), b[c].values.astype(float)
            same = np.isclose(x, y, atol=atol, rtol=rtol) | (np.isnan(x) & np.isnan(y))
            if not same.all():
                bad.append(c)
        out[cut] = bad
    return out
