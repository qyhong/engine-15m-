# -*- coding: utf-8 -*-
"""H65: post-mortem of the Setups book (b_targets), where its results come from. Research only; registered in
research/HYPOTHESES.md before this file existed. Reads the evidence store and the cached fits; changes nothing.

    /data/venv-research/bin/python research/h65_setups_postmortem.py --fits-dir research/out/h60_regime_exits/fits_today
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

from engine15 import labels, shadows  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h65_setups_postmortem")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
MID = pd.Timestamp("2023-06-08", tz="UTC")
MIN_PART = 100
TARGET_WORDS = ("T2", "STOP_BE")


def rows_of(prep, a, lo, n, book, cfg):
    """One row per closed trade with the readings of the bar that decided it."""
    times, px, ev, odds = prep["times"], prep["px"][a], prep["ev"][a], prep["odds"][a]
    h, l, c = px["high"], px["low"], px["close"]
    tide, bias = ev["tide"].values, ev["htf_bias"].values
    delay = int(cfg.get("fill_delay_bars", 0) or 0)
    out, prev = [], None
    for t in book["trades"].itertuples():
        i, j, side = int(t.i_in), int(t.i_out), int(t.side)
        k = max(i - 1 - delay, 0)                                 # the bar that decided it
        risk = abs(t.p_in - t.stop0)
        i30 = int(times.searchsorted(times[k] - pd.Timedelta(days=30)))
        mv = np.nan if i30 <= 0 else c[k] / c[i30] - 1.0          # no bar 30 days back yet: unknown
        pu, pd_ = odds[k, labels.UP], odds[k, labels.DOWN]
        lead = side * (pu - pd_) if pu == pu and pd_ == pd_ else np.nan
        best = 0.0
        if j > i and risk > 0:
            fav = (h[i:j].max() - t.p_in) if side > 0 else (t.p_in - l[i:j].min())
            best = max(0.0, fav) / risk
        tags = str(t.why_out).split("+")
        end = "stop" if tags[-1] == "STOP" else ("target" if tags[-1] in TARGET_WORDS else "other")
        b = bias[k]
        td = tide[k]
        out.append({"asset": a, "time": times[i], "half": 1 if times[i] < MID else 2, "r": float(t.r_mult),
                    "win": bool(t.pnl_usd > 0), "word": str(t.why_in), "side": "long" if side > 0 else "short",
                    "bias": "none" if not (b == b) or b == 0 else ("with" if int(b) == side else "against"),
                    "tide": "unknown" if not (td == td) or td == 0 else ("with" if np.sign(td) == side else "against"),
                    "move30": "unknown" if not (mv == mv) or mv == 0 else ("with" if np.sign(mv) == side else "against"),
                    "lead": float(lead), "stop_pct": float(risk / t.p_in * 100.0),
                    "t1_r": float(abs(t.target_1 - t.p_in) / risk) if t.target_1 == t.target_1 and risk > 0 else np.nan,
                    "before": "first" if prev is None else prev["end"],
                    "same_side": None if prev is None else prev["side"] == side,
                    "exit": str(t.why_out), "end": end, "took_t1": "T1" in tags, "best_r": float(best), "bars": j - i})
        prev = {"end": end, "side": side}
    return out


def thirds(df, col, cuts):
    lo_, hi_ = cuts
    return np.where(df[col].isna(), "unknown", np.where(df[col] <= lo_, "low", np.where(df[col] <= hi_, "mid", "high")))


def cell(d):
    if not len(d):
        return {"n": 0}
    return {"n": int(len(d)), "won": float(d["win"].mean() * 100), "mean_r": float(d["r"].mean()), "sum_r": float(d["r"].sum())}


def table(df, col):
    out = {}
    for v in sorted(df[col].dropna().astype(str).unique()):
        d = df[df[col].astype(str) == v]
        parts = {"all": cell(d), "h1": cell(d[d.half == 1]), "h2": cell(d[d.half == 2]),
                 "vault": cell(d[d.asset.isin(VAULT)]), "others": cell(d[~d.asset.isin(VAULT)]),
                 "vault_h1": cell(d[d.asset.isin(VAULT) & (d.half == 1)]), "vault_h2": cell(d[d.asset.isin(VAULT) & (d.half == 2)])}
        four = [parts[k] for k in ("h1", "h2", "vault", "others")]
        ok = all(p["n"] >= MIN_PART for p in four)
        signs = set(np.sign(p["mean_r"]) for p in four) if ok else set()
        parts["call"] = ("consistent %s" % ("positive" if signs == {1.0} else "negative")) if ok and len(signs) == 1 and 0.0 not in signs \
            else ("not consistent" if ok else "too few trades in a part")
        out[v] = parts
    return out


def run(fits_root, log=print):
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    t0 = time.time()
    rows = []
    for g, assets in GROUPS:
        prep = h59.prep_cut(g, assets, os.path.join(fits_root, g), h62.group_end(g, assets), log=log)
        n = len(prep["times"])
        for a in assets:
            ok = np.isfinite(prep["odds"][a][:, 0])
            lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
            aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
            cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
            book = h59.run_book("b_targets", prep, a, lo, n, aux)
            got = rows_of(prep, a, lo, n, book, cfg)
            rows += got
            log("%s: %d trades, sum of R %+.1f (%.0fs)" % (a, len(got), sum(r["r"] for r in got), time.time() - t0))
        del prep
    df = pd.DataFrame(rows)
    df = df[np.isfinite(df["r"])].reset_index(drop=True)
    h1 = df[df.half == 1]
    df["lead3"] = thirds(df, "lead", tuple(h1["lead"].quantile([1 / 3, 2 / 3])))
    df["t1r3"] = thirds(df, "t1_r", tuple(h1["t1_r"].quantile([1 / 3, 2 / 3])))
    df["stop3"] = "unknown"
    for a in df.asset.unique():
        m = df.asset == a
        q = tuple(h1[h1.asset == a]["stop_pct"].quantile([1 / 3, 2 / 3]))
        df.loc[m, "stop3"] = thirds(df[m], "stop_pct", q)
    df["before_side"] = df["before"] + np.where(df["same_side"].isna(), "", np.where(df["same_side"] == True, ", same side", ", other side"))  # noqa: E712
    res = {"trades": int(len(df)), "from": str(df.time.min())[:16], "to": str(df.time.max())[:16],
           "overall": {"all": cell(df), "h1": cell(h1), "h2": cell(df[df.half == 2]), "vault": cell(df[df.asset.isin(VAULT)]),
                       "others": cell(df[~df.asset.isin(VAULT)])},
           "per_market": dict((a, {"all": cell(df[df.asset == a]), "h1": cell(df[(df.asset == a) & (df.half == 1)]),
                                   "h2": cell(df[(df.asset == a) & (df.half == 2)])}) for a in df.asset.unique()),
           "slices": {}}
    for name, col in (("1 entry word", "word"), ("2 side", "side"), ("3 higher-timeframe bias", "bias"), ("4 tide", "tide"),
                      ("5 the market's 30-day move", "move30"), ("6 lead in the odds (thirds)", "lead3"),
                      ("7 stop distance (thirds per market)", "stop3"), ("8 Target 1 distance in R (thirds)", "t1r3"),
                      ("9a the trade before ended", "before"), ("9b ... and this one is on", "before_side")):
        res["slices"][name] = table(df, col)
    stops = df[df["exit"] == "STOP"]
    t1 = df[df.took_t1]
    ex = {}
    for w, d in df.groupby("exit"):
        ex[w] = cell(d)
    res["exits"] = {"words": ex,
                    "stopped_at_entry_stop": int(len(stops)),
                    "of_those_had_half_r_first_pct": float((stops.best_r >= 0.5).mean() * 100) if len(stops) else None,
                    "of_those_had_one_r_first_pct": float((stops.best_r >= 1.0).mean() * 100) if len(stops) else None,
                    "took_t1": int(len(t1)), "took_t1_pct": float(len(t1) / len(df) * 100),
                    "of_t1_reached_t2_pct": float(t1["exit"].str.endswith("T2").mean() * 100) if len(t1) else None,
                    "of_t1_back_to_entry_pct": float(t1["exit"].str.endswith("STOP_BE").mean() * 100) if len(t1) else None,
                    "median_bars_held": float(df.bars.median()),
                    "median_bars_held_stopped": float(stops.bars.median()) if len(stops) else None,
                    "by_half": dict((h, {"stopped_pct": float((d["exit"] == "STOP").mean() * 100),
                                         "took_t1_pct": float(d.took_t1.mean() * 100)}) for h, d in df.groupby("half"))}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res)
    return res


def _c(p):
    return "-" if not p.get("n") else "%d, %.0f%%, %+.3f, %+.1f" % (p["n"], p["won"], p["mean_r"], p["sum_r"])


def write_report(res):
    L = ["# H65: post-mortem of the Setups book", "",
         "History replay, %d closed trades on eight markets, %s to %s UTC. Registered before any number." % (
             res["trades"], res["from"], res["to"]),
         "Every cell: trades, share won, mean R, sum of R. A history replay is a warm-up, not a forward result.", "",
         "## Overall", "", "| Part | All | First half | Second half |", "|---|---|---|---|",
         "| All eight | %s | %s | %s |" % (_c(res["overall"]["all"]), _c(res["overall"]["h1"]), _c(res["overall"]["h2"])),
         "| BTC and ETH | %s | | |" % _c(res["overall"]["vault"]), "| The other six | %s | | |" % _c(res["overall"]["others"])]
    for a, p in res["per_market"].items():
        L.append("| %s | %s | %s | %s |" % (a, _c(p["all"]), _c(p["h1"]), _c(p["h2"])))
    for name, tab in res["slices"].items():
        L += ["", "## Slice %s" % name, "", "| Cell | All | First half | Second half | BTC and ETH | The other six | Call |",
              "|---|---|---|---|---|---|---|"]
        for v, p in tab.items():
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (v, _c(p["all"]), _c(p["h1"]), _c(p["h2"]), _c(p["vault"]),
                                                             _c(p["others"]), p["call"]))
    e = res["exits"]
    L += ["", "## Slice 10: exits (facts, not a slice to trade on)", "", "| Exit | Trades, won, mean R, sum R |", "|---|---|"]
    for w, p in sorted(e["words"].items(), key=lambda kv: -kv[1]["n"]):
        L.append("| %s | %s |" % (w, _c(p)))
    L += ["", "- Stopped at the entry stop: %d trades; %.0f%% of them had been at least 0.5R in open profit first, %.0f%% at least 1R." % (
        e["stopped_at_entry_stop"], e["of_those_had_half_r_first_pct"], e["of_those_had_one_r_first_pct"]),
          "- Took Target 1: %d trades (%.0f%%); of those %.0f%% went on to Target 2 and %.0f%% came back to the entry." % (
              e["took_t1"], e["took_t1_pct"], e["of_t1_reached_t2_pct"], e["of_t1_back_to_entry_pct"]),
          "- Median bars held: %.0f (stopped trades: %.0f)." % (e["median_bars_held"], e["median_bars_held_stopped"])]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    if a.report:
        with open(os.path.join(OUT, "results.json")) as fh:
            write_report(json.load(fh))
        return
    run(a.fits_dir)


if __name__ == "__main__":
    main()
