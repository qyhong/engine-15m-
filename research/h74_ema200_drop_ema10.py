# -*- coding: utf-8 -*-
"""H74: the owner's daily pattern on BTC and ETH (registration: research/HYPOTHESES.md, H74).

After a daily close below the daily EMA200 (breakdown B) and a drop of more than 20% inside the
30 days after B, the first daily close back above the daily EMA10: does it win more than 60%?

Run on the research server:  python h74_ema200_drop_ema10.py <workdir> <mind15_data_dir>
  - fetches daily candles (public klines) into <workdir>/daily_<coin>.csv unless already there
  - reads <mind15_data_dir>/<coin>_15m.csv read-only
  - writes <workdir>/results.json, report.md, events.csv
"""
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
from scipy import stats

COINS = ["BTCUSDT", "ETHUSDT"]
BASE = "https://data-api.binance.vision/api/v3/klines"
FEE = 0.001                 # 0.05% per side
SEED = 20261122
NBOOT = 10000
DAY = timedelta(days=1)
READ_D = ["D1", "D2"]
READ_W = ["W1", "W2", "W3"]
HORIZON = {"W1": 10, "W2": 5}


# ---------------------------------------------------------------- data
def fetch_daily(sym, path, last_day_open_ms):
    import requests
    rows, cursor = [], int(datetime(2017, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
    sess = requests.Session()
    sess.headers["User-Agent"] = "python-requests"
    for _ in range(6):
        r = sess.get(BASE, params={"symbol": sym, "interval": "1d", "startTime": cursor, "limit": 1000}, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for k in batch:
            if int(k[0]) <= last_day_open_ms:
                rows.append((int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
        cursor = int(batch[-1][0]) + 86400000
        if len(batch) < 1000 or cursor > last_day_open_ms:
            break
        time.sleep(1.0)
    df = pd.DataFrame(rows, columns=["ts_ms", "open", "high", "low", "close", "volume"]).drop_duplicates("ts_ms")
    df.sort_values("ts_ms").to_csv(path, index=False)


def load_daily(path):
    df = pd.read_csv(path)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)).tz_localize(None)
    return df


def load_15m(path, last_day):
    df = pd.read_csv(path)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)).tz_localize(None)
    return df[df.index < last_day + DAY]


def ema(x, n):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


# ---------------------------------------------------------------- stats
def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def p60(k, n):
    if n == 0:
        return 1.0
    return float(stats.binomtest(k, n, 0.6, alternative="greater").pvalue)


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def n_needed(alpha):
    za = stats.norm.ppf(1 - alpha)
    return int(math.ceil(((za * 0.5 + 0.841621 * math.sqrt(0.24)) / 0.10) ** 2))


# ---------------------------------------------------------------- frame per coin
class Series:
    """closes / lows / EMAs on a contiguous time grid, with time -> index lookup."""

    def __init__(self, df, step):
        self.t = df.index
        self.c = df["close"].to_numpy(float)
        self.lo = df["low"].to_numpy(float)
        self.e10 = ema(self.c, 10)
        self.e200 = ema(self.c, 200) if step == DAY else None
        self.pos = {ts: i for i, ts in enumerate(self.t)}
        self.step = step

    def at(self, ts):
        return self.pos.get(ts)

    def cross_up(self, i):
        return (i >= 1 and not np.isnan(self.e10[i - 1]) and self.c[i] > self.e10[i]
                and self.c[i - 1] <= self.e10[i - 1])

    def outcome(self, i, horizon_steps):
        """-> dict W1, W2, W3 results (None when the horizon passes the data)."""
        out = {}
        for w, d in HORIZON.items():
            j = self.at(self.t[i] + d * DAY)
            out[w] = None if j is None else self.c[j] / self.c[i] - 1
        u = None
        for j in range(i + 1, len(self.c)):
            if self.c[j] < self.e10[j]:
                u = j
                break
        if u is None:
            out["W3"], out["held"], out["mae"] = None, None, None
        else:
            out["W3"] = self.c[u] / self.c[i] - 1
            out["held"] = (self.t[u] - self.t[i]) / DAY
            out["mae"] = float(np.min(self.lo[i + 1:u + 1]) / self.c[i] - 1)
            out["exit_day"] = str(self.t[u])
        if out.get("mae") is None and u is None:
            out["mae_open"] = float(np.min(self.lo[i + 1:]) / self.c[i] - 1) if i + 1 < len(self.c) else None
        return out


def win(w, r):
    if r is None:
        return None
    return (r - FEE > 0) if w == "W3" else (r > 0)


def breakdowns(d):
    """all breakdown indices, and the counted chain."""
    allb = [i for i in range(1, len(d.c)) if not np.isnan(d.e200[i - 1])
            and d.c[i] < d.e200[i] and d.c[i - 1] >= d.e200[i - 1]]
    counted, last = [], None
    for i in allb:
        if last is None or (d.t[i] - d.t[last]) > 30 * DAY:
            counted.append(i)
            last = i
    return allb, counted


def drop_day(d, b, D):
    """first index in [B, B+30] where the drop condition holds; also peak P."""
    pk = [d.at(d.t[b] - k * DAY) for k in range(1, 61)]
    pk = [j for j in pk if j is not None]
    P = float(np.max(d.c[pk]))
    low, deep = float("inf"), False
    end = d.t[b] + 30 * DAY
    i = b
    while i < len(d.c) and d.t[i] <= end:
        low = min(low, d.c[i])
        if d.c[i] <= 0.80 * d.e200[i]:
            deep = True
        if (D == "D1" and low <= 0.80 * P) or (D == "D2" and deep):
            return i, P
        i += 1
    return None, P


def daily_events(d, coin, last_day):
    allb, counted = breakdowns(d)
    ev, noentry, excl = {D: [] for D in READ_D}, {D: [] for D in READ_D}, {D: [] for D in READ_D}
    for D in READ_D:
        for b in allb:                                   # baseline exclusion: any breakdown with the drop met
            ds, _ = drop_day(d, b, D)
            if ds is not None:
                excl[D].append((max(d.t[b] + DAY, d.t[ds]), d.t[b] + 30 * DAY))
        for b in counted:
            ds, P = drop_day(d, b, D)
            if ds is None:
                continue
            start, end = max(d.t[b] + DAY, d.t[ds]), d.t[b] + 30 * DAY
            entry = None
            i = d.at(start)
            while i is not None and i < len(d.c) and d.t[i] <= end:
                if d.cross_up(i):
                    entry = i
                    break
                i += 1
            if entry is None:
                k30 = d.at(end)
                noentry[D].append({"coin": coin, "B": str(d.t[b].date()), "drop_day": str(d.t[ds].date()),
                                   "window_complete": end <= last_day,
                                   "chg_from_B_to_B30": None if k30 is None else d.c[k30] / d.c[b] - 1,
                                   "chg_from_dropday_to_B30": None if k30 is None else d.c[k30] / d.c[ds] - 1})
                continue
            seg = range(b, entry + 1)
            L = float(min(d.c[j] for j in seg))
            deepest = float(min(d.c[j] / d.e200[j] - 1 for j in seg))
            o = d.outcome(entry, None)
            ev[D].append(dict(coin=coin, B=str(d.t[b].date()), peak=P, drop_from_peak=1 - L / P,
                              deepest_below_ema200=deepest, drop_day=str(d.t[ds].date()),
                              entry_day=str(d.t[entry].date()), entry_ts=d.t[entry], entry_close=float(d.c[entry]),
                              below_ema200_at_entry=bool(d.c[entry] < d.e200[entry]), **o))
    return ev, noentry, excl, len(allb), len(counted)


def h4_events(d, h, coin, dev, start4):
    """4-hour entries for the same daily breakdowns/drops (descriptive)."""
    allb, counted = breakdowns(d)
    ev, excl = {D: [] for D in READ_D}, {D: [] for D in READ_D}
    for D in READ_D:
        for b in allb:
            ds, _ = drop_day(d, b, D)
            if ds is not None:
                excl[D].append((max(d.t[b], d.t[ds]) + DAY, d.t[b] + 30 * DAY))
        for b in counted:
            ds, P = drop_day(d, b, D)
            if ds is None:
                continue
            s, e = max(d.t[b], d.t[ds]) + DAY, d.t[b] + 31 * DAY      # bars opening in [s, e - 4h]
            if s < start4:
                continue
            entry = None
            for j in range(np.searchsorted(h.t, s), len(h.c)):
                if h.t[j] + timedelta(hours=4) > e:
                    break
                if h.cross_up(j):
                    entry = j
                    break
            if entry is None:
                continue
            o = h.outcome(entry, None)
            ev[D].append(dict(coin=coin, B=str(d.t[b].date()), drop_day=str(d.t[ds].date()),
                              entry_day=str(h.t[entry]), entry_ts=h.t[entry], entry_close=float(h.c[entry]), **o))
    return ev, excl


def baseline(s, excl, first_ok):
    """EMA10 up-crosses outside qualifying windows -> list of (month, results dict)."""
    out = []
    for i in range(1, len(s.c)):
        if s.t[i] < first_ok or not s.cross_up(i):
            continue
        day = s.t[i].normalize()
        if any(a <= day <= b for a, b in excl):
            continue
        out.append((s.t[i].strftime("%Y-%m"), s.outcome(i, None)))
    return out


def drift(d, n):
    ok = ~np.isnan(d.e200)
    k = tot = 0
    for i in np.where(ok)[0]:
        j = d.at(d.t[i] + n * DAY)
        if j is None:
            continue
        tot += 1
        k += d.c[j] > d.c[i]
    return k, tot


# ---------------------------------------------------------------- tests
def clusters(evs):
    evs = sorted(evs, key=lambda e: (e["entry_ts"], e["coin"]))
    cl, cur, last = [], [], None
    for e in evs:
        if last is not None and (e["entry_ts"] - last) > 10 * DAY:
            cl.append(cur)
            cur = []
        cur.append(e)
        last = e["entry_ts"]
    if cur:
        cl.append(cur)
    return cl


def boot_diff(groups, base, w, rng):
    """groups: list of lists of event wins (resampling units); base: list of (month, win)."""
    bm = {}
    for m, x in base:
        bm.setdefault(m, []).append(x)
    months = list(bm.values())
    bk = np.array([sum(v) for v in months], float)
    bn = np.array([len(v) for v in months], float)
    gk = np.array([sum(g) for g in groups], float)
    gn = np.array([len(g) for g in groups], float)
    rates, diffs = [], []
    for _ in range(NBOOT):
        gi = rng.integers(0, len(groups), len(groups))
        bi = rng.integers(0, len(months), len(months))
        r = gk[gi].sum() / gn[gi].sum()
        rb = bk[bi].sum() / bn[bi].sum()
        rates.append(r)
        diffs.append(r - rb)
    return (float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5)),
            float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))


def cell(evs, base_items, w, pooled, rng):
    evs = [e for e in evs if e[w] is not None]
    base = [(m, win(w, o[w])) for m, o in base_items if o[w] is not None]
    bw = sum(x for _, x in base) / len(base) if base else float("nan")
    res = {"events": len(evs), "baseline_n": len(base), "baseline_rate": bw}
    if not evs:
        res.update(episodes=0, wins=0, rate=None, wilson=None, p60=1.0, diff=None, diff_ci=None)
        return res
    wins = [win(w, e[w]) for e in evs]
    cl = clusters(evs)
    res["episodes"] = len(cl)
    res["wins"] = int(sum(wins))
    res["rate"] = sum(wins) / len(wins)
    if pooled:
        reps = [c[0] for c in cl]
        k = int(sum(win(w, e[w]) for e in reps))
        res["rep_wins"], res["rep_n"] = k, len(reps)
        res["wilson"] = wilson(k, len(reps))
        res["p60"] = p60(k, len(reps))
        groups = [[win(w, e[w]) for e in c] for c in cl]
        lo, hi, dlo, dhi = boot_diff(groups, base, w, rng)
        res["cluster_boot_ci"] = (lo, hi)
    else:
        res["wilson"] = wilson(res["wins"], len(wins))
        res["p60"] = p60(res["wins"], len(wins))
        groups = [[x] for x in wins]
        _, _, dlo, dhi = boot_diff(groups, base, w, rng)
    res["diff"] = res["rate"] - bw
    res["diff_ci"] = (dlo, dhi)
    return res


def verdict(c, padj):
    if c["events"] == 0:
        return "too few cases to tell"
    if padj < 0.05 and c["diff_ci"][0] > 0:
        return "supported"
    if c["wilson"][1] < 0.60:
        return "not supported"
    return "too few cases to tell"


def summarize(evs, w, fee):
    r = [e[w] - (fee if fee else 0) for e in evs if e[w] is not None]
    if not r:
        return None
    return {"n": len(r), "mean": float(np.mean(r)), "median": float(np.median(r)), "worst": float(np.min(r)),
            "best": float(np.max(r)), "win_rate": float(np.mean([x > 0 for x in r]))}


# ---------------------------------------------------------------- main
def main():
    work, mdata = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc)
    last_day = pd.Timestamp(now.date()) - DAY                        # last complete UTC day (open time)
    last_ms = int(pd.Timestamp(last_day, tz="UTC").timestamp() * 1000)
    rng = np.random.default_rng(SEED)
    R = {"run_utc": now.isoformat(), "last_complete_day": str(last_day.date()), "fee_round_trip": FEE}
    daily, h4, check, fetched = {}, {}, {}, True
    for coin in COINS:
        p = os.path.join(work, "daily_%s.csv" % coin.lower())
        if not os.path.exists(p):
            try:
                fetch_daily(coin, p, last_ms)
            except Exception as ex:                                  # noqa
                fetched = False
                R["fetch_error_" + coin] = repr(ex)
        f15 = load_15m(os.path.join(mdata, "%s_15m.csv" % coin.lower()), last_day)
        g = f15["close"].resample("1D").agg(["last", "count"])
        d15 = g[g["count"] == 96]["last"]
        if fetched and os.path.exists(p):
            dd = load_daily(p)
            dd = dd[dd.index <= last_day]
            ov = dd["close"].reindex(d15.index).dropna()
            diff = (ov - d15.reindex(ov.index)).abs()
            rel = diff / d15.reindex(ov.index)
            gaps = int(((dd.index[1:] - dd.index[:-1]) != DAY).sum())
            check[coin] = {"daily_first": str(dd.index[0].date()), "daily_last": str(dd.index[-1].date()),
                           "daily_rows": len(dd), "grid_gaps": gaps, "overlap_days": int(len(ov)),
                           "max_abs_diff": float(diff.max()), "max_rel_diff": float(rel.max()),
                           "days_rel_diff_over_1e-6": int((rel > 1e-6).sum()),
                           "15m_days_incomplete": int((g["count"] != 96).sum())}
            if gaps:
                full = pd.date_range(dd.index[0], dd.index[-1], freq="1D")
                missing = full.difference(dd.index)
                check[coin]["missing_days"] = [str(x.date()) for x in missing][:20]
        else:
            agg = f15.resample("1D").agg({"close": "last", "low": "min"}).dropna()
            dd = agg[agg.index <= last_day]
        daily[coin] = Series(dd, DAY)
        a4 = f15.resample("4h").agg({"close": "last", "low": "min", "open": "count"})
        a4 = a4[a4["open"] == 16]
        h4[coin] = (Series(a4, timedelta(hours=4)), a4.index[0])
    R["data_check"], R["fetched_daily"] = check, fetched

    events, noentry, excl, cnt, drift_r = {}, {}, {}, {}, {}
    ev4, excl4 = {}, {}
    for coin in COINS:
        d = daily[coin]
        events[coin], noentry[coin], excl[coin], na, nc = daily_events(d, coin, last_day)
        cnt[coin] = {"breakdowns": na, "counted_breakdowns": nc}
        drift_r[coin] = {w: drift(d, n) for w, n in HORIZON.items()}
        h, s4 = h4[coin]
        ev4[coin], excl4[coin] = h4_events(d, h, coin, None, s4 + timedelta(days=3))
    R["counts"] = cnt

    first_ok = {c: daily[c].t[int(np.where(~np.isnan(daily[c].e200))[0][0])] for c in COINS}
    base = {c: {D: baseline(daily[c], excl[c][D], first_ok[c]) for D in READ_D} for c in COINS}
    base4 = {c: {D: baseline(h4[c][0], excl4[c][D], h4[c][1] + timedelta(days=3)) for D in READ_D} for c in COINS}

    def table(EV, BASE, tag):
        out = {}
        for samp in ["BTCUSDT", "ETHUSDT", "pooled"]:
            cells = {}
            for D in READ_D:
                for w in READ_W:
                    if samp == "pooled":
                        evs = EV["BTCUSDT"][D] + EV["ETHUSDT"][D]
                        bb = BASE["BTCUSDT"][D] + BASE["ETHUSDT"][D]
                    else:
                        evs, bb = EV[samp][D], BASE[samp][D]
                    cells[D + w] = cell(evs, bb, w, samp == "pooled", rng)
            keys = list(cells)
            adj = holm([cells[k]["p60"] for k in keys])
            for k, a in zip(keys, adj):
                cells[k]["p60_holm"] = a
                cells[k]["verdict"] = verdict(cells[k], a) if tag == "daily" else "descriptive"
            out[samp] = cells
        return out

    R["daily"] = table(events, base, "daily")
    R["h4"] = table(ev4, base4, "h4")
    R["drift_all_days"] = {c: {w: {"up": k, "n": n, "rate": k / n} for w, (k, n) in v.items()} for c, v in drift_r.items()}
    pk = {w: sum(drift_r[c][w][0] for c in COINS) for w in HORIZON}
    pn = {w: sum(drift_r[c][w][1] for c in COINS) for w in HORIZON}
    R["drift_all_days"]["pooled"] = {w: {"up": pk[w], "n": pn[w], "rate": pk[w] / pn[w]} for w in HORIZON}
    R["n_needed_60_vs_50_power80"] = {"alpha_0.05": n_needed(0.05), "alpha_0.05/6": n_needed(0.05 / 6)}

    # descriptive
    desc = {}
    for D in READ_D:
        allev = sorted(events["BTCUSDT"][D] + events["ETHUSDT"][D], key=lambda e: e["entry_ts"])
        half = int(math.ceil(len(allev) / 2))
        parts = {"all": allev, "first_half": allev[:half], "second_half": allev[half:],
                 "2017_2019": [e for e in allev if e["entry_ts"].year <= 2019],
                 "2020_on": [e for e in allev if e["entry_ts"].year >= 2020],
                 "BTCUSDT": [e for e in allev if e["coin"] == "BTCUSDT"],
                 "ETHUSDT": [e for e in allev if e["coin"] == "ETHUSDT"]}
        desc[D] = {name: {w + ("_fee" if f else ""): summarize(evs, w, f)
                          for w in READ_W for f in ([0, FEE] if w != "W3" else [FEE])} for name, evs in parts.items()}
        desc[D]["no_entry"] = noentry["BTCUSDT"][D] + noentry["ETHUSDT"][D]
        desc[D]["open_W3"] = [e["coin"] + " " + e["entry_day"] for e in allev if e["W3"] is None]
        allev4 = ev4["BTCUSDT"][D] + ev4["ETHUSDT"][D]
        desc[D]["h4_all"] = {w + ("_fee" if f else ""): summarize(allev4, w, f)
                             for w in READ_W for f in ([0, FEE] if w != "W3" else [FEE])}
    R["descriptive"] = desc

    # events table
    rows = []
    for tag, EV in [("daily", events), ("4h", ev4)]:
        for c in COINS:
            for D in READ_D:
                for e in EV[c][D]:
                    rows.append({"signal": tag, "reading_D": D, **{k: v for k, v in e.items() if k != "entry_ts"}})
    pd.DataFrame(rows).to_csv(os.path.join(work, "events.csv"), index=False)
    R["events"] = {D: [{k: v for k, v in e.items() if k != "entry_ts"}
                       for e in sorted(events["BTCUSDT"][D] + events["ETHUSDT"][D], key=lambda e: e["entry_ts"])]
                   for D in READ_D}
    with open(os.path.join(work, "results.json"), "w") as fh:
        json.dump(R, fh, indent=1, default=str)
    write_report(R, work)


def pc(x, nd=1):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else ("%.*f%%" % (nd, 100 * x))


def write_report(R, work):
    L = ["# H74 report: EMA200 breakdown + 20% drop, then the first close above EMA10 (BTC, ETH)", "",
         "Run %s; data to the last complete UTC day %s. Fetched daily candles: %s." % (
             R["run_utc"][:16], R["last_complete_day"], R["fetched_daily"]), ""]
    L.append("## Data check (fetched daily close vs daily close from stored 15m bars)")
    for c, v in R["data_check"].items():
        L.append("- %s: %s" % (c, json.dumps(v)))
    L.append("- breakdowns (all / counted): %s" % json.dumps(R["counts"]))
    L += ["", "Needed independent cases to tell 60%% from 50%% at 80%% power: %s" % json.dumps(R["n_needed_60_vs_50_power80"]), ""]
    for tag in ["daily", "h4"]:
        L.append("## %s signal%s" % ("Daily" if tag == "daily" else "4-hour", "" if tag == "daily" else " (DESCRIPTIVE ONLY)"))
        L.append("")
        L.append("| sample | reading | events | episodes | wins | win rate | 95% interval | p vs 60% | Holm p | "
                 "baseline (crosses) | diff [95%] | verdict |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for samp, cells in R[tag].items():
            for k, c in cells.items():
                if c["rate"] is None:
                    L.append("| %s | %s | 0 | 0 | 0 | - | - | - | - | %s | - | %s |" % (samp, k, pc(c["baseline_rate"]), c["verdict"]))
                    continue
                wi = "%s-%s" % (pc(c["wilson"][0]), pc(c["wilson"][1]))
                if samp == "pooled":
                    wi += " (1/cluster %d/%d); cluster boot %s-%s" % (c["rep_wins"], c["rep_n"],
                                                                      pc(c["cluster_boot_ci"][0]), pc(c["cluster_boot_ci"][1]))
                L.append("| %s | %s | %d | %d | %d | %s | %s | %.3f | %.3f | %s (n=%d) | %s [%s, %s] | %s |" % (
                    samp, k, c["events"], c["episodes"], c["wins"], pc(c["rate"]), wi, c["p60"], c["p60_holm"],
                    pc(c["baseline_rate"]), c["baseline_n"], pc(c["diff"]), pc(c["diff_ci"][0]), pc(c["diff_ci"][1]),
                    c["verdict"]))
        L.append("")
    L.append("Drift baseline (share of all days with a higher close N days later): %s" % json.dumps(
        {c: {w: round(v["rate"], 3) for w, v in d.items()} for c, d in R["drift_all_days"].items()}))
    L += ["", "## Result per trade (descriptive)", ""]
    for D, dd in R["descriptive"].items():
        L.append("### %s" % D)
        L.append("| part | measure | n | mean | median | worst | best | share > 0 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for part, m in dd.items():
            if part in ("no_entry", "open_W3"):
                continue
            for w, s in m.items():
                if s:
                    L.append("| %s | %s | %d | %s | %s | %s | %s | %s |" % (part, w, s["n"], pc(s["mean"]), pc(s["median"]),
                                                                       pc(s["worst"]), pc(s["best"]), pc(s["win_rate"])))
        L.append("")
        L.append("Open under W3: %s" % dd["open_W3"])
        L.append("")
        L.append("Windows with the drop met but no EMA10 cross (%d):" % len(dd["no_entry"]))
        for x in dd["no_entry"]:
            L.append("- %s B %s drop day %s complete=%s B->B+30 %s, drop day->B+30 %s" % (
                x["coin"], x["B"], x["drop_day"], x["window_complete"], pc(x["chg_from_B_to_B30"]),
                pc(x["chg_from_dropday_to_B30"])))
        L.append("")
    L += ["## Events (daily signal)", ""]
    for D, evs in R["events"].items():
        L.append("### %s" % D)
        L.append("| coin | B | drop from peak | deepest below EMA200 | drop day | entry day | entry close | below EMA200 at entry | W1 | W2 | W3 (gross) | days held | largest fall |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for e in evs:
            L.append("| %s | %s | %s | %s | %s | %s | %.2f | %s | %s | %s | %s | %s | %s |" % (
                e["coin"], e["B"], pc(e["drop_from_peak"]), pc(e["deepest_below_ema200"]), e["drop_day"], e["entry_day"],
                e["entry_close"], e["below_ema200_at_entry"], pc(e["W1"]), pc(e["W2"]), pc(e["W3"]),
                "-" if e["held"] is None else "%d" % e["held"], pc(e["mae"])))
        L.append("")
    with open(os.path.join(work, "report.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
