# -*- coding: utf-8 -*-
import sys, os, json, statistics as st
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
E = json.load(open(os.path.join(A, "enriched.json")))
B = {s: bars(s) for s in MK}; IDX = {s: {b[0]: i for i, b in enumerate(B[s])} for s in MK}
H = 3600e3
LOW = ms("2026-11-21 06:30")
for book, es in E.items():
    print("\n=====", book)
    # before / after the 21 Nov low (by entry time)
    for lab, sel in (("opened before the 21 Nov low", [e for e in es if e["t_in"] < LOW]), ("opened after it", [e for e in es if e["t_in"] >= LOW])):
        pn = [e["pnl_usd"] for e in sel]
        if pn: print("%-30s n=%2d won=%2d net=%9.2f mean=%8.2f" % (lab, len(pn), sum(p > 0 for p in pn), sum(pn), sum(pn) / len(pn)))
    # re-entry after a losing stop on the same market
    by = defaultdict(list)
    for e in es: by[e["sym"]].append(e)
    re = []
    for s, v in by.items():
        v.sort(key=lambda e: e["t_in"])
        for a, b in zip(v, v[1:]):
            if a["pnl_usd"] < 0 and "STOP" in a["why_out"]:
                re.append((b, (b["t_in"] - a["t_out"]) / H, a["side"] == b["side"]))
    if re:
        same = [x for x in re if x[2]]
        print("next trade after a losing stop: n=%d, same side %d, median gap %.1fh; won %d, net %.2f" % (len(re), len(same), st.median(x[1] for x in re), sum(x[0]["pnl_usd"] > 0 for x in re), sum(x[0]["pnl_usd"] for x in re)))
        for b, gap, sm in re: print("   %-8s gap %5.1fh %s %-6s -> %9.2f %s" % (b["sym"], gap, "same side" if sm else "flipped  ", b["why_in"], b["pnl_usd"], b["why_out"]))
    # stops by candle
    c = Counter(ts(e["t_out"]) for e in es if e["pnl_usd"] < 0)
    days = Counter(ts(e["t_out"])[:5] for e in es if e["pnl_usd"] < 0)
    print("losing closes by day:", dict(sorted(days.items())))
    print("candles with 2+ losing closes:", {k: v for k, v in c.items() if v > 1})
    # the stop candle: its range vs the stop distance
    for e in es:
        if e["pnl_usd"] < 0:
            i = IDX[e["sym"]][e["t_out"]]; b = B[e["sym"]][i]
            rng = (b[2] - b[3]) / b[1] * 100
            prev = B[e["sym"]][i - 96:i]
            med = st.median((x[2] - x[3]) / x[1] * 100 for x in prev)
            print("   stop %-8s %s candle range %.2f%% = %.1fx its 24h median; trade's best point %.2f%%, stop distance %s%%, held %.0fh" % (e["sym"], ts(e["t_out"]), rng, rng / med, e["mfe"], "%.2f" % e["stop_pct"] if e["stop_pct"] else "?", e["hold_h"]))
    # concurrency: how many markets short at once (bar by bar, 15m grid)
    grid = range(ms("2026-11-11 08:00"), ms("2026-11-24 11:30"), 900000)
    cnt = []
    for t in grid:
        n = sum(1 for e in es if e["t_in"] <= t < e["t_out"] and e["side"] < 0)
        cnt.append(n)
    print("markets short at the same moment: mean %.1f, max %d, share of time with 5 or more: %.0f%%" % (st.mean(cnt), max(cnt), 100 * sum(x >= 5 for x in cnt) / len(cnt)))
    print("fees total %.2f; gross before fees %.2f" % (sum(e["fees_usd"] for e in es), sum(e["pnl_usd"] + e["fees_usd"] for e in es)))
# main book equity now
ls = json.load(open(os.path.join(A, "data", "live_state.json")))
tot = 0
print("\n===== main books now")
for s, b in ls["books"].items():
    last = B[s][-1][4]
    un = b["qty"] * b["pos"] * (last - b["entry"]) if b["pos"] else 0.0
    tot += b["eq"] + un
    print("%-8s closed-trade equity %9.2f  open: %s  unrealised %8.2f  stop %s  idle %s" % (s, b["eq"], {1: "LONG", -1: "SHORT", 0: "flat"}[b["pos"]] + (" from %.5g (%s)" % (b["entry"], b["why_in"]) if b["pos"] else ""), un, b["stop"], b["idle"]))
print("all eight: %.2f on 80,000 = %+.2f%%" % (tot, (tot / 80000 - 1) * 100))
