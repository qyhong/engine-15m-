# -*- coding: utf-8 -*-
"""B trail's SECOND CHECK, as registered in research/VERDICT_RULES.md (approved by the owner 17 Nov 2026). PAPER ONLY.

    py -3 -X utf8 research/b_trail_second_check.py                       laptop copy (out/live, data/shadow_state.json)
    ssh ... '/data/venv/bin/python - --live-dir /data/mind15/out/live --state /data/mind15/data/shadow_state.json' \
        < research/b_trail_second_check.py                               on the box, read only

What it reads (never writes anything):
  * <live-dir>/shadow_trades_b_trail_<MARKET>.csv   the book's closed live trades (the scoreboard's source)
  * <live-dir>/scoreboard.json                      the server scoreboard row for b_trail (when it is there)
  * <state> (shadow_state.json), books -> b_trail and books -> main (the fresh main copy, the hold rule)

The gate. The registered second check is read at the first server scoreboard at or past 60 closed trades AND no earlier
than 10 Dec 2026 (VERDICT_RULES.md section 4, decision table; section 7, lines 3 and 4). Until BOTH hold this script
prints facts only: closed trades, wins, realised net, per-market counts, distinct entry days, open positions. It prints
no verdict, no range, no comparison with any other book. There is no switch to force the graded part: the date is the
UTC clock of the machine it runs on.

When both hold it prints what the registered check asks for, and nothing is decided by the script:
  1. the verdict at 30 as recorded (section 8: "ahead", scoreboard of 2026-11-18 13:18 UTC, 31 trades);
  2. the verdict now, computed exactly as engine15/reports.py _stats (pooled pnl_usd, sample sd, mean +/- 1.645 sd/sqrt n),
     beside the server scoreboard's own row;
  3. condition 1: total marked equity of b_trail minus the fresh main copy's (shadows.scoreboard "vs_main_usd");
  4. condition 2: the same per market, and how many of the 8 are above zero (5 needed);
  5. condition 3: at least 50 closed trades;
  6. which row of the registered decision table that lands in, and the items to report beside it.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import math
import os
import sys

BOOK = "b_trail"
YARDSTICK = "main"                         # shadows.CHALLENGERS["main"]: "Main rule (v5), fresh copy", rule {} = hold
MARKETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")
MIN_TRADES_CHECK = 60                      # VERDICT_RULES.md section 4: "a second check at 60 trades"
NOT_BEFORE = dt.date(2026, 12, 10)         # VERDICT_RULES.md section 7 line 4: "no earlier than 10 Dec 2026"
LAST_CHECK = 100                           # VERDICT_RULES.md section 4: "a last check at 100 trades"
MIN_TRADES_VERDICT = 30                    # engine15/reports.py MIN_TRADES
MIN_TRADES_STANDING = 50                   # condition 3 (THOUGHT_PROCESS.md standing minimum)
MARKETS_NEEDED = 5                         # condition 2: ahead of the fresh main copy in at least 5 of 8 markets
VERDICT_AT_30 = {"verdict": "ahead: even the low end of the range is positive", "scoreboard_utc": "2026-11-18 13:18",
                 "trades": 31, "net_usd": 6330.69, "range90_usd": [138.45, 269.98], "vs_main_usd": 831.0}
HISTORY_NOTE = ("history replay, in-sample: 2020 to Nov 2026, eight markets, -$48,808 against main +$329,439, ahead of "
                "main in 0 of 8 markets (research/out/exits/trail_study.md); the 18 Nov replay to each live start: "
                "-$47,444 against +$187,617 (HANDOFF.md, research/out/b_trail_history/summary.json)")


def utc(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000.0, tz=dt.timezone.utc)


def read_trades(live_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(live_dir, "shadow_trades_%s_*.csv" % BOOK))):
        market = os.path.basename(path)[len("shadow_trades_%s_" % BOOK):-len(".csv")]
        if not market.isalnum():                                  # "setups_BTCUSDT": another book's file (b_trail_setups,
            continue                                              # 26 Nov 2026), never pooled into this registered check
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    pnl = float(r.get("pnl_usd") or "nan")
                except ValueError:
                    continue
                if pnl != pnl:                      # reports.pnl_of skips the same rows
                    continue
                rows.append({"market": market, "pnl": pnl, "side": int(float(r.get("side") or 0)),
                             "t_in": utc(r["t_in_ms"]), "t_out": utc(r["t_out_ms"]),
                             "why_in": r.get("why_in", ""), "why_out": r.get("why_out", ""),
                             "r": float(r["r_mult"]) if r.get("r_mult") not in (None, "") else None})
    rows.sort(key=lambda x: x["t_out"])
    return rows


def stats(pnls):
    """engine15/reports.py _stats, copied line for line (pooled, sample sd, 1.645)."""
    n = len(pnls)
    if not n:
        return {"trades": 0, "net_usd": 0.0, "mean_usd": None, "range90_usd": None, "verdict": "no trades yet"}
    mean = sum(pnls) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in pnls) / (n - 1)) if n > 1 else 0.0
    half = 1.645 * sd / math.sqrt(n) if n > 1 else None
    lo, hi = (None, None) if half is None else (mean - half, mean + half)
    if n < MIN_TRADES_VERDICT:
        verdict = "too few trades to judge (%d of %d)" % (n, MIN_TRADES_VERDICT)
    elif lo is not None and lo > 0:
        verdict = "ahead: even the low end of the range is positive"
    elif hi is not None and hi < 0:
        verdict = "behind: even the high end of the range is negative"
    else:
        verdict = "undecided: the range includes zero"
    return {"trades": n, "net_usd": round(sum(pnls), 2), "mean_usd": round(mean, 2),
            "range90_usd": None if lo is None else [round(lo, 2), round(hi, 2)], "verdict": verdict,
            "won_pct": round(100.0 * sum(1 for x in pnls if x > 0) / n, 1)}


def marked(st):
    return float(st.get("equity_marked", st.get("eq", 10000.0)))


def print_facts(trades, state, now):
    pn = [t["pnl"] for t in trades]
    n = len(pn)
    print("FACTS (no grading)")
    print("  closed trades: %d   wins: %d   realised net: %+.2f USD" % (n, sum(1 for x in pn if x > 0), sum(pn)))
    if trades:
        first, last = min(t["t_in"] for t in trades), max(t["t_out"] for t in trades)
        print("  first entry: %s UTC   latest close: %s UTC" % (first.strftime("%Y-%m-%d %H:%M"), last.strftime("%Y-%m-%d %H:%M")))
    print("  per market (closed / won / realised USD):")
    for m in MARKETS:
        mt = [t for t in trades if t["market"] == m]
        print("    %-8s %3d  %3d  %+10.2f" % (m, len(mt), sum(1 for t in mt if t["pnl"] > 0), sum(t["pnl"] for t in mt)))
    extra = sorted(set(t["market"] for t in trades) - set(MARKETS))
    if extra:
        print("    (files for other markets too: %s)" % ", ".join(extra))
    print("  sides: %d short, %d long" % (sum(1 for t in trades if t["side"] < 0), sum(1 for t in trades if t["side"] > 0)))
    reasons = {}
    for t in trades:
        reasons[t["why_out"]] = reasons.get(t["why_out"], 0) + 1
    print("  exit reasons: " + ", ".join("%s %d" % kv for kv in sorted(reasons.items(), key=lambda kv: -kv[1])))
    days = {}
    for t in trades:
        days[t["t_in"].date()] = days.get(t["t_in"].date(), 0) + 1
    print("  distinct entry days (UTC): %d  ->  %s" % (len(days), ", ".join("%s:%d" % (d.strftime("%d %b"), k)
                                                                            for d, k in sorted(days.items()))))
    print("  open positions (state %s):" % state.get("updated_utc", "?"))
    book = (state.get("books") or {}).get(BOOK) or {}
    any_open = False
    for m in MARKETS:
        st = book.get(m)
        if not st or not st.get("pos"):
            continue
        any_open = True
        t_in = utc(st["t_in_ms"]).strftime("%Y-%m-%d %H:%M") if st.get("t_in_ms") else "?"
        print("    %-8s %-5s since %s UTC  entry %s  stop %s  trail armed: %s" % (
            m, "LONG" if st["pos"] > 0 else "SHORT", t_in, st.get("entry"), round(float(st["stop"]), 5)
            if st.get("stop") is not None else None, "yes" if st.get("trail_on") else "no"))
    if not any_open:
        print("    none")
    if trades:
        span = (now - min(t["t_in"] for t in trades)).total_seconds() / 86400.0
        recent = [t for t in trades if (now - t["t_out"]).total_seconds() <= 7 * 86400]
        print("  pace: %.2f closed trades per calendar day over %.1f days; %d closed in the last 7 days" % (
            n / span if span > 0 else float("nan"), span, len(recent)))


def print_graded(trades, state, scoreboard_row):
    pn = [t["pnl"] for t in trades]
    s = stats(pn)
    n = s["trades"]
    print()
    print("SECOND CHECK (VERDICT_RULES.md section 4; owner's approval 17 Nov 2026, lines 3 and 4)")
    print("  verdict at 30 (recorded, section 8): %s  [scoreboard %s UTC, %d trades, range %s]" % (
        VERDICT_AT_30["verdict"], VERDICT_AT_30["scoreboard_utc"], VERDICT_AT_30["trades"], VERDICT_AT_30["range90_usd"]))
    print("  verdict now, from the trade files: %s" % s["verdict"])
    print("    trades %d, net %+.2f, mean %+.2f, 90%% range %s, won %.1f%%" % (n, s["net_usd"], s["mean_usd"],
                                                                         s["range90_usd"], s["won_pct"]))
    if scoreboard_row:
        print("  server scoreboard row (%s): %s, %s trades, range %s" % (
            scoreboard_row.get("_generated_utc"), scoreboard_row.get("verdict"), scoreboard_row.get("trades"),
            scoreboard_row.get("range90_usd")))
        if scoreboard_row.get("trades") != n:
            print("    NOTE: the scoreboard and the trade files differ in count; the registered reading is the scoreboard's.")
    else:
        print("  server scoreboard row: not found (the registered reading is the first server scoreboard; read it there)")

    books = state.get("books") or {}
    b, m = books.get(BOOK) or {}, books.get(YARDSTICK) or {}
    missing = [a for a in MARKETS if a not in b or a not in m]
    per = {}
    for a in MARKETS:
        if a in b and a in m:
            per[a] = marked(b[a]) - marked(m[a])
    total = sum(marked(b[a]) for a in b) - sum(marked(m[a]) for a in m)
    late = ((state.get("late_starts") or {}).get(BOOK) or {})
    print("  yardstick: shadow book '%s' (the fresh main copy, hold rule), marked equity at state %s" % (
        YARDSTICK, state.get("updated_utc")))
    if late:
        print("    NOTE: state shows a late start for %s %s; the scoreboard then compares since that start only." % (BOOK, late))
    print("  condition 1, total above the fresh main copy (vs_main_usd > 0): %+.2f -> %s" % (total, "met" if total > 0 else "NOT met"))
    ahead = [a for a, v in per.items() if v > 0]
    print("  condition 2, ahead of it in >= %d of 8 markets: %d of %d -> %s" % (
        MARKETS_NEEDED, len(ahead), len(per), "met" if len(ahead) >= MARKETS_NEEDED else "NOT met"))
    for a in MARKETS:
        if a in per:
            print("    %-8s b_trail %10.2f  main copy %10.2f  diff %+10.2f" % (a, marked(b[a]), marked(m[a]), per[a]))
    if missing:
        print("    missing in the state: %s" % ", ".join(missing))
    print("  condition 3, at least %d closed trades: %d -> %s" % (MIN_TRADES_STANDING, n, "met" if n >= MIN_TRADES_STANDING else "NOT met"))

    v_now = s["verdict"].split(":")[0]
    v_30 = VERDICT_AT_30["verdict"].split(":")[0]
    conds = total > 0 and len(ahead) >= MARKETS_NEEDED and n >= MIN_TRADES_STANDING
    if v_now == "ahead" and v_30 == "ahead" and conds:
        row = "'ahead' at 30 and at 60 and all three conditions hold: PROPOSE to the owner (only a proposal)."
    elif v_now == "ahead" and v_30 != "ahead":
        row = "'ahead' at 60 but not at 30: no proposal; same test at 100 with 60 and 100 as checkpoints."
    elif v_now == "ahead":
        row = "'ahead' but a condition fails: no proposal; stays a shadow book; read once more at 100, for the record."
    elif v_now == "undecided":
        row = "'undecided': runs on to 100 trades; no decision."
    else:
        row = "'behind': post-mortem, then the retire-or-reference proposal to the owner."
    print("  decision table row: " + row)
    print("    The owner decides. 'Ahead' is 'ahead on %d live trades', never an edge (section 6 rule 7)." % n)
    print("    Since think15-v5.2.8 (21 Nov 2026) six main books already trail on this rule: a proposal can only")
    print("    concern what is not yet done (USDJPY, SPX) or confirm/withdraw the six; see the status note.")
    if n >= LAST_CHECK:
        print("  WARNING: %d trades is at or past the LAST check (%d). The registered text does not say how the 60 and 100"
              " checks are read when both fall on or before 10 Dec; take the owner's written ruling first." % (n, LAST_CHECK))

    print("  reported beside, not conditions:")
    top = sorted(pn, reverse=True)[:6]
    net = sum(pn)
    print("    share of net from the 6 largest winners: %s" % ("%.0f%%" % (100 * sum(top) / net) if net > 0 else "n/a (net <= 0)"))
    eq, peak, worst = 0.0, 0.0, 0.0
    for t in trades:                                       # pooled realised curve, by close time
        eq += t["pnl"]
        peak = max(peak, eq)
        worst = min(worst, eq - peak)
    print("    worst fall of the pooled realised curve: %.2f USD (main copy's: not computable from closed trades;"
          " it holds)" % worst)
    print("    " + HISTORY_NOTE)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--live-dir", default=os.path.join("out", "live"))
    ap.add_argument("--state", default=os.path.join("data", "shadow_state.json"))
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    trades = read_trades(a.live_dir)
    with open(a.state, encoding="utf-8") as fh:
        state = json.load(fh)
    sb_row = None
    sb_path = os.path.join(a.live_dir, "scoreboard.json")
    if os.path.exists(sb_path):
        with open(sb_path, encoding="utf-8") as fh:
            sb = json.load(fh)
        for r in sb.get("rows", []):
            if r.get("book") == BOOK and r.get("kind") == "shadow":
                sb_row = dict(r, _generated_utc=sb.get("generated_utc"))
    n = len(trades)
    print("B TRAIL SECOND CHECK  run %s UTC  (paper only; read only)" % now.strftime("%Y-%m-%d %H:%M"))
    print("  closed live trades: %d (needs %d)   UTC date: %s (needs %s or later)" % (
        n, MIN_TRADES_CHECK, now.date().isoformat(), NOT_BEFORE.isoformat()))
    if sb_row:
        print("  server scoreboard written %s shows %s trades for %s" % (sb_row["_generated_utc"], sb_row.get("trades"), BOOK))
    print()
    print_facts(trades, state, now)
    count_ok, date_ok = n >= MIN_TRADES_CHECK, now.date() >= NOT_BEFORE
    print()
    if not (count_ok and date_ok):
        why = []
        if not count_ok:
            why.append("%d of %d closed trades" % (n, MIN_TRADES_CHECK))
        if not date_ok:
            why.append("today %s is before %s" % (now.date().isoformat(), NOT_BEFORE.isoformat()))
        print("NOT DUE: the registered second check is not graded today (%s)." % "; ".join(why))
        print("  No verdict, range or comparison with the main copy is printed before both conditions hold.")
        return 0
    print_graded(trades, state, sb_row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
