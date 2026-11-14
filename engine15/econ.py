# -*- coding: utf-8 -*-
"""econ -- economic indicators: the calendar of scheduled US releases and the macro tape.

Two sources, both free and public, both kept on disk so the engine has the data points:

  calendar    the weekly feed the estate's own economic-calendar job reads
              (nfs.faireconomy.media, ForexFactory's week file): every USD High-impact
              release with its forecast and previous print -> data/econ_events.csv, which
              only ever grows. Seeded once from the CPI / NFP / FOMC times embedded in the
              estate's src/strategy/event_calendar.py (May 2026 onward). Before that there
              is no calendar read.
  macro tape  daily closes of the S&P 500, the dollar index, the VIX and the US 10-year
              yield from Yahoo's chart API (2018 onward) -> data/macro_<name>.csv.

Readings (features), all known at the 15m close they sit on:
  ec_next      1 at a release, fading to 0 a day before it     (something is about to print)
  ec_prev      1 at a release, fading to 0 twelve hours after  (something just printed)
  mac_spx_5d   the S&P's 5-day move, in units of its own volatility
  mac_dxy_5d   the dollar's 5-day move, likewise
  mac_vix      the VIX against 20
  mac_y10_5d   the 10-year yield's 5-day change, in quarter points
A daily close is used from 00:00 UTC of the NEXT day (the US session ends 21:00 UTC).
"""
import os
import re
import time

import numpy as np
import pandas as pd

from .config import DATA_DIR, ESTATE

YAHOO = {"spx": "%5EGSPC", "dxy": "DX-Y.NYB", "vix": "%5EVIX", "y10": "%5ETNX"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CAL_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
EVENTS_CSV = os.path.join(DATA_DIR, "econ_events.csv")
FEATURES = ["ec_next", "ec_prev", "mac_spx_5d", "mac_dxy_5d", "mac_vix", "mac_y10_5d"]
RAW = ["raw_spx", "raw_dxy", "raw_vix", "raw_y10"]              # the levels themselves, for reading


def _macro_path(name):
    return os.path.join(DATA_DIR, "macro_%s.csv" % name)


def update_macro():
    import requests
    out = {}
    os.makedirs(DATA_DIR, exist_ok=True)
    for name, sym in YAHOO.items():
        try:
            r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%s" % sym, headers=UA, timeout=25,
                             params={"interval": "1d", "period1": 1514764800, "period2": int(time.time())})
            res = r.json()["chart"]["result"][0]
            d = pd.DataFrame({"ts": res["timestamp"], "close": res["indicators"]["quote"][0]["close"]}).dropna()
            d["date"] = pd.to_datetime(d["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
            d = d.drop_duplicates("date", keep="last")[["date", "close"]]
            today = time.strftime("%Y-%m-%d", time.gmtime())
            d = d[d["date"] < today]                                 # today's bar is still forming
            d.to_csv(_macro_path(name), index=False)
            out[name] = len(d)
        except Exception as e:                                       # a failed source keeps its old file
            out[name] = "failed: %s" % str(e)[:80]
    return out


def load_macro():
    cols = {}
    for name in YAHOO:
        if os.path.exists(_macro_path(name)):
            d = pd.read_csv(_macro_path(name))
            cols[name] = pd.Series(d["close"].values, index=pd.to_datetime(d["date"], utc=True))
    return pd.DataFrame(cols).sort_index()


def _seed_events():
    """The CPI / NFP / FOMC times embedded in the estate's event_calendar.py, read as text."""
    path = os.path.join(ESTATE, "src", "strategy", "event_calendar.py")
    rows = []
    if os.path.exists(path):
        pat = re.compile(r"\(datetime\((\d+), (\d+), (\d+), (\d+), (\d+), tzinfo=timezone\.utc\), \"([^\"]+)\"\)")
        with open(path, encoding="utf-8") as fh:
            for y, m, d, hh, mm, title in pat.findall(fh.read()):
                ts = pd.Timestamp(int(y), int(m), int(d), int(hh), int(mm), tz="UTC")
                rows.append((int(ts.timestamp() * 1000), title, "USD", "High", "", ""))
    return rows


def _load_live():
    """The live calendar file alone (econ_events.csv): what update_calendar() extends."""
    if not os.path.exists(EVENTS_CSV):
        return pd.DataFrame(columns=["ts_ms", "title", "country", "impact", "forecast", "previous"])
    return pd.read_csv(EVENTS_CSV, dtype={"forecast": str, "previous": str}).fillna("")


def load_events():
    """The live calendar joined with the US High-impact history 2019 onward (calhistory.py,
    data/sources/calendar_history.csv); one row per time and title, the live row wins. The
    history's oil rows are never included (calhistory.oil_events())."""
    live = _load_live()
    try:
        from . import calhistory
        return calhistory.merge(live, calhistory.us_events())
    except Exception:                                                # no or unreadable history: the live file as before
        return live


def update_calendar():
    import requests
    rows = [tuple(r) for r in _load_live().itertuples(index=False)] or _seed_events()
    note = "kept"
    try:
        feed = requests.get(CAL_URL, headers=UA, timeout=25).json()
        for e in feed:
            if e.get("country") == "USD" and e.get("impact") == "High":
                ts = int(pd.Timestamp(e["date"]).tz_convert("UTC").timestamp() * 1000)
                rows.append((ts, e.get("title", ""), "USD", "High", e.get("forecast") or "", e.get("previous") or ""))
        note = "feed read"
    except Exception as e:
        note = "feed failed: %s" % str(e)[:80]
    d = pd.DataFrame(rows, columns=["ts_ms", "title", "country", "impact", "forecast", "previous"])
    d = d.drop_duplicates(["ts_ms", "title"], keep="last").sort_values("ts_ms")
    os.makedirs(DATA_DIR, exist_ok=True)
    d.to_csv(EVENTS_CSV, index=False)
    return len(d), note


def next_event(at):
    """-> the next USD High-impact release at or after `at` (a UTC Timestamp), or None."""
    ev = load_events()
    ms = int(at.timestamp() * 1000)
    ev = ev[ev.ts_ms >= ms]
    if not len(ev):
        return None
    first = ev[ev.ts_ms == ev.ts_ms.iloc[0]]
    return {"time_utc": str(pd.Timestamp(int(first.ts_ms.iloc[0]), unit="ms", tz="UTC"))[:16],
            "hours_away": round((int(first.ts_ms.iloc[0]) - ms) / 3600000.0, 1),
            "titles": list(first.title)[:4], "forecast": list(first.forecast)[:4], "previous": list(first.previous)[:4]}


def features(index15, bar_ms=900000):
    """-> frame of FEATURES on the 15m index (0.0 = no read)."""
    out = pd.DataFrame(0.0, index=index15, columns=FEATURES)
    for col in RAW:
        out[col] = np.nan
    close_ms = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + bar_ms
    ev = np.sort(load_events().ts_ms.unique().astype("int64")) if os.path.exists(EVENTS_CSV) else np.array([], dtype="int64")
    if len(ev):
        k = np.searchsorted(ev, close_ms, side="left")              # the first release at or after the close
        ahead = np.where(k < len(ev), ev[np.minimum(k, len(ev) - 1)] - close_ms, np.inf) / 3600000.0
        since = np.where(k > 0, close_ms - ev[np.maximum(k - 1, 0)], np.inf) / 3600000.0
        out["ec_next"] = np.clip(1.0 - ahead / 24.0, 0.0, 1.0)
        out["ec_prev"] = np.clip(1.0 - since / 12.0, 0.0, 1.0)
    mac = load_macro()
    if len(mac):
        f = pd.DataFrame(index=mac.index)
        for name in ("spx", "dxy"):
            if name in mac:
                lr = np.log(mac[name]).diff()
                f["mac_%s_5d" % name] = (np.log(mac[name] / mac[name].shift(5)) / (lr.rolling(60).std() * np.sqrt(5))).clip(-3, 3)
        if "vix" in mac:
            f["mac_vix"] = ((mac["vix"] - 20.0) / 20.0).clip(-1, 2)
        if "y10" in mac:
            f["mac_y10_5d"] = ((mac["y10"] - mac["y10"].shift(5)) / 0.25).clip(-2, 2)
        for name in mac.columns:
            f["raw_" + name] = mac[name]
        f = f.ffill()
        f.index = f.index + pd.Timedelta(days=1)                    # a daily close is used from the next UTC day
        j = f.reindex(index15 + pd.Timedelta(milliseconds=bar_ms), method="ffill")
        for col in f.columns:
            out[col] = j[col].values if col in RAW else j[col].fillna(0.0).values
    return out
