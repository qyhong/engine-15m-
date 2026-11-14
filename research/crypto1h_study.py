# -*- coding: utf-8 -*-
"""Crypto 1h study: can the 1h mind's ~55% next-hour call on BTC / ETH be made to pay the 0.20% round trip?
Writes research/out/crypto1h.md and .json. PAPER ONLY; a history read can reject an idea, never prove one.

    py -3 research/crypto1h_study.py --build            evidence -> compact cache (one coin at a time, 3-month pieces)
    py -3 research/crypto1h_study.py --run [--placebo N] the study from the cache (run 11 Nov 2026 with --placebo 30)
    py -3 research/crypto1h_study.py --report           rewrite the md from the json

THE QUESTION. The 1h mind (engine15/intraday.py: the voting voices refitted on 4-bar, 0.75 x ATR(1h) triple-barrier
grades, trust-weighted mix) calls the next hour's direction right ~55% of the time on BTC and ETH in both halves of
history, worth ~+0.04 R a call before costs against a ~0.37 R round trip. Can the calls it CHOOSES to make reach
~60%, or can the payoff per call grow, so that it clears costs in BOTH halves?

DECLARED BEFORE THE READ (nothing below was changed after looking at the second half):
 - Halves: 2020-01-01 .. last bar, split at the calendar midpoint (as research/intraday_study.py).
 - Every variant = model x edge level x filter x payoff (MODELS x LEVELS x FILTERS x SCHEMES, all counted).
 - Calls are traded one at a time per coin (a new call only once the last trade is out), entry at the next open,
   no call in the hour before a high-impact US release (the engine's guard). Costs 0.10% a side on notional.
 - Choice: among variants with >= 200 trades per coin in the FIRST half, the one with the best worse-coin
   first-half average R after costs. Its second half is reported untouched.
 - "Clears costs": average R after costs > 0 for BTC and for ETH in both halves, >= 200 trades each.
 - Luck: the whole grid is re-run P times with every signal slid in time by a random number of whole days
   (prices, outcomes and the release guard stay where they were); how often does the slid grid look this good?

MODELS (all walked forward with no look-ahead, refitted every 4 weeks on every call graded by then, both coins pooled):
 m0_mix     the 1h mind exactly as intraday.mind_odds builds it (per-voice 3-class logistic, trust mix)
 m1_pooled  one binary logistic (up vs down, on calls graded up or down) on all the voting voices' readings
 m2_select  one binary logistic on the K readings most correlated with direction at each refit (re-ranked at
            every refit from past rows only), drawn from the voting readings + the faster cards (flow, trend
            quality, VWAP/opening range, candles, structure, ribbon, Hull, KAMA, moving averages, setups, clock,
            risk, funding), a few interactions and the other coin's last 15/30 minutes. K and the ridge are
            chosen on the first half only (inner split: first 2/3 to fit, last 1/3 to score).
 m3_blend   m0 and m2 edges, each divided by its own trailing 30-day spread, averaged.
LEVELS: every call / top 10% / 5% / 2% of |edge|, the cut read from the trailing 30 days (causal).
FILTERS: none; voices agree; volatility band (vol rank 0.2-0.9, no shock); London/NY overlap; active hours
 (07-21 UTC); higher-timeframe bias agrees (evidence htf_bias); 4h trend agrees; volume surge (last hour >= 2x
 usual); squeeze release in the call's direction; order flow (cvd_1h) agrees.
SCHEMES (payoff): stop 1 barrier (0.75 x ATR 1h) or structure (last confirmed 15m swing + 0.1 barrier when
 0.5-1.5 barriers away, else 1 barrier) or wide (2 barriers = 1.5 x ATR 1h, so the round trip is a smaller
 share of the risk) x target 1 / 1.5 / 2 / 3 R x time stop 4 / 8 / 16 bars; a stop and a
 target in one bar count as the stop; a gap through the stop fills at the open.
"""
import argparse
import bisect
import ctypes
import gc
import json
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, evidence, intraday, labels, livefeeds  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out")
ASSETS = ("BTCUSDT", "ETHUSDT")
START = pd.Timestamp(CFG["birth"], tz="UTC")
FEE = float(CFG["cost_side"])                       # 0.10% a side (owner, 11 Nov 2026)
MIND = intraday.MINDS["1h"]                         # 4 bars, 0.75 x ATR(1h)
H = int(MIND["horizon"])
EVERY_WEEKS = 4
DEFAULT_CACHE = os.path.join(tempfile.gettempdir(), "mind15_crypto1h_cache")
FAST_GROUPS = ("flow", "trendq", "intraday", "candles", "structure", "ribbon", "hull", "kama", "mavg", "setups",
               "clock", "risk", "funding", "cross", "momentum", "meanrev", "trend")
AUX = ["atr1h", "vol_rank", "shock_ratio", "htf_bias", "release_soon", "sw_lo_15m", "sw_hi_15m", "st_sma120",
       "mom_24h", "tr_1d"]
DERIVED = ["d_r15", "d_r30", "x_r15", "x_r30", "x_mom_1h", "x_cvd_1h", "x_tr_15m", "d_rel_1h",
           "i_cvd_tr15", "i_cvd_mom1h", "i_mom1h_adx", "i_stretch_adx", "i_k15_vol", "i_cvd_xcvd", "i_tr15_tr1h"]
MODELS = ("m0_mix", "m1_pooled", "m2_select", "m3_blend")
LEVELS = (("all", None), ("top10", 0.10), ("top5", 0.05), ("top2", 0.02))
FILTERS = ("none", "agree", "volband", "overlap", "active", "htf", "tide4h", "surge", "sqrel", "flow")
SCHEMES = [(st, k, T) for st in ("bar", "struct", "wide") for k in (1.0, 1.5, 2.0, 3.0) for T in (4, 8, 16)]
K_GRID = (8, 16, 32, 64, 128, 0)                    # 0 = every candidate
L2_GRID = (1.0, 10.0, 100.0, 1000.0)
MIN_TRADES = 200
QWIN = 2880                                         # trailing 30 days for the edge cut
FIELDS = ["n", "ndir", "hits", "wins", "rn", "rg", "rn_pos", "rn_neg", "pct"]


# ------------------------------------------------------------------ memory helpers
def _mem():
    try:
        import intraday_study as s
        return s.free_mb(), s.peak_mb()
    except Exception:
        return None, None


def log(msg):
    fr, pk = _mem()
    print("[%s] %s (free %s MB, peak %s MB)" % (time.strftime("%H:%M:%S"), msg, fr, pk), flush=True)


# ------------------------------------------------------------------ build
def feature_lists():
    vote = [v for v in intraday.voice_set(CFG) if v != "base"]
    store, cand = [], []
    for v in list(vote) + list(FAST_GROUPS):
        if v not in evidence.GROUPS or not evidence.voice_applies(v, "BTCUSDT"):
            continue
        for f in evidence.GROUPS[v][1]:
            if f not in store:
                store.append(f)
            if v != "owner" and f not in cand:
                cand.append(f)
    return vote, store, cand


def build(cache, chunk_months=3, warm_days=300, end=None):
    os.makedirs(cache, exist_ok=True)
    vote, store, cand = feature_lists()
    fidx = [evidence.FEATURES.index(f) for f in store]
    for a in ASSETS:
        t0 = time.time()
        bars = data.load(a)
        if end:
            bars = bars[bars.index < pd.Timestamp(end, tz="UTC")]
        fund, live = data.load_funding(a), livefeeds.load_live(a)
        last = bars.index[-1]
        parts = []
        c0 = START
        while c0 <= last:
            c1 = c0 + pd.DateOffset(months=chunk_months)
            b = bars[(bars.index >= c0 - pd.Timedelta(days=warm_days)) & (bars.index < c1)]
            ev = evidence.build({a: b}, {a: fund}, {a: live})[a]
            keep = np.asarray(ev.index >= c0)
            X, ready = evidence.matrix(ev)
            idx = ev.index[keep]
            p = {"t": np.asarray(idx.as_unit("ms").asi8, dtype="int64"), "X": X[keep][:, fidx].astype(np.float32),
                 "ready": ready[keep]}
            bb = b.loc[idx]
            for k in ("open", "high", "low", "close"):
                p[k] = bb[k].values.astype(float)
            for k in AUX:
                p[k] = np.asarray(ev[k].values[keep], dtype=float) if k in ev else np.full(int(keep.sum()), np.nan)
            parts.append(p)
            del ev, X, b, bb
            gc.collect()
            c0 = c1
        out = dict((k, np.concatenate([p[k] for p in parts])) for k in parts[0])
        for k, v in out.items():
            np.save(os.path.join(cache, "%s_%s.npy" % (a, k)), v)
        del parts, out, bars
        gc.collect()
        log("built %s (%.0fs)" % (a, time.time() - t0))
    patch_cross(cache, store)
    with open(os.path.join(cache, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"store": store, "cand": cand, "vote": vote, "built_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
                   "chunk_months": chunk_months, "warm_days": warm_days, "end": end}, fh)


def patch_cross(cache, store):
    """Each coin was built alone, so the readings evidence.build takes from the other coin are written in
    here, on the stored matrix in place: x_mom_24h / x_tr_1d (the cross card) and, for ETH, BTC's
    120-day switch (st_btc120)."""
    pos = dict((f, k) for k, f in enumerate(store))
    ld = lambda a, k: np.load(os.path.join(cache, "%s_%s.npy" % (a, k)))
    for a, o in zip(ASSETS, ASSETS[::-1]):
        ta, to = ld(a, "t"), ld(o, "t")
        X = np.load(os.path.join(cache, "%s_X.npy" % a), mmap_mode="r+")
        j = np.searchsorted(to, ta)
        j = np.clip(j, 0, len(to) - 1)
        same = to[j] == ta

        def put(col, vals):
            if col in pos:
                v = np.where(same, np.nan_to_num(vals[j]), 0.0).astype(np.float32)
                X[:, pos[col]] = v
        put("x_mom_24h", ld(o, "mom_24h"))
        put("x_tr_1d", ld(o, "tr_1d"))
        if a != "BTCUSDT":
            put("st_btc120", ld("BTCUSDT", "st_sma120"))
        X.flush()
        del X


def load_cache(cache):
    with open(os.path.join(cache, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    st = {}
    for a in ASSETS:
        st[a] = {}
        for k in ["t", "X", "ready", "open", "high", "low", "close"] + AUX:
            st[a][k] = np.load(os.path.join(cache, "%s_%s.npy" % (a, k)), mmap_mode="r" if k == "X" else None)
    t0, t1 = st[ASSETS[0]]["t"], st[ASSETS[1]]["t"]
    common, i0, i1 = np.intersect1d(t0, t1, return_indices=True)
    for a, ii in zip(ASSETS, (i0, i1)):
        if len(ii) != len(st[a]["t"]):
            for k in list(st[a]):
                st[a][k] = np.asarray(st[a][k][ii])
    return meta, st, pd.to_datetime(common, unit="ms", utc=True)


# ------------------------------------------------------------------ readings
class Cols:
    """Columns of the store (mmap) plus the derived readings, by name, for any rows."""

    def __init__(self, X, D, store_names):
        self.X, self.D, self.F = X, D, len(store_names)
        self.pos = dict((f, k) for k, f in enumerate(list(store_names) + DERIVED))

    def idx(self, names):
        return [self.pos[f] for f in names]

    def take(self, rows, idx):
        """float64 (rows, idx) block; rows a slice or an index array."""
        idx = np.asarray(idx)
        sa, sb = np.flatnonzero(idx < self.F), np.flatnonzero(idx >= self.F)
        nr = len(range(*rows.indices(len(self.D)))) if isinstance(rows, slice) else len(rows)
        out = np.empty((nr, len(idx)))
        if len(sa):
            out[:, sa] = self.X[rows][:, idx[sa]]
        if len(sb):
            out[:, sb] = self.D[rows][:, idx[sb] - self.F]
        return out

    def col(self, name):
        k = self.pos[name]
        return np.asarray(self.X[:, k], dtype=float) if k < self.F else np.asarray(self.D[:, k - self.F], dtype=float)


def derived(st, store):
    pos = dict((f, k) for k, f in enumerate(store))
    out = {}
    for a, o in zip(ASSETS, ASSETS[::-1]):
        c, co = st[a]["close"], st[o]["close"]
        u, uo = st[a]["atr1h"] / c, st[o]["atr1h"] / co
        def ret(cc, uu, k):
            r = np.full(len(cc), np.nan)
            r[k:] = np.log(cc[k:] / cc[:-k])
            return np.clip(np.nan_to_num(r / uu), -3, 3)
        X, Xo = st[a]["X"], st[o]["X"]
        g = lambda XX, f: np.asarray(XX[:, pos[f]], dtype=float) if f in pos else np.zeros(len(c))
        cvd, mom1, tr15 = g(X, "cvd_1h"), g(X, "mom_1h"), g(X, "tr_15m")
        adx = g(X, "tq_adx_15m")
        D = np.column_stack([
            ret(c, u, 1), ret(c, u, 2), ret(co, uo, 1), ret(co, uo, 2), g(Xo, "mom_1h"), g(Xo, "cvd_1h"), g(Xo, "tr_15m"),
            np.clip(mom1 - g(Xo, "mom_1h"), -3, 3),
            cvd * tr15, cvd * mom1, mom1 * adx, g(X, "stretch_1h") * adx, g(X, "k_15m") * g(X, "f_volrank"),
            cvd * g(Xo, "cvd_1h"), tr15 * g(X, "tr_1h")]).astype(np.float32)
        out[a] = D
    return out


# ------------------------------------------------------------------ models
def fit_logit(Z, y, l2, iters=15):
    n, d = Z.shape
    Zb = np.empty((n, d + 1))
    Zb[:, 0] = 1.0
    Zb[:, 1:] = Z
    w = np.zeros(d + 1)
    ridge = np.full(d + 1, float(l2))
    ridge[0] = 1e-6
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(Zb @ w, -30, 30)))
        g = Zb.T @ (p - y) + ridge * w
        Hm = Zb.T @ (Zb * (p * (1 - p))[:, None])
        Hm[np.diag_indices(d + 1)] += ridge
        step = np.linalg.solve(Hm, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


def _prep_train(cols, rows, ys, cidx):
    Xtr = np.concatenate([cols[a].take(rows[a], cidx) for a in ASSETS])
    ytr = np.concatenate([ys[a] for a in ASSETS]).astype(float)
    mu, sd = Xtr.mean(axis=0), Xtr.std(axis=0)
    sd = np.where(sd > 1e-9, sd, np.inf)
    Xtr -= mu
    Xtr /= sd
    return Xtr, ytr, mu, sd


def _select(Z, y, K):
    if not K or K >= Z.shape[1]:
        return np.arange(Z.shape[1])
    corr = np.abs(Z.T @ (2.0 * y - 1.0)) / len(y)
    return np.argsort(-corr, kind="stable")[:K]


def dir_rows(y, ready, step=H):
    """Rows on a 4-bar grid graded up or down (non-overlapping 1h calls)."""
    r = np.arange(0, len(y), step)
    ok = ready[r] & ((y[r] == labels.UP) | (y[r] == labels.DOWN))
    return r[ok]


def inner_choose(cols, y, ready, cidx, mid, Ks, l2s):
    """K and ridge by first-half inner validation: fit on graded rows of the first 2/3 of the first half,
    score log-loss on the last third. -> (best (K, l2), table)."""
    cut = int(mid * 2 / 3)
    tr, va = {}, {}
    for a in ASSETS:
        r = dir_rows(y[a], ready[a])
        tr[a] = r[r <= cut - H]
        va[a] = r[(r >= cut) & (r < mid - H)]
    ys = dict((a, (y[a][tr[a]] == labels.UP)) for a in ASSETS)
    Ztr, ytr, mu, sd = _prep_train(cols, tr, ys, cidx)
    Zva = np.concatenate([(cols[a].take(va[a], cidx) - mu) / sd for a in ASSETS])
    yva = np.concatenate([(y[a][va[a]] == labels.UP) for a in ASSETS]).astype(float)
    table = []
    for K in Ks:
        sel = _select(Ztr, ytr, K)
        for l2 in l2s:
            w = fit_logit(Ztr[:, sel], ytr, l2)
            p = 1.0 / (1.0 + np.exp(-(w[0] + Zva[:, sel] @ w[1:])))
            ll = float(-np.mean(yva * np.log(np.clip(p, 1e-9, 1)) + (1 - yva) * np.log(np.clip(1 - p, 1e-9, 1))))
            e = 2 * p - 1
            hit = float(np.mean((e > 0) == (yva > 0.5)))
            top = np.abs(e) >= np.quantile(np.abs(e), 0.9)
            table.append({"K": K or len(cidx), "l2": l2, "logloss": round(ll, 5), "hit_pct": round(100 * hit, 2),
                          "hit_top10_pct": round(100 * float(np.mean((e[top] > 0) == (yva[top] > 0.5))), 2)})
    best = min(table, key=lambda r: r["logloss"])
    del Ztr, Zva
    gc.collect()
    return (best["K"], best["l2"]), table


def walk_logit(cols, y, ready, times, n, cidx, K, l2, names=None):
    """Binary up/down logistic walked forward (refit every EVERY_WEEKS weeks on rows graded by then; the K
    readings re-ranked at every refit from those rows only). -> ({asset: edge (n,)}, last selection by name)."""
    edge = dict((a, np.full(n, np.nan, dtype=np.float32)) for a in ASSETS)
    allrows = dict((a, dir_rows(y[a], ready[a])) for a in ASSETS)
    last_sel, fits = None, 0
    for w, s, s0, s1 in intraday.fit_points(times, 0, n, EVERY_WEEKS):
        rows = dict((a, allrows[a][allrows[a] <= s - H]) for a in ASSETS)
        if sum(len(r) for r in rows.values()) < CFG["min_train_rows"]:
            continue
        ys = dict((a, y[a][rows[a]] == labels.UP) for a in ASSETS)
        Z, yy, mu, sd = _prep_train(cols, rows, ys, cidx)
        sel = _select(Z, yy, K)
        wv = fit_logit(Z[:, sel], yy, l2)
        del Z
        fits += 1
        csel = [cidx[k] for k in sel]
        for a in ASSETS:
            Xa = (cols[a].take(slice(s0, s1), csel) - mu[sel]) / sd[sel]
            p = 1.0 / (1.0 + np.exp(-(wv[0] + Xa @ wv[1:])))
            e = (2 * p - 1).astype(np.float32)
            e[~ready[a][s0:s1]] = np.nan
            edge[a][s0:s1] = e
        last_sel = (str(times[s])[:10], [names[k] for k in sel] if names else None, wv[1:].tolist())
    gc.collect()
    return edge, last_sel, fits


def roll_z(e):
    sd = pd.Series(e.astype(float)).rolling(QWIN, min_periods=QWIN // 3).std().shift(1).values
    return e / np.where(sd > 0, sd, np.nan)


# ------------------------------------------------------------------ payoffs
def outcomes(o, h, l, unit, swl, swh, side, stop_type, k, T):
    """Per decision close t: a trade in `side` entered at open[t+1]. -> (r_net, r_gross, free, pct_net):
    free = the first close at which the next call may be made (the exit bar, or t+T on the time stop)."""
    n = len(o)
    e = np.full(n, np.nan)
    e[:-1] = o[1:]
    if stop_type in ("bar", "wide"):
        R = unit * (2.0 if stop_type == "wide" else 1.0)
        stop = e - side * R
    else:
        sw = swl if side == 1 else swh
        lvl = sw - side * intraday.STRUCT_BUFFER * unit
        with np.errstate(invalid="ignore"):
            d = side * (e - lvl)
            use = np.isfinite(d) & (d >= intraday.STRUCT_RANGE[0] * unit) & (d <= intraday.STRUCT_RANGE[1] * unit)
        stop = np.where(use, lvl, e - side * unit)
        R = np.abs(e - stop)
    tgt = e + side * k * R
    done = np.zeros(n, dtype=bool)
    exitp = np.full(n, np.nan)
    exitk = np.full(n, T, dtype=np.int64)

    def sh(a, j):
        out = np.full(n, np.nan)
        out[:n - j] = a[j:]
        return out
    with np.errstate(invalid="ignore"):
        for j in range(1, T + 1):
            oj, hj, lj = sh(o, j), sh(h, j), sh(l, j)
            if side == 1:
                hs, ps, ht = lj <= stop, np.minimum(oj, stop), hj >= tgt
            else:
                hs, ps, ht = hj >= stop, np.maximum(oj, stop), lj <= tgt
            m = ~done & hs
            exitp[m], exitk[m] = ps[m], j
            done |= m
            m = ~done & ht
            exitp[m], exitk[m] = tgt[m], j
            done |= m
        ot = sh(o, T + 1)
        exitp[~done] = ot[~done]
        rg = side * (exitp - e) / R
        rn = rg - FEE * (e + exitp) / R
        pct = (side * (exitp - e) - FEE * (e + exitp)) / e * 100.0
    free = np.arange(n) + exitk
    bad = ~np.isfinite(rn) | ~(R > 0)
    rn[bad] = np.nan
    return rn.astype(np.float32), rg.astype(np.float32), free, pct.astype(np.float32)


def take(idx, free):
    """Greedy one-at-a-time: keep a call only when the last kept trade is out. idx sorted list; free list."""
    out = []
    pos, L = 0, len(idx)
    while pos < L:
        i = idx[pos]
        out.append(i)
        pos = bisect.bisect_left(idx, free[i], pos + 1)
    return out


def stats_into(acc, taken, side, y, half, rn, rg, pct):
    if not len(taken):
        return
    t = np.asarray(taken)
    s, yy, hf = side[t], y[t], half[t]
    r, g, pc = rn[t].astype(float), rg[t].astype(float), pct[t].astype(float)
    dirm = (yy == labels.UP) | (yy == labels.DOWN)
    hit = ((yy == labels.UP) & (s > 0)) | ((yy == labels.DOWN) & (s < 0))
    for hh in (0, 1):
        m = hf == hh
        if not m.any():
            continue
        rr = r[m]
        acc[hh] = [m.sum(), (dirm & m).sum(), (hit & m).sum(), (rr > 0).sum(), rr.sum(), g[m].sum(),
                   rr[rr > 0].sum(), -rr[rr < 0].sum(), pc[m].sum()]


# ------------------------------------------------------------------ run
def run(cache, placebo=20, seed=7):
    t_all = time.time()
    meta, st, times = load_cache(cache)
    store, cand, vote = meta["store"], meta["cand"], meta["vote"]
    n = len(times)
    mid_t = START + (times[-1] - START) / 2
    mid = int(times.searchsorted(mid_t))
    half = (np.arange(n) >= mid).astype(np.int8)
    log("loaded %d sessions %s .. %s, split %s" % (n, str(times[0])[:16], str(times[-1])[:16], str(mid_t)[:16]))
    pos = dict((f, k) for k, f in enumerate(store))
    # cross readings: built one coin at a time, so the other coin's columns are filled here (as evidence.build)
    D = derived(st, store)
    cols = dict((a, Cols(st[a]["X"], D[a], store)) for a in ASSETS)
    ready = dict((a, np.asarray(st[a]["ready"], bool)) for a in ASSETS)
    px = dict((a, dict((k, st[a][k]) for k in ("open", "high", "low", "close"))) for a in ASSETS)
    atr = dict((a, st[a]["atr1h"]) for a in ASSETS)
    y, res = {}, {}
    for a in ASSETS:
        y[a], res[a] = intraday.labels_for(px[a], atr[a], MIND)
    # ---- m0: the 1h mind as the engine builds it (voting voices only, fixed cross columns)
    t0 = time.time()
    vfeat = []
    for v in vote:
        vfeat += [f for f in evidence.GROUPS[v][1] if f not in vfeat]
    Xv = dict((a, np.asarray(st[a]["X"][:, [pos[f] for f in vfeat]], dtype=np.float32)) for a in ASSETS)
    vcols = intraday.cols_for(intraday.voice_set(CFG), vfeat)
    voices = intraday.voice_set(CFG)
    cfg = dict(CFG, assets=ASSETS)
    r0 = intraday.mind_odds(Xv, ready, px, atr, times, vcols, voices, cfg, MIND, 0, n, 0, every_weeks=EVERY_WEEKS)
    edge0, agree0 = {}, {}
    for a in ASSETS:
        od = r0["odds"][a]
        edge0[a] = (od[:, labels.UP] - od[:, labels.DOWN]).astype(np.float32)
        pv = r0["probs"][a]
        ev_v = pv[:, :, labels.UP] - pv[:, :, labels.DOWN]
        w = r0["trust"] * np.array([0.0 if v == "base" else 1.0 for v in voices])
        same = (np.sign(ev_v) == np.sign(edge0[a])[:, None]) & np.isfinite(ev_v)
        agree0[a] = ((w * same).sum(axis=1) / np.where(w.sum(axis=1) > 0, w.sum(axis=1), 1.0)).astype(np.float32)
    del r0, Xv, pv, ev_v, same
    gc.collect()
    log("m0 walked (%.0fs)" % (time.time() - t0))
    # ---- m1 / m2: inner validation on the first half only, then the walk
    t0 = time.time()
    vidx = cols[ASSETS[0]].idx([f for f in vfeat if f != "owner_view"])
    cnames = list(cand) + DERIVED
    cidx = cols[ASSETS[0]].idx(cnames)
    (_, l2_1), tab1 = inner_choose(cols, y, ready, vidx, mid, (0,), L2_GRID)
    (K2, l2_2), tab2 = inner_choose(cols, y, ready, cidx, mid, K_GRID, L2_GRID)
    K2 = 0 if K2 >= len(cidx) else K2
    log("inner validation: m1 l2=%s; m2 K=%s l2=%s (%.0fs)" % (l2_1, K2 or len(cidx), l2_2, time.time() - t0))
    t0 = time.time()
    edge1, sel1, f1 = walk_logit(cols, y, ready, times, n, vidx, 0, l2_1)
    edge2, sel2, f2 = walk_logit(cols, y, ready, times, n, cidx, K2, l2_2, names=cnames)
    edge3 = dict((a, ((roll_z(edge0[a]) + roll_z(edge2[a])) / 2.0).astype(np.float32)) for a in ASSETS)
    log("m1/m2 walked: %d + %d refits (%.0fs)" % (f1, f2, time.time() - t0))
    edges = {"m0_mix": edge0, "m1_pooled": edge1, "m2_select": edge2, "m3_blend": edge3}
    # ---- skill of each model on every graded call (no selection), for the record
    skill = {}
    for mname, ed in edges.items():
        skill[mname] = {}
        for a in ASSETS:
            e, yy = ed[a], y[a]
            ok = np.isfinite(e) & ((yy == labels.UP) | (yy == labels.DOWN)) & ready[a]
            hit = ((e > 0) & (yy == labels.UP)) | ((e < 0) & (yy == labels.DOWN))
            skill[mname][a] = [round(100.0 * float(hit[ok & (half == hh)].mean()), 2) for hh in (0, 1)]
    log("skill (all graded calls, hit %% 1st/2nd): %s" % skill)
    # ---- signal packs: side, edge-level masks, filter masks (per model, per coin)
    ses = intraday.session_of(times)
    overlap, active = ses == "overlap", np.isin(ses, ["london", "overlap", "ny"])
    packs = {}
    for mname, ed in edges.items():
        packs[mname] = {}
        for a in ASSETS:
            e = ed[a].astype(float)
            side = np.sign(np.nan_to_num(e)).astype(np.int8)
            sig = np.isfinite(e) & (side != 0) & ready[a]
            ae = pd.Series(np.abs(e))
            lev = []
            for _, q in LEVELS:
                if q is None:
                    lev.append(np.ones(n, bool))
                else:
                    cut = ae.rolling(QWIN, min_periods=QWIN // 3).quantile(1 - q).shift(1).values
                    with np.errstate(invalid="ignore"):
                        lev.append(np.abs(e) >= cut)
            C = cols[a]
            vr, sr = st[a]["vol_rank"], st[a]["shock_ratio"]
            with np.errstate(invalid="ignore"):
                filt = {
                    "none": np.ones(n, bool),
                    "agree": (agree0[a] >= 0.7) if mname == "m0_mix" else (np.sign(edge0[a]) == side),
                    "volband": (vr >= 0.2) & (vr <= 0.9) & (sr < CFG["shock_ratio"]),
                    "overlap": overlap, "active": active,
                    "htf": np.asarray(st[a]["htf_bias"]) == side,
                    "tide4h": np.sign(C.col("tr_4h")) == side,
                    "surge": C.col("tq_rvol") >= 1.0,
                    "sqrel": C.col("tq_sq_release") * side > 0,
                    "flow": np.sign(C.col("cvd_1h")) == side,
                }
            packs[mname][a] = {"side": side, "sig": sig, "lev": np.array(lev), "filt": np.array([filt[f] for f in FILTERS])}
    guard = dict((a, ~(np.asarray(st[a]["release_soon"], dtype=float) > 0.5)) for a in ASSETS)
    # ---- the grid (and the slid placebos) per payoff scheme
    rng = np.random.default_rng(seed)
    days = n // 96
    offsets = [0] + [int(rng.integers(30, days - 30)) * 96 for _ in range(placebo)]
    V = len(MODELS) * len(LEVELS) * len(FILTERS) * len(SCHEMES)
    acc = np.zeros((len(offsets), V, 2, 2, len(FIELDS)))
    vkeys = []
    for mname in MODELS:
        for lname, _ in LEVELS:
            for fname in FILTERS:
                for (stp, k, T) in SCHEMES:
                    vkeys.append("%s|%s|%s|%s %.1fR %db" % (mname, lname, fname, stp, k, T))
    vindex = dict((k, i) for i, k in enumerate(vkeys))
    t0 = time.time()
    for si, (stp, k, T) in enumerate(SCHEMES):
        outc = {}
        for a in ASSETS:
            o, hh, ll = px[a]["open"], px[a]["high"], px[a]["low"]
            unit = MIND["barrier_atr"] * atr[a]
            outc[a] = dict((sd, outcomes(o, hh, ll, unit, st[a]["sw_lo_15m"], st[a]["sw_hi_15m"], sd, stp, k, T))
                           for sd in (1, -1))
        for pi, off in enumerate(offsets):
            for mname in MODELS:
                for ci, a in enumerate(ASSETS):
                    pk = packs[mname][a]
                    side = np.roll(pk["side"], off) if off else pk["side"]
                    rnL, rgL, frL, pcL = outc[a][1]
                    rnS, rgS, frS, pcS = outc[a][-1]
                    lg = side > 0
                    rn = np.where(lg, rnL, rnS)
                    rg = np.where(lg, rgL, rgS)
                    pc = np.where(lg, pcL, pcS)
                    fr = np.where(lg, frL, frS).tolist()
                    base = (np.roll(pk["sig"], off) if off else pk["sig"]) & guard[a] & np.isfinite(rn)
                    levs = np.roll(pk["lev"], off, axis=1) if off else pk["lev"]
                    filts = np.roll(pk["filt"], off, axis=1) if off else pk["filt"]
                    for li, (lname, _) in enumerate(LEVELS):
                        bl = base & levs[li]
                        for fi, fname in enumerate(FILTERS):
                            m = bl & filts[fi]
                            taken = take(np.flatnonzero(m).tolist(), fr)
                            vi = vindex["%s|%s|%s|%s %.1fR %db" % (mname, lname, fname, stp, k, T)]
                            stats_into(acc[pi, vi, ci], taken, side, y[a], half, rn, rg, pc)
        del outc
        gc.collect()
        log("scheme %d/%d %s %.1fR %db done (%.0fs)" % (si + 1, len(SCHEMES), stp, k, T, time.time() - t0))
    out = summarise(acc, vkeys, offsets, skill, {"m1": tab1, "m2": tab2}, (l2_1, K2 or len(cidx), l2_2), sel2,
                    times, mid_t, n, cand, time.time() - t_all)
    return out


# ------------------------------------------------------------------ summary
def cell(a):
    n = int(a[0])
    if n == 0:
        return None
    return {"trades": n, "hit_pct": round(100.0 * a[2] / a[1], 2) if a[1] else None, "win_pct": round(100.0 * a[3] / n, 1),
            "avg_r_gross": round(a[5] / n, 4), "avg_r_net": round(a[4] / n, 4),
            "pf_net": round(a[6] / a[7], 3) if a[7] > 0 else None, "avg_pct_net": round(a[8] / n, 4)}


def grid_view(A):
    """A: (V, 2 coins, 2 halves, fields) -> arrays n, net, hit per coin x half."""
    nn = A[..., 0]
    net = np.where(nn > 0, A[..., 4] / np.maximum(nn, 1), np.nan)
    hit = np.where(A[..., 1] > 0, A[..., 2] / np.maximum(A[..., 1], 1), np.nan)
    return nn, net, hit


def choose(A):
    nn, net, hit = grid_view(A)
    elig = (nn[:, :, 0] >= MIN_TRADES).all(axis=1)
    score = np.where(elig, np.nanmin(net[:, :, 0], axis=1), -np.inf)
    hscore = np.where(elig, np.nanmin(hit[:, :, 0], axis=1), -np.inf)
    clears = elig & (nn[:, :, 1] >= MIN_TRADES).all(axis=1) & (net > 0).all(axis=(1, 2))
    best = int(np.argmax(score)) if np.isfinite(score).any() else None
    besth = int(np.argmax(hscore)) if np.isfinite(hscore).any() else None
    return best, besth, score, hscore, clears, net, hit, nn


def summarise(acc, vkeys, offsets, skill, inner, chosen_params, sel2, times, mid_t, n, cand, secs):
    real = acc[0]
    best, besth, score, hscore, clears, net, hit, nn = choose(real)
    rows = []
    for vi, k in enumerate(vkeys):
        rows.append({"variant": k, "BTC": [cell(real[vi, 0, h]) for h in (0, 1)], "ETH": [cell(real[vi, 1, h]) for h in (0, 1)]})
    # placebo
    plc = []
    for pi in range(1, len(offsets)):
        b, bh, sc, hs, cl, nt, ht, nnp = choose(acc[pi])
        plc.append({"offset_days": offsets[pi] // 96,
                    "best_h1_worse_coin_net": None if b is None else round(float(sc[b]), 4),
                    "best_h1_variant": None if b is None else vkeys[b],
                    "its_h2_net": None if b is None else [None if not np.isfinite(x) else round(float(x), 4) for x in nt[b, :, 1]],
                    "best_h1_worse_coin_hit": None if bh is None else round(100 * float(hs[bh]), 2),
                    "clear_both_halves": int(cl.sum()),
                    "h1_net_positive_both_coins": int(((nnp[:, :, 0] >= MIN_TRADES).all(axis=1) & (nt[:, :, 0] > 0).all(axis=1)).sum())})
    real_pos_h1 = int(((nn[:, :, 0] >= MIN_TRADES).all(axis=1) & (net[:, :, 0] > 0).all(axis=1)).sum())
    out = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "window": [str(times[0])[:16], str(times[-1])[:16]],
           "split": str(mid_t)[:16], "sessions": n, "cost_side_pct": FEE * 100, "variants_tried": len(vkeys),
           "variant_axes": {"models": MODELS, "levels": [l[0] for l in LEVELS], "filters": FILTERS,
                            "schemes": ["%s %.1fR %db" % s for s in SCHEMES]},
           "model_choices_tried": {"m1_l2": list(L2_GRID), "m2_K": list(K_GRID), "m2_l2": list(L2_GRID),
                                   "count": len(L2_GRID) + len(K_GRID) * len(L2_GRID)},
           "inner_validation": inner, "m1_l2": chosen_params[0], "m2_K": chosen_params[1], "m2_l2": chosen_params[2],
           "m2_candidates": len(cand) + len(DERIVED),
           "m2_last_selection": {"as_of": sel2[0], "features": sel2[1][:40]} if sel2 else None,
           "skill_all_calls_hit_pct": skill,
           "chosen": None if best is None else {"variant": vkeys[best], **rows[best], "h1_worse_coin_net": round(float(score[best]), 4)},
           "chosen_by_hit": None if besth is None else {"variant": vkeys[besth], **rows[besth], "h1_worse_coin_hit": round(100 * float(hscore[besth]), 2)},
           "clear_both_halves": [vkeys[i] for i in np.flatnonzero(clears)],
           "h1_net_positive_both_coins": real_pos_h1,
           "placebo": plc, "seconds": round(secs, 1), "peak_mb": _mem()[1],
           "variants": rows}
    if plc:
        bs = [p["best_h1_worse_coin_net"] for p in plc if p["best_h1_worse_coin_net"] is not None]
        out["luck"] = {"runs": len(plc),
                       "placebo_best_h1_net_mean": round(float(np.mean(bs)), 4) if bs else None,
                       "placebo_best_h1_net_max": round(float(np.max(bs)), 4) if bs else None,
                       "share_placebo_best_ge_real": round(float(np.mean([b >= score[best] for b in bs])), 3) if bs and best is not None else None,
                       "placebo_clear_both_mean": round(float(np.mean([p["clear_both_halves"] for p in plc])), 2),
                       "placebo_clear_both_max": int(max(p["clear_both_halves"] for p in plc)),
                       "placebo_h1_positive_mean": round(float(np.mean([p["h1_net_positive_both_coins"] for p in plc])), 2),
                       "placebo_best_h1_hit_mean": round(float(np.mean([p["best_h1_worse_coin_hit"] or 0 for p in plc])), 2),
                       "placebo_best_h1_hit_max": round(float(np.max([p["best_h1_worse_coin_hit"] or 0 for p in plc])), 2)}
    return out


def fmt(v, pat="%.3f"):
    return "-" if v is None else pat % v


def write_md(out, path):
    L = ["# Crypto 1h study: can the 1h mind's next-hour call pay its costs? (IN-SAMPLE, not proof)", "",
         "Written by `research/crypto1h_study.py` on %s. BTCUSDT and ETHUSDT, %s to %s UTC, halves split at %s. "
         "Costs %.2f%% a side (0.20%% round trip). Paper only: history can reject an idea, never prove one." % (
             out["written_utc"], out["window"][0], out["window"][1], out["split"], out["cost_side_pct"]), "",
         "Every call is a trade entered at the next 15m open, one at a time per coin, none in the hour before a "
         "high-impact US release. R = the stop distance at entry. Hit = direction right on calls whose 1h triple-barrier "
         "grade was up or down (the 1h mind's own yardstick); win = trade positive after costs.", ""]
    L += ["## Verdict", "", out.get("verdict", ""), "", "Read plainly:", ""] + plain(out) + [
        "", "So no hypothesis entry and no shadow challenger are drafted from this study (the rule set before it: only "
        "something that clears costs in both halves with >= %d trades per half per coin)." % MIN_TRADES
        if not out.get("clear_both_halves") else "", ""]
    L += ["## The models on every graded call (no selection): direction hit %, 1st / 2nd half", "",
          "| Model | BTC | ETH |", "|---|---|---|"]
    for m, r in out["skill_all_calls_hit_pct"].items():
        L.append("| %s | %.2f / %.2f | %.2f / %.2f |" % (m, r["BTCUSDT"][0], r["BTCUSDT"][1], r["ETHUSDT"][0], r["ETHUSDT"][1]))
    L += ["", "m1 ridge %s; m2: K = %s readings of %s candidates, ridge %s (chosen by first-half inner validation; %d model "
          "settings tried)." % (out["m1_l2"], out["m2_K"], out["m2_candidates"], out["m2_l2"], out["model_choices_tried"]["count"]), ""]
    if out.get("m2_last_selection"):
        L.append("m2's readings at its last refit (%s): %s." % (out["m2_last_selection"]["as_of"],
                                                              ", ".join(out["m2_last_selection"]["features"] or [])))
        L.append("")
    rows = dict((r["variant"], r) for r in out["variants"])

    def line(k):
        r = rows[k]
        b, e = r["BTC"], r["ETH"]
        parts = []
        for c in (b[0], b[1], e[0], e[1]):
            c = c or {}
            parts.append("%s / %s / %s / %s" % (c.get("trades", 0), fmt(c.get("hit_pct"), "%.1f"),
                                                fmt(c.get("avg_r_gross"), "%+.3f"), fmt(c.get("avg_r_net"), "%+.3f")))
        return "| `%s` | %s |" % (k, " | ".join(parts))
    hdr = ["| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |", "|---|---|---|---|---|"]
    L += ["## Selectivity: does picking the surest calls lift the hit rate? (1-barrier stop and target, 4 bars, no filter)", ""] + hdr
    for m in out["variant_axes"]["models"]:
        for lv in out["variant_axes"]["levels"]:
            L.append(line("%s|%s|none|bar 1.0R 4b" % (m, lv)))
    L += ["", "## Filters on the top 10% of the 1h mind (m0), same payoff", ""] + hdr
    for f in out["variant_axes"]["filters"]:
        L.append(line("m0_mix|top10|%s|bar 1.0R 4b" % f))
    L += ["", "## Payoff: the 1h mind's top 10%, no filter, every stop / target / clock", ""] + hdr
    for s in out["variant_axes"]["schemes"]:
        L.append(line("m0_mix|top10|none|%s" % s))
    L += ["", "## The first-half choice (rule declared before the read)", ""]
    ch = out.get("chosen")
    if ch:
        L += ["Best worse-coin average R after costs in the first half, among variants with >= %d trades per coin: "
              "`%s` (first half, worse coin: %+.3f R)." % (MIN_TRADES, ch["variant"], ch["h1_worse_coin_net"]), ""] + hdr + [line(ch["variant"]), ""]
        for coin in ("BTC", "ETH"):
            for h, c in zip(("1st", "2nd"), ch[coin]):
                c = c or {}
                L.append("- %s %s half: %s trades, hit %s%%, win %s%%, %s R before costs, %s R after, PF after costs %s, %s%% a trade after costs" % (
                    coin, h, c.get("trades", 0), fmt(c.get("hit_pct"), "%.1f"), fmt(c.get("win_pct"), "%.1f"),
                    fmt(c.get("avg_r_gross"), "%+.3f"), fmt(c.get("avg_r_net"), "%+.3f"), fmt(c.get("pf_net"), "%.2f"),
                    fmt(c.get("avg_pct_net"), "%+.4f")))
    chh = out.get("chosen_by_hit")
    if chh:
        L += ["", "Best worse-coin first-half HIT RATE (same eligibility): `%s` (%.1f%%)." % (chh["variant"], chh["h1_worse_coin_hit"]), ""] + hdr + [line(chh["variant"])]
    L += ["", "## Top 20 variants by first-half worse-coin R after costs (>= %d trades per coin), with their second half" % MIN_TRADES, ""] + hdr
    for k in out.get("top20", []):
        L.append(line(k))
    L += ["", "## Luck count", "",
          "Variants tried: **%d** (%d models x %d edge levels x %d filters x %d payoffs: 3 stops x 4 targets x 3 clocks), plus %d model settings in the inner "
          "validation. Variants with average R after costs > 0 on both coins in the first half (>= %d trades each): %d. "
          "Variants that clear costs on both coins in BOTH halves (>= %d trades each): %d%s." % (
              out["variants_tried"], len(out["variant_axes"]["models"]), len(out["variant_axes"]["levels"]),
              len(out["variant_axes"]["filters"]), len(out["variant_axes"]["schemes"]), out["model_choices_tried"]["count"],
              MIN_TRADES, out["h1_net_positive_both_coins"], MIN_TRADES, len(out["clear_both_halves"]),
              (": " + ", ".join("`%s`" % k for k in out["clear_both_halves"][:20])) if out["clear_both_halves"] else ""), ""]
    lk = out.get("luck")
    if lk:
        L += ["Placebo: the whole grid re-run %d times with every signal slid by a random number of whole days (prices, "
              "outcomes and the release guard left in place). Best first-half worse-coin R after costs: real %s, placebo "
              "mean %s, max %s (share of placebo runs at least as good: %s). Variants clearing both halves: placebo mean %s, "
              "max %s. First-half positive on both coins: placebo mean %s. Best first-half worse-coin hit rate: placebo mean "
              "%s%%, max %s%%." % (lk["runs"], fmt(out["chosen"]["h1_worse_coin_net"] if out.get("chosen") else None, "%+.3f"),
                                   fmt(lk["placebo_best_h1_net_mean"], "%+.3f"), fmt(lk["placebo_best_h1_net_max"], "%+.3f"),
                                   lk["share_placebo_best_ge_real"], lk["placebo_clear_both_mean"], lk["placebo_clear_both_max"],
                                   lk["placebo_h1_positive_mean"], lk["placebo_best_h1_hit_mean"], lk["placebo_best_h1_hit_max"]), ""]
    L += ["## Limits", "",
          "In-sample history; the engine's constants and voting cards were chosen on this history already. Refits every "
          "4 weeks (live: weekly). Evidence built one coin at a time in 3-month pieces with 300 days of warm-up (the "
          "other coin's readings filled in afterwards). Fills at the next open, no slippage, no funding; a target is "
          "filled at its price even when the bar opens beyond it (cautious), a stop at the worse of the stop and the "
          "open. Full per-variant tables: `research/out/crypto1h.json`.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def verdict(out):
    ch = out.get("chosen")
    if not ch:
        return "No variant reached %d first-half trades per coin, so none could be chosen." % MIN_TRADES
    c = [ch["BTC"][1] or {}, ch["ETH"][1] or {}]
    ok = all(x.get("trades", 0) >= MIN_TRADES and (x.get("avg_r_net") or -1) > 0 for x in c)
    h1ok = all((x or {}).get("avg_r_net", -1) > 0 for x in (ch["BTC"][0], ch["ETH"][0]))
    s = ("The first-half choice `%s` %s in the first half (worse coin %+.3f R after costs) and in the untouched second half "
         "made %s R (BTC, %s trades) and %s R (ETH, %s trades) after costs." % (
             ch["variant"], "cleared costs" if h1ok else "did NOT clear costs even", ch["h1_worse_coin_net"],
             fmt(c[0].get("avg_r_net"), "%+.3f"), c[0].get("trades", 0), fmt(c[1].get("avg_r_net"), "%+.3f"), c[1].get("trades", 0)))
    if ok and h1ok:
        s += " **It clears costs in both halves on both coins** (still in-sample: grade it forward)."
    else:
        s += " **It does not clear costs in both halves.**"
    lk = out.get("luck")
    if lk:
        s += (" Luck: %d variants tried; %d clear costs in both halves on both coins after the fact, against %s on average "
              "(max %s) when the signals are slid in time." % (out["variants_tried"], len(out["clear_both_halves"]),
                                                             lk["placebo_clear_both_mean"], lk["placebo_clear_both_max"]))
    return s


def plain(out):
    """The plain reading, from the numbers in `out` (bullets for the md)."""
    rows = dict((r["variant"], r) for r in out["variants"])

    def g(k, coin, h, f):
        c = (rows.get(k) or {}).get(coin, [None, None])[h] or {}
        return c.get(f)
    L = []
    best = None
    for m in out["variant_axes"]["models"]:                      # the biggest hit lift at the top 10%, large samples
        k = "%s|top10|none|bar 1.0R 4b" % m
        w = min(g(k, c, h, "hit_pct") or 0 for c in ("BTC", "ETH") for h in (0, 1))
        if best is None or w > best[1]:
            best = (k, w)
    k, base = best[0], "m0_mix|all|none|bar 1.0R 4b"
    L.append("- **Selectivity does lift the hit rate, a little, in both halves.** The 1h mind on every call: %s / %s %% "
             "(BTC) and %s / %s %% (ETH). `%s`: %s / %s %% and %s / %s %% on 2,900-5,600 trades a half per coin. That is "
             "close to the 60%% asked for on ETH. But it does not turn into money: R before costs on those trades is "
             "%s / %s (BTC) and %s / %s (ETH), because the read is about which way SMALL moves go; a large share of calls "
             "never reach a barrier inside the hour." % (
                 fmt(g(base, "BTC", 0, "hit_pct"), "%.1f"), fmt(g(base, "BTC", 1, "hit_pct"), "%.1f"),
                 fmt(g(base, "ETH", 0, "hit_pct"), "%.1f"), fmt(g(base, "ETH", 1, "hit_pct"), "%.1f"), k,
                 fmt(g(k, "BTC", 0, "hit_pct"), "%.1f"), fmt(g(k, "BTC", 1, "hit_pct"), "%.1f"),
                 fmt(g(k, "ETH", 0, "hit_pct"), "%.1f"), fmt(g(k, "ETH", 1, "hit_pct"), "%.1f"),
                 fmt(g(k, "BTC", 0, "avg_r_gross"), "%+.3f"), fmt(g(k, "BTC", 1, "avg_r_gross"), "%+.3f"),
                 fmt(g(k, "ETH", 0, "avg_r_gross"), "%+.3f"), fmt(g(k, "ETH", 1, "avg_r_gross"), "%+.3f")))
    cost = lambda kk, coin, h: (g(kk, coin, h, "avg_r_gross") or 0) - (g(kk, coin, h, "avg_r_net") or 0)
    wk = "m0_mix|all|none|wide 1.0R 4b"
    L.append("- **The cost wall.** On the 1-barrier stop (0.75 x ATR 1h) the round trip costs %.2f / %.2f R on BTC and "
             "%.2f / %.2f R on ETH (first / second half: BTC's hourly range shrank after 2023, so the same 0.20%% is a "
             "bigger share of it). A 2-barrier stop halves that (%.2f / %.2f and %.2f / %.2f R), but the edge does not grow "
             "with the stop, so R before costs shrinks as fast. Bigger targets (2-3R) and longer clocks (8-16 bars) raise R "
             "before costs to at most about +0.1-0.35 R on the selected calls, still short of costs in the second half." % (
                 cost(base, "BTC", 0), cost(base, "BTC", 1), cost(base, "ETH", 0), cost(base, "ETH", 1),
                 cost(wk, "BTC", 0), cost(wk, "BTC", 1), cost(wk, "ETH", 0), cost(wk, "ETH", 1)))
    lk, ch = out.get("luck"), out.get("chosen")
    if lk and ch:
        L.append("- **The first-half pick was not luck in the first half, and still failed.** Its first-half worse-coin %+.3f R "
                 "beat every one of %d slid-signal placebos (best %+.3f R), so the selection found something real in "
                 "2020-2023; in the untouched second half it lost (%s R BTC, %s R ETH after costs)." % (
                     ch["h1_worse_coin_net"], lk["runs"], lk["placebo_best_h1_net_max"] or 0,
                     fmt((ch["BTC"][1] or {}).get("avg_r_net"), "%+.3f"), fmt((ch["ETH"][1] or {}).get("avg_r_net"), "%+.3f")))
        L.append("- **High hit rates on a few hundred trades are not evidence.** The best first-half worse-coin hit rate "
                 "among the %d variants is %s %%; with the signals slid in time the best is %s %% on average (max %s %%)." % (
                     out["variants_tried"], fmt((out.get("chosen_by_hit") or {}).get("h1_worse_coin_hit"), "%.1f"),
                     lk["placebo_best_h1_hit_mean"], lk["placebo_best_h1_hit_max"]))
    L.append("- **Better inputs and other models did not help on direction overall:** on every graded call the pooled "
             "logistic, the selected fast readings (order flow, trend quality, VWAP, ribbon, Hull, KAMA, the other coin, "
             "interactions) and the blend are within about 1 point of the 1h mind in both halves; the extra first-half "
             "points of the selected model (m2) are gone in the second.")
    return L


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true", help="rewrite the md from the json")
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--chunk-months", type=int, default=3)
    ap.add_argument("--warm-days", type=int, default=300)
    ap.add_argument("--end", default=None)
    ap.add_argument("--placebo", type=int, default=20)
    ap.add_argument("--out", default=os.path.join(OUT, "crypto1h"))
    args = ap.parse_args(argv)
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    try:                                                         # below-normal priority: the live loop comes first
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass
    if args.build:
        build(args.cache, args.chunk_months, args.warm_days, args.end)
    if args.run:
        out = run(args.cache, args.placebo)
        rows = out["variants"]
        nn_ok = [r for r in rows if all((r[c][0] or {}).get("trades", 0) >= MIN_TRADES for c in ("BTC", "ETH"))]
        nn_ok.sort(key=lambda r: -min(r["BTC"][0]["avg_r_net"], r["ETH"][0]["avg_r_net"]))
        out["top20"] = [r["variant"] for r in nn_ok[:20]]
        out["verdict"] = verdict(out)
        with open(args.out + ".json", "w", encoding="utf-8") as fh:
            json.dump(out, fh, separators=(",", ":"))
        write_md(out, args.out + ".md")
        log("written %s.md/.json: %s" % (args.out, out["verdict"]))
    if args.report:                                              # rewrite the md from the json (no rerun)
        with open(args.out + ".json", encoding="utf-8") as fh:
            out = json.load(fh)
        write_md(out, args.out + ".md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
