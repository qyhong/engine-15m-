# -*- coding: utf-8 -*-
"""H112: an entry bar set per market, for the six non-crypto markets where a 5-point Lead is out of reach. Research
only; registered in research/HYPOTHESES.md (H112) before any number on history. Every book is the engine's own
shadows.run_challenger("b_targets"); the bars are changed only through the cfg dict handed to it. Reads the evidence
store and the cached fits; changes nothing in the engine.

    py -3 -X utf8 research/h112_entry_bar_per_market.py --fits-dir fits_today
    py -3 -X utf8 research/h112_entry_bar_per_market.py --fits-dir fits_today --smoke     (fx only, made-up scale)
    py -3 -X utf8 research/h112_entry_bar_per_market.py --fits-dir fits_today --by-year   (unregistered extra, after the results)
    py -3 -X utf8 research/h112_entry_bar_per_market.py --fits-dir x --report-only        (report.md again from results.json)

report.md = the tables from results.json, then the extra look (extra_lead_by_period.json) and the hand-written reading
(reading.md) when those files are in the output folder.
"""
import argparse
import gc
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

OUT = os.path.join(ROOT, "research", "out", "h112_entry_bar_per_market")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
CRYPTO = ("BTCUSDT", "ETHUSDT")
SIX = ("XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")
CUT = "2026-11-24 04:30"                 # each group ends at its last stored session at or before this
# segments by session time, disjoint: [first, next segment's first)
EDGES = (("h1", None, "2023-06-08"), ("h2", "2023-06-08", "2025-11-11"), ("holdout", "2025-11-11", "2026-11-11"),
         ("forward", "2026-11-11", None))
SEGS = tuple(k for k, _a, _z in EDGES)
JUDGED = ("h2", "holdout", "forward")    # never h1: the bar is fitted there
BASE = {"theta_enter": 0.05, "theta_enter_shock": 0.10, "theta_flip": 0.10, "theta_counter": 0.15}   # as registered
BAR_PTS = 5.0                            # the engine's entry bar in points
FLOOR_PTS = 1.0                          # a fitted bar is never below this
PCTS = (50, 75, 90, 95, 99)
WORDS = ("ENTER", "FORCED", "FLIP")
RULES = ("current", "all_scaled", "enter_only")
MIN_CLASS = 30                           # leg 3: closed trades needed in each of ENTER and FORCED
DRAWS, SEED = 10000, 20261124112
SMOKE_SCALE = 0.5                        # --smoke only: a made-up scale (p* needs crypto); never a result
START = shadows.START_EQUITY


# ------------------------------------------------------------------------------------------------ pure parts (tested)
def lead_pts(odds):
    """The Lead in points per session: 100 x (P(up first) - P(down first)); NaN where there are no odds."""
    return 100.0 * (odds[:, labels.UP] - odds[:, labels.DOWN])


def seg_bounds(times, lo, n):
    """{segment: (a, z)}: sessions a .. z-1 of each segment, clipped to lo .. n. Disjoint, in order, covering lo .. n."""
    out = {}
    for k, first, nxt in EDGES:
        a = lo if first is None else int(times.searchsorted(pd.Timestamp(first, tz="UTC")))
        z = n if nxt is None else int(times.searchsorted(pd.Timestamp(nxt, tz="UTC")))
        a, z = min(max(a, lo), n), min(max(z, lo), n)
        out[k] = (a, max(a, z))
    return out


def lead_stats(x, bar=BAR_PTS):
    """Read-outs of |Lead| (points) over the steps given (NaN = no odds = not a step)."""
    x = np.abs(np.asarray(x, dtype=float))
    x = x[np.isfinite(x)]
    if not len(x):
        return {"steps": 0, "share_at_bar": None, "pct": dict((str(p), None) for p in PCTS), "max": None}
    return {"steps": int(len(x)), "share_at_bar": float((x >= bar).mean() * 100.0),
            "pct": dict((str(p), float(np.percentile(x, p))) for p in PCTS), "max": float(x.max())}


def share_at(x, bar):
    x = np.abs(np.asarray(x, dtype=float))
    x = x[np.isfinite(x)]
    return float((x >= bar).mean() * 100.0) if len(x) else None


def crypto_share(abs_leads, bar=BAR_PTS):
    """p*: the share (0..1) of steps with |Lead| >= bar over all the given markets' steps in one count."""
    x = np.concatenate([np.abs(np.asarray(v, dtype=float)) for v in abs_leads]) if len(abs_leads) else np.array([])
    x = x[np.isfinite(x)]
    if not len(x):
        raise RuntimeError("no crypto steps in h1: p* cannot be fitted")
    return float((x >= bar).mean())


def fit_bar(abs_lead_h1, p_star):
    """bar_m in points: the (1 - p*) quantile of the market's |Lead| over its h1 steps, rounded to 0.01, floor 1.00."""
    x = np.abs(np.asarray(abs_lead_h1, dtype=float))
    x = x[np.isfinite(x)]
    if not len(x):
        raise RuntimeError("no h1 steps: the bar cannot be fitted")
    q = float(np.quantile(x, min(max(1.0 - p_star, 0.0), 1.0)))
    return max(FLOOR_PTS, round(q, 2))


def rule_cfg(cfg, rule, scale):
    """The cfg for one rule: `current` unchanged; `all_scaled` the four bars times scale; `enter_only` theta_enter only."""
    for k, v in BASE.items():
        if abs(float(cfg[k]) - v) > 1e-12:
            raise RuntimeError("the config's %s is %r, not the registered %r" % (k, cfg[k], v))
    out = dict(cfg)
    if rule == "all_scaled":
        for k in BASE:
            out[k] = BASE[k] * scale
    elif rule == "enter_only":
        out["theta_enter"] = BASE["theta_enter"] * scale
    elif rule != "current":
        raise ValueError(rule)
    return out


def fall(eq):
    """Worst fall in percent of a marked-equity path that starts from START."""
    e = np.asarray(eq, dtype=float)
    e = np.concatenate([[START], e[np.isfinite(e)]])
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0)


def _rs(tr):
    r = tr.r_mult.values.astype(float)
    return r[np.isfinite(r)]


def by_word(tr):
    out = {}
    for w in WORDS:
        t = tr[tr.why_in == w]
        r = _rs(t)
        out[w] = {"trades": int(len(t)), "sum_r": float(r.sum()), "mean_r": float(r.mean()) if len(r) else None,
                  "n_r": int(len(r)), "won": float((t.pnl_usd > 0).mean() * 100.0) if len(t) else None}
    other = tr[~tr.why_in.isin(WORDS)]
    if len(other):
        raise RuntimeError("entry words not in %s: %s" % (WORDS, sorted(set(other.why_in))))
    return out


def book_stats(book, a, z, fresh):
    """Read-outs of one book over sessions a .. z-1 (trades by entry bar). fresh: the book started flat at a with START."""
    tr = book["trades"]
    tr = tr[(tr.i_in >= a) & (tr.i_in < z)]
    r = _rs(tr)
    eq = book["equity"][a:z]
    out = {"trades": int(len(tr)), "n_r": int(len(r)), "won_n": int((tr.pnl_usd > 0).sum()),
           "won": float((tr.pnl_usd > 0).mean() * 100.0) if len(tr) else None,
           "sum_r": float(r.sum()), "mean_r": float(r.mean()) if len(r) else None, "words": by_word(tr),
           "real_share": float((tr.why_in == "ENTER").mean() * 100.0) if len(tr) else None,
           "flat_pct": float((book["held"][a:z] == 0).mean() * 100.0) if z > a else None}
    if fresh:
        fin = eq[np.isfinite(eq)]
        out["net"] = float(fin[-1] - START) if len(fin) else 0.0
        out["worst_fall"] = fall(eq)
    return out


def pool(cells):
    """Pool per-market cells (book_stats) of one rule and segment: sums; mean R = pooled sum of R over pooled trades with R."""
    tr = sum(c["trades"] for c in cells)
    n_r = sum(c["n_r"] for c in cells)
    sr = sum(c["sum_r"] for c in cells)
    won = sum(c["won_n"] for c in cells)
    words = {}
    for w in WORDS:
        wn = sum(c["words"][w]["trades"] for c in cells)
        wr = sum(c["words"][w]["n_r"] for c in cells)
        ws = sum(c["words"][w]["sum_r"] for c in cells)
        words[w] = {"trades": wn, "n_r": wr, "sum_r": ws, "mean_r": ws / wr if wr else None}
    out = {"trades": tr, "n_r": n_r, "won_n": won, "won": won * 100.0 / tr if tr else None, "sum_r": sr,
           "mean_r": sr / n_r if n_r else None, "words": words,
           "real_share": words["ENTER"]["trades"] * 100.0 / tr if tr else None,
           "flat_pct": float(np.mean([c["flat_pct"] for c in cells if c["flat_pct"] is not None])) if cells else None}
    if all("net" in c for c in cells):
        out["net"] = sum(c["net"] for c in cells)
    return out


def months_between(t0, t1):
    """Every calendar month (UTC) from t0's to t1's, as 'YYYY-MM'."""
    return [str(p) for p in pd.period_range(pd.Timestamp(t0).tz_localize(None).to_period("M"),
                                            pd.Timestamp(t1).tz_localize(None).to_period("M"), freq="M")]


def month_sums(months, r, months_all):
    """Sum of R per calendar month of `months_all` (a month with no trade counts as zero)."""
    s = pd.Series(np.asarray(r, dtype=float), index=list(months)).groupby(level=0).sum() if len(r) else pd.Series(dtype=float)
    return np.array([float(s.get(m, 0.0)) for m in months_all])


def boot_diff(d, draws=DRAWS, seed=SEED):
    """Month-clustered bootstrap of a summed monthly difference: months drawn with replacement, 2.5th..97.5th percentile."""
    d = np.asarray(d, dtype=float)
    if len(d) < 2:
        return {"months": int(len(d)), "diff": float(d.sum()), "lo": None, "hi": None, "share_above_zero": None}
    rng = np.random.default_rng(seed)
    tot = np.empty(draws)
    for k0 in range(0, draws, 1000):
        idx = rng.integers(0, len(d), size=(min(1000, draws - k0), len(d)))
        tot[k0:k0 + len(idx)] = d[idx].sum(axis=1)
    return {"months": int(len(d)), "diff": float(d.sum()), "lo": float(np.percentile(tot, 2.5)),
            "hi": float(np.percentile(tot, 97.5)), "share_above_zero": float((tot > 0).mean() * 100.0)}


def verdict(pooled):
    """The registered pass condition on the pooled six-market cells {rule: {segment: cell}}."""
    cur, pri = pooled["current"], pooled["all_scaled"]
    w = pri["h2"]["words"]
    enough = w["ENTER"]["n_r"] >= MIN_CLASS and w["FORCED"]["n_r"] >= MIN_CLASS
    legs = {"sum_r_higher_h2": bool(pri["h2"]["sum_r"] > cur["h2"]["sum_r"]),
            "sum_r_higher_holdout": bool(pri["holdout"]["sum_r"] > cur["holdout"]["sum_r"]),
            "real_calls_beat_forced_h2": bool(enough and w["ENTER"]["mean_r"] > w["FORCED"]["mean_r"])}
    return {"legs": legs, "enough_trades_leg3": bool(enough), "passes": bool(all(legs.values()))}


# ------------------------------------------------------------------------------------------------------- the run
def group_end(g, assets):
    from engine15 import evcache
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, g, assets[0]))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (g, assets[0]))
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(pd.Timestamp(CUT, tz="UTC"), side="right"))
    return str(full[k - 1])[:16]


def _walkforward():
    """research/queue/walkforward.py by its path (the folder is no package, and `queue` is a standard-library name)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("h112_walkforward", os.path.join(ROOT, "research", "queue", "walkforward.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(fits_root, smoke=False, log=print):
    wf = _walkforward()
    fits_root = os.path.abspath(fits_root)
    t0 = time.time()
    said, say = [], log

    def log(x):                                             # keep every line (the loader's refit counts) in results.json
        said.append(str(x))
        say(x)
    out_dir = os.path.join(OUT, "smoke") if smoke else OUT
    groups = [x for x in GROUPS if x[0] == "fx"] if smoke else GROUPS
    res = {"smoke": bool(smoke), "cut": CUT, "segments": dict((k, [a, z]) for k, a, z in EDGES), "markets": {},
           "fit": {"bar_pts": {}, "scale": {}, "h1_steps": {}}}
    crypto_h1, curves, monthly = [], {}, {}
    p_star = None
    for g, assets in groups:
        prep = wf.prep_cut_lean(g, assets, os.path.join(fits_root, g), group_end(g, assets), log=log)
        times = prep["times"]
        n = len(times)
        for a in assets:
            lead = lead_pts(prep["odds"][a])
            ok = np.isfinite(lead)
            lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
            segs = seg_bounds(times, lo, n)
            aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
            m = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]],
                 "segment_sessions": dict((k, [str(times[s0])[:16], str(times[s1 - 1])[:16]] if s1 > s0 else None)
                                          for k, (s0, s1) in segs.items()),
                 "lead": dict((k, lead_stats(lead[s0:s1])) for k, (s0, s1) in segs.items())}
            m["lead"]["all"] = lead_stats(lead[lo:n])
            # step 1: the current Setups book as the engine runs it, one continuous book
            b = shadows.run_challenger("b_targets", prep, a, lo, n, aux=aux)
            m["current_continuous"] = dict((k, book_stats(b, s0, s1, fresh=False)) for k, (s0, s1) in segs.items())
            m["current_continuous"]["all"] = book_stats(b, lo, n, fresh=False)
            del b
            h1a, h1z = segs["h1"]
            if a in CRYPTO:
                crypto_h1.append(np.abs(lead[h1a:h1z]))
            if a in SIX:
                if smoke:
                    bar = round(BAR_PTS * SMOKE_SCALE, 2)
                else:
                    if p_star is None:
                        p_star = crypto_share(crypto_h1)
                        res["fit"]["p_star_pct"] = p_star * 100.0
                        res["fit"]["crypto_h1_steps"] = int(sum(np.isfinite(v).sum() for v in crypto_h1))
                        log("p* (BTC+ETH, h1, |Lead| >= 5): %.2f%% of %d steps" % (p_star * 100.0, res["fit"]["crypto_h1_steps"]))
                    bar = fit_bar(lead[h1a:h1z], p_star)
                scale = bar / BAR_PTS
                res["fit"]["bar_pts"][a], res["fit"]["scale"][a] = bar, scale
                res["fit"]["h1_steps"][a] = int(np.isfinite(lead[h1a:h1z]).sum())
                m["share_at_fitted_bar"] = dict((k, share_at(lead[s0:s1], bar)) for k, (s0, s1) in segs.items())
                m["books"] = {}
                for rule in RULES:
                    cfg = rule_cfg(prep["cfg"], rule, scale)
                    m["books"][rule] = {}
                    for k in JUDGED:
                        s0, s1 = segs[k]
                        if s1 - s0 < 2:
                            raise RuntimeError("%s: no sessions in %s" % (a, k))
                        bk = shadows.run_challenger("b_targets", prep, a, s0, s1, cfg=cfg, aux=aux)   # fresh, flat, $10,000
                        m["books"][rule][k] = book_stats(bk, s0, s1, fresh=True)
                        curves[(rule, k, a)] = pd.Series(bk["equity"][s0:s1], index=times[s0:s1])
                        tr = bk["trades"]
                        r = tr.r_mult.values.astype(float)
                        keep = np.isfinite(r)
                        mon = [str(pd.Timestamp(times[int(i)]).tz_localize(None).to_period("M")) for i in tr.i_in.values[keep]]
                        monthly[(rule, k, a)] = (mon, r[keep], months_between(times[s0], times[s1 - 1]))
                        del bk
                log("%s: bar %.2f pts (scale %.3f); %s (%.0fs)" % (a, bar, scale, "; ".join(
                    "%s %s" % (k, " / ".join("%d tr %+.1fR" % (m["books"][r_][k]["trades"], m["books"][r_][k]["sum_r"])
                                             for r_ in RULES)) for k in JUDGED), time.time() - t0))
            elif a in CRYPTO:
                log("%s: |Lead| >= 5 in h1 %.1f%% of steps (%.0fs)" % (a, m["lead"]["h1"]["share_at_bar"] or 0, time.time() - t0))
            res["markets"][a] = m
        del prep
        gc.collect()

    six = [a for a in SIX if a in res["markets"]]
    res["pooled"] = dict((rule, dict((k, pool([res["markets"][a]["books"][rule][k] for a in six])) for k in JUDGED))
                         for rule in RULES)
    for rule in RULES:
        for k in JUDGED:
            tot = pd.concat([curves[(rule, k, a)] for a in six], axis=1, sort=True).sort_index().ffill().fillna(START).sum(axis=1)
            e = np.concatenate([[START * len(six)], tot.values])
            res["pooled"][rule][k]["worst_fall"] = float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0)
    # step 1 pooled: the current continuous book's entries by word, six and crypto apart
    res["step1_pooled"] = {}
    for name, ms in (("six", six), ("crypto", [a for a in CRYPTO if a in res["markets"]])):
        if ms:
            res["step1_pooled"][name] = dict((k, pool([res["markets"][a]["current_continuous"][k] for a in ms]))
                                             for k in SEGS + ("all",))
    # descriptive: month-clustered bootstrap of (rule - current) sum of R, pooled six
    res["boot"] = {}
    for rule in ("all_scaled", "enter_only"):
        res["boot"][rule] = {}
        for k in ("h2", "holdout"):
            months_all = sorted(set(mm for a in six for mm in monthly[(rule, k, a)][2]))
            d = np.zeros(len(months_all))
            for a in six:
                d += month_sums(monthly[(rule, k, a)][0], monthly[(rule, k, a)][1], months_all)
                d -= month_sums(monthly[("current", k, a)][0], monthly[("current", k, a)][1], months_all)
            res["boot"][rule][k] = boot_diff(d)
    res["verdict"] = verdict(res["pooled"])
    res["seconds"] = round(time.time() - t0, 1)
    res["log"] = said
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res, out_dir)
    log("legs: %s -> %s (%.0fs)" % (res["verdict"]["legs"], "PASS" if res["verdict"]["passes"] else "does not pass",
                                    time.time() - t0))
    return res


# ---------------------------------------------------------------------------------------------------- the report
NAMES = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P 500",
         "WTI": "WTI", "BRENT": "Brent"}
SEG_NAMES = {"h1": "h1 (to 2023-06-07)", "h2": "h2 (2023-06-08 to 2025-11-10)", "holdout": "holdout (2025-11-11 to 2026-11-10)",
             "forward": "forward (2026-11-11 on)"}
RULE_NAMES = {"current": "current rule", "all_scaled": "all bars scaled (PRIMARY)", "enter_only": "entry bar only (secondary)"}
LIVE_MAX = {"XAUUSD": 4.6, "XAGUSD": 4.7, "USDJPY": 5.0, "SPX": 3.5, "WTI": 4.2, "BRENT": 4.5}


def _n(x, f="%.1f"):
    return "-" if x is None else f % x


def _r(x, f="%+.3f"):
    return "-" if x is None else (f % x) + "R"


def _wcell(c):
    return " | ".join("%d, %s, %s" % (c["words"][w_]["trades"], _r(c["words"][w_]["mean_r"]),
                                      _r(c["words"][w_]["sum_r"], "%+.1f")) for w_ in WORDS)


def _cell(c):
    if not c["trades"]:
        return "0 trades"
    return "%d, %s%%, %s%%, %s, %s, %s, %s%%" % (
        c["trades"], _n(c["real_share"], "%.0f"), _n(c["won"], "%.0f"), _r(c["sum_r"], "%+.1f"), _r(c["mean_r"]),
        _n(c.get("net"), "%+.0f"), _n(c.get("worst_fall")))


def write_report(res, out_dir):
    v, fit, mk = res["verdict"], res["fit"], res["markets"]
    six = [a for a in SIX if a in mk]
    L = ["# H112: an entry bar set per market, for the six non-crypto markets", ""]
    if res["smoke"]:
        L += ["**SMOKE RUN: fx only, a made-up scale. Nothing below is a result.**", ""]
    L += ["A replay on history. It is post-mortem material, not validation. Nothing live was changed.",
          "Registered in `research/HYPOTHESES.md` (H112) before any number on history was computed.",
          "The prior expectation was low: earlier studies (H65, H80, H82b, H92, H93) found that the book's entry word, its",
          "odds and its entry bar made little or no measurable difference on history.", "",
          "## Words", "",
          "- **Lead**: the engine's P(up first) minus P(down first), in points. |Lead| is its size, whichever way it points.",
          "- **Step**: one 15-minute session for which the engine had odds.",
          "- **Entry bar**: the Lead a side needs before the book enters by itself. Today it is 5 points on every market.",
          "- **Real call**: an entry made because the Lead cleared the entry bar (entry word ENTER).",
          "- **Forced entry**: after four flat sessions with no real call the book must enter, on the trend's side (FORCED).",
          "- **Flip**: leaving a held side for the other side (FLIP).",
          "- **R**: a trade's result after fees, divided by what it risked at its entry stop. +1R wins what was risked.",
          "- **Worst fall**: the deepest drop of the paper book from an earlier high, in percent.",
          "- **Segments**: h1 = up to 2023-06-07 (the bars are fitted here). h2 = 2023-06-08 to 2025-11-10.",
          "  Holdout = 2025-11-11 to 2026-11-10. Forward = 2026-11-11 to the end of the data (%s UTC)." % res["cut"], "",
          "## Verdict by the registered condition", "",
          "**The PRIMARY rule (all bars scaled) %s.**" % ("PASSES" if v["passes"] else "DOES NOT PASS")]
    cur, pri = res["pooled"]["current"], res["pooled"]["all_scaled"]
    w = pri["h2"]["words"]
    L += ["", "| Leg (pooled over the six markets) | Current rule | All bars scaled | Met |", "|---|---|---|---|",
          "| 1. Sum of R higher in h2 | %+.1fR | %+.1fR | %s |" % (cur["h2"]["sum_r"], pri["h2"]["sum_r"],
                                                               "yes" if v["legs"]["sum_r_higher_h2"] else "NO"),
          "| 2. Sum of R higher in the holdout | %+.1fR | %+.1fR | %s |" % (
              cur["holdout"]["sum_r"], pri["holdout"]["sum_r"], "yes" if v["legs"]["sum_r_higher_holdout"] else "NO"),
          "| 3. In the new book in h2, real calls have a higher mean R than forced entries | | real calls %s (%d trades), "
          "forced %s (%d trades) | %s |" % (_r(w["ENTER"]["mean_r"]), w["ENTER"]["trades"],
                                            _r(w["FORCED"]["mean_r"]), w["FORCED"]["trades"],
                                            "yes" if v["legs"]["real_calls_beat_forced_h2"] else "NO")]
    if not v["enough_trades_leg3"]:
        L += ["", "Leg 3 needs at least %d closed trades in each class. It did not have them." % MIN_CLASS]
    L += ["", "A pass would lead only to a proposal for a forward paper shadow book. It would never change a live book or the vault.",
          "", "## Step 1. Is the 5-point bar out of reach on history too?", "",
          "Share of steps with |Lead| at or above 5 points, per segment. Then the |Lead| reached in half of all steps (p50),",
          "and the levels passed in only 25%, 10%, 5% and 1% of steps (p75, p90, p95, p99), and the largest reading.", "",
          "| Market | Segment | Steps | Share at 5+ | p50 | p75 | p90 | p95 | p99 | Largest |", "|---|---|---|---|---|---|---|---|---|---|"]
    for a in [x for x in CRYPTO + SIX if x in mk]:
        for k in SEGS:
            s = mk[a]["lead"][k]
            L.append("| %s | %s | %d | %s%% | %s | %s |" % (
                NAMES[a], k, s["steps"], _n(s["share_at_bar"], "%.2f"),
                " | ".join(_n(s["pct"][str(p)], "%.2f") for p in PCTS), _n(s["max"], "%.2f")))
    L += ["", "Live, 10 to 24 Nov 2026 (from the audit, already known): the largest reading was gold 4.6, silver 4.7, USDJPY 5.0,",
          "S&P 3.5, WTI 4.2, Brent 4.5. The replay's forward rows above cover nearly the same days.", "",
          "### The current Setups book's entries, by how they were made", "",
          "One continuous book per market, as the engine runs it. Each cell: real calls / forced / flips (share that are real calls).",
          "", "| Market | h1 | h2 | holdout | forward |", "|---|---|---|---|---|"]

    def ent(c):
        return "-" if not c["trades"] else "%d / %d / %d (%s%%)" % (
            c["words"]["ENTER"]["trades"], c["words"]["FORCED"]["trades"], c["words"]["FLIP"]["trades"],
            _n(c["real_share"], "%.0f"))
    for a in [x for x in CRYPTO + SIX if x in mk]:
        L.append("| %s | %s |" % (NAMES[a], " | ".join(ent(mk[a]["current_continuous"][k]) for k in SEGS)))
    for name, lab in (("crypto", "BTC + ETH"), ("six", "The six")):
        if name in res["step1_pooled"]:
            L.append("| **%s** | %s |" % (lab, " | ".join(ent(res["step1_pooled"][name][k]) for k in SEGS)))
    L += ["", "The same book's result by entry word, pooled (trades, mean R, sum of R). Descriptive.", "",
          "| Markets | Segment | Real calls | Forced | Flips |", "|---|---|---|---|---|"]
    for name, lab in (("crypto", "BTC + ETH"), ("six", "The six")):
        if name in res["step1_pooled"]:
            for k in SEGS:
                c = res["step1_pooled"][name][k]
                L.append("| %s | %s | %s |" % (lab, k, _wcell(c)))
    L += ["", "## Step 2. The fitted bars (h1 only)", ""]
    if res["smoke"]:
        L += ["SMOKE: scale %.2f, made up." % SMOKE_SCALE, ""]
    else:
        L += ["On BTC and ETH together, |Lead| was at or above 5 points in **%.2f%%** of h1 steps (%d steps)." % (
            fit["p_star_pct"], fit["crypto_h1_steps"]),
            "Each market's bar is the |Lead| it reached in that same share of its own h1 steps (never below 1.00 point).",
            "The other bars move by the same factor: the high-risk entry bar (10 points today), the flip bar (10) and the bar",
            "for an entry against the higher-timeframe trend (15).", ""]
    L += ["| Market | Fitted entry bar | Factor | High-risk bar | Flip bar | Counter-trend bar | Share of steps at or above the fitted bar: h1 / h2 / holdout / forward |",
          "|---|---|---|---|---|---|---|"]
    for a in six:
        s = fit["scale"][a]
        sh = mk[a]["share_at_fitted_bar"]
        L.append("| %s | %.2f | %.3f | %.2f | %.2f | %.2f | %s |" % (
            NAMES[a], fit["bar_pts"][a], s, 10 * s, 10 * s, 15 * s, " / ".join(_n(sh[k], "%.1f") + "%" for k in SEGS)))
    cs = [a for a in CRYPTO if a in mk]
    if cs:
        L += ["", "For comparison, the share of steps at 5+ points on crypto: " + "; ".join(
            "%s %s" % (NAMES[a], " / ".join(_n(mk[a]["lead"][k]["share_at_bar"], "%.1f") + "%" for k in SEGS)) for a in cs)
            + " (h1 / h2 / holdout / forward)."]
    L += ["", "## Step 2. The replay, pooled over the six markets", "",
          "Each book starts flat with $10,000 per market at the start of its segment. h1 is not compared: the bars were fitted there.",
          "Each cell: trades, share that are real calls, share won, sum of R, mean R, net dollars (six books), worst fall (six books summed).",
          "", "| Rule | h2 | holdout | forward |", "|---|---|---|---|"]
    for rule in RULES:
        L.append("| %s | %s |" % (RULE_NAMES[rule], " | ".join(_cell(res["pooled"][rule][k]) for k in JUDGED)))
    L += ["", "By entry word (trades, mean R, sum of R):", "", "| Rule | Segment | Real calls | Forced | Flips |", "|---|---|---|---|---|"]
    for rule in RULES:
        for k in JUDGED:
            c = res["pooled"][rule][k]
            L.append("| %s | %s | %s |" % (RULE_NAMES[rule], k, _wcell(c)))
    L += ["", "### How much of the difference could be noise (descriptive, not part of the verdict)", "",
          "Difference in sum of R against the current rule. The range comes from redrawing the calendar months 10,000 times.",
          "A range that spans zero means the difference cannot be told from chance on this history.", "",
          "| Rule | Segment | Months | Difference | 95% range | Share of redraws above zero |", "|---|---|---|---|---|---|"]
    for rule in ("all_scaled", "enter_only"):
        for k in ("h2", "holdout"):
            b = res["boot"][rule][k]
            L.append("| %s | %s | %d | %+.1fR | %s to %s | %s%% |" % (RULE_NAMES[rule], k, b["months"], b["diff"],
                                                                 _n(b["lo"], "%+.1f"), _n(b["hi"], "%+.1f"),
                                                                 _n(b["share_above_zero"], "%.0f")))
    L += ["", "## Per market", "",
          "Each cell: trades, share that are real calls, share won, sum of R, mean R, net dollars, worst fall.", "",
          "| Market | Rule | h2 | holdout | forward |", "|---|---|---|---|---|"]
    for a in six:
        for rule in RULES:
            L.append("| %s | %s | %s |" % (NAMES[a], RULE_NAMES[rule], " | ".join(_cell(mk[a]["books"][rule][k]) for k in JUDGED)))
    L += ["", "## Limits", "",
          "- This is a replay on history. It cannot prove that any rule has an edge.",
          "- The six markets share days and trends. Their trades are not independent, so the totals rest on fewer separate bets than the counts suggest.",
          "- The holdout was already read by earlier studies of this book (H65, H67, H68, H72). It is not a sealed test.",
          "- The forward segment is about two weeks. Its numbers are too few to mean anything.",
          "- The bar is fitted from how often the Lead is large, not from whether large Leads were right.",
          "- The replay's odds come from the engine's own walk of weekly refits. Most were read from the cache. The last year's fits for BTC, ETH",
          "  and USDJPY were not in it and were refitted on the laptop by the same code. The odds can differ a little from what",
          "  the live engine printed.",
          "- Each compared book starts fresh at its segment. A book carried over from 2020 would differ slightly at the joins.",
          "- Fees are the engine's paper fees. Funding and slippage are not charged."]
    extra = os.path.join(out_dir, "extra_lead_by_period.json")
    if os.path.exists(extra):                                # the unregistered look (--by-year), after the results
        with open(extra, encoding="utf-8") as fh:
            ex = json.load(fh)["markets"]
        years = sorted(set(y for m in ex.values() for y in m["year"]))
        L += ["", "## Extra look, NOT registered, made after the results: the 5-point bar year by year", "",
              "Share of steps with |Lead| at or above 5 points in each calendar year, and the last step that reached it.",
              "Descriptive only. It changes no verdict.", "",
              "| Market | %s | Last step at 5+ (UTC) |" % " | ".join(years), "|---|%s---|" % ("---|" * len(years))]
        for a in [x for x in SIX if x in ex]:
            L.append("| %s | %s | %s |" % (NAMES[a], " | ".join(
                (_n(ex[a]["year"][y]["share_at_bar"], "%.1f") + "%") if y in ex[a]["year"] else "-" for y in years),
                ex[a]["last_step_at_bar"] or "never"))
        oil = [a for a in ("WTI", "BRENT") if a in ex]
        if oil:
            mos = sorted(ex[oil[0]]["month_2026"])
            L += ["", "Oil in 2026, month by month:", "", "| Market | %s |" % " | ".join(mos), "|---|%s" % ("---|" * len(mos))]
            for a in oil:
                L.append("| %s | %s |" % (NAMES[a], " | ".join(_n(ex[a]["month_2026"][m_]["share_at_bar"], "%.1f") + "%" for m_ in mos)))
    reading = os.path.join(out_dir, "reading.md")
    if os.path.exists(reading):                              # written by hand after the run; kept beside the numbers
        with open(reading, encoding="utf-8") as fh:
            L += ["", fh.read().rstrip("\n")]
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def by_year(fits_root, log=print):
    """ADDED AFTER THE RESULTS, NOT REGISTERED, descriptive only: the share of steps with |Lead| >= 5 points per calendar
    year (and per month of 2026) on the six markets. Written to extra_lead_by_period.json; changes no result."""
    wf = _walkforward()
    fits_root = os.path.abspath(fits_root)
    out = {"note": "not registered; computed after the H112 results; descriptive", "bar_pts": BAR_PTS, "markets": {}}
    for g, assets in [x for x in GROUPS if x[0] != "crypto"]:
        prep = wf.prep_cut_lean(g, assets, os.path.join(fits_root, g), group_end(g, assets), log=log)
        times = prep["times"]
        n = len(times)
        for a in assets:
            lead = np.abs(lead_pts(prep["odds"][a]))
            ok = np.isfinite(lead)
            lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
            s = pd.Series(lead[lo:n], index=times[lo:n].tz_localize(None)).dropna()
            yr = s.groupby(s.index.year)
            m26 = s[s.index.year == 2026]
            mo = m26.groupby(m26.index.to_period("M"))
            out["markets"][a] = {
                "year": dict((str(k), {"steps": int(len(v)), "share_at_bar": float((v >= BAR_PTS).mean() * 100.0),
                                       "p95": float(np.percentile(v, 95)), "max": float(v.max())}) for k, v in yr),
                "month_2026": dict((str(k), {"steps": int(len(v)), "share_at_bar": float((v >= BAR_PTS).mean() * 100.0),
                                             "p95": float(np.percentile(v, 95)), "max": float(v.max())}) for k, v in mo),
                "last_step_at_bar": str(s.index[np.where(s.values >= BAR_PTS)[0][-1]])[:16] if (s.values >= BAR_PTS).any() else None}
            log("%s: %s; last step at 5+: %s" % (a, " ".join("%s %.1f%%" % (k, v["share_at_bar"])
                                                             for k, v in out["markets"][a]["year"].items()),
                                               out["markets"][a]["last_step_at_bar"]))
            log("   2026 by month: %s" % " ".join("%s %.1f%%" % (k[5:], v["share_at_bar"])
                                                  for k, v in out["markets"][a]["month_2026"].items()))
        del prep
        gc.collect()
    with open(os.path.join(OUT, "extra_lead_by_period.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=float)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--by-year", action="store_true", help="the unregistered descriptive extra, after the results")
    ap.add_argument("--report-only", action="store_true", help="rewrite report.md from results.json (no data is read)")
    a = ap.parse_args(argv)
    if a.report_only:
        with open(os.path.join(OUT, "results.json"), encoding="utf-8") as fh:
            write_report(json.load(fh), OUT)
    elif a.by_year:
        by_year(a.fits_dir)
    else:
        run(a.fits_dir, smoke=a.smoke)


if __name__ == "__main__":
    main()
