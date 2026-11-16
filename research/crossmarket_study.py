# -*- coding: utf-8 -*-
"""H51 CROSS-MARKET CONFIRMATION at a daily-level break. PAPER RESEARCH ONLY.

Registered before any code or outcome: research/hypotheses_pending/H51.md (16 Nov 2026, 09:50 UTC). In short:
  * events and outcome = H46/H47: the first 15m close beyond the prior UTC day's high/low (pday) or the previous 96
    bars' high/low (roll24) per UTC day per direction (dailybreak_study.daily_breaks, momentum OFF); follow hit =
    +0.5 daily ATR before -0.5 from the next open within 72 h (confluence_study.outcome), fade = the mirror;
  * the partner reading: the partner market's bars that CLOSE in (T - 60 min, T], T = the event bar's close (only bars
    closed by the event's close). Confirmed = a partner close beyond its own same-type level in direction r x s;
    divergent = not confirmed and the partner moved r x s x m <= -1.0 ATR15 over the window; unconfirmed = neither;
    no read = no partner bar in the window;
  * pairs P1 BTC<->ETH, P2 XAU<->XAG, P3 WTI<->BRENT, P4 XAU vs USDJPY (inverse), P5 SPX vs BTC, P6 WTI vs SPX;
    variants V1-V6 = P1-P6 on pday, V7 = all pairs pday "any partner", V8 = V7 on roll24;
  * 8 variants x 3 buckets x 2 sides = 48 tests per half, Bonferroni 0.05/48; pass bar as H47 with a majority of the
    variant's markets positive after costs in the second half;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

    python research/crossmarket_study.py            (run, write research/out/crossmarket/study.json + study.md)
    python research/crossmarket_study.py --report   (rewrite study.md from study.json)
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

from engine15 import playbook as pb  # noqa: E402
from engine15.sources import adr  # noqa: E402

from liqhunt2_study import log, ms_of  # noqa: E402
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402
import confluence_study as cb  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 09:50 UTC"
ASSETS = rb.ASSETS
OUT = os.path.join(ROOT, "research", "out", "crossmarket")
BAR_MS, DAY_MS = pb.BAR_MS, 86400000
N_BARS, X_ATR = 4, 1.0
LEVELS = ("pday", "roll24")
SIDES = ("follow", "fade")
BUCKETS = ("confirmed", "unconfirmed", "divergent")

PAIRS = {"P1": ("BTCUSDT", "ETHUSDT", 1), "P2": ("XAUUSD", "XAGUSD", 1), "P3": ("WTI", "BRENT", 1),
         "P4": ("XAUUSD", "USDJPY", -1), "P5": ("SPX", "BTCUSDT", 1), "P6": ("WTI", "SPX", 1)}
PAIR_NAME = {"P1": "BTC <-> ETH", "P2": "XAU <-> XAG", "P3": "WTI <-> BRENT", "P4": "XAU vs USDJPY (inverse)",
             "P5": "SPX vs BTC (risk-on)", "P6": "WTI vs SPX (oil / risk)"}
VARIANTS = {"V1": ("P1", "pday"), "V2": ("P2", "pday"), "V3": ("P3", "pday"), "V4": ("P4", "pday"),
            "V5": ("P5", "pday"), "V6": ("P6", "pday"), "V7": ("ALL", "pday"), "V8": ("ALL", "roll24")}
N_TESTS = len(VARIANTS) * len(BUCKETS) * len(SIDES)            # 48
ALPHA = 0.05 / N_TESTS
N_CONTRASTS = len(VARIANTS)
ALPHA_C = 0.05 / N_CONTRASTS
MIN_RESOLVED, PASS_HIT = 200, 55.0


def partners_of(asset):
    """-> [(pair id, partner, relation)] for every pair the asset is in (each pair used both ways)."""
    out = []
    for pid, (a, b, r) in PAIRS.items():
        if asset == a:
            out.append((pid, b, r))
        elif asset == b:
            out.append((pid, a, r))
    return out


def variant_markets(v):
    pid, _lv = VARIANTS[v]
    return list(ASSETS) if pid == "ALL" else [PAIRS[pid][0], PAIRS[pid][1]]


# ---------------------------------------------------------------- the partner reading (truncation-tested)
def partner_frame(RB, level):
    """Partner readings -> the arrays the partner reading needs (all known at each partner bar's close)."""
    hi, lo = (RB["pdh"], RB["pdl"]) if level == "pday" else (RB["box_hi"], RB["box_lo"])
    c = RB["c"]
    with np.errstate(invalid="ignore"):
        up = np.nan_to_num(c > hi).astype(bool) & np.isfinite(hi)
        dn = np.nan_to_num(c < lo).astype(bool) & np.isfinite(lo)
    return {"ms": RB["ms"], "o": RB["o"], "c": c, "atr": RB["atr15"],
            "cum_up": np.concatenate([[0], np.cumsum(up)]), "cum_dn": np.concatenate([[0], np.cumsum(dn)])}


def partner_reading(PB, ms_i, want, n_bars=N_BARS, x=X_ATR):
    """Event bar opening at ms_i (close T = ms_i + 15 min); want = r x s (+1: partner should break up, -1 down).
    Window = partner bars with open in (ms_i - n_bars x 15 min, ms_i] (they close in (T - n_bars x 15 min, T]).
    -> dict(status in {"noread", "confirmed", "divergent", "unconfirmed"}, move_atr, both)."""
    ms = PB["ms"]
    lo = int(np.searchsorted(ms, ms_i - n_bars * BAR_MS, side="right"))
    hi = int(np.searchsorted(ms, ms_i, side="right"))
    if hi <= lo:
        return {"status": "noread", "move_atr": None, "both": False}
    a = PB["atr"][hi - 1]
    cum = PB["cum_up"] if want > 0 else PB["cum_dn"]
    conf = bool(cum[hi] - cum[lo] > 0)
    if not (a == a and a > 0):
        return {"status": "confirmed" if conf else "noread", "move_atr": None, "both": False}
    m = want * (PB["c"][hi - 1] - PB["o"][lo]) / a
    div = bool(m <= -x)
    st = "confirmed" if conf else ("divergent" if div else "unconfirmed")
    return {"status": st, "move_atr": float(m), "both": bool(conf and div)}


def combine(statuses):
    """V7/V8 'any partner' rule -> status in {"noread", "confirmed", "divergent", "unconfirmed", "mixed"}."""
    s = set(statuses)
    if s <= {"noread"}:
        return "noread"
    c, d = "confirmed" in s, "divergent" in s
    if c and d:
        return "mixed"
    if c:
        return "confirmed"
    if d:
        return "divergent"
    return "unconfirmed"


# ---------------------------------------------------------------- events with outcomes
def events(R, level):
    """-> list of event dicts with follow and fade outcomes (H46's outcome, the fade with the side flipped)."""
    dirs = db.daily_breaks(R, level, False)
    D, ms = R["datr"], R["ms"]
    out, excl = [], 0
    for i in np.flatnonzero(dirs != 0):
        if not (D[i] == D[i] and D[i] > 0):
            continue
        s = int(dirs[i])
        fo = cb.outcome(R, int(i), s, float(D[i]))
        if fo is None:
            excl += 1
            continue
        fa = cb.outcome(R, int(i), -s, float(D[i]))
        e = {"i": int(i), "ms": int(ms[i]), "side": s, "datr": float(D[i]), "entry_ms": int(ms[fo["e"]])}
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
    return out, excl


def read_events(evs, frames, partners, level):
    """Attach the partner reading per pair (and the V7 'any partner' status) to each event, in place."""
    for e in evs:
        sts = []
        for pid, b, r in partners:
            pr = partner_reading(frames[(b, level)], e["ms"], r * e["side"])
            e["p_" + pid] = pr["status"]
            e["m_" + pid] = pr["move_atr"]
            e["both_" + pid] = pr["both"]
            sts.append(pr["status"])
        e["p_ALL"] = combine(sts)
    return evs


def reading_key(evs, pids):
    return [(e["i"], e["side"]) + tuple((e["p_" + p], None if e["m_" + p] is None else round(e["m_" + p], 9)) for p in pids)
            + (e["p_ALL"],) for e in evs]


# ---------------------------------------------------------------- truncation check on the real bars
def truncation_check(dfs, asset, level, cuts_frac=(0.6, 0.97)):
    """Partner readings of asset's events with (a) the event frame and every partner frame truncated at the same clock
    time, (b) only the partners truncated to bars opening at or before the event bar's open -> identical to full."""
    partners = partners_of(asset)
    pids = [p for p, _b, _r in partners]
    full_frames = dict(((b, level), partner_frame(adr.readings(dfs[b], box=db.BOX), level)) for _p, b, _r in partners)
    RA = adr.readings(dfs[asset], box=db.BOX)
    full = reading_key(read_events(events(RA, level)[0], full_frames, partners, level), pids)
    bad, checked = 0, 0
    A = dfs[asset]
    for fr in cuts_frac:
        cut_ts = A.index[int(len(A) * fr)]
        pa = A[A.index < cut_ts]
        pf = dict(((b, level), partner_frame(adr.readings(dfs[b][dfs[b].index < cut_ts], box=db.BOX), level))
                  for _p, b, _r in partners)
        # events whose 72 h outcome is complete before the cut are identical; compare the partner part only
        evp = read_events(events(adr.readings(pa, box=db.BOX), level)[0], pf, partners, level)
        part = dict((k[0], k) for k in reading_key(evp, pids))
        for k in full:
            if k[0] < len(pa) - 1:                      # the last bar has no entry bar in the truncated frame
                checked += 1
                if part.get(k[0]) != k:
                    bad += 1
    # (b) partner truncated per event, sampled
    evs = read_events(events(RA, level)[0], full_frames, partners, level)
    samp = evs[:: max(1, len(evs) // 25)]
    for e in samp:
        for pid, b, r in partners:
            B = dfs[b]
            pb_ = partner_frame(adr.readings(B[B.index <= pd.Timestamp(e["ms"], unit="ms", tz="UTC")], box=db.BOX), level)
            pr = partner_reading(pb_, e["ms"], r * e["side"])
            checked += 1
            if pr["status"] != e["p_" + pid] or (pr["move_atr"] is not None and abs(pr["move_atr"] - e["m_" + pid]) > 1e-9):
                bad += 1
    return {"compared": checked, "mismatched": bad}


# ---------------------------------------------------------------- aggregation
def diff_test(k1, n1, k2, n2):
    """Two-proportion z test (pooled variance), two-sided -> (difference in points, p). (H47's.)"""
    if not n1 or not n2:
        return None, None
    p1, p2 = k1 / float(n1), k2 / float(n2)
    pp = (k1 + k2) / float(n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1.0 / n1 + 1.0 / n2))
    if se <= 0:
        return round(100 * (p1 - p2), 2), None
    z = (p1 - p2) / se
    return round(100 * (p1 - p2), 2), float(math.erfc(abs(z) / math.sqrt(2.0)))


def cell(evs, side):
    h = "hit" if side == "follow" else "f_hit"
    res = [e for e in evs if e[h] is not None]
    k = int(sum(e[h] for e in res))
    m = len(res)
    return {"events": len(evs), "resolved": m, "hits": k, "unresolved": len(evs) - m,
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": cb.binom_p(k, m) if m else None}


def variant_rows(E, v):
    """-> list of (event, status) for variant v (each event once)."""
    pid, lv = VARIANTS[v]
    mk = variant_markets(v)
    key = "p_" + pid
    return [(e, e[key]) for e in E if e["level"] == lv and e["asset"] in mk and key in e]


def side_view(e, side):
    pre = "" if side == "follow" else "f_"
    return {"i": e["i"], "side": e["side"] if side == "follow" else -e["side"], "entry_ms": e["entry_ms"],
            "exit_ms": e[pre + "exit_ms"], "why": e[pre + "why"], "entry": e[pre + "entry"], "stop": e[pre + "stop"],
            "exit": e[pre + "exit"], "exit_bar": e[pre + "exit_bar"]}


def months(half):
    a, b = (START, SPLIT) if half == "first" else (SPLIT, SEAL)
    return (ms_of(b) - ms_of(a)) / (DAY_MS * 30.4375)


def trades(sel, side, markets):
    split_ms = ms_of(SPLIT)
    node = {"pooled": {}, "markets": {}}
    allt = []
    for a in markets:
        ev = sorted([side_view(e, side) for e in sel if e["asset"] == a], key=lambda x: x["i"])
        tr = cb.trades_of(ev, pb.fee_side(a))
        allt += tr
        node["markets"][a] = dict((hf, db.metrics([t for t in tr if (t["entry_ms"] < split_ms) == (hf == "first")]))
                                  for hf in ("first", "second"))
    for hf in ("first", "second"):
        node["pooled"][hf] = db.metrics([t for t in allt if (t["entry_ms"] < split_ms) == (hf == "first")])
    pos = [a for a in markets if node["markets"][a]["second"].get("trades") and node["markets"][a]["second"]["net_usd"] > 0]
    node["markets_positive_second"] = pos
    node["majority_needed"] = len(markets) // 2 + 1
    node["cost_ok"] = bool(node["pooled"]["second"].get("trades") and node["pooled"]["second"]["net_usd"] > 0
                           and len(pos) >= node["majority_needed"])
    return node


def aggregate(E):
    A = {}
    for v in VARIANTS:
        pid, lv = VARIANTS[v]
        rows = variant_rows(E, v)
        mk = variant_markets(v)
        node = {"pair": pid, "level": lv, "markets": mk, "counts": {}, "reference": {}, "buckets": {}, "trades": {},
                "per_market": {}, "per_month": {}}
        for hf in ("first", "second"):
            hrows = [(e, st) for e, st in rows if e["half"] == hf]
            node["counts"][hf] = dict((st, sum(1 for _e, s in hrows if s == st))
                                      for st in ("noread", "mixed") + BUCKETS)
            node["counts"][hf]["events"] = len(hrows)
            if pid != "ALL":
                node["counts"][hf]["confirmed_and_divergent"] = sum(1 for e, _s in hrows if e.get("both_" + pid))
            read = [e for e, s in hrows if s in BUCKETS]
            node["reference"][hf] = dict((sd, cell(read, sd)) for sd in SIDES)
        for b in BUCKETS:
            sel = [e for e, s in rows if s == b]
            node["buckets"][b] = {}
            node["per_month"][b] = dict((hf, round(len([e for e in sel if e["half"] == hf]) / months(hf), 2))
                                        for hf in ("first", "second"))
            for sd in SIDES:
                cells = dict((hf, cell([e for e in sel if e["half"] == hf], sd)) for hf in ("first", "second"))
                c1, c2 = cells["first"], cells["second"]
                okn = c1["resolved"] >= MIN_RESOLVED and c2["resolved"] >= MIN_RESOLVED
                cells["hit_ok"] = bool(okn and c1["hit_pct"] >= PASS_HIT and c2["hit_pct"] >= PASS_HIT)
                cells["n_ok"] = bool(okn)
                cells["bonf_both"] = bool(c1["p"] is not None and c2["p"] is not None and c1["p"] < ALPHA and c2["p"] < ALPHA)
                tnode = trades(sel, sd, mk)
                node["trades"]["%s|%s" % (b, sd)] = tnode
                cells["cost_ok"] = tnode["cost_ok"]
                cells["pass"] = bool(cells["hit_ok"] and cells["bonf_both"] and cells["cost_ok"])
                node["buckets"][b][sd] = cells
            node["per_market"][b] = dict((a, dict((hf, cell([e for e in sel if e["asset"] == a and e["half"] == hf], "follow"))
                                                  for hf in ("first", "second"))) for a in mk)
        # secondary: confirmed-follow minus divergent-follow
        con = {}
        for hf in ("first", "second"):
            c, d = node["buckets"]["confirmed"]["follow"][hf], node["buckets"]["divergent"]["follow"][hf]
            diff, p = diff_test(c["hits"], c["resolved"], d["hits"], d["resolved"])
            con[hf] = {"diff_pts": diff, "p": p}
        con["matters"] = bool(con["first"]["p"] is not None and con["second"]["p"] is not None
                              and con["first"]["p"] < ALPHA_C and con["second"]["p"] < ALPHA_C
                              and (con["first"]["diff_pts"] > 0) == (con["second"]["diff_pts"] > 0))
        node["contrast"] = con
        A[v] = node
    return A


def union_reference(E):
    out = {}
    for lv in LEVELS:
        out[lv] = dict((hf, cell([e for e in E if e["level"] == lv and e["half"] == hf], "follow")) for hf in ("first", "second"))
    return out


# ---------------------------------------------------------------- report
def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | -"
    p = c["p"]
    return "%.1f%% | %d | %s" % (c["hit_pct"], c["resolved"], ("%.1e" % p) if p < 0.001 else ("%.3f" % p))


def fmt_tr(m):
    if not m or not m.get("trades"):
        return "0 | | | | | "
    return "%d | %.1f%% | %+.3f | %+.3f | %+.4f%% | %s" % (m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"],
                                                         m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


def report(S):
    A, res = S["agg"], S["results"]
    passes = S["passes"]
    L = ["# H51: cross-market confirmation at a daily-level break", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/hypotheses_pending/H51.md`) before any outcome. Development data "
         "only (rows before %s 00:00 UTC; the holdout was not read). Events with entry from %s; first half before %s. "
         "Written %s." % (REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Event = the first 15m close beyond the level in its UTC day per direction (H45/H46 code). Follow hit = +0.5 daily "
         "ATR before -0.5 from the next 15m open within 72 h (a bar touching both = miss; neither = unresolved, excluded); "
         "fade = the mirror. Partner window = the partner's bars closing in (T - 60 min, T], T = the event bar's close. "
         "Confirmed = a partner close beyond its own same-type level in the expected direction (inverse for USDJPY vs XAU); "
         "divergent = not confirmed and the partner moved the other way by >= 1.0 of its own ATR15 over the window; "
         "unconfirmed = neither; no read = no partner bar in the window. p = exact two-sided binomial vs 50%%. Tests: %d "
         "variants x %d buckets x %d sides = **%d** per half; Bonferroni p < %.2e." % (
             len(VARIANTS), len(BUCKETS), len(SIDES), N_TESTS, ALPHA), "",
         "Pairs: " + "; ".join("%s %s" % (p, PAIR_NAME[p]) for p in PAIRS) + ".", "",
         "Variants: " + "; ".join("%s = %s %s" % (v, "all pairs (any partner)" if pid == "ALL" else "%s %s" % (pid, PAIR_NAME[pid]), lv)
                                  for v, (pid, lv) in VARIANTS.items()) + ".", ""]
    L += ["## Verdict: %s" % ("PASS (%d)" % len(passes) if passes else "NO PASS"), ""]
    for p in passes:
        L.append("- %s" % p)
    if not passes:
        L.append("No variant / bucket / side met all of: >= %.0f%% in both halves, >= %d resolved per half, p < %.2e in "
                 "both halves, net > 0 after costs in the second half pooled and in a majority of its markets." % (
                     PASS_HIT, MIN_RESOLVED, ALPHA))
    L += ["", "Cells passing Bonferroni in both halves (any direction): %d of %d. Cells with >= 55%% in both halves and "
          ">= %d resolved: %d. Cells passing the cost part: %d." % (S["n_bonf"], N_TESTS, MIN_RESOLVED, S["n_hit"], S["n_cost"]), ""]
    u = S["union"]
    L += ["Sanity (union of all events, follow): pday %s / %s; roll24 %s / %s (first / second: hit | n | p)." % (
        _h(u["pday"]["first"]), _h(u["pday"]["second"]), _h(u["roll24"]["first"]), _h(u["roll24"]["second"])), ""]
    L += ["## Hit rates per variant, bucket and side", "",
          "| variant | bucket | side | first: hit | n | p | second: hit | n | p | Bonf. both | >=55% & n | cost ok | events / month 1st / 2nd |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v, node in A.items():
        for sd in SIDES:
            r = node["reference"]
            L.append("| %s | reference (all read) | %s | %s | %s | | | | |" % (v, sd, _h(r["first"][sd]), _h(r["second"][sd])))
        for b in BUCKETS:
            for sd in SIDES:
                c = node["buckets"][b][sd]
                pm = node["per_month"][b]
                L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %.1f / %.1f |" % (
                    v, b, sd, _h(c["first"]), _h(c["second"]), "yes" if c["bonf_both"] else "",
                    "yes" if c["hit_ok"] else "", "yes" if c["cost_ok"] else "", pm["first"], pm["second"]))
    L += ["", "## Counts per variant (events by partner status, first / second half)", "",
          "| variant | events | no read | confirmed | unconfirmed | divergent | mixed (V7/V8) | confirmed and moved >= 1 ATR15 the other way |",
          "|---|---|---|---|---|---|---|---|"]
    for v, node in A.items():
        c1, c2 = node["counts"]["first"], node["counts"]["second"]
        L.append("| %s | %d / %d | %d / %d | %d / %d | %d / %d | %d / %d | %d / %d | %s |" % (
            v, c1["events"], c2["events"], c1["noread"], c2["noread"], c1["confirmed"], c2["confirmed"],
            c1["unconfirmed"], c2["unconfirmed"], c1["divergent"], c2["divergent"], c1["mixed"], c2["mixed"],
            ("%d / %d" % (c1["confirmed_and_divergent"], c2["confirmed_and_divergent"])) if "confirmed_and_divergent" in c1 else "-"))
    L += ["", "## Secondary: confirmed-follow minus divergent-follow (points, two-proportion z; 'matters' needs the same "
          "sign and p < %.4f in both halves)" % ALPHA_C, "", "| variant | first: diff | p | second: diff | p | matters |",
          "|---|---|---|---|---|---|"]
    for v, node in A.items():
        c = node["contrast"]
        f = lambda x: "-" if x is None else ("%+.1f" % x)  # noqa: E731
        g = lambda x: "-" if x is None else ("%.4f" % x)  # noqa: E731
        L.append("| %s | %s | %s | %s | %s | %s |" % (v, f(c["first"]["diff_pts"]), g(c["first"]["p"]), f(c["second"]["diff_pts"]),
                                                     g(c["second"]["p"]), "yes" if c["matters"] else "no"))
    L += ["", "## After costs: every bucket traded (stop and target 0.5 dATR, 72 h max, own fee a side, one position per "
          "market)", "", "| variant | bucket | side | half | trades | won | R before costs | R after costs | per trade (% stake) | net $ | markets net > 0 (2nd) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v, node in A.items():
        for b in BUCKETS:
            for sd in SIDES:
                t = node["trades"]["%s|%s" % (b, sd)]
                for hf in ("first", "second"):
                    L.append("| %s | %s | %s | %s | %s | %s |" % (
                        v if hf == "first" else "", b if hf == "first" else "", sd if hf == "first" else "", hf,
                        fmt_tr(t["pooled"][hf]),
                        ("%d of %d (need %d): %s" % (len(t["markets_positive_second"]), len(node["markets"]), t["majority_needed"],
                                                      ", ".join(t["markets_positive_second"]) or "none")) if hf == "second" else ""))
    L += ["", "## Per event market inside each variant (follow hit, first / second half: hit (resolved))", ""]
    for v, node in A.items():
        L += ["### %s" % v, "", "| market | " + " | ".join(BUCKETS) + " |", "|---|---|---|---|"]
        for a in node["markets"]:
            cells = []
            for b in BUCKETS:
                pm = node["per_market"][b][a]
                cells.append(" / ".join(("%.1f%% (%d)" % (pm[hf]["hit_pct"], pm[hf]["resolved"])) if pm[hf]["resolved"] else "- (0)"
                                        for hf in ("first", "second")))
            L.append("| %s | %s |" % (a, " | ".join(cells)))
        L.append("")
    L += ["## Checks", ""]
    for a, r in res.items():
        L.append("- %s: %d bars (%s to %s), fee %.2f%% a side; events pday %d, roll24 %d (no same-day entry excluded: %s); "
                 "partner-reading truncation: %s." % (
                     a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], r["events"]["pday"],
                     r["events"]["roll24"], r["excluded"],
                     "; ".join("%s %d compared, %d mismatched" % (lv, t["compared"], t["mismatched"]) for lv, t in r["truncation"].items())))
    L += ["", "Partners are read only from bars that closed by the event bar's close. Markets shut at different hours, so "
          "'no read' is common for pairs with SPX (cash hours) and for weekend crypto events against metals / oil / fx.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- main
def run(assets=ASSETS, truncation=True):
    dfs = {}
    for a in assets:
        dfs[a] = rb.load_dev(a)
        log("%s: %d dev bars" % (a, len(dfs[a])))
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    Rs = dict((a, adr.readings(dfs[a], box=db.BOX)) for a in assets)
    frames = dict(((a, lv), partner_frame(Rs[a], lv)) for a in assets for lv in LEVELS)
    E, results = [], {}
    for a in assets:
        partners = [p for p in partners_of(a) if p[1] in dfs]
        res = {"bars": int(len(dfs[a])), "first_bar": str(dfs[a].index[0]), "last_bar": str(dfs[a].index[-1]),
               "fee_side": pb.fee_side(a), "events": {}, "excluded": {}, "truncation": {}}
        for lv in LEVELS:
            evs, excl = events(Rs[a], lv)
            evs = [e for e in evs if e["entry_ms"] >= start_ms]
            read_events(evs, frames, partners, lv)
            for e in evs:
                e.update(asset=a, level=lv, half="first" if e["entry_ms"] < split_ms else "second")
            E += evs
            res["events"][lv] = len(evs)
            res["excluded"][lv] = excl
            if truncation:
                res["truncation"][lv] = truncation_check(dfs, a, lv)
        results[a] = res
        log("%s: events pday %d roll24 %d; truncation %s" % (a, res["events"]["pday"], res["events"]["roll24"], res["truncation"]))
    return E, results


def main():
    os.makedirs(OUT, exist_ok=True)
    E, results = run()
    A = aggregate(E)
    passes, n_bonf, n_hit, n_cost = [], 0, 0, 0
    for v, node in A.items():
        for b in BUCKETS:
            for sd in SIDES:
                c = node["buckets"][b][sd]
                n_bonf += c["bonf_both"]
                n_hit += c["hit_ok"]
                n_cost += c["cost_ok"]
                if c["pass"]:
                    passes.append("%s %s %s: first %.1f%% of %d, second %.1f%% of %d" % (
                        v, b, sd, c["first"]["hit_pct"], c["first"]["resolved"], c["second"]["hit_pct"], c["second"]["resolved"]))
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC, "n_tests": N_TESTS,
         "alpha": ALPHA, "pairs": PAIRS, "variants": VARIANTS, "N_bars": N_BARS, "X_atr": X_ATR, "agg": A,
         "union": union_reference(E), "passes": passes, "n_bonf": n_bonf, "n_hit": n_hit, "n_cost": n_cost, "results": results}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("done: %d events, passes %d, Bonferroni-both %d" % (len(E), len(passes), n_bonf))
    return S


if __name__ == "__main__":
    if "--report" in sys.argv:
        with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
            S = json.load(fh)
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(S))
    else:
        main()
