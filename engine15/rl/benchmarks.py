# -*- coding: utf-8 -*-
"""benchmarks -- what any Phase 2 agent must beat, judged by the same costs and splits.

Rules were fixed in configs/rl/phase1.yaml before any result was seen:
  buy_hold : target +1.0 at every bar close.
  momentum : (frozen 11 Nov 2026, Phase 2 task 1, before any agent result existed) decided ONCE A DAY at
             the close of the bar ending 00:00 UTC, filled at the next bar's open: target = sign of the
             30-day (2,880-bar) log return, long/short (+1 / -1; 0 if exactly zero or not enough history),
             held until the next day's decision. Long/short because Phase 1's design was long/short.
             The retired Phase 1 rule (sign of the 96-bar return at EVERY bar close) traded ~1,800 times
             a year and was a straw man; it stays below as momentum_every_bar for the record only.
  random   : a new target drawn uniformly from {-1, 0, +1} every 96 bars, at the close of the bar
             ending at 00:00 UTC, held in between; one series per seed (>= 5 seeds).
None of them trains, so each is one target series over all history, sliced by the walk-forward.
"""
import numpy as np
import pandas as pd

from . import store


def buy_hold(index, target=1.0):
    return pd.Series(float(target), index=index)


def momentum_every_bar(close, window=96):
    """RETIRED Phase 1 rule (kept only so the old numbers can be re-made): sign of the
    `window`-bar log return at every bar close."""
    r = np.log(close.astype(float)).diff(window)
    return pd.Series(np.sign(r.fillna(0.0).values), index=close.index)


def momentum(close, lookback_days=30, long_short=True, interval_ms=900000):
    """THE momentum benchmark: decide once a day at the close of the bar ending 00:00 UTC
    (fill at the next open, done by the backtester's delay), target = sign of the trailing
    `lookback_days` return (bars counted: lookback_days * 96 on 15m), held until the next decision.
    long_short=False maps a negative sign to flat."""
    per_day = int(86400000 // interval_ms)
    w = int(lookback_days) * per_day
    r = np.log(close.astype(float)).diff(w).values
    close_ms = store.to_ms(close.index) + interval_ms
    decide = (close_ms % 86400000) == 0
    sig = np.sign(np.nan_to_num(r, nan=0.0))
    if not long_short:
        sig = np.maximum(sig, 0.0)
    tgt = np.full(len(close), np.nan)
    tgt[decide] = sig[decide]
    return pd.Series(tgt, index=close.index).ffill().fillna(0.0)


def random_agent(index, seed, hold_bars=96, choices=(-1.0, 0.0, 1.0), interval_ms=900000):
    close_ms = store.to_ms(index) + interval_ms
    redraw = (close_ms % (hold_bars * interval_ms)) == 0          # the bar ending on the schedule (00:00 UTC)
    rng = np.random.default_rng(seed)
    draws = rng.choice(np.asarray(choices, dtype=float), size=int(redraw.sum()))
    tgt = np.full(len(index), np.nan)
    tgt[redraw] = draws
    return pd.Series(tgt, index=index).ffill().fillna(0.0)


def all_targets(bars, bcfg):
    """-> {name: target series}; random seeds as random_s<seed>."""
    out = {"buy_hold": buy_hold(bars.index, bcfg["buy_hold"]["target"]),
           "momentum": momentum(bars["close"], bcfg["momentum"]["lookback_days"],
                                bcfg["momentum"].get("sides", "long_short") == "long_short")}
    rc = bcfg["random"]
    for s in rc["seeds"]:
        out["random_s%d" % s] = random_agent(bars.index, s, rc["hold_bars"], rc["choices"])
    return out
