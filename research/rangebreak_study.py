# -*- coding: utf-8 -*-
"""H44 range breaks with momentum, read against the daily ATR budget ("eagle view"). PAPER RESEARCH ONLY.

Registered before any code or number: research/HYPOTHESES.md H44 (16 Nov 2026, 04:40 UTC). In short:
  * eight markets, rows before the sealed holdout 2025-11-11 00:00 UTC only (later rows dropped right after loading);
  * trades from 2020-01-01 by entry time; first half before 2023-06-07, second half from it to the seal;
  * the readings are engine15/sources/adr.py's (`readings`, `breaks`): one definition for the study and the card;
  * the trade is playbook.simulate unchanged (next open, stop 1 x ATR15 from the break close, half 1R / rest 2R or the
    day's room level, break-even after 1R, hold 16 bars, the market's own fee a side);
  * selection on the first half among V1-V6; pass bar on the second half against the chosen variant's no-eagle twin.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market.

    py -3 research/rangebreak_study.py            (run, write study.json + study.md, then print the live scan)
    py -3 research/rangebreak_study.py --report   (rewrite study.md from study.json)
    py -3 research/rangebreak_study.py --scan     (the live setup scan only: latest closed bars, paper)
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

START, SPLIT, SEAL = "2020-01-01", "2023-06-07", "2025-11-11"
REGISTERED_UTC = "2026-11-16 04:40 UTC"
ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")
OUT = os.path.join(ROOT, "research", "out", "rangebreak")
NEED_MB = 1500
HOLD = 16
STOP_ATR = 1.0
MIN_TRADES_ASSET, MIN_TRADES_ALL, MIN_TRADES_PASS = 20, 100, 100
PASS_MARKETS, PASS_PF = 5, 1.1
HORIZONS = (4, 8, 16)

# id: (range kind, box bars, k, daily filter, exit, selectable)
VARIANTS = {
    "V1": {"kind": "box", "box": 24, "k": 1.5, "filter": "room", "exit": "E1", "select": True},
    "V2": {"kind": "box", "box": 24, "k": 2.0, "filter": "room", "exit": "E1", "select": True},
    "V3": {"kind": "box", "box": 12, "k": 1.5, "filter": "room", "exit": "E1", "select": True},
    "V4": {"kind": "pday", "box": 24, "k": 1.5, "filter": "room", "exit": "E1", "select": True},
    "V5": {"kind": "or", "box": 24, "k": 1.5, "filter": "room", "exit": "E1", "select": True},
    "V6": {"kind": "box", "box": 24, "k": 1.5, "filter": "room", "exit": "Eroom", "select": True},
    "V7": {"kind": "box", "box": 24, "k": 1.5, "filter": "exhausted", "exit": "E1", "select": False},
    "V8": {"kind": "box", "box": 24, "k": 1.5, "filter": "none", "exit": "E1", "select": False},
}
TWINS = dict(("%s_twin" % v, dict(VARIANTS[v], filter="none", select=False)) for v in ("V2", "V3", "V4", "V5", "V6"))
TWIN_OF = {"V1": "V8", "V2": "V2_twin", "V3": "V3_twin", "V4": "V4_twin", "V5": "V5_twin", "V6": "V6_twin"}
ALL = dict(VARIANTS, **TWINS)
ORDER = list(VARIANTS) + list(TWINS)
# descriptive event sets: (label, kind, box, k)
EVENT_SETS = [("box24 k1.5", "box", 24, 1.5), ("box24 k2.0", "box", 24, 2.0), ("box12 k1.5", "box", 12, 1.5),
              ("prior day k1.5", "pday", 24, 1.5), ("opening range k1.5", "or", 24, 1.5)]
BUCKETS = ("room left", "middle", "exhausted")

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402  (same lock, same log format)


def vdesc(v):
    rng = {"box": "last %d bars" % v["box"], "pday": "prior UTC day", "or": "opening range (first 4 bars)"}[v["kind"]]
    flt = {"room": "room-left (used < 0.65)", "exhausted": "exhausted (used >= 1.0)", "none": "no daily filter"}[v["filter"]]
    ex = "half 1R / rest 2R" if v["exit"] == "E1" else "half 1R / rest at the day's room level"
    return "%s, k %.1f, %s, %s" % (rng, v["k"], flt, ex)


# ---------------------------------------------------------------- signals (the function the truncation test checks)
def signals(R, var, Rbox=None):
    """R: adr.readings(bars, box=var['box']) -> list of sig dicts for playbook.simulate, oldest first. Everything a
    signal holds is known at the close of its decision bar i_dec."""
    br = adr.breaks(R, var["kind"], var["k"])
    used, atr, c = R["used"], R["atr15"], R["c"]
    with np.errstate(invalid="ignore"):
        if var["filter"] == "room":
            ok = used < adr.ROOM_LEFT
        elif var["filter"] == "exhausted":
            ok = used >= adr.EXHAUSTED
        else:
            ok = np.ones(len(c), dtype=bool)
        ok = ok & np.isfinite(atr) & (atr > 0) & (br != 0)
    level = {"box": (R["box_hi"], R["box_lo"]), "pday": (R["pdh"], R["pdl"]), "or": (R["or_hi"], R["or_lo"])}[var["kind"]]
    sigs = []
    for i in np.flatnonzero(ok):
        s = int(br[i])
        room_px = (R["day_low"][i] + R["datr"][i]) if s > 0 else (R["day_high"][i] - R["datr"][i])
        sigs.append({"book": "h44", "i_dec": int(i), "i_start": int(i), "side": s, "pool": var["kind"],
                     "level": float(level[0][i] if s > 0 else level[1][i]), "extreme": float(c[i]),
                     "stop": float(c[i] - s * STOP_ATR * atr[i]), "used": float(used[i]) if used[i] == used[i] else None,
                     "t1_cands": [], "t2_cand": ("day room", float(room_px))})
    return sigs


def frame_of(R):
    return {"n": R["n"], "o": R["o"], "h": R["h"], "l": R["l"], "c": R["c"], "ms": R["ms"]}


def run_variant(Rs, var, fee):
    R = Rs[var["box"]]
    return pb.simulate(frame_of(R), signals(R, var), "fixed" if var["exit"] == "E1" else "struct", HOLD, fee)


# ---------------------------------------------------------------- descriptive statistics (pre-cost, events)
def event_stats(R, dirs, start_ms):
    """dirs: +1/-1/0 per bar. -> per (half, bucket): counts and forward statistics in ATR15 units."""
    n, o, h, l, c, ms, A, used = R["n"], R["o"], R["h"], R["l"], R["c"], R["ms"], R["atr15"], R["used"]
    idx = np.flatnonzero((dirs != 0) & np.isfinite(A) & (A > 0) & (ms + pb.BAR_MS >= start_ms))
    idx = idx[idx + HOLD < n]
    out = {}
    if not len(idx):
        return out
    s = dirs[idx].astype(float)
    a = A[idx]
    entry = o[idx + 1]
    fwd = dict((hh, s * (c[idx + hh] - entry) / a) for hh in HORIZONS)
    fwd_pct = dict((hh, 100.0 * s * (c[idx + hh] - entry) / entry) for hh in HORIZONS)
    win = np.arange(1, HOLD + 1)
    H, L = h[idx[:, None] + win], l[idx[:, None] + win]
    up_ex = (H.max(axis=1) - entry) / a
    dn_ex = (entry - L.min(axis=1)) / a
    mfe = np.where(s > 0, up_ex, dn_ex)
    mae = np.where(s > 0, dn_ex, up_ex)
    fav = np.where(s[:, None] > 0, H >= entry[:, None] + a[:, None], L <= entry[:, None] - a[:, None])
    adv = np.where(s[:, None] > 0, L <= entry[:, None] - a[:, None], H >= entry[:, None] + a[:, None])
    big = HOLD + 1
    f_first = np.where(fav.any(axis=1), fav.argmax(axis=1), big)
    a_first = np.where(adv.any(axis=1), adv.argmax(axis=1), big)
    win1 = f_first < a_first                                             # same bar = loss
    neither = (f_first == big) & (a_first == big)
    u = used[idx]
    bk = np.where(~np.isfinite(u), "no read", np.where(u < adr.ROOM_LEFT, "room left",
                                                       np.where(u >= adr.EXHAUSTED, "exhausted", "middle")))
    half = np.where(ms[idx] + pb.BAR_MS < ms_of(SPLIT), "first", "second")
    for hf in ("first", "second", "all"):
        for b in BUCKETS + ("all",):
            m = np.ones(len(idx), dtype=bool)
            if hf != "all":
                m &= half == hf
            if b != "all":
                m &= bk == b
            out[(hf, b)] = {"n": int(m.sum()), "sum": _sums(m, fwd, fwd_pct, mfe, mae, win1, neither)}
    return out


def _sums(m, fwd, fwd_pct, mfe, mae, win1, neither):
    d = {"n": int(m.sum())}
    for hh in HORIZONS:
        d["f%d" % hh] = float(fwd[hh][m].sum())
        d["p%d" % hh] = float(fwd_pct[hh][m].sum())
        d["pos%d" % hh] = int((fwd[hh][m] > 0).sum())
    d["mfe"], d["mae"] = float(mfe[m].sum()), float(mae[m].sum())
    d["win1"], d["neither"] = int(win1[m].sum()), int(neither[m].sum())
    return d


def merge_sums(parts):
    tot = {}
    for p in parts:
        for k, v in p.items():
            tot[k] = tot.get(k, 0) + v
    return tot


def finish(s):
    n = s.get("n", 0)
    if not n:
        return {"n": 0}
    out = {"n": n}
    for hh in HORIZONS:
        out["fwd%d_atr" % hh] = round(s["f%d" % hh] / n, 3)
        out["fwd%d_pct" % hh] = round(s["p%d" % hh] / n, 4)
        out["up%d_pct" % hh] = round(100.0 * s["pos%d" % hh] / n, 1)
    out["mfe_atr"], out["mae_atr"] = round(s["mfe"] / n, 3), round(s["mae"] / n, 3)
    res = n - s["neither"]
    out["hit1_pct"] = round(100.0 * s["win1"] / res, 1) if res else None
    out["neither_pct"] = round(100.0 * s["neither"] / n, 1)
    return out


# ---------------------------------------------------------------- per market
def load_dev(asset):
    df = data.load(asset)
    return df[df.index < pd.Timestamp(SEAL, tz="UTC")]


def metrics(tr):
    n = len(tr)
    if not n:
        return {"trades": 0, "net_usd": 0.0}
    tr = sorted(tr, key=lambda t: t["exit_ms"])
    net = np.array([t["pnl_usd"] for t in tr])
    gross = np.array([t["gross_usd"] for t in tr])
    eq = np.concatenate([[0.0], np.cumsum(net)])
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    return {"trades": n, "win_pct": round(100.0 * float((net > 0).mean()), 1),
            "avg_r_gross": round(float(np.mean([t["gross_r"] for t in tr])), 3),
            "avg_r": round(float(np.mean([t["r"] for t in tr])), 3),
            "pf": round(float(pos / neg), 3) if neg > 0 else None,
            "exp_pct": round(float(net.mean() / pb.STAKE * 100), 4),
            "gross_exp_pct": round(float(gross.mean() / pb.STAKE * 100), 4),
            "net_usd": round(float(net.sum()), 2), "fees_usd": round(float(sum(t["fees_usd"] for t in tr)), 2),
            "max_dd_usd": round(float((np.maximum.accumulate(eq) - eq).max()), 2),
            "median_risk_pct": round(float(np.median([t["risk"] / t["entry"] * 100 for t in tr])), 3),
            "median_cost_r": round(float(np.median([t["gross_r"] - t["r"] for t in tr])), 3),
            "t1_hit_pct": round(100.0 * float(np.mean([bool(t.get("t1_hit")) for t in tr])), 1)}


def slim(t, asset):
    gross_r = t["gross_usd"] / (pb.STAKE * t["risk"] / t["entry"])
    return {"asset": asset, "side": int(t["side"]), "entry_ms": int(t["entry_ms"]), "exit_ms": int(t["exit_ms"]),
            "pnl_usd": float(t["pnl_usd"]), "gross_usd": float(t["gross_usd"]), "fees_usd": float(t["fees_usd"]),
            "r": float(t["r"]), "gross_r": float(gross_r), "risk": float(t["risk"]), "entry": float(t["entry"]),
            "t1_hit": bool(t.get("t1_hit")), "why_out": t["why_out"]}


def _r9(x):
    return None if x != x else round(x, 9)


def truncation_check(df, cuts):
    """Signals of every rule on bars cut at each point must equal the full run's signals before the cut."""
    def key(sigs):
        return [(s["i_dec"], s["side"], round(s["stop"], 9), _r9(s["t2_cand"][1])) for s in sigs]
    boxes = sorted(set(v["box"] for v in ALL.values()))
    full_R = dict((b, adr.readings(df, box=b)) for b in boxes)
    full = dict((v, key(signals(full_R[ALL[v]["box"]], ALL[v]))) for v in ORDER)
    bad, checked = 0, 0
    for cut in cuts:
        part_R = dict((b, adr.readings(df.iloc[:cut], box=b)) for b in boxes)
        for v in ORDER:
            want = [x for x in full[v] if x[0] < cut]
            got = key(signals(part_R[ALL[v]["box"]], ALL[v]))
            checked += len(want)
            if got != want:
                bad += 1
    return {"cuts": len(cuts), "signals_checked": checked, "mismatched_runs": bad}


def run_asset(asset):
    df = load_dev(asset)
    fee = pb.fee_side(asset)
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    boxes = sorted(set(v["box"] for v in ALL.values()))
    Rs = dict((b, adr.readings(df, box=b)) for b in boxes)
    res = {"asset": asset, "fee_side": fee, "bars": int(len(df)), "first_bar": str(df.index[0]), "last_bar": str(df.index[-1]),
           "variants": {}, "trades": {}}
    for v in ORDER:
        tr = [slim(t, asset) for t in run_variant(Rs, ALL[v], fee) if t["status"] == "CLOSED" and t["entry_ms"] >= start_ms]
        h1 = [t for t in tr if t["entry_ms"] < split_ms]
        h2 = [t for t in tr if t["entry_ms"] >= split_ms]
        res["variants"][v] = {"first": metrics(h1), "second": metrics(h2)}
        res["trades"][v] = tr
    ev = {}
    for label, kind, box, k in EVENT_SETS:
        st = event_stats(Rs[box], adr.breaks(Rs[box], kind, k), start_ms)
        ev[label] = dict(("%s|%s" % kk, vv["sum"]) for kk, vv in st.items())
    # reference: 24-bar breaks WITHOUT momentum (true range < 1.0 x ATR15 of the bar before)
    R = Rs[24]
    with np.errstate(invalid="ignore"):
        nomo = np.where(R["bar_x"] < 1.0, np.where(R["c"] > R["box_hi"], 1, np.where(R["c"] < R["box_lo"], -1, 0)), 0)
    st = event_stats(R, nomo.astype(int), start_ms)
    ev["box24 NO momentum (TR < 1.0 ATR15)"] = dict(("%s|%s" % kk, vv["sum"]) for kk, vv in st.items())
    res["events"] = ev
    n = len(df)
    res["truncation"] = truncation_check(df, [int(n * 0.6) + 7, n - 40])
    return res


# ---------------------------------------------------------------- pooling, selection, pass bar
def pooled(results, v, half):
    split_ms = ms_of(SPLIT)
    tr = []
    for r in results.values():
        tr += [t for t in r["trades"][v] if (t["entry_ms"] < split_ms) == (half == "first")]
    return metrics(tr)


def score(results, v):
    vals = [r["variants"][v]["first"]["exp_pct"] for r in results.values()
            if r["variants"][v]["first"]["trades"] >= MIN_TRADES_ASSET]
    return float(np.mean(vals)) if vals else None


def judge(results):
    J = {"scores": {}, "pooled": {}}
    for v in ORDER:
        J["pooled"][v] = {"first": pooled(results, v, "first"), "second": pooled(results, v, "second")}
    cands = []
    for v in VARIANTS:
        if not VARIANTS[v]["select"]:
            continue
        sc = score(results, v)
        J["scores"][v] = sc
        if sc is not None and J["pooled"][v]["first"]["trades"] >= MIN_TRADES_ALL:
            cands.append((-sc, int(v[1:]), v))
    chosen = sorted(cands)[0][2] if cands else None
    J["chosen"] = chosen
    if chosen:
        twin = TWIN_OF[chosen]
        p2, t2 = J["pooled"][chosen]["second"], J["pooled"][twin]["second"]
        pos_markets = [a for a, r in results.items() if r["variants"][chosen]["second"]["net_usd"] > 0]
        bar = {"pooled_net_positive": bool(p2["trades"] >= MIN_TRADES_PASS and p2["net_usd"] > 0),
               "markets_positive": len(pos_markets), "markets_positive_list": pos_markets,
               "markets_ok": len(pos_markets) >= PASS_MARKETS,
               "pf_ok": bool(p2.get("pf") is not None and p2["pf"] >= PASS_PF),
               "beats_twin": bool(p2["trades"] and t2["trades"] and p2["exp_pct"] > t2["exp_pct"]),
               "twin": twin}
        bar["pass"] = bool(bar["pooled_net_positive"] and bar["markets_ok"] and bar["pf_ok"] and bar["beats_twin"])
        J["bar"] = bar
    return J


def events_table(results):
    T = {}
    labels = list(next(iter(results.values()))["events"])
    for label in labels:
        T[label] = {}
        for hf in ("first", "second", "all"):
            for b in BUCKETS + ("all",):
                key = "%s|%s" % (hf, b)
                T[label][key] = finish(merge_sums([r["events"][label].get(key, {}) for r in results.values()]))
    return T


# ---------------------------------------------------------------- report
def fmt(m):
    if not m or not m.get("trades"):
        return "| 0 | | | | | | |"
    return "| %d | %.1f%% | %+.3f | %+.3f | %s | %+.4f%% | %s |" % (
        m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"], "n/a" if m["pf"] is None else "%.2f" % m["pf"],
        m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


HDR = "| trades | won | R before costs | R after costs | PF | per trade (% stake) | net $ |"


def report(S):
    J, res, T = S["judge"], S["results"], S["events"]
    L = ["# H44: range breaks with momentum against the daily ATR budget", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H44) before any number. Development data only "
         "(rows before %s 00:00 UTC; the holdout was not read). Trades from %s; first half before %s. Written %s." % (
             REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Readings from `engine15/sources/adr.py` (`readings`, `breaks`); trades through `playbook.simulate` unchanged "
         "(next open, stop 1 x ATR15 from the break close, break-even after 1R, hold %d bars, each market's own fee a side)." % HOLD, ""]
    if J.get("chosen"):
        b = J["bar"]
        L += ["## Verdict: %s" % ("PASS" if b["pass"] else "NO PASS"), "",
              "Chosen on the first half: **%s** (%s), score %+.4f%% a trade." % (J["chosen"], vdesc(VARIANTS[J["chosen"]]),
                                                                              J["scores"][J["chosen"]]), "",
              "Pass bar (second half): pooled net > 0 with >= %d trades: **%s**; net > 0 in >= %d of 8 markets: **%s** (%d: %s); "
              "PF >= %.1f: **%s**; per trade better than its no-eagle twin (%s): **%s**." % (
                  MIN_TRADES_PASS, "YES" if b["pooled_net_positive"] else "NO", PASS_MARKETS, "YES" if b["markets_ok"] else "NO",
                  b["markets_positive"], ", ".join(b["markets_positive_list"]) or "none", PASS_PF, "YES" if b["pf_ok"] else "NO",
                  b["twin"], "YES" if b["beats_twin"] else "NO"), ""]
    L += ["## Variants, pooled over the eight markets", "",
          "Score = mean over markets (>= %d first-half trades) of the first-half expectancy after costs." % MIN_TRADES_ASSET, "",
          "| id | rule | score | half " + HDR, "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        sc = J["scores"].get(v)
        for hf in ("first", "second"):
            L.append("| %s | %s | %s | %s |%s" % (v if hf == "first" else "", vdesc(ALL[v]) if hf == "first" else "",
                                                ("%+.4f%%" % sc) if (sc is not None and hf == "first") else "", hf,
                                                fmt(J["pooled"][v][hf])[1:]))
    if J.get("chosen"):
        ch, tw = J["chosen"], J["bar"]["twin"]
        L += ["", "## Chosen variant %s vs its no-eagle twin %s and the exhausted contrast V7, per market" % (ch, tw), ""]
        L += ["| market | half | %s net $ | %s per trade | %s trades | %s net $ | %s per trade | %s trades | V7 net $ | V7 per trade | V7 trades |" % (
            ch, ch, ch, tw, tw, tw), "|---|---|---|---|---|---|---|---|---|---|---|"]
        for a, r in res.items():
            for hf in ("first", "second"):
                cells = []
                for v in (ch, tw, "V7"):
                    m = r["variants"][v][hf]
                    cells += ["{:+,.0f}".format(m["net_usd"]), ("%+.4f%%" % m["exp_pct"]) if m["trades"] else "", str(m["trades"])]
                L.append("| %s | %s | %s |" % (a if hf == "first" else "", hf, " | ".join(cells)))
    L += ["", "## Descriptive: what happens after a break with momentum (pre-cost, events, overlaps allowed)", "",
          "Forward return in the break direction from the next open, in 15m ATRs (and %); MFE / MAE over the next 16 bars "
          "in 15m ATRs; hit = reached +1 ATR15 before -1 ATR15 (same bar = miss; 'neither' left out of the hit rate). "
          "Buckets: share of the daily ATR used at the break (room left < 0.65, middle 0.65-1.0, exhausted >= 1.0).", "",
          "| events | half | bucket | n | fwd 4 (ATR) | fwd 8 | fwd 16 | fwd 16 % | up at 16 | MFE | MAE | hit +1 before -1 | neither |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, rows in T.items():
        first = True
        for hf in ("first", "second", "all"):
            for b in BUCKETS + ("all",):
                m = rows["%s|%s" % (hf, b)]
                if not m.get("n"):
                    continue
                L.append("| %s | %s | %s | %d | %+.3f | %+.3f | %+.3f | %+.3f%% | %.1f%% | %.2f | %.2f | %s | %.1f%% |" % (
                    label if first else "", hf, b, m["n"], m["fwd4_atr"], m["fwd8_atr"], m["fwd16_atr"], m["fwd16_pct"],
                    m["up16_pct"], m["mfe_atr"], m["mae_atr"], "n/a" if m["hit1_pct"] is None else "%.1f%%" % m["hit1_pct"],
                    m["neither_pct"]))
                first = False
    L += ["", "## Per market, every variant (second half)", "", "| market | " + " | ".join(ORDER) + " |",
          "|---|" + "---|" * len(ORDER)]
    for a, r in res.items():
        L.append("| %s | %s |" % (a, " | ".join(("%+.3f%% (%d)" % (r["variants"][v]["second"]["exp_pct"], r["variants"][v]["second"]["trades"]))
                                                if r["variants"][v]["second"]["trades"] else "-" for v in ORDER)))
    L += ["", "## Checks", ""]
    for a, r in res.items():
        tc = r["truncation"]
        L.append("- %s: %d bars (%s to %s), fee %.2f%% a side; truncation check %d cuts, %d signals compared, %d mismatched runs." % (
            a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], tc["cuts"], tc["signals_checked"],
            tc["mismatched_runs"]))
    L += ["", "## Overlap with what the engine already reads", "", S["overlap"], ""]
    return "\n".join(L)


OVERLAP = (
    "- `cs_used_x` (card 'Candle size and realistic targets', `sources/ltf.py`): today's high-low / the 14-day AVERAGE "
    "high-low range (simple mean, % of open). H44's `used` is the same idea against the Wilder daily ATR(14) (true "
    "range, so gaps count) and is held fixed for the day; the two agree closely. NEW in H44: room left in each direction, "
    "and the break flag conditioned on it.\n"
    "- `tq_bos` (card 'Trend quality and squeeze'): a CLOSE beyond the last confirmed 5-bar swing, no size condition. "
    "H44's break is beyond a fixed 24-bar box AND needs a bar >= 1.5 x ATR15; many H44 breaks are also BOS events, "
    "but the momentum condition and the daily budget are not read there.\n"
    "- `tq_sq_release` (same card): a Bollinger-inside-Keltner squeeze ending; a volatility-regime event, not a range "
    "break. Related (a release often coincides with a large bar) but different.\n"
    "- `id_or` (card 'Intraday levels'): position vs the first UTC hour's range (above / inside / below), no momentum "
    "condition, no first-break event. V5 uses the same range (first 4 bars of the UTC day on file).\n"
    "- H7 (breakout trap, `playbook.py` p2) FADES failed first closes beyond the 48-bar / prior-day / swing levels; "
    "H44 trades WITH the break.")


# ---------------------------------------------------------------- live setup scan (paper)
def scan(chosen=None, passed=False, max_age=4, now_ms=None):
    """On the latest closed bars of each market (the whole file, live tail included: this reads the present, it does
    not grade anything) -> list of dict rows and printable lines. A break with momentum in the last `max_age` bars is
    listed with its eagle-view context and the levels of the chosen rule (entry = the next open after the break)."""
    var = VARIANTS.get(chosen or "V1")
    rows, lines = [], []
    label = "PAPER, %s" % ("passed H44's history bar" if passed else "UNTESTED / did NOT pass H44's history bar")
    lines.append("H44 live setup scan (%s), rule %s: %s" % (label, chosen or "V1", vdesc(var)))
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    for a in ASSETS:
        try:
            df = data.load(a)
        except Exception as ex:
            lines.append("  %-8s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=60)]
        df = df[data.to_ms(df.index) + pb.BAR_MS <= now_ms]                # closed bars only
        R = adr.readings(df, box=var["box"])
        br = adr.breaks(R, var["kind"], var["k"])
        n = R["n"]
        i_last = n - 1
        last_close = pd.Timestamp(int(R["ms"][i_last]) + pb.BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - (int(R["ms"][i_last]) + pb.BAR_MS)) / 3600000.0
        ctx = "used %s of daily ATR %s, room up %s / down %s" % (
            _pc(R["used"][i_last]), _p(R["datr"][i_last]), _f(R["room_up"][i_last]), _f(R["room_dn"][i_last]))
        recent = [i for i in range(max(0, n - max_age), n) if br[i] != 0]
        R24 = R if var["box"] == 24 else adr.readings(df, box=24)
        b24 = adr.breaks(R24, "box", 1.5)
        ev = np.flatnonzero(b24 != 0)
        if len(ev):                                                   # the card's definition (24-bar box, k 1.5)
            j = int(ev[-1])
            ctx += "; card's 24-bar break: last %s %d bars ago at %s (day had used %s, %s)" % (
                "UP" if b24[j] > 0 else "DOWN", n - 1 - j, _p(R24["c"][j]), _pc(R24["used"][j]), adr.bucket(R24["used"][j]))
        head = "  %-8s last close %s%s; %s" % (a, last_close.strftime("%d %b %H:%M UTC"),
                                              " (stale %.1f h: market shut)" % age_h if age_h > 1 else "", ctx)
        if not recent:
            lines.append(head + "; no break with momentum in the last %d bars." % max_age)
            rows.append({"asset": a, "break": None, "context": ctx})
            continue
        i = recent[-1]
        s = int(br[i])
        u = R["used"][i]
        ok_filter = (var["filter"] == "none") or (var["filter"] == "room" and u < adr.ROOM_LEFT) or \
                    (var["filter"] == "exhausted" and u >= adr.EXHAUSTED)
        entry = R["o"][i + 1] if i + 1 < n else R["c"][i]
        stop = R["c"][i] - s * STOP_ATR * R["atr15"][i]
        risk = abs(entry - stop)
        t1, t2 = entry + s * risk, entry + s * 2.0 * risk
        if var["exit"] == "Eroom":
            room_px = (R["day_low"][i] + R["datr"][i]) if s > 0 else (R["day_high"][i] - R["datr"][i])
            if s * (room_px - t1) >= 0.5 * risk:
                t2 = room_px
        when = pd.Timestamp(int(R["ms"][i]) + pb.BAR_MS, unit="ms", tz="UTC").strftime("%H:%M UTC")
        txt = ("%s; BREAK %s with momentum at the %s close (bar %.1fx ATR15), day had used %s (%s)%s. Plan if taken: %s %s %s, "
               "stop %s, T1 %s (1R), T2 %s; hold %d bars. %s" % (
                   head, "UP" if s > 0 else "DOWN", when, R["bar_x"][i], _pc(u), adr.bucket(u),
                   "" if ok_filter else " -> FILTERED OUT by the rule's daily-ATR condition",
                   "LONG" if s > 0 else "SHORT", "at" if i + 1 < n else "at the next open, about", _p(entry), _p(stop),
                   _p(t1), _p(t2), HOLD, label))
        lines.append(txt)
        rows.append({"asset": a, "break": s, "close_utc": when, "used": None if u != u else round(float(u), 3),
                     "bucket": adr.bucket(u), "passes_filter": bool(ok_filter), "entry": float(entry), "stop": float(stop),
                     "t1": float(t1), "t2": float(t2), "context": ctx})
    return rows, lines


def _p(v):
    return "n/a" if v is None or v != v else pb._px(float(v))


def _pc(v):
    return "n/a" if v is None or v != v else "%.0f%%" % (100.0 * v)


def _f(v):
    return "n/a" if v is None or v != v else "%+.2f" % v


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H44 rangebreak study")
    results = {}
    try:
        for a in ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a] = run_asset(a)
            log("%s: done in %.0f s; V8 first-half trades %d, truncation %s" % (
                a, time.time() - t0, results[a]["variants"]["V8"]["first"]["trades"], results[a]["truncation"]))
    finally:
        release_lock()
    J = judge(results)
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC,
         "variants": dict((v, ALL[v]) for v in ORDER), "judge": J, "events": events_table(results), "overlap": OVERLAP,
         "results": dict((a, dict((k, v) for k, v in r.items() if k != "trades")) for a, r in results.items())}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("chosen %s, pass %s" % (J.get("chosen"), J.get("bar", {}).get("pass")))
    return S


def load_study():
    with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
        return json.load(fh)


def print_scan():
    try:
        S = load_study()
        ch, ps = S["judge"].get("chosen"), bool(S["judge"].get("bar", {}).get("pass"))
    except Exception:
        ch, ps = None, False
    _rows, lines = scan(ch, ps)
    print("\n".join(lines))


if __name__ == "__main__":
    if "--report" in sys.argv:
        S = load_study()
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(S))
    elif "--scan" in sys.argv:
        print_scan()
    else:
        main()
        print_scan()
