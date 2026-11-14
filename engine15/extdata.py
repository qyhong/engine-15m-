# -*- coding: utf-8 -*-
"""extdata -- 15-minute bars for the markets that are not on Binance: gold, silver, USDJPY, S&P 500.

Same store and conventions as data.py: data/<asset lower>_15m.csv, a bar keyed by its OPEN time
(UTC), CLOSED at open + 15 minutes, only closed bars ever stored. `taker_buy` is empty here.

Two sources, joined once by build_history (docs/EXTDATA.md has the plain-English account):
  older history   Dukascopy BID 15m candles (the read-only Kronos store), from 2019-01-01
  recent + live   Yahoo's free chart API (about 60 days of 15m bars), extended by update()
Dukascopy prices are multiplied by one ratio so the series has no step where the sources meet.

Nothing here trades and nothing here is read by the engine unless the engine asks for it.
"""
import datetime as dt
import os
import time

import numpy as np
import pandas as pd

from . import data

BAR_MS = 900000
BAR_S = 900
OHLC = ["open", "high", "low", "close"]
NY, LONDON = "America/New_York", "Europe/London"

MARKETS = {
    "XAUUSD": {"name": "Gold", "yahoo": "GC=F", "session": "metal", "decimals": 3},
    "XAGUSD": {"name": "Silver", "yahoo": "SI=F", "session": "metal", "decimals": 5},
    "USDJPY": {"name": "US dollar / Japanese yen", "yahoo": "JPY=X", "session": "fx", "decimals": 5},
    "SPX": {"name": "S&P 500", "yahoo": "^GSPC", "session": "us_cash", "decimals": 3},
    # oil (owner, 11 Nov 2026). Dukascopy CFDs LIGHTCMDUSD / BRENTCMDUSD below, front-month futures from
    # Yahoo on top. Known limit: Yahoo's CL=F / BZ=F roll to the next contract each month, which can
    # leave a step of ~1% in the live series on roll day (not adjusted yet).
    "WTI": {"name": "WTI crude oil", "yahoo": "CL=F", "session": "metal", "decimals": 3},
    "BRENT": {"name": "Brent crude oil", "yahoo": "BZ=F", "session": "ice", "decimals": 3},
}
# Session kinds (all anchored on New York wall time, so they move an hour in UTC with US daylight saving):
#   metal    Sunday 18:00 -> Friday 17:00, closed 17:00-18:00 every day  (winter UTC: 23:00 -> 22:00, break 22:00-23:00)
#   fx       Sunday 17:00 -> Friday 17:00                                (winter UTC: Sunday 22:00 -> Friday 22:00)
#   us_cash  Monday-Friday 09:30-16:00, NYSE holidays shut, 13:00 on its three half days

DUKA_DIR = os.environ.get("ENGINE15_MARKETS", r"C:\tmp\kronos\data\markets")    # read-only
HIST_START = "2019-01-01"          # the same first day as the crypto history (config data_start)
YF_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
YF_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/130.0.0.0 Safari/537.36")
YF_TIMEOUT = 30
YF_PAUSE = 1.0                     # seconds between two Yahoo requests, at least
YF_QUIET = 1200                    # no trade for 20 minutes: the market is closed, its last bars are final
JOIN_BARS = 96                     # the splice ratio is the median over the first 96 bars both sources have
#                                    (one day, right at the join). None = the whole overlap. See splice().
MIN_OVERLAP = 20
VOLUME_NOTE = ("volume is each source's own number: Dukascopy's quoted size before the join, Yahoo's after "
               "(futures contracts for gold and silver, index share volume for the S&P 500, always 0 for USDJPY); "
               "the two are not comparable")

_last_request = [0.0]


def _now():
    """The clock, in one place (the tests move it)."""
    return time.time()


# ------------------------------------------------------------------ clocks
def _tz_ok():
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(NY), ZoneInfo(LONDON)
        return True
    except Exception:                                   # no time-zone data on this machine
        return False


TZ_OK = _tz_ok()


def _sunday(year, month, n):
    """The n-th Sunday of a month (n = -1: the last) -> date."""
    if n > 0:
        first = dt.date(year, month, 1)
        return first + dt.timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))
    last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() + 1) % 7)


def _epoch_ms(day, hour):
    return int(dt.datetime(day.year, day.month, day.day, hour, tzinfo=dt.timezone.utc).timestamp() * 1000)


def _manual_offset_ms(ms, zone):
    """UTC offset without a time-zone database. US rule: second Sunday of March 02:00 to first Sunday
    of November 02:00 local. UK rule: last Sunday of March to last Sunday of October, 01:00 UTC."""
    ms = np.asarray(ms, dtype="int64")
    off = np.full(len(ms), -5 * 3600000 if zone == NY else 0, dtype="int64")
    if not len(ms):
        return off
    years = range(pd.Timestamp(int(ms.min()), unit="ms").year, pd.Timestamp(int(ms.max()), unit="ms").year + 1)
    for y in years:
        if zone == NY:
            start, end = _epoch_ms(_sunday(y, 3, 2), 7), _epoch_ms(_sunday(y, 11, 1), 6)
        else:
            start, end = _epoch_ms(_sunday(y, 3, -1), 1), _epoch_ms(_sunday(y, 10, -1), 1)
        off[(ms >= start) & (ms < end)] += 3600000
    return off


def _local(idx, zone):
    """A UTC index -> the zone's wall-clock time as a naive index."""
    if TZ_OK:
        return idx.tz_convert(zone).tz_localize(None)
    ms = data.to_ms(idx)
    return pd.to_datetime(ms + _manual_offset_ms(ms, zone), unit="ms")


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    j, k = divmod(c, 4)
    m = (a + 11 * h) // 319
    r = (2 * e + 2 * j - k - h + m + 32) % 7
    month = (h - m + r + 90) // 25
    return dt.date(year, month, (h - m + r + month + 19) % 32)


NYSE_SPECIAL = (dt.date(2018, 12, 5), dt.date(2025, 1, 9))      # days of mourning: no rule gives these


def nyse_days(year):
    """-> (days the NYSE cash session is shut, days it shuts at 13:00) for one year, as sets of dates."""
    def nth(month, weekday, n):
        if n > 0:
            first = dt.date(year, month, 1)
            return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
        last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
        return last - dt.timedelta(days=(last.weekday() - weekday) % 7)

    def observed(day):                                  # Saturday -> Friday, Sunday -> Monday
        return day - dt.timedelta(days=1) if day.weekday() == 5 else day + dt.timedelta(days=1) if day.weekday() == 6 else day

    thanksgiving = nth(11, 3, 4)
    shut = {nth(1, 0, 3), nth(2, 0, 3), _easter(year) - dt.timedelta(days=2), nth(5, 0, -1),
            observed(dt.date(year, 7, 4)), nth(9, 0, 1), thanksgiving, observed(dt.date(year, 12, 25))}
    if dt.date(year, 1, 1).weekday() != 5:              # a Saturday New Year is not observed on 31 December
        shut.add(observed(dt.date(year, 1, 1)))
    if year >= 2022:
        shut.add(observed(dt.date(year, 6, 19)))
    shut |= {d for d in NYSE_SPECIAL if d.year == year}
    early = {thanksgiving + dt.timedelta(days=1)}
    early |= {d for d in (dt.date(year, 7, 3), dt.date(year, 12, 24)) if d.weekday() < 4}
    return shut, early - shut


def open_mask(asset, idx, calendar=True, feed=False):
    """Vector form of is_open: one True/False per timestamp of a UTC DatetimeIndex.
    calendar=False ignores the NYSE holiday list (weekly hours only)."""
    kind = MARKETS[asset]["session"]
    loc = _local(idx, NY)
    wd = np.asarray(loc.weekday)
    mins = np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
    if kind == "us_cash":
        m = (wd < 5) & (mins >= 570) & (mins < 960)
        if calendar and len(idx):
            shut, early = set(), set()
            for y in range(int(loc.year.min()), int(loc.year.max()) + 1):
                s, e = nyse_days(y)
                shut |= s
                early |= e
            day = loc.normalize()
            m &= ~np.asarray(day.isin(pd.DatetimeIndex(sorted(shut))))
            m &= ~(np.asarray(day.isin(pd.DatetimeIndex(sorted(early)))) & (mins >= 780))
        return m
    opens = {"metal": 1080, "ice": 1200}.get(kind, 1020)   # Sunday's open, New York minutes
    m = ((wd == 6) & (mins >= opens)) | (wd < 4) | ((wd == 4) & (mins < 1020))
    if kind in ("metal", "ice"):                        # the daily break: 17:00-18:00 (CME), 17:00-20:00 (ICE Brent)
        m &= ~((wd < 4) & (mins >= 1020) & (mins < opens))
    if feed and kind == "fx":                           # Yahoo's FX week starts at London midnight on Monday
        m &= np.asarray(_local(idx, LONDON).weekday) != 6
    return m


def _as_utc(when):
    if isinstance(when, (int, float, np.integer, np.floating)):
        return pd.Timestamp(int(when), unit="ms", tz="UTC")
    ts = pd.Timestamp(when)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def is_open(asset, when_utc, feed=False):
    """Is this market trading at that moment? `when_utc`: a datetime/Timestamp (naive = UTC) or epoch ms.
    feed=True answers for the live Yahoo feed instead of the venue: the same hours, except that
    Yahoo's USDJPY starts each week two hours after the market does (London midnight on Monday).
    Known limits: for gold, silver and USDJPY public holidays are not modelled (Christmas reads open)."""
    return bool(open_mask(asset, pd.DatetimeIndex([_as_utc(when_utc)]), feed=feed)[0])


# ------------------------------------------------------------------ frames
def _frame(ts_ms, o, h, l, c, v):
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, dtype=float)
    df["taker_buy"] = np.nan
    df.index = pd.DatetimeIndex(pd.to_datetime(np.asarray(ts_ms, dtype="int64"), unit="ms", utc=True), name="open_time")
    return df[data.COLS]


def _empty():
    return _frame([], [], [], [], [], [])


def _tidy(asset, df):
    """Round prices to the market's decimals, order, de-duplicate; OHLC order is kept by rounding."""
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[data.COLS].astype(float)
    df[OHLC] = df[OHLC].round(MARKETS[asset]["decimals"])
    df.index = pd.DatetimeIndex(df.index, name="open_time")
    return df


def ohlc_violations(df):
    return int(((df.high < df[["open", "close"]].max(axis=1)) | (df.low > df[["open", "close"]].min(axis=1))
                | (df[OHLC] <= 0).any(axis=1)).sum())


def _save(asset, df):
    for attempt in range(5):                            # Windows: a reader holding the file blocks the rename briefly
        try:
            return data.save(asset, df)
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5 + attempt)


def _stored(asset):
    return data.load(asset) if os.path.exists(data.path_for(asset)) else _empty()


# ------------------------------------------------------------------ Dukascopy (read-only)
def read_dukascopy(asset, start=HIST_START):
    """The Kronos store's 15m candles from `start` on, read in chunks. -> frame in data.COLS."""
    path = os.path.join(DUKA_DIR, asset, "15m.csv.gz")
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    parts = []
    for chunk in pd.read_csv(path, chunksize=100000):
        chunk = chunk[(chunk.ts_ms >= start_ms) & (chunk.ts_ms % BAR_MS == 0)]
        if len(chunk):
            parts.append(chunk)
    if not parts:
        return _empty()
    d = pd.concat(parts).drop_duplicates("ts_ms").sort_values("ts_ms")
    df = _frame(d.ts_ms.values, d.open.values, d.high.values, d.low.values, d.close.values, d.volume.values)
    return df[(df[OHLC] > 0).all(axis=1)]


# ------------------------------------------------------------------ Yahoo
def fetch_chart(symbol, rng):
    """ONE request to Yahoo's chart API -> its JSON. Raises on any failure; callers decide what that means."""
    import requests
    wait = YF_PAUSE - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(YF_URL + symbol, params={"interval": "15m", "range": rng},
                         headers={"User-Agent": YF_UA}, timeout=YF_TIMEOUT)
    finally:
        _last_request[0] = time.time()
    r.raise_for_status()
    return r.json()


def parse_chart(payload, now=None):
    """Yahoo's chart JSON -> (closed 15m bars, info). The closed-bar rules (Kronos S283):
      - Yahoo's LAST element is always the live one (an off-grid tick, the bar still trading, or the
        closing print after a session): it is dropped;
      - a bar counts only once the feed's own last trade time (regularMarketTime; futures run about
        10 minutes late) has passed its end, or the market has been quiet for 20 minutes; and never
        before the clock has passed its end;
      - rows with a null or non-positive price (Yahoo's empty slots and break hours) and rows off the
        15-minute grid are dropped; a null volume is 0 (FX has none).
    info: rmt (the feed's last trade time, s), feed_delay_s, quiet, forming (bars left out as still trading)."""
    now = _now() if now is None else float(now)
    res = payload["chart"]["result"][0]
    meta = res.get("meta") or {}
    try:
        rmt = int(meta.get("regularMarketTime") or now)
    except (TypeError, ValueError):
        rmt = int(now)
    quiet = now - rmt >= YF_QUIET
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0] or {}
    raw = pd.DataFrame({"t": pd.Series(ts, dtype="int64")})
    for k in OHLC + ["volume"]:
        col = list(q.get(k) or [])[:len(ts)]
        raw[k] = pd.to_numeric(pd.Series(col + [None] * (len(ts) - len(col)), dtype=object), errors="coerce")
    raw = raw.iloc[:-1]                                                     # the live element
    raw = raw[raw[OHLC].notna().all(axis=1) & (raw[OHLC] > 0).all(axis=1) & (raw.t % BAR_S == 0)]
    done = ((raw.t + BAR_S <= rmt) | quiet) & (raw.t + BAR_S <= now)
    forming = int((~done).sum())
    raw = raw[done].drop_duplicates("t", keep="last").sort_values("t")
    hi, lo = raw[OHLC].max(axis=1), raw[OHLC].min(axis=1)                    # a high below the close: widen, never invert
    repaired = int(((raw.high < hi) | (raw.low > lo)).sum())
    df = _frame(raw.t.values * 1000, raw.open.values, hi.values, lo.values, raw.close.values, raw.volume.fillna(0).values)
    return df, {"rmt": rmt, "feed_delay_s": round(now - rmt, 1), "quiet": bool(quiet), "forming": forming,
                "repaired": repaired, "fetched_at": now}


def yahoo_bars(asset, rng, now=None):
    """Closed Yahoo bars of one market, inside its weekly trading hours. One request. Raises on failure."""
    payload = fetch_chart(MARKETS[asset]["yahoo"], rng)
    df, info = parse_chart(payload, now=now)
    keep = open_mask(asset, df.index, calendar=False)   # single prints stamped in the daily break / after the close
    info["stray"] = int((~keep).sum())
    return _tidy(asset, df[keep]), info


# ------------------------------------------------------------------ the join
def splice(asset, duka, yahoo, join_bars=JOIN_BARS):
    """Dukascopy below, Yahoo on top, one price level. -> (frame, info).

    ratio = median of yahoo_close / dukascopy_close over the bars both have; every Dukascopy price
    before the first Yahoo bar is multiplied by it; Yahoo is used from its first bar on.
    The median is taken over the FIRST `join_bars` common bars, the ones at the join: a futures
    price (Yahoo's gold and silver) drifts toward spot as the contract ages, so the ratio is not
    one number over two months, and the whole-overlap median would leave a step where the sources
    meet. The whole-overlap median is reported next to it; for a steady pair they are the same."""
    if not len(yahoo):
        raise RuntimeError("%s: Yahoo returned no closed bars" % asset)
    join = yahoo.index[0]
    both = yahoo.index.intersection(duka.index)
    if len(both) < MIN_OVERLAP:
        raise RuntimeError("%s: only %d bars in both sources (Dukascopy ends %s, Yahoo starts %s): "
                           "refresh the Dukascopy store, the join would leave a hole"
                           % (asset, len(both), duka.index[-1] if len(duka) else None, join))
    r = (yahoo.close.reindex(both) / duka.close.reindex(both)).astype(float)
    near = r.iloc[:join_bars] if join_bars else r
    ratio = float(near.median())
    whole = float(r.median())
    old = duka[duka.index < join].copy()
    old[OHLC] = old[OHLC] * ratio
    out = _tidy(asset, pd.concat([old, yahoo]))
    info = {
        "splice_ratio": ratio, "ratio_whole_overlap": whole, "join": str(join), "overlap_bars": int(len(both)),
        "ratio_bars": int(len(near)),
        "mad_join_pct": float((near / ratio - 1).abs().median() * 100),      # agreement where the ratio was taken
        "mad_overlap_pct": float((r / ratio - 1).abs().median() * 100),      # ... and over everything both have
        "drift_pct": float((r.iloc[-len(near):].median() / near.median() - 1) * 100),   # ratio at the end vs at the join
        # where Yahoo's first common bar closes against the adjusted Dukascopy close of the SAME bar: the step
        # the series takes at the join (not the market's own move, nor an overnight gap)
        "join_step_pct": float((r.iloc[0] / ratio - 1) * 100),
        "dukascopy_bars": int(len(old)), "yahoo_bars": int(len(yahoo)),
    }
    return out, info


def _dukascopy_for(asset):
    d = read_dukascopy(asset)
    if MARKETS[asset]["session"] == "us_cash":          # the CFD trades round the clock: keep the cash session only
        d = d[open_mask(asset, d.index)]
    return d


def build_history(asset, log=print):
    """Create data/<asset>_15m.csv from scratch: Dukascopy from 2019 below, Yahoo's last 60 days on top.
    -> report(asset) plus the join's numbers and how late the live feed was. Raises if a source is missing."""
    duka = _dukascopy_for(asset)
    log("%s: Dukascopy %d bars %s .. %s" % (asset, len(duka), duka.index[0], duka.index[-1]))
    yahoo, yinfo = yahoo_bars(asset, "60d")
    log("%s: Yahoo %s %d closed bars %s .. %s (feed %.0f s behind the clock)"
        % (asset, MARKETS[asset]["yahoo"], len(yahoo), yahoo.index[0], yahoo.index[-1], yinfo["feed_delay_s"]))
    df, info = splice(asset, duka, yahoo)
    bad = ohlc_violations(df)
    if bad:
        raise RuntimeError("%s: %d bars break high >= max(open, close) / low <= min(open, close)" % (asset, bad))
    _save(asset, df)
    out = report(asset, df=df, duka=duka)
    out.update(info)
    out.update({"yahoo_feed_delay_s": yinfo["feed_delay_s"], "yahoo_quiet": yinfo["quiet"],
                "yahoo_forming_bars": yinfo["forming"], "yahoo_stray_bars": yinfo["stray"],
                "yahoo_repaired_bars": yinfo["repaired"],
                "newest_closed_age_s": round(yinfo["fetched_at"] - (data.to_ms(df.index)[-1] / 1000.0 + BAR_S), 1)})
    log("%s: wrote %d bars; ratio %.6f over %d bars at the join (whole overlap %.6f, %d bars); "
        "difference after adjustment %.4f%% at the join, %.4f%% over the overlap"
        % (asset, len(df), info["splice_ratio"], info["ratio_bars"], info["ratio_whole_overlap"],
           info["overlap_bars"], info["mad_join_pct"], info["mad_overlap_pct"]))
    return out


ROLL_ASSETS = ("WTI", "BRENT", "XAUUSD", "XAGUSD")   # live feeds are front-month futures that roll
ROLL_MIN = 0.003                                     # a re-served overlap off the stored bars by >= 0.3% = a roll


def roll_adjust(asset, old, new, log=print):
    """Keep the stored series continuous across a futures roll. Yahoo's CL=F / BZ=F / GC=F / SI=F switch
    to the next contract on roll day and re-serve the last days at the NEW contract's prices, so the
    bars Yahoo returns that overlap the stored ones are all off by about the roll spread. When the
    median ratio stored / re-served over the overlap is off by at least ROLL_MIN, the new bars are
    scaled by that ratio (a ratio back-adjustment of the new contract to the stored level), and the
    roll is logged to data/rolls.csv. Without overlap nothing is changed."""
    if asset not in ROLL_ASSETS or not len(new) or not len(old):
        return new
    common = old.index.intersection(new.index)
    if len(common) < 8:
        return new
    ratio = float(np.median(old.loc[common, "close"].values / new.loc[common, "close"].values))
    if not np.isfinite(ratio) or abs(ratio - 1.0) < ROLL_MIN:
        return new
    adj = new.copy()
    adj[OHLC] = adj[OHLC] * ratio
    try:
        p = os.path.join(os.path.dirname(data.path_for(asset)), "rolls.csv")
        head = not os.path.exists(p)
        with open(p, "a", encoding="utf-8") as fh:
            if head:
                fh.write("t_utc,asset,ratio,overlap_bars\n")
            fh.write("%s,%s,%.6f,%d\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), asset, ratio, len(common)))
    except OSError:
        pass
    log("%s: futures roll seen (re-served bars %.2f%% off the stored ones); new bars scaled by %.6f" % (
        asset, (1.0 / ratio - 1.0) * 100, ratio))
    return adj


def update(asset, log=print):
    """Append every bar closed since the last stored one. One Yahoo request (5 days; 60 when the store
    is more than 4 days old). -> (all bars, number of new bars). Never raises on a network failure or
    a broken answer: the stored bars come back with 0."""
    old = _stored(asset)
    if not len(old):
        log("%s: no stored history, run build_history first" % asset)
        return old, 0
    last = old.index[-1]
    try:
        stale = _now() - last.timestamp() > 4 * 86400
        new, info = yahoo_bars(asset, "60d" if stale else "5d")
    except Exception as e:                              # network, HTTP status, a broken or empty answer
        log("%s: update failed, keeping %d stored bars (%s: %s)" % (asset, len(old), type(e).__name__, e))
        return old, 0
    new = roll_adjust(asset, old, new, log=log)
    new = new[new.index > last]
    if not len(new):
        return old, 0
    df = _tidy(asset, pd.concat([old, new]))
    try:
        _save(asset, df)
    except OSError as e:                                # the file is held open elsewhere: the next call appends them
        log("%s: could not write %d new bars, keeping the stored file (%s)" % (asset, len(new), e))
        return old, 0
    return df, int(len(new))


# ------------------------------------------------------------------ the report
def _gaps(asset, df, top=5):
    """Missing 15-minute slots INSIDE trading hours between two stored bars, longest first."""
    ms = data.to_ms(df.index)
    grid = pd.date_range(df.index[0], df.index[-1], freq="15min")
    is_on = open_mask(asset, grid)
    seen = np.cumsum(is_on)
    pos = (ms - ms[0]) // BAR_MS
    inside = np.concatenate([[0], seen[pos[1:] - 1] - seen[pos[:-1]]]) if len(pos) > 1 else np.zeros(len(pos), dtype=int)
    order = np.argsort(-inside, kind="stable")[:top]
    rows = [{"after": str(df.index[i - 1]), "next": str(df.index[i]), "hours": float(inside[i]) / 4.0}
            for i in order if inside[i] > 0]
    expected = int(is_on.sum())
    return {"largest_gap_hours": rows[0]["hours"] if rows else 0.0, "largest_gap_after": rows[0]["after"] if rows else None,
            "top_gaps": rows, "missing_in_session": int(inside.sum()),
            "missing_in_session_share": round(float(inside.sum()) / max(expected, 1), 5),
            "bars_outside_session": int((~is_on[pos]).sum())}


def _find_join(asset, df, duka):
    """Read the join back out of the stored file: the Dukascopy part is the leading run of bars whose
    four prices are Dukascopy's times one constant. -> (ratio, join time) or (None, None)."""
    both = df.index.intersection(duka.index)
    if len(both) < MIN_OVERLAP:
        return None, None
    r = df.loc[both, OHLC] / duka.loc[both, OHLC]
    ratio = float(r.close.iloc[:2000].median())
    same = pd.Series(False, index=df.index)
    same[both] = ((r / ratio - 1).abs().max(axis=1) < 3e-6).values
    after = np.flatnonzero(~same.values)
    return ratio, (str(df.index[after[0]]) if len(after) else None)


def report(asset, df=None, duka=None):
    """What is in the stored file: rows, first/last bar, bars per weekday, typical bars per trading day,
    the splice ratio and join date (read back from the file against Dukascopy), gaps inside trading hours."""
    df = data.load(asset) if df is None else df
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    per_wd = pd.Series(1, index=df.index.weekday).groupby(level=0).sum()
    per_day = pd.Series(1, index=df.index.normalize()).groupby(level=0).sum()
    per_day = per_day[per_day.index.weekday < 5]
    ms = data.to_ms(df.index)
    out = {"asset": asset, "name": MARKETS[asset]["name"], "yahoo_symbol": MARKETS[asset]["yahoo"],
           "rows": int(len(df)), "first": str(df.index[0]), "last": str(df.index[-1]),
           "bars_per_weekday": dict((names[int(k)], int(v)) for k, v in per_wd.items()),
           "typical_bars_per_day": float(per_day.median()),
           "monotone": bool(df.index.is_monotonic_increasing), "duplicates": int(df.index.duplicated().sum()),
           "off_grid": int((ms % BAR_MS != 0).sum()), "ohlc_violations": ohlc_violations(df),
           "volume_note": VOLUME_NOTE, "zoneinfo": TZ_OK}
    out.update(_gaps(asset, df))
    try:
        duka = read_dukascopy(asset) if duka is None else duka
        out["splice_ratio"], out["join"] = _find_join(asset, df, duka)
    except (OSError, ValueError, KeyError) as e:        # the Dukascopy store is not on this machine
        out["splice_ratio"], out["join"] = None, None
        out["splice_note"] = "Dukascopy store not readable (%s)" % type(e).__name__
    return out
