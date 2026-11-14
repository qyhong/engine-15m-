# -*- coding: utf-8 -*-
"""env3 -- a Gymnasium env on Phase 3's reward and observations, used ONLY to give Phase 2's algorithm (PPO)
the same learnability check as the Phase 3 Q agent: same 15m clock, same features, same reward

    R(t, p, a) = scale x ( k[t] x (a x g[t] - cost_mult x c1[t] x |a - p|) - risk_aversion x a^2 x v[t] )

(qagent.reward_arrays), same action set (target sizes, 'hold' = keep p, free), same minimum hold.
Episodes: `episode_bars` consecutive bars from a random start inside [lo, hi - 1)."""
import gymnasium as gym
import numpy as np


class Env3(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, raw, rd, lo, hi, mu, sd, actions, qcfg, min_hold=0, episode_bars=2048, seed=0, clip=5.0):
        super().__init__()
        self.raw, self.rd = raw, rd
        self.lo, self.hi = int(lo), int(hi) - 1
        self.mu, self.sd = np.asarray(mu, np.float32), np.asarray(sd, np.float32)
        self.acts = np.asarray(actions, dtype=np.float32)
        self.A = len(self.acts)
        self.c = qcfg
        self.min_hold = int(min_hold)
        self.L = int(episode_bars)
        self.clip = clip
        self.rng = np.random.default_rng(seed)
        F = raw.shape[1]
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(F + self.A,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(self.A)
        self.zero = int(np.argmin(np.abs(self.acts)))

    def _obs(self):
        x = (self.raw[self.t] - self.mu) / self.sd
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(x, -self.clip, self.clip, out=x)
        oh = np.zeros(self.A, np.float32)
        oh[self.ip] = 1.0
        return np.concatenate([x, oh]).astype(np.float32)

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.t = int(self.rng.integers(self.lo, max(self.lo + 1, self.hi - self.L)))
        self.ip = int(self.rng.integers(0, self.A))
        self.since = self.min_hold
        self.n = 0
        return self._obs(), {}

    def step(self, action):
        a = int(action)
        if a != self.ip and self.since < self.min_hold:
            a = self.ip
        c, rd, t = self.c, self.rd, self.t
        p, av = self.acts[self.ip], self.acts[a]
        r = float(c["reward_scale"]) * (rd["k"][t] * (av * rd["g"][t] - float(c["cost_mult"]) * rd["c1"][t] * abs(av - p))
                                        - float(c.get("risk_aversion", 0.0)) * av * av * rd["v"][t])
        self.since = 0 if a != self.ip else self.since + 1
        self.ip = a
        self.t += 1
        self.n += 1
        term = self.t >= self.hi
        trunc = (self.n >= self.L) and not term
        if term:
            self.t = self.hi - 1
        return self._obs(), float(r), bool(term), bool(trunc), {}


def logits_all(pol, raw_rows, A, clip=5.0):
    """NumpyPolicy logits for every bar x every position (one-hot), shaped like Q: (n, A, A)."""
    x = (np.asarray(raw_rows, np.float32) - pol.mu) / pol.sd
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    np.clip(x, -clip, clip, out=x)
    n, F = x.shape
    eye = np.eye(A, dtype=np.float32)
    h = np.concatenate([np.repeat(x[:, None, :], A, axis=1), np.broadcast_to(eye, (n, A, A))], axis=2).reshape(n * A, F + A)
    return pol.logits(h).reshape(n, A, A).astype(np.float32)
