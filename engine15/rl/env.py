# -*- coding: utf-8 -*-
"""env -- the Phase 2 trading environment (Gymnasium), built on Phase 1's features and cost model.

Timing (the engine's honest frame, identical to backtest.py):
  * A decision is taken at the CLOSE of a decision bar i (every `decision_every_bars` bars, the bar
    whose close is on the schedule, e.g. each UTC hour). The observation is the feature row of bar i,
    which uses closed bars only (features.py; tests/rl/test_env.py checks obs(t) ignores data after t).
  * The target is filled at the OPEN of bar i + delay (CostModel.delay_bars >= 1) and held until the
    next decision. Position at bar j = target in force at bar j - delay.
  * Each step realises the bars i+1 .. next decision bar: per bar, gross = pos x (open[j+1]/open[j] - 1)
    (the last bar of the series: close/open), costs = CostModel.step(trade, pos, vol[j - delay], rate[j]).
    Same formula, same arrays as backtest.run, so env P&L == backtest P&L for the same targets (tested).
  * reward = reward_scale x ( sum_j log(1 + net_j) - turnover_penalty x |target change| ).
  * The risk manager sees equity marked at each bar's CLOSE (open-to-close of that bar), never the next
    bar's open, so nothing it decides at bar j uses a price from after bar j.

Between the agent and execution: a minimum holding period (a change is refused until min_hold_bars
after the last change) and the risk manager (risk.py), whose equity rules are checked at every bar
close and can flatten the book between decisions. The executed target series is recorded so the
shared backtester can replay it.

Market holds the read-only arrays for the whole series once; several envs share it (lean on memory).
"""
import gymnasium as gym
import numpy as np

from . import store
from .costs import CostModel
from .risk import RiskManager


class Market:
    """Read-only per-bar arrays over the full series: prices, vol, funding, raw features (float32)."""

    def __init__(self, bars, funding, feats, model=None, interval_ms=900000):
        self.model = model or CostModel()
        self.index = bars.index
        self.n = len(bars)
        self.interval_ms = int(interval_ms)
        self.close_ms = store.to_ms(bars.index) + self.interval_ms
        o = bars["open"].values.astype(float)
        c = bars["close"].values.astype(float)
        nxt = np.append(o[1:], c[-1]) if len(o) else o
        self.r_px = nxt / o - 1.0                                    # exactly backtest.run's r_px
        self.r_bar = c / o - 1.0                                     # open -> close of the bar itself
        self.vol = self.model.bar_vol(bars)                          # known at each bar's close
        self.rate = self.model.funding_on_bars(bars.index, funding, interval_ms)
        self.columns = list(feats.columns)
        self.raw = np.ascontiguousarray(feats.values, dtype=np.float32)

    def with_model(self, model):
        """Same market, another cost model (e.g. the 0.05% fee). Arrays are shared, not copied."""
        m = object.__new__(Market)
        m.__dict__.update(self.__dict__)
        m.model = model
        if model.slippage_vol_window != self.model.slippage_vol_window:
            raise ValueError("vol window differs; build a new Market")
        return m

    def col(self, name):
        return self.columns.index(name) if name in self.columns else None

    def fit_norm(self, lo, hi):
        """mean / std of the raw features over bars [lo, hi) (a fold's TRAINING slice only)."""
        import warnings
        x = self.raw[lo:hi].astype(np.float64)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)              # an all-NaN column -> (0, 1) below
            mu = np.nanmean(x, axis=0)
            sd = np.nanstd(x, axis=0)
        mu = np.where(np.isfinite(mu), mu, 0.0)
        sd = np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
        return mu.astype(np.float32), sd.astype(np.float32)

    def decision_bars(self, lo, hi, every):
        """Indices i in [lo, hi) whose close lands on the decision schedule."""
        cm = self.close_ms[lo:hi]
        return np.nonzero((cm % (int(every) * self.interval_ms)) == 0)[0] + lo


class TradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, market, lo, hi, norm, ecfg, risk_cfg=None, episode_decisions=None, seed=0,
                 random_start_position=False, record=False, log_risk_events=False):
        super().__init__()
        self.m = market
        self.lo, self.hi = int(lo), int(hi)
        self.norm = norm                                             # (mu, sd) or a callable: bar index -> (mu, sd)
        self.k = int(ecfg.get("decision_every_bars", 4))
        self.min_hold = int(ecfg.get("min_hold_bars", 0))
        self.penalty = float(ecfg.get("turnover_penalty", 0.0))
        self.scale = float(ecfg.get("reward_scale", 1.0))
        self.clip = float(ecfg.get("obs_clip", 5.0))
        self.actions = np.asarray(ecfg.get("actions", [-1.0, 0.0, 1.0]), dtype=float)
        self.d = int(market.model.delay_bars)
        self.ep_len = episode_decisions
        self.rand_pos = bool(random_start_position)
        self.dec = market.decision_bars(self.lo, self.hi, self.k)
        if len(self.dec) < 2:
            raise ValueError("fewer than 2 decision bars in [%d, %d)" % (lo, hi))
        self.risk = RiskManager(risk_cfg, log_events=log_risk_events) if risk_cfg is not None else None
        rc = self.risk.cfg if self.risk else None
        self.vs = market.col(rc.vol_breaker_short) if rc else None
        self.vl = market.col(rc.vol_breaker_long) if rc else None
        self.record = record
        nf = market.raw.shape[1]
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(nf + 3,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(len(self.actions))
        self.rng = np.random.default_rng(seed)
        self.stats = {"min_hold_refusals": 0}
        if record:
            self.tgt_rec = np.full(market.n, np.nan)
            self.r_net = np.zeros(market.n)
            self.r_gross = np.zeros(market.n)
            self.cost = dict((c, np.zeros(market.n)) for c in ("fee", "spread", "slippage", "funding"))
            self.pos_rec = np.zeros(market.n)
        self._t = np.zeros(market.n, dtype=np.float32)                # executed target per bar (this episode)

    # ---- observation: features of the decision bar (closed bars only) + own state
    def _obs(self):
        i = self.dec[self.p]
        mu, sd = self.norm(i) if callable(self.norm) else self.norm
        x = (self.m.raw[i] - mu) / sd
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(x, -self.clip, self.clip, out=x)
        held = min(self.since, 384) / 384.0
        flag = 1.0 if (self.risk is not None and self.risk.restricting()) else 0.0
        return np.concatenate([x, np.array([self.cur, held, flag], dtype=np.float32)]).astype(np.float32)

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}
        if self.ep_len and len(self.dec) > self.ep_len + 1:
            self.p = int(self.rng.integers(0, len(self.dec) - self.ep_len))
        else:
            self.p = 0
        self.p0 = self.p
        if "position" in options:
            self.cur = float(options["position"])
        elif self.rand_pos:
            self.cur = float(self.rng.choice(self.actions))
        else:
            self.cur = 0.0
        self.since = int(options.get("since", self.min_hold))
        self.equity = float(options.get("equity", 1.0))
        i = self.dec[self.p]
        a0 = max(0, i - self.d)
        self._t[a0:i + 1] = self.cur                                  # what was held going in
        self.prev_pos = self.cur
        if self.record:
            self.tgt_rec[self.lo:i] = self.cur                         # bars before the first decision
        if self.risk is not None:
            self.risk.reset(self.equity, None)
        self.steps = 0
        return self._obs(), {}

    def step(self, action):
        m, d = self.m, self.d
        i = self.dec[self.p]
        last = self.p + 1 >= len(self.dec)
        nxt = self.dec[self.p + 1] if not last else min(i + self.k, self.hi - 1, m.n - 1)
        rec_end = nxt if not last else self.hi                        # the last decision holds to the slice end
        req = float(self.actions[int(action)])
        tgt = self.cur
        if req != self.cur:
            if self.since >= self.min_hold:
                tgt = req
            else:
                self.stats["min_hold_refusals"] += 1
        if self.risk is not None:
            vs = float(m.raw[i, self.vs]) if self.vs is not None else None
            vl = float(m.raw[i, self.vl]) if self.vl is not None else None
            tgt = self.risk.filter(tgt, self.cur, int(m.close_ms[i]), vs, vl)
        change = abs(tgt - self.cur)
        if tgt != self.cur:
            self.since = 0
        self.cur = tgt
        self._t[i:max(nxt, i + 1)] = tgt
        if self.record:
            self.tgt_rec[i:rec_end] = tgt
        logsum = 0.0
        model = m.model
        for j in range(i + 1, nxt + 1):
            if j >= m.n:
                break
            pos = float(self._t[j - d])
            trade = pos - self.prev_pos
            c = model.step(trade, pos, m.vol[j - d], m.rate[j])
            cost = c["fee"] + c["spread"] + c["slippage"] + c["funding"]
            g = pos * m.r_px[j]
            net = g - cost
            mark = self.equity * (1.0 + pos * m.r_bar[j] - cost)     # marked at bar j's close: no later price
            self.equity *= (1.0 + net)
            logsum += np.log1p(net) if net > -1.0 else -50.0
            self.prev_pos = pos
            self.since += 1
            if self.record:
                self.r_net[j], self.r_gross[j], self.pos_rec[j] = net, g, pos
                for key in ("fee", "spread", "slippage", "funding"):
                    self.cost[key][j] = c[key]
            if self.risk is not None:
                self.risk.on_bar(int(m.close_ms[j]), mark)
                if j < nxt and self.cur != 0.0 and self.risk.must_flatten():
                    self.risk.forced(int(m.close_ms[j]), self.cur)
                    self.cur = 0.0
                    self.since = 0
                    change += abs(float(self._t[j]))
                    self._t[j:nxt] = 0.0
                    if self.record:
                        self.tgt_rec[j:rec_end] = 0.0
        reward = self.scale * (logsum - self.penalty * change)
        self.p += 1
        self.steps += 1
        terminated = self.p >= len(self.dec) or self.equity <= 0.0
        truncated = bool(self.ep_len) and (self.steps >= self.ep_len) and not terminated
        if self.p >= len(self.dec):
            self.p = len(self.dec) - 1
        return self._obs(), float(reward), bool(terminated), bool(truncated), {}

    def state(self):
        return {"position": self.cur, "since": self.since, "equity": self.equity}


def run_policy(env, act_fn, p_start=None, p_end=None):
    """Drive `env` sequentially (no random start) with act_fn(obs) -> action index, over its decision
    bars. -> number of decisions taken. The env must have been built with record=True to read results."""
    obs, _ = env.reset(options={"position": 0.0})
    n = 0
    while True:
        obs, r, term, trunc, _ = env.step(act_fn(obs))
        n += 1
        if term or trunc:
            break
    return n


def frame_from_record(env, lo, hi):
    """A metrics-ready frame (r_net, r_gross, pos, costs) for bars [lo, hi) from a recording env."""
    import pandas as pd
    sl = slice(lo, hi)
    df = pd.DataFrame({"r_net": env.r_net[sl], "r_gross": env.r_gross[sl], "pos": env.pos_rec[sl],
                       "fee": env.cost["fee"][sl], "spread": env.cost["spread"][sl],
                       "slippage": env.cost["slippage"][sl], "funding": env.cost["funding"][sl]},
                      index=env.m.index[sl])
    return df
