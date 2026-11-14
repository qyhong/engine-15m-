# -*- coding: utf-8 -*-
"""playbook7 -- H37's V4 "rv_bear" (BTC/ETH relative value in downtrends), run FORWARD as a paper book. PAPER ONLY.
NOT PASSED.

The owner asked, 13 Nov 2026: "Also explore long-short strategies. It does not need fully naked short." The H37 study
(research/longshort_study.py, research/out/longshort/study.md; registered in research/HYPOTHESES.md 13 Nov 2026 09:33
UTC) found no variant worth a formal loop registration. V4 was the only structure that made money in downtrends on both
coins. The owner approved it as a forward paper shadow book the same day ("Yes"). It is exploration: no loop rule is
changed and no loop variant is added.

THE RULE (frozen exactly as H37's V4; research/longshort_study.py: daily_feats, rv_targets, run_legs):
  D (a coin's downtrend) = its last closed UTC daily close is below its 200-day average AND that average is lower than
  20 days earlier. Daily values reach the 15m clock through engine15.data.htf_on_15 (closed daily bars only).
  Each sleeve has its "own" coin:
    own coin not in D -> own coin spot long 1x (no hedge).
    own coin in D     -> long the STRONGER coin spot 0.75x and short the WEAKER coin perp 0.75x, where stronger = the
                         higher 30-day log return of daily closes (a tie goes to BTC). Gross 1.5x, net about 0.
  BTC sleeve and ETH sleeve, each its own $10,000 paper book from REGISTERED.

ACCOUNTING (as H37): a target decided at the close of bar t is held from the open of bar t + 1. Four legs per sleeve
(own spot, own perp, other spot, other perp), each on its coin's 15m bars on the common BTC/ETH index: gross = position
x (next open / open - 1); fee 0.10% a side of |trade|; half spread 0.5 bp; slippage 0.10 x the 96-bar per-bar vol known
at the decision; perp legs pay (or receive) funding at each settlement (+rate costs a long, pays a short); spot legs pay
none. The spot-perp basis is ignored (both legs use the same series), as in the study.

FORWARD ONLY. Unlike playbook4 (which waits for its rule's next entry), the book takes the rule's position at the first
close after REGISTERED, as its spot buy-and-hold comparison does; nothing before that counts. A trade is one run of the
same four-leg position; when the rule switches state the old trade ends and the new one starts at the same open, and the
switching costs fall on the new trade. Stateless: the book is recomputed from the bars at each step from a FIXED warm-up
anchor (REGISTERED - WARMUP_DAYS); the same bars give the same rows. Rows follow docs/PLAYBOOK_INTERFACE.md: asset = the
sleeve's own coin, side = the sign of the own coin's net exposure, no stop or targets, why_out "RULE" or "OPEN", r None.
"""
import numpy as np
import pandas as pd

from . import data
from . import playbook4 as p4

REGISTERED = "2026-11-13 11:30"     # UTC: forward start; owner-approved 13 Nov 2026 ("Yes")
STAKE = 10000.0
WARMUP_DAYS = 450                   # 200-day average + 20-day slope + 30-day return, with room
BAR_MS = p4.BAR_MS
DAY_MS = p4.DAY_MS
ASSETS = ("BTCUSDT", "ETHUSDT")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
OTHER = {"BTCUSDT": "ETHUSDT", "ETHUSDT": "BTCUSDT"}

# ---------------------------------------------------------------- frozen H37 V4 parameters (do not change)
SMA_DAYS = 200
SLOPE_DAYS = 20
RET_DAYS = 30
SIZE_D = 0.75                       # each leg in D (gross 1.5x)
SIZE_U = 1.0                        # own spot outside D
FEE = p4.FEE
HS = p4.HALF_SPREAD_BPS * 1e-4
SLIP = p4.SLIP_COEF
LEGS = ("own_spot", "own_perp", "oth_spot", "oth_perp")

NOT_PASSED = ("From the H37 hedged long-short study (exploration, development data only); NOT passed: no H37 variant met "
              "the bar for a formal loop registration. V4 was the only structure that made money in downtrends on both "
              "coins; fold share 24%, not significant. Running forward on paper to collect unseen evidence.")
DETAIL = ("History (Oct 2020 - Nov 2025, development span, after 0.10% fees and funding): BTC sleeve CAGR +78.5%, Sharpe "
          "1.29, max DD 57% vs spot buy-and-hold +56.2%, 1.03, 77%; ETH sleeve +80.8%, 1.19, 60% vs +56.6%, 0.96, 81%. "
          "Most of the gain came from ETH falling against BTC in 2021-2025; a sharp ETH rebound against BTC is its squeeze "
          "risk. The holdout year was not used.")
BOOKS = {
    "p7_rvbear": {"title": "Pair book: BTC/ETH relative value in downtrends (H37 V4), forward paper; NOT passed",
                  "short": "Pair book", "hypothesis": "H37 V4 forward", "registered": REGISTERED, "assets": ASSETS,
                  "scoreboard_title": "Strategy: pair book, BTC/ETH relative value in downtrends, H37 V4 (NOT passed, "
                                      "forward paper)"},
}

LAST_STATE = {}


def reg_ms():
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


# ---------------------------------------------------------------- readings (row t uses closed bars <= t only)
def daily_feats(bars):
    """-> frame on the 15m index: D (0/1) and ret30 (30-day log return of daily closes), from the last UTC day closed
    by each row's close. As research/longshort_study.daily_feats (the two columns V4 uses)."""
    d1 = data.resample(bars[["open", "high", "low", "close"]].astype(float).assign(volume=0.0, taker_buy=0.0), "1D")
    c = d1["close"]
    sma = c.rolling(SMA_DAYS).mean()
    down = ((c < sma) & (sma < sma.shift(SLOPE_DAYS))).astype(float)
    f = pd.DataFrame({"D": down, "ret30": np.log(c).diff(RET_DAYS), "sma200": sma, "close_d": c}, index=d1.index)
    out = data.htf_on_15(bars, "1D", f)
    out["D"] = out["D"].fillna(0.0)
    return out


def targets(f_own, f_oth, own_is_btc):
    """As research/longshort_study.rv_targets. -> dict leg -> target array."""
    D = f_own["D"].values > 0
    ro = np.nan_to_num(f_own["ret30"].values, nan=0.0)
    rx = np.nan_to_num(f_oth["ret30"].values, nan=0.0)
    strong = (ro > rx) | ((ro == rx) & own_is_btc)
    return {"own_spot": np.where(D, np.where(strong, SIZE_D, 0.0), SIZE_U),
            "own_perp": np.where(D & ~strong, -SIZE_D, 0.0),
            "oth_spot": np.where(D & ~strong, SIZE_D, 0.0),
            "oth_perp": np.where(D & strong, -SIZE_D, 0.0)}


def held(target):
    t = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    pos = np.zeros_like(t)
    pos[1:] = t[:-1]
    return pos


def legs_frame(pos, M_own, M_oth):
    """pos: dict leg -> held position per bar. -> dict of per-bar fractions of equity."""
    n = len(M_own["r_px"])
    z = np.zeros(n)
    out = {"gross": z.copy(), "fee": z.copy(), "other": z.copy(), "funding": z.copy()}
    for leg in LEGS:
        M = M_own if leg.startswith("own") else M_oth
        p = pos[leg]
        a = np.abs(np.diff(p, prepend=0.0))
        out["gross"] += p * M["r_px"]
        out["fee"] += FEE * a
        out["other"] += HS * a + SLIP * M["vol_dec"] * a
        if leg.endswith("perp"):
            out["funding"] -= p * M["rate"]                       # + = received
    out["r_net"] = out["gross"] - out["fee"] - out["other"] + out["funding"]
    return out


def sleeve(own, b_own, b_oth, fu_own, fu_oth, rms):
    """One sleeve on the common index. -> dict with features, targets, forward positions, frame, equity, trades."""
    F_own, F_oth = p4.features(b_own), p4.features(b_oth)
    M_own, M_oth = p4.market(F_own, fu_own), p4.market(F_oth, fu_oth)
    f_own, f_oth = daily_feats(b_own), daily_feats(b_oth)
    T = targets(f_own, f_oth, own == "BTCUSDT")
    cm = F_own["close_ms"]
    n = len(cm)
    keep = np.zeros(n)
    keep[1:] = (cm[:-1] > rms).astype(float)                      # held at t was decided at the close of t - 1
    pos = dict((leg, held(T[leg]) * keep) for leg in LEGS)
    fr = legs_frame(pos, M_own, M_oth)
    eq = STAKE * np.cumprod(1.0 + fr["r_net"])
    bh = p4.bh_spot(F_own, M_own, rms)
    vec = np.stack([pos[leg] for leg in LEGS], axis=1)
    trades = []
    fwd = np.flatnonzero(keep > 0)
    if len(fwd):
        s = int(fwd[0])
        for t in range(s + 1, n + 1):
            if t == n or not np.array_equal(vec[t], vec[s]):
                closed = t < n
                e = t - 1
                eprev = eq[s - 1:e] if s > 0 else np.concatenate([[STAKE], eq[:e]])
                seg = slice(s, e + 1)
                e0 = eq[s - 1] if s > 0 else STAKE
                trades.append({"s": s, "e": e, "closed": closed, "x": t if closed else None, "vec": vec[s].copy(),
                               "e0": float(e0), "e1": float(eq[e]), "pnl": float(eq[e] - e0),
                               "fees": float(np.sum(fr["fee"][seg] * eprev)),
                               "costs": float(np.sum((fr["other"][seg] - fr["funding"][seg]) * eprev)),
                               "funding": float(np.sum(fr["funding"][seg] * eprev)),
                               "entry": float(F_own["o"][s]), "exit": float(F_own["o"][t]) if closed else None})
                s = t
    return {"F": F_own, "F_oth": F_oth, "f_own": f_own, "f_oth": f_oth, "T": T, "pos": pos, "frame": fr, "eq": eq,
            "bh": bh, "trades": trades, "keep": keep}


# ---------------------------------------------------------------- words
def legs_text(own, v):
    a, o = SHORT_NAME[own], SHORT_NAME[OTHER[own]]
    parts = []
    for leg, x in zip(LEGS, v.tolist()):
        if x == 0:
            continue
        coin = a if leg.startswith("own") else o
        kind = "spot" if leg.endswith("spot") else "perp"
        parts.append("%s %s %.2fx %s" % ("long" if x > 0 else "short", coin, abs(x), kind))
    return " / ".join(parts) if parts else "flat"


def _side(own, v):
    net = v[0] + v[1]
    return 1 if net > 0 else -1 if net < 0 else 0


def sentence(own, t, S):
    a = SHORT_NAME[own]
    cm = S["F"]["close_ms"]
    v = t["vec"]
    inD = v[0] != SIZE_U
    why = ("%s in its downtrend (below a falling 200-day average): long the stronger coin, short the weaker" % a
           if inD else "%s not in its downtrend: spot long" % a)
    head = "Pair book, %s sleeve: %s from the %s UTC close (%s); %s at %s" % (
        a, legs_text(own, v), p4._utc(cm[t["s"] - 1]), why, a, p4._px(t["entry"]))
    if t["closed"]:
        out = "%s. Ended at the %s UTC close when the rule changed state (%s at %s): %+.2f%%, %+.2f USD after %.2f USD " \
              "fees and %+.2f USD funding." % (head, p4._utc(cm[t["e"]]), a, p4._px(t["exit"]),
                                               100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["funding"])
    else:
        out = "%s. Open, marked at the %s UTC close (%s %s): %+.2f%%, %+.2f USD so far (fees %.2f USD, funding %+.2f USD)." % (
            head, p4._utc(cm[-1]), a, p4._px(S["F"]["c"][-1]), 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["funding"])
    return out + " Paper, forward, NOT passed."


def _row(own, t, S):
    cm = S["F"]["close_ms"]
    v = t["vec"]
    return {"book": "p7_rvbear", "asset": own, "status": "CLOSED" if t["closed"] else "OPEN", "side": _side(own, v),
            "setup_utc": p4._utc(cm[t["s"] - 1]), "entry_utc": p4._utc(cm[t["s"] - 1]), "entry": p4._rnd(t["entry"]),
            "stop": None, "target_1": None, "target_2": None,
            "exit_utc": p4._utc(cm[t["e"]]) if t["closed"] else None, "exit": p4._rnd(t["exit"]),
            "why_out": "RULE" if t["closed"] else "OPEN", "r": None,
            "pnl_usd": p4._rnd(t["pnl"], 2), "fees_usd": p4._rnd(t["fees"], 2), "costs_usd": p4._rnd(t["costs"], 2),
            "funding_usd": p4._rnd(t["funding"], 2), "pnl_pct": p4._rnd(100 * t["pnl"] / t["e0"], 3),
            "legs": dict((leg, float(x)) for leg, x in zip(LEGS, v.tolist())), "legs_text": legs_text(own, v),
            "equity_before_usd": p4._rnd(t["e0"], 2), "equity_after_usd": p4._rnd(t["e1"], 2),
            "text": sentence(own, t, S)}


def _state(own, S, rms):
    F, f = S["F"], S["f_own"]
    i = len(F["c"]) - 1
    cm = F["close_ms"]
    eq, bh = S["eq"], S["bh"]
    fwd = cm > rms
    want = np.array([S["T"][leg][i] for leg in LEGS])
    r30 = f["ret30"].values[i]
    r30o = S["f_oth"]["ret30"].values[i]
    st = {"last_close_utc": p4._utc(cm[i]), "close": p4._rnd(F["c"][i]),
          "rule_exposure": p4._rnd(want[0] + want[1], 4), "rule_legs": legs_text(own, want),
          "downtrend": bool(f["D"].values[i] > 0),
          "sma200_daily": p4._rnd(f["sma200"].values[i], 2),
          "momentum_30d_pct": p4._rnd(100 * (np.exp(r30) - 1) if r30 == r30 else None, 2),
          "other_momentum_30d_pct": p4._rnd(100 * (np.exp(r30o) - 1) if r30o == r30o else None, 2),
          "daily_direction": int(np.sign(r30)) if r30 == r30 else 0,
          "equity_usd": p4._rnd(eq[i] if len(eq) else STAKE, 2),
          "return_pct": p4._rnd(100 * (eq[i] / STAKE - 1) if len(eq) else 0.0, 3),
          "bh_spot_equity_usd": p4._rnd(bh[i] if len(bh) else STAKE, 2),
          "bh_spot_return_pct": p4._rnd(100 * (bh[i] / STAKE - 1) if len(bh) else 0.0, 3),
          "max_dd_pct": p4._rnd(100 * p4._dd(eq[fwd]), 3), "bh_max_dd_pct": p4._rnd(100 * p4._dd(bh[fwd]), 3),
          "forward_trades": len(S["trades"]), "closed": sum(1 for t in S["trades"] if t["closed"])}
    tr = S["trades"]
    if tr and not tr[-1]["closed"]:
        v = tr[-1]["vec"]
        since = p4._utc(cm[tr[-1]["s"] - 1])
        if v[0] == SIZE_U and not v[1:].any():
            st["book_position"] = "long %.2fx since %s UTC" % (SIZE_U, since)
        else:
            st["book_position"] = "%s since %s UTC" % (legs_text(own, v), since)
    else:
        st["book_position"] = "flat: waiting for the first close after the forward start (%s UTC)" % REGISTERED
    return st


# ---------------------------------------------------------------- live interface
def step(bars=None, now_ms=None, funding=None):
    """bars: {asset: 15m frame} (None loads both coins from disk); funding: {asset: frame rate / settle_ms} (None reads
    data/<asset>_funding.csv). -> rows (docs/PLAYBOOK_INTERFACE.md)."""
    rms = reg_ms()
    anchor = pd.Timestamp(REGISTERED, tz="UTC") - pd.Timedelta(days=WARMUP_DAYS)
    LAST_STATE.clear()
    B, FU = {}, {}
    for a in ASSETS:
        try:
            df = data.load(a) if bars is None else bars.get(a)
            if df is None:
                return []
            fu = (funding or {}).get(a)
            if fu is None:
                fu = p4.funding_frame(data.load_funding(a))
        except Exception:
            return []
        df = df[df.index >= anchor][["open", "high", "low", "close"]].astype(float)
        if now_ms is not None:
            df = df[p4._to_ms(df.index) + BAR_MS <= int(now_ms)]
        B[a], FU[a] = df, fu
    common = B["BTCUSDT"].index.intersection(B["ETHUSDT"].index)
    if len(common) < 200:
        return []
    last_close = int(p4._to_ms(common[-1:])[0]) + BAR_MS
    for a in ASSETS:
        B[a] = B[a].loc[common]
        f = FU[a]
        if f is not None and len(f):
            FU[a] = f[np.asarray(f["settle_ms"], dtype="int64") <= last_close]
    rows = []
    for own in ASSETS:
        S = sleeve(own, B[own], B[OTHER[own]], FU[own], FU[OTHER[own]], rms)
        for t in S["trades"]:
            rows.append(_row(own, t, S))
        LAST_STATE.setdefault("p7_rvbear", {})[own] = _state(own, S, rms)
    return rows


def _totals(closed):
    return p4._totals(closed)


def rule_text(book="p7_rvbear"):
    return ("%s Each coin's downtrend = its last daily close below its 200-day average AND that average lower than 20 "
            "days earlier (closed daily bars only). Outside its downtrend a sleeve holds its own coin spot long 1x. In "
            "its downtrend it holds the STRONGER coin (higher 30-day return) spot long 0.75x and the WEAKER coin perp short "
            "0.75x: it profits from the gap between the two coins, not from the market's direction. Decided at a 15m "
            "close, filled at the next open; fees 0.10%% a side, spread 0.5 bp, volatility slippage, real perp funding "
            "paid or received on the short leg. %s BTC sleeve and ETH sleeve, each its own $10,000 paper book from %s "
            "UTC." % (NOT_PASSED, DETAIL, REGISTERED))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1",
                                              "target_2", "r", "pnl_usd", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"] + " UTC",
                     "not_passed": True, "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r.get(k)) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit",
                                                              "why_out", "r", "pnl_usd", "pnl_pct", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "books": dict(LAST_STATE.get(book, {})),
                     "pass_rule": ("No forward verdict before 30 closed forward trades (both sleeves together); then, "
                                   "after fees and funding, against spot buy-and-hold of each coin since go-live. A "
                                   "forward pass would still not make it a passed rule in history."),
                     "note": NOT_PASSED + " " + DETAIL}
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"])
        for a, s in b["books"].items():
            print("  ", a, s)


if __name__ == "__main__":
    main()
