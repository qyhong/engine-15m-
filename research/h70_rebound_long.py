# -*- coding: utf-8 -*-
"""H70: BTC and ETH, a long on a sharp rebound out of an oversold state, in three sealed stages. Research only;
registered in research/HYPOTHESES.md (H70) before this file existed. Reads the evidence store and cached fits; changes
nothing in the engine.

    python research/h70_rebound_long.py --stage 1 --fits-dir <fits>   discovery, data cut at 2023-06-07 23:45
    python research/h70_rebound_long.py --stage 2 --fits-dir <fits>   needs selection_stage1.json; only those candidates
    python research/h70_rebound_long.py --stage 3 --fits-dir <fits>   needs selection_stage2.json; only its survivors
    python research/h70_rebound_long.py --report                      merge into results.json + report.md

Each stage cuts every input at its own period's end (h59.prep_cut) before anything is computed.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, indicators as ind, labels, shadows  # noqa: E402
from engine15.sources import structure  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h70_rebound_long")
COINS = ["BTCUSDT", "ETHUSDT"]
OTHERS = [("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]), ("energy", ["WTI", "BRENT"])]
FINAL_END = "2026-11-21 13:45"
PERIODS = {1: (None, "2023-06-07 23:45"), 2: ("2023-06-08 00:00", "2025-11-10 23:45"), 3: ("2025-11-11 00:00", FINAL_END)}
WIN = 96                 # bars k+1 .. k+96
LOOK = 16                # oversold within k-15..k; stop at the low of k-15..k
B, SEED = 5000, 20261122
MIN1, MIN2, MIN3 = 150, 80, 30
OVERSOLD, TRIGGERS, CONFS = ("O1", "O2", "O3"), ("R1", "R2", "R3"), ("C0", "C1")
CANDS = ["%s-%s-%s" % (o, r, c) for o in OVERSOLD for r in TRIGGERS for c in CONFS]


# ----------------------------------------------------------------------------------------------- data
def group_end(g, assets, end):
    """The group's last stored session at or before `end`."""
    from engine15 import evcache
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, g, assets[0]))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (g, assets[0]))
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
    return str(full[k - 1])[:16]


def load_group(g, assets, end, fits_root, log=print):
    import h59_half_be as h59
    return h59.prep_cut(g, assets, os.path.join(fits_root, g), group_end(g, assets, end), log=log)


def readings(prep, a):
    """Every reading H70 uses, as known at each bar's close. -> dict of arrays + where each came from."""
    times, px, ev, odds = prep["times"], prep["px"][a], prep["ev"][a], prep["odds"][a]
    n = len(times)
    df = pd.DataFrame({k: px[k] for k in ("open", "high", "low", "close")}, index=times)
    df["volume"], df["taker_buy"] = 0.0, 0.0
    src = {}

    def stored(col, fallback):
        if ev is not None and col in ev and np.isfinite(np.asarray(ev[col].values, float)).any():
            src[col] = "store"
            return np.asarray(ev[col].values, float)
        src[col] = "computed"
        return np.asarray(fallback(), float)

    h1 = data.resample(df, "1h")
    atr15 = stored("atr15", lambda: ind.atr_wilder(df).values)
    atr1h = stored("atr1h", lambda: data.htf_on_15(df, "1h", ind.atr_wilder(h1)).values)
    ema50 = stored("bias_ema50_1h_px", lambda: data.htf_on_15(
        df, "1h", h1["close"].ewm(span=50, adjust=False, min_periods=50).mean()).values)
    swhi = stored("sw_hi_15m", lambda: structure.swings(px["high"], px["low"], structure.SWING_K["15m"])[1])
    rsi1h = data.htf_on_15(df, "1h", ind.rsi(h1["close"], 14)).values.astype(float)
    c = px["close"]
    ema20 = pd.Series(c).ewm(span=20, adjust=False).mean().values
    ref = times - pd.Timedelta(hours=24)
    j = times.searchsorted(ref, side="right") - 1
    ret24 = np.where(j >= 0, c / c[np.maximum(j, 0)] - 1.0, np.nan)
    lead = odds[:, labels.UP] - odds[:, labels.DOWN]
    low16 = pd.Series(px["low"]).rolling(LOOK, min_periods=LOOK).min().values
    return {"atr15": atr15, "atr1h": atr1h, "ema50": ema50, "swhi": swhi, "rsi1h": rsi1h, "ema20": ema20,
            "ret24": ret24, "lead": lead, "low16": low16, "n": n, "src": src}


def masks(px, rd):
    """-> {O1..O3: oversold within the last 16 bars}, {R1..R3: trigger onset}, {C0, C1}."""
    c = px["close"]
    with np.errstate(invalid="ignore"):
        o1 = c <= rd["ema50"] - 3.0 * rd["atr1h"]
        o2 = rd["ret24"] <= -0.06
        rs = pd.Series(np.where(np.isfinite(rd["rsi1h"]), rd["rsi1h"], np.inf)).rolling(32, min_periods=1).min().values
        o3 = rs <= 30.0
        r1 = c > rd["ema20"]
        r2 = c >= rd["low16"] + 1.5 * rd["atr15"]
        r3 = c > rd["swhi"]
        c1 = rd["lead"] >= -0.05

    def recent(m):
        return pd.Series(m.astype(float)).rolling(LOOK, min_periods=1).max().values > 0

    def onset(m):
        prev = np.concatenate([[True], m[:-1]])
        return m & ~prev
    O = {"O1": recent(o1), "O2": recent(o2), "O3": recent(o3)}
    R = {"R1": onset(r1), "R2": onset(r2), "R3": onset(r3)}
    C = {"C0": np.ones(len(c), bool), "C1": np.asarray(c1, bool)}
    return O, R, C


# ----------------------------------------------------------------------------------------------- the trade
def outcomes(px, rd, ks, fee):
    """The registered trade decided at each close k in `ks` (k+96 must exist). -> dict of arrays per k:
    status (0 ok, 1 entry <= stop, 2 stop < 0.3%, 3 stop > 8%, 4 no reading), r (net R), pct (net), xbar (exit bar)."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    m = len(ks)
    st = np.zeros(m, int)
    r = np.full(m, np.nan)
    pct = np.full(m, np.nan)
    xb = np.full(m, -1, int)
    P = o[ks + 1]
    S = rd["low16"][ks] - 0.25 * rd["atr15"][ks]
    R = P - S
    bad = ~(np.isfinite(P) & np.isfinite(S))
    st[bad] = 4
    with np.errstate(invalid="ignore"):
        st[(st == 0) & (R <= 0)] = 1
        st[(st == 0) & (R / P < 0.003)] = 2
        st[(st == 0) & (R / P > 0.08)] = 3
    ok = np.flatnonzero(st == 0)
    J = np.arange(WIN)
    for s in range(0, len(ok), 20000):
        q = ok[s:s + 20000]
        k = ks[q]
        idx = k[:, None] + 1 + J[None, :]
        Pq, Sq, Rq = P[q], S[q], R[q]
        L, H, O, C = l[idx], h[idx], o[idx], c[idx]

        def first(mask):
            return np.where(mask.any(1), mask.argmax(1), WIN)
        js = first(L <= Sq[:, None])
        j1 = first(H >= (Pq + Rq)[:, None])
        t2 = H >= (Pq + 2.5 * Rq)[:, None]
        after = J[None, :] > j1[:, None]
        jb = first((L <= Pq[:, None]) & after)
        j2 = first(t2 & (J[None, :] >= j1[:, None]))
        rows = np.arange(len(q))
        A = (js <= j1) & (js < WIN)
        Bm = (~A) & (j1 < WIN)
        # A: all out at the stop (or the open below it)
        fillA = np.minimum(O[rows, np.minimum(js, WIN - 1)], Sq)
        # B: half at +1R, the rest at +2.5R / the entry / the last close
        T1, T2 = Pq + Rq, Pq + 2.5 * Rq
        same = j2 == j1
        be_first = (~same) & (jb < WIN) & (jb <= j2)
        t2_first = (~same) & (~be_first) & (j2 < WIN)
        restX = np.where(same | t2_first, T2,
                         np.where(be_first, np.minimum(O[rows, np.minimum(jb, WIN - 1)], Pq), C[:, -1]))
        restJ = np.where(same, j1, np.where(be_first, jb, np.where(t2_first, j2, WIN - 1)))
        # C: neither: all out at the last close
        lastC = C[:, -1]
        X_full = np.where(A, fillA, lastC)
        rq = np.where(Bm, 0.5 * 1.0 + 0.5 * (restX - Pq) / Rq, (X_full - Pq) / Rq)
        fees = np.where(Bm, fee * (Pq + 0.5 * T1 + 0.5 * restX), fee * (Pq + X_full)) / Rq
        pq = np.where(Bm, 0.5 * (T1 / Pq - 1) + 0.5 * (restX / Pq - 1) - fee * (1 + 0.5 * T1 / Pq + 0.5 * restX / Pq),
                      X_full / Pq - 1 - fee * (1 + X_full / Pq))
        jx = np.where(A, js, np.where(Bm, restJ, WIN - 1))
        r[q] = rq - fees
        pct[q] = pq
        xb[q] = k + 1 + jx
    return {"status": st, "r": r, "pct": pct, "xbar": xb}


def period_range(times, lo, stage, cont=False):
    """Deciding bars k of a stage whose 96-bar window ends inside the period (cont: the whole history)."""
    n = len(times)
    if cont:
        a, z = 0, n - 1
    else:
        s, e = PERIODS[stage]
        a = 0 if s is None else int(times.searchsorted(pd.Timestamp(s, tz="UTC")))
        z = int(times.searchsorted(pd.Timestamp(e, tz="UTC"), side="right")) - 1
    k0 = max(a, lo + 1, LOOK)
    k1 = z - WIN
    return np.arange(k0, k1 + 1) if k1 >= k0 else np.arange(0)


def months_of(times, ks):
    t = times[ks]
    return np.asarray(t.year * 100 + t.month)


def market_frame(prep, a, stage, cont=False):
    """Everything about one market in one stage: readings, masks, all-bar outcomes, monthly baseline."""
    times, px = prep["times"], prep["px"][a]
    ok = np.isfinite(prep["odds"][a][:, 0])
    lo = max(int(np.argmax(ok)) if ok.any() else len(times), prep["birth_idx"], 1)
    rd = readings(prep, a)
    O, R, C = masks(px, rd)
    ks = period_range(times, lo, stage, cont)
    fee = shadows.asset_cfg(a, dict(prep["cfg"]))["cost_side"]
    out = outcomes(px, rd, ks, fee)
    mo = months_of(times, ks)
    good = out["status"] == 0
    base = {}
    for m_ in np.unique(mo):
        sel = good & (mo == m_)
        base[int(m_)] = float(np.mean(out["r"][sel])) if sel.any() else np.nan
    return {"asset": a, "times": times, "px": px, "lo": lo, "rd": rd, "O": O, "R": R, "C": C, "ks": ks, "out": out,
            "months": mo, "base": base, "fee": fee, "allmonths": sorted(base),
            "baseline_all": float(np.nanmean(out["r"][good])) if good.any() else None,
            "eligible_bars": int(good.sum())}


def trades_of(fr, cand):
    """The candidate's trades on one market: one at a time, events at their onset."""
    o, r_, c_ = cand.split("-")
    ks = fr["ks"]
    if not len(ks):
        return [], {}
    fire = fr["O"][o][ks] & fr["R"][r_][ks] & fr["C"][c_][ks]
    pos = np.flatnonzero(fire)
    out, skips, last = [], {"events": int(len(pos)), "while_open": 0, "entry_at_or_below_stop": 0,
                            "stop_under_0.3pct": 0, "stop_over_8pct": 0, "no_reading": 0}, -1
    names = {1: "entry_at_or_below_stop", 2: "stop_under_0.3pct", 3: "stop_over_8pct", 4: "no_reading"}
    for p in pos:
        k = int(ks[p])
        if k < last:
            skips["while_open"] += 1
            continue
        s = int(fr["out"]["status"][p])
        if s:
            skips[names[s]] += 1
            continue
        m_ = int(fr["months"][p])
        rr = float(fr["out"]["r"][p])
        out.append({"asset": fr["asset"], "k": k, "time": str(fr["times"][k])[:16], "month": m_, "r": rr,
                    "pct": float(fr["out"]["pct"][p]), "xbar": int(fr["out"]["xbar"][p]),
                    "bars": int(fr["out"]["xbar"][p] - k), "excess": rr - fr["base"][m_]})
        last = int(fr["out"]["xbar"][p])
    skips["entries_window_past_period_end"] = "not taken by construction (deciding bars limited to period end - 96)"
    return out, skips


# ----------------------------------------------------------------------------------------------- statistics
def draws(months):
    rng = np.random.default_rng(SEED)
    return rng.integers(0, len(months), size=(B, len(months)))


def boot(trades, months, D, key):
    """Month-clustered bootstrap of the mean of `key` over trades. -> (observed, lo95, hi95, one-sided p for > 0)."""
    if not trades:
        return None
    mi = dict((m_, i) for i, m_ in enumerate(months))
    S, N = np.zeros(len(months)), np.zeros(len(months))
    for t in trades:
        i = mi[t["month"]]
        S[i] += t[key]
        N[i] += 1
    obs = S.sum() / N.sum()
    ss, nn = S[D].sum(1), N[D].sum(1)
    v = ss[nn > 0] / nn[nn > 0]
    p = (1 + np.sum(v - obs >= obs)) / (len(v) + 1)
    return {"obs": float(obs), "lo": float(np.percentile(v, 2.5)), "hi": float(np.percentile(v, 97.5)), "p": float(p)}


def summary(trades, months, D):
    if not trades:
        return {"n": 0}
    r = np.array([t["r"] for t in trades])
    srt = sorted(trades, key=lambda t: t["time"])
    run = best = 0
    for t in srt:
        run = run + 1 if t["r"] < 0 else 0
        best = max(best, run)
    cum = np.cumsum([t["r"] for t in srt])
    dd = float(np.min(cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:])) if len(cum) else 0.0
    return {"n": int(len(r)), "won_pct": float((r > 0).mean() * 100), "mean_r": boot(trades, months, D, "r"),
            "sum_r": float(r.sum()), "excess": boot(trades, months, D, "excess"),
            "median_bars": float(np.median([t["bars"] for t in trades])),
            "mean_pct": float(np.mean([t["pct"] for t in trades]) * 100),
            "longest_losing_run": int(best), "deepest_fall_r": dd}


def evaluate(frames, cands, stage):
    months = sorted(set(m_ for fr in frames.values() for m_ in fr["allmonths"]))
    D = draws(months)
    res = {}
    for cand in cands:
        per, alltr, skips = {}, [], {}
        for a, fr in frames.items():
            tr, sk = trades_of(fr, cand)
            alltr += tr
            skips[a] = sk
            ma = fr["allmonths"]
            per[a] = summary(tr, ma, draws(ma)) if tr else {"n": 0}
        res[cand] = {"pooled": summary(alltr, months, D), "per_coin": per, "skips": skips}
    return res, months


def stage1_select(res):
    q = []
    for cand, v in res.items():
        p = v["pooled"]
        if p["n"] < MIN1 or p["mean_r"]["obs"] <= 0 or p["excess"]["obs"] <= 0 or p["excess"]["lo"] <= 0:
            continue
        if not all(v["per_coin"][a].get("n") and v["per_coin"][a]["excess"]["obs"] > 0 for a in COINS):
            continue
        q.append((p["excess"]["obs"], cand))
    q.sort(reverse=True)
    return [c for _, c in q], [c for _, c in q[:3]]


def stage2_pass(res, m):
    out = {}
    for cand, v in res.items():
        p = v["pooled"]
        why = []
        if p["n"] < MIN2:
            why.append("fewer than %d trades" % MIN2)
        if p["n"] and p["mean_r"]["obs"] <= 0:
            why.append("mean R not above zero")
        if p["n"] and (p["excess"]["obs"] <= 0 or p["excess"]["p"] >= 0.05 / m):
            why.append("excess not above zero at p < %.4f" % (0.05 / m))
        for a in COINS:
            if not v["per_coin"][a].get("n") or v["per_coin"][a]["excess"]["obs"] <= 0:
                why.append("excess not positive on %s" % a)
        out[cand] = {"passes": not why, "why_not": why}
    return out


# ----------------------------------------------------------------------------------------------- stages
def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=float)


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        raise SystemExit("REFUSED: %s does not exist; the stage before has not selected anything yet" % name)
    with open(p) as fh:
        return json.load(fh)


def strip(res):
    return res


def run_stage(stage, fits_root, log=print):
    t0 = time.time()
    if stage == 1:
        cands = CANDS
    elif stage == 2:
        sel = load("selection_stage1.json")
        cands = sel["selected"]
    else:
        sel = load("selection_stage2.json")
        cands = sel["passed"]
    for c in cands:
        if c not in CANDS:
            raise SystemExit("REFUSED: unknown candidate %s" % c)
    if not cands:
        msg = {1: "", 2: "nothing to confirm (Stage 1 selected none)", 3: "nothing passed Stage 2; the holdout stays sealed"}[stage]
        save("stage%d.json" % stage, {"stage": stage, "skipped": msg})
        log("stage %d not run: %s" % (stage, msg))
        return
    end = PERIODS[stage][1]
    prep = load_group("crypto", COINS, end, fits_root, log=log)
    frames = dict((a, market_frame(prep, a, stage)) for a in COINS)
    res, months = evaluate(frames, cands, stage)
    meta = {"stage": stage, "period": PERIODS[stage], "data_cut": str(prep["times"][-1])[:16], "candidates": cands,
            "months": len(months), "bootstrap": {"draws": B, "seed": SEED},
            "per_coin": dict((a, {"first_decided": str(fr["times"][fr["lo"]])[:16],
                                  "first_bar": str(fr["times"][fr["ks"][0]])[:16] if len(fr["ks"]) else None,
                                  "last_bar": str(fr["times"][fr["ks"][-1]])[:16] if len(fr["ks"]) else None,
                                  "eligible_bars": fr["eligible_bars"], "baseline_mean_r_all_bars": fr["baseline_all"],
                                  "reading_source": fr["rd"]["src"], "fee_side": fr["fee"]}) for a, fr in frames.items())}
    out = dict(meta, results=res)
    if stage == 1:
        qual, chosen = stage1_select(res)
        out["qualified"] = qual
        save("stage1.json", out)
        save("selection_stage1.json", {"selected": chosen, "qualified": qual, "rule": "registered H70 Stage 1"})
    elif stage == 2:
        pr = stage2_pass(res, len(cands))
        out["pass"] = pr
        out["bonferroni_alpha"] = 0.05 / len(cands)
        save("stage2.json", out)
        save("selection_stage2.json", {"passed": [c for c in cands if pr[c]["passes"]], "rule": "registered H70 Stage 2"})
    else:
        for c in cands:
            p = res[c]["pooled"]
            res[c]["holds"] = bool(p["n"] >= MIN3 and p["mean_r"]["obs"] > 0 and p["excess"]["obs"] > 0)
        out["descriptive"] = descriptive(prep, frames, cands, fits_root, log)
        save("stage3.json", out)
    log("stage %d done in %.0fs" % (stage, time.time() - t0))
    for c in cands:
        p = res[c]["pooled"]
        if p["n"]:
            log("%s: n=%d meanR %+.3f excess %+.3f [%+.3f, %+.3f] p=%.4f" % (
                c, p["n"], p["mean_r"]["obs"], p["excess"]["obs"], p["excess"]["lo"], p["excess"]["hi"], p["excess"]["p"]))
        else:
            log("%s: no trades" % c)


def descriptive(prep, frames3, cands, fits_root, log):
    """Only for Stage 2 survivors: rallies, frequency, what the book held, other six markets."""
    import h59_half_be as h59
    times = prep["times"]
    n = len(times)
    out = {"rallies": {}, "frequency": {}, "book_at_entry": {}, "other_markets": {}}
    cont = dict((a, market_frame(prep, a, 3, cont=True)) for a in COINS)
    books = {}
    for a in COINS:
        fr = cont[a]
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        books[a] = h59.run_book("b_targets", prep, a, fr["lo"], n, aux)
    eps = {}
    for a in COINS:
        c, held = prep["px"][a]["close"], books[a]["held"]
        t, lst = cont[a]["lo"], []
        while t + WIN < n:
            if held[t] == -1 and c[t + WIN] / c[t] - 1.0 >= 0.05:
                lst.append(t)
                t += WIN
            else:
                t += 1
        eps[a] = lst
    for cand in cands:
        tr = dict((a, trades_of(cont[a], cand)[0]) for a in COINS)
        hit, hrs, rr = 0, [], []
        for a in COINS:
            ks = np.array([x["k"] for x in tr[a]], int)
            for t in eps[a]:
                inside = [x for x in tr[a] if t < x["k"] <= t + WIN]
                if inside:
                    hit += 1
                    hrs.append((inside[0]["k"] - t) * 0.25)
                    rr += [x["r"] for x in inside]
        total_eps = sum(len(v) for v in eps.values())
        out["rallies"][cand] = {"episodes": total_eps, "episodes_per_coin": dict((a, len(v)) for a, v in eps.items()),
                                "fired_inside": hit, "fired_inside_pct": hit / total_eps * 100 if total_eps else None,
                                "median_hours_after_start": float(np.median(hrs)) if hrs else None,
                                "trades_inside": len(rr), "mean_r_inside": float(np.mean(rr)) if rr else None,
                                "sum_r_inside": float(np.sum(rr)) if rr else None,
                                "won_pct_inside": float(np.mean(np.array(rr) > 0) * 100) if rr else None}
        fq = {}
        for a in COINS:
            yrs = (times[n - 1] - times[cont[a]["lo"]]).days / 365.25
            fq[a] = {"trades": len(tr[a]), "per_year": len(tr[a]) / yrs if yrs > 0 else None,
                     "median_bars_held": float(np.median([x["bars"] for x in tr[a]])) if tr[a] else None,
                     "mean_r": float(np.mean([x["r"] for x in tr[a]])) if tr[a] else None}
        out["frequency"][cand] = fq
        be = {}
        for a in COINS:
            held, eq = books[a]["held"], books[a]["equity"]
            for x in tr[a]:
                k = x["k"]
                w = {1: "long", -1: "short", 0: "flat"}[int(held[k])]
                d = be.setdefault(w, {"n": 0, "book_pct": [], "cand_pct": [], "cand_r": []})
                d["n"] += 1
                d["book_pct"].append(float((eq[min(k + WIN, n - 1)] / eq[k] - 1) * 100))
                d["cand_pct"].append(x["pct"] * 100)
                d["cand_r"].append(x["r"])
        out["book_at_entry"][cand] = dict((w, {"n": d["n"], "book_mean_pct_24h": float(np.mean(d["book_pct"])),
                                               "book_median_pct_24h": float(np.median(d["book_pct"])),
                                               "candidate_mean_pct": float(np.mean(d["cand_pct"])),
                                               "candidate_mean_r": float(np.mean(d["cand_r"]))}) for w, d in be.items())
    for g, assets in OTHERS:
        try:
            pg = load_group(g, assets, FINAL_END, fits_root, log=log)
        except Exception as e:                                         # descriptive only: say it, carry on
            out["other_markets"][g] = {"error": str(e)}
            continue
        for a in assets:
            row = {}
            for st in (1, 2, 3):
                fr = market_frame(pg, a, st)
                for cand in cands:
                    tr, _ = trades_of(fr, cand)
                    ma = fr["allmonths"]
                    s = summary(tr, ma, draws(ma)) if tr and ma else {"n": 0}
                    row.setdefault(cand, {})["stage%d" % st] = {
                        "n": s["n"], "mean_r": s["mean_r"]["obs"] if s["n"] else None,
                        "excess": s["excess"]["obs"] if s["n"] else None,
                        "excess_lo": s["excess"]["lo"] if s["n"] else None, "excess_hi": s["excess"]["hi"] if s["n"] else None}
            out["other_markets"][a] = row
        del pg
    return out


# ----------------------------------------------------------------------------------------------- report
def _b(x):
    return "-" if not x else "%+.3f [%+.3f, %+.3f]" % (x["obs"], x["lo"], x["hi"])


def _row(c, v):
    p = v["pooled"]
    if not p.get("n"):
        return "| %s | 0 | | | | | | |" % c
    pc = v["per_coin"]
    ex = lambda a: "%+.3f (%d)" % (pc[a]["excess"]["obs"], pc[a]["n"]) if pc[a].get("n") else "- (0)"   # noqa: E731
    return "| %s | %d | %.0f%% | %s | %+.1f | %s | %.4f | %s | %s |" % (
        c, p["n"], p["won_pct"], _b(p["mean_r"]), p["sum_r"], _b(p["excess"]), p["excess"]["p"], ex("BTCUSDT"), ex("ETHUSDT"))


HDR = ["| Candidate | Trades | Won | Mean R [95%] | Sum R | Excess over baseline [95%] | p (excess>0) | BTC excess (n) | ETH excess (n) |",
       "|---|---|---|---|---|---|---|---|---|"]


def report():
    res = {}
    for s in (1, 2, 3):
        p = os.path.join(OUT, "stage%d.json" % s)
        if os.path.exists(p):
            with open(p) as fh:
                res["stage%d" % s] = json.load(fh)
    for s in (1, 2):
        p = os.path.join(OUT, "selection_stage%d.json" % s)
        if os.path.exists(p):
            with open(p) as fh:
                res["selection_stage%d" % s] = json.load(fh)
    save("results.json", res)
    L = ["# H70: a long on a sharp rebound out of an oversold state (BTC and ETH, three sealed stages)", "",
         "Registered in research/HYPOTHESES.md before any number. R after fees (0.10% a side). Excess = R minus the mean R",
         "of the same trade entered at every eligible bar of the same coin and calendar month. Intervals and p-values:",
         "month-clustered bootstrap, %d draws, seed %d. No result here is a proven edge." % (B, SEED), ""]
    for s in (1, 2, 3):
        st = res.get("stage%d" % s)
        if not st:
            continue
        L += ["## Stage %d (%s to %s)" % (s, st.get("period", ["", ""])[0] or "first decided session", st.get("period", ["", ""])[1]), ""]
        if st.get("skipped"):
            L += ["Not run: %s." % st["skipped"], ""]
            continue
        for a, m in st["per_coin"].items():
            L.append("- %s: deciding bars %s to %s, %d eligible bars, all-bar baseline mean R %+.3f; readings: %s." % (
                a, m["first_bar"], m["last_bar"], m["eligible_bars"], m["baseline_mean_r_all_bars"] or 0,
                ", ".join("%s %s" % kv for kv in m["reading_source"].items())))
        L += [""] + HDR
        for c, v in st["results"].items():
            L.append(_row(c, v))
        if s == 1:
            sel = res.get("selection_stage1", {})
            L += ["", "Qualified by the Stage 1 rule: %s. Selected: %s." % (", ".join(sel.get("qualified", [])) or "none",
                                                                          ", ".join(sel.get("selected", [])) or "none")]
        if s == 2:
            L += ["", "Bonferroni alpha: %.4f." % st["bonferroni_alpha"]]
            for c, v in st["pass"].items():
                L.append("- %s: %s" % (c, "PASSES" if v["passes"] else "fails: " + "; ".join(v["why_not"])))
        if s == 3:
            for c, v in st["results"].items():
                p = v["pooled"]
                L.append("- %s: %s; longest losing run %s, deepest fall of cumulative R %s." % (
                    c, "HOLDS in the holdout" if v.get("holds") else "does NOT hold in the holdout",
                    p.get("longest_losing_run"), "%.2f" % p["deepest_fall_r"] if p.get("n") else "-"))
            L += ["", "Descriptive (whole history, passes nothing):", "", "```", json.dumps(st.get("descriptive"), indent=1, default=float), "```"]
        for c, v in st["results"].items():
            sk = v["skips"]
            L.append("- skipped events %s: %s" % (c, "; ".join("%s %s" % (a, dict((k, x) for k, x in d.items() if k != "entries_window_past_period_end")) for a, d in sk.items())))
        L.append("")
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def selftest():
    """The trade walk on hand-made bars (no store needed)."""
    n = 140
    o = np.full(n, 100.0)
    h, l, c = o + 0.2, o - 0.2, o.copy()
    px = {"open": o.copy(), "high": h.copy(), "low": l.copy(), "close": c.copy()}
    rd = {"low16": pd.Series(px["low"]).rolling(LOOK, min_periods=LOOK).min().values, "atr15": np.full(n, 1.0)}
    k = 20                               # entry 100 at bar 21, stop 99.8 - 0.25 = 99.55, R 0.45
    px1 = {x: v.copy() for x, v in px.items()}
    px1["low"][25] = 99.0                                    # stop out
    r = outcomes(px1, rd, np.array([k]), 0.0)
    assert abs(r["r"][0] + 1.0) < 1e-9 and r["xbar"][0] == 25, r
    px2 = {x: v.copy() for x, v in px.items()}
    px2["high"][23] = 100.5                                  # +1R, then back to the entry
    px2["low"][24] = 99.95
    r = outcomes(px2, rd, np.array([k]), 0.0)
    assert abs(r["r"][0] - 0.5) < 1e-9 and r["xbar"][0] == 24, r
    px3 = {x: v.copy() for x, v in px.items()}
    px3["high"][23] = 101.2                                  # +1R and +2.5R in one bar
    r = outcomes(px3, rd, np.array([k]), 0.0)
    assert abs(r["r"][0] - 1.75) < 1e-9, r
    px4 = {x: v.copy() for x, v in px.items()}
    px4["low"][23], px4["high"][23] = 99.0, 101.0            # both in one bar: the stop first
    r = outcomes(px4, rd, np.array([k]), 0.0)
    assert abs(r["r"][0] + 1.0) < 1e-9, r
    px5 = {x: v.copy() for x, v in px.items()}
    px5["close"][k + WIN] = 100.225                          # nothing hit: out at the close of bar k+96
    r = outcomes(px5, rd, np.array([k]), 0.0)
    assert abs(r["r"][0] - 0.5) < 1e-9 and r["xbar"][0] == k + WIN, r
    px6 = {x: v.copy() for x, v in px.items()}
    px6["open"][30], px6["low"][30] = 99.0, 98.9             # gap through the stop: the open
    r = outcomes(px6, rd, np.array([k]), 0.001)
    assert abs(r["r"][0] - ((99.0 - 100.0) / 0.45 - 0.001 * (100 + 99.0) / 0.45)) < 1e-9, r
    m = np.array([False, True, True, False, True])
    prev = np.concatenate([[True], m[:-1]])
    assert list(m & ~prev) == [False, True, False, False, True]
    print("selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, choices=(1, 2, 3))
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return
    if a.report:
        report()
        return
    run_stage(a.stage, a.fits_dir)
    report()


if __name__ == "__main__":
    main()
