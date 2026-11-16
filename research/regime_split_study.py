# -*- coding: utf-8 -*-
"""H47 REGIME SPLIT at a daily-level break. PAPER RESEARCH ONLY.

Registered before any code or outcome: research/HYPOTHESES.md H47 (16 Nov 2026, 05:40 UTC). In short:
  * events and outcome = H46's (first 15m close beyond the prior UTC day's high/low or the previous 96 bars' high/low per
    UTC day per direction; +0.5 daily ATR before -0.5 daily ATR from the next open within 72 h; confluence_study.outcome);
    the FADE side = the same event against the break (confluence_study.outcome with the side flipped);
  * five regime measures on closed UTC daily bars through data.htf_on_15: R1 the engine's regime_daily label, R2 daily
    ADX(14), R3 Kaufman ER(20), R4 realised-volatility percentile (rv20 within 250 days), R5 variance ratio VR(5) over
    250 daily returns; 23 buckets x 2 sides x 2 levels x 6 scopes = 552 tests per half (Bonferroni 9.06e-5);
  * pass bar (pooled): >= 55% both halves, >= 200 resolved per half, Bonferroni both halves, net after costs > 0 in the
    second half pooled and in >= 5 of 8 markets; core question: trend vs range follow hit rate, z test, p < 0.005 both halves;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market. Reads data/*.csv only; writes research/out/regime_split/.

    py -3 research/regime_split_study.py            (run, write study.json + study.md, then the live scan)
    py -3 research/regime_split_study.py --report   (rewrite study.md from study.json)
    py -3 research/regime_split_study.py --scan     (the live scan only: latest closed bars, paper / untested)
"""
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, indicators as ind, playbook as pb  # noqa: E402
from engine15.sources import adr, ltf  # noqa: E402
from engine15.rl import resources  # noqa: E402

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402
import confluence_study as cb  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 05:40 UTC"
ASSETS = rb.ASSETS
MGROUPS = db.GROUPS
GROUP_OF = db.GROUP_OF
SCOPES = ["pooled"] + list(MGROUPS)
LEVELS = ("pday", "roll24")
SIDES = ("follow", "fade")
OUT = os.path.join(ROOT, "research", "out", "regime_split")
NEED_MB = 1500
DAY_MS = 86400000

# ---- the registered constants
ADX_N, ADX_TREND, ADX_RANGE = 14, 25.0, 20.0
ER_N = 20
RV_N, RV_WIN = 20, 250
VR_Q, VR_WIN = 5, 250
MIN_RESOLVED, PASS_HIT, PASS_MARKETS = 200, 55.0, 5
TREND_LABELS = ("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN")
TERCILE_MEASURES = ("er", "rvp", "vr")
VALS = ("label", "adx", "dip", "er", "dir20", "rvp", "vr")

FAMILIES = {"R1": "engine regime label (regime_daily)", "R2": "daily ADX(14)", "R3": "efficiency ratio, 20 daily closes",
            "R4": "realised-volatility percentile (rv20 in 250 days)", "R5": "variance ratio VR(5), 250 daily returns"}


def _aligned_label(e, kind):
    lab, s = e["label"], e["side"]
    return lab == ("%s_UP" % kind if s > 0 else "%s_DOWN" % kind)


def _counter_label(e, kind):
    lab, s = e["label"], e["side"]
    return lab == ("%s_DOWN" % kind if s > 0 else "%s_UP" % kind)


def bucket_defs(cut):
    """cut = {"er": (lo, hi), "rvp": (lo, hi), "vr": (lo, hi)} first-half tercile cutoffs.
    -> ordered list of (bucket id, family, description, test on an event dict -> True / False / None (no read))."""
    def has(e, k):
        v = e[k]
        return v is not None and v == v

    def tri(k, part):
        lo, hi = cut[k]

        def f(e):
            if not has(e, k):
                return None
            v = e[k]
            return v >= hi if part == "high" else (v < lo if part == "low" else lo <= v < hi)
        return f

    def lab(fn):
        return lambda e: None if not isinstance(e["label"], str) else fn(e)

    def adx(fn):
        return lambda e: None if not has(e, "adx") else fn(e)

    def er_dir(want_aligned):
        hi = cut["er"][1]

        def f(e):
            if not has(e, "er") or not has(e, "dir20"):
                return None
            return e["er"] >= hi and ((e["dir20"] * e["side"] > 0) if want_aligned else (e["dir20"] * e["side"] < 0))
        return f

    B = [
        ("R1a", "R1", "TREND aligned with the break", lab(lambda e: _aligned_label(e, "TREND"))),
        ("R1b", "R1", "TREND counter to the break", lab(lambda e: _counter_label(e, "TREND"))),
        ("R1c", "R1", "MOMENTUM aligned", lab(lambda e: _aligned_label(e, "MOMENTUM"))),
        ("R1d", "R1", "MOMENTUM counter", lab(lambda e: _counter_label(e, "MOMENTUM"))),
        ("R1e", "R1", "TRENDING any (TREND_* or MOMENTUM_*)", lab(lambda e: e["label"] in TREND_LABELS)),
        ("R1f", "R1", "RANGE", lab(lambda e: e["label"] == "RANGE")),
        ("R1g", "R1", "TRANSITION", lab(lambda e: e["label"] == "TRANSITION")),
        ("R2a", "R2", "ADX >= 25", adx(lambda e: e["adx"] >= ADX_TREND)),
        ("R2b", "R2", "ADX >= 25, DI aligned", adx(lambda e: e["adx"] >= ADX_TREND and has(e, "dip") and e["dip"] * e["side"] > 0)),
        ("R2c", "R2", "ADX >= 25, DI counter", adx(lambda e: e["adx"] >= ADX_TREND and has(e, "dip") and e["dip"] * e["side"] < 0)),
        ("R2d", "R2", "20 <= ADX < 25", adx(lambda e: ADX_RANGE <= e["adx"] < ADX_TREND)),
        ("R2e", "R2", "ADX < 20", adx(lambda e: e["adx"] < ADX_RANGE)),
        ("R3a", "R3", "ER high tercile", tri("er", "high")),
        ("R3b", "R3", "ER high, 20-day move aligned", er_dir(True)),
        ("R3c", "R3", "ER high, 20-day move counter", er_dir(False)),
        ("R3d", "R3", "ER middle tercile", tri("er", "mid")),
        ("R3e", "R3", "ER low tercile", tri("er", "low")),
        ("R4a", "R4", "volatility percentile high tercile", tri("rvp", "high")),
        ("R4b", "R4", "volatility percentile middle", tri("rvp", "mid")),
        ("R4c", "R4", "volatility percentile low tercile", tri("rvp", "low")),
        ("R5a", "R5", "VR(5) high tercile (persistent)", tri("vr", "high")),
        ("R5b", "R5", "VR(5) middle", tri("vr", "mid")),
        ("R5c", "R5", "VR(5) low tercile (mean reverting)", tri("vr", "low")),
    ]
    return B


N_BUCKETS = 23
N_TESTS = N_BUCKETS * len(SIDES) * len(LEVELS) * len(SCOPES)        # 552
ALPHA = 0.05 / N_TESTS
CONTRASTS = [("R1", "R1e", "R1f"), ("R2", "R2a", "R2e"), ("R3", "R3a", "R3e"), ("R4", "R4a", "R4c"), ("R5", "R5a", "R5c")]
SECONDARY = [("R1", "R1a", "R1b"), ("R2", "R2b", "R2c"), ("R3", "R3b", "R3c")]
N_CONTRASTS = len(CONTRASTS) * len(LEVELS)                            # 10
ALPHA_DIFF = 0.05 / N_CONTRASTS


# ---------------------------------------------------------------- statistics
def diff_test(k1, n1, k2, n2):
    """Two-proportion z test (pooled variance), two-sided -> (difference in points, p)."""
    if not n1 or not n2:
        return None, None
    p1, p2 = k1 / float(n1), k2 / float(n2)
    pp = (k1 + k2) / float(n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1.0 / n1 + 1.0 / n2))
    if se <= 0:
        return round(100 * (p1 - p2), 2), None
    z = (p1 - p2) / se
    return round(100 * (p1 - p2), 2), float(math.erfc(abs(z) / math.sqrt(2.0)))


# ---------------------------------------------------------------- the regime readings (truncation-tested)
def regimes(bars):
    """15m bars -> dict of arrays on the bars' rows, each known at the close of its row (closed UTC daily bars only,
    joined with data.htf_on_15): label (object), adx, dip (+DI - -DI), er, dir20, rvp, vr."""
    b = bars[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)
    if not b.index.is_monotonic_increasing or b.index.has_duplicates:
        b = b[~b.index.duplicated(keep="last")].sort_index()
    d1 = data.resample(b, "1D")
    c = d1["close"]
    lr = np.log(c).diff()
    a = ltf.adx(d1, ADX_N)
    er = (c - c.shift(ER_N)).abs() / c.diff().abs().rolling(ER_N).sum().replace(0, np.nan)
    rv = lr.rolling(RV_N).std()
    rvp = rv.rolling(RV_WIN).rank(pct=True)
    s5 = lr.rolling(VR_Q).sum()
    vr = s5.rolling(VR_WIN - VR_Q + 1).var() / (VR_Q * lr.rolling(VR_WIN).var())
    num = pd.DataFrame({"adx": a["adx"], "dip": a["plus"] - a["minus"], "er": er,
                        "dir20": np.sign(c - c.shift(ER_N)), "rvp": rvp, "vr": vr}, index=d1.index)
    j = data.htf_on_15(b, "1D", num)
    lab = data.htf_on_15(b, "1D", ind.regime_daily(d1))
    out = dict((k, j[k].values.astype(float)) for k in num.columns)
    out["label"] = np.array([x if isinstance(x, str) else None for x in lab.values], dtype=object)
    out["n"] = len(b)
    return out


def regime_at(G, i):
    return dict((k, (G[k][i] if k == "label" else (float(G[k][i]) if G[k][i] == G[k][i] else None))) for k in VALS)


# ---------------------------------------------------------------- events, outcomes, trades
def events(R, G, level):
    """-> list of event dicts (break rows, oldest first) with the regime reading at the break bar's close and the
    follow / fade outcome (H46's outcome function, the fade with the side flipped)."""
    dirs = db.daily_breaks(R, level, False)
    D = R["datr"]
    ms = R["ms"]
    out = []
    for i in np.flatnonzero(dirs != 0):
        if not (D[i] == D[i] and D[i] > 0):
            continue
        s = int(dirs[i])
        fo = cb.outcome(R, int(i), s, float(D[i]))
        if fo is None:
            out.append({"i": int(i), "side": s, "excluded": "no_entry_same_day"})
            continue
        fa = cb.outcome(R, int(i), -s, float(D[i]))
        e = {"i": int(i), "side": s, "datr": float(D[i]), "entry_ms": int(ms[fo["e"]]), "excluded": None}
        e.update(regime_at(G, int(i)))
        for pre, oc in (("", fo), ("f_", fa)):
            e[pre + "hit"] = oc["hit"]
            e[pre + "ambiguous"] = oc["ambiguous"]
            e[pre + "why"] = oc["why"]
            e[pre + "entry"] = oc["entry"]
            e[pre + "stop"] = oc["stop"]
            e[pre + "exit"] = oc.get("exit")
            e[pre + "exit_bar"] = oc.get("exit_bar")
            e[pre + "exit_ms"] = int(ms[oc["exit_bar"]]) if oc.get("exit_bar") is not None else None
        out.append(e)
    return out


def side_view(e, side):
    """-> the event as confluence_study.trades_of expects it, for the follow or the fade trade."""
    pre = "" if side == "follow" else "f_"
    return {"i": e["i"], "side": e["side"] if side == "follow" else -e["side"], "entry_ms": e["entry_ms"],
            "exit_ms": e[pre + "exit_ms"], "why": e[pre + "why"], "entry": e[pre + "entry"], "stop": e[pre + "stop"],
            "exit": e[pre + "exit"], "exit_bar": e[pre + "exit_bar"]}


def regime_key(G, upto):
    out = []
    for k in VALS:
        x = G[k][:upto]
        if k == "label":
            out.append(tuple(x))
        else:
            out.append(tuple(np.round(np.where(np.isfinite(x), x, -999.0), 9)))
    return out


def truncation_check(df, cuts):
    G = regimes(df)
    bad, checked = 0, 0
    for cut in cuts:
        P = regimes(df.iloc[:cut])
        checked += cut
        for k in VALS:
            a, b = P[k], G[k][:cut]
            if k == "label":
                same = list(a) == list(b)
            else:
                same = np.array_equal(np.isfinite(a), np.isfinite(b)) and np.allclose(a[np.isfinite(a)], b[np.isfinite(b)], rtol=1e-9, atol=1e-12)
            if not same:
                bad += 1
    return {"cuts": len(cuts), "rows_checked": checked, "mismatched_arrays": bad}


def evidence_label_check(df):
    """R1 must equal evidence.py's recipe: htf_on_15(df15, '1D', regime_daily(resample(df15, '1D')))."""
    lab = data.htf_on_15(df, "1D", ind.regime_daily(data.resample(df, "1D")))
    want = np.array([x if isinstance(x, str) else None for x in lab.values], dtype=object)
    return int(sum(1 for a, b in zip(want, regimes(df)["label"]) if a != b))


# ---------------------------------------------------------------- per market
def run_asset(asset):
    df = rb.load_dev(asset)
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    R = adr.readings(df, box=db.BOX)
    G = regimes(df)
    res = {"asset": asset, "group": GROUP_OF[asset], "fee_side": pb.fee_side(asset), "bars": int(len(df)),
           "first_bar": str(df.index[0]), "last_bar": str(df.index[-1]), "excluded": {}, "no_read": {}}
    E = []
    for lv in LEVELS:
        ex = {"no_entry_same_day": 0, "before_start": 0, "open_at_seal": 0}
        nr = dict((k, 0) for k in ("label", "adx", "er", "rvp", "vr"))
        for e in events(R, G, lv):
            if e["excluded"]:
                ex[e["excluded"]] += 1
                continue
            if e["entry_ms"] < start_ms:
                ex["before_start"] += 1
                continue
            if e["why"] == "OPEN":
                ex["open_at_seal"] += 1
            for k in nr:
                if e[k] is None:
                    nr[k] += 1
            e.update(asset=asset, mgroup=GROUP_OF[asset], level=lv, half="first" if e["entry_ms"] < split_ms else "second")
            E.append(e)
        res["excluded"][lv] = ex
        res["no_read"][lv] = nr
    n = len(df)
    res["truncation"] = truncation_check(df, [int(n * 0.6) + 7, n - 40])
    res["evidence_label_mismatches"] = evidence_label_check(df)
    return res, E


# ---------------------------------------------------------------- aggregation
def cutoffs(E):
    first = [e for e in E if e["half"] == "first"]
    cut = {}
    for k in TERCILE_MEASURES:
        v = np.array([e[k] for e in first if e[k] is not None], dtype=float)
        cut[k] = (float(np.percentile(v, 100.0 / 3)), float(np.percentile(v, 200.0 / 3)))
    return cut


def cell(evs, side):
    h = "hit" if side == "follow" else "f_hit"
    res = [e for e in evs if e[h] is not None]
    k = int(sum(e[h] for e in res))
    m = len(res)
    return {"events": len(evs), "resolved": m, "hits": k, "unresolved": len(evs) - m,
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": cb.binom_p(k, m) if m else None}


def in_scope(e, scope):
    return scope == "pooled" or e["mgroup"] == scope


def aggregate(E, B):
    """-> {level: {scope: {"reference": {side: {half: cell}}, "buckets": {bid: {side: {half: cell, ...}}}}}}"""
    A = {}
    for lv in LEVELS:
        A[lv] = {}
        for sc in SCOPES:
            ev = [e for e in E if e["level"] == lv and in_scope(e, sc)]
            halves = {"first": [e for e in ev if e["half"] == "first"], "second": [e for e in ev if e["half"] == "second"]}
            node = {"reference": dict((sd, dict((hf, cell(x, sd)) for hf, x in halves.items())) for sd in SIDES),
                    "buckets": {}}
            for bid, _fam, _d, fn in B:
                node["buckets"][bid] = {}
                for sd in SIDES:
                    cells = dict((hf, cell([e for e in x if fn(e)], sd)) for hf, x in halves.items())
                    c1, c2 = cells["first"], cells["second"]
                    enough = c1["resolved"] >= MIN_RESOLVED and c2["resolved"] >= MIN_RESOLVED
                    cells["bonf_both"] = bool(c1["p"] is not None and c2["p"] is not None and c1["p"] < ALPHA and c2["p"] < ALPHA)
                    cells["hit_part"] = bool(enough and c1["hit_pct"] >= PASS_HIT and c2["hit_pct"] >= PASS_HIT and cells["bonf_both"])
                    cells["min_hit"] = min(c1["hit_pct"], c2["hit_pct"]) if (c1["hit_pct"] is not None and c2["hit_pct"] is not None) else None
                    node["buckets"][bid][sd] = cells
            A[lv][sc] = node
    return A


def contrasts(A):
    """-> list of rows: measure, level, scope, trend bucket, range bucket, per half (trend hit, n, range hit, n, diff, p)."""
    rows = []
    for pairs, kind in ((CONTRASTS, "primary"), (SECONDARY, "secondary")):
        for fam, t, r in pairs:
            for lv in LEVELS:
                for sc in SCOPES:
                    row = {"kind": kind, "family": fam, "level": lv, "scope": sc, "trend": t, "range": r}
                    for hf in ("first", "second"):
                        ct = A[lv][sc]["buckets"][t]["follow"][hf]
                        cr = A[lv][sc]["buckets"][r]["follow"][hf]
                        d, p = diff_test(ct["hits"], ct["resolved"], cr["hits"], cr["resolved"])
                        row[hf] = {"trend_hit": ct["hit_pct"], "trend_n": ct["resolved"], "range_hit": cr["hit_pct"],
                                   "range_n": cr["resolved"], "diff": d, "p": p}
                    f, s = row["first"], row["second"]
                    row["significant_both"] = bool(kind == "primary" and sc == "pooled" and f["p"] is not None and s["p"] is not None
                                                   and f["p"] < ALPHA_DIFF and s["p"] < ALPHA_DIFF
                                                   and f["diff"] * s["diff"] > 0)
                    row["nominal_both"] = bool(f["p"] is not None and s["p"] is not None and f["p"] < 0.05 and s["p"] < 0.05
                                               and f["diff"] * s["diff"] > 0)
                    rows.append(row)
    return rows


def months(half):
    a, b = (START, SPLIT) if half == "first" else (SPLIT, SEAL)
    return (ms_of(b) - ms_of(a)) / (DAY_MS * 30.4375)


def trade_table(E, B):
    """Every pooled bucket traded on both sides -> {"level|bucket|side": {"pooled": {half: m}, "markets": {...}, "per_month"}}"""
    split_ms = ms_of(SPLIT)
    T = {}
    for lv in LEVELS:
        evl = [e for e in E if e["level"] == lv]
        for bid, _fam, _d, fn in B:
            sel = [e for e in evl if fn(e)]
            for sd in SIDES:
                node = {"pooled": {}, "markets": {}, "per_month": {}}
                allt = []
                for a in ASSETS:
                    ev = sorted([side_view(e, sd) for e in sel if e["asset"] == a], key=lambda x: x["i"])
                    tr = cb.trades_of(ev, pb.fee_side(a))
                    allt += tr
                    node["markets"][a] = {}
                    for hf in ("first", "second"):
                        node["markets"][a][hf] = db.metrics([t for t in tr if (t["entry_ms"] < split_ms) == (hf == "first")])
                for hf in ("first", "second"):
                    node["pooled"][hf] = db.metrics([t for t in allt if (t["entry_ms"] < split_ms) == (hf == "first")])
                    node["per_month"][hf] = round(len([e for e in sel if e["half"] == hf]) / months(hf), 2)
                pos = sum(1 for a in ASSETS if node["markets"][a]["second"].get("trades") and node["markets"][a]["second"]["net_usd"] > 0)
                node["markets_positive_second"] = pos
                node["cost_part"] = bool(node["pooled"]["second"].get("trades") and node["pooled"]["second"]["net_usd"] > 0
                                         and pos >= PASS_MARKETS)
                T["%s|%s|%s" % (lv, bid, sd)] = node
    return T


# ---------------------------------------------------------------- report
def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | -"
    p = c["p"]
    return "%.1f%% | %d | %s" % (c["hit_pct"], c["resolved"], ("%.1e" % p) if p < 0.001 else ("%.3f" % p))


def _p(p):
    return "-" if p is None else (("%.1e" % p) if p < 0.001 else "%.3f" % p)


def fmt_tr(m):
    if not m or not m.get("trades"):
        return "0 | | | | |"
    return "%d | %.1f%% | %+.3f | %+.3f | %+.4f%% | %s" % (m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"],
                                                         m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


def report(S):
    A, T, res, C, cut = S["agg"], S["trades"], S["results"], S["contrasts"], S["cutoffs"]
    desc = dict((b[0], (b[1], b[2])) for b in S["buckets"])
    L = ["# H47: regime split at a daily-level break", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H47) before any outcome. Development data only "
         "(rows before %s 00:00 UTC; the holdout was not read). Events with entry from %s; first half before %s. "
         "Written %s." % (REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Events and outcome are H46's: the first 15m close beyond the level in its UTC day per direction; **follow** hit = "
         "+0.5 daily ATR in the break direction before -0.5 daily ATR from the next 15m open within 72 h; **fade** hit = the "
         "mirror (-0.5 before +0.5). A bar touching both = a miss for either side; neither within 72 h = unresolved, "
         "excluded. A coin flip is ~50%%. p = exact two-sided binomial against 50%%. Regime readings are taken from closed "
         "UTC daily bars at the break bar's close. Tests: %d buckets x 2 sides x 2 levels x 6 scopes = **%d** per half; "
         "Bonferroni p < %.2e." % (N_BUCKETS, N_TESTS, ALPHA), "",
         "Tercile cutoffs (first-half events, fixed): ER %.3f / %.3f; volatility percentile %.3f / %.3f; VR(5) %.3f / %.3f." % (
             cut["er"][0], cut["er"][1], cut["rvp"][0], cut["rvp"][1], cut["vr"][0], cut["vr"][1]), ""]
    L += ["## Verdict: %s" % ("%d bucket(s) PASS" % len(S["passes"]) if S["passes"] else "NO PASS"), ""]
    for p in S["passes"]:
        L.append("- %s" % p)
    if not S["passes"]:
        L.append("No regime bucket (follow or fade, either level, pooled) met the bar: >= %.0f%% in both halves with >= %d "
                 "resolved per half, Bonferroni in both halves, and positive after costs in the second half pooled and in "
                 ">= %d of 8 markets." % (PASS_HIT, MIN_RESOLVED, PASS_MARKETS))
        L.append("")
        L.append("Best pooled bucket by the lower of its two halves: %s." % S["best"])
    L += ["", "Buckets passing Bonferroni in both halves (any scope, any side, any hit rate): %d of %d." % (S["bonf_both_count"], N_TESTS), ""]
    nsig = [r for r in C if r["significant_both"]]
    L += ["## Does regime explain the 50%? Trend vs range, follow side, pooled", "",
          "Two-proportion z test, two-sided; 'significant' = same sign and p < %.3f (0.05 / %d) in BOTH halves." % (ALPHA_DIFF, N_CONTRASTS), "",
          "| measure | level | trend bucket | range bucket | 1st: trend hit (n) | range hit (n) | diff | p | 2nd: trend hit (n) | range hit (n) | diff | p | significant both |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def crow(r):
        f, s = r["first"], r["second"]

        def hn(h, n):
            return "-" if h is None else "%.1f%% (%d)" % (h, n)
        return "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["family"], r["level"], r["trend"], r["range"], hn(f["trend_hit"], f["trend_n"]), hn(f["range_hit"], f["range_n"]),
            "-" if f["diff"] is None else "%+.1f" % f["diff"], _p(f["p"]), hn(s["trend_hit"], s["trend_n"]),
            hn(s["range_hit"], s["range_n"]), "-" if s["diff"] is None else "%+.1f" % s["diff"], _p(s["p"]),
            "YES" if r["significant_both"] else ("nominal only" if r["nominal_both"] else ""))
    for r in C:
        if r["kind"] == "primary" and r["scope"] == "pooled":
            L.append(crow(r))
    L += ["", "%d of %d primary contrasts significant in both halves." % (len(nsig), N_CONTRASTS), "",
          "Secondary (descriptive): aligned vs counter within the trend buckets, pooled:", "",
          "| measure | level | aligned | counter | 1st: aligned hit (n) | counter hit (n) | diff | p | 2nd: aligned hit (n) | counter hit (n) | diff | p | nominal both |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in C:
        if r["kind"] == "secondary" and r["scope"] == "pooled":
            L.append(crow(r))
    L += ["", "Per market group (primary contrasts, follow side; diff first / second half in points, p in brackets):", "",
          "| measure | level | " + " | ".join(MGROUPS) + " |", "|---|---|" + "---|" * len(MGROUPS)]
    for fam, t, rr in CONTRASTS:
        for lv in LEVELS:
            cells = []
            for sc in MGROUPS:
                r = [x for x in C if x["kind"] == "primary" and x["family"] == fam and x["level"] == lv and x["scope"] == sc][0]
                f, s = r["first"], r["second"]
                cells.append("-" if f["diff"] is None or s["diff"] is None else "%+.1f [%s] / %+.1f [%s]" % (f["diff"], _p(f["p"]), s["diff"], _p(s["p"])))
            L.append("| %s | %s | %s |" % (fam, lv, " | ".join(cells)))
    L += ["", "## Reference: every daily break", "", "| level | scope | side | first: hit | n | p | second: hit | n | p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        for sc in SCOPES:
            for sd in SIDES:
                r = A[lv][sc]["reference"][sd]
                L.append("| %s | %s | %s | %s | %s |" % (lv, sc, sd, _h(r["first"]), _h(r["second"])))
    for lv in LEVELS:
        L += ["", "## Every bucket, pooled, %s" % lv, "",
              "| bucket | description | follow 1st: hit | n | p | follow 2nd: hit | n | p | fade 1st: hit | n | p | fade 2nd: hit | n | p |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for b in S["buckets"]:
            bid = b[0]
            c = A[lv]["pooled"]["buckets"][bid]
            L.append("| %s | %s | %s | %s | %s | %s |" % (bid, desc[bid][1], _h(c["follow"]["first"]), _h(c["follow"]["second"]),
                                                       _h(c["fade"]["first"]), _h(c["fade"]["second"])))
    L += ["", "## After costs: every pooled bucket traded (stop 0.5 dATR, target 0.5 dATR, 72 h max, own fee a side, one "
          "position per market)", "",
          "| level | bucket | side | 1st: trades | won | R gross | R net | % stake / trade | net $ | 2nd: trades | won | R gross | R net | % stake / trade | net $ | markets > 0 (2nd) | events / month (2nd) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, node in T.items():
        lv, bid, sd = key.split("|")
        L.append("| %s | %s | %s | %s | %s | %d | %.1f |" % (lv, bid, sd, fmt_tr(node["pooled"]["first"]), fmt_tr(node["pooled"]["second"]),
                                                          node["markets_positive_second"], node["per_month"]["second"]))
    L += ["", "## Per market group, every bucket (follow / fade hit rate, first / second half, resolved n in brackets)", ""]
    for lv in LEVELS:
        L += ["### %s" % lv, "", "| bucket | " + " | ".join(MGROUPS) + " |", "|---|" + "---|" * len(MGROUPS)]
        for b in S["buckets"]:
            bid = b[0]
            cells = []
            for sc in MGROUPS:
                c = A[lv][sc]["buckets"][bid]
                f1, f2 = c["follow"]["first"], c["follow"]["second"]
                if not f1["resolved"] or not f2["resolved"]:
                    cells.append("-")
                    continue
                cells.append("F %.0f/%.0f, X %.0f/%.0f (%d/%d)%s" % (
                    f1["hit_pct"], f2["hit_pct"], c["fade"]["first"]["hit_pct"], c["fade"]["second"]["hit_pct"],
                    f1["resolved"], f2["resolved"], " B" if (c["follow"]["bonf_both"] or c["fade"]["bonf_both"]) else ""))
            L.append("| %s | %s |" % (bid, " | ".join(cells)))
        L.append("")
    L += ["F = follow, X = fade; B = Bonferroni in both halves.", "", "## Checks", ""]
    for a, r in res.items():
        tc = r["truncation"]
        L.append("- %s: %d bars (%s to %s), fee %.2f%% a side; excluded %s; events without a read %s; regime truncation %d cuts, "
                 "%d mismatched arrays; R1 vs evidence.py recipe mismatches %d." % (
                     a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"],
                     "; ".join("%s %s" % (lv, ", ".join("%s %d" % kv for kv in ex.items())) for lv, ex in r["excluded"].items()),
                     "; ".join("%s %s" % (lv, ", ".join("%s %d" % kv for kv in nr.items())) for lv, nr in r["no_read"].items()),
                     tc["cuts"], tc["mismatched_arrays"], r["evidence_label_mismatches"]))
    L += ["", "Sanity: the follow reference above must equal H46's reference table (`research/out/confluence/study.md`).", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- live scan (paper / untested)
def scan(now_ms=None, cut=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if cut is None:
        try:
            cut = dict((k, tuple(v)) for k, v in load_study()["cutoffs"].items())
        except Exception:
            cut = None
    B = bucket_defs(cut) if cut else None
    lines = ["H47 live regime-split scan (PAPER, UNTESTED: regime buckets are not validated setups; see study.md)"]
    rows = []
    for a in ASSETS:
        try:
            df = data.load(a)
        except Exception as ex:
            lines.append("  %-8s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=700)]
        df = df[data.to_ms(df.index) + pb.BAR_MS <= now_ms]
        R = adr.readings(df, box=db.BOX)
        G = regimes(df)
        i = R["n"] - 1
        day = R["ms"] // DAY_MS
        last_close = pd.Timestamp(int(R["ms"][i]) + pb.BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - (int(R["ms"][i]) + pb.BAR_MS)) / 3600000.0
        g = regime_at(G, i)
        head = "  %-8s last close %s%s; regime %s, ADX %s, ER %s, vol pct %s, VR %s" % (
            a, last_close.strftime("%d %b %H:%M UTC"), " (stale %.1f h)" % age_h if age_h > 1 else "", g["label"],
            "-" if g["adx"] is None else "%.0f" % g["adx"], "-" if g["er"] is None else "%.2f" % g["er"],
            "-" if g["rvp"] is None else "%.2f" % g["rvp"], "-" if g["vr"] is None else "%.2f" % g["vr"])
        found = []
        for lv in LEVELS:
            dirs = db.daily_breaks(R, lv, False)
            for j in np.flatnonzero(dirs != 0):
                if day[j] != day[i]:
                    continue
                e = dict(regime_at(G, int(j)), side=int(dirs[j]))
                when = pd.Timestamp(int(R["ms"][j]) + pb.BAR_MS, unit="ms", tz="UTC").strftime("%H:%M UTC")
                inb = [b[0] for b in B if b[3](e)] if B else []
                found.append("%s %s at %s: %s" % (lv, "UP" if e["side"] > 0 else "DOWN", when, ", ".join(inb) or "no bucket"))
                rows.append({"asset": a, "level": lv, "side": e["side"], "close_utc": when, "buckets": inb, "regime": e})
        lines.append(head + ("\n             breaks today: " + "; ".join(found) if found else "\n             no daily-level break today yet"))
    lines.append("  (paper / untested; H47's verdict is in research/out/regime_split/study.md)")
    return rows, lines


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H47 regime split study")
    results, E = {}, []
    try:
        for a in ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a], ev = run_asset(a)
            E += ev
            log("%s: done in %.0f s; %d events; truncation %s; R1 vs evidence mismatches %d" % (
                a, time.time() - t0, len(ev), results[a]["truncation"], results[a]["evidence_label_mismatches"]))
    finally:
        release_lock()
    cut = cutoffs(E)
    B = bucket_defs(cut)
    A = aggregate(E, B)
    C = contrasts(A)
    T = trade_table(E, B)
    passes, rank = [], []
    for lv in LEVELS:
        for bid, fam, d, _fn in B:
            for sd in SIDES:
                c = A[lv]["pooled"]["buckets"][bid][sd]
                t = T["%s|%s|%s" % (lv, bid, sd)]
                if c["min_hit"] is not None and c["first"]["resolved"] >= MIN_RESOLVED and c["second"]["resolved"] >= MIN_RESOLVED:
                    rank.append((-c["min_hit"], lv, bid, sd))
                if c["hit_part"] and t["cost_part"]:
                    m = t["pooled"]["second"]
                    passes.append("%s / %s %s (%s) / %s: first %.1f%% of %d, second %.1f%% of %d; second-half trades %d, net $%.0f, "
                                  "%+.4f%% a trade, %d of 8 markets > 0, %.1f events / month" % (
                                      lv, bid, d, fam, sd, c["first"]["hit_pct"], c["first"]["resolved"], c["second"]["hit_pct"],
                                      c["second"]["resolved"], m["trades"], m["net_usd"], m["exp_pct"], t["markets_positive_second"],
                                      t["per_month"]["second"]))
    best = None
    if rank:
        _x, lv, bid, sd = sorted(rank)[0]
        c = A[lv]["pooled"]["buckets"][bid][sd]
        best = "%s / %s / %s: lower half %.1f%% (first %.1f%% of %d, second %.1f%% of %d)" % (
            lv, bid, sd, c["min_hit"], c["first"]["hit_pct"], c["first"]["resolved"], c["second"]["hit_pct"], c["second"]["resolved"])
    nb = sum(1 for lv in LEVELS for sc in SCOPES for bb in A[lv][sc]["buckets"].values() for sd in SIDES if bb[sd]["bonf_both"])
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC, "n_tests": N_TESTS,
         "alpha": ALPHA, "alpha_diff": ALPHA_DIFF, "cutoffs": cut, "buckets": [(b[0], b[1], b[2]) for b in B], "agg": A,
         "contrasts": C, "trades": T, "passes": passes, "best": best, "bonf_both_count": nb, "results": results,
         "events": len(E)}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("done: %d events, %d passes, %d Bonferroni-both cells, %d significant primary contrasts" % (
        len(E), len(passes), nb, sum(1 for r in C if r["significant_both"])))
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
        print("\n".join(scan()[1]))
    else:
        main()
        print("\n".join(scan()[1]))
