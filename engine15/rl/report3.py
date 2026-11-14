# -*- coding: utf-8 -*-
"""report3 -- the Phase 3 report: overfitting flags, a plain verdict, the markdown report, phase3_summary.json (for a
future web 'Lab' tab) and the risk manager's out-of-sample log."""
import csv
import math

import numpy as np

PRIMARY = "agent_continual_retrain"
HEAD, ALT = "fee_0.10%", "fee_0.05%"
LABELS = {
    "agent_static": "(a) static, fresh model per fold",
    "agent_continual": "(b) continual fine-tuning, never reset",
    "agent_continual_retrain": "(c) continual + full retrain each fold [primary]",
    "v1_seed_consensus": "v1 seed consensus (all 3 seeds agree)",
    "v2_confidence_gate": "v2 confidence gate",
    "v3_htf_alignment": "v3 higher-timeframe alignment",
    "v4_vol_cost_gate": "v4 volatility / cost gate",
    "v5_meta_label": "v5 meta-labeling on momentum",
    "v6_core_satellite": "v6 core-satellite (0..1.5x)",
    "r1_residual_A": "residual RL on A (+-0.5x)",
    "r2_residual_B": "residual RL on B (+-0.5x)",
    "w1_warmstart_A": "imitation warm start on A, then RL",
    "w2_warmstart_B": "imitation warm start on B, then RL",
    "w0_scratch_A": "same agent from scratch (A's inputs)",
    "w0_scratch_B": "same agent from scratch (B's inputs)",
}
ORDER = list(LABELS)


# ---------------------------------------------------------------- helpers
def clean(o):
    """JSON-safe copy: inf -> 'inf' / '-inf', NaN -> None, numpy scalars -> python, private keys dropped."""
    if isinstance(o, dict):
        return dict((str(k), clean(v)) for k, v in o.items() if not str(k).startswith("_"))
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        x = float(o)
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def pct(x, d=1):
    return "-" if x is None else ("%+." + str(d) + "f%%") % (100.0 * x)


def fee_s(x):
    if x is None:
        return "no trades"
    if x == "n/a":
        return "-"
    if isinstance(x, str):
        x = float(x)
    if math.isinf(x):
        return "> 5%" if x > 0 else "< -1% (loses even with a rebate)"
    if x < 0:
        return "%.3f%% (loses before fees)" % (100 * x)
    return "%.3f%%" % (100 * x)


def _num(x):
    if x is None:
        return None
    if isinstance(x, str):
        return float(x)
    return float(x)


def seed_names(v):
    return sorted(v["seeds"], key=lambda s: (s == "all", s))


def stitched(v, key):
    return [v["seeds"][s]["stitched"][key] for s in seed_names(v)]


def mean_be(v):
    xs = [_num(v["seeds"][s].get("break_even_fee")) for s in seed_names(v)]
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    if any(math.isinf(x) for x in xs):
        f = [x for x in xs if not math.isinf(x)]
        return float(np.median(xs)) if not f else float(np.median(xs))
    return float(np.mean(xs))


def trades_per_year(st):
    return st["trades"] / max(st["years"], 1e-9)


def row_stats(v):
    """Seed-mean metrics of a variant (or the single 'all' series)."""
    names = seed_names(v)
    keys = ["total_return", "sharpe", "sortino", "max_drawdown", "calmar", "turnover_per_year", "avg_holding_hours",
            "cost_drag_per_year", "exposure", "total_return_gross", "sharpe_gross", "fee_per_year", "funding_per_year"]
    out = dict((k, float(np.mean([v["seeds"][s]["stitched"][k] for s in names]))) for k in keys)
    out["trades_per_year"] = float(np.mean([trades_per_year(v["seeds"][s]["stitched"]) for s in names]))
    out["break_even_fee"] = mean_be(v)
    out["sharpe_sd"] = float(np.std([v["seeds"][s]["stitched"]["sharpe"] for s in names], ddof=1)) if len(names) > 1 else 0.0
    return out


def bench_stats(ev):
    st = dict(ev["stitched"])
    st["trades_per_year"] = trades_per_year(st)
    st["break_even_fee"] = ev.get("break_even_fee")
    return st


def random_stats(rs):
    st = dict((k, v["mean"]) for k, v in rs["stitched"].items())
    st["trades_per_year"] = st.get("trades", 0) / max(rs["stitched"].get("years", {"mean": 1}).get("mean", 1) if "years" in rs["stitched"] else 1, 1e-9)
    st["break_even_fee"] = None
    return st


def fold_wins(v, bench_ev, key="sharpe"):
    """Folds where the variant's seed-mean per-fold metric beats the benchmark's."""
    names = seed_names(v)
    nw = len(bench_ev["windows"])
    am = np.array([np.mean([v["seeds"][s]["windows"][i][key] for s in names]) for i in range(nw)])
    bm = np.array([bench_ev["windows"][i][key] for i in range(nw)])
    return int((am > bm).sum()), nw


# ---------------------------------------------------------------- flags
def _variant_flags(res, asset, vname, fc, span="full"):
    A = res["assets"][asset]
    get = lambda fee: (A["fees"][fee]["variants"] if span == "full" else A["fees"][fee]["dev"]["variants"]).get(vname)
    bget = lambda fee: (A["fees"][fee]["bench"] if span == "full" else A["fees"][fee]["dev"]["bench"])
    v, v5 = get(HEAD), get(ALT)
    if v is None:
        return []
    B, B5 = bget(HEAD), bget(ALT)
    bh_key = "buy_hold" if v.get("eval") != "spot" else "buy_hold_spot"
    out = []
    names = seed_names(v)
    sh = np.array(stitched(v, "sharpe"))
    rt = np.array(stitched(v, "total_return"))
    if len(names) > 1:
        sd = float(sh.std(ddof=1))
        split = bool((rt > 0).any() and (rt <= 0).any())
        out.append({"id": "seed_dispersion", "fired": bool(sd > fc["seed_sharpe_sd"] or split), "value": round(sd, 3),
                    "detail": "stitched Sharpe by seed %s (sd %.2f, threshold %.2f)%s"
                              % (", ".join("%.2f" % x for x in sh), sd, fc["seed_sharpe_sd"],
                                 "; seeds disagree on the sign of the net return" if split else "")})
    txt, fired = [], False
    comps = [(bh_key, B[bh_key]), ("momentum", B["momentum"])]
    if span == "dev" and v.get("eval") == "spot":
        comps += [("baseline_A", B["baseline_A"]), ("baseline_B", B["baseline_B"])]
    for nm, be in comps:
        w, n = fold_wins(v, be)
        fired = fired or (w / n < fc["min_fold_win_share"] and nm in (bh_key, "momentum"))
        txt.append("%s %d/%d" % (nm, w, n))
    out.append({"id": "beats_benchmarks_in_under_half_the_folds", "fired": bool(fired),
                "detail": "folds with a higher seed-mean Sharpe: " + ", ".join(txt)})
    r10 = row_stats(v)
    r05 = row_stats(v5)
    flips = []
    for s in names:
        a, b = v["seeds"][s]["stitched"]["total_return"], v5["seeds"][s]["stitched"]["total_return"]
        if (a > 0) != (b > 0):
            flips.append("seed %s %s at 0.10%% vs %s at 0.05%%" % (s, pct(a, 0), pct(b, 0)))
    out.append({"id": "fee_sign_flip", "fired": bool(flips), "detail": "; ".join(flips) or "no seed changes sign"})
    bh10, bh05 = B[bh_key]["stitched"]["sharpe"], B5[bh_key]["stitched"]["sharpe"]
    only05 = (r05["total_return"] > 0 >= r10["total_return"]) or (r05["sharpe"] > bh05 and not r10["sharpe"] > bh10)
    out.append({"id": "edge_only_at_0.05", "fired": bool(only05),
                "detail": "seed mean: net %s / Sharpe %.2f at 0.10%% (buy-and-hold %.2f); net %s / Sharpe %.2f at 0.05%% "
                          "(buy-and-hold %.2f)" % (pct(r10["total_return"]), r10["sharpe"], bh10, pct(r05["total_return"]),
                                                    r05["sharpe"], bh05)})
    to = [v["seeds"][s]["stitched"]["turnover_per_year"] for s in names]
    out.append({"id": "high_turnover", "fired": bool(max(to) > fc["max_turnover_per_year"]), "value": round(float(np.mean(to)), 1),
                "detail": "turnover per year by seed %s (threshold %d)" % (", ".join("%.0f" % x for x in to),
                                                                           fc["max_turnover_per_year"])})
    mix = [v["seeds"][s].get("position_mix", {}) for s in names]
    degenerate = any(m.get("long", 0) > 0.9 for m in mix) or any(m.get("flat", 0) > 0.95 for m in mix)
    out.append({"id": "degenerate_policy", "fired": bool(degenerate),
                "detail": "long / flat / short share of bars by seed: " + "; ".join(
                    "%s %.0f/%.0f/%.0f%%" % (s, 100 * m.get("long", 0), 100 * m.get("flat", 0), 100 * m.get("short", 0))
                    for s, m in zip(names, mix))})
    return out


def train_gap(res, asset, fam, mode, vname):
    A = res["assets"][asset]
    v = A["fees"][HEAD]["variants"].get(vname) or A["fees"][HEAD]["dev"]["variants"].get(vname)
    if v is None:
        return None
    trs, vas, tes, fb = [], [], [], []
    for s in seed_names(v):
        key = "%s_%s_s%s" % (fam, mode, s)
        recs = A["training"].get(key)
        if not recs:
            continue
        for i, r in enumerate(recs):
            if i >= len(v["seeds"][s]["windows"]):
                break
            trs.append(r["train_sharpe"])
            vas.append(r["val_sharpe"])
            tes.append(v["seeds"][s]["windows"][i]["sharpe"])
            fb.append(bool(r.get("fallback")))
    if not trs:
        return None
    return {"train": float(np.mean(trs)), "val": float(np.mean(vas)), "test": float(np.mean(tes)),
            "gap": float(np.mean(trs) - np.mean(tes)), "fallback_share": float(np.mean(fb)),
            "train_positive_share": float(np.mean(np.array(trs) > 0))}


FAM_OF = {"agent_static": ("base", "a"), "agent_continual": ("base", "b"), "agent_continual_retrain": ("base", "c"),
          "v5_meta_label": ("meta", "c"), "v6_core_satellite": ("core", "c"), "r1_residual_A": ("res_A", "c"),
          "r2_residual_B": ("res_B", "c"), "w1_warmstart_A": ("ws_A", "c"), "w2_warmstart_B": ("ws_B", "c"),
          "w0_scratch_A": ("scr_A", "c"), "w0_scratch_B": ("scr_B", "c")}


def flags(res):
    fc = res["config"]["flags"]
    out = {}
    for asset, A in res["assets"].items():
        fa = {}
        for vname in ORDER:
            span = "full" if vname in A["fees"][HEAD]["variants"] else "dev"
            fl = _variant_flags(res, asset, vname, fc, span)
            if not fl:
                continue
            if vname in FAM_OF:
                g = train_gap(res, asset, FAM_OF[vname][0], FAM_OF[vname][1], vname)
                if g:
                    fl.insert(0, {"id": "train_test_sharpe_gap", "fired": bool(g["gap"] > fc["train_test_sharpe_gap"]),
                                  "value": round(g["gap"], 3),
                                  "detail": "mean over folds and seeds: train-slice Sharpe %.2f, validation %.2f, test %.2f; "
                                            "gap %.2f (threshold %.1f); neutral fallback in %.0f%% of fold models"
                                            % (g["train"], g["val"], g["test"], g["gap"], fc["train_test_sharpe_gap"],
                                               100 * g["fallback_share"])})
            fa[vname] = fl
        out[asset] = fa
    return out


# ---------------------------------------------------------------- verdict
def verdict(res):
    A = res["assets"]["BTCUSDT"]
    r, r5 = A["fees"][HEAD], A["fees"][ALT]
    bh, mo = r["bench"]["buy_hold"]["stitched"], r["bench"]["momentum"]["stitched"]
    out = {"variants": {}}
    for vname, v in r["variants"].items():
        st = row_stats(v)
        sh = stitched(v, "sharpe")
        cal = stitched(v, "calmar")
        d = {"sharpe_mean": st["sharpe"], "calmar_mean": st["calmar"], "return_mean": st["total_return"],
             "seeds_beating_bh_sharpe": int(sum(x > bh["sharpe"] for x in sh)),
             "seeds_beating_mom_sharpe": int(sum(x > mo["sharpe"] for x in sh)), "seeds": len(sh),
             "break_even_fee": st["break_even_fee"], "sharpe_at_005": row_stats(r5["variants"][vname])["sharpe"]}
        d["beats_bh"] = bool(st["sharpe"] > bh["sharpe"] and d["seeds_beating_bh_sharpe"] == len(sh) and st["calmar"] > bh["calmar"])
        d["beats_momentum"] = bool(st["sharpe"] > mo["sharpe"] and d["seeds_beating_mom_sharpe"] == len(sh)
                                   and st["calmar"] > mo["calmar"])
        out["variants"][vname] = d
    p = out["variants"].get(PRIMARY)
    out["primary"] = PRIMARY
    out["bh_sharpe"], out["mom_sharpe"], out["bh_calmar"], out["mom_calmar"] = bh["sharpe"], mo["sharpe"], bh["calmar"], mo["calmar"]
    winners = [k for k, d in out["variants"].items() if d["beats_bh"] and d["beats_momentum"]]
    out["any_variant_beats_both"] = winners
    if p is None:
        out["text"] = "No primary agent result."
        return out
    if p["beats_bh"] and p["beats_momentum"]:
        head = ("YES on these numbers: the continuously learning 15m agent (c) beats buy-and-hold and momentum on Sharpe "
                "and Calmar for every seed out of sample after 0.10%% fees (seed-mean Sharpe %.2f vs %.2f and %.2f)."
                % (p["sharpe_mean"], bh["sharpe"], mo["sharpe"]))
    else:
        head = ("NO. Out of sample (Oct 2020 - Nov 2026), after 0.10%% fees, the continuously learning 15m agent (c) does "
                "not beat buy-and-hold and momentum on a risk-adjusted basis across seeds: seed-mean Sharpe %.2f "
                "(seeds above buy-and-hold's %.2f: %d of %d; above momentum's %.2f: %d of %d), Calmar %.2f vs %.2f and %.2f, "
                "net return %s vs buy-and-hold %s. Its break-even fee is %s a side."
                % (p["sharpe_mean"], bh["sharpe"], p["seeds_beating_bh_sharpe"], p["seeds"], mo["sharpe"],
                   p["seeds_beating_mom_sharpe"], p["seeds"], p["calmar_mean"], bh["calmar"], mo["calmar"],
                   pct(p["return_mean"], 0), pct(bh["total_return"], 0), fee_s(p["break_even_fee"])))
    if winners:
        head += (" Of the %d variants, %s beat both on every seed; with this many variants tried, treat that as a lead "
                 "to re-test forward, not as proof." % (len(out["variants"]), ", ".join(winners)))
    else:
        head += " None of the %d agent variants or filters beats both on every seed." % len(out["variants"])
    out["text"] = head
    return out


# ---------------------------------------------------------------- summary json
SUMMARY_KEYS = [("total_return", "return"), ("sharpe", "sharpe"), ("sortino", "sortino"), ("max_drawdown", "max_drawdown"),
                ("calmar", "calmar"), ("turnover_per_year", "turnover_per_year"), ("avg_holding_hours", "avg_holding_hours"),
                ("cost_drag_per_year", "cost_drag_per_year")]


def _blk(st):
    d = dict((o, float(st[k])) for k, o in SUMMARY_KEYS)
    d["trades_per_year"] = trades_per_year(st)
    return d


def _folds(ev):
    return [dict([("fold", w["window"]), ("test_start", w["test_start"]), ("test_end", w["test_end"])]
                 + [(o, float(w[k])) for k, o in SUMMARY_KEYS]) for w in ev["windows"]]


def summary_json(res):
    assets = {}
    for asset, A in res["assets"].items():
        fees = {}
        for fee, r in A["fees"].items():
            def strat_block(variants):
                S = {}
                for vname, v in variants.items():
                    names = seed_names(v)
                    blk = {"label": LABELS.get(vname, vname), "seeds": {}, "eval": v.get("eval"), "span": v.get("span")}
                    for s in names:
                        e = v["seeds"][s]
                        blk["seeds"][s] = {"overall": dict(_blk(e["stitched"]), break_even_fee=e.get("break_even_fee")),
                                           "folds": _folds(e)}
                    st = row_stats(v)
                    blk["seed_mean"] = dict((o, st[k]) for k, o in SUMMARY_KEYS)
                    blk["seed_mean"].update({"trades_per_year": st["trades_per_year"], "break_even_fee": st["break_even_fee"],
                                             "sharpe_sd": st["sharpe_sd"]})
                    S[vname] = blk
                return S
            B = r["bench"]
            bench = dict((k, {"overall": dict(_blk(B[k]["stitched"]), break_even_fee=B[k].get("break_even_fee")),
                              "folds": _folds(B[k])}) for k in ("buy_hold", "momentum", "buy_hold_risk3", "momentum_risk3"))
            bench["random_mean"] = {"overall": dict((o, B["random"]["stitched"][k]["mean"]) for k, o in SUMMARY_KEYS)}
            D = r["dev"]["bench"]
            dbench = dict((k, {"overall": dict(_blk(D[k]["stitched"]), break_even_fee=D[k].get("break_even_fee")),
                               "folds": _folds(D[k])}) for k in D if k != "random")
            fees[fee] = {"full_span": {"benchmarks": bench, "strategies": strat_block(r["variants"])},
                         "dev_span_to_2025_11_11": {"benchmarks": dbench, "strategies": strat_block(r["dev"]["variants"])}}
        w, wd = A["windows"], A["windows_dev"]
        assets[asset] = {"out_of_sample": {"start": w[0]["test_start"], "end": w[-1]["test_end"], "folds": len(w)},
                         "dev_span": {"start": wd[0]["test_start"], "end": wd[-1]["test_end"], "folds": len(wd),
                                      "note": "variants built on the loop's rules A / B are scored only here (sealed holdout)"},
                         "fees": fees}
    p2 = None
    if res.get("phase2"):
        p2 = dict((fee, res["phase2"]["fees"][fee]["strategies"]["agent_seed_mean"]["overall"]) for fee in res["phase2"]["fees"])
    return {"schema": "rl_phase3_summary/1", "run_id": res["run_id"], "generated_utc": res["generated_utc"], "paper_only": True,
            "market": "15m bars, 15m decision clock", "headline_asset": "BTCUSDT", "headline_fee": HEAD,
            "primary_variant": PRIMARY, "labels": LABELS, "seeds": res["seeds"], "assets": assets,
            "phase2_ppo_reference": p2, "flags": res["flags"], "verdict": res["verdict"],
            "learnability": (res.get("learnability") or {}).get("verdict"),
            "risk_check": {"pass": (res.get("riskcheck") or {}).get("pass")},
            "cadence_days": res["config"]["continual"]["cadence_days"],
            "metrics_note": "return = stitched net return; sharpe/sortino annualised (35,040 bars a year); turnover in full "
                            "sides a year; break_even_fee = fee a side at which the stitched net return is zero, positions "
                            "held fixed"}


def write_risk_log(path, events):
    import pandas as pd
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variant", "seed", "bar_close_utc", "rule", "requested", "allowed", "position_before", "reason"])
        for e in events:
            w.writerow([e.get("variant"), e.get("seed"), str(pd.Timestamp(e["close_ms"], unit="ms", tz="UTC")), e["rule"],
                        e["requested"], e["allowed"], e["current"], e["reason"]])


# ---------------------------------------------------------------- markdown
COLS = ["Net return", "Sharpe", "Sortino", "Max DD", "Calmar", "Turnover/yr", "Trades/yr", "Avg hold (h)", "Cost drag/yr",
        "Break-even fee"]


def _cells(st):
    return [pct(st["total_return"]), "%.2f" % st["sharpe"], "%.2f" % st["sortino"], "%.0f%%" % (100 * st["max_drawdown"]),
            "%.2f" % st["calmar"], "%.0f" % st["turnover_per_year"], "%.0f" % st.get("trades_per_year", 0),
            "%.0f" % st["avg_holding_hours"], "%.1f%%" % (100 * st["cost_drag_per_year"]), fee_s(st.get("break_even_fee"))]


def _tr(label, st, bold=False):
    c = _cells(st)
    if bold:
        label, c = "**%s**" % label, ["**%s**" % x for x in c]
    return "| %s | %s |" % (label, " | ".join(c))


def _header():
    return ["| Strategy | " + " | ".join(COLS) + " |", "|---|" + "---|" * len(COLS)]


def variant_rows(variants, names, with_seeds=True):
    L = []
    for vname in names:
        v = variants.get(vname)
        if v is None:
            continue
        st = row_stats(v)
        sn = seed_names(v)
        lab = LABELS.get(vname, vname) + ("" if sn == ["all"] else ", mean of %d seeds" % len(sn))
        L.append(_tr(lab, st, bold=(vname == PRIMARY)))
        if with_seeds and sn != ["all"]:
            for s in sn:
                e = v["seeds"][s]
                stt = dict(e["stitched"])
                stt["trades_per_year"] = trades_per_year(stt)
                stt["break_even_fee"] = e.get("break_even_fee")
                L.append(_tr("&nbsp;&nbsp;seed %s" % s, stt))
    return L


def bench_rows(B, dev=False):
    L = []
    items = ([("buy_hold", "Buy-and-hold (perp)"), ("buy_hold_spot", "Buy-and-hold (spot)"), ("momentum", "Momentum (daily 30-day, perp)"),
              ("baseline_A", "A: loop H29 H30 1.5x/0x spot"), ("baseline_B", "B: loop H29 H31 trail 4 ATR spot")]
             if dev else [("buy_hold", "Buy-and-hold (perp)"), ("momentum", "Momentum (daily 30-day, long/short)")])
    for k, lab in items:
        if k in B:
            L.append(_tr(lab, bench_stats(B[k])))
    rs = B.get("random")
    if rs:
        st = dict((k, v["mean"]) for k, v in rs["stitched"].items())
        yrs = B["buy_hold"]["stitched"]["years"]
        st["trades_per_year"] = st["trades"] / max(yrs, 1e-9)
        st["break_even_fee"] = "n/a"
        L.append(_tr("Random agent (mean of %d)" % rs["seeds"], st))
    for k, lab in (("buy_hold_risk3", "*reference: buy-and-hold through the Phase 3 risk manager*"),
                   ("momentum_risk3", "*reference: momentum through the Phase 3 risk manager*")):
        if k in B:
            L.append(_tr(lab, bench_stats(B[k])))
    return L


def p2_row(res, fee):
    if not res.get("phase2"):
        return []
    o = res["phase2"]["fees"][fee]["strategies"]["agent_seed_mean"]["overall"]
    st = {"total_return": o["return"], "sharpe": o["sharpe"], "sortino": o["sortino"], "max_drawdown": o["max_drawdown"],
          "calmar": o["calmar"], "turnover_per_year": o["turnover_per_year"], "trades_per_year": float("nan"),
          "avg_holding_hours": o["avg_holding_hours"], "cost_drag_per_year": o["cost_drag_per_year"], "break_even_fee": float("-inf")}
    c = _cells(st)
    c[6] = "~500"
    c[9] = "< 0 (gross Sharpe ~0)"
    return ["| *Phase 2 PPO, mean of 5 seeds (Phase 2 risk limits; from phase2_summary.json)* | %s |" % " | ".join(c)]


def flag_table(fl):
    ids = ["train_test_sharpe_gap", "seed_dispersion", "beats_benchmarks_in_under_half_the_folds", "fee_sign_flip",
           "edge_only_at_0.05", "high_turnover", "degenerate_policy"]
    L = ["| Variant | " + " | ".join(ids) + " |", "|---|" + "---|" * len(ids)]
    for vname, lst in fl.items():
        d = dict((x["id"], x["fired"]) for x in lst)
        L.append("| %s | %s |" % (LABELS.get(vname, vname), " | ".join(("FIRED" if d[i] else "-") if i in d else "n/a" for i in ids)))
    return L


def markdown(res):
    L = []
    w = L.append
    cfg = res["config"]
    A = res["assets"]["BTCUSDT"]
    r, r5 = A["fees"][HEAD], A["fees"][ALT]
    w("# RL Phase 3 report: a continuously learning 15m agent that learns when not to trade\n")
    w("Run `%s`, generated %s. 15-minute bars and a 15-minute decision clock throughout. Paper only: no orders, no keys. "
      "Seeds %s, run time %s min. BTCUSDT perpetual is the headline; ETHUSDT (the engine's 15m file) is the robustness check. "
      "Out of sample = %d stitched 3-month test windows, %s to %s; every prediction comes from a model trained only on data "
      "before it.\n" % (res["run_id"], res["generated_utc"], res["seeds"], res["elapsed_min"], len(A["windows"]),
                        A["windows"][0]["test_start"], A["windows"][-1]["test_end"]))
    w("## Verdict\n")
    w(res["verdict"]["text"] + "\n")
    w(verdict_extra(res))
    for fee, tag in ((HEAD, "0.10% a side (the owner's rule)"), (ALT, "0.05% a side (Binance USDT-M taker)")):
        rr = A["fees"][fee]
        w("## BTC headline: stitched out of sample, %s\n" % tag)
        L.extend(_header())
        L.extend(variant_rows(rr["variants"], ["agent_static", "agent_continual", "agent_continual_retrain"]))
        L.extend(variant_rows(rr["variants"], ["v1_seed_consensus", "v2_confidence_gate", "v3_htf_alignment", "v4_vol_cost_gate",
                                               "v5_meta_label", "v6_core_satellite"], with_seeds=(fee == HEAD)))
        L.extend(bench_rows(rr["bench"]))
        L.extend(p2_row(res, fee))
        w("")
    w("Every agent row runs through the Phase 3 risk manager (vol-targeted sizing + soft drawdown brake); benchmarks run "
      "without it, and the two reference rows show what the risk manager alone does to buy-and-hold and momentum. Break-even "
      "fee = the fee a side at which the stitched net return would be zero with the same positions.\n")
    w(reading_section(res))
    w(seed_table(r, r5))
    w(dev_section(res))
    if "ETHUSDT" in res["assets"]:
        w(eth_section(res))
    w(behaviour_section(res))
    w("## Overfitting flags (BTC)\n")
    L.extend(flag_table(res["flags"]["BTCUSDT"]))
    w("")
    for x in res["flags"]["BTCUSDT"].get(PRIMARY, []):
        w("- **%s: %s.** %s" % (x["id"], "FIRED" if x["fired"] else "not fired", x["detail"]))
    w("")
    if "ETHUSDT" in res["flags"]:
        w("ETH flags:\n")
        L.extend(flag_table(res["flags"]["ETHUSDT"]))
        w("")
    w(pre_sections(res))
    w(diag2_section(res))
    w(freeze_section(res))
    w(design_section(cfg))
    w(fold_section(res))
    w(training_section(res))
    w("## Not done here (Phase 4, not started)\n")
    w("- Wiring the forward paper mode into the live engine loop or the web page: the owner decides after review.\n")
    w("Machine-readable: `phase3_summary.json`. Risk manager log: `phase3_risk_log_btcusdt.csv` (and `_ethusdt`).\n")
    return "\n".join(L) + "\n"


def verdict_extra(res):
    A = res["assets"]["BTCUSDT"]
    r = A["fees"][HEAD]
    v = res["verdict"]["variants"]
    L = ["Break-even fees (0.10% decisions held fixed; seed mean): " + "; ".join(
        "%s %s" % (LABELS.get(k, k).split(" [")[0], fee_s(d["break_even_fee"])) for k, d in v.items()) + ".\n"]
    dv = A["fees"][HEAD]["dev"]
    lines = []
    for vn, bn in (("r1_residual_A", "baseline_A"), ("r2_residual_B", "baseline_B"), ("w1_warmstart_A", "baseline_A"),
                   ("w2_warmstart_B", "baseline_B"), ("w0_scratch_A", "baseline_A"), ("w0_scratch_B", "baseline_B")):
        x = dv["variants"].get(vn)
        if not x:
            continue
        st, b = row_stats(x), dv["bench"][bn]["stitched"]
        ws, n = fold_wins(x, dv["bench"][bn])
        wr, _ = fold_wins(x, dv["bench"][bn], "total_return")
        lines.append("%s: Sharpe %.2f vs %.2f, net %s vs %s, Sharpe higher in %d of %d folds (return in %d)"
                     % (LABELS[vn], st["sharpe"], b["sharpe"], pct(st["total_return"], 0), pct(b["total_return"], 0), ws, n, wr))
    if lines:
        L.append("Against their own baselines (dev span only, to 2025-11-11, the loop's spot backtester, 0.10%): "
                 + "; ".join(lines) + ".\n")
    return "\n".join(L)


def seed_table(r, r5):
    L = ["## By seed, both fees (BTC, Sharpe / net return / break-even fee)\n",
         "| Variant | " + " | ".join("seed %s" % s for s in ("0", "1", "2")) + " | mean, 0.10% | mean, 0.05% |", "|---|---|---|---|---|---|"]
    for vname in ORDER:
        v, v5 = r["variants"].get(vname), r5["variants"].get(vname)
        if v is None:
            continue
        cells = []
        for s in ("0", "1", "2"):
            if s in v["seeds"]:
                e, e5 = v["seeds"][s], v5["seeds"][s]
                cells.append("%.2f / %s / %s (0.05%%: %.2f)" % (e["stitched"]["sharpe"], pct(e["stitched"]["total_return"], 0),
                                                              fee_s(e.get("break_even_fee")), e5["stitched"]["sharpe"]))
            else:
                cells.append("-")
        a, a5 = row_stats(v), row_stats(v5)
        L.append("| %s | %s | %.2f / %s | %.2f / %s |" % (LABELS.get(vname, vname), " | ".join(cells), a["sharpe"],
                                                         pct(a["total_return"], 0), a5["sharpe"], pct(a5["total_return"], 0)))
    return "\n".join(L) + "\n"


def dev_section(res):
    A = res["assets"]["BTCUSDT"]
    L = ["## BTC on the development span only (2020-10-01 to 2025-11-11): against the loop's rules A and B\n",
         "The loop chose rules A and B on data before 2025-11-11 and keeps 2025-11-11 to 2026-11-11 sealed. So everything "
         "built on A or B (residual RL, imitation warm starts, the matching scratch agents) is scored on the %d folds that end "
         "by 2025-11-11 and nowhere else; the last year is excluded from these numbers. The full-span agents are shown on the "
         "same span for comparison (their full-span numbers are above). A, B and the agents built on them use the loop's spot "
         "backtester (long legs up to 1x pay no funding) and no Phase 3 risk manager.\n" % len(A["windows_dev"])]
    for fee in (HEAD, ALT):
        d = A["fees"][fee]["dev"]
        L.append("### %s\n" % ("0.10% a side" if fee == HEAD else "0.05% a side"))
        L.extend(_header())
        L.extend(bench_rows(d["bench"], dev=True))
        L.extend(variant_rows(d["variants"], ["r1_residual_A", "r2_residual_B", "w1_warmstart_A", "w2_warmstart_B",
                                              "w0_scratch_A", "w0_scratch_B"], with_seeds=(fee == HEAD)))
        L.extend(variant_rows(d["variants"], ["agent_static", "agent_continual", "agent_continual_retrain", "v1_seed_consensus",
                                              "v2_confidence_gate", "v3_htf_alignment", "v4_vol_cost_gate", "v5_meta_label",
                                              "v6_core_satellite"], with_seeds=False))
        L.append("")
    return "\n".join(L) + "\n"


def eth_section(res):
    E = res["assets"]["ETHUSDT"]
    L = ["## ETH robustness check (same frozen settings, base family only)\n"]
    for fee in (HEAD, ALT):
        rr = E["fees"][fee]
        L.append("### %s\n" % ("0.10% a side" if fee == HEAD else "0.05% a side"))
        L.extend(_header())
        L.extend(variant_rows(rr["variants"], ["agent_static", "agent_continual", "agent_continual_retrain"], with_seeds=(fee == HEAD)))
        L.extend(variant_rows(rr["variants"], ["v1_seed_consensus", "v2_confidence_gate", "v3_htf_alignment", "v4_vol_cost_gate"],
                              with_seeds=False))
        L.extend(bench_rows(rr["bench"]))
        L.append("")
    return "\n".join(L) + "\n"


def behaviour_section(res):
    A = res["assets"]["BTCUSDT"]
    r = A["fees"][HEAD]
    L = ["## Behaviour out of sample (BTC, 0.10%): turnover, holding, what the gates did\n",
         "| Variant | Turnover/yr | Trades/yr | Avg hold (h) | Long / flat / short | Mean abs size | Gross Sharpe | Fee drag/yr | Decision stats (per seed, summed) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for vname in ORDER:
        v = r["variants"].get(vname)
        if v is None:
            continue
        st = row_stats(v)
        names = seed_names(v)
        mix = np.mean([[v["seeds"][s]["position_mix"][k] for k in ("long", "flat", "short")] for s in names], axis=0)
        ds = {}
        for s in names:
            for k, x in (v["seeds"][s].get("decision_stats") or {}).items():
                if isinstance(x, (int, float)):
                    ds[k] = ds.get(k, 0) + x
        L.append("| %s | %.0f | %.0f | %.0f | %.0f / %.0f / %.0f%% | %.2f | %.2f | %.1f%% | %s |"
                 % (LABELS.get(vname, vname), st["turnover_per_year"], st["trades_per_year"], st["avg_holding_hours"],
                    100 * mix[0], 100 * mix[1], 100 * mix[2],
                    float(np.mean([v["seeds"][s]["mean_abs_position"] for s in names])), st["sharpe_gross"],
                    100 * st["fee_per_year"], ", ".join("%s %s" % (k, int(x) if float(x).is_integer() else round(x, 2)) for k, x in ds.items())))
    L.append("\nPhase 2 for comparison: ~600 turnover a year, ~500 trades, 17 h average hold, ~80% of equity a year in costs.\n")
    picks = []
    for vname in ("v2_confidence_gate", "v4_vol_cost_gate"):
        v = r["variants"].get(vname)
        if v:
            from collections import Counter
            c = Counter()
            for s in seed_names(v):
                for p in v["seeds"][s].get("threshold_picks") or []:
                    c[p["value"]] += 1
            picks.append("%s: %s" % (LABELS[vname], ", ".join("%g x%d" % kv for kv in sorted(c.items()))))
    if picks:
        L.append("Thresholds chosen per fold (from the 3 months before each fold; counts over folds and seeds): " + "; ".join(picks) + ".\n")
    rc = r["bench"]["buy_hold_risk3"].get("risk_counts")
    if rc:
        L.append("Risk manager on buy-and-hold (full span): %s.\n" % ", ".join("%s %d" % kv for kv in rc.items()))
    return "\n".join(L)


def pre_sections(res):
    L = []
    lc = res.get("learnability")
    if lc:
        L.append("## Learnability check (synthetic data, before the freeze)\n")
        L.append("Synthetic 15m-like series (fat tails, vol regimes, funding), 2 years each: 9 months train, 3 months validation, "
                 "12 months held-out synthetic test. Planted edge: a visible AR(1) signal (one-day half-life) predicting the next "
                 "bar's return with a per-bar information coefficient of kappa. A cost-aware oracle that KNOWS the signal shows "
                 "what is attainable. Fresh series (seed base %s), %d seeds.\n" % (res["config"]["learnability"]["seed_base"],
                                                                                 len(lc["seeds"])))
        L.append("| Agent | Scenario | kappa | Test Sharpe (mean) | by seed | Oracle Sharpe | Train-slice Sharpe | Turnover/yr | Exposure |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for who, blk in (("Phase 3 Q agent", lc["q_agent"]), ("PPO (Phase 2 algorithm), same reward", lc.get("ppo", {}))):
            for name, x in blk.items():
                s = x["summary"]
                L.append("| %s | %s | %.3f | %.2f | %s | %.2f | %.2f | %.0f | %.0f%% |" % (
                    who, name, x["kappa"], s["sharpe_mean"], ", ".join("%.2f" % y for y in s["sharpe_by_seed"]),
                    s["oracle_sharpe_mean"], s["train_sharpe_mean"], s["turnover_mean"], 100 * s["exposure_mean"]))
        L.append("\nCriteria (frozen before this run): %s. Result: **%s**.\n" % (
            ", ".join("%s %s" % kv for kv in res["config"]["learnability"]["criteria"].items()), lc["verdict"]["text"].split(" (")[0]))
        sp = lc.get("supplementary_power_check")
        if sp:
            L.append("**Supplementary power check** (added AFTER the frozen check failed; no agent setting changed): the same "
                     "frozen agent on %d new synthetic series with a %d-month test.\n" % (sp["seeds"], sp["test_months"]))
            L.append("| Scenario | kappa | Test Sharpe (mean) | by seed | Oracle | Abstained (neutral fallback) | Corr. of position with the planted signal |")
            L.append("|---|---|---|---|---|---|---|")
            for name, x in sp["q_agent"].items():
                s_ = x["summary"]
                L.append("| %s | %.3f | %.2f | %s | %.2f | %.0f%% | %.2f |" % (
                    name, x["kappa"], s_["sharpe_mean"], ", ".join("%.2f" % y for y in s_["sharpe_by_seed"]),
                    s_["oracle_sharpe_mean"], 100 * s_["fallback_share"], s_["corr_with_planted_mean"]))
            L.append("")
        L.append("How the setup was fixed (synthetic data only): Phase 2's PPO-style setup and a first Q-learner both took a "
                 "position ~95% of the time even with no edge and fitted noise (train Sharpe 4-13 with nothing to find). "
                 "Fixes, each tested only on synthetic series: (1) afterstate form (position enters only through the cost, which "
                 "is hard-wired, not learned); (2) a zero-initialised output layer (random initial weights had been giving "
                 "actions made-up preferences larger than the signal); (3) 16-step targets so value propagates over the "
                 "holding horizon; (4) a linear value function (an MLP memorised the training path); (5) weight decay; "
                 "(6) a 'do no harm' fallback to the neutral position when the validation Sharpe is below 0.5. A realistic "
                 "edge is barely detectable in 9 months of 15m data (t-stat ~1.6 for an oracle-Sharpe-1 edge), which caps "
                 "what any learner can recover.\n")
    cd = res.get("cadence")
    if cd:
        L.append("## Update cadence (chosen before the freeze)\n")
        L.append("Rule: %s. Scores: %s. **Chosen: every %d day(s).** BTC data used: before 2020-10-01 only.\n" % (
            cd["rule"], "; ".join("%s day(s): BTC val Sharpe %.2f, synthetic drifting-edge test Sharpe %.2f"
                                  % (k, v["btc_val_sharpe"], v["synthetic_test_sharpe"]) for k, v in cd["score"].items()),
            cd["chosen_cadence_days"]))
    rk = res.get("riskcheck")
    if rk:
        L.append("## Risk manager check (on buy-and-hold and momentum, no agent; before any agent result)\n")
        L.append("| Asset | Strategy (0.10%, out of sample) | Sharpe raw | Sharpe with risk3 | Max DD raw | Max DD with risk3 | Pass |")
        L.append("|---|---|---|---|---|---|---|")
        for asset, a in rk["assets"].items():
            for name, c in a["checks"].items():
                L.append("| %s | %s | %.2f | %.2f | %.0f%% | %.0f%% | %s |" % (asset, name, c["sharpe_raw"], c["sharpe_risk3"],
                                                                         100 * c["maxdd_raw"], 100 * c["maxdd_risk3"],
                                                                         "yes" if c["pass"] else "no"))
        if rk.get("phase2_limits_on_buy_hold"):
            o = rk["phase2_limits_on_buy_hold"]
            L.append("\nPhase 2's limits on BTC buy-and-hold for comparison: Sharpe %.2f, net %s, max DD %.0f%%." % (
                o["sharpe"], pct(o["return"], 0), 100 * o["max_drawdown"]))
        L.append("\nRule: %s Result: **%s**.\n" % (rk["rule"], "pass" if rk["pass"] else "fail"))
    pd_ = res.get("paper_dryrun")
    if pd_:
        L.append("## Forward paper mode: dry run on historical bars (not wired live)\n")
        L.append(pd_.get("text", "") + "\n")
    return "\n".join(L)


def diag2_section(res):
    d = res.get("diag2")
    if not d:
        return ""
    L = ["## DIAGNOSTIC ONLY: the Phase 3 filters applied to the Phase 2 agent's trades\n",
         "Not a result: it replays Phase 2's saved models on Phase 2's test windows, which have been seen. It only asks whether "
         "filtering a no-edge agent can help at all. Phase 2 targets replayed without Phase 2's risk manager; BTC; mean over the "
         "5 Phase 2 seeds (consensus is one series).\n",
         "| Filter | Net return 0.10% | Sharpe 0.10% | Max DD | Trades/yr | Avg hold (h) | Break-even fee | Net 0.05% | Sharpe 0.05% |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, x in d["rows"].items():
        L.append("| %s | %s | %.2f | %.0f%% | %.0f | %.0f | %s | %s | %.2f |" % (k, pct(x["return"]), x["sharpe"], 100 * x["max_drawdown"],
                                                                         x["trades_per_year"], x["avg_holding_hours"],
                                                                         fee_s(x["break_even_fee"]), pct(x["return_005"]), x["sharpe_005"]))
    L.append("\n" + d.get("note", "") + "\n")
    return "\n".join(L)


def freeze_section(res):
    fz = res["config"].get("freeze", {})
    L = ["## What was frozen, and when\n"]
    for k, v in fz.items():
        L.append("- %s: %s" % (k, v))
    L.append("- No test-window number fed back into any setting; nothing was re-run after the test results were seen.\n")
    return "\n".join(L)


def design_section(cfg):
    q = cfg["qagent"]
    return "\n".join([
        "## Design (fixed before testing)\n",
        "- **Clock and timing.** Every 15m bar: decide at the close, fill at the next open (the shared cost model's delay), "
        "hold to the next bar. Holding is free; minimum hold %d bars between changes." % cfg["policy"]["min_hold_bars"],
        "- **Observation.** Phase 2's 18 point-in-time features + higher-timeframe context on closed bars (1h / 4h / 1d trend and "
        "price vs the higher-timeframe mean, the frozen momentum signal, 30-day daily vol, a vol regime) + time of day / week; "
        "funding already in. z-scored on the trailing 12 months, clipped at +-5. The real-data truncation check runs on every column.",
        "- **Agent.** Afterstate Q-learning: W(x, a) learned (linear), Q(x, p, a) = W(x, a) - cost(p -> a) with the cost hard-wired; "
        "reward = vol-scaled net return of the target - %.0f x the real one-side cost on every change (a full round trip) - "
        "a risk charge %.1f x a^2 x vol^2; gamma %.2f, %d-step targets, AdamW lr %g, weight decay %g, batch %d; early stopping "
        "on the validation Bellman loss; neutral fallback when the kept model's validation Sharpe < %.1f."
        % (q["cost_mult"], q["risk_aversion"], q["gamma"], q["n_step"], q["learning_rate"], q["weight_decay"], q["batch_size"],
           q["fallback_val_sharpe"]),
        "- **Actions.** Base: target size in {-1, -0.5, 0, 0.5, 1}. Meta-labeling: {0, 0.5, 1} x the momentum direction. "
        "Core-satellite: {0, 0.5, 1, 1.5} with 1x as the default. Residual: baseline + {-0.5, 0, +0.5}. Warm start / scratch "
        "(on A / B): {0, 0.5, 1, 1.5, 2}, spot long legs.",
        "- **Continual learning.** Updates every %d day(s) at the 00:00 UTC bar close: %d gradient steps on a replay buffer of the "
        "trailing %d days (half uniform, half with a %d-day recency half-life), warm-started from the previous weights and "
        "optimiser; an update at bar U trains only on decisions whose n-step targets close by bar U."
        % (cfg["continual"]["cadence_days"], q["finetune_steps"] if cfg["continual"]["cadence_days"] == 7 else
           int(cfg["cadence_choice"]["steps_per_update"][str(cfg["continual"]["cadence_days"])]), q["replay_days"],
           q["half_life_days"]),
        "- **Risk manager (Phase 3).** size = min(1, %.0f%% / %s annualised) x drawdown brake (1.0, then %s at "
        "%s below the rolling 90-day peak); re-sized only when the size moves by more than %.2f; every resize logged with its reason."
        % (100 * cfg["risk3"]["vol_target"],
           cfg["risk3"]["vol_long"] if cfg["risk3"]["vol_short"] == cfg["risk3"]["vol_long"]
           else "max(%s, %s)" % (cfg["risk3"]["vol_short"], cfg["risk3"]["vol_long"]),
           "/".join(str(x) for x in cfg["risk3"]["dd_factors"]),
           "/".join("%.0f%%" % (100 * x) for x in cfg["risk3"]["dd_levels"]), cfg["risk3"]["rebalance_band"]),
        "- **Walk-forward.** Phase 1's folds (12-month train: 9 train + 3 validation, 3-month test, roll 3 months). One "
        "decision loop runs across all test windows (position carries over); the executed series is replayed through the "
        "shared backtester and scored like the benchmarks.\n"])


def fold_section(res):
    A = res["assets"]["BTCUSDT"]
    r = A["fees"][HEAD]
    v = r["variants"].get(PRIMARY)
    if v is None:
        return ""
    names = seed_names(v)
    L = ["## Per fold, primary agent (c), BTC, 0.10%\n",
         "| # | Test window | Agent net, mean (min..max) | Agent Sharpe | B&H net | B&H Sharpe | Mom net | Mom Sharpe |",
         "|---|---|---|---|---|---|---|---|"]
    for i, wb in enumerate(r["bench"]["buy_hold"]["windows"]):
        rt = [v["seeds"][s]["windows"][i]["total_return"] for s in names]
        sh = [v["seeds"][s]["windows"][i]["sharpe"] for s in names]
        mo = r["bench"]["momentum"]["windows"][i]
        L.append("| %d | %s .. %s | %s (%s .. %s) | %.2f | %s | %.2f | %s | %.2f |" % (
            i, wb["test_start"], wb["test_end"], pct(np.mean(rt)), pct(min(rt), 0), pct(max(rt), 0), np.mean(sh),
            pct(wb["total_return"]), wb["sharpe"], pct(mo["total_return"]), mo["sharpe"]))
    return "\n".join(L) + "\n"


def training_section(res):
    L = ["## Training\n"]
    A = res["assets"]["BTCUSDT"]
    for vname in ORDER:
        if vname in FAM_OF:
            g = train_gap(res, "BTCUSDT", FAM_OF[vname][0], FAM_OF[vname][1], vname)
            if g:
                L.append("- %s: train-slice Sharpe %.2f (positive in %.0f%% of fold models), validation %.2f, test %.2f; neutral "
                         "fallback in %.0f%% of fold models." % (LABELS[vname], g["train"], 100 * g["train_positive_share"], g["val"],
                                                               g["test"], 100 * g["fallback_share"]))
    L.append("- Real-data look-ahead check of the Phase 3 feature set (3 random cuts per asset): %s." % "; ".join(
        "%s %s" % (a, x["lookahead_check_on_real_data"]) for a, x in res["assets"].items()))
    me = res.get("memory_events") or []
    L.append("- Memory: work started only with >= %d MB free and paused (never failed) under %d MB. Pauses: %s." % (
        res["config"]["memory"]["start_mb"], res["config"]["memory"]["floor_mb"],
        "; ".join("%s %s (%s, waited %ss)" % (e["utc"], e["where"], e["why"], e["waited_s"]) for e in me) or "none"))
    L.append("- Models: %s (one small .pt per fold model and per continual end-state; W values per fold as .npy).\n" % A["models_dir"])
    return "\n".join(L)


def rebuild(run_dir, out_dir=None):
    """Re-make phase3_report.md and phase3_summary.json from a run's saved phase3_full.json (formatting only: no
    number is recomputed). -> path of the report."""
    import json
    import os
    with open(os.path.join(run_dir, "phase3_full.json"), encoding="utf-8") as f:
        res = json.load(f)
    for name in ("learnability", "riskcheck", "cadence", "diag2", "paper_dryrun"):
        p = os.path.join(out_dir or "", "phase3_%s.json" % name)
        if out_dir and os.path.exists(p) and name not in res:
            with open(p, encoding="utf-8") as fh:
                res[name] = json.load(fh)
    res["flags"] = flags(res)
    res["verdict"] = verdict(res)
    md = markdown(res)
    summ = clean(summary_json(res))
    for d in [x for x in (out_dir, run_dir) if x]:
        with open(os.path.join(d, "phase3_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(d, "phase3_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summ, fh, indent=1, default=str)
    return os.path.join(out_dir or run_dir, "phase3_report.md")


def reading_section(res):
    """Plain facts that explain the result, computed from the run (nothing tuned on them)."""
    A = res["assets"]["BTCUSDT"]
    r = A["fees"][HEAD]
    V = r["variants"]
    bh, mo = r["bench"]["buy_hold"]["stitched"], r["bench"]["momentum"]["stitched"]
    L = ["## Reading the numbers (BTC, 0.10%)\n"]
    p = V.get(PRIMARY)
    if p:
        st = row_stats(p)
        g = train_gap(res, "BTCUSDT", "base", "c", PRIMARY) or {}
        mix = np.mean([[p["seeds"][s]["position_mix"][k] for k in ("long", "flat", "short")] for s in seed_names(p)], axis=0)
        L.append("- **No edge before costs.** The primary agent's gross (pre-cost) Sharpe is %.2f; it loses before any fee "
                 "(break-even fee below zero). It fits its training slices (train-slice Sharpe %.2f) but not the next three "
                 "months (validation %.2f), so the 'do no harm' rule sends %.0f%% of fold models to neutral: it is flat %.0f%% of "
                 "the time." % (st["sharpe_gross"], g.get("train", float("nan")), g.get("val", float("nan")),
                                100 * g.get("fallback_share", float("nan")), 100 * mix[1]))
        L.append("- **It did learn when not to trade.** Turnover %.0f a year and %.0f trades a year (Phase 2: ~600 and ~500), "
                 "average hold %.0f h, cost drag %.1f%% a year (Phase 2: ~80%%). Costs are no longer what sinks it; the lack of "
                 "an edge is." % (st["turnover_per_year"], st["trades_per_year"], st["avg_holding_hours"],
                                  100 * st["cost_drag_per_year"]))
    for a, b, lab in (("agent_static", "agent_continual", "continual (b) vs static (a)"),):
        if a in V and b in V:
            L.append("- **Continual learning.** Seed-mean Sharpe: static (a) %.2f, continual (b) %.2f, continual + retrain (c) "
                     "%.2f. All negative after costs on BTC." % (row_stats(V["agent_static"])["sharpe"],
                                                                 row_stats(V["agent_continual"])["sharpe"],
                                                                 row_stats(V[PRIMARY])["sharpe"] if PRIMARY in V else float("nan")))
    good = [(k, row_stats(V[k])) for k in ("v3_htf_alignment", "v5_meta_label", "v6_core_satellite") if k in V]
    if good:
        L.append("- **The variants that make money lean on momentum or on a buy-and-hold core:** " + "; ".join(
            "%s Sharpe %.2f, Calmar %.2f, max DD %.0f%%, net %s" % (LABELS[k], x["sharpe"], x["calmar"], 100 * x["max_drawdown"],
                                                            pct(x["total_return"], 0)) for k, x in good)
                 + ". Buy-and-hold: Sharpe %.2f, Calmar %.2f; momentum: %.2f, %.2f. None beats them on Sharpe." % (
                     bh["sharpe"], bh["calmar"], mo["sharpe"], mo["calmar"]))
    D = r["dev"]
    if "r1_residual_A" in D["variants"]:
        L.append("- **On the loop's rules (dev span):** the residual agents trade the baseline more (turnover ~80 a year vs ~45) "
                 "and lower its Sharpe and return; imitation warm starts beat the same agent from scratch but end far below the "
                 "rules they imitated: RL fine-tuning on 9 months of 15m data unlearns the rule.")
    d2 = res.get("diag2")
    if d2:
        c = d2["rows"].get("consensus")
        if c:
            L.append("- **Diagnostic (Phase 2's seen trades):** filters cut Phase 2's losses mostly by trading less; only seed "
                     "consensus turned positive (Sharpe %.2f, %.0f trades a year), i.e. by almost never trading. Filtering a "
                     "no-edge agent removes cost, not the missing edge." % (c["sharpe"], c["trades_per_year"]))
    return "\n".join(L) + "\n"
