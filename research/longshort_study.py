# -*- coding: utf-8 -*-
"""H37 -- hedged long-short structures for BTC and ETH downtrends (registered in research/HYPOTHESES.md, 13 Nov 2026
09:33 UTC, before this file existed). EXPLORATION, not a loop round: it changes no loop rule and cannot make a pass.

    py -3 research/longshort_study.py            compute on development data, write research/out/longshort/

Development data only: research/harness/core.load(asset, dev_only=True) drops every bar from 2025-11-11 on (the
sealed holdout is never loaded here). Reported over the loop's walk-forward out-of-sample span 2020-10-01 .. 2025-11-11.
Paper research only: nothing here places orders.

Accounting: two legs per coin, spot (s >= 0, no funding) and perpetual (p, pays p x rate at each settlement: a positive
rate costs a long and pays a short). Fee 0.10% a side, half spread 0.5 bp and slippage 0.10 x per-bar vol on every
leg's trades (the harness cost model). A target decided at the close of bar t is held from the open of bar t + 1.
Both legs use the same 15m price series (spot-perp basis ignored).
"""
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15 import data as edata  # noqa: E402
from engine15.rl import metrics, walkforward  # noqa: E402
from research.harness import core  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "longshort")
ASSETS = ("BTCUSDT", "ETHUSDT")
BAR_MS = 900000
DAY_MS = 86400000
BPY = core.BPY
FEE = core.FEE_HEAD
HS = core.COST_KW["half_spread_bps"] * 1e-4
SLIP = core.COST_KW["slippage_coef"]
GROSS_MAX = 1.5
N_VARIANTS = 11                                   # 5 rules x 2 coins + the V4 two-coin book (registered)
REGISTERED_UTC = "2026-11-13 09:33 UTC"

VARIANTS = ["V1_dial0", "V2_dialm05", "V3_dial0_fund", "V4_rv_bear", "V5_fr_hedge"]
REFS = ["R_flat", "R_naked", "R_naked_FR"]
LABEL = {"BH_spot": "Spot buy-and-hold 1x",
         "V1_dial0": "V1 dial0: D -> spot 0.75 + perp -0.75 (net 0)",
         "V2_dialm05": "V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5)",
         "V3_dial0_fund": "V3 dial0_fund: V1 only when funding > 0, else flat",
         "V4_rv_bear": "V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75",
         "V5_fr_hedge": "V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally",
         "R_flat": "ref R-flat: D -> flat",
         "R_naked": "ref R-naked: D -> perp -1 (naked short)",
         "R_naked_FR": "ref R-naked-FR: V5 signal, flat base, perp -1"}
# calendar windows the owner named (chosen with hindsight; shown for reference beside the rule's own windows)
NAMED = [("2021-11-10", "2023-01-01", "Nov 2021 - Dec 2022 bear"),
         ("2025-01-20", "2025-04-09", "Jan - Apr 2025 drawdown"),
         ("2025-10-06", "2025-11-11", "Oct - Nov 2025 drawdown (to the seal)")]

# Plain-words reading, written AFTER the first run's numbers were read (13 Nov 2026, ~09:40 UTC). It quotes them; if a
# re-run changed any number this text would have to be rewritten by hand.
FINDINGS = """Development data only; no holdout bar was used.

**No variant meets the bar registered for a later formal registration.** The closest is V4 (rv_bear). It meets every
part on ETH, and on BTC it fails only one part: its D-bar return (+12%) is below the naked short's (+27%).

- **Everything that steps aside in downtrends beats buy-and-hold on this span, and the reason is one event.** The rule
  caught most of 2022. Almost every structure, R-flat included, earns about +58-83% CAGR against buy-and-hold's +56%,
  with a smaller drawdown (ETH's naked short, +48.9%, is the exception). Loop rounds 2-3 already found this and failed it on fold share and significance. These
  rules match buy-and-hold exactly in 13 of BTC's 21 folds (9 of ETH's), so their fold share is 0-24%. None reaches
  this study's significance level (best p 0.087 vs 0.0045).
- **The hedge dial (V1) is going flat plus a little carry.** Spot 0.75 + perp -0.75 trades the same amount as selling
  to flat, and with the basis ignored it has the same price exposure. Its only extra is funding, about +0.6% a year on
  each coin (+3% per year of D on BTC, +2% on ETH). V1 vs R-flat: BTC +75.4% vs +74.3% CAGR, ETH +66.8% vs +65.9%.
  Against flat, V1 earns the funding and keeps a spot core. It has no other edge.
- **The partial net short (V2) is the naked short at half size.** Both depend on the coin:
  - BTC's one long bear (Mar 2022 - Jan 2023): V2 made +34%, R-naked +60%, R-flat 0%.
  - ETH's bears whipsawed: V2 -14% and R-naked -42% over all D bars, R-flat -1%. ETH's naked short ended BELOW
    buy-and-hold over the whole span (+48.9% CAGR vs +56.6%).
  - The owner's observation holds: shorts pay in a clean, long bear and give it back in choppy ones.
- **The funding filter (V3) hurt on both coins.** Switching both legs on and off with the 3-settlement funding sign cost
  about 2.6% a year on BTC and 5.4% on ETH in fees and slippage. That is far more than the funding it avoided. In
  this sample, funding in downtrends was mostly POSITIVE for shorts: annualised +4.3% on BTC and +2.5% on ETH while
  D held, and negative on only 16% / 23% of D days. Paying negative funding while short was not a main loss source.
- **Shorting failed rallies (V5) lost on both coins.** The hedge signal alone (R-naked-FR) lost 11% (BTC) and 28% (ETH)
  over D bars. Its exits were mostly stops and time stops (BTC 9 stops and 7 time stops vs 6 take-profits; ETH 12, 9
  and 7). Bear rallies kept going past the 20/50-day averages. V5's base of 0.5 spot through D also carried half of
  the bear's loss (-27% on BTC's D bars).
- **Relative value in downtrends (V4) is the only structure that earned in D on both coins.** It made +12% on BTC's D
  bars and +55% on ETH's. As a two-coin book: +79.7% CAGR, Sharpe 1.25, max DD -57%, against half-and-half spot
  buy-and-hold at +56.4%, 0.99 and -79%. +90% on bars where either coin was in D, against -7%. The caveat is large:
  ETH lost ground to BTC almost all the way from late 2021 to mid-2025. V4 mostly harvests that one long trend (short
  ETH / long BTC in ETH's downtrends). A sharp ETH/BTC reversal inside a downtrend is its squeeze risk: the worst 7-day
  hedge-leg loss was -24% (to 2022-06-25).
- **Where the damage comes from, by cause:**
  - *Late entry* is the biggest. The median fall from the 180-day high before D turned on was -33% on both coins (BTC
    2022: -37%). Every dial structure's maximum drawdown on BTC (about -57%, Apr 2021 - Jan 2022) happened BEFORE the
    rule turned on. No hedge structure can fix that; only an earlier signal can.
  - *Whipsaw*: 3 of BTC's 4 D turn-ons and 6 of ETH's 10 lasted under 30 days. In BTC's short episodes buy-and-hold
    gained +22% while R-naked lost 21% and V2 lost 11%.
  - *Squeeze*: the worst 7-day result on the hedge leg was -23% (BTC, V2 / naked) and -47% (ETH, V2 / naked), both
    the July 2022 relief rally. V1's smaller hedge kept it to -17% / -35%.
  - *Funding*: a small net gain for shorts here, not a loss.
  - *Gaps*: the worst single 15m bars (-10.3% BTC, -10.0% ETH) fell in up regimes on the long leg, not on any hedge.

**Recommendation.**
- No structure here has earned a formal loop registration on this evidence. The one candidate, V4 rv_bear as a two-coin
  book, would have to be registered fresh under the loop's full rules, disclosing this study's 11 variants. On this
  data it would almost certainly fail fold share and significance, like every rule before it. The book's Sharpe edge
  over buy-and-hold is +0.34 on daily returns (bootstrap standard error 0.27, p 0.10). The loop's level (0.05 / 1,910)
  would need an edge of about 1.07 at that standard error. Its fold share is 24%.
- If the owner wants forward data points, V4 is the only structure worth a forward paper shadow book. It should be
  labelled not passed and run from a stated go-live, like the round-2 books.
- V1 needs no book of its own. In this model it is R-flat plus carry, so it adds nothing a forward test would teach.
- V2, V3 and V5 are not worth continuing.

**Caveats.**
- The span holds one long bear (2022) and a few short ones. Every D result rests on very few independent episodes.
- Spot-perp basis is ignored: BTC bars are perp prices and ETH bars are spot.
- Positions are fractions of equity held constant, so the drift between legs is rebalanced for free (the harness
  convention). Margin, liquidation and borrow limits are not modelled.
- The named calendar windows were picked with hindsight. The rule never turned on for BTC in early 2025 or Oct-Nov
  2025, so every structure equals buy-and-hold there.
- 11 variants were tried; a p of 0.09-0.55 against buy-and-hold is consistent with luck.
- V6 (agent hedge ratio) was not run: it would have needed fold-model inference over the full span, including the sealed
  holdout, and the heavy-job lock.""".split("\n")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ------------------------------------------------------------------ point-in-time daily features (closed daily bars only)

def daily_feats(bars):
    """Daily values joined to the 15m index through edata.htf_on_15: row t sees the last UTC day closed by t's close."""
    d1 = edata.resample(bars[["open", "high", "low", "close", "volume"]].assign(taker_buy=0.0), "1D")
    c, h, lo = d1["close"], d1["high"], d1["low"]
    sma20, sma50, sma200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    pc = c.shift(1)
    tr = np.maximum(h - lo, np.maximum((h - pc).abs(), (lo - pc).abs()))
    atr = tr.ewm(alpha=1 / 14.0, adjust=False).mean()
    down = ((c < sma200) & (sma200 < sma200.shift(20))).astype(float)
    touch = (h >= np.minimum(sma20, sma50) - 0.25 * atr)
    close_ms = pd.Series(edata.to_ms(d1.index) + DAY_MS, index=d1.index).astype(float)
    tms = close_ms.where(touch)                                    # close time of a touched day
    last_touch3 = pd.concat([tms, tms.shift(1), tms.shift(2)], axis=1).max(axis=1)   # most recent touch in the last 3 days
    stall = (c < sma20) & (c < pc)
    no_break = c > c.shift(1).rolling(20).min()
    f = pd.DataFrame({"close_d": c, "sma20": sma20, "sma50": sma50, "sma200": sma200, "atr": atr, "D": down,
                      "last_touch_ms": last_touch3, "stall": stall.astype(float), "no_break": no_break.astype(float),
                      "ret30": np.log(c).diff(30)}, index=d1.index)
    out = edata.htf_on_15(bars, "1D", f)
    out["D"] = out["D"].fillna(0.0)
    for k in ("stall", "no_break"):
        out[k] = out[k].fillna(0.0)
    close15 = edata.to_ms(bars.index) + BAR_MS
    out["is_daily"] = (close15 % DAY_MS) == 0
    out["close_ms"] = close15.astype(float)
    out["close"] = bars["close"].values.astype(float)
    return out


def funding_mean3(index, fund):
    """Mean of the last 3 settled funding rates known at each bar's close (settle_ms <= close)."""
    close_ms = edata.to_ms(index) + BAR_MS
    if fund is None or not len(fund):
        return np.zeros(len(index))
    s = np.asarray(fund["settle_ms"], dtype="int64")
    o = np.argsort(s, kind="stable")
    s, r = s[o], np.asarray(fund["rate"], dtype=float)[o]
    cs = np.concatenate([[0.0], np.cumsum(r)])
    k = np.searchsorted(s, close_ms, side="right")
    lo = np.maximum(k - 3, 0)
    cnt = k - lo
    return np.where(cnt > 0, (cs[k] - cs[lo]) / np.maximum(cnt, 1), 0.0)


# ------------------------------------------------------------------ targets (each reads row t and its own state only)

def dial(f, s_d, p_d):
    D = f["D"].values > 0
    return np.where(D, s_d, 1.0), np.where(D, p_d, 0.0)


def dial_fund(f, fm3):
    """V3: in D, hedge (spot 0.75 / perp -0.75) only if the 3-settlement mean known at the latest 00:00 decision is > 0."""
    D = f["D"].values > 0
    daily = f["is_daily"].values
    pos = pd.Series(np.where(daily, (fm3 > 0).astype(float), np.nan)).ffill().fillna(0.0).values > 0
    s = np.where(D, np.where(pos, 0.75, 0.0), 1.0)
    p = np.where(D, np.where(pos, -0.75, 0.0), 0.0)
    return s, p


def fr_hedge(f, base_spot=0.5, hedge=-1.0, tp=1.5, stop=0.5, max_bars=960, collect=None):
    """V5 (base 0.5) and R-naked-FR (base 0): failed-rally hedge state machine on the 15m clock."""
    D = (f["D"].values > 0).tolist()
    daily = f["is_daily"].values.tolist()
    c = f["close"].values.tolist()
    s20, s50, atr = f["sma20"].values.tolist(), f["sma50"].values.tolist(), f["atr"].values.tolist()
    cd = f["close_d"].values.tolist()
    ltm = np.nan_to_num(f["last_touch_ms"].values, nan=-1.0).tolist()
    stall, nob = f["stall"].values.tolist(), f["no_break"].values.tolist()
    cms = f["close_ms"].values.tolist()
    n = len(c)
    s_out, p_out = np.ones(n), np.zeros(n)
    on, ref, aref, t0, last_exit = False, 0.0, 0.0, 0, -1.0
    for t in range(n):
        if not D[t]:
            if on and collect is not None:
                collect.append(("regime", t - t0))
            if on:
                last_exit = cms[t]
            on = False
            continue
        s_out[t] = base_spot
        if on:
            why = None
            if c[t] <= ref - tp * aref:
                why = "take_profit"
            elif c[t] > max(s20[t], s50[t]) + stop * atr[t]:
                why = "stop"
            elif t - t0 >= max_bars:
                why = "time"
            if why:
                on, last_exit = False, cms[t]
                if collect is not None:
                    collect.append((why, t - t0))
        if (not on and daily[t] and ltm[t] > last_exit and stall[t] > 0 and nob[t] > 0
                and atr[t] == atr[t] and s20[t] == s20[t] and s50[t] == s50[t]):
            on, ref, aref, t0 = True, cd[t], atr[t], t
        if on:
            p_out[t] = hedge
    return s_out, p_out


def coin_targets(bars, fund, f=None, collect=None):
    """-> dict name -> (spot target, perp target) for the single-coin rules and references."""
    f = daily_feats(bars) if f is None else f
    fm3 = funding_mean3(bars.index, fund)
    T = {"BH_spot": (np.ones(len(bars)), np.zeros(len(bars))),
         "V1_dial0": dial(f, 0.75, -0.75),
         "V2_dialm05": dial(f, 0.5, -1.0),
         "V3_dial0_fund": dial_fund(f, fm3),
         "V5_fr_hedge": fr_hedge(f, 0.5, -1.0, collect=collect),
         "R_flat": dial(f, 0.0, 0.0),
         "R_naked": dial(f, 0.0, -1.0),
         "R_naked_FR": fr_hedge(f, 0.0, -1.0)}
    return T, f


def rv_targets(f_own, f_other, own_is_btc):
    """V4 sleeve on a common index: U -> own spot 1. D (own) -> long the stronger coin spot 0.75, short the weaker perp
    0.75; stronger = higher 30-day log return (ties -> BTC). -> dict leg -> target (own_spot, own_perp, oth_spot, oth_perp)."""
    D = f_own["D"].values > 0
    ro = np.nan_to_num(f_own["ret30"].values, nan=0.0)
    rx = np.nan_to_num(f_other["ret30"].values, nan=0.0)
    own_strong = (ro > rx) | ((ro == rx) & own_is_btc)
    n = len(D)
    own_s = np.where(D, np.where(own_strong, 0.75, 0.0), 1.0)
    own_p = np.where(D & ~own_strong, -0.75, 0.0)
    oth_s = np.where(D & ~own_strong, 0.75, 0.0)
    oth_p = np.where(D & own_strong, -0.75, 0.0)
    assert len(own_s) == n
    return {"own_spot": own_s, "own_perp": own_p, "oth_spot": oth_s, "oth_perp": oth_p}


# ------------------------------------------------------------------ multi-leg accounting

def held(target):
    t = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    pos = np.zeros_like(t)
    pos[1:] = t[:-1]
    return pos


def run_legs(legs, fee=FEE):
    """legs: list of (core.Market, target, is_perp). -> dict of per-bar arrays: r_net, spot_pnl, perp_pnl, funding
    (+ = received), costs, changed (any leg's held position changed), gross_exposure, net_exposure."""
    n = len(legs[0][0].r_px)
    z = np.zeros(n)
    out = {"spot_pnl": z.copy(), "perp_pnl": z.copy(), "funding": z.copy(), "costs": z.copy(), "fees": z.copy(),
           "changed": np.zeros(n, bool), "gross": z.copy(), "net": z.copy(), "turnover": z.copy()}
    for mkt, tgt, perp in legs:
        pos = held(tgt)
        a = np.abs(np.diff(pos, prepend=0.0))
        g = pos * mkt.r_px
        out["perp_pnl" if perp else "spot_pnl"] += g
        if perp:
            out["funding"] -= pos * mkt.rate
        out["costs"] += (fee + HS) * a + SLIP * mkt.vol_dec * a
        out["fees"] += fee * a
        out["changed"] |= a > 0
        out["turnover"] += a
        out["gross"] += np.abs(pos)
        out["net"] += pos
    out["r_net"] = out["spot_pnl"] + out["perp_pnl"] + out["funding"] - out["costs"]
    return out


def stitch_oos(x, oos):
    return np.where(oos, np.nan_to_num(np.asarray(x, dtype=float)), 0.0)


# ------------------------------------------------------------------ scoring

def year_returns(r, index, oos):
    s = pd.Series(r[oos], index=index[oos])
    g = (1.0 + s).groupby(s.index.year).prod() - 1.0
    return dict((int(k), float(v)) for k, v in g.items())


def stats(res, index, wins, oos, bh_folds=None):
    r = res["r_net"]
    x = r[oos]
    eq = np.cumprod(1 + x)
    years = len(x) / BPY
    out = {"total_return": float(eq[-1] - 1), "cagr": metrics.cagr(x), "sharpe": metrics.sharpe(x),
           "max_drawdown": metrics.max_drawdown(np.concatenate([[1.0], eq])), "calmar": metrics.calmar(x),
           "years": years, "trades_per_year": float(res["changed"][oos].sum() / years),
           "turnover_per_year": float(res["turnover"][oos].sum() / years),
           "avg_gross": float(res["gross"][oos].mean()), "avg_net": float(res["net"][oos].mean()),
           "max_gross": float(res["gross"][oos].max())}
    for k in ("spot_pnl", "perp_pnl", "funding", "costs", "fees"):
        out[k + "_per_year"] = float(res[k][oos].sum() / years)
    _, te = core.masks(index, wins)
    out["folds"] = [{"test_start": str(w["test_start"].date()), "total_return": float(np.prod(1 + r[m]) - 1),
                     "sharpe": metrics.sharpe(r[m])} for w, m in zip(wins, te)]
    out["positive_fold_share"] = float(np.mean([fd["total_return"] > 0 for fd in out["folds"]]))
    if bh_folds is not None:
        out["fold_share"] = float(np.mean([a["sharpe"] > b["sharpe"] for a, b in zip(out["folds"], bh_folds)]))
        diff = [i for i, (a, b) in enumerate(zip(out["folds"], bh_folds)) if abs(a["total_return"] - b["total_return"]) > 1e-9]
        out["folds_differing_from_bh"] = len(diff)
        out["fold_share_among_differing"] = (float(np.mean([out["folds"][i]["sharpe"] > bh_folds[i]["sharpe"] for i in diff]))
                                             if diff else None)
    full = np.concatenate([[1.0], eq])
    k_tr = int(np.argmax(np.maximum.accumulate(full) / full))
    k_pk = int(np.argmax(full[:k_tr + 1]))
    ix = index[oos]
    out["dd_peak"] = str(ix[max(k_pk - 1, 0)].date())
    out["dd_trough"] = str(ix[max(k_tr - 1, 0)].date())
    out["years_table"] = year_returns(r, index, oos)
    return out


def episodes(mask):
    """-> list of (start, end_exclusive) runs of True."""
    m = np.asarray(mask, bool).astype(int)
    d = np.diff(np.concatenate([[0], m, [0]]))
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def merge_windows(eps, gap_bars, min_bars):
    out = []
    for a, b in eps:
        if out and a - out[-1][1] <= gap_bars:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= min_bars]


def comp(r, a, b):
    return float(np.prod(1 + r[a:b]) - 1)


def regime_analysis(name_r, f, index, oos, close):
    """Rule-identified D windows, pooled D / U bars, whipsaw and late-entry measures."""
    Dpos = held(f["D"].values)                          # the regime the HELD position was decided in
    Dm = (Dpos > 0) & oos
    eps = episodes(Dm)
    wins = merge_windows(eps, 14 * 96, 30 * 96)
    out = {"turn_ons": len(eps), "short_episodes_lt30d": int(sum(1 for a, b in eps if b - a < 30 * 96)),
           "d_share_of_span": float(Dm.sum() / oos.sum()), "windows": [], "pooled": {}}
    short_m = np.zeros(len(index), bool)
    long_m = np.zeros(len(index), bool)
    for a, b in eps:
        (short_m if b - a < 30 * 96 else long_m)[a:b] = True
    um = (Dpos == 0) & oos
    for nm, r in name_r.items():
        out["pooled"][nm] = {"D_bars": float(np.prod(1 + r[Dm]) - 1), "U_bars": float(np.prod(1 + r[um]) - 1),
                             "D_short_episodes": float(np.prod(1 + r[short_m]) - 1),
                             "D_long_episodes": float(np.prod(1 + r[long_m]) - 1)}
    cd = pd.Series(close, index=index)
    for a, b in wins:
        w = {"start": str(index[a].date()), "end": str(index[b - 1].date()), "days": round((b - a) / 96.0, 1),
             "d_bar_share": float(Dm[a:b].mean()), "returns": dict((nm, comp(r, a, b)) for nm, r in name_r.items())}
        pre = cd[(cd.index > index[a] - pd.Timedelta(days=180)) & (cd.index <= index[a])]
        w["fall_before_turn_on"] = float(close[a] / pre.max() - 1)          # late entry: how much was already lost
        w["low_inside"] = float(close[a:b].min() / close[a] - 1)
        w["rise_from_low_to_end"] = float(close[b - 1] / close[a:b].min() - 1)   # late exit
        out["windows"].append(w)
    falls = []
    for a, b in eps:
        pre = cd[(cd.index > index[a] - pd.Timedelta(days=180)) & (cd.index <= index[a])]
        falls.append(float(close[a] / pre.max() - 1))
    out["median_fall_before_turn_on"] = float(np.median(falls)) if falls else None
    return out


def named_windows(name_r, index):
    out = []
    for a, b, nm in NAMED:
        m = (index >= pd.Timestamp(a, tz="UTC")) & (index < pd.Timestamp(b, tz="UTC"))
        out.append({"window": nm, "start": a, "end": b,
                    "returns": dict((k, float(np.prod(1 + r[m]) - 1)) for k, r in name_r.items())})
    return out


def leg_risks(res, index, oos, Dm):
    """Squeeze (worst 7-day perp-leg result incl. funding), gaps (worst single bars), funding inside D."""
    perp = res["perp_pnl"] + res["funding"]
    out = {}
    if np.any(perp[oos] != 0):
        roll = pd.Series(np.where(oos, perp, 0.0)).rolling(672).sum().values
        k = int(np.nanargmin(roll))
        out["worst_7d_perp_leg"] = float(roll[k])
        out["worst_7d_perp_leg_end"] = str(index[k].date())
        kb = int(np.argmin(np.where(oos, perp, np.inf)))
        out["worst_bar_perp_leg"] = float(perp[kb])
        out["worst_bar_perp_leg_at"] = str(index[kb])
    r = np.where(oos, res["r_net"], np.inf)
    kb = int(np.argmin(r))
    out["worst_bar"] = float(res["r_net"][kb])
    out["worst_bar_at"] = str(index[kb])
    yd = Dm.sum() / BPY
    out["funding_in_D_per_D_year"] = float(res["funding"][Dm].sum() / yd) if yd else 0.0
    out["perp_price_in_D_per_D_year"] = float(res["perp_pnl"][Dm].sum() / yd) if yd else 0.0
    out["costs_in_D_per_D_year"] = float(res["costs"][Dm].sum() / yd) if yd else 0.0
    return out


def funding_in_D(fund, f, index, oos):
    """Share of D days whose summed settled funding was negative; mean annualised funding in D vs U."""
    m = core.model()
    rb = m.funding_on_bars(index, fund)
    Dpos = held(f["D"].values) > 0
    s = pd.Series(rb, index=index)
    day = s.resample("1D").sum()
    dD = pd.Series(Dpos & oos, index=index).resample("1D").mean() > 0.5
    dU = pd.Series((~Dpos) & oos, index=index).resample("1D").mean() > 0.5
    return {"neg_funding_day_share_D": float((day[dD] < 0).mean()) if dD.any() else None,
            "neg_funding_day_share_U": float((day[dU] < 0).mean()) if dU.any() else None,
            "funding_ann_D": float(day[dD].mean() * 365) if dD.any() else None,
            "funding_ann_U": float(day[dU].mean() * 365) if dU.any() else None}


def signif(r, rb, index, oos):
    obs, p, se = core.boot_sharpe_diff_z(r[oos], rb[oos], index[oos])
    return {"sharpe_minus_bh": obs, "p": p, "se": se, "p_level_study": 0.05 / N_VARIANTS,
            "dsr": core.deflated_sharpe(r[oos], N_VARIANTS)}


# ------------------------------------------------------------------ the study

def run_coin(asset):
    bars, fund = core.load(asset, dev_only=True)
    assert bars.index[-1] < core.HOLDOUT_START
    mkt = core.Market(bars, fund)
    idx = bars.index
    wins = core.windows(idx)
    oos = walkforward.oos_mask(idx, wins)
    fr_log = []
    T, f = coin_targets(bars, fund, collect=fr_log)
    R = {}
    for nm, (s, p) in T.items():
        R[nm] = run_legs([(mkt, stitch_oos(s, oos), False), (mkt, stitch_oos(p, oos), True)])
        assert R[nm]["gross"].max() <= GROSS_MAX + 1e-12, nm
    # sanity: the spot buy-and-hold equals the harness's own (core.Market, spot=True)
    chk = float(np.max(np.abs(R["BH_spot"]["r_net"] - mkt.net(stitch_oos(np.ones(len(idx)), oos), FEE, spot=True))))
    S = {"BH_spot": stats(R["BH_spot"], idx, wins, oos)}
    bhf = S["BH_spot"]["folds"]
    S["BH_spot"]["fold_share"] = 0.0
    for nm in T:
        if nm != "BH_spot":
            S[nm] = stats(R[nm], idx, wins, oos, bhf)
            S[nm]["significance"] = signif(R[nm]["r_net"], R["BH_spot"]["r_net"], idx, oos)
    Dm = (held(f["D"].values) > 0) & oos
    risks = dict((nm, leg_risks(R[nm], idx, oos, Dm)) for nm in T)
    name_r = dict((nm, R[nm]["r_net"]) for nm in T)
    reg = regime_analysis(name_r, f, idx, oos, bars["close"].values)
    named = named_windows(name_r, idx)
    exits = {}
    for why, nb in fr_log:
        e = exits.setdefault(why, [0, 0])
        e[0] += 1
        e[1] += nb
    fr_exits = dict((k, {"count": v[0], "avg_hours": v[1] / v[0] / 4.0}) for k, v in exits.items())
    out = {"asset": asset, "bars": len(idx), "first": str(idx[0]), "last": str(idx[-1]),
           "oos": [str(wins[0]["test_start"].date()), str(wins[-1]["test_end"].date())], "folds": len(wins),
           "bh_matches_harness_max_abs_diff": chk, "stats": S, "regime": reg, "named_windows": named, "risks": risks,
           "funding_regime": funding_in_D(fund, f, idx, oos), "fr_hedge_exits_all_history": fr_exits}
    keep = {"bars": bars, "fund": fund, "f": f, "R": R, "oos": oos, "wins": wins}
    return out, keep


def run_rv(K):
    """V4 sleeves and the two-coin book on the common BTC/ETH index."""
    bB, bE = K["BTCUSDT"]["bars"], K["ETHUSDT"]["bars"]
    common = bB.index.intersection(bE.index)
    bB, bE = bB.loc[common], bE.loc[common]
    fB = K["BTCUSDT"]["f"].loc[common]
    fE = K["ETHUSDT"]["f"].loc[common]
    mB = core.Market(bB, K["BTCUSDT"]["fund"])
    mE = core.Market(bE, K["ETHUSDT"]["fund"])
    wins = core.windows(common)
    oos = walkforward.oos_mask(common, wins)
    out, Rr = {"common_bars": len(common), "sleeves": {}}, {}
    for own, f_own, f_oth, m_own, m_oth, is_btc in (("BTCUSDT", fB, fE, mB, mE, True), ("ETHUSDT", fE, fB, mE, mB, False)):
        t = rv_targets(f_own, f_oth, is_btc)
        res = run_legs([(m_own, stitch_oos(t["own_spot"], oos), False), (m_own, stitch_oos(t["own_perp"], oos), True),
                        (m_oth, stitch_oos(t["oth_spot"], oos), False), (m_oth, stitch_oos(t["oth_perp"], oos), True)])
        assert res["gross"].max() <= GROSS_MAX + 1e-12
        bh = run_legs([(m_own, stitch_oos(np.ones(len(common)), oos), False)])
        naked = run_legs([(m_own, stitch_oos(np.where(f_own["D"].values > 0, 0.0, 1.0), oos), False),
                          (m_own, stitch_oos(np.where(f_own["D"].values > 0, -1.0, 0.0), oos), True)])
        flat = run_legs([(m_own, stitch_oos(np.where(f_own["D"].values > 0, 0.0, 1.0), oos), False)])
        sb = stats(bh, common, wins, oos)
        sv = stats(res, common, wins, oos, sb["folds"])
        sv["significance"] = signif(res["r_net"], bh["r_net"], common, oos)
        Dm = (held(f_own["D"].values) > 0) & oos
        name_r = {"BH_spot": bh["r_net"], "V4_rv_bear": res["r_net"], "R_flat": flat["r_net"], "R_naked": naked["r_net"]}
        reg = regime_analysis(name_r, f_own, common, oos, (bB if is_btc else bE)["close"].values)
        out["sleeves"][own] = {"stats": {"BH_spot_common": sb, "V4_rv_bear": sv}, "risks": leg_risks(res, common, oos, Dm),
                               "regime": reg, "named_windows": named_windows(name_r, common),
                               "long_btc_share_in_D": float(np.mean((t["own_spot" if is_btc else "oth_spot"] > 0)[held(f_own["D"].values) > 0]))}
        Rr[own] = (res, bh)
    # the book: two never-rebalanced half sleeves vs never-rebalanced half-and-half spot buy-and-hold
    def book(r1, r2):
        e1 = np.cumprod(1 + np.where(oos, r1, 0.0))
        e2 = np.cumprod(1 + np.where(oos, r2, 0.0))
        eq = 0.5 * e1 + 0.5 * e2
        return np.diff(eq, prepend=1.0) / np.concatenate([[1.0], eq[:-1]])
    rb = book(Rr["BTCUSDT"][0]["r_net"], Rr["ETHUSDT"][0]["r_net"])
    rbh = book(Rr["BTCUSDT"][1]["r_net"], Rr["ETHUSDT"][1]["r_net"])
    ch = Rr["BTCUSDT"][0]["changed"] | Rr["ETHUSDT"][0]["changed"]
    z = np.zeros(len(common))
    pseudo = lambda r, c: {"r_net": r, "changed": c, "turnover": z, "gross": z, "net": z, "spot_pnl": z, "perp_pnl": z,
                           "funding": z, "costs": z, "fees": z}
    sbh = stats(pseudo(rbh, np.zeros(len(common), bool)), common, wins, oos)
    sbk = stats(pseudo(rb, ch), common, wins, oos, sbh["folds"])
    sbk["significance"] = signif(rb, rbh, common, oos)
    Dany = ((held(fB["D"].values) > 0) | (held(fE["D"].values) > 0)) & oos
    out["book"] = {"BH_half_half": sbh, "V4_rv_bear_book": sbk,
                   "D_any_bars": {"V4_rv_bear_book": float(np.prod(1 + rb[Dany]) - 1), "BH_half_half": float(np.prod(1 + rbh[Dany]) - 1)},
                   "named_windows": named_windows({"BH_half_half": rbh, "V4_rv_bear_book": rb}, common)}
    return out


def worth_registering(C, RV):
    """The registered descriptive bar: on BOTH coins Sharpe > spot B&H's, max DD <= 0.75 x B&H's, pooled D-bar return
    above R-flat's and R-naked's."""
    out = {}
    for v in VARIANTS:
        per = {}
        for a in ASSETS:
            if v == "V4_rv_bear":
                sl = RV["sleeves"][a]
                s, b = sl["stats"]["V4_rv_bear"], sl["stats"]["BH_spot_common"]
                pool = sl["regime"]["pooled"]
            else:
                s, b = C[a]["stats"][v], C[a]["stats"]["BH_spot"]
                pool = C[a]["regime"]["pooled"]
            c1 = s["sharpe"] > b["sharpe"]
            c2 = s["max_drawdown"] <= 0.75 * b["max_drawdown"]
            c3 = pool[v]["D_bars"] > pool["R_flat"]["D_bars"] and pool[v]["D_bars"] > pool["R_naked"]["D_bars"]
            per[a] = {"sharpe_gt_bh": bool(c1), "dd_le_075_bh": bool(c2), "D_beats_flat_and_naked": bool(c3)}
        out[v] = {"per_coin": per, "meets": bool(all(all(x.values()) for x in per.values()))}
    return out


def clean(o):
    if isinstance(o, dict):
        return dict((str(k), clean(v)) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        x = float(o)
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    return o


# ------------------------------------------------------------------ report

def pct(x, d=1):
    return "n/a" if x is None else ("%+.*f%%" % (d, 100 * x))


def report(J):
    L = []
    w = L.append
    w("# H37 study: hedged long-short structures for BTC and ETH downtrends (exploration, development data only)")
    w("")
    w("Registered in `research/HYPOTHESES.md` (H37, %s) before this code existed. **Not a loop round**: no loop rule is "
      "changed, nothing here is a pass, and the loop count (1,910) is unchanged. Sealed holdout 2025-11-11 .. 2026-11-11 "
      "never loaded (`core.load(..., dev_only=True)`; last bar used: %s). Span: the loop's out-of-sample folds %s .. %s "
      "(%d folds). Costs: 0.10%% a side on every leg + half spread 0.5 bp + slippage 0.10 x bar vol; real perp funding on "
      "every perp leg (paid or received); spot legs pay none. Generated %s." % (
          REGISTERED_UTC, J["BTCUSDT"]["last"], J["BTCUSDT"]["oos"][0], J["BTCUSDT"]["oos"][1], J["BTCUSDT"]["folds"],
          J["generated_utc"]))
    w("")
    w("Downtrend rule D: last daily close < SMA200 and SMA200 below its value 20 days earlier (closed daily bars via "
      "`data.htf_on_15`). V6 (agent hedge ratio) was not run (see HYPOTHESES.md). Spot buy-and-hold check: equals the "
      "harness's own to %.1e (BTC) / %.1e (ETH)." % (J["BTCUSDT"]["bh_matches_harness_max_abs_diff"],
                                                       J["ETHUSDT"]["bh_matches_harness_max_abs_diff"]))
    w("")
    order = ["BH_spot"] + [v for v in VARIANTS if v != "V4_rv_bear"] + REFS
    for a in ASSETS:
        C = J[a]
        S = C["stats"]
        rv = J["rv"]["sleeves"][a]["stats"]
        w("## %s, full development span (%s .. %s)" % (a, C["oos"][0], C["oos"][1]))
        w("")
        w("| Strategy | Total return | CAGR | Sharpe | Max DD (peak .. trough) | Calmar | Trades/yr | Fold share (of differing folds) | Folds > 0 | Avg net | p vs B&H |")
        w("|---|---|---|---|---|---|---|---|---|---|---|")

        def row(nm, s, lab=None):
            sig = s.get("significance", {})
            fsd = s.get("fold_share_among_differing")
            fs = "-" if nm == "BH_spot" else "%.0f%% (%s of %d)" % (
                100 * s.get("fold_share", 0), "n/a" if fsd is None else "%.0f%%" % (100 * fsd), s.get("folds_differing_from_bh", 0))
            w("| %s | %s | %s | %.2f | %s (%s .. %s) | %.2f | %.1f | %s | %s | %.2f | %s |" % (
                lab or LABEL[nm], pct(s["total_return"], 0), pct(s["cagr"]), s["sharpe"], pct(-s["max_drawdown"], 0),
                s["dd_peak"], s["dd_trough"], s["calmar"], s["trades_per_year"], fs,
                "%.0f%%" % (100 * s["positive_fold_share"]), s["avg_net"],
                ("%.3f" % sig["p"]) if sig else "-"))
        for nm in order:
            row(nm, S[nm])
        row("V4_rv_bear", rv["V4_rv_bear"], LABEL["V4_rv_bear"] + " (common index)")
        w("")
        w("Attribution per year over the span (sums of per-bar contributions, fraction of equity): spot leg / perp leg "
          "price / funding (+ received) / costs.")
        w("")
        w("| Strategy | Spot leg | Perp leg price | Funding | Costs | Worst 7-day perp leg (squeeze) | Worst bar (gap) |")
        w("|---|---|---|---|---|---|---|")
        for nm in order:
            s, rk = S[nm], C["risks"][nm]
            sq = ("%s (to %s)" % (pct(rk["worst_7d_perp_leg"]), rk["worst_7d_perp_leg_end"])) if "worst_7d_perp_leg" in rk else "-"
            w("| %s | %s | %s | %s | %s | %s | %s (%s) |" % (LABEL[nm], pct(s["spot_pnl_per_year"]), pct(s["perp_pnl_per_year"]),
                                                          pct(s["funding_per_year"], 2), pct(-s["costs_per_year"], 2), sq,
                                                          pct(rk["worst_bar"], 2), rk["worst_bar_at"][:16]))
        s, rk = rv["V4_rv_bear"], J["rv"]["sleeves"][a]["risks"]
        w("| %s | %s | %s | %s | %s | %s | %s (%s) |" % (LABEL["V4_rv_bear"], pct(s["spot_pnl_per_year"]), pct(s["perp_pnl_per_year"]),
                                                      pct(s["funding_per_year"], 2), pct(-s["costs_per_year"], 2),
                                                      "%s (to %s)" % (pct(rk.get("worst_7d_perp_leg")), rk.get("worst_7d_perp_leg_end")),
                                                      pct(rk["worst_bar"], 2), rk["worst_bar_at"][:16]))
        w("")
        reg = C["regime"]
        fr = C["funding_regime"]
        w("### %s inside downtrends" % a)
        w("")
        w("D held on %.0f%% of the span; %d D turn-ons, %d of them episodes shorter than 30 days (whipsaw). Median fall from "
          "the 180-day high close before D turned on: %s (late entry). Funding: %.0f%% of D days net negative (U days %.0f%%); "
          "annualised funding rate in D %s, in U %s." % (
              100 * reg["d_share_of_span"], reg["turn_ons"], reg["short_episodes_lt30d"], pct(reg["median_fall_before_turn_on"], 0),
              100 * (fr["neg_funding_day_share_D"] or 0), 100 * (fr["neg_funding_day_share_U"] or 0), pct(fr["funding_ann_D"]),
              pct(fr["funding_ann_U"])))
        w("")
        rvp = J["rv"]["sleeves"][a]["regime"]["pooled"]["V4_rv_bear"]
        w("Pooled returns: all D bars, all U bars, D bars in short (< 30 d) episodes, D bars in long episodes.")
        w("")
        w("| Strategy | D bars | U bars | D short episodes | D long episodes | Funding in D /yr of D | Perp price in D /yr of D |")
        w("|---|---|---|---|---|---|---|")
        for nm in order:
            p, rk = reg["pooled"][nm], C["risks"][nm]
            w("| %s | %s | %s | %s | %s | %s | %s |" % (LABEL[nm], pct(p["D_bars"], 0), pct(p["U_bars"], 0), pct(p["D_short_episodes"], 0),
                                                     pct(p["D_long_episodes"], 0), pct(rk["funding_in_D_per_D_year"], 2),
                                                     pct(rk["perp_price_in_D_per_D_year"])))
        rk = J["rv"]["sleeves"][a]["risks"]
        w("| %s | %s | %s | %s | %s | %s | %s |" % (LABEL["V4_rv_bear"], pct(rvp["D_bars"], 0), pct(rvp["U_bars"], 0),
                                                 pct(rvp["D_short_episodes"], 0), pct(rvp["D_long_episodes"], 0),
                                                 pct(rk["funding_in_D_per_D_year"], 2), pct(rk["perp_price_in_D_per_D_year"])))
        w("")
        w("Each D window found by the rule (episodes merged across gaps <= 14 days, >= 30 days kept): return over the window.")
        w("")
        cols = ["BH_spot", "V1_dial0", "V2_dialm05", "V3_dial0_fund", "V5_fr_hedge", "R_flat", "R_naked", "R_naked_FR"]
        w("| Window | Days | D share | Fall before D on | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        rvw = dict((x["start"], x) for x in J["rv"]["sleeves"][a]["regime"]["windows"])
        for x in reg["windows"]:
            r = x["returns"]
            v4 = rvw.get(x["start"], {}).get("returns", {}).get("V4_rv_bear")
            vals = [pct(r[c], 0) for c in cols]
            vals.insert(4, pct(v4, 0) if v4 is not None else "-")
            w("| %s .. %s | %.0f | %.0f%% | %s | %s |" % (x["start"], x["end"], x["days"], 100 * x["d_bar_share"],
                                                        pct(x["fall_before_turn_on"], 0), " | ".join(vals)))
        w("")
        w("Named calendar windows (picked with hindsight by the owner's request; reference only):")
        w("")
        w("| Window | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        rvn = dict((x["window"], x) for x in J["rv"]["sleeves"][a]["named_windows"])
        for x in C["named_windows"]:
            r = x["returns"]
            vals = [pct(r[c], 0) for c in cols]
            vals.insert(4, pct(rvn[x["window"]]["returns"]["V4_rv_bear"], 0))
            w("| %s (%s .. %s) | %s |" % (x["window"], x["start"], x["end"], " | ".join(vals)))
        w("")
        w("Calendar years (net):")
        w("")
        yrs = sorted(S["BH_spot"]["years_table"].keys())
        w("| Strategy | " + " | ".join(str(y) for y in yrs) + " |")
        w("|---|" + "---|" * len(yrs))
        for nm in order:
            w("| %s | %s |" % (LABEL[nm], " | ".join(pct(S[nm]["years_table"].get(y), 0) for y in yrs)))
        w("| %s | %s |" % (LABEL["V4_rv_bear"], " | ".join(pct(rv["V4_rv_bear"]["years_table"].get(y), 0) for y in yrs)))
        w("")
        w("V4 sleeve: share of its D bars spent long BTC / short ETH: %.0f%%." % (100 * J["rv"]["sleeves"][a]["long_btc_share_in_D"]))
        w("")
        ex = C["fr_hedge_exits_all_history"]
        w("V5 hedge exits (all history incl. warm-up before the span): " + ", ".join(
            "%s %d (avg %.0f h)" % (k, v["count"], v["avg_hours"]) for k, v in sorted(ex.items())) + ".")
        w("")
    B = J["rv"]["book"]
    w("## V4 two-coin book (half BTC sleeve, half ETH sleeve, never rebalanced) vs half-and-half spot buy-and-hold")
    w("")
    w("| Book | Total return | CAGR | Sharpe | Max DD | Calmar | Trades/yr | Fold share | Folds > 0 | Return on bars with D on either coin |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for nm, lab in (("BH_half_half", "Half-and-half spot buy-and-hold"), ("V4_rv_bear_book", "V4 rv_bear book")):
        s = B[nm]
        w("| %s | %s | %s | %.2f | %s | %.2f | %.1f | %s | %.0f%% | %s |" % (
            lab, pct(s["total_return"], 0), pct(s["cagr"]), s["sharpe"], pct(-s["max_drawdown"], 0), s["calmar"],
            s["trades_per_year"], "-" if nm == "BH_half_half" else "%.0f%%" % (100 * s["fold_share"]),
            100 * s["positive_fold_share"], pct(B["D_any_bars"][nm], 0)))
    w("")
    w("## The registered bar for a later formal registration (descriptive)")
    w("")
    w("On BOTH coins: Sharpe above spot buy-and-hold's, max drawdown at most 0.75 x buy-and-hold's, pooled D-bar return "
      "above R-flat's and R-naked's.")
    w("")
    w("| Variant | BTC: Sharpe > B&H / DD <= 0.75 B&H / D beats flat and naked | ETH: same | Meets |")
    w("|---|---|---|---|")
    yn = lambda b: "yes" if b else "no"
    for v, x in J["worth_registering"].items():
        pc = x["per_coin"]
        w("| %s | %s | %s | **%s** |" % (LABEL[v], " / ".join(yn(b) for b in pc["BTCUSDT"].values()),
                                         " / ".join(yn(b) for b in pc["ETHUSDT"].values()), yn(x["meets"])))
    w("")
    w("p vs B&H: paired block bootstrap of the daily Sharpe gap against spot buy-and-hold (normal approximation, "
      "one-sided); this study's own level is 0.05 / %d = %.4f, and the loop's cumulative level (0.05 / 1,910) is far "
      "stricter. Information only." % (N_VARIANTS, 0.05 / N_VARIANTS))
    w("")
    if J.get("findings"):
        w("## What it means")
        w("")
        for line in J["findings"]:
            w(line)
        w("")
    return "\n".join(L) + "\n"


def main():
    from engine15.rl import resources
    resources.low_priority()
    os.makedirs(OUT, exist_ok=True)
    if "--report" in sys.argv:                          # rebuild study.md from study.json
        with open(os.path.join(OUT, "study.json"), encoding="utf-8") as fh:
            J = json.load(fh)
        J["findings"] = FINDINGS
        with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
            fh.write(report(J))
        return
    t0 = time.time()
    J, K = {}, {}
    for a in ASSETS:
        log("%s: running" % a)
        J[a], K[a] = run_coin(a)
        log("%s: done (%.0fs)" % (a, time.time() - t0))
    J["rv"] = run_rv(K)
    log("rv: done (%.0fs)" % (time.time() - t0))
    J["worth_registering"] = worth_registering({a: J[a] for a in ASSETS}, J["rv"])
    J["generated_utc"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    J["registered_utc"] = REGISTERED_UTC
    J["n_variants"] = N_VARIANTS
    J["labels"] = LABEL
    J["findings"] = FINDINGS
    with open(os.path.join(OUT, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(clean(J), fh, indent=1)
    with open(os.path.join(OUT, "study.md"), "w", encoding="utf-8") as fh:
        fh.write(report(J))
    log("written %s (%.0fs)" % (OUT, time.time() - t0))


if __name__ == "__main__":
    main()
