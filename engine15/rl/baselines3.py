# -*- coding: utf-8 -*-
"""baselines3 -- the strategy loop's two best rules as Phase 3 baselines (owner's addendum, 11 Nov 2026).

  A  "H29 H30 1.5x/0x spot": daily 30-day momentum; 1.5x long in uptrends, flat in downtrends (entries wait for a
     15m pullback, as in the loop); long legs held as spot, so funding is paid only on exposure above 1x.
  B  "H29 H31 trail 4 ATR spot": vol-targeted momentum (60% a year, up to 2x), long only, with a 15m trailing exit at
     4 daily ATRs; spot long legs.

The rules are imported READ-ONLY from research/harness (round2.R2, core.features, core.Market): the code that
produced the loop's numbers, unchanged. Every input is point-in-time (closed bars, htf_on_15), so the targets
computed on the full history equal those computed on data cut at any bar (tests/rl/test_phase3_baselines.py).

HOLDOUT HYGIENE (owner): the loop chose these rules on data before 2025-11-11 and keeps 2025-11-11 .. 2026-11-11
sealed. Every Phase 3 number for A, B or anything built on them (residual agents, imitation warm starts, the
long-only scratch agent they are compared with) is computed on folds that end by 2025-11-11 only: the dev span.
"""
import os
import sys

import numpy as np
import pandas as pd

from ..config import ROOT

HOLDOUT_START = pd.Timestamp("2025-11-11", tz="UTC")


def _harness():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from research.harness import core, round2
    return core, round2


def targets(bars):
    """-> {"A": target, "B": target} decided at each bar's close (fill next open), on bars' index."""
    core, round2 = _harness()
    b = bars[["open", "high", "low", "close", "volume"]].astype(float)
    feats = core.features(b)
    ex = round2.extra_features(b, feats)
    r2 = round2.R2(b, feats, ex)
    return {"A": np.asarray(r2.h30(1.5, 0.0), dtype=float), "B": np.asarray(r2.h31(4.0), dtype=float)}


def spot_market(bars, fund):
    core, _ = _harness()
    return core.Market(bars[["open", "high", "low", "close", "volume"]].astype(float), fund)


def spot_frame(smkt, target, fee, spot=True):
    """The loop's backtester (bit for bit engine15.rl.backtest, plus spot funding): long part up to 1x is spot."""
    return smkt.frame(np.asarray(target, dtype=float), fee, spot)


def funded_multiplier(base):
    """Residual agents: an adjustment pays funding only where the baseline already holds >= 1x (spot below)."""
    return (np.asarray(base, dtype=float) >= 1.0).astype(np.float32)


def dev_cut_index(index):
    return int(index.searchsorted(HOLDOUT_START))
