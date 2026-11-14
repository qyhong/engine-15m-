# -*- coding: utf-8 -*-
"""shadow -- paper shadow books for registered hypotheses (research/HYPOTHESES.md).

A shadow book trades a written rule on paper beside the main books, so the rule is graded
on what happens AFTER it was registered. Nothing here touches the main books.

H1, CPI follow-through (registered 10 Nov 2026): after a US CPI release bar closes, take the
side of its close at the next 15-minute open, if the bar moved at least 0.3% open to close;
stop beyond the release bar's far extreme; exit at the open 16 sessions (4 hours) after
entry. $10,000 a trade, 0.10% a side.

The book is recomputed from the bars and the calendar at every step, so it needs no state
of its own and can never drift from its rule.

    py -3 -m engine15 shadow
"""
import numpy as np
import pandas as pd

from . import data, econ
from .config import CFG

H1_REGISTERED = "2026-11-10"
H1_MIN_MOVE = 0.003
H1_HOLD = 16
STAKE = 10000.0


def h1_cpi(bars=None, assets=None):
    """-> one row per coin per CPI release since registration."""
    assets = assets or list(CFG["assets"])
    ev = econ.load_events()
    since = int(pd.Timestamp(H1_REGISTERED, tz="UTC").timestamp() * 1000)
    cpi = sorted(set(int(t) for t, title in zip(ev.ts_ms, ev.title) if "CPI" in str(title).upper() and t >= since))
    fee, rows = CFG["cost_side"], []
    for a in assets:
        df = (bars or {}).get(a)
        if df is None:
            df = data.load(a)
        ms = data.to_ms(df.index)
        o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
        waiting = False
        for ts in cpi:
            if waiting:                                             # only the next release is listed as waiting
                break
            i = int(np.searchsorted(ms, ts))
            base = {"hypothesis": "H1 CPI follow-through", "asset": a, "release_utc": str(pd.Timestamp(ts, unit="ms", tz="UTC"))[:16]}
            if i >= len(ms) or ms[i] != ts:
                waiting = True
                rows.append(dict(base, status="WAITING", note="the release bar has not printed yet"))
                continue
            if i + 1 >= len(ms):
                rows.append(dict(base, status="WAITING", note="the release bar closed; entry is at the next open"))
                continue
            move = c[i] / o[i] - 1.0
            if abs(move) < H1_MIN_MOVE:
                rows.append(dict(base, status="SKIPPED", release_move_pct=round(move * 100, 2),
                                 note="the release bar moved less than 0.3%"))
                continue
            side = 1 if move > 0 else -1
            entry, stop = o[i + 1], (l[i] if side > 0 else h[i])
            exit_px, why, j_out = None, None, None
            for j in range(i + 1, min(i + 1 + H1_HOLD, len(ms))):
                if (side > 0 and l[j] <= stop) or (side < 0 and h[j] >= stop):
                    exit_px, why, j_out = (min(o[j], stop) if side > 0 else max(o[j], stop)), "stop", j
                    break
            if exit_px is None and i + 1 + H1_HOLD < len(ms):
                exit_px, why, j_out = o[i + 1 + H1_HOLD], "4 hours", i + 1 + H1_HOLD
            row = dict(base, side="LONG" if side > 0 else "SHORT", release_move_pct=round(move * 100, 2),
                       entry_utc=str(df.index[i + 1])[:16], entry=round(float(entry), 2), stop=round(float(stop), 2),
                       stop_distance_pct=round(abs(stop - entry) / entry * 100, 2))
            if exit_px is None:
                mark = c[-1]
                gross = side * (mark - entry) / entry
                row.update(status="RUNNING", mark=round(float(mark), 2), pnl_pct=round((gross - fee) * 100, 2),
                           pnl_usd=round((gross - fee) * STAKE, 2), sessions_left=int(i + 1 + H1_HOLD - (len(ms) - 1)))
            else:
                gross = side * (exit_px - entry) / entry
                row.update(status="CLOSED", exit=round(float(exit_px), 2), exit_utc=str(df.index[j_out])[:16], exit_reason=why,
                           pnl_pct=round((gross - 2 * fee) * 100, 2), pnl_usd=round((gross - 2 * fee) * STAKE, 2))
            rows.append(row)
    return rows


def book(bars=None):
    rows = h1_cpi(bars)
    closed = [r for r in rows if r["status"] == "CLOSED"]
    return {"rows": rows, "closed": len(closed), "won": sum(1 for r in closed if r["pnl_usd"] > 0),
            "total_usd": round(sum(r["pnl_usd"] for r in closed), 2),
            "verdict_rule": "after 6 releases: keep only if 8 of 12 coin-rows are profitable and the mean is above +0.4%"}


def main(argv):
    b = book()
    for r in b["rows"]:
        print("%(asset)s  release %(release_utc)s  %(status)s" % r, {k: v for k, v in r.items()
                                                                    if k not in ("asset", "release_utc", "status", "hypothesis")})
    print("closed %d, won %d, total %+.2f USD. Verdict rule: %s" % (b["closed"], b["won"], b["total_usd"], b["verdict_rule"]))
