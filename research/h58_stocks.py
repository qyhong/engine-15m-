# -*- coding: utf-8 -*-
"""H58, the stocks' own model on history (research/HYPOTHESES.md, registered 20 Nov 2026 02:50 UTC). PAPER ONLY.
Research server only. Nothing under engine15/ or data/ is written; data/ files are copied read-only once (prep).

    python research/h58_stocks.py prep                  copy the S&P bars and the megacap earnings file (read-only)
    python research/h58_stocks.py readings TICKER ..    the stock's readings, the two stock-only readings, grades
    python research/h58_stocks.py walk SET ..           SET = primary | e1 | loto_<TICKER>: the walk-forward model
    python research/h58_stocks.py report                measures, pass bar, report.md + results.json

The model (registration, "The model"): cards rated with research/rate_cards.py's own functions and voices fitted with
engine15/model.py's fit_softmax, both only on rows whose grade was known at the refit (per ticker: the 26th bar after the
row had opened by the refit session's open, the engine's t <= s - horizon), refits every 672 sessions of the 13 tickers'
common timeline from 2022-01-03; trust = model.trust_path's Hedge on the walked-forward voices' losses, masked to the
refit's voting voices and capped, then per row over the voices that speak (stocks.stance_odds's mix); side =
stocks.decide. H57's helpers (month_readings, measure, ...) are reused unchanged.
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

from engine15 import data, evidence, labels, model, stocks  # noqa: E402
from engine15.config import CFG  # noqa: E402
import h57_stocks as h57  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h58_stocks")
INP = os.path.join(OUT, "inputs")
READ = os.path.join(OUT, "readings")
SETS = os.path.join(OUT, "sets")
H57_OUT = h57.OUT
H57_BARS = h57.BARS
SEAL_MS = h57.SEAL_MS
TICKERS = ("NVDA", "MU", "T", "AAPL", "MSFT", "AMZN", "GOOGL", "AVGO", "META", "TSLA", "BRK.B", "JPM", "LLY")
FLOOR = pd.Timestamp("2020-12-01", tz="UTC")          # the first month with a full 60-day window of 15m bars
FIRST_REFIT = pd.Timestamp("2022-01-03", tz="UTC")
FLOOR_MS = int(FLOOR.timestamp() * 1000)
FIRST_REFIT_MS = int(FIRST_REFIT.timestamp() * 1000)
H = stocks.HORIZON                                    # 26
EVERY = int(CFG["refit_every"])                       # 672
STEP = int(CFG["train_step"])                         # 16
BAR_MS = int(CFG["bar_ms"])
DAY_MS = 86400000
RS_K = (("rs_1h", 4), ("rs_1d", 26), ("rs_5d", 130))
ERN_FEATS = ("ern_next_s", "ern_last_s")
NEW_VOICES = {"stk_rs": ("Strength against the S&P 500", [k for k, _ in RS_K]),
              "stk_ern": ("Own earnings date", list(ERN_FEATS))}


def log(*m):
    print(time.strftime("[%H:%M:%S]"), *m, flush=True)


def _own_market():
    _, own, market = stocks._voice_sets()
    return list(own), list(market)


def own_feats():
    own, _ = _own_market()
    f = []
    for v in own:
        f += [x for x in model.VOICES[v][1] if x not in f]
    return f


# =====================================================================================
# prep: read-only copies of the two data/ files used
# =====================================================================================
def prep():
    os.makedirs(INP, exist_ok=True)
    spx = data.load("x", path=os.path.join(ROOT, "data", "spx_15m.csv"))
    spx = spx[data.to_ms(spx.index) < SEAL_MS]
    data.save("x", spx, path=os.path.join(INP, "spx_15m.csv"))
    shutil.copyfile(os.path.join(ROOT, "data", "sources", "earnings_megacap.csv"), os.path.join(INP, "earnings_megacap.csv"))
    log("prep: S&P bars %d (%s .. %s), earnings file copied" % (len(spx), spx.index[0], spx.index[-1]))


# =====================================================================================
# the two stock-only readings (pure; tested for no look-ahead)
# =====================================================================================
def rel_strength(b15, spx15):
    """rs_k = clip(sum of the last k (stock log return - S&P log return) / (std of that over 672 bars x sqrt k), 3).
    A bar without an S&P bar at the same open time: no read (NaN) for every sum that holds it."""
    c = np.log(b15["close"].astype(float))
    s = np.log(spx15["close"].astype(float)).reindex(b15.index)
    d = c.diff() - s.diff()
    sig = d.rolling(672, min_periods=600).std()
    out = pd.DataFrame(index=b15.index)
    for name, k in RS_K:
        out[name] = (d.rolling(k, min_periods=k).sum() / (sig * np.sqrt(k))).clip(-3.0, 3.0)
    return out


def earnings_feats(open_ms, ticker, src_dir):
    """ern_next_s = clip(1 - days to the next KNOWN report / 7, 0, 1); ern_last_s = clip(1 - days since the last report
    / 5, 0, 1), at each close (open + 15 min). equity_events' release times and known-at rule. Not in the file: 0."""
    from engine15.sources import equity_events as ee
    n = len(open_ms)
    nxt, last = np.zeros(n), np.zeros(n)
    e = ee.events(src_dir)
    e = e[e["symbol"].astype(str).str.upper() == ticker]
    if not len(e):
        return nxt, last, False
    close = np.asarray(open_ms, dtype=np.int64) + BAR_MS
    rel, known, gone = e["release_ms"].values.astype(np.int64), e["known_ms"].values.astype(np.int64), e["gone"].values
    for r, k, g in zip(rel, known, gone):
        m = (close >= k) & (close < r) & (close < g)
        v = 1.0 - (r - close[m]) / (7.0 * DAY_MS)
        nxt[m] = np.maximum(nxt[m], np.clip(v, 0.0, 1.0))
        m2 = (close >= r) & (close < r + 5 * DAY_MS)
        v2 = 1.0 - (close[m2] - r) / (5.0 * DAY_MS)
        last[m2] = np.maximum(last[m2], np.clip(v2, 0.0, 1.0))
    return nxt, last, True


# =====================================================================================
# readings stage
# =====================================================================================
def readings_stage(ticker):
    t0 = time.time()
    spx = h57.load_spx()
    names = [str(x) for x in spx["mk_names"]]
    b15 = data.load("x", path=os.path.join(H57_BARS, "%s_15m.csv" % ticker))
    daily = data.load("x", path=os.path.join(H57_BARS, "%s_1d.csv" % ticker))
    b15 = b15[data.to_ms(b15.index) < SEAL_MS]                               # the seal, at load
    daily = daily[data.to_ms(daily.index) < SEAL_MS]
    spx15 = data.load("x", path=os.path.join(INP, "spx_15m.csv"))
    spx15 = spx15[data.to_ms(spx15.index) < SEAL_MS]
    OF = own_feats()
    parts = []
    for ms, me, ws in h57.month_windows(b15.index):
        if ms < FLOOR:
            continue
        ev = h57.month_readings(b15, daily, ticker, ms, me, ws)
        if ev is None or not len(ev):
            continue
        X = np.zeros((len(ev), len(OF)), dtype=np.float32)
        for j, f in enumerate(OF):
            if f in ev.columns:
                col = np.array(pd.to_numeric(ev[f], errors="coerce"), dtype=float, copy=True)
                col[~np.isfinite(col)] = 0.0
                X[:, j] = col
        req = np.ones(len(ev), bool)
        for c in stocks.REQUIRED:
            col = ev[c]
            if pd.api.types.is_numeric_dtype(col.dtype):
                req &= np.isfinite(col.astype(float).values)
            else:
                req &= col.notna().values
        sh = ev["shock"]
        shock = np.array([bool(v) if v == v and v is not None else False for v in sh.values])
        num = lambda c: pd.to_numeric(ev[c], errors="coerce").astype(float).values
        parts.append({"bar_ms": data.to_ms(ev.index).astype(np.int64), "X": X, "req": req, "shock": shock,
                      "tide": num("tide"), "bias": num("htf_bias"), "atr1h": num("atr1h")})
        log("%s %s: %d rows" % (ticker, str(ms)[:7], len(ev)))
    cat = dict((k, np.concatenate([p[k] for p in parts])) for k in parts[0])
    bar_ms = cat["bar_ms"]
    # market-wide readings and the guard: the S&P call's row at the same close
    pos = np.array([spx["pos"].get(int(t), -1) for t in bar_ms])
    has_index = pos >= 0
    MK = np.zeros((len(bar_ms), len(names)), dtype=np.float32)
    MK[has_index] = spx["mk"][pos[has_index]].astype(np.float32)
    MK[~np.isfinite(MK)] = 0.0
    # the two stock-only readings
    rs = rel_strength(b15, spx15).reindex(pd.DatetimeIndex(pd.to_datetime(bar_ms, unit="ms", utc=True)))
    NEW = np.zeros((len(bar_ms), len(RS_K) + len(ERN_FEATS)), dtype=np.float32)
    for j, (name, _) in enumerate(RS_K):
        v = np.array(rs[name], dtype=float, copy=True)
        v[~np.isfinite(v)] = 0.0
        NEW[:, j] = v
    en, el, in_file = earnings_feats(bar_ms, ticker, INP)
    NEW[:, len(RS_K)] = en
    NEW[:, len(RS_K) + 1] = el
    # grades on the stock's full bars (h57.grade's method), and when each grade is known
    fms = data.to_ms(b15.index).astype(np.int64)
    i = np.searchsorted(fms, bar_ms)
    assert (fms[i] == bar_ms).all()
    unit = np.full(len(b15), np.nan)
    unit[i] = CFG["barrier_atr"] * cat["atr1h"]
    y, res = labels.triple_barrier(b15["open"].values.astype(float), b15["high"].values.astype(float),
                                   b15["low"].values.astype(float), unit, H)
    big = np.iinfo(np.int64).max
    hz = np.where(i + H < len(fms), fms[np.minimum(i + H, len(fms) - 1)], big)            # open of the 26th bar after
    yy, rr = y[i].astype(np.int64), res[i].astype(np.int64)
    arr = np.where((yy > 0) & (i + rr < len(fms)), fms[np.minimum(i + np.maximum(rr, 0), len(fms) - 1)], big)
    os.makedirs(READ, exist_ok=True)
    np.savez_compressed(os.path.join(READ, "%s.npz" % ticker), bar_ms=bar_ms, X=cat["X"], own_feats=np.array(OF),
                        MK=MK, mk_names=np.array(names), NEW=NEW,
                        new_names=np.array([k for k, _ in RS_K] + list(ERN_FEATS)), req=cat["req"],
                        has_index=has_index, shock=cat["shock"], tide=cat["tide"], bias=cat["bias"],
                        atr1h=cat["atr1h"], y=yy, res=rr, i=i, hz_ms=hz, arr_ms=arr, in_earn_file=np.array(in_file))
    cov = dict((n, float((NEW[:, j] != 0).mean())) for j, n in enumerate([k for k, _ in RS_K] + list(ERN_FEATS)))
    log("%s: %d rows, required ok %.1f%%, with S&P row %.1f%%, new-reading coverage %s, %.0fs" % (
        ticker, len(bar_ms), 100 * cat["req"].mean(), 100 * has_index.mean(),
        dict((k, round(v, 3)) for k, v in cov.items()), time.time() - t0))


# =====================================================================================
# the walk-forward model
# =====================================================================================
class Pool:
    """Every ticker's rows from the readings stage, one feature matrix F (own, market, new) per ticker."""

    def __init__(self, tickers=TICKERS):
        self.t = list(tickers)
        self.d = {}
        feats = None
        for t in self.t:
            with np.load(os.path.join(READ, "%s.npz" % t)) as z:
                r = dict((k, z[k]) for k in z.files)
            f = [str(x) for x in r["own_feats"]] + [str(x) for x in r["mk_names"]] + [str(x) for x in r["new_names"]]
            if feats is None:
                feats = f
            assert f == feats
            keep = (r["bar_ms"] >= FLOOR_MS) & (r["bar_ms"] < SEAL_MS) & r["has_index"]
            X = np.concatenate([r["X"], r["MK"], r["NEW"]], axis=1)[keep]
            dd = dict((k, r[k][keep]) for k in ("bar_ms", "req", "shock", "tide", "bias", "atr1h", "y", "res", "i",
                                                "hz_ms", "arr_ms"))
            dd["X"] = np.ascontiguousarray(X, dtype=np.float32)
            dd["ec_next"] = r["MK"][keep][:, [str(x) for x in r["mk_names"]].index("ec_next")].astype(float)
            self.d[t] = dd
            del r
        # names: a feature appearing twice (an own reading that is also a market one) keeps its first column
        self.feats = feats
        self.col = {}
        for j, f in enumerate(feats):
            self.col.setdefault(f, j)
        self.grid = np.unique(np.concatenate([self.d[t]["bar_ms"] for t in self.t]))
        for t in self.t:
            self.d[t]["g"] = np.searchsorted(self.grid, self.d[t]["bar_ms"])
            a = self.d[t]["arr_ms"]
            ga = np.searchsorted(self.grid, a, side="left")
            ga[(a == np.iinfo(np.int64).max) | (ga >= len(self.grid))] = -1
            self.d[t]["g_arr"] = ga
        self.g_floor = int(np.searchsorted(self.grid, FLOOR_MS))
        s0 = int(np.searchsorted(self.grid, FIRST_REFIT_MS))
        self.refits = list(range(s0, len(self.grid), EVERY))


def voice_defs(pool, with_new=True):
    """[(voice, [feature columns])]: the engine voices that read on a stock, the new ones, 'all' and 'base'."""
    own, market = _own_market()
    out = []
    for v in own + market:
        out.append((v, [pool.col[f] for f in model.VOICES[v][1]]))
    if with_new:
        for v, (_, fs) in NEW_VOICES.items():
            out.append((v, [pool.col[f] for f in fs]))
    allc = sorted(set(c for _, cs in out for c in cs))
    out.append(("all", allc))
    out.append(("base", []))
    return out


def card_scope(with_new=True):
    """{card: (voices, readings)} for the cards that read on a stock (rate_cards.scope's shape)."""
    own, market = _own_market()
    ok = set(own + market)
    out = {}
    for card, voices in evidence.CARDS.items():
        vs = [v for v in voices if v in ok]
        if not vs:
            continue
        fs = []
        for v in vs:
            fs += [f for f in model.VOICES[v][1] if f not in fs]
        out[card] = (vs, fs)
    if with_new:
        for v, (title, fs) in NEW_VOICES.items():
            out[title] = ([v], list(fs))
    return out


def train_mask(dd, T_ms, g_floor):
    """Rows a refit at the session opening T_ms may learn from: required readings, grade known (the 26th bar after
    the row opened at or before T_ms), from the floor on. (pure; tested)"""
    return dd["req"] & (dd["y"] >= 0) & (dd["hz_ms"] <= T_ms) & (dd["g"] >= g_floor)


def rate_and_choose(pool, train, T_ms, scope):
    import rate_cards as rc
    xs, ups, gs = [], [], []
    for t in train:
        dd = pool.d[t]
        m = train_mask(dd, T_ms, pool.g_floor) & (dd["y"] > 0)
        xs.append(dd["X"][m])
        ups.append(dd["y"][m] == labels.UP)
        gs.append(dd["g"][m])
    Xr, up, g = np.concatenate(xs), np.concatenate(ups), np.concatenate(gs)
    first = g < np.median(g)
    feat = {}
    needed = sorted(set(f for _, fs in scope.values() for f in fs))
    for f in needed:
        x = Xr[:, pool.col[f]].astype(np.float64)
        pooled, _ = rc.rate_reading(x, up, first)
        if pooled is not None:
            feat[f] = pooled
    rows = rc.card_rows(feat, {}, scope, [])
    cards, voices = rc.choose_voting(rows)
    voices = [v for v in voices if v != "owner"]                # never reads on a stock (registration)
    slim = [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]
    return cards, voices, slim, int(len(up))


def run_set(pool, name, train, judge, with_new=True, say=log):
    """One walk-forward. -> (stance rows of the judged tickers, per-refit log)."""
    cfg = stocks.index_cfg()
    V = voice_defs(pool, with_new)
    vnames = [v for v, _ in V]
    scope = card_scope(with_new)
    G = len(pool.grid)
    s0 = pool.refits[0]
    need = sorted(set(train) | set(judge))
    probs = dict((t, np.full((len(pool.d[t]["bar_ms"]), len(V), 3), np.nan, dtype=np.float32)) for t in need)
    votes_at = np.zeros((len(pool.refits), len(V)))
    warm, rlog = {}, []
    for k, s in enumerate(pool.refits):
        t0 = time.time()
        e = min(s + EVERY, G)
        T = int(pool.grid[s])
        cards, voices, rated, n_rated = rate_and_choose(pool, train, T, scope)
        votes_at[k] = [1.0 if v in voices else 0.0 for v in vnames]
        Xs, ys = [], []
        for t in train:
            dd = pool.d[t]
            m = train_mask(dd, T, pool.g_floor) & (((dd["g"] - pool.g_floor) % STEP) == 0)
            Xs.append(dd["X"][m])
            ys.append(dd["y"][m])
        Xtr, ytr = np.concatenate(Xs).astype(np.float64), np.concatenate(ys)
        del Xs, ys
        if len(ytr) < cfg["min_train_rows"]:
            raise RuntimeError("refit %d: %d training rows" % (k, len(ytr)))
        Ws = {}
        for v, cols in V:
            W = model.fit_softmax(Xtr[:, cols], ytr, cfg["l2"], warm.get(v))
            warm[v] = W
            if cfg.get("even_prior"):
                W = W.copy()
                W[:, 0] = W[:, 0].mean()
            Ws[v] = W
        del Xtr
        for t in need:
            dd = pool.d[t]
            m = (dd["g"] >= s) & (dd["g"] < e)
            if not m.any():
                continue
            Xc = dd["X"][m].astype(np.float64)
            pr = np.stack([model.predict(Ws[v], Xc[:, cols]) for v, cols in V], axis=1)
            pr[~dd["req"][m]] = np.nan
            probs[t][m] = pr
        rlog.append({"refit": k, "session_utc": str(pd.Timestamp(T, unit="ms", tz="UTC"))[:16], "train_rows": int(len(ytr)),
                     "rated_rows": n_rated, "cards": cards, "voices": voices,
                     "new_cards": [r for r in rated if r[0] in [NEW_VOICES[v][0] for v in NEW_VOICES]],
                     "top": rated[:12], "seconds": round(time.time() - t0, 1)})
        say("%s refit %d/%d %s: %d train rows, %d rated, voting %s (%.0fs)" % (
            name, k + 1, len(pool.refits), rlog[-1]["session_utc"], len(ytr), n_rated, ",".join(voices), time.time() - t0))
    # trust: model.trust_path's Hedge on the training tickers' losses, arriving at their grade's close
    arriving = np.zeros((G, len(V)))
    for t in train:
        dd = pool.d[t]
        L = model.losses(probs[t].astype(np.float64), dd["y"])
        idx = np.where(np.isfinite(L[:, 0]) & (dd["g_arr"] >= 0))[0]
        np.add.at(arriving, dd["g_arr"][idx], L[idx])
    decay = 0.5 ** (1.0 / cfg["trust_halflife"])
    eta, tfloor = cfg["trust_eta"], cfg["trust_floor"]
    trust = np.empty((G, len(V)))
    S = np.zeros(len(V))
    for g in range(G):
        S = decay * S + arriving[g]
        w = np.exp(-eta * (S - S.min()))
        w = np.maximum(w / w.sum(), tfloor)
        trust[g] = w / w.sum()
    # the stance on the judged tickers
    out, share = [], []
    cap = cfg.get("trust_cap")
    for t in judge:
        dd = pool.d[t]
        jm = (dd["g"] >= s0) & dd["req"] & np.isfinite(probs[t][:, 0, 0])
        idx = np.where(jm)[0]
        g = dd["g"][idx]
        kk = np.searchsorted(np.array(pool.refits), g, side="right") - 1
        w = trust[g] * votes_at[kk]
        w = w / w.sum(axis=1, keepdims=True)
        w = model.cap_shares(w, cap)
        Xj = dd["X"][idx]
        speaks = np.stack([(np.abs(Xj[:, cols]).sum(axis=1) > 0) if cols else np.zeros(len(idx), bool) for _, cols in V], axis=1)
        w2 = w * speaks
        tot = w2.sum(axis=1, keepdims=True)
        w2 = np.where(tot > 0, w2 / np.where(tot > 0, tot, 1.0), w)
        w2 = model.cap_shares(w2, cap)
        odds = model.mix(probs[t][idx].astype(np.float64), w2)
        share.append(w2)
        for r, j in enumerate(idx):
            o = odds[r]
            ec = dd["ec_next"][j]
            guard = bool(np.isfinite(ec) and ec >= 1.0 - 1.0 / 24.0 - 1e-9)
            tide = dd["tide"][j]
            bias = dd["bias"][j]
            side, why = stocks.decide(o, bool(dd["shock"][j]), None if not np.isfinite(tide) else float(tide),
                                      0 if not np.isfinite(bias) else int(bias), guard, cfg)
            out.append((t, int(dd["bar_ms"][j]), side, float(o[labels.UP] - o[labels.DOWN]) * 100.0, float(o[labels.UP]),
                        float(o[labels.DOWN]), float(o[labels.NEITHER]), why, int(dd["y"][j]), int(dd["res"][j]),
                        int(dd["i"][j]), CFG["barrier_atr"] * float(dd["atr1h"][j])))
    rows = pd.DataFrame(out, columns=["ticker", "bar_ms", "side", "score", "p_up", "p_down", "p_neither", "why", "y", "res",
                                      "i", "unit"])
    ws = np.concatenate(share) if share else np.zeros((0, len(V)))
    trust_share = dict((v, float(ws[:, j].mean())) for j, v in enumerate(vnames)) if len(ws) else {}
    return rows, {"refits": rlog, "trust_share": trust_share, "voices": vnames}


def walk_stage(names):
    pool = Pool()
    log("pool: %d tickers, grid %d sessions (%s .. %s), %d refits from %s, %d features" % (
        len(pool.t), len(pool.grid), pd.Timestamp(pool.grid[0], unit="ms", tz="UTC"),
        pd.Timestamp(pool.grid[-1], unit="ms", tz="UTC"), len(pool.refits),
        pd.Timestamp(pool.grid[pool.refits[0]], unit="ms", tz="UTC"), len(pool.feats)))
    os.makedirs(SETS, exist_ok=True)
    for name in names:
        t0 = time.time()
        if name == "primary":
            rows, info = run_set(pool, name, TICKERS, TICKERS, True)
        elif name == "e1":
            rows, info = run_set(pool, name, TICKERS, TICKERS, False)
        elif name.startswith("loto_"):
            out = name[5:]
            assert out in TICKERS
            rows, info = run_set(pool, name, [t for t in TICKERS if t != out], [out], True)
        else:
            raise SystemExit("unknown set %s" % name)
        rows.to_csv(os.path.join(SETS, "%s.csv" % name), index=False)
        with open(os.path.join(SETS, "%s.json" % name), "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
        log("%s: %d stance rows %s (%.0fs)" % (name, len(rows), rows["side"].value_counts().to_dict(), time.time() - t0))
        gc.collect()


# =====================================================================================
# report
# =====================================================================================
_pct, _f = h57._pct, h57._f


def sides_line(rows):
    s = rows["side"].value_counts().to_dict()
    tot = float(len(rows)) or 1.0
    return s, "of %d closes: %d LONG (%.2f%%), %d SHORT (%.2f%%), %d FLAT (%.2f%%)" % (
        int(tot), s.get("LONG", 0), 100 * s.get("LONG", 0) / tot, s.get("SHORT", 0), 100 * s.get("SHORT", 0) / tot,
        s.get("FLAT", 0), 100 * s.get("FLAT", 0) / tot)


def pass_rows(res):
    P = res["pass"]
    L = ["| condition | required | result | met |", "|---|---|---|---|"]
    for h in ("first", "second"):
        p = res["pooled"][h]
        L.append("| pooled nov hit, %s half | > 50%% and 95%% lower bound > 50%% | %s (%s .. %s, n %d) | %s |" % (
            h, _pct(p["nov_hit"]), _pct(p["nov_lo"]), _pct(p["nov_hi"]), p["nov_graded"],
            "yes" if (p["nov_hit"] or 0) > 0.5 and (p["nov_lo"] or 0) > 0.5 else "no"))
    L.append("| tickers with full-period nov hit > 50%% | >= %d of %d | %d (%s) | %s |" % (
        P["tickers_needed"], P["tickers_tested"], len(P["tickers_above_50"]), ", ".join(P["tickers_above_50"]) or "none",
        "yes" if P["enough_tickers"] else "no"))
    L.append("| **verdict** | both | | **%s** |" % ("PASS" if P["PASS"] else "NO PASS"))
    return L


def hit_table(res, tickers, rows):
    L = ["| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |",
         "|---|---|---|---|---|---|---|---|---|"]

    def line(name, d):
        f, a, b = d["full"], d["first"], d["second"]
        sd = f.get("sides") or {}
        L.append("| %s | %d | %s | %d | %s | %s .. %s | %s (%d) | %s (%d) | %s |" % (
            name, f["calls"], _pct(f["hit_all"]), f["nov_graded"], _pct(f["nov_hit"]), _pct(f["nov_lo"]), _pct(f["nov_hi"]),
            _pct(a["nov_hit"]), a["nov_graded"], _pct(b["nov_hit"]), b["nov_graded"],
            "%s / %s / %s" % (sd.get("LONG", 0), sd.get("SHORT", 0), sd.get("FLAT", 0)) if sd else "-"))
    for t in tickers:
        line(t, res["per_ticker"][t])
    for nm in ("five", "ten", "pooled"):
        line("**%s**" % nm, res[nm])
    return L


def prob_table(res, tickers):
    L = ["| ticker | rows | UP share | Brier | base | skill | log-loss | base | skill | skill first | skill second |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]

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
    for nm in ("five", "ten", "pooled"):
        pline("**%s**" % nm, res[nm])
    return L


def headline(res):
    p = res["pooled"]
    return {"nov_hit": p["full"]["nov_hit"], "nov_lo": p["full"]["nov_lo"], "nov_hi": p["full"]["nov_hi"],
            "nov_n": p["full"]["nov_graded"], "calls": p["full"]["calls"], "hit_all": p["full"]["hit_all"],
            "first": (p["first"]["nov_hit"], p["first"]["nov_lo"], p["first"]["nov_graded"]),
            "second": (p["second"]["nov_hit"], p["second"]["nov_lo"], p["second"]["nov_graded"]),
            "boot": (p["full"]["boot_lo"], p["full"]["boot_hi"]), "brier_skill": p["full"]["prob"].get("brier_skill"),
            "logloss_skill": p["full"]["prob"].get("logloss_skill"),
            "tickers_above": len(res["pass"]["tickers_above_50"]), "PASS": res["pass"]["PASS"], "split": res["split_utc"]}


def set_path(name):
    """sets/<name>.csv, or the gzipped copy kept on the server after the run."""
    p = os.path.join(SETS, "%s.csv" % name)
    return p if os.path.exists(p) or not os.path.exists(p + ".gz") else p + ".gz"


def report_stage():
    tick = list(TICKERS)
    prim = pd.read_csv(set_path("primary"))
    res = h57.measure(prim, tick)
    with open(os.path.join(SETS, "primary.json"), encoding="utf-8") as fh:
        pinfo = json.load(fh)
    out = {"registered": "research/HYPOTHESES.md H58 (20 Nov 2026, 02:50 UTC)", "version": CFG.get("version"),
           "primary": res}
    out["primary_sides"], prim_sides = sides_line(prim)
    # leave-one-ticker-out, pooled
    lo_parts = []
    for t in tick:
        p = set_path("loto_%s" % t)
        if os.path.exists(p):
            lo_parts.append(pd.read_csv(p))
    loto = pd.concat(lo_parts, ignore_index=True) if len(lo_parts) == len(tick) else None
    if loto is not None:
        out["loto"] = h57.measure(loto, tick)
        out["loto_sides"], loto_sides = sides_line(loto)
    e1p = set_path("e1")
    e1 = pd.read_csv(e1p) if os.path.exists(e1p) else None
    if e1 is not None:
        out["e1"] = h57.measure(e1, tick)
        out["e1_sides"], e1_sides = sides_line(e1)
    # H57's own rows, full and on the same judged dates
    h57rows = pd.concat([pd.read_csv(os.path.join(h57.ROWS, "%s.csv" % t)) for t in tick], ignore_index=True)
    h57same = h57rows[h57rows["bar_ms"] >= int(prim["bar_ms"].min())]
    out["h57_same_dates"] = h57.measure(h57same, tick)
    out["h57_same_sides"], h57_sides = sides_line(h57same)
    with open(os.path.join(H57_OUT, "results.json"), encoding="utf-8") as fh:
        h57res = json.load(fh)
    # card selection over the refits
    from collections import Counter
    cnt = Counter(c for r in pinfo["refits"] for c in r["cards"])
    nref = len(pinfo["refits"])
    out["card_votes"] = dict(cnt.most_common())
    out["trust_share"] = pinfo["trust_share"]
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    P = res["pass"]
    L = ["# H58: the stocks' own model on history", "",
         "Registered in research/HYPOTHESES.md (H58, 20 Nov 2026 02:50 UTC) before any H58 code or number. Engine %s. "
         "PAPER ONLY. Development data only (rows before 2025-11-11)." % CFG.get("version"), "",
         "**Verdict: %s.**" % ("PASS" if P["PASS"] else "NO PASS"), ""]
    L += pass_rows(res)
    L += ["", "How often a stance is taken: %s." % prim_sides, ""]
    hp, hs, hf = headline(res), headline(out["h57_same_dates"]), h57res["pooled"]
    lo = headline(out["loto"]) if loto is not None else None
    L += ["## Side by side with H57", "",
          "| measure | H58 primary (2022-01-03 .. seal) | H58 leave-one-ticker-out | H57 same dates | H57 as reported (2021-01-12 .. seal) |",
          "|---|---|---|---|---|"]

    def cell(h, key):
        if h is None:
            return "-"
        if key == "nov":
            return "%s (%s .. %s, n %d)" % (_pct(h["nov_hit"]), _pct(h["nov_lo"]), _pct(h["nov_hi"]), h["nov_n"])
        if key in ("first", "second"):
            v = h[key]
            return "%s (lower %s, n %d)" % (_pct(v[0]), _pct(v[1]), v[2])
        if key == "boot":
            return "%s .. %s" % (_pct(h["boot"][0]), _pct(h["boot"][1]))
        if key == "calls":
            return "%d (all hit %s)" % (h["calls"], _pct(h["hit_all"]))
        if key == "tick":
            return "%d of 13" % h["tickers_above"]
        return _f(h[key])
    hrep = {"nov_hit": hf["full"]["nov_hit"], "nov_lo": hf["full"]["nov_lo"], "nov_hi": hf["full"]["nov_hi"],
            "nov_n": hf["full"]["nov_graded"], "calls": hf["full"]["calls"], "hit_all": hf["full"]["hit_all"],
            "first": (hf["first"]["nov_hit"], hf["first"]["nov_lo"], hf["first"]["nov_graded"]),
            "second": (hf["second"]["nov_hit"], hf["second"]["nov_lo"], hf["second"]["nov_graded"]),
            "boot": (hf["full"]["boot_lo"], hf["full"]["boot_hi"]), "brier_skill": hf["full"]["prob"].get("brier_skill"),
            "logloss_skill": hf["full"]["prob"].get("logloss_skill"),
            "tickers_above": len(h57res["pass"]["tickers_above_50"])}
    for lab, key in (("calls (LONG/SHORT)", "calls"), ("pooled non-overlapping hit", "nov"), ("first half", "first"),
                     ("second half", "second"), ("day-block bootstrap 95%", "boot"), ("tickers above 50%", "tick"),
                     ("Brier skill vs base", "brier_skill"), ("log-loss skill vs base", "logloss_skill")):
        L.append("| %s | %s | %s | %s | %s |" % (lab, cell(hp, key), cell(lo, key), cell(hs, key), cell(hrep, key)))
    L.append("| share of closes with a stance | %s | %s | %s | 0.48%% |" % (
        "%.2f%%" % (100 * (1 - out["primary_sides"].get("FLAT", 0) / float(len(prim)))),
        "-" if loto is None else "%.2f%%" % (100 * (1 - out["loto_sides"].get("FLAT", 0) / float(len(loto)))),
        "%.2f%%" % (100 * (1 - out["h57_same_sides"].get("FLAT", 0) / float(len(h57same))))))
    L += ["", "Halves: H58 split at %s UTC; H57-same-dates split at %s UTC (each at its own median graded call)." % (
        res["split_utc"], out["h57_same_dates"]["split_utc"]), ""]
    L += ["## H58 primary: hit rate of LONG / SHORT calls (NEITHER not counted)", ""]
    L += hit_table(res, tick, prim)
    L += ["", "Day-block bootstrap of the pooled non-overlapping hit rate: full %s .. %s, first %s .. %s, second %s .. %s." % tuple(
        _pct(res["pooled"][h][k]) for h in ("full", "first", "second") for k in ("boot_lo", "boot_hi")), ""]
    L += ["## H58 primary: probabilities against each ticker's own UP share", ""]
    L += prob_table(res, tick)
    if loto is not None:
        L += ["", "## Leave-one-ticker-out (a check, not the verdict)", "",
              "Each ticker judged by a model whose card rating, voices and trust never saw it. Stances: %s." % loto_sides, ""]
        L += pass_rows(out["loto"])
        L += [""] + hit_table(out["loto"], tick, loto)
    if e1 is not None:
        L += ["", "## E1 (exploratory): without the two stock-only cards", "", "Stances: %s." % e1_sides, ""]
        L += pass_rows(out["e1"])
        L += [""] + hit_table(out["e1"], tick, e1)
    L += ["", "## Which cards voted (primary, %d refits)" % nref, "", "| card | refits voting |", "|---|---|"]
    for c, n in cnt.most_common():
        L.append("| %s | %d |" % (c, n))
    L += ["", "Mean say per voice on judged closes (after voting mask, speaking mask and the 40% cap), largest first:", ""]
    for v, s in sorted(pinfo["trust_share"].items(), key=lambda kv: -kv[1])[:15]:
        L.append("- %s: %.1f%%" % (v, 100 * s))
    L += ["", "## The two stock-only cards at each refit (1st half, 2nd half, steady, direction)", "",
          "| refit | strength vs S&P 500 | own earnings date |", "|---|---|---|"]
    for r in pinfo["refits"]:
        d = dict((x[0], x) for x in r["new_cards"])
        f = lambda x: "-" if x is None else "%s / %s / %s / %s (%s)" % (x[2], x[3], x[4], x[5], x[1])
        L.append("| %s | %s | %s |" % (r["session_utc"][:10], f(d.get("Strength against the S&P 500")), f(d.get("Own earnings date"))))
    L += ["", "## How it was made", "",
          "- Bars: H57's Dukascopy CFD 15-minute cash-hours bars; S&P 500 bars from the engine's data/spx_15m.csv (copied read-only).",
          "- Readings: engine15/stocks.py's readings per calendar month from a 60-day window (as live), market-wide cards "
          "from the S&P call's readings at the same close; strength against the S&P 500 and own earnings date (megacap "
          "earnings file; MU, T, LLY no read).",
          "- Model: walk-forward, refit every 672 sessions of the 13 tickers' common timeline from 2022-01-03; at each refit "
          "the cards are rated (rate_cards.py's functions) and the voices fitted (model.fit_softmax) only on rows whose "
          "grade was known then; trust is the engine's Hedge on graded losses as they arrive; the stance is stocks.decide.",
          "- Grading: labels.triple_barrier, 1.5 x atr1h, 26 bars; NEITHER not counted. Not a trading test: no costs."]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    log("report written: %s" % ("PASS" if P["PASS"] else "NO PASS"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "report"
    if cmd == "prep":
        prep()
    elif cmd == "readings":
        for t in argv[1:]:
            readings_stage(t)
            gc.collect()
    elif cmd == "walk":
        walk_stage(argv[1:])
    elif cmd == "report":
        report_stage()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
