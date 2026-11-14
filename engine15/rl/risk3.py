# -*- coding: utf-8 -*-
"""risk3 -- the Phase 3 risk manager: volatility-targeted sizing with a soft drawdown brake.

Phase 2's limits (5% daily stop, 30% kill switch) cut buy-and-hold from Sharpe 0.64 to 0.18: they sold
into every fall and missed the rebound. Phase 3 replaces them with sizing, not stopping:

  size      = min(max_position, vol_target / vol_est) x brake        (a multiplier on the requested target)
  vol_est   = max(rv_short, rv_long) x sqrt(35,040)                  annualised, closed bars only (rv_96, rv_672)
  brake     = 1.0 below dd_levels[0] drawdown, then the factors in dd_factors (soft: never 0)
  drawdown  = 1 - equity / max(equity marks over the last dd_window_bars)  -> a rolling peak, so the brake
              releases by itself after a long flat stretch instead of locking the book out for good
  executed  = requested x size, re-sized ONLY when it moves by more than rebalance_band (in position units)
              or the requested target itself changes; a requested 0 is always executed at once.

It works on a whole target series (decided at bar closes), so the same code sizes buy-and-hold, momentum
and every agent: the agent never sees the risk state (its observation has none), so its own decisions do not
depend on it. Equity is marked at each bar's close (open of the bar -> its close, after that bar's costs), so
no decision uses a later price. Every resize is logged with its reason; counts by reason are kept.
"""
from collections import deque
from dataclasses import asdict, dataclass, field

import numpy as np

BARS_PER_YEAR = 35040


@dataclass
class Risk3Config:
    enabled: bool = True
    vol_target: float = 0.50
    max_position: float = 1.0
    vol_short: str = "rv_96"
    vol_long: str = "rv_672"
    rebalance_band: float = 0.20
    dd_window_bars: int = 8640
    dd_levels: list = field(default_factory=lambda: [0.20, 0.30])
    dd_factors: list = field(default_factory=lambda: [0.75, 0.50])

    @classmethod
    def from_cfg(cls, c):
        c = dict(c or {})
        keys = set(cls.__dataclass_fields__)
        return cls(**dict((k, v) for k, v in c.items() if k in keys))

    def as_dict(self):
        return asdict(self)


def brake_factor(dd, cfg):
    f = 1.0
    for lvl, fac in zip(cfg.dd_levels, cfg.dd_factors):
        if dd >= lvl:
            f = fac
    return f


class Stepper:
    """The risk manager one bar at a time (used by apply() and by the forward paper mode, so both are the same code).
    step(t, req) is called at bar t's close with the agent's requested target; it needs bar t's own data and the
    previous bar's open-to-open return (open[t] is known by then), never anything after bar t's close."""

    def __init__(self, cfg, model, max_abs=None, log_events=True, dd_window_bars=None):
        self.cfg = cfg if isinstance(cfg, Risk3Config) else Risk3Config.from_cfg(cfg)
        self.model = model
        self.cap = float(self.cfg.max_position if max_abs is None else max_abs)
        self.log_events = log_events
        self.W = int(self.cfg.dd_window_bars if dd_window_bars is None else dd_window_bars)
        self.counts = {"vol_resize": 0, "brake_resize": 0, "brake_on_bars": 0}
        self.events = []
        self.eq = 1.0
        self.peak_q = deque()
        self.hist = deque([0.0] * (int(model.delay_bars) + 1), maxlen=int(model.delay_bars) + 1)   # exec[t-d .. t-1]
        self.prev_pos = 0.0
        self.pending = None                              # (pos, cost) of the last bar, to finish with its r_px
        self.cur = 0.0
        self.last_req = None

    def seed(self, exec_before, prev_pos=0.0):
        """Exec targets decided before the first step (oldest first) and the position held before them."""
        for x in exec_before:
            self.hist.append(float(x))
        self.cur = float(exec_before[-1]) if len(exec_before) else 0.0
        self.prev_pos = float(prev_pos)

    def step(self, t, req, close_ms, r_bar, r_px_prev, vol_dec, rate, v_short, v_long):
        """-> executed target for the decision at bar t's close."""
        cfg, model = self.cfg, self.model
        d = int(model.delay_bars)
        if self.pending is not None:                     # finish the previous bar's equity with its open-to-open return
            ppos, pc = self.pending
            self.eq *= (1.0 + ppos * r_px_prev - pc)
        pos = self.hist[-d]                              # exec decided at t - d, held over bar t
        trade = pos - self.prev_pos
        c1 = (model.fee_side + model.half_spread_bps * 1e-4 + model.slippage_coef * vol_dec) * abs(trade)
        fund = pos * rate if model.funding else 0.0
        mark = self.eq * (1.0 + pos * r_bar - c1 - fund)
        self.pending = (pos, c1 + fund)
        self.prev_pos = pos
        while self.peak_q and self.peak_q[-1][1] <= mark:
            self.peak_q.pop()
        self.peak_q.append((t, mark))
        while self.peak_q[0][0] <= t - self.W:
            self.peak_q.popleft()
        peak = self.peak_q[0][1]
        dd = 1.0 - mark / peak if peak > 0 else 0.0
        ann = np.sqrt(BARS_PER_YEAR)
        v = max(v_short if v_short == v_short else 0.0, v_long if v_long == v_long else 0.0) * ann
        cap = self.cap
        vsize = min(cap, cfg.vol_target / v) if v > 0 else cap
        bf = brake_factor(dd, cfg)
        if bf < 1.0:
            self.counts["brake_on_bars"] += 1
        size = vsize * bf
        want = req * size
        if abs(want) > cap:
            want = np.sign(want) * cap
        cur, last_req = self.cur, self.last_req
        if req == 0.0:
            new = 0.0
        elif last_req is None or req != last_req:
            new = want
        elif abs(want - cur) > cfg.rebalance_band:
            new = want
        else:
            new = cur
        if new != cur and req != 0.0:
            why = []
            if vsize < cap - 1e-12:
                why.append("vol %.0f%% a year > target %.0f%%: size %.2f" % (100 * v, 100 * cfg.vol_target, vsize))
            if bf < 1.0:
                why.append("drawdown %.1f%% from the %d-bar peak: brake x%.2f" % (100 * dd, self.W, bf))
            if not why:
                why.append("full size %.2f" % cap)
            kind = "brake_resize" if bf < 1.0 else "vol_resize"
            if req == last_req:
                self.counts[kind] += 1
            if self.log_events:
                self.events.append({"close_ms": int(close_ms), "rule": kind if req == last_req else "size_new_target",
                                    "requested": float(req), "allowed": float(new), "current": float(cur),
                                    "reason": "; ".join(why), "size": float(size), "drawdown": float(dd)})
        self.cur = new
        self.last_req = req
        self.hist.append(new)
        self.size = size
        return new


def apply(market, target, lo, hi, cfg, log_events=True, max_abs=None):
    """target: array over the full index (decided at each bar's close). -> dict(exec, events, counts, size).
    Bars outside [lo, hi) are copied unchanged (0 before the span normally)."""
    cfg = cfg if isinstance(cfg, Risk3Config) else Risk3Config.from_cfg(cfg)
    tgt = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    out = tgt.copy()
    if not cfg.enabled:
        return {"exec": out, "events": [], "counts": {}, "size": np.ones(len(tgt))}
    m = market
    cs, cl = m.col(cfg.vol_short), m.col(cfg.vol_long)
    rs = m.raw[:, cs].astype(float) if cs is not None else m.vol
    rl = m.raw[:, cl].astype(float) if cl is not None else m.vol
    d = int(m.model.delay_bars)
    st = Stepper(cfg, m.model, max_abs, log_events)
    st.seed([out[k] if k >= 0 else 0.0 for k in range(lo - d - 1, lo)], out[lo - d - 1] if lo - d - 1 >= 0 else 0.0)
    size_rec = np.ones(len(tgt))
    for t in range(lo, hi):
        out[t] = st.step(t, tgt[t], m.close_ms[t], m.r_bar[t], m.r_px[t - 1] if t >= 1 else 0.0,
                         m.vol[t - d] if t - d >= 0 else 0.0, m.rate[t], float(rs[t]), float(rl[t]))
        size_rec[t] = st.size
    return {"exec": out, "events": st.events, "counts": st.counts, "size": size_rec}
