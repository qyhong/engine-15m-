# -*- coding: utf-8 -*-
"""metrics -- performance numbers for a backtest frame.

Annualisation: 15-minute bars, 24/7 crypto, so ONE YEAR = 365 x 96 = 35,040 bars.
  sharpe   = mean(r) / std(r, ddof=1) * sqrt(35040)              (risk-free rate 0)
  sortino  = mean(r) / sqrt(mean(min(r, 0)^2)) * sqrt(35040)    (target 0, all bars in the denominator)
  max_dd   = largest fall of equity from its running peak, as a positive fraction
  cagr     = (end / start) ^ (1 / years) - 1, years = bars / 35040
  calmar   = cagr / max_dd
  turnover = sum |position change| per year (1.0 = one full-size side a year)
  holding  = mean length of a run of bars with the same non-zero position sign
  cost drag = sum(r_gross - r_net) per year (fees + spread + slippage + funding, fraction of equity)
"""
import numpy as np

BARS_PER_YEAR = 365 * 96


def sharpe(r, per_year=BARS_PER_YEAR):
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return 0.0
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(per_year)) if sd > 0 else 0.0


def sortino(r, per_year=BARS_PER_YEAR):
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return 0.0
    dd = np.sqrt(np.mean(np.minimum(r, 0.0) ** 2))
    return float(r.mean() / dd * np.sqrt(per_year)) if dd > 0 else 0.0


def max_drawdown(equity):
    e = np.asarray(equity, dtype=float)
    if not len(e):
        return 0.0
    peak = np.maximum.accumulate(e)
    return float(-(e / peak - 1.0).min())


def cagr(r, per_year=BARS_PER_YEAR):
    r = np.asarray(r, dtype=float)
    if not len(r):
        return 0.0
    growth = float(np.prod(1.0 + r))
    if growth <= 0:
        return -1.0
    return float(growth ** (per_year / len(r)) - 1.0)


def calmar(r, per_year=BARS_PER_YEAR):
    dd = max_drawdown(np.cumprod(1.0 + np.asarray(r, dtype=float)))
    return float(cagr(r, per_year) / dd) if dd > 0 else 0.0


def turnover(pos, per_year=BARS_PER_YEAR, prev=0.0):
    p = np.asarray(pos, dtype=float)
    if not len(p):
        return 0.0
    return float(np.abs(np.diff(p, prepend=prev)).sum() / (len(p) / per_year))


def holding_runs(pos):
    """-> lengths (bars) of runs with the same non-zero sign."""
    s = np.sign(np.asarray(pos, dtype=float))
    runs, cur, n = [], 0.0, 0
    for v in s:
        if v != 0 and v == cur:
            n += 1
        else:
            if cur != 0 and n:
                runs.append(n)
            cur, n = v, (1 if v != 0 else 0)
    if cur != 0 and n:
        runs.append(n)
    return runs


def summary(frame, per_year=BARS_PER_YEAR, prev_pos=0.0):
    """A backtest frame (or a slice of one) -> dict of metrics. `prev_pos` is the position held
    before the slice, so a slice's turnover counts only the trades inside it."""
    rn, rg = frame["r_net"].values, frame["r_gross"].values
    pos = frame["pos"].values
    years = len(rn) / per_year
    runs = holding_runs(pos)
    eq = np.cumprod(1.0 + rn)
    costs = dict(("%s_per_year" % k, float(frame[k].sum() / years) if years else 0.0)
                 for k in ("fee", "spread", "slippage", "funding"))
    out = {"bars": int(len(rn)), "years": round(years, 4),
           "total_return": float(eq[-1] - 1.0) if len(eq) else 0.0,
           "total_return_gross": float(np.prod(1.0 + rg) - 1.0) if len(rg) else 0.0,
           "cagr": cagr(rn, per_year), "sharpe": sharpe(rn, per_year), "sortino": sortino(rn, per_year),
           "sharpe_gross": sharpe(rg, per_year),
           "max_drawdown": max_drawdown(np.concatenate([[1.0], eq])), "calmar": calmar(rn, per_year),
           "turnover_per_year": turnover(pos, per_year, prev_pos),
           "trades": int(np.count_nonzero(np.diff(pos, prepend=prev_pos))),
           "avg_holding_bars": float(np.mean(runs)) if runs else 0.0,
           "avg_holding_hours": float(np.mean(runs)) / 4.0 if runs else 0.0,
           "exposure": float(np.mean(pos != 0)) if len(pos) else 0.0,
           "cost_drag_per_year": float((rg - rn).sum() / years) if years else 0.0}
    out.update(costs)
    return out
