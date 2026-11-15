# -*- coding: utf-8 -*-
"""liqhunt2 -- the H41 "liquidity hunt v2" rule set: the P1 sweep fade (engine15/playbook.py) with a trend filter,
wider stops, confirmation / retest entries and no round-number pools. PAPER RESEARCH ONLY.

Registered before any code or number: research/HYPOTHESES.md H41 (15 Nov 2026, 05:45 UTC).
History study: research/liqhunt2_study.py -> research/out/liqhunt2/study.md / .json.

Reuses playbook.py unchanged: prepare(), p1_signals() (the H6 sweep detection: k 0.25 ATR, reclaim within 2 bars,
wick >= 50%, funding confirmation on BTC/ETH), htf_bias(), fee_side(), _money(). Only the filters on top of those
signals, the stop pad, the entry (next open / confirmation close / limit retest) and the exit scheme are new here.

THE FRAME (as playbook.py): closed bars only; decision at the close of bar i, fill at the open of bar i+1; a fill
that gaps beyond the stop is not taken; a stop and a target inside one bar = stop first; a gap through the stop fills
at the open; one trade per asset at a time; $10,000 a trade; the asset's own fee a side.
"""
import numpy as np

from . import playbook as pb

BASE_RULE = {"k": 0.25, "m": 2, "exit": "fixed", "confirm": "funding"}   # the H6 registered sweep detection (fixed copy)
HOLD_V2 = 24                       # bars; every v2 variant
HOLD_P1 = 16                       # the original P1
RETEST_BARS = 4                    # a retest limit order lives for the 4 bars after the reclaim

# exit schemes: (fraction, target in R) legs in order; be = the stop to entry from the bar after the first leg fills
EXITS = {"E1": {"legs": ((0.5, 1.0), (0.5, 2.0)), "be": True},
         "E2": {"legs": ((1.0, 1.5),), "be": False}}

VARIANTS = {
    "V1": {"trend": True, "no_round": True, "pad": 0.1, "entry": "open", "exit": "E1", "hold": HOLD_V2},
    "V2": {"trend": True, "no_round": True, "pad": 0.5, "entry": "open", "exit": "E1", "hold": HOLD_V2},
    "V3": {"trend": True, "no_round": True, "pad": 1.0, "entry": "open", "exit": "E1", "hold": HOLD_V2},
    "V4": {"trend": True, "no_round": True, "pad": 0.5, "entry": "confirm", "exit": "E1", "hold": HOLD_V2},
    "V5": {"trend": True, "no_round": True, "pad": 0.5, "entry": "retest", "exit": "E1", "hold": HOLD_V2},
    "V6": {"trend": True, "no_round": True, "pad": 0.5, "entry": "open", "exit": "E2", "hold": HOLD_V2},
    "V7": {"trend": True, "no_round": True, "pad": 0.5, "entry": "confirm", "exit": "E2", "hold": HOLD_V2},
    "V8": {"trend": False, "no_round": True, "pad": 0.5, "entry": "open", "exit": "E1", "hold": HOLD_V2},
}
CONTROL = {"trend": False, "no_round": False, "pad": pb.STOP_PAD_ATR, "entry": "open", "exit": "E1", "hold": HOLD_P1}


def n_levers(var):
    """Levers changed from the original P1 (the registered tie-break: fewer levers)."""
    return (int(var["trend"]) + int(var["no_round"]) + int(var["pad"] != pb.STOP_PAD_ATR) + int(var["entry"] != "open")
            + int(var["exit"] != "E1") + int(var["hold"] != HOLD_P1))


def base_signals(P, no_round):
    """The H6 sweep signals; with no_round the round-number pool is removed before detection."""
    if no_round:
        nan = np.full(P["n"], np.nan)
        P = dict(P, rup=nan, rdn=nan)
    return pb.p1_signals(P, BASE_RULE)


def signals(P, var):
    """-> signals for one variant, oldest decision first. Each: i_dec (the decision bar), side, stop, level, extreme,
    pool, i_reclaim, bias; a retest signal also carries limit (price) and limit_bars."""
    n, h, l, c, atr = P["n"], P["h"], P["l"], P["c"], P["atr"]
    bias = pb.htf_bias(P) if var["trend"] else None
    out = []
    for s in base_signals(P, var["no_round"]):
        r, side = s["i_dec"], s["side"]
        d, ext = r, s["extreme"]
        if var["entry"] == "confirm":
            d = r + 1
            if d >= n:                                                   # the confirmation bar has not closed yet
                continue
            if not (side * (s["level"] - c[d]) > 0):                     # must close on the reclaimed side again
                continue
            ext = max(ext, float(h[d])) if side < 0 else min(ext, float(l[d]))
        b = int(bias[d]) if bias is not None else None
        if b is not None and ((side < 0 and b > 0) or (side > 0 and b < 0)):
            continue                                                     # never fade a sweep into the trend's strong side
        stop = ext - side * var["pad"] * float(atr[d])
        if not np.isfinite(stop):
            continue
        sig = dict(s, i_dec=int(d), i_reclaim=int(r), extreme=float(ext), stop=float(stop), bias=b)
        sig.pop("t1_cands", None)
        sig.pop("t2_cand", None)
        if var["entry"] == "retest":
            sig["limit"], sig["limit_bars"] = float(s["level"]), RETEST_BARS
        out.append(sig)
    out.sort(key=lambda x: x["i_dec"])
    return out


def simulate(P, sigs, exit_name, hold, fee):
    """Trade the signals one at a time. -> trade dicts (status WAITING / OPEN / CLOSED), playbook.simulate's fields
    plus gross_r. With exit E1 and next-open entries this reproduces playbook.simulate(..., "fixed", ...) exactly."""
    n, o, h, l, c, ms = P["n"], P["o"], P["h"], P["l"], P["c"], P["ms"]
    legs_def, be = EXITS[exit_name]["legs"], EXITS[exit_name]["be"]
    last_name = "T2" if len(legs_def) > 1 else "T1"
    trades, busy = [], -1
    for sig in sigs:
        r = sig["i_dec"]
        if r <= busy:
            continue
        side, stop = sig["side"], float(sig["stop"])
        t = dict(sig, setup_ms=int(ms[r]) + pb.BAR_MS)
        intrabar = False
        if "limit" in sig:
            lv, nb = float(sig["limit"]), int(sig["limit_bars"])
            e = entry = None
            for j in range(r + 1, min(r + 1 + nb, n)):
                if side * (o[j] - stop) <= 0:                            # opened beyond the stop: the order is cancelled
                    break
                if side * (lv - o[j]) >= 0 and o[j] != lv:               # opened beyond the level (not the stop): fill at the open
                    e, entry = j, float(o[j])
                    break
                through = (h[j] > lv) if side < 0 else (l[j] < lv)
                if through:
                    e, entry, intrabar = j, lv, True
                    break
            if e is None:
                cancelled = any(side * (o[j] - stop) <= 0 for j in range(r + 1, min(r + 1 + nb, n)))
                if r + nb >= n and not cancelled:                        # the order is still live at the last close
                    risk = abs(lv - stop)
                    tg = [lv + side * m * risk for _, m in legs_def]
                    t.update(status="WAITING", entry=None, est_entry=lv, risk=risk, target_1=tg[0],
                             target_2=tg[-1] if len(tg) > 1 else None, t1_name="%gR" % legs_def[0][1],
                             t2_name=("%gR" % legs_def[-1][1]) if len(tg) > 1 else "-")
                    trades.append(t)
                    busy = n
                else:
                    busy = r + nb - 1
                continue
        else:
            e = r + 1
            if e >= n:                                                   # entry is at the next open
                est = float(c[r])
                risk = abs(est - stop)
                tg = [est + side * m * risk for _, m in legs_def]
                t.update(status="WAITING", entry=None, est_entry=est, risk=risk, target_1=tg[0],
                         target_2=tg[-1] if len(tg) > 1 else None, t1_name="%gR" % legs_def[0][1],
                         t2_name=("%gR" % legs_def[-1][1]) if len(tg) > 1 else "-")
                trades.append(t)
                busy = n
                continue
            entry = float(o[e])
            if side * (entry - stop) <= 0:                               # the open gapped beyond the stop: no trade
                continue
        risk = abs(entry - stop)
        tgts = [entry + side * m * risk for _, m in legs_def]
        legs, cur_stop, k, j_out, why = [], stop, 0, None, None
        for j in range(e, min(e + hold, n)):
            rem = 1.0 - sum(f for f, _ in legs)
            adverse = l[j] if side > 0 else h[j]
            fav = h[j] if side > 0 else l[j]
            if not (j == e and intrabar) and side * (o[j] - cur_stop) <= 0:
                legs.append((rem, float(o[j])))
                j_out, why = j, "STOP"
                break
            if side * (adverse - cur_stop) <= 0:                         # stop first when both are in one bar
                legs.append((rem, cur_stop))
                j_out, why = j, "STOP"
                break
            if j == e and intrabar:                                      # filled inside this bar: targets from the next
                continue
            hit = False
            while k < len(tgts) and side * (fav - tgts[k]) >= 0:
                legs.append((legs_def[k][0], float(o[j]) if side * (o[j] - tgts[k]) >= 0 else tgts[k]))
                k += 1
                hit = True
            if k == len(tgts):
                j_out, why = j, last_name
                break
            if hit and be:
                cur_stop = entry                                         # break-even from the next bar
        t.update(entry_ms=int(ms[e]), entry=entry, stop=stop, risk=risk, t1_name="%gR" % legs_def[0][1],
                 target_1=tgts[0], t2_name=("%gR" % legs_def[-1][1]) if len(tgts) > 1 else "-",
                 target_2=tgts[-1] if len(tgts) > 1 else None, t1_hit=k > 0, entry_bar=int(e))
        if why is None and e + hold < n:
            rem = 1.0 - sum(f for f, _ in legs)
            legs.append((rem, float(o[e + hold])))
            j_out, why = e + hold, "TIME"
        if why is None:                                                  # still open: marked at the last close
            rem = 1.0 - sum(f for f, _ in legs)
            mark = legs + [(rem, float(c[-1]))]
            mo = pb._money(mark, entry, risk, side, fee)
            t.update(status="OPEN", mark=float(c[-1]), why_out="OPEN", exit=None, exit_ms=None, **mo)
            busy = n
        else:
            frac = sum(f for f, _ in legs)
            px = sum(f * p for f, p in legs) / frac
            mo = pb._money(legs, entry, risk, side, fee)
            t.update(status="CLOSED", exit=px, exit_ms=int(ms[j_out]), why_out=why, exit_bar=int(j_out), **mo)
            busy = j_out - 1                                             # flat by the close of the exit bar
        t["gross_r"] = t["gross_usd"] / (pb.STAKE * risk / entry)
        trades.append(t)
    return trades


def run(P, var, fee=None):
    fee = pb.fee_side(P["asset"]) if fee is None else fee
    return simulate(P, signals(P, var), var["exit"], var["hold"], fee)
