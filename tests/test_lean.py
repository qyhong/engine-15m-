# -*- coding: utf-8 -*-
"""The live step's lean think stage (evcache.py, leanprep.py) gives exactly backtest.prepare's numbers.

Since layout 2 (17 Nov 2026) the store keeps no X.bin: the feature matrix is rebuilt from the stored
readings. The tests below hold it to the bytes of evidence.matrix (what X.bin held), to the refits,
odds, paper-book decisions and journal entries of the full prepare, and check that an older or
half-written store is built again rather than read.

    py -3 -m pytest tests/test_lean.py -q
"""
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, evcache, evidence, journal, leanprep, live, model  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
from test_engine import make_bars  # noqa: E402


def _cfg(bars):
    end = min(df.index[-1] for df in bars.values())
    return dict(CFG, assets=tuple(bars), birth=str((end - pd.Timedelta(days=240)).date()), voting=voting_for("crypto"))


def _same(a, b):
    return np.array_equal(np.asarray(a), np.asarray(b), equal_nan=True)


def _bits(a):
    """The raw bytes: 0.0 and -0.0, or two different NaNs, are NOT the same here."""
    return np.ascontiguousarray(np.asarray(a)).tobytes()


def _book(prep, a, lo, n):
    """The main paper book over sessions lo .. n-1 from a flat start, as live.step_group runs it."""
    ev, cfg = prep["ev"][a], prep["cfg"]
    acfg = live.asset_cfg(a, cfg)
    acfg["risk_budget_usd"] = None
    return backtest.run_book(prep["px"][a], prep["odds"][a], ev["shock"].values, ev["tide"].values,
                             (cfg["barrier_atr"] * ev["atr1h"]).values, acfg, lo, n, state=None,
                             bias=ev["htf_bias"].values, guard=ev["release_soon"].values)


def _old_layout_X(path, X, n):
    """The feature matrix as layout 1 kept it: evidence.matrix's rows written as they are into X.bin
    (row-major float64 with spare rows), read back as a memory map of the stored rows."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cap = n + 100
    mm = np.memmap(path, dtype=np.float64, mode="w+", shape=(cap, X.shape[1]))
    for s in range(0, n, 7000):                                      # in pieces, as the store was built
        mm[s:min(s + 7000, n)] = X[s:min(s + 7000, n)]
    mm.flush()
    del mm
    return np.memmap(path, dtype=np.float64, mode="r", shape=(cap, X.shape[1]))[:n]


def test_build_rows_equals_full_build():
    bars = {"BTCUSDT": make_bars(n=12000, seed=1), "ETHUSDT": make_bars(n=12000, seed=2)}
    full = evidence.build(bars)
    rows = np.array([0, 5, 777, 8000, 11998, 11999])
    part = evidence.build(bars, rows=rows)
    for a in bars:
        want = full[a].iloc[rows]
        assert list(part[a].columns) == list(want.columns)
        assert part[a].dtypes.equals(want.dtypes)
        assert part[a].equals(want)


def test_lean_prepare_matches_prepare(tmp_path):
    n0 = 30000
    allbars = {"BTCUSDT": make_bars(n=n0 + 40, seed=1), "ETHUSDT": make_bars(n=n0 + 40, seed=2)}
    for step, n in enumerate((n0, n0 + 1, n0 + 40)):                 # a first build, one new bar, a catch-up
        bars = dict((a, df.iloc[:n]) for a, df in allbars.items())
        cfg = _cfg(bars)
        ref = backtest.prepare(cfg=cfg, bars=bars, funding={}, live={})
        lean = leanprep.prepare_live(cfg, bars, {}, {}, "test", root=str(tmp_path))
        lo = lean["lean_lo"]
        assert lo == ref["birth_idx"]
        assert lean["times"].equals(ref["times"])
        for a in bars:
            assert _same(lean["odds"][a], ref["odds"][a])
            assert _same(lean["probs"][a][lo:n], ref["probs"][a][lo:])
            assert np.isnan(ref["probs"][a][:lo]).all() and np.isnan(ref["odds"][a][:lo]).all()
            assert _same(lean["X"][a], ref["X"][a]) and _same(lean["ready"][a], ref["ready"][a])
            assert _same(lean["y"][a], ref["y"][a]) and _same(lean["res"][a], ref["res"][a])
            assert lean["ev"][a].dtypes.equals(ref["ev"][a].dtypes)
            assert lean["ev"][a].equals(ref["ev"][a])
            for k in ("open", "high", "low", "close"):
                assert _same(lean["px"][a][k], ref["px"][a][k])
        assert _same(lean["trust"][lo:n], ref["trust"][lo:])
        assert [m[0] for m in lean["models"]] == [m[0] for m in ref["models"]]
        for (s1, w1, r1), (s2, w2, r2) in zip(lean["models"], ref["models"]):
            assert r1 == r2 and all(_same(w1[v], w2[v]) for v in model.VOICES)
        if step:
            assert lean["fits"]["reused"] >= 1                        # earlier refits come from the cache
        for a in bars:                                                # layout 2: no X.bin, and X bit for bit the same
            assert not os.path.exists(os.path.join(str(tmp_path), "test", a, "X.bin"))
            assert isinstance(lean["X"][a], evcache.FeatureRows) and lean["X"][a].shape == ref["X"][a].shape
            assert _bits(lean["X"][a]) == _bits(ref["X"][a])
            assert _bits(lean["odds"][a]) == _bits(ref["odds"][a])
            assert _bits(lean["probs"][a].arr) == _bits(ref["probs"][a][lo:])
        assert _bits(lean["trust"].arr) == _bits(ref["trust"][lo:])
        b1 = dict((a, _book(lean, a, lo, n)) for a in bars)           # the decisions: the same trades, the same book
        b2 = dict((a, _book(ref, a, lo, n)) for a in bars)
        for a in bars:
            assert b1[a]["trades"].equals(b2[a]["trades"]) and len(b1[a]["trades"]) > 0
            assert json.dumps(b1[a]["state"], sort_keys=True, default=str) == json.dumps(b2[a]["state"], sort_keys=True, default=str)
        st1 = backtest.store_from(lean, b1, (lo, n))
        st2 = backtest.store_from(ref, b2, (lo, n))
        for i in (lo, n - 2, n - 1):
            for a in bars:
                assert _same(st1["X"][a][i], st2["X"][a][i]) and _same(st1["probs"][a][i], st2["probs"][a][i])
                e1, e2 = journal.entry(st1, a, i), journal.entry(st2, a, i)   # every journal field of the session
                assert set(e1) == set(e2) and e1["decision"] == e2["decision"] and e1.get("odds") == e2.get("odds")
                assert e1.get("cards") and e1.get("data") and (i == lo or "odds" in e1)       # (full entries)
                assert json.dumps(e1, sort_keys=True, default=str) == json.dumps(e2, sort_keys=True, default=str)
            assert _same(st1["trust"][i], st2["trust"][i])
        from engine15 import shadows
        for a in bars:
            assert _same(shadows.h5_odds(lean, a), shadows.h5_odds(ref, a))
    # the layout before 17 Nov 2026 kept X in X.bin: the same think stage on such a file finds every refit of the
    # walk above under the same key (a key is a hash of the exact training bytes) and gives the same calls
    old_X = dict((a, _old_layout_X(os.path.join(str(tmp_path), "layout1", a, "X.bin"), ref["X"][a], n)) for a in bars)
    fits_old = os.path.join(str(tmp_path), "layout1", "fits")
    shutil.copytree(os.path.join(str(tmp_path), "test", "fits"), fits_old)
    names = sorted(os.listdir(fits_old))
    floor_idx = int(lean["times"].searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    probs, models, frep = leanprep.walk_forward_cached(old_X, lean["ready"], lean["y"], cfg, lo, min(floor_idx, lo), n, fits_old)
    assert frep == {"refits": 0, "reused": len(lean["models"])} and sorted(os.listdir(fits_old)) == names
    for a in bars:
        assert _bits(old_X[a]) == _bits(lean["X"][a])
        assert _bits(probs[a].arr) == _bits(lean["probs"][a].arr)
    for (s1, w1, r1), (s2, w2, r2) in zip(models, lean["models"]):
        assert s1 == s2 and r1 == r2 and all(_bits(w1[v]) == _bits(w2[v]) for v in model.VOICES)
    del old_X, probs


def _frame(n=500, seed=0):
    """Readings of every kind the store keeps, with the awkward values: NaN, -0.0, inf, an all-NaN column, text."""
    rng = np.random.RandomState(seed)
    fr = pd.DataFrame({"a8": rng.normal(size=n), "b4": rng.normal(size=n).astype(np.float32), "flag": rng.rand(n) < 0.3,
                       "cnt": rng.randint(-5, 6, n).astype(np.int64), "empty8": np.full(n, np.nan),
                       "empty4": np.full(n, np.nan, dtype=np.float32), "txt": np.where(rng.rand(n) < 0.5, "up", "down"),
                       "other": rng.normal(size=n) * 1e-300})
    fr.loc[fr.index[::7], "a8"] = np.nan
    fr.loc[fr.index[::11], "b4"] = np.nan
    fr.loc[3, "a8"], fr.loc[5, "a8"], fr.loc[6, "a8"], fr.loc[9, "b4"] = -0.0, np.inf, -np.inf, np.float32(-0.0)
    return fr


FEATS = ["b4", "empty8", "flag", "a8", "cnt", "empty4"]


def _matrix(fr):
    """evidence.matrix's own expression, on this frame's feature columns."""
    return fr[FEATS].astype(float).fillna(0.0).values


def _store(path, fr, upto=None, spare=50):
    st = evcache.AssetStore(str(path))
    st.create(list(fr.columns), evcache.kinds_of(fr), [str(d) for d in fr.dtypes], len(FEATS), len(fr) + spare, features=FEATS)
    upto = len(fr) if upto is None else upto
    X, rd = _matrix(fr), fr["a8"].notna().values
    for s, e in ((0, min(300, upto)), (min(300, upto), upto)):       # two writes, like a build in pieces
        if e > s:
            st.write(s, np.arange(s, e, dtype=np.int64), fr.iloc[s:e], X[s:e], rd[s:e])
    st.save_meta()
    return st


def test_feature_rows_is_the_matrix_the_store_no_longer_keeps(tmp_path):
    fr = _frame()
    n, X = len(fr), _matrix(fr)
    st = _store(tmp_path / "s", fr)
    assert sorted(os.listdir(str(tmp_path / "s"))) == ["b1.bin", "code.bin", "f4.bin", "f8.bin", "i8.bin", "meta.json",
                                                      "ready.bin", "times.bin"]              # no X.bin
    Xs = st.X()
    assert isinstance(Xs, evcache.FeatureRows) and Xs.shape == X.shape and len(Xs) == n and Xs.dtype == np.float64
    assert _bits(Xs) == _bits(X)                                      # every bit: -0.0 stays -0.0, inf stays inf, NaN -> 0.0
    assert np.signbit(np.asarray(Xs)[3, 3]) and np.isinf(np.asarray(Xs)[5, 3]) and not np.isnan(np.asarray(Xs)).any()
    assert st.frame(pd.RangeIndex(n)).equals(fr) and st.frame(pd.RangeIndex(n)).dtypes.equals(fr.dtypes)
    rows = np.array([400, 1, 5, 5, 499, 0])
    mask = np.asarray(fr["flag"])
    for got, want in ((Xs[10], X[10]), (Xs[-1], X[-1]), (Xs[np.int64(7)], X[7]), (Xs[5:40], X[5:40]), (Xs[5:40][3:10], X[8:15]),
                      (Xs[:0], X[:0]), (Xs[490:9999], X[490:]), (Xs[::3], X[::3]), (Xs[rows], X[rows]), (Xs[list(rows)], X[rows]),
                      (Xs[-rows - 1], X[-rows - 1]), (Xs[mask], X[mask]), (Xs[[]], X[[]]), (Xs[5:40, [0, 3]], X[5:40][:, [0, 3]]),
                      (Xs[:, 3], X[:, 3]), (Xs[7, 2], X[7, 2]), (Xs[7, 1:4], X[7, 1:4]), (Xs[2:9, 1:4], X[2:9, 1:4]),
                      (Xs[rows, 3], X[rows, 3]), (Xs[5:40][:, [0, 3]], X[5:40][:, [0, 3]])):
        assert np.asarray(got).shape == np.asarray(want).shape and _bits(got) == _bits(want)
    assert isinstance(Xs[5:40], evcache.FeatureRows)                  # a slice reads nothing until it is asked
    assert _bits(np.asarray(Xs[2:9], dtype=np.float32)) == _bits(X[2:9].astype(np.float32))
    assert _bits(Xs[2:9].astype(np.float32)) == _bits(X[2:9].astype(np.float32))
    for bad in (n, -n - 1, [0, n], np.array([0.5])):
        with pytest.raises(IndexError):
            Xs[bad]
    with pytest.raises(IndexError):
        Xs[rows, [0, 1]]
    # a write whose matrix is not what the stored readings give back is refused (the smallest possible difference)
    X2 = X.copy()
    X2[450, 3] = np.nextafter(X2[450, 3], 1.0)
    with pytest.raises(evcache.StoreError):
        st.write(400, np.arange(400, n, dtype=np.int64), fr.iloc[400:], X2[400:], fr["a8"].notna().values[400:])
    # a "no read" column that starts reading in rows rewritten in the middle of the store: every other row stays NaN
    st = _store(tmp_path / "s2", fr)                                  # (a folder of its own each time: Windows cannot
    fr2 = fr.copy()                                                   # remove files this test still has mapped)
    fr2.loc[100:102, "empty8"] = [1.5, -2.5, 3.5]
    st.write(100, np.arange(100, 103, dtype=np.int64), fr2.iloc[100:103], _matrix(fr2)[100:103], fr2["a8"].notna().values[100:103],
             overwrite=True)
    assert st.meta["n"] == n
    assert st.frame(pd.RangeIndex(n)).equals(fr2) and _bits(st.X()) == _bits(_matrix(fr2))
    st.save_meta()
    st.close()
    # a store is read only if its layout is this one and every file has the size its meta says
    for k, spoil in enumerate(("longer", "missing", "layout 1")):
        p = str(tmp_path / ("s%d" % (k + 3)))
        st = _store(p, fr)
        st.close()
        assert evcache.AssetStore(p).load()
        if spoil == "longer":                                         # a crash while the files were being enlarged
            with open(os.path.join(p, "f8.bin"), "ab") as fh:
                fh.write(bytes(8))
        elif spoil == "missing":
            os.rename(os.path.join(p, "ready.bin"), os.path.join(p, "ready.bin.old"))
        else:                                                         # the layout before 17 Nov 2026
            st.meta["version"] = 1
            st.save_meta()
        assert not evcache.AssetStore(p).load()


def test_store_grows_and_keeps_its_rows(tmp_path):
    fr = _frame(900, seed=4)
    st = _store(tmp_path / "g", fr, upto=600, spare=-250)             # room for 650 rows only
    X, rd = _matrix(fr), fr["a8"].notna().values
    st.write(600, np.arange(600, 900, dtype=np.int64), fr.iloc[600:], X[600:], rd[600:])   # grows the files
    st.save_meta()
    assert st.meta["cap"] >= 900 and st.meta["n"] == 900
    st2 = evcache.AssetStore(str(tmp_path / "g"))
    assert st2.load() and st2.frame(pd.RangeIndex(900)).equals(fr) and _bits(st2.X()) == _bits(X)
    assert _same(st2.ready(), rd) and _same(st2.times_ms(), np.arange(900))
    assert not [f for f in os.listdir(str(tmp_path / "g")) if f.endswith(".old")]
    st2.close()


def test_older_and_half_written_stores_are_built_again(tmp_path, monkeypatch):
    bars = {"BTCUSDT": make_bars(n=3000, seed=3)}
    cfg, root, a = _cfg(bars), str(tmp_path), "BTCUSDT"
    want = evidence.build(bars)[a]
    Xw, rdw = evidence.matrix(want)
    gpath, spath = os.path.join(root, "g", "group.json"), os.path.join(root, "g", a)
    calls = []

    def build(bars_, funding=None, live=None, rows=None):             # the rows of the one real build above (that
        calls.append(1)                                               # build(rows=...) equals them is the first test
        if calls[0] is not None and len(calls) >= calls[0]:           # of this file): the store is built eight times
            raise KeyboardInterrupt("killed in the middle of a build")
        return {a: want.iloc[rows].copy()}
    calls.append(None)                                                # calls[0]: the call that dies (None: none does)
    monkeypatch.setattr(evidence, "build", build)

    def check(expect_rebuilt):
        stores, common, rep = evcache.update("g", bars, {}, {}, cfg, log=lambda *_: None, root=root)
        st = stores[a]
        assert rep["rebuilt"] is expect_rebuilt
        fr = st.frame(common)
        assert fr.dtypes.equals(want.dtypes) and fr.equals(want)
        assert _bits(st.X()) == _bits(Xw) and _same(st.ready(), rdw)
        assert not os.path.exists(os.path.join(spath, "X.bin")) and st.meta["version"] == evcache.LAYOUT
        with open(gpath, encoding="utf-8") as fh:
            assert json.load(fh).get("sig") == evcache.code_signature()
        del fr
        st.close()

    check(True)                                                       # a first build
    check(False)                                                      # and it is trusted afterwards
    # 1. a store of the older layout under the SAME signature: X.bin beside the readings, meta version 1
    with open(os.path.join(spath, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["version"] = 1
    del meta["features"]
    with open(os.path.join(spath, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    with open(os.path.join(spath, "X.bin"), "wb") as fh:
        fh.truncate(meta["cap"] * meta["n_x"] * 8)
    check(True)                                                       # built again, and the old X.bin is gone
    check(False)
    # 2. a crash in the middle of a build: the group says "building" (no signature), the next step starts over
    monkeypatch.setattr(evcache, "CHUNK_ROWS", 1000)
    os.remove(os.path.join(spath, "times.bin"))                       # (something that makes the store build again)
    calls[0] = len(calls) + 3                                         # the third build from here dies: the first only
    with pytest.raises(KeyboardInterrupt):                            # looks at the last rows, the second is rows 0-999
        evcache.update("g", bars, {}, {}, cfg, log=lambda *_: None, root=root)
    calls[0] = None
    with open(gpath, encoding="utf-8") as fh:
        assert json.load(fh) == {"building": True}
    half = evcache.AssetStore(spath)
    assert half.load() and half.meta["n"] == 1000                     # a readable store of 1,000 rows of 3,000 ...
    half.close()
    check(True)                                                       # ... that is not trusted
    check(False)
    # 3. a file that has not the size its meta says (a crash while the files were being enlarged)
    with open(os.path.join(spath, "f4.bin"), "ab") as fh:
        fh.write(bytes(4096))
    check(True)
    check(False)
