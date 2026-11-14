# -*- coding: utf-8 -*-
"""report4 -- the Phase 4 report: overfitting flags, the plain verdict, the markdown report and phase4_summary.json."""
import math

import numpy as np

from .report3 import (_variant_flags, bench_stats, clean, fee_s, fold_wins, pct, row_stats, seed_names, stitched,
                      trades_per_year)

HEAD, ALT = "fee_0.10%", "fee_0.05%"
LABELS = {
    "q_pool2_full": "Q agent, BTC+ETH pooled, expanding, readings",
    "sp_pool2_full": "SP agent, BTC+ETH pooled, expanding, readings",
    "sp_pool8_full": "SP agent, 8 markets pooled, expanding, readings",
    "sp_pool2_p3": "SP agent, BTC+ETH pooled, expanding, Phase 3 inputs",
    "sp_single_full": "SP agent, one asset, expanding, readings",
    "sp_single_p3": "SP agent, one asset, expanding, Phase 3 inputs",
    "sp_single12_full": "SP agent, one asset, 12-month window, readings",
    "sp_single12_p3": "SP agent, one asset, 12-month window, Phase 3 inputs",
    "phase3_agent_c": "Phase 3 agent (c), continual + retrain [Phase 3 primary]",
    "phase3_agent_a": "Phase 3 agent (a), static per fold",
}
BENCH = [("buy_hold", "Buy-and-hold (perp)"), ("buy_hold_spot", "Buy-and-hold (spot)"),
         ("momentum", "Momentum (daily 30-day, long/short)"), ("random", "Random agent (mean of 10)"),
         ("buy_hold_risk3", "*reference: buy-and-hold through the Phase 3 risk manager*"),
         ("momentum_risk3", "*reference: momentum through the Phase 3 risk manager*")]
YEARS_FULL = 6.11


def label(v, cfg=None):
    return LABELS.get(v, v)


def order(res):
    p = res["config"]["primary"]
    return [p] + [v for v in res["config"]["variants"] if v != p]


# ---------------------------------------------------------------- flags
def train_gap(res, asset, vname, span="full"):
    A = res["assets"][asset]
    v = A["fees"][HEAD]["variants"].get(vname) if span == "full" else A["fees"][HEAD]["dev"]["variants"].get(vname)
    tr = A["training"].get(vname)
    if v is None or not tr:
        return None
    trs, vas, tes, fb = [], [], [], []
    for s in seed_names(v):
        for i, r in enumerate(tr.get(s, [])):
            if i >= len(v["seeds"][s]["windows"]):
                break
            trs.append(r["train_sharpe"])
            vas.append(r["val_sharpe"])
            tes.append(v["seeds"][s]["windows"][i]["sharpe"])
            fb.append(bool(r["fallback"]))
    if not trs:
        return None
    return {"train": float(np.mean(trs)), "val": float(np.mean(vas)), "test": float(np.mean(tes)),
            "gap": float(np.mean(trs) - np.mean(tes)), "fallback_share": float(np.mean(fb))}


def flags(res):
    fc = res["config"]["flags"]
    out = {}
    for asset in res["assets"]:
        fa = {}
        for vname in order(res):
            fl = _variant_flags(res, asset, vname, fc, "full")
            g = train_gap(res, asset, vname)
            if g:
                fl.insert(0, {"id": "train_test_sharpe_gap", "fired": bool(g["gap"] > fc["train_test_sharpe_gap"]),
                              "value": round(g["gap"], 3),
                              "detail": "mean over folds and seeds: train-slice Sharpe %.2f, validation %.2f, test %.2f; gap "
                                        "%.2f (threshold %.1f); neutral fallback in %.0f%% of fold models"
                                        % (g["train"], g["val"], g["test"], g["gap"], fc["train_test_sharpe_gap"],
                                           100 * g["fallback_share"])})
            fa[vname] = fl
        out[asset] = fa
    return out


# ---------------------------------------------------------------- verdict
def edge(v, years):
    """Edge before costs of a variant (seed values): gross Sharpe, its t-stat (Sharpe x sqrt(years)), break-even fee."""
    names = seed_names(v)
    g = [float(v["seeds"][s]["stitched"]["sharpe_gross"]) for s in names]
    be = [v["seeds"][s].get("break_even_fee") for s in names]
    be = [None if x is None else float(x) if not isinstance(x, str) else float(x) for x in be]
    return {"gross_sharpe_by_seed": g, "gross_sharpe_mean": float(np.mean(g)),
            "t_stat_mean": float(np.mean(g) * math.sqrt(years)), "break_even_by_seed": be,
            "edge_every_seed": bool(all(x > 0 for x in g) and all(b is not None and b > 0 for b in be))}


def judge_variant(r, r5, vname, span_years):
    v = r["variants"][vname]
    bh, mo = r["bench"]["buy_hold"]["stitched"], r["bench"]["momentum"]["stitched"]
    st = row_stats(v)
    sh, cal = stitched(v, "sharpe"), stitched(v, "calmar")
    d = {"sharpe_mean": st["sharpe"], "calmar_mean": st["calmar"], "return_mean": st["total_return"],
         "max_dd_mean": st["max_drawdown"], "turnover_mean": st["turnover_per_year"],
         "seeds_beating_bh_sharpe": int(sum(x > bh["sharpe"] for x in sh)),
         "seeds_beating_mom_sharpe": int(sum(x > mo["sharpe"] for x in sh)), "seeds": len(sh),
         "break_even_fee": st["break_even_fee"], "sharpe_at_005": row_stats(r5["variants"][vname])["sharpe"],
         "sharpe_by_seed": sh}
    d["beats_bh"] = bool(st["sharpe"] > bh["sharpe"] and d["seeds_beating_bh_sharpe"] == len(sh) and st["calmar"] > bh["calmar"])
    d["beats_momentum"] = bool(st["sharpe"] > mo["sharpe"] and d["seeds_beating_mom_sharpe"] == len(sh)
                               and st["calmar"] > mo["calmar"])
    d["edge"] = edge(v, span_years)
    return d


def verdict(res):
    p = res["config"]["primary"]
    out = {"primary": p, "assets": {}}
    for asset, A in res["assets"].items():
        a = {}
        for span in ("full", "dev"):
            r = A["fees"][HEAD] if span == "full" else A["fees"][HEAD]["dev"]
            r5 = A["fees"][ALT] if span == "full" else A["fees"][ALT]["dev"]
            yrs = r["bench"]["buy_hold"]["stitched"]["years"]
            vs = dict((vn, judge_variant(r, r5, vn, yrs)) for vn in r["variants"])
            a[span] = {"variants": vs, "bh_sharpe": r["bench"]["buy_hold"]["stitched"]["sharpe"],
                       "mom_sharpe": r["bench"]["momentum"]["stitched"]["sharpe"],
                       "bh_calmar": r["bench"]["buy_hold"]["stitched"]["calmar"],
                       "mom_calmar": r["bench"]["momentum"]["stitched"]["calmar"], "years": yrs,
                       "winners": [k for k, d in vs.items() if d["beats_bh"] and d["beats_momentum"]]}
            if span == "dev" and "baseline_A" in r["bench"]:
                a[span]["A_sharpe"] = r["bench"]["baseline_A"]["stitched"]["sharpe"]
                a[span]["B_sharpe"] = r["bench"]["baseline_B"]["stitched"]["sharpe"]
        out["assets"][asset] = a
    b = out["assets"]["BTCUSDT"]["full"]
    pv = b["variants"][p]
    e = pv["edge"]
    edge_txt = ("an edge before costs on every seed (gross Sharpe %s, mean %.2f, t about %.1f; break-even fee %s)"
                % (", ".join("%.2f" % x for x in e["gross_sharpe_by_seed"]), e["gross_sharpe_mean"], e["t_stat_mean"],
                   ", ".join(fee_s(x) for x in e["break_even_by_seed"]))
                if e["edge_every_seed"] else
                "no reliable edge before costs (gross Sharpe by seed %s, mean %.2f, t about %.1f; break-even fee by seed %s)"
                % (", ".join("%.2f" % x for x in e["gross_sharpe_by_seed"]), e["gross_sharpe_mean"], e["t_stat_mean"],
                   ", ".join(fee_s(x) for x in e["break_even_by_seed"])))
    both = pv["beats_bh"] and pv["beats_momentum"]
    head = ("%s. Out of sample (Oct 2020 - Nov 2026, BTC, the headline), the Phase 4 primary agent (%s) shows %s. After "
            "0.10%% fees it %s buy-and-hold and momentum risk-adjusted across seeds: seed-mean Sharpe %.2f (seeds above "
            "buy-and-hold's %.2f: %d of %d; above momentum's %.2f: %d of %d), Calmar %.2f vs %.2f and %.2f, net return %s."
            % ("YES" if both else "NO", label(p), edge_txt, "beats" if both else "does not beat", pv["sharpe_mean"],
               b["bh_sharpe"], pv["seeds_beating_bh_sharpe"], pv["seeds"], b["mom_sharpe"], pv["seeds_beating_mom_sharpe"],
               pv["seeds"], pv["calmar_mean"], b["bh_calmar"], b["mom_calmar"], pct(pv["return_mean"], 0)))
    if b["winners"]:
        head += (" Variants beating both on every seed: %s; with %d variants tried, treat that as a lead to re-test forward, "
                 "not as proof." % (", ".join(label(w) for w in b["winners"]), len(b["variants"])))
    else:
        head += " None of the %d Phase 4 variants beats both on every seed." % len(b["variants"])
    out["text"] = head
    out["edge_before_costs"] = bool(e["edge_every_seed"])
    out["beats_both"] = bool(both)
    return out


# ---------------------------------------------------------------- tables
def _st(v):
    """Row stats of a variant (seed mean) or a single evaluation."""
    if "seeds" in v:
        return row_stats(v)
    st = bench_stats(v)
    st.setdefault("sharpe_gross", st.get("sharpe_gross"))
    return st


def _cells(st):
    g = st.get("sharpe_gross")
    return [pct(st["total_return"]), "%.2f" % st["sharpe"], "%.2f" % st["sortino"], "%.0f%%" % (100 * st["max_drawdown"]),
            "%.2f" % st["calmar"], "%.0f" % st["turnover_per_year"], "%.0f" % st["trades_per_year"],
            "%.0f" % st["avg_holding_hours"], "%.1f%%" % (100 * st["cost_drag_per_year"]),
            "-" if g is None else "%.2f" % g, fee_s(st.get("break_even_fee"))]


HDR = ("| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr "
       "| Gross Sharpe | Break-even fee |\n|---|---|---|---|---|---|---|---|---|---|---|---|")


def _row(lbl, st, bold=False):
    c = _cells(st)
    if bold:
        return "| **%s** | " % lbl + " | ".join("**%s**" % x for x in c) + " |"
    return "| %s | " % lbl + " | ".join(c) + " |"


def _random_st(rs, years):
    st = dict((k, v["mean"]) for k, v in rs["stitched"].items())
    st["trades_per_year"] = st.get("trades", 0) / max(years, 1e-9)
    st["break_even_fee"] = "n/a"
    st["sharpe_gross"] = None
    st["sortino"] = st.get("sortino", 0.0)
    return st


def table(res, asset, fee, span, primary):
    A = res["assets"][asset]
    r = A["fees"][fee] if span == "full" else A["fees"][fee]["dev"]
    rows = [HDR]
    for vn in order(res):
        v = r["variants"][vn]
        st = row_stats(v)
        rows.append(_row("%s%s, mean of %d seeds" % (label(vn), " [primary]" if vn == primary else "", len(v["seeds"])), st,
                         bold=vn == primary))
        if vn == primary:
            for s in seed_names(v):
                x = bench_stats(v["seeds"][s])
                rows.append(_row("&nbsp;&nbsp;seed %s" % s, x))
    for nm, v in (r.get("phase3") or {}).items():
        rows.append(_row("%s, mean of %d seeds" % (label(nm), len(v["seeds"])), row_stats(v)))
    for key, lbl in BENCH:
        if key not in r["bench"]:
            continue
        if key == "random":
            rows.append(_row(lbl, _random_st(r["bench"]["random"], r["bench"]["buy_hold"]["stitched"]["years"])))
        else:
            rows.append(_row(lbl, bench_stats(r["bench"][key])))
    if span == "dev":
        for key, lbl in (("baseline_A", "A: loop H29 H30 1.5x/0x spot"), ("baseline_B", "B: loop H29 H31 trail 4 ATR spot")):
            if key in r["bench"]:
                rows.append(_row(lbl, bench_stats(r["bench"][key])))
    return "\n".join(rows)


def seed_table(res, asset, span="full"):
    A = res["assets"][asset]
    r = A["fees"][HEAD] if span == "full" else A["fees"][HEAD]["dev"]
    r5 = A["fees"][ALT] if span == "full" else A["fees"][ALT]["dev"]
    names = seed_names(r["variants"][order(res)[0]])
    hdr = "| Variant | " + " | ".join("seed %s" % s for s in names) + " | mean, 0.10% | mean, 0.05% |\n|---|" + "---|" * (len(names) + 2)
    rows = [hdr]
    for vn in order(res):
        v, v5 = r["variants"][vn], r5["variants"][vn]
        cells = []
        for s in names:
            a, b = v["seeds"][s], v5["seeds"][s]
            cells.append("%.2f / %s / %s (0.05%%: %.2f)" % (a["stitched"]["sharpe"], pct(a["stitched"]["total_return"], 0),
                                                           fee_s(a.get("break_even_fee")), b["stitched"]["sharpe"]))
        m, m5 = row_stats(v), row_stats(v5)
        rows.append("| %s | %s | %.2f / %s | %.2f / %s |" % (label(vn), " | ".join(cells), m["sharpe"], pct(m["total_return"], 0),
                                                           m5["sharpe"], pct(m5["total_return"], 0)))
    return "\n".join(rows)


def edge_table(res):
    rows = ["| Variant | Asset | Span | Gross Sharpe by seed | Mean | t (approx.) | Break-even fee by seed | Net Sharpe 0.10% (mean) |",
            "|---|---|---|---|---|---|---|---|"]
    V = res["verdict"]["assets"]
    for vn in order(res):
        for asset in res["assets"]:
            for span in ("full", "dev"):
                d = V[asset][span]["variants"][vn]
                e = d["edge"]
                rows.append("| %s | %s | %s | %s | %.2f | %.1f | %s | %.2f |" % (
                    label(vn), asset, "2020-10 .. 2026-11" if span == "full" else "to 2025-11-11",
                    ", ".join("%.2f" % x for x in e["gross_sharpe_by_seed"]), e["gross_sharpe_mean"], e["t_stat_mean"],
                    ", ".join(fee_s(x) for x in e["break_even_by_seed"]), d["sharpe_mean"]))
    return "\n".join(rows)


def ablation_table(res):
    rows = ["| Variant | Model | Data | Inputs | BTC net Sharpe | BTC gross | ETH net Sharpe | ETH gross | train / val / test Sharpe (BTC) | neutral folds (BTC) | rows per model, last fold |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    cfgv = res["config"]["variants"]
    for vn in order(res):
        v = cfgv[vn]
        cells = []
        for asset in ("BTCUSDT", "ETHUSDT"):
            if asset not in res["assets"]:
                cells += ["-", "-"]
                continue
            st = row_stats(res["assets"][asset]["fees"][HEAD]["variants"][vn])
            cells += ["%.2f" % st["sharpe"], "%.2f" % st["sharpe_gross"]]
        g = train_gap(res, "BTCUSDT", vn)
        tr = res["assets"]["BTCUSDT"]["training"][vn]
        last = [x[-1].get("rows_refit") for x in tr.values()]
        data = {"single": "one asset", "pool2": "BTC+ETH", "pool8": "8 markets"}[v["pool"]] + (
            ", 12-month window" if v["window"] == "window12" else ", expanding from 2019")
        rows.append("| %s | %s | %s | %s | %s | %s | %.2f / %.2f / %.2f | %.0f%% | %s |" % (
            vn, v["model"].upper(), data, "Phase 3" if v["inputs"] == "p3" else "Phase 3 + readings", " | ".join(cells[:2]),
            " | ".join(cells[2:]), g["train"], g["val"], g["test"], 100 * g["fallback_share"],
            "{:,}".format(int(np.mean([x for x in last if x]))) if any(last) else "-"))
    return "\n".join(rows)


def flag_section(res):
    out = []
    for asset, fa in res["flags"].items():
        ids = []
        for fl in fa.values():
            for f in fl:
                if f["id"] not in ids:
                    ids.append(f["id"])
        out.append("**%s**\n\n| Variant | " % asset + " | ".join(ids) + " |\n|---|" + "---|" * len(ids))
        for vn, fl in fa.items():
            d = dict((f["id"], f) for f in fl)
            out.append("| %s | " % label(vn) + " | ".join("FIRED" if d.get(i, {}).get("fired") else ("-" if i in d else "n/a")
                                                         for i in ids) + " |")
        out.append("")
        p = res["config"]["primary"]
        for f in fa.get(p, []):
            out.append("- **%s: %s.** %s" % (f["id"], "FIRED" if f["fired"] else "not fired", f["detail"]))
        out.append("")
    return "\n".join(out)


def learn_section(res):
    L = res.get("learnability")
    if not L:
        return "_No learnability result found._"
    out = ["Same test span of synthetic series 1 traded by models trained on three data sizes (Phase 4 code, selection, "
           "refit and 'do no harm' included). Fresh synthetic series; criteria = Phase 3's frozen ones.", "",
           "| Family / size | Scenario | kappa | Test Sharpe mean | by seed | Oracle | Train | Val | Turnover/yr | Exposure | Corr. with planted | Neutral | Found the edge |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, v in L["main"].items():
        for sc, sm in v["summary"].items():
            if not sm:
                continue
            k = float(res["config"]["learnability"]["scenarios"].get(sc, 0.0))
            out.append("| %s | %s | %.3f | %.2f | %s | %.2f | %.2f | %.2f | %.0f | %.0f%% | %.2f | %.0f%% | %d of %d |" % (
                key, sc, k, sm["test_sharpe_mean"], ", ".join("%.2f" % x for x in sm["test_sharpe_by_seed"]),
                sm["oracle_sharpe_mean"], sm["train_sharpe_mean"], sm["val_sharpe_mean"], sm["turnover_mean"],
                100 * sm["exposure_mean"], sm["corr_mean"], 100 * sm["fallback_share"], sm["found_edge_seeds"], sm["n"]))
    out += ["", "| Family / size | finds planted edge | fits training slice | near flat without edge | PASS |", "|---|---|---|---|---|"]
    for key, v in L["main"].items():
        j = v["judge"]
        out.append("| %s | %s | %s | %s | **%s** |" % (key, j.get("finds_planted_edge"), j.get("fits_training_slice"),
                                                       j.get("near_flat_without_edge"), "PASS" if j["pass"] else "FAIL"))
    out += ["", "**Power check** (10 seeds, 24-month test):", "",
            "| Family / size | Scenario | Test Sharpe mean | sd over seeds | by seed | Oracle | Corr. with planted | Neutral | Found the edge |",
            "|---|---|---|---|---|---|---|---|---|"]
    for key, v in L.get("power", {}).items():
        for sc, sm in v["summary"].items():
            if not sm:
                continue
            out.append("| %s | %s | %.2f | %.2f | %s | %.2f | %.2f | %.0f%% | %d of %d |" % (
                key, sc, sm["test_sharpe_mean"], sm["test_sharpe_sd"], ", ".join("%.2f" % x for x in sm["test_sharpe_by_seed"]),
                sm["oracle_sharpe_mean"], sm["corr_mean"], 100 * sm["fallback_share"], sm["found_edge_seeds"], sm["n"]))
    return "\n".join(out)


def lookahead_section(res):
    L = res.get("lookahead")
    if not L:
        return "_No look-ahead result found._"
    out = ["| Asset | Cuts | build_one readings, data cut | basis / Coinbase, source files cut | store == code | Clean |",
           "|---|---|---|---|---|---|"]
    for a, v in L["assets"].items():
        bad1 = sorted(set(c for x in v["build_one_cut"].values() for c in x))
        bad2 = sorted(set(c for x in v["sources_cut"].values() for c in x))
        mism = dict((k, n) for k, n in v["store_vs_code"].items() if n)
        out.append("| %s | %s | %s | %s | %s | %s |" % (a, ", ".join(x[:16] for x in v["cuts"]), ", ".join(bad1) or "all equal",
                                                       (", ".join(bad2) or "all equal") if v["sources_cut"] else "n/a",
                                                       mism or "all equal", "yes" if v["clean"] else "NO"))
    for a, d in (L.get("assembled") or {}).items():
        out.append("")
        out.append("Assembled inputs on %s's bars (Phase 3 features + readings + flags), cut at %s: offending columns %s."
                   % (a, ", ".join(k[:16] for k in d), sorted(set(c for x in d.values() for c in x)) or "none"))
    return "\n".join(out)


def fold_section(res, asset="BTCUSDT"):
    p = res["config"]["primary"]
    r = res["assets"][asset]["fees"][HEAD]
    v = r["variants"][p]
    names = seed_names(v)
    bh, mo = r["bench"]["buy_hold"]["windows"], r["bench"]["momentum"]["windows"]
    tr = res["assets"][asset]["training"][p]
    rows = ["| # | Test window | Agent net, mean (min..max) | Agent Sharpe | Neutral seeds | B&H net | B&H Sharpe | Mom net | Mom Sharpe |",
            "|---|---|---|---|---|---|---|---|---|"]
    for i, w in enumerate(bh):
        nets = [v["seeds"][s]["windows"][i]["total_return"] for s in names]
        shs = [v["seeds"][s]["windows"][i]["sharpe"] for s in names]
        nn = sum(1 for s in names if tr[s][i]["fallback"])
        rows.append("| %d | %s .. %s | %s (%s .. %s) | %.2f | %d of %d | %s | %.2f | %s | %.2f |" % (
            i, w["test_start"], w["test_end"], pct(np.mean(nets)), pct(min(nets), 0), pct(max(nets), 0), np.mean(shs), nn,
            len(names), pct(w["total_return"]), w["sharpe"], pct(mo[i]["total_return"]), mo[i]["sharpe"]))
    return "\n".join(rows)


def training_section(res):
    out = []
    for vn in order(res):
        tr = res["assets"]["BTCUSDT"]["training"][vn]
        ch = [x.get("chosen") or {} for s in tr for x in tr[s]]
        hl = {}
        for c in ch:
            k = "none" if c.get("half_life_days") is None else "%g d" % c["half_life_days"]
            hl[k] = hl.get(k, 0) + 1
        al = {}
        for c in ch:
            if "alpha" in c:
                al["%g" % c["alpha"]] = al.get("%g" % c["alpha"], 0) + 1
        g = train_gap(res, "BTCUSDT", vn)
        out.append("- %s: train-slice Sharpe %.2f, validation %.2f, test %.2f (BTC, fold means); neutral in %.0f%% of fold models; "
                   "half-life chosen %s%s." % (label(vn), g["train"], g["val"], g["test"], 100 * g["fallback_share"],
                                              ", ".join("%s x%d" % kv for kv in sorted(hl.items())),
                                              ("; ridge penalty chosen " + ", ".join("%s x%d" % kv for kv in sorted(al.items())))
                                              if al else ""))
    return "\n".join(out)


def freeze_section(res):
    return "\n".join("- %s: %s" % (k, v) for k, v in (res["config"].get("freeze") or {}).items())


def design_section(cfg):
    sp, q, t4 = cfg["sp"], cfg["q"], cfg["train4"]
    return "\n".join([
        "- **Clock.** 15m bars, a decision at every 15m close, fill at the next open, minimum hold %d bars; actions %s." % (
            cfg["policy"]["min_hold_bars"], cfg["actions"]),
        "- **More data per model.** Each fold model trains on every bar from 2019 (each market's first bar + %d days of "
        "warm-up; BTC perp from Sept 2019) up to the fold, i.e. 1 year for the first fold growing to about 7 for the last, "
        "pooled across BTC and ETH (and, in one variant, all 8 engine markets with their own costs); recency half-life "
        "chosen per fold on the validation slice (last %d months) from %s days (None = no recency); then refit on everything "
        "up to the fold. Ablations keep Phase 3's 12-month single-asset window." % (
            t4["warmup_days"], t4["validation_months_expanding"], sp["half_life_days"]),
        "- **Inputs.** Phase 3's features (z-scored per asset on the fold's training rows, clipped at +-5) plus %d Mind 15 "
        "readings from the evidence store and %d availability flags (an unavailable reading is NaN -> 0 after z-scoring, with "
        "its group's flag at 0)." % (len(cfg.get("_readings", [])) or 18, 7),
        "- **SP (supervised-then-policy).** Weighted ridge on the next %d bars' vol-scaled net return, penalty from %s chosen "
        "with the half-life by the validation information coefficient; block-bootstrap seeds (1-week blocks); Phase 3's cost-"
        "aware policy on the prediction (round-trip cost band, risk charge %.1f)." % (
            sp["horizon_bars"], sp["alphas"], cfg["qagent"]["risk_aversion"]),
        "- **Q.** The Phase 3 afterstate Q-learner unchanged (linear, %d-step double Q, weight decay %.1f, round-trip cost "
        "hard-wired), up to %d x %d steps with early stopping on the validation Bellman loss (patience %d), half-life chosen "
        "by that loss; refit for the kept steps." % (cfg["qagent"]["n_step"], cfg["qagent"]["weight_decay"], q["evals"],
                                                     q["eval_every"], q["patience"]),
        "- **Do no harm.** A fold whose validation-stage model nets a Sharpe under %.1f on an asset's validation slice acts "
        "flat on that asset for the fold." % sp["fallback_val_sharpe"],
        "- **Risk manager and costs.** Agents through the Phase 3 risk manager (vol-targeted size, soft drawdown brake) into "
        "the shared backtester; 0.10% a side headline, 0.05% comparison; funding on perp positions.",
    ])


def markdown(res):
    cfg = res["config"]
    p = cfg["primary"]
    V = res["verdict"]
    lines = ["# RL Phase 4 report: more data per model", "",
             "Run `%s`, generated %s. 15-minute bars and a 15-minute decision clock throughout. Paper only: no orders, no keys. "
             "Seeds %s, run time %.1f min. BTCUSDT perpetual is the headline; ETHUSDT is reported the same way. Out of sample = "
             "25 stitched 3-month test windows, 2020-10-01 to 2026-11-11; every decision comes from a model trained only on "
             "data before its window. The strategy loop's rules A and B (and every comparison with them) are scored only up "
             "to 2025-11-11, the start of the loop's sealed holdout." % (res["run_id"], res["generated_utc"], res["seeds"],
                                                                          res["elapsed_min"]), "",
             "## Verdict", "", V["text"], ""]
    for asset in res["assets"]:
        a = V["assets"][asset]
        for span, nm in (("full", "full span 2020-10-01 .. 2026-11-11"), ("dev", "span up to 2025-11-11")):
            d = a[span]["variants"][p]
            lines.append("- %s, %s: primary Sharpe %.2f (seeds %s) vs buy-and-hold %.2f and momentum %.2f; gross Sharpe %.2f; "
                         "break-even fee %s%s." % (asset, nm, d["sharpe_mean"], ", ".join("%.2f" % x for x in d["sharpe_by_seed"]),
                                                   a[span]["bh_sharpe"], a[span]["mom_sharpe"], d["edge"]["gross_sharpe_mean"],
                                                   fee_s(d["break_even_fee"]),
                                                   ("; loop rules A %.2f, B %.2f" % (a[span]["A_sharpe"], a[span]["B_sharpe"]))
                                                   if "A_sharpe" in a[span] else ""))
    lines += ["", "## BTC headline: stitched out of sample 2020-10-01 .. 2026-11-11, 0.10% a side (the owner's rule)", "",
              table(res, "BTCUSDT", HEAD, "full", p), "",
              "## BTC: stitched out of sample 2020-10-01 .. 2026-11-11, 0.05% a side (Binance USDT-M taker)", "",
              table(res, "BTCUSDT", ALT, "full", p), "",
              "Agent rows run through the Phase 3 risk manager; benchmarks run without it (the two reference rows show what it "
              "does to buy-and-hold and momentum). Gross Sharpe = before every cost (fees, spread, slippage, funding) with the "
              "same positions. Break-even fee = the fee a side at which the stitched net return would be zero.", "",
              "## By seed (BTC, full span): Sharpe / net return / break-even fee", "", seed_table(res, "BTCUSDT"), "",
              "## BTC up to 2025-11-11 (the loop's development span): against the loop's rules A and B", "",
              "The loop chose A and B on data before 2025-11-11 and keeps 2025-11-11 .. 2026-11-11 sealed, so this table stops "
              "there (21 folds). A and B use the loop's spot backtester (long legs up to 1x pay no funding), no risk manager.", "",
              "### 0.10% a side", "", table(res, "BTCUSDT", HEAD, "dev", p), "", "### 0.05% a side", "",
              table(res, "BTCUSDT", ALT, "dev", p), ""]
    if "ETHUSDT" in res["assets"]:
        lines += ["## ETH: stitched out of sample 2020-10-01 .. 2026-11-11", "", "### 0.10% a side", "",
                  table(res, "ETHUSDT", HEAD, "full", p), "", "### 0.05% a side", "", table(res, "ETHUSDT", ALT, "full", p), "",
                  "### ETH up to 2025-11-11, 0.10%", "", table(res, "ETHUSDT", HEAD, "dev", p), "",
                  "### By seed (ETH, full span)", "", seed_table(res, "ETHUSDT"), ""]
    lines += ["## Edge before costs", "", edge_table(res), "",
              "t (approx.) = gross Sharpe x sqrt(years): about 2 is the usual bar for 'distinguishable from luck' (one test; "
              "with this many variants a higher bar is fair).", "",
              "## Does more data help? (the ablation grid, all frozen before any result)", "", ablation_table(res), "",
              "Net Sharpe at 0.10%, seed means, full span; gross = before costs. Reading: compare a row with the one that "
              "differs in one respect only (12-month window vs expanding, one asset vs pooled, Phase 3 inputs vs + readings).", "",
              "## Overfitting flags", "", flag_section(res), "",
              "## Learnability check at the new data sizes (synthetic, before the freeze)", "", learn_section(res), "",
              "## No-look-ahead check of every input (real data)", "", lookahead_section(res), "",
              "## What was frozen, and when", "", freeze_section(res),
              "- No test-window number fed back into any setting; nothing was rerun after the test results were seen.", "",
              "## Design (fixed before testing)", "", design_section(cfg), "",
              "## Per fold, primary agent, BTC, 0.10%", "", fold_section(res), "",
              "## Training", "", training_section(res), "",
              "- Memory: heavy steps started only with >= %d MB free and paused under %d MB. Pauses: %s." % (
                  cfg["memory"]["start_mb"], cfg["memory"]["floor_mb"],
                  "; ".join("%s %s (%s, waited %ss)" % (e["utc"], e["where"], e["why"], e["waited_s"])
                            for e in res.get("memory_events", [])) or "none"),
              "- Models: %s (one W file per fold, seed and asset; a JSON record per fold)." % res.get("models_dir"),
              "- Phase 3 benchmark rows: from run `%s` (same data, folds, backtester and risk manager)." % res.get("phase3_run"),
              "", "Machine-readable: `phase4_summary.json`. Nothing here is wired into the live engine or the page.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- summary json
KEYS = [("total_return", "return"), ("sharpe", "sharpe"), ("sortino", "sortino"), ("max_drawdown", "max_drawdown"),
        ("calmar", "calmar"), ("turnover_per_year", "turnover_per_year"), ("avg_holding_hours", "avg_holding_hours"),
        ("cost_drag_per_year", "cost_drag_per_year"), ("sharpe_gross", "sharpe_gross")]


def _blk(st, be=None):
    d = dict((o, float(st[k])) for k, o in KEYS if k in st)
    d["trades_per_year"] = trades_per_year(st)
    if be is not None:
        d["break_even_fee"] = be
    return d


def summary_json(res):
    assets = {}
    for asset, A in res["assets"].items():
        fees = {}
        for fee, r in A["fees"].items():
            spans = {}
            for span, rr in (("full_span", r), ("to_2025_11_11", r["dev"])):
                strat = {}
                for vn, v in rr["variants"].items():
                    strat[vn] = {"label": label(vn), "seed_mean": dict(row_stats(v)),
                                 "seeds": dict((s, _blk(v["seeds"][s]["stitched"], v["seeds"][s].get("break_even_fee")))
                                               for s in seed_names(v)),
                                 "folds_seed_mean": [{"fold": i, "sharpe": float(np.mean([v["seeds"][s]["windows"][i]["sharpe"]
                                                                                           for s in seed_names(v)])),
                                                      "return": float(np.mean([v["seeds"][s]["windows"][i]["total_return"]
                                                                               for s in seed_names(v)]))}
                                                     for i in range(len(v["seeds"][seed_names(v)[0]]["windows"]))]}
                for nm, v in (rr.get("phase3") or {}).items():
                    strat[nm] = {"label": label(nm), "seed_mean": dict(row_stats(v))}
                bench = {}
                for k, ev in rr["bench"].items():
                    if k == "random":
                        bench[k] = dict((kk, vv["mean"]) for kk, vv in ev["stitched"].items())
                    else:
                        bench[k] = _blk(ev["stitched"], ev.get("break_even_fee"))
                spans[span] = {"strategies": strat, "benchmarks": bench}
            fees[fee] = spans
        assets[asset] = {"fees": fees}
    return {"phase": 4, "paper_only": True, "run_id": res["run_id"], "generated_utc": res["generated_utc"],
            "headline_fee": HEAD, "primary": res["config"]["primary"], "seeds": res["seeds"],
            "out_of_sample": "2020-10-01 .. 2026-11-11 (25 folds); loop rules A/B and comparisons with them to 2025-11-11 only",
            "verdict": {"text": res["verdict"]["text"], "edge_before_costs": res["verdict"]["edge_before_costs"],
                        "beats_both": res["verdict"]["beats_both"]},
            "assets": assets,
            "flags": dict((a, dict((v, [{"id": f["id"], "fired": f["fired"], "detail": f["detail"]} for f in fl])
                                   for v, fl in fa.items())) for a, fa in res["flags"].items()),
            "learnability": dict((k, v["judge"]) for k, v in (res.get("learnability") or {}).get("main", {}).items()),
            "lookahead_clean": (res.get("lookahead") or {}).get("clean"),
            "freeze": res["config"].get("freeze"), "elapsed_min": res["elapsed_min"],
            "memory_events": res.get("memory_events", [])}
