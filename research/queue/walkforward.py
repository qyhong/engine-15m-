# -*- coding: utf-8 -*-
"""Queue family H90-H101: WALK-FORWARD tests of one setting of the Setups rule at a time. Research only; registered in
research/HYPOTHESES.md (H90-H101) before any number. Every book is the engine's own shadows.run under the b_targets rule;
one setting is varied through (1) a cfg override, or (2) an entry filter OR-ed into the `guard` input. Reads the evidence
store and the cached fits; changes nothing in the engine.

    python research/queue/walkforward.py --study H90 --fits-dir <fits_today> --out <out dir>
    python research/queue/walkforward.py --study H90 --estimate          (CPU hours, one number)
    python research/queue/walkforward.py --study H90 --fits-dir ... --out ... --smoke   (tiny version, out/smoke/)

THE ORDER, enforced in code (see run_study):
  1. CHOICE: every grid value on the choice period. The data are loaded ONLY up to CHOICE_LAST (the test period is not
     in memory). The choice is written to choice.json.
  2. TEST: only the current setting and the chosen one (test_book refuses any other key while verdict.json is absent).
     The paired monthly statistic is computed and written to verdict.json.
  3. DESCRIPTIVE: only now the other grid values on the test period, marked "descriptive, not used for any choice".
THE HOLDOUT: nothing at or after 2025-11-11 is loaded. wall() is the one place that enforces DATA_END.
"""
import argparse
import gc
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

# ---------------------------------------------------------------------------------------------------- fixed by H90-H101
DATA_END = "2025-11-10 23:45"           # THE HOLDOUT WALL: the last session that may be loaded (wall() enforces it)
CHOICE_LAST = "2023-06-07 23:45"        # the choice period ends at the last stored session at or before this
TEST_FIRST = "2023-06-08 00:00"         # the test period starts at the first session at or after this
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
SEED = 20261122
DRAWS = 20000                           # month-clustered bootstrap draws (registered: at least 5,000)
N_PART_A = 12                           # H90-H101: the Bonferroni count of Part A
ALPHA = 0.05 / N_PART_A
START = shadows.START_EQUITY
NEVER_IDLE = 10 ** 9                    # idle_max "never forced"
NEVER_FLIP = 9.0                        # theta_flip "never flip" (an edge is at most 1.0)
TRAIL_DAYS, MIN_DAYS = 90, 30           # the masks' trailing window; fewer days with bars than MIN_DAYS: no block
MIN_MONTHS = 12                         # a bootstrap over fewer months passes nothing (only a smoke run has fewer)
FAMILY = ["H90", "H91", "H92", "H93", "H94", "H95", "H96", "H97", "H98", "H99", "H100"]
# the current setting as registered (think15-v5.2.9); check_current() refuses to run if the engine has moved
CURRENT = {"stop_units": 2.0, "idle_max": 4, "theta_enter": 0.05, "theta_enter_shock": 0.10, "theta_flip": 0.10,
           "theta_counter": 0.15, "htf_bias": True, "trend_tiebreak": True, "step_aside": False, "release_guard": True}
# measured on the research server (22 Nov 2026, nice 19, one thread): seconds per group load and per book run
PREP_S = {"choice": {"crypto": 15.0, "metals": 10.0, "fx": 7.0, "index": 2.0, "energy": 9.0},     # measured x 1.5
          "test": {"crypto": 26.0, "metals": 17.0, "fx": 11.0, "index": 3.0, "energy": 15.0}}
RUN_S = {"choice": 4.0, "test": 5.0}    # an unmasked book ~0.4 s, a volatility-masked one up to ~4.7 s (crypto, test)


class HoldoutError(RuntimeError):
    pass


class PeekError(RuntimeError):
    pass


class NotReady(RuntimeError):
    pass


def S(cfg=None, mask=None):
    return {"cfg": dict(cfg or {}), "mask": list(mask or [])}


def _grid(key, vals, fmt="%g"):
    return [(("%s=" + fmt) % (key, v), S({key: v})) for v in vals]


STUDIES = {
    "H90": {"title": "the stop distance (stop_units)", "current": "stop_units=2",
            "grid": _grid("stop_units", (1.0, 1.5, 2.0, 2.5, 3.0, 4.0))},
    "H91": {"title": "the forced-entry clock (idle_max)", "current": "idle_max=4",
            "grid": _grid("idle_max", (2, 4, 8, 16, 48)) + [("idle_max=never", S({"idle_max": NEVER_IDLE}))]},
    "H92": {"title": "the entry bar (theta_enter)", "current": "theta_enter=0.05",
            "grid": _grid("theta_enter", (0.02, 0.03, 0.05, 0.08, 0.10))},
    "H93": {"title": "the flip bar (theta_flip)", "current": "theta_flip=0.1",
            "grid": _grid("theta_flip", (0.05, 0.10, 0.15, 0.20)) + [("theta_flip=never", S({"theta_flip": NEVER_FLIP}))]},
    "H94": {"title": "the counter-bias entry bar (theta_counter)", "current": "theta_counter=0.15",
            "grid": _grid("theta_counter", (0.05, 0.10, 0.15, 0.25))},
    "H95": {"title": "the higher-timeframe bias and the trend tiebreak", "current": "bias=on,tiebreak=on",
            "grid": [("bias=on,tiebreak=on", S()), ("bias=on,tiebreak=off", S({"trend_tiebreak": False})),
                     ("bias=off,tiebreak=on", S({"htf_bias": False})),
                     ("bias=off,tiebreak=off", S({"htf_bias": False, "trend_tiebreak": False}))]},
    "H96": {"title": "no new entry when the stop would be unusually tight", "current": "none",
            "grid": [("none", S())] + [("tight_q=%g" % q, S(mask=[{"kind": "tight_stop", "q": q}])) for q in (0.2, 0.33, 0.5)]},
    "H97": {"title": "no new entry in one 6-hour block of the day (UTC)", "current": "none",
            "grid": [("none", S())] + [("block_%02d-%02d" % (h, h + 6), S(mask=[{"kind": "hours", "h0": h, "h1": h + 6}]))
                                       for h in (0, 6, 12, 18)]},
    "H98": {"title": "no new entry at the weekend (BTC and ETH only)", "current": "none",
            "grid": [("none", S()), ("sat_sun", S(mask=[{"kind": "weekend", "mode": "sat_sun"}])),
                     ("fri21_sun21", S(mask=[{"kind": "weekend", "mode": "fri21_sun21"}]))]},
    "H99": {"title": "no new entry when 24-hour realised volatility is in a trailing third", "current": "none",
            "grid": [("none", S()), ("block_top_third", S(mask=[{"kind": "vol", "third": "top"}])),
                     ("block_bottom_third", S(mask=[{"kind": "vol", "third": "bottom"}]))]},
    "H100": {"title": "the high-risk rules (theta_enter_shock, step_aside)", "current": "shock=0.1,step_aside=off",
             "grid": [("shock=%g,step_aside=%s" % (t, "on" if sa else "off"), S({"theta_enter_shock": t, "step_aside": sa}))
                      for t in (0.05, 0.10, 0.20) for sa in (False, True)]},
    "H101": {"title": "the kitchen sink: every chosen setting of H90-H100 stacked, tested once", "current": "current",
             "grid": None},
}


# ---------------------------------------------------------------------------------------------------- small helpers
def wall(limit):
    """THE HOLDOUT WALL. Every load goes through here: a limit after DATA_END is refused."""
    t = pd.Timestamp(limit, tz="UTC") if not isinstance(limit, pd.Timestamp) else limit
    if t > pd.Timestamp(DATA_END, tz="UTC"):
        raise HoldoutError("refused: %s is after the holdout wall %s" % (t, DATA_END))
    return t


def jdump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, default=_jsonable)
    os.replace(tmp, path)


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if x != x else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def check_current():
    bad = dict((k, (CFG.get(k), v)) for k, v in CURRENT.items() if CFG.get(k) != v)
    if bad:
        raise RuntimeError("the engine's constants differ from the registered current setting: %s" % bad)


def canonical(spec, a):
    """The spec as it acts on market a: cfg overrides equal to the base value dropped, weekend masks dropped off
    BTC/ETH. The current setting is S() on every market. -> (canonical spec, key)"""
    base = shadows.asset_cfg(a, dict(CFG))
    cfg = dict((k, v) for k, v in sorted(spec["cfg"].items()) if base.get(k) != v)
    mask = [m for m in spec["mask"] if not (m["kind"] == "weekend" and a not in VAULT)]
    c = {"cfg": cfg, "mask": mask}
    return c, hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------------------------------- the masks
def _trail_quantiles(close_ms, vals, qs, days=TRAIL_DAYS, min_days=MIN_DAYS):
    """For each bar: the qs-quantiles of `vals` over the bars whose decision close falls in the `days` whole UTC days
    BEFORE this bar's UTC day (so only bars closed before this one). Fewer than min_days days with a value: NaN."""
    day = close_ms // 86400000
    ok = np.isfinite(vals)
    out = np.full((len(vals), len(qs)), np.nan)
    uday = np.unique(day)
    order = np.argsort(day, kind="stable")
    d_sorted = day[order]
    for D in uday:
        a0 = np.searchsorted(d_sorted, D - days, side="left")
        a1 = np.searchsorted(d_sorted, D, side="left")
        sel = order[a0:a1]
        sel = sel[ok[sel]]
        if len(sel) == 0 or len(np.unique(day[sel])) < min_days:
            continue
        qv = np.quantile(vals[sel], qs)
        out[day == D] = qv
    return out


def realised_vol_24h(close_ms, close):
    """sqrt of the sum of squared 15m log returns of the bars that closed in the last 24 hours (this bar included)."""
    r = np.full(len(close), np.nan)
    r[1:] = np.log(close[1:] / close[:-1])
    s = pd.Series(np.where(np.isfinite(r), r * r, 0.0), index=pd.to_datetime(close_ms, unit="ms", utc=True))
    cnt = pd.Series(np.isfinite(r).astype(float), index=s.index)
    tot = s.rolling("24h").sum().values
    n = cnt.rolling("24h").sum().values
    out = np.sqrt(tot)
    out[n < 1] = np.nan
    return out


def build_mask(mask_specs, a, close_ms, close, unit):
    """True where this market opens nothing new at that close (OR of the specs). Only readings known at the bar's close:
    the close time itself, the close, the volatility unit at that close, and bars closed earlier."""
    n = len(close)
    if not mask_specs:
        return None
    m = np.zeros(n, dtype=bool)
    ts = pd.to_datetime(close_ms, unit="ms", utc=True)
    for sp in mask_specs:
        k = sp["kind"]
        if k == "hours":
            h = np.asarray(ts.hour)
            m |= (h >= sp["h0"]) & (h < sp["h1"])
        elif k == "weekend":
            if a not in VAULT:
                continue
            wd, h = np.asarray(ts.weekday), np.asarray(ts.hour)
            if sp["mode"] == "sat_sun":
                m |= wd >= 5
            elif sp["mode"] == "fri21_sun21":
                m |= ((wd == 4) & (h >= 21)) | (wd == 5) | ((wd == 6) & (h < 21))
            else:
                raise ValueError(sp)
        elif k == "tight_stop":
            ratio = np.asarray(unit, dtype=float) / np.asarray(close, dtype=float)
            q = _trail_quantiles(close_ms, ratio, [sp["q"]])[:, 0]
            m |= np.isfinite(q) & np.isfinite(ratio) & (ratio <= q)
        elif k == "vol":
            rv = realised_vol_24h(close_ms, np.asarray(close, dtype=float))
            q = _trail_quantiles(close_ms, rv, [1.0 / 3.0, 2.0 / 3.0])
            if sp["third"] == "top":
                m |= np.isfinite(q[:, 1]) & np.isfinite(rv) & (rv >= q[:, 1])
            else:
                m |= np.isfinite(q[:, 0]) & np.isfinite(rv) & (rv <= q[:, 0])
        else:
            raise ValueError(sp)
    return m


def merge_guard(guard, m, n):
    """The market's real guard OR the study's mask. bool() of each real value is kept exactly as policy.decide reads it."""
    if m is None:
        return guard
    g0 = np.zeros(n, dtype=bool) if guard is None else np.array([bool(x) for x in guard], dtype=bool)
    return g0 | m


# ---------------------------------------------------------------------------------------------------- loading (one place)
def last_session(g, assets, limit):
    from engine15 import evcache
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, g, assets[0]))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (g, assets[0]))
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(wall(limit), side="right"))
    return str(full[k - 1])[:16]


def fits_overlay(fits_root, g, out):
    """A folder of links to the given fits, so a cache miss writes into our own output and never into fits_root."""
    src = os.path.join(fits_root, g)
    dst = os.path.join(out, "fits_overlay", g)
    if not os.path.isdir(src):
        return src
    os.makedirs(dst, exist_ok=True)
    try:
        have = set(os.listdir(dst))
        for f in os.listdir(src):
            if f not in have:
                os.symlink(os.path.join(os.path.abspath(src), f), os.path.join(dst, f))
        return dst
    except (OSError, NotImplementedError):
        return src


def book_columns():
    """The evidence columns the Setups book reads (shadows.book_inputs, shadows.aux_from_ev, plan_targets via row_of)."""
    cols = ["shock", "tide", "atr1h", "htf_bias", "release_soon", "atr15", "sw_lo_15m", "sw_hi_15m", "sw_lo_1h", "sw_hi_1h",
            "reach_1h_med_pct", "reach_4h_med_pct"] + list(shadows.TARGET_COLS)
    for tf in shadows.PB_FIB_TFS:
        cols += ["fib_%s_dir" % tf, "fib_%s_broken" % tf, "fib_%s_r500_px" % tf, "fib_%s_entry_px" % tf]
    cols += ["ma_%s_%s_px" % (tf, m) for tf in shadows.PB_MA_TFS for m in shadows.PB_MAS]
    return list(dict.fromkeys(cols))


def prep_cut_lean(group, assets, fits_dir, end, log=print):
    """research/h59_half_be.prep_cut, line for line, with two memory savings and nothing else changed: the evidence frame
    keeps only the book's columns (book_columns), and the "which voices speak" mask is computed in row chunks instead of
    materialising the whole feature matrix (h59 peaks near 3 GB on crypto; this stays well under). The tests and the smoke
    check compare its odds and books with h59.prep_cut."""
    import gc as _gc
    from engine15 import evcache, labels, leanprep, model
    from engine15.config import voting_for
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
    n = int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
    if str(full[n - 1])[:16] != end:
        raise RuntimeError("%s: the store has no session at %s (last <= it: %s)" % (group, end, full[n - 1]))
    times = full[:n]
    cfg = dict(CFG, assets=tuple(assets), birth=CFG["birth"], voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    keep = book_columns()
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        f = st.frame(full)
        ev[a] = f[[c for c in keep if c in f.columns]].iloc[:n]
        del f
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
        speaks = np.zeros((n - lo, len(model.VOICE_NAMES)), dtype=bool)
        for r0 in range(lo, n, 20000):                           # chunks of rows: the same values as h59's one block
            r1 = min(n, r0 + 20000)
            Xa = np.asarray(X[a][r0:r1])
            for j, v in enumerate(model.VOICE_NAMES):
                if model._COLS[v]:
                    speaks[r0 - lo:r1 - lo, j] = np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0
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
    _gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds, "birth_idx": birth_idx}


def load_prep(g, assets, fits_root, limit, out, log=print):
    """THE ONLY LOADER. The group's inputs up to the last stored session at or before `limit` (never after DATA_END)."""
    end = last_session(g, assets, limit)
    prep = prep_cut_lean(g, assets, fits_overlay(fits_root, g, out), end, log=log)
    if prep["times"][-1] > wall(limit):
        raise HoldoutError("loaded past the limit")
    return prep


# ---------------------------------------------------------------------------------------------------- one book run
def market_window(prep, a):
    n = len(prep["times"])
    ok = np.isfinite(prep["odds"][a][:, 0])
    lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
    return lo, n


def run_book(prep, a, spec, lo, hi, aux):
    """b_targets as it runs now, with spec's cfg overrides and mask, by the engine's own shadows.run."""
    times = prep["times"]
    tms = data.to_ms(times)
    cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    cfg.update(spec["cfg"])
    rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
    inp = shadows.book_inputs(prep, a)
    n = len(times)
    m = build_mask(spec["mask"], a, tms + CFG["bar_ms"], prep["px"][a]["close"], inp["unit"])
    if m is not None and not cfg.get("release_guard"):
        raise RuntimeError("a mask needs release_guard on")
    guard = merge_guard(inp["guard"], m, n)
    tgt = aux["targets"]
    return shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, hi, bias=inp["bias"],
                       guard=guard, rule=rule, aux=aux, times_ms=tms,
                       row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))


def book_record(b, times, lo, hi, with_equity):
    tr = b["trades"]
    tr = tr[(tr.i_in >= lo) & (tr.i_in < hi)]
    rec = {"trades": [[int(t), int(o) if o == o else None, int(s), None if r != r else float(r), float(p), str(wi), str(wo)]
                      for t, o, s, r, p, wi, wo in zip(tr.t_in_ms, tr.t_out_ms, tr.side, tr.r_mult, tr.pnl_usd, tr.why_in,
                                                       tr.why_out)],
           "bars": int(hi - lo), "flat_bars": int((b["held"][lo:hi] == 0).sum()),
           "first": str(times[lo])[:16], "last": str(times[hi - 1])[:16]}
    eq = b["equity"][lo:hi]
    base = START
    rec["net"] = float(eq[np.isfinite(eq)][-1] - base) if np.isfinite(eq).any() else 0.0
    if with_equity:
        rec["eq_ms"] = data.to_ms(times[lo:hi]).tolist()
        rec["eq"] = [None if v != v else round(float(v), 4) for v in eq]
    return rec


def sum_r(rec):
    return float(sum(t[3] for t in rec["trades"] if t[3] is not None))


# ---------------------------------------------------------------------------------------------------- the statistics
def choose(order, current, pooled, vault):
    """The registered choice: largest pooled sum of R among values whose BTC+ETH sum of R is at least the current
    setting's. Ties: the current setting first, then grid order."""
    elig = [k for k in order if vault[k] >= vault[current] - 1e-9]
    best = max(pooled[k] for k in elig)
    tied = [k for k in elig if pooled[k] >= best - 1e-9]
    return current if current in tied else tied[0]


def month_keys(first, last):
    p0, p1 = pd.Timestamp(first).to_period("M"), pd.Timestamp(last).to_period("M")
    return [str(p) for p in pd.period_range(p0, p1, freq="M")]


def monthly_r(rec, months):
    """sum of R and number of closed trades by calendar month of entry (UTC)."""
    idx = dict((m, i) for i, m in enumerate(months))
    s, c = np.zeros(len(months)), np.zeros(len(months))
    for t in rec["trades"]:
        if t[3] is None:
            continue
        m = str(pd.Timestamp(t[0], unit="ms", tz="UTC").tz_localize(None).to_period("M"))
        if m in idx:
            s[idx[m]] += t[3]
            c[idx[m]] += 1
    return s, c


def boot_mean(d, draws=DRAWS, seed=SEED):
    """Month-clustered bootstrap of the mean of d (one value per calendar month): whole months with replacement.
    -> mean, 95% percentile interval, one-sided p = (1 + #{mean* <= 0}) / (draws + 1)."""
    d = np.asarray(d, dtype=float)
    M = len(d)
    rng = np.random.default_rng(seed)
    means = np.empty(draws)
    for a0 in range(0, draws, 2000):
        k = min(2000, draws - a0)
        means[a0:a0 + k] = d[rng.integers(0, M, size=(k, M))].mean(axis=1)
    return {"mean": float(d.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)),
            "p_one_sided": float((1 + (means <= 0).sum()) / (draws + 1)), "months": M, "draws": draws}


def boot_ratio(s, c, draws=DRAWS, seed=SEED + 1):
    """Mean R per trade, month-clustered: resample months, sum R / trades."""
    s, c = np.asarray(s, float), np.asarray(c, float)
    M = len(s)
    rng = np.random.default_rng(seed)
    out = []
    for a0 in range(0, draws, 2000):
        k = min(2000, draws - a0)
        ix = rng.integers(0, M, size=(k, M))
        cs = c[ix].sum(axis=1)
        out.append(np.where(cs > 0, s[ix].sum(axis=1) / np.where(cs > 0, cs, 1), np.nan))
    v = np.concatenate(out)
    v = v[np.isfinite(v)]
    return {"mean_r": float(s.sum() / c.sum()) if c.sum() else None,
            "lo": float(np.percentile(v, 2.5)) if len(v) else None, "hi": float(np.percentile(v, 97.5)) if len(v) else None,
            "trades": int(c.sum())}


def worst_fall_pooled(recs):
    cs = []
    for rec in recs:
        if rec.get("eq"):
            cs.append(pd.Series(np.array([np.nan if v is None else v for v in rec["eq"]], float),
                                index=pd.to_datetime(rec["eq_ms"], unit="ms", utc=True)))
    if not cs:
        return 0.0
    tot = pd.concat(cs, axis=1).sort_index().ffill().fillna(START).sum(axis=1).values
    return float(np.min(tot / np.maximum.accumulate(tot) - 1.0) * 100.0)


def verdict_stats(cur, cho, months, markets, alpha=ALPHA):
    """cur/cho: {market: test record}. The registered statistic: per calendar month, the eight markets' summed
    (chosen - current) R; its mean with a month-clustered bootstrap; pass = p < alpha AND BTC+ETH difference >= 0."""
    D = np.zeros(len(months))
    per = {}
    S_cur, C_cur, S_cho, C_cho = (np.zeros(len(months)) for _ in range(4))
    for a in markets:
        s1, c1 = monthly_r(cur[a], months)
        s2, c2 = monthly_r(cho[a], months)
        D += s2 - s1
        S_cur += s1
        C_cur += c1
        S_cho += s2
        C_cho += c2
        per[a] = {"current_sum_r": float(s1.sum()), "chosen_sum_r": float(s2.sum()), "diff": float((s2 - s1).sum()),
                  "current_trades": int(c1.sum()), "chosen_trades": int(c2.sum())}
    vault_diff = float(sum(per[a]["diff"] for a in markets if a in VAULT))
    b = boot_mean(D)
    passed = bool(b["p_one_sided"] < alpha and vault_diff >= 0 and len(months) >= MIN_MONTHS)
    return {"monthly_diff": D.tolist(), "months": months, "boot": b, "alpha": alpha, "vault_diff": vault_diff,
            "pooled_diff": float(D.sum()), "per_market": per, "passed": passed,
            "conclusion": "beats the current setting on later data" if passed else "does not",
            "mean_r": {"current": boot_ratio(S_cur, C_cur), "chosen": boot_ratio(S_cho, C_cho)},
            "worst_fall": {"current": worst_fall_pooled([cur[a] for a in markets]),
                           "chosen": worst_fall_pooled([cho[a] for a in markets])},
            "flat_pct": {"current": float(np.mean([cur[a]["flat_bars"] / max(cur[a]["bars"], 1) * 100 for a in markets])),
                         "chosen": float(np.mean([cho[a]["flat_bars"] / max(cho[a]["bars"], 1) * 100 for a in markets]))},
            "trades": {"current": int(C_cur.sum()), "chosen": int(C_cho.sum())},
            "net": {"current": float(sum(cur[a]["net"] for a in markets)), "chosen": float(sum(cho[a]["net"] for a in markets))}}


# ---------------------------------------------------------------------------------------------------- the study
class Ctx:
    def __init__(self, study, out, fits_root, smoke=False, log=print):
        self.study, self.out, self.fits_root, self.smoke, self.log = study, out, fits_root, smoke, log
        self.groups = [("crypto", ["BTCUSDT", "ETHUSDT"])] if smoke else GROUPS
        self.markets = [a for _g, ass in self.groups for a in ass]
        self.choice_last = "2020-03-31 23:45" if smoke else CHOICE_LAST
        self.test_first = "2020-04-01 00:00" if smoke else TEST_FIRST
        self.test_last = "2020-04-20 23:45" if smoke else DATA_END
        wall(self.choice_last), wall(self.test_last)
        self.t0 = time.time()
        self.started = utcnow()
        self.done_here = 0
        os.makedirs(os.path.join(out, "runs", "choice"), exist_ok=True)
        os.makedirs(os.path.join(out, "runs", "test"), exist_ok=True)

    def path(self, *p):
        return os.path.join(self.out, *p)

    def run_path(self, period, a, key):
        return self.path("runs", period, "%s__%s.json" % (a, key))


def study_grid(ctx):
    st = STUDIES[ctx.study]
    if ctx.study != "H101":
        grid = st["grid"]
        if ctx.smoke:
            keep = [st["current"]] + [k for k, _s in grid if k != st["current"]][:1]
            grid = [(k, s) for k, s in grid if k in keep]
        return grid, st["current"]
    return kitchen_sink(ctx), "current"


def kitchen_sink(ctx):
    """H101: the chosen value of each of H90-H100, read from their choice.json in the queue's sibling folders."""
    parent = os.path.dirname(os.path.abspath(ctx.out))
    if ctx.smoke:
        parent = os.path.dirname(parent)                    # <queue out>/H101/smoke -> <queue out>
    cfg, mask, src = {}, [], {}
    for sid in FAMILY:
        p = os.path.join(parent, sid, "smoke" if ctx.smoke else "", "choice.json")
        if not os.path.exists(p):
            if ctx.smoke:
                continue
            raise NotReady("H101 needs %s (run %s first)" % (p, sid))
        ch = jload(p)
        src[sid] = {"chosen": ch["chosen"], "current": ch["current"], "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
        if ch["chosen"] != ch["current"]:
            sp = ch["specs"][ch["chosen"]]
            for k, v in sp["cfg"].items():
                if k in cfg and cfg[k] != v:
                    raise RuntimeError("H101: two studies set %s differently" % k)
                cfg[k] = v
            mask += sp["mask"]
    if ctx.smoke and not src:
        cfg, mask = {"stop_units": 1.5}, [{"kind": "hours", "h0": 0, "h1": 6}]
    ctx.sources = src
    return [("current", S()), ("stacked", S(cfg, mask))]


def needed(ctx, grid, period, keys):
    """[(group, assets, [(label, market, canonical spec, key) still to run])]."""
    todo = []
    specs = dict(grid)
    for g, assets in ctx.groups:
        rows, seen = [], set()
        for lab in keys:
            for a in assets:
                c, k = canonical(specs[lab], a)
                if (a, k) in seen or os.path.exists(ctx.run_path(period, a, k)):
                    continue
                seen.add((a, k))
                rows.append((lab, a, c, k))
        todo.append((g, assets, rows))
    return todo


def write_progress(ctx, done, total, phase):
    el = time.time() - ctx.t0
    left = (total - done) * (el / ctx.done_here) if ctx.done_here else estimate_hours(ctx.study, remaining=total - done) * 3600
    jdump(ctx.path("progress.json"), {"study": ctx.study, "phase": phase, "done": int(done), "total": int(total),
                                      "started_utc": ctx.started, "updated_utc": utcnow(),
                                      "est_hours_left": round(left / 3600.0, 3), "smoke": ctx.smoke})


def count_runs(ctx, grid, current, chosen=None):
    """(done, total) over all three phases, in distinct book runs."""
    specs = dict(grid)
    done = total = 0
    phases = [("choice", [k for k, _s in grid])] if ctx.study != "H101" else []
    if chosen is None or chosen != current:
        phases.append(("test", [k for k, _s in grid]))
    for period, keys in phases:
        for a in ctx.markets:
            ks = set(canonical(specs[lab], a)[1] for lab in keys)
            total += len(ks)
            done += sum(os.path.exists(ctx.run_path(period, a, k)) for k in ks)
    return done, total


def run_phase(ctx, grid, period, keys, limit, lo_from=None, with_equity=False, gate=None, verify_current=False):
    """Run every (label, market) of `keys` on `period` not yet checkpointed; one market group in memory at a time."""
    current = study_grid(ctx)[1] if ctx.study != "H101" else "current"
    for g, assets, rows in needed(ctx, grid, period, keys):
        if not rows:
            continue
        if gate is not None:
            for lab, _a, _c, _k in rows:
                gate(lab)
        prep = load_prep(g, assets, ctx.fits_root, limit, ctx.out, log=ctx.log)
        times = prep["times"]
        for a in assets:
            mine = [r for r in rows if r[1] == a]
            if not mine:
                continue
            lo, n = market_window(prep, a)
            if lo_from is not None:
                lo = max(lo, int(times.searchsorted(pd.Timestamp(lo_from, tz="UTC"))))
            if lo >= n - 1:
                raise RuntimeError("%s: no bars in the %s period" % (a, period))
            aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
            for lab, _a, c, k in mine:
                t1 = time.time()
                b = run_book(prep, a, c, lo, n, aux)
                if verify_current and not c["cfg"] and not c["mask"]:
                    ref = shadows.run_challenger("b_targets", prep, a, lo, n, aux=aux)
                    if not (len(ref["trades"]) == len(b["trades"]) and np.allclose(ref["equity"][lo:n], b["equity"][lo:n],
                                                                                   equal_nan=True)):
                        raise RuntimeError("%s: the current spec is not the engine's own b_targets book" % a)
                rec = book_record(b, times, lo, n, with_equity)
                rec.update(spec=c, label=lab, market=a, period=period, seconds=round(time.time() - t1, 1))
                jdump(ctx.run_path(period, a, k), rec)
                ctx.done_here += 1
                d, tot = count_runs(ctx, grid, current)
                write_progress(ctx, d, tot, period)
                ctx.log("%s %s %s %s: %d trades (%.0fs)" % (ctx.study, period, a, lab, len(rec["trades"]), time.time() - t1))
        del prep
        gc.collect()


def load_runs(ctx, grid, period, labels):
    specs = dict(grid)
    out = {}
    for lab in labels:
        out[lab] = {}
        for a in ctx.markets:
            out[lab][a] = jload(ctx.run_path(period, a, canonical(specs[lab], a)[1]))
    return out


def allowed_test_labels(ctx):
    """Which grid values may be computed on the TEST period: the current and the chosen setting, read from choice.json
    on disk; the rest only after verdict.json exists (the descriptive table)."""
    p = ctx.path("choice.json")
    if not os.path.exists(p):
        raise PeekError("no choice.json: the test period cannot be computed before the choice is written")
    ch = jload(p)
    ok = {ch["current"], ch["chosen"]}
    if os.path.exists(ctx.path("verdict.json")):
        ok |= set(ch["specs"])
    return ok


def test_gate(ctx):
    def gate(label):
        if label not in allowed_test_labels(ctx):
            raise PeekError("refused: %s is not the chosen or the current setting, and the verdict is not written" % label)
    return gate


def run_study(ctx):
    check_current()
    grid, current = study_grid(ctx)
    labels = [k for k, _s in grid]
    # ---- 1. CHOICE (data loaded only up to choice_last)
    if not os.path.exists(ctx.path("choice.json")):
        if ctx.study == "H101":
            chosen, choice_tab = "stacked", None
            if not grid[1][1]["cfg"] and not grid[1][1]["mask"]:
                chosen = "current"
        else:
            run_phase(ctx, grid, "choice", labels, ctx.choice_last, verify_current=True)
            runs = load_runs(ctx, grid, "choice", labels)
            pooled = dict((k, sum(sum_r(runs[k][a]) for a in ctx.markets)) for k in labels)
            vault = dict((k, sum(sum_r(runs[k][a]) for a in ctx.markets if a in VAULT)) for k in labels)
            chosen = choose(labels, current, pooled, vault)
            choice_tab = dict((k, {"pooled_sum_r": pooled[k], "vault_sum_r": vault[k],
                                   "trades": sum(len(runs[k][a]["trades"]) for a in ctx.markets)}) for k in labels)
        jdump(ctx.path("choice.json"), {"study": ctx.study, "current": current, "chosen": chosen,
                                        "specs": dict(grid), "choice_period": [None, ctx.choice_last],
                                        "choice_table": choice_tab, "sources": getattr(ctx, "sources", None),
                                        "written_utc": utcnow(), "smoke": ctx.smoke})
    ch = jload(ctx.path("choice.json"))
    chosen = ch["chosen"]
    months = month_keys(ctx.test_first[:10], ctx.test_last[:10])
    if chosen == current:
        res = {"study": ctx.study, "title": STUDIES[ctx.study]["title"], "conclusion": "the current setting was already the choice",
               "choice": ch, "smoke": ctx.smoke}
        return finish(ctx, res)
    # ---- 2. TEST: the current and the chosen setting only
    gate = test_gate(ctx)
    gate(chosen), gate(current)
    run_phase(ctx, grid, "test", [current, chosen], ctx.test_last, lo_from=ctx.test_first, with_equity=True, gate=gate)
    if not os.path.exists(ctx.path("verdict.json")):
        runs = load_runs(ctx, grid, "test", [current, chosen])
        v = verdict_stats(runs[current], runs[chosen], months, ctx.markets)
        v.update(study=ctx.study, chosen=chosen, current=current, written_utc=utcnow())
        jdump(ctx.path("verdict.json"), v)
    v = jload(ctx.path("verdict.json"))
    # ---- 3. DESCRIPTIVE, computed last: every grid value on the test period
    others = [k for k in labels if k not in (current, chosen)]
    run_phase(ctx, grid, "test", others, ctx.test_last, lo_from=ctx.test_first, with_equity=False, gate=gate)
    allr = load_runs(ctx, grid, "test", labels)
    desc = dict((k, {"pooled_sum_r": sum(sum_r(allr[k][a]) for a in ctx.markets),
                     "vault_sum_r": sum(sum_r(allr[k][a]) for a in ctx.markets if a in VAULT),
                     "trades": sum(len(allr[k][a]["trades"]) for a in ctx.markets)}) for k in labels)
    res = {"study": ctx.study, "title": STUDIES[ctx.study]["title"], "conclusion": v["conclusion"], "choice": ch,
           "verdict": v, "descriptive_test_table": {"note": "descriptive, not used for any choice", "rows": desc},
           "smoke": ctx.smoke}
    return finish(ctx, res)


def finish(ctx, res):
    res["finished_utc"] = utcnow()
    res["periods"] = {"choice_last": ctx.choice_last, "test_first": ctx.test_first, "test_last": ctx.test_last,
                      "holdout_wall": DATA_END}
    jdump(ctx.path("results.json"), res)
    with open(ctx.path("report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report(res))
    d, tot = count_runs(ctx, study_grid(ctx)[0], res["choice"]["current"], res["choice"]["chosen"])
    write_progress(ctx, tot, tot, "done")
    open(ctx.path("DONE"), "w").close()
    return res


def report(res):
    ch = res["choice"]
    L = ["# %s: %s%s" % (res["study"], res["title"], " (SMOKE RUN ON A TINY SLICE: NOT A RESULT)" if res["smoke"] else ""), "",
         "**Conclusion: %s.**" % res["conclusion"], ""]
    if "verdict" in res:
        v = res["verdict"]
        b = v["boot"]
        L += ["Chosen on the choice period: `%s` (the current setting is `%s`). On the test period %s to %s, paired by calendar"
              % (ch["chosen"], ch["current"], res["periods"]["test_first"][:10], res["periods"]["test_last"][:10]),
              "month over the eight markets, the chosen setting made %+.2f R a month more than the current one on average"
              % b["mean"],
              "(95%% month-clustered interval %+.2f to %+.2f, %d months, %d draws), one-sided p = %.4f against the pass level %.5f;"
              % (b["lo"], b["hi"], b["months"], b["draws"], b["p_one_sided"], v["alpha"]),
              "BTC and ETH together: %+.1f R over the test period (the rule needs this not negative)." % v["vault_diff"], "",
              "| | current | chosen |", "|---|---|---|",
              "| trades | %d | %d |" % (v["trades"]["current"], v["trades"]["chosen"]),
              "| mean R per trade [95%%] | %s | %s |" % tuple(
                  "%+.3f [%+.3f, %+.3f]" % (m["mean_r"], m["lo"], m["hi"]) if m["mean_r"] is not None else "-"
                  for m in (v["mean_r"]["current"], v["mean_r"]["chosen"])),
              "| worst fall, eight books summed | %.1f%% | %.1f%% |" % (v["worst_fall"]["current"], v["worst_fall"]["chosen"]),
              "| share of bars flat (markets' mean) | %.1f%% | %.1f%% |" % (v["flat_pct"]["current"], v["flat_pct"]["chosen"]),
              "| paper net, eight books ($) | %+.0f | %+.0f |" % (v["net"]["current"], v["net"]["chosen"]), "",
              "## Per market, test period (sum of R)", "", "| market | current | chosen | difference |", "|---|---|---|---|"]
        for a, p in v["per_market"].items():
            L.append("| %s | %+.1f (%d) | %+.1f (%d) | %+.1f |" % (a, p["current_sum_r"], p["current_trades"],
                                                                 p["chosen_sum_r"], p["chosen_trades"], p["diff"]))
    if ch.get("choice_table"):
        L += ["", "## The choice period (the only numbers the choice used)", "", "| value | pooled sum R | BTC+ETH sum R | trades |",
              "|---|---|---|---|"]
        for k, r in ch["choice_table"].items():
            L.append("| %s%s | %+.1f | %+.1f | %d |" % (k, " (current)" if k == ch["current"] else " (chosen)" if k == ch["chosen"]
                                                       else "", r["pooled_sum_r"], r["vault_sum_r"], r["trades"]))
    if "descriptive_test_table" in res:
        L += ["", "## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)", "",
              "| value | pooled sum R | BTC+ETH sum R | trades |", "|---|---|---|---|"]
        for k, r in res["descriptive_test_table"]["rows"].items():
            L.append("| %s | %+.1f | %+.1f | %d |" % (k, r["pooled_sum_r"], r["vault_sum_r"], r["trades"]))
    if ch.get("sources"):
        L += ["", "Stacked from: " + ", ".join("%s `%s`" % (k, s["chosen"]) for k, s in ch["sources"].items())]
    L += ["", "A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,",
          "the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------------- estimate / main
def estimate_hours(study, remaining=None):
    st = STUDIES[study]
    g = len(st["grid"]) if st["grid"] else 2
    weekend = study == "H98"
    per_choice = (g - 1) * (2 if weekend else 8) + 8 + 8          # + the current, + its check against run_challenger
    per_test = (g - 1) * (2 if weekend else 8) + 8
    if study == "H101":
        per_choice = 0
    runs = per_choice + per_test
    secs = per_choice * RUN_S["choice"] + per_test * RUN_S["test"]
    secs += (sum(PREP_S["choice"].values()) if per_choice else 0) + sum(PREP_S["test"].values())
    if remaining is not None:
        return secs / 3600.0 * remaining / max(runs, 1)
    return secs / 3600.0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, choices=sorted(STUDIES))
    ap.add_argument("--fits-dir")
    ap.add_argument("--out")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.estimate:
        print("%.3f" % estimate_hours(a.study))
        return 0
    if not a.out or not a.fits_dir:
        ap.error("--out and --fits-dir are required")
    out = os.path.join(a.out, "smoke") if a.smoke else a.out
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "DONE")):
        print("already DONE: %s" % out)
        return 0
    try:
        run_study(Ctx(a.study, out, a.fits_dir, smoke=a.smoke))
    except NotReady as e:
        print("NOT READY: %s" % e, file=sys.stderr)
        return 75
    return 0


if __name__ == "__main__":
    sys.exit(main())
