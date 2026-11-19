# -*- coding: utf-8 -*-
"""The evidence store's once-a-day check (evcache.update, check=True) writes what changed, not the files.

19 Nov 2026: the crypto worker spent 43 minutes in disk wait writing ~292 GB. The daily check rewrote
every run of changed rows with its own AssetStore.write(), and every write() ended in close(), which
flushes every memory map of the asset. The files are column-major (slot, cap), so a run of a few rows
dirties one page in EVERY column of every file, and each run flushed them again: scattered changed rows
cost (runs x columns x 4 KB) plus a flush of every file per run. Now the changed rows of a piece go in
one write_rows() (one pass, one bit-for-bit check, one flush), and a check that would still write too
much or take too long stops for the day.

The meter below counts what the operating system would write back: the pages each memory-map
assignment dirties, written once per flush of that file (msync / FlushViewOfFile write dirty pages only).

    py -3 -m pytest tests/test_daily_check.py -q
"""
import json
import mmap
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import evcache, evidence  # noqa: E402
from engine15.config import CFG  # noqa: E402

N8, N4, NB, NI = 200, 60, 10, 10          # a realistic mix (the real stores: ~440 features, ~550 columns)
ASSETS = ("BTCUSDT", "ETHUSDT")


def _bars(n, seed):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    c = 100 + rng.normal(size=n).cumsum()
    return pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": rng.rand(n)}, index=idx)


def _truth(n, seed):
    """Readings of every kind the store keeps, with the awkward values (NaN, -0.0, inf, None, text)."""
    rng = np.random.RandomState(seed)
    cols = {}
    for i in range(N8):
        v = rng.normal(size=n)
        v[rng.rand(n) < 0.05] = np.nan
        cols["f8_%d" % i] = v
    for i in range(N4):
        v = rng.normal(size=n).astype(np.float32)
        v[rng.rand(n) < 0.05] = np.nan
        cols["f4_%d" % i] = v
    for i in range(NB):
        cols["b_%d" % i] = rng.rand(n) < 0.3
    for i in range(NI):
        cols["i_%d" % i] = rng.randint(-5, 6, n).astype(np.int64)
    cols["empty8"] = np.full(n, np.nan)                               # "no read": starts reading in old rows later
    cols["empty4"] = np.full(n, np.nan, dtype=np.float32)
    early = np.full(n, np.nan)                                        # reads only early on: "no read" in the tail,
    early[: n // 3] = rng.normal(size=n // 3)                         # promoted to a slot during the build
    cols["early8"] = early
    obj = np.where(rng.rand(n) < 0.5, "up", "down").astype(object)
    obj[::13], obj[5::17] = None, np.nan
    cols["txt_obj"] = obj
    fr = pd.DataFrame(cols)
    fr["txt_str"] = pd.Series(np.where(rng.rand(n) < 0.5, "a", "b"), dtype="str")
    fr.loc[fr.index[::19], "txt_str"] = np.nan
    fr.loc[3, "f8_0"], fr.loc[5, "f8_1"], fr.loc[6, "f8_1"], fr.loc[9, "f4_0"] = -0.0, np.inf, -np.inf, np.float32(-0.0)
    fr.loc[fr.index[::23], "f8_2"] = -0.0
    return fr


FEATS = ["f8_%d" % i for i in range(N8)] + ["f4_%d" % i for i in range(N4)] + ["b_%d" % i for i in range(NB)] + \
    ["i_%d" % i for i in range(NI)] + ["empty8", "empty4", "early8"]


class Group:
    """A synthetic market group: evidence.build is the rows of `truth` (what build(rows=...) means)."""

    def __init__(self, tmp_path, monkeypatch, n=20000, root="root"):
        self.n, self.root, self.logs, self.builds = n, str(tmp_path / root), [], []
        self.bars = dict((a, _bars(n, k)) for k, a in enumerate(ASSETS))
        self.truth = dict((a, _truth(n, 10 + k)) for k, a in enumerate(ASSETS))
        birth = str(self.bars[ASSETS[0]].index[1000].date())
        self.cfg = dict(CFG, birth=birth, train_floor=birth, train_step=16)
        monkeypatch.setattr(evidence, "FEATURES", FEATS)
        monkeypatch.setattr(evidence, "REQUIRED", ["f8_3"])
        monkeypatch.setattr(evidence, "build", self._build)
        self.cms = np.asarray(self.bars[ASSETS[0]].index.as_unit("ms").asi8, dtype=np.int64)
        self.R = int(self.bars[ASSETS[0]].index.searchsorted(self.bars[ASSETS[0]].index[-1] - pd.Timedelta(days=evcache.REFRESH_DAYS)))
        self.birth_idx = 1000 - 1000 % 96

    def _build(self, bars, funding=None, live=None, rows=None):
        self.builds.append(np.asarray(rows))
        return dict((a, self.truth[a].iloc[rows].copy()) for a in bars)

    def update(self, force_check=False, root=None):
        return evcache.update("g", self.bars, {}, {}, self.cfg, log=self.logs.append, root=root or self.root,
                              force_check=force_check)

    def assert_stored(self, stores, truth=None):
        for a in ASSETS:
            want = (truth or self.truth)[a]
            st = stores[a]
            fr = st.frame(pd.RangeIndex(self.n))
            assert fr.dtypes.equals(want.dtypes) and fr.equals(want)
            X, rd = evidence.matrix(want)
            assert np.ascontiguousarray(np.asarray(st.X())).tobytes() == np.ascontiguousarray(X).tobytes()
            assert np.array_equal(st.ready(), rd) and np.array_equal(st.times_ms(), self.cms)


class Meter:
    """Pages dirtied through memory maps and written back at each flush; write calls."""

    def __init__(self, monkeypatch):
        self.dirty, self.flushed, self.flushes, self.writes, self.batches = {}, 0, 0, 0, 0
        set0, flush0 = np.memmap.__setitem__, np.memmap.flush
        w0, wr0 = evcache.AssetStore.write, evcache.AssetStore.write_rows
        meter = self

        def setitem(mm, key, value):
            set0(mm, key, value)
            if mm.mode in ("r+", "w+"):
                assert isinstance(mm.base, mmap.mmap), "the meter only knows whole-file maps"
                meter._touch(mm, key)

        def flush(mm):
            flush0(mm)
            meter.flushes += 1
            meter.flushed += len(meter.dirty.pop(mm.filename, ())) * evcache.PAGE

        def write(st, *a, **k):
            meter.writes += 1
            return w0(st, *a, **k)

        def write_rows(st, rows, *a, **k):
            meter.batches += 1 if len(rows) else 0
            return wr0(st, rows, *a, **k)
        monkeypatch.setattr(np.memmap, "__setitem__", setitem)
        monkeypatch.setattr(np.memmap, "flush", flush)
        monkeypatch.setattr(evcache.AssetStore, "write", write)
        monkeypatch.setattr(evcache.AssetStore, "write_rows", write_rows)

    @staticmethod
    def _ix(k, n):
        if isinstance(k, slice):
            return np.arange(*k.indices(n))
        return np.atleast_1d(np.asarray(k, dtype=np.int64))

    def _touch(self, mm, key):
        if mm.ndim == 1:
            flat = self._ix(key, mm.shape[0])
        else:
            slot, rk = key
            flat = int(slot) * mm.shape[1] + self._ix(rk, mm.shape[1])
        pages = np.unique((mm.offset + flat * mm.itemsize) // evcache.PAGE)
        self.dirty.setdefault(mm.filename, set()).update(pages.tolist())

    def reset(self):
        self.dirty, self.flushed, self.flushes, self.writes, self.batches = {}, 0, 0, 0, 0

    def bytes(self):
        """Everything written back, flushed or not yet (the system writes those later anyway)."""
        return self.flushed + sum(len(p) for p in self.dirty.values()) * evcache.PAGE


def _runs(rows):
    out = []
    for r in rows:
        if out and r == out[-1][1]:
            out[-1][1] = r + 1
        else:
            out.append([r, r + 1])
    return out


def test_daily_check_writes_the_changed_pages_once_not_every_file_per_run(tmp_path, monkeypatch):
    monkeypatch.setattr(evcache, "CHUNK_ROWS", 6000)
    g = Group(tmp_path, monkeypatch)
    stores, common, rep = g.update()
    assert rep["rebuilt"]
    for st in stores.values():
        st.close()
    # late data moves scattered old rows (every 50th session since the birth date) and a "no read" column
    # starts reading in a few of them
    hit = np.arange(g.birth_idx + 7, g.R, 50)
    old_truth = dict((a, df.copy()) for a, df in g.truth.items())
    for a in ASSETS:
        g.truth[a].loc[hit, "f8_5"] = g.truth[a].loc[hit, "f8_5"].fillna(0.0) + 1.0
        g.truth[a].loc[hit[::40], "empty8"] = 2.5
    shutil.copytree(os.path.join(g.root, "g"), os.path.join(str(tmp_path / "before"), "g"))
    meter = Meter(monkeypatch)
    # BEFORE (the code until 19 Nov 2026): one write(..., overwrite=True) per run of changed rows, each ending in a
    # flush of every file. On a copy of the same store, for one asset.
    a = ASSETS[0]
    old = evcache.AssetStore(os.path.join(str(tmp_path / "before"), "g", a))
    assert old.load()
    fr = g.truth[a]
    X, rd = evidence.matrix(fr)
    runs = _runs(hit.tolist())
    t0 = time.perf_counter()
    for r0, r1 in runs:
        old.write(r0, g.cms[r0:r1], fr.iloc[r0:r1], X[r0:r1], rd[r0:r1], overwrite=True)
    before = {"writes": meter.writes, "flushes": meter.flushes, "bytes": meter.bytes(), "s": time.perf_counter() - t0}
    old.save_meta()
    old.close()
    # AFTER: the daily check itself, both assets (and the refresh window, which every step rewrites)
    meter.reset()
    t0 = time.perf_counter()
    stores, common, rep = g.update(force_check=True)
    after = {"batches": meter.batches, "writes": meter.writes, "flushes": meter.flushes, "bytes": meter.bytes(),
             "s": time.perf_counter() - t0}
    print("\nchanged rows per asset %d in %d runs; before (one asset): %s; after (two assets + refresh): %s"
          % (len(hit), len(runs), before, after))
    assert rep["checked"] and not rep.get("check_stopped") and rep["changed_rows"] == dict((x, len(hit)) for x in ASSETS)
    g.assert_stored(stores)                                           # the same readings, X bit for bit
    want = np.arange(g.birth_idx, g.n)
    starts = np.arange(0, len(want), evcache.CHUNK_ROWS)
    pieces, refresh_pieces = len(starts), sum(int(want[min(s + evcache.CHUNK_ROWS, len(want)) - 1] >= g.R) for s in starts)
    assert after["batches"] <= pieces * len(ASSETS)                   # one write per piece and asset, not per run
    assert after["writes"] == refresh_pieces * len(ASSETS)            # (+ the refresh window's write per piece)
    assert before["writes"] == len(runs) and len(runs) > 300
    # the bytes: the before path wrote more for ONE asset than the check now writes for both, by a wide margin
    assert after["bytes"] * 3 < before["bytes"]
    assert before["bytes"] >= len(runs) * (N8 + N4 + NB + NI) * evcache.PAGE * 0.9    # every column's page per run
    # what the check now writes is bounded by the pages of the checked rows (each once) and the refresh
    slots = N8 + N4 + NB + NI + 6
    bound = sum(stores[x].dirty_bytes(want) + (pieces + 2) * slots * evcache.PAGE + g.n * 8 for x in ASSETS)
    assert after["bytes"] <= bound
    # the store "before" holds exactly the same readings: the fix changes how the rows are written, not what
    st_b = evcache.AssetStore(os.path.join(str(tmp_path / "before"), "g", a))
    assert st_b.load()
    assert st_b.frame(pd.RangeIndex(g.n)).equals(stores[a].frame(pd.RangeIndex(g.n)))
    assert np.asarray(st_b.X()).tobytes() == np.asarray(stores[a].X()).tobytes()
    st_b.close()
    for st in stores.values():
        st.close()
    del old_truth


def test_unchanged_rows_are_not_reported_changed(tmp_path, monkeypatch):
    """NaN, -0.0, inf, None / NaN text, a promoted column: a check over identical readings finds nothing."""
    g = Group(tmp_path, monkeypatch, n=12000)
    stores, common, rep = g.update()
    for st in stores.values():
        st.close()
    meter = Meter(monkeypatch)
    stores, common, rep = g.update(force_check=True)
    assert rep["checked"] and rep["changed_rows"] == dict((a, 0) for a in ASSETS)
    assert meter.batches == 0 and meter.writes == len(ASSETS)         # only the refresh window
    g.assert_stored(stores)
    for st in stores.values():
        st.close()


def _changed_everywhere(g):
    """Old rows changed in every piece of the check, and a row inside the refresh window."""
    rows = np.arange(g.birth_idx + 3, g.R, 97)
    for a in ASSETS:
        g.truth[a].loc[rows, "f8_7"] = 9.0
        g.truth[a].loc[g.n - 5, "f8_7"] = -9.0
    return rows


@pytest.mark.parametrize("budget", ["bytes", "seconds"])
def test_daily_check_budget_stops_for_the_day_and_the_step_goes_on(tmp_path, monkeypatch, budget):
    monkeypatch.setattr(evcache, "CHUNK_ROWS", 3000)
    g = Group(tmp_path, monkeypatch, n=12000)
    stores, common, rep = g.update()
    for st in stores.values():
        st.close()
    before = dict((a, df.copy()) for a, df in g.truth.items())
    rows = _changed_everywhere(g)
    if budget == "bytes":
        monkeypatch.setattr(evcache, "CHECK_MAX_BYTES", 1 << 20)       # less than the first piece's changed pages
    else:
        monkeypatch.setattr(evcache, "CHECK_MAX_SECONDS", -1)          # any time at all is over it
    g.builds.clear()
    stores, common, rep = g.update(force_check=True)
    lines = [x for x in g.logs if "daily check stopped" in x]
    assert len(lines) == 1 and lines[0].startswith("g: daily check stopped (BTCUSDT: ") and \
        lines[0].endswith("), will retry tomorrow")
    assert ("GB to write" in lines[0]) if budget == "bytes" else ("s comparing and writing" in lines[0])
    assert rep["check_stopped"] and rep["checked"] and not rep["rebuilt"]
    with open(os.path.join(g.root, "g", "group.json"), encoding="utf-8") as fh:
        gm = json.load(fh)
    assert gm["checked_day"] == time.strftime("%Y-%m-%d", time.gmtime()) and gm["sig"] == evcache.code_signature()
    # no old row was rewritten, the refresh window was (the step goes on), and after the stop only the
    # piece holding the refresh rows was computed
    expect = dict((a, df.copy()) for a, df in before.items())
    for a in ASSETS:
        expect[a].iloc[g.R:] = g.truth[a].iloc[g.R:]
    g.assert_stored(stores, expect)
    assert g.builds[0][0] == g.birth_idx and g.builds[0][-1] < g.R and len(g.builds[0]) == evcache.CHUNK_ROWS
    assert np.array_equal(np.concatenate(g.builds[1:]), np.arange(g.R, g.n))
    for st in stores.values():
        st.close()
    # the same day: no check; the next day (forced here) with the budget back: everything is checked and fixed
    stores, common, rep = g.update()
    assert not rep["checked"]
    for st in stores.values():
        st.close()
    monkeypatch.setattr(evcache, "CHECK_MAX_BYTES", 2 << 30)
    monkeypatch.setattr(evcache, "CHECK_MAX_SECONDS", 300)
    stores, common, rep = g.update(force_check=True)
    assert not rep.get("check_stopped") and rep["changed_rows"] == dict((a, len(rows)) for a in ASSETS)
    g.assert_stored(stores)
    for st in stores.values():
        st.close()
