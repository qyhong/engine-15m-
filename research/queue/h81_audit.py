# -*- coding: utf-8 -*-
"""AUDIT of the H81 side placebo (research only; registers nothing, changes nothing in placebo.py or the engine).

    python research/queue/h81_audit.py extract --fits-dir <fits_today> --out <folder> [--sides <H81 out folder>]
    python research/queue/h81_audit.py analyse --out <folder>
    python research/queue/h81_audit.py toy --out <folder>

extract: every real b_targets trade (placebo.py's own loader, book, gate and machine_r), scored with its own side AND
         the opposite side, with the stop, both targets and their basis for each side; month moves of each market.
         Checked against H81's own sides_<group>.json when --sides is given.
analyse: the decompositions (own vs flipped, 50/50, global share, the registered month permutation, the month share
         split by donors entered before / after the trade, causal shares, month direction vs the share of longs).
toy:     a random walk and a causal momentum rule scored with the same machinery, permuted within month as H81 does.
Data end at placebo.CUT (the holdout is not read: placebo.load_group enforces it).
"""
import argparse
import json
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import placebo as P  # noqa: E402
from engine15 import live  # noqa: E402


def basis_code(b):
    b = str(b)
    if b.startswith("Fibonacci 1.272 of the 1h"):
        return "fib1h"
    if b.startswith("Fibonacci 1.272 of the 4h"):
        return "fib4h"
    if b.startswith("Fibonacci 1.618"):
        return "fib"
    if b.startswith("a typical day"):
        return "reach"
    if b.startswith("1.5 x"):
        return "1.5R"
    if b.startswith("2 x"):
        return "2R"
    return b[:10]


# ------------------------------------------------------------------ extract (server)
def extract(args):
    os.makedirs(args.out, exist_ok=True)
    rows, months, checks = [], [], {}
    for g, assets in P.GROUPS:
        prep = P.load_group(g, assets, args.fits_dir, args.out, P.CUT)
        side_rec = None
        if args.sides:
            pth = os.path.join(args.sides, "sides_%s.json" % g)
            if os.path.exists(pth):
                side_rec = json.load(open(pth))
        for a in assets:
            ctx = P.market_ctx(prep, a)
            cur = P.run_book(ctx, P.RULE_CURRENT)
            ok, bad = P.replay_gate(ctx, cur["trades"])
            s = P.real_slots(cur["trades"])
            px, unit, cfg, tms, n = ctx["inp"]["px"], ctx["inp"]["unit"], ctx["cfg"], ctx["tms"], ctx["n"]
            fee = cfg["cost_side"]
            tr = cur["trades"]
            max_dev = 0.0
            for j in range(len(s["side"])):
                i0, p, sd0 = int(s["i_in"][j]), float(s["p_in"][j]), int(s["side"][j])
                e = P.cap_bar(tms, i0, n)
                rec = {"market": a, "j": j, "i_in": i0, "t_in": str(prep["times"][i0])[:16],
                       "month": int(ctx["month"][i0]), "h2": bool(i0 >= ctx["mid"]), "side": sd0, "p_in": p,
                       "book_r": float(s["r"][j]), "book_exit": str(tr.why_out.values[j]), "i_out": int(s["i_out"][j]),
                       "cap_bar": e, "cap_at_end": bool(e == n - 1), "p_cap": float(px["close"][e])}
                dist = cfg["stop_units"] * unit[i0 - 1]
                rec["dist"] = float(dist)
                rec["fee_rt_r"] = float(2 * fee * p / dist) if dist else np.nan
                for tag, sd in (("own", sd0), ("flip", -sd0)):
                    stop = p - sd * dist
                    t = live.plan_targets(sd, p, float(stop), ctx["trow"](i0 - 1))
                    r, word, jo = P.replay_trade(sd, i0, p, i0 - 1, e, False, px, unit, cfg, ctx["trow"])
                    rm = P.machine_r(ctx, sd, i0, p)
                    if np.isfinite(r) or np.isfinite(rm):
                        max_dev = max(max_dev, abs(r - rm))
                    t1, t2 = t.get("target_1"), t.get("target_2")
                    rec.update({
                        tag + "_stop": float(stop), tag + "_t1": t1, tag + "_t2": t2,
                        tag + "_t1_basis": basis_code(t.get("target_1_basis")),
                        tag + "_t2_basis": basis_code(t.get("target_2_basis")),
                        tag + "_t1_r": (sd * (t1 - p) / dist) if (t1 is not None and dist) else np.nan,
                        tag + "_t2_r": (sd * (t2 - p) / dist) if (t2 is not None and dist) else np.nan,
                        tag + "_stop_ok": bool(sd * (p - stop) > 0),
                        tag + "_r": float(r), tag + "_exit": word, tag + "_i_exit": int(jo),
                        tag + "_hold_d": float((tms[jo] - tms[i0]) / P.DAY_MS)})
                rows.append(rec)
            chk = {"gate_ok": bool(ok), "gate_bad": int(bad), "trades": int(len(s["side"])),
                   "max_dev_vs_machine_r": float(max_dev)}
            if side_rec is not None:
                m = side_rec["markets"][a]
                mine = [r for r in rows if r["market"] == a]
                rp = np.array([r["own_r"] if r["side"] == 1 else r["flip_r"] for r in mine])
                rm_ = np.array([r["flip_r"] if r["side"] == 1 else r["own_r"] for r in mine])
                chk["same_sides_as_H81"] = bool(np.array_equal(np.array(m["side"]), s["side"]))
                chk["max_dev_r_plus_vs_H81"] = float(np.nanmax(np.abs(rp - np.array(m["r_plus"], dtype=float))))
                chk["max_dev_r_minus_vs_H81"] = float(np.nanmax(np.abs(rm_ - np.array(m["r_minus"], dtype=float))))
            checks[a] = chk
            P.log("%s: %s" % (a, chk))
            # month moves (first open to last close of the bars the book could trade in)
            lo = ctx["lo"]
            mo = ctx["month"][lo:n]
            o, c, u = px["open"][lo:n], px["close"][lo:n], unit[lo:n]
            for mv in np.unique(mo):
                ix = np.flatnonzero(mo == mv)
                months.append({"market": a, "month": int(mv), "ret_pct": float(100 * (c[ix[-1]] / o[ix[0]] - 1)),
                               "move_units": float((c[ix[-1]] - o[ix[0]]) / np.nanmedian(u[ix]))})
            del cur
        del prep
    pd.DataFrame(rows).to_csv(os.path.join(args.out, "audit_trades.csv"), index=False)
    pd.DataFrame(months).to_csv(os.path.join(args.out, "audit_months.csv"), index=False)
    json.dump(checks, open(os.path.join(args.out, "audit_checks.json"), "w"), indent=1)
    P.log("extract done")


# ------------------------------------------------------------------ analyse
def cells(df):
    yield "BTCUSDT", df[df.market == "BTCUSDT"]
    yield "ETHUSDT", df[df.market == "ETHUSDT"]
    yield "vault (BTC+ETH)", df[df.market.isin(P.VAULT)]
    yield "others (6)", df[~df.market.isin(P.VAULT)]
    yield "pooled (8)", df


def month_share_parts(d):
    """Per trade: expected R under the registered permutation, split by donors (self / earlier / later in the month)."""
    out = {"E_perm": [], "E_loo": [], "E_before": [], "E_after": [], "has_b": [], "has_a": [], "E_prevmonth": [],
           "E_prev10": []}
    for a, dm in d.groupby("market", sort=False):
        dm = dm.sort_values("i_in")
        side = dm.side.values
        rp, rmn = dm.rp.values, dm.rm.values
        mo = dm.month.values
        share = dm.groupby("month").side.apply(lambda x: float((x == 1).mean()))
        for k in range(len(dm)):
            same = np.flatnonzero(mo == mo[k])
            sl = side[same]
            s_all = (sl == 1).mean()
            out["E_perm"].append(s_all * rp[k] + (1 - s_all) * rmn[k])
            oth = same[same != k]
            if len(oth):
                s = (side[oth] == 1).mean()
                out["E_loo"].append(s * rp[k] + (1 - s) * rmn[k])
            else:
                out["E_loo"].append(np.nan)
            b, af = same[same < k], same[same > k]
            for nm, ix in (("before", b), ("after", af)):
                if len(ix):
                    s = (side[ix] == 1).mean()
                    out["E_" + nm].append(s * rp[k] + (1 - s) * rmn[k])
                else:
                    out["E_" + nm].append(np.nan)
            out["has_b"].append(len(b) > 0)
            out["has_a"].append(len(af) > 0)
            pm = share.get(mo[k] - 1, np.nan)
            out["E_prevmonth"].append(pm * rp[k] + (1 - pm) * rmn[k] if pm == pm else np.nan)
            prev = side[max(0, k - 10):k]
            if len(prev):
                s = (prev == 1).mean()
                out["E_prev10"].append(s * rp[k] + (1 - s) * rmn[k])
            else:
                out["E_prev10"].append(np.nan)
    return dict((k, np.asarray(v, dtype=float)) for k, v in out.items())


def analyse(args):
    df = pd.read_csv(os.path.join(args.out, "audit_trades.csv"))
    mo = pd.read_csv(os.path.join(args.out, "audit_months.csv"))
    df = df[np.isfinite(df.own_r) & np.isfinite(df.flip_r)].copy()
    df["rp"] = np.where(df.side == 1, df.own_r, df.flip_r)
    df["rm"] = np.where(df.side == 1, df.flip_r, df.own_r)
    res = {"cells": {}, "targets": {}, "month_dir": {}, "react": {}, "exits": {}}
    rng = np.random.default_rng(81)
    for name, d in cells(df):
        d = d.sort_values(["market", "i_in"])
        mk = d.market.map(P.MARKETS.index).values
        grp = mk * 100000 + d.month.values
        rp, rm_, side = d.rp.values, d.rm.values, d.side.values
        glob = d.groupby("market").side.transform(lambda x: float((x == 1).mean())).values
        parts = month_share_parts(d)
        perm, half = [], []
        for k in range(300):
            src = P.permute_within(grp, P.draw_rng(P.STUDIES["H81"]["seed"], k))
            perm.append(np.where(side[src] == 1, rp, rm_).mean())
            sd = np.where(rng.random(len(d)) < 0.5, 1, -1)
            half.append(np.where(sd == 1, rp, rm_).mean())
        perm, half = np.array(perm), np.array(half)
        hb, ha = parts["has_b"].astype(bool), parts["has_a"].astype(bool)
        both = hb & ha
        c = {
            "n": int(len(d)),
            "own_mean": float(d.own_r.mean()),
            "flip_mean": float(d.flip_r.mean()),
            "own_plus_flip_mean": float((d.own_r + d.flip_r).mean()),
            "minus_2_roundtrip_fees_r": float(-2 * d.fee_rt_r.mean()),
            "all_long_mean": float(rp.mean()), "all_short_mean": float(rm_.mean()),
            "long_share": float((side == 1).mean()),
            "half_half_expected": float(((rp + rm_) / 2).mean()),
            "half_half_q05_q95": [float(np.quantile(half, .05)), float(np.quantile(half, .95))],
            "global_share_expected": float((glob * rp + (1 - glob) * rm_).mean()),
            "month_perm_expected": float(np.nanmean(parts["E_perm"])),
            "month_perm_300_median": float(np.median(perm)),
            "month_perm_300_q05_q95": [float(np.quantile(perm, .05)), float(np.quantile(perm, .95))],
            "month_loo_expected": float(np.nanmean(parts["E_loo"])),
            "n_with_before_and_after": int(both.sum()),
            "own_mean_on_those": float(d.own_r.values[both].mean()),
            "donors_before_expected": float(np.nanmean(parts["E_before"][both])),
            "donors_after_expected": float(np.nanmean(parts["E_after"][both])),
            "prev_month_share_expected": float(np.nanmean(parts["E_prevmonth"])),
            "prev_month_n": int(np.isfinite(parts["E_prevmonth"]).sum()),
            "prev_10_trades_share_expected": float(np.nanmean(parts["E_prev10"])),
            "own_mean_h1": float(d.own_r[~d.h2].mean()), "own_mean_h2": float(d.own_r[d.h2].mean()),
            "perm_expected_h1": float(np.nanmean(parts["E_perm"][~d.h2.values])),
            "perm_expected_h2": float(np.nanmean(parts["E_perm"][d.h2.values])),
            "cap_at_data_end": int(d.cap_at_end.sum()),
        }
        res["cells"][name] = c
        # targets: own vs flipped
        res["targets"][name] = {
            "own_t1_basis": d.own_t1_basis.value_counts(normalize=True).round(3).to_dict(),
            "flip_t1_basis": d.flip_t1_basis.value_counts(normalize=True).round(3).to_dict(),
            "own_t1_r_median": float(d.own_t1_r.median()), "flip_t1_r_median": float(d.flip_t1_r.median()),
            "own_t2_r_median": float(d.own_t2_r.median()), "flip_t2_r_median": float(d.flip_t2_r.median()),
            "own_t1_r_min": float(d.own_t1_r.min()), "flip_t1_r_min": float(d.flip_t1_r.min()),
            "stop_wrong_side": int((~d.own_stop_ok).sum() + (~d.flip_stop_ok).sum()),
            "t1_wrong_side": int(((d.own_t1_r <= 0) | (d.flip_t1_r <= 0)).sum()),
            "t2_not_beyond_t1": int(((d.own_t2_r <= d.own_t1_r) | (d.flip_t2_r <= d.flip_t1_r)).sum()),
        }
        res["exits"][name] = {
            "own": d.own_exit.value_counts(normalize=True).round(3).to_dict(),
            "flip": d.flip_exit.value_counts(normalize=True).round(3).to_dict(),
            "own_mean_r_by_exit": d.groupby("own_exit").own_r.mean().round(3).to_dict(),
            "flip_mean_r_by_exit": d.groupby("flip_exit").flip_r.mean().round(3).to_dict(),
            # the same trades, flipped, with Target 1 forced to the same basis family as own (reach vs fib)
            "own_minus_flip_when_both_reach": float((d.own_r - d.flip_r)[(d.own_t1_basis == "reach")
                                                                         & (d.flip_t1_basis == "reach")].mean()),
            "n_both_reach": int(((d.own_t1_basis == "reach") & (d.flip_t1_basis == "reach")).sum()),
            "own_minus_flip_when_own_fib": float((d.own_r - d.flip_r)[d.own_t1_basis.str.startswith("fib")].mean()),
            "n_own_fib": int(d.own_t1_basis.str.startswith("fib").sum()),
        }
        # reactivity: does the next trade's side follow the move since the previous entry?
        agree, mvs = [], []
        for a, dm in d.groupby("market"):
            dm = dm.sort_values("i_in")
            mv = np.sign(np.diff(dm.p_in.values))
            agree += list(dm.side.values[1:] == mv)
            mvs += list(mv)
        res["react"][name] = {"next_side_follows_move_since_last_entry": float(np.mean(agree)), "pairs": len(agree)}
        # the month's own direction against its share of longs
        sh = d.groupby(["market", "month"]).side.apply(lambda x: float((x == 1).mean())).rename("share").reset_index()
        m2 = sh.merge(mo, on=["market", "month"], how="left").sort_values(["market", "month"])
        m2["prev_units"] = m2.groupby("market").move_units.shift(1)
        m2["next_units"] = m2.groupby("market").move_units.shift(-1)
        res["month_dir"][name] = {
            "months": int(len(m2)),
            "corr_share_vs_this_month_move": float(m2[["share", "move_units"]].corr().iloc[0, 1]),
            "corr_share_vs_prev_month_move": float(m2[["share", "prev_units"]].corr().iloc[0, 1]),
            "corr_share_vs_next_month_move": float(m2[["share", "next_units"]].corr().iloc[0, 1]),
            "sign_agree_share_vs_this_month": float(np.mean(np.sign(m2.share - 0.5)[m2.share != 0.5]
                                                            == np.sign(m2.move_units)[m2.share != 0.5])),
        }
    # concrete trades: BTC/ETH, flipped better, one each by kind
    v = df[df.market.isin(P.VAULT)].copy()
    v["gain"] = v.flip_r - v.own_r
    cols = ["market", "t_in", "side", "p_in", "dist", "own_stop", "own_t1", "own_t1_basis", "own_t2", "own_exit",
            "own_hold_d", "own_r", "flip_stop", "flip_t1", "flip_t1_basis", "flip_t2", "flip_exit", "flip_hold_d",
            "flip_r", "book_exit", "book_r"]
    ex = pd.concat([v.sort_values("gain").tail(2), v.sample(4, random_state=7)])[cols]
    res["examples"] = json.loads(ex.to_json(orient="records"))
    json.dump(res, open(os.path.join(args.out, "audit_results.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


# ------------------------------------------------------------------ toy: random walk, causal rules, same machinery
def toy(args):
    rng = np.random.default_rng(2026)
    years, per_day = 6, 96
    nbar = years * 365 * per_day
    ret = rng.standard_normal(nbar) * 0.003                    # ~ 3% a day, no drift: a martingale (log price)
    close = 30000 * np.exp(np.cumsum(ret))
    op = np.r_[close[0], close[:-1]]
    hi = np.maximum(op, close) * np.exp(np.abs(rng.standard_normal(nbar)) * 0.001)
    lo_ = np.minimum(op, close) * np.exp(-np.abs(rng.standard_normal(nbar)) * 0.001)
    px = {"open": op, "high": hi, "low": lo_, "close": close}
    unit = np.full(nbar, 0.012 * 30000)
    unit = close * 0.012                                        # a stop unit ~ 1.2% of price (2 units = 2.4%)
    tms = np.arange(nbar, dtype="int64") * 900000
    month = (tms // (30 * P.DAY_MS)).astype("int64")
    cfg = {"cost_side": 0.001, "stop_units": 2.0}
    empty = (lambda k: {})                                      # no readings: Target 1 = 1.5R, Target 2 = 2R
    out = {}
    for rule in ("momentum_3d", "reversal_3d", "coin"):
        i0s, sides = [], []
        t = 3 * per_day + 1
        while t < nbar - 2:
            if rule == "coin":
                sd = 1 if rng.random() < 0.5 else -1
            else:
                mv = close[t - 1] - close[t - 1 - 3 * per_day]
                sd = (1 if mv > 0 else -1) * (1 if rule == "momentum_3d" else -1)
            i0s.append(t)
            sides.append(sd)
            t += int(rng.integers(per_day // 2, 4 * per_day))   # about one entry every 2 days, like the book
        i0s, sides = np.array(i0s), np.array(sides)
        rp, rm_ = np.empty(len(i0s)), np.empty(len(i0s))
        for k, i0 in enumerate(i0s):
            e = P.cap_bar(tms, i0, nbar)
            p = close[i0 - 1]
            rp[k] = P.replay_trade(1, i0, p, i0 - 1, e, False, px, unit, cfg, empty)[0]
            rm_[k] = P.replay_trade(-1, i0, p, i0 - 1, e, False, px, unit, cfg, empty)[0]
        real = np.where(sides == 1, rp, rm_).mean()
        grp = month[i0s]
        perm = [np.where(sides[P.permute_within(grp, P.draw_rng(1, k))] == 1, rp, rm_).mean() for k in range(300)]
        # causal donors only: each trade gets the side of a random EARLIER trade of the same month (else its own)
        caus = []
        for k in range(300):
            r2 = np.random.default_rng([7, k])
            sd2 = sides.copy()
            for i in range(len(sides)):
                same = np.flatnonzero((grp == grp[i]) & (np.arange(len(sides)) <= i))
                sd2[i] = sides[same[int(r2.integers(len(same)))]]
            caus.append(np.where(sd2 == 1, rp, rm_).mean())
        out[rule] = {"trades": int(len(i0s)), "real_mean_r": float(real),
                     "fee_rt_r": float(2 * 0.001 / 0.024),
                     "month_perm_median": float(np.median(perm)),
                     "month_perm_q05_q95": [float(np.quantile(perm, .05)), float(np.quantile(perm, .95))],
                     "p_upper_vs_300": float((np.sum(np.array(perm) >= real) + 1) / 301),
                     "earlier_donor_perm_median": float(np.median(caus))}
        P.log("toy %s: %s" % (rule, out[rule]))
    json.dump(out, open(os.path.join(args.out, "audit_toy.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("extract", "analyse", "toy"))
    ap.add_argument("--fits-dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sides")
    a = ap.parse_args(argv)
    t0 = time.time()
    {"extract": extract, "analyse": analyse, "toy": toy}[a.cmd](a)
    P.log("%s done in %.0fs" % (a.cmd, time.time() - t0))


if __name__ == "__main__":
    main()
