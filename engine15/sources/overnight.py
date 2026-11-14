# -*- coding: utf-8 -*-
"""overnight -- one decision card for the S&P 500 cash index: what happened while the cash market was shut.

  overnight  S&P futures overnight   the session from the previous cash close (16:00 New York) to today's
                                     cash open (09:30), read from a nearly-24-hour S&P series

Applies to SPX only (APPLIES). Readings, at every SPX 15m close of the cash session:
  opening gap        today's cash open against yesterday's cash close, in % and in hourly ATRs
  overnight move     the futures move from yesterday's cash close to 09:30, against its 20-session typical size
  overnight range    the futures high and low in that window, put on the cash index's scale; where the open sat
                     in it, where price sits now, and how far the high and low are from price (in hourly ATRs)
  gap fill           how much of the gap has been retraced so far today, and whether yesterday's close was reached
  trend strength     efficiency of the overnight path: net move / distance travelled by the 15m closes
  sessions           the move split into late US (to 18:00 New York), Asia (to 08:00 London) and Europe (to 09:30)

THE NEARLY-24-HOUR SERIES (kept in data/sources/overnight_es_15m.csv, ts_ms = bar OPEN, UTC; closed bars only)
  older   the Dukascopy USA500 index CFD (the read-only Kronos store, C:\\tmp\\kronos\\data\\markets\\SPX\\15m.csv.gz),
          every hour it trades (Sunday 18:00 to Friday 16:15 New York, shut 16:15-18:00), from 2018-11-01
  recent  Yahoo ES=F (E-mini S&P futures, front contract, 15m, about 60 days served), extended by update()
  splice  as extdata.splice does: one ratio, the median ES/CFD close over the 96 common bars at the join, multiplies
          every older CFD price; ES=F is used after the last CFD bar. Later fetches are stitched onto the file by the
          median stored/new close over the bars both have, so a re-served contract (Yahoo swaps the whole 60 days
          to the new contract at a roll) does not leave a step.
  The file's price LEVEL means nothing on its own (a futures level, or a scaled CFD). Every reading is a ratio
  inside one overnight window, put on the cash scale by that window's own basis (below).

BASIS (futures -> cash). The brief asked for the futures/cash ratio at the open. Measured 2 Sep - 10 Nov 2026
(49 sessions, ES=F against ^GSPC), the ratio at the 09:30 open moved +/-0.12% (std; up to 0.29%) from one day to
the next because the cash index's first print is stale, while the ratio at the previous cash close moved 0.02%.
So levels are scaled by the ratio at the PREVIOUS CASH CLOSE (cash close / futures close of the bar ending then),
which is known before the window starts; the ratio at the open is used only to detect a contract roll inside the
window. It is shown as on_basis_pct (futures over cash, % at the previous close).

ROLLS. A step from one futures contract to the next (~+0.5% to +1.1% for ES at 2024-26 rates) inside a window
would read as an overnight move. If the basis at the open differs from the basis at the previous close by more
than ROLL_GUARD, that difference is the step; the trading break inside the window whose price step is nearest
to it (within ROLL_TOL) is taken as where it happened, and the bars before it are moved by the measured basis
change only (a real move across the same break is kept): on_roll = 1. If no break fits, the futures readings
of that day are "no read" (on_roll = 2). The CFD history tracks the cash index and has no rolls, so there a
mismatch that large means stale prices (seen once, 24 Mar 2020, the futures limit-locked) and is "no read" too.

BAD PRINTS. Yahoo's ES=F has bars whose open is a stray print (seen: +2.6% on 30 Oct 2026, high = open). In
continuous trading a bar opens where the last one closed, so an open more than SPIKE_PCT from the previous close
(with no break between them) is set to that close, and a high/low that was the stray open is re-cut.

THE ONE RULE (tests/test_overnight.py): row i uses only what had closed by the close of SPX 15m bar i.
  yesterday's close            the last cash bar of the previous session
  the overnight window         futures bars that CLOSED at or before today's first cash bar opened (09:30)
  basis                        the futures bar that closed at yesterday's cash close
  today's open, gap fill       today's cash bars up to and including bar i
  the typical move             the previous 20 sessions' overnight moves, never today's
  hourly ATR                   data.htf_on_15: an hourly bar counts once it has closed; the gap is measured
                               in the ATR known at the session's first close
No futures bar during the cash session (other than the one ending at the previous close) is read at all.

Live: ES=F runs about 10 minutes behind the clock on Yahoo; the window's last bar (09:15-09:30) is there by
about 09:40, before the first cash close (09:45). Docs: docs/SOURCES_overnight.md. No reading here is claimed
to predict anything.
"""
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data as _data
from .. import indicators as _ind
from ..config import DATA_DIR

# =====================================================================================
# THE ONE CONSTANT BLOCK. Declared once, none tuned against outcomes.
# =====================================================================================
SRC_DIR = os.path.join(DATA_DIR, "sources")       # override per call with src_dir=...
FILE = "overnight_es_15m.csv"
SYMBOL = "ES=F"                                   # Yahoo: E-mini S&P 500 futures, front contract
ASSET = "SPX"
NY, LONDON = "America/New_York", "Europe/London"
BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
HIST_START = "2018-11-01"                         # the engine's SPX history starts 2019-01-02; 20 sessions of warm-up
JOIN_BARS, MIN_OVERLAP = 96, 20                   # the splice ratio: median over the 96 common bars at the join
FRESH_S = 20 * 60                                 # newest stored bar closed less than 20 minutes ago: nothing to fetch
RETRY_S, RETRY_SHUT_S = 10 * 60, 60 * 60          # at most one request per 10 minutes (60 while the futures are shut)
LONG_FETCH_S = 4 * 86400                          # a store older than 4 days asks Yahoo for 60 days, else 5
SPIKE_PCT = 0.25                                  # an open this far from the previous close, no break between: a stray print
MAX_EDGE_MS = 30 * 60000                          # the futures price at the previous close / at the open may be <= 30 min old
MIN_BARS = 24                                     # a window needs at least six hours of futures bars
MAX_WINDOW_MS = 100 * HOUR_MS                     # longer than a holiday weekend (Fri 16:00 -> Tue 09:30 = 89.5 h): a data hole
ROLL_GUARD = 0.0040                               # basis at the open vs at the previous close: 0.40% (no-roll max seen 0.29%)
ROLL_TOL = 0.0050                                 # a break's price step within 0.50% of that change is taken as the roll
GAP_MIN_PCT = 0.05                                # a gap under 0.05% has nothing to fill: no fill read
ATR_N = 14                                        # Wilder ATR(14) of the 1-hour chart, the engine's yardstick
GAP_UNIT_ATR = 2.0                                # on_gap: a gap of 2 hourly ATRs = 1.0
MOVE_UNIT = 2.0                                   # on_move: twice the typical overnight move = 1.0
TYP_N, TYP_MIN = 20, 10                           # typical move: mean |move| of the previous 20 sessions (10 to start)
ER_UNIT = 0.5                                     # on_trend: an efficiency ratio of 0.5 = 1.0 (a random walk is ~0.1)
CLIP = 1.5                                        # gap, position and move features are clipped at +/-1.5
CASH_OPEN_MIN, CASH_CLOSE_MIN = 9 * 60 + 30, 16 * 60
# =====================================================================================

GROUPS = OrderedDict([
    ("overnight", ("S&P futures overnight", ["on_gap", "on_fill", "on_pos", "on_move", "on_trend"])),
])
APPLIES = {"overnight": (ASSET,)}
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
# readable columns for the journal (NaN = no read). Prices are on the cash index's scale.
RAW = ["on_close", "on_atr1h",                                   # the bar's cash close; hourly ATR(14), in points
       "on_prev_close", "on_open", "on_gap_pct", "on_gap_atr",   # yesterday's close, today's open, the gap
       "on_high_px", "on_low_px", "on_range_pct",                # overnight high / low (cash scale) and range in %
       "on_open_pos_pct",                                        # where the futures sat in that range at 09:30, 0-100
       "on_move_pct", "on_typical_pct", "on_move_x", "on_er",    # overnight move, its 20-session typical size, ratio; efficiency
       "on_late_pct", "on_asia_pct", "on_europe_pct",            # the move by session
       "on_fill_pct", "on_filled", "on_fill_bars",               # gap retraced so far today (0-100), reached (0/1), after N bars
       "on_high_atr", "on_low_atr", "on_pos_pct",                # high above / low below price in ATRs; price in the range, %
       "on_basis_pct", "on_roll", "on_bars", "on_hours", "on_src"]
#        futures over cash at the previous close (%); 0 none / 1 roll removed / 2 roll suspected (no read);
#        futures bars in the window; window length in hours; 0 = Dukascopy CFD, 1 = Yahoo ES=F
SERIES_COLS = ["ts_ms", "open", "high", "low", "close", "volume", "src"]
OHLC = ["open", "high", "low", "close"]


def _now():
    """The clock, in one place (the tests move it)."""
    return time.time()


# ------------------------------------------------------------------ storage
def path_for(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, FILE)


_cache = {}


def _empty():
    idx = pd.DatetimeIndex([], tz="UTC", name="open_time")
    return pd.DataFrame(dict((c, pd.Series(dtype=float, index=idx)) for c in SERIES_COLS[1:]), index=idx)


def load_series(src_dir=None):
    """-> the stored nearly-24h series, indexed by bar OPEN time (UTC); empty when there is no file.
    Cached per process on the file's size and modification time."""
    path = path_for(src_dir)
    if not os.path.exists(path):
        return _empty()
    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    if _cache.get("key") == key:
        return _cache["frame"]
    d = pd.read_csv(path)
    for c in SERIES_COLS:
        if c not in d:
            d[c] = np.nan
    d = d[SERIES_COLS].dropna(subset=["ts_ms", "close"])
    d = d[d["ts_ms"] % BAR_MS == 0].drop_duplicates("ts_ms", keep="last").sort_values("ts_ms")
    f = d[SERIES_COLS[1:]].astype(float)
    f.index = pd.DatetimeIndex(pd.to_datetime(d["ts_ms"].values.astype("int64"), unit="ms", utc=True), name="open_time")
    _cache.clear()
    _cache.update({"key": key, "frame": f})
    return f


def _write(frame, src_dir=None):
    path = path_for(src_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = frame[SERIES_COLS[1:]].copy()
    out[OHLC] = out[OHLC].round(4)
    out.insert(0, "ts_ms", _data.to_ms(frame.index))
    tmp = path + ".tmp"
    out.to_csv(tmp, index=False)
    for attempt in range(5):                                         # Windows: a reader may hold the file briefly
        try:
            os.replace(tmp, path)
            return len(out)
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5 + attempt)


# ------------------------------------------------------------------ network (update only)
def _yahoo(rng, now=None):
    """Closed ES=F 15m bars from Yahoo's chart API (one request, browser User-Agent, 30 s timeout, no key),
    through extdata's closed-bar rules. Raises on any failure."""
    from .. import extdata
    payload = extdata.fetch_chart(SYMBOL, rng)
    df, info = extdata.parse_chart(payload, now=now)
    df = df[OHLC + ["volume"]].astype(float)
    df["src"] = 1.0
    return df, info


def splice(duka, es, join_bars=JOIN_BARS):
    """Dukascopy CFD below (times one ratio), ES=F after the last CFD bar. -> (frame, info).
    ratio = median ES close / CFD close over the `join_bars` common bars nearest the join (extdata.splice's rule,
    with the CFD kept wherever it exists: it tracks the cash index and has no contract rolls)."""
    duka = duka[OHLC + ["volume"]].astype(float).copy()
    duka["src"] = 0.0
    if not len(es):
        return duka, {"splice_ratio": None, "overlap_bars": 0, "join": None}
    both = es.index.intersection(duka.index)
    if len(both) >= MIN_OVERLAP:
        r = (es["close"].reindex(both) / duka["close"].reindex(both)).astype(float)
        ratio = float(r.iloc[-join_bars:].median())
    else:                                                            # no overlap: a hole between them, level unknown
        ratio = 1.0
    duka[OHLC] = duka[OHLC] * ratio
    after = es[es.index > duka.index[-1]] if len(duka) else es
    out = pd.concat([duka, after])
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out, {"splice_ratio": ratio, "overlap_bars": int(len(both)),
                 "join": str(after.index[0]) if len(after) else None}


def stitch(old, new):
    """Append the bars of `new` newer than the last stored one, scaled by the median old/new close over the
    (up to 96 most recent) bars both have, so a contract Yahoo re-served does not leave a step. -> (frame, added, ratio)."""
    both = new.index.intersection(old.index)
    ratio = 1.0
    if len(both) >= 4:
        r = (old["close"].reindex(both) / new["close"].reindex(both)).astype(float).iloc[-JOIN_BARS:]
        ratio = float(r.median())
    add = new[new.index > old.index[-1]].copy() if len(old) else new.copy()
    if not len(add):
        return old, 0, ratio
    add[OHLC] = add[OHLC] * ratio
    return pd.concat([old, add[SERIES_COLS[1:]]]), int(len(add)), ratio


def build(log=print, src_dir=None):
    """Make the file from scratch: Dukascopy CFD from HIST_START, ES=F's last 60 days on top. -> rows written.
    Falls back to ES=F alone if the Kronos store is not readable; raises if both sources fail."""
    from .. import extdata
    try:
        duka = extdata.read_dukascopy(ASSET, start=HIST_START)
    except Exception as e:
        duka = None
        log("sources.overnight: Dukascopy store not readable (%s: %s); ES=F only" % (type(e).__name__, str(e)[:80]))
    try:
        es, _info = _yahoo("60d")
    except Exception as e:
        if duka is None:
            raise
        es = _empty()
        log("sources.overnight: ES=F not fetched (%s); Dukascopy only" % (str(e)[:80],))
    if duka is None or not len(duka):
        if not len(es):
            raise RuntimeError("no bars from either source")
        frame, info = es, {"splice_ratio": None}
    else:
        frame, info = splice(duka, es)
    n = _write(frame, src_dir)
    log("sources.overnight: wrote %d bars %s .. %s (splice ratio %s over %s common bars)"
        % (n, frame.index[0], frame.index[-1], info.get("splice_ratio"), info.get("overlap_bars")))
    return n


def futures_open(when_s):
    """CME equity futures hours, New York time: Sunday 18:00 to Friday 17:00, shut 17:00-18:00 each day."""
    t = pd.Timestamp(when_s, unit="s", tz="UTC").tz_convert(NY)
    wd, mins = t.dayofweek, t.hour * 60 + t.minute
    if wd == 5 or (wd == 6 and mins < 18 * 60) or (wd == 4 and mins >= 17 * 60):
        return False
    return not (17 * 60 <= mins < 18 * 60)


_last_try = [0.0]


def _update(src_dir, log):
    path = path_for(src_dir)
    if not os.path.exists(path):
        _last_try[0] = _now()
        return build(log=log, src_dir=src_dir)
    old = load_series(src_dir)
    if not len(old):
        _last_try[0] = _now()
        return build(log=log, src_dir=src_dir)
    now = _now()
    newest_close = _data.to_ms(old.index[-1:])[0] / 1000.0 + BAR_MS / 1000.0
    if now - newest_close < FRESH_S:
        return len(old)                                              # fresh: no request
    wait = RETRY_S if futures_open(now) else RETRY_SHUT_S
    if now - max(os.path.getmtime(path), _last_try[0]) < wait:
        return len(old)                                              # asked recently: nothing new is likely
    _last_try[0] = now
    new, _info = _yahoo("60d" if now - newest_close > LONG_FETCH_S else "5d")
    both, added, ratio = stitch(old, new)
    if not added:
        return len(old)
    if abs(ratio - 1.0) > 1e-4:
        log("sources.overnight: ES=F re-served at another level (contract roll?); new bars scaled by %.6f" % ratio)
    return _write(both, src_dir)


def update(log=print, src_dir=None):
    """Keep data/sources/overnight_es_15m.csv fresh: built once (Dukascopy + 60 days of ES=F), then extended with
    ES=F only when the newest bar is stale. -> {"overnight_ES": rows on disk, or "failed: <reason>"}. Never raises."""
    out = OrderedDict()
    key = "overnight_ES"
    try:
        out[key] = int(_update(src_dir, log))
    except Exception as e:                                           # a failed fetch keeps the old file and says why
        out[key] = "failed: %s" % (str(e) or type(e).__name__)[:160]
    try:
        log("sources.overnight %s: %s" % (key, out[key]))
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ reading the series
def repair(ms, o, h, l, c):
    """Stray opens (see the module docstring), fixed in copies; uses only the bar before. -> (o, h, l, n_fixed)."""
    o, h, l = o.copy(), h.copy(), l.copy()
    if len(ms) < 2:
        return o, h, l, 0
    k = np.flatnonzero((np.diff(ms) == BAR_MS) & (np.abs(o[1:] / c[:-1] - 1.0) * 100.0 > SPIKE_PCT)) + 1
    for i in k:
        bad, good = o[i], c[i - 1]
        o[i] = good
        if h[i] == bad:
            h[i] = max(good, c[i])
        if l[i] == bad:
            l[i] = min(good, c[i])
        h[i], l[i] = max(h[i], o[i], c[i]), min(l[i], o[i], c[i])
    return o, h, l, int(len(k))


def _instants(days, hour, zone):
    """Local calendar days (int days since 1970) at a wall-clock hour of a zone -> epoch ms."""
    naive = pd.to_datetime(np.asarray(days, dtype="int64") * DAY_MS + int(hour * HOUR_MS), unit="ms")
    return _data.to_ms(pd.DatetimeIndex(naive).tz_localize(zone))


def _hbars(b):
    agg = b.resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


SESSION_COLS = ["prev_close", "open", "gap_pct", "hours", "high", "low", "range_pct", "open_pos", "move_pct",
                "er", "late_pct", "asia_pct", "europe_pct", "basis_pct", "roll", "bars", "src", "ratio"]


def sessions(cash, fut):
    """Per cash session: yesterday's close, today's open, and the overnight window read from the futures.
    cash: frame with ms/o/h/l/c arrays (one session = one New York date); fut: the same for the futures (repaired).
    -> dict of arrays, one value per session (NaN = no read)."""
    S = len(cash["first"])
    out = dict((k, np.full(S, np.nan)) for k in SESSION_COLS)
    ms, o, c = cash["ms"], cash["o"], cash["c"]
    first, last = cash["first"], cash["last"]
    Fms, Fo, Fh, Fl, Fc, Fs = fut["ms"], fut["o"], fut["h"], fut["l"], fut["c"], fut["src"]
    nF = len(Fms)
    day0 = cash["day"][first]
    asia = _instants(day0 - 1, 18, NY)                               # 18:00 New York the calendar day before
    europe = _instants(day0, 8, LONDON)                              # 08:00 London on the day
    for s in range(1, S):
        pc, pct = c[last[s - 1]], ms[last[s - 1]] + BAR_MS           # yesterday's close and when it closed
        op, opt = o[first[s]], ms[first[s]]                          # today's first cash bar opens at opt
        out["prev_close"][s], out["open"][s] = pc, op
        out["gap_pct"][s] = 100.0 * (op / pc - 1.0)
        out["hours"][s] = (opt - pct) / float(HOUR_MS)
        if opt - pct > MAX_WINDOW_MS or nF == 0:
            continue
        a = int(np.searchsorted(Fms, pct, "left"))                   # first futures bar opening at/after the close
        b = int(np.searchsorted(Fms, opt - BAR_MS, "right"))         # bars that closed by the open: [a, b)
        p = int(np.searchsorted(Fms, pct - BAR_MS, "right")) - 1     # the bar that closed at yesterday's close
        q = b - 1                                                    # the bar that closed at 09:30
        out["bars"][s] = max(b - a, 0)
        if b - a < MIN_BARS or p < 0 or q < a:
            continue
        if Fms[p] + BAR_MS < pct - MAX_EDGE_MS or Fms[q] + BAR_MS < opt - MAX_EDGE_MS:
            continue
        wc, wh, wl = Fc[a:b].copy(), Fh[a:b].copy(), Fl[a:b].copy()
        p0 = Fc[p]
        basis = pc / p0                                              # cash per futures point at yesterday's close
        delta = (op / wc[-1]) / basis - 1.0                          # the basis at the open against it
        roll = 0.0
        if abs(delta) > ROLL_GUARD:
            jump = 1.0 / (1.0 + delta) - 1.0                         # the step the futures took against the cash index
            ks = np.arange(a, b)
            holes = ks[(Fms[ks] - Fms[ks - 1]) > BAR_MS]             # bars that open after a break
            if len(holes) and Fs[q] != 0:                            # the CFD has no contracts: a mismatch there is stale prices
                steps = Fo[holes] / Fc[holes - 1] - 1.0
                j = int(np.argmin(np.abs(steps - jump)))             # the break whose step looks most like it
                if abs(steps[j] - jump) < ROLL_TOL:
                    m = int(holes[j]) - a                            # bars before the step: the old contract
                    wc[:m] *= 1.0 + jump                             # only the basis change is removed, so a real
                    wh[:m] *= 1.0 + jump                             # move across the same break is kept
                    wl[:m] *= 1.0 + jump
                    p0 *= 1.0 + jump
                    basis = pc / p0
                    roll = 1.0
            if roll == 0.0:
                out["roll"][s] = 2.0                                 # a step it cannot place: no futures read today
                continue
        hi, lo, fo = float(wh.max()), float(wl.min()), float(wc[-1])
        travelled = abs(wc[0] - p0) + float(np.abs(np.diff(wc)).sum())

        def price_at(t_ms):                                          # the last futures close at or before t_ms
            i = int(np.searchsorted(Fms, t_ms - BAR_MS, "right")) - 1
            return p0 if i < a else fo if i > q else float(wc[i - a])

        pa, pe = price_at(asia[s]), price_at(europe[s])
        out["high"][s], out["low"][s] = hi * basis, lo * basis
        out["range_pct"][s] = 100.0 * (hi / lo - 1.0)
        out["open_pos"][s] = 100.0 * (fo - lo) / (hi - lo) if hi > lo else np.nan
        out["move_pct"][s] = 100.0 * (fo / p0 - 1.0)
        out["er"][s] = (fo - p0) / travelled if travelled > 0 else 0.0
        out["late_pct"][s] = 100.0 * (pa / p0 - 1.0)
        out["asia_pct"][s] = 100.0 * (pe / pa - 1.0)
        out["europe_pct"][s] = 100.0 * (fo / pe - 1.0)
        out["basis_pct"][s] = 100.0 * (1.0 / basis - 1.0)
        out["roll"][s], out["src"][s], out["ratio"][s] = roll, Fs[q], basis
    return out


def _cash_arrays(bars):
    b = bars[OHLC].astype(float)
    if not b.index.is_monotonic_increasing or b.index.has_duplicates:
        b = b[~b.index.duplicated(keep="last")].sort_index()
    loc = b.index.tz_convert(NY)
    mins = np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
    b = b[(np.asarray(loc.dayofweek) < 5) & (mins >= CASH_OPEN_MIN) & (mins < CASH_CLOSE_MIN)]   # cash-session bars only
    ms = _data.to_ms(b.index)
    day = _data.to_ms(b.index.tz_convert(NY).tz_localize(None)) // DAY_MS
    new = np.concatenate([[True], day[1:] != day[:-1]]) if len(day) else np.zeros(0, dtype=bool)
    first = np.flatnonzero(new)
    last = np.concatenate([first[1:] - 1, [len(day) - 1]]) if len(first) else first
    return {"b": b, "ms": ms, "day": day, "sid": np.cumsum(new) - 1, "first": first, "last": last,
            "o": b["open"].values, "h": b["high"].values, "l": b["low"].values, "c": b["close"].values}


def _fut_arrays(fut):
    f = fut
    if not f.index.is_monotonic_increasing or f.index.has_duplicates:
        f = f[~f.index.duplicated(keep="last")].sort_index()
    ms = _data.to_ms(f.index)
    o, h, l, c = (f[k].values.astype(float) for k in OHLC)
    o, h, l, fixed = repair(ms, o, h, l, c)
    src = f["src"].values.astype(float) if "src" in f else np.full(len(f), np.nan)
    return {"ms": ms, "o": o, "h": h, "l": l, "c": c, "src": src, "fixed": fixed}


def _read(cash, fut, out):
    """Every column of the card on the cash bars (dict of arrays)."""
    b, n, sid, first = cash["b"], len(cash["ms"]), cash["sid"], cash["first"]
    c, h, l = cash["c"], cash["h"], cash["l"]
    ses = sessions(cash, fut)
    atr = _data.htf_on_15(b, "1h", _ind.atr_wilder(_hbars(b), ATR_N)).values.astype(float)
    atr = np.where(np.isfinite(atr) & (atr > 0), atr, np.nan)
    atr0 = atr[first][sid]                                           # the ATR known at the session's first close
    typ = pd.Series(np.abs(ses["move_pct"])).shift(1).rolling(TYP_N, min_periods=TYP_MIN).mean().values
    on = dict((k, ses[k][sid]) for k in SESSION_COLS)
    typ_r = typ[sid]
    pc, op, gap = on["prev_close"], on["open"], on["open"] - on["prev_close"]
    lo_sf = pd.Series(l).groupby(sid).cummin().values               # today so far, this bar included
    hi_sf = pd.Series(h).groupby(sid).cummax().values
    with np.errstate(divide="ignore", invalid="ignore"):
        has_gap = np.isfinite(gap) & (np.abs(on["gap_pct"]) >= GAP_MIN_PCT)
        fill = np.where(gap > 0, (op - lo_sf) / gap, (hi_sf - op) / -gap)
        fill = np.where(has_gap, np.clip(fill, 0.0, 1.0), np.nan)
        reached = np.where(gap > 0, lo_sf <= pc, hi_sf >= pc) & has_gap
        rows = np.arange(n)
        first_hit = pd.Series(np.where(reached, rows, n + 1)).groupby(sid).cummin().values
        gap_atr = gap / atr0
        hi_c, lo_c = on["high"], on["low"]
        pos = (c - lo_c) / (hi_c - lo_c)
        move_x = on["move_pct"] / typ_r
        out["on_gap"] = np.clip(gap_atr / GAP_UNIT_ATR, -CLIP, CLIP)
        out["on_fill"] = -np.sign(gap) * fill                        # the direction of the fill move: - = an up gap filling
        out["on_pos"] = np.clip(2.0 * pos - 1.0, -CLIP, CLIP)
        out["on_move"] = np.clip(move_x / MOVE_UNIT, -CLIP, CLIP)
        out["on_trend"] = np.clip(on["er"] / ER_UNIT, -1.0, 1.0)
        out["on_close"], out["on_atr1h"] = c, atr
        out["on_prev_close"], out["on_open"], out["on_gap_pct"], out["on_gap_atr"] = pc, op, on["gap_pct"], gap_atr
        out["on_high_px"], out["on_low_px"], out["on_range_pct"] = hi_c, lo_c, on["range_pct"]
        out["on_open_pos_pct"] = on["open_pos"]
        out["on_move_pct"], out["on_typical_pct"], out["on_move_x"], out["on_er"] = on["move_pct"], typ_r, move_x, on["er"]
        out["on_late_pct"], out["on_asia_pct"], out["on_europe_pct"] = on["late_pct"], on["asia_pct"], on["europe_pct"]
        out["on_fill_pct"] = 100.0 * fill
        out["on_filled"] = np.where(has_gap, reached.astype(float), np.nan)
        out["on_fill_bars"] = np.where(reached, (first_hit - first[sid] + 1).astype(float), np.nan)
        out["on_high_atr"], out["on_low_atr"] = (hi_c - c) / atr, (c - lo_c) / atr
        out["on_pos_pct"] = 100.0 * pos
        out["on_basis_pct"], out["on_roll"], out["on_bars"] = on["basis_pct"], on["roll"], on["bars"]
        out["on_hours"], out["on_src"] = on["hours"], on["src"]


def features(index15, asset, bars=None, fut=None, src_dir=None):
    """-> frame on index15 (15m bar OPEN times, UTC): every feature named in GROUPS as a float (0.0 = no read,
    never NaN) plus the readable RAW columns (NaN = no read).

    bars: the SPX cash 15m frame (data.load("SPX") when None); fut: the nearly-24h series (the stored file under
    data/sources/ when None). Any asset but SPX is "no read". An index row without a cash bar is "no read".
    A failure is "no read" with the reason in .attrs["errors"]."""
    index15 = pd.DatetimeIndex(index15)
    names = FEATURES + RAW
    at_col = dict((c, j) for j, c in enumerate(names))
    block = np.full((len(index15), len(names)), np.nan, order="F")
    errors = {}
    if asset == ASSET and len(index15):
        try:
            if bars is None:
                bars = _data.load(asset)
            if fut is None:
                fut = load_series(src_dir)
            cash = _cash_arrays(bars)
            if len(cash["ms"]):
                card = {}
                _read(cash, _fut_arrays(fut), card)
                want = _data.to_ms(index15)
                at = np.minimum(np.searchsorted(cash["ms"], want), len(cash["ms"]) - 1)
                hit = cash["ms"][at] == want
                at = at[hit]
                for col, values in card.items():
                    block[hit, at_col[col]] = np.asarray(values, dtype=float)[at]
                if not len(fut):
                    errors["futures"] = "no stored futures series (run update)"
        except Exception as e:                                       # a broken file is "no read", not a crash
            errors["overnight"] = "%s: %s" % (type(e).__name__, str(e)[:160])
            block[:] = np.nan
    feats = block[:, :len(FEATURES)]
    feats[~np.isfinite(feats)] = 0.0
    out = pd.DataFrame(block, index=index15, columns=names, copy=False)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _num(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _px(v):
    return "n/a" if v is None else "{:,.2f}".format(v)


def _pc(v, signed=True):
    return "n/a" if v is None else (("%+.2f%%" if signed else "%.2f%%") % v)


def _read_row(row):
    return dict((k, _num(row, k)) for k in RAW)


def _gap_words(r):
    g = r["on_gap_pct"]
    if g is None:
        return None
    if abs(g) < GAP_MIN_PCT:
        return "opened flat on yesterday's close (%s, %s)" % (_px(r["on_prev_close"]), _pc(g))
    s = "opened %s %s yesterday's close (%s to %s" % (_pc(abs(g), False), "above" if g > 0 else "below",
                                                     _px(r["on_prev_close"]), _px(r["on_open"]))
    if r["on_gap_atr"] is not None:
        s += ", %.1f hourly ATRs" % abs(r["on_gap_atr"])
    return s + ")"


def _fill_words(r):
    if r["on_fill_pct"] is None:
        return None
    if r["on_filled"]:
        bars = r["on_fill_bars"]
        return "the gap has filled (price traded back to %s%s)" % (
            _px(r["on_prev_close"]), "" if bars is None else " within %d bar%s of the open" % (bars, "" if bars == 1 else "s"))
    return "so far today price has retraced at most %.0f%% of the gap (yesterday's close %s not reached)" % (
        r["on_fill_pct"], _px(r["on_prev_close"]))


def _session_words(r):
    parts = [(n, r[k]) for n, k in (("late US", "on_late_pct"), ("Asia", "on_asia_pct"), ("Europe", "on_europe_pct"))]
    if any(v is None for _n, v in parts):
        return None
    big = max(parts, key=lambda p: abs(p[1]))
    return "by session: %s (largest: %s)" % (", ".join("%s %s" % (n, _pc(v)) for n, v in parts), big[0])


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    title = GROUPS["overnight"][0]
    if asset != ASSET:
        return OrderedDict([(title, "Applies to the S&P 500 only.")])
    r = _read_row(row)
    gap = _gap_words(r)
    if gap is None:
        return OrderedDict([(title, "No read: no previous S&P cash close or no cash bar for this close.")])
    s = "The S&P 500 " + gap
    if r["on_move_pct"] is None:
        why = ("a futures contract roll inside the window could not be placed" if r["on_roll"] == 2
               else "no complete futures series for the overnight window")
        s += "; no overnight futures read (%s)" % why
    else:
        s += "; S&P futures moved %s from yesterday's cash close to 09:30" % _pc(r["on_move_pct"])
        if r["on_move_x"] is not None:
            s += " (%.1fx the 20-session typical %s)" % (abs(r["on_move_x"]), _pc(r["on_typical_pct"], False))
        sess = _session_words(r)
        if sess:
            s += ", %s" % sess
        s += "; the overnight range was %s to %s (%s) and the open sat %.0f%% of the way up it" % (
            _px(r["on_low_px"]), _px(r["on_high_px"]), _pc(r["on_range_pct"], False), r["on_open_pos_pct"] or 0.0)
        if r["on_close"] is not None and r["on_high_atr"] is not None:
            s += "; at %s price is %.1f hourly ATRs %s the overnight high and %.1f %s the low" % (
                _px(r["on_close"]), abs(r["on_high_atr"]), "below" if r["on_high_atr"] >= 0 else "above",
                abs(r["on_low_atr"]), "above" if r["on_low_atr"] >= 0 else "below")
    fill = _fill_words(r)
    if fill:
        s += "; " + fill
    return OrderedDict([(title, s + ".")])


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: prices, percentages and counts."""
    title = GROUPS["overnight"][0]
    if asset != ASSET:
        return OrderedDict([(title, [["Applies to", "the S&P 500 only"]])])
    r = _read_row(row)
    fut = r["on_move_pct"] is not None
    levels = "n/a"
    if fut and r["on_close"] is not None and r["on_high_atr"] is not None:
        levels = "high %s (%+.1f ATR from price), low %s (%+.1f ATR)" % (
            _px(r["on_high_px"]), r["on_high_atr"], _px(r["on_low_px"]), -r["on_low_atr"])
    roll = {1.0: " (a contract roll was removed)", 2.0: " (contract roll not placed: no read)"}.get(r["on_roll"], "")
    return OrderedDict([(title, [
        ["Opening gap", _gap_words(r) or "n/a"],
        ["Overnight futures move", "n/a" + roll if not fut else "%s%s%s" % (
            _pc(r["on_move_pct"]), "" if r["on_move_x"] is None else
            ", %.1fx the 20-session typical %s" % (abs(r["on_move_x"]), _pc(r["on_typical_pct"], False)), roll)],
        ["Overnight range (cash scale)", "n/a" if not fut else "%s to %s (%s); open at %.0f%% of it; trend efficiency %.2f" % (
            _px(r["on_low_px"]), _px(r["on_high_px"]), _pc(r["on_range_pct"], False), r["on_open_pos_pct"] or 0.0,
            r["on_er"] or 0.0)],
        ["Overnight high / low as levels", levels],
        ["Gap fill", _fill_words(r) or "no gap to fill"],
        ["Move by session", _session_words(r) or "n/a"],
    ])])
