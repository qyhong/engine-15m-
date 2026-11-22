# -*- coding: utf-8 -*-
"""H71: BTC and ETH in an oversold state - do the engine's own odds, voices and card readings carry information about
a rebound? Registered in research/HYPOTHESES.md (H71) before this file was run. Research only; reads the evidence store
and a COPY of the cached weekly fits; changes nothing in the engine.

    python research/h71_voices_at_rebounds.py --stage discovery    --fits-dir fits/crypto
    python research/h71_voices_at_rebounds.py --stage confirmation --fits-dir fits/crypto   (needs selection.json)
    python research/h71_voices_at_rebounds.py --stage holdout      --fits-dir fits/crypto   (needs confirmation.json)
    python research/h71_voices_at_rebounds.py --report

Each stage cuts the walk and every input at its own end (prep_cut(end=...)) before anything is formed, and computes
numbers only for the readings the previous stage passed on.
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

from engine15 import data, evcache, labels, leanprep, model  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h71_voices_at_rebounds")
GROUP, ASSETS = "crypto", ["BTCUSDT", "ETHUSDT"]
SHORT = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
STAGES = {"discovery": ("2020-02-01 00:00", "2023-06-07 23:45"),
          "confirmation": ("2023-06-08 00:00", "2025-11-10 23:45"),
          "holdout": ("2025-11-11 00:00", "2026-11-21 13:45")}
VOICE_READINGS = {"v_meanrev": "meanrev", "v_pullback": "pullback", "v_momentum": "momentum", "v_structure": "structure",
                  "v_regime": "regime", "v_levels": "levels", "v_flow": "flow"}
RAW_READINGS = ["k_1h", "stretch_4h", "cvd_div", "fund_z"]
READINGS = ["lead"] + list(VOICE_READINGS) + RAW_READINGS          # the 12 registered, in order
HORIZONS = {"24h": 96, "4h": 16}
CONTROLS = {"r_1h": 4, "r_4h": 16, "r_24h": 96, "r_7d": 672}
DRAWS, SEED = 4000, 20261122
SEL_MIN, SEL_MAX = 0.02, 3
REBOUND = 0.05


# ------------------------------------------------------------------ data (h59_half_be.prep_cut, keeping the voices)
def last_session_at_or_before(ts):
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, GROUP, ASSETS[0]))
    if not st.load():
        raise RuntimeError("no evidence store for crypto")
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(pd.Timestamp(ts, tz="UTC"), side="right"))
    return str(full[k - 1])[:16]


def prep_cut_voices(fits_dir, end, voices, log=print):
    """research/h59_half_be.py::prep_cut, line for line, plus each requested voice's own lead (P(up) - P(down)),
    read from the same out-of-sample walk before its probabilities are freed."""
    stores = {}
    for a in ASSETS:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, GROUP, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (GROUP, a))
        stores[a] = st
    full = pd.DatetimeIndex(pd.to_datetime(stores[ASSETS[0]].times_ms(), unit="ms", utc=True))
    assert np.array_equal(stores[ASSETS[1]].times_ms(), stores[ASSETS[0]].times_ms())
    n = int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
    if str(full[n - 1])[:16] != end:
        raise RuntimeError("the store has no session at %s" % end)
    times = full[:n]
    cfg = dict(CFG, assets=tuple(ASSETS), birth=CFG["birth"], voting=voting_for(GROUP))
    if GROUP in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][GROUP]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in ASSETS:
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
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n, fits_dir)
    log("crypto: %d sessions to %s; voices walked from %s: %d refits, %d from the cache (%.0fs)" % (
        n, str(times[-1])[:16], cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    del models
    lo = birth_idx
    vlead = {}
    for a in ASSETS:
        vlead[a] = {}
        for name in voices:
            vi = model.VOICE_NAMES.index(VOICE_READINGS[name])
            arr = np.full(n, np.nan)
            arr[lo:] = probs[a].arr[:, vi, labels.UP] - probs[a].arr[:, vi, labels.DOWN]
            vlead[a][name] = arr
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    odds = {}
    for a in ASSETS:
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
    return {"times": times, "ev": ev, "px": px, "odds": odds, "vlead": vlead, "frep": frep}


def ema_gap(a, prep, ev):
    """(close - 1h EMA50) / ATR(1h): the stored readings where present, else built from bars as evidence.py does."""
    c = prep["px"][a]["close"]
    if "bias_ema50_1h_px" in ev.columns and ev["bias_ema50_1h_px"].notna().any():
        return (c - ev["bias_ema50_1h_px"].values.astype(float)) / ev["atr1h"].values.astype(float), "stored"
    from engine15 import indicators as ind
    df15 = data.load(a).reindex(prep["times"])
    h1 = data.resample(df15, "1h")
    e50 = data.htf_on_15(df15, "1h", h1["close"].ewm(span=50, adjust=False, min_periods=50).mean())
    return (c - np.asarray(e50, float)) / ev["atr1h"].values.astype(float), "from bars"


def frame_of(prep, a, stage, want):
    """One row per bar of the stage for coin a: state, controls, forward outcomes (inside the stage), readings."""
    t0, _ = STAGES[stage]
    times, ev, c = prep["times"], prep["ev"][a], prep["px"][a]["close"]
    n = len(times)
    lc = np.log(c)
    df = pd.DataFrame({"time": times, "close": c})
    for k, h in CONTROLS.items():
        df[k] = lc - np.r_[np.full(h, np.nan), lc[:-h]]
    lr = np.r_[np.nan, np.diff(lc)]
    df["vol24"] = pd.Series(lr).rolling(96).std().values
    for k, h in HORIZONS.items():
        f = np.full(n, np.nan)
        f[:n - h] = lc[h:] - lc[:n - h]                         # nothing past the stage's cut exists here
        df["f_" + k] = f
    df["reb"] = np.where(np.isfinite(df["f_24h"]), (np.exp(df["f_24h"]) - 1.0) >= REBOUND, np.nan)
    r24 = np.exp(df["r_24h"].values) - 1.0
    gap, gsrc = ema_gap(a, prep, ev)
    df["ret24"], df["gap"] = r24, gap
    over = (r24 <= -0.06) | (gap <= -3.0)
    mirror = (r24 >= 0.06) | (gap >= 3.0)
    known = np.isfinite(r24) & np.isfinite(gap)
    df["state"] = np.where(~known, "unknown", np.where(over, "oversold", np.where(mirror, "overbought", "calm")))
    df["bias"] = ev["htf_bias"].values.astype(float)
    odds = prep["odds"][a]
    df["lead"] = odds[:, labels.UP] - odds[:, labels.DOWN]
    for name in want:
        if name in VOICE_READINGS:
            df[name] = prep["vlead"][a][name]
        elif name in RAW_READINGS:
            df[name] = ev[name].values.astype(float) if name in ev.columns else np.nan
    keep = (df["time"] >= pd.Timestamp(t0, tz="UTC")) & np.isfinite(df["lead"])
    df = df[keep].reset_index(drop=True)
    df["month"] = df["time"].dt.year * 12 + df["time"].dt.month - 1
    df["asset"] = a
    return df, gsrc


# ------------------------------------------------------------------ statistics
def _rank(v):
    return pd.Series(v).rank().values


def _resid(v, Z):
    beta, *_ = np.linalg.lstsq(Z, v, rcond=None)
    return v - Z @ beta


def vectors(d, reading, hz, partial):
    """Centred rank vectors (x, y) and month keys for one coin, the rows where everything is known."""
    cols = [reading, "f_" + hz] + (list(CONTROLS) + ["vol24"] if partial else [])
    m = np.isfinite(d[cols].values.astype(float)).all(axis=1)
    if m.sum() < 30:
        return None
    s = d[m]
    x, yv = _rank(s[reading].values), _rank(s["f_" + hz].values)
    if partial:
        Z = np.column_stack([np.ones(len(s))] + [_rank(s[k].values) for k in list(CONTROLS) + ["vol24"]])
        x, yv = _resid(x, Z), _resid(yv, Z)
    else:
        x, yv = x - x.mean(), yv - yv.mean()
    return x, yv, s["month"].values


class Boot:
    """Month-clustered bootstrap over a fixed list of months, the same draws for every statistic of a stage."""

    def __init__(self, months):
        self.months = np.array(sorted(set(int(m) for m in months)))
        rng = np.random.default_rng(SEED)
        M = len(self.months)
        idx = rng.integers(0, M, size=(DRAWS, M))
        self.C = np.zeros((DRAWS, M))
        for b in range(DRAWS):
            self.C[b] = np.bincount(idx[b], minlength=M)

    def corr(self, parts):
        """parts: list of (x, y, months). -> point estimate, draws."""
        M = len(self.months)
        S = np.zeros((6, M))
        for x, yv, mo in parts:
            j = np.searchsorted(self.months, mo)
            for r, v in enumerate((np.ones_like(x), x, yv, x * yv, x * x, yv * yv)):
                S[r] += np.bincount(j, weights=v, minlength=M)

        def c(T):
            N, Sx, Sy, Sxy, Sxx, Syy = T
            num = Sxy - Sx * Sy / N
            den = np.sqrt(np.maximum(Sxx - Sx * Sx / N, 1e-300) * np.maximum(Syy - Sy * Sy / N, 1e-300))
            return num / den
        est = float(c(S.sum(axis=1)))
        draws = c((self.C @ S.T).T)                          # (draws, 6) -> six rows of totals
        return est, draws


def ic_cell(boot, frames, reading, hz, partial):
    """IC per coin and pooled with month-clustered 95% intervals."""
    out, parts = {}, []
    for a, d in frames.items():
        v = vectors(d, reading, hz, partial)
        if v is None:
            out[SHORT[a]] = {"n": 0}
            continue
        parts.append(v)
        est, dr = boot.corr([v])
        out[SHORT[a]] = {"n": int(len(v[0])), "months": int(len(set(v[2]))), "ic": est,
                         "lo": float(np.nanpercentile(dr, 2.5)), "hi": float(np.nanpercentile(dr, 97.5))}
    if parts:
        est, dr = boot.corr(parts)
        out["pooled"] = {"n": int(sum(len(p[0]) for p in parts)), "ic": est, "lo": float(np.nanpercentile(dr, 2.5)),
                         "hi": float(np.nanpercentile(dr, 97.5)), "_draws": dr}
    return out


def p_one_sided(est, draws, sign):
    """Share of centred draws at least as far as the estimate in the registered direction."""
    cen = draws - est
    cnt = int(np.sum(sign * cen >= sign * est))
    return (1 + cnt) / (1 + len(draws))


def hit_rates(frames, reading, cuts, state="oversold"):
    out = {}
    for a, d in frames.items():
        s = d[(d["state"] == state) & np.isfinite(d[reading]) & np.isfinite(d["reb"])]
        lo_, hi_ = cuts[a]
        top, bot = s[s[reading] > hi_], s[s[reading] <= lo_]
        out[SHORT[a]] = {"n": int(len(s)), "base_pct": float(s["reb"].mean() * 100) if len(s) else None,
                         "top_n": int(len(top)), "top_pct": float(top["reb"].mean() * 100) if len(top) else None,
                         "bottom_n": int(len(bot)), "bottom_pct": float(bot["reb"].mean() * 100) if len(bot) else None}
    return out


def readout(frames):
    """Descriptive: the combined odds' lead in the oversold state, and what the next 24 hours did."""
    d = pd.concat([f[f["state"] == "oversold"] for f in frames.values()])
    d = d[np.isfinite(d["f_24h"])]
    d["fwd_pct"] = (np.exp(d["f_24h"]) - 1.0) * 100

    def cell(s):
        if not len(s):
            return {"n": 0}
        return {"n": int(len(s)), "share_pct": float(len(s) / max(len(base), 1) * 100), "months": int(s["month"].nunique()),
                "mean_fwd_pct": float(s["fwd_pct"].mean()), "median_fwd_pct": float(s["fwd_pct"].median()),
                "rebound_pct": float(s["reb"].mean() * 100)}
    out = {}
    for label, sel in (("all", np.ones(len(d), bool)), ("bias down", d["bias"].values == -1),
                       ("bias not down", d["bias"].values != -1)):
        base = d[sel]
        L = base["lead"]
        out[label] = {"all": cell(base), "up 5+": cell(base[L >= 0.05]), "up 15+": cell(base[L >= 0.15]),
                      "between": cell(base[(L > -0.05) & (L < 0.05)]), "down 5+": cell(base[L <= -0.05])}
        for a in ASSETS:
            b2 = base[base["asset"] == a]
            out[label][SHORT[a] + " up 5+ share_pct"] = float((b2["lead"] >= 0.05).mean() * 100) if len(b2) else None
    return out


def counts(frames):
    out = {}
    for a, d in frames.items():
        vc = d["state"].value_counts()
        ov = d[d["state"] == "oversold"]
        out[SHORT[a]] = {"bars": int(len(d)), "from": str(d["time"].iloc[0])[:16], "to": str(d["time"].iloc[-1])[:16],
                         "states": dict((k, int(v)) for k, v in vc.items()), "oversold_months": int(ov["month"].nunique()),
                         "oversold_rebound_base_pct": float(np.nanmean(ov["reb"]) * 100) if len(ov) else None,
                         "calm_rebound_base_pct": float(np.nanmean(d[d["state"] == "calm"]["reb"]) * 100)}
    return out


def strip(o):
    if isinstance(o, dict):
        return dict((k, strip(v)) for k, v in o.items() if not k.startswith("_"))
    return o


# ------------------------------------------------------------------ stages
def load_stage(stage, want, fits_dir, log):
    end = last_session_at_or_before(STAGES[stage][1])
    log("%s: cut at %s; readings %s" % (stage, end, ", ".join(want)))
    prep = prep_cut_voices(fits_dir, end, [w for w in want if w in VOICE_READINGS], log=log)
    frames, gsrc = {}, {}
    for a in ASSETS:
        frames[a], gsrc[a] = frame_of(prep, a, stage, want)
    frep = prep["frep"]
    del prep
    gc.collect()
    return frames, {"cut": end, "ema_gap_source": gsrc, "refits": frep["refits"], "reused": frep["reused"]}


def measures(frames, want):
    res = {}
    boots = {}
    for st in ("oversold", "calm"):
        mo = np.concatenate([d.loc[d["state"] == st, "month"].values for d in frames.values()])
        boots[st] = Boot(mo)
    for r in want:
        res[r] = {}
        for st in ("oversold", "calm"):
            sub = dict((a, d[d["state"] == st]) for a, d in frames.items())
            res[r][st] = {}
            for hz in HORIZONS:
                for kind, partial in (("raw", False), ("partial", True)):
                    res[r][st]["%s_%s" % (kind, hz)] = ic_cell(boots[st], sub, r, hz, partial)
    return res


def discovery(fits_dir, log):
    frames, meta = load_stage("discovery", READINGS, fits_dir, log)
    cuts = {}
    for r in READINGS:
        cuts[r] = {}
        for a, d in frames.items():
            s = d.loc[d["state"] == "oversold", r]
            s = s[np.isfinite(s)]
            cuts[r][a] = [float(s.quantile(1 / 3)), float(s.quantile(2 / 3))] if len(s) else [np.nan, np.nan]
    res = measures(frames, READINGS)
    cand = []
    for r in READINGS:
        c = res[r]["oversold"]["partial_24h"]
        b, e, p = c.get("BTC", {}), c.get("ETH", {}), c.get("pooled", {})
        ok = (b.get("n", 0) and e.get("n", 0) and p.get("n", 0) and np.sign(b["ic"]) == np.sign(e["ic"]) != 0
              and (p["lo"] > 0 or p["hi"] < 0) and abs(p["ic"]) >= SEL_MIN and np.sign(p["ic"]) == np.sign(b["ic"]))
        res[r]["selection_check"] = {"same_sign_btc_eth": bool(b.get("n", 0) and e.get("n", 0) and np.sign(b["ic"]) == np.sign(e["ic"])),
                                     "pooled_interval_excludes_zero": bool(p.get("n", 0) and (p["lo"] > 0 or p["hi"] < 0)),
                                     "abs_pooled_at_least_0.02": bool(p.get("n", 0) and abs(p["ic"]) >= SEL_MIN), "qualifies": bool(ok)}
        res[r]["hits"] = hit_rates(frames, r, cuts[r])
        if ok:
            cand.append((abs(p["ic"]), r, float(np.sign(p["ic"]))))
    cand.sort(reverse=True)
    sel = [{"reading": r, "sign": s, "pooled_partial_ic": float(res[r]["oversold"]["partial_24h"]["pooled"]["ic"])}
           for _, r, s in cand[:SEL_MAX]]
    out = {"stage": "discovery", "meta": meta, "counts": counts(frames), "cuts": cuts, "readings": strip(res),
           "qualified": [r for _, r, _ in cand], "readout": readout(frames)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "discovery.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    with open(os.path.join(OUT, "selection.json"), "w") as f:
        json.dump({"written_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "selected": sel,
                   "nothing_to_confirm": not sel}, f, indent=1)
    log("discovery: qualified %s; selected %s" % ([r for _, r, _ in cand], [s["reading"] for s in sel]))


def later(stage, fits_dir, log):
    prev = os.path.join(OUT, "selection.json" if stage == "confirmation" else "confirmation.json")
    if not os.path.exists(prev):
        raise SystemExit("%s needs %s first" % (stage, prev))
    with open(prev) as f:
        P = json.load(f)
    items = P["selected"] if stage == "confirmation" else P["passed"]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, stage + ".json")
    if not items:
        with open(path, "w") as f:
            json.dump({"stage": stage, "not_opened": True, "why": "nothing to carry from the previous stage",
                       "passed": []}, f, indent=1)
        log("%s: nothing to carry; the stage's data were not loaded" % stage)
        return
    with open(os.path.join(OUT, "discovery.json")) as f:
        cuts = json.load(f)["cuts"]
    want = [it["reading"] for it in items]
    frames, meta = load_stage(stage, want, fits_dir, log)
    res = measures(frames, want)
    k = len(items)
    passed = []
    for it in items:
        r, sgn = it["reading"], it["sign"]
        c = res[r]["oversold"]["partial_24h"]
        p = c.get("pooled", {})
        pv = p_one_sided(p["ic"], p["_draws"], sgn) if p.get("n", 0) else 1.0
        if stage == "confirmation":
            ok = (c["BTC"].get("n", 0) and c["ETH"].get("n", 0) and np.sign(c["BTC"]["ic"]) == sgn
                  and np.sign(c["ETH"]["ic"]) == sgn and pv < 0.05 / k)
        else:
            ok = p.get("n", 0) and np.sign(p["ic"]) == sgn and pv < 0.05 / k
        res[r]["test"] = {"sign": sgn, "one_sided_p": pv, "threshold": 0.05 / k, "passed": bool(ok)}
        res[r]["hits"] = hit_rates(frames, r, cuts[r])
        if ok:
            passed.append({"reading": r, "sign": sgn})
    out = {"stage": stage, "meta": meta, "counts": counts(frames), "readings": strip(res), "passed": passed}
    if stage == "confirmation":
        out["readout"] = readout(frames)
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=float)
    log("%s: passed %s" % (stage, [p["reading"] for p in passed]))


def readout_confirmation(fits_dir, log):
    """The registered descriptive read-out for the confirmation period, on its own: the combined odds' lead buckets
    only (no tested reading is loaded or measured), for when nothing was selected for the confirmation stage."""
    frames, meta = load_stage("confirmation", [], fits_dir, log)
    out = {"stage": "readout-confirmation", "meta": meta, "counts": counts(frames), "readout": readout(frames)}
    with open(os.path.join(OUT, "readout_confirmation.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    log("readout for the confirmation period written")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(STAGES) + ["readout-confirmation"])
    ap.add_argument("--fits-dir", default=None)
    a = ap.parse_args(argv)
    t0 = time.time()

    def log(m):
        print("[%5.0fs] %s" % (time.time() - t0, m), flush=True)
    if a.stage == "discovery":
        discovery(a.fits_dir, log)
    elif a.stage == "readout-confirmation":
        readout_confirmation(a.fits_dir, log)
    elif a.stage:
        later(a.stage, a.fits_dir, log)


if __name__ == "__main__":
    main()
