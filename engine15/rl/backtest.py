# -*- coding: utf-8 -*-
"""backtest -- vectorised backtester for a target-position series.

Input: a target in [-1, 1] (fraction of max size; [-max_abs, max_abs] if given) decided at each bar's CLOSE. The engine's
honest frame: the fill is at the OPEN of bar t + delay (CostModel.delay_bars, >= 1), never
inside the decision bar. A missing target (NaN) means flat. Returns are open-to-open: the
position filled at open k earns open[k+1] / open[k] - 1 (the last bar: close / open).
Equity compounds (positions are fractions of current equity); costs come from costs.CostModel.

    res = run(bars, target, CostModel(), funding)
    res["frame"]   per bar: target, pos, trade, r_gross, fee, spread, slippage, funding, r_net,
                   equity_gross, equity_net
    res["trades"]  one row per position change (fill time, from, to, fill price, costs)
"""
import numpy as np
import pandas as pd

from .costs import CostModel

COST_COLS = ["fee", "spread", "slippage", "funding"]


def positions(target, delay, max_abs=1.0):
    """Target decided at bar t -> position held from the open of bar t + delay. |target| is capped at
    max_abs (1.0 everywhere except Phase 3's core-satellite overlay, which may hold up to 1.5x)."""
    t = np.clip(np.nan_to_num(np.asarray(target, dtype=float), nan=0.0), -max_abs, max_abs)
    pos = np.zeros_like(t)
    if delay < len(t):
        pos[delay:] = t[:len(t) - delay]
    return pos


def run(bars, target, model=None, funding=None, start_equity=1.0, interval_ms=900000, max_abs=1.0):
    model = model or CostModel()
    idx = bars.index
    tgt = pd.Series(target, index=idx) if not isinstance(target, pd.Series) else target.reindex(idx)
    tgt = tgt.astype(float)
    d = int(model.delay_bars)
    pos = positions(tgt.values, d, max_abs)
    trade = np.diff(pos, prepend=0.0)
    o = bars["open"].values.astype(float)
    c = bars["close"].values.astype(float)
    nxt = np.append(o[1:], c[-1]) if len(o) else o
    r_px = nxt / o - 1.0
    r_gross = pos * r_px
    vol = model.bar_vol(bars)
    vol_dec = np.zeros_like(vol)                                  # vol known at the decision bar (t = k - delay)
    if d < len(vol):
        vol_dec[d:] = vol[:len(vol) - d]
    rate = model.funding_on_bars(idx, funding, interval_ms)
    cst = model.step(trade, pos, vol_dec, rate)
    total = cst["fee"] + cst["spread"] + cst["slippage"] + cst["funding"]
    r_net = r_gross - total
    frame = pd.DataFrame({"target": tgt.values, "pos": pos, "trade": trade, "r_gross": r_gross,
                          "fee": cst["fee"], "spread": cst["spread"], "slippage": cst["slippage"],
                          "funding": cst["funding"], "r_net": r_net}, index=idx)
    frame["equity_gross"] = start_equity * np.cumprod(1.0 + r_gross)
    frame["equity_net"] = start_equity * np.cumprod(1.0 + r_net)
    ch = np.nonzero(trade != 0)[0]
    trades = pd.DataFrame({"fill_time": idx[ch], "from": pos[ch] - trade[ch], "to": pos[ch], "fill_price": o[ch],
                           "fee": cst["fee"][ch], "spread": cst["spread"][ch], "slippage": cst["slippage"][ch]})
    return {"frame": frame, "trades": trades, "model": model.as_dict()}
