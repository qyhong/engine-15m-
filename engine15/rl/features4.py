# -*- coding: utf-8 -*-
"""features4 -- Phase 4 inputs: Phase 3's point-in-time features plus a small, economically motivated subset of Mind 15's
own readings, read (read only) from the compact evidence store engine15/evcache.py.

Why these readings (each has a reason to carry information about the next hours to days, not just a fit):
  trend      tr_1h, tr_4h, tr_1d, tr_1w      time-series momentum across timeframes: the best documented edge in crypto and
                                             futures; the engine's own multi-timeframe trend scores
  funding    fund_z, fund_3d                 crowded leveraged positioning: extreme funding marks one-sided books that pay
                                             to stay (carry) and unwind violently
  basis      pb_z, pb_chg_4h                 perpetual premium over the index: leverage demand, the same story priced live
  flow       cvd_4h, cvd_24h, cvd_div, cbp_z taker aggression (cumulative volume delta), buying without price progress, and
                                             the Coinbase premium (US spot demand)
  vol        vol_rank, shock_ratio, rg_er    volatility regime and trend efficiency: when momentum works and when costs eat it
  levels     sr_room, sr_lean, sr_pd_pos     room to the next support / resistance and the place in yesterday's range:
                                             where short-horizon moves stall
Not used: live-only readings (order book, Kronos, news, open interest, long/short ratios: no history, NaN in the past),
options (from 2021 only), ETF flows (2024+), macro, the owner's view and the hundreds of chart-pattern columns.

AVAILABILITY. A reading that is missing at a row is UNAVAILABLE, never a zero-valued signal: the value is NaN (source
modules store 0.0 for "no read"; their raw companion column tells, so those zeros are turned back into NaN), and each
group gets a 0/1 flag 'avail_<group>' (1 = every reading of the group is there). Downstream, values are z-scored per asset
on the training window only (NaN rows excluded), so an unavailable reading becomes 0 = "nothing to add" and the flag
tells the model the difference.

POINT IN TIME. The evidence store is read as a snapshot (research/out/rl/phase4_cache/readings_<asset>.npz) and joined to
the bars by bar open time; nothing is computed from the store. lookahead() is the truncation test: every reading used
here is recomputed with the engine's own code on data cut at random bars (evidence.build_one for the bar / funding
readings; the basis and Coinbase source modules on source files cut to what was known by then) and must equal the
full-data value on every row up to the cut; it also checks that the store holds exactly what the code computes.
Read only: evcache.py, evidence.py and the source modules are imported, never changed, and no store is written.
"""
import json
import os
import shutil
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import features, features3

# reading -> (group, column whose finiteness says the reading is available; None = the reading itself)
READINGS = OrderedDict([
    ("tr_1h", ("trend", None)), ("tr_4h", ("trend", None)), ("tr_1d", ("trend", None)), ("tr_1w", ("trend", None)),
    ("fund_z", ("funding", "fund_raw")), ("fund_3d", ("funding", "fund_raw")),
    ("pb_z", ("basis", "pb_premium_pct")), ("pb_chg_4h", ("basis", "pb_premium_pct")),
    ("cvd_4h", ("flow", None)), ("cvd_24h", ("flow", None)), ("cvd_div", ("flow", None)),
    ("cbp_z", ("cbprem", "cbp_bps")),
    ("vol_rank", ("vol", None)), ("shock_ratio", ("vol", None)), ("rg_er", ("vol", None)),
    ("sr_room", ("levels", None)), ("sr_lean", ("levels", None)), ("sr_pd_pos", ("levels", None)),
])
GROUPS = list(OrderedDict.fromkeys(g for g, _ in READINGS.values()))
FLAGS = ["avail_" + g for g in GROUPS]
AVAIL_COLS = sorted(set(a for _, a in READINGS.values() if a))
BUILD_ONE = [r for r in READINGS if r not in ("pb_z", "pb_chg_4h", "cbp_z")]     # computed by evidence.build_one
DERIVS = ["pb_z", "pb_chg_4h", "pb_premium_pct"]                                  # engine15/sources/derivs.py (basis card)
MARKET = ["cbp_z", "cbp_bps"]                                                     # engine15/sources/market.py (Coinbase)
GROUP_OF = {"BTCUSDT": "crypto", "ETHUSDT": "crypto", "XAUUSD": "metals", "XAGUSD": "metals", "USDJPY": "fx",
            "SPX": "index", "WTI": "energy", "BRENT": "energy"}


# ---------------------------------------------------------------- the snapshot (read only)
def store_path(asset, root=None):
    from .. import evcache
    return os.path.join(root or evcache.CACHE_DIR, GROUP_OF[asset], asset)


def snapshot(asset, cache_dir, root=None, retries=3, log=print):
    """Read the readings (+ availability columns) of one asset from the evidence store into
    cache_dir/readings_<asset>.npz (float32 values, int64 open times). Reused if present. Read only."""
    os.makedirs(cache_dir, exist_ok=True)
    out = os.path.join(cache_dir, "readings_%s.npz" % asset)
    if os.path.exists(out):
        return out
    from .. import evcache
    cols = list(READINGS) + AVAIL_COLS
    last = None
    for k in range(retries):
        try:
            st = evcache.AssetStore(store_path(asset, root))
            if not st.load():
                raise FileNotFoundError("no evidence store for %s" % asset)
            n = st.meta["n"]
            t = st.times_ms()
            fr = st.frame(pd.RangeIndex(n))
            vals = dict((c, np.asarray(fr[c], dtype=np.float64).astype(np.float32)) for c in cols if c in fr.columns)
            meta = {"asset": asset, "rows": int(n), "first": str(pd.Timestamp(int(t[0]), unit="ms", tz="UTC")),
                    "last": str(pd.Timestamp(int(t[-1]), unit="ms", tz="UTC")), "store_created": st.meta.get("created_utc"),
                    "read_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "columns": list(vals)}
            del fr
            st.close()
            tmp = out + ".tmp.npz"
            np.savez(tmp, times_ms=t.astype(np.int64), meta=json.dumps(meta), **vals)
            os.replace(tmp, out)
            log("readings snapshot %s: %d rows %s .. %s (store built %s)" % (asset, n, meta["first"], meta["last"],
                                                                            meta["store_created"]))
            return out
        except Exception as e:                      # the live engine may be rewriting the store: wait and retry
            last = e
            time.sleep(5 * (k + 1))
    raise RuntimeError("could not read the evidence store for %s: %s" % (asset, last))


def readings_frame(snap_path, index):
    """Snapshot -> DataFrame on `index` (bar open times): readings (NaN = unavailable) + avail_<group> flags."""
    z = np.load(snap_path, allow_pickle=False)
    t = z["times_ms"]
    ms = np.asarray(pd.DatetimeIndex(index).as_unit("ms").asi8, dtype=np.int64)
    pos = np.searchsorted(t, ms)
    hit = (pos < len(t)) & (t[np.minimum(pos, len(t) - 1)] == ms)
    raw = {}
    for c in list(READINGS) + AVAIL_COLS:
        v = np.full(len(ms), np.nan)
        if c in z.files:
            v[hit] = z[c][pos[hit]].astype(np.float64)
        raw[c] = v
    return assemble(raw, index)


def assemble(raw, index):
    """{reading or availability column: array on index} -> readings (NaN = unavailable) + avail_<group> flags."""
    out = {}
    n = len(index)
    raw = dict((c, np.asarray(raw[c], dtype=np.float64) if c in raw else np.full(n, np.nan))
               for c in list(READINGS) + AVAIL_COLS)
    for r, (g, a) in READINGS.items():
        v = raw[r].copy()
        ok = np.isfinite(v) if a is None else (np.isfinite(raw[a]) & np.isfinite(v))
        v[~ok] = np.nan
        out[r] = v
    for g in GROUPS:
        members = [r for r, (gg, _) in READINGS.items() if gg == g]
        out["avail_" + g] = np.all([np.isfinite(out[r]) for r in members], axis=0).astype(np.float64)
    return pd.DataFrame(out, index=index)


def build(bars, funding, fcfg, readings=None):
    """Phase 3 features (+ the readings frame and flags when given). -> DataFrame."""
    df = features3.build(bars, funding, dict(fcfg))
    if readings is not None:
        for c in readings.columns:
            df[c] = readings[c].values
    return df.replace([np.inf, -np.inf], np.nan)


def p3_columns(fcfg, bars_sample=None):
    """The Phase 3 column names (on a tiny frame)."""
    from .. import data as _d  # noqa: F401
    if bars_sample is None:
        idx = pd.date_range("2022-01-01", periods=3200, freq="15min", tz="UTC").as_unit("ms")
        c = 100 * np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.003, len(idx))))
        bars_sample = pd.DataFrame({"open": c, "high": c * 1.001, "low": c * 0.999, "close": c, "volume": 1.0}, index=idx)
    return list(features3.build(bars_sample, None, dict(fcfg)).columns)


# ---------------------------------------------------------------- the truncation test (real data)
def _engine_inputs(asset):
    from .. import data as edata
    b = edata.load(asset)
    f = edata.load_funding(asset)
    return b, f


def _cmp(a, b, atol=1e-9, rtol=1e-7):
    a, b = np.asarray(a, float), np.asarray(b, float)
    same = np.isclose(a, b, atol=atol, rtol=rtol) | (np.isnan(a) & np.isnan(b))
    return int((~same).sum())


def _cut_sources(asset, cut_close_ms, tmp):
    """Source files cut to what was KNOWN by cut_close_ms: a 15m premium bar at its close, a Coinbase hour at its end."""
    from ..sources import derivs, market
    os.makedirs(tmp, exist_ok=True)
    pb = derivs.load_source("basis", asset)
    pb = pb[pb["ts_ms"].values + 900000 <= cut_close_ms]
    pb.to_csv(derivs.path_for("basis", asset, tmp), index=False)
    src = market.coinbase_path(asset)
    if os.path.exists(src):
        cb = pd.read_csv(src)
        cb = cb[cb["ts_ms"].values + 3600000 <= cut_close_ms]
        cb.to_csv(market.coinbase_path(asset, tmp), index=False)


def synthetic_readings(bars, funding_frame, seed):
    """Readings for a synthetic series (learnability check): the engine's own build_one readings computed on the
    synthetic bars (taker buys drawn at random so order flow is defined), and persistent noise (AR(1), one-day half-life)
    standing in for the basis and Coinbase readings, which have no synthetic source. -> readings frame + flags."""
    from .. import evidence
    rng = np.random.default_rng(seed)
    b = bars[["open", "high", "low", "close", "volume"]].copy()
    b["taker_buy"] = b["volume"] * np.clip(0.5 + 0.08 * rng.standard_normal(len(b)), 0.05, 0.95)
    f = pd.Series(np.asarray(funding_frame["rate"], float),
                  index=pd.to_datetime(np.asarray(funding_frame["settle_ms"], dtype="int64"), unit="ms", utc=True))
    ev = evidence.build_one(b, f, None)
    raw = dict((c, ev[c].values) for c in BUILD_ONE + ["fund_raw"])
    phi = 0.5 ** (1.0 / 96)
    for c in ("pb_z", "pb_chg_4h", "cbp_z"):
        e = rng.standard_normal(len(b)) * np.sqrt(1 - phi * phi)
        x = np.empty(len(b))
        x[0] = e[0]
        for i in range(1, len(b)):
            x[i] = phi * x[i - 1] + e[i]
        raw[c] = x
    raw["pb_premium_pct"] = raw["pb_z"]
    raw["cbp_bps"] = raw["cbp_z"]
    del ev
    return assemble(raw, bars.index)


def lookahead(assets, n_cuts=3, seed=20261112, tmp_dir=None, root=None, log=print, extra_cuts=1):
    """For each asset: (1) evidence.build_one on bars + funding cut at random bars == the full-data rows up to the cut,
    for every build_one reading; (2) crypto only: the basis and Coinbase readings from source files cut to what was known
    == the full-data rows up to the cut; (3) the evidence store's values == what the code computes on full data (so the
    stored history is the same point-in-time computation). -> report dict (lists of offending columns; empty = clean)."""
    from .. import evcache, evidence
    from ..sources import derivs, market
    rng = np.random.default_rng(seed)
    rep = {"seed": seed, "assets": {}}
    for asset in assets:
        t0 = time.time()
        b, f = _engine_inputs(asset)
        st = evcache.AssetStore(store_path(asset, root))
        st.load()
        sidx = pd.to_datetime(st.times_ms(), unit="ms", utc=True)
        b = b[b.index.isin(sidx)]                       # the store computes a group on its markets' common bars
        n = len(b)
        crypto = GROUP_OF[asset] == "crypto"
        k = n_cuts if crypto else extra_cuts
        lo = int(b.index.searchsorted(pd.Timestamp("2020-01-01", tz="UTC")))
        cuts = sorted(int(c) for c in rng.integers(lo, n - 200, k))
        full = evidence.build_one(b, f, None)
        a = {"rows": n, "cuts": [str(b.index[c]) for c in cuts], "build_one_cut": {}, "sources_cut": {},
             "store_vs_code": {}}
        for c in cuts:
            close_ms = int(b.index[c].value // 10**6) + 900000
            part = evidence.build_one(b.iloc[:c + 1], f[np.asarray(f.index.as_unit("ms").asi8) <= close_ms] if len(f) else f, None)
            bad = [r for r in BUILD_ONE if _cmp(full[r].values[:c + 1], part[r].values) > 0]
            a["build_one_cut"][str(b.index[c])] = bad
            del part
        if crypto:
            import tempfile
            tmp = tmp_dir or tempfile.mkdtemp(prefix="p4_lookahead_")
            fd = derivs.features(b.index, asset, bars=b)
            fm = market.features(b.index, asset, bars={asset: b})
            for c in cuts:
                close_ms = int(b.index[c].value // 10**6) + 900000
                d = os.path.join(tmp, "%s_%d" % (asset, c))
                _cut_sources(asset, close_ms, d)
                pd_ = derivs.features(b.index[:c + 1], asset, src_dir=d, bars=b.iloc[:c + 1])
                pm = market.features(b.index[:c + 1], asset, src_dir=d, bars={asset: b.iloc[:c + 1]})
                bad = [r for r in DERIVS if _cmp(fd[r].values[:c + 1], pd_[r].values) > 0]
                bad += [r for r in MARKET if _cmp(fm[r].values[:c + 1], pm[r].values) > 0]
                a["sources_cut"][str(b.index[c])] = bad
                shutil.rmtree(d, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)
        sn = st.meta["n"]
        sfr = st.frame(pd.RangeIndex(sn))
        code = full.reindex(sidx)
        both = np.asarray(sidx.isin(b.index))            # rows the store and the bar file both hold
        for r in BUILD_ONE:
            a["store_vs_code"][r] = _cmp(np.asarray(sfr[r], float)[both], code[r].values[both])
        if crypto:
            fdx, fmx = fd.reindex(sidx), fm.reindex(sidx)
            # the store keeps rows up to its own last step; source files have grown since, so compare up to the
            # oldest REFRESH window the live step recomputes (older rows are final)
            old = sidx < (sidx[-1] - pd.Timedelta(days=evcache.REFRESH_DAYS + 1))
            for r in DERIVS:
                a["store_vs_code"][r] = _cmp(np.asarray(sfr[r], float)[old], fdx[r].values[old])
            for r in MARKET:
                a["store_vs_code"][r] = _cmp(np.asarray(sfr[r], float)[old], fmx[r].values[old])
        del sfr, code, full
        st.close()
        a["clean"] = (all(not v for v in a["build_one_cut"].values()) and all(not v for v in a["sources_cut"].values())
                      and all(v == 0 for v in a["store_vs_code"].values()))
        a["seconds"] = round(time.time() - t0, 1)
        rep["assets"][asset] = a
        log("look-ahead check %s: %s (%.0fs) cuts %s; store vs code mismatches %s"
            % (asset, "clean" if a["clean"] else "NOT CLEAN", a["seconds"], a["cuts"],
               dict((k, v) for k, v in a["store_vs_code"].items() if v) or "none"))
    rep["clean"] = all(v["clean"] for v in rep["assets"].values())
    return rep


def features_lookahead(bars, fund, fcfg, snap, cuts):
    """The assembled matrix (Phase 3 features + snapshot readings + flags) on bars cut at each cut == full rows."""
    rf = lambda b, f: build(b, f, fcfg, readings_frame(snap, b.index) if snap else None)
    return features.lookahead_report(rf, bars, fund, cuts)
