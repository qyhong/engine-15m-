# -*- coding: utf-8 -*-
"""report6 -- the Phase 6 report: shaped rewards (flat scores weakly), long / short symmetry, 'do no harm' modes,
downtrends; plain answers by the rules frozen in configs/rl/phase6.yaml."""
import json
import os

import numpy as np

from . import report4
from .report3 import clean, fee_s, pct, row_stats, seed_names
from .report5 import view

HEAD, ALT = report4.HEAD, report4.ALT
LABELS6 = {
    "p4_rule": "Phase 4 primary, 'do no harm' = flat (as it is)",
    "p4_none": "Phase 4 primary, no fallback",
    "p4_trend": "Phase 4 primary, fallback = trend reference",
    "m_rule": "missed-opportunity reward, fallback flat",
    "m_none": "missed-opportunity reward, no fallback",
    "m_trend": "missed-opportunity reward, fallback = trend reference",
    "f_rule": "flat-time charge, fallback flat",
    "f_none": "flat-time charge, no fallback",
    "f_trend": "flat-time charge, fallback = trend reference",
}
REF = "p4_rule"


def _st(res, asset, span, vn, fee=HEAD):
    A = res["assets"][asset]
    r = A["fees"][fee] if span == "full" else A["fees"][fee]["dev"]
    return row_stats(r["variants"][vn])


def _seeds(res, asset, span, vn, key="sharpe"):
    A = res["assets"][asset]
    r = A["fees"][HEAD] if span == "full" else A["fees"][HEAD]["dev"]
    v = r["variants"][vn]
    return [v["seeds"][s]["stitched"][key] for s in seed_names(v)]


def clearly_beats(res, vn):
    ok, why = True, []
    for a in res["assets"]:
        P, S = _st(res, a, "full", REF), _st(res, a, "full", vn)
        sh = _seeds(res, a, "full", vn)
        c1 = S["sharpe"] >= P["sharpe"] + 0.10
        c2 = all(x > P["sharpe"] for x in sh)
        c3 = S["calmar"] > P["calmar"]
        c4 = _st(res, a, "dev", vn)["sharpe"] > _st(res, a, "dev", REF)["sharpe"]
        ok = ok and c1 and c2 and c3 and c4
        why.append("%s: Sharpe %.2f vs %.2f%s, seeds %s, Calmar %.2f vs %.2f, to 2025-11-11 %.2f vs %.2f" % (
            a, S["sharpe"], P["sharpe"], " (+0.10 needed)" if not c1 else "", ", ".join("%.2f" % x for x in sh),
            S["calmar"], P["calmar"], _st(res, a, "dev", vn)["sharpe"], _st(res, a, "dev", REF)["sharpe"]))
    return ok, "; ".join(why)


def turnover_flags(res):
    out = {}
    for a in res["assets"]:
        P = _st(res, a, "full", REF)
        for vn in res["config"]["variants"]:
            S = _st(res, a, "full", vn)
            out.setdefault(vn, {})[a] = {"turnover": S["turnover_per_year"], "trades": S["trades_per_year"],
                                         "exploded": bool(S["turnover_per_year"] > 100 or S["trades_per_year"] > 2 * P["trades_per_year"])}
    return out


def chosen_values(res, vn, asset="BTCUSDT"):
    tr = res["assets"][asset]["training"].get(vn) or {}
    vals, fb = [], []
    for s, recs in tr.items():
        for r in recs:
            ch = r.get("chosen") or {}
            if "shaping_value" in ch:
                vals.append(ch["shaping_value"])
            fb.append(bool(r.get("fallback")))
    cnt = dict((str(v), vals.count(v)) for v in sorted(set(vals)))
    return cnt, (float(np.mean(fb)) if fb else None)


def sides_table(res):
    rows = ["| Variant | Asset | Long / short / flat (time) | Net from long bars /yr | Net from short bars /yr | Gross long /yr | "
            "Gross short /yr |", "|---|---|---|---|---|---|---|"]
    for vn in list(res["config"]["variants"]) + ["buy_hold", "momentum"]:
        for a, AN in res["analytics"].items():
            x = AN.get(vn)
            if not x:
                continue
            f = x["full"]
            rows.append("| %s | %s | %.0f%% / %.0f%% / %.0f%% | %s | %s | %s | %s |" % (
                report4.label(vn) if vn in LABELS6 else {"buy_hold": "Buy-and-hold (perp)", "momentum": "Momentum (daily, L/S)"}[vn],
                a, 100 * f["long_share"], 100 * f["short_share"], 100 * f["flat_share"], pct(f["net_long_per_year"]),
                pct(f["net_short_per_year"]), pct(f["gross_long_per_year"]), pct(f["gross_short_per_year"])))
    rows.append("")
    rows.append("Full span, 0.10% a side, seed means; per-bar returns summed by the side held (a simple, additive split).")
    return "\n".join(rows)


def down_table(res):
    pers = list(res["periods"])
    rows = ["| Variant | Asset | " + " | ".join("%s (%s .. %s)" % (p, res["periods"][p][0], res["periods"][p][1][:10]) for p in pers)
            + " | Down months: mean / profitable | Up months: mean |", "|---|---|" + "---|" * (len(pers) + 2)]
    for vn in list(res["config"]["variants"]) + ["buy_hold", "momentum"]:
        for a, AN in res["analytics"].items():
            x = AN.get(vn)
            if not x:
                continue
            m = x["monthly"]
            rows.append("| %s | %s | %s | %s / %s of %d | %s |" % (
                report4.label(vn) if vn in LABELS6 else {"buy_hold": "Buy-and-hold (perp)", "momentum": "Momentum (daily, L/S)"}[vn],
                a, " | ".join("-" if x["periods"][p] is None else pct(x["periods"][p]) for p in pers),
                "-" if m["mean_down_month_pct"] is None else "%+.1f%%" % m["mean_down_month_pct"],
                "-" if m["share_down_months_profitable"] is None else "%.0f%%" % (100 * m["share_down_months_profitable"]),
                int(m["down_months"]), "-" if m["mean_up_month_pct"] is None else "%+.1f%%" % m["mean_up_month_pct"]))
    rows.append("")
    rows.append("Net of 0.10% fees, seed means. The current decline overlaps the strategy loop's sealed year; it is shown for "
                "RL only (nothing here is compared with the loop's rules there).")
    return "\n".join(rows)


def p5_rows(res):
    p5 = res.get("phase5") or {}
    head = p5.get("headline") or {}
    rows = []
    for a, H in head.items():
        for vn in ("t1_band2x", "t2_hold2d", "t3_tilt"):
            if vn in H:
                f = H[vn]["full"]
                rows.append("| Phase 5 %s | %s | %.2f | %.2f | %.0f%% | %.2f | %.0f |" % (
                    vn, a, f["sharpe"], f["sharpe_gross"], 100 * f["max_drawdown"], f["calmar"], f["turnover_per_year"]))
    if not rows:
        return ""
    return "\n".join(["| Phase 5 variant (reference) | Asset | Net Sharpe 0.10% | Gross Sharpe | Max DD | Calmar | Turnover/yr |",
                      "|---|---|---|---|---|---|---|"] + rows)


def fold_split(res):
    """Compounded net return (0.10%) over the folds where the model traded vs the folds where 'do no harm' fired (which
    are flat under 'rule', the model under 'none', the momentum rule under 'trend'), per seed."""
    rows = ["| Variant | Asset | 'Do no harm' folds by seed (of 25) | Return in the agent's folds, by seed | Return in the 'do no harm' "
            "folds, by seed |", "|---|---|---|---|---|"]
    for vn in res["config"]["variants"]:
        for a, A in res["assets"].items():
            v = A["fees"][HEAD]["variants"][vn]
            tr = A["training"][vn]
            n, ra, rf = [], [], []
            for s in seed_names(v):
                w = v["seeds"][s]["windows"]
                fb = [bool(r["fallback"]) for r in tr[s]][:len(w)]
                n.append(sum(fb))
                ra.append(float(np.prod([1 + x["total_return"] for x, f in zip(w, fb) if not f]) - 1))
                rf.append(float(np.prod([1 + x["total_return"] for x, f in zip(w, fb) if f]) - 1))
            rows.append("| %s | %s | %s | %s | %s |" % (LABELS6.get(vn, vn), a, ", ".join(str(x) for x in n),
                                                      ", ".join(pct(x, 0) for x in ra), ", ".join(pct(x, 0) for x in rf)))
    return "\n".join(rows)


def verdict(res):
    p = res["config"]["primary"]
    names = list(res["config"]["variants"])
    lines = []
    beats = dict((vn, clearly_beats(res, vn)) for vn in names if vn != REF)
    P = dict((a, _st(res, a, "full", REF)) for a in res["assets"])
    S = dict((a, _st(res, a, "full", p)) for a in res["assets"])
    an = res["analytics"]
    lines.append("%s. The Phase 6 primary (%s), BTC full span after 0.10%% fees: net Sharpe %.2f (seeds %s) vs the Phase 4 "
                 "primary's %.2f; ETH %.2f vs %.2f. Time long / short / flat (BTC): %.0f%% / %.0f%% / %.0f%% (Phase 4 primary "
                 "%.0f%% / %.0f%% / %.0f%%)." % (
                     "YES" if beats[p][0] else "NO", LABELS6[p], S["BTCUSDT"]["sharpe"],
                     ", ".join("%.2f" % x for x in _seeds(res, "BTCUSDT", "full", p)), P["BTCUSDT"]["sharpe"],
                     S["ETHUSDT"]["sharpe"], P["ETHUSDT"]["sharpe"],
                     100 * an["BTCUSDT"][p]["full"]["long_share"], 100 * an["BTCUSDT"][p]["full"]["short_share"],
                     100 * an["BTCUSDT"][p]["full"]["flat_share"], 100 * an["BTCUSDT"][REF]["full"]["long_share"],
                     100 * an["BTCUSDT"][REF]["full"]["short_share"], 100 * an["BTCUSDT"][REF]["full"]["flat_share"]))
    win = [vn for vn, (ok, _) in beats.items() if ok]
    if win:
        lines.append("Variants that clearly beat the Phase 4 primary by the frozen rule: %s (of %d tried)." % (
            ", ".join(LABELS6[v] for v in win), len(names) - 1))
    else:
        lines.append("No Phase 6 variant clearly beats the Phase 4 primary by the frozen rule (%d tried)." % (len(names) - 1))
    return " ".join(lines), beats, win


def markdown(res):
    report4.LABELS.update(LABELS6)
    p = res["config"]["primary"]
    names = [p] + [n for n in res["config"]["variants"] if n != p]
    v = view(res, names)
    v["config"]["primary"] = p
    vtxt, beats, win = verdict(res)
    tf = turnover_flags(res)
    L = ["# RL Phase 6 report: flat scores weakly, long and short both ways", "",
         "Run `%s`, generated %s. Paper only. Seeds %s; 15-minute bars and clock; Phase 4's data, folds, inputs, risk manager, "
         "backtester, fees and benchmarks. Owner's direction: \"the RL need to learn to profit from downtrend also. stay flat "
         "should have a weak scoring so the RL will have more motivation to take long or short\"." % (
             res["run_id"], res["generated_utc"], res["seeds"]), "",
         "**Holdout honesty.** Phase 4 already scored every test window through 2026-11-11, so no historical span is unseen "
         "for RL: everything below was designed after those windows were seen. Both spans are shown; the loop's rules A and B "
         "only up to 2025-11-11. The forward paper run is the real test.", "",
         "## Verdict", "", vtxt, ""]
    L += ["## What changed (frozen in configs/rl/phase6.yaml before any result)", "",
          "- **Reward (training only).** The literal \"net return - beta x reference return\" cannot change any decision with "
          "this agent: the reference's return does not depend on the action, so it lowers every action's value equally (flat "
          "scores negative in a trend, but long scores lower by the same amount). It was replaced before any run by forms "
          "that charge the IDLE part of the book: *missed opportunity* (the idle part pays beta x the daily momentum rule's "
          "return, long or short; beta in {0.25, 0.5, 1} chosen on validation) and *flat-time charge* (the idle part pays "
          "lam x one round trip per day; lam in {0.25, 0.5, 1} on validation). Decisions and results use the real net P&L.",
          "- **Symmetry.** Actions -1, -0.5, 0, +0.5, +1 with the same costs each way; perp funding on the whole position both "
          "ways (shorts receive positive funding); signed features.",
          "- **'Do no harm'.** Three modes on the same trained models: flat (Phase 4's rule), none, the trend reference.", ""]
    for vn in ("m_trend", "f_trend"):
        cnt, fb = chosen_values(res, vn)
        L.append("- Chosen per fold (BTC records, 3 seeds): %s: %s; validation net Sharpe under 0.5 (the 'do no harm' "
                 "trigger) in %.0f%% of fold models." % (LABELS6[vn].split(",")[0], cnt, 100 * (fb or 0)))
    cnt, fb = chosen_values(res, REF)
    L.append("- Phase 4 primary: 'do no harm' trigger in %.0f%% of fold models." % (100 * (fb or 0)))
    L.append("")
    for asset in res["assets"]:
        L += ["## %s, 2020-10-01 .. 2026-11-11, 0.10%% a side" % asset, "", report4.table(v, asset, HEAD, "full", p), ""]
        L += ["### %s, 0.05%% a side" % asset, "", report4.table(v, asset, ALT, "full", p), ""]
        L += ["### %s, up to 2025-11-11, 0.10%%%s" % (asset, " (with the loop's rules A and B)" if asset == "BTCUSDT" else ""),
              "", report4.table(v, asset, HEAD, "dev", p), ""]
    pr = p5_rows(res)
    if pr:
        L += ["### Phase 5's trade-less variants (reference, full span)", "", pr, ""]
    L += ["## Where the gain comes from: the agent's folds vs the 'do no harm' folds", "",
          "The 'trend' fallback hands the folds whose validation net Sharpe is under 0.5 to the daily momentum rule; those folds "
          "are flat under 'rule' and the model's own under 'none'. A large share of the 'trend' variants' gain is momentum's "
          "return in those folds, and the pattern behind it (the Phase 4 agent sat flat in folds where momentum made large "
          "gains: folds 6, 9, 12, 22 in Phase 4's per-fold table) was visible before Phase 6 was designed: hindsight risk.", "",
          fold_split(res), ""]
    L += ["## Long vs short", "", sides_table(res), ""]
    L += ["## Downtrends", "", down_table(res), ""]
    L += ["## By seed (full span): Sharpe / net return / break-even fee", ""]
    for asset in res["assets"]:
        L += ["**%s**" % asset, "", report4.seed_table(v, asset), ""]
    from .report5 import judge
    V = {"assets": dict((a, dict((sp, {"variants": dict((vn, judge(res, a, sp, vn)) for vn in names)}) for sp in ("full", "dev")))
                        for a in res["assets"])}
    v["verdict"] = V
    L += ["## Edge before costs", "", report4.edge_table(v), ""]
    fl = report4.flags(v)
    L += ["## Flags", ""]
    for asset, fa in fl.items():
        ids = [f["id"] for f in next(iter(fa.values()))]
        L.append("**%s**\n" % asset)
        L.append("| Variant | " + " | ".join(ids) + " | turnover exploded |\n|---|" + "---|" * (len(ids) + 1))
        for vn, f in fa.items():
            d = dict((x["id"], x["fired"]) for x in f)
            L.append("| %s | %s | %s |" % (report4.label(vn), " | ".join("FIRED" if d.get(i) else "-" for i in ids),
                                           "FIRED" if tf[vn][asset]["exploded"] else "- (%.0f /yr, %.0f trades)" % (
                                               tf[vn][asset]["turnover"], tf[vn][asset]["trades"])))
        L.append("")
    L += ["## Clearly beats the Phase 4 primary? (frozen rule)", ""]
    for vn, (ok, why) in beats.items():
        L.append("- %s: **%s**. %s" % (LABELS6[vn], "yes" if ok else "no", why))
    L.append("")
    if win:
        best = res["config"]["primary"] if res["config"]["primary"] in win else max(win, key=lambda x: _st(res, "BTCUSDT", "full", x)["sharpe"])
        L += ["**Proposal (not wired in):** a second forward paper book for %s, in playbook5's style (same live step, its own "
              "models, the chosen 'do no harm' mode), NOT passed, with %d variants tried stated on the page." % (
                  LABELS6[best], len(names) - 1), ""]
    else:
        L += ["No second forward book is proposed (the frozen bar was not met).", ""]
    L += ["## What was frozen, and when", ""]
    for k, x in (res["config"]["phase6"].get("freeze") or {}).items():
        L.append("- %s: %s" % (k, x))
    if res.get("training_run"):
        L.append("- Training: %.0f min, memory pauses: %s" % (res["training_run"]["minutes"],
                                                             res["training_run"]["memory_events"] or "none"))
    L.append("- Evaluation: %.0f min, memory pauses: %s" % (res["elapsed_min"], res.get("memory_events") or "none"))
    L += ["", "Machine-readable: `phase6_summary.json`. Nothing here is wired into the live engine."]
    return "\n".join(L) + "\n", vtxt, beats, win, tf


def write(res, out_dir, run_dir=None):
    md, vtxt, beats, win, tf = markdown(res)
    summ = {"phase": 6, "paper_only": True, "run_id": res["run_id"], "generated_utc": res["generated_utc"],
            "verdict": vtxt, "clearly_beats": dict((k, {"yes": b[0], "why": b[1]}) for k, b in beats.items()),
            "proposal": win, "turnover": tf, "analytics": res["analytics"], "periods": res["periods"],
            "headline": dict((a, dict((vn, {"full": dict(row_stats(res["assets"][a]["fees"][HEAD]["variants"][vn])),
                                            "dev": dict(row_stats(res["assets"][a]["fees"][HEAD]["dev"]["variants"][vn])),
                                            "full_005": dict(row_stats(res["assets"][a]["fees"][ALT]["variants"][vn]))})
                                      for vn in res["assets"][a]["fees"][HEAD]["variants"])) for a in res["assets"])}
    for d in [out_dir] + ([run_dir] if run_dir else []):
        with open(os.path.join(d, "phase6_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(d, "phase6_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(clean(summ), fh, indent=1, default=float)
    return os.path.join(out_dir, "phase6_report.md")
