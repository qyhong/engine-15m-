# -*- coding: utf-8 -*-
"""report2 -- the Phase 2 report: overfitting flags, a plain verdict, the markdown report, the small
phase2_summary.json a future web "Lab" tab can read, and the risk manager's out-of-sample log."""
import csv

import numpy as np

SUMMARY_KEYS = [("total_return", "return"), ("sharpe", "sharpe"), ("sortino", "sortino"),
                ("max_drawdown", "max_drawdown"), ("calmar", "calmar"), ("turnover_per_year", "turnover_per_year"),
                ("avg_holding_hours", "avg_holding_hours"), ("cost_drag_per_year", "cost_drag_per_year")]


def _pct(x, d=1):
    return ("%+." + str(d) + "f%%") % (100.0 * x)


def _fees(res):
    f = list(res["results"])
    return f[0], f[1]


def _seed_names(r):
    return sorted(r["agents"], key=lambda s: int(s.split("_s")[1]))


def _agent_window_mean(r, key):
    names = _seed_names(r)
    return np.array([[r["agents"][s]["windows"][i][key] for s in names] for i in range(len(r["agents"][names[0]]["windows"]))])


def _random_window_mean(r, key):
    rw = r["random_windows"]
    names = sorted(rw)
    return np.array([[rw[s][i][key] for s in names] for i in range(len(rw[names[0]]))]).mean(axis=1)


def fold_table(res):
    """Per fold: agent test metrics per seed, train/val Sharpe per seed, benchmarks (headline fee)."""
    f10, _ = _fees(res)
    r = res["results"][f10]
    names = _seed_names(r)
    rows = []
    for i, w in enumerate(r["buy_hold"]["windows"]):
        tr = [res["training"]["s%s_f%02d" % (s.split("_s")[1], i)]["train"]["sharpe"] for s in names]
        va = [res["training"]["s%s_f%02d" % (s.split("_s")[1], i)]["val"]["sharpe"] for s in names]
        te = [r["agents"][s]["windows"][i]["sharpe"] for s in names]
        rt = [r["agents"][s]["windows"][i]["total_return"] for s in names]
        rows.append({"fold": i, "test_start": w["test_start"], "test_end": w["test_end"],
                     "agent_return_mean": float(np.mean(rt)), "agent_return_min": float(np.min(rt)),
                     "agent_return_max": float(np.max(rt)), "agent_sharpe_mean": float(np.mean(te)),
                     "train_sharpe_mean": float(np.mean(tr)), "val_sharpe_mean": float(np.mean(va)),
                     "train_sharpe": tr, "val_sharpe": va, "test_sharpe": te,
                     "bh_return": w["total_return"], "bh_sharpe": w["sharpe"],
                     "mom_return": r["momentum"]["windows"][i]["total_return"],
                     "mom_sharpe": r["momentum"]["windows"][i]["sharpe"]})
    return rows


def flags(res):
    """-> list of {id, fired, detail}. Thresholds come from the frozen config (flags section)."""
    fc = res["config"]["flags"]
    f10, f05 = _fees(res)
    r, r5 = res["results"][f10], res["results"][f05]
    names = _seed_names(r)
    out = []
    ft = fold_table(res)
    tr = np.array([x["train_sharpe"] for x in ft])
    va = np.array([x["val_sharpe"] for x in ft])
    te = np.array([x["test_sharpe"] for x in ft])
    gap, vgap = float((tr - te).mean()), float((va - te).mean())
    out.append({"id": "train_test_sharpe_gap", "fired": bool(gap > fc["train_test_sharpe_gap"]),
                "value": round(gap, 3),
                "detail": "mean over folds and seeds: train-slice Sharpe %.2f, validation %.2f, test %.2f; train - test = %.2f "
                          "(threshold %.1f); validation - test = %.2f."
                          % (tr.mean(), va.mean(), te.mean(), gap, fc["train_test_sharpe_gap"], vgap)})
    sh = np.array([r["agents"][s]["stitched"]["sharpe"] for s in names])
    rt = np.array([r["agents"][s]["stitched"]["total_return"] for s in names])
    sign_split = bool((rt > 0).any() and (rt <= 0).any())
    wsign = np.sign(_agent_window_mean(r, "total_return"))
    disagree = float(np.mean([len(set(row[row != 0])) > 1 for row in wsign]))
    out.append({"id": "seed_dispersion", "fired": bool(sh.std(ddof=1) > fc["seed_sharpe_sd"] or sign_split),
                "value": round(float(sh.std(ddof=1)), 3),
                "detail": "stitched Sharpe by seed %s (sd %.2f, threshold %.2f); stitched return by seed %s%s; seeds disagree on "
                          "the sign of a fold's return in %.0f%% of folds."
                          % (", ".join("%.2f" % x for x in sh), sh.std(ddof=1), fc["seed_sharpe_sd"],
                             ", ".join(_pct(x, 0) for x in rt), " (signs differ)" if sign_split else "", 100 * disagree)})
    am = _agent_window_mean(r, "sharpe").mean(axis=1)
    ar = _agent_window_mean(r, "total_return").mean(axis=1)
    wins_txt, fired = [], False
    for name, sh_b, rt_b in (("buy-and-hold", np.array([w["sharpe"] for w in r["buy_hold"]["windows"]]),
                              np.array([w["total_return"] for w in r["buy_hold"]["windows"]])),
                             ("momentum", np.array([w["sharpe"] for w in r["momentum"]["windows"]]),
                              np.array([w["total_return"] for w in r["momentum"]["windows"]])),
                             ("random (mean)", _random_window_mean(r, "sharpe"), _random_window_mean(r, "total_return"))):
        s_share, r_share = float((am > sh_b).mean()), float((ar > rt_b).mean())
        fired = fired or s_share < fc["min_fold_win_share"]
        wins_txt.append("%s: Sharpe higher in %d of %d folds (%.0f%%), return higher in %d (%.0f%%)"
                        % (name, int((am > sh_b).sum()), len(am), 100 * s_share, int((ar > rt_b).sum()), 100 * r_share))
    out.append({"id": "beats_benchmarks_in_under_half_the_folds", "fired": bool(fired),
                "detail": "agent seed mean per fold vs " + "; ".join(wins_txt) + " (flag if any Sharpe share < %.0f%%)."
                          % (100 * fc["min_fold_win_share"])})
    flips = []
    for s in names + ["mean"]:
        a = r["agent"]["stitched"]["total_return"]["mean"] if s == "mean" else r["agents"][s]["stitched"]["total_return"]
        b = r5["agent"]["stitched"]["total_return"]["mean"] if s == "mean" else r5["agents"][s]["stitched"]["total_return"]
        if (a > 0) != (b > 0):
            flips.append("%s %s at %s vs %s at %s" % (s, _pct(a, 0), f10, _pct(b, 0), f05))
    bh10, bh05 = r["buy_hold"]["stitched"]["sharpe"], r5["buy_hold"]["stitched"]["sharpe"]
    m10, m05 = r["agent"]["stitched"]["sharpe"]["mean"], r5["agent"]["stitched"]["sharpe"]["mean"]
    if (m10 > bh10) != (m05 > bh05):
        flips.append("the agent's Sharpe is %s buy-and-hold's at %s but %s it at %s"
                     % ("above" if m10 > bh10 else "below", f10, "above" if m05 > bh05 else "below", f05))
    out.append({"id": "fee_sign_flip", "fired": bool(flips),
                "detail": "; ".join(flips) if flips else "no seed (nor the mean) changes sign between %s and %s, and the "
                                                        "comparison with buy-and-hold does not flip." % (f10, f05)})
    to = np.array([r["agents"][s]["stitched"]["turnover_per_year"] for s in names])
    cd = np.array([r["agents"][s]["stitched"]["cost_drag_per_year"] - r["agents"][s]["stitched"]["funding_per_year"]
                   for s in names])
    out.append({"id": "high_turnover", "fired": bool((to > fc["max_turnover_per_year"]).any()),
                "value": round(float(to.mean()), 1),
                "detail": "turnover per year by seed %s (threshold %d); trading costs excluding funding %s a year."
                          % (", ".join("%.0f" % x for x in to), fc["max_turnover_per_year"],
                             ", ".join("%.1f%%" % (100 * x) for x in cd))})
    mix = [r["agents"][s].get("position_mix", {}) for s in names]
    longish = [m.get("long", 0) for m in mix]
    flat = [m.get("flat", 0) for m in mix]
    degenerate = any(l > 0.9 for l in longish) or any(f_ > 0.95 for f_ in flat)
    out.append({"id": "degenerate_policy", "fired": bool(degenerate),
                "detail": "share of out-of-sample bars long / flat / short by seed: %s (flag if a seed is long > 90%% of the "
                          "time, a buy-and-hold clone, or flat > 95%%)."
                          % "; ".join("s%s %.0f/%.0f/%.0f%%" % (s.split("_s")[1], 100 * m.get("long", 0), 100 * m.get("flat", 0),
                                                              100 * m.get("short", 0)) for s, m in zip(names, mix))})
    return out


def diagnostics(res):
    """Plain facts that explain the result (computed, not tuned on): before-cost edge, cost split,
    training fit, checkpoint choice, and what the risk manager alone does to buy-and-hold."""
    f10, _ = _fees(res)
    r = res["results"][f10]
    names = _seed_names(r)
    st = [r["agents"][s]["stitched"] for s in names]
    tk = list(res["training"].values())
    kept = [max([h["check"] for h in t["checks"] if h.get("kept")]) for t in tk]
    bh, bhr = r["buy_hold"]["stitched"], r["buy_hold_risk_manager"]["stitched"]
    return {"agent_gross_return_mean": float(np.mean([x["total_return_gross"] for x in st])),
            "agent_gross_sharpe_by_seed": [float(x["sharpe_gross"]) for x in st],
            "agent_fee_per_year_mean": float(np.mean([x["fee_per_year"] for x in st])),
            "agent_slippage_spread_per_year_mean": float(np.mean([x["slippage_per_year"] + x["spread_per_year"] for x in st])),
            "agent_trades_per_year_mean": float(np.mean([x["trades"] / max(x["years"], 1e-9) for x in st])),
            "min_hold_refusals_mean": float(np.mean([r["agents"][s].get("min_hold_refusals", 0) for s in names])),
            "train_slice_sharpe_mean": float(np.mean([t["train"]["sharpe"] for t in tk])),
            "train_slice_sharpe_positive_share": float(np.mean([t["train"]["sharpe"] > 0 for t in tk])),
            "kept_first_check_share": float(np.mean([k == 1 for k in kept])),
            "bh_sharpe": bh["sharpe"], "bh_with_risk_manager_sharpe": bhr["sharpe"],
            "bh_with_risk_manager_return": bhr["total_return"],
            "bh_with_risk_manager_kill_triggers": r["buy_hold_risk_manager"].get("risk_counts", {}).get("kill_switch_triggered", 0),
            "bh_with_risk_manager_daily_triggers": r["buy_hold_risk_manager"].get("risk_counts", {}).get("daily_loss_triggered", 0)}


def verdict(res):
    f10, f05 = _fees(res)
    r = res["results"][f10]
    names = _seed_names(r)
    bh, mo = r["buy_hold"]["stitched"], r["momentum"]["stitched"]
    ag = r["agent"]["stitched"]
    sh = [r["agents"][s]["stitched"]["sharpe"] for s in names]
    cal = [r["agents"][s]["stitched"]["calmar"] for s in names]
    v = {"agent_sharpe_mean": ag["sharpe"]["mean"], "bh_sharpe": bh["sharpe"], "momentum_sharpe": mo["sharpe"],
         "agent_calmar_mean": ag["calmar"]["mean"], "bh_calmar": bh["calmar"],
         "agent_return_mean": ag["total_return"]["mean"], "bh_return": bh["total_return"],
         "agent_maxdd_mean": ag["max_drawdown"]["mean"], "bh_maxdd": bh["max_drawdown"],
         "seeds_beating_bh_sharpe": int(sum(s > bh["sharpe"] for s in sh)), "seeds": len(names),
         "seeds_beating_bh_calmar": int(sum(c > bh["calmar"] for c in cal))}
    v["beats_bh_risk_adjusted"] = bool(v["agent_sharpe_mean"] > bh["sharpe"] and v["seeds_beating_bh_sharpe"] == len(names)
                                       and v["agent_calmar_mean"] > bh["calmar"])
    v["beats_momentum_risk_adjusted"] = bool(v["agent_sharpe_mean"] > mo["sharpe"] and v["agent_calmar_mean"] > mo["calmar"])
    if v["beats_bh_risk_adjusted"]:
        txt = ("YES on these numbers: out of sample, after %s fees, the agent's Sharpe (seed mean %.2f) is above buy-and-hold's "
               "(%.2f) for all %d seeds, and its Calmar (%.2f) is above buy-and-hold's (%.2f). Read the flags before believing it."
               % (f10.replace("fee_", ""), v["agent_sharpe_mean"], bh["sharpe"], len(names), v["agent_calmar_mean"], bh["calmar"]))
    else:
        why = []
        if v["agent_sharpe_mean"] <= bh["sharpe"]:
            why.append("its seed-mean Sharpe %.2f is not above buy-and-hold's %.2f" % (v["agent_sharpe_mean"], bh["sharpe"]))
        if v["seeds_beating_bh_sharpe"] < len(names):
            why.append("only %d of %d seeds beat buy-and-hold's Sharpe" % (v["seeds_beating_bh_sharpe"], len(names)))
        if v["agent_calmar_mean"] <= bh["calmar"]:
            why.append("its Calmar %.2f is not above buy-and-hold's %.2f" % (v["agent_calmar_mean"], bh["calmar"]))
        txt = ("NO. Out of sample, after %s fees, the PPO agent does not beat buy-and-hold on a risk-adjusted basis across seeds: %s. "
               "Net return: agent %s on average over %d seeds vs buy-and-hold %s (max drawdown %.0f%% vs %.0f%%)."
               % (f10.replace("fee_", ""), "; ".join(why), _pct(v["agent_return_mean"], 0), len(names), _pct(bh["total_return"], 0),
                  100 * v["agent_maxdd_mean"], 100 * bh["max_drawdown"]))
    txt += (" Against the daily 30-day momentum rule (Sharpe %.2f, Calmar %.2f) the agent %s."
            % (mo["sharpe"], mo["calmar"], "is better on both" if v["beats_momentum_risk_adjusted"] else "is not better on both"))
    v["text"] = txt
    return v


def _metric_block(st):
    return dict((out, float(st[k])) for k, out in SUMMARY_KEYS)


def _fold_blocks(wins):
    return [dict([("fold", w["window"]), ("test_start", w["test_start"]), ("test_end", w["test_end"])] +
                 [(out, float(w[k])) for k, out in SUMMARY_KEYS]) for w in wins]


def _mean_folds(win_lists):
    n = len(win_lists[0])
    out = []
    for i in range(n):
        w0 = win_lists[0][i]
        row = {"fold": w0["window"], "test_start": w0["test_start"], "test_end": w0["test_end"]}
        for k, o in SUMMARY_KEYS:
            row[o] = float(np.mean([wl[i][k] for wl in win_lists]))
        out.append(row)
    return out


def summary_json(res):
    """Small, stable shape for a future web 'Lab' tab. Out-of-sample numbers only."""
    fees = {}
    for fee, r in res["results"].items():
        names = _seed_names(r)
        strat = {"agent_seed_mean": {"overall": dict((o, float(r["agent"]["stitched"][k]["mean"])) for k, o in SUMMARY_KEYS),
                                     "overall_sd": dict((o, float(r["agent"]["stitched"][k]["sd"])) for k, o in SUMMARY_KEYS),
                                     "folds": _mean_folds([r["agents"][s]["windows"] for s in names])}}
        for s in names:
            strat[s] = {"overall": _metric_block(r["agents"][s]["stitched"]), "folds": _fold_blocks(r["agents"][s]["windows"])}
        strat["buy_hold"] = {"overall": _metric_block(r["buy_hold"]["stitched"]), "folds": _fold_blocks(r["buy_hold"]["windows"])}
        strat["momentum"] = {"overall": _metric_block(r["momentum"]["stitched"]), "folds": _fold_blocks(r["momentum"]["windows"])}
        rw = r["random_windows"]
        strat["random_mean"] = {"overall": dict((o, float(r["random"]["stitched"][k]["mean"])) for k, o in SUMMARY_KEYS),
                                "folds": _mean_folds([rw[s] for s in sorted(rw)]), "seeds": r["random"]["seeds"]}
        strat["buy_hold_with_risk_manager"] = {"overall": _metric_block(r["buy_hold_risk_manager"]["stitched"]),
                                               "folds": _fold_blocks(r["buy_hold_risk_manager"]["windows"]),
                                               "note": "reference only: the agent's risk manager applied to always-long"}
        fees[fee] = {"strategies": strat}
    w = res["windows"]
    return {"schema": "rl_phase2_summary/1", "run_id": res["run_id"], "generated_utc": res["generated_utc"],
            "paper_only": True, "market": "%s perpetual, 15m bars" % res["config"]["data"]["symbol"],
            "out_of_sample": {"start": w[0]["test_start"], "end": w[-1]["test_end"], "folds": len(w)},
            "headline_fee": list(res["results"])[0], "seeds": res["seeds"], "timesteps_per_fold": res["timesteps"],
            "metrics_note": "return = stitched net return; sharpe/sortino annualised (35,040 bars a year); max_drawdown fraction; "
                            "turnover_per_year in full sides; cost_drag_per_year = fees + spread + slippage + funding",
            "fees": fees, "flags": res["flags"], "diagnostics": diagnostics(res),
            "verdict": dict((k, v) for k, v in res["verdict"].items())}


def write_risk_log(path, events):
    import pandas as pd
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seed", "bar_close_utc", "rule", "requested", "allowed", "position_before", "reason"])
        for e in events:
            w.writerow([e["seed"], str(pd.Timestamp(e["close_ms"], unit="ms", tz="UTC")), e["rule"], e["requested"],
                        e["allowed"], e["current"], e["reason"]])


# ---------------------------------------------------------------- markdown
COLS = [("total_return", "Net return", lambda x: _pct(x)), ("sharpe", "Sharpe", lambda x: "%.2f" % x),
        ("sortino", "Sortino", lambda x: "%.2f" % x), ("max_drawdown", "Max DD", lambda x: "%.0f%%" % (100 * x)),
        ("calmar", "Calmar", lambda x: "%.2f" % x), ("turnover_per_year", "Turnover/yr", lambda x: "%.0f" % x),
        ("avg_holding_hours", "Avg hold (h)", lambda x: "%.0f" % x),
        ("cost_drag_per_year", "Cost drag/yr", lambda x: "%.1f%%" % (100 * x))]


def _row(label, st):
    return "| %s | " % label + " | ".join(fn(st[k]) for k, _, fn in COLS) + " |"


def _table(r):
    head = "| Strategy | " + " | ".join(c[1] for c in COLS) + " |\n|---|" + "---|" * len(COLS)
    a = r["agent"]["stitched"]
    rows = [head, "| **PPO agent, mean of %d seeds** | " % r["agent"]["seeds"] +
            " | ".join("**%s**" % fn(a[k]["mean"]) for k, _, fn in COLS) + " |",
            "| agent sd across seeds | " + " | ".join(fn(a[k]["sd"]).replace("+", "") for k, _, fn in COLS) + " |"]
    for s in _seed_names(r):
        rows.append(_row("agent seed %s" % s.split("_s")[1], r["agents"][s]["stitched"]))
    rows.append(_row("Buy-and-hold", r["buy_hold"]["stitched"]))
    rows.append(_row("Momentum (daily, 30-day sign, long/short)", r["momentum"]["stitched"]))
    ra = r["random"]["stitched"]
    rows.append("| Random agent (mean of %d) | " % r["random"]["seeds"] + " | ".join(fn(ra[k]["mean"]) for k, _, fn in COLS) + " |")
    rows.append(_row("*reference: buy-and-hold through the risk manager*", r["buy_hold_risk_manager"]["stitched"]))
    return "\n".join(rows) + "\n"


def markdown(res):
    cfg = res["config"]
    f10, f05 = _fees(res)
    r, r5 = res["results"][f10], res["results"][f05]
    names = _seed_names(r)
    v = res["verdict"]
    w = res["windows"]
    e, rk, ag, tr = cfg["env"], cfg["risk"], cfg["agent"], cfg["train"]
    s = ["# RL Phase 2 report: PPO agent, walk-forward, out of sample after costs", "",
         "Run `%s`, generated %s. %s perpetual (Binance USD-M), 15-minute bars. Paper only: no orders, no keys. "
         "Out of sample = %d stitched 3-month test windows, %s to %s. Seeds %s, %d PPO steps per fold and seed, "
         "run time %.0f min." % (res["run_id"], res["generated_utc"], cfg["data"]["symbol"], len(w), w[0]["test_start"],
                                 w[-1]["test_end"], res["seeds"], res["timesteps"], res["elapsed_min"]), "",
         "## Verdict", "", v["text"], ""]
    s += ["## Headline: stitched out of sample, %s a side (the owner's rule)" % f10.replace("fee_", ""), "", _table(r)]
    s += ["## Same, %s a side (Binance USDT-M taker)" % f05.replace("fee_", ""), "", _table(r5)]
    s += ["Every number is out of sample and after costs (fee, half-spread, vol-scaled slippage, funding). The agent's test "
          "windows were each touched once, by a model trained only on the 12 months before. The risk manager is part of the "
          "agent's execution; the benchmarks run without it, and the reference row shows what the risk manager alone does to "
          "buy-and-hold.", ""]
    s += ["## Overfitting flags", ""]
    for fl in res["flags"]:
        s.append("- **%s: %s.** %s" % (fl["id"], "FIRED" if fl["fired"] else "not fired", fl["detail"]))
    dg = diagnostics(res)
    s += ["", "## Reading the numbers (%s)" % f10.replace("fee_", ""), "",
          "- **No edge before costs.** The agent's gross (pre-cost) return averages %s over the span; gross Sharpe by seed %s. "
          "Before any fee it is about as good as a coin."
          % (_pct(dg["agent_gross_return_mean"], 0), ", ".join("%.2f" % x for x in dg["agent_gross_sharpe_by_seed"])),
          "- **Costs then finish it.** About %.0f trades a year: fees %.0f%% and spread + slippage %.0f%% of equity a year. "
          "The turnover penalty and the 12-hour minimum hold did not stop the churn: the policy asked for a change the "
          "minimum hold refused %.0f times per seed out of sample."
          % (dg["agent_trades_per_year_mean"], 100 * dg["agent_fee_per_year_mean"],
             100 * dg["agent_slippage_spread_per_year_mean"], dg["min_hold_refusals_mean"]),
          "- **PPO did not even fit its own training data.** Mean Sharpe on the training slice (the data it learned on) "
          "%.2f, positive in %.0f%% of the 125 fold-seed trainings; validation kept the very first checkpoint in %.0f%% "
          "of them. With hourly decisions on 9 months of 15m data, the reward is mostly noise and costs."
          % (dg["train_slice_sharpe_mean"], 100 * dg["train_slice_sharpe_positive_share"], 100 * dg["kept_first_check_share"]),
          "- **The frozen risk limits are costly on their own.** Buy-and-hold through the same risk manager makes %s "
          "(Sharpe %.2f vs %.2f without it): the 30%% kill switch fired %d times and the 5%% daily-loss stop %d times, "
          "each time selling into a fall and missing the rebound. That handicap applies to the agent too. It is a "
          "finding about the limits, not the main reason: the agent has no edge before costs, and even buy-and-hold "
          "under these limits (Sharpe %.2f) is far ahead of it."
          % (_pct(dg["bh_with_risk_manager_return"], 0), dg["bh_with_risk_manager_sharpe"], dg["bh_sharpe"],
             dg["bh_with_risk_manager_kill_triggers"], dg["bh_with_risk_manager_daily_triggers"],
             dg["bh_with_risk_manager_sharpe"])]
    s += ["", "## What was frozen, and when", "",
          "- 11 Nov 2026, before any RL code was run: the momentum benchmark (daily at the 00:00 UTC bar close, fill next open, "
          "sign of the 30-day return, long/short), recorded in `configs/rl/phase1.yaml` and `docs/RL.md`; Phase 1 benchmarks "
          "were re-run with it.",
          "- 11 Nov 2026 about 12:55 UTC, before any agent was trained or evaluated on any window: every value in "
          "`configs/rl/phase2.yaml` (features, action set, decision schedule, minimum hold, reward and turnover penalty, risk "
          "limits, PPO hyperparameters, training budget, validation rule, seeds, overfitting-flag thresholds). Only speed and "
          "memory were measured first (an 8,192-step smoke run) to size the budget.",
          "- Model choice inside each fold used only the validation slice (last 3 months of the train window). No test number "
          "fed back into any choice; nothing was re-run after the test results were seen.", ""]
    s += ["## Design (fixed before testing)", "",
          "- Observation at a decision bar: the %d point-in-time features of that bar (z-scored with the fold's training-slice "
          "mean/sd, clipped at +-%.0f) + current target, time in position, risk-restriction flag." % (len(res["features"]["columns"]), e["obs_clip"]),
          "- Action: target position in %s, decided at the close of each %d-th bar (each UTC hour), filled at the next open. "
          "Minimum hold %d bars (%.0f h) between changes; risk exits are never held back." % (e["actions"], e["decision_every_bars"],
                                                                                            e["min_hold_bars"], e["min_hold_bars"] / 4.0),
          "- Reward: %.0f x (sum of per-bar log(1 + net return) - %.4f x |target change|); net return uses the shared cost model "
          "(`costs.py`), the same arrays as the backtester (env and backtest P&L agree to %.1e per bar on the real run)."
          % (e["reward_scale"], e["turnover_penalty"], res["env_backtest_max_abs_diff"]),
          "- Risk manager (training and evaluation): max position %.1f; daily loss %.0f%% -> flat for the rest of the UTC day; "
          "drawdown kill switch %.0f%% from peak -> flat %d bars, then peak reset; vol breaker %s > %.1f x %s -> |position| <= %.1f. "
          "Every block/resize is logged (`phase2_risk_log.csv`)." % (rk["max_position"], 100 * rk["max_daily_loss"],
                                                                    100 * rk["kill_drawdown"], rk["kill_cooldown_bars"],
                                                                    rk["vol_breaker_short"], rk["vol_breaker_mult"],
                                                                    rk["vol_breaker_long"], rk["vol_breaker_max_position"]),
          "- PPO (Stable-Baselines3): MLP %s (tanh) for policy and value, lr %g, %d envs x %d steps, batch %d, %d epochs, gamma %.2f, "
          "GAE %.2f, clip %.1f, entropy %.3f; CPU, %d torch threads, below-normal priority. Training episodes: %d hourly "
          "decisions from a random start in the training slice." % (ag["net_arch"], ag["learning_rate"], ag["n_envs"], ag["n_steps"],
                                                                     ag["batch_size"], ag["n_epochs"], ag["gamma"], ag["gae_lambda"],
                                                                     ag["clip_range"], ag["ent_coef"], ag["torch_threads"],
                                                                     e["episode_decisions"]),
          "- Per fold: train on the first 9 months of the 12-month window, check the policy on the last 3 months %d times during "
          "training, keep the best validation Sharpe (early stop after %d checks without improvement), then run it once on the "
          "next 3 months. Out of sample, one simulation runs across all test windows (position and risk state carry over) and "
          "the executed target series is replayed through the Phase 1 backtester." % (tr["evals"], tr["patience"]), ""]
    ft = fold_table(res)
    s += ["## Per fold, %s a side" % f10.replace("fee_", ""), "",
          "| # | Test window | Agent net, mean (min..max of seeds) | Agent Sharpe | Train Sharpe | Val Sharpe | B&H net | B&H Sharpe | Mom net | Mom Sharpe |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for x in ft:
        s.append("| %d | %s .. %s | %s (%s .. %s) | %.2f | %.2f | %.2f | %s | %.2f | %s | %.2f |"
                 % (x["fold"], x["test_start"], x["test_end"], _pct(x["agent_return_mean"]), _pct(x["agent_return_min"], 0),
                    _pct(x["agent_return_max"], 0), x["agent_sharpe_mean"], x["train_sharpe_mean"], x["val_sharpe_mean"],
                    _pct(x["bh_return"]), x["bh_sharpe"], _pct(x["mom_return"]), x["mom_sharpe"]))
    s += ["", "## Behaviour out of sample (%s)" % f10.replace("fee_", ""), "",
          "| Seed | Long / flat / short (share of bars) | Trades/yr | Min-hold refusals | Risk: vol breaker | daily-loss blocks (triggers) | kill-switch blocks (triggers) | forced flats |",
          "|---|---|---|---|---|---|---|---|"]
    for sn in names:
        a = r["agents"][sn]
        m, c = a.get("position_mix", {}), a.get("risk_counts", {})
        s.append("| %s | %.0f%% / %.0f%% / %.0f%% | %.0f | %d | %d | %d (%d) | %d (%d) | %d |"
                 % (sn.split("_s")[1], 100 * m.get("long", 0), 100 * m.get("flat", 0), 100 * m.get("short", 0),
                    a["stitched"]["trades"] / max(a["stitched"]["years"], 1e-9), a.get("min_hold_refusals", 0),
                    c.get("vol_breaker", 0), c.get("daily_loss", 0), c.get("daily_loss_triggered", 0), c.get("kill_switch", 0),
                    c.get("kill_switch_triggered", 0), c.get("forced_flat", 0)))
    c = r["buy_hold_risk_manager"].get("risk_counts", {})
    s.append("| B&H + risk manager | - | %.0f | - | %d | %d (%d) | %d (%d) | %d |"
             % (r["buy_hold_risk_manager"]["stitched"]["trades"] / max(r["buy_hold_risk_manager"]["stitched"]["years"], 1e-9),
                c.get("vol_breaker", 0), c.get("daily_loss", 0), c.get("daily_loss_triggered", 0), c.get("kill_switch", 0),
                c.get("kill_switch_triggered", 0), c.get("forced_flat", 0)))
    tk = res["training"]
    secs = [t["seconds"] for t in tk.values()]
    steps = [t["timesteps_run"] for t in tk.values()]
    kept = [max([h["check"] for h in t["checks"] if h.get("kept")]) for t in tk.values()]
    s += ["", "## Training", "",
          "- %d fold-seed trainings; PPO steps run %d..%d (early stopping), mean %.0f s each; kept checkpoint: %s."
          % (len(tk), min(steps), max(steps), np.mean(secs),
             ", ".join("check %d x%d" % (k, kept.count(k)) for k in sorted(set(kept)))),
          "- Models: `%s` (one ~20 KB .npz per fold and seed: actor weights + the fold's normaliser)." % res["models_dir"],
          "- Real-data look-ahead check of the Phase 2 feature set at 3 random cuts: %s." % res["features"]["lookahead_check_on_real_data"],
          "- Memory: every fold started with >= %d MB free; the guard stops training under %d MB. Waits and stops in this "
          "run (the owner's history replay ran alongside): %s."
          % (tr["memory_start_mb"], tr["memory_floor_mb"],
             "; ".join("seed %s fold %s at %s UTC: %s" % (m["seed"], m["fold"], m["utc"], m["event"])
                       for m in res["progress"].get("memory_events", [])) or "none"), "",
          "## Not done here (Phase 3, not started)", "",
          "- Robustness: more seeds, cost stress, regime splits, ETH, decision-interval and penalty sensitivity reported as such "
          "(new experiments, never re-tuning on these test windows).", "",
          "Machine-readable: `phase2_summary.json` (per fold and overall, every strategy, both fees, flags, verdict).", ""]
    return "\n".join(s)
