# -*- coding: utf-8 -*-
"""H40 -- Deribit options flow (put/call and skew), each input tested ALONE for BTC and ETH risk information (registered
in research/HYPOTHESES.md, 14 Nov 2026 09:00 UTC, before any H40 history was downloaded or any number computed).
EXPLORATION, not a loop round: it changes no loop rule, cannot make a pass and adds nothing to either loop's count.

    py -3 research/options_study.py          compute on development data, write research/out/options/

The method is H39's (research/flows_study.py), imported from it unchanged: daily decisions at 00:00 UTC, oriented risk
IC = -Spearman, partial IC on [1, m, D], moving-block bootstrap (block max(10, 2h) days, 2,000 draws), risk-off tail
calls, halves. H40 adds one registered test per input and coin: the partial IC at 7 days also controlling for DVOL z90.

Development data only: core.load(asset, dev_only=True) drops every bar from 2025-11-11 on; options_hist.inputs(...,
cutoff_ms=SEAL_MS) drops every options row known at or after 2025-11-11 00:00 UTC (and the fetch itself stopped there).
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

from engine15.sources import options_hist  # noqa: E402
from research import flows_study as fs  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "options")
ASSETS = fs.ASSETS
DAY_MS = fs.DAY_MS
SEAL_MS = fs.SEAL_MS
REGISTERED_UTC = "2026-11-14 09:00 UTC"
HORIZONS = fs.HORIZONS
BAR_IC = 0.12

# input -> (label, risk-off side: +1 HIGH, -1 LOW)   (as registered; the order is the register's)
INPUTS = [
    ("op_pcr_7d", "O1 put/call notional, ln ratio, 7 days", +1),
    ("op_pcr_1d_z90", "O2 put/call notional 24h, ln ratio, z 90d", +1),
    ("op_taker_bear_7d", "O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d", +1),
    ("op_rr25", "O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts", +1),
    ("op_rr25_chg7", "O5 25-delta skew, 7-day change", +1),
    ("op_block_bear_7d", "O6 block-trade bearish flow / block notional, 7d", +1),
]
N_TESTS_REGISTERED = len(INPUTS) * len(ASSETS) * (2 * len(HORIZONS) + len(HORIZONS) + 1)   # 120


def frame_for(asset):
    """Daily dev bars -> decision frame with H39's targets and controls, the H40 inputs and DVOL z90."""
    d = fs.daily_bars(asset)
    decision = (d.index.as_unit("ms").asi8 + DAY_MS).astype("int64")
    f = pd.DataFrame(index=decision)
    f["day"] = d.index.strftime("%Y-%m-%d")
    c, lo = d["close"].values, d["low"].values
    n = len(c)
    for h in HORIZONS:                                                # exactly fs.frame_for's targets
        r = np.full(n, np.nan)
        dd = np.full(n, np.nan)
        r[:n - h] = c[h:] / c[:n - h] - 1.0
        for i in range(n - h):
            dd[i] = min(lo[i + 1:i + h + 1].min() / c[i] - 1.0, 0.0)
        ok = np.zeros(n, dtype=bool)
        ok[:n - h] = (decision[h:] - decision[:n - h]) == h * DAY_MS
        f["r%d" % h] = np.where(ok, r, np.nan)
        f["dd%d" % h] = np.where(ok, dd, np.nan)
    cs = pd.Series(c, index=decision)
    f["m"] = np.sign(cs / cs.shift(30) - 1.0)
    sma = cs.rolling(200, min_periods=200).mean()
    f["D"] = ((cs < sma) & (sma < sma.shift(20))).astype(float).where(sma.shift(20).notna())
    x = options_hist.inputs(decision, asset, cutoff_ms=SEAL_MS)
    assert not x.attrs["errors"], x.attrs["errors"]
    for name, _l, _s in INPUTS:
        f[name] = x[name].values
    for r in options_hist.RAW:
        f[r] = x[r].values
    f["dvol_z90"] = fs.dvol_input(asset, decision).values
    assert decision.max() <= SEAL_MS and decision.min() > 1500000000000, "decision times are not epoch ms"
    return f


def partial_dvol(f, name, side, h=7):
    """Partial rank IC with r_h controlling for [1, m, D, DVOL z90] (registered for H40)."""
    s = side * f[name]
    y = f["r%d" % h]
    ok = s.notna() & y.notna() & f["m"].notna() & f["D"].notna() & f["dvol_z90"].notna()
    n = int(ok.sum())
    if n < 200:
        return None
    sv, yv = fs.rank(s[ok].values), fs.rank(y[ok].values)
    X = np.column_stack([np.ones(n), f["m"][ok].values, f["D"][ok].values, fs.rank(f["dvol_z90"][ok].values)])

    def stat(i):
        return -fs.corr(fs.resid(sv[i], X[i]), fs.resid(yv[i], X[i]))
    pt, se, lo, hi, p = fs.boot(stat, n, max(10, 2 * h))
    return {"n": n, "ic": pt, "se": se, "lo": lo, "hi": hi, "p": p}


def coverage(f, name):
    s = f[name]
    return {"n": int(s.notna().sum()), "first": f["day"][s.notna()].iloc[0] if s.notna().any() else None,
            "mean": float(s.mean()) if s.notna().any() else None, "sd": float(s.std()) if s.notna().sum() > 2 else None,
            "corr_dvol": fs.spearman(s.values, f["dvol_z90"].values)}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    frames, results = {}, {}
    for asset in ASSETS:
        f = frame_for(asset)
        frames[asset] = f
        results[asset] = {}
        for name, label, side in INPUTS:
            r = fs.analyse(f, name, side)
            pdv = partial_dvol(f, name, side)
            if pdv is not None:
                r["partial_dvol_r7"] = pdv
            r["coverage"] = coverage(f, name)
            results[asset][name] = r
    keys = ["ic_r%d" % h for h in HORIZONS] + ["ic_dd%d" % h for h in HORIZONS] + \
           ["partial_r%d" % h for h in HORIZONS] + ["partial_dvol_r7"]
    tests = []
    for asset in ASSETS:
        for name, *_ in INPUTS:
            r = results[asset][name]
            for key in keys:
                if key in r and np.isfinite(r[key]["p"]):
                    tests.append((asset, name, key, r[key]["p"]))
    n_tests = len(tests)
    q = fs.bh([t[3] for t in tests]) if tests else []
    alpha = 0.05 / n_tests if n_tests else float("nan")
    alpha_reg = 0.05 / N_TESTS_REGISTERED
    for (asset, name, key, p), qq in zip(tests, q):
        results[asset][name][key]["q_bh"] = float(qq)
        results[asset][name][key]["bonferroni_sig"] = bool(p <= min(alpha, alpha_reg))
    verdict = {}
    for name, label, side in INPUTS:
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
    data_cov = {}
    for asset in ASSETS:
        h = options_hist.load_source("hourly", asset)
        h = h[h["known_ms"] < SEAL_MS]
        days = h.groupby(h["ts_ms"] // DAY_MS)["n"].sum()
        data_cov[asset] = {"hours": int(len(h)), "first_hour": pd.Timestamp(int(h.ts_ms.iloc[0]), unit="ms").strftime("%Y-%m-%d %H:%M"),
                           "last_hour": pd.Timestamp(int(h.ts_ms.iloc[-1]), unit="ms").strftime("%Y-%m-%d %H:%M"),
                           "gapless": bool((np.diff(h.ts_ms.values) == fs.HOUR_MS).all()),
                           "trades": int(h["n"].sum()), "skipped": int(h["skipped"].sum()),
                           "days_without_trades": int((days == 0).sum()),
                           "trades_per_day_by_year": dict((str(y), int(v)) for y, v in days.groupby(
                               pd.to_datetime(days.index * DAY_MS, unit="ms").year).mean().round().items()),
                           "block_trades": int(h["blk_n"].sum()),
                           "earliest_served": options_hist.EARLIEST_SERVED[asset]}
    out = {"hypothesis": "H40", "registered_utc": REGISTERED_UTC,
           "computed_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "seal": "2025-11-11 00:00 UTC (holdout not loaded; no options trade from it fetched; rows known at or after it dropped)",
           "n_tests_registered": N_TESTS_REGISTERED, "n_tests_run": n_tests, "bonferroni_alpha": min(alpha, alpha_reg),
           "draws": fs.DRAWS, "inputs": [dict(name=n, label=l, risk_off_side="HIGH" if s > 0 else "LOW") for n, l, s in INPUTS],
           "results": results, "verdict": verdict, "data": data_cov,
           "spans": dict((a, {"first_decision_day": frames[a]["day"].iloc[0], "last_decision_day": frames[a]["day"].iloc[-1]})
                         for a in ASSETS),
           "runtime_s": round(time.time() - t0, 1)}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else o)
    write_md(out)
    print("done in %.0f s; %d tests; alpha %.2e" % (time.time() - t0, n_tests, min(alpha, alpha_reg)))


def write_md(o):
    R, L = o["results"], []
    a = L.append
    num, pct = fs.num, fs.pct
    a("# H40: Deribit options flow (put/call and skew), each input tested alone (exploration, not a loop round)")
    a("")
    a("Registered %s in `research/HYPOTHESES.md` before any H40 history was downloaded or any number computed; computed %s. "
      "Code `research/options_study.py` (H39's statistics imported from `research/flows_study.py` unchanged); data "
      "`engine15/sources/options_hist.py` (docs `docs/SOURCES_options_hist.md`; not wired into the live engine); "
      "machine-readable `research/out/options/study.json`." % (o["registered_utc"], o["computed_utc"]))
    a("")
    a("Development data only: bars before 2025-11-11; option trades fetched only up to 2025-11-11 00:00 UTC and every row "
      "known at or after it dropped; forward windows end before the seal. Decisions: each daily close (00:00 UTC). "
      "Risk IC = -Spearman(oriented input, outcome): **positive = the registered risk-off side (HIGH for every input) was "
      "right**. Partial IC = the same after removing the 30-day momentum sign m and the 200-day downtrend rule D; "
      "'Partial +DVOL' also removes DVOL z90. Moving-block bootstrap (block max(10, 2h) days, %d draws)." % o["draws"])
    a("")
    a("**Multiple testing:** %d tests run (%d registered: 6 inputs x 2 coins x 10); Bonferroni level %.2e; BH q in the JSON."
      % (o["n_tests_run"], o["n_tests_registered"], o["bonferroni_alpha"]))
    a("")
    a("**Bar (registered, H39's, not lowered):** partial IC at 7 days >= 0.12, positive, Bonferroni-significant, on both "
      "coins, same sign in both halves. RL loop S4 needs an IC of about 0.12-0.17 (0.160 for an information ratio of 1.15 "
      "at 7 days, one independent bet a week).")
    a("")
    a("## Data")
    a("")
    a("| Coin | First option trade served | Hours stored (dev) | Gapless | Trades | Block trades | Days without trades | Trades a day by year |")
    a("|---|---|---|---|---|---|---|---|")
    for asset in ASSETS:
        d = o["data"][asset]
        a("| %s | %s | %d (%s .. %s) | %s | %s | %s | %d | %s |" % (
            asset, d["earliest_served"], d["hours"], d["first_hour"], d["last_hour"], "yes" if d["gapless"] else "NO",
            "{:,}".format(d["trades"]), "{:,}".format(d["block_trades"]), d["days_without_trades"],
            ", ".join("%s: %s" % (y, "{:,}".format(v)) for y, v in d["trades_per_day_by_year"].items())))
    a("")
    for asset in ASSETS:
        a("## %s" % asset)
        a("")
        a("| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd1 | Risk IC dd7 | "
          "**Partial IC r7** [95%] (p) | Partial +DVOL r7 (p) | Partial r1 | Partial r30 | Halves r7 | corr m | corr DVOL z |")
        a("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for name, label, side in [(i["name"], i["label"], 1) for i in o["inputs"]]:
            r = R[asset][name]
            if "ic_r7" not in r:
                a("| %s | %s | %d | not enough data | | | | | | | | | | | |" % (label, r.get("first_day", "-"), r["n_days_with_input"]))
                continue
            g = lambda k: r.get(k, {}).get("ic") if k in r else None              # noqa: E731
            i7, p7, pd7 = r["ic_r7"], r.get("partial_r7", {}), r.get("partial_dvol_r7", {})
            star = " **(Bonf.)**" if p7.get("bonferroni_sig") else ""
            hv = r.get("ic_r7_halves")
            a("| %s | %s .. %s | %d | %s | %s [%s, %s] | %s | %s | %s | %s [%s, %s] (%.3g)%s | %s (%.3g) | %s | %s | %s | %s | %s |" % (
                label, r["first_day"], r["last_day"], i7["n"], num(g("ic_r1")), num(i7["ic"]), num(i7["lo"], 2),
                num(i7["hi"], 2), num(g("ic_r30")), num(g("ic_dd1")), num(g("ic_dd7")),
                num(p7.get("ic")), num(p7.get("lo"), 2), num(p7.get("hi"), 2), p7.get("p", float("nan")), star,
                num(pd7.get("ic")), pd7.get("p", float("nan")), num(g("partial_r1")), num(g("partial_r30")),
                "-" if hv is None else "%+.2f / %+.2f" % tuple(hv), num(r.get("corr_with_m"), 2),
                num(r["coverage"].get("corr_dvol"), 2)))
        a("")
        a("Risk-off calls (input at or above the 80th percentile of its trailing 365 days), 7-day horizon; momentum's own "
          "risk-off (m = -1) over the same days for reference:")
        a("")
        a("| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | "
          "Calls already m = -1 | Momentum-off hit rate / mean r7 |")
        a("|---|---|---|---|---|---|---|---|---|")
        for i in o["inputs"]:
            c = R[asset][i["name"]].get("calls_7")
            if not c:
                a("| %s | - | | | | | | | |" % i["label"])
                continue
            a("| %s | %d | %d (%.0f%%) | %s | %s | %s / %s | %s / %s | %s | %s / %s |" % (
                i["label"], c["n_days"], c["n_calls"], 100 * c["call_share"], pct(c["hit_rate"], 0), pct(c["base_rate"], 0),
                pct(c["mean_r_calls"]), pct(c["mean_r_rest"]), pct(c["mean_dd_calls"]), pct(c["mean_dd_rest"]),
                pct(c["calls_also_mom_off"], 0), pct(c["mom_hit_rate"], 0), pct(c["mom_mean_r"])))
        a("")
    a("## Bonferroni survivors")
    a("")
    surv = []
    for asset in ASSETS:
        for i in o["inputs"]:
            for k, v in R[asset][i["name"]].items():
                if isinstance(v, dict) and v.get("bonferroni_sig"):
                    surv.append((v["p"], asset, i["label"], k, v["ic"], v.get("q_bh")))
    if surv:
        a("| Coin | Input | Test | Risk IC | p | BH q |")
        a("|---|---|---|---|---|---|")
        for p, asset, label, k, ic, qq in sorted(surv):
            a("| %s | %s | %s | %+.3f | %.2g | %.2g |" % (asset[:3], label, k, ic, p, qq))
    else:
        a("None.")
    a("")
    a("## Verdict against the registered bar")
    a("")
    a("| Input | Qualifies | Why not |")
    a("|---|---|---|")
    for i in o["inputs"]:
        v = o["verdict"][i["name"]]
        a("| %s | %s | %s |" % (i["label"], "YES" if v["qualifies"] else "no", "; ".join(v["why_not"]) or "-"))
    a("")
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
