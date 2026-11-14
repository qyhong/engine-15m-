# -*- coding: utf-8 -*-
"""flows -- derivatives positioning and on-chain flow sources with deep, free history (BTC and ETH).

  metrics    Binance USDT-M positioning       public archive data.binance.vision, daily `metrics` files: open interest,
                                              top-trader and account long/short, taker ratio; 5-minute rows, kept at 15m;
                                              BTCUSDT from 1 Sep 2020, ETHUSDT from 1 Dec 2021
  bitfinex   Bitfinex margin positions        api-pub.bitfinex.com stats1 pos.size, hourly, from 22 Feb 2021
  cme        CME futures positioning (CFTC)   weekly Commitments of Traders, traders in financial futures, futures only:
                                              CME Bitcoin (133741) from Apr 2018, CME Ether (146021) from Apr 2021
  onchain    On-chain activity and flows      CoinMetrics community API (no key), daily: MVRV, active addresses,
                                              exchange in/outflows and exchange supply, hash rate, issuance, tx count

WIRED INTO THE LIVE ENGINE from think15-v5.1.1 (13 Nov 2026, owner's "Yes"): listed in sources.MODULES, four crypto
cards (BTC and ETH only, APPLIES), fetched by the live step at most every MIN_GAP_S per source. Still not an RL input
(that needs a registered round). Also the data source of research/flows_study.py (hypothesis H39).

Everything is kept as CSV under data/sources/ (written to a .tmp file and swapped in, only ever extended: a row once
stored is never changed, later fetches only add rows). The Binance archive zips are kept under
data/raw/binance_metrics/<SYMBOL>/ and are only read as data. `update` fetches; `features` and `inputs` read files only,
never the network.

THE ONE RULE (tests/test_sources_flows.py): row i may use only what was known at the close of 15m bar i. Every stored
row carries an explicit KNOWN-AT time (column known_ms), publication lag included:

    archive metrics row of UTC day D        known at D+1 00:00 + METRICS_LAG_MS (12 h; files appear 06:30-08:20 UTC)
    CoinMetrics value of UTC day D          known at D+1 00:00 + ONCHAIN_LAG_MS (6 h; flash values computed 01:15-03:20)
    Bitfinex hourly snapshot at stamp T     known at T + BFX_LAG_MS (1 h 5 min; conservative, the snapshot is AT T)
    CFTC report with positions as of Tue    known at its release (cot.release_ms: Friday 15:30 New York, with overrides)

and, for a row first fetched within LIVE_WINDOW_MS of that nominal time (a live update rather than the backfill), the
later of the nominal time and the moment update() first saw it, so the replay never knows more than a live run did.

Every reading is computed on its source's own gapless grid (days, hours, reports), looking backward only, then handed to
the 15m row whose close is at or after its known-at time (and not staler than the source's MAX_AGE: "no read", 0.0).

Docs: docs/SOURCES_flows.md. No reading here is claimed to predict anything.
"""
import io
import json
import os
import time
import zipfile
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from ..config import CFG, DATA_DIR

SRC_DIR = os.path.join(DATA_DIR, "sources")            # override per call with src_dir=...
RAW_DIR = os.path.join(DATA_DIR, "raw", "binance_metrics")   # override per call with raw_dir=...
ARCHIVE = "https://data.binance.vision/data/futures/um/daily/metrics/%s/%s-metrics-%s.zip"
BFX = "https://api-pub.bitfinex.com/v2/stats1/pos.size:1h:t%sUSD:%s/hist"
CFTC = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"     # traders in financial futures, futures only
CM = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}   # generic; nothing personal
TIMEOUT_S = 40
PAUSE_S = {"data.binance.vision": 0.30, "api-pub.bitfinex.com": 3.0, "publicreporting.cftc.gov": 1.0,
           "community-api.coinmetrics.io": 1.2}   # CoinMetrics community: 10 requests / 6 s per IP; Bitfinex: rate-limits early
RETRIES = 4                                             # on 429 / 5xx / network error: back off 2, 4, 8, 16 s
RATE_LIMIT_WAIT_S = 65.0                                # ... but at least 65 s after a 429 / 418 (Bitfinex blocks for a minute)

BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000

# ---- where each history starts (what the providers serve; checked 13 Nov 2026)
METRICS_START = {"BTCUSDT": "2020-09-01", "ETHUSDT": "2021-12-01"}
BFX_START_MS = 1612137600000                            # 2021-02-01: before the first hourly row Bitfinex serves
CME_CODE = {"BTCUSDT": ("133741", "CME Bitcoin futures"), "ETHUSDT": ("146021", "CME Ether futures")}
CME_START = "2017-12-01"
CM_ASSET = {"BTCUSDT": "btc", "ETHUSDT": "eth"}
CM_START = "2015-01-01"
CM_METRICS = ["CapMVRVCur", "AdrActCnt", "FlowInExNtv", "FlowOutExNtv", "SplyExNtv", "HashRate", "IssTotUSD",
              "TxCnt", "CapMrktCurUSD"]

# ---- known-at lags (see the module docstring; measured 11-13 Nov 2026, then rounded UP)
METRICS_LAG_MS = 12 * HOUR_MS
ONCHAIN_LAG_MS = 6 * HOUR_MS
BFX_LAG_MS = HOUR_MS + 5 * 60000
LIVE_WINDOW_MS = 7 * DAY_MS                             # first seen within a week of its nominal time = a live fetch

# ---- how long a reading may stand in for a missing newer one before it is "no read"
METRICS_MAX_AGE = 3 * DAY_MS                            # a daily value; one missed archive day is tolerated
ONCHAIN_MAX_AGE = 3 * DAY_MS
BFX_MAX_AGE = 6 * HOUR_MS
CME_MAX_AGE = 15 * DAY_MS                               # a weekly report may stand in for one missed week

# ---- the transforms (declared in research/HYPOTHESES.md H39 before any history was fetched) and their read units
OI_DAYS = 7                                             # X1: 7-day log change of open interest (coins)
LS_Z_DAYS, LS_Z_MIN = 90, 30                            # X2, X3: z-score against the trailing 90 days (30 to speak)
BFX_HOURS = 14 * 24                                     # X4: 14-day change of ln(margin longs / shorts)
CME_Z_REPORTS, CME_Z_MIN = 52, 26                       # X5: z against the trailing 52 weekly reports (26 to speak)
MVRV_Z_DAYS, MVRV_Z_MIN = 365, 180                      # X6: z of ln(MVRV) against 365 days (180 to speak)
FLOW_DAYS = 7                                           # X7: 7-day net exchange flow / exchange supply
ADDR_SHORT, ADDR_LONG, ADDR_LONG_MIN = 30, 365, 180     # X8: ln(30-day mean / 365-day mean) of active addresses
HASH_FAST, HASH_SLOW = 30, 60                           # X9: ln(SMA30 / SMA60) of the hash rate ("hash ribbon")
UNITS = OrderedDict([                                   # feature = clip(input / unit, +-3)
    ("fl_oi_7d", 0.10),                                 # a 10% change in open interest over 7 days = 1.0
    ("fl_ls_global_z", 1.0), ("fl_ls_topgap_z", 1.0),   # already in standard deviations
    ("fl_bfx_14d", 0.25),                               # a 0.25 move in ln(longs/shorts) over 14 days = 1.0
    ("fl_cme_lev_z", 1.0),
    ("fl_mvrv_z", 1.0),
    ("fl_netflow_7d", 0.005),                           # net inflow of 0.5% of exchange supply over 7 days = 1.0
    ("fl_addr", 0.20),                                  # active addresses 20% above their yearly mean = 1.0
    ("fl_hash_ribbon", 0.05),                           # 30-day hash rate 5% above the 60-day = 1.0
])

GROUPS = OrderedDict([
    ("metrics", ("Binance positioning (archive)", ["fl_oi_7d", "fl_ls_global_z", "fl_ls_topgap_z"])),
    ("bitfinex", ("Bitfinex margin positions", ["fl_bfx_14d"])),
    ("cme", ("CME futures positioning (CFTC)", ["fl_cme_lev_z"])),
    ("onchain", ("On-chain activity and flows", ["fl_mvrv_z", "fl_netflow_7d", "fl_addr", "fl_hash_ribbon"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
APPLIES = dict((_v, ("BTCUSDT", "ETHUSDT")) for _v in GROUPS)   # crypto cards only (evidence.voice_applies)
# The live step calls update() every 15 minutes; with the default folders each source is asked at most this often
# (the archive and CoinMetrics publish once a day, Bitfinex hourly, the CFTC weekly). Explicit folders always fetch.
MIN_GAP_S = {"metrics": 3600, "bitfinex": 3000, "cme": 6 * 3600, "onchain": 2 * 3600}
STATE_NAME = "flows_state.json"                         # last attempt per source, under SRC_DIR
RAW = ["fl_oi", "fl_global_ls", "fl_top_pos_ls", "fl_bfx_long", "fl_bfx_short", "fl_cme_lev_net_pct",
       "fl_cme_am_net_pct", "fl_mvrv", "fl_exch_supply", "fl_addr_act", "fl_hashrate_btc"]
INPUTS = list(UNITS)                                    # the unclipped transforms, as H39 tests them

METRICS_COLS = ["ts_ms", "oi", "oi_value", "top_acct_ls", "top_pos_ls", "global_ls", "taker_ls", "known_ms"]
BFX_COLS = ["ts_ms", "long", "short", "known_ms"]
CME_COLS = ["date", "oi", "lev_long", "lev_short", "am_long", "am_short", "dealer_long", "dealer_short", "known_ms"]
CM_COLS = ["date"] + CM_METRICS + ["known_ms"]
FILES = OrderedDict([("metrics", METRICS_COLS), ("bitfinex", BFX_COLS), ("cme", CME_COLS), ("onchain", CM_COLS)])
_ARCHIVE_FIELDS = OrderedDict([("oi", "sum_open_interest"), ("oi_value", "sum_open_interest_value"),
                               ("top_acct_ls", "count_toptrader_long_short_ratio"),
                               ("top_pos_ls", "sum_toptrader_long_short_ratio"),
                               ("global_ls", "count_long_short_ratio"),
                               ("taker_ls", "sum_taker_long_short_vol_ratio")])


# ------------------------------------------------------------------ storage
def path_for(kind, asset, src_dir=None):
    """kind: one of FILES. -> data/sources/flows_<kind>_<asset>.csv"""
    return os.path.join(src_dir or SRC_DIR, "flows_%s_%s.csv" % (kind, asset.lower()))


def raw_dir_for(asset, raw_dir=None):
    return os.path.join(raw_dir or RAW_DIR, asset.upper())


def load_source(kind, asset, src_dir=None):
    """-> the stored rows of one file, sorted by time, unique; empty (with the right columns) when there is none."""
    cols, path = FILES[kind], path_for(kind, asset, src_dir)
    key = cols[0]
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(dict((c, pd.Series(dtype=object if c == "date" else "float64")) for c in cols))
    d = pd.read_csv(path, dtype={"date": str} if key == "date" else None)
    for c in cols:
        if c not in d:
            d[c] = np.nan
    d = d[cols].dropna(subset=[key])
    if key == "ts_ms":
        d["ts_ms"] = d["ts_ms"].astype("int64")
    d["known_ms"] = pd.to_numeric(d["known_ms"], errors="coerce")
    num = [c for c in cols if c not in ("date", "ts_ms", "known_ms")]
    d[num] = d[num].apply(pd.to_numeric, errors="coerce").astype(float)
    return d.drop_duplicates(key, keep="first").sort_values(key).reset_index(drop=True)


def _write(path, frame):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    for attempt in range(5):                                       # Windows: a reader may hold the file a moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.3 * (attempt + 1))


def _extend(kind, asset, src_dir, old, new):
    """Append rows whose key is not stored yet. A stored row is NEVER changed. -> rows on disk."""
    key = FILES[kind][0]
    if new is None or not len(new):
        return len(old)
    new = new[FILES[kind]]
    new = new[~new[key].isin(set(old[key]))] if len(old) else new
    if not len(new):
        return len(old)
    both = pd.concat([old, new], ignore_index=True) if len(old) else new.copy()
    both = both.drop_duplicates(key, keep="first").sort_values(key)
    if key == "ts_ms":
        both["ts_ms"] = both["ts_ms"].astype("int64")
    _write(path_for(kind, asset, src_dir), both)
    return len(both)


def known_at(nominal_ms, first_seen_ms):
    """The known-at rule for a fetched row: its nominal publication time, or, when it was first fetched within
    LIVE_WINDOW_MS of that time (a live fetch), the later of the two."""
    nominal_ms = np.asarray(nominal_ms, dtype="int64")
    seen = np.broadcast_to(np.asarray(first_seen_ms, dtype="int64"), nominal_ms.shape)
    live = seen - nominal_ms < LIVE_WINDOW_MS
    return np.where(live, np.maximum(nominal_ms, seen), nominal_ms).astype("int64")


def _day_ms(dates):
    """'YYYY-MM-DD' strings -> epoch ms of 00:00 UTC of each date."""
    t = pd.to_datetime(pd.Series(list(dates), dtype=str), utc=True)
    return np.asarray(t.dt.as_unit("ms").astype("int64"), dtype="int64") if len(t) else np.zeros(0, dtype="int64")


# ------------------------------------------------------------------ network (update only)
_last = {}


def _get(url, params=None):
    """One polite GET (a pause per host, generic user agent, no key) with back-off on 429 / 5xx / network errors.
    -> requests.Response with status 200, or 404 returned as is (the caller decides); raises otherwise."""
    import requests
    host = url.split("/")[2]
    for attempt in range(RETRIES + 1):
        wait = PAUSE_S.get(host, 1.0) - (time.time() - _last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        err = None
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT_S)
        except Exception as e:                                         # network error: back off and retry
            r, err = None, e
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


def parse_metrics_zip(blob):
    """The bytes of one archive zip -> frame on the 15-minute grid (stamps at :00, :15, :30, :45):
    open interest and the ratios as the snapshot AT the stamp, the taker ratio as the geometric mean of the three
    5-minute ratios stamped in [stamp, stamp + 15 min). The zip is only read as data (CSV text)."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    bad = z.testzip()
    if bad is not None:
        raise RuntimeError("corrupt member %s" % bad)
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if len(names) != 1:
        raise RuntimeError("expected one CSV in the zip, found %s" % z.namelist()[:3])
    d = pd.read_csv(io.BytesIO(z.read(names[0])))
    miss = [c for c in ["create_time"] + list(_ARCHIVE_FIELDS.values()) if c not in d]
    if miss:
        raise RuntimeError("missing columns %s" % miss)
    t = pd.to_datetime(d["create_time"], utc=True)
    ts = np.asarray(t.dt.as_unit("ms").astype("int64"), dtype="int64")
    d = pd.DataFrame(dict([("ts_ms", ts)] + [(k, pd.to_numeric(d[v], errors="coerce")) for k, v in _ARCHIVE_FIELDS.items()]))
    d = d.drop_duplicates("ts_ms", keep="last").sort_values("ts_ms")
    d = d[d["ts_ms"] % 300000 == 0]                                    # the 5-minute grid only
    slot = d["ts_ms"] // BAR_MS * BAR_MS
    lt = np.log(d["taker_ls"].where(d["taker_ls"] > 0))
    taker = np.exp(lt.groupby(slot).mean())
    snap = d[d["ts_ms"] % BAR_MS == 0].set_index("ts_ms")
    out = snap.drop(columns="taker_ls").join(taker.rename("taker_ls"), how="left")
    out.index.name = "ts_ms"
    return out.reset_index()


def _archive_days(asset, now_ms):
    """Every UTC day whose archive file could exist by now (the day has ended), oldest first."""
    last = (now_ms // DAY_MS - 1) * DAY_MS                             # yesterday 00:00 UTC
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(METRICS_START[asset], pd.Timestamp(last, unit="ms"), freq="D")]


def _update_metrics(asset, src_dir, raw_dir, now_ms, log=None):
    """Download the archive zips not on disk yet (into data/raw/binance_metrics/<SYMBOL>/), then add the days after
    the CSV's last day. A day the archive does not have (404) is skipped; if it is one of the last 3 days it is simply
    not published yet and will be asked for again next time."""
    folder = raw_dir_for(asset, raw_dir)
    os.makedirs(folder, exist_ok=True)
    days = _archive_days(asset, now_ms)
    have = set(f[len(asset) + 9:len(asset) + 19] for f in os.listdir(folder) if f.endswith(".zip"))
    missing_old = set()
    gone_path = os.path.join(folder, "_not_in_archive.txt")             # days the archive answered 404 for, kept
    if os.path.exists(gone_path):
        with open(gone_path) as fh:
            missing_old = set(x.strip() for x in fh if x.strip())
    recent = set(days[-3:])
    todo = [d for d in days if d not in have and (d not in missing_old or d in recent)]
    err, got, gone = None, 0, set()
    for i, day in enumerate(todo):
        try:
            r = _get(ARCHIVE % (asset, asset, day))
        except Exception as e:
            err = e
            break
        if r.status_code == 404:
            if day not in recent:
                gone.add(day)
            continue
        blob = r.content
        try:
            parse_metrics_zip(blob)                                    # refuse a broken file before keeping it
        except Exception as e:
            err = RuntimeError("%s: %s" % (day, e))
            break
        path = os.path.join(folder, "%s-metrics-%s.zip" % (asset, day))
        with open(path + ".tmp", "wb") as fh:
            fh.write(blob)
        os.replace(path + ".tmp", path)
        got += 1
        if log is not None and got % 200 == 0:
            try:
                log("sources.flows metrics_%s: %d of %d files" % (asset, got, len(todo)))
            except Exception:
                pass
    if gone:
        with open(gone_path, "w") as fh:
            fh.write("\n".join(sorted(missing_old | gone)) + "\n")
    old = load_source("metrics", asset, src_dir)
    last_day = pd.Timestamp(int(old["ts_ms"].iloc[-1]), unit="ms").strftime("%Y-%m-%d") if len(old) else ""
    frames = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".zip"):
            continue
        day = f[len(asset) + 9:len(asset) + 19]
        if day <= last_day:
            continue
        with open(os.path.join(folder, f), "rb") as fh:
            rows = parse_metrics_zip(fh.read())
        start = int(_day_ms([day])[0])
        rows = rows[(rows["ts_ms"] >= start) & (rows["ts_ms"] < start + DAY_MS)]   # a file holds its own day only
        fetched = int(os.path.getmtime(os.path.join(folder, f)) * 1000)       # when the zip was downloaded
        rows["known_ms"] = known_at(np.full(len(rows), start + DAY_MS + METRICS_LAG_MS), fetched)
        frames.append(rows)
    n = _extend("metrics", asset, src_dir, old, pd.concat(frames, ignore_index=True) if frames else None)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _update_bitfinex(asset, src_dir, now_ms):
    old = load_source("bitfinex", asset, src_dir)
    coin = asset[:-4]
    start = int(old["ts_ms"].iloc[-1]) + HOUR_MS if len(old) else BFX_START_MS
    sides, err = {}, None
    for side in ("long", "short"):
        cursor, rows = start, []
        try:
            while cursor <= now_ms:
                batch = _get(BFX % (coin, side), {"start": cursor, "end": now_ms, "limit": 10000, "sort": 1}).json()
                if not isinstance(batch, list):
                    raise RuntimeError("unexpected reply %s" % str(batch)[:60])
                batch = [(int(a), float(b)) for a, b in batch if int(a) % HOUR_MS == 0]
                if not batch:
                    break
                rows += batch
                cursor = batch[-1][0] + HOUR_MS
                if len(batch) < 5000:
                    break
        except Exception as e:
            err = e
        sides[side] = pd.Series(dict(rows), dtype=float)
    both = pd.DataFrame(sides).dropna()                                  # only hours both sides have
    both = both[both.index + HOUR_MS <= now_ms]                         # keep the stored file free of a half-seen hour
    if len(both):
        seen = int(time.time() * 1000)
        both = both.rename_axis("ts_ms").reset_index()
        both["ts_ms"] = both["ts_ms"].astype("int64")
        both["known_ms"] = known_at(both["ts_ms"].values + BFX_LAG_MS, seen)
    n = _extend("bitfinex", asset, src_dir, old, both if len(both) else None)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def _update_cme(asset, src_dir, now_ms):
    from . import cot
    old = load_source("cme", asset, src_dir)
    code = CME_CODE[asset][0]
    since = str(old["date"].iloc[-1]) if len(old) else None
    where = "cftc_contract_market_code='%s' AND report_date_as_yyyy_mm_dd %s '%sT00:00:00'" % (
        code, ">" if since else ">=", since or CME_START)
    sel = ("report_date_as_yyyy_mm_dd,open_interest_all,lev_money_positions_long,lev_money_positions_short,"
           "asset_mgr_positions_long,asset_mgr_positions_short,dealer_positions_long_all,dealer_positions_short_all")
    rows = _get(CFTC, {"$where": where, "$select": sel, "$order": "report_date_as_yyyy_mm_dd", "$limit": 5000}).json()
    if not isinstance(rows, list):
        raise RuntimeError("unexpected reply %s" % str(rows)[:60])
    seen = int(time.time() * 1000)
    out = []
    for r in rows:
        day = str(r.get("report_date_as_yyyy_mm_dd", ""))[:10]
        if len(day) != 10:
            continue
        rel = int(cot.release_ms(day))
        if rel > seen:                                                  # not released yet by the rule: never store early
            continue

        def f(k):
            try:
                return float(r.get(k))
            except (TypeError, ValueError):
                return np.nan
        out.append((day, f("open_interest_all"), f("lev_money_positions_long"), f("lev_money_positions_short"),
                    f("asset_mgr_positions_long"), f("asset_mgr_positions_short"), f("dealer_positions_long_all"),
                    f("dealer_positions_short_all"), int(known_at([rel], seen)[0])))
    new = pd.DataFrame(out, columns=CME_COLS) if out else None
    return _extend("cme", asset, src_dir, old, new)


def _update_onchain(asset, src_dir, now_ms):
    old = load_source("onchain", asset, src_dir)
    start = (pd.Timestamp(str(old["date"].iloc[-1])) + pd.Timedelta(days=1)).strftime("%Y-%m-%d") if len(old) else CM_START
    today = pd.Timestamp(now_ms // DAY_MS * DAY_MS, unit="ms").strftime("%Y-%m-%d")
    params = {"assets": CM_ASSET[asset], "metrics": ",".join(CM_METRICS), "frequency": "1d", "page_size": 10000,
              "start_time": start, "paging_from": "start"}
    rows, url, err = [], CM, None
    try:
        while url:
            j = _get(url, params).json()
            if "error" in j:
                raise RuntimeError(str(j["error"])[:90])
            rows += j.get("data", [])
            url, params = j.get("next_page_url"), None                 # the next page URL carries every parameter
    except Exception as e:
        err = e
    seen = int(time.time() * 1000)
    out = []
    for d in rows:
        day = str(d.get("time", ""))[:10]
        if len(day) != 10 or day >= today:                              # complete UTC days only
            continue
        vals = []
        for m in CM_METRICS:
            try:
                vals.append(float(d.get(m)))
            except (TypeError, ValueError):
                vals.append(np.nan)
        out.append([day] + vals)
    new = None
    if out:
        new = pd.DataFrame(out, columns=["date"] + CM_METRICS).drop_duplicates("date")
        new["known_ms"] = known_at(_day_ms(new["date"]) + DAY_MS + ONCHAIN_LAG_MS, seen)
    n = _extend("onchain", asset, src_dir, old, new)
    if err is not None:
        raise RuntimeError("%s (file has %d rows)" % (str(err)[:90], n))
    return n


def update(log=print, src_dir=None, raw_dir=None, assets=None, sources=None, force=False):
    """Fetch / extend every file. -> {"<source>_<ASSET>": rows on disk, or "failed: <reason>"}. Never raises; a source
    that fails keeps its old file plus whatever arrived before the failure. sources: a subset of FILES to run.
    With the default folders (the live loop) a source asked less than MIN_GAP_S ago is skipped unless force."""
    out = OrderedDict()
    names = list(sources or FILES)
    gate = src_dir is None and raw_dir is None and not force
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
    for asset in assets or [a for a in CFG["assets"] if a in METRICS_START]:
        for name in names:
            key = "%s_%s" % (name, asset)
            now = int(time.time() * 1000)
            try:
                if name == "metrics":
                    out[key] = int(_update_metrics(asset, src_dir, raw_dir, now, log))
                elif name == "bitfinex":
                    out[key] = int(_update_bitfinex(asset, src_dir, now))
                elif name == "cme":
                    out[key] = int(_update_cme(asset, src_dir, now))
                else:
                    out[key] = int(_update_onchain(asset, src_dir, now))
            except Exception as e:
                out[key] = "failed: %s" % (str(e) or type(e).__name__)[:160]
            try:
                log("sources.flows %s: %s" % (key, out[key]))
            except Exception:
                pass
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


# ------------------------------------------------------------------ the no-lookahead join
def _asof(known_ms, values, close_ms, max_age_ms):
    """THE JOIN. values[j] became known at known_ms[j]. -> for each close, the newest non-NaN value known at or before
    it (by known-at time), or NaN when there is none or it is older than max_age_ms."""
    known_ms, values = np.asarray(known_ms, dtype="float64"), np.asarray(values, dtype=float)
    keep = np.isfinite(values) & np.isfinite(known_ms)
    known_ms, values = known_ms[keep].astype("int64"), values[keep]
    order = np.argsort(known_ms, kind="stable")
    known_ms, values = known_ms[order], values[order]
    close_ms = np.asarray(close_ms, dtype="int64")
    out = np.full(len(close_ms), np.nan)
    if not len(values):
        return out
    k = np.searchsorted(known_ms, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    ok = (k >= 0) & (close_ms - known_ms[kk] <= max_age_ms)
    out[ok] = values[kk[ok]]
    return out


def _daily_grid(frame):
    """A date-keyed frame -> on a gapless daily grid (a missing day is a NaN row), index = 00:00 UTC ms of the day.
    Each day's known_ms is kept; a filled-in day has NaN known_ms (never used)."""
    if not len(frame):
        return frame.set_index(pd.Index([], dtype="int64"))
    f = frame.copy()
    f.index = _day_ms(f["date"])
    f = f.drop(columns="date")
    return f.reindex(np.arange(int(f.index[0]), int(f.index[-1]) + DAY_MS, DAY_MS, dtype="int64"))


def _z(s, n, n_min):
    w = s.rolling(n, min_periods=n_min)
    sd = w.std()
    return (s - w.mean()) / sd.where(sd > 0)


def _metrics_daily(asset, src_dir, cutoff_ms=None):
    """-> daily frame (index = 00:00 UTC of day D) with oi (last snapshot of D), daily means of ln(ratios) and
    known_ms of the day = the latest known_ms among its rows."""
    m = load_source("metrics", asset, src_dir)
    if cutoff_ms is not None:
        m = m[m["known_ms"] < cutoff_ms]
    if not len(m):
        return pd.DataFrame()
    day = m["ts_ms"] // DAY_MS * DAY_MS
    ln = lambda c: np.log(m[c].where(m[c] > 0))                        # noqa: E731
    g = pd.DataFrame({"day": day, "oi": m["oi"], "oi_value": m["oi_value"], "ln_global": ln("global_ls"),
                      "ln_top_pos": ln("top_pos_ls"), "ln_top_acct": ln("top_acct_ls"), "known_ms": m["known_ms"]})
    agg = g.groupby("day").agg(oi=("oi", "last"), oi_value=("oi_value", "last"), ln_global=("ln_global", "mean"),
                               ln_top_pos=("ln_top_pos", "mean"), ln_top_acct=("ln_top_acct", "mean"),
                               known_ms=("known_ms", "max"), n=("oi", "size"))
    agg = agg[agg["n"] >= 48]                                           # at least half a day of 15m rows
    return agg.reindex(np.arange(int(agg.index[0]), int(agg.index[-1]) + DAY_MS, DAY_MS, dtype="int64")) if len(agg) else agg


def inputs(close_ms, asset, src_dir=None, cutoff_ms=None):
    """-> frame indexed like close_ms (epoch ms of decision instants) with the H39 transforms X1-X9 (INPUTS, unclipped)
    and the readable raw columns (RAW), each the newest value KNOWN at or before the instant (NaN = no read).
    cutoff_ms: drop every stored row known at or after it before computing anything (the study passes the holdout seal)."""
    close_ms = np.asarray(close_ms, dtype="int64")
    out = pd.DataFrame(np.nan, index=close_ms, columns=INPUTS + RAW)
    errors = {}

    try:                                                                # X1-X3: Binance archive positioning
        d = _metrics_daily(asset, src_dir, cutoff_ms)
        if len(d):
            k = d["known_ms"].values
            ln_oi = np.log(d["oi"].where(d["oi"] > 0))
            out["fl_oi_7d"] = _asof(k, ln_oi - ln_oi.shift(OI_DAYS), close_ms, METRICS_MAX_AGE)
            out["fl_ls_global_z"] = _asof(k, _z(d["ln_global"], LS_Z_DAYS, LS_Z_MIN), close_ms, METRICS_MAX_AGE)
            out["fl_ls_topgap_z"] = _asof(k, _z(d["ln_top_pos"] - d["ln_global"], LS_Z_DAYS, LS_Z_MIN), close_ms,
                                          METRICS_MAX_AGE)
            out["fl_oi"] = _asof(k, d["oi"], close_ms, METRICS_MAX_AGE)
            out["fl_global_ls"] = _asof(k, np.exp(d["ln_global"]), close_ms, METRICS_MAX_AGE)
            out["fl_top_pos_ls"] = _asof(k, np.exp(d["ln_top_pos"]), close_ms, METRICS_MAX_AGE)
    except Exception as e:
        errors["metrics"] = "%s: %s" % (type(e).__name__, str(e)[:160])

    try:                                                                # X4: Bitfinex margin longs / shorts, hourly grid
        b = load_source("bitfinex", asset, src_dir)
        if cutoff_ms is not None:
            b = b[b["known_ms"] < cutoff_ms]
        b = b[b["ts_ms"] % HOUR_MS == 0]
        if len(b):
            g = b.set_index("ts_ms")
            g = g.reindex(np.arange(int(g.index[0]), int(g.index[-1]) + HOUR_MS, HOUR_MS, dtype="int64"))
            net = np.log(g["long"].where(g["long"] > 0) / g["short"].where(g["short"] > 0))
            k = g["known_ms"].values
            out["fl_bfx_14d"] = _asof(k, net - net.shift(BFX_HOURS), close_ms, BFX_MAX_AGE)
            out["fl_bfx_long"] = _asof(k, g["long"], close_ms, BFX_MAX_AGE)
            out["fl_bfx_short"] = _asof(k, g["short"], close_ms, BFX_MAX_AGE)
    except Exception as e:
        errors["bitfinex"] = "%s: %s" % (type(e).__name__, str(e)[:160])

    try:                                                                # X5: CFTC leveraged funds, weekly reports
        c = load_source("cme", asset, src_dir)
        if cutoff_ms is not None:
            c = c[c["known_ms"] < cutoff_ms]
        if len(c):
            oi = c["oi"].where(c["oi"] > 0)
            lev = 100.0 * (c["lev_long"] - c["lev_short"]) / oi
            am = 100.0 * (c["am_long"] - c["am_short"]) / oi
            k = c["known_ms"].values                                    # one row per report: the grid is the reports
            out["fl_cme_lev_z"] = _asof(k, _z(lev, CME_Z_REPORTS, CME_Z_MIN), close_ms, CME_MAX_AGE)
            out["fl_cme_lev_net_pct"] = _asof(k, lev, close_ms, CME_MAX_AGE)
            out["fl_cme_am_net_pct"] = _asof(k, am, close_ms, CME_MAX_AGE)
    except Exception as e:
        errors["cme"] = "%s: %s" % (type(e).__name__, str(e)[:160])

    try:                                                                # X6-X9: CoinMetrics daily
        def onchain(a):
            o = load_source("onchain", a, src_dir)
            if cutoff_ms is not None:
                o = o[o["known_ms"] < cutoff_ms]
            return _daily_grid(o)
        o = onchain(asset)
        if len(o):
            k = o["known_ms"].values
            mvrv = o["CapMVRVCur"].where(o["CapMVRVCur"] > 0)
            out["fl_mvrv_z"] = _asof(k, _z(np.log(mvrv), MVRV_Z_DAYS, MVRV_Z_MIN), close_ms, ONCHAIN_MAX_AGE)
            net = (o["FlowInExNtv"] - o["FlowOutExNtv"]).rolling(FLOW_DAYS, min_periods=FLOW_DAYS).sum()
            out["fl_netflow_7d"] = _asof(k, net / o["SplyExNtv"].where(o["SplyExNtv"] > 0), close_ms, ONCHAIN_MAX_AGE)
            a = o["AdrActCnt"].where(o["AdrActCnt"] > 0)
            ratio = a.rolling(ADDR_SHORT, min_periods=ADDR_SHORT).mean() / a.rolling(ADDR_LONG, min_periods=ADDR_LONG_MIN).mean()
            out["fl_addr"] = _asof(k, np.log(ratio), close_ms, ONCHAIN_MAX_AGE)
            out["fl_mvrv"] = _asof(k, mvrv, close_ms, ONCHAIN_MAX_AGE)
            out["fl_exch_supply"] = _asof(k, o["SplyExNtv"], close_ms, ONCHAIN_MAX_AGE)
            out["fl_addr_act"] = _asof(k, a, close_ms, ONCHAIN_MAX_AGE)
        h = o if asset == "BTCUSDT" else onchain("BTCUSDT")             # the hash ribbon is BTC's, for both coins
        if len(h):
            hr = h["HashRate"].where(h["HashRate"] > 0)
            rib = hr.rolling(HASH_FAST, min_periods=HASH_FAST).mean() / hr.rolling(HASH_SLOW, min_periods=HASH_SLOW).mean()
            k = h["known_ms"].values
            out["fl_hash_ribbon"] = _asof(k, np.log(rib), close_ms, ONCHAIN_MAX_AGE)
            out["fl_hashrate_btc"] = _asof(k, hr, close_ms, ONCHAIN_MAX_AGE)
    except Exception as e:
        errors["onchain"] = "%s: %s" % (type(e).__name__, str(e)[:160])

    out = out.replace([np.inf, -np.inf], np.nan)
    out.attrs["errors"] = errors
    return out


def features(index15, asset, src_dir=None, bars=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature in GROUPS as a float clipped to +-3 (0.0 = no read,
    never NaN) plus the readable RAW columns (NaN = no read). Reads only files under data/sources/; `bars` is accepted
    for the same signature as the other source modules and not needed."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = _data.to_ms(index15) + BAR_MS
    x = inputs(close_ms, asset, src_dir)
    out = pd.DataFrame(index=index15)
    for f in FEATURES:
        out[f] = np.clip(x[f].values / UNITS[f], -3.0, 3.0)
    for r in RAW:
        out[r] = x[r].values
    out[FEATURES] = out[FEATURES].astype(float).fillna(0.0)
    out.attrs["errors"] = x.attrs["errors"]
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
    oi, g, t = _num(row, "fl_oi"), _num(row, "fl_global_ls"), _num(row, "fl_top_pos_ls")
    if oi is None and g is None:
        say[GROUPS["metrics"][0]] = "No Binance archive positioning read for %s at this close." % coin
    else:
        bits = []
        if oi is not None:
            bits.append("open interest %.0f %s (%+.1f%% over 7 days)" % (oi, coin, (_num(row, "fl_oi_7d") or 0.0) * 10.0))
        if g is not None:
            bits.append("%.2f long accounts per short" % g)
        if t is not None:
            bits.append("top traders %.2f long per short by position" % t)
        say[GROUPS["metrics"][0]] = "Binance %s futures, as of the last archived day: %s." % (coin, "; ".join(bits))
    lo, sh = _num(row, "fl_bfx_long"), _num(row, "fl_bfx_short")
    if lo is None or sh is None:
        say[GROUPS["bitfinex"][0]] = "No Bitfinex margin read for %s at this close." % coin
    else:
        say[GROUPS["bitfinex"][0]] = ("Bitfinex margin: %.0f %s long against %.0f short (%.1f long per short); the "
                                      "ratio's log moved %+.2f over 14 days."
                                      % (lo, coin, sh, lo / sh if sh > 0 else float("nan"),
                                         (_num(row, "fl_bfx_14d") or 0.0) * UNITS["fl_bfx_14d"]))
    lev, am = _num(row, "fl_cme_lev_net_pct"), _num(row, "fl_cme_am_net_pct")
    if lev is None:
        say[GROUPS["cme"][0]] = "No CFTC report on %s at this close." % CME_CODE.get(asset, ("", "CME futures"))[1]
    else:
        say[GROUPS["cme"][0]] = ("%s (CFTC, last released report): leveraged funds net %+.1f%% of open interest, asset "
                                 "managers net %+.1f%%." % (CME_CODE[asset][1], lev, am if am is not None else float("nan")))
    mv, sup, ad = _num(row, "fl_mvrv"), _num(row, "fl_exch_supply"), _num(row, "fl_addr_act")
    if mv is None and sup is None and ad is None:
        say[GROUPS["onchain"][0]] = "No on-chain read for %s at this close." % coin
    else:
        bits = []
        if mv is not None:
            bits.append("market value is %.2fx realised value" % mv)
        if sup is not None:
            bits.append("%.0f %s on exchanges" % (sup, coin))
        if ad is not None:
            bits.append("%.0f active addresses a day" % ad)
        say[GROUPS["onchain"][0]] = "CoinMetrics, last complete day: %s." % "; ".join(bits)
    return say
