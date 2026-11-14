# -*- coding: utf-8 -*-
"""scorecard -- grade every trade on HOW it was taken, not only on which side it took.

WHY (owner, 10 Nov 2026): "The idea of this experiment is not just test AI engine able to do
long/short/flat call. Also test and improve its trade setup. How to make a good and fast
entry to the directional call ... Propose a framework to score this."

Five parts, each 0 to 100, measured from the bars the trade lived through. One "unit" is the
engine's own yardstick: 1.5 x the 1-hour ATR at the decision.

  DIRECTION  was the side right?  100 = price went one unit its way before one unit against
             (the same grade the calls get), 50 = neither, 0 = wrong.
  ENTRY      how good was the fill?  Where the fill sat in the range of the 2 hours after it:
             100 = it bought the low (sold the high) of those 2 hours, 0 = the worst price.
  SPEED      how fast did it work?  Sessions until the trade was half a unit in profit:
             100 = within 1 hour, falling to 0 at 8 hours or never.
  EXIT       how much of the move was kept?  Realised move as a share of the best the trade
             ever showed (its maximum favourable excursion). 100 = out at the best price.
  RISK       how much heat did it take?  The worst move against it: 100 = none,
             0 = two units or more (the stop).

  TRADE SCORE = 35% direction + 25% entry + 10% speed + 20% exit + 10% risk.

The score is for comparing: this month against last month, one entry method against another,
entries made by choice against entries forced by the mandate. It is not a profit number.

    py -3 -m engine15 scorecard            the replay's trades, by how they were opened
    py -3 -m engine15 scorecard live       the live paper trades so far
"""
import sys

import numpy as np
import pandas as pd

WEIGHTS = {"direction": 0.35, "entry": 0.25, "speed": 0.10, "exit": 0.20, "risk": 0.10}
ENTRY_WINDOW = 8            # sessions after the fill that define "the price available": 2 hours
SPEED_FAST, SPEED_SLOW = 4, 32


def score_one(side, i_in, i_out, p_in, p_out, high, low, unit, grade):
    """One closed trade -> its measurements and its five part scores. grade: 1 up-first, 2 down-first,
    0 neither, at the decision that opened it (labels.py)."""
    hi, lo = high[i_in:i_out + 1], low[i_in:i_out + 1]
    fav = (hi.max() - p_in) if side > 0 else (p_in - lo.min())
    adv = (p_in - lo.min()) if side > 0 else (hi.max() - p_in)
    real = side * (p_out - p_in)
    w_hi, w_lo = high[i_in:i_in + ENTRY_WINDOW].max(), low[i_in:i_in + ENTRY_WINDOW].min()
    span = max(w_hi - w_lo, 1e-12)
    entry_eff = (w_hi - p_in) / span if side > 0 else (p_in - w_lo) / span
    run = (hi - p_in) if side > 0 else (p_in - lo)
    hit = np.where(run >= 0.5 * unit)[0]
    t_half = int(hit[0]) + 1 if len(hit) else None
    speed = 0.0 if t_half is None else float(np.clip((SPEED_SLOW - t_half) / (SPEED_SLOW - SPEED_FAST), 0, 1))
    right = (grade == 1 and side > 0) or (grade == 2 and side < 0)
    direction = 100.0 if right else 50.0 if grade == 0 else 0.0
    exit_eff = float(np.clip(real / fav, 0, 1)) if fav > 0 else 0.0
    parts = {"direction": direction, "entry": 100.0 * float(np.clip(entry_eff, 0, 1)), "speed": 100.0 * speed,
             "exit": 100.0 * exit_eff, "risk": 100.0 * float(1 - min(adv / (2 * unit), 1))}
    parts["score"] = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    parts.update(mfe_units=fav / unit, mae_units=adv / unit, realised_units=real / unit,
                 sessions_to_half_unit=t_half, sessions_held=int(i_out - i_in))
    return parts


def score_book(trades, px, unit, grades):
    """trades: a book's trades frame (i_in, i_out, side, p_in, p_out, why_in, why_out).
    -> the same rows with the scorecard columns added (open trades left out)."""
    rows = []
    t = trades[(trades.why_out != "OPEN") & (trades.i_in > 0)]
    for r in t.itertuples():
        u = unit[r.i_in - 1]
        if not (u > 0):
            continue
        s = score_one(int(r.side), int(r.i_in), int(r.i_out), r.p_in, r.p_out, px["high"], px["low"], u, int(grades[r.i_in - 1]))
        rows.append(dict(s, i_in=int(r.i_in), side=int(r.side), why_in=r.why_in, why_out=r.why_out, pnl_pct=r.pnl_pct))
    return pd.DataFrame(rows)


def summary(scored, by="why_in"):
    cols = ["score", "direction", "entry", "speed", "exit", "risk", "mfe_units", "mae_units", "realised_units", "pnl_pct"]
    g = scored.groupby(by)[cols].mean().round(1)
    g.insert(0, "trades", scored.groupby(by).size())
    return g


def main(argv):
    from . import journal
    store = journal.load_store("replay")
    cfg = store["cfg"]
    pd.set_option("display.width", 220)
    allrows = []
    for a in store["assets"]:
        unit = (cfg["barrier_atr"] * store["ev"][a]["atr1h"]).values
        sc = score_book(store["books"][a]["trades"], store["px"][a], unit, store["y"][a])
        sc.insert(0, "asset", a)
        allrows.append(sc)
    sc = pd.concat(allrows, ignore_index=True)
    sc["year"] = store["times"][sc.i_in.values].year
    print("TRADE SCORECARD, history replay (%d closed trades). Parts are 0-100; units = 1.5 x ATR(1h)." % len(sc))
    print("\nBy how the trade was opened:")
    print(summary(sc, "why_in").to_string())
    print("\nBy how it was closed:")
    print(summary(sc, "why_out").to_string())
    print("\nBy coin:")
    print(summary(sc, "asset").to_string())
    import json
    import os
    from .config import OUT_DIR
    cols = ["score", "direction", "entry", "speed", "exit", "risk"]
    with open(os.path.join(OUT_DIR, "replay", "scorecard.json"), "w", encoding="utf-8") as fh:
        json.dump({"trades": int(len(sc)), "parts": dict((k, round(float(sc[k].mean()), 1)) for k in cols),
                   "weights": WEIGHTS, "version": cfg["version"]}, fh)
    print("\nBy year:")
    print(summary(sc, "year")[["trades", "score", "direction", "entry", "speed", "exit", "risk"]].to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
