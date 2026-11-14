# -*- coding: utf-8 -*-
"""families -- the registered rules (research/HYPOTHESES.md H20-H24). Each turns point-in-time features
into a target decided at a bar's close (the backtester fills it at the next open).

Every loop below reads row t only (and its own state), so no rule can see a later bar.
"""
import itertools

import numpy as np
import pandas as pd

from . import core

# ------------------------------------------------------------------ family 1: filters on 15m bases

BASES = {"mom": ("z_mom", (0.0, 1.0)), "ema": ("z_ema", (0.0, 1.0)), "mr": ("z_mr", (2.0, 2.5))}
TRENDS = ("none", "4h", "1d", "both")
GATES = (0.0, 1.5, 2.5)
SESSIONS = ("all", "active")
HOLDS = (1, 16, 96)
COOLS = (0, 96)


def f1_keys():
    out = []
    for b, (_, es) in BASES.items():
        for e, T, k, S, H, CD in itertools.product(es, TRENDS, GATES, SESSIONS, HOLDS, COOLS):
            out.append((b, e, T, k, S, H, CD))
    return out


def ladder():
    """H21: fixed levels per base (name, key)."""
    out = []
    for b, (_, es) in BASES.items():
        e0, e1 = es
        lv = [("L0 base", (b, e0, "none", 0.0, "all", 1, 0)),
              ("L1 +hold16", (b, e0, "none", 0.0, "all", 16, 0)),
              ("L2 hold96", (b, e0, "none", 0.0, "all", 96, 0)),
              ("L3 +trend1d", (b, e0, "1d", 0.0, "all", 96, 0)),
              ("L4 +confidence", (b, e1, "1d", 0.0, "all", 96, 0)),
              ("L5 +costgate", (b, e1, "1d", 1.5, "all", 96, 0)),
              ("L6 +session", (b, e1, "1d", 1.5, "active", 96, 0)),
              ("L7 +cooldown", (b, e1, "1d", 1.5, "active", 96, 96))]
        out += [(b, n, k) for n, k in lv]
    return out


def raw_side(z, e):
    """Long when z > e, short when z < -e, flat once z crosses 0 (hysteresis); e = 0 is sign(z)."""
    z = np.asarray(z, dtype=float)
    if e == 0:
        return np.sign(z)
    ev = np.full(len(z), np.nan)
    sz = np.sign(z)
    cross = np.zeros(len(z), dtype=bool)
    cross[1:] = (sz[1:] != sz[:-1])
    ev[cross] = 0.0
    ev[z > e] = 1.0
    ev[z < -e] = -1.0
    return pd.Series(ev).ffill().fillna(0.0).values


def run_state(raw, gate, H, CD, close):
    """raw desired side per bar; gate = entry allowed; H = min bars between changes; CD = bars of no entry
    after a losing close. -> target per bar."""
    n = len(raw)
    rl = raw.tolist()
    gl = gate.tolist() if gate is not None else [True] * n
    cl = close.tolist()
    out = [0.0] * n
    cur, last, cool, epx = 0.0, -10 ** 9, -1, 0.0
    for t in range(n):
        r = rl[t]
        if r != cur and t - last >= H:
            new = r
            if r != 0 and (not gl[t] or t < cool):
                new = 0.0
            if new != cur:
                if cur != 0 and CD > 0:
                    if (cl[t] / epx - 1.0) * (1.0 if cur > 0 else -1.0) < 0:
                        cool = t + CD
                        if new != 0:
                            new = 0.0
                if new != cur:
                    cur, last = new, t
                    if cur != 0:
                        epx = cl[t]
        out[t] = cur
    return np.asarray(out)


class F1:
    def __init__(self, feats, close):
        self.f, self.close = feats, np.asarray(close, dtype=float)
        rv = feats["rv96"].values
        self.ratio = (rv * 2.0) / (2.0 * (core.FEE_HEAD + 0.5e-4 + 0.10 * rv))
        self._raw = {}

    def raw(self, b, e, T):
        k = (b, e, T)
        if k not in self._raw:
            s = raw_side(self.f[BASES[b][0]].values, e)
            if T in ("4h", "both"):
                s = np.where(s == self.f["trend4h"].values, s, 0.0)
            if T in ("1d", "both"):
                s = np.where(s == self.f["trend1d"].values, s, 0.0)
            self._raw[k] = s
        return self._raw[k]

    def target(self, key):
        b, e, T, k, S, H, CD = key
        gate = np.ones(len(self.close), dtype=bool)
        if k > 0:
            gate &= self.ratio >= k
        if S == "active":
            gate &= self.f["active"].values
        return run_state(self.raw(b, e, T), gate, H, CD, self.close)


def f1_name(key):
    b, e, T, k, S, H, CD = key
    return "%s e=%g trend=%s gate=%g session=%s hold=%d cool=%d" % (b, e, T, k, S, H, CD)


# ------------------------------------------------------------------ family 2: meta-labeling on daily momentum

SHORTS = (0.0, 0.5, 1.0)
SIZES = ("R0", "R1", "R2", "R3")
ENTRIES = (("E0", 0.0, 0), ("E1", 0.5, 24), ("E2", 1.0, 48))


def f2_keys():
    return [(s, r, e[0]) for s, r, e in itertools.product(SHORTS, SIZES, ENTRIES)]


def vol_regime(feats):
    """R1: at each daily decision, 1 if rv672 <= trailing 365-day median of rv672 at daily decisions, else 0.5;
    held until the next daily decision."""
    d = feats["is_daily"].values
    v = feats["rv672"].values
    out = np.full(len(v), np.nan)
    vd = pd.Series(v[d])
    med = vd.rolling(365, min_periods=60).median().values
    sz = np.where(np.isnan(med) | np.isnan(vd.values), 1.0, np.where(vd.values <= med, 1.0, 0.5))
    out[d] = sz
    return pd.Series(out).ffill().fillna(1.0).values


class F2:
    def __init__(self, feats, close):
        self.f, self.close = feats, np.asarray(close, dtype=float)
        self.d = feats["trend1d"].values
        self.R1 = vol_regime(feats)

    def target(self, key):
        short_size, R, E = key
        f = self.f
        d = self.d
        agree = (f["trend4h"].values == d)
        if R == "R0":
            size = np.ones(len(d))
        elif R == "R1":
            size = self.R1
        elif R == "R2":
            size = np.where(agree, 1.0, 0.5)
        else:
            size = np.where(agree, 1.0, 0.0)
        size = size * np.where(d < 0, short_size, 1.0)
        want = d * size                                  # desired exposure without entry timing
        if E == "E0":
            return want
        a, W = dict((e[0], (e[1], e[2])) for e in ENTRIES)[E]
        c = self.close.tolist()
        lvl_lo = (f["ema20"].values - a * f["atr14"].values).tolist()
        lvl_hi = (f["ema20"].values + a * f["atr14"].values).tolist()
        dl = np.sign(d).tolist()
        wl = want.tolist()
        out = [0.0] * len(c)
        waiting, prev_dir, wait_from = False, 0.0, -1
        for t in range(len(c)):
            dt = dl[t]
            if dt != prev_dir:                       # a new daily direction: wait for a pullback
                waiting, wait_from, prev_dir = dt != 0, t, dt
            if waiting:
                pull = (c[t] <= lvl_lo[t]) if dt > 0 else (c[t] >= lvl_hi[t])
                if pull or t - wait_from >= W:
                    waiting = False
            out[t] = 0.0 if waiting else wl[t]
        return np.asarray(out)


def f2_name(key):
    return "short=%g size=%s entry=%s" % key


# ------------------------------------------------------------------ family 3: core-satellite

SIGNALS = ("ema15m", "trend4h", "mom1d")
BANDS = ((0.5, 1.5), (0.0, 1.5), (0.0, 1.0))
F3HOLD = (16, 96)


def f3_keys():
    return list(itertools.product(SIGNALS, BANDS, F3HOLD))


class F3:
    def __init__(self, feats, close):
        self.f, self.close = feats, np.asarray(close, dtype=float)

    def target(self, key):
        sig, (lo, hi), H = key
        s = {"ema15m": np.sign(self.f["z_ema"].values), "trend4h": self.f["trend4h"].values,
             "mom1d": self.f["trend1d"].values}[sig]
        raw = np.where(s > 0, hi, np.where(s < 0, lo, 1.0))
        return run_state(raw, None, H, 0, self.close)


def f3_name(key):
    sig, (lo, hi), H = key
    return "core 1x, signal=%s band=[%g, %g] hold=%d" % (sig, lo, hi, H)


# ------------------------------------------------------------------ family 4: replay trades

def replay_filter(trades, bars, split="2023-06-07"):
    """H24 on one coin's replay trades (entered before the seal). -> dict of per-half stats."""
    t = trades.copy()
    t["time_in"] = pd.to_datetime(t["time_in"], utc=True)
    t = t[t["time_in"] < core.HOLDOUT_START]
    mom = pd.Series(core.benchmarks.momentum(bars["close"]).values, index=bars.index)
    # sign known at the bar BEFORE entry (the entry bar's open follows the previous bar's close)
    prev = mom.shift(1).reindex(t["time_in"], method="ffill").values
    t["mom"] = prev
    t["aligned"] = np.sign(t["side"].values) == np.sign(prev)
    out = {}
    sp = pd.Timestamp(split, tz="UTC")
    for name, m in (("first", t["time_in"] < sp), ("second", t["time_in"] >= sp), ("all", t["time_in"] > pd.Timestamp(0, tz="UTC"))):
        x = t[m]
        k = x[x["aligned"]]
        out[name] = {"trades": int(len(x)), "mean_pct_all": float(x["pnl_pct"].mean()) if len(x) else 0.0,
                     "compound_all_pct": float((np.prod(1 + x["pnl_pct"].values / 100.0) - 1) * 100) if len(x) else 0.0,
                     "kept": int(len(k)), "mean_pct_kept": float(k["pnl_pct"].mean()) if len(k) else 0.0,
                     "compound_kept_pct": float((np.prod(1 + k["pnl_pct"].values / 100.0) - 1) * 100) if len(k) else 0.0,
                     "win_rate_all": float((x["pnl_pct"] > 0).mean()) if len(x) else 0.0,
                     "win_rate_kept": float((k["pnl_pct"] > 0).mean()) if len(k) else 0.0}
    return out
