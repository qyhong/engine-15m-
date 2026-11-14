# -*- coding: utf-8 -*-
"""H39 -- new positioning and on-chain inputs, each tested ALONE for BTC and ETH risk information (registered in
research/HYPOTHESES.md, 13 Nov 2026 10:52 UTC, before any H39 history was downloaded or any number computed).
EXPLORATION, not a loop round: it changes no loop rule, cannot make a pass and adds nothing to either loop's count.

    py -3 research/flows_study.py            compute on development data, write research/out/flows/

Development data only: research/harness/core.load(asset, dev_only=True) drops every bar from 2025-11-11 on, and every
source row known at or after 2025-11-11 00:00 UTC is dropped before anything is computed (flows.inputs(cutoff_ms=...)
and the same cut for the existing files). Forward windows that would need a bar from the seal on are left out.
Paper research only: nothing here places orders. Nothing here is wired into the live engine.
"""
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15.sources import derivs, flows, market  # noqa: E402
from research.harness import core  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "flows")
ASSETS = ("BTCUSDT", "ETHUSDT")
DAY_MS, HOUR_MS = 86400000, 3600000
SEAL_MS = int(core.HOLDOUT_START.value // 10 ** 6)
REGISTERED_UTC = "2026-11-13 10:52 UTC"
HORIZONS = (1, 7, 30)
DRAWS, SEED = 2000, 39
IR_TARGET = 1.15                                      # round 3: the overlay information ratio S4 needs
BAR_IC = 0.12                                         # the registered bar: partial risk IC at 7 days >= 0.12
CALL_PCT, CALL_WINDOW, CALL_MIN = 0.80, 365, 180

# input -> (label, risk-off side: +1 HIGH, -1 LOW, family)   (as registered; the order is the register's)
INPUTS = [
    ("fl_oi_7d", "X1 Binance open interest, 7-day log change", +1, "positioning"),
    ("fl_ls_global_z", "X2 Binance global account long/short, z 90d", +1, "positioning"),
    ("fl_ls_topgap_z", "X3 Binance top-trader position L/S minus global account L/S, z 90d", -1, "positioning"),
    ("fl_bfx_14d", "X4 Bitfinex margin ln(longs/shorts), 14-day change", -1, "positioning"),
    ("fl_cme_lev_z", "X5 CME leveraged funds net % OI, z 52 reports", +1, "positioning"),
    ("fl_mvrv_z", "X6 MVRV, ln z 365d", +1, "on-chain"),
    ("fl_netflow_7d", "X7 exchange net inflow 7d / exchange supply", +1, "on-chain"),
    ("fl_addr", "X8 active addresses, ln(30d mean / 365d mean)", -1, "on-chain"),
    ("fl_hash_ribbon", "X9 BTC hash ribbon ln(SMA30/SMA60)", -1, "on-chain"),
    ("stable_30d", "X10 stablecoin supply, 30-day log change", -1, "existing"),
    ("fng_7d", "X11 Fear & Greed, 7-day mean", +1, "existing"),
    ("dvol_z90", "X12 Deribit DVOL, z 90d", +1, "existing"),
]
N_TESTS_REGISTERED = len(INPUTS) * len(ASSETS) * (2 * len(HORIZONS) + len(HORIZONS))   # 216


# ------------------------------------------------------------------ data
def daily_bars(asset):
    """Development 15m bars -> UTC daily bars (open time = day D, the close is known at D+1 00:00)."""
    bars, _fund = core.load(asset, dev_only=True)
    d = bars.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(subset=["close"])
    n15 = bars["close"].resample("1D", label="left", closed="left").count()
    d = d[n15.reindex(d.index).values >= 90]                     # whole days only (a day needs 90 of 96 bars)
    return d


def _asof(known_ms, values, close_ms, max_age_ms):
    return flows._asof(known_ms, values, close_ms, max_age_ms)


def existing_inputs(decision_ms):
    """X10-X12 from the existing files, with their own modules' known-at rules, cut at the seal."""
    out = pd.DataFrame(index=decision_ms)
    st = market.load_daily(market.stable_path(), market.STABLE_COLS)
    known = st.index.values.astype("int64") + market.DAILY_LAG_MS
    st = st[known < SEAL_MS]
    s = st["total_usd"].reindex(market._grid(st.index[0], st.index[-1], DAY_MS))
    s = np.log(s.where(s > 0))
    out["stable_30d"] = _asof(s.index.values + market.DAILY_LAG_MS, (s - s.shift(30)).values, decision_ms,
                              market.DAILY_MAX_AGE_MS)
    fg = market.load_daily(market.fng_path(), market.FNG_COLS)
    known = fg.index.values.astype("int64") + market.FNG_LAG_MS
    fg = fg[known < SEAL_MS]
    v = fg["value"].reindex(market._grid(fg.index[0], fg.index[-1], DAY_MS)).astype(float)
    out["fng_7d"] = _asof(v.index.values + market.FNG_LAG_MS, v.rolling(7, min_periods=5).mean().values, decision_ms,
                          market.DAILY_MAX_AGE_MS)
    return out


def dvol_input(asset, decision_ms):
    g = derivs.load_source("options_dvol", asset)
    known = g["ts_ms"].values + HOUR_MS
    g, known = g[known < SEAL_MS], known[known < SEAL_MS]
    v = pd.Series(_asof(known, g["close"].values, decision_ms, derivs.DVOL_MAX_AGE), index=decision_ms)
    w = v.rolling(90, min_periods=30)                            # on the daily decision series, trailing only
    return (v - w.mean()) / w.std().where(w.std() > 0)


def frame_for(asset):
    d = daily_bars(asset)
    decision = (d.index.as_unit("ms").asi8 + DAY_MS).astype("int64")   # the close of day D = 00:00 UTC of D+1 (ms, unit-safe)
    f = pd.DataFrame(index=decision)
    f["day"] = d.index.strftime("%Y-%m-%d")
    c, lo = d["close"].values, d["low"].values
    n = len(c)
    for h in HORIZONS:
        r = np.full(n, np.nan)
        dd = np.full(n, np.nan)
        r[:n - h] = c[h:] / c[:n - h] - 1.0
        for i in range(n - h):
            dd[i] = min(lo[i + 1:i + h + 1].min() / c[i] - 1.0, 0.0)
        # a forward window must be h consecutive calendar days of dev bars
        ok = np.zeros(n, dtype=bool)
        ok[:n - h] = (decision[h:] - decision[:n - h]) == h * DAY_MS
        f["r%d" % h] = np.where(ok, r, np.nan)
        f["dd%d" % h] = np.where(ok, dd, np.nan)
    cs = pd.Series(c, index=decision)
    f["m"] = np.sign(cs / cs.shift(30) - 1.0)
    sma = cs.rolling(200, min_periods=200).mean()
    f["D"] = ((cs < sma) & (sma < sma.shift(20))).astype(float).where(sma.shift(20).notna())
    x = flows.inputs(decision, asset, cutoff_ms=SEAL_MS)
    assert not x.attrs["errors"], x.attrs["errors"]
    for name, _l, _s, fam in INPUTS:
        if name.startswith("fl_"):
            f[name] = x[name].values
    f = f.join(existing_inputs(decision))
    f["dvol_z90"] = dvol_input(asset, decision).values
    assert decision.max() <= SEAL_MS and decision.min() > 1500000000000, "decision times are not epoch ms"
    return f


# ------------------------------------------------------------------ statistics
def rank(a):
    return pd.Series(a).rank().values


def spearman(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    return corr(rank(a[ok]), rank(b[ok])) if ok.sum() > 10 else float("nan")


def resid(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def corr(a, b):
    a, b = a - a.mean(), b - b.mean()
    den = math.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else float("nan")


def block_idx(n, block, rng):
    k = int(math.ceil(n / float(block)))
    starts = rng.randint(0, max(n - block, 0) + 1, size=k)
    return (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]


def boot(stat, n, block, draws=DRAWS, seed=SEED):
    """Moving-block bootstrap of stat(idx) over n time-ordered rows -> (point, se, lo95, hi95, p two-sided)."""
    point = stat(np.arange(n))
    rng = np.random.RandomState(seed)
    vals = np.array([stat(block_idx(n, block, rng)) for _ in range(draws)])
    vals = vals[np.isfinite(vals)]
    se = float(vals.std(ddof=1)) if len(vals) > 10 else float("nan")
    z = point / se if se and se > 0 else float("nan")
    p = float(math.erfc(abs(z) / math.sqrt(2.0))) if np.isfinite(z) else float("nan")
    return float(point), se, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), p


def trailing_pct(s, window=CALL_WINDOW, min_n=CALL_MIN):
    """Share of the trailing window (today included) at or below today's value; NaN before min_n values."""
    v = s.values
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if not np.isfinite(v[i]):
            continue
        w = v[max(0, i - window + 1):i + 1]
        w = w[np.isfinite(w)]
        if len(w) >= min_n:
            out[i] = float((w <= v[i]).mean())
    return out


def analyse(f, name, side):
    """All registered measures for one input on one coin."""
    s_all = side * f[name]
    res = {"n_days_with_input": int(s_all.notna().sum())}
    have = f.index[s_all.notna()]
    if not len(have):
        return res
    res["first_day"] = f.loc[have[0], "day"]
    res["last_day"] = f.loc[have[-1], "day"]
    res["corr_with_m"] = spearman(s_all.values, f["m"].values)
    res["corr_with_D"] = spearman(s_all.values, f["D"].values)
    pct = trailing_pct(s_all)
    for h in HORIZONS:
        block = max(10, 2 * h)
        for tgt in ("r", "dd"):
            y = f["%s%d" % (tgt, h)]
            ok = s_all.notna() & y.notna()
            sv, yv = rank(s_all[ok].values), rank(y[ok].values)
            n = int(ok.sum())
            if n < 200:
                continue
            pt, se, lo, hi, p = boot(lambda i: -corr(sv[i], yv[i]), n, block)
            res["ic_%s%d" % (tgt, h)] = {"n": n, "ic": pt, "se": se, "lo": lo, "hi": hi, "p": p}
        # incremental: partial rank correlation with r_h given [1, m, D]
        y = f["r%d" % h]
        ok = s_all.notna() & y.notna() & f["m"].notna() & f["D"].notna()
        n = int(ok.sum())
        if n >= 200:
            sv, yv = rank(s_all[ok].values), rank(y[ok].values)
            X = np.column_stack([np.ones(n), f["m"][ok].values, f["D"][ok].values])

            def partial(i):
                return -corr(resid(sv[i], X[i]), resid(yv[i], X[i]))
            pt, se, lo, hi, p = boot(partial, n, block)
            # nested regression r_h ~ m + D (+ z(rank s)): added R^2
            yr = y[ok].values
            zs = (sv - sv.mean()) / sv.std()
            r0 = resid(yr, X)
            r1 = resid(yr, np.column_stack([X, zs]))
            tss = ((yr - yr.mean()) ** 2).sum()
            res["partial_r%d" % h] = {"n": n, "ic": pt, "se": se, "lo": lo, "hi": hi, "p": p,
                                      "added_r2": float(((r0 ** 2).sum() - (r1 ** 2).sum()) / tss),
                                      "ic_needed_ir115": IR_TARGET / math.sqrt(365.0 / h)}
        # risk-off calls (descriptive)
        y, dd = f["r%d" % h], f["dd%d" % h]
        ok = np.isfinite(pct) & y.notna().values
        if ok.sum() >= 200:
            call = ok & (pct >= CALL_PCT)
            rest = ok & (pct < CALL_PCT)
            mom = ok & (f["m"].values == -1)
            res["calls_%d" % h] = {
                "n_days": int(ok.sum()), "n_calls": int(call.sum()), "call_share": float(call.sum() / ok.sum()),
                "hit_rate": float((y.values[call] < 0).mean()) if call.any() else None,
                "base_rate": float((y.values[ok] < 0).mean()),
                "mean_r_calls": float(y.values[call].mean()) if call.any() else None,
                "mean_r_rest": float(y.values[rest].mean()) if rest.any() else None,
                "mean_dd_calls": float(dd.values[call].mean()) if call.any() else None,
                "mean_dd_rest": float(dd.values[rest].mean()) if rest.any() else None,
                "mom_hit_rate": float((y.values[mom] < 0).mean()) if mom.any() else None,
                "mom_mean_r": float(y.values[mom].mean()) if mom.any() else None,
                "mom_share": float(mom.sum() / ok.sum()),
                "calls_also_mom_off": float((f["m"].values[call] == -1).mean()) if call.any() else None}
    # halves of its own span, risk IC at 7 days
    y = f["r7"]
    ok = s_all.notna() & y.notna()
    idx = np.where(ok.values)[0]
    if len(idx) >= 200:
        half = len(idx) // 2
        hv = []
        for part in (idx[:half], idx[half:]):
            hv.append(-corr(rank(s_all.values[part]), rank(y.values[part])))
        res["ic_r7_halves"] = hv
        res["halves_split_day"] = f["day"].values[idx[half]]
    return res


def bh(pvals):
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank_i, j in enumerate(order[::-1]):
        k = n - rank_i
        prev = min(prev, p[j] * n / k)
        q[j] = prev
    return q


# ------------------------------------------------------------------ report
def pct(x, d=1):
    return "-" if x is None or not np.isfinite(x) else ("%+." + str(d) + "f%%") % (100.0 * x)


def num(x, d=3):
    return "-" if x is None or not np.isfinite(x) else ("%+." + str(d) + "f") % x


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    frames, results = {}, {}
    for asset in ASSETS:
        f = frame_for(asset)
        frames[asset] = f
        results[asset] = {}
        for name, label, side, fam in INPUTS:
            results[asset][name] = analyse(f, name, side)
    # multiple testing over every p-value actually computed
    tests = []
    for asset in ASSETS:
        for name, *_ in INPUTS:
            r = results[asset][name]
            for key in ["ic_r%d" % h for h in HORIZONS] + ["ic_dd%d" % h for h in HORIZONS] + \
                       ["partial_r%d" % h for h in HORIZONS]:
                if key in r and np.isfinite(r[key]["p"]):
                    tests.append((asset, name, key, r[key]["p"]))
    n_tests = len(tests)
    q = bh([t[3] for t in tests]) if tests else []
    alpha = 0.05 / n_tests if n_tests else float("nan")
    for (asset, name, key, p), qq in zip(tests, q):
        results[asset][name][key]["q_bh"] = float(qq)
        results[asset][name][key]["bonferroni_sig"] = bool(p <= alpha)
    alpha_reg = 0.05 / N_TESTS_REGISTERED
    verdict = {}
    for name, label, side, fam in INPUTS:
        ok, why = True, []
        for asset in ASSETS:
            r = results[asset][name]
            pr = r.get("partial_r7")
            if pr is None:
                ok = False
                why.append("%s: not enough data" % asset[:3])
                continue
            if not (pr["ic"] > 0 and pr["p"] <= min(alpha, alpha_reg) and pr["ic"] >= BAR_IC):
                ok = False
                why.append("%s partial IC7 %+.3f (p %.3g)" % (asset[:3], pr["ic"], pr["p"]))
            hv = r.get("ic_r7_halves")
            if hv is None or np.sign(hv[0]) != np.sign(hv[1]):
                ok = False
                why.append("%s halves %s" % (asset[:3], "n/a" if hv is None else "%+.3f / %+.3f" % tuple(hv)))
        verdict[name] = {"qualifies": ok, "why_not": why}
    out = {"hypothesis": "H39", "registered_utc": REGISTERED_UTC, "computed_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "seal": "2025-11-11 00:00 UTC (holdout not loaded; source rows known at or after it dropped)",
           "n_tests_registered": N_TESTS_REGISTERED, "n_tests_run": n_tests, "bonferroni_alpha": alpha,
           "draws": DRAWS, "inputs": [dict(name=n, label=l, risk_off_side="HIGH" if s > 0 else "LOW", family=fm)
                                      for n, l, s, fm in INPUTS],
           "results": results, "verdict": verdict,
           "spans": dict((a, {"first_decision_day": frames[a]["day"].iloc[0], "last_decision_day": frames[a]["day"].iloc[-1]})
                         for a in ASSETS),
           "runtime_s": round(time.time() - t0, 1)}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else o)
    write_md(out)
    print("done in %.0f s; %d tests; alpha %.2e" % (time.time() - t0, n_tests, alpha))


def write_md(o):
    R, L = o["results"], []
    a = L.append
    a("# H39: new positioning and on-chain inputs, each tested alone (exploration, not a loop round)")
    a("")
    a("Registered %s in `research/HYPOTHESES.md` before any H39 history was downloaded or any number computed; computed %s. "
      "Code `research/flows_study.py`; data `engine15/sources/flows.py` (docs `docs/SOURCES_flows.md`; not wired into the "
      "live engine); machine-readable `research/out/flows/study.json`." % (o["registered_utc"], o["computed_utc"]))
    a("")
    a("Development data only: bars before 2025-11-11 (`core.load(dev_only=True)`); source rows known at or after "
      "2025-11-11 00:00 UTC dropped first; forward windows end before the seal. The holdout was not touched. Decisions: "
      "each daily close (00:00 UTC). Risk IC = -Spearman(oriented input, outcome): **positive = the registered risk-off "
      "side was right** (high input, lower forward return / deeper forward drawdown). Partial IC = the same after removing "
      "the 30-day momentum sign m and the 200-day downtrend rule D (rank residuals on [1, m, D]). 95%% intervals and p from "
      "a moving-block bootstrap (block max(10, 2h) days, %d draws)." % o["draws"])
    a("")
    a("**Multiple testing:** %d tests run (%d registered: 12 inputs x 2 coins x 9); Bonferroni level %.2e; BH q in the JSON."
      % (o["n_tests_run"], o["n_tests_registered"], o["bonferroni_alpha"]))
    a("")
    a("**IC needed for an overlay information ratio of 1.15** (round 3's S4 estimate), one independent bet per horizon: "
      "1 day 0.060, 7 days 0.160, 30 days 0.331. Round 3's 0.12-0.17 band corresponds to the 7-day horizon; the "
      "registered bar for an RL round 4 is a partial IC at 7 days >= 0.12, Bonferroni-significant, on both coins, with "
      "the same sign in both halves of the input's span.")
    a("")
    for asset in ASSETS:
        a("## %s" % asset)
        a("")
        a("| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd7 | Risk IC dd30 | "
          "**Partial IC r7** [95%] (p) | Partial r30 | Added R2 r7 | Halves r7 | corr with m |")
        a("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for name, label, side, fam in INPUTS:
            r = R[asset][name]
            if "ic_r7" not in r:
                a("| %s | %s | %d | not enough data | | | | | | | | | |" % (label, r.get("first_day", "-"), r["n_days_with_input"]))
                continue
            g = lambda k: r.get(k, {}).get("ic") if k in r else None              # noqa: E731
            i7, p7 = r["ic_r7"], r.get("partial_r7", {})
            star = " **(Bonf.)**" if p7.get("bonferroni_sig") else ""
            hv = r.get("ic_r7_halves")
            a("| %s | %s .. %s | %d | %s | %s [%s, %s] | %s | %s | %s | %s [%s, %s] (%.3g)%s | %s | %s | %s | %s |" % (
                label, r["first_day"], r["last_day"], i7["n"], num(g("ic_r1")), num(i7["ic"]), num(i7["lo"], 2),
                num(i7["hi"], 2), num(g("ic_r30")), num(g("ic_dd7")), num(g("ic_dd30")),
                num(p7.get("ic")), num(p7.get("lo"), 2), num(p7.get("hi"), 2), p7.get("p", float("nan")), star,
                num(g("partial_r30")), "%.4f" % p7.get("added_r2", float("nan")),
                "-" if hv is None else "%+.2f / %+.2f" % tuple(hv), num(r.get("corr_with_m"), 2)))
        a("")
        a("Risk-off calls (input in its registered risk-off tail: at or above the 80th percentile of its trailing 365 days), "
          "7-day horizon; momentum's own risk-off (m = -1) over the same days for reference:")
        a("")
        a("| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | "
          "Calls already m = -1 | Momentum-off hit rate / mean r7 |")
        a("|---|---|---|---|---|---|---|---|---|")
        for name, label, side, fam in INPUTS:
            c = R[asset][name].get("calls_7")
            if not c:
                a("| %s | - | | | | | | | |" % label)
                continue
            a("| %s | %d | %d (%.0f%%) | %s | %s | %s / %s | %s / %s | %s | %s / %s |" % (
                label, c["n_days"], c["n_calls"], 100 * c["call_share"], pct(c["hit_rate"], 0), pct(c["base_rate"], 0),
                pct(c["mean_r_calls"]), pct(c["mean_r_rest"]), pct(c["mean_dd_calls"]), pct(c["mean_dd_rest"]),
                pct(c["calls_also_mom_off"], 0), pct(c["mom_hit_rate"], 0), pct(c["mom_mean_r"])))
        a("")
    a("## Verdict against the registered bar")
    a("")
    a("| Input | Qualifies for an RL round 4 | Why not |")
    a("|---|---|---|")
    for name, label, side, fam in INPUTS:
        v = o["verdict"][name]
        a("| %s | %s | %s |" % (label, "YES" if v["qualifies"] else "no", "; ".join(v["why_not"]) or "-"))
    a("")
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
