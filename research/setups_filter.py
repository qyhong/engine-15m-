# -*- coding: utf-8 -*-
"""H55, the Setups quality filter (research/HYPOTHESES.md, registered 17 Nov 2026 12:03 UTC). PAPER ONLY. HISTORY, NOT PROOF.

    python research/setups_filter.py --group crypto      stage A, one market group (research server, read-only on data/)
    python research/setups_filter.py --report            stage B: the two filters, the pass bar, report.md / results.json

Can the engine's own readings at a setup's start tell which Setups (S1) signals are worth sending? A supervised
"take it or skip it" classifier on top of the existing b_targets book (meta-labelling). Nothing is tuned here: the
population, label, inputs, variants, hyperparameters, the median cut, the halves, the pass bar and the bootstrap are
H55's, fixed before this file existed.

STAGE A (per market group). The engine's evidence store data/evcache/<group>/<asset> is opened READ-ONLY with
research/card_overlap.open_stores (mode "r" memory maps, the store's version checked against the code, a store that is
being built is waited for and never read). The rows before the seal (2025-11-11 00:00 UTC) are copied into memory at
once and the store is let go: no row at or after the seal is ever read (the bar files are cut the same way the moment
they are loaded). Nothing under data/ is written. The odds are formed as leanprep.prepare_live forms them (labels,
weekly refits by leanprep.walk_forward_cached, trust, the group's voting cards, the 40% trust cap, the mix), walked from
the engine's birth (2020-01-01) as H36 replayed the books (research/exit_study.py), with the refits cached in a PRIVATE
folder research/out/setups_filter/fits/<group> (that function deletes refits it did not use, so it is never given the
engine's own folder). Then the b_targets book (shadows.run_challenger, rule unchanged) runs from the first session with
odds. Every closed b_targets trade is a candidate signal:
  * a trade that opens and closes inside its own fill bar never shows on the page and is never a signal (H53 amendment);
  * a trade still open at the seal, or a followable trade not finished by the seal, has no result and is left out (counted);
  * the signal is what the page would show after the fill bar F closed (prices rounded as shadows._px rounds them; if
    Target 1 already traded in bar F the page shows the stop at the entry and it is a "do not enter" = no fill);
  * it is scored by engine15/signals.py itself (build_signal + step_bar, the live state machine): the alert goes out in
    the 15-minute slot after F (bar A = F+1, the earliest the page can show it); the book's own close becomes known when
    the bar it closed in is stepped (as the live check sees it), and an exit alert for an open followable trade goes out
    in the slot after that bar (rule 4: the followable trade closes at the open of the first bar after that slot).
  * Bars are the asset's own 15-minute bar file (as signals.py reads them), cut at the seal.
Inputs at the book's DECISION bar k only (k = fill bar - 1 - the market's fill delay: the close at which policy.decide
called the entry): the 437 readings of evidence.FEATURES as stored for that row (the engine's matrix: NaN -> 0), the
main call's odds signed to the setup's side (P(with), P(against), P(neither)) and edge points (side x (P(up)-P(down)) x
100), the UTC hour and weekday of the decision close, and the stop distance and Target-1 distance in ATR(14, 15m) and
their ratio. The fill price (the next bar's open) is not known at the decision close, so the two distances are the
book's own plan made at the decision close: entry = the close of bar k, stop = 2 barriers (unit of row k), Target 1 =
live.plan_targets on row k. The market one-hot is added in stage B. tests/test_setups_filter.py proves the inputs at k
are the same with and without the rows after k.

STAGE B. y = 1 if the followable result is > 0 R after costs, else 0 (a no fill is y = 0 and 0 R). First half: entries
(the fill bar's open) before 2023-06-07; second half: 2023-06-07 to the seal. Each variant is trained ONCE on the first
half; it keeps a signal when its predicted probability is at or above the median of its first-half predictions.
Nothing from the second half trains, scales, cuts or chooses.

LIBRARY (H55 library note, 17 Nov 2026 12:36 UTC, before any real-data number): when scikit-learn is importable (the
separate research setup /data/venv-research on the server), F1 and F2 are judged with scikit-learn exactly as registered
(SkF1, SkF2 below) and the numpy stand-ins are reported beside as a cross-check only. Without it the stand-ins are judged.
The stand-ins were written while scikit-learn was NOT installed on the research server (nor on the laptop) (stated here,
fixed before any H55 number existed):
  F1  logistic regression, L2, C = 0.1, inputs standardised on the training rows (mean, population sd; a constant input
      keeps scale 1, as StandardScaler), class weights balanced (n / (2 n_class)), intercept not penalised: sklearn's
      objective C * sum(w_i * logloss_i) + 0.5 * |coef|^2, solved here exactly by Newton's method in numpy (the problem is
      strictly convex: one optimum, whichever solver finds it). Not a stand-in for the model, only for the library.
  F2  the registered stand-in for HistGradientBoostingClassifier: HGBStandIn below, gradient-boosted trees on binary
      log-loss written in numpy with the registered settings (max_depth 3, learning_rate 0.05, 200 iterations,
      min_samples_leaf 50, l2_regularization 1.0, no early stopping) and sklearn's defaults otherwise: 255 bins per input
      from the training rows (midpoints of distinct values when there are <= 255, else the 254 inner percentiles,
      "midpoint" method, duplicates dropped; a value goes to the first threshold >= it), the baseline log-odds of the
      training base rate, Newton leaf values -lr * G / (H + l2), split gain 0.5 * (GL^2/(HL+l2) + GR^2/(HR+l2) -
      G^2/(H+l2)) required > 0, each child >= 50 rows and hessian >= 1e-3, every node split until depth 3 (the default
      31-leaf cap cannot bind at depth 3), no row or column subsampling, no class weights.
  Missing inputs (NaN; the readings are already NaN -> 0) are replaced by the training-half mean of that input, for
  both variants; the count is reported.
  "The ten inputs that move each variant most": F1 by |coefficient| on the standardised inputs; F2 by total split gain.
Pass bar (second half, each variant on its own, Bonferroni over 2 = p <= 0.025):
  (1) mean followable R per SENT signal, kept set > all signals, one-sided block bootstrap: the second half's calendar
      weeks (Monday to Sunday UTC, by entry) resampled with replacement, 10,000 times, numpy default_rng(55) (a fresh
      generator per variant, so both see the same resamples); d* = mean(kept)* - mean(all)*;
      p = (1 + #{d* <= 0}) / (1 + 10,000);
  (2) total followable R of the kept set > 0; (3) kept mean > all mean in >= 5 of the markets with >= 20 second-half
  signals; (4) kept set >= 100 second-half signals.
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

from engine15 import signals  # noqa: E402  (light: config only)
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "setups_filter")
FITS = os.path.join(OUT, "fits")
SEAL = "2025-11-11"                     # sealed holdout: rows at or after 2025-11-11 00:00 UTC are never read
SPLIT = "2023-06-07"                    # first half: entries before it; second half: from it to the seal
SEAL_MS = int(pd.Timestamp(SEAL, tz="UTC").value // 10 ** 6)
SPLIT_MS = int(pd.Timestamp(SPLIT, tz="UTC").value // 10 ** 6)
BAR = signals.BAR_MS
ALERT_LAG_MS = 150000                   # the live step finishes ~140-150 s after the quarter hour (live.log)
SEED, BOOT = 55, 10000
MARKETS = ["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"]
GROUP_ORDER = ("crypto", "metals", "fx", "energy", "index")
EXTRA = ["odds_with", "odds_against", "odds_neither", "edge_signed", "hour_utc", "weekday", "stop_atr", "t1_atr",
         "t1_stop_ratio"]
F1_C = 0.1
F2 = dict(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0, max_bins=255,
          min_hessian_to_split=1e-3)


# =====================================================================================
# the seal
# =====================================================================================
def seal_n(times):
    """Rows of a sorted time index strictly before the seal."""
    return int(pd.DatetimeIndex(times).searchsorted(pd.Timestamp(SEAL, tz="UTC")))


def sealed_bars(df):
    """A bar frame (index = open time, UTC) cut at the seal: the first thing done with any bar file."""
    return df[df.index < pd.Timestamp(SEAL, tz="UTC")]


# =====================================================================================
# stage A: read-only copy of the store, the odds, the book
# =====================================================================================
def ev_columns():
    from engine15 import shadows
    cols = ["shock", "tide", "atr1h", "atr15", "htf_bias", "release_soon", "sw_lo_15m", "sw_hi_15m", "sw_lo_1h",
            "sw_hi_1h", "reach_1h_med_pct", "reach_4h_med_pct"]
    for tf in shadows.PB_FIB_TFS:
        cols += ["fib_%s_dir" % tf, "fib_%s_broken" % tf, "fib_%s_r500_px" % tf, "fib_%s_entry_px" % tf]
    cols += ["ma_%s_%s_px" % (tf, m) for tf in shadows.PB_MA_TFS for m in shadows.PB_MAS]
    cols += list(shadows.TARGET_COLS)
    return list(dict.fromkeys(cols))


def quiet_window(log):
    """Wait until the engine's step is not rewriting its stores (it runs for ~2.5 minutes after xx:00/15/30/45 UTC):
    a copy starts between 4 and 13 minutes into a quarter hour."""
    while True:
        m = time.gmtime()
        q = (m.tm_min % 15) + m.tm_sec / 60.0
        if 4.0 <= q < 13.0:
            return
        log("waiting for the engine's step to finish (%.1f min into the quarter hour)" % q)
        time.sleep(30)


def snapshot(group, assets, log):
    """Rows before the seal, copied into memory: times, X (float64), ready, the readings the book needs (stored dtype).
    The store is let go afterwards; a copy taken while the store changed hands is taken again."""
    from card_overlap import open_stores
    from engine15 import evcache
    want = ev_columns()
    for attempt in range(8):
        quiet_window(log)
        stores, gm = open_stores(group, assets, log)
        try:
            t_ms = stores[assets[0]].times_ms()
            for a in assets[1:]:
                if not np.array_equal(stores[a].times_ms(), t_ms):
                    raise RuntimeError("timelines differ")
            times_full = pd.DatetimeIndex(pd.to_datetime(t_ms, unit="ms", utc=True))
            n = seal_n(times_full)
            X, ready, ev = {}, {}, {}
            for a in assets:
                X[a] = np.ascontiguousarray(np.asarray(stores[a].X()[:n]), dtype=np.float64)
                ready[a] = np.array(stores[a].ready()[:n], dtype=bool)
                fr = stores[a].frame(times_full)
                cols = [c for c in want if c in fr.columns]
                sub = fr[cols].iloc[:n]
                ev[a] = pd.DataFrame(dict((c, np.array(sub[c].to_numpy(), copy=True)) for c in cols), index=times_full[:n])
                del fr, sub
            features = list(stores[assets[0]].meta["features"])
        except Exception as e:                                   # a file swapped under the read: try again later
            log("%s: read interrupted (%r); again in 60s" % (group, e))
            for st in stores.values():
                st._mm = {}
            gc.collect()
            time.sleep(60)
            continue
        for st in stores.values():
            st._mm = {}                                          # drop the read-only maps (never close(): it flushes)
        gc.collect()
        with open(os.path.join(evcache.CACHE_DIR, group, "group.json"), encoding="utf-8") as fh:
            gm2 = json.load(fh)
        if gm2.get("building") or gm2.get("sig") != gm.get("sig") or gm2.get("n", 0) < gm.get("n", 0) or \
                gm2.get("updated_utc") != gm.get("updated_utc"):
            log("%s: the store was written during the copy; again in 60s" % group)
            time.sleep(60)
            continue
        return {"times": times_full[:n], "n": n, "X": X, "ready": ready, "ev": ev, "features": features,
                "store": {"sig": gm.get("sig"), "updated_utc": gm.get("updated_utc"), "n_store": gm.get("n")}}
    raise RuntimeError("%s: no stable copy of the store" % group)


def prep_group(group, snap, log):
    """The odds as leanprep.prepare_live forms them (from the engine's birth, as H36), on the sealed copy."""
    from engine15 import data, evidence, labels, leanprep, model
    from engine15.config import voting_for
    t0 = time.time()
    assets = list(snap["X"])
    if snap["features"] != list(evidence.FEATURES):
        raise RuntimeError("%s: the store's feature list is not the engine's" % group)
    times, n = snap["times"], snap["n"]
    cfg = dict(CFG, assets=tuple(assets), voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    px, y, res, own = {}, {}, {}, {}
    for a in assets:
        b_all = sealed_bars(data.load(a))                       # cut at the seal the moment it is loaded
        own[a] = b_all
        b = b_all.reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * snap["ev"][a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    fits = os.path.join(FITS, group)
    assert os.path.abspath(fits).startswith(os.path.abspath(OUT))        # never the engine's fits folder
    X, ready = snap["X"], snap["ready"]
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth, min(floor, birth), n, fits)
    del models
    log("%s: voices walked from %s: %d refits (%d from the private cache), %.0fs" % (
        group, cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    lo = birth
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))
    odds = {}
    for a in assets:
        Xa = X[a][lo:n]
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        probs[a] = None
        del speaks, w
    del probs, trust
    gc.collect()
    log("%s: trust and odds done (%.0fs)" % (group, time.time() - t0))
    return {"cfg": cfg, "assets": assets, "times": times, "ev": snap["ev"], "px": px, "odds": odds, "birth_idx": birth,
            "own_bars": own, "X": X}


# =====================================================================================
# inputs at the decision bar (pure; rows after k are never touched)
# =====================================================================================
def decision_inputs(A, k, side):
    """The registered inputs at decision bar k for a setup on `side` (+1 long, -1 short). A: X (rows, features),
    odds (rows, 3: neither, up, down), close, unit (barrier in price), atr15, targets (a frame of shadows.TARGET_COLS
    or None), times_ms (bar open times). Only row k of each is read. -> (feature row float64, {extra input: value})"""
    from engine15 import labels
    from engine15.live import plan_targets
    k = int(k)
    x = np.array(np.asarray(A["X"][k]), dtype=np.float64, copy=True)
    o = np.asarray(A["odds"][k], dtype=float)
    up, dn, ne = float(o[labels.UP]), float(o[labels.DOWN]), float(o[labels.NEITHER])
    c, unit, atr = float(A["close"][k]), float(A["unit"][k]), float(A["atr15"][k])
    stop_d = CFG["stop_units"] * unit
    row = A["targets"].iloc[k] if A.get("targets") is not None and len(A["targets"].columns) else pd.Series(dtype=float)
    t1 = plan_targets(int(side), c, c - side * stop_d, row).get("target_1") if stop_d == stop_d and stop_d > 0 else None
    t1_d = abs(t1 - c) if t1 is not None else np.nan
    close_t = pd.Timestamp(int(A["times_ms"][k]) + BAR, unit="ms", tz="UTC")
    ok = atr == atr and atr > 0
    extra = {"odds_with": up if side > 0 else dn, "odds_against": dn if side > 0 else up, "odds_neither": ne,
             "edge_signed": side * (up - dn) * 100.0, "hour_utc": float(close_t.hour), "weekday": float(close_t.weekday()),
             "stop_atr": stop_d / atr if ok else np.nan, "t1_atr": t1_d / atr if ok else np.nan,
             "t1_stop_ratio": t1_d / stop_d if stop_d == stop_d and stop_d > 0 else np.nan}
    return x, extra


# =====================================================================================
# the followable score: engine15/signals.py's own state machine on history
# =====================================================================================
def page_view(side, entry, stop, t1, t2, f_ms, early):
    """What the page shows for the b_targets position after its fill bar closed (shadows.asset_view's rounding)."""
    from engine15.shadows import _px
    return {"status": "LONG" if side > 0 else "SHORT", "opened_utc": signals._dt(f_ms).strftime("%Y-%m-%d %H:%M"),
            "entry": _px(entry), "stop": _px(entry) if early else _px(stop), "target_1": _px(t1),
            "target_2": _px(t2), "t1_taken": bool(early)}


def score_followable(asset, view, bars, t_out_ms, why_out):
    """One signal through signals.build_signal / signals.step_bar, as the live check would see it.
    view: page_view(...); bars: (ts_ms, open, high, low, close) arrays of the asset's own bars, all before the seal;
    t_out_ms / why_out: the book's own exit (bar open time of its exit, its words).
    -> {"state": "closed" | "no_fill" | "not_a_signal" | "unresolved", "reason", "r", "pct", "usd", "fill_ms", "end_ms"}"""
    ts, o, h, l, c = bars
    if len(ts) and int(ts[-1]) >= SEAL_MS:
        raise ValueError("a bar at or after the seal reached the scorer")
    f_ms = signals._parse_utc(view["opened_utc"])
    sig, why = signals.build_signal(asset, view, f_ms + BAR + ALERT_LAG_MS)
    if sig is None:
        return {"state": "not_a_signal", "reason": why}
    if sig["early_t1"]:                                          # Target 1 before the alert: "do not enter" = no fill
        return {"state": "no_fill", "reason": "target", "r": 0.0, "pct": 0.0, "usd": 0.0}
    f = sig["follow"]
    j = int(np.searchsorted(ts, f_ms, side="left"))
    for j in range(j, len(ts)):
        t = int(ts[j])
        if not sig["book"]["closed"] and t >= t_out_ms:          # the page shows the book closed by the time this bar is stepped
            sig["book"].update(closed=True, known=True, t_out_ms=int(t_out_ms), why_out=str(why_out))
        signals.step_bar(sig, (t, float(o[j]), float(h[j]), float(l[j]), float(c[j])))
        f["last_bar_ms"] = t
        if f["state"] not in signals.ACTIVE:
            break
        if sig["book"]["closed"] and f.get("exit_alert_ms") is None:     # rule 4: the alert goes out in the next slot
            f["exit_alert_ms"] = int(t_out_ms) + BAR
    st = f["state"]
    if st == signals.NO_FILL:
        return {"state": "no_fill", "reason": f.get("reason"), "r": 0.0, "pct": 0.0, "usd": 0.0, "end_ms": f.get("end_ms")}
    if st == signals.CLOSED:
        res = f["result"]
        return {"state": "closed", "reason": f.get("why"), "r": res["r"], "pct": res["pct"], "usd": res["usd"],
                "fill_ms": f.get("fill_ms"), "end_ms": f.get("end_ms")}
    if st == signals.WAITING and len(ts) and int(ts[-1]) + BAR >= sig["valid_until_ms"]:
        return {"state": "no_fill", "reason": "window", "r": 0.0, "pct": 0.0, "usd": 0.0}
    return {"state": "unresolved", "reason": st}


# =====================================================================================
# stage A: one group
# =====================================================================================
def run_group(group, log):
    from engine15 import data, shadows
    t0 = time.time()
    assets = list(dict(CFG["universes"])[group])
    snap = snapshot(group, assets, log)
    log("%s: %d rows before %s copied (%s .. %s), %d readings (%.0fs)" % (
        group, snap["n"], SEAL, str(snap["times"][0])[:16], str(snap["times"][-1])[:16], len(snap["features"]),
        time.time() - t0))
    prep = prep_group(group, snap, log)
    times, n = prep["times"], len(prep["times"])
    tms = data.to_ms(times)
    out = {"group": group, "store": snap["store"], "n_rows": n, "assets": {}}
    rows, Xrows = [], []
    for a in assets:
        cfg_a = shadows.asset_cfg(a, prep["cfg"])
        delay = int(cfg_a.get("fill_delay_bars", 0) or 0)
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        b = shadows.run_challenger("b_targets", prep, a, lo, n, aux=aux)
        tr = b["trades"]
        ev = prep["ev"][a]
        A = {"X": prep["X"][a], "odds": prep["odds"][a], "close": prep["px"][a]["close"],
             "unit": (prep["cfg"]["barrier_atr"] * ev["atr1h"]).values, "atr15": shadows._col(ev, "atr15", n),
             "targets": aux["targets"], "times_ms": tms}
        own = prep["own_bars"][a]
        bars = (np.asarray(data.to_ms(own.index), dtype=np.int64), own["open"].values.astype(float),
                own["high"].values.astype(float), own["low"].values.astype(float), own["close"].values.astype(float))
        hi_, lo_ = prep["px"][a]["high"], prep["px"][a]["low"]
        cnt = {"book_trades": int(len(tr)), "instant": 0, "not_a_signal": 0, "unresolved": 0,
               "open_at_seal": int(b["state"]["pos"] != 0), "signals": 0}
        for t in tr.itertuples(index=False):
            i_in, i_out, side = int(t.i_in), int(t.i_out), int(t.side)
            if i_out == i_in:
                cnt["instant"] += 1                              # opened and closed inside its fill bar: never on the page
                continue
            if t.target_1 is None or t.target_1 != t.target_1:
                cnt["not_a_signal"] += 1
                continue
            early = bool(hi_[i_in] >= t.target_1) if side > 0 else bool(lo_[i_in] <= t.target_1)
            view = page_view(side, float(t.p_in), float(t.stop0), float(t.target_1), float(t.target_2), int(t.t_in_ms), early)
            fo = score_followable(a, view, bars, int(t.t_out_ms), t.why_out)
            if fo["state"] == "not_a_signal":
                cnt["not_a_signal"] += 1
                continue
            if fo["state"] == "unresolved":
                cnt["unresolved"] += 1
                continue
            k = i_in - 1 - delay
            x, extra = decision_inputs(A, k, side)
            cnt["signals"] += 1
            rows.append(dict({"asset": a, "t_in_ms": int(t.t_in_ms), "t_dec_ms": int(tms[k]), "k": k, "i_in": i_in,
                              "i_out": i_out, "side": side, "entry": view["entry"], "stop": view["stop"],
                              "t1": view["target_1"], "t2": view["target_2"], "early_t1": early,
                              "why_out": str(t.why_out), "book_r": float(t.r_mult) if t.r_mult == t.r_mult else np.nan,
                              "book_pct": float(t.pnl_pct), "follow_state": fo["state"],
                              "follow_reason": str(fo.get("reason")), "follow_r": float(fo["r"]) if fo.get("r") is not None else np.nan,
                              "follow_pct": float(fo["pct"]), "fill_ms": fo.get("fill_ms")}, **extra))
            Xrows.append(x)
        out["assets"][a] = dict(cnt, window=[str(times[lo])[:16], str(times[n - 1])[:16]], fill_delay=delay,
                                fee_side=cfg_a["cost_side"])
        log("%s %s: %d book trades, %d signals, %d instant, %d not a signal, %d unresolved, open at seal %d (%.0fs)" % (
            group, a, cnt["book_trades"], cnt["signals"], cnt["instant"], cnt["not_a_signal"], cnt["unresolved"],
            cnt["open_at_seal"], time.time() - t0))
    meta = pd.DataFrame(rows)
    Xm = np.vstack(Xrows) if Xrows else np.zeros((0, len(snap["features"])))
    meta.to_csv(os.path.join(OUT, "rows_%s.csv" % group), index=False)
    np.save(os.path.join(OUT, "X_%s.npy" % group), Xm)
    out["features"] = snap["features"]
    out["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, "group_%s.json" % group), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    log("%s done in %.0fs: %d signals" % (group, time.time() - t0, len(meta)))
    return out


# =====================================================================================
# stage B: the two variants (numpy; scikit-learn is not installed)
# =====================================================================================
def _sigmoid(z):
    return 0.5 * (1.0 + np.tanh(0.5 * z))


def balanced_weights(y):
    y = np.asarray(y).astype(int)
    n, w = len(y), np.ones(len(y))
    for c in (0, 1):
        m = y == c
        if m.any():
            w[m] = n / (2.0 * m.sum())
    return w


class LogitL2(object):
    """F1: sklearn's LogisticRegression(penalty="l2", C, class_weight="balanced") objective on standardised inputs,
    C * sum(w_i * logloss_i) + 0.5 * |coef|^2 (intercept free), minimised by Newton's method with a backtracking step."""

    def __init__(self, C=F1_C, tol=1e-10, max_iter=100):
        self.C, self.tol, self.max_iter = C, tol, max_iter

    def fit(self, X, y):
        X = np.asarray(X, float)
        y = np.asarray(y, float)
        self.mean_ = X.mean(axis=0)
        sd = X.std(axis=0)
        self.scale_ = np.where(sd > 0, sd, 1.0)
        Z = np.hstack([(X - self.mean_) / self.scale_, np.ones((len(X), 1))])
        sw = balanced_weights(y) * self.C
        d = Z.shape[1]
        reg = np.ones(d)
        reg[-1] = 0.0
        w = np.zeros(d)

        def obj(w):
            z = Z @ w
            return float(np.sum(sw * (np.logaddexp(0, z) - y * z)) + 0.5 * np.sum(reg * w * w))
        f = obj(w)
        self.n_iter_ = 0
        for it in range(self.max_iter):
            p = _sigmoid(Z @ w)
            g = Z.T @ (sw * (p - y)) + reg * w
            Hm = (Z * (sw * p * (1 - p))[:, None]).T @ Z + np.diag(reg)
            step = np.linalg.solve(Hm, g)
            t = 1.0
            while True:
                w_new = w - t * step
                f_new = obj(w_new)
                if f_new <= f - 1e-4 * t * float(g @ step) or t < 1e-10:
                    break
                t *= 0.5
            w, f = w_new, f_new
            self.n_iter_ = it + 1
            if float(np.max(np.abs(g))) < self.tol * max(1.0, abs(f)) or float(np.max(np.abs(t * step))) < 1e-12:
                break
        p = _sigmoid(Z @ w)
        self.grad_norm_ = float(np.max(np.abs(Z.T @ (sw * (p - y)) + reg * w)))
        self.coef_, self.intercept_ = w[:-1], float(w[-1])
        return self

    def predict_proba(self, X):
        Z = (np.asarray(X, float) - self.mean_) / self.scale_
        return _sigmoid(Z @ self.coef_ + self.intercept_)

    def importance(self):
        return np.abs(self.coef_)


class HGBStandIn(object):
    """F2's registered stand-in for HistGradientBoostingClassifier (see the module doc for every rule)."""

    def __init__(self, max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0,
                 max_bins=255, min_hessian_to_split=1e-3):
        self.max_depth, self.lr, self.max_iter = max_depth, learning_rate, max_iter
        self.msl, self.l2, self.max_bins, self.min_h = min_samples_leaf, l2_regularization, max_bins, min_hessian_to_split

    @staticmethod
    def thresholds(col, max_bins=255):
        u = np.unique(col[np.isfinite(col)])
        if len(u) <= max_bins:
            return (u[:-1] + u[1:]) * 0.5
        pct = np.linspace(0, 100, max_bins + 1)[1:-1]
        return np.unique(np.percentile(col, pct, method="midpoint"))

    def bin(self, X):
        X = np.asarray(X, float)
        out = np.empty(X.shape, dtype=np.uint8)
        for j, th in enumerate(self.th_):
            out[:, j] = np.searchsorted(th, X[:, j], side="left")
        return out

    def _best_split(self, Xb, rows, g, h):
        F = Xb.shape[1]
        nb = 256
        idx = (Xb[rows].astype(np.int64) + (np.arange(F, dtype=np.int64) * nb)[None, :]).ravel()
        Gh = np.bincount(idx, weights=np.repeat(g[rows], F), minlength=F * nb).reshape(F, nb)
        Hh = np.bincount(idx, weights=np.repeat(h[rows], F), minlength=F * nb).reshape(F, nb)
        Ch = np.bincount(idx, minlength=F * nb).reshape(F, nb)
        G, H, N = float(g[rows].sum()), float(h[rows].sum()), len(rows)
        GL, HL, CL = np.cumsum(Gh, axis=1)[:, :-1], np.cumsum(Hh, axis=1)[:, :-1], np.cumsum(Ch, axis=1)[:, :-1]
        GR, HR, CR = G - GL, H - HL, N - CL
        ok = (CL >= self.msl) & (CR >= self.msl) & (HL >= self.min_h) & (HR >= self.min_h)
        par = G * G / (H + self.l2)
        gain = 0.5 * (GL * GL / (HL + self.l2) + GR * GR / (HR + self.l2) - par)
        gain = np.where(ok, gain, -np.inf)
        f, b = np.unravel_index(int(np.argmax(gain)), gain.shape)
        if not np.isfinite(gain[f, b]) or gain[f, b] <= 0:
            return None
        return int(f), int(b), float(gain[f, b])

    def _grow(self, Xb, rows, g, h, depth, nodes):
        me = len(nodes)
        nodes.append(None)
        G, H = float(g[rows].sum()), float(h[rows].sum())
        sp = None
        if depth < self.max_depth and len(rows) >= 2 * self.msl and H >= self.min_h:
            sp = self._best_split(Xb, rows, g, h)
        if sp is None:
            nodes[me] = ("leaf", -self.lr * G / (H + self.l2))
            return me
        f, b, gain = sp
        self.gain_[f] += gain
        left = rows[Xb[rows, f] <= b]
        right = rows[Xb[rows, f] > b]
        li = self._grow(Xb, left, g, h, depth + 1, nodes)
        ri = self._grow(Xb, right, g, h, depth + 1, nodes)
        nodes[me] = ("split", f, b, li, ri)
        return me

    @staticmethod
    def _apply(nodes, Xb):
        out = np.zeros(len(Xb))
        stack = [(0, np.arange(len(Xb)))]
        while stack:
            k, rows = stack.pop()
            nd = nodes[k]
            if nd[0] == "leaf":
                out[rows] = nd[1]
                continue
            _, f, b, li, ri = nd
            m = Xb[rows, f] <= b
            stack.append((li, rows[m]))
            stack.append((ri, rows[~m]))
        return out

    def fit(self, X, y):
        X = np.asarray(X, float)
        y = np.asarray(y, float)
        self.th_ = [self.thresholds(X[:, j], self.max_bins) for j in range(X.shape[1])]
        Xb = self.bin(X)
        p0 = min(max(y.mean(), 1e-12), 1 - 1e-12)
        self.base_ = float(np.log(p0 / (1 - p0)))
        raw = np.full(len(y), self.base_)
        self.trees_, self.gain_ = [], np.zeros(X.shape[1])
        rows = np.arange(len(y))
        for _ in range(self.max_iter):
            p = _sigmoid(raw)
            g, h = p - y, p * (1 - p)
            nodes = []
            self._grow(Xb, rows, g, h, 0, nodes)
            self.trees_.append(nodes)
            raw += self._apply(nodes, Xb)
        return self

    def predict_proba(self, X):
        Xb = self.bin(X)
        raw = np.full(len(Xb), self.base_)
        for nodes in self.trees_:
            raw += self._apply(nodes, Xb)
        return _sigmoid(raw)

    def importance(self):
        return self.gain_


def importlib_find(name):
    import importlib.util
    return importlib.util.find_spec(name) is not None


def sklearn_available():
    return importlib_find("sklearn")


class SkF1(object):
    """F1 as judged (H55 library note, 17 Nov 2026 12:36 UTC): StandardScaler on the training rows, then
    LogisticRegression(penalty="l2", C=0.1, class_weight="balanced", solver="lbfgs", max_iter=5000)."""

    def fit(self, X, y):
        import warnings
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler().fit(X)
        kw = dict(C=F1_C, class_weight="balanced", solver="lbfgs", max_iter=5000)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                self.lr = LogisticRegression(penalty="l2", **kw)
            except TypeError:                                    # a version without the argument: L2 is its only default
                self.lr = LogisticRegression(**kw)
            self.lr.fit(self.scaler.transform(X), y)
        self.warnings_ = sorted(set(str(x.message)[:200] for x in w))
        self.coef_ = np.asarray(self.lr.coef_[0], float)
        self.n_iter_ = int(np.max(self.lr.n_iter_))
        return self

    def predict_proba(self, X):
        return self.lr.predict_proba(self.scaler.transform(X))[:, 1]

    def importance(self):
        return np.abs(self.coef_)

    def info(self):
        return {"library": "scikit-learn LogisticRegression (lbfgs)", "iterations": self.n_iter_,
                "warnings": self.warnings_}


class SkF2(object):
    """F2 as judged (H55 library note): HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
    min_samples_leaf=50, l2_regularization=1.0, early_stopping=False, random_state=55). Importance: total split gain."""

    def fit(self, X, y):
        import warnings
        from sklearn.ensemble import HistGradientBoostingClassifier
        self.m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50,
                                                l2_regularization=1.0, early_stopping=False, random_state=55)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.m.fit(X, y)
        self.warnings_ = sorted(set(str(x.message)[:200] for x in w))
        self.n_features_ = X.shape[1]
        return self

    def predict_proba(self, X):
        return self.m.predict_proba(X)[:, 1]

    def importance(self):
        g = np.zeros(self.n_features_)
        try:
            for it in self.m._predictors:
                for pr in it:
                    nd = pr.nodes
                    sp = ~nd["is_leaf"].astype(bool)
                    np.add.at(g, nd["feature_idx"][sp].astype(int), nd["gain"][sp].astype(float))
        except Exception:                                        # private layout changed: no ranking rather than a wrong one
            g[:] = np.nan
        return g

    def info(self):
        return {"library": "scikit-learn HistGradientBoostingClassifier", "iterations": int(self.m.n_iter_),
                "warnings": self.warnings_}


def judged_models():
    """-> ({"F1", "F2"}: the judged models, the library in words). scikit-learn when it is installed (the H55 library
    note); the numpy stand-ins otherwise."""
    if sklearn_available():
        import sklearn
        return {"F1": SkF1(), "F2": SkF2()}, "scikit-learn %s" % sklearn.__version__
    return {"F1": LogitL2(C=F1_C), "F2": HGBStandIn(**F2)}, "numpy stand-ins (scikit-learn not installed)"


def auc(score, y):
    """Area under the ROC curve (Mann-Whitney, ties at half)."""
    y = np.asarray(y).astype(bool)
    s = np.asarray(score, float)
    n1, n0 = int(y.sum()), int((~y).sum())
    if not n1 or not n0:
        return None
    r = pd.Series(s).rank(method="average").to_numpy()
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def week_ids(t_ms):
    """Calendar week (Monday 00:00 UTC to Sunday) of each entry, as an integer."""
    monday0 = int(pd.Timestamp("1970-01-05", tz="UTC").value // 10 ** 6)      # a Monday
    return ((np.asarray(t_ms, dtype=np.int64) - monday0) // (7 * 86400000)).astype(np.int64)


def block_bootstrap_p(r, keep, weeks, n=BOOT, seed=SEED):
    """One-sided: mean R of the kept set vs mean R of all, calendar weeks resampled with replacement.
    -> (observed difference, p = (1 + #{d* <= 0}) / (1 + n), share of resamples with no kept signal)"""
    r, keep = np.asarray(r, float), np.asarray(keep, bool)
    u, wi = np.unique(np.asarray(weeks), return_inverse=True)
    W = len(u)
    s_all = np.bincount(wi, weights=r, minlength=W)
    n_all = np.bincount(wi, minlength=W).astype(float)
    s_k = np.bincount(wi, weights=r * keep, minlength=W)
    n_k = np.bincount(wi, weights=keep.astype(float), minlength=W)
    obs = float(r[keep].mean() - r.mean()) if keep.any() else float("nan")
    rng = np.random.default_rng(seed)
    le, empty = 0, 0
    for _ in range(n):
        c = np.bincount(rng.integers(0, W, W), minlength=W).astype(float)
        nk = c @ n_k
        if nk <= 0:
            empty += 1
            le += 1
            continue
        d = (c @ s_k) / nk - (c @ s_all) / (c @ n_all)
        le += int(d <= 0)
    return obs, (1.0 + le) / (1.0 + n), empty / float(n)


def block(df, rcol="R"):
    """Counts, fill rate, mean and total R per sent signal, win rate (of filled trades for the followable record, of
    trades for the book record)."""
    n = len(df)
    if not n:
        return {"n": 0}
    filled = df["follow_state"] == "closed"
    r = df[rcol].astype(float)
    if rcol == "R":
        wins = (r[filled] > 0).mean() if filled.any() else np.nan
    else:
        wins = (r > 0).mean()
    return {"n": int(n), "filled": int(filled.sum()), "fill_rate_pct": round(100.0 * filled.mean(), 1),
            "mean_r": round(float(r.mean()), 4), "total_r": round(float(r.sum()), 2),
            "win_rate_pct": None if wins != wins else round(100.0 * float(wins), 1),
            "label_rate_pct": round(100.0 * float((df["y"] == 1).mean()), 1)}


def load_rows(log):
    metas, Xs, groups, feats = [], [], {}, None
    for g in GROUP_ORDER:
        p = os.path.join(OUT, "rows_%s.csv" % g)
        if not os.path.exists(p):
            log("no rows for %s" % g)
            continue
        with open(os.path.join(OUT, "group_%s.json" % g), encoding="utf-8") as fh:
            groups[g] = json.load(fh)
        if feats is None:
            feats = groups[g]["features"]
        elif feats != groups[g]["features"]:
            raise RuntimeError("feature lists differ between groups")
        m = pd.read_csv(p)
        X = np.load(os.path.join(OUT, "X_%s.npy" % g))
        if len(m) != len(X):
            raise RuntimeError("%s: rows and inputs disagree" % g)
        keep = m["t_in_ms"].values < SEAL_MS                    # defensive: nothing at or after the seal
        metas.append(m[keep])
        Xs.append(X[keep])
    meta = pd.concat(metas, ignore_index=True)
    X = np.vstack(Xs)
    return meta, X, groups, feats


def design(meta, X, feats):
    onehot = np.stack([(meta["asset"].values == a).astype(float) for a in MARKETS], axis=1)
    extra = meta[EXTRA].astype(float).values
    D = np.hstack([X, extra, onehot])
    names = list(feats) + EXTRA + ["market_%s" % a for a in MARKETS]
    return D, names


def evaluate(name, model, D, names, meta, first, second, log):
    t0 = time.time()
    Dtr = D[first]
    model.fit(Dtr, meta.loc[first, "y"].values)
    p = model.predict_proba(D)
    cut = float(np.median(p[first]))
    keep = p >= cut
    m2 = meta[second].copy()
    m2["keep"] = keep[second]
    m1 = meta[first].copy()
    m1["keep"] = keep[first]
    all2, kept2 = m2, m2[m2["keep"]]
    obs, pval, empty = block_bootstrap_p(m2["R"].values, m2["keep"].values, week_ids(m2["t_in_ms"].values))
    per = {}
    for a in MARKETS:
        s = m2[m2["asset"] == a]
        if len(s):
            k = s[s["keep"]]
            per[a] = {"n": int(len(s)), "kept": int(len(k)), "mean_all": round(float(s["R"].mean()), 4),
                      "mean_kept": round(float(k["R"].mean()), 4) if len(k) else None,
                      "eligible": bool(len(s) >= 20),
                      "kept_better": bool(len(k) and float(k["R"].mean()) > float(s["R"].mean()))}
    elig = [a for a, v in per.items() if v["eligible"]]
    better = [a for a in elig if per[a]["kept_better"]]
    rules = {
        "r1_mean_kept_gt_all_p": {"kept_mean_r": round(float(kept2["R"].mean()), 4) if len(kept2) else None,
                                  "all_mean_r": round(float(all2["R"].mean()), 4), "diff": round(obs, 4),
                                  "p": round(pval, 5), "resamples_no_kept_share": empty,
                                  "pass": bool(len(kept2) and obs > 0 and pval <= 0.025)},
        "r2_kept_total_r_gt_0": {"kept_total_r": round(float(kept2["R"].sum()), 2), "pass": bool(float(kept2["R"].sum()) > 0)},
        "r3_markets": {"eligible": elig, "kept_better": better, "count": len(better), "need": 5,
                       "pass": bool(len(better) >= 5)},
        "r4_kept_n": {"kept_n": int(len(kept2)), "need": 100, "pass": bool(len(kept2) >= 100)}}
    passed = all(v["pass"] for v in rules.values())
    imp = np.nan_to_num(np.asarray(model.importance(), float), nan=-1.0)
    top = [(names[i], round(float(imp[i]), 5)) for i in np.argsort(-imp)[:10]]
    if hasattr(model, "coef_"):
        top = [(names[i], round(float(model.coef_[i]), 5)) for i in np.argsort(-imp)[:10]]

    def tables(df, rcol):
        out = {}
        for half, d in (("first", df[0]), ("second", df[1])):
            row = {"all": block(d, rcol), "kept": block(d[d["keep"]], rcol), "skipped": block(d[~d["keep"]], rcol)}
            row["by_market"] = dict((a, {"all": block(d[d["asset"] == a], rcol),
                                         "kept": block(d[(d["asset"] == a) & d["keep"]], rcol),
                                         "skipped": block(d[(d["asset"] == a) & ~d["keep"]], rcol)})
                                    for a in MARKETS if (d["asset"] == a).any())
            out[half] = row
        return out
    res = {"variant": name, "cut": cut, "auc_first": auc(p[first], meta.loc[first, "y"].values),
           "auc_second": auc(p[second], meta.loc[second, "y"].values), "kept_share_first": round(float(keep[first].mean()), 4),
           "kept_share_second": round(float(keep[second].mean()), 4), "rules": rules, "passed": passed,
           "per_market_second": per, "top_inputs": top, "follow": tables((m1, m2), "R"),
           "book": tables((m1, m2), "book_r"), "seconds": round(time.time() - t0, 1)}
    if isinstance(model, LogitL2):
        res["solver"] = {"library": "numpy Newton (this file)", "iterations": model.n_iter_,
                         "max_abs_gradient": model.grad_norm_}
    elif isinstance(model, HGBStandIn):
        res["solver"] = {"library": "numpy HGBStandIn (this file)", "iterations": len(model.trees_)}
    elif hasattr(model, "info"):
        res["solver"] = model.info()
    res["_keep"] = keep
    log("%s: AUC first %.3f second %.3f, kept %d of %d second-half signals, mean R kept %+.4f vs all %+.4f, p %.4f, "
        "pass %s (%.0fs)" % (name, res["auc_first"] or 0, res["auc_second"] or 0, len(kept2), len(all2),
                             rules["r1_mean_kept_gt_all_p"]["kept_mean_r"] or 0, rules["r1_mean_kept_gt_all_p"]["all_mean_r"],
                             pval, passed, res["seconds"]))
    return res


def report(log):
    t0 = time.time()
    meta, X, groups, feats = load_rows(log)
    meta = meta.reset_index(drop=True)
    meta["R"] = meta["follow_r"].where(meta["follow_state"] == "closed", 0.0).astype(float)
    meta["y"] = (meta["R"] > 0).astype(int)
    D, names = design(meta, X, feats)
    first = (meta["t_in_ms"].values < SPLIT_MS)
    second = (meta["t_in_ms"].values >= SPLIT_MS) & (meta["t_in_ms"].values < SEAL_MS)
    nan_cells = np.isnan(D)
    nan_by_col = dict((names[j], int(nan_cells[:, j].sum())) for j in np.flatnonzero(nan_cells.any(axis=0)))
    mu = np.nanmean(np.where(first[:, None], D, np.nan), axis=0)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    D = np.where(nan_cells, mu[None, :], D)
    log("%d signals (%d first half, %d second half), %d inputs, %d missing cells" % (
        len(meta), first.sum(), second.sum(), D.shape[1], int(nan_cells.sum())))
    pop = {}
    for half, m in (("first", first), ("second", second)):
        d = meta[m]
        pop[half] = {"all": block(d.assign(keep=True), "R"),
                     "by_market": dict((a, block(d[d["asset"] == a], "R")) for a in MARKETS if (d["asset"] == a).any()),
                     "book_all": block(d, "book_r"),
                     "book_by_market": dict((a, block(d[d["asset"] == a], "book_r")) for a in MARKETS if (d["asset"] == a).any()),
                     "no_fill_reasons": dict(d.loc[d["follow_state"] == "no_fill", "follow_reason"].value_counts().astype(int))}
    models, library = judged_models()
    log("judged with %s" % library)
    variants, cross = {}, {}
    variants["F1"] = evaluate("F1", models["F1"], D, names, meta, first, second, log)
    variants["F2"] = evaluate("F2", models["F2"], D, names, meta, first, second, log)
    if not isinstance(models["F1"], LogitL2):                    # the numpy stand-ins beside, a cross-check only
        cross["F1_numpy"] = evaluate("F1_numpy (cross-check, not judged)", LogitL2(C=F1_C), D, names, meta, first,
                                     second, log)
        cross["F2_numpy"] = evaluate("F2_numpy (cross-check, not judged)", HGBStandIn(**F2), D, names, meta, first,
                                     second, log)
        for k, j in (("F1_numpy", "F1"), ("F2_numpy", "F2")):
            a, b = cross[k]["_keep"], variants[j]["_keep"]
            cross[k]["keep_agreement_second_pct"] = round(100.0 * float((a[second] == b[second]).mean()), 1)
            cross[k]["keep_agreement_first_pct"] = round(100.0 * float((a[first] == b[first]).mean()), 1)
    for v in list(variants.values()) + list(cross.values()):
        v.pop("_keep", None)
    res = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "seal": SEAL, "split": SPLIT,
           "n_signals": int(len(meta)), "n_first": int(first.sum()), "n_second": int(second.sum()),
           "label_base_rate_pct": {"all": round(100.0 * meta["y"].mean(), 2), "first": round(100.0 * meta.loc[first, "y"].mean(), 2),
                                   "second": round(100.0 * meta.loc[second, "y"].mean(), 2)},
           "inputs": len(names), "missing_cells": int(nan_cells.sum()), "missing_by_input": nan_by_col,
           "markets_present": sorted(meta["asset"].unique().tolist(), key=MARKETS.index),
           "groups": dict((g, {"store": v["store"], "n_rows": v["n_rows"], "assets": v["assets"], "seconds": v["seconds"]})
                          for g, v in groups.items()),
           "population": pop, "variants": variants, "library": library, "cross_check": cross,
           "passed_any": bool(variants["F1"]["passed"] or variants["F2"]["passed"]),
           "seconds": round(time.time() - t0, 1)}
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    write_md(res, os.path.join(OUT, "report.md"))
    log("report written (%.0fs)" % (time.time() - t0))
    return res


# =====================================================================================
# the report
# =====================================================================================
def _f(v, pat="%+.3f"):
    return "-" if v is None or (isinstance(v, float) and v != v) else pat % v


def _brow(label, b, book=False):
    if not b or not b.get("n"):
        return "| %s | 0 | - | - | - | - |" % label
    return "| %s | %d | %s | %s | %s | %s |" % (label, b["n"], "-" if book else "%.1f%%" % b["fill_rate_pct"],
                                               _f(b["mean_r"], "%+.4f"), _f(b["total_r"], "%+.1f"),
                                               _f(b.get("win_rate_pct"), "%.1f%%"))


def write_md(res, path):
    V = res["variants"]
    L = ["# H55: the Setups quality filter on history (NOT proof)", "",
         "Written by `research/setups_filter.py` on %s. Registered in `research/HYPOTHESES.md` (H55, 17 Nov 2026 12:03 UTC) "
         "before any H55 code or number existed. Paper only; history the engine's authors have lived through; the sealed "
         "holdout (from %s) was never read." % (res["written_utc"], res["seal"]), "",
         "**Plainly:** a history read can reject an idea, never prove one. A pass would only be a reason to propose a "
         "forward paper filter book (S1-F) to the owner.", "",
         "## Verdict", ""]
    for k in ("F1", "F2"):
        v = V[k]
        L.append("- **%s: %s.** AUC first half %s (in-sample), second half %s." % (
            k, "PASS" if v["passed"] else "NO PASS", _f(v["auc_first"], "%.3f"), _f(v["auc_second"], "%.3f")))
    L.append("")
    L.append("Judged with %s." % res.get("library"))
    L += ["", "## Pass table (second half, %s to the seal)" % res["split"], "",
          "| Rule | F1 | F1 pass | F2 | F2 pass |", "|---|---|---|---|---|"]
    r1, r2 = V["F1"]["rules"], V["F2"]["rules"]
    L.append("| (1) mean R per sent signal, kept > all, block bootstrap p <= 0.025 | kept %s vs all %s (diff %s), p = %s | %s | "
             "kept %s vs all %s (diff %s), p = %s | %s |" % (
                 _f(r1["r1_mean_kept_gt_all_p"]["kept_mean_r"], "%+.4f"), _f(r1["r1_mean_kept_gt_all_p"]["all_mean_r"], "%+.4f"),
                 _f(r1["r1_mean_kept_gt_all_p"]["diff"], "%+.4f"), _f(r1["r1_mean_kept_gt_all_p"]["p"], "%.4f"),
                 "yes" if r1["r1_mean_kept_gt_all_p"]["pass"] else "no",
                 _f(r2["r1_mean_kept_gt_all_p"]["kept_mean_r"], "%+.4f"), _f(r2["r1_mean_kept_gt_all_p"]["all_mean_r"], "%+.4f"),
                 _f(r2["r1_mean_kept_gt_all_p"]["diff"], "%+.4f"), _f(r2["r1_mean_kept_gt_all_p"]["p"], "%.4f"),
                 "yes" if r2["r1_mean_kept_gt_all_p"]["pass"] else "no"))
    L.append("| (2) kept total R > 0 | %s R | %s | %s R | %s |" % (
        _f(r1["r2_kept_total_r_gt_0"]["kept_total_r"], "%+.1f"), "yes" if r1["r2_kept_total_r_gt_0"]["pass"] else "no",
        _f(r2["r2_kept_total_r_gt_0"]["kept_total_r"], "%+.1f"), "yes" if r2["r2_kept_total_r_gt_0"]["pass"] else "no"))
    L.append("| (3) kept mean > all mean in >= 5 markets with >= 20 signals | %d of %d (%s) | %s | %d of %d (%s) | %s |" % (
        r1["r3_markets"]["count"], len(r1["r3_markets"]["eligible"]), ", ".join(r1["r3_markets"]["kept_better"]) or "none",
        "yes" if r1["r3_markets"]["pass"] else "no",
        r2["r3_markets"]["count"], len(r2["r3_markets"]["eligible"]), ", ".join(r2["r3_markets"]["kept_better"]) or "none",
        "yes" if r2["r3_markets"]["pass"] else "no"))
    L.append("| (4) kept >= 100 second-half signals | %d | %s | %d | %s |" % (
        r1["r4_kept_n"]["kept_n"], "yes" if r1["r4_kept_n"]["pass"] else "no", r2["r4_kept_n"]["kept_n"],
        "yes" if r2["r4_kept_n"]["pass"] else "no"))
    L += ["", "## Population", "",
          "%d signals: %d first half (entries before %s), %d second half. Label base rate (followable > 0 R after costs; a "
          "no fill = 0): %.1f%% all, %.1f%% first half, %.1f%% second half. Markets present: %s." % (
              res["n_signals"], res["n_first"], res["split"], res["n_second"], res["label_base_rate_pct"]["all"],
              res["label_base_rate_pct"]["first"], res["label_base_rate_pct"]["second"], ", ".join(res["markets_present"])), "",
          "| Market | Book trades | Signals | Opened and closed in the fill bar (never a signal) | Not a signal | "
          "Unresolved at the seal | Open at the seal | Replay window |", "|---|---|---|---|---|---|---|---|"]
    for g, gv in res["groups"].items():
        for a, c in gv["assets"].items():
            L.append("| %s | %d | %d | %d | %d | %d | %d | %s .. %s |" % (
                a, c["book_trades"], c["signals"], c["instant"], c["not_a_signal"], c["unresolved"], c["open_at_seal"],
                c["window"][0], c["window"][1]))
    for half in ("first", "second"):
        P = res["population"][half]
        L += ["", "### All signals, %s half (followable R per sent signal; book R beside)" % half, "",
              "| Market | Signals | Fill rate | Mean R | Total R | Win rate (filled) | Book mean R | Book total R | Book win rate |",
              "|---|---|---|---|---|---|---|---|---|"]
        rows = [("all", P["all"], P["book_all"])] + [(a, P["by_market"][a], P["book_by_market"][a]) for a in P["by_market"]]
        for a, b, bb in rows:
            L.append("| %s | %d | %.1f%% | %s | %s | %s | %s | %s | %s |" % (
                a, b["n"], b["fill_rate_pct"], _f(b["mean_r"], "%+.4f"), _f(b["total_r"], "%+.1f"),
                _f(b.get("win_rate_pct"), "%.1f%%"), _f(bb["mean_r"], "%+.4f"), _f(bb["total_r"], "%+.1f"),
                _f(bb.get("win_rate_pct"), "%.1f%%")))
        L.append("")
        L.append("No-fill reasons: %s." % ", ".join("%s %d" % kv for kv in P["no_fill_reasons"].items()))
    for k in ("F1", "F2"):
        v = V[k]
        L += ["", "## %s: kept and skipped" % k, "",
              "Cut = median of first-half predictions = %.5f; kept %.1f%% of first-half and %.1f%% of second-half signals. "
              "AUC first half %s (in-sample), second half %s." % (
                  v["cut"], 100 * v["kept_share_first"], 100 * v["kept_share_second"], _f(v["auc_first"], "%.3f"),
                  _f(v["auc_second"], "%.3f"))]
        if v.get("solver"):
            s = v["solver"]
            L.append("Fitted with %s: %s iterations%s." % (
                s.get("library"), s.get("iterations"),
                "; warnings: %s" % "; ".join(s["warnings"]) if s.get("warnings") else ""))
        for rec, title in (("follow", "followable R"), ("book", "BOOK R (as b_targets booked it)")):
            for half in ("first", "second"):
                T = v[rec][half]
                book = rec == "book"
                L += ["", "**%s, %s half**" % (title, half), "",
                      "| Set | Signals | Fill rate | Mean R | Total R | Win rate |", "|---|---|---|---|---|---|"]
                for s in ("all", "kept", "skipped"):
                    L.append(_brow(s, T[s], book))
                for a, mt in T["by_market"].items():
                    for s in ("kept", "skipped"):
                        L.append(_brow("%s %s" % (a, s), mt[s], book))
        L += ["", "Top ten inputs (%s):" % ("coefficient on the standardised input" if k == "F1" else "total split gain"), ""]
        L += ["%d. `%s` %s" % (i + 1, nm, val) for i, (nm, val) in enumerate(v["top_inputs"])]
    C = res.get("cross_check") or {}
    if C:
        L += ["", "## Cross-check only (not judged): the numpy stand-ins", "",
              "| Stand-in | AUC first | AUC second | Kept (2nd half) | Kept mean R vs all | p | Total kept R | Markets | "
              "Would pass | Same keep/skip as the judged variant (1st / 2nd half) |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k, v in C.items():
            r = v["rules"]
            L.append("| %s | %s | %s | %d | %s vs %s | %.4f | %s | %d of %d | %s | %.1f%% / %.1f%% |" % (
                k, _f(v["auc_first"], "%.3f"), _f(v["auc_second"], "%.3f"), r["r4_kept_n"]["kept_n"],
                _f(r["r1_mean_kept_gt_all_p"]["kept_mean_r"], "%+.4f"), _f(r["r1_mean_kept_gt_all_p"]["all_mean_r"], "%+.4f"),
                r["r1_mean_kept_gt_all_p"]["p"], _f(r["r2_kept_total_r_gt_0"]["kept_total_r"], "%+.1f"),
                r["r3_markets"]["count"], len(r["r3_markets"]["eligible"]), "yes" if v["passed"] else "no",
                v.get("keep_agreement_first_pct", float("nan")), v.get("keep_agreement_second_pct", float("nan"))))
    if C:
        lib_note = ("- Judged with %s in the separate research Python setup (`/data/venv-research`; the engine's "
                    "`/data/venv` unchanged), as decided in the H55 library note (17 Nov 2026 12:36 UTC, before any "
                    "real-data number). The numpy stand-ins written while scikit-learn was missing are shown beside as a "
                    "cross-check only." % res.get("library"))
    else:
        lib_note = ("- Judged with %s: F1 is the registered logistic regression solved by Newton's method in numpy (same "
                    "objective, one optimum); F2 is the registered stand-in `HGBStandIn`." % res.get("library"))
    L += ["", "## Method notes and deviations", "", lib_note,
          "- Missing input cells (replaced by the first-half mean): %d (%s)." % (
              res["missing_cells"], ", ".join("%s %d" % kv for kv in res["missing_by_input"].items()) or "none"),
          "- Bar A is the slot after the fill bar (the earliest the page shows a b_targets position, H53 amendment); a "
          "trade that opens and closes in its own fill bar is never a signal; a trade still open at the seal, or a "
          "followable trade unfinished at the seal, is left out (counts above).",
          "- Stop and Target-1 distances are the book's plan at the decision close (entry = that close), because the fill "
          "price is the next bar's open. The decision bar is the fill bar minus 1 minus the market's fill delay.",
          "- The odds are walked from the engine's birth (2020-01-01) as H36 replayed the books; the live step walks the "
          "last 240 days.",
          "- Markets present: %s.%s" % (", ".join(res["markets_present"]),
                                        "" if "SPX" in res["markets_present"] else
                                        " SPX is MISSING: its evidence store was on an older code signature and was not "
                                        "rebuilt by the engine before the cutoff fixed in advance (16:00 UTC, 17 Nov "
                                        "2026), so it could not be read under the current code."), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None, help="one group, or several separated by commas")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("[%H:%M:%S]"), *m, flush=True)      # noqa: E731
    if args.report:
        report(log)
        return
    for g in (args.group or ",".join(GROUP_ORDER)).split(","):
        run_group(g.strip(), log)
        gc.collect()


if __name__ == "__main__":
    main()
