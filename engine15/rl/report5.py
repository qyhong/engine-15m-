# -*- coding: utf-8 -*-
"""report5 -- the Phase 5 report: part 1 checks (forward run), part 2 trade-less variants, part 3 ablation; plain answers
by the rules frozen in configs/rl/phase5.yaml."""
import copy
import json
import os

import numpy as np

from . import report4
from .report3 import clean, fee_s, pct, row_stats, seed_names

HEAD, ALT = report4.HEAD, report4.ALT
PRIMARY = "q_pool2_full"
PART2 = ["t1_band2x", "t2_hold2d", "t3_tilt"]
GROUP_NAMES = {"trend": "trend", "funding": "funding / positioning", "basis": "basis", "flow": "flow / CVD / Coinbase",
               "vol": "volatility regime", "levels": "levels"}


def _labels(res):
    from .phase5 import LABELS5
    report4.LABELS.update(LABELS5)
    for g in res["config"]["phase5"]["ablation"]["groups"]:
        report4.LABELS["o_no_" + g] = "occlusion: trained primary with %s inputs set to 0" % GROUP_NAMES.get(g, g)
    report4.LABELS[PRIMARY] = "Phase 4 primary (Q, BTC+ETH pooled, expanding, readings)"


def view(res, names):
    """A copy of the result restricted to some variants (primary first), for report4's tables and flags."""
    v = dict(res)
    v["config"] = dict(res["config"])
    names = [n for n in names if n in res["config"]["variants"]]
    v["config"]["variants"] = dict((n, res["config"]["variants"][n]) for n in names)
    assets = {}
    for a, A in res["assets"].items():
        AA = dict(A)
        AA["fees"] = {}
        for fee, r in A["fees"].items():
            rr = dict(r)
            rr["variants"] = dict((n, r["variants"][n]) for n in names if n in r["variants"])
            rr["dev"] = dict(r["dev"])
            rr["dev"]["variants"] = dict((n, r["dev"]["variants"][n]) for n in names if n in r["dev"]["variants"])
            AA["fees"][fee] = rr
        assets[a] = AA
    v["assets"] = assets
    return v


def judge(res, asset, span, vn):
    A = res["assets"][asset]
    r = A["fees"][HEAD] if span == "full" else A["fees"][HEAD]["dev"]
    r5 = A["fees"][ALT] if span == "full" else A["fees"][ALT]["dev"]
    if r["variants"][vn].get("eval") == "spot":                       # the tilt is judged against spot buy-and-hold
        r = dict(r)
        r["bench"] = dict(r["bench"])
        r["bench"]["buy_hold"] = r["bench"]["buy_hold_spot"]
    yrs = r["bench"]["buy_hold"]["stitched"]["years"]
    return report4.judge_variant(r, r5, vn, yrs)


def _st(res, asset, span, vn, fee=HEAD):
    A = res["assets"][asset]
    r = A["fees"][fee] if span == "full" else A["fees"][fee]["dev"]
    return row_stats(r["variants"][vn])


def part2_summary(res):
    out = {}
    p5 = res["config"]["phase5"]
    for asset in res["assets"]:
        P = _st(res, asset, "full", PRIMARY)
        for vn in PART2:
            if vn not in res["config"]["variants"]:
                continue
            S = _st(res, asset, "full", vn)
            d = {"full": judge(res, asset, "full", vn), "dev": judge(res, asset, "dev", vn)}
            d["keeps_edge"] = bool(S["sharpe_gross"] >= 0.8 * P["sharpe_gross"])
            d["trades_less"] = bool(S["turnover_per_year"] <= 0.6 * P["turnover_per_year"])
            d["primary"] = {"gross": P["sharpe_gross"], "turnover": P["turnover_per_year"], "trades": P["trades_per_year"],
                            "net": P["sharpe"]}
            d["variant"] = {"gross": S["sharpe_gross"], "turnover": S["turnover_per_year"], "trades": S["trades_per_year"],
                            "net": S["sharpe"]}
            out.setdefault(vn, {})[asset] = d
    out["rules"] = {"keeps_edge": p5["trade_less"]["keeps_edge_rule"], "trades_less": p5["trade_less"]["trades_less_rule"]}
    return out


def part3_summary(res):
    p5 = res["config"]["phase5"]
    out = {"rows": {}, "occlusion": {}}
    P = dict((a, _st(res, a, "full", PRIMARY)) for a in res["assets"])
    for vn in p5["ablation"]["variants"]:
        if vn not in res["config"]["variants"]:
            continue
        row = {}
        for a in res["assets"]:
            S = _st(res, a, "full", vn)
            row[a] = {"gross": S["sharpe_gross"], "net": S["sharpe"], "d_gross": S["sharpe_gross"] - P[a]["sharpe_gross"],
                      "d_net": S["sharpe"] - P[a]["sharpe"], "turnover": S["turnover_per_year"],
                      "gross_dev": _st(res, a, "dev", vn)["sharpe_gross"], "net_dev": _st(res, a, "dev", vn)["sharpe"]}
        out["rows"][vn] = row
    for g in p5["ablation"]["groups"]:
        vn = "o_no_" + g
        if vn in res["config"]["variants"]:
            out["occlusion"][g] = dict((a, {"gross": _st(res, a, "full", vn)["sharpe_gross"],
                                            "d_gross": _st(res, a, "full", vn)["sharpe_gross"] - P[a]["sharpe_gross"],
                                            "net": _st(res, a, "full", vn)["sharpe"]}) for a in res["assets"])
    carries = []
    for g in p5["ablation"]["groups"]:
        r = out["rows"].get("a_no_" + g)
        if r and all(r[a]["d_gross"] <= -0.20 for a in res["assets"]):
            carries.append(g)
    out["carries_value"] = carries
    corr = dict((a, res["assets"][a].get("correlations")) for a in res["assets"])
    out["correlations"] = corr
    pos_mom = [((corr.get(a) or {}).get("full") or {}).get("position_vs_momentum") for a in res["assets"]]
    trend_by_corr = any(x is not None and x >= 0.5 for x in pos_mom)
    out["mostly_trend"] = bool(trend_by_corr or carries == ["trend"])
    out["primary_gross"] = dict((a, P[a]["sharpe_gross"]) for a in res["assets"])
    return out


def _f(x, k=2):
    return "-" if x is None else ("%+.*f" % (k, x))


def part3_text(s3, res):
    rows = s3["rows"]
    if not rows:
        return "The retrained ablations have not finished; only the occlusion and the correlations are reported."
    c = s3["correlations"]
    lines = []
    btc, eth = (c.get("BTCUSDT") or {}).get("full", {}), (c.get("ETHUSDT") or {}).get("full", {})
    lines.append("Correlation of the agent's position with the daily momentum rule's: BTC %s, ETH %s (full span); "
                 "daily net returns: BTC %s, ETH %s; with buy-and-hold's daily returns: BTC %s, ETH %s." % (
                     _f(btc.get("position_vs_momentum")), _f(eth.get("position_vs_momentum")),
                     _f(btc.get("daily_return_vs_momentum")), _f(eth.get("daily_return_vs_momentum")),
                     _f(btc.get("daily_return_vs_buy_hold")), _f(eth.get("daily_return_vs_buy_hold"))))
    bd, ed = (c.get("BTCUSDT") or {}).get("dev", {}), (c.get("ETHUSDT") or {}).get("dev", {})
    lines.append("With the loop's rule A (to 2025-11-11 only): position BTC %s, ETH %s; daily returns BTC %s, ETH %s." % (
        _f(bd.get("position_vs_rule_A")), _f(ed.get("position_vs_rule_A")), _f(bd.get("daily_return_vs_rule_A")),
        _f(ed.get("daily_return_vs_rule_A"))))
    rows_ = s3["rows"]
    if "a_p3_only" in rows_ and "a_readings_only" in rows_:
        lines.append("Together the readings carry most of the edge: Phase 3 inputs alone give gross Sharpe BTC %.2f, ETH %.2f "
                     "(primary %.2f, %.2f); the readings alone keep BTC %.2f, ETH %.2f." % (
                         rows_["a_p3_only"]["BTCUSDT"]["gross"], rows_["a_p3_only"]["ETHUSDT"]["gross"],
                         s3["primary_gross"]["BTCUSDT"], s3["primary_gross"]["ETHUSDT"],
                         rows_["a_readings_only"]["BTCUSDT"]["gross"], rows_["a_readings_only"]["ETHUSDT"]["gross"]))
    lines.append("Mostly trend-following by the frozen rule: %s (the rule: position correlation with momentum >= 0.5, or "
                 "the trend readings the only group that clears the 0.20 bar)." % ("YES" if s3["mostly_trend"] else "NO"))
    if s3["carries_value"]:
        lines.append("Groups whose removal (retrained) costs >= 0.20 gross Sharpe on BTC and ETH: %s." %
                     ", ".join(GROUP_NAMES.get(g, g) for g in s3["carries_value"]))
    else:
        lines.append("No single reading group clears the frozen bar (dropping it, retrained, costs >= 0.20 gross Sharpe "
                     "on BTC and on ETH).")
    return " ".join(lines)


# ---------------------------------------------------------------- markdown
def p2_table(s2, res):
    rows = ["| Variant | Asset | Gross Sharpe (primary) | Net Sharpe 0.10% (primary) | Turnover/yr (primary) | Trades/yr (primary) "
            "| Keeps edge | Trades less | Beats B&H* | Beats momentum | Edge every seed |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for vn in PART2:
        for a, d in (s2.get(vn) or {}).items():
            j = d["full"]
            rows.append("| %s | %s | %.2f (%.2f) | %.2f (%.2f) | %.0f (%.0f) | %.0f (%.0f) | %s | %s | %s | %s | %s |" % (
                report4.label(vn), a, d["variant"]["gross"], d["primary"]["gross"], d["variant"]["net"], d["primary"]["net"],
                d["variant"]["turnover"], d["primary"]["turnover"], d["variant"]["trades"], d["primary"]["trades"],
                "yes" if d["keeps_edge"] else "no", "yes" if d["trades_less"] else "no", "yes" if j["beats_bh"] else "no",
                "yes" if j["beats_momentum"] else "no", "yes" if j["edge"]["edge_every_seed"] else "no"))
    rows.append("")
    rows.append("Full span 2020-10-01 .. 2026-11-11, seed means, after 0.10% fees. *B&H = perp buy-and-hold; for t3 (a spot "
                "core) spot buy-and-hold. Beats = Phase 4's rule (seed-mean Sharpe and Calmar above, every seed's Sharpe "
                "above).")
    return "\n".join(rows)


def p3_table(s3, res):
    rows = ["| Variant | BTC gross Sharpe (vs primary) | BTC net 0.10% | ETH gross Sharpe (vs primary) | ETH net 0.10% | "
            "BTC turnover/yr | BTC gross to 2025-11-11 | ETH gross to 2025-11-11 |", "|---|---|---|---|---|---|---|---|"]
    pg = s3["primary_gross"]
    rows.append("| **%s** | **%.2f** | **%.2f** | **%.2f** | **%.2f** | **%.0f** | **%.2f** | **%.2f** |" % (
        report4.label(PRIMARY), pg["BTCUSDT"], _st(res, "BTCUSDT", "full", PRIMARY)["sharpe"], pg["ETHUSDT"],
        _st(res, "ETHUSDT", "full", PRIMARY)["sharpe"], _st(res, "BTCUSDT", "full", PRIMARY)["turnover_per_year"],
        _st(res, "BTCUSDT", "dev", PRIMARY)["sharpe_gross"], _st(res, "ETHUSDT", "dev", PRIMARY)["sharpe_gross"]))
    for vn, r in s3["rows"].items():
        b, e = r["BTCUSDT"], r["ETHUSDT"]
        rows.append("| %s | %.2f (%+.2f) | %.2f | %.2f (%+.2f) | %.2f | %.0f | %.2f | %.2f |" % (
            report4.label(vn), b["gross"], b["d_gross"], b["net"], e["gross"], e["d_gross"], e["net"], b["turnover"],
            b["gross_dev"], e["gross_dev"]))
    return "\n".join(rows)


def occ_table(s3):
    rows = ["| Group set to 0 in the trained primary | BTC gross Sharpe (vs primary) | ETH gross Sharpe (vs primary) |",
            "|---|---|---|"]
    for g, d in s3["occlusion"].items():
        rows.append("| %s | %.2f (%+.2f) | %.2f (%+.2f) |" % (GROUP_NAMES.get(g, g), d["BTCUSDT"]["gross"],
                                                            d["BTCUSDT"]["d_gross"], d["ETHUSDT"]["gross"], d["ETHUSDT"]["d_gross"]))
    return "\n".join(rows)


def corr_table(s3):
    rows = ["| Asset | Span | Position vs momentum | Same side as momentum (when in) | Daily return vs momentum | Daily return vs "
            "buy-and-hold | Position vs rule A | Daily return vs rule A | Long / short share |", "|---|---|---|---|---|---|---|---|---|"]
    for a, c in s3["correlations"].items():
        for span in ("full", "dev"):
            o = (c or {}).get(span) or {}
            rows.append("| %s | %s | %s | %s | %s | %s | %s | %s | %.0f%% / %.0f%% |" % (
                a, "2020-10 .. 2026-11" if span == "full" else "to 2025-11-11", _f(o.get("position_vs_momentum")),
                "-" if o.get("same_side_as_momentum_when_in_market") is None else "%.0f%%" % (100 * o["same_side_as_momentum_when_in_market"]),
                _f(o.get("daily_return_vs_momentum")), _f(o.get("daily_return_vs_buy_hold")),
                _f(o.get("position_vs_rule_A")) if span == "dev" else "(not shown: sealed)",
                _f(o.get("daily_return_vs_rule_A")) if span == "dev" else "(not shown: sealed)",
                100 * o.get("long_share", 0), 100 * o.get("short_share", 0)))
    return "\n".join(rows)


def flags_md(res, names):
    v = view(res, names)
    fl = report4.flags(v)
    out = []
    for asset, fa in fl.items():
        ids = [f["id"] for f in next(iter(fa.values()))]
        out.append("**%s**\n" % asset)
        out.append("| Variant | " + " | ".join(ids) + " |\n|---|" + "---|" * len(ids))
        for vn, f in fa.items():
            d = dict((x["id"], x["fired"]) for x in f)
            out.append("| %s | %s |" % (report4.label(vn), " | ".join("FIRED" if d.get(i) else "-" for i in ids)))
        out.append("")
    return "\n".join(out), fl


def markdown(res, s2, s3):
    p5 = res["config"]["phase5"]
    names2 = [PRIMARY] + [n for n in PART2 if n in res["config"]["variants"]]
    names3 = [PRIMARY] + [n for n in p5["ablation"]["variants"] if n in res["config"]["variants"]]
    v2 = view(res, names2)
    L = ["# RL Phase 5 report: trade-less variants and which readings carry the edge", "",
         "Run `%s`, generated %s. Paper only. Parts 2 and 3 of Phase 5 (part 1, the forward paper run, is "
         "`engine15/playbook5.py`; its checks are summarised below). Seeds %s; 15-minute bars and clock; Phase 4's data, "
         "folds, inputs, risk manager, backtester, fees and benchmarks." % (res["run_id"], res["generated_utc"], res["seeds"]),
         "", "**Holdout honesty.** Phase 4 already scored every test window through 2026-11-11, so no historical span is "
         "unseen for RL any more: every number below is in-sample in the sense that matters (the setup was chosen after "
         "looking at these windows). Both spans are shown: 2020-10-01 .. 2026-11-11 and up to 2025-11-11. The strategy "
         "loop's rules A and B (and every comparison with them) stop at 2025-11-11, the start of the loop's sealed year. "
         "The forward paper run is the only real test left.", ""]
    # part 1
    L += ["## Part 1: the forward paper run (checks)", ""]
    rp = res.get("repro")
    if rp:
        L.append("- Phase 4's fold-%d models rebuilt with the export hook: max |W - Phase 4's stored W| = %s per seed and "
                 "coin; exact: %s." % (rp["fold"], ", ".join("%s" % max(v[a] for a in ("BTCUSDT", "ETHUSDT"))
                                                             for v in rp["seeds"].values()), rp["exact"]))
    fc = res.get("forward_check")
    if fc:
        L.append("- Forward step vs Phase 4's batch walk-forward on %s .. %s (%d bars, %d incremental steps, same model and "
                 "bars): decisions identical %s; executed positions max difference %.2e; book equity max difference %.2e; "
                 "values max |W forward - W stored| %.2e." % (fc["start"], fc["end"], fc["bars"], fc["steps"],
                                                              fc["decisions_equal"], fc["exec_max_diff"],
                                                              fc["equity_max_diff"], fc["w_max_diff"]))
    L.append("")
    # part 2
    L += ["## Part 2: trade-less variants (frozen before any result; no retraining)", "",
          "Each variant uses the Phase 4 primary's trained fold models unchanged; only the step from values to positions "
          "differs (configs/rl/phase5.yaml `trade_less`).", "", p2_table(s2, res), ""]
    for asset in res["assets"]:
        L += ["### %s, 2020-10-01 .. 2026-11-11, 0.10%% a side" % asset, "", report4.table(v2, asset, HEAD, "full", PRIMARY), ""]
        L += ["### %s, 2020-10-01 .. 2026-11-11, 0.05%% a side" % asset, "", report4.table(v2, asset, ALT, "full", PRIMARY), ""]
        L += ["### %s, up to 2025-11-11, 0.10%% a side%s" % (asset, " (with the loop's rules A and B)" if asset == "BTCUSDT" else ""),
              "", report4.table(v2, asset, HEAD, "dev", PRIMARY), ""]
    L += ["### By seed (full span): Sharpe / net return / break-even fee", ""]
    for asset in res["assets"]:
        L += ["**%s**" % asset, "", report4.seed_table(v2, asset), ""]
    V = {"assets": dict((a, dict((sp, {"variants": dict((vn, judge(res, a, sp, vn)) for vn in names2)})
                                 for sp in ("full", "dev"))) for a in res["assets"])}
    v2["verdict"] = V
    L += ["### Edge before costs", "", report4.edge_table(v2), "",
          "t (approx.) = gross Sharpe x sqrt(years). For t3 the gross Sharpe includes the 1x spot core.", ""]
    fm, _ = flags_md(res, names2)
    L += ["### Overfitting flags (Phase 4's)", "", fm]
    # part 3
    L += ["### Plain answer (part 2)", ""]
    for vn in PART2:
        d = s2.get(vn) or {}
        if not d:
            continue
        L.append("- %s: %s" % (report4.label(vn), "; ".join(
            "%s gross %.2f (primary %.2f), net %.2f (primary %.2f), turnover %.0f (%.0f): keeps the edge %s, trades less %s, "
            "beats %s %s, beats momentum %s" % (a, x["variant"]["gross"], x["primary"]["gross"], x["variant"]["net"],
                                                x["primary"]["net"], x["variant"]["turnover"], x["primary"]["turnover"],
                                                "yes" if x["keeps_edge"] else "no", "yes" if x["trades_less"] else "no",
                                                "spot B&H" if vn == "t3_tilt" else "B&H", "yes" if x["full"]["beats_bh"] else "no",
                                                "yes" if x["full"]["beats_momentum"] else "no") for a, x in d.items())))
    L.append("")
    L += ["## Part 3: which readings carry the edge (registered; retrained per variant)", "",
          "The Phase 4 primary setup retrained with one input set changed at a time (same folds, seeds, data, selection, "
          "refit, 'do no harm', risk manager). Gross = before every cost. Frozen rule: a group carries independent value if "
          "dropping it costs >= 0.20 gross Sharpe on BTC and on ETH.", ""]
    if s3["rows"]:
        L += [p3_table(s3, res), ""]
        v3 = view(res, names3)
        for asset in res["assets"]:
            L += ["### %s, 2020-10-01 .. 2026-11-11, 0.10%% a side" % asset, "", report4.table(v3, asset, HEAD, "full", PRIMARY), ""]
        fm3, _ = flags_md(res, names3)
        L += ["### Flags (ablations)", "", fm3]
    if s3["occlusion"]:
        L += ["### Occlusion (supplementary, no retraining)", "", "What the TRAINED primary leans on: each group's inputs set to "
              "0 ('nothing to add') in its stored values; a retrained agent may recover some of it from other inputs.", "",
              occ_table(s3), ""]
    L += ["### Correlation with the momentum rule and the loop's rule A", "", corr_table(s3), "",
          "Position = the agent's executed position (mean of seeds, after the risk manager) vs the rule's target, per 15m bar; "
          "daily = correlation of daily net returns. Rule A only up to 2025-11-11.", ""]
    L += ["### Plain answer", "", part3_text(s3, res), ""]
    L += ["## What was frozen, and when", ""]
    for k, v in (p5.get("freeze") or {}).items():
        L.append("- %s: %s" % (k, v))
    if res.get("ablation_training"):
        L.append("- Ablation training: %.0f min, memory pauses: %s" % (res["ablation_training"]["minutes"],
                                                                      res["ablation_training"]["memory_events"] or "none"))
    L.append("- Evaluation: %.0f min, memory pauses: %s" % (res["elapsed_min"], res.get("memory_events") or "none"))
    L += ["", "Machine-readable: `phase5_summary.json`. Nothing here changes the live engine except the forward paper book "
          "(engine15/playbook5.py), which the owner reviews before the loop is restarted."]
    return "\n".join(L) + "\n"


def write(res, out_dir, run_dir=None):
    _labels(res)
    s2, s3 = part2_summary(res), part3_summary(res)
    md = markdown(res, s2, s3)
    summ = {"phase": 5, "paper_only": True, "run_id": res["run_id"], "generated_utc": res["generated_utc"],
            "part2": s2, "part3": s3, "repro": res.get("repro"), "forward_check": res.get("forward_check"),
            "holdout": "no historical span is unseen for RL any more (Phase 4 scored every window to 2026-11-11); loop "
                       "rules A/B and comparisons with them to 2025-11-11 only",
            "headline": dict((a, dict((vn, {"full": dict(row_stats(res["assets"][a]["fees"][HEAD]["variants"][vn])),
                                            "dev": dict(row_stats(res["assets"][a]["fees"][HEAD]["dev"]["variants"][vn]))})
                                      for vn in res["assets"][a]["fees"][HEAD]["variants"])) for a in res["assets"])}
    for d in [out_dir] + ([run_dir] if run_dir else []):
        with open(os.path.join(d, "phase5_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(d, "phase5_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(clean(summ), fh, indent=1, default=float)
    return os.path.join(out_dir, "phase5_report.md")
