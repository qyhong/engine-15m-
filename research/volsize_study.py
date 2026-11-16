# -*- coding: utf-8 -*-
"""H52, SIZE BY EXPECTED MOVE: scale position size by a volatility forecast, entries and exits unchanged.
PAPER RESEARCH ONLY. Registered before any code or number: research/hypotheses_pending/H52.md (16 Nov 2026, 09:50 UTC).

  * one forecast, no fitted coefficient: equal-weight HAR of 15m squared log returns over B, 5B, 22B bars
    (B = the market's bars per trading day), sigma = sqrt(B * f) = the forecast daily volatility;
  * reference m = median of sigma at UTC-day-end bars over the trailing 365 calendar days (>= 60 day-ends), tercile
    cuts = the 33rd / 67th percentiles of the same set; all known at the decision bar;
  * PRIMARY decision stream = the main book's own replayed trades (laptop: `--replay`, read-only from data/evcache,
    every array cut at the seal) -> research/out/volsize/main_trades.json; SECONDARY (descriptive) = daily 30-day
    momentum sign, re-sized daily;
  * 7 sizing rows S0..S6 (S0 constant notional = baseline), $10,000 a market, not compounded, own fee a side;
  * development rows before 2025-11-11 00:00 UTC only; results from 2020-01-01; halves split 2023-06-07.

    py -3 research/volsize_study.py --replay [--group crypto]   LAPTOP ONLY: replay the main book, write main_trades.json
    py -3 research/volsize_study.py                             the sizing study (server): study.json + study.md
    py -3 research/volsize_study.py --report                    rewrite study.md from study.json
"""
import argparse
import gc
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

from engine15 import data, playbook as pb  # noqa: E402

REGISTERED_UTC = "2026-11-16 09:50 UTC"
START, SPLIT, SEAL = "2020-01-01", "2023-06-07", "2025-11-11"
ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")
OUT = os.path.join(ROOT, "research", "out", "volsize")
TRADES_FILE = os.path.join(OUT, "main_trades.json")
CAPITAL = 10000.0
REF_DAYS, REF_MIN = 365, 60
MOM_DAYS = 30
DAY_MS = 86400000
BAR_MS = 900000

VARIANTS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6")
VDESC = {"S0": "constant notional, w = 1 (baseline)",
         "S1": "inverse volatility, w = clip(m / sigma, 0.25, 4)",
         "S2": "inverse variance, w = clip((m / sigma)^2, 0.25, 4)",
         "S3": "half-strength inverse volatility, w = clip(sqrt(m / sigma), 0.25, 4)",
         "S4": "cut only, w = min(1, m / sigma), floor 0.25",
         "S5": "top-tercile cut, w = 0.5 above the trailing 67th percentile, else 1",
         "S6": "three regimes, w = 1.5 / 1 / 0.5 by trailing terciles"}
TESTED = VARIANTS[1:]
BONF = 0.05 / len(TESTED)


# =====================================================================================
# the forecast (closed bars only)
# =====================================================================================
def load_dev(asset):
    df = data.load(asset)
    return df[df.index < pd.Timestamp(SEAL, tz="UTC")]


def bars_per_day(index):
    """B: the median count of 15m bars per UTC calendar day with any bar (a structural session constant)."""
    day = np.asarray(data.to_ms(index)) // DAY_MS
    _, cnt = np.unique(day, return_counts=True)
    return int(np.median(cnt))


def har_sigma(close, B):
    """sigma_i = sqrt(B * (v1 + v5 + v22) / 3), v_k = mean squared 15m log return over the last k*B bars <= i."""
    c = np.asarray(close, float)
    r = np.full(len(c), np.nan)
    r[1:] = np.log(c[1:] / c[:-1])
    r2 = np.where(np.isfinite(r), r * r, 0.0)
    cs = np.concatenate([[0.0], np.cumsum(r2)])                 # cs[k] = sum of r2[0..k-1]; r2[0] = 0 (no return)
    n = len(c)
    out = np.zeros(n)
    idx = np.arange(n)
    ok = np.ones(n, bool)
    for k in (1, 5, 22):
        L = k * B
        lo = idx - L + 1
        good = lo >= 1                                          # needs L real returns (bars 1..i)
        v = np.where(good, (cs[idx + 1] - cs[np.maximum(lo, 0)]) / L, np.nan)
        out = out + v
        ok &= good
    f = out / 3.0
    return np.where(ok, np.sqrt(B * f), np.nan)


def day_ends(index):
    """Bool mask of the last bar of each UTC calendar day with bars, and each bar's day number."""
    day = np.asarray(data.to_ms(index)) // DAY_MS
    end = np.ones(len(day), bool)
    end[:-1] = day[1:] != day[:-1]
    return end, day


def reference(sig, times_ms, end_mask, at):
    """For decision bars `at`: (m, q33, q67) from sigma at day-end bars strictly BEFORE the decision bar with open time
    in (t - 365 d, t), >= 60 of them (else NaN). A day-end bar j < i is known as one by bar i (bar j + 1 <= i is in a
    later day), so nothing after the decision bar is read."""
    e_idx = np.where(end_mask & np.isfinite(sig))[0]
    e_t = np.asarray(times_ms)[e_idx]
    e_s = sig[e_idx]
    m = np.full(len(at), np.nan)
    q33 = np.full(len(at), np.nan)
    q67 = np.full(len(at), np.nan)
    for k, i in enumerate(np.asarray(at, int)):
        t = times_ms[i]
        hi = int(np.searchsorted(e_t, t, side="left"))
        lo = int(np.searchsorted(e_t, t - REF_DAYS * DAY_MS, side="right"))
        if hi - lo >= REF_MIN:
            v = e_s[lo:hi]
            m[k] = np.median(v)
            q33[k], q67[k] = np.percentile(v, [100.0 / 3.0, 200.0 / 3.0])
    return m, q33, q67


def weight(v, s, m, q33, q67):
    """The size multiplier of variant v from sigma s and the reference (m, q33, q67); 1 when there is no reference."""
    s, m, q33, q67 = (np.asarray(x, float) for x in (s, m, q33, q67))
    ok = np.isfinite(s) & np.isfinite(m) & (s > 0)
    x = np.where(ok, m / np.where(ok, s, 1.0), 1.0)
    if v == "S0":
        w = np.ones_like(x)
    elif v == "S1":
        w = np.clip(x, 0.25, 4.0)
    elif v == "S2":
        w = np.clip(x * x, 0.25, 4.0)
    elif v == "S3":
        w = np.clip(np.sqrt(x), 0.25, 4.0)
    elif v == "S4":
        w = np.clip(np.minimum(1.0, x), 0.25, 1.0)
    elif v == "S5":
        w = np.where(ok & (s > q67), 0.5, 1.0)
    elif v == "S6":
        w = np.where(ok & (s < q33), 1.5, np.where(ok & (s > q67), 0.5, 1.0))
    else:
        raise ValueError(v)
    return np.where(ok, w, 1.0)


def forecast_quality(df, sig, B):
    """Per valid day d (>= B/2 bars): sigma at d's last bar vs the next valid day's (high - low) / d's last close."""
    end, day = day_ends(df.index)
    h, l, c = (df[k].values.astype(float) for k in ("high", "low", "close"))
    days, first = np.unique(day, return_index=True)
    last = np.r_[first[1:] - 1, len(day) - 1]
    cnt = last - first + 1
    valid = cnt >= B / 2.0
    rows = []
    vd = np.where(valid)[0]
    for a, b in zip(vd[:-1], vd[1:]):
        i_end = last[a]
        rng = (h[first[b]:last[b] + 1].max() - l[first[b]:last[b] + 1].min()) / c[i_end]
        rows.append((int(days[b]) * DAY_MS, sig[i_end], rng))
    t = pd.DataFrame(rows, columns=["t_ms", "f", "rng"]).dropna()
    t = t[(t.f > 0) & (t.rng > 0) & (t.t_ms >= _ms(START))]
    res = {}
    for name, part in (("first_half", t[t.t_ms < _ms(SPLIT)]), ("second_half", t[t.t_ms >= _ms(SPLIT)]), ("all", t)):
        if len(part) < 20:
            res[name] = {"n": int(len(part))}
            continue
        sp = float(np.corrcoef(part.f.rank(), part.rng.rank())[0, 1])
        pl = float(np.corrcoef(np.log(part.f), np.log(part.rng))[0, 1])
        res[name] = {"n": int(len(part)), "spearman": round(sp, 4), "pearson_log": round(pl, 4),
                     "mean_ratio_rng_to_f": round(float((part.rng / part.f).mean()), 3)}
    return res


def _ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10 ** 6)


# =====================================================================================
# decision streams -> per-bar P&L and exposure for one market and one variant
# =====================================================================================
def trade_pnl(o, c, trades, w, fee, n):
    """Per-bar P&L ($) and exposure (w * capital per bar held) of fixed trades, quantity set once at entry.
    trades: list of (i_in, i_out, side, p_in, p_out); entry at bar i_in's fill price, exit inside or at the open of
    bar i_out at p_out."""
    pnl = np.zeros(n)
    expo = np.zeros(n)
    for (i_in, i_out, s, p_in, p_out), wk in zip(trades, w):
        q = wk * CAPITAL / p_in
        if i_out == i_in:
            pnl[i_in] += q * s * (p_out - p_in)
        else:
            pnl[i_in] += q * s * (c[i_in] - p_in)
            if i_out - i_in > 1:
                pnl[i_in + 1:i_out] += q * s * (c[i_in + 1:i_out] - c[i_in:i_out - 1])
            pnl[i_out] += q * s * (p_out - c[i_out - 1])
        pnl[i_in] -= fee * q * p_in
        pnl[i_out] -= fee * q * p_out
        expo[i_in:max(i_out, i_in + 1)] += wk * CAPITAL
    return pnl, expo


def proxy_decisions(df, B):
    """Daily 30-day momentum sign at the last bar of each valid UTC day: (decision bar, side). The side reads closes
    <= the decision bar only; it fills at the next bar's open, the moment that bar shows the day has ended."""
    end, day = day_ends(df.index)
    tms = np.asarray(data.to_ms(df.index))
    c = df["close"].values.astype(float)
    days, first, cnt = np.unique(day, return_index=True, return_counts=True)
    last = first + cnt - 1
    out = []
    for k in range(len(days)):
        if cnt[k] < B / 2.0:
            continue
        i = int(last[k])
        j = int(np.searchsorted(tms, tms[i] - MOM_DAYS * DAY_MS, side="right")) - 1
        if j < 0:
            continue
        out.append((i, int(np.sign(c[i] / c[j] - 1.0))))
    return out


def proxy_pnl(o, c, decisions, w, fee, n, start_i):
    """Daily re-sized book: at the open after each decision bar the quantity becomes side * w * capital / open."""
    q = np.full(n, np.nan)
    q[:start_i] = 0.0
    for (i, s), wk in zip(decisions, w):
        if i + 1 < n and i + 1 >= start_i:
            q[i + 1] = s * wk * CAPITAL / o[i + 1]
    q = pd.Series(q).ffill().fillna(0.0).values
    qp = np.r_[0.0, q[:-1]]
    cp = np.r_[o[0], c[:-1]]
    pnl = qp * (o - cp) + q * (c - o) - fee * np.abs(q - qp) * o
    expo = np.abs(q) * o
    return pnl, expo


# =====================================================================================
# metrics
# =====================================================================================
def daily_series(index, pnl, cal):
    """Marked P&L per UTC calendar day on the calendar `cal` (days with no bar = 0)."""
    day = pd.DatetimeIndex(index).floor("D")
    s = pd.Series(pnl, index=day).groupby(level=0).sum()
    return s.reindex(cal, fill_value=0.0)


def sharpe(d):
    d = np.asarray(d, float)
    return float(d.mean() / d.std() * math.sqrt(365)) if len(d) > 10 and d.std() > 0 else None


def max_dd(d):
    eq = np.concatenate([[0.0], np.cumsum(d)])
    return float((np.maximum.accumulate(eq) - eq).max())


def seg_metrics(d, capital, expo_avg, trades=None, fees=None):
    sr = sharpe(d)
    dd = max_dd(d)
    ret = float(np.sum(d))
    return {"return_pct": round(100 * ret / capital, 2), "sharpe": None if sr is None else round(sr, 3),
            "max_dd_pct": round(100 * dd / capital, 2),
            "ret_over_dd": round(ret / dd, 3) if dd > 0 else None,
            "avg_exposure": None if expo_avg is None else round(expo_avg, 4),
            "trades": trades, "fees_pct": None if fees is None else round(100 * fees / capital, 2)}


def jk_memmel(d1, d2):
    """Jobson-Korkie test of equal Sharpe ratios with Memmel's (2003) correction; -> (z, two-sided p)."""
    a, b = np.asarray(d1, float), np.asarray(d2, float)
    T = len(a)
    if T < 30 or a.std() == 0 or b.std() == 0:
        return None, None
    s1, s2 = a.mean() / a.std(), b.mean() / b.std()
    rho = float(np.corrcoef(a, b)[0, 1])
    theta = 2 - 2 * rho + 0.5 * (s1 ** 2 + s2 ** 2 - 2 * s1 * s2 * rho ** 2)
    if theta <= 0:
        return None, None
    z = (s1 - s2) / math.sqrt(theta / T)
    p = math.erfc(abs(z) / math.sqrt(2))
    return round(float(z), 3), float(p)


# =====================================================================================
# the study (server)
# =====================================================================================
def load_main_trades():
    with open(TRADES_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def map_trades(df, recs):
    """main_trades.json records -> (i_in, i_out, side, p_in, p_out) on this market's bars (+ checks)."""
    tms = np.asarray(data.to_ms(df.index))
    pos = dict((int(t), k) for k, t in enumerate(tms))
    o = df["open"].values
    out, missing, open_match = [], 0, 0
    for r in recs:
        i_in, i_out = pos.get(int(r["t_in_ms"])), pos.get(int(r["t_out_ms"]))
        if i_in is None or i_out is None or i_out < i_in:
            missing += 1
            continue
        out.append((i_in, i_out, int(r["side"]), float(r["p_in"]), float(r["p_out"])))
        open_match += int(abs(float(r["p_in"]) / o[i_in] - 1) < 1e-9)
    return out, {"mapped": len(out), "unmapped": missing, "entry_at_bar_open": open_match}


def run_market(a, main_recs, log=print):
    df = load_dev(a)
    tms = np.asarray(data.to_ms(df.index))
    n = len(df)
    o, c = df["open"].values.astype(float), df["close"].values.astype(float)
    B = bars_per_day(df.index)
    sig = har_sigma(c, B)
    end, _ = day_ends(df.index)
    fee = pb.fee_side(a)
    fq = forecast_quality(df, sig, B)
    start_i = int(np.searchsorted(tms, _ms(START)))
    res = {"B": B, "fee_side": fee, "forecast": fq, "first_bar": str(df.index[0])[:16], "last_bar": str(df.index[-1])[:16]}
    streams = {}
    # primary: the main book's trades (decision bar = the bar before the entry bar)
    if main_recs is not None:
        tr, chk = map_trades(df, main_recs)
        tr = [t for t in tr if t[0] >= start_i]
        dec = np.array([t[0] - 1 for t in tr], int)
        m, q33, q67 = reference(sig, tms, end, dec) if len(dec) else (np.array([]),) * 3
        s_at = sig[dec] if len(dec) else np.array([])
        chk.update(trades_used=len(tr), no_reference=int(np.sum(~np.isfinite(m))) if len(dec) else 0)
        res["main_check"] = chk
        streams["main"] = {}
        for v in VARIANTS:
            w = weight(v, s_at, m, q33, q67) if len(dec) else np.array([])
            pnl, expo = trade_pnl(o, c, tr, w, fee, n)
            streams["main"][v] = {"pnl": pnl, "expo": expo, "w": w,
                                  "entry_t": np.array([tms[t[0]] for t in tr], np.int64), "fees": None}
    # secondary: daily 30-day momentum sign, re-sized daily
    dec = proxy_decisions(df, B)
    dec = [d for d in dec if d[0] + 1 >= start_i]
    di = np.array([d[0] for d in dec], int)
    m, q33, q67 = reference(sig, tms, end, di)
    s_at = sig[di]
    streams["proxy"] = {}
    for v in VARIANTS:
        w = weight(v, s_at, m, q33, q67)
        pnl, expo = proxy_pnl(o, c, dec, w, fee, n, start_i)
        streams["proxy"][v] = {"pnl": pnl, "expo": expo, "w": w, "entry_t": None, "fees": None}
    res["proxy_check"] = {"decisions": len(dec), "no_reference": int(np.sum(~np.isfinite(m))),
                          "long_share": round(float(np.mean([d[1] > 0 for d in dec])), 3)}
    log("%s: B=%d, fee %.5f, forecast spearman %s / %s" % (
        a, B, fee, fq["first_half"].get("spearman"), fq["second_half"].get("spearman")))
    return df.index, res, streams


def half_masks(cal):
    split = pd.Timestamp(SPLIT, tz="UTC")
    return {"first_half": cal < split, "second_half": cal >= split, "all": np.ones(len(cal), bool)}


def summarise(per_index, streams_by_mkt, cal):
    """-> {stream: {variant: {half: {pooled: m, markets: {a: m}, jk: (z, p)}}}}"""
    halves = half_masks(cal)
    bar_half = {}
    out = {}
    for st in ("main", "proxy"):
        mk = [a for a in ASSETS if st in streams_by_mkt[a]]
        if not mk:
            continue
        out[st] = {}
        daily = {}
        expo_h = {}
        n_tr = {}
        for a in mk:
            idx = per_index[a]
            if a not in bar_half:
                split = pd.Timestamp(SPLIT, tz="UTC")
                st_ = pd.Timestamp(START, tz="UTC")
                bar_half[a] = {"first_half": (idx >= st_) & (idx < split), "second_half": idx >= split,
                               "all": idx >= st_}
            for v in VARIANTS:
                S = streams_by_mkt[a][st][v]
                daily[(a, v)] = daily_series(idx, S["pnl"], cal).values
                for h, bm in bar_half[a].items():
                    expo_h[(a, v, h)] = float(S["expo"][bm].mean()) / CAPITAL if bm.any() else 0.0
                    if S["entry_t"] is not None:
                        t0 = _ms(START) if h != "second_half" else _ms(SPLIT)
                        t1 = _ms(SPLIT) if h == "first_half" else _ms(SEAL)
                        n_tr[(a, v, h)] = int(np.sum((S["entry_t"] >= t0) & (S["entry_t"] < t1)))
        for v in VARIANTS:
            out[st][v] = {}
            for h, hm in halves.items():
                markets, pooled_d, pooled_d_raw = {}, np.zeros(int(hm.sum())), np.zeros(int(hm.sum()))
                for a in mk:
                    e0, ev = expo_h[(a, "S0", h)], expo_h[(a, v, h)]
                    k = e0 / ev if ev > 0 else 1.0
                    d = daily[(a, v)][hm]
                    pooled_d += k * d
                    pooled_d_raw += d
                    mm = seg_metrics(k * d, CAPITAL, ev, n_tr.get((a, v, h)))
                    mm["sharpe_raw"] = mm["sharpe"]
                    mm["match_k"] = round(k, 4)
                    mm["return_raw_pct"] = round(100 * float(d.sum()) / CAPITAL, 2)
                    markets[a] = mm
                pm = seg_metrics(pooled_d, CAPITAL * len(mk), float(np.mean([expo_h[(a, v, h)] for a in mk])),
                                 sum(n_tr.get((a, v, h), 0) for a in mk) if st == "main" else None)
                pm["sharpe_unmatched_pool"] = None if sharpe(pooled_d_raw) is None else round(sharpe(pooled_d_raw), 3)
                base = None
                if v != "S0":
                    base = np.zeros(int(hm.sum()))
                    for a in mk:
                        base += daily[(a, "S0")][hm]
                    z, p = jk_memmel(pooled_d, base)
                    pm["jk_z"], pm["jk_p"] = z, p
                out[st][v][h] = {"pooled": pm, "markets": markets, "_pooled_daily": pooled_d}
    return out


def judge(S, fq_pooled):
    """The registered pass bar on the primary stream ('main')."""
    st = "main" if "main" in S else None
    res = {"stream": st, "variants": {}}
    if st is None:
        res["verdict"] = "NO MAIN STREAM"
        return res
    fpos = {h: (fq_pooled[h] is not None and fq_pooled[h] > 0) for h in ("first_half", "second_half")}

    def cond(v, h):
        b, x = S[st]["S0"][h], S[st][v][h]
        c1 = (x["pooled"]["sharpe"] or -9) > (b["pooled"]["sharpe"] or -9)
        beats = [a for a in x["markets"] if (x["markets"][a]["sharpe"] if x["markets"][a]["sharpe"] is not None else -9)
                 > (b["markets"][a]["sharpe"] if b["markets"][a]["sharpe"] is not None else -9)]
        c2 = len(beats) >= 5
        c3 = x["pooled"]["max_dd_pct"] <= b["pooled"]["max_dd_pct"]
        return {"c1_pooled_sharpe": c1, "c2_markets": c2, "markets_beating": beats, "c3_dd": c3,
                "c4_forecast": fpos[h], "all": bool(c1 and c2 and c3 and fpos[h]),
                "sharpe_gain": round((x["pooled"]["sharpe"] or 0) - (b["pooled"]["sharpe"] or 0), 3)}

    for v in TESTED:
        f, s = cond(v, "first_half"), cond(v, "second_half")
        res["variants"][v] = {"first_half": f, "second_half": s, "passes_full_bar": bool(f["all"] and s["all"])}
    elig = [v for v in TESTED if all(res["variants"][v]["first_half"][k] for k in ("c1_pooled_sharpe", "c2_markets", "c3_dd"))]
    pool = elig or list(TESTED)
    chosen = max(pool, key=lambda v: res["variants"][v]["first_half"]["sharpe_gain"])
    res["chosen"] = chosen
    res["chosen_met_first_half_1_3"] = bool(elig)
    res["passed"] = bool(res["variants"][chosen]["second_half"]["all"] and res["variants"][chosen]["first_half"]["all"])
    res["verdict"] = "PASS" if res["passed"] else "NO PASS"
    res["full_bar_passers"] = [v for v in TESTED if res["variants"][v]["passes_full_bar"]]
    return res


def truncation_check(a, cuts=(0.5, 0.8)):
    """sigma, the reference and every weight at decision bars on bars cut at each point equal the full run's."""
    df = load_dev(a)
    B = bars_per_day(df.index)
    full_sig = har_sigma(df["close"].values, B)
    end, _ = day_ends(df.index)
    tms = np.asarray(data.to_ms(df.index))
    bad, compared = 0, 0
    for f in cuts:
        k = int(len(df) * f)
        d2 = df.iloc[:k]
        s2 = har_sigma(d2["close"].values, B)
        e2, _ = day_ends(d2.index)                       # the cut's last bar looks like a day end; never used (j < i)
        at = np.arange(max(0, k - 3000), k, 7)
        r_full = reference(full_sig, tms, end, at)
        r_cut = reference(s2, tms[:k], e2, at)
        for v in VARIANTS:
            w1 = weight(v, full_sig[at], *r_full)
            w2 = weight(v, s2[at], *r_cut)
            bad += int(np.sum(~np.isclose(w1, w2, rtol=1e-12, atol=0, equal_nan=True)))
        bad += int(np.sum(~np.isclose(full_sig[:k], s2, rtol=1e-12, atol=0, equal_nan=True)))
        for x, y in zip(r_full, r_cut):
            bad += int(np.sum(~np.isclose(x, y, rtol=1e-12, atol=0, equal_nan=True)))
        compared += k + len(at) * (len(VARIANTS) + 3)
        # proxy decisions on the cut bars equal the full run's before the cut (the last cut day may be partial)
        p_full = [d for d in proxy_decisions(df, B) if d[0] < k - 2 * B]
        p_cut = [d for d in proxy_decisions(d2, B) if d[0] < k - 2 * B]
        bad += int(p_full != p_cut)
    return {"compared": compared, "mismatches": bad}


def strip(S):
    out = {}
    for st, vv in S.items():
        out[st] = {}
        for v, hh in vv.items():
            out[st][v] = dict((h, {"pooled": x["pooled"], "markets": x["markets"]}) for h, x in hh.items())
    return out


def run_study(log=print):
    os.makedirs(OUT, exist_ok=True)
    main = None
    if os.path.exists(TRADES_FILE):
        main = load_main_trades()
        log("main trades: %s" % dict((a, len(main["assets"].get(a, {}).get("trades", []))) for a in ASSETS))
    else:
        log("NO main_trades.json: primary stream missing")
    cal = pd.date_range(pd.Timestamp(START, tz="UTC"), pd.Timestamp(SEAL, tz="UTC") - pd.Timedelta(days=1), freq="D")
    per_index, streams, mkt = {}, {}, {}
    for a in ASSETS:
        recs = None
        if main is not None:
            A = main["assets"].get(a, {})
            recs = list(A.get("trades", []))
            if A.get("open_at_seal"):
                recs.append(A["open_at_seal"])
        idx, res, st = run_market(a, recs, log)
        per_index[a], mkt[a], streams[a] = idx, res, st
        w_main = dict((v, [round(float(x), 3) for x in st["main"][v]["w"]]) for v in ("S1", "S5")) if "main" in st else {}
        res["main_w_summary"] = dict((v, {"mean": round(float(np.mean(x)), 3) if x else None,
                                          "p10": round(float(np.percentile(x, 10)), 3) if x else None,
                                          "p90": round(float(np.percentile(x, 90)), 3) if x else None})
                                     for v, x in w_main.items())
        gc.collect()
    S = summarise(per_index, streams, cal)
    fq_pooled = {}
    for h in ("first_half", "second_half", "all"):
        vals = [mkt[a]["forecast"][h].get("spearman") for a in ASSETS]
        vals = [x for x in vals if x is not None]
        fq_pooled[h] = round(float(np.mean(vals)), 4) if vals else None
    J = judge(S, fq_pooled)
    # descriptive: the same bar on the proxy stream
    Jp = judge({"main": S["proxy"]}, fq_pooled) if "proxy" in S else None
    trunc = {}
    for a in ASSETS:
        trunc[a] = truncation_check(a)
        log("%s truncation: %s" % (a, trunc[a]))
    out = {"hypothesis": "H52", "registered_utc": REGISTERED_UTC, "seal": SEAL, "split": SPLIT, "start": START,
           "variants": VDESC, "bonferroni": BONF, "tests": len(TESTED),
           "main_meta": None if main is None else dict((k, v) for k, v in main.items() if k != "assets"),
           "markets": mkt, "forecast_pooled_spearman": fq_pooled, "results": strip(S), "judge": J,
           "judge_proxy_descriptive": Jp, "truncation": trunc,
           "main_trades_per_market": None if main is None else dict(
               (a, {"closed": len(main["assets"].get(a, {}).get("trades", [])),
                    "open_at_seal": bool(main["assets"].get(a, {}).get("open_at_seal")),
                    "window": main["assets"].get(a, {}).get("window")}) for a in ASSETS)}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    report(out)
    log("verdict %s (chosen %s), full-bar passers %s" % (J.get("verdict"), J.get("chosen"), J.get("full_bar_passers")))
    return out


# =====================================================================================
# the report
# =====================================================================================
def _f(x, fmt="%.2f"):
    return "-" if x is None else fmt % x


def report(R):
    L = ["# H52: size by expected move (volatility-forecast sizing), entries and exits unchanged", "",
         "Registered %s (research/hypotheses_pending/H52.md) before any code or number. PAPER RESEARCH ONLY. "
         "Development rows before %s 00:00 UTC; results from %s; first half before %s, second half from it. "
         "Capital $10,000 a market, not compounded; each market's own fee a side. Sharpe on daily marked P&L over "
         "calendar days, sqrt(365). Return and max drawdown are exposure-matched to S0 per (market, half); Sharpe "
         "and return/DD are scale-free." % (R["registered_utc"], R["seal"], R["start"], R["split"]), ""]
    J = R["judge"]
    L += ["## Verdict", "", "**%s** on the primary stream (the main book's replayed trades). Chosen on the first half: "
          "**%s** (%s). Variants passing the full bar in both halves: %s." % (
              J.get("verdict"), J.get("chosen"), VDESC.get(J.get("chosen"), ""), J.get("full_bar_passers") or "none"), ""]
    fq = R["forecast_pooled_spearman"]
    L += ["## 1. Forecast quality", "",
          "sigma = sqrt(B x mean of (v1, v5, v22)), equal-weight HAR of 15m squared log returns; vs the next valid "
          "day's (high - low) / close. Pooled = mean of the 8 per-market Spearman correlations: first half %s, "
          "second half %s." % (_f(fq["first_half"], "%.3f"), _f(fq["second_half"], "%.3f")), "",
          "| market | B | fee a side | Spearman 1st | Spearman 2nd | Pearson(log) 1st | Pearson(log) 2nd | days 1st / 2nd |",
          "|---|---|---|---|---|---|---|---|"]
    for a in ASSETS:
        m = R["markets"][a]
        f1, f2 = m["forecast"]["first_half"], m["forecast"]["second_half"]
        L.append("| %s | %d | %.5f | %s | %s | %s | %s | %s / %s |" % (
            a, m["B"], m["fee_side"], _f(f1.get("spearman"), "%.3f"), _f(f2.get("spearman"), "%.3f"),
            _f(f1.get("pearson_log"), "%.3f"), _f(f2.get("pearson_log"), "%.3f"), f1.get("n"), f2.get("n")))
    for st, title in (("main", "2. Primary stream: the main book's own replayed trades"),
                      ("proxy", "3. Secondary stream (descriptive): daily 30-day momentum sign, re-sized daily")):
        if st not in R["results"]:
            continue
        L += ["", "## " + title, ""]
        if st == "main" and R.get("main_meta"):
            L.append("Replay: %s" % json.dumps(R["main_meta"]))
            L.append("")
            L.append("Trades per market (closed / open at the seal): " + ", ".join(
                "%s %d%s" % (a, v["closed"], " +1" if v["open_at_seal"] else "") for a, v in R["main_trades_per_market"].items()))
            L.append("")
        for h in ("first_half", "second_half"):
            L += ["### %s, pooled (8 markets, $80,000)" % h.replace("_", " "), "",
                  "| variant | Sharpe | return % | max DD % | return/DD | avg exposure | trades | JK z | JK p |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for v in VARIANTS:
                p = R["results"][st][v][h]["pooled"]
                L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    v, _f(p["sharpe"], "%.3f"), _f(p["return_pct"]), _f(p["max_dd_pct"]), _f(p["ret_over_dd"]),
                    _f(p["avg_exposure"], "%.3f"), p.get("trades") if p.get("trades") is not None else "-",
                    _f(p.get("jk_z"), "%.2f"), _f(p.get("jk_p"), "%.4f")))
            L += ["", "Per-market Sharpe (%s):" % h.replace("_", " "), "",
                  "| variant | " + " | ".join(ASSETS) + " |", "|---|" + "---|" * len(ASSETS)]
            for v in VARIANTS:
                mk = R["results"][st][v][h]["markets"]
                L.append("| %s | " % v + " | ".join(_f(mk[a]["sharpe"], "%.2f") if a in mk else "-" for a in ASSETS) + " |")
            L += ["", "Per-market return %% / max DD %% (exposure-matched, %s):" % h.replace("_", " "), "",
                  "| variant | " + " | ".join(ASSETS) + " |", "|---|" + "---|" * len(ASSETS)]
            for v in VARIANTS:
                mk = R["results"][st][v][h]["markets"]
                L.append("| %s | " % v + " | ".join("%s / %s" % (_f(mk[a]["return_pct"], "%.1f"), _f(mk[a]["max_dd_pct"], "%.1f"))
                                                    if a in mk else "-" for a in ASSETS) + " |")
            L.append("")
        JJ = R["judge"] if st == "main" else R.get("judge_proxy_descriptive")
        if JJ and JJ.get("variants"):
            L += ["Pass-bar conditions (%s): c1 pooled Sharpe > S0, c2 >= 5 of 8 markets beat S0 on Sharpe, c3 pooled "
                  "matched max DD <= S0, c4 forecast correlation > 0." % ("REGISTERED" if st == "main" else "descriptive only"), "",
                  "| variant | 1st: gain / c1 c2 c3 c4 (markets) | 2nd: gain / c1 c2 c3 c4 (markets) | full bar |", "|---|---|---|---|"]
            for v in TESTED:
                x = JJ["variants"][v]

                def cs(c):
                    return "%+.3f / %s%s%s%s (%d)" % (c["sharpe_gain"], *("Y" if c[k] else "n" for k in
                                                       ("c1_pooled_sharpe", "c2_markets", "c3_dd", "c4_forecast")),
                                                       len(c["markets_beating"]))
                L.append("| %s | %s | %s | %s |" % (v, cs(x["first_half"]), cs(x["second_half"]), "PASS" if x["passes_full_bar"] else "no"))
            L.append("")
            L.append("Chosen on the first half: %s; verdict on it: %s." % (JJ["chosen"], JJ["verdict"]))
    L += ["", "## 4. Checks", "",
          "Truncation (sigma, reference, weights, proxy sides on bars cut at 50% / 80% vs the full run): " +
          ", ".join("%s %d/%d" % (a, v["mismatches"], v["compared"]) for a, v in R["truncation"].items()) +
          " (mismatches / values compared).", ""]
    for a in ASSETS:
        m = R["markets"][a]
        if "main_check" in m:
            L.append("- %s main trades: %s; S1 / S5 weights at entry: %s; proxy: %s" % (
                a, json.dumps(m["main_check"]), json.dumps(m.get("main_w_summary")), json.dumps(m["proxy_check"])))
        else:
            L.append("- %s proxy: %s" % (a, json.dumps(m["proxy_check"])))
    L += ["", "Variants: " + "; ".join("%s %s" % (k, v) for k, v in VDESC.items()) + ".",
          "Sharpe-difference test vs S0 (Jobson-Korkie, Memmel correction) on pooled matched daily P&L; Bonferroni "
          "threshold %.4f over %d variants (reported, not a pass condition)." % (R["bonferroni"], R["tests"]), ""]
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


# =====================================================================================
# the main-book replay (LAPTOP ONLY: needs data/evcache; read-only, every array cut at the seal)
# =====================================================================================
def prep_cut(group, assets, fits_dir, log=print):
    """exit_study.prep_readonly with every array cut at the seal (rows before 2025-11-11 00:00 UTC)."""
    from engine15 import evcache, labels, leanprep, model
    from engine15.config import CFG, voting_for
    stores = {}
    for a in assets:
        st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, group, a))
        if not st.load():
            raise RuntimeError("no evidence store for %s/%s" % (group, a))
        stores[a] = st
    full = pd.DatetimeIndex(pd.to_datetime(stores[assets[0]].times_ms(), unit="ms", utc=True))
    for a in assets[1:]:
        assert np.array_equal(stores[a].times_ms(), stores[assets[0]].times_ms())
    n = int(full.searchsorted(pd.Timestamp(SEAL, tz="UTC")))
    times = full[:n]
    cfg = dict(CFG, assets=tuple(assets), birth=CFG["birth"], voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    ev, X, ready, y, res, px = {}, {}, {}, {}, {}, {}
    padded = {}
    for a in assets:
        st = stores[a]
        ev[a] = st.frame(full).iloc[:n]
        X[a] = st.X()[:n]
        width = 1 + max(int(np.max(np.r_[c])) if not isinstance(c, slice) else c.stop - 1
                        for c in model._COLS.values() if c is not None and not (isinstance(c, (list, tuple)) and not c))
        if X[a].shape[1] < width:                                # a store older than the newest cards: those
            log("%s: store has %d feature columns, the model reads %d; the missing cards are silent (zeros)" % (
                a, X[a].shape[1], width))                       # cards are silent (zeros), disclosed in the study
            pad = np.zeros((n, width), dtype=X[a].dtype)
            pad[:, :X[a].shape[1]] = X[a]
            X[a] = pad
            padded[a] = int(width - st.X().shape[1])
        ready[a] = st.ready()[:n]
        b = load_dev(a).reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    t0 = time.time()
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth_idx, min(floor_idx, birth_idx), n, fits_dir)
    log("%s: voices walked to the seal: %d refits, %d from the private cache (%.0fs)" % (
        group, frep["refits"], frep["reused"], time.time() - t0))
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
        probs[a] = None
    del probs, trust, X
    gc.collect()
    return {"cfg": cfg, "assets": list(assets), "times": times, "ev": ev, "px": px, "odds": odds, "birth_idx": birth_idx,
            "padded": padded}


def replay(groups_wanted=None, fits_root=None, log=print):
    import exit_study as ex                                      # the lock, memory and priority helpers
    from engine15 import shadows
    from engine15.config import CFG
    os.makedirs(OUT, exist_ok=True)
    fits_root = fits_root or os.path.join(ROOT, "research", "out", "volsize_fits")
    ex.below_normal()
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    allout = {"assets": {}}
    if os.path.exists(TRADES_FILE):
        allout = load_main_trades()
    for g in (groups_wanted or list(groups)):
        ex.acquire("volsize_study replay %s (H52)" % g, log)
        try:
            ex.wait_memory(ex.MIN_FREE_START, log)
            prep = prep_cut(g, groups[g], os.path.join(fits_root, g), log)
            times = prep["times"]
            n = len(times)
            tms = data.to_ms(times)
            for a in groups[g]:
                ok = np.isfinite(prep["odds"][a][:, 0])
                lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
                aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
                b = ex.run_book("main", prep, a, lo, n, aux)
                tr = b["trades"]
                recs = [{"t_in_ms": int(r.t_in_ms), "t_out_ms": int(r.t_out_ms), "side": int(r.side), "p_in": float(r.p_in),
                         "p_out": float(r.p_out), "why_in": str(r.why_in), "why_out": str(r.why_out),
                         "engine_pnl_pct": float(r.pnl_pct)} for r in tr.itertuples()]
                st = b["state"]
                op = None
                if st.get("pos"):
                    op = {"t_in_ms": int(st["t_in_ms"]), "t_out_ms": int(tms[n - 1]), "side": int(st["pos"]),
                          "p_in": float(st["entry"]), "p_out": float(prep["px"][a]["close"][n - 1]),
                          "why_in": str(st.get("why_in")), "why_out": "OPEN_AT_SEAL"}
                allout["assets"][a] = {"trades": recs, "open_at_seal": op, "window": [str(times[lo])[:16], str(times[n - 1])[:16]],
                                       "group": g, "silent_missing_feature_columns": prep["padded"].get(a, 0)}
                log("%s %s: %d closed trades, open at seal %s, window %s .. %s" % (
                    g, a, len(recs), bool(op), str(times[lo])[:16], str(times[n - 1])[:16]))
            del prep
            gc.collect()
        finally:
            ex.release()
        allout.update(engine_version=CFG.get("version"), cut="rows before %s 00:00 UTC" % SEAL,
                      written_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), rule="main (hold to stop or flip)")
        with open(TRADES_FILE, "w", encoding="utf-8") as fh:
            json.dump(allout, fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.replay:
        replay([args.group] if args.group else None, log=log)
    elif args.report:
        with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
            report(json.load(fh))
    else:
        run_study(log)


if __name__ == "__main__":
    main()
