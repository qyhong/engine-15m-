# -*- coding: utf-8 -*-
"""report -- grade H20-H24 against the registered criteria, write harness_report.md, harness_summary.json and
loop_state.json (the holdout ledger in loop_state.json is preserved, never rewritten)."""
import json
import math
import os
import time

import numpy as np

from . import core

TARGET, MILESTONE = 0.25, 0.10
NOTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes_round1.md")
STATE = os.path.join(core.OUT_DIR, "loop_state.json")
P2 = os.path.join(core.ROOT, "research", "out", "rl", "phase2_summary.json")
HEAD, ALT = "fee_0.10%", "fee_0.05%"


def pct(x, d=1):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else ("%+.*f%%" % (d, 100 * x))


def fee_s(x):
    if x is None:
        return "none (loses at 0 fee)"
    if x == float("inf") or (isinstance(x, float) and x > 0.04):
        return "> 4%"
    return "%.3f%%" % (100 * x)


def grade(s, bench, eth=None, other="ETHUSDT"):
    """Registered criteria T (thesis) and L (loop target) + flags for one graded strategy (one asset)."""
    h, a = s[HEAD]["stitched"], s[ALT]["stitched"]
    bh, bha = bench["buy_hold"][HEAD]["stitched"], bench["buy_hold"][ALT]["stitched"]
    bhf = bench["buy_hold"][HEAD]["folds"]
    folds = s[HEAD]["folds"]
    nf = len(folds)
    share_sh = sum(1 for f, b in zip(folds, bhf) if f["sharpe"] > b["sharpe"]) / nf
    share_pos = sum(1 for f in folds if f["total_return"] > 0) / nf
    beats = lambda x, b: x["sharpe"] > b["sharpe"] and x["calmar"] > b["calmar"]
    rnd = s.get("random_matched", {}).get("sharpe_mean", -9)
    T = {"a_trades_le_100": h["trades_per_year"] <= 100, "b_beats_bh_risk_adjusted": beats(h, bh),
         "c_fold_share_ge_half": share_sh >= 0.5, "d_holds_at_0.10": beats(h, bh) or not beats(a, bha),
         "e_beats_matched_random": h["sharpe"] > rnd}
    flags = {"fold_share": share_sh < 0.5, "fee_only_at_0.05": beats(a, bha) and not beats(h, bh),
             "high_turnover": h["trades_per_year"] > 100,
             "not_significant": not s["significance"]["significant"]}
    if eth is not None:
        e, ebh = eth["s"][HEAD]["stitched"], eth["bench"]["buy_hold"][HEAD]["stitched"]
        flags["%s_fails" % other[:3].lower()] = e["cagr"] <= 0 or e["max_drawdown"] > ebh["max_drawdown"]
    L_core = {"cagr_ge_25": h["cagr"] >= TARGET, "maxdd_le_bh": h["max_drawdown"] <= bh["max_drawdown"],
              "positive_folds_gt_half": share_pos > 0.5}
    ok_flags = not any(flags.values())
    return {"T": T, "thesis_pass": all(T.values()), "L": L_core, "flags": flags,
            "development_pass": all(L_core.values()) and ok_flags,
            "milestone_10": h["cagr"] >= MILESTONE and L_core["maxdd_le_bh"] and L_core["positive_folds_gt_half"] and ok_flags,
            "fold_share_sharpe_vs_bh": share_sh, "positive_fold_share": share_pos}


def _row(name, m, be=None, extra=""):
    return "| %s | %s | %s | %.2f | %.2f | %.2f | %.0f%% | %.2f | %.0f | %s | %.1f%% | %s |%s" % (
        name, pct(m["cagr"]), pct(m["total_return"], 0), m["sharpe"], m.get("sharpe_gross", float("nan")), m["sortino"],
        100 * m["max_drawdown"], m["calmar"], m["trades_per_year"],
        ("%.0f" % m["avg_holding_hours"]) if m["avg_holding_hours"] < 40000 else "whole span",
        100 * m["cost_drag_per_year"], fee_s(be) if be is not False else "-", extra)


HDR = ("| Strategy | CAGR | Net return | Sharpe | Gross Sharpe | Sortino | Max DD | Calmar | Trades/yr | Avg hold (h) "
       "| Cost drag/yr | Break-even fee |\n|---|---|---|---|---|---|---|---|---|---|---|---|")


def build(caches, replay, n_graded, n_trials, log=print):
    if not caches:
        log("no caches")
        return
    p2 = None
    if os.path.exists(P2):
        with open(P2, encoding="utf-8") as f:
            p2 = json.load(f)
    grades = {}
    for asset, c in caches.items():
        g = {}
        other = [x for x in caches if x != asset]
        oc = caches[other[0]] if other else None
        for h, s in c["families"].items():
            eth = {"s": oc["families"][h], "bench": oc["benchmarks"]} if oc else None
            g[h] = grade(s, c["benchmarks"], eth, other[0] if other else "ETHUSDT")
        for i, s in enumerate(c["ladder"]):
            eth = {"s": oc["ladder"][i], "bench": oc["benchmarks"]} if oc else None
            g["H21:" + s["name"]] = grade(s, c["benchmarks"], eth, other[0] if other else "ETHUSDT")
        grades[asset] = g

    L = []
    w = L.append
    btc = caches.get("BTCUSDT") or list(caches.values())[0]
    w("# Harness study (loop round 1): can a harness turn an over-trading 15m strategy into one that beats buy-and-hold?\n")
    w("Generated %s UTC by `py -3 research/harness/run.py`. Paper research only; nothing here places orders. "
      "Hypotheses H20-H24 were registered in `research/HYPOTHESES.md` at 13:45 UTC on 11 Nov 2026, before any harness "
      "result existed. **Development data only:** the last 12 months (2025-11-11 to 2026-11-11) are a sealed holdout "
      "that no number in this report has touched. No holdout look was used in round 1 (see `research/harness/LOOP.md`).\n"
      % time.strftime("%Y-%m-%d %H:%M", time.gmtime()))
    if os.path.exists(NOTES):
        with open(NOTES, encoding="utf-8") as f:
            w(f.read().strip() + "\n")

    w("## Method\n")
    w("- Markets: BTCUSDT perpetual (the RL Phase 2 bars and funding, `data/rl/`), then ETHUSDT (engine spot 15m bars + "
      "perp funding) under identical rules. Bars %s to %s (BTC).\n" % (btc["first_bar"][:16], btc["last_bar"][:16]))
    w("- Walk-forward: the RL Phase 1/2 folds cut at the seal: 12-month train, next 3 months test, roll 3 months; "
      "%d folds; development out of sample = stitched test windows %s to %s. In each fold the variant with the best "
      "train-window net Sharpe at 0.10%% is used on the test window; one backtest runs over the stitched series "
      "(positions and costs carry across fold edges). The 0.05%% line re-runs the same selections.\n"
      % (btc["folds"], btc["oos_start"], btc["oos_end"]))
    w("- Costs: `engine15.rl.costs` exactly (a test checks the lean backtester equals `engine15.rl.backtest` to 1e-15 per "
      "bar): fee 0.10% a side (headline) or 0.05%, half-spread 0.5 bp, slippage 0.10 x 96-bar vol, funding on the "
      "position held at each settlement. Decide at a bar's close, fill at the next open. Above 1x (family 3) every cost "
      "term scales linearly.\n")
    w("- Metrics: `engine15.rl.metrics` (15m bars, 35,040 a year). CAGR = (final / initial)^(1 / years) - 1 of the "
      "stitched out-of-sample equity, net of fees and funding. Trades/yr = position changes a year (a tilt counts). "
      "Break-even fee = the fee a side at which the stitched net return is zero.\n")
    w("- Benchmarks over the same span and costs: buy-and-hold 1x; the frozen daily 30-day momentum rule (long/short); "
      "a random strategy with the same number of position changes (10 seeds, levels drawn from the strategy's own); "
      "Phase 1's daily random agent; the RL Phase 2 agent for reference (its numbers cover Oct 2020 to Nov 2026, "
      "holdout included, so they are not on the same span).\n")
    w("- Multiple testing: %d variants per asset this round (%d graded strategies per asset: 3 walk-forward headlines + 24 "
      "ladder levels). Each graded strategy gets a paired block-bootstrap p-value for Sharpe minus buy-and-hold Sharpe "
      "(daily returns, 20-day blocks, 2,000 draws), judged at the Bonferroni level 0.05 / %d = %.4f, and a deflated "
      "Sharpe probability with %d trials (crude, assumes independent trials: a caution, not a test).\n"
      % (n_trials, n_graded, n_graded, 0.05 / n_graded, n_trials))

    for asset, c in caches.items():
        b = c["benchmarks"]
        bh, mo = b["buy_hold"][HEAD]["stitched"], b["momentum"][HEAD]["stitched"]
        w("## %s: development out of sample %s to %s\n" % (asset, c["oos_start"], c["oos_end"]))
        w("### Annual return (CAGR) against the target, 0.10%% a side\n")
        w("| Strategy | CAGR | vs 25%% target | vs buy-and-hold (%s) | vs momentum (%s) | 10%% milestone | Max DD (B&H %.0f%%) | Positive folds | Development pass |"
          % (pct(bh["cagr"]), pct(mo["cagr"]), 100 * bh["max_drawdown"]))
        w("|---|---|---|---|---|---|---|---|---|")
        allg = [(h, c["families"][h]) for h in ("H20", "H22", "H23")] + [("H21:" + s["name"], s) for s in c["ladder"]]
        for h, s in allg:
            m = s[HEAD]["stitched"]
            g = grades[asset][h]
            w("| %s %s | %s | %s | %s | %s | %s | %.0f%% | %.0f%% | %s |" % (
                h.split(":")[0], s["name"] if h.startswith("H21") else s["name"].split(":")[0], pct(m["cagr"]),
                pct(m["cagr"] - TARGET), pct(m["cagr"] - bh["cagr"]), pct(m["cagr"] - mo["cagr"]),
                "yes" if g["milestone_10"] else ("CAGR only" if m["cagr"] >= MILESTONE else "no"),
                100 * m["max_drawdown"], 100 * g["positive_fold_share"], "YES" if g["development_pass"] else "no"))
        w("| Buy-and-hold | %s | %s | 0 | %s | | %.0f%% | | |" % (pct(bh["cagr"]), pct(bh["cagr"] - TARGET),
                                                               pct(bh["cagr"] - mo["cagr"]), 100 * bh["max_drawdown"]))
        w("| Momentum (daily, 30-day) | %s | %s | %s | 0 | | %.0f%% | | |\n" % (pct(mo["cagr"]), pct(mo["cagr"] - TARGET),
                                                                          pct(mo["cagr"] - bh["cagr"]), 100 * mo["max_drawdown"]))
        for fee in (HEAD, ALT):
            w("### Headline table, %s a side\n" % fee[4:])
            w(HDR)
            for h in ("H20", "H22", "H23"):
                s = c["families"][h]
                w(_row("**%s %s**" % (h, s["name"]), s[fee]["stitched"], s.get("breakeven_fee") if fee == HEAD else False))
            for k, nm in (("buy_hold", "Buy-and-hold"), ("momentum", "Momentum (daily, 30-day, long/short)")):
                w(_row(nm, b[k][fee]["stitched"], b[k].get("breakeven_fee") if fee == HEAD else False))
            if fee == HEAD:
                rd = b["random_daily"][HEAD]["stitched"]
                w(_row("Random agent, daily (Phase 1), mean of 10", rd, False))
                for h in ("H20", "H22", "H23"):
                    rm = c["families"][h]["random_matched"]
                    w("| Random, matched to %s (mean of 10) | %s | %s | %.2f | | | %.0f%% | | (same) | | | |" % (
                        h, pct(rm["cagr_mean"]), pct(rm["total_return_mean"], 0), rm["sharpe_mean"], 100 * rm["max_drawdown_mean"]))
                if p2 and asset == "BTCUSDT":
                    o = p2["fees"][HEAD]["strategies"]["agent_seed_mean"]["overall"]
                    w("| *RL Phase 2 agent, mean of 5 seeds (Oct 2020 - Nov 2026, not the same span)* | - | %s | %.2f | | %.2f | %.0f%% | %.2f | ~600 turnover | %.0f | %.0f%% | |"
                      % (pct(o["return"], 0), o["sharpe"], o["sortino"], 100 * o["max_drawdown"], o["calmar"],
                         o["avg_holding_hours"], 100 * o["cost_drag_per_year"]))
            w("")
        w("### Graded strategies: registered criteria and flags (%s)\n" % asset)
        w("| Strategy | T: <=100 trades/yr | beats B&H Sharpe+Calmar | Sharpe > B&H in >= half folds | > matched random | Thesis pass | Flags fired | Boot p (Sharpe - B&H) | DSR prob |")
        w("|---|---|---|---|---|---|---|---|---|")
        for h, s in allg:
            g = grades[asset][h]
            fl = [k for k, v in g["flags"].items() if v]
            sg = s["significance"]
            yn = lambda v: "yes" if v else "no"
            w("| %s %s | %s | %s | %s (%.0f%%) | %s | %s | %s | %.3f | %.2f |" % (
                h.split(":")[0], s["name"].split(":")[0] if not h.startswith("H21") else s["name"],
                yn(g["T"]["a_trades_le_100"]), yn(g["T"]["b_beats_bh_risk_adjusted"]), yn(g["T"]["c_fold_share_ge_half"]),
                100 * g["fold_share_sharpe_vs_bh"], yn(g["T"]["e_beats_matched_random"]),
                "**YES**" if g["thesis_pass"] else "no", ", ".join(fl) if fl else "none", sg["boot_p"], sg["deflated_sharpe_prob"]))
        w("")
        w("### Per fold, 0.10%% (%s): net return (Sharpe)\n" % asset)
        w("| # | Test window | H20 | H22 | H23 | Buy-and-hold | Momentum | H20 / H22 / H23 variant chosen on the train window |")
        w("|---|---|---|---|---|---|---|---|")
        F = dict((h, c["families"][h]) for h in ("H20", "H22", "H23"))
        for i, bf in enumerate(b["buy_hold"][HEAD]["folds"]):
            cell = lambda x: "%s (%.2f)" % (pct(x["total_return"], 0), x["sharpe"])
            w("| %d | %s .. %s | %s | %s | %s | %s | %s | %s / %s / %s |" % (
                i, bf["test_start"], bf["test_end"], cell(F["H20"][HEAD]["folds"][i]), cell(F["H22"][HEAD]["folds"][i]),
                cell(F["H23"][HEAD]["folds"][i]), cell(bf), cell(b["momentum"][HEAD]["folds"][i]),
                F["H20"]["selected"][i], F["H22"]["selected"][i], F["H23"]["selected"][i]))
        w("")
        w("### Trade count vs net return (%s)\n" % asset)
        w("**Out of sample, the fixed ladder (H21; nothing fitted), 0.10% a side:**\n")
        w("| Base | Level | Trades/yr | CAGR | Net return | Sharpe | Gross Sharpe | Max DD | Cost drag/yr | Break-even fee |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for s in c["ladder"]:
            m = s[HEAD]["stitched"]
            w("| %s | %s | %.0f | %s | %s | %.2f | %.2f | %.0f%% | %.1f%% | %s |" % (
                s["base"], s["level"], m["trades_per_year"], pct(m["cagr"]), pct(m["total_return"], 0), m["sharpe"],
                m["sharpe_gross"], 100 * m["max_drawdown"], 100 * m["cost_drag_per_year"], fee_s(s.get("breakeven_fee"))))
        w("")
        ex = c["families"]["H20"]["train_exploration"]
        bins = [(0, 10), (10, 30), (30, 100), (100, 300), (300, 1000), (1000, 1e9)]
        w("**Training data only (exploration, not evidence): H20's 864 variants, mean over the folds' train windows, "
          "0.10% a side:**\n")
        w("| Trades/yr | Variants | Median Sharpe | Best Sharpe | Median CAGR | Share with CAGR > 0 |")
        w("|---|---|---|---|---|---|")
        for lo, hi in bins:
            xs = [x for x in ex if lo <= x["trades_per_year"] < hi]
            if not xs:
                continue
            sh = np.array([x["sharpe"] for x in xs])
            cg = np.array([x["cagr"] for x in xs])
            w("| %s-%s | %d | %.2f | %.2f | %s | %.0f%% |" % (lo, "" if hi > 1e8 else int(hi), len(xs), np.median(sh),
                                                          sh.max(), pct(float(np.median(cg))), 100 * np.mean(cg > 0)))
        w("")

    w("## Family 4: Mind 15's own replay trades (H24; in-sample, descriptive)\n")
    w("The 10 Nov 2026 replay (`out/replay/trades_*.csv`, 0.10% fees, trades entered before the seal) already trades "
      "about 35-40 times a year. H24 keeps a trade only when its side agrees with the frozen daily momentum at entry. "
      "The replay is warm-up material for an engine designed on this history, so H24 can neither pass nor go to the "
      "holdout. Forward data (`out/live/`, since 10-11 Nov 2026) holds no closed BTC/ETH main-book trades yet: too short "
      "to say anything.\n")
    w("| Coin | Half | Trades | Mean net/trade, all | Compounded, all | Kept | Mean net/trade, kept | Compounded, kept | Win rate all / kept |")
    w("|---|---|---|---|---|---|---|---|---|")
    h24_pass = True
    for asset, r in replay.items():
        for half in ("first", "second", "all"):
            x = r[half]
            w("| %s | %s | %d | %+.2f%% | %+.0f%% | %d | %+.2f%% | %+.0f%% | %.0f%% / %.0f%% |" % (
                asset, half, x["trades"], x["mean_pct_all"], x["compound_all_pct"], x["kept"], x["mean_pct_kept"],
                x["compound_kept_pct"], 100 * x["win_rate_all"], 100 * x["win_rate_kept"]))
            if half != "all":
                h24_pass &= x["mean_pct_kept"] > x["mean_pct_all"] and x["compound_kept_pct"] > 0
    w("\nH24 registered test (kept mean above all-trades mean and kept compounded result positive, both halves, both "
      "coins): **%s** (in-sample; no pass can come of it).\n" % ("met" if h24_pass and replay else "not met"))

    # ---------------- verdicts
    w("## Verdict per family (BTCUSDT headline, 0.10% a side, development out of sample)\n")
    bb = btc["benchmarks"]
    bhm = bb["buy_hold"][HEAD]["stitched"]
    verdicts = {}
    for h, label in (("H20", "Filters on frequent 15m bases"), ("H21", "The fixed filter ladder"),
                     ("H22", "Meta-labeling on daily momentum"), ("H23", "Core-satellite overlay")):
        if h == "H21":
            lad = btc["ladder"]
            gs = [grades["BTCUSDT"]["H21:" + s["name"]] for s in lad] if "BTCUSDT" in grades else []
            best = max(lad, key=lambda s: s[HEAD]["stitched"]["sharpe"])
            bm = best[HEAD]["stitched"]
            anyp = any(g["thesis_pass"] for g in gs)
            txt = ("%s. Best ladder level by Sharpe: %s (%.0f trades/yr, CAGR %s, Sharpe %.2f vs buy-and-hold %.2f, "
                   "break-even fee %s). %s" % ("YES" if anyp else "NO", best["name"], bm["trades_per_year"], pct(bm["cagr"]),
                                               bm["sharpe"], bhm["sharpe"], fee_s(best.get("breakeven_fee")),
                                               "Some level meets the thesis criteria." if anyp else
                                               "No level cuts trades AND beats buy-and-hold risk-adjusted."))
            verdicts[h] = {"thesis_pass": anyp, "development_pass": any(g["development_pass"] for g in gs), "text": txt}
        else:
            s = btc["families"][h]
            m = s[HEAD]["stitched"]
            g = grades["BTCUSDT"][h] if "BTCUSDT" in grades else grades[list(grades)[0]][h]
            fl = [k for k, v in g["flags"].items() if v]
            txt = ("%s. %.0f trades/yr; CAGR %s (buy-and-hold %s); Sharpe %.2f vs %.2f; Calmar %.2f vs %.2f; max DD %.0f%% vs "
                   "%.0f%%; break-even fee %s; flags: %s. Development pass (25%% target): %s." % (
                       "YES" if g["thesis_pass"] else "NO", m["trades_per_year"], pct(m["cagr"]), pct(bhm["cagr"]),
                       m["sharpe"], bhm["sharpe"], m["calmar"], bhm["calmar"], 100 * m["max_drawdown"],
                       100 * bhm["max_drawdown"], fee_s(s.get("breakeven_fee")), ", ".join(fl) or "none",
                       "YES" if g["development_pass"] else "no"))
            verdicts[h] = {"thesis_pass": g["thesis_pass"], "development_pass": g["development_pass"], "text": txt}
        w("- **%s (%s): %s**\n" % (label, h, verdicts[h]["text"]))
    verdicts["H24"] = {"thesis_pass": None, "development_pass": False,
                       "text": "in-sample replay; registered test %s" % ("met" if h24_pass and replay else "not met")}

    # ---------------- JSON + loop state
    def clean(o):
        if isinstance(o, dict):
            return dict((k, clean(v)) for k, v in o.items() if k not in ("train_exploration",))
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
            return None if math.isnan(o) else "inf"
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o
    summ = {"schema": "harness_summary/1", "generated_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "paper_only": True, "round": 1, "hypotheses": ["H20", "H21", "H22", "H23", "H24"],
            "sealed_holdout": {"start": "2025-11-11", "end": "2026-11-11", "looks_used_this_round": 0},
            "target": {"cagr": TARGET, "milestone_cagr": MILESTONE, "basis": "CAGR of stitched OOS equity, net of 0.10% a side and funding",
                       "also": "15m decision clock, max DD <= buy-and-hold, > half the folds positive, flags clear"},
            "variants_per_asset": n_trials, "graded_per_asset": n_graded,
            "assets": clean(caches), "grades": clean(grades), "replay_h24": replay, "verdicts": verdicts}
    with open(os.path.join(core.OUT_DIR, "harness_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=float)

    state = {}
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
    ledger = state.get("holdout_looks", [])
    dev_passes = []
    best = None
    for asset in ("BTCUSDT",):
        if asset not in caches:
            continue
        c = caches[asset]
        allg = [(h, c["families"][h]) for h in ("H20", "H22", "H23")] + [("H21:" + s["name"], s) for s in c["ladder"]]
        for h, s in allg:
            m = s[HEAD]["stitched"]
            g = grades[asset][h]
            if g["development_pass"]:
                dev_passes.append({"id": "R1-%s-%s" % (asset, h), "cagr": m["cagr"]})
            if best is None or m["cagr"] > best["dev_cagr"]:
                best = {"id": "R1-%s-%s" % (asset, h), "name": s["name"], "dev_cagr": m["cagr"], "dev_sharpe": m["sharpe"],
                        "dev_max_drawdown": m["max_drawdown"], "trades_per_year": m["trades_per_year"],
                        "development_pass": g["development_pass"], "milestone_10": g["milestone_10"],
                        "flags": [k for k, v in g["flags"].items() if v]}
    closest = None
    if "BTCUSDT" in caches:
        c = caches["BTCUSDT"]
        allg = [(h, c["families"][h]) for h in ("H20", "H22", "H23")] + [("H21:" + s["name"], s) for s in c["ladder"]]
        def rank(h):
            score = sum(grades[a][h]["L"][k] for a in grades for k in grades[a][h]["L"])
            nfl = sum(1 for v in grades["BTCUSDT"][h]["flags"].values() if v)
            return (score, -nfl, caches["BTCUSDT"]["families"][h][HEAD]["stitched"]["cagr"] if h in caches["BTCUSDT"]["families"] else -9)
        hb = max([h for h, _ in allg], key=rank)
        closest = {"id": "R1-BTCUSDT-%s" % hb, "loop_target_criteria_met_btc_eth": rank(hb)[0], "of": 3 * len(grades),
                   "flags_btc": [k for k, v in grades["BTCUSDT"][hb]["flags"].items() if v],
                   "flags_eth": [k for k, v in grades.get("ETHUSDT", {}).get(hb, {"flags": {}})["flags"].items() if v]}
    state.update({"round": 1, "closest_to_pass": closest, "updated_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                  "target": {"cagr": TARGET, "milestone_cagr": MILESTONE,
                             "history": ["10% CAGR (owner, 11 Nov 2026)", "raised to 25% CAGR before any holdout look (owner, 11 Nov 2026)"]},
                  "sealed_holdout": {"start": "2025-11-11", "end": "2026-11-11"},
                  "variants_tried": {"round_1": {"per_asset": n_trials, "assets": list(caches)},
                                     "total": n_trials * len(caches)},
                  "development_passes": dev_passes, "holdout_looks": ledger, "holdout_looks_used": len(ledger),
                  "historical_passes": state.get("historical_passes", []), "confirmed": state.get("confirmed", []),
                  "best_so_far": best})
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(clean(state), f, indent=1, default=float)
    w("## Loop status after round 1\n")
    w("- Development passes (CAGR >= 25%%, max DD <= buy-and-hold, > half the folds positive, flags clear): %s." %
      (", ".join(d["id"] for d in dev_passes) if dev_passes else "**none**"))
    w("- Holdout looks used: %d (ledger in `research/out/harness/loop_state.json` and `research/harness/LOOP.md`)." % len(ledger))
    if best:
        w("- Best so far by development CAGR (BTC, 0.10%%): %s, CAGR %s, Sharpe %.2f, max DD %.0f%%, %.0f trades/yr; flags: %s."
          % (best["name"], pct(best["dev_cagr"]), best["dev_sharpe"], 100 * best["dev_max_drawdown"], best["trades_per_year"],
             ", ".join(best["flags"]) or "none"))
    if closest:
        w("- Closest to a development pass: %s (meets %d of %d loop-target criteria over BTC and ETH; flags BTC: %s; ETH: %s)."
          % (closest["id"], closest["loop_target_criteria_met_btc_eth"], closest["of"], ", ".join(closest["flags_btc"]) or "none",
             ", ".join(closest["flags_eth"]) or "none"))
    w("\nMachine-readable: `harness_summary.json`; loop state: `loop_state.json`; per-asset caches `cache_<asset>.json`.")
    with open(os.path.join(core.OUT_DIR, "harness_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    log("report written")
