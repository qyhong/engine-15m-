# -*- coding: utf-8 -*-
"""Queue family H80-H89: PLACEBO, PERMUTATION AND BOOTSTRAP tests of the Setups book (`b_targets`) and of the two
variants found on the same history (H67 30-day trend filter, H68 wait after a stop-out). Research only; every study is
registered in research/HYPOTHESES.md (blocks H80 .. H89) before any number. Reads the evidence store and the cached
fits; changes nothing in the engine, the books or the vault.

    python research/queue/placebo.py --study H80 --fits-dir <fits_today> --out <folder>
    python research/queue/placebo.py --study H80 --fits-dir <fits_today> --out <folder> --estimate   # CPU hours
    python research/queue/placebo.py --study H80 --fits-dir <fits_today> --out <folder> --smoke      # < 2 minutes

Resumable: finished draws are appended to <out>/draws_<group>.jsonl in batches (one line per batch, at least once a
minute); running the same command again skips every recorded draw and never records one twice. Lines written by
another version of this file, seed or draw count are ignored (the fingerprint). progress.json is rewritten with every
batch. --smoke writes into <out>/smoke, never into the study's own files.
On success: results.json, report.md and an empty DONE; exit code 0. One process, one thread; one market group in
memory at a time.

THE HOLDOUT IS NOT READ: every market group is cut at its last stored session at or before CUT (below; the one place
it is set). load_group() refuses any other end.
"""
import argparse
import gc
import hashlib
import json
import math
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")                               # one thread

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, live, policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

# ------------------------------------------------------------------ fixed for the whole family
CUT = "2025-11-10 23:45"            # THE ONE PLACE the end is set: nothing at or after the holdout (2025-11-11) is read
SMOKE_CUT = "2022-12-31 23:45"      # --smoke only: SPX to the end of 2022 (labelled SMOKE, numbers never reported)
MID = "2023-06-08"                  # halves split here (by entry bar)
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
MARKETS = [a for _g, aa in GROUPS for a in aa]
VAULT = ("BTCUSDT", "ETHUSDT")
START = shadows.START_EQUITY
DAY_MS = 86400000
RULE_CURRENT = dict(shadows.CHALLENGERS["b_targets"]["rule"])        # {"targets": True, "early": True}
RULE_TREND = dict(shadows.CHALLENGERS["b_trend30"]["rule"])          # + trend_days 30
RULE_WAIT = dict(shadows.CHALLENGERS["b_wait_stop"]["rule"])         # + wait_after_stop
SEED0 = 20261122
NSTAT = 15                           # per market and draw: (trades, sum_r, wins, flat_bars, bars) x (all, h1, h2)

# Seconds of ONE processor, measured on the research server on 22 Nov 2026 (timing runs, `--time-draws 2`, full window to
# CUT; they printed seconds and memory only): loading a market group with its real books and gates, and one draw of each
# study on that group. Used by --estimate and progress.json.
PREP_S = {"crypto": 24.0, "metals": 15.0, "fx": 9.5, "index": 2.5, "energy": 14.5}
DRAW_S = {
    "H80": {"crypto": 1.54, "metals": 1.04, "fx": 0.54, "index": 0.12, "energy": 0.95},
    "H82": {"crypto": 0.16, "metals": 0.10, "fx": 0.05, "index": 0.01, "energy": 0.09},
    "H83": {"crypto": 1.61, "metals": 1.08, "fx": 0.56, "index": 0.13, "energy": 0.99},
    "H84": {"crypto": 1.51, "metals": 0.85, "fx": 0.48, "index": 0.10, "energy": 0.87},
    "H85": {"crypto": 1.17, "metals": 0.78, "fx": 0.42, "index": 0.10, "energy": 0.74},
    "H86": {"crypto": 1.57, "metals": 1.05, "fx": 0.55, "index": 0.13, "energy": 0.96},
}

STUDIES = {
    "H80": {"kind": "book", "draws": 10000, "title": "odds placebo: each market's odds circularly shifted in time (>= 30 days)"},
    "H81": {"kind": "side", "draws": 100000, "title": "side placebo: the real trades' sides permuted within market and month"},
    "H82": {"kind": "trade", "draws": 100000, "title": "entry-time placebo: the real trades at random bars of the same month"},
    "H83": {"kind": "book", "draws": 10000, "title": "trend-filter placebo: the 30-day move circularly shifted in time (>= 60 days)"},
    "H84": {"kind": "book", "draws": 11000, "title": "wait-after-stop placebo: the wait switched on after random exits"},
    "H85": {"kind": "book", "draws": 13000, "title": "higher-timeframe placebo: bias and tide circularly shifted in time (>= 30 days)"},
    "H86": {"kind": "book", "draws": 10000, "title": "stop-size placebo: the volatility unit shuffled across bars within each month"},
    "H87": {"kind": "boot", "draws": 20000, "title": "block bootstrap of 12-month results (current rule, H67, H68)"},
    "H88": {"kind": "costs", "draws": 5000, "title": "costs surface: fee x entry slip"},
    "H89": {"kind": "years", "draws": 10000, "title": "year by year and leave one year out"},
    # registered after the H81 audit (H81 void, H82 withdrawn): causal versions, no information the book did not have
    "H81b": {"kind": "causal", "draws": 200000, "seed": 20261122812,
             "title": "causal side placebo: each trade's side drawn from the long share of the book's previous 20 trades "
                      "on the market (and a fair coin)"},
    "H82b": {"kind": "causal", "draws": 200000, "seed": 20261122822,
             "title": "causal entry-time placebo: each trade, same side, moved to a random bar at or after its real entry, "
                      "within the median of the book's previous 20 entry gaps"},
}
for _k, _s in STUDIES.items():
    if "seed" not in _s:
        _s["seed"] = SEED0 * 100 + int(_k[1:])                # e.g. 2026112280 for H80


def log(msg):
    print("%s %s" % (time.strftime("%H:%M:%S", time.gmtime()), msg), flush=True)


# =====================================================================================
# data: one market group, cut at CUT
# =====================================================================================
def group_end(g, assets, cut):
    """The group's last stored session at or before `cut` (never after CUT)."""
    from engine15 import evcache
    if cut > CUT:
        raise RuntimeError("cut %s is after the holdout cut %s" % (cut, CUT))
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, g, assets[0]))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (g, assets[0]))
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(pd.Timestamp(cut, tz="UTC"), side="right"))
    return str(full[k - 1])[:16]


def fits_overlay(src_root, out_dir, g):
    """A folder of links to the cached fits of group g, inside our own --out: a fit missing from the cache is then
    written here, never into the source folder (which belongs to the engine and is read only)."""
    src = os.path.join(src_root, g)
    dst = os.path.join(out_dir, "fits_overlay", g)
    os.makedirs(dst, exist_ok=True)
    have = set(os.listdir(dst))
    if os.path.isdir(src):
        for f in os.listdir(src):
            if f.endswith(".npz") and f not in have:
                os.symlink(os.path.join(os.path.abspath(src), f), os.path.join(dst, f))
    return dst


def prep_lean(group, assets, fits_dir, end, log=log, chunk=20000):
    """research/h59_half_be.prep_cut, line for line, except that the voices' "speaks" mask is built in row chunks, before
    the trust is computed, instead of materialising a market's whole feature matrix at once after it (that step took
    the crypto group over 4 GB).
    The odds are the same numbers (checked against prep_cut in a smoke run on the server)."""
    from engine15 import evcache, labels, leanprep, model
    from engine15.config import voting_for
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    ns = set(st.meta["n"] for st in stores.values())
    if len(ns) != 1:
        raise RuntimeError("stores of %s disagree on rows: %s" % (group, ns))
    full = pd.DatetimeIndex(pd.to_datetime(stores[assets[0]].times_ms(), unit="ms", utc=True))
    for a in assets[1:]:
        assert np.array_equal(stores[a].times_ms(), stores[assets[0]].times_ms())
    n = int(full.searchsorted(pd.Timestamp(end, tz="UTC"), side="right"))
    if str(full[n - 1])[:16] != end:
        raise RuntimeError("%s: the store has no session at %s (last <= it: %s)" % (group, end, full[n - 1]))
    times = full[:n]
    cfg = dict(CFG, assets=tuple(assets), birth=CFG["birth"], voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        ev[a] = st.frame(full).iloc[:n]
        X[a] = st.X()[:n]
        ready[a] = st.ready()[:n]
        b = data.load(a).reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    t0 = time.time()
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n, fits_dir)
    log("%s: %d sessions to %s; voices walked from %s: %d refits, %d from the cache (%.0fs)" % (
        group, n, str(times[-1])[:16], cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    del models
    lo = birth_idx
    speaks_of = {}
    for a in assets:                                             # the change: row chunks, and done BEFORE trust_tail
        speaks = np.zeros((n - lo, len(model.VOICE_NAMES)), dtype=bool)     # so the feature matrices can be freed first
        for s0 in range(lo, n, chunk):
            Xa = np.asarray(X[a][s0:min(s0 + chunk, n)])
            for vi, v in enumerate(model.VOICE_NAMES):
                if model._COLS[v]:
                    speaks[s0 - lo:s0 - lo + len(Xa), vi] = np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0
            del Xa
        speaks_of[a] = speaks
    del X, ready, stores                                         # unmaps the feature matrices (memory-mapped files)
    gc.collect()
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    odds = {}
    for a in assets:
        speaks = speaks_of.pop(a)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        del speaks, w
        probs[a] = None
    del probs, trust
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds,
            "birth_idx": birth_idx, "_refits": int(frep["refits"])}


def load_group(g, assets, fits_root, out_dir, cut=CUT):
    end = group_end(g, assets, cut)
    t0 = time.time()
    prep = prep_lean(g, assets, fits_overlay(fits_root, out_dir, g), end, log=log)
    times = prep["times"]
    if str(times[-1])[:16] > CUT:                                # the holdout guard, checked again on what was loaded
        raise RuntimeError("%s: data run to %s, after %s" % (g, times[-1], CUT))
    prep["_load_s"] = time.time() - t0
    return prep


def market_ctx(prep, a):
    times = prep["times"]
    n = len(times)
    ok = np.isfinite(prep["odds"][a][:, 0])
    lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
    aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
    inp = shadows.book_inputs(prep, a)
    cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    tgt = aux["targets"]
    cols = list(tgt.columns)
    tarr = dict((col, np.asarray(tgt[col].values, dtype=float)) for col in cols)
    tms = np.asarray(data.to_ms(times), dtype="int64")
    mid = min(max(int(times.searchsorted(pd.Timestamp(MID, tz="UTC"))), lo + 1), n - 1)
    month = np.asarray(times.year * 12 + times.month - 1, dtype="int64")
    return {"a": a, "lo": lo, "n": n, "mid": mid, "aux": aux, "inp": inp, "cfg": cfg, "tms": tms, "month": month,
            "row_of": (lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)),
            "trow": (lambda k, tarr=tarr: dict((col, v[k]) for col, v in tarr.items())),
            "years": np.asarray(times.year, dtype="int64")}


def run_book(ctx, rule, odds=None, tide=None, bias=None, unit=None, aux=None):
    """The engine's own shadows.run on one market, any input replaced by a scrambled copy."""
    inp = ctx["inp"]
    return shadows.run(inp["px"], inp["odds"] if odds is None else odds, inp["shock"], inp["tide"] if tide is None else tide,
                       inp["unit"] if unit is None else unit, ctx["cfg"], ctx["lo"], ctx["n"],
                       bias=inp["bias"] if bias is None else bias, guard=inp["guard"], rule=dict(rule),
                       aux=ctx["aux"] if aux is None else aux, times_ms=ctx["tms"], row_of=ctx["row_of"])


def stats_from(i_in, r, won, held, lo, mid, hi):
    """(trades, sum_r, wins, flat_bars, bars) for all / first half / second half, trades by entry bar."""
    i_in = np.asarray(i_in, dtype="int64")
    r = np.asarray(r, dtype=float)
    won = np.asarray(won, dtype=bool)
    ok = np.isfinite(r)
    out = []
    for a, z in ((lo, hi), (lo, mid), (mid, hi)):
        m = ok & (i_in >= a) & (i_in < z)
        flat = int((held[a:z] == 0).sum()) if held is not None else 0
        out += [int(m.sum()), float(r[m].sum()), int((won & m).sum()), flat, int(z - a)]
    return out


def book_stats(book, ctx):
    tr = book["trades"]
    return stats_from(tr.i_in.values, tr.r_mult.values, tr.pnl_usd.values > 0, book["held"], ctx["lo"], ctx["mid"],
                      ctx["n"])


# =====================================================================================
# scramblers (pure; tested in tests/test_queue_placebo.py)
# =====================================================================================
def shift_src(tms, lo, hi, u, min_days, margin_days=7):
    """Circular shift in TIME over rows lo .. hi-1: row j takes the row in force at t_j - delta (wrapped round the
    window), delta = min_days + u * (window - 2 * min_days - margin_days) days. The margin covers the gap to the row in
    force (weekends, closed hours), so every row's source is at least min_days away, both ways round the circle.
    -> int array of source rows for lo .. hi-1."""
    t = np.asarray(tms[lo:hi], dtype="int64")
    W = int(t[-1] - t[0]) + int(CFG["bar_ms"])
    md, mg = int(min_days * DAY_MS), int(margin_days * DAY_MS)
    if W <= 2 * md + mg + DAY_MS:
        raise ValueError("window of %.0f days too short for a %d-day shift" % (W / DAY_MS, min_days))
    delta = md + int(u * (W - 2 * md - mg))
    tau = t - delta
    tau = np.where(tau < t[0], tau + W, tau)
    j = np.clip(np.searchsorted(t, tau, side="right") - 1, 0, len(t) - 1)
    return j + lo


def apply_src(arr, src, lo, hi):
    out = np.array(arr, copy=True)
    out[lo:hi] = np.asarray(arr)[src]
    return out


def month_shuffle_src(month, lo, hi, rng):
    """A permutation of rows lo .. hi-1 that moves rows only within their calendar month. -> source rows."""
    m = np.asarray(month[lo:hi])
    key = rng.random(len(m))
    order = np.lexsort((key, m))                                 # rows grouped by month, random order inside
    base = np.argsort(m, kind="stable")                          # rows grouped by month, in time order
    src = np.empty(len(m), dtype="int64")
    src[base] = order
    return src + lo


def permute_within(groups, rng):
    """A permutation that moves items only within their group: out[i] is the index whose value item i receives."""
    g = np.asarray(groups)
    order = np.lexsort((rng.random(len(g)), g))
    base = np.argsort(g, kind="stable")
    src = np.empty(len(g), dtype="int64")
    src[base] = order
    return src


def draw_rng(seed, k, *more):
    """The generator of draw k (and of one market / group inside it): draw k is reproducible on its own."""
    return np.random.default_rng([int(seed), int(k)] + [int(x) for x in more])


# =====================================================================================
# the research-side copy of the Setups loop (H84 only): shadows.run reduced to the b_targets path (targets, early,
# wait_after_stop, trend_days), with ONE hook: which exit switches the wait on. Gate: with the hook = "the exit word is
# STOP" it must give b_wait_stop, and with no wait b_targets, trade for trade on every market (checked in each run).
# =====================================================================================
def run_setups_copy(px, odds, shock, tide, unit, cfg, lo, hi, bias=None, guard=None, rule=None, aux=None,
                    times_ms=None, row_of=None, trigger=None):
    from engine15 import labels
    from engine15.backtest import leverage as _lev
    rule = rule or {}
    use_targets = bool(rule.get("targets"))
    early = bool(rule.get("early")) and cfg.get("early_fill") is True and not int(cfg.get("fill_delay_bars", 0) or 0)
    wait = bool(rule.get("wait_after_stop"))
    if wait and trigger is None:
        trigger = (lambda word: word == "STOP")                  # the engine's own rule
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    n = len(c)
    held = np.zeros(n, dtype=np.int8)
    eq_arr = np.full(n, np.nan)
    trades = []
    fee = cfg["cost_side"]
    tms = (lambda i: None) if times_ms is None else (lambda i: int(times_ms[i]))
    S = {"pos": 0, "idle": 0, "qty": 0.0, "entry": 0.0, "eq": START, "stop": np.nan, "why_in": "", "t_in": -1,
         "t_in_ms": None, "stop0": np.nan}
    tg = {"t1": None, "t2": None, "t1_hit": False}
    part = {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []}
    ws = {"on": 0, "blocked": 0, "episodes": 0} if wait else None
    pending = None

    def book_trade(i, price, why, q0, pnl, fees_t):
        p_in, s0 = S["entry"], S["stop0"]
        risk = q0 * abs(p_in - s0) if s0 == s0 else np.nan
        r = pnl / risk if risk and risk == risk else np.nan
        trades.append((S["t_in_ms"], tms(i), S["t_in"], i, S["pos"], p_in, price, S["why_in"], why,
                       pnl / (q0 * p_in) * 100.0, S["eq"], q0, pnl, fees_t, s0, risk, r, tg["t1"], tg["t2"]))

    def close(i, price, why):
        nonlocal part
        qty, pos, entry = S["qty"], S["pos"], S["entry"]
        gross = qty * pos * (price - entry)
        fees = fee * qty * (entry + price)
        S["eq"] += gross - fees
        if part["q"]:
            tot_q = part["q"] + qty
            p_out = (part["qpx"] + qty * price) / tot_q
            book_trade(i, p_out, "+".join(part["tags"] + [why]), tot_q, part["pnl"] + gross - fees, part["fees"] + fees)
        else:
            book_trade(i, price, why, qty, gross - fees, fees)
        S["pos"], S["qty"], S["stop"] = 0, 0.0, np.nan
        part = {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []}
        tg.update(t1=None, t2=None, t1_hit=False)

    def take_part(price, q, tag):
        gross = q * S["pos"] * (price - S["entry"])
        fees = fee * q * (S["entry"] + price)
        S["eq"] += gross - fees
        part["pnl"] += gross - fees
        part["fees"] += fees
        part["qpx"] += q * price
        part["q"] += q
        part["tags"].append(tag)
        S["qty"] -= q

    def open_pos(i, side, price, why, k_dec, at_ms=None):
        S["pos"], S["entry"], S["t_in"], S["why_in"] = side, price, i, why
        S["qty"] = S["eq"] * _lev(cfg, price, cfg["stop_units"] * unit[i - 1]) / price
        S["t_in_ms"] = tms(i) if at_ms is None else at_ms
        S["stop"] = price - side * cfg["stop_units"] * unit[i - 1]
        S["stop0"] = S["stop"]
        if ws is not None:
            ws["on"] = 0
        tg.update(t1=None, t2=None, t1_hit=False)
        if use_targets and row_of is not None:
            t = live.plan_targets(int(side), float(price), float(S["stop"]), row_of(k_dec))
            tg.update(t1=t.get("target_1"), t2=t.get("target_2"))

    p_up, p_dn = odds[:, labels.UP], odds[:, labels.DOWN]
    trend_days = int(rule.get("trend_days") or 0)
    move = (aux or {}).get("trend_move") if trend_days else None
    if trend_days and move is None:
        move = shadows.trend_move(times_ms, c, trend_days, lo, hi)
    for i in range(lo, hi):
        if pending is not None and len(pending) > 3 and pending[3] > 0:
            pending = tuple(pending[:3]) + (pending[3] - 1,)
        elif pending is not None:
            a, target, why = pending[:3]
            if S["pos"] != 0 and target != S["pos"]:
                close(i, o[i], a)
                if ws is not None and target == 0 and trigger(a):
                    ws["on"] = 1                                 # placebo hooks only: the engine's rule never fires here
            if target != 0 and S["pos"] == 0:
                open_pos(i, target, o[i], a, i - 1)
            pending = None
        held[i] = S["pos"]
        be_moved = tg["t1_hit"] and use_targets
        pos, stop = S["pos"], S["stop"]
        if pos == 1 and l[i] <= stop:
            word = "STOP_BE" if be_moved else "STOP"
            close(i, min(o[i], stop), word)
            S["idle"] = 0
            if ws is not None and trigger(word):
                ws["on"] = 1
        elif pos == -1 and h[i] >= stop:
            word = "STOP_BE" if be_moved else "STOP"
            close(i, max(o[i], stop), word)
            S["idle"] = 0
            if ws is not None and trigger(word):
                ws["on"] = 1
        if use_targets and S["pos"] != 0 and tg["t1"] is not None:
            pos = S["pos"]
            reach = (lambda t: h[i] >= t) if pos == 1 else (lambda t: l[i] <= t)
            if not tg["t1_hit"] and reach(tg["t1"]):
                take_part(tg["t1"], S["qty"] * shadows.PART, "T1")
                tg["t1_hit"] = True
                S["stop"] = S["entry"]
            if tg["t1_hit"] and tg["t2"] is not None and S["pos"] != 0 and reach(tg["t2"]):
                close(i, tg["t2"], "T2")
                S["idle"] = 0
                if ws is not None and trigger("T2"):
                    ws["on"] = 1
        pos = S["pos"]
        pu = p_up[i]
        a, target, why = policy.decide(pos, S["idle"], None if pu != pu else pu, p_dn[i], bool(shock[i]),
                                       tide[i] if tide[i] == tide[i] else 0.0, cfg,
                                       bias=0 if bias is None or bias[i] != bias[i] else int(bias[i]),
                                       guard=False if guard is None else bool(guard[i]))
        if ws is not None and ws["on"] and pos == 0 and a == policy.FORCED:
            a, target, why = policy.IDLE, 0, "wait_for_signal_after_stop"
            ws["blocked"] += 1
            if ws["on"] == 1:
                ws["on"], ws["episodes"] = 2, ws["episodes"] + 1
        if move is not None and target != 0 and a in (policy.ENTER, policy.FORCED, policy.FLIP):
            mv = move[i]
            if mv == mv and mv != 0 and (mv > 0) != (target > 0):
                if a == policy.FLIP:
                    target, why = 0, "trend_filter_flat"
                else:
                    a, target, why = policy.IDLE, 0, "trend_filter"
        if a == policy.IDLE:
            S["idle"] += 1
        elif a == policy.STEP_ASIDE:
            S["idle"] = 1
        elif a != policy.HOLD:
            S["idle"] = 0
        if a in (policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE):
            if early and pos == 0 and target != 0 and pending is None and a in (policy.ENTER, policy.FORCED):
                open_pos(i + 1, target, c[i], a, i, at_ms=None if times_ms is None else int(times_ms[i]) + CFG["bar_ms"])
            elif not (a == policy.STEP_ASIDE and pos == 0):
                delay = int(cfg.get("fill_delay_bars", 0) or 0)
                if not (delay and pending is not None and pending[1] == target):
                    pending = (a, target, why) if not delay else (a, target, why, delay)
        eq_arr[i] = S["eq"] + (S["qty"] * S["pos"] * (c[i] - S["entry"]) if S["pos"] else 0.0)
    tr = pd.DataFrame(trades, columns=shadows.TRADE_COLS)
    return {"trades": tr, "equity": eq_arr, "held": held, "wait": dict(ws) if ws is not None else None}


def copy_book(ctx, rule, trigger=None):
    inp = ctx["inp"]
    return run_setups_copy(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], ctx["cfg"], ctx["lo"], ctx["n"],
                           bias=inp["bias"], guard=inp["guard"], rule=dict(rule), aux=ctx["aux"], times_ms=ctx["tms"],
                           row_of=ctx["row_of"], trigger=trigger)


def same_book(ref, mine, lo, n, tol=1e-6):
    import h62_setups_wide_stop as h62
    return h62.same_book(ref, mine, lo, n, tol=tol)


# =====================================================================================
# trade-level replay (H81, H82): one trade with the Setups book's own stop, Target 1 (half off, stop to the entry),
# Target 2, in the engine's order inside a bar, ended at the latest at bar e (at its open when the real trade ended
# there by a decision, else at its close). Its R does not depend on size: qty 1. Gate: with the real side, entry bar
# and window it gives every real trade's R and exit, on every market (checked in each run).
# =====================================================================================
INTRABAR = ("STOP", "STOP_BE", "T2")


def open_exit_of(why_out):
    """True when the real trade ended at a bar's OPEN by a decision (a flip, a step aside), not inside a bar."""
    return str(why_out).split("+")[-1] not in INTRABAR


def replay_trade(side, i0, p, k, e, open_exit, px, unit, cfg, trow):
    """-> (R, last exit word, exit bar). Entry at price p, first bar checked i0, decision row k (targets and stop
    from row k: the engine uses unit[i0 - 1] and row i0 - 1)."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    fee = cfg["cost_side"]
    stop = p - side * cfg["stop_units"] * unit[i0 - 1]
    dist = abs(p - stop)
    if not dist or dist != dist:
        return np.nan, "NO_STOP", i0
    t = live.plan_targets(int(side), float(p), float(stop), trow(k))
    t1, t2 = t.get("target_1"), t.get("target_2")
    qty, pnl, t1_hit = 1.0, 0.0, False
    for j in range(i0, e + 1):
        if open_exit and j == e:
            price = o[j]
            pnl += qty * side * (price - p) - fee * qty * (p + price)
            return pnl / dist, "OPEN", j
        if (side == 1 and l[j] <= stop) or (side == -1 and h[j] >= stop):
            price = min(o[j], stop) if side == 1 else max(o[j], stop)
            pnl += qty * side * (price - p) - fee * qty * (p + price)
            return pnl / dist, ("STOP_BE" if t1_hit else "STOP"), j
        if t1 is not None:
            reach = (lambda x: h[j] >= x) if side == 1 else (lambda x: l[j] <= x)
            if not t1_hit and reach(t1):
                q = qty * shadows.PART
                pnl += q * side * (t1 - p) - fee * q * (p + t1)
                qty -= q
                t1_hit = True
                stop = p
            if t1_hit and t2 is not None and reach(t2):
                pnl += qty * side * (t2 - p) - fee * qty * (p + t2)
                return pnl / dist, "T2", j
        if j == e:
            price = c[j]
            pnl += qty * side * (price - p) - fee * qty * (p + price)
            return pnl / dist, "TIME", j
    return np.nan, "NONE", e


def real_slots(trades):
    """The real trades as replay slots: side, entry bar, entry price, last bar, open exit."""
    tr = trades
    return {"side": tr.side.values.astype(int), "i_in": tr.i_in.values.astype(int), "i_out": tr.i_out.values.astype(int),
            "p_in": tr.p_in.values.astype(float), "r": tr.r_mult.values.astype(float),
            "open_exit": np.array([open_exit_of(w) for w in tr.why_out.values], dtype=bool),
            "last": np.array([str(w).split("+")[-1] for w in tr.why_out.values])}


CAP_DAYS = 30                       # H81/H82: a placebo trade (and its real twin) ends at the latest 30 days after entry


def cap_bar(tms, i0, n):
    """The last bar a machinery trade entered at bar i0 may run to: the last bar opening before entry + CAP_DAYS."""
    return int(min(max(np.searchsorted(tms, int(tms[i0]) + CAP_DAYS * DAY_MS, side="left") - 1, i0), n - 1))


def machine_r(ctx, side, i0, p):
    """R of one trade under the exits machinery ALONE: its own stop, Target 1 (half off, stop to the entry), Target 2,
    else at the close of the cap bar. Nothing about how the real trade ended is used (that would leak: a real stop-out
    is a move in the other side's favour)."""
    return replay_trade(side, i0, p, i0 - 1, cap_bar(ctx["tms"], i0, ctx["n"]), False, ctx["inp"]["px"],
                        ctx["inp"]["unit"], ctx["cfg"], ctx["trow"])[0]


def replay_gate(ctx, trades, tol=1e-9):
    """Every real trade replayed with its own side, bar and window must give its R and its kind of exit."""
    s = real_slots(trades)
    px, unit = ctx["inp"]["px"], ctx["inp"]["unit"]
    bad = 0
    for j in range(len(s["side"])):
        r, word, jo = replay_trade(s["side"][j], s["i_in"][j], s["p_in"][j], s["i_in"][j] - 1, s["i_out"][j],
                                   s["open_exit"][j], px, unit, ctx["cfg"], ctx["trow"])
        want = "OPEN" if s["open_exit"][j] else s["last"][j]
        ok_r = (abs(r - s["r"][j]) <= tol * max(1.0, abs(s["r"][j]))) if np.isfinite(s["r"][j]) else not np.isfinite(r)
        if not (ok_r and word == want and jo == s["i_out"][j]):
            bad += 1
            if bad <= 3:
                log("  replay gate: %s trade %d: R %.9f vs %.9f, %s vs %s, bar %d vs %d" % (
                    ctx["a"], j, r, s["r"][j], word, want, jo, s["i_out"][j]))
    return bad == 0, bad


# =====================================================================================
# one placebo draw per kind
# =====================================================================================
def book_draw(study, ctxs, k, gi):
    """Draw k of a book-level study on one market group -> {market: stats (+ extras)}."""
    seed = STUDIES[study]["seed"]
    u = draw_rng(seed, k).random()                               # common to all markets: dependence across markets kept
    out = {}
    gperm = None
    for a, ctx in ctxs.items():
        lo, n, inp = ctx["lo"], ctx["n"], ctx["inp"]
        mi = MARKETS.index(a)
        extra = {}
        if study == "H80":
            src = shift_src(ctx["tms"], lo, n, u, 30)
            b = run_book(ctx, RULE_CURRENT, odds=apply_src(inp["odds"], src, lo, n))
        elif study == "H85":
            src = shift_src(ctx["tms"], lo, n, u, 30)
            bias = None if inp["bias"] is None else apply_src(np.asarray(inp["bias"], dtype=float), src, lo, n)
            b = run_book(ctx, RULE_CURRENT, tide=apply_src(np.asarray(inp["tide"], dtype=float), src, lo, n), bias=bias)
        elif study == "H86":
            if gperm is None:                                    # one permutation per group: rows are aligned in a group
                g_lo = min(c["lo"] for c in ctxs.values())
                gperm = (g_lo, month_shuffle_src(ctx["month"], g_lo - 1, n, draw_rng(seed, k, 100 + gi)))
            g_lo, src = gperm
            b = run_book(ctx, RULE_CURRENT, unit=apply_src(np.asarray(inp["unit"], dtype=float), src, g_lo - 1, n))
        elif study == "H83":
            src = shift_src(ctx["tms"], lo, n, u, 60)
            mv = apply_src(ctx["move30"], src, lo, n)
            b = run_book(ctx, RULE_TREND, aux=dict(ctx["aux"], trend_move=mv))
        elif study == "H84":
            p = ctx["p_trigger"]
            rng = draw_rng(seed, k, mi)
            b = copy_book(ctx, RULE_WAIT, trigger=lambda word, rng=rng, p=p: bool(rng.random() < p))
            extra = {"episodes": int(b["wait"]["episodes"]), "blocked": int(b["wait"]["blocked"])}
        else:
            raise ValueError(study)
        out[a] = {"s": book_stats(b, ctx), **extra}
        del b
    return out


def trade_draw(study, ctxs, k, gi):
    """H82 draw k on one group: each real trade moved to a random bar of its own month and market, same side, under the
    exits machinery alone (machine_r), as its real twin is in the real statistic."""
    seed = STUDIES[study]["seed"]
    out = {}
    for a, ctx in ctxs.items():
        rng = draw_rng(seed, k, MARKETS.index(a))
        s, px, unit = ctx["slots"], ctx["inp"]["px"], ctx["inp"]["unit"]
        early = ctx["cfg"].get("early_fill") is True and not int(ctx["cfg"].get("fill_delay_bars", 0) or 0)
        n = ctx["n"]
        r_out = np.full(len(s["side"]), np.nan)
        i_out = np.zeros(len(s["side"]), dtype="int64")
        for j in range(len(s["side"])):
            bars = ctx["valid_by_month"][ctx["month"][s["i_in"][j]]]
            i0 = int(bars[int(rng.integers(len(bars)))])
            p = px["close"][i0 - 1] if early else px["open"][i0]
            r_out[j] = machine_r(ctx, int(s["side"][j]), i0, float(p))
            i_out[j] = i0
        out[a] = {"s": stats_from(i_out, r_out, r_out > 0, None, ctx["lo"], ctx["mid"], n)}
    return out


# =====================================================================================
# H81b / H82b: the CAUSAL side and entry-time placebos (registered after the H81 audit; H81 void, H82 withdrawn).
# Every placebo trade uses only what the book knew at that trade's own entry: a side drawn from the book's PREVIOUS
# trades (H81b) or the real side moved to a bar AT OR AFTER the real entry, inside a window whose length is set by the
# book's PREVIOUS entries (H82b). Trades are scored by machine_r exactly as in H81/H82. The pure functions below are
# also what the random-walk check (rw_check) and tests/test_queue_placebo.py exercise.
# =====================================================================================
TRAIL_N = 20                        # H81b / H82b: the book's previous 20 trades on the market (fewer at the start)


def trailing_long_share(sides, n_prev=TRAIL_N):
    """p[j] = the long share of the book's previous n_prev trades on the market (all earlier ones while fewer exist;
    0.5 for the first). Uses sides[:j] only: the trade's own side and every later side are never read."""
    s = (np.asarray(sides) == 1).astype(float)
    c = np.concatenate([[0.0], np.cumsum(s)])
    j = np.arange(len(s))
    a = np.maximum(j - int(n_prev), 0)
    cnt = j - a
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(cnt > 0, (c[j] - c[a]) / np.where(cnt > 0, cnt, 1), 0.5)
    return p


def trailing_gap(pos, n_prev=TRAIL_N):
    """L[j] = the median of the book's previous n_prev entry gaps on the market, in drawable bars (the gap from trade
    j-1 to trade j is known at trade j's entry, so it counts; no later entry is read), truncated to an integer, at
    least 1. L[0] = 1 (no gap known yet: the first trade stays at its real bar)."""
    pos = np.asarray(pos, dtype="int64")
    g = np.diff(pos)
    out = np.ones(len(pos), dtype="int64")
    for j in range(1, len(pos)):
        out[j] = max(1, int(np.median(g[max(0, j - int(n_prev)):j])))
    return out


def h81b_sides(p, u):
    """Placebo sides from uniforms u: long where u < p. With p = trailing_long_share it is the H81b draw; with
    p = 0.5 it is the coin cell."""
    return np.where(np.asarray(u) < np.asarray(p), 1, -1)


def h82b_offsets(L, u):
    """Offsets in [0, L) (uniform integers) from uniforms u in [0, 1): offset 0 is the real entry bar."""
    L = np.asarray(L, dtype="int64")
    return np.minimum((np.asarray(u) * L).astype("int64"), L - 1)


# ------------------------------------------------------------------ the random-walk check (no market data)
def rw_walk(seed, years=2, per_day=24, vol_day=0.03):
    """A driftless random walk (a martingale in log price) of hourly bars, with every trade outcome precomputed: R of a
    long and of a short entered at bar i (price close[i-1], decision row i-1), scored by replay_trade exactly as
    machine_r scores the book (stop 2 units, no readings: Target 1 1.5R, Target 2 2R, 30-day cap)."""
    rng = np.random.default_rng([2026, 8182, int(seed)])
    nbar = int(years * 365 * per_day)
    ret = rng.standard_normal(nbar) * vol_day / math.sqrt(per_day)
    close = 30000.0 * np.exp(np.cumsum(ret))
    op = np.r_[close[0], close[:-1]]
    wig = vol_day / math.sqrt(per_day) / 3.0
    hi = np.maximum(op, close) * np.exp(np.abs(rng.standard_normal(nbar)) * wig)
    lo_ = np.minimum(op, close) * np.exp(-np.abs(rng.standard_normal(nbar)) * wig)
    px = {"open": op, "high": hi, "low": lo_, "close": close}
    unit = close * 0.012
    tms = np.arange(nbar, dtype="int64") * (DAY_MS // per_day)
    cfg = {"cost_side": 0.001, "stop_units": 2.0}
    empty = (lambda k: {})
    R = {1: np.full(nbar, np.nan), -1: np.full(nbar, np.nan)}
    E = {1: np.zeros(nbar, dtype="int64"), -1: np.zeros(nbar, dtype="int64")}
    for i in range(1, nbar):
        e = cap_bar(tms, i, nbar)
        for sd in (1, -1):
            r, _w, jo = replay_trade(sd, i, close[i - 1], i - 1, e, False, px, unit, cfg, empty)
            R[sd][i], E[sd][i] = r, jo
    return {"close": close, "R": R, "E": E, "nbar": nbar, "per_day": per_day, "tms": tms, "rng_seed": int(seed)}


def rw_book(w, rule, seed, lookback_days=3):
    """A one-position toy book on the walk: side by a CAUSAL rule at the close before entry (momentum: the sign of the
    last lookback_days' move; reversal: its opposite; coin), out by the machinery, the next entry 0-23 bars after the
    exit (so, like the real book, when it enters next depends on how the trade ended). -> entry bars, sides."""
    rng = np.random.default_rng([2026, 8183, int(seed), ["momentum", "reversal", "coin"].index(rule)])
    lb = int(lookback_days * w["per_day"])
    c, nbar = w["close"], w["nbar"]
    i, ins, sides = lb + 1, [], []
    while i < nbar - 1:
        if rule == "coin":
            sd = 1 if rng.random() < 0.5 else -1
        else:
            sd = (1 if c[i - 1] > c[i - 1 - lb] else -1) * (1 if rule == "momentum" else -1)
        ins.append(i)
        sides.append(sd)
        i = int(w["E"][sd][i]) + 1 + int(rng.integers(0, 24))
    return np.array(ins, dtype="int64"), np.array(sides, dtype="int64")


def rw_placebos(w, ins, sides, draws, seed):
    """Per placebo design, the mean R a trade of each draw on one toy book. The causal designs (H81b trailing share,
    H81b coin, H82b trailing-gap window) and, for comparison, the designs found to look ahead (H81 within-month
    permutation, H82 random bar of the month, and the brief's H82b window that runs to the NEXT real entry)."""
    R = w["R"]
    nbar = w["nbar"]
    rp, rm = R[1][ins], R[-1][ins]
    month = (w["tms"] // (30 * DAY_MS)).astype("int64")[ins]
    p_tr = trailing_long_share(sides)
    pos = ins                                                    # every bar is drawable on the walk
    L = trailing_gap(pos)
    nxt = np.r_[ins[1:], nbar - 1]
    Lnext = np.maximum(nxt - ins, 1)                             # the brief's window: up to the next real entry (future)
    month_all = (w["tms"] // (30 * DAY_MS)).astype("int64")
    mstart = np.maximum(np.searchsorted(month_all, month, side="left"), 1)
    mend = np.searchsorted(month_all, month, side="right")
    res = dict((k, np.empty(draws)) for k in ("h81_month_perm", "h81b_trailing", "h81b_coin", "h82_month_bar",
                                               "h82b_window_to_next_entry", "h82b_trailing_gap"))
    T = len(ins)

    def rs(sd, i0):
        return np.where(sd == 1, R[1][i0], R[-1][i0])
    for k in range(draws):
        g = draw_rng(seed, k)
        u = g.random((5, T))
        res["h81_month_perm"][k] = np.nanmean(np.where(sides[permute_within(month, g)] == 1, rp, rm))
        res["h81b_trailing"][k] = np.nanmean(np.where(h81b_sides(p_tr, u[0]) == 1, rp, rm))
        res["h81b_coin"][k] = np.nanmean(np.where(h81b_sides(0.5, u[1]) == 1, rp, rm))
        i0 = mstart + (u[2] * (mend - mstart)).astype("int64")
        res["h82_month_bar"][k] = np.nanmean(rs(sides, np.minimum(i0, nbar - 1)))
        res["h82b_window_to_next_entry"][k] = np.nanmean(rs(sides, np.minimum(ins + h82b_offsets(Lnext, u[3]), nbar - 1)))
        res["h82b_trailing_gap"][k] = np.nanmean(rs(sides, np.minimum(ins + h82b_offsets(L, u[4]), nbar - 1)))
    real = float(np.nanmean(np.where(sides == 1, rp, rm)))
    return real, res


def rw_check(walks=12, draws=200, years=2, rules=("momentum", "reversal", "coin"), log=None):
    """The random-walk check of H81b and H82b. On driftless walks no causal side rule and no entry timing can earn
    anything, so a sound placebo must show no difference from the real toy book on average (any rule), and must not
    reproduce the old designs' tilt (placebo better than a momentum rule, worse than a reversal rule).
    -> {rule: {design: {mean gap placebo - real, its SE over walks, share of walks with p_upper <= 0.05 / >= 0.95}}}"""
    gaps, pu = {}, {}
    for s in range(walks):
        w = rw_walk(s, years=years)
        for rule in rules:
            ins, sides = rw_book(w, rule, s)
            real, res = rw_placebos(w, ins, sides, draws, 818200 + s)
            for d, v in res.items():
                gaps.setdefault(rule, {}).setdefault(d, []).append(float(np.nanmean(v)) - real)
                pu.setdefault(rule, {}).setdefault(d, []).append((1 + int(np.sum(v >= real - 1e-12))) / (1 + len(v)))
        if log:
            log("rw walk %d of %d done" % (s + 1, walks))
    out = {}
    for rule in gaps:
        out[rule] = {}
        for d in gaps[rule]:
            g, p = np.array(gaps[rule][d]), np.array(pu[rule][d])
            out[rule][d] = {"walks": int(len(g)), "gap_mean": float(g.mean()),
                            "gap_se": float(g.std(ddof=1) / math.sqrt(len(g))) if len(g) > 1 else float("nan"),
                            "share_p_upper_le_0.05": float(np.mean(p <= 0.05)),
                            "share_p_upper_ge_0.95": float(np.mean(p >= 0.95))}
    return out


# =====================================================================================
# checkpoints and progress
# =====================================================================================
def fingerprint(study, draws, cut):
    src = open(os.path.abspath(__file__), "rb").read()
    return hashlib.sha256(("%s|%d|%d|%s|" % (study, draws, STUDIES[study]["seed"], cut)).encode() + src).hexdigest()[:16]


def iter_lines(path):
    """Finished records of a jsonl checkpoint, one at a time (a long study never holds them all as Python objects);
    a torn last line (a kill mid-write) is dropped and cut off the file."""
    if not os.path.exists(path):
        return
    keep, torn = 0, False
    with open(path, "rb") as fh:
        for line in fh:
            if not line.endswith(b"\n"):
                torn = True
                break
            if line.strip():
                try:
                    rec = json.loads(line.decode("utf-8"))
                except ValueError:
                    torn = True
                    break
                yield rec
            keep += len(line)
    if torn:
        with open(path, "r+b") as fh:
            fh.truncate(keep)


def read_lines(path):
    return list(iter_lines(path))


def append_line(path, rec):
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, default=_jsonable)
    os.replace(tmp, path)


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.bool_,)):
        return bool(x)
    raise TypeError(type(x))


class Progress:
    def __init__(self, out, total, cost_of):
        self.out, self.total, self.cost_of = out, total, cost_of
        p = os.path.join(out, "progress.json")
        old = json.load(open(p)) if os.path.exists(p) else {}
        self.started = old.get("started_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.t0, self.cost_done_here, self.done = time.time(), 0.0, 0
        self.cost_left = None

    def update(self, done, cost_left, cost_step=0.0, note=""):
        self.done = done
        self.cost_done_here += cost_step
        el = time.time() - self.t0
        rate = (el / self.cost_done_here) if self.cost_done_here > 0 and el > 60 else 1.0   # measured vs table
        write_json(os.path.join(self.out, "progress.json"), {
            "done": int(done), "total": int(self.total), "started_utc": self.started,
            "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "est_hours_left": round(cost_left * rate / 3600.0, 3), "note": note})


# =====================================================================================
# the studies
# =====================================================================================
def real_books_for(study, ctxs, gate_log, prep=None):
    """The real book(s) of one group, with the gates. -> {market: {"current": stats, "real": stats, ...}}
    With prep given, the real book run here must be the engine's own challenger (b_targets, or b_trend30 for H83)."""
    real = {}
    for a, ctx in ctxs.items():
        cur = run_book(ctx, RULE_CURRENT)
        gate_log.setdefault(a, {})
        if prep is not None:
            okc, whyc = same_book(shadows.run_challenger("b_targets", prep, a, ctx["lo"], ctx["n"], aux=ctx["aux"]), cur,
                                  ctx["lo"], ctx["n"])
            gate_log[a]["run_is_engine_b_targets"] = okc
            if not okc:
                raise RuntimeError("%s: the real book is not the engine's b_targets: %s" % (a, whyc))
        rec = {"current": book_stats(cur, ctx)}
        if study in ("H81", "H82", "H81b", "H82b"):
            ok, bad = replay_gate(ctx, cur["trades"])
            gate_log[a].update(replay_gate=ok, trades=int(len(cur["trades"])), mismatches=int(bad))
            if not ok:
                raise RuntimeError("replay gate failed on %s: %d trades differ" % (a, bad))
            ctx["slots"] = sl = real_slots(cur["trades"])
            sl["r_mach"] = np.array([machine_r(ctx, int(sl["side"][j]), int(sl["i_in"][j]), float(sl["p_in"][j]))
                                     for j in range(len(sl["side"]))])
            rec["real"] = stats_from(sl["i_in"], sl["r_mach"], sl["r_mach"] > 0, None, ctx["lo"], ctx["mid"], ctx["n"])
        elif study == "H83":
            ctx["move30"] = shadows.trend_move(ctx["tms"], ctx["inp"]["px"]["close"], 30, ctx["lo"], ctx["n"])
            tb = run_book(ctx, RULE_TREND, aux=dict(ctx["aux"], trend_move=ctx["move30"]))
            if prep is not None:
                okt, whyt = same_book(shadows.run_challenger("b_trend30", prep, a, ctx["lo"], ctx["n"], aux=ctx["aux"]), tb,
                                      ctx["lo"], ctx["n"])
                gate_log[a]["run_is_engine_b_trend30"] = okt
                if not okt:
                    raise RuntimeError("%s: the filter book is not the engine's b_trend30: %s" % (a, whyt))
            rec["real"] = book_stats(tb, ctx)
            del tb
        elif study == "H84":
            ok1, why1 = same_book(cur, copy_book(ctx, RULE_CURRENT), ctx["lo"], ctx["n"])
            wb = run_book(ctx, RULE_WAIT)
            mine = copy_book(ctx, RULE_WAIT)
            ok2, why2 = same_book(wb, mine, ctx["lo"], ctx["n"])
            ok3 = mine["wait"] == dict(wb["state"]["wait_stop"])
            gate_log[a].update(copy_is_b_targets=ok1, copy_is_b_wait_stop=bool(ok2 and ok3), detail=[why1, why2],
                               trades=int(len(wb["trades"])))
            if not (ok1 and ok2 and ok3):
                raise RuntimeError("loop-copy gate failed on %s: %s / %s / wait %s" % (a, why1, why2, ok3))
            last = np.array([str(w).split("+")[-1] for w in wb["trades"].why_out.values])
            flat_exits = last != "FLIP"
            ctx["p_trigger"] = float((last == "STOP").sum() / max(1, flat_exits.sum()))
            rec["real"] = book_stats(wb, ctx)
            rec["p_trigger"] = ctx["p_trigger"]
            rec["episodes"], rec["blocked"] = int(mine["wait"]["episodes"]), int(mine["wait"]["blocked"])
            del wb, mine
        else:
            rec["real"] = rec["current"]
        real[a] = rec
        del cur
    return real


BATCH = 200                                                      # draws per checkpoint line (and at least one a minute)


def compact(res):
    """Floats rounded to 1e-9 (R sums), so checkpoint lines stay short."""
    return dict((a, dict((k, [round(x, 9) if isinstance(x, float) else x for x in v] if k == "s" else v)
                         for k, v in rec.items())) for a, rec in res.items())


def done_keys(rec):
    return rec.get("ks") or []


def run_draw_study(study, args, out, groups, cut, draws, smoke=False):
    kind = STUDIES[study]["kind"]
    fp = fingerprint(study, draws, cut)
    costs = DRAW_S[study]
    total = draws * len(groups)

    def done_by_group():
        return dict((g, set(k for r in iter_lines(os.path.join(out, "draws_%s.jsonl" % g)) if r.get("fp") == fp
                             for k in done_keys(r))) for g, _a in groups)
    done = done_by_group()

    def cost_left():
        return sum((draws - len(done[g])) * costs[g] + (PREP_S[g] if len(done[g]) < draws else 0) for g, _a in groups)
    prog = Progress(out, total, cost_left)
    prog.update(sum(len(v) for v in done.values()), cost_left(), note="starting")
    gates = {}
    for gi, (g, assets) in enumerate(groups):
        real_path = os.path.join(out, "real_%s.json" % g)
        if len(done[g]) >= draws and os.path.exists(real_path):
            continue
        prep = load_group(g, assets, args.fits_dir, out, cut)
        ctxs = dict((a, market_ctx(prep, a)) for a in assets)
        gl = {}
        real = real_books_for(study, ctxs, gl, prep)
        if kind == "trade":
            for a, ctx in ctxs.items():
                unit = ctx["inp"]["unit"]
                valid = {}
                rows = np.arange(ctx["lo"] + 1, ctx["n"] - 1)
                rows = rows[np.isfinite(unit[rows - 1]) & (unit[rows - 1] > 0)]
                for m in np.unique(ctx["month"][rows]):
                    valid[int(m)] = rows[ctx["month"][rows] == m]
                for i in ctx["slots"]["i_in"]:                    # every real entry month has bars to draw from
                    if int(ctx["month"][i]) not in valid:
                        valid[int(ctx["month"][i])] = np.array([i])
                ctx["valid_by_month"] = valid
        rec = {"fp": fp, "group": g, "end": str(prep["times"][-1])[:16], "load_s": prep["_load_s"], "real": real,
               "gate": gl, "windows": dict((a, [str(prep["times"][c["lo"]])[:16], str(prep["times"][c["n"] - 1])[:16]])
                                           for a, c in ctxs.items())}
        if os.path.exists(real_path):                            # a resume must see the very same real book
            old = json.load(open(real_path))
            if old.get("fp") == fp and json.dumps(old["real"], sort_keys=True, default=_jsonable) != \
                    json.dumps(json.loads(json.dumps(real, default=_jsonable)), sort_keys=True):
                raise RuntimeError("%s: the real book differs from the one saved before the resume" % g)
        write_json(real_path, rec)
        gates[g] = gl
        log("%s: loaded to %s in %.0fs; %d of %d draws done before" % (g, rec["end"], prep["_load_s"], len(done[g]), draws))
        last_log, buf, t_buf = time.time(), [], time.time()

        def flush():
            if buf:                                              # one line per batch: all its draws or none
                append_line(os.path.join(out, "draws_%s.jsonl" % g), {"fp": fp, "ks": [b[0] for b in buf],
                                                                      "m": [b[1] for b in buf]})
                for b in buf:
                    done[g].add(b[0])
                prog.update(sum(len(v) for v in done.values()), cost_left(), costs[g] * len(buf),
                            note="%s draw %d" % (g, buf[-1][0]))
                del buf[:]
        for k in range(draws):
            if k in done[g]:
                continue
            res = book_draw(study, ctxs, k, gi) if kind == "book" else trade_draw(study, ctxs, k, gi)
            buf.append((k, compact(res)))
            if len(buf) >= BATCH or time.time() - t_buf > 60:    # at least once a minute (contract: every 10 minutes)
                flush()
                t_buf = time.time()
            if smoke or time.time() - last_log > 600:
                log("%s: draw %d done; %d of %d" % (g, k, len(done[g]) + len(buf), draws))
                last_log = time.time()
        flush()
        del prep, ctxs
        gc.collect()
    return fp


def collect(out, groups, fp, draws):
    """-> real {market: rec}, D (draws x markets x NSTAT) array, extras."""
    reals, D, ex = {}, np.full((draws, len(MARKETS), NSTAT), np.nan), {}
    meta = {}
    for g, assets in groups:
        rr = json.load(open(os.path.join(out, "real_%s.json" % g)))
        reals.update(rr["real"])
        meta[g] = {"end": rr["end"], "gate": rr["gate"], "windows": rr["windows"]}
        for r in iter_lines(os.path.join(out, "draws_%s.jsonl" % g)):
            if r.get("fp") != fp:
                continue
            for k, m in zip(done_keys(r), r["m"]):
                if k >= draws:
                    continue
                for a, v in m.items():
                    D[k, MARKETS.index(a)] = v["s"]
                    for key in ("episodes", "blocked"):
                        if key in v:
                            ex.setdefault(key, np.full((draws, len(MARKETS)), np.nan))[k, MARKETS.index(a)] = v[key]
    return reals, D, ex, meta


SLICES = (("pooled", MARKETS), ("vault", list(VAULT)), ("others", [a for a in MARKETS if a not in VAULT]))
PARTS = (("all", 0), ("h1", 5), ("h2", 10))


def agg(S, mk_idx, off):
    """S: (..., markets, NSTAT) -> (trades, sum_r, mean_r, flat share) over the chosen markets and part."""
    tr = np.nansum(S[..., mk_idx, off + 0], axis=-1)
    sr = np.nansum(S[..., mk_idx, off + 1], axis=-1)
    fl = np.nansum(S[..., mk_idx, off + 3], axis=-1)
    bars = np.nansum(S[..., mk_idx, off + 4], axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return tr, sr, np.where(tr > 0, sr / np.where(tr > 0, tr, 1), np.nan), np.where(bars > 0, fl / np.where(bars > 0, bars, 1), np.nan)


def pvals(real, dist):
    d = np.asarray(dist, dtype=float)
    n = len(d)
    ge = int(np.sum(d >= real - 1e-12))                         # NaN (no trades) never counts as at least as good
    le = int(np.sum(d <= real + 1e-12))
    return {"p_upper": (1 + ge) / (1 + n), "p_lower": (1 + le) / (1 + n), "n": n,
            "q05": float(np.nanpercentile(d, 5)) if n else None, "q50": float(np.nanpercentile(d, 50)) if n else None,
            "q95": float(np.nanpercentile(d, 95)) if n else None}


def summarise_draws(study, reals, D, ex, which="real"):
    have = np.all(np.isfinite(D[:, :, 0]) | np.array([[a not in reals for a in MARKETS]]), axis=1)
    D = D[have]
    R = np.full((len(MARKETS), NSTAT), np.nan)
    for a, rec in reals.items():
        R[MARKETS.index(a)] = rec[which]
    C = np.full((len(MARKETS), NSTAT), np.nan)
    for a, rec in reals.items():
        C[MARKETS.index(a)] = rec["current"]
    out = {"draws_used": int(len(D)), "cells": {}}
    for sname, mk in SLICES:
        idx = [MARKETS.index(a) for a in mk if a in reals]
        for pname, off in PARTS:
            rt, rs, rm, rf = agg(R, idx, off)
            ct, cs, cm, cf = agg(C, idx, off)
            dt, ds, dm, dfl = agg(D, idx, off)
            out["cells"]["%s_%s" % (sname, pname)] = {
                "real": {"trades": int(rt), "sum_r": float(rs), "mean_r": float(rm), "flat": float(rf)},
                "current_rule": {"trades": int(ct), "sum_r": float(cs), "mean_r": float(cm), "flat": float(cf)},
                "placebo_trades_median": float(np.nanmedian(dt)) if len(dt) else None,
                "placebo_flat_median": float(np.nanmedian(dfl)) if len(dfl) else None,
                "mean_r": pvals(rm, dm), "sum_r": pvals(rs, ds)}
    for key, arr in ex.items():
        arr = arr[have]
        out[key + "_median"] = dict((a, float(np.nanmedian(arr[:, MARKETS.index(a)]))) for a in reals)
    out["per_market"] = {}
    for a in reals:
        i = MARKETS.index(a)
        rt, rs, rm, rf = agg(R, [i], 0)
        dt, ds, dm, dfl = agg(D, [i], 0)
        out["per_market"][a] = {"real_trades": int(rt), "real_mean_r": float(rm), "real_sum_r": float(rs),
                                "mean_r": pvals(rm, dm)}
    return out


# ------------------------------------------------------------------ H81: precomputed both-side outcomes
def run_side_study(args, out, groups, cut, draws, smoke=False):
    study = "H81"
    fp = fingerprint(study, draws, cut)
    total = len(groups) + draws
    prog = Progress(out, total, None)
    gl_all = {}
    for g, assets in groups:
        path = os.path.join(out, "sides_%s.json" % g)
        if os.path.exists(path) and json.load(open(path)).get("fp") == fp:
            continue
        prep = load_group(g, assets, args.fits_dir, out, cut)
        ctxs = dict((a, market_ctx(prep, a)) for a in assets)
        gl = {}
        real = real_books_for(study, ctxs, gl, prep)
        rec = {"fp": fp, "group": g, "end": str(prep["times"][-1])[:16], "gate": gl, "real": real, "markets": {}}
        for a, ctx in ctxs.items():
            s, px, unit = ctx["slots"], ctx["inp"]["px"], ctx["inp"]["unit"]
            both = []
            for j in range(len(s["side"])):
                rj = {}
                for side in (1, -1):
                    rj[side] = machine_r(ctx, side, int(s["i_in"][j]), float(s["p_in"][j]))
                both.append((rj[1], rj[-1]))
            rec["markets"][a] = {"side": s["side"].tolist(), "r_plus": [x[0] for x in both], "r_minus": [x[1] for x in both],
                                 "month": [int(ctx["month"][i]) for i in s["i_in"]],
                                 "h2": [bool(i >= ctx["mid"]) for i in s["i_in"]], "real_r": s["r"].tolist()}
        write_json(path, rec)
        gl_all[g] = gl
        prog.update(0, 60.0, note="%s outcomes" % g)
        del prep, ctxs
        gc.collect()
    # the draws: vectorised, checkpointed in blocks
    side, rp, rm_, grp, h2, mk = [], [], [], [], [], []
    for g, assets in groups:
        rec = json.load(open(os.path.join(out, "sides_%s.json" % g)))
        for a in assets:
            m = rec["markets"][a]
            side += m["side"]
            rp += m["r_plus"]
            rm_ += m["r_minus"]
            grp += [MARKETS.index(a) * 100000 + x for x in m["month"]]
            h2 += m["h2"]
            mk += [MARKETS.index(a)] * len(m["side"])
    side, rp, rm_, grp, h2, mk = (np.asarray(x) for x in (side, rp, rm_, grp, h2, mk))
    real_r = np.where(side == 1, rp, rm_)
    blk_path = os.path.join(out, "draws_H81.npz")
    have = {}
    if os.path.exists(blk_path):
        z = np.load(blk_path)
        if str(z["fp"]) == fp:
            have = {"S": z["S"], "done": int(z["done"])}
    S = have.get("S", np.full((draws, len(MARKETS), NSTAT), np.nan))
    k0 = have.get("done", 0)
    seed = STUDIES[study]["seed"]
    last = time.time()
    for k in range(k0, draws):
        src = permute_within(grp, draw_rng(seed, k))
        r = np.where(side[src] == 1, rp, rm_)
        for mi in np.unique(mk):
            sel = mk == mi
            rr, hh = r[sel], h2[sel]
            ok = np.isfinite(rr)
            for off, part in ((0, ok), (5, ok & ~hh), (10, ok & hh)):
                S[k, mi, off:off + 5] = [part.sum(), rr[part].sum(), (rr[part] > 0).sum(), 0, 0]
        if time.time() - last > 300 or k == draws - 1:
            np.savez(blk_path + ".tmp.npz", S=S, done=k + 1, fp=fp)
            os.replace(blk_path + ".tmp.npz", blk_path)
            prog.update(len(groups) + k + 1, (draws - k - 1) * 0.002, note="draw %d" % k)
            last = time.time()
    # the real record in the same form (from the replay, which the gate tied to the book)
    reals = {}
    for g, assets in groups:
        rec = json.load(open(os.path.join(out, "sides_%s.json" % g)))
        for a in assets:
            mi = MARKETS.index(a)
            sel = mk == mi
            rr, hh = real_r[sel], h2[sel]
            ok = np.isfinite(rr)
            st = []
            for part in (ok, ok & ~hh, ok & hh):
                st += [int(part.sum()), float(rr[part].sum()), int((rr[part] > 0).sum()), 0, 0]
            reals[a] = {"real": st, "current": rec["real"][a]["current"]}
            gl_all.setdefault(g, rec["gate"])
    return reals, S, gl_all


# ------------------------------------------------------------------ H81b / H82b: causal placebos, outcomes precomputed
CAUSAL_BLOCK = 5000                 # draws per checkpoint file (each block takes seconds: well inside a minute)

# Seconds of ONE processor on the research server (22 Nov 2026, `--time-draws 200` on the full window to CUT; seconds and
# memory only were printed): per group, the outcome precompute after the load (H81b: both sides of every real trade;
# H82b: every bar of every trade's window), and one vectorised draw over all eight markets.
CAUSAL_PRE_S = {"H81b": {"crypto": 0.3, "metals": 0.2, "fx": 0.1, "index": 0.05, "energy": 0.2},
                "H82b": {"crypto": 23.8, "metals": 14.5, "fx": 6.7, "index": 1.5, "energy": 11.2}}
CAUSAL_DRAW_S = {"H81b": 0.0005, "H82b": 0.0003}  # measured: 0.0005 s and 0.0003 s a draw over the 5,162 trades


def causal_outcomes(study, ctx):
    """One market's precomputed outcomes for H81b / H82b (after real_books_for: ctx["slots"] with r_mach).
    H81b: R of each real trade with either side at its real entry (machine_r), and the trailing long share.
    H82b: for each real trade j, R of its own side entered at each of the L_j drawable bars starting AT its real entry
    bar (offset 0 = the real entry), L_j = trailing_gap of the drawable positions; entry price by the real trade's own
    convention (the close of the bar before for an early entry, else the bar's open).
    Checks that no placebo uses a later side or an earlier bar; raises if one would."""
    s = ctx["slots"]
    i_in, i_out, side = s["i_in"], s["i_out"], s["side"]
    if len(i_in) > 1 and not (np.all(np.diff(i_in) > 0) and np.all(i_out[:-1] <= i_in[1:])):
        raise RuntimeError("%s: the book's trades are not one after another" % ctx["a"])
    rec = {"side": side.tolist(), "h2": [bool(i >= ctx["mid"]) for i in i_in], "real_r": s["r"].tolist(),
           "r_mach": s["r_mach"].tolist()}
    px, unit, n = ctx["inp"]["px"], ctx["inp"]["unit"], ctx["n"]
    if study == "H81b":
        rp = np.array([machine_r(ctx, 1, int(i_in[j]), float(s["p_in"][j])) for j in range(len(side))])
        rm = np.array([machine_r(ctx, -1, int(i_in[j]), float(s["p_in"][j])) for j in range(len(side))])
        own = np.where(side == 1, rp, rm)
        if not np.allclose(own, s["r_mach"], rtol=0, atol=1e-12, equal_nan=True):
            raise RuntimeError("%s: both-side outcomes disagree with the real machinery R" % ctx["a"])
        rec.update(r_plus=rp.tolist(), r_minus=rm.tolist(), p_long=trailing_long_share(side).tolist())
        return rec
    rows = np.arange(ctx["lo"] + 1, n)
    rows = rows[np.isfinite(unit[rows - 1]) & (unit[rows - 1] > 0)]
    valid = np.union1d(rows, i_in).astype("int64")              # every real entry bar is drawable (offset 0)
    pos = np.searchsorted(valid, i_in)
    if not np.array_equal(valid[pos], i_in):
        raise RuntimeError("%s: a real entry bar is not drawable" % ctx["a"])
    L = np.minimum(trailing_gap(pos), len(valid) - pos)
    early = ctx["cfg"].get("early_fill") is True and not int(ctx["cfg"].get("fill_delay_bars", 0) or 0)
    tab, early_j = [], []
    for j in range(len(side)):
        ej = bool(early and s["p_in"][j] == px["close"][i_in[j] - 1])
        early_j.append(ej)
        bars = valid[pos[j]:pos[j] + L[j]]
        if bars[0] != i_in[j] or np.any(bars < i_in[j]):
            raise RuntimeError("%s: a placebo bar before the real entry" % ctx["a"])
        for i0 in bars:
            p = px["close"][i0 - 1] if ej else px["open"][i0]
            tab.append(machine_r(ctx, int(side[j]), int(i0), float(p)))
    tab = np.asarray(tab, dtype=float)
    off = np.concatenate([[0], np.cumsum(L)[:-1]]).astype("int64") if len(L) else np.zeros(0, dtype="int64")
    if not np.allclose(tab[off], s["r_mach"], rtol=0, atol=1e-12, equal_nan=True):
        raise RuntimeError("%s: offset 0 is not the real trade" % ctx["a"])
    nxt = np.r_[i_in[1:], n]
    last_bar = valid[pos + L - 1] if len(L) else np.zeros(0, dtype="int64")
    rec.update(L=L.tolist(), tab=tab.tolist(), early=early_j,
               L_median=float(np.median(L)) if len(L) else None,
               share_window_past_next_entry=float(np.mean(last_bar >= nxt)) if len(L) else None)
    return rec


def causal_stats(r, mk, h2, nm=len(MARKETS)):
    """(markets, NSTAT) stats of one draw: per market (trades, sum_r, wins, 0, 0) for all / first half / second half."""
    ok = np.isfinite(r)
    rr = np.where(ok, r, 0.0)
    out = np.zeros((nm, NSTAT))
    for off, sel in ((0, ok), (5, ok & ~h2), (10, ok & h2)):
        out[:, off] = np.bincount(mk, weights=sel.astype(float), minlength=nm)
        out[:, off + 1] = np.bincount(mk, weights=np.where(sel, rr, 0.0), minlength=nm)
        out[:, off + 2] = np.bincount(mk, weights=(sel & (rr > 0)).astype(float), minlength=nm)
    return out


def causal_draw(study, D, k, seed):
    """Draw k over all markets at once (D: the concatenated outcomes) -> {cell name: (markets, NSTAT)}."""
    g = draw_rng(seed, k)
    if study == "H81b":
        u = g.random((2, D["T"]))
        r_tr = np.where(h81b_sides(D["p_long"], u[0]) == 1, D["rp"], D["rm"])
        r_coin = np.where(h81b_sides(0.5, u[1]) == 1, D["rp"], D["rm"])
        return {"main": causal_stats(r_tr, D["mk"], D["h2"]), "coin": causal_stats(r_coin, D["mk"], D["h2"])}
    u = g.random(D["T"])
    r = D["tab"][D["off"] + h82b_offsets(D["L"], u)]
    return {"main": causal_stats(r, D["mk"], D["h2"])}


def causal_concat(recs, groups):
    """The per-market outcome records, concatenated in the fixed market order."""
    D = {"mk": [], "h2": [], "side": [], "rp": [], "rm": [], "p_long": [], "tab": [], "L": [], "off": [], "real": []}
    base = 0
    for g, assets in groups:
        for a in assets:
            m = recs[g]["markets"][a]
            nt = len(m["side"])
            D["mk"] += [MARKETS.index(a)] * nt
            D["h2"] += m["h2"]
            D["side"] += m["side"]
            D["real"] += m["r_mach"]
            if "r_plus" in m:
                D["rp"] += m["r_plus"]
                D["rm"] += m["r_minus"]
                D["p_long"] += m["p_long"]
            if "tab" in m:
                L = np.asarray(m["L"], dtype="int64")
                D["off"] += (base + np.concatenate([[0], np.cumsum(L)[:-1]])).astype("int64").tolist() if nt else []
                D["L"] += m["L"]
                D["tab"] += m["tab"]
                base += len(m["tab"])
    out = dict((k, np.asarray(v)) for k, v in D.items())
    out["mk"] = out["mk"].astype("int64")
    out["h2"] = out["h2"].astype(bool)
    out["L"] = out["L"].astype("int64")
    out["off"] = out["off"].astype("int64")
    out["T"] = int(len(out["mk"]))
    return out


def run_causal_study(study, args, out, groups, cut, draws, smoke=False):
    """H81b / H82b. Phase 1 (per group, resumable): load, real book + gates, outcomes -> outcomes_<group>.json.
    Phase 2: vectorised draws in blocks of CAUSAL_BLOCK, each block one file written whole (atomic rename), so a resume
    recomputes only an unfinished block and no draw is ever counted twice."""
    fp = fingerprint(study, draws, cut)
    seed = STUDIES[study]["seed"]
    nblk = int(math.ceil(draws / float(CAUSAL_BLOCK)))
    total = len(groups) + nblk

    def blk_path(b):
        return os.path.join(out, "draws_%s_%04d.npz" % (study, b))

    def blk_ok(b):
        p = blk_path(b)
        if not os.path.exists(p):
            return False
        try:
            z = np.load(p)
            return str(z["fp"]) == fp
        except Exception:                                        # a torn file: recomputed
            return False

    def cost_left(gdone, bdone):
        pre = sum(PREP_S[g] + CAUSAL_PRE_S[study][g] for g, _a in groups if g not in gdone)
        return pre + (nblk - bdone) * CAUSAL_BLOCK * CAUSAL_DRAW_S[study]
    prog = Progress(out, total, None)
    recs, gdone = {}, set()
    for g, assets in groups:
        path = os.path.join(out, "outcomes_%s.json" % g)
        if os.path.exists(path):
            r = json.load(open(path))
            if r.get("fp") == fp:
                recs[g] = r
                gdone.add(g)
    prog.update(len(gdone), cost_left(gdone, 0), note="starting")
    for g, assets in groups:
        if g in gdone:
            continue
        prep = load_group(g, assets, args.fits_dir, out, cut)
        ctxs = dict((a, market_ctx(prep, a)) for a in assets)
        gl = {}
        real = real_books_for(study, ctxs, gl, prep)
        rec = {"fp": fp, "group": g, "end": str(prep["times"][-1])[:16], "gate": gl, "real": real, "markets": {},
               "windows": dict((a, [str(prep["times"][c["lo"]])[:16], str(prep["times"][c["n"] - 1])[:16]])
                               for a, c in ctxs.items())}
        for a, ctx in ctxs.items():
            rec["markets"][a] = causal_outcomes(study, ctx)
        write_json(os.path.join(out, "outcomes_%s.json" % g), rec)
        recs[g] = rec
        gdone.add(g)
        log("%s: loaded to %s, outcomes saved" % (g, rec["end"]))
        prog.update(len(gdone), cost_left(gdone, 0), note="%s outcomes" % g)
        del prep, ctxs
        gc.collect()
    D = causal_concat(recs, groups)
    bdone = sum(1 for b in range(nblk) if blk_ok(b))
    for b in range(nblk):
        if blk_ok(b):
            continue
        k0, k1 = b * CAUSAL_BLOCK, min(draws, (b + 1) * CAUSAL_BLOCK)
        S = {}
        for k in range(k0, k1):
            for name, st in causal_draw(study, D, k, seed).items():
                S.setdefault(name, np.empty((k1 - k0, len(MARKETS), NSTAT)))[k - k0] = st
        tmp = blk_path(b) + ".tmp.npz"
        np.savez(tmp, fp=fp, k0=k0, k1=k1, **S)
        os.replace(tmp, blk_path(b))
        bdone += 1
        prog.update(len(groups) + bdone, cost_left(gdone, bdone), note="draws to %d" % k1)
        if smoke:
            log("%s: draws %d-%d done" % (study, k0, k1 - 1))
    # collect
    names = ("main", "coin") if study == "H81b" else ("main",)
    S = dict((nm, np.full((draws, len(MARKETS), NSTAT), np.nan)) for nm in names)
    for b in range(nblk):
        z = np.load(blk_path(b))
        if str(z["fp"]) != fp:
            raise RuntimeError("block %d is from another configuration" % b)
        for nm in names:
            S[nm][int(z["k0"]):int(z["k1"])] = z[nm]
    reals, gates, windows, diag = {}, {}, {}, {}
    real_st = causal_stats(D["real"].astype(float), D["mk"], D["h2"])
    for g, assets in groups:
        gates[g], windows[g] = recs[g]["gate"], recs[g]["windows"]
        for a in assets:
            reals[a] = {"real": real_st[MARKETS.index(a)].tolist(), "current": recs[g]["real"][a]["current"]}
            m = recs[g]["markets"][a]
            if study == "H82b":
                diag[a] = {"window_median_bars": m["L_median"], "share_window_past_next_entry": m["share_window_past_next_entry"]}
    # exact expectations of the placebo mean R (descriptive): H81b closed form, H82b the mean over each window
    exp = {}
    for sname, mk in SLICES:
        idx = np.isin(D["mk"], [MARKETS.index(a) for a in mk])
        if study == "H81b":
            e = D["p_long"] * D["rp"] + (1 - D["p_long"]) * D["rm"]
            ec = 0.5 * D["rp"] + 0.5 * D["rm"]
            ok = idx & np.isfinite(e)
            exp[sname] = {"main": float(e[ok].mean()) if ok.any() else None,
                          "coin": float(ec[ok].mean()) if ok.any() else None}
        else:
            e = np.array([np.nanmean(D["tab"][o:o + l]) for o, l in zip(D["off"], D["L"])]) if D["T"] else np.zeros(0)
            ok = idx & np.isfinite(e)
            exp[sname] = {"main": float(e[ok].mean()) if ok.any() else None}
    return reals, S, gates, windows, {"exact_expectation_all": exp, "per_market": diag}


# ------------------------------------------------------------------ H87 / H88 / H89: the real books' trades
def real_trades(args, out, groups, cut, study):
    """Per group, the trades of the current rule, the 30-day filter and the wait, saved once (resumable)."""
    fp = fingerprint(study, STUDIES[study]["draws"], cut)
    allr = {}
    prog = Progress(out, len(groups) + 1, None)
    for gi, (g, assets) in enumerate(groups):
        path = os.path.join(out, "trades_%s.json" % g)
        if os.path.exists(path) and json.load(open(path)).get("fp") == fp:
            allr[g] = json.load(open(path))
            continue
        prep = load_group(g, assets, args.fits_dir, out, cut)
        rec = {"fp": fp, "group": g, "end": str(prep["times"][-1])[:16], "markets": {}}
        for a in assets:
            ctx = market_ctx(prep, a)
            books = {"current": run_book(ctx, RULE_CURRENT), "trend30": run_book(ctx, RULE_TREND),
                     "wait": run_book(ctx, RULE_WAIT)}
            if study == "H88":                                   # gate: the post-hoc fee is the replayed fee
                cfg2 = dict(ctx["cfg"], cost_side=0.0015)
                inp = ctx["inp"]
                b2 = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg2, ctx["lo"], ctx["n"],
                                 bias=inp["bias"], guard=inp["guard"], rule=dict(RULE_CURRENT), aux=ctx["aux"],
                                 times_ms=ctx["tms"], row_of=ctx["row_of"])
                t0, t1 = books["current"]["trades"], b2["trades"]
                ok = len(t0) == len(t1) and np.array_equal(t0.i_in.values, t1.i_in.values)
                if ok:
                    gross = t0.r_mult.values + t0.fees_usd.values / t0.risk_usd.values
                    post = gross - (0.0015 / ctx["cfg"]["cost_side"]) * t0.fees_usd.values / t0.risk_usd.values
                    ok = bool(np.allclose(post, t1.r_mult.values, rtol=0, atol=1e-9, equal_nan=True))
                rec.setdefault("gate", {})[a] = ok
                if not ok:
                    raise RuntimeError("fee gate failed on %s" % a)
            rec["markets"][a] = {"fee": ctx["cfg"]["cost_side"], "mid_ms": int(ctx["tms"][ctx["mid"]]), "books": {}}
            for name, b in books.items():
                t = b["trades"]
                rec["markets"][a]["books"][name] = {
                    "t_in_ms": [int(x) for x in t.t_in_ms.values], "r": [float(x) for x in t.r_mult.values],
                    "fees_r": [float(x) for x in (t.fees_usd.values / t.risk_usd.values)],
                    "slip_r": [float(x) for x in (t.p_in.values / np.abs(t.p_in.values - t.stop0.values))]}
            del books
        write_json(path, rec)
        allr[g] = rec
        prog.update(gi + 1, 60.0 * (len(groups) - gi - 1), note=g)
        del prep
        gc.collect()
    return allr, prog


def frame_of(allr, book):
    rows = []
    for g, rec in allr.items():
        for a, m in rec["markets"].items():
            b = m["books"][book]
            for t, r, f, s in zip(b["t_in_ms"], b["r"], b["fees_r"], b["slip_r"]):
                rows.append((a, t, r, f, s, m["fee"], t >= m["mid_ms"]))
    df = pd.DataFrame(rows, columns=["a", "t", "r", "fees_r", "slip_r", "fee", "h2"])
    ts = pd.to_datetime(df.t, unit="ms", utc=True)
    df["month"] = ts.dt.year * 12 + ts.dt.month - 1
    df["year"] = ts.dt.year
    df = df[np.isfinite(df.r)]
    return df


def slice_df(df, sname):
    if sname == "vault":
        return df[df.a.isin(VAULT)]
    if sname == "others":
        return df[~df.a.isin(VAULT)]
    return df


def cluster_ci(r, month, B, rng, stat="mean"):
    """Month-clustered bootstrap: calendar months resampled with replacement; -> (2.5%, 97.5%) of the mean R per trade."""
    if len(r) == 0:
        return [None, None]
    um, inv = np.unique(month, return_inverse=True)
    s = np.bincount(inv, weights=r, minlength=len(um))
    c = np.bincount(inv, minlength=len(um)).astype(float)
    idx = rng.integers(0, len(um), size=(B, len(um)))
    S, C = s[idx].sum(axis=1), c[idx].sum(axis=1)
    m = S / np.where(C > 0, C, np.nan) if stat == "mean" else S
    return [float(np.nanpercentile(m, 2.5)), float(np.nanpercentile(m, 97.5))]


def study_boot(args, out, groups, cut, draws):
    allr, prog = real_trades(args, out, groups, cut, "H87")
    seed = STUDIES["H87"]["seed"]
    res = {"books": {}}
    for book in ("current", "trend30", "wait"):
        df = frame_of(allr, book)
        months = np.arange(df.month.min(), df.month.max() + 1)
        res["books"][book] = {}
        for sname, _mk in SLICES:
            d = slice_df(df, sname)
            for pname, sel in (("all", None), ("h1", False), ("h2", True)):
                dd = d if sel is None else d[d.h2 == sel]
                mm = months if sel is None else np.unique(df[df.h2 == sel].month)
                if len(mm) == 0:                                 # no trade in this half (a smoke slice)
                    res["books"][book]["%s_%s" % (sname, pname)] = None
                    continue
                mm = np.arange(mm.min(), mm.max() + 1)
                monthly = dd.groupby("month").r.sum().reindex(mm, fill_value=0.0).values
                cell = {"months": int(len(mm)), "monthly_mean_r": float(monthly.mean())}
                for blk in (3, 1):
                    rng = draw_rng(seed, blk, SLICES.index((sname, _mk)), ["all", "h1", "h2"].index(pname),
                                   ["current", "trend30", "wait"].index(book))
                    nb = 12 // blk
                    starts = rng.integers(0, len(mm), size=(draws, nb))
                    idx = (starts[:, :, None] + np.arange(blk)[None, None, :]) % len(mm)   # circular moving blocks
                    path = monthly[idx.reshape(draws, 12)]
                    cum = np.cumsum(path, axis=1)
                    peak = np.maximum.accumulate(np.concatenate([np.zeros((draws, 1)), cum], axis=1), axis=1)[:, 1:]
                    fall = (cum - peak).min(axis=1)
                    tot = cum[:, -1]
                    cell["block%d" % blk] = {
                        "sum12_q": [float(x) for x in np.percentile(tot, [5, 25, 50, 75, 95])],
                        "p_losing_year": float((tot < 0).mean()),
                        "worst_fall_q": [float(x) for x in np.percentile(fall, [5, 25, 50, 75, 95])]}
                res["books"][book]["%s_%s" % (sname, pname)] = cell
    prog.update(len(groups) + 1, 0.0, note="bootstrap done")
    return res


def study_costs(args, out, groups, cut, draws):
    allr, prog = real_trades(args, out, groups, cut, "H88")
    seed = STUDIES["H88"]["seed"]
    FEES, SLIPS = (0.0002, 0.0005, 0.0010, 0.0015), (0.0, 0.0002, 0.0005, 0.0010)
    res = {"fees": FEES, "slips": SLIPS, "books": {}, "gate": dict((g, r.get("gate")) for g, r in allr.items())}
    for bi, book in enumerate(("current", "trend30", "wait")):
        df = frame_of(allr, book)
        gross = df.r.values + df.fees_r.values
        unit_fee = df.fees_r.values / df.fee.values               # R paid per unit of fee a side
        res["books"][book] = {}
        for si, (sname, _mk) in enumerate(SLICES):
            m = df.a.isin(VAULT).values if sname == "vault" else ~df.a.isin(VAULT).values if sname == "others" else \
                np.ones(len(df), bool)
            cells = {}
            for fi, f in enumerate(FEES):
                for sj, s in enumerate(SLIPS):
                    r = gross - f * unit_fee - s * df.slip_r.values
                    cell = {}
                    for pname, sel in (("all", m), ("h1", m & ~df.h2.values), ("h2", m & df.h2.values)):
                        rr = r[sel]
                        cell[pname] = {"trades": int(len(rr)), "mean_r": float(rr.mean()) if len(rr) else None,
                                       "sum_r": float(rr.sum())}
                    cell["all"]["ci"] = cluster_ci(r[m], df.month.values[m], draws, draw_rng(seed, bi, si, fi, sj))
                    cells["fee%.2f_slip%.2f" % (f * 100, s * 100)] = cell
                # break-even slip at this fee: mean R is linear in the slip
                a0 = (gross[m] - f * unit_fee[m]).mean()
                b0 = df.slip_r.values[m].mean()
                cells["breakeven_slip_pct_at_fee%.2f" % (f * 100)] = float(a0 / b0 * 100) if b0 else None
            a1, b1 = gross[m].mean(), unit_fee[m].mean()
            cells["breakeven_fee_pct_at_slip0"] = float(a1 / b1 * 100) if b1 else None
            res["books"][book][sname] = cells
    prog.update(len(groups) + 1, 0.0, note="surface done")
    return res


def study_years(args, out, groups, cut, draws):
    allr, prog = real_trades(args, out, groups, cut, "H89")
    seed = STUDIES["H89"]["seed"]
    res = {"books": {}}
    for bi, book in enumerate(("current", "trend30", "wait")):
        df = frame_of(allr, book)
        years = sorted(df.year.unique())
        res["books"][book] = {}
        for si, (sname, _mk) in enumerate(SLICES):
            d = slice_df(df, sname)
            cell = {"all": {"trades": int(len(d)), "mean_r": float(d.r.mean()), "sum_r": float(d.r.sum()),
                            "ci": cluster_ci(d.r.values, d.month.values, draws, draw_rng(seed, bi, si, 0))}}
            for y in years:
                one, rest = d[d.year == y], d[d.year != y]
                cell[str(y)] = {
                    "alone": {"trades": int(len(one)), "mean_r": float(one.r.mean()) if len(one) else None,
                              "sum_r": float(one.r.sum()),
                              "ci": cluster_ci(one.r.values, one.month.values, draws, draw_rng(seed, bi, si, y, 1))},
                    "left_out": {"trades": int(len(rest)), "mean_r": float(rest.r.mean()) if len(rest) else None,
                                 "sum_r": float(rest.r.sum()),
                                 "ci": cluster_ci(rest.r.values, rest.month.values, draws, draw_rng(seed, bi, si, y, 2))}}
            full = cell["all"]["mean_r"]
            flips = [y for y in years if cell[str(y)]["left_out"]["mean_r"] is not None
                     and np.sign(cell[str(y)]["left_out"]["mean_r"]) != np.sign(full)]
            cell["years_whose_removal_flips_the_sign"] = [int(y) for y in flips]
            res["books"][book][sname] = cell
    prog.update(len(groups) + 1, 0.0, note="years done")
    return res


# =====================================================================================
# report
# =====================================================================================
WHAT = {
    "H80": ("the Setups book (b_targets)", "its odds shifted in time"),
    "H81": ("the Setups book (b_targets)", "its trades' sides permuted within market and month"),
    "H82": ("the Setups book (b_targets)", "its trades moved to random bars of the same month"),
    "H83": ("the 30-day filter book (b_trend30)", "the 30-day move shifted in time"),
    "H84": ("the wait-after-stop book (b_wait_stop)", "the wait switched on after random exits"),
    "H85": ("the Setups book (b_targets)", "its higher-timeframe bias and tide shifted in time"),
    "H86": ("the Setups book (b_targets)", "its volatility unit shuffled within each month"),
    "H81b": ("the Setups book's choice of side (b_targets)",
             "sides drawn from the long share of its previous 20 trades on the market"),
    "H82b": ("the Setups book's entry timing (b_targets)",
             "the same trades moved to random bars at or after the real entry, within the median of its previous 20 "
             "entry gaps"),
}
WHAT_COIN = {"H81b": ("the Setups book's choice of side (b_targets)", "a fair coin for each trade's side")}


def verdict_line(study, summ, smoke):
    c = summ["cells"]["pooled_all"]
    p = c["mean_r"]["p_upper"]
    who, how = WHAT[study]
    word = "IS distinguishable" if p <= 0.05 else "is NOT distinguishable"
    pre = "SMOKE RUN (tiny slice, numbers are not results). " if smoke else ""
    return ("%s**%s %s from its placebo (%s) at p = %.4f** (primary: pooled mean R per trade over the eight markets, "
            "one-sided, real at least as good; %d draws). Real %+.4fR a trade; placebo median %+.4fR (5%%-95%%: %+.4f to %+.4f). "
            "Lower-tail p (real at most as good) = %.4f." % (
                pre, who[0].upper() + who[1:], word, how, p, summ["draws_used"], c["real"]["mean_r"], c["mean_r"]["q50"],
                c["mean_r"]["q05"], c["mean_r"]["q95"], c["mean_r"]["p_lower"]))


def write_report(out, study, res, smoke):
    L = ["# %s: %s" % (study, STUDIES[study]["title"]), ""]
    if smoke:
        L += ["**SMOKE RUN on a tiny slice. These numbers test the code; they are not results and are not reported.**", ""]
    kind = STUDIES[study]["kind"]
    if kind in ("book", "trade", "side", "causal"):
        summ = res["summary"]
        L += ["## Conclusion", "", verdict_line(study, summ, smoke), ""]
        if kind == "causal":
            if "summary_coin" in res:
                c = res["summary_coin"]["cells"]["pooled_all"]["mean_r"]
                who, how = WHAT_COIN[study]
                L += ["Secondary (registered, not used for the conclusion): %s %s from %s at p = %.4f (lower-tail p = "
                      "%.4f; placebo median %+.4fR)." % (who[0].upper() + who[1:], "IS distinguishable" if c["p_upper"] <= 0.05
                                                          else "is NOT distinguishable", how, c["p_upper"], c["p_lower"],
                                                          c["q50"]), ""]
            L += ["Exact placebo expectations (descriptive): `%s`" % json.dumps(res.get("extra", {}).get(
                "exact_expectation_all"), default=_jsonable), ""]
            if res.get("extra", {}).get("per_market"):
                L += ["Windows (H82b, descriptive): `%s`" % json.dumps(res["extra"]["per_market"], default=_jsonable), ""]
        L += [
              "Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or "
              "two will look significant by chance. Data end at the last session at or before %s (the holdout is not read)."
              % CUT, "", "## All cells (p_upper: share of draws at least as good, +1 corrected)", "",
              "| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | "
              "p sum R | p lower (mean) | placebo trades (median) |", "|---|---|---|---|---|---|---|---|---|---|"]
        for name, c in summ["cells"].items():
            L.append("| %s | %d | %+.4f | %+.1f | %+.4f | %s | %.4f | %.4f | %.4f | %s |" % (
                name, c["real"]["trades"], c["real"]["mean_r"], c["real"]["sum_r"], c["current_rule"]["mean_r"],
                "-" if c["mean_r"]["q50"] is None else "%+.4f" % c["mean_r"]["q50"], c["mean_r"]["p_upper"],
                c["sum_r"]["p_upper"], c["mean_r"]["p_lower"],
                "-" if c["placebo_trades_median"] is None else "%.0f" % c["placebo_trades_median"]))
        L += ["", "## Per market (all; descriptive)", "", "| Market | trades | real mean R | placebo median | p |",
              "|---|---|---|---|---|"]
        for a, m in summ["per_market"].items():
            L.append("| %s | %d | %+.4f | %s | %.4f |" % (a, m["real_trades"], m["real_mean_r"],
                                                         "-" if m["mean_r"]["q50"] is None else "%+.4f" % m["mean_r"]["q50"],
                                                         m["mean_r"]["p_upper"]))
        L += ["", "Gates: %s" % json.dumps(res.get("gates", {}), default=_jsonable)]
    elif kind == "boot":
        L += ["## Conclusion", ""]
        for book in ("current", "trend30", "wait"):
            c = res["books"][book]["pooled_all"]["block3"]
            v = res["books"][book]["vault_all"]["block3"]
            L.append("- %s: chance of a losing 12 months %.0f%% (eight markets) and %.0f%% (BTC+ETH); median 12-month sum %+.1fR; "
                     "median worst fall inside the year %.1fR (3-month blocks)." % (
                         book, 100 * c["p_losing_year"], 100 * v["p_losing_year"], c["sum12_q"][2], c["worst_fall_q"][2]))
        L += ["", "A bootstrap of history describes what history would give if the future were like it; it is not a "
              "forecast. The two variants were found on this same history, so their figures are flattered.", "",
              "```", json.dumps(res["books"], indent=1, default=_jsonable), "```"]
    elif kind == "costs":
        L += ["## Conclusion", ""]
        for book in ("current", "trend30", "wait"):
            for sname in ("pooled", "vault"):
                c = res["books"][book][sname]
                L.append("- %s, %s: break-even fee with no slip %s%% a side; break-even slip at 0.10%% fee %s%%." % (
                    book, sname, _pct(c["breakeven_fee_pct_at_slip0"]), _pct(c["breakeven_slip_pct_at_fee0.10"])))
        L += ["", "```", json.dumps(res["books"], indent=1, default=_jsonable), "```"]
    elif kind == "years":
        L += ["## Conclusion", ""]
        for book in ("current", "trend30", "wait"):
            for sname in ("pooled", "vault", "others"):
                c = res["books"][book][sname]
                fl = c["years_whose_removal_flips_the_sign"]
                L.append("- %s, %s: mean %+.4fR over %d trades; %s" % (
                    book, sname, c["all"]["mean_r"], c["all"]["trades"],
                    ("leaving out %s alone turns the sign: the result rests on %s" % (
                        ", ".join(map(str, fl)), "one year" if len(fl) == 1 else "those years")) if fl else
                    "no single year turns the sign when left out"))
        L += ["", "```", json.dumps(res["books"], indent=1, default=_jsonable), "```"]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def _pct(x):
    return "-" if x is None else "%.3f" % x


# =====================================================================================
# main
# =====================================================================================
def estimate_hours(study, groups=GROUPS, draws=None):
    s = STUDIES[study]
    draws = s["draws"] if draws is None else draws
    prep = sum(PREP_S[g] for g, _a in groups)
    if s["kind"] in ("book", "trade"):
        return (prep + draws * sum(DRAW_S[study][g] for g, _a in groups)) / 3600.0
    if s["kind"] == "causal":                                    # outcomes precomputed once per group, then cheap draws
        return (prep + sum(CAUSAL_PRE_S[study][g] for g, _a in groups) + draws * CAUSAL_DRAW_S[study]) / 3600.0
    if s["kind"] == "side":                                      # both sides of every trade replayed once, then cheap draws
        return (prep + 2 * sum(DRAW_S["H82"][g] for g, _a in groups) + draws * 0.003) / 3600.0
    return (prep + 3 * sum(DRAW_S["H80"][g] for g, _a in groups) / 2 + 120.0) / 3600.0   # three engine runs per market


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, choices=sorted(STUDIES))
    ap.add_argument("--fits-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--time-draws", type=int, default=0, help="timing only: N draws per group, nothing kept or printed but seconds")
    args = ap.parse_args(argv)
    study = args.study
    if args.estimate:
        print("%.2f" % estimate_hours(study))
        return 0
    if args.time_draws:
        return time_draws(study, args)
    groups, cut, draws, out = GROUPS, CUT, STUDIES[study]["draws"], args.out
    if args.smoke:
        groups, cut, out = [("index", ["SPX"])], SMOKE_CUT, os.path.join(args.out, "smoke")
        draws = {"side": 200, "boot": 500, "costs": 200, "years": 200, "causal": 400}.get(STUDIES[study]["kind"], 3)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "DONE")):
        log("%s already DONE in %s" % (study, out))
        return 0
    t0 = time.time()
    kind = STUDIES[study]["kind"]
    res = {"study": study, "title": STUDIES[study]["title"], "seed": STUDIES[study]["seed"], "draws": draws, "cut": cut,
           "mid": MID, "smoke": bool(args.smoke)}
    if kind in ("book", "trade"):
        fp = run_draw_study(study, args, out, groups, cut, draws, smoke=args.smoke)
        reals, D, ex, meta = collect(out, groups, fp, draws)
        res["summary"] = summarise_draws(study, reals, D, ex)
        res["gates"] = dict((g, m["gate"]) for g, m in meta.items())
        res["windows"] = dict((g, m["windows"]) for g, m in meta.items())
        res["real"] = reals
        if res["summary"]["draws_used"] < draws:
            raise RuntimeError("only %d of %d draws found" % (res["summary"]["draws_used"], draws))
    elif kind == "side":
        reals, S, gl = run_side_study(args, out, groups, cut, draws, smoke=args.smoke)
        res["summary"] = summarise_draws(study, reals, S, {})
        res["gates"] = gl
        res["real"] = reals
    elif kind == "causal":
        reals, S, gl, win, extra = run_causal_study(study, args, out, groups, cut, draws, smoke=args.smoke)
        res["summary"] = summarise_draws(study, reals, S["main"], {})
        if "coin" in S:
            res["summary_coin"] = summarise_draws(study, reals, S["coin"], {})
        res["gates"], res["windows"], res["real"], res["extra"] = gl, win, reals, extra
        if res["summary"]["draws_used"] < draws:
            raise RuntimeError("only %d of %d draws found" % (res["summary"]["draws_used"], draws))
    elif kind == "boot":
        res.update(study_boot(args, out, groups, cut, draws))
    elif kind == "costs":
        res.update(study_costs(args, out, groups, cut, draws))
    elif kind == "years":
        res.update(study_years(args, out, groups, cut, draws))
    res["seconds"] = round(time.time() - t0, 1)
    write_json(os.path.join(out, "results.json"), res)
    write_report(out, study, res, args.smoke)
    open(os.path.join(out, "DONE"), "w").close()
    p = os.path.join(out, "progress.json")
    if os.path.exists(p):
        pr = json.load(open(p))
        pr.update(done=pr.get("total", pr.get("done")), est_hours_left=0.0,
                  updated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), note="DONE")
        write_json(p, pr)
    log("%s done in %.0fs -> %s" % (study, time.time() - t0, out))
    return 0


def time_draws(study, args):
    """Timing only (registration aid): per group, the load time and the seconds of N placebo draws; prints seconds and
    peak memory, keeps and prints no statistic."""
    import resource
    out = os.path.join(args.out, "timing_scratch")
    os.makedirs(out, exist_ok=True)
    kind = STUDIES[study]["kind"]
    if kind == "causal":
        return time_causal(study, args, out)
    for gi, (g, assets) in enumerate(GROUPS):
        prep = load_group(g, assets, args.fits_dir, out, CUT)
        t1 = time.time()
        ctxs = dict((a, market_ctx(prep, a)) for a in assets)
        real_books_for(study, ctxs, {})
        if kind == "trade":
            for a, ctx in ctxs.items():
                unit = ctx["inp"]["unit"]
                rows = np.arange(ctx["lo"] + 1, ctx["n"] - 1)
                rows = rows[np.isfinite(unit[rows - 1]) & (unit[rows - 1] > 0)]
                ctx["valid_by_month"] = dict((int(m), rows[ctx["month"][rows] == m]) for m in np.unique(ctx["month"][rows]))
        t_real = time.time() - t1
        secs = []
        for k in range(args.time_draws):
            t2 = time.time()
            _ = book_draw(study, ctxs, k, gi) if kind == "book" else trade_draw(study, ctxs, k, gi)
            secs.append(time.time() - t2)
        print("TIMING %s %s load %.1fs real+gates %.1fs draw %s maxrss %.0f MB" % (
            study, g, prep["_load_s"], t_real, " ".join("%.2f" % s for s in secs),
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0), flush=True)
        del prep, ctxs
        gc.collect()
    return 0


def time_causal(study, args, out):
    """Timing only for H81b / H82b: per group the load, the real book with its gates, the outcome precompute; then N
    vectorised draws over every group loaded. Prints seconds and peak memory only."""
    import resource
    recs = {}
    for g, assets in GROUPS:
        prep = load_group(g, assets, args.fits_dir, out, CUT)
        t1 = time.time()
        ctxs = dict((a, market_ctx(prep, a)) for a in assets)
        real_books_for(study, ctxs, {})
        t2 = time.time()
        recs[g] = {"markets": dict((a, causal_outcomes(study, ctx)) for a, ctx in ctxs.items())}
        print("TIMING %s %s load %.1fs real+gates %.1fs outcomes %.1fs maxrss %.0f MB" % (
            study, g, prep["_load_s"], t2 - t1, time.time() - t2,
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0), flush=True)
        del prep, ctxs
        gc.collect()
    D = causal_concat(recs, GROUPS)
    t3 = time.time()
    for k in range(args.time_draws):
        causal_draw(study, D, k, STUDIES[study]["seed"])
    print("TIMING %s draw %.4fs each (%d draws, %d trades) maxrss %.0f MB" % (
        study, (time.time() - t3) / args.time_draws, args.time_draws, D["T"],
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0), flush=True)
    return 0


def rw_main(argv=None):
    """`placebo.py --rw-check [walks]`: the random-walk check of H81b / H82b (synthetic data only), printed as JSON."""
    walks = int(argv[0]) if argv else 120
    print(json.dumps(rw_check(walks=walks, draws=400, years=2, log=log), indent=1))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rw-check":
        sys.exit(rw_main(sys.argv[2:]))
    sys.exit(main())
