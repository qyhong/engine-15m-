# -*- coding: utf-8 -*-
"""agent -- the PPO agent (Stable-Baselines3) and a tiny numpy copy of its policy.

  make_ppo(vec_env, acfg, seed)   PPO("MlpPolicy"), small: two layers of 64 (pi and vf), CPU, 2 threads
  NumpyPolicy.from_sb3(model)     the actor's weights in numpy: deterministic action = argmax of logits.
                                  Used for validation and out-of-sample evaluation (fast, no torch), and
                                  saved as a small .npz (weights + the fold's feature normaliser + meta).
  MemoryGuard                     SB3 callback: stops training cleanly when free memory < floor
Paper only: an agent here only ever produces target positions for the simulator.
"""
import json

import numpy as np

from . import resources


def make_ppo(vec_env, acfg, seed):
    resources.torch_lean(acfg.get("torch_threads", 2))
    import torch
    from stable_baselines3 import PPO
    arch = list(acfg.get("net_arch", [64, 64]))
    return PPO("MlpPolicy", vec_env, learning_rate=float(acfg["learning_rate"]), n_steps=int(acfg["n_steps"]),
               batch_size=int(acfg["batch_size"]), n_epochs=int(acfg["n_epochs"]), gamma=float(acfg["gamma"]),
               gae_lambda=float(acfg["gae_lambda"]), clip_range=float(acfg["clip_range"]),
               ent_coef=float(acfg["ent_coef"]), vf_coef=float(acfg["vf_coef"]),
               max_grad_norm=float(acfg["max_grad_norm"]), seed=int(seed), device="cpu", verbose=0,
               policy_kwargs={"net_arch": {"pi": arch, "vf": arch}, "activation_fn": torch.nn.Tanh})


class NumpyPolicy:
    """Deterministic actor: tanh MLP -> logits -> argmax. Weights copied from an SB3 PPO policy."""

    def __init__(self, Ws, bs, mu, sd, meta=None):
        self.Ws = [np.asarray(w, dtype=np.float32) for w in Ws]
        self.bs = [np.asarray(b, dtype=np.float32) for b in bs]
        self.mu = np.asarray(mu, dtype=np.float32)
        self.sd = np.asarray(sd, dtype=np.float32)
        self.meta = dict(meta or {})

    @classmethod
    def from_sb3(cls, model, mu, sd, meta=None):
        import torch
        pol = model.policy
        lin = [m for m in pol.mlp_extractor.policy_net if isinstance(m, torch.nn.Linear)] + [pol.action_net]
        Ws = [m.weight.detach().cpu().numpy().copy() for m in lin]
        bs = [m.bias.detach().cpu().numpy().copy() for m in lin]
        return cls(Ws, bs, mu, sd, meta)

    def logits(self, obs):
        h = np.asarray(obs, dtype=np.float32)
        for W, b in zip(self.Ws[:-1], self.bs[:-1]):
            h = np.tanh(h @ W.T + b)
        return h @ self.Ws[-1].T + self.bs[-1]

    def act(self, obs):
        return int(np.argmax(self.logits(obs)))

    def save(self, path):
        arrs = {"mu": self.mu, "sd": self.sd, "meta": np.array(json.dumps(self.meta, default=str))}
        for i, (W, b) in enumerate(zip(self.Ws, self.bs)):
            arrs["W%d" % i] = W
            arrs["b%d" % i] = b
        np.savez_compressed(path, **arrs)

    @classmethod
    def load(cls, path):
        z = np.load(path, allow_pickle=False)
        n = sum(1 for k in z.files if k.startswith("W"))
        return cls([z["W%d" % i] for i in range(n)], [z["b%d" % i] for i in range(n)], z["mu"], z["sd"],
                   json.loads(str(z["meta"])))


def memory_guard(floor_mb, every=512):
    from stable_baselines3.common.callbacks import BaseCallback

    class MemoryGuard(BaseCallback):
        def __init__(self):
            super().__init__()
            self.tripped = None

        def _on_step(self):
            if self.n_calls % every == 0:
                f = resources.free_mb()
                if f is not None and f < floor_mb:
                    self.tripped = f
                    return False
            return True

    return MemoryGuard()
