# -*- coding: utf-8 -*-
"""Phase 5, part 1: the forward paper run of the Phase 4 primary (engine15/rl/forward5.py, engine15/playbook5.py).

Real data (skipped when Phase 4's caches / the rebuilt fold-24 model are missing):
  1. forward == batch: over a recent historical slice, the forward step (features from a bar window + readings rows, the
     exported model, decisions in several calls on data cut at each call, recorded, the book rebuilt from the record)
     gives exactly Phase 4's batch walk-forward decisions (its STORED fold values -> policy3.decide -> risk3.apply ->
     backtester) for the same model and bars; the forward values equal Phase 4's stored values.
  2. no look-ahead (truncation): perturbing every bar, funding rate and reading after a cut never changes a decision at
     or before the cut; window features == Phase 4's full-history cache rows.
  3. the live readings source (the evidence store's tail rows) == Phase 4's snapshot on settled rows.
Planted data (always):
  4. forward == a batch path built from Phase 4's own functions; incremental == one shot; resume from the record.
  5. a model never decides a bar that closes before its data end; 'do no harm' keeps a seed flat.
  6. the update launcher: never two at once, never under 1,500 MB free, not when not due, retries spaced.
"""
import copy
import json
import os

import numpy as np
import pandas as pd
import pytest

from conftest import make_bars, make_funding
from engine15.rl import features4, forward5, policy3, pool4, qagent, risk3
from engine15.rl.config import resolve
from engine15.rl.env import Market

CFG = forward5.load_cfg()
REPRO = os.path.join(resolve(CFG["phase5"]["report"]["models_dir5"]), "repro_f24", "model_phase4_f24.json")
P4CACHE = pool4.cache_dir(CFG)


def _real():
    if not (os.path.exists(REPRO) and os.path.exists(os.path.join(P4CACHE, "BTCUSDT", "meta.json"))):
        pytest.skip("Phase 4 caches or the rebuilt fold-24 model are missing (py -3 -m engine15.rl phase5-repro)")


# ---------------------------------------------------------------- real data
def test_forward_decisions_equal_phase4_batch_for_the_same_model_and_bars(tmp_path):
    _real()
    rep = forward5.forward_vs_batch(CFG, REPRO, "2026-11-01", None, steps=4, journal_dir=str(tmp_path), log=lambda *_: None)
    assert rep["decisions_equal"], rep
    assert rep["exec_max_diff"] <= 1e-12, rep
    assert rep["equity_max_diff"] <= 1e-9, rep
    assert rep["w_max_diff"] <= 1e-6, rep                 # forward values == Phase 4's stored fold values
    assert rep["bars"] > 1500


def test_no_lookahead_truncation_on_real_data(tmp_path):
    _real()
    model = forward5.load_model(REPRO)
    models = [(int(model["data_end_close_ms"]), model)]
    asset = "BTCUSDT"
    bars, fund = pool4.load_bars(CFG, asset, True, lambda *_: None)
    snap = os.path.join(P4CACHE, "readings_%s.npz" % asset)
    te_hi = int(model["info"]["geo"][asset]["te_hi"])
    i_s, cut, i_e = te_hi - 900, te_hi - 400, te_hi - 1
    cm = np.asarray(bars.index.as_unit("ms").asi8) + forward5.BAR_MS
    reg = int(cm[i_s - 1])
    W = int(CFG["phase5"]["forward"]["feature_window_bars"])
    lo = i_s - W - 50
    t, raw, _ = forward5.readings_tail(asset, int(bars.index[lo].value // 10**6), snapshot=snap)

    def run(b, f, tt, rr, name):
        jp = str(tmp_path / name)
        forward5.advance(asset, CFG, reg, jp, models, b, f, (tt, rr, int(tt[-1])), log=lambda *_: None)
        return forward5.read_journal(jp)

    # (a) data cut at the cut bar
    keep = t <= int(bars.index[cut].value // 10**6)
    Ja = run(bars.iloc[lo:cut + 1], fund[np.asarray(fund["settle_ms"]) <= cm[cut]], t[keep],
             dict((k, v[keep]) for k, v in raw.items()), "a.jsonl")
    # (b) full data with everything after the cut perturbed
    rng = np.random.default_rng(5)
    b2 = bars.iloc[lo:i_e + 1].copy()
    k = cut + 1 - lo
    for c in ("open", "high", "low", "close", "volume"):
        b2.iloc[k:, b2.columns.get_loc(c)] *= np.exp(rng.normal(0, 0.05, len(b2) - k))
    f2 = fund[np.asarray(fund["settle_ms"]) <= cm[i_e]].copy()
    late = np.asarray(f2["settle_ms"]) > cm[cut]
    f2.loc[late, "rate"] = rng.normal(0, 0.01, int(late.sum()))
    raw2 = dict((kk, v.copy()) for kk, v in raw.items())
    after = t > int(bars.index[cut].value // 10**6)
    for kk in raw2:
        raw2[kk][after] = rng.normal(0, 3, int(after.sum()))
    Jb = run(b2, f2, t, raw2, "b.jsonl")
    assert len(Ja) == cut + 1 - i_s
    for x, y in zip(Ja, Jb[:len(Ja)]):
        assert x["t"] == y["t"] and x["ip"] == y["ip"] and x["since"] == y["since"]
    # window features == Phase 4's full-history cache rows (float32)
    A = pool4.Asset(os.path.join(P4CACHE, asset))
    bw = bars.iloc[cut - W:cut + 1]
    fw = features4.build(bw, fund[np.asarray(fund["settle_ms"]) <= cm[cut]], CFG["features"],
                         forward5.readings_on(bw.index, t, raw)).astype("float32")
    X = np.asarray(A.X[cut - 200:cut + 1][:, A.cols(model["columns"])])
    Y = fw[model["columns"]].values[-201:]
    same = (X == Y) | (np.isnan(X) & np.isnan(Y))
    assert np.mean(same) > 0.999 and np.allclose(np.nan_to_num(X), np.nan_to_num(Y), rtol=1e-6, atol=1e-7)


def test_live_readings_source_equals_phase4_snapshot_on_settled_rows():
    _real()
    for asset in ("BTCUSDT", "ETHUSDT"):
        snap = os.path.join(P4CACHE, "readings_%s.npz" % asset)
        if not os.path.exists(os.path.join(features4.store_path(asset), "meta.json")):
            pytest.skip("no evidence store")
        t0 = int(pd.Timestamp("2026-08-01", tz="UTC").value // 10**6)
        t1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)
        ts, rs, _ = forward5.readings_tail(asset, t0, snapshot=snap)
        tl, rl, _ = forward5.readings_tail(asset, t0)
        ms, ml = ts < t1, tl < t1
        assert np.array_equal(ts[ms], tl[ml])
        for c in rs:
            a, b = rs[c][ms], rl[c][ml].astype(np.float32).astype(np.float64)
            assert np.array_equal(np.isnan(a), np.isnan(b)), c
            assert np.allclose(np.nan_to_num(a), np.nan_to_num(b), rtol=0, atol=0), c


# ---------------------------------------------------------------- planted data
def _snapshot(path, index, seed=3):
    rng = np.random.default_rng(seed)
    vals = dict((c, rng.standard_normal(len(index)).astype(np.float32)) for c in list(features4.READINGS) + features4.AVAIL_COLS)
    vals["fund_raw"][:300] = np.nan
    np.savez(path, times_ms=np.asarray(index.as_unit("ms").asi8, dtype=np.int64), meta=json.dumps({}), **vals)


def _model(feats, assets, data_end_ms, seed=0, scale=3.0, fallback=None, mid="m_test"):
    cols = list(feats.columns)
    rng = np.random.default_rng(seed)
    F = len(cols)
    mu, sd = pool4.norm_stats(feats.values.astype(np.float32), 0, len(feats), np.arange(F))
    s = {"weights": [(scale * rng.standard_normal((5, F))).tolist()], "biases": [np.zeros(5).tolist()],
         "stats": dict((a, {"mu": mu.tolist(), "sd": sd.tolist()}) for a in assets),
         "fallback": dict((a, bool((fallback or {}).get(a, False))) for a in assets)}
    q = CFG["qagent"]
    return {"id": mid, "data_end_close_ms": int(data_end_ms), "data_end_utc": "", "columns": cols,
            "actions": CFG["actions"], "min_hold_bars": 4,
            "qagent": dict((k, q[k]) for k in ("reward_scale", "cost_mult", "obs_clip", "activation", "vol_scale",
                                               "vol_ref_annual", "vol_scale_cap", "risk_aversion", "net_arch")),
            "seeds": {"0": s, "1": dict(s, weights=[(scale * np.random.default_rng(seed + 1).standard_normal((5, F))).tolist()]),
                      "2": dict(s, weights=[(scale * np.random.default_rng(seed + 2).standard_normal((5, F))).tolist()])},
            "info": {}}


def _planted(tmp_path, n=6200):
    b = make_bars(n=n, seed=21)
    f = make_funding(b.index, seed=22)
    snap = str(tmp_path / "snap.npz")
    _snapshot(snap, b.index)
    rf = features4.readings_frame(snap, b.index)
    feats = features4.build(b, f, CFG["features"], rf).astype("float32")
    return b, f, snap, feats


def _batch(b, f, feats, model, asset, i_s, i_e):
    """A batch path from Phase 4's own functions: env.Market + qagent.reward_arrays, pool4.normalised, qagent.w_numpy,
    q_from_w, policy3.decide from flat, risk3.apply."""
    from engine15.rl import costs
    m = Market(b, f, feats, costs.from_cfg(CFG))
    rd = qagent.reward_arrays(m, CFG["qagent"])
    acts = np.asarray(CFG["actions"], float)
    out = {}
    cols = np.array([list(feats.columns).index(c) for c in model["columns"]])
    for s in ("0", "1", "2"):
        ms = model["seeds"][s]
        st = ms["stats"][asset]
        x = pool4.normalised(m.raw, i_s, i_e + 1, cols, np.asarray(st["mu"], np.float32), np.asarray(st["sd"], np.float32))
        F = x.shape[1]
        W = qagent.w_numpy(([np.asarray(w, np.float32) for w in ms["weights"]], [np.asarray(v, np.float32) for v in ms["biases"]]),
                           x, np.zeros(F, np.float32), np.ones(F, np.float32), model["qagent"])
        if ms["fallback"][asset]:
            from engine15.rl.continual import neutral_w
            W = neutral_w(len(W), acts, 0.0)
        Q = qagent.q_from_w(W, rd["k"][i_s:i_e + 1], rd["c1"][i_s:i_e + 1], qagent.cost_matrix(acts), CFG["qagent"])
        ip, _ = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), 4)
        tgt = np.zeros(len(b))
        tgt[i_s:i_e + 1] = acts[ip]
        out[s] = (ip, risk3.apply(m, tgt, i_s, i_e + 1, dict(CFG["risk3"]), log_events=False)["exec"])
    return out


def _forward(tmp_path, b, f, snap, models, reg, cuts, name="j.jsonl", asset="TEST"):
    jp = str(tmp_path / name)
    for c in cuts:
        bc = b.iloc[:c + 1]
        t, raw, _ = forward5.readings_tail(asset, int(bc.index[0].value // 10**6), snapshot=snap)
        keep = t <= int(bc.index[-1].value // 10**6)
        cm = int(bc.index[-1].value // 10**6) + forward5.BAR_MS
        forward5.advance(asset, CFG, reg, jp, models, bc, f[np.asarray(f["settle_ms"]) <= cm],
                         (t[keep], dict((k, v[keep]) for k, v in raw.items()), int(t[keep][-1])), log=lambda *_: None)
    return jp


def test_forward_equals_batch_incremental_equals_one_shot_on_planted_data(tmp_path):
    b, f, snap, feats = _planted(tmp_path)
    i_s, i_e = 5000, len(b) - 1
    cm = np.asarray(b.index.as_unit("ms").asi8) + forward5.BAR_MS
    model = _model(feats, ["TEST"], cm[i_s - 1])
    models = [(model["data_end_close_ms"], model)]
    bt = _batch(b, f, feats, model, "TEST", i_s, i_e)
    for name, cuts in (("inc.jsonl", [5100, 5101, 5400, 5900, i_e]), ("one.jsonl", [i_e])):
        jp = _forward(tmp_path, b, f, snap, models, int(cm[i_s - 1]), cuts, name)
        J = forward5.read_journal(jp)
        assert len(J) == i_e + 1 - i_s
        ip = np.array([r["ip"] for r in J])
        for k, s in enumerate(("0", "1", "2")):
            assert np.array_equal(ip[:, k], bt[s][0]), (name, s)
        assert sum(np.count_nonzero(np.diff(bt[s][0])) for s in bt) > 10      # the planted model does trade
        B = forward5.risk_and_book(CFG, b, f, J, int(cm[i_s - 1]))
        for k, s in enumerate(("0", "1", "2")):
            assert np.max(np.abs(B["exec"][k, B["lo"]:] - bt[s][1][i_s:i_e + 1])) <= 1e-12
    # resume: nothing new to decide -> nothing appended
    n0 = len(forward5.read_journal(jp))
    _forward(tmp_path, b, f, snap, models, int(cm[i_s - 1]), [i_e], "one.jsonl")
    assert len(forward5.read_journal(jp)) == n0


def test_a_model_never_decides_bars_before_its_data_end_and_do_no_harm_is_flat(tmp_path):
    b, f, snap, feats = _planted(tmp_path)
    cm = np.asarray(b.index.as_unit("ms").asi8) + forward5.BAR_MS
    i_s = 5000
    m1 = _model(feats, ["TEST"], cm[i_s - 1], seed=0, mid="old")
    m2 = _model(feats, ["TEST"], cm[5500], seed=9, mid="new", fallback={"TEST": True})
    jp = _forward(tmp_path, b, f, snap, [(m1["data_end_close_ms"], m1), (m2["data_end_close_ms"], m2)], int(cm[i_s - 1]),
                  [len(b) - 1])
    J = forward5.read_journal(jp)
    for r in J:
        assert r["m"] == ("new" if r["c"] >= m2["data_end_close_ms"] else "old")
    late = [r for r in J if r["m"] == "new"]
    assert late and all(r["fb"] == [True, True, True] for r in late)
    assert all(r["req"] == [0.0, 0.0, 0.0] for r in late[10:])          # flat after at most the minimum hold


def _tmp_cfg(tmp_path):
    c = copy.deepcopy(CFG)
    c["phase5"]["report"] = {"models_dir5": str(tmp_path / "models5"), "cache_dir5": str(tmp_path / "cache"),
                             "forward_dir": str(tmp_path / "fwd")}
    return c


def test_update_launcher_guards(tmp_path):
    c = _tmp_cfg(tmp_path)
    calls = []
    now = int(pd.Timestamp("2026-11-18 03:00", tz="UTC").value // 10**6)        # a Wednesday
    # no model at all -> due; under 1,500 MB free -> not launched
    assert forward5.maybe_launch_update(c, now, log=lambda *_: None, free_mb=1000, launcher=lambda: calls.append(1)) == "low memory"
    assert not calls
    # retries are spaced (30 min)
    assert forward5.maybe_launch_update(c, now, log=lambda *_: None, free_mb=4000, launcher=lambda: calls.append(1)) == "waiting to retry"
    os.remove(os.path.join(forward5.forward_dir(c), "update_attempt.json"))
    assert forward5.maybe_launch_update(c, now, log=lambda *_: None, free_mb=4000, launcher=lambda: calls.append(1)) == "launched"
    assert calls == [1]
    # an update holding the lock (a live PID) -> never a second one
    os.remove(os.path.join(forward5.forward_dir(c), "update_attempt.json"))
    with open(os.path.join(forward5.forward_dir(c), "update.lock"), "w") as fh:
        json.dump({"pid": os.getpid()}, fh)
    assert forward5.maybe_launch_update(c, now, log=lambda *_: None, free_mb=4000, launcher=lambda: calls.append(1)) == "running"
    assert forward5.update_cli(c, log=lambda *_: None, force=True) == 0 and calls == [1]
    assert os.path.exists(os.path.join(forward5.forward_dir(c), "update.lock"))   # the other update's lock is untouched
    # a dead PID's lock is stale
    with open(os.path.join(forward5.forward_dir(c), "update.lock"), "w") as fh:
        json.dump({"pid": 999999}, fh)
    assert not forward5.update_running(c)
    # a model with data through the latest Monday 00:00 UTC -> not due
    os.makedirs(forward5.live_models_dir(c), exist_ok=True)
    mon = forward5.last_monday_ms(now)
    assert pd.Timestamp(mon, unit="ms").dayofweek == 0
    with open(os.path.join(forward5.live_models_dir(c), "model_x.json"), "w") as fh:
        json.dump({"data_end_close_ms": mon + 900000}, fh)
    assert forward5.maybe_launch_update(c, now, log=lambda *_: None, free_mb=4000, launcher=lambda: calls.append(1)) == "not due"
    assert forward5.update_due(c, now + 6 * 86400000)                            # a week later it is due again
