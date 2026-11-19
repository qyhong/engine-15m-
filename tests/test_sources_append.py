# -*- coding: utf-8 -*-
"""The source files are only ever appended to: the stored bytes never move (flows._store, used by flows and cryptox).

pandas 3.0's default CSV parser lands some 17-digit floats 1 ULP off; the old full rewrite wrote that back and nudged
old values on every daily append. These tests pin: the old bytes are untouched by an append, values survive repeated
appends exactly, a key in the middle rewrites from an exact read, a failed append leaves the old file whole.

    py -3 -m pytest tests/test_sources_append.py -q        (from the project folder)
"""
import hashlib
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import cryptox as cx  # noqa: E402
from engine15.sources import flows  # noqa: E402

A = "BTCUSDT"
BAR, DAY = flows.BAR_MS, flows.DAY_MS
T0 = 1_600_000_000_000 // BAR * BAR
# 17-significant-digit values, and values pandas 3.0's default parser reads 1 ULP off (found by a random probe)
TRICKY = [0.30000000000000004, 1.0000000000000002, 123456789.12345679, 4.0973523936194694e-06, 912755.5772777217,
          0.005436249914654229, 8132.702392002724, 2.2250738585072014e-308, 1.7976931348623157e+308, 0.1]


def metrics_rows(start, n, seed=0):
    rng = np.random.default_rng(seed)
    cols = flows.METRICS_COLS
    ts = T0 + (start + np.arange(n)) * BAR
    d = pd.DataFrame({"ts_ms": ts.astype("int64")})
    for i, c in enumerate(cols[1:-1]):
        v = rng.random(n) * 10.0 ** rng.integers(-6, 12, n)
        d[c] = v
    vals = np.resize(np.array(TRICKY), n)
    d["oi"] = vals
    d.loc[d.index[1::7], "taker_ls"] = np.nan                       # gaps are stored as empty fields
    d["known_ms"] = (ts + DAY).astype("int64")
    return d[cols]


def onchain_rows(start, n, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=start + n, freq="D")[start:].strftime("%Y-%m-%d")
    d = pd.DataFrame({"date": list(dates)})
    for c in flows.CM_METRICS:
        d[c] = rng.random(n) * 10.0 ** rng.integers(-3, 10, n)
    d[flows.CM_METRICS[0]] = np.resize(np.array(TRICKY), n)
    d["known_ms"] = (flows._day_ms(d["date"]) + 2 * DAY).astype("int64")
    return d[flows.CM_COLS]


def raw(path):
    with open(path, "rb") as fh:
        return fh.read()


def add(kind, src, rows):
    """What update() does: load (plain read, as the live code does) then _extend."""
    return flows._extend(kind, A, src, flows.load_source(kind, A, src), rows)


def test_append_leaves_the_stored_bytes_untouched_and_matches_a_full_write(tmp_path):
    src = str(tmp_path)
    path = flows.path_for("metrics", A, src)
    add("metrics", src, metrics_rows(0, 500))
    before = raw(path)
    digest = hashlib.sha256(before).hexdigest()
    n = add("metrics", src, metrics_rows(500, 300, seed=5))
    after = raw(path)
    assert n == 800
    assert hashlib.sha256(after[:len(before)]).hexdigest() == digest           # the old prefix, byte for byte
    assert after[len(before):].count(os.linesep.encode()) == 300               # only the new lines were added
    assert not os.path.exists(path + ".tmp")
    # the appended text is exactly what one full to_csv of the whole table writes
    full = str(tmp_path / "full.csv")
    flows.load_source("metrics", A, src, exact=True).to_csv(full, index=False)
    assert raw(full) == after


def test_ten_appends_keep_17_digit_values_exact(tmp_path):
    for kind, make in (("metrics", metrics_rows), ("onchain", onchain_rows)):
        src = str(tmp_path / kind)
        path = flows.path_for(kind, A, src)
        first = make(0, 60)
        add(kind, src, first)
        original = raw(path)
        for i in range(10):
            prev = raw(path)
            add(kind, src, make(60 + 20 * i, 20, seed=10 + i))
            assert raw(path).startswith(prev) and raw(path).startswith(original)
        got = flows.load_source(kind, A, src, exact=True)
        key = flows.FILES[kind][0]
        got = got[got[key].isin(set(first[key]))].reset_index(drop=True)
        num = [c for c in flows.FILES[kind] if c not in ("ts_ms", "date", "known_ms")]
        a, b = got[num].to_numpy(), first[num].to_numpy(dtype=float)
        assert ((a == b) | (np.isnan(a) & np.isnan(b))).all()                   # bit for bit, not "close"
        assert len(flows.load_source(kind, A, src)) == 260


def test_exact_read_is_exact_on_this_pandas(tmp_path):
    path = str(tmp_path / "x.csv")
    rng = np.random.default_rng(3)
    vals = np.concatenate([np.array(TRICKY), rng.random(5000) * 10.0 ** rng.integers(-6, 12, 5000)])
    pd.DataFrame({"x": vals}).to_csv(path, index=False)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")                                          # no deprecation noise either
        got = flows.read_csv_exact(path)["x"].to_numpy()
    assert (got == vals).all()


def test_a_key_in_the_middle_rewrites_and_every_untouched_line_is_byte_identical(tmp_path):
    src = str(tmp_path)
    path = flows.path_for("metrics", A, src)
    rows = metrics_rows(0, 400)
    add("metrics", src, rows.drop(index=200))                                  # a hole at row 200
    before = raw(path).split(os.linesep.encode())
    n = add("metrics", src, rows.loc[[200]])                                   # lands in the middle: full rewrite
    after = raw(path).split(os.linesep.encode())
    assert n == 400 and len(after) == len(before) + 1
    assert after[:201] == before[:201] and after[202:] == before[201:]          # every old line exactly as it was
    got = flows.load_source("metrics", A, src, exact=True)
    assert (np.diff(got["ts_ms"]) == BAR).all()
    assert not os.path.exists(path + ".tmp")


def test_cryptox_appends_too(tmp_path):
    src = str(tmp_path)
    path = cx.path_for("bybit_oi", A, src)
    f = pd.DataFrame({"ts_ms": (T0 + np.arange(50) * BAR).astype("int64"), "oi": np.resize(np.array(TRICKY), 50),
                      "known_ms": (T0 + np.arange(50) * BAR + BAR).astype("int64")})
    cx._extend("bybit_oi", A, src, cx.load_source("bybit_oi", A, src), f.iloc[:30])
    before = raw(path)
    n = cx._extend("bybit_oi", A, src, cx.load_source("bybit_oi", A, src), f)  # the 30 stored are skipped
    assert n == 50 and raw(path).startswith(before) and len(raw(path)) > len(before)
    assert (cx.load_source("bybit_oi", A, src)["oi"].to_numpy() == f["oi"].to_numpy()).all()


def test_a_failed_append_leaves_the_old_file_whole(tmp_path, monkeypatch):
    src = str(tmp_path)
    path = flows.path_for("metrics", A, src)
    add("metrics", src, metrics_rows(0, 100))
    before = raw(path)

    real_open = open

    class HalfWriter:                       # writes half the text, then the machine "dies"
        def __init__(self, fh):
            self.fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.fh.close()

        def write(self, b):
            self.fh.write(b[:len(b) // 2])
            self.fh.flush()
            raise KeyboardInterrupt("simulated crash mid-append")

    def fake_open(p, mode="r", *a, **k):
        fh = real_open(p, mode, *a, **k)
        return HalfWriter(fh) if mode == "ab" else fh

    monkeypatch.setattr(flows, "open", fake_open, raising=False)
    with pytest.raises(KeyboardInterrupt):
        add("metrics", src, metrics_rows(100, 50, seed=4))
    monkeypatch.undo()
    assert raw(path) == before and not os.path.exists(path + ".tmp")        # the old file, whole; no half line
    assert len(flows.load_source("metrics", A, src)) == 100

    def no_swap(tmp, p):
        raise PermissionError("held by a reader")
    monkeypatch.setattr(flows, "_swap_in", no_swap)
    with pytest.raises(PermissionError):
        add("metrics", src, metrics_rows(100, 50, seed=4))
    monkeypatch.undo()
    assert raw(path) == before and not os.path.exists(path + ".tmp")
    assert add("metrics", src, metrics_rows(100, 50, seed=4)) == 150          # the next run goes through
    assert raw(path).startswith(before)


def test_a_cut_or_foreign_file_is_rewritten_not_appended_to(tmp_path):
    src = str(tmp_path)
    path = flows.path_for("metrics", A, src)
    add("metrics", src, metrics_rows(0, 20))
    good = raw(path)
    with open(path, "wb") as fh:                                               # a last line without its line ending
        fh.write(good.rstrip(b"\r\n"))
    assert flows._tail_layout(path, flows.METRICS_COLS) is None
    assert add("metrics", src, metrics_rows(20, 5)) == 25
    assert raw(path).startswith(good) and raw(path).endswith(os.linesep.encode())
    # a file written elsewhere with \n (or \r\n) line endings keeps its own ending when appended to
    for term in (b"\n", b"\r\n"):
        lines = raw(path).replace(b"\r\n", b"\n").split(b"\n")
        with open(path, "wb") as fh:
            fh.write(term.join(lines))
        before = raw(path)
        n = len(flows.load_source("metrics", A, src))
        add("metrics", src, metrics_rows(n, 3, seed=n))
        tail = raw(path)[len(before):]
        assert raw(path).startswith(before) and tail.count(term) == 3 and tail.count(b"\n") == 3
