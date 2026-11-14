# -*- coding: utf-8 -*-
"""costs -- THE cost model. One model, shared by the Phase 1 backtester and (later) the
Phase 2 simulator, so an agent is trained against exactly the costs it is judged by.

Units: positions are fractions of max size (= current equity, 1x); every cost is a fraction of
equity charged on the bar it happens in.
  fee       = fee_side * |trade|                     taker fee, every side
  spread    = half_spread_bps / 1e4 * |trade|        crossing half the spread, every side
  slippage  = slippage_coef * vol * |trade|          vol = per-bar realised vol known at the DECISION
  funding   = position held at a settlement * rate   positive = paid (longs pay a positive rate)
Execution delay: a target decided at the close of bar t is filled at the open of bar t + delay_bars
(delay_bars >= 1). A position filled at the open of bar k is held over [open_k, open_k+1).
Funding settles on the 15m grid; the position that pays a settlement at time S is the one held
over the bar that ENDS at S (an order decided at S fills after it).
"""
from dataclasses import asdict, dataclass

import numpy as np

from . import store


@dataclass(frozen=True)
class CostModel:
    fee_side: float = 0.0010
    half_spread_bps: float = 0.5
    slippage_coef: float = 0.10
    slippage_vol_window: int = 96
    funding: bool = True
    delay_bars: int = 1

    def __post_init__(self):
        if int(self.delay_bars) < 1:
            raise ValueError("delay_bars must be >= 1: a decision at a bar's close cannot fill inside that bar")

    @classmethod
    def from_cfg(cls, c, fee_side=None):
        return cls(fee_side=float(c["fee_side"] if fee_side is None else fee_side),
                   half_spread_bps=float(c["half_spread_bps"]), slippage_coef=float(c["slippage_coef"]),
                   slippage_vol_window=int(c["slippage_vol_window"]), funding=bool(c["funding"]),
                   delay_bars=int(c["delay_bars"]))

    def as_dict(self):
        return asdict(self)

    # ---- the per-step formula (the simulator calls this one bar at a time)
    def step(self, trade, held, vol, funding_rate):
        """One bar: |trade| filled at its open, `held` carried over it, `vol` known at the decision,
        `funding_rate` settled at its end (0 if none). -> dict of costs (fractions of equity)."""
        a = np.abs(trade)
        return {"fee": self.fee_side * a,
                "spread": self.half_spread_bps * 1e-4 * a,
                "slippage": self.slippage_coef * vol * a,
                "funding": (held * funding_rate) if self.funding else held * 0.0}

    # ---- helpers that put market data on the bar grid
    def bar_vol(self, bars):
        """Per-bar realised vol (std of 1-bar log returns) known at each bar's close."""
        lr = np.log(bars["close"].astype(float)).diff()
        return lr.rolling(self.slippage_vol_window, min_periods=2).std().fillna(0.0).values

    @staticmethod
    def funding_on_bars(index, funding, interval_ms=900000):
        """-> array: the rate settled at the END of each bar (0 where none settles). A settlement
        that falls in an exchange gap is charged to the last bar before it (that position was held)."""
        out = np.zeros(len(index))
        if funding is None or not len(funding) or not len(index):
            return out
        s = np.asarray(funding["settle_ms"], dtype="int64")
        r = np.asarray(funding["rate"], dtype=float)
        close_ms = store.to_ms(index) + interval_ms
        k = np.searchsorted(close_ms, s, side="right") - 1          # last bar closing at or before S
        ok = (k >= 0) & (s <= close_ms[-1])
        np.add.at(out, k[ok], r[ok])
        return out


def from_cfg(cfg, fee_side=None):
    return CostModel.from_cfg(cfg["costs"], fee_side)


def fee_profiles(cfg):
    """The two fee levels every report shows: the owner's 0.10% and Binance taker 0.05%."""
    c = cfg["costs"]
    return {"fee_%.2f%%" % (c["fee_side"] * 100): from_cfg(cfg),
            "fee_%.2f%%" % (c["fee_side_alt"] * 100): from_cfg(cfg, c["fee_side_alt"])}
