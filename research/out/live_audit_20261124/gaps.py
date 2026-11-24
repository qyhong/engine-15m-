import sys, os, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
J = journal()
per = defaultdict(Counter); acts = defaultdict(Counter); reasons = defaultdict(Counter)
for (a, t), r in J.items():
    per[a][r["time"][:10]] += 1; acts[a][r["action"]] += 1; reasons[a][r.get("reason")] += 1
days = sorted({d for a in per for d in per[a]})
print("steps journalled per day (crypto full day = 96)")
print("%-8s " % "" + " ".join(d[8:] for d in days))
for a in MK: print("%-8s " % a + " ".join("%2d" % per[a].get(d, 0) for d in days))
for a in MK: print(a, dict(acts[a]))
print()
for a in MK: print(a, dict(reasons[a].most_common(8)))
# bars present but no journal line (crypto only: continuous market)
for a in ("BTCUSDT", "ETHUSDT"):
    b = bars(a); t0 = ms("2026-11-10 13:15")
    miss = [x[0] + 900000 for x in b if x[0] + 900000 >= t0 and (a, x[0] + 900000) not in J]
    runs = []
    for m in miss:
        if runs and m - runs[-1][1] == 900000: runs[-1][1] = m
        else: runs.append([m, m])
    print(a, "closes with no journal line:", len(miss), [(ts(x), ts(y), int((y - x) / 900000) + 1) for x, y in runs])
# USDJPY main position timeline
prev = None
for (a, t), r in sorted(J.items(), key=lambda kv: kv[0][1]):
    if a == "USDJPY" and (r["position"] != prev or r["action"] not in ("HOLD", "IDLE")):
        print("USDJPY", r["time"], r["action"], r["reason"], r["position"], r["edge_pts"], r["decision"][:150]); prev = r["position"]
