# -*- coding: utf-8 -*-
"""playbook2 -- three standalone rule-based strategy books on 15-minute bars (batch 2). PAPER ONLY.

Owner, 11 Nov 2026: "build all 12" (charter task K). Interface: docs/PLAYBOOK_INTERFACE.md.
Plain-English rules and history: docs/PLAYBOOK2.md. History study: research/playbook2_study.py ->
research/out/playbook2.md / .json.

P3  OPENING RANGE BREAKOUT (H8). At a session open (S&P cash 09:30 New York; London 08:00 for gold,
    silver and USDJPY; Tokyo 09:00 for USDJPY; the US equity open and 00:00 UTC for BTC and ETH) the
    opening range is the first 15 or 30 minutes. The first 15m close outside the range is traded in
    its direction; stop at the opposite side of the range (or its middle); targets 1R / 2R / both /
    the session's realistic reach; flat by the session end (S&P 16:00 New York, others 8 hours).
P4  OVERNIGHT GAP FILL, S&P 500 (H9). At the cash open, a gap from yesterday's 16:00 close inside a
    band (in % or in hourly ATRs) is faded toward the fill, immediately or once the first 15 / 30
    minutes do not extend it; stop beyond the first 15 / 30 minutes' extreme; targets half-way and
    yesterday's close; flat by 16:00. The opposite ("gap and go": the gap holds 30 minutes, trade
    with it) is in the same grid.
P5  SQUEEZE BREAKOUT (H10). Bollinger(20, 2) inside Keltner(20, 1.5 x mean true range) on 15m or 1h
    for at least N bars; on release, trade the first 15m close beyond the squeeze's range (within 8
    bars) or the side of the MACD histogram at release; stop at the squeeze range's opposite side;
    targets 1R / 2R / both / realistic reach; time exit 16 or 32 bars.

THE FRAME (all books, as engine15/playbook.py): closed bars only; the decision is at the close of
bar i and fills at the open of bar i+1 (a fill beyond the stop is not taken); a stop and a target
inside the same bar count as the stop first; a gap through a stop fills at the open; one open trade
per book per asset; $10,000 a trade; the asset's own fee a side (config asset_cost, else cost_side).
A trade needs a stop at least MIN_RISK_FEES one-side fees away (so the round trip costs at most half
of 1R). No position is held through a market break longer than 3 hours (a weekend, the S&P
overnight); a time exit fills at the close of the window's last bar. Target schemes: "1R", "2R"
(everything at that target), "split" (half at 1R, the rest at 2R, the stop moved to the entry from
the bar after 1R fills), "reach" (everything at the realistic-reach target).

The books are recomputed from the bars at every step from a FIXED warm-up anchor (registration minus
WARMUP_DAYS), so they hold no state and the same bars always give the same rows.
"""
import numpy as np
import pandas as pd

from . import data, extdata
from . import indicators as ind
from .config import CFG
from .sources import ltf as _ltf

REGISTERED = "2026-11-11"
STAKE = 10000.0
WARMUP_DAYS = 450
BAR_MS, HOUR_MS, DAY_MS = 900000, 3600000, 86400000
NY, LONDON, TOKYO = "America/New_York", "Europe/London", "Asia/Tokyo"
ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P 500"}

# ---------------------------------------------------------------- fixed constants (declared once, not tuned)
MIN_RISK_FEES = 4.0                # the stop is at least 4 one-side fees from the entry
SEG_GAP_MS = 3 * HOUR_MS           # a break longer than this = the market shut: no position held through it
TYP_N, TYP_MIN = 20, 10            # "typical": the previous 20 sessions of the same kind (10 to start)
ORB_HOURS = 8                      # sessions other than the S&P cash session last 8 hours
SQ_N, SQ_BB_K, SQ_KC_K = 20, 2.0, 1.5
SQ_BREAK_BARS = 8                  # P5 "break": the first close beyond the squeeze range within 8 bars of the release
VOL_N, VOL_SURGE = 20, 1.5         # P5 volume filter: decision bar volume >= 1.5 x the mean of the previous 20 bars
REACH_WIN, REACH_MIN = 2160, 720   # P5 reach: hourly samples, the last 90 days (30 to start), as sources/ltf.py
GAP_MIN_PCT = 0.05                 # an S&P gap under 0.05% has no direction (P3's gap filter)
NO_VOLUME = ("USDJPY",)            # the live FX feed has no volume (always 0): P5's volume filter does not apply

# ---------------------------------------------------------------- sessions (P3)
ORB_SESSIONS = {
    "SPX": (("ny_cash", "New York cash open"),),
    "XAUUSD": (("london", "London open"),),
    "XAGUSD": (("london", "London open"),),
    "USDJPY": (("tokyo", "Tokyo open"), ("london", "London open")),
    "BTCUSDT": (("utc0", "00:00 UTC"), ("us_open", "US equity open")),
    "ETHUSDT": (("utc0", "00:00 UTC"), ("us_open", "US equity open")),
}
SESSION_CLOCK = {"ny_cash": (9, 30, NY), "us_open": (9, 30, NY), "london": (8, 0, LONDON),
                 "tokyo": (9, 0, TOKYO), "utc0": (0, 0, "UTC")}
SESSION_LABELS = [lab for kinds in ORB_SESSIONS.values() for _k, lab in kinds]
SESSION_LABELS = sorted(set(SESSION_LABELS))

# ---------------------------------------------------------------- the variant grids (research/playbook2_study.py)
TARGETS = ("1R", "2R", "split", "reach")
ORB_GRID = [{"or_len": L, "stop": s, "target": t, "filter": None}
            for L in (15, 30) for s in ("far", "mid") for t in TARGETS]                 # stage 1: 16
ORB_FILTERS = ("narrow", "htf", "gap")                                                  # stage 2, on the best base
GAP_BANDS = (("pct", 0.10, 0.50), ("pct", 0.25, 1.00), ("atr", 0.25, 1.00), ("atr", 0.50, 2.00))
GAP_GRID = ([{"mode": "fill", "band": b, "entry": e, "target": t}
             for b in GAP_BANDS for e in ("now", "c15", "c30") for t in ("half", "full", "split")]
            + [{"mode": "go", "band": b, "target": t} for b in GAP_BANDS for t in ("1R", "2R")])   # 36 + 8 = 44
SQ_GRID = [{"tf": tf, "N": N, "dir": d, "target": t, "hold": hd, "filter": None}
           for tf in ("15m", "1h") for N in (6, 12) for d in ("break", "macd") for t in TARGETS for hd in (16, 32)]  # 64
SQ_FILTERS = ("vol", "htf", "session")

# ---------------------------------------------------------------- the registered rules
# Chosen on the FIRST half of history only (research/playbook2_study.py, docs/PLAYBOOK2.md).
# None of the three cleared costs in the second half (docs/PLAYBOOK2.md); each runs forward as a paper
# book only so that the forward record, not the history, gives the verdict.
RULES = {
    "p3_orb": {"or_len": 30, "stop": "far", "target": "2R", "filter": "htf"},
    "p4_gapfill": {"mode": "fill", "band": ("atr", 0.25, 1.00), "entry": "c30", "target": "full"},
    "p5_squeeze": {"tf": "1h", "N": 6, "dir": "break", "target": "2R", "hold": 32, "filter": "session"},
}

BOOKS = {
    "p3_orb": {"title": "Opening range breakout", "hypothesis": "H8", "registered": REGISTERED, "assets": ASSETS},
    "p4_gapfill": {"title": "S&P 500 overnight gap fill", "hypothesis": "H9", "registered": REGISTERED, "assets": ("SPX",)},
    "p5_squeeze": {"title": "Squeeze breakout", "hypothesis": "H10", "registered": REGISTERED, "assets": ASSETS},
}

WHY = ("STOP", "T1", "T2", "TIME", "OPEN")
ST_SKIP, ST_WAIT, ST_OPEN, ST_CLOSED = 0, 1, 2, 3
STATUS = {ST_WAIT: "WAITING", ST_OPEN: "OPEN", ST_CLOSED: "CLOSED"}
K_R, K_PX, K_FRAC = 0, 1, 2        # a target given in R, as a price, or as a fraction of the entry
M_T1, M_T2, M_SPLIT = 0, 1, 2      # everything at T1 / everything at T2 / half and half


def fee_side(asset):
    return float(CFG.get("asset_cost", {}).get(asset, CFG["cost_side"]))


def vname(book, p):
    """A short readable name of a variant."""
    if book == "p3_orb":
        return "OR%d stop-%s %s%s" % (p["or_len"], p["stop"], p["target"], "" if not p.get("filter") else " +" + p["filter"])
    if book == "p4_gapfill":
        b = p["band"]
        band = "%s %.2f-%.2f" % ("gap%" if b[0] == "pct" else "gapATR", b[1], b[2])
        if p["mode"] == "go":
            return "go %s %s" % (band, p["target"])
        return "fill %s %s %s" % (band, p["entry"], p["target"])
    return "%s N%d %s %s hold%d%s" % (p["tf"], p["N"], p["dir"], p["target"], p["hold"],
                                      "" if not p.get("filter") else " +" + p["filter"])


# ---------------------------------------------------------------- clocks
def _local_to_ms(naive, zone):
    """Naive local wall-clock times -> epoch ms (UTC)."""
    naive = pd.DatetimeIndex(naive)
    raw = data.to_ms(naive)
    if zone == "UTC":
        return raw
    if zone == TOKYO:                                                  # Japan keeps no daylight saving: UTC+9
        return raw - 9 * HOUR_MS
    if extdata.TZ_OK:
        return data.to_ms(naive.tz_localize(zone))
    guess = raw - extdata._manual_offset_ms(raw, zone)                 # no time-zone data: the US / UK rules by hand
    return raw - extdata._manual_offset_ms(guess, zone)


def session_windows(kind, first_ms, last_ms):
    """-> (start ms, end ms) of every session of a kind whose local date lies in the span.
    ny_cash / us_open: NYSE trading days (shut days skipped, 13:00 close on half days for ny_cash);
    london / tokyo: Monday-Friday local; utc0: every day."""
    h, m, zone = SESSION_CLOCK[kind]
    d0 = pd.Timestamp(int(first_ms) - 2 * DAY_MS, unit="ms").normalize()
    d1 = pd.Timestamp(int(last_ms) + 2 * DAY_MS, unit="ms").normalize()
    days = pd.date_range(d0, d1, freq="D")
    keep = np.ones(len(days), dtype=bool) if kind == "utc0" else np.asarray(days.weekday < 5)
    early = np.zeros(len(days), dtype=bool)
    if kind in ("ny_cash", "us_open"):
        shut, half = set(), set()
        for y in range(d0.year, d1.year + 1):
            s, e = extdata.nyse_days(y)
            shut |= s
            half |= e
        dd = [x.date() for x in days]
        keep &= np.array([x not in shut for x in dd], dtype=bool)
        early = np.array([x in half for x in dd], dtype=bool)
    days, early = days[keep], early[keep]
    start = _local_to_ms(days + pd.Timedelta(hours=h, minutes=m), zone)
    if kind == "ny_cash":
        end = start + np.where(early, 210, 390) * 60000
    else:
        end = start + ORB_HOURS * HOUR_MS
    return start.astype("int64"), np.asarray(end, dtype="int64")


# ---------------------------------------------------------------- one asset's bars and its cached readings
class Ctx(object):
    def __init__(self, df, asset, now_ms=None):
        if not df.index.is_monotonic_increasing or df.index.has_duplicates:
            df = df[~df.index.duplicated(keep="last")].sort_index()
        cols = [c for c in ("open", "high", "low", "close", "volume", "taker_buy") if c in df.columns]
        self.df = df[cols].astype(float)
        self.asset = asset
        self.o, self.h, self.l, self.c = (np.array(self.df[k].values, dtype=float) for k in ("open", "high", "low", "close"))
        v = np.array(self.df["volume"].values, dtype=float) if "volume" in self.df else np.zeros(len(self.df))
        self.v = np.where(np.isfinite(v), v, 0.0)
        self.ms = data.to_ms(self.df.index)
        self.n = len(self.c)
        last_close = int(self.ms[-1]) + BAR_MS if self.n else 0
        self.now = max(int(now_ms), last_close) if now_ms is not None else last_close
        self.last_seg_done = self.now - last_close >= SEG_GAP_MS
        self.fee = fee_side(asset)
        self._c = {}

    def get(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def seg_end(self):
        """For every bar: the index of the last bar before the next market break (> 3 hours)."""
        def make():
            ends = np.flatnonzero(np.diff(self.ms) > SEG_GAP_MS)
            ends = np.concatenate([ends, [self.n - 1]]).astype(int)
            return ends[np.searchsorted(ends, np.arange(self.n))]
        return self.get("seg_end", make)

    def bias(self):
        """The engine's v5 higher-timeframe bias (evidence.py / engine15.playbook.htf_bias): +1 when the 1h, 4h
        and 1d trend scores are all >= +0.5 and the close is above the 1h EMA50 and the 4h EMA20 and EMA50;
        -1 the mirror; else 0. Higher bars reach a 15m row only once closed (data.htf_on_15)."""
        def make():
            df = self.df
            h1, h4, d1 = data.resample(df, "1h"), data.resample(df, "4h"), data.resample(df, "1D")
            t1 = data.htf_on_15(df, "1h", ind.trend_score(h1["close"])).values
            t4 = data.htf_on_15(df, "4h", ind.trend_score(h4["close"])).values
            td = data.htf_on_15(df, "1D", ind.trend_score(d1["close"])).values
            e50_1h = data.htf_on_15(df, "1h", h1["close"].ewm(span=50, adjust=False, min_periods=50).mean()).values
            e20_4h = data.htf_on_15(df, "4h", h4["close"].ewm(span=20, adjust=False, min_periods=20).mean()).values
            e50_4h = data.htf_on_15(df, "4h", h4["close"].ewm(span=50, adjust=False, min_periods=50).mean()).values
            c = self.c
            with np.errstate(invalid="ignore"):
                up = (t1 >= 0.5) & (t4 >= 0.5) & (td >= 0.5) & (c > e50_1h) & (c > e20_4h) & (c > e50_4h)
                dn = (t1 <= -0.5) & (t4 <= -0.5) & (td <= -0.5) & (c < e50_1h) & (c < e20_4h) & (c < e50_4h)
            return np.where(up, 1, np.where(dn, -1, 0))
        return self.get("bias", make)

    def atr1h(self):
        def make():
            h1 = data.resample(self.df, "1h")
            return np.array(data.htf_on_15(self.df, "1h", ind.atr_wilder(h1, 14)).values, dtype=float)
        return self.get("atr1h", make)

    def london_ny(self):
        """True where the bar opens between 08:00 London and 16:00 New York on a London weekday."""
        def make():
            lon = extdata._local(self.df.index, LONDON)
            nyc = extdata._local(self.df.index, NY)
            lm = np.asarray(lon.hour) * 60 + np.asarray(lon.minute)
            nm = np.asarray(nyc.hour) * 60 + np.asarray(nyc.minute)
            return (lm >= 480) & (nm < 960) & (np.asarray(lon.weekday) < 5)
        return self.get("london_ny", make)

    def vol_ratio(self):
        def make():
            v = pd.Series(np.where(self.v > 0, self.v, np.nan))
            prior = v.shift(1).rolling(VOL_N, min_periods=VOL_N).mean().values
            with np.errstate(invalid="ignore", divide="ignore"):
                return v.values / prior
        return self.get("vol_ratio", make)

    def reach(self, nb):
        """Realistic reach over the next nb bars, as a fraction of price: the median, over the last 90 days of
        hourly samples, of the largest move either way within nb bars (sources/ltf.py's reach, used only once
        each sample is history)."""
        def make():
            with np.errstate(invalid="ignore", divide="ignore"):
                fr = _ltf.forward_reach(self.h, self.l, self.c, nb) / self.c
            sample = np.flatnonzero(self.ms % HOUR_MS == HOUR_MS - BAR_MS)
            med = pd.Series(fr[sample]).rolling(REACH_WIN, min_periods=REACH_MIN).median().values
            known = sample + nb
            k = np.searchsorted(known, np.arange(self.n), side="right") - 1
            out = np.full(self.n, np.nan)
            ok = k >= 0
            out[ok] = med[k[ok]]
            return out
        return self.get(("reach", nb), make)


# ---------------------------------------------------------------- P3: opening range breakout
def orb_events(ctx, or_len):
    """Every session's opening range and its first close outside it. -> dict of arrays, one per session."""
    def make():
        n, ms, o, h, l, c = ctx.n, ctx.ms, ctx.o, ctx.h, ctx.l, ctx.c
        k = or_len // 15
        cols = dict((x, []) for x in ("kind", "start", "end", "a", "hi", "lo", "p0", "dec", "side", "last",
                                      "done", "width", "exc", "gap"))
        kinds = ORB_SESSIONS.get(ctx.asset, ())
        if not n:
            return dict((x, np.array(v)) for x, v in cols.items())
        for kc, (kind, _label) in enumerate(kinds):
            starts, ends = session_windows(kind, ms[0], ms[-1])
            A = np.searchsorted(ms, starts)
            B = np.searchsorted(ms, ends)
            for s in range(len(starts)):
                a, st, en, b_end = int(A[s]), int(starts[s]), int(ends[s]), int(B[s])
                if a + k - 1 >= n or ms[a] != st or ms[a + k - 1] != st + (k - 1) * BAR_MS:
                    continue                                           # the opening range is not complete on file
                hi, lo = float(h[a:a + k].max()), float(l[a:a + k].min())
                if not hi > lo:
                    continue
                p0 = float(c[a + k - 1])
                done = ctx.now >= en or b_end < n
                seg = c[a + k:b_end]
                brk = np.flatnonzero((seg > hi) | (seg < lo))
                dec = a + k + int(brk[0]) if len(brk) else -1
                side = (1 if c[dec] > hi else -1) if dec >= 0 else 0
                exc = np.nan
                if done and b_end > a + k:
                    exc = max(float(h[a + k:b_end].max()) - p0, p0 - float(l[a + k:b_end].min())) / p0
                gap = (o[a] / c[a - 1] - 1.0) if (a > 0 and ms[a] - ms[a - 1] > SEG_GAP_MS) else np.nan
                for x, val in (("kind", kc), ("start", st), ("end", en), ("a", a), ("hi", hi), ("lo", lo), ("p0", p0),
                               ("dec", dec), ("side", side), ("last", b_end - 1), ("done", done),
                               ("width", (hi - lo) / p0), ("exc", exc), ("gap", gap)):
                    cols[x].append(val)
        E = dict((x, np.array(v)) for x, v in cols.items())
        if not len(E["start"]):
            return E
        order = np.argsort(E["start"], kind="stable")
        E = dict((x, v[order]) for x, v in E.items())
        typ, rch = np.full(len(order), np.nan), np.full(len(order), np.nan)
        for kc in np.unique(E["kind"]):                                # the previous 20 sessions of the same kind
            m = E["kind"] == kc
            typ[m] = pd.Series(E["width"][m]).shift(1).rolling(TYP_N, min_periods=TYP_MIN).median().values
            rch[m] = pd.Series(E["exc"][m]).shift(1).rolling(TYP_N, min_periods=TYP_MIN).median().values
        E["typ_width"], E["reach"] = typ, rch
        return E
    return ctx.get(("orb", or_len), make)


def _targets_spec(target, reach_frac):
    """(t1 kind, t1 value, t2 kind, t2 value, mode) arrays for a target scheme."""
    m = len(reach_frac)
    t1k, t1v = np.full(m, K_R), np.ones(m)
    if target == "1R":
        return t1k, t1v, np.full(m, K_R), np.full(m, 2.0), np.full(m, M_T1)
    if target == "2R":
        return t1k, t1v, np.full(m, K_R), np.full(m, 2.0), np.full(m, M_T2)
    if target == "split":
        return t1k, t1v, np.full(m, K_R), np.full(m, 2.0), np.full(m, M_SPLIT)
    if target == "reach":
        return t1k, t1v, np.full(m, K_FRAC), np.asarray(reach_frac, dtype=float), np.full(m, M_T2)
    raise ValueError(target)


def orb_setups(ctx, p):
    E = orb_events(ctx, p["or_len"])
    if not len(E.get("start", [])):
        return _empty_setups()
    sel = E["dec"] >= 0
    f = p.get("filter")
    with np.errstate(invalid="ignore"):
        if f == "narrow":
            sel &= E["width"] < E["typ_width"]
        elif f == "htf":
            b = ctx.bias()
            sel &= b[np.maximum(E["dec"], 0)] == E["side"]
        elif f == "gap":                                               # S&P only; the other markets are unfiltered
            if ctx.asset == "SPX":
                g = E["gap"]
                sel &= np.isfinite(g) & (np.abs(g) * 100.0 >= GAP_MIN_PCT) & (np.sign(g) == E["side"])
        elif f:
            raise ValueError(f)
        if p["target"] == "reach":
            sel &= np.isfinite(E["reach"])
    ev = np.flatnonzero(sel)
    side = E["side"][ev].astype(int)
    hi, lo = E["hi"][ev], E["lo"][ev]
    stop = np.where(side > 0, lo, hi) if p["stop"] == "far" else (hi + lo) / 2.0
    t1k, t1v, t2k, t2v, mode = _targets_spec(p["target"], E["reach"][ev])
    dec = E["dec"][ev].astype(int)
    done = E["done"][ev].astype(bool)
    can_wait = ~done & (ctx.ms[np.minimum(dec, ctx.n - 1)] + BAR_MS < E["end"][ev])
    return {"i": dec, "side": side, "stop": stop, "t1k": t1k, "t1v": t1v, "t2k": t2k, "t2v": t2v, "mode": mode,
            "last": E["last"][ev].astype(int), "done": done, "can_wait": can_wait, "ev": ev,
            "lab": E["kind"][ev].astype(int)}


# ---------------------------------------------------------------- P4: S&P overnight gap fill
def gap_days(ctx):
    """Every S&P cash session: yesterday's close, today's open, the gap in % and in hourly ATRs."""
    def make():
        n, ms, o, c = ctx.n, ctx.ms, ctx.o, ctx.c
        loc = extdata._local(ctx.df.index, NY)
        day = data.to_ms(loc.normalize()) // DAY_MS
        mins = np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
        new = np.concatenate([[True], day[1:] != day[:-1]]) if n else np.zeros(0, dtype=bool)
        first = np.flatnonzero(new)
        lastb = np.concatenate([first[1:] - 1, [n - 1]]).astype(int) if len(first) else first
        ok = (first > 0) & (mins[first] == 570)
        ok &= np.r_[False, (ms[first[1:]] - ms[first[1:] - 1]) <= 4.5 * DAY_MS] if len(first) else ok
        a, last = first[ok], lastb[ok]
        pc, op = c[a - 1], o[a]
        atr = ctx.atr1h()[a]
        start = ms[a]
        early = set()
        for y in range(int(pd.Timestamp(int(ms[0]), unit="ms").year), int(pd.Timestamp(int(ms[-1]), unit="ms").year) + 1):
            early |= extdata.nyse_days(y)[1]
        is_early = np.array([pd.Timestamp(int(d) * DAY_MS, unit="ms").date() in early for d in day[a]], dtype=bool)
        end = start + np.where(is_early, 210, 390) * 60000
        done = (last < n - 1) | (ctx.now >= end)
        with np.errstate(invalid="ignore", divide="ignore"):
            return {"a": a, "last": last, "pc": pc, "op": op, "gap_pct": 100.0 * (op / pc - 1.0),
                    "gap_atr": np.abs(op - pc) / np.where(atr > 0, atr, np.nan), "end": end, "done": done}
    return ctx.get("gapdays", make)


def gap_setups(ctx, p):
    if ctx.asset != "SPX" or not ctx.n:
        return _empty_setups()
    G = gap_days(ctx)
    n, o, h, l, c, ms = ctx.n, ctx.o, ctx.h, ctx.l, ctx.c, ctx.ms
    kind, g_lo, g_hi = p["band"]
    size = np.abs(G["gap_pct"]) if kind == "pct" else G["gap_atr"]
    with np.errstate(invalid="ignore"):
        sel = (size >= g_lo) & (size < g_hi)
    a, last, pc, op = G["a"], G["last"], G["pc"], G["op"]
    g = np.sign(op - pc).astype(int)
    a1 = np.minimum(a + 1, n - 1)
    have2 = (a + 1 <= last)                                            # the 09:45 bar exists for this day
    if p["mode"] == "fill":
        side = -g
        w2 = p["entry"] == "c30"
        dec = np.where(w2, a + 1, a)
        sel &= have2 if w2 else np.ones(len(a), dtype=bool)
        hi_w = np.where(w2, np.maximum(h[a], h[a1]), h[a])
        lo_w = np.where(w2, np.minimum(l[a], l[a1]), l[a])
        stop = np.where(g > 0, hi_w, lo_w)                             # beyond the first 15 / 30 minutes' extreme
        filled = np.where(g > 0, lo_w <= pc, hi_w >= pc)
        sel &= ~filled                                                 # the gap has not filled yet
        if p["entry"] == "c15":
            sel &= side * (c[a] - op) > 0                              # the first bar closed back toward the fill
        elif w2:
            sel &= side * (c[a1] - op) > 0                             # still back toward the fill after 30 minutes
        half = (op + pc) / 2.0
        m = len(a)
        t1k, t1v, t2k, t2v = np.full(m, K_PX), half, np.full(m, K_PX), pc.astype(float)
        mode = np.full(m, {"half": M_T1, "full": M_T2, "split": M_SPLIT}[p["target"]])
    else:                                                              # gap and go
        side = g
        dec = a + 1
        sel &= have2
        lo2, hi2 = np.minimum(l[a], l[a1]), np.maximum(h[a], h[a1])
        held = np.where(g > 0, lo2 > pc, hi2 < pc) & (g * (c[a1] - op) > 0)
        sel &= held
        stop = np.where(g > 0, lo2, hi2)
        m = len(a)
        t1k, t1v, t2k, t2v = np.full(m, K_R), np.ones(m), np.full(m, K_R), np.full(m, 2.0)
        mode = np.full(m, M_T1 if p["target"] == "1R" else M_T2)
    sel &= g != 0
    ev = np.flatnonzero(sel)
    dec = dec[ev].astype(int)
    done = G["done"][ev].astype(bool)
    return {"i": dec, "side": side[ev].astype(int), "stop": stop[ev], "t1k": t1k[ev], "t1v": t1v[ev], "t2k": t2k[ev],
            "t2v": t2v[ev], "mode": mode[ev], "last": last[ev].astype(int), "done": done,
            "can_wait": ~done & (ms[np.minimum(dec, n - 1)] + BAR_MS < G["end"][ev]), "ev": ev,
            "lab": (g[ev] < 0).astype(int)}


# ---------------------------------------------------------------- P5: squeeze breakout
def sq_releases(ctx, tf, N):
    """Every squeeze of at least N bars on the timeframe that has released. -> arrays: the 15m row at whose
    close the release is known (d), the squeeze's high / low, its length, MACD histogram side at release."""
    def make():
        if tf == "15m":
            b = ctx.df
        else:
            b = data.resample(ctx.df, "1h")
        bms = data.to_ms(b.index)
        bh, bl = np.array(b["high"].values, dtype=float), np.array(b["low"].values, dtype=float)
        close = b["close"].astype(float)
        mid = close.rolling(SQ_N).mean()
        sd = close.rolling(SQ_N).std(ddof=0)
        kc = SQ_KC_K * ind.true_range(b).rolling(SQ_N).mean()
        valid = (mid.notna() & sd.notna() & kc.notna()).values
        on = valid & ((SQ_BB_K * sd).values < kc.values)
        rows = np.arange(len(on))
        last_off = np.maximum.accumulate(np.where(~on, rows, -1))
        run = np.where(on, rows - last_off, 0)
        rel = np.flatnonzero(on[:-1] & ~on[1:] & valid[1:]) + 1 if len(on) > 1 else np.zeros(0, dtype=int)
        L = run[rel - 1] if len(rel) else rel
        keep = L >= N
        rel, L = rel[keep], L[keep]
        hi = np.array([bh[r - k:r].max() for r, k in zip(rel, L)], dtype=float)
        lo = np.array([bl[r - k:r].min() for r, k in zip(rel, L)], dtype=float)
        hist = _ltf.macd_hist(close).values
        msign = np.sign(hist[rel]) if len(rel) else np.zeros(0)
        if tf == "15m":
            d = rel.astype(int)
        else:                                                          # known at the close of the 1h bar
            d = np.searchsorted(ctx.ms, bms[rel] + HOUR_MS - BAR_MS).astype(int)
        ok = d < ctx.n                                                 # an unfinished 1h bar is not a release yet
        return {"d": d[ok], "hi": hi[ok], "lo": lo[ok], "len": L[ok], "macd": msign[ok], "rel_ms": bms[rel][ok]}
    return ctx.get(("sq", tf, N), make)


def sq_setups(ctx, p):
    R = sq_releases(ctx, p["tf"], p["N"])
    n = ctx.n
    if not len(R["d"]):
        return _empty_setups()
    d, hi, lo = R["d"], R["hi"], R["lo"]
    segE = ctx.seg_end()
    if p["dir"] == "break":
        K = SQ_BREAK_BARS
        J = d[:, None] + np.arange(K)[None, :]
        inw = J <= np.minimum(segE[d], n - 1)[:, None]
        C = ctx.c[np.minimum(J, n - 1)]
        up, dn = inw & (C > hi[:, None]), inw & (C < lo[:, None])
        hit = up | dn
        got = hit.any(axis=1)
        j = hit.argmax(axis=1)
        dec = (d + j)[got]
        side = np.where(up[np.arange(len(d)), j], 1, -1)[got]
        ev = np.flatnonzero(got)
    else:
        side = R["macd"].astype(int)
        ev = np.flatnonzero(side != 0)
        dec, side = d[ev], side[ev]
    hi, lo = hi[ev], lo[ev]
    sel = np.ones(len(ev), dtype=bool)
    f = p.get("filter")
    if f == "vol":
        if ctx.asset not in NO_VOLUME:
            with np.errstate(invalid="ignore"):
                sel &= ctx.vol_ratio()[dec] >= VOL_SURGE
    elif f == "htf":
        sel &= ctx.bias()[dec] == side
    elif f == "session":
        sel &= ctx.london_ny()[dec]
    elif f:
        raise ValueError(f)
    reach = ctx.reach(p["hold"])[dec] if p["target"] == "reach" else np.zeros(len(dec))
    if p["target"] == "reach":
        sel &= np.isfinite(reach)
    k = np.flatnonzero(sel)
    dec, side, hi, lo, ev, reach = dec[k], side[k], hi[k], lo[k], ev[k], reach[k]
    stop = np.where(side > 0, lo, hi)
    t1k, t1v, t2k, t2v, mode = _targets_spec(p["target"], reach)
    e = dec + 1
    se = segE[dec]
    last_hold = e + p["hold"] - 1
    last = np.minimum(last_hold, se)
    seg_finished = (se < n - 1) | ctx.last_seg_done
    done = ((last_hold <= se) & (last_hold <= n - 1)) | ((last_hold > se) & seg_finished)
    can_wait = (e >= n) & (not ctx.last_seg_done)
    hour = (ctx.ms[dec] % DAY_MS) // HOUR_MS
    lab = np.where(hour < 7, 0, np.where(hour < 13, 1, np.where(hour < 20, 2, 3)))
    return {"i": dec.astype(int), "side": side.astype(int), "stop": stop, "t1k": t1k, "t1v": t1v, "t2k": t2k,
            "t2v": t2v, "mode": mode, "last": last.astype(int), "done": done, "can_wait": can_wait, "ev": ev, "lab": lab}


SQ_SESSIONS = ("Asia (00-07 UTC)", "London (07-13 UTC)", "New York (13-20 UTC)", "Late (20-24 UTC)")
GAP_LABELS = ("gap up", "gap down")


def _empty_setups():
    z = np.zeros(0, dtype=int)
    f = np.zeros(0)
    return {"i": z, "side": z, "stop": f, "t1k": z, "t1v": f, "t2k": z, "t2v": f, "mode": z, "last": z,
            "done": np.zeros(0, dtype=bool), "can_wait": np.zeros(0, dtype=bool), "ev": z, "lab": z}


def setups(book, ctx, p):
    if book == "p3_orb":
        return orb_setups(ctx, p)
    if book == "p4_gapfill":
        return gap_setups(ctx, p)
    if book == "p5_squeeze":
        return sq_setups(ctx, p)
    raise ValueError(book)


def labels_for(book, asset):
    """The names behind a setup's `lab` code: the session (P3), the gap's direction (P4), the UTC session (P5)."""
    if book == "p3_orb":
        return [lab for _k, lab in ORB_SESSIONS.get(asset, ())]
    return list(GAP_LABELS if book == "p4_gapfill" else SQ_SESSIONS)


def labels(book, ctx):
    return labels_for(book, ctx.asset)


# ---------------------------------------------------------------- the paper trade (vectorised), then one at a time
def _tgt(kind, val, entry, side, risk):
    return np.where(kind == K_R, entry + side * val * risk, np.where(kind == K_PX, val, entry * (1.0 + side * val)))


def simulate(ctx, S):
    """Trade the setups one at a time. -> dict of arrays over the KEPT setups (index k into S), oldest first:
    k, status, entry, risk, t1, t2, exit, exit_bar, exit_ms, why, t1_hit, r, pnl, fees, gross."""
    n, o, h, l, c, ms, fee = ctx.n, ctx.o, ctx.h, ctx.l, ctx.c, ctx.ms, ctx.fee
    i = np.asarray(S["i"], dtype=int)
    N = len(i)
    side = np.asarray(S["side"], dtype=float)
    stop = np.asarray(S["stop"], dtype=float)
    mode, last = np.asarray(S["mode"], dtype=int), np.asarray(S["last"], dtype=int)
    done = np.asarray(S["done"], dtype=bool)
    e = i + 1
    has_e = e < n
    ec = np.minimum(e, max(n - 1, 0))
    entry = np.where(has_e, o[ec] if n else np.nan, c[np.minimum(i, n - 1)] if n else np.nan)   # waiting: the last close
    with np.errstate(invalid="ignore"):
        risk = side * (entry - stop)
        t1 = _tgt(S["t1k"], S["t1v"], entry, side, risk)
        t2 = _tgt(S["t2k"], S["t2v"], entry, side, risk)
        act = np.where(mode == M_T1, t1, t2)
        good = (risk > 0) & (risk >= MIN_RISK_FEES * fee * np.abs(entry)) & (side * (act - entry) > 0)
        good &= (mode != M_SPLIT) | ((side * (t1 - entry) > 0) & (side * (t2 - t1) > 0))
    status = np.full(N, ST_SKIP)
    status[good & ~has_e & np.asarray(S["can_wait"], dtype=bool)] = ST_WAIT
    sim = np.flatnonzero(good & has_e & (e <= last))
    exit_px, exit_bar, why = np.full(N, np.nan), np.full(N, -1), np.full(N, 4)
    t1_hit = np.zeros(N, dtype=bool)
    f1, p1, f2, p2 = np.zeros(N), np.full(N, np.nan), np.zeros(N), np.zeros(N)
    if len(sim):
        ee, ll = e[sim], last[sim]
        H = int((ll - ee).max()) + 1
        cols = np.arange(H)[None, :]
        J = ee[:, None] + cols
        inw = J <= ll[:, None]
        Jc = np.minimum(J, n - 1)
        sd = side[sim][:, None]
        A = np.where(sd > 0, l[Jc], h[Jc])
        F = np.where(sd > 0, h[Jc], l[Jc])
        O = o[Jc]
        rr = np.arange(len(sim))
        BIG = H + 1

        def first(mask):
            return np.where(mask.any(axis=1), mask.argmax(axis=1), BIG)

        def at(M, j):
            return M[rr, np.minimum(j, H - 1)]

        s1, st1, en1 = side[sim], stop[sim], entry[sim]
        T1, T2, M = t1[sim], t2[sim], mode[sim]
        TA = np.where(M == M_T1, T1, T2)
        js = first(inw & (sd * (A - st1[:, None]) <= 0))
        px_stop = np.where(s1 * (at(O, js) - st1) <= 0, at(O, js), st1)      # a gap through the stop fills at the open
        fin = done[sim]
        end_px = np.where(fin, c[ll], c[n - 1])                               # time exit at the last close / mark
        end_why = np.where(fin, 3, 4)
        end_bar = np.where(fin, ll, n)
        # one target
        jt = first(inw & (sd * (F - TA[:, None]) >= 0))
        px_t = np.where(s1 * (at(O, jt) - TA) >= 0, at(O, jt), TA)
        sf = (js <= jt) & (js < BIG)
        tf = ~sf & (jt < BIG)
        one_p = np.where(sf, px_stop, np.where(tf, px_t, end_px))
        one_w = np.where(sf, 0, np.where(tf, np.where(M == M_T1, 1, 2), end_why))
        one_b = np.where(sf, ee + js, np.where(tf, ee + jt, end_bar))
        # split: half at T1, the rest at T2, the stop at the entry from the bar after T1
        j1 = first(inw & (sd * (F - T1[:, None]) >= 0))
        px1 = np.where(s1 * (at(O, j1) - T1) >= 0, at(O, j1), T1)
        stopA = (js <= j1) & (js < BIG)
        got1 = ~stopA & (j1 < BIG)
        j2 = first(inw & (cols >= j1[:, None]) & (sd * (F - T2[:, None]) >= 0))
        jbe = first(inw & (cols > j1[:, None]) & (sd * (A - en1[:, None]) <= 0))
        px2 = np.where(s1 * (at(O, j2) - T2) >= 0, at(O, j2), T2)
        pxbe = np.where(s1 * (at(O, jbe) - en1) <= 0, at(O, jbe), en1)
        be_first = (j2 != j1) & (jbe <= j2) & (jbe < BIG)
        t2hit = ~be_first & (j2 < BIG)
        leg2_p = np.where(t2hit, px2, np.where(be_first, pxbe, end_px))
        leg2_w = np.where(t2hit, 2, np.where(be_first, 0, end_why))
        leg2_b = np.where(t2hit, ee + j2, np.where(be_first, ee + jbe, end_bar))
        sp = M == M_SPLIT
        g1 = sp & got1
        f1[sim] = np.where(g1, 0.5, 1.0)
        p1[sim] = np.where(sp, np.where(stopA, px_stop, np.where(got1, px1, end_px)), one_p)
        f2[sim] = np.where(g1, 0.5, 0.0)
        p2[sim] = np.where(g1, leg2_p, 0.0)
        why[sim] = np.where(sp, np.where(stopA, 0, np.where(got1, leg2_w, end_why)), one_w)
        exit_bar[sim] = np.where(sp, np.where(stopA, ee + js, np.where(got1, leg2_b, end_bar)), one_b)
        t1_hit[sim] = g1
        status[sim] = np.where(why[sim] == 4, ST_OPEN, ST_CLOSED)
    with np.errstate(invalid="ignore", divide="ignore"):
        tot = f1 + f2
        exit_px = np.where(tot > 0, (f1 * p1 + f2 * p2) / np.where(tot > 0, tot, 1.0), np.nan)
        gross = (f1 * side * (p1 - entry) + f2 * side * (p2 - entry)) / entry * STAKE
        fees = fee * STAKE + (f1 * p1 + f2 * p2) / entry * fee * STAKE
        pnl = gross - fees
        r = pnl / (STAKE * risk / entry)
    # one open trade per book per asset
    kept, busy = [], -1
    for k in np.argsort(i, kind="stable"):
        if status[k] == ST_SKIP or i[k] <= busy:
            continue
        kept.append(k)
        busy = exit_bar[k] - 1 if status[k] == ST_CLOSED else n
    kept = np.array(kept, dtype=int)
    exit_ms = np.full(N, -1, dtype="int64")
    cl = status == ST_CLOSED
    if cl.any():
        eb = exit_bar[cl]
        exit_ms[cl] = np.where(why[cl] == 3, ms[np.minimum(eb, n - 1)] + BAR_MS, ms[np.minimum(eb, n - 1)])
    out = {"k": kept}
    for name, arr in (("status", status), ("entry", entry), ("risk", risk), ("t1", t1), ("t2", t2), ("exit", exit_px),
                      ("exit_bar", exit_bar), ("exit_ms", exit_ms), ("why", why), ("t1_hit", t1_hit), ("r", r),
                      ("pnl", pnl), ("fees", fees), ("gross", gross)):
        out[name] = arr[kept] if len(kept) else arr[:0]
    return out


def run(book, ctx, p=None):
    """-> (setups, kept trades) of one book on one asset."""
    p = p or RULES[book]
    S = setups(book, ctx, p)
    return S, simulate(ctx, S)


# ---------------------------------------------------------------- words
def _px(v):
    if v is None or v != v:
        return "n/a"
    a = abs(v)
    return ("{:,.0f}".format(v) if a >= 10000 else "{:,.1f}".format(v) if a >= 1000 else "{:,.2f}".format(v) if a >= 10
            else "{:,.3f}".format(v))


def _hm(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%H:%M")


def _utc(ms):
    return None if ms is None or ms < 0 else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def target_names(book, p):
    """-> (T1 name, T2 name, how the exit works)."""
    if book == "p4_gapfill":
        if p["mode"] == "fill":
            how = {"half": "everything at T1", "full": "everything at T2",
                   "split": "half at T1, the rest at T2, stop to entry after T1"}[p["target"]]
            return "half-way", "yesterday's close", how
        return "1R", "2R", "everything at %s" % ("T1" if p["target"] == "1R" else "T2")
    how = {"1R": "everything at T1", "2R": "everything at T2", "reach": "everything at T2",
           "split": "half at T1, the rest at T2, stop to entry after T1"}[p["target"]]
    return "1R", ("realistic reach" if p["target"] == "reach" else "2R"), how


def _head(book, ctx, S, k, p):
    a = SHORT_NAME.get(ctx.asset, ctx.asset)
    i, side = int(S["i"][k]), int(S["side"][k])
    word = "above" if side > 0 else "below"
    if book == "p3_orb":
        E = orb_events(ctx, p["or_len"])
        ev = int(S["ev"][k])
        lab = labels(book, ctx)[int(S["lab"][k])]
        st = int(E["start"][ev])
        return ("Opening range breakout, %s, %s: the %s-%s UTC range was %s to %s; the %s bar closed %s it at %s" % (
            a, lab, _hm(st), _hm(st + p["or_len"] * 60000), _px(E["lo"][ev]), _px(E["hi"][ev]), _hm(ctx.ms[i]), word,
            _px(ctx.c[i])))
    if book == "p4_gapfill":
        G = gap_days(ctx)
        ev = int(S["ev"][k])
        gp, ga = G["gap_pct"][ev], G["gap_atr"][ev]
        s = "S&P 500 opened %.2f%% %s yesterday's close %s (%.1f hourly ATRs)" % (
            abs(gp), "above" if gp > 0 else "below", _px(G["pc"][ev]), ga if ga == ga else float("nan"))
        if p["mode"] == "go":
            return "Gap and go, " + s + "; the gap held the first 30 minutes and the 10:00 close was beyond the open"
        how = {"now": "fade at once", "c15": "the first 15 minutes closed back toward the fill",
               "c30": "after 30 minutes price was back toward the fill"}[p["entry"]]
        return "Gap fill, " + s + "; " + how
    R = sq_releases(ctx, p["tf"], p["N"])
    ev = int(S["ev"][k])
    how = ("the %s bar closed %s the range at %s" % (_hm(ctx.ms[i]), word, _px(ctx.c[i])) if p["dir"] == "break"
           else "the MACD histogram pointed %s" % ("up" if side > 0 else "down"))
    return "Squeeze breakout, %s: a %d-bar %s squeeze (%s to %s) released at %s UTC; %s" % (
        a, int(R["len"][ev]), p["tf"], _px(R["lo"][ev]), _px(R["hi"][ev]), _hm(R["rel_ms"][ev] + (BAR_MS if p["tf"] == "15m" else HOUR_MS)), how)


def sentence(book, ctx, S, T, j, p):
    k = int(T["k"][j])
    st = int(T["status"][j])
    side = int(S["side"][k])
    n1, n2, how = target_names(book, p)
    entry = T["entry"][j]
    plan = "%s %s%s, stop %s, T1 (%s) %s, T2 (%s) %s, %s" % (
        "LONG" if side > 0 else "SHORT", "at the next open (about) " if st == ST_WAIT else "", _px(entry),
        _px(S["stop"][k]), n1, _px(T["t1"][j]), n2, _px(T["t2"][j]), how)
    out = "%s: %s." % (_head(book, ctx, S, k, p), plan)
    if st == ST_CLOSED:
        w = WHY[int(T["why"][j])]
        res = {"STOP": "stopped" + (" at break-even after T1" if T["t1_hit"][j] else ""), "T1": "T1 reached",
               "T2": "T2 reached", "TIME": "closed at the session / time limit" + (" after T1" if T["t1_hit"][j] else "")}[w]
        out += " Result: %s, exit %s, %+.2fR, %+.2f USD after %.2f USD fees." % (
            res, _px(T["exit"][j]), T["r"][j], T["pnl"][j], T["fees"][j])
    elif st == ST_OPEN:
        out += " Open, marked at %s: %+.2fR." % (_px(ctx.c[-1]), T["r"][j])
    else:
        out += " Waiting for the next open."
    return out


def _row(book, ctx, S, T, j, p):
    k = int(T["k"][j])
    st = int(T["status"][j])
    rnd = lambda v, d=6: None if v is None or v != v else round(float(v), d)   # noqa: E731
    n1, n2, _how = target_names(book, p)
    i = int(S["i"][k])
    lab = labels(book, ctx)[int(S["lab"][k])] if len(labels(book, ctx)) else None
    closed, opened = st == ST_CLOSED, st in (ST_OPEN, ST_CLOSED)
    return {"book": book, "asset": ctx.asset, "status": STATUS[st], "side": int(S["side"][k]),
            "setup_utc": _utc(int(ctx.ms[i]) + BAR_MS), "entry_utc": _utc(int(ctx.ms[i + 1])) if opened else None,
            "entry": rnd(T["entry"][j]) if opened else None, "est_entry": rnd(T["entry"][j]) if st == ST_WAIT else None,
            "stop": rnd(S["stop"][k]), "target_1": rnd(T["t1"][j]), "target_2": rnd(T["t2"][j]),
            "t1_name": n1, "t2_name": n2,
            "exit_utc": _utc(int(T["exit_ms"][j])) if closed else None, "exit": rnd(T["exit"][j]) if closed else None,
            "why_out": WHY[int(T["why"][j])] if opened else "OPEN", "t1_hit": bool(T["t1_hit"][j]),
            "r": rnd(T["r"][j], 3) if opened else None, "pnl_usd": rnd(T["pnl"][j], 2) if opened else None,
            "fees_usd": rnd(T["fees"][j], 2) if opened else None, "session": lab,
            "text": sentence(book, ctx, S, T, j, p)}


# ---------------------------------------------------------------- live interface
def _subset(S, keep):
    return dict((key, np.asarray(v)[keep]) for key, v in S.items())


def step(bars=None, now_ms=None):
    """bars: {asset: 15m frame}; None loads every asset from disk. -> rows (docs/PLAYBOOK_INTERFACE.md).
    Only setups decided at or after the registration date; stateless and deterministic."""
    reg = pd.Timestamp(REGISTERED, tz="UTC")
    reg_ms = int(reg.value // 10**6)
    anchor = reg - pd.Timedelta(days=WARMUP_DAYS)
    rows = []
    for asset in ASSETS:
        if bars is None:
            try:
                df = data.load(asset)
            except Exception:
                continue
        else:
            df = bars.get(asset)
            if df is None:
                continue
        df = df[df.index >= anchor]
        if now_ms is not None:
            df = df[data.to_ms(df.index) + BAR_MS <= int(now_ms)]
        if len(df) < 200:
            continue
        ctx = Ctx(df, asset, now_ms)
        for book, facts in BOOKS.items():
            if asset not in facts["assets"]:
                continue
            p = RULES[book]
            S = setups(book, ctx, p)
            S = _subset(S, ctx.ms[S["i"]] + BAR_MS >= reg_ms) if len(S["i"]) else S
            T = simulate(ctx, S)
            for j in range(len(T["k"])):
                rows.append(_row(book, ctx, S, T, j, p))
    return rows


def _totals(closed):
    n = len(closed)
    if not n:
        return {"trades": 0, "won": 0, "win_rate_pct": None, "avg_r": None, "net_usd": 0.0, "fees_usd": 0.0}
    won = sum(1 for r in closed if r["pnl_usd"] > 0)
    return {"trades": n, "won": won, "win_rate_pct": round(100.0 * won / n, 1),
            "avg_r": round(sum(r["r"] for r in closed) / n, 3), "net_usd": round(sum(r["pnl_usd"] for r in closed), 2),
            "fees_usd": round(sum(r["fees_usd"] for r in closed), 2)}


def rule_text(book, p=None):
    p = p or RULES[book]
    n1, n2, how = target_names(book, p)
    if book == "p3_orb":
        f = {None: "", "narrow": "; only when the range is narrower than its 20-session median",
             "htf": "; only in the direction of the engine's higher-timeframe bias",
             "gap": "; on the S&P only in the direction of the overnight gap (other markets unfiltered)"}[p.get("filter")]
        return ("At each session open (S&P 09:30 New York; London 08:00 for gold, silver, USDJPY; Tokyo 09:00 for USDJPY; "
                "US equity open and 00:00 UTC for BTC, ETH) take the first %d minutes' range; trade the first 15m close outside "
                "it at the next open; stop at the range's %s; T1 %s, T2 %s, %s; flat by the session end (S&P 16:00 New York, "
                "else 8 hours)%s." % (p["or_len"], "opposite side" if p["stop"] == "far" else "middle", n1, n2, how, f))
    if book == "p4_gapfill":
        b = p["band"]
        band = ("%.2f%% to %.2f%%" % (b[1], b[2])) if b[0] == "pct" else ("%.2f to %.2f hourly ATRs" % (b[1], b[2]))
        if p["mode"] == "go":
            return ("S&P 500: when the cash open gaps %s from yesterday's 16:00 close and the gap holds the first 30 minutes "
                    "(not filled, 10:00 close beyond the open), trade with it at 10:00; stop at the first 30 minutes' opposite "
                    "extreme; %s; flat by 16:00." % (band, how.replace("T1", "1R").replace("T2", "2R")))
        ent = {"now": "at 09:45 whatever the first bar did", "c15": "at 09:45 if the first 15 minutes closed back toward the fill",
               "c30": "at 10:00 if after 30 minutes price is back toward the fill"}[p["entry"]]
        return ("S&P 500: when the cash open gaps %s from yesterday's 16:00 close, fade it %s (gap not yet filled); stop beyond "
                "the first %d minutes' extreme; T1 half-way, T2 yesterday's close, %s; flat by 16:00." % (
                    band, ent, 30 if p["entry"] == "c30" else 15, how))
    f = {None: "", "vol": "; only when the decision bar's volume is at least 1.5x the last 20 bars' mean (not USDJPY: no volume)",
         "htf": "; only in the direction of the engine's higher-timeframe bias",
         "session": "; only between 08:00 London and 16:00 New York"}[p.get("filter")]
    d = ("the first 15m close beyond the squeeze's high or low within 8 bars" if p["dir"] == "break"
         else "the side of the MACD histogram at the release")
    return ("Squeeze = Bollinger(20, 2) inside Keltner(20, 1.5) on %s for at least %d bars; on release trade %s at the next "
            "open; stop at the squeeze range's opposite side; T1 %s, T2 %s, %s; time exit after %d bars (never held through "
            "a market close)%s." % (p["tf"], p["N"], d, n1, n2, how, p["hold"], f))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "est_entry", "stop",
                                             "target_1", "target_2", "r", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"],
                     "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r[k]) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit", "why_out",
                                                          "r", "pnl_usd", "text")) for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per,
                     "note": "Paper only. Registered rule graded forward from %s; history does not prove it." % facts["registered"]}
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"])
