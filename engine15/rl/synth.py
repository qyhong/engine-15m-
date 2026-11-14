# -*- coding: utf-8 -*-
"""synth -- synthetic 15m-like series with a planted, known edge, for the Phase 3 learnability check.

A series of 15m bars (24/7, UTC) whose open-to-open return over bar k is

    r_k = kappa x sigma_k x regime x s_{k-1}  +  sigma_k x eps_k
    s   = AR(1) signal with unit variance and a half-life of `half_life` bars (one day by default),
          visible to the agent at bar k-1's close as the feature column `planted`
    sigma_k = per-bar volatility with slow log-AR(1) regimes around vol_annual (fat tails: eps ~ t(4), unit var)
    regime = +1, or flips sign at random (mean `flip_days` apart) for the drifting-edge scenario

so the planted column predicts the NEXT bar's return with a per-bar information coefficient of about kappa,
exactly in the engine's timing (decide at the close, fill at the next open). kappa = 0 is the no-edge
control: the column is still there, but pure noise. Funding settles every 8 hours (mean 0.01%).

oracle(): the best simple rule that KNOWS the planted signal (hysteresis on `planted`, threshold picked on the
training part) shows what is attainable after costs.
"""
import numpy as np
import pandas as pd

from . import data as rdata


def make(n, seed, kappa, half_life=96, vol_annual=0.65, flip_days=None, start="2021-01-01", obs_noise=0.0):
    """-> (bars DataFrame, funding DataFrame, planted (n,) array, info dict)."""
    rng = np.random.default_rng(seed)
    phi = 0.5 ** (1.0 / half_life)
    s = np.empty(n)
    s[0] = rng.normal()
    e = rng.normal(size=n) * np.sqrt(1 - phi * phi)
    for k in range(1, n):
        s[k] = phi * s[k - 1] + e[k]
    base = vol_annual / np.sqrt(35040)
    lv = np.empty(n)
    lv[0] = 0.0
    pv = 0.5 ** (1.0 / 4000)
    ev = rng.normal(size=n) * 0.35 * np.sqrt(1 - pv * pv)
    for k in range(1, n):
        lv[k] = pv * lv[k - 1] + ev[k]
    sig = base * np.exp(lv - 0.5 * 0.35 ** 2)
    reg = np.ones(n)
    if flip_days:
        k, cur = 0, 1.0
        while k < n:
            L = max(96, int(rng.exponential(flip_days * 96)))
            reg[k:k + L] = cur
            cur = -cur
            k += L
    eps = rng.standard_t(4, size=n) / np.sqrt(2.0)
    mu = np.zeros(n)
    mu[1:] = kappa * sig[1:] * reg[:-1] * s[:-1]
    r = mu + sig * eps
    lo = np.log(30000.0) + np.concatenate([[0.0], np.cumsum(np.log1p(np.clip(r, -0.5, None)))])
    opn = np.exp(lo[:-1])
    nxt = np.exp(lo[1:])
    close = nxt                                            # close of bar k = open of bar k + 1
    wig = np.abs(rng.normal(size=n)) * sig * 0.5
    high = np.maximum(opn, close) * (1 + wig)
    low = np.minimum(opn, close) * (1 - wig)
    vol = np.exp(rng.normal(5.0, 0.3, n) + 30 * np.abs(r))
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC").as_unit("ms")
    bars = pd.DataFrame({"open": opn, "high": high, "low": low, "close": close, "volume": vol,
                         "quote_volume": vol * close, "trades": vol * 10, "taker_buy": vol * 0.5}, index=idx)
    times = pd.date_range(idx[0].floor("8h"), idx[-1] + pd.Timedelta("1h"), freq="8h", tz="UTC")
    raw = times.as_unit("ms").asi8.astype("int64") + rng.integers(0, 40, len(times))
    fund = pd.DataFrame({"rate": rng.normal(0.0001, 0.0001, len(times)), "settle_ms": rdata.settlement_ms(raw)},
                        index=pd.to_datetime(raw, unit="ms", utc=True))
    planted = s + obs_noise * rng.normal(size=n)
    return bars, fund, planted, {"kappa": kappa, "half_life": half_life, "vol_annual": vol_annual,
                                 "flip_days": flip_days, "regime": reg}


def oracle_targets(planted, h, sizes=1.0, regime=None):
    """Hysteresis on the planted signal: long above +h, short below -h, else keep; optional known regime."""
    x = planted * (1.0 if regime is None else regime)
    out = np.zeros(len(x))
    cur = 0.0
    for k, v in enumerate(x):
        if v > h:
            cur = sizes
        elif v < -h:
            cur = -sizes
        out[k] = cur
    return out
