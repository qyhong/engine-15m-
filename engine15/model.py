# -*- coding: utf-8 -*-
"""model -- stages 2 and 3 of the thought process: the VOICES and how much each is TRUSTED.

A voice is one way of thinking about the tape. Each voice sees only its own evidence and
answers the same question at every 15m close: "over the next 24 hours, will price touch
one barrier up first, one barrier down first, or neither?" -- three probabilities.

Two learning loops, both fed only by calls whose grade is already known:
  1. REFIT (daily): every voice is refitted on the last 180 days of graded calls
     (a 3-class logistic regression with a ridge; no third-party library).
  2. TRUST (every session): each call graded up or down costs each voice its error on the
     DIRECTION; trust is the Hedge weight exp(-eta x discounted loss), floored so no voice
     is ever fully ignored.
The engine's own odds are the trust-weighted mix of the voices.

Classes: 0 NEITHER (reference), 1 UP, 2 DOWN (labels.py).
"""
from collections import OrderedDict

import numpy as np

from .evidence import FEATURES, GROUPS

# One voice per evidence group, then the whole evidence at once, then the no-skill baseline.
VOICES = OrderedDict(list(GROUPS.items()) + [
    ("all", ("All the evidence at once", list(FEATURES))),
    ("base", ("Base rate (no skill)", [])),
])
VOICE_NAMES = list(VOICES)
_COLS = dict((v, [FEATURES.index(f) for f in VOICES[v][1]]) for v in VOICES)


def fit_softmax(X, y, l2=10.0, W0=None, iters=6):
    """3-class logistic regression by Newton steps. X (n, d), y in {0, 1, 2}.
    -> W (2, d + 1): row 0 the UP logit, row 1 the DOWN logit, against NEITHER; column 0
    the intercept (not penalised)."""
    n, d = X.shape
    p = d + 1
    Xb = np.empty((n, p))
    Xb[:, 0] = 1.0
    Xb[:, 1:] = X
    Y = np.stack([y == 1, y == 2], axis=1).astype(float)
    W = np.zeros((2, p)) if W0 is None else W0.copy()
    ridge = np.full(p, float(l2))
    ridge[0] = 1e-6
    for _ in range(iters):
        P = _probs(Xb @ W.T)[:, 1:]
        G = (Xb.T @ (P - Y)).T + ridge * W
        H = np.zeros((2 * p, 2 * p))
        for a in (0, 1):
            for b in (a, 1) if a == 0 else (1,):
                blk = Xb.T @ (Xb * (P[:, a] * ((a == b) - P[:, b]))[:, None])
                H[a * p:(a + 1) * p, b * p:(b + 1) * p] = blk
                H[b * p:(b + 1) * p, a * p:(a + 1) * p] = blk.T
        H[np.diag_indices(2 * p)] += np.tile(ridge, 2)
        step = np.linalg.solve(H, G.ravel()).reshape(2, p)
        W -= step
        if np.abs(step).max() < 1e-7:
            break
    return W


def _probs(Z):
    """logits (n, 2) for UP, DOWN -> probabilities (n, 3) for NEITHER, UP, DOWN."""
    full = np.concatenate([np.zeros((len(Z), 1)), Z], axis=1)
    full -= full.max(axis=1, keepdims=True)
    e = np.exp(full)
    return e / e.sum(axis=1, keepdims=True)


def predict(W, X):
    return _probs(W[:, 0] + X @ W[:, 1:].T)


def walk_forward(X, ready, y, cfg, birth_idx, n_end=None, floor_idx=None):
    """The daily refit, walked through history with no look-ahead.

    X, ready, y: {asset: array} on ONE common timeline of n sessions. At refit session s a
    voice may train only on rows t <= s - horizon (their grade is known by the close of s),
    never before birth_idx, one row an hour, all assets pooled; the fitted voice then
    answers sessions s .. s + refit_every - 1.
    -> probs {asset: (n, voices, 3)} (NaN where the engine has no model or no evidence),
       models [(s, {voice: W})]."""
    assets = list(X)
    n = len(y[assets[0]]) if n_end is None else n_end
    H, every = cfg["horizon"], cfg["refit_every"]
    span, step = cfg["train_days"] * 96, cfg["train_step"]
    probs = dict((a, np.full((n, len(VOICES), 3), np.nan)) for a in assets)
    models, warm = [], {}
    floor = birth_idx if floor_idx is None else floor_idx       # the first row a voice may learn from
    for s in range(birth_idx, n, every):
        rows = np.arange(max(floor, s - H - span + 1), s - H + 1, step)
        if len(rows) == 0:
            continue
        Xs, ys = [], []
        for a in assets:
            ok = ready[a][rows] & (y[a][rows] >= 0)
            Xs.append(X[a][rows[ok]])
            ys.append(y[a][rows[ok]])
        Xtr, ytr = np.concatenate(Xs), np.concatenate(ys)
        if len(ytr) < cfg["min_train_rows"]:
            continue
        fitted = {}
        for vi, v in enumerate(VOICES):
            W = fit_softmax(Xtr[:, _COLS[v]], ytr, cfg["l2"], warm.get(v))
            warm[v] = W
            if cfg.get("even_prior"):                # no standing lean: up and down start level
                W = W.copy()
                W[:, 0] = W[:, 0].mean()
            fitted[v] = W
            for a in assets:
                chunk = slice(s, min(s + every, n))
                pr = predict(W, X[a][chunk][:, _COLS[v]])
                pr[~ready[a][chunk]] = np.nan
                probs[a][chunk, vi] = pr
        models.append((s, fitted, len(ytr)))
    return probs, models


def losses(probs, y):
    """What each voice's call cost it, on every call graded UP or DOWN: (n, voices), NaN elsewhere.

    The loss is on DIRECTION only: -log of the share of its up-plus-down odds the voice had
    put on the side that happened. The mandate asks one thing, long or short, so a voice is
    trusted for telling up from down. (Scoring all three classes let the volatility voice,
    which is good at "neither" and silent on direction, take three quarters of the trust on
    the first live step, 10 Nov 2026; that is why this is directional.)"""
    n, V, _ = probs.shape
    out = np.full((n, V), np.nan)
    ok = (y > 0) & np.isfinite(probs[:, 0, 0])
    idx = np.where(ok)[0]
    side = probs[idx, :, y[idx].astype(int)]
    out[idx] = -np.log(np.clip(side / np.clip(probs[idx, :, 1] + probs[idx, :, 2], 1e-9, None), 1e-9, 1.0))
    return out


def trust_path(probs, y, res, cfg):
    """Trust in each voice at every session, from calls graded AT OR BEFORE that session.
    A call made at t is graded at t + res[t]; its loss enters the sum there, never earlier.
    -> (n, voices), rows sum to 1."""
    assets = list(probs)
    n, V = probs[assets[0]].shape[:2]
    arriving = np.zeros((n, V))
    for a in assets:
        L = losses(probs[a], y[a])
        idx = np.where(np.isfinite(L[:, 0]))[0]
        idx = idx[idx + res[a][idx] < n]                 # a grade that arrives after the data ends is not known yet
        np.add.at(arriving, idx + res[a][idx], L[idx])
    decay = 0.5 ** (1.0 / cfg["trust_halflife"])
    eta, floor = cfg["trust_eta"], cfg["trust_floor"]
    out = np.empty((n, V))
    S = np.zeros(V)
    for s in range(n):
        S = decay * S + arriving[s]
        w = np.exp(-eta * (S - S.min()))
        w = np.maximum(w / w.sum(), floor)
        out[s] = w / w.sum()
    return out


def mix(probs, trust):
    """The engine's own odds: the trust-weighted mix of the voices. (n, 3)."""
    return np.einsum("nv,nvc->nc", trust, probs)


def evidence_pulls(W_all, x):
    """Inside the 'all' voice: how far each reading pushes the UP-minus-DOWN logit.
    -> [(feature, push)] strongest first by size."""
    push = (W_all[0, 1:] - W_all[1, 1:]) * x
    order = np.argsort(-np.abs(push))
    return [(FEATURES[i], float(push[i])) for i in order]
