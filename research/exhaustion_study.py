# -*- coding: utf-8 -*-
"""H49 the EXHAUSTION FADE: weak new extremes on a day that has already used its daily ATR. PAPER RESEARCH ONLY.

Registered before any code or outcome: research/HYPOTHESES.md H49 (16 Nov 2026, 06:25 UTC). In short:
  * event = the first 15m close per UTC day per direction beyond today's running high/low ("run") or a fresh close
    beyond the prior UTC day's high/low ("pday"), on a day that has already used >= U x its daily ATR (U 1.0 / 1.3),
    on a WEAK bar (true range < K x ATR15 of the bar before; K 1.0 / 0.7), optionally confirmed by the next bar
    closing back; 8 variants X1-X8, every one counted;
  * fade it: entry next 15m open against the push, stop beyond the day's extreme + 0.25 ATR15 or + 0.25 daily ATR,
    target 0.5 daily ATR or the day's midpoint, out at the close of the UTC day's last bar, own fee a side, one
    position per market;
  * primary statistic: -0.5 daily ATR (the fade's way) before +0.5 daily ATR against, within the day; 72 h secondary;
  * 8 variants x 6 scopes = 48 tests per half, Bonferroni 1.04e-3; pass bar in HYPOTHESES.md H49;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market. Reads data/*.csv through data.load only; writes research/out/exhaustion/.

    py -3 research/exhaustion_study.py            (run, write study.json + study.md, then print the live scan)
    py -3 research/exhaustion_study.py --report   (rewrite study.md from study.json)
    py -3 research/exhaustion_study.py --scan     (the live scan only: latest closed bars, paper / untested)
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, playbook as pb  # noqa: E402
from engine15.sources import adr  # noqa: E402
from engine15.rl import resources  # noqa: E402

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402  (same lock, same log format)
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402
import confluence_study as cs  # noqa: E402
import session_break_study as sb  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 06:25 UTC"
ASSETS = rb.ASSETS
MGROUPS = db.GROUPS
GROUP_OF = db.GROUP_OF
SCOPES = ["pooled"] + list(MGROUPS)
OUT = os.path.join(ROOT, "research", "out", "exhaustion")
NEED_MB = 1500
BAR_MS, DAY_MS = pb.BAR_MS, 86400000
X = 0.5                      # +/- 0.5 daily ATR, the symmetric outcome
PAD_A15, PAD_D = 0.25, 0.25  # stop pad beyond the day's extreme
MID_FLOOR = 0.25             # a midpoint target nearer than 0.25 D -> entry -/+ 0.25 D

VARIANTS = {
    "X1": {"level": "run", "U": 1.0, "K": 1.0, "confirm": False, "stop": "a15", "target": "half"},
    "X2": {"level": "run", "U": 1.3, "K": 1.0, "confirm": False, "stop": "a15", "target": "half"},
    "X3": {"level": "run", "U": 1.0, "K": 0.7, "confirm": False, "stop": "a15", "target": "half"},
    "X4": {"level": "run", "U": 1.0, "K": 1.0, "confirm": True, "stop": "a15", "target": "half"},
    "X5": {"level": "pday", "U": 1.0, "K": 1.0, "confirm": False, "stop": "a15", "target": "half"},
    "X6": {"level": "pday", "U": 1.0, "K": 1.0, "confirm": True, "stop": "a15", "target": "half"},
    "X7": {"level": "run", "U": 1.0, "K": 1.0, "confirm": False, "stop": "dATR", "target": "mid"},
    "X8": {"level": "run", "U": 1.3, "K": 1.0, "confirm": True, "stop": "dATR", "target": "mid"},
}
ORDER = list(VARIANTS)
N_TESTS = len(VARIANTS) * len(SCOPES)        # 48
ALPHA = 0.05 / N_TESTS
PASS_HIT, MIN_RESOLVED, PASS_PF, PASS_MARKETS = 55.0, 200, 1.1, 5


def vdesc(v):
    var = VARIANTS[v] if isinstance(v, str) else v
    lv = {"run": "close beyond today's running high/low", "pday": "fresh close beyond the prior UTC day's high/low"}[var["level"]]
    cf = ", next bar closes back (%s)" % ("below / above the push close" if var["level"] == "run" else "inside the level") \
        if var["confirm"] else ""
    st = "stop day extreme + 0.25 ATR15" if var["stop"] == "a15" else "stop day extreme + 0.25 daily ATR"
    tg = "target 0.5 daily ATR" if var["target"] == "half" else "target the day's midpoint (floor 0.25 dATR)"
    return "%s, day used >= %d%% of daily ATR, push bar TR < %.1f x ATR15%s; fade: %s, %s, out at the day's end" % (
        lv, round(100 * var["U"]), var["K"], cf, st, tg)


# ---------------------------------------------------------------- the event (truncation-tested)
def _prev_same_day(x, day):
    """x of the previous bar if it is in the same UTC day, else NaN."""
    out = np.full(len(x), np.nan)
    if len(x) > 1:
        same = day[1:] == day[:-1]
        out[1:] = np.where(same, x[:-1], np.nan)
    return out


def qualifying(R, var):
    """-> (up, dn) bool arrays: bar i is a weak push beyond the level on an exhausted day (known at bar i's close)."""
    c, day = R["c"], R["ms"] // DAY_MS
    with np.errstate(invalid="ignore"):
        if var["level"] == "run":
            hi = _prev_same_day(R["day_high"], day)          # today's highest high BEFORE bar i
            lo = _prev_same_day(R["day_low"], day)
            up = np.nan_to_num(c > hi).astype(bool) & np.isfinite(hi)
            dn = np.nan_to_num(c < lo).astype(bool) & np.isfinite(lo)
        else:
            cp = adr._sh(c)                                  # the previous bar's close
            pdh, pdl = R["pdh"], R["pdl"]
            up = np.nan_to_num((c > pdh) & (cp <= pdh)).astype(bool)
            dn = np.nan_to_num((c < pdl) & (cp >= pdl)).astype(bool)
        D, A = R["datr"], R["atr15"]
        ok = np.isfinite(D) & (D > 0) & np.isfinite(A) & (A > 0)
        ok &= np.nan_to_num(R["used"] >= var["U"]).astype(bool)
        ok &= np.nan_to_num(R["bar_x"] < var["K"]).astype(bool) & np.isfinite(R["bar_x"])
    return up & ok, dn & ok


def decision_dirs(R, var):
    """-> (dirs, push): dirs[j] = +1 / -1 if bar j is the decision bar of an up / down event, push[j] = the push bar."""
    n, c, day = R["n"], R["c"], R["ms"] // DAY_MS
    up, dn = qualifying(R, var)
    push = np.arange(n)
    if var["confirm"]:
        cu, cd = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
        if n > 1:
            same = day[1:] == day[:-1]
            if var["level"] == "run":
                back_up, back_dn = c[1:] < c[:-1], c[1:] > c[:-1]
            else:
                with np.errstate(invalid="ignore"):
                    back_up = np.nan_to_num(c[1:] < R["pdh"][:-1]).astype(bool)
                    back_dn = np.nan_to_num(c[1:] > R["pdl"][:-1]).astype(bool)
            cu[1:] = up[:-1] & same & back_up
            cd[1:] = dn[:-1] & same & back_dn
        up, dn = cu, cd
        push = np.arange(n) - 1
    fu = up & (pd.Series(up.astype(int)).groupby(day).cumsum().values == 1)
    fd = dn & (pd.Series(dn.astype(int)).groupby(day).cumsum().values == 1)
    return np.where(fu, 1, np.where(fd, -1, 0)).astype(int), push


def events(R, var):
    """-> list of event dicts (oldest first); everything known at the close of the decision bar i."""
    dirs, push = decision_dirs(R, var)
    out = []
    for i in np.flatnonzero(dirs != 0):
        s = int(dirs[i])
        p = int(push[i])
        dh, dl = float(R["day_high"][i]), float(R["day_low"][i])
        out.append({"i": int(i), "push": p, "side": s, "datr": float(R["datr"][i]), "used": float(R["used"][p]),
                    "bar_x": float(R["bar_x"][p]), "ext": dh if s > 0 else dl, "mid": 0.5 * (dh + dl),
                    "a15": float(R["atr15"][i]), "push_close": float(R["c"][p])})
    return out


def _r9(x):
    return None if x is None or x != x else round(float(x), 9)


def event_key(evs):
    return [(e["i"], e["push"], e["side"], _r9(e["datr"]), _r9(e["used"]), _r9(e["ext"]), _r9(e["mid"]), _r9(e["a15"]))
            for e in evs]


# ---------------------------------------------------------------- outcome and the trade
def day_end(R, i):
    """Index one past the last bar of bar i's UTC day."""
    day = R["ms"] // DAY_MS
    return int(np.searchsorted(day, day[i], side="right"))


def plan(ev, entry, var):
    """-> (stop, target) of the fade (side -s) for a fill at `entry`."""
    s, D = ev["side"], ev["datr"]
    pad = PAD_A15 * ev["a15"] if var["stop"] == "a15" else PAD_D * D
    stop = ev["ext"] + s * pad
    if var["target"] == "half":
        tgt = entry - s * X * D
    else:
        tgt = ev["mid"]
        if -s * (tgt - entry) < MID_FLOOR * D:
            tgt = entry - s * MID_FLOOR * D
    return stop, tgt


def trade(R, ev, var, fee):
    """The registered fade for one event -> dict (or None: no same-day entry, or the entry opens beyond the stop).
    Stop first inside a bar; an open beyond the stop or the target fills there; out at the close of the day's last bar."""
    n, o, h, l, c, ms = R["n"], R["o"], R["h"], R["l"], R["c"], R["ms"]
    day = ms // DAY_MS
    i = ev["i"]
    e = i + 1
    if e >= n or day[e] != day[i]:
        return None
    f = -ev["side"]
    entry = float(o[e])
    stop, tgt = plan(ev, entry, var)
    if f * (entry - stop) <= 0:
        return {"skip": "gap beyond stop"}
    risk = abs(entry - stop)
    x = day_end(R, i)
    px, j_out, why = None, None, None
    for j in range(e, min(x, n)):
        adverse = l[j] if f > 0 else h[j]
        fav = h[j] if f > 0 else l[j]
        if f * (o[j] - stop) <= 0:
            px, j_out, why = float(o[j]), j, "STOP"
            break
        if f * (adverse - stop) <= 0:
            px, j_out, why = stop, j, "STOP"
            break
        if f * (o[j] - tgt) >= 0:
            px, j_out, why = float(o[j]), j, "TARGET"
            break
        if f * (fav - tgt) >= 0:
            px, j_out, why = tgt, j, "TARGET"
            break
    t = {"entry_ms": int(ms[e]), "entry": entry, "stop": float(stop), "target": float(tgt), "risk": risk, "side": f}
    if why is None:
        if x < n:
            px, j_out, why = float(c[x - 1]), x - 1, "TIME"
            t.update(exit=px, exit_ms=int(ms[x - 1]) + BAR_MS, why_out=why, busy=x - 1)
        else:
            t.update(why_out="OPEN", exit=None, exit_ms=None, busy=10 ** 12)
            return t
    else:
        t.update(exit=px, exit_ms=int(ms[j_out]), why_out=why, busy=j_out - 1)
    m = db._money(px, entry, risk, f, fee)
    m["gross_r"] = m["gross_usd"] / (pb.STAKE * risk / entry)
    t.update(m)
    t["t1_hit"] = why == "TARGET"
    return t


def trades_of(evs):
    """One position per market at a time over the variant's events (time order); H45/H46's rule."""
    out, busy = [], -1
    for ev in evs:
        t = ev.get("trade")
        if ev["i"] <= busy or not t or "skip" in t:
            continue
        if t["why_out"] == "OPEN":
            busy = 10 ** 12
            continue
        out.append(dict(t, asset=ev["asset"], half=ev["half"]))
        busy = t["busy"]
    return out


# ---------------------------------------------------------------- per market
def truncation_check(df, cuts):
    full_R = adr.readings(df, box=db.BOX)
    full = dict((v, event_key(events(full_R, VARIANTS[v]))) for v in ORDER)
    bad, checked = 0, 0
    for cut in cuts:
        part_R = adr.readings(df.iloc[:cut], box=db.BOX)
        for v in ORDER:
            want = [x for x in full[v] if x[0] < cut]
            checked += len(want)
            if event_key(events(part_R, VARIANTS[v])) != want:
                bad += 1
    return {"cuts": len(cuts), "events_checked": checked, "mismatched_runs": bad}


def run_market(asset):
    df = rb.load_dev(asset)
    fee = pb.fee_side(asset)
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    R = adr.readings(df, box=db.BOX)
    res = {"asset": asset, "group": GROUP_OF[asset], "fee_side": fee, "bars": int(len(df)),
           "first_bar": str(df.index[0]), "last_bar": str(df.index[-1]), "dropped": {}, "skipped_gap": {}}
    E = {}
    for v in ORDER:
        var = VARIANTS[v]
        evs, dropped, gaps = [], 0, 0
        for ev in events(R, var):
            i = ev["i"]
            if i + 1 >= R["n"] or (R["ms"][i + 1] // DAY_MS) != (R["ms"][i] // DAY_MS):
                if R["ms"][i] + BAR_MS >= start_ms:
                    dropped += 1
                continue
            if R["ms"][i + 1] < start_ms:
                continue
            D = ev["datr"]
            od = sb.outcome_window(R, i, -ev["side"], D, day_end(R, i), X, "close")
            o3 = cs.outcome(R, i, -ev["side"], D)
            t = trade(R, ev, var, fee)
            if t and "skip" in t:
                gaps += 1
            ev.update(asset=asset, group=GROUP_OF[asset], entry_ms=int(R["ms"][i + 1]),
                      half="first" if R["ms"][i + 1] < split_ms else "second",
                      hit=od["hit"], ambiguous=od["ambiguous"], hit72=o3["hit"] if o3 else None, trade=t,
                      utc_hour=int((R["ms"][i] + BAR_MS) % DAY_MS // 3600000))
            evs.append(ev)
        E[v] = evs
        res["dropped"][v] = dropped
        res["skipped_gap"][v] = gaps
    n = len(df)
    res["truncation"] = truncation_check(df, [int(n * 0.6) + 7, n - 40])
    return res, E


# ---------------------------------------------------------------- aggregation and the pass bar
def cell(evs, key="hit"):
    res = [e for e in evs if e.get(key) is not None]
    k = int(sum(e[key] for e in res))
    m = len(res)
    return {"events": len(evs), "resolved": m, "hits": k, "unresolved": len(evs) - m,
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": cs.binom_p(k, m) if m else None}


def halves(evs, key="hit"):
    return {"first": cell([e for e in evs if e["half"] == "first"], key),
            "second": cell([e for e in evs if e["half"] == "second"], key), "all": cell(evs, key)}


def tmetrics(tr):
    return db.metrics(tr) if tr else {"trades": 0, "net_usd": 0.0}


def months_of(half):
    a, b = (START, SPLIT) if half == "first" else (SPLIT, SEAL)
    return (ms_of(b) - ms_of(a)) / (DAY_MS * 30.4375)


def in_scope(asset, scope):
    return scope == "pooled" or GROUP_OF[asset] == scope or asset == scope


def aggregate(E):
    A, J = {}, {"passed": [], "rows": {}}
    for v in ORDER:
        allev = sorted([e for a in ASSETS for e in E[a][v]], key=lambda e: (e["entry_ms"], e["asset"]))
        trades = []
        for a in ASSETS:
            trades += trades_of(E[a][v])
        node = {"scopes": {}, "markets": {}, "trades": {}, "freq": {}}
        for sc in SCOPES:
            sev = [e for e in allev if in_scope(e["asset"], sc)]
            str_ = [t for t in trades if in_scope(t["asset"], sc)]
            node["scopes"][sc] = {"day": halves(sev), "h72": halves(sev, "hit72"),
                                  "trade": {"first": tmetrics([t for t in str_ if t["half"] == "first"]),
                                            "second": tmetrics([t for t in str_ if t["half"] == "second"])}}
        for a in ASSETS:
            sev = [e for e in allev if e["asset"] == a]
            str_ = [t for t in trades if t["asset"] == a]
            node["markets"][a] = {"day": halves(sev), "h72": halves(sev, "hit72"),
                                  "trade": {"first": tmetrics([t for t in str_ if t["half"] == "first"]),
                                            "second": tmetrics([t for t in str_ if t["half"] == "second"])}}
        for hf in ("first", "second"):
            node["freq"][hf] = {"events_month": round(sum(1 for e in allev if e["half"] == hf) / months_of(hf), 1),
                                "trades_month": round(sum(1 for t in trades if t["half"] == hf) / months_of(hf), 1)}
        # descriptive: by direction of the push (pooled)
        node["by_side"] = dict(("up push (fade short)" if s > 0 else "down push (fade long)",
                                halves([e for e in allev if e["side"] == s])) for s in (1, -1))
        node["median_used"] = round(float(np.median([e["used"] for e in allev])), 3) if allev else None
        node["median_risk_datr"] = round(float(np.median([t["risk"] / e["datr"] for e in allev
                                                          for t in [e.get("trade")] if t and "risk" in t])), 3) if allev else None
        P = node["scopes"]["pooled"]
        d1, d2 = P["day"]["first"], P["day"]["second"]
        t2 = P["trade"]["second"]
        good_mk = [a for a in ASSETS if node["markets"][a]["trade"]["second"]["trades"]
                   and node["markets"][a]["trade"]["second"]["net_usd"] > 0
                   and (node["markets"][a]["trade"]["second"].get("pf") or 0) >= PASS_PF]
        conds = {
            "hit_both": bool(d1["hit_pct"] is not None and d2["hit_pct"] is not None and d1["hit_pct"] >= PASS_HIT and d2["hit_pct"] >= PASS_HIT),
            "n_both": bool(d1["resolved"] >= MIN_RESOLVED and d2["resolved"] >= MIN_RESOLVED),
            "p_both": bool(d1["p"] is not None and d2["p"] is not None and d1["p"] < ALPHA and d2["p"] < ALPHA),
            "trade_pooled": bool(t2["trades"] and t2["net_usd"] > 0 and (t2.get("pf") or 0) >= PASS_PF),
            "markets": len(good_mk), "markets_list": good_mk, "markets_ok": len(good_mk) >= PASS_MARKETS}
        conds["pass"] = bool(conds["hit_both"] and conds["n_both"] and conds["p_both"] and conds["trade_pooled"] and conds["markets_ok"])
        lo = None
        if d1["hit_pct"] is not None and d2["hit_pct"] is not None:
            lo = min(d1["hit_pct"], d2["hit_pct"])
        conds["min_hit"] = lo
        node["bar"] = conds
        # Bonferroni count over all 48 cells, per half
        node["bonf_cells"] = [sc for sc in SCOPES if all(
            node["scopes"][sc]["day"][hf]["p"] is not None and node["scopes"][sc]["day"][hf]["p"] < ALPHA for hf in ("first", "second"))]
        A[v] = node
        if conds["pass"]:
            J["passed"].append(v)
    pool = J["passed"] or [v for v in ORDER if A[v]["bar"]["n_both"] and A[v]["bar"]["min_hit"] is not None]
    J["chosen"] = sorted(pool, key=lambda v: (-A[v]["bar"]["min_hit"], int(v[1:])))[0] if pool else None
    return A, J


# ---------------------------------------------------------------- report
def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | |"
    return "%.1f%% | %d (%d unres.) | %s" % (c["hit_pct"], c["resolved"], c["unresolved"], _p(c["p"]))


def _p(p):
    if p is None:
        return ""
    return "%.2e" % p if p < 1e-3 else "%.3f" % p


def _t(m):
    if not m or not m.get("trades"):
        return "0 | | | | | | "
    return "%d | %.1f%% | %+.3f | %+.3f | %s | %+.4f%% | %s" % (
        m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"], "n/a" if m.get("pf") is None else "%.2f" % m["pf"],
        m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


THDR = "trades | won | R before | R after | PF | per trade (% stake) | net $"


def report(S):
    A, J, res = S["agg"], S["judge"], S["results"]
    L = ["# H49: the exhaustion fade", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H49) before any code or outcome. Development data "
         "only (rows before %s 00:00 UTC; the holdout was not read). Events with entry from %s; first half before %s. "
         "Written %s." % (REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Event = the first qualifying 15m bar per UTC day per direction: a close beyond today's running high/low (or a "
         "fresh close beyond the prior day's high/low) on a day that has already used >= U x its daily ATR (14, last closed "
         "day), on a bar whose true range < K x ATR15 (the weak push). Fade hit = -0.5 daily ATR in the fade's favour "
         "before +0.5 daily ATR against, from the next open, within the UTC day (a bar touching both = miss; neither = "
         "unresolved, excluded). Chance ~50%%. p = exact two-sided binomial against 50%%. Tests: %d variants x %d scopes = "
         "**%d** per half; Bonferroni p < %.2e." % (len(ORDER), len(SCOPES), S["n_tests"], S["alpha"]), ""]
    passed = J["passed"]
    L += ["## Verdict: %s" % (("PASS: " + ", ".join(passed)) if passed else "NO PASS"), ""]
    ch = J.get("chosen")
    if ch:
        b = A[ch]["bar"]
        P = A[ch]["scopes"]["pooled"]
        L += ["%s variant: **%s** (%s)." % ("Passing" if passed else "Best by the lower of the two halves' pooled hit rate (reported, not passed)",
                                            ch, vdesc(ch)), "",
              "Bar for %s: hit >= 55%% both halves **%s** (%.1f%% / %.1f%%); >= 200 resolved both halves **%s** (%d / %d); "
              "p < %.2e both halves **%s** (%s / %s); second-half trade pooled net > 0 and PF >= 1.1 **%s** (net %s, PF %s); "
              ">= 5 of 8 markets net > 0 with PF >= 1.1 **%s** (%d: %s)." % (
                  ch, "YES" if b["hit_both"] else "NO", P["day"]["first"]["hit_pct"] or 0, P["day"]["second"]["hit_pct"] or 0,
                  "YES" if b["n_both"] else "NO", P["day"]["first"]["resolved"], P["day"]["second"]["resolved"], S["alpha"],
                  "YES" if b["p_both"] else "NO", _p(P["day"]["first"]["p"]), _p(P["day"]["second"]["p"]),
                  "YES" if b["trade_pooled"] else "NO", "{:+,.0f}".format(P["trade"]["second"]["net_usd"]),
                  P["trade"]["second"].get("pf"), "YES" if b["markets_ok"] else "NO", b["markets"],
                  ", ".join(b["markets_list"]) or "none"), ""]
    nb = sum(len(A[v]["bonf_cells"]) for v in ORDER)
    L += ["Cells (variant x scope) whose p passes Bonferroni in BOTH halves (either side of 50%%): %d of %d%s." % (
        nb, S["n_tests"], (": " + "; ".join("%s %s" % (v, ", ".join(A[v]["bonf_cells"])) for v in ORDER if A[v]["bonf_cells"])) if nb else ""), ""]
    L += ["## The variants", "", "| id | rule |", "|---|---|"]
    for v in ORDER:
        L.append("| %s | %s |" % (v, vdesc(v)))
    L += ["", "## Pooled fade hit rates (primary: within the day; secondary: 72 h)", "",
          "| id | first: hit | resolved | p | second: hit | resolved | p | 72 h first | 72 h second | events / month 1st / 2nd | dropped (no same-day entry) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        P = A[v]["scopes"]["pooled"]
        drop = sum(r["dropped"][v] for r in res.values())
        L.append("| %s | %s | %s | %.1f%% (%d) / %.1f%% (%d) | %.1f / %.1f | %d |" % (
            v, _h(P["day"]["first"]), _h(P["day"]["second"]),
            P["h72"]["first"]["hit_pct"] or 0, P["h72"]["first"]["resolved"],
            P["h72"]["second"]["hit_pct"] or 0, P["h72"]["second"]["resolved"],
            A[v]["freq"]["first"]["events_month"], A[v]["freq"]["second"]["events_month"], drop))
    L += ["", "## The registered trade, pooled (after each market's own fee a side)", "",
          "| id | half | " + THDR + " | trades / month | median stop (dATR) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        for hf in ("first", "second"):
            L.append("| %s | %s | %s | %.1f | %s |" % (v if hf == "first" else "", hf, _t(A[v]["scopes"]["pooled"]["trade"][hf]),
                                                      A[v]["freq"][hf]["trades_month"], A[v]["median_risk_datr"] if hf == "first" else ""))
    L += ["", "## Pass bar, every variant", "",
          "| id | hit >= 55% both | >= 200 resolved both | p < alpha both | trade 2nd half pooled net > 0 & PF >= 1.1 | markets net > 0 & PF >= 1.1 (2nd half) | PASS |",
          "|---|---|---|---|---|---|---|"]
    for v in ORDER:
        b = A[v]["bar"]
        yn = lambda x: "yes" if x else "no"  # noqa: E731
        L.append("| %s | %s | %s | %s | %s | %d (%s) | **%s** |" % (v, yn(b["hit_both"]), yn(b["n_both"]), yn(b["p_both"]),
                                                                  yn(b["trade_pooled"]), b["markets"], ", ".join(b["markets_list"]) or "-",
                                                                  "PASS" if b["pass"] else "no"))
    L += ["", "## Fade hit rate within the day, per market group (tests) and per market (descriptive)", "",
          "| id | scope | first: hit | resolved | p | second: hit | resolved | p |", "|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        first = True
        for sc in SCOPES[1:]:
            c = A[v]["scopes"][sc]["day"]
            L.append("| %s | %s | %s | %s |" % (v if first else "", sc, _h(c["first"]), _h(c["second"])))
            first = False
        for a in ASSETS:
            c = A[v]["markets"][a]["day"]
            L.append("| | %s | %s | %s |" % (a, _h(c["first"]), _h(c["second"])))
    L += ["", "## The registered trade per market group and per market", "",
          "| id | scope | half | " + THDR + " |", "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        first = True
        for sc in SCOPES[1:] + list(ASSETS):
            node = A[v]["scopes"][sc] if sc in A[v]["scopes"] else A[v]["markets"][sc]
            for hf in ("first", "second"):
                L.append("| %s | %s | %s | %s |" % (v if first else "", sc if hf == "first" else "", hf, _t(node["trade"][hf])))
                first = False
    L += ["", "## Descriptive: by the push's direction (pooled, within the day)", "",
          "| id | push | first: hit | resolved | p | second: hit | resolved | p |", "|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        for k, c in A[v]["by_side"].items():
            L.append("| %s | %s | %s | %s |" % (v, k, _h(c["first"]), _h(c["second"])))
    L += ["", "## Checks", "",
          "| market | bars | first bar | last bar | fee a side | truncation cuts | events compared | mismatched runs | entries skipped (gap beyond stop, all variants) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a, r in res.items():
        tc = r["truncation"]
        L.append("| %s | %d | %s | %s | %.3f%% | %d | %d | %d | %d |" % (
            a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], tc["cuts"], tc["events_checked"],
            tc["mismatched_runs"], sum(r["skipped_gap"].values())))
    L += ["", "## Overlap with earlier tests and what the engine reads", "", OVERLAP, ""]
    if S.get("scan_lines"):
        L += ["## Live scan at write time (PAPER / UNTESTED)", "", "```"] + S["scan_lines"] + ["```", ""]
    return "\n".join(L)


OVERLAP = (
    "- H44 V7 (exhausted contrast) traded WITH 24-bar breaks on a momentum bar on exhausted days; H49 fades the weak "
    "(no momentum) pushes. H44's reference row (24-bar breaks without momentum on exhausted days drifted back) is where "
    "the idea came from, so H49 is not independent of H44's data.\n"
    "- H7 (breakout trap, `playbook.py` p2) faded failed first closes beyond the 48-bar / prior-day / swing levels with no "
    "daily-budget condition; it lost about its costs.\n"
    "- `cs_used_x` (card 'Candle size and realistic targets') and `adr_used` (reading-only, not wired) already read the "
    "share of the day's range used; `adr_bar` reads the bar's size in ATR15. H49's event is the combination of the two "
    "at a new extreme.")


# ---------------------------------------------------------------- live scan (paper)
def _px(x):
    if x is None or x != x:
        return "n/a"
    return ("%.2f" % x) if abs(x) >= 100 else ("%.4f" % x)


def scan(S=None, now_ms=None):
    passed = (S or {}).get("judge", {}).get("passed", [])
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    lines = ["H49 live exhaustion-fade scan, %s (PAPER; %s)" % (
        pd.Timestamp(now_ms, unit="ms", tz="UTC").strftime("%d %b %Y %H:%M UTC"),
        ("passed H49's history bar: " + ", ".join(passed)) if passed else "UNTESTED / no variant passed H49's history bar")]
    rows = []
    for a in ASSETS:
        try:
            df = data.load(a)
        except Exception as ex:                       # noqa: BLE001
            lines.append("  %-8s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=60)]
        df = df[data.to_ms(df.index) + BAR_MS <= now_ms]
        R = adr.readings(df, box=db.BOX)
        n = R["n"]
        if not n:
            continue
        i = n - 1
        day = R["ms"] // DAY_MS
        last_close = pd.Timestamp(int(R["ms"][i]) + BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - int(R["ms"][i]) - BAR_MS) / 3600000.0
        note = (" (%.0f h old: market shut; last session shown)" % age_h) if age_h > 6 else (
            " (%.1f h old)" % age_h if age_h > 0.5 else "")
        lines.append("  %-8s last close %s%s; daily ATR %s; day used %s of it (high %s / low %s)" % (
            a, last_close.strftime("%a %d %b %H:%M UTC"), note, _px(R["datr"][i]),
            "n/a" if R["used"][i] != R["used"][i] else "%.0f%%" % (100 * R["used"][i]), _px(R["day_high"][i]), _px(R["day_low"][i])))
        found = []
        for v in ORDER:
            var = VARIANTS[v]
            for ev in events(R, var):
                j = ev["i"]
                if day[j] != day[i]:
                    continue
                s = ev["side"]
                when = pd.Timestamp(int(R["ms"][j]) + BAR_MS, unit="ms", tz="UTC").strftime("%H:%M")
                t = trade(R, ev, var, pb.fee_side(a)) if j + 1 < n else None
                if t is None and j + 1 >= n:
                    est = float(R["c"][j])
                    st, tg = plan(ev, est, var)
                    txt = "%s %s push at %s close (used %.0f%%, bar %.2f ATR15): fade %s at the next open (about %s), stop %s, target %s, WAITING" % (
                        v, "UP" if s > 0 else "DOWN", when, 100 * ev["used"], ev["bar_x"], "SHORT" if s > 0 else "LONG",
                        _px(est), _px(st), _px(tg))
                    status = "WAITING"
                elif t is None or "skip" in t:
                    txt = "%s %s push at %s close: no fill (%s)" % (v, "UP" if s > 0 else "DOWN", when,
                                                                  "no same-day entry" if t is None else t["skip"])
                    status = "NO FILL"
                else:
                    status = {"STOP": "stopped", "TARGET": "target hit", "TIME": "out at day end", "OPEN": "open"}[t["why_out"]]
                    txt = "%s %s push at %s close (used %.0f%%, bar %.2f ATR15): fade %s entry %s, stop %s, target %s: %s" % (
                        v, "UP" if s > 0 else "DOWN", when, 100 * ev["used"], ev["bar_x"], "SHORT" if s > 0 else "LONG",
                        _px(t["entry"]), _px(t["stop"]), _px(t["target"]), status)
                found.append(txt)
                rows.append({"asset": a, "variant": v, "side": s, "close_utc": when, "status": status})
        lines += ["      " + x for x in found] if found else ["      no exhaustion-fade event today"]
    lines.append("  (PAPER / UNTESTED unless marked passed; nothing is traded or wired)")
    return rows, lines


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H49 exhaustion study")
    results, E = {}, {}
    try:
        for a in ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a], E[a] = run_market(a)
            log("%s: done in %.0f s; events %s; truncation %s" % (
                a, time.time() - t0, dict((v, len(x)) for v, x in E[a].items()), results[a]["truncation"]))
    finally:
        release_lock()
    A, J = aggregate(E)
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC,
         "n_tests": N_TESTS, "alpha": ALPHA, "variants": dict((v, dict(VARIANTS[v], desc=vdesc(v))) for v in ORDER),
         "agg": A, "judge": J, "results": results}
    try:
        S["scan_lines"] = scan(S)[1]
    except Exception as ex:                           # noqa: BLE001
        S["scan_lines"] = ["scan failed: %s" % ex]
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("passed %s, chosen %s" % (J["passed"], J["chosen"]))
    return S


def load_study():
    with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    if "--report" in sys.argv:
        S = load_study()
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(S))
    elif "--scan" in sys.argv:
        try:
            S = load_study()
        except Exception:                             # noqa: BLE001
            S = None
        print("\n".join(scan(S)[1]))
    else:
        S = main()
        print("\n".join(S["scan_lines"]))
