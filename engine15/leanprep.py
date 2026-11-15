# -*- coding: utf-8 -*-
"""leanprep -- the live step's think stage without holding all history in memory. PAPER ONLY.

backtest.prepare builds every reading of every session since 2019 in memory (about 5 GB for the
crypto group) although a live step only consumes: the training rows (one every train_step
sessions since train_floor), the sessions since the birth date (the voices' calls, trust and odds)
and the few sessions it decides on. prepare_live gives the live step the same numbers:
  * readings and the feature matrix come from evcache (memory maps, only new rows computed),
  * the weekly refits are cached on disk, keyed by the refit session and a hash of exactly the
    rows, grades and warm start each one learns from (a refit is reused only when it is the same fit),
  * the voices' calls and trust are kept from the birth date on (before it there is no model, so
    the full computation has NaN odds there and trust that has learned nothing),
with the timeline still full length, so every session keeps its row number from step to step.
Same code as the replay wherever it computes (model.fit_softmax, model.predict, model.losses,
model.mix, labels.triple_barrier); tests/test_lean.py and the proof in the scratchpad compare it
with backtest.prepare bar by bar.
"""
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

from . import evcache, evidence, labels, model
from .config import DATA_DIR

FITS_DIR = os.path.join(DATA_DIR, "evcache")


class Tail:
    """Rows lo .. n-1 of a full-length array, indexed by full-length row numbers. Reading a row
    before lo raises (the live step never needs one; the replay keeps full arrays)."""

    def __init__(self, arr, lo, n):
        self.arr, self.lo, self.n = arr, int(lo), int(n)
        self.shape = (self.n,) + tuple(arr.shape[1:])
        self.dtype = arr.dtype

    def __len__(self):
        return self.n

    def _row(self, k):
        k = int(k)
        if k < 0:
            k += self.n
        if not self.lo <= k < self.n:
            raise IndexError("row %d is outside the kept rows %d .. %d" % (k, self.lo, self.n - 1))
        return k - self.lo

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self[key[0]][key[1:]] if not isinstance(key[0], slice) else self[key[0]][(slice(None),) + key[1:]]
        if isinstance(key, slice):
            start, stop, step = key.indices(self.n)
            if start < self.lo and stop > start:
                raise IndexError("rows from %d: only %d .. %d are kept" % (start, self.lo, self.n - 1))
            return self.arr[start - self.lo:stop - self.lo:step]
        if isinstance(key, (int, np.integer)):
            return self.arr[self._row(key)]
        raise TypeError("Tail supports row numbers and slices, not %r" % (type(key),))

    def astype(self, dt):
        return Tail(self.arr.astype(dt), self.lo, self.n)

    def __array__(self, *a, **k):
        raise TypeError("a Tail is not a full-length array (rows %d .. %d only)" % (self.lo, self.n - 1))


# --------------------------------------------------------------------------------------------
# the weekly refits, cached
# --------------------------------------------------------------------------------------------
def _fit_sig(cfg):
    keys = ("horizon", "refit_every", "train_days", "train_step", "min_train_rows", "l2", "even_prior")
    s = json.dumps(dict((k, cfg.get(k)) for k in keys), sort_keys=True) + "|" + ",".join(model.VOICE_NAMES)
    s += "|" + json.dumps(dict((v, model._COLS[v]) for v in model.VOICE_NAMES), sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()


def walk_forward_cached(X, ready, y, cfg, birth_idx, floor_idx, n, fits_dir=None, log=None):
    """model.walk_forward's refits and calls for sessions birth_idx .. n-1, with each refit taken
    from disk when its key matches: (refit session, the exact training rows and grades of every
    asset, the warm start, the config) chained through every earlier refit of the walk.
    -> (probs {asset: Tail (n, voices, 3)}, models [(s, {voice: W}, rows)], report)"""
    assets = list(X)
    H, every = cfg["horizon"], cfg["refit_every"]
    span, step = cfg["train_days"] * 96, cfg["train_step"]
    V = len(model.VOICES)
    probs = dict((a, np.full((n - birth_idx, V, 3), np.nan)) for a in assets)
    models, warm = [], {}
    floor = birth_idx if floor_idx is None else floor_idx
    os.makedirs(fits_dir, exist_ok=True)
    chain = _fit_sig(cfg)
    hashers = dict((a, hashlib.sha256()) for a in assets)       # running hash of each asset's training rows
    fed = dict((a, 0) for a in assets)
    lat = None
    used, fitted, reused = set(), 0, 0
    for s in range(birth_idx, n, every):
        lo_row = max(floor, s - H - span + 1)
        rows = np.arange(lo_row, s - H + 1, step)
        if len(rows) == 0:
            continue
        prefix = lo_row == floor
        sels = []
        for a in assets:
            ok = ready[a][rows] & (y[a][rows] >= 0)
            sels.append(rows[ok])
        n_rows = int(sum(len(x) for x in sels))
        if n_rows < cfg["min_train_rows"]:
            continue

        def training():
            Xs = [np.asarray(np.asarray(X[a])[sel]) for a, sel in zip(assets, sels)]
            ys = [y[a][sel] for a, sel in zip(assets, sels)]
            return Xs, ys
        h = hashlib.sha256(chain.encode())
        h.update(str(int(s)).encode())
        if prefix:                                               # rows from floor: extend each running hash
            if lat is None:
                lat = np.arange(floor, n, step)
            for a in assets:
                k = int(np.searchsorted(lat, s - H, side="right"))
                new = lat[fed[a]:k]
                if len(new):
                    ok = ready[a][new] & (y[a][new] >= 0)
                    hashers[a].update(np.ascontiguousarray(new).tobytes())
                    hashers[a].update(np.ascontiguousarray(ok).tobytes())
                    hashers[a].update(np.ascontiguousarray(np.asarray(X[a][new[ok]])).tobytes())
                    hashers[a].update(np.ascontiguousarray(y[a][new[ok]]).tobytes())
                    fed[a] = k
                h.update(hashers[a].copy().digest())
        else:
            Xs, ys = training()
            for a, xa, ya in zip(assets, Xs, ys):
                h.update(a.encode())
                h.update(np.ascontiguousarray(xa).tobytes())
                h.update(np.ascontiguousarray(ya).tobytes())
        key = h.hexdigest()[:32]
        chain = key
        path = os.path.join(fits_dir, key + ".npz")
        raw = None
        if os.path.exists(path):
            try:
                with np.load(path) as z:
                    raw = dict((v, z[v]) for v in model.VOICES)
                reused += 1
            except Exception:
                raw = None
        if raw is None:
            Xs, ys = training()
            Xtr, ytr = np.concatenate(Xs), np.concatenate(ys)
            del Xs, ys
            raw = {}
            for v in model.VOICES:
                raw[v] = model.fit_softmax(Xtr[:, model._COLS[v]], ytr, cfg["l2"], warm.get(v))
                warm[v] = raw[v]
            np.savez(path + ".tmp.npz", **raw)
            os.replace(path + ".tmp.npz", path)
            fitted += 1
        warm = dict(raw)
        used.add(key)
        fitted_w = {}
        for vi, v in enumerate(model.VOICES):
            W = raw[v]
            if cfg.get("even_prior"):
                W = W.copy()
                W[:, 0] = W[:, 0].mean()
            fitted_w[v] = W
            for a in assets:
                chunk = slice(s, min(s + every, n))
                pr = model.predict(W, np.asarray(X[a][chunk])[:, model._COLS[v]])
                pr[~ready[a][chunk]] = np.nan
                probs[a][chunk.start - birth_idx:chunk.stop - birth_idx, vi] = pr
        models.append((s, fitted_w, n_rows))
        Xtr = ytr = None
    for f in os.listdir(fits_dir):                               # keep only this walk's refits
        if f.endswith(".npz") and f[:-4] not in used:
            try:
                os.remove(os.path.join(fits_dir, f))
            except OSError:
                pass
    return dict((a, Tail(p, birth_idx, n)) for a, p in probs.items()), models, {"refits": fitted, "reused": reused}


def trust_tail(probs, y, res, cfg, lo, n):
    """model.trust_path for sessions lo .. n-1, where lo is at or before the first session with a
    call (no loss arrives before it, so the running sum starts at exactly zero there)."""
    assets = list(probs)
    V = probs[assets[0]].shape[1]
    arriving = np.zeros((n - lo, V))
    for a in assets:
        L = model.losses(probs[a].arr, y[a][lo:n])
        idx = np.where(np.isfinite(L[:, 0]))[0]
        r = res[a][lo:n]
        idx = idx[idx + lo + r[idx] < n]
        np.add.at(arriving, idx + r[idx], L[idx])
    decay = 0.5 ** (1.0 / cfg["trust_halflife"])
    eta, floor = cfg["trust_eta"], cfg["trust_floor"]
    out = np.empty((n - lo, V))
    S = np.zeros(V)
    for s in range(n - lo):
        S = decay * S + arriving[s]
        w = np.exp(-eta * (S - S.min()))
        w = np.maximum(w / w.sum(), floor)
        out[s] = w / w.sum()
    return out


def prepare_live(cfg, bars, funding, live, group, log=None, root=None):
    """backtest.prepare for the live step (see the module doc). -> the same dict keys, with
    "lean_lo" (the first row kept for probs / trust) and "evcache" (the store's report)."""
    t0 = time.time()
    say = log or (lambda *_: None)
    stores, common, rep = evcache.update(group, bars, funding, live, cfg, log=say, root=root)
    assets = list(bars)
    times = common
    n = len(times)
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        ev[a] = st.frame(times)
        X[a] = st.X()
        ready[a] = st.ready()
        b = bars[a].loc[times]
        px[a] = dict((k, b[k].values) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    say("evidence store: %d rows written, %s (%.0fs)" % (rep["rows_written"], rep, time.time() - t0))
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    fits = os.path.join(root or FITS_DIR, group, "fits")
    probs, models, frep = walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n, fits)
    say("voices: %d refits, %d from the cache (%.0fs)" % (frep["refits"], frep["reused"], time.time() - t0))
    lo = birth_idx
    trust = trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))             # v5.2: no card above the cap
    odds = {}
    for a in assets:
        Xa = np.asarray(X[a][lo:n])
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        del Xa, speaks, w
    say("trust and odds done (%.0fs)" % (time.time() - t0))
    return {"cfg": dict(cfg), "assets": assets, "times": times, "ev": ev, "px": px, "X": X, "ready": ready,
            "y": y, "res": res, "probs": probs, "models": models, "trust": Tail(trust, lo, n), "odds": odds,
            "birth_idx": birth_idx, "lean_lo": lo, "evcache": rep, "fits": frep}
