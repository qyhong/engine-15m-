# -*- coding: utf-8 -*-
"""Queue family H102-H106: simple chart-pattern claims on BTC and ETH daily bars. Research only; registered in
research/HYPOTHESES.md before any number. Daily UTC bars are built from the stored 15-minute bars (2019 onward) and END
at 2025-11-10 (the holdout, 2025-11-11 onward, is not read: wall() is the one place that enforces it).

    python research/queue/pattern.py --study H102 --out <out dir> [--fits-dir ignored] [--smoke] [--estimate]
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from engine15 import data  # noqa: E402

DATA_END = "2025-11-10 23:45"           # THE HOLDOUT WALL: the last 15-minute bar (open time) that may be read
DATA_START = "2019-01-01"
HALF = "2023-06-08"                     # halves by entry day, as Part A
COINS = ("BTCUSDT", "ETHUSDT")
FEE_SIDE = 0.0005
CLUSTER_DAYS = 10
SEED = 20261122
DRAWS = 10000
N_PART_B = 18                           # tests in Part B (H102: 2 kinds x 3 readings; H103-H106: 3 each)
ALPHA = 0.05 / N_PART_B
READINGS = ("W5", "W10", "WEMA10")

STUDIES = {
    "H102": {"title": "golden cross and death cross (daily EMA50 against EMA200)",
             "kinds": [("golden_cross_long", 1, 0.55), ("death_cross_short", -1, 0.55)]},
    "H103": {"title": "daily RSI(14) at or below 30, entry on the first close back above 30",
             "kinds": [("rsi30_reclaim_long", 1, 0.55)]},
    "H104": {"title": "three consecutive daily closes down totalling at least 10%, entry at the third close",
             "kinds": [("three_down_10pct_long", 1, 0.55)]},
    "H105": {"title": "a daily close back above the EMA200 after at least 30 days below it",
             "kinds": [("ema200_reclaim_after_30d_long", 1, 0.55)]},
    "H106": {"title": "the mirror of H74: after a rise above the daily EMA200 of more than 20%, the first close back "
                      "below the daily EMA10, going short", "kinds": [("ema200_rise_ema10_break_short", -1, 0.50)]},
}


class HoldoutError(RuntimeError):
    pass


def wall(ts):
    t = pd.Timestamp(ts, tz="UTC") if not isinstance(ts, pd.Timestamp) else ts
    if t > pd.Timestamp(DATA_END, tz="UTC"):
        raise HoldoutError("refused: %s is after the holdout wall %s" % (t, DATA_END))
    return t


# ---------------------------------------------------------------------------------------------------- data
def daily_from_15m(df, end=DATA_END):
    """UTC daily bars from 15-minute bars opening at or after DATA_START and at or before `end` (never past the wall)."""
    end_t = wall(end)
    df = df[(df.index >= pd.Timestamp(DATA_START, tz="UTC")) & (df.index <= end_t)]
    g = df.groupby(df.index.floor("D"))
    d = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(),
                      "bars": g["close"].count()})
    return d


def ema(c, n):
    """alpha 2/(n+1), seeded with the simple mean of the first n closes, defined from the n-th close on (as H74)."""
    c = np.asarray(c, float)
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    a = 2.0 / (n + 1)
    out[n - 1] = c[:n].mean()
    for i in range(n, len(c)):
        out[i] = a * c[i] + (1 - a) * out[i - 1]
    return out


def rsi(c, n=14):
    """Wilder's RSI: average gain and loss seeded with the simple mean of the first n changes."""
    c = np.asarray(c, float)
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    ch = np.diff(c)
    g, l_ = np.maximum(ch, 0), np.maximum(-ch, 0)
    ag, al = g[:n].mean(), l_[:n].mean()
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ag = (ag * (n - 1) + g[i - 1]) / n
        al = (al * (n - 1) + l_[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


# ---------------------------------------------------------------------------------------------------- events
def events_for(kind, c):
    """Entry day indices (into the daily close array c) of one event kind. Each uses closes up to its entry day only."""
    c = np.asarray(c, float)
    n = len(c)
    e10, e50, e200 = ema(c, 10), ema(c, 50), ema(c, 200)
    ok = lambda *xs: all(np.isfinite(x) for x in xs)   # noqa: E731
    ev = []
    if kind in ("golden_cross_long", "death_cross_short"):
        s = 1 if kind == "golden_cross_long" else -1
        for d in range(1, n):
            if ok(e50[d], e200[d], e50[d - 1], e200[d - 1]):
                if s == 1 and e50[d] > e200[d] and e50[d - 1] <= e200[d - 1]:
                    ev.append(d)
                if s == -1 and e50[d] < e200[d] and e50[d - 1] >= e200[d - 1]:
                    ev.append(d)
    elif kind == "rsi30_reclaim_long":
        r = rsi(c)
        ev = [d for d in range(1, n) if ok(r[d], r[d - 1]) and r[d - 1] <= 30 and r[d] > 30]
    elif kind == "three_down_10pct_long":
        in_streak_event = False
        for d in range(1, n):
            if c[d] >= c[d - 1]:
                in_streak_event = False                      # the down streak is broken
                continue
            if d >= 3 and c[d] < c[d - 1] < c[d - 2] < c[d - 3] and c[d] / c[d - 3] - 1 <= -0.10 and not in_streak_event:
                ev.append(d)
                in_streak_event = True                       # one event per down streak
    elif kind == "ema200_reclaim_after_30d_long":
        for d in range(31, n):
            if ok(e200[d]) and c[d] > e200[d] and all(np.isfinite(e200[d - k]) and c[d - k] < e200[d - k] for k in range(1, 31)):
                ev.append(d)
    elif kind == "ema200_rise_ema10_break_short":
        last_b = None
        for B in range(1, n):
            if not ok(e200[B], e200[B - 1]) or not (c[B] > e200[B] and c[B - 1] <= e200[B - 1]):
                continue
            if last_b is not None and B - last_b <= 30:
                continue
            last_b = B
            if B < 60:
                continue
            P = c[B - 60:B].min()
            dstar = None
            for d in range(B, min(B + 30, n - 1) + 1):
                if c[B:d + 1].max() >= 1.20 * P:
                    dstar = d
                    break
            if dstar is None:
                continue
            for t in range(max(B + 1, dstar), min(B + 30, n - 1) + 1):
                if ok(e10[t], e10[t - 1]) and c[t] < e10[t] and c[t - 1] >= e10[t - 1]:
                    ev.append(t)
                    break
    else:
        raise ValueError(kind)
    return ev


def outcome(c, e10, t, side, reading):
    """win (True/False) or None (horizon past the data) of a trade entered at close t on `side`."""
    n = len(c)
    if reading in ("W5", "W10"):
        h = 5 if reading == "W5" else 10
        if t + h >= n:
            return None
        return bool(side * (c[t + h] - c[t]) > 0)
    for u in range(t + 1, n):
        if np.isfinite(e10[u]) and ((side == 1 and c[u] < e10[u]) or (side == -1 and c[u] > e10[u])):
            res = side * (c[u] / c[t] - 1) - 2 * FEE_SIDE
            return bool(res > 0)
    return None


# ---------------------------------------------------------------------------------------------------- statistics
def wilson(k, n, z=1.959964):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def binom_p_upper(k, n, thr):
    """exact one-sided P(X >= k) for X ~ Binomial(n, thr)."""
    if n == 0:
        return None
    return float(sum(math.comb(n, i) * thr ** i * (1 - thr) ** (n - i) for i in range(k, n + 1)))


def clusters(entries, days=CLUSTER_DAYS):
    """entries: list of (day_ms, coin). Single linkage: sorted by day, a gap over `days` starts a new cluster."""
    order = sorted(range(len(entries)), key=lambda i: (entries[i][0], COINS.index(entries[i][1]) if entries[i][1] in COINS else 9))
    lab = [0] * len(entries)
    cl, prev = -1, None
    for i in order:
        if prev is None or (entries[i][0] - prev) / 86400000.0 > days:
            cl += 1
        lab[i] = cl
        prev = entries[i][0]
    return lab, order


def analyse(evs, base, thr, alpha=ALPHA, draws=DRAWS, seed=SEED):
    """evs: list of dicts (day_ms, coin, win); base: list of (month, win) for the baseline days."""
    evs = [e for e in evs if e["win"] is not None]
    n = len(evs)
    out = {"events": n, "wins": int(sum(e["win"] for e in evs)), "threshold": thr}
    if n == 0:
        out.update(conclusion="too few cases to tell", episodes=0)
        return out
    lab, order = clusters([(e["day_ms"], e["coin"]) for e in evs])
    first = {}
    for i in order:
        first.setdefault(lab[i], i)
    one = [evs[i]["win"] for i in sorted(first.values())]
    k1, n1 = int(sum(one)), len(one)
    lo, hi = wilson(k1, n1)
    p = binom_p_upper(k1, n1, thr)
    rng = np.random.default_rng(seed)
    ncl = max(lab) + 1
    by_cl = [[evs[i]["win"] for i in range(n) if lab[i] == c] for c in range(ncl)]
    w_cl = np.array([sum(x) for x in by_cl], float)
    n_cl = np.array([len(x) for x in by_cl], float)
    bm = pd.DataFrame(base, columns=["m", "w"]) if base else pd.DataFrame(columns=["m", "w"])
    months = bm.groupby("m")["w"].agg(["sum", "count"]) if len(bm) else None
    rates, diffs = [], []
    for _ in range(draws):
        ix = rng.integers(0, ncl, ncl)
        r = w_cl[ix].sum() / n_cl[ix].sum()
        rates.append(r)
        if months is not None:
            jx = rng.integers(0, len(months), len(months))
            br = months["sum"].values[jx].sum() / months["count"].values[jx].sum()
            diffs.append(r - br)
    base_rate = float(bm["w"].mean()) if len(bm) else None
    out.update(episodes=n1, episode_wins=k1, rate_all=out["wins"] / n, rate_episodes=k1 / n1, wilson_episodes=[lo, hi],
               p_binom_episodes=p, cluster_interval=[float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))],
               baseline_rate=base_rate, baseline_days=int(len(bm)),
               diff=None if base_rate is None else out["wins"] / n - base_rate,
               diff_interval=[float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))] if diffs else None,
               alpha=alpha)
    if p < alpha and diffs and out["diff_interval"][0] > 0:
        out["conclusion"] = "supported"
    elif hi < thr:
        out["conclusion"] = "not supported"
    else:
        out["conclusion"] = "too few cases to tell"
    return out


# ---------------------------------------------------------------------------------------------------- the study
def load_daily(coin, end=DATA_END):
    return daily_from_15m(data.load(coin), end)


def run_study(study, out, smoke=False, log=print):
    t0 = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    end = "2021-12-31 23:45" if smoke else DATA_END
    st = STUDIES[study]
    total = len(st["kinds"]) * len(READINGS)
    days = {}
    for coin in COINS:
        days[coin] = load_daily(coin, end)
    res = {"study": study, "title": st["title"], "smoke": smoke, "data": {}, "cells": {}, "events": {}}
    for coin, d in days.items():
        res["data"][coin] = {"first": str(d.index[0])[:10], "last": str(d.index[-1])[:10], "days": int(len(d)),
                             "days_short_of_96_bars": int((d["bars"] < 96).sum())}
    done = 0
    for kind, side, thr in st["kinds"]:
        rows = []
        per_coin = {}
        for coin, d in days.items():
            c = d["close"].values
            e10, e200 = ema(c, 10), ema(c, 200)
            ev = events_for(kind, c)
            per_coin[coin] = (d, c, e10, e200, ev)
            for t in ev:
                rows.append({"coin": coin, "day": str(d.index[t])[:10], "close": float(c[t]),
                             "W5": outcome(c, e10, t, side, "W5"), "W10": outcome(c, e10, t, side, "W10"),
                             "WEMA10": outcome(c, e10, t, side, "WEMA10")})
        res["events"][kind] = rows
        for reading in READINGS:
            evs, base, halves = [], [], {"first": [], "second": []}
            for coin, (d, c, e10, e200, ev) in per_coin.items():
                evset = set(ev)
                for t in ev:
                    w = outcome(c, e10, t, side, reading)
                    day_ms = int(d.index[t].value // 10 ** 6)
                    evs.append({"day_ms": day_ms, "coin": coin, "win": w})
                    if w is not None:
                        halves["first" if str(d.index[t])[:10] < HALF else "second"].append(w)
                for t in range(len(c)):                      # the baseline: the same trade on every other day
                    if t in evset or not np.isfinite(e200[t]):
                        continue
                    w = outcome(c, e10, t, side, reading)
                    if w is not None:
                        base.append((str(d.index[t])[:7], w))
            cell = analyse(evs, base, thr)
            cell["halves"] = dict((k, {"events": len(v), "win_rate": (sum(v) / len(v)) if v else None}) for k, v in halves.items())
            cell["per_coin"] = dict((coin, {"events": sum(1 for e in evs if e["coin"] == coin and e["win"] is not None),
                                            "wins": sum(1 for e in evs if e["coin"] == coin and e["win"])}) for coin in COINS)
            res["cells"]["%s|%s" % (kind, reading)] = cell
            done += 1
            json.dump({"done": done, "total": total, "started_utc": started,
                       "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "est_hours_left": round((total - done) * (time.time() - t0) / done / 3600, 4)},
                      open(os.path.join(out, "progress.json"), "w"))
    res["alpha"], res["n_tests_part_b"] = ALPHA, N_PART_B
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report(res))
    open(os.path.join(out, "DONE"), "w").close()
    return res


def _pct(x):
    return "-" if x is None else "%.1f%%" % (100 * x)


def report(res):
    words = [c["conclusion"] for c in res["cells"].values()]
    head = "supported" if "supported" in words else "not supported" if all(w == "not supported" for w in words) else \
        "mixed: see the cells" if "not supported" in words else "too few cases to tell"
    L = ["# %s: %s%s" % (res["study"], res["title"], " (SMOKE RUN ON A TINY SLICE: NOT A RESULT)" if res["smoke"] else ""), "",
         "**Conclusion: %s.** (%d readings; each is judged at alpha %.4f = 0.05 / %d Part B tests)" % (
             head, len(words), res["alpha"], res["n_tests_part_b"]), "",
         "| event, reading | conclusion | events / episodes | win rate (all) | per episode [95% Wilson] | p vs threshold |"
         " cluster interval | baseline | difference [95%] | first half / second half |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in res["cells"].items():
        if not c.get("episodes"):
            L.append("| %s | %s | 0 | - | - | - | - | - | - | - |" % (k.replace("|", " / "), c["conclusion"]))
            continue
        L.append("| %s (threshold %s) | %s | %d / %d | %s | %s [%s, %s] | %.4f | %s-%s | %s | %s [%s, %s] | %s (%d) / %s (%d) |" % (
            k.replace("|", " / "), _pct(c["threshold"]), c["conclusion"], c["events"], c["episodes"], _pct(c["rate_all"]), _pct(c["rate_episodes"]),
            _pct(c["wilson_episodes"][0]), _pct(c["wilson_episodes"][1]), c["p_binom_episodes"], _pct(c["cluster_interval"][0]),
            _pct(c["cluster_interval"][1]), _pct(c["baseline_rate"]), _pct(c["diff"]),
            _pct(c["diff_interval"][0]) if c["diff_interval"] else "-", _pct(c["diff_interval"][1]) if c["diff_interval"] else "-",
            _pct(c["halves"]["first"]["win_rate"]), c["halves"]["first"]["events"], _pct(c["halves"]["second"]["win_rate"]),
            c["halves"]["second"]["events"]))
    L += ["", "Data: " + "; ".join("%s %s to %s (%d days)" % (k, v["first"], v["last"], v["days"]) for k, v in res["data"].items()),
          "The holdout (2025-11-11 onward) was not read. A history check is not proof of anything; a 'supported' reading",
          "leads at most to a proposal for a forward paper shadow book, on the owner's word."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, choices=sorted(STUDIES))
    ap.add_argument("--fits-dir")
    ap.add_argument("--out")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.estimate:
        print("0.020")
        return 0
    if not a.out:
        ap.error("--out is required")
    out = os.path.join(a.out, "smoke") if a.smoke else a.out
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "DONE")):
        print("already DONE: %s" % out)
        return 0
    run_study(a.study, out, smoke=a.smoke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
