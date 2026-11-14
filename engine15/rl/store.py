# -*- coding: utf-8 -*-
"""store -- the ONE place that knows how tables live on disk.

Format today: gzip-compressed CSV (`.csv.gz`), because pyarrow / parquet cannot be installed on
this laptop (Windows on ARM64). Every table has an integer `ts_ms` column (UTC epoch
milliseconds) that becomes a UTC DatetimeIndex (unit ms) on read. Floats are written with
pandas' shortest round-trip repr, so a write followed by a read gives back the same bits.

To move to parquet later, change only EXT, write_frame and read_frame here.
"""
import os

import numpy as np
import pandas as pd

EXT = ".csv.gz"


def path(directory, name):
    """name without extension -> full path with this store's extension."""
    return os.path.join(directory, name + EXT)


def exists(p):
    return os.path.exists(p)


def to_ms(index):
    """A datetime index -> int64 epoch milliseconds."""
    return np.asarray(pd.DatetimeIndex(index).as_unit("ms").asi8, dtype="int64")


def from_ms(ms, name="open_time"):
    """int64 epoch milliseconds -> UTC DatetimeIndex (unit ms)."""
    return pd.DatetimeIndex(pd.to_datetime(np.asarray(ms, dtype="int64"), unit="ms", utc=True), name=name).as_unit("ms")


def write_frame(df, p, index_name="open_time"):
    """Atomic write: a frame indexed by UTC time -> p (temp file, then replace)."""
    out = df.copy()
    out.insert(0, "ts_ms", to_ms(df.index))
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    tmp = p + ".tmp"
    out.to_csv(tmp, index=False, compression="gzip")
    os.replace(tmp, p)


def read_frame(p, index_name="open_time"):
    """p -> frame indexed by UTC time (unit ms), sorted; an empty frame if the file is absent."""
    if not os.path.exists(p):
        return pd.DataFrame(index=from_ms([], index_name))
    df = pd.read_csv(p, compression="gzip", float_precision="round_trip")
    df.index = from_ms(df.pop("ts_ms").values, index_name)
    return df.sort_index()
