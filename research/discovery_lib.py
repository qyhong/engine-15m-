# -*- coding: utf-8 -*-
"""discovery_lib -- shared code for the discovery machine (charter L1 surprise mining, L2 market-state map).

Everything here reads BACKWARDS only: a reading or a state at bar t depends on bars <= t,
and higher timeframes reach a 15m row only once closed (data.htf_on_15). The only things
that look forward are the OUTCOMES (what followed), which are what we measure, never inputs.

Time conventions (same as the engine): a bar is keyed by its OPEN time (UTC) and is known at
its CLOSE (open + 15 minutes). A call at the close of bar t fills at the open of bar t+1.

Cut points (terciles and the other quantiles) are fitted on the FIRST HALF of the analysis
window only, so every state in the second half is labelled with numbers fixed beforehand.
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15 import data, indicators as ind, labels  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT_DIR = os.path.join(ROOT, "research", "out")
FEE_RT_PCT = 2 * CFG["cost_side"] * 100.0          # 0.20% for a round trip at 0.10% a side
BAR = pd.Timedelta(milliseconds=CFG["bar_ms"])
MONTH_BARS = 2880                                   # 30 days of 15m bars

# ---------------------------------------------------------------- the state dimensions
# (name, bucket labels, plain-English description). Codes are 0..k-1, -1 = no reading yet.
SESSIONS = ("Asia", "London", "London+NY overlap", "New York", "weekend")
DIMS = [
    ("vol", ("quiet", "normal", "wild"),
     "volatility: the last hour's average 15m range against its 30-day average (terciles)"),
    ("trend", ("down", "mixed", "up"),
     "trend: 4h AND daily trend scores both DOWN (<= -0.5) / both UP (>= +0.5) / anything else"),
    ("session", SESSIONS,
     "session by the UTC hour of the bar's close: Asia 22-07, London 07-12, overlap 12-16, "
     "New York 16-22; Saturday and Sunday = weekend"),
    ("flow", ("selling", "balanced", "buying"),
     "order flow: net taker buying over the last 4 hours as a share of volume (terciles)"),
    ("place", ("near 24h low", "middle of 24h range", "near 24h high"),
     "place: where the close sits in the last 24 hours' high-low range (terciles)"),
    ("move", ("fell", "flat", "rose"),
     "recent move: the last hour's return in units of the 1-hour ATR14 (terciles)"),
]
DIM_NAMES = [d[0] for d in DIMS]
DIM_LABELS = dict((d[0], d[1]) for d in DIMS)
DIM_TEXT = dict((d[0], d[2]) for d in DIMS)
TERCILE_SOURCE = {"vol": "vol_ratio", "flow": "flow4h", "place": "pos24", "move": "move1h"}

# quantile cut points for the surprise precursors (fitted on the first half, like the terciles)
EXTRA_Q = {"width24": (0.20,), "compress": (0.80,), "volsurge": (0.90,), "move4h": (0.10, 0.90),
           "flow1h": (0.10, 0.90), "funding": (0.10, 0.90)}


def peak_mb():
    """Peak working set of this process in MB (Windows), or resident max on POSIX; None if unknown."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            k32 = ctypes.WinDLL("kernel32")
            psapi = ctypes.WinDLL("psapi")
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return round(pmc.PeakWorkingSetSize / 2.0 ** 20, 1)
            return None
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:
        return None


# ---------------------------------------------------------------- readings (backward-looking)
def readings(df, funding=None, events_ms=None):
    """15m bars -> frame of continuous readings, each known at the bar's close.

    funding: Series of funding rates keyed by the time each was set (data.load_funding), optional.
    events_ms: sorted int64 array of US high-impact release times (econ calendar), optional."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    v, tb = df["volume"], df["taker_buy"]
    h1 = data.resample(df, "1h")
    atr1h = data.htf_on_15(df, "1h", ind.atr_wilder(h1))
    t4 = data.htf_on_15(df, "4h", ind.trend_score(data.resample(df, "4h")["close"]))
    t1d = data.htf_on_15(df, "1D", ind.trend_score(data.resample(df, "1D")["close"]))
    rng = (h - l) / c
    rng_month = rng.rolling(MONTH_BARS, min_periods=960).mean()
    hi24, lo24 = h.rolling(96).max(), l.rolling(96).min()
    hi7, lo7 = h.rolling(672).max(), l.rolling(672).min()
    net = 2.0 * tb - v
    f = pd.DataFrame(index=df.index)
    f["atr1h"] = atr1h
    f["vol_ratio"] = rng.rolling(4).mean() / rng_month
    f["trend4h"] = t4
    f["trend1d"] = t1d
    f["flow4h"] = net.rolling(16).sum() / v.rolling(16).sum().replace(0, np.nan)
    f["flow1h"] = net.rolling(4).sum() / v.rolling(4).sum().replace(0, np.nan)
    f["pos24"] = (c - lo24) / (hi24 - lo24).replace(0, np.nan)
    f["move1h"] = (c - c.shift(4)) / atr1h
    f["move4h"] = (c - c.shift(16)) / atr1h
    f["compress"] = rng.rolling(16).mean() / rng.rolling(96).mean()        # last 4h range vs last 24h
    f["width24"] = (hi24 - lo24) / atr1h                                   # 24h range in ATR units
    f["d_hi24"] = (hi24 - c) / atr1h
    f["d_lo24"] = (c - lo24) / atr1h
    f["d_hi7d"] = (hi7 - c) / atr1h
    f["d_lo7d"] = (c - lo7) / atr1h
    f["volsurge"] = v.rolling(4).mean() / v.rolling(MONTH_BARS, min_periods=960).mean()
    close_at = df.index + BAR
    f["hour"] = close_at.hour.astype(float)
    f["dow"] = close_at.dayofweek.astype(float)
    f["funding"] = np.nan
    if funding is not None and len(funding):
        f["funding"] = funding.sort_index().reindex(close_at, method="ffill").values
    f["hrs_to_econ"] = np.nan
    f["hrs_since_econ"] = np.nan
    if events_ms is not None and len(events_ms):
        ev = np.sort(np.asarray(events_ms, dtype="int64"))
        cms = data.to_ms(close_at)
        k = np.searchsorted(ev, cms, side="left")
        covered = cms >= ev[0] - 7 * 86400000                              # no calendar before it starts
        ahead = np.where(k < len(ev), (ev[np.minimum(k, len(ev) - 1)] - cms) / 3.6e6, np.nan)
        since = np.where(k > 0, (cms - ev[np.maximum(k - 1, 0)]) / 3.6e6, np.nan)
        f["hrs_to_econ"] = np.where(covered, ahead, np.nan)
        f["hrs_since_econ"] = np.where(covered, since, np.nan)
    return f.astype("float32")


def session_code(hour, dow):
    hour = np.asarray(hour, dtype=float)
    dow = np.asarray(dow, dtype=float)
    s = np.full(len(hour), 0, dtype=np.int8)                               # Asia 22-07
    s[(hour >= 7) & (hour < 12)] = 1
    s[(hour >= 12) & (hour < 16)] = 2
    s[(hour >= 16) & (hour < 22)] = 3
    s[dow >= 5] = 4
    s[~np.isfinite(hour)] = -1
    return s


def fit_thresholds(f, mask):
    """Cut points from the rows in `mask` (the first half): terciles + surprise-precursor quantiles."""
    thr = {}
    for dim, col in TERCILE_SOURCE.items():
        x = f[col].values[mask]
        x = x[np.isfinite(x)]
        thr[dim] = [float(np.quantile(x, 1 / 3.0)), float(np.quantile(x, 2 / 3.0))]
    for col, qs in EXTRA_Q.items():
        x = f[col].values[mask]
        x = x[np.isfinite(x)]
        thr["q_" + col] = [float(np.quantile(x, q)) for q in qs] if len(x) else [float("nan")] * len(qs)
    return thr


def _tercile(x, cuts):
    x = np.asarray(x, dtype=float)
    out = np.where(x <= cuts[0], 0, np.where(x <= cuts[1], 1, 2)).astype(np.int8)
    out[~np.isfinite(x)] = -1
    return out


def states(f, thr):
    """Readings + fixed cut points -> frame of int8 state codes (one column per dimension, -1 = none)."""
    s = pd.DataFrame(index=f.index)
    s["vol"] = _tercile(f["vol_ratio"].values, thr["vol"])
    t4, t1 = f["trend4h"].values.astype(float), f["trend1d"].values.astype(float)
    tr = np.ones(len(f), dtype=np.int8)
    tr[(t4 >= 0.5) & (t1 >= 0.5)] = 2
    tr[(t4 <= -0.5) & (t1 <= -0.5)] = 0
    tr[~(np.isfinite(t4) & np.isfinite(t1))] = -1
    s["trend"] = tr
    s["session"] = session_code(f["hour"].values, f["dow"].values)
    s["flow"] = _tercile(f["flow4h"].values, thr["flow"])
    s["place"] = _tercile(f["pos24"].values, thr["place"])
    s["move"] = _tercile(f["move1h"].values, thr["move"])
    return s[DIM_NAMES]


# ---------------------------------------------------------------- outcomes (what followed)
FWD = (1, 4, 16)
TB_H = (16, 96)
METRICS = ("f1", "f4", "f16", "tb16", "tb96")
METRIC_H = {"f1": 1, "f4": 4, "f16": 16, "tb16": 16, "tb96": 96}
METRIC_TEXT = {"f1": "the next 15 minutes", "f4": "the next hour", "f16": "the next 4 hours",
               "tb16": "a 4-hour triple-barrier trade", "tb96": "the engine's 24-hour triple-barrier trade"}


def outcomes(df, unit):
    """What followed a call at the close of each bar, entering at the next bar's open.
    f<h>: % return from the open of t+1 to the close of t+h.
    tb<h>: triple barrier at +-unit (labels.triple_barrier): class y<h> (1 up, 2 down, 0 neither,
    -1 unknown) and the % P&L of a LONG trade that exits at the first barrier, or at the close of the
    horizon's last bar if none is touched (also when both are touched inside one bar)."""
    o, hi, lo, c = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    n = len(c)
    out = pd.DataFrame(index=df.index)
    nxt = np.full(n, np.nan)
    nxt[:-1] = o[1:]
    for hh in FWD:
        r = np.full(n, np.nan)
        r[:n - hh] = c[hh:] / nxt[:n - hh] - 1.0
        out["f%d" % hh] = r * 100.0
    unit = np.asarray(unit, dtype=float)
    for hh in TB_H:
        y, _ = labels.triple_barrier(o, hi, lo, np.nan_to_num(unit, nan=-1.0), hh)
        ret_h = np.full(n, np.nan)
        ret_h[:n - hh] = c[hh:] / nxt[:n - hh] - 1.0
        u = unit / nxt
        pnl = np.where(y == labels.UP, u, np.where(y == labels.DOWN, -u, ret_h))
        pnl[y == labels.UNKNOWN] = np.nan
        out["y%d" % hh] = y
        out["tb%d" % hh] = pnl * 100.0
    for k in out.columns:
        if k.startswith("y"):
            out[k] = out[k].astype(np.int8)
        else:
            out[k] = out[k].astype("float32")
    return out


def surprise_moves(df, atr1h):
    """Move from the close of t to the close of t+4 and t+16, in units of the 1-hour ATR14 at t."""
    c = df["close"].values.astype(float)
    a = np.asarray(atr1h, dtype=float)
    n = len(c)
    out = {}
    for hh in (4, 16):
        m = np.full(n, np.nan)
        m[:n - hh] = (c[hh:] - c[:n - hh]) / a[:n - hh]
        out["m%d" % hh] = m.astype("float32")
    return pd.DataFrame(out, index=df.index)


# ---------------------------------------------------------------- one asset, end to end
def build(asset, df=None, with_extras=True):
    """-> dict: df (bars), f (readings), st (states), out (outcomes), thr, half (0 warm-up, 1, 2),
    start/mid/end timestamps. Cut points are fitted on half 1 only."""
    if df is None:
        df = data.load(asset)
    funding = events = None
    if with_extras:
        try:
            funding = data.load_funding(asset)
        except Exception:
            funding = None
        try:
            from engine15 import econ
            ev = econ.load_events()
            events = ev.ts_ms.unique().astype("int64") if len(ev) else None
        except Exception:
            events = None
    f = readings(df, funding=funding, events_ms=events)
    start = max(pd.Timestamp(CFG["birth"], tz="UTC"), df.index[0])
    end = df.index[-1]
    mid = start + (end - start) / 2
    half = np.zeros(len(df), dtype=np.int8)
    half[(df.index >= start) & (df.index < mid)] = 1
    half[df.index >= mid] = 2
    thr = fit_thresholds(f, half == 1)
    st = states(f, thr)
    out = outcomes(df, CFG["barrier_atr"] * f["atr1h"].values)
    return {"asset": asset, "df": df, "f": f, "st": st, "out": out, "thr": thr, "half": half,
            "start": start, "mid": mid, "end": end}


# ---------------------------------------------------------------- grouped statistics
def group_stats(codes, ncodes, y, pos, h):
    """Per state code: n, n_eff (distinct h-bar blocks touched: overlapping horizons count once),
    sum, sum of squares, count > 0, count < 0. codes -1 and non-finite y are skipped."""
    m = (codes >= 0) & np.isfinite(y)
    cc = codes[m].astype(np.int64)
    yy = y[m].astype(np.float64)
    n = np.bincount(cc, minlength=ncodes)
    s = np.bincount(cc, yy, minlength=ncodes)
    ss = np.bincount(cc, yy * yy, minlength=ncodes)
    up = np.bincount(cc, (yy > 0).astype(float), minlength=ncodes)
    dn = np.bincount(cc, (yy < 0).astype(float), minlength=ncodes)
    blocks = pos[m].astype(np.int64) // h
    nb = int(blocks.max()) + 1 if len(blocks) else 1
    uk = np.unique(cc * nb + blocks)
    neff = np.bincount(uk // nb, minlength=ncodes)
    return n, neff, s, ss, up, dn


def finish(n, neff, s, ss):
    """-> mean, t (with the independence-adjusted count), using the sample sd."""
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s / n
        var = (ss - n * mean * mean) / np.maximum(n - 1, 1)
        se = np.sqrt(np.maximum(var, 0) / np.maximum(neff, 1))
        t = mean / se
    return mean, t


def group_medians(codes, ncodes, y):
    m = (codes >= 0) & np.isfinite(y)
    cc = codes[m].astype(np.int64)
    yy = y[m].astype(np.float64)
    order = np.lexsort((yy, cc))
    cc, yy = cc[order], yy[order]
    lo = np.searchsorted(cc, np.arange(ncodes), side="left")
    hi = np.searchsorted(cc, np.arange(ncodes), side="right")
    med = np.full(ncodes, np.nan)
    for g in range(ncodes):
        if hi[g] > lo[g]:
            seg = yy[lo[g]:hi[g]]
            k = len(seg)
            med[g] = seg[k // 2] if k % 2 else 0.5 * (seg[k // 2 - 1] + seg[k // 2])
    return med


def groupings():
    """Every single dimension and every pair: -> list of tuples of dimension names."""
    gs = [(d,) for d in DIM_NAMES]
    for i in range(len(DIM_NAMES)):
        for j in range(i + 1, len(DIM_NAMES)):
            gs.append((DIM_NAMES[i], DIM_NAMES[j]))
    return gs


def combo_codes(st_arrays, dims):
    """st_arrays: dict dim -> int8 codes. -> (codes for the combination, number of codes)."""
    code = np.zeros(len(st_arrays[dims[0]]), dtype=np.int64)
    bad = np.zeros(len(code), dtype=bool)
    k = 1
    for d in dims:
        nb = len(DIM_LABELS[d])
        x = st_arrays[d].astype(np.int64)
        bad |= x < 0
        code = code * nb + x
        k *= nb
    code[bad] = -1
    return code, k


def decode(dims, code):
    out = []
    for d in reversed(dims):
        nb = len(DIM_LABELS[d])
        out.append((d, DIM_LABELS[d][code % nb]))
        code //= nb
    return list(reversed(out))


def cell_name(dims, code):
    return " & ".join("%s=%s" % (d, lab) for d, lab in decode(dims, code))


def fmt_time(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
