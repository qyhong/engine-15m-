# -*- coding: utf-8 -*-
"""data -- 15-minute bars: fetch, store, quality gates, closed-bar resampling.

WHY its own store: the estate's 15m files come from binance.us, where up to a quarter of
ETH's 15-minute bars in a year have no trade at all. A 15-minute engine needs a liquid
tape, so this project keeps its own history from Binance spot's public market-data host.

Conventions: a bar is keyed by its OPEN time (UTC). It is CLOSED at open + 15 minutes.
Only closed bars are ever stored or read.
"""
import os
import time

import numpy as np
import pandas as pd

from .config import CFG, DATA_DIR

COLS = ["open", "high", "low", "close", "volume", "taker_buy"]   # taker_buy: base volume bought at the ask (for CVD)
PERIOD = {"15min": 900000, "1h": 3600000, "4h": 14400000, "1D": 86400000}


def to_ms(index):
    """A datetime index -> epoch milliseconds, whatever unit pandas stores it in."""
    return np.asarray(index.as_unit("ms").asi8, dtype="int64")


def path_for(asset):
    return os.path.join(DATA_DIR, "%s_15m.csv" % asset.lower())


def load(asset, path=None):
    """-> DataFrame indexed by open time (UTC), float columns open/high/low/close/volume."""
    df = pd.read_csv(path or path_for(asset))
    df.index = pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)
    df.index.name = "open_time"
    if "taker_buy" not in df.columns:                 # an older file without order-flow: no CVD read
        df["taker_buy"] = np.nan
    return df[COLS].astype(float)


def save(asset, df, path=None):
    out = df[COLS].copy()
    out.insert(0, "ts_ms", to_ms(df.index))
    target = path or path_for(asset)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, target)


def fetch(asset, start_ms, end_ms=None, base_url=None, pause=0.12, log=None):
    """Public klines, closed bars only, from start_ms (inclusive) up to end_ms or now."""
    import requests
    base_url = base_url or CFG["data_base_url"]
    now_ms = int(time.time() * 1000)
    end_ms = min(end_ms or now_ms, now_ms)
    rows, cursor = [], int(start_ms)
    while cursor < end_ms:
        r = requests.get(base_url + "/api/v3/klines", timeout=30,
                         params={"symbol": asset, "interval": "15m", "startTime": cursor, "limit": 1000})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for k in batch:
            if int(k[6]) < now_ms and int(k[0]) < end_ms:          # close time passed: a closed bar
                rows.append((int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9])))
        cursor = int(batch[-1][0]) + CFG["bar_ms"]
        if log and len(rows) % 20000 < 1000:
            log("%s %d bars, at %s" % (asset, len(rows), pd.to_datetime(cursor, unit="ms")))
        if len(batch) < 1000:
            break
        time.sleep(pause)
    df = pd.DataFrame(rows, columns=["ts_ms"] + COLS).drop_duplicates("ts_ms").sort_values("ts_ms")
    df.index = pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)
    df.index.name = "open_time"
    return df


def update(asset, log=None):
    """Create or extend the local history with every bar closed since the last stored one."""
    start = int(pd.Timestamp(CFG["data_start"], tz="UTC").value // 10**6)
    old = load(asset) if os.path.exists(path_for(asset)) else None
    if old is not None and len(old):
        start = int(old.index[-1].value // 10**6) + CFG["bar_ms"]
    new = fetch(asset, start, log=log)
    df = new if old is None else pd.concat([old, new])
    df = df[~df.index.duplicated(keep="last")].sort_index()[COLS].astype(float)
    df.index = pd.DatetimeIndex(df.index, name="open_time")
    save(asset, df)
    return df, len(new)


FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"      # Binance USDT perpetuals, public


def funding_path(asset):
    return os.path.join(DATA_DIR, "%s_funding.csv" % asset.lower())


def load_funding(asset):
    """-> Series of funding rates keyed by the time each was SET (known from then on); empty if no file."""
    if not os.path.exists(funding_path(asset)):
        return pd.Series(dtype=float)
    f = pd.read_csv(funding_path(asset))
    return pd.Series(f["rate"].values.astype(float), index=pd.to_datetime(f["ts_ms"], unit="ms", utc=True)).sort_index()


def update_funding(asset):
    import requests
    old = load_funding(asset)
    cursor = int(old.index[-1].value // 10**6) + 1 if len(old) else int(pd.Timestamp("2019-09-01", tz="UTC").value // 10**6)
    rows = []
    while True:
        r = requests.get(FUNDING_URL, params={"symbol": asset, "startTime": cursor, "limit": 1000}, timeout=30)
        r.raise_for_status()
        batch = r.json()
        rows += [(int(b["fundingTime"]), float(b["fundingRate"])) for b in batch]
        if len(batch) < 1000:
            break
        cursor = int(batch[-1]["fundingTime"]) + 1
        time.sleep(0.3)
    new = pd.DataFrame(rows, columns=["ts_ms", "rate"])
    prior = pd.DataFrame({"ts_ms": to_ms(old.index), "rate": old.values}) if len(old) else new.iloc[:0]
    allf = pd.concat([prior, new]).drop_duplicates("ts_ms")
    os.makedirs(DATA_DIR, exist_ok=True)
    allf.sort_values("ts_ms").to_csv(funding_path(asset), index=False)
    return len(allf), len(new)


def gates(df):
    """The estate's data gates (H1 A.8): monotone, duplicates, gaps, OHLC sanity; plus the
    share of no-trade bars a year, the reason this project left binance.us."""
    idx = df.index
    step = np.diff(to_ms(idx))
    gaps = step[step != CFG["bar_ms"]]
    missing = int(((gaps // CFG["bar_ms"]) - 1).sum()) if len(gaps) else 0
    bad = int(((df.high < df[["open", "close"]].max(axis=1)) | (df.low > df[["open", "close"]].min(axis=1))
               | (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | (df.volume < 0)).sum())
    flat = (df.volume == 0).groupby(idx.year).mean()
    return {
        "rows": int(len(df)), "first": str(idx[0]), "last": str(idx[-1]),
        "monotone": bool(idx.is_monotonic_increasing), "duplicates": int(idx.duplicated().sum()),
        "missing_bars": missing, "gap_events": int(len(gaps)),
        "largest_gap_hours": float(gaps.max() / 3600000.0) if len(gaps) else 0.0,
        "ohlc_violations": bad,
        "no_trade_share_by_year": dict((int(k), round(float(v), 4)) for k, v in flat.items()),
        "pass": bool(idx.is_monotonic_increasing and not idx.duplicated().any() and bad == 0
                     and missing / max(len(df), 1) < 0.005),
    }


def resample(df15, rule):
    """15m bars -> higher-timeframe bars keyed by OPEN time. Used only through htf_on_15,
    which hands a higher bar to a 15m row only once that higher bar has closed."""
    agg = df15.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "taker_buy": "sum"})
    return agg.dropna(subset=["close"])


def htf_on_15(df15, rule, values):
    """THE NO-LOOKAHEAD JOIN. `values` is a frame/series computed on resample(df15, rule),
    keyed by the higher bar's OPEN time. -> the same values on the 15m index, where each
    15m row sees the last higher bar that had CLOSED by the 15m row's own close."""
    period = pd.Timedelta(milliseconds=PERIOD[rule])
    closed_at = values.copy()
    closed_at.index = values.index + period
    my_close = df15.index + pd.Timedelta(milliseconds=CFG["bar_ms"])
    out = closed_at.reindex(my_close, method="ffill")
    out.index = df15.index
    return out
