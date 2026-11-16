# -*- coding: utf-8 -*-
"""H50 POST-NEWS DRIFT: does the first 15-60 minutes after a high-impact US release keep going? PAPER RESEARCH ONLY.

Registered before any code or number: research/hypotheses_pending/H50.md (16 Nov 2026, 09:48 UTC). In short:
  * releases: CPI, NFP, FOMC, PCE, advance GDP from engine15/calhistory.py (official dates, agency release times),
    rows at the same UTC minute = one release (type FOMC > CPI > NFP > PCE > GDP);
  * impulse I = (close of the k-th 15m bar from T - the close of the bar ending at T) / daily ATR, k = 1 or 4;
  * condition abs(I) >= 0.25 / 0.5 (k = 1) or 0.5 / 1.0 (k = 4) daily ATR; trade WITH (N1-N4) or FADE (F1-F4) at the
    next 15m open; outcome +0.5 D before -0.5 D within the rest of the UTC day (24 h secondary);
  * the trade = that bracket, out at the day's last close, own fee a side, one position per market per variant;
  * 8 variants x 2 outcomes = 16 tests per half, Bonferroni 3.13e-3; pass bar in H50.md;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

    python research/newsdrift_study.py            (run, write research/out/newsdrift/study.json + study.md)
    python research/newsdrift_study.py --report   (rewrite study.md from study.json)
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

from engine15 import calhistory, playbook as pb  # noqa: E402
from engine15.sources import adr  # noqa: E402

from liqhunt2_study import log, ms_of  # noqa: E402
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402
import confluence_study as cs  # noqa: E402
import session_break_study as sb  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 09:48 UTC"
ASSETS = rb.ASSETS
OUT = os.path.join(ROOT, "research", "out", "newsdrift")
BAR_MS, DAY_MS = pb.BAR_MS, 86400000
X = 0.5                                   # +/- 0.5 daily ATR bracket
KINDS = ("FOMC", "CPI", "NFP", "PCE", "GDP")          # priority order for the release type
KS = (1, 4)

VARIANTS = {
    "N1": {"k": 1, "thr": 0.25, "mode": "with"},
    "N2": {"k": 1, "thr": 0.5, "mode": "with"},
    "N3": {"k": 4, "thr": 0.5, "mode": "with"},
    "N4": {"k": 4, "thr": 1.0, "mode": "with"},
    "F1": {"k": 1, "thr": 0.25, "mode": "fade"},
    "F2": {"k": 1, "thr": 0.5, "mode": "fade"},
    "F3": {"k": 4, "thr": 0.5, "mode": "fade"},
    "F4": {"k": 4, "thr": 1.0, "mode": "fade"},
}
ORDER = list(VARIANTS)
N_TESTS = len(VARIANTS) * 2              # x (day, 24 h) per half = 16
ALPHA = 0.05 / N_TESTS
PASS_HIT, MIN_RESOLVED, PASS_MARKETS = 55.0, 100, 5
D_BUCKETS = [(0.0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, np.inf)]
A_BUCKETS = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, np.inf)]


def vdesc(v):
    var = VARIANTS[v] if isinstance(v, str) else v
    return "impulse over the first %d min, abs >= %.2f daily ATR, trade %s it at the next 15m open" % (
        15 * var["k"], var["thr"], "WITH" if var["mode"] == "with" else "AGAINST (fade)")


# ---------------------------------------------------------------- the releases
def load_releases(hist=None):
    """-> DataFrame, one row per release minute: ts_ms, type, kinds, titles, irregular, coreleased."""
    d = calhistory.load_history() if hist is None else hist.copy()
    d = d[(d["country"] == "USD") & (d["impact"] == "High")]
    d = d.assign(src=d["source"].astype(str))
    rows = []
    for ts, g in d.groupby("ts_ms"):
        main = g[g["kind"].isin(KINDS) & g["src"].str.startswith("official:")]
        if not len(main):
            continue
        kinds = [k for k in KINDS if k in set(main["kind"])]
        rows.append({"ts_ms": int(ts), "type": kinds[0], "kinds": "+".join(kinds),
                     "titles": "; ".join(main["title"].astype(str)),
                     "irregular": bool(main["src"].str.contains("irregular").any()),
                     "coreleased": "+".join(sorted(set(g["kind"]) - set(KINDS)))})
    return pd.DataFrame(rows, columns=["ts_ms", "type", "kinds", "titles", "irregular", "coreleased"])


# ---------------------------------------------------------------- the event (truncation-tested)
def release_events(R, rel, k):
    """R: adr.readings(bars). rel: load_releases() frame. -> list of dicts, one per release (oldest first):
    status 'ok' (impulse known at bar k's close, entry bar on file the same UTC day), 'closed' (a needed bar is not on
    file: market shut or a gap), 'pending' (entry bar not on file yet), 'flat' (I == 0) or 'no_atr'."""
    ms, c, n = R["ms"], R["c"], R["n"]
    out = []
    for r in rel.itertuples(index=False):
        T = int(r.ts_ms)
        ev = {"T": T, "type": r.type, "k": k, "status": "closed"}
        out.append(ev)
        i0 = int(np.searchsorted(ms, T - BAR_MS, side="left"))
        if i0 >= n or ms[i0] != T - BAR_MS:
            continue
        idec = i0 + k
        if idec >= n:
            ev["status"] = "pending"
            continue
        if ms[idec] != T + (k - 1) * BAR_MS:            # a bar between is missing
            continue
        e = idec + 1
        if e >= n:
            ev["status"] = "pending"
            continue
        if ms[e] != T + k * BAR_MS or ms[e] // DAY_MS != ms[idec] // DAY_MS:
            continue
        D = float(R["datr"][idec])
        if not (D == D and D > 0):
            ev["status"] = "no_atr"
            continue
        c0, ck = float(c[i0]), float(c[idec])
        imp = (ck - c0) / D
        a15 = float(R["atr15"][i0])
        ev.update(i0=i0, i=idec, e=e, c0=c0, ck=ck, D=D, imp=imp, side=int(np.sign(imp)),
                  a15=a15, imp_a15=(ck - c0) / a15 if a15 == a15 and a15 > 0 else None)
        ev["status"] = "ok" if imp != 0 else "flat"
    return out


def _r9(x):
    return None if x is None or x != x else round(float(x), 9)


def event_key(evs, cut=None):
    return [(e["T"], e["i0"], e["i"], e["side"], _r9(e["c0"]), _r9(e["ck"]), _r9(e["D"]), _r9(e["a15"]))
            for e in evs if e["status"] in ("ok", "flat") and (cut is None or e["e"] < cut)]


# ---------------------------------------------------------------- outcome and trade
def day_end(R, i):
    day = R["ms"] // DAY_MS
    return int(np.searchsorted(day, day[i], side="right"))


def end_24h(R, e):
    return int(np.searchsorted(R["ms"], R["ms"][e] + DAY_MS, side="left"))


def trade_of(R, od, side, D, fee):
    """The registered bracket trade from a day outcome dict -> dict or None (still open at the end of the file)."""
    if od is None or od.get("why") == "OPEN" or od.get("exit") is None:
        return None
    entry, px = od["entry"], float(od["exit"])
    risk = X * D
    m = db._money(px, entry, risk, side, fee)
    m["gross_r"] = m["gross_usd"] / (pb.STAKE * risk / entry)
    m.update(entry=entry, exit=px, risk=risk, side=side, why_out=od["why"], t1_hit=od["why"] == "TARGET",
             exit_ms=int(od["exit_ms"]), busy=int(od["busy"]), e=int(od["e"]))
    return m


def rows_of(R, evs, asset, fee, start_ms, split_ms):
    """Every 'ok' event with entry from START -> row dicts with WITH / FADE outcomes, trades and drift."""
    n, o, c, ms = R["n"], R["o"], R["c"], R["ms"]
    out = []
    for ev in evs:
        if ev["status"] != "ok" or ms[ev["e"]] < start_ms:
            continue
        i, e, s, D = ev["i"], ev["e"], ev["side"], ev["D"]
        xd, x24 = day_end(R, i), end_24h(R, e)
        en = float(o[e])
        row = {"asset": asset, "T": ev["T"], "type": ev["type"], "k": ev["k"], "imp": ev["imp"], "imp_a15": ev["imp_a15"],
               "side": s, "D": D, "e": e, "entry_ms": int(ms[e]), "half": "first" if ms[e] < split_ms else "second",
               "drift_day": s * (float(c[xd - 1]) - en) / D if xd <= n and xd - 1 >= e else None,
               "drift_24": s * (float(c[x24 - 1]) - en) / D if x24 < n and x24 - 1 >= e else None}
        for mode, side in (("with", s), ("fade", -s)):
            od = sb.outcome_window(R, i, side, D, xd, X, "close")
            o24 = sb.outcome_window(R, i, side, D, x24, X, "close")
            row["%s_day" % mode] = od["hit"] if od else None
            row["%s_amb" % mode] = bool(od["ambiguous"]) if od else False
            row["%s_24" % mode] = o24["hit"] if o24 else None
            row["%s_trade" % mode] = trade_of(R, od, side, D, fee)
        out.append(row)
    return out


def trades_of(rows, mode):
    """One position per market per variant (rows of one market, time order)."""
    out, busy = [], -1
    for r in sorted(rows, key=lambda r: r["entry_ms"]):
        t = r["%s_trade" % mode]
        if r["e"] <= busy:
            continue
        if t is None:
            busy = 10 ** 12
            continue
        out.append(dict(t, asset=r["asset"], half=r["half"], type=r["type"], entry_ms=r["entry_ms"]))
        busy = t["busy"]
    return out


# ---------------------------------------------------------------- per market
def truncation_check(df, rel, cuts):
    full_R = adr.readings(df, box=db.BOX)
    full = dict((k, release_events(full_R, rel, k)) for k in KS)
    bad, checked = 0, 0
    for cut in cuts:
        part_R = adr.readings(df.iloc[:cut], box=db.BOX)
        for k in KS:
            want = event_key(full[k], cut)
            got = event_key(release_events(part_R, rel, k), cut)
            checked += len(want)
            if got != want:
                bad += 1
    return {"cuts": len(cuts), "events_checked": checked, "mismatched_runs": bad}


def run_market(asset, rel):
    df = rb.load_dev(asset)
    fee = pb.fee_side(asset)
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    R = adr.readings(df, box=db.BOX)
    res = {"asset": asset, "fee_side": fee, "bars": int(len(df)), "first_bar": str(df.index[0]),
           "last_bar": str(df.index[-1]), "status": {}}
    rows = {}
    seal_ms = ms_of(SEAL)
    in_span = rel[(rel["ts_ms"] >= start_ms - DAY_MS) & (rel["ts_ms"] < seal_ms)]
    for k in KS:
        evs = release_events(R, in_span, k)
        st = {}
        for ev in evs:
            if ev["T"] + k * BAR_MS < start_ms:
                continue
            st.setdefault(ev["type"], {}).setdefault(ev["status"], 0)
            st[ev["type"]][ev["status"]] += 1
        res["status"][str(k)] = st
        rows[k] = rows_of(R, evs, asset, fee, start_ms, split_ms)
    n = len(df)
    res["truncation"] = truncation_check(df, in_span, [int(n * 0.6) + 7, n - 40])
    return res, rows


# ---------------------------------------------------------------- aggregation and the pass bar
def cell(rows, key):
    res = [r for r in rows if r.get(key) is not None]
    k = int(sum(r[key] for r in res))
    m = len(res)
    return {"rows": len(rows), "resolved": m, "hits": k, "unresolved": len(rows) - m,
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": cs.binom_p(k, m) if m else None}


def halves(rows, key):
    return {"first": cell([r for r in rows if r["half"] == "first"], key),
            "second": cell([r for r in rows if r["half"] == "second"], key), "all": cell(rows, key)}


def release_level(rows, key):
    """Each release counted once: hit if most of its resolved market rows hit; ties dropped."""
    out = {}
    for hf in ("first", "second"):
        by = {}
        for r in rows:
            if r["half"] == hf and r.get(key) is not None:
                by.setdefault(r["T"], []).append(r[key])
        votes = [1 if np.mean(v) > 0.5 else 0 for v in by.values() if np.mean(v) != 0.5]
        k, m = int(sum(votes)), len(votes)
        out[hf] = {"releases": len(by), "decided": m, "hits": k, "hit_pct": round(100.0 * k / m, 2) if m else None,
                   "p": cs.binom_p(k, m) if m else None}
    return out


def tmetrics(tr):
    return db.metrics(tr) if tr else {"trades": 0, "net_usd": 0.0}


def sel(rows_k, var):
    return [r for r in rows_k if abs(r["imp"]) >= var["thr"]]


def aggregate(ROWS):
    """ROWS: {asset: {k: rows}} -> (per-variant nodes, judge)."""
    A, J = {}, {"passed": []}
    for v in ORDER:
        var = VARIANTS[v]
        mode = var["mode"]
        dk, hk = "%s_day" % mode, "%s_24" % mode
        allr = sorted([r for a in ASSETS for r in sel(ROWS[a][var["k"]], var)], key=lambda r: (r["entry_ms"], r["asset"]))
        trades = []
        for a in ASSETS:
            trades += trades_of(sel(ROWS[a][var["k"]], var), mode)
        node = {"pooled": {"day": halves(allr, dk), "h24": halves(allr, hk),
                           "trade": dict((hf, tmetrics([t for t in trades if t["half"] == hf])) for hf in ("first", "second"))},
                "release_level": release_level(allr, dk), "types": {}, "markets": {},
                "ambiguous_pct": round(100.0 * np.mean([r["%s_amb" % mode] for r in allr]), 1) if allr else None}
        for ty in KINDS:
            rr = [r for r in allr if r["type"] == ty]
            tt = [t for t in trades if t["type"] == ty]
            node["types"][ty] = {"day": halves(rr, dk), "h24": halves(rr, hk),
                                 "trade": dict((hf, tmetrics([t for t in tt if t["half"] == hf])) for hf in ("first", "second"))}
        for a in ASSETS:
            rr = [r for r in allr if r["asset"] == a]
            tt = [t for t in trades if t["asset"] == a]
            node["markets"][a] = {"day": halves(rr, dk), "h24": halves(rr, hk),
                                  "trade": dict((hf, tmetrics([t for t in tt if t["half"] == hf])) for hf in ("first", "second"))}
        P = node["pooled"]
        d1, d2 = P["day"]["first"], P["day"]["second"]
        t2 = P["trade"]["second"]
        good_mk = [a for a in ASSETS if node["markets"][a]["trade"]["second"]["trades"]
                   and node["markets"][a]["trade"]["second"]["net_usd"] > 0]
        b = {"hit_both": bool(d1["hit_pct"] is not None and d2["hit_pct"] is not None
                              and d1["hit_pct"] >= PASS_HIT and d2["hit_pct"] >= PASS_HIT),
             "n_both": bool(d1["resolved"] >= MIN_RESOLVED and d2["resolved"] >= MIN_RESOLVED),
             "p_both": bool(d1["p"] is not None and d2["p"] is not None and d1["p"] < ALPHA and d2["p"] < ALPHA),
             "trade_pooled": bool(t2["trades"] and t2["net_usd"] > 0),
             "markets": len(good_mk), "markets_list": good_mk}
        b["markets_ok"] = b["markets"] >= PASS_MARKETS
        b["pass"] = bool(b["hit_both"] and b["n_both"] and b["p_both"] and b["trade_pooled"] and b["markets_ok"])
        b["min_hit"] = min(d1["hit_pct"], d2["hit_pct"]) if d1["hit_pct"] is not None and d2["hit_pct"] is not None else None
        node["bar"] = b
        node["bonf_both"] = [o for o in ("day", "h24") if all(
            P[o][hf]["p"] is not None and P[o][hf]["p"] < ALPHA for hf in ("first", "second"))]
        A[v] = node
        if b["pass"]:
            J["passed"].append(v)
    return A, J


def impulse_table(ROWS, k, unit):
    buckets = D_BUCKETS if unit == "datr" else A_BUCKETS
    key = "imp" if unit == "datr" else "imp_a15"
    rows = [r for a in ASSETS for r in ROWS[a][k] if r.get(key) is not None]
    out = []
    for lo, hi in buckets:
        rr = [r for r in rows if lo <= abs(r[key]) < hi]
        line = {"lo": lo, "hi": None if hi == np.inf else hi}
        for hf in ("first", "second"):
            h = [r for r in rr if r["half"] == hf]
            dd = [r["drift_day"] for r in h if r["drift_day"] is not None]
            d24 = [r["drift_24"] for r in h if r["drift_24"] is not None]
            c = cell(h, "with_day")
            line[hf] = {"rows": len(h), "drift_day": round(float(np.mean(dd)), 3) if dd else None,
                        "drift_day_med": round(float(np.median(dd)), 3) if dd else None,
                        "drift_24": round(float(np.mean(d24)), 3) if d24 else None,
                        "pos_day_pct": round(100.0 * float(np.mean([x > 0 for x in dd])), 1) if dd else None,
                        "with_hit": c["hit_pct"], "resolved": c["resolved"], "p": c["p"]}
        out.append(line)
    return out


def type_table(ROWS, k):
    """Impulse-size / drift by release type (descriptive), all rows of window k."""
    rows = [r for a in ASSETS for r in ROWS[a][k]]
    out = {}
    for ty in KINDS:
        rr = [r for r in rows if r["type"] == ty]
        node = {}
        for hf in ("first", "second"):
            h = [r for r in rr if r["half"] == hf]
            dd = [r["drift_day"] for r in h if r["drift_day"] is not None]
            node[hf] = {"rows": len(h), "releases": len(set(r["T"] for r in h)),
                        "med_abs_imp": round(float(np.median([abs(r["imp"]) for r in h])), 3) if h else None,
                        "drift_day": round(float(np.mean(dd)), 3) if dd else None,
                        "with_hit": cell(h, "with_day")["hit_pct"], "resolved": cell(h, "with_day")["resolved"]}
        out[ty] = node
    return out


def releases_used(rel, ROWS):
    split_ms = ms_of(SPLIT)
    out = {}
    for ty in KINDS:
        node = {}
        for hf in ("first", "second"):
            node["in_calendar"] = node.get("in_calendar", {})
            a, b = (ms_of(START), split_ms) if hf == "first" else (split_ms, ms_of(SEAL))
            node["in_calendar"][hf] = int(((rel["type"] == ty) & (rel["ts_ms"] >= a) & (rel["ts_ms"] < b)).sum())
            for k in KS:
                rr = [r for x in ASSETS for r in ROWS[x][k] if r["type"] == ty and r["half"] == hf]
                node.setdefault("k%d" % k, {})[hf] = {"releases": len(set(r["T"] for r in rr)), "rows": len(rr)}
        out[ty] = node
    return out


# ---------------------------------------------------------------- report
def _p(p):
    if p is None:
        return ""
    return "%.2e" % p if p < 1e-3 else "%.3f" % p


def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | "
    return "%.1f%% | %d (%d unres.) | %s" % (c["hit_pct"], c["resolved"], c["unresolved"], _p(c["p"]))


def _t(m):
    if not m or not m.get("trades"):
        return "0 | | | | | | "
    return "%d | %.1f%% | %+.3f | %+.3f | %s | %+.4f%% | %s" % (
        m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"], "n/a" if m.get("pf") is None else "%.2f" % m["pf"],
        m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


def _f(x, fmt="%+.3f"):
    return "" if x is None else fmt % x


THDR = "trades | won | R before | R after | PF | per trade (% stake) | net $"


def report(S):
    A, J, res = S["agg"], S["judge"], S["results"]
    L = ["# H50: post-news drift", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/hypotheses_pending/H50.md`) before any code or number. Development "
         "data only (rows before %s 00:00 UTC; the holdout was not read). Releases with entry from %s; first half before "
         "%s. Written %s." % (REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Releases: CPI, NFP, FOMC, PCE, advance GDP from `engine15/calhistory.py` (official dates, agency release times; "
         "same-minute rows = one release, typed FOMC > CPI > NFP > PCE > GDP). Impulse I = (close of the k-th 15m bar from "
         "the release - the last close before it) / daily ATR. Hit = +0.5 daily ATR in the trade's favour before -0.5 "
         "against, from the next 15m open, within the release's UTC day (a bar touching both = miss; neither = "
         "unresolved, excluded). p = exact two-sided binomial against 50%%. Tests: %d variants x 2 outcomes = **%d** per "
         "half; Bonferroni p < %.2e. Rows = release x market pairs; one release moves all markets together, so the "
         "pooled p overstates the evidence (see the release-level check)." % (len(ORDER), S["n_tests"], S["alpha"]), ""]
    passed = J["passed"]
    L += ["## Verdict: %s" % (("PASS: " + ", ".join(passed)) if passed else "NO PASS"), ""]
    L += ["## Releases used", "",
          "| type | in calendar 1st / 2nd | k=1: releases with a row 1st / 2nd | rows 1st / 2nd | k=4: releases 1st / 2nd | rows 1st / 2nd |",
          "|---|---|---|---|---|---|"]
    for ty, u in S["releases_used"].items():
        L.append("| %s | %d / %d | %d / %d | %d / %d | %d / %d | %d / %d |" % (
            ty, u["in_calendar"]["first"], u["in_calendar"]["second"],
            u["k1"]["first"]["releases"], u["k1"]["second"]["releases"], u["k1"]["first"]["rows"], u["k1"]["second"]["rows"],
            u["k4"]["first"]["releases"], u["k4"]["second"]["releases"], u["k4"]["first"]["rows"], u["k4"]["second"]["rows"]))
    L += ["", "## The variants", "", "| id | rule |", "|---|---|"]
    for v in ORDER:
        L.append("| %s | %s |" % (v, vdesc(v)))
    L += ["", "## Pooled hit rates (primary: rest of the UTC day; secondary: 24 h)", "",
          "| id | first: hit | resolved | p | second: hit | resolved | p | 24 h first | p | 24 h second | p | both barriers in one bar |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        P = A[v]["pooled"]
        L.append("| %s | %s | %s | %s (%d) | %s | %s (%d) | %s | %s%% |" % (
            v, _h(P["day"]["first"]), _h(P["day"]["second"]),
            _f(P["h24"]["first"]["hit_pct"], "%.1f%%"), P["h24"]["first"]["resolved"], _p(P["h24"]["first"]["p"]),
            _f(P["h24"]["second"]["hit_pct"], "%.1f%%"), P["h24"]["second"]["resolved"], _p(P["h24"]["second"]["p"]),
            A[v]["ambiguous_pct"]))
    L += ["", "## Release-level check (each release counted once; descriptive, not a test)", "",
          "| id | first: releases | decided | hit % | p | second: releases | decided | hit % | p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        R = A[v]["release_level"]
        L.append("| %s | %d | %d | %s | %s | %d | %d | %s | %s |" % (
            v, R["first"]["releases"], R["first"]["decided"], _f(R["first"]["hit_pct"], "%.1f"), _p(R["first"]["p"]),
            R["second"]["releases"], R["second"]["decided"], _f(R["second"]["hit_pct"], "%.1f"), _p(R["second"]["p"])))
    L += ["", "## The registered trade, pooled (the +/- 0.5 dATR bracket, out at the day's last close; own fee a side)", "",
          "| id | half | " + THDR + " |", "|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        for hf in ("first", "second"):
            L.append("| %s | %s | %s |" % (v if hf == "first" else "", hf, _t(A[v]["pooled"]["trade"][hf])))
    L += ["", "## Pass bar, every variant", "",
          "| id | hit >= 55% both | >= 100 resolved both | p < alpha both | trade 2nd half pooled net > 0 | markets net > 0 (2nd half) | PASS |",
          "|---|---|---|---|---|---|---|"]
    yn = lambda x: "yes" if x else "no"  # noqa: E731
    for v in ORDER:
        b = A[v]["bar"]
        L.append("| %s | %s | %s | %s | %s | %d (%s) | **%s** |" % (
            v, yn(b["hit_both"]), yn(b["n_both"]), yn(b["p_both"]), yn(b["trade_pooled"]), b["markets"],
            ", ".join(b["markets_list"]) or "-", "PASS" if b["pass"] else "no"))
    nb = [(v, o) for v in ORDER for o in A[v]["bonf_both"]]
    L += ["", "Outcome cells whose pooled p passes Bonferroni in BOTH halves (either side of 50%%): %d of %d%s." % (
        len(nb), S["n_tests"], (": " + ", ".join("%s %s" % x for x in nb)) if nb else ""), ""]
    for k in KS:
        L += ["## Impulse size vs drift, k = %d (%d min), every release-market row, no threshold" % (k, 15 * k), "",
              "Drift = move from the entry open (next 15m open after the window) to the day's last close / the 24 h close, "
              "in the impulse's direction, daily-ATR units. WITH hit = the primary bracket traded with the impulse.", "",
              "| abs(I) in daily ATR | half | rows | mean drift day | median drift day | mean drift 24 h | drift > 0 | WITH hit | resolved | p |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for line in S["impulse"]["k%d_datr" % k]:
            lab = "%.2f-%s" % (line["lo"], "%.2f" % line["hi"] if line["hi"] is not None else "up")
            for hf in ("first", "second"):
                c = line[hf]
                L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %d | %s |" % (
                    lab if hf == "first" else "", hf, c["rows"], _f(c["drift_day"]), _f(c["drift_day_med"]), _f(c["drift_24"]),
                    _f(c["pos_day_pct"], "%.1f%%"), _f(c["with_hit"], "%.1f%%"), c["resolved"], _p(c["p"])))
        L += ["", "Same rows by abs(I) in ATR15 units (ATR15 of the bar before the release):", "",
              "| abs(I) in ATR15 | half | rows | mean drift day (dATR) | mean drift 24 h | drift > 0 | WITH hit | resolved |",
              "|---|---|---|---|---|---|---|---|"]
        for line in S["impulse"]["k%d_a15" % k]:
            lab = "%.0f-%s" % (line["lo"], "%.0f" % line["hi"] if line["hi"] is not None else "up")
            for hf in ("first", "second"):
                c = line[hf]
                L.append("| %s | %s | %d | %s | %s | %s | %s | %d |" % (
                    lab if hf == "first" else "", hf, c["rows"], _f(c["drift_day"]), _f(c["drift_24"]),
                    _f(c["pos_day_pct"], "%.1f%%"), _f(c["with_hit"], "%.1f%%"), c["resolved"]))
        L += ["", "By release type (k = %d, every row, no threshold):" % k, "",
              "| type | half | releases | rows | median abs(I) dATR | mean drift day | WITH hit | resolved |",
              "|---|---|---|---|---|---|---|---|"]
        for ty, node in S["types_k%d" % k].items():
            for hf in ("first", "second"):
                c = node[hf]
                L.append("| %s | %s | %d | %d | %s | %s | %s | %d |" % (
                    ty if hf == "first" else "", hf, c["releases"], c["rows"], _f(c["med_abs_imp"], "%.3f"),
                    _f(c["drift_day"]), _f(c["with_hit"], "%.1f%%"), c["resolved"]))
        L.append("")
    L += ["## By release type, every variant (descriptive)", "",
          "| id | type | first: hit | resolved | p | second: hit | resolved | p | trade 2nd half: trades | net $ |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        first = True
        for ty in KINDS:
            c = A[v]["types"][ty]
            t2 = c["trade"]["second"]
            L.append("| %s | %s | %s | %s | %d | %s |" % (v if first else "", ty, _h(c["day"]["first"]), _h(c["day"]["second"]),
                                                        t2["trades"], "{:+,.0f}".format(t2["net_usd"])))
            first = False
    L += ["", "## Per market (descriptive)", "",
          "| id | market | first: hit | resolved | p | second: hit | resolved | p | trade first: net $ | trade second: trades | won | R after | net $ |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        first = True
        for a in ASSETS:
            c = A[v]["markets"][a]
            t1, t2 = c["trade"]["first"], c["trade"]["second"]
            L.append("| %s | %s | %s | %s | %s | %d | %s | %s | %s |" % (
                v if first else "", a, _h(c["day"]["first"]), _h(c["day"]["second"]), "{:+,.0f}".format(t1["net_usd"]),
                t2["trades"], _f(t2.get("win_pct"), "%.1f%%"), _f(t2.get("avg_r")), "{:+,.0f}".format(t2["net_usd"])))
            first = False
    L += ["", "## Checks", "",
          "| market | bars | first bar | last bar | fee a side | truncation cuts | events compared | mismatched runs | k=1 release status (ok / closed / other) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a, r in res.items():
        tc = r["truncation"]
        st = r["status"]["1"]
        ok = sum(x.get("ok", 0) for x in st.values())
        cl = sum(x.get("closed", 0) for x in st.values())
        ot = sum(v for x in st.values() for kk, v in x.items() if kk not in ("ok", "closed"))
        L.append("| %s | %d | %s | %s | %.3f%% | %d | %d | %d | %d / %d / %d |" % (
            a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], tc["cuts"], tc["events_checked"],
            tc["mismatched_runs"], ok, cl, ot))
    L += ["", "## Notes", "", NOTES, ""]
    return "\n".join(L)


NOTES = (
    "- Release times are each agency's standard release time on the official release date (ALFRED vintage dates for "
    "BLS/BEA, federalreserve.gov for the FOMC); they were not checked row by row against the tape here.\n"
    "- The S&P 500 file is cash hours only: it sees the FOMC statement (14:00 ET) but not the 8:30 ET releases.\n"
    "- F1-F4 use N1-N4's rows with the opposite side; with a symmetric bracket their hit rates are close to the "
    "complement of N1-N4's (a bar touching both barriers is a miss for both).\n"
    "- Related forward-only shadows: H1 (CPI follow-through, BTC/ETH) and H16 (release-day follow-through) were set on "
    "the 2026 live calendar; H50 is the first look at 2020-2025 and does not change them.")


# ---------------------------------------------------------------- main
def _jsonable(o):
    if isinstance(o, dict):
        return dict((str(k), _jsonable(v)) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if o != o else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and (o != o or o in (np.inf, -np.inf)):
        return None
    return o


def run(assets=ASSETS):
    t0 = time.time()
    rel = load_releases()
    log("releases: %d (%s)" % (len(rel), ", ".join("%s %d" % (k, int((rel["type"] == k).sum())) for k in KINDS)))
    res, ROWS = {}, {}
    for a in assets:
        log("market %s ..." % a)
        r, rows = run_market(a, rel)
        res[a], ROWS[a] = r, rows
        log("  %s: k1 rows %d, k4 rows %d, truncation mismatches %d (%d events)" % (
            a, len(rows[1]), len(rows[4]), r["truncation"]["mismatched_runs"], r["truncation"]["events_checked"]))
    for a in ASSETS:
        ROWS.setdefault(a, {1: [], 4: []})
    A, J = aggregate(ROWS)
    S = {"hypothesis": "H50", "registered": REGISTERED_UTC, "written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
         "n_tests": N_TESTS, "alpha": ALPHA, "variants": VARIANTS, "results": res, "agg": A, "judge": J,
         "releases_used": releases_used(rel, ROWS),
         "impulse": dict(("k%d_%s" % (k, u), impulse_table(ROWS, k, u)) for k in KS for u in ("datr", "a15")),
         "types_k1": type_table(ROWS, 1), "types_k4": type_table(ROWS, 4),
         "rows": dict((a, dict((str(k), [dict((kk, vv) for kk, vv in r.items() if not kk.endswith("_trade"))
                                         for r in ROWS[a][k]]) for k in KS)) for a in ASSETS),
         "seconds": round(time.time() - t0, 1)}
    S = _jsonable(S)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, indent=1)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as f:
        f.write(report(S))
    log("done in %.0f s: %s" % (time.time() - t0, ("PASS " + ", ".join(J["passed"])) if J["passed"] else "NO PASS"))
    for v in ORDER:
        P = A[v]["pooled"]
        log("  %s day %s%% (%d) p %s / %s%% (%d) p %s; trade 2nd net %s" % (
            v, P["day"]["first"]["hit_pct"], P["day"]["first"]["resolved"], _p(P["day"]["first"]["p"]),
            P["day"]["second"]["hit_pct"], P["day"]["second"]["resolved"], _p(P["day"]["second"]["p"]),
            P["trade"]["second"]["net_usd"]))
    return S


def main():
    if "--report" in sys.argv:
        with open(os.path.join(OUT, "study.json"), encoding="utf-8") as f:
            S = json.load(f)
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as f:
            f.write(report(S))
        return
    assets = ASSETS
    if "--assets" in sys.argv:
        assets = tuple(sys.argv[sys.argv.index("--assets") + 1].split(","))
    run(assets)


if __name__ == "__main__":
    main()
