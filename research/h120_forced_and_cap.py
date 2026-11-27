# -*- coding: utf-8 -*-
"""H120: the Setups book on BTC and ETH without forced entries (A), and with no card above 20% of the say (B), replayed
against the live rule. Registered in research/HYPOTHESES.md before any number. Research only; reads the evidence store
and a COPY of the cached fits; changes nothing.

The odds are built exactly as engine15/leanprep.py builds them for the live engine (the voting cards' trust path, the
trust cap of v5.2 in both places, the per-session weights of the cards that speak), with the cap as a parameter. (The
helper earlier studies used, research/h59_half_be.py prep_cut, leaves the cap out.)

    python research/h120_forced_and_cap.py --fits-dir <copy of data/evcache/<group>/fits, one folder per group>
                                           [--groups crypto,metals,...] [--out <folder>]
"""
import argparse
import csv
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, evcache, labels, leanprep, model, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h120_forced_and_cap")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
END = "2026-11-26 23:45"
CUTS = (("mid", "2023-06-08"), ("holdout", "2025-11-11"), ("forward", "2026-11-11"))
NO_FORCED = 10 ** 9                                   # idle_max out of reach: never a forced entry
CAPS = (("live", 0.40), ("cap20", 0.20), ("equal", "equal"))
# book -> (odds variant, idle_max or None = the live one); the bar is for A and B against current
BOOKS = (("current", "live", None), ("A_no_forced", "live", NO_FORCED), ("B_cap20", "cap20", None),
         ("AB_both", "cap20", NO_FORCED), ("equal", "equal", None))
TESTED = ("A_no_forced", "B_cap20")
START = shadows.START_EQUITY
SEGS = ("all", "h1", "h2", "holdout", "forward")


# ------------------------------------------------------------------ the odds, as leanprep builds them, cap as a parameter
def prep_group(group, assets, fits_dir, end, log=print):
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    full = pd.DatetimeIndex(pd.to_datetime(stores[assets[0]].times_ms(), unit="ms", utc=True))
    for a in assets[1:]:
        if not np.array_equal(stores[a].times_ms(), stores[assets[0]].times_ms()):
            raise RuntimeError("stores of %s disagree on rows" % group)
    n = int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
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
    probs, _models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n,
                                                        fits_dir)
    log("%s: %d sessions to %s; %d refits, %d from the cache (%.0fs)" % (
        group, n, str(times[-1])[:16], frep["refits"], frep["reused"], time.time() - t0))
    lo = birth_idx
    raw = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES]) if cfg.get("voting") else \
        np.ones(len(model.VOICE_NAMES))
    voted = raw * votes
    voted = voted / voted.sum(axis=1, keepdims=True)
    odds, top = dict((k, {}) for k, _c in CAPS), dict((k, {}) for k, _c in CAPS)
    for a in assets:
        Xa = np.asarray(X[a][lo:n])
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        del Xa
        for key, cap in CAPS:
            if cap == "equal":                               # every voting card that speaks has the same share
                trust = np.tile(votes / votes.sum(), (n - lo, 1))
                c = None
            else:
                trust = model.cap_shares(voted, cap)
                c = cap
            w = trust * speaks
            tot = w.sum(axis=1, keepdims=True)
            w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
            w = model.cap_shares(w, c)
            o = np.full((n, 3), np.nan)
            o[lo:] = model.mix(probs[a].arr, w)
            odds[key][a] = o
            top[key][a] = float(np.median(w.max(axis=1)))
        del speaks
        probs[a] = None
    del probs, X
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds, "top": top,
            "birth_idx": birth_idx}


# ------------------------------------------------------------------ read-outs
def seg(book, a, z):
    tr = book["trades"]
    tr = tr[(tr.i_in >= a) & (tr.i_in < z)]
    r = tr.r_mult.values.astype(float)
    r = r[np.isfinite(r)]
    eq = book["equity"]
    base = eq[a - 1] if a > 0 and np.isfinite(eq[a - 1]) else START
    return {"trades": int(len(tr)), "won": float((tr.pnl_usd > 0).mean() * 100) if len(tr) else None,
            "sum_r": float(r.sum()), "mean_r": float(r.mean()) if len(r) else None,
            "net": float(eq[z - 1] - base), "flat_pct": float((book["held"][a:z] == 0).mean() * 100),
            "by_word": dict((str(k), int(v)) for k, v in tr.why_in.value_counts().items())}


def fall(eq):
    e = eq[np.isfinite(eq)]
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0) if len(e) else 0.0


def longest_flat_h(held, a, z):
    best = cur = 0
    for h in held[a:z]:
        cur = cur + 1 if h == 0 else 0
        best = max(best, cur)
    return best * 0.25


def live_match(book, a, tms, live_dir):
    """Of the live Setups trades on this market (out/live/shadow_trades_b_targets_<A>.csv), the share whose entry time
    and side the replay's current book also has. Descriptive: the live book started flat on 11 Nov."""
    p = os.path.join(live_dir, "shadow_trades_b_targets_%s.csv" % a)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        live = [(int(float(r["t_in_ms"])), int(float(r["side"]))) for r in csv.DictReader(fh)]
    mine = set(zip([int(x) for x in book["trades"].t_in_ms.values], [int(x) for x in book["trades"].side.values]))
    return {"live": len(live), "found": sum(1 for x in live if x in mine)}


def run(fits_root, groups, live_dir, log=print):
    t0 = time.time()
    res = {"markets": {}, "end": END, "books": [b for b, _o, _i in BOOKS], "tested": list(TESTED)}
    curves = dict((b, {}) for b, _o, _i in BOOKS)
    for g, assets in GROUPS:
        if groups and g not in groups:
            continue
        prep = prep_group(g, assets, os.path.join(fits_root, g), END, log=log)
        times = prep["times"]
        tms = data.to_ms(times)
        n = len(times)
        for a in assets:
            ok = np.isfinite(prep["odds"]["live"][a][:, 0])
            lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
            aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
            tgt = aux["targets"]
            row_of = lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
            idx = dict((k, min(max(int(times.searchsorted(pd.Timestamp(d, tz="UTC"))), lo + 1), n - 1)) for k, d in CUTS)
            span = {"all": (lo, n), "h1": (lo, idx["mid"]), "h2": (idx["mid"], n), "holdout": (idx["holdout"], n),
                    "forward": (idx["forward"], n)}
            out = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "books": {},
                   "top_share_median": dict((k, prep["top"][k][a]) for k, _c in CAPS)}
            rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
            sides = {}
            for name, variant, idle in BOOKS:
                p = dict(prep, odds=prep["odds"][variant])
                inp = shadows.book_inputs(p, a)
                cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
                if idle is not None:
                    cfg["idle_max"] = idle
                b = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, bias=inp["bias"],
                                guard=inp["guard"], rule=rule, aux=aux, times_ms=tms, row_of=row_of)
                o = inp["odds"][lo:n]
                sides[variant] = np.sign(o[:, labels.UP] - o[:, labels.DOWN])    # the Lead's sign
                out["books"][name] = dict((s, seg(b, *span[s])) for s in SEGS)
                out["books"][name]["worst_fall"] = fall(b["equity"][lo:n])
                out["books"][name]["longest_flat_h"] = longest_flat_h(b["held"], lo, n)
                curves[name][a] = pd.Series(b["equity"][lo:n], index=times[lo:n])
                if name == "current":
                    out["live_match_forward"] = live_match(b, a, tms, live_dir)
            for variant in ("cap20", "equal"):
                both = (sides["live"] != 0) & (sides[variant] != 0)
                out["side_differs_pct_" + variant] = float((sides["live"][both] != sides[variant][both]).mean() * 100)
            res["markets"][a] = out
            log("%s done (%.0fs)" % (a, time.time() - t0))
        del prep
        gc.collect()
    # pooled: BTC + ETH, the other six, all eight
    sets = {"vault": [a for a in VAULT if a in res["markets"]],
            "others": [a for a in res["markets"] if a not in VAULT], "all8": list(res["markets"])}
    res["pooled"] = {}
    for key, ms in sets.items():
        if not ms:
            continue
        res["pooled"][key] = {}
        for name, _v, _i in BOOKS:
            cell = {}
            for s in SEGS:
                xs = [res["markets"][a]["books"][name][s] for a in ms]
                t = sum(x["trades"] for x in xs)
                sr = sum(x["sum_r"] for x in xs)
                cell[s] = {"trades": t, "sum_r": sr, "mean_r": sr / t if t else None,
                           "won": (sum((x["won"] or 0) * x["trades"] for x in xs) / t) if t else None,
                           "net": sum(x["net"] for x in xs)}
            eq = pd.concat([curves[name][a] for a in ms], axis=1).ffill().fillna(START).sum(axis=1)
            cell["worst_fall"] = fall(eq.values)
            res["pooled"][key][name] = cell
    # the registered bar, BTC + ETH, each tested book against current
    res["bar"] = {}
    if "vault" in res["pooled"]:
        v = res["pooled"]["vault"]
        for name in TESTED:
            c1 = all(v[name][h]["sum_r"] > v["current"][h]["sum_r"] for h in ("h1", "h2"))
            c2 = all((v[name][h]["mean_r"] or 0) > 0 for h in ("h1", "h2"))
            c3 = v[name]["worst_fall"] >= v["current"]["worst_fall"]
            res["bar"][name] = {"sum_r_above_both_halves": c1, "mean_r_positive_both_halves": c2, "fall_not_deeper": c3,
                                "verdict": "survives as a rule" if (c1 and c2 and c3) else "does not survive as a rule"}
    res["seconds"] = round(time.time() - t0, 1)
    return res


# ------------------------------------------------------------------ the report
def _r(x, d=3):
    return "-" if x is None else ("%+.*f" % (d, x))


def write_report(res, out):
    L = ["# H120: Setups on BTC and ETH without forced entries (A), and with no card above 20% of the say (B)", "",
         "Replay to %s; halves split at 2023-06-08; holdout from 2025-11-11 and forward from 2026-11-11 shown apart. "
         "The engine's own shadows.run under the Setups rule; odds built as the live engine builds them (trust cap "
         "included). Research only." % res["end"], "", "## The registered bar (BTC and ETH together)", ""]
    for name, b in res.get("bar", {}).items():
        L.append("- **%s: %s** (sum of R above current in both halves: %s; mean R above zero in both halves: %s; worst "
                 "fall not deeper: %s)" % (name, b["verdict"], b["sum_r_above_both_halves"], b["mean_r_positive_both_halves"],
                                          b["fall_not_deeper"]))
    for key, title in (("vault", "BTC and ETH"), ("others", "The other six (descriptive)"), ("all8", "All eight (descriptive)")):
        if key not in res["pooled"]:
            continue
        L += ["", "## %s" % title, "", "| Book | all: trades, won, mean R, sum R, net | first half | second half | holdout | "
              "forward | worst fall |", "|---|---|---|---|---|---|---|"]
        for name, c in res["pooled"][key].items():
            def cell(s, c=c):
                x = c[s]
                return "%d, %s%%, %s, %+.1f, %+.0f" % (x["trades"], "-" if x["won"] is None else "%.0f" % x["won"],
                                                      _r(x["mean_r"]), x["sum_r"], x["net"])
            L.append("| %s | %s | %s | %s | %s | %s | %.1f%% |" % (name, cell("all"), cell("h1"), cell("h2"),
                                                                  cell("holdout"), cell("forward"), c["worst_fall"]))
    L += ["", "## Per market (descriptive)", "", "| Market | book | trades | mean R | sum R | flat % | entries by word | "
          "longest flat (h) |", "|---|---|---|---|---|---|---|---|"]
    for a, m in res["markets"].items():
        for name, b in m["books"].items():
            x = b["all"]
            L.append("| %s | %s | %d | %s | %+.1f | %.0f | %s | %.0f |" % (a, name, x["trades"], _r(x["mean_r"]), x["sum_r"],
                                                                        x["flat_pct"], x["by_word"], b["longest_flat_h"]))
    L += ["", "## Checks", ""]
    for a, m in res["markets"].items():
        L.append("- %s: window %s to %s; the largest card's share of the say (median): live %.2f, cap20 %.2f, equal %.2f; "
                 "sessions where the side differs from live: cap20 %.1f%%, equal %.1f%%; live Setups trades since 11 Nov "
                 "found in the replay: %s" % (a, m["window"][0], m["window"][1], m["top_share_median"]["live"],
                                               m["top_share_median"]["cap20"], m["top_share_median"]["equal"],
                                               m["side_differs_pct_cap20"], m["side_differs_pct_equal"],
                                               m.get("live_match_forward")))
    L.append("")
    L.append("Run time %.0f s." % res["seconds"])
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True, help="a folder holding a COPY of each group's fits (<dir>/<group>)")
    ap.add_argument("--groups", default="", help="comma list; default all five")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--live-dir", default=os.path.join(ROOT, "out", "live"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    res = run(a.fits_dir, [g for g in a.groups.split(",") if g], a.live_dir, log=lambda s: print(s, flush=True))
    with open(os.path.join(a.out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    write_report(res, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
