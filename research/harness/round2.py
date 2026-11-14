# -*- coding: utf-8 -*-
"""Harness loop, round 2 (H25-H31, registered in research/HYPOTHESES.md before any result). Development data only.

    py -3 research/harness/round2.py            compute BTC and ETH, books, grade, write the round-2 report
    py -3 research/harness/round2.py --report   rebuild the report from research/out/harness/r2_cache.json

Outputs: research/out/harness/harness_report_round2.md, harness_summary_round2.json, loop_state.json (updated,
holdout ledger preserved), r2_cache.json. Paper research only.
"""
import argparse
import gc
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine15 import data as edata  # noqa: E402
from engine15.rl import metrics, resources, walkforward  # noqa: E402
from research.harness import core, families  # noqa: E402

ASSETS = ("BTCUSDT", "ETHUSDT")
ROUND1_VARIANTS = 1838
ROUND2_VARIANTS = 64
N_CUM = ROUND1_VARIANTS + ROUND2_VARIANTS
TARGET, MILESTONE = 0.25, 0.10
HEAD, ALT = "fee_0.10%", "fee_0.05%"
CACHE = os.path.join(core.OUT_DIR, "r2_cache.json")
STATE = os.path.join(core.OUT_DIR, "loop_state.json")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def wait_mem(need=1000):
    while True:
        f = resources.free_mb()
        if f is None or f >= need:
            return
        log("waiting for memory: %.0f MB free" % f)
        time.sleep(30)


# ------------------------------------------------------------------ building blocks (each reads row t and its own state only)

def extra_features(bars, feats):
    f = {}
    f["rv_ann"] = feats["rv672"].values * math.sqrt(core.BPY)
    f["ens"] = np.mean([core.benchmarks.momentum(bars["close"], L).values for L in (10, 20, 30, 60, 90)], axis=0)
    d1 = edata.resample(bars.assign(taker_buy=0.0), "1D")
    pc = d1["close"].shift(1)
    tr = np.maximum(d1["high"] - d1["low"], np.maximum((d1["high"] - pc).abs(), (d1["low"] - pc).abs()))
    atr = tr.ewm(alpha=1 / 14.0, adjust=False).mean()
    f["atr1d"] = edata.htf_on_15(bars, "1D", atr).values.astype(float)
    return pd.DataFrame(f, index=bars.index)


def resize(want, step=0.25):
    """Held exposure changes when the wanted sign differs or |wanted - held| >= step."""
    w = np.nan_to_num(np.asarray(want, dtype=float)).tolist()
    out, cur = [0.0] * len(w), 0.0
    for t, x in enumerate(w):
        if np.sign(x) != np.sign(cur) or abs(x - cur) >= step:
            cur = x
        out[t] = cur
    return np.asarray(out)


def pullback(want, feats, close, a=1.0, W=48, on_increase=False):
    """E2: a new direction (or, with on_increase, a larger exposure on the same side) waits up to W bars for a 15m
    close at/below EMA20 - a x ATR14 (long; mirror short). Flat while waiting for a new direction; the lower exposure
    is kept while waiting for an increase. Decreases happen at once."""
    lo = (feats["ema20"].values - a * feats["atr14"].values).tolist()
    hi = (feats["ema20"].values + a * feats["atr14"].values).tolist()
    c = np.asarray(close, dtype=float).tolist()
    w = np.nan_to_num(np.asarray(want, dtype=float)).tolist()
    out = [0.0] * len(w)
    cur, pending, waiting, wf = 0.0, 0.0, False, 0
    for t in range(len(w)):
        x = w[t]
        target_now = pending if waiting else cur
        if x != target_now:
            sc = x != 0 and np.sign(x) != np.sign(cur)
            inc = on_increase and x != 0 and np.sign(x) == np.sign(cur) and abs(x) > abs(cur)
            if sc or inc:
                if not (waiting and np.sign(pending) == np.sign(x)):
                    wf = t
                pending, waiting = x, True
                if sc:
                    cur = 0.0
            else:
                cur, waiting = x, False
        if waiting:
            s = np.sign(pending)
            if (c[t] <= lo[t] if s > 0 else c[t] >= hi[t]) or t - wf >= W:
                cur, waiting = pending, False
        out[t] = cur
    return np.asarray(out)


def trailing_exit(base, feats, ex, close, m, a=1.0, W=48):
    """H31: while long, a close below (highest close since entry - m x daily ATR14) goes flat; re-entry only at a later
    00:00 UTC decision with d > 0, then with the E2 pullback."""
    b = np.asarray(base, dtype=float).tolist()
    c = np.asarray(close, dtype=float).tolist()
    atr = np.nan_to_num(ex["atr1d"].values, nan=np.inf).tolist()
    daily = feats["is_daily"].values.tolist()
    d = feats["trend1d"].values.tolist()
    lo = (feats["ema20"].values - a * feats["atr14"].values).tolist()
    out = [0.0] * len(b)
    blocked, waiting, wf, peak, prev = False, False, 0, 0.0, 0.0
    for t in range(len(b)):
        if blocked:
            if daily[t] and d[t] > 0:
                blocked, waiting, wf = False, True, t
            else:
                out[t] = prev = 0.0
                continue
        if waiting:
            if b[t] <= 0:
                waiting = False
            elif c[t] <= lo[t] or t - wf >= W:
                waiting = False
            else:
                out[t] = prev = 0.0
                continue
        x = b[t]
        if x > 0:
            peak = c[t] if prev <= 0 else max(peak, c[t])
            if c[t] < peak - m * atr[t]:
                blocked = True
                out[t] = prev = 0.0
                continue
        out[t] = prev = x
    return np.asarray(out)


class R2:
    def __init__(self, bars, feats, ex):
        self.bars, self.f, self.ex = bars, feats, ex
        self.c = bars["close"].values.astype(float)
        self.d = feats["trend1d"].values
        self.f2 = families.F2(feats, self.c)

    def h25(self, key):
        s, vt, Lmax = key
        rv = np.where(self.ex["rv_ann"].values > 0, self.ex["rv_ann"].values, np.nan)
        k = np.nan_to_num(vt / rv, nan=1.0)
        want = np.where(self.d > 0, np.minimum(Lmax, k), np.where(self.d < 0, -s * np.minimum(1.0, k), 0.0))
        return pullback(resize(want), self.f, self.c)

    def h26(self, v):
        e = self.ex["ens"].values
        want = {"ls": e, "lo": np.maximum(e, 0.0), "lo15": 1.5 * np.maximum(e, 0.0)}[v]
        return pullback(want, self.f, self.c)

    def h28(self):
        return self.f2.target((0.0, "R1", "E2"))

    def h30(self, U, D):
        want = np.where(self.d > 0, U, np.where(self.d < 0, D, 0.0))
        return pullback(want, self.f, self.c, on_increase=True)

    def h31(self, m):
        rv = np.where(self.ex["rv_ann"].values > 0, self.ex["rv_ann"].values, np.nan)
        k = np.nan_to_num(0.6 / rv, nan=1.0)
        want = np.where(self.d > 0, np.minimum(2.0, k), 0.0)
        base = pullback(resize(want), self.f, self.c)
        return trailing_exit(base, self.f, self.ex, self.c, m)


H25_KEYS = [(s, vt, L) for s in (0.0, 0.5) for vt in (0.5, 0.8) for L in (1.5, 2.0)]
H30_KEYS = [(1.5, 0.5), (2.0, 0.0), (1.5, 0.0)]
H31_KEYS = [2.5, 4.0]


# ------------------------------------------------------------------ scoring

def year_returns(r, index, oos):
    s = pd.Series(r[oos], index=index[oos])
    g = (1.0 + s).groupby(s.index.year).prod() - 1.0
    return dict((int(k), float(v)) for k, v in g.items())


def stats_from_r(r, index, wins, oos, pos=None):
    """Metrics of a per-bar return series over the OOS span and per fold (books and strategies alike)."""
    x = r[oos]
    eq = np.cumprod(1 + x)
    years = len(x) / core.BPY
    out = {"cagr": metrics.cagr(x), "total_return": float(eq[-1] - 1), "sharpe": metrics.sharpe(x),
           "sortino": metrics.sortino(x), "max_drawdown": metrics.max_drawdown(np.concatenate([[1.0], eq])),
           "calmar": metrics.calmar(x), "years": years}
    if pos is not None:
        p = pos[oos]
        prev = pos[np.argmax(oos) - 1] if np.argmax(oos) > 0 else 0.0
        out["trades_per_year"] = float(np.count_nonzero(np.diff(p, prepend=prev)) / years)
        out["avg_exposure"] = float(np.mean(np.abs(p)))
    _, te = core.masks(index, wins)
    out["folds"] = [{"test_start": str(w["test_start"].date()), "total_return": float(np.prod(1 + r[m]) - 1),
                     "sharpe": metrics.sharpe(r[m])} for w, m in zip(wins, te)]
    out["years_table"] = year_returns(r, index, oos)
    return out


class Coin:
    def __init__(self, asset):
        self.asset = asset
        self.bars, self.fund = core.load(asset, dev_only=True)
        self.feats = core.features(self.bars)
        self.ex = extra_features(self.bars, self.feats)
        self.mkt = core.Market(self.bars, self.fund)
        self.wins = core.windows(self.bars.index)
        self.oos = walkforward.oos_mask(self.bars.index, self.wins)
        self.r2 = R2(self.bars, self.feats, self.ex)
        self.idx = self.bars.index
        ones = np.ones(len(self.idx))
        self.bench = {}
        for nm, spot in (("bh_spot", True), ("bh_perp", False)):
            st = core.walkforward.stitch(self.idx, self.wins, lambda tr, te: ones[te])
            self.bench[nm] = self.run(st.values, spot)
        mom = core.benchmarks.momentum(self.bars["close"]).values
        self.bench["momentum"] = self.run(np.where(self.oos, mom, 0.0), False)

    def run(self, target, spot, rand=False):
        """target already stitched (0 outside OOS) -> stats at both fees + returns arrays kept for grading."""
        out = {}
        for fee, tag in ((core.FEE_HEAD, HEAD), (core.FEE_ALT, ALT)):
            fr = self.mkt.frame(target, fee, spot)
            r, pos = fr["r_net"].values, fr["pos"].values
            out[tag] = stats_from_r(r, self.idx, self.wins, self.oos, pos)
            out[tag]["sharpe_gross"] = metrics.sharpe(fr["r_gross"].values[self.oos])
            out[tag]["cost_drag_per_year"] = float((fr["r_gross"].values - r)[self.oos].sum() / out[tag]["years"])
            if fee == core.FEE_HEAD:
                out["_r"] = r.copy()
                out["_pos"] = pos.copy()
                out["breakeven_fee"] = core.breakeven_fee(fr, self.oos)
            del fr
        if rand:
            rs = []
            for s in range(10):
                t = core.random_matched(self.idx, self.oos, out["_pos"][self.oos], s)
                rs.append(metrics.sharpe(self.mkt.net(t, core.FEE_HEAD, spot)[self.oos]))
            out["random_matched_sharpe"] = float(np.mean(rs))
        return out

    def fixed(self, target, spot):
        return self.run(np.where(self.oos, target, 0.0), spot, rand=True)

    def selected(self, keys, fn, spot):
        choice, _ = core.select(self.mkt, self.wins, keys, fn, spot=spot)
        st = core.stitch(self.idx, self.wins, choice, fn)
        res = self.run(st, spot, rand=True)
        res["selected"] = [str(k) for k in choice]
        return res


def strategies(coin):
    r2 = coin.r2
    S = {}
    S["H25 vol-targeted momentum (perp)"] = ("H25", coin.selected(H25_KEYS, r2.h25, False))
    for v, nm in (("ls", "long/short"), ("lo", "long-only"), ("lo15", "long-only 1.5x")):
        S["H26 ensemble %s (perp)" % nm] = ("H26", coin.fixed(r2.h26(v), False))
    t28 = r2.h28()
    S["H28 fixed H22 variant (perp)"] = ("H28", coin.fixed(t28, False))
    S["H29 H25 spot longs"] = ("H29", coin.selected(H25_KEYS, r2.h25, True))
    S["H29 H28 spot longs"] = ("H29", coin.fixed(t28, True))
    for U, D in H30_KEYS:
        t = r2.h30(U, D)
        S["H30 trend core %gx/%gx (perp)" % (U, D)] = ("H30", coin.fixed(t, False))
        S["H29 H30 %gx/%gx spot longs" % (U, D)] = ("H29", coin.fixed(t, True))
    for m in H31_KEYS:
        t = r2.h31(m)
        S["H31 vol-target + trail %g ATR (perp)" % m] = ("H31", coin.fixed(t, False))
        S["H29 H31 trail %g ATR spot longs" % m] = ("H29", coin.fixed(t, True))
    return S


def book(c1, c2, r1, r2):
    """Two never-rebalanced half books on c1's index (c2's returns on bars it lacks are 0)."""
    s2 = pd.Series(r2, index=c2.idx).reindex(c1.idx).fillna(0.0).values
    oos = c1.oos
    e1 = np.cumprod(1 + np.where(oos, r1, 0.0))
    e2 = np.cumprod(1 + np.where(oos, s2, 0.0))
    eq = 0.5 * e1 + 0.5 * e2
    r = np.diff(eq, prepend=1.0) / np.concatenate([[1.0], eq[:-1]])
    return r


# ------------------------------------------------------------------ grading (rules set before round 2)

def grade(res, bench, idx, oos, n_cum, check_turnover=True):
    h, a = res[HEAD], res[ALT]
    out = {}
    for bname in ("bh_spot", "bh_perp"):
        b, ba = bench[bname][HEAD], bench[bname][ALT]
        beats = lambda x, y: x["sharpe"] > y["sharpe"] and x["calmar"] > y["calmar"]
        nf = len(h["folds"])
        fs = sum(1 for f, g in zip(h["folds"], b["folds"]) if f["sharpe"] > g["sharpe"]) / nf
        pos = sum(1 for f in h["folds"] if f["total_return"] > 0) / nf
        obs, p, se = core.boot_sharpe_diff_z(res["_r"][oos], bench[bname]["_r"][oos], idx[oos])
        rules = {"1_cagr_ge_25": h["cagr"] >= TARGET, "2_cagr_gt_bh": h["cagr"] > b["cagr"],
                 "3_sharpe_gt_bh_and_dd_le_bh": h["sharpe"] > b["sharpe"] and h["max_drawdown"] <= b["max_drawdown"],
                 "4_fold_share_ge_half": fs >= 0.5, "5_significant": p <= 0.05 / n_cum,
                 "6_no_fee_only_at_0.05": not (beats(a, ba) and not beats(h, b)),
                 "6_no_high_turnover": (h.get("trades_per_year", 0) <= 100) if check_turnover else True,
                 "7_positive_folds_gt_half": pos > 0.5}
        out[bname] = {"rules": rules, "pass": all(rules.values()), "fold_share": fs, "positive_fold_share": pos,
                      "sharpe_minus_bh": obs, "p": p, "se": se, "rules_met": sum(rules.values())}
    out["dsr"] = core.deflated_sharpe(res["_r"][oos], n_cum)
    out["milestone_10"] = h["cagr"] >= MILESTONE
    return out


def strip(o):
    if isinstance(o, dict):
        return dict((str(k), strip(v)) for k, v in o.items() if not str(k).startswith("_"))
    if isinstance(o, list):
        return [strip(v) for v in o]
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return None if math.isnan(o) else "inf"
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


def compute():
    resources.low_priority()
    coins, res = {}, {}
    for a in ASSETS:
        wait_mem(1000)
        t0 = time.time()
        c = Coin(a)
        S = strategies(c)
        g = dict((k, grade(v, c.bench, c.idx, c.oos, N_CUM)) for k, (_, v) in S.items())
        coins[a] = c
        res[a] = {"oos": [str(c.wins[0]["test_start"].date()), str(c.wins[-1]["test_end"].date())],
                  "bench": c.bench, "strategies": dict((k, {"hyp": h, "res": v, "grade": g[k]}) for k, (h, v) in S.items())}
        log("%s done in %.0fs" % (a, time.time() - t0))
        for k, (h, v) in S.items():
            m = v[HEAD]
            log("  %-38s CAGR %+6.1f%%  Sharpe %.2f  DD %3.0f%%  tr/yr %4.0f  rules met vs spot %d/8" % (
                k, 100 * m["cagr"], m["sharpe"], 100 * m["max_drawdown"], m["trades_per_year"],
                g[k]["bh_spot"]["rules_met"]))
    # books (H27): on BTC's index and folds
    b, e = coins["BTCUSDT"], coins["ETHUSDT"]
    bk = {}
    bb = {}
    for nm in ("bh_spot", "bh_perp"):
        bb[nm] = {"_r": book(b, e, b.bench[nm]["_r"], e.bench[nm]["_r"])}
    for nm, key in (("H27 book: H28 on both coins", "H28 fixed H22 variant (perp)"),
                    ("H27 book: H25 on both coins", "H25 vol-targeted momentum (perp)")):
        rb_ = res["BTCUSDT"]["strategies"][key]["res"]
        re_ = res["ETHUSDT"]["strategies"][key]["res"]
        r = book(b, e, rb_["_r"], re_["_r"])
        st = stats_from_r(r, b.idx, b.wins, b.oos)
        st["trades_per_year"] = rb_[HEAD]["trades_per_year"] + re_[HEAD]["trades_per_year"]
        bk[nm] = {"hyp": "H27", "res": {HEAD: st, ALT: st, "_r": r}, "note": "0.05% line not computed for books"}
    for nm in bb:
        bb[nm][HEAD] = stats_from_r(bb[nm]["_r"], b.idx, b.wins, b.oos)
        bb[nm][ALT] = bb[nm][HEAD]
    for nm, v in bk.items():
        v["grade"] = grade(v["res"], bb, b.idx, b.oos, N_CUM, check_turnover=False)
        v["grade"]["note"] = "turnover rule applied per coin; 0.05% rule not applicable (books at 0.10% only)"
    res["books"] = {"bench": bb, "books": bk}
    out = strip(res)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f, default=float)
    return out


# ------------------------------------------------------------------ report

def pct(x, d=1):
    return "-" if x is None else "%+.*f%%" % (d, 100 * x)


def fee_s(x):
    if x is None:
        return "none"
    if x == "inf" or (isinstance(x, float) and x > 0.04):
        return "> 4%"
    return "%.3f%%" % (100 * x)


def report(R):
    L = []
    w = L.append
    w("# Harness loop, round 2: strict outperformance of buy-and-hold at >= 25% CAGR\n")
    w("Generated %s UTC by `py -3 research/harness/round2.py`. Paper research only. H25-H31 registered in "
      "`research/HYPOTHESES.md` at 14:05 UTC on 11 Nov 2026, before any round-2 result. Development data only "
      "(out of sample %s to %s, 21 walk-forward folds); the sealed holdout (2025-11-11 to 2026-11-11) is untouched.\n"
      % (time.strftime("%Y-%m-%d %H:%M", time.gmtime()), R["BTCUSDT"]["oos"][0], R["BTCUSDT"]["oos"][1]))
    notes = os.path.join(HERE, "notes_round2.md")
    if os.path.exists(notes):
        with open(notes, encoding="utf-8") as f:
            w(f.read().strip() + "\n")
    w("## Rules (owner, set before round 2; per coin)\n")
    w("1 CAGR >= 25%% net of 0.10%% a side and funding; 2 CAGR > buy-and-hold's; 3 Sharpe > buy-and-hold's and max DD <= "
      "buy-and-hold's; 4 Sharpe > buy-and-hold's in >= half the folds; 5 bootstrap p <= 0.05 / %d (all variants tried in "
      "the loop: 1,838 in round 1 + 64 in round 2) = %.1e, deflated-Sharpe probability reported; 6 no fee_only_at_0.05, "
      "no high turnover (> 100 changes a year); 7 (kept from round 1) more than half the folds net positive. Benchmark "
      "for the pass: **spot buy-and-hold** (no funding); perp buy-and-hold shown too.\n" % (N_CUM, 0.05 / N_CUM))
    for a in ASSETS:
        A = R[a]
        bs, bp, mo = A["bench"]["bh_spot"][HEAD], A["bench"]["bh_perp"][HEAD], A["bench"]["momentum"][HEAD]
        w("## %s\n" % a)
        w("### CAGR against the target and the benchmarks, 0.10%% a side (spot buy-and-hold %s, perp buy-and-hold %s, momentum %s)\n"
          % (pct(bs["cagr"]), pct(bp["cagr"]), pct(mo["cagr"])))
        w("| Strategy | CAGR | vs 25%% | vs spot B&H | vs momentum | Sharpe (spot B&H %.2f) | Max DD (spot B&H %.0f%%) | Calmar | Trades/yr | Avg exposure | Break-even fee | Rules met vs spot (of 8) | vs perp (of 8) | Boot p | DSR | Pass |"
          % (bs["sharpe"], 100 * bs["max_drawdown"]))
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k, v in A["strategies"].items():
            m, g = v["res"][HEAD], v["grade"]
            w("| %s | %s | %s | %s | %s | %.2f | %.0f%% | %.2f | %.0f | %.2f | %s | %d | %d | %.3f | %.2f | %s |" % (
                k, pct(m["cagr"]), pct(m["cagr"] - TARGET), pct(m["cagr"] - bs["cagr"]), pct(m["cagr"] - mo["cagr"]),
                m["sharpe"], 100 * m["max_drawdown"], m["calmar"], m["trades_per_year"], m["avg_exposure"],
                fee_s(v["res"].get("breakeven_fee")), g["bh_spot"]["rules_met"], g["bh_perp"]["rules_met"],
                g["bh_spot"]["p"], g["dsr"], "**YES**" if g["bh_spot"]["pass"] else "no"))
        for nm, b in (("Buy-and-hold, spot", bs), ("Buy-and-hold, perp", bp), ("Momentum (daily, 30-day, perp)", mo)):
            w("| %s | %s | %s | | | %.2f | %.0f%% | %.2f | %.0f | | | | | | | |" % (
                nm, pct(b["cagr"]), pct(b["cagr"] - TARGET), b["sharpe"], 100 * b["max_drawdown"], b["calmar"],
                b.get("trades_per_year", 0)))
        w("")
        w("### Which rules fail (vs spot buy-and-hold, %s)\n" % a)
        w("| Strategy | CAGR >= 25% | CAGR > B&H | Sharpe > B&H & DD <= B&H | fold share (%) | significant | no fee-only-0.05 | turnover <= 100 | folds positive (%) | at 0.05%: CAGR / Sharpe |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        yn = lambda x: "yes" if x else "no"
        for k, v in A["strategies"].items():
            r, g = v["grade"]["bh_spot"]["rules"], v["grade"]["bh_spot"]
            m5 = v["res"][ALT]
            w("| %s | %s | %s | %s | %s (%.0f) | %s | %s | %s | %s (%.0f) | %s / %.2f |" % (
                k, yn(r["1_cagr_ge_25"]), yn(r["2_cagr_gt_bh"]), yn(r["3_sharpe_gt_bh_and_dd_le_bh"]),
                yn(r["4_fold_share_ge_half"]), 100 * g["fold_share"], yn(r["5_significant"]), yn(r["6_no_fee_only_at_0.05"]),
                yn(r["6_no_high_turnover"]), yn(r["7_positive_folds_gt_half"]), 100 * g["positive_fold_share"],
                pct(m5["cagr"]), m5["sharpe"]))
        w("")
        w("### Calendar-year returns, 0.10%% a side (%s; 2020 from 1 Oct, 2025 to 10 Nov)\n" % a)
        yrs = sorted(int(y) for y in bs["years_table"])
        w("| Strategy | " + " | ".join(str(y) for y in yrs) + " | Years beating spot B&H |")
        w("|---|" + "---|" * (len(yrs) + 1))
        for nm, yt in [("Buy-and-hold, spot", bs["years_table"]), ("Buy-and-hold, perp", bp["years_table"]),
                       ("Momentum (perp)", mo["years_table"])] + [(k, v["res"][HEAD]["years_table"]) for k, v in A["strategies"].items()]:
            wins = sum(1 for y in yrs if yt[str(y)] > bs["years_table"][str(y)])
            w("| %s | %s | %d of %d |" % (nm, " | ".join(pct(yt[str(y)], 0) for y in yrs), wins, len(yrs)))
        w("")
        sel = [(k, v["res"]["selected"]) for k, v in A["strategies"].items() if "selected" in v["res"]]
        for k, s in sel:
            from collections import Counter
            w("- %s, walk-forward choices (s, vt, Lmax) by count: %s" % (k, ", ".join("%s x%d" % kv for kv in Counter(s).most_common())))
        w("")
    B = R["books"]
    bs = B["bench"]["bh_spot"][HEAD]
    w("## H27: two-coin books (half BTC, half ETH, never rebalanced; vs the same spot buy-and-hold book)\n")
    w("| Book | CAGR | Sharpe | Max DD | Calmar | Trades/yr (both coins) | Fold share vs B&H | Folds positive | Boot p | DSR | Pass |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for k, v in B["books"].items():
        m, g = v["res"][HEAD], v["grade"]
        w("| %s | %s | %.2f | %.0f%% | %.2f | %.0f | %.0f%% | %.0f%% | %.3f | %.2f | %s |" % (
            k, pct(m["cagr"]), m["sharpe"], 100 * m["max_drawdown"], m["calmar"], m["trades_per_year"],
            100 * g["bh_spot"]["fold_share"], 100 * g["bh_spot"]["positive_fold_share"], g["bh_spot"]["p"], g["dsr"],
            "**YES**" if g["bh_spot"]["pass"] else "no"))
    for nm in ("bh_spot", "bh_perp"):
        m = B["bench"][nm][HEAD]
        w("| Buy-and-hold book, %s | %s | %.2f | %.0f%% | %.2f | | | | | | |" % (nm[3:], pct(m["cagr"]), m["sharpe"], 100 * m["max_drawdown"], m["calmar"]))
    yrs = sorted(int(y) for y in bs["years_table"])
    w("\n| Book | " + " | ".join(str(y) for y in yrs) + " |")
    w("|---|" + "---|" * len(yrs))
    for nm, yt in [("Buy-and-hold book, spot", bs["years_table"])] + [(k, v["res"][HEAD]["years_table"]) for k, v in B["books"].items()]:
        w("| %s | %s |" % (nm, " | ".join(pct(yt[str(y)], 0) for y in yrs)))
    w("")
    # passes
    passes = []
    for k in R["BTCUSDT"]["strategies"]:
        gb, ge = R["BTCUSDT"]["strategies"][k]["grade"], R["ETHUSDT"]["strategies"][k]["grade"]
        if gb["bh_spot"]["pass"] and ge["bh_spot"]["pass"]:
            passes.append(k)
    for k, v in B["books"].items():
        if v["grade"]["bh_spot"]["pass"]:
            passes.append(k)
    best = max(R["BTCUSDT"]["strategies"], key=lambda k: (R["BTCUSDT"]["strategies"][k]["grade"]["bh_spot"]["rules_met"]
                                                          + R["ETHUSDT"]["strategies"][k]["grade"]["bh_spot"]["rules_met"],
                                                          R["BTCUSDT"]["strategies"][k]["res"][HEAD]["cagr"]))
    w("## Round 2 result\n")
    w("- Development passes (all rules, BTC and ETH, vs spot buy-and-hold): %s." % (", ".join(passes) if passes else "**none**"))
    gb, ge = R["BTCUSDT"]["strategies"][best]["grade"]["bh_spot"], R["ETHUSDT"]["strategies"][best]["grade"]["bh_spot"]
    w("- Closest: %s (rules met %d/8 on BTC, %d/8 on ETH; failing on BTC: %s; on ETH: %s)." % (
        best, gb["rules_met"], ge["rules_met"], ", ".join(k for k, v in gb["rules"].items() if not v),
        ", ".join(k for k, v in ge["rules"].items() if not v)))
    w("- Holdout looks used: %d." % len(_state().get("holdout_looks", [])))
    with open(os.path.join(core.OUT_DIR, "harness_report_round2.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    summ = {"schema": "harness_summary_round2/1", "generated_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "paper_only": True, "round": 2, "hypotheses": ["H25", "H26", "H27", "H28", "H29", "H30", "H31"],
            "variants_round2": ROUND2_VARIANTS, "variants_cumulative": N_CUM, "bonferroni_alpha": 0.05 / N_CUM,
            "benchmark_for_pass": "spot buy-and-hold", "development_passes": passes, "closest": best, "results": R}
    with open(os.path.join(core.OUT_DIR, "harness_summary_round2.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=float)
    st = _state()
    st["round"] = 2
    st.pop("round_in_progress", None)
    st["updated_utc"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    vt = st.setdefault("variants_tried", {})
    vt["round_2"] = {"per_coin": 31, "books": 2, "total": ROUND2_VARIANTS}
    vt["total"] = N_CUM
    st["development_passes"] = st.get("development_passes", []) + [{"id": "R2-%s" % p} for p in passes]
    mb = R["BTCUSDT"]["strategies"][best]["res"][HEAD]
    st["closest_to_pass"] = {"id": "R2-" + best, "rules_met_btc": gb["rules_met"], "rules_met_eth": ge["rules_met"], "of": 8,
                             "failing_btc": [k for k, v in gb["rules"].items() if not v],
                             "failing_eth": [k for k, v in ge["rules"].items() if not v]}
    cands = [(k, v["res"][HEAD]) for k, v in R["BTCUSDT"]["strategies"].items()]
    k_best, m_best = max(cands, key=lambda kv: kv[1]["cagr"])
    prev = st.get("best_so_far") or {}
    if m_best["cagr"] > prev.get("dev_cagr", -9):
        st["best_so_far"] = {"id": "R2-" + k_best, "name": k_best, "dev_cagr": m_best["cagr"], "dev_sharpe": m_best["sharpe"],
                             "dev_max_drawdown": m_best["max_drawdown"], "trades_per_year": m_best["trades_per_year"],
                             "note": "BTC, 0.10%, by development CAGR; not a pass unless listed in development_passes"}
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, default=float)
    log("round-2 report written; passes: %s; closest: %s" % (passes or "none", best))
    del mb


def _state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    os.makedirs(core.OUT_DIR, exist_ok=True)
    if a.report:
        with open(CACHE, encoding="utf-8") as f:
            R = json.load(f)
    else:
        R = compute()
        gc.collect()
    report(R)


if __name__ == "__main__":
    main()
