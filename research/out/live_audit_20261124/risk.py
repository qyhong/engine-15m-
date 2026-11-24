import sys, os, json, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
E = json.load(open(os.path.join(A, "enriched.json")))
for book in ("b_targets", "b_trail"):
    es = E[book]; g = defaultdict(list)
    for e in es:
        eq0 = e["equity"] - e["pnl_usd"]            # equity before (single-market book; parts merged -> last equity)
        r0 = trades(book)
    rows = merged(trades(book))
    print("\n", book)
    allr = []
    for e in rows:
        r = e["parts"][0]
        eq_before = e["parts"][0]["equity"] - e["parts"][0]["pnl_usd"]
        risk = r["risk_usd"] / eq_before * 100
        lev = e["qty"] * e["p_in"] / eq_before if len(e["parts"]) == 1 else sum(p["qty"] for p in e["parts"]) * e["p_in"] / eq_before
        g[e["sym"]].append((risk, lev, e["pnl_usd"] / r["risk_usd"], e["pnl_usd"]))
        allr.append((risk, e["pnl_usd"] / r["risk_usd"], e["pnl_usd"], e["sym"]))
    for s in MK:
        v = g.get(s)
        if v: print("%-8s n=%2d planned loss at the stop: mean %.1f%% of the book (min %.1f, max %.1f); size mean %.1fx; sum R %+.1f; net $%+.0f" % (s, len(v), st.mean(x[0] for x in v), min(x[0] for x in v), max(x[0] for x in v), st.mean(x[1] for x in v), sum(x[2] for x in v), sum(x[3] for x in v)))
    print("all: mean planned loss %.1f%%; share of trades risking more than 2.5%%: %d of %d" % (st.mean(x[0] for x in allr), sum(x[0] > 2.5 for x in allr), len(allr)))
    print("sum of R all markets %+.1f; at a flat 2%% of $10,000 per trade that is $%+.0f (actual $%+.0f)" % (sum(x[1] for x in allr), sum(x[1] for x in allr) * 200, sum(x[2] for x in allr)))
    lossR = [x for x in allr if x[2] < 0]
    print("losing trades: mean loss %.1f%% of the book; crypto %.1f%%, others %.1f%%" % (st.mean(-x[2] / 100 for x in lossR), st.mean([-x[2] / 110 for x in lossR if x[3] in ("BTCUSDT", "ETHUSDT")] or [0]), st.mean([-x[2] / 100 for x in lossR if x[3] not in ("BTCUSDT", "ETHUSDT")] or [0])))
