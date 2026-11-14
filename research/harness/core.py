# -*- coding: utf-8 -*-
"""core -- data, point-in-time features, a lean backtester that reproduces engine15.rl.backtest bit for bit,
walk-forward selection, benchmarks, random matched-frequency strategies, break-even fees and the
multiple-testing helpers. Read-only use of engine15 (costs, metrics, benchmarks, walkforward, data).

Sealed holdout: bars from HOLDOUT_START on are dropped by load(..., dev_only=True), which every
development run uses. Only research/harness/holdout.py may load them, and only for ledgered looks.
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15 import data as edata                          # noqa: E402
from engine15.rl import benchmarks, costs, metrics, store, walkforward  # noqa: E402
from engine15.rl import data as rldata                      # noqa: E402

HOLDOUT_START = pd.Timestamp("2025-11-11", tz="UTC")
DATA_START = pd.Timestamp("2019-09-08 19:00", tz="UTC")       # BTC perp listing (Phase 1/2 start)
WF = dict(train_months=12, test_months=3, step_months=3, start="2019-10-01", min_test_days=30)
FEE_HEAD, FEE_ALT = 0.0010, 0.0005
COST_KW = dict(half_spread_bps=0.5, slippage_coef=0.10, slippage_vol_window=96, funding=True, delay_bars=1)
BPY = metrics.BARS_PER_YEAR
OUT_DIR = os.path.join(ROOT, "research", "out", "harness")


def model(fee=FEE_HEAD):
    return costs.CostModel(fee_side=fee, **COST_KW)


# ------------------------------------------------------------------ data

def load(asset, dev_only=True):
    """-> (bars with open/high/low/close/volume, funding frame rate/settle_ms). BTC = the RL perp store."""
    if asset == "BTCUSDT":
        cfg = {"data": {"dir": "data/rl", "symbol": "BTCUSDT", "interval_ms": 900000, "funding_snap_s": 60}}
        bars = rldata.load_bars(cfg)[["open", "high", "low", "close", "volume"]]
        fund = rldata.load_funding(cfg)
    else:
        bars = edata.load(asset)[["open", "high", "low", "close", "volume"]]
        f = edata.load_funding(asset)
        raw = edata.to_ms(f.index) if len(f) else np.zeros(0, dtype="int64")
        fund = pd.DataFrame({"rate": f.values.astype(float), "settle_ms": rldata.settlement_ms(raw)}, index=f.index)
    bars = bars[bars.index >= DATA_START].astype(float)
    if dev_only:
        bars = bars[bars.index < HOLDOUT_START]
        hold_ms = int(HOLDOUT_START.value // 10**6)
        fund = fund[np.asarray(fund["settle_ms"]) < hold_ms]
    return bars, fund


# ------------------------------------------------------------------ features (closed bars only)

def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def features(bars):
    """Every column at row t uses bars <= t only (4h through engine15.data.htf_on_15)."""
    c = bars["close"].values.astype(float)
    lr = np.log(bars["close"]).diff()
    rv96 = lr.rolling(96, min_periods=2).std().fillna(0.0).values
    rv672 = lr.rolling(672, min_periods=96).std().values
    vol4 = np.where(rv96 > 0, rv96 * 4.0, np.nan)
    f = {}
    f["z_mom"] = np.nan_to_num(np.log(bars["close"]).diff(16).values / vol4)
    e20, e50 = ema(c, 20), ema(c, 50)
    f["z_ema"] = np.nan_to_num((e20 - e50) / (c * vol4))
    sma = bars["close"].rolling(48).mean().values
    sd = bars["close"].rolling(48).std().values
    f["z_mr"] = np.nan_to_num(-(c - sma) / np.where(sd > 0, sd, np.nan))
    f["rv96"], f["rv672"] = rv96, rv672
    f["ema20"] = e20
    h, lo = bars["high"].values, bars["low"].values
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    f["atr14"] = pd.Series(tr).ewm(alpha=1 / 14.0, adjust=False).mean().values
    b4 = edata.resample(bars.assign(taker_buy=0.0), "4h")
    t4 = np.sign(b4["close"] - b4["close"].ewm(span=50, adjust=False).mean())
    f["trend4h"] = np.nan_to_num(edata.htf_on_15(bars, "4h", t4).values.astype(float))
    f["trend1d"] = benchmarks.momentum(bars["close"]).values          # frozen daily 30-day sign, as decided
    close_ms = store.to_ms(bars.index) + 900000
    hr = (close_ms // 3600000) % 24
    f["active"] = (hr >= 12) & (hr < 21)
    f["is_daily"] = (close_ms % 86400000) == 0
    f["is_4h"] = (close_ms % 14400000) == 0
    return pd.DataFrame(f, index=bars.index)


# ------------------------------------------------------------------ lean backtester

class Market:
    """Precomputed per-bar arrays; net(target, fee) reproduces engine15.rl.backtest.run's r_net exactly
    (no clipping, so exposures above 1x are allowed: every cost term is linear in position)."""

    def __init__(self, bars, fund):
        self.index = bars.index
        o, c = bars["open"].values.astype(float), bars["close"].values.astype(float)
        nxt = np.append(o[1:], c[-1])
        self.r_px = nxt / o - 1.0
        m = model()
        vol = m.bar_vol(bars)
        self.vol_dec = np.zeros_like(vol)
        self.vol_dec[1:] = vol[:-1]
        self.rate = m.funding_on_bars(bars.index, fund)
        self.close = c

    @staticmethod
    def funded(pos, spot=False):
        """Position that pays funding. spot=True: the long part up to 1x is spot (no funding); above 1x and shorts are perp."""
        return (np.minimum(pos, 0.0) + np.maximum(pos - 1.0, 0.0)) if spot else pos

    def parts(self, target, spot=False):
        t = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
        pos = np.zeros_like(t)
        pos[1:] = t[:-1]
        trade = np.diff(pos, prepend=0.0)
        a = np.abs(trade)
        gross = pos * self.r_px
        other = COST_KW["half_spread_bps"] * 1e-4 * a + COST_KW["slippage_coef"] * self.vol_dec * a + self.funded(pos, spot) * self.rate
        return pos, trade, gross, other, a

    def net(self, target, fee=FEE_HEAD, spot=False):
        pos, trade, gross, other, a = self.parts(target, spot)
        return gross - other - fee * a

    def frame(self, target, fee=FEE_HEAD, spot=False):
        pos, trade, gross, other, a = self.parts(target, spot)
        hs = COST_KW["half_spread_bps"] * 1e-4 * a
        sl = COST_KW["slippage_coef"] * self.vol_dec * a
        fu = self.funded(pos, spot) * self.rate
        fe = fee * a
        return pd.DataFrame({"pos": pos, "trade": trade, "r_gross": gross, "fee": fe, "spread": hs,
                             "slippage": sl, "funding": fu, "r_net": gross - fe - hs - sl - fu}, index=self.index)


# ------------------------------------------------------------------ walk-forward

def windows(index):
    return walkforward.windows(index, **WF)


def masks(index, wins):
    tr = [walkforward.mask(index, w["train_start"], w["train_end"]) for w in wins]
    te = [walkforward.mask(index, w["test_start"], w["test_end"]) for w in wins]
    return tr, te


def slice_sharpe(r, m):
    x = r[m]
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(BPY)) if sd > 0 else -9.0


def stitch(index, wins, choice, target_of):
    """choice[i] = variant key for fold i; target_of(key) -> full-history target. -> stitched target."""
    out = np.zeros(len(index))
    _, te = masks(index, wins)
    cache = {}
    for i, k in enumerate(choice):
        if k not in cache:
            cache[k] = np.asarray(target_of(k), dtype=float)
        out[te[i]] = cache[k][te[i]]
    return out


def evaluate(mkt, target, wins, fee=FEE_HEAD, spot=False):
    fr = mkt.frame(target, fee, spot)
    return walkforward.evaluate(fr, wins), fr


def select(mkt, wins, keys, target_of, fee=FEE_HEAD, log=None, spot=False):
    """Per fold, the key with the best train-window net Sharpe. Also returns each key's per-fold train
    Sharpe, trades/yr and CAGR (training data: exploration only)."""
    tr, _ = masks(mkt.index, wins)
    sh = np.zeros((len(keys), len(wins)))
    tpy = np.zeros_like(sh)
    cg = np.zeros_like(sh)
    for j, k in enumerate(keys):
        t = np.asarray(target_of(k), dtype=float)
        r = mkt.net(t, fee, spot)
        pos = np.zeros_like(t)
        pos[1:] = t[:-1]
        ch = np.diff(pos, prepend=0.0) != 0
        for i, m in enumerate(tr):
            sh[j, i] = slice_sharpe(r, m)
            yrs = m.sum() / BPY
            tpy[j, i] = ch[m].sum() / yrs
            cg[j, i] = metrics.cagr(r[m])
        if log and (j + 1) % 100 == 0:
            log("  selected over %d / %d variants" % (j + 1, len(keys)))
    choice = [keys[int(np.argmax(sh[:, i]))] for i in range(len(wins))]
    return choice, {"sharpe": sh, "trades_per_year": tpy, "cagr": cg}


# ------------------------------------------------------------------ benchmarks and random

def random_matched(index, oos, pos_oos, seed):
    """Same number of position changes inside the OOS span as the strategy, at random bars, each new level
    drawn from the strategy's own OOS levels (not the current one)."""
    rng = np.random.default_rng(seed)
    idx = np.nonzero(oos)[0]
    p = pos_oos
    n = int(np.count_nonzero(np.diff(p, prepend=0.0)))
    levels = np.unique(p)
    if len(levels) < 2:
        levels = np.array([0.0, levels[0]]) if levels[0] != 0 else np.array([0.0, 1.0])
    t = np.zeros(len(index))
    if n == 0:
        t[oos] = p[0] if len(p) else 0.0
        return t
    at = np.sort(rng.choice(idx, size=min(n, len(idx)), replace=False))
    cur = 0.0
    vals = np.zeros(len(at))
    for i in range(len(at)):
        opts = levels[levels != cur]
        cur = float(rng.choice(opts))
        vals[i] = cur
    s = np.full(len(index), np.nan)
    s[at] = vals
    s = np.array(pd.Series(s).ffill().fillna(0.0).values, dtype=float)
    s[~oos] = 0.0
    return s


# ------------------------------------------------------------------ break-even fee, significance

def breakeven_fee(fr, oos, target_fn=None):
    """Fee a side at which the OOS compounded net return is 0 (or a Sharpe target if target_fn given).
    r_net(f) = (r_net + fee) - f * |trade|. -> fee (fraction) or None if negative even at fee 0."""
    base = (fr["r_net"].values + fr["fee"].values)[oos]
    a = np.abs(fr["trade"].values)[oos]

    def val(f):
        r = base - f * a
        if target_fn is not None:
            return target_fn(r)
        return float(np.sum(np.log1p(np.maximum(r, -0.999999))))

    if val(0.0) <= 0:
        return None
    if a.sum() == 0 or val(0.05) > 0:
        return float("inf")
    lo, hi = 0.0, 0.05
    for _ in range(60):
        mid = (lo + hi) / 2
        if val(mid) > 0:
            lo = mid
        else:
            hi = mid
    return lo


def daily(r, index):
    return pd.Series(np.log1p(r), index=index).resample("1D").sum().values


def boot_sharpe_diff(rs, rb, index, draws=2000, block=20, seed=7):
    """Paired circular block bootstrap of daily log returns: p-value that Sharpe(s) - Sharpe(b) <= 0."""
    ds, db = daily(rs, index), daily(rb, index)

    def sh(x):
        sd = x.std(ddof=1)
        return x.mean() / sd * np.sqrt(365) if sd > 0 else 0.0
    obs = sh(ds) - sh(db)
    n = len(ds)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    diffs = np.empty(draws)
    for k in range(draws):
        st = rng.integers(0, n, nb)
        ii = (st[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        diffs[k] = sh(ds[ii]) - sh(db[ii])
    # centred bootstrap: H0 diff <= 0
    p = float(np.mean(diffs - obs >= obs)) if obs > 0 else 1.0
    return float(obs), p


def boot_sharpe_diff_z(rs, rb, index, draws=2000, block=20, seed=7):
    """Round 2 on: same paired block bootstrap; p from its standard error (normal approximation), one-sided."""
    from statistics import NormalDist
    ds, db = daily(rs, index), daily(rb, index)

    def sh(x):
        sd = x.std(ddof=1)
        return x.mean() / sd * np.sqrt(365) if sd > 0 else 0.0
    obs = sh(ds) - sh(db)
    n = len(ds)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    diffs = np.empty(draws)
    for k in range(draws):
        st = rng.integers(0, n, nb)
        ii = (st[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        diffs[k] = sh(ds[ii]) - sh(db[ii])
    se = float(diffs.std(ddof=1))
    p = 1.0 - NormalDist().cdf(obs / se) if se > 0 else (0.0 if obs > 0 else 1.0)
    return float(obs), float(p), se


def deflated_sharpe(r, n_trials, sr_bench=0.0):
    """Bailey & Lopez de Prado DSR on per-bar returns (annualised Sharpe in, probability out). The expected
    max Sharpe of n_trials null strategies replaces sr_bench when larger (trials assumed independent: crude)."""
    from math import erf, sqrt, log, e
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n < 10 or r.std() == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    sk = float(((r - r.mean()) ** 3).mean() / r.std() ** 3)
    ku = float(((r - r.mean()) ** 4).mean() / r.std() ** 4)
    # expected max of N standard normals (per-bar SR scale: sd of SR estimate ~ 1/sqrt(n))
    g = 0.5772156649
    N = max(int(n_trials), 1)
    if N > 1:
        from statistics import NormalDist
        nd = NormalDist()
        emax = (1 - g) * nd.inv_cdf(1 - 1.0 / N) + g * nd.inv_cdf(1 - 1.0 / (N * e))
    else:
        emax = 0.0
    sr0 = max(sr_bench / sqrt(BPY), emax / sqrt(n))
    z = (sr - sr0) * sqrt(n - 1) / sqrt(max(1 - sk * sr + (ku - 1) / 4.0 * sr * sr, 1e-12))
    return float(0.5 * (1 + erf(z / sqrt(2))))
