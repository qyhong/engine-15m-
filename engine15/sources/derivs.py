# -*- coding: utf-8 -*-
"""derivs -- five decision cards read from the derivatives tape and from the clock.

  basis     Perp basis and premium            Binance USDT-perp premium index, 15m bars, late 2019 on
  lsratio   Long/short positioning            Binance account / top-trader / taker ratios, 15m, ~30 days + what update keeps
  liq       Liquidation pressure (proxy)      open-interest drops joined with large price bars; NOT a liquidation feed
  options   Options: implied vol and skew     Deribit DVOL (hourly, 2021 on) + a live put/call and skew read
  clock     Time and session                  pure computation, no network

Everything is kept as CSV under data/sources/ (ts_ms first, written atomically, only ever
extended). `update` fetches what is newer than each file; `features` reads the files and
never the network.

THE ONE RULE (tests/test_sources_derivs.py): row i may use only what was known at the
close of 15m bar i (open + 15 minutes). Each stored row has a KNOWN-AT time:

    premium bar                     stamped at its open   -> known at stamp + 15 minutes
    DVOL hourly bar                 stamped at its open   -> known at stamp + 1 hour
    account / position ratios, OI   a snapshot at stamp   -> known at stamp + STATS_LAG_MS
    taker-volume bar                stamped at its open   -> known at stamp + 15 minutes + STATS_LAG_MS
    options live read               stamped when fetched  -> known at stamp

STATS_LAG_MS exists because Binance publishes its futures statistics late: measured on
10 Nov 2026, the taker bar appeared 57 s after its period ended and the ratio and
open-interest snapshots 156 to 164 s after their stamp, while the live loop steps 75 s after
a close. So the statistics of bar i reach row i+1, in the replay exactly as they would live.

Every reading is computed on the source's own gapless time grid, looking backward only, and
is then handed to the 15m row whose close is at or after its known-at time (and not staler
than the source's MAX_AGE; staler than that is "no read", 0.0).

Docs: docs/SOURCES_derivs.md. No reading here is claimed to predict anything.
"""
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from ..config import CFG, DATA_DIR

SRC_DIR = os.path.join(DATA_DIR, "sources")          # override per call with src_dir=...
FAPI = "https://fapi.binance.com"
DERIBIT = "https://www.deribit.com/api/v2/public/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PAUSE_S = 0.35                                        # between any two requests (the brief asks >= 0.25)
TIMEOUT_S = 30

BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
BASIS_START_MS = 1567296000000                        # 2019-09-01: before the first premium bar Binance serves
DVOL_START_MS = 1614556800000                         # 2021-03-01: before the first DVOL hour Deribit serves
STATS_KEEP_MS = 30 * DAY_MS - HOUR_MS                 # Binance serves ~30 days of /futures/data/*

# ---- known-at lag of Binance's futures statistics (see the module docstring): published 1 to 3 minutes late
STATS_LAG_MS = 5 * 60000                              # anything from 1 ms to 15 min has the same effect: one bar later

# ---- how long a reading may stand in for a missing newer one before it is "no read"
BASIS_MAX_AGE = HOUR_MS
LS_MAX_AGE = HOUR_MS
LIQ_SUM_MAX_AGE = HOUR_MS
DVOL_MAX_AGE = 3 * HOUR_MS                            # an hourly value, so up to two missed hours
RV_MAX_AGE = HOUR_MS                                  # realised volatility is a 30-day figure; a bar late changes little
OPT_LIVE_MAX_AGE = 24 * HOUR_MS                       # option open interest moves slowly; update decides how fresh it is

# ---- scales (declared once, before any data was looked at for fit; see docs for the reason behind each)
PREMIUM_UNIT = 0.0005                                 # 0.05%: the same yardstick evidence.py uses for funding
BASIS_Z_BARS, BASIS_Z_MIN = 2880, 672                 # z-score against 30 days; needs 7 days to speak
LS_CHG_UNIT = 0.25                                    # a 24h move of 0.25 in ln(ratio) (about 28%) = 1.0
TAKER_UNIT = 0.20                                     # ln(1h taker buy/sell) of 0.20 (about 22% more buying) = 1.0
LIQ_SIGMA_BARS, LIQ_SIGMA_MIN = 672, 96               # "large" and "sharp" are judged against the prior 7 days
LIQ_OI_Z = 2.0                                        # a sharp OI drop: at least 2 sigma of the 15m OI change
LIQ_MOVE_Z = 2.0                                      # a large bar: at least 2 sigma of the 15m return
DVOL_RANGE_H, DVOL_RANGE_MIN = 2160, 720              # DVOL against its 90-day range; needs 30 days
DVOL_CHG_UNIT = 0.10                                  # a 10% relative change in DVOL over 24h = 1.0
RV_BARS, RV_MIN = 2880, 672                           # realised volatility over 30 days (DVOL is a 30-day figure)
ANNUAL_BARS = 96 * 365                                # 15m bars in a 365-day year, as DVOL annualises
IV_RV_UNIT = 20.0                                     # implied minus realised: 20 volatility points = 1.0
PCR_UNIT = 0.5                                        # ln(put OI / call OI) of 0.5 = 1.0
SKEW_UNIT = 10.0                                      # 10 volatility points of put-wing minus call-wing IV = 1.0
SKEW_WING = 0.10                                      # wings: strikes 10% below and above the forward
SKEW_DAYS = (7.0, 60.0, 30.0)                         # use the expiry nearest 30 days, between 7 and 60
US_OPEN_CAP_H = 24.0                                  # hours to the US cash open: 0 at the open, 1.0 = a day or more
SESSIONS = OrderedDict([                              # cash hours in local time, Monday to Friday (holidays not modelled)
    ("asia", ("Asia/Tokyo", 9 * 60, 15 * 60)),
    ("europe", ("Europe/London", 8 * 60, 16 * 60 + 30)),
    ("us", ("America/New_York", 9 * 60 + 30, 16 * 60)),
])

GROUPS = OrderedDict([
    ("basis", ("Perp basis and premium", ["pb_level", "pb_z", "pb_chg_4h"])),
    ("lsratio", ("Long/short positioning",
                 ["ls_global", "ls_global_24h", "ls_top", "ls_top_24h", "ls_taker", "ls_taker_24h"])),
    ("liq", ("Liquidation pressure (proxy)", ["lq_bar", "lq_4h"])),
    ("options", ("Options: implied volatility and skew",
                 ["op_dvol_rank", "op_dvol_24h", "op_iv_rv", "op_pcr", "op_skew"])),
    ("clock", ("Time and session", ["ck_hour_sin", "ck_hour_cos", "ck_dow_sin", "ck_dow_cos", "ck_weekend",
                                    "ck_asia", "ck_europe", "ck_us", "ck_us_open_in"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
# readable columns for the journal (NaN = no read)
RAW = ["pb_premium_pct",                                              # the premium at the bar's close, in %
       "ls_global_ratio", "ls_top_ratio", "ls_taker_ratio",           # long/short ratios as published (taker: last hour)
       "lq_oi", "lq_oi_chg_pct", "lq_bar_sigma",                      # open interest; its change in and the size of the bar read
       "op_dvol", "op_rv", "op_pc_ratio", "op_skew_pts",              # DVOL, realised vol (both annualised %), live reads
       "ck_us_open_hours"]                                            # hours to the next US cash open

BASIS_COLS = ["ts_ms", "open", "high", "low", "close"]
LS_COLS = ["ts_ms", "global_ls", "global_long", "top_ls", "top_long", "taker_bs", "taker_buy", "taker_sell"]
OI_COLS = ["ts_ms", "oi", "oi_value"]
DVOL_COLS = ["ts_ms", "open", "high", "low", "close"]
OPT_LIVE_COLS = ["ts_ms", "put_oi", "call_oi", "pc_ratio", "skew_pts", "atm_iv", "expiry_days"]
FILES = OrderedDict([("basis", BASIS_COLS), ("lsratio", LS_COLS), ("liq_oi", OI_COLS),
                     ("options_dvol", DVOL_COLS), ("options_live", OPT_LIVE_COLS)])
LS_ENDPOINTS = OrderedDict([                           # name -> (path, {file column: API field}, the row covers a period)
    ("global", ("/futures/data/globalLongShortAccountRatio",
                OrderedDict([("global_ls", "longShortRatio"), ("global_long", "longAccount")]), 0)),
    ("top", ("/futures/data/topLongShortPositionRatio",
             OrderedDict([("top_ls", "longShortRatio"), ("top_long", "longAccount")]), 0)),
    ("taker", ("/futures/data/takerlongshortRatio",
               OrderedDict([("taker_bs", "buySellRatio"), ("taker_buy", "buyVol"), ("taker_sell", "sellVol")]), BAR_MS)),
])
_MONTHS = dict((m, i + 1) for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()))


# ------------------------------------------------------------------ storage
def path_for(kind, asset, src_dir=None):
    """kind: one of FILES. -> data/sources/<kind>_<asset>.csv"""
    return os.path.join(src_dir or SRC_DIR, "%s_%s.csv" % (kind, asset.lower()))


def load_source(kind, asset, src_dir=None):
    """-> the stored rows of one source file, ts_ms ascending and unique; empty when there is no file."""
    cols, path = FILES[kind], path_for(kind, asset, src_dir)
    if not os.path.exists(path):
        return pd.DataFrame(dict((c, pd.Series(dtype="int64" if c == "ts_ms" else "float64")) for c in cols))
    d = pd.read_csv(path)
    for c in cols:
        if c not in d:
            d[c] = np.nan
    d = d[cols].dropna(subset=["ts_ms"])
    d["ts_ms"] = d["ts_ms"].astype("int64")
    d[cols[1:]] = d[cols[1:]].astype(float)
    return d.drop_duplicates("ts_ms", keep="last").sort_values("ts_ms").reset_index(drop=True)


def _write(path, frame):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _extend(kind, asset, src_dir, old, rows):
    """Add fetched rows to a file (a newer row replaces an older one with the same stamp). -> rows on disk."""
    if not rows:
        return len(old)
    new = pd.DataFrame(rows, columns=FILES[kind])
    both = pd.concat([old, new], ignore_index=True) if len(old) else new
    both = both.drop_duplicates("ts_ms", keep="last").sort_values("ts_ms")
    both["ts_ms"] = both["ts_ms"].astype("int64")
    _write(path_for(kind, asset, src_dir), both)
    return len(both)


# ------------------------------------------------------------------ network (update only)
_last_request = [0.0]


def _get(url, params):
    """One polite GET -> parsed JSON; raises on any failure."""
    import requests
    wait = PAUSE_S - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT_S)
    finally:
        _last_request[0] = time.time()
    if r.status_code != 200:
        raise RuntimeError("HTTP %d %s" % (r.status_code, r.text[:60].replace("\n", " ")))
    return r.json()


def _update_basis(asset, src_dir, now_ms):
    old = load_source("basis", asset, src_dir)
    cursor = int(old["ts_ms"].iloc[-1]) + BAR_MS if len(old) else BASIS_START_MS
    rows, err = [], None
    try:
        while cursor + BAR_MS <= now_ms:
            batch = _get(FAPI + "/fapi/v1/premiumIndexKlines",
                         {"symbol": asset, "interval": "15m", "startTime": cursor, "limit": 1500})
            if not batch:
                break
            rows += [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]))
                     for k in batch if int(k[6]) < now_ms]            # close time passed: a closed bar
            cursor = int(batch[-1][0]) + BAR_MS
            if len(batch) < 1500:
                break
    except Exception as e:                                           # keep what was fetched; the next update resumes
        err = e
    n = _extend("basis", asset, src_dir, old, rows)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _fetch_stats(path, fields, period_ms, asset, last_ms, now_ms):
    """Binance /futures/data/* at period=15m, oldest first: everything stamped after last_ms that
    the API still serves. A row that covers a period is kept only once that period has ended.
    -> (rows, the error that stopped it or None); rows fetched before an error are contiguous."""
    floor = now_ms - STATS_KEEP_MS
    cursor, rows, first = max(last_ms + 1, floor), [], True
    try:
        while cursor <= now_ms:
            end = min(cursor + 500 * BAR_MS - 1, now_ms)
            try:
                batch = _get(FAPI + path, {"symbol": asset, "period": "15m", "limit": 500,
                                           "startTime": cursor, "endTime": end})
            except Exception:
                if first and cursor == floor:                        # the 30-day edge was refused: start a day later, once
                    cursor, first = now_ms - 29 * DAY_MS, False
                    continue
                raise
            first = False
            if not isinstance(batch, list):
                raise RuntimeError("unexpected reply %s" % str(batch)[:60])
            for x in batch:
                ts = int(x["timestamp"])
                if last_ms < ts and ts + period_ms <= now_ms:
                    rows.append((ts,) + tuple(float(x[f]) for f in fields.values()))
            cursor = end + 1
    except Exception as e:
        return rows, e
    return rows, None


def _update_lsratio(asset, src_dir, now_ms):
    old = load_source("lsratio", asset, src_dir)
    merged, errs, got = old.set_index("ts_ms"), [], 0
    for name, (path, fields, period_ms) in LS_ENDPOINTS.items():
        have = merged[list(fields)[0]].dropna()                      # each endpoint resumes from its own last row
        rows, err = _fetch_stats(path, fields, period_ms, asset, int(have.index[-1]) if len(have) else 0, now_ms)
        if err is not None:
            errs.append("%s: %s" % (name, str(err)[:70]))
        if rows:
            new = pd.DataFrame(rows, columns=["ts_ms"] + list(fields)).drop_duplicates("ts_ms", keep="last")
            merged = new.set_index("ts_ms").combine_first(merged)
            got += len(rows)
    if got:
        merged = merged.reindex(columns=LS_COLS[1:]).sort_index()
        merged.index = merged.index.astype("int64")
        merged.index.name = "ts_ms"
        _write(path_for("lsratio", asset, src_dir), merged.reset_index())
    if errs:
        raise RuntimeError("%s (file has %d rows)" % ("; ".join(errs), len(merged)))
    return len(merged)


def _update_oi(asset, src_dir, now_ms):
    old = load_source("liq_oi", asset, src_dir)
    fields = OrderedDict([("oi", "sumOpenInterest"), ("oi_value", "sumOpenInterestValue")])
    rows, err = _fetch_stats("/futures/data/openInterestHist", fields, 0, asset,
                             int(old["ts_ms"].iloc[-1]) if len(old) else 0, now_ms)
    n = _extend("liq_oi", asset, src_dir, old, rows)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _update_dvol(asset, src_dir, now_ms):
    old = load_source("options_dvol", asset, src_dir)
    cursor = int(old["ts_ms"].iloc[-1]) + HOUR_MS if len(old) else DVOL_START_MS
    rows, err = [], None
    try:
        while cursor + HOUR_MS <= now_ms:                            # forward, 1000 hours a request
            end = upto = min(cursor + 1000 * HOUR_MS - 1, now_ms)
            page = []
            while upto:                                              # Deribit pages backward inside a window, if at all
                reply = _get(DERIBIT + "get_volatility_index_data", {"currency": asset[:-4], "start_timestamp": cursor,
                                                                     "end_timestamp": upto, "resolution": 3600})["result"]
                page += [(int(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]))
                         for d in reply["data"] if int(d[0]) + HOUR_MS <= now_ms]         # the hour has ended
                upto = reply.get("continuation") if reply["data"] else None
            rows += page                                             # only whole windows, so the file never has a hole
            cursor = end + 1
    except Exception as e:
        err = e
    n = _extend("options_dvol", asset, src_dir, old, rows)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def options_snapshot(summaries, now_ms):
    """Deribit book summaries of every listed option of one currency -> one live read:
    put and call open interest (all expiries), their ratio, and for the expiry nearest 30 days
    the IV 10% below the forward (puts) minus the IV 10% above it (calls), in volatility points."""
    put_oi = call_oi = 0.0
    by_exp = {}
    for s in summaries:
        parts = str(s.get("instrument_name", "")).split("-")
        if len(parts) != 4 or parts[3] not in ("C", "P"):
            continue
        oi = float(s.get("open_interest") or 0.0)
        if parts[3] == "P":
            put_oi += oi
        else:
            call_oi += oi
        try:
            day, mon, year = int(parts[1][:-5]), _MONTHS[parts[1][-5:-2]], 2000 + int(parts[1][-2:])
            exp_ms = int(pd.Timestamp(year, mon, day, 8, tz="UTC").timestamp() * 1000)   # Deribit expires 08:00 UTC
            strike = float(parts[2].replace("d", "."))
            iv, fwd = float(s.get("mark_iv") or 0.0), float(s.get("underlying_price") or 0.0)
        except (KeyError, ValueError):
            continue
        if iv > 0 and fwd > 0:
            by_exp.setdefault(exp_ms, []).append((parts[3], strike, iv, fwd))
    out = {"put_oi": put_oi, "call_oi": call_oi, "pc_ratio": put_oi / call_oi if call_oi > 0 and put_oi > 0 else np.nan,
           "skew_pts": np.nan, "atm_iv": np.nan, "expiry_days": np.nan}
    lo, hi, want = SKEW_DAYS
    days = dict((e, (e - now_ms) / float(DAY_MS)) for e in by_exp)
    ok = [e for e in by_exp if lo <= days[e] <= hi]
    if ok:
        exp = min(ok, key=lambda e: abs(days[e] - want))
        fwd = float(np.median([q[3] for q in by_exp[exp]]))
        puts = sorted((k, iv) for kind, k, iv, _ in by_exp[exp] if kind == "P" and k <= fwd)
        calls = sorted((k, iv) for kind, k, iv, _ in by_exp[exp] if kind == "C" and k >= fwd)
        out["expiry_days"] = days[exp]
        if puts and calls:
            pk, pv = np.array(puts).T
            ck, cv = np.array(calls).T
            out["atm_iv"] = float((pv[-1] + cv[0]) / 2.0)
            kp, kc = fwd * (1.0 - SKEW_WING), fwd * (1.0 + SKEW_WING)
            if pk[0] <= kp and ck[-1] >= kc:                         # both wings are listed
                out["skew_pts"] = float(np.interp(kp, pk, pv) - np.interp(kc, ck, cv))
    return out


def _update_options_live(asset, src_dir, now_ms):
    old = load_source("options_live", asset, src_dir)
    reply = _get(DERIBIT + "get_book_summary_by_currency", {"currency": asset[:-4], "kind": "option"})
    stamp = int(time.time() * 1000)                                  # known from the moment it was read
    read = options_snapshot(reply["result"], stamp)
    if not np.isfinite(read["pc_ratio"]):
        raise RuntimeError("no option open interest in the reply")
    return _extend("options_live", asset, src_dir, old, [(stamp,) + tuple(read[c] for c in OPT_LIVE_COLS[1:])])


_UPDATERS = OrderedDict([("basis", _update_basis), ("lsratio", _update_lsratio), ("liq", _update_oi),
                         ("options", _update_dvol), ("options_live", _update_options_live)])


def update(log=print, src_dir=None, assets=None):
    """Fetch / extend every file under data/sources/. -> {"<source>_<ASSET>": rows on disk, or "failed: <reason>"}.
    A source that fails keeps its old file (plus whatever arrived before the failure). Never raises.
    The clock card has nothing to fetch and is not listed."""
    out = OrderedDict()
    for asset in assets or CFG["assets"]:
        for name, fn in _UPDATERS.items():
            key = "%s_%s" % (name, asset)
            try:
                out[key] = int(fn(asset, src_dir, int(time.time() * 1000)))
            except Exception as e:                                   # a failed source keeps its file and says why
                out[key] = "failed: %s" % (str(e) or type(e).__name__)[:160]
            try:
                log("sources.derivs %s: %s" % (key, out[key]))
            except Exception:
                pass
    return out


# ------------------------------------------------------------------ the no-lookahead join
def _grid(frame, step_ms):
    """A ts_ms-keyed frame on a gapless grid (a missing stamp is a NaN row), so that shift(k) and
    rolling(k) mean k steps of TIME. Off-grid stamps are dropped."""
    f = frame[frame["ts_ms"] % step_ms == 0].set_index("ts_ms")
    if not len(f):
        return f
    return f.reindex(np.arange(int(f.index[0]), int(f.index[-1]) + step_ms, step_ms, dtype="int64"))


def _asof(known_ms, values, close_ms, max_age_ms):
    """THE JOIN. values[j] became known at known_ms[j] (ascending). -> for each 15m close, the
    newest non-NaN value known at or before that close, or NaN when there is none or it is older
    than max_age_ms. Nothing known after a close can reach its row."""
    known_ms, values = np.asarray(known_ms, dtype="int64"), np.asarray(values, dtype=float)
    keep = np.isfinite(values)
    known_ms, values = known_ms[keep], values[keep]
    out = np.full(len(close_ms), np.nan)
    if not len(values):
        return out
    k = np.searchsorted(known_ms, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    ok = (k >= 0) & (close_ms - known_ms[kk] <= max_age_ms)
    out[ok] = values[kk[ok]]
    return out


def _clip(x, lim):
    return np.clip(x, -lim, lim)


def _ln(s):
    return np.log(s.where(s > 0))


# ------------------------------------------------------------------ the five cards
def _basis(out, close_ms, asset, src_dir, bars):
    g = _grid(load_source("basis", asset, src_dir), BAR_MS)
    if not len(g):
        return
    known = g.index.values + BAR_MS                                  # a premium bar is known at its close
    prem = g["close"]
    level = prem.rolling(4, min_periods=2).mean()                    # the last hour's average premium
    month = level.rolling(BASIS_Z_BARS, min_periods=BASIS_Z_MIN)
    mean, std = month.mean(), month.std()
    z = (level - mean) / std.where(std > 0)
    out["pb_level"] = _asof(known, _clip(level / PREMIUM_UNIT, 3.0), close_ms, BASIS_MAX_AGE)
    out["pb_z"] = _asof(known, _clip(z, 3.0), close_ms, BASIS_MAX_AGE)
    out["pb_chg_4h"] = _asof(known, _clip((level - level.shift(16)) / PREMIUM_UNIT, 3.0), close_ms, BASIS_MAX_AGE)
    out["pb_premium_pct"] = _asof(known, prem * 100.0, close_ms, BASIS_MAX_AGE)


def _lsratio(out, close_ms, asset, src_dir, bars):
    g = _grid(load_source("lsratio", asset, src_dir), BAR_MS)
    if not len(g):
        return
    snap = g.index.values + STATS_LAG_MS                             # account / position ratios: snapshots, published late
    for name in ("global", "top"):
        ln = _ln(g[name + "_ls"])                                    # 0 = as many long as short; + = more long
        out["ls_" + name] = _asof(snap, _clip(ln, 3.0), close_ms, LS_MAX_AGE)
        out["ls_%s_24h" % name] = _asof(snap, _clip((ln - ln.shift(96)) / LS_CHG_UNIT, 3.0), close_ms, LS_MAX_AGE)
        out["ls_%s_ratio" % name] = _asof(snap, g[name + "_ls"], close_ms, LS_MAX_AGE)
    done = g.index.values + BAR_MS + STATS_LAG_MS                    # taker volume covers a bar, and is published late
    ratio = g["taker_buy"].rolling(4, min_periods=4).sum() / g["taker_sell"].rolling(4, min_periods=4).sum()
    ln = _ln(ratio)                                                  # the last hour's taker buying against selling
    out["ls_taker"] = _asof(done, _clip(ln / TAKER_UNIT, 3.0), close_ms, LS_MAX_AGE)
    out["ls_taker_24h"] = _asof(done, _clip((ln - ln.shift(96)) / TAKER_UNIT, 3.0), close_ms, LS_MAX_AGE)
    out["ls_taker_ratio"] = _asof(done, ratio, close_ms, LS_MAX_AGE)


def _bar_returns(bars):
    """-> (close time in ms, 15m log return, that return in sigmas of the PRIOR 7 days)."""
    c = bars["close"].astype(float)
    r = np.log(c / c.shift(1))
    sig = r.rolling(LIQ_SIGMA_BARS, min_periods=LIQ_SIGMA_MIN).std().shift(1)
    return _data.to_ms(bars.index) + BAR_MS, r, r / sig.where(sig > 0)


def _liq(out, close_ms, asset, src_dir, bars):
    g = _grid(load_source("liq_oi", asset, src_dir), BAR_MS)
    if not len(g) or bars is None or not len(bars):
        return
    d_oi = _ln(g["oi"]).diff()                                       # at stamp t: the change over the bar that closed at t
    sig = d_oi.rolling(LIQ_SIGMA_BARS, min_periods=LIQ_SIGMA_MIN).std().shift(1)
    oi_z = d_oi / sig.where(sig > 0)
    bar_close, _r, r_z = _bar_returns(bars)
    move = pd.Series(r_z.values, index=bar_close).reindex(g.index)   # the price bar that closed at the same stamp
    drop_z, size_z = (-oi_z).clip(0.0, 6.0), move.abs().clip(0.0, 6.0)
    hit = (drop_z >= LIQ_OI_Z) & (size_z >= LIQ_MOVE_Z)
    # 1.0 = an event just at both thresholds; the sign is the bar's: down = longs closed out, up = shorts
    event = (np.sign(move) * np.sqrt(drop_z * size_z) / np.sqrt(LIQ_OI_Z * LIQ_MOVE_Z)).where(hit, 0.0)
    event = event.where(oi_z.notna() & move.notna())                 # no OI or no bar: no read, not "no event"
    known = g.index.values + STATS_LAG_MS                            # so row i reads the bar before it (i-1)
    newest = BAR_MS - 1                                              # only the newest bar that can be known, or nothing
    out["lq_bar"] = _asof(known, _clip(event, 3.0), close_ms, newest)
    out["lq_4h"] = _asof(known, _clip(event.rolling(16, min_periods=8).sum(), 3.0), close_ms, LIQ_SUM_MAX_AGE)
    out["lq_oi"] = _asof(known, g["oi"], close_ms, LIQ_SUM_MAX_AGE)
    out["lq_oi_chg_pct"] = _asof(known, d_oi * 100.0, close_ms, newest)
    out["lq_bar_sigma"] = _asof(known, move, close_ms, newest)


def _options(out, close_ms, asset, src_dir, bars):
    g = _grid(load_source("options_dvol", asset, src_dir), HOUR_MS)
    if len(g):
        known = g.index.values + HOUR_MS                             # an hourly DVOL bar is known when its hour ends
        v = g["close"]
        span = v.rolling(DVOL_RANGE_H, min_periods=DVOL_RANGE_MIN)
        lo, hi = span.min(), span.max()
        rank = 2.0 * (v - lo) / (hi - lo).where(hi > lo) - 1.0       # -1 = at the 90-day low, +1 = at the high
        out["op_dvol_rank"] = _asof(known, _clip(rank, 1.0), close_ms, DVOL_MAX_AGE)
        out["op_dvol_24h"] = _asof(known, _clip(np.log(v / v.shift(24)) / DVOL_CHG_UNIT, 3.0), close_ms, DVOL_MAX_AGE)
        out["op_dvol"] = _asof(known, v, close_ms, DVOL_MAX_AGE)
    if bars is not None and len(bars):
        c = bars["close"].astype(float)
        r = np.log(c / c.shift(1))
        rv = np.sqrt((r * r).rolling(RV_BARS, min_periods=RV_MIN).mean() * ANNUAL_BARS) * 100.0
        out["op_rv"] = _asof(_data.to_ms(bars.index) + BAR_MS, rv, close_ms, RV_MAX_AGE)   # the row's own bar, normally
        out["op_iv_rv"] = _clip((out["op_dvol"] - out["op_rv"]) / IV_RV_UNIT, 3.0)
    live = load_source("options_live", asset, src_dir)
    if len(live):
        known = live["ts_ms"].values                                 # stamped when it was read
        pcr = live["pc_ratio"].where(live["pc_ratio"] > 0)
        out["op_pcr"] = _asof(known, _clip(np.log(pcr) / PCR_UNIT, 3.0), close_ms, OPT_LIVE_MAX_AGE)
        out["op_skew"] = _asof(known, _clip(live["skew_pts"] / SKEW_UNIT, 3.0), close_ms, OPT_LIVE_MAX_AGE)
        out["op_pc_ratio"] = _asof(known, pcr, close_ms, OPT_LIVE_MAX_AGE)
        out["op_skew_pts"] = _asof(known, live["skew_pts"], close_ms, OPT_LIVE_MAX_AGE)


def _local(close_ms, tz):
    """-> (weekday Monday=0, minutes since local midnight) of each instant in a time zone (DST aware)."""
    t = pd.to_datetime(close_ms, unit="ms", utc=True).tz_convert(tz)
    return np.asarray(t.dayofweek), np.asarray(t.hour) * 60 + np.asarray(t.minute)


def _clock(out, close_ms, asset=None, src_dir=None, bars=None):
    """The clock is read at the bar's CLOSE: the moment the engine decides."""
    hour = (close_ms % DAY_MS) / float(HOUR_MS)
    dow = (close_ms // DAY_MS + 3) % 7                               # 1 Jan 1970 was a Thursday; Monday = 0
    out["ck_hour_sin"], out["ck_hour_cos"] = np.sin(2 * np.pi * hour / 24.0), np.cos(2 * np.pi * hour / 24.0)
    week = (dow + hour / 24.0) / 7.0
    out["ck_dow_sin"], out["ck_dow_cos"] = np.sin(2 * np.pi * week), np.cos(2 * np.pi * week)
    out["ck_weekend"] = (dow >= 5).astype(float)
    for name, (tz, start, end) in SESSIONS.items():
        wd, mins = _local(close_ms, tz)
        out["ck_" + name] = np.where((wd < 5) & (mins >= start) & (mins < end), 1.0, -1.0)
    tz, start, _end = SESSIONS["us"]
    wd, mins = _local(close_ms, tz)
    today = (wd < 5) & (mins <= start)
    days = np.where(wd == 4, 3, np.where(wd == 5, 2, 1))             # after Friday's open the next is Monday's
    hours = np.where(today, (start - mins) / 60.0, days * 24.0 - (mins - start) / 60.0)
    out["ck_us_open_hours"] = hours
    out["ck_us_open_in"] = np.clip(hours / US_OPEN_CAP_H, 0.0, 1.0)


_CARDS = OrderedDict([("basis", _basis), ("lsratio", _lsratio), ("liq", _liq), ("options", _options), ("clock", _clock)])


def features(index15, asset, src_dir=None, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature named in GROUPS as a float
    (0.0 = no read, never NaN) plus the readable RAW columns (NaN = no read).

    Reads only the files under data/sources/ (src_dir overrides) and the project's own 15m bars
    (bars overrides data.load(asset); used for the liquidation proxy and realised volatility).
    A card that cannot be built is left at "no read"; the reason is in .attrs["errors"]."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = _data.to_ms(index15) + BAR_MS
    out = pd.DataFrame(np.nan, index=index15, columns=FEATURES + RAW)
    errors = {}
    if bars is None:
        try:
            bars = _data.load(asset)
        except Exception as e:
            errors["bars"] = str(e)[:160]
    for name, fn in _CARDS.items():
        try:
            fn(out, close_ms, asset, src_dir, bars)
        except Exception as e:                                       # a broken file is "no read", not a crash
            errors[name] = "%s: %s" % (type(e).__name__, str(e)[:160])
            out[GROUPS[name][1]] = np.nan
    out[FEATURES] = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    coin, say = asset.replace("USDT", ""), OrderedDict()

    prem = _num(row, "pb_premium_pct")
    if prem is None:
        say[GROUPS["basis"][0]] = "No premium read for the %s perpetual at this close." % coin
    else:
        z, chg = _num(row, "pb_z") or 0.0, (_num(row, "pb_chg_4h") or 0.0) * PREMIUM_UNIT * 100.0
        norm = "has no 30-day norm to be set against yet" if z == 0.0 else (
            "is %.1f standard deviations %s its 30-day norm" % (abs(z), "above" if z > 0 else "below"))
        say[GROUPS["basis"][0]] = (
            "The %s perpetual closed the bar %.3f%% %s its spot index; the last hour's average premium %s and %s "
            "%.3f percentage points over 4 hours."
            % (coin, abs(prem), "above" if prem >= 0 else "below", norm, "rose" if chg >= 0 else "fell", abs(chg)))

    g, t, k = _num(row, "ls_global_ratio"), _num(row, "ls_top_ratio"), _num(row, "ls_taker_ratio")
    if g is None and t is None and k is None:
        say[GROUPS["lsratio"][0]] = "No long/short positioning read at this close."
    else:
        bits = []
        if g is not None:
            day = (np.exp((_num(row, "ls_global_24h") or 0.0) * LS_CHG_UNIT) - 1.0) * 100.0
            bits.append("%.0f%% of accounts are long (%.2f long per short, that ratio %+.0f%% over 24 hours)"
                        % (100.0 * g / (1.0 + g), g, day))
        if t is not None:
            bits.append("top traders hold %.2f long per short by position" % t)
        if k is not None:
            bits.append("takers bought %.2f for every 1 sold over the last hour" % k)
        say[GROUPS["lsratio"][0]] = "On Binance %s futures: %s." % (coin, "; ".join(bits))

    oi, d_oi, size = _num(row, "lq_oi"), _num(row, "lq_oi_chg_pct"), _num(row, "lq_bar_sigma")
    now, sum4 = _num(row, "lq_bar") or 0.0, _num(row, "lq_4h") or 0.0
    head = "A proxy, not a liquidation feed: "
    if oi is None and d_oi is None:
        say[GROUPS["liq"][0]] = head + "no open-interest read at this close, so nothing to infer."
    elif now != 0.0 and d_oi is not None and size is not None:
        say[GROUPS["liq"][0]] = head + (
            "in the last bar it can see, open interest fell %.2f%% during a %.1f-sigma %s bar, which is read as %s "
            "being closed out (%+.2f); "
            "the 4-hour sum is %+.2f." % (abs(d_oi), abs(size), "down" if size < 0 else "up",
                                           "longs" if size < 0 else "shorts", now, sum4))
    else:
        say[GROUPS["liq"][0]] = head + (
            "no sharp open-interest drop inside a large bar in the last bar it can see%s; the 4-hour sum is %+.2f."
            % ("" if d_oi is None else " (open interest %+.2f%%)" % d_oi, sum4))

    dvol, rv, pcr, skew = _num(row, "op_dvol"), _num(row, "op_rv"), _num(row, "op_pc_ratio"), _num(row, "op_skew_pts")
    if dvol is None and pcr is None:
        say[GROUPS["options"][0]] = "No options read for %s at this close." % coin
    else:
        bits = []
        if dvol is not None:
            rank = _num(row, "op_dvol_rank") or 0.0
            where = "" if rank == 0.0 else " %.0f%% of the way up its 90-day range," % (50.0 * (rank + 1.0))
            bits.append("Deribit's 30-day implied volatility (DVOL) is %.1f,%s %+.1f%% over 24 hours"
                        % (dvol, where, (np.exp((_num(row, "op_dvol_24h") or 0.0) * DVOL_CHG_UNIT) - 1.0) * 100.0))
            if rv is not None:
                bits.append("realised 30-day volatility is %.1f, so implied is %.1f points %s realised"
                            % (rv, abs(dvol - rv), "above" if dvol >= rv else "below"))
        if pcr is not None:
            bits.append("live read: %.2f puts of open interest per call" % pcr)
        if skew is not None:
            bits.append("puts 10%% below the forward are priced %.1f volatility points %s calls 10%% above it"
                        % (abs(skew), "over" if skew >= 0 else "under"))
        say[GROUPS["options"][0]] = "%s options: %s." % (coin, "; ".join(bits))

    try:
        at = (pd.Timestamp(row.name) + pd.Timedelta(milliseconds=BAR_MS)).strftime("%A %H:%M UTC")
    except Exception:
        at = "This close"
    opened = [n.capitalize() if n != "us" else "US" for n in SESSIONS if (_num(row, "ck_" + n) or 0.0) > 0]
    hours = _num(row, "ck_us_open_hours")
    say[GROUPS["clock"][0]] = "%s%s; %s; the US cash open is %s." % (
        at, " (weekend)" if (_num(row, "ck_weekend") or 0.0) > 0 else "",
        ("cash session open: " + ", ".join(opened)) if opened else "no cash session open in Asia, Europe or the US",
        "not read" if hours is None else "now" if hours == 0 else "%.1f hours away" % hours)
    return say
