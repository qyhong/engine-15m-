# -*- coding: utf-8 -*-
"""cards6 -- H122: six commodity cards for gold, silver, WTI and Brent, as a separate PAPER test. NOT passed.

Owner, 28 Nov 2026, in this project: "Yes, build all six" (separate paper test, the contract-switch calendar first).
Registered in research/HYPOTHESES.md H122 before this file existed: the rules below are H122's, never tuned here.
Built so far: C1 (release impulse), C2 (leader lag), C5 (time-of-week drift). C3, C4 and C6 follow.

The live engine NEVER reads this module (it is not in sources.MODULES). Its votes reach only its own paper books, which
are shadow MINDS (shadows.MINDS): advanced after every other book, inside a try/except, writing only their own state.

    votes            v in {-1, -0.5, 0, +0.5, +1} per card at each 15-minute close (0 = silent), from what is known
                     at that close only (closed bars; ATR1h is the engine's own `atr1h` reading)
    mind odds        each speaking card is a voice with share 0.10 and odds (up, down) = (0.35 + 0.10v, 0.35 - 0.10v),
                     neither 0.30; with k cards speaking: (1 - 0.10k) x the live odds + 0.10 x each card's
    books            m_cards6     the Setups rule on the mind odds              (yardstick b_targets)
                     m_cards6_nf  the same, idle_max out of reach               (yardstick b_no_forced)
                     c6_c1 ...    one per card: in at the next open when the card takes a side or flips, out at the
                                  engine's stop or at the next open after the card leaves that side; 2% risk
Kill rules K1-K3 and M1 are checked on the books' own records each step (K4 at the checkpoints, from the journal).
"""
import os
import time

import numpy as np
import pandas as pd

from . import rolls

ASSETS = ("XAUUSD", "XAGUSD", "WTI", "BRENT")
CARDS = ("c1", "c2", "c5")                               # built; "c3", "c4", "c6" to come (H122)
LABEL = "NOT passed, paper only"
HYPOTHESIS = "H122"
SHARE, P_BASE, P_STEP, P_NEITHER = 0.10, 0.35, 0.10, 0.30
BAR_MS = 15 * 60 * 1000
UP, DOWN, NEITHER = 1, 2, 0                              # labels.py: the odds columns

# ---- C1 release impulse (H122)
C1_FULL, C1_HALF, C1_BARS = 1.5, 1.0, 16
C1_METAL_KINDS = ("FOMC", "CPI", "PCE", "GDP")
# ---- C2 leader lag (H122)
C2_WINDOW, C2_RHO, C2_Z, C2_FULL, C2_HALF, C2_BARS, C2_DONE = 20 * 92, 0.20, 2.0, 0.25, 0.5, 4, 0.8
C2_LEADER = {"XAUUSD": "USDJPY", "XAGUSD": "USDJPY", "WTI": "ES", "BRENT": "ES"}
C2_MIN_PAIRS = 500                                       # fewer valid pairs in the window: no estimate, silent
# ---- C5 time-of-week drift (H122)
C5_WEEKS, C5_FULL, C5_HALF, C5_AHEAD = 104, 3.0, 2.5, 16
C5_MIN_HALF = 26                                         # samples needed in each 52-week half (fixed with H122's code)
WEEK_MS = 7 * 86400 * 1000
# ---- kill rules (H122)
K1_R, K2_FROM, K3_SPEAK, K3_SPEAK_SLOW, M1_R = -4.0, 12, 0.40, 0.60, 6.0
START_EQUITY = 10000.0


# =====================================================================================
# helpers
# =====================================================================================
def _ms(times):
    return np.asarray(pd.DatetimeIndex(times).as_unit("ms").asi8, dtype=np.int64)   # whatever unit pandas stores


def _ny(ms):
    """New York local time of epoch ms (vector), via extdata's own daylight-saving rule (no tz database needed)."""
    from . import extdata
    ms = np.asarray(ms, dtype=np.int64)
    off = extdata._manual_offset_ms(ms, extdata.NY)
    return pd.to_datetime(ms + off, unit="ms")


def _trade_dates(close_ms):
    """The futures trade date (New York date; 17:00 and later belongs to the next day) of each bar close."""
    loc = _ny(close_ms)
    d = loc.normalize() + pd.to_timedelta((loc.hour >= 17).astype(int), unit="D")
    return [x.date() for x in d]


def _sizes(x, full, half):
    """|x| -> 1.0 at or above full, 0.5 in [half, full), else 0."""
    ax = np.abs(x)
    return np.where(ax >= full, 1.0, np.where(ax >= half, 0.5, 0.0))


def _consecutive(ms, k, j):
    """True when bars k .. j (k < j) are back to back on the 15-minute grid."""
    return ms[j] - ms[k] == (j - k) * BAR_MS


# =====================================================================================
# release times (C1)
# =====================================================================================
def _eia_rule(start_ms, end_ms):
    """EIA weekly crude report times by rule: Wednesday 10:30 New York; Thursday 11:00 in a week with a US federal
    holiday Monday to Wednesday (calhistory's rule)."""
    from . import calhistory
    out = []
    d = pd.Timestamp(start_ms, unit="ms").normalize().date()
    end = pd.Timestamp(end_ms, unit="ms").date()
    d -= pd.Timedelta(days=d.weekday()).to_pytimedelta()
    while d <= end:
        hol = set(calhistory.federal_holidays(d.year)) | set(calhistory.federal_holidays(d.year + 1))
        mon = d
        shifted = any((mon + pd.Timedelta(days=i).to_pytimedelta()) in hol for i in range(3))
        day = mon + pd.Timedelta(days=3 if shifted else 2).to_pytimedelta()
        out.append(calhistory.et_to_utc_ms(day, 11 if shifted else 10, 0 if shifted else 30))
        d = mon + pd.Timedelta(days=7).to_pytimedelta()
    return [t for t in out if start_ms <= t <= end_ms]


def release_times(asset, until_ms=None, hist_path=None, live_path=None):
    """Sorted epoch ms of the releases C1 reads for this asset: history (calhistory) and, after its last row, the
    engine's live calendar (metals) or the EIA rule (oil)."""
    from . import calhistory
    from .config import DATA_DIR
    hist_path = hist_path or calhistory.HISTORY_CSV
    live_path = live_path or os.path.join(DATA_DIR, "econ_events.csv")
    try:
        h = pd.read_csv(hist_path)
    except (OSError, ValueError):
        h = pd.DataFrame(columns=["ts_ms", "title", "kind"])
    oil = asset in ("WTI", "BRENT")
    if oil:
        h = h[h["kind"] == "EIA"]
    else:
        h = h[h["kind"].isin(C1_METAL_KINDS)]
        h = h[(h["kind"] != "GDP") | h["title"].astype(str).str.contains("Advance", case=False)]
    ts = set(int(x) for x in h["ts_ms"].tolist())
    last = max(ts) if ts else 0
    end = int(until_ms) if until_ms is not None else int(time.time() * 1000) + 30 * 86400 * 1000
    if oil:
        ts |= set(t for t in _eia_rule(last + 86400000, end))
    else:
        try:
            lv = pd.read_csv(live_path)
            t = lv["title"].astype(str)
            keep = ((t.str.match(r"^FOMC [A-Z][a-z]{2} \d{4}$")) | (t.str.match(r"^CPI [A-Z][a-z]{2} \d{4}$"))
                    | t.str.contains("PCE", case=False) | t.str.contains("Advance GDP", case=False))
            lv = lv[keep & (lv["country"].astype(str) == "USD")]
            ts |= set(int(x) for x in lv["ts_ms"].tolist() if int(x) > last)
        except (OSError, ValueError, KeyError):
            pass
    return np.array(sorted(t for t in ts if t <= end), dtype=np.int64)


# =====================================================================================
# the cards: each -> votes for rows r0 .. n-1 (float array of length n - r0)
# =====================================================================================
def c1_votes(ms, o, c, atr, rel_ms, r0, n):
    """C1 release impulse (H122)."""
    out = np.zeros(n - r0)
    if not len(rel_ms):
        return out
    first = max(r0 - C1_BARS - 2, 1)
    lo_ms = ms[first]
    for t in rel_ms[(rel_ms >= lo_ms) & (rel_ms < ms[n - 1] + BAR_MS)]:
        R = int(np.searchsorted(ms, t, side="right")) - 1         # the bar whose 15 minutes hold the release
        if R < 1 or R + 1 >= n or not (ms[R] <= t < ms[R] + BAR_MS) or not _consecutive(ms, R, R + 1):
            continue
        a = atr[R - 1]
        if not (a == a and a > 0):
            continue
        imp = (c[R + 1] - o[R]) / a
        size = float(_sizes(np.array([imp]), C1_FULL, C1_HALF)[0])
        if not size:
            continue
        s = 1.0 if imp > 0 else -1.0
        for k in range(R + 1, min(R + 1 + C1_BARS, n)):
            if s * (c[k] - o[R]) < 0:                             # a close back beyond R's open: silent for good
                break
            if k >= r0:
                out[k - r0] = s * size
    return out


def _leader_close(leader, ms, bars=None):
    """The leader's 15-minute closes on the asset's bar times (NaN where it has no bar)."""
    if bars is None:
        bars = load_leader(leader)
    if bars is None or not len(bars):
        return np.full(len(ms), np.nan)
    return bars.reindex(ms).values.astype(float)


def load_leader(leader):
    """-> pd.Series of closes keyed by bar open ms, or None. USDJPY: the engine's own bar file; ES: the overnight
    card's ES=F file."""
    from .config import DATA_DIR
    path = os.path.join(DATA_DIR, "usdjpy_15m.csv") if leader == "USDJPY" else \
        os.path.join(DATA_DIR, "sources", "overnight_es_15m.csv")
    try:
        df = pd.read_csv(path, usecols=["ts_ms", "close"])
    except (OSError, ValueError):
        return None
    df = df.dropna().drop_duplicates("ts_ms", keep="last")
    if leader == "USDJPY":
        # The fx group writes this file during the same step, and in the parallel step it may already have fetched
        # its new bars while gold and silver are stepped (one after another it never has). So only the bars the fx
        # group had stepped by the end of its last step are read: data/live_state.json "last_ms"["fx"], which no
        # group changes before the fx group's own turn. No mark yet: no leader (C2 silent). The same votes either way.
        try:
            import json
            with open(os.path.join(DATA_DIR, "live_state.json"), encoding="utf-8") as fh:
                mark = (json.load(fh).get("last_ms") or {}).get("fx")
        except (OSError, ValueError):
            mark = None
        if mark is None:
            return None
        df = df[df["ts_ms"] <= int(mark)]
    return pd.Series(df["close"].values, index=df["ts_ms"].values.astype(np.int64))


def c2_votes(asset, ms, o, c, lead_c, r0, n):
    """C2 leader lag (H122). lead_c: the leader's closes on the asset's bar times (NaN = no bar)."""
    out = np.zeros(n - r0)
    gap_ok = np.r_[False, np.diff(ms) == BAR_MS]
    with np.errstate(divide="ignore", invalid="ignore"):
        ra = np.where(gap_ok, np.log(c / np.r_[np.nan, c[:-1]]), np.nan)
        rl = np.where(gap_ok, np.log(lead_c / np.r_[np.nan, lead_c[:-1]]), np.nan)
    valid = np.isfinite(ra) & np.isfinite(rl)
    vidx = np.where(valid)[0]
    leader = C2_LEADER[asset]
    first = max(r0 - C2_BARS, 1)
    speak = {}                                                    # row -> vote, from triggers at first .. n-1
    for k in range(first, n):
        if not valid[k]:
            continue
        j = int(np.searchsorted(vidx, k))                         # pairs strictly before k
        win = vidx[max(j - C2_WINDOW, 0):j]
        if len(win) < C2_MIN_PAIRS:
            continue
        x, y = rl[win], ra[win]
        sx = x.std()
        if not sx > 0 or not y.std() > 0:
            continue
        rho = float(np.corrcoef(x, y)[0, 1])
        z = rl[k] / sx
        if abs(rho) < C2_RHO or abs(z) < C2_Z:
            continue
        if rolls.near_switch(asset, int(ms[k]) + BAR_MS) or (leader == "ES" and rolls.near_switch("ES", int(ms[k]) + BAR_MS)):
            continue
        beta = float(np.cov(x, y, bias=True)[0, 1] / (sx * sx))
        E = beta * rl[k]
        if not E:
            continue
        ratio = ra[k] / E
        size = 1.0 if ratio <= C2_FULL else 0.5 if ratio <= C2_HALF else 0.0
        if not size:
            continue
        s = 1.0 if E > 0 else -1.0
        for m in range(k, min(k + C2_BARS, n)):
            if m > k:
                if not _consecutive(ms, k, m) or not np.isfinite(lead_c[m]):
                    break
                if np.log(c[m] / o[k]) / E >= C2_DONE:            # the asset has caught up: silent
                    break
            speak[m] = s * size                                   # a later trigger overrides an earlier one
    for m, v in speak.items():
        if r0 <= m < n:
            out[m - r0] = v
    return out


def _clock_change_week(dates):
    """True for New York dates in the 7 days from a US clock-change Sunday (second Sunday of March, first of Nov)."""
    out = []
    cache = {}
    for d in dates:
        y = d.year
        if y not in cache:
            mar = pd.Timestamp(y, 3, 1)
            nov = pd.Timestamp(y, 11, 1)
            s1 = (mar + pd.Timedelta(days=(6 - mar.weekday()) % 7 + 7)).date()
            s2 = (nov + pd.Timedelta(days=(6 - nov.weekday()) % 7)).date()
            cache[y] = (s1, s2)
        out.append(any(0 <= (d - s).days < 7 for s in cache[y]))
    return np.array(out, dtype=bool)


def c5_prepare(asset, ms, c):
    """The per-bar facts C5 needs, for the whole history (one pass): slot, close ms, the next-4h log return (NaN when
    incomplete or not back to back), and whether the bar is excluded (near a switch, a holiday, a clock-change week)."""
    n = len(ms)
    close = ms + BAR_MS
    loc = _ny(close)
    slot = (loc.weekday * 48 + loc.hour * 2 + loc.minute // 30).values.astype(np.int16)
    fr = np.full(n, np.nan)
    k = np.arange(n - C5_AHEAD)
    ok = (ms[k + C5_AHEAD] - ms[k]) == C5_AHEAD * BAR_MS
    with np.errstate(divide="ignore", invalid="ignore"):
        fr[k[ok]] = np.log(c[k[ok] + C5_AHEAD] / c[k[ok]])
    tdates = _trade_dates(close)
    uniq = sorted(set(tdates))
    bad_day = {}
    for d in uniq:
        bad = (not rolls.is_bday(d)) or rolls.near_switch(asset, pd.Timestamp(d).value // 10 ** 6 + 17 * 3600000)
        bad_day[d] = bad
    excl = np.array([bad_day[d] for d in tdates], dtype=bool) | _clock_change_week([x.date() for x in loc.normalize()])
    return {"slot": slot, "close": close, "fr": fr, "excl": excl}


def c5_votes(prep5, r0, n):
    """C5 time-of-week drift (H122), from c5_prepare's facts."""
    out = np.zeros(n - r0)
    slot, close, fr, excl = prep5["slot"], prep5["close"], prep5["fr"], prep5["excl"]
    usable = np.isfinite(fr) & ~excl
    groups = {}
    for k in range(r0, n):
        if excl[k]:
            continue
        s = int(slot[k])
        if s not in groups:
            idx = np.where((slot == s) & usable)[0]
            groups[s] = idx
        idx = groups[s]
        t = close[k]
        done = idx[(close[idx] + C5_AHEAD * BAR_MS <= t) & (close[idx] >= t - C5_WEEKS * WEEK_MS)]
        if len(done) < 2 * C5_MIN_HALF:
            continue
        mid = t - (C5_WEEKS // 2) * WEEK_MS
        old, new = done[close[done] < mid], done[close[done] >= mid]
        if len(old) < C5_MIN_HALF or len(new) < C5_MIN_HALF:
            continue
        x = fr[done]
        sd = x.std(ddof=1)
        if not sd > 0:
            continue
        tstat = x.mean() / (sd / np.sqrt(len(x)))
        size = float(_sizes(np.array([tstat]), C5_FULL, C5_HALF)[0])
        if not size:
            continue
        sg = np.sign(x.mean())
        if np.sign(fr[old].mean()) != sg or np.sign(fr[new].mean()) != sg:
            continue
        out[k - r0] = sg * size
    return out


# =====================================================================================
# all cards of one asset, and the mind odds
# =====================================================================================
def votes(asset, times, px, ev, r0, n, leader=None, rel=None, c5=None):
    """{card: votes for rows r0 .. n-1} for one asset of a group prep (times, px dict, ev frame)."""
    ms = _ms(times)
    o, c = np.asarray(px["open"], float), np.asarray(px["close"], float)
    atr = np.asarray(ev["atr1h"].values, float)
    rel = release_times(asset, until_ms=int(ms[n - 1]) + BAR_MS) if rel is None else rel
    lead_c = _leader_close(C2_LEADER[asset], ms, leader)
    c5 = c5_prepare(asset, ms[:n], c[:n]) if c5 is None else c5
    return {"c1": c1_votes(ms, o, c, atr, rel, r0, n),
            "c2": c2_votes(asset, ms, o, c, lead_c, r0, n),
            "c5": c5_votes(c5, r0, n)}


def mind_odds(live, card_votes, muted=()):
    """(rows, 3) live odds + {card: votes of the same rows} -> the mind's odds (H122's mixing). A muted card is
    treated as silent. Rows where the live odds are NaN stay NaN."""
    live = np.asarray(live, float)
    out = live.copy()
    vs = [np.asarray(v, float) for k, v in card_votes.items() if k not in muted]
    if not vs:
        return out
    V = np.stack(vs, axis=1)                                     # (rows, cards)
    speak = V != 0
    k = speak.sum(axis=1)
    out = live * (1.0 - SHARE * k)[:, None]
    out[:, UP] += SHARE * np.where(speak, P_BASE + P_STEP * V, 0.0).sum(axis=1)
    out[:, DOWN] += SHARE * np.where(speak, P_BASE - P_STEP * V, 0.0).sum(axis=1)
    out[:, NEITHER] += SHARE * P_NEITHER * k
    return out


# =====================================================================================
# a card's own book (c6_<card>)
# =====================================================================================
def _blank():
    return {"pos": 0, "eq": START_EQUITY, "equity_marked": START_EQUITY, "fees": 0.0, "qty": 0.0, "entry": None,
            "stop": None, "t_in_ms": None, "i_in": None, "why_in": None, "stop0": None, "mark": None,
            "act": None, "sig": 0, "stats": {"n": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0, "r_n": 0, "win_usd": 0.0, "loss_usd": 0.0}}


def card_book(st, ms, o, h, l, c, unit, vote, r0, n, cfg):
    """Advance one card's paper book over rows r0 .. n-1 (vote[k - r0] is known at the close of row k; orders fill at
    the next bar's open). -> (state, closed trades as tuples in shadows.TRADE_COLS order)."""
    st = dict(st) if st else _blank()
    st["stats"] = dict(st.get("stats") or _blank()["stats"])
    fee = float(cfg.get("cost_side", 0.0))
    risk = float(cfg.get("risk_per_trade", 0.02))
    cap = float(cfg.get("leverage_cap", 1.0) or 1.0)
    stop_mult = float(cfg.get("stop_units", 2.0))
    trades = []

    def close(k, price, why):
        pos, q, e = st["pos"], st["qty"], st["entry"]
        gross = q * pos * (price - e)
        fees = fee * q * (e + price)
        st["eq"] += gross - fees
        st["fees"] += fees
        pnl = gross - fees
        risk_usd = q * abs(e - st["stop0"])
        r = pnl / risk_usd if risk_usd else np.nan
        trades.append((st["t_in_ms"], int(ms[k]), st["i_in"], k, pos, e, price, st["why_in"], why,
                       pnl / (q * e) * 100.0, st["eq"], q, pnl, fees, st["stop0"], risk_usd, r, None, None))
        s = st["stats"]
        s["n"] += 1
        s["wins"] += int(pnl > 0)
        s["pnl"] += pnl
        s["win_usd" if pnl > 0 else "loss_usd"] += abs(pnl)
        if r == r:
            s["r_sum"] += r
            s["r_n"] += 1
        st.update(pos=0, qty=0.0, entry=None, stop=None, t_in_ms=None, i_in=None, why_in=None, stop0=None)

    for k in range(r0, n):
        act = st.get("act")                                      # decided at the previous close, done at this open
        if act is not None and k > 0:
            if st["pos"] and (act == "exit" or act != st["pos"]):
                close(k, o[k], "CARD_OFF" if act == "exit" else "CARD_FLIP")
            u = unit[k - 1]
            if act in (1, -1) and not st["pos"] and u == u and u > 0:
                dist = stop_mult * u
                lev = min(cap, max(1.0, risk / (dist / o[k]))) if cap > 1.0 else 1.0
                q = lev * st["eq"] / o[k]
                st.update(pos=act, qty=q, entry=float(o[k]), stop=float(o[k] - act * dist),
                          stop0=float(o[k] - act * dist), t_in_ms=int(ms[k]), i_in=k, why_in="CARD")
            st["act"] = None
        if st["pos"]:
            hit = l[k] <= st["stop"] if st["pos"] > 0 else h[k] >= st["stop"]
            if hit:
                px_ = min(o[k], st["stop"]) if st["pos"] > 0 else max(o[k], st["stop"])   # a gap through the stop
                close(k, px_, "STOP")
        s, p = int(np.sign(vote[k - r0])), int(st.get("sig") or 0)
        if s and s != p:                                         # silent -> a side, or a flip: in at the next open
            st["act"] = s
        elif not s and st["pos"]:                                # the card left its side: out at the next open
            st["act"] = "exit"
        st["sig"] = s
        st["mark"] = float(c[k])
        st["equity_marked"] = st["eq"] + (st["qty"] * st["pos"] * (c[k] - st["entry"]) if st["pos"] else 0.0)
        st["last_ms"] = int(ms[k])
    return st, trades


# =====================================================================================
# kill rules (H122), from a book's closed trades
# =====================================================================================
def kill_state(trades_r, speak_share, card):
    """trades_r: the R of each closed trade in order. -> (muted?, reason or None)."""
    r = [x for x in trades_r if x == x]
    if sum(r) <= K1_R:
        return True, "K1: sum %.1fR <= %.1fR" % (sum(r), K1_R)
    if len(r) >= K2_FROM:
        wins = sum(1 for x in r if x > 0)
        avg_w = np.mean([x for x in r if x > 0]) if wins else 0.0
        avg_l = -np.mean([x for x in r if x <= 0]) if wins < len(r) else 0.0
        be = avg_l / (avg_w + avg_l) if (avg_w + avg_l) > 0 else 1.0
        if np.mean(r) < 0 and wins / len(r) < be:
            return True, "K2: mean %.2fR, won %.0f%% below break-even %.0f%%" % (np.mean(r), 100 * wins / len(r), 100 * be)
    lim = K3_SPEAK_SLOW if card in ("c5", "c6") else K3_SPEAK
    if speak_share is not None and speak_share > lim:
        return True, "K3: speaks on %.0f%% of open bars (limit %.0f%%)" % (100 * speak_share, 100 * lim)
    return False, None
