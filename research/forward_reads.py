# -*- coding: utf-8 -*-
"""forward_reads -- where each pending "30 closed forward trades" read stands. READ ONLY. PAPER ONLY.

It reads the live trade files, the shadow state, playbook.json and scoreboard.json, and prints for each book:
the closed trades counted the way the registered read counts them, the registered condition (quoted with file
and line), "DUE" or "not due (N of M)", and ONLY when due the numbers that read asks for. While a read is not
due it prints the count, the realised net as a plain fact and the pace of closed trades, nothing else: no
range, no comparison, no verdict text.

It writes nothing, imports nothing from engine15 (so it runs piped over ssh on the box as well as on a copy):

    cd /data/mind15 && /data/venv/bin/python - < research/forward_reads.py
    py -3 -X utf8 research/forward_reads.py --live-dir <copy>/out/live --state <copy>/data/shadow_state.json

Counting follows engine15/reports.py: one row per closed trade from out/live/(shadow_)trades_*.csv, rows of ONE
file that share (time_in, side) are one trade closed in parts and count once (`per_entry`, think15-v5.2.6);
P&L is pnl_usd after fees. The 90% range and the verdict words, printed only for a book that is due, are
`reports._stats` copied exactly (MIN_TRADES 30, half = 1.645 sd / sqrt(n)).

Standard library only (numpy / pandas not needed).
"""
import argparse
import csv
import glob
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

MIN_TRADES = 30
UTC = timezone.utc

# the registered conditions, quoted (file:line as of 22 Nov 2026)
REG = {
    "b_targets": [
        ('docs/CHARTER.md:107-108', '"L4: out/live/scoreboard.json and page.json \\"scoreboard_all\\": every book (main, shadows, '
         'strategy books), live trades only, net, a 90% range per trade, a verdict once a book has 30 trades."'),
        ('research/HYPOTHESES.md:3259 (and 3396)', '"... `b_be_t1` and `b_targets` keep running, and the lines are read at 30 '
         'closed forward trades."'),
        ('engine15/reports.py:156-161', 'verdict: ahead if the low end of the 90% range per trade > 0, behind if the high end '
         '< 0, else undecided (comparison with ZERO, all markets pooled).'),
        ('NOT registered', 'which moment is "the read" (research/VERDICT_RULES.md rule 1 pins it for b_trail and p8_fvg '
         'only), what follows from each verdict, and how the think15-v5.2.9 early entry (BTC/ETH, 22 Nov) is treated.'),
    ],
    "f_floor_33_3r": [
        ('research/HYPOTHESES.md:3523', '"Read it at 30 closed forward trades against the hold copy on the same trades, not '
         'before. Nothing follows from it for the main book without a new registration."'),
        ('research/HYPOTHESES.md:3469', '"... proposed to the owner as a FORWARD shadow book beside the main book, read at 30 '
         'closed forward trades like the other exit books."'),
        ('NOT registered', 'what counts as ahead / behind / undecided against the hold copy (no statistic, no threshold), '
         'whether the trade adopted at the start (opened before the book existed) counts as forward, and whether the 30 '
         'are pooled (other exit books: "per book (all markets together)", HYPOTHESES.md:955).'),
    ],
    "main": [
        ('docs/CHARTER.md:107-108', '"... every book (main, shadows, strategy books), live trades only, net, a 90% range '
         'per trade, a verdict once a book has 30 trades."'),
        ('engine15/reports.py:186-187', '"Only trades closed live count (the main books since 10 Nov ...)"; the eight '
         'markets pooled, compared with zero.'),
        ('research/HYPOTHESES.md:3053', '"... their USDJPY lines and the main book\'s own are read at 30 closed forward '
         'trades, as research/VERDICT_RULES.md says" (VERDICT_RULES.md has no section on the main books or USDJPY).'),
        ('NOT registered', 'whether the per-market "lines" (USDJPY, S&P 500) mean 30 trades in that market or 30 pooled; '
         'how trades under v5.2.5-v5.2.8 rule changes are split; what follows from each verdict.'),
    ],
    "paper_desk": [
        ('docs/CHARTER.md:488', '"It models the book\'s trades at three sizes, not the vault. A first read at 30 closed trades."'),
        ('research/HYPOTHESES.md:3635 (H63)', '"This is a description, not a hypothesis with a pass bar: nothing can \\"pass\\"."'),
        ('NOT registered', '30 closed trades of what (the desk\'s trades, or each wallet\'s joined-and-closed trades, which '
         'differ when the brake skips a trade), what is reported, and against what.'),
    ],
    "b_trend30": [
        ('NOT registered', 'no H67 block and no `b_trend30` in research/HYPOTHESES.md, docs/ or engine15/ (local and '
         'server copies, 22 Nov 2026 ~10:50 UTC).'),
    ],
    "rl": [
        ('docs/CHARTER.md:423', '"Verdict rule for all three books: nothing before 30 closed forward trades PER COIN."'),
        ('configs/rl/phase5.yaml:53-54 (p5_rlq)', '"no forward verdict before 30 closed forward trades per coin; then, after '
         'fees, by Phase 4\'s rule against spot and perp buy-and-hold since go-live (Sharpe and Calmar), stated with its '
         'uncertainty. Not a pass in history."'),
        ('research/HYPOTHESES.md:879-881 (p6_*)', '"no verdict before 30 closed forward trades per coin; then, after fees, '
         'Sharpe and Calmar since go-live against spot and perp buy-and-hold, `p5_rlq`, and each other."'),
        ('configs/rl/phase4.yaml:127-128', '"beats_benchmarks": seed-mean Sharpe above the benchmark\'s, every seed\'s Sharpe '
         'above it, and seed-mean Calmar above it.'),
        ('NOT registered', 'whether a coin is read when IT reaches 30 or only when both coins have; the scoreboard pools '
         'both coins and will print a verdict at 30 pooled, which the per-coin rule does not allow.'),
    ],
}


# ------------------------------------------------------------------ helpers (copies of engine15/reports.py)
def per_entry(rows):
    """reports.per_entry, verbatim in effect: rows sharing a key are one trade; a row without a key counts alone."""
    out, at = [], {}
    for key, pnl in rows:
        if key in (None, "") or key not in at:
            if key not in (None, ""):
                at[key] = len(out)
            out.append(float(pnl))
        else:
            out[at[key]] += float(pnl)
    return out


def stats(pnls):
    """reports._stats, the same formula and words. Called ONLY for a book whose read is due."""
    n = len(pnls)
    if not n:
        return {"trades": 0}
    mean = sum(pnls) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in pnls) / (n - 1)) if n > 1 else 0.0
    half = 1.645 * sd / math.sqrt(n) if n > 1 else None
    lo, hi = (None, None) if half is None else (mean - half, mean + half)
    if n < MIN_TRADES:
        verdict = "too few trades to judge (%d of %d)" % (n, MIN_TRADES)
    elif lo is not None and lo > 0:
        verdict = "ahead: even the low end of the range is positive"
    elif hi is not None and hi < 0:
        verdict = "behind: even the high end of the range is negative"
    else:
        verdict = "undecided: the range includes zero"
    return {"trades": n, "net_usd": round(sum(pnls), 2), "mean_usd": round(mean, 2),
            "range90_usd": None if lo is None else [round(lo, 2), round(hi, 2)], "verdict": verdict,
            "won_pct": round(100.0 * sum(1 for x in pnls if x > 0) / n, 1)}


def ts(s):
    """'2026-11-11 06:45' or '2026-11-10 17:00:00+00:00' -> aware datetime (minute precision), None if empty."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:16], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
    except ValueError:
        return None


def fmt(d):
    return "-" if d is None else d.strftime("%Y-%m-%d %H:%M")


def read_trades(path):
    """One trade file -> list of trades (per_entry within this file), each
    {key, side, pnl, t_in, t_out, rows, why_out, market}."""
    market = os.path.basename(path)[:-4].rsplit("_", 1)[1]
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    v = float(r.get("pnl_usd") or "nan")
                except ValueError:
                    continue
                if v != v:
                    continue
                t_in = (r.get("time_in") or "").strip()
                rows.append(((t_in, r.get("side")) if t_in else None, v, r))
    except OSError:
        return []
    trades, at = [], {}
    for key, v, r in rows:
        if key is None or key not in at:
            if key is not None:
                at[key] = len(trades)
            trades.append({"key": key, "side": r.get("side"), "pnl": v, "t_in": ts(r.get("time_in")),
                           "t_out": ts(r.get("time_out")), "rows": 1, "why_out": r.get("why_out"), "market": market})
        else:
            t = trades[at[key]]
            t["pnl"] += v
            t["rows"] += 1
            t["why_out"] = "%s+%s" % (t["why_out"], r.get("why_out"))
            o = ts(r.get("time_out"))
            if o and (t["t_out"] is None or o > t["t_out"]):
                t["t_out"] = o                                   # the trade is closed when its last part is
    check = per_entry([(k, v) for k, v, _ in rows])              # the same count as reports.per_entry, by construction
    assert len(check) == len(trades) and abs(sum(check) - sum(t["pnl"] for t in trades)) < 1e-6
    return trades


def book_trades(live_dir, pattern):
    out = []
    for p in sorted(glob.glob(os.path.join(live_dir, pattern))):
        out += read_trades(p)
    return out


def pace(n, start, now, need=MIN_TRADES):
    """Closed trades per day since `start`, and the date the count reaches `need` at that pace."""
    if start is None or now <= start:
        return None, None
    days = (now - start).total_seconds() / 86400.0
    rate = n / days if days > 0 else 0.0
    if n >= need:
        return rate, None
    if rate <= 0:
        return rate, None
    return rate, now + timedelta(days=(need - n) / rate)


def load_json(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def first_n(trades, n=MIN_TRADES):
    """The trades closed up to and including the close that made the count reach n (two closing at the same time
    are both in, as in the first scoreboard written at or past n)."""
    tt = sorted([t for t in trades if t["t_out"] is not None], key=lambda t: t["t_out"])
    if len(tt) < n:
        return None, None
    cut = tt[n - 1]["t_out"]
    return [t for t in tt if t["t_out"] <= cut], cut


# ------------------------------------------------------------------ printing
L = []


def out(s=""):
    L.append(s)


def head(title):
    out("")
    out("=" * 100)
    out(title)
    out("=" * 100)


def registered(key):
    out("Registered:")
    for where, text in REG[key]:
        out("  [%s] %s" % (where, text))


def status_line(n, need=MIN_TRADES):
    return "DUE (%d of %d)" % (n, need) if n >= need else "not due (%d of %d)" % (n, need)


def show_pace(n, start, now, label=""):
    rate, eta = pace(n, start, now)
    if rate is None:
        out("  Pace%s: no start time" % label)
    elif eta is None and n < MIN_TRADES:
        out("  Pace%s: %d closed since %s (no closes yet: no estimate)" % (label, n, fmt(start)))
    elif eta is None:
        out("  Pace%s: %.2f closed trades a day since %s" % (label, rate, fmt(start)))
    else:
        out("  Pace%s: %.2f closed trades a day since %s; at this pace trade %d closes about %s UTC (an estimate, not a "
            "date)" % (label, rate, fmt(start), MIN_TRADES, eta.strftime("%Y-%m-%d")))
    return rate, eta


def show_due_stats(name, trades, extra=None):
    sel, cut = first_n(trades)
    if sel is not None:
        s = stats([t["pnl"] for t in sel])
        out("  The read at the 30th close (%s UTC; trades closed up to then: %d): %s" % (fmt(cut), len(sel), json.dumps(s)))
    s_all = stats([t["pnl"] for t in trades])
    out("  All closed trades to date (what scoreboard.json shows now): %s" % json.dumps(s_all))
    if extra:
        extra()


# ------------------------------------------------------------------ the books
def b_targets(a, now, state):
    head("1. Setups book `b_targets` (shadow book; the book the vault follows on BTC and ETH)")
    registered("b_targets")
    tr = book_trades(a.live_dir, "shadow_trades_b_targets_*.csv")
    n = len(tr)
    rows = sum(t["rows"] for t in tr)
    out("Counted: %d closed trades from %d rows (rows sharing time_in and side within one market file count once; "
        "%d such merge(s))" % (n, rows, rows - n))
    per = {}
    for t in tr:
        per.setdefault(t["market"], []).append(t)
    out("  per market: " + ", ".join("%s %d" % (m, len(v)) for m, v in sorted(per.items())))
    out("  BTC+ETH (what members follow): %d" % sum(len(per.get(m, [])) for m in ("BTCUSDT", "ETHUSDT")))
    last = max((t["t_out"] for t in tr if t["t_out"]), default=None)
    out("  last close: %s UTC; realised net (a plain fact, not a read): %+.2f USD" % (fmt(last), sum(t["pnl"] for t in tr)))
    opens = []
    for m, b in sorted(((state or {}).get("books", {}).get("b_targets") or {}).items()):
        if b and b.get("pos"):
            opens.append("%s %s since %s%s" % (m, "LONG" if b["pos"] > 0 else "SHORT",
                                              fmt(datetime.fromtimestamp(b["t_in_ms"] / 1000, UTC)) if b.get("t_in_ms") else "?",
                                              " (Target 1 taken)" if b.get("t1_hit") else ""))
    out("  open now (any of these closing makes the next count): " + ("; ".join(opens) if opens else "none"))
    out("  The 30th trade: the next b_targets trade whose LAST part closes, in any of the 8 markets. A Target 1 half "
        "alone writes no row for this book (its rows are written once, at the final exit, e.g. T1+T2, T1+STOP_BE), "
        "so it does not count until the rest closes.")
    out("Status: " + status_line(n))
    start = min((ts(g.get("started_utc")) for g in ((state or {}).get("groups") or {}).values() if g.get("started_utc")),
                default=None)
    show_pace(n, start, now)
    if n >= MIN_TRADES:
        show_due_stats("b_targets", tr)


def floor_follower(a, now, state):
    head("2. Profit-floor follower `f_floor_33_3r` (H61) against the hold copy `main` (shadow)")
    registered("f_floor_33_3r")
    books = (state or {}).get("books", {})
    fb, hb = books.get("f_floor_33_3r") or {}, books.get("main") or {}
    started = dict((m, b.get("copied_utc") or "-") for m, b in fb.items())
    out("Markets the follower has started in (copied from the hold copy at): " +
        (", ".join("%s %s" % kv for kv in sorted(started.items())) if started else "none"))
    missing = sorted(set(hb) - set(fb))
    if missing:
        out("  not started yet (their group has had no session since the book was added): " + ", ".join(missing))
    inherited = dict((m, (b.get("stats") or {}).get("n", 0)) for m, b in fb.items() if (b.get("stats") or {}).get("n"))
    if inherited:
        out("  NOTE: the state's trade counter includes trades inherited from the hold copy at the start: %s; the page's "
            "\"trades\" for this book is therefore NOT its forward count. Counted here from its own trade files only."
            % inherited)
    tr = book_trades(a.live_dir, "shadow_trades_f_floor_33_3r_*.csv")
    n = len(tr)
    out("Counted: %d closed forward trades (shadow_trades_f_floor_33_3r_*.csv; same counting as the scoreboard)" % n)
    if tr:
        per = {}
        for t in tr:
            per.setdefault(t["market"], 0)
            per[t["market"]] += 1
        out("  per market: " + ", ".join("%s %d" % kv for kv in sorted(per.items())))
        out("  realised net of its own closed trades (a plain fact, not a comparison): %+.2f USD" % sum(t["pnl"] for t in tr))
        out("  of which left at its own floor (why_out FLOOR): %d" % sum(1 for t in tr if "FLOOR" in str(t["why_out"])))
    adopted = [m for m, b in fb.items() if b.get("adopted")]
    if adopted:
        out("  open trades it adopted at the start (opened by the hold copy before the book existed): " + ", ".join(sorted(adopted)))
    out("Status: " + status_line(n))
    # pace: the follower takes exactly the hold copy's trades, so its pace is the hold copy's
    h = book_trades(a.live_dir, "shadow_trades_main_*.csv")
    start = min((ts(g.get("started_utc")) for g in ((state or {}).get("groups") or {}).values() if g.get("started_utc")),
                default=None)
    out("  The follower closes a trade only when the hold copy does (or earlier, at its floor, on the same trade), so its "
        "pace is the hold copy's: %d closed in all 8 markets since %s." % (len(h), fmt(start)))
    show_pace(len(h), start, now, " (hold copy, all markets; the follower's 30 counts only trades closed after it started)")
    if n >= MIN_TRADES:
        out("  The registered read: against the hold copy on the same trades. No statistic or threshold was registered; "
            "the numbers below are the comparison only, not graded.")
        hold = dict(((t["market"], t["key"]), t) for t in h)
        diffs, unmatched = [], 0
        for t in tr:
            m = hold.get((t["market"], t["key"]))
            if m is None:
                unmatched += 1
                continue
            diffs.append(t["pnl"] - m["pnl"])
        out("  same trades matched (market, time_in, side): %d, unmatched: %d" % (len(diffs), unmatched))
        if diffs:
            s = stats(diffs)
            out("  floor minus hold per matched trade, USD: sum %+.2f, mean %+.2f, 90%% range %s, floor better on %d, "
                "worse on %d, equal on %d" % (sum(diffs), s["mean_usd"], s["range90_usd"], sum(1 for d in diffs if d > 1e-9),
                                               sum(1 for d in diffs if d < -1e-9), sum(1 for d in diffs if abs(d) <= 1e-9)))
        vs = 0.0
        for m, b in fb.items():                                  # shadows.scoreboard's vs_main_usd: same assets only
            hm = hb.get(m)
            if hm is None:
                continue
            vs += b.get("equity_marked", b.get("eq", 10000.0)) - hm.get("equity_marked", hm.get("eq", 10000.0))
        out("  vs_main_usd (marked equity, follower minus hold copy, same markets, since each market's copy): %+.2f" % vs)


def main_books(a, now, state):
    head("3. Main books (the eight markets' own books)")
    registered("main")
    tr = book_trades(a.live_dir, "trades_*.csv")
    n = len(tr)
    rows = sum(t["rows"] for t in tr)
    out("Counted: %d closed trades from %d rows (%d merge(s) of a trade closed in parts)" % (n, rows, rows - n))
    per = {}
    for t in tr:
        per.setdefault(t["market"], 0)
        per[t["market"]] += 1
    out("  per market: " + ", ".join("%s %d" % kv for kv in sorted(per.items())))
    out("  realised net (a plain fact, not a read): %+.2f USD" % sum(t["pnl"] for t in tr))
    out("Status: " + status_line(n))
    start = min((t["t_in"] for t in tr if t["t_in"]), default=None)
    show_pace(n, start, now)
    if n >= MIN_TRADES:
        show_due_stats("main", tr)


def paper_desk(a, now, sb):
    head("4. Paper desk (three paper wallets on b_targets' BTC and ETH trades; engine15/paper_desk.py)")
    registered("paper_desk")
    pdk = (sb or {}).get("paper_desk")
    start = datetime(2026, 11, 23, 0, 0, tzinfo=UTC)
    if pdk and pdk.get("started_utc"):
        try:
            start = datetime.strptime(pdk["started_utc"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
        except ValueError:
            pass
    if not pdk:
        out("Live: NO paper_desk block in scoreboard.json (the desk ships with think15-v5.2.9 and starts %s UTC)." % fmt(start))
    else:
        out("Live block: status %r, desk trades %s, as of %s" % (pdk.get("status"), pdk.get("trades"), pdk.get("as_of_utc")))
        for w in pdk.get("wallets") or []:
            out("  wallet %s (%s): closed %s, joined %s, not joined %s, status %s" % (
                w.get("key"), w.get("title"), w.get("closed"), w.get("joined"), w.get("not_joined"), w.get("status")))
    # the book's BTC/ETH trades opened at or after the desk's start, deduplicated as the desk does
    tr = [t for t in book_trades(a.live_dir, "shadow_trades_b_targets_BTCUSDT.csv") +
          book_trades(a.live_dir, "shadow_trades_b_targets_ETHUSDT.csv") if t["t_in"] and t["t_in"] >= start]
    n = len(tr)
    out("Counted from the trade files: %d closed b_targets BTC/ETH trades opened at or after %s UTC" % (n, fmt(start)))
    counts = [n] + [w.get("closed") or 0 for w in ((pdk or {}).get("wallets") or [])]
    out("Status: " + status_line(n) + " by the book's trades; by each wallet's closed trades: " +
        (", ".join("%s %s" % (w.get("key"), status_line(w.get("closed") or 0)) for w in (pdk or {}).get("wallets") or [])
         or "no wallets yet"))
    # pace: the book's BTC+ETH trades since the book started
    allbe = book_trades(a.live_dir, "shadow_trades_b_targets_BTCUSDT.csv") + \
        book_trades(a.live_dir, "shadow_trades_b_targets_ETHUSDT.csv")
    s0 = datetime(2026, 11, 11, 5, 45, tzinfo=UTC)
    rate, _ = pace(len(allbe), s0, now)
    if rate:
        eta = max(now, start) + timedelta(days=(MIN_TRADES - n) / rate) if n < MIN_TRADES else None
        out("  Pace: b_targets has closed %.2f BTC/ETH trades a day since %s; from the desk's start, trade 30 about %s UTC "
            "(an estimate)" % (rate, fmt(s0), eta.strftime("%Y-%m-%d") if eta else "-"))
    if max(counts) >= MIN_TRADES and pdk:
        out("  DUE by at least one count. What the registered read reports was not fixed; the desk's own numbers now:")
        for w in pdk.get("wallets") or []:
            out("    %s %s: equity %s (%s%%), worst fall %s%%, closed %s, wins %s, fees %s, funding %s, status %s" % (
                w.get("key"), w.get("title"), w.get("equity"), w.get("pct"), w.get("worst_fall_pct"), w.get("closed"),
                w.get("wins"), w.get("fees_usd"), w.get("funding_paid_usd"), w.get("status")))


def trend30(a, now, state):
    head("5. Trend-filter shadow `b_trend30` (H67)")
    registered("b_trend30")
    files = glob.glob(os.path.join(a.live_dir, "shadow_trades_b_trend30_*.csv"))
    in_state = "b_trend30" in ((state or {}).get("books") or {})
    if not files and not in_state:
        out("Live: does not exist (no trade file, not in shadow_state.json).")
        out("Status: not due (0 of 30); no start, no pace.")
        return
    tr = book_trades(a.live_dir, "shadow_trades_b_trend30_*.csv")
    out("Counted: %d closed trades; in state: %s" % (len(tr), in_state))
    out("  realised net (a plain fact): %+.2f USD" % sum(t["pnl"] for t in tr))
    out("Status: " + status_line(len(tr)) + " (no registered rule found; nothing is printed beyond the count)")


def rl_books(a, now, pb):
    head("6. RL books `p5_rlq`, `p6_mtrend`, `p6_p4trend` (30 closed forward trades PER COIN)")
    registered("rl")
    if not pb:
        out("playbook.json not readable")
        return
    for mod, book, reg in (("playbook5", "p5_rlq", "2026-11-12 04:30"), ("playbook6", "p6_mtrend", "2026-11-13 03:00"),
                           ("playbook6", "p6_p4trend", "2026-11-13 03:00")):
        b = (pb.get(mod) or {}).get(book)
        if not b:
            out("%s: not in playbook.json" % book)
            continue
        start = datetime.strptime((b.get("registered") or reg)[:16], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        out("%s (go-live %s UTC):" % (book, fmt(start)))
        per = b.get("by_asset") or {}
        bk = b.get("books") or {}
        dues = []
        for coin in ("BTCUSDT", "ETHUSDT"):
            c = (bk.get(coin) or {}).get("closed")
            if c is None:
                c = (per.get(coin) or {}).get("trades", 0)
            c = int(c or 0)
            dues.append(c >= MIN_TRADES)
            rate, eta = pace(c, start, now)
            fb = (bk.get(coin) or {}).get("seed_fallback")
            out("  %s: %s; realised net %s USD (plain fact)%s; pace %s%s" % (
                coin, status_line(c), (per.get(coin) or {}).get("net_usd"),
                "; all seeds on the fallback now" if fb and all(fb) else "",
                "%.2f a day" % rate if rate is not None else "-",
                ", 30 about %s UTC (estimate)" % eta.strftime("%Y-%m-%d") if eta else (" (no closes: no estimate)" if c == 0 else "")))
            if c >= MIN_TRADES:
                v = bk.get(coin) or {}
                out("    DUE on this coin. Numbers the registered read asks for that this file holds: equity %s, return %s%%, "
                    "max DD %s%%; spot buy-and-hold %s (%s%%), its max DD %s%%. Sharpe, Calmar and perp buy-and-hold "
                    "are NOT in playbook.json: compute them from the decision records before the read."
                    % (v.get("equity_usd"), v.get("return_pct"), v.get("max_dd_pct"), v.get("bh_spot_equity_usd"),
                       v.get("bh_spot_return_pct"), v.get("bh_max_dd_pct")))
        out("  book: %s" % ("DUE on both coins" if all(dues) else "DUE on one coin only (whether that is a read was not "
                                                                 "registered)" if any(dues) else "not due on either coin"))
    sb_rows = [r for r in (load_json(os.path.join(a.live_dir, "scoreboard.json")) or {}).get("rows", [])
               if r.get("book") in ("p5_rlq", "p6_mtrend", "p6_p4trend")]
    if sb_rows:
        out("  NOTE: scoreboard.json pools the two coins for these books (%s) and will print an ahead/behind verdict at 30 "
            "pooled; under the registered per-coin rule that text is not a read."
            % ", ".join("%s %d" % (r["book"], r["trades"]) for r in sb_rows))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--live-dir", default=os.path.join("out", "live"))
    ap.add_argument("--state", default=os.path.join("data", "shadow_state.json"))
    ap.add_argument("--playbook", default=None, help="default: <live-dir>/playbook.json")
    ap.add_argument("--scoreboard", default=None, help="default: <live-dir>/scoreboard.json")
    ap.add_argument("--now", default=None, help="UTC 'YYYY-mm-dd HH:MM' (default: the clock)")
    a = ap.parse_args(argv)
    now = (datetime.strptime(a.now, "%Y-%m-%d %H:%M").replace(tzinfo=UTC) if a.now
           else datetime.now(UTC).replace(second=0, microsecond=0))
    state = load_json(a.state)
    pb = load_json(a.playbook or os.path.join(a.live_dir, "playbook.json"))
    sb = load_json(a.scoreboard or os.path.join(a.live_dir, "scoreboard.json"))
    out("forward_reads: STATUS, NOT A READ. Paper only. Run %s UTC on %s" % (fmt(now), os.path.abspath(a.live_dir)))
    out("scoreboard.json written %s; shadow_state.json updated %s" % ((sb or {}).get("generated_utc"),
                                                                     (state or {}).get("updated_utc")))
    out("A read is made when its registered condition is met and not before. Below a count of 30, only the count, the "
        "realised net (a plain fact) and the pace are printed.")
    b_targets(a, now, state)
    floor_follower(a, now, state)
    main_books(a, now, state)
    paper_desk(a, now, sb)
    trend30(a, now, state)
    rl_books(a, now, pb)
    sys.stdout.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
