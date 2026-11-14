# -*- coding: utf-8 -*-
"""data -- BTCUSDT perpetual (Binance USD-M) 15m bars, funding history, open interest.

Public market-data endpoints only; no keys, no orders. Every fetch is polite (one request at
a time, a pause between pages), has a timeout, retries with back-off and NEVER raises on a
network blip: it returns what it got and the next run resumes from the last stored bar.

Conventions (same as engine15.data): a bar is keyed by its OPEN time (UTC, ms) and is closed
at open + 15 minutes; only closed bars are stored. Gaps are reported, never filled.

Funding: a rate is keyed by its SETTLEMENT time. Binance stamps settlements a few
milliseconds after the hour (1-47 ms in the history); `settlement_ms` snaps a stamp within
`funding_snap_s` of the 15m grid down to that grid time. The rate is known from that time on.

Open interest: /futures/data/openInterestHist serves only ~30 days, so it is LIVE ONLY:
fetched and stored for the live phase, OFF in every backtest (config data.open_interest).
"""
import os
import time

import numpy as np
import pandas as pd

from . import store
from .config import resolve

BAR_COLS = ["open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy"]
OI_LIVE_ONLY = True


def _say(log, msg):
    if log:
        log(msg)


def _get(url, params, timeout=20, retries=5, log=None):
    """GET -> parsed JSON, or None after `retries` failures. Never raises."""
    import requests
    wait = 1.0
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code in (418, 429):                      # rate limit: back off as told
                pause = float(r.headers.get("Retry-After", 30))
                _say(log, "rate limited (%d), sleeping %.0fs" % (r.status_code, pause))
                time.sleep(min(pause, 120))
                continue
            if r.status_code >= 500:
                raise IOError("server %d" % r.status_code)
            if r.status_code != 200:
                _say(log, "GET %s -> %d %s" % (url, r.status_code, r.text[:200]))
                return None
            return r.json()
        except Exception as e:                                    # network blip: retry, then give up quietly
            _say(log, "GET %s failed (%s), attempt %d/%d" % (url, e, attempt + 1, retries))
            time.sleep(wait)
            wait = min(wait * 2, 30)
    return None


# ---------------------------------------------------------------- paths

def _dir(cfg):
    return resolve(cfg["data"]["dir"])


def bars_path(cfg):
    return store.path(_dir(cfg), "%s_perp_15m" % cfg["data"]["symbol"].lower())


def funding_path(cfg):
    return store.path(_dir(cfg), "%s_perp_funding" % cfg["data"]["symbol"].lower())


def oi_path(cfg):
    return store.path(_dir(cfg), "%s_perp_oi_15m" % cfg["data"]["symbol"].lower())


# ---------------------------------------------------------------- klines

def _frame(rows):
    df = pd.DataFrame(rows, columns=["ts_ms"] + BAR_COLS)
    df = df.drop_duplicates("ts_ms", keep="last").sort_values("ts_ms")
    idx = store.from_ms(df.pop("ts_ms").values)
    df.index = idx
    return df.astype(float)


def fetch_klines(d, start_ms, end_ms=None, log=None, on_pages=None):
    """Closed 15m klines from start_ms. -> (frame, complete). `d` is cfg["data"].
    `on_pages(frame)` is called every d["save_every_pages"] pages so progress can be saved."""
    now_ms = int(time.time() * 1000)
    end_ms = min(end_ms or now_ms, now_ms)
    step = int(d["interval_ms"])
    rows, cursor, pages, complete = [], int(start_ms), 0, True
    while cursor < end_ms:
        batch = _get(d["base_url"] + "/fapi/v1/klines",
                     {"symbol": d["symbol"], "interval": "15m", "startTime": cursor, "limit": int(d["page_limit"])},
                     timeout=d["timeout_s"], retries=d["retries"], log=log)
        if batch is None:
            complete = False
            break
        if not batch:
            break
        for k in batch:
            if int(k[6]) < now_ms and int(k[0]) < end_ms:            # close time passed: a closed bar
                rows.append((int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]),
                             float(k[7]), float(k[8]), float(k[9])))
        cursor = int(batch[-1][0]) + step
        pages += 1
        if on_pages and pages % int(d["save_every_pages"]) == 0 and rows:
            on_pages(_frame(rows))
            _say(log, "klines: %d bars fetched, at %s" % (len(rows), pd.to_datetime(cursor, unit="ms")))
        if len(batch) < int(d["page_limit"]):
            break
        time.sleep(float(d["pause_s"]))
    return (_frame(rows) if rows else pd.DataFrame(columns=BAR_COLS, index=store.from_ms([])).astype(float)), complete


def gap_list(index, interval_ms):
    """-> list of (last bar before the gap, first bar after it, missing bar count)."""
    ms = store.to_ms(index)
    if len(ms) < 2:
        return []
    step = np.diff(ms)
    where = np.nonzero(step != interval_ms)[0]
    return [(str(index[i]), str(index[i + 1]), int(step[i] // interval_ms) - 1) for i in where]


def clean(df, interval_ms):
    """Sort, de-duplicate, drop the pre-listing no-trade head and OHLC-invalid bars.
    Gaps are reported, not filled. -> (clean frame, report dict)."""
    rep = {"rows_in": int(len(df))}
    if not len(df):
        rep.update({"rows": 0, "first_bar": None, "last_bar": None, "gap_events": 0, "missing_bars": 0})
        return df, rep
    df = df.sort_index(kind="mergesort")                         # stable: of two copies, the later one wins
    dup = df.index.duplicated(keep="last")
    rep["duplicates_dropped"] = int(dup.sum())
    df = df[~dup]
    # the listing head: placeholder bars with no volume or a flat price (BTCUSDT: 5 bars at 10,000 on 8 Sep 2019)
    traded = np.nonzero((df["volume"].values > 0) & (df["high"].values > df["low"].values))[0]
    head = int(traded[0]) if len(traded) else len(df)
    rep["pre_listing_bars_dropped"] = head
    df = df.iloc[head:]
    px = df[["open", "high", "low", "close"]]
    bad = (px.isna().any(axis=1) | (px <= 0).any(axis=1) | (df["high"] < px[["open", "close"]].max(axis=1))
           | (df["low"] > px[["open", "close"]].min(axis=1)) | (df["high"] < df["low"]) | (df["volume"] < 0))
    rep["ohlc_invalid_dropped"] = int(bad.sum())
    rep["ohlc_invalid_examples"] = [str(t) for t in df.index[bad.values][:10]]
    df = df[~bad.values]
    gl = gap_list(df.index, interval_ms)
    rep.update({"rows": int(len(df)), "first_bar": str(df.index[0]) if len(df) else None,
                "last_bar": str(df.index[-1]) if len(df) else None,
                "gap_events": len(gl), "missing_bars": int(sum(g[2] for g in gl)),
                "largest_gaps": sorted(gl, key=lambda g: -g[2])[:10],
                "zero_volume_bars": int((df["volume"] == 0).sum()),
                "zero_volume_examples": [str(t) for t in df.index[(df["volume"] == 0).values][:25]]})
    return df, rep


def load_bars(cfg):
    df = store.read_frame(bars_path(cfg))
    return df[BAR_COLS].astype(float) if len(df) else df


def update_klines(cfg, log=None):
    """Create or extend the stored bars; resumable. -> (clean bars, report)."""
    d = cfg["data"]
    old = load_bars(cfg)
    start = int(pd.Timestamp(d["start"], tz="UTC").value // 10**6)
    if len(old):
        start = int(store.to_ms(old.index[-1:])[0]) + int(d["interval_ms"])

    def save(new):
        merged = pd.concat([old, new]) if len(old) else new
        store.write_frame(clean(merged, int(d["interval_ms"]))[0], bars_path(cfg))

    new, complete = fetch_klines(d, start, log=log, on_pages=save)
    merged = pd.concat([old, new]) if len(old) else new
    bars, rep = clean(merged, int(d["interval_ms"]))
    if len(bars):
        store.write_frame(bars, bars_path(cfg))
    rep.update({"new_bars": int(len(new)), "fetch_complete": bool(complete)})
    return bars, rep


# ---------------------------------------------------------------- funding

def settlement_ms(raw_ms, interval_ms=900000, snap_s=60):
    """Raw settlement stamps -> settlement times on the 15m grid. A stamp at most `snap_s`
    after a grid time is that grid time; anything else rounds UP (never earlier than stamped)."""
    raw = np.asarray(raw_ms, dtype="int64")
    floor = raw - raw % interval_ms
    ceil = np.where(raw % interval_ms == 0, raw, floor + interval_ms)
    return np.where(raw - floor <= snap_s * 1000, floor, ceil).astype("int64")


def load_funding(cfg):
    """-> frame indexed by the raw settlement stamp: rate, settle_ms (grid settlement time)."""
    f = store.read_frame(funding_path(cfg), index_name="funding_time")
    if not len(f):
        return pd.DataFrame({"rate": [], "settle_ms": []}, index=store.from_ms([], "funding_time"))
    f["settle_ms"] = settlement_ms(store.to_ms(f.index), int(cfg["data"]["interval_ms"]), cfg["data"]["funding_snap_s"])
    return f[["rate", "settle_ms"]]


def update_funding(cfg, log=None):
    """Extend the stored funding history (seeded read-only from engine15.data's file). -> report."""
    d = cfg["data"]
    old = store.read_frame(funding_path(cfg), index_name="funding_time")
    if not len(old):
        try:                                                     # reuse the engine's own funding file (read only)
            from .. import data as edata
            s = edata.load_funding(d["symbol"])
            if len(s):
                old = pd.DataFrame({"rate": s.values.astype(float)}, index=store.from_ms(edata.to_ms(s.index), "funding_time"))
                _say(log, "funding: seeded %d rows from data/%s_funding.csv" % (len(old), d["symbol"].lower()))
        except Exception as e:
            _say(log, "funding: could not seed from engine15.data (%s)" % e)
    cursor = (int(store.to_ms(old.index[-1:])[0]) + 1) if len(old) else int(pd.Timestamp(d["start"], tz="UTC").value // 10**6)
    rows, complete = [], True
    while True:
        batch = _get(d["base_url"] + "/fapi/v1/fundingRate", {"symbol": d["symbol"], "startTime": cursor, "limit": 1000},
                     timeout=d["timeout_s"], retries=d["retries"], log=log)
        if batch is None:
            complete = False
            break
        rows += [(int(b["fundingTime"]), float(b["fundingRate"])) for b in batch]
        if len(batch) < 1000:
            break
        cursor = int(batch[-1]["fundingTime"]) + 1
        time.sleep(float(d["pause_s"]))
    new = pd.DataFrame({"rate": [r for _, r in rows]}, index=store.from_ms([t for t, _ in rows], "funding_time"))
    allf = pd.concat([old, new]) if len(old) else new
    allf = allf[~allf.index.duplicated(keep="last")].sort_index()
    if len(allf):
        store.write_frame(allf, funding_path(cfg), index_name="funding_time")
    return {"rows": int(len(allf)), "new": int(len(new)), "fetch_complete": complete,
            "first": str(allf.index[0]) if len(allf) else None, "last": str(allf.index[-1]) if len(allf) else None}


# ---------------------------------------------------------------- open interest (LIVE ONLY)

def load_open_interest(cfg):
    return store.read_frame(oi_path(cfg))


def update_open_interest(cfg, log=None):
    """Fetch the ~30 days the free endpoint keeps and merge into the store. LIVE ONLY:
    the history is far too short for any backtest, so features ignore it unless
    data.open_interest.enabled_in_backtest is set (it is not)."""
    d = cfg["data"]
    old = load_open_interest(cfg)
    rows, end, complete = [], None, True
    for _ in range(12):                                          # 12 pages x 500 x 15m covers > 30 days
        params = {"symbol": d["symbol"], "period": d["open_interest"]["period"], "limit": 500}
        if end is not None:
            params["endTime"] = end
        batch = _get(d["base_url"] + "/futures/data/openInterestHist", params,
                     timeout=d["timeout_s"], retries=d["retries"], log=log)
        if batch is None:
            complete = bool(rows)                                # past the ~30 days kept, the endpoint refuses
            break
        if not batch:
            break
        rows += [(int(b["timestamp"]), float(b["sumOpenInterest"]), float(b["sumOpenInterestValue"])) for b in batch]
        first = min(int(b["timestamp"]) for b in batch)
        if end is not None and first >= end:
            break
        end = first - 1
        if len(batch) < 500:
            break
        time.sleep(float(d["pause_s"]))
    new = pd.DataFrame({"oi": [r[1] for r in rows], "oi_value": [r[2] for r in rows]},
                       index=store.from_ms([r[0] for r in rows]))
    allo = pd.concat([old, new]) if len(old) else new
    allo = allo[~allo.index.duplicated(keep="last")].sort_index()
    if len(allo):
        store.write_frame(allo, oi_path(cfg))
    return {"rows": int(len(allo)), "new": int(len(new)), "fetch_complete": complete, "live_only": OI_LIVE_ONLY,
            "first": str(allo.index[0]) if len(allo) else None, "last": str(allo.index[-1]) if len(allo) else None}


def update_all(cfg, log=None, offline=False):
    """-> (bars, funding, report). With offline=True nothing is fetched."""
    rep = {}
    if offline:
        bars, rep["bars"] = clean(load_bars(cfg), int(cfg["data"]["interval_ms"]))
    else:
        bars, rep["bars"] = update_klines(cfg, log)
        rep["funding"] = update_funding(cfg, log)
        if cfg["data"]["open_interest"].get("fetch"):
            rep["open_interest"] = update_open_interest(cfg, log)
    fund = load_funding(cfg)
    rep.setdefault("funding", {"rows": int(len(fund))})
    return bars, fund, rep
