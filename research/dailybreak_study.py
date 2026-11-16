# -*- coding: utf-8 -*-
"""H45 daily range breaks traded with a DAILY-sized trade. PAPER RESEARCH ONLY.

Registered before any code or number: research/HYPOTHESES.md H45 (16 Nov 2026, 04:58 UTC). In short:
  * eight markets, rows before the sealed holdout 2025-11-11 00:00 UTC only (later rows dropped right after loading);
  * trades from 2020-01-01 by entry time; first half before 2023-06-07, second half from it to the seal (H44's split);
  * levels: the prior UTC day's high/low (pday) or the previous 96 bars' high/low (roll24), from
    engine15/sources/adr.py `readings` (daily ATR of the last closed day through data.htf_on_15, held for the day);
  * the event: the FIRST 15m close beyond the level in the UTC day per direction, with momentum (true range >= 1.5 x
    ATR15 of the bar before) or without (D3);
  * the trade: next open (same UTC day only), stop 0.5 x daily ATR from entry (S1) or the level -/+ 0.25 x daily ATR
    (S2), target the remaining daily room (Troom, floor 0.25 daily ATR) or 1 daily ATR (T1), out at the next UTC day's
    first open or after 72 h; stop first in a bar, gaps fill at the open, one position per market, own fee a side;
  * selection on the first half among D1-D4; pass bar (H44's) on the second half against the no-eagle twin.

A minimal simulator is used (single stop, single target, per-trade exit bar) because playbook.simulate always takes
half at T1 with a break-even stop and has one hold length for every signal.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB
free before each market.

    py -3 research/dailybreak_study.py            (run, write study.json + study.md, then print the live scan)
    py -3 research/dailybreak_study.py --report   (rewrite study.md from study.json)
    py -3 research/dailybreak_study.py --scan     (the live scan only: latest closed bars, paper)
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

from engine15 import data, playbook as pb  # noqa: E402
from engine15.sources import adr  # noqa: E402
from engine15.rl import resources  # noqa: E402

from liqhunt2_study import acquire_lock, release_lock, log, ms_of  # noqa: E402  (same lock, same log format)
import rangebreak_study as rb  # noqa: E402  (metrics, loader, report helpers: one definition)

START, SPLIT, SEAL = rb.START, rb.SPLIT, rb.SEAL
REGISTERED_UTC = "2026-11-16 04:58 UTC"
ASSETS = rb.ASSETS
GROUPS = {"crypto": ("BTCUSDT", "ETHUSDT"), "metals": ("XAUUSD", "XAGUSD"), "fx": ("USDJPY",), "index": ("SPX",),
          "energy": ("WTI", "BRENT")}
GROUP_OF = dict((a, g) for g, aa in GROUPS.items() for a in aa)
OUT = os.path.join(ROOT, "research", "out", "dailybreak")
NEED_MB = 1500
BAR_MS, DAY_MS = pb.BAR_MS, 86400000
BOX = 96                      # roll24: the previous 96 bars
MOM_K = 1.5
STOP_S1, STOP_S2_PAD, TARGET_T1, ROOM_FLOOR = 0.5, 0.25, 1.0, 0.25
HOLD_3D_MS = 3 * DAY_MS
MIN_TRADES_ASSET, MIN_TRADES_ALL, MIN_TRADES_PASS = 20, 100, 100
PASS_MARKETS, PASS_PF = 5, 1.1
BUCKETS = ("room left", "middle", "exhausted")

VARIANTS = {
    "D1": {"level": "pday", "mom": True, "stop": "S1", "target": "Troom", "exit": "dayend", "filter": "room", "select": True},
    "D2": {"level": "roll24", "mom": True, "stop": "S1", "target": "Troom", "exit": "dayend", "filter": "room", "select": True},
    "D3": {"level": "pday", "mom": False, "stop": "S1", "target": "Troom", "exit": "dayend", "filter": "room", "select": True},
    "D4": {"level": "pday", "mom": True, "stop": "S2", "target": "T1", "exit": "3d", "filter": "room", "select": True},
}
TWINS = dict(("%sn" % v, dict(VARIANTS[v], filter="none", select=False)) for v in VARIANTS)
TWIN_OF = dict((v, "%sn" % v) for v in VARIANTS)
ALL = dict(VARIANTS, **TWINS)
ORDER = list(VARIANTS) + list(TWINS)
EVENT_SETS = [("pday, every first close", "pday", False), ("pday, with momentum", "pday", True),
              ("roll24, every first close", "roll24", False), ("roll24, with momentum", "roll24", True)]
PRIOR_FAMILY = {"selectable": 6, "contrast": 1, "controls": 6}      # H44


def vdesc(v):
    lv = {"pday": "prior UTC day", "roll24": "rolling 96 bars"}[v["level"]]
    mo = "momentum (TR >= 1.5 ATR15)" if v["mom"] else "every first close"
    st = {"S1": "stop 0.5 dATR from entry", "S2": "stop level -/+ 0.25 dATR"}[v["stop"]]
    tg = {"Troom": "target remaining daily room", "T1": "target 1 dATR"}[v["target"]]
    ex = {"dayend": "out at next UTC day's first open", "3d": "out after 72 h"}[v["exit"]]
    fl = {"room": "room-left (used < 0.65)", "none": "no daily filter"}[v["filter"]]
    return "%s, %s, %s, %s, %s, %s" % (lv, mo, st, tg, ex, fl)


# ---------------------------------------------------------------- the event and the signals (truncation-tested)
def daily_breaks(R, level, momentum, k=MOM_K):
    """-> int array: +1 / -1 on the bar that is the FIRST close above / below the level in its UTC day (and, if
    momentum, only when that first close is on a bar with true range >= k x ATR15 of the bar before), else 0."""
    c = R["c"]
    day = R["ms"] // DAY_MS
    hi, lo = (R["pdh"], R["pdl"]) if level == "pday" else (R["box_hi"], R["box_lo"])
    with np.errstate(invalid="ignore"):
        up = np.nan_to_num(c > hi).astype(bool) & np.isfinite(hi)
        dn = np.nan_to_num(c < lo).astype(bool) & np.isfinite(lo)
    cu = pd.Series(up.astype(int)).groupby(day).cumsum().values
    cd = pd.Series(dn.astype(int)).groupby(day).cumsum().values
    fu, fd = up & (cu == 1), dn & (cd == 1)
    if momentum:
        with np.errstate(invalid="ignore"):
            mom = np.nan_to_num(R["bar_x"] >= k).astype(bool)
        fu, fd = fu & mom, fd & mom
    return np.where(fu, 1, np.where(fd, -1, 0)).astype(int)


def signals(R, var):
    """R: adr.readings(bars, box=96) -> list of signal dicts, oldest first; everything known at the close of i_dec."""
    dirs = daily_breaks(R, var["level"], var["mom"])
    used, datr = R["used"], R["datr"]
    with np.errstate(invalid="ignore"):
        ok = (dirs != 0) & np.isfinite(datr) & (datr > 0)
        if var["filter"] == "room":
            ok &= np.nan_to_num(used < adr.ROOM_LEFT).astype(bool) & np.isfinite(used)
    hi, lo = (R["pdh"], R["pdl"]) if var["level"] == "pday" else (R["box_hi"], R["box_lo"])
    sigs = []
    for i in np.flatnonzero(ok):
        s = int(dirs[i])
        D = float(datr[i])
        room_px = (R["day_low"][i] + D) if s > 0 else (R["day_high"][i] - D)
        sigs.append({"i_dec": int(i), "side": s, "level": float(hi[i] if s > 0 else lo[i]), "datr": D,
                     "used": float(used[i]) if used[i] == used[i] else None, "room_px": float(room_px),
                     "close": float(R["c"][i]), "bar_x": float(R["bar_x"][i])})
    return sigs


def plan(sig, entry, var):
    """-> (stop, target) for a fill at `entry`."""
    s, D = sig["side"], sig["datr"]
    stop = entry - s * STOP_S1 * D if var["stop"] == "S1" else sig["level"] - s * STOP_S2_PAD * D
    if var["target"] == "T1":
        tgt = entry + s * TARGET_T1 * D
    else:
        tgt = sig["room_px"]
        if s * (tgt - entry) < ROOM_FLOOR * D:
            tgt = entry + s * ROOM_FLOOR * D
    return stop, tgt


def exit_bar(ms, day, r, e, var):
    """Index of the bar at whose OPEN the time exit fills (may be == n: not on file yet)."""
    if var["exit"] == "dayend":
        return int(np.searchsorted(day, day[r], side="right"))
    return int(np.searchsorted(ms, ms[e] + HOLD_3D_MS, side="left"))


def simulate(R, sigs, var, fee):
    """One position at a time. -> list of trade dicts (status WAITING / OPEN / CLOSED). Stop first inside a bar; an open
    beyond the stop or the target fills at that open; a fill that gaps beyond the stop is not taken."""
    n, o, h, l, c, ms = R["n"], R["o"], R["h"], R["l"], R["c"], R["ms"]
    day = ms // DAY_MS
    trades, busy = [], -1
    for sig in sigs:
        r = sig["i_dec"]
        if r <= busy:
            continue
        s = sig["side"]
        e = r + 1
        if e >= n:
            est = float(c[r])
            st, tg = plan(sig, est, var)
            trades.append(dict(sig, status="WAITING", entry=None, est_entry=est, stop=st, target=tg))
            busy = n
            continue
        if day[e] != day[r]:                                              # nothing left of the break's day
            continue
        entry = float(o[e])
        stop, tgt = plan(sig, entry, var)
        if s * (entry - stop) <= 0:
            continue
        risk = abs(entry - stop)
        x = exit_bar(ms, day, r, e, var)
        px, j_out, why = None, None, None
        for j in range(e, min(x, n)):
            adverse = l[j] if s > 0 else h[j]
            fav = h[j] if s > 0 else l[j]
            if s * (o[j] - stop) <= 0:
                px, j_out, why = float(o[j]), j, "STOP"
                break
            if s * (adverse - stop) <= 0:
                px, j_out, why = stop, j, "STOP"
                break
            if s * (o[j] - tgt) >= 0:
                px, j_out, why = float(o[j]), j, "TARGET"
                break
            if s * (fav - tgt) >= 0:
                px, j_out, why = tgt, j, "TARGET"
                break
        t = dict(sig, entry_ms=int(ms[e]), entry=entry, stop=float(stop), target=float(tgt), risk=risk)
        if why is None and x < n:
            px, j_out, why = float(o[x]), x, "TIME"
        if why is None:
            t.update(status="OPEN", mark=float(c[-1]), why_out="OPEN", exit_ms=None, **_money(float(c[-1]), entry, risk, s, fee))
            busy = n
        else:
            t.update(status="CLOSED", exit=px, exit_ms=int(ms[j_out]), why_out=why, exit_bar=int(j_out),
                     **_money(px, entry, risk, s, fee))
            busy = j_out - 1
        trades.append(t)
    return trades


def _money(px, entry, risk, side, fee):
    gross = side * (px - entry) / entry * pb.STAKE
    fees = fee * pb.STAKE + fee * pb.STAKE * px / entry
    net = gross - fees
    return {"gross_usd": gross, "fees_usd": fees, "pnl_usd": net, "pnl_pct": net / pb.STAKE * 100.0,
            "r": net / (pb.STAKE * risk / entry)}


def slim(t, asset):
    gross_r = t["gross_usd"] / (pb.STAKE * t["risk"] / t["entry"])
    return {"asset": asset, "side": int(t["side"]), "entry_ms": int(t["entry_ms"]), "exit_ms": int(t["exit_ms"]),
            "pnl_usd": float(t["pnl_usd"]), "gross_usd": float(t["gross_usd"]), "fees_usd": float(t["fees_usd"]),
            "r": float(t["r"]), "gross_r": float(gross_r), "risk": float(t["risk"]), "entry": float(t["entry"]),
            "t1_hit": t["why_out"] == "TARGET", "why_out": t["why_out"]}


def metrics(tr):
    m = rb.metrics(tr)
    if tr:
        for w in ("STOP", "TARGET", "TIME"):
            m["out_%s_pct" % w.lower()] = round(100.0 * float(np.mean([t["why_out"] == w for t in tr])), 1)
    return m


# ---------------------------------------------------------------- descriptive statistics (pre-cost, events)
SUM_KEYS = ("n", "fday", "f1d", "f3d", "posday", "pos3d", "h05day", "h05", "h10", "nei05", "nei10")


def event_stats(R, dirs, start_ms):
    """-> {"half|bucket": sums} for every event in dirs (no filter): forward moves in daily-ATR units."""
    n, o, h, l, c, ms, D, used = R["n"], R["o"], R["h"], R["l"], R["c"], R["ms"], R["datr"], R["used"]
    day = ms // DAY_MS
    split_ms = ms_of(SPLIT)
    out = {}
    for i in np.flatnonzero(dirs != 0):
        e = i + 1
        if e >= n or day[e] != day[i] or not (D[i] == D[i] and D[i] > 0) or ms[e] < start_ms:
            continue
        x3 = int(np.searchsorted(ms, ms[e] + HOLD_3D_MS, side="left"))
        if x3 >= n:
            continue
        xd = int(np.searchsorted(day, day[i], side="right"))
        x1 = int(np.searchsorted(ms, ms[e] + DAY_MS, side="left"))
        s, d, en = int(dirs[i]), float(D[i]), float(o[e])
        fday = s * (c[xd - 1] - en) / d
        f1d = s * (c[x1 - 1] - en) / d
        f3d = s * (c[x3 - 1] - en) / d
        H, L = h[e:x3], l[e:x3]
        fav = (H - en) / d if s > 0 else (en - L) / d
        adv = (en - L) / d if s > 0 else (H - en) / d
        big = len(H) + 1
        a5 = int(np.argmax(adv >= 0.5)) if (adv >= 0.5).any() else big
        f5 = int(np.argmax(fav >= 0.5)) if (fav >= 0.5).any() else big
        f10 = int(np.argmax(fav >= 1.0)) if (fav >= 1.0).any() else big
        nd = xd - e
        u = used[i]
        b = "no read" if u != u else ("room left" if u < adr.ROOM_LEFT else ("exhausted" if u >= adr.EXHAUSTED else "middle"))
        hf = "first" if ms[e] < split_ms else "second"
        row = {"n": 1, "fday": fday, "f1d": f1d, "f3d": f3d, "posday": int(fday > 0), "pos3d": int(f3d > 0),
               "h05day": int(f5 < a5 and f5 < nd), "h05": int(f5 < a5), "h10": int(f10 < a5),
               "nei05": int(f5 == big and a5 == big), "nei10": int(f10 == big and a5 == big)}
        for k in ("%s|%s" % (hf, b), "%s|all" % hf, "all|%s" % b, "all|all"):
            acc = out.setdefault(k, dict((kk, 0) for kk in SUM_KEYS))
            for kk in SUM_KEYS:
                acc[kk] += row[kk]
    return out


def finish(s):
    n = s.get("n", 0)
    if not n:
        return {"n": 0}
    return {"n": n, "fday": round(s["fday"] / n, 3), "f1d": round(s["f1d"] / n, 3), "f3d": round(s["f3d"] / n, 3),
            "posday": round(100.0 * s["posday"] / n, 1), "pos3d": round(100.0 * s["pos3d"] / n, 1),
            "h05day": round(100.0 * s["h05day"] / n, 1), "h05": round(100.0 * s["h05"] / n, 1),
            "h10": round(100.0 * s["h10"] / n, 1), "nei05": round(100.0 * s["nei05"] / n, 1),
            "nei10": round(100.0 * s["nei10"] / n, 1)}


# ---------------------------------------------------------------- per market
def _r9(x):
    return None if x is None or x != x else round(x, 9)


def sig_key(sigs):
    return [(s["i_dec"], s["side"], _r9(s["level"]), _r9(s["datr"]), _r9(s["room_px"]), _r9(s["used"])) for s in sigs]


def truncation_check(df, cuts):
    full_R = adr.readings(df, box=BOX)
    full = dict((v, sig_key(signals(full_R, ALL[v]))) for v in ORDER)
    bad, checked = 0, 0
    for cut in cuts:
        part_R = adr.readings(df.iloc[:cut], box=BOX)
        for v in ORDER:
            want = [x for x in full[v] if x[0] < cut]
            checked += len(want)
            if sig_key(signals(part_R, ALL[v])) != want:
                bad += 1
    return {"cuts": len(cuts), "signals_checked": checked, "mismatched_runs": bad}


def run_asset(asset):
    df = rb.load_dev(asset)
    fee = pb.fee_side(asset)
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    R = adr.readings(df, box=BOX)
    res = {"asset": asset, "group": GROUP_OF[asset], "fee_side": fee, "bars": int(len(df)), "first_bar": str(df.index[0]),
           "last_bar": str(df.index[-1]), "variants": {}, "trades": {}}
    for v in ORDER:
        raw = [t for t in simulate(R, signals(R, ALL[v]), ALL[v], fee) if t["status"] == "CLOSED" and t["entry_ms"] >= start_ms]
        tr = [slim(t, asset) for t in raw]
        h1 = [t for t in tr if t["entry_ms"] < split_ms]
        h2 = [t for t in tr if t["entry_ms"] >= split_ms]
        res["variants"][v] = {"first": metrics(h1), "second": metrics(h2),
                              "median_risk_datr": round(float(np.median([t["risk"] / t["datr"] for t in raw])), 3) if raw else None}
        res["trades"][v] = tr
    res["events"] = dict((label, event_stats(R, daily_breaks(R, lv, mo), start_ms)) for label, lv, mo in EVENT_SETS)
    n = len(df)
    res["truncation"] = truncation_check(df, [int(n * 0.6) + 7, n - 40])
    return res


# ---------------------------------------------------------------- pooling, selection, pass bar
def pooled(results, v, half):
    split_ms = ms_of(SPLIT)
    tr = []
    for r in results.values():
        tr += [t for t in r["trades"][v] if (t["entry_ms"] < split_ms) == (half == "first")]
    return metrics(tr)


def score(results, v):
    vals = [r["variants"][v]["first"]["exp_pct"] for r in results.values()
            if r["variants"][v]["first"]["trades"] >= MIN_TRADES_ASSET]
    return float(np.mean(vals)) if vals else None


def judge(results):
    J = {"scores": {}, "pooled": {}}
    for v in ORDER:
        J["pooled"][v] = {"first": pooled(results, v, "first"), "second": pooled(results, v, "second")}
    cands = []
    for v in VARIANTS:
        sc = score(results, v)
        J["scores"][v] = sc
        if sc is not None and J["pooled"][v]["first"]["trades"] >= MIN_TRADES_ALL:
            cands.append((-sc, int(v[1:]), v))
    chosen = sorted(cands)[0][2] if cands else None
    J["chosen"] = chosen
    if chosen:
        twin = TWIN_OF[chosen]
        p2, t2 = J["pooled"][chosen]["second"], J["pooled"][twin]["second"]
        pos_markets = [a for a, r in results.items() if r["variants"][chosen]["second"]["net_usd"] > 0]
        bar = {"pooled_net_positive": bool(p2["trades"] >= MIN_TRADES_PASS and p2["net_usd"] > 0),
               "markets_positive": len(pos_markets), "markets_positive_list": pos_markets,
               "markets_ok": len(pos_markets) >= PASS_MARKETS,
               "pf_ok": bool(p2.get("pf") is not None and p2["pf"] >= PASS_PF),
               "beats_twin": bool(p2["trades"] and t2["trades"] and p2["exp_pct"] > t2["exp_pct"]),
               "twin": twin}
        bar["pass"] = bool(bar["pooled_net_positive"] and bar["markets_ok"] and bar["pf_ok"] and bar["beats_twin"])
        J["bar"] = bar
    return J


def _merge(parts):
    tot = {}
    for p in parts:
        for k, v in p.items():
            tot[k] = tot.get(k, 0) + v
    return tot


def events_table(results):
    """-> {label: {"half|bucket": finished, "group:<g>|<half>": finished}}"""
    T = {}
    for label, _lv, _mo in EVENT_SETS:
        T[label] = {}
        for hf in ("first", "second", "all"):
            for b in BUCKETS + ("all",):
                key = "%s|%s" % (hf, b)
                T[label][key] = finish(_merge([r["events"][label].get(key, {}) for r in results.values()]))
            for g, aa in GROUPS.items():
                T[label]["group:%s|%s" % (g, hf)] = finish(_merge([r["events"][label].get("%s|all" % hf, {})
                                                                   for a, r in results.items() if a in aa]))
            for g, aa in GROUPS.items():
                for b in BUCKETS:
                    T[label]["group:%s|%s|%s" % (g, hf, b)] = finish(_merge([r["events"][label].get("%s|%s" % (hf, b), {})
                                                                            for a, r in results.items() if a in aa]))
    return T


# ---------------------------------------------------------------- report
HDR = "| trades | won | R before costs | R after costs | PF | per trade (% stake) | net $ | stop / target / time |"


def fmt(m):
    if not m or not m.get("trades"):
        return "| 0 | | | | | | | |"
    return "| %d | %.1f%% | %+.3f | %+.3f | %s | %+.4f%% | %s | %.0f / %.0f / %.0f%% |" % (
        m["trades"], m["win_pct"], m["avg_r_gross"], m["avg_r"], "n/a" if m["pf"] is None else "%.2f" % m["pf"],
        m["exp_pct"], "{:+,.0f}".format(m["net_usd"]), m["out_stop_pct"], m["out_target_pct"], m["out_time_pct"])


EV_HDR = ("| n | to day close (dATR) | to 24 h | to 72 h | up at day close | up at 72 h | +0.5 before -0.5 by day end | "
          "+0.5 before -0.5 (72 h) | +1.0 before -0.5 (72 h) | neither (+0.5, 72 h) |")


def ev_cells(m):
    return "%d | %+.3f | %+.3f | %+.3f | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%%" % (
        m["n"], m["fday"], m["f1d"], m["f3d"], m["posday"], m["pos3d"], m["h05day"], m["h05"], m["h10"], m["nei05"])


def report(S):
    J, res, T = S["judge"], S["results"], S["events"]
    L = ["# H45: daily range breaks traded with a daily-sized trade", "",
         "PAPER RESEARCH ONLY. Registered %s (`research/HYPOTHESES.md` H45) before any number. Development data only "
         "(rows before %s 00:00 UTC; the holdout was not read). Trades from %s; first half before %s. Written %s." % (
             REGISTERED_UTC, SEAL, START, SPLIT, S["written"]), "",
         "Levels and the daily ATR from `engine15/sources/adr.py` `readings` (box 96; daily ATR of the last closed UTC day "
         "through `data.htf_on_15`, held for the day). Event = the first 15m close beyond the level in its UTC day per "
         "direction. Trades through the study's minimal simulator: next open (same UTC day only), single stop and target, "
         "stop first inside a bar, gaps fill at the open, one position per market, $10,000 a trade, each market's own fee "
         "a side. 'dATR' = daily ATR(14).", ""]
    if J.get("chosen"):
        b = J["bar"]
        L += ["## Verdict: %s" % ("PASS" if b["pass"] else "NO PASS"), "",
              "Chosen on the first half: **%s** (%s), score %+.4f%% a trade." % (J["chosen"], vdesc(VARIANTS[J["chosen"]]),
                                                                              J["scores"][J["chosen"]]), "",
              "Pass bar (second half): pooled net > 0 with >= %d trades: **%s**; net > 0 in >= %d of 8 markets: **%s** (%d: %s); "
              "PF >= %.1f: **%s**; per trade better than its no-eagle twin (%s): **%s**." % (
                  MIN_TRADES_PASS, "YES" if b["pooled_net_positive"] else "NO", PASS_MARKETS, "YES" if b["markets_ok"] else "NO",
                  b["markets_positive"], ", ".join(b["markets_positive_list"]) or "none", PASS_PF, "YES" if b["pf_ok"] else "NO",
                  b["twin"], "YES" if b["beats_twin"] else "NO"), "",
              "Variant count in the H44/H45 range-break family: H44 %d selectable + %d contrast + %d controls; H45 %d "
              "selectable + %d controls." % (PRIOR_FAMILY["selectable"], PRIOR_FAMILY["contrast"], PRIOR_FAMILY["controls"],
                                             len(VARIANTS), len(TWINS)), ""]
    L += ["## Variants, pooled over the eight markets", "",
          "Score = mean over markets (>= %d first-half trades) of the first-half expectancy after costs." % MIN_TRADES_ASSET, "",
          "| id | rule | score | half " + HDR, "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in ORDER:
        sc = J["scores"].get(v)
        for hf in ("first", "second"):
            L.append("| %s | %s | %s | %s |%s" % (v if hf == "first" else "", vdesc(ALL[v]) if hf == "first" else "",
                                                ("%+.4f%%" % sc) if (sc is not None and hf == "first") else "", hf,
                                                fmt(J["pooled"][v][hf])[1:]))
    if J.get("chosen"):
        ch, tw = J["chosen"], J["bar"]["twin"]
        L += ["", "## Chosen variant %s vs its no-eagle twin %s, per market" % (ch, tw), ""]
        L += ["| market | half | %s net $ | %s per trade | %s R gross | %s trades | %s net $ | %s per trade | %s R gross | %s trades |" % (
            ch, ch, ch, ch, tw, tw, tw, tw), "|---|---|---|---|---|---|---|---|---|---|"]
        for a, r in res.items():
            for hf in ("first", "second"):
                cells = []
                for v in (ch, tw):
                    m = r["variants"][v][hf]
                    cells += ["{:+,.0f}".format(m["net_usd"]), ("%+.4f%%" % m["exp_pct"]) if m["trades"] else "",
                              ("%+.3f" % m["avg_r_gross"]) if m["trades"] else "", str(m["trades"])]
                L.append("| %s | %s | %s |" % (a if hf == "first" else "", hf, " | ".join(cells)))
    L += ["", "## Per market, every variant (second half: per trade after costs, trades)", "",
          "| market | " + " | ".join(ORDER) + " |", "|---|" + "---|" * len(ORDER)]
    for a, r in res.items():
        L.append("| %s | %s |" % (a, " | ".join(("%+.3f%% (%d)" % (r["variants"][v]["second"]["exp_pct"], r["variants"][v]["second"]["trades"]))
                                                if r["variants"][v]["second"]["trades"] else "-" for v in ORDER)))
    L += ["", "Median risk (stop distance) in daily ATRs, all trades: " + "; ".join(
        "%s %s" % (v, ", ".join("%s %s" % (a[:3], r["variants"][v]["median_risk_datr"]) for a, r in res.items())) for v in ("D4", "D4n")) + ".", ""]
    L += ["## Descriptive: what a daily break does next (pre-cost, events, no daily filter, overlaps allowed)", "",
          "Forward move in the break direction from the next open, in daily ATRs, to the close of the break's UTC day, "
          "24 h and 72 h after entry. Hit rates are shares of ALL events (same bar = loss). A driftless walk gives about "
          "50% for +0.5 before -0.5 and about 33% for +1.0 before -0.5. Buckets: share of the daily ATR used at the break "
          "bar's close (room left < 0.65, middle 0.65-1.0, exhausted >= 1.0).", ""]
    for label, _lv, _mo in EVENT_SETS:
        rows = T[label]
        L += ["### %s" % label, "", "| half | bucket " + EV_HDR, "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for hf in ("first", "second", "all"):
            for b in BUCKETS + ("all",):
                m = rows["%s|%s" % (hf, b)]
                if m.get("n"):
                    L.append("| %s | %s | %s |" % (hf, b, ev_cells(m)))
        L += ["", "| group | half " + EV_HDR, "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in GROUPS:
            for hf in ("first", "second", "all"):
                m = rows["group:%s|%s" % (g, hf)]
                if m.get("n"):
                    L.append("| %s | %s | %s |" % (g, hf, ev_cells(m)))
        L += ["", "| group | bucket (all dev) " + EV_HDR, "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in GROUPS:
            for b in BUCKETS:
                m = rows["group:%s|all|%s" % (g, b)]
                if m.get("n"):
                    L.append("| %s | %s | %s |" % (g, b, ev_cells(m)))
        L.append("")
    L += ["## Checks", ""]
    for a, r in res.items():
        tc = r["truncation"]
        L.append("- %s: %d bars (%s to %s), fee %.2f%% a side; truncation check %d cuts, %d signals compared, %d mismatched runs." % (
            a, r["bars"], r["first_bar"][:16], r["last_bar"][:16], 100 * r["fee_side"], tc["cuts"], tc["signals_checked"],
            tc["mismatched_runs"]))
    L += ["", "## Relation to H44 and H7", "",
          "- H44 V4 (prior-day cross with momentum, room-left) traded the same kind of event with a 15m-sized trade (stop 1 x "
          "ATR15, 1R/2R, 4 h) and lost in all 8 markets. H45 keeps the event (first close of the day only) and changes the trade "
          "to daily size and a day-end / 72 h horizon.",
          "- H7 (breakout trap, `playbook.py` p2) FADES failed first closes beyond the prior-day level; H45 trades WITH them.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- live scan (paper)
def scan(chosen=None, passed=False, now_ms=None):
    var = VARIANTS.get(chosen or "D1")
    label = "PAPER, %s" % ("passed H45's history bar" if passed else "UNTESTED / did NOT pass H45's history bar")
    lines = ["H45 live daily-break scan (%s), rule %s: %s" % (label, chosen or "D1", vdesc(var))]
    rows = []
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    for a in ASSETS:
        try:
            df = data.load(a)
        except Exception as ex:
            lines.append("  %-8s no bars (%s)" % (a, ex))
            continue
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=60)]
        df = df[data.to_ms(df.index) + BAR_MS <= now_ms]
        R = adr.readings(df, box=BOX)
        n = R["n"]
        i = n - 1
        day = R["ms"] // DAY_MS
        last_close = pd.Timestamp(int(R["ms"][i]) + BAR_MS, unit="ms", tz="UTC")
        age_h = (now_ms - (int(R["ms"][i]) + BAR_MS)) / 3600000.0
        hi, lo = (R["pdh"], R["pdl"]) if var["level"] == "pday" else (R["box_hi"], R["box_lo"])
        D = R["datr"][i]
        ctx = "dATR %s, used %s (%s), %s high %s / low %s, close %s" % (
            rb._p(D), rb._pc(R["used"][i]), adr.bucket(R["used"][i]), var["level"], rb._p(hi[i]), rb._p(lo[i]), rb._p(R["c"][i]))
        head = "  %-8s last close %s%s; %s" % (a, last_close.strftime("%d %b %H:%M UTC"),
                                              " (stale %.1f h: market shut)" % age_h if age_h > 1 else "", ctx)
        today = day == day[i]
        ev_all = daily_breaks(R, var["level"], False)
        ev_mom = daily_breaks(R, var["level"], True)
        found = []
        for j in np.flatnonzero(today & (ev_all != 0)):
            s = int(ev_all[j])
            u = R["used"][j]
            mom = bool(ev_mom[j] != 0)
            ok = (var["filter"] == "none" or (u == u and u < adr.ROOM_LEFT)) and (mom or not var["mom"])
            when = pd.Timestamp(int(R["ms"][j]) + BAR_MS, unit="ms", tz="UTC").strftime("%H:%M UTC")
            txt = "first close %s the %s %s at %s (bar %.1fx ATR15%s), day had used %s (%s)" % (
                "ABOVE" if s > 0 else "BELOW", var["level"], "high" if s > 0 else "low", when, R["bar_x"][j],
                "" if mom else ", NO momentum", rb._pc(u), adr.bucket(u))
            if ok:
                sig = [x for x in signals(R, var) if x["i_dec"] == j][0]
                entry = R["o"][j + 1] if j + 1 < n else R["c"][j]
                st, tg = plan(sig, float(entry), var)
                txt += "; rule fires: %s %s %s, stop %s, target %s, %s" % (
                    "LONG" if s > 0 else "SHORT", "at" if j + 1 < n else "at the next open, about", rb._p(entry),
                    rb._p(st), rb._p(tg), {"dayend": "out at the next UTC day's first open", "3d": "out after 72 h"}[var["exit"]])
            else:
                txt += "; rule does NOT fire (%s)" % ("no momentum" if (var["mom"] and not mom) else "day past 65% of its ATR")
            found.append(txt)
            rows.append({"asset": a, "side": s, "close_utc": when, "used": None if u != u else round(float(u), 3),
                         "momentum": mom, "fires": bool(ok)})
        tr = simulate(R, signals(R, var), var, pb.fee_side(a))
        open_tr = [t for t in tr if t["status"] in ("OPEN", "WAITING")]
        if open_tr:
            t = open_tr[-1]
            found.append("paper position %s: %s from %s, stop %s, target %s, marked %+.2f%%" % (
                t["status"], "LONG" if t["side"] > 0 else "SHORT", rb._p(t.get("entry") or t.get("est_entry")),
                rb._p(t["stop"]), rb._p(t["target"]), t.get("pnl_pct", 0.0)))
        lines.append(head + ("; " + "; ".join(found) if found else "; no daily break today yet") + ".")
    lines.append("  (%s)" % label)
    return rows, lines


# ---------------------------------------------------------------- main
def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    acquire_lock("H45 dailybreak study")
    results = {}
    try:
        for a in ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("not enough free memory for %s" % a)
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            t0 = time.time()
            results[a] = run_asset(a)
            log("%s: done in %.0f s; D1n first-half trades %d, truncation %s" % (
                a, time.time() - t0, results[a]["variants"]["D1n"]["first"]["trades"], results[a]["truncation"]))
    finally:
        release_lock()
    J = judge(results)
    S = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "registered": REGISTERED_UTC,
         "variants": dict((v, ALL[v]) for v in ORDER), "judge": J, "events": events_table(results),
         "results": dict((a, dict((k, v) for k, v in r.items() if k not in ("trades", "events"))) for a, r in results.items())}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, indent=1, default=str)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(S))
    log("chosen %s, pass %s" % (J.get("chosen"), J.get("bar", {}).get("pass")))
    return S


def load_study():
    with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
        return json.load(fh)


def print_scan():
    try:
        S = load_study()
        ch, ps = S["judge"].get("chosen"), bool(S["judge"].get("bar", {}).get("pass"))
    except Exception:
        ch, ps = None, False
    _rows, lines = scan(ch, ps)
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
