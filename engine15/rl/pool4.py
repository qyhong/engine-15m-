# -*- coding: utf-8 -*-
"""pool4 -- Phase 4 data: one asset at a time, into memory-mapped float32 arrays, then pooled per fold.

prepare(cfg, asset) loads an asset's 15m bars (BTC: the RL perp store, as Phases 1-3; every other market: the engine's own
file, read only), cuts them at the frozen data end, builds the Phase 4 inputs (features4: Phase 3 features + readings +
availability flags) and the per-bar reward arrays of the shared cost model (qagent.reward_arrays), and saves:

    phase4_cache/<asset>/X.npy        float32 (n, F)   inputs, all columns (variants pick theirs by name)
    phase4_cache/<asset>/rd_<k>.npy   float32 (n,)     g, c1, k, v, rpx, rate (see qagent.py)
    phase4_cache/<asset>/times.npy    int64   (n,)     bar open times (ms)
    phase4_cache/<asset>/meta.json                     columns, cost model, first trainable bar

Training reads them back with mmap_mode='r' (the OS pages in only what a fold touches). Nothing here feeds the live engine.

Fold geometry (by TIME, so assets with different sessions line up): for fold f with selection boundary S (validation
start) and test start T, an asset's rows are [start_a, S_a) to select / validate and [start_a, T_a) to refit, where X_a is
the first bar of that asset at or after time X. A training row t needs its target's last price by the close of bar
boundary - 1, so rows end at boundary - horizon - 1.
"""
import json
import os

import numpy as np
import pandas as pd

from . import costs, features4, qagent
from .config import resolve
from .env import Market

RD_KEYS = ("g", "c1", "k", "v", "rpx", "rate")


def cache_dir(cfg):
    return resolve(cfg["report"]["cache_dir"])


def asset_model(cfg, asset, fee_side=None):
    """Cost model of an asset: BTC / ETH = the shared perp model (0.10% headline, 0.05% comparison, funding on);
    other markets = their engine15/config.py asset_cost a side (spread included), no funding data, same slippage rule."""
    a = cfg["assets"][asset]
    if a.get("cost_side") is None:
        return costs.from_cfg(cfg, fee_side)
    c = dict(cfg["costs"])
    c.update({"fee_side": float(a["cost_side"]), "half_spread_bps": 0.0, "funding": False})
    return costs.CostModel.from_cfg(c)


def load_bars(cfg, asset, offline=True, log=print):
    """-> (bars, funding frame with rate / settle_ms) cut at cfg['data_end']."""
    from . import data as rdata, phase3
    a = cfg["assets"][asset]
    if a["source"] == "rl_store":
        import copy
        c = copy.deepcopy(cfg)
        c["data"]["symbol"] = asset
        c["assets"] = {asset: {"source": "rl_store"}}
        bars, fund, _ = phase3.load_bars(c, offline, log)
        return bars, fund
    from .. import data as edata
    bars = edata.load(asset)[["open", "high", "low", "close", "volume"]].astype(float)
    f = edata.load_funding(asset)
    raw = np.asarray(f.index.as_unit("ms").asi8, dtype="int64") if len(f) else np.zeros(0, dtype="int64")
    fund = pd.DataFrame({"rate": np.asarray(f.values, dtype=float), "settle_ms": rdata.settlement_ms(raw)},
                        index=f.index if len(f) else pd.DatetimeIndex([], tz="UTC"))
    end = cfg.get("data_end")
    if end:
        cut = pd.Timestamp(end, tz="UTC")
        bars = bars[bars.index < cut]
        fund = fund[np.asarray(fund["settle_ms"]) < int(cut.value // 10**6)]
    return bars, fund


def prepare(cfg, asset, offline=True, log=print, readings_root=None, force=False, bars_fund=None):
    """Build (or reuse) the cached arrays of one asset. -> cache folder."""
    d = os.path.join(cache_dir(cfg), asset)
    if not force and os.path.exists(os.path.join(d, "meta.json")):
        return d
    os.makedirs(d, exist_ok=True)
    bars, fund = bars_fund if bars_fund is not None else load_bars(cfg, asset, offline, log)
    snap = None
    if cfg.get("readings_source", "evcache") == "evcache":
        snap = features4.snapshot(asset, cache_dir(cfg), root=readings_root, log=log)
    rf = features4.readings_frame(snap, bars.index) if snap else None
    feats = features4.build(bars, fund, cfg["features"], rf).astype("float32")
    model = asset_model(cfg, asset)
    m = Market(bars, fund, feats, model)
    rd = qagent.reward_arrays(m, cfg["qagent"])
    np.save(os.path.join(d, "X.npy"), m.raw)
    for k in RD_KEYS:
        np.save(os.path.join(d, "rd_%s.npy" % k), rd[k])
    np.save(os.path.join(d, "times.npy"), np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64))
    warm = int(cfg["train4"]["warmup_days"]) * 96
    meta = {"asset": asset, "n": int(len(bars)), "first": str(bars.index[0]), "last": str(bars.index[-1]),
            "columns": list(m.columns), "model": model.as_dict(), "start": int(min(warm, len(bars) - 1)),
            "readings": snap is not None}
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    log("%s: %d bars %s .. %s, %d inputs, cached in %s" % (asset, len(bars), bars.index[0], bars.index[-1],
                                                           len(m.columns), d))
    del m, feats, rf, rd
    return d


class Asset:
    """Memory-mapped view of one asset's cached arrays."""

    def __init__(self, folder):
        with open(os.path.join(folder, "meta.json"), encoding="utf-8") as fh:
            self.meta = json.load(fh)
        self.name = self.meta["asset"]
        self.X = np.load(os.path.join(folder, "X.npy"), mmap_mode="r")
        self.rd = dict((k, np.load(os.path.join(folder, "rd_%s.npy" % k), mmap_mode="r")) for k in RD_KEYS)
        self.t = np.load(os.path.join(folder, "times.npy"))
        self.n = int(self.meta["n"])
        self.start = int(self.meta["start"])
        self.columns = self.meta["columns"]

    def cols(self, names):
        return np.array([self.columns.index(c) for c in names], dtype=np.intp)

    def at(self, ts):
        """First bar at or after time ts (pandas Timestamp)."""
        return int(np.searchsorted(self.t, int(pd.Timestamp(ts).value // 10**6)))


def norm_stats(X, lo, hi, cols, chunk=60000):
    """Per-column mean / sd over rows [lo, hi) ignoring NaN (float64 accumulation, chunked). sd 0 -> 1."""
    k = len(cols)
    s, ss, cnt = np.zeros(k), np.zeros(k), np.zeros(k)
    for a in range(lo, hi, chunk):
        x = np.asarray(X[a:min(hi, a + chunk)][:, cols], dtype=np.float64)
        ok = np.isfinite(x)
        x = np.where(ok, x, 0.0)
        s += x.sum(0)
        ss += (x * x).sum(0)
        cnt += ok.sum(0)
    mu = np.where(cnt > 0, s / np.maximum(cnt, 1), 0.0)
    var = np.where(cnt > 1, ss / np.maximum(cnt, 1) - mu * mu, 0.0)
    sd = np.sqrt(np.maximum(var, 0.0))
    sd = np.where(sd > 1e-12, sd, 1.0)
    return mu.astype(np.float32), sd.astype(np.float32)


def normalised(X, lo, hi, cols, mu, sd, clip=5.0):
    """Rows [lo, hi) of the chosen columns, z-scored, clipped, NaN -> 0 (float32)."""
    x = (np.asarray(X[lo:hi][:, cols], dtype=np.float32) - mu) / sd
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    np.clip(x, -clip, clip, out=x)
    return x


def recency(t_ms, now_ms, half_life_days):
    """Recency weight of rows stamped t_ms seen from now_ms: 0.5 ** (age / half-life); None / 0 = no recency."""
    if not half_life_days:
        return np.ones(len(t_ms))
    age = (float(now_ms) - np.asarray(t_ms, dtype=np.float64)) / 86400000.0
    return np.power(0.5, age / float(half_life_days))


def bootstrap_counts(n, block, rng):
    """Block bootstrap multiplicities for n rows (blocks of `block` rows drawn with replacement)."""
    if n <= 0:
        return np.zeros(0)
    nb = max(1, int(np.ceil(n / float(block))))
    draw = rng.integers(0, nb, nb)
    c = np.bincount(draw, minlength=nb).astype(np.float64)
    return np.repeat(c, block)[:n]
