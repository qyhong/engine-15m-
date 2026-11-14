# -*- coding: utf-8 -*-
"""Shared helpers for the RL module's tests. Planted data only; no network."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def make_bars(n=6000, seed=1, start="2022-01-01", drift=0.0):
    rng = np.random.RandomState(seed)
    close = 30000.0 * np.exp(np.cumsum(rng.normal(drift, 0.003, n)))
    opn = np.concatenate([[30000.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                         "close": close, "volume": vol, "quote_volume": vol * close, "trades": vol * 10,
                         "taker_buy": vol * rng.uniform(0.3, 0.7, n)},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC").as_unit("ms"))


def make_funding(index, seed=2, jitter=True):
    """8-hourly settlements over the bars' span, stamped a few ms late like Binance's."""
    from engine15.rl import data
    rng = np.random.RandomState(seed)
    t0 = index[0].floor("8h")
    times = pd.date_range(t0, index[-1] + pd.Timedelta("1h"), freq="8h", tz="UTC")
    raw = (times.as_unit("ms").asi8 + (rng.randint(0, 40, len(times)) if jitter else 0)).astype("int64")
    rates = rng.normal(0.0001, 0.0002, len(times))
    return pd.DataFrame({"rate": rates, "settle_ms": data.settlement_ms(raw)},
                        index=pd.to_datetime(raw, unit="ms", utc=True))


@pytest.fixture
def bars():
    return make_bars()


@pytest.fixture
def funding(bars):
    return make_funding(bars.index)
