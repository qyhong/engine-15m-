# -*- coding: utf-8 -*-
"""playbook4 -- the strategy loop's two best round-2 rules, run FORWARD as paper books. PAPER ONLY. NOT PASSED.

From the strategy loop (research/harness, round 2); NOT passed: each failed fold share and significance on
development data; they run forward on paper to collect unseen evidence. The owner approved this on 12 Nov 2026
(local time; 11 Nov UTC): "Yes, add both". Registry: research/HYPOTHESES.md ("Forward paper books from round 2").
Loop rules and log: research/harness/LOOP.md (loop status stays "paused"; these books change no loop rule and add no
variant: they are frozen copies of rules already counted in round 2).

L1  "H29 H30 1.5x/0x spot" (book p4_h30spot). d = the daily 30-day momentum sign, decided at the close of the 15m bar
    ending 00:00 UTC (log close now / log close 2,880 bars ago). Exposure 1.5x when d > 0, 0 when d < 0. A new
    direction (or an increase) waits up to 48 bars for a 15m close at or below EMA20 - 1.0 x ATR14 (the "E2
    pullback"; flat while waiting), else enters after bar 48; a decrease is done at once.
L2  "H29 H31 trail 4 ATR spot" (book p4_h31trail). Wanted exposure min(2.0, 0.60 / rv) when d > 0, else 0, where rv
    is the 672-bar realised vol of 15m log returns x sqrt(35,040). The held exposure changes when the wanted sign
    differs from it or |wanted - held| >= 0.25; E2 pullback on a new direction. While long, a 15m close below (the
    highest close since entry - 4 x the 14-day Wilder ATR of the last closed daily bars) goes flat; re-entry only at
    a later 00:00 UTC decision with d > 0, then with the E2 pullback.

Every parameter is the round-2 one (research/harness/round2.py: R2.h30(1.5, 0.0), R2.h31(4.0), pullback, resize,
trailing_exit, extra_features; research/harness/core.py: features, Market, the cost model). This module reimplements
them without importing the harness or engine15.rl, and tests/test_playbook4.py proves it reproduces the harness's
targets, positions and per-bar net returns on history.

ACCOUNTING (as in round 2, H29 "spot long legs"). A target decided at the close of bar t is held from the open of bar
t + 1. Per bar, as a fraction of the book's equity: gross = position x (next open / open - 1); fee 0.10% a side of
|trade| (the engine's crypto fee); half spread 0.5 bp of |trade|; slippage 0.10 x (the 96-bar per-bar vol known at the
decision) x |trade|; funding = the funded part of the position x the rate settled at the bar's end, where the long
part up to 1x is spot (no funding) and only exposure above 1x pays perp funding. Live Mind 15 trades perps (a long
pays funding on all of it); these books hold longs up to 1x as spot, exactly as the loop graded them, so the
comparison with the loop is like for like and the comparison with the main books is stated, not hidden.

FORWARD ONLY. Each market (BTCUSDT, ETHUSDT) has its own $10,000 paper book from REGISTERED. A trade is one run of
non-zero exposure (flat to flat; re-sizes inside it belong to it). Only trades whose ENTRY decision (the close of the
bar where the target turned on) comes after REGISTERED are forward trades and enter the book; anything the rule held
from before is warm-up and is shown as the rule's state, never counted. The book is recomputed from the bars at each
step from a FIXED warm-up anchor (REGISTERED - WARMUP_DAYS), holds no state, and the same bars give the same rows.

Rows (docs/PLAYBOOK_INTERFACE.md): status WAITING / OPEN / CLOSED, side 1 (long only), stop = the trailing level for
L2 (None for L1), no targets; why_out "STOP" (L2's trailing exit), "TREND" (the daily momentum turned) or "OPEN";
r is None (these books have no fixed risk unit); pnl_usd, fees_usd (the 0.10% fee) and costs_usd (spread, slippage,
funding) in the book's compounding dollars.
"""
import math

import numpy as np
import pandas as pd

from . import data

REGISTERED = "2026-11-11 20:00"     # UTC: forward start (12 Nov 2026 04:00 local, UTC+8); owner-approved 12 Nov 2026
STAKE = 10000.0
WARMUP_DAYS = 450                   # EWMs (daily ATR, alpha 1/14) converge to < 1e-12 well inside this
BAR_MS = 900000
DAY_MS = 86400000
BPY = 365 * 96                      # bars a year (engine15.rl.metrics.BARS_PER_YEAR)
ASSETS = ("BTCUSDT", "ETHUSDT")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}

# ---------------------------------------------------------------- frozen round-2 parameters (do not change)
FEE = 0.0010                        # a side (core.FEE_HEAD; engine15/config.py cost_side for crypto)
HALF_SPREAD_BPS = 0.5               # core.COST_KW
SLIP_COEF = 0.10
SLIP_WIN = 96
FUND_SNAP_S = 60                    # funding stamps within 60 s after a 15m grid time settle on it
MOM_DAYS = 30                       # benchmarks.momentum: 30 days x 96 bars, decided at the 00:00 UTC close
E2_A, E2_W = 1.0, 48                # E2 pullback: close <= EMA20 - 1.0 x ATR14, wait at most 48 bars
RESIZE_STEP = 0.25
H30_U, H30_D = 1.5, 0.0             # H30_KEYS (1.5, 0.0)
H31_VT, H31_LMAX, H31_M = 0.6, 2.0, 4.0   # R2.h31: vt 0.6, Lmax 2.0; H31_KEYS 4.0

NOT_PASSED = ("From the strategy loop; NOT passed: it failed fold share and significance on development data; "
              "running forward on paper to collect unseen evidence.")
SPOT_NOTE = ("Live Mind 15 trades perps; this book accounts longs up to 1x as spot (no funding) and charges perp "
             "funding only on exposure above 1x, exactly as the loop graded it, so the comparison is honest.")

BOOKS = {
    "p4_h30spot": {"title": "Loop book A: H29 H30 1.5x/0x spot (from the strategy loop; NOT passed)",
                   "short": "Loop book A", "hypothesis": "H29-H30 forward", "registered": REGISTERED,
                   "assets": ASSETS, "loop_id": "R2-H29 H30 1.5x/0x spot longs",
                   "scoreboard_title": "Strategy: loop book A, H29 H30 1.5x/0x spot (NOT passed, forward paper)"},
    "p4_h31trail": {"title": "Loop book B: H29 H31 vol-target + 4 ATR trail, spot (from the strategy loop; NOT passed)",
                    "short": "Loop book B", "hypothesis": "H29-H31 forward", "registered": REGISTERED,
                    "assets": ASSETS, "loop_id": "R2-H29 H31 trail 4 ATR spot longs",
                    "scoreboard_title": "Strategy: loop book B, H29 H31 trail 4 ATR spot (NOT passed, forward paper)"},
}

LAST_STATE = {}                     # filled by step(): per book, per asset, the book and rule state for page_block


def reg_ms():
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


def _to_ms(index):
    return np.asarray(pd.DatetimeIndex(index).as_unit("ms").asi8, dtype="int64")


# ---------------------------------------------------------------- readings (row t uses bars <= t only)
def features(bars):
    """bars: 15m frame (open/high/low/close). -> dict of arrays, as core.features + round2.extra_features."""
    b = bars[["open", "high", "low", "close"]].astype(float)
    c = b["close"].values
    close_ms = _to_ms(b.index) + BAR_MS
    lr = np.log(b["close"]).diff()
    F = {"o": b["open"].values, "c": c, "close_ms": close_ms, "n": len(c)}
    F["ema20"] = pd.Series(c).ewm(span=20, adjust=False).mean().values
    h, lo = b["high"].values, b["low"].values
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    F["atr14"] = pd.Series(tr).ewm(alpha=1 / 14.0, adjust=False).mean().values
    F["rv_ann"] = lr.rolling(672, min_periods=96).std().values * math.sqrt(BPY)
    w = MOM_DAYS * int(DAY_MS // BAR_MS)
    r = np.log(b["close"]).diff(w).values
    decide = (close_ms % DAY_MS) == 0
    sig = np.sign(np.nan_to_num(r, nan=0.0))
    tgt = np.full(len(c), np.nan)
    tgt[decide] = sig[decide]
    F["d"] = pd.Series(tgt, index=b.index).ffill().fillna(0.0).values
    F["is_daily"] = decide
    F["mom30"] = r
    bb = bars[["open", "high", "low", "close"]].astype(float).assign(volume=0.0, taker_buy=0.0)
    d1 = data.resample(bb, "1D")
    pcd = d1["close"].shift(1)
    trd = np.maximum(d1["high"] - d1["low"], np.maximum((d1["high"] - pcd).abs(), (d1["low"] - pcd).abs()))
    atr = trd.ewm(alpha=1 / 14.0, adjust=False).mean()
    F["atr1d"] = data.htf_on_15(bb, "1D", atr).values.astype(float)
    F["vol"] = lr.rolling(SLIP_WIN, min_periods=2).std().fillna(0.0).values
    return F


# ---------------------------------------------------------------- the frozen state machines (round2.py)
def resize(want, step=RESIZE_STEP):
    w = np.nan_to_num(np.asarray(want, dtype=float)).tolist()
    out, cur = [0.0] * len(w), 0.0
    for t, x in enumerate(w):
        if np.sign(x) != np.sign(cur) or abs(x - cur) >= step:
            cur = x
        out[t] = cur
    return np.asarray(out)


def pullback(want, F, a=E2_A, W=E2_W, on_increase=False):
    """round2.pullback, plus: wait[t] = waiting for an E2 entry from flat, pend[t] = the exposure waited for,
    since[t] = the bar the wait began."""
    lo = (F["ema20"] - a * F["atr14"]).tolist()
    hi = (F["ema20"] + a * F["atr14"]).tolist()
    c = np.asarray(F["c"], dtype=float).tolist()
    w = np.nan_to_num(np.asarray(want, dtype=float)).tolist()
    n = len(w)
    out, wait, pend, since = [0.0] * n, [False] * n, [0.0] * n, [-1] * n
    cur, pending, waiting, wf = 0.0, 0.0, False, 0
    for t in range(n):
        x = w[t]
        target_now = pending if waiting else cur
        if x != target_now:
            sc = x != 0 and np.sign(x) != np.sign(cur)
            inc = on_increase and x != 0 and np.sign(x) == np.sign(cur) and abs(x) > abs(cur)
            if sc or inc:
                if not (waiting and np.sign(pending) == np.sign(x)):
                    wf = t
                pending, waiting = x, True
                if sc:
                    cur = 0.0
            else:
                cur, waiting = x, False
        if waiting:
            s = np.sign(pending)
            if (c[t] <= lo[t] if s > 0 else c[t] >= hi[t]) or t - wf >= W:
                cur, waiting = pending, False
        out[t] = cur
        if waiting and cur == 0:
            wait[t], pend[t], since[t] = True, pending, wf
    return np.asarray(out), np.asarray(wait), np.asarray(pend), np.asarray(since)


def trailing_exit(base, F, m, a=E2_A, W=E2_W):
    """round2.trailing_exit, plus per bar: trail level (peak - m x daily ATR) while long, 'blocked' (flat after a
    trailing exit until a 00:00 UTC decision with d > 0), 're-entry wait' and the bar it began, 'exit fired here'."""
    b = np.asarray(base, dtype=float).tolist()
    c = np.asarray(F["c"], dtype=float).tolist()
    atr = np.nan_to_num(F["atr1d"], nan=np.inf).tolist()
    daily = F["is_daily"].tolist()
    d = F["d"].tolist()
    lo = (F["ema20"] - a * F["atr14"]).tolist()
    n = len(b)
    out, level, blk, rw, rws, fired = [0.0] * n, [np.nan] * n, [False] * n, [False] * n, [-1] * n, [False] * n
    blocked, waiting, wf, peak, prev = False, False, 0, 0.0, 0.0
    for t in range(n):
        if blocked:
            if daily[t] and d[t] > 0:
                blocked, waiting, wf = False, True, t
            else:
                out[t] = prev = 0.0
                blk[t] = True
                continue
        if waiting:
            if b[t] <= 0:
                waiting = False
            elif c[t] <= lo[t] or t - wf >= W:
                waiting = False
            else:
                out[t] = prev = 0.0
                rw[t], rws[t] = True, wf
                continue
        x = b[t]
        if x > 0:
            peak = c[t] if prev <= 0 else max(peak, c[t])
            if c[t] < peak - m * atr[t]:
                blocked = True
                out[t] = prev = 0.0
                blk[t] = fired[t] = True
                continue
            level[t] = peak - m * atr[t]
        out[t] = prev = x
    return (np.asarray(out), np.asarray(level), np.asarray(blk), np.asarray(rw), np.asarray(rws),
            np.asarray(fired))


def targets(F):
    """-> {book: dict(target=..., wait=..., pend=..., since=..., level=..., fired=...)} (target decided at each close)."""
    d = F["d"]
    want_a = np.where(d > 0, H30_U, np.where(d < 0, H30_D, 0.0))
    ta, wa, pa, sa = pullback(want_a, F, on_increase=True)
    rv = np.where(F["rv_ann"] > 0, F["rv_ann"], np.nan)
    k = np.nan_to_num(H31_VT / rv, nan=1.0)
    want_b = np.where(d > 0, np.minimum(H31_LMAX, k), 0.0)
    base, wb, pb_, sb = pullback(resize(want_b), F)
    tb, level, blk, rw, rws, fired = trailing_exit(base, F, H31_M)
    wait_b = rw | (wb & ~blk & (tb == 0))
    pend_b = np.where(rw, base, np.where(wait_b, pb_, 0.0))
    since_b = np.where(rw, rws, np.where(wait_b, sb, -1))
    n = F["n"]
    return {"p4_h30spot": {"target": ta, "wait": wa, "pend": pa, "since": sa, "level": np.full(n, np.nan),
                           "fired": np.zeros(n, dtype=bool)},
            "p4_h31trail": {"target": tb, "wait": wait_b, "pend": pend_b, "since": since_b, "level": level,
                            "fired": fired}}


# ---------------------------------------------------------------- costs (core.Market, spot long legs)
def settlement_ms(raw_ms, interval_ms=BAR_MS, snap_s=FUND_SNAP_S):
    raw = np.asarray(raw_ms, dtype="int64")
    floor = raw - raw % interval_ms
    ceil = np.where(raw % interval_ms == 0, raw, floor + interval_ms)
    return np.where(raw - floor <= snap_s * 1000, floor, ceil).astype("int64")


def funding_frame(series):
    """engine15.data.load_funding output (rates keyed by stamp) -> frame rate / settle_ms (on the 15m grid)."""
    if series is None or not len(series):
        return pd.DataFrame({"rate": [], "settle_ms": []})
    raw = _to_ms(series.index)
    return pd.DataFrame({"rate": np.asarray(series.values, dtype=float), "settle_ms": settlement_ms(raw)},
                        index=series.index)


def funding_on_bars(close_ms, fund):
    out = np.zeros(len(close_ms))
    if fund is None or not len(fund) or not len(close_ms):
        return out
    s = np.asarray(fund["settle_ms"], dtype="int64")
    r = np.asarray(fund["rate"], dtype=float)
    k = np.searchsorted(close_ms, s, side="right") - 1
    ok = (k >= 0) & (s <= close_ms[-1])
    np.add.at(out, k[ok], r[ok])
    return out


def market(F, fund):
    o, c = F["o"], F["c"]
    nxt = np.append(o[1:], c[-1])
    vd = np.zeros_like(F["vol"])
    vd[1:] = F["vol"][:-1]
    return {"r_px": nxt / o - 1.0, "vol_dec": vd, "rate": funding_on_bars(F["close_ms"], fund)}


def funded(pos):
    """Spot long legs: only exposure above 1x (and any short) pays funding."""
    return np.minimum(pos, 0.0) + np.maximum(pos - 1.0, 0.0)


def costs_from_pos(pos, M, fee=FEE):
    """Held position per bar -> dict of per-bar fractions of equity, in core.Market.frame's order."""
    trade = np.diff(pos, prepend=0.0)
    a = np.abs(trade)
    gross = pos * M["r_px"]
    hs = HALF_SPREAD_BPS * 1e-4 * a
    sl = SLIP_COEF * M["vol_dec"] * a
    fu = funded(pos) * M["rate"]
    fe = fee * a
    return {"pos": pos, "trade": trade, "gross": gross, "fee": fe, "spread": hs, "slippage": sl, "funding": fu,
            "r_net": gross - fe - hs - sl - fu}


def frame(target, M, fee=FEE):
    t = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    pos = np.zeros_like(t)
    pos[1:] = t[:-1]
    return costs_from_pos(pos, M, fee)


def compute(bars, fund=None):
    """bars (15m frame), funding frame (rate / settle_ms) -> (features, market, {book: targets + frame})."""
    F = features(bars)
    M = market(F, fund)
    out = {}
    for book, T in targets(F).items():
        T = dict(T)
        T["frame"] = frame(T["target"], M)
        out[book] = T
    return F, M, out


# ---------------------------------------------------------------- forward trades
def runs(pos):
    """Runs of non-zero held exposure: [(s, e)] with pos[s..e] != 0 and flat on both sides."""
    nz = np.asarray(pos) != 0
    out, s = [], None
    for t, v in enumerate(nz.tolist()):
        if v and s is None:
            s = t
        elif not v and s is not None:
            out.append((s, t - 1))
            s = None
    if s is not None:
        out.append((s, len(nz) - 1))
    return out


def forward_book(T, F, M, rms):
    """The $10,000 forward book: the rule's position only inside runs whose entry decision (the close of bar s - 1)
    is after REGISTERED. -> (trades, book frame, equity)."""
    pos = T["frame"]["pos"]
    cm = F["close_ms"]
    keep = np.zeros(len(pos))
    trades = []
    for s, e in runs(pos):
        if s == 0 or cm[s - 1] <= rms:
            continue
        keep[s:e + 1] = 1.0
        trades.append({"s": s, "e": e})
    posb = pos * keep
    fb = costs_from_pos(posb, M)
    eq = STAKE * np.cumprod(1.0 + fb["r_net"])
    n = len(pos)
    for t in trades:
        s, e = t["s"], t["e"]
        x = e + 1                                         # the bar whose open fills the exit
        closed = x < n
        last = x if closed else n - 1
        e0 = eq[s - 1]
        eprev = eq[s - 1:last]                            # equity at the start of each bar s..last
        seg = slice(s, last + 1)
        t.update(closed=closed, x=x if closed else None, e0=e0, e1=eq[last],
                 pnl=float(eq[last] - e0), fees=float(np.sum(fb["fee"][seg] * eprev)),
                 costs=float(np.sum((fb["spread"][seg] + fb["slippage"][seg] + fb["funding"][seg]) * eprev)),
                 funding=float(np.sum(fb["funding"][seg] * eprev)),
                 entry=float(F["o"][s]), exit=float(F["o"][x]) if closed else None,
                 x_entry=float(pos[s]), x_max=float(np.max(pos[s:e + 1])), x_now=float(pos[e]),
                 resizes=int(np.count_nonzero(np.diff(pos[s:e + 1]))),
                 trail_exit=bool(T["fired"][e]) if closed else False)
    return trades, fb, eq


def bh_spot(F, M, rms):
    """Spot buy-and-hold over the same forward span: 1x long decided at the first close after REGISTERED."""
    tgt = (F["close_ms"] > rms).astype(float)
    return STAKE * np.cumprod(1.0 + frame(tgt, M)["r_net"])


def _dd(eq):
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.max(1.0 - eq / peak))


# ---------------------------------------------------------------- words
def _px(v):
    if v is None or v != v:
        return "n/a"
    a = abs(v)
    return "{:,.0f}".format(v) if a >= 10000 else "{:,.1f}".format(v) if a >= 1000 else "{:,.2f}".format(v)


def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _xs(x):
    if x <= 1.0:
        return "%.2fx spot" % x
    return "%.2fx (1x spot + %.2fx perp)" % (x, x - 1.0)


def sentence(book, asset, t, F, T):
    a = SHORT_NAME.get(asset, asset)
    cm, s = F["close_ms"], t["s"]
    name = BOOKS[book]["short"]
    if book == "p4_h30spot":
        head = "%s, %s: long %s from %s at %s UTC (entry decided at the %s UTC close; daily 30-day momentum up)" % (
            name, a, _xs(t["x_entry"]), _px(t["entry"]), _utc(cm[s - 1]), _utc(cm[s - 1]))
    else:
        head = "%s, %s: long %s from %s at %s UTC (entry decided at the %s UTC close; momentum up, sized to 60%% a year vol)" % (
            name, a, _xs(t["x_entry"]), _px(t["entry"]), _utc(cm[s - 1]), _utc(cm[s - 1]))
        if t["resizes"]:
            head += ", re-sized %d time%s, now %s" % (t["resizes"], "" if t["resizes"] == 1 else "s", _xs(t["x_now"]))
    if t["closed"]:
        why = ("the trailing stop (a 15m close below the highest close since entry minus 4 x daily ATR)"
               if t["trail_exit"] else "the daily 30-day momentum turned down")
        out = "%s. Closed at %s on %s UTC after %s: %+.2f%%, %+.2f USD after %.2f USD fees and %.2f USD spread, slippage and funding." % (
            head, _px(t["exit"]), _utc(cm[t["e"]]), why, 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["costs"])
    else:
        out = "%s. Open, marked at the %s UTC close %s: %+.2f%%, %+.2f USD so far (fees %.2f USD)" % (
            head, _utc(cm[-1]), _px(F["c"][-1]), 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"])
        lv = T["level"][-1]
        out += (", trailing stop about %s." % _px(lv)) if lv == lv else "."
    return out + " Paper, forward, NOT a passed rule."


def waiting_sentence(book, asset, F, T):
    a = SHORT_NAME.get(asset, asset)
    cm, i = F["close_ms"], len(F["c"]) - 1
    st = int(T["since"][i])
    left = max(E2_W - (i - st), 0)
    lvl = F["ema20"][i] - E2_A * F["atr14"][i]
    return ("%s, %s: the rule wants %s long since the %s UTC close and waits for a 15m close at or below EMA20 - ATR14 "
            "(now %s, last close %s), else it enters after %d more bar%s. Paper, forward, NOT a passed rule." % (
                BOOKS[book]["short"], a, _xs(float(T["pend"][i])), _utc(cm[st]), _px(lvl), _px(F["c"][i]), left,
                "" if left == 1 else "s"))


def _rnd(v, k=6):
    return None if v is None or v != v else round(float(v), k)


def _row(book, asset, t, F, T):
    cm = F["close_ms"]
    lv = T["level"][-1] if not t["closed"] else np.nan
    return {"book": book, "asset": asset, "status": "CLOSED" if t["closed"] else "OPEN", "side": 1,
            "setup_utc": _utc(cm[t["s"] - 1]), "entry_utc": _utc(cm[t["s"] - 1]), "entry": _rnd(t["entry"]),
            "stop": _rnd(lv), "target_1": None, "target_2": None,
            "exit_utc": _utc(cm[t["e"]]) if t["closed"] else None, "exit": _rnd(t["exit"]),
            "why_out": ("STOP" if t["trail_exit"] else "TREND") if t["closed"] else "OPEN",
            "r": None, "pnl_usd": _rnd(t["pnl"], 2), "fees_usd": _rnd(t["fees"], 2), "costs_usd": _rnd(t["costs"], 2),
            "funding_usd": _rnd(t["funding"], 2), "pnl_pct": _rnd(100 * t["pnl"] / t["e0"], 3),
            "exposure_entry": _rnd(t["x_entry"], 4), "exposure_now": _rnd(t["x_now"], 4),
            "exposure_max": _rnd(t["x_max"], 4), "equity_before_usd": _rnd(t["e0"], 2),
            "equity_after_usd": _rnd(t["e1"], 2), "text": sentence(book, asset, t, F, T)}


def _state(book, asset, F, T, trades, eq, bh, rms):
    """The rule's and the book's state at the last closed bar (for page_block)."""
    i = len(F["c"]) - 1
    cm = F["close_ms"]
    tgt = float(T["target"][i])
    fwd = np.asarray(cm > rms)
    st = {"last_close_utc": _utc(cm[i]), "close": _rnd(F["c"][i]), "rule_exposure": _rnd(tgt, 4),
          "momentum_30d_pct": _rnd(100 * (math.exp(F["mom30"][i]) - 1) if F["mom30"][i] == F["mom30"][i] else None, 2),
          "daily_direction": int(F["d"][i]), "equity_usd": _rnd(eq[i] if len(eq) else STAKE, 2),
          "return_pct": _rnd(100 * (eq[i] / STAKE - 1) if len(eq) else 0.0, 3),
          "bh_spot_equity_usd": _rnd(bh[i] if len(bh) else STAKE, 2),
          "bh_spot_return_pct": _rnd(100 * (bh[i] / STAKE - 1) if len(bh) else 0.0, 3),
          "max_dd_pct": _rnd(100 * _dd(eq[fwd]), 3), "bh_max_dd_pct": _rnd(100 * _dd(bh[fwd]), 3),
          "forward_trades": len(trades), "closed": sum(1 for t in trades if t["closed"])}
    in_book = bool(trades) and not trades[-1]["closed"]
    if in_book:
        st["book_position"] = "long %s since %s UTC" % (_xs(trades[-1]["x_now"]), _utc(cm[trades[-1]["s"] - 1]))
    elif tgt != 0:
        rr = runs(T["frame"]["pos"])
        since = _utc(cm[rr[-1][0] - 1]) if rr and rr[-1][0] > 0 else "?"
        st["book_position"] = ("flat: the rule has been long %s since %s UTC, a warm-up position decided before the "
                               "forward start; the book waits for the rule's next entry" % (_xs(tgt), since))
    elif bool(T["wait"][i]):
        st["book_position"] = "flat, waiting for an E2 pullback entry"
    else:
        st["book_position"] = "flat (daily 30-day momentum %s)" % ("down" if F["d"][i] < 0 else "up; rule out after a trailing exit until a later 00:00 UTC decision" if F["d"][i] > 0 else "unknown")
    return st


# ---------------------------------------------------------------- live interface
def _load(asset):
    return data.load(asset), funding_frame(data.load_funding(asset))


def step(bars=None, now_ms=None, funding=None):
    """bars: {asset: 15m frame}; None loads BTCUSDT / ETHUSDT from disk. funding: {asset: frame rate / settle_ms}
    (None reads data/<asset>_funding.csv). -> rows (docs/PLAYBOOK_INTERFACE.md)."""
    rms = reg_ms()
    anchor = pd.Timestamp(REGISTERED, tz="UTC") - pd.Timedelta(days=WARMUP_DAYS)
    rows = []
    LAST_STATE.clear()
    for asset in ASSETS:
        try:
            if bars is None:
                df, fund = _load(asset)
            else:
                df = bars.get(asset)
                if df is None:
                    continue
                fund = (funding or {}).get(asset)
                if fund is None and funding is None:
                    fund = funding_frame(data.load_funding(asset))
        except Exception:
            continue
        df = df[df.index >= anchor]
        if now_ms is not None:
            df = df[_to_ms(df.index) + BAR_MS <= int(now_ms)]
        if len(df) < 200:
            continue
        if fund is not None and len(fund):
            last_close = int(_to_ms(df.index[-1:])[0]) + BAR_MS
            fund = fund[np.asarray(fund["settle_ms"], dtype="int64") <= last_close]
        F, M, R = compute(df, fund)
        bh = bh_spot(F, M, rms)
        for book, T in R.items():
            trades, fb, eq = forward_book(T, F, M, rms)
            for t in trades:
                rows.append(_row(book, asset, t, F, T))
            i = F["n"] - 1
            in_trade = bool(trades) and not trades[-1]["closed"]
            if not in_trade and bool(T["wait"][i]) and F["close_ms"][int(T["since"][i])] > rms:
                rows.append({"book": book, "asset": asset, "status": "WAITING", "side": 1,
                             "setup_utc": _utc(F["close_ms"][int(T["since"][i])]), "entry_utc": None, "entry": None,
                             "stop": None, "target_1": None, "target_2": None, "exit_utc": None, "exit": None,
                             "why_out": "OPEN", "r": None, "pnl_usd": None, "fees_usd": None,
                             "exposure_wanted": _rnd(float(T["pend"][i]), 4),
                             "text": waiting_sentence(book, asset, F, T)})
            LAST_STATE.setdefault(book, {})[asset] = _state(book, asset, F, T, trades, eq, bh, rms)
    return rows


def _totals(closed):
    n = len(closed)
    if not n:
        return {"trades": 0, "won": 0, "win_rate_pct": None, "avg_r": None, "net_usd": 0.0, "fees_usd": 0.0,
                "costs_usd": 0.0}
    won = sum(1 for r in closed if r["pnl_usd"] > 0)
    return {"trades": n, "won": won, "win_rate_pct": round(100.0 * won / n, 1), "avg_r": None,
            "avg_pct": round(sum(r["pnl_pct"] for r in closed) / n, 3),
            "net_usd": round(sum(r["pnl_usd"] for r in closed), 2), "fees_usd": round(sum(r["fees_usd"] for r in closed), 2),
            "costs_usd": round(sum(r.get("costs_usd") or 0.0 for r in closed), 2)}


def rule_text(book):
    if book == "p4_h30spot":
        r = ("Daily 30-day momentum, decided at the 00:00 UTC close, filled at the next 15m open: 1.5x long in uptrends "
             "(1x spot + 0.5x perp), flat in downtrends; a new entry waits up to 48 bars (12 h) for a 15m close at or "
             "below EMA20 - 1 x ATR14 (E2 pullback); an exit is done at once.")
    else:
        r = ("Daily 30-day momentum, decided at the 00:00 UTC close: long only, sized min(2, 0.60 / realised vol) "
             "(672-bar 15m vol, annualised), re-sized on the 15m clock when it drifts 0.25x or more; E2 pullback on a new "
             "entry; while long, a 15m close below (highest close since entry - 4 x daily ATR14) goes flat until a later "
             "00:00 UTC decision with momentum up.")
    return ("%s %s Frozen exactly as in round 2 (%s). Fees 0.10%% a side, spread 0.5 bp, volatility slippage. %s "
            "BTC and ETH, each its own $10,000 paper book from %s UTC; only trades decided after that count." % (
                NOT_PASSED, r, BOOKS[book]["loop_id"], SPOT_NOTE, REGISTERED))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1",
                                              "target_2", "r", "pnl_usd", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"] + " UTC",
                     "not_passed": True, "loop_id": facts["loop_id"], "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r.get(k)) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit",
                                                              "why_out", "r", "pnl_usd", "pnl_pct", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "books": dict(LAST_STATE.get(book, {})),
                     "pass_rule": ("Forward verdict once the book has 30 closed forward trades (BTC and ETH together), "
                                   "by the loop's strict rules where they apply forward; see research/HYPOTHESES.md. "
                                   "Even a forward pass is not a loop pass (no holdout look was earned)."),
                     "note": NOT_PASSED + " " + SPOT_NOTE}
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"])
        for a, s in b["books"].items():
            print("  ", a, s)


if __name__ == "__main__":
    main()
