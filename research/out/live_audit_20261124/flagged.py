import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
B = {s: bars(s) for s in MK}; IDX = {s: {b[0]: i for i, b in enumerate(B[s])} for s in MK}
for book in ("b_targets", "b_trend30"):
    for r in trades(book):
        i = IDX[r["sym"]].get(r["t_out"])
        o, h, l, c = B[r["sym"]][i][1:]
        if not (l * 0.9985 <= r["p_out"] <= h * 1.0015):
            t1, t2 = r.get("target_1"), r.get("target_2")
            blend = None if t1 is None or t2 is None else (t1 + t2) / 2
            print(book, r["sym"], ts(r["t_in"]), r["why_in"], r["why_out"], "p_out %.5g" % r["p_out"], "T1 %s T2 %s mid %s" % (t1, t2, blend), "stop0", r.get("stop0"), "exit bar L/H %.5g %.5g" % (l, h))
