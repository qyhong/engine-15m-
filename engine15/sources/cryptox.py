# -*- coding: utf-8 -*-
"""cryptox -- batch 3 (crypto): six reading-only cards for BTC and ETH from free, keyless sources.

Owner, 15 Nov 2026: batch 3 (crypto) approved as six reading-only decision cards. BUILT, NOT WIRED: this module is not
in sources.MODULES (tests/test_sources_cryptox.py::test_not_wired_yet); the parent session wires it as think15-v5.2.2
after review. No reading here is claimed to predict anything.

  optflow   Options flow (Deribit)          every Deribit option trade (history.deribit.com, no key), folded per UTC hour
                                            by sources/options_hist.py (the H40 aggregation), extended live to the last
                                            whole hour: put/call notional 7d, put/call 24h z, taker bearish 7d, approx
                                            25-delta skew and its 7d change, block bearish 7d
  kprem     Korea premium                   Upbit KRW-BTC / KRW-ETH 15m candles (api.upbit.com, public) against the
                                            project's Binance spot bars converted with USD/KRW (ECB reference rate via
                                            api.frankfurter.dev, keyless): premium, its z against 30 days, 24h change
  cmegap    CME gap (spot proxy)            no free, keyless, terms-compatible CME futures price history was found, so
                                            the card reads the project's own spot bars at CME's weekly session times:
                                            spot at Friday 16:00 Chicago (CME close) against spot at Sunday 17:00 (reopen);
                                            the open weekend move, and the nearest unfilled gap above / below
  dom       BTC dominance                   CoinMetrics community market caps (no key) of BTC, ETH and 12 long-listed
                                            coins plus DefiLlama total stablecoins: BTC share and stablecoin share of that
                                            tracked total, 7d / 30d changes (a proxy: the free tiers do not serve total
                                            market cap history; SOL, BNB and others are missing from the total)
  spotlead  Spot vs perp leadership         Binance USDT-M perpetual 15m klines (fapi.binance.com, public) against the
                                            project's own bars, which are Binance SPOT (data-api.binance.vision): spot
                                            share of combined volume and its z, spot minus perp taker-buy imbalance, and
                                            a lag-1 cross-correlation lead/lag over the last 24 h
  xfund     Cross-exchange funding and OI   Bybit and OKX public funding history and open interest against Binance
                                            funding (data.load_funding): the average, the highest-lowest spread, Binance
                                            minus the others, and the 24h open-interest change where history exists

Storage: CSV under data/sources/cx_<kind>[_<asset>].csv (Deribit: options_hourly_<asset>.csv), written to a .tmp file
and swapped in, ONLY EVER EXTENDED: a stored row is never changed. update() fetches (polite: a pause per host, back-off
on 429 / 5xx, a generic user agent, no keys, no accounts, nothing personal) and never raises; features() reads files.
The live loop calls update() every 15 minutes: with the default folders each source is asked at most every MIN_GAP_S and
each call is capped (LIVE_MAX_REQ) so a long gap is caught up over several calls instead of holding the loop.

THE ONE RULE (tests/test_sources_cryptox.py): row i may use only what was known at the close of 15m bar i. Every
stored row carries known_ms (publication lag included; for a row first fetched within its source's live window of its
nominal time, the later of the nominal time and the fetch time). Readings are computed on each source's own gapless grid
looking backward only, then joined as of known_ms (flows._asof) with a maximum age, after which they are "no read"
(feature 0.0, raw NaN). A 15m bar fetched from another venue is known one minute after its close (BAR_LAG_MS), so the
paired readings (Korea premium, spot vs perp) describe the bar before the decision's own bar, in the replay and live.

Docs: docs/SOURCES_cryptox.md.
"""
import json
import os
import time
import warnings
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from ..config import DATA_DIR
from . import options_hist as _oh
from .flows import _asof, _write

SRC_DIR = os.path.join(DATA_DIR, "sources")
STATE_NAME = "cryptox_state.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}   # generic; nothing personal
TIMEOUT_S = 40
PAUSE_S = {"api.upbit.com": 0.25, "api.frankfurter.dev": 1.0, "community-api.coinmetrics.io": 1.2,
           "stablecoins.llama.fi": 1.0, "fapi.binance.com": 0.5, "api.bybit.com": 0.3, "www.okx.com": 0.4}
RETRIES = 4                                             # on 429 / 5xx / network error: back off 2, 4, 8, 16 s
RATE_LIMIT_WAIT_S = 30.0

BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
ASSETS = ("BTCUSDT", "ETHUSDT")
COIN = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}

UPBIT = "https://api.upbit.com/v1/candles/minutes/15"
FX_URL = "https://api.frankfurter.dev/v1/%s..%s"
CM = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
STABLE_URL = "https://stablecoins.llama.fi/stablecoincharts/all"
FAPI = "https://fapi.binance.com/fapi/v1/klines"
BYBIT_FUND = "https://api.bybit.com/v5/market/funding/history"
BYBIT_OI = "https://api.bybit.com/v5/market/open-interest"
OKX_FUND = "https://www.okx.com/api/v5/public/funding-rate-history"
OKX_OI = "https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history"

# ---- where each fetch starts (a source that serves nothing that early simply answers empty windows)
UPBIT_START = "2019-09-01"
PERP_START = {"BTCUSDT": "2019-09-08", "ETHUSDT": "2019-11-27"}   # USDT-M perpetual listings
FX_START = "2019-06-01"
DOM_START = "2019-01-01"
BYBIT_START = "2020-03-01"
CME_START = {"BTCUSDT": "2017-12-15", "ETHUSDT": "2021-02-05"}     # CME Bitcoin / Ether futures launch weeks
DOM_ALTS = ["xrp", "ada", "doge", "ltc", "bch", "link", "xlm", "etc", "xmr", "zec", "dash", "algo"]
DOM_CM = ["btc", "eth"] + DOM_ALTS                      # all served by the community tier since 2019 or earlier

# ---- known-at lags and live windows
BAR_LAG_MS = 60000                                      # a 15m candle from another venue: its close + 1 minute
FX_KNOWN_LOCAL = "17:00"                                # ECB reference rate (published ~16:00 CET): 17:00 Frankfurt
DOM_LAG_MS = 6 * HOUR_MS                                # day D (CoinMetrics close, DefiLlama end of day): D+1 06:00
FUND_LAG_MS = 60000                                     # a funding rate settled at T: T + 1 minute
OI_LAG_MS = HOUR_MS + 5 * 60000                         # an hourly open-interest stamp T: T + 1 h 5 min (conservative)
LIVE_WINDOW = {"bar": DAY_MS, "fund": DAY_MS, "fx": DAY_MS, "daily": 7 * DAY_MS}   # ECB rates are never revised: 1 day

# ---- maximum ages
KP_MAX_AGE = HOUR_MS
FX_MAX_AGE = 5 * DAY_MS                                 # weekends and TARGET holidays
SL_MAX_AGE = HOUR_MS
DOM_MAX_AGE = 3 * DAY_MS
FUND_MAX_AGE = 10 * HOUR_MS                             # 8-hour settlements, plus slack for a late fetch
OI_MAX_AGE = 3 * HOUR_MS

# ---- the transforms
KP_Z_BARS, KP_Z_MIN, KP_CHG_BARS = 30 * 96, 10 * 96, 96
SL_WIN, SL_Z_BARS, SL_Z_MIN, SL_LEAD_BARS = 16, 30 * 96, 10 * 96, 96
CG_MIN_GAP = 0.002                                      # a weekend move under 0.2% of price is not kept as a gap
CG_ATR_DAYS, CG_NEAR_ATR = 14, 3.0                      # proximity: 1.0 at the level, 0.0 at 3 daily ATRs or more
FUND_BASE = 1e-4                                        # the usual 0.01% per 8 hours
# feature = clip(input / unit, -1, 1). Units set 15 Nov 2026 from each reading's own spread on 2020-2026 BTC history (about
# its 95th percentile of |input|, so roughly 5% of rows saturate); a scale only, never fitted to any outcome.
UNITS = OrderedDict([
    ("kp_prem", 0.05), ("kp_z30", 3.0), ("kp_chg24", 0.02),
    ("dm_btc_7d", 2.5), ("dm_btc_30d", 5.0), ("dm_stable_7d", 1.5), ("dm_stable_30d", 3.0),   # percentage points
    ("sl_share_z", 3.0), ("sl_taker_diff", 0.15), ("sl_lead", 0.03),
    ("xf_avg", 4e-4), ("xf_spread", 3e-4), ("xf_bin_gap", 4e-4), ("xf_oi_24h", 0.10),
])
OF_MAP = OrderedDict([("of_pcr_7d", "op_pcr_7d"), ("of_pcr_1d_z", "op_pcr_1d_z90"), ("of_taker_bear_7d", "op_taker_bear_7d"),
                      ("of_rr25", "op_rr25"), ("of_rr25_chg7", "op_rr25_chg7"), ("of_block_bear_7d", "op_block_bear_7d")])

GROUPS = OrderedDict([
    ("optflow", ("Options flow (Deribit)", list(OF_MAP))),
    ("kprem", ("Korea premium", ["kp_prem", "kp_z30", "kp_chg24"])),
    ("cmegap", ("CME gap (spot proxy)", ["cg_open", "cg_above", "cg_below"])),
    ("dom", ("BTC dominance", ["dm_btc_7d", "dm_btc_30d", "dm_stable_7d", "dm_stable_30d"])),
    ("spotlead", ("Spot vs perp leadership", ["sl_share_z", "sl_taker_diff", "sl_lead"])),
    ("xfund", ("Cross-exchange funding and OI", ["xf_avg", "xf_spread", "xf_bin_gap", "xf_oi_24h"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
APPLIES = dict((_v, ASSETS) for _v in GROUPS)          # crypto cards only (evidence.voice_applies)
RAW = ["of_put_usd_24h", "of_call_usd_24h", "of_trades_24h", "of_atm_iv", "of_rr25_vol",
       "kp_prem_pct", "kp_z30_raw", "kp_chg24_pct", "kp_usdkrw", "kp_upbit_krw",
       "cg_cme_close", "cg_open_atr", "cg_above_lvl", "cg_above_atr", "cg_above_age_d", "cg_below_lvl", "cg_below_atr",
       "cg_below_age_d", "cg_n_open",
       "dm_btc_share", "dm_eth_share", "dm_stable_share", "dm_btc_7d_pp", "dm_btc_30d_pp", "dm_stable_7d_pp",
       "dm_stable_30d_pp",
       "sl_spot_share", "sl_share_z_raw", "sl_taker_spot", "sl_taker_perp", "sl_lead_raw", "sl_basis_bp",
       "xf_binance", "xf_bybit", "xf_okx", "xf_avg_raw", "xf_spread_raw", "xf_bin_gap_raw", "xf_oi_bybit_24h",
       "xf_oi_okx_24h", "xf_n_venues"]

# The live step calls update() every 15 minutes; with the default folders each source is asked at most this often.
SOURCES = ("optflow", "upbit", "fx", "dom", "perp", "bybit", "okx")
GLOBAL_SOURCES = ("fx", "dom")
MIN_GAP_S = {"optflow": 3000, "upbit": 600, "fx": 6 * 3600, "dom": 6 * 3600, "perp": 600, "bybit": 1800, "okx": 1800}
LIVE_MAX_REQ = {"optflow_hours": 6, "upbit": 10, "perp": 4, "bybit": 12, "okx": 20}   # per call, default folders only

FILES = OrderedDict([
    ("upbit", ["ts_ms", "close", "vol_krw", "known_ms"]),
    ("perp", ["ts_ms", "open", "high", "low", "close", "volume", "taker_buy", "known_ms"]),
    ("fx", ["date", "usdkrw", "known_ms"]),
    ("caps", ["date"] + DOM_CM + ["known_ms"]),
    ("stables", ["date", "total_usd", "known_ms"]),
    ("bybit_fund", ["ts_ms", "rate", "known_ms"]),
    ("bybit_oi", ["ts_ms", "oi", "known_ms"]),
    ("okx_fund", ["ts_ms", "rate", "known_ms"]),
    ("okx_oi", ["ts_ms", "oi", "known_ms"]),
])
GLOBAL_FILES = ("fx", "caps", "stables")


# ------------------------------------------------------------------ storage
def path_for(kind, asset=None, src_dir=None):
    """-> data/sources/cx_<kind>_<asset>.csv (cx_<kind>.csv for the files shared by both coins)."""
    name = "cx_%s.csv" % kind if kind in GLOBAL_FILES else "cx_%s_%s.csv" % (kind, str(asset).lower())
    return os.path.join(src_dir or SRC_DIR, name)


def load_source(kind, asset=None, src_dir=None):
    """-> the stored rows of one file, sorted, unique; empty (with the right columns) when there is none."""
    cols, path = FILES[kind], path_for(kind, asset, src_dir)
    key = cols[0]
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(dict((c, pd.Series(dtype=object if c == "date" else "float64")) for c in cols))
    st = os.stat(path)
    ck = (os.path.abspath(path), st.st_mtime_ns, st.st_size)            # a file rewritten is read again
    if ck in _CACHE:
        return _CACHE[ck].copy()
    d = _read(path, cols, key)
    _CACHE[ck] = d
    while len(_CACHE) > 24:
        _CACHE.pop(next(iter(_CACHE)))
    return d.copy()


_CACHE = OrderedDict()


def _read(path, cols, key):
    d = pd.read_csv(path, dtype={"date": str} if key == "date" else None, float_precision="round_trip")
    for c in cols:
        if c not in d:
            d[c] = np.nan
    d = d[cols].dropna(subset=[key])
    if key == "ts_ms":
        d["ts_ms"] = d["ts_ms"].astype("int64")
    num = [c for c in cols if c not in ("date", "ts_ms")]
    d[num] = d[num].apply(pd.to_numeric, errors="coerce").astype(float)
    return d.drop_duplicates(key, keep="first").sort_values(key).reset_index(drop=True)


def _extend(kind, asset, src_dir, old, new):
    """Append rows whose key is not stored yet. A stored row is NEVER changed. -> rows on disk."""
    cols = FILES[kind]
    key = cols[0]
    if new is None or not len(new):
        return len(old)
    new = new[cols]
    if len(old):
        new = new[~new[key].isin(set(old[key]))]
    if not len(new):
        return len(old)
    both = pd.concat([old, new], ignore_index=True) if len(old) else new.copy()
    both = both.drop_duplicates(key, keep="first").sort_values(key)
    if key == "ts_ms":
        both["ts_ms"] = both["ts_ms"].astype("int64")
    _write(path_for(kind, asset, src_dir), both)
    return len(both)


def known_at(nominal_ms, seen_ms, window_ms):
    """Nominal publication time, or, for a row first fetched within window_ms of it (a live fetch), the later of the
    nominal time and the fetch time: a replay never knows more than a live run did."""
    nominal_ms = np.asarray(nominal_ms, dtype="int64")
    seen = np.broadcast_to(np.asarray(seen_ms, dtype="int64"), nominal_ms.shape)
    live = seen - nominal_ms < window_ms
    return np.where(live, np.maximum(nominal_ms, seen), nominal_ms).astype("int64")


def _ms(text):
    return int(pd.Timestamp(text, tz="UTC").value // 10 ** 6)


def _day_ms(dates):
    t = pd.to_datetime(pd.Series(list(dates), dtype=str), utc=True)
    return np.asarray(t.dt.as_unit("ms").astype("int64"), dtype="int64") if len(t) else np.zeros(0, dtype="int64")


def _day_str(ms):
    return pd.Timestamp(int(ms), unit="ms").strftime("%Y-%m-%d")


def _now():
    return int(time.time() * 1000)


# ------------------------------------------------------------------ network (update only)
_last = {}


def _get(url, params=None):
    """One polite GET (a pause per host, generic user agent, no key) with back-off on 429 / 418 / 5xx / network errors.
    -> requests.Response with status 200 or 404 (the caller decides); raises otherwise."""
    import requests
    host = url.split("/")[2]
    for attempt in range(RETRIES + 1):
        wait = PAUSE_S.get(host, 1.0) - (time.time() - _last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        err, r = None, None
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT_S)
        except Exception as e:
            err = e
        finally:
            _last[host] = time.time()
        if r is not None and r.status_code in (200, 404):
            return r
        if r is not None and r.status_code not in (418, 429) and r.status_code < 500:
            raise RuntimeError("HTTP %d from %s: %s" % (r.status_code, host, r.text[:80].replace("\n", " ")))
        if attempt == RETRIES:
            raise RuntimeError("gave up on %s: %s" % (host, err if err is not None else "HTTP %d" % r.status_code))
        limited = r is not None and r.status_code in (418, 429)
        time.sleep(max(2.0 * 2 ** attempt, RATE_LIMIT_WAIT_S if limited else 0.0))


def _json(url, params=None):
    r = _get(url, params)
    if r.status_code != 200:
        raise RuntimeError("HTTP %d from %s" % (r.status_code, url.split("/")[2]))
    return r.json()


def _update_upbit(asset, src_dir, now_ms, max_req=None):
    """Upbit 15m candles, paged forward from the bar after the file's last row. Closed bars only (ended 20 s ago)."""
    old = load_source("upbit", asset, src_dir)
    cur = int(old["ts_ms"].iloc[-1]) + BAR_MS if len(old) else _ms(UPBIT_START)
    stop = (now_ms - 20000 - BAR_MS) // BAR_MS * BAR_MS + BAR_MS        # bars [ts, ts+15m) with ts+15m <= now-20s
    n_req, rows, err, n = 0, [], None, len(old)
    try:
        while cur < stop and (max_req is None or n_req < max_req):
            to = min(cur + 200 * BAR_MS, stop)
            batch = _json(UPBIT, {"market": "KRW-" + COIN[asset], "count": 200,
                                  "to": pd.Timestamp(to, unit="ms").strftime("%Y-%m-%dT%H:%M:%SZ")})
            n_req += 1
            if not isinstance(batch, list):
                raise RuntimeError("unexpected reply %s" % str(batch)[:60])
            if batch:
                ts = np.asarray(pd.to_datetime([c["candle_date_time_utc"] for c in batch], utc=True)
                                .as_unit("ms").asi8, dtype="int64")
                for t, c in zip(ts, batch):
                    if cur <= t < to:
                        rows.append((int(t), float(c["trade_price"]), float(c.get("candle_acc_trade_price") or 0.0)))
            cur = to
            if len(rows) >= 20000:
                n, old, rows = _flush_bars("upbit", asset, src_dir, old, rows), load_source("upbit", asset, src_dir), []
    except Exception as e:
        err = e
    n = _flush_bars("upbit", asset, src_dir, old, rows) if rows else n
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _flush_bars(kind, asset, src_dir, old, rows):
    cols = FILES[kind][:-1]
    f = pd.DataFrame(rows, columns=cols).drop_duplicates("ts_ms").sort_values("ts_ms")
    f["known_ms"] = known_at(f["ts_ms"].values + BAR_MS + BAR_LAG_MS, _now(), LIVE_WINDOW["bar"])
    return _extend(kind, asset, src_dir, old, f)


def _update_perp(asset, src_dir, now_ms, max_req=None):
    """Binance USDT-M perpetual 15m klines, paged forward (1,500 a request). Closed bars only."""
    old = load_source("perp", asset, src_dir)
    cur = int(old["ts_ms"].iloc[-1]) + BAR_MS if len(old) else _ms(PERP_START[asset])
    stop = (now_ms - 20000 - BAR_MS) // BAR_MS * BAR_MS + BAR_MS
    n_req, rows, err, n = 0, [], None, len(old)
    try:
        while cur < stop and (max_req is None or n_req < max_req):
            batch = _json(FAPI, {"symbol": asset, "interval": "15m", "startTime": cur, "endTime": stop - 1, "limit": 1500})
            n_req += 1
            if not isinstance(batch, list):
                raise RuntimeError("unexpected reply %s" % str(batch)[:60])
            got = [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9]))
                   for k in batch if cur <= int(k[0]) < stop]
            rows += got
            cur = got[-1][0] + BAR_MS if got else cur + 1500 * BAR_MS
            if len(rows) >= 50000:
                n, old, rows = _flush_bars("perp", asset, src_dir, old, rows), load_source("perp", asset, src_dir), []
    except Exception as e:
        err = e
    n = _flush_bars("perp", asset, src_dir, old, rows) if rows else n
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _fx_known(dates):
    """ECB reference rate of date D: known at D 17:00 Frankfurt time (published about 16:00 CET)."""
    t = pd.to_datetime(pd.Series(list(dates), dtype=str) + " " + FX_KNOWN_LOCAL).dt.tz_localize("Europe/Berlin")
    return np.asarray(t.dt.tz_convert("UTC").dt.as_unit("ms").astype("int64"), dtype="int64") if len(t) \
        else np.zeros(0, dtype="int64")


def _update_fx(src_dir, now_ms):
    """USD/KRW from the ECB reference rates (EUR crosses) served by api.frankfurter.dev, one calendar year a request."""
    old = load_source("fx", None, src_dir)
    last = str(old["date"].iloc[-1]) if len(old) else None
    start = (pd.Timestamp(last) + pd.Timedelta(days=1)) if last else pd.Timestamp(FX_START)
    today = pd.Timestamp(now_ms, unit="ms").normalize()
    rows, err = [], None
    try:
        while start <= today:
            end = min(pd.Timestamp(year=start.year, month=12, day=31), today)
            j = _json(FX_URL % (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")), {"base": "USD", "symbols": "KRW"})
            for day, v in sorted((j.get("rates") or {}).items()):
                try:
                    rows.append((str(day)[:10], float(v["KRW"])))
                except (KeyError, TypeError, ValueError):
                    continue
            start = end + pd.Timedelta(days=1)
    except Exception as e:
        err = e
    n = len(old)
    if rows:
        f = pd.DataFrame(rows, columns=["date", "usdkrw"]).drop_duplicates("date")
        if last:
            f = f[f["date"] > last]
        nominal = _fx_known(f["date"])
        seen = _now()
        f = f[nominal <= seen]                                           # never store a rate before its publication time
        f["known_ms"] = known_at(_fx_known(f["date"]), seen, LIVE_WINDOW["fx"])
        n = _extend("fx", None, src_dir, old, f)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _update_caps(src_dir, now_ms):
    """CoinMetrics community CapMrktCurUSD, daily, for DOM_CM. A day is stored once BTC, ETH and every alt have it, or
    once it is 3 days old (a missing alt then stays NaN; readings compare like with like). Stored in date order."""
    old = load_source("caps", None, src_dir)
    last = str(old["date"].iloc[-1]) if len(old) else None
    start = (pd.Timestamp(last) + pd.Timedelta(days=1)).strftime("%Y-%m-%d") if last else DOM_START
    today = _day_str(now_ms)
    params = {"assets": ",".join(DOM_CM), "metrics": "CapMrktCurUSD", "frequency": "1d", "page_size": 10000,
              "start_time": start, "paging_from": "start"}
    got, url, err = {}, CM, None
    try:
        while url:
            j = _json(url, params)
            if "error" in j:
                raise RuntimeError(str(j["error"])[:90])
            for d in j.get("data", []):
                day = str(d.get("time", ""))[:10]
                try:
                    got.setdefault(day, {})[d["asset"]] = float(d["CapMrktCurUSD"])
                except (KeyError, TypeError, ValueError):
                    continue
            url, params = j.get("next_page_url"), None
    except Exception as e:
        err = e
    rows = []
    old_cut = _day_str(now_ms - 3 * DAY_MS)
    for day in sorted(got):
        if len(day) != 10 or day >= today or (last and day <= last):
            continue
        v = got[day]
        complete = all(a in v for a in DOM_CM)
        if not complete and not (day <= old_cut and "btc" in v and "eth" in v):
            break                                                         # keep the stored days contiguous
        rows.append([day] + [v.get(a, np.nan) for a in DOM_CM])
    n = len(old)
    if rows:
        f = pd.DataFrame(rows, columns=["date"] + DOM_CM)
        f["known_ms"] = known_at(_day_ms(f["date"]) + DAY_MS + DOM_LAG_MS, _now(), LIVE_WINDOW["daily"])
        n = _extend("caps", None, src_dir, old, f)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _update_stables(src_dir, now_ms):
    """DefiLlama total stablecoin supply (every peg, in USD), complete UTC days only."""
    old = load_source("stables", None, src_dir)
    last = str(old["date"].iloc[-1]) if len(old) else None
    today = _day_str(now_ms)
    rows = []
    for e in _json(STABLE_URL):
        usd = e.get("totalCirculatingUSD") or {}
        try:
            day = _day_str(int(e["date"]) * 1000)
            tot = float(sum(float(x or 0.0) for x in usd.values()))
        except (KeyError, TypeError, ValueError):
            continue
        if day < today and day >= DOM_START and (not last or day > last) and tot > 0:
            rows.append((day, tot))
    if not rows:
        return len(old)
    f = pd.DataFrame(rows, columns=["date", "total_usd"]).drop_duplicates("date")
    f["known_ms"] = known_at(_day_ms(f["date"]) + DAY_MS + DOM_LAG_MS, _now(), LIVE_WINDOW["daily"])
    return _extend("stables", None, src_dir, old, f)


def _store_fund(kind, asset, src_dir, old, rows, lag_ms, step_ok_ms):
    if not rows:
        return len(old)
    f = pd.DataFrame(rows, columns=FILES[kind][:2]).drop_duplicates("ts_ms").sort_values("ts_ms")
    seen = _now()
    f = f[f["ts_ms"] + step_ok_ms <= seen]                               # a stamp is stored once it has settled
    if len(old):
        f = f[f["ts_ms"] > int(old["ts_ms"].iloc[-1])]
    f["known_ms"] = known_at(f["ts_ms"].values + lag_ms, seen, LIVE_WINDOW["fund"])
    return _extend(kind, asset, src_dir, old, f)


def _update_bybit(asset, src_dir, now_ms, max_req=None):
    """Bybit linear perpetual funding history (50-day windows) and hourly open interest (200-hour windows), forward."""
    out, errs = {}, []
    for kind, url, win, extra in (("bybit_fund", BYBIT_FUND, 50 * DAY_MS, {}),
                                  ("bybit_oi", BYBIT_OI, 199 * HOUR_MS, {"intervalTime": "1h"})):
        old = load_source(kind, asset, src_dir)
        cur = int(old["ts_ms"].iloc[-1]) + 1 if len(old) else _ms(BYBIT_START)
        rows, n_req = [], 0
        try:
            while cur < now_ms and (max_req is None or n_req < max_req):
                end = min(cur + win, now_ms)
                p = dict(extra, category="linear", symbol=asset, startTime=cur, endTime=end, limit=200)
                j = _json(url, p)
                n_req += 1
                if str(j.get("retCode")) != "0":
                    raise RuntimeError("retCode %s: %s" % (j.get("retCode"), str(j.get("retMsg"))[:60]))
                for x in (j.get("result") or {}).get("list") or []:
                    if kind == "bybit_fund":
                        rows.append((int(x["fundingRateTimestamp"]), float(x["fundingRate"])))
                    else:
                        rows.append((int(x["timestamp"]), float(x["openInterest"])))
                cur = end + 1
        except Exception as e:
            errs.append("%s: %s" % (kind, str(e)[:80]))
        if kind == "bybit_fund":
            out[kind] = _store_fund(kind, asset, src_dir, old, rows, FUND_LAG_MS, 0)
        else:
            out[kind] = _store_fund(kind, asset, src_dir, old, [r for r in rows if r[0] % HOUR_MS == 0], OI_LAG_MS, HOUR_MS)
    if errs:
        raise RuntimeError("%s (files have %s rows)" % ("; ".join(errs)[:120], out))
    return out


def _update_okx(asset, src_dir, now_ms, max_req=None):
    """OKX USDT swap funding history (the API serves about three months) and hourly open interest (about 60 days),
    paged backward from now until the file's last stamp."""
    inst = "%s-USDT-SWAP" % COIN[asset]
    out, errs = {}, []
    for kind in ("okx_fund", "okx_oi"):
        old = load_source(kind, asset, src_dir)
        last = int(old["ts_ms"].iloc[-1]) if len(old) else 0
        rows, cursor, n_req = [], None, 0
        try:
            while max_req is None or n_req < max_req:
                if kind == "okx_fund":
                    p = {"instId": inst, "limit": 100}
                    if cursor:
                        p["after"] = cursor
                    j = _json(OKX_FUND, p)
                else:
                    p = {"instId": inst, "period": "1H", "limit": 100}
                    if cursor:
                        p["end"] = cursor
                    j = _json(OKX_OI, p)
                n_req += 1
                if str(j.get("code")) != "0":
                    raise RuntimeError("code %s: %s" % (j.get("code"), str(j.get("msg"))[:60]))
                d = j.get("data") or []
                if not d:
                    break
                if kind == "okx_fund":
                    page = [(int(x["fundingTime"]), float(x["fundingRate"])) for x in d]
                else:
                    page = [(int(x[0]), float(x[2])) for x in d]
                rows += page
                oldest = min(t for t, _v in page)
                if oldest <= last or len(d) < 100:
                    break
                cursor = str(oldest) if kind == "okx_fund" else str(oldest - 1)
        except Exception as e:
            errs.append("%s: %s" % (kind, str(e)[:80]))
        if kind == "okx_fund":
            out[kind] = _store_fund(kind, asset, src_dir, old, rows, FUND_LAG_MS, 0)
        else:
            out[kind] = _store_fund(kind, asset, src_dir, old, [r for r in rows if r[0] % HOUR_MS == 0], OI_LAG_MS, HOUR_MS)
    if errs:
        raise RuntimeError("%s (files have %s rows)" % ("; ".join(errs)[:120], out))
    return out


def update(log=print, src_dir=None, assets=None, sources=None, force=False):
    """Fetch / extend every file. -> {"<source>_<ASSET>" or "<source>": rows on disk, or "failed: <reason>"}. Never
    raises; a source that fails keeps its old file plus whatever arrived before the failure. sources: a subset of
    SOURCES. With the default folder (the live loop) a source asked less than MIN_GAP_S ago is skipped unless force,
    and each call is capped by LIVE_MAX_REQ."""
    out = OrderedDict()
    names = [n for n in (sources or SOURCES) if n in SOURCES]
    gate = src_dir is None and not force
    caps = LIVE_MAX_REQ if gate else {}
    state_path = os.path.join(SRC_DIR, STATE_NAME)
    state = {}
    if gate:
        try:
            with open(state_path, encoding="utf-8") as fh:
                state = json.load(fh)
        except Exception:
            state = {}
        now_s = time.time()
        names = [n for n in names if now_s - float(state.get(n, 0.0)) >= MIN_GAP_S.get(n, 3600)]
        if not names:
            return out
    coins = [a for a in (assets or ASSETS) if a in COIN]

    def say(key):
        try:
            log("sources.cryptox %s: %s" % (key, out[key]))
        except Exception:
            pass

    for name in names:
        if name in GLOBAL_SOURCES:
            jobs = [("fx", lambda: _update_fx(src_dir, _now()))] if name == "fx" else \
                [("caps", lambda: _update_caps(src_dir, _now())), ("stables", lambda: _update_stables(src_dir, _now()))]
            for key, job in jobs:
                try:
                    out[key] = int(job())
                except Exception as e:
                    out[key] = "failed: %s" % (str(e) or type(e).__name__)[:160]
                say(key)
            continue
        for asset in coins:
            key = "%s_%s" % (name, asset)
            try:
                if name == "optflow":
                    r = _oh.update(log=lambda *_: None, src_dir=src_dir, assets=[asset], live=True,
                                   max_hours=caps.get("optflow_hours"))
                    v = r.get("hourly_%s" % asset)
                    out[key] = v if isinstance(v, int) else str(v)
                elif name == "upbit":
                    out[key] = int(_update_upbit(asset, src_dir, _now(), caps.get("upbit")))
                elif name == "perp":
                    out[key] = int(_update_perp(asset, src_dir, _now(), caps.get("perp")))
                else:
                    r = (_update_bybit if name == "bybit" else _update_okx)(asset, src_dir, _now(), caps.get(name))
                    for k, v in r.items():
                        out["%s_%s" % (k, asset)] = int(v)
                        say("%s_%s" % (k, asset))
                    continue
            except Exception as e:
                out[key] = "failed: %s" % (str(e) or type(e).__name__)[:160]
            say(key)
    if gate:
        for name in names:
            state[name] = time.time()
        try:
            os.makedirs(SRC_DIR, exist_ok=True)
            with open(state_path + ".tmp", "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=1, sort_keys=True)
            os.replace(state_path + ".tmp", state_path)
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ readings (files only)
def _bars_of(asset, bars):
    if isinstance(bars, dict):
        bars = bars.get(asset)
    if bars is None:
        bars = _data.load(asset)
    b = bars[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)
    if not b.index.is_monotonic_increasing or b.index.has_duplicates:
        b = b[~b.index.duplicated(keep="last")].sort_index()
    return b


def _grid(frame, step):
    """A ts_ms-keyed frame -> gapless grid (index = stamps), missing stamps NaN (their known_ms NaN: never used)."""
    g = frame.set_index("ts_ms")
    if not len(g):
        return g
    return g.reindex(np.arange(int(g.index[0]), int(g.index[-1]) + step, step, dtype="int64"))


def _z(s, n, n_min):
    w = s.rolling(n, min_periods=n_min)
    sd = w.std()
    return (s - w.mean()) / sd.where(sd > 0)


def _optflow(close_ms, asset, src_dir, out):
    x = _oh.inputs(close_ms, asset, src_dir)
    for f, src in OF_MAP.items():
        out[f] = np.clip(x[src].values / (3.0 * _oh.UNITS[src]), -1.0, 1.0)   # the H40 units, +-3 mapped to +-1
    out["of_put_usd_24h"] = x["op_put_usd_24h"].values
    out["of_call_usd_24h"] = x["op_call_usd_24h"].values
    out["of_trades_24h"] = x["op_trades_24h"].values
    out["of_atm_iv"] = x["op_atm_iv"].values
    out["of_rr25_vol"] = x["op_rr25"].values
    return x.attrs.get("errors") or {}


def _spot_ms(b):
    return pd.DataFrame({"close": b["close"].values, "volume": b["volume"].values, "taker_buy": b["taker_buy"].values,
                         "high": b["high"].values, "low": b["low"].values}, index=_data.to_ms(b.index))


def _kprem(close_ms, asset, src_dir, spot, out):
    up = load_source("upbit", asset, src_dir)
    if not len(up):
        return
    fx = load_source("fx", None, src_dir)
    g = _grid(up[["ts_ms", "close", "known_ms"]], BAR_MS)
    sc = spot["close"].reindex(g.index)
    if len(fx):
        usdkrw = _asof(fx["known_ms"].values, fx["usdkrw"].values, g.index.values + BAR_MS, FX_MAX_AGE)
    else:
        usdkrw = np.full(len(g), np.nan)
    prem = pd.Series(g["close"].values / (usdkrw * sc.values) - 1.0, index=g.index)
    prem = prem.replace([np.inf, -np.inf], np.nan)
    z = _z(prem, KP_Z_BARS, KP_Z_MIN)
    chg = prem - prem.shift(KP_CHG_BARS)
    k = g["known_ms"].values
    p = _asof(k, prem.values, close_ms, KP_MAX_AGE)
    zz = _asof(k, z.values, close_ms, KP_MAX_AGE)
    cc = _asof(k, chg.values, close_ms, KP_MAX_AGE)
    out["kp_prem"] = p / UNITS["kp_prem"]
    out["kp_z30"] = zz / UNITS["kp_z30"]
    out["kp_chg24"] = cc / UNITS["kp_chg24"]
    out["kp_prem_pct"] = 100.0 * p
    out["kp_z30_raw"] = zz
    out["kp_chg24_pct"] = 100.0 * cc
    out["kp_usdkrw"] = _asof(k, usdkrw, close_ms, KP_MAX_AGE)
    out["kp_upbit_krw"] = _asof(k, g["close"].values, close_ms, KP_MAX_AGE)


def cme_sessions(first_ms, last_ms):
    """-> list of (close_ms, reopen_ms): CME crypto futures' weekly close (Friday 16:00 Chicago; Thursday when Friday is
    Good Friday) and reopen (Sunday 17:00 Chicago), DST-aware. Mid-week holiday halts are not modelled."""
    from dateutil.easter import easter
    out = []
    lo = pd.Timestamp(int(first_ms), unit="ms") - pd.Timedelta(days=7)
    hi = pd.Timestamp(int(last_ms), unit="ms") + pd.Timedelta(days=7)
    for fri in pd.date_range(lo.normalize(), hi.normalize(), freq="W-FRI"):
        close_day = fri
        if fri.date() == easter(fri.year) - pd.Timedelta(days=2).to_pytimedelta():
            close_day = fri - pd.Timedelta(days=1)
        c = pd.Timestamp(close_day.strftime("%Y-%m-%d") + " 16:00").tz_localize("America/Chicago")
        o = pd.Timestamp((fri + pd.Timedelta(days=2)).strftime("%Y-%m-%d") + " 17:00").tz_localize("America/Chicago")
        out.append((int(c.tz_convert("UTC").value // 10 ** 6), int(o.tz_convert("UTC").value // 10 ** 6)))
    return out


def _cmegap(b, asset):
    """On the bar grid of b (spot): the open weekend move and the nearest unfilled gaps. -> frame on b's rows."""
    n = len(b)
    cl = _data.to_ms(b.index) + BAR_MS                                  # each row's close
    close, high, low = b["close"].values, b["high"].values, b["low"].values
    d = _data.resample(b, "1D")
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
    atr = _data.htf_on_15(b, "1D", tr.rolling(CG_ATR_DAYS, min_periods=CG_ATR_DAYS).mean()).values
    atr = np.where(atr > 0, atr, np.nan)
    r = dict((c, np.full(n, np.nan)) for c in ("cg_cme_close", "cg_open_atr", "cg_above_lvl", "cg_above_age_d",
                                               "cg_below_lvl", "cg_below_age_d"))
    above_lvl, above_t = np.full(n, np.inf), np.zeros(n, dtype="int64")
    below_lvl, below_t = np.full(n, -np.inf), np.zeros(n, dtype="int64")
    n_open = np.zeros(n)
    start = _ms(CME_START[asset])
    pos = dict(zip(cl.tolist(), range(n)))
    last_close = np.full(n, np.nan)
    for c_ms, o_ms in cme_sessions(cl[0], cl[-1]):
        if c_ms < start or c_ms not in pos:
            continue
        ic = pos[c_ms]
        F = close[ic]
        j_end = int(np.searchsorted(cl, o_ms, side="left"))                # first row closing at/after the reopen
        last_close[ic:] = F                                                 # the latest CME close (proxy) from here on
        if ic + 1 < j_end:                                                  # rows while CME is shut
            sl = slice(ic + 1, j_end)
            r["cg_open_atr"][sl] = (close[sl] - F) / atr[sl]
        if o_ms not in pos:
            continue
        i0 = pos[o_ms]
        O = close[i0]
        if not (np.isfinite(F) and np.isfinite(O)) or abs(O - F) < CG_MIN_GAP * F:
            continue
        after = slice(i0 + 1, n)
        hit = (low[after] <= F) if O > F else (high[after] >= F)
        j = i0 + 1 + int(np.argmax(hit)) if hit.any() else n               # the row that fills it (its close: filled)
        sl = slice(i0, j)
        n_open[sl] += 1
        if O > F:                                                            # gap up: an unfilled level below
            better = F > below_lvl[sl]
            below_lvl[sl] = np.where(better, F, below_lvl[sl])
            below_t[sl] = np.where(better, o_ms, below_t[sl])
        else:
            better = F < above_lvl[sl]
            above_lvl[sl] = np.where(better, F, above_lvl[sl])
            above_t[sl] = np.where(better, o_ms, above_t[sl])
    r["cg_cme_close"] = last_close
    ha, hb = np.isfinite(above_lvl), np.isfinite(below_lvl)
    r["cg_above_lvl"] = np.where(ha, above_lvl, np.nan)
    r["cg_below_lvl"] = np.where(hb, below_lvl, np.nan)
    r["cg_above_atr"] = np.where(ha, (above_lvl - close) / atr, np.nan)
    r["cg_below_atr"] = np.where(hb, (close - below_lvl) / atr, np.nan)
    r["cg_above_age_d"] = np.where(ha, (cl - above_t) / float(DAY_MS), np.nan)
    r["cg_below_age_d"] = np.where(hb, (cl - below_t) / float(DAY_MS), np.nan)
    r["cg_n_open"] = np.where(cl >= start, n_open, np.nan)
    f = pd.DataFrame(r, index=b.index)
    f["cg_open"] = f["cg_open_atr"]
    f["cg_above"] = (1.0 - f["cg_above_atr"] / CG_NEAR_ATR).clip(0.0, 1.0)
    f["cg_below"] = -(1.0 - f["cg_below_atr"] / CG_NEAR_ATR).clip(0.0, 1.0)
    return f


def _dom(close_ms, src_dir, out):
    caps, st = load_source("caps", None, src_dir), load_source("stables", None, src_dir)
    if not len(caps) or not len(st):
        return
    d = caps.merge(st, on="date", how="inner", suffixes=("", "_st"))
    if not len(d):
        return
    d["known"] = np.maximum(d["known_ms"].values, d["known_ms_st"].values)
    d.index = _day_ms(d["date"])
    d = d.reindex(np.arange(int(d.index[0]), int(d.index[-1]) + DAY_MS, DAY_MS, dtype="int64"))
    btc, eth, stb = d["btc"], d["eth"], d["total_usd"]
    A = d[DOM_ALTS]
    P = A.notna()
    total = btc + eth + stb + A.where(P, 0.0).sum(axis=1)
    share = lambda x, t: 100.0 * x / t.where(t > 0)                     # noqa: E731
    k = d["known"].values
    out["dm_btc_share"] = _asof(k, share(btc, total).values, close_ms, DOM_MAX_AGE)
    out["dm_eth_share"] = _asof(k, share(eth, total).values, close_ms, DOM_MAX_AGE)
    out["dm_stable_share"] = _asof(k, share(stb, total).values, close_ms, DOM_MAX_AGE)
    for lag in (7, 30):
        S = P & P.shift(lag, fill_value=False)                          # alts present on both days: like with like
        now_t = btc + eth + stb + A.where(S, 0.0).sum(axis=1)
        then_t = btc.shift(lag) + eth.shift(lag) + stb.shift(lag) + A.shift(lag).where(S, 0.0).sum(axis=1)
        db = share(btc, now_t) - share(btc.shift(lag), then_t)
        ds = share(stb, now_t) - share(stb.shift(lag), then_t)
        b_, s_ = _asof(k, db.values, close_ms, DOM_MAX_AGE), _asof(k, ds.values, close_ms, DOM_MAX_AGE)
        out["dm_btc_%dd_pp" % lag], out["dm_stable_%dd_pp" % lag] = b_, s_
        out["dm_btc_%dd" % lag] = b_ / UNITS["dm_btc_%dd" % lag]
        out["dm_stable_%dd" % lag] = s_ / UNITS["dm_stable_%dd" % lag]


def _spotlead(close_ms, asset, src_dir, spot, out):
    p = load_source("perp", asset, src_dir)
    if not len(p) or not len(spot):
        return
    lo, hi = max(int(p["ts_ms"].iloc[0]), int(spot.index[0])), int(p["ts_ms"].iloc[-1])
    if hi < lo:
        return
    idx = np.arange(lo, hi + BAR_MS, BAR_MS, dtype="int64")
    g = p.set_index("ts_ms").reindex(idx)
    s = spot.reindex(idx)
    n = SL_WIN
    sv, st = s["volume"].rolling(n, min_periods=n).sum(), s["taker_buy"].rolling(n, min_periods=n).sum()
    pv, pt = g["volume"].rolling(n, min_periods=n).sum(), g["taker_buy"].rolling(n, min_periods=n).sum()
    tot = sv + pv
    share = sv / tot.where(tot > 0)
    z = _z(share, SL_Z_BARS, SL_Z_MIN)
    imb_s = 2.0 * st / sv.where(sv > 0) - 1.0
    imb_p = 2.0 * pt / pv.where(pv > 0) - 1.0
    rs = np.log(s["close"].where(s["close"] > 0)).diff()
    rp = np.log(g["close"].where(g["close"] > 0)).diff()
    m = SL_LEAD_BARS
    lead = rs.shift(1).rolling(m, min_periods=m).corr(rp) - rp.shift(1).rolling(m, min_periods=m).corr(rs)
    basis = 1e4 * (g["close"] / s["close"] - 1.0)
    k = np.where(s["close"].notna().values, g["known_ms"].values, np.nan)
    k = np.maximum(k, idx + BAR_MS)
    J = lambda v: _asof(k, np.asarray(v, dtype=float), close_ms, SL_MAX_AGE)   # noqa: E731
    out["sl_spot_share"] = 100.0 * J(share.values)
    zz, dd, ll = J(z.values), J((imb_s - imb_p).values), J(lead.values)
    out["sl_share_z_raw"], out["sl_lead_raw"] = zz, ll
    out["sl_taker_spot"], out["sl_taker_perp"] = J(imb_s.values), J(imb_p.values)
    out["sl_basis_bp"] = J(basis.values)
    out["sl_share_z"] = zz / UNITS["sl_share_z"]
    out["sl_taker_diff"] = dd / UNITS["sl_taker_diff"]
    out["sl_lead"] = ll / UNITS["sl_lead"]


def _per8h(ts, rate):
    """Funding rates -> 8-hour equivalents (an exchange that settles every 4 h or 1 h is scaled up)."""
    ts, rate = np.asarray(ts, dtype="int64"), np.asarray(rate, dtype=float)
    gap = np.diff(ts, prepend=ts[0] - 8 * HOUR_MS) if len(ts) else ts
    gap = np.clip(np.round(gap / float(HOUR_MS)) * HOUR_MS, HOUR_MS, 8 * HOUR_MS)   # settlement stamps carry ms jitter
    return rate * (8.0 * HOUR_MS / gap)


def _binance_funding(asset, src_dir):
    """The project's Binance funding file (data.load_funding); with an explicit folder, <folder>/binance_funding_<asset>.csv
    (ts_ms, rate), so tests never read the real file."""
    if src_dir is None:
        s = _data.load_funding(asset)
        return _data.to_ms(s.index) if len(s) else np.zeros(0, dtype="int64"), s.values.astype(float)
    path = os.path.join(src_dir, "binance_funding_%s.csv" % asset.lower())
    if not os.path.exists(path):
        return np.zeros(0, dtype="int64"), np.zeros(0)
    f = pd.read_csv(path).sort_values("ts_ms")
    return f["ts_ms"].values.astype("int64"), f["rate"].values.astype(float)


def _xfund(close_ms, asset, src_dir, out):
    rates = OrderedDict()
    bt, br = _binance_funding(asset, src_dir)
    if len(bt):
        rates["binance"] = _asof(bt + FUND_LAG_MS, _per8h(bt, br), close_ms, FUND_MAX_AGE)
    for name, kind in (("bybit", "bybit_fund"), ("okx", "okx_fund")):
        f = load_source(kind, asset, src_dir)
        if len(f):
            rates[name] = _asof(f["known_ms"].values, _per8h(f["ts_ms"].values, f["rate"].values), close_ms, FUND_MAX_AGE)
    nan = np.full(len(close_ms), np.nan)
    for name in ("binance", "bybit", "okx"):
        out["xf_" + name] = rates.get(name, nan)
    M = np.vstack([out["xf_binance"].values, out["xf_bybit"].values, out["xf_okx"].values])
    cnt = np.isfinite(M).sum(axis=0)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        avg = np.where(cnt >= 1, np.nanmean(np.where(np.isfinite(M), M, np.nan), axis=0), np.nan)
        spread = np.where(cnt >= 2, np.nanmax(M, axis=0) - np.nanmin(M, axis=0), np.nan)
        others = np.nanmean(M[1:], axis=0)
    gap = np.where(np.isfinite(M[0]) & (np.isfinite(M[1:]).sum(axis=0) >= 1), M[0] - others, np.nan)
    out["xf_avg_raw"], out["xf_spread_raw"], out["xf_bin_gap_raw"] = avg, spread, gap
    out["xf_n_venues"] = np.where(cnt > 0, cnt, np.nan)
    out["xf_avg"] = (avg - FUND_BASE) / UNITS["xf_avg"]
    out["xf_spread"] = spread / UNITS["xf_spread"]
    out["xf_bin_gap"] = gap / UNITS["xf_bin_gap"]
    ois = []
    for name, kind in (("bybit", "bybit_oi"), ("okx", "okx_oi")):
        f = load_source(kind, asset, src_dir)
        v = nan
        if len(f):
            g = _grid(f, HOUR_MS)
            lo = np.log(g["oi"].where(g["oi"] > 0))
            v = _asof(g["known_ms"].values, (lo - lo.shift(24)).values, close_ms, OI_MAX_AGE)
        out["xf_oi_%s_24h" % name] = v
        ois.append(v)
    O = np.vstack(ois)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        oi = np.where(np.isfinite(O).any(axis=0), np.nanmean(O, axis=0), np.nan)
    out["xf_oi_24h"] = oi / UNITS["xf_oi_24h"]


def features(index15, asset, src_dir=None, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature in GROUPS clipped to [-1, 1] (0.0 = no read, never
    NaN) plus the readable RAW columns (NaN = no read). Reads only files (and the project's own spot bars: `bars`, a
    frame or {asset: frame}, else data.load)."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = _data.to_ms(index15) + BAR_MS
    out = pd.DataFrame(np.nan, index=np.arange(len(index15)), columns=FEATURES + RAW)
    errors = {}
    if asset not in COIN:
        out.index = index15
        out[FEATURES] = 0.0
        out.attrs["errors"] = errors
        return out
    try:
        e = _optflow(close_ms, asset, src_dir, out)
        if e:
            errors["optflow"] = str(e)[:160]
    except Exception as ex:
        errors["optflow"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
    spot, b = None, None
    try:
        b = _bars_of(asset, bars)
        spot = _spot_ms(b)
    except Exception as ex:
        errors["bars"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
    for name, job in (("kprem", lambda: _kprem(close_ms, asset, src_dir, spot, out)),
                      ("dom", lambda: _dom(close_ms, src_dir, out)),
                      ("spotlead", lambda: _spotlead(close_ms, asset, src_dir, spot, out)),
                      ("xfund", lambda: _xfund(close_ms, asset, src_dir, out))):
        if spot is None and name in ("kprem", "spotlead"):
            continue
        try:
            job()
        except Exception as ex:
            errors[name] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
    if b is not None and len(b):
        try:
            cg = _cmegap(b, asset)
            cg = cg.reindex(index15)
            for c in cg.columns:
                out[c] = cg[c].values
        except Exception as ex:
            errors["cmegap"] = "%s: %s" % (type(ex).__name__, str(ex)[:160])
    out.index = index15
    out = out.replace([np.inf, -np.inf], np.nan)
    out[FEATURES] = out[FEATURES].astype(float).clip(-1.0, 1.0).fillna(0.0)
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
    coin, say = COIN.get(asset, asset.replace("USDT", "")), OrderedDict()
    T = dict((v, GROUPS[v][0]) for v in GROUPS)
    p, c = _num(row, "of_put_usd_24h"), _num(row, "of_call_usd_24h")
    if p is None or c is None:
        say[T["optflow"]] = "No Deribit option-trade read for %s at this close." % coin
    else:
        bits = ["$%.0fm of puts and $%.0fm of calls traded over 24 hours" % (p / 1e6, c / 1e6)]
        rr = _num(row, "of_rr25_vol")
        if rr is not None:
            bits.append("25-delta put trade IV %+.1f vol points against calls (3 days)" % rr)
        tb = _num(row, "of_taker_bear_7d")
        if tb is not None and tb != 0.0:
            bits.append("7-day taker flow leans %s" % ("to puts" if tb > 0 else "to calls"))
        say[T["optflow"]] = "Deribit %s options: %s." % (coin, "; ".join(bits))
    kp = _num(row, "kp_prem_pct")
    if kp is None:
        say[T["kprem"]] = "No Korea premium read for %s at this close." % coin
    else:
        z, ch = _num(row, "kp_z30_raw"), _num(row, "kp_chg24_pct")
        bits = ["%s on Upbit trades %+.2f%% against Binance at the ECB dollar-won rate" % (coin, kp)]
        if ch is not None:
            bits.append("%+.2f points over 24 hours" % ch)
        if z is not None:
            bits.append("%+.1f standard deviations from its 30-day mean" % z)
        say[T["kprem"]] = "Korea premium (previous 15m bar): %s." % "; ".join(bits)
    bits = []
    op = _num(row, "cg_open_atr")
    if op is not None:
        bits.append("CME is shut and %s is %+.2f daily ranges from the CME close" % (coin, op))
    for side, word in (("above", "above"), ("below", "below")):
        lv, dist, age = _num(row, "cg_%s_lvl" % side), _num(row, "cg_%s_atr" % side), _num(row, "cg_%s_age_d" % side)
        if lv is not None and dist is not None:
            bits.append("nearest unfilled gap %s at %.0f (%.1f daily ranges away, %.0f days old)" % (word, lv, dist, age or 0.0))
    if not bits:
        n_open = _num(row, "cg_n_open")
        say[T["cmegap"]] = ("No open CME weekend gap for %s at this close." % coin if n_open is not None
                            else "No CME gap read for %s at this close." % coin)
    else:
        say[T["cmegap"]] = "CME gap, spot proxy: %s." % "; ".join(bits)
    bs, ss = _num(row, "dm_btc_share"), _num(row, "dm_stable_share")
    if bs is None:
        say[T["dom"]] = "No market-share read at this close."
    else:
        b7, b30, s7 = _num(row, "dm_btc_7d_pp"), _num(row, "dm_btc_30d_pp"), _num(row, "dm_stable_7d_pp")
        bits = ["BTC is %.1f%% of the tracked crypto market cap" % bs]
        if b7 is not None and b30 is not None:
            bits[0] += " (%+.1f points in 7 days, %+.1f in 30)" % (b7, b30)
        if ss is not None:
            bits.append("stablecoins %.1f%%%s" % (ss, "" if s7 is None else " (%+.2f points in 7 days)" % s7))
        say[T["dom"]] = "Market share, last complete day: %s." % "; ".join(bits)
    sh = _num(row, "sl_spot_share")
    if sh is None:
        say[T["spotlead"]] = "No spot against perpetual read for %s at this close." % coin
    else:
        bits = ["spot was %.0f%% of Binance %s spot plus perpetual volume over 4 hours" % (sh, coin)]
        ts_, tp = _num(row, "sl_taker_spot"), _num(row, "sl_taker_perp")
        if ts_ is not None and tp is not None:
            bits.append("taker-buy imbalance %+.2f on spot and %+.2f on the perpetual" % (ts_, tp))
        ld = _num(row, "sl_lead_raw")
        if ld is not None and abs(ld) < 0.01:
            bits.append("over 24 hours neither moved first by lag-one correlation (%+.3f)" % ld)
        elif ld is not None:
            bits.append("over 24 hours %s moved first by lag-one correlation (%+.3f)" % ("spot" if ld > 0 else "the perpetual", ld))
        say[T["spotlead"]] = "Spot against perpetual (previous 15m bar): %s." % "; ".join(bits)
    av = _num(row, "xf_avg_raw")
    if av is None:
        say[T["xfund"]] = "No cross-exchange funding read for %s at this close." % coin
    else:
        names = [("Binance", "xf_binance"), ("Bybit", "xf_bybit"), ("OKX", "xf_okx")]
        parts = ["%s %+.4f%%" % (nm, 100.0 * _num(row, k)) for nm, k in names if _num(row, k) is not None]
        bits = ["average %+.4f%% per 8 hours (%s)" % (100.0 * av, ", ".join(parts))]
        sp = _num(row, "xf_spread_raw")
        if sp is not None:
            bits.append("highest minus lowest %.4f points" % (100.0 * sp))
        oi = [(nm, _num(row, "xf_oi_%s_24h" % nm.lower())) for nm in ("Bybit", "OKX")]
        oi = ["%s %+.1f%%" % (nm, 100.0 * (np.exp(v) - 1.0)) for nm, v in oi if v is not None]
        if oi:
            bits.append("open interest over 24 hours %s" % ", ".join(oi))
        say[T["xfund"]] = "Funding, last settled: %s." % "; ".join(bits)
    return say
