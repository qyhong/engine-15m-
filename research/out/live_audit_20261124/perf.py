# -*- coding: utf-8 -*-
import sys, os, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
B = {s: bars(s) for s in MK}; IDX = {s: {b[0]: i for i, b in enumerate(B[s])} for s in MK}
J = journal()
H = 3600e3

def enrich(e):
    s, side = e["sym"], e["side"]
    i0, i1 = IDX[s].get(e["t_in"]), IDX[s].get(e["t_out"])
    seg = B[s][i0:i1 + 1]
    hi, lo = max(b[2] for b in seg), min(b[3] for b in seg)
    p = e["p_in"]
    e["mfe"] = (hi - p) / p * 100 if side > 0 else (p - lo) / p * 100
    e["mae"] = (p - lo) / p * 100 if side > 0 else (hi - p) / p * 100
    e["move"] = e["pnl_usd"] / (e["qty"] * p) * 100 if e["qty"] else None   # realised % of notional, net
    e["hold_h"] = (e["t_out"] - e["t_in"]) / H
    r0 = e["parts"][0]
    e["R"] = (e["pnl_usd"] / r0["risk_usd"]) if r0.get("risk_usd") else None
    e["stop_pct"] = abs(r0["stop0"] - p) / p * 100 if r0.get("stop0") else None
    j = J.get((s, e["t_in"])) or {}
    e["lead"] = None if j.get("edge_pts") is None else j["edge_pts"] * side      # in the trade's direction
    e["jact"], e["regime"], e["struct"] = j.get("action"), j.get("regime"), j.get("structure")
    # after the exit: best and worst move in the trade's direction over the next 24h (96 bars)
    post = B[s][i1 + 1:i1 + 97]
    px = e["p_out_last"]
    if post:
        phi, plo = max(b[2] for b in post), min(b[3] for b in post)
        e["post_fav"] = (phi - px) / px * 100 if side > 0 else (px - plo) / px * 100
        e["post_adv"] = (px - plo) / px * 100 if side > 0 else (phi - px) / px * 100
        e["post_n"] = len(post)
    else:
        e["post_fav"] = e["post_adv"] = None; e["post_n"] = 0
    return e

def f(x, n=2, w=7):
    return ("%*s" % (w, "-")) if x is None else "%*.*f" % (w, n, x)

def table(book):
    es = [enrich(e) for e in merged(trades(book))]
    print("\n===== %s: %d trades =====" % (book, len(es)))
    print("sym      side in           out          hold_h why_in  why_out        lead   pnl$     R   move%  mfe%   mae%  stop% | 24h after exit: fav%  adv%")
    for e in es:
        print("%-8s %-5s %s  %s %6.1f %-7s %-13s %s %8.2f %s %s %s %s %s |  %s %s" % (
            e["sym"], "LONG" if e["side"] > 0 else "SHORT", ts(e["t_in"]), ts(e["t_out"]), e["hold_h"], e["why_in"], e["why_out"][:13],
            f(e["lead"], 1, 5), e["pnl_usd"], f(e["R"], 2, 5), f(e["move"], 2, 6), f(e["mfe"], 2, 6), f(e["mae"], 2, 6), f(e["stop_pct"], 2, 6), f(e["post_fav"], 2, 6), f(e["post_adv"], 2, 6)))
    return es

def grp(es, key, title):
    g = {}
    for e in es:
        g.setdefault(key(e), []).append(e)
    print("\n-- %s" % title)
    print("%-22s %3s %5s %10s %9s %7s %7s" % ("", "n", "won%", "net$", "mean$", "meanR", "hold_h"))
    for k in sorted(g, key=lambda k: str(k)):
        v = g[k]; pn = [e["pnl_usd"] for e in v]; R = [e["R"] for e in v if e["R"] is not None]
        print("%-22s %3d %5.0f %10.2f %9.2f %7s %7.1f" % (str(k), len(v), 100 * sum(p > 0 for p in pn) / len(v), sum(pn), sum(pn) / len(v), f(st.mean(R), 2, 7) if R else "      -", st.mean(e["hold_h"] for e in v)))

def lb(e):
    l = e["lead"]
    return "lead ?" if l is None else "lead 1: above 5" if l > 5 else "lead 2: 2 to 5" if l >= 2 else "lead 3: under 2" if l >= 0 else "lead 4: against"

def sess(e):
    h = int(ts(e["t_in"])[6:8])
    return "1 Asia 00-07" if h < 7 else "2 Europe 07-13" if h < 13 else "3 US 13-21" if h < 21 else "4 late 21-24"

ALL = {}
for book in ("main", "b_targets", "b_trail"):
    es = table(book); ALL[book] = es
    grp(es, lambda e: e["sym"], "by market")
    grp(es, lambda e: e["why_in"], "by how it opened")
    grp(es, lb, "by Lead at the open (in the trade's direction)")
    grp(es, lambda e: e["why_out"], "by how it closed")
    grp(es, lambda e: "LONG" if e["side"] > 0 else "SHORT", "by side")
    grp(es, sess, "by session of the entry (UTC)")
    grp(es, lambda e: ts(e["t_out"])[:5], "by day closed")
    grp(es, lambda e: "1 under 6h" if e["hold_h"] < 6 else "2 6-24h" if e["hold_h"] < 24 else "3 1-3 days" if e["hold_h"] < 72 else "4 over 3 days", "by holding time")
    # capture and give-back
    w = [e for e in es if e["mfe"] is not None]
    print("\n-- best point reached vs what was kept (%% of price, mean): mfe %.2f, kept %.2f; losers' best point before losing: %.2f (n=%d)" % (
        st.mean(e["mfe"] for e in w), st.mean(e["move"] for e in w),
        st.mean([e["mfe"] for e in w if e["pnl_usd"] <= 0] or [0]), sum(e["pnl_usd"] <= 0 for e in w)))
    stops = [e for e in es if "STOP" in e["why_out"] and e["pnl_usd"] < 0 and e["post_fav"] is not None]
    if stops:
        print("-- after a losing stop, next 24h: mean further move in the trade's direction %.2f%%, against %.2f%%; went the trade's way by more than the loss in %d of %d" % (
            st.mean(e["post_fav"] for e in stops), st.mean(e["post_adv"] for e in stops), sum(e["post_fav"] > abs(e["move"]) for e in stops), len(stops)))
    wins = [e for e in es if e["pnl_usd"] > 0 and e["post_fav"] is not None]
    if wins:
        print("-- after a winning exit, next 24h: mean further move in the trade's direction %.2f%%, against %.2f%% (n=%d)" % (st.mean(e["post_fav"] for e in wins), st.mean(e["post_adv"] for e in wins), len(wins)))
json.dump({b: [{k: v for k, v in e.items() if k != "parts"} for e in es] for b, es in ALL.items()}, open(os.path.join(A, "enriched.json"), "w"), default=str)

# the market itself over the live span
print("\n===== the markets since 10 Nov 13:15 UTC =====")
t0 = ms("2026-11-10 13:15")
for s in MK:
    seg = [b for b in B[s] if b[0] >= t0]
    a, z = seg[0][1], seg[-1][4]
    lo = min(b[3] for b in seg); hi = max(b[2] for b in seg)
    print("%-8s first %.5g last %.5g change %+.1f%%  low %.5g (%+.1f%%) high %.5g (%+.1f%%)" % (s, a, z, (z / a - 1) * 100, lo, (lo / a - 1) * 100, hi, (hi / a - 1) * 100))
