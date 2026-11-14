# -*- coding: utf-8 -*-
"""forward5 -- Phase 5 part 1: the Phase 4 primary agent run FORWARD on paper inside Mind 15. PAPER ONLY. NOT PASSED.

Two halves that never mix:

TRAINING (heavy, a separate below-normal-priority process: `py -3 -m engine15.rl phase5-update`). Exactly the Phase 4
primary's procedure (models4.q_fold: the Q agent pooled on BTC+ETH, expanding window from 2019, Phase 3 features + the 18
Mind 15 readings, half-life and 'do no harm' judged on the last 6 months, refit on every row up to the data end), one
learner per seed (0, 1, 2), on the engine's own 15m files up to the time of the update. q_fold's export hook hands back
the refit model itself (weights, bias, per-asset z-score stats, the 'do no harm' flags); it is written atomically as one
small JSON file research/out/rl/models5/live/model_<UTC>.json. The update is due weekly (a model with data through the
latest Monday 00:00 UTC is wanted). maybe_launch_update() is all the live step does about it: if due, no update is running
(lock), the last attempt is 30+ minutes old and at least 1,500 MB are free, it starts the subprocess and returns at once.

LIVE STEP (light, inside the live loop via engine15/playbook5.py). Per coin: read the tail of the engine's bar file, the
funding file and the tail rows of the evidence store (engine15/evcache.py, read only), build the Phase 4 inputs for the
closed bars not decided yet (features4.build on a 4,300-bar window: identical to the full-history rows, tested), value
them with the newest model whose data end is at or before each bar's close, decide with Phase 3's policy (policy3.decide:
round-trip cost band, minimum hold 4 bars) from the state recorded at the last decision, and APPEND the decisions to
research/out/rl/forward5/decisions_<asset>.jsonl. Nothing is retrained here and no model is written here.

The book is then rebuilt from the recorded decisions: each seed's requested target through the Phase 3 risk manager
(risk3.Stepper, the same code as risk3.apply), the book holds the MEAN of the three seeds' executed positions, and the
shared backtester's cost model (0.10% a side, half spread 0.5 bp, slippage, funding on the whole position: Phase 4's perp
accounting) gives the $10,000 book from REGISTERED; spot buy-and-hold over the same span is the comparison.

Decision at bar t's close, fill at bar t+1's open (Phase 4's frame). The live loop reaches the step a few minutes after a
close, so a recorded decision's fill is a paper fill at that open; the recorded `lag_s` says how late each decision was.
tests/rl/test_phase5.py: forward decisions == the Phase 4 batch walk-forward for the same model and bars; no look-ahead.
"""
import copy
import gc
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import yaml

from . import features4, policy3, risk3
from .config import load_phase4, resolve
from .continual import neutral_w
from .costs import CostModel
from .qagent import cost_matrix, q_from_w, w_numpy

BAR_MS = 900000
DAY_MS = 86400000
ASSETS = ("BTCUSDT", "ETHUSDT")
P5_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "configs", "rl",
                       "phase5.yaml")
_CFG = {}


# ---------------------------------------------------------------- config and paths
def load_cfg(path5=None):
    """Phase 1 + Phase 4 config with the Phase 5 file under cfg['phase5'] (cached per path)."""
    key = path5 or P5_PATH
    if key not in _CFG:
        cfg = load_phase4()
        with open(key, encoding="utf-8") as fh:
            cfg["phase5"] = yaml.safe_load(fh)
        _CFG[key] = cfg
    return _CFG[key]


def forward_dir(cfg):
    return resolve(cfg["phase5"]["report"]["forward_dir"])


def live_models_dir(cfg):
    return os.path.join(resolve(cfg["phase5"]["report"]["models_dir5"]), "live")


def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _jwrite(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, default=float)
    os.replace(tmp, path)


# ---------------------------------------------------------------- data (read only)
def funding_frame(series):
    """engine15.data.load_funding output -> frame rate / settle_ms (pool4.load_bars' rule)."""
    from . import data as rdata
    if series is None or not len(series):
        return pd.DataFrame({"rate": np.zeros(0), "settle_ms": np.zeros(0, dtype="int64")})
    raw = np.asarray(series.index.as_unit("ms").asi8, dtype="int64")
    return pd.DataFrame({"rate": np.asarray(series.values, dtype=float), "settle_ms": rdata.settlement_ms(raw)},
                        index=series.index)


def tail_bars(asset, nrows, path=None):
    """The last `nrows` bars of the engine's 15m file (engine15.data.load's format), read from the end of the file."""
    from .. import data as edata
    p = path or edata.path_for(asset)
    with open(p, "rb") as fh:
        header = fh.readline().decode("utf-8").strip().split(",")
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        want = max(int(nrows) * 96, 65536)
        while True:
            start = max(0, size - want)
            fh.seek(start)
            chunk = fh.read(size - start)
            lines = chunk.split(b"\n")
            if start > 0:
                lines = lines[1:]                        # a partial first line
            lines = [ln for ln in lines if ln.strip() and not ln.startswith(b"ts_ms")]
            if len(lines) >= nrows or start == 0:
                break
            want *= 2
    lines = lines[-int(nrows):]
    df = pd.read_csv(io.BytesIO(b"\n".join(lines)), header=None, names=header)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)).as_unit("ms")
    df.index.name = "open_time"
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def readings_tail(asset, t0_ms, root=None, snapshot=None):
    """Readings (+ availability columns) of the rows from open time t0_ms on. -> (times_ms, {column: float64 array},
    last stored open time). Live: the evidence store's memory maps, tail rows only, read only. snapshot: a Phase 4
    readings_<asset>.npz instead (the test feeds the batch's own source)."""
    names = list(features4.READINGS) + features4.AVAIL_COLS
    if snapshot is not None:
        z = np.load(snapshot, allow_pickle=False)
        t = z["times_ms"]
        r0 = int(np.searchsorted(t, int(t0_ms)))
        raw = dict((c, z[c][r0:].astype(np.float64) if c in z.files else np.full(len(t) - r0, np.nan)) for c in names)
        return t[r0:].astype(np.int64), raw, int(t[-1]) if len(t) else None
    from .. import evcache
    st = evcache.AssetStore(features4.store_path(asset, root))
    if not st.load():
        return np.zeros(0, np.int64), dict((c, np.zeros(0)) for c in names), None
    try:
        n = int(st.meta["n"])
        times = np.array(st.mm("times")[:n], dtype=np.int64)
        r0 = int(np.searchsorted(times, int(t0_ms)))
        spec = dict((c[0], c) for c in st.meta["cols"])
        raw = {}
        for c in names:
            s = spec.get(c)
            if s is None or s[1] not in ("f8", "f4"):
                raw[c] = np.full(n - r0, np.nan)
            else:
                raw[c] = np.array(st.mm(s[1])[int(s[2]), r0:n], dtype=np.float64)
        return times[r0:], raw, int(times[-1]) if n else None
    finally:
        st.close()


def readings_on(index, times, raw):
    """Readings on the bars' index (joined by open time; a bar the store lacks = unavailable) -> features4.assemble."""
    ms = np.asarray(pd.DatetimeIndex(index).as_unit("ms").asi8, dtype=np.int64)
    pos = np.searchsorted(times, ms)
    hit = (pos < len(times)) & (times[np.minimum(pos, max(len(times) - 1, 0))] == ms) if len(times) else np.zeros(len(ms), bool)
    out = {}
    for c, v in raw.items():
        a = np.full(len(ms), np.nan)
        if len(times):
            a[hit] = v[pos[hit]]
        out[c] = a
    return features4.assemble(out, index)


# ---------------------------------------------------------------- per-bar market arrays (env.Market / qagent, no gym)
def market_arrays(bars, fund, feats, model, qcfg):
    """The arrays the decision and the risk manager need, exactly as env.Market + qagent.reward_arrays compute them."""
    o = bars["open"].values.astype(float)
    c = bars["close"].values.astype(float)
    nxt = np.append(o[1:], c[-1]) if len(o) else o
    vol = model.bar_vol(bars)
    out = {"close_ms": np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64) + BAR_MS, "r_px": nxt / o - 1.0,
           "r_bar": c / o - 1.0, "vol": vol, "rate": model.funding_on_bars(bars.index, fund)}
    if feats is not None:
        c1 = model.fee_side + model.half_spread_bps * 1e-4 + model.slippage_coef * vol
        est = vol.copy()
        for name in ("rv_96", "rv_672"):
            if name in feats.columns:
                x = feats[name].values.astype(np.float32).astype(float)
                est = np.fmax(est, np.where(np.isfinite(x), x, 0.0))
        pos = est[est > 0]
        est = np.where(est > 0, est, np.median(pos) if len(pos) else 1e-3)
        ref = float(qcfg.get("vol_ref_annual", 0.60)) / np.sqrt(35040)
        k = np.minimum(ref / est, float(qcfg.get("vol_scale_cap", 3.0))) if qcfg.get("vol_scale", False) else np.ones(len(o))
        out["k"] = k.astype(np.float32)
        out["c1"] = c1.astype(np.float32)
    return out


def normalised(X, mu, sd, clip=5.0):
    """pool4.normalised on in-memory rows (float32: z-score, NaN -> 0, clip)."""
    x = (np.asarray(X, dtype=np.float32) - np.asarray(mu, np.float32)) / np.asarray(sd, np.float32)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    np.clip(x, -clip, clip, out=x)
    return x


TREND_COL = "mom_signal"


def trend_w(feats, actions, penalty=10.0):
    """W rows that hold the trend reference position (Phase 6's 'trend' fallback, phase5.oos_w's formula): the frozen
    daily 30-day momentum target at each bar (features3's mom_signal, +1 / -1, NaN -> 0), -penalty x |a - ref|."""
    ref = np.nan_to_num(np.asarray(feats[TREND_COL].values, dtype=np.float32), nan=0.0)
    a = np.asarray(actions, dtype=np.float32)
    return (-float(penalty) * np.abs(a[None, :] - ref[:, None])).astype(np.float32)


def model_w(model, seed, asset, feats, fallback="rule"):
    """W (n, A) of one seed's model on feature rows (model's columns), or, in a 'do no harm' model, the fallback's values:
    "rule" = flat (Phase 4/5), "trend" = the trend reference position (Phase 6), "none" = the model's own values."""
    m = model["seeds"][str(seed)]
    acts = model["actions"]
    if m["fallback"].get(asset, False) and fallback != "none":
        if fallback == "trend":
            return trend_w(feats, acts)
        return neutral_w(len(feats), acts, 0.0)
    st = m["stats"][asset]
    x = normalised(feats[model["columns"]].values, st["mu"], st["sd"])
    F = x.shape[1]
    ws = ([np.asarray(w, np.float32) for w in m["weights"]], [np.asarray(b, np.float32) for b in m["biases"]])
    return w_numpy(ws, x, np.zeros(F, np.float32), np.ones(F, np.float32), model["qagent"])


def decisions(model_for_rows, assets_feats, k, c1, actions, qcfg, min_hold, state, seeds, cost_mult=None, fallback="rule"):
    """Values -> Phase 3 policy for a block of consecutive bars, from state {seed: (ip, since)}. model_for_rows: list of
    (model, row slice). -> ({seed: ip array}, {seed: (ip, since) after the block})."""
    acts = np.asarray(actions, dtype=float)
    q_cfg = dict(qcfg)
    if cost_mult is not None:
        q_cfg["cost_mult"] = float(cost_mult)
    D = cost_matrix(acts)
    out, new = {}, {}
    asset, feats = assets_feats
    for s in seeds:
        W = np.concatenate([model_w(m, s, asset, feats.iloc[sl], fallback) for m, sl in model_for_rows])
        Q = q_from_w(W, k, c1, D, q_cfg)
        ip0, since0 = state[s]
        ip, _ = policy3.decide(Q, acts, int(ip0), int(min_hold), since0=int(since0))
        prev = np.concatenate([[ip0], ip[:-1]])
        ch = np.nonzero(ip != prev)[0]
        since = int(len(ip) - ch[-1]) if len(ch) else int(since0) + len(ip)
        out[s], new[s] = ip, (int(ip[-1]), since)
    return out, new


# ---------------------------------------------------------------- models
def list_models(folder):
    """-> [(data_end_close_ms, path)] oldest first."""
    if not os.path.isdir(folder):
        return []
    out = []
    for f in os.listdir(folder):
        if f.startswith("model_") and f.endswith(".json"):
            try:
                with open(os.path.join(folder, f), encoding="utf-8") as fh:
                    head = json.load(fh)
                out.append((int(head["data_end_close_ms"]), os.path.join(folder, f)))
            except (ValueError, KeyError, OSError):
                continue
    return sorted(out)


_MODEL_CACHE = {}


def load_model(path):
    mt = os.path.getmtime(path)
    hit = _MODEL_CACHE.get(path)
    if hit and hit[0] == mt:
        return hit[1]
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    _MODEL_CACHE[path] = (mt, m)
    return m


def model_payload(exports, columns, cfg, data_end_close_ms, info, id_prefix="m5_", kind="phase4 primary (q_pool2_full) refit"):
    q = cfg["qagent"]
    return {"id": id_prefix + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "kind": kind,
            "created_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "data_end_close_ms": int(data_end_close_ms), "data_end_utc": _utc(data_end_close_ms),
            "columns": list(columns), "actions": list(cfg["actions"]), "min_hold_bars": int(cfg["policy"]["min_hold_bars"]),
            "qagent": dict((k, q[k]) for k in ("reward_scale", "cost_mult", "obs_clip", "activation", "vol_scale",
                                               "vol_ref_annual", "vol_scale_cap", "risk_aversion", "net_arch")),
            "seeds": dict((str(s), e) for s, e in exports.items()), "info": info}


# ---------------------------------------------------------------- training (the update subprocess; heavy)
def training_bars(cfg, asset, until_ms=None):
    """The engine's file (read only) cut to closed bars with close <= until_ms, from the configured start. -> bars, fund."""
    from .. import data as edata
    bars = edata.load(asset)[["open", "high", "low", "close", "volume"]].astype(float)
    bars.index = bars.index.as_unit("ms")
    start = cfg["phase5"]["forward"]["data"][asset].get("start")
    if start:
        bars = bars[bars.index >= pd.Timestamp(start, tz="UTC")]
    if until_ms is not None:
        bars = bars[np.asarray(bars.index.as_unit("ms").asi8) + BAR_MS <= int(until_ms)]
    fund = funding_frame(edata.load_funding(asset))
    last_close = int(bars.index[-1].value // 10**6) + BAR_MS
    fund = fund[np.asarray(fund["settle_ms"], dtype="int64") <= last_close]
    return bars, fund


def train_model(cfg, until_ms=None, log=print, pause=None, out_dir=None, keep_cache=False, seeds=None, fit=None,
                tag="phase5", id_prefix="m5_", kind="phase4 primary (q_pool2_full) refit", cache_root=None):
    """Refit the Phase 4 primary on everything up to until_ms (default: the last closed bar both coins have) and write
    the model file atomically. -> path. fit / tag / id_prefix / kind / cache_root: another learner on the same data and
    geometry (forward6.py: Phase 6's shaped-reward learner); fit(assets, names, cols_idx, geo, c, seed, pause, where,
    export) -> (W, rec) with the export dict filled. Defaults = Phase 5 exactly."""
    from . import phase4, pool4, resources
    from .models4 import q_fold
    if fit is None:
        def fit(assets_, names, ci, geo_, c_, sd, pause_, where, export):
            return q_fold(assets_, names, ci, geo_, c_["q"], dict(c_["qagent"]), c_["actions"],
                          int(c_["policy"]["min_hold_bars"]), sd, pause_, where, export=export)
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    p5 = cfg["phase5"]
    seeds = list(p5["forward"]["seeds"] if seeds is None else seeds)
    data = {}
    for a in ASSETS:
        data[a] = training_bars(cfg, a, until_ms)
    end_close = min(int(b.index[-1].value // 10**6) + BAR_MS for b, _ in data.values())
    for a in ASSETS:                                     # both coins end at the same close
        b, f = data[a]
        keep = np.asarray(b.index.as_unit("ms").asi8) + BAR_MS <= end_close
        data[a] = (b[keep], f[np.asarray(f["settle_ms"], dtype="int64") <= end_close])
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    c = copy.deepcopy(cfg)
    c["report"]["cache_dir"] = os.path.join(cache_root or resolve(p5["report"]["cache_dir5"]), stamp)
    c["readings_source"] = "evcache"
    assets = []
    for a in ASSETS:
        if pause is not None:
            pause.before_start(tag + " cache " + a)
        pool4.prepare(c, a, offline=True, log=log, force=True, bars_fund=data[a])
        assets.append(pool4.Asset(os.path.join(pool4.cache_dir(c), a)))
        gc.collect()
    del data
    cols = phase4.input_columns(c, assets[0], "full")
    for A in assets[1:]:
        assert [A.columns[i] for i in A.cols(cols)] == cols
    test_start = pd.Timestamp(end_close, unit="ms", tz="UTC")
    val = test_start - pd.DateOffset(months=int(p5["forward"]["validation_months"]))
    geo = dict((A.name, {"lo": A.start, "val": A.at(val), "te_lo": A.n, "te_hi": A.n}) for A in assets)
    exports = {}
    off = int(p5["forward"]["fold_seed_offset"])
    for s in seeds:
        if pause is not None:
            pause.before_start("%s seed %d" % (tag, s))
        ex = {}
        t0 = time.time()
        _, rec = fit(assets, list(ASSETS), assets[0].cols(cols), geo, c, int(s) * 1000 + off, pause,
                     "%s seed %d" % (tag, s), ex)
        ex["seconds"] = round(time.time() - t0, 1)
        exports[s] = ex
        fb_word = " -> neutral" if tag == "phase5" else " -> fallback"
        log("%s model seed %d: chosen %s; %s; %.0fs" % (tag, s, ex["chosen"], "; ".join(
            "%s val %+.2f%s" % (a, ex["val"][a]["sharpe"], fb_word if ex["fallback"][a] else "") for a in ASSETS),
            ex["seconds"]))
        gc.collect()
    info = {"assets": dict((A.name, {"first": A.meta["first"], "last": A.meta["last"], "n": A.n, "start": A.start})
                           for A in assets), "geo": geo, "validation_from": str(val), "sources": "engine 15m files "
            "(read only), funding files, evidence-store snapshot; BTC from %s" % p5["forward"]["data"]["BTCUSDT"]["start"]}
    payload = model_payload(exports, cols, c, end_close, info, id_prefix, kind)
    out_dir = out_dir or live_models_dir(cfg)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_%s.json" % stamp)
    _jwrite(payload, path)
    del assets
    gc.collect()
    if not keep_cache:
        import shutil
        shutil.rmtree(c["report"]["cache_dir"], ignore_errors=True)
    log("model written: %s (data end %s)" % (path, _utc(end_close)))
    return path


def reproduce_phase4_fold(cfg, fold=24, seeds=(0, 1, 2), log=print, out_dir=None):
    """Rebuild a Phase 4 fold model with the export hook from Phase 4's own caches and check its test values against
    Phase 4's stored file. -> (model path, report). The test of forward == batch uses this model."""
    from . import phase4, pool4, resources, walkforward
    from .models4 import q_fold
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    assets = [pool4.Asset(os.path.join(pool4.cache_dir(cfg), a)) for a in ASSETS]
    wf = cfg["walkforward"]
    idx = pd.to_datetime(assets[0].t, unit="ms", utc=True)
    wins = walkforward.windows(idx, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"], wf["min_test_days"])
    ft = phase4.fold_times(cfg, wins)[fold]
    cols = phase4.input_columns(cfg, assets[0], "full")
    geo = dict((A.name, phase4.geo_for(A, ft, "expanding")) for A in assets)
    root = os.path.join(resolve(cfg["report"]["models_dir"]), phase4.work_hash(cfg), cfg["primary"])
    exports, rep = {}, {"fold": fold, "test_start": str(ft["test_start"]), "test_end": str(ft["test_end"]), "seeds": {}}
    for s in seeds:
        ex = {}
        W, rec = q_fold(assets, list(ASSETS), assets[0].cols(cols), geo, cfg["q"], dict(cfg["qagent"]), cfg["actions"],
                        int(cfg["policy"]["min_hold_bars"]), int(s) * 1000 + fold, None, "", export=ex)
        exports[s] = ex
        r = {}
        for a in ASSETS:
            st = np.load(os.path.join(root, "s%d" % s, "w_f%02d_%s.npy" % (fold, a)))
            r[a] = float(np.max(np.abs(W[a] - st)))
        with open(os.path.join(root, "s%d" % s, "rec_f%02d_pool.json" % fold), encoding="utf-8") as fh:
            old = json.load(fh)
        r["fallback_same"] = all(old["assets"][a]["fallback"] == ex["fallback"][a] for a in ASSETS)
        r["chosen_same"] = old["chosen"] == rec["chosen"]
        rep["seeds"][str(s)] = r
        log("fold %d seed %d: max |W - Phase 4's stored W| %s; fallback same %s; chosen same %s" % (
            fold, s, dict((a, r[a]) for a in ASSETS), r["fallback_same"], r["chosen_same"]))
    end_close = int(pd.Timestamp(ft["test_start"]).value // 10**6)
    payload = model_payload(exports, cols, cfg, end_close, {"phase4_fold": fold, "geo": geo, "work_hash": phase4.work_hash(cfg)})
    payload["id"] = "phase4_f%02d_repro" % fold
    out_dir = out_dir or os.path.join(resolve(cfg["phase5"]["report"]["models_dir5"]), "repro_f%02d" % fold)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_phase4_f%02d.json" % fold)
    _jwrite(payload, path)
    rep["exact"] = all(v[a] == 0.0 for v in rep["seeds"].values() for a in ASSETS)
    rep["model"] = path
    return path, rep


# ---------------------------------------------------------------- the weekly update (launcher + subprocess)
def last_monday_ms(now_ms):
    day = int(now_ms) // DAY_MS
    return ((day - ((day + 3) % 7)) * DAY_MS)          # 1970-01-01 was a Thursday; Monday = (day + 3) % 7 == 0


def update_due(cfg, now_ms=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    ms = list_models(live_models_dir(cfg))
    if not ms:
        return True
    return ms[-1][0] < last_monday_ms(now_ms)


def _lock_path(cfg):
    return os.path.join(forward_dir(cfg), "update.lock")


def _pid_alive(pid):
    try:
        if sys.platform == "win32":
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(h)
            return code.value == 259                                          # STILL_ACTIVE
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def update_running(cfg):
    p = _lock_path(cfg)
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as fh:
            info = json.load(fh)
    except (ValueError, OSError):
        info = {}
    age_h = (time.time() - os.path.getmtime(p)) / 3600.0
    stale = age_h > float(cfg["phase5"]["forward"]["update"]["stale_lock_hours"]) or (
        info.get("pid") and not _pid_alive(info["pid"]))
    if stale:
        try:
            os.remove(p)
        except OSError:
            pass
        return False
    return True


def maybe_launch_update(cfg, now_ms=None, log=print, free_mb=None, launcher=None, due=None, command="phase5-update",
                        status_dir=None, tag="phase5", hold=None):
    """Called by the live step: start `py -3 -m engine15.rl phase5-update` if an update is due, none is running, the
    last attempt is old enough and memory allows. Never waits for it. -> what happened (a short string).
    due / command / status_dir / tag / hold: another weekly refit sharing this one's lock (forward6.py: Phase 6's), so
    that two refits never run at once; hold() -> a reason to wait (or None) is checked after the lock."""
    from . import resources
    u = cfg["phase5"]["forward"]["update"]
    if not (update_due(cfg, now_ms) if due is None else due(cfg, now_ms)):
        return "not due"
    if update_running(cfg):
        return "running"
    if hold is not None:
        why = hold(cfg, now_ms)
        if why:
            return why
    d = status_dir or forward_dir(cfg)
    os.makedirs(d, exist_ok=True)
    stamp = os.path.join(d, "update_attempt.json")
    now = time.time()
    try:
        with open(stamp, encoding="utf-8") as fh:
            last = float(json.load(fh).get("t", 0))
    except (ValueError, OSError):
        last = 0.0
    if now - last < 60 * float(u["retry_minutes"]):
        return "waiting to retry"
    f = resources.free_mb() if free_mb is None else free_mb
    _jwrite({"t": now, "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)), "free_mb": f}, stamp)
    if f is not None and f < float(u["min_free_mb"]):
        log("%s update due but only %.0f MB free (needs %d); retry in %d min" % (tag, f, u["min_free_mb"], u["retry_minutes"]))
        return "low memory"
    if launcher is not None:
        launcher()
        return "launched"
    from ..config import ROOT
    logf = open(os.path.join(d, "update.log"), "a", encoding="utf-8")
    flags = 0
    if sys.platform == "win32":
        flags = 0x00004000 | 0x08000000 | 0x00000200     # BELOW_NORMAL | CREATE_NO_WINDOW | NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, "-m", "engine15.rl", command], cwd=ROOT, stdout=logf, stderr=logf,
                     stdin=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    logf.close()
    log("%s update launched (below-normal priority, %.0f MB free)" % (tag, f or -1))
    return "launched"


def update_cli(cfg, log=print, force=False, train=None, due=None, status_dir=None, tag="phase5"):
    """The update subprocess: one at a time (lock with this PID), >= min_free_mb to start, pauses under the floor.
    train / due / status_dir / tag: another refit under the same lock (forward6.py); defaults = Phase 5."""
    from . import resources
    resources.low_priority()
    u = cfg["phase5"]["forward"]["update"]
    d = status_dir or forward_dir(cfg)
    os.makedirs(d, exist_ok=True)
    os.makedirs(forward_dir(cfg), exist_ok=True)
    if not force and not (update_due(cfg) if due is None else due(cfg)):
        log("%s update: not due" % tag)
        return 0
    if update_running(cfg):
        log("%s update: another update holds the lock" % tag)
        return 0
    try:
        fd = os.open(_lock_path(cfg), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        log("%s update: another update holds the lock" % tag)
        return 0
    with os.fdopen(fd, "w") as fh:
        json.dump({"pid": os.getpid(), "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "job": tag}, fh)
    try:
        f = resources.free_mb()
        if f is not None and f < float(u["min_free_mb"]):
            log("%s update: only %.0f MB free (needs %d); try later" % (tag, f, u["min_free_mb"]))
            return 75
        pause = resources.MemoryPause(float(u["min_free_mb"]), float(u["floor_mb"]), 20, log)
        t0 = time.time()
        path = (train or train_model)(cfg, log=log, pause=pause)
        _jwrite({"utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "model": path,
                 "minutes": round((time.time() - t0) / 60, 1), "memory_events": pause.events},
                os.path.join(d, "last_update.json"))
        return 0
    finally:
        try:
            os.remove(_lock_path(cfg))
        except OSError:
            pass


# ---------------------------------------------------------------- the live step
def read_journal(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue
    return out


def advance(asset, cfg, reg_ms, journal_path, models, bars, fund, readings, now_s=None, seeds=None, log=print,
            fallback="rule", feats_cache=None):
    """Decide every closed bar after REGISTERED not yet recorded (and covered by the readings and a model), append the
    decisions to the journal. bars: the tail frame (enough rows for the feature window before the first pending bar).
    readings: (times, raw, last_open_ms). models: [(data_end_close_ms, model dict)] oldest first. -> new records.
    fallback: what a 'do no harm' seed does ("rule" = flat, Phase 5; "trend" = the trend reference, Phase 6); with a
    fallback other than "rule" each record also says each seed's mode ("model" / "trend"). feats_cache: a dict shared
    by several books in one step (the same bars give the same inputs; keyed by the window's first and last open)."""
    p5 = cfg["phase5"]["forward"]
    seeds = list(p5["seeds"] if seeds is None else seeds)
    acts = np.asarray(cfg["actions"], dtype=float)
    zero = int(np.argmin(np.abs(acts)))
    mh = int(cfg["policy"]["min_hold_bars"])
    rows = read_journal(journal_path)
    last_t = rows[-1]["t"] if rows else None
    state = dict((s, (rows[-1]["ip"][i], rows[-1]["since"][i])) if rows else (s, (zero, mh)) for i, s in enumerate(seeds))
    open_ms = np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64)
    close_ms = open_ms + BAR_MS
    times, raw, r_last = readings
    pend = (close_ms > int(reg_ms))
    if last_t is not None:
        pend &= open_ms > int(last_t)
    if r_last is None:
        return []
    pend &= open_ms <= int(r_last)
    idx = np.nonzero(pend)[0]
    if not len(idx) or not models:
        return []
    ends = np.array([m[0] for m in models])
    which = np.searchsorted(ends, close_ms[idx], side="right") - 1      # newest model with data end <= the bar's close
    ok = which >= 0
    if not ok.all():
        idx, which = idx[ok], which[ok]
        if not len(idx):
            return []
    i0, i1 = int(idx[0]), int(idx[-1])
    W = int(p5["feature_window_bars"])
    lo = max(0, i0 - W)
    b = bars.iloc[lo:i1 + 1]
    f = fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(close_ms[i1])] if len(fund) else fund
    key = (asset, int(open_ms[lo]), int(open_ms[i1]), len(times))
    feats = None if feats_cache is None else feats_cache.get(key)
    if feats is None:
        rf = readings_on(b.index, times, raw)
        feats = features4.build(b, f, cfg["features"], rf).astype("float32")
        if feats_cache is not None:
            feats_cache[key] = feats
    model = CostModel.from_cfg(cfg["costs"])
    M = market_arrays(b, f, feats, model, cfg["qagent"])
    rel = idx - lo
    blocks, start = [], 0
    for j in range(1, len(rel) + 1):
        if j == len(rel) or which[j] != which[start]:
            blocks.append((models[which[start]][1], slice(int(rel[start]), int(rel[j - 1]) + 1)))
            start = j
    ips, new = decisions(blocks, (asset, feats), M["k"][rel], M["c1"][rel], acts, cfg["qagent"], mh, state, seeds,
                         fallback=fallback)
    now_s = time.time() if now_s is None else now_s
    av = feats[features4.FLAGS].values[rel]
    recs = []
    for j, i in enumerate(idx):
        mdl = models[which[j]][1]
        ipj = [int(ips[s][j]) for s in seeds]
        recs.append({"t": int(open_ms[i]), "c": int(close_ms[i]), "m": mdl["id"], "ip": ipj,
                     "req": [float(acts[x]) for x in ipj],
                     "fb": [bool(mdl["seeds"][str(s)]["fallback"].get(asset, False)) for s in seeds],
                     "av": int("".join("1" if x else "0" for x in av[j] > 0.5), 2),
                     "at": round(float(now_s), 1), "lag_s": round(float(now_s) - close_ms[i] / 1000.0, 1)})
        if fallback != "rule":
            recs[-1]["mode"] = [fallback if f_ else "model" for f_ in recs[-1]["fb"]]
    # the policy state after each record (needed to resume): recompute 'since' per record cheaply
    since_run = dict((s, state[s][1]) for s in seeds)
    ip_prev = dict((s, state[s][0]) for s in seeds)
    for r in recs:
        sv = []
        for k, s in enumerate(seeds):
            since_run[s] = 1 if r["ip"][k] != ip_prev[s] else since_run[s] + 1
            ip_prev[s] = r["ip"][k]
            sv.append(int(since_run[s]))
        r["since"] = sv
    os.makedirs(os.path.dirname(journal_path), exist_ok=True)
    with open(journal_path, "a", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    return recs


def risk_and_book(cfg, bars, fund, journal, reg_ms, seeds=None, stake=None):
    """Recorded requests -> each seed through the Phase 3 risk manager -> the book (mean of seeds) -> the shared
    backtester's per-bar frame from REGISTERED. -> dict or None (nothing decided yet)."""
    from . import backtest
    p5 = cfg["phase5"]["forward"]
    seeds = list(p5["seeds"] if seeds is None else seeds)
    stake = float(p5["stake_usd"] if stake is None else stake)
    if not journal:
        return None
    open_ms = np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64)
    close_ms = open_ms + BAR_MS
    last_t = journal[-1]["t"]
    keep = open_ms <= last_t
    b = bars[keep]
    open_ms, close_ms = open_ms[keep], close_ms[keep]
    f = fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(close_ms[-1])] if len(fund) else fund
    lo = int(np.searchsorted(close_ms, int(reg_ms), side="right"))       # first bar closing after REGISTERED
    n = len(b)
    by_t = dict((r["t"], r) for r in journal)
    req = np.zeros((len(seeds), n))
    cur = np.zeros(len(seeds))
    for i in range(lo, n):
        r = by_t.get(int(open_ms[i]))
        if r is not None:
            cur = np.asarray(r["req"], dtype=float)
        req[:, i] = cur
    model = CostModel.from_cfg(cfg["costs"])
    M = market_arrays(b, f, None, model, cfg["qagent"])
    lr = np.log(b["close"].astype(float)).diff()
    rcfg = risk3.Risk3Config.from_cfg(cfg["risk3"])
    vs = lr.rolling(int(rcfg.vol_short.split("_")[1]), min_periods=int(rcfg.vol_short.split("_")[1])).std().values
    vl = lr.rolling(int(rcfg.vol_long.split("_")[1]), min_periods=int(rcfg.vol_long.split("_")[1])).std().values
    vs = vs.astype(np.float32).astype(float)
    vl = vl.astype(np.float32).astype(float)
    d = int(model.delay_bars)
    ex = np.zeros((len(seeds), n))
    for k in range(len(seeds)):
        st = risk3.Stepper(rcfg, model, None, False)
        st.seed([0.0] * (d + 1), 0.0)
        for t in range(lo, n):
            ex[k, t] = st.step(t, req[k, t], close_ms[t], M["r_bar"][t], M["r_px"][t - 1] if t >= 1 else 0.0,
                               M["vol"][t - d] if t - d >= 0 else 0.0, M["rate"][t], float(vs[t]), float(vl[t]))
    book = ex.mean(axis=0)
    fr = backtest.run(b, book, model, f)["frame"]
    spot = CostModel(fee_side=model.fee_side, half_spread_bps=model.half_spread_bps, slippage_coef=model.slippage_coef,
                     slippage_vol_window=model.slippage_vol_window, funding=False, delay_bars=model.delay_bars)
    bh_t = (np.arange(n) >= lo).astype(float)
    frb = backtest.run(b, bh_t, spot, f)["frame"]
    rn = fr["r_net"].values[lo:]
    eq = stake * np.cumprod(1.0 + rn)
    beq = stake * np.cumprod(1.0 + frb["r_net"].values[lo:])
    return {"lo": lo, "n": n, "bars": b, "req": req, "exec": ex, "book": book, "frame": fr.iloc[lo:], "equity": eq,
            "bh_equity": beq, "close_ms": close_ms, "open_ms": open_ms}


# ---------------------------------------------------------------- the forward == batch check (Phase 4's own data)
def forward_vs_batch(cfg, model_path, start, end=None, steps=4, assets=ASSETS, journal_dir=None, log=print):
    """Phase 4's batch path (its stored fold values -> policy3.decide from flat -> risk3.apply -> backtester) against this
    module's forward path (features from a bar window + readings rows, the exported model, decisions in `steps` calls
    on data cut at each call's bar, recorded, then the book rebuilt from the record) on the same bars (Phase 4's own:
    BTC perp store, ETH engine file, readings snapshot). -> report dict."""
    import tempfile
    from . import backtest, phase4, pool4
    model = load_model(model_path)
    fold = int(model["info"]["phase4_fold"])
    seeds = sorted(int(s) for s in model["seeds"])
    acts = np.asarray(cfg["actions"], dtype=float)
    zero = int(np.argmin(np.abs(acts)))
    mh = int(cfg["policy"]["min_hold_bars"])
    root = os.path.join(resolve(cfg["report"]["models_dir"]), model["info"]["work_hash"], cfg["primary"])
    jd = journal_dir or tempfile.mkdtemp(prefix="p5_fwd_")
    rep = {"model": os.path.basename(model_path), "fold": fold, "assets": {}, "steps": int(steps)}
    allok, ex_max, eq_max, w_max, nb = True, 0.0, 0.0, 0.0, 0
    for asset in assets:
        bars, fund = pool4.load_bars(cfg, asset, True, log)
        A = pool4.Asset(os.path.join(pool4.cache_dir(cfg), asset))
        assert A.n == len(bars)
        cm = np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64) + BAR_MS
        te_lo = int(model["info"]["geo"][asset]["te_lo"])
        te_hi = int(model["info"]["geo"][asset]["te_hi"])
        i_s = max(te_lo, int(np.searchsorted(bars.index, pd.Timestamp(start, tz="UTC"))))
        i_e = min(te_hi, int(np.searchsorted(bars.index, pd.Timestamp(end, tz="UTC")))) - 1 if end else te_hi - 1
        reg = int(cm[i_s - 1])
        # ---- batch (Phase 4's code and stored values)
        feats = pd.DataFrame(np.asarray(A.X), index=bars.index, columns=A.columns)
        from .env import Market
        m = Market(bars, fund, feats, pool4.asset_model(cfg, asset))
        del feats
        rd = dict((k, np.asarray(v)) for k, v in A.rd.items())
        bt = {}
        for s in seeds:
            with open(os.path.join(root, "s%d" % s, "rec_f%02d_pool.json" % fold), encoding="utf-8") as fh:
                fb = json.load(fh)["assets"][asset]["fallback"]
            Wst = np.load(os.path.join(root, "s%d" % s, "w_f%02d_%s.npy" % (fold, asset)))
            W = neutral_w(len(Wst), acts, 0.0) if fb else Wst
            Wsl = W[i_s - te_lo:i_e + 1 - te_lo]
            Q = q_from_w(Wsl, rd["k"][i_s:i_e + 1], rd["c1"][i_s:i_e + 1], cost_matrix(acts), cfg["qagent"])
            ip, _ = policy3.decide(Q, acts, zero, mh)
            tgt = np.zeros(len(bars))
            tgt[i_s:i_e + 1] = acts[ip]
            ex = risk3.apply(m, tgt, i_s, i_e + 1, dict(cfg["risk3"]), log_events=False)["exec"]
            bt[s] = {"ip": ip, "exec": ex, "Wst": Wst[i_s - te_lo:i_e + 1 - te_lo], "fb": fb}
        book_b = np.mean([bt[s]["exec"] for s in seeds], axis=0)
        frb = backtest.run(bars.iloc[:i_e + 1], book_b[:i_e + 1], m.model, fund)["frame"]
        eq_b = float(cfg["phase5"]["forward"]["stake_usd"]) * np.cumprod(1.0 + frb["r_net"].values[i_s:])
        del m
        # ---- forward (this module), in `steps` calls on data cut at each call
        snap = os.path.join(pool4.cache_dir(cfg), "readings_%s.npz" % asset)
        jp = os.path.join(jd, "decisions_%s.jsonl" % asset)
        if os.path.exists(jp):
            os.remove(jp)
        cuts = sorted(set(int(x) for x in np.linspace(i_s, i_e, int(steps) + 1)[1:]))
        Wn = int(cfg["phase5"]["forward"]["feature_window_bars"])
        models = [(int(model["data_end_close_ms"]), model)]
        for c in cuts:
            lo = max(0, c - Wn - 900 - (c - i_s))
            bc = bars.iloc[lo:c + 1]
            fc = fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(cm[c])]
            t, raw, last = readings_tail(asset, int(bc.index[0].value // 10**6), snapshot=snap)
            keep = t <= int(bars.index[c].value // 10**6)
            t, raw = t[keep], dict((k, v[keep]) for k, v in raw.items())
            advance(asset, cfg, reg, jp, models, bc, fc, (t, raw, int(t[-1])), seeds=seeds, log=log)
        J = read_journal(jp)
        bc = bars.iloc[max(0, i_s - Wn - 900):i_e + 1]
        B = risk_and_book(cfg, bc, fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(cm[i_e])], J, reg, seeds=seeds)
        ipf = np.array([r["ip"] for r in J])
        same = len(J) == i_e + 1 - i_s and all(np.array_equal(ipf[:, k], bt[s]["ip"]) for k, s in enumerate(seeds))
        exd = max(float(np.max(np.abs(B["exec"][k, B["lo"]:] - bt[s]["exec"][i_s:i_e + 1]))) for k, s in enumerate(seeds))
        eqd = float(np.max(np.abs(B["equity"] - eq_b) / eq_b))
        # values: forward W on the slice vs Phase 4's stored W
        bw = bars.iloc[max(0, i_s - Wn):i_e + 1]
        t, raw, _ = readings_tail(asset, int(bw.index[0].value // 10**6), snapshot=snap)
        fw = features4.build(bw, fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(cm[i_e])], cfg["features"],
                             readings_on(bw.index, t, raw)).astype("float32")
        fw = fw.iloc[len(bw) - (i_e + 1 - i_s):]
        wd = 0.0
        for s in seeds:
            if not bt[s]["fb"]:
                wd = max(wd, float(np.max(np.abs(model_w(model, s, asset, fw) - bt[s]["Wst"]))))
        rep["assets"][asset] = {"start": _utc(cm[i_s - 1]), "end": _utc(cm[i_e]), "bars": int(i_e + 1 - i_s),
                                "decisions_equal": bool(same), "exec_max_diff": exd, "equity_max_rel_diff": eqd,
                                "w_max_diff": wd, "fallback": dict((str(s), bt[s]["fb"]) for s in seeds),
                                "changes": dict((str(s), int(np.count_nonzero(np.diff(bt[s]["ip"])))) for s in seeds),
                                "book_return_pct": float(100 * (B["equity"][-1] / B["equity"][0] - 1)) if len(B["equity"]) else 0.0}
        allok &= same
        ex_max, eq_max, w_max, nb = max(ex_max, exd), max(eq_max, eqd), max(w_max, wd), nb + i_e + 1 - i_s
        log("forward vs batch %s: %s" % (asset, rep["assets"][asset]))
    rep.update({"decisions_equal": bool(allok), "exec_max_diff": ex_max, "equity_max_diff": eq_max, "w_max_diff": w_max,
                "bars": nb, "start": min(v["start"] for v in rep["assets"].values()),
                "end": max(v["end"] for v in rep["assets"].values())})
    return rep
