# -*- coding: utf-8 -*-
"""Workstream M, the history study (charter M1, M2, M4): where does short-horizon skill live, and does
any of it pay its costs? Writes research/out/intraday.md and .json (and intraday_<group>.json per group).

    py -3 research/intraday_study.py --group crypto        one market group (one at a time: memory)
    py -3 research/intraday_study.py --report              merge the groups, choose on the first half, write

PER GROUP
 1. Evidence, built in chunks (--chunk-months, default 12) each with --warm-days (300) of warm-up bars
    before it, so that no more than ~2 years of the full evidence frame is in memory at once; only the
    matrix columns the voices below read are kept (float32), with the bars, ATRs, swings, reach, regime
    and the release guard. Differences from the live step's one-piece build: slow readings whose warm-up
    exceeds 300 days (the weekly trend's 100/200-week averages) are read with fewer components.
 2. Three minds on the same voices (intraday.voice_set: the main engine's ten voting cards and the owner,
    plus the base rate): 1h (4 bars, 0.75 x ATR 1h), 4h (16 bars, 1 x ATR 1h) and, for comparison, the
    main question (96 bars, 1.5 x ATR 1h). Walked forward with no look-ahead, refitted every 4 weeks
    (live: every week; cheaper here, same rule otherwise), trust and the mix as the engine.
 3. M1 skill per market, per session (UTC: asia 21-07, london 07-12, overlap 12-16, ny 16-21), per regime
    and per half (the halves split the calendar span 2020-01-01 .. last bar in two, the same date for
    every market): calls graded, log-loss skill against the base rate, direction hit rate, claimed-edge
    (5 points) hit rate. Plus a voice rating at each horizon: every voice listed in RATE_VOICES fitted once
    on the first half and scored on the second (which cards know the next hour?).
 4. M2: how often the expected value after costs clears 0 / 0.05 / 0.10 R (1-barrier stop and target).
 5. M3/M4: the swing book (intraday.run_swing) over the whole span under GRID (stop x target x margin),
    each trade attributed to the session / regime / half of its decision close, per market:
    trades, wins, R before and after costs, profit factor, % per trade.
REPORT: one variant per mind is chosen on the FIRST HALF only, pooled over all eight markets (best net R
per trade, at least 300 trades); every variant tried is counted and listed; the second half is the
out-of-sample read. A history read can reject an idea, never prove one.
"""
import argparse
import ctypes
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, evidence, intraday, labels, livefeeds, model  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out")
START = pd.Timestamp(CFG["birth"], tz="UTC")
EVERY_WEEKS = 4
MIND_SPECS = [("1h", intraday.MINDS["1h"]), ("4h", intraday.MINDS["4h"]), ("24h", intraday.REF_24H)]
# voices rated at each horizon (fitted on the first half, scored on the second): the voting voices and
# the cards most about the next hours; the live-only voices (book, Kronos, news) have no history
RATE_EXTRA = ("clock", "intraday", "trendq", "candles", "structure", "setups", "fib", "mavg", "risk", "macro",
              "cross", "funding", "liq", "lsratio", "overnight", "volx", "rates", "metals", "japan", "cot")
EV_MARGINS = (0.0, 0.05, 0.10)
GRID = [(stop, tgt, k, m) for stop in ("barrier", "structure")
        for tgt, k in (("r", 1.0), ("r", 1.5), ("r", 2.0), ("reach", 1.5))
        for m in (0.0, 0.05, 0.10)]
SESS = [s[0] for s in intraday.SESSIONS]
KEEP_EV = ["atr1h", "atr15", "regime", "release_soon", "sw_lo_15m", "sw_hi_15m", "sw_lo_1h", "sw_hi_1h",
           "reach_1h_med_pct", "reach_4h_med_pct"]
MIN_FREE_MB = 2500


# ------------------------------------------------------------------ memory
def free_mb():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys / 2 ** 20)
    except Exception:
        return None


def peak_mb():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    try:
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return int(c.PeakWorkingSetSize / 2 ** 20)
    except Exception:
        return None


# ------------------------------------------------------------------ 1. evidence, in chunks
def voices_for(assets):
    vote = intraday.voice_set(CFG)
    rate = [v for v in model.VOICE_NAMES if (v in RATE_EXTRA or v in vote) and v not in ("all", "base")]
    rate = [v for v in rate if any(evidence.voice_applies(v, a) for a in assets)]
    return vote, rate + ["base"]


def build_compact(assets, chunk_months, warm_days, log, end=None):
    crypto = CFG.get("crypto", CFG["assets"])
    bars = dict((a, data.load(a)) for a in assets)
    if end:
        cutoff = pd.Timestamp(end, tz="UTC")
        bars = dict((a, df[df.index < cutoff]) for a, df in bars.items())
    funding = dict((a, data.load_funding(a) if a in crypto else None) for a in assets)
    live = dict((a, livefeeds.load_live(a)) for a in assets)
    last = min(df.index[-1] for df in bars.values())
    vote, rate = voices_for(assets)
    feats = []
    for v in rate:
        feats += [f for f in model.VOICES[v][1] if f not in feats]
    fidx = [evidence.FEATURES.index(f) for f in feats]
    parts = dict((a, []) for a in assets)
    c0 = START
    while c0 <= last:
        c1 = c0 + pd.DateOffset(months=chunk_months)
        t0 = time.time()
        b = dict((a, df[(df.index >= c0 - pd.Timedelta(days=warm_days)) & (df.index < c1)]) for a, df in bars.items())
        ev = evidence.build(b, funding, live)
        for a in assets:
            e = ev[a]
            keep = np.asarray(e.index >= c0)
            X, ready = evidence.matrix(e)
            idx = e.index[keep]
            p = {"times": idx, "X": X[keep][:, fidx].astype(np.float32), "ready": ready[keep]}
            bb = b[a].loc[idx]
            for k in ("open", "high", "low", "close"):
                p[k] = bb[k].values.astype(float)
            for k in KEEP_EV:
                p[k] = e[k].values[keep] if k in e else np.full(int(keep.sum()), np.nan)
            parts[a].append(p)
            del X
        del ev, b
        gc.collect()
        log("  evidence %s .. %s: %d sessions (%.0fs, peak %s MB)" % (str(c0)[:10], str(min(c1, last))[:10],
                                                                    len(parts[assets[0]][-1]["times"]), time.time() - t0, peak_mb()))
        c0 = c1
    del bars
    st = {"assets": assets, "feats": feats, "vote": vote, "rate": rate}
    times = parts[assets[0]][0]["times"].append([p["times"] for p in parts[assets[0]][1:]])
    st["times"] = times
    for a in assets:
        st[a] = {}
        for k in parts[a][0]:
            if k == "times":
                continue
            st[a][k] = np.concatenate([p[k] for p in parts[a]])
        parts[a] = None
        assert len(st[a]["close"]) == len(times)
    return st


# ------------------------------------------------------------------ 3. skill tables
def skill_rows(y, odds, base, mask):
    """Graded calls in mask: count, log-loss skill vs base %, hit %, claimed-edge calls and hit %."""
    ok = mask & (y >= 0) & np.isfinite(odds[:, 0]) & np.isfinite(base[:, 0])
    if not ok.any():
        return {"calls": 0}
    yi = y[ok].astype(int)
    ll = -np.log(np.clip(odds[ok][np.arange(ok.sum()), yi], 1e-9, 1))
    lb = -np.log(np.clip(base[ok][np.arange(ok.sum()), yi], 1e-9, 1))
    edge = odds[ok][:, labels.UP] - odds[ok][:, labels.DOWN]
    d = yi > 0
    hit = ((edge > 0) & (yi == labels.UP)) | ((edge < 0) & (yi == labels.DOWN))
    sure = d & (np.abs(edge) >= intraday.EDGE_BAR)
    return {"calls": int(ok.sum()), "neither_pct": round(100.0 * (yi == 0).mean(), 1),
            "edge_p95_pts": round(float(np.percentile(np.abs(edge), 95)) * 100, 2),
            "skill_pct": round(float(1 - ll.mean() / lb.mean()) * 100, 2),
            "hit_pct": round(100.0 * hit[d].mean(), 2) if d.any() else None, "dir_calls": int(d.sum()),
            "edge_hit_pct": round(100.0 * hit[sure].mean(), 2) if sure.any() else None, "edge_calls": int(sure.sum())}


def rate_voices(st, y, H, rate, cols, cfg, mid):
    """Each voice fitted once on rows graded before the split, scored on the second half: log-loss skill vs base."""
    assets = st["assets"]
    X = dict((a, st[a]["X"]) for a in assets)
    rd = dict((a, st[a]["ready"]) for a in assets)
    W = intraday.fit_voices(X, rd, y, cols, rate, mid, 0, H, cfg)
    if W is None:
        return {}
    out, dirs = {}, {}
    lls = dict((v, []) for v in rate)
    hits = dict((v, []) for v in rate)
    for a in assets:
        rows = np.arange(mid, len(y[a]), 4)
        ok = rd[a][rows] & (y[a][rows] >= 0)
        rr, yy = rows[ok], y[a][rows[ok]].astype(int)
        Xa = np.asarray(X[a][rr], dtype=float)
        for v in rate:
            p = model.predict(W[v], Xa[:, cols[v]])
            lls[v].append(-np.log(np.clip(p[np.arange(len(yy)), yy], 1e-9, 1)))
            d = yy > 0
            e = p[d, labels.UP] - p[d, labels.DOWN]
            hits[v].append(((e > 0) == (yy[d] == labels.UP)))
    base = np.concatenate(lls["base"]).mean()
    for v in rate:
        if v != "base":
            out[v] = round(float(1 - np.concatenate(lls[v]).mean() / base) * 100, 3)
            dirs[v] = round(100.0 * float(np.concatenate(hits[v]).mean()), 2)
    return {"skill": dict(sorted(out.items(), key=lambda kv: -kv[1])),
            "direction_hit": dict(sorted(dirs.items(), key=lambda kv: -kv[1]))}


# ------------------------------------------------------------------ 5. swing aggregates
def agg_add(acc, key, r_g, r_n, pct, win):
    a = acc.setdefault(key, [0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    a[0] += 1
    a[1] += int(win)
    a[2] += r_g
    a[3] += r_n
    a[4] += max(r_g, 0.0)
    a[5] += max(-r_g, 0.0)
    a[6] += max(r_n, 0.0)
    a[7] += max(-r_n, 0.0)
    a[8] += pct


AGG_FIELDS = ["trades", "wins", "r_gross_sum", "r_net_sum", "gross_win_r", "gross_loss_r", "net_win_r", "net_loss_r", "pct_sum"]


def run_group(g, assets, args, log=print):
    t0 = time.time()
    st = build_compact(list(assets), args.chunk_months, args.warm_days, log, end=args.end)
    times = st["times"]
    n = len(times)
    feats = st["feats"]
    cols = intraday.cols_for(list(dict.fromkeys(st["rate"] + st["vote"])), feats)
    vote = st["vote"]
    cfg = dict(CFG, assets=tuple(assets))
    end_t = times[-1]
    mid_t = START + (end_t - START) / 2
    mid = int(times.searchsorted(mid_t))
    half = np.where(np.arange(n) < mid, 0, 1)
    sess = intraday.session_of(times)
    res = {"group": g, "assets": list(assets), "window": [str(times[0])[:16], str(end_t)[:16]], "split": str(mid_t)[:16],
           "sessions_n": n, "voices_voting": [v for v in vote if v != "base"], "minds": {}, "ev": {}, "swing": {},
           "voice_rating": {}}
    X = dict((a, st[a]["X"]) for a in assets)
    ready = dict((a, st[a]["ready"]) for a in assets)
    px = dict((a, dict((k, st[a][k]) for k in ("open", "high", "low", "close"))) for a in assets)
    atr = dict((a, st[a]["atr1h"]) for a in assets)
    vcols = dict((v, cols[v]) for v in vote)
    odds_of = {}
    for name, mind in MIND_SPECS:
        t1 = time.time()
        r = intraday.mind_odds(X, ready, px, atr, times, vcols, vote, cfg, mind, 0, n, 0, every_weeks=EVERY_WEEKS)
        bi = vote.index("base")
        tab = {}
        for a in assets:
            regime = np.asarray(st[a]["regime"], dtype=object)
            base = r["probs"][a][:, bi]
            y, od = r["y"][a], r["odds"][a]
            row = {}
            for h in (0, 1):
                hm = half == h
                row["half%d" % (h + 1)] = skill_rows(y, od, base, hm)
                for s in SESS:
                    row.setdefault("session", {}).setdefault(s, {})["half%d" % (h + 1)] = skill_rows(y, od, base, hm & (sess == s))
                for rg in sorted(set(x for x in regime if isinstance(x, str))):
                    row.setdefault("regime", {}).setdefault(rg, {})["half%d" % (h + 1)] = skill_rows(y, od, base, hm & (regime == rg))
            tab[a] = row
        res["minds"][name] = {"horizon": mind["horizon"], "barrier_atr": mind["barrier_atr"], "markets": tab}
        res["voice_rating"][name] = rate_voices(st, r["y"], int(mind["horizon"]), st["rate"], cols, cfg, mid)
        odds_of[name] = r["odds"]
        if name == "24h":
            y24 = r["y"]
        log("  mind %s: walked and graded (%.0fs, peak %s MB)" % (name, time.time() - t1, peak_mb()))
        del r
        gc.collect()
    # ---- M2: how often the EV after costs clears the margin (1-barrier stop and target)
    for name, mind in intraday.MINDS.items():
        res["ev"][name] = {}
        for a in assets:
            fee = CFG.get("asset_cost", {}).get(a, CFG["cost_side"])
            unit = mind["barrier_atr"] * atr[a]
            side, ev = intraday.best_ev(odds_of[name][a], fee, px[a]["close"], unit)
            ok = np.isfinite(ev)
            row = {"cost_rt_pct": round(200 * fee, 3),
                   "median_unit_pct": round(float(np.nanmedian(unit / px[a]["close"])) * 100, 3),
                   "median_cost_r": round(float(np.nanmedian(2 * fee * px[a]["close"] / unit)), 3)}
            for h in (0, 1):
                hm = ok & (half == h)
                row["half%d" % (h + 1)] = dict(("clears_%.2f_pct" % m, round(100.0 * float((ev[hm] >= m).mean()), 2) if hm.any() else None)
                                               for m in EV_MARGINS)
                row["half%d" % (h + 1)]["sessions"] = dict((s, round(100.0 * float((ev[hm & (sess == s)] >= 0.05).mean()), 2)
                                                            if (hm & (sess == s)).any() else None) for s in SESS)
            res["ev"][name][a] = row
    # ---- M3/M4: the swing book under every variant
    for name, mind in intraday.MINDS.items():
        t1 = time.time()
        res["swing"][name] = {}
        for vi, (stop, tgt, k, m) in enumerate(GRID):
            rule = dict(intraday.SWING_RULES[name], stop=stop, target=tgt, target_r=k, margin=m)
            vkey = "%s|%s|%.1f|%.2f" % (stop, tgt, k, m)
            acc = {}
            for a in assets:
                acfg = dict(CFG, cost_side=CFG.get("asset_cost", {}).get(a, CFG["cost_side"]),
                            leverage_cap=CFG.get("max_leverage", {}).get(a, 1.0))
                aux = {"sw_lo": st[a]["sw_lo_15m"], "sw_hi": st[a]["sw_hi_15m"], "sw_lo_1h": st[a]["sw_lo_1h"],
                       "sw_hi_1h": st[a]["sw_hi_1h"], "reach": {"1h": st[a]["reach_1h_med_pct"], "4h": st[a]["reach_4h_med_pct"]}}
                b = intraday.run_swing(px[a], odds_of[name][a], mind["barrier_atr"] * atr[a], acfg, 0, n,
                                       guard=np.asarray(st[a]["release_soon"], dtype=float) > 0.5, rule=rule, aux=aux)
                tr = b["trades"]
                if not len(tr):
                    continue
                dec = np.maximum(tr.i_in.values - 1, 0)
                regime = np.asarray(st[a]["regime"], dtype=object)
                for kk in range(len(tr)):
                    j = dec[kk]
                    rg, rn, pc = float(tr.r_gross.values[kk]), float(tr.r_mult.values[kk]), float(tr.pnl_pct.values[kk])
                    if rg != rg:
                        continue
                    hk = "half%d" % (half[j] + 1)
                    win = tr.pnl_usd.values[kk] > 0
                    for key in ("%s|all|%s" % (a, hk), "%s|s:%s|%s" % (a, sess[j], hk), "%s|r:%s|%s" % (a, regime[j], hk)):
                        agg_add(acc, key, rg, rn, pc, win)
            res["swing"][name][vkey] = acc
        log("  swing %s: %d variants (%.0fs)" % (name, len(GRID), time.time() - t1))
    if getattr(args, "time_live", False):
        res["live_timing"] = time_live(st, g, list(assets), y24, odds_of["24h"], log)
    res["seconds"] = round(time.time() - t0, 1)
    res["peak_mb"] = peak_mb()
    return res


def time_live(st, g, assets, y24, odds24, log):
    """M5: what the swing minds add to a live step. A prep shaped like live's (all history, the 240-day
    birth), the study's matrix widened to every feature (the columns no voting voice reads stay 0),
    then intraday.live_minds twice: cold (every week of the trust window fitted) and warm (cached)."""
    import tempfile
    times = st["times"]
    n = len(times)
    fpos = dict((f, k) for k, f in enumerate(st["feats"]))
    Xf = {}
    for a in assets:
        Xf[a] = np.zeros((n, len(evidence.FEATURES)), dtype=np.float32)
        for k, f in enumerate(evidence.FEATURES):
            if f in fpos:
                Xf[a][:, k] = st[a]["X"][:, fpos[f]]
    birth = times[-1] - pd.Timedelta(days=240)
    prep = {"cfg": dict(CFG, assets=tuple(assets), birth=str(birth.date())), "times": times, "assets": assets, "X": Xf,
            "ready": dict((a, st[a]["ready"]) for a in assets),
            "px": dict((a, dict((k, st[a][k]) for k in ("open", "high", "low", "close"))) for a in assets),
            "ev": dict((a, pd.DataFrame({"atr1h": st[a]["atr1h"]}, index=times)) for a in assets),
            "y": y24, "odds": odds24, "birth_idx": int(times.searchsorted(birth))}
    d = tempfile.mkdtemp()
    out = {}
    for run in ("cold", "warm"):
        t = time.time()
        intraday.live_minds(prep, g, cache_path=os.path.join(d, "m.json"), skill_path=os.path.join(d, "s.json"), log=lambda *_: None)
        out[run + "_s"] = round(time.time() - t, 2)
    from engine15 import shadows
    t = time.time()
    for a in assets:                                             # one new session of both swing books
        for name in ("1h", "4h"):
            intraday.run_swing(prep["px"][a], odds24[a], st[a]["atr1h"], dict(CFG, leverage_cap=1.0), n - 1, n,
                               rule=intraday.SWING_RULES[name])
    out["books_one_session_s"] = round(time.time() - t, 3)
    log("  live timing: %s" % out)
    del Xf, prep
    gc.collect()
    return out


# ------------------------------------------------------------------ report
def stats_of(a):
    if not a or not a[0]:
        return None
    n = a[0]
    return {"trades": n, "win_pct": round(100.0 * a[1] / n, 1), "avg_r_gross": round(a[2] / n, 3), "avg_r_net": round(a[3] / n, 3),
            "pf_gross": round(a[4] / a[5], 2) if a[5] > 0 else None, "pf_net": round(a[6] / a[7], 2) if a[7] > 0 else None,
            "avg_pct_net": round(a[8] / n, 4)}


def pool(acc, key_filter):
    tot = [0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    for k, v in acc.items():
        if key_filter(k):
            tot = [x + y for x, y in zip(tot, v)]
    return tot


def fmt(v, pat="%.1f"):
    return "-" if v is None else pat % v


def report(log=print):
    groups = {}
    for g, _assets in CFG["universes"]:
        p = os.path.join(OUT, "intraday_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                groups[g] = json.load(fh)
    if not groups:
        log("no group results yet")
        return None
    markets = [a for gr in groups.values() for a in gr["assets"]]
    out = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "groups_done": list(groups),
           "markets": markets, "variants_tried": len(GRID) * len(intraday.MINDS), "chosen": {}, "variants": {}}
    # ---- choose one variant per mind on the FIRST half, pooled over every market
    for name in intraday.MINDS:
        rows = []
        for vkey in groups[next(iter(groups))]["swing"][name]:
            acc = {}
            for gr in groups.values():
                acc.update(gr["swing"][name].get(vkey, {}))
            h1 = stats_of(pool(acc, lambda k: k.endswith("|all|half1")))
            h2 = stats_of(pool(acc, lambda k: k.endswith("|all|half2")))
            rows.append((vkey, h1, h2, acc))
        out["variants"][name] = [{"variant": v, "half1": h1, "half2": h2} for v, h1, h2, _ in rows]
        elig = [r for r in rows if r[1] and r[1]["trades"] >= 300]
        best = max(elig, key=lambda r: r[1]["avg_r_net"]) if elig else None
        if best is None:                                         # nothing traded enough to choose from
            out.setdefault("not_chosen", {})[name] = (
                "no variant reached 300 first-half trades over all markets (most: %s); the pre-declared rule "
                "(intraday.SWING_RULES) stands" % max((r[1] or {}).get("trades", 0) for r in rows))
            continue
        vkey, h1, h2, acc = best
        cells = {}
        for a in markets:
            cells[a] = {"all": [stats_of(acc.get("%s|all|half%d" % (a, h))) for h in (1, 2)]}
            for s in SESS:
                cells[a][s] = [stats_of(acc.get("%s|s:%s|half%d" % (a, s, h))) for h in (1, 2)]
        regimes = sorted(set(k.split("|")[1][2:] for k in acc if "|r:" in k))
        reg = dict((r, [stats_of(pool(acc, lambda k, r=r, h=h: ("|r:%s|half%d" % (r, h)) in k)) for h in (1, 2)]) for r in regimes)
        out["chosen"][name] = {"variant": vkey, "half1": h1, "half2": h2, "cells": cells, "regimes": reg}
    # ---- where it clears costs: market x session cells positive after costs in BOTH halves (>= 30 trades each)
    for name, ch in out["chosen"].items():
        both = []
        for a, cc in ch["cells"].items():
            for s, (h1, h2) in cc.items():
                if h1 and h2 and h1["trades"] >= 30 and h2["trades"] >= 30 and h1["avg_r_net"] > 0 and h2["avg_r_net"] > 0:
                    both.append("%s %s" % (a, s))
        ch["clears_both_halves"] = both
    out["minds"] = dict((g, gr["minds"]) for g, gr in groups.items())
    out["ev"] = dict((g, gr["ev"]) for g, gr in groups.items())
    out["voice_rating"] = dict((g, gr["voice_rating"]) for g, gr in groups.items())
    out["meta"] = dict((g, {"window": gr["window"], "split": gr["split"], "seconds": gr.get("seconds"), "peak_mb": gr.get("peak_mb")})
                       for g, gr in groups.items())
    with open(os.path.join(OUT, "intraday.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    write_md(out, os.path.join(OUT, "intraday.md"))
    return out


def write_md(out, path):
    L = ["# Workstream M: the intraday mind on history (IN-SAMPLE, not proof)", "",
         "Written by `research/intraday_study.py` on %s. Groups: %s. Paper only. A history read can reject an idea, "
         "never prove one; forward results decide (docs/CHARTER.md). See docs/INTRADAY.md for the plain-English summary." % (
             out["written_utc"], ", ".join(out["groups_done"])), ""]
    for g, m in out["meta"].items():
        L.append("- %s: %s to %s UTC, halves split at %s (%ss, peak %s MB)" % (g, m["window"][0], m["window"][1], m["split"],
                                                                             m["seconds"], m["peak_mb"]))
    L += ["", "## M1: skill per horizon, per market, both halves", "",
          "Hit = direction right on calls graded up or down; edge hit = the same on calls with a 5-point claimed edge; "
          "skill = log-loss gain over the base rate (%). 24h = the main engine's question asked of the same voting voices.", "",
          "| Market | Horizon | Neither % | Skill 1st / 2nd | Hit 1st / 2nd | Edge hit 1st / 2nd | Edge calls 1st / 2nd | |edge| p95, pts |", "|---|---|---|---|---|---|---|---|"]
    for g, minds in out["minds"].items():
        for a in next(iter(minds.values()))["markets"]:
            for name, md in minds.items():
                h1, h2 = md["markets"][a]["half1"], md["markets"][a]["half2"]
                L.append("| %s | %s | %s | %s / %s | %s / %s | %s / %s | %s / %s | %s |" % (
                    a, name, fmt(h2.get("neither_pct")), fmt(h1.get("skill_pct"), "%.2f"), fmt(h2.get("skill_pct"), "%.2f"),
                    fmt(h1.get("hit_pct")), fmt(h2.get("hit_pct")), fmt(h1.get("edge_hit_pct")), fmt(h2.get("edge_hit_pct")),
                    h1.get("edge_calls", 0), h2.get("edge_calls", 0), fmt(h2.get("edge_p95_pts"), "%.1f")))
    L += ["", "### Edge hit rate by session (1st / 2nd half)", "", "| Market | Horizon | " + " | ".join(SESS) + " |",
          "|---|---|" + "---|" * len(SESS)]
    for g, minds in out["minds"].items():
        for a in next(iter(minds.values()))["markets"]:
            for name in ("1h", "4h"):
                ss = minds[name]["markets"][a].get("session", {})
                L.append("| %s | %s | %s |" % (a, name, " | ".join("%s / %s" % (fmt((ss.get(s) or {}).get("half1", {}).get("edge_hit_pct")),
                                                                             fmt((ss.get(s) or {}).get("half2", {}).get("edge_hit_pct")))
                                                                  for s in SESS)))
    L += ["", "### Edge hit rate by regime, 1h and 4h minds (1st / 2nd half, calls in 2nd)", ""]
    for g, minds in out["minds"].items():
        for name in ("1h", "4h"):
            for a, row in minds[name]["markets"].items():
                parts = []
                for rg, v in (row.get("regime") or {}).items():
                    parts.append("%s %s / %s (%s)" % (rg, fmt(v.get("half1", {}).get("edge_hit_pct")), fmt(v.get("half2", {}).get("edge_hit_pct")),
                                                       v.get("half2", {}).get("edge_calls", 0)))
                L.append("- %s %s: %s" % (a, name, "; ".join(parts)))
    L += ["", "### Which voices know the next hours (each fitted alone on the 1st half, scored on the 2nd)", "",
          "Log-loss skill % (mostly knowing WHETHER price will move: the 'neither' class) and the direction hit % on "
          "calls graded up or down (knowing WHICH WAY). Top 6 of each.", ""]
    for g, vr in out["voice_rating"].items():
        for name, r in vr.items():
            L.append("- %s, %s: skill %s; direction %s" % (
                g, name, ", ".join("%s %+.2f" % kv for kv in list(r["skill"].items())[:6]),
                ", ".join("%s %.1f%%" % kv for kv in list(r["direction_hit"].items())[:6])))
    L += ["", "## M2: how often the expected value after costs clears the margin", "",
          "EV = P(win) - P(loss) - round trip / risk, in R, with a 1-barrier stop and target. Share of sessions (%).", "",
          "| Market | Mind | Round trip | Median barrier | Median cost in R | >=0 1st / 2nd | >=0.05 1st / 2nd | >=0.10 1st / 2nd |",
          "|---|---|---|---|---|---|---|---|"]
    for g, evg in out["ev"].items():
        for name, rows in evg.items():
            for a, r in rows.items():
                L.append("| %s | %s | %.3f%% | %.3f%% | %.3f | %s / %s | %s / %s | %s / %s |" % (
                    a, name, r["cost_rt_pct"], r["median_unit_pct"], r["median_cost_r"],
                    *[fmt(r["half%d" % h].get("clears_%.2f_pct" % m), "%.2f") for m in EV_MARGINS for h in (1, 2)]))
    L += ["", "## M3/M4: the swing book (%d variants tried: %d per mind)" % (out["variants_tried"], len(GRID)), "",
          "Variant = stop | target | target R | EV margin. Pooled over every market; R per trade before and after costs.", ""]
    for name, rows in out["variants"].items():
        L += ["### %s mind: every variant" % name, "", "| Variant | Trades 1st | Avg R gross 1st | Avg R net 1st | PF net 1st | Trades 2nd | Avg R gross 2nd | Avg R net 2nd | PF net 2nd |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            h1, h2 = r["half1"] or {}, r["half2"] or {}
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["variant"], h1.get("trades", 0), fmt(h1.get("avg_r_gross"), "%+.3f"), fmt(h1.get("avg_r_net"), "%+.3f"),
                fmt(h1.get("pf_net"), "%.2f"), h2.get("trades", 0), fmt(h2.get("avg_r_gross"), "%+.3f"),
                fmt(h2.get("avg_r_net"), "%+.3f"), fmt(h2.get("pf_net"), "%.2f")))
        L.append("")
    for name, why in (out.get("not_chosen") or {}).items():
        L += ["### %s mind: no variant chosen" % name, "", why[0].upper() + why[1:] + ".", ""]
    for name, ch in out["chosen"].items():
        L += ["### %s mind: chosen on the 1st half: `%s`" % (name, ch["variant"]), "",
              "Pooled: 1st half %s trades, %+.3f R net (%+.3f gross); 2nd half %s trades, %+.3f R net (%+.3f gross)." % (
                  ch["half1"]["trades"], ch["half1"]["avg_r_net"], ch["half1"]["avg_r_gross"],
                  (ch["half2"] or {}).get("trades", 0), (ch["half2"] or {}).get("avg_r_net", 0), (ch["half2"] or {}).get("avg_r_gross", 0)), "",
              "| Market | Session | Trades 1st / 2nd | Win % 1st / 2nd | Avg R gross 1st / 2nd | Avg R net 1st / 2nd | PF net 1st / 2nd | Net % per trade 1st / 2nd |",
              "|---|---|---|---|---|---|---|---|"]
        for a, cc in ch["cells"].items():
            for s in ["all"] + SESS:
                h1, h2 = cc.get(s) or [None, None]
                h1, h2 = h1 or {}, h2 or {}
                L.append("| %s | %s | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s |" % (
                    a, s, h1.get("trades", 0), h2.get("trades", 0), fmt(h1.get("win_pct")), fmt(h2.get("win_pct")),
                    fmt(h1.get("avg_r_gross"), "%+.3f"), fmt(h2.get("avg_r_gross"), "%+.3f"),
                    fmt(h1.get("avg_r_net"), "%+.3f"), fmt(h2.get("avg_r_net"), "%+.3f"),
                    fmt(h1.get("pf_net"), "%.2f"), fmt(h2.get("pf_net"), "%.2f"),
                    fmt(h1.get("avg_pct_net"), "%+.4f"), fmt(h2.get("avg_pct_net"), "%+.4f")))
        L += ["", "By regime (pooled, avg R net 1st / 2nd): " + "; ".join(
            "%s %s / %s" % (r, fmt((v[0] or {}).get("avg_r_net"), "%+.3f"), fmt((v[1] or {}).get("avg_r_net"), "%+.3f"))
            for r, v in ch["regimes"].items()), "",
              "Market x session cells positive after costs in BOTH halves (>= 30 trades each): %s. Picked after looking, "
              "out of %d cells: leads for forward grading, not findings." % (", ".join(ch["clears_both_halves"]) or "none",
                                                                            len(ch["cells"]) * (len(SESS) + 1)), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--chunk-months", type=int, default=12)
    ap.add_argument("--warm-days", type=int, default=300)
    ap.add_argument("--end", default=None, help="ignore bars from this date (tests / quick runs)")
    ap.add_argument("--force", action="store_true", help="run even with less than 2,500 MB free")
    ap.add_argument("--time-live", action="store_true", help="also time intraday.live_minds as the live step runs it (M5)")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    try:                                                         # below-normal priority: the live loop comes first
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass
    if args.group:
        free = free_mb()
        if free is not None and free < MIN_FREE_MB and not args.force:
            print("only %s MB free (need %d): not starting" % (free, MIN_FREE_MB))
            return 2
        assets = dict(CFG["universes"])[args.group]
        print("%s %s: free %s MB" % (args.group, assets, free))
        res = run_group(args.group, assets, args)
        with open(os.path.join(OUT, "intraday_%s.json" % args.group), "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        print("%s done in %ss, peak %s MB" % (args.group, res["seconds"], res["peak_mb"]))
    if args.report:
        out = report()
        if out:
            for name, ch in out["chosen"].items():
                print(name, ch["variant"], ch["half1"], ch["half2"], "both halves:", ch["clears_both_halves"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
