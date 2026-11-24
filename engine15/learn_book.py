# -*- coding: utf-8 -*-
"""learn_book -- the exit learner `b_learn` (H109): a forward PAPER book for BTC and ETH. PAPER ONLY, NOT passed.

Owner, 24 Nov 2026, on three RL-style ideas that "would run as a paper shadow first": "Ok lets do it" (docs/RL_NEXT.md,
R1; only the EXIT part). Registered as H109 in research/HYPOTHESES.md BEFORE this file existed; every constant below is
that registration's and is not to be tuned here.

What it is. Six shadow books already run six exit rules on BTC and ETH (shadows.CHALLENGERS: the ARMS below). Each
closed trade of an arm is a reward for that arm: its net R-multiple after fees. `b_learn` keeps one exponential-weights
table per market state (four BUCKETS, read from closed 15-minute bars at the entry) and FOLLOWS:

    when it is flat on a coin and the best-weighted arm for the entry's bucket opens a trade on that coin, it copies
    THAT trade from entry to exit at the arm's own fills, earning the arm's return on equity; then it chooses again.

No lookahead: the choice at an entry at time T uses arm trades that closed strictly before T and bars closed by T.

It is NOT a rule of shadows.run and it changes no book. It READS the arms' closed-trade files
(out/live/shadow_trades_<arm>_<coin>.csv), the shadow books' state (their open trades) and the tail of the two bar
files, and is recomputed from scratch at every step: it keeps no state of its own, so a restart, a lost file or a late
deploy gives the trades a continuous run from START_UTC gives. It WRITES its own closed trades
(out/live/shadow_trades_b_learn_<coin>.csv, which puts it on the scoreboard like any shadow book) and returns the
`exit_learner` block of out/live/scoreboard.json. Nothing here reaches the Setups book or the vault feed.

What must be said with it (H109): on history holding beat every other exit (H36). The learner can only beat the best
single rule if the right exit depends on the market state at the entry. That is unproven; this book is the test.

    py -3 -m engine15.learn_book          prints the block (reads only, writes nothing)
"""
import calendar
import csv
import io
import json
import math
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import data, signals
from .config import CFG
from .shadows import STATE_PATH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DIR = os.path.join(ROOT, "out", "live")

NAME = "b_learn"
HYPOTHESIS = "H109"
SCOREBOARD_TITLE = "Shadow: b_learn (exit learner, H109; paper only, NOT passed)"
# ---- the registration's constants (research/HYPOTHESES.md H109; none tuned here, none in CFG)
ARMS = ("b_targets", "main", "b_trail", "b_be_t1", "b_ema20_1h_t1", "b_sma20_1h_t1")   # this order breaks ties
COINS = ("BTCUSDT", "ETHUSDT")
BUCKETS = ("calm_agree", "calm_mixed", "wild_agree", "wild_mixed")
START_UTC = "2026-11-25T00:00:00Z"               # flat then; only arm trades entered at or after it are followed
START_MS = calendar.timegm(time.strptime(START_UTC, "%Y-%m-%dT%H:%M:%SZ")) * 1000
START_EQUITY = 10000.0                           # per coin, as every shadow book
HALF_LIFE_MS = 30 * 86400000                     # a closed trade's reward halves every 30 days
ETA = 0.5                                        # learning rate per R: shapes the weights shown, never a choice
MIN_BUCKET_TRADES = 12                           # closed arm trades a bucket needs before its own table is used
VOL_NOW, VOL_REF = 96, 2880                      # 24 hours of bars against the median over 30 days of bars
TREND_N = 20                                     # the simple average of 20 closed 4h / daily closes
STALE_MS = 3600000                               # a reading older than one hour at the entry is no reading
READ_AT = (30, 60)                               # the reads (closed forward trades of b_learn)
# ---- plumbing
BAR_MS = int(CFG.get("bar_ms", 900000))
LOOKBACK_MS = 40 * 86400000                      # bars read before the earliest arm trade (the look-backs need 31 days)
BARS_CAP = 1 << 27
INF = float("inf")
COLS = ["t_in_ms", "t_out_ms", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty", "pnl_usd",
        "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "time_in", "time_out",
        "arm", "bucket", "table"]                # the shadow books' columns, then whom it followed and why
NOTE = ("Paper only, NOT passed (H109). One book per coin on BTC and ETH since %s: when flat it copies the next trade of "
        "the exit rule with the best recent net R in the market state of that entry (volatility calm or wild, 4h and "
        "daily trend agreeing or mixed). On history holding beat every other exit, so this only adds something if the "
        "right exit depends on the market state. That is unproven. Read at 30 and 60 closed trades against the Setups "
        "book and the best single rule over the same days." % START_UTC[:10])


def _iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) // 1000))


def _utc(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ms) // 1000))


def _num(v):
    """A float from a CSV cell or a state value; NaN for an empty or missing one."""
    if v is None or v == "":
        return float("nan")
    return float(v)


def _fin(*vals):
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals)


# ------------------------------------------------------------------ the market state at an entry (closed bars only)
def _mean_last(v, n):
    """The mean of the last n values at each place (NaN before there are n). Every window is summed by itself, so a
    value is the same however much earlier data the array holds (a running sum would carry its rounding along)."""
    v = np.asarray(v, dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(v, n).mean(axis=1)
    return out


def regimes(ts, high, low, close):
    """Per 15-minute bar, what is known at that bar's CLOSE: (wild, agree), each 1.0 / 0.0, NaN where the look-back is
    not there yet. wild: the mean of true range / previous close over VOL_NOW bars is above its own median over VOL_REF
    closes. agree: on 4h and on daily bars the last CLOSED bar's close is on the same side of the simple average of the
    last TREND_N closed closes (data.resample + data.htf_on_15, the engine's no-lookahead join). Only fixed look-backs
    are used, so a value never depends on how far back the bars were read."""
    idx = pd.to_datetime(np.asarray(ts, dtype="int64"), unit="ms", utc=True)
    c = np.asarray(close, dtype=float)
    h, l = np.asarray(high, dtype=float), np.asarray(low, dtype=float)
    pc = np.concatenate(([np.nan], c[:-1]))
    with np.errstate(invalid="ignore", divide="ignore"):
        x = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))) / pc
    now = _mean_last(x, VOL_NOW)
    ref = pd.Series(now).rolling(VOL_REF).median().values         # a median is an order statistic: exact
    wild = np.where(np.isfinite(now) & np.isfinite(ref), (now > ref).astype(float), np.nan)
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": 0.0, "taker_buy": 0.0}, index=idx)
    sign = {}
    for rule in ("4h", "1D"):
        hc = data.resample(df, rule)["close"]                     # a higher bar's close is its last 15m close
        side = pd.Series(np.sign(hc.values - _mean_last(hc.values, TREND_N)), index=hc.index)
        sign[rule] = np.asarray(data.htf_on_15(df, rule, side).values, dtype=float)
    s4, sd = sign["4h"], sign["1D"]
    agree = np.where(np.isfinite(s4) & np.isfinite(sd), ((s4 == sd) & (s4 != 0)).astype(float), np.nan)
    return wild, agree


def read_bars(path, since_ms, chunk=1 << 16, cap=BARS_CAP):
    """The closed bars after since_ms from the TAIL of a bar file -> (open times, open, high, low, close), or None when
    the read cannot be trusted (missing, empty, a line that is not a whole bar, times out of order, the tail does not
    reach back to since_ms). signals.read_bars' rules, parsed in one go: this book reads weeks of bars at every step."""
    try:
        size = os.path.getsize(path)
        if size <= 0:
            return None
        back = chunk
        with io.open(path, "rb") as fh:
            while True:
                start = max(0, size - back)
                fh.seek(start)
                raw = fh.read(size - start)
                body = raw[raw.find(b"\n") + 1:] if start else raw   # the first line of a tail may be cut
                if body.startswith(b"ts_ms"):
                    body = body[body.find(b"\n") + 1:]
                if start == 0 or (body and int(body[:body.index(b",")]) <= since_ms):
                    break
                if back >= cap:
                    return None
                back *= 4
        if not body.endswith(b"\n"):
            body = body[:body.rfind(b"\n") + 1]                   # the last line may still be being written
        lo, hi = 0, len(body)                                     # the tail grows fourfold: skip what is before
        while hi - lo > 8192:                                     # since_ms (lines are in time order; lo and hi are
            nl = body.find(b"\n", (lo + hi) // 2)                 # line starts) so only the bars asked for are parsed
            if nl < 0 or nl + 1 >= hi:
                hi = (lo + hi) // 2
            elif int(body[nl + 1:body.index(b",", nl + 1)]) <= since_ms:
                lo = nl + 1
            else:
                hi = nl + 1
        body = body[lo:]
        if not body.strip():
            return None
        df = pd.read_csv(io.BytesIO(body), header=None, usecols=[0, 1, 2, 3, 4], skip_blank_lines=True,
                         float_precision="round_trip",            # the very numbers float() gives the engine
                         dtype={0: "int64", 1: "float64", 2: "float64", 3: "float64", 4: "float64"})
    except (OSError, ValueError, TypeError, LookupError, OverflowError):   # pandas' parser errors are ValueErrors
        return None
    ts = df[0].values
    px = df[[1, 2, 3, 4]].values
    if not len(ts) or (ts % BAR_MS).any() or (np.diff(ts) <= 0).any() or not (np.isfinite(px).all() and (px > 0).all()):
        return None
    keep = ts > since_ms
    if not keep.any():
        return None
    px = px[keep]
    return ts[keep].astype("int64"), px[:, 0], px.max(axis=1), px.min(axis=1), px[:, 3]


def read_regimes(data_dir, coin, since_ms):
    """(bar open times, wild, agree) from the tail of the coin's bar file, or None when it cannot be read."""
    got = read_bars(signals.bar_path(data_dir, coin), int(since_ms))
    if got is None:
        return None
    ts, _o, h, l, c = got
    wild, agree = regimes(ts, h, l, c)
    return ts, wild, agree


def bucket_at(reg, t_ms):
    """The bucket of an entry at t_ms from (times, wild, agree): the last bar that had closed by t_ms. None when there
    is no such bar, it closed more than STALE_MS before, or a look-back is not filled."""
    if reg is None:
        return None
    ts, wild, agree = reg
    k = int(np.searchsorted(ts, int(t_ms), side="left")) - 1      # the last bar that opened before t_ms
    if k < 0:
        return None
    closed = int(ts[k]) + BAR_MS
    if closed > t_ms or t_ms - closed > STALE_MS:
        return None
    w, g = wild[k], agree[k]
    if not (w == w and g == g):
        return None
    return ("wild" if w else "calm") + "_" + ("agree" if g else "mixed")


# ------------------------------------------------------------------ the arms' records (read only)
def read_arm(live_dir, arm, coin):
    """One arm's closed trades on one coin -> ([trade dicts by entry time], rows left out). A missing file is no
    trades. A row written twice counts once (the engine may repeat a row after a crash); a garbled row, a row whose
    numbers do not add up or a trade that starts before the one before it ended is left out and counted."""
    path = os.path.join(live_dir, "shadow_trades_%s_%s.csv" % (arm, coin))
    if not os.path.exists(path):
        return [], 0
    keep, odd = {}, 0
    with io.open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        while True:
            try:
                r = next(rd)
            except StopIteration:
                break
            except csv.Error:                                     # a line the reader refuses: one odd row, read on
                odd += 1
                continue
            try:
                if str(r.get("why_out")) == "OPEN":
                    continue
                t = {"arm": arm, "coin": coin, "t_in": int(float(r["t_in_ms"])), "t_out": int(float(r["t_out_ms"])),
                     "side": int(float(r["side"])), "p_in": float(r["p_in"]), "p_out": float(r["p_out"]),
                     "why_in": str(r.get("why_in") or ""), "why_out": str(r.get("why_out") or ""),
                     "pnl": float(r["pnl_usd"]), "eq_after": float(r["equity"]), "qty": _num(r.get("qty")),
                     "fees": _num(r.get("fees_usd")), "stop0": _num(r.get("stop0")), "risk": _num(r.get("risk_usd")),
                     "r": float(r["r_mult"]), "pnl_pct": _num(r.get("pnl_pct")),
                     "t1": _num(r.get("target_1")), "t2": _num(r.get("target_2"))}
                t["eq0"] = t["eq_after"] - t["pnl"]               # the arm's realized equity before this trade
                ok = (t["side"] in (1, -1) and t["t_out"] >= t["t_in"] > 0 and t["p_in"] > 0 and t["p_out"] > 0
                      and _fin(t["pnl"], t["eq_after"], t["r"]) and t["eq0"] > 0)
            except (KeyError, TypeError, ValueError, OverflowError):
                ok = False
            if not ok:
                odd += 1
                continue
            keep[(t["t_in"], t["side"])] = t
    out = []
    for k in sorted(keep):                                         # one trade at a time per arm and coin
        if out and keep[k]["t_in"] < out[-1]["t_out"]:
            odd += 1
            continue
        out.append(keep[k])
    return out, odd


def read_open(state, arm, coin):
    """The arm's open trade on the coin from the shadow books' state, or None when it is flat. Raises ValueError when
    the state does not add up (the caller leaves it out)."""
    books = state.get("books") if isinstance(state, dict) else None
    mine = books.get(arm) if isinstance(books, dict) else None
    b = mine.get(coin) if isinstance(mine, dict) else None
    if not isinstance(b, dict) or not b.get("pos"):
        return None
    side = int(b["pos"])
    part = b.get("part") if isinstance(b.get("part"), dict) else {}
    t = {"arm": arm, "coin": coin, "t_in": int(b["t_in_ms"]), "t_out": None, "side": side, "p_in": float(b["entry"]),
         "qty": float(b["qty"]), "why_in": str(b.get("why_in") or ""), "part_pnl": float(part.get("pnl") or 0.0),
         "stop": _num(b.get("stop")), "stop0": _num(b.get("stop0")), "mark": _num(b.get("mark")),
         "t1": _num(b.get("t1")), "t2": _num(b.get("t2")), "t1_hit": bool(b.get("t1_hit"))}
    t["eq0"] = float(b["eq"]) - t["part_pnl"]                     # realized equity before the trade (a part taken at
    if side not in (1, -1) or t["t_in"] <= 0 or not (t["p_in"] > 0 and t["qty"] > 0 and t["eq0"] > 0) \
            or not _fin(t["p_in"], t["qty"], t["eq0"], t["part_pnl"]):   # Target 1 is already in the arm's equity)
        raise ValueError("an open trade that does not add up")
    return t


def gather(live_dir, state):
    """Every arm's closed and open trades on both coins -> (closed, opens, rows left out)."""
    closed, opens, odd = [], [], 0
    for coin in COINS:
        for arm in ARMS:
            try:
                rows, bad = read_arm(live_dir, arm, coin)
            except (OSError, csv.Error, UnicodeError):
                rows, bad = [], 1                                 # an unreadable file is no trades this step, and said
            closed += rows
            odd += bad
            try:
                o = read_open(state, arm, coin)
            except (KeyError, TypeError, ValueError, OverflowError):
                o, odd = None, odd + 1
            if o is None:
                continue
            if any(r["t_in"] == o["t_in"] and r["side"] == o["side"] for r in rows):
                continue                                          # its closed row is already written: the file wins
            if rows and o["t_in"] < rows[-1]["t_out"]:
                odd += 1                                          # open before its last closed trade ended: left out
                continue
            opens.append(o)
    return closed, opens, odd


# ------------------------------------------------------------------ the learner and the follower (pure)
def walk(closed, opens, bucket_of, start_ms=START_MS, as_of_ms=None):
    """The whole book from the arms' records. closed / opens: trade dicts (read_arm / read_open); bucket_of(coin, t_ms)
    -> a bucket or None. Nothing is read here and nothing is kept between calls.
    -> {"trades": {coin: [copied closed trades]}, "open": {coin: copied open trade or None}, "equity": {coin: realized},
        "choices": [every copy decision], "tables": the scores at as_of_ms, "no_reading": trades left out for it}"""
    a_ix = dict((a, i) for i, a in enumerate(ARMS))
    c_ix = dict((c, i) for i, c in enumerate(COINS))
    seen, no_reading = {}, 0

    def bkt(t):
        k = (t["coin"], t["t_in"])
        if k not in seen:
            seen[k] = bucket_of(t["coin"], t["t_in"])
        return seen[k]

    feed, live = [], []
    for src, dst in ((closed, feed), (opens, live)):
        for t in src:
            if t["arm"] not in a_ix or t["coin"] not in c_ix:
                continue
            b = bkt(t)
            if b not in BUCKETS:
                no_reading += 1                                   # neither followed nor used for weights (H109)
                continue
            dst.append(dict(t, bucket=b))
    feed.sort(key=lambda t: (t["t_out"], c_ix[t["coin"]], a_ix[t["arm"]], t["t_in"]))
    entries = sorted((t for t in feed + live if t["t_in"] >= start_ms),
                     key=lambda t: (t["t_in"], c_ix[t["coin"]], a_ix[t["arm"]]))
    # Scores are kept "inflated": a reward r closed at t_out is stored as r x 2^((t_out - t0) / half-life). Every score
    # at a later time T is that sum x 2^(-(T - t0) / half-life): one common factor, so the ORDER of the arms at T (all
    # the choice needs) is read from the inflated sums directly, and no reward closed at or after T is ever in them.
    # t0 is the book's start, a constant, so a stored reward never depends on which other rows the records hold.
    t0 = start_ms
    infl = dict((b, [0.0] * len(ARMS)) for b in BUCKETS)
    count = dict((b, 0) for b in BUCKETS)
    fed = [0]

    def advance(T):                                               # take in every reward closed STRICTLY before T
        j = fed[0]
        while j < len(feed) and feed[j]["t_out"] < T:
            f = feed[j]
            infl[f["bucket"]][a_ix[f["arm"]]] += f["r"] * 2.0 ** ((f["t_out"] - t0) / float(HALF_LIFE_MS))
            count[f["bucket"]] += 1
            j += 1
        fed[0] = j

    def table_of(b):
        if count[b] >= MIN_BUCKET_TRADES:
            return infl[b], b
        return [sum(infl[x][i] for x in BUCKETS) for i in range(len(ARMS))], "pooled"

    def leader(b):
        row, name = table_of(b)
        return ARMS[max(range(len(ARMS)), key=lambda i: (row[i], -i))], name   # ties: the first in ARMS

    eq = dict((c, START_EQUITY) for c in COINS)
    busy = dict((c, (None, None)) for c in COINS)                  # (when its copied trade closes, whose it was)
    out = dict((c, []) for c in COINS)
    held = dict((c, None) for c in COINS)
    choices = []
    for e in entries:
        T, c, a = e["t_in"], e["coin"], e["arm"]
        advance(T)
        until, who = busy[c]
        if not (until is None or until < T or (until == T and who == a)):
            continue                                              # still in a copied trade (an arm's own flip is free)
        lead, table = leader(e["bucket"])
        if lead != a:
            continue                                              # only the best-weighted arm's entry is copied
        choices.append({"coin": c, "t_in": T, "arm": a, "bucket": e["bucket"], "table": table, "side": e["side"]})
        scale = eq[c] / e["eq0"]                                  # the arm's return on equity, on this book's equity
        if e["t_out"] is None:
            busy[c] = (INF, a)
            unreal = e["qty"] * e["side"] * (e["mark"] - e["p_in"]) if e["mark"] == e["mark"] else 0.0
            held[c] = dict(e, table=table, scale=scale, unrealized=scale * (e["part_pnl"] + unreal))
            continue
        busy[c] = (e["t_out"], a)
        pnl = e["pnl"] * scale
        eq[c] += pnl
        out[c].append(dict(e, table=table, pnl=pnl, eq_after=eq[c], qty=e["qty"] * scale, fees=e["fees"] * scale,
                           risk=e["risk"] * scale))
    last = max([start_ms] + [t["t_out"] for t in feed] + [t["t_in"] for t in live])
    as_of = last + BAR_MS if as_of_ms is None else int(as_of_ms)
    advance(INF)                                                  # the tables as they stand now, for the next entry
    fade = 2.0 ** (-(as_of - t0) / float(HALF_LIFE_MS))
    tables = OrderedDict()
    for b in BUCKETS + ("pooled",):
        row = infl[b] if b != "pooled" else [sum(infl[x][i] for x in BUCKETS) for i in range(len(ARMS))]
        sc = [v * fade for v in row]
        top = max(sc)
        w = [math.exp(ETA * (v - top)) for v in sc]
        tot = sum(w)
        tables[b] = {"closed_trades": count[b] if b != "pooled" else sum(count.values()),
                     "leader": ARMS[max(range(len(ARMS)), key=lambda i: (row[i], -i))],
                     "scores_r": dict((a, round(sc[i], 3)) for i, a in enumerate(ARMS)),
                     "weights": dict((a, round(w[i] / tot, 4)) for i, a in enumerate(ARMS))}
        if b != "pooled":
            tables[b]["in_use"] = count[b] >= MIN_BUCKET_TRADES    # else the pooled table decides for this bucket
    return {"trades": out, "open": held, "equity": eq, "choices": choices, "tables": tables, "no_reading": no_reading,
            "as_of_ms": as_of, "next": dict((b, leader(b)) for b in BUCKETS)}


# ------------------------------------------------------------------ the record and the block
def _cell(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return repr(float(v)) if isinstance(v, float) else str(v)


def trade_rows(trades):
    """A coin's copied closed trades as rows of COLS (strings)."""
    rows = []
    for t in trades:
        rows.append([_cell(x) for x in (
            t["t_in"], t["t_out"], t["side"], t["p_in"], t["p_out"], t["why_in"], t["why_out"], t["pnl_pct"],
            t["eq_after"], t["qty"], t["pnl"], t["fees"], t["stop0"], t["risk"], t["r"], t["t1"], t["t2"],
            _utc(t["t_in"]), _utc(t["t_out"]), t["arm"], t["bucket"], t["table"])])
    return rows


def write_trades(live_dir, coin, trades):
    """The coin's record, written whole and atomically, only when it differs from what is there. A book with no closed
    trade writes no file (and leaves none behind that it did not write). -> True when the file was written."""
    path = os.path.join(live_dir, "shadow_trades_%s_%s.csv" % (NAME, coin))
    if not trades and not os.path.exists(path):
        return False
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLS)
    w.writerows(trade_rows(trades))
    body = buf.getvalue()
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            if fh.read() == body:
                return False
    except (OSError, UnicodeError):
        pass
    os.makedirs(live_dir, exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
    os.replace(tmp, path)
    return True


def _same_days(closed, res):
    """The baselines of H109: each arm's own closed trades entered at or after START_UTC, both coins together, beside
    the learner's. ret_pct = the mean over the two coins of the compounded return on the book's equity."""
    out = OrderedDict()

    def line(rows):
        by = dict((c, 1.0) for c in COINS)
        for t in rows:
            by[t["coin"]] *= 1.0 + t["pnl"] / t["eq0"]
        return {"trades": len(rows), "wins": sum(1 for t in rows if t["pnl"] > 0),
                "sum_r": round(sum(t["r"] for t in rows), 3),
                "ret_pct": round((sum(by.values()) / len(COINS) - 1.0) * 100.0, 3)}
    mine = [dict(t, eq0=t["eq_after"] - t["pnl"]) for c in COINS for t in res["trades"][c]]
    out[NAME] = line(mine)
    for a in ARMS:
        out[a] = line([t for t in closed if t["arm"] == a and t["t_in"] >= START_MS])
    return out


def compute(live_dir=None, data_dir=None, state_path=None):
    """Read the arms' records and bars, walk the book. -> (the block, {coin: copied closed trades}, {coin: True when
    every input of that coin was read at this step}). Never raises for a missing or odd input: it says so."""
    live_dir, data_dir = live_dir or LIVE_DIR, data_dir or data.DATA_DIR
    blk = OrderedDict([("book", NAME), ("hypothesis", HYPOTHESIS), ("label", "paper only, NOT passed"),
                       ("started_utc", START_UTC), ("note", NOTE), ("arms", list(ARMS)), ("read_at_trades", list(READ_AT))])
    state_ok = True
    try:
        with io.open(state_path or STATE_PATH, encoding="utf-8") as fh:
            state = json.load(fh)
        if not isinstance(state, dict):
            raise ValueError("not a state")
    except (OSError, ValueError):
        state, state_ok = {}, False                               # no state: open trades are unknown at this step
    closed, opens, odd = gather(live_dir, state)
    first = min([t["t_in"] for t in closed + opens] + [START_MS])
    regs, bars_ok = {}, {}
    for c in COINS:
        try:
            regs[c] = read_regimes(data_dir, c, first - LOOKBACK_MS)
        except Exception:                                         # an odd bar file: no reading for this coin
            regs[c] = None
        bars_ok[c] = regs[c] is not None
    ends = [int(regs[c][0][-1]) + BAR_MS for c in COINS if bars_ok[c]]
    as_of = max(ends) if ends else None
    res = walk(closed, opens, lambda coin, t: bucket_at(regs.get(coin), t), as_of_ms=as_of)
    ok = dict((c, bool(bars_ok[c] and state_ok)) for c in COINS)
    n = sum(len(res["trades"][c]) for c in COINS)
    if as_of is None:
        status = "the bar files could not be read at this step"
    elif as_of <= START_MS:
        status = "not started (it starts %s UTC)" % START_UTC[:16].replace("T", " ")
    elif not all(ok.values()):
        status = "running; an input could not be read at this step (the record on file was left as it was)"
    else:
        status = "running"
    coins = OrderedDict()
    marked = 0.0
    for c in COINS:
        o, eq = res["open"][c], res["equity"][c]
        v = {"status": "FLAT" if o is None else ("LONG" if o["side"] > 0 else "SHORT"), "realized_equity": round(eq, 2),
             "equity": round(eq + (o["unrealized"] if o else 0.0), 2), "trades": len(res["trades"][c]),
             "wins": sum(1 for t in res["trades"][c] if t["pnl"] > 0)}
        marked += v["equity"]
        if o is not None:
            v.update(following=o["arm"], entry=o["p_in"], opened_utc=_utc(o["t_in"]), bucket=o["bucket"],
                     table=o["table"], stop=None if o["stop"] != o["stop"] else o["stop"],
                     unrealized_usd=round(o["unrealized"], 2))
        elif as_of is not None and bars_ok[c]:
            b = bucket_at(regs[c], as_of)
            v["bucket_now"] = b
            if b is not None:                                     # whose next entry it would copy if it came now
                v["would_follow"], v["table"] = res["next"][b]
        if as_of is not None and as_of > START_MS:
            used = sum(min(t["t_out"], as_of) - t["t_in"] for t in res["trades"][c]) + \
                (max(0, as_of - o["t_in"]) if o is not None else 0)
            v["flat_share_pct"] = round(100.0 * (1.0 - min(1.0, used / float(as_of - START_MS))), 1)
        coins[c] = v
    followed = OrderedDict((a, sum(1 for c in COINS for t in res["trades"][c] if t["arm"] == a)) for a in ARMS)
    same = _same_days(closed, res)
    arms_only = [(a, same[a]) for a in ARMS if same[a]["trades"]]
    blk.update(status=status, as_of_utc=None if as_of is None else _iso(as_of), trades=n,
               next_read_at=next((k for k in READ_AT if n < k), None), equity=round(marked, 2),
               pnl_usd=round(marked - START_EQUITY * len(COINS), 2), coins=coins, followed=followed,
               tables=res["tables"], same_days=same,
               best_single_arm=max(arms_only, key=lambda x: x[1]["sum_r"])[0] if arms_only else None,
               left_out={"no_reading": res["no_reading"], "odd_rows": odd})
    return blk, res["trades"], ok


def step(live_dir=None, data_dir=None, state_path=None, write=True, log=print):
    """The live step's hook (reports.scoreboard, in its own try/except): recompute the book, rewrite its closed-trade
    files where they changed, -> the `exit_learner` block. A coin whose inputs could not all be read at this step keeps
    the file it has, so a half-written bar file never shortens the record."""
    blk, trades, ok = compute(live_dir, data_dir, state_path)
    if write:
        for c in COINS:
            if not ok[c]:
                continue
            try:
                write_trades(live_dir or LIVE_DIR, c, trades[c])
            except Exception as e:                                # one coin's file never stops the other or the step
                log("exit learner: %s record not written (%r)" % (c, e))
    return blk


if __name__ == "__main__":
    print(json.dumps(step(write=False), indent=1))
