# -*- coding: utf-8 -*-
"""Phase 6: the shaped rewards (training only) do what they claim; the literal 'net - beta x reference' cannot change a
decision; no training row reaches past its fold; the 'do no harm' modes. Planted data only."""
import numpy as np

from engine15.rl import config, learn6, phase5, qagent
from test_phase4 import _cfg4, _geo, _mem_asset


def _targets(kind, value, A, idx, seed=3):
    c = _cfg4()
    acts = c["actions"]
    learn6.add_reference(A)
    L = learn6.Learner6(len(A.columns), acts, c["qagent"], seed, None, None, kind, value)
    raw = np.nan_to_num(A.X).astype(np.float32)
    return L._targets(raw, A.rd, idx, None).numpy(), c


def test_zero_shaping_is_the_phase4_learner_exactly():
    A, _, _ = _mem_asset("A", 96 * 40, 41, 0.02)
    idx = np.arange(3000, 3256)
    y0, c = _targets("missed", 0.0, A, idx)
    L = qagent.Learner(len(A.columns), c["actions"], c["qagent"], 3)
    y1 = L._targets(np.nan_to_num(A.X).astype(np.float32), A.rd, idx, None).numpy()
    assert np.allclose(y0, y1, atol=1e-6)


def test_shaping_charges_only_the_idle_part_of_the_book():
    A, _, _ = _mem_asset("A", 96 * 40, 42, 0.02)
    idx = np.arange(3000, 3256)
    acts = np.asarray(_cfg4()["actions"])
    full = np.abs(acts) == 1.0
    half = np.abs(acts) == 0.5
    flat = acts == 0.0
    y0, c = _targets("flat", 0.0, A, idx)
    q = c["qagent"]
    n, gamma, scale = int(q["n_step"]), float(q["gamma"]), float(q["reward_scale"])
    for kind, val in (("flat", 0.5), ("missed", 1.0)):
        y, _ = _targets(kind, val, A, idx)
        d = y - y0
        assert np.allclose(d[:, full], 0.0, atol=1e-6)                     # a full position is never charged
        exp = np.zeros(len(idx))
        for j in range(n):
            k, g, c1, ref = (A.rd[x][idx + j].astype(float) for x in ("k", "g", "c1", "ref"))
            pen = val * 2.0 / 96.0 * c1 if kind == "flat" else val * ref * g
            exp += (gamma ** j) * scale * k * pen
        assert np.allclose(d[:, flat][:, 0], -exp, rtol=1e-3, atol=1e-5)
        assert np.allclose(d[:, half], -0.5 * exp[:, None], rtol=1e-3, atol=1e-5)
    # flat-time charge: flat is always worse than before; missed: worse exactly when the reference earned
    y, _ = _targets("flat", 0.5, A, idx)
    assert (y[:, flat] < y0[:, flat]).all()


def test_literal_reference_return_shift_changes_no_decision():
    """'net - beta x reference return' subtracts the same amount from every action: every W(a) - W(p) is unchanged."""
    rng = np.random.default_rng(0)
    W = rng.standard_normal((500, 5)).astype(np.float32)
    shift = rng.standard_normal((500, 1)).astype(np.float32) * 3.0
    acts = np.asarray(config.load_phase4()["actions"], float)
    k = np.full(500, 1.0, np.float32)
    c1 = np.full(500, 0.0012, np.float32)
    qc = config.load_phase4()["qagent"]
    from engine15.rl import policy3
    Q1 = qagent.q_from_w(W, k, c1, qagent.cost_matrix(acts), qc)
    Q2 = qagent.q_from_w(W - shift, k, c1, qagent.cost_matrix(acts), qc)
    a1, _ = policy3.decide(Q1, acts, 2, 4)
    a2, _ = policy3.decide(Q2, acts, 2, 4)
    assert np.array_equal(a1, a2)


def test_q_fold6_never_trains_past_the_fold_and_records_its_choice():
    c = _cfg4()
    A1, _, _ = _mem_asset("A1", 96 * 70, 31, 0.02)
    A2, _, _ = _mem_asset("A2", 96 * 70, 32, 0.02)
    cols = A1.cols(A1.columns)
    geo = {"A1": _geo(A1), "A2": _geo(A2)}
    sh = {"kind": "missed", "values": [0.25, 1.0]}
    W1, r1 = learn6.q_fold6([A1, A2], ["A1"], cols, geo, c["q"], c["qagent"], c["actions"], 4, 7, sh)
    assert r1["chosen"]["shaping_value"] in (0.25, 1.0) and set(r1["grid"]) == {"0.25", "1.0"}
    for A in (A1, A2):
        lo = geo[A.name]["te_lo"]
        A.X[lo:] = np.random.default_rng(5).standard_normal(A.X[lo:].shape).astype(np.float32)
        for k in ("g", "rpx", "rate", "k", "c1", "v", "ref"):
            A.rd[k][lo:] = A.rd[k][lo:][::-1] * 3.0
    W2, r2 = learn6.q_fold6([A1, A2], ["A1"], cols, geo, c["q"], c["qagent"], c["actions"], 4, 7, sh)
    assert np.allclose(np.asarray(r1["coef"]), np.asarray(r2["coef"]))
    assert r1["chosen"] == r2["chosen"]


def test_fallback_modes(tmp_path):
    """'rule' -> flat values, 'none' -> the model's own, 'trend' -> the momentum reference position."""
    import json
    import os
    A, _, _ = _mem_asset("A", 96 * 40, 43, 0.0)
    learn6.add_reference(A)
    A.at = lambda ts: int(np.searchsorted(A.t, int(ts.value // 10**6)))
    acts = [-1.0, -0.5, 0.0, 0.5, 1.0]
    lo, hi = 3000, 3200
    d = tmp_path / "v" / "s0"
    d.mkdir(parents=True)
    Wm = np.random.default_rng(1).standard_normal((hi - lo, 5)).astype(np.float32)
    np.save(d / "w_f00_A.npy", Wm)
    with open(d / "rec_f00_pool.json", "w") as fh:
        json.dump({"assets": {"A": {"fallback": True}}, "geo": {"A": {"lo": 0, "te_lo": lo, "te_hi": hi}}, "columns": []}, fh)
    import pandas as pd
    fts = [{"i": 0, "test_start": pd.Timestamp(int(A.t[lo]), unit="ms", tz="UTC"),
            "test_end": pd.Timestamp(int(A.t[hi]), unit="ms", tz="UTC")}]
    Wr, _, _, _ = phase5.oos_w(str(tmp_path), "v", 0, fts, A, acts, None, "rule")
    Wn, _, _, _ = phase5.oos_w(str(tmp_path), "v", 0, fts, A, acts, None, "none")
    Wt, _, _, _ = phase5.oos_w(str(tmp_path), "v", 0, fts, A, acts, None, "trend")
    assert (np.argmax(Wr, 1) == 2).all() and np.array_equal(Wn, Wm)
    assert np.array_equal(np.asarray(acts)[np.argmax(Wt, 1)], A.rd["ref"][lo:hi])
