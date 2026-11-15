# -*- coding: utf-8 -*-
"""H41 liquidity hunt v2: history study of the eight registered variants (engine15/liqhunt2.py) and the original P1
rule, six markets, development data only. PAPER RESEARCH ONLY.

Registered before any code or number: research/HYPOTHESES.md H41 (15 Nov 2026, 05:45 UTC). In short:
  * bars before the sealed holdout 2025-11-11 00:00 UTC only (later bars and funding rows dropped right after load);
  * trades from 2020-01-01 by entry time; first half before 2023-06-07, second half from it to the seal;
  * selection on the first half only: the highest mean over markets (>= 20 first-half trades each) of the first-half
    expectancy after costs (% of stake per trade), among variants with >= 100 first-half trades in all; ties: fewer levers;
  * pass bar (chosen variant, second half): pooled net $ > 0 with >= 100 trades, AND net $ > 0 in >= 4 of 6 markets,
    AND pooled expectancy per trade above the original P1's re-run through the same code.

Resources: one market at a time, below-normal priority, research/out/heavy_job.lock held while running, >= 1,500 MB free
before each market.

    py -3 research/liqhunt2_study.py            (run, write study.json + study.md)
    py -3 research/liqhunt2_study.py --report   (rewrite study.md from study.json)
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, playbook as pb, liqhunt2 as lh  # noqa: E402
from engine15.rl import resources  # noqa: E402

START, SPLIT, SEAL = "2020-01-01", "2023-06-07", "2025-11-11"
REGISTERED_UTC = "2026-11-15 05:45 UTC"
OUT = os.path.join(ROOT, "research", "out", "liqhunt2")
LOCK = os.path.join(ROOT, "research", "out", "heavy_job.lock")
NEED_MB = 1500
MIN_TRADES_ASSET, MIN_TRADES_ALL, MIN_TRADES_PASS = 20, 100, 100
PRIOR_VARIANTS = 29
ALL = dict(lh.VARIANTS, P1=lh.CONTROL)
ORDER = list(lh.VARIANTS) + ["P1"]


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def _pid_alive(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32
        hnd = k.OpenProcess(0x1000, False, int(pid))
        if not hnd:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(hnd, ctypes.byref(code))
        k.CloseHandle(hnd)
        return bool(ok) and code.value == 259
    except Exception:
        return True


def acquire_lock(label):
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "label": label,
                                     "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}).encode())
            os.close(fd)
            log("heavy_job.lock taken")
            return
        except FileExistsError:
            try:
                with open(LOCK, encoding="utf-8") as fh:
                    held = json.load(fh)
                pid = int(held.get("pid", -1))
            except Exception:
                held, pid = {}, -1
            if pid > 0 and _pid_alive(pid):
                log("heavy_job.lock held by pid %d (%s); waiting 60 s" % (pid, held.get("label")))
                time.sleep(60)
                continue
            log("heavy_job.lock held by dead pid %s; taking it over" % pid)
            try:
                os.remove(LOCK)
            except FileNotFoundError:
                pass


def release_lock():
    try:
        with open(LOCK, encoding="utf-8") as fh:
            mine = int(json.load(fh).get("pid", -1)) == os.getpid()
        if mine:
            os.remove(LOCK)
            log("heavy_job.lock released")
    except FileNotFoundError:
        pass


def ms_of(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def load_dev(asset):
    """Bars and funding strictly before the seal (dropped right after reading)."""
    seal = pd.Timestamp(SEAL, tz="UTC")
    df = data.load(asset)
    df = df[df.index < seal]
    fund = None
    if asset in pb.CFG["crypto"]:
        fund = data.load_funding(asset)
        fund = fund[fund.index < seal]
    return df, fund


def metrics(tr):
    n = len(tr)
    if not n:
        return {"trades": 0}
    tr = sorted(tr, key=lambda t: t["exit_ms"])
    net = np.array([t["pnl_usd"] for t in tr])
    gross = np.array([t["gross_usd"] for t in tr])
    eq = np.concatenate([[0.0], np.cumsum(net)])
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    return {"trades": n, "win_pct": round(100.0 * float((net > 0).mean()), 1),
            "avg_r_gross": round(float(np.mean([t["gross_r"] for t in tr])), 3),
            "avg_r": round(float(np.mean([t["r"] for t in tr])), 3),
            "pf": round(float(pos / neg), 2) if neg > 0 else None,
            "exp_pct": round(float(net.mean() / pb.STAKE * 100), 4),
            "gross_exp_pct": round(float(gross.mean() / pb.STAKE * 100), 4),
            "net_usd": round(float(net.sum()), 2), "fees_usd": round(float(sum(t["fees_usd"] for t in tr)), 2),
            "max_dd_usd": round(float((np.maximum.accumulate(eq) - eq).max()), 2),
            "median_risk_pct": round(float(np.median([t["risk"] / t["entry"] * 100 for t in tr])), 3),
            "median_cost_r": round(float(np.median([t["gross_r"] - t["r"] for t in tr])), 3),
            "t1_hit_pct": round(100.0 * float(np.mean([bool(t.get("t1_hit")) for t in tr])), 1)}


def slim(t, asset):
    return {"asset": asset, "side": int(t["side"]), "entry_ms": int(t["entry_ms"]), "exit_ms": int(t["exit_ms"]),
            "pnl_usd": float(t["pnl_usd"]), "gross_usd": float(t["gross_usd"]), "fees_usd": float(t["fees_usd"]),
            "r": float(t["r"]), "gross_r": float(t["gross_r"]), "risk": float(t["risk"]), "entry": float(t["entry"]),
            "t1_hit": bool(t.get("t1_hit")), "why_out": t["why_out"], "pool": t["pool"]}


def truncation_check(df, asset, fund, cuts):
    """Every variant re-run on bars cut at each point must reproduce every trade closed before the cut."""
    full_P = pb.prepare(df, asset, funding=fund)
    full = dict((v, set((t["entry_ms"], t["exit_ms"], round(t["r"], 9)) for t in lh.run(full_P, ALL[v]) if t["status"] == "CLOSED"))
                for v in ORDER)
    checked = bad = 0
    for cut in cuts:
        P = pb.prepare(df[df.index < cut], asset, funding=fund)
        for v in ORDER:
            for t in lh.run(P, ALL[v]):
                if t["status"] == "CLOSED":
                    checked += 1
                    bad += (t["entry_ms"], t["exit_ms"], round(t["r"], 9)) not in full[v]
    return {"checked": checked, "mismatched": bad}


def run_asset(asset, start_ms, split_ms):
    df, fund = load_dev(asset)
    P = pb.prepare(df, asset, funding=fund)
    fee = pb.fee_side(asset)
    out = {"span": [str(df.index[0])[:16], str(df.index[-1])[:16]], "fee_side": fee, "variants": {}}
    # the control through liqhunt2 must equal playbook.simulate exactly
    ref = pb.simulate(P, pb.p1_signals(P, lh.BASE_RULE), "fixed", lh.HOLD_P1, fee)
    mine = lh.run(P, lh.CONTROL)
    key = lambda ts: [(t["status"], t.get("entry_ms"), t.get("exit_ms"), round(t.get("r", 0.0), 9)) for t in ts]  # noqa: E731
    out["control_equals_playbook"] = key(ref) == key(mine)
    trades = {}
    for v in ORDER:
        tr = lh.run(P, ALL[v], fee)
        cl = [t for t in tr if t["status"] == "CLOSED" and t["entry_ms"] >= start_ms]
        f = [slim(t, asset) for t in cl if t["entry_ms"] < split_ms]
        s = [slim(t, asset) for t in cl if t["entry_ms"] >= split_ms]
        trades[v] = (f, s)
        out["variants"][v] = {"first": metrics(f), "second": metrics(s),
                              "first_long": metrics([t for t in f if t["side"] > 0]), "first_short": metrics([t for t in f if t["side"] < 0]),
                              "second_long": metrics([t for t in s if t["side"] > 0]), "second_short": metrics([t for t in s if t["side"] < 0])}
    end = df.index[-1]
    sub = df[df.index >= end - pd.Timedelta(days=600)]
    out["truncation"] = truncation_check(sub, asset, fund, [end - pd.Timedelta(days=d) for d in (200, 30)])
    del P, df
    return out, trades


def score(res, v):
    vals, tot = [], 0
    for a in pb.ASSETS:
        m = res[a]["variants"][v]["first"]
        tot += m["trades"]
        if m["trades"] >= MIN_TRADES_ASSET:
            vals.append(m["exp_pct"])
    return (float(np.mean(vals)) if vals else -99.0), tot


def main():
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    if "--report" in sys.argv:
        with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
            J = json.load(fh)
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(J))
        return
    t0 = time.time()
    start_ms, split_ms = ms_of(START), ms_of(SPLIT)
    acquire_lock("H41 liqhunt2_study")
    try:
        res, pooled = {}, dict((v, ([], [])) for v in ORDER)
        for a in pb.ASSETS:
            if not resources.wait_for_memory(NEED_MB, max_wait_s=3600, poll_s=30, log=log):
                raise SystemExit("under %d MB free for an hour; stopped before %s" % (NEED_MB, a))
            log("%s: running (%.0f MB free)" % (a, resources.free_mb() or -1))
            res[a], tr = run_asset(a, start_ms, split_ms)
            for v in ORDER:
                pooled[v][0].extend(tr[v][0])
                pooled[v][1].extend(tr[v][1])
            log("%s: done (%.0fs), control==playbook %s, truncation %s" % (a, time.time() - t0, res[a]["control_equals_playbook"], res[a]["truncation"]))
    finally:
        release_lock()
    J = {"registered_utc": REGISTERED_UTC, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
         "protocol": {"start": START, "split": SPLIT, "seal": SEAL, "min_trades_asset": MIN_TRADES_ASSET,
                      "min_trades_all": MIN_TRADES_ALL, "min_trades_pass": MIN_TRADES_PASS,
                      "variants_h41": len(lh.VARIANTS), "variants_overall": PRIOR_VARIANTS + len(lh.VARIANTS)},
         "variants": dict((v, dict(ALL[v], levers=lh.n_levers(ALL[v]))) for v in ORDER), "assets": res, "pooled": {}}
    for v in ORDER:
        f, s = pooled[v]
        J["pooled"][v] = {"first": metrics(f), "second": metrics(s),
                          "first_long": metrics([t for t in f if t["side"] > 0]), "first_short": metrics([t for t in f if t["side"] < 0]),
                          "second_long": metrics([t for t in s if t["side"] > 0]), "second_short": metrics([t for t in s if t["side"] < 0])}
        pools = {}
        for half, ts in (("first", f), ("second", s)):
            for p in sorted(set(t["pool"] for t in ts)):
                pools.setdefault(p, {})[half] = metrics([t for t in ts if t["pool"] == p])
        J["pooled"][v]["pools"] = pools
    scores = dict((v, score(res, v)) for v in ORDER)
    J["scores_first_half"] = dict((v, {"score_pct": round(sc, 4), "trades": tot}) for v, (sc, tot) in scores.items())
    elig = [v for v in lh.VARIANTS if scores[v][1] >= MIN_TRADES_ALL]
    chosen = max(elig, key=lambda v: (round(scores[v][0], 10), -lh.n_levers(ALL[v]))) if elig else None
    J["chosen"] = chosen
    if chosen:
        s2, c2 = J["pooled"][chosen]["second"], J["pooled"]["P1"]["second"]
        pos_mk = [a for a in pb.ASSETS if res[a]["variants"][chosen]["second"].get("net_usd", 0) > 0]
        c1 = s2.get("trades", 0) >= MIN_TRADES_PASS and s2.get("net_usd", 0) > 0
        c3 = s2.get("trades", 0) > 0 and s2["exp_pct"] > c2.get("exp_pct", -99)
        J["pass"] = {"pooled_positive": bool(c1), "markets_positive": pos_mk, "markets_ok": len(pos_mk) >= 4,
                     "beats_p1": bool(c3), "passed": bool(c1 and len(pos_mk) >= 4 and c3)}
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(J))
    log("written %s (%.0fs); chosen %s; pass %s" % (OUT, time.time() - t0, chosen, J.get("pass")))


PLAIN = """- **No pass.** The chosen variant (V8: the P1 sweep without round-number pools, stop 0.5 ATR beyond the extreme, half at
  1R / rest at 2R, 24-bar hold) lost money in the second half on all six markets (pooled -0.066% a trade, -0.25R after
  costs, 9,815 trades). It lost less per trade than the original P1 (-0.076%), but the bar needs a profit, not a smaller
  loss.
- **The sweep itself carries no edge before costs.** Every variant, in both halves, averages between -0.03R and +0.01R
  BEFORE costs (the original P1: -0.03R / -0.02R). The levers change how much of each trade the costs eat (a wider stop
  cut the median cost from about 0.25R to 0.13-0.19R), but they cannot turn a zero-edge entry into a winning one. That
  is the main finding: on 2020-2025 history the "obvious pool, wick and reclaim" pattern is a coin flip before fees.
- **The trend filter did not help on history.** V2 (with the filter) and V8 (the same without it) are almost the same
  per trade in both halves; V8 scored slightly better and was chosen. On history long and short fades lose about the
  same (V8 second half: longs -0.063%, shorts -0.070% a trade). The four live days in which longs lost far more were one
  falling regime; history does not support that as a general rule.
- **Confirmation entries were worse.** Waiting for one more close on the reclaimed side (V4, V7) cut trades by about
  65%; their median stop was tighter (0.14-0.15% of price), so costs rose to about 0.3R. The limit retest (V5) sat
  in between.
- **Wider stops cut the cost share, not the loss in money.** V3 (1.0 ATR) has the best mean R after costs (-0.17R) but
  loses about the same % of stake per trade as V1 (0.1 ATR): fewer trades with more risk each and the same zero gross edge.
- **By the registered score, the original P1 (-0.092%) was not beaten even in the first half** by any v2 variant (best:
  V8 -0.095%). V8 is better only when trades are pooled (it drops many crypto and round-number trades). The choice was
  made among the eight v2 variants, as registered.
- Crypto pays the most: on BTC/ETH costs alone are 0.24-0.67R a trade on average (V8 and P1, both halves), and no variant overcame them.
- Checks passed: the control reproduces `playbook.simulate` trade for trade on every market, and every variant passes a
  truncation (no look-ahead) test. Variants tried overall: 37 (H6/H7 29 + H41 8). The holdout was not touched.
- Nothing goes forward: no `engine15/playbook8.py` was written. The original P1 keeps running as registered, under its
  own verdict rule.""".split("\n")


def vdesc(var):
    return "%s, %s, stop pad %.1f ATR, entry %s, exit %s, hold %d" % (
        "trend filter" if var["trend"] else "no trend filter", "no round numbers" if var["no_round"] else "round numbers in",
        var["pad"], var["entry"], {"E1": "half 1R / rest 2R, BE after 1R", "E2": "all at 1.5R"}[var["exit"]], var["hold"])


COLS = ("trades", "win_pct", "avg_r_gross", "avg_r", "pf", "exp_pct", "net_usd", "max_dd_usd", "median_risk_pct", "median_cost_r")
HEAD = "| trades | win % | mean R before costs | mean R after costs | PF | exp % / trade | net $ | max DD $ | median stop % | median cost R |"


def row(m):
    if not m or not m.get("trades"):
        return " | ".join(["0"] + ["-"] * (len(COLS) - 1))
    return " | ".join("-" if m.get(k) is None else ("{:,.2f}".format(m[k]) if k in ("net_usd", "max_dd_usd") else str(m[k])) for k in COLS)


def report(J):
    L = []
    a = L.append
    ch = J.get("chosen")
    ps = J.get("pass", {})
    a("# H41 liquidity hunt v2: history study")
    a("")
    a("Generated by `research/liqhunt2_study.py` (%s); rules in `engine15/liqhunt2.py`; registered in `research/HYPOTHESES.md` "
      "H41 at %s, before any code or number. Paper research only: history can reject a rule, never prove one." % (J["generated_utc"], J["registered_utc"]))
    a("")
    a("Development data only: bars before the sealed holdout %s 00:00 UTC (later bars and funding rows dropped right after loading). "
      "Trades from %s by entry time; first half before %s (used to choose), second half from it to the seal (used to confirm). "
      "$10,000 a trade at each asset's own fee a side (crypto 0.10%%, gold 0.02%%, silver 0.03%%, USDJPY 0.01%%, S&P 0.02%%). "
      "**Variants: 8 in H41; %d across H6, H7 and H41.** The original P1 (H6 registered rule) is re-run through the same code as "
      "the control." % (J["protocol"]["seal"], J["protocol"]["start"], J["protocol"]["split"], J["protocol"]["variants_overall"]))
    a("")
    a("## Verdict")
    a("")
    if ch:
        s1, s2 = J["pooled"][ch]["first"], J["pooled"][ch]["second"]
        p1, p2 = J["pooled"]["P1"]["first"], J["pooled"]["P1"]["second"]
        a("Chosen on the first half: **%s** (%s). First half pooled: %d trades, %s%% won, %+.3fR before / %+.3fR after costs, "
          "net $%s. Second half pooled: %d trades, %s%% won, %+.3fR before / %+.3fR after costs, net $%s, %+.4f%% a trade "
          "(original P1: %d trades, %+.4f%% a trade, net $%s)." % (
              ch, vdesc(J["variants"][ch]), s1["trades"], s1["win_pct"], s1["avg_r_gross"], s1["avg_r"], "{:,.0f}".format(s1["net_usd"]),
              s2["trades"], s2["win_pct"], s2["avg_r_gross"], s2["avg_r"], "{:,.0f}".format(s2["net_usd"]), s2["exp_pct"],
              p2["trades"], p2["exp_pct"], "{:,.0f}".format(p2["net_usd"])))
        a("")
        a("Pass bar (all three needed): pooled second half positive after costs with >= 100 trades: **%s**; positive in >= 4 of 6 "
          "markets: **%s** (%d: %s); better per trade than the original P1 in the second half: **%s**. **Result: %s.**" % (
              "yes" if ps["pooled_positive"] else "no", "yes" if ps["markets_ok"] else "no", len(ps["markets_positive"]),
              ", ".join(pb.SHORT_NAME[x] for x in ps["markets_positive"]) or "none", "yes" if ps["beats_p1"] else "no",
              "PASS" if ps["passed"] else "NO PASS"))
    else:
        a("No variant had 100 first-half trades; nothing chosen. **Result: NO PASS.**")
    a("")
    a("Checks: the control run through `liqhunt2.simulate` equals `playbook.simulate` trade for trade on every market: **%s**. "
      "Truncation test (every variant re-run on the last 600 days cut 200 and 30 days before the seal; every trade closed before "
      "a cut must match the full run): %s." % (
          "yes" if all(J["assets"][x]["control_equals_playbook"] for x in pb.ASSETS) else "NO",
          "; ".join("%s %d checked / %d mismatched" % (pb.SHORT_NAME[x], J["assets"][x]["truncation"]["checked"], J["assets"][x]["truncation"]["mismatched"]) for x in pb.ASSETS)))
    a("")
    a("## The variants and the first-half selection score")
    a("")
    a("Score = mean over markets (each with >= 20 first-half trades) of first-half expectancy after costs, % of stake per trade; "
      "eligible with >= 100 first-half trades in all.")
    a("")
    a("| id | rule | score % | first-half trades |")
    a("|---|---|---|---|")
    for v in ORDER:
        sc = J["scores_first_half"][v]
        a("| %s%s | %s | %s | %d |" % (v, " (chosen)" if v == ch else (" (control)" if v == "P1" else ""), vdesc(J["variants"][v]), sc["score_pct"], sc["trades"]))
    a("")
    a("## Pooled six markets, every variant")
    a("")
    a("| id | half " + HEAD)
    a("|---|---" + "|---" * len(COLS) + "|")
    for v in ORDER:
        for half in ("first", "second"):
            a("| %s | %s | %s |" % (v, half, row(J["pooled"][v][half])))
    a("")
    a("## Long and short fades, pooled (descriptive)")
    a("")
    a("| id | side | half " + HEAD)
    a("|---|---|---" + "|---" * len(COLS) + "|")
    for v in [x for x in ORDER if x in ((ch,) if ch else ()) + ("V2", "V8", "P1")]:
        for side in ("long", "short"):
            for half in ("first", "second"):
                a("| %s | %s | %s | %s |" % (v, side, half, row(J["pooled"][v]["%s_%s" % (half, side)])))
    a("")
    a("## Per market, every variant")
    for x in pb.ASSETS:
        a("")
        a("### %s (bars %s to %s, fee %.2f%% a side)" % (pb.SHORT_NAME[x], J["assets"][x]["span"][0], J["assets"][x]["span"][1], 100 * J["assets"][x]["fee_side"]))
        a("")
        a("| id | half " + HEAD)
        a("|---|---" + "|---" * len(COLS) + "|")
        for v in ORDER:
            for half in ("first", "second"):
                a("| %s | %s | %s |" % (v, half, row(J["assets"][x]["variants"][v][half])))
    if ch:
        a("")
        a("## Chosen variant by pool, pooled (descriptive, not used to choose)")
        a("")
        a("| pool | half | trades | win % | mean R after costs | exp % / trade | net $ |")
        a("|---|---|---|---|---|---|---|")
        for p, d in sorted(J["pooled"][ch]["pools"].items()):
            for half in ("first", "second"):
                m = d.get(half, {})
                if m.get("trades"):
                    a("| %s | %s | %d | %s | %s | %s | %s |" % (p, half, m["trades"], m["win_pct"], m["avg_r"], m["exp_pct"], "{:,.0f}".format(m["net_usd"])))
    a("")
    a("## Plain English")
    a("")
    for line in PLAIN:
        a(line)
    a("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
