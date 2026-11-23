# -*- coding: utf-8 -*-
"""H107: BTC and ETH, a long after a capitulation low that rebounds (rule A), and the same with shorts paying funding
(rule B). Research only; registered in research/HYPOTHESES.md (H107) before any H107 number on history was computed.
Reads only the 15-minute bar files and the funding files; uses no evidence store, no fits, no engine book. Changes
nothing in the engine, the books or the vault.

    py -3 -X utf8 research/h107_capitulation_rebound.py --data-dir <folder with btcusdt_15m.csv, ethusdt_15m.csv,
                                                         btcusdt_funding.csv, ethusdt_funding.csv>

History run: every input is CUT at 2025-11-10 23:45 UTC (the bar opening then) BEFORE anything is computed, and a trade
must end by that bar. The event mode (`--event`) reads bars from 2026-08-01 only and reports the rules on
19-23 Nov 2026 (the event the rules were shaped on), descriptive only.
"""
import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, indicators as ind  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h107_capitulation_rebound")
COINS = ("BTCUSDT", "ETHUSDT")
START = "2019-10-01 00:00"           # first deciding bar (funding exists from 2019-09-10; 30-day low needs 30 days)
CUT = "2025-11-10 23:45"             # last bar that may be read (the sealed holdout starts 2025-11-11 00:00)
MID = "2023-06-08 00:00"             # halves split by the deciding bar
EVENT_FROM, EVENT_LOAD = "2026-11-19 00:00", "2026-08-01 00:00"
FEE = float(CFG["cost_side"])        # 0.10% a side (BTC and ETH)
STOP_ATR = float(CFG["stop_units"]) * float(CFG["barrier_atr"])   # 2 x 1.5 = 3 x ATR(14) of the 1h chart
B, SEED = 10000, 20261123
REG = {"look": 16, "low_days": 30, "drop_days": 7, "drop": 0.10, "bounce_atr": 2.0, "hold": 192}
MIN_ALL, MIN_HALF = 60, 20
ALPHA = 0.05


# ------------------------------------------------------------------------------------------------- data
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(coin, ddir, start=None, end=None):
    """-> (15m bars, funding series keyed by the time it was set), both cut at `end` (inclusive) before use."""
    df = data.load(coin, os.path.join(ddir, coin.lower() + "_15m.csv"))
    f = pd.read_csv(os.path.join(ddir, coin.lower() + "_funding.csv"))
    fund = pd.Series(f["rate"].values.astype(float), index=pd.to_datetime(f["ts_ms"], unit="ms", utc=True)).sort_index()
    if start is not None:
        df = df.loc[pd.Timestamp(start, tz="UTC"):]
    if end is not None:
        e = pd.Timestamp(end, tz="UTC")
        df = df.loc[:e]
        # a funding rate is known from its own time on; nothing set after the last bar's close may be read
        fund = fund.loc[:e + pd.Timedelta(minutes=15)]
    return df, fund


def features(df, fund, p=REG):
    """Every reading as known at each 15m bar's close. -> dict of arrays."""
    t = df.index
    o, h, l, c = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    h1 = data.resample(df, "1h")
    atr1h = data.htf_on_15(df, "1h", ind.atr_wilder(h1)).values.astype(float)
    low16 = pd.Series(l).rolling(p["look"], min_periods=p["look"]).min().values
    lowN = pd.Series(l, index=t).rolling("%dD" % p["low_days"]).min().values
    have = t >= t[0] + pd.Timedelta(days=p["low_days"])          # a full 30-day window behind the bar
    j = t.searchsorted(t - pd.Timedelta(days=p["drop_days"]), side="right") - 1
    cref = np.where(j >= 0, c[np.maximum(j, 0)], np.nan)
    close_ms = data.to_ms(t) + int(CFG["bar_ms"])
    fms = data.to_ms(fund.index)
    fi = np.searchsorted(fms, close_ms, side="right") - 1        # last funding set at or before the bar's close
    fv = np.concatenate([fund.values.astype(float), [np.nan]])   # no funding set yet -> NaN (ETH's file starts 2019-11-27)
    fund_last = np.where(fi >= 0, fv[np.where(fi >= 0, fi, len(fv) - 1)], np.nan)
    with np.errstate(invalid="ignore"):
        fresh = have & (low16 <= lowN)
        drop = low16 / cref - 1.0 <= -p["drop"]
        bounce = c - low16 >= p["bounce_atr"] * atr1h
        trig = fresh & drop & bounce & np.isfinite(atr1h)
        neg = fund_last < 0
    prev = np.concatenate([[True], trig[:-1]])
    onset = trig & ~prev
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "atr1h": atr1h, "low16": low16, "lowN": lowN, "cref": cref,
            "fund": fund_last, "A": onset, "B": onset & neg, "trig": trig}


# ------------------------------------------------------------------------------------------------- the trade
def walk(fx, ks, hold):
    """The registered long decided at each close k in `ks` (bars k+1 .. k+hold must exist). Vectorised.
    -> dict of arrays: r (net R), pct (net), xbar (exit bar), how (0 stop, 1 T1 then entry, 2 T1+T2, 3 T1 then time,
    4 time), entry, stop."""
    o, h, l, c, atr = fx["o"], fx["h"], fx["l"], fx["c"], fx["atr1h"]
    m = len(ks)
    out = {k: np.full(m, np.nan) for k in ("r", "pct", "entry", "stop")}
    out["xbar"], out["how"] = np.full(m, -1, int), np.full(m, -1, int)
    J = np.arange(hold)
    for s in range(0, m, 5000):
        k = np.asarray(ks[s:s + 5000], int)
        P = o[k + 1]
        R = STOP_ATR * atr[k]
        S, T1, T2 = P - R, P + R, P + 2 * R
        idx = k[:, None] + 1 + J[None, :]
        L, H, O, C = l[idx], h[idx], o[idx], c[idx]
        rows = np.arange(len(k))

        def first(mask):
            return np.where(mask.any(1), mask.argmax(1), hold)
        js = first(L <= S[:, None])                                    # the stop is looked at first in a bar
        j1 = first(H >= T1[:, None])
        A = (js < hold) & (js <= j1)                                   # stopped before (or in the bar of) Target 1
        Bm = (~A) & (j1 < hold)
        fillA = np.minimum(O[rows, np.minimum(js, hold - 1)], S)       # at the stop, or at the open below it
        after = J[None, :] > j1[:, None]                               # stop at the entry from the bar after T1
        jb = first((L <= P[:, None]) & after)
        j2 = first((H >= T2[:, None]) & (J[None, :] >= j1[:, None]))
        same = j2 == j1
        be_first = (~same) & (jb < hold) & (jb <= j2)
        t2_first = (~same) & (~be_first) & (j2 < hold)
        restX = np.where(same | t2_first, T2, np.where(be_first, np.minimum(O[rows, np.minimum(jb, hold - 1)], P),
                                                       C[:, -1]))
        restJ = np.where(same, j1, np.where(be_first, jb, np.where(t2_first, j2, hold - 1)))
        Xfull = np.where(A, fillA, C[:, -1])
        gross = np.where(Bm, 0.5 * (T1 - P) + 0.5 * (restX - P), Xfull - P)
        fees = FEE * np.where(Bm, P + 0.5 * T1 + 0.5 * restX, P + Xfull)
        sl = slice(s, s + len(k))
        out["r"][sl] = (gross - fees) / R
        out["pct"][sl] = (gross - fees) / P
        out["xbar"][sl] = k + 1 + np.where(A, js, np.where(Bm, restJ, hold - 1))
        out["how"][sl] = np.where(A, 0, np.where(Bm, np.where(be_first, 1, np.where(same | t2_first, 2, 3)), 4))
        out["entry"][sl], out["stop"][sl] = P, S
    return out


def walk_loop(fx, k, hold):
    """The same trade, bar by bar (a cross-check of `walk`)."""
    o, h, l, c = fx["o"], fx["h"], fx["l"], fx["c"]
    P = o[k + 1]
    R = STOP_ATR * fx["atr1h"][k]
    stop, T1, T2, q, got, fees = P - R, P + R, P + 2 * R, 1.0, 0.0, FEE * P
    t1 = False
    for j in range(k + 1, k + 1 + hold):
        if l[j] <= stop:
            x = min(o[j], stop)
            got += q * (x - P)
            fees += FEE * q * x
            return (got - fees) / R
        new_t1 = False
        if not t1 and h[j] >= T1:
            got += 0.5 * (T1 - P)
            fees += FEE * 0.5 * T1
            q, t1, new_t1 = 0.5, True, True
        if t1 and h[j] >= T2:
            got += q * (T2 - P)
            fees += FEE * q * T2
            return (got - fees) / R
        if new_t1:
            stop = P
    x = c[k + hold]
    got += q * (x - P)
    fees += FEE * q * x
    return (got - fees) / R


def trades_of(fx, rule, k0, k1, hold):
    """One trade at a time: a signal at k is taken only if k >= the exit bar of the previous trade and k+hold <= k1."""
    ks = np.flatnonzero(fx[rule][k0:k1 + 1]) + k0
    ks = ks[ks + hold <= k1]
    ok = np.isfinite(fx["atr1h"][ks]) & (fx["atr1h"][ks] > 0)
    ks = ks[ok]
    w = walk(fx, ks, hold)
    taken, last = [], -1
    for i, k in enumerate(ks):
        if k < last:
            continue
        taken.append(i)
        last = int(w["xbar"][i])
    return ks[taken], dict((x, v[taken]) for x, v in w.items()), int(len(ks) - len(taken))


# ------------------------------------------------------------------------------------------------- statistics
def month_of(t):
    return int(t.year * 100 + t.month)


def all_months(a, z):
    ms = pd.period_range(pd.Timestamp(a).to_period("M"), pd.Timestamp(z).to_period("M"), freq="M")
    return [p.year * 100 + p.month for p in ms]


def boot(rows, months, D, key="r"):
    """Month-clustered bootstrap of the mean of `key`. -> obs, 95% interval, one-sided p for > 0 (shifted)."""
    if not rows:
        return None
    mi = dict((m_, i) for i, m_ in enumerate(months))
    S, N = np.zeros(len(months)), np.zeros(len(months))
    for t in rows:
        S[mi[t["month"]]] += t[key]
        N[mi[t["month"]]] += 1
    obs = S.sum() / N.sum()
    ss, nn = S[D].sum(1), N[D].sum(1)
    v = ss[nn > 0] / nn[nn > 0]
    p = (1 + np.sum(v - obs >= obs)) / (len(v) + 1)
    return {"obs": float(obs), "lo": float(np.percentile(v, 2.5)), "hi": float(np.percentile(v, 97.5)), "p": float(p),
            "draws": int(len(v))}


def summary(rows):
    if not rows:
        return {"n": 0}
    r = np.array([t["r"] for t in rows])
    srt = sorted(rows, key=lambda t: t["time"])
    run = worst_run = 0
    for t in srt:
        run = run + 1 if t["r"] < 0 else 0
        worst_run = max(worst_run, run)
    cum = np.cumsum([t["r"] for t in srt])
    dd = float(np.min(cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:])) if len(cum) else 0.0
    hows = dict((n_, int(sum(1 for t in rows if t["how"] == i))) for i, n_ in
                enumerate(("stop", "T1_then_entry", "T1_T2", "T1_then_time", "time")))
    return {"n": int(len(r)), "won_pct": float((r > 0).mean() * 100), "mean_r": float(r.mean()), "sum_r": float(r.sum()),
            "median_r": float(np.median(r)), "mean_pct": float(np.mean([t["pct"] for t in rows]) * 100),
            "longest_losing_run": int(worst_run), "worst_fall_cum_r": dd, "exits": hows,
            "months_with_a_trade": int(len(set(t["month"] for t in rows)))}


def holm(ps):
    """Holm-adjusted p-values, same order as given."""
    m = len(ps)
    order = np.argsort(ps)
    adj, run = np.zeros(m), 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


# ------------------------------------------------------------------------------------------------- history run
def coin_frame(coin, ddir, p=REG):
    df, fund = load(coin, ddir, end=CUT)
    assert str(df.index[-1])[:16] <= CUT and (len(fund) == 0 or fund.index[-1] <= pd.Timestamp(CUT, tz="UTC")
                                                + pd.Timedelta(minutes=15)), "holdout read"
    fx = features(df, fund, p)
    t = fx["t"]
    k0 = int(t.searchsorted(pd.Timestamp(START, tz="UTC")))
    k1 = len(t) - 1
    return fx, k0, k1


def baseline(fx, k0, k1, hold, months_needed):
    """Mean R of the same trade entered at EVERY bar of each needed calendar month (window inside the period)."""
    t = fx["t"]
    ks = np.arange(k0, k1 - hold + 1)
    ks = ks[np.isfinite(fx["atr1h"][ks]) & (fx["atr1h"][ks] > 0)]
    mo = np.asarray(t[ks].year * 100 + t[ks].month)
    out = {}
    for m_ in months_needed:
        sel = ks[mo == m_]
        if len(sel):
            out[int(m_)] = float(np.mean(walk(fx, sel, hold)["r"]))
    return out


def rule_rows(coin, fx, rule, k0, k1, hold):
    ks, w, skipped = trades_of(fx, rule, k0, k1, hold)
    t = fx["t"]
    rows = []
    for i, k in enumerate(ks):
        rows.append({"coin": coin, "k": int(k), "time": str(t[k])[:16], "month": month_of(t[k]),
                     "half": 1 if t[k] < pd.Timestamp(MID, tz="UTC") else 2, "r": float(w["r"][i]),
                     "pct": float(w["pct"][i]), "how": int(w["how"][i]), "entry": float(w["entry"][i]),
                     "stop": float(w["stop"][i]), "exit_time": str(t[int(w["xbar"][i])])[:16],
                     "funding": float(fx["fund"][k]), "drop_pct": float((fx["low16"][k] / fx["cref"][k] - 1) * 100)})
    return rows, skipped


def lookahead_test(coin, ddir, fx, k0, k1, rows, n_random=40, seed=SEED):
    """Recompute the readings on data cut at bar k (funding at its close) for every signal bar and some random bars;
    every flag and the stop must be identical to the full-run value."""
    df, fund = load(coin, ddir, end=CUT)
    rng = np.random.default_rng(seed)
    sig = sorted(set([r_["k"] for r_ in rows] + list(np.flatnonzero(fx["trig"][k0:k1 + 1]) + k0)[:200]))
    rnd = list(rng.integers(k0, k1 + 1, n_random))
    bad = []
    for k in sig + rnd:
        k = int(k)
        cut_t = fx["t"][k]
        g = features(df.iloc[:k + 1], fund.loc[:cut_t + pd.Timedelta(minutes=15)])
        for key in ("A", "B", "trig"):
            if bool(g[key][-1]) != bool(fx[key][k]):
                bad.append((k, key))
        if not np.isclose(g["atr1h"][-1], fx["atr1h"][k], rtol=1e-9, equal_nan=True):
            bad.append((k, "atr1h"))
    return {"bars_checked": len(sig) + len(rnd), "mismatches": bad[:20], "n_mismatch": len(bad)}


def run_history(ddir, log=print):
    t0 = time.time()
    res = {"registered": REG, "start": START, "cut": CUT, "mid": MID, "fee_side": FEE, "stop_atr1h": STOP_ATR,
           "bootstrap": {"draws": B, "seed": SEED}, "files": {}, "rules": {}}
    for c_ in COINS:
        for suf in ("_15m.csv", "_funding.csv"):
            pth = os.path.join(ddir, c_.lower() + suf)
            res["files"][os.path.basename(pth)] = md5(pth)
    frames = {}
    for c_ in COINS:
        fx, k0, k1 = coin_frame(c_, ddir)
        frames[c_] = (fx, k0, k1)
        log("%s: bars %s .. %s (decide from %s)" % (c_, str(fx["t"][0])[:16], str(fx["t"][k1])[:16], str(fx["t"][k0])[:16]))
    months = all_months(START, CUT)
    rng = np.random.default_rng(SEED)
    D = rng.integers(0, len(months), size=(B, len(months)))
    m1 = [m_ for m_ in months if m_ < 202306]
    m2 = [m_ for m_ in months if m_ >= 202306]
    hold = REG["hold"]
    pvals = {}
    for rule in ("A", "B"):
        rows, skipped, checks = [], {}, {}
        for c_ in COINS:
            fx, k0, k1 = frames[c_]
            rr, sk = rule_rows(c_, fx, rule, k0, k1, hold)
            skipped[c_] = sk
            # cross-check the vectorised walk bar by bar on every trade
            diffs = [abs(walk_loop(fx, r_["k"], hold) - r_["r"]) for r_ in rr]
            checks[c_] = float(max(diffs)) if diffs else 0.0
            base = baseline(fx, k0, k1, hold, sorted(set(r_["month"] for r_ in rr)))
            for r_ in rr:
                r_["baseline"] = base.get(r_["month"], np.nan)
                r_["excess"] = r_["r"] - r_["baseline"]
            rows += rr
        cell = {}
        parts = {"all": rows, "h1": [r_ for r_ in rows if r_["half"] == 1], "h2": [r_ for r_ in rows if r_["half"] == 2]}
        for pname, pr in parts.items():
            for cname, cr in (("pooled", pr), ("BTC", [r_ for r_ in pr if r_["coin"] == "BTCUSDT"]),
                              ("ETH", [r_ for r_ in pr if r_["coin"] == "ETHUSDT"])):
                ms = months if pname == "all" else (m1 if pname == "h1" else m2)
                Dp = D if pname == "all" else rng.integers(0, len(ms), size=(B, len(ms)))
                cell["%s_%s" % (cname, pname)] = dict(summary(cr), boot_r=boot(cr, ms, Dp, "r"),
                                                      boot_excess=boot(cr, ms, Dp, "excess"))
        pvals[rule] = cell["pooled_all"]["boot_r"]["p"] if cell["pooled_all"].get("boot_r") else 1.0
        res["rules"][rule] = {"cells": cell, "signals_skipped_while_a_trade_was_open": skipped,
                              "walk_crosscheck_max_abs_diff_r": checks, "trades": rows}
    adj = holm([pvals["A"], pvals["B"]])
    for i, rule in enumerate(("A", "B")):
        cell = res["rules"][rule]["cells"]
        pa, h1, h2 = cell["pooled_all"], cell["pooled_h1"], cell["pooled_h2"]
        c = {"n_all>=60": pa["n"] >= MIN_ALL, "n_h1>=20": h1["n"] >= MIN_HALF, "n_h2>=20": h2["n"] >= MIN_HALF,
             "mean_r_h1>0": h1["n"] > 0 and h1["mean_r"] > 0, "mean_r_h2>0": h2["n"] > 0 and h2["mean_r"] > 0,
             "mean_r_BTC>0": cell["BTC_all"]["n"] > 0 and cell["BTC_all"]["mean_r"] > 0,
             "mean_r_ETH>0": cell["ETH_all"]["n"] > 0 and cell["ETH_all"]["mean_r"] > 0,
             "holm_p<0.05": bool(adj[i] < ALPHA),
             "excess_pooled>0": bool(pa.get("boot_excess") and pa["boot_excess"]["obs"] > 0)}
        enough = c["n_all>=60"] and c["n_h1>=20"] and c["n_h2>=20"]
        verdict = "PASS" if all(c.values()) else ("TOO FEW TRADES TO JUDGE (no pass)" if not enough else "FAIL")
        res["rules"][rule].update({"p_raw": float(pvals[rule]), "p_holm": float(adj[i]), "checks": c, "verdict": verdict})
    res["lookahead_test"] = {}
    for c_ in COINS:
        fx, k0, k1 = frames[c_]
        rows = [r_ for r_ in res["rules"]["A"]["trades"] if r_["coin"] == c_]
        res["lookahead_test"][c_] = lookahead_test(c_, ddir, fx, k0, k1, rows)
    res["descriptive_sensitivity"] = sensitivity(ddir, months, log)
    res["seconds"] = round(time.time() - t0, 1)
    return res


def sensitivity(ddir, months, log=print):
    """Descriptive only, decides nothing: one setting moved at a time around the registered rule."""
    variants = [("bounce 1.5 ATR", dict(REG, bounce_atr=1.5)), ("bounce 2.5 ATR", dict(REG, bounce_atr=2.5)),
                ("drop 8%", dict(REG, drop=0.08)), ("drop 12%", dict(REG, drop=0.12)),
                ("hold 24h", dict(REG, hold=96)), ("hold 96h", dict(REG, hold=384))]
    out = {}
    for name, p in variants:
        for rule in ("A", "B"):
            rows = []
            for c_ in COINS:
                df, fund = load(c_, ddir, end=CUT)
                fx = features(df, fund, p)
                k0 = int(fx["t"].searchsorted(pd.Timestamp(START, tz="UTC")))
                rr, _ = rule_rows(c_, fx, rule, k0, len(fx["t"]) - 1, p["hold"])
                rows += rr
            out["%s | %s" % (rule, name)] = {
                "all": summary(rows), "h1": summary([r_ for r_ in rows if r_["half"] == 1]),
                "h2": summary([r_ for r_ in rows if r_["half"] == 2])}
    return out


# ------------------------------------------------------------------------------------------------- event (descriptive)
def run_event(ddir):
    """The two rules on 19-23 Nov 2026, the event they were shaped on. Bars read from 2026-08-01 only."""
    out = {}
    for c_ in COINS:
        df, fund = load(c_, ddir, start=EVENT_LOAD)
        fx = features(df, fund)
        t = fx["t"]
        k0 = int(t.searchsorted(pd.Timestamp(EVENT_FROM, tz="UTC")))
        n = len(t)
        sig = {}
        for rule in ("A", "B"):
            ks = list(np.flatnonzero(fx[rule][k0:]) + k0)
            trades = []
            last = -1
            for k in ks:
                if k < last or k + 1 >= n:
                    continue
                hold = min(REG["hold"], n - 1 - k)
                w = walk(fx, np.array([k]), hold)
                done = hold == REG["hold"] or int(w["how"][0]) in (0, 1, 2)
                trades.append({"decided_bar_open": str(t[k])[:16], "decided_close_utc": str(t[k] + pd.Timedelta(minutes=15))[:16],
                               "entry": float(w["entry"][0]), "stop": float(w["stop"][0]),
                               "target_1": float(w["entry"][0] + (w["entry"][0] - w["stop"][0])),
                               "target_2": float(w["entry"][0] + 2 * (w["entry"][0] - w["stop"][0])),
                               "funding_last": float(fx["fund"][k]), "drop_pct": float((fx["low16"][k] / fx["cref"][k] - 1) * 100),
                               "bounce_atr": float((fx["c"][k] - fx["low16"][k]) / fx["atr1h"][k]),
                               "r_so_far_or_final": float(w["r"][0]), "finished": bool(done),
                               "how": ["stop", "T1 then entry", "T1+T2", "T1 then time", "time"][int(w["how"][0])],
                               "marked_or_exit_bar": str(t[int(w["xbar"][0])])[:16]})
                last = int(w["xbar"][0]) if done else n
            sig[rule] = trades
        out[c_] = {"last_bar": str(t[-1])[:16], "signals": sig}
    return out


# ------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--event", action="store_true", help="only the descriptive event read (19-23 Nov 2026)")
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    if a.event:
        ev = run_event(a.data_dir)
        with open(os.path.join(OUT, "event.json"), "w") as fh:
            json.dump(ev, fh, indent=1)
        print(json.dumps(ev, indent=1))
        return
    res = run_history(a.data_dir)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    for rule in ("A", "B"):
        r = res["rules"][rule]
        print(rule, r["verdict"], "p", round(r["p_raw"], 4), "holm", round(r["p_holm"], 4), r["checks"])
        for k, v in r["cells"].items():
            print("  ", k, dict((x, (round(y, 3) if isinstance(y, float) else y)) for x, y in v.items()
                                if x in ("n", "won_pct", "mean_r", "sum_r")), v.get("boot_r"))
    print("lookahead", res["lookahead_test"], "crosscheck", {r: res["rules"][r]["walk_crosscheck_max_abs_diff_r"] for r in "AB"})


if __name__ == "__main__":
    main()
