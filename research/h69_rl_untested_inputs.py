# -*- coding: utf-8 -*-
"""H69: RL round 5 pre-check. Do the four untested crypto inputs (Korea premium, BTC dominance, spot vs perp leadership,
CME gap) carry anything on their own, one at a time? Registration: research/HYPOTHESES.md "## H69" (committed before
this file existed).

Run from a folder holding engine15/ and research/ (this branch's code) and data -> the engine's data folder (read only):
    nice -n 19 /data/venv-research/bin/python -X utf8 research/h69_rl_untested_inputs.py

What it does, as registered:
  * copies the cryptox source files the four cards read into ./h69_cut_sources, keeping only rows whose known_ms is
    before 2025-11-11 00:00 UTC (the sealed holdout is never loaded into the computation);
  * loads the spot bars and drops every bar opening at or after 2025-11-10 23:45 UTC before anything is computed;
  * recomputes the 13 features with the engine's own cryptox.features() (no new transform);
  * a truncation check: features recomputed on bars and sources cut at an earlier time must equal the full values on
    every row up to that time;
  * raw and partial (beyond past price) Spearman ICs against forward log returns at 4, 16, 96 bars, per coin and half,
    with month-clustered bootstrap intervals; volatility-third ICs (descriptive); the registered verdicts.
Writes research/out/h69_rl_untested_inputs/results.json and report.md. Writes nothing else except the cut copies.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine15 import data as D            # noqa: E402
from engine15.sources import cryptox as CX  # noqa: E402

ASSETS = ["BTCUSDT", "ETHUSDT"]
START = pd.Timestamp("2020-01-01 00:00", tz="UTC")
SPLIT = pd.Timestamp("2023-06-08 00:00", tz="UTC")
LAST_OPEN_EXCL = pd.Timestamp("2025-11-10 23:45", tz="UTC")     # bars opening before this only
CUT_MS = int(pd.Timestamp("2025-11-11 00:00", tz="UTC").value // 10 ** 6)
HORIZONS = [4, 16, 96]
BAR_MS = 900000
B = 2000
SEED = 20261122
MIN_IC = 0.01

GROUP_FEATS = {
    "kprem": ["kp_prem", "kp_z30", "kp_chg24"],
    "dom": ["dm_btc_7d", "dm_btc_30d", "dm_stable_7d", "dm_stable_30d"],
    "spotlead": ["sl_share_z", "sl_taker_diff", "sl_lead"],
    "cmegap": ["cg_open", "cg_above", "cg_below"],
}
GROUP_TITLE = {"kprem": "Korea premium", "dom": "BTC dominance", "spotlead": "Spot vs perp leadership",
               "cmegap": "CME gap (spot proxy)"}
# feature -> raw companion columns that must all be finite for a read
COMPANION = {
    "kp_prem": ["kp_prem_pct"], "kp_z30": ["kp_z30_raw"], "kp_chg24": ["kp_chg24_pct"],
    "dm_btc_7d": ["dm_btc_7d_pp"], "dm_btc_30d": ["dm_btc_30d_pp"],
    "dm_stable_7d": ["dm_stable_7d_pp"], "dm_stable_30d": ["dm_stable_30d_pp"],
    "sl_share_z": ["sl_share_z_raw"], "sl_taker_diff": ["sl_taker_spot", "sl_taker_perp"], "sl_lead": ["sl_lead_raw"],
    "cg_open": ["cg_open_atr"], "cg_above": ["cg_n_open"], "cg_below": ["cg_n_open"],
}
SOURCE_FILES = [("upbit", "BTCUSDT"), ("upbit", "ETHUSDT"), ("perp", "BTCUSDT"), ("perp", "ETHUSDT"),
                ("fx", None), ("caps", None), ("stables", None)]
OUT = os.path.join(ROOT, "research", "out", "h69_rl_untested_inputs")
CUT_DIR = os.path.join(ROOT, "h69_cut_sources")


def say(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ------------------------------------------------------------------ data, cut before the holdout
def cut_sources(dst, cut_ms):
    """Copy each source file keeping header + rows with known_ms < cut_ms (text kept verbatim). -> {file: rows kept}."""
    os.makedirs(dst, exist_ok=True)
    kept = {}
    for kind, asset in SOURCE_FILES:
        src = CX.path_for(kind, asset)
        out = CX.path_for(kind, asset, dst)
        n = 0
        with open(src, "r", encoding="utf-8") as fi, open(out, "w", encoding="utf-8", newline="") as fo:
            head = fi.readline()
            fo.write(head)
            k = head.strip().split(",").index("known_ms")
            for line in fi:
                parts = line.rstrip("\r\n").split(",")
                try:
                    v = float(parts[k])
                except (ValueError, IndexError):
                    continue
                if np.isfinite(v) and v < cut_ms:
                    fo.write(line)
                    n += 1
        kept[os.path.basename(out)] = n
    return kept


def load_bars(asset, last_open_excl):
    b = D.load(asset)
    b = b[~b.index.duplicated(keep="last")].sort_index()
    return b[b.index < last_open_excl]


# ------------------------------------------------------------------ statistics
def ranks(x):
    return pd.Series(x).rank(method="average").values


def zs(x):
    x = np.asarray(x, dtype=float)
    s = x.std()
    return (x - x.mean()) / s if s > 0 else x * 0.0


def resid(y, X):
    A = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def month_sums(x, y, months):
    df = pd.DataFrame({"m": months, "x": x, "y": y})
    df["xx"], df["yy"], df["xy"], df["n"] = df.x * df.x, df.y * df.y, df.x * df.y, 1.0
    g = df.groupby("m")[["n", "x", "y", "xx", "yy", "xy"]].sum()
    return g.values


def corr_from(S):
    n, sx, sy, sxx, syy, sxy = [S[..., i] for i in range(6)]
    num = n * sxy - sx * sy
    den = np.sqrt(np.maximum(n * sxx - sx * sx, 0) * np.maximum(n * syy - sy * sy, 0))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


_W = {}


def boot_weights(m):
    if m not in _W:
        rng = np.random.default_rng(SEED + m)
        _W[m] = rng.multinomial(m, np.full(m, 1.0 / m), size=B).astype(float)
    return _W[m]


def ic_with_ci(x, y, months):
    """Pearson of (already ranked / residualised) x, y; month-clustered bootstrap 95% interval."""
    S = month_sums(x, y, months)
    est = float(corr_from(S.sum(axis=0)))
    W = boot_weights(len(S))
    bs = corr_from(W @ S)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return {"ic": round(est, 5), "lo": round(float(lo), 5), "hi": round(float(hi), 5), "n": int(len(x)),
            "months": int(len(S))}


# ------------------------------------------------------------------ per asset
def frame_for(asset, bars, src_dir):
    f = CX.features(bars.index, asset, src_dir=src_dir, bars=bars)
    grid = pd.date_range(bars.index[0], bars.index[-1], freq="15min")
    c = bars["close"].reindex(grid)
    lc = np.log(c)
    r1 = lc.diff()
    t = pd.DataFrame(index=grid)
    for h in HORIZONS:
        t["fwd_%d" % h] = lc.shift(-h) - lc
    for h in (4, 16, 96, 672):
        t["past_%d" % h] = lc - lc.shift(h)
    t["rv96"] = r1.rolling(96, min_periods=80).std()
    t = t.reindex(bars.index)
    return f, t


def shut_mask(index, asset):
    """Rows whose close lies while CME is shut (from the CME launch week): the denominator for cg_open."""
    cl = D.to_ms(index) + BAR_MS
    m = np.zeros(len(cl), dtype=bool)
    start = CX._ms(CX.CME_START[asset])
    for c_ms, o_ms in CX.cme_sessions(cl[0], cl[-1]):
        if c_ms < start:
            continue
        a, b = np.searchsorted(cl, c_ms, side="right"), np.searchsorted(cl, o_ms, side="left")
        m[a:b] = True
    return m


def usable(f, feat):
    ok = np.ones(len(f), dtype=bool)
    for c in COMPANION[feat]:
        ok &= np.isfinite(f[c].values)
    return ok & np.isfinite(f[feat].values)


def truncation_check(asset, bars_full, f_full, cut_ts, tmp_dir):
    cut_ms = int(cut_ts.value // 10 ** 6)
    cut_sources(tmp_dir, cut_ms)
    b = bars_full[bars_full.index < cut_ts - pd.Timedelta(minutes=15)]          # last bar closes at cut_ts or before
    g = CX.features(b.index, asset, src_dir=tmp_dir, bars=b)
    cols = sorted(set(sum(GROUP_FEATS.values(), [])) | set(sum(COMPANION.values(), [])))
    a, z = f_full.loc[b.index, cols].values.astype(float), g[cols].values.astype(float)
    same = (np.isclose(a, z, rtol=1e-9, atol=1e-12) | (np.isnan(a) & np.isnan(z)))
    bad = {c: int((~same[:, i]).sum()) for i, c in enumerate(cols) if (~same[:, i]).any()}
    return {"cut": str(cut_ts), "rows": int(len(b)), "mismatched_cells_by_column": bad, "ok": not bad}


def run():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    say("cutting source files before the holdout")
    kept = cut_sources(CUT_DIR, CUT_MS)
    res = {"study": "H69", "registered_commit_note": "registration committed before this code (research/HYPOTHESES.md H69)",
           "data": {"start": str(START), "split": str(SPLIT), "last_bar_open_before": str(LAST_OPEN_EXCL),
                    "source_cut_known_ms_before": CUT_MS, "source_rows_kept": kept},
           "horizons_bars": HORIZONS, "bootstrap": {"B": B, "seed": SEED, "cluster": "calendar month of the decision"},
           "availability": {}, "truncation": {}, "ic": {}, "vol_thirds": {}, "pass": {}, "verdict": {}, "errors": {}}
    store = {}
    for asset in ASSETS:
        say("%s: bars and features" % asset)
        bars = load_bars(asset, LAST_OPEN_EXCL)
        f, t = frame_for(asset, bars, CUT_DIR)
        res["errors"][asset] = f.attrs.get("errors", {})
        cut_ts = pd.Timestamp("2022-09-14 13:00", tz="UTC") if asset == "BTCUSDT" else pd.Timestamp("2024-03-20 07:00", tz="UTC")
        say("%s: truncation check at %s" % (asset, cut_ts))
        res["truncation"][asset] = truncation_check(asset, bars, f, cut_ts, CUT_DIR + "_trunc")
        store[asset] = (bars, f, t)

    # ---- per coin: rows, halves, availability
    for asset in ASSETS:
        bars, f, t = store[asset]
        idx = bars.index
        dec_close = idx + pd.Timedelta(minutes=15)
        in_range = idx >= START
        half = np.where(dec_close < SPLIT, 1, 2)
        months = np.asarray(idx.strftime("%Y-%m"))
        shut = shut_mask(idx, asset)
        rv = t["rv96"].values
        q = np.nanquantile(rv[in_range], [1 / 3, 2 / 3])
        third = np.where(np.isfinite(rv), np.digitize(rv, q), -1)
        res["availability"][asset] = {"vol_third_cuts_rv96": [float(q[0]), float(q[1])]}
        for g, feats in GROUP_FEATS.items():
            for feat in feats:
                ok = usable(f, feat) & in_range
                first = str(idx[np.argmax(ok)]) if ok.any() else None
                av = {"first_read": first}
                for hh in (1, 2):
                    base = in_range & (half == hh)
                    if feat == "cg_open":
                        base = base & shut
                    okh = ok & (half == hh)
                    mcount = pd.Series(okh).groupby(months).sum()
                    av["half%d" % hh] = {"rows": int(base.sum()), "usable": int(okh.sum()),
                                         "share_usable": round(float(okh.sum()) / max(int(base.sum()), 1), 4),
                                         "months_1000": int((mcount >= 1000).sum())}
                res["availability"][asset][feat] = av
                for h in HORIZONS:
                    fwd = t["fwd_%d" % h].values
                    fwd_close = dec_close + pd.Timedelta(minutes=15 * h)
                    ctrl = t[["past_4", "past_16", "past_96", "past_672", "rv96"]].values
                    for hh in (1, 2):
                        if hh == 1:
                            sel = (dec_close < SPLIT) & (fwd_close < SPLIT)
                        else:
                            sel = dec_close >= SPLIT
                        sel = np.asarray(sel) & ok & np.isfinite(fwd) & np.all(np.isfinite(ctrl), axis=1)
                        key = "%s|%s|h%d|half%d" % (asset, feat, h, hh)
                        if sel.sum() < 1000:
                            res["ic"][key] = {"raw": None, "partial": None, "n": int(sel.sum())}
                            continue
                        x, y, m = f[feat].values[sel], fwd[sel], months[sel]
                        rx, ry = zs(ranks(x)), zs(ranks(y))
                        raw = ic_with_ci(rx, ry, m)
                        C = np.column_stack([zs(ranks(ctrl[sel][:, j])) for j in range(ctrl.shape[1])])
                        px, py = resid(rx, C), resid(ry, C)
                        part = ic_with_ci(px, py, m)
                        res["ic"][key] = {"raw": raw, "partial": part}
                        vt = {}
                        th = third[sel]
                        for k in (0, 1, 2):
                            s2 = th == k
                            if s2.sum() < 1000:
                                vt["third%d" % (k + 1)] = None
                                continue
                            vt["third%d" % (k + 1)] = ic_with_ci(zs(ranks(x[s2])), zs(ranks(y[s2])), m[s2])
                        res["vol_thirds"][key] = vt
        say("%s: ICs done" % asset)

    # ---- the registered rule
    def coin_pass(asset, feat, h, meas):
        cells = [res["ic"].get("%s|%s|h%d|half%d" % (asset, feat, h, hh), {}).get(meas) for hh in (1, 2)]
        if any(c is None for c in cells):
            return False, 0
        s = [np.sign(c["ic"]) for c in cells]
        ok = (s[0] == s[1] != 0 and all(abs(c["ic"]) >= MIN_IC for c in cells)
              and all(c["lo"] > 0 or c["hi"] < 0 for c in cells))
        return bool(ok), int(s[0])

    def testable(g):
        out = {}
        for asset in ASSETS:
            for hh in (1, 2):
                avs = [res["availability"][asset][ft]["half%d" % hh] for ft in GROUP_FEATS[g]]
                bad = all(a["months_1000"] < 12 for a in avs) or all(a["share_usable"] < 0.5 for a in avs)
                out["%s|half%d" % (asset, hh)] = not bad
        return all(out.values()), out

    for g, feats in GROUP_FEATS.items():
        ok_t, cells = testable(g)
        worth, past, one = [], [], []
        for feat in feats:
            for h in HORIZONS:
                rec = {}
                for meas in ("raw", "partial"):
                    pb, sb = coin_pass("BTCUSDT", feat, h, meas)
                    pe, se = coin_pass("ETHUSDT", feat, h, meas)
                    both = pb and pe and (sb == se or g == "dom")
                    rec[meas] = {"btc": pb, "btc_sign": sb, "eth": pe, "eth_sign": se, "both": bool(both)}
                res["pass"]["%s|h%d" % (feat, h)] = rec
                tag = "%s h%d" % (feat, h)
                if rec["raw"]["both"] and rec["partial"]["both"]:
                    worth.append(tag)
                elif rec["raw"]["both"]:
                    past.append(tag)
                for c in ("btc", "eth"):
                    if rec["raw"][c] and rec["partial"][c]:
                        one.append("%s (%s)" % (tag, c.upper()))
        if not ok_t:
            v = "CANNOT BE TESTED YET"
        elif worth:
            v = "WORTH A REGISTERED PLACE IN ROUND 5"
        elif past:
            v = "MOSTLY PAST PRICE"
        elif one:
            v = "ONE COIN ONLY"
        else:
            v = "NOTHING SHOWN"
        res["verdict"][g] = {"title": GROUP_TITLE[g], "verdict": v, "testable_cells": cells, "passes_raw_and_partial": worth,
                             "passes_raw_only": past, "one_coin_raw_and_partial": one}
    res["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fo:
        json.dump(res, fo, indent=1)
    write_report(res)
    say("done in %.0f s" % res["seconds"])


def fmt(c):
    if not c:
        return "n/a"
    star = "*" if (c["lo"] > 0 or c["hi"] < 0) else ""
    return "%+.3f%s" % (c["ic"], star)


def write_report(res):
    L = ["# H69 results: the four untested crypto inputs, one at a time", "",
         "Registered in `research/HYPOTHESES.md` (H69) before any code or number. Decisions 2020-01-01 to the last bar "
         "opening before 2025-11-10 23:45 UTC; halves split 2023-06-08; the sealed holdout (2025-11-11 on) was not loaded. "
         "IC = Spearman rank correlation of the feature at a bar's close with the forward log return; partial = after "
         "taking out trailing returns (1h, 4h, 24h, 7d) and 24h realised volatility. * = month-clustered 95% interval "
         "excludes zero. Nothing here is evidence of an advantage.", "", "## Verdicts", ""]
    for g, v in res["verdict"].items():
        L.append("- **%s**: %s. Raw and partial pass: %s. Raw only: %s. One coin: %s." % (
            v["title"], v["verdict"], ", ".join(v["passes_raw_and_partial"]) or "none",
            ", ".join(v["passes_raw_only"]) or "none", ", ".join(v["one_coin_raw_and_partial"]) or "none"))
    L += ["", "## Truncation check", ""]
    for a, t in res["truncation"].items():
        L.append("- %s cut %s, %d rows: %s %s" % (a, t["cut"], t["rows"], "OK" if t["ok"] else "MISMATCH",
                                                 t["mismatched_cells_by_column"] or ""))
    L += ["", "## Availability (usable rows, share of the half, months with 1,000+ rows)", "",
          "| Feature | Coin | first read | half 1 | half 2 |", "|---|---|---|---|---|"]
    for g, feats in GROUP_FEATS.items():
        for ft in feats:
            for a in ASSETS:
                av = res["availability"][a][ft]
                h1, h2 = av["half1"], av["half2"]
                L.append("| %s | %s | %s | %d, %.0f%%, %d | %d, %.0f%%, %d |" % (
                    ft, a[:3], (av["first_read"] or "none")[:16], h1["usable"], 100 * h1["share_usable"], h1["months_1000"],
                    h2["usable"], 100 * h2["share_usable"], h2["months_1000"]))
    L += ["", "## ICs: raw / partial, half 1 | half 2", "",
          "| Feature | h | BTC raw | BTC partial | ETH raw | ETH partial | pass raw | pass partial |",
          "|---|---|---|---|---|---|---|---|"]
    for g, feats in GROUP_FEATS.items():
        for ft in feats:
            for h in HORIZONS:
                cells = []
                for a in ASSETS:
                    for meas in ("raw", "partial"):
                        c1 = res["ic"].get("%s|%s|h%d|half1" % (a, ft, h), {}).get(meas)
                        c2 = res["ic"].get("%s|%s|h%d|half2" % (a, ft, h), {}).get(meas)
                        cells.append("%s / %s" % (fmt(c1), fmt(c2)))
                p = res["pass"]["%s|h%d" % (ft, h)]
                pr = lambda r: ("both" if r["both"] else "BTC" if r["btc"] else "ETH" if r["eth"] else "-")  # noqa: E731
                L.append("| %s | %d | %s | %s | %s |" % (ft, h, " | ".join(cells), pr(p["raw"]), pr(p["partial"])))
    L += ["", "Volatility-third ICs (descriptive, pass nothing) are in `results.json` under `vol_thirds`.",
          "Errors from cards not under test (options flow, cross-exchange funding: their files were not copied) are "
          "expected: %s" % json.dumps(res["errors"])]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fo:
        fo.write("\n".join(L) + "\n")


if __name__ == "__main__":
    run()
