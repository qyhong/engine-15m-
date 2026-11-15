# -*- coding: utf-8 -*-
"""options_hist -- Deribit option trade history (BTC and ETH), aggregated per UTC hour, for hypothesis H40.

  hourly     every inverse option trade from history.deribit.com (public/get_last_trades_by_currency_and_time,
             kind=option, no key), folded as it arrives into one row per UTC hour per coin: put / call notional and
             counts, taker buys, block-trade flow, premium, and amount-weighted trade IV in a 25-delta put bucket, a
             25-delta call bucket and an at-the-money bucket (expiries 7-60 days away; delta from Black-Scholes with the
             trade's own IV and the index price). Raw trade pages are never kept.

NOT WIRED INTO THE LIVE ENGINE: not listed in sources.MODULES, nothing in the live loop imports it
(tests/test_sources_options_hist.py::test_not_wired_into_the_live_engine). Wiring is a separate, versioned,
owner-approved step. Data source of research/options_study.py (H40) and, from batch 3 (15 Nov 2026, built not wired),
of the "Options flow (Deribit)" card in sources/cryptox.py, which calls update(live=True).

Storage: data/sources/options_hourly_<asset>.csv, written to a .tmp file and swapped in, ONLY EVER EXTENDED (a stored
hour is never changed). update() resumes at the hour after the file's last row and works at most one UTC day per
request series; it stores every hour of what it fetched (an hour without trades is a row of zeros), so the file's last
row is the resume point: an interrupted fetch repeats at most the chunks not yet flushed (FLUSH_DAYS). By default it
stops at the last whole UTC day (the H40 backfill); live=True stops at the last whole hour that ended LIVE_LAG_MS ago.
The H40 seal (2025-11-11) is applied by the study (cutoff_ms), not by the file: rows after it exist for the live card.

THE ONE RULE: a row may use only what was known at its decision instant. Trades are public the moment they print, so
the hour [T, T + 1 h) is known at known_ms = T + 1 h (KNOWN_LAG_MS = 0); an hour first fetched within LIVE_WINDOW_MS of
its end (a live fetch) is known at the later of T + 1 h and the fetch time. Readings are computed on the gapless hourly grid
with backward windows only, then joined as of known_ms (flows._asof). inputs(..., cutoff_ms=...) drops every stored row
known at or after cutoff_ms before anything is computed.

Docs: docs/SOURCES_options_hist.md. No reading here is claimed to predict anything.
"""
import json
import math
import os
import re
import sys
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from ..config import DATA_DIR
from .flows import _asof, _write                       # the same as-of join and atomic write as flows.py

SRC_DIR = os.path.join(DATA_DIR, "sources")
HIST = "https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}   # generic; nothing personal
TIMEOUT_S = 40
PAUSE_S = 0.60                                          # per process, from the end of one request to the next
RETRIES = 5                                             # on 429 / 5xx / network error: back off 2, 4, 8, 16, 32 s
RATE_LIMIT_WAIT_S = 30.0                                # at least this long after a 429
PAGE = 1000                                             # the documented maximum count per call
FLUSH_DAYS = 7                                          # days kept in memory before the CSV is extended

BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
YEAR_MS = 365.0 * DAY_MS
COIN = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
EARLIEST_SERVED = {"BTCUSDT": "2016-11-29", "ETHUSDT": "2019-03-21"}   # first option trade served (probed 14 Nov 2026)
FETCH_START = {"BTCUSDT": "2019-01-01", "ETHUSDT": "2019-03-21"}       # dev bars start 2019-09-08; earlier is not needed
KNOWN_LAG_MS = 0
LIVE_LAG_MS = 5 * 60000                                 # live=True: an hour is fetched once it ended 5 minutes ago
LIVE_WINDOW_MS = 6 * 3600000                            # an hour first fetched within 6 h of its end: known at the fetch

# ---- the buckets (registered in research/HYPOTHESES.md H40 before any history was fetched)
TENOR_MIN_D, TENOR_MAX_D = 7.0, 60.0
RR_LO, RR_HI = 0.15, 0.35                               # |delta| of the 25-delta buckets
ATM_LO, ATM_HI = 0.40, 0.60
EXPIRY_HOUR_UTC = 8

# ---- the H40 transforms (windows in hours, ending at the decision)
W7, W1, W3 = 7 * 24, 24, 72
Z_DAYS, Z_MIN = 90, 30
RR_MIN_N, BLK_MIN_N = 10, 5
MAX_AGE = 3 * HOUR_MS                                   # an hourly value older than this is "no read"
UNITS = OrderedDict([                                   # feature = clip(input / unit, +-3)
    ("op_pcr_7d", 0.25), ("op_pcr_1d_z90", 1.0), ("op_taker_bear_7d", 0.10),
    ("op_rr25", 5.0), ("op_rr25_chg7", 3.0), ("op_block_bear_7d", 0.20)])
INPUTS = list(UNITS)
GROUPS = OrderedDict([("options_hist", ("Deribit options flow (history)", INPUTS))])
FEATURES = list(INPUTS)
APPLIES = {"options_hist": ("BTCUSDT", "ETHUSDT")}
RAW = ["op_put_usd_24h", "op_call_usd_24h", "op_trades_24h", "op_atm_iv"]

HOURLY_COLS = ["ts_ms", "n", "n_put", "n_call", "put_usd", "call_usd", "put_buy_usd", "call_buy_usd",
               "prem_put_usd", "prem_call_usd", "blk_n", "blk_put_buy_usd", "blk_put_sell_usd", "blk_call_buy_usd",
               "blk_call_sell_usd", "rr_put_ivw", "rr_put_w", "rr_put_n", "rr_call_ivw", "rr_call_w", "rr_call_n",
               "atm_ivw", "atm_w", "skipped", "known_ms"]
SUM_COLS = HOURLY_COLS[1:-1]
FILES = OrderedDict([("hourly", HOURLY_COLS)])
_MON = dict((m, i + 1) for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
                                               "NOV", "DEC"]))
_NAME = re.compile(r"^([A-Z]+)-(\d{1,2})([A-Z]{3})(\d{2})-([0-9d.]+)-([PC])$")


# ------------------------------------------------------------------ storage
def path_for(kind, asset, src_dir=None):
    """-> data/sources/options_<kind>_<asset>.csv"""
    return os.path.join(src_dir or SRC_DIR, "options_%s_%s.csv" % (kind, asset.lower()))


def load_source(kind, asset, src_dir=None):
    cols, path = FILES[kind], path_for(kind, asset, src_dir)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(dict((c, pd.Series(dtype="float64")) for c in cols))
    d = pd.read_csv(path, float_precision="round_trip")         # exact: a re-written stored row stays bit-identical
    for c in cols:
        if c not in d:
            d[c] = np.nan
    d = d[cols].dropna(subset=["ts_ms"])
    d["ts_ms"] = d["ts_ms"].astype("int64")
    d[cols[1:]] = d[cols[1:]].apply(pd.to_numeric, errors="coerce").astype(float)
    return d.drop_duplicates("ts_ms", keep="first").sort_values("ts_ms").reset_index(drop=True)


def _extend(kind, asset, src_dir, old, new):
    """Append rows whose hour is not stored yet. A stored row is NEVER changed. -> rows on disk."""
    if new is None or not len(new):
        return len(old)
    new = new[FILES[kind]]
    if len(old):
        new = new[~new["ts_ms"].isin(set(old["ts_ms"]))]
    if not len(new):
        return len(old)
    both = pd.concat([old, new], ignore_index=True) if len(old) else new.copy()
    both = both.drop_duplicates("ts_ms", keep="first").sort_values("ts_ms")
    both["ts_ms"] = both["ts_ms"].astype("int64")
    _write(path_for(kind, asset, src_dir), both)
    return len(both)


# ------------------------------------------------------------------ one trade -> the hour's sums
def parse_instrument(name):
    """'BTC-25MAR22-50000-P' -> (expiry epoch ms at 08:00 UTC, strike, 'P' or 'C'), or None."""
    m = _NAME.match(str(name))
    if not m or m.group(3) not in _MON:
        return None
    try:
        day, mon, yr = int(m.group(2)), _MON[m.group(3)], 2000 + int(m.group(4))
        strike = float(m.group(5).replace("d", "."))
        exp = int(pd.Timestamp(year=yr, month=mon, day=day, hour=EXPIRY_HOUR_UTC, tz="UTC").value // 10 ** 6)
    except (ValueError, TypeError):
        return None
    return exp, strike, m.group(6)


def bs_delta(spot, strike, years, vol, kind):
    """Black-Scholes delta with zero rates (the forward approximated by the index). vol as a fraction."""
    if not (spot > 0 and strike > 0 and years > 0 and vol > 0):
        return float("nan")
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * years) / (vol * math.sqrt(years))
    nd1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
    return nd1 if kind == "C" else nd1 - 1.0


def _empty_hour():
    return dict((c, 0.0) for c in SUM_COLS)


def add_trade(acc, t, cache=None):
    """Fold one trade (a dict as the API returns it) into acc (a dict of SUM_COLS). Returns False when skipped."""
    cache = {} if cache is None else cache
    name = t.get("instrument_name")
    if name not in cache:
        cache[name] = parse_instrument(name)
    parsed = cache[name]
    try:
        amt, idx, ts = float(t["amount"]), float(t["index_price"]), int(t["timestamp"])
        price = float(t.get("price") or 0.0)
    except (KeyError, TypeError, ValueError):
        parsed = None
    if parsed is None or not (amt > 0 and idx > 0):
        acc["skipped"] += 1
        return False
    exp, strike, kind = parsed
    usd = amt * idx
    buy = str(t.get("direction")) == "buy"
    put = kind == "P"
    acc["n"] += 1
    acc["n_put" if put else "n_call"] += 1
    acc["put_usd" if put else "call_usd"] += usd
    if buy:
        acc["put_buy_usd" if put else "call_buy_usd"] += usd
    acc["prem_put_usd" if put else "prem_call_usd"] += price * usd
    if t.get("block_trade_id"):
        acc["blk_n"] += 1
        acc["blk_%s_%s_usd" % ("put" if put else "call", "buy" if buy else "sell")] += usd
    try:
        iv = float(t.get("iv"))
    except (TypeError, ValueError):
        iv = float("nan")
    days = (exp - ts) / float(DAY_MS)
    if np.isfinite(iv) and iv > 0 and TENOR_MIN_D <= days <= TENOR_MAX_D:
        d = abs(bs_delta(idx, strike, (exp - ts) / YEAR_MS, iv / 100.0, kind))
        if RR_LO <= d <= RR_HI:
            side = "rr_put" if put else "rr_call"
            acc[side + "_ivw"] += iv * amt
            acc[side + "_w"] += amt
            acc[side + "_n"] += 1
        elif ATM_LO <= d <= ATM_HI:
            acc["atm_ivw"] += iv * amt
            acc["atm_w"] += amt
    return True


def aggregate_hours(trades, start_ms, n_hours):
    """All trades of [start_ms, start_ms + n_hours h) -> n_hours hourly rows (zeros for an hour without trades), with
    known_ms = hour end. start_ms must be on the hour."""
    hours = [_empty_hour() for _ in range(n_hours)]
    cache = {}
    for t in trades:
        try:
            h = (int(t["timestamp"]) - start_ms) // HOUR_MS
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= h < n_hours:
            add_trade(hours[h], t, cache)
    f = pd.DataFrame(hours, columns=SUM_COLS)
    f.insert(0, "ts_ms", start_ms + np.arange(n_hours, dtype="int64") * HOUR_MS)
    f["known_ms"] = f["ts_ms"] + HOUR_MS + KNOWN_LAG_MS
    return f[HOURLY_COLS]


def aggregate_day(trades, day_ms):
    """All trades of one UTC day -> 24 hourly rows (zeros for an hour without trades), with known_ms = hour end."""
    return aggregate_hours(trades, day_ms, 24)


def live_known(known_ms, seen_ms):
    """An hour first fetched within LIVE_WINDOW_MS of its end is known at the later of its end and the fetch time, so a
    replay never knows more than a live run did. A backfilled hour keeps its end."""
    known_ms = np.asarray(known_ms, dtype="int64")
    live = int(seen_ms) - known_ms < LIVE_WINDOW_MS
    return np.where(live, np.maximum(known_ms, int(seen_ms)), known_ms).astype("int64")


# ------------------------------------------------------------------ network (update only)
_last = {}


def _get(url, params=None):
    """One polite GET (a pause per host, generic user agent, no key) with back-off on 429 / 5xx / network errors.
    -> the decoded JSON 'result'; raises otherwise."""
    import requests
    host = url.split("/")[2]
    err = None
    for attempt in range(RETRIES + 1):
        wait = PAUSE_S - (time.time() - _last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        r = None
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT_S)
        except Exception as e:
            err = e
        finally:
            _last[host] = time.time()
        if r is not None and r.status_code == 200:
            j = r.json()
            if "result" in j:
                return j["result"]
            err = RuntimeError("no result: %s" % str(j)[:80])
        elif r is not None and r.status_code != 429 and r.status_code < 500:
            raise RuntimeError("HTTP %d from %s: %s" % (r.status_code, host, r.text[:80].replace("\n", " ")))
        if attempt == RETRIES:
            raise RuntimeError("gave up on %s: %s" % (host, err if err is not None else "HTTP %d" % r.status_code))
        limited = r is not None and r.status_code == 429
        time.sleep(max(2.0 * 2 ** attempt, RATE_LIMIT_WAIT_S if limited else 0.0))


def fetch_day(asset, day_ms, stats=None):
    """Every option trade of one UTC day. -> list of trade dicts."""
    return fetch_range(asset, day_ms, day_ms + DAY_MS, stats)


def fetch_range(asset, start_ms, end_ms, stats=None):
    """Every option trade in [start_ms, end_ms), paging forward in time; trades sharing the page-boundary millisecond
    are asked for again and de-duplicated by trade_id. -> list of trade dicts."""
    stats = {} if stats is None else stats
    end = end_ms - 1
    cursor, seen, out = start_ms, set(), []
    while cursor <= end:
        res = _get(HIST, {"currency": COIN[asset], "kind": "option", "start_timestamp": cursor, "end_timestamp": end,
                          "count": PAGE, "sorting": "asc"})
        stats["requests"] = stats.get("requests", 0) + 1
        trades = res.get("trades") or []
        fresh = [t for t in trades if t.get("trade_id") not in seen]
        for t in fresh:
            seen.add(t.get("trade_id"))
        out += fresh
        if not res.get("has_more") or not trades:
            break
        last = int(trades[-1]["timestamp"])
        if not fresh or last <= cursor and len(trades) >= PAGE:     # a full page inside one millisecond: step past it
            stats["stuck_ms"] = stats.get("stuck_ms", 0) + 1
            cursor = max(cursor, last) + 1
        else:
            cursor = last
    return out


def update(log=print, src_dir=None, assets=None, end_ms=None, start=None, max_days=None, live=False, max_hours=None):
    """Fetch / extend the hourly file of each coin from the hour after the file's last row (or FETCH_START / start), at
    most one UTC day per chunk, up to the last whole day before end_ms (default: now), or with live=True up to the last
    whole hour that ended LIVE_LAG_MS before it. max_days caps the chunks, max_hours the hours fetched (the live card
    caps each call so the live loop is never held long). -> {"hourly_<ASSET>": rows on disk, or "failed: <reason>
    (file has N rows)"}. Never raises; what was flushed before a failure stays."""
    out = OrderedDict()
    now = int(time.time() * 1000)
    end = min(end_ms, now) if end_ms is not None else now
    stop = (end - LIVE_LAG_MS) // HOUR_MS * HOUR_MS if live else end // DAY_MS * DAY_MS   # first hour NOT fetched
    for asset in assets or list(COIN):
        key = "hourly_%s" % asset
        stats, n = {}, 0
        try:
            old = load_source("hourly", asset, src_dir)
            n = len(old)
            if len(old):
                cur = int(old["ts_ms"].iloc[-1]) // HOUR_MS * HOUR_MS + HOUR_MS
            else:
                cur = int(pd.Timestamp(start or FETCH_START[asset], tz="UTC").value // 10 ** 6) // HOUR_MS * HOUR_MS
            buf, done, hours, t0 = [], 0, 0, time.time()
            while cur < stop and (max_days is None or done < max_days) and (max_hours is None or hours < max_hours):
                nxt = min((cur // DAY_MS + 1) * DAY_MS, stop)
                if max_hours is not None:
                    nxt = min(nxt, cur + (max_hours - hours) * HOUR_MS)
                rows = aggregate_hours(fetch_range(asset, cur, nxt, stats), cur, (nxt - cur) // HOUR_MS)
                rows["known_ms"] = live_known(rows["known_ms"].values, int(time.time() * 1000))
                buf.append(rows)
                hours += (nxt - cur) // HOUR_MS
                cur = nxt
                done += 1
                if (len(buf) >= FLUSH_DAYS or cur >= stop or (max_days is not None and done >= max_days)
                        or (max_hours is not None and hours >= max_hours)):
                    n = _extend("hourly", asset, src_dir, old, pd.concat(buf, ignore_index=True))
                    old, buf = load_source("hourly", asset, src_dir), []
                    try:
                        log("sources.options_hist %s: through %s, %d rows, %d requests, %.0f s" % (
                            asset, pd.Timestamp(cur - HOUR_MS, unit="ms").strftime("%Y-%m-%d %H:00"), n,
                            stats.get("requests", 0), time.time() - t0))
                    except Exception:
                        pass
            out[key] = int(n)
        except Exception as e:
            out[key] = "failed: %s (file has %d rows)" % ((str(e) or type(e).__name__)[:140], n)
        if stats.get("stuck_ms"):
            out[key + "_stuck_ms"] = int(stats["stuck_ms"])
        try:
            log("sources.options_hist %s: %s" % (key, out[key]))
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ readings (files only)
def _hourly_grid(asset, src_dir=None, cutoff_ms=None):
    h = load_source("hourly", asset, src_dir)
    if cutoff_ms is not None:
        h = h[h["known_ms"] < cutoff_ms]
    if not len(h):
        return h.set_index(pd.Index([], dtype="int64"))
    g = h.set_index("ts_ms")
    return g.reindex(np.arange(int(g.index[0]), int(g.index[-1]) + HOUR_MS, HOUR_MS, dtype="int64"))


def _roll(s, n):
    return s.rolling(n, min_periods=n).sum()                         # a window with a missing hour is NaN


def _ln_ratio(a, b):
    return np.log(a.where(a > 0) / b.where(b > 0))


def readings(g):
    """Hourly grid -> frame on the same grid with the H40 transforms (value at hour T uses hours up to T only)."""
    out = pd.DataFrame(index=g.index)
    if not len(g):
        for c in INPUTS + RAW:
            out[c] = pd.Series(dtype=float)
        return out
    put, call = g["put_usd"], g["call_usd"]
    out["op_pcr_7d"] = _ln_ratio(_roll(put, W7), _roll(call, W7))
    p1 = _ln_ratio(_roll(put, W1), _roll(call, W1))
    phase = (g.index.values // HOUR_MS) % 24                         # each hour of the day: its own daily series
    mu = p1.groupby(phase).transform(lambda s: s.rolling(Z_DAYS, min_periods=Z_MIN).mean())
    sd = p1.groupby(phase).transform(lambda s: s.rolling(Z_DAYS, min_periods=Z_MIN).std())
    out["op_pcr_1d_z90"] = (p1 - mu) / sd.where(sd > 0)
    tot = _roll(put + call, W7)
    pb, cb = _roll(g["put_buy_usd"], W7), _roll(g["call_buy_usd"], W7)
    ps, cs = _roll(put, W7) - pb, _roll(call, W7) - cb
    out["op_taker_bear_7d"] = ((pb - ps) - (cb - cs)) / tot.where(tot > 0)
    pw, cw = _roll(g["rr_put_w"], W3), _roll(g["rr_call_w"], W3)
    ok = (_roll(g["rr_put_n"], W3) >= RR_MIN_N) & (_roll(g["rr_call_n"], W3) >= RR_MIN_N)
    rr = (_roll(g["rr_put_ivw"], W3) / pw.where(pw > 0) - _roll(g["rr_call_ivw"], W3) / cw.where(cw > 0)).where(ok)
    out["op_rr25"] = rr
    out["op_rr25_chg7"] = rr - rr.shift(W7)
    bpb, bps = _roll(g["blk_put_buy_usd"], W7), _roll(g["blk_put_sell_usd"], W7)
    bcb, bcs = _roll(g["blk_call_buy_usd"], W7), _roll(g["blk_call_sell_usd"], W7)
    btot = bpb + bps + bcb + bcs
    out["op_block_bear_7d"] = (((bpb - bps) - (bcb - bcs)) / btot.where(btot > 0)).where(_roll(g["blk_n"], W7) >= BLK_MIN_N)
    out["op_put_usd_24h"] = _roll(put, W1)
    out["op_call_usd_24h"] = _roll(call, W1)
    out["op_trades_24h"] = _roll(g["n"], W1)
    aw = _roll(g["atm_w"], W1)
    out["op_atm_iv"] = _roll(g["atm_ivw"], W1) / aw.where(aw > 0)
    return out.replace([np.inf, -np.inf], np.nan)


def inputs(close_ms, asset, src_dir=None, cutoff_ms=None):
    """-> frame indexed like close_ms (epoch ms of decision instants) with the H40 transforms (INPUTS, unclipped) and
    the RAW columns, each the newest value KNOWN at or before the instant (NaN = no read). cutoff_ms: drop every stored
    row known at or after it before computing anything (the study passes the holdout seal)."""
    close_ms = np.asarray(close_ms, dtype="int64")
    out = pd.DataFrame(np.nan, index=close_ms, columns=INPUTS + RAW)
    errors = {}
    try:
        g = _hourly_grid(asset, src_dir, cutoff_ms)
        if len(g):
            r = readings(g)
            k = g["known_ms"].values                                 # a filled-in (missing) hour has NaN: never used
            for c in INPUTS + RAW:
                out[c] = _asof(k, r[c].values, close_ms, MAX_AGE)
    except Exception as e:
        errors["hourly"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    out.attrs["errors"] = errors
    return out


def features(index15, asset, src_dir=None, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature clipped to +-3 (0.0 = no read, never NaN) plus the
    RAW columns (NaN = no read). Reads only files."""
    index15 = pd.DatetimeIndex(index15)
    x = inputs(_data.to_ms(index15) + BAR_MS, asset, src_dir)
    out = pd.DataFrame(index=index15)
    for f in FEATURES:
        out[f] = np.clip(x[f].values / UNITS[f], -3.0, 3.0)
    for r in RAW:
        out[r] = x[r].values
    out[FEATURES] = out[FEATURES].astype(float).fillna(0.0)
    out.attrs["errors"] = x.attrs["errors"]
    return out


def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    coin, title = COIN.get(asset, asset), GROUPS["options_hist"][0]
    p, c = _num(row, "op_put_usd_24h"), _num(row, "op_call_usd_24h")
    if p is None or c is None:
        return OrderedDict([(title, "No Deribit option-trade history read for %s at this close." % coin)])
    bits = ["$%.0fm of puts and $%.0fm of calls traded over 24 hours" % (p / 1e6, c / 1e6)]
    rr = _num(row, "op_rr25")                                        # the clipped feature: vol points / UNITS
    if rr is not None and rr != 0.0:
        bits.append("25-delta put trade IV about %+.1f vol points over calls (3 days)" % (rr * UNITS["op_rr25"]))
    iv = _num(row, "op_atm_iv")
    if iv is not None:
        bits.append("at-the-money trade IV %.0f%%" % iv)
    return OrderedDict([(title, "Deribit %s options: %s." % (coin, "; ".join(bits)))])


def main(argv=None):
    """py -3 -m engine15.sources.options_hist BTCUSDT [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--max-days N] [--src DIR]
    [--live] (--start applies only to an empty file; --src writes to another folder, e.g. a second date range to merge
    later; --live fetches up to the last whole hour instead of the last whole day)"""
    argv = list(sys.argv[1:] if argv is None else argv)
    assets = [a for a in argv if a in COIN] or list(COIN)
    end = argv[argv.index("--end") + 1] if "--end" in argv else None
    maxd = int(argv[argv.index("--max-days") + 1]) if "--max-days" in argv else None
    start = argv[argv.index("--start") + 1] if "--start" in argv else None
    src = argv[argv.index("--src") + 1] if "--src" in argv else None
    end_ms = int(pd.Timestamp(end, tz="UTC").value // 10 ** 6) if end else None
    res = update(log=lambda s: print(time.strftime("%H:%M:%S"), s, flush=True), src_dir=src, assets=assets,
                 end_ms=end_ms, start=start, max_days=maxd, live="--live" in argv)
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
