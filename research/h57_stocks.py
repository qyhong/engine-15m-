# -*- coding: utf-8 -*-
"""H57, stock stances on history (research/HYPOTHESES.md). PAPER ONLY. Research server.

    python research/h57_stocks.py spx                 the S&P model as it stood at each close (walk-forward, private)
    python research/h57_stocks.py stock TICKER ..     replay the stance of these tickers (needs spx + h57_data.py files)
    python research/h57_stocks.py report              grade nothing new: measures, pass bar, report.md + results.json

The stance is engine15/stocks.py's, made with its own functions (readings, feature_vector, entry_trust,
stance_odds, decide), at every US-hours 15-minute close where the S&P 500 also has a close, with:
  * the stock's readings from a window that starts 60 days before the close's calendar month (the live store's
    situation: 60 days of 15-minute bars, daily bars before them), only that month's rows kept;
  * the market-wide cards and the release guard (ec_next) from the S&P 500 call's readings at the same close: the
    index group's evidence store, copied READ-ONLY by research/b_trail_history.snapshot (quiet window, version
    check, copy taken again if the store changed during it); nothing under data/ is written;
  * the S&P model as it stood at that close: the voices walked forward weekly from the engine's birth by
    leanprep.walk_forward_cached with the refits in a PRIVATE folder (research/out/h57_stocks/fits/, deleted after);
    the refit in force at the close; trust = leanprep.trust_tail with the index group's voting cards and the trust
    cap, as leanprep.prepare_live forms it (what the S&P call's journal entry records), renormalised by
    stocks.entry_trust;
  * grading: labels.triple_barrier on the stock's 15-minute bars, unit 1.5 x atr1h at the close, 26 bars.
"""
import gc
import json
import math
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, labels, model, stocks  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h57_stocks")
BARS = os.path.join(OUT, "bars")
FITS = os.path.join(OUT, "fits")
ROWS = os.path.join(OUT, "rows")
SPX_FILE = os.path.join(OUT, "spx_model.npz")
SEAL = "2025-11-11"
SEAL_MS = int(pd.Timestamp(SEAL, tz="UTC").timestamp() * 1000)
WINDOW_DAYS = 60
GROUP, INDEX = "index", "SPX"
FIVE = ("NVDA", "ARGX", "MU", "T", "DDOG")
BOOT = 2000


def log(*m):
    print(time.strftime("[%H:%M:%S]"), *m, flush=True)


def index_cfg():
    """The index group's config as leanprep.prepare_live / stocks.index_cfg use it."""
    cfg = dict(CFG, assets=(INDEX,), voting=voting_for(GROUP))
    cfg["horizon"] = stocks.HORIZON
    return cfg


def market_features():
    """The features copied from the S&P call: the market-wide voices' (ec_next is one of macro's)."""
    _, _, market = stocks._voice_sets()
    f = []
    for v in market:
        f += [x for x in model.VOICES[v][1] if x not in f]
    if "ec_next" not in f:
        f.append("ec_next")
    return f


# =====================================================================================
# the S&P model, walk-forward (pure given the arrays: tested for no look-ahead)
# =====================================================================================
def walk_model(X, ready, y, res, cfg, birth, floor, n, fits_dir):
    """The index group's refits and trust as leanprep.prepare_live forms them, on arrays of rows 0 .. n-1.
    -> (refit starts (k,), {voice: (k, ...) W stack}, trust (n - birth, V) voting-masked and capped)."""
    from engine15 import leanprep
    probs, models, _rep = leanprep.walk_forward_cached(X, ready, y, cfg, birth, min(floor, birth), n, fits_dir)
    trust = leanprep.trust_tail(probs, y, res, cfg, birth, n)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))
    starts = np.array([s for s, _, _ in models], dtype=np.int64)
    W = dict((v, np.stack([w[v] for _, w, _ in models])) if models else (v, None) for v in model.VOICE_NAMES)
    return starts, W, trust


def refit_at(i, starts, every):
    """The refit in force at row i: the walk's chunk s .. s+every-1 holding i, or -1 (no model there)."""
    k = int(np.searchsorted(starts, i, side="right")) - 1
    if k < 0 or i >= starts[k] + every:
        return -1
    return k


def spx_stage():
    import b_trail_history as bth
    t0 = time.time()
    snap = bth.snapshot(GROUP, [INDEX], SEAL)
    log("index: %d rows before %s copied (%s .. %s), store %s.." % (snap["n"], SEAL, str(snap["times"][0])[:16],
                                                                  str(snap["times"][-1])[:16], str(snap["store"]["sig"])[:10]))
    from engine15 import evidence
    if snap["features"] != list(evidence.FEATURES):
        raise RuntimeError("the store's feature list is not the engine's")
    cfg = index_cfg()
    times, n = snap["times"], snap["n"]
    b = snap["bars"][INDEX].reindex(times)
    if b["close"].isna().any():
        raise RuntimeError("%d index sessions have no bar" % int(b["close"].isna().sum()))
    unit = (cfg["barrier_atr"] * snap["ev"][INDEX]["atr1h"]).values
    y, res = labels.triple_barrier(b["open"].values.astype(float), b["high"].values.astype(float),
                                   b["low"].values.astype(float), unit, cfg["horizon"])
    birth = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    fits = os.path.join(FITS, GROUP)
    assert os.path.abspath(fits).startswith(os.path.abspath(OUT))            # never the engine's fits folder
    X, ready = {INDEX: snap["X"][INDEX]}, {INDEX: snap["ready"][INDEX]}
    starts, W, trust = walk_model(X, ready, {INDEX: y}, {INDEX: res}, cfg, birth, floor, n, fits)
    feats = market_features()
    pos = [evidence.FEATURES.index(f) for f in feats]
    mk = np.ascontiguousarray(X[INDEX][:, pos])
    out = {"times_ms": data.to_ms(times), "mk": mk, "mk_names": np.array(feats), "trust": trust,
           "birth": np.array(birth), "starts": starts, "every": np.array(cfg["refit_every"]),
           "ready": ready[INDEX], "voices": np.array(model.VOICE_NAMES), "store_sig": np.array(str(snap["store"]["sig"])),
           "store_updated": np.array(str(snap["store"]["updated_utc"]))}
    for v in model.VOICE_NAMES:
        out["W__" + v] = W[v]
    os.makedirs(OUT, exist_ok=True)
    np.savez(SPX_FILE + ".tmp.npz", **out)
    os.replace(SPX_FILE + ".tmp.npz", SPX_FILE)
    shutil.rmtree(FITS, ignore_errors=True)                                  # the private refits are temporary
    log("index model: %d refits (first %s), trust rows %d, saved (%.0fs)" % (
        len(starts), str(times[starts[0]])[:16] if len(starts) else None, len(trust), time.time() - t0))


def load_spx():
    with np.load(SPX_FILE) as z:
        d = dict((k, z[k]) for k in z.files)
    d["W"] = dict((v, d.pop("W__" + v)) for v in model.VOICE_NAMES)
    d["pos"] = dict((int(t), i) for i, t in enumerate(d["times_ms"]))
    return d


class SpxAt:
    """What the S&P call had at one close: (trust on model.VOICE_NAMES, {voice: W}, {feature: value}) or None."""

    def __init__(self, spx):
        self.s = spx
        self.names = [str(x) for x in spx["mk_names"]]
        self.every = int(spx["every"])
        self.birth = int(spx["birth"])

    def __call__(self, open_ms):
        i = self.s["pos"].get(int(open_ms))
        if i is None or i < self.birth or not bool(self.s["ready"][i]):
            return None
        k = refit_at(i, self.s["starts"], self.every)
        if k < 0:
            return None
        trust = self.s["trust"][i - self.birth]
        W = dict((v, self.s["W"][v][k]) for v in model.VOICE_NAMES)
        feats = dict(zip(self.names, (float(x) for x in self.s["mk"][i])))
        return trust, W, feats


# =====================================================================================
# the stock: readings by month window, stance per close, grades
# =====================================================================================
def month_windows(index, window_days=WINDOW_DAYS):
    """[(month start, month end, window start)] over the months that hold bars of `index` (UTC)."""
    if not len(index):
        return []
    m0 = pd.Timestamp(index[0].tz_convert("UTC").strftime("%Y-%m-01"), tz="UTC")
    out = []
    m = m0
    while m <= index[-1]:
        nxt = (m + pd.offsets.MonthBegin(1))
        out.append((m, nxt, m - pd.Timedelta(days=window_days)))
        m = nxt
    return out


def month_readings(b15, daily, ticker, ms, me, ws):
    """stocks.readings on the window [ws, me) with the daily bars before it; rows of [ms, me) kept."""
    win = b15[(b15.index >= ws) & (b15.index < me)]
    if not (win.index >= ms).any():
        return None
    d = daily[daily.index < win.index[0].normalize()] if daily is not None and len(daily) else daily
    ev = stocks.readings(win, d, ticker)
    return ev[ev.index >= ms]


def stance_row(row, at, cfg):
    """stocks._stance's decision for one readings row and what the S&P call had at that close (`at`), or None
    (required readings missing, or no S&P model). -> dict (side, score, p_up, p_down, p_neither, why, unit)."""
    missing = [c for c in stocks.REQUIRED if not (isinstance(row.get(c), str) or stocks._num(row.get(c)) is not None)]
    if missing or at is None:
        return None
    trust_row, W, feats = at
    entry = {"voices": [{"voice": v, "trust": float(trust_row[k])} for k, v in enumerate(model.VOICE_NAMES)],
             "data": feats}
    trust = stocks.entry_trust(entry)
    x = stocks.feature_vector(row, entry["data"])
    odds, _w, _p = stocks.stance_odds(x, trust, W)
    score = float(odds[labels.UP] - odds[labels.DOWN]) * 100.0
    ec = stocks._num(feats.get("ec_next"))
    guard = ec is not None and ec >= 1.0 - 1.0 / 24.0 - 1e-9
    shock = bool(row.get("shock")) if row.get("shock") == row.get("shock") else False
    tide, bias = stocks._num(row.get("tide")), stocks._num(row.get("htf_bias"))
    side, why = stocks.decide(odds, shock, tide, bias, guard, cfg)
    unit = stocks._num(row.get("atr1h"))
    return {"side": side, "score": score, "p_up": float(odds[labels.UP]), "p_down": float(odds[labels.DOWN]),
            "p_neither": float(odds[labels.NEITHER]), "why": why,
            "unit": None if unit is None else cfg["barrier_atr"] * unit}


def stances(b15, daily, ticker, spx_at, cfg, log=None):
    """Every close's stance (the rows where one is made). -> DataFrame indexed by bar open time."""
    say = log or (lambda *_: None)
    rows = []
    for ms, me, ws in month_windows(b15.index):
        ev = month_readings(b15, daily, ticker, ms, me, ws)
        if ev is None or not len(ev):
            continue
        t_ms = data.to_ms(ev.index)
        made = 0
        for j in range(len(ev)):
            at = spx_at(t_ms[j])
            if at is None:
                continue
            st = stance_row(ev.iloc[j], at, cfg)
            if st is None:
                continue
            st["bar_ms"] = int(t_ms[j])
            rows.append(st)
            made += 1
        say("%s %s: %d closes, %d stances" % (ticker, str(ms)[:7], len(ev), made))
    if not rows:
        return pd.DataFrame(columns=["bar_ms", "side", "score", "p_up", "p_down", "p_neither", "why", "unit"])
    return pd.DataFrame(rows)


def grade(b15, st, horizon=stocks.HORIZON):
    """labels.triple_barrier on the stock's bars with each stance row's unit. -> st with y, res, i (bar row)."""
    st = st.copy()
    ms = data.to_ms(b15.index)
    i = np.searchsorted(ms, st["bar_ms"].values.astype(np.int64))
    unit = np.full(len(b15), np.nan)
    unit[i] = st["unit"].astype(float).values
    y, res = labels.triple_barrier(b15["open"].values.astype(float), b15["high"].values.astype(float),
                                   b15["low"].values.astype(float), unit, horizon)
    st["i"] = i
    st["y"] = y[i]
    st["res"] = res[i]
    return st


def stock_stage(ticker):
    t0 = time.time()
    spx = load_spx()
    at = SpxAt(spx)
    b15 = data.load("x", path=os.path.join(BARS, "%s_15m.csv" % ticker))
    daily = data.load("x", path=os.path.join(BARS, "%s_1d.csv" % ticker))
    b15 = b15[data.to_ms(b15.index) < SEAL_MS]                               # the seal, again, at load
    daily = daily[data.to_ms(daily.index) < SEAL_MS]
    first = int(spx["times_ms"][int(spx["starts"][0])]) if len(spx["starts"]) else SEAL_MS
    m0 = pd.Timestamp(pd.Timestamp(first, unit="ms", tz="UTC").strftime("%Y-%m-01"), tz="UTC")
    # months before the index model's first refit have no stance: start the windows there (the readings of a month
    # depend only on its own window, so nothing changes for the months kept)
    sub = b15[b15.index >= m0 - pd.Timedelta(days=WINDOW_DAYS)]
    cfg = stocks.index_cfg()
    st = stances(sub, daily, ticker, at, cfg, log=log)
    st = st[st["bar_ms"] >= int(m0.timestamp() * 1000)] if len(st) else st
    st = grade(b15, st)
    st["ticker"] = ticker
    os.makedirs(ROWS, exist_ok=True)
    st.to_csv(os.path.join(ROWS, "%s.csv" % ticker), index=False)
    log("%s: %d stances (%s), %.0fs" % (ticker, len(st), st["side"].value_counts().to_dict(), time.time() - t0))


# =====================================================================================
# the measures (pure; tested)
# =====================================================================================
def wilson(k, n, z=1.959964):
    if n <= 0:
        return None, None
    p = k / float(n)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def non_overlap(i, res):
    """Calls in time order (bar rows i, sessions until known res): a call is taken when the previous taken call's
    grade was known by its close (i >= i_prev + res_prev). -> boolean mask."""
    keep = np.zeros(len(i), bool)
    free = -1
    for k in np.argsort(i, kind="stable"):
        if i[k] >= free:
            keep[k] = True
            free = i[k] + max(int(res[k]), 1)
    return keep


def hits(df):
    g = df[df["y"].isin([labels.UP, labels.DOWN])]
    right = ((g["side"] == "LONG") & (g["y"] == labels.UP)) | ((g["side"] == "SHORT") & (g["y"] == labels.DOWN))
    return int(right.sum()), int(len(g))


def hit_block(calls):
    """calls: LONG/SHORT rows with y known (NEITHER included) and the 'nov' mask column."""
    k_all, n_all = hits(calls)
    nv = calls[calls["nov"]]
    k, n = hits(nv)
    lo, hi = wilson(k, n)
    return {"calls": int(len(calls)), "graded_all": n_all, "hit_all": None if not n_all else k_all / n_all,
            "neither_all": int((calls["y"] == labels.NEITHER).sum()),
            "nov_calls": int(len(nv)), "nov_graded": n, "nov_hits": k, "nov_hit": None if not n else k / n,
            "nov_lo": lo, "nov_hi": hi}


def prob_block(rows, base_of):
    """Two-way p = p_up / (p_up + p_down) on rows graded UP/DOWN vs the ticker's own UP share (base_of: {ticker: b})."""
    g = rows[rows["y"].isin([labels.UP, labels.DOWN])]
    if not len(g):
        return {"rows": 0}
    o = (g["y"] == labels.UP).astype(float).values
    p = (g["p_up"] / (g["p_up"] + g["p_down"])).astype(float).values
    b = g["ticker"].map(base_of).astype(float).values
    eps = 1e-6
    br_m, br_b = float(((p - o) ** 2).sum()), float(((b - o) ** 2).sum())
    pc, bc = np.clip(p, eps, 1 - eps), np.clip(b, eps, 1 - eps)
    ll_m = float(-(o * np.log(pc) + (1 - o) * np.log(1 - pc)).sum())
    ll_b = float(-(o * np.log(bc) + (1 - o) * np.log(1 - bc)).sum())
    n = len(g)
    return {"rows": int(n), "up_share": float(o.mean()), "brier": br_m / n, "brier_base": br_b / n,
            "brier_skill": 1 - br_m / br_b if br_b > 0 else None, "logloss": ll_m / n, "logloss_base": ll_b / n,
            "logloss_skill": 1 - ll_m / ll_b if ll_b > 0 else None}


def day_bootstrap(nv, reps=BOOT, seed=57):
    """Hit rate of non-overlapping graded calls, trading days resampled with replacement: 2.5% and 97.5%."""
    g = nv[nv["y"].isin([labels.UP, labels.DOWN])].copy()
    if not len(g):
        return None, None
    g["right"] = (((g["side"] == "LONG") & (g["y"] == labels.UP)) | ((g["side"] == "SHORT") & (g["y"] == labels.DOWN)))
    g["day"] = pd.to_datetime(g["bar_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    agg = g.groupby("day")["right"].agg(["sum", "count"])
    k, n = agg["sum"].values.astype(float), agg["count"].values.astype(float)
    rng = np.random.RandomState(seed)
    out = np.empty(reps)
    for r in range(reps):
        pick = rng.randint(0, len(k), len(k))
        out[r] = k[pick].sum() / n[pick].sum()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def measure(all_rows, tickers):
    """all_rows: every ticker's stance rows (with y, res, i, ticker). -> results dict (pure)."""
    rows = all_rows[all_rows["y"] >= 0].copy()                    # grade known (UNKNOWN at the seal's edge dropped)
    rows["nov"] = False
    calls = rows[rows["side"].isin(["LONG", "SHORT"])].copy()
    for t in tickers:
        m = calls["ticker"] == t
        if m.any():
            calls.loc[m, "nov"] = non_overlap(calls.loc[m, "i"].values, calls.loc[m, "res"].values)
    graded_calls = calls[calls["y"].isin([labels.UP, labels.DOWN])]
    split_ms = int(np.median(graded_calls["bar_ms"].values)) if len(graded_calls) else None
    halves = {"full": lambda d: d,
              "first": lambda d: d[d["bar_ms"] < split_ms],
              "second": lambda d: d[d["bar_ms"] >= split_ms]}
    res = {"split_utc": None if split_ms is None else str(pd.Timestamp(split_ms, unit="ms", tz="UTC"))[:16],
           "per_ticker": {}, "pooled": {}, "five": {}, "ten": {}}
    for h, f in halves.items():
        r_h = f(rows)
        base = dict((t, float((r_h[(r_h["ticker"] == t) & r_h["y"].isin([1, 2])]["y"] == labels.UP).mean()))
                    for t in tickers if ((r_h["ticker"] == t) & r_h["y"].isin([1, 2])).any())
        c_h = f(calls)
        for t in tickers:
            ct, rt = c_h[c_h["ticker"] == t], r_h[r_h["ticker"] == t]
            d = res["per_ticker"].setdefault(t, {})
            d[h] = hit_block(ct)
            d[h]["prob"] = prob_block(rt, base)
            d[h]["sides"] = rt["side"].value_counts().to_dict()
            d[h]["rows"] = int(len(rt))
            if h == "full" and len(rt):
                d[h]["from_utc"] = str(pd.Timestamp(int(rt["bar_ms"].min()), unit="ms", tz="UTC"))[:16]
                d[h]["to_utc"] = str(pd.Timestamp(int(rt["bar_ms"].max()), unit="ms", tz="UTC"))[:16]
        for name, sel in (("pooled", list(tickers)), ("five", [t for t in tickers if t in FIVE]),
                          ("ten", [t for t in tickers if t not in FIVE])):
            ct, rt = c_h[c_h["ticker"].isin(sel)], r_h[r_h["ticker"].isin(sel)]
            blk = hit_block(ct)
            blk["prob"] = prob_block(rt, base)
            blk["boot_lo"], blk["boot_hi"] = day_bootstrap(ct[ct["nov"]])
            blk["tickers"] = sel
            res[name][h] = blk
    above = [t for t in tickers if (res["per_ticker"][t]["full"]["nov_hit"] or 0) > 0.5]
    need = int(math.ceil(0.4 * len(tickers)))
    c1 = all((res["pooled"][h]["nov_hit"] or 0) > 0.5 and (res["pooled"][h]["nov_lo"] or 0) > 0.5 for h in ("first", "second"))
    c2 = len(above) >= need
    res["pass"] = {"pooled_halves_above_50_with_interval": bool(c1), "tickers_above_50": above,
                   "tickers_needed": need, "tickers_tested": len(tickers), "enough_tickers": bool(c2),
                   "PASS": bool(c1 and c2)}
    return res


# =====================================================================================
# report
# =====================================================================================
def _pct(x, d=1):
    return "-" if x is None or x != x else ("%.*f%%" % (d, 100.0 * x))


def _f(x, d=4):
    return "-" if x is None or x != x else ("%.*f" % (d, x))


def report_stage():
    with open(os.path.join(OUT, "probe.json"), encoding="utf-8") as fh:
        probe = json.load(fh)
    dj = {}
    if os.path.exists(os.path.join(OUT, "data.json")):
        with open(os.path.join(OUT, "data.json"), encoding="utf-8") as fh:
            dj = json.load(fh)
    tickers = [t for t in probe["five_tested"] + probe["ten"] if os.path.exists(os.path.join(ROWS, "%s.csv" % t))]
    missing = [t for t in probe["five_tested"] + probe["ten"] if t not in tickers]
    if missing:
        raise RuntimeError("no stance rows for %s" % missing)
    all_rows = pd.concat([pd.read_csv(os.path.join(ROWS, "%s.csv" % t)) for t in tickers], ignore_index=True)
    res = measure(all_rows, tickers)
    res["population"] = {"five_tested": probe["five_tested"], "five_not_testable": probe["five_not_testable"],
                         "ten": probe["ten"], "ten_replaced": probe["replaced"], "dukascopy_first_month": probe["first_month"]}
    res["data"] = dj
    with np.load(SPX_FILE) as z:
        res["index_store"] = {"sig": str(z["store_sig"]), "updated_utc": str(z["store_updated"]),
                              "refits": int(len(z["starts"])),
                              "first_refit_utc": str(pd.Timestamp(int(z["times_ms"][int(z["starts"][0])]), unit="ms", tz="UTC"))[:16]}
    res["registered"] = "research/HYPOTHESES.md H57 (19 Nov 2026, 09:58 UTC)"
    res["version"] = CFG.get("version")
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    L = []
    P = res["pass"]
    L.append("# H57: stock stances on history")
    L.append("")
    L.append("Registered in research/HYPOTHESES.md (H57, 19 Nov 2026 09:58 UTC) before any H57 code or number. "
             "Engine %s. PAPER ONLY. Development data only (rows before %s)." % (res["version"], SEAL))
    L.append("")
    L.append("**Verdict: %s.** Pooled non-overlapping hit rate above 50%% with the 95%% interval above 50%% in both "
             "halves: %s. Tickers above 50%% (full period, non-overlapping): %d of %d (needed %d)." % (
                 "PASS" if P["PASS"] else "NO PASS", "yes" if P["pooled_halves_above_50_with_interval"] else "no",
                 len(P["tickers_above_50"]), P["tickers_tested"], P["tickers_needed"]))
    L.append("")
    L.append("## Population and data")
    L.append("")
    L.append("- Five tested: %s; not testable (no Dukascopy CFD): %s." % (", ".join(probe["five_tested"]),
                                                                         ", ".join(probe["five_not_testable"]) or "none"))
    L.append("- Ten (largest S&P 500 companies, NVDA counted in the five): %s%s." % (
        ", ".join(probe["ten"]), ("; replaced (no usable CFD): " + ", ".join(probe["replaced"])) if probe["replaced"] else ""))
    L.append("- Index model: %d weekly refits walked forward from the engine's birth, first in force %s (store %s.., copied %s)." % (
        res["index_store"]["refits"], res["index_store"]["first_refit_utc"], res["index_store"]["sig"][:10],
        res["index_store"]["updated_utc"]))
    L.append("")
    L.append("| ticker | Dukascopy from | 15m bars | stance closes | first .. last | splits |")
    L.append("|---|---|---|---|---|---|")
    for t in tickers:
        d = dj.get(t, {})
        pt = res["per_ticker"][t]["full"]
        sp = "; ".join("%s x%g (%s)" % (s["date"], s["ratio"], "source adjusted" if s["source_already_adjusted"] else "adjusted here")
                       for s in d.get("splits", [])) or "-"
        L.append("| %s | %s | %s | %d | %s .. %s | %s |" % (t, d.get("first_month", "-"), d.get("bars15", "-"), pt["rows"],
                                                           pt.get("from_utc", "-"), pt.get("to_utc", "-"), sp))
    L.append("")
    L.append("## Hit rate of LONG / SHORT calls (NEITHER not counted)")
    L.append("")
    L.append("Halves split at %s UTC (median date of the pooled graded calls). nov = non-overlapping calls; interval = "
             "Wilson 95%% on them. 'all' = every call, overlapping, no interval." % res["split_utc"])
    L.append("")
    L.append("| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |")
    L.append("|---|---|---|---|---|---|---|---|---|")

    def line(name, d):
        f, a, b = d["full"], d["first"], d["second"]
        sides = f.get("sides") or {}
        L.append("| %s | %d | %s | %d | %s | %s .. %s | %s (%d) | %s (%d) | %s |" % (
            name, f["calls"], _pct(f["hit_all"]), f["nov_graded"], _pct(f["nov_hit"]), _pct(f["nov_lo"]), _pct(f["nov_hi"]),
            _pct(a["nov_hit"]), a["nov_graded"], _pct(b["nov_hit"]), b["nov_graded"],
            "%s / %s / %s" % (sides.get("LONG", 0), sides.get("SHORT", 0), sides.get("FLAT", 0)) if sides else "-"))
    for t in tickers:
        line(t, res["per_ticker"][t])
    for name in ("five", "ten", "pooled"):
        line("**%s**" % name, res[name])
    L.append("")
    L.append("Day-block bootstrap of the pooled non-overlapping hit rate (descriptive; calls of different stocks at the same "
             "time are correlated): full %s .. %s, first %s .. %s, second %s .. %s." % tuple(
                 _pct(res["pooled"][h][k]) for h in ("full", "first", "second") for k in ("boot_lo", "boot_hi")))
    L.append("")
    L.append("## Probabilities: Brier and log-loss of P(up) / (P(up) + P(down)) against the ticker's own UP share")
    L.append("")
    L.append("Every stance row (LONG, SHORT, FLAT) graded UP or DOWN, overlapping; base rate = the ticker's UP share in the "
             "same half (in-sample, favours the base). Skill > 0 = better than the base rate.")
    L.append("")
    L.append("| ticker | rows | UP share | Brier | base | skill | log-loss | base | skill | skill first | skill second |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")

    def pline(name, d):
        p = d["full"]["prob"]
        if not p.get("rows"):
            L.append("| %s | 0 | | | | | | | | | |" % name)
            return
        L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, p["rows"], _pct(p["up_share"]), _f(p["brier"]), _f(p["brier_base"]), _f(p["brier_skill"]),
            _f(p["logloss"]), _f(p["logloss_base"]), _f(p["logloss_skill"]),
            _f(d["first"]["prob"].get("brier_skill")), _f(d["second"]["prob"].get("brier_skill"))))
    for t in tickers:
        pline(t, res["per_ticker"][t])
    for name in ("five", "ten", "pooled"):
        pline("**%s**" % name, res[name])
    L.append("")
    L.append("## Pass table (fixed in the registration)")
    L.append("")
    L.append("| condition | required | result | met |")
    L.append("|---|---|---|---|")
    for h in ("first", "second"):
        p = res["pooled"][h]
        L.append("| pooled nov hit, %s half | > 50%% and 95%% lower bound > 50%% | %s (%s .. %s, n %d) | %s |" % (
            h, _pct(p["nov_hit"]), _pct(p["nov_lo"]), _pct(p["nov_hi"]), p["nov_graded"],
            "yes" if (p["nov_hit"] or 0) > 0.5 and (p["nov_lo"] or 0) > 0.5 else "no"))
    L.append("| tickers with full-period nov hit > 50%% | >= %d of %d | %d (%s) | %s |" % (
        P["tickers_needed"], P["tickers_tested"], len(P["tickers_above_50"]), ", ".join(P["tickers_above_50"]) or "none",
        "yes" if P["enough_tickers"] else "no"))
    L.append("| **H57** | both | | **%s** |" % ("PASS" if P["PASS"] else "NO PASS"))
    L.append("")
    L.append("## How it was made")
    L.append("")
    L.append("- Bars: Dukascopy BID minute candles of each stock CFD -> 15-minute cash-hours bars (research/h57_data.py); "
             "daily bars from the same bars (hourly candles before the minute data). CFD prices are not the exchange's "
             "prints (a quote-driven feed; minute volume is the CFD's), checked against Yahoo's daily closes (data.json).")
    L.append("- Stance: engine15/stocks.py's own functions at every cash-hours close where the S&P 500 has one, with the "
             "S&P model as it stood then (weekly refits walked forward on the index store's rows, trust and cap as "
             "leanprep.prepare_live forms them). Readings per calendar month from a window starting 60 days before it "
             "(the live store's situation), daily bars before the window.")
    L.append("- Grading: labels.triple_barrier on the stock's bars, 1.5 x atr1h, 26 bars; NEITHER not counted.")
    L.append("- Not a trading test: no costs, no positions; a stance's hit rate only.")
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    log("report written: %s" % ("PASS" if P["PASS"] else "NO PASS"))
    return res


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "report"
    if cmd == "spx":
        spx_stage()
    elif cmd == "stock":
        for t in argv[1:]:
            stock_stage(t)
            gc.collect()
    elif cmd == "report":
        report_stage()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
