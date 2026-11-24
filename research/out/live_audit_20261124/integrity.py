# -*- coding: utf-8 -*-
import sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
B = {s: bars(s) for s in MK}
IDX = {s: {b[0]: i for i, b in enumerate(B[s])} for s in MK}
J = journal()
books = sorted(set(os.path.basename(p)[len("shadow_trades_"):].rsplit("_", 1)[0] for p in glob.glob(os.path.join(A, "out", "live", "shadow_trades_*.csv"))))
print("bars span:", {s: (ts(B[s][0][0]), ts(B[s][-1][0]), len(B[s])) for s in MK})
issues = []
tot = 0
for book in ["main"] + books:
    rows = trades(book)
    tot += len(rows)
    # per market: order, overlap, equity chain
    for sym in MK:
        rs = [r for r in rows if r["sym"] == sym]
        prev_eq, prev_out = None, None
        seen = set()
        for r in rs:
            key = (r["t_in"], r["t_out"], r["why_out"])
            if key in seen: issues.append((book, sym, ts(r["t_in"]), "duplicate row"))
            seen.add(key)
            if r["t_out"] < r["t_in"]: issues.append((book, sym, ts(r["t_in"]), "closes before it opens"))
            # direction of result vs prices
            gross = r["side"] * (r["p_out"] - r["p_in"]) * r["qty"]
            net = gross - r["fees_usd"]
            if abs(net - r["pnl_usd"]) > max(1.0, 0.02 * abs(r["pnl_usd"])):
                # fees may be both-sides vs this-part; report the gap
                issues.append((book, sym, ts(r["t_in"]), "pnl %.2f vs qty*move-fees %.2f (gross %.2f fees %.2f)" % (r["pnl_usd"], net, gross, r["fees_usd"])))
            if prev_eq is not None and abs(prev_eq + r["pnl_usd"] - r["equity"]) > 0.02:
                issues.append((book, sym, ts(r["t_in"]), "equity chain: %.2f + %.2f != %.2f" % (prev_eq, r["pnl_usd"], r["equity"])))
            prev_eq = r["equity"]
            # prices inside the bars
            for t, p, lab in ((r["t_in"], r["p_in"], "entry"), (r["t_out"], r["p_out"], "exit")):
                i = IDX[sym].get(t)
                if i is None:
                    issues.append((book, sym, ts(r["t_in"]), "%s bar %s not in the bar file" % (lab, ts(t)))); continue
                o, h, l, c = B[sym][i][1:]
                # allow slippage of 0.1%
                if not (l * 0.9985 <= p <= h * 1.0015):
                    pb = B[sym][i - 1]
                    ok_prev = pb[3] * 0.9985 <= p <= pb[2] * 1.0015
                    issues.append((book, sym, ts(r["t_in"]), "%s price %.5g outside its bar %s [%.5g, %.5g]%s" % (lab, p, ts(t), l, h, " (inside the bar before)" if ok_prev else "")))
        # overlaps between different entries
        ents = merged(rs)
        for a, b in zip(ents, ents[1:]):
            if b["t_in"] < a["t_out"]:
                issues.append((book, sym, ts(b["t_in"]), "opens before the previous trade closed (%s)" % ts(a["t_out"])))
print("rows checked:", tot)
from collections import Counter
c = Counter((i[0], i[3].split(" ")[0] + " " + i[3].split(" ")[1]) for i in issues)
for k, v in sorted(c.items()): print(v, k)
print()
for i in issues[:400]: print(i)
