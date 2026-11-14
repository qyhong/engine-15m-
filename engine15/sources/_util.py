# -*- coding: utf-8 -*-
"""_util -- small shared pieces for the cot, japan and equity_events source modules.

Not a source module itself (it is not listed in MODULES and has no GROUPS). Everything here is
plain file and clock handling: the as-of join, atomic CSV writes, a polite GET, a tiny JSON
state file, and New York wall-clock times.
"""
import json
import os
import time

import numpy as np
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, text/csv, */*", "Accept-Language": "en-US,en;q=0.9"}
TIMEOUT_S = 30
NY = "America/New_York"
H_MS, D_MS, BAR_MS = 3600000, 86400000, 900000

_last = {}                                                   # host -> time of the last request


def now_ms():
    return int(time.time() * 1000)


def get(url, params=None, pause=1.0, timeout=TIMEOUT_S):
    """One polite GET (a pause per host between requests, a browser User-Agent, no keys) -> Response.
    Raises on a network error or a status other than 200."""
    import requests
    host = url.split("/")[2]
    wait = pause - (time.time() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
    finally:
        _last[host] = time.time()
    if r.status_code != 200:
        raise RuntimeError("HTTP %d from %s: %s" % (r.status_code, host, r.text[:80].replace("\n", " ")))
    return r


def write_csv(frame, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    for attempt in range(5):                                 # Windows: a reader may hold the file for a moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.3 * (attempt + 1))


def read_csv(path, cols, dtype=None):
    """A source file -> frame with at least `cols` (missing columns are NaN); a missing/empty file -> empty frame."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(dict((c, pd.Series(dtype=object)) for c in cols))
    try:
        d = pd.read_csv(path, dtype=dtype)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(dict((c, pd.Series(dtype=object)) for c in cols))
    for c in cols:
        if c not in d:
            d[c] = np.nan
    return d


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(path, state):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        pass


def ny_ms(day, hour, minute=0):
    """A calendar date ('YYYY-MM-DD', date or Timestamp) at New York wall-clock hour:minute -> epoch ms (DST aware)."""
    t = pd.Timestamp(pd.Timestamp(day).date()) + pd.Timedelta(hours=hour, minutes=minute)
    return int(t.tz_localize(NY).tz_convert("UTC").value // 1000000)


def ny_ms_vec(days, hour, minute=0):
    """Vector form of ny_ms for an array of 'YYYY-MM-DD' strings."""
    t = pd.to_datetime(pd.Series(days, dtype=str)) + pd.Timedelta(hours=hour, minutes=minute)
    return np.array(t.dt.tz_localize(NY).dt.tz_convert("UTC").dt.as_unit("ms").astype("int64"), dtype="int64") \
        if len(t) else np.array([], dtype="int64")


def to_ms_vec(texts):
    """UTC date/time strings -> epoch ms, whatever unit pandas parses them in."""
    t = pd.to_datetime(pd.Series(texts, dtype=str), utc=True)
    return np.array(t.dt.as_unit("ms").astype("int64"), dtype="int64")


def ny_date(ms):
    """epoch ms -> the New York calendar date as 'YYYY-MM-DD'."""
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").tz_convert(NY).strftime("%Y-%m-%d")


def asof(known_ms, values, close_ms, max_age_ms):
    """THE NO-LOOKAHEAD JOIN. values[j] became known at known_ms[j]. -> for each close, the newest
    non-NaN value known at or before it, or NaN when there is none or it is older than max_age_ms."""
    known_ms, values = np.asarray(known_ms, dtype="int64"), np.asarray(values, dtype=float)
    order = np.argsort(known_ms, kind="stable")
    known_ms, values = known_ms[order], values[order]
    keep = np.isfinite(values)
    known_ms, values = known_ms[keep], values[keep]
    close_ms = np.asarray(close_ms, dtype="int64")
    out = np.full(len(close_ms), np.nan)
    if not len(values):
        return out
    k = np.searchsorted(known_ms, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    ok = (k >= 0) & (close_ms - known_ms[kk] <= max_age_ms)
    out[ok] = values[kk[ok]]
    return out


def nyse_trading_days(lo_year, hi_year):
    """-> sorted array of 'YYYY-MM-DD' NYSE trading days (weekdays minus the holiday list in extdata)."""
    from .. import extdata
    shut = set()
    for y in range(int(lo_year), int(hi_year) + 1):
        s, _e = extdata.nyse_days(y)
        shut |= set(d.strftime("%Y-%m-%d") for d in s)
    days = pd.date_range("%d-01-01" % lo_year, "%d-12-31" % hi_year, freq="D")
    days = days[days.dayofweek < 5].strftime("%Y-%m-%d")
    return np.array([d for d in days if d not in shut])


def bars_of(asset, bars):
    """bars: None (load the project's own file), a frame, or {asset: frame} -> the asset's 15m frame or None."""
    if isinstance(bars, dict):
        bars = bars.get(asset)
    if bars is None:
        from .. import data
        try:
            bars = data.load(asset)
        except Exception:
            return None
    return bars


def num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def close_text(row):
    try:
        return (pd.Timestamp(row.name) + pd.Timedelta(milliseconds=BAR_MS)).strftime("%a %d %b %Y %H:%M UTC")
    except Exception:
        return "this close"


def ordinal(x):
    """57.3 -> '57th', 32 -> '32nd', 11 -> '11th'."""
    n = int(round(float(x)))
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suf)
