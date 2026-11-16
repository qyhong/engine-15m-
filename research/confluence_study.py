# -*- coding: utf-8 -*-
"""H46 momentum / speed / participation CONFLUENCE at a daily-level break. PAPER RESEARCH ONLY.

Registered before any code or outcome: research/HYPOTHESES.md H46 (16 Nov 2026, 05:11 UTC). In short:
  * events = H45's first 15m close beyond the prior UTC day's high/low (pday) or the previous 96 bars' high/low
    (roll24) per UTC day per direction (dailybreak_study.daily_breaks, momentum OFF), eight markets;
  * outcome = +0.5 daily ATR in the break direction before -0.5 daily ATR from the next open within 72 h (same bar =
    miss, neither = unresolved, excluded and counted);
  * seven yes/no confluence groups at the break bar's close (speed, 1h trend strength, oscillator, participation,
    squeeze release, 4h/1d alignment, crypto open interest), the count, 32 buckets per level and scope, 384 tests;
  * a "70% setup" needs >= 70% with >= 100 resolved events and Bonferroni p < 0.05/384 in BOTH halves;
  * development rows before 2025-11-11 only; entries from 2020-01-01; halves split at 2023-06-07.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market. Reads data/*.csv and data/sources/flows_metrics_*.csv only; writes research/out/confluence/.

    py -3 research/confluence_study.py            (run, write study.json + study.md + events.csv, then the live scan)
    py -3 research/confluence_study.py --report   (rewrite study.md from study.json)
    py -3 research/confluence_study.py --scan     (the live scan only: latest closed bars, paper / untested)
"""
import itertools
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, indicators as ind, playbook as pb  # noqa: E402
from engine15.sources import adr, flows, ltf  # noqa: E402
from engine15.rl import resources  # noqa: E402

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402
import rangebreak_study as rb  # noqa: E402
import dailybreak_study as db  # noqa: E402

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 05:11 UTC"
ASSETS = rb.ASSETS
CRYPTO = ("BTCUSDT", "ETHUSDT")
MGROUPS = db.GROUPS
GROUP_OF = db.GROUP_OF
SCOPES = ["pooled"] + list(MGROUPS)
LEVELS = ("pday", "roll24")
OUT = os.path.join(ROOT, "research", "out", "confluence")
NEED_MB = 1500
BAR_MS, DAY_MS, HOUR_MS = pb.BAR_MS, 86400000, 3600000
HOLD_MS = 3 * DAY_MS
TGT = 0.5                                   # +/- 0.5 daily ATR

# ---- the registered group constants
SPEED_BARS, SPEED_WIN, SPEED_MIN, SPEED_SD, MOM_K = 4, 2880, 672, 1.0, 1.5
ADX_MIN = 20.0
RSI_N, RSI1H_EDGE, RSI4H_EDGE = 14, 10.0, 30.0
VOL_DAYS, VOL_MIN_DAYS, VOL_X = 20, 10, 2.0
BB_N, BB_K, KC_N, KC_K, SQ_BARS = 20, 2.0, 20, 1.5, 8
OI_LAG_MS = 4 * HOUR_MS

GNAMES = ["speed", "trend", "osc", "part", "squeeze", "htf", "lev"]
GTITLE = {"speed": "1 speed", "trend": "2 trend strength", "osc": "3 oscillator", "part": "4 participation",
          "squeeze": "5 squeeze release", "htf": "6 HTF alignment", "lev": "7 leverage (OI)"}
MIN_RESOLVED, PASS_HIT = 100, 70.0


def bucket_defs():
    """-> ordered list of (bucket id, test function on an event dict). 32 per level and scope."""
    B = [("count>=3", lambda e: e["count"] >= 3), ("count>=4", lambda e: e["count"] >= 4),
         ("count>=5", lambda e: e["count"] >= 5), ("all", lambda e: e["all"])]
    for g in GNAMES:
        B.append((g, (lambda g: lambda e: e[g])(g)))
    for a, b in itertools.combinations(GNAMES, 2):
        B.append(("%s+%s" % (a, b), (lambda a, b: lambda e: e[a] and e[b])(a, b)))
    return B


BUCKETS = bucket_defs()
N_TESTS = len(BUCKETS) * len(LEVELS) * len(SCOPES)            # 32 x 2 x 6 = 384
ALPHA = 0.05 / N_TESTS


# ---------------------------------------------------------------- statistics
def binom_p(k, n):
    """Exact two-sided binomial p-value of k successes in n against 0.5 (symmetric: 2 x the smaller tail)."""
    if n <= 0:
        return None
    m = min(k, n - k)
    j = np.arange(0, m + 1, dtype=float)
    # log C(n, j) by cumulative sums: log C(n, j+1) = log C(n, j) + log(n - j) - log(j + 1)
    steps = np.log(n - j[:-1]) - np.log(j[:-1] + 1.0) if m > 0 else np.zeros(0)
    logc = np.concatenate([[0.0], np.cumsum(steps)])
    lp = logc - n * math.log(2.0)
    mx = lp.max()
    tail = math.exp(mx) * float(np.exp(lp - mx).sum())
    return float(min(1.0, 2.0 * tail))


# ---------------------------------------------------------------- the confluence groups (truncation-tested)
def _sh(x, d=1):
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if 0 < d < len(x):
        out[d:] = x[:len(x) - d]
    elif d == 0:
        out = x.copy()
    return out


def _clean(bars):
    b = bars.copy()
    for col in ("volume", "taker_buy"):
        if col not in b:
            b[col] = np.nan
    b = b[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)
    if not b.index.is_monotonic_increasing or b.index.has_duplicates:
        b = b[~b.index.duplicated(keep="last")].sort_index()
    return b


def _rsi(close):
    r = ind.rsi(close, RSI_N)
    return r.where(np.arange(len(r)) >= RSI_N)


def squeeze_age(b):
    """ltf.py trendq's squeeze: -> (on, valid, bars since the last release (NaN while ON or before the first))."""
    c = b["close"]
    mid = c.rolling(BB_N).mean()
    sd = c.rolling(BB_N).std(ddof=0)
    kc = KC_K * ind.true_range(b).rolling(KC_N).mean()
    valid = (sd.notna() & kc.notna() & mid.notna()).values
    on = valid & ((BB_K * sd).values < kc.values)
    prev_on = np.concatenate([[False], on[:-1]])
    released = prev_on & ~on & valid
    n = len(on)
    last = np.maximum.accumulate(np.where(released, np.arange(n), -1)) if n else np.zeros(0, int)
    age = np.where(last >= 0, np.arange(n) - last, np.nan).astype(float)
    age = np.where(on, np.nan, age)
    return on, valid, age


def confluence(bars, oi=None, crypto=False):
    """15m bars (+ an optional open-interest frame ts_ms / oi) -> dict of arrays on the bars' rows, each known at the
    close of its row: up_<g> / dn_<g> (bool: group g confirms an up / a down break at this close), read7 (an OI read),
    and the raw values behind them (for the scan). Row i uses only bars <= i (and OI snapshots stamped <= its open)."""
    b = _clean(bars)
    n = len(b)
    ms = data.to_ms(b.index)
    o, h, l, c, v, tb = (b[k].values.astype(float) for k in ("open", "high", "low", "close", "volume", "taker_buy"))
    F = {"n": n, "ms": ms}
    with np.errstate(divide="ignore", invalid="ignore"):
        # 1 SPEED
        lc = np.log(c)
        r1h = lc - _sh(lc, SPEED_BARS)
        sd1h = pd.Series(r1h).rolling(SPEED_WIN, min_periods=SPEED_MIN).std().values
        tr = ind.true_range(b).values.astype(float)
        atr15 = ind.atr_wilder(b, 14).values.astype(float)
        bar_x = tr / _sh(atr15)
        F["r1h_z"] = np.where(sd1h > 0, r1h / sd1h, np.nan)
        F["bar_x"] = bar_x
        big = np.nan_to_num(bar_x >= MOM_K).astype(bool)
        F["up_speed"] = np.nan_to_num(F["r1h_z"] >= SPEED_SD).astype(bool) | big
        F["dn_speed"] = np.nan_to_num(-F["r1h_z"] >= SPEED_SD).astype(bool) | big
        # 2 TREND STRENGTH (1h) and 3 OSCILLATOR (1h, 4h)
        h1 = data.resample(b, "1h")
        a = ltf.adx(h1)
        hist = ltf.macd_hist(h1["close"])
        f1 = pd.DataFrame({"adx": a["adx"], "adx_prev": a["adx"].shift(1), "dip": a["plus"] - a["minus"],
                           "hist": hist, "hist_prev": hist.shift(1), "rsi": _rsi(h1["close"])}, index=h1.index)
        j1 = data.htf_on_15(b, "1h", f1)
        adx_, adxp, dip = j1["adx"].values, j1["adx_prev"].values, j1["dip"].values
        hs, hp = j1["hist"].values, j1["hist_prev"].values
        strong = (adx_ >= ADX_MIN) & (adx_ > adxp)
        F["up_trend"] = np.nan_to_num((strong & (dip > 0)) | ((hs > 0) & (hs > hp))).astype(bool)
        F["dn_trend"] = np.nan_to_num((strong & (dip < 0)) | ((hs < 0) & (hs < hp))).astype(bool)
        F["adx1h"], F["dip1h"], F["hist1h"], F["hist1h_prev"] = adx_, dip, hs, hp
        h4 = data.resample(b, "4h")
        r1 = j1["rsi"].values
        r4 = data.htf_on_15(b, "4h", pd.DataFrame({"rsi": _rsi(h4["close"])}, index=h4.index))["rsi"].values
        ok4 = np.isfinite(r4)
        F["up_osc"] = np.nan_to_num((r1 - 50.0 > RSI1H_EDGE) & ok4 & ~(r4 - 50.0 > RSI4H_EDGE)).astype(bool)
        F["dn_osc"] = np.nan_to_num((50.0 - r1 > RSI1H_EDGE) & ok4 & ~(50.0 - r4 > RSI4H_EDGE)).astype(bool)
        F["rsi1h"], F["rsi4h"] = r1, r4
        # 4 PARTICIPATION
        slot = ms % DAY_MS
        vs = pd.Series(v)
        med = vs.groupby(slot).transform(lambda s: s.shift(1).rolling(VOL_DAYS, min_periods=VOL_MIN_DAYS).median()).values
        vol_x = np.where((med > 0) & np.isfinite(v), v / np.where(med > 0, med, 1.0), np.nan)
        F["vol_x"] = vol_x
        loud = np.nan_to_num(vol_x >= VOL_X).astype(bool)
        if crypto:
            share = np.where(v > 0, tb / np.where(v > 0, v, 1.0), np.nan)
            F["taker_share"] = share
            F["up_part"] = loud & np.nan_to_num(share > 0.5).astype(bool)
            F["dn_part"] = loud & np.nan_to_num(share < 0.5).astype(bool)
        else:
            F["taker_share"] = np.full(n, np.nan)
            F["up_part"] = loud.copy()
            F["dn_part"] = loud.copy()
        # 5 SQUEEZE RELEASE
        on, valid, age = squeeze_age(b)
        sq = valid & ~on & np.nan_to_num(age <= SQ_BARS).astype(bool) & np.isfinite(age)
        F["sq_age"], F["sq_on"] = age, on
        F["up_squeeze"], F["dn_squeeze"] = sq.copy(), sq.copy()
        # 6 HTF ALIGNMENT
        s4 = data.htf_on_15(b, "4h", ind.trend_score(h4["close"]).rename("s")).values.astype(float)
        d1 = data.resample(b, "1D")
        s1 = data.htf_on_15(b, "1D", ind.trend_score(d1["close"]).rename("s")).values.astype(float)
        F["score4h"], F["score1d"] = s4, s1
        F["up_htf"] = np.nan_to_num((s4 > 0) & (s1 > 0)).astype(bool)
        F["dn_htf"] = np.nan_to_num((s4 < 0) & (s1 < 0)).astype(bool)
        # 7 LEVERAGE (crypto open interest, snapshot at the bar's open vs 4 h earlier)
        F["oi_4h"] = np.full(n, np.nan)
        if crypto and oi is not None and len(oi):
            s = pd.Series(oi["oi"].values.astype(float), index=oi["ts_ms"].values.astype("int64"))
            s = s[~s.index.duplicated(keep="last")].sort_index()
            now = s.reindex(ms).values
            prev = s.reindex(ms - OI_LAG_MS).values
            okoi = (now > 0) & (prev > 0)
            F["oi_4h"] = np.where(okoi, np.log(np.where(okoi, now, 1.0) / np.where(okoi, prev, 1.0)), np.nan)
        F["read7"] = np.isfinite(F["oi_4h"])
        F["up_lev"] = np.nan_to_num(F["oi_4h"] > 0).astype(bool)
        F["dn_lev"] = F["up_lev"].copy()
    return F


def flags_at(F, i, s):
    """-> the event's group flags, count and 'all' at row i for side s."""
    pre = "up_" if s > 0 else "dn_"
    e = dict((g, bool(F[pre + g][i])) for g in GNAMES)
    e["count"] = int(sum(e[g] for g in GNAMES))
    e["read7"] = bool(F["read7"][i])
    e["all"] = bool(all(e[g] for g in GNAMES[:6]) and (e["lev"] or not e["read7"]))
    return e


def events(R, F, level):
    """-> list of event dicts (break rows, oldest first) with flags; everything known at the close of the break bar."""
    dirs = db.daily_breaks(R, level, False)
    out = []
    D = R["datr"]
    for i in np.flatnonzero(dirs != 0):
        if not (D[i] == D[i] and D[i] > 0):
            continue
        s = int(dirs[i])
        e = {"i": int(i), "side": s, "datr": float(D[i])}
        e.update(flags_at(F, i, s))
        out.append(e)
    return out


def event_key(evs):
    return [(e["i"], e["side"], round(e["datr"], 9)) + tuple(e[g] for g in GNAMES) + (e["count"], e["all"], e["read7"])
            for e in evs]


# ---------------------------------------------------------------- outcome and the trade
def outcome(R, i, s, D):
    """-> dict: entry row e, hit (1 / 0 / None unresolved), ambiguous (both in one bar), exit for the trade
    (why STOP / TARGET / TIME / OPEN, price, row). Bars e .. x3-1 (x3 = the first bar at or after entry + 72 h)."""
    n, o, h, l, ms = R["n"], R["o"], R["h"], R["l"], R["ms"]
    day = ms // DAY_MS
    e = i + 1
    if e >= n or day[e] != day[i]:
        return None
    en = float(o[e])
    stop, tgt = en - s * TGT * D, en + s * TGT * D
    x3 = int(np.searchsorted(ms, ms[e] + HOLD_MS, side="left"))
    H, L, O = h[e:x3], l[e:x3], o[e:x3]
    if s > 0:
        adv, fav = L <= stop, H >= tgt
    else:
        adv, fav = H >= stop, L <= tgt
    ja = int(np.argmax(adv)) if adv.any() else None
    jf = int(np.argmax(fav)) if fav.any() else None
    r = {"e": e, "entry": en, "stop": stop, "target": tgt, "ambiguous": False}
    if ja is None and jf is None:
        r["hit"] = None
        if x3 < n:
            r.update(why="TIME", exit=float(o[x3]), exit_bar=x3)
        else:
            r.update(why="OPEN", exit=None, exit_bar=None)
        return r
    if jf is None or (ja is not None and ja <= jf):
        j = ja
        r["hit"], r["ambiguous"] = 0, bool(jf is not None and ja == jf)
        px = float(O[j]) if s * (O[j] - stop) <= 0 else stop
        r.update(why="STOP", exit=px, exit_bar=e + j)
    else:
        j = jf
        r["hit"] = 1
        px = float(O[j]) if s * (O[j] - tgt) >= 0 else tgt
        r.update(why="TARGET", exit=px, exit_bar=e + j)
    return r


def money(ev, fee):
    s, en, px = ev["side"], ev["entry"], ev["exit"]
    risk = abs(en - ev["stop"])
    gross = s * (px - en) / en * pb.STAKE
    fees = fee * pb.STAKE + fee * pb.STAKE * px / en
    net = gross - fees
    unit = pb.STAKE * risk / en
    return {"gross_usd": gross, "fees_usd": fees, "pnl_usd": net, "r": net / unit, "gross_r": gross / unit}


def trades_of(evs, fee):
    """One position per market at a time over the bucket's events (time order). A signal decided at bar r is taken if
    r > the exit bar - 1 of the open trade (dailybreak_study.simulate's rule)."""
    out, busy = [], -1
    for ev in evs:
        if ev["i"] <= busy or ev.get("why") in (None, "OPEN"):
            if ev.get("why") == "OPEN" and ev["i"] > busy:
                busy = 10 ** 12
            continue
        t = {"entry_ms": ev["entry_ms"], "exit_ms": ev["exit_ms"], "why_out": ev["why"], "risk": abs(ev["entry"] - ev["stop"]),
             "entry": ev["entry"], "t1_hit": ev["why"] == "TARGET"}
        t.update(money(ev, fee))
        out.append(t)
        busy = ev["exit_bar"] - 1
    return out


# ---------------------------------------------------------------- per market
def load_oi(asset, before_ms=None):
    if asset not in CRYPTO:
        return None
    d = flows.load_source("metrics", asset)
    d = d[["ts_ms", "oi"]].dropna()
    if before_ms is not None:
        d = d[d["ts_ms"] < before_ms]
    return d.reset_index(drop=True)


def truncation_check(df, oi, crypto, cuts):
    full_R = adr.readings(df, box=db.BOX)
    full_F = confluence(df, oi, crypto)
    full = dict((lv, event_key(events(full_R, full_F, lv))) for lv in LEVELS)
    bad_ev, bad_flag, checked = 0, 0, 0
    keys = ["up_" + g for g in GNAMES] + ["dn_" + g for g in GNAMES]
    for cut in cuts:
        pR = adr.readings(df.iloc[:cut], box=db.BOX)
        pF = confluence(df.iloc[:cut], oi, crypto)
        for lv in LEVELS:
            want = [x for x in full[lv] if x[0] < cut]
            checked += len(want)
            if event_key(events(pR, pF, lv)) != want:
                bad_ev += 1
        for k in keys:
            if not np.array_equal(pF[k], full_F[k][:cut]):
                bad_flag += 1
    return {"cuts": len(cuts), "events_checked": checked, "mismatched_event_runs": bad_ev, "mismatched_flag_arrays": bad_flag}


def run_asset(asset):
    df = rb.load_dev(asset)
    seal_ms, start_ms, split_ms = ms_of(SEAL), ms_of(START), ms_of(SPLIT)
    crypto = asset in CRYPTO
    oi = load_oi(asset, seal_ms)
    R = adr.readings(df, box=db.BOX)
    F = confluence(df, oi, crypto)
    ms = R["ms"]
    res = {"asset": asset, "group": GROUP_OF[asset], "fee_side": pb.fee_side(asset), "bars": int(len(df)),
           "first_bar": str(df.index[0]), "last_bar": str(df.index[-1]), "excluded": {}}
    evs_all = []
    for lv in LEVELS:
        ex = {"no_entry_same_day": 0, "before_start": 0, "open_at_seal": 0}
        for ev in events(R, F, lv):
            oc = outcome(R, ev["i"], ev["side"], ev["datr"])
            if oc is None:
                ex["no_entry_same_day"] += 1
                continue
            ems = int(ms[oc["e"]])
            if ems < start_ms:
                ex["before_start"] += 1
                continue
            if oc["why"] == "OPEN":
                ex["open_at_seal"] += 1
            ev.update(oc)
            ev.update(asset=asset, mgroup=GROUP_OF[asset], level=lv, entry_ms=ems,
                      exit_ms=int(ms[oc["exit_bar"]]) if oc.get("exit_bar") is not None else None,
                      half="first" if ems < split_ms else "second")
            evs_all.append(ev)
        res["excluded"][lv] = ex
    n = len(df)
    res["truncation"] = truncation_check(df, oi, crypto, [int(n * 0.6) + 7, n - 40])
    res["oi_rows"] = 0 if oi is None else int(len(oi))
    return res, evs_all


# ---------------------------------------------------------------- aggregation
def cell(evs):
    res = [e for e in evs if e["hit"] is not None]
    k = int(sum(e["hit"] for e in res))
    m = len(res)
    return {"events": len(evs), "resolved": m, "hits": k, "unresolved": len(evs) - m,
            "ambiguous": int(sum(e["ambiguous"] for e in evs)),
            "hit_pct": round(100.0 * k / m, 2) if m else None, "p": binom_p(k, m) if m else None}


def in_scope(e, scope):
    return scope == "pooled" or e["mgroup"] == scope


def aggregate(E):
    """-> {level: {scope: {"reference": {half: cell}, "buckets": {bid: {half: cell}}}}}"""
    A = {}
    for lv in LEVELS:
        A[lv] = {}
        for sc in SCOPES:
            ev = [e for e in E if e["level"] == lv and in_scope(e, sc)]
            halves = {"first": [e for e in ev if e["half"] == "first"], "second": [e for e in ev if e["half"] == "second"]}
            node = {"reference": dict((hf, cell(x)) for hf, x in halves.items()), "buckets": {}}
            node["reference"]["all"] = cell(ev)
            for bid, fn in BUCKETS:
                cells = dict((hf, cell([e for e in x if fn(e)])) for hf, x in halves.items())
                c1, c2 = cells["first"], cells["second"]
                ok = (c1["resolved"] >= MIN_RESOLVED and c2["resolved"] >= MIN_RESOLVED)
                cells["min_hit"] = min(c1["hit_pct"], c2["hit_pct"]) if ok else None
                cells["setup70"] = bool(ok and c1["hit_pct"] >= PASS_HIT and c2["hit_pct"] >= PASS_HIT
                                        and c1["p"] < ALPHA and c2["p"] < ALPHA)
                cells["bonf_both"] = bool(ok and c1["p"] is not None and c2["p"] is not None and c1["p"] < ALPHA and c2["p"] < ALPHA)
                node["buckets"][bid] = cells
            A[lv][sc] = node
    return A


def months(half):
    a, b = (START, SPLIT) if half == "first" else (SPLIT, SEAL)
    return (ms_of(b) - ms_of(a)) / (DAY_MS * 30.4375)


def top_buckets(A, k=10):
    rows = []
    for lv in LEVELS:
        for bid, c in A[lv]["pooled"]["buckets"].items():
            if c["min_hit"] is not None:
                rows.append((-c["min_hit"], lv, bid))
    top = [(lv, bid) for _x, lv, bid in sorted(rows)[:k]]
    for lv in LEVELS:
        for sc in SCOPES:
            for bid, c in A[lv][sc]["buckets"].items():
                if c["setup70"] and (lv, bid) not in top:
                    top.append((lv, bid))
    return top


def trade_table(E, top):
    """-> {"level|bucket": {"pooled": {half: metrics}, "markets": {asset: {half: metrics}}, "per_month": {...}}}"""
    fn = dict(BUCKETS)
    T = {}
    split_ms = ms_of(SPLIT)
    for lv, bid in top:
        node = {"pooled": {}, "markets": {}, "per_month": {}}
        allt = []
        for a in ASSETS:
            ev = sorted([e for e in E if e["level"] == lv and e["asset"] == a and fn[bid](e)], key=lambda e: e["i"])
            tr = trades_of(ev, pb.fee_side(a))
            allt += tr
            node["markets"][a] = {}
            for hf in ("first", "second"):
                x = [t for t in tr if (t["entry_ms"] < split_ms) == (hf == "first")]
                node["markets"][a][hf] = db.metrics(x)
                node["per_month"].setdefault(a, {})[hf] = round(
                    len([e for e in ev if e["half"] == hf]) / months(hf), 2)
        for hf in ("first", "second"):
            x = [t for t in allt if (t["entry_ms"] < split_ms) == (hf == "first")]
            node["pooled"][hf] = db.metrics(x)
            node["per_month"].setdefault("pooled", {})[hf] = round(
                len([e for e in E if e["level"] == lv and e["half"] == hf and fn[bid](e)]) / months(hf), 2)
        T["%s|%s" % (lv, bid)] = node
    return T


def single_lift(A):
    """-> {level: {scope: [(group, hit first, hit second, lift first, lift second, share of events)]}}"""
    out = {}
    for lv in LEVELS:
        out[lv] = {}
        for sc in SCOPES:
            node = A[lv][sc]
            ref = node["reference"]
            rows = []
            for g in GNAMES:
                c = node["buckets"][g]
                r = {"group": g}
                for hf in ("first", "second"):
                    h = c[hf]["hit_pct"]
                    r[hf] = h
                    r["lift_" + hf] = None if (h is None or ref[hf]["hit_pct"] is None) else round(h - ref[hf]["hit_pct"], 2)
                    r["share_" + hf] = round(100.0 * c[hf]["events"] / ref[hf]["events"], 1) if ref[hf]["events"] else None
                rows.append(r)
            out[lv][sc] = rows
    return out


# ---------------------------------------------------------------- report
def _h(c):
    if not c or not c.get("resolved"):
        return "- | 0 | |"
    p = c["p"]
    return "%.1f%% | %d (%d unres.) | %s" % (c["hit_pct"], c["resolved"], c["unresolved"],
                                           ("%.1e" % p) if p < 0.001 else ("%.3f" % p))


def bucket_rows(node, sort=True):
    items = list(node["buckets"].items())
    if sort:
        items.sort(key=lambda kv: (kv[1]["min_hit"] is None, -(kv[1]["min_hit"] or 0.0),
                                   -((kv[1]["first"]["hit_pct"] or 0) + (kv[1]["second"]["hit_pct"] or 0))))
    return items


def fmt_tr(m):
    if not m or not m.get("trades"):
        return "0 | | | | | |"
    return "%d | %.1f%% | %+.3f | %+.3f | %+.4f%% | %s" % (m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"],
                                                         m["exp_pct"], "{:+,.0f}".format(m["net_usd"]))


def report(S):
    A, T, res, L1 = S["agg"], S["trades"], S["results"], S["lift"]
    passes = S["setups70"]
    L = ["# H46: momentum / speed / participation confluence at a daily-level break", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H46) before any outcome. Development data only "
         "(rows before %s 00:00 UTC; the holdout was not read). Events with entry from %s; first half before %s. "
         "Written %s." % (REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Event = the first 15m close beyond the level in its UTC day per direction (H45's code, no momentum condition). "
         "Outcome = +0.5 daily ATR in the break direction before -0.5 daily ATR from the next 15m open within 72 h "
         "(a bar touching both = miss; neither = unresolved, excluded). Hit rate = hits / resolved; a coin flip is ~50%%. "
         "p = exact two-sided binomial against 50%%. Buckets tested: %d per level and scope x %d levels x %d scopes = "
         "**%d**; Bonferroni threshold per half p < %.2e." % (len(BUCKETS), len(LEVELS), len(SCOPES), N_TESTS, ALPHA), ""]
    L += ["## Verdict: %s" % ("a 70%% setup was found (%d)" % len(passes) if passes else "NO 70% setup"), ""]
    if passes:
        for p in passes:
            L.append("- %s" % p)
    else:
        best = S["best_min"]
        L.append("No bucket in any scope or level reached 70%% in both halves with >= %d resolved events per half. "
                 "The best lower-of-two-halves hit rate among the pooled buckets is %s." % (MIN_RESOLVED, best))
    nb = S["bonf_both_count"]
    L += ["", "Buckets whose p-value passes Bonferroni in BOTH halves (any hit rate, either side of 50%%): %d of %d." % (nb, N_TESTS), ""]
    L += ["## Reference: every daily break (no confluence)", "", "| level | scope | first: hit | n | p | second: hit | n | p |",
          "|---|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        for sc in SCOPES:
            r = A[lv][sc]["reference"]
            L.append("| %s | %s | %s | %s |" % (lv, sc, _h(r["first"]), _h(r["second"])))
    L += ["", "## Top buckets (pooled, sorted by the lower of the two halves' hit rates, >= %d resolved per half)" % MIN_RESOLVED, "",
          "| # | level | bucket | first: hit | n | p | second: hit | n | p | events / month (pooled, 1st / 2nd) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k, (lv, bid) in enumerate(S["top"], 1):
        c = A[lv]["pooled"]["buckets"][bid]
        pm = T["%s|%s" % (lv, bid)]["per_month"]["pooled"]
        L.append("| %d | %s | %s | %s | %s | %.1f / %.1f |" % (k, lv, bid, _h(c["first"]), _h(c["second"]), pm["first"], pm["second"]))
    L += ["", "## Which single groups help (pooled; lift = bucket hit rate minus the level's reference, percentage points)", "",
          "| level | group | share of events 1st / 2nd | hit 1st | lift 1st | hit 2nd | lift 2nd |", "|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        for r in L1[lv]["pooled"]:
            L.append("| %s | %s | %s / %s%% | %s | %s | %s | %s |" % (
                lv, GTITLE[r["group"]], r["share_first"], r["share_second"],
                "-" if r["first"] is None else "%.1f%%" % r["first"], "-" if r["lift_first"] is None else "%+.1f" % r["lift_first"],
                "-" if r["second"] is None else "%.1f%%" % r["second"], "-" if r["lift_second"] is None else "%+.1f" % r["lift_second"]))
    L += ["", "Per market group, single-group lift (first / second half, points):", "",
          "| level | group | " + " | ".join(list(MGROUPS)) + " |", "|---|---|" + "---|" * len(MGROUPS)]
    for lv in LEVELS:
        for j, g in enumerate(GNAMES):
            cells = []
            for sc in MGROUPS:
                r = L1[lv][sc][j]
                cells.append("-" if r["lift_first"] is None or r["lift_second"] is None else "%+.1f / %+.1f" % (r["lift_first"], r["lift_second"]))
            L.append("| %s | %s | %s |" % (lv, GTITLE[g], " | ".join(cells)))
    L += ["", "## After costs: the top buckets traded (stop -0.5 dATR, target +0.5 dATR, 72 h max, own fee a side, one "
          "position per market)", "", "| level | bucket | half | trades | won | R before costs | R after costs | per trade (% stake) | net $ |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, node in T.items():
        lv, bid = key.split("|")
        for hf in ("first", "second"):
            L.append("| %s | %s | %s | %s |" % (lv if hf == "first" else "", bid if hf == "first" else "", hf, fmt_tr(node["pooled"][hf])))
    L += ["", "Per market, second half (per trade after costs, trades; events per month in brackets):", "",
          "| level | bucket | " + " | ".join(ASSETS) + " |", "|---|---|" + "---|" * len(ASSETS)]
    for key, node in T.items():
        lv, bid = key.split("|")
        cells = []
        for a in ASSETS:
            m = node["markets"][a]["second"]
            cells.append(("%+.3f%% (%d) [%.1f]" % (m["exp_pct"], m["trades"], node["per_month"][a]["second"])) if m.get("trades") else "- [%.1f]" % node["per_month"][a]["second"])
        L.append("| %s | %s | %s |" % (lv, bid, " | ".join(cells)))
    L += ["", "Per market, first half:", "", "| level | bucket | " + " | ".join(ASSETS) + " |", "|---|---|" + "---|" * len(ASSETS)]
    for key, node in T.items():
        lv, bid = key.split("|")
        cells = []
        for a in ASSETS:
            m = node["markets"][a]["first"]
            cells.append(("%+.3f%% (%d) [%.1f]" % (m["exp_pct"], m["trades"], node["per_month"][a]["first"])) if m.get("trades") else "- [%.1f]" % node["per_month"][a]["first"])
        L.append("| %s | %s | %s |" % (lv, bid, " | ".join(cells)))
    L += ["", "## Every bucket, pooled (sorted by the lower half's hit rate; then the rest)", ""]
    for lv in LEVELS:
        L += ["### %s" % lv, "", "| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |", "|---|---|---|---|---|---|---|---|"]
        for bid, c in bucket_rows(A[lv]["pooled"]):
            L.append("| %s | %s | %s | %s |" % (bid, _h(c["first"]), _h(c["second"]), "yes" if c["bonf_both"] else ""))
        L.append("")
    L += ["## Every bucket per market group (top 8 by the lower half, then any passing Bonferroni in both halves)", ""]
    for lv in LEVELS:
        for sc in MGROUPS:
            rows = bucket_rows(A[lv][sc])
            keep = rows[:8] + [kv for kv in rows[8:] if kv[1]["bonf_both"]]
            L += ["### %s, %s" % (lv, sc), "", "| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |",
                  "|---|---|---|---|---|---|---|---|"]
            for bid, c in keep:
                L.append("| %s | %s | %s | %s |" % (bid, _h(c["first"]), _h(c["second"]), "yes" if c["bonf_both"] else ""))
            L.append("")
    L += ["## Checks", ""]
    for a, r in res.items():
        tc = r["truncation"]
        L.append("- %s: %d bars (%s to %s), fee %.2f%% a side, OI rows %d; excluded %s; truncation %d cuts, %d events "
                 "compared, %d mismatched event runs, %d mismatched flag arrays." % (
                     a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], r["oi_rows"],
                     "; ".join("%s %s" % (lv, ", ".join("%s %d" % kv for kv in ex.items())) for lv, ex in r["excluded"].items()),
                     tc["cuts"], tc["events_checked"], tc["mismatched_event_runs"], tc["mismatched_flag_arrays"]))
    L += ["", "Group 7 (open interest) uses Binance archive snapshots that the live engine only sees ~12-36 h later; "
          "it describes a live OI feed the engine does not have. Non-crypto volume changes source at each market's join "
          "(VOLUME_NOTE); USDJPY has no volume after its join, so group 4 rarely reads there.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- live scan (paper / untested)
def scan(now_ms=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    lines = ["H46 live confluence scan (PAPER, UNTESTED: no bucket is a validated setup; see study.md for each bucket's history)"]
    rows = []
    for a in ASSETS:
        try:
            df = data.load(a)
        except Exception as ex:
            lines.append("  %-8s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=420)]
        df = df[data.to_ms(df.index) + BAR_MS <= now_ms]
        crypto = a in CRYPTO
        try:
            oi = load_oi(a)
        except Exception:
            oi = None
        R = adr.readings(df, box=db.BOX)
        F = confluence(df, oi, crypto)
        i = R["n"] - 1
        day = R["ms"] // DAY_MS
        last_close = pd.Timestamp(int(R["ms"][i]) + BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - (int(R["ms"][i]) + BAR_MS)) / 3600000.0
        head = "  %-8s last close %s%s" % (a, last_close.strftime("%d %b %H:%M UTC"), " (stale %.1f h)" % age_h if age_h > 1 else "")
        found = []
        for lv in LEVELS:
            for ev in events(R, F, lv):
                j = ev["i"]
                if day[j] != day[i]:
                    continue
                when = pd.Timestamp(int(R["ms"][j]) + BAR_MS, unit="ms", tz="UTC").strftime("%H:%M UTC")
                yes = [g for g in GNAMES if ev[g]]
                navail = 7 if ev["read7"] else 6
                found.append("%s %s at %s: confluence %d of %d (%s)%s" % (
                    lv, "UP" if ev["side"] > 0 else "DOWN", when, ev["count"], navail, ", ".join(yes) or "none",
                    "" if crypto is False or ev["read7"] else "; OI no read (archive lag)"))
                rows.append({"asset": a, "level": lv, "side": ev["side"], "close_utc": when, "count": ev["count"],
                             "groups": yes, "oi_read": ev["read7"]})
        lines.append(head + ("; " + "; ".join(found) if found else "; no daily-level break today yet") + ".")
    lines.append("  (paper / untested; H46 found no 70% setup unless study.md says otherwise)")
    return rows, lines


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H46 confluence study")
    results, E = {}, []
    try:
        for a in ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a], ev = run_asset(a)
            E += ev
            log("%s: done in %.0f s; %d events; truncation %s" % (a, time.time() - t0, len(ev), results[a]["truncation"]))
    finally:
        release_lock()
    A = aggregate(E)
    top = top_buckets(A, 10)
    T = trade_table(E, top)
    setups = []
    for lv in LEVELS:
        for sc in SCOPES:
            for bid, c in A[lv][sc]["buckets"].items():
                if c["setup70"]:
                    setups.append("%s / %s / %s: first %.1f%% of %d, second %.1f%% of %d" % (
                        lv, sc, bid, c["first"]["hit_pct"], c["first"]["resolved"], c["second"]["hit_pct"], c["second"]["resolved"]))
    best = None
    if top:
        lv, bid = top[0]
        c = A[lv]["pooled"]["buckets"][bid]
        best = "%s / %s: %.1f%% (first %.1f%% of %d, second %.1f%% of %d)" % (
            lv, bid, c["min_hit"], c["first"]["hit_pct"], c["first"]["resolved"], c["second"]["hit_pct"], c["second"]["resolved"])
    nb = sum(1 for lv in LEVELS for sc in SCOPES for c in A[lv][sc]["buckets"].values() if c["bonf_both"])
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC, "n_tests": N_TESTS,
         "alpha": ALPHA, "buckets": [b for b, _f in BUCKETS], "agg": A, "top": top, "trades": T, "lift": single_lift(A),
         "setups70": setups, "best_min": best, "bonf_both_count": nb, "results": results}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    cols = ["asset", "mgroup", "level", "i", "side", "entry_ms", "half", "datr", "entry", "hit", "ambiguous", "why",
            "count", "all", "read7"] + GNAMES
    pd.DataFrame([dict((k, e.get(k)) for k in cols) for e in E]).to_csv(os.path.join(OUT, "events.csv"), index=False)
    log("done: %d events, %d 70%% setups, %d Bonferroni-both buckets" % (len(E), len(setups), nb))
    return S


def load_study():
    with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
        S = json.load(fh)
    S["top"] = [tuple(x) for x in S["top"]]
    return S


if __name__ == "__main__":
    if "--report" in sys.argv:
        S = load_study()
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(S))
    elif "--scan" in sys.argv:
        print("\n".join(scan()[1]))
    else:
        main()
        print("\n".join(scan()[1]))
