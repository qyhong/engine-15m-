# -*- coding: utf-8 -*-
"""regime_trust -- H108: card trust kept separately per regime bucket, as a shadow MIND. PAPER ONLY. NOT passed.

RL idea R3 (docs/RL_NEXT.md; owner, 24 Nov 2026: "Ok lets do it"). Registered in research/HYPOTHESES.md H108 before
this file existed. There is no evidence yet that it helps: the forward paper book is the only test.

The live engine learns ONE set of card weights per market group from every graded call (model.trust_path). This
mind keeps one set per REGIME BUCKET: a call made while its market was in bucket b only moves bucket b's weights.

    bucket (per market, at each 15m close, from readings the engine already has at that close):
        trend / range   the `regime` reading (daily, last CLOSED daily bar): TREND_* and MOMENTUM_* = trend,
                        RANGE and TRANSITION = range
        high / low      the `vol_rank` reading: 0.5 or more = high, below = low
        -> trend_hi, trend_lo, range_hi, range_lo; a bar with either reading missing has no bucket
    table of bucket b   model.trust_path fed only with the calls made in b: the same loss, the same clock (a loss
                        counts from the bar its grade arrives, and halves every trust_halflife bars), the same
                        trust_eta / trust_floor, all read from the live config (prep["cfg"]), never copied here
    odds at bar s       the table of the bucket the market is in at s, then the live mixing unchanged (voting cards,
                        the cap, silent cards, the cap, model.mix); a bar with no bucket: the engine's own odds
    book                `m_regime_trust`: shadows.run with NO rule switched on (the fresh main copy's rule and
                        sizing) on those odds; it starts flat on each market at its first live bar

NO LOOK-AHEAD: the table used at bar s holds only calls whose grade had arrived by s (tests/test_regime_trust.py cuts
the future off and compares). Nothing here is fitted: one weighted sum of losses per bucket and a few rows of
arithmetic per step. It changes no other book: shadows.advance calls `advance` after every challenger and follower,
inside a try/except, and this module writes only its own book (`sst["books"][NAME]`) and its own start record.

Verdict (H108, forward only): nothing is read before 30 closed forward trades; then the scoreboard's row against zero
and `compare`'s line against the fresh main copy over the same days ("ahead of" / "behind" / "level with").
"""
import time

import numpy as np
import pandas as pd

from . import model

NAME = "m_regime_trust"
HYPOTHESIS = "H108"
LABEL = "NOT passed, paper only"
TITLE = "Regime trust mind (H108): card trust kept per regime bucket. NOT passed, paper only"
# reports.scoreboard: it must start with "Shadow" (the Telegram bot tells shadow rows by that word)
SCOREBOARD_TITLE = "Shadow mind: %s (H108, card trust per regime bucket). NOT passed, paper only" % NAME

# ---- the buckets, fixed by H108 before any number was seen (never tuned here)
TREND_LABELS = ("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN")
RANGE_LABELS = ("RANGE", "TRANSITION")
VOL_SPLIT = 0.5                                                  # vol_rank at or above: "high"
BUCKETS = ("trend_hi", "trend_lo", "range_hi", "range_lo")

# ---- the verdict rule's constants (H108)
MIN_TRADES = 30                                                  # nothing is read before this many closed trades
LEVEL_BAND_PTS = 1.0                                             # "level with": returns less than 1.0 point apart
START_EQUITY = 10000.0
NEEDS = ("probs", "y", "res", "X", "odds", "ev", "px", "cfg", "times")


# =====================================================================================
# the buckets
# =====================================================================================
def bucket_codes(ev, lo, n):
    """One market's bucket at the close of bars lo .. n-1: an index into BUCKETS, or -1 (no bucket).
    Row k of `ev` holds what was known at the close of bar k (evidence.py), so nothing here looks ahead."""
    out = np.full(max(n - lo, 0), -1, dtype=np.int8)
    if ev is None or "regime" not in ev or "vol_rank" not in ev or n <= lo:
        return out
    reg = pd.Series(np.asarray(ev["regime"].values[lo:n], dtype=object))
    vr = np.asarray(ev["vol_rank"].values[lo:n], dtype=float)
    trend, rng = reg.isin(TREND_LABELS).values, reg.isin(RANGE_LABELS).values
    hi, lw = vr >= VOL_SPLIT, vr < VOL_SPLIT                     # NaN is neither
    out[trend & hi], out[trend & lw], out[rng & hi], out[rng & lw] = 0, 1, 2, 3
    return out


# =====================================================================================
# the tables and the odds
# =====================================================================================
def _window_lo(prep, n):
    """The first row the live learner has calls for (leanprep keeps probs from there; before it there is no model)."""
    lo = prep["lean_lo"] if "lean_lo" in prep else prep.get("birth_idx", 0)
    return int(min(max(int(lo), 0), n))


def _rows(x, lo, n):
    """Rows lo .. n-1 of a full-length array or of a leanprep.Tail."""
    arr = getattr(x, "arr", None)
    if arr is not None and hasattr(x, "lo"):
        return arr[lo - x.lo:n - x.lo]
    return x[lo:n]


def loss_sums(prep, assets, codes, lo, n, r0):
    """The discounted loss sums of every bucket at sessions r0 .. n-1: (n - r0, buckets, voices), and the number of
    graded calls behind each bucket at n-1. Exactly model.trust_path's running sum S, fed only with the calls of one
    bucket: a call made at bar t (market a in bucket b at t) adds its loss at bar t + res[t], never earlier, and every
    sum is multiplied by `decay` at each bar. codes: {asset: bucket_codes(ev, lo, n)}. Needs lo <= r0 < n."""
    cfg = prep["cfg"]
    decay = 0.5 ** (1.0 / cfg["trust_halflife"])
    K, V, R, j0 = len(BUCKETS), len(model.VOICE_NAMES), n - r0, r0 - lo
    S = np.zeros((R, K, V))
    calls = np.zeros(K, dtype=np.int64)
    for a in assets:
        L = model.losses(np.asarray(_rows(prep["probs"][a], lo, n)), np.asarray(prep["y"][a][lo:n]))
        idx = np.where(np.isfinite(L[:, 0]))[0]
        g = idx + np.asarray(prep["res"][a][lo:n])[idx]          # the bar the grade arrives (rows from lo)
        keep = (g < n - lo) & (codes[a][idx] >= 0)               # a grade that arrives after bar n-1 is not known yet
        idx, g = idx[keep], g[keep]
        b = codes[a][idx]
        old = g <= j0                                            # known by r0: one weighted sum per bucket
        w, Lo, bo = decay ** (j0 - g[old]).astype(float), L[idx[old]], b[old]
        for k in range(K):
            m = bo == k
            if m.any():
                S[0, k] += w[m] @ Lo[m]
        new = ~old                                               # arriving at r0+1 .. n-1: added at their own bar below
        if new.any():
            np.add.at(S, (g[new] - j0, b[new]), L[idx[new]])
        calls += np.bincount(b, minlength=K)[:K]
    for r in range(1, R):
        S[r] += decay * S[r - 1]
    return S, calls


def weights(S, cfg):
    """model.trust_path's weights from running sums S (..., voices): Hedge, floored, rows sum to 1."""
    w = np.exp(-cfg["trust_eta"] * (S - S.min(axis=-1, keepdims=True)))
    w = np.maximum(w / w.sum(axis=-1, keepdims=True), cfg["trust_floor"])
    return w / w.sum(axis=-1, keepdims=True)


def mix_rows(prep, a, T, r0, n):
    """One market's odds at sessions r0 .. n-1 from the trust rows T (n - r0, voices): the live mixing, line for
    line as backtest.prepare / leanprep.prepare_live do it (voting cards, cap, silent cards, cap, mix)."""
    cfg = prep["cfg"]
    T = np.array(T, dtype=float, copy=True)
    if cfg.get("voting"):
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        T = T * votes
        T = T / T.sum(axis=1, keepdims=True)
    T = model.cap_shares(T, cfg.get("trust_cap"))
    Xa = np.asarray(prep["X"][a][r0:n])
    speaks = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - r0, bool)
                       for v in model.VOICE_NAMES], axis=1)
    w = T * speaks
    tot = w.sum(axis=1, keepdims=True)
    w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), T)
    w = model.cap_shares(w, cfg.get("trust_cap"))
    return model.mix(np.asarray(_rows(prep["probs"][a], r0, n)), w)


def odds(prep, assets, r0, n):
    """The mind's odds for every market of one group at sessions r0 .. n-1.
    -> ({asset: (n - r0, 3)}, {asset: bucket codes for r0 .. n-1}, graded calls behind each bucket at n-1).
    Uses rows below n only, and of those only calls graded by the bar they are used at."""
    missing = [k for k in NEEDS if k not in prep]
    if missing:
        raise KeyError("the prep has no %s" % ", ".join(missing))
    lo = _window_lo(prep, n)
    if not lo <= r0 < n:
        raise ValueError("rows %d .. %d are outside the learning window (from %d)" % (r0, n - 1, lo))
    codes = dict((a, bucket_codes(prep["ev"][a], lo, n)) for a in assets)
    S, calls = loss_sums(prep, assets, codes, lo, n, r0)
    W = weights(S, prep["cfg"])                                  # (rows, buckets, voices)
    out, now = {}, {}
    rows = np.arange(n - r0)
    for a in assets:
        code = codes[a][r0 - lo:]
        od = mix_rows(prep, a, W[rows, np.clip(code, 0, None)], r0, n)
        none = code < 0                                          # no bucket: the engine's own odds
        if none.any():
            od[none] = np.asarray(prep["odds"][a][r0:n])[none]
        out[a], now[a] = od, code
    return out, now, calls


# =====================================================================================
# the forward book (called by shadows.advance, guarded there)
# =====================================================================================
def _utc_close(times, k, bar_ms):
    return str(times[k] + pd.Timedelta(milliseconds=bar_ms))[:16]


def advance(prep, group, assets, lo, n, sst, cfg=None, mains_before=None, log=None):
    """Advance the mind's book on every market of one group to session n-1 (changes only sst["books"][NAME] and
    sst["late_starts"][NAME]). A market seen for the first time starts flat at session lo (the group's first new
    session); afterwards each market resumes after the last session it processed, so a skipped step is caught up.
    mains_before: {asset: the fresh main copy's state BEFORE this step}, for the same-days comparison.
    One market failing is logged in one line and skipped; the others go on. -> {(NAME, asset): closed trades}"""
    from . import data, shadows                                  # shadows imports this module: late import
    from .config import CFG
    t0 = time.perf_counter()
    say = log or (lambda *_: None)
    times = prep["times"]
    times_ms = data.to_ms(times)
    books = sst.get("books", {}).get(NAME) or {}
    start = {}
    for a in assets:
        last = ((books.get(a) or {}).get("mind") or {}).get("last_ms")
        start[a] = int(lo) if last is None else int(np.searchsorted(times_ms, int(last), side="right"))
    todo = [a for a in assets if start[a] < n]
    if not todo:
        return {}
    wlo = _window_lo(prep, n)
    r0 = max(min(start[a] for a in todo), wlo)                   # before the window there is no model: NaN odds (WAIT)
    if r0 >= n:
        return {}
    od, code, calls = odds(prep, list(assets), r0, n)            # every market of the group feeds the tables
    closed, said = {}, []
    for a in todo:
        try:
            inp = shadows.book_inputs(prep, a)
            full = np.full((len(inp["px"]["close"]), 3), np.nan)
            full[r0:n] = od[a]
            old = books.get(a)
            b = shadows.run(inp["px"], full, inp["shock"], inp["tide"], inp["unit"],
                            shadows.asset_cfg(a, dict(cfg or prep["cfg"])), start[a], n, state=old,
                            bias=inp["bias"], guard=inp["guard"], rule={}, times_ms=times_ms)
            st = b["state"]
            seen = dict(((old or {}).get("mind") or {}).get("bars") or {})
            for k in code[a][max(start[a] - r0, 0):]:            # forward bars spent in each bucket
                key = BUCKETS[k] if k >= 0 else "none"
                seen[key] = int(seen.get(key, 0)) + 1
            k_now = int(code[a][-1])
            st["mind"] = {"last_ms": int(times_ms[n - 1]), "bucket": BUCKETS[k_now] if k_now >= 0 else None,
                          "table_calls": int(calls[k_now]) if k_now >= 0 else None, "bars": seen}
            if old is None:                                      # its first live bar: remember when, and the fresh main
                mb = (mains_before or {}).get(a) or {}           # copy's marked equity then (the same-days comparison)
                sst.setdefault("late_starts", {}).setdefault(NAME, {})[a] = {
                    "ms": int(times_ms[start[a]]), "utc": _utc_close(times, start[a], CFG["bar_ms"]),
                    "main_eq": float(mb.get("equity_marked", mb.get("eq", START_EQUITY)))}
            sst.setdefault("books", {}).setdefault(NAME, {})[a] = st
            if len(b["trades"]):
                closed[(NAME, a)] = b["trades"]
            said.append("%s %s" % (a, st["mind"]["bucket"] or "no bucket"))
        except Exception as e:
            say("%s: regime trust mind failed on %s: %r" % (group, a, e))
    say("%s: regime trust mind (%s, paper) %.3fs: %s" % (group, HYPOTHESIS, time.perf_counter() - t0, ", ".join(said)))
    return closed


def view_extra(st):
    """What the page view of one market's book adds to shadows.asset_view."""
    m = (st or {}).get("mind") or {}
    return {"regime_bucket": m.get("bucket"), "bucket_graded_calls": m.get("table_calls"), "label": LABEL}


# =====================================================================================
# the registered comparison (H108: against the fresh main copy, the same markets, the same days)
# =====================================================================================
def _line(pairs, closed_trades):
    """pairs: [(the mind's change in marked equity, the main copy's change since the mind started)] per market."""
    k = len(pairs)
    if not k:
        return None
    mind = 100.0 * sum(p[0] for p in pairs) / (START_EQUITY * k)
    main = 100.0 * sum(p[1] for p in pairs) / (START_EQUITY * k)
    d = mind - main
    word = "ahead of" if d >= LEVEL_BAND_PTS else "behind" if d <= -LEVEL_BAND_PTS else "level with"
    return {"markets": k, "mind_return_pct": round(mind, 2), "main_copy_return_pct": round(main, 2),
            "difference_pts": round(d, 2), "read": word,
            "sentence": "%s %+.2f%% vs the fresh main copy %+.2f%% over the same days, %d closed trades: %s the main "
                        "copy by %.2f points. Paper only, NOT passed." % (NAME, mind, main, closed_trades, word, abs(d))}


def compare(sst, closed_trades):
    """The comparison line of H108's verdict rule, from the shadow books' state. Before MIN_TRADES closed forward
    trades it gives no number and no word: only how many trades there are."""
    books = (sst or {}).get("books") or {}
    mine, main = books.get(NAME) or {}, books.get("main") or {}
    late = ((sst or {}).get("late_starts") or {}).get(NAME) or {}
    out = {"hypothesis": HYPOTHESIS, "against": "main (the fresh main copy): same rule, sizing, markets and days",
           "closed_trades": int(closed_trades), "min_trades": MIN_TRADES, "level_band_pts": LEVEL_BAND_PTS}
    if closed_trades < MIN_TRADES:
        out["read"] = "no read before %d closed forward trades (%d of %d)" % (MIN_TRADES, closed_trades, MIN_TRADES)
        return out
    pairs = {}
    for a, st in mine.items():
        ls, m = late.get(a), main.get(a)
        if not st or not ls or ls.get("main_eq") is None or not m:
            continue
        pairs[a] = (float(st.get("equity_marked", st.get("eq", START_EQUITY))) - START_EQUITY,
                    float(m.get("equity_marked", m.get("eq", START_EQUITY))) - float(ls["main_eq"]))
    line = _line(list(pairs.values()), closed_trades)
    if line is None:
        out["read"] = "no read: the books' state is not available"
        return out
    out.update(line)
    starts = [late[a]["utc"] for a in pairs if late[a].get("utc")]
    out["since_utc"] = min(starts) if starts else None
    crypto = _line([pairs[a] for a in ("BTCUSDT", "ETHUSDT") if a in pairs], closed_trades)
    if crypto is not None:                                       # beside it, not the rule
        out["btc_eth_beside_not_the_rule"] = dict((k, crypto[k]) for k in (
            "markets", "mind_return_pct", "main_copy_return_pct", "difference_pts", "read"))
    return out


def scoreboard_extra(closed_trades, state_path=None):
    """What reports.scoreboard adds to this book's row: the label and the comparison line. None when the mind has
    neither started nor closed a trade (no row is shown for a book that does not exist yet)."""
    import json
    import os
    from .shadows import STATE_PATH
    sst = None
    path = state_path or STATE_PATH
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            sst = json.load(fh)
    if not closed_trades and not ((sst or {}).get("books") or {}).get(NAME):
        return None
    return {"title": SCOREBOARD_TITLE, "label": LABEL, "passed": False, "paper_only": True, "hypothesis": HYPOTHESIS,
            "vs_main_copy": compare(sst, int(closed_trades))}
