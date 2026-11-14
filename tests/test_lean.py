# -*- coding: utf-8 -*-
"""The live step's lean think stage (evcache.py, leanprep.py) gives exactly backtest.prepare's numbers.

    py -3 -m pytest tests/test_lean.py -q
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, evidence, leanprep, model  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
from test_engine import make_bars  # noqa: E402


def _cfg(bars):
    end = min(df.index[-1] for df in bars.values())
    return dict(CFG, assets=tuple(bars), birth=str((end - pd.Timedelta(days=240)).date()), voting=voting_for("crypto"))


def _same(a, b):
    return np.array_equal(np.asarray(a), np.asarray(b), equal_nan=True)


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
        st1 = backtest.store_from(lean, {}, (lo, n))
        st2 = backtest.store_from(ref, {}, (lo, n))
        for i in (lo, n - 2, n - 1):
            for a in bars:
                assert _same(st1["X"][a][i], st2["X"][a][i]) and _same(st1["probs"][a][i], st2["probs"][a][i])
            assert _same(st1["trust"][i], st2["trust"][i])
        from engine15 import shadows
        for a in bars:
            assert _same(shadows.h5_odds(lean, a), shadows.h5_odds(ref, a))
