# -*- coding: utf-8 -*-
"""playbook -- two standalone rule-based strategy books on 15-minute bars. PAPER ONLY.

Owner, 11 Nov 2026: "include strategy to profit from liquidation hunt. Also, breakout trap."
Interface: docs/PLAYBOOK_INTERFACE.md. Plain-English rules and history: docs/PLAYBOOK.md.
History study: research/playbook_study.py -> research/out/playbook.md / .json.

P1  LIQUIDATION HUNT (stop-run fade, hypothesis H6). Price spikes through an obvious liquidity
    pool (where stops and liquidations rest: the last confirmed 15m swing high / low, the 24h or
    7-day high / low, the prior UTC day's high / low, a round number) by at least k x ATR(14, 15m)
    and closes back on the near side of the pool on the same bar or within m bars, leaving a long
    wick (the wick on the swept side is at least half the range of the sweep candle: the bars from
    the first bar through the pool to the reclaim bar, read as one candle). Fade it at the next
    open: a sweep above -> SHORT. Stop: beyond the sweep's extreme + 0.1 x ATR(15m).
P2  BREAKOUT TRAP (failed breakout, hypothesis H7). A bar CLOSES beyond a level (the high / low of
    the last 48 bars, the prior UTC day's high / low, or the last confirmed 15m swing) for the first
    time - the breakout traders are in - and within j bars a bar closes back inside. Trade the trap
    at the next open: a failed upside breakout -> SHORT. Stop: beyond the highest high (lowest low)
    from the breakout bar to the reclaim bar + 0.1 x ATR(15m). Targets: the range mid, then the
    opposite edge of the range.

THE FRAME (all books): closed bars only; every level a bar is tested against is the one known at
the close of the bar BEFORE it (swings only once confirmed); the decision is at the close of bar
i and fills at the open of bar i+1 (a fill that gaps beyond the stop is not taken); a stop and a
target inside the same bar count as the stop first; a gap through the stop fills at the open; one
open trade per book per asset; $10,000 a trade; the asset's own fee a side (config asset_cost,
else cost_side). Exit schemes: "struct" = half at Target 1, the rest at Target 2, the stop moved to
the entry from the bar after Target 1 fills; "fixed" = the same with Target 1 at 1R and Target 2
at 2R. Whatever is still open after the hold limit is closed at the next open.

The books are recomputed from the bars at every step from a FIXED warm-up anchor (registration
minus WARMUP_DAYS), so they hold no state and the same bars always give the same rows.
"""
import time

import numpy as np
import pandas as pd

from . import data
from . import indicators as ind
from .config import CFG

REGISTERED = "2026-11-11"
STAKE = 10000.0
WARMUP_DAYS = 450                  # the live books start reading here: enough for the daily trend score
BAR_MS = 900000
DAY_MS = 86400000
ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P 500"}

# ---------------------------------------------------------------- fixed constants (both books)
SWING_K = 5                        # the 15m swing of structure.py: known 5 bars (75 min) after it forms
STOP_PAD_ATR = 0.1                 # stops sit 0.1 x ATR(15m) beyond the extreme
WICK_MIN = 0.5                     # P1: the swept-side wick is at least half the sweep candle's range
STRUCT_MIN_R = 0.5                 # a structural target nearer than 0.5R is replaced by 1R (T1) / T1 + 1R (T2)
VOL_DAYS = 20                      # volume is compared with the median of the same 15-minute slot, last 20 days
VOL_SURGE = 2.0                    # P1 volume confirmation: 2 x that median
FUND_LOOKBACK = 90                 # P1 funding confirmation: the rate's rank among the last 90 settlements (30 days)
FUND_EXTREME = 0.8                 # ... top fifth against a short-side sweep's longs (bottom fifth for a long)
P2_RANGE_BARS = 48                 # P2 "range" level: the high / low of the last 48 bars (12 hours)
VOL_LOW, VOL_HIGH = 1.0, 1.5       # P2 filters: breakout bar volume below 1x / at least 1.5x its slot median
SHALLOW_ATR = 0.5                  # P2 filter: price went no more than 0.5 x ATR(15m) beyond the level
HOLD = {"p1_liqhunt": 16, "p2_trap": 24}

# ---------------------------------------------------------------- the registered rules
# Chosen on the FIRST half of history only (research/playbook_study.py, docs/PLAYBOOK.md).
# Neither cleared costs on history in either half; they run forward because forward results decide.
#  P1  k0.25 m2 fixed +funding: sweep >= 0.25 ATR, reclaim on the sweep bar or within 2 bars, half at
#      1R / rest at 2R; on BTC / ETH only when funding is in the top (bottom) fifth of its last 90
#      settlements against the swept side (other markets have no funding: unfiltered).
#  P2  pday j2 fixed +with_bias: prior-day high / low, back inside within 2 bars, half at 1R / rest at
#      2R, only when the trade is on the side of the engine's v5 higher-timeframe bias (the breakout
#      went against the bias). Chosen on 115 first-half trades in all: rare and thinly evidenced.
RULES = {
    "p1_liqhunt": {"k": 0.25, "m": 2, "exit": "fixed", "confirm": "funding"},
    "p2_trap": {"level": "pday", "j": 2, "exit": "fixed", "filter": "with_bias"},
}

# Retired books (owner's word): no trade entered at or after the stamp counts; the record before it is kept as is.
# p1_liqhunt: owner "Retire it" (15 Nov 2026) after the post-mortem (research/out/p1_postmortem.md) and H41
# (research/out/liqhunt2/study.md): 37 variants, no edge before costs on 2020-2025 history; 65 live trades, -$1,421.
RETIRED = {"p1_liqhunt": "2026-11-15 06:15"}

BOOKS = {
    "p1_liqhunt": {"title": "Liquidation hunt (retired 15 Nov 2026)", "hypothesis": "H6", "registered": REGISTERED, "assets": ASSETS},
    "p2_trap": {"title": "Breakout trap", "hypothesis": "H7", "registered": REGISTERED, "assets": ASSETS},
}

P1_POOLS_HI = ("swing high", "24h high", "7-day high", "prior-day high", "round number")
P1_POOLS_LO = ("swing low", "24h low", "7-day low", "prior-day low", "round number")
P2_LEVELS = {"n48": ("12-hour high", "12-hour low"), "pday": ("prior-day high", "prior-day low"),
             "swing": ("swing high", "swing low")}


def fee_side(asset):
    return float(CFG.get("asset_cost", {}).get(asset, CFG["cost_side"]))


def _sh(x, d):
    """x shifted d bars later: out[i] = x[i - d] (NaN before the start)."""
    x = np.asarray(x, dtype=float)
    if d == 0:
        return x
    out = np.full(len(x), np.nan)
    out[d:] = x[:-d]
    return out


def _round_levels(c_prev):
    """The round-number grid of levels.py (largest 1 / 2.5 / 5 x 10^n step not above 2% of price):
    -> (the grid number above the prior close, the one below)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        target = 0.02 * c_prev
        expo = np.floor(np.log10(target))
        mant = target / 10.0 ** expo
        step = np.where(mant >= 5.0, 5.0, np.where(mant >= 2.5, 2.5, 1.0)) * 10.0 ** expo
        up = (np.floor(c_prev / step + 1e-9) + 1.0) * step
        dn = (np.ceil(c_prev / step - 1e-9) - 1.0) * step
    return up, dn


def _session_word(ms):
    hr = int((ms % DAY_MS) // 3600000)
    return "Asia" if hr < 7 else "London" if hr < 13 else "New York" if hr < 20 else "Late"


# ---------------------------------------------------------------- readings, all known at bar closes
def prepare(df, asset, funding=None):
    """-> dict of arrays for one asset. Values marked 'prior' are known at the close of the bar
    BEFORE their row; the rest at the close of their own row."""
    df = df[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)
    o, h, l, c, v = (df[k].values for k in ("open", "high", "low", "close", "volume"))
    tb = df["taker_buy"].values
    ms = data.to_ms(df.index)
    n = len(c)
    P = {"asset": asset, "df": df, "n": n, "o": o, "h": h, "l": l, "c": c, "v": v, "ms": ms}
    P["c_prev"] = _sh(c, 1)
    atr = ind.atr_wilder(df).values
    P["atr"], P["atr_prev"] = atr, _sh(atr, 1)
    from .sources import structure
    _st, sw_hi, sw_lo = structure.swings(h, l, SWING_K)
    P["sw_hi"], P["sw_lo"] = _sh(sw_hi, 1), _sh(sw_lo, 1)             # prior: a swing confirmed by the last close
    hs, ls = df["high"], df["low"]
    P["hi24"] = hs.rolling("24h", closed="left").max().values         # prior: bars opened in the last 24h before this one
    P["lo24"] = ls.rolling("24h", closed="left").min().values
    P["hi7d"] = hs.rolling("7D", closed="left").max().values
    P["lo7d"] = ls.rolling("7D", closed="left").min().values
    P["hi24_now"] = hs.rolling("24h").max().values                    # this bar included (targets)
    P["lo24_now"] = ls.rolling("24h").min().values
    day = df.resample("1D", label="left", closed="left").agg({"high": "max", "low": "min"}).dropna()
    pd_ = data.htf_on_15(df, "1D", day)
    P["pdh"], P["pdl"] = _sh(pd_["high"].values, 1), _sh(pd_["low"].values, 1)
    P["rup"], P["rdn"] = _round_levels(P["c_prev"])
    P["n48_hi"] = _sh(hs.rolling(P2_RANGE_BARS).max().values, 1)
    P["n48_lo"] = _sh(ls.rolling(P2_RANGE_BARS).min().values, 1)
    # session VWAP anchored 00:00 UTC (equal weights on a day with no volume on file)
    tp = (h + l + c) / 3.0
    dkey = ms // DAY_MS
    w = np.where(np.isfinite(v) & (v > 0), v, 0.0)
    g = pd.DataFrame({"pw": tp * w, "w": w, "p": tp, "one": 1.0}).groupby(dkey).cumsum()
    with np.errstate(invalid="ignore", divide="ignore"):
        P["vwap"] = np.where(g["w"].values > 0, g["pw"].values / g["w"].values, g["p"].values / g["one"].values)
    # volume against the median of the same 15-minute slot over the prior 20 days
    slot = (ms % DAY_MS) // BAR_MS
    vs = pd.Series(np.where(w > 0, w, np.nan))
    med = vs.groupby(slot).transform(lambda x: x.rolling(VOL_DAYS, min_periods=10).median().shift(1)).values
    with np.errstate(invalid="ignore", divide="ignore"):
        P["vratio"] = vs.values / med
        P["taker_share"] = np.where(w > 0, tb / np.where(w > 0, w, 1.0), np.nan)
    # funding: rank of the newest rate known at each close among the last 90 settlements
    P["fund_rank"] = np.full(n, np.nan)
    if asset in CFG["crypto"]:
        f = funding if funding is not None else data.load_funding(asset)
        if len(f):
            rk = f.rolling(FUND_LOOKBACK, min_periods=30).rank(pct=True)
            fms = data.to_ms(f.index)
            k = np.searchsorted(fms, ms + BAR_MS, side="right") - 1
            ok = k >= 0
            P["fund_rank"][ok] = rk.values[k[ok]]
    # London open (08:00-10:00 London) and New York open (09:30-11:30 New York), local clocks
    lon = df.index.tz_convert("Europe/London")
    nyc = df.index.tz_convert("America/New_York")
    lm, nm = lon.hour * 60 + lon.minute, nyc.hour * 60 + nyc.minute
    P["open_window"] = np.asarray(((lm >= 480) & (lm < 600)) | ((nm >= 570) & (nm < 690)))
    return P


def htf_bias(P):
    """The engine's v5 bias (evidence.py), on these bars: +1 when the 1h, 4h and 1d trend scores are all
    >= +0.5 and the close is above the 1h EMA50 and the 4h EMA20 / EMA50; -1 the mirror; else 0."""
    if "bias" in P:
        return P["bias"]
    df = P["df"]
    h1, h4, d1 = data.resample(df, "1h"), data.resample(df, "4h"), data.resample(df, "1D")
    t1 = data.htf_on_15(df, "1h", ind.trend_score(h1["close"])).values
    t4 = data.htf_on_15(df, "4h", ind.trend_score(h4["close"])).values
    td = data.htf_on_15(df, "1D", ind.trend_score(d1["close"])).values
    e50_1h = data.htf_on_15(df, "1h", h1["close"].ewm(span=50, adjust=False, min_periods=50).mean()).values
    e20_4h = data.htf_on_15(df, "4h", h4["close"].ewm(span=20, adjust=False, min_periods=20).mean()).values
    e50_4h = data.htf_on_15(df, "4h", h4["close"].ewm(span=50, adjust=False, min_periods=50).mean()).values
    c = P["c"]
    with np.errstate(invalid="ignore"):
        up = (t1 >= 0.5) & (t4 >= 0.5) & (td >= 0.5) & (c > e50_1h) & (c > e20_4h) & (c > e50_4h)
        dn = (t1 <= -0.5) & (t4 <= -0.5) & (td <= -0.5) & (c < e50_1h) & (c < e20_4h) & (c < e50_4h)
    P["bias"] = np.where(up, 1, np.where(dn, -1, 0))
    return P["bias"]


# ---------------------------------------------------------------- P1: liquidation hunt
def p1_signals(P, rule):
    """-> list of signals (dicts), one per decision bar, oldest first."""
    k, m = float(rule["k"]), int(rule["m"])
    n, o, h, l, c = P["n"], P["o"], P["h"], P["l"], P["c"]
    pools = {-1: [P["sw_hi"], P["hi24"], P["hi7d"], P["pdh"], P["rup"]],
             +1: [P["sw_lo"], P["lo24"], P["lo7d"], P["pdl"], P["rdn"]]}
    found = {}
    with np.errstate(invalid="ignore"):
        for side in (-1, 1):
            lev, pidx, dd = np.full(n, np.nan), np.full(n, -1), np.full(n, -1)
            for d in range(m + 1):
                H = np.fmax.reduce([_sh(h, e) for e in range(d + 1)]) if d else h
                L = np.fmin.reduce([_sh(l, e) for e in range(d + 1)]) if d else l
                o_s, cprev_s, atr_s = _sh(o, d), _sh(P["c_prev"], d), _sh(P["atr_prev"], d)
                rng = H - L
                if side < 0:
                    wick = (rng > 0) & (H - np.fmax(o_s, c) >= WICK_MIN * rng)
                else:
                    wick = (rng > 0) & (np.fmin(o_s, c) - L >= WICK_MIN * rng)
                for pi, arr in enumerate(pools[side]):
                    Ps = _sh(arr, d)
                    if side < 0:
                        cond = (Ps > cprev_s) & (_sh(h, d) > Ps) & (H >= Ps + k * atr_s) & (c < Ps)
                        for e in range(1, d + 1):
                            cond &= _sh(c, e) >= Ps
                        better = cond & wick & ~(lev >= Ps)            # the highest pool swept wins
                    else:
                        cond = (Ps < cprev_s) & (_sh(l, d) < Ps) & (L <= Ps - k * atr_s) & (c > Ps)
                        for e in range(1, d + 1):
                            cond &= _sh(c, e) <= Ps
                        better = cond & wick & ~(lev <= Ps)
                    lev[better], pidx[better], dd[better] = Ps[better], pi, d
            found[side] = (lev, pidx, dd)
    sigs = []
    for side in (-1, 1):
        lev, pidx, dd = found[side]
        other = found[-side][1] >= 0
        for r in np.where((pidx >= 0) & ~other)[0]:
            d = int(dd[r])
            s = r - d
            H, L = float(h[s:r + 1].max()), float(l[s:r + 1].min())
            rng = H - L
            wick = (H - max(o[s], c[r])) if side < 0 else (min(o[s], c[r]) - L)
            vr = P["vratio"][s:r + 1]
            vr = float(np.nanmax(vr)) if np.isfinite(vr).any() else float("nan")
            sig = {"book": "p1_liqhunt", "i_dec": int(r), "i_start": int(s), "side": side, "pool": (P1_POOLS_HI if side < 0 else P1_POOLS_LO)[pidx[r]],
                   "level": float(lev[r]), "extreme": H if side < 0 else L, "wick_pct": 100.0 * wick / rng,
                   "vratio": vr, "taker_share": float(P["taker_share"][r]), "fund_rank": float(P["fund_rank"][r]),
                   "stop": (H + STOP_PAD_ATR * P["atr"][r]) if side < 0 else (L - STOP_PAD_ATR * P["atr"][r]),
                   "t1_cands": [("VWAP", float(P["vwap"][r])), ("24h mid", float((P["hi24_now"][r] + P["lo24_now"][r]) / 2.0))],
                   "t2_cand": ("24h low", float(P["lo24_now"][r])) if side < 0 else ("24h high", float(P["hi24_now"][r]))}
            if _p1_confirmed(sig, rule.get("confirm"), P["asset"]):
                sigs.append(sig)
    sigs.sort(key=lambda x: x["i_dec"])
    return sigs


def _p1_confirmed(sig, confirm, asset):
    if not confirm:
        return True
    side = sig["side"]
    if confirm == "volume":
        return sig["vratio"] >= VOL_SURGE
    if asset not in CFG["crypto"]:                                     # crypto-only confirmations do not apply elsewhere
        return True
    if confirm == "taker":                                            # the reclaim bar's takers lean against the sweep
        return (sig["taker_share"] < 0.5) if side < 0 else (sig["taker_share"] > 0.5)
    if confirm == "funding":                                          # the crowd on the swept side pays to be there
        return (sig["fund_rank"] >= FUND_EXTREME) if side < 0 else (sig["fund_rank"] <= 1.0 - FUND_EXTREME)
    raise ValueError(confirm)


# ---------------------------------------------------------------- P2: breakout trap
def p2_signals(P, rule):
    j, level = int(rule["j"]), rule["level"]
    up_lv, dn_lv = {"n48": (P["n48_hi"], P["n48_lo"]), "pday": (P["pdh"], P["pdl"]),
                    "swing": (P["sw_hi"], P["sw_lo"])}[level]
    n, h, l, c = P["n"], P["h"], P["l"], P["c"]
    sigs = []
    with np.errstate(invalid="ignore"):
        for side in (-1, 1):                                          # -1: a failed UPSIDE breakout -> short
            lvl, opp = (up_lv, dn_lv) if side < 0 else (dn_lv, up_lv)
            for e in range(1, j + 1):
                Lb, Ob = _sh(lvl, e), _sh(opp, e)
                cb, cpb = _sh(c, e), _sh(P["c_prev"], e)
                if side < 0:
                    cond = (cb > Lb) & (cpb <= Lb) & (c < Lb) & (Lb > Ob)
                    for f in range(1, e):
                        cond &= _sh(c, f) >= Lb
                else:
                    cond = (cb < Lb) & (cpb >= Lb) & (c > Lb) & (Lb < Ob)
                    for f in range(1, e):
                        cond &= _sh(c, f) <= Lb
                for r in np.where(cond)[0]:
                    b = r - e
                    H, L = float(h[b:r + 1].max()), float(l[b:r + 1].min())
                    ext = H if side < 0 else L
                    lv, op = float(Lb[r]), float(Ob[r])
                    names = P2_LEVELS[level]
                    sig = {"book": "p2_trap", "i_dec": int(r), "i_start": int(b), "side": side, "pool": names[0] if side < 0 else names[1],
                           "level": lv, "opposite": op, "extreme": ext, "break_close": float(c[b]),
                           "vratio": float(P["vratio"][b]), "open_window": bool(P["open_window"][b]),
                           "beyond_atr": abs(ext - lv) / P["atr_prev"][b] if P["atr_prev"][b] > 0 else float("nan"),
                           "stop": (H + STOP_PAD_ATR * P["atr"][r]) if side < 0 else (L - STOP_PAD_ATR * P["atr"][r]),
                           "t1_cands": [("range mid", (lv + op) / 2.0)],
                           "t2_cand": (names[1] if side < 0 else names[0], op)}
                    if rule.get("filter") in ("with_bias", "against_bias"):
                        sig["bias"] = int(htf_bias(P)[r])
                    if _p2_passes(sig, rule.get("filter"), P):
                        sigs.append(sig)
    sigs.sort(key=lambda x: (x["i_dec"], -x["i_start"]))                       # one signal a bar: the latest breakout
    out, seen = [], set()
    for s in sigs:
        if s["i_dec"] not in seen:
            seen.add(s["i_dec"])
            out.append(s)
    return out


def _p2_passes(sig, filt, P):
    if not filt:
        return True
    if filt == "vol_low":
        return sig["vratio"] < VOL_LOW
    if filt == "vol_high":
        return sig["vratio"] >= VOL_HIGH
    if filt in ("with_bias", "against_bias"):
        b = int(htf_bias(P)[sig["i_dec"]])
        return b == sig["side"] if filt == "with_bias" else b == -sig["side"]
    if filt == "open_window":
        return sig["open_window"]
    if filt == "shallow":
        return sig["beyond_atr"] <= SHALLOW_ATR
    raise ValueError(filt)


def signals(book, P, rule):
    return p1_signals(P, rule) if book == "p1_liqhunt" else p2_signals(P, rule)


# ---------------------------------------------------------------- the paper trade
def _targets(sig, entry, risk, scheme):
    side = sig["side"]
    if scheme == "fixed":
        return ("1R", entry + side * risk), ("2R", entry + side * 2.0 * risk)
    t1 = ("1R", entry + side * risk)
    for name, px in sig["t1_cands"]:
        if px == px and side * (px - entry) >= STRUCT_MIN_R * risk:
            t1 = (name, px)
            break
    name, px = sig["t2_cand"]
    t2 = (name, px) if (px == px and side * (px - t1[1]) >= STRUCT_MIN_R * risk) else ("T1 + 1R", t1[1] + side * risk)
    return t1, t2


def simulate(P, sigs, scheme, hold, fee):
    """Trade the signals one at a time. -> list of trade dicts (status WAITING / OPEN / CLOSED)."""
    n, o, h, l, c, ms = P["n"], P["o"], P["h"], P["l"], P["c"], P["ms"]
    trades, busy = [], -1
    for sig in sigs:
        r = sig["i_dec"]
        if r <= busy:
            continue
        side, stop = sig["side"], float(sig["stop"])
        t = dict(sig, setup_ms=int(ms[r]) + BAR_MS)
        t.pop("t1_cands", None)
        t.pop("t2_cand", None)
        e = r + 1
        if e >= n:                                                    # entry is at the next open
            est = float(c[r])
            (n1, t1), (n2, t2) = _targets(sig, est, abs(est - stop), scheme)
            t.update(status="WAITING", entry=None, est_entry=est, t1_name=n1, target_1=t1, t2_name=n2, target_2=t2)
            trades.append(t)
            busy = n
            continue
        entry = float(o[e])
        if side * (entry - stop) <= 0:                                # the open gapped beyond the stop: no trade
            continue
        risk = abs(entry - stop)
        (n1, t1), (n2, t2) = _targets(sig, entry, risk, scheme)
        legs, cur_stop, t1_done, j_out, why = [], stop, False, None, None
        last = min(e + hold, n)
        for j in range(e, last):
            adverse = l[j] if side > 0 else h[j]
            fav = h[j] if side > 0 else l[j]
            rem = 0.5 if t1_done else 1.0
            if side * (o[j] - cur_stop) <= 0:
                legs.append((rem, float(o[j])))
                j_out, why = j, "STOP"
                break
            if side * (adverse - cur_stop) <= 0:                      # stop first when both are in one bar
                legs.append((rem, cur_stop))
                j_out, why = j, "STOP"
                break
            hit1 = False
            if not t1_done and side * (fav - t1) >= 0:
                legs.append((0.5, float(o[j]) if side * (o[j] - t1) >= 0 else t1))
                t1_done, hit1 = True, True
            if t1_done and side * (fav - t2) >= 0:
                legs.append((0.5, float(o[j]) if side * (o[j] - t2) >= 0 else t2))
                j_out, why = j, "T2"
                break
            if hit1:
                cur_stop = entry                                      # break-even from the next bar
        t.update(entry_ms=int(ms[e]), entry=entry, stop=stop, risk=risk, t1_name=n1, target_1=t1, t2_name=n2,
                 target_2=t2, t1_hit=t1_done)
        if why is None and e + hold < n:
            rem = 0.5 if t1_done else 1.0
            legs.append((rem, float(o[e + hold])))
            j_out, why = e + hold, "TIME"
        if why is None:                                               # still open: marked at the last close
            rem = 0.5 if t1_done else 1.0
            mark = legs + [(rem, float(c[-1]))]
            t.update(status="OPEN", mark=float(c[-1]), why_out="OPEN", exit=None, exit_ms=None,
                     **_money(mark, entry, risk, side, fee))
            busy = n
        else:
            frac = sum(f for f, _ in legs)
            px = sum(f * p for f, p in legs) / frac
            # exit_ms: the open of the exit bar (a time exit fills at that open; a stop or target inside it)
            t.update(status="CLOSED", exit=px, exit_ms=int(ms[j_out]), why_out=why,
                     exit_bar=int(j_out), **_money(legs, entry, risk, side, fee))
            busy = j_out - 1                                          # flat by the close of the exit bar
        trades.append(t)
    return trades


def _money(legs, entry, risk, side, fee):
    gross = sum(f * side * (p - entry) / entry for f, p in legs) * STAKE
    fees = fee * STAKE + sum(f * fee * STAKE * p / entry for f, p in legs)
    net = gross - fees
    return {"gross_usd": gross, "fees_usd": fees, "pnl_usd": net, "pnl_pct": net / STAKE * 100.0,
            "r": net / (STAKE * risk / entry)}


def run(book, P, rule=None, fee=None):
    rule = rule or RULES[book]
    return simulate(P, signals(book, P, rule), rule["exit"], HOLD[book], fee_side(P["asset"]) if fee is None else fee)


# ---------------------------------------------------------------- words
def _px(v):
    if v is None or v != v:
        return "n/a"
    a = abs(v)
    return "{:,.0f}".format(v) if a >= 10000 else "{:,.1f}".format(v) if a >= 1000 else "{:,.2f}".format(v) if a >= 100 else "{:,.3f}".format(v)


def _hm(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%H:%M")


def sentence(t, P):
    a = SHORT_NAME.get(P["asset"], P["asset"])
    side, ms = t["side"], P["ms"]
    word = "SHORT" if side < 0 else "LONG"
    s, r = t["i_start"], t["i_dec"]
    bars = ("%s bar" % _hm(ms[r])) if s == r else ("%s-%s bars" % (_hm(ms[s]), _hm(ms[r])))
    entry = t["entry"] if t.get("entry") is not None else t.get("est_entry")
    tn = lambda nm: ("(%s)" % nm) if "R" in nm and nm[0] in "12T" else nm   # noqa: E731  "T1 (1R) 4,038" / "T1 VWAP 73,900"
    plan = "%s %s%s, stop %s, T1 %s %s, T2 %s %s" % (
        word, "" if t.get("entry") is not None else "at the next open (about) ", _px(entry), _px(t["stop"]),
        tn(t["t1_name"]), _px(t["target_1"]), tn(t["t2_name"]), _px(t["target_2"]))
    if t["book"] == "p1_liqhunt":
        vol = ("" if t["vratio"] != t["vratio"] else " and %.1fx volume" % t["vratio"])
        if t.get("fund_rank") == t.get("fund_rank") and t.get("fund_rank") is not None:
            vol += ", funding at the %.0fth percentile of its last 30 days" % (100 * t["fund_rank"])
        head = "Liquidation hunt, %s: %s %s to %s %s the %s %s and closed back at %s with a %.0f%% %s wick%s" % (
            a, bars, "spiked" if side < 0 else "dropped", _px(t["extreme"]), "above" if side < 0 else "below",
            t["pool"], _px(t["level"]), _px(P["c"][r]), t["wick_pct"], "upper" if side < 0 else "lower", vol)
    else:
        b = t["i_start"]
        head = "Breakout trap, %s: the %s bar closed at %s %s the %s %s (breakout %s in), and the %s bar closed back inside at %s" % (
            a, _hm(ms[b]), _px(t["break_close"]), "above" if side < 0 else "below", t["pool"], _px(t["level"]),
            "buyers" if side < 0 else "sellers", _hm(ms[r]), _px(P["c"][r]))
        if t.get("bias") is not None:
            head += ", the higher-timeframe bias %s" % {1: "LONG", -1: "SHORT", 0: "NONE"}[t["bias"]]
    out = "%s: %s." % (head, plan)
    if t["status"] == "CLOSED":
        how = {"STOP": "stopped" + (" at break-even after T1" if t.get("t1_hit") else ""), "T2": "T2 reached",
               "TIME": "closed at the time limit" + (" after T1" if t.get("t1_hit") else "")}[t["why_out"]]
        out += " Result: %s, average exit %s, %+.2fR, %+.2f USD after %.2f USD fees." % (how, _px(t["exit"]), t["r"], t["pnl_usd"], t["fees_usd"])
    elif t["status"] == "OPEN":
        out += " Open%s, marked %s: %+.2fR." % (" (T1 taken, stop at entry)" if t.get("t1_hit") else "", _px(t["mark"]), t["r"])
    else:
        out += " Waiting for the next open."
    return out


# ---------------------------------------------------------------- live interface
def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _row(book, asset, t, P):
    rnd = lambda v, k=6: None if v is None or v != v else round(float(v), k)   # noqa: E731
    return {"book": book, "asset": asset, "status": t["status"], "side": int(t["side"]),
            "setup_utc": _utc(t["setup_ms"]), "entry_utc": _utc(t.get("entry_ms")), "entry": rnd(t.get("entry")),
            "stop": rnd(t["stop"]), "target_1": rnd(t["target_1"]), "target_2": rnd(t["target_2"]),
            "t1_name": t["t1_name"], "t2_name": t["t2_name"], "exit_utc": _utc(t.get("exit_ms")), "exit": rnd(t.get("exit")),
            "why_out": t.get("why_out", "OPEN"), "t1_hit": bool(t.get("t1_hit", False)),
            "r": rnd(t.get("r"), 3), "pnl_usd": rnd(t.get("pnl_usd"), 2), "fees_usd": rnd(t.get("fees_usd"), 2),
            "pool": t["pool"], "level": rnd(t["level"]), "text": sentence(t, P)}


def step(bars=None, now_ms=None):
    """bars: {asset: 15m frame}; None loads every asset from disk. -> rows (docs/PLAYBOOK_INTERFACE.md)."""
    reg = pd.Timestamp(REGISTERED, tz="UTC")
    reg_ms = int(reg.value // 10**6)
    anchor = reg - pd.Timedelta(days=WARMUP_DAYS)
    rows = []
    for asset in ASSETS:
        if bars is None:
            try:
                df = data.load(asset)
            except Exception:
                continue
        else:
            df = bars.get(asset)
            if df is None:
                continue
        df = df[df.index >= anchor]
        if now_ms is not None:
            df = df[data.to_ms(df.index) + BAR_MS <= int(now_ms)]
        if len(df) < 200:
            continue
        P = prepare(df, asset)
        for book, facts in BOOKS.items():
            if asset not in facts["assets"]:
                continue
            rule = RULES[book]
            sigs = [s for s in signals(book, P, rule) if int(P["ms"][s["i_dec"]]) + BAR_MS > reg_ms]
            ret = RETIRED.get(book)
            ret_ms = int(pd.Timestamp(ret, tz="UTC").value // 10**6) if ret else None
            for t in simulate(P, sigs, rule["exit"], HOLD[book], fee_side(asset)):
                fill_ms = t.get("entry_ms")
                if fill_ms is None:                                   # WAITING: it cannot fill before the next bar opens,
                    now_eff = int(now_ms) if now_ms is not None else int(time.time() * 1000)   # nor before now
                    fill_ms = max(int(P["ms"][-1]) + BAR_MS, now_eff)
                if ret_ms is not None and int(fill_ms) >= ret_ms:
                    continue                                          # retired: nothing entered from the stamp on
                rows.append(_row(book, asset, t, P))
    return rows


def _totals(closed):
    n = len(closed)
    if not n:
        return {"trades": 0, "won": 0, "win_rate_pct": None, "avg_r": None, "net_usd": 0.0, "fees_usd": 0.0}
    won = sum(1 for r in closed if r["pnl_usd"] > 0)
    return {"trades": n, "won": won, "win_rate_pct": round(100.0 * won / n, 1),
            "avg_r": round(sum(r["r"] for r in closed) / n, 3), "net_usd": round(sum(r["pnl_usd"] for r in closed), 2),
            "fees_usd": round(sum(r["fees_usd"] for r in closed), 2)}


def rule_text(book):
    r = RULES[book]
    if book == "p1_liqhunt":
        return ("Fade a sweep of a liquidity pool (15m swing, 24h, 7-day or prior-day high/low, round number) by >= %.2f x ATR(15m) "
                "that closes back inside %s with a >= 50%% wick; stop beyond the extreme + 0.1 ATR; %s; hold %d bars%s." % (
                    r["k"], "on the same bar" if r["m"] == 0 else "within %d bars" % r["m"],
                    "half at T1 (VWAP or 24h mid), rest at T2 (far side of the 24h range), stop to entry after T1" if r["exit"] == "struct"
                    else "half at 1R, rest at 2R, stop to entry after 1R", HOLD[book],
                    "" if not r["confirm"] else "; confirmation: " + r["confirm"]))
    lv = {"n48": "the 48-bar (12h) high/low", "pday": "the prior UTC day's high/low", "swing": "the last confirmed 15m swing"}[r["level"]]
    return ("Trade a failed breakout: a first close beyond %s, then a close back inside within %d bars; stop beyond the breakout "
            "extreme + 0.1 ATR; %s; hold %d bars%s." % (
                lv, r["j"], "half at the range mid, rest at the opposite edge, stop to entry after T1" if r["exit"] == "struct"
                else "half at 1R, rest at 2R, stop to entry after 1R", HOLD[book], "" if not r["filter"] else "; filter: " + r["filter"]))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r[k]) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1", "target_2", "r", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"],
                     "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r[k]) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit", "why_out", "r", "pnl_usd", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per,
                     "note": ("Paper only. Registered rule graded forward from %s; history does not prove it." % facts["registered"])
                     if book not in RETIRED else
                     ("Retired %s UTC (owner): the post-mortem and a test of 8 improved versions (H41) found no edge before "
                      "costs on 2020-2025 history. No new trades; the live record is kept." % RETIRED[book])}
        if book in RETIRED:
            out[book]["retired"] = RETIRED[book]
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"])
