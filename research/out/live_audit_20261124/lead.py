import sys, os, json, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
J = journal()
byA = defaultdict(list)
for (a, t), r in J.items():
    if r.get("edge_pts") is not None: byA[a].append((t, r["edge_pts"], r["price"]))
print("Lead (points) by market over the live span, and what price did over the next 4 hours and 24 hours")
tot = defaultdict(lambda: [0, 0, 0.0, 0, 0, 0.0])
for a in MK:
    v = sorted(byA[a]); px = {t: p for t, e, p in v}
    ab = [abs(e) for t, e, p in v]
    up = sum(e > 0 for t, e, p in v)
    print("\n%-8s steps %4d  Lead favours up in %2.0f%% of steps; |Lead| median %.1f, 90th pct %.1f, max %.1f; above 5: %.1f%% of steps" % (a, len(v), 100 * up / len(v), st.median(ab), sorted(ab)[int(.9 * len(ab))], max(ab), 100 * sum(x > 5 for x in ab) / len(ab)))
    for lab, lo, hi in (("under 2", 0, 2), ("2 to 5", 2, 5), ("5 to 10", 5, 10), ("over 10", 10, 999)):
        row = []
        for hname, hbars in (("4h", 16), ("24h", 96)):
            xs = []
            for t, e, p in v:
                if lo <= abs(e) < hi and e != 0:
                    q = px.get(t + hbars * 900000)
                    if q: xs.append((q / p - 1) * 100 * (1 if e > 0 else -1))
            row.append((hname, xs))
            k = (lab, hname); T = tot[k]; T[0] += len(xs); T[1] += sum(x > 0 for x in xs); T[2] += sum(xs)
        print("   |Lead| %-8s " % lab + "   ".join("%s: n=%4d right side %3.0f%% mean move its way %+.2f%%" % (h, len(xs), 100 * sum(x > 0 for x in xs) / len(xs) if xs else 0, st.mean(xs) if xs else 0) for h, xs in row))
print("\nall eight markets together")
for (lab, h), T in tot.items():
    if T[0]: print("   |Lead| %-8s %s: n=%5d right side %3.0f%% mean move its way %+.2f%%" % (lab, h, T[0], 100 * T[1] / T[0], T[2] / T[0]))
