# -*- coding: utf-8 -*-
"""H36, the exit study (charter task B): moving-average trails and break-even after Target 1 on the main
book's OWN entries. Only the exit changes; entries, sizing, fees, the protective stop, flips and the mandate
are the main book's (engine15/shadows.run, the same frame as backtest.run_book). PAPER ONLY. IN-SAMPLE.

    py -3 research/exit_study.py --group fx          one market group (one at a time: memory)
    py -3 research/exit_study.py --report            merge the groups, write research/out/exits/trail_study.md/.json

THE ODDS. Formed as the live step forms them, without touching anything the live loop writes:
  * readings and the feature matrix from the evidence store data/evcache/<group>/<asset> (memory maps,
    opened READ-ONLY; nothing is appended, nothing rebuilt),
  * the voices walked forward weekly from the engine's birth (CFG birth, 2020-01-01) by
    leanprep.walk_forward_cached, the replay's code, with the refits cached in a PRIVATE directory
    (--fits-dir; the live fits directory is never used: that function deletes fits it did not use),
  * trust and the mix as leanprep.prepare_live, with the group's own voting cards and grading horizon.
--learn-days N instead walks only the last N days (the live step uses 240): the registered fallback.

THE BOOKS. main (hold to stop or flip), b_targets, b_trail (the existing shadow rules) and the 15 frozen
H36 variants (research/HYPOTHESES.md), each from $10,000 per market at the first session with odds.

Heavy work shares research/out/heavy_job.lock with other agents (created O_CREAT|O_EXCL with our PID;
a dead holder's lock is taken over; released when the group is done), runs at below-normal priority,
starts only with >= 1,500 MB free and pauses while free memory is under 600 MB.
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

from engine15 import data, evcache, labels, leanprep, model, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "exits")
LOCK = os.path.join(ROOT, "research", "out", "heavy_job.lock")
START = shadows.START_EQUITY
MIN_FREE_START, MIN_FREE_RUN = 1500, 600

# ---- the frozen grid (research/HYPOTHESES.md, H36): 15 variants, all counted
def _v(ma=None, arm="1r", be=False, half=False):
    r = {}
    if ma:
        r.update(ma_trail=ma, ma_arm=arm)
    if be:
        r["be_t1"] = True
    if half:
        r["half_t1"] = True
    return r


VARIANTS = [
    ("be_t1", _v(be=True)),
    ("ema20_15m_1r", _v("15m ema20")), ("ema50_15m_1r", _v("15m ema50")), ("ema20_1h_1r", _v("1h ema20")),
    ("sma20_15m_1r", _v("15m sma20")), ("sma50_15m_1r", _v("15m sma50")), ("sma20_1h_1r", _v("1h sma20")),
    ("ema20_1h_entry", _v("1h ema20", "entry")), ("sma20_1h_entry", _v("1h sma20", "entry")),
    ("ema20_1h_t1", _v("1h ema20", "t1")), ("sma20_1h_t1", _v("1h sma20", "t1")),
    ("be_ema20_1h_1r", _v("1h ema20", be=True)), ("be_sma20_1h_1r", _v("1h sma20", be=True)),
    ("half_ema20_1h_t1", _v("1h ema20", "t1", half=True)), ("half_sma20_1h_t1", _v("1h sma20", "t1", half=True)),
]
BASES = ["main", "b_targets", "b_trail"]
BOOKS = BASES + [k for k, _ in VARIANTS]


def family(name):
    r = dict(VARIANTS).get(name, {})
    m = r.get("ma_trail") or ""
    return "ema" if "ema" in m else "sma" if "sma" in m else None


# =====================================================================================
# housekeeping: memory, priority, the shared lock
# =====================================================================================
class _MS(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_mb():
    m = _MS()
    m.dwLength = ctypes.sizeof(_MS)
    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys / 2 ** 20)
    except Exception:
        return 10 ** 6


def wait_memory(need, log, poll=30):
    while free_mb() < need:
        log("waiting for memory: %d MB free, need %d" % (free_mb(), need))
        time.sleep(poll)


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
    except Exception:
        pass


def pid_alive(pid):
    try:
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))           # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259                # STILL_ACTIVE
    except Exception:
        return True


def acquire(label, log, poll=60):
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "label": label,
                                     "since_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}).encode())
            os.close(fd)
            return
        except FileExistsError:
            try:
                with open(LOCK, encoding="utf-8") as fh:
                    held = json.load(fh)
            except Exception:
                held = {}
            if held.get("pid") and not pid_alive(held["pid"]):
                log("heavy-job lock held by dead pid %s (%s): taking it over" % (held.get("pid"), held.get("label")))
                try:
                    os.remove(LOCK)
                except OSError:
                    pass
                continue
            log("heavy-job lock held by %s: waiting" % held)
            time.sleep(poll)


def release():
    try:
        with open(LOCK, encoding="utf-8") as fh:
            if json.load(fh).get("pid") != os.getpid():
                return
        os.remove(LOCK)
    except Exception:
        pass


# =====================================================================================
# the odds, read-only
# =====================================================================================
def prep_readonly(group, assets, fits_dir, learn_days=None, log=print):
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    ns = set(st.meta["n"] for st in stores.values())
    if len(ns) != 1:
        raise RuntimeError("stores of %s disagree on rows: %s" % (group, ns))
    times = pd.DatetimeIndex(pd.to_datetime(stores[assets[0]].times_ms(), unit="ms", utc=True))
    n = len(times)
    for a in assets[1:]:
        assert np.array_equal(stores[a].times_ms(), stores[assets[0]].times_ms())
    last_open = times[-1]
    birth = CFG["birth"] if not learn_days else str((last_open - pd.Timedelta(days=learn_days)).date())
    cfg = dict(CFG, assets=tuple(assets), birth=birth, voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    for a in assets:
        st = stores[a]
        ev[a] = st.frame(times)
        X[a] = st.X()
        ready[a] = st.ready()
        b = data.load(a).reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    t0 = time.time()
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n,
                                                       fits_dir)
    log("%s: voices walked from %s: %d refits, %d from the private cache (%.0fs, %d MB free)" % (
        group, cfg["birth"], frep["refits"], frep["reused"], time.time() - t0, free_mb()))
    del models
    lo = birth_idx
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    odds = {}
    for a in assets:
        Xa = np.asarray(X[a][lo:n])
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        del Xa
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        del speaks, w
        probs[a] = None
    del probs, trust, X
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds,
            "birth_idx": birth_idx}


# =====================================================================================
# books and numbers
# =====================================================================================
def run_book(name, prep, a, lo, n, aux):
    if name in shadows.CHALLENGERS:
        return shadows.run_challenger(name, prep, a, lo, n, aux=aux)
    cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    inp = shadows.book_inputs(prep, a)
    tgt = aux["targets"]
    return shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                       bias=inp["bias"], guard=inp["guard"], rule=dict(VARIANTS)[name], aux=aux,
                       times_ms=data.to_ms(prep["times"]),
                       row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))


def daily(eq, times, lo, n):
    s = pd.Series(eq[lo:n], index=times[lo:n]).ffill()
    return s.resample("1D").last().ffill()


def sharpe(d):
    r = d.pct_change().dropna()
    return round(float(r.mean() / r.std() * np.sqrt(365)), 2) if len(r) > 10 and r.std() > 0 else None


def max_dd(curve):
    c = np.asarray(curve, float)
    c = c[np.isfinite(c)]
    return round(float((c / np.maximum.accumulate(c) - 1).min()) * 100, 2) if len(c) else None


def trade_stats(tr):
    t = tr
    w, l_ = t.pnl_usd[t.pnl_usd > 0], t.pnl_usd[t.pnl_usd <= 0]
    top6 = float(t.pnl_usd.nlargest(6).sum()) if len(t) else 0.0
    return {"trades": int(len(t)), "win_rate_pct": round(float((t.pnl_usd > 0).mean() * 100), 1) if len(t) else None,
            "avg_win_usd": round(float(w.mean()), 2) if len(w) else None,
            "avg_loss_usd": round(float(l_.mean()), 2) if len(l_) else None,
            "avg_r": round(float(t.r_mult.mean()), 3) if len(t) and t.r_mult.notna().any() else None,
            "avg_hold_bars": round(float((t.i_out - t.i_in).mean()), 1) if len(t) else None,
            "fees_usd": round(float(t.fees_usd.sum()), 2), "closed_pnl_usd": round(float(t.pnl_usd.sum()), 2),
            "top6_usd": round(top6, 2)}


def seg_stats(eq, tr, times, lo, hi, base):
    e = eq[lo:hi]
    e = e[np.isfinite(e)]
    if not len(e):
        return {}
    d = daily(eq, times, lo, hi)
    out = {"pnl_usd": round(float(e[-1] - base), 2), "return_pct": round(float(e[-1] / base - 1) * 100, 2),
           "sharpe": sharpe(pd.concat([pd.Series([base], index=[d.index[0] - pd.Timedelta(days=1)]), d])),
           "max_dd_pct": max_dd(np.concatenate([[base], e]))}
    out.update(trade_stats(tr))
    out["top6_share_pct"] = round(100.0 * out["top6_usd"] / out["pnl_usd"], 1) if out["pnl_usd"] > 0 else None
    return out


def run_group(g, assets, args, log=print):
    t0 = time.time()
    fits = os.path.join(args.fits_dir, g)
    prep = prep_readonly(g, assets, fits, args.learn_days, log=log)
    times = prep["times"]
    n = len(times)
    mid_ts = pd.Timestamp(args.mid, tz="UTC")
    out = {"group": g, "birth": prep["cfg"]["birth"], "assets": {}, "learn_days": args.learn_days}
    curves = {}
    for a in assets:
        wait_memory(MIN_FREE_RUN, log)
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        mid = int(times.searchsorted(mid_ts))
        mid = min(max(mid, lo + 1), n - 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        missing = [k for k in ("15m ema20", "15m ema50", "15m sma20", "15m sma50", "1h ema20", "1h sma20")
                   if not np.isfinite(aux["ma"][k][lo:]).any()]
        c, o = prep["px"][a]["close"], prep["px"][a]["open"]
        fee = shadows.asset_cfg(a, prep["cfg"])["cost_side"]
        res = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid])[:16],
               "missing_ma": missing, "fee_side": fee,
               "buy_hold_return_pct": round(float(c[n - 1] / o[lo] * (1 - 2 * fee) - 1) * 100, 2), "books": {}}
        for name in BOOKS:
            b = run_book(name, prep, a, lo, n, aux)
            eq, tr = b["equity"], b["trades"]
            base_mid = eq[mid - 1] if np.isfinite(eq[mid - 1]) else START
            res["books"][name] = {"all": seg_stats(eq, tr, times, lo, n, START),
                                  "first_half": seg_stats(eq, tr[tr.i_out < mid], times, lo, mid, START),
                                  "second_half": seg_stats(eq, tr[tr.i_out >= mid], times, mid, n, base_mid),
                                  "exits": dict((str(k), int(v)) for k, v in tr.why_out.value_counts().items()),
                                  "open_at_end": {1: "LONG", -1: "SHORT"}.get(b["state"]["pos"], "FLAT")}
            curves[name] = daily(eq, times, lo, n)
        out["assets"][a] = res
        out.setdefault("curves", {})[a] = dict((k, {"t": [str(x)[:10] for x in v.index], "eq": [round(float(x), 2) for x in v.values]})
                                               for k, v in curves.items())
        curves = {}
        m = res["books"]["main"]["all"]
        log("%s %s: %s .. %s, main %+.0f (%d trades), buy-hold %+.1f%%, missing MAs %s (%.0fs, %d MB free)" % (
            g, a, res["window"][0], res["window"][1], m.get("pnl_usd", 0), m.get("trades", 0),
            res["buy_hold_return_pct"], missing or "none", time.time() - t0, free_mb()))
        gc.collect()
    del prep
    gc.collect()
    return out


# =====================================================================================
# the report
# =====================================================================================
def pooled(groups, mid, drop=()):
    frames = {}
    for g in groups.values():
        for a, cv in g["curves"].items():
            if a in drop:
                continue
            for name, s in cv.items():
                frames[(a, name)] = pd.Series(s["eq"], index=pd.to_datetime(s["t"]))
    frame = pd.concat(frames, axis=1).sort_index().ffill().fillna(START)
    assets = sorted(set(k[0] for k in frame.columns))
    mid_t = pd.Timestamp(mid)
    out = {}
    for name in BOOKS:
        tot = frame[[(a, name) for a in assets]].sum(axis=1)
        k = len(assets)
        base = START * k
        first = tot[tot.index < mid_t]
        b_mid = float(first.iloc[-1]) if len(first) else base
        out[name] = {"assets": k, "pnl_usd": round(float(tot.iloc[-1] - base), 2),
                     "return_pct": round(float(tot.iloc[-1] / base - 1) * 100, 2),
                     "sharpe": sharpe(pd.concat([pd.Series([base], index=[tot.index[0] - pd.Timedelta(days=1)]), tot])),
                     "max_dd_pct": max_dd(np.concatenate([[base], tot.values])),
                     "first_half_usd": round(b_mid - base, 2), "second_half_usd": round(float(tot.iloc[-1]) - b_mid, 2)}
    return out


def report(args, log=print):
    groups = {}
    for g, _assets in CFG["universes"]:
        p = os.path.join(OUT, "trail_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                groups[g] = json.load(fh)
    if not groups:
        raise SystemExit("no group results in %s" % OUT)
    pool = pooled(groups, args.mid)
    pool_x = pooled(groups, args.mid, drop=("ETHUSDT",))       # ETH's compounding dwarfs every other market
    per = dict((a, r) for g in groups.values() for a, r in g["assets"].items())
    main = pool["main"]
    summary = {}
    for name in BOOKS:
        p = pool[name]
        beats = [a for a, r in per.items() if r["books"][name]["all"].get("pnl_usd", 0) > r["books"]["main"]["all"].get("pnl_usd", 0)]
        g1, g2 = p["first_half_usd"] - main["first_half_usd"], p["second_half_usd"] - main["second_half_usd"]
        trades = sum(r["books"][name]["all"].get("trades", 0) for r in per.values())
        top6 = sum(r["books"][name]["all"].get("top6_usd", 0) for r in per.values())
        wins = [r["books"][name]["all"] for r in per.values()]
        gaps_pct = [r["books"][name]["all"].get("return_pct", 0) - r["books"]["main"]["all"].get("return_pct", 0)
                    for r in per.values()]
        summary[name] = dict(p, vs_main_usd=round(p["pnl_usd"] - main["pnl_usd"], 2),
                             ex_eth_pnl_usd=pool_x[name]["pnl_usd"],
                             ex_eth_vs_main_usd=round(pool_x[name]["pnl_usd"] - pool_x["main"]["pnl_usd"], 2),
                             ex_eth_sharpe=pool_x[name]["sharpe"], ex_eth_max_dd_pct=pool_x[name]["max_dd_pct"],
                             median_market_gap_pct=round(float(np.median(gaps_pct)), 2),
                             vs_b_targets_usd=round(p["pnl_usd"] - pool["b_targets"]["pnl_usd"], 2),
                             vs_b_trail_usd=round(p["pnl_usd"] - pool["b_trail"]["pnl_usd"], 2),
                             gap_first_half=round(g1, 2), gap_second_half=round(g2, 2), worse_half_gap=round(min(g1, g2), 2),
                             markets_beating_main=len(beats), trades=trades,
                             fees_usd=round(sum(w.get("fees_usd", 0) for w in wins), 2),
                             top6_sum_usd=round(top6, 2),
                             better_than_hold=bool(name not in BASES and g1 > 0 and g2 > 0 and len(beats) >= 5 and
                                                   (p["max_dd_pct"] or 0) >= (main["max_dd_pct"] or 0)))
    pick, pick_amended = {"be": "be_t1"}, {"be": "be_t1"}
    for fam in ("ema", "sma"):
        cands = [k for k, _ in VARIANTS if family(k) == fam]
        pick[fam] = max(cands, key=lambda k: (summary[k]["worse_half_gap"], summary[k]["pnl_usd"]))
        # amendment (13 Nov 2026, after the results, disclosed in HYPOTHESES.md): the registered dollar worse-half
        # rule is degenerate under compounding (a variant that has lost ~99% by the midpoint cannot lose many
        # dollars after it, so it "wins" the worse half). The forward books use whole-window pooled net P&L.
        pick_amended[fam] = max(cands, key=lambda k: (summary[k]["pnl_usd"], summary[k]["worse_half_gap"]))
    names = [k for k, _ in VARIANTS]
    ranking = sorted(names, key=lambda k: (-summary[k]["pnl_usd"], -summary[k]["worse_half_gap"]))
    robust = sorted(names, key=lambda k: (-summary[k]["worse_half_gap"], -summary[k]["pnl_usd"]))
    res = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "mid": args.mid,
           "ranking_by_pnl": ranking, "ranking_by_worse_half_gap": robust,
           "groups": dict((g, {"birth": v["birth"], "learn_days": v.get("learn_days"),
                               "assets": v["assets"]}) for g, v in groups.items()),
           "pooled": summary, "picked_registered_rule": pick, "picked_for_shadows": pick_amended, "variants": dict(VARIANTS), "n_variants": len(VARIANTS)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "trail_study.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    write_md(res, os.path.join(OUT, "trail_study.md"))
    for name in BOOKS:
        s = summary[name]
        log("%-18s P&L %+10.0f vs main %+9.0f  halves gap %+8.0f / %+8.0f  DD %6.2f%%  Sharpe %s  trades %d  beats %d/8" % (
            name, s["pnl_usd"], s["vs_main_usd"], s["gap_first_half"], s["gap_second_half"], s["max_dd_pct"],
            s["sharpe"], s["trades"], s["markets_beating_main"]))
    log("picked (registered rule): %s; forward books (amended rule): %s" % (pick, pick_amended))


V52_NOTES = [
    "## If the owner switches the main book (v5.2): what it needs", "",
    "Not done here; the main book is unchanged (v5.1). The rule lives once, in `engine15/exits.py` (pure per-bar "
    "functions: `ma_trail_step`, `be_stop`, `reached`, and `trail_from_history` for open trades); `shadows.run` calls "
    "it and `backtest.run_book` can call the same functions.", "",
    "1. **Config** (`engine15/config.py`): one key, e.g. `\"exit_rule\": {\"be_t1\": True}` (or "
    "`{\"ma_trail\": \"1h sma20\", \"ma_arm\": \"t1\"}`, the same dicts as the H36 grid), and `version` -> "
    "`think15-v5.2`, said in the journal's next entry. An empty dict = v5.1.",
    "2. **`backtest.run_book`**: know Target 1 at entry (today `live.py` computes `plan_targets` after the book "
    "runs, from the readings row of the decision bar; move it into the book via a `row_of(k)` or a precomputed "
    "target array, as `shadows.run` does); per bar after the stop check: `exits.reached` -> `t1_hit`, `exits.be_stop`; "
    "at the close `exits.ma_trail_step` on the MA column (`ev[\"ma_1h_sma20_px\"]` etc.); a trail exit is a pending "
    "order (`TRAIL_MA`, target 0) through the same next-open fill and late-feed delay; idle as after a stop. New state "
    "keys: `stop0`, `t1`, `t1_hit`, `ma_on`, `trail_px` (restored on resume). The stop word after break-even: `STOP_BE` "
    "(journal.py line ~127 looks for `STOP` only: widen it).",
    "3. **Open trades at the switch** (state migration, closed bars only): for each open main-book trade call "
    "`exits.trail_from_history(pos, entry, stop0=book[\"stop\"] (v5.1 stops never move, so the live stop is the entry "
    "stop), t1=book[\"target_1\"], arm, high, low, close, ma, i_in=times.searchsorted(t_in_ms), i_last=last closed "
    "row, be_t1=...)`. Set `stop`, `t1_hit`, `ma_on`, `trail_px` from it. If it returns an `exit_row`, the rule would "
    "already have closed the trade: close it at the next open and journal it as a switch exit; never back-date a fill.",
    "4. **Shadows**: add `main_v51_hold` (rule `{}`, title \"Main v5.1: hold to stop or flip\") so the old rule keeps "
    "running forward; give `main` (the fresh copy of the main rule) the v5.2 rule (`run_challenger` passes the spec's "
    "rule to `shadows.run`). If v5.2 = `be_t1`, `b_be_t1` duplicates `main` and can be retired. New books join flat "
    "and the scoreboard compares them with main over their own time (`late_starts`).",
    "5. **Tests to update**: `tests/test_shadows.py::test_run_book_is_unchanged_on_a_fixed_slice` (PINNED: pin v5.1 with "
    "an empty exit rule and add a v5.2 pin), `test_shadow_engine_without_rules_is_run_book_exactly` (compare "
    "`run_book` under the exit rule with `shadows.run(rule=exit_rule)`, both ways across a resume cut), "
    "`tests/test_engine.py` book tests, `tests/test_lean.py` (lean vs full prep through `run_book`), and keep "
    "`test_trail_from_history_matches_the_book` and `test_evidence_never_reads_the_future` green.", ""]


def recommendation(res):
    """The ranked answer for the owner's v5.2 question: the single best variant for the main book."""
    S = res["pooled"]
    m = S["main"]
    rk, rb = res["ranking_by_pnl"], res["ranking_by_worse_half_gap"]
    L = ["## Recommendation for the main book (v5.2 question)", "",
         "Ranked by pooled net P&L over all eight markets (the registered robust ranking, by the worse half's gap to "
         "main, is shown beside it). Main v5.1 (hold to stop or flip): $%s, Sharpe %s, max DD %.2f%%." % (
             _f(m["pnl_usd"]), _f(m["sharpe"], "%.2f"), m["max_dd_pct"]), "",
         "| Rank | Variant | Net P&L | vs main | Sharpe (main %s) | Max DD (main %.2f%%) | 1st half vs main | 2nd half vs main | "
         "Markets beating main | Rank by worse half |" % (_f(m["sharpe"], "%.2f"), m["max_dd_pct"]),
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, k in enumerate(rk, 1):
        s = S[k]
        L.append("| %d | `%s` | $%s | $%s | %s | %.2f%% | $%s | $%s | %d/8 | %d |" % (
            i, k, _f(s["pnl_usd"]), _f(s["vs_main_usd"]), _f(s["sharpe"], "%.2f"), s["max_dd_pct"],
            _f(s["gap_first_half"]), _f(s["gap_second_half"]), s["markets_beating_main"], rb.index(k) + 1))
    best, second = rk[0], rk[1]
    L.append("")
    lose = [k for k in rk if S[k]["vs_main_usd"] <= 0]
    if len(lose) == len(rk):
        L.append("**Every one of the %d trail / break-even variants made less than holding.** The best, `%s`, trails "
                 "main by $%s (%s of main's net); the worst, `%s`, by $%s." % (
                     len(rk), best, _f(-S[best]["vs_main_usd"], "%.0f"),
                     "%.0f%%" % (100.0 * -S[best]["vs_main_usd"] / m["pnl_usd"]) if m["pnl_usd"] > 0 else "-",
                     rk[-1], _f(-S[rk[-1]]["vs_main_usd"], "%.0f")))
    else:
        L.append("%d of %d variants made more than holding over the whole window; %d passed the registered 'better "
                 "than hold' test (both halves, 5 of 8 markets, drawdown no worse)." % (
                     len(rk) - len(lose), len(rk), sum(1 for k in rk if S[k]["better_than_hold"])))
    L += ["", "- **Best for the main book: `%s`** (%s): net $%s vs main $%s, Sharpe %s vs %s, max DD %.2f%% vs %.2f%%, "
          "halves vs main $%s / $%s, ahead of main in %d of 8 markets." % (
              best, json.dumps(res["variants"][best]), _f(S[best]["pnl_usd"]), _f(m["pnl_usd"]),
              _f(S[best]["sharpe"], "%.2f"), _f(m["sharpe"], "%.2f"), S[best]["max_dd_pct"], m["max_dd_pct"],
              _f(S[best]["gap_first_half"]), _f(S[best]["gap_second_half"]), S[best]["markets_beating_main"]),
          "- **Runner-up: `%s`** (%s): net $%s, Sharpe %s, max DD %.2f%%, halves vs main $%s / $%s." % (
              second, json.dumps(res["variants"][second]), _f(S[second]["pnl_usd"]), _f(S[second]["sharpe"], "%.2f"),
              S[second]["max_dd_pct"], _f(S[second]["gap_first_half"]), _f(S[second]["gap_second_half"])),
          "- Robust ranking (worse half's gap to main) puts `%s` first and `%s` second (dollar halves compound: see "
          "the note on the forward picks above)." % (rb[0], rb[1]),
          "- Without ETHUSDT (whose compounding dominates the dollars): `%s` vs main $%s, Sharpe %s vs %s, max DD %.1f%% "
          "vs %.1f%%; `%s` vs main $%s." % (
              best, _f(S[best]["ex_eth_vs_main_usd"]), _f(S[best]["ex_eth_sharpe"], "%.2f"), _f(m["ex_eth_sharpe"], "%.2f"),
              S[best]["ex_eth_max_dd_pct"], m["ex_eth_max_dd_pct"], second, _f(S[second]["ex_eth_vs_main_usd"])), "",
          "**Plainly:** on this history no exit tried here beats holding to the stop or the flip. The main book wins "
          "about one trade in five and its winners are four to six times its losers; its six largest trades per market "
          "add up to more than its whole net. Every MA trail cut those winners, re-entered (often by the mandate) and "
          "was stopped, turning the pooled profit into a loss. Break-even after Target 1 is the least harmful and the "
          "only candidate if the owner still wants a v5.2 profit plan; the cost on this history is real.", ""]
    return L


def _f(v, pat="%+.0f"):
    return "-" if v is None else pat % v


def write_md(res, path):
    S = res["pooled"]
    groups = res["groups"]
    per = dict((a, r) for g in groups.values() for a, r in g["assets"].items())
    births = sorted(set(g["birth"] for g in groups.values()))
    L = ["# H36: moving-average trails and break-even on the main book's own entries (IN-SAMPLE, not proof)", "",
         "Written by `research/exit_study.py` on %s. Every book takes the main book's entries (v5.1 odds as the live "
         "step forms them, voices walked forward weekly from %s), sizing, fees, protective stop, flips and mandate; "
         "only the exit differs. $10,000 per market, %d markets. Halves split at %s. Paper only." % (
             res["written_utc"], " / ".join(births), len(per), res["mid"]), "",
         "**Read this plainly:** history the engine's authors have lived through, %d exit variants tried (plus "
         "b_targets and b_trail), eight markets that partly move together. A history read can reject an idea, "
         "never prove one. Nothing here changes the main book; only the owner can." % res["n_variants"], "",
         "## All markets together", "",
         "| Book | Net P&L | Return | vs main | vs b_targets | vs b_trail | Sharpe | Max DD | 1st half vs main | "
         "2nd half vs main | Markets beating main | Median market gap (return pts) | Without ETH: vs main / Sharpe / DD | "
         "Trades | Fees | Top-6 trades $ | Better than hold? |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in BOOKS:
        s = S[name]
        L.append("| `%s` | $%s | %+.2f%% | $%s | $%s | $%s | %s | %.2f%% | $%s | $%s | %d/%d | %+.1f | $%s / %s / %.1f%% | %d | $%.0f | $%s | %s |" % (
            name, _f(s["pnl_usd"]), s["return_pct"], _f(s["vs_main_usd"]), _f(s["vs_b_targets_usd"]),
            _f(s["vs_b_trail_usd"]), _f(s["sharpe"], "%.2f"), s["max_dd_pct"], _f(s["gap_first_half"]),
            _f(s["gap_second_half"]), s["markets_beating_main"], s["assets"], s["median_market_gap_pct"],
            _f(s["ex_eth_vs_main_usd"]), _f(s["ex_eth_sharpe"], "%.2f"), s["ex_eth_max_dd_pct"], s["trades"], s["fees_usd"],
            _f(s["top6_sum_usd"]), "-" if name in BASES else ("yes" if s["better_than_hold"] else "no")))
    L += ["", "Pooled curves: the markets' daily marked equity summed (a market not yet trading counts at $10,000). "
          "Sharpe on daily returns, sqrt(365). Top-6 trades $: the six largest closed trades of each market, summed. "
          "'Better than hold' (registered): above main in both halves, in at least 5 of 8 markets, and drawdown no worse.", "",
          "Dollar halves compound: ETHUSDT's main book alone made $%s of the pooled $%s, so pooled dollar gaps are "
          "mostly ETH; the 'Without ETH' and 'Median market gap' columns show the rest." % (
              _f(per["ETHUSDT"]["books"]["main"]["all"]["pnl_usd"]) if "ETHUSDT" in per else "-", _f(S["main"]["pnl_usd"])), "",
          "Forward shadow books. The registered rule (best worse-half dollar gap to main) picks %s: it is degenerate "
          "under compounding (the from-entry trails lost ~99%% by the midpoint, so they had no dollars left to lose in "
          "the second half and 'won' the worse half while being the worst variants). Amended after the results, "
          "disclosed in research/HYPOTHESES.md: whole-window pooled net P&L within each family, which picks %s." % (
              ", ".join("%s = `%s`" % kv for kv in res["picked_registered_rule"].items()),
              ", ".join("%s = `%s`" % kv for kv in res["picked_for_shadows"].items())), ""]
    L += ["## Per market (whole window)", ""]
    for a, r in per.items():
        mn = r["books"]["main"]["all"]
        L += ["### %s: %s to %s UTC, buy and hold %+.2f%%, fee %.3f%% a side%s" % (
            a, r["window"][0], r["window"][1], r["buy_hold_return_pct"], 100 * r["fee_side"],
            "; MISSING averages: %s" % r["missing_ma"] if r["missing_ma"] else ""), "",
              "Main book: top 6 trades $%s of $%s net (%s%%)." % (_f(mn.get("top6_usd")), _f(mn.get("pnl_usd")),
                                                                 _f(mn.get("top6_share_pct"), "%.0f")), "",
              "| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | "
              "Top-6 share | 1st half | 2nd half | Exits |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for name in BOOKS:
            b = r["books"][name]
            s, h1, h2 = b["all"], b["first_half"], b["second_half"]
            ex = ", ".join("%s %d" % kv for kv in sorted(b["exits"].items(), key=lambda kv: -kv[1])[:4])
            L.append("| `%s` | $%s | $%s | %s%% | %s | %s%% | %s | %s%% | $%s | $%s | %s | %s | $%s | $%s | %s |" % (
                name, _f(s.get("pnl_usd")), _f(s.get("pnl_usd", 0) - mn.get("pnl_usd", 0)), _f(s.get("return_pct"), "%+.1f"),
                _f(s.get("sharpe"), "%.2f"), _f(s.get("max_dd_pct"), "%.1f"), s.get("trades"),
                _f(s.get("win_rate_pct"), "%.0f"), _f(s.get("avg_win_usd")), _f(s.get("avg_loss_usd")),
                _f(s.get("avg_hold_bars"), "%.0f"), _f(s.get("top6_share_pct"), "%.0f%%"),
                _f(h1.get("pnl_usd")), _f(h2.get("pnl_usd")), ex))
        L.append("")
    L += recommendation(res)
    L += V52_NOTES
    L += ["## The variants (frozen in research/HYPOTHESES.md, H36)", ""]
    for k, v in res["variants"].items():
        L.append("- `%s`: %s" % (k, json.dumps(v)))
    L += ["", "Conventions: MA trail levels are read at the 15m close from bars closed by then (1h averages: the last "
          "closed 1h bar), ratcheted so they never loosen; a close beyond the level exits at the next open; the "
          "protective stop stays live inside every bar and comes first; break-even moves the stop to entry from the "
          "bar after Target 1 trades; half at Target 1 fills at the target. Fees per side as live.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--learn-days", type=int, default=None)
    ap.add_argument("--mid", default="2023-06-08")
    ap.add_argument("--fits-dir", default=os.path.join(OUT, "fits"))
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.report:
        report(args, log)
        return
    below_normal()
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    todo = [args.group] if args.group else list(groups)
    for g in todo:
        acquire("exit_study %s (H36)" % g, log)
        try:
            wait_memory(MIN_FREE_START, log)
            r = run_group(g, groups[g], args, log)
            with open(os.path.join(OUT, "trail_%s.json" % g), "w", encoding="utf-8") as fh:
                json.dump(r, fh)
        finally:
            release()
        gc.collect()


if __name__ == "__main__":
    main()
