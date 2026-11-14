# -*- coding: utf-8 -*-
"""indicators -- the estate's own definitions, vectorised.

Each function names the estate file it mirrors, so a reading here means what the same
word means in the AI Trading Bot's library:
  trend_score   src/strategy/trend_map.py   (trend-map-v1, owner 2026-10-12)
  regime_daily  scripts/regime.py           (six-regime taxonomy, 2026-09-20)
  stoch_rsi     src/indicators/stochrsi.py
  atr_wilder    src/indicators/volume.py
All of them read backwards only: a value at row i depends on rows <= i.
"""
import numpy as np
import pandas as pd

LENGTHS = (5, 10, 20, 50, 100, 200)
STACK_PAIRS = ((5, 10), (10, 20), (20, 50), (50, 100), (100, 200))
SLOPE_LENGTHS = (20, 50, 200)
SLOPE_LOOKBACK = 3
MIN_COMPONENTS = 14                 # of 28: fewer available = NO DATA
REGIMES = ("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN", "RANGE", "TRANSITION")


def sma(close, n):
    return close.rolling(n).mean()


def ema_seeded(close, n, min_factor=2):
    """EMA_N, alpha = 2/(N+1), seeded with the SMA of the first N closes; reported only
    with at least min_factor x N closed bars (trend_map.ema)."""
    v = close.values.astype(float)
    out = np.full(len(v), np.nan)
    if len(v) >= n:
        tail = np.concatenate([[v[:n].mean()], v[n:]])
        out[n - 1:] = pd.Series(tail).ewm(alpha=2.0 / (n + 1.0), adjust=False).mean().values
        out[:max(min_factor * n - 1, n - 1)] = np.nan
    return pd.Series(out, index=close.index)


def trend_score(close):
    """The trend-map score of ONE timeframe, for every bar: per family (EMA, SMA) the mean
    of position (close vs average), stack (shorter vs longer average) and slope (average now
    vs 3 bars earlier) components, each -1/0/+1; the timeframe's score is the mean of the
    two family scores; NaN (NO DATA) with fewer than 14 of the 28 components.
    -> Series in [-1, +1]. UP at or above +0.5, DOWN at or below -0.5, MIXED between."""
    fam_scores, total = [], 0
    for fn in (ema_seeded, sma):
        avg = dict((n, fn(close, n)) for n in LENGTHS)
        comps = [np.sign(close - avg[n]) for n in LENGTHS]
        comps += [np.sign(avg[a] - avg[b]) for a, b in STACK_PAIRS]
        comps += [np.sign(avg[n] - avg[n].shift(SLOPE_LOOKBACK)) for n in SLOPE_LENGTHS]
        m = pd.concat(comps, axis=1)
        fam_scores.append(m.mean(axis=1, skipna=True))
        total = total + m.notna().sum(axis=1)
    score = pd.concat(fam_scores, axis=1).mean(axis=1, skipna=True)
    return score.where(total >= MIN_COMPONENTS)


def label_of(score):
    if score is None or score != score:
        return "NO DATA"
    return "UP" if score >= 0.5 else "DOWN" if score <= -0.5 else "MIXED"


def true_range(df):
    pc = df["close"].shift(1)
    return pd.concat([(df["high"] - df["low"]).abs(), (df["high"] - pc).abs(), (df["low"] - pc).abs()],
                     axis=1).max(axis=1)


def atr_wilder(df, n=14):
    return true_range(df).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def atr_simple(df, n=14):
    """Simple mean of the last n true ranges (the library's Donchian / Burst specs, regime.py)."""
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.where(pc.notna()).rolling(n).mean()


def rsi(close, n=14):
    d = close.diff()
    gain = d.clip(lower=0).ewm(alpha=1.0 / n, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1.0 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, 1e-12))


def stoch_rsi_k(close, rsi_len=14, stoch_len=14, k=3):
    r = rsi(close, rsi_len)
    lo, hi = r.rolling(stoch_len).min(), r.rolling(stoch_len).max()
    raw = (100 * (r - lo) / (hi - lo).replace(0, 1e-12)).clip(0, 100)
    return raw.rolling(k).mean().clip(0, 100)


def regime_daily(d1):
    """scripts/regime.py's label on every completed daily bar (needs 210 closes):
    MOMENTUM (|5d return| >= 8% with ATR14 >= 1.15x its 50-bar mean) first, then TREND
    (efficiency ratio over 20 bars >= 0.35 with EMA20/50/200 stacked), then RANGE
    (ratio <= 0.20), else TRANSITION."""
    c = d1["close"]
    e20, e50, e200 = (ema_seeded(c, n, min_factor=1) for n in (20, 50, 200))
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum().replace(0, np.nan)
    atr = atr_simple(d1, 14)
    expanding = atr / atr.rolling(50).mean() >= 1.15
    ret5 = c / c.shift(5) - 1.0
    up, dn = (e20 > e50) & (e50 > e200), (e20 < e50) & (e50 < e200)
    lab = pd.Series("TRANSITION", index=c.index, dtype=object)
    lab[er.fillna(0) <= 0.20] = "RANGE"
    lab[(er >= 0.35) & up] = "TREND_UP"
    lab[(er >= 0.35) & dn] = "TREND_DOWN"
    lab[(ret5.abs() >= 0.08) & expanding & (ret5 > 0)] = "MOMENTUM_UP"
    lab[(ret5.abs() >= 0.08) & expanding & (ret5 < 0)] = "MOMENTUM_DOWN"
    lab[np.arange(len(c)) < 209] = None
    return lab


# ------------------------------------------------------------------ the library's working strategies
def _breakout_state(d1, long_sig, short_sig):
    """A daily position state for the library's two complete specs that share one stop and one
    exit: fixed stop 3 x ATR14 (simple) of the signal bar, exit when the close crosses the
    Donchian-40 midline. -> +1 / 0 / -1 as of each daily close."""
    hi, lo, c = d1["high"].values, d1["low"].values, d1["close"].values
    mid = ((d1["high"].rolling(40).max() + d1["low"].rolling(40).min()) / 2.0).shift(1).values
    atr = atr_simple(d1, 14).values
    ls, ss = long_sig.fillna(False).values, short_sig.fillna(False).values
    state = np.zeros(len(c))
    pos, stop = 0, 0.0
    for i in range(len(c)):
        if pos == 1 and (lo[i] <= stop or c[i] < mid[i]):
            pos = 0
        elif pos == -1 and (hi[i] >= stop or c[i] > mid[i]):
            pos = 0
        if pos == 0 and atr[i] == atr[i]:
            if ls[i]:
                pos, stop = 1, c[i] - 3.0 * atr[i]
            elif ss[i]:
                pos, stop = -1, c[i] + 3.0 * atr[i]
        state[i] = pos
    return pd.Series(state, index=d1.index)


def strat_donchian_c12(d1):
    """Library record eth-trend-1-c12-donchian: close beyond the prior 40-day high/low AND
    beyond the 200-day simple average."""
    c = d1["close"]
    up, dn, m = d1["high"].rolling(40).max().shift(1), d1["low"].rolling(40).min().shift(1), sma(c, 200)
    return _breakout_state(d1, (c > up) & (c > m), (c < dn) & (c < m))


def strat_burst2(d1):
    """Library record eth-burst2-b05-momentum-midline: a 10-day closing breakout with ATR14
    >= 1.15x its 50-bar mean and a 5-day move of 5%."""
    c = d1["close"]
    atr = atr_simple(d1, 14)
    hot = atr >= 1.15 * atr.rolling(50).mean().shift(1)
    r5 = c / c.shift(5) - 1.0
    return _breakout_state(d1, (c > c.rolling(10).max().shift(1)) & hot & (r5 >= 0.05),
                           (c < c.rolling(10).min().shift(1)) & hot & (r5 <= -0.05))


def strat_tsmom(d1):
    """Library record crypto-tsmom-voltarget-brake-only-r85's signal: long while the 30-day
    return is positive and the daily close is above its EMA50; otherwise out."""
    c = d1["close"]
    return ((c / c.shift(30) - 1.0 > 0) & (c > ema_seeded(c, 50))).astype(float)


def strat_sma120(d1):
    """The BTC trend engine of the estate's constitution: long above the 120-day simple
    average, cash below (+1 / -1 here: a reading, not a position)."""
    c = d1["close"]
    return np.sign(c - sma(c, 120)).fillna(0.0)


def strat_bh_regime(d1):
    """Library record bh-trend-accumulation's regime: weekly EMA20 against weekly EMA50."""
    w = d1["close"].resample("W-MON", label="left", closed="left").last().dropna()
    r = np.sign(ema_seeded(w, 20, min_factor=1) - ema_seeded(w, 50, min_factor=1)).fillna(0.0)
    r.index = r.index + pd.Timedelta(days=7)            # known once the week has closed
    out = r.reindex(d1.index + pd.Timedelta(days=1), method="ffill")
    out.index = d1.index
    return out.fillna(0.0)


def strat_core_zone(k4h, k1d):
    """Library record stochrsi-4h-1d-confluence-core, its mechanism sentence only: the 4H
    StochRSI %K at an extreme with the last closed 1D %K agreeing. +1 = the long (oversold)
    zone, -1 = the short (overbought) zone. NOT the engine's graded rule list."""
    return ((k4h < 20) & (k1d < 30)).astype(float) - ((k4h > 80) & (k1d > 70)).astype(float)
