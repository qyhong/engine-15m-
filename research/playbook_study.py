# -*- coding: utf-8 -*-
"""History study of the two strategy books in engine15/playbook.py (P1 liquidation hunt, P2 breakout
trap) on all six markets, 2020 to now, after each asset's own costs. PAPER RESEARCH ONLY.

THE PROTOCOL, fixed before the first run:
  * Trades count from 2020-01-01 (2019 is warm-up). History is split at SPLIT (the midpoint of
    2020-01-01 to the end of the data) into a first and a second half, by entry time.
  * The variant grid is small and every variant is counted (the register's luck rule):
      P1 base   k (sweep depth, x ATR15m) in {0.10, 0.25} x m (bars to reclaim) in {0, 2}
                x exit scheme in {struct, fixed}                                  = 8
      P1 confirmations, each alone on the chosen base: volume surge, taker flip (crypto),
                funding extreme (crypto)                                          = 3
      P2 base   level in {48-bar range, prior day, 15m swing} x j in {2, 4} x exit = 12
      P2 filters, each alone on the chosen base: breakout volume low, high; with the
                higher-timeframe bias; against it; London / New York open; shallow  = 6
                                                                             total = 29
    The open-interest / liquidation-proxy confirmation is NOT in the grid: Binance serves about
    30 days of open-interest history, so there is no history to test it on.
  * SELECTION (first half only): the base variant with the highest score = the mean over the
    assets (each with at least 20 first-half trades) of the first-half expectancy after costs
    (% of stake per trade), among variants with at least 100 first-half trades in all. A
    confirmation / filter is adopted only if it lifts that score by at least 0.02 percentage
    points and keeps at least 100 first-half trades (crypto-only ones are scored on BTC and ETH
    against the base on BTC and ETH, and would apply to crypto only).
  * The chosen variant's second half is then reported untouched, per asset and by session.
  * A truncation test: the registered variants re-run on history cut at three points must
    reproduce every trade closed before each cut exactly.

    py -3 research/playbook_study.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, playbook as pb  # noqa: E402

START = "2020-01-01"
SPLIT = "2023-06-07"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
MIN_TRADES_ASSET, MIN_TRADES_ALL, MIN_LIFT = 20, 100, 0.02

P1_BASE = [{"k": k, "m": m, "exit": x, "confirm": None} for k in (0.10, 0.25) for m in (0, 2) for x in ("struct", "fixed")]
P1_EXTRA = ("volume", "taker", "funding")
P2_BASE = [{"level": lv, "j": j, "exit": x, "filter": None} for lv in ("n48", "pday", "swing") for j in (2, 4) for x in ("struct", "fixed")]
P2_EXTRA = ("vol_low", "vol_high", "with_bias", "against_bias", "open_window", "shallow")
CRYPTO_ONLY = ("taker", "funding")


def vname(book, rule):
    if book == "p1_liqhunt":
        return "k%.2f m%d %s%s" % (rule["k"], rule["m"], rule["exit"], "" if not rule["confirm"] else " +" + rule["confirm"])
    return "%s j%d %s%s" % (rule["level"], rule["j"], rule["exit"], "" if not rule["filter"] else " +" + rule["filter"])


def metrics(trades, months):
    n = len(trades)
    if not n:
        return {"trades": 0}
    net = np.array([t["pnl_usd"] for t in trades])
    gross = np.array([t["gross_usd"] for t in trades])
    rr = np.array([t["r"] for t in trades])
    eq = np.cumsum(net)
    dd = float((np.maximum.accumulate(np.concatenate([[0.0], eq])) - np.concatenate([[0.0], eq])).max())
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    return {"trades": n, "win_pct": round(100.0 * (net > 0).mean(), 1), "avg_r": round(float(rr.mean()), 3),
            "pf": round(float(pos / neg), 2) if neg > 0 else None,
            "exp_pct": round(float(net.mean() / pb.STAKE * 100), 4), "gross_exp_pct": round(float(gross.mean() / pb.STAKE * 100), 4),
            "net_usd": round(float(net.sum()), 2), "fees_usd": round(float(sum(t["fees_usd"] for t in trades)), 2),
            "max_dd_usd": round(dd, 2), "per_month": round(n / months, 1),
            "median_risk_pct": round(float(np.median([t["risk"] / t["entry"] * 100 for t in trades])), 3)}


def split(trades, start_ms, split_ms):
    cl = [t for t in trades if t["status"] == "CLOSED" and t["entry_ms"] >= start_ms]
    return [t for t in cl if t["entry_ms"] < split_ms], [t for t in cl if t["entry_ms"] >= split_ms]


def score(res, book, vn, assets):
    """Mean first-half expectancy over the assets with enough trades; total first-half trades."""
    vals, tot = [], 0
    for a in assets:
        m = res[a][book][vn]["first"]
        tot += m["trades"]
        if m["trades"] >= MIN_TRADES_ASSET:
            vals.append(m["exp_pct"])
    return (float(np.mean(vals)) if vals else -99.0), tot


def truncation_test(df, asset, cuts):
    full_P = pb.prepare(df, asset)
    bad, checked = 0, 0
    full = dict((b, pb.run(b, full_P)) for b in pb.BOOKS)
    for cut in cuts:
        sub = df[df.index < cut]
        P = pb.prepare(sub, asset)
        for b in pb.BOOKS:
            want = set((t["entry_ms"], t["exit_ms"], round(t["r"], 9)) for t in full[b] if t["status"] == "CLOSED")
            for t in pb.run(b, P):
                if t["status"] == "CLOSED":
                    checked += 1
                    bad += (t["entry_ms"], t["exit_ms"], round(t["r"], 9)) not in want
    return {"checked": checked, "mismatched": bad}


def main():
    t0 = time.time()
    start_ms = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    split_ms = int(pd.Timestamp(SPLIT, tz="UTC").value // 10**6)
    res, trades_keep, months, spans = {}, {}, {}, {}
    variants = {"p1_liqhunt": list(P1_BASE) + [dict(P1_BASE[0], confirm=c) for c in P1_EXTRA],
                "p2_trap": list(P2_BASE) + [dict(P2_BASE[0], filter=f) for f in P2_EXTRA]}
    # pass 1: the base grids (extras are run once a base is chosen)
    for asset in pb.ASSETS:
        df = data.load(asset)
        P = pb.prepare(df, asset)
        last = int(P["ms"][-1])
        months[asset] = ((split_ms - max(start_ms, int(P["ms"][0]))) / (30.44 * 86400000), (last - split_ms) / (30.44 * 86400000))
        spans[asset] = (str(df.index[0])[:10], str(df.index[-1])[:16])
        res[asset] = {"p1_liqhunt": {}, "p2_trap": {}}
        for book, grid in (("p1_liqhunt", P1_BASE), ("p2_trap", P2_BASE)):
            for rule in grid:
                tr = pb.simulate(P, pb.signals(book, P, rule), rule["exit"], pb.HOLD[book], pb.fee_side(asset))
                f, s = split(tr, start_ms, split_ms)
                res[asset][book][vname(book, rule)] = {"first": metrics(f, months[asset][0]), "second": metrics(s, months[asset][1])}
        print("%s base grid done (%.0fs)" % (asset, time.time() - t0), flush=True)
        del P, df
    chosen = {}
    for book, grid in (("p1_liqhunt", P1_BASE), ("p2_trap", P2_BASE)):
        scored = [(score(res, book, vname(book, r), pb.ASSETS), r) for r in grid]
        ok = [(sc, r) for (sc, tot), r in scored if tot >= MIN_TRADES_ALL]
        chosen[book] = max(ok, key=lambda x: x[0])[1]
    # pass 2: the extras on the chosen base, and the chosen variants' trades
    extras = {"p1_liqhunt": [dict(chosen["p1_liqhunt"], confirm=c) for c in P1_EXTRA],
              "p2_trap": [dict(chosen["p2_trap"], filter=f) for f in P2_EXTRA]}
    variants = {b: [r for r in (P1_BASE if b == "p1_liqhunt" else P2_BASE)] + extras[b] for b in pb.BOOKS}
    for asset in pb.ASSETS:
        df = data.load(asset)
        P = pb.prepare(df, asset)
        for book in pb.BOOKS:
            for rule in extras[book]:
                tr = pb.simulate(P, pb.signals(book, P, rule), rule["exit"], pb.HOLD[book], pb.fee_side(asset))
                f, s = split(tr, start_ms, split_ms)
                res[asset][book][vname(book, rule)] = {"first": metrics(f, months[asset][0]), "second": metrics(s, months[asset][1])}
        print("%s extras done (%.0fs)" % (asset, time.time() - t0), flush=True)
        del P, df
    registered = {}
    for book in pb.BOOKS:
        base = chosen[book]
        key = "confirm" if book == "p1_liqhunt" else "filter"
        best, best_lift = None, MIN_LIFT
        for rule in extras[book]:
            scope = pb.CFG["crypto"] if rule[key] in CRYPTO_ONLY else pb.ASSETS
            b_sc, _ = score(res, book, vname(book, base), scope)
            sc, tot = score(res, book, vname(book, rule), scope)
            if tot >= MIN_TRADES_ALL and sc - b_sc >= best_lift:
                best, best_lift = rule, sc - b_sc
        registered[book] = best or base
    # pass 3: the registered variants in detail (sessions, pools, exits) and the truncation test
    detail, trunc = {}, {}
    for asset in pb.ASSETS:
        df = data.load(asset)
        P = pb.prepare(df, asset)
        detail[asset] = {}
        for book in pb.BOOKS:
            rule = registered[book]
            tr = pb.simulate(P, pb.signals(book, P, rule), rule["exit"], pb.HOLD[book], pb.fee_side(asset))
            f, s = split(tr, start_ms, split_ms)
            d = {"sessions": {}, "pools": {}, "exits": {}}
            for half, ts, mo in (("first", f, months[asset][0]), ("second", s, months[asset][1])):
                for sess in ("Asia", "London", "New York", "Late"):
                    d["sessions"].setdefault(sess, {})[half] = metrics([t for t in ts if pb._session_word(t["entry_ms"]) == sess], mo)
                for pool in sorted(set(t["pool"] for t in f + s)):
                    d["pools"].setdefault(pool, {})[half] = metrics([t for t in ts if t["pool"] == pool], mo)
                d["exits"][half] = dict((w, sum(1 for t in ts if t["why_out"] == w)) for w in ("STOP", "T2", "TIME"))
                d["exits"][half]["t1_hit"] = sum(1 for t in ts if t.get("t1_hit"))
            detail[asset][book] = d
        cut_base = df.index[-1]
        cuts = [cut_base - pd.Timedelta(days=dd) for dd in (400, 120, 9)]
        sub = df[df.index >= cut_base - pd.Timedelta(days=700)]
        # truncation uses the live rule set: run with the registered rules
        saved = dict(pb.RULES)
        pb.RULES.update(registered)
        trunc[asset] = truncation_test(sub, asset, cuts)
        pb.RULES.clear()
        pb.RULES.update(saved)
        print("%s detail done (%.0fs)" % (asset, time.time() - t0), flush=True)
        del P, df
    out = {"protocol": {"start": START, "split": SPLIT, "variants_tried": sum(len(v) for v in variants.values()),
                        "variants_by_book": dict((b, len(v)) for b, v in variants.items()),
                        "min_trades_asset": MIN_TRADES_ASSET, "min_trades_all": MIN_TRADES_ALL, "min_lift_pct": MIN_LIFT},
           "spans": spans, "chosen_base": dict((b, vname(b, r)) for b, r in chosen.items()),
           "registered": dict((b, dict(r, name=vname(b, r))) for b, r in registered.items()),
           "scores_first_half": dict((b, dict((vname(b, r), round(score(res, b, vname(b, r),
                                                                         pb.CFG["crypto"] if (r.get("confirm") or r.get("filter")) in CRYPTO_ONLY else pb.ASSETS)[0], 4))
                                              for r in variants[b])) for b in pb.BOOKS),
           "results": res, "registered_detail": detail, "truncation": trunc}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "playbook.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    write_md(out, variants)
    print("done in %.0fs" % (time.time() - t0))


def _m(m, keys=("trades", "win_pct", "avg_r", "pf", "exp_pct", "gross_exp_pct", "max_dd_usd", "per_month")):
    if not m or not m.get("trades"):
        return " | ".join(["0"] + ["-"] * (len(keys) - 1))
    return " | ".join("-" if m.get(k) is None else ("%s" % m[k]) for k in keys)


def write_md(out, variants):
    L = ["# Strategy books P1 and P2: history study", "",
         "Generated by `research/playbook_study.py`. Paper research only. History can reject a rule, never prove one.", "",
         "Trades from %s; first half before %s, second half after (by entry time). Costs per side: crypto 0.10%%, gold 0.02%%, "
         "silver 0.03%%, USDJPY 0.01%%, S&P 500 0.02%%. $10,000 per trade. **Variants tried: %d** (P1 %d, P2 %d)." % (
             out["protocol"]["start"], out["protocol"]["split"], out["protocol"]["variants_tried"],
             out["protocol"]["variants_by_book"]["p1_liqhunt"], out["protocol"]["variants_by_book"]["p2_trap"]), "",
         "Columns: trades, win %, average R after costs, profit factor, expectancy after costs (% of stake per trade), "
         "expectancy before costs, max drawdown ($, trades at $10,000), trades per month.", ""]
    for book in pb.BOOKS:
        reg = out["registered"][book]
        L += ["## %s (%s)" % (pb.BOOKS[book]["title"], pb.BOOKS[book]["hypothesis"]), "",
              "Chosen base on the first half: `%s`. Registered: **`%s`**." % (out["chosen_base"][book], reg["name"]), "",
              "### Every variant, first half only (the selection score is the mean over assets of expectancy after costs)", "",
              "| variant | score % | trades (all assets) |", "|---|---|---|"]
        for r in variants[book]:
            vn = vname(book, r)
            tot = sum(out["results"][a][book][vn]["first"].get("trades", 0) for a in pb.ASSETS)
            L.append("| %s | %s | %d |" % (vn, out["scores_first_half"][book][vn], tot))
        L += ["", "### Registered variant, per asset", "",
              "| asset | half | trades | win % | avg R | PF | exp % | gross exp % | max DD $ | per month |", "|---|---|---|---|---|---|---|---|---|---|"]
        for a in pb.ASSETS:
            for half in ("first", "second"):
                L.append("| %s | %s | %s |" % (pb.SHORT_NAME[a], half, _m(out["results"][a][book][reg["name"]][half])))
        L += ["", "### Registered variant by session (UTC entry hour: Asia 00-07, London 07-13, New York 13-20, Late 20-24), all assets pooled by trade", "",
              "| session | half | trades | win % | exp % (trade-weighted) |", "|---|---|---|---|---|"]
        for sess in ("Asia", "London", "New York", "Late"):
            for half in ("first", "second"):
                n = w = e = 0.0
                for a in pb.ASSETS:
                    m = out["registered_detail"][a][book]["sessions"][sess][half]
                    if m.get("trades"):
                        n += m["trades"]
                        w += m["win_pct"] * m["trades"]
                        e += m["exp_pct"] * m["trades"]
                L.append("| %s | %s | %d | %s | %s |" % (sess, half, n, "-" if not n else round(w / n, 1), "-" if not n else round(e / n, 4)))
        L += ["", "### Registered variant by pool / level (descriptive only, not used to choose)", "",
              "| pool | half | trades | exp % (trade-weighted, all assets) |", "|---|---|---|---|"]
        pools = sorted(set(p for a in pb.ASSETS for p in out["registered_detail"][a][book]["pools"]))
        for p in pools:
            for half in ("first", "second"):
                n = e = 0.0
                for a in pb.ASSETS:
                    m = out["registered_detail"][a][book]["pools"].get(p, {}).get(half, {})
                    if m.get("trades"):
                        n += m["trades"]
                        e += m["exp_pct"] * m["trades"]
                L.append("| %s | %s | %d | %s |" % (p, half, n, "-" if not n else round(e / n, 4)))
        L.append("")
    L += ["## Truncation test", "", "Registered rules re-run on history cut 400, 120 and 9 days before the end; every trade closed "
          "before a cut must match the full run exactly.", "", "| asset | closed trades checked | mismatched |", "|---|---|---|"]
    for a in pb.ASSETS:
        t = out["truncation"][a]
        L.append("| %s | %d | %d |" % (pb.SHORT_NAME[a], t["checked"], t["mismatched"]))
    with open(os.path.join(OUT, "playbook.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
