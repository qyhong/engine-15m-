# -*- coding: utf-8 -*-
"""H42, a more balanced trust blend (research/HYPOTHESES.md). PAPER ONLY. IN-SAMPLE (development data only).

    py -3 research/trust_study.py --group crypto     one market group (one at a time: memory)
    py -3 research/trust_study.py --report           merge the groups, write research/out/trust/study.md/.json

The voices' odds are formed as the live step forms them (leanprep.prepare_live), without touching anything the live
loop writes: readings and X from data/evcache/<group> (memory maps opened READ-ONLY), rows before 2025-11-11 00:00 UTC
only (bars truncated BEFORE the grades are computed), voices walked forward weekly by leanprep.walk_forward_cached with
the refits in a PRIVATE directory (research/out/trust/fits/<group>; that function deletes fits it did not use, so the
live fits directory is never given to it). The per-voice odds and grades are computed ONCE per group; every variant
re-runs only the trust path (model.trust_path's arithmetic with its two constants changed through a cfg copy), the
voting restriction, the silent-voice mask, the mix and the main book (backtest.run_book, the asset's fee, leverage cap
and fill delay as live). engine15/config.py is not edited.

Heavy work shares research/out/heavy_job.lock (the exit study's helpers), below-normal priority, >= 1,500 MB free.
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

from engine15 import backtest, data, evcache, labels, leanprep, model, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
import exit_study as ex  # noqa: E402  (lock, memory, priority, Sharpe / drawdown helpers)

OUT = os.path.join(ROOT, "research", "out", "trust")
FITS = os.path.join(OUT, "fits")
CUT = "2025-11-11"            # development data only: rows strictly before 2025-11-11 00:00 UTC
MID = "2022-12-06"            # calendar midpoint of 2020-01-01 .. 2025-11-11 (registered)
START = backtest.START_EQUITY
GROUPS = ("crypto", "metals", "fx", "index", "energy")
EV_COLS = ("shock", "tide", "atr1h", "htf_bias", "release_soon")

# ---- the frozen grid (research/HYPOTHESES.md, H42): 6 variants, all counted
VARIANTS = [
    ("base", {"trust_eta": 0.2, "trust_floor": 0.02}),
    ("f05", {"trust_eta": 0.2, "trust_floor": 0.05}),
    ("f08", {"trust_eta": 0.2, "trust_floor": 0.08}),
    ("e10", {"trust_eta": 0.1, "trust_floor": 0.02}),
    ("e05", {"trust_eta": 0.05, "trust_floor": 0.02}),
    ("e10f05", {"trust_eta": 0.1, "trust_floor": 0.05}),
]
NAMES = [k for k, _ in VARIANTS]


# =====================================================================================
# the per-voice odds and grades, once per group (read-only)
# =====================================================================================
def voices_readonly(group, assets, log):
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    t_ms = stores[assets[0]].times_ms()
    for a in assets[1:]:
        assert np.array_equal(stores[a].times_ms(), t_ms)
    full_times = pd.DatetimeIndex(pd.to_datetime(t_ms, unit="ms", utc=True))
    n = int(full_times.searchsorted(pd.Timestamp(CUT, tz="UTC")))      # rows before the cut only
    times = full_times[:n]
    cfg = dict(CFG, assets=tuple(assets), voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        fr = st.frame(full_times)
        ev[a] = pd.DataFrame(dict((c, np.array(fr[c].values[:n])) for c in EV_COLS if c in fr.columns), index=times)
        del fr
        X[a] = st.X()[:n]
        ready[a] = st.ready()[:n]
        b = data.load(a)
        b = b[b.index < pd.Timestamp(CUT, tz="UTC")].reindex(times)       # later bars dropped before grading
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    t0 = time.time()
    fits = os.path.join(FITS, group)
    assert os.path.abspath(fits).startswith(os.path.abspath(OUT))       # never the live fits directory
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n, fits)
    del models
    log("%s: %d rows to %s, voices walked from %s: %d refits, %d from the private cache (%.0fs, %d MB free)" % (
        group, n, str(times[-1])[:16], cfg["birth"], frep["refits"], frep["reused"], time.time() - t0, ex.free_mb()))
    lo = birth_idx
    speaks = {}
    for a in assets:
        Xa = np.asarray(X[a][lo:n])
        speaks[a] = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                              for v in model.VOICE_NAMES], axis=1)
        del Xa
    del X
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "n": n, "lo": lo, "ev": ev, "px": px, "y": y,
            "res": res, "probs": probs, "speaks": speaks, "frep": frep}


def loss_sums(prep):
    """The decayed loss sum S of every voice at every session from lo (model.trust_path's running sum; it does not
    depend on eta or the floor, so it is computed once)."""
    lo, n, cfg = prep["lo"], prep["n"], prep["cfg"]
    V = len(model.VOICE_NAMES)
    arriving = np.zeros((n - lo, V))
    for a in prep["assets"]:
        L = model.losses(prep["probs"][a].arr, prep["y"][a][lo:n])
        idx = np.where(np.isfinite(L[:, 0]))[0]
        r = prep["res"][a][lo:n]
        idx = idx[idx + lo + r[idx] < n]
        np.add.at(arriving, idx + r[idx], L[idx])
    decay = 0.5 ** (1.0 / cfg["trust_halflife"])
    S = np.empty((n - lo, V))
    s = np.zeros(V)
    for k in range(n - lo):
        s = decay * s + arriving[k]
        S[k] = s
    return S


def trust_from(S, eta, floor):
    """model.trust_path's weights from the running sums, for one (eta, floor)."""
    w = np.exp(-eta * (S - S.min(axis=1, keepdims=True)))
    w = np.maximum(w / w.sum(axis=1, keepdims=True), floor)
    return w / w.sum(axis=1, keepdims=True)


# =====================================================================================
# metrics
# =====================================================================================
def odds_skill(prep, odds, lo_k, hi_k):
    """Log-loss and direction hit rates of the mixed odds on calls made in sessions lo_k .. hi_k-1, assets pooled."""
    ll, hit_all, hit5 = [], [], []
    for a in prep["assets"]:
        y, o = prep["y"][a][lo_k:hi_k], odds[a][lo_k:hi_k]
        ok = (y >= 0) & np.isfinite(o[:, 0])
        yi = y[ok].astype(int)
        oo = o[ok]
        ll.append(-np.log(np.clip(oo[np.arange(len(yi)), yi], 1e-9, 1)))
        edge = oo[:, labels.UP] - oo[:, labels.DOWN]
        d = yi > 0
        right = ((edge > 0) & (yi == labels.UP)) | ((edge < 0) & (yi == labels.DOWN))
        hit_all.append(right[d])
        hit5.append(right[d & (np.abs(edge) >= 0.05)])
    ll, ha, h5 = np.concatenate(ll), np.concatenate(hit_all), np.concatenate(hit5)
    return {"graded": int(len(ll)), "logloss": round(float(ll.mean()), 5) if len(ll) else None,
            "hit_pct": round(float(ha.mean() * 100), 2) if len(ha) else None, "dir_calls": int(len(ha)),
            "hit5_pct": round(float(h5.mean() * 100), 2) if len(h5) else None, "dir_calls_5": int(len(h5))}


def trust_stats(tv, voters, idx):
    """Concentration of the voting trust over the sessions idx (rows of tv, voting voices only)."""
    t = tv[idx]
    env = 1.0 / (t ** 2).sum(axis=1)
    top = t.max(axis=1)
    lead = t.argmax(axis=1)
    srt = np.sort(t, axis=1)
    tie = (srt[:, -1] - srt[:, -2]) < 1e-6          # several voices share the top (e.g. all at the floor): no leader
    counts = np.bincount(lead[~tie], minlength=len(voters)) / max(len(lead), 1)
    order = np.argsort(-counts)
    mean_w = t.mean(axis=0)
    return {"env_mean": round(float(env.mean()), 2), "env_median": round(float(np.median(env)), 2),
            "env_p10": round(float(np.percentile(env, 10)), 2), "env_p90": round(float(np.percentile(env, 90)), 2),
            "leader_share_mean": round(float(top.mean()), 3), "pct_time_one_over_50": round(float((top > 0.5).mean() * 100), 1),
            "pct_time_one_over_30": round(float((top > 0.3).mean() * 100), 1),
            "pct_time_no_leader": round(float(tie.mean() * 100), 1),
            "leaders": [[voters[j], round(float(counts[j] * 100), 1)] for j in order[:4] if counts[j] > 0],
            "mean_trust": dict((voters[j], round(float(mean_w[j]), 3)) for j in np.argsort(-mean_w))}


def book_half(prep, a, odds, lo_k, hi_k):
    ev = prep["ev"][a]
    acfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    b = backtest.run_book(prep["px"][a], odds, ev["shock"].values, ev["tide"].values,
                          (acfg["barrier_atr"] * ev["atr1h"]).values, acfg, lo_k, hi_k,
                          bias=ev["htf_bias"].values if "htf_bias" in ev else None,
                          guard=ev["release_soon"].values if "release_soon" in ev else None)
    eq = b["equity"]
    d = ex.daily(eq, prep["times"], lo_k, hi_k)
    tr = b["trades"]
    closed = tr[tr.why_out != "OPEN"]
    e = eq[lo_k:hi_k]
    e = e[np.isfinite(e)]
    st = {"return_pct": round(float(e[-1] / START - 1) * 100, 2) if len(e) else None,
          "sharpe": ex.sharpe(pd.concat([pd.Series([START], index=[d.index[0] - pd.Timedelta(days=1)]), d])),
          "max_dd_pct": ex.max_dd(np.concatenate([[START], e])), "trades": int(len(closed)),
          "win_pct": round(float((closed.pnl_usd > 0).mean() * 100), 1) if len(closed) else None,
          "fees_usd": round(float(closed.fees_usd.sum()), 2)}
    return st, d


def run_group(g, assets, log):
    t0 = time.time()
    prep = voices_readonly(g, assets, log)
    times, n, lo = prep["times"], prep["n"], prep["lo"]
    voters = [v for v in model.VOICE_NAMES if v in prep["cfg"]["voting"]]
    vidx = np.array([model.VOICE_NAMES.index(v) for v in voters])
    votes = np.zeros(len(model.VOICE_NAMES))
    votes[vidx] = 1.0
    S = loss_sums(prep)
    # the baseline's trust must equal the engine's own code exactly
    ref = leanprep.trust_tail(prep["probs"], prep["y"], prep["res"], prep["cfg"], lo, n)
    mine = trust_from(S, prep["cfg"]["trust_eta"], prep["cfg"]["trust_floor"])
    gap = float(np.abs(ref - mine).max())
    assert gap < 1e-9, "baseline trust differs from leanprep.trust_tail by %g" % gap
    del ref, mine
    first = {}
    for a in assets:
        ok = np.isfinite(prep["probs"][a].arr[:, 0, 0])
        first[a] = lo + (int(np.argmax(ok)) if ok.any() else n - lo)
    mid = int(times.searchsorted(pd.Timestamp(MID, tz="UTC")))
    k0 = min(first.values())
    halves = {"first": (max(k0, lo), mid), "second": (mid, n)}
    out = {"group": g, "assets": list(assets), "rows": n, "first_odds": dict((a, str(times[k])[:16]) for a, k in first.items()),
           "split": str(times[mid])[:16], "last_row": str(times[n - 1])[:16], "voters": voters,
           "refits": prep["frep"], "baseline_trust_check_max_gap": gap, "variants": {}, "overall_leader": {}}
    best = S.argmin(axis=1)                             # the voice with the lowest decayed loss of all 59 (any eta)
    for h, (a_k, b_k) in halves.items():
        b = best[a_k - lo:b_k - lo]
        cnt = np.bincount(b, minlength=len(model.VOICE_NAMES)) / max(len(b), 1)
        out["overall_leader"][h] = {
            "pct_time_a_voter": round(float(np.isin(b, vidx).mean() * 100), 1),
            "top": [[model.VOICE_NAMES[j], round(float(cnt[j] * 100), 1)] for j in np.argsort(-cnt)[:5] if cnt[j] > 0]}
    for name, consts in VARIANTS:
        ex.wait_memory(ex.MIN_FREE_RUN, log)
        trust = trust_from(S, consts["trust_eta"], consts["trust_floor"]) * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
        tv = trust[:, vidx]
        odds = {}
        for a in assets:
            w = trust * prep["speaks"][a]
            tot = w.sum(axis=1, keepdims=True)
            w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
            o = np.full((n, 3), np.nan)
            o[lo:] = model.mix(prep["probs"][a].arr, w)
            odds[a] = o
            del w
        r = {"consts": consts}
        for h, (a_k, b_k) in halves.items():
            rows = np.arange(a_k - lo, b_k - lo)
            rr = {"skill": odds_skill(prep, odds, a_k, b_k), "trust": trust_stats(tv, voters, rows), "books": {},
                  "curves": {}}
            for a in assets:
                fa = max(a_k, first[a])
                st, d = book_half(prep, a, odds[a], fa, b_k)
                rr["books"][a] = st
                rr["curves"][a] = {"t": [str(x)[:10] for x in d.index], "eq": [round(float(x), 2) for x in d.values]}
            r[h] = rr
        env = 1.0 / (tv ** 2).sum(axis=1)
        m = pd.Series(env, index=times[lo:n]).resample("1MS").mean()
        r["env_monthly"] = {"t": [str(x)[:7] for x in m.index], "env": [round(float(x), 2) for x in m.values]}
        out["variants"][name] = r
        s2 = r["second"]
        log("%s %-7s 2nd half: logloss %.5f hit %.2f%% ENV %.2f leader>50%% %.0f%% of time; books %s (%.0fs, %d MB free)" % (
            g, name, s2["skill"]["logloss"], s2["skill"]["hit_pct"], s2["trust"]["env_mean"],
            s2["trust"]["pct_time_one_over_50"],
            ", ".join("%s %+.1f%%" % (a, s2["books"][a]["return_pct"]) for a in assets), time.time() - t0, ex.free_mb()))
        del trust, tv, odds
        gc.collect()
    del prep, S
    gc.collect()
    return out


# =====================================================================================
# the report
# =====================================================================================
def pool_curves(curves):
    frame = pd.concat(dict((a, pd.Series(c["eq"], index=pd.to_datetime(c["t"]))) for a, c in curves.items()), axis=1)
    frame = frame.sort_index().ffill().fillna(START)
    tot = frame.sum(axis=1)
    base = START * frame.shape[1]
    return {"markets": int(frame.shape[1]), "return_pct": round(float(tot.iloc[-1] / base - 1) * 100, 2),
            "sharpe": ex.sharpe(pd.concat([pd.Series([base], index=[tot.index[0] - pd.Timedelta(days=1)]), tot])),
            "max_dd_pct": ex.max_dd(np.concatenate([[base], tot.values]))}


def report(log):
    G = {}
    for g in GROUPS:
        p = os.path.join(OUT, "group_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                G[g] = json.load(fh)
    missing = [g for g in GROUPS if g not in G]
    if missing:
        raise SystemExit("missing group results: %s" % missing)
    table = {}
    for name in NAMES:
        t = {}
        for h in ("first", "second"):
            per = {}
            all_curves = {}
            trades = 0
            for g in GROUPS:
                r = G[g]["variants"][name][h]
                per[g] = {"skill": r["skill"], "trust": dict((k, v) for k, v in r["trust"].items() if k != "mean_trust"),
                          "books": r["books"], "pooled_book": pool_curves(r["curves"])}
                all_curves.update(r["curves"])
                trades += sum(b["trades"] for b in r["books"].values())
            pooled = pool_curves(all_curves)
            pooled["trades"] = trades
            t[h] = {"groups": per, "pooled_book": pooled}
        table[name] = t
    # selection: first half only
    def ll(name, h, g):
        return table[name][h]["groups"][g]["skill"]["logloss"]
    sel = {}
    for name in NAMES[1:]:
        wins = sum(1 for g in GROUPS if ll(name, "first", g) < ll("base", "first", g))
        mean_d = float(np.mean([ll(name, "first", g) - ll("base", "first", g) for g in GROUPS]))
        sel[name] = {"groups_better_first": wins, "mean_logloss_gap_first": round(mean_d, 6)}
    chosen = sorted(NAMES[1:], key=lambda k: (-sel[k]["groups_better_first"], sel[k]["mean_logloss_gap_first"]))[0]
    # the pass bar: second half only
    wins2 = [g for g in GROUPS if ll(chosen, "second", g) < ll("base", "second", g)]
    pb, pc = table["base"]["second"]["pooled_book"], table[chosen]["second"]["pooled_book"]
    sharpe_ok = (pc["sharpe"] or -99) >= (pb["sharpe"] or -99)
    dd_ok = (pc["max_dd_pct"] or -100) >= (pb["max_dd_pct"] or -100) - 2.0
    verdict = {"chosen": chosen, "groups_better_second": wins2, "logloss_ok": len(wins2) >= 4,
               "sharpe_ok": bool(sharpe_ok), "dd_ok": bool(dd_ok), "passes": bool(len(wins2) >= 4 and sharpe_ok and dd_ok)}
    for name in NAMES[1:]:
        sel[name]["groups_better_second"] = sum(1 for g in GROUPS if ll(name, "second", g) < ll("base", "second", g))
    res = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "cut": CUT, "mid": MID,
           "variants": dict(VARIANTS), "n_variants": len(VARIANTS), "selection": sel, "verdict": verdict,
           "groups": dict((g, {k: G[g].get(k) for k in ("assets", "rows", "first_odds", "split", "last_row", "voters", "refits",
                                                         "baseline_trust_check_max_gap", "overall_leader")}) for g in GROUPS),
           "mean_trust": dict((name, dict((g, dict((h, G[g]["variants"][name][h]["trust"]["mean_trust"])
                                                    for h in ("first", "second"))) for g in GROUPS)) for name in NAMES),
           "env_monthly": dict((name, dict((g, G[g]["variants"][name]["env_monthly"]) for g in GROUPS)) for name in NAMES),
           "table": table}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    write_md(res, os.path.join(OUT, "study.md"))
    log("chosen %s; verdict %s" % (chosen, verdict))


# Plain-English reading, written AFTER the numbers below were computed (15 Nov 2026, ~09:57 UTC).
CONCLUSIONS = [
    "## Plain-English conclusions (written after the results)", "",
    "- **Prediction: every balanced variant is a little better, and only a little.** In the second half all 5 "
    "challengers have lower log-loss than the live setting in all 5 groups (first half: 4 of 5; fx was the "
    "exception for every challenger). The gains are tiny: 0.00004 to 0.0011 nats, i.e. 0.005% to 0.15% of the "
    "log-loss. Direction hit rate on all up/down calls stays within about half a point of 50% everywhere "
    "(crypto 51.3-51.7% for every variant). Spreading the say is a mild smoothing, not a new skill.",
    "- **Calls with a 5-point edge:** a flatter blend makes far fewer of them (crypto second half 30,701 -> 18,289 "
    "for `f08`) and those it makes are right a bit more often in crypto (51.3% -> 53.6%; `e05` 55.3% on 16,646). "
    "In metals and the S&P the counts fall to a few dozen or one, so those hit rates mean nothing.",
    "- **Trading: no improvement.** The main book barely depends on the blend: gold, silver and the S&P trade identically under all 6 "
    "variants, and USDJPY identically under all 5 challengers, because most of their "
    "positions come from the higher-timeframe bias, forced entries and long holds, not from the size of the edge. "
    "Where the book does move (crypto, oil) it moves a lot and in no steady direction: ETH's second half is +124% "
    "under the live setting and -6% to -17% under every challenger, while BTC is better under every challenger. "
    "Pooled over 8 markets in the second half the chosen `f08` has Sharpe 0.95 vs 1.06, so it fails the bar; `e10` "
    "is the only challenger slightly above the live setting (1.10), and it was not chosen. First half the order was "
    "different again (`e05`/`e10f05` best). The book differences look like path noise from a few large holds.",
    "- **How concentrated trust has been in history (live setting):** crypto's voting trust had one voice above "
    "50% for 17% (first half) and 19% (second half) of the time; mean effective number of voices 8.4 of 13. Energy "
    "32% then 23% (mean 6.6-6.9 voices of 11), metals 21% then 4%, fx 7% then 0%, the S&P 0%. The live picture (levels ~79%, the rest at the floor) is "
    "more concentrated than the development history's average, and it falls after the development cut, so this "
    "study does not cover it.",
    "- **Why the floor variants look 'flat':** the Hedge leader is picked among all 59 voices before the voting "
    "cards are picked out, and in most groups the lowest-loss voice is a NON-voting voice 45-72% of the time (e.g. "
    "`all` and `ichimoku` in crypto). Then the voters often all sit at the floor and the vote is equal-weighted "
    "('No single leader' column). A floor of 0.08 makes this the usual state in the second half (50-94% of the time).",
    "- **Bottom line:** no pass. A more balanced blend gives a consistent but very small log-loss gain and no "
    "trading gain on this history; nothing here argues for changing `trust_eta` or `trust_floor`.", ""]


def _f(v, pat="%+.2f"):
    return "-" if v is None else pat % v


def write_md(res, path):
    T, V = res["table"], res["verdict"]
    ch = V["chosen"]
    L = ["# H42: a more balanced trust blend for the voices (IN-SAMPLE, development data only)", "",
         "Written by `research/trust_study.py` on %s. Rows before %s 00:00 UTC only; halves split at %s 00:00 UTC "
         "(first = selection, second = confirmation). Odds formed as the live step forms them (voices walked forward "
         "weekly from 2020-01-01, the group's voting cards, the silent-voice mask); only `trust_eta` and `trust_floor` "
         "change. Main book per market from $10,000 at the start of each half (flat), the asset's fee, leverage cap and "
         "fill delay as live; the live-only total-risk cap across books is not applied. %d variants (1 baseline + %d "
         "challengers). Paper only." % (res["written_utc"], res["cut"], res["mid"], res["n_variants"], res["n_variants"] - 1), "",
         "## Verdict", "",
         "Chosen on the first half (registered rule: most groups with log-loss below base, ties by mean gap): **`%s`** "
         "(%s)." % (ch, json.dumps(res["variants"][ch])), "",
         "Second-half pass bar: log-loss below base in >= 4 of 5 groups: **%s** (%d: %s); pooled 8-market book Sharpe "
         "not lower than base: **%s** (%s vs %s); pooled max drawdown no worse by more than 2 points: **%s** (%s%% vs %s%%)." % (
             "yes" if V["logloss_ok"] else "no", len(V["groups_better_second"]), ", ".join(V["groups_better_second"]) or "none",
             "yes" if V["sharpe_ok"] else "no", _f(T[ch]["second"]["pooled_book"]["sharpe"], "%.2f"),
             _f(T["base"]["second"]["pooled_book"]["sharpe"], "%.2f"), "yes" if V["dd_ok"] else "no",
             _f(T[ch]["second"]["pooled_book"]["max_dd_pct"], "%.2f"), _f(T["base"]["second"]["pooled_book"]["max_dd_pct"], "%.2f")), "",
         "**%s**" % ("PASS (in-sample; a reason to ask the owner, not proof)." if V["passes"] else "NO PASS."), ""] + CONCLUSIONS + [
         "## Selection table", "", "| Variant | eta | floor | Groups below base, 1st half | Mean log-loss gap, 1st half | "
         "Groups below base, 2nd half |", "|---|---|---|---|---|---|"]
    for name in NAMES[1:]:
        s = res["selection"][name]
        L.append("| `%s` | %s | %s | %d/5 | %+.5f | %d/5 |" % (name, res["variants"][name]["trust_eta"],
                                                           res["variants"][name]["trust_floor"], s["groups_better_first"],
                                                           s["mean_logloss_gap_first"], s["groups_better_second"]))
    for h, title in (("first", "First half (selection)"), ("second", "Second half (confirmation)")):
        L += ["", "## %s" % title, "", "### Odds and trust per group", "",
              "| Group | Variant | Log-loss | vs base | Hit % (all up/down) | Hit % (edge >= 5) | Calls (edge >= 5) | "
              "ENV mean | ENV p10-p90 | Leader share | Time one voice > 50% | No single leader | Most often leading |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in GROUPS:
            b = T["base"][h]["groups"][g]["skill"]["logloss"]
            for name in NAMES:
                r = T[name][h]["groups"][g]
                s, t = r["skill"], r["trust"]
                L.append("| %s | `%s` | %.5f | %+.5f | %s | %s | %d | %.2f | %.2f-%.2f | %.2f | %.1f%% | %.1f%% | %s |" % (
                    g, name, s["logloss"], s["logloss"] - b, _f(s["hit_pct"], "%.2f"), _f(s["hit5_pct"], "%.2f"),
                    s["dir_calls_5"], t["env_mean"], t["env_p10"], t["env_p90"], t["leader_share_mean"],
                    t["pct_time_one_over_50"], t.get("pct_time_no_leader", 0.0),
                    ", ".join("%s %.0f%%" % (v, p) for v, p in t["leaders"][:2]) or "-"))
        L += ["", "### Main book per group (markets pooled) and all 8 markets", "",
              "| Group | Variant | Return | Sharpe | Max DD | Trades | Per market (return / Sharpe / DD / trades) |",
              "|---|---|---|---|---|---|---|"]
        for g in GROUPS + ("ALL",):
            for name in NAMES:
                if g == "ALL":
                    p = T[name][h]["pooled_book"]
                    L.append("| **all 8** | `%s` | %s%% | %s | %s%% | %d | |" % (
                        name, _f(p["return_pct"]), _f(p["sharpe"], "%.2f"), _f(p["max_dd_pct"], "%.2f"), p["trades"]))
                    continue
                r = T[name][h]["groups"][g]
                p = r["pooled_book"]
                L.append("| %s | `%s` | %s%% | %s | %s%% | %d | %s |" % (
                    g, name, _f(p["return_pct"]), _f(p["sharpe"], "%.2f"), _f(p["max_dd_pct"], "%.2f"),
                    sum(b["trades"] for b in r["books"].values()),
                    "; ".join("%s %s%% / %s / %s%% / %d" % (a, _f(b["return_pct"], "%+.1f"), _f(b["sharpe"], "%.2f"),
                                                            _f(b["max_dd_pct"], "%.1f"), b["trades"]) for a, b in r["books"].items())))
    L += ["", "## Data notes", ""]
    for g, m in res["groups"].items():
        L.append("- %s: %d rows to %s UTC; first odds %s; split row %s; voters %s; refits %s; baseline trust equals "
                 "`leanprep.trust_tail` (max gap %.1e)." % (g, m["rows"], m["last_row"], m["first_odds"], m["split"],
                                                           ", ".join(m["voters"]), m["refits"], m["baseline_trust_check_max_gap"]))
    L += ["", "Which of ALL 59 voices has the lowest decayed loss (the Hedge leader before the voting cards are picked "
          "out; the same for every variant, since only eta and the floor change):", ""]
    for g, m in res["groups"].items():
        ol = m.get("overall_leader") or {}
        L.append("- %s: %s" % (g, "; ".join("%s half: a voting card %.0f%% of the time, most often %s" % (
            h, v["pct_time_a_voter"], ", ".join("%s %.0f%%" % (n, p) for n, p in v["top"][:3])) for h, v in ol.items())))
    L += ["", "ENV = effective number of voices, 1 / sum(w^2) of the voting trust (before the per-asset silent-voice "
          "mask). Sharpe on daily marked equity, sqrt(365). Pooled curves sum the markets' daily equity.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.report:
        report(log)
        return
    ex.below_normal()
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    todo = [args.group] if args.group else list(GROUPS)
    for g in todo:
        ex.acquire("trust_study %s (H42)" % g, log)
        try:
            ex.wait_memory(ex.MIN_FREE_START, log)
            r = run_group(g, groups[g], log)
            with open(os.path.join(OUT, "group_%s.json" % g), "w", encoding="utf-8") as fh:
                json.dump(r, fh)
        finally:
            ex.release()
        gc.collect()


if __name__ == "__main__":
    main()
