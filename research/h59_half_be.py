# -*- coding: utf-8 -*-
"""H59: half at Target 1 + stop to entry on the rest (`half_be_t1`), on the main book's own entries, in H36's
frame (research/HYPOTHESES.md, H59). PAPER ONLY. IN-SAMPLE. Gates nothing: the owner adopted the rule for the
S&P 500 main book before this read.

    python research/h59_half_be.py --group index --window h36     one group, cut at H36's last stored session
    python research/h59_half_be.py --group index --window today   one group, to the store's last session
    python research/h59_half_be.py --report                       merge, write research/out/h59_half_be/report.md + results.json

Everything that forms the odds and runs the books is research/exit_study.py's (prep, run_book, seg_stats, daily,
max_dd, sharpe), so `main` and `be_t1` here must reproduce H36's per-market lines over H36's window. The only
addition to exit_study.prep_readonly is the cut: every per-row input (readings, features, ready flags, bars, labels)
is truncated to the sessions up to the cut BEFORE labels and the walk are formed, exactly as if the store had ended
there. H36's own outputs in research/out/exits/ are never written; refits are cached in this study's own folder.
"""
import argparse
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import exit_study as ex  # noqa: E402
from engine15 import data, evcache, labels, leanprep, model, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h59_half_be")
START = shadows.START_EQUITY
RULES = {"be_t1": {"be_t1": True}, "half_be_t1": {"half_t1": True, "be_t1": True}}
BOOKS = ["main", "b_targets", "be_t1", "half_be_t1"]
NEW = "half_be_t1"
# H36's last stored session per group (research/out/exits/trail_study.md, per-market headings)
H36_END = {"crypto": "2026-11-13 04:00", "metals": "2026-11-13 03:30", "fx": "2026-11-13 03:45",
           "index": "2026-11-12 20:45", "energy": "2026-11-13 03:30"}
# H36's per-market lines (trail_study.md) for the reconciliation: (net P&L $, trades)
H36_REF = {
    "BTCUSDT": {"main": (-2649, 317), "be_t1": (-1750, 398), "b_targets": (-9583, 1128)},
    "ETHUSDT": {"main": (266807, 237), "be_t1": (53596, 344), "b_targets": (-6380, 1043)},
    "XAUUSD": {"main": (17712, 134), "be_t1": (13945, 170), "b_targets": (-4105, 749)},
    "XAGUSD": {"main": (-796, 161), "be_t1": (-1387, 212), "b_targets": (-7871, 737)},
    "USDJPY": {"main": (19209, 120), "be_t1": (27238, 145), "b_targets": (2939, 744)},
    "SPX": {"main": (6816, 36), "be_t1": (6334, 42), "b_targets": (1018, 237)},
    "WTI": {"main": (13328, 156), "be_t1": (9346, 215), "b_targets": (-3184, 752)},
    "BRENT": {"main": (9012, 161), "be_t1": (354, 238), "b_targets": (-1695, 731)},
}
H36_POOLED = {"main": 329439, "be_t1": 107673, "b_targets": -28862}
ORDER = ["SPX", "BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "WTI", "BRENT"]


def prep_cut(group, assets, fits_dir, end=None, log=print):
    """exit_study.prep_readonly with every per-row input truncated at `end` (inclusive) first."""
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    ns = set(st.meta["n"] for st in stores.values())
    if len(ns) != 1:
        raise RuntimeError("stores of %s disagree on rows: %s" % (group, ns))
    full = pd.DatetimeIndex(pd.to_datetime(stores[assets[0]].times_ms(), unit="ms", utc=True))
    for a in assets[1:]:
        assert np.array_equal(stores[a].times_ms(), stores[assets[0]].times_ms())
    n = len(full) if end is None else int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
    if end is not None and str(full[n - 1])[:16] != end:
        raise RuntimeError("%s: the store has no session at %s (last <= it: %s)" % (group, end, full[n - 1]))
    times = full[:n]
    cfg = dict(CFG, assets=tuple(assets), birth=CFG["birth"], voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        ev[a] = st.frame(full).iloc[:n]
        X[a] = st.X()[:n]
        ready[a] = st.ready()[:n]
        b = data.load(a).reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    t0 = time.time()
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n,
                                                       fits_dir)
    log("%s: %d sessions to %s; voices walked from %s: %d refits, %d from the cache (%.0fs)" % (
        group, n, str(times[-1])[:16], cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    del models
    lo = birth_idx
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    odds = {}
    for a in assets:
        Xa = np.asarray(X[a][lo:n])
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        del Xa
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        del speaks, w
        probs[a] = None
    del probs, trust, X
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds,
            "birth_idx": birth_idx}


def run_book(name, prep, a, lo, n, aux):
    if name in shadows.CHALLENGERS:                       # main, b_targets: exactly exit_study's path
        return ex.run_book(name, prep, a, lo, n, aux)
    cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    inp = shadows.book_inputs(prep, a)
    tgt = aux["targets"]
    return shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                       bias=inp["bias"], guard=inp["guard"], rule=dict(RULES[name]), aux=aux,
                       times_ms=data.to_ms(prep["times"]),
                       row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))


def run_group(g, assets, window, fits_root, mid, log=print):
    t0 = time.time()
    prep = prep_cut(g, assets, os.path.join(fits_root, g), H36_END[g] if window == "h36" else None, log=log)
    times = prep["times"]
    n = len(times)
    mid_ts = pd.Timestamp(mid, tz="UTC")
    out = {"group": g, "window_kind": window, "assets": {}, "curves": {}}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        mid_i = min(max(int(times.searchsorted(mid_ts)), lo + 1), n - 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        c, o = prep["px"][a]["close"], prep["px"][a]["open"]
        fee = shadows.asset_cfg(a, prep["cfg"])["cost_side"]
        res = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid_i])[:16],
               "fee_side": fee, "buy_hold_return_pct": round(float(c[n - 1] / o[lo] * (1 - 2 * fee) - 1) * 100, 2),
               "books": {}}
        curves = {}
        for name in BOOKS:
            b = run_book(name, prep, a, lo, n, aux)
            eq, tr = b["equity"], b["trades"]
            base_mid = eq[mid_i - 1] if np.isfinite(eq[mid_i - 1]) else START
            st = b["state"]
            res["books"][name] = {"all": ex.seg_stats(eq, tr, times, lo, n, START),
                                  "first_half": ex.seg_stats(eq, tr[tr.i_out < mid_i], times, lo, mid_i, START),
                                  "second_half": ex.seg_stats(eq, tr[tr.i_out >= mid_i], times, mid_i, n, base_mid),
                                  "exits": dict((str(k), int(v)) for k, v in tr.why_out.value_counts().items()),
                                  "open_at_end": {1: "LONG", -1: "SHORT"}.get(st["pos"], "FLAT"),
                                  "open_t1_hit": bool(st.get("t1_hit")) if st["pos"] else None}
            cv = ex.daily(eq, times, lo, n)
            curves[name] = {"t": [str(x)[:10] for x in cv.index], "eq": [round(float(x), 2) for x in cv.values]}
        out["assets"][a] = res
        out["curves"][a] = curves
        m, h = res["books"]["main"]["all"], res["books"][NEW]["all"]
        log("%s %s: %s .. %s, main %+.0f (%d), be_t1 %+.0f, half_be_t1 %+.0f (%d) (%.0fs)" % (
            g, a, res["window"][0], res["window"][1], m.get("pnl_usd", 0), m.get("trades", 0),
            res["books"]["be_t1"]["all"].get("pnl_usd", 0), h.get("pnl_usd", 0), h.get("trades", 0), time.time() - t0))
        gc.collect()
    del prep
    gc.collect()
    return out


# =====================================================================================
# the report
# =====================================================================================
def pooled(groups, mid):
    frames = {}
    for g in groups.values():
        for a, cv in g["curves"].items():
            for name, s in cv.items():
                frames[(a, name)] = pd.Series(s["eq"], index=pd.to_datetime(s["t"]))
    frame = pd.concat(frames, axis=1).sort_index().ffill().fillna(START)
    assets = sorted(set(k[0] for k in frame.columns))
    mid_t = pd.Timestamp(mid)
    out = {}
    for name in BOOKS:
        tot = frame[[(a, name) for a in assets]].sum(axis=1)
        base = START * len(assets)
        first = tot[tot.index < mid_t]
        b_mid = float(first.iloc[-1]) if len(first) else base
        out[name] = {"assets": len(assets), "pnl_usd": round(float(tot.iloc[-1] - base), 2),
                     "return_pct": round(float(tot.iloc[-1] / base - 1) * 100, 2),
                     "sharpe": ex.sharpe(pd.concat([pd.Series([base], index=[tot.index[0] - pd.Timedelta(days=1)]), tot])),
                     "max_dd_pct": ex.max_dd(np.concatenate([[base], tot.values])),
                     "first_half_usd": round(b_mid - base, 2), "second_half_usd": round(float(tot.iloc[-1]) - b_mid, 2)}
    return out


def summarize(groups, mid):
    pool = pooled(groups, mid)
    per = dict((a, r) for g in groups.values() for a, r in g["assets"].items())
    m = pool["main"]
    for name in BOOKS:
        p = pool[name]
        beats = [a for a, r in per.items()
                 if r["books"][name]["all"].get("pnl_usd", 0) > r["books"]["main"]["all"].get("pnl_usd", 0)]
        g1, g2 = p["first_half_usd"] - m["first_half_usd"], p["second_half_usd"] - m["second_half_usd"]
        p.update(vs_main_usd=round(p["pnl_usd"] - m["pnl_usd"], 2), gap_first_half=round(g1, 2),
                 gap_second_half=round(g2, 2), markets_beating_main=beats,
                 trades=sum(r["books"][name]["all"].get("trades", 0) for r in per.values()),
                 better_than_hold=None if name == "main" else bool(
                     g1 > 0 and g2 > 0 and len(beats) >= 5 and (p["max_dd_pct"] or 0) >= (m["max_dd_pct"] or 0)))
    return pool, per


def reconcile(per):
    rows, worst = [], 0.0
    for a in ORDER:
        if a not in per:
            continue
        for name in ("main", "be_t1", "b_targets"):
            s = per[a]["books"][name]["all"]
            ref = H36_REF[a][name]
            d = s.get("pnl_usd", 0) - ref[0]
            dt = s.get("trades", 0) - ref[1]
            worst = max(worst, 1.0 if (abs(d) >= 1 or dt != 0) else 0.0)
            rows.append({"asset": a, "book": name, "h36_pnl": ref[0], "pnl": round(s.get("pnl_usd", 0)),
                         "diff_usd": round(d, 2), "h36_trades": ref[1], "trades": s.get("trades", 0), "diff_trades": dt})
    return rows, worst == 0


def _f(v, pat="%+.0f"):
    return "-" if v is None else pat % v


def market_table(r, L):
    mn = r["books"]["main"]["all"]
    L += ["| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | "
          "2nd half | Exits | Open at end |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in BOOKS:
        b = r["books"][name]
        s, h1, h2 = b["all"], b["first_half"], b["second_half"]
        ex_ = ", ".join("%s %d" % kv for kv in sorted(b["exits"].items(), key=lambda kv: -kv[1]))
        L.append("| `%s` | $%s | $%s | %s%% | %s | %s%% | %s | %s%% | $%s | $%s | $%s | $%s | %s | %s |" % (
            name, _f(s.get("pnl_usd")), _f(s.get("pnl_usd", 0) - mn.get("pnl_usd", 0)), _f(s.get("return_pct"), "%+.1f"),
            _f(s.get("sharpe"), "%.2f"), _f(s.get("max_dd_pct"), "%.1f"), s.get("trades"),
            _f(s.get("win_rate_pct"), "%.0f"), _f(s.get("avg_win_usd")), _f(s.get("avg_loss_usd")),
            _f(h1.get("pnl_usd")), _f(h2.get("pnl_usd")), ex_,
            b["open_at_end"] + (" (T1 hit)" if b.get("open_t1_hit") else "")))
    L.append("")


def section(kind, groups, mid, L, res):
    pool, per = summarize(groups, mid)
    rec, clean = reconcile(per) if kind == "h36" else ([], None)
    res[kind] = {"pooled": pool, "per_market": per, "reconcile": rec, "reproduced_h36": clean}
    title = {"h36": "H36's window (each market's start to H36's last stored session, 12/13 Nov 2026)",
             "today": "To the store's last session (H36's frame, longer window)"}[kind]
    L += ["## %s" % title, ""]
    if kind == "h36":
        L += ["**Reconciliation with H36** (`main`, `be_t1`, `b_targets` per market, net P&L and trades): %s" % (
            "**reproduced exactly** (every line within $1 and the same trade count)." if clean else
            "**NOT exact**; differences below."), "",
              "| Market | Book | H36 net | Here | Diff $ | H36 trades | Here | Diff |", "|---|---|---|---|---|---|---|---|"]
        for x in rec:
            L.append("| %s | `%s` | $%+d | $%+d | %+.2f | %d | %d | %+d |" % (
                x["asset"], x["book"], x["h36_pnl"], x["pnl"], x["diff_usd"], x["h36_trades"], x["trades"], x["diff_trades"]))
        L.append("")
    if "SPX" in per:
        r = per["SPX"]
        L += ["### S&P 500 (SPX) first: %s to %s UTC, buy and hold %+.2f%%, fee %.3f%% a side" % (
            r["window"][0], r["window"][1], r["buy_hold_return_pct"], 100 * r["fee_side"]), ""]
        market_table(r, L)
    L += ["### All eight markets together", "",
          "| Book | Net P&L | Return | vs main | Sharpe | Max DD | 1st half | 2nd half | 1st half vs main | "
          "2nd half vs main | Markets beating main | Trades | Better than hold? |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in BOOKS:
        s = pool[name]
        L.append("| `%s` | $%s | %+.2f%% | $%s | %s | %.2f%% | $%s | $%s | $%s | $%s | %d/%d | %d | %s |" % (
            name, _f(s["pnl_usd"]), s["return_pct"], _f(s["vs_main_usd"]), _f(s["sharpe"], "%.2f"), s["max_dd_pct"],
            _f(s["first_half_usd"]), _f(s["second_half_usd"]), _f(s["gap_first_half"]), _f(s["gap_second_half"]),
            len(s["markets_beating_main"]), s["assets"], s["trades"],
            "-" if s["better_than_hold"] is None else ("yes" if s["better_than_hold"] else "no")))
    s = pool[NEW]
    L += ["", "`half_be_t1` against the registered test: 1st half vs main $%s (%s), 2nd half vs main $%s (%s), ahead of "
          "main in %d of 8 markets (%s; needs 5), pooled max DD %.2f%% vs main %.2f%% (%s). **Better than holding: %s.**" % (
              _f(s["gap_first_half"]), "pass" if s["gap_first_half"] > 0 else "fail",
              _f(s["gap_second_half"]), "pass" if s["gap_second_half"] > 0 else "fail",
              len(s["markets_beating_main"]), ", ".join(s["markets_beating_main"]) or "none",
              s["max_dd_pct"], pool["main"]["max_dd_pct"],
              "pass" if (s["max_dd_pct"] or 0) >= (pool["main"]["max_dd_pct"] or 0) else "fail",
              "YES" if s["better_than_hold"] else "NO"), ""]
    L += ["### Net P&L by market (whole window)", "",
          "| Market | main | be_t1 | b_targets | half_be_t1 | half_be_t1 vs main | half_be_t1 vs be_t1 | half_be_t1 1st / 2nd half | "
          "main 1st / 2nd half | DD main / half_be_t1 | Trades main / half_be_t1 | Win main / half_be_t1 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ORDER:
        if a not in per:
            continue
        B = per[a]["books"]
        g = lambda k, f="pnl_usd", part="all": B[k][part].get(f)  # noqa: E731
        L.append("| %s | $%s | $%s | $%s | $%s | $%s | $%s | $%s / $%s | $%s / $%s | %s%% / %s%% | %s / %s | %s%% / %s%% |" % (
            a, _f(g("main")), _f(g("be_t1")), _f(g("b_targets")), _f(g(NEW)), _f(g(NEW) - g("main")),
            _f(g(NEW) - g("be_t1")), _f(g(NEW, part="first_half")), _f(g(NEW, part="second_half")),
            _f(g("main", part="first_half")), _f(g("main", part="second_half")),
            _f(g("main", "max_dd_pct"), "%.1f"), _f(g(NEW, "max_dd_pct"), "%.1f"), g("main", "trades"), g(NEW, "trades"),
            _f(g("main", "win_rate_pct"), "%.0f"), _f(g(NEW, "win_rate_pct"), "%.0f")))
    L += ["", "### Per market, every book", ""]
    for a in ORDER:
        if a in per and a != "SPX":
            r = per[a]
            L += ["#### %s: %s to %s UTC, buy and hold %+.2f%%" % (a, r["window"][0], r["window"][1],
                                                                   r["buy_hold_return_pct"]), ""]
            market_table(r, L)


def report(args, log=print):
    L = ["# H59: half at Target 1 + stop to entry on the rest, on the main book's own entries (IN-SAMPLE, not proof)", "",
         "Written by `research/h59_half_be.py` on %s. H36's frame in every respect (v5.1 odds as the live step formed "
         "them before the v5.2 trust cap, voices walked weekly from 2020-01-01, the main book's entries, sizing, fees, "
         "protective stop, flips and mandate; $10,000 per market; halves split at %s). Only the exit differs. Paper only." % (
             time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), args.mid), "",
         "**Read this plainly:** descriptive and in-sample, on history the project has already read (H36, 13 Nov). "
         "`half_be_t1` = `{\"half_t1\": true, \"be_t1\": true}` is the 16th exit variant counted on these entries, chosen "
         "after H36's results and after the owner had adopted the rule for the S&P 500 main book. It gates nothing. "
         "'Better than hold' (registered, H36's): pooled net above main in both halves, ahead of main in at least 5 of 8 "
         "markets, pooled max drawdown no worse.", ""]
    res = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "mid": args.mid,
           "variant": {NEW: RULES[NEW]}, "books": BOOKS}
    for kind in ("h36", "today"):
        groups = {}
        for g, _a in CFG["universes"]:
            p = os.path.join(OUT, "%s_%s.json" % (kind, g))
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    groups[g] = json.load(fh)
        if len(groups) == len(CFG["universes"]):
            section(kind, groups, args.mid, L, res)
        elif groups:
            L += ["## %s: only %d of %d groups ran (%s); not pooled" % (kind, len(groups), len(CFG["universes"]),
                                                                       ", ".join(groups)), ""]
    L += ["Conventions (shadows.run): half at Target 1 is a limit at the target, filled when a bar reaches it, after "
          "the stop check in that bar; the stop moves to the entry from the next bar, only ever tighter; a trade that "
          "took half at Target 1 is one trade (exit word `T1+...`). Target 1 is `live.plan_targets` at entry. "
          "Sharpe on daily marked equity, sqrt(365). Pooled: markets' daily equity summed, a market not yet trading at $10,000.", ""]
    for kind in ("h36", "today"):
        if kind in res:
            for a, r in res[kind]["per_market"].items():
                r.pop("curves", None)
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    for kind in ("h36", "today"):
        if kind in res:
            log("%s: reproduced H36 = %s" % (kind, res[kind]["reproduced_h36"]))
            for name in BOOKS:
                s = res[kind]["pooled"][name]
                log("  %-11s %+10.0f vs main %+10.0f halves %+9.0f / %+9.0f DD %6.2f%% beats %d BTH %s" % (
                    name, s["pnl_usd"], s["vs_main_usd"], s["gap_first_half"], s["gap_second_half"], s["max_dd_pct"],
                    len(s["markets_beating_main"]), s["better_than_hold"]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--window", choices=("h36", "today"), default="h36")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--mid", default="2023-06-08")
    ap.add_argument("--fits-dir", default=None, help="default research/out/h59_half_be/fits_<window>")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.report:
        report(args, log)
        return
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    fits = args.fits_dir or os.path.join(OUT, "fits_%s" % args.window)
    for g in ([args.group] if args.group else list(groups)):
        r = run_group(g, groups[g], args.window, fits, args.mid, log)
        with open(os.path.join(OUT, "%s_%s.json" % (args.window, g)), "w", encoding="utf-8") as fh:
            json.dump(r, fh)
        gc.collect()


if __name__ == "__main__":
    main()
