# -*- coding: utf-8 -*-
"""H111: pairs as one bet. The Setups book's trades counted at half size when the pair partner already holds the same
side (V1, the primary variant), and a cap on trades open in one direction (V2, descriptive). Research only; registered
in research/HYPOTHESES.md (H111) before any number. Every book is the engine's own shadows.run under the b_targets
rule. Reads the evidence store and the cached fits; changes nothing in the engine.

    python research/h111_pair_bets.py --fits-dir fits_today --group fx      one group's books -> cache_trades/<group>.*
    python research/h111_pair_bets.py --analyse                             all five groups' trades -> report + results
    python research/h111_pair_bets.py --analyse --smoke                     whatever groups are cached -> out/smoke/

Only the --group step loads the evidence store (take the history lock for it). --analyse is arithmetic on the trades.
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
sys.path.insert(0, os.path.join(ROOT, "research", "queue"))

OUT = os.path.join(ROOT, "research", "out", "h111_pair_bets")
CACHE = os.path.join(OUT, "cache_trades")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
ORDER = ["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"]      # V2's order among ties
PAIRS = (("BTCUSDT", "ETHUSDT"), ("XAUUSD", "XAGUSD"), ("WTI", "BRENT"))
NAMES = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P 500",
         "WTI": "WTI", "BRENT": "Brent"}
MID, HOLDOUT, FORWARD = "2023-06-08", "2025-11-11", "2026-11-11"      # first day of h2, of the holdout, of the forward slice
H68_CUT = "2026-11-21 13:45"
H68_REF = {"all": (5963, 22.5), "vault": (2074, -7.7), "others": (3889, 30.3)}   # H68's "current" book: trades, sum of R
SEGS = ("all", "h1", "h2", "holdout", "forward")
LEGS = ("h1", "h2", "holdout")
CAP = 4                    # V2: a trade is dropped when this many kept trades are open on its side on other markets
PLACEBO_DRAWS, PLACEBO_SEED = 2000, 2026112411
KEEP_TOTAL = 0.85
DAY_MS, BAR_MS = 86400000, 900000
AT_OPEN, INSIDE = {"FLIP", "STEP_ASIDE"}, {"STOP", "STOP_BE", "T2"}   # the last word of why_out: a fill at the open / in the bar


# ------------------------------------------------------------------------------------------------ the books (store)
def store_end(g, assets):
    """The group's last stored session, as prep_cut_lean wants it."""
    from engine15 import evcache
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, g, assets[0]))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (g, assets[0]))
    return str(pd.to_datetime(int(st.times_ms()[-1]), unit="ms", utc=True))[:16]


def run_group(g, fits_root, log=print):
    """The b_targets book of every market of one group, to the store's last session -> cache_trades/<g>.csv + .json"""
    import walkforward as wf
    from engine15 import data, shadows
    assets = dict(GROUPS)[g]
    t0 = time.time()
    prep = wf.prep_cut_lean(g, assets, os.path.join(fits_root, g), store_end(g, assets), log=log)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    frames, meta = [], {}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        inp = shadows.book_inputs(prep, a)
        cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
        tgt = aux["targets"]
        row_of = lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
        b = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, bias=inp["bias"],
                        guard=inp["guard"], rule=dict(shadows.CHALLENGERS["b_targets"]["rule"]), aux=aux, times_ms=tms,
                        row_of=row_of)                              # exactly H68's "current" book
        ref = shadows.run_challenger("b_targets", prep, a, lo, n, aux=aux)    # the engine's own book must be this very one
        assert len(ref["trades"]) == len(b["trades"]) and np.allclose(ref["equity"][lo:n], b["equity"][lo:n])
        assert np.allclose(ref["trades"].pnl_usd.values, b["trades"].pnl_usd.values)
        assert np.array_equal(ref["trades"].t_in_ms.values, b["trades"].t_in_ms.values)
        tr = b["trades"].copy()
        tr.insert(0, "market", a)
        frames.append(tr)
        st = b["state"]
        meta[a] = {"first_ms": int(tms[lo]), "last_ms": int(tms[n - 1]), "open_side": int(st["pos"]),
                   "open_t_in_ms": None if not st["pos"] else int(st["t_in_ms"]), "end_equity": float(st["eq"])}
        log("%s: %d closed trades, %s to %s (%.0fs)" % (a, len(tr), str(times[lo])[:16], str(times[n - 1])[:16],
                                                        time.time() - t0))
    del prep
    gc.collect()
    os.makedirs(CACHE, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(os.path.join(CACHE, g + ".csv"), index=False)
    with open(os.path.join(CACHE, g + ".json"), "w") as fh:
        json.dump(meta, fh, indent=1)


def load_cached(groups):
    frames, meta = [], {}
    for g in groups:
        frames.append(pd.read_csv(os.path.join(CACHE, g + ".csv")))
        with open(os.path.join(CACHE, g + ".json")) as fh:
            meta.update(json.load(fh))
    return pd.concat(frames, ignore_index=True), meta


# ------------------------------------------------------------------------------------------------ arithmetic on trades
def add_points(tr):
    """pts = the trade's result in percent of its book's equity just before it opened; t_end_x = the first moment at
    which the trade is no longer open (its exit bar's open for a FLIP or STEP_ASIDE fill, one ms later otherwise);
    day = the UTC day its exit bar opened."""
    tr = tr.copy()
    before = tr.equity.values - tr.pnl_usd.values
    if not (before > 0).all():
        raise RuntimeError("a book's equity before a trade is not above zero")
    tr["pts"] = 100.0 * tr.pnl_usd.values / before
    last = tr.why_out.astype(str).str.split("+").str[-1]
    unknown = set(last) - AT_OPEN - INSIDE
    if unknown:
        raise RuntimeError("exit words this study does not know: %s" % sorted(unknown))
    tr["t_end_x"] = tr.t_out_ms.values.astype(np.int64) + np.where(last.isin(AT_OPEN).values, 0, 1)
    tr["day"] = tr.t_out_ms.values.astype(np.int64) // DAY_MS
    return tr


def v1_weights(tr, tie_half=True):
    """V1: 0.5 for a trade entered while its pair partner holds an open trade on the same side, else 1. Two partner
    trades entered at the same moment on the same side: both 0.5 (tie_half) or both 1 (the strict reading, V1s)."""
    w = pd.Series(1.0, index=tr.index)
    by = dict((m, t.sort_values("t_in_ms")) for m, t in tr.groupby("market"))
    for a, b in PAIRS:
        for me, other in ((a, b), (b, a)):
            if me not in by or other not in by:
                continue
            x, y = by[me], by[other]
            y_in, y_end, y_side = y.t_in_ms.values, y.t_end_x.values, y.side.values
            for idx, t, s in zip(x.index, x.t_in_ms.values, x.side.values):
                k = int(np.searchsorted(y_in, t, side="left"))
                if k > 0 and t < y_end[k - 1] and y_side[k - 1] == s:        # the partner's trade was entered before t
                    w[idx] = 0.5
                elif tie_half and k < len(y_in) and y_in[k] == t and y_side[k] == s:
                    w[idx] = 0.5
    return w


def v2_keep(tr, cap=CAP):
    """V2: in order of entry (ties by ORDER), a trade is dropped when `cap` or more kept trades are open on its side
    on other markets at its entry (kept trades entered at the same moment and earlier in the order count)."""
    rank = dict((m, i) for i, m in enumerate(ORDER))
    o = tr.assign(_r=tr.market.map(rank)).sort_values(["t_in_ms", "_r"])
    keep = pd.Series(True, index=tr.index)
    last = {}                                                     # market -> (side, t_end_x) of its last kept trade
    for idx, m, t, s, e in zip(o.index, o.market.values, o.t_in_ms.values, o.side.values, o.t_end_x.values):
        open_same = sum(1 for k, (sd, end) in last.items() if k != m and sd == s and t < end)
        if open_same >= cap:
            keep[idx] = False
        else:
            last[m] = (s, e)
    return keep


def seg_days(d0, d1):
    """Segment -> (first day, last day + 1) in days since 1970, clipped to d0 .. d1 (inclusive)."""
    day = lambda s: int(pd.Timestamp(s, tz="UTC").value // (DAY_MS * 10 ** 6))   # noqa: E731
    mid, hold, fwd = day(MID), day(HOLDOUT), day(FORWARD)
    raw = {"all": (d0, d1 + 1), "h1": (d0, mid), "h2": (mid, hold), "holdout": (hold, fwd), "forward": (fwd, d1 + 1)}
    return dict((k, (min(max(a, d0), d1 + 1), min(max(z, d0), d1 + 1))) for k, (a, z) in raw.items())


def seg_of_day(days, segs):
    out = np.full(len(days), "", dtype=object)
    for k in ("h1", "h2", "holdout", "forward"):
        a, z = segs[k]
        out[(days >= a) & (days < z)] = k
    return out


def daily(days, pts, d0, d1):
    return np.bincount(np.asarray(days, dtype=np.int64) - d0, weights=np.asarray(pts, dtype=float), minlength=d1 - d0 + 1)


def measures(x):
    """Total, worst day, worst fall (the largest drop of the running sum from its highest point so far, the running
    sum starting at zero) and total / worst fall, of one stretch of daily points."""
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return {"days": 0, "total": 0.0, "worst_day": None, "worst_fall": 0.0, "ratio": None}
    cum = np.cumsum(x)
    peak = np.maximum(np.maximum.accumulate(cum), 0.0)
    fall = float(np.max(peak - cum))
    total = float(cum[-1])
    return {"days": int(len(x)), "total": total, "worst_day": float(x.min()), "worst_fall": fall,
            "ratio": total / fall if fall > 0 else None}


def by_segment(series, d0, segs):
    return dict((k, measures(series[a - d0:z - d0])) for k, (a, z) in segs.items())


def verdict(v0, v1):
    """The registered PASS condition, and the brief's wording alone (no above-zero requirement) beside it."""
    legs, brief = {}, {}
    for k in LEGS:
        r0, r1 = v0[k]["ratio"], v1[k]["ratio"]
        higher = r0 is not None and r1 is not None and r1 > r0
        legs[k] = bool(higher and v1[k]["total"] > 0)
        brief[k] = bool(higher)
    t0, t1 = v0["all"]["total"], v1["all"]["total"]
    keep = bool(t1 >= KEEP_TOTAL * t0) if t0 > 0 else bool(t1 >= t0)
    legs["total_kept"] = brief["total_kept"] = keep
    return {"legs": legs, "pass": all(legs.values()), "brief_wording": brief, "brief_wording_pass": all(brief.values())}


def placebo(tr, w1, d0, d1, segs, v1_ratio, draws=PLACEBO_DRAWS, seed=PLACEBO_SEED):
    """The same number of trades halved in each market and segment, chosen at random. -> per segment: the share of
    draws whose ratio is at least V1's, and the draws' median ratio."""
    seg = seg_of_day(tr.day.values, segs)
    cells = []
    for (m, s), idx in tr.groupby(["market", pd.Series(seg, index=tr.index)]).indices.items():
        k = int((w1.values[idx] < 1).sum())
        if k:
            cells.append((np.asarray(idx), k))
    days, pts = tr.day.values, tr.pts.values
    got = dict((k, []) for k in SEGS)
    for j in range(draws):
        rng = np.random.default_rng([seed, j])
        w = np.ones(len(tr))
        for idx, k in cells:
            w[rng.choice(idx, size=k, replace=False)] = 0.5
        ms = by_segment(daily(days, pts * w, d0, d1), d0, segs)
        for k in SEGS:
            got[k].append(np.nan if ms[k]["ratio"] is None else ms[k]["ratio"])
    out = {}
    for k in SEGS:
        g = np.asarray(got[k], dtype=float)
        ok = np.isfinite(g)
        r = v1_ratio[k]
        out[k] = {"draws": int(ok.sum()), "median_ratio": float(np.median(g[ok])) if ok.any() else None,
                  "share_at_least_v1": float((1 + (g[ok] >= r).sum()) / (1 + ok.sum())) if r is not None and ok.any() else None}
    return out


def holding_grid(tr, meta):
    """Per market, on a 15-minute grid over the time when all eight books have started: +1 / -1 / 0 = the side of its
    open trade (a slot counts when the trade is open during any part of it; the trade still open at the end counts)."""
    t0 = max(v["first_ms"] for v in meta.values())
    t1 = min(v["last_ms"] for v in meta.values())
    n = (t1 - t0) // BAR_MS + 1
    grid = {}
    for m, t in tr.groupby("market"):
        d = np.zeros(n + 1, dtype=np.int64)
        a = np.clip(np.ceil((t.t_in_ms.values - t0) / BAR_MS).astype(np.int64), 0, n)
        z = np.clip(np.ceil((t.t_end_x.values - t0) / BAR_MS).astype(np.int64), 0, n)      # first slot not held
        np.add.at(d, a, t.side.values)
        np.add.at(d, z, -t.side.values)
        if meta[m]["open_side"]:
            d[min(max((meta[m]["open_t_in_ms"] - t0 + BAR_MS - 1) // BAR_MS, 0), n)] += meta[m]["open_side"]
        h = np.cumsum(d[:n])
        if np.abs(h).max() > 1:
            raise RuntimeError("%s holds two trades at once on the grid" % m)
        grid[m] = h.astype(np.int8)
    return t0, n, grid


def same_side_table(tr, meta, segs):
    t0, n, grid = holding_grid(tr, meta)
    H = np.stack([grid[m] for m in ORDER if m in grid])
    longs, shorts = (H == 1).sum(axis=0), (H == -1).sum(axis=0)
    most = np.maximum(longs, shorts)
    day = (t0 + np.arange(n, dtype=np.int64) * BAR_MS) // DAY_MS
    out = {"window": [str(pd.to_datetime(t0, unit="ms"))[:16], str(pd.to_datetime(t0 + (n - 1) * BAR_MS, unit="ms"))[:16]],
           "markets": int(H.shape[0]), "segments": {}}
    for k, (a, z) in segs.items():
        sel = (day >= a) & (day < z)
        if not sel.any():
            out["segments"][k] = None
            continue
        out["segments"][k] = {"long5_pct": float((longs[sel] >= 5).mean() * 100), "short5_pct": float((shorts[sel] >= 5).mean() * 100),
                              "either5_pct": float((most[sel] >= 5).mean() * 100),
                              "most_pct": [float((most[sel] == c).mean() * 100) for c in range(H.shape[0] + 1)],
                              "mean_long": float(longs[sel].mean()), "mean_short": float(shorts[sel].mean())}
    pairs = {}
    for a, b in PAIRS:
        if a in grid and b in grid:
            both = (grid[a] != 0) & (grid[b] != 0)
            same = both & (grid[a] == grid[b])
            pairs[a + "+" + b] = {"same_side_pct_of_time": float(same.mean() * 100), "opposite_pct_of_time": float((both & ~same).mean() * 100)}
    return out, pairs


def analyse(tr, meta, log=print, draws=PLACEBO_DRAWS):
    tr = add_points(tr).reset_index(drop=True)
    markets = [m for m in ORDER if m in set(tr.market)]
    d0 = min(v["first_ms"] for v in meta.values()) // DAY_MS
    d1 = max(v["last_ms"] for v in meta.values()) // DAY_MS
    segs = seg_days(d0, d1)
    w1, w1s, keep2 = v1_weights(tr, True), v1_weights(tr, False), v2_keep(tr)
    weights = {"V0": np.ones(len(tr)), "V1": w1.values, "V1s": w1s.values, "V2": keep2.values.astype(float)}
    res = {"window_days": [str(pd.to_datetime(d0 * DAY_MS, unit="ms"))[:10], str(pd.to_datetime(d1 * DAY_MS, unit="ms"))[:10]],
           "segments": dict((k, [str(pd.to_datetime(a * DAY_MS, unit="ms"))[:10], str(pd.to_datetime((z - 1) * DAY_MS, unit="ms"))[:10]])
                            for k, (a, z) in segs.items()),
           "markets": {}, "variants": {}}
    series = {}
    for name, w in weights.items():
        series[name] = daily(tr.day.values, tr.pts.values * w, d0, d1)
        res["variants"][name] = by_segment(series[name], d0, segs)
    res["verdict"] = verdict(res["variants"]["V0"], res["variants"]["V1"])
    seg = seg_of_day(tr.day.values, segs)
    # counts and the halved-against-full table
    res["counts"], res["halved_vs_full"] = {}, {}
    for k in SEGS:
        sel = np.ones(len(tr), bool) if k == "all" else (seg == k)
        half = sel & (w1.values < 1)
        full = sel & (w1.values == 1)
        paired = sel & tr.market.isin([m for p in PAIRS for m in p]).values
        res["counts"][k] = {"trades": int(sel.sum()), "in_pairs": int(paired.sum()), "v1_halved": int(half.sum()),
                            "v1s_halved": int((sel & (w1s.values < 1)).sum()), "v2_dropped": int((sel & ~keep2.values).sum())}
        cell = lambda q: {"trades": int(q.sum()), "mean_pts": float(tr.pts.values[q].mean()) if q.any() else None,   # noqa: E731
                          "sum_pts": float(tr.pts.values[q].sum()), "won_pct": float((tr.pts.values[q] > 0).mean() * 100) if q.any() else None}
        res["halved_vs_full"][k] = {"halved": cell(half), "full_in_pairs": cell(full & paired), "v2_dropped": cell(sel & ~keep2.values),
                                    "v2_kept": cell(sel & keep2.values)}
    # per market
    per_day = {}
    for m in markets:
        q = (tr.market == m).values
        per_day[m] = daily(tr.day.values[q], tr.pts.values[q], d0, d1)
        r = tr.r_mult.values[q]
        res["markets"][m] = {"trades": int(q.sum()), "first": str(pd.to_datetime(meta[m]["first_ms"], unit="ms"))[:16],
                             "last": str(pd.to_datetime(meta[m]["last_ms"], unit="ms"))[:16],
                             "sum_r": float(np.nansum(r)), "end_equity": meta[m]["end_equity"],
                             "pts": dict((k, float(tr.pts.values[q & (np.ones(len(tr), bool) if k == "all" else seg == k)].sum())) for k in SEGS),
                             "pts_v1": float((tr.pts.values * w1.values)[q].sum()), "v1_halved": int((q & (w1.values < 1)).sum()),
                             "v2_dropped": int((q & ~keep2.values).sum()), "short_pct": float((tr.side.values[q] == -1).mean() * 100)}
    # pairs: correlation of daily points
    closes = dict((m, daily(tr.day.values[(tr.market == m).values], np.ones(int((tr.market == m).sum())), d0, d1)) for m in markets)
    grid_tab, pair_time = same_side_table(tr, meta, segs) if len(markets) == len(ORDER) else (None, {})
    res["same_side"] = grid_tab
    res["pairs"] = {}
    for a, b in PAIRS:
        if a not in per_day or b not in per_day:
            continue
        both0 = max(meta[a]["first_ms"], meta[b]["first_ms"]) // DAY_MS - d0
        xa, xb = per_day[a][both0:], per_day[b][both0:]
        bc = (closes[a][both0:] > 0) & (closes[b][both0:] > 0)
        corr = lambda u, v: float(np.corrcoef(u, v)[0, 1]) if len(u) > 2 and u.std() > 0 and v.std() > 0 else None   # noqa: E731
        p = {"corr_all_days": corr(xa, xb), "days": int(len(xa)), "corr_days_both_closed": corr(xa[bc], xb[bc]), "days_both_closed": int(bc.sum()),
             "both_lose_days_pct": float(((xa < 0) & (xb < 0)).mean() * 100), "corr_by_segment": {}}
        for k in ("h1", "h2", "holdout", "forward"):
            s0, s1 = segs[k][0] - d0, segs[k][1] - d0
            p["corr_by_segment"][k] = corr(per_day[a][max(s0, both0):s1], per_day[b][max(s0, both0):s1])
        for m in (a, b):
            q = (tr.market == m).values
            p["halved_pct_" + m] = float((w1.values[q] < 1).mean() * 100)
        p.update(pair_time.get(a + "+" + b, {}))
        res["pairs"][a + "+" + b] = p
    # the 20 worst V0 days
    v0 = series["V0"]
    worst = np.argsort(v0, kind="stable")[:20]
    rows, any_pair = [], 0
    pair_hits = dict((a + "+" + b, 0) for a, b in PAIRS if a in per_day and b in per_day)
    for i in worst:
        hit = [k for k in pair_hits if per_day[k.split("+")[0]][i] < 0 and per_day[k.split("+")[1]][i] < 0]
        for k in hit:
            pair_hits[k] += 1
        any_pair += bool(hit)
        rows.append({"day": str(pd.to_datetime((d0 + int(i)) * DAY_MS, unit="ms"))[:10], "v0": float(v0[i]), "v1": float(series["V1"][i]),
                     "v2": float(series["V2"][i]), "markets_losing": int(sum(per_day[m][i] < 0 for m in markets)),
                     "pairs_both_losing": hit, "by_market": dict((m, round(float(per_day[m][i]), 3)) for m in markets if per_day[m][i] != 0)})
    any_all = np.zeros(len(v0), bool)
    for k in pair_hits:
        a, b = k.split("+")
        any_all |= (per_day[a] < 0) & (per_day[b] < 0)
    res["worst20"] = {"days": rows, "with_a_pair_both_losing": int(any_pair), "per_pair": pair_hits,
                      "all_days_with_a_pair_both_losing_pct": float(any_all.mean() * 100),
                      "losing_days_with_a_pair_both_losing_pct": float(any_all[v0 < 0].mean() * 100) if (v0 < 0).any() else None,
                      "sum_v0": float(v0[worst].sum()), "sum_v1": float(series["V1"][worst].sum()), "sum_v2": float(series["V2"][worst].sum())}
    # the placebo for V1
    res["placebo"] = placebo(tr, w1, d0, d1, segs, dict((k, res["variants"]["V1"][k]["ratio"]) for k in SEGS), draws=draws) if draws else None
    # reconciliation with H68's "current" book (trades closed by its cut)
    cut = int(pd.Timestamp(H68_CUT, tz="UTC").value // 10 ** 6)
    q = tr.t_out_ms.values <= cut
    vault = tr.market.isin(["BTCUSDT", "ETHUSDT"]).values
    rec = lambda s: {"trades": int(s.sum()), "sum_r": float(np.nansum(tr.r_mult.values[s]))}   # noqa: E731
    res["h68_reconciliation"] = {"cut": H68_CUT, "here": {"all": rec(q), "vault": rec(q & vault), "others": rec(q & ~vault)},
                                 "h68": dict((k, {"trades": v[0], "sum_r": v[1]}) for k, v in H68_REF.items())}
    res["open_at_end"] = dict((m, meta[m]["open_side"]) for m in markets)
    return res, tr.assign(w_v1=w1.values, w_v1s=w1s.values, v2_kept=keep2.values.astype(int), segment=seg)


# ------------------------------------------------------------------------------------------------ the report
def _n(x, f="%+.1f"):
    return "-" if x is None else f % x


def _cell(p):
    return "%s | %s | %s | %s" % (_n(p["total"]), _n(p["worst_day"]), _n(p["worst_fall"], "%.1f"), _n(p["ratio"], "%+.2f"))


def write_report(res, out):
    V, vd = res["variants"], res["verdict"]
    seg_name = {"all": "All history", "h1": "h1", "h2": "h2", "holdout": "Holdout", "forward": "Forward (14 days)"}
    L = ["# H111: pairs as one bet (BTC+ETH, gold+silver, WTI+Brent) on the Setups book", "",
         "A replay on history, registered before any number was computed (research/HYPOTHESES.md, H111). It is post-mortem",
         "material, not validation. Nothing live was changed. The books are the engine's own Setups rule (`b_targets`),",
         "one $10,000 paper book per market, %s to %s." % (res["window_days"][0], res["window_days"][1]), "",
         "## Verdict by the registered condition", "",
         "**V1 (pair-half) %s.**" % ("PASSES" if vd["pass"] else "DOES NOT PASS"), "",
         "| Leg | Needed | Met |", "|---|---|---|"]
    for k in LEGS:
        L.append("| %s | V1's ratio above V0's (%s against %s) and V1's total above zero (%s) | %s |" % (
            seg_name[k], _n(V["V1"][k]["ratio"], "%+.2f"), _n(V["V0"][k]["ratio"], "%+.2f"), _n(V["V1"][k]["total"]),
            "yes" if vd["legs"][k] else "NO"))
    L.append("| Total kept | V1's total over all history at least 85%% of V0's (%s against %s) | %s |" % (
        _n(V["V1"]["all"]["total"]), _n(V["V0"]["all"]["total"]), "yes" if vd["legs"]["total_kept"] else "NO"))
    L += ["", "By the brief's wording alone (the ratio higher in the three legs and the total kept, with no need for V1's total",
          "to be above zero): %s (%s)." % ("pass" if vd["brief_wording_pass"] else "does not pass",
                                          ", ".join("%s %s" % (k, "yes" if v else "no") for k, v in vd["brief_wording"].items())),
          "The registered condition is the one that decides.", "",
          "## Words used", "",
          "- **Point**: one percent of one book's own money. A trade that makes 2% of its book adds 2 points. Points of the",
          "  eight books are added up by the day a trade closed. Eight books each losing 1% on one day is a day of -8 points.",
          "- **V0**: the books as they are. **V1**: a trade that opens while its pair partner already holds a trade on the same",
          "  side counts at half; two partner trades opened at the same moment both count at half. **V1s**: as V1, but trades",
          "  opened at the same moment stay full. **V2**: a trade is left out when four other markets already hold that side.",
          "- **Worst day**: the worst single day of portfolio points. **Worst fall**: the largest drop of the running total from",
          "  its highest point so far. **Ratio**: total divided by worst fall. Higher is better. Making every trade smaller by",
          "  the same amount does not change it.",
          "- **h1**: %s to %s. **h2**: %s to %s. **Holdout**: %s to %s. **Forward**: %s to %s, the days that prompted this" % (
              res["segments"]["h1"][0], res["segments"]["h1"][1], res["segments"]["h2"][0], res["segments"]["h2"][1],
              res["segments"]["holdout"][0], res["segments"]["holdout"][1], res["segments"]["forward"][0], res["segments"]["forward"][1]),
          "  study, shown apart and part of no leg.", "",
          "## The numbers", "", "Each cell: total points | worst day | worst fall | ratio.", "",
          "| Variant | " + " | ".join(seg_name[k] for k in SEGS) + " |", "|---|" + "---|" * len(SEGS)]
    vn = {"V0": "V0 current", "V1": "V1 pair-half (primary)", "V1s": "V1s (descriptive)", "V2": "V2 direction cap (descriptive)"}
    for name in ("V0", "V1", "V1s", "V2"):
        L.append("| %s | %s |" % (vn[name], " | ".join(_cell(V[name][k]) for k in SEGS)))
    c = res["counts"]
    L += ["", "Trades: " + "; ".join("%s %d (in pairs %d, V1 halves %d, V1s halves %d, V2 drops %d)" % (
        seg_name[k], c[k]["trades"], c[k]["in_pairs"], c[k]["v1_halved"], c[k]["v1s_halved"], c[k]["v2_dropped"]) for k in SEGS) + ".",
        "", "V2 is descriptive only. A real book that skips a trade is flat afterwards and would enter differently later.",
        "Here the trade is only removed from the record. The replay cannot show what the book would then have done."]
    if res.get("placebo"):
        P = res["placebo"]
        L += ["", "## Does it matter WHICH trades are halved", "",
              "Placebo: the same number of trades halved in each market and period, picked at random, %d times." % PLACEBO_DRAWS,
              "", "| | " + " | ".join(seg_name[k] for k in SEGS) + " |", "|---|" + "---|" * len(SEGS),
              "| V0 ratio | " + " | ".join(_n(V["V0"][k]["ratio"], "%+.2f") for k in SEGS) + " |",
              "| V1 ratio | " + " | ".join(_n(V["V1"][k]["ratio"], "%+.2f") for k in SEGS) + " |",
              "| Random halving, median ratio | " + " | ".join(_n(P[k]["median_ratio"], "%+.2f") for k in SEGS) + " |",
              "| Share of random draws at least as good as V1 | " + " | ".join(
                  "-" if P[k]["share_at_least_v1"] is None else "%.0f%%" % (P[k]["share_at_least_v1"] * 100) for k in SEGS) + " |"]
    hv = res["halved_vs_full"]
    L += ["", "## The trades V1 halves against the ones it leaves full", "",
          "Pair markets only, at full size. Each cell: trades, mean points a trade, share won.", "",
          "| | " + " | ".join(seg_name[k] for k in SEGS) + " |", "|---|" + "---|" * len(SEGS)]
    hc = lambda p: "-" if not p["trades"] else "%d, %+.3f, %.0f%%" % (p["trades"], p["mean_pts"], p["won_pct"])   # noqa: E731
    L.append("| Halved by V1 (partner already on that side) | " + " | ".join(hc(hv[k]["halved"]) for k in SEGS) + " |")
    L.append("| Left full | " + " | ".join(hc(hv[k]["full_in_pairs"]) for k in SEGS) + " |")
    L.append("| Dropped by V2 (all markets) | " + " | ".join(hc(hv[k]["v2_dropped"]) for k in SEGS) + " |")
    L.append("| Kept by V2 (all markets) | " + " | ".join(hc(hv[k]["v2_kept"]) for k in SEGS) + " |")
    if res.get("same_side"):
        S = res["same_side"]
        L += ["", "## How often five or more markets hold the same side", "",
              "Share of time, %s to %s, positions carried over closed hours." % (S["window"][0], S["window"][1]), "",
              "| | " + " | ".join(seg_name[k] for k in SEGS) + " |", "|---|" + "---|" * len(SEGS)]
        for key, lab in (("either5_pct", "5+ on one side (long or short)"), ("long5_pct", "5+ long"), ("short5_pct", "5+ short")):
            L.append("| %s | " % lab + " | ".join("-" if S["segments"][k] is None else "%.0f%%" % S["segments"][k][key] for k in SEGS) + " |")
        a = S["segments"]["all"]
        L += ["", "Largest number of markets on one side, share of time (all history): " + ", ".join(
            "%d: %.0f%%" % (i, x) for i, x in enumerate(a["most_pct"]) if x >= 0.5) + "."]
    L += ["", "## The pairs", "",
          "| Pair | Daily results move together (correlation, all days) | Only days both closed a trade | Both hold the same side, share of time | Opposite sides | Trades V1 halves |",
          "|---|---|---|---|---|---|"]
    for k, p in res["pairs"].items():
        a, b = k.split("+")
        L.append("| %s + %s | %s | %s (%d days) | %s | %s | %s %.0f%%, %s %.0f%% |" % (
            NAMES[a], NAMES[b], _n(p["corr_all_days"], "%+.2f"), _n(p["corr_days_both_closed"], "%+.2f"), p["days_both_closed"],
            "-" if "same_side_pct_of_time" not in p else "%.0f%%" % p["same_side_pct_of_time"],
            "-" if "opposite_pct_of_time" not in p else "%.0f%%" % p["opposite_pct_of_time"],
            NAMES[a], p["halved_pct_" + a], NAMES[b], p["halved_pct_" + b]))
    L += ["", "Correlation runs from -1 to +1. 0 means the two books' days have nothing to do with each other. +1 means they",
          "win and lose together every day.", "",
          "Correlation by period: " + "; ".join("%s + %s: %s" % (NAMES[k.split("+")[0]], NAMES[k.split("+")[1]], ", ".join(
              "%s %s" % (s, _n(p["corr_by_segment"][s], "%+.2f")) for s in ("h1", "h2", "holdout", "forward"))) for k, p in res["pairs"].items()) + "."]
    W = res["worst20"]
    L += ["", "## The 20 worst days of the books as they are (V0)", "",
          "On %d of the 20, both members of at least one pair lost that day (%s)." % (
              W["with_a_pair_both_losing"], ", ".join("%s + %s: %d" % (NAMES[k.split("+")[0]], NAMES[k.split("+")[1]], v) for k, v in W["per_pair"].items())),
          "Over all days that happens on %.1f%% of days, and on %s of losing days." % (
              W["all_days_with_a_pair_both_losing_pct"], "-" if W["losing_days_with_a_pair_both_losing_pct"] is None
              else "%.0f%%" % W["losing_days_with_a_pair_both_losing_pct"]),
          "The 20 days together: V0 %+.1f points, V1 %+.1f, V2 %+.1f." % (W["sum_v0"], W["sum_v1"], W["sum_v2"]), "",
          "| Day | V0 | V1 | V2 | Markets losing | Pairs with both losing |", "|---|---|---|---|---|---|"]
    for r in W["days"]:
        L.append("| %s | %+.1f | %+.1f | %+.1f | %d | %s |" % (r["day"], r["v0"], r["v1"], r["v2"], r["markets_losing"], ", ".join(
            "%s+%s" % tuple(NAMES[x] for x in k.split("+")) for k in r["pairs_both_losing"]) or "-"))
    L += ["", "## Per market", "", "| Market | Trades | Short | Points V0 (all) | h1 | h2 | Holdout | Forward | Points V1 (all) | V1 halves | V2 drops | Sum of R |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in res["markets"].items():
        L.append("| %s | %d | %.0f%% | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %d | %d | %+.1f |" % (
            NAMES[m], v["trades"], v["short_pct"], v["pts"]["all"], v["pts"]["h1"], v["pts"]["h2"], v["pts"]["holdout"], v["pts"]["forward"],
            v["pts_v1"], v["v1_halved"], v["v2_dropped"], v["sum_r"]))
    R = res["h68_reconciliation"]
    L += ["", "## Check against H68", "",
          "Trades closed by %s UTC: here %d trades, %+.1fR (BTC+ETH %d, %+.1fR; the other six %d, %+.1fR). H68 reported %d," % (
              R["cut"], R["here"]["all"]["trades"], R["here"]["all"]["sum_r"], R["here"]["vault"]["trades"], R["here"]["vault"]["sum_r"],
              R["here"]["others"]["trades"], R["here"]["others"]["sum_r"], R["h68"]["all"]["trades"]),
          "%+.1fR (BTC+ETH %d, %+.1fR; the other six %d, %+.1fR)." % (R["h68"]["all"]["sum_r"], R["h68"]["vault"]["trades"], R["h68"]["vault"]["sum_r"],
                                                                  R["h68"]["others"]["trades"], R["h68"]["others"]["sum_r"])]
    reading = os.path.join(out, "reading.md")                    # written by hand after the run: the reading and the limits
    if os.path.exists(reading):                                  # placed after the words, before the tables
        with open(reading, encoding="utf-8") as fh:
            k = L.index("## The numbers")
            L[k:k] = [fh.read().replace("\r", "").strip(), ""]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir")
    ap.add_argument("--group", choices=[g for g, _a in GROUPS])
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="analyse whatever groups are cached, into out/smoke (not a result)")
    args = ap.parse_args(argv)
    if args.group:
        if not args.fits_dir:
            ap.error("--group needs --fits-dir")
        run_group(args.group, args.fits_dir)
    if args.analyse:
        have = [g for g, _a in GROUPS if os.path.exists(os.path.join(CACHE, g + ".csv"))]
        if not args.smoke and len(have) != len(GROUPS):
            raise SystemExit("cached groups: %s; all five are needed (or --smoke)" % have)
        tr, meta = load_cached(have)
        res, trades = analyse(tr, meta, draws=50 if args.smoke else PLACEBO_DRAWS)
        out = os.path.join(OUT, "smoke") if args.smoke else OUT
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "results.json"), "w") as fh:
            json.dump(res, fh, indent=1, default=float)
        trades.to_csv(os.path.join(out, "trades.csv.gz"), index=False)
        write_report(res, out)
        print("SMOKE (not a result)" if args.smoke else "verdict: %s" % ("PASS" if res["verdict"]["pass"] else "DOES NOT PASS"))


if __name__ == "__main__":
    main()
