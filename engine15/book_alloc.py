# -*- coding: utf-8 -*-
"""book_alloc -- `a_alloc`, one PAPER wallet split each UTC day between the forward books. PAPER ONLY. NOT PASSED.

Owner, 24 Nov 2026, on RL idea R2 of docs/RL_NEXT.md ("would run as a paper shadow first"): "Ok lets do it".
Registered as H110 in research/HYPOTHESES.md BEFORE any number was computed; the rules below are that entry's and must
not be tuned here.

    wallet     $10,000 at START_UTC; nothing before it counts (only trades OPENED at or after it)
    books      the 37 forward books of BOOKS (the main books, 17 shadow books, 19 strategy books), fixed at registration
    a day      a book's result on UTC day D = the pnl_usd of its rows that CLOSED in D / ($10,000 x its markets).
               Closed trades only: open trades are not marked, a long trade books its whole result on its closing day
    method     exponential weights: raw weight = exp(ETA x score), score = the sum of the book's daily results on the
               days BEFORE D (each cut to +/-RET_CLIP for the score only). No random draw, no forgetting
    cap/floor  no book above CAP (25%); a book with fewer than FLOOR_TRADES (30) closed trades since the start holds at
               least FLOOR_X (half) of the equal share
    yardstick  the equal-weight mix of the same books over the same days; `a_alloc` is "ahead" only against it
    verdict    two reads, after the first 30 and the first 60 completed days: ahead / behind / level by the 90% range
               of the mean daily difference (the scoreboard's formula). A read changes nothing by itself

It places nothing and changes no book and no decision. It READS the main books' and the shadow books' closed-trade
files in out/live and the strategy rows the step already holds, and is recomputed from START_UTC at every step: it
keeps no state of its own, so there is nothing to lose or to roll back. Its only output is the "a_alloc" block of
out/live/scoreboard.json (reports.scoreboard), which the page carries under scoreboard_all.

No lookahead: the shares of day D are a function of rows whose close time is before D 00:00 UTC, and of nothing else
(tests/test_book_alloc.py removes the later days and gets the same shares). A row that is written late (gold, silver
and oil step one bar behind) can still move the newest day's shares in that day's first hour.

What it is not: an edge. It cannot create an edge that none of the books has; the books are correlated and share
market spells; no cost of moving the wallet between books is counted. Constants live here, not in CFG (a CFG key
would rebuild the reading cache on the live box).
"""
import calendar
import csv
import glob
import io
import json
import math
import os
import time
from collections import OrderedDict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DIR = os.path.join(ROOT, "out", "live")
NAME = "a_alloc"
HYPOTHESIS = "H110"
START_UTC = "2026-11-25T00:00:00Z"               # the first day of allocation; trades opened before it never count
START_MS = calendar.timegm(time.strptime(START_UTC, "%Y-%m-%dT%H:%M:%SZ")) * 1000
DAY_MS = 86400000
START_W = 10000.0
STAKE = 10000.0                                  # a book's capital base = STAKE x the number of markets it trades
ETA = 7.0                                        # sqrt(8 ln 37 / 60) / 0.10 = 6.94, rounded (H110)
RET_CLIP = 0.05                                  # a daily result is cut to +/-5% for the SCORE only
CAP = 0.25                                       # no book above 25% of the wallet
FLOOR_X = 0.5                                    # the floor: this share of the equal share ...
FLOOR_TRADES = 30                                # ... while the book has fewer closed trades than this since the start
READ_DAYS = (30, 60)                             # the two reads, in completed days
Z90 = 1.645                                      # the scoreboard's 90% range (reports._stats)
SETTLE_MS = 3600000                              # a day is complete one hour after it ends (late rows have arrived)
ROWS_KEPT = 90                                   # daily rows shown in the block (the curve holds every day)
MAX_DAYS = 3660                                  # a clock that far off is an error, not a ten-year loop

_ALL8, _SIX, _COINS = 8, 6, 2
BOOKS = OrderedDict(                             # (kind, book) -> markets. Fixed by H110; a new book is NOT added here
    [(("main", "main"), _ALL8)]
    + [(("shadow", b), _ALL8) for b in (
        "main", "v4", "h3_flip_limit", "b_targets", "b_trend30", "b_wait_stop", "b_trail", "a_pullback", "y_4h", "y_1d",
        "h5_damp", "m_swing_1h", "m_swing_4h", "b_be_t1", "b_ema20_1h_t1", "b_sma20_1h_t1", "f_floor_33_3r")]
    + [(("strategy", b), m) for b, m in (
        ("p1_liqhunt", _SIX), ("p2_trap", _SIX), ("p3_orb", _SIX), ("p4_gapfill", 1), ("p5_squeeze", _SIX),
        ("p6_vwap", _SIX), ("p7_session", 2), ("p8_fvg", _SIX), ("p9_cascade", _COINS), ("p10_round", _SIX),
        ("p11_release", _SIX), ("p12_orb_us", _COINS), ("p4_h30spot", _COINS), ("p4_h31trail", _COINS),
        ("p5_rlq", _COINS), ("p6_mtrend", _COINS), ("p6_p4trend", _COINS), ("p7_rvbear", _COINS), ("p8_mom", _COINS))])
NOTE = ("One paper wallet of $10,000 split each UTC day between %d forward books since %s, by exponential weights on "
        "each book's daily closed-trade result (no book above 25%%; a book with fewer than 30 closed trades keeps at "
        "least half the equal share). Yardstick: the same books held equally over the same days. Paper only and NOT "
        "passed (H110): it cannot create an edge that none of the books has. Daily results are closed trades booked on "
        "the day they close: open trades are not marked, and no cost of moving the wallet is counted. The books are "
        "correlated and share market spells, so a read after 30 or 60 days is not proof." % (len(BOOKS), START_UTC[:10]))


class BookError(Exception):
    """A book's record cannot be read at this step: the book is left out, the rest carries on."""


# ------------------------------------------------------------------ the records (read only)
def _ms(v):
    """A time as epoch milliseconds: a number of ms, or 'YYYY-MM-DD HH:MM[:SS]' in UTC ('T', 'Z' and '+00:00' allowed)."""
    s = str(v).strip()
    try:
        f = float(s)
    except ValueError:
        f = None
    if f is not None:
        if not math.isfinite(f):
            raise ValueError("not a time: %r" % (v,))
        return int(f)
    y, mo, d, hh, mm = int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16])
    if s[4] != "-" or s[7] != "-" or s[10] not in " T" or s[13] != ":":
        raise ValueError("not a time: %r" % (v,))
    sec, zone = 0, s[16:]
    if zone[:1] == ":":
        sec, zone = int(zone[1:3]), zone[3:]
    if zone[:1] == ".":                                           # a fraction of a second
        zone = zone[1:].lstrip("0123456789")
    if zone.strip() not in ("", "Z", "+00:00", "+0000", "UTC"):
        raise ValueError("not a UTC time: %r" % (v,))
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= sec <= 60):
        raise ValueError("not a time: %r" % (v,))
    return calendar.timegm((y, mo, d, hh, mm, sec)) * 1000


def _trade(asset, t_in, t_out, side, pnl):
    """One closed row as (asset, entry ms, close ms, side, pnl). Raises ValueError / TypeError for a garbled row."""
    pnl = float(pnl)
    if not math.isfinite(pnl):
        raise ValueError("no result")
    t_in, t_out = _ms(t_in), _ms(t_out)
    if t_out < t_in:
        raise ValueError("closed before it opened")
    try:
        side = int(float(side))
    except (TypeError, ValueError):
        side = str(side)
    return (str(asset), t_in, t_out, side, round(pnl, 6))


def read_file(path, asset):
    """The closed rows of one trade file -> ([trade], garbled rows). The file must exist. A file that cannot be opened,
    or whose header lacks the result or the time columns, raises BookError (its book is left out of this step)."""
    try:
        with io.open(path, encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            head = next(rd, None) or []
            at = dict((str(h).strip(), i) for i, h in enumerate(head))
            c_in = at.get("t_in_ms", at.get("time_in"))
            c_out = at.get("t_out_ms", at.get("time_out"))
            c_pnl, c_side = at.get("pnl_usd"), at.get("side")
            if c_in is None or c_out is None or c_pnl is None:
                raise BookError("%s: no result or time column" % os.path.basename(path))
            out, bad = [], 0
            for r in rd:
                if not r:
                    continue
                try:
                    out.append(_trade(asset, r[c_in], r[c_out], r[c_side] if c_side is not None else 0, r[c_pnl]))
                except (ValueError, TypeError, IndexError):
                    bad += 1                                      # a garbled line is not a trade
            return out, bad
    except (OSError, csv.Error) as e:
        raise BookError("%s: %s" % (os.path.basename(path), type(e).__name__))


def read_books(live_dir=None, playbook_rows=None):
    """Every registered book's closed rows. -> (trades {key: [trade]}, left_out {key: why}, not_registered [key],
    garbled rows). A registered book with no file and no row has no trade yet: it stays in with an empty list."""
    live_dir = live_dir or LIVE_DIR
    trades = OrderedDict((k, []) for k in BOOKS)
    left_out, other, bad = OrderedDict(), set(), 0
    files = OrderedDict((k, []) for k in BOOKS)
    try:
        names = sorted(glob.glob(os.path.join(live_dir, "trades_*.csv")) +
                       glob.glob(os.path.join(live_dir, "shadow_trades_*.csv")))
    except OSError:
        names = []
    for p in names:
        base = os.path.basename(p)[:-4]
        if base.startswith("shadow_trades_"):
            book, _, asset = base[len("shadow_trades_"):].rpartition("_")
            key = ("shadow", book)
        else:
            key, asset = ("main", "main"), base[len("trades_"):]
        if key in files:
            files[key].append((p, asset))
        else:
            other.add(key)
    for key, mine in files.items():
        try:
            for p, asset in mine:
                rows, b = read_file(p, asset)
                trades[key] += rows
                bad += b
        except BookError as e:
            left_out[key] = str(e)
        except Exception as e:                                    # anything else about one book stays with that book
            left_out[key] = "%s" % type(e).__name__
    try:
        for r in playbook_rows or ():
            if not isinstance(r, dict) or r.get("status") != "CLOSED" or r.get("pnl_usd") is None:
                continue
            key = ("strategy", r.get("book"))
            if key not in trades:
                other.add(key)
                continue
            try:
                trades[key].append(_trade(r.get("asset"), r.get("entry_utc"), r.get("exit_utc"), r.get("side"),
                                          r.get("pnl_usd")))
            except (ValueError, TypeError, IndexError):
                bad += 1
    except Exception as e:                                        # rows that cannot even be walked: no strategy book
        for key in BOOKS:                                         # can be trusted at this step
            if key[0] == "strategy":
                left_out[key] = "strategy rows unreadable (%s)" % type(e).__name__
    for key in left_out:
        trades.pop(key, None)
    for key in trades:
        trades[key] = sorted(set(trades[key]), key=lambda t: (t[2], t[1], t[0], str(t[3]), t[4]))   # a row twice: once
    return trades, left_out, sorted(other, key=lambda k: (str(k[0]), str(k[1]))), bad


# ------------------------------------------------------------------ the rule (H110)
def shares_for(score, protected, cap=CAP, floor_x=FLOOR_X, eta=ETA):
    """One day's shares from the books' scores (results BEFORE that day) -> (shares, cash).
    shares = clip(c x exp(eta x score), floor, cap) with the one number c that makes them add up to 1; floor =
    floor_x / n for a protected book (fewer than 30 closed trades), else 0. Fewer than 1 / cap books cannot be fully
    invested under the cap: each holds the cap and the rest is cash."""
    score = np.asarray(score, dtype=float)
    n = len(score)
    if n == 0:
        return np.zeros(0), 1.0
    if n * cap <= 1.0:
        return np.full(n, cap), max(0.0, 1.0 - n * cap)
    raw = np.maximum(np.exp(eta * (score - np.max(score))), 1e-300)
    lo = np.where(np.asarray(protected, dtype=bool), min(floor_x / n, cap), 0.0)
    bp = np.sort(np.concatenate([lo / raw, cap / raw]))          # where a book meets its floor or the cap
    tot = np.clip(bp[:, None] * raw[None, :], lo, cap).sum(axis=1)   # the shares' total at each: it only rises
    k = int(np.searchsorted(tot, 1.0, side="left"))
    if k <= 0:
        c = bp[0]
    elif k >= len(bp):
        c = bp[-1]
    else:
        a, b, fa, fb = bp[k - 1], bp[k], tot[k - 1], tot[k]
        c = a + (1.0 - fa) * (b - a) / (fb - fa) if fb > fa else b
    return np.clip(c * raw, lo, cap), 0.0


def day_tables(trades, bases, n_days):
    """-> (R, C): per day and book, the result (closed pnl / capital base) and the trades first closed that day
    (a trade = one entry: rows that share market, entry time and side are one trade closed in parts)."""
    R, C = np.zeros((n_days, len(trades))), np.zeros((n_days, len(trades)))
    for j, (key, rows) in enumerate(trades.items()):
        seen = set()
        for asset, t_in, t_out, side, pnl in rows:               # sorted by close time
            d = (t_out - START_MS) // DAY_MS
            if t_in < START_MS or d < 0 or d >= n_days:
                continue                                          # opened before the start, or dated after "now"
            R[d, j] += pnl / bases[j]
            if (asset, t_in, side) not in seen:
                seen.add((asset, t_in, side))
                C[d, j] += 1
    return R, C


def walk(R, C):
    """The allocator and the yardstick over the days of R. Row d of `shares` uses rows 0 .. d-1 of R and C only.
    -> dict: shares, cash, score (before each day), count (before each day), a_ret, y_ret, a_eq, y_eq, turnover."""
    n_days, n = R.shape
    before = lambda X: np.vstack([np.zeros((1, n)), np.cumsum(X, axis=0)])[:n_days + 1]    # noqa: E731
    score, count = before(np.clip(R, -RET_CLIP, RET_CLIP)), before(C)   # row d = the days before d; one row more than
    shares, cash = np.zeros((n_days + 1, n)), np.zeros(n_days + 1)     # the days: the shares of the day after the last
    for d in range(n_days + 1):
        shares[d], cash[d] = shares_for(score[d], count[d] < FLOOR_TRADES)
    a_ret = (shares[:n_days] * R).sum(axis=1)
    y_ret = R.mean(axis=1) if n else np.zeros(n_days)
    turn = np.zeros(n_days)
    if n_days > 1:
        turn[1:] = 0.5 * np.abs(shares[1:n_days] - shares[:n_days - 1]).sum(axis=1)
    return {"shares": shares, "cash": cash, "score": score, "count": count, "a_ret": a_ret, "y_ret": y_ret,
            "a_eq": START_W * np.cumprod(np.maximum(1.0 + a_ret, 0.0)),
            "y_eq": START_W * np.cumprod(np.maximum(1.0 + y_ret, 0.0)), "turnover": turn}


def read_of(a_ret, y_ret, n):
    """The registered read over the FIRST n completed days: ahead / behind / level by the 90% range of the mean
    daily difference. Fewer days than n: too early."""
    have = min(len(a_ret), len(y_ret))
    if have < n:
        return {"days": n, "word": "too early to read (%d of %d days)" % (have, n)}
    a, y = np.asarray(a_ret[:n], dtype=float), np.asarray(y_ret[:n], dtype=float)
    d = a - y
    mean = float(d.mean())
    half = Z90 * float(d.std(ddof=1)) / math.sqrt(n) if n > 1 else 0.0
    lo, hi = mean - half, mean + half
    a_pct = (float(np.prod(np.maximum(1.0 + a, 0.0))) - 1.0) * 100.0
    y_pct = (float(np.prod(np.maximum(1.0 + y, 0.0))) - 1.0) * 100.0
    return {"days": n, "word": "ahead" if lo > 0 else "behind" if hi < 0 else "level",
            "alloc_pct": round(a_pct, 3), "yardstick_pct": round(y_pct, 3), "diff_pts": round(a_pct - y_pct, 3),
            "mean_daily_diff_pct": round(mean * 100.0, 4), "range90_daily_diff_pct": [round(lo * 100.0, 4), round(hi * 100.0, 4)]}


# ------------------------------------------------------------------ the block
def _day(d):
    return time.strftime("%Y-%m-%d", time.gmtime((START_MS + int(d) * DAY_MS) // 1000))


def _share_rows(keys, bases, shares, score, count, closed, net, n):
    """Today's shares, largest first. score and floor are what today's shares were made from (the days before today);
    trades and net_usd are everything closed since the start, today included."""
    rows = [{"book": k[1], "kind": k[0], "share_pct": round(float(shares[j]) * 100.0, 3),
             "equal_pct": round(100.0 / n, 3), "score_pct": round(float(score[j]) * 100.0, 3),
             "trades": int(closed[j]), "floor": bool(count[j] < FLOOR_TRADES), "net_usd": round(float(net[j]), 2),
             "markets": int(round(bases[j] / STAKE))} for j, k in enumerate(keys)]
    rows.sort(key=lambda r: (-r["share_pct"], r["kind"], r["book"]))
    return rows


def block(playbook_rows=None, live_dir=None, now=None):
    """The "a_alloc" block of scoreboard.json. A book it cannot read is left out and named; the rest carries on."""
    now_ms = int((time.time() if now is None else now) * 1000)
    out = {"book": NAME, "hypothesis": HYPOTHESIS, "passed": False, "started_utc": START_UTC, "start_wallet": START_W,
           "method": "exponential weights on each book's daily closed-trade result (eta %.1f, results cut to +/-%.0f%% "
                     "for the score); cap %.0f%%; floor %.0f%% of the equal share until %d closed trades" % (
                         ETA, RET_CLIP * 100, CAP * 100, FLOOR_X * 100, FLOOR_TRADES),
           "daily_result": "closed trades only, booked on the day they close; open trades are not marked",
           "yardstick": "the same books held equally over the same days", "note": NOTE}
    trades, left_out, other, bad = read_books(live_dir, playbook_rows)
    keys = list(trades)
    n = len(keys)
    bases = [STAKE * BOOKS[k] for k in keys]
    n_days = 0 if now_ms < START_MS else int((now_ms - START_MS) // DAY_MS) + 1
    if n_days > MAX_DAYS:
        raise RuntimeError("the clock is %d days past the start" % n_days)
    done = 0 if now_ms < START_MS else int(max(0, now_ms - START_MS - SETTLE_MS) // DAY_MS)   # completed days
    R, C = day_tables(trades, bases, n_days)
    w = walk(R, C)
    t = max(0, n_days - 1)                                        # today's row (day 0 before the start: equal shares)
    net = (R * np.asarray(bases, dtype=float)).sum(axis=0) if n_days else np.zeros(n)
    a_eq = float(w["a_eq"][-1]) if n_days else START_W
    y_eq = float(w["y_eq"][-1]) if n_days else START_W
    out.update(
        status=("running" if n_days else "not started (it starts %s UTC)" % START_UTC[:16].replace("T", " ")),
        as_of_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms // 1000)), today=_day(t),
        days=n_days, days_complete=done, books=n,
        equity=round(a_eq, 2), pct=round((a_eq / START_W - 1.0) * 100.0, 3),
        yardstick_equity=round(y_eq, 2), yardstick_pct=round((y_eq / START_W - 1.0) * 100.0, 3),
        vs_yardstick_pts=round((a_eq - y_eq) / START_W * 100.0, 3),
        cash_pct=round(float(w["cash"][t]) * 100.0, 3),
        shares_today=_share_rows(keys, bases, w["shares"][t], w["score"][t], w["count"][t], C.sum(axis=0), net, n) if n else [],
        books_left_out=[{"book": k[1], "kind": k[0], "why": why} for k, why in left_out.items()],
        books_not_registered=[{"book": str(k[1]), "kind": str(k[0])} for k in other], rows_skipped=int(bad))
    if left_out:
        out["status"] += "; %d book(s) left out at this step (their records could not be read)" % len(left_out)
    rows = []
    for d in range(n_days):
        top = int(np.argmax(w["shares"][d])) if n else None
        rows.append({"day": _day(d), "complete": bool(d < done),
                     "alloc_pct": round(float(w["a_ret"][d]) * 100.0, 4), "yardstick_pct": round(float(w["y_ret"][d]) * 100.0, 4),
                     "alloc_equity": round(float(w["a_eq"][d]), 2), "yardstick_equity": round(float(w["y_eq"][d]), 2),
                     "turnover_pct": round(float(w["turnover"][d]) * 100.0, 3), "trades": int(C[d].sum()),
                     "top_book": None if top is None else keys[top][1],
                     "top_share_pct": None if top is None else round(float(w["shares"][d][top]) * 100.0, 3)})
    out["daily"] = rows[-ROWS_KEPT:]
    out["curve"] = {"first_day": START_UTC[:10], "alloc": [r["alloc_equity"] for r in rows],
                    "yardstick": [r["yardstick_equity"] for r in rows]}
    out["reads"] = dict((str(k), read_of(w["a_ret"][:done], w["y_ret"][:done], k)) for k in READ_DAYS)
    out["verdict"] = "NOT passed. " + "; ".join(
        "%s read (%d days): %s" % (name, k, out["reads"][str(k)]["word"]) for name, k in zip(("first", "second"), READ_DAYS))
    json.dumps(out, allow_nan=False)                              # a number that is not a number (an absurd row) must
    return out                                                    # never reach scoreboard.json: an error, logged upstream
