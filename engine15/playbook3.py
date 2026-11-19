# -*- coding: utf-8 -*-
"""playbook3 -- seven standalone rule-based strategy books on 15-minute bars (batch 3). PAPER ONLY.

Owner, 11 Nov 2026: "build all 12" (charter task K, batch 3). Interface: docs/PLAYBOOK_INTERFACE.md.
Plain-English rules and history: docs/PLAYBOOK3.md. History study: research/playbook3_study.py ->
research/out/playbook3.md / .json.

P6   VWAP REVERSION / RECLAIM (H11). Daily VWAP anchored 00:00 UTC with volume-weighted sigma bands.
     "fade": in a range (1h ADX < 20, or no higher-timeframe bias) fade a close beyond VWAP +- k sigma
     back toward VWAP. "reclaim": with the higher-timeframe bias on, buy (sell) the day's first pullback
     that tags VWAP and closes back on the trend side.
P7   SESSION PLAYS (H12). "judas": the first move after the London open that takes out the Asian range
     (00:00 UTC to the London open) and closes back inside within 4 bars is faded. "abo": the first
     15m close outside the Asian range in the first 4 London hours is traded (gold, USDJPY). "drift":
     long BTC / ETH at a weekday 16:00 or 18:00 UTC close, held 4 hours (the market-state map's lead).
P8   FAIR VALUE GAP / ORDER BLOCK (H13). Candle 1's high below candle 3's low (bullish), gap at least
     k x ATR(15m); wait up to 12 hours for price to come back into the gap (or the last opposite candle
     before the impulse) and, if the zone holds at that bar's close, trade in the impulse direction;
     stop beyond the zone; targets 2R, or half at the impulse extreme and the rest at 2R or beyond.
P9   CRYPTO LIQUIDATION CASCADES (H14). A drop (rise) of at least x hourly ATRs within 4 bars, on a
     volume surge, with the takers one-sided: "cont" trades with it at once; "bounce" waits up to 8 bars
     for a bar that closes beyond the previous bar's extreme against the move and fades the cascade.
P10  ROUND-NUMBER MAGNETS (H15). "magnet": a first approach within y hourly ATRs of a big round number
     is traded toward it; "reject": a first touch of a round number in 24 hours that closes back away
     from it is faded.
P11  RELEASE-DAY TRADES BEYOND CPI (H16). FOMC, payrolls and the other US high-impact releases on the
     calendar (CPI is H1's): "follow" the release bar's close (stop beyond its far extreme, 4 hours) or
     "fade" it (stop beyond its extreme, target its open).
P12  CRYPTO OPENING RANGE AT THE US EQUITY OPEN (H17). playbook2's registered P3 rule (30-minute range,
     first close outside it with the higher-timeframe bias, stop at the far side, 2R, 8 hours), on BTC and
     ETH at the US cash open only. FOUND in the playbook2 session breakdown: forward-only.

THE FRAME (all books, as engine15/playbook2.py, whose simulator is reused unchanged): closed bars only;
the decision is at the close of bar i and fills at the open of bar i+1 (a fill beyond the stop is not
taken); stop and target inside one bar = the stop; a gap through the stop fills at the open; one open
trade per book per asset; $10,000 a trade; the asset's own fee a side; the stop at least 4 one-side
fees away; nothing held through a market break longer than 3 hours; a time exit fills at the close of
the window's last bar. Structural stops sit PAD_ATR x ATR(1h) beyond the structure.

The books are recomputed from the bars at every step from a FIXED warm-up anchor (registration minus
WARMUP_DAYS), so they hold no state and the same bars always give the same rows.
"""
import time

import numpy as np
import pandas as pd

from . import data, econ
from . import indicators as ind
from . import playbook2 as pb2
from .config import CFG
from .playbook2 import (BAR_MS, HOUR_MS, DAY_MS, K_R, K_PX, M_T2, M_SPLIT, ST_WAIT, ST_OPEN, ST_CLOSED,  # noqa: F401
                        STATUS, WHY, fee_side, simulate, session_windows, _subset, _totals, _px, _hm, _utc)
from .sources import ltf as _ltf

REGISTERED = "2026-11-11"
STAKE = pb2.STAKE
WARMUP_DAYS = 450
ASSETS = pb2.ASSETS
CRYPTO = ("BTCUSDT", "ETHUSDT")
SHORT_NAME = pb2.SHORT_NAME
UTC_SESSIONS = pb2.SQ_SESSIONS                 # Asia 00-07, London 07-13, New York 13-20, Late 20-24 UTC

# ---------------------------------------------------------------- fixed constants (declared once, not tuned)
PAD_ATR = 0.25                     # structural stops sit 0.25 x ATR(14) of the 1h chart beyond the structure
FAR_R = 50.0                       # a "target" never reached: the trade is a time exit
NO_VOLUME = ("USDJPY",)            # the live FX feed has no volume: its VWAP weights every bar equally
VWAP_MIN_BARS = 4                  # P6: the sigma bands are read once the day is an hour old
ADX_RANGE = 20.0                   # P6: "range" = 1h ADX(14) below 20
HOLD_VWAP, HOLD_FVG, HOLD_CASC, HOLD_ROUND, HOLD_REL, HOLD_DRIFT = 32, 32, 16, 16, 16, 16
JUDAS_REVERSE = 4                  # P7: back inside within 4 bars of the take-out (the take-out bar included)
ASIA_MIN_SHARE = 0.8               # P7: at least 80% of the Asian session's bars on file
ABO_WINDOW = 16                    # P7: an Asian-range breakout counts in the first 4 London hours
FVG_WAIT, OB_BACK = 48, 5          # P8: the return must come within 12 hours; the order block within 5 bars
CASC_BARS, CASC_VOL_N = 4, 96      # P9: the move within 4 bars; volume against the previous 24 hours
TAKER_ONE_SIDED = 0.45             # P9: taker buying at most 45% of volume in a drop (at least 55% in a rise)
BOUNCE_WAIT = 8                    # P9: the exhaustion bar must come within 2 hours
FUND_N = 90                        # P9: funding rank among the last 90 settlements (30 days)
ROUND_STEPS = {"base": {"BTCUSDT": 1000.0, "ETHUSDT": 100.0, "XAUUSD": 50.0, "XAGUSD": 1.0, "USDJPY": 0.5, "SPX": 50.0},
               "major": {"BTCUSDT": 5000.0, "ETHUSDT": 500.0, "XAUUSD": 100.0, "XAGUSD": 5.0, "USDJPY": 1.0, "SPX": 100.0}}
MAGNET_FRESH, TOUCH_FRESH = 16, 96  # P10: untouched over the last 4 hours (magnet) / 24 hours (reject)
P3_RULE = dict(pb2.RULES["p3_orb"])  # P12 = playbook2's registered P3 rule ...
US_LAB = 1                         # ... at its second crypto session, the US equity open (pb2.ORB_SESSIONS)

# ---------------------------------------------------------------- the variant grids (research/playbook3_study.py)
VWAP_GRID = ([{"mode": "fade", "k": k, "entry": e, "target": t, "regime": g}
              for k in (2.0, 2.5) for e in ("close", "back") for t in ("vwap", "2R") for g in ("adx", "nobias")]
             + [{"mode": "reclaim", "stop": s, "target": t} for s in ("bar", "atr") for t in ("2R", "3R")])      # 16 + 4
SESSION_GRID = ([{"play": "judas", "window": w, "target": t} for w in (8, 12) for t in ("opp", "2R")]
                + [{"play": "abo", "stop": s, "target": t} for s in ("far", "mid") for t in ("2R", "3R")]
                + [{"play": "drift", "hour": hr, "stop_atr": m} for hr in (16, 18) for m in (1.5, 3.0)])      # 4 + 4 + 4
FVG_GRID = [{"zone": z, "k": k, "target": t, "filter": f}
            for z in ("fvg", "ob") for k in (0.5, 1.0) for t in ("2R", "ext") for f in (None, "bias")]         # 16
CASC_GRID = [{"mode": m, "x": x, "vol": v, "target": t, "filter": None}
             for m in ("cont", "bounce") for x in (2.0, 3.0) for v in (1.5, 2.5)
             for t in (("2R", "3R") if m == "cont" else ("2R", "half"))]                                        # 16
CASC_FILTERS = ("funding",)                                                                                     # stage 2: +2
ROUND_GRID = ([{"mode": "magnet", "grid": g, "y": y, "stop": s} for g in ("base", "major") for y in (0.5, 1.0)
               for s in ("half", "full")]
              + [{"mode": "reject", "grid": g, "target": t} for g in ("base", "major") for t in ("2R", "3R")])  # 8 + 4
RELEASE_GRID = [{"mode": m, "min_atr": a} for m in ("follow", "fade") for a in (0.5, 1.0)]                       # 4
ORB_US_GRID = [{"orb": "us_open"}]                                                                              # 1

GRIDS = {"p6_vwap": VWAP_GRID, "p7_session": SESSION_GRID, "p8_fvg": FVG_GRID, "p9_cascade": CASC_GRID,
         "p10_round": ROUND_GRID, "p11_release": RELEASE_GRID, "p12_orb_us": ORB_US_GRID}

# ---------------------------------------------------------------- the registered rules
# Chosen on the FIRST half of history only (research/playbook3_study.py, docs/PLAYBOOK3.md); P11 on the
# few releases on file (all after May 2026); P12 not chosen at all (the one rule where the lead was found).
# A book may run more than one part (each part a variant); their setups share the one-trade-at-a-time rule.
# None of P6-P10 cleared costs in the second half (docs/PLAYBOOK3.md); each runs forward as a paper book only so
# that the forward record, not the history, gives the verdict.
#  P6   no fade variant was near zero (best -0.25R); the reclaim (stop 1 hourly ATR beyond VWAP, 2R) lost least.
#  P7   no sub-play had a positive first half, so only the best one: the Asian-range breakout (gold, USDJPY).
#  P9   continuation beat the bounce in every pairing; the funding filter lifted the first half (+0.061R).
#  P10  the magnet (within 1 hourly ATR, stop as far behind as the number is ahead) lost least.
#  P11  chosen on the 2-10 releases a market had on file (May-Nov 2026): in-sample, forward only.
RULES = {
    "p6_vwap": [{"mode": "reclaim", "stop": "atr", "target": "2R"}],
    "p7_session": [{"play": "abo", "stop": "far", "target": "3R"}],
    "p8_fvg": [{"zone": "fvg", "k": 1.0, "target": "ext", "filter": None}],
    "p9_cascade": [{"mode": "cont", "x": 3.0, "vol": 1.5, "target": "3R", "filter": "funding"}],
    "p10_round": [{"mode": "magnet", "grid": "base", "y": 1.0, "stop": "full"}],
    "p11_release": [{"mode": "follow", "min_atr": 1.0}],
    "p12_orb_us": [{"orb": "us_open"}],
}

# Retired books (owner's word): no trade entered at or after the stamp counts; the record before it is kept as is
# (as playbook.RETIRED). p10_round: owner "Post-mortem, then retire" (19 Nov 2026) after 120 live trades, -$2,018,
# -0.14R a trade even before costs (research/out/p10_postmortem.md); its history had no edge before costs either.
RETIRED = {"p10_round": "2026-11-19 04:00"}

BOOKS = {
    "p6_vwap": {"title": "VWAP reversion / reclaim", "hypothesis": "H11", "registered": REGISTERED, "assets": ASSETS},
    "p7_session": {"title": "Session plays", "hypothesis": "H12", "registered": REGISTERED, "assets": ("XAUUSD", "USDJPY")},
    "p8_fvg": {"title": "Fair value gap / order block", "hypothesis": "H13", "registered": REGISTERED, "assets": ASSETS},
    "p9_cascade": {"title": "Crypto liquidation cascades", "hypothesis": "H14", "registered": REGISTERED, "assets": CRYPTO},
    "p10_round": {"title": "Round-number magnets (retired 19 Nov 2026)", "hypothesis": "H15", "registered": REGISTERED, "assets": ASSETS},
    "p11_release": {"title": "Release-day trades beyond CPI", "hypothesis": "H16", "registered": REGISTERED, "assets": ASSETS},
    "p12_orb_us": {"title": "Crypto opening range at the US equity open", "hypothesis": "H17", "registered": REGISTERED,
                   "assets": CRYPTO, "forward_only": True},
}

PLAY_ASSETS = {"judas": ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY"), "abo": ("XAUUSD", "USDJPY"), "drift": CRYPTO}
PLAY_LABELS = ("London false move", "Asian-range breakout", "New York afternoon drift")
RELEASE_KINDS = ("FOMC", "Payrolls", "Other")


UNIVERSE = {"p9_cascade": CRYPTO, "p12_orb_us": CRYPTO}       # where a book's variants may trade (default: all six)


def applies(book, p, asset):
    """Does variant p of a book trade this asset? (The study's universe, not only the registered rule's markets.)"""
    if asset not in UNIVERSE.get(book, ASSETS):
        return False
    if book == "p7_session":
        return asset in PLAY_ASSETS[p["play"]]
    return True


def vname(book, p):
    """A short readable name of a variant."""
    if book == "p6_vwap":
        if p["mode"] == "fade":
            return "fade %.1fsd %s %s %s" % (p["k"], p["entry"], p["target"], p["regime"])
        return "reclaim stop-%s %s" % (p["stop"], p["target"])
    if book == "p7_session":
        if p["play"] == "judas":
            return "judas %dbars %s" % (p["window"], p["target"])
        if p["play"] == "abo":
            return "asia-break stop-%s %s" % (p["stop"], p["target"])
        return "drift %02d:00 stop%.1fATR" % (p["hour"], p["stop_atr"])
    if book == "p8_fvg":
        return "%s k%.1f %s%s" % (p["zone"], p["k"], p["target"], "" if not p.get("filter") else " +" + p["filter"])
    if book == "p9_cascade":
        return "%s x%.0f vol%.1f %s%s" % (p["mode"], p["x"], p["vol"], p["target"], "" if not p.get("filter") else " +" + p["filter"])
    if book == "p10_round":
        if p["mode"] == "magnet":
            return "magnet %s y%.1f stop-%s" % (p["grid"], p["y"], p["stop"])
        return "reject %s %s" % (p["grid"], p["target"])
    if book == "p11_release":
        return "%s move>=%.1fATR" % (p["mode"], p["min_atr"])
    return "US-open OR30 stop-far 2R +htf (P3 rule)"


def group_of(book, p):
    """The sub-play a variant belongs to (P6 / P7 / P9 / P10 / P11 may register one part per group)."""
    return {"p6_vwap": p.get("mode"), "p7_session": p.get("play"), "p9_cascade": p.get("mode"),
            "p10_round": p.get("mode"), "p11_release": p.get("mode")}.get(book, "all")


# ---------------------------------------------------------------- one asset's bars and its cached readings
class Ctx(pb2.Ctx):
    """playbook2's context (bars, bias, ATR(1h), market breaks, ...) plus the readings batch 3 needs.
    `events` (tests): [(ms, kind 0 FOMC / 1 payrolls / 2 other, title), ...] instead of the calendar file."""

    def __init__(self, df, asset, now_ms=None, funding=None, events=None):
        super(Ctx, self).__init__(df, asset, now_ms)
        self._funding = funding
        self._events = events
        self.tb = (np.array(self.df["taker_buy"].values, dtype=float) if "taker_buy" in self.df
                   else np.full(self.n, np.nan))

    def entry_est(self, dec):
        """The fill of a decision at bar dec: the next open, or the last close while it is pending (as simulate)."""
        dec = np.asarray(dec, dtype=int)
        if not self.n or not len(dec):
            return np.zeros(len(dec))
        e = dec + 1
        return np.where(e < self.n, self.o[np.minimum(e, self.n - 1)], self.c[np.minimum(dec, self.n - 1)])

    def prev(self, x, d=1):
        x = np.asarray(x, dtype=float)
        out = np.full(len(x), np.nan)
        if d < len(x):
            out[d:] = x[:-d] if d else x
        return out

    def atr15(self):
        return self.get("atr15", lambda: np.array(ind.atr_wilder(self.df).values, dtype=float))

    def adx1h(self):
        def make():
            h1 = data.resample(self.df, "1h")
            return np.array(data.htf_on_15(self.df, "1h", _ltf.adx(h1)["adx"]).values, dtype=float)
        return self.get("adx1h", make)

    def utc_lab(self):
        def make():
            hour = (self.ms % DAY_MS) // HOUR_MS
            return np.where(hour < 7, 0, np.where(hour < 13, 1, np.where(hour < 20, 2, 3))).astype(int)
        return self.get("utc_lab", make)

    def vwap(self):
        """Daily VWAP (00:00 UTC anchor) of the typical price and its volume-weighted sigma, this bar included
        (sources/ltf.py's _session_vwap). USDJPY weights every bar equally (its live feed has no volume)."""
        def make():
            class X(object):
                pass
            x = X()
            x.h, x.l, x.c = self.h, self.l, self.c
            x.v = np.ones(self.n) if self.asset in NO_VOLUME else self.v
            vw, sd, cnt = _ltf._session_vwap(x, self.ms // DAY_MS)
            return vw, sd, cnt
        return self.get("vwap", make)

    def funding_rank(self):
        """Rank (0-1) of the newest funding rate known at each close among the last 90 settlements; NaN off crypto."""
        def make():
            out = np.full(self.n, np.nan)
            if self.asset not in CFG["crypto"] or not self.n:
                return out
            f = self._funding if self._funding is not None else data.load_funding(self.asset)
            if not len(f):
                return out
            rk = f.rolling(FUND_N, min_periods=30).rank(pct=True)
            k = np.searchsorted(data.to_ms(f.index), self.ms + BAR_MS, side="right") - 1
            ok = k >= 0
            out[ok] = rk.values[k[ok]]
            return out
        return self.get("fund_rank", make)

    def london_asia(self):
        """Every London session (08:00 London, Monday-Friday) with its Asian range: the bars from 00:00 UTC to
        the London open. -> arrays: a (row of the London open bar), start, end (open + 8 hours), hi, lo."""
        def make():
            empty = dict((k, np.zeros(0, dtype=int if k == "a" else float)) for k in ("a", "start", "end", "hi", "lo"))
            n, ms = self.n, self.ms
            if not n:
                return empty
            st, en = session_windows("london", ms[0], ms[-1])
            a0 = st - st % DAY_MS
            ia, ib = np.searchsorted(ms, a0), np.searchsorted(ms, st)
            need = (st - a0) // BAR_MS
            ok = (ib < n) & (ib - ia >= ASIA_MIN_SHARE * need) & (ib > ia)
            ok &= ms[np.minimum(ib, n - 1)] == st
            st, en, ia, ib = st[ok], en[ok], ia[ok], ib[ok]
            if not len(st):
                return empty
            hi = np.array([self.h[x:y].max() for x, y in zip(ia, ib)], dtype=float)
            lo = np.array([self.l[x:y].min() for x, y in zip(ia, ib)], dtype=float)
            return {"a": ib.astype(int), "start": st, "end": en, "hi": hi, "lo": lo}
        return self.get("london_asia", make)

    def events(self):
        """US high-impact releases other than CPI: (ms array, kind array, titles). CPI is H1's (engine15/shadow.py)."""
        def make():
            if self._events is not None:
                rows = list(self._events)
            else:
                rows = []
                ev = econ.load_events()
                if len(ev):
                    for ts, g in ev.groupby("ts_ms"):
                        t = " ".join(str(x) for x in g["title"]).upper()
                        if "CPI" in t:
                            continue
                        kind = 0 if ("FOMC" in t or "FEDERAL FUNDS" in t) else 1 if ("NFP" in t or "NON-FARM" in t
                                                                                     or "EMPLOYMENT" in t) else 2
                        rows.append((int(ts), kind, " / ".join(str(x) for x in g["title"])[:60]))
            rows.sort()
            return (np.array([r[0] for r in rows], dtype="int64"), np.array([r[1] for r in rows], dtype=int),
                    [r[2] for r in rows])
        return self.get("events", make)


# ---------------------------------------------------------------- windows and the setup arrays
def hold_window(ctx, dec, hold):
    """A trade from the open after dec, for `hold` bars, never across a market break.
    -> (last bar, window finished, may wait for its fill)."""
    n = ctx.n
    dec = np.asarray(dec, dtype=int)
    if not len(dec):
        z = np.zeros(0, dtype=bool)
        return np.zeros(0, dtype=int), z, z
    se = ctx.seg_end()[dec]
    e = dec + 1
    last_hold = e + hold - 1
    last = np.minimum(last_hold, se)
    seg_finished = (se < n - 1) | ctx.last_seg_done
    done = ((last_hold <= se) & (last_hold <= n - 1)) | ((last_hold > se) & seg_finished)
    can_wait = (e >= n) & (not ctx.last_seg_done)
    return last.astype(int), done, can_wait


def end_window(ctx, dec, end_ms):
    """A trade from the open after dec to a clock time (exclusive), never across a market break."""
    n, ms = ctx.n, ctx.ms
    dec = np.asarray(dec, dtype=int)
    if not len(dec):
        z = np.zeros(0, dtype=bool)
        return np.zeros(0, dtype=int), z, z
    end_ms = np.asarray(end_ms, dtype="int64")
    B = np.searchsorted(ms, end_ms)
    last_t = B - 1
    se = ctx.seg_end()[dec]
    last = np.minimum(last_t, se)
    complete = (B < n) | (ctx.now >= end_ms)
    seg_finished = (se < n - 1) | ctx.last_seg_done
    done = np.where(last_t <= se, complete, seg_finished)
    can_wait = (dec + 1 >= n) & (not ctx.last_seg_done) & (ms[dec] + BAR_MS < end_ms)
    return last.astype(int), done, can_wait


def _mk(dec, side, stop, t1k, t1v, t2k, t2v, mode, win, lab, sub=0, x1=np.nan, x2=np.nan):
    """-> the setup dict playbook2.simulate reads (+ sub, x1, x2 for the words)."""
    dec = np.asarray(dec, dtype=int)
    m = len(dec)
    last, done, can_wait = win

    def f(v, dt=float):
        return np.array(np.broadcast_to(np.asarray(v, dtype=dt), (m,)))
    return {"i": dec, "side": f(side, int), "stop": f(stop), "t1k": f(t1k, int), "t1v": f(t1v), "t2k": f(t2k, int),
            "t2v": f(t2v), "mode": f(mode, int), "last": f(last, int), "done": f(done, bool), "can_wait": f(can_wait, bool),
            "ev": np.arange(m), "lab": f(lab, int), "sub": f(sub, int), "x1": f(x1), "x2": f(x2)}


def _empty():
    z = np.zeros(0, dtype=int)
    return _mk(z, 0, 0.0, 0, 0.0, 0, 0.0, 0, (z, np.zeros(0, dtype=bool), np.zeros(0, dtype=bool)), 0)


def _cat(parts):
    parts = [s for s in parts if len(s["i"])]
    if not parts:
        return _empty()
    out = dict((k, np.concatenate([s[k] for s in parts])) for k in parts[0])
    order = np.argsort(out["i"], kind="stable")
    return dict((k, v[order]) for k, v in out.items())


def _r_target(r):
    """(t1 kind, t1 value, t2 kind, t2 value, mode) for everything at r R."""
    return K_R, 1.0, K_R, float(r), M_T2


def _first(mask):
    """Row-wise first True column; -1 where none."""
    if mask.shape[1] == 0:
        return np.full(mask.shape[0], -1)
    return np.where(mask.any(axis=1), mask.argmax(axis=1), -1)


# ---------------------------------------------------------------- P6: VWAP reversion / reclaim
def vwap_setups(ctx, p):
    n = ctx.n
    if n < 3:
        return _empty()
    vw, sd, cnt = ctx.vwap()
    c, h, l = ctx.c, ctx.h, ctx.l
    day = ctx.ms // DAY_MS
    atr = ctx.atr1h()
    same_day = np.r_[False, day[1:] == day[:-1]]
    valid = (cnt >= VWAP_MIN_BARS) & (sd > 0) & np.isfinite(vw) & np.isfinite(atr)
    parts = []
    with np.errstate(invalid="ignore"):
        if p["mode"] == "fade":
            k = p["k"]
            up, dn = vw + k * sd, vw - k * sd
            reg = (ctx.adx1h() < ADX_RANGE) if p["regime"] == "adx" else (ctx.bias() == 0)
            for side in (-1, 1):                                          # -1: above the upper band -> short
                beyond = (c > up) if side < 0 else (c < dn)
                beyond &= valid
                pb_ = np.r_[False, beyond[:-1]] & same_day
                if p["entry"] == "close":
                    sig = beyond & ~pb_
                    ext = h if side < 0 else l
                else:                                                     # back inside the band after a close beyond
                    sig = ~beyond & pb_ & valid & ((c > vw) if side < 0 else (c < vw))
                    run = np.cumsum(~beyond)                              # beyond bars share the id of the bar before them
                    g = pd.Series(h if side < 0 else l).groupby(run)
                    cum = (g.cummax() if side < 0 else g.cummin()).values
                    prev_cum = np.r_[np.nan, cum[:-1]]
                    ext = np.fmax(prev_cum, h) if side < 0 else np.fmin(prev_cum, l)
                sig &= reg
                dec = np.flatnonzero(sig)
                stop = ext[dec] + (-side) * PAD_ATR * atr[dec]
                if p["target"] == "vwap":
                    t = (K_R, 1.0, K_PX, vw[dec], np.full(len(dec), M_T2))
                else:
                    t = _r_target(2.0)
                parts.append(_mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_VWAP),
                                 ctx.utc_lab()[dec], sub=0, x1=vw[dec], x2=(up if side < 0 else dn)[dec]))
        else:
            b = ctx.bias()
            for side in (1, -1):
                if side > 0:
                    tag = valid & (b == 1) & (l <= vw) & (c > vw) & (ctx.prev(c) > ctx.prev(vw)) & same_day
                else:
                    tag = valid & (b == -1) & (h >= vw) & (c < vw) & (ctx.prev(c) < ctx.prev(vw)) & same_day
                first = tag & (pd.Series(tag.astype(int)).groupby(day).cumsum().values == 1)
                dec = np.flatnonzero(first)
                if p["stop"] == "bar":
                    stop = (l[dec] - PAD_ATR * atr[dec]) if side > 0 else (h[dec] + PAD_ATR * atr[dec])
                else:
                    stop = vw[dec] - side * atr[dec]
                t = _r_target(2.0 if p["target"] == "2R" else 3.0)
                parts.append(_mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_VWAP),
                                 ctx.utc_lab()[dec], sub=1, x1=vw[dec]))
    return _cat(parts)


# ---------------------------------------------------------------- P7: session plays
def judas_setups(ctx, p):
    L = ctx.london_asia()
    if not len(L["a"]):
        return _empty()
    n = ctx.n
    a, hi, lo, end = L["a"], L["hi"], L["lo"], L["end"]
    W, R = int(p["window"]), JUDAS_REVERSE
    K = W + R
    lim = np.minimum(np.searchsorted(ctx.ms, end) - 1, ctx.seg_end()[a])
    cols = np.arange(K)[None, :]
    J = a[:, None] + cols
    inw = J <= lim[:, None]
    Jc = np.minimum(J, n - 1)
    H, Lw, C = ctx.h[Jc], ctx.l[Jc], ctx.c[Jc]
    up, dn = inw & (H > hi[:, None]), inw & (Lw < lo[:, None])
    j0 = _first((up | dn) & (cols < W))
    rr = np.arange(len(a))
    jc = np.maximum(j0, 0)
    upf, dnf = up[rr, jc], dn[rr, jc]
    ok = (j0 >= 0) & (upf != dnf)                                      # one side only (both in one bar: no read)
    inside = inw & (C < hi[:, None]) & (C > lo[:, None]) & (cols >= jc[:, None]) & (cols < jc[:, None] + R)
    jd = _first(inside)
    ok &= jd >= 0
    span = inw & (cols >= jc[:, None]) & (cols <= np.maximum(jd, 0)[:, None])
    ext_hi = np.where(span, H, -np.inf).max(axis=1)
    ext_lo = np.where(span, Lw, np.inf).min(axis=1)
    ev = np.flatnonzero(ok)
    side = np.where(upf[ev], -1, 1)
    dec = (a + jd)[ev].astype(int)
    atr = ctx.atr1h()[dec]
    stop = np.where(side < 0, ext_hi[ev] + PAD_ATR * atr, ext_lo[ev] - PAD_ATR * atr)
    if p["target"] == "opp":
        t = (K_R, 1.0, K_PX, np.where(side < 0, lo[ev], hi[ev]), M_T2)
    else:
        t = _r_target(2.0)
    return _mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], end_window(ctx, dec, end[ev]), 0, sub=0,
               x1=hi[ev], x2=lo[ev])


def abo_setups(ctx, p):
    L = ctx.london_asia()
    if not len(L["a"]):
        return _empty()
    n = ctx.n
    a, hi, lo, end = L["a"], L["hi"], L["lo"], L["end"]
    lim = np.minimum(np.searchsorted(ctx.ms, end) - 1, ctx.seg_end()[a])
    cols = np.arange(ABO_WINDOW)[None, :]
    J = a[:, None] + cols
    inw = J <= lim[:, None]
    C = ctx.c[np.minimum(J, n - 1)]
    up, dn = inw & (C > hi[:, None]), inw & (C < lo[:, None])
    j = _first(up | dn)
    ev = np.flatnonzero(j >= 0)
    side = np.where(up[ev, j[ev]], 1, -1)
    dec = (a + j)[ev].astype(int)
    stop = np.where(side > 0, lo[ev], hi[ev]) if p["stop"] == "far" else (hi[ev] + lo[ev]) / 2.0
    t = _r_target(2.0 if p["target"] == "2R" else 3.0)
    return _mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], end_window(ctx, dec, end[ev]), 1, sub=1,
               x1=hi[ev], x2=lo[ev])


def drift_setups(ctx, p):
    ms = ctx.ms
    tod = ms % DAY_MS
    wd = (ms // DAY_MS + 3) % 7                                        # 1 Jan 1970 was a Thursday: Monday = 0
    dec = np.flatnonzero((tod == p["hour"] * HOUR_MS - BAR_MS) & (wd < 5))
    stop = ctx.entry_est(dec) - p["stop_atr"] * ctx.atr1h()[dec]
    t = _r_target(FAR_R)
    return _mk(dec, 1, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_DRIFT), 2, sub=2)


def session_setups(ctx, p):
    if ctx.asset not in PLAY_ASSETS[p["play"]]:
        return _empty()
    return {"judas": judas_setups, "abo": abo_setups, "drift": drift_setups}[p["play"]](ctx, p)


# ---------------------------------------------------------------- P8: fair value gap / order block
def fvg_setups(ctx, p):
    n = ctx.n
    if n < 10:
        return _empty()
    o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
    atr15, atr = ctx.atr15(), ctx.atr1h()
    segE = ctx.seg_end()
    parts = []
    i_all = np.arange(n)
    with np.errstate(invalid="ignore"):
        ref = ctx.prev(atr15, 3)                                       # the ATR before the three candles
        for side in (1, -1):
            h2, l2 = ctx.prev(h, 2), ctx.prev(l, 2)
            imp = ctx.prev(c, 1) - ctx.prev(o, 1)
            if side > 0:
                gap_ok = (l > h2) & (l - h2 >= p["k"] * ref) & (imp > 0)
            else:
                gap_ok = (h < l2) & (l2 - h >= p["k"] * ref) & (imp < 0)
            gap_ok &= (i_all >= 3) & (segE[np.maximum(i_all - 2, 0)] >= i_all)    # no market break inside the pattern
            gi = np.flatnonzero(gap_ok)
            if not len(gi):
                continue
            if p["zone"] == "fvg":
                top, bot = (l[gi], h[gi - 2]) if side > 0 else (h[gi], l[gi - 2])   # top = the near edge, bot = the far edge
                keep = np.ones(len(gi), dtype=bool)
            else:                                                      # the last opposite candle before the impulse
                back = gi[:, None] - 2 - np.arange(OB_BACK)[None, :]
                bc = np.maximum(back, 0)
                opp = (back >= 0) & (((c[bc] < o[bc]) if side > 0 else (c[bc] > o[bc])))
                jb = _first(opp)
                keep = jb >= 0
                ob = bc[np.arange(len(gi)), np.maximum(jb, 0)]
                top, bot = (h[ob], l[ob]) if side > 0 else (l[ob], h[ob])
            gi, top, bot = gi[keep], top[keep], bot[keep]
            if not len(gi):
                continue
            cols = np.arange(FVG_WAIT)[None, :]
            J = gi[:, None] + 1 + cols
            inw = J <= np.minimum(segE[gi], n - 1)[:, None]
            Jc = np.minimum(J, n - 1)
            if side > 0:
                touch = inw & (l[Jc] <= top[:, None])
                runx = np.maximum.accumulate(np.concatenate([h[gi][:, None], h[Jc]], axis=1), axis=1)
            else:
                touch = inw & (h[Jc] >= top[:, None])
                runx = np.minimum.accumulate(np.concatenate([l[gi][:, None], l[Jc]], axis=1), axis=1)
            jt = _first(touch)
            ok = jt >= 0
            rr = np.arange(len(gi))
            jtc = np.maximum(jt, 0)
            dec = gi + 1 + jtc
            held = (c[np.minimum(dec, n - 1)] >= bot) if side > 0 else (c[np.minimum(dec, n - 1)] <= bot)
            ok &= held
            ext = runx[rr, jtc]                                        # the impulse extreme before the return
            ev = np.flatnonzero(ok)
            dec, top, bot, ext = dec[ev].astype(int), top[ev], bot[ev], ext[ev]
            if p.get("filter") == "bias":
                fb = ctx.bias()[dec] == side
                dec, top, bot, ext = dec[fb], top[fb], bot[fb], ext[fb]
            elif p.get("filter"):
                raise ValueError(p["filter"])
            stop = bot - side * PAD_ATR * atr[dec]
            if p["target"] == "2R":
                t = _r_target(2.0)
            else:                                                      # half at the impulse extreme, rest at 2R or 1R past it
                en = ctx.entry_est(dec)
                risk = side * (en - stop)
                t1 = np.where(side * (ext - en) >= 0.5 * risk, ext, en + side * risk)
                t2 = np.where(side > 0, np.maximum(en + 2 * risk, t1 + risk), np.minimum(en - 2 * risk, t1 - risk))
                t = (K_PX, t1, K_PX, t2, M_SPLIT)
            parts.append(_mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_FVG),
                             ctx.utc_lab()[dec], sub=0 if p["zone"] == "fvg" else 1, x1=top, x2=bot))
    return _cat(parts)


# ---------------------------------------------------------------- P9: crypto liquidation cascades
def cascade_events(ctx, x, vol):
    """Every cascade's first bar. -> (rows, side of the move, the move's start extreme, the move in ATRs, volume x)."""
    def make():
        n = ctx.n
        h, l, c, v, tb = ctx.h, ctx.l, ctx.c, ctx.v, ctx.tb
        ref = ctx.prev(ctx.atr1h(), CASC_BARS)                         # the hourly ATR before the move
        hs, ls = pd.Series(h), pd.Series(l)
        top = hs.rolling(CASC_BARS).max().values
        bot = ls.rolling(CASC_BARS).min().values
        vs = pd.Series(np.where(v > 0, v, np.nan))
        v4 = vs.rolling(CASC_BARS).sum().values
        usual = vs.shift(CASC_BARS).rolling(CASC_VOL_N, min_periods=CASC_VOL_N // 2).mean().values * CASC_BARS
        tb4 = pd.Series(tb).rolling(CASC_BARS).sum().values
        span_ok = ctx.seg_end()[np.maximum(np.arange(n) - CASC_BARS + 1, 0)] >= np.arange(n)
        with np.errstate(invalid="ignore", divide="ignore"):
            vx = v4 / usual
            share = tb4 / v4
            drop = (top - c) / ref
            rise = (c - bot) / ref
            dn = (drop >= x) & (vx >= vol) & (share <= TAKER_ONE_SIDED) & span_ok
            upm = (rise >= x) & (vx >= vol) & (share >= 1.0 - TAKER_ONE_SIDED) & span_ok
        fire = dn | upm
        fire &= ~(dn & upm)
        fresh = fire & ~np.r_[False, fire[:-1]]
        rows = np.flatnonzero(fresh)
        side = np.where(dn[rows], -1, 1)
        return {"i": rows, "side": side, "start": np.where(side < 0, top[rows], bot[rows]),
                "atrs": np.where(side < 0, drop[rows], rise[rows]), "vx": vx[rows], "share": share[rows]}
    return ctx.get(("casc", x, vol), make)


def cascade_setups(ctx, p):
    if ctx.asset not in CRYPTO or ctx.n < 200:
        return _empty()
    E = cascade_events(ctx, p["x"], p["vol"])
    i, mside = E["i"], E["side"]
    if not len(i):
        return _empty()
    n, h, l, c = ctx.n, ctx.h, ctx.l, ctx.c
    atr = ctx.atr1h()
    sel = np.ones(len(i), dtype=bool)
    if p.get("filter") == "funding":                                   # funding has reset against the crowd that was flushed
        fr = ctx.funding_rank()[i]
        with np.errstate(invalid="ignore"):
            sel &= np.where(mside < 0, fr <= 0.5, fr >= 0.5)
    elif p.get("filter"):
        raise ValueError(p["filter"])
    k = np.flatnonzero(sel)
    i, mside, start = i[k], mside[k], E["start"][k]
    atrs, vx = E["atrs"][k], E["vx"][k]
    if p["mode"] == "cont":
        dec, side = i, mside
        stop = start
        t = _r_target(2.0 if p["target"] == "2R" else 3.0)
        return _mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_CASC), ctx.utc_lab()[dec],
                   sub=0, x1=atrs, x2=vx)
    cols = np.arange(BOUNCE_WAIT)[None, :]
    J = i[:, None] + 1 + cols
    inw = J <= np.minimum(ctx.seg_end()[i], n - 1)[:, None]
    Jc = np.minimum(J, n - 1)
    Jp = np.maximum(Jc - 1, 0)
    rev = inw & np.where(mside[:, None] < 0, c[Jc] > h[Jp], c[Jc] < l[Jp])
    j = _first(rev)
    ok = j >= 0
    ev = np.flatnonzero(ok)
    dec = (i + 1 + j)[ev].astype(int)
    side = -mside[ev]
    span = cols[:, :] <= j[ev][:, None]                                # the bars from the event's close to the decision
    Jv = Jc[ev]
    lo_ext = np.minimum(np.where(span, l[Jv], np.inf).min(axis=1), l[i[ev]])
    hi_ext = np.maximum(np.where(span, h[Jv], -np.inf).max(axis=1), h[i[ev]])
    lo_ext = np.minimum(lo_ext, pd.Series(l).rolling(CASC_BARS).min().values[i[ev]])
    hi_ext = np.maximum(hi_ext, pd.Series(h).rolling(CASC_BARS).max().values[i[ev]])
    ref = atr[dec]
    stop = np.where(side > 0, lo_ext - PAD_ATR * ref, hi_ext + PAD_ATR * ref)
    if p["target"] == "2R":
        t = _r_target(2.0)
    else:                                                              # half the cascade back
        far = np.where(side > 0, lo_ext, hi_ext)
        t = (K_R, 1.0, K_PX, (start[ev] + far) / 2.0, M_T2)
    return _mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_CASC), ctx.utc_lab()[dec],
               sub=1, x1=atrs[ev], x2=vx[ev])


# ---------------------------------------------------------------- P10: round-number magnets
def round_setups(ctx, p):
    n = ctx.n
    if n < 100:
        return _empty()
    step = ROUND_STEPS[p["grid"]][ctx.asset]
    h, l, c = ctx.h, ctx.l, ctx.c
    atr = ctx.atr1h()
    with np.errstate(invalid="ignore", divide="ignore"):
        if p["mode"] == "magnet":
            U, D = np.ceil(c / step) * step, np.floor(c / step) * step
            du, dd = U - c, c - D
            side = np.where(du <= dd, 1, -1)
            L = np.where(side > 0, U, D)
            dist = np.abs(L - c)
            y = p["y"]
            pdist = np.abs(L - ctx.prev(c))
            near = (dist <= y * atr) & (dist > 0) & (pdist > y * ctx.prev(atr))
            hmax = pd.Series(h).rolling(MAGNET_FRESH, min_periods=MAGNET_FRESH).max().values
            lmin = pd.Series(l).rolling(MAGNET_FRESH, min_periods=MAGNET_FRESH).min().values
            fresh = np.where(side > 0, hmax < L, lmin > L)
            dec = np.flatnonzero(near & fresh)
            side, L = side[dec], L[dec]
            en = ctx.entry_est(dec)
            f = 0.5 if p["stop"] == "half" else 1.0
            stop = en - side * np.abs(L - en) * f
            return _mk(dec, side, stop, K_R, 1.0, K_PX, L, M_T2, hold_window(ctx, dec, HOLD_ROUND), ctx.utc_lab()[dec],
                       sub=0, x1=L)
        cp = ctx.prev(c)
        Up = (np.floor(cp / step + 1e-9) + 1.0) * step
        Dn = (np.ceil(cp / step - 1e-9) - 1.0) * step
        pmax = pd.Series(h).shift(1).rolling(TOUCH_FRESH, min_periods=TOUCH_FRESH).max().values
        pmin = pd.Series(l).shift(1).rolling(TOUCH_FRESH, min_periods=TOUCH_FRESH).min().values
        tu = (h >= Up) & (c < Up) & (pmax < Up)
        td = (l <= Dn) & (c > Dn) & (pmin > Dn)
        both = tu & td
        tu, td = tu & ~both, td & ~both
    dec = np.flatnonzero(tu | td)
    side = np.where(tu[dec], -1, 1)
    L = np.where(side < 0, Up[dec], Dn[dec])
    stop = np.where(side < 0, h[dec] + PAD_ATR * atr[dec], l[dec] - PAD_ATR * atr[dec])
    t = _r_target(2.0 if p["target"] == "2R" else 3.0)
    return _mk(dec, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, dec, HOLD_ROUND), ctx.utc_lab()[dec],
               sub=1, x1=L)


# ---------------------------------------------------------------- P11: release-day trades beyond CPI
def release_setups(ctx, p):
    n = ctx.n
    ems, kinds, _titles = ctx.events()
    if not n or not len(ems):
        return _empty()
    idx = np.searchsorted(ctx.ms, ems)
    ok = idx < n
    ok[ok] &= ctx.ms[idx[ok]] == ems[ok]                               # the release bar is on file (market open)
    ev = np.flatnonzero(ok)
    i = idx[ev].astype(int)
    o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
    atr = ctx.atr1h()[i]
    mv = c[i] - o[i]
    with np.errstate(invalid="ignore"):
        big = np.abs(mv) >= p["min_atr"] * atr
    k = np.flatnonzero(big & (mv != 0))
    i, ev, mv, atr = i[k], ev[k], mv[k], atr[k]
    msign = np.sign(mv).astype(int)
    if p["mode"] == "follow":
        side = msign
        stop = np.where(side > 0, l[i], h[i])
        t = _r_target(FAR_R)
    else:
        side = -msign
        stop = np.where(side < 0, h[i] + PAD_ATR * atr, l[i] - PAD_ATR * atr)
        t = (K_R, 1.0, K_PX, o[i], M_T2)
    with np.errstate(invalid="ignore", divide="ignore"):
        return _mk(i, side, stop, t[0], t[1], t[2], t[3], t[4], hold_window(ctx, i, HOLD_REL), kinds[ev], sub=ev,
                   x1=100.0 * mv / o[i], x2=mv / atr)


# ---------------------------------------------------------------- P12: crypto opening range at the US equity open
def orb_us_setups(ctx, p):
    if ctx.asset not in CRYPTO:
        return _empty()
    S = pb2.orb_setups(ctx, P3_RULE)
    if not len(S["i"]):
        return _empty()
    S = _subset(S, S["lab"] == US_LAB)
    E = pb2.orb_events(ctx, P3_RULE["or_len"])
    ev = S["ev"].astype(int)
    m = len(S["i"])
    S["lab"] = np.zeros(m, dtype=int)
    S["sub"] = np.zeros(m, dtype=int)
    S["x1"] = E["hi"][ev] if m else np.zeros(0)
    S["x2"] = E["lo"][ev] if m else np.zeros(0)
    S["xs"] = E["start"][ev].astype(float) if m else np.zeros(0)
    return S


# ---------------------------------------------------------------- dispatch
SETUP_FN = {"p6_vwap": vwap_setups, "p7_session": session_setups, "p8_fvg": fvg_setups, "p9_cascade": cascade_setups,
            "p10_round": round_setups, "p11_release": release_setups, "p12_orb_us": orb_us_setups}


def setups(book, ctx, p):
    """One variant (a dict) or a registered rule (a list of variants, setups merged)."""
    if isinstance(p, (list, tuple)):
        parts = [setups(book, ctx, q) for q in p]
        if book == "p12_orb_us":
            return parts[0] if parts else _empty()
        return _cat(parts)
    if not applies(book, p, ctx.asset):
        return _empty()
    return SETUP_FN[book](ctx, p)


def run(book, ctx, p=None):
    """-> (setups, kept trades) of one book (or variant) on one asset."""
    p = RULES[book] if p is None else p
    S = setups(book, ctx, p)
    return S, simulate(ctx, S)


def labels_for(book, asset=None):
    """The names behind a setup's `lab` code."""
    if book == "p7_session":
        return list(PLAY_LABELS)
    if book == "p11_release":
        return list(RELEASE_KINDS)
    if book == "p12_orb_us":
        return ["US equity open"]
    return list(UTC_SESSIONS)


# ---------------------------------------------------------------- words
def target_names(book, S, k):
    t1k, t2k, mode = int(S["t1k"][k]), int(S["t2k"][k]), int(S["mode"][k])
    sub = int(S["sub"][k])
    if book == "p8_fvg" and mode == M_SPLIT:
        return "impulse extreme", "2R / extreme + 1R", "half at T1, the rest at T2, stop to entry after T1"
    if t2k == K_R and S["t2v"][k] >= FAR_R:
        return "1R", "none (time exit)", "held to the time limit"
    n2 = "%gR" % S["t2v"][k] if t2k == K_R else {
        "p6_vwap": "VWAP", "p7_session": "the far side of the Asian range", "p9_cascade": "half the cascade back",
        "p10_round": "the round number", "p11_release": "the release bar's open"}.get(book, "target")
    del t1k, sub
    return "1R", n2, "everything at T2"


def _head(book, ctx, S, k):
    a = SHORT_NAME.get(ctx.asset, ctx.asset)
    i, side, sub = int(S["i"][k]), int(S["side"][k]), int(S["sub"][k])
    x1, x2 = float(S["x1"][k]), float(S["x2"][k])
    t = _hm(ctx.ms[i])
    if book == "p6_vwap":
        if sub == 0:
            return ("VWAP fade, %s: the %s bar closed at %s after a close %s the daily VWAP band %s (VWAP %s), in a range" % (
                a, t, _px(ctx.c[i]), "above" if side < 0 else "below", _px(x2), _px(x1)))
        return ("VWAP reclaim, %s: with the higher-timeframe bias %s, the %s bar tagged the daily VWAP %s and closed back %s it at %s" % (
            a, "LONG" if side > 0 else "SHORT", t, _px(x1), "above" if side > 0 else "below", _px(ctx.c[i])))
    if book == "p7_session":
        if sub == 0:
            return ("London false move, %s: the Asian range was %s to %s; after the London open price took out its %s and the %s bar "
                    "closed back inside at %s" % (a, _px(x2), _px(x1), "high" if side < 0 else "low", t, _px(ctx.c[i])))
        if sub == 1:
            return "Asian-range breakout, %s: the %s bar closed %s the Asian range %s to %s at %s" % (
                a, t, "above" if side > 0 else "below", _px(x2), _px(x1), _px(ctx.c[i]))
        return "New York afternoon drift, %s: weekday close at %s UTC, %s" % (a, _hm(ctx.ms[i] + BAR_MS), _px(ctx.c[i]))
    if book == "p8_fvg":
        return ("%s, %s: price came back into a %s zone %s to %s and the %s bar held it at %s" % (
            "Fair value gap" if sub == 0 else "Order block", a, "bullish" if side > 0 else "bearish",
            _px(min(x1, x2)), _px(max(x1, x2)), t, _px(ctx.c[i])))
    if book == "p9_cascade":
        return ("Liquidation cascade, %s: price %s %.1f hourly ATRs within 4 bars on %.1fx volume; %s at the %s close %s" % (
            a, "fell" if (side < 0) == (sub == 0) else "rose", x1, x2, "continuation" if sub == 0 else "the first reversal bar",
            t, _px(ctx.c[i])))
    if book == "p10_round":
        if sub == 0:
            return "Round number, %s: price came within reach of %s; the %s bar closed at %s" % (a, _px(x1), t, _px(ctx.c[i]))
        return "Round number, %s: the first touch of %s in 24 hours was rejected; the %s bar closed at %s" % (
            a, _px(x1), t, _px(ctx.c[i]))
    if book == "p11_release":
        _ms, _k, titles = ctx.events()
        title = titles[sub] if 0 <= sub < len(titles) else "release"
        return "Release, %s, %s: the %s UTC release bar moved %+.2f%% (%.1f hourly ATRs)" % (a, title, t, x1, abs(x2))
    st = int(S["xs"][k]) if "xs" in S else int(ctx.ms[i])
    return ("US-open range, %s: the %s-%s UTC range was %s to %s; the %s bar closed %s it at %s" % (
        a, _hm(st), _hm(st + 30 * 60000), _px(x2), _px(x1), t, "above" if side > 0 else "below", _px(ctx.c[i])))


def sentence(book, ctx, S, T, j):
    k = int(T["k"][j])
    st = int(T["status"][j])
    side = int(S["side"][k])
    n1, n2, how = target_names(book, S, k)
    plan = "%s %s%s, stop %s, T1 (%s) %s, T2 (%s) %s, %s" % (
        "LONG" if side > 0 else "SHORT", "at the next open (about) " if st == ST_WAIT else "", _px(T["entry"][j]),
        _px(S["stop"][k]), n1, _px(T["t1"][j]), n2, "-" if T["t2"][j] != T["t2"][j] or abs(T["t2"][j] - T["entry"][j]) >
        (FAR_R - 1) * abs(T["risk"][j]) else _px(T["t2"][j]), how)
    out = "%s: %s." % (_head(book, ctx, S, k), plan)
    if st == ST_CLOSED:
        w = WHY[int(T["why"][j])]
        res = {"STOP": "stopped" + (" at break-even after T1" if T["t1_hit"][j] else ""), "T1": "T1 reached",
               "T2": "T2 reached", "TIME": "closed at the time limit" + (" after T1" if T["t1_hit"][j] else "")}[w]
        out += " Result: %s, exit %s, %+.2fR, %+.2f USD after %.2f USD fees." % (
            res, _px(T["exit"][j]), T["r"][j], T["pnl"][j], T["fees"][j])
    elif st == ST_OPEN:
        out += " Open, marked at %s: %+.2fR." % (_px(ctx.c[-1]), T["r"][j])
    else:
        out += " Waiting for the next open."
    return out


def _row(book, ctx, S, T, j):
    k = int(T["k"][j])
    st = int(T["status"][j])
    rnd = lambda v, d=6: None if v is None or v != v else round(float(v), d)   # noqa: E731
    n1, n2, _how = target_names(book, S, k)
    i = int(S["i"][k])
    labs = labels_for(book, ctx.asset)
    lab = int(S["lab"][k])
    closed, opened = st == ST_CLOSED, st in (ST_OPEN, ST_CLOSED)
    t2 = T["t2"][j]
    if t2 == t2 and abs(t2 - T["entry"][j]) > (FAR_R - 1) * abs(T["risk"][j]):
        t2 = None                                                      # a time-exit book has no second target
    return {"book": book, "asset": ctx.asset, "status": STATUS[st], "side": int(S["side"][k]),
            "setup_utc": _utc(int(ctx.ms[i]) + BAR_MS), "entry_utc": _utc(int(ctx.ms[i + 1])) if opened else None,
            "entry": rnd(T["entry"][j]) if opened else None, "est_entry": rnd(T["entry"][j]) if st == ST_WAIT else None,
            "stop": rnd(S["stop"][k]), "target_1": rnd(T["t1"][j]), "target_2": rnd(t2),
            "t1_name": n1, "t2_name": n2,
            "exit_utc": _utc(int(T["exit_ms"][j])) if closed else None, "exit": rnd(T["exit"][j]) if closed else None,
            "why_out": WHY[int(T["why"][j])] if opened else "OPEN", "t1_hit": bool(T["t1_hit"][j]),
            "r": rnd(T["r"][j], 3) if opened else None, "pnl_usd": rnd(T["pnl"][j], 2) if opened else None,
            "fees_usd": rnd(T["fees"][j], 2) if opened else None,
            "session": labs[lab] if 0 <= lab < len(labs) else None, "text": sentence(book, ctx, S, T, j)}


# ---------------------------------------------------------------- live interface
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
            S = setups(book, ctx, RULES[book])
            if not len(S["i"]):
                continue
            S = _subset(S, ctx.ms[S["i"]] + BAR_MS >= reg_ms)
            T = simulate(ctx, S)
            ret = RETIRED.get(book)
            ret_ms = int(pd.Timestamp(ret, tz="UTC").value // 10**6) if ret else None
            for j in range(len(T["k"])):
                if ret_ms is not None:
                    if int(T["status"][j]) == ST_WAIT:                # WAITING: it cannot fill before the next bar opens,
                        now_eff = int(now_ms) if now_ms is not None else int(time.time() * 1000)   # nor before now
                        fill_ms = max(int(ctx.ms[-1]) + BAR_MS, now_eff)
                    else:
                        fill_ms = int(ctx.ms[int(S["i"][int(T["k"][j])]) + 1])
                    if fill_ms >= ret_ms:
                        continue                                      # retired: nothing entered from the stamp on
                rows.append(_row(book, ctx, S, T, j))
    return rows


def rule_text(book, p=None):
    p = RULES[book] if p is None else p
    if isinstance(p, (list, tuple)):
        return " PLUS ".join(rule_text(book, q) for q in p)
    if book == "p6_vwap":
        if p["mode"] == "fade":
            reg = "the 1h ADX(14) is below 20" if p["regime"] == "adx" else "the engine's higher-timeframe bias is off"
            ent = ("on the first 15m close beyond the daily VWAP %.1f-sigma band" % p["k"] if p["entry"] == "close"
                   else "on the first 15m close back inside the daily VWAP %.1f-sigma band after closes beyond it (still on the far side of VWAP)" % p["k"])
            return ("VWAP fade: when %s, fade %s, at the next open; stop beyond the excursion's extreme + 0.25 hourly ATR; "
                    "target %s; time exit after 32 bars." % (reg, ent, "the daily VWAP at the decision" if p["target"] == "vwap" else "2R"))
        return ("VWAP reclaim: with the engine's higher-timeframe bias on, trade the day's first 15m bar that tags the daily VWAP "
                "and closes back on the trend side (the bar before also on that side), at the next open; stop %s; target %s; time "
                "exit after 32 bars." % ("beyond the tag bar's extreme + 0.25 hourly ATR" if p["stop"] == "bar"
                                         else "1 hourly ATR beyond VWAP", p["target"]))
    if book == "p7_session":
        if p["play"] == "judas":
            return ("London false move (gold, silver, USDJPY, BTC, ETH): Asian range = 00:00 UTC to the London open (08:00 London). "
                    "If the first take-out of that range in the first %d bars after the London open closes back inside within 4 bars, "
                    "fade it at the next open; stop beyond the take-out extreme + 0.25 hourly ATR; target %s; flat 8 hours after the "
                    "London open." % (p["window"], "the far side of the Asian range" if p["target"] == "opp" else "2R"))
        if p["play"] == "abo":
            return ("Asian-range breakout (gold, USDJPY): the first 15m close outside the Asian range in the first 4 London hours is "
                    "traded at the next open; stop at the range's %s; target %s; flat 8 hours after the London open." % (
                        "opposite side" if p["stop"] == "far" else "middle", p["target"]))
        return ("New York afternoon drift (BTC, ETH): LONG at the open after each weekday %02d:00 UTC close; stop %.1f hourly ATRs "
                "below the entry; no target; exit at the close 4 hours later." % (p["hour"], p["stop_atr"]))
    if book == "p8_fvg":
        z = ("the gap itself" if p["zone"] == "fvg" else "the last opposite candle before the impulse (within 5 bars): the order block")
        tg = "2R" if p["target"] == "2R" else "half at the impulse extreme (1R if nearer than 0.5R), the rest at 2R or 1R past it"
        return ("Fair value gap: three candles where the first's high is below the third's low (bullish; mirror bearish), the middle "
                "candle in the move's direction, gap at least %.1f x ATR(15m). Zone = %s. The first bar within 12 hours that trades "
                "into the zone, if its close has not gone through the zone's far edge, is traded in the impulse direction at the "
                "next open; stop beyond the far edge + 0.25 hourly ATR; target %s; time exit after 32 bars%s." % (
                    p["k"], z, tg, "; only with the higher-timeframe bias" if p.get("filter") == "bias" else ""))
    if book == "p9_cascade":
        base = ("Cascade (BTC, ETH): price moves at least %.0f hourly ATRs (ATR before the move) from the 4-bar extreme to the close, "
                "volume of those 4 bars at least %.1fx the previous day's average, taker buying at most 45%% (drop) / at least 55%% "
                "(rise) of it; first bar only" % (p["x"], p["vol"]))
        f = "; only when funding is at or below its 30-day median after a drop (at or above after a rise)" if p.get("filter") == "funding" else ""
        if p["mode"] == "cont":
            return base + "%s. Trade WITH it at the next open; stop at the 4-bar extreme where the move began; target %s; exit after 16 bars." % (f, p["target"])
        return base + ("%s. Wait up to 8 bars for a bar that closes beyond the previous bar's extreme against the move; FADE the cascade "
                       "at the next open; stop beyond the cascade's extreme + 0.25 hourly ATR; target %s; exit after 16 bars." % (
                           f, "2R" if p["target"] == "2R" else "half the cascade back"))
    if book == "p10_round":
        steps = ", ".join("%s %g" % (SHORT_NAME[a], s) for a, s in ROUND_STEPS[p["grid"]].items())
        if p["mode"] == "magnet":
            return ("Round-number magnet (%s): when the close first comes within %.1f hourly ATRs of the nearest round number, not touched "
                    "in the last 4 hours, trade toward it at the next open; target the number; stop %s; exit after 16 bars." % (
                        steps, p["y"], "half the distance behind the entry (a 2R target)" if p["stop"] == "half" else "the same distance behind (1R)"))
        return ("Round-number rejection (%s): the first touch of a round number in 24 hours whose bar closes back on the near side is "
                "faded at the next open; stop beyond the bar's extreme + 0.25 hourly ATR; target %s; exit after 16 bars." % (steps, p["target"]))
    if book == "p11_release":
        if p["mode"] == "follow":
            return ("Release follow-through (FOMC, payrolls, other US high-impact releases; not CPI): when the release bar moves at least "
                    "%.1f hourly ATRs open to close, take its side at the next open; stop beyond its far extreme; exit after 16 bars "
                    "(4 hours)." % p["min_atr"])
        return ("Release fade (FOMC, payrolls, other US high-impact releases; not CPI): when the release bar moves at least %.1f hourly "
                "ATRs, fade it at the next open; stop beyond its extreme + 0.25 hourly ATR; target its open; exit after 16 bars." % p["min_atr"])
    return ("US-open range (BTC, ETH): the first 30 minutes from the US cash open (09:30 New York, NYSE days); the first 15m close outside "
            "it, in the direction of the engine's higher-timeframe bias, is traded at the next open; stop at the range's opposite side; "
            "target 2R; flat 8 hours after the open. FORWARD ONLY: found in the playbook2 session breakdown.")


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
        note = "Paper only. Registered rule graded forward from %s; history does not prove it." % facts["registered"]
        if facts.get("forward_only"):
            note = ("Paper only. FOUND in the history (playbook2 session breakdown), so it is graded forward only, from %s."
                    % facts["registered"])
        if book in RETIRED:
            note = ("Retired %s UTC (owner): the post-mortem found no pull toward round numbers even before costs, live as on "
                    "2019-2026 history. No new trades; the live record is kept." % RETIRED[book])
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"],
                     "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r[k]) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit", "why_out",
                                                          "r", "pnl_usd", "text")) for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "note": note}
        if book in RETIRED:
            out[book]["retired"] = RETIRED[book]
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"])
