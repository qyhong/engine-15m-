# -*- coding: utf-8 -*-
"""H57 data: free 15-minute history of single US stocks (Dukascopy stock CFDs). PAPER ONLY. Research server.

    python research/h57_data.py probe              which tickers Dukascopy has, and from when (the population rule)
    python research/h57_data.py fetch [TICKER ..]  download the selected tickers (resumable), then build their files
    python research/h57_data.py build [TICKER ..]  build the files from the cached raw downloads only
    python research/h57_data.py clean              delete the raw downloads (after every ticker is built)

Everything lives under research/out/h57_stocks/ (raw/, bars/, probe.json, data.json). Nothing under data/ is read
or written. Requests are strictly sequential over one keep-alive connection, started at least PACE seconds apart.

Files (research/HYPOTHESES.md, H57 "Data"):
  bars/<T>_15m.csv     Dukascopy BID minute candles (flat zero-volume minutes dropped) -> 15-minute bars keyed by open
                       time, US cash hours only (extdata.open_mask("SPX", .., calendar=False), as stocks.fetch_15m),
                       a slot without a traded minute absent; split steps removed; rows opening at or after the seal
                       (2025-11-11 00:00 UTC) never written.
  bars/<T>_1d.csv      daily bars per New York trading date: from the 15-minute bars where they exist, else (days
                       before the minute downloads start) from Dukascopy's hourly candles of the cash-session hours.
"""
import datetime as dt
import http.client
import json
import lzma
import os
import shutil
import struct
import sys
import time
import urllib.parse

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, extdata  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h57_stocks")
RAW = os.path.join(OUT, "raw")
BARS = os.path.join(OUT, "bars")
SEAL = "2025-11-11"
SEAL_MS = int(pd.Timestamp(SEAL, tz="UTC").timestamp() * 1000)
MINUTES_FROM = "2020-10-01"          # minute files from here (the index model's first odds are in 2021: 60-day window)
HOURS_FROM = (2015, 1)               # hourly files (daily bars before the minute data) from here, or the first month
LATEST_FIRST = "2024-11-11"          # a ticker whose 15m history starts later is not usable (the registration)
FIVE = ("NVDA", "ARGX", "MU", "T", "DDOG")
TEN = ("AAPL", "MSFT", "AMZN", "GOOGL", "AVGO", "META", "TSLA", "BRK.B", "JPM", "LLY")
FALLBACK = ("WMT", "ORCL", "V", "MA", "XOM", "NFLX", "COST")
BASE = "https://datafeed.dukascopy.com/datafeed"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"}
PACE = 1.0
ROW = struct.Struct(">IIIIIf")       # seconds from the file's start, open, close, low, high, volume
SCALES = (1000, 100000, 100)
UTC = dt.timezone.utc
_last = [0.0]
_conn = {}
STATS = {"requests": 0, "fetched": 0, "n404": 0, "fails": 0}


def log(*m):
    print(time.strftime("[%H:%M:%S]"), *m, flush=True)


# ------------------------------------------------------------------ pure pieces (tested)
ALIAS = {"META": "FBUSUSD"}         # Meta Platforms' CFD keeps its old name (FB) at Dukascopy


def instrument(ticker):
    """Dukascopy's name of a US stock CFD: NVDA -> NVDAUSUSD, BRK.B -> BRKBUSUSD, META -> FBUSUSD."""
    if ticker.upper() in ALIAS:
        return ALIAS[ticker.upper()]
    return ticker.replace(".", "").replace("-", "").upper() + "USUSD"


def decode(raw, base_ms, scale, max_off_s=32 * 86400):
    """Dukascopy candle file bytes -> list of (ts_ms, o, h, l, c, v); flat zero-volume filler rows dropped."""
    if not raw:
        return []
    dec = lzma.decompress(raw)
    if len(dec) % ROW.size:
        raise ValueError("decompressed size %d is not a multiple of %d" % (len(dec), ROW.size))
    out, prev = [], -1
    for off, o, c, lo, h, v in ROW.iter_unpack(dec):
        if off <= prev or off >= max_off_s:
            raise ValueError("offset %d out of order" % off)
        prev = off
        if v == 0.0 and o == c == lo == h:
            continue
        if not (lo <= min(o, c) and h >= max(o, c) and lo > 0):
            raise ValueError("OHLC broken at offset %d" % off)
        out.append((base_ms + off * 1000, o / scale, h / scale, lo / scale, c / scale, float(v)))
    return out


def to_frame(rows):
    if not rows:
        return pd.DataFrame(columns=data.COLS, index=pd.DatetimeIndex([], tz="UTC", name="open_time"), dtype=float)
    a = np.array(rows, dtype=float)
    df = pd.DataFrame({"open": a[:, 1], "high": a[:, 2], "low": a[:, 3], "close": a[:, 4], "volume": a[:, 5]})
    df["taker_buy"] = np.nan
    df.index = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype("int64"), unit="ms", utc=True), name="open_time")
    return df[data.COLS]


def bucket(df, minutes):
    """Bars -> bars of `minutes` keyed by the bucket's open (epoch-aligned); a bucket with no bar is absent."""
    if not len(df):
        return df
    key = df.index.floor("%dmin" % minutes)
    g = df.groupby(key)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum()})
    out["taker_buy"] = np.nan
    out.index = pd.DatetimeIndex(out.index, name="open_time")
    return out[data.COLS]


def cash15(df):
    """15-minute bars of the US cash session (weekly hours, as stocks.fetch_15m keeps Yahoo's), before the seal."""
    df = df[extdata.open_mask("SPX", df.index, calendar=False)]
    return df[data.to_ms(df.index) < SEAL_MS]


def daily_of(df):
    """Intraday bars -> one bar per New York trading date, keyed by that date's UTC midnight (stocks.parse_daily's key)."""
    if not len(df):
        return df
    day = extdata._local(df.index, extdata.NY).normalize()
    key = pd.DatetimeIndex(pd.to_datetime(np.asarray(day.strftime("%Y-%m-%d"))).tz_localize("UTC"), name="open_time")
    g = df.groupby(key)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum()})
    out["taker_buy"] = np.nan
    out.index = pd.DatetimeIndex(out.index, name="open_time")
    return out[data.COLS]


def cash_hours(df):
    """Hourly bars whose hour overlaps the cash session 09:30-16:00 New York (weekdays)."""
    loc = extdata._local(df.index, extdata.NY)
    h = np.asarray(loc.hour)
    return df[(np.asarray(loc.weekday) < 5) & (h >= 9) & (h < 16)]


def split_factors(index, splits, adjusted_before):
    """Multiplier for prices at each bar: for every split (date, ratio) the source has NOT adjusted, bars before the
    split date are divided by the ratio. splits: [(Timestamp UTC midnight of the NY date the split took effect, ratio)].
    adjusted_before: {date: bool} True when the source already shows the split."""
    f = np.ones(len(index))
    for day, ratio in splits:
        if adjusted_before.get(day):
            continue
        f[np.asarray(index < day)] /= ratio
    return f


def apply_factor(df, f):
    out = df.copy()
    for k in ("open", "high", "low", "close"):
        out[k] = out[k].values * f
    out["volume"] = out["volume"].values / f
    return out


# ------------------------------------------------------------------ network
def http_get(url, timeout=30):
    wait = PACE - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    STATS["requests"] += 1
    u = urllib.parse.urlsplit(url)
    for attempt in range(2):
        conn = _conn.get(u.netloc)
        if conn is None:
            conn = _conn[u.netloc] = http.client.HTTPSConnection(u.netloc, timeout=timeout)
        try:
            conn.request("GET", u.path + ("?" + u.query if u.query else ""), headers=dict(UA, Connection="keep-alive"))
            r = conn.getresponse()
            body = r.read()
            if r.getheader("Connection", "").lower() == "close":
                conn.close()
                _conn.pop(u.netloc, None)
            return r.status, body
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            _conn.pop(u.netloc, None)
            if attempt:
                return -1, repr(e).encode()
            time.sleep(PACE)
    return -1, b""


def cached(url, path, attempts=6):
    """-> (bytes, ok). An empty cached file = a genuine 404."""
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return fh.read(), True
    delays = (0, 4, 10, 20, 40, 60)
    for i in range(attempts):
        if i:
            time.sleep(delays[i])
        st, body = http_get(url)
        if st in (200, 404):
            body = body if st == 200 else b""
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", "wb") as fh:
                fh.write(body)
            os.replace(path + ".tmp", path)
            STATS["fetched" if st == 200 else "n404"] += 1
            return body, True
        log("retry %d %s -> %s" % (i + 1, url.split("/datafeed/")[-1], st))
    STATS["fails"] += 1
    return b"", False


def hour_url(instr, y, m):
    return "%s/%s/%d/%02d/BID_candles_hour_1.bi5" % (BASE, instr, y, m - 1)


def min_url(instr, d):
    return "%s/%s/%d/%02d/%02d/BID_candles_min_1.bi5" % (BASE, instr, d.year, d.month - 1, d.day)


def month_ms(y, m):
    return int(dt.datetime(y, m, 1, tzinfo=UTC).timestamp() * 1000)


def months(a, b):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def hour_path(t, y, m):
    return os.path.join(RAW, t, "1h", "%d-%02d.bi5" % (y, m))


def min_path(t, d):
    return os.path.join(RAW, t, "1m", "%d" % d.year, d.strftime("%Y-%m-%d") + ".bi5")


def hour_rows(t, y, m, scale):
    raw, ok = cached(hour_url(instrument(t), y, m), hour_path(t, y, m))
    return decode(raw, month_ms(y, m), scale) if ok else None


# ------------------------------------------------------------------ probe (availability only; no outcome)
def has_month(t, y, m):
    raw, ok = cached(hour_url(instrument(t), y, m), hour_path(t, y, m))
    if not ok:
        raise RuntimeError("%s %d-%02d: no answer" % (t, y, m))
    return len(decode(raw, month_ms(y, m), 1000)) > 0


def first_month(t, lo=(2012, 1), hi=(2025, 10)):
    """The first month with live hours (binary search; Dukascopy's coverage is continuous once it starts), or None."""
    ms = list(months(lo, hi))
    if not has_month(t, *ms[-1]):
        return None
    a, b = 0, len(ms) - 1
    while a < b:
        c = (a + b) // 2
        if has_month(t, *ms[c]):
            b = c
        else:
            a = c + 1
    return ms[a]


def probe():
    res = {}
    for t in FIVE + TEN + FALLBACK:
        fm = first_month(t)
        res[t] = None if fm is None else "%d-%02d" % fm
        log("probe %s (%s): first month %s" % (t, instrument(t), res[t]))
    ok = lambda t: res.get(t) is not None and res[t] + "-01" <= LATEST_FIRST    # noqa: E731
    five = [t for t in FIVE if ok(t)]
    ten = [t for t in TEN if ok(t)]
    for t in FALLBACK:
        if len(ten) >= 10:
            break
        if ok(t):
            ten.append(t)
    doc = {"first_month": res, "five_tested": five, "five_not_testable": [t for t in FIVE if t not in five],
           "ten": ten, "replaced": [t for t in TEN if t not in ten], "rule": "first 15m month on or before %s" % LATEST_FIRST,
           "probed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requests": dict(STATS)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "probe.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    log("selected: five %s, ten %s, not testable %s" % (five, ten, doc["five_not_testable"]))
    return doc


def selected():
    with open(os.path.join(OUT, "probe.json"), encoding="utf-8") as fh:
        p = json.load(fh)
    return p["five_tested"] + [t for t in p["ten"] if t not in p["five_tested"]], p


# ------------------------------------------------------------------ download
def fetch(t, first):
    """Hourly files from max(first month, HOURS_FROM); minute files of every day with a live hour from MINUTES_FROM."""
    y0, m0 = max(tuple(int(x) for x in first.split("-")), HOURS_FROM)
    hours = []
    for y, m in months((y0, m0), (2025, 11)):
        rows = hour_rows(t, y, m, 1000)
        for p in range(4):                           # Dukascopy sometimes answers 503 for a while
            if rows is not None:
                break
            log("%s %d-%02d: hourly file did not load; again after a pause" % (t, y, m))
            time.sleep(120)
            rows = hour_rows(t, y, m, 1000)
        if rows is None:
            raise RuntimeError("%s %d-%02d: hourly file did not load" % (t, y, m))
        hours += rows
    days = sorted(set(pd.to_datetime([r[0] for r in hours], unit="ms", utc=True).normalize()))
    days = [d for d in days if pd.Timestamp(MINUTES_FROM, tz="UTC") <= d < pd.Timestamp(SEAL, tz="UTC")]
    log("%s: %d hourly rows; %d minute days to fetch" % (t, len(hours), len(days)))
    failed = []
    for k, d in enumerate(days):
        raw, ok = cached(min_url(instrument(t), d), min_path(t, d), attempts=3)
        if not ok:                                   # Dukascopy sometimes answers 503 for a while: later pass
            failed.append(d)
        if k % 250 == 0:
            log("%s: %d / %d days (%s) %s" % (t, k, len(days), d.date(), STATS))
    for p in range(4):                               # the days that did not load, again, after a pause
        if not failed:
            break
        log("%s: %d minute days did not load; pass %d after a pause" % (t, len(failed), p + 2))
        time.sleep(120)
        failed = [d for d in failed if not cached(min_url(instrument(t), d), min_path(t, d), attempts=3)[1]]
    missing = [str(d.date()) for d in failed]
    if missing:
        log("%s: %d minute days never loaded (left absent): %s" % (t, len(missing), missing[:20]))
    return missing


# ------------------------------------------------------------------ Yahoo daily (scale and split check only)
def yahoo_daily(t):
    """Yahoo's daily closes (split-adjusted) and split events. -> (Series of close by NY date midnight UTC, splits)."""
    url = extdata.YF_URL + t.replace(".", "-") + "?interval=1d&period1=1420070400&period2=%d&events=split" % int(time.time())
    # (range=max can come back at 3-month intervals; an explicit period gives daily bars)
    for i in range(4):
        st, body = http_get(url)
        if st == 200:
            break
        time.sleep(5 + 10 * i)
    else:
        raise RuntimeError("%s: Yahoo daily did not load" % t)
    res = json.loads(body)["chart"]["result"][0]
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    day = extdata._local(pd.DatetimeIndex(pd.to_datetime(ts, unit="s", utc=True)), extdata.NY).strftime("%Y-%m-%d")
    close = pd.Series(pd.to_numeric(pd.Series(q.get("close") or [], dtype=object), errors="coerce").values,
                      index=pd.DatetimeIndex(pd.to_datetime(np.asarray(day))).tz_localize("UTC")).dropna()
    close = close[~close.index.duplicated(keep="last")]
    splits = []
    for v in ((res.get("events") or {}).get("splits") or {}).values():
        d = extdata._local(pd.DatetimeIndex([pd.Timestamp(int(v["date"]), unit="s", tz="UTC")]), extdata.NY)[0]
        r = float(v["numerator"]) / float(v["denominator"])
        if r > 0 and abs(r - 1) > 1e-9:
            splits.append((pd.Timestamp(d.strftime("%Y-%m-%d"), tz="UTC"), r))
    return close, sorted(splits)


def build(t, first, yahoo=None):
    """Raw files -> bars/<T>_15m.csv and bars/<T>_1d.csv, scale and splits checked against Yahoo's daily closes."""
    y0, m0 = max(tuple(int(x) for x in first.split("-")), HOURS_FROM)
    hrows = []
    for y, m in months((y0, m0), (2025, 11)):
        p = hour_path(t, y, m)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                hrows += decode(fh.read(), month_ms(y, m), 1000)
    mrows = []
    d1 = os.path.join(RAW, t, "1m")
    for root, _, files in os.walk(d1):
        for f in files:
            if f.endswith(".bi5"):
                d = pd.Timestamp(f[:-4], tz="UTC")
                with open(os.path.join(root, f), "rb") as fh:
                    mrows += decode(fh.read(), int(d.timestamp() * 1000), 1000, max_off_s=86400)
    m1 = to_frame(sorted(mrows))
    b15 = cash15(bucket(m1, 15))
    h1 = to_frame(sorted(hrows))
    h1 = h1[data.to_ms(h1.index) < SEAL_MS]
    first15 = b15.index[0] if len(b15) else pd.Timestamp(SEAL, tz="UTC")
    d_15 = daily_of(b15)
    d_h = daily_of(cash_hours(h1))
    d_h = d_h[d_h.index < first15.normalize()]
    daily = pd.concat([d_h, d_15]).sort_index()
    daily = daily[~daily.index.duplicated(keep="last")]
    close, splits = yahoo if yahoo is not None else yahoo_daily(t)
    both = daily["close"].reindex(close.index).dropna()
    ratio = (close.reindex(both.index) / both)
    # scale: the store is decoded at 1000; the median ratio over the last year says whether another scale applies
    last = ratio[ratio.index >= ratio.index[-1] - pd.Timedelta(days=365)]
    med = float(np.median(last.values))
    scale_fix = 1.0
    for s in SCALES:
        k = 1000.0 / s
        if abs(med / k - 1) < 0.05:
            scale_fix = k
            break
    else:
        raise RuntimeError("%s: Dukascopy / Yahoo close ratio %.4f fits no scale" % (t, med))
    adjusted = {}
    notes = []
    for day, r in splits:
        if day <= daily.index[0] or day > daily.index[-1]:
            continue
        pre = ratio[(ratio.index < day) & (ratio.index >= day - pd.Timedelta(days=10))]
        post = ratio[(ratio.index >= day) & (ratio.index < day + pd.Timedelta(days=10))]
        if not len(pre) or not len(post):
            continue
        jump = float(np.median(pre.values) / np.median(post.values))     # unadjusted source: yahoo/duka drops by 1/r
        adjusted[day] = abs(jump - 1) < 0.2
        notes.append({"date": str(day.date()), "ratio": r, "source_already_adjusted": bool(adjusted[day]),
                      "pre_post_ratio_jump": round(jump, 4)})
    f15 = split_factors(b15.index, splits, adjusted) * scale_fix
    fd = split_factors(daily.index, splits, adjusted) * scale_fix
    b15 = apply_factor(b15, f15)
    daily = apply_factor(daily, fd)
    chk = (close.reindex(daily.index) / daily["close"]).dropna()
    os.makedirs(BARS, exist_ok=True)
    data.save("x", b15, path=os.path.join(BARS, "%s_15m.csv" % t))
    data.save("x", daily, path=os.path.join(BARS, "%s_1d.csv" % t))
    info = {"ticker": t, "instrument": instrument(t), "first_month": first,
            "bars15": int(len(b15)), "first15_utc": str(b15.index[0])[:16] if len(b15) else None,
            "last15_utc": str(b15.index[-1])[:16] if len(b15) else None, "days15": int(len(d_15)),
            "daily": int(len(daily)), "daily_from_hourly": int(len(d_h)),
            "first_daily": str(daily.index[0].date()) if len(daily) else None,
            "scale_fix": scale_fix, "splits": notes,
            "yahoo_close_ratio_after_fix": {"median": round(float(chk.median()), 4),
                                            "p05": round(float(chk.quantile(0.05)), 4),
                                            "p95": round(float(chk.quantile(0.95)), 4)},
            "bars_per_day15_median": float(np.median(b15.groupby(b15.index.normalize()).size())) if len(b15) else None}
    log("%s built: %s" % (t, json.dumps(info)))
    return info


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "probe"
    if cmd == "probe":
        probe()
        return
    if cmd == "clean":
        shutil.rmtree(RAW, ignore_errors=True)
        log("raw downloads deleted")
        return
    tick, p = selected()
    if len(argv) > 1:
        tick = [t for t in argv[1:] if t in tick]
    path = os.path.join(OUT, "data.json")
    doc = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    for t in tick:
        missing = fetch(t, p["first_month"][t]) if cmd == "fetch" else (doc.get(t) or {}).get("minute_days_missing", [])
        doc[t] = build(t, p["first_month"][t])
        doc[t]["minute_days_missing"] = missing
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        os.replace(path + ".tmp", path)
    log("done %s" % STATS)


if __name__ == "__main__":
    main()
