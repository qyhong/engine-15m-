# -*- coding: utf-8 -*-
"""B trail's history replay: the shadow book b_trail (engine15/shadows.py) on every market from 2020-01-01 to the
moment its LIVE forward record starts, with today's engine. PAPER ONLY.

    HISTORY REPLAY WITH TODAY'S ENGINE, IN-SAMPLE, NOT A TEST.

    python research/b_trail_history.py                  every market group, one after another, then the report
    python research/b_trail_history.py --group fx       one group (stage A: research/out/b_trail_history/parts/)
    python research/b_trail_history.py --report         merge the parts: trades.csv and summary.json

What it is. The owner wants ONE place where B trail's past trades (this replay) and its forward trades (live, since
11 Nov 2026: out/live/shadow_trades_b_trail_<ASSET>.csv) are seen together (engine15/book_view.py reads the files
written here). The book's rule is not touched: shadows.run_challenger("b_trail") runs exactly as the live step runs
it (the main book's entries; once a trade is +1R the stop trails the last confirmed 15m swing or 2 x ATR(14, 15m),
whichever is tighter; it re-enters on its own clock). The main book's rule (shadows "main", hold to the stop or the
flip) runs beside it on the same span for comparison, as H36 did (research/exit_study.py).

The odds, as H36 / research/setups_filter.py formed them, with the CURRENT engine (version and readings of today):
  * the evidence store data/evcache/<group>/<asset> is opened READ-ONLY with research/card_overlap.open_stores (mode
    "r" memory maps; the store's version is checked against the code; a store being built is waited for, never read);
    the copy is taken between 4 and 13 minutes into a quarter hour (the engine rewrites the stores for ~2.5 minutes
    after each one) and taken again if group.json changed during it; rows are copied into memory and the maps let go;
    nothing under data/ is ever written;
  * labels, weekly refits walked forward from the engine's birth (2020-01-01) by leanprep.walk_forward_cached, the
    refits cached in a PRIVATE folder research/out/b_trail_history/fits/<group> (deleted after the run), trust, the
    group's voting cards and grading horizon, the trust cap and the mix exactly as leanprep.prepare_live forms them
    (the live step walks only the last 240 days; this walk starts at the birth, as H36).

The hand-over. Each market group's forward books started flat at page["shadows"]["markets"][group]["started_utc"]
(the close of the first session they read; their first fill is at that time at the earliest). The replay uses only
the bars that OPEN before that time, so its last mark is the close at started_utc and the two records never overlap.
A trade still open then is closed in this file at that close, at the marked price less the exit fee (why_out
HANDOVER, at_handover = 1), so that each market's trades add up to its final equity. Each market's book starts at
$10,000 and compounds (each entry sized from the book's equity, as live).
"""
import argparse
import gc
import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "b_trail_history")
FITS = os.path.join(OUT, "fits")
PARTS = os.path.join(OUT, "parts")
PAGE = os.path.join(ROOT, "out", "live", "page.json")
LABEL = "history replay with today's engine, in-sample, not a test"
BOOK, BASE = "b_trail", "main"
START = 10000.0
GROUP_ORDER = ("crypto", "metals", "fx", "energy", "index")
TRADE_FIELDS = ["market", "group", "side", "time_in", "time_out", "entry", "exit", "stop", "why_in", "why_out",
                "pnl_pct", "pnl_usd", "r", "fees_usd", "equity_after", "qty", "at_handover"]
H36 = {"source": "research/out/exits/trail_study.json (H36, written 13 Nov 2026 04:30 UTC)", "version": "think15-v5.1",
       "span": "first session with odds (Feb 2020; SPX Jan 2021) to 13 Nov 2026 ~04:00 UTC",
       "b_trail_net_usd": -48808.27, "b_trail_trades": 11663, "main_net_usd": 329439.1, "main_trades": 1322}


def log(*m):
    print(time.strftime("[%H:%M:%S]"), *m, flush=True)


# =====================================================================================
# the hand-over times
# =====================================================================================
def handovers(page_path=PAGE, override=None):
    """{group: started_utc 'YYYY-MM-DD HH:MM'} from the live page (the forward books' start per group)."""
    out = {}
    try:
        with open(page_path, encoding="utf-8") as fh:
            page = json.load(fh)
        for g, v in ((page.get("shadows") or {}).get("markets") or {}).items():
            if isinstance(v, dict) and v.get("started_utc"):
                out[g] = str(v["started_utc"])[:16]
    except (OSError, ValueError) as e:
        log("page.json not readable (%r)" % (e,))
    out.update(override or {})
    return out


# =====================================================================================
# stage A: read-only copy of the store (rows that open before the hand-over), the odds, the books
# =====================================================================================
def ev_columns():
    from engine15 import shadows
    cols = ["shock", "tide", "atr1h", "atr15", "htf_bias", "release_soon", "sw_lo_15m", "sw_hi_15m", "sw_lo_1h",
            "sw_hi_1h", "reach_1h_med_pct", "reach_4h_med_pct"]
    for tf in shadows.PB_FIB_TFS:
        cols += ["fib_%s_dir" % tf, "fib_%s_broken" % tf, "fib_%s_r500_px" % tf, "fib_%s_entry_px" % tf]
    cols += ["ma_%s_%s_px" % (tf, m) for tf in shadows.PB_MA_TFS for m in shadows.PB_MAS]
    cols += list(shadows.TARGET_COLS)
    return list(dict.fromkeys(cols))


def quiet_window():
    """Wait until the engine's step is not rewriting its stores: a copy starts 4 to 13 minutes into a quarter hour."""
    while True:
        m = time.gmtime()
        q = (m.tm_min % 15) + m.tm_sec / 60.0
        if 4.0 <= q < 13.0:
            return
        log("waiting for the engine's step to finish (%.1f min into the quarter hour)" % q)
        time.sleep(30)


def snapshot(group, assets, cut_utc):
    """Rows whose bar opens before cut_utc, copied into memory (times, X float64, ready, the readings the books need)
    and the bars of the same rows. The store's maps are let go after; a copy taken while it changed is taken again."""
    from card_overlap import open_stores
    from engine15 import data, evcache
    want = ev_columns()
    cut = pd.Timestamp(cut_utc, tz="UTC")
    for attempt in range(8):
        quiet_window()
        stores, gm = open_stores(group, assets, log)
        try:
            t_ms = stores[assets[0]].times_ms()
            for a in assets[1:]:
                if not np.array_equal(stores[a].times_ms(), t_ms):
                    raise RuntimeError("timelines differ")
            times_full = pd.DatetimeIndex(pd.to_datetime(t_ms, unit="ms", utc=True))
            n = int(times_full.searchsorted(cut))
            X, ready, ev = {}, {}, {}
            for a in assets:
                X[a] = np.ascontiguousarray(np.asarray(stores[a].X()[:n]), dtype=np.float64)
                ready[a] = np.array(stores[a].ready()[:n], dtype=bool)
                fr = stores[a].frame(times_full)
                cols = [c for c in want if c in fr.columns]
                sub = fr[cols].iloc[:n]
                ev[a] = pd.DataFrame(dict((c, np.array(sub[c].to_numpy(), copy=True)) for c in cols), index=times_full[:n])
                del fr, sub
            features = list(stores[assets[0]].meta["features"])
            bars = {}
            for a in assets:                                     # the bar files, read in the same quiet window
                b = data.load(a)
                bars[a] = b[b.index < cut]
        except Exception as e:                                   # a file swapped under the read: try again later
            log("%s: read interrupted (%r); again in 60s" % (group, e))
            for st in stores.values():
                st._mm = {}
            gc.collect()
            time.sleep(60)
            continue
        for st in stores.values():
            st._mm = {}                                          # drop the read-only maps (never close(): it flushes)
        gc.collect()
        with open(os.path.join(evcache.CACHE_DIR, group, "group.json"), encoding="utf-8") as fh:
            gm2 = json.load(fh)
        if gm2.get("building") or gm2.get("sig") != gm.get("sig") or gm2.get("n", 0) < gm.get("n", 0) or \
                gm2.get("updated_utc") != gm.get("updated_utc"):
            log("%s: the store was written during the copy; again in 60s" % group)
            time.sleep(60)
            continue
        return {"times": times_full[:n], "n": n, "X": X, "ready": ready, "ev": ev, "bars": bars, "features": features,
                "store": {"sig": gm.get("sig"), "updated_utc": gm.get("updated_utc"), "n_store": gm.get("n")}}
    raise RuntimeError("%s: no stable copy of the store" % group)


def prep_group(group, snap):
    """The odds as leanprep.prepare_live forms them, walked from the engine's birth (as H36), on the copy."""
    from engine15 import evidence, labels, leanprep, model
    from engine15.config import voting_for
    t0 = time.time()
    assets = list(snap["X"])
    if snap["features"] != list(evidence.FEATURES):
        raise RuntimeError("%s: the store's feature list is not the engine's" % group)
    times, n = snap["times"], snap["n"]
    cfg = dict(CFG, assets=tuple(assets), voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    px, y, res = {}, {}, {}
    for a in assets:
        b = snap["bars"][a].reindex(times)
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        px[a] = dict((k, b[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * snap["ev"][a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    fits = os.path.join(FITS, group)
    assert os.path.abspath(fits).startswith(os.path.abspath(OUT))        # never the engine's fits folder
    X, ready = snap["X"], snap["ready"]
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth, min(floor, birth), n, fits)
    del models
    log("%s: voices walked from %s: %d refits (%d from the private cache), %.0fs" % (
        group, cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    lo = birth
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))
    odds = {}
    for a in assets:
        Xa = X[a][lo:n]
        speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                           for v in model.VOICE_NAMES], axis=1)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        o = np.full((n, 3), np.nan)
        o[lo:] = model.mix(probs[a].arr, w)
        odds[a] = o
        probs[a] = None
        del speaks, w
    del probs, trust
    gc.collect()
    log("%s: trust and odds done (%.0fs)" % (group, time.time() - t0))
    return {"cfg": cfg, "assets": assets, "times": times, "ev": snap["ev"], "px": px, "odds": odds, "birth_idx": birth}


def _utc(ms):
    return str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def trade_rows(a, group, tr, b, prep, n, to_utc, fee):
    """The book's closed trades as rows of TRADE_FIELDS, plus the trade still open at the hand-over (closed at the
    last close, less the exit fee). -> (rows, final equity)"""
    rows = []
    for t in tr.itertuples(index=False):
        rows.append({"market": a, "group": group, "side": "LONG" if int(t.side) > 0 else "SHORT",
                     "time_in": _utc(t.t_in_ms), "time_out": _utc(t.t_out_ms), "entry": float(t.p_in),
                     "exit": float(t.p_out), "stop": None if t.stop0 != t.stop0 else float(t.stop0),
                     "why_in": str(t.why_in), "why_out": str(t.why_out), "pnl_pct": float(t.pnl_pct),
                     "pnl_usd": float(t.pnl_usd), "r": None if t.r_mult != t.r_mult else float(t.r_mult),
                     "fees_usd": float(t.fees_usd), "equity_after": float(t.equity), "qty": float(t.qty), "at_handover": 0})
    st = b["state"]
    eq = float(st["eq"])
    if st.get("pos"):
        pos, qty, entry = int(st["pos"]), float(st["qty"]), float(st["entry"])
        c = float(prep["px"][a]["close"][n - 1])
        gross, fees = qty * pos * (c - entry), fee * qty * (entry + c)
        pnl = gross - fees
        eq += pnl
        s0 = st.get("stop0")
        risk = qty * abs(entry - s0) if s0 is not None else None
        rows.append({"market": a, "group": group, "side": "LONG" if pos > 0 else "SHORT",
                     "time_in": _utc(st["t_in_ms"]) if st.get("t_in_ms") is not None else None, "time_out": to_utc,
                     "entry": entry, "exit": c, "stop": s0, "why_in": str(st.get("why_in")), "why_out": "HANDOVER",
                     "pnl_pct": pnl / (qty * entry) * 100.0, "pnl_usd": pnl, "r": pnl / risk if risk else None,
                     "fees_usd": fees, "equity_after": eq, "qty": qty, "at_handover": 1})
    return rows, eq


def run_group(group, to_utc):
    from engine15 import shadows
    t0 = time.time()
    assets = list(dict(CFG["universes"])[group])
    snap = snapshot(group, assets, to_utc)
    log("%s: %d rows opening before %s copied (%s .. %s), %d readings, store %s.. (%.0fs)" % (
        group, snap["n"], to_utc, str(snap["times"][0])[:16], str(snap["times"][-1])[:16], len(snap["features"]),
        str(snap["store"]["sig"])[:10], time.time() - t0))
    prep = prep_group(group, snap)
    times, n = prep["times"], len(prep["times"])
    out = {"group": group, "to_utc": to_utc, "store": snap["store"], "n_rows": n, "version": CFG["version"],
           "assets": {}, "curves": {}}
    rows = {BOOK: [], BASE: []}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        fee = shadows.asset_cfg(a, prep["cfg"])["cost_side"]
        info = {"from_utc": str(times[lo])[:16], "last_bar_utc": str(times[n - 1])[:16], "fee_side": fee}
        for name in (BOOK, BASE):
            b = shadows.run_challenger(name, prep, a, lo, n, aux=aux)
            r, eq_end = trade_rows(a, group, b["trades"], b, prep, n, to_utc, fee)
            rows[name] += r
            e = pd.Series(b["equity"][lo:n], index=times[lo:n]).ffill()
            d = e.resample("1D").last().ffill()
            d.iloc[-1] = eq_end                                  # the hand-over close, after its exit fee
            curve = np.concatenate([[START], b["equity"][lo:n][np.isfinite(b["equity"][lo:n])], [eq_end]])
            peak = np.maximum.accumulate(curve)
            info[name] = {"trades": len(r), "equity_end": round(eq_end, 2),
                          "max_dd_pct": round(float((curve / peak - 1).min()) * 100, 2),
                          "max_dd_usd": round(float((curve - peak).min()), 2),
                          "open_at_handover": {1: "LONG", -1: "SHORT"}.get(int(b["state"]["pos"]), "FLAT")}
            out["curves"].setdefault(name, {})[a] = {"t": [str(x)[:10] for x in d.index],
                                                     "eq": [round(float(x), 2) for x in d.values]}
        out["assets"][a] = info
        log("%s %s: %s .. %s, b_trail %d trades -> $%.0f, main %d trades -> $%.0f (%.0fs)" % (
            group, a, info["from_utc"], info["last_bar_utc"], info[BOOK]["trades"], info[BOOK]["equity_end"],
            info[BASE]["trades"], info[BASE]["equity_end"], time.time() - t0))
    del prep, snap
    gc.collect()
    os.makedirs(PARTS, exist_ok=True)
    pd.DataFrame(rows[BOOK], columns=TRADE_FIELDS).to_csv(os.path.join(PARTS, "trades_%s.csv" % group), index=False)
    pd.DataFrame(rows[BASE], columns=TRADE_FIELDS).to_csv(os.path.join(PARTS, "main_%s.csv" % group), index=False)
    out["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(PARTS, "group_%s.json" % group), "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    log("%s done in %.0fs" % (group, time.time() - t0))
    return out


# =====================================================================================
# stage B: the report (pure functions of the parts; tested on synthetic numbers by hand)
# =====================================================================================
def _r(v, d=2):
    return None if v is None or v != v else round(float(v), d)


def book_stats(tr):
    """trades, won %, net $, fees, best / worst trade of a frame of TRADE_FIELDS rows."""
    if not len(tr):
        return {"trades": 0, "won_pct": None, "net_usd": 0.0, "fees_usd": 0.0, "best_usd": None, "worst_usd": None}
    return {"trades": int(len(tr)), "won_pct": _r(100.0 * (tr.pnl_usd > 0).mean(), 1), "net_usd": _r(tr.pnl_usd.sum()),
            "fees_usd": _r(tr.fees_usd.sum()), "best_usd": _r(tr.pnl_usd.max()), "worst_usd": _r(tr.pnl_usd.min())}


def pooled_curve(curves, markets):
    """The markets' daily equity summed (a market not yet trading counts at $10,000)."""
    frame = pd.concat(dict((a, pd.Series(curves[a]["eq"], index=pd.to_datetime(curves[a]["t"]))) for a in markets),
                      axis=1).sort_index().ffill().fillna(START)
    return frame.sum(axis=1)


def periods(tr, total, freq):
    """Per calendar year ("Y") or month ("M"): trades and net $ by exit time, the pooled equity at the period's end."""
    key = "year" if freq == "Y" else "month"
    cut = 4 if freq == "Y" else 7
    ends = total.groupby(total.index.strftime("%Y" if freq == "Y" else "%Y-%m")).last()
    out = []
    by = tr.groupby(tr.time_out.str[:cut]) if len(tr) else None
    for p, eq in ends.items():
        g = by.get_group(p) if by is not None and p in by.groups else tr.iloc[0:0]
        row = {key: p, "trades": int(len(g)), "net_usd": _r(g.pnl_usd.sum()) if len(g) else 0.0,
               "equity_end": _r(eq)}
        if freq == "Y":
            row["won_pct"] = _r(100.0 * (g.pnl_usd > 0).mean(), 1) if len(g) else None
        out.append(row)
    return out


def book_summary(name, tr, groups):
    markets = [a for g in groups.values() for a in g["assets"]]
    curves = dict((a, c) for g in groups.values() for a, c in g["curves"][name].items())
    total = pooled_curve(curves, markets)
    peak = np.maximum.accumulate(np.concatenate([[START * len(markets)], total.values]))
    vals = np.concatenate([[START * len(markets)], total.values])
    per = {}
    for g in groups.values():
        for a, info in g["assets"].items():
            s = book_stats(tr[tr.market == a])
            s.update(equity_end=info[name]["equity_end"], max_dd_pct=info[name]["max_dd_pct"],
                     max_dd_usd=info[name]["max_dd_usd"], from_utc=info["from_utc"], to_utc=g["to_utc"],
                     open_at_handover=info[name]["open_at_handover"])
            per[a] = s
    tot = book_stats(tr)
    tot.update(markets=len(markets), start_usd=START * len(markets), equity_end=_r(total.iloc[-1]),
               max_dd_pct=_r(float((vals / peak - 1).min()) * 100), max_dd_usd=_r(float((vals - peak).min())),
               from_utc=min(p["from_utc"] for p in per.values()), to_utc=max(g["to_utc"] for g in groups.values()))
    return {"total": tot, "markets": per, "years": periods(tr, total, "Y"), "months": periods(tr, total, "M")}


def report():
    groups = {}
    for g in GROUP_ORDER:
        p = os.path.join(PARTS, "group_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                groups[g] = json.load(fh)
    missing = [g for g in GROUP_ORDER if g not in groups]
    if missing:
        raise SystemExit("groups not run yet: %s" % missing)
    tr = pd.concat([pd.read_csv(os.path.join(PARTS, "trades_%s.csv" % g)) for g in groups], ignore_index=True)
    mn = pd.concat([pd.read_csv(os.path.join(PARTS, "main_%s.csv" % g)) for g in groups], ignore_index=True)
    tr = tr.sort_values(["time_out", "market"], kind="mergesort").reset_index(drop=True)
    b, m = book_summary(BOOK, tr, groups), book_summary(BASE, mn, groups)
    summary = {
        "label": LABEL, "book": BOOK, "name": "B trail",
        "note": "History replay with today's engine, in-sample, not a test. Paper only. Each market's book starts at "
                "$10,000 and compounds. Trades are counted in the month and year they closed; equity_end is all "
                "markets' marked equity summed at the period's last daily close. A trade open at the hand-over is closed "
                "at that close less the exit fee (why_out HANDOVER).",
        "rule": "The main book's entries; once a trade is 1R in profit the stop trails the last confirmed 15-minute swing "
                "or 2 x ATR(14, 15m), whichever is tighter; it re-enters on its own clock.",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "version": CFG["version"],
        "from_utc": b["total"]["from_utc"], "to_utc": b["total"]["to_utc"],
        "handover_utc": dict((g, v["to_utc"]) for g, v in groups.items()),
        "store": dict((g, v["store"]) for g, v in groups.items()),
        "b_trail": b, "main": m,
        "vs_main_usd": _r(b["total"]["net_usd"] - m["total"]["net_usd"]),
        "h36_reference": H36}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "trades.csv.tmp"), "w", encoding="utf-8", newline="") as fh:
        fh.write("# B trail: %s. Paper only. Read with pandas.read_csv(path, comment='#')." % LABEL + "\n")
        tr.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")
    os.replace(os.path.join(OUT, "trades.csv.tmp"), os.path.join(OUT, "trades.csv"))
    with open(os.path.join(OUT, "summary.json.tmp"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, allow_nan=False)
    os.replace(os.path.join(OUT, "summary.json.tmp"), os.path.join(OUT, "summary.json"))
    for name, s in (("b_trail", b), ("main", m)):
        t = s["total"]
        log("%-8s %d trades, won %s%%, net $%+.0f, equity $%.0f, max DD %.1f%%" % (
            name, t["trades"], t["won_pct"], t["net_usd"], t["equity_end"], t["max_dd_pct"]))
        for a, x in s["markets"].items():
            log("   %-8s %5d trades  won %5s%%  net $%+10.0f  DD %6.1f%%  best $%s worst $%s" % (
                a, x["trades"], x["won_pct"], x["net_usd"], x["max_dd_pct"], x["best_usd"], x["worst_usd"]))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--handover", action="append", default=[], help="group=YYYY-MM-DD HH:MM (else from page.json)")
    ap.add_argument("--keep-fits", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    if args.report:
        report()
        return
    ho = handovers(override=dict(x.split("=", 1) for x in args.handover))
    todo = [args.group] if args.group else list(GROUP_ORDER)
    for g in todo:
        if g not in ho:
            raise SystemExit("%s: no hand-over time (page.json shadows.markets.%s.started_utc)" % (g, g))
    log("hand-over: %s; version %s" % (ho, CFG["version"]))
    for g in todo:
        run_group(g, ho[g])
        gc.collect()
    if not args.group:
        report()
        if not args.keep_fits:
            shutil.rmtree(FITS, ignore_errors=True)


if __name__ == "__main__":
    main()
