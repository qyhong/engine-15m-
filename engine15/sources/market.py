# -*- coding: utf-8 -*-
"""market -- five market-wide decision cards, each a free public source kept on disk.

  etf        Spot ETF flows             Farside Investors' daily flow tables (US spot Bitcoin
                                        ETFs from 11 Jan 2024, Ether ETFs from 23 Jul 2024)
  stable     Stablecoin supply          DefiLlama, total circulating, daily from Nov 2017
  cbprem     Coinbase premium           Coinbase Exchange hourly candles (BTC-USD, ETH-USD)
                                        against this project's own Binance bars
  breadth    Market breadth and ETH/BTC Binance spot hourly closes of ten large altcoins, and
                                        the ETH/BTC ratio from this project's own bars
  sentiment  Fear and Greed             alternative.me, daily index 0-100 from Feb 2018

Everything lives under data/sources/ as CSV, written atomically. update() extends the
files; features() only ever reads them.

THE ONE RULE (known at the 15m close, tests/test_sources_market.py):
  an hourly bar stamped H (its open)  is used from H + 1 hour (its end);
  a daily value stamped UTC day D     is used from 00:00 UTC of D + 1;
  an ETF flow for US trading date D   is used from 12:00 UTC of D + 1 (the issuers report
                                      through the US evening; 00:00 UTC would be too early).
Every reading is computed on the source's own time grid with backward-looking windows only,
then handed to a 15m row by an as-of join on the time the value became known. A value older
than its card's MAX_AGE is "no read" (0.0), so a file that stopped updating falls silent
instead of repeating itself.

Readings are dimensionless and clipped; 0.0 = no read. The readable columns (RAW) may be NaN.
"""
import html
import os
import re
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data
from ..config import CFG, DATA_DIR

GROUPS = OrderedDict([
    ("etf", ("Spot ETF flows", ["etf_1d", "etf_5d"])),
    ("stable", ("Stablecoin supply", ["stb_7d", "stb_30d"])),
    ("cbprem", ("Coinbase premium", ["cbp_z", "cbp_24h", "cbp_d4h"])),
    ("breadth", ("Market breadth and ETH/BTC", ["brd_above_24h", "brd_above_7d", "brd_above_30d", "brd_rel_24h",
                                                "brd_ethbtc_1d", "brd_ethbtc_7d"])),
    ("sentiment", ("Fear and Greed", ["fng_level", "fng_7d", "fng_extreme"])),
])
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
RAW = ["etf_net_musd", "etf_sum5_musd", "stb_total_busd", "stb_chg7_pct", "stb_chg30_pct", "cbp_bps", "cbp_24h_bps",
       "brd_n", "brd_pct_24h", "brd_pct_7d", "brd_pct_30d", "brd_rel_24h_pct", "brd_ethbtc", "fng_value", "fng_chg7"]

# ---- where things live (module attributes so a test can point them at a temp folder)
SRC_DIR = os.path.join(DATA_DIR, "sources")
BARS_PATH = data.path_for                 # asset -> the project's own 15m file

# ---- constants, declared once (docs/SOURCES_market.md says why)
H_MS, D_MS, BAR_MS = 3600000, 86400000, CFG["bar_ms"]
START_MS = 1546300800000                  # 2019-01-01, where the project's own bars begin
COINS = ("SOL", "BNB", "XRP", "ADA", "DOGE", "LINK", "AVAX", "LTC", "DOT", "TRX")
CB_PRODUCT = {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD"}
ETF_KEY = {"BTCUSDT": "btc", "ETHUSDT": "eth"}
ETF_NAME = {"BTCUSDT": "Bitcoin", "ETHUSDT": "Ether"}
DAILY_LAG_MS = D_MS                       # a daily value for day D: known from 00:00 UTC of D + 1
FNG_LAG_MS = D_MS                         # Fear and Greed: the same rule (the site shows D's value during D itself)
ETF_LAG_MS = D_MS + 12 * H_MS             # an ETF flow for trading date D: known from 12:00 UTC of D + 1
HOURLY_MAX_AGE_MS = 6 * H_MS              # an hourly reading goes silent 6 hours after it became known
DAILY_MAX_AGE_MS = 3 * D_MS               # a daily reading: 3 days
ETF_MAX_AGE_MS = 6 * D_MS                 # an ETF flow: 6 days (a long weekend is 4)
ETF_STD_DAYS, ETF_STD_MIN = 30, 10        # flows are scaled by their own last 30 trading days (10 to start)
STB_RMS_DAYS, STB_RMS_MIN = 365, 90       # supply changes are scaled by their own typical size over a year
CB_WIN_H, CB_WIN_MIN = 720, 168           # the premium is judged against its last 30 days (7 to start)
CB_SCALE = 0.001                          # the 24h mean premium is read in units of 0.1% (10 basis points)
VOL_WIN_H, VOL_WIN_MIN = 720, 168         # volatility = std of hourly log returns over 30 days
BREADTH_WINDOWS = (("24h", 24), ("7d", 168), ("30d", 720))
MA_MIN_SHARE = 0.9                        # a coin's average needs 90% of its window present
MIN_COINS = 3                             # fewer coins than this with a read: no breadth read
FNG_CHG_SCALE = 25.0                      # the 7-day change is read in units of 25 index points
FNG_LOW, FNG_HIGH = 20, 80                # "extreme" fear / greed
DAILY_REFETCH_H = 3.0                     # a daily source is asked again at most every 3 hours
TIMEOUT = 30
CB_PAUSE, BN_PAUSE = 0.35, 0.15           # seconds between requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}

ETF_URLS = {"btc": ("https://farside.co.uk/bitcoin-etf-flow-all-data/", "https://farside.co.uk/btc/"),
            "eth": ("https://farside.co.uk/ethereum-etf-flow-all-data/", "https://farside.co.uk/eth/")}
STABLE_URL = "https://stablecoins.llama.fi/stablecoincharts/all"
COINBASE_URL = "https://api.exchange.coinbase.com/products/%s/candles"
BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
FNG_URL = "https://api.alternative.me/fng/?limit=0"

ETF_COLS = ["date", "net_musd", "n_funds"]
STABLE_COLS = ["date", "total_usd", "usd_pegged"]
FNG_COLS = ["date", "value"]
HOURLY_COLS = ["ts_ms", "close"]
LAST_ERRORS = {}                          # card -> why features() could not read it, last call


# ------------------------------------------------------------------ files
def etf_path(key, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "etf_%s.csv" % key)


def stable_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "stablecoins.csv")


def fng_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "fear_greed.csv")


def coinbase_path(asset, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "coinbase_%s_1h.csv" % CB_PRODUCT[asset].replace("-", "").lower())


def coin_path(coin, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "binance_%susdt_1h.csv" % coin.lower())


def _read(path, cols):
    """A source file -> frame; a missing or empty file -> an empty frame with those columns."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(columns=cols)
    try:
        return pd.read_csv(path, float_precision="round_trip")      # exactly the number that was written
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=cols)


def _write(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _day_ms(dates):
    """'YYYY-MM-DD' strings -> epoch ms of 00:00 UTC that day."""
    return data.to_ms(pd.DatetimeIndex(pd.to_datetime(pd.Series(dates, dtype=str), utc=True)))


def load_daily(path, cols):
    """A daily file -> frame of its value columns keyed by the day's 00:00 UTC in epoch ms."""
    d = _read(path, cols)
    if not len(d):
        return pd.DataFrame(columns=cols[1:], index=pd.Index([], dtype="int64"), dtype=float)
    out = d[cols[1:]].astype(float)
    out.index = pd.Index(_day_ms(d["date"].values), dtype="int64")
    return out[~out.index.duplicated(keep="last")].sort_index()


def load_hourly(path):
    """An hourly file -> Series of closes keyed by the hour's OPEN in epoch ms."""
    d = _read(path, HOURLY_COLS)
    if not len(d):
        return pd.Series(dtype=float, index=pd.Index([], dtype="int64"))
    s = pd.Series(d["close"].values.astype(float), index=pd.Index(d["ts_ms"].values.astype("int64")))
    return s[~s.index.duplicated(keep="last")].sort_index()


def _hourly_close(asset, bars=None):
    """The project's own 15m bars -> hourly closes keyed by the hour's OPEN (epoch ms).
    The close of hour H is the close of the 15m bar that opens at H + 45 min and nothing else:
    an hour whose last bar is missing has no close."""
    if bars is not None and asset in bars:
        ms, close = data.to_ms(bars[asset].index), bars[asset]["close"].values.astype(float)
    else:
        path = BARS_PATH(asset)
        if not os.path.exists(path):
            return pd.Series(dtype=float, index=pd.Index([], dtype="int64"))
        d = pd.read_csv(path, usecols=["ts_ms", "close"])
        ms, close = d["ts_ms"].values.astype("int64"), d["close"].values.astype(float)
    last = (ms % H_MS) == (H_MS - BAR_MS)
    s = pd.Series(close[last], index=pd.Index(ms[last] - (H_MS - BAR_MS), dtype="int64"))
    return s[~s.index.duplicated(keep="last")].sort_index()


def _grid(lo, hi, step):
    return pd.Index(np.arange(int(lo), int(hi) + step, step, dtype="int64"))


def _clean(frame):
    return frame.replace([np.inf, -np.inf], np.nan)


# ------------------------------------------------------------------ the readings, each on its source's own grid
# Each builder returns a list of (frame keyed by the source stamp in ms, lag until known in ms, max age in ms).
def _etf_frames(asset, src_dir):
    key = ETF_KEY.get(asset)
    d = load_daily(etf_path(key, src_dir), ETF_COLS) if key else None
    if d is None or not len(d):
        return []
    net = d["net_musd"].dropna()                                     # one row per reported US trading day
    sd = net.rolling(ETF_STD_DAYS, min_periods=ETF_STD_MIN).std()
    sd = sd.where(sd > 0)
    sum5 = net.rolling(5, min_periods=5).sum()
    f = pd.DataFrame({"etf_1d": (net / sd).clip(-3, 3), "etf_5d": (sum5 / (sd * np.sqrt(5.0))).clip(-3, 3),
                      "etf_net_musd": net, "etf_sum5_musd": sum5})
    return [(f, ETF_LAG_MS, ETF_MAX_AGE_MS)]


def _stable_frames(src_dir):
    d = load_daily(stable_path(src_dir), STABLE_COLS)
    if not len(d):
        return []
    s = d["total_usd"].reindex(_grid(d.index[0], d.index[-1], D_MS))  # calendar days; a missing day stays missing
    s = s.where(s > 0)
    f = pd.DataFrame({"stb_total_busd": s / 1e9})
    for tag, n in (("7", 7), ("30", 30)):
        chg = s / s.shift(n) - 1.0
        rms = np.sqrt((chg ** 2).rolling(STB_RMS_DAYS, min_periods=STB_RMS_MIN).mean())
        f["stb_%sd" % tag] = (chg / rms.where(rms > 0)).clip(-3, 3)
        f["stb_chg%s_pct" % tag] = 100.0 * chg
    return [(f, DAILY_LAG_MS, DAILY_MAX_AGE_MS)]


def _cbprem_frames(asset, src_dir, bars):
    if asset not in CB_PRODUCT:
        return []
    cb, bn = load_hourly(coinbase_path(asset, src_dir)), _hourly_close(asset, bars)
    if not len(cb) or not len(bn):
        return []
    grid = _grid(min(cb.index[0], bn.index[0]), max(cb.index[-1], bn.index[-1]), H_MS)
    prem = cb.reindex(grid) / bn.reindex(grid) - 1.0                 # same hour on both venues, else no premium
    mean = prem.rolling(CB_WIN_H, min_periods=CB_WIN_MIN).mean()
    sd = prem.rolling(CB_WIN_H, min_periods=CB_WIN_MIN).std()
    m24 = prem.rolling(24, min_periods=12).mean()
    d4 = prem - prem.shift(4)
    sd4 = d4.rolling(CB_WIN_H, min_periods=CB_WIN_MIN).std()
    f = pd.DataFrame({"cbp_z": ((prem - mean) / sd.where(sd > 0)).clip(-3, 3), "cbp_24h": (m24 / CB_SCALE).clip(-3, 3),
                      "cbp_d4h": (d4 / sd4.where(sd4 > 0)).clip(-3, 3), "cbp_bps": 1e4 * prem, "cbp_24h_bps": 1e4 * m24})
    return [(f, H_MS, HOURLY_MAX_AGE_MS)]


def _breadth_frames(src_dir, bars):
    out = []
    btc, eth = _hourly_close("BTCUSDT", bars), _hourly_close("ETHUSDT", bars)
    coins = OrderedDict()
    for c in COINS:
        s = load_hourly(coin_path(c, src_dir))
        if len(s):
            coins[c] = s
    if coins:
        grid = _grid(min(s.index[0] for s in coins.values()), max(s.index[-1] for s in coins.values()), H_MS)
        px = pd.DataFrame(dict((c, s.reindex(grid)) for c, s in coins.items()), index=grid)
        px = px.where(px > 0)
        f = pd.DataFrame(index=grid)
        for tag, w in BREADTH_WINDOWS:
            sma = px.rolling(w, min_periods=int(w * MA_MIN_SHARE)).mean()
            valid = px.notna() & sma.notna()                         # a coin not yet listed does not count
            n = valid.sum(axis=1)
            share = ((px > sma) & valid).sum(axis=1) / n.where(n >= MIN_COINS)
            f["brd_above_%s" % tag] = (2.0 * share - 1.0).clip(-1, 1)
            f["brd_pct_%s" % tag] = 100.0 * share
            if tag == "24h":
                f["brd_n"] = n.where(n >= MIN_COINS)
        if len(btc):
            b = btc.reindex(grid)
            r24 = np.log(px / px.shift(24))
            group = r24.mean(axis=1).where(r24.notna().sum(axis=1) >= MIN_COINS)
            vol = np.log(b / b.shift(1)).rolling(VOL_WIN_H, min_periods=VOL_WIN_MIN).std() * np.sqrt(24.0)
            spread = group - np.log(b / b.shift(24))
            f["brd_rel_24h"] = (spread / vol.where(vol > 0)).clip(-3, 3)
            f["brd_rel_24h_pct"] = 100.0 * spread
        out.append((f, H_MS, HOURLY_MAX_AGE_MS))
    if len(btc) and len(eth):
        grid = _grid(max(btc.index[0], eth.index[0]), min(btc.index[-1], eth.index[-1]), H_MS)
        if len(grid):
            ratio = eth.reindex(grid) / btc.reindex(grid)
            lr = np.log(ratio)
            vol = lr.diff().rolling(VOL_WIN_H, min_periods=VOL_WIN_MIN).std()
            vol = vol.where(vol > 0)
            g = pd.DataFrame({"brd_ethbtc": ratio,
                              "brd_ethbtc_1d": ((lr - lr.shift(24)) / (vol * np.sqrt(24.0))).clip(-3, 3),
                              "brd_ethbtc_7d": ((lr - lr.shift(168)) / (vol * np.sqrt(168.0))).clip(-3, 3)})
            out.append((g, H_MS, HOURLY_MAX_AGE_MS))
    return out


def _fng_frames(src_dir):
    d = load_daily(fng_path(src_dir), FNG_COLS)
    if not len(d):
        return []
    v = d["value"].reindex(_grid(d.index[0], d.index[-1], D_MS))      # calendar days; a missing day stays missing
    chg = v - v.shift(7)
    extreme = pd.Series(np.where(v <= FNG_LOW, -1.0, np.where(v >= FNG_HIGH, 1.0, 0.0)), index=v.index).where(v.notna())
    f = pd.DataFrame({"fng_level": ((v - 50.0) / 50.0).clip(-1, 1), "fng_7d": (chg / FNG_CHG_SCALE).clip(-3, 3),
                      "fng_extreme": extreme, "fng_value": v, "fng_chg7": chg})
    return [(f, FNG_LAG_MS, DAILY_MAX_AGE_MS)]


def _asof(known_ms, values, close_ms, max_age_ms):
    """THE NO-LOOKAHEAD JOIN. For each 15m close: the last value that was known at or before
    it (NaN if none, or if that value is older than max_age_ms)."""
    values = np.asarray(values, dtype=float)
    out = np.full(len(close_ms), np.nan)
    have = ~np.isnan(values)
    if not have.any():
        return out
    k_ms, v = np.asarray(known_ms, dtype="int64")[have], values[have]
    k = np.searchsorted(k_ms, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    hit = (k >= 0) & ((close_ms - k_ms[kk]) <= max_age_ms)
    out[hit] = v[kk[hit]]
    return out


def features(index15, asset, src_dir=None, bars=None, strict=False):
    """-> frame on the 15m index: every feature in GROUPS (float, 0.0 = no read, never NaN)
    and the readable RAW columns (NaN where there is no read).

    index15  15m bar OPEN times (UTC); a row is known at open + 15 min
    bars     optional {asset: 15m frame} to use instead of the project's bar files
    strict   raise on a broken source instead of leaving its card at "no read" (tests)
    """
    close_ms = data.to_ms(index15) + BAR_MS
    out = pd.DataFrame(np.nan, index=index15, columns=FEATURES + RAW, dtype=float)
    LAST_ERRORS.clear()
    builders = (("etf", lambda: _etf_frames(asset, src_dir)), ("stable", lambda: _stable_frames(src_dir)),
                ("cbprem", lambda: _cbprem_frames(asset, src_dir, bars)),
                ("breadth", lambda: _breadth_frames(src_dir, bars)), ("sentiment", lambda: _fng_frames(src_dir)))
    for name, build in builders:
        try:
            for frame, lag_ms, max_age_ms in build():
                frame = _clean(frame)
                known_ms = np.asarray(frame.index, dtype="int64") + lag_ms
                for col in frame.columns:
                    out[col] = _asof(known_ms, frame[col].values, close_ms, max_age_ms)
        except Exception as e:                                       # a broken file silences its card, not the engine
            if strict:
                raise
            LAST_ERRORS[name] = "%s: %s" % (type(e).__name__, str(e)[:120])
    out[FEATURES] = out[FEATURES].fillna(0.0)
    return out


# ------------------------------------------------------------------ plain English
def _v(row, key):
    try:
        x = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return float("nan")
    return x


def _money(m):
    return "%s$%s million" % ("-" if m < 0 else "+", format(abs(m), ",.1f"))


def describe(row, asset, src_dir=None):
    """One row of features() -> {card title: one sentence}."""
    out = OrderedDict()
    ok = lambda x: x == x                                            # not NaN

    title, name = GROUPS["etf"][0], ETF_NAME.get(asset, asset)
    net, sum5 = _v(row, "etf_net_musd"), _v(row, "etf_sum5_musd")
    key = ETF_KEY.get(asset)
    if key is None or not len(_read(etf_path(key, src_dir), ETF_COLS)):
        out[title] = "No source reachable: there is no US spot %s ETF flow file on disk." % name
    elif not ok(net):
        out[title] = "No read: no US spot %s ETF flow is on file for this time." % name
    else:
        s = "US spot %s ETFs: %s net on the last reported day (%+.1f times a usual day's swing)" % (
            name, _money(net), _v(row, "etf_1d"))
        if ok(sum5):
            s += "; %s over the last five trading days (%+.1f)" % (_money(sum5), _v(row, "etf_5d"))
        out[title] = s + "."

    title = GROUPS["stable"][0]
    tot, c7, c30 = _v(row, "stb_total_busd"), _v(row, "stb_chg7_pct"), _v(row, "stb_chg30_pct")
    if not ok(tot):
        out[title] = "No read: no stablecoin supply figure is on file for this time."
    else:
        s = "Total stablecoin supply is $%s billion" % format(tot, ",.1f")
        if ok(c7):
            s += ", %+.2f%% over 7 days" % c7
        if ok(c30):
            s += " and %+.2f%% over 30 days" % c30
        out[title] = s + " (%+.1f and %+.1f times its usual swing of the past year)." % (_v(row, "stb_7d"), _v(row, "stb_30d"))

    title, coin = GROUPS["cbprem"][0], asset.replace("USDT", "")
    bps, m24 = _v(row, "cbp_bps"), _v(row, "cbp_24h_bps")
    if not ok(bps):
        out[title] = "No read: no Coinbase %s price is on file for the last closed hour." % coin
    else:
        s = "%s closed the last hour %.1f basis points %s on Coinbase than on Binance" % (
            coin, abs(bps), "higher" if bps >= 0 else "lower")
        if ok(m24):
            s += "; the 24-hour average gap is %+.1f basis points" % m24
        out[title] = s + "; against its last 30 days that is %+.1f standard deviations, 4-hour change %+.1f." % (
            _v(row, "cbp_z"), _v(row, "cbp_d4h"))

    title = GROUPS["breadth"][0]
    n, ratio = _v(row, "brd_n"), _v(row, "brd_ethbtc")
    parts = []
    if ok(n):
        s = "Of %d large altcoins tracked, %.0f%% are above their 24-hour average" % (n, _v(row, "brd_pct_24h"))
        for tag, label in (("7d", "7-day"), ("30d", "30-day")):
            if ok(_v(row, "brd_pct_%s" % tag)):
                s += ", %.0f%% above their %s average" % (_v(row, "brd_pct_%s" % tag), label)
        parts.append(s)
        if ok(_v(row, "brd_rel_24h_pct")):
            parts.append("over 24 hours the group returned %+.2f%% against BTC (%+.1f in units of BTC's daily volatility)" % (
                _v(row, "brd_rel_24h_pct"), _v(row, "brd_rel_24h")))
    if ok(ratio):
        parts.append("ETH/BTC is %.5f, trend %+.1f over one day and %+.1f over seven days (in volatility units)" % (
            ratio, _v(row, "brd_ethbtc_1d"), _v(row, "brd_ethbtc_7d")))
    out[title] = (parts[0][0].upper() + parts[0][1:] + "".join("; " + p for p in parts[1:]) + ".") if parts \
        else "No read: no altcoin hourly closes and no ETH/BTC ratio are on file for the last closed hour."

    title = GROUPS["sentiment"][0]
    v, chg = _v(row, "fng_value"), _v(row, "fng_chg7")
    if not ok(v):
        out[title] = "No read: no Fear and Greed value is on file for this time."
    else:
        word = ("extreme fear" if v <= FNG_LOW else "fear" if v < 45 else "neutral" if v <= 55
                else "greed" if v < FNG_HIGH else "extreme greed")
        s = "The Fear and Greed index last printed %d (%s)" % (round(v), word)
        if ok(chg):
            s += ", %s over 7 days" % ("unchanged" if chg == 0 else "%s %d points" % ("up" if chg > 0 else "down", abs(round(chg))))
        out[title] = s + "."
    return out


# ------------------------------------------------------------------ fetch
def _now_ms():
    return int(time.time() * 1000)


def _get(sess, url, params=None):
    """One polite GET: 30 s timeout, two more tries on a busy or failing server."""
    last = None
    for attempt in range(3):
        try:
            r = sess.get(url, params=params, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            if attempt == 2 or getattr(getattr(e, "response", None), "status_code", None) in (400, 401, 403, 404):
                raise
            time.sleep(2.0 * (attempt + 1))
    raise last


def _fresh(path, hours):
    return (os.path.exists(path) and len(_read(path, [])) > 0
            and (time.time() - os.path.getmtime(path)) < hours * 3600.0)


_MONTH = dict((m, i + 1) for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split()))
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_DATE = re.compile(r"^(\d{1,2}) ([A-Za-z]{3}) (\d{4})$")


def _num(cell):
    s = cell.replace(",", "").replace("$", "").replace("−", "-").strip()
    neg = s.startswith("(") and s.endswith(")")
    try:
        x = float(s.strip("()"))
    except ValueError:
        return None
    return -x if neg else x


def parse_etf_table(text):
    """Farside's flow page -> frame date, net_musd (US$ million, all funds), n_funds (funds that
    reported a number). A day on which no fund has a number (a holiday, or not yet published)
    is left out."""
    rows, total_at = [], None
    for tr in _TR.findall(text):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in _TD.findall(tr)]
        if len(cells) < 3:
            continue
        if total_at is None and cells[-1].lower() == "total":
            total_at = len(cells) - 1                                 # the header row: funds, then Total
            continue
        m = _DATE.match(cells[0])
        if not m or m.group(2).lower() not in _MONTH:
            continue
        at = total_at if total_at is not None and total_at < len(cells) else len(cells) - 1
        funds = [x for x in (_num(c) for c in cells[1:at]) if x is not None]
        if not funds:
            continue
        total = _num(cells[at])
        rows.append(("%04d-%02d-%02d" % (int(m.group(3)), _MONTH[m.group(2).lower()], int(m.group(1))),
                     float(total if total is not None else sum(funds)), len(funds)))
    d = pd.DataFrame(rows, columns=ETF_COLS)
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def _update_etf(sess, key, src_dir, force):
    path = etf_path(key, src_dir)
    if not force and _fresh(path, DAILY_REFETCH_H):
        return len(_read(path, ETF_COLS))
    old, new, why = _read(path, ETF_COLS), None, "no page tried"
    for url in ETF_URLS[key]:
        try:
            got = parse_etf_table(_get(sess, url).text)
            if len(got) >= 5:
                new = got
                break
            why = "no flow table found at %s" % url
        except Exception as e:
            why = "%s (%s)" % (str(e)[:80] or type(e).__name__, url)
        time.sleep(1.0)
    if new is None:
        if not os.path.exists(path):
            _write(old, path)                                         # an empty file: the reader finds "no source"
        raise RuntimeError(why)
    now = _now_ms()
    new = new[_day_ms(new["date"].values) + ETF_LAG_MS <= now]         # a date is stored once it counts as known
    recent = time.strftime("%Y-%m-%d", time.gmtime(now / 1000.0 - 7 * 86400))
    keep = old[(old["date"].astype(str) < recent) | ~old["date"].astype(str).isin(new["date"])]   # the last week may still be completed
    add = new[(new["date"] >= recent) | ~new["date"].isin(old["date"].astype(str))]
    allr = pd.concat([keep, add]) if len(keep) else add
    allr = allr.drop_duplicates("date", keep="last").sort_values("date")
    _write(allr[ETF_COLS], path)
    return len(allr)


def _append_daily(path, cols, new):
    """Dates already on disk stay as first stored (what the engine saw); new dates are added."""
    old = _read(path, cols)
    old["date"] = old["date"].astype(str)
    add = new[~new["date"].isin(old["date"])]
    allr = (pd.concat([old, add]) if len(old) else add).drop_duplicates("date", keep="first").sort_values("date")
    _write(allr[cols], path)
    return len(allr)


def _update_stable(sess, src_dir, force):
    path = stable_path(src_dir)
    if not force and _fresh(path, DAILY_REFETCH_H):
        return len(_read(path, STABLE_COLS))
    today = time.strftime("%Y-%m-%d", time.gmtime(_now_ms() / 1000.0))
    rows = []
    for e in _get(sess, STABLE_URL).json():
        usd = e.get("totalCirculatingUSD") or {}
        day = time.strftime("%Y-%m-%d", time.gmtime(int(e["date"])))
        if day < today and usd:                                       # today's point is still moving
            rows.append((day, float(sum(float(x or 0.0) for x in usd.values())), float(usd.get("peggedUSD") or 0.0)))
    if len(rows) < 30:
        raise RuntimeError("only %d daily rows in the reply" % len(rows))
    return _append_daily(path, STABLE_COLS, pd.DataFrame(rows, columns=STABLE_COLS))


def _update_fng(sess, src_dir, force):
    path = fng_path(src_dir)
    if not force and _fresh(path, DAILY_REFETCH_H):
        return len(_read(path, FNG_COLS))
    rows = [(time.strftime("%Y-%m-%d", time.gmtime(int(e["timestamp"]))), int(e["value"]))
            for e in _get(sess, FNG_URL).json()["data"]]
    if len(rows) < 30:
        raise RuntimeError("only %d daily rows in the reply" % len(rows))
    return _append_daily(path, FNG_COLS, pd.DataFrame(rows, columns=FNG_COLS))


def _extend_hourly(path, batches):
    """Add fetched (ts_ms, close) rows to an hourly file. Whatever arrived before a failure is
    kept, so the next update resumes from there; the failure is still reported."""
    old, rows, err = _read(path, HOURLY_COLS), [], None
    try:
        for batch in batches:
            rows += batch
    except Exception as e:
        err = e
    allr = old
    if rows or not os.path.exists(path):
        new = pd.DataFrame(rows, columns=HOURLY_COLS)
        allr = (pd.concat([old[HOURLY_COLS], new]) if len(old) else new).drop_duplicates("ts_ms", keep="last").sort_values("ts_ms")
        allr["ts_ms"] = allr["ts_ms"].astype("int64")
        _write(allr, path)
    if err is not None:
        raise err
    return len(allr)


def _next_hour(path):
    old = _read(path, HOURLY_COLS)
    return int(old["ts_ms"].max()) + H_MS if len(old) else START_MS


def _coinbase_batches(sess, product, start_ms):
    """Closed hourly candles from start_ms on, 300 hours a request, oldest window first."""
    last_closed = (_now_ms() // H_MS) * H_MS - H_MS                   # the open of the last hour that has ended
    cur = int(start_ms)
    while cur <= last_closed:
        end = min(cur + 299 * H_MS, last_closed)
        iso = lambda ms: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000.0))
        got = _get(sess, COINBASE_URL % product, {"granularity": 3600, "start": iso(cur), "end": iso(end)}).json()
        if not isinstance(got, list):
            raise RuntimeError("unexpected reply: %s" % str(got)[:80])
        yield [(int(c[0]) * 1000, float(c[4])) for c in got if cur <= int(c[0]) * 1000 <= end]   # [time, low, high, open, close, volume]
        cur = end + H_MS
        if cur <= last_closed:
            time.sleep(CB_PAUSE)


def _binance_batches(sess, symbol, start_ms):
    """Closed hourly klines from start_ms (or the listing) on, 1000 a request."""
    cur = int(start_ms)
    while True:
        now = _now_ms()
        if cur + H_MS > now:
            break
        got = _get(sess, BINANCE_URL, {"symbol": symbol, "interval": "1h", "startTime": cur, "limit": 1000}).json()
        if not isinstance(got, list):
            raise RuntimeError("unexpected reply: %s" % str(got)[:80])
        if not got:
            break
        yield [(int(k[0]), float(k[4])) for k in got if int(k[6]) < now]   # close time passed: a closed bar
        cur = int(got[-1][0]) + H_MS
        if len(got) < 1000:
            break
        time.sleep(BN_PAUSE)


def update(log=print, force=False, src_dir=None):
    """Fetch / extend every file under data/sources/. -> {source: rows on disk, or "failed: why"}.
    Never raises; a source that fails keeps its old file. Daily sources are asked again at most
    every DAILY_REFETCH_H hours unless force=True; hourly ones fetch only the hours since their
    last stored row."""
    out = OrderedDict()
    d = src_dir or SRC_DIR
    try:
        import requests
        os.makedirs(d, exist_ok=True)
        sess = requests.Session()
        sess.headers.update(UA)
    except Exception as e:
        return {"all": "failed: %s" % (str(e)[:120] or type(e).__name__)}
    jobs = [("etf_btc", lambda: _update_etf(sess, "btc", d, force)), ("etf_eth", lambda: _update_etf(sess, "eth", d, force)),
            ("stable", lambda: _update_stable(sess, d, force)), ("sentiment", lambda: _update_fng(sess, d, force))]
    for asset, product in CB_PRODUCT.items():
        path = coinbase_path(asset, d)
        jobs.append(("coinbase_%s" % asset[:3].lower(),
                     lambda path=path, product=product: _extend_hourly(path, _coinbase_batches(sess, product, _next_hour(path)))))
    for coin in COINS:
        path = coin_path(coin, d)
        jobs.append(("breadth_%s" % coin.lower(),
                     lambda path=path, coin=coin: _extend_hourly(path, _binance_batches(sess, coin + "USDT", _next_hour(path)))))
    for name, job in jobs:
        try:
            out[name] = int(job())
        except Exception as e:                                        # a failed source keeps its old file
            out[name] = "failed: %s" % (str(e)[:120] or type(e).__name__)
        try:
            if log:
                log("sources.market %s: %s" % (name, out[name]))
        except Exception:
            pass
    return out
