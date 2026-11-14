# -*- coding: utf-8 -*-
"""labels -- how every call is GRADED: the triple barrier.

A call made at the close of bar t would be filled at the OPEN of bar t+1. Two barriers sit
one unit above and one unit below that fill, a unit being barrier_atr x ATR14(1h) as read at
bar t. Looking at bars t+1 .. t+horizon:
  UP       the upper barrier is touched first  -> a LONG from here was rewarding
  DOWN     the lower barrier is touched first  -> a SHORT from here was rewarding
  NEITHER  none is touched inside the horizon, or both inside one bar (order unknown)
The grade is KNOWN at bar t + res (the bar of the first touch, or the horizon's last bar);
nothing may learn from it earlier.
"""
import numpy as np

NEITHER, UP, DOWN, UNKNOWN = 0, 1, 2, -1


def triple_barrier(opn, high, low, unit, horizon):
    """arrays -> (y, res): y in {0 NEITHER, 1 UP, 2 DOWN, -1 not yet known};
    res = sessions until the grade is known (0 where unknown)."""
    n = len(opn)
    ref = np.full(n, np.nan)
    ref[:-1] = opn[1:]
    up, dn = ref + unit, ref - unit
    big = horizon + 1
    up_k = np.full(n, big, dtype=np.int32)
    dn_k = np.full(n, big, dtype=np.int32)
    for k in range(1, horizon + 1):
        hk = np.full(n, np.nan)
        lk = np.full(n, np.nan)
        hk[:n - k] = high[k:]
        lk[:n - k] = low[k:]
        up_k[(up_k == big) & (hk >= up)] = k
        dn_k[(dn_k == big) & (lk <= dn)] = k
    first = np.minimum(up_k, dn_k)
    y = np.full(n, NEITHER, dtype=np.int8)
    y[up_k < dn_k] = UP
    y[dn_k < up_k] = DOWN
    res = np.where(first == big, horizon, first).astype(np.int32)
    unknown = (np.arange(n) + res > n - 1) | ~np.isfinite(up) | ~(unit > 0)
    y[unknown] = UNKNOWN
    res[unknown] = 0
    return y, res
