# -*- coding: utf-8 -*-
"""H113: BTC and ETH, how fast the Lead turns after a capitulation low (part a, descriptive), and whether the Setups
book's shorts opened in the 48 hours after H107's rule A fires do worse than its other shorts (part b, the test).
Research only; registered in research/HYPOTHESES.md (H113) before any H113 number on history was computed. Reads the
bar and funding files, the evidence store and a private copy of the cached fits; changes nothing in the engine, the
books or the vault.

    py -3 -X utf8 research/h113_lead_after_capitulation.py --fits-dir fits_today              build, then analyse
    py -3 -X utf8 research/h113_lead_after_capitulation.py --fits-dir fits_today --analyse    analyse from the saved Lead

    ... --analyse --journal <journal_slim.jsonl> --audit-live <out/live> --reg-commit <hash>
        the event apart also from a copy of the live journal and trade files; the commit quoted in the report

The report's "In short" section is research/out/h113_lead_after_capitulation/reading.md, written by hand after the run.
The build step is the heavy one (it loads the crypto evidence store once): it saves the Lead per close and the Setups
book's trades to <out>/cache/. The analyse step reads only that and the bar files. The capitulation trigger is
research/h107_capitulation_rebound.py::features, imported, not copied.
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

import h107_capitulation_rebound as h107  # noqa: E402
from engine15 import data, labels, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h113_lead_after_capitulation")
COINS = ("BTCUSDT", "ETHUSDT")
MID, HOLDOUT, EVENT = "2023-06-08 00:00", "2025-11-11 00:00", "2026-11-19 00:00"
SEGS = ("h1", "h2", "holdout", "event")
SEG_NAMES = {"h1": "First half (2020-02 to 2023-06-07)", "h2": "Second half (2023-06-08 to 2025-11-10)",
             "holdout": "Holdout (2025-11-11 to 2026-11-18)", "event": "The event apart (from 2026-11-19)"}
BAR_MS = int(CFG["bar_ms"])
WIN = 192                      # the post-capitulation window: the trigger's close and the next 191 closes (48 hours)
AFTER = 192                    # a confirmed low is not undercut in the next 192 bars
PRE, POST = 96, 288            # the Lead is read from 24 hours before to 72 hours after
GAP_DAYS = 7                   # confirmed lows on one coin at least 7 days apart
MARKS = (96, 192, 288)         # +24h, +48h, +72h
MIN_HALF, MIN_HOLD = 20, 10
B, SEED = 10000, 20261124
LONG_BAR = 5.0                 # from flat the engine goes long by itself at +5 points


# ------------------------------------------------------------------------------------------------- pure helpers
def seg_of(t):
    """The segment of a deciding bar's open time (a tz-aware Timestamp)."""
    if t < pd.Timestamp(MID, tz="UTC"):
        return "h1"
    if t < pd.Timestamp(HOLDOUT, tz="UTC"):
        return "h2"
    if t < pd.Timestamp(EVENT, tz="UTC"):
        return "holdout"
    return "event"


def seg_array(t):
    """seg_of for a whole DatetimeIndex."""
    cuts = pd.DatetimeIndex([pd.Timestamp(x, tz="UTC") for x in (MID, HOLDOUT, EVENT)])
    return np.array(SEGS)[np.asarray(cuts.searchsorted(pd.DatetimeIndex(t), side="right"))]


def low_candidates(t, low, lowN, cref, lead, drop=h107.REG["drop"], low_days=h107.REG["low_days"], after=AFTER):
    """Bars whose low is the lowest of the 30 days up to it (H107's lowN), at least `drop` under the close a week
    earlier (H107's cref), not undercut in the next `after` bars, with a Lead at the bar. -> indices."""
    n = len(low)
    have = np.asarray(t >= t[0] + pd.Timedelta(days=low_days))
    nxt = np.full(n, np.nan)                                     # lowest low of bars k+1 .. k+after (needs all of them)
    if n > after:
        fwd = pd.Series(low[::-1]).rolling(after, min_periods=after).min().values[::-1]   # min of low[k .. k+after-1]
        nxt[:n - after] = fwd[1:n - after + 1]
    with np.errstate(invalid="ignore"):
        cand = have & (low <= lowN) & (low / cref - 1.0 <= -drop) & (low <= nxt) & np.isfinite(lead)
    return np.flatnonzero(cand)


def confirmed_lows(t, low, lowN, cref, lead, drop=h107.REG["drop"], low_days=h107.REG["low_days"], after=AFTER,
                   gap_days=GAP_DAYS):
    """The candidates in time order, one dropped when it comes less than `gap_days` after the last one kept.
    -> (kept indices, number of candidates)."""
    ks = low_candidates(t, low, lowN, cref, lead, drop, low_days, after)
    kept, last = [], None
    gap = pd.Timedelta(days=gap_days)
    for k in ks:
        if last is None or t[k] - t[last] >= gap:
            kept.append(int(k))
            last = int(k)
    return np.array(kept, int), int(len(ks))


def window_mask(n, onsets, win=WIN):
    """True at every close inside a window: an onset's own close and the next win-1 closes; windows join."""
    m = np.zeros(n, bool)
    for k in onsets:
        m[int(k):min(n, int(k) + win)] = True
    return m


def bars_since(n, onsets):
    """Bars since the latest onset at or before each close (a large number when there is none)."""
    out = np.full(n, 10 ** 9, np.int64)
    on = np.sort(np.asarray(onsets, int))
    if len(on):
        idx = np.arange(n)
        j = np.searchsorted(on, idx, side="right") - 1
        ok = j >= 0
        out[ok] = idx[ok] - on[j[ok]]
    return out


def first_at_or_above(path, level):
    """Hours from the anchor's close (path[0]) to the first close with the Lead at or above `level`; None if never."""
    with np.errstate(invalid="ignore"):
        hit = np.flatnonzero(np.asarray(path, float) >= level)
    return float(hit[0]) / 4.0 if len(hit) else None


def anchor_row(coin, k, t, lead, close, low, anchor_px=None):
    """Read-outs of the Lead and price around bar k. anchor_px: the low itself (part a); None = the close (a trigger)."""
    n = len(lead)
    a, z = k - PRE, min(n, k + POST + 1)
    path = np.full(PRE + POST + 1, np.nan)
    path[max(0, -a):z - a] = lead[max(a, 0):z]
    post = path[PRE:]                                            # offsets 0 .. +288 bars
    seen = int(np.isfinite(post).sum())
    row = {"coin": coin, "k": int(k), "time": str(t[k])[:16], "seg": seg_of(t[k]), "lead_at": float(lead[k]),
           "low": float(low[k]), "close": float(close[k]), "full_72h": bool(k + POST < n),
           "hours_seen_after": round((min(n - 1, k + POST) - k) / 4.0, 2),
           "to_zero_h": first_at_or_above(post, 0.0), "to_long_bar_h": first_at_or_above(post, LONG_BAR),
           "max_lead_72h": float(np.nanmax(post)) if seen else None,
           "share_below_0_72h": float(np.mean(post[1:][np.isfinite(post[1:])] < 0)) if np.isfinite(post[1:]).any() else None,
           "hourly": [None if x != x else round(float(x), 2) for x in path[::4]]}
    for m in MARKS:
        h = m // 4
        if k + m < n:
            row["down_at_%dh" % h] = None if lead[k + m] != lead[k + m] else bool(lead[k + m] < 0)
            row["px_vs_close_%dh" % h] = float(close[k + m] / close[k] - 1.0) * 100
            if anchor_px is not None:
                row["px_vs_low_%dh" % h] = float(close[k + m] / anchor_px - 1.0) * 100
        else:
            row["down_at_%dh" % h] = row["px_vs_close_%dh" % h] = None
            if anchor_px is not None:
                row["px_vs_low_%dh" % h] = None
    return row


def _med(xs):
    xs = [x for x in xs if x is not None and x == x]
    return float(np.median(xs)) if xs else None


def _share(flags):
    fl = [f for f in flags if f is not None]
    return (float(np.mean(fl)) * 100, len(fl)) if fl else (None, 0)


def summarise(rows):
    """One cell of part (a): the events' read-outs together."""
    n = len(rows)
    if not n:
        return {"n": 0}
    out = {"n": n, "lead_at_median": _med([r["lead_at"] for r in rows]),
           "max_lead_72h_median": _med([r["max_lead_72h"] for r in rows]),
           "share_of_72h_below_0_median": _med([None if r["share_below_0_72h"] is None else r["share_below_0_72h"] * 100
                                                for r in rows])}
    for key, name in (("to_zero_h", "zero"), ("to_long_bar_h", "long_bar")):
        hs = [r[key] for r in rows]
        for lim in (24, 48, 72):
            out["%s_within_%dh_pct" % (name, lim)] = float(np.mean([h is not None and h <= lim for h in hs]) * 100)
        turned = sorted(h for h in hs if h is not None)
        out["%s_never_in_72h" % name] = int(n - len(turned))
        # the median over all events, "never" counted as beyond 72 hours: a number only if at least half turned
        med = float(np.median(turned + [np.inf] * (n - len(turned))))
        out["%s_median_h" % name] = med if np.isfinite(med) else None
        out["%s_median_h_of_those_that_turned" % name] = float(np.median(turned)) if turned else None
    for m in MARKS:
        h = m // 4
        out["down_at_%dh_pct" % h], out["down_at_%dh_n" % h] = _share([r["down_at_%dh" % h] for r in rows])
        out["px_vs_close_%dh_median" % h] = _med([r["px_vs_close_%dh" % h] for r in rows])
        if "px_vs_low_%dh" % h in rows[0]:
            out["px_vs_low_%dh_median" % h] = _med([r.get("px_vs_low_%dh" % h) for r in rows])
            out["px_up_vs_close_%dh_pct" % h] = _share([None if r["px_vs_close_%dh" % h] is None else r["px_vs_close_%dh" % h] > 0
                                                        for r in rows])[0]
    H = np.array([[np.nan if x is None else x for x in r["hourly"]] for r in rows], float)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out["hourly_median"] = [None if x != x else round(float(x), 2) for x in np.nanmedian(H, axis=0)]
            out["hourly_q25"] = [None if x != x else round(float(x), 2) for x in np.nanpercentile(H, 25, axis=0)]
            out["hourly_q75"] = [None if x != x else round(float(x), 2) for x in np.nanpercentile(H, 75, axis=0)]
            out["hourly_share_below_0"] = [None if not np.isfinite(col).any() else round(float(np.mean(col[np.isfinite(col)] < 0) * 100), 1)
                                           for col in H.T]
    return out


def stats(r):
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if not len(r):
        return {"n": 0, "mean_r": None, "sum_r": 0.0, "won_pct": None, "median_r": None}
    return {"n": int(len(r)), "mean_r": float(r.mean()), "sum_r": float(r.sum()), "won_pct": float((r > 0).mean() * 100),
            "median_r": float(np.median(r))}


def boot_diff(df, months, draws=B, seed=SEED):
    """Month-clustered bootstrap of (in-window mean R - others' mean R). df: columns month, inwin, r."""
    mi = dict((m, i) for i, m in enumerate(months))
    S = np.zeros((2, len(months)))
    N = np.zeros((2, len(months)))
    for m, w, r in zip(df["month"].values, df["inwin"].values, df["r"].values):
        S[int(bool(w)), mi[int(m)]] += r
        N[int(bool(w)), mi[int(m)]] += 1
    if N[1].sum() == 0 or N[0].sum() == 0:
        return None
    obs = S[1].sum() / N[1].sum() - S[0].sum() / N[0].sum()
    rng = np.random.default_rng(seed)
    D = rng.integers(0, len(months), size=(draws, len(months)))
    si, ni, so, no = S[1][D].sum(1), N[1][D].sum(1), S[0][D].sum(1), N[0][D].sum(1)
    ok = (ni > 0) & (no > 0)
    v = si[ok] / ni[ok] - so[ok] / no[ok]
    return {"obs": float(obs), "lo": float(np.percentile(v, 2.5)), "hi": float(np.percentile(v, 97.5)),
            "share_of_draws_below_0": float(np.mean(v < 0) * 100), "draws": int(len(v)), "months": int(len(months)),
            "months_with_an_in_window_trade": int((N[1] > 0).sum())}


def split_cell(tr, side, seg, win_col="inwin"):
    """In-window against the others for one side and one segment. tr: the trade frame (both coins)."""
    d = tr[(tr.side == side) & (tr.seg == seg) & np.isfinite(tr.r)]
    a, b = d[d[win_col]], d[~d[win_col]]
    return {"in": stats(a.r.values), "out": stats(b.r.values)}


def verdict(h1, h2):
    """The registered PASS condition on the two halves' short cells."""
    checks = {}
    for name, c in (("h1", h1), ("h2", h2)):
        i, o = c["in"], c["out"]
        checks["%s_at_least_%d_in_window" % (name, MIN_HALF)] = i["n"] >= MIN_HALF
        checks["%s_in_window_mean_r_below_0" % name] = bool(i["n"] and i["mean_r"] < 0)
        checks["%s_in_window_below_others" % name] = bool(i["n"] and o["n"] and i["mean_r"] < o["mean_r"])
    enough = checks["h1_at_least_%d_in_window" % MIN_HALF] and checks["h2_at_least_%d_in_window" % MIN_HALF]
    word = "PASS" if all(checks.values()) else ("TOO FEW TO JUDGE (no pass)" if not enough else "DOES NOT PASS")
    return word, checks


# ------------------------------------------------------------------------------------------------- build (heavy)
def build(fits_root, cache, log=print):
    """Load the crypto group once; save the Lead per close and the Setups book's trades."""
    import h59_half_be as h59
    t0 = time.time()
    prep = h59.prep_cut("crypto", list(COINS), os.path.join(fits_root, "crypto"), None, log=log)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    os.makedirs(cache, exist_ok=True)
    meta = {"store_first": str(times[0])[:16], "store_last": str(times[n - 1])[:16], "n": int(n), "coins": {},
            "version": CFG["version"], "built_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime())}
    arrays = {"times_ms": np.asarray(tms, np.int64)}
    for a in COINS:
        odds = prep["odds"][a]
        ok = np.isfinite(odds[:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        arrays["lead_" + a] = (odds[:, labels.UP] - odds[:, labels.DOWN]) * 100.0
        ev = prep["ev"][a]
        for col in ("htf_bias", "shock"):
            arrays["%s_%s" % (col, a)] = ev[col].values.astype(float) if col in ev else np.full(n, np.nan)
        aux = shadows.aux_from_ev(ev, prep["px"][a])
        b = shadows.run_challenger("b_targets", prep, a, lo, n, aux=aux)      # the engine's own Setups book
        tr = b["trades"].copy()
        tr.to_csv(os.path.join(cache, "trades_%s.csv" % a), index=False)
        st = b["state"]
        meta["coins"][a] = {"first_close_with_odds": str(times[lo])[:16], "lo": int(lo), "trades": int(len(tr)),
                            "sum_r": float(np.nansum(tr.r_mult.values.astype(float))),
                            "end_state": {"pos": st.get("pos"), "entry": st.get("entry"), "why_in": st.get("why_in"),
                                          "t_in_ms": st.get("t_in_ms"), "stop": st.get("stop"), "t1_hit": st.get("t1_hit"),
                                          "equity_marked": st.get("equity_marked")}}
        log("%s: Lead from %s, Setups book %d trades, %+.1fR (%.0fs)" % (a, str(times[lo])[:16], len(tr),
                                                                        meta["coins"][a]["sum_r"], time.time() - t0))
    np.savez_compressed(os.path.join(cache, "lead.npz"), **arrays)
    with open(os.path.join(cache, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1, default=float)
    del prep
    return meta


# ------------------------------------------------------------------------------------------------- analyse (light)
def coin_frame(coin, ddir, cache, z):
    """The bar-file frame of one coin: H107's readings, the Lead joined by time, the book's trades with the bar that
    decided each."""
    df, fund = h107.load(coin, ddir)
    fx = h107.features(df, fund)                                  # H107's own code, its registered settings
    t = fx["t"]
    st_t = pd.DatetimeIndex(pd.to_datetime(z["times_ms"], unit="ms", utc=True))
    lead = pd.Series(z["lead_" + coin], index=st_t).reindex(t).values.astype(float)
    tr = pd.read_csv(os.path.join(cache, "trades_%s.csv" % coin))
    dec_ms = z["times_ms"][tr.i_in.values.astype(int) - 1]        # the store row before the entry bar decided it
    bar_ms = data.to_ms(t)
    kd = np.searchsorted(bar_ms, dec_ms)
    assert (kd < len(bar_ms)).all() and np.array_equal(bar_ms[kd], dec_ms), "a deciding session has no bar"
    tr = tr.assign(coin=coin, kd=kd, dec_time=t[kd], r=tr.r_mult.astype(float))
    return {"df": df, "fund": fund, "fx": fx, "t": t, "lead": lead, "trades": tr}


def lookahead_guard(coin, fr, n_random=40, seed=SEED):
    """`features` recomputed on bars cut at each trigger bar (and some random bars): the flag must match."""
    fx, df, fund = fr["fx"], fr["df"], fr["fund"]
    t = fx["t"]
    k0 = int(t.searchsorted(pd.Timestamp(h107.START, tz="UTC")))
    rng = np.random.default_rng(seed)
    ks = sorted(set(int(k) for k in np.flatnonzero(fx["A"])) | set(int(k) for k in rng.integers(k0, len(t), n_random)))
    bad = []
    for k in ks:
        g = h107.features(df.iloc[:k + 1], fund.loc[:t[k] + pd.Timedelta(minutes=15)])
        if bool(g["A"][-1]) != bool(fx["A"][k]):
            bad.append(k)
    return {"bars_checked": len(ks), "n_mismatch": len(bad), "mismatches": bad[:20]}


def months_of(a, z):
    ms = pd.period_range(pd.Timestamp(a).to_period("M"), pd.Timestamp(z).to_period("M"), freq="M")
    return [p.year * 100 + p.month for p in ms]


def part_b(frames, segs, win=WIN, full=True):
    """The in-window split for the given segments. full: the descriptive read-outs too."""
    parts = []
    for coin, fr in frames.items():
        n = len(fr["t"])
        on = np.flatnonzero(fr["fx"]["A"])
        mask = window_mask(n, on, win)
        since = bars_since(n, on)
        tr = fr["trades"]
        parts.append(tr.assign(inwin=mask[tr.kd.values], since=since[tr.kd.values], lead_dec=fr["lead"][tr.kd.values],
                               seg=seg_array(pd.DatetimeIndex(tr.dec_time)),
                               month=[x.year * 100 + x.month for x in tr.dec_time]))
    tr = pd.concat(parts, ignore_index=True)
    tr = tr[tr.seg.isin(segs)]                                    # nothing outside the asked segments is split
    out = {}
    for seg in segs:
        cell = {"shorts": split_cell(tr, -1, seg)}
        if full:
            d = tr[(tr.side == -1) & (tr.seg == seg) & np.isfinite(tr.r)]
            a = d[d.inwin]
            first = pd.Timestamp({"h1": "2020-02-01", "h2": MID, "holdout": HOLDOUT, "event": EVENT}[seg])
            last = pd.Timestamp({"h1": MID, "h2": HOLDOUT, "holdout": EVENT, "event": "2026-11-25"}[seg]) - pd.Timedelta(minutes=15)
            cell["boot_diff"] = boot_diff(d, months_of(first, last)) if len(d) else None
            keys = set(zip(a.coin, a.month))
            same = d[(~d.inwin) & np.array([(c, m) in keys for c, m in zip(d.coin, d.month)], bool)]
            cell["others_same_coin_months"] = stats(same.r.values)
            cell["by_coin"] = dict((c, {"in": stats(d[d.inwin & (d.coin == c)].r.values),
                                        "out": stats(d[(~d.inwin) & (d.coin == c)].r.values)}) for c in COINS)
            cell["by_entry_word"] = dict((w, {"in": stats(d[d.inwin & (d.why_in == w)].r.values),
                                              "out": stats(d[(~d.inwin) & (d.why_in == w)].r.values)})
                                         for w in ("ENTER", "FORCED", "FLIP"))
            cell["first_24h"] = stats(a[a.since < 96].r.values)
            cell["second_24h"] = stats(a[a.since >= 96].r.values)
            cell["exit_words_in_window"] = dict((str(k), int(v)) for k, v in a.why_out.value_counts().items())
            cell["longs"] = split_cell(tr, 1, seg)
            ld = a.lead_dec.values.astype(float)
            cell["lead_at_entry_in_window"] = {
                "median": float(np.nanmedian(ld)) if len(ld) else None,
                "share_at_or_below_minus_5": float(np.mean(ld <= -LONG_BAR) * 100) if len(ld) else None}
        out[seg] = cell
    return out, tr


def part_a(frames):
    """Confirmed lows (hindsight) and the trigger-anchored yardstick, per coin and segment."""
    lows, trig, base, counts, cands = [], [], {}, {}, []
    for coin, fr in frames.items():
        fx, t, lead = fr["fx"], fr["t"], fr["lead"]
        ks, n_cand = confirmed_lows(t, fx["l"], fx["lowN"], fx["cref"], lead)
        counts[coin] = {"candidates": n_cand, "kept": int(len(ks))}
        for k in low_candidates(t, fx["l"], fx["lowN"], fx["cref"], lead):   # post hoc: without the 7-day rule
            cands.append(dict(anchor_row(coin, int(k), t, lead, fx["c"], fx["l"], anchor_px=float(fx["l"][k])),
                              kept=bool(k in set(ks))))
        for k in ks:
            lows.append(anchor_row(coin, int(k), t, lead, fx["c"], fx["l"], anchor_px=float(fx["l"][k])))
        on = np.flatnonzero(fx["A"])
        starts = [int(k) for i, k in enumerate(on) if i == 0 or k - on[i - 1] >= WIN]   # the trigger that opens a window
        for k in starts:
            if np.isfinite(lead[k]):
                trig.append(anchor_row(coin, k, t, lead, fx["c"], fx["l"]))
        seg = seg_array(t)
        mask = window_mask(len(t), on)
        fin = np.isfinite(lead)
        base[coin] = {}
        for s in SEGS:
            sel = fin & (seg == s)
            base[coin][s] = {"closes": int(sel.sum()),
                             "lead_below_0_pct": float(np.mean(lead[sel] < 0) * 100) if sel.any() else None,
                             "lead_at_or_above_long_bar_pct": float(np.mean(lead[sel] >= LONG_BAR) * 100) if sel.any() else None,
                             "triggers": int(sum(1 for k in on if seg[k] == s and fin[k])),
                             "window_starts": int(sum(1 for k in starts if seg[k] == s and fin[k])),
                             "closes_inside_a_window_pct": float(np.mean(mask[sel]) * 100) if sel.any() else None}
    cells = {}
    for name, rows in (("lows", lows), ("triggers", trig), ("candidates_posthoc", cands)):
        cells[name] = {}
        for s in SEGS:
            for c in ("both",) + COINS:
                cells[name]["%s_%s" % (s, c)] = summarise([r for r in rows if r["seg"] == s and (c == "both" or r["coin"] == c)])
        for c in ("both",) + COINS:                                  # the three test-free segments together
            cells[name]["history_%s" % c] = summarise([r for r in rows if r["seg"] != "event" and (c == "both" or r["coin"] == c)])
    cands = [dict((k, v) for k, v in r.items() if k != "hourly") for r in cands]   # the paths are in "lows" already
    return {"cells": cells, "lows": lows, "triggers": trig, "yardstick": base, "counts": counts,
            "candidates_posthoc": cands}


def journal_event(path, frames):
    """The live Lead around the 21 Nov 2026 lows, from the audit's copy of the journal (descriptive)."""
    if not path or not os.path.exists(path):
        return None
    rows = {}
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            r = json.loads(ln)
            if r.get("asset") in COINS and r.get("edge_pts") is not None:
                rows.setdefault(r["asset"], []).append((pd.Timestamp(r["time"], tz="UTC"), float(r["edge_pts"]), float(r["price"])))
    out = {}
    for coin, v in rows.items():
        fr = frames[coin]
        t, c = fr["t"], fr["fx"]["c"]
        s = pd.DataFrame(v, columns=["time", "lead", "price"]).drop_duplicates("time").set_index("time").sort_index()
        # is the journal's time the bar's open time or its close time? the price must be that bar's close
        same = pd.Series(c, index=t).reindex(s.index)
        prev = pd.Series(c, index=t + pd.Timedelta(minutes=15)).reindex(s.index)
        m_open = float(np.nanmean(np.isclose(same.values, s.price.values, rtol=1e-6)))
        m_close = float(np.nanmean(np.isclose(prev.values, s.price.values, rtol=1e-6)))
        shift = pd.Timedelta(0) if m_open >= m_close else pd.Timedelta(minutes=15)
        live = s.lead.copy()
        live.index = live.index - shift                           # now keyed by the bar's open time
        lead_live = live.reindex(t).values.astype(float)
        lows = [k for k in low_candidates(t, fr["fx"]["l"], fr["fx"]["lowN"], fr["fx"]["cref"], fr["lead"])
                if seg_of(t[k]) == "event"]                       # the event's lows: candidates, the 7-day rule aside
        on = [int(k) for k in np.flatnonzero(fr["fx"]["A"]) if seg_of(t[k]) == "event"]
        both = np.isfinite(lead_live) & np.isfinite(fr["lead"])
        out[coin] = {"journal_time_is": "bar open" if m_open >= m_close else "bar close",
                     "price_match_pct": round(max(m_open, m_close) * 100, 1),
                     "steps": int(np.isfinite(lead_live).sum()),
                     "live_first": str(live.index[0])[:16], "live_last": str(live.index[-1])[:16],
                     "live_lead_below_0_pct": float(np.mean(lead_live[np.isfinite(lead_live)] < 0) * 100),
                     "replay_vs_live": {"closes_with_both": int(both.sum()),
                                        "mean_abs_diff_pts": float(np.mean(np.abs(lead_live[both] - fr["lead"][both]))) if both.any() else None,
                                        "same_sign_pct": float(np.mean(np.sign(lead_live[both]) == np.sign(fr["lead"][both])) * 100) if both.any() else None,
                                        "corr": float(np.corrcoef(lead_live[both], fr["lead"][both])[0, 1]) if both.sum() > 2 else None},
                     "lows": [anchor_row(coin, int(k), t, lead_live, c, fr["fx"]["l"], anchor_px=float(fr["fx"]["l"][k])) for k in lows],
                     "triggers": [anchor_row(coin, int(k), t, lead_live, c, fr["fx"]["l"]) for k in on]}
    return out


def live_trades_event(audit_live, frames):
    """The live books' BTC and ETH trades decided from 19 Nov 2026 on, from the audit's copy (descriptive)."""
    if not audit_live or not os.path.isdir(audit_live):
        return None
    out = {}
    for book, pat in (("Setups (b_targets)", "shadow_trades_b_targets_%s.csv"), ("B trail", "shadow_trades_b_trail_%s.csv"),
                      ("main", "trades_%s.csv")):
        rows = []
        for coin in COINS:
            p = os.path.join(audit_live, pat % coin)
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p)
            fr = frames[coin]
            t = fr["t"]
            on = np.flatnonzero(fr["fx"]["A"])
            mask = window_mask(len(t), on)
            for r in d.itertuples():
                tin = pd.Timestamp(str(r.time_in)[:16], tz="UTC")
                dec = tin - pd.Timedelta(minutes=15)             # an entry is stamped with the close that decided it
                if dec < pd.Timestamp(EVENT, tz="UTC"):
                    continue
                kd = int(t.searchsorted(dec))
                rows.append({"coin": coin, "time_in": str(tin)[:16], "time_out": str(r.time_out)[:16], "side": int(r.side),
                             "why_in": r.why_in, "why_out": r.why_out, "p_in": float(r.p_in), "pnl_usd": float(r.pnl_usd),
                             "r": float(r.r_mult) if hasattr(r, "r_mult") and r.r_mult == r.r_mult else None,
                             "in_window": bool(kd < len(t) and t[kd] == dec and mask[kd])})
        out[book] = sorted(rows, key=lambda x: (x["time_in"], x["coin"]))
    return out


def analyse(ddir, cache, journal=None, audit_live=None, log=print):
    t0 = time.time()
    z = np.load(os.path.join(cache, "lead.npz"))
    with open(os.path.join(cache, "meta.json")) as fh:
        meta = json.load(fh)
    frames = dict((c, coin_frame(c, ddir, cache, z)) for c in COINS)
    res = {"registered": {"trigger": dict(h107.REG), "window_bars": WIN, "min_half": MIN_HALF, "min_holdout": MIN_HOLD,
                          "mid": MID, "holdout": HOLDOUT, "event": EVENT, "bootstrap": {"draws": B, "seed": SEED}},
           "store": meta, "files": dict((c.lower() + "_15m.csv", h107.md5(os.path.join(ddir, c.lower() + "_15m.csv")))
                                        for c in COINS)}
    end67 = int(pd.Timestamp("2026-11-21 13:45", tz="UTC").value // 10 ** 6) + BAR_MS      # H67/H68's last session's close
    rec = {}
    for c in COINS:
        d = frames[c]["trades"]
        d = d[d.t_out_ms <= end67]
        rec[c] = {"trades": int(len(d)), "sum_r": float(np.nansum(d.r.values))}
    res["reconcile_h67"] = dict(rec, both={"trades": sum(v["trades"] for v in rec.values()),
                                           "sum_r": sum(v["sum_r"] for v in rec.values())},
                                h67_record={"trades": 2074, "sum_r": -7.7, "BTCUSDT_sum_r": -66.9, "ETHUSDT_sum_r": 59.2})
    res["lookahead_guard"] = dict((c, lookahead_guard(c, frames[c])) for c in COINS)
    log("look-ahead guard: %s (%.0fs)" % (res["lookahead_guard"], time.time() - t0))
    res["part_a"] = part_a(frames)
    # ---- part (b): the halves first; the holdout only if both pass
    halves, tr_h = part_b(frames, ("h1", "h2"))
    word, checks = verdict(halves["h1"]["shorts"], halves["h2"]["shorts"])
    pb = {"halves": halves, "verdict": word, "checks": checks, "holdout_opened": word == "PASS"}
    if word == "PASS":
        ho, _ = part_b(frames, ("holdout",))
        c = ho["holdout"]["shorts"]
        ok = bool(c["in"]["n"] >= MIN_HOLD and c["in"]["mean_r"] < 0 and c["out"]["n"] and c["in"]["mean_r"] < c["out"]["mean_r"])
        pb["holdout"] = ho["holdout"]
        pb["holdout_confirms"] = ok
        pb["proposal_stands"] = ok
    else:
        pb["holdout"] = None                                      # not computed: sealed for this question
        pb["proposal_stands"] = False
    tr_y = tr_h if word != "PASS" else part_b(frames, ("h1", "h2", "holdout"), full=False)[1]
    d = tr_y[(tr_y.side == -1) & np.isfinite(tr_y.r)]
    pb["by_year_posthoc"] = dict((int(y), {"in": stats(g[g.inwin].r.values), "out": stats(g[~g.inwin].r.values)})
                                 for y, g in d.groupby(pd.DatetimeIndex(d.dec_time).year))
    pb["other_windows"] = {}
    for hours, w in (("24h", 96), ("96h", 384)):
        segs_o = ("h1", "h2") + (("holdout",) if word == "PASS" else ())
        alt, _ = part_b(frames, segs_o, win=w, full=False)
        pb["other_windows"][hours] = dict((s, alt[s]["shorts"]) for s in segs_o)
    res["part_b"] = pb
    # ---- the event apart (descriptive)
    ev, tr = part_b(frames, ("event",), full=False)
    d = tr[tr.seg == "event"].sort_values(["dec_time", "coin"])
    res["event"] = {"replay_cells": {"shorts": ev["event"]["shorts"], "longs": split_cell(tr, 1, "event")},
                    "replay_trades": [{"coin": r.coin, "decided_bar_open": str(r.dec_time)[:16], "side": int(r.side),
                                       "why_in": r.why_in, "why_out": r.why_out, "p_in": float(r.p_in), "r": float(r.r),
                                       "pnl_usd": float(r.pnl_usd), "in_window": bool(r.inwin),
                                       "lead_at_decision": None if r.lead_dec != r.lead_dec else float(r.lead_dec)}
                                      for r in d.itertuples()],
                    "replay_open_at_end": dict((c, meta["coins"][c]["end_state"]) for c in COINS),
                    "triggers": dict((c, [str(frames[c]["t"][k])[:16] for k in np.flatnonzero(frames[c]["fx"]["A"])
                                          if seg_of(frames[c]["t"][k]) == "event"]) for c in COINS),
                    "live_journal": journal_event(journal, frames), "live_trades": live_trades_event(audit_live, frames)}
    res["seconds_analyse"] = round(time.time() - t0, 1)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    log("part (b): %s %s" % (word, checks))
    for s in ("h1", "h2"):
        c = halves[s]["shorts"]
        log("  %s shorts in-window %s | others %s" % (s, c["in"], c["out"]))
    return res


# ------------------------------------------------------------------------------------------------- the report
def _n(x, f="%+.1f", none="-"):
    return none if x is None or x != x else f % x


def _hours(c, name):
    if not c.get("n"):
        return "-"
    m = c["%s_median_h" % name]
    return ("%.1f" % m) if m is not None else "more than 72"


def _cellb(c):
    return "-" if not c["n"] else "%d, %.0f%%, %+.3f, %+.1f" % (c["n"], c["won_pct"], c["mean_r"], c["sum_r"])


def _row_a(label, c, lows=True):
    if not c.get("n"):
        return "| %s | 0 | - | - | - | - | - |" % label
    px = "px_vs_low" if lows else "px_vs_close"
    return "| %s | %d | %s | %s | %.0f%% / %.0f%% / %.0f%% | %s / %s / %s | %s / %s / %s |" % (
        label, c["n"], _n(c["lead_at_median"]), _hours(c, "zero"),
        c["zero_within_24h_pct"], c["zero_within_48h_pct"], c["zero_within_72h_pct"],
        _n(c["down_at_24h_pct"], "%.0f%%"), _n(c["down_at_48h_pct"], "%.0f%%"), _n(c["down_at_72h_pct"], "%.0f%%"),
        _n(c["%s_24h_median" % px], "%+.1f%%"), _n(c["%s_48h_median" % px], "%+.1f%%"), _n(c["%s_72h_median" % px], "%+.1f%%"))


HDR_A = ["| %s | Events | Lead at the %s (median) | Hours until the Lead first favours up (median) | Turned up within 24h / 48h / 72h "
         "| Still favours down at +24h / +48h / +72h | Price against the %s at +24h / +48h / +72h (median) |",
         "|---|---|---|---|---|---|---|"]
HOURS = (-24, -12, -6, 0, 3, 6, 12, 18, 24, 36, 48, 60, 72)
SEG_SHORT = {"h1": "First half", "h2": "Second half", "holdout": "Holdout"}


def _yes(flag):
    return "yes" if flag else "NO"


def write_report(res, reg_commit="(see HYPOTHESES.md)"):
    pa, pb, ev = res["part_a"], res["part_b"], res["event"]
    st = res["store"]
    L = ["# H113: how fast the Lead turns after a capitulation low (BTC and ETH)", "",
         "Research only. Nothing in the engine, the books or the vault was changed. Registered in",
         "`research/HYPOTHESES.md` (H113, commit %s) before any number below was computed." % reg_commit, "",
         "This is a replay on history. A replay is post-mortem material. It is not validation, and nothing here shows",
         "that a reading or a rule has an edge.", ""]
    rd = os.path.join(OUT, "reading.md")
    if os.path.exists(rd):                                        # written by hand after the run
        with open(rd, encoding="utf-8") as fh:
            L += fh.read().replace("\r\n", "\n").rstrip("\n").split("\n") + [""]
    L += ["## Words", "",
         "- **Lead**: the engine's chance of \"up first\" minus its chance of \"down first\", in points. Above 0 it favours",
         "  up. Below 0 it favours down. From flat, the engine goes long by itself only at +5 points or more.",
         "- **Capitulation low**: a 15-minute low that is the lowest of the last 30 days, at least 10% under the price a",
         "  week earlier, and not undercut in the next 48 hours. It can only be named two days later (hindsight).",
         "- **Trigger**: H107's rule A, known at the time. A fresh 30-day low in the last 4 hours, 10% under a week",
         "  earlier, and a close that has bounced 2 x ATR(1h) off that low. ATR(1h) is the average size of a 1-hour bar.",
         "- **Window**: the 48 hours that start at a trigger's close.",
         "- **Setups book**: the paper book `b_targets`. **R**: a trade's result divided by what it risked at its stop,",
         "  after fees. +1R wins what was risked. -1R loses it.",
         "- **Segments**: first half (2020-02 to 2023-06-07), second half (2023-06-08 to 2025-11-10), holdout",
         "  (2025-11-11 to 2026-11-18, kept aside as a check), and the 21 Nov 2026 event, shown apart.", "",
         "Data: the laptop's copy of the box's data, sessions %s to %s. The Lead is the replay's Lead. It has no trust cap,"
         % (st["store_first"], st["store_last"]),
         "so it is close to the live Lead but not the same.", ""]
    # ---- verdict
    h1, h2 = pb["halves"]["h1"]["shorts"], pb["halves"]["h2"]["shorts"]
    ck = pb["checks"]
    L += ["## Verdict on the registered test (part b)", "",
          "**%s**" % ("The two halves PASS. The holdout %s. The proposal %s." % (
              "confirms" if pb.get("holdout_confirms") else "does NOT confirm",
              "stands" if pb["proposal_stands"] else "does not stand") if pb["verdict"] == "PASS" else pb["verdict"] + "."),
          "The claim was: shorts opened in the 48 hours after a trigger do worse than the book's other shorts.",
          "To pass, in EACH half the in-window shorts had to number at least %d, average below zero, and average below the"
          % MIN_HALF, "other shorts.", "",
          "| Check | First half | Second half |", "|---|---|---|",
          "| At least %d in-window shorts | %s (%d) | %s (%d) |" % (
              MIN_HALF, _yes(ck["h1_at_least_%d_in_window" % MIN_HALF]), h1["in"]["n"],
              _yes(ck["h2_at_least_%d_in_window" % MIN_HALF]), h2["in"]["n"]),
          "| Their mean R is below zero | %s (%s) | %s (%s) |" % (
              _yes(ck["h1_in_window_mean_r_below_0"]), _n(h1["in"]["mean_r"], "%+.3f"),
              _yes(ck["h2_in_window_mean_r_below_0"]), _n(h2["in"]["mean_r"], "%+.3f")),
          "| Their mean R is below the other shorts' | %s (%s vs %s) | %s (%s vs %s) |" % (
              _yes(ck["h1_in_window_below_others"]), _n(h1["in"]["mean_r"], "%+.3f"), _n(h1["out"]["mean_r"], "%+.3f"),
              _yes(ck["h2_in_window_below_others"]), _n(h2["in"]["mean_r"], "%+.3f"), _n(h2["out"]["mean_r"], "%+.3f")), ""]
    if pb["holdout_opened"]:
        c = pb["holdout"]["shorts"]
        L += ["Both halves passed, so the holdout was opened: in-window %s; others %s (trades, share won, mean R, sum of R)."
              % (_cellb(c["in"]), _cellb(c["out"])),
              "**The holdout %s.** %s" % ("confirms" if pb["holdout_confirms"] else "does NOT confirm",
                                          "The proposal for a forward paper shadow book stands." if pb["proposal_stands"]
                                          else "The proposal does not stand."), ""]
    else:
        L += ["The halves did not pass, so the holdout was NOT opened for this test. It stays sealed for this question.",
              "No proposal for a shadow book follows from this study.", ""]
    # ---- part a
    cl = pa["cells"]["lows"]
    L += ["## Part (a): the Lead after a confirmed capitulation low", "",
          "Descriptive. The lows are picked with hindsight, so this is a description and not a forecast.",
          "BTC and ETH mostly make their lows on the same days, so \"both\" is not twice the evidence.", ""]
    L += [HDR_A[0] % ("Segment, both coins", "low", "low"), HDR_A[1]]
    for s_ in ("h1", "h2", "holdout"):
        L.append(_row_a(SEG_NAMES[s_], cl["%s_both" % s_]))
    L.append(_row_a("All three together", cl["history_both"]))
    L.append(_row_a("BTC, all three", cl["history_BTCUSDT"]))
    L.append(_row_a("ETH, all three", cl["history_ETHUSDT"]))
    L.append(_row_a("Not registered: every candidate, no 7-day rule", pa["cells"]["candidates_posthoc"]["history_both"]))
    hb = cl["history_both"]
    if hb.get("n"):
        L += ["", "Candidates before the 7-day rule: %s. Kept: %s." % (
            ", ".join("%s %d" % (c[:3], pa["counts"][c]["candidates"]) for c in COINS),
            ", ".join("%s %d" % (c[:3], pa["counts"][c]["kept"]) for c in COINS)),
            "Events where the Lead never favoured up in 72 hours: %d of %d. Of those that turned, the median wait was %s hours."
            % (hb["zero_never_in_72h"], hb["n"], _n(hb["zero_median_h_of_those_that_turned"], "%.1f")),
            "The Lead reached the +5 points that a long from flat needs within 24h / 48h / 72h in %.0f%% / %.0f%% / %.0f%% of events."
            % (hb["long_bar_within_24h_pct"], hb["long_bar_within_48h_pct"], hb["long_bar_within_72h_pct"]),
            "Median share of the 72 hours after the low spent favouring down: %s. Median highest Lead in those 72 hours: %s points."
            % (_n(hb["share_of_72h_below_0_median"], "%.0f%%"), _n(hb["max_lead_72h_median"])),
            "Price at +72h was above the low bar's close in %s of events (at +24h: %s)." % (
                _n(hb.get("px_up_vs_close_72h_pct"), "%.0f%%"), _n(hb.get("px_up_vs_close_24h_pct"), "%.0f%%")), "",
            "The Lead's path around the low, all three segments, both coins (points; hour 0 is the low bar's close):", "",
            "| Hour | " + " | ".join("%+d" % x for x in HOURS) + " |", "|---|" + "---|" * len(HOURS)]
        for lab, key, f in (("Median Lead", "hourly_median", "%+.1f"), ("Lower quarter", "hourly_q25", "%+.1f"),
                            ("Upper quarter", "hourly_q75", "%+.1f"),
                            ("Share of events favouring down", "hourly_share_below_0", "%.0f%%")):
            L.append("| %s | " % lab + " | ".join(_n(hb[key][24 + x], f) for x in HOURS) + " |")
    L += ["", "Yardstick: how often the Lead favours down at ANY close, and how often it is at +5 or more:", "",
          "| Segment | BTC: below 0 | BTC: +5 or more | ETH: below 0 | ETH: +5 or more |", "|---|---|---|---|---|"]
    for s_ in SEGS:
        y = [pa["yardstick"][c][s_] for c in COINS]
        L.append("| %s | %s | %s | %s | %s |" % (SEG_NAMES[s_], _n(y[0]["lead_below_0_pct"], "%.0f%%"),
                                              _n(y[0]["lead_at_or_above_long_bar_pct"], "%.1f%%"),
                                              _n(y[1]["lead_below_0_pct"], "%.0f%%"),
                                              _n(y[1]["lead_at_or_above_long_bar_pct"], "%.1f%%")))
    ct = pa["cells"]["triggers"]
    L += ["", "Without hindsight: the same read-outs counted from the trigger that opens a window (price against the",
          "trigger's close, which can be undercut):", "",
          HDR_A[0] % ("Segment, both coins", "trigger", "trigger's close"), HDR_A[1]]
    for s_ in ("h1", "h2", "holdout"):
        L.append(_row_a(SEG_NAMES[s_], ct["%s_both" % s_], lows=False))
    L.append(_row_a("All three together", ct["history_both"], lows=False))
    L.append(_row_a("21 Nov 2026 (apart, replay Lead)", ct["event_both"], lows=False))
    # ---- part b
    L += ["", "## Part (b): the Setups book's shorts inside the window against its other shorts", "",
          "No look-ahead: the trigger is known at its close, and a short counts as in-window by the close that decided it.",
          "Each cell: trades, share won, mean R, sum of R. BTC and ETH together.", "",
          "| Segment | Shorts in the window | Other shorts | Difference in mean R [95% range] | Other shorts in the same coin-months |",
          "|---|---|---|---|---|"]
    segs_b = ["h1", "h2"] + (["holdout"] if pb["holdout_opened"] else [])
    cells = dict(pb["halves"], **({"holdout": pb["holdout"]} if pb["holdout_opened"] else {}))
    for s_ in segs_b:
        c = cells[s_]
        bd = c.get("boot_diff")
        L.append("| %s | %s | %s | %s | %s |" % (
            SEG_NAMES[s_], _cellb(c["shorts"]["in"]), _cellb(c["shorts"]["out"]),
            "-" if not bd else "%+.3f [%+.3f, %+.3f]" % (bd["obs"], bd["lo"], bd["hi"]),
            _cellb(c["others_same_coin_months"])))
    if not pb["holdout_opened"]:
        L.append("| %s | not opened | not opened | - | - |" % SEG_NAMES["holdout"])
    L += ["", "The 95% range comes from redrawing whole calendar months 10,000 times. A range that spans zero means the",
          "difference could be chance.", "", "Beside the test (descriptive, decides nothing):", "",
          "| Read-out | " + " | ".join(SEG_SHORT[x] for x in segs_b) + " |", "|---|" + "---|" * len(segs_b)]

    def _line(label, fn):
        L.append("| %s | " % label + " | ".join(fn(x) for x in segs_b) + " |")

    def _pair(c):
        return "%s / %s" % (_cellb(c["in"]), _cellb(c["out"]))
    for c_ in COINS:
        _line("%s shorts: in window / others" % c_[:3], lambda x, c_=c_: _pair(cells[x]["by_coin"][c_]))
    for w in ("ENTER", "FORCED", "FLIP"):
        _line("Shorts entered by %s: in window / others" % w, lambda x, w=w: _pair(cells[x]["by_entry_word"][w]))
    _line("In-window shorts, first 24 hours of the window", lambda x: _cellb(cells[x]["first_24h"]))
    _line("In-window shorts, second 24 hours", lambda x: _cellb(cells[x]["second_24h"]))
    _line("LONGS in the window / other longs (the mirror)", lambda x: _pair(cells[x]["longs"]))
    for hours in ("24h", "96h"):
        _line("Window of %s instead of 48: shorts in / others" % hours.replace("h", " hours"),
              lambda x, hours=hours: _pair(pb["other_windows"][hours][x]))
    _line("Median Lead when an in-window short was decided (points)", lambda x: _n(cells[x]["lead_at_entry_in_window"]["median"]))
    y = pa["yardstick"]
    _line("Triggers (BTC + ETH) / share of closes inside a window", lambda x: "%d / %.1f%%" % (
        sum(y[c][x]["triggers"] for c in COINS), np.mean([y[c][x]["closes_inside_a_window_pct"] for c in COINS])))
    L += ["", "Not registered, added after the run: the shorts by calendar year of the deciding bar"
          + (" (holdout included, since it was opened)." if pb["holdout_opened"] else " (first and second half only)."), "",
          "| Year | Shorts in the window | Other shorts |", "|---|---|---|"]
    for y_ in sorted(pb["by_year_posthoc"], key=int):
        c = pb["by_year_posthoc"][y_]
        L.append("| %s | %s | %s |" % (y_, _cellb(c["in"]), _cellb(c["out"])))
    rc = res["reconcile_h67"]
    L += ["", "Check against H67's record of the same book to 21 Nov 13:45 (2,074 trades, -7.7R; BTC -66.9R, ETH +59.2R):",
          "this run has %d trades, %+.1fR (BTC %+.1fR, ETH %+.1fR) closed by then." % (
              rc["both"]["trades"], rc["both"]["sum_r"], rc["BTCUSDT"]["sum_r"], rc["ETHUSDT"]["sum_r"])]
    g = res["lookahead_guard"]
    L += ["", "Look-ahead guard: the trigger was recomputed on bars cut at %d bars (every trigger bar and 40 random bars per"
          % sum(g[c]["bars_checked"] for c in COINS),
          "coin). Mismatches: %d." % sum(g[c]["n_mismatch"] for c in COINS)]
    # ---- the event
    trig_txt = []
    for c in COINS:
        ts_ = ["%s close" % str(pd.Timestamp(x) + pd.Timedelta(minutes=15))[5:16] for x in ev["triggers"][c]]
        trig_txt.append("%s at the %s" % (c[:3], ", ".join(ts_) if ts_ else "none"))
    L += ["", "## The 21 Nov 2026 event, apart (descriptive only)", "",
          "This event shaped H107's trigger and prompted this study. It is not part of any test.", "",
          "Triggers in the replay: " + "; ".join(trig_txt) + " (UTC).", ""]
    lj = ev.get("live_journal")
    L += ["| Coin | Lead used | Low (UTC) | Lead at the low | Hours until the Lead first favoured up "
          "| Still favours down at +24h / +48h / +72h | Highest Lead after the low | Price against the low at +24h / +48h / +72h |",
          "|---|---|---|---|---|---|---|---|"]

    def _ev_row(coin, kind, r):
        turn = ("%.2f" % r["to_zero_h"]) if r["to_zero_h"] is not None else "never in the %.1f hours seen" % r["hours_seen_after"]
        down = ["-" if r["down_at_%dh" % h] is None else ("yes" if r["down_at_%dh" % h] else "no") for h in (24, 48, 72)]
        px = [_n(r.get("px_vs_low_%dh" % h), "%+.1f%%") for h in (24, 48, 72)]
        return "| %s | %s | %s | %s | %s | %s | %s | %s |" % (coin[:3], kind, r["time"][5:], _n(r["lead_at"]), turn,
                                                         " / ".join(down), _n(r["max_lead_72h"]), " / ".join(px))
    ev_lows = [x for x in pa["candidates_posthoc"] if x["seg"] == "event"]
    for r in ev_lows:
        L.append(_ev_row(r["coin"], "replay", r))
    if lj:
        for coin in COINS:
            for r in lj.get(coin, {}).get("lows", []):
                L.append(_ev_row(coin, "live journal", r))
        L += ["", "Live journal against the replay over the live days: " + "; ".join(
            "%s %d closes with both, same sign %s, mean gap %s points, live Lead below 0 in %s of its steps" % (
                c[:3], lj[c]["replay_vs_live"]["closes_with_both"], _n(lj[c]["replay_vs_live"]["same_sign_pct"], "%.0f%%"),
                _n(lj[c]["replay_vs_live"]["mean_abs_diff_pts"], "%.1f"), _n(lj[c]["live_lead_below_0_pct"], "%.0f%%"))
            for c in COINS if c in lj) + "."]
    else:
        L += ["", "The audit's copy of the live journal was not on disk for this run, so only the replay Lead is shown."]
    for r in ev_lows:
        if not r["kept"]:
            before = [x["time"] for x in pa["lows"] if x["coin"] == r["coin"] and x["time"] < r["time"]]
            L += ["", "%s: the 21 Nov low is left out of part (a)'s tables by the 7-day rule (a confirmed low on %s was kept)."
                  % (r["coin"][:3], before[-1][:10] if before else "an earlier day")]
    L += ["", "Replay Setups book, trades decided from 19 Nov 2026 on:", "",
          "| Coin | Decided (bar open, UTC) | Side | Entry word | Exit | R | In a window | Lead at the decision |",
          "|---|---|---|---|---|---|---|---|"]
    for r in ev["replay_trades"]:
        L.append("| %s | %s | %s | %s | %s | %+.2f | %s | %s |" % (
            r["coin"][:3], r["decided_bar_open"][5:], "short" if r["side"] < 0 else "long", r["why_in"], r["why_out"], r["r"],
            "yes" if r["in_window"] else "no", _n(r["lead_at_decision"])))
    if ev.get("live_trades"):
        for book, rows in ev["live_trades"].items():
            L += ["", "Live %s book, BTC and ETH trades decided from 19 Nov 2026 on (the audit's copy of the box's files):" % book,
                  "", "| Coin | Entered (UTC) | Side | Entry word | Exit | Result | In a window |", "|---|---|---|---|---|---|---|"]
            for r in rows:
                L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                    r["coin"][:3], r["time_in"][5:], "short" if r["side"] < 0 else "long", r["why_in"], r["why_out"],
                    ("%+.2fR, " % r["r"] if r["r"] is not None else "") + "%+.0f USD" % r["pnl_usd"],
                    "yes" if r["in_window"] else "no"))
            inw = [r for r in rows if r["in_window"] and r["side"] < 0]
            L += ["", "Shorts in a window: %d, %d won, %+.0f USD." % (len(inw), sum(r["pnl_usd"] > 0 for r in inw),
                                                                    sum(r["pnl_usd"] for r in inw))]
    L += ["", "## Limits", "",
          "- A replay on history. The engine was fitted week by week on the past only, but the rules of the book were",
          "  shaped on this same history. Nothing here is a forward result.",
          "- Few separate events. The triggers come in clusters, and BTC and ETH fall together. Calendar months that hold",
          "  an in-window short: " + ", ".join("%s %d" % (SEG_SHORT[x].lower(), cells[x]["boot_diff"]["months_with_an_in_window_trade"])
                                              for x in segs_b if cells[x].get("boot_diff")) + ". A handful of sell-offs decides each number.",
          "- Part (a) picks its lows with hindsight. Price after the low looks good by construction.",
          "- The replay's Lead has no trust cap, so it is not the live Lead." + (
              " Over the live days it had the live Lead's sign at %.0f%% of closes and differed by %.1f points on average."
              % (np.mean([lj[c]["replay_vs_live"]["same_sign_pct"] for c in lj]),
                 np.mean([lj[c]["replay_vs_live"]["mean_abs_diff_pts"] for c in lj])) if lj else ""),
          "  Before 10 Nov 2026 there is no live Lead to compare with.",
          "- The trigger was shaped on the 21 Nov 2026 event (H107). That event is kept out of every test.",
          "- The holdout has now been read for this question. It cannot serve as a fresh check for a variant of it.",
          "- Part (b) splits the trades the book made. A book that skips some shorts would trade a different sequence",
          "  afterwards. That book was not replayed.",
          "- Fees are the book's own (0.10% a side). Funding is not charged or paid."]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "fits_today"))
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--cache", default=os.path.join(OUT, "cache"))
    ap.add_argument("--analyse", action="store_true", help="skip the build; analyse from the saved Lead and trades")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--journal", default=None, help="the audit's journal_slim.jsonl (the live Lead, for the event apart)")
    ap.add_argument("--audit-live", default=None, help="the audit's out/live folder (live trade files, for the event apart)")
    ap.add_argument("--reg-commit", default="(see HYPOTHESES.md)", help="the registration commit, quoted in the report")
    a = ap.parse_args(argv)
    if not a.analyse:
        build(a.fits_dir, a.cache)
    if not a.build_only:
        write_report(analyse(a.data_dir, a.cache, a.journal, a.audit_live), a.reg_commit)


if __name__ == "__main__":
    main()
