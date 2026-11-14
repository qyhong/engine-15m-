# -*- coding: utf-8 -*-
"""levels -- support and resistance: where they are, how strong, and what price just did there.

One row per closed 15-minute bar. Row i uses ONLY what is known at the close of bar i
(tests/test_levels.py::test_no_lookahead cuts the future off and checks no row changes).
The research behind every choice is in docs/SUPPORT_RESISTANCE.md.

What counts as a level:
  pivot zone      confirmed swing highs/lows (a bar that is the extreme of k bars on EACH
                  side, so it is only known k bars later) clustered into zones half an
                  hourly ATR wide. Four swing sizes stand for the 15m / 1h / 4h / 1D charts.
  prior-day       high, low and close of the last CLOSED UTC day
  prior-week      high and low of the last CLOSED UTC week (Monday to Monday)
  round number    the price grid traders quote (1 / 2.5 / 5 x 10^n, about 1-2% of price apart)

Support is the nearest meaningful level below the close, resistance the nearest at or above
it -- so a support that price closes through becomes resistance by itself (role reversal).
Levels that sit within one zone-width of each other are read as one (confluence).
"""
import math
from bisect import bisect_left, bisect_right

import numpy as np
import pandas as pd

from . import indicators as ind
from .config import CFG
from .data import htf_on_15

# =====================================================================================
# THE ONE CONSTANT BLOCK. Conventional values, declared once. None was tuned against a
# return or a hit rate; docs/SUPPORT_RESISTANCE.md section 4 names the two that were changed
# during the build (after counting how often things appeared, never what price did next).
# =====================================================================================
SWING_K = (10, 20, 48, 192)       # bars each side of a swing = its DELAY: 2.5h, 5h, 12h, 2 days -- the windows of
#                                   a 10/10 pivot on 15m, a 5-bar one on 1h, a 3-bar one on 4h, a 2-bar fractal on 1D
DEGREE_WEIGHT = (0.25, 0.50, 0.75, 1.00)   # a swing of a higher timeframe matters more (linear ladder)
HALFLIFE_PER_K = 20               # a zone's strength halves every 20 x k bars untouched: 2, 4, 10, 40 days
ZONE_HALF_ATR = 0.25              # a zone is its centre +/- 0.25 hourly ATR (half an ATR wide); also "touched"
BREAK_ATR = 0.25                  # a BREAK is a CLOSE beyond the far edge of the zone, not a wick
TOUCH_SEP_BARS = 16               # swings less than 4 hours apart count as ONE touch of a zone
TOUCH_FULL = 4                    # four touches = a fully proven zone; more adds nothing
REACT_FULL_ATR = 3.0              # a swing price left by 3 hourly ATRs within its k bars = full rejection score
VOL_WINDOW = 96                   # a swing bar's volume is compared with the prior 24 hours' average ...
VOL_FULL = 3.0                    # ... and three times that average = full volume score (average = none)
W_TOUCH, W_DEGREE, W_REACT, W_VOLUME = 0.40, 0.30, 0.20, 0.10   # strength mix: touches first, volume last
BREAK_KEEP = 0.8                  # a zone keeps 80% of its strength each time price closes through it ...
MAX_BREAKS = 3                    # ... and is dropped at the third: price chops through it, it is not a level
MAX_ZONES = 64                    # live pivot zones kept (weakest dropped first): bounds memory and time
S_PD_HILO = 0.50                  # strength of the prior-day high / low
S_PD_CLOSE = 0.30                 # ... of the prior-day close (the "daily open" of a 24h market)
S_PW_HILO = 0.70                  # ... of the prior-week high / low (higher timeframe, watched by more)
ROUND_STEP_PCT = 0.02             # round grid: the largest 1 / 2.5 / 5 x 10^n step not above 2% of price
S_ROUND = (0.20, 0.40, 0.60)      # a grid number (adds to a level, is not one alone); the next coarser grid; the one above
MIN_STRENGTH = 0.30               # the least strength a level (or confluence) needs to be read as S/R
STRONG = 0.60                     # "strong": the journal's word, its bar for naming an event, and the statistic's
SEARCH_ATR = 10.0                 # levels further than 10 hourly ATRs away are not read at all
DIST_CLIP_ATR = 4.0               # features treat 4 hourly ATRs away (or no level) as "far" (the barrier is 1.5)
NEAR_ATR = 1.5                    # "near" a NAMED level (prior-day high/low, round number): within the engine's barrier
REJ_LOOKBACK = 3                  # a rejection: the level was touched within the last 3 bars and price closed back
REJECT_FULL_ATR = 0.5             # ... having recovered 0.5 hourly ATR from the wick = full size
EVENT_HALFLIFE = 4                # break / rejection features fade with a 1-hour half-life
# =====================================================================================

KINDS = ("pivot zone", "flipped zone", "prior-day high", "prior-day low", "prior-day close",
         "prior-week high", "prior-week low", "round number")
K_PIVOT, K_FLIP, K_PDH, K_PDL, K_PDC, K_PWH, K_PWL, K_ROUND = range(8)

FEATURES = ["sr_sup_near", "sr_res_near", "sr_sup_str", "sr_res_str", "sr_room", "sr_lean",
            "sr_break", "sr_reject", "sr_pdh_near", "sr_pdl_near", "sr_pd_pos", "sr_round_near"]
READS = ["sup_px", "sup_str", "sup_kind", "sup_touches", "sup_dist_atr",
         "res_px", "res_str", "res_kind", "res_touches", "res_dist_atr",
         "pd_high", "pd_low", "pd_close", "pw_high", "pw_low", "round_px", "sr_event"]

# a level in the live list: [price, side, kind, base strength, last touch row, decay per bar,
#                            touches, breaks, degree, reaction, volume, pivots, last swing row, role since]
PX, SIDE, KIND, BASE, LAST, DECAY, TOUCH, BRK, DEG, REACT, VOL, NPIV, FORMED, SINCE = range(14)
_LN2 = math.log(2.0)
_ROUND_TIERS = {1.0: (5, 10), 2.5: (2, 4), 5.0: (2, 10)}    # grid step -> the two coarser grids (in steps)


# ------------------------------------------------------------------ vectorised, causal inputs
def _bars(df15, rule):
    """15m bars -> higher-timeframe high / low / close keyed by OPEN time (data.resample's
    convention; kept here so this module needs only the open/high/low/close/volume columns).
    Read only through data.htf_on_15, which hands over a higher bar once it has CLOSED."""
    agg = df15.resample(rule, label="left", closed="left").agg({"high": "max", "low": "min", "close": "last"})
    return agg.dropna(subset=["close"])


def _swing_events(high, low, atr_ok):
    """Every confirmed swing as an event at the row where it becomes KNOWN (swing row + k).
    A swing high: high >= the k highs before it and > the k highs after it (one per plateau).
    -> lists (event_row, swing_row, is_high, degree, reaction in price), sorted by event row."""
    n = len(high)
    rows, src, hi_flag, deg, react = [], [], [], [], []
    h, l = pd.Series(high), pd.Series(low)
    hr, lr = pd.Series(high[::-1]), pd.Series(low[::-1])
    for d, k in enumerate(SWING_K):
        if n < 2 * k + 1:
            continue
        left_max = h.shift(1).rolling(k).max().values
        left_min = l.shift(1).rolling(k).min().values
        right_max = hr.shift(1).rolling(k).max().values[::-1]     # the k bars AFTER the swing:
        right_min = lr.shift(1).rolling(k).min().values[::-1]     # known only k bars later
        with np.errstate(invalid="ignore"):
            is_hi = (high >= left_max) & (high > right_max)
            is_lo = (low <= left_min) & (low < right_min)
        for flag, mask, size in ((1, is_hi, high - right_min), (0, is_lo, right_max - low)):
            j = np.flatnonzero(mask)
            rows.append(j + k)
            src.append(j)
            hi_flag.append(np.full(len(j), flag))
            deg.append(np.full(len(j), d))
            react.append(size[j])
    if not rows:
        return [], [], [], [], []
    rows, src, hi_flag, deg, react = (np.concatenate(x) for x in (rows, src, hi_flag, deg, react))
    keep = atr_ok[rows]                                           # no yardstick yet = no level
    rows, src, hi_flag, deg, react = rows[keep], src[keep], hi_flag[keep], deg[keep], react[keep]
    order = np.lexsort((src, deg, rows))
    return (rows[order].tolist(), src[order].tolist(), hi_flag[order].tolist(),
            deg[order].tolist(), react[order].tolist())


def _prior_week(df15):
    """High / low of the last CLOSED UTC week (Monday 00:00 to Monday 00:00) on the 15m index."""
    w = df15.resample("W-MON", label="left", closed="left").agg({"high": "max", "low": "min"}).dropna()
    w.index = w.index + pd.Timedelta(days=7)                      # a week is known when it has closed
    out = w.reindex(df15.index + pd.Timedelta(milliseconds=CFG["bar_ms"]), method="ffill")
    return out["high"].values, out["low"].values


def _round_grid(close):
    """-> (step, index of the grid number at or below the close). The step is the largest
    1 / 2.5 / 5 x 10^n not above ROUND_STEP_PCT of the price."""
    with np.errstate(invalid="ignore", divide="ignore"):
        target = ROUND_STEP_PCT * close
        expo = np.floor(np.log10(target))
        mant = target / 10.0 ** expo
        lm = np.where(mant >= 5.0, 5.0, np.where(mant >= 2.5, 2.5, 1.0))
        step = lm * 10.0 ** expo
        idx = np.floor(close / step + 1e-9)
    ok = np.isfinite(step) & (step > 0) & np.isfinite(idx)
    return np.where(ok, step, 0.0), np.where(ok, idx, 0).astype(np.int64), np.where(ok, lm, 1.0)


def _changed(*cols):
    """True at rows where any of the (forward-filled) columns shows a new finite value."""
    out = np.zeros(len(cols[0]), dtype=bool)
    for c in cols:
        prev = np.concatenate([[np.nan], c[:-1]])
        out |= np.isfinite(c) & ~(c == prev)
    return out


# ------------------------------------------------------------------ the live level list
def _zone_base(e):
    return ((W_TOUCH * min(e[TOUCH], TOUCH_FULL) / TOUCH_FULL + W_DEGREE * DEGREE_WEIGHT[e[DEG]]
             + W_REACT * e[REACT] + W_VOLUME * e[VOL]) * BREAK_KEEP ** e[BRK])


def _insert(P, E, e):
    j = bisect_left(P, e[PX])
    P.insert(j, e[PX])
    E.insert(j, e)


def _remove(P, E, e):
    j = bisect_left(P, e[PX])
    while E[j] is not e:
        j += 1
    del P[j]
    del E[j]


def _fixed(price, kind, strength, c, i):
    return [price, 1 if price < c else -1, kind, strength, i, 0.0, 0, 0, 0, 0.0, 0.0, 0, i, i]


def _fmt(px):
    if px != px:
        return "n/a"
    return "{:,.0f}".format(px) if abs(px) >= 1000 else "{:,.2f}".format(px) if abs(px) >= 1 else "{:.5f}".format(px)


def _kind_names(codes):
    """code = strongest kind + 8 x (bit mask of every kind in the confluence) -> text such as
    "prior-day high + pivot zone" (strongest first); -1 -> "" (no level)."""
    names = {-1: ""}
    for code in np.unique(codes):
        if code >= 0:
            top, mask = int(code) % 8, int(code) // 8
            names[int(code)] = " + ".join([KINDS[top]] + [KINDS[k] for k in range(8) if k != top and mask >> k & 1])
    return np.array([names[c] for c in codes.tolist()], dtype=object)


def build(df15, _check=False):
    """Index = df15.index. One row per closed 15m bar; row i uses only data known at the
    close of bar i. Columns: FEATURES (dimensionless, NaN-free, 0.0 = no read) and READS
    (prices, strengths and kinds for the journal). _check=True verifies the list's
    bookkeeping by brute force on every bar (tests only; slow)."""
    n = len(df15)
    high = df15["high"].values.astype(float)
    low = df15["low"].values.astype(float)
    close = df15["close"].values.astype(float)
    volume = df15["volume"].values.astype(float)

    atr = htf_on_15(df15, "1h", ind.atr_wilder(_bars(df15, "1h"))).values.astype(float)
    atr_ok = np.isfinite(atr) & (atr > 0) & np.isfinite(close)
    pday = htf_on_15(df15, "1D", _bars(df15, "1D"))               # the last CLOSED UTC day
    pdh, pdl, pdc = (pday[c].values.astype(float) for c in ("high", "low", "close"))
    pwh, pwl = _prior_week(df15)
    day_new, week_new = _changed(pdh, pdl, pdc), _changed(pwh, pwl)
    with np.errstate(invalid="ignore", divide="ignore"):
        vol_score = np.clip((volume / pd.Series(volume).rolling(VOL_WINDOW).mean().values - 1.0)
                            / (VOL_FULL - 1.0), 0.0, 1.0)
    vol_score = np.where(np.isfinite(vol_score), vol_score, 0.0).tolist()
    low_n = pd.Series(low).rolling(REJ_LOOKBACK, min_periods=1).min().values.tolist()
    high_n = pd.Series(high).rolling(REJ_LOOKBACK, min_periods=1).max().values.tolist()
    r_step, r_idx, r_mant = _round_grid(close)
    step_l, idx_l, mant_l = r_step.tolist(), r_idx.tolist(), r_mant.tolist()
    day_l, week_l = day_new.tolist(), week_new.tolist()
    ev_row, ev_src, ev_hi, ev_deg, ev_react = _swing_events(high, low, atr_ok)
    n_ev = len(ev_row)

    nan = float("nan")
    o_sp, o_ss, o_sk, o_st = [nan] * n, [0.0] * n, [-1] * n, [0] * n
    o_rp, o_rs, o_rk, o_rt = [nan] * n, [0.0] * n, [-1] * n, [0] * n
    o_brk, o_rej, o_evt = [0.0] * n, [0.0] * n, [""] * n

    P, E = [], []                       # live levels: prices (sorted) and their records, in step
    fixed = {}                          # kind -> record of the prior-day / prior-week levels
    rounds = {}                         # grid index -> record of the round numbers around price
    r_step_now, r_idx_now = 0.0, None
    n_zones = 0
    ep = 0
    brk_f = rej_f = 0.0
    fade = 0.5 ** (1.0 / EVENT_HALFLIFE)
    prev_dn = prev_up = None
    c_l, h_l, l_l, a_l = close.tolist(), high.tolist(), low.tolist(), atr.tolist()
    ok_l = atr_ok.tolist()
    exp = math.exp

    for i in range(n):
        if not ok_l[i]:
            while ep < n_ev and ev_row[ep] <= i:
                ep += 1
            continue
        c, a = c_l[i], a_l[i]
        tol = ZONE_HALF_ATR * a

        # ---- 1. the prior day / week just closed: replace those levels
        if day_l[i]:
            for kind, px, s in ((K_PDH, pdh[i], S_PD_HILO), (K_PDL, pdl[i], S_PD_HILO), (K_PDC, pdc[i], S_PD_CLOSE)):
                if kind in fixed:
                    _remove(P, E, fixed.pop(kind))
                if px == px:
                    fixed[kind] = _fixed(float(px), kind, s, c, i)
                    _insert(P, E, fixed[kind])
        if week_l[i]:
            for kind, px in ((K_PWH, pwh[i]), (K_PWL, pwl[i])):
                if kind in fixed:
                    _remove(P, E, fixed.pop(kind))
                if px == px:
                    fixed[kind] = _fixed(float(px), kind, S_PW_HILO, c, i)
                    _insert(P, E, fixed[kind])

        # ---- 2. round numbers: two grid numbers below the close, two above
        step, ib = step_l[i], idx_l[i]
        if step > 0 and (step != r_step_now or ib != r_idx_now):
            if step != r_step_now:
                for e in rounds.values():
                    _remove(P, E, e)
                rounds = {}
                r_step_now = step
                m2, m3 = _ROUND_TIERS[mant_l[i]]
            r_idx_now = ib
            for g in [g for g in rounds if g < ib - 1 or g > ib + 2]:
                _remove(P, E, rounds.pop(g))
            for g in (ib - 1, ib, ib + 1, ib + 2):
                if g not in rounds and g > 0:
                    s = S_ROUND[2] if g % m3 == 0 else S_ROUND[1] if g % m2 == 0 else S_ROUND[0]
                    rounds[g] = _fixed(g * step, K_ROUND, s, c, i)
                    _insert(P, E, rounds[g])

        # ---- 3. swings confirmed at this close: join the nearest zone within reach, or start one
        while ep < n_ev and ev_row[ep] <= i:
            if ev_row[ep] < i:
                ep += 1
                continue
            j, d = ev_src[ep], ev_deg[ep]
            p = h_l[j] if ev_hi[ep] else l_l[j]
            react = min(ev_react[ep] / (REACT_FULL_ATR * a), 1.0)
            ep += 1
            best, best_d = None, tol
            q = bisect_left(P, p)
            t = q - 1
            while t >= 0 and p - P[t] <= tol:
                if E[t][KIND] == K_PIVOT and p - P[t] <= best_d:
                    best, best_d = E[t], p - P[t]
                    break
                t -= 1
            t = q
            while t < len(P) and P[t] - p <= tol:
                if E[t][KIND] == K_PIVOT and P[t] - p < best_d:
                    best, best_d = E[t], P[t] - p
                    break
                t += 1
            if best is None:
                e = [p, 1 if p < c else -1, K_PIVOT, 0.0, i, _LN2 / (HALFLIFE_PER_K * SWING_K[d]),
                     1, 0, d, react, vol_score[j], 1, j, i]
                e[BASE] = _zone_base(e)
                _insert(P, E, e)
                n_zones += 1
                if n_zones > MAX_ZONES:                           # drop the weakest live zone
                    worst, worst_s = None, 2.0
                    for z in E:
                        if z[KIND] == K_PIVOT and z is not e:
                            s = z[BASE] * exp(-(i - z[LAST]) * z[DECAY])
                            if s < worst_s:
                                worst, worst_s = z, s
                    _remove(P, E, worst)
                    n_zones -= 1
                continue
            e = best
            if d == 0:                                            # a new swing (d > 0: a known swing grew a degree)
                _remove(P, E, e)
                e[PX] = (e[PX] * e[NPIV] + p) / (e[NPIV] + 1)     # the zone centre: mean of its swings
                e[NPIV] += 1
                _insert(P, E, e)
                if j - e[FORMED] >= TOUCH_SEP_BARS:
                    e[TOUCH] += 1
                if j > e[FORMED]:
                    e[FORMED] = j
                e[LAST] = i
            if d > e[DEG]:
                e[DEG] = d
                e[DECAY] = _LN2 / (HALFLIFE_PER_K * SWING_K[d])
            if react > e[REACT]:
                e[REACT] = react
            if vol_score[j] > e[VOL]:
                e[VOL] = vol_score[j]
            e[BASE] = _zone_base(e)

        # ---- 4. BREAKS: a close beyond the far edge of a level flips its role
        buf = BREAK_ATR * a
        dn, up = c - buf, c + buf
        if prev_dn is None:
            prev_dn, prev_up = dn, up
        keep_up = keep_dn = 1.0
        evt = ""
        evt_s = 0.0
        guard = min(prev_dn, dn) - tol            # below this every level is already support
        j = bisect_left(P, dn) - 1
        while j >= 0 and P[j] >= guard:
            e = E[j]
            if e[SIDE] < 0:                       # closed UP through a resistance
                s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY])
                keep_up *= 1.0 - s
                if s > evt_s:
                    evt_s, evt = s, "broke above %s (%s)" % (_fmt(e[PX]), KINDS[K_FLIP if e[BRK] else e[KIND]])
                e[SIDE], e[SINCE] = 1, i
                if e[KIND] == K_PIVOT:
                    e[BRK] += 1
                    if e[BRK] >= MAX_BREAKS:
                        del P[j]
                        del E[j]
                        n_zones -= 1
                    else:
                        e[BASE] = _zone_base(e)
            j -= 1
        guard = max(prev_up, up) + tol            # above this every level is already resistance
        j = bisect_right(P, up)
        while j < len(P) and P[j] <= guard:
            e = E[j]
            if e[SIDE] > 0:                       # closed DOWN through a support
                s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY])
                keep_dn *= 1.0 - s
                if s > evt_s:
                    evt_s, evt = s, "broke below %s (%s)" % (_fmt(e[PX]), KINDS[K_FLIP if e[BRK] else e[KIND]])
                e[SIDE], e[SINCE] = -1, i
                if e[KIND] == K_PIVOT:
                    e[BRK] += 1
                    if e[BRK] >= MAX_BREAKS:
                        del P[j]
                        del E[j]
                        n_zones -= 1
                        continue
                    e[BASE] = _zone_base(e)
            j += 1
        prev_dn, prev_up = dn, up
        if _check:
            for e in E:
                assert not (e[PX] < dn and e[SIDE] < 0) and not (e[PX] > up and e[SIDE] > 0), (i, e)
            assert P == [e[PX] for e in E] and P == sorted(P), i
            assert n_zones == sum(1 for e in E if e[KIND] == K_PIVOT) <= MAX_ZONES, i
        brk_f *= fade                             # the strongest recent event stands until it has faded
        new = keep_dn - keep_up                   # = (strength broken upward) - (strength broken downward)
        broke = new != 0.0 and abs(new) >= abs(brk_f)
        if broke:
            brk_f = new
        o_brk[i] = brk_f

        # ---- 5. REJECTIONS: touched (or wicked through) within the last bars, closed back
        old = i - REJ_LOOKBACK                    # the level must have held its role through the window
        r_up = r_dn = 0.0
        r_evt = ""
        lo3, hi3 = low_n[i], high_n[i]
        size = min((c - lo3) / (REJECT_FULL_ATR * a), 1.0)
        if size > 0:
            lim = lo3 - tol
            j = bisect_left(P, c) - 1
            while j >= 0 and P[j] >= lim:
                e = E[j]
                if e[SIDE] > 0 and e[SINCE] <= old:
                    s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY]) * size
                    if s > r_up:
                        r_up = s
                        r_evt = "bounced off %s (%s)" % (_fmt(e[PX]), KINDS[K_FLIP if e[BRK] else e[KIND]])
                j -= 1
        size = min((hi3 - c) / (REJECT_FULL_ATR * a), 1.0)
        if size > 0:
            lim = hi3 + tol
            j = bisect_right(P, c)
            while j < len(P) and P[j] <= lim:
                e = E[j]
                if e[SIDE] < 0 and e[SINCE] <= old:
                    s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY]) * size
                    if s > r_dn:
                        r_dn = s
                        if s > r_up:
                            r_evt = "rejected at %s (%s)" % (_fmt(e[PX]), KINDS[K_FLIP if e[BRK] else e[KIND]])
                j += 1
        rej_f *= fade
        new = r_up - r_dn
        turned = new != 0.0 and abs(new) >= abs(rej_f)
        if turned:
            rej_f = new
        o_rej[i] = rej_f
        if broke and evt_s >= STRONG:             # the journal names an event only when it is strong
            o_evt[i] = evt                        # and the strongest recent one (the features carry the rest)
        elif turned and max(r_up, r_dn) >= STRONG:
            o_evt[i] = r_evt

        # ---- 6. the READ: nearest meaningful support below the close, resistance at or above
        m = len(P)
        reach = SEARCH_ATR * a
        j = bisect_left(P, c) - 1
        while j >= 0 and c - P[j] <= reach:
            edge = P[j] - tol
            keep, top, top_e, touches, mask = 1.0, -1.0, None, 0, 0
            t = j
            while t >= 0 and P[t] >= edge:                        # everything within one zone-width: one level
                e = E[t]
                s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY])
                keep *= 1.0 - s
                touches += e[TOUCH]
                mask |= 1 << (K_FLIP if e[BRK] else e[KIND])
                if s > top:
                    top, top_e = s, e
                t -= 1
            if 1.0 - keep >= MIN_STRENGTH:
                o_sp[i], o_ss[i], o_st[i] = top_e[PX], 1.0 - keep, touches
                o_sk[i] = (K_FLIP if top_e[BRK] else top_e[KIND]) + 8 * mask
                break
            j -= 1
        j = bisect_left(P, c)
        while j < m and P[j] - c <= reach:
            edge = P[j] + tol
            keep, top, top_e, touches, mask = 1.0, -1.0, None, 0, 0
            t = j
            while t < m and P[t] <= edge:
                e = E[t]
                s = e[BASE] * exp(-(i - e[LAST]) * e[DECAY])
                keep *= 1.0 - s
                touches += e[TOUCH]
                mask |= 1 << (K_FLIP if e[BRK] else e[KIND])
                if s > top:
                    top, top_e = s, e
                t += 1
            if 1.0 - keep >= MIN_STRENGTH:
                o_rp[i], o_rs[i], o_rt[i] = top_e[PX], 1.0 - keep, touches
                o_rk[i] = (K_FLIP if top_e[BRK] else top_e[KIND]) + 8 * mask
                break
            j += 1

    # ------------------------------------------------------------------ assemble
    out = pd.DataFrame(index=df15.index)
    sp, rp = np.array(o_sp), np.array(o_rp)
    with np.errstate(invalid="ignore", divide="ignore"):
        sd, rd = (close - sp) / atr, (rp - close) / atr
        far = DIST_CLIP_ATR
        sdc = np.where(np.isfinite(sd), np.minimum(sd, far), far)
        rdc = np.where(np.isfinite(rd), np.minimum(rd, far), far)
        ss, rs = np.array(o_ss), np.array(o_rs)
        out["sr_sup_near"] = np.where(np.isfinite(sd), 1.0 - sdc / far, 0.0)      # 1 = on it, 0 = far / none
        out["sr_res_near"] = np.where(np.isfinite(rd), 1.0 - rdc / far, 0.0)
        out["sr_sup_str"] = ss
        out["sr_res_str"] = rs
        out["sr_room"] = np.where(atr_ok, (rdc - sdc) / (rdc + sdc), 0.0)         # + = more room up than down
        out["sr_lean"] = ss * out["sr_sup_near"].values - rs * out["sr_res_near"].values
        out["sr_break"] = np.clip(o_brk, -1.0, 1.0)
        out["sr_reject"] = np.clip(o_rej, -1.0, 1.0)
        out["sr_pdh_near"] = np.clip(1.0 - np.abs(close - pdh) / (NEAR_ATR * atr), 0.0, 1.0)
        out["sr_pdl_near"] = np.clip(1.0 - np.abs(close - pdl) / (NEAR_ATR * atr), 0.0, 1.0)
        out["sr_pd_pos"] = np.clip(2.0 * (close - pdl) / (pdh - pdl) - 1.0, -2.0, 2.0) / 2.0
        below = r_idx * r_step
        round_px = np.where(close - below <= below + r_step - close, below, below + r_step)
        round_px = np.where((r_step > 0) & (round_px > 0), round_px, np.nan)
        out["sr_round_near"] = np.clip(1.0 - np.abs(close - round_px) / (NEAR_ATR * atr), 0.0, 1.0)
    out[FEATURES] = out[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    sk, rk = np.array(o_sk, dtype=np.int64), np.array(o_rk, dtype=np.int64)
    out["sup_px"], out["sup_str"] = sp, ss
    out["sup_kind"] = _kind_names(sk)
    out["sup_touches"] = np.array(o_st, dtype=np.int64)
    out["sup_dist_atr"] = sd
    out["res_px"], out["res_str"] = rp, rs
    out["res_kind"] = _kind_names(rk)
    out["res_touches"] = np.array(o_rt, dtype=np.int64)
    out["res_dist_atr"] = rd
    out["pd_high"], out["pd_low"], out["pd_close"] = pdh, pdl, pdc
    out["pw_high"], out["pw_low"] = pwh, pwl
    out["round_px"] = round_px
    out["sr_event"] = np.array(o_evt, dtype=object)
    out["sr_atr1h"] = atr
    return out


def _side(row, name, word):
    px = row.get(name + "_px", float("nan"))
    if px is None or px != px:
        return "no %s within %g ATR" % (word, SEARCH_ATR)
    kind, touches, s = row.get(name + "_kind", ""), int(row.get(name + "_touches", 0) or 0), float(row[name + "_str"])
    what = kind or "level"
    if touches:
        what += ", %d touch%s" % (touches, "" if touches == 1 else "es")
    return "%s %s (%s, %s %.2f, %.1f ATR %s)" % (
        word, _fmt(float(px)), what, "strong" if s >= STRONG else "strength", s,
        float(row[name + "_dist_atr"]), "below" if name == "sup" else "above")


def describe(row):
    """One plain-English sentence for the journal from one row of build()'s output."""
    sup, res = _side(row, "sup", "support"), _side(row, "res", "resistance")
    text = sup[0].upper() + sup[1:] + "; " + res
    sd, rd = row.get("sup_dist_atr", float("nan")), row.get("res_dist_atr", float("nan"))
    if sd == sd and rd == rd:                                     # distances floored at 0.1 ATR: "on the level"
        room = max(float(rd), 0.1) / max(float(sd), 0.1)
        text += "; room up/down %s" % ("%.1f" % room if room < 10 else "over 10")
    evt = row.get("sr_event", "")
    if isinstance(evt, str) and evt:
        text += "; just %s" % evt
    return text + "."
