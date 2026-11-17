# -*- coding: utf-8 -*-
"""H55 (research/setups_filter.py): the inputs at a decision bar never read a later row; the history scoring of a signal
is engine15/signals.py's own live result on synthetic bars (signals.run driven check by check through fake pages and
files); nothing at or after the seal is used; and the two numpy variants do what they say."""
import io
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import setups_filter as sf  # noqa: E402
from engine15 import shadows, signals  # noqa: E402

BAR = signals.BAR_MS
CSV_HEAD = ("t_in_ms,t_out_ms,side,p_in,p_out,why_in,why_out,pnl_pct,equity,qty,pnl_usd,fees_usd,stop0,risk_usd,r_mult,"
            "target_1,target_2,time_in,time_out")


# ---------------------------------------------------------------------------------- no look-ahead
def _arrays(n, seed=1):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.3, n))
    odds = rng.dirichlet([2, 2, 2], n)
    tg = pd.DataFrame({"fib_1h_dir": rng.choice([-1.0, 1.0, np.nan], n), "fib_1h_t1_px": close + rng.normal(0, 2, n),
                       "fib_1h_t2_px": close + rng.normal(0, 3, n), "fib_4h_dir": rng.choice([-1.0, 1.0], n),
                       "fib_4h_t1_px": close + rng.normal(0, 2, n), "fib_4h_t2_px": close + rng.normal(0, 3, n),
                       "reach_24h_med_pct": rng.uniform(0.5, 3, n)})
    t0 = int(pd.Timestamp("2022-03-01", tz="UTC").value // 10 ** 6)
    return {"X": rng.normal(size=(n, 12)), "odds": odds, "close": close, "unit": rng.uniform(0.2, 1.0, n),
            "atr15": rng.uniform(0.05, 0.4, n), "targets": tg, "times_ms": t0 + BAR * np.arange(n, dtype=np.int64)}


def _cut(A, m):
    return dict((k, (v.iloc[:m].copy() if isinstance(v, pd.DataFrame) else np.array(v[:m], copy=True))) for k, v in A.items())


def _scramble(A, k, seed=9):
    """The same arrays with every row after k replaced by other numbers."""
    rng = np.random.default_rng(seed)
    B = _cut(A, len(A["close"]))
    for key, v in B.items():
        if isinstance(v, pd.DataFrame):
            v.iloc[k + 1:] = rng.normal(size=v.iloc[k + 1:].shape) * 50
        elif key == "times_ms":
            continue
        else:
            v[k + 1:] = rng.normal(size=v[k + 1:].shape) * 50
    return B


@pytest.mark.parametrize("k", [0, 5, 77, 198])
@pytest.mark.parametrize("side", [1, -1])
def test_inputs_at_k_ignore_every_later_row(k, side):
    A = _arrays(200)
    x0, e0 = sf.decision_inputs(A, k, side)
    for B in (_cut(A, k + 1), _scramble(A, k)):
        x1, e1 = sf.decision_inputs(B, k, side)
        assert np.array_equal(x0, x1)
        assert sorted(e0) == sorted(e1) == sorted(sf.EXTRA)
        for name in e0:
            assert (e0[name] == e1[name]) or (e0[name] != e0[name] and e1[name] != e1[name]), name


def test_inputs_are_signed_to_the_side():
    A = _arrays(50)
    _, lo = sf.decision_inputs(A, 10, 1)
    _, sh = sf.decision_inputs(A, 10, -1)
    assert lo["odds_with"] == sh["odds_against"] and lo["odds_against"] == sh["odds_with"]
    assert lo["edge_signed"] == -sh["edge_signed"]
    assert lo["stop_atr"] == pytest.approx(2.0 * A["unit"][10] / A["atr15"][10])
    assert lo["hour_utc"] == pd.Timestamp(int(A["times_ms"][10]) + BAR, unit="ms", tz="UTC").hour


# ---------------------------------------------------------------------------------- history scoring == signals.run
def _utc(ms):
    return signals._dt(ms).strftime("%Y-%m-%d %H:%M")


class Live(object):
    """signals.run driven check by check: one check per 15-minute slot, 150 s into it; the page has reached the last bar
    that closed before the check; the book's position shows until the bar it closed in has been processed."""

    def __init__(self, tmp, asset, group, bars, trade):
        self.asset, self.group, self.bars, self.tr = asset, group, bars, trade
        self.data, self.live = str(tmp / "data"), str(tmp / "live")
        os.makedirs(self.data)
        os.makedirs(self.live)
        self.state, self.log = os.path.join(self.data, "st.json"), os.path.join(self.data, "log.jsonl")
        ts, o, h, l, c = bars
        with io.open(signals.bar_path(self.data, asset), "wb") as fh:
            fh.write(b"ts_ms,open,high,low,close,volume,taker_buy\n")
            for j in range(len(ts)):
                fh.write(("%d,%r,%r,%r,%r,1.0,\n" % (int(ts[j]), float(o[j]), float(h[j]), float(l[j]), float(c[j]))).encode())
        self.booked = False

    def page(self, now_ms):
        ts = self.bars[0]
        done = ts[ts + BAR <= now_ms]
        last = int(done[-1]) if len(done) else int(ts[0]) - BAR
        tr = self.tr
        if last >= tr["f_ms"] and last < tr["t_out_ms"]:
            view = dict(tr["view"])
        else:
            view = {"status": "FLAT", "trades": 0, "wins": 0}
        if last >= tr["t_out_ms"] and not self.booked:
            path = signals.trades_path(self.live, self.asset)
            with io.open(path, "a", encoding="utf-8") as fh:
                fh.write(CSV_HEAD + "\n" + "%d,%d,%d,%r,%r,ENTER,%s,%r,10000,1,%r,2,%r,200,%r,%r,%r,%s,%s\n" % (
                    tr["f_ms"], tr["t_out_ms"], tr["side"], tr["view"]["entry"], 1.0, tr["why_out"], 0.5, 50.0,
                    tr["view"]["stop"], 0.3, tr["view"]["target_1"], tr["view"]["target_2"], _utc(tr["f_ms"]),
                    _utc(tr["t_out_ms"])))
            self.booked = True
        return {"markets": {self.group: [self.asset]}, "assets": {self.asset: {"market_group": self.group}},
                "shadows": {"books": {signals.BOOK: {"assets": {self.asset: view}}},
                            "markets": {self.group: {"as_of_utc": _utc(last + BAR)}}}}

    def play(self):
        send = lambda text, reply_to=None: (True, 1)      # noqa: E731
        f_ms = self.tr["f_ms"]
        slot = f_ms - 3 * BAR
        signals.run(self.page(slot + 150000), signals._dt(slot + 150000), send, self.data, self.live, self.state, self.log)
        issued = False
        end = int(self.bars[0][-1]) + 3 * BAR
        while slot <= end:
            slot += BAR
            now = slot + 150000
            signals.run(self.page(now), signals._dt(now), send, self.data, self.live, self.state, self.log)
            st = signals.load_state(self.state)
            issued = issued or bool(st["open"]) or any(e.get("ev") == "signal" for e in signals.read_log(self.log))
            if issued and not st["open"]:
                break
        ev = dict((e["ev"], e) for e in signals.read_log(self.log) if e.get("id"))
        if "closed" in ev:
            return {"state": "closed", "reason": ev["closed"]["why"], "r": ev["closed"]["r"], "pct": ev["closed"]["pct"]}
        if "no_fill" in ev:
            return {"state": "no_fill", "reason": ev["no_fill"]["reason"]}
        return {"state": "unresolved" if "signal" in ev else "not_a_signal"}


def _market(seed, n=160, gaps=True):
    rng = np.random.default_rng(seed)
    t0 = int(pd.Timestamp("2024-02-05 00:00", tz="UTC").value // 10 ** 6)
    slots = np.arange(n + 40)
    if gaps:                                                      # a few shut sessions
        keep = np.ones(len(slots), bool)
        for g in rng.integers(10, n, 3):
            keep[g:g + rng.integers(2, 9)] = False
        slots = slots[keep]
    slots = slots[:n]
    ts = t0 + BAR * slots.astype(np.int64)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.0015, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.003, n)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.003, n)))
    return ts, o, h, l, c


def _trade(bars, seed):
    rng = np.random.default_rng(1000 + seed)
    ts, o, h, l, c = bars
    F = int(rng.integers(5, len(ts) - 60))
    side = int(rng.choice([1, -1]))
    E = float(o[F])
    R = E * float(rng.uniform(0.002, 0.03))
    S = E - side * R
    T1 = E + side * R * float(rng.uniform(0.6, 2.0))
    T2 = T1 + side * R * float(rng.uniform(0.3, 1.5))
    out = F + int(rng.integers(1, 50))
    why = str(rng.choice(["STOP", "T1+T2", "FLIP", "T1+STOP_BE", "STEP_ASIDE"]))
    early = bool(h[F] >= T1) if side > 0 else bool(l[F] <= T1)
    view = sf.page_view(side, E, S, T1, T2, int(ts[F]), early)
    return {"f_ms": int(ts[F]), "t_out_ms": int(ts[out]), "side": side, "why_out": why, "view": view}


@pytest.mark.parametrize("seed", list(range(100)))
def test_history_scoring_is_the_live_state_machine(tmp_path, seed):
    bars = _market(seed, gaps=seed % 3 != 0)
    tr = _trade(bars, seed)
    asset = ["BTCUSDT", "XAUUSD", "SPX", "WTI"][seed % 4]
    hist = sf.score_followable(asset, tr["view"], bars, tr["t_out_ms"], tr["why_out"])
    live = Live(tmp_path, asset, "g", bars, tr).play()
    assert hist["state"] == live["state"], (hist, live)
    if live["state"] in ("closed", "no_fill"):
        assert hist["reason"] == live["reason"], (hist, live)
    if live["state"] == "closed":
        assert hist["r"] == pytest.approx(live["r"], abs=1e-12)
        assert hist["pct"] == pytest.approx(live["pct"], abs=1e-12)


def test_scoring_covers_every_outcome():
    seen = set()
    for seed in range(40):
        bars = _market(seed, gaps=seed % 3 != 0)
        tr = _trade(bars, seed)
        r = sf.score_followable("BTCUSDT", tr["view"], bars, tr["t_out_ms"], tr["why_out"])
        seen.add((r["state"], r.get("reason")))
    states = set(s for s, _ in seen)
    assert {"closed", "no_fill"} <= states, seen
    assert len(seen) >= 5, seen


# ---------------------------------------------------------------------------------- the seal
def test_rows_after_the_seal_are_dropped_on_load():
    idx = pd.date_range("2025-11-10 22:00", "2025-11-11 03:00", freq="15min", tz="UTC")
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=idx)
    cut = sf.sealed_bars(df)
    assert len(cut) == 8 and cut.index.max() < pd.Timestamp(sf.SEAL, tz="UTC")
    assert sf.seal_n(idx) == 8


def test_the_scorer_refuses_bars_at_or_after_the_seal():
    ts = sf.SEAL_MS + BAR * np.arange(-5, 3, dtype=np.int64)
    one = np.ones(len(ts))
    view = sf.page_view(1, 1.0, 0.99, 1.02, 1.03, int(ts[0]), False)
    with pytest.raises(ValueError):
        sf.score_followable("BTCUSDT", view, (ts, one, one, one, one), int(ts[-1]), "FLIP")


def test_a_signal_decided_only_after_the_seal_is_unresolved_not_guessed():
    ts = sf.SEAL_MS + BAR * np.arange(-8, 0, dtype=np.int64)       # the last eight bars before the seal
    E = 100.0
    o = np.full(len(ts), 100.5)
    h, l, c = o + 0.3, o - 0.6, o.copy()                             # the entry fills (low 99.9 <= 100), nothing else trades
    view = sf.page_view(1, E, 98.0, 103.0, 105.0, int(ts[0]), False)
    r = sf.score_followable("BTCUSDT", view, (ts, o, h, l, c), sf.SEAL_MS + 50 * BAR, "FLIP")
    assert r["state"] == "unresolved"


def test_stage_b_reads_no_row_at_or_after_the_seal(tmp_path, monkeypatch):
    monkeypatch.setattr(sf, "OUT", str(tmp_path))
    meta = pd.DataFrame({"asset": ["BTCUSDT"] * 3, "t_in_ms": [sf.SPLIT_MS, sf.SEAL_MS - BAR, sf.SEAL_MS]})
    meta.to_csv(os.path.join(str(tmp_path), "rows_crypto.csv"), index=False)
    np.save(os.path.join(str(tmp_path), "X_crypto.npy"), np.zeros((3, 2)))
    import json
    with open(os.path.join(str(tmp_path), "group_crypto.json"), "w") as fh:
        json.dump({"features": ["a", "b"]}, fh)
    m, X, _g, _f = sf.load_rows(lambda *a: None)
    assert len(m) == 2 and len(X) == 2 and (m["t_in_ms"] < sf.SEAL_MS).all()


# ---------------------------------------------------------------------------------- the two numpy variants
def _toy(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 6))
    z = 1.2 * X[:, 0] - 0.8 * X[:, 1] + 0.9 * (X[:, 2] > 0.5)
    y = (rng.random(n) < 1 / (1 + np.exp(-(z - 0.7)))).astype(int)
    return X, y


def test_f1_reaches_the_optimum_of_the_registered_objective():
    X, y = _toy()
    X[:, 5] = 3.0                                                  # a constant input keeps scale 1
    m = sf.LogitL2(C=0.1).fit(X, y)
    assert m.grad_norm_ < 1e-6
    assert m.scale_[5] == 1.0 and m.coef_[5] == pytest.approx(0.0, abs=1e-9)
    assert sf.auc(m.predict_proba(X), y) > 0.7
    w = sf.balanced_weights(y)
    assert w[y == 1].sum() == pytest.approx(w[y == 0].sum())


def test_f2_stand_in_learns_and_keeps_its_settings():
    X, y = _toy()
    m = sf.HGBStandIn(**sf.F2).fit(X[:2000], y[:2000])
    assert len(m.trees_) == 200
    for nodes in m.trees_:
        assert sum(1 for nd in nodes if nd[0] == "leaf") <= 8
    assert sf.auc(m.predict_proba(X[2000:]), y[2000:]) > 0.7
    assert np.argmax(m.importance()) in (0, 1, 2)
    th = sf.HGBStandIn.thresholds(np.arange(10, dtype=float))
    assert np.allclose(th, np.arange(9) + 0.5)
    assert len(sf.HGBStandIn.thresholds(np.random.default_rng(0).normal(size=5000))) <= 254


def test_the_sklearn_path_is_judged_when_it_is_installed(monkeypatch):
    monkeypatch.setattr(sf, "sklearn_available", lambda: False)
    m, lib = sf.judged_models()
    assert isinstance(m["F1"], sf.LogitL2) and isinstance(m["F2"], sf.HGBStandIn) and "numpy" in lib
    if not sf.importlib_find("sklearn"):
        fake = type(sys)("sklearn")
        fake.__version__ = "0.test"
        monkeypatch.setitem(sys.modules, "sklearn", fake)
    monkeypatch.setattr(sf, "sklearn_available", lambda: True)
    m, lib = sf.judged_models()
    assert isinstance(m["F1"], sf.SkF1) and isinstance(m["F2"], sf.SkF2) and lib.startswith("scikit-learn")


def test_sklearn_variants_fit_as_registered():
    pytest.importorskip("sklearn")
    assert sf.sklearn_available()
    X, y = _toy()
    f1 = sf.SkF1().fit(X[:2000], y[:2000])
    assert f1.lr.C == 0.1 and f1.lr.class_weight == "balanced" and f1.lr.solver == "lbfgs" and f1.lr.max_iter == 5000
    ref = sf.LogitL2(C=0.1).fit(X[:2000], y[:2000])           # the numpy stand-in reaches the same optimum
    assert np.allclose(f1.coef_, ref.coef_, atol=1e-3)
    assert np.allclose(f1.predict_proba(X[2000:]), ref.predict_proba(X[2000:]), atol=1e-3)
    f2 = sf.SkF2().fit(X[:2000], y[:2000])
    p = f2.m.get_params()
    assert (p["max_depth"], p["learning_rate"], p["max_iter"], p["min_samples_leaf"], p["l2_regularization"],
            p["early_stopping"], p["random_state"]) == (3, 0.05, 200, 50, 1.0, False, 55)
    assert f2.m.n_iter_ == 200
    assert sf.auc(f2.predict_proba(X[2000:]), y[2000:]) > 0.7
    assert np.argmax(f2.importance()) in (0, 1, 2)


def test_block_bootstrap_is_fixed_and_one_sided():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 1, 2000)
    weeks = np.repeat(np.arange(100), 20)
    keep = r > 0
    obs, p, _ = sf.block_bootstrap_p(r, keep, weeks, n=2000)
    assert obs > 0 and p < 0.01
    obs2, p2, _ = sf.block_bootstrap_p(r, ~keep, weeks, n=2000)
    assert obs2 < 0 and p2 > 0.99
    assert sf.block_bootstrap_p(r, keep, weeks, n=500)[1] == sf.block_bootstrap_p(r, keep, weeks, n=500)[1]
