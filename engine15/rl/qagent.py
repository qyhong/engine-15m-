# -*- coding: utf-8 -*-
"""qagent -- the Phase 3 agent: a cost-aware Q-learner on the 15m clock (paper only).

Why not PPO again: Phase 2's PPO could not even fit its training slice (train Sharpe -1.27), and on synthetic
data with a planted edge it does no better (see the learnability check). A 15m paper book has a special
structure: the market does not react to it, so the price path is the same whatever the agent does, and the only
state it changes is its own position. For every bar t, position held p and target a, the one-bar reward is known:

    R(t, p, a) = scale x ( k[t] x ( a x g[t] - cost_mult x c1[t] x |a - p| )  -  risk_aversion x a^2 x v[t] )
    g[t]  = r_px[t+1] - funding[t+1]        (decide at bar t's CLOSE, fill at t+1's OPEN, hold over bar t+1)
    c1[t] = fee + half-spread + slippage_coef x vol[t]      one side, the shared cost model's formula
    k[t]  = vol_ref / vol_est[t] (vol-scaled reward, matching the vol-targeted risk manager), v[t] = (k vol_est)^2

cost_mult = 2 charges a full round trip on every change; holding (a = p) is free. risk_aversion x a^2 x v is a
log-utility-style variance charge, so without an edge "flat" is worth more than a coin-flip position.

AFTERSTATE form (exact, not an approximation): p enters R only through the immediate cost, and the next state is
(x[t+1], a). So Q(x, p, a) = W(x, a) - scale x k x cost_mult x c1 x |a - p|, and the network learns only W from the
features (no position input):

    W(x[t], a) <- scale x (k a g - ra a^2 v)  +  gamma x max_{a' allowed at t+1} [ W(x[t+1], a') - scale k' cm c1' |a' - a| ]

in its n-step form: hold a for n bars (the sum of their discounted rewards), then the best move at t+n. The output
layer starts at zero, so every action starts equal and costs make holding the default until something is learned.

(double Q-learning: argmax with the online net, value with the target net; Huber loss; AdamW; hard target copies).
Every sampled bar updates all actions at once ("full counterfactual" updates: no exploration noise needed).
The cost structure is hard-wired, so the no-trade band is exact: a change happens only when W(a) - W(p) exceeds
the round-trip cost. Observation = the bar's point-in-time features, z-scored with the trailing window's
mean / sd and clipped at +-5. Masks restrict actions per bar (meta-labeling: {0, 0.5, 1} x the momentum side).

  Learner.train(raw, rd, steps, pool, weights)   gradient steps on bars from `pool` (recency weights optional)
  Learner.q(raw, rd, lo, hi)                     Q for bars [lo, hi) x every position x every action (numpy)
  Learner.save / load                            weights + target net + optimiser + normaliser (warm starts)
"""
import copy
import json

import numpy as np

from . import resources


def reward_arrays(market, qcfg=None):
    """-> dict of per-bar float32 arrays used by R and Q: g, c1, k, v (see the module docstring)."""
    qcfg = qcfg or {}
    m, mod = market, market.model
    n = m.n
    g = np.zeros(n)
    g[:-1] = m.r_px[1:] - (m.rate[1:] if mod.funding else 0.0)
    c1 = mod.fee_side + mod.half_spread_bps * 1e-4 + mod.slippage_coef * m.vol
    est = m.vol.copy()
    for name in ("rv_96", "rv_672"):
        c = m.col(name)
        if c is not None:
            x = m.raw[:, c].astype(float)
            est = np.fmax(est, np.where(np.isfinite(x), x, 0.0))
    pos = est[est > 0]
    est = np.where(est > 0, est, np.median(pos) if len(pos) else 1e-3)
    ref = float(qcfg.get("vol_ref_annual", 0.60)) / np.sqrt(35040)
    k = np.minimum(ref / est, float(qcfg.get("vol_scale_cap", 3.0))) if qcfg.get("vol_scale", False) else np.ones(n)
    v = (k * est) ** 2
    rpx = np.zeros(n)
    rpx[:-1] = m.r_px[1:]
    rate = np.zeros(n)
    if mod.funding:
        rate[:-1] = m.rate[1:]
    return {"g": g.astype(np.float32), "c1": c1.astype(np.float32), "k": k.astype(np.float32), "v": v.astype(np.float32),
            "rpx": rpx.astype(np.float32), "rate": rate.astype(np.float32)}


def funded_vector(actions, mode):
    """Exposure that pays funding for each action: perp = all of it; spot = only the part above 1x (and shorts);
    residual = the adjustment itself, times a per-bar multiplier (1 where the baseline already holds >= 1x)."""
    a = np.asarray(actions, dtype=np.float32)
    if mode == "spot":
        return np.maximum(a - 1.0, 0.0) + np.minimum(a, 0.0)
    return a


def recency_weights(pool, now_idx, half_life_bars, mix):
    """Sampling weights over `pool` (bar indices): (1 - mix) uniform + mix x exponential decay by age."""
    pool = np.asarray(pool)
    u = np.full(len(pool), 1.0 / len(pool))
    if not mix or not half_life_bars:
        return u
    age = (now_idx - pool).astype(float)
    e = np.exp(-np.log(2.0) * age / float(half_life_bars))
    e /= e.sum()
    return (1.0 - mix) * u + mix * e


def cost_matrix(actions):
    a = np.asarray(actions, dtype=np.float32)
    return np.abs(a[None, :] - a[:, None])                    # [p, a] = |a - p|


class Learner:
    def __init__(self, n_features, actions, qcfg, seed=0, mu=None, sd=None):
        torch = resources.torch_lean(qcfg.get("torch_threads", 2))
        self.torch = torch
        self.cfg = dict(qcfg)
        self.actions = np.asarray(actions, dtype=np.float32)
        self.A = len(self.actions)
        self.F = int(n_features)
        self.seed = int(seed)
        torch.manual_seed(self.seed)
        self.rng = np.random.default_rng(self.seed + 7919)
        self.net = self._mlp()
        self.tgt = self._mlp()
        self.tgt.load_state_dict(self.net.state_dict())
        for p in self.tgt.parameters():
            p.requires_grad_(False)
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=float(qcfg["learning_rate"]),
                                     weight_decay=float(qcfg.get("weight_decay", 0.0)))
        self.steps = 0
        self.mu = np.zeros(self.F, np.float32) if mu is None else np.asarray(mu, np.float32)
        self.sd = np.ones(self.F, np.float32) if sd is None else np.asarray(sd, np.float32)
        self.D = cost_matrix(self.actions)
        self.D_t = torch.tensor(self.D)
        self.act_t = torch.tensor(self.actions)
        self.meta = {}

    def _mlp(self):
        nn = self.torch.nn
        layers, d = [], self.F
        act = nn.ReLU if self.cfg.get("activation", "relu") == "relu" else nn.Tanh
        for h in self.cfg.get("net_arch", [32, 32]):
            layers += [nn.Linear(d, int(h)), act()]
            d = int(h)
        out = nn.Linear(d, self.A)
        nn.init.zeros_(out.weight)                    # every action starts equal: no made-up preference at step 0
        nn.init.zeros_(out.bias)
        layers.append(out)
        return nn.Sequential(*layers)

    # ---- inputs
    def set_norm(self, mu, sd):
        self.mu, self.sd = np.asarray(mu, np.float32), np.asarray(sd, np.float32)

    def _x(self, raw_rows):
        clip = float(self.cfg.get("obs_clip", 5.0))
        x = (np.asarray(raw_rows, dtype=np.float32) - self.mu) / self.sd
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(x, -clip, clip, out=x)
        return x

    # ---- learning
    def _targets(self, raw, rd, idx, masks):
        """n-step Bellman targets y (B, a) for bars idx: hold a for n bars (decisions t .. t+n-1), then the best
        allowed move at t+n, valued with the target network (double Q). Needs idx + n inside the data."""
        torch = self.torch
        c = self.cfg
        A, B = self.A, len(idx)
        n = int(c.get("n_step", 1))
        gamma = float(c["gamma"])
        scale, cm, ra = float(c["reward_scale"]), float(c["cost_mult"]), float(c.get("risk_aversion", 0.0))
        a = self.act_t.view(1, A)
        mode = c.get("funding_mode", "perp")
        F = torch.tensor(funded_vector(self.actions, mode)).view(1, A)
        r = torch.zeros(B, A)
        for j in range(n):
            ij = idx + j
            col = lambda key: torch.from_numpy(rd[key][ij]).view(B, 1)
            if mode == "perp":
                ret = a * col("g")
            elif mode == "spot":
                ret = a * col("rpx") - F * col("rate")
            else:                                       # residual: funding on the adjustment where the base is >= 1x
                ret = a * col("rpx") - F * col("rate") * col("fmult")
            r = r + (gamma ** j) * scale * (col("k") * ret - ra * a * a * col("v"))
        i1 = idx + n
        x1 = torch.from_numpy(self._x(raw[i1]))
        k1 = torch.from_numpy(rd["k"][i1]).view(B, 1, 1)
        c11 = torch.from_numpy(rd["c1"][i1]).view(B, 1, 1)
        cost1 = scale * cm * k1 * c11 * self.D_t.view(1, A, A)                                    # (B, a, a')
        w1o = self.net(x1).view(B, 1, A) - cost1
        w1t = self.tgt(x1).view(B, 1, A) - cost1
        if masks is not None:
            mk = torch.from_numpy(masks[i1]).view(B, 1, A).expand(B, A, A)
            w1o = w1o.masked_fill(~mk, -1e9)
        best = w1o.argmax(dim=2, keepdim=True)
        v1 = w1t.gather(2, best).squeeze(2)                                                       # (B, a)
        return r + (gamma ** n) * v1

    def _loss(self, w0, y, idx, masks):
        torch = self.torch
        l = torch.nn.functional.smooth_l1_loss(w0, y, beta=float(self.cfg.get("huber_beta", 1.0)), reduction="none")
        if masks is None:
            return l.mean()
        mk0 = torch.from_numpy(masks[idx]).float()
        return (l * mk0).sum() / mk0.sum().clamp(min=1.0)

    def train(self, raw, rd, pool, n_steps, weights=None, masks=None):
        """n_steps gradient steps on bars drawn from `pool` (each needs pool + 1 inside the data)."""
        torch = self.torch
        c = self.cfg
        B = int(c["batch_size"])
        every = int(c.get("target_every", 250))
        noise = float(c.get("input_noise", 0.0))
        pool = np.asarray(pool)
        p = None if weights is None else np.asarray(weights, dtype=float)
        loss_sum = 0.0
        for _ in range(int(n_steps)):
            idx = self.rng.choice(pool, size=B, p=p)
            with torch.no_grad():
                y = self._targets(raw, rd, idx, masks)
            x0 = torch.from_numpy(self._x(raw[idx]))
            if noise > 0:
                x0 = x0 + noise * torch.randn_like(x0)
            loss = self._loss(self.net(x0), y, idx, masks)
            self.opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), float(c.get("max_grad_norm", 1.0)))
            self.opt.step()
            self.steps += 1
            loss_sum += float(loss.item())
            if self.steps % every == 0:
                self.tgt.load_state_dict(self.net.state_dict())
        return loss_sum / max(1, int(n_steps))

    def bc(self, raw, rd, pool, target_idx, prev_idx, n_steps, tau=0.3):
        """Behaviour cloning (imitation warm start): cross-entropy so that the greedy choice
        argmax_a [W(x_t, a) - cost(prev_t -> a)] reproduces the baseline's target index at t."""
        torch = self.torch
        c = self.cfg
        B = int(c["batch_size"])
        scale, cm = float(c["reward_scale"]), float(c["cost_mult"])
        pool = np.asarray(pool)
        tot = 0.0
        for _ in range(int(n_steps)):
            idx = self.rng.choice(pool, size=B)
            x = torch.from_numpy(self._x(raw[idx]))
            cost = (scale * cm * torch.from_numpy(rd["k"][idx] * rd["c1"][idx]).view(B, 1)
                    * self.D_t[torch.from_numpy(prev_idx[idx].astype(np.int64))])
            logits = (self.net(x) - cost) / float(tau)
            loss = torch.nn.functional.cross_entropy(logits, torch.from_numpy(target_idx[idx].astype(np.int64)))
            self.opt.zero_grad(set_to_none=True)
            loss.backward()
            self.opt.step()
            tot += float(loss.item())
        self.tgt.load_state_dict(self.net.state_dict())
        return tot / max(1, int(n_steps))

    def eval_loss(self, raw, rd, idx, masks=None, chunk=4096):
        """Mean Bellman (Huber) loss over bars idx, no gradient: the validation loss."""
        torch = self.torch
        tot, n = 0.0, 0
        with torch.no_grad():
            for s in range(0, len(idx), chunk):
                ii = np.asarray(idx[s:s + chunk])
                y = self._targets(raw, rd, ii, masks)
                w0 = self.net(torch.from_numpy(self._x(raw[ii])))
                tot += float(self._loss(w0, y, ii, masks)) * len(ii)
                n += len(ii)
        return tot / max(n, 1)

    # ---- inference (numpy)
    def weights_np(self):
        lin = [m for m in self.net if hasattr(m, "weight")]
        return ([m.weight.detach().cpu().numpy().copy() for m in lin], [m.bias.detach().cpu().numpy().copy() for m in lin])

    def w(self, raw_rows):
        return w_numpy(self.weights_np(), raw_rows, self.mu, self.sd, self.cfg)

    def q(self, raw, rd, lo, hi):
        """Q (hi-lo, A positions, A actions) = W(x, a) - scale x cost_mult x k x c1 x |a - p|."""
        return q_from_w(self.w(raw[lo:hi]), rd["k"][lo:hi], rd["c1"][lo:hi], self.D, self.cfg)

    # ---- state
    def state(self):
        return {"net": copy.deepcopy(self.net.state_dict()), "tgt": copy.deepcopy(self.tgt.state_dict()),
                "opt": copy.deepcopy(self.opt.state_dict()), "steps": self.steps,
                "mu": self.mu.copy(), "sd": self.sd.copy(), "rng": copy.deepcopy(self.rng.bit_generator.state)}

    def load_state(self, st):
        self.net.load_state_dict(st["net"])
        self.tgt.load_state_dict(st["tgt"])
        self.opt.load_state_dict(st["opt"])
        self.steps = int(st["steps"])
        self.mu, self.sd = np.asarray(st["mu"], np.float32), np.asarray(st["sd"], np.float32)
        if "rng" in st:
            self.rng.bit_generator.state = st["rng"]

    def save(self, path, meta=None):
        """One .pt file: weights, target net, optimiser, normaliser, meta (warm-startable, tens of KB)."""
        st = self.state()
        st["meta"] = json.dumps(dict(meta or {}, actions=self.actions.tolist(), F=self.F, cfg=self.cfg), default=str)
        st["rng"] = json.dumps(st["rng"])
        tmp = str(path) + ".tmp"
        self.torch.save(st, tmp)
        import os
        os.replace(tmp, path)

    @classmethod
    def load(cls, path, qcfg=None):
        torch = resources.torch_lean((qcfg or {}).get("torch_threads", 2))
        st = torch.load(path, weights_only=False)
        meta = json.loads(st["meta"])
        lr = cls(meta["F"], meta["actions"], qcfg or meta["cfg"])
        st["rng"] = json.loads(st["rng"])
        lr.load_state(st)
        lr.meta = meta
        return lr


def w_numpy(weights, raw_rows, mu, sd, cfg, chunk=50000):
    """W values (n, A) from numpy weights; the same normalisation as Learner._x."""
    Ws, bs = weights
    clip = float(cfg.get("obs_clip", 5.0))
    relu = cfg.get("activation", "relu") == "relu"
    raw_rows = np.asarray(raw_rows, dtype=np.float32)
    n = raw_rows.shape[0]
    out = np.empty((n, Ws[-1].shape[0]), dtype=np.float32)
    for s in range(0, n, chunk):
        h = (raw_rows[s:s + chunk] - mu) / sd
        h = np.nan_to_num(h, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(h, -clip, clip, out=h)
        for W, b in zip(Ws[:-1], bs[:-1]):
            h = h @ W.T + b
            h = np.maximum(h, 0.0) if relu else np.tanh(h)
        out[s:s + h.shape[0]] = h @ Ws[-1].T + bs[-1]
    return out


def q_from_w(W, k, c1, D, cfg):
    scale, cm = float(cfg["reward_scale"]), float(cfg["cost_mult"])
    cost = (scale * cm * np.asarray(k, np.float32) * np.asarray(c1, np.float32))[:, None, None] * D[None, :, :]
    return (W[:, None, :] - cost).astype(np.float32)
