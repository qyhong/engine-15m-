# -*- coding: utf-8 -*-
"""H71: write research/out/h71_voices_at_rebounds/report.md from the stage JSON files (formatting only)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "research", "out", "h71_voices_at_rebounds")


def load(name):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


def f(v, pat="%+.3f"):
    return "-" if v is None else pat % v


def ic(c):
    if not c or not c.get("n"):
        return "-"
    return "%s [%s, %s]" % (f(c["ic"]), f(c.get("lo")), f(c.get("hi")))


def ic_table(L, R, state):
    L.append("| Reading | 24h partial BTC | 24h partial ETH | 24h partial pooled [95%] | 24h raw pooled | 4h partial pooled | 4h raw pooled |")
    L.append("|---|---|---|---|---|---|---|")
    for r, v in R.items():
        s = v[state]
        L.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (
            r, f(s["partial_24h"]["BTC"].get("ic")), f(s["partial_24h"]["ETH"].get("ic")), ic(s["partial_24h"].get("pooled")),
            ic(s["raw_24h"].get("pooled")), ic(s["partial_4h"].get("pooled")), ic(s["raw_4h"].get("pooled"))))


def hits(L, R):
    L.append("| Reading | BTC base / top third / bottom third (%) | ETH base / top / bottom (%) |")
    L.append("|---|---|---|")
    for r, v in R.items():
        h = v["hits"]
        L.append("| `%s` | %s / %s / %s | %s / %s / %s |" % (
            r, f(h["BTC"]["base_pct"], "%.1f"), f(h["BTC"]["top_pct"], "%.1f"), f(h["BTC"]["bottom_pct"], "%.1f"),
            f(h["ETH"]["base_pct"], "%.1f"), f(h["ETH"]["top_pct"], "%.1f"), f(h["ETH"]["bottom_pct"], "%.1f")))


def readout(L, ro):
    L.append("| Bias | Lead bucket | bars | share of state | months | mean fwd 24h % | median fwd 24h % | rebound +5% rate |")
    L.append("|---|---|---|---|---|---|---|---|")
    for b in ("all", "bias down", "bias not down"):
        for k in ("all", "up 5+", "up 15+", "between", "down 5+"):
            c = ro[b][k]
            if not c.get("n"):
                L.append("| %s | %s | 0 | | | | | |" % (b, k))
                continue
            L.append("| %s | %s | %d | %.1f%% | %d | %+.2f | %+.2f | %.1f%% |" % (
                b, k, c["n"], c["share_pct"], c["months"], c["mean_fwd_pct"], c["median_fwd_pct"], c["rebound_pct"]))


def counts(L, C):
    for a, c in C.items():
        L.append("- %s: %d bars %s to %s; states %s; oversold months %d; sharp-rebound base rate oversold %.1f%%, calm %.1f%%" % (
            a, c["bars"], c["from"], c["to"], c["states"], c["oversold_months"], c["oversold_rebound_base_pct"] or 0,
            c["calm_rebound_base_pct"] or 0))


def main():
    L = ["# H71 report: the engine's own odds, voices and readings in BTC/ETH oversold states", "",
         "Written by `research/h71_report.py` from the stage files computed by `research/h71_voices_at_rebounds.py` "
         "(registered in `research/HYPOTHESES.md`, H71). IC = Spearman rank correlation with the forward log return; "
         "partial = after removing trailing 1h/4h/24h/7d returns and 24h volatility; intervals are month-clustered "
         "bootstrap 95% (4,000 draws, seed 20261122).", ""]
    D = load("discovery.json")
    if D:
        L += ["## Discovery (%s)" % D["meta"]["cut"], "", "Walk: %d refits, %d from the cache; EMA gap source %s." % (
            D["meta"]["refits"], D["meta"]["reused"], D["meta"]["ema_gap_source"]), ""]
        counts(L, D["counts"])
        L += ["", "### Oversold state", ""]
        ic_table(L, D["readings"], "oversold")
        L += ["", "Selection checks (same sign BTC/ETH; pooled interval excludes 0; |pooled| >= 0.02):", ""]
        for r, v in D["readings"].items():
            L.append("- `%s`: %s" % (r, v["selection_check"]))
        L += ["", "Qualified: %s" % (D["qualified"] or "none"), "", "### Sharp-rebound hit rates (oversold, descriptive)", ""]
        hits(L, D["readings"])
        L += ["", "### Calm state (contrast)", ""]
        ic_table(L, D["readings"], "calm")
        L += ["", "### Descriptive read-out: the combined odds in the oversold state", ""]
        readout(L, D["readout"])
    S = load("selection.json")
    if S:
        L += ["", "## Selection", "", "```", json.dumps(S, indent=1), "```"]
    RC = load("readout_confirmation.json")
    if RC:
        L += ["", "## Descriptive read-out, confirmation period (%s; lead buckets only)" % RC["meta"]["cut"], ""]
        counts(L, RC["counts"])
        L.append("")
        readout(L, RC["readout"])
    for st in ("confirmation", "holdout"):
        C = load(st + ".json")
        if not C:
            continue
        L += ["", "## %s" % st.capitalize(), ""]
        if C.get("not_opened"):
            L.append("Not opened: %s." % C["why"])
            continue
        L.append("Cut %s." % C["meta"]["cut"])
        counts(L, C["counts"])
        L.append("")
        ic_table(L, C["readings"], "oversold")
        L.append("")
        for r, v in C["readings"].items():
            L.append("- `%s`: %s" % (r, v["test"]))
        L.append("")
        hits(L, C["readings"])
        if "readout" in C:
            L += ["", "### Descriptive read-out (confirmation period)", ""]
            readout(L, C["readout"])
        if st == "holdout":
            L += ["", "One year is short: a holdout this size can confirm or contradict only a large effect."]
    open(os.path.join(OUT, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
