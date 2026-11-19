# -*- coding: utf-8 -*-
"""evcache -- every session's readings kept on disk, so a live step only adds what is new. PAPER ONLY.

The past does not change: a row of evidence uses only what was known at its close (evidence.py),
so the live step keeps the readings of every session of a market group in
data/evcache/<group>/<asset>/ as memory maps (the operating system pages in only the rows a step
touches; they do not count against the process's own memory) and computes, each step, only:
  * the sessions it has not stored yet,
  * a refresh window (REFRESH_DAYS) for inputs that legitimately arrive late: live reads, funding,
    the daily / weekly source files, the macro tape and the release calendar, the owner's answers,
  * from the first session whose bars, funding or live reads differ from what was stored,
  * once a UTC day, every row the step's learning reads (the training rows since train_floor and
    every session since the birth date), compared with what is stored and rewritten where changed:
    the changed rows of a piece in one write and one flush, and an asset that would write more than
    CHECK_MAX_BYTES or take more than CHECK_MAX_SECONDS stops the group's check until the next day.
Those rows come from evidence.build(..., rows=...), the replay's own code: each reading is still
computed over all history (several have unbounded memory: the seeded EMAs of the weekly trend
score, the support/resistance list), then only the requested rows are kept.

Stored compactly: float64 / float32 columns in their own dtype, a column with no reading in any
stored row is not stored at all (a "no read" filler), text columns as small integer codes plus a
table. The feature matrix X is NOT stored (layout 2, 17 Nov 2026; it was a third of the store):
X is evidence.matrix's ev[FEATURES].astype(float).fillna(0.0), a pure function of the stored
readings, so FeatureRows rebuilds exactly the rows a caller asks for from the stored columns, and
every write checks, bit for bit, that the stored readings give back the matrix evidence.matrix made.
The whole store is rebuilt automatically when the code or the config that makes the readings
changes (a signature of those files and CFG), when its layout is an older one, when a file has not
the size its meta says (a crash while the files were being enlarged) or when its shape no longer
fits. A build that did not finish is never trusted: group.json says "building" until it has.
"""
import gc
import hashlib
import json
import os
import shutil
import time

import numpy as np
import pandas as pd

from .config import CFG, DATA_DIR, ROOT

CACHE_DIR = os.path.join(DATA_DIR, "evcache")
REFRESH_DAYS = 30           # every step recomputes at least this much recent history (late data)
CHUNK_ROWS = 30000          # a first build computes the rows in pieces of this size (memory)
SPARE_COLS = 16             # free column slots per float kind (a "no read" column that starts reading)
GROW_ROWS = 96 * 120        # free rows kept at the end of each file (about four months)
HASH_BLOCK = 4096           # rows per fingerprint block of the bars
MISS = {-1: None, -2: "nan", -3: "na"}   # codes of missing values in a text column
LAYOUT = 2                  # 1: X.bin beside the readings (until 17 Nov 2026); 2: X rebuilt from the readings
PAGE = 4096                 # a memory map is written back to the disk in pages of this size
CHECK_MAX_BYTES = 2 << 30   # the daily check of one asset stops past this many bytes written (pages) ...
CHECK_MAX_SECONDS = 300     # ... or past this many seconds comparing and writing (it retries the next UTC day)


class Rebuild(Exception):
    """The store no longer fits the readings: build it again from scratch."""


class StoreError(Exception):
    """The store cannot serve these readings exactly (building it again would not help): the live
    step falls back to the full prepare and says so."""


class FeatureRows:
    """The feature matrix of a store's rows, rebuilt on demand from the stored readings: for each
    feature the stored column as float64 with NaN -> 0.0, which is evidence.matrix's
    ev[FEATURES].astype(float).fillna(0.0) value for value (float32 -> float64 is exact; a "no read"
    column is 0.0). It behaves like the (n, features) memory map it replaces wherever the engine reads
    it: X[i] -> one row, X[a:b] -> the same thing for those rows (still nothing read),
    X[row numbers] / X[mask] -> an array, X[rows, cols] -> only those columns are read,
    np.asarray(X) -> the whole matrix in memory (do that on a slice, not on all history)."""

    ndim = 2

    def __init__(self, src, lo, n):
        self._src, self._lo, self._n = list(src), int(lo), int(n)   # src: None | (is text, (slots, cap) array, slot)
        self.shape = (self._n, len(self._src))
        self.dtype = np.dtype(np.float64)

    def __len__(self):
        return self._n

    def _take(self, rows):
        """rows: a slice or an array of the STORE's row numbers -> (len, features) float64."""
        k = rows.stop - rows.start if isinstance(rows, slice) else len(rows)
        out = np.zeros((k, len(self._src)))
        if not k:
            return out
        for j, s in enumerate(self._src):
            if s is None:                                        # no reading in any stored row: 0.0
                continue
            text, base, slot = s
            v = base[slot, rows]
            if text:                                             # a text column can only be a feature while empty
                if (v >= 0).any():
                    raise StoreError("feature column %d holds text" % j)
                continue
            out[:, j] = v
        np.copyto(out, 0.0, where=np.isnan(out))
        return out

    def _rows(self, key):
        """A row key -> ("view", lo, n) | ("one", row) | ("rows", store row numbers)."""
        n = self._n
        if isinstance(key, slice):
            a, b, step = key.indices(n)
            if step == 1:
                return "view", self._lo + a, max(b - a, 0)
            return "rows", self._lo + np.arange(a, b, step)
        if isinstance(key, (int, np.integer)):
            k = int(key) + (n if key < 0 else 0)
            if not 0 <= k < n:
                raise IndexError("row %d of %d" % (int(key), n))
            return "one", self._lo + k
        rows = np.asarray(key)
        if rows.ndim != 1:
            raise IndexError("rows are picked by a number, a slice or a 1-d array")
        if rows.dtype == bool:
            if len(rows) != n:
                raise IndexError("a mask of %d rows for %d" % (len(rows), n))
            rows = np.flatnonzero(rows)
        elif not len(rows):
            rows = np.zeros(0, dtype=np.int64)
        elif rows.dtype.kind not in "iu":
            raise IndexError("rows are picked by whole numbers, not %s" % rows.dtype)
        rows = np.where(rows < 0, rows + n, rows).astype(np.int64)
        if len(rows) and (rows.min() < 0 or rows.max() >= n):
            raise IndexError("a row outside 0 .. %d" % (n - 1))
        return "rows", self._lo + rows

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) == 1:
                return self[key[0]]
            if len(key) != 2:
                raise IndexError("a feature matrix has two axes")
            rk, ck = key
            if isinstance(ck, (int, np.integer)):
                return np.asarray(FeatureRows([self._src[ck]], self._lo, self._n)[rk])[..., 0]
            if isinstance(ck, slice):
                src = self._src[ck]
            else:
                if not isinstance(rk, (slice, int, np.integer)):
                    raise IndexError("rows and columns both by arrays: take the rows first, X[rows][:, cols]")
                ck = np.asarray(ck)
                ck = np.flatnonzero(ck) if ck.dtype == bool else ck
                src = [self._src[int(i)] for i in ck]
            return np.asarray(FeatureRows(src, self._lo, self._n)[rk])
        how = self._rows(key)
        if how[0] == "view":
            return FeatureRows(self._src, how[1], how[2])
        if how[0] == "one":
            return self._take(slice(how[1], how[1] + 1))[0]
        return self._take(how[1])

    def __array__(self, dtype=None, copy=None):
        out = self._take(slice(self._lo, self._lo + self._n))
        return out if dtype is None else out.astype(dtype, copy=False)

    def astype(self, dtype):
        return np.asarray(self).astype(dtype, copy=False)


# --------------------------------------------------------------------------------------------
# signatures and fingerprints
# --------------------------------------------------------------------------------------------
def code_signature():
    """Hash of everything that decides the readings: evidence, levels, indicators, data, econ, owner,
    every source module, this file, CFG, and the pandas / numpy versions."""
    h = hashlib.sha256()
    base = os.path.join(ROOT, "engine15")
    files = ["evidence.py", "levels.py", "indicators.py", "data.py", "econ.py", "owner.py", "evcache.py",
             "extdata.py", "livefeeds.py", "calhistory.py"]
    src = os.path.join(base, "sources")
    files += [os.path.join("sources", f) for f in sorted(os.listdir(src)) if f.endswith(".py")]
    for f in files:
        p = os.path.join(base, f)
        if os.path.exists(p):
            h.update(f.encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    h.update(json.dumps(CFG, sort_keys=True, default=str).encode())
    h.update(("pandas %s numpy %s" % (pd.__version__, np.__version__)).encode())
    return h.hexdigest()


def _bar_hashes(df):
    """Fingerprints of one asset's bars (on the group's common index), one per HASH_BLOCK rows."""
    cols = [c for c in ("open", "high", "low", "close", "volume", "taker_buy") if c in df.columns]
    m = np.ascontiguousarray(df[cols].to_numpy(dtype=float))
    out = []
    for s in range(0, len(m), HASH_BLOCK):
        out.append(hashlib.blake2b(m[s:s + HASH_BLOCK].tobytes(), digest_size=12).hexdigest())
    return out


def _series_rows(new, old_t, old_v, common_ms):
    """First row of `common_ms` whose readings a change in a time-keyed series can move (or None).
    new: (times ms int64, values float64); old_*: what was stored."""
    nt, nv = new
    k = min(len(nt), len(old_t))
    same_t = np.array_equal(nt[:k], old_t[:k])
    diff = np.flatnonzero(~((nv[:k] == old_v[:k]) | (np.isnan(nv[:k]) & np.isnan(old_v[:k])))) if same_t else np.array([0])
    if not same_t:
        first = int(np.flatnonzero(nt[:k] != old_t[:k])[0]) if k and (nt[:k] != old_t[:k]).any() else k
    elif len(diff):
        first = int(diff[0])
    elif len(nt) != len(old_t):
        first = k
    else:
        return None
    if first >= len(nt) and first >= len(old_t):
        return None
    t = min(nt[first] if first < len(nt) else np.iinfo(np.int64).max,
            old_t[first] if first < len(old_t) else np.iinfo(np.int64).max)
    return int(np.searchsorted(common_ms, t - CFG["bar_ms"], side="left"))


def _funding_arrays(f):
    if f is None or not len(f):
        return np.zeros(0, np.int64), np.zeros(0, float)
    t = np.asarray(pd.DatetimeIndex(f.index).as_unit("ms").asi8, dtype=np.int64)
    return t, np.asarray(f.values, dtype=float)


def _live_arrays(lv):
    """A live-reads frame -> (row times ms, flattened values) for change detection."""
    if lv is None or not len(lv):
        return np.zeros(0, np.int64), np.zeros(0, float)
    lv = lv.sort_index()
    t = np.asarray(pd.DatetimeIndex(lv.index).as_unit("ms").asi8, dtype=np.int64)
    num = lv.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    w = num.shape[1]
    return np.repeat(t, w), num.ravel()


# --------------------------------------------------------------------------------------------
# one asset's store
# --------------------------------------------------------------------------------------------
class AssetStore:
    """data/evcache/<group>/<asset>/: meta.json, times.bin, f8.bin, f4.bin, b1.bin, i8.bin, code.bin,
    ready.bin. Column-major blocks (cols, cap) for the readings. The feature matrix is not a file:
    X() rebuilds its rows from the readings (FeatureRows)."""

    KINDS = {"f8": np.float64, "f4": np.float32, "b1": np.bool_, "i8": np.int64, "code": np.int32}
    FILES = ("times", "ready") + tuple(KINDS)

    def __init__(self, path):
        self.path = path
        self.meta = None
        self._mm = {}

    # ---- files
    def _file(self, name):
        return os.path.join(self.path, name + ".bin")

    def load(self):
        p = os.path.join(self.path, "meta.json")
        if not os.path.exists(p):
            return False
        self._mm = {}
        self.meta = None
        try:
            with open(p, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            return False
        if meta.get("version") != LAYOUT or "features" not in meta:   # an older layout (X.bin): build again
            return False
        self.meta = meta
        for name in self.FILES:                                  # every file exactly the size the meta says: a crash
            shape, dt = self._spec(name)                         # while the files were being enlarged leaves one that
            want = int(np.prod(shape)) * np.dtype(dt).itemsize   # is not, and such a store is never read
            try:
                have = os.path.getsize(self._file(name))
            except OSError:
                have = -1
            if have != want:
                self.meta = None
                return False
        return True

    def save_meta(self):
        os.makedirs(self.path, exist_ok=True)
        tmp = os.path.join(self.path, "meta.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.meta, fh)
        os.replace(tmp, os.path.join(self.path, "meta.json"))

    def _spec(self, name, cap=None):
        """(shape, dtype) of one file for `cap` rows."""
        m = self.meta
        cap = m["cap"] if cap is None else cap
        if name == "times":
            return (cap,), np.int64
        if name == "ready":
            return (cap,), np.bool_
        return (m["slots"][name], cap), self.KINDS[name]

    def mm(self, name, mode="r"):
        """The memory map of one file (cached per mode)."""
        key = (name, mode)
        if key not in self._mm:
            shape, dt = self._spec(name)
            if 0 in shape:
                return np.zeros(shape, dt)
            self._mm[key] = np.memmap(self._file(name), dtype=dt, mode=mode, shape=shape)
        return self._mm[key]

    def close(self):
        for v in self._mm.values():
            try:
                v.flush()
            except Exception:
                pass
        self._mm = {}

    # ---- creating the files
    def create(self, columns, kinds, dtypes, n_x, cap, features=None):
        """Empty files for `cap` rows. columns/kinds/dtypes in the evidence frame's order; features:
        the columns of the feature matrix, in its order (evidence.FEATURES). Whatever stood in the
        folder (an older layout's X.bin too) is removed first, so a rebuild never needs more disk
        than the store it replaces."""
        if features is None:
            from .evidence import FEATURES as features
        features = list(features)
        known = set(columns)
        missing = [f for f in features if f not in known]
        if len(features) != int(n_x) or missing:
            raise StoreError("the feature matrix (%d wide) is not made of the readings: %s" % (n_x, missing[:5]))
        self.close()
        gc.collect()                                             # Windows cannot remove a file that is still mapped
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        os.makedirs(self.path)
        slots = dict((k, 0) for k in self.KINDS)
        cols = []
        for c, k, d in zip(columns, kinds, dtypes):
            if k in ("nan8", "nan4"):
                cols.append([c, k, -1, d])
            else:
                cols.append([c, k, slots[k], d])
                slots[k] += 1
        used = dict(slots)
        slots["f8"] += SPARE_COLS
        slots["f4"] += SPARE_COLS
        self.meta = {"version": LAYOUT, "n": 0, "cap": int(cap), "n_x": int(n_x), "cols": cols, "slots": slots,
                     "used": used, "tables": {}, "features": features,
                     "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        for name in self.FILES:
            self._alloc(name)
        self.save_meta()

    def _alloc(self, name, cap=None):
        shape, dt = self._spec(name, cap)
        with open(self._file(name), "wb") as fh:
            nbytes = int(np.prod(shape)) * np.dtype(dt).itemsize
            if nbytes:
                fh.truncate(nbytes)

    def grow(self, need):
        """More rows at the end of every file: each file is copied into a larger one, a column (or
        a block of rows) at a time, so memory stays small. A rare event (every few months). The new
        size goes into meta.json last: after a crash in between, load() finds a file that has not the
        size the meta says and the store is built again."""
        n, cap_old = self.meta["n"], self.meta["cap"]
        cap = int(need + GROW_ROWS)
        self.close()
        gc.collect()
        for name in self.FILES:
            src = self._file(name)
            (shape_o, dt), (shape_n, _) = self._spec(name, cap_old), self._spec(name, cap)
            if 0 in shape_o:
                self._alloc(name, cap)
                continue
            os.replace(src, src + ".old")
            self._alloc(name, cap)
            oldm = np.memmap(src + ".old", dtype=dt, mode="r", shape=shape_o)
            newm = np.memmap(src, dtype=dt, mode="r+", shape=shape_n)
            if name in ("times", "ready"):
                newm[:n] = oldm[:n]
            else:
                for j in range(shape_o[0]):
                    newm[j, :n] = oldm[j, :n]
            newm.flush()
            del oldm, newm
            gc.collect()
            os.remove(src + ".old")
        self.meta["cap"] = cap
        self.save_meta()

    # ---- writing rows
    def write(self, start, times_ms, frame, X, ready, overwrite=False):
        """Rows start .. start+len(frame)-1 (the store must already hold rows 0 .. start-1). X, the
        matrix evidence.matrix made of `frame`, is not stored: it is compared, bit for bit, with what
        the stored readings give back (StoreError if they differ). overwrite: rows in the middle of
        the store are rewritten and the rows after them stay."""
        m = self.meta
        k = len(frame)
        if start > m["n"]:
            raise Rebuild("gap: writing row %d with %d stored" % (start, m["n"]))
        self._fits(frame, X)
        end = start + k
        if end > m["cap"]:
            self.grow(end)
        self._put(slice(start, end), max(start, m["n"]), times_ms, frame, X, ready, "rows %d .. %d" % (start, end - 1))
        m["n"] = max(m["n"], end) if overwrite else end
        self.close()

    def write_rows(self, rows, times_ms, frame, X, ready):
        """Rewrite some stored rows in place (sorted row numbers, all below n; frame/X/ready: their
        rows in that order) in ONE pass: every column written at those rows, the feature matrix checked
        bit for bit once for all of them, one flush. The daily check uses it for every changed row of a
        piece at once: what reaches the disk is the pages those rows touch, once, not one flush of every
        file per run of changed rows. -> the bytes written (dirty_bytes)."""
        m = self.meta
        rows = np.asarray(rows, dtype=np.int64)
        if not len(rows):
            return 0
        if len(frame) != len(rows) or rows[0] < 0 or rows[-1] >= m["n"] or (np.diff(rows) <= 0).any():
            raise ValueError("write_rows: sorted distinct stored rows, one per frame row")
        self._fits(frame, X)
        cost = self.dirty_bytes(rows)
        self._put(rows, m["n"], times_ms, frame, X, ready, "%d rows %d .. %d" % (len(rows), rows[0], rows[-1]))
        self.close()
        return cost

    def dirty_bytes(self, rows):
        """About what writing these rows (sorted) puts on the disk: every file holds a row of each of
        its columns in a different page, and a flush writes whole pages."""
        rows = np.asarray(rows, dtype=np.int64)
        if not len(rows):
            return 0
        count = dict((k, 0) for k in self.KINDS)
        for _, kind, _, _ in self.meta["cols"]:
            if kind in count:
                count[kind] += 1
        total = 0
        for isz, cols in [(8, 1), (1, 1)] + [(np.dtype(dt).itemsize, count[k]) for k, dt in self.KINDS.items()]:
            if cols:
                total += cols * len(np.unique(rows * isz // PAGE)) * PAGE
        return int(total)

    def _fits(self, frame, X):
        m = self.meta
        if list(frame.columns) != [c[0] for c in m["cols"]]:
            raise Rebuild("columns changed")
        if X.shape[1] != m["n_x"]:
            raise Rebuild("feature matrix width changed")

    def _put(self, where, fill_to, times_ms, frame, X, ready, what):
        """Every column, the times and the ready flags at `where` (a slice or sorted row numbers), then
        the bit-for-bit check of the feature matrix there. fill_to: a "no read" column that starts
        reading gets a slot whose rows 0 .. fill_to-1 are NaN (still "no read") before its rows here."""
        m = self.meta
        for spec in m["cols"]:
            c, kind, slot, dts = spec
            s = frame[c]
            if str(s.dtype) != dts:
                raise Rebuild("dtype of %s changed: %s -> %s" % (c, dts, s.dtype))
            if kind in ("nan8", "nan4"):
                v = np.asarray(s.to_numpy())
                if not np.isnan(v).all():                        # a column that starts reading: give it a slot
                    kind = "f8" if kind == "nan8" else "f4"
                    if m["used"][kind] >= m["slots"][kind]:
                        raise Rebuild("no spare %s slot for %s" % (kind, c))
                    slot = m["used"][kind]
                    m["used"][kind] += 1
                    w = self.mm(kind, "r+")
                    w[slot, :fill_to] = np.nan                   # every other stored row of it: still "no read"
                    spec[1], spec[2] = kind, slot
                else:
                    continue
            w = self.mm(kind, "r+")
            if kind == "code":
                w[slot, where] = self._encode(c, s)
            else:
                w[slot, where] = s.to_numpy(dtype=self.KINDS[kind])
        self.mm("times", "r+")[where] = times_ms
        self.mm("ready", "r+")[where] = ready
        want = np.ascontiguousarray(X, dtype=np.float64)
        got = self._features("r+")._take(where)
        if got.shape != want.shape or not np.array_equal(got.view(np.int64), want.view(np.int64)):
            self.close()
            raise StoreError("%s: the stored readings do not give back the feature matrix" % what)
        del got, want

    def _encode(self, col, s):
        table = self.meta["tables"].setdefault(col, [])
        pos = dict((v, i) for i, v in enumerate(table))
        out = np.empty(len(s), np.int32)
        for i, v in enumerate(s.astype(object).tolist()):
            if v is None:
                out[i] = -1
            elif v is pd.NA:
                out[i] = -3
            elif isinstance(v, float) and v != v:
                out[i] = -2
            elif type(v) is str:
                j = pos.get(v)
                if j is None:
                    j = pos[v] = len(table)
                    table.append(v)
                out[i] = j
            else:
                raise Rebuild("column %s holds a %s, not text" % (col, type(v).__name__))
        return out

    # ---- reading
    def frame(self, index):
        """The stored readings as a DataFrame on `index` (len n): float columns are memory-map views,
        a "no read" column is a shared NaN row; bool/int/text columns are read into memory."""
        import pandas.api.internals as pai
        m, n = self.meta, self.meta["n"]
        if len(index) != n:
            raise ValueError("index has %d rows, store %d" % (len(index), n))
        groups = {}
        for j, (c, kind, slot, dts) in enumerate(m["cols"]):
            groups.setdefault((kind, dts if kind in ("code",) else None), []).append((j, slot, dts))
        blocks = []
        nan8 = nan4 = None
        for (kind, _), items in groups.items():
            place = np.array([j for j, _, _ in items], dtype=np.intp)
            if kind == "nan8":
                nan8 = np.full(n, np.nan) if nan8 is None else nan8
                blocks.append((np.broadcast_to(nan8, (len(items), n)), place))
            elif kind == "nan4":
                nan4 = np.full(n, np.nan, dtype=np.float32) if nan4 is None else nan4
                blocks.append((np.broadcast_to(nan4, (len(items), n)), place))
            elif kind in ("f8", "f4"):
                mm = self.mm(kind)
                slots = [s for _, s, _ in items]
                if slots == list(range(slots[0], slots[0] + len(slots))):
                    blocks.append((mm[slots[0]:slots[0] + len(slots), :n], place))
                else:                                            # promoted columns out of order: one block each
                    for (j, s, _) in items:
                        blocks.append((mm[s:s + 1, :n], np.array([j], dtype=np.intp)))
            elif kind in ("b1", "i8"):
                mm = self.mm(kind)
                blocks.append((np.array(mm[[s for _, s, _ in items], :n]), place))
            elif kind == "code":
                mm = self.mm("code")
                for (j, s, dts) in items:
                    c = m["cols"][j][0]
                    blocks.append((self._decode(c, np.asarray(mm[s, :n]), dts), np.array([j], dtype=np.intp)))
        return pai.create_dataframe_from_blocks(blocks, index=index, columns=pd.Index([c[0] for c in m["cols"]]))

    def _decode(self, col, codes, dts):
        table = list(self.meta["tables"].get(col, []))
        ext = np.empty(len(table) + 3, dtype=object)
        ext[:len(table)] = table
        ext[len(table)], ext[len(table) + 1], ext[len(table) + 2] = pd.NA, np.nan, None
        idx = np.where(codes >= 0, codes, len(table) + 3 + codes)      # -1 None, -2 nan, -3 NA
        vals = ext[idx]
        if dts == "object":
            return vals.reshape(1, -1)
        return pd.array(vals, dtype=pd.api.types.pandas_dtype(dts))

    def _features(self, mode="r"):
        """FeatureRows over every row slot of the files (rows past n too: write() checks what it wrote)."""
        m = self.meta
        spec = dict((c[0], c) for c in m["cols"])
        base, src = {}, []
        for f in m["features"]:
            _, kind, slot, _ = spec[f]
            if kind in ("nan8", "nan4"):
                src.append(None)
                continue
            if kind not in base:
                base[kind] = np.asarray(self.mm(kind, mode))     # a plain view of the memory map (it keeps it open)
            src.append((kind == "code", base[kind], int(slot)))
        return FeatureRows(src, 0, m["cap"])

    def X(self):
        """The feature matrix of the stored rows (FeatureRows: nothing is read until rows are asked for)."""
        return self._features()[:self.meta["n"]]

    def ready(self):
        return np.array(self.mm("ready")[:self.meta["n"]])

    def times_ms(self):
        return np.array(self.mm("times")[:self.meta["n"]])

    def rows_frame(self, rows):
        """Stored readings of some rows as an ordinary frame (for comparisons)."""
        idx = pd.RangeIndex(len(rows))
        full = self.frame(pd.RangeIndex(self.meta["n"]))
        out = full.iloc[rows].copy()
        out.index = idx
        return out


def kinds_of(frame):
    """Storage kind of each column of a first chunk."""
    out = []
    for c in frame.columns:
        s = frame[c]
        dk = s.dtype.kind if isinstance(s.dtype, np.dtype) else None
        if dk == "f":
            allnan = bool(np.isnan(s.to_numpy()).all())
            if s.dtype == np.float64:
                out.append("nan8" if allnan else "f8")
            elif s.dtype == np.float32:
                out.append("nan4" if allnan else "f4")
            else:
                raise Rebuild("float dtype %s" % s.dtype)
        elif dk == "b":
            out.append("b1")
        elif dk == "i" and s.dtype == np.int64:
            out.append("i8")
        elif dk == "O" or str(s.dtype) in ("str", "string") or isinstance(s.dtype, pd.StringDtype):
            out.append("code")
        else:
            raise Rebuild("cannot store column %s of dtype %s" % (c, s.dtype))
    return out


# --------------------------------------------------------------------------------------------
# a market group's stores, brought up to date
# --------------------------------------------------------------------------------------------
def common_index(bars):
    common = None
    for df in bars.values():
        common = df.index if common is None else common.intersection(df.index)
    return common


def lattice_rows(common, cfg, n):
    """The rows the voices may train on: one every train_step sessions from train_floor."""
    floor = int(common.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    birth = int(common.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    return np.arange(min(floor, birth), n, int(cfg["train_step"]))


def update(group, bars, funding, live, cfg, log=print, root=None, force_check=False):
    """Bring the group's stores up to `bars` (each asset's frame up to the last closed bar).
    -> ({asset: AssetStore}, common index, report dict)."""
    from . import evidence
    t0 = time.time()
    base = os.path.join(root or CACHE_DIR, group)
    assets = list(bars)
    common = common_index(bars)
    n = len(common)
    cms = np.asarray(common.as_unit("ms").asi8, dtype=np.int64)
    sig = code_signature()
    stores = dict((a, AssetStore(os.path.join(base, a))) for a in assets)
    gmeta_p = os.path.join(base, "group.json")
    gmeta = {}
    if os.path.exists(gmeta_p):
        with open(gmeta_p, encoding="utf-8") as fh:
            gmeta = json.load(fh)
    ok = gmeta.get("sig") == sig and gmeta.get("assets") == assets and all(s.load() for s in stores.values())
    rep = {"rebuilt": False, "rows_written": 0, "changed_rows": {}, "checked": False}
    if ok:
        stored = min(s.meta["n"] for s in stores.values())
        st_t = stores[assets[0]].times_ms()[:stored]
        k = min(stored, n)
        bad = np.flatnonzero(st_t[:k] != cms[:k])
        R = int(bad[0]) if len(bad) else k                       # rows still on the same timeline
        for a in assets:                                         # bars, funding, live reads: first change
            hs = _bar_hashes(bars[a].loc[common])
            old = gmeta.get("bars", {}).get(a, [])
            for b, (x, y) in enumerate(zip(hs, old)):
                if x != y:
                    R = min(R, b * HASH_BLOCK)
                    break
            for name, arrs in (("funding", _funding_arrays((funding or {}).get(a))),
                               ("live", _live_arrays((live or {}).get(a)))):
                p = os.path.join(base, "%s_%s.npz" % (name, a))
                if os.path.exists(p):
                    with np.load(p) as z:
                        r = _series_rows(arrs, z["t"], z["v"], cms)
                else:
                    r = 0 if len(arrs[0]) else None
                if r is not None:
                    R = min(R, r)
        R = min(R, int(common.searchsorted(common[-1] - pd.Timedelta(days=REFRESH_DAYS))))
        R = max(R, 0)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        check = force_check or os.environ.get("ENGINE15_EVCHECK") == "1" or gmeta.get("checked_day") != today
        try:
            rows = np.arange(R, n)
            extra = np.zeros(0, dtype=np.int64)
            if check:                                            # once a day: every row the learning reads
                birth = int(common.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
                lat = lattice_rows(common, cfg, n)
                extra = np.union1d(lat[lat < R], np.arange(min(birth, R), R))
            want = np.union1d(extra, rows)
            changed = dict((a, 0) for a in assets)
            spent, took, stop = dict((a, 0) for a in assets), dict((a, 0.0) for a in assets), None
            for p0 in range(0, len(want), CHUNK_ROWS):           # in pieces, so a long catch-up stays small
                piece = want[p0:p0 + CHUNK_ROWS]
                if stop is not None:                             # the check stopped: only the refresh rows still
                    piece = piece[piece >= R]
                    if not len(piece):
                        continue
                te = time.perf_counter()
                ev = evidence.build(bars, funding, live, rows=piece)
                rep["evidence_s"] = round(rep.get("evidence_s", 0.0) + time.perf_counter() - te, 2)   # for the step log
                old_part = piece < R                             # checked rows: compare, rewrite where changed
                for a in assets:
                    fr = ev[a]
                    Xr, rd = evidence.matrix(fr)
                    st = stores[a]
                    if old_part.any() and stop is None:
                        tc = time.perf_counter()
                        rr = piece[old_part]
                        j = np.flatnonzero(old_part)
                        old = st.rows_frame(rr)
                        newf = fr.iloc[j].reset_index(drop=True)
                        ne = st.ready()[rr] != rd[j]             # (X is made of the columns: no column changed,
                        for c in old.columns:                    # no row of X changed)
                            ne |= ~_col_equal(old[c], newf[c])
                        del old, newf
                        jj = j[ne]                               # every changed row of the piece: ONE write, one flush
                        cost = st.dirty_bytes(piece[jj])
                        took[a] += time.perf_counter() - tc
                        if took[a] > CHECK_MAX_SECONDS:
                            stop = "%s: %.0f s comparing and writing, over the %d s budget" % (a, took[a], CHECK_MAX_SECONDS)
                        elif spent[a] + cost > CHECK_MAX_BYTES:
                            stop = "%s: %.2f GB to write, over the %.2f GB budget" % (a, (spent[a] + cost) / 2.0 ** 30,
                                                                                   CHECK_MAX_BYTES / 2.0 ** 30)
                        else:
                            tc = time.perf_counter()
                            spent[a] += st.write_rows(piece[jj], cms[piece[jj]], fr.iloc[jj], Xr[jj], rd[jj])
                            took[a] += time.perf_counter() - tc
                            changed[a] += int(ne.sum())
                        rep["checked"] = True
                        if stop is not None:
                            log("%s: daily check stopped (%s), will retry tomorrow" % (group, stop))
                            rep["check_stopped"] = stop
                    j = np.flatnonzero(~old_part)
                    if len(j):
                        start = int(piece[j[0]])
                        if start < st.meta["n"]:                 # what the refresh changes (for the log)
                            ov = np.arange(start, min(st.meta["n"], int(piece[j[-1]]) + 1))
                            oX = np.asarray(st.X()[ov])
                            nX = Xr[j[:len(ov)]]
                            changed[a] += int((~_rows_equal(oX, nX)).sum())
                        st.write(start, cms[piece[j]], fr.iloc[j], Xr[j], rd[j])
                del ev
            rep["changed_rows"] = changed
            rep["rows_written"] = int(len(rows))
        except Rebuild as e:
            log("%s: evidence store rebuilt (%s)" % (group, e))
            ok = False
            for s in stores.values():
                s.close()
        if ok:
            gmeta["checked_day"] = today if check else gmeta.get("checked_day")
    if not ok:
        os.makedirs(base, exist_ok=True)
        with open(gmeta_p + ".tmp", "w", encoding="utf-8") as fh:   # until the build has finished the group has no
            json.dump({"building": True}, fh)                       # signature: after a crash in between it is built
        os.replace(gmeta_p + ".tmp", gmeta_p)                       # again, a half-written store is never trusted
        _build_all(group, stores, bars, funding, live, common, log)
        rep["rebuilt"] = True
        gmeta = {"checked_day": time.strftime("%Y-%m-%d", time.gmtime())}
    gmeta.update(sig=sig, assets=assets, n=n, bars=dict((a, _bar_hashes(bars[a].loc[common])) for a in assets),
                 updated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    os.makedirs(base, exist_ok=True)
    for a in assets:
        stores[a].save_meta()
        for name, arrs in (("funding", _funding_arrays((funding or {}).get(a))), ("live", _live_arrays((live or {}).get(a)))):
            np.savez(os.path.join(base, "%s_%s.npz" % (name, a)), t=arrs[0], v=arrs[1])
    with open(gmeta_p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(gmeta, fh)
    os.replace(gmeta_p + ".tmp", gmeta_p)
    rep["seconds"] = round(time.time() - t0, 1)
    return stores, common, rep


def _rows_equal(a, b):
    """Row by row: every value equal (NaN equal to NaN)."""
    return np.all((a == b) | (np.isnan(a) & np.isnan(b)), axis=1)


def _col_equal(a, b):
    """Element by element, two columns of the same dtype: equal, or both missing."""
    x, y = a.to_numpy(), b.to_numpy()
    if x.dtype.kind == "f":
        return (x == y) | (np.isnan(x) & np.isnan(y))
    if x.dtype.kind in "biu":
        return x == y
    sa, sb = pd.Series(a.to_numpy(dtype=object)), pd.Series(b.to_numpy(dtype=object))
    return ((sa == sb) | (sa.isna() & sb.isna())).to_numpy(dtype=bool)


def _build_all(group, stores, bars, funding, live, common, log):
    """A store from scratch: the rows in pieces of CHUNK_ROWS (each piece is one evidence.build)."""
    from . import evidence
    n = len(common)
    cms = np.asarray(common.as_unit("ms").asi8, dtype=np.int64)
    t0 = time.time()
    tail = evidence.build(bars, funding, live, rows=np.arange(max(0, n - 2000), n))   # which columns read today
    kinds = dict((a, kinds_of(tail[a])) for a in stores)
    del tail
    first = True
    for s in range(0, n, CHUNK_ROWS):
        rows = np.arange(s, min(s + CHUNK_ROWS, n))
        ev = evidence.build(bars, funding, live, rows=rows)
        for a, st in stores.items():
            fr = ev[a]
            Xr, rd = evidence.matrix(fr)
            if first:
                st.create(list(fr.columns), kinds[a], [str(fr[c].dtype) for c in fr.columns], Xr.shape[1], n + GROW_ROWS,
                          features=evidence.FEATURES)
            st.write(s, cms[rows], fr, Xr, rd)
            st.save_meta()
        first = False
        del ev
        log("%s: evidence store %d/%d rows (%.0fs)" % (group, rows[-1] + 1, n, time.time() - t0))
