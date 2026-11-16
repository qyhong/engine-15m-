# -*- coding: utf-8 -*-
"""H48 FX and session timing. PAPER RESEARCH ONLY.

Registered before any code or outcome: research/HYPOTHESES.md H48 (16 Nov 2026, 05:55 UTC). In short:
  * A1/A2: H46's daily-level break (prior UTC day / previous 96 bars, first 15m close beyond per direction per day) on
    FX only (USDJPY from the engine files, USDSGD from the read-only Kronos store), outcome +0.5 vs -0.5 daily ATR from
    the next open within 72 h (confluence_study.outcome, unchanged); trade stop/target 0.5 daily ATR, 72 h;
  * B1-B3: session ranges (Asia 00:00-07:00 UTC into the London window 07:00-10:00; pre-NY 00:00-13:30 and London
    07:00-13:30 into the NY window 13:30-16:00) on USDJPY, USDSGD, XAUUSD, XAGUSD, WTI, BRENT; B4/B5: the index
    opening range (first 30 / 60 minutes of the NYSE cash session) on SPX and NDX (Kronos CFD, cash hours only);
    outcome +0.5 vs -0.5 daily ATR within the same UTC day (0.25 daily ATR secondary, descriptive);
  * 33 tests per half (each variant's pooled cell + one per market), Bonferroni 0.05/33; pass bar: >= 55% both halves,
    >= 200 resolved per half, p < 1.52e-3 both halves, net > 0 after costs in the second half pooled and in a majority
    of the variant's markets;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market. Reads data/*.csv and C:\\tmp\\kronos\\data\\markets\\{USDSGD,NDX}\\15m.csv.gz (read only, via
pandas; nothing is written there). Writes research/out/session_break/ only.

    py -3 research/session_break_study.py            (run, write study.json + study.md, then print the live scan)
    py -3 research/session_break_study.py --report   (rewrite study.md from study.json)
    py -3 research/session_break_study.py --scan     (the live scan only: latest closed bars, paper / untested)
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, extdata, playbook as pb  # noqa: E402
from engine15.sources import adr  # noqa: E402
from engine15.rl import resources  # noqa: E402

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402
import confluence_study as cs  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 05:55 UTC"
OUT = os.path.join(ROOT, "research", "out", "session_break")
KRONOS = os.environ.get("ENGINE15_MARKETS", r"C:\tmp\kronos\data\markets")      # READ ONLY
KRONOS_ASSETS = ("USDSGD", "NDX")
FEE_EXTRA = {"USDSGD": 0.00015, "NDX": 0.0002}
NEED_MB = 1500
BAR_MS, DAY_MS, HOUR_MS = pb.BAR_MS, 86400000, 3600000
HOLD_MS = 3 * DAY_MS
X_MAIN, X_SEC = 0.5, 0.25
LONDON, NY = extdata.LONDON, extdata.NY

FX = ("USDJPY", "USDSGD")
SIX = ("USDJPY", "USDSGD", "XAUUSD", "XAGUSD", "WTI", "BRENT")
IDX = ("SPX", "NDX")
MARKETS = ("USDJPY", "USDSGD", "XAUUSD", "XAGUSD", "WTI", "BRENT", "SPX", "NDX")

VARIANTS = {
    "A1": {"kind": "daily", "level": "pday", "markets": FX},
    "A2": {"kind": "daily", "level": "roll24", "markets": FX},
    "B1": {"kind": "clock", "range": (0, 420), "window": (420, 600), "need": 14, "markets": SIX},
    "B2": {"kind": "clock", "range": (0, 810), "window": (810, 960), "need": 27, "markets": SIX},
    "B3": {"kind": "clock", "range": (420, 810), "window": (810, 960), "need": 13, "markets": SIX},
    "B4": {"kind": "or", "range": (0, 30), "window": (30, 150), "need": 2, "markets": IDX},
    "B5": {"kind": "or", "range": (0, 60), "window": (60, 150), "need": 4, "markets": IDX},
}
ORDER = list(VARIANTS)
N_TESTS = sum(1 + len(v["markets"]) for v in VARIANTS.values())       # 33
ALPHA = 0.05 / N_TESTS
PASS_HIT, MIN_RESOLVED = 55.0, 200
LOCAL_CHECK = ("B1", "B2", "B3")                                       # recomputed on London wall-clock (descriptive)


def vdesc(v):
    var = VARIANTS[v]
    if var["kind"] == "daily":
        return {"pday": "first 15m close beyond the prior UTC day's high/low",
                "roll24": "first 15m close beyond the previous 96 bars' high/low"}[var["level"]] + "; 72 h"
    if var["kind"] == "or":
        return "opening range = first %d min of the NYSE cash session, broken by a close up to open + 2 h 30; rest of the session" % var["range"][1]
    hm = lambda m: "%02d:%02d" % divmod(m, 60)  # noqa: E731
    return "range %s-%s UTC broken by the first close in %s-%s UTC; rest of the UTC day" % (
        hm(var["range"][0]), hm(var["range"][1]), hm(var["window"][0]), hm(var["window"][1]))


def fee_of(asset):
    return FEE_EXTRA.get(asset, pb.fee_side(asset))


# ---------------------------------------------------------------- data
def load_kronos(asset, dev=True):
    """The Kronos store's 15m bars (read only). NDX: NYSE cash session only (the engine's SPX filter)."""
    d = pd.read_csv(os.path.join(KRONOS, asset, "15m.csv.gz"))
    d.index = pd.to_datetime(d.pop("ts_ms"), unit="ms", utc=True)
    d.index.name = "open_time"
    if dev:
        d = d[d.index < pd.Timestamp(SEAL, tz="UTC")]
    if asset == "NDX":
        d = d[extdata.open_mask("SPX", d.index)]
    d["taker_buy"] = np.nan
    return d[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)


def load_market(asset, dev=True):
    if asset in KRONOS_ASSETS:
        return load_kronos(asset, dev)
    return rb.load_dev(asset) if dev else data.load(asset)


# ---------------------------------------------------------------- the session events (truncation-tested)
def _local_minutes(idx, zone):
    loc = extdata._local(idx, zone)
    mins = np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
    dkey = np.asarray(data.to_ms(loc.normalize().tz_localize("UTC"))) // DAY_MS
    return mins.astype(int), dkey.astype(np.int64)


def clock(R, var, tz=None):
    """-> (mins, dkey): the minute on the variant's clock and its day key (mins -1 = no session day).
    clock: UTC minute of the day (or the zone's wall clock); or: minutes since the cash session's first bar, only on
    days whose first bar opens at 09:30 New York."""
    ms = R["ms"]
    if var["kind"] == "or":
        day = ms // DAY_MS
        first = pd.Series(ms).groupby(day).transform("min").values
        fm, _ = _local_minutes(pd.to_datetime(first, unit="ms", utc=True), NY)
        mins = np.where(fm == 570, (ms - first) // 60000, -1).astype(int)
        return mins, day
    if tz is None:
        return ((ms % DAY_MS) // 60000).astype(int), ms // DAY_MS
    return _local_minutes(R["index"], tz)


def session_events(R, var, tz=None):
    """-> (dirs, rhi, rlo, cnt): dirs +1 / -1 on the FIRST close above / below the session range inside the event
    window of its day (per direction), else 0. rhi / rlo / cnt = the range's high / low / bar count as known at each
    bar's close (cumulative over the day's range bars so far, so nothing after the bar is read)."""
    mins, dkey = clock(R, var, tz)
    r0, r1 = var["range"]
    w0, w1 = var["window"]
    in_r = (mins >= r0) & (mins < r1)
    in_w = (mins >= w0) & (mins < w1)
    g = pd.DataFrame({"h": np.where(in_r, R["h"], -np.inf), "l": np.where(in_r, R["l"], np.inf),
                      "k": in_r.astype(int)}).groupby(dkey)
    rhi, rlo, cnt = g["h"].cummax().values, g["l"].cummin().values, g["k"].cumsum().values
    ok = in_w & (cnt >= var["need"]) & np.isfinite(rhi) & np.isfinite(rlo)
    c = R["c"]
    up, dn = ok & (c > rhi), ok & (c < rlo)
    cu = pd.Series(up.astype(int)).groupby(dkey).cumsum().values
    cd = pd.Series(dn.astype(int)).groupby(dkey).cumsum().values
    dirs = np.where(up & (cu == 1), 1, np.where(dn & (cd == 1), -1, 0)).astype(int)
    return dirs, np.where(np.isfinite(rhi), rhi, np.nan), np.where(np.isfinite(rlo), rlo, np.nan), cnt


def event_dirs(R, var, tz=None):
    if var["kind"] == "daily":
        return db.daily_breaks(R, var["level"], False)
    return session_events(R, var, tz)[0]


def event_key(R, var, tz=None):
    """Rows, sides, range values and daily ATR of every event (for the truncation check)."""
    if var["kind"] == "daily":
        d = event_dirs(R, var)
        hi, lo = (R["pdh"], R["pdl"]) if var["level"] == "pday" else (R["box_hi"], R["box_lo"])
    else:
        d, hi, lo, _ = session_events(R, var, tz)
    return [(int(i), int(d[i]), db._r9(float(hi[i])), db._r9(float(lo[i])), db._r9(float(R["datr"][i])))
            for i in np.flatnonzero(d != 0)]


# ---------------------------------------------------------------- outcome and the trade
def outcome_window(R, i, s, D, x_end, X=X_MAIN, time_exit="close"):
    """+X*D before -X*D from the next open, over bars e .. x_end-1 (a bar touching both = miss). time_exit 'close' =
    out at the close of bar x_end-1 (the day's last bar; only if a later bar is on file, else OPEN); 'open' = out at
    the open of bar x_end (H46's 72 h rule). -> dict or None if the entry bar is not in the break's UTC day."""
    n, o, h, l, c, ms = R["n"], R["o"], R["h"], R["l"], R["c"], R["ms"]
    day = ms // DAY_MS
    e = i + 1
    if e >= n or day[e] != day[i]:
        return None
    en = float(o[e])
    stop, tgt = en - s * X * D, en + s * X * D
    H, L, O = h[e:x_end], l[e:x_end], o[e:x_end]
    if s > 0:
        adv, fav = L <= stop, H >= tgt
    else:
        adv, fav = H >= stop, L <= tgt
    ja = int(np.argmax(adv)) if adv.any() else None
    jf = int(np.argmax(fav)) if fav.any() else None
    r = {"e": e, "entry": en, "stop": stop, "target": tgt, "ambiguous": False}
    if ja is None and jf is None:
        r["hit"] = None
        if x_end < n:
            if time_exit == "open":
                r.update(why="TIME", exit=float(o[x_end]), exit_bar=x_end, busy=x_end - 1, exit_ms=int(ms[x_end]))
            else:
                r.update(why="TIME", exit=float(c[x_end - 1]), exit_bar=x_end - 1, busy=x_end - 1,
                         exit_ms=int(ms[x_end - 1]) + BAR_MS)
        else:
            r.update(why="OPEN", exit=None, exit_bar=None, busy=None, exit_ms=None)
        return r
    if jf is None or (ja is not None and ja <= jf):
        j = ja
        r["hit"], r["ambiguous"] = 0, bool(jf is not None and ja == jf)
        px = float(O[j]) if s * (O[j] - stop) <= 0 else stop
        r.update(why="STOP", exit=px)
    else:
        j = jf
        r["hit"] = 1
        px = float(O[j]) if s * (O[j] - tgt) >= 0 else tgt
        r.update(why="TARGET", exit=px)
    r.update(exit_bar=e + j, busy=e + j - 1, exit_ms=int(ms[e + j]))
    return r


def x_end_of(R, var, i):
    ms = R["ms"]
    if var["kind"] == "daily":
        return int(np.searchsorted(ms, ms[i + 1] + HOLD_MS, side="left"))
    day = ms // DAY_MS
    return int(np.searchsorted(day, day[i], side="right"))


def outcome(R, var, i, s, D, X=X_MAIN):
    if var["kind"] == "daily" and X == X_MAIN:
        if i + 1 >= R["n"]:
            return None
        r = cs.outcome(R, i, s, D)                     # H46's, unchanged
        if r is None:
            return r
        xb = r.get("exit_bar")
        r["busy"] = None if xb is None else xb - 1
        r["exit_ms"] = None if xb is None else int(R["ms"][xb])
        return r
    if i + 1 >= R["n"]:
        return None
    return outcome_window(R, i, s, D, x_end_of(R, var, i), X, "open" if var["kind"] == "daily" else "close")


def trades_of(evs, fee):
    """One position per market at a time over the variant's events (time order); H46's rule."""
    out, busy = [], -1
    for ev in evs:
        if ev["i"] <= busy:
            continue
        if ev["why"] == "OPEN":
            busy = 10 ** 12
            continue
        t = {"asset": ev["asset"], "side": ev["side"], "entry_ms": ev["entry_ms"], "exit_ms": ev["exit_ms"],
             "why_out": ev["why"], "risk": abs(ev["entry"] - ev["stop"]), "entry": ev["entry"],
             "t1_hit": ev["why"] == "TARGET", "half": ev["half"]}
        t.update(cs.money(ev, fee))
        out.append(t)
        busy = ev["busy"]
    return out


# ---------------------------------------------------------------- per market
def season_flags(idx):
    """-> (london_bst, us_dst) boolean arrays (summer time on at the bar)."""
    ms = data.to_ms(idx)
    lo = data.to_ms(extdata._local(idx, LONDON).tz_localize("UTC")) - ms
    ny = data.to_ms(extdata._local(idx, NY).tz_localize("UTC")) - ms
    return np.asarray(lo) != 0, np.asarray(ny) == -4 * HOUR_MS


def build_events(R, var, asset, vid, tz=None):
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    dirs = event_dirs(R, var, tz)
    D = R["datr"]
    ms = R["ms"]
    bst, usd = season_flags(R["index"])
    evs, ex = [], {"no_entry_same_day": 0, "no_datr": 0, "before_start": 0, "open_at_end": 0}
    for i in np.flatnonzero(dirs != 0):
        if not (D[i] == D[i] and D[i] > 0):
            ex["no_datr"] += 1
            continue
        s = int(dirs[i])
        oc = outcome(R, var, i, s, float(D[i]))
        if oc is None:
            ex["no_entry_same_day"] += 1
            continue
        ems = int(ms[oc["e"]])
        if ems < start_ms:
            ex["before_start"] += 1
            continue
        if oc["why"] == "OPEN":
            ex["open_at_end"] += 1
        ev = {"i": int(i), "side": s, "datr": float(D[i]), "asset": asset, "variant": vid, "entry_ms": ems,
              "half": "first" if ems < split_ms else "second"}
        ev.update(oc)
        ts = pd.Timestamp(ems, unit="ms", tz="UTC")
        ev.update(year=int(ts.year), month=int(ts.month), weekday=int(ts.weekday()), bst=bool(bst[oc["e"]]),
                  usdst=bool(usd[oc["e"]]))
        if var["kind"] != "daily":
            o2 = outcome(R, var, i, s, float(D[i]), X=X_SEC)
            ev["hit25"] = None if o2 is None else o2["hit"]
        evs.append(ev)
    return evs, ex


def truncation_check(df, vids, cuts):
    R = adr.readings(df, box=db.BOX)
    jobs = [(v, None) for v in vids] + [(v, LONDON) for v in vids if v in LOCAL_CHECK]
    full = dict(((v, tz), event_key(R, VARIANTS[v], tz)) for v, tz in jobs)
    bad, checked = 0, 0
    for cut in cuts:
        pR = adr.readings(df.iloc[:cut], box=db.BOX)
        for v, tz in jobs:
            want = [x for x in full[(v, tz)] if x[0] < cut]
            checked += len(want)
            if event_key(pR, VARIANTS[v], tz) != want:
                bad += 1
    return {"cuts": len(cuts), "events_checked": checked, "mismatched_runs": bad}


def run_market(asset):
    df = load_market(asset)
    R = adr.readings(df, box=db.BOX)
    vids = [v for v in ORDER if asset in VARIANTS[v]["markets"]]
    res = {"asset": asset, "fee_side": fee_of(asset), "bars": int(len(df)), "first_bar": str(df.index[0]),
           "last_bar": str(df.index[-1]), "source": "Kronos store (read only)" if asset in KRONOS_ASSETS else "engine data/",
           "excluded": {}}
    E, L = {}, {}
    for v in vids:
        E[v], res["excluded"][v] = build_events(R, VARIANTS[v], asset, v)
        if v in LOCAL_CHECK:
            L[v], _ = build_events(R, VARIANTS[v], asset, v + "L", LONDON)
    n = len(df)
    res["truncation"] = truncation_check(df, vids, [int(n * 0.6) + 7, n - 40])
    return res, E, L


# ---------------------------------------------------------------- aggregation
def cell(evs, key="hit"):
    res = [e for e in evs if e.get(key) is not None]
    k = int(sum(e[key] for e in res))
    m = len(res)
    return {"events": len(evs), "resolved": m, "hits": k, "unresolved": len(evs) - m,
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": cs.binom_p(k, m) if m else None}


def halves(evs, key="hit"):
    return {"first": cell([e for e in evs if e["half"] == "first"], key),
            "second": cell([e for e in evs if e["half"] == "second"], key), "all": cell(evs, key)}


def tmetrics(tr):
    return db.metrics(tr) if tr else {"trades": 0, "net_usd": 0.0}


def months_of(half):
    a, b = (START, SPLIT) if half == "first" else (SPLIT, SEAL)
    return (ms_of(b) - ms_of(a)) / (DAY_MS * 30.4375)


def aggregate(E, L, results):
    A = {}
    for v in ORDER:
        var = VARIANTS[v]
        evs = [e for a in var["markets"] for e in E.get(a, {}).get(v, [])]
        node = {"pooled": halves(evs), "markets": dict((a, halves(E[a][v])) for a in var["markets"] if v in E.get(a, {}))}
        if var["kind"] != "daily":
            node["x025"] = {"pooled": halves(evs, "hit25"),
                            "markets": dict((a, halves(E[a][v], "hit25")) for a in var["markets"] if v in E.get(a, {}))}
        # trades
        trs = {}
        for a in var["markets"]:
            trs[a] = trades_of(E[a][v], fee_of(a)) if v in E.get(a, {}) else []
        allt = [t for a in trs for t in trs[a]]
        node["trades"] = {"pooled": dict((hf, tmetrics([t for t in allt if t["half"] == hf])) for hf in ("first", "second")),
                          "markets": dict((a, dict((hf, tmetrics([t for t in trs[a] if t["half"] == hf]))
                                                   for hf in ("first", "second"))) for a in trs)}
        node["trades"]["per_month"] = dict((hf, round(len([t for t in allt if t["half"] == hf]) / months_of(hf), 2))
                                           for hf in ("first", "second"))
        node["events_per_month"] = dict((hf, round(len([e for e in evs if e["half"] == hf]) / months_of(hf), 2))
                                        for hf in ("first", "second"))
        # descriptive splits
        node["by_dir"] = {"pooled": dict((("up" if s > 0 else "down"), halves([e for e in evs if e["side"] == s])) for s in (1, -1)),
                          "markets": dict((a, dict((("up" if s > 0 else "down"), halves([e for e in E[a][v] if e["side"] == s]))
                                                   for s in (1, -1))) for a in var["markets"] if v in E.get(a, {}))}
        yrs = sorted(set(e["year"] for e in evs))
        node["by_year"] = {"pooled": dict((str(y), cell([e for e in evs if e["year"] == y])) for y in yrs),
                           "markets": dict((a, dict((str(y), cell([e for e in E[a][v] if e["year"] == y])) for y in yrs))
                                           for a in var["markets"] if v in E.get(a, {}))}
        node["by_weekday"] = dict((str(d), cell([e for e in evs if e["weekday"] == d])) for d in range(7))
        node["by_month"] = dict((str(m), cell([e for e in evs if e["month"] == m])) for m in range(1, 13))
        if var["kind"] == "or":
            node["season"] = {"US summer time": halves([e for e in evs if e["usdst"]]),
                              "US winter time": halves([e for e in evs if not e["usdst"]])}
        else:
            node["season"] = {"London BST (summer)": halves([e for e in evs if e["bst"]]),
                              "London GMT (winter)": halves([e for e in evs if not e["bst"]])}
        if v in LOCAL_CHECK:
            le = [e for a in var["markets"] for e in L.get(a, {}).get(v, [])]
            node["london_local"] = {"pooled": halves(le),
                                    "markets": dict((a, halves(L[a][v])) for a in var["markets"] if v in L.get(a, {}))}
        # the pass bar
        c1, c2 = node["pooled"]["first"], node["pooled"]["second"]
        t2 = node["trades"]["pooled"]["second"]
        pos = [a for a in var["markets"] if node["trades"]["markets"][a]["second"].get("net_usd", 0) > 0
               and node["trades"]["markets"][a]["second"].get("trades", 0) > 0]
        need_m = len(var["markets"]) // 2 + 1
        bar = {"hit_both": bool(c1["hit_pct"] is not None and c2["hit_pct"] is not None and c1["hit_pct"] >= PASS_HIT
                                and c2["hit_pct"] >= PASS_HIT),
               "n_both": bool(c1["resolved"] >= MIN_RESOLVED and c2["resolved"] >= MIN_RESOLVED),
               "p_both": bool(c1["p"] is not None and c2["p"] is not None and c1["p"] < ALPHA and c2["p"] < ALPHA),
               "net_second_pooled": bool(t2.get("trades", 0) > 0 and t2["net_usd"] > 0),
               "markets_positive": pos, "markets_needed": need_m, "markets_ok": len(pos) >= need_m}
        bar["pass"] = bool(bar["hit_both"] and bar["n_both"] and bar["p_both"] and bar["net_second_pooled"] and bar["markets_ok"])
        node["bar"] = bar
        node["min_hit"] = (min(c1["hit_pct"], c2["hit_pct"]) if (c1["resolved"] >= MIN_RESOLVED and c2["resolved"] >= MIN_RESOLVED)
                           else None)
        A[v] = node
    # per-market cells passing Bonferroni in both halves (descriptive count over all 33 cells)
    bonf = []
    for v in ORDER:
        cells = [("pooled", A[v]["pooled"])] + list(A[v]["markets"].items())
        for name, c in cells:
            if c["first"]["p"] is not None and c["second"]["p"] is not None and c["first"]["p"] < ALPHA and c["second"]["p"] < ALPHA:
                bonf.append("%s %s" % (v, name))
    passed = [v for v in ORDER if A[v]["bar"]["pass"]]
    cands = [(A[v]["min_hit"], v) for v in ORDER if A[v]["min_hit"] is not None]
    best = passed[0] if passed else (max(cands)[1] if cands else None)
    return A, {"passed": passed, "best": best, "bonf_both": bonf}


# ---------------------------------------------------------------- report
WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | -"
    return "%.1f%% | %d (%d unres.) | %s" % (c["hit_pct"], c["resolved"], c["unresolved"], _p(c["p"]))


def _p(p):
    if p is None:
        return "-"
    return "%.1e" % p if p < 0.001 else "%.3f" % p


def _hs(c):
    return "-" if not c or not c.get("resolved") else "%.1f%% (%d)" % (c["hit_pct"], c["resolved"])


def _t(m):
    if not m or not m.get("trades"):
        return "0 | | | | |"
    return "%d | %.1f%% | %+.3f / %+.3f | %+.4f%% | %s" % (m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"],
                                                         m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


def report(S):
    A, J, res = S["agg"], S["judge"], S["results"]
    L = ["# H48: FX daily-break continuation and session-range breakouts", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H48) before any outcome. Development data only "
         "(rows before %s 00:00 UTC; the holdout was not read). Events with entry from %s; first half before %s. Written %s." % (
             REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Outcome = +0.5 daily ATR in the break direction before -0.5 daily ATR from the next 15m open (A: within 72 h, "
         "H46's code; B: within the same UTC day). A bar touching both = miss; neither = unresolved, excluded. Hit rate = "
         "hits / resolved; a coin flip is ~50%%. p = exact two-sided binomial against 50%%. Tests per half: **%d** (each "
         "variant's pooled cell + one per market); Bonferroni threshold p < %.2e. Trade: next open, stop and target 0.5 "
         "daily ATR, out after 72 h (A) or at the close of the UTC day's last bar (B), one position per market, $10,000, "
         "own fee a side." % (N_TESTS, ALPHA), ""]
    L += ["## Verdict: %s" % (("PASS: " + ", ".join(J["passed"])) if J["passed"] else "NO PASS"), "",
          "| id | rule | markets | 1st: hit | n | p | 2nd: hit | n | p | hit>=55 both | n>=200 both | p both | net 2nd pooled > 0 | markets net > 0 (2nd) | PASS |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    for v in ORDER:
        a, b = A[v], A[v]["bar"]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d of %d (need %d): %s | **%s** |" % (
            v, vdesc(v), ", ".join(VARIANTS[v]["markets"]), _h(a["pooled"]["first"]), _h(a["pooled"]["second"]),
            yn(b["hit_both"]), yn(b["n_both"]), yn(b["p_both"]), yn(b["net_second_pooled"]), len(b["markets_positive"]),
            len(VARIANTS[v]["markets"]), b["markets_needed"], ", ".join(b["markets_positive"]) or "none",
            "PASS" if b["pass"] else "no"))
    L += ["", "Cells passing Bonferroni in BOTH halves (any side of 50%%), of %d: %s." % (
        N_TESTS, ", ".join(J["bonf_both"]) or "none"), ""]
    L += ["## Per market (hit rate, resolved n, p)", "", "| id | market | 1st: hit | n | p | 2nd: hit | n | p | all dev: hit | n | p |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        for m, c in A[v]["markets"].items():
            L.append("| %s | %s | %s | %s | %s |" % (v, m, _h(c["first"]), _h(c["second"]), _h(c["all"])))
    L += ["", "## After costs (stop / target 0.5 daily ATR)", "",
          "| id | scope | half | trades | won | R before / after costs | per trade (% stake) | net $ |", "|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        T = A[v]["trades"]
        for hf in ("first", "second"):
            L.append("| %s | pooled | %s | %s |" % (v, hf, _t(T["pooled"][hf])))
        for m in VARIANTS[v]["markets"]:
            L.append("| %s | %s | second | %s |" % (v, m, _t(T["markets"][m]["second"])))
    L += ["", "Trades a month (pooled, 1st / 2nd half): " + "; ".join(
        "%s %.1f / %.1f" % (v, A[v]["trades"]["per_month"]["first"], A[v]["trades"]["per_month"]["second"]) for v in ORDER) + ".", ""]
    # A steadiness
    L += ["## (A) FX steadiness", "", "### By direction", "", "| id | scope | direction | 1st: hit | n | p | 2nd: hit | n | p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for v in ("A1", "A2"):
        for dname in ("up", "down"):
            c = A[v]["by_dir"]["pooled"][dname]
            L.append("| %s | pooled | %s | %s | %s |" % (v, dname, _h(c["first"]), _h(c["second"])))
            for m in VARIANTS[v]["markets"]:
                c = A[v]["by_dir"]["markets"][m][dname]
                L.append("| %s | %s | %s | %s | %s |" % (v, m, dname, _h(c["first"]), _h(c["second"])))
    for v in ("A1", "A2"):
        yrs = list(A[v]["by_year"]["pooled"])
        L += ["", "### %s by calendar year (hit rate, resolved n)" % v, "", "| scope | " + " | ".join(yrs) + " |",
              "|---|" + "---|" * len(yrs)]
        L.append("| pooled | " + " | ".join(_hs(A[v]["by_year"]["pooled"][y]) for y in yrs) + " |")
        for m in VARIANTS[v]["markets"]:
            L.append("| %s | " % m + " | ".join(_hs(A[v]["by_year"]["markets"][m].get(y)) for y in yrs) + " |")
    # B secondary
    L += ["", "## (B) secondary: X = 0.25 daily ATR (descriptive, not counted)", "",
          "| id | scope | 1st: hit | n | p | 2nd: hit | n | p |", "|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        if "x025" not in A[v]:
            continue
        c = A[v]["x025"]["pooled"]
        L.append("| %s | pooled | %s | %s |" % (v, _h(c["first"]), _h(c["second"])))
        for m, c in A[v]["x025"]["markets"].items():
            L.append("| %s | %s | %s | %s |" % (v, m, _h(c["first"]), _h(c["second"])))
    # DST
    L += ["", "## Daylight saving (descriptive)", "", "UTC windows split by season, and B1-B3 recomputed with the same clock "
          "windows read in London local time (so in BST they sit one hour earlier in UTC).", "",
          "| id | split | 1st: hit | n | p | 2nd: hit | n | p |", "|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        if VARIANTS[v]["kind"] == "daily":
            continue
        for k, c in A[v]["season"].items():
            L.append("| %s | %s | %s | %s |" % (v, k, _h(c["first"]), _h(c["second"])))
        if "london_local" in A[v]:
            c = A[v]["london_local"]["pooled"]
            L.append("| %s | London-local windows, pooled | %s | %s |" % (v, _h(c["first"]), _h(c["second"])))
    # best variant extras
    bv = J["best"]
    if bv:
        a = A[bv]
        L += ["", "## %s variant %s: by weekday and month of year (all development data, pooled)" % (
            "Passing" if J["passed"] else "Best (highest lower-half hit rate, not passing)", bv), "",
              "| weekday | " + " | ".join(WD[int(d)] for d in a["by_weekday"] if a["by_weekday"][d]["events"]) + " |",
              "|---|" + "---|" * sum(1 for d in a["by_weekday"] if a["by_weekday"][d]["events"]),
              "| hit (n) | " + " | ".join(_hs(c) for c in a["by_weekday"].values() if c["events"]) + " |", "",
              "| month | " + " | ".join(a["by_month"]) + " |", "|---|" + "---|" * 12,
              "| hit (n) | " + " | ".join(_hs(c) for c in a["by_month"].values()) + " |", "",
              "Events a month (pooled, 1st / 2nd): %.1f / %.1f; trades a month: %.1f / %.1f." % (
                  a["events_per_month"]["first"], a["events_per_month"]["second"], a["trades"]["per_month"]["first"],
                  a["trades"]["per_month"]["second"]), ""]
    L += ["## Data and checks", ""]
    for m, r in res.items():
        tc = r["truncation"]
        L.append("- %s (%s): %d bars %s to %s, fee %.3f%% a side; truncation check %d cuts, %d events compared, %d mismatched runs; "
                 "excluded %s." % (m, r["source"], r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"],
                                   tc["cuts"], tc["events_checked"], tc["mismatched_runs"],
                                   "; ".join("%s %s" % (v, ", ".join("%s %d" % (k, x) for k, x in ex.items() if x))
                                             for v, ex in r["excluded"].items())))
    L += ["", "USDJPY is where H46 found the FX lean, so A's pooled cells are not independent of H46; USDSGD alone is "
          "the out-of-family check. NDX = the Dukascopy Nasdaq-100 CFD restricted to NYSE cash hours (engine SPX filter). "
          "No data was fetched from the internet.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- live scan (paper)
def _px(v):
    if v is None or v != v:
        return "n/a"
    a = abs(v)
    return "{:,.1f}".format(v) if a >= 1000 else ("%.3f" % v if a >= 10 else "%.5f" % v)


def scan(S=None, now_ms=None):
    passed = (S or {}).get("judge", {}).get("passed", [])
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    lines = ["H48 live session-break scan, %s (PAPER; %s)" % (
        pd.Timestamp(now_ms, unit="ms", tz="UTC").strftime("%d %b %Y %H:%M UTC"),
        ("passed: " + ", ".join(passed)) if passed else "UNTESTED / no variant passed H48's history bar")]
    rows = []
    for a in MARKETS:
        try:
            df = load_market(a, dev=False)
        except Exception as ex:                       # noqa: BLE001
            lines.append("  %-7s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=40)]
        df = df[data.to_ms(df.index) + BAR_MS <= now_ms]
        R = adr.readings(df, box=db.BOX)
        n = R["n"]
        if not n:
            continue
        i = n - 1
        day = R["ms"] // DAY_MS
        last_close = pd.Timestamp(int(R["ms"][i]) + BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - int(R["ms"][i]) - BAR_MS) / 3600000.0
        D = R["datr"][i]
        if a in KRONOS_ASSETS and age_h > 1:
            note = " (STALE %.0f h: the Kronos store has not been refreshed; events shown are for that last day)" % age_h
        elif age_h > 6:
            note = " (%.0f h old: market shut; events shown are for the last session on file)" % age_h
        elif age_h > 0.5:
            note = " (%.1f h old: feed lag)" % age_h
        else:
            note = ""
        head = "  %-7s last close %s%s, daily ATR %s" % (a, last_close.strftime("%a %d %b %H:%M UTC"), note, _px(D))
        lines.append(head)
        today = day == day[i]
        for v in ORDER:
            var = VARIANTS[v]
            if a not in var["markets"]:
                continue
            if var["kind"] == "daily":
                dirs = event_dirs(R, var)
                hi, lo = (R["pdh"], R["pdl"]) if var["level"] == "pday" else (R["box_hi"], R["box_lo"])
                st = "%s high %s / low %s" % (var["level"], _px(hi[i]), _px(lo[i]))
            else:
                dirs, hi, lo, cnt = session_events(R, var)
                mins, _ = clock(R, var)
                if var["kind"] == "or" and mins[i] < 0:
                    st = "no cash session today yet"
                elif mins[i] < var["range"][1]:
                    st = "range still forming (%d bars so far, hi %s / lo %s)" % (cnt[i], _px(hi[i]), _px(lo[i]))
                else:
                    st = "range hi %s / lo %s (%d bars)%s" % (_px(hi[i]), _px(lo[i]), cnt[i],
                                                            ", window closed" if mins[i] >= var["window"][1] else ", window OPEN")
            evs = []
            for j in np.flatnonzero(today & (dirs != 0)):
                s = int(dirs[j])
                when = pd.Timestamp(int(R["ms"][j]) + BAR_MS, unit="ms", tz="UTC").strftime("%H:%M")
                oc = outcome(R, var, j, s, float(R["datr"][j])) if R["datr"][j] > 0 else None
                if oc is None:
                    entry = float(R["c"][j])
                    txt = "%s break at %s close, entry at the next open (about %s), stop %s, target %s" % (
                        "UP" if s > 0 else "DOWN", when, _px(entry), _px(entry - s * X_MAIN * D), _px(entry + s * X_MAIN * D))
                    status = "WAITING"
                else:
                    status = {1: "TARGET hit", 0: "STOP hit"}.get(oc["hit"], "open" if oc["why"] == "OPEN" else "time exit")
                    txt = "%s break at %s close, entry %s, stop %s, target %s: %s" % (
                        "UP" if s > 0 else "DOWN", when, _px(oc["entry"]), _px(oc["stop"]), _px(oc["target"]), status)
                evs.append(txt)
                rows.append({"asset": a, "variant": v, "side": s, "close_utc": when, "status": status})
            lines.append("      %s: %s; %s" % (v, st, "; ".join(evs) if evs else "no event today"))
    lines.append("  (PAPER / UNTESTED unless marked passed; nothing is traded or wired)")
    return rows, lines


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H48 session break study")
    results, E, L = {}, {}, {}
    try:
        for a in MARKETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a], E[a], L[a] = run_market(a)
            log("%s: done in %.0f s; events %s; truncation %s" % (
                a, time.time() - t0, dict((v, len(x)) for v, x in E[a].items()), results[a]["truncation"]))
    finally:
        release_lock()
    A, J = aggregate(E, L, results)
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC,
         "n_tests": N_TESTS, "alpha": ALPHA, "variants": dict((v, dict(VARIANTS[v], desc=vdesc(v))) for v in ORDER),
         "agg": A, "judge": J, "results": results}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("passed %s, best %s" % (J["passed"], J["best"]))
    return S


def load_study():
    with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
        return json.load(fh)


def print_scan():
    try:
        S = load_study()
    except Exception:                                 # noqa: BLE001
        S = None
    _rows, lines = scan(S)
    print("\n".join(lines))


if __name__ == "__main__":
    if "--report" in sys.argv:
        S = load_study()
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(S))
    elif "--scan" in sys.argv:
        print_scan()
    else:
        main()
        print_scan()
