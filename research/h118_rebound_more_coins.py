# -*- coding: utf-8 -*-
"""H118: H107's capitulation-rebound rules A and B, UNCHANGED, on ten more coins (test 1, the decision) and on BTC and
ETH's years before October 2019 (test 2, descriptive). Research only; registered in research/HYPOTHESES.md (H118)
before any H118 number was computed and before the data was downloaded. Changes nothing in the engine, the books or the
vault. Every rule, the trade walk, the bootstrap and the look-ahead guard's readings come from H107's script by import.

    py -3 -X utf8 research/h118_rebound_more_coins.py --download    # fetch the data into data/sources/h118/
    py -3 -X utf8 research/h118_rebound_more_coins.py               # the registered run

Nothing from 2025-11-11 00:00 UTC on is downloaded (the sealed holdout), and every input is cut at the bar opening
2025-11-10 23:45 UTC before anything is computed.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data  # noqa: E402
import h107_capitulation_rebound as H  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h118_rebound_more_coins")
DDIR = os.path.join(ROOT, "data", "sources", "h118")
H107_RESULTS = os.path.join(ROOT, "research", "out", "h107_capitulation_rebound", "results.json")
ALTS = ("ADAUSDT", "AVAXUSDT", "BNBUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "TRXUSDT", "XRPUSDT")
OLD = ("BTCUSDT", "ETHUSDT")
CUT = H.CUT                                  # "2025-11-10 23:45": last bar that may be read
MID = H.MID                                  # "2023-06-08 00:00"
PRE_DECIDE_END = "2019-09-30 23:45"          # test 2: last deciding bar
PRE_FILE_END = "2019-10-05 23:45"            # test 2: last bar in the pre-2019 files (trades decided by 30 Sep finish)
REG = H.REG                                  # unchanged
B, SEED = 10000, 20261126
MIN_ALL, MIN_HALF, MIN_COIN_N, MIN_COINS_POS = 100, 30, 5, 7
ALPHA = 0.05
KLINES = "https://data-api.binance.vision/api/v3/klines"
FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
BAR = 900000
MAX_MB = 320


def ms(ts):
    return int(pd.Timestamp(ts, tz="UTC").value // 10**6)


def kline_path(coin):
    return os.path.join(DDIR, coin.lower() + ("_15m_pre2019.csv" if coin in OLD else "_15m.csv"))


def funding_path(coin):
    return os.path.join(DDIR, coin.lower() + "_funding.csv")


# ------------------------------------------------------------------------------------------------- download
class Blocked(Exception):
    pass


def get_json(url, params, tries=8):
    import requests
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 451):
                raise Blocked("%s %s" % (r.status_code, r.text[:200]))
            last = "HTTP %s %s" % (r.status_code, r.text[:200])
            time.sleep(60 if r.status_code in (418, 429) else 2 * (i + 1))
        except requests.RequestException as e:
            last = repr(e)
            time.sleep(2 * (i + 1))
    raise RuntimeError("gave up on %s %s: %s" % (url, params, last))


def fetch_klines(coin, end_open_ms, log=print):
    """Every 15m bar from the coin's first to the bar opening at end_open_ms (inclusive). 1000 a page, 0.2 s pause."""
    rows, cursor, pages = [], 0, 0
    while cursor <= end_open_ms:
        batch = get_json(KLINES, {"symbol": coin, "interval": "15m", "startTime": cursor,
                                  "endTime": end_open_ms + BAR - 1, "limit": 1000})
        pages += 1
        if not batch:
            break
        for k in batch:
            if int(k[0]) <= end_open_ms:
                rows.append((int(k[0]), k[1], k[2], k[3], k[4], k[5], k[9]))
        cursor = int(batch[-1][0]) + BAR
        if pages % 50 == 0:
            log("  %s %d bars, at %s" % (coin, len(rows), pd.to_datetime(cursor, unit="ms")))
        if len(batch) < 1000:
            break
        time.sleep(0.2)
    df = pd.DataFrame(rows, columns=["ts_ms"] + data.COLS).drop_duplicates("ts_ms").sort_values("ts_ms")
    assert len(df) == 0 or int(df["ts_ms"].iloc[-1]) <= end_open_ms, "holdout bar fetched"
    return df, pages


def fetch_funding(coin):
    """Every funding rate set before 2025-11-11 00:00 UTC (strictly)."""
    end = ms("2025-11-11 00:00") - 1
    rows, cursor = [], ms("2017-01-01 00:00")
    while True:
        batch = get_json(FUNDING, {"symbol": coin, "startTime": cursor, "endTime": end, "limit": 1000})
        rows += [(int(b["fundingTime"]), b["fundingRate"]) for b in batch]
        if len(batch) < 1000:
            break
        cursor = int(batch[-1]["fundingTime"]) + 1
        time.sleep(0.3)
    df = pd.DataFrame(rows, columns=["ts_ms", "rate"]).drop_duplicates("ts_ms").sort_values("ts_ms")
    assert len(df) == 0 or int(df["ts_ms"].iloc[-1]) <= end, "holdout funding fetched"
    return df


def write_csv(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def total_mb():
    return sum(os.path.getsize(os.path.join(DDIR, f)) for f in os.listdir(DDIR) if f.endswith(".csv")) / 1e6


def download(log=print):
    os.makedirs(DDIR, exist_ok=True)
    t0 = time.time()
    rec = {"started_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "klines": {}, "funding": {},
           "funding_blocked": None}
    jobs = [(c, ms(CUT)) for c in ALTS] + [(c, ms(PRE_FILE_END)) for c in OLD]
    for coin, end in jobs:
        if os.path.exists(kline_path(coin)):
            log("%s: already there, kept" % coin)
            continue
        t1 = time.time()
        df, pages = fetch_klines(coin, end, log)
        write_csv(df, kline_path(coin))
        rec["klines"][coin] = {"rows": int(len(df)), "pages": pages, "seconds": round(time.time() - t1, 1),
                               "first": str(pd.to_datetime(df["ts_ms"].iloc[0], unit="ms")),
                               "last": str(pd.to_datetime(df["ts_ms"].iloc[-1], unit="ms"))}
        log("%s: %d bars %s .. %s, %.0f s, folder %.1f MB" % (coin, len(df), rec["klines"][coin]["first"],
                                                             rec["klines"][coin]["last"], time.time() - t1, total_mb()))
        if total_mb() > MAX_MB:
            rec["stopped"] = "folder past %d MB" % MAX_MB
            log("STOP: folder past %d MB" % MAX_MB)
            break
    if "stopped" not in rec:
        for coin in ALTS:
            if os.path.exists(funding_path(coin)):
                continue
            try:
                f = fetch_funding(coin)
            except Blocked as e:
                rec["funding_blocked"] = str(e)
                log("FUNDING BLOCKED: %s" % e)
                break
            write_csv(f, funding_path(coin))
            rec["funding"][coin] = {"rows": int(len(f)),
                                    "first": str(pd.to_datetime(f["ts_ms"].iloc[0], unit="ms")) if len(f) else None,
                                    "last": str(pd.to_datetime(f["ts_ms"].iloc[-1], unit="ms")) if len(f) else None}
            log("%s funding: %d rates" % (coin, len(f)))
    rec["seconds"] = round(time.time() - t0, 1)
    rec["total_mb"] = round(total_mb(), 2)
    rec["finished_utc"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    with open(os.path.join(DDIR, "download_log.json"), "w") as fh:
        json.dump(rec, fh, indent=1)
    log("done: %.1f MB in %.0f s" % (rec["total_mb"], rec["seconds"]))
    return rec


# ------------------------------------------------------------------------------------------------- data
def empty_funding():
    return pd.Series([], index=pd.DatetimeIndex([], tz="UTC"), dtype=float)


def load(coin, end):
    """-> (15m bars, funding keyed by the time it was set), both cut at `end` (inclusive; funding to the bar's close)."""
    df = data.load(coin, kline_path(coin))
    fp = funding_path(coin)
    fund = empty_funding()
    if coin in ALTS and os.path.exists(fp):
        f = pd.read_csv(fp)
        if len(f):
            fund = pd.Series(f["rate"].values.astype(float),
                             index=pd.to_datetime(f["ts_ms"], unit="ms", utc=True)).sort_index()
    e = pd.Timestamp(end, tz="UTC")
    df = df.loc[:e]
    fund = fund.loc[:e + pd.Timedelta(minutes=15)]
    assert str(df.index[-1])[:16] <= CUT, "holdout read"
    return df, fund


def frame(coin, p=REG):
    end = CUT if coin in ALTS else PRE_FILE_END
    df, fund = load(coin, end)
    fx = H.features(df, fund, p)
    t = fx["t"]
    k0 = int(t.searchsorted(t[0] + pd.Timedelta(days=p["low_days"])))     # 30 days after the first bar
    k1 = len(t) - 1                                                        # trades must end by this bar
    kdec = k1 if coin in ALTS else int(t.searchsorted(pd.Timestamp(PRE_DECIDE_END, tz="UTC"), side="right")) - 1
    return {"df": df, "fund": fund, "fx": fx, "k0": k0, "k1": k1, "kdec": kdec}


def limited(fx, kdec):
    """fx with signals after the last deciding bar switched off (test 2); readings are untouched."""
    g = dict(fx)
    keep = np.arange(len(fx["t"])) <= kdec
    for key in ("A", "B"):
        g[key] = fx[key] & keep
    return g


def coin_rows(coin, F, rule, hold, p_tag="reg"):
    fx = limited(F["fx"], F["kdec"])
    rr, skipped = H.rule_rows(coin, fx, rule, F["k0"], F["k1"], hold)
    return rr, skipped


# ------------------------------------------------------------------------------------------------- statistics
def months_between(a_ts, z_ts):
    return H.all_months(a_ts, z_ts)


def cells(rows, coins, months, first_month, rng):
    """H107's read-outs: pooled and per coin x all / h1 / h2, with the month-clustered bootstrap."""
    out = {}
    m1 = [m for m in months if m <= 202306]
    m2 = [m for m in months if m >= 202306]
    D = rng.integers(0, len(months), size=(B, len(months)))
    parts = {"all": rows, "h1": [r for r in rows if r["half"] == 1], "h2": [r for r in rows if r["half"] == 2]}
    for pname, pr in parts.items():
        groups = [("pooled", pr, months)]
        for c in coins:
            cm = [m for m in months if m >= first_month[c]]
            groups.append((c, [r for r in pr if r["coin"] == c], cm))
        for cname, cr, ms_ in groups:
            if pname == "h1":
                ms_ = [m for m in ms_ if m <= 202306]
            elif pname == "h2":
                ms_ = [m for m in ms_ if m >= 202306]
            if not ms_:
                out["%s_%s" % (cname, pname)] = {"n": 0}
                continue
            Dp = D if (pname == "all" and cname == "pooled") else rng.integers(0, len(ms_), size=(B, len(ms_)))
            out["%s_%s" % (cname, pname)] = dict(H.summary(cr), boot_r=H.boot(cr, ms_, Dp, "r"),
                                                 boot_excess=H.boot(cr, ms_, Dp, "excess"))
    del m1, m2
    return out


def by_key(rows, keyf):
    g = {}
    for r in rows:
        g.setdefault(keyf(r), []).append(r)
    return dict((k, short(v)) for k, v in sorted(g.items()))


def short(rows):
    s = H.summary(rows)
    if not s["n"]:
        return s
    return {"n": s["n"], "won_pct": s["won_pct"], "mean_r": s["mean_r"], "sum_r": s["sum_r"]}


def lookahead_test(coin, F, rows, n_random=40):
    """H107's guard (i) on these files: readings recomputed on data cut at bar k (funding at its close) must equal the
    full run, for every signal bar, up to 200 trigger bars and 40 random bars."""
    fx, df, fund, k0, kdec = F["fx"], F["df"], F["fund"], F["k0"], F["kdec"]
    rng = np.random.default_rng(SEED)
    sig = sorted(set([r_["k"] for r_ in rows] + list(np.flatnonzero(fx["trig"][k0:kdec + 1]) + k0)[:200]))
    rnd = list(rng.integers(k0, kdec + 1, n_random))
    bad = []
    for k in sig + rnd:
        k = int(k)
        g = H.features(df.iloc[:k + 1], fund.loc[:fx["t"][k] + pd.Timedelta(minutes=15)])
        for key in ("A", "B", "trig"):
            if bool(g[key][-1]) != bool(fx[key][k]):
                bad.append((k, key))
        if not np.isclose(g["atr1h"][-1], fx["atr1h"][k], rtol=1e-9, equal_nan=True):
            bad.append((k, "atr1h"))
    return {"bars_checked": len(sig) + len(rnd), "mismatches": bad[:20], "n_mismatch": len(bad)}


# ------------------------------------------------------------------------------------------------- the run
def run_rules(coins, frames, rules, hold, months, first_month, rng, with_baseline=True):
    res = {}
    for rule in rules:
        rows, skipped, checks = [], {}, {}
        for c in coins:
            F = frames[c]
            rr, sk = coin_rows(c, F, rule, hold)
            skipped[c] = sk
            diffs = [abs(H.walk_loop(F["fx"], r_["k"], hold) - r_["r"]) for r_ in rr]
            checks[c] = float(max(diffs)) if diffs else 0.0
            if with_baseline:
                base = H.baseline(F["fx"], F["k0"], F["k1"], hold, sorted(set(r_["month"] for r_ in rr)))
                for r_ in rr:
                    r_["baseline"] = base.get(r_["month"], np.nan)
                    r_["excess"] = r_["r"] - r_["baseline"]
            rows += rr
        rows.sort(key=lambda r_: (r_["time"], r_["coin"]))
        res[rule] = {"cells": cells(rows, coins, months, first_month, rng),
                     "by_year": by_key(rows, lambda r_: r_["time"][:4]),
                     "signals_skipped_while_a_trade_was_open": skipped,
                     "walk_crosscheck_max_abs_diff_r": checks, "trades": rows}
    return res


def judge(res):
    pv = dict((rule, res[rule]["cells"]["pooled_all"]["boot_r"]["p"] if res[rule]["cells"]["pooled_all"].get("boot_r")
               else 1.0) for rule in res)
    rules = list(res)
    adj = H.holm([pv[r] for r in rules]) if len(rules) == 2 else np.array([pv[r] for r in rules])
    for i, rule in enumerate(rules):
        cl = res[rule]["cells"]
        pa, h1, h2 = cl["pooled_all"], cl["pooled_h1"], cl["pooled_h2"]
        elig = [c for c in ALTS if cl["%s_all" % c]["n"] >= MIN_COIN_N]
        pos = [c for c in elig if cl["%s_all" % c]["mean_r"] > 0]
        c = {"n_all>=100": pa["n"] >= MIN_ALL, "n_h1>=30": h1["n"] >= MIN_HALF, "n_h2>=30": h2["n"] >= MIN_HALF,
             "mean_r_h1>0": h1["n"] > 0 and h1["mean_r"] > 0, "mean_r_h2>0": h2["n"] > 0 and h2["mean_r"] > 0,
             "coins_with_mean_r>0_of_coins_with_5+_trades>=7": len(pos) >= MIN_COINS_POS,
             "holm_p<0.05": bool(adj[i] < ALPHA),
             "excess_pooled>0": bool(pa.get("boot_excess") and pa["boot_excess"]["obs"] > 0)}
        enough = c["n_all>=100"] and c["n_h1>=30"] and c["n_h2>=30"]
        verdict = "PASS" if all(c.values()) else ("TOO FEW TRADES TO JUDGE (no pass)" if not enough else "FAIL")
        res[rule].update({"p_raw": float(pv[rule]), "p_holm": float(adj[i]), "checks": c, "verdict": verdict,
                          "coins_with_5plus_trades": elig, "coins_with_mean_r_above_0": pos})


def sensitivity(log=print):
    variants = [("bounce 1.5 ATR", dict(REG, bounce_atr=1.5)), ("bounce 2.5 ATR", dict(REG, bounce_atr=2.5)),
                ("drop 8%", dict(REG, drop=0.08)), ("drop 12%", dict(REG, drop=0.12)),
                ("hold 24h", dict(REG, hold=96)), ("hold 96h", dict(REG, hold=384))]
    out = {}
    for name, p in variants:
        fr = dict((c, frame(c, p)) for c in ALTS)
        for rule in ("A", "B"):
            rows = []
            for c in ALTS:
                rr, _ = coin_rows(c, fr[c], rule, p["hold"])
                rows += rr
            per = by_key(rows, lambda r_: r_["coin"])
            elig = [c for c, v in per.items() if v["n"] >= MIN_COIN_N]
            out["%s | %s" % (rule, name)] = {
                "all": short(rows), "h1": short([r for r in rows if r["half"] == 1]),
                "h2": short([r for r in rows if r["half"] == 2]),
                "coins_5plus": len(elig), "coins_5plus_mean_above_0": sum(1 for c in elig if per[c]["mean_r"] > 0)}
        log("variant %s done" % name)
    return out


def run(log=print):
    t0 = time.time()
    dl_log = os.path.join(DDIR, "download_log.json")
    dl = json.load(open(dl_log)) if os.path.exists(dl_log) else None
    files = dict((f, H.md5(os.path.join(DDIR, f))) for f in sorted(os.listdir(DDIR)) if f.endswith(".csv"))
    sizes = dict((f, os.path.getsize(os.path.join(DDIR, f))) for f in files)
    funding_ok = all(os.path.exists(funding_path(c)) for c in ALTS) and not (dl and dl.get("funding_blocked"))
    rules = ("A", "B") if funding_ok else ("A",)
    res = {"registered": REG, "cut": CUT, "mid": MID, "fee_side": H.FEE, "stop_atr1h": H.STOP_ATR,
           "bootstrap": {"draws": B, "seed": SEED}, "files_md5": files, "files_bytes": sizes,
           "total_mb": round(sum(sizes.values()) / 1e6, 2), "download": dl, "rule_B_tested": funding_ok}
    frames, gates, info = {}, {}, {}
    for c in ALTS + OLD:
        F = frame(c)
        frames[c] = F
        gg = data.gates(F["df"])
        gates[c] = dict((k, gg[k]) for k in ("rows", "first", "last", "missing_bars", "gap_events", "largest_gap_hours",
                                             "ohlc_violations", "duplicates", "pass"))
        t = F["fx"]["t"]
        nf = len(F["fund"])
        info[c] = {"first_bar": str(t[0])[:16], "first_deciding_bar": str(t[F["k0"]])[:16],
                   "last_deciding_bar": str(t[F["kdec"]])[:16], "last_bar": str(t[F["k1"]])[:16],
                   "funding_from": str(F["fund"].index[0])[:16] if nf else None, "funding_rates": nf}
        log("%s: %s" % (c, info[c]))
    res["data_gates"], res["coins"] = gates, info

    # ---- test 1: the ten alts pooled (the decision)
    rng = np.random.default_rng(SEED)
    fm = dict((c, H.month_of(frames[c]["fx"]["t"][frames[c]["k0"]])) for c in ALTS)
    start1 = min(frames[c]["fx"]["t"][frames[c]["k0"]] for c in ALTS)
    months1 = H.all_months(start1.tz_localize(None), CUT)
    t1 = run_rules(ALTS, frames, rules, REG["hold"], months1, fm, rng)
    judge(t1)
    for rule in t1:
        t1[rule]["by_coin"] = dict((c, short([r for r in t1[rule]["trades"] if r["coin"] == c])) for c in ALTS)
    res["test1"] = {"months": [months1[0], months1[-1]], "rules": t1}
    if not funding_ok:
        res["test1"]["rule_B"] = "not tested: funding could not be fetched"
    log("test 1 done")

    # ---- test 2: BTC and ETH before Oct 2019 (descriptive)
    fm2 = dict((c, H.month_of(frames[c]["fx"]["t"][frames[c]["k0"]])) for c in OLD)
    start2 = min(frames[c]["fx"]["t"][frames[c]["k0"]] for c in OLD)
    months2 = H.all_months(start2.tz_localize(None), PRE_DECIDE_END)
    t2 = run_rules(OLD, frames, ("A", "B"), REG["hold"], months2, fm2, rng)
    for rule in t2:
        t2[rule]["by_coin"] = dict((c, short([r for r in t2[rule]["trades"] if r["coin"] == c])) for c in OLD)
    res["test2"] = {"months": [months2[0], months2[-1]], "rules": t2,
                    "note": "descriptive only; about two years on two coins is too short to decide; rule B cannot fire "
                            "(no funding before 2019-09/11)"}
    log("test 2 done")

    # ---- look-ahead guards
    res["lookahead_test"] = {}
    for c in ALTS + OLD:
        tr = (t1 if c in ALTS else t2)["A"]["trades"]
        res["lookahead_test"][c] = lookahead_test(c, frames[c], [r for r in tr if r["coin"] == c])
        log("guard %s %s" % (c, res["lookahead_test"][c]["n_mismatch"]))
    res["walk_crosscheck_max_abs_diff_r"] = max(
        [v for tt in (t1, t2) for rule in tt for v in tt[rule]["walk_crosscheck_max_abs_diff_r"].values()] + [0.0])

    # ---- all 12 coins x all years (descriptive): H107's trades as written in its results.json + tests 1 and 2
    h107 = json.load(open(H107_RESULTS))
    res["h107_results_md5"] = H.md5(H107_RESULTS)
    allc = {}
    for rule in ("A", "B"):
        rows = [dict(r, src="H107") for r in h107["rules"][rule]["trades"]]
        rows += [dict(r, src="test2") for r in t2[rule]["trades"]]
        if rule in t1:
            rows += [dict(r, src="test1") for r in t1[rule]["trades"]]
        allc[rule] = {"all": short(rows), "by_year": by_key(rows, lambda r_: r_["time"][:4]),
                      "by_coin": by_key(rows, lambda r_: r_["coin"]),
                      "by_source": by_key(rows, lambda r_: r_["src"])}
    res["all_12_coins_all_years"] = allc

    # ---- one setting at a time on test 1 (descriptive)
    res["descriptive_sensitivity_test1"] = sensitivity(log)
    res["seconds"] = round(time.time() - t0, 1)
    return res


# ------------------------------------------------------------------------------------------------- report
def f3(x):
    return "%+.3f" % x


def cell_line(v):
    if not v or not v.get("n"):
        return "0 trades"
    b = v.get("boot_r")
    iv = " [%s, %s], p %.3f" % (f3(b["lo"]), f3(b["hi"]), b["p"]) if b else ""
    return "%d, %.0f%% won, mean %s%s, sum %+.1fR" % (v["n"], v["won_pct"], f3(v["mean_r"]), iv, v["sum_r"])


def report(res):
    L = ["# H118: H107's rebound rules on ten more coins and BTC/ETH before Oct 2019", "",
         "Registered in research/HYPOTHESES.md (H118) before any number. Fee 0.10%% a side on every coin (generous to "
         "alts). Data to the bar opening %s UTC; the holdout was not downloaded. Run %.0f s." % (CUT, res["seconds"]), ""]
    L.append("## Test 1 (the decision): ten alts pooled")
    for rule, r in res["test1"]["rules"].items():
        L += ["", "### Rule %s: **%s**" % (rule, r["verdict"]), "",
              "- p %.4f, Holm %.4f; checks: %s" % (r["p_raw"], r["p_holm"],
                                                    ", ".join("%s %s" % (k, "ok" if v else "FAILED") for k, v in r["checks"].items())),
              "- coins with 5+ trades: %d; with mean R > 0: %d (%s)" % (len(r["coins_with_5plus_trades"]),
                                                                     len(r["coins_with_mean_r_above_0"]),
                                                                     ", ".join(r["coins_with_mean_r_above_0"])),
              "- pooled: " + cell_line(r["cells"]["pooled_all"]),
              "- first half: " + cell_line(r["cells"]["pooled_h1"]),
              "- second half: " + cell_line(r["cells"]["pooled_h2"])]
        ex = r["cells"]["pooled_all"].get("boot_excess")
        if ex:
            L.append("- excess over the drift baseline: %s [%s, %s]" % (f3(ex["obs"]), f3(ex["lo"]), f3(ex["hi"])))
        pa = r["cells"]["pooled_all"]
        if pa.get("n"):
            L.append("- exits %s; longest losing run %d; deepest fall of cumulative R %.1fR; median %s" % (
                pa["exits"], pa["longest_losing_run"], pa["worst_fall_cum_r"], f3(pa["median_r"])))
        L += ["", "| coin | trades | won | mean R [95%] | sum R | h1 mean (n) | h2 mean (n) | skipped |", "|---|---|---|---|---|---|---|---|"]
        for c in ALTS:
            a, h1, h2 = (r["cells"]["%s_%s" % (c, x)] for x in ("all", "h1", "h2"))
            if not a.get("n"):
                L.append("| %s | 0 | | | | | | %d |" % (c, r["signals_skipped_while_a_trade_was_open"][c]))
                continue
            b = a["boot_r"]
            L.append("| %s | %d | %.0f%% | %s [%s, %s] | %+.1f | %s | %s | %d |" % (
                c, a["n"], a["won_pct"], f3(a["mean_r"]), f3(b["lo"]), f3(b["hi"]), a["sum_r"],
                ("%s (%d)" % (f3(h1["mean_r"]), h1["n"])) if h1.get("n") else "-",
                ("%s (%d)" % (f3(h2["mean_r"]), h2["n"])) if h2.get("n") else "-",
                r["signals_skipped_while_a_trade_was_open"][c]))
        L += ["", "By year: " + "; ".join("%s %d tr %s (sum %+.1f)" % (y, v["n"], f3(v["mean_r"]), v["sum_r"])
                                          for y, v in r["by_year"].items())]
    L += ["", "## Test 2 (descriptive): BTC and ETH before Oct 2019", "", res["test2"]["note"], ""]
    for rule, r in res["test2"]["rules"].items():
        L.append("- Rule %s pooled: %s" % (rule, cell_line(r["cells"]["pooled_all"])))
        for c in OLD:
            L.append("  - %s: %s" % (c, cell_line(r["cells"]["%s_all" % c])))
    L += ["", "## All 12 coins x all years (descriptive; H107's trades from its results.json + tests 1 and 2)", ""]
    for rule, v in res["all_12_coins_all_years"].items():
        a = v["all"]
        L.append("- Rule %s: %d trades, %.0f%% won, mean %s, sum %+.1fR" % (rule, a["n"], a["won_pct"], f3(a["mean_r"]), a["sum_r"]))
        L.append("  - by year: " + "; ".join("%s %d %s" % (y, w["n"], f3(w["mean_r"])) for y, w in v["by_year"].items()))
        L.append("  - by coin: " + "; ".join("%s %d %s" % (c, w["n"], f3(w["mean_r"])) for c, w in v["by_coin"].items()))
    L += ["", "## One setting at a time on test 1 (descriptive, decides nothing)", "",
          "| variant | trades | mean R | h1 mean (n) | h2 mean (n) | coins 5+ / mean > 0 |", "|---|---|---|---|---|---|"]
    for k, v in res["descriptive_sensitivity_test1"].items():
        a, h1, h2 = v["all"], v["h1"], v["h2"]
        L.append("| %s | %d | %s | %s | %s | %d / %d |" % (
            k.replace(" | ", ", "), a["n"], f3(a["mean_r"]) if a["n"] else "-", ("%s (%d)" % (f3(h1["mean_r"]), h1["n"])) if h1["n"] else "-",
            ("%s (%d)" % (f3(h2["mean_r"]), h2["n"])) if h2["n"] else "-", v["coins_5plus"], v["coins_5plus_mean_above_0"]))
    lt = res["lookahead_test"]
    L += ["", "## Look-ahead guards", "",
          "- (i) bars recomputed on data cut at the bar: %d, mismatches %d" % (
              sum(v["bars_checked"] for v in lt.values()), sum(v["n_mismatch"] for v in lt.values())),
          "- (ii) vectorised walk against the bar-by-bar walk, largest difference over every trade: %.2e R" %
          res["walk_crosscheck_max_abs_diff_r"], "",
          "## Data", "", "Total %.1f MB in data/sources/h118/. Gates per file:" % res["total_mb"], ""]
    for c, g in res["data_gates"].items():
        L.append("- %s: %d rows %s .. %s, missing bars %d in %d gaps (largest %.1f h), OHLC violations %d; funding from %s" % (
            c, g["rows"], g["first"][:16], g["last"][:16], g["missing_bars"], g["gap_events"], g["largest_gap_hours"],
            g["ohlc_violations"], res["coins"][c]["funding_from"]))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args(argv)
    if a.download:
        download()
        return
    os.makedirs(OUT, exist_ok=True)
    res = run()
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(res))
    for rule, r in res["test1"]["rules"].items():
        print(rule, r["verdict"], "p", round(r["p_raw"], 4), "holm", round(r["p_holm"], 4), r["checks"])


if __name__ == "__main__":
    main()
