# -*- coding: utf-8 -*-
"""Charter item E (cheaper fills): would limit (maker) orders make the SAME trades pay more?

The replay's paper book fills every entry and every exit at the next 15m bar's open as a
market order and charges 0.10% a side. This study keeps the replay's trades exactly as the
engine decided them (side, decision bar, exit reason, stop level) and re-fills each one under
other order policies, counting fees saved, better prices AND trades missed.

THE TRADES
  out/replay/trades_<ASSET>.csv. Each row carries time_in / time_out (written by
  backtest.save_run from the replay's common index), so a trade is located on the coin's own
  15m bars by timestamp. Check: p_in equals that bar's open for every trade (tested).
  The decision was made at the close of bar j_in - 1; the incumbent filled at open[j_in].

THE FILL POLICIES (an order is placed at the open of the bar the incumbent filled on)
  market            fill at that open, taker fee
  limit(k, N, T)    buy limit at  open - k x ATR15  (sell limit at open + k x ATR15), where
                    ATR15 is Wilder ATR(14) of 15m bars at the DECISION bar (j - 1): known.
                    Filled only if a bar in the window trades STRICTLY through the price
                    (low < limit for a buy, high > limit for a sell): touching is not enough,
                    a crude allowance for queue position. Fill price = the limit (no gap bonus).
                    The window is the order bar and the next N - 1 bars.
                    T = skip: not filled -> the entry is dropped (the trade is missed).
                    T = chase: not filled -> market at the open after the window, taker fee.
  Exits: STOP exits stay market at the incumbent's price (same bar, same level). Flip exits
  may be limits; an exit cannot be skipped, so an unfilled exit always chases. While an exit
  limit waits, the position is still open and its stop is still live; if the stop level and
  the limit are both reached in one bar the stop is assumed to come first (worst case).
  An entry still unfilled when the incumbent's own exit is decided is cancelled (missed).

STOP LEVEL: the incumbent's (fill - side x stop_units x barrier_atr x ATR1h at the decision
bar). It is kept at the same price whatever the new entry, so a trade lives exactly as long as
the replay's did and only its prices and fees change. Reconstructed and checked against the
replay's stop exits (tested).

FEES (Binance, regular tier, a side)
  spot      taker 0.10%  maker 0.10%     (the incumbent assumption)
  spot_bnb  taker 0.075% maker 0.075%    (fees paid in BNB, 25% off)
  perp      taker 0.05%  maker 0.02%     (USD-M futures; the perp's funding IS charged, from
                                          data/<asset>_funding.csv, for every 8h settlement held)

Money: every trade at a fixed $10,000 notional (fees and P&L in dollars), plus the compounding
return of a $10,000 book at full size, as the replay does. Drawdown is on closed-trade equity.

    py -3 research/fills.py           (writes out/fills/fills_grid.csv and out/fills/summary.json)
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, indicators as ind  # noqa: E402
from engine15.config import CFG, OUT_DIR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTIONAL = 10000.0
SPLIT = "2023-06-06"                          # the middle of 2020-01-01 .. 2026-11-10
FEES = {"spot": {"taker": 0.0010, "maker": 0.0010},
        "spot_bnb": {"taker": 0.00075, "maker": 0.00075},
        "perp": {"taker": 0.0005, "maker": 0.0002}}
MARKET = {"kind": "market"}
KS, NS = (0.0, 0.1, 0.25, 0.5), (1, 2, 4)


def limit(k, n, timeout="chase"):
    return {"kind": "limit", "k": float(k), "n": int(n), "timeout": timeout}


CANDIDATE_EXIT = limit(0.25, 4, "chase")      # the rule docs/FILLS.md proposes to register (chosen after the grid)


def name(pol):
    if pol["kind"] == "market":
        return "market"
    return "limit k%.2f N%d %s" % (pol["k"], pol["n"], pol["timeout"])


# ---------------------------------------------------------------- inputs

def bars_arrays(bars, funding=None):
    """15m bars -> the arrays the fills need. ATR15 and ATR1h at row j use bars <= j only.
    fund[j] = the sum of perp funding rates SET at or before bar j's open (0 without a file):
    a position held from bar a to bar b pays side x (fund[b] - fund[a]) of its notional."""
    h1 = data.resample(bars, "1h")
    fund = np.zeros(len(bars))
    if funding is not None and len(funding):
        cum = np.cumsum(funding.values)
        k = funding.index.searchsorted(bars.index, side="right")
        fund = np.where(k > 0, cum[np.maximum(k - 1, 0)], 0.0)
    return {"times": bars.index, "o": bars["open"].values, "h": bars["high"].values, "l": bars["low"].values,
            "c": bars["close"].values, "atr15": ind.atr_wilder(bars).values,
            "atr1h": data.htf_on_15(bars, "1h", ind.atr_wilder(h1)).values, "fund": fund}


def load_trades(asset, path=None):
    tr = pd.read_csv(path or os.path.join(OUT_DIR, "replay", "trades_%s.csv" % asset))
    tr["time_in"] = pd.to_datetime(tr["time_in"], utc=True)
    tr["time_out"] = pd.to_datetime(tr["time_out"], utc=True)
    return tr


def locate(trades, px, cfg=CFG):
    """Put each replay trade on the coin's own bars: j_in, j_out, the stop level, and checks."""
    t = px["times"]
    tr = trades.copy()
    tr["j_in"] = t.get_indexer(tr["time_in"])
    tr["j_out"] = t.get_indexer(tr["time_out"])
    if (tr.j_in < 0).any() or (tr.j_out < 0).any():
        raise ValueError("a trade time is not on the bar index")
    tr["open_ok"] = np.isclose(px["o"][tr.j_in.values], tr.p_in.values, rtol=1e-9, atol=1e-9)
    dist = cfg["stop_units"] * cfg["barrier_atr"] * px["atr1h"][tr.j_in.values - 1]
    tr["stop"] = tr.p_in.values - tr.side.values * dist
    return tr


# ---------------------------------------------------------------- one leg

def limit_price(px, j0, side, k):
    """Order placed at open[j0]; side +1 buys below, -1 sells above. Uses ATR15 of bar j0-1."""
    return px["o"][j0] - side * k * px["atr15"][j0 - 1]


def first_fill(px, j0, j_last, side, price):
    """First bar in j0..j_last that trades strictly through `price` for an order of `side`."""
    h, l = px["h"], px["l"]
    for j in range(j0, min(j_last, len(h) - 1) + 1):
        if (side > 0 and l[j] < price) or (side < 0 and h[j] > price):
            return j
    return None


def entry_leg(px, tr, pol):
    """-> (bar, price, maker) or None when the entry is missed."""
    s, j0, jx, stop_exit = int(tr.side), int(tr.j_in), int(tr.j_out), tr.why_out == "STOP"
    if pol["kind"] == "market":
        return j0, px["o"][j0], False
    price = limit_price(px, j0, s, pol["k"])
    last_live = jx if stop_exit else jx - 1                # the order dies when the exit is decided
    j_end = j0 + pol["n"] - 1
    j = first_fill(px, j0, min(j_end, last_live), s, price)
    if j is not None:
        return j, price, True
    if pol["timeout"] == "skip" or j_end >= last_live or j_end + 1 >= len(px["o"]):
        return None
    jc = j_end + 1                                          # chase at the next open
    if not stop_exit and jc >= jx:
        return None
    return jc, px["o"][jc], False


def exit_leg(px, tr, pol, j_entry):
    """-> (bar, price, maker). STOP exits keep the incumbent's price; flips may rest a limit."""
    s, jx = int(tr.side), int(tr.j_out)
    if tr.why_out == "STOP" or pol["kind"] == "market":
        return jx, float(tr.p_out), False
    o, h, l = px["o"], px["h"], px["l"]
    price = limit_price(px, jx, -s, pol["k"])               # closing a long sells above the open
    stop = float(tr.stop)
    last = min(jx + pol["n"] - 1, len(o) - 1)
    for j in range(jx, last + 1):
        if s > 0 and l[j] <= stop:                         # the stop is still live, checked first
            return j, min(o[j], stop), False
        if s < 0 and h[j] >= stop:
            return j, max(o[j], stop), False
        if (s > 0 and h[j] > price) or (s < 0 and l[j] < price):
            return j, price, True
    jc = min(last + 1, len(o) - 1)
    return jc, o[jc], False


def simulate(px, trades, entry_pol, exit_pol, venue):
    """Every closed replay trade under one policy. -> one row per trade."""
    fee = FEES[venue]
    rows = []
    for tr in trades.itertuples(index=False):
        if tr.why_out == "OPEN":
            continue
        e = entry_leg(px, tr, entry_pol)
        if e is None:
            rows.append((tr.time_in, int(tr.side), False, np.nan, np.nan, False, False, 0.0, 0.0, 0.0))
            continue
        x = exit_leg(px, tr, exit_pol, e[0])
        f_in = fee["maker" if e[2] else "taker"]
        f_out = fee["maker" if x[2] else "taker"]
        gross = tr.side * (x[1] - e[1]) / e[1]
        fees = f_in + f_out * x[1] / e[1]
        fund = tr.side * (px["fund"][x[0]] - px["fund"][e[0]]) if venue == "perp" else 0.0
        rows.append((tr.time_in, int(tr.side), True, e[1], x[1], e[2], x[2], gross - fees - fund, fees, fund))
    return pd.DataFrame(rows, columns=["time_in", "side", "filled", "p_in", "p_out", "maker_in", "maker_out",
                                       "ret", "fee_frac", "fund_frac"])


# ---------------------------------------------------------------- scoring

def _book(ret):
    eq = np.cumprod(1.0 + np.asarray(ret, float)) * NOTIONAL
    if not len(eq):
        return 0.0, 0.0
    curve = np.concatenate([[NOTIONAL], eq])
    dd = float((curve / np.maximum.accumulate(curve) - 1.0).min())
    return float(eq[-1] / NOTIONAL - 1.0), dd


def score(sim, mkt):
    """`sim` against `mkt` (the same trades filled at market on the same venue)."""
    f = sim.filled.values
    miss = ~f
    m_ret = mkt.ret.values
    ret, dd = _book(sim.ret.values)
    out = {"trades": int(len(sim)), "filled": int(f.sum()), "missed": int(miss.sum()),
           "missed_winners": int((miss & (m_ret > 0)).sum()), "missed_losers": int((miss & (m_ret <= 0)).sum()),
           "missed_mkt_pnl_usd": round(float(m_ret[miss].sum() * NOTIONAL), 0),
           "fill_rate_mkt_winners": round(float(f[m_ret > 0].mean()), 3) if (m_ret > 0).any() else None,
           "fill_rate_mkt_losers": round(float(f[m_ret <= 0].mean()), 3) if (m_ret <= 0).any() else None,
           "maker_share_in": round(float(sim.maker_in[f].mean()), 3) if f.any() else None,
           "maker_share_out": round(float(sim.maker_out[f].mean()), 3) if f.any() else None,
           "pnl_usd": round(float(sim.ret.sum() * NOTIONAL), 0),
           "fees_usd": round(float(sim.fee_frac.sum() * NOTIONAL), 0),
           "funding_usd": round(float(sim.fund_frac.sum() * NOTIONAL), 0),
           "return_pct": round(ret * 100, 1), "max_dd_pct": round(dd * 100, 1)}
    if f.any():                                            # per round trip, on trades both books took
        d = (sim.ret.values[f] - m_ret[f]) * NOTIONAL
        fee_saved = (mkt.fee_frac.values[f] - sim.fee_frac.values[f]) * NOTIONAL
        out["saved_per_rt_usd"] = round(float(d.mean()), 2)
        out["fee_saved_per_rt_usd"] = round(float(fee_saved.mean()), 2)
        out["price_gain_per_rt_usd"] = round(float((d - fee_saved).mean()), 2)
    t = pd.DatetimeIndex(pd.to_datetime(sim.time_in, utc=True))
    first = np.asarray(t < pd.Timestamp(SPLIT, tz="UTC"))
    for tag, sel in (("h1", first), ("h2", ~first)):
        out["pnl_usd_" + tag] = round(float(sim.ret.values[sel].sum() * NOTIONAL), 0)
        out["missed_" + tag] = int(miss[sel].sum())
    out["by_year_usd"] = dict((int(y), round(float(g.sum() * NOTIONAL), 0))
                              for y, g in pd.Series(sim.ret.values, index=t.year).groupby(level=0))
    return out


def policies():
    entries = [MARKET] + [limit(k, n, to) for k, n, to in itertools.product(KS, NS, ("skip", "chase"))]
    exits = [MARKET] + [limit(k, n, "chase") for k, n in itertools.product(KS, NS)]
    return entries, exits


def run_asset(asset, log=print):
    bars = data.load(asset)
    bars = bars[bars.index >= pd.Timestamp(CFG["birth"], tz="UTC") - pd.Timedelta(days=60)]
    px = bars_arrays(bars, data.load_funding(asset))
    del bars
    tr = locate(load_trades(asset), px)
    checks = {"trades": int(len(tr)), "p_in_equals_open": int(tr.open_ok.sum())}
    st = tr[tr.why_out == "STOP"]
    exact = ~np.isclose(st.p_out.values, px["o"][st.j_out.values])     # stop filled at its level, not a gap
    checks["stop_level_matches"] = "%d of %d" % (int(np.isclose(st.p_out.values[exact], st.stop.values[exact],
                                                                rtol=1e-6).sum()), int(exact.sum()))
    inc = simulate(px, tr, MARKET, MARKET, "spot")
    closed = tr[tr.why_out != "OPEN"]
    checks["incumbent_max_abs_err_pct"] = float(np.abs(inc.ret.values * 100 - closed.pnl_pct.values).max())
    log(asset, checks)
    entries, exits = policies()
    rows, mkts = [], {}
    for venue in FEES:
        mkts[venue] = simulate(px, tr, MARKET, MARKET, venue)
    for venue, en, ex in itertools.product(FEES, entries, exits):
        sim = mkts[venue] if (en is MARKET and ex is MARKET) else simulate(px, tr, en, ex, venue)
        sc = score(sim, mkts[venue])
        sc.update({"asset": asset, "venue": venue, "entry": name(en), "exit": name(ex)})
        rows.append(sc)
    base = score(inc, inc)
    return rows, checks, base


def main():
    out_dir = os.path.join(OUT_DIR, "fills")
    os.makedirs(out_dir, exist_ok=True)
    allrows, summary = [], {"checks": {}, "incumbent": {}}
    for asset in CFG["assets"]:
        rows, checks, base = run_asset(asset)
        allrows += rows
        summary["checks"][asset], summary["incumbent"][asset] = checks, base
    grid = pd.DataFrame(allrows)
    flat = grid.drop(columns=["by_year_usd"])
    flat.to_csv(os.path.join(out_dir, "fills_grid.csv"), index=False)
    both = flat.groupby(["venue", "entry", "exit"])[["pnl_usd", "pnl_usd_h1", "pnl_usd_h2", "fees_usd",
                                                    "missed"]].sum().reset_index()
    inc_pnl = sum(summary["incumbent"][a]["pnl_usd"] for a in summary["incumbent"])
    both["vs_incumbent_usd"] = both.pnl_usd - inc_pnl
    summary["top10_both_coins"] = both.sort_values("pnl_usd", ascending=False).head(10).to_dict("records")
    keep = grid[grid.entry.isin(["market", "limit k0.00 N1 chase", "limit k0.10 N4 chase", "limit k0.25 N4 chase",
                                 "limit k0.10 N4 skip", "limit k0.25 N2 skip"])
                & grid.exit.isin(["market", "limit k0.00 N2 chase", name(CANDIDATE_EXIT)])]
    summary["selected"] = keep.to_dict("records")
    cand = grid[(grid.entry == "market") & (grid.exit == name(CANDIDATE_EXIT)) & (grid.venue == "spot")]
    summary["candidate"] = {"rule": "entries market; stop exits market; flip exits " + name(CANDIDATE_EXIT),
                            "rows": cand.to_dict("records")}
    years = pd.DataFrame(dict(("%s %s" % (a[:3], tag), pd.Series(by))
                              for a in summary["incumbent"]
                              for tag, by in (("incumbent", summary["incumbent"][a]["by_year_usd"]),
                                              ("candidate", cand[cand.asset == a].by_year_usd.iloc[0]))))
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=str)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 200)
    cols = ["asset", "venue", "entry", "exit", "return_pct", "max_dd_pct", "pnl_usd", "fees_usd", "funding_usd",
            "missed", "missed_winners", "missed_losers", "missed_mkt_pnl_usd", "saved_per_rt_usd", "pnl_usd_h1",
            "pnl_usd_h2"]
    print(keep[cols].to_string(index=False))
    print("\nbest 15 of %d policy pairs by $ P&L, both coins (a grid search: expect the top to be lucky)"
          % len(both))
    print(both.sort_values("pnl_usd", ascending=False).head(15).to_string(index=False))
    print("\nby year, $ at $10,000 a trade, spot fees: incumbent vs candidate (%s)" % summary["candidate"]["rule"])
    print(years.to_string())
    print("saved to", out_dir)


if __name__ == "__main__":
    main()
