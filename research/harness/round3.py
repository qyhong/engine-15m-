# -*- coding: utf-8 -*-
"""Harness loop, round 3 (H32-H35, registered in research/HYPOTHESES.md before any result). Development data only.

    py -3 research/harness/round3.py            BTC, ETH (graded) + six other markets (report only), then the report
    py -3 research/harness/round3.py --report   rebuild the report from research/out/harness/r3_cache.json

Outputs: research/out/harness/harness_report_round3.md, harness_summary_round3.json, r3_cache.json, loop_state.json.
"""
import argparse
import json
import math
import os
import sys
import time
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine15.config import CFG  # noqa: E402
from engine15.rl import metrics, resources, walkforward  # noqa: E402
from research.harness import core, round2  # noqa: E402
from research.harness.round2 import pullback, resize, trailing_exit, grade, strip  # noqa: E402

CRYPTO = ("BTCUSDT", "ETHUSDT")
OTHERS = ("XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")
ROUND3_VARIANTS = 8
N_CUM = 1902 + ROUND3_VARIANTS
HEAD, ALT = "fee_0.10%", "fee_0.05%"
CACHE = os.path.join(core.OUT_DIR, "r3_cache.json")
STATE = os.path.join(core.OUT_DIR, "loop_state.json")
Z = NormalDist().inv_cdf(1 - 0.05 / N_CUM)
NAMES = {"H32": "H32 vol-managed buy-and-hold core (spot)", "H33": "H33 vol-target + trail 4 ATR, ensemble direction (spot)",
         "H34": "H34 funding-aware 1.5x/0x trend core (spot)", "H35": "H35 H32 in positive hours only (spot)"}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ------------------------------------------------------------------ calendar-day momentum for markets that do not trade 24/7

def day_end_flags(index):
    d = index.normalize()
    out = np.zeros(len(index), dtype=bool)
    out[:-1] = d[1:] != d[:-1]
    return out


def mom_cal(bars, days, day_end):
    """Sign of the return over the last `days` calendar days, decided at each UTC day's last bar, held until the next."""
    c = bars["close"].values.astype(float)
    ct = core.store.to_ms(bars.index) + 900000                      # close times, epoch ms (any index unit)
    ref = ct - int(days) * 86400000
    k = np.searchsorted(ct, ref, side="right") - 1
    ret = np.where(k >= 0, np.log(c / c[np.maximum(k, 0)]), np.nan)
    tgt = np.full(len(c), np.nan)
    tgt[day_end] = np.sign(np.nan_to_num(ret[day_end], nan=0.0))
    return pd.Series(tgt).ffill().fillna(0.0).values


class Mkt:
    def __init__(self, asset):
        self.asset = asset
        self.crypto = asset in CRYPTO
        self.bars, self.fund = core.load(asset, dev_only=True)
        self.idx = self.bars.index
        self.feats = core.features(self.bars)
        self.wins = core.windows(self.idx)
        self.oos = walkforward.oos_mask(self.idx, self.wins)
        span_years = (self.idx[self.oos][-1] - self.idx[self.oos][0]).total_seconds() / (365.25 * 86400)
        self.bpy = core.BPY if self.crypto else float(self.oos.sum() / span_years)
        if not self.crypto:
            de = day_end_flags(self.idx)
            self.feats["is_daily"] = de
            self.feats["trend1d"] = mom_cal(self.bars, 30, de)
            ens = np.mean([mom_cal(self.bars, L, de) for L in (10, 20, 30, 60, 90)], axis=0)
        else:
            ens = None
        self.ex = round2.extra_features(self.bars, self.feats)
        self.ex["rv_ann"] = self.feats["rv672"].values * math.sqrt(self.bpy)
        if ens is not None:
            self.ex["ens"] = ens
        self.mkt = core.Market(self.bars, self.fund)
        self.fee = core.FEE_HEAD if self.crypto else CFG["asset_cost"][asset]
        self.c = self.bars["close"].values.astype(float)
        ones = np.ones(len(self.idx))
        bh = np.where(self.oos, ones, 0.0)
        self.bench = {"bh_spot": self.run(bh, True), "bh_perp": self.run(bh, False),
                      "momentum": self.run(np.where(self.oos, self.feats["trend1d"].values, 0.0), False)}

    # ---- the four registered rules
    def vt_want(self, direction):
        rv = np.where(self.ex["rv_ann"].values > 0, self.ex["rv_ann"].values, np.nan)
        k = np.nan_to_num(0.60 / rv, nan=1.0)
        return np.where(direction > 0, np.minimum(2.0, k), 0.0)

    def h32(self):
        return resize(self.vt_want(np.ones(len(self.c))))

    def h33(self):
        e = np.sign(self.ex["ens"].values)
        base = pullback(resize(self.vt_want(e)), self.feats, self.c)
        f2 = self.feats.copy()
        f2["trend1d"] = e
        return trailing_exit(base, f2, self.ex, self.c, 4.0)

    def h34(self):
        d = self.feats["trend1d"].values
        ok = np.ones(len(self.c), dtype=bool)
        if self.crypto and len(self.fund):
            r = pd.Series(np.asarray(self.fund["rate"], dtype=float))
            med = r.rolling(270, min_periods=90).median()
            flag = (r <= med).values & med.notna().values
            s = np.asarray(self.fund["settle_ms"], dtype="int64")
            close_ms = core.store.to_ms(self.idx) + 900000
            k = np.searchsorted(s, close_ms, side="right") - 1
            ok = np.where(k >= 0, flag[np.maximum(k, 0)], False)
        want = np.where(d > 0, np.where(ok, 1.5, 1.0), 0.0)
        return pullback(want, self.feats, self.c, on_increase=True)

    def h35(self):
        base = self.h32()
        hr_next = (self.idx + pd.Timedelta(minutes=15)).hour.values      # the hour of the bar the position is held over
        hr_bar = self.idx.hour.values
        tr, te = core.masks(self.idx, self.wins)
        out = np.zeros(len(self.c))
        chosen = []
        for i in range(len(self.wins)):
            allowed = set()
            for h in range(24):
                m = tr[i] & (hr_bar == h)
                if m.sum() > 50 and self.mkt.r_px[m].mean() > 0:
                    allowed.add(h)
            out[te[i]] = base[te[i]] * np.isin(hr_next[te[i]], list(allowed))
            chosen.append(len(allowed))
        self.h35_hours = chosen
        return out

    # ---- scoring
    def stats(self, r, pos):
        x = r[self.oos]
        eq = np.cumprod(1 + x)
        years = len(x) / self.bpy
        p = pos[self.oos]
        prev = pos[np.argmax(self.oos) - 1] if np.argmax(self.oos) > 0 else 0.0
        _, te = core.masks(self.idx, self.wins)
        s = pd.Series(x, index=self.idx[self.oos])
        yt = (1 + s).groupby(s.index.year).prod() - 1
        return {"cagr": metrics.cagr(x, self.bpy), "total_return": float(eq[-1] - 1), "sharpe": metrics.sharpe(x, self.bpy),
                "sortino": metrics.sortino(x, self.bpy), "max_drawdown": metrics.max_drawdown(np.concatenate([[1.0], eq])),
                "calmar": metrics.calmar(x, self.bpy), "years": years,
                "trades_per_year": float(np.count_nonzero(np.diff(p, prepend=prev)) / years),
                "avg_exposure": float(np.mean(np.abs(p))),
                "folds": [{"test_start": str(w["test_start"].date()), "total_return": float(np.prod(1 + r[m]) - 1),
                           "sharpe": metrics.sharpe(r[m], self.bpy)} for w, m in zip(self.wins, te)],
                "years_table": dict((int(k), float(v)) for k, v in yt.items())}

    def run(self, target, spot):
        out = {}
        fees = ((self.fee, HEAD), (core.FEE_ALT, ALT)) if self.crypto else ((self.fee, HEAD),)
        for fee, tag in fees:
            fr = self.mkt.frame(target, fee, spot)
            out[tag] = self.stats(fr["r_net"].values, fr["pos"].values)
            out[tag]["sharpe_gross"] = metrics.sharpe(fr["r_gross"].values[self.oos], self.bpy)
            if tag == HEAD:
                out["_r"] = fr["r_net"].values.copy()
                out["breakeven_fee"] = core.breakeven_fee(fr, self.oos)
        if ALT not in out:
            out[ALT] = out[HEAD]
        return out


def compute():
    resources.low_priority()
    R = {}
    for a in CRYPTO + OTHERS:
        f = resources.free_mb()
        while f is not None and f < 1000:
            log("waiting for memory (%.0f MB)" % f)
            time.sleep(30)
            f = resources.free_mb()
        t0 = time.time()
        m = Mkt(a)
        S = {}
        for h, fn in (("H32", m.h32), ("H33", m.h33), ("H34", m.h34), ("H35", m.h35)):
            res = m.run(np.where(m.oos, fn(), 0.0), True)
            g = grade(res, m.bench, m.idx, m.oos, N_CUM)
            g["sharpe_edge_needed"] = Z * g["bh_spot"]["se"]
            S[h] = {"res": res, "grade": g}
        R[a] = {"graded": m.crypto, "fee": m.fee, "bars_per_year": m.bpy, "bench": m.bench, "strategies": S,
                "h35_hours_kept_per_fold": getattr(m, "h35_hours", None)}
        log("%s done in %.0fs" % (a, time.time() - t0))
        for h, v in S.items():
            x = v["res"][HEAD]
            log("  %s CAGR %+6.1f%% Sharpe %.2f DD %3.0f%% tr/yr %5.0f rules %d/8 (B&H CAGR %+.1f%% Sharpe %.2f DD %.0f%%)" % (
                h, 100 * x["cagr"], x["sharpe"], 100 * x["max_drawdown"], x["trades_per_year"], v["grade"]["bh_spot"]["rules_met"],
                100 * m.bench["bh_spot"][HEAD]["cagr"], m.bench["bh_spot"][HEAD]["sharpe"], 100 * m.bench["bh_spot"][HEAD]["max_drawdown"]))
        del m
    out = strip(R)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f, default=float)
    return out


def pct(x, d=1):
    return "-" if x is None else "%+.*f%%" % (d, 100 * x)


def report(R):
    L = []
    w = L.append
    w("# Harness loop, round 3: vol management, better exits, fewer variants\n")
    w("Generated %s UTC by `py -3 research/harness/round3.py`. Paper research only. H32-H35 registered in "
      "`research/HYPOTHESES.md` at 14:13 UTC on 11 Nov 2026, before any round-3 result. Development data only (out of "
      "sample 2020-10-01 to 2025-11-11, 21 folds); sealed holdout untouched; 0 holdout looks used.\n"
      % time.strftime("%Y-%m-%d %H:%M", time.gmtime()))
    notes = os.path.join(HERE, "notes_round3.md")
    if os.path.exists(notes):
        with open(notes, encoding="utf-8") as f:
            w(f.read().strip() + "\n")
    w("## Rules (unchanged from round 2)\n")
    w("Per coin (BTC and ETH), against spot buy-and-hold: CAGR >= 25%%; CAGR > B&H; Sharpe > B&H and max DD <= B&H; "
      "Sharpe > B&H in >= half the folds; bootstrap p <= 0.05 / %d = %.1e (z >= %.2f); no fee-only-at-0.05%%; <= 100 "
      "trades a year; > half the folds positive.\n" % (N_CUM, 0.05 / N_CUM, Z))
    for a in CRYPTO:
        A = R[a]
        bs, bp, mo = A["bench"]["bh_spot"][HEAD], A["bench"]["bh_perp"][HEAD], A["bench"]["momentum"][HEAD]
        w("## %s (graded)\n" % a)
        w("| Strategy | CAGR | Sharpe | Max DD | Calmar | Trades/yr | Avg exposure | Fold share vs B&H | Folds positive | Sharpe edge (daily) | Edge needed | Boot p | DSR | Rules met (of 8) | Failing | Pass |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for h, v in A["strategies"].items():
            m, g = v["res"][HEAD], v["grade"]
            gs = g["bh_spot"]
            w("| %s | %s | %.2f | %.0f%% | %.2f | %.0f | %.2f | %.0f%% | %.0f%% | %+.2f | %.2f | %.3f | %.2f | %d | %s | %s |" % (
                NAMES[h], pct(m["cagr"]), m["sharpe"], 100 * m["max_drawdown"], m["calmar"], m["trades_per_year"],
                m["avg_exposure"], 100 * gs["fold_share"], 100 * gs["positive_fold_share"], gs["sharpe_minus_bh"],
                g["sharpe_edge_needed"], gs["p"], g["dsr"], gs["rules_met"],
                ", ".join(k for k, x in gs["rules"].items() if not x) or "none", "**YES**" if gs["pass"] else "no"))
        for nm, b in (("Buy-and-hold, spot", bs), ("Buy-and-hold, perp", bp), ("Momentum (daily, 30-day)", mo)):
            w("| %s | %s | %.2f | %.0f%% | %.2f | %.0f | | | | | | | | | | |" % (nm, pct(b["cagr"]), b["sharpe"],
                                                                           100 * b["max_drawdown"], b["calmar"], b["trades_per_year"]))
        yrs = sorted(int(y) for y in bs["years_table"])
        w("\n**Calendar-year returns, 0.10% a side (2020 from 1 Oct, 2025 to 10 Nov):**\n")
        w("| Strategy | " + " | ".join(str(y) for y in yrs) + " | Years beating spot B&H |")
        w("|---|" + "---|" * (len(yrs) + 1))
        rows = [("Buy-and-hold, spot", bs["years_table"]), ("Buy-and-hold, perp", bp["years_table"]), ("Momentum", mo["years_table"])]
        rows += [(NAMES[h], v["res"][HEAD]["years_table"]) for h, v in A["strategies"].items()]
        for nm, yt in rows:
            wins = sum(1 for y in yrs if yt[str(y)] > bs["years_table"][str(y)])
            w("| %s | %s | %d of %d |" % (nm, " | ".join(pct(yt[str(y)], 0) for y in yrs), wins, len(yrs)))
        m5 = dict((h, v["res"][ALT]) for h, v in A["strategies"].items())
        w("\nAt 0.05%% a side: %s.\n" % "; ".join("%s CAGR %s, Sharpe %.2f" % (h, pct(x["cagr"]), x["sharpe"]) for h, x in m5.items()))
        if A.get("h35_hours_kept_per_fold"):
            w("H35 hours kept per fold (of 24): %s.\n" % ", ".join(str(x) for x in A["h35_hours_kept_per_fold"]))
    w("## Other Mind 15 markets (robustness, report only; cannot pass or block a pass)\n")
    w("Same frozen rules; each market's fee a side; no funding; 'daily' = the last bar of each UTC day; momentum lookbacks "
      "in calendar days; leverage financing not modelled. Annualised with each market's own bars a year.\n")
    w("| Market | Fee/side | Buy-and-hold CAGR / Sharpe / DD | H32 | H33 | H34 | H35 | Momentum CAGR / Sharpe |")
    w("|---|---|---|---|---|---|---|---|")
    for a in OTHERS:
        if a not in R:
            continue
        A = R[a]
        b = A["bench"]["bh_spot"][HEAD]
        cell = lambda x, g: "%s / %.2f / %.0f%% (fold share %.0f%%, %.0f tr/yr)" % (
            pct(x["cagr"]), x["sharpe"], 100 * x["max_drawdown"], 100 * g["bh_spot"]["fold_share"], x["trades_per_year"])
        mo = A["bench"]["momentum"][HEAD]
        w("| %s | %.2f%% | %s / %.2f / %.0f%% | %s | %s | %s | %s | %s / %.2f |" % (
            a, 100 * A["fee"], pct(b["cagr"]), b["sharpe"], 100 * b["max_drawdown"],
            *[cell(A["strategies"][h]["res"][HEAD], A["strategies"][h]["grade"]) for h in ("H32", "H33", "H34", "H35")],
            pct(mo["cagr"]), mo["sharpe"]))
    w("")
    beat = dict((h, sum(1 for a in OTHERS if a in R and R[a]["strategies"][h]["res"][HEAD]["sharpe"] > R[a]["bench"]["bh_spot"][HEAD]["sharpe"]
                        and R[a]["strategies"][h]["res"][HEAD]["max_drawdown"] <= R[a]["bench"]["bh_spot"][HEAD]["max_drawdown"]))
                for h in ("H32", "H33", "H34", "H35"))
    w("Markets (of %d) where the rule has a higher Sharpe AND no deeper drawdown than buy-and-hold: %s.\n" % (
        len([a for a in OTHERS if a in R]), ", ".join("%s %d" % kv for kv in beat.items())))
    passes = [h for h in ("H32", "H33", "H34", "H35") if all(R[a]["strategies"][h]["grade"]["bh_spot"]["pass"] for a in CRYPTO)]
    w("## Round 3 result\n")
    w("- Development passes (all rules, BTC and ETH): %s." % (", ".join(passes) if passes else "**none**"))
    w("- Sharpe edge over spot buy-and-hold the significance rule now demands (z = %.2f x bootstrap standard error): "
      "%s." % (Z, "; ".join("%s %s: %.2f" % (a[:3], h, R[a]["strategies"][h]["grade"]["sharpe_edge_needed"])
                            for a in CRYPTO for h in ("H32", "H33", "H34"))))
    w("- Holdout looks used: 0. Cumulative variants: %d." % N_CUM)
    with open(os.path.join(core.OUT_DIR, "harness_report_round3.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    summ = {"schema": "harness_summary_round3/1", "generated_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "paper_only": True, "round": 3, "hypotheses": ["H32", "H33", "H34", "H35"], "variants_round3": ROUND3_VARIANTS,
            "variants_cumulative": N_CUM, "bonferroni_alpha": 0.05 / N_CUM, "z_needed": Z,
            "benchmark_for_pass": "spot buy-and-hold", "development_passes": passes, "results": R,
            "other_markets_report_only": list(OTHERS)}
    with open(os.path.join(core.OUT_DIR, "harness_summary_round3.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=float)
    st = {}
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            st = json.load(f)
    st["round"] = 3
    st["updated_utc"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    st.setdefault("variants_tried", {})["round_3"] = {"per_coin": 4, "coins": 2, "total": ROUND3_VARIANTS,
                                                      "other_markets_report_only": "4 rules x 6 markets, not counted"}
    st["variants_tried"]["total"] = N_CUM
    st["development_passes"] = st.get("development_passes", []) + [{"id": "R3-" + p} for p in passes]
    st["significance_edge_needed_round3"] = dict(("%s %s" % (a, h), R[a]["strategies"][h]["grade"]["sharpe_edge_needed"])
                                                 for a in CRYPTO for h in ("H32", "H33", "H34", "H35"))
    best = max(("H32", "H33", "H34", "H35"), key=lambda h: (sum(R[a]["strategies"][h]["grade"]["bh_spot"]["rules_met"] for a in CRYPTO),
                                                              R["BTCUSDT"]["strategies"][h]["res"][HEAD]["sharpe"]))
    st["round3_closest"] = {"id": "R3-" + best, "rules_met_btc": R["BTCUSDT"]["strategies"][best]["grade"]["bh_spot"]["rules_met"],
                            "rules_met_eth": R["ETHUSDT"]["strategies"][best]["grade"]["bh_spot"]["rules_met"], "of": 8}
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, default=float)
    log("round-3 report written; passes: %s" % (passes or "none"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.report:
        with open(CACHE, encoding="utf-8") as f:
            R = json.load(f)
    else:
        R = compute()
    report(R)


if __name__ == "__main__":
    main()
