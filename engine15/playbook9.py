# -*- coding: utf-8 -*-
"""playbook9 -- H115: H107's capitulation-rebound long on BTC and ETH, rule A and rule B side by side, run FORWARD as
two paper books (p9_rebound_a, p9_rebound_b). PAPER ONLY. NOT PASSED.

Owner, 24 Nov 2026: "So how can we seize the opportunity when the capitulation occur. How can we do the long setup?"
and, to the proposal: "build the paper capitulation-long book with the Telegram alert". Registered as H115 in
research/HYPOTHESES.md BEFORE this code. History does NOT support the rule (H107: rule A flat over 123 trades, lost in
the first half and won in the second; rule B 32 trades, too few to judge; H70, H71, H113 agree): the book exists
because the owner asked for it. It places no order, changes no book and no decision, and never reaches the VIP vault.

THE RULES (frozen exactly as H107's; research/h107_capitulation_rebound.py: features, walk_loop, trades_of; held equal
to that script trade for trade by tests/test_playbook9.py). Per coin, at the close of each 15m bar k, bars up to k only:
  ATR(1h)  Wilder ATR(14) of the 1h bars, through data.htf_on_15 (closed 1h bars only)
  low16    the lowest low of bars k-15..k (4 hours);  low30d  the lowest low of the bars opened in the 30 days up to k
  c7       the close of the last bar opened at or before open(k) - 7 days
  rule A   low16 <= low30d  AND  low16 / c7 - 1 <= -10%  AND  close(k) >= low16 + 2 x ATR(1h), and not all three true
           at k-1 (onset only)
  rule B   rule A's signal AND the last funding rate set at or before the close of k is below zero (shorts pay)
  trade    long at the open of bar k+1 = P; R = 3 x ATR(1h) at k; stop P - R; bars k+1 .. k+192 (48 hours) are walked:
           the stop first (out at the stop, or at the open if the open is below it); then Target 1 = P + R (half out;
           the stop on the rest moves to P from the NEXT bar); then Target 2 = P + 2R (the rest out, also in the
           Target 1 bar); what is left goes out at the close of bar k+192. One trade at a time per rule and coin; a
           signal while that rule's trade is open is counted and not taken.

FUNDING (rule B): the engine's live source, data/<coin>_funding.csv (data.load_funding; live._update_bars refreshes it
at every crypto step). Stale = the rate was set more than FUND_MAX_AGE_MS (9 hours: one 8-hour interval plus one hour)
before the deciding close. Missing or stale: rule B does not fire, and one log line says so.

SIZING: $10,000 per trade, per coin and per rule, 1x, not compounded (docs/PLAYBOOK_INTERFACE.md); fee 0.10% a side on
the entry and on each part's exit; funding is not charged (as H107's R). Each trade records its net R and its dollars.

FORWARD ONLY, WITH ITS OWN STATE (data/capit_long_state.json, written atomically). Unlike the stateless books, a
decision here is made ONCE, by the step that first sees the bar, with the funding known then, and is never recomputed.
The record starts at the first step that finds no state (the last 15m close before that step's clock, never before
REGISTERED): only a bar that CLOSES after that can decide, so no trade from history is ever written. A restart
resumes from the file; a missing or unreadable file starts flat again and says so (an unreadable one is kept as
capit_long_state.json.bad-<unix time>). Bars missed while the engine was down are walked one by one when it is back;
a trigger found late is taken at the rule's own fill and marked late.

THE ALERT: the state's "alerts" list holds one entry per coin and deciding close at which a rule opened a trade;
engine15/telegram_notify.py (a separate process, read only) sends it to the owner's own chat once. Nothing here sends
anything.

THE RETEST LEVELS (owner, 24 Nov 2026; a NOTICE, not a setup, not a hypothesis, no trade): the low behind each rule A
trigger is H116's "level" (research/h116_retest_capitulation_low.py, machine): dead, armed, first touch, and here also
broken (a low under it after the first touch). The levels are recomputed at every new bar from a 93-day tail of closed
bars (levels_of; LEVEL_TAIL_DAYS says why 93), kept under the state's "zone" key beside the trades (the trades' own
keys are not touched) and shown on the page; telegram_notify.py sends the owner one notice at the first touch and one
at the break. They open, close and change nothing in the two books.

THE REBOUND SIGNAL FILE (owner, 25 Nov 2026: "(2) a dry run of the rebound in the vault"): out/live/rebound_signal.json,
rewritten at every live step, holds rule A's trade per coin (p9_rebound_a: the trigger and the long b_rebound takes)
as none / waiting / open, with its id, levels and time exit, and its last closed trade. It is for the VIP vault's DRY
RUN only (log what it would have done per member, place nothing). Nothing on the money path reads it; it adds no key
to the book or to an intent; it changes no trade here. Only the live step writes it (state_path None), or a caller
that names signal_path.

Rows follow docs/PLAYBOOK_INTERFACE.md (status WAITING / OPEN / CLOSED, side 1). A failure is logged in one line and
skipped; it never stops the engine's step (reports.playbooks wraps the module too). Constants live here, not in CFG.
"""
import copy
import io
import json
import math
import os
import time

import numpy as np
import pandas as pd

from . import data
from . import indicators as ind
from .config import DATA_DIR, OUT_DIR

REGISTERED = "2026-11-24 12:50"     # UTC: H115 committed; the record never starts before it
STAKE = 10000.0
BAR_MS = 900000
ASSETS = ("BTCUSDT", "ETHUSDT")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}

# ---------------------------------------------------------------- frozen H107 parameters (do not change)
LOOK = 16                           # bars: the 4-hour low
LOW_DAYS = 30                       # a fresh 30-day low
DROP_DAYS = 7                       # ... at least DROP below the close a week earlier
DROP = 0.10
BOUNCE_ATR = 2.0                    # the rebound off that low, in ATR(1h)
HOLD = 192                          # bars: 48 hours
STOP_ATR = 3.0                      # the engine's stop when H107 was registered: stop_units 2 x barrier_atr 1.5
FEE = 0.0010                        # a side, of notional (CFG["cost_side"] when H107 was registered)

# ---------------------------------------------------------------- this book's own settings (H115)
FUND_INTERVAL_MS = 8 * 3600000      # Binance sets BTC and ETH funding every 8 hours
FUND_GRACE_MS = 3600000             # one hour: four engine steps for a late fetch, far short of a second interval
FUND_MAX_AGE_MS = FUND_INTERVAL_MS + FUND_GRACE_MS
TAIL_BARS = 45 * 96                 # bars read each step: 30 days for the low, the rest for the 7-day close and the ATR
LATE_MS = BAR_MS                    # a trigger first seen after the next bar has closed is marked late
ALERTS_KEPT = 100
STATE_VERSION = 1
STATE_PATH = os.path.join(DATA_DIR, "capit_long_state.json")
SIGNAL_PATH = os.path.join(OUT_DIR, "live", "rebound_signal.json")   # the vault's dry run reads it (25 Nov 2026)
SIGNAL_SCHEMA = 1
SIGNAL_BOOK = "p9_rebound_a"        # rule A: the trigger and the long that b_rebound (H117) takes

# ---------------------------------------------------------------- the retest levels (H116's level; a notice, no trade)
LEVEL_LIFE_DAYS = 30                # a level counts at bars that open at most this long after its trigger bar opened
LEVEL_ARM = 0.05                    # armed: a high at least 5% above the low
LEVEL_ZONE = 0.015                  # first touch: a low at or below the low + 1.5%
LEVEL_KEEP_DAYS = 2                 # a level stays listed this long after its last bar (the bot's 48-hour limit)
# The tail the levels are recomputed from at every new bar, counted back from the newest bar T:
#   32 days  a level is listed when its trigger bar opened in the last LEVEL_LIFE_DAYS + LEVEL_KEEP_DAYS days;
#   30 days  the same-low rule asks which levels were made in the 30 days before that trigger, so the triggers must be
#            right back to T - 62 days;
#   30 days  a trigger is right only with a full 30 days of lows behind it AND behind the bar before it (the onset),
#            so the tail must start by T - 92 days - 15 minutes. The 7-day close and the 16-bar low lie inside that,
#            and Wilder's ATR(1h) then has at least 30 days behind every bar that can trigger (its start weighs
#            (13/14)^720, about 1e-23, by then).
#   1 day    spare. A gap in the bars only makes the tail reach further back.
# Not covered, by any tail: three or more triggers off EXACTLY the same low price that chain across more than 30 days
# (each within 30 days of the next); tests/test_capit_zone.py holds the tail to the research script on the real bars.
LEVEL_TAIL_DAYS = LEVEL_LIFE_DAYS + LEVEL_KEEP_DAYS + 30 + 30 + 1
LEVEL_TAIL_BARS = LEVEL_TAIL_DAYS * 96
LEVELS_NOTE = ("A notice, not a setup: no trade is opened at a level. The level is the low behind a rule A trigger "
               "(H116). On history (77 retests, 2019 to 2025) price traded under the old low within four days in 88% of "
               "the retests (median lowest point 6.6% below it), and a day after the first touch it was higher in 58% "
               "(median +1.9%). H116 tested buying the retest: too few trades to judge, and a small loss on those.")

RULES = {"p9_rebound_a": "A", "p9_rebound_b": "B"}
HOW = ("STOP", "T1+BE", "T1+T2", "T1+TIME", "TIME")       # research walk(): how 0..4
HOW_WORDS = ("stopped", "Target 1, then stopped at the entry", "Target 1 and Target 2",
             "Target 1, then the 48-hour exit", "the 48-hour exit")
HISTORY = ("On history (H107, 2019-10 to 2025-11, BTC + ETH, after fees) rule A was flat over 123 trades (-0.006R a "
           "trade; it lost in the first half and won in the second) and rule B had 32 trades (+0.19R a trade), too few "
           "to judge. H70, H71 and H113 found no rebound-long rule or reading that held up.")
NOT_PASSED = ("NOT passed. Started because the owner asked for it (24 Nov 2026), not because a study passed: H107's "
              "rule A FAILED its registered test and rule B had too few trades to judge. Paper only; it never reaches "
              "the vault.")
BOOKS = {
    "p9_rebound_a": {"title": "Capitulation rebound long, rule A (H107 rule A, forward paper); NOT passed",
                     "short": "Capitulation long A", "hypothesis": "H115 (H107 rule A), forward", "rule_id": "A",
                     "registered": REGISTERED, "assets": ASSETS,
                     "scoreboard_title": "Strategy: capitulation rebound long, rule A, H115 (NOT passed, forward paper)"},
    "p9_rebound_b": {"title": "Capitulation rebound long, rule B: A when shorts pay funding (H107 rule B, forward "
                              "paper); NOT passed",
                     "short": "Capitulation long B", "hypothesis": "H115 (H107 rule B), forward", "rule_id": "B",
                     "registered": REGISTERED, "assets": ASSETS,
                     "scoreboard_title": "Strategy: capitulation rebound long, rule B (A when shorts pay funding), "
                                         "H115 (NOT passed, forward paper)"},
}

LAST_RUN = {}


def reg_ms():
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


# ---------------------------------------------------------------- small helpers
def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _f(v, k=None):
    """A finite float (rounded to k places) or None: nothing that is not a number reaches the state or a row."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return x if k is None else round(x, k)


def _px(v):
    v = _f(v)
    return "n/a" if v is None else "{:,.2f}".format(v)


def _say(log, text):
    try:
        if log is not None:
            log(text)
    except Exception:
        pass


# ---------------------------------------------------------------- readings (row k uses closed bars <= k only)
def features(df, fund=None, max_age_ms=FUND_MAX_AGE_MS):
    """Every reading as known at each 15m bar's close, as research/h107_capitulation_rebound.features, plus when the
    funding rate was set and whether it is fresh. df: 15m frame keyed by open time (open/high/low/close); fund: Series
    of rates keyed by the time each was SET (data.load_funding), or None. max_age_ms None: no staleness guard.
    -> dict of arrays."""
    t = df.index
    n = len(t)
    o, h, l, c = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    full = df
    for col in ("volume", "taker_buy"):                          # data.resample sums them; they are not read here
        if col not in full.columns:
            full = full.assign(**{col: 0.0})
    h1 = data.resample(full, "1h")
    atr1h = data.htf_on_15(df, "1h", ind.atr_wilder(h1)).values.astype(float)
    low16 = pd.Series(l).rolling(LOOK, min_periods=LOOK).min().values
    lowN = pd.Series(l, index=t).rolling("%dD" % LOW_DAYS).min().values
    have = np.asarray(t >= t[0] + pd.Timedelta(days=LOW_DAYS)) if n else np.zeros(0, bool)
    j = t.searchsorted(t - pd.Timedelta(days=DROP_DAYS), side="right") - 1
    cref = np.where(j >= 0, c[np.maximum(j, 0)], np.nan) if n else np.zeros(0)
    open_ms = data.to_ms(t)
    close_ms = open_ms + BAR_MS
    fund_last = np.full(n, np.nan)
    fund_set = np.full(n, -1, dtype="int64")
    if fund is not None and len(fund):
        fms = data.to_ms(pd.DatetimeIndex(fund.index))
        fv = np.asarray(fund.values, dtype=float)
        if len(fms) > 1 and not (np.diff(fms) >= 0).all():
            order = np.argsort(fms, kind="stable")
            fms, fv = fms[order], fv[order]
        fi = np.searchsorted(fms, close_ms, side="right") - 1    # the last rate set at or before the bar's close
        got = fi >= 0
        fund_last[got] = fv[fi[got]]
        fund_set[got] = fms[fi[got]]
    known = (fund_set >= 0) & np.isfinite(fund_last)
    fresh = known if max_age_ms is None else known & (close_ms - fund_set <= int(max_age_ms))
    with np.errstate(invalid="ignore", divide="ignore"):
        is_low = have & (low16 <= lowN)
        drop = low16 / cref - 1.0 <= -DROP
        bounce = c - low16 >= BOUNCE_ATR * atr1h
        trig = is_low & drop & bounce & np.isfinite(atr1h)
        neg = fund_last < 0
    prev = np.concatenate([[True], trig[:-1]]) if n else np.zeros(0, bool)
    onset = trig & ~prev
    return {"t": t, "open_ms": open_ms, "close_ms": close_ms, "o": o, "h": h, "l": l, "c": c, "atr1h": atr1h,
            "low16": low16, "lowN": lowN, "cref": cref, "fund": fund_last, "fund_set_ms": fund_set, "fund_fresh": fresh,
            "is_low": is_low, "drop": drop, "bounce": bounce, "trig": trig, "A": onset, "B": onset & neg & fresh}


# ---------------------------------------------------------------- the state
def new_state(started_ms):
    return {"version": STATE_VERSION, "started_ms": int(started_ms), "started_utc": _utc(started_ms),
            "last_open_ms": {}, "books": dict((b, dict((a, {"pending": None, "open": None}) for a in ASSETS))
                                              for b in RULES),
            "closed": [], "alerts": [], "skipped": dict((b, dict((a, 0) for a in ASSETS)) for b in RULES),
            "readings": {}}


def _valid(st):
    if not isinstance(st, dict) or st.get("version") != STATE_VERSION:
        return False
    if not isinstance(st.get("started_ms"), int) or not isinstance(st.get("last_open_ms"), dict):
        return False
    if not isinstance(st.get("closed"), list) or not isinstance(st.get("alerts"), list):
        return False
    bk, sk = st.get("books"), st.get("skipped")
    if not isinstance(bk, dict) or not isinstance(sk, dict) or not isinstance(st.get("readings"), dict):
        return False
    for b in RULES:
        if not isinstance(bk.get(b), dict) or not isinstance(sk.get(b), dict):
            return False
        for a in ASSETS:
            slot = bk[b].get(a)
            if not isinstance(slot, dict) or "pending" not in slot or "open" not in slot:
                return False
            for key in ("pending", "open"):
                if slot[key] is not None and not isinstance(slot[key], dict):
                    return False
    return True


def load_state(path=None, log=print):
    """-> (state or None, why). None: the file is missing or cannot be used, and the book starts flat. An unreadable
    file is moved aside (<path>.bad-<unix time>), never overwritten unseen."""
    path = path or STATE_PATH
    if not os.path.exists(path):
        _say(log, "playbook9: no state file (%s): the book starts flat from this step" % os.path.basename(path))
        return None, "missing"
    try:
        with io.open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        if not _valid(st):
            raise ValueError("not this book's state")
        return st, None
    except Exception as e:
        kept = "%s.bad-%d" % (path, int(time.time()))
        try:
            os.replace(path, kept)
            where = "kept as %s" % os.path.basename(kept)
        except OSError:
            where = "it could not be moved aside"
        _say(log, "playbook9: the state file cannot be read (%s; %s): the book starts flat from this step and the "
                  "record made so far is not in it" % (type(e).__name__, where))
        return None, "corrupt"


def save_state(st, path=None):
    path = path or STATE_PATH
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, allow_nan=False, sort_keys=True)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


# ---------------------------------------------------------------- the trade, one bar at a time (H107's walk_loop)
def _open_trade(p, entry, entry_open_ms):
    """A waiting entry filled at the open of the bar after its deciding bar."""
    R = float(p["r_dist"])
    P = float(entry)
    tr = dict(p)
    tr.update({"entry": P, "entry_open_ms": int(entry_open_ms), "stop0": P - R, "stop": P - R, "t1": P + R,
               "t2": P + 2.0 * R, "q": 1.0, "t1_taken": False, "t1_close_ms": None, "got": 0.0, "fees": FEE * P,
               "bars": 0, "mark": P, "r_mark": -FEE * 2.0 * P / R})
    return tr


def _walk_bar(tr, o, h, l, c, close_ms):
    """One bar of an open trade, as research walk_loop. Mutates tr. -> None while it stays open, else the trade
    closed (how 0 stop, 1 Target 1 then the entry, 2 Target 1 and Target 2, 3 Target 1 then time, 4 time)."""
    P, R = tr["entry"], tr["r_dist"]
    tr["bars"] += 1
    how, x = None, None
    if l <= tr["stop"]:                                           # the stop is looked at first in a bar
        x = min(o, tr["stop"])
        how = 1 if tr["t1_taken"] else 0
    else:
        new_t1 = False
        if not tr["t1_taken"] and h >= tr["t1"]:
            tr["got"] += 0.5 * (tr["t1"] - P)
            tr["fees"] += FEE * 0.5 * tr["t1"]
            tr["q"], tr["t1_taken"], tr["t1_close_ms"], new_t1 = 0.5, True, int(close_ms), True
        if tr["t1_taken"] and h >= tr["t2"]:
            x, how = tr["t2"], 2
        else:
            if new_t1:
                tr["stop"] = P                                    # from the NEXT bar
            if tr["bars"] >= HOLD:
                x, how = c, (3 if tr["t1_taken"] else 4)
    if how is None:
        tr["mark"] = float(c)
        tr["r_mark"] = (tr["got"] + tr["q"] * (c - P) - tr["fees"] - FEE * tr["q"] * c) / R
        return None
    tr["got"] += tr["q"] * (x - P)
    tr["fees"] += FEE * tr["q"] * x
    net = tr["got"] - tr["fees"]
    done = dict(tr)
    for k in ("mark", "r_mark", "q", "stop"):
        done.pop(k, None)
    done.update({"exit": float(x), "exit_close_ms": int(close_ms), "how": int(how), "why_out": HOW[how],
                 "r": net / R, "pct": net / P, "pnl_usd": STAKE * net / P, "fees_usd": STAKE * tr["fees"] / P})
    return done


def _alert(st, asset, dec):
    for a in st["alerts"]:
        if a.get("id") == "%s|%d" % (asset, dec):
            return a
    return None


def _advance(st, asset, fx, i, now_ms=None, log=None):
    """Bar i of `asset` has closed: fill what was waiting at its open, walk the open trades through it, then decide
    at its close. Uses fx at rows <= i only. Mutates st."""
    o, h, l, c = float(fx["o"][i]), float(fx["h"][i]), float(fx["l"][i]), float(fx["c"][i])
    open_ms, close_ms = int(fx["open_ms"][i]), int(fx["close_ms"][i])
    name = SHORT_NAME.get(asset, asset)
    for book, rule in RULES.items():
        slot = st["books"][book][asset]
        if slot["pending"] is not None:                           # decided at an earlier close: this bar's open fills it
            tr = _open_trade(slot["pending"], o, open_ms)
            slot["pending"], slot["open"] = None, tr
            al = _alert(st, asset, tr["decided_ms"])
            if al is not None and "entry" not in al:
                al.update({"entry": tr["entry"], "stop": tr["stop0"], "t1": tr["t1"], "t2": tr["t2"]})
            _say(log, "playbook9 %s rule %s: paper long filled at %s (stop %s, Target 1 %s, Target 2 %s)" % (
                name, rule, _px(tr["entry"]), _px(tr["stop0"]), _px(tr["t1"]), _px(tr["t2"])))
        if slot["open"] is not None:
            done = _walk_bar(slot["open"], o, h, l, c, close_ms)
            if done is not None:
                slot["open"] = None
                done["id"] = "%s|%s|%d" % (book, asset, done["decided_ms"])
                st["closed"].append(done)
                _say(log, "playbook9 %s rule %s: closed (%s) at %s: %+.2fR, %+.2f USD on paper" % (
                    name, rule, HOW_WORDS[done["how"]], _px(done["exit"]), done["r"], done["pnl_usd"]))
    if not bool(fx["A"][i]):
        return
    atr = float(fx["atr1h"][i])
    if not (math.isfinite(atr) and atr > 0):                      # research trades_of: no trade without an ATR
        return
    fund, fset = _f(fx["fund"][i]), int(fx["fund_set_ms"][i])
    fresh = bool(fx["fund_fresh"][i])
    R = STOP_ATR * atr
    dec = {"asset": asset, "k_open_ms": open_ms, "decided_ms": close_ms, "decided_utc": _utc(close_ms), "close": c,
           "atr1h": atr, "r_dist": R, "low16": float(fx["low16"][i]),
           "drop_pct": float((fx["low16"][i] / fx["cref"][i] - 1.0) * 100.0),
           "bounce_atr": float((c - fx["low16"][i]) / atr), "funding": fund,
           "funding_set_ms": fset if fset >= 0 else None, "funding_fresh": fresh,
           "seen_ms": None if now_ms is None else int(now_ms),
           "late": bool(now_ms is not None and int(now_ms) - close_ms > LATE_MS)}
    took, why = [], {}
    for book, rule in RULES.items():
        slot = st["books"][book][asset]
        if rule == "B" and not bool(fx["B"][i]):
            if fund is None or fset < 0:
                why["B"] = "funding_missing"
            elif not fresh:
                why["B"] = "funding_stale"
            else:
                why["B"] = "funding_not_negative"
            continue
        if slot["open"] is not None or slot["pending"] is not None:
            st["skipped"][book][asset] = int(st["skipped"][book][asset]) + 1
            why[rule] = "in_trade"
            continue
        slot["pending"] = dict(dec, book=book, rule=rule)
        took.append(rule)
    at = "%s UTC close (%s %s)" % (_utc(close_ms), name, _px(c))
    if why.get("B") == "funding_missing":
        _say(log, "playbook9 %s: rule A fired at the %s but there is no funding reading: rule B does not fire" % (name, at))
    elif why.get("B") == "funding_stale":
        _say(log, "playbook9 %s: rule A fired at the %s but the funding reading is stale (last set %s UTC, %.1f h before "
                  "the close; limit %.0f h): rule B does not fire" % (
                      name, at, _utc(fset), (close_ms - fset) / 3600000.0, FUND_MAX_AGE_MS / 3600000.0))
    for rule, w in sorted(why.items()):
        if w == "in_trade":
            _say(log, "playbook9 %s: rule %s fired again at the %s while its trade is open: counted, not taken" % (
                name, rule, at))
    if not took:
        return
    st["alerts"].append(dict(dec, id="%s|%d" % (asset, close_ms), rules=took, not_taken=why,
                             entry_est=c, stop_est=c - R, t1_est=c + R, t2_est=c + 2.0 * R,
                             risk_pct=100.0 * R / c, time_exit_ms=close_ms + HOLD * BAR_MS,
                             time_exit_utc=_utc(close_ms + HOLD * BAR_MS)))
    del st["alerts"][:-ALERTS_KEPT]
    _say(log, "playbook9 %s: %s %s fired at the %s: paper long at the next open, stop about %s, Target 1 about %s%s. "
              "NOT passed, paper only" % (name, "rules" if len(took) > 1 else "rule", " and ".join(took), at,
                                          _px(c - R), _px(c + R), " (found late)" if dec["late"] else ""))


def _readings(fx, i):
    """The rule's readings at bar i, for the page: how far the market is from a trigger."""
    atr = _f(fx["atr1h"][i])
    c, low16, cref = _f(fx["c"][i]), _f(fx["low16"][i]), _f(fx["cref"][i])
    fset = int(fx["fund_set_ms"][i])
    return {"last_close_utc": _utc(int(fx["close_ms"][i])), "close": c, "atr_1h": _f(atr, 4),
            "low_4h": low16, "low_30d": _f(fx["lowN"][i]), "fresh_30d_low": bool(fx["is_low"][i]),
            "drop_from_week_ago_pct": None if low16 is None or not cref else _f((low16 / cref - 1.0) * 100.0, 2),
            "drop_enough": bool(fx["drop"][i]),
            "rebound_atr": None if not atr or c is None or low16 is None else _f((c - low16) / atr, 2),
            "rebound_enough": bool(fx["bounce"][i]), "all_three": bool(fx["trig"][i]),
            "funding_rate": _f(fx["fund"][i]), "funding_set_utc": _utc(fset) if fset >= 0 else None,
            "funding_fresh": bool(fx["fund_fresh"][i])}


def replay(asset, df, fund, start_ms, max_age_ms=FUND_MAX_AGE_MS, now_of=None, log=None):
    """The book's own bar-by-bar code over a whole frame in one go, from a flat state: every bar that closes after
    start_ms goes through _advance, exactly as the live step feeds it. For tests and the parity check with the
    research script; nothing is read from or written to disk. now_of(close_ms) -> the clock of the step that saw the
    bar (None: no clock, nothing is marked late). -> the state."""
    st = new_state(int(start_ms))
    fx = features(df, fund, max_age_ms=max_age_ms)
    i0 = int(np.searchsorted(fx["close_ms"], int(start_ms), side="right"))
    A = fx["A"]
    slots = [st["books"][b][asset] for b in RULES]
    for i in range(i0, len(A)):
        if not A[i] and all(s["pending"] is None and s["open"] is None for s in slots):
            continue                                              # flat and no signal: nothing can happen in this bar
        _advance(st, asset, fx, i, None if now_of is None else now_of(int(fx["close_ms"][i])), log)
    if len(A):
        st["last_open_ms"][asset] = int(fx["open_ms"][-1])
    return st


# ---------------------------------------------------------------- the retest levels (a notice only; no trade)
def levels_of(fx, n=None):
    """H116's level machine (research/h116_retest_capitulation_low.machine: the level, dead, armed, first touch), and
    the first low under the level from the first touch on, with bars [0, n) only. Stateless: every level comes from
    the bars, and each step at a bar reads bars up to it, so what is found on a prefix stays as it is when bars are
    appended. For each rule A onset k: L = the lowest low of bars k-15..k, b = the first of them with that low; no
    level when one at the same L was made in the 30 days before; e = the last bar that opens within 30 days of bar k;
    dead when a bar after b has a low under L before, or in, the arming bar; armed at the first bar after b with a high
    >= 1.05 x L; first touch at the first bar after both the arming bar and k with a low <= 1.015 x L; broken at the
    first bar from the first touch on with a low under L (all up to e).
    -> list of {"k", "L", "b", "e", "a", "u", "f", "s", "state"} (bar indices or None; state waiting / dead / armed /
    touched / broken)."""
    open_ms, h, l = fx["open_ms"], fx["h"], fx["l"]
    n = len(l) if n is None else int(n)
    life = LEVEL_LIFE_DAYS * 86400000
    out = []
    for k in np.flatnonzero(fx["A"][:n]):
        k = int(k)
        L = float(fx["low16"][k])
        b = k - (LOOK - 1) + int(np.argmin(l[k - (LOOK - 1):k + 1]))     # the first of the 16 bars with that low
        if any(lv["L"] == L and open_ms[k] - open_ms[lv["k"]] <= life for lv in out[-40:]):
            continue                                              # the same low again: one level (the script's -40 too)
        e = min(int(np.searchsorted(open_ms, open_ms[k] + life, side="right")) - 1, n - 1)
        lv = {"k": k, "L": L, "b": b, "e": e, "a": None, "u": None, "f": None, "s": None, "state": "waiting"}
        out.append(lv)
        arm = np.flatnonzero(h[b + 1:e + 1] >= (1.0 + LEVEL_ARM) * L)
        und = np.flatnonzero(l[b + 1:e + 1] < L)
        a = b + 1 + int(arm[0]) if len(arm) else None
        u = b + 1 + int(und[0]) if len(und) else None
        if u is not None and (a is None or u <= a):
            lv["state"], lv["u"] = "dead", u                      # undercut before (or in) the arming bar
            continue
        if a is None:
            continue
        lv["a"], lv["state"] = a, "armed"
        g = max(a, k) + 1
        touch = np.flatnonzero(l[g:e + 1] <= (1.0 + LEVEL_ZONE) * L)
        if not len(touch):
            continue
        f = g + int(touch[0])
        lv["f"], lv["state"] = f, "touched"
        under = np.flatnonzero(l[f:e + 1] < L)
        if len(under):
            lv["s"], lv["state"] = f + int(under[0]), "broken"
    return out


def level_rows(asset, fx, levels):
    """The levels whose trigger bar opened in the last LEVEL_LIFE_DAYS + LEVEL_KEEP_DAYS days, as the state keeps
    them. Times are epoch ms of a bar's OPEN, except trigger_close_ms and live_until_ms (closes)."""
    open_ms, l = fx["open_ms"], fx["l"]
    n = len(l)
    if not n:
        return []
    last = int(open_ms[n - 1])
    life = LEVEL_LIFE_DAYS * 86400000
    rows = []
    for lv in levels:
        k_open = int(open_ms[lv["k"]])
        if k_open < last - life - LEVEL_KEEP_DAYS * 86400000:
            continue
        at = lambda i: None if i is None else int(open_ms[i])      # noqa: E731
        L = lv["L"]
        rows.append({"id": "%s|%d" % (asset, k_open + BAR_MS), "asset": asset, "L": L,
                     "zone_top": (1.0 + LEVEL_ZONE) * L, "arm_price": (1.0 + LEVEL_ARM) * L, "state": lv["state"],
                     "live": bool(last < k_open + life), "low_open_ms": at(lv["b"]), "trigger_close_ms": k_open + BAR_MS,
                     "live_until_ms": k_open + life + BAR_MS, "armed_open_ms": at(lv["a"]), "dead_open_ms": at(lv["u"]),
                     "touch_open_ms": at(lv["f"]), "broken_open_ms": at(lv["s"]),
                     "new_low": None if lv["s"] is None else _f(np.min(l[lv["s"]:n]))})
    return rows


def _level_frame(asset, bars, now):
    """The closed bars the levels are recomputed from: the last LEVEL_TAIL_BARS of them."""
    if bars is None:
        df = tail_bars(asset, LEVEL_TAIL_BARS + 8)
    else:
        df = bars.get(asset)
        if df is None:
            return None
    df = df[data.to_ms(df.index) + BAR_MS <= int(now)]
    return df.iloc[-LEVEL_TAIL_BARS:]


def _step_levels(st, asset, bars, now, log=None):
    """Recompute `asset`'s levels when a bar has closed since they were last computed. Writes only st["zone"][asset].
    -> True when it changed. Raises on anything it cannot read (the caller logs one line; the trades are not touched)."""
    zone = st.get("zone") if isinstance(st.get("zone"), dict) else {}
    old = zone.get(asset) if isinstance(zone.get(asset), dict) else {}
    seen = old.get("as_of_open_ms")
    if isinstance(seen, int) and seen >= (int(now) // BAR_MS) * BAR_MS - BAR_MS:
        return False                                              # by the clock no bar has closed since: nothing is read
    df = _level_frame(asset, bars, now)
    if df is None or not len(df):
        return False
    fx = features(df, None)
    i = len(df) - 1
    last = int(fx["open_ms"][i])
    if seen == last:
        return False                                              # the bar file is behind the clock: nothing new
    rows = level_rows(asset, fx, levels_of(fx))
    block = {"as_of_open_ms": last, "as_of_utc": _utc(last + BAR_MS), "bars": int(len(df)), "close": _f(fx["c"][i]),
             "atr_1h": _f(fx["atr1h"][i]), "low_4h": _f(fx["low16"][i]), "low_30d": _f(fx["lowN"][i]),
             "week_ago_close": _f(fx["cref"][i]), "fresh_30d_low": bool(fx["is_low"][i]),
             "drop_enough": bool(fx["drop"][i]), "all_three": bool(fx["trig"][i]), "levels": rows}
    was = dict((r.get("id"), r.get("state")) for r in (old.get("levels") or []) if isinstance(r, dict))
    name = SHORT_NAME.get(asset, asset)
    for r in rows:
        if was.get(r["id"]) != r["state"] and (r["live"] or r["id"] in was):
            _say(log, "playbook9 %s: the %s low of %s UTC is %s (zone up to %s, counts until the %s UTC close). A notice "
                      "only, no trade" % (name, _px(r["L"]), _utc(r["low_open_ms"]), r["state"], _px(r["zone_top"]),
                                          _utc(r["live_until_ms"])))
    zone = dict(zone)
    zone[asset] = block
    st["zone"] = zone
    return True


def page_levels(st):
    """{asset: [the small level rows for the page]} from the state. A block or a row that is not what _step_levels
    writes is left out (it is replaced at that coin's next new bar); never raises."""
    out = {}
    zone = st.get("zone") if isinstance(st.get("zone"), dict) else {}
    for asset in ASSETS:
        blk = zone.get(asset)
        if not isinstance(blk, dict) or not isinstance(blk.get("levels"), list):
            continue
        rows = []
        for r in blk["levels"]:
            try:
                rows.append({"L": r["L"], "low_utc": _utc(r["low_open_ms"]), "made_utc": _utc(r["trigger_close_ms"]),
                             "zone_top": _f(r["zone_top"], 6), "state": r["state"], "live": r["live"],
                             "live_until_utc": _utc(r["live_until_ms"]), "touch_utc": _utc(r["touch_open_ms"]),
                             "broken_utc": _utc(r["broken_open_ms"]), "new_low": r["new_low"],
                             "as_of_utc": blk.get("as_of_utc")})
            except Exception:
                continue
        out[asset] = rows
    return out


# ---------------------------------------------------------------- the rebound signal file (the vault's dry run)
def _iso(ms):
    return None if ms is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) // 1000))


def _sig_id(asset, decided_ms):
    return "%s.%s.rebound" % (asset, time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(int(decided_ms) // 1000)))


def _rule_b(t):
    """Was rule B's condition true at the trigger too (a fresh negative funding rate)? None when it could not be read."""
    f = _f(t.get("funding"))
    if f is None or not t.get("funding_fresh"):
        return None
    return bool(f < 0)


def signal(st, now_ms):
    """The rebound signal file's body from the state: per coin, rule A's trade as none / waiting / open and its last
    closed trade. Pure; never raises on a state that _valid accepts. Times are ISO UTC; `decided_utc` is the close of
    the trigger bar, which is also the open of the bar whose open fills the long."""
    out = {"schema": SIGNAL_SCHEMA, "generated_utc": _iso(now_ms), "book": SIGNAL_BOOK,
           "rule": "H107 rule A: the capitulation-rebound long that b_rebound (H117) takes from a short or flat book",
           "paper_only": True, "passed": False,
           "use": "the VIP vault's DRY RUN only: log what each member would have done; place nothing (owner, 25 Nov 2026)",
           "stale_after_minutes": 30, "markets": {}}
    books = (st.get("books") or {}).get(SIGNAL_BOOK) or {}
    closed = [t for t in st.get("closed") or [] if t.get("book") == SIGNAL_BOOK]
    for asset in ASSETS:
        slot = books.get(asset) or {}
        m = {"state": "none"}
        t = slot.get("open")
        if t is not None:
            m = {"state": "open", "id": _sig_id(asset, t["decided_ms"]), "side": "LONG",
                 "decided_utc": _iso(t["decided_ms"]), "entry_utc": _iso(t["entry_open_ms"]), "entry": _f(t["entry"], 6),
                 "stop": _f(t["stop0"], 6), "stop_now": _f(t["stop"], 6), "target_1": _f(t["t1"], 6),
                 "target_2": _f(t["t2"], 6), "t1_taken": bool(t["t1_taken"]), "t1_utc": _iso(t.get("t1_close_ms")),
                 "time_exit_utc": _iso(int(t["decided_ms"]) + HOLD * BAR_MS), "rule_b_too": _rule_b(t),
                 "late": bool(t.get("late"))}
        elif slot.get("pending") is not None:
            t = slot["pending"]
            R = float(t["r_dist"])
            m = {"state": "waiting", "id": _sig_id(asset, t["decided_ms"]), "side": "LONG",
                 "decided_utc": _iso(t["decided_ms"]), "entry_utc": _iso(t["decided_ms"]),
                 "entry_est": _f(t["close"], 6), "stop_est": _f(t["close"] - R, 6), "target_1_est": _f(t["close"] + R, 6),
                 "target_2_est": _f(t["close"] + 2.0 * R, 6), "stop_distance": _f(R, 6),
                 "time_exit_utc": _iso(int(t["decided_ms"]) + HOLD * BAR_MS), "rule_b_too": _rule_b(t),
                 "late": bool(t.get("late")),
                 "note": "the long fills at the open of the bar that opens at entry_utc; the levels are set from that "
                         "open: stop = entry - stop_distance, Target 1 = entry + stop_distance, Target 2 = entry + 2 x"}
        last = [c for c in closed if c.get("asset") == asset]
        if last:
            c = last[-1]
            m["last_closed"] = {"id": _sig_id(asset, c["decided_ms"]), "entry": _f(c["entry"], 6),
                                "exit": _f(c["exit"], 6), "exit_utc": _iso(c["exit_close_ms"]), "why_out": c["why_out"],
                                "r": _f(c["r"], 4)}
        out["markets"][asset] = m
    return out


def write_signal(st, now_ms, path=None):
    """Write the signal file atomically (a reader never sees half a file)."""
    path = path or SIGNAL_PATH
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(signal(st, now_ms), fh, allow_nan=False, sort_keys=True, indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------- bars
def tail_bars(asset, nrows, path=None):
    """The last `nrows` bars of the engine's 15m file, as data.load gives them, read from the end of the file."""
    p = path or data.path_for(asset)
    nrows = max(1, int(nrows))
    with open(p, "rb") as fh:
        header = fh.readline().decode("utf-8").strip().split(",")
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        want = max(nrows * 96, 65536)
        while True:
            start = max(0, size - want)
            fh.seek(start)
            lines = fh.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]                                 # a partial first line
            lines = [ln for ln in lines if ln.strip() and not ln.startswith(b"ts_ms")]
            if len(lines) >= nrows or start == 0:
                break
            want *= 2
    df = pd.read_csv(io.BytesIO(b"\n".join(lines[-nrows:])), header=None, names=header)
    df.index = pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)
    df.index.name = "open_time"
    if "taker_buy" not in df.columns:
        df["taker_buy"] = np.nan
    return df[data.COLS].astype(float)


def _frame(asset, bars, now, n_new):
    """The closed bars the step may read: the tail that the readings need plus the bars not yet seen."""
    want = TAIL_BARS + int(n_new) + 8
    if bars is None:
        df = tail_bars(asset, want)
    else:
        df = bars.get(asset)
        if df is None:
            return None
    df = df[data.to_ms(df.index) + BAR_MS <= int(now)]
    return df.iloc[-want:]


# ---------------------------------------------------------------- live interface
def _step_asset(st, asset, bars, funding, now, log):
    """-> True when the state changed. Raises on anything it cannot read (the caller logs one line)."""
    last = st["last_open_ms"].get(asset)
    if last is None:                                              # first sight of this coin: nothing before the start
        last = int(st["started_ms"]) - BAR_MS
        st["last_open_ms"][asset] = last
    n_new = max(0, (int(now) - int(last)) // BAR_MS)
    df = _frame(asset, bars, now, n_new)
    if df is None or not len(df):
        return False
    open_ms = data.to_ms(df.index)
    i0 = int(np.searchsorted(open_ms, int(last), side="right"))
    if i0 >= len(df):
        return False                                              # no bar has closed since the last step
    fund = (funding or {}).get(asset) if funding is not None else None
    if fund is None and funding is None:
        fund = data.load_funding(asset)
    fx = features(df, fund)
    for i in range(i0, len(df)):
        _advance(st, asset, fx, i, now, log)
    st["last_open_ms"][asset] = int(open_ms[-1])
    st["readings"][asset] = _readings(fx, len(df) - 1)
    return True


def step(bars=None, now_ms=None, funding=None, state_path=None, log=print, start_ms=None, signal_path=None):
    """bars: {asset: 15m frame from engine15.data.load} (None reads the tails of the engine's files); funding:
    {asset: Series of rates keyed by set time} (None reads data/<asset>_funding.csv); state_path: default
    data/capit_long_state.json; start_ms: only for a state that does not exist yet (tests): the close after which bars
    count; by default the last 15m close before this step's clock, never before REGISTERED; signal_path: where the
    rebound signal file goes (the live step, state_path None, writes SIGNAL_PATH; a caller that names a state_path
    writes none unless it names signal_path too).
    -> rows (docs/PLAYBOOK_INTERFACE.md). Never raises."""
    t0 = time.perf_counter()
    rows = []
    try:
        path = state_path or STATE_PATH
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        st, why = load_state(path, log=log)
        changed = False
        if st is None:
            # the last close this step's clock has passed: only a bar that closes AFTER it can decide, whatever the
            # bar files hold (a file that is behind cannot bring an older bar into the record later)
            started = max(reg_ms(), (now // BAR_MS) * BAR_MS) if start_ms is None else int(start_ms)
            st = new_state(started)
            st["state_note"] = "started flat at %s UTC (%s state file)" % (_utc(started), why)
            changed = True
        for asset in ASSETS:
            trial = copy.deepcopy(st)                             # a coin that fails leaves no half-made step behind
            try:
                if _step_asset(trial, asset, bars, funding, now, log):
                    st, changed = trial, True
            except Exception as e:
                _say(log, "playbook9 %s failed: %r" % (asset, e))
        for asset in ASSETS:                                      # the retest levels (a notice only): after the trades,
            try:                                                  # on their own, so nothing here can reach a trade
                changed = _step_levels(st, asset, bars, now, log) or changed
            except Exception as e:
                _say(log, "playbook9 %s: the retest levels were not updated (%r); the trades are not affected" % (asset, e))
        if changed:
            try:
                save_state(st, path)
            except Exception as e:
                _say(log, "playbook9: the state could not be written (%r): this step is redone at the next one" % (e,))
        if signal_path or not state_path:
            try:
                write_signal(st, now, signal_path or SIGNAL_PATH)
            except Exception as e:
                _say(log, "playbook9: the rebound signal file was not written (%r); the trades are not affected" % (e,))
        rows = rows_of(st)
        LAST_RUN.update({"started_utc": st.get("started_utc"), "skipped": copy.deepcopy(st.get("skipped")),
                         "readings": copy.deepcopy(st.get("readings")), "state_note": st.get("state_note"),
                         "levels": page_levels(st)})
    except Exception as e:
        _say(log, "playbook9 failed: %r" % (e,))
    LAST_RUN.update({"seconds": round(time.perf_counter() - t0, 4), "utc": _utc(int(time.time() * 1000))})
    return rows


# ---------------------------------------------------------------- rows and words
def _levels(t):
    return "stop %s, Target 1 %s, Target 2 %s" % (_px(t["stop0"]), _px(t["t1"]), _px(t["t2"]))


def _row(t, status):
    book, asset = t["book"], t["asset"]
    name, rule = SHORT_NAME.get(asset, asset), t["rule"]
    head = "Capitulation long, rule %s, %s: decided at the %s UTC close (%s; the 4-hour low was %.1f%% under the " \
           "close a week earlier, the rebound %.1f ATR)" % (rule, name, t["decided_utc"], _px(t["close"]),
                                                             abs(t["drop_pct"]), t["bounce_atr"])
    tail = " Paper, forward, NOT passed."
    row = {"book": book, "asset": asset, "status": status, "side": 1, "rule": rule, "setup_utc": t["decided_utc"],
           "entry_utc": t["decided_utc"], "entry": None, "stop": None, "target_1": None, "target_2": None,
           "exit_utc": None, "exit": None, "why_out": "OPEN", "r": None, "pnl_usd": None, "fees_usd": None,
           "pnl_pct": None, "risk_pct": _f(100.0 * t["r_dist"] / t["close"], 3), "funding": t.get("funding"),
           "funding_set_utc": _utc(t.get("funding_set_ms")), "late": bool(t.get("late")),
           "time_exit_utc": _utc(t["decided_ms"] + HOLD * BAR_MS)}
    if status == "WAITING":
        row["text"] = "%s. Long at the next bar's open; stop about %s, Target 1 about %s.%s" % (
            head, _px(t["close"] - t["r_dist"]), _px(t["close"] + t["r_dist"]), tail)
        return row
    row.update({"entry": _f(t["entry"], 6), "stop": _f(t["stop0"], 6), "target_1": _f(t["t1"], 6),
                "target_2": _f(t["t2"], 6), "t1_taken": bool(t["t1_taken"]), "bars_held": int(t["bars"])})
    if status == "OPEN":
        pct = t["r_mark"] * t["r_dist"] / t["entry"]
        row.update({"stop_now": _f(t["stop"], 6), "r": _f(t["r_mark"], 4), "pnl_usd": _f(STAKE * pct, 2),
                    "pnl_pct": _f(100.0 * pct, 3), "fees_usd": _f(STAKE * t["fees"] / t["entry"], 2),
                    "mark": _f(t["mark"], 6)})
        row["text"] = "%s. Long from %s, %s%s. Open, marked at %s: %+.2fR so far; it goes out by the %s UTC close.%s" % (
            head, _px(t["entry"]), _levels(t), "; Target 1 taken, half is out and the stop is at the entry"
            if t["t1_taken"] else "", _px(t["mark"]), t["r_mark"], row["time_exit_utc"], tail)
        return row
    row.update({"exit_utc": _utc(t["exit_close_ms"]), "exit": _f(t["exit"], 6), "why_out": t["why_out"],
                "r": _f(t["r"], 4), "pnl_usd": _f(t["pnl_usd"], 2), "pnl_pct": _f(100.0 * t["pct"], 3),
                "fees_usd": _f(t["fees_usd"], 2)})
    row["text"] = "%s. Long from %s, %s. Closed at the %s UTC close (%s) at %s: %+.2fR, %+.2f USD after %.2f USD " \
                  "fees.%s" % (head, _px(t["entry"]), _levels(t), row["exit_utc"], HOW_WORDS[t["how"]], _px(t["exit"]),
                               t["r"], t["pnl_usd"], t["fees_usd"], tail)
    return row


def rows_of(st):
    """The state as rows: every closed trade, then what is open or waiting."""
    rows = [_row(t, "CLOSED") for t in st.get("closed", [])]
    for book in RULES:
        for asset in ASSETS:
            slot = st["books"][book][asset]
            if slot["open"] is not None:
                rows.append(_row(slot["open"], "OPEN"))
            elif slot["pending"] is not None:
                rows.append(_row(slot["pending"], "WAITING"))
    return rows


def _totals(closed):
    n = len(closed)
    if not n:
        return {"trades": 0, "won": 0, "win_rate_pct": None, "avg_r": None, "sum_r": 0.0, "net_usd": 0.0, "fees_usd": 0.0}
    won = sum(1 for r in closed if r["pnl_usd"] > 0)
    return {"trades": n, "won": won, "win_rate_pct": round(100.0 * won / n, 1),
            "avg_r": round(sum(r["r"] for r in closed) / n, 3), "sum_r": round(sum(r["r"] for r in closed), 3),
            "net_usd": round(sum(r["pnl_usd"] for r in closed), 2), "fees_usd": round(sum(r["fees_usd"] for r in closed), 2)}


def rule_text(book):
    b = ("Rule B: rule A's signal AND the last funding rate is below zero (shorts are paying); a funding reading older "
         "than 9 hours is stale and rule B does not fire on it. " if RULES[book] == "B" else "")
    return ("%s Rule A, at a 15m close: a fresh 30-day low in the last 4 hours, that low at least 10%% under the close a "
            "week earlier, and the close at least 2 x ATR(1h) above that low (the first bar this is true). %sThe trade: "
            "long at the next bar's open; stop 3 x ATR(1h) below; half out at Target 1 (+1R), then the stop at the "
            "entry; the rest out at Target 2 (+2R) or at the close 48 hours after the signal. One trade at a time per "
            "coin. $10,000 per trade, 1x, fee 0.10%% a side. %s BTC and ETH, forward only, from the first step after "
            "the deploy (never before %s UTC)." % (NOT_PASSED, b, HISTORY, REGISTERED))


PASS_RULE = ("First read at 30 closed forward trades (BTC and ETH together), second at 60, by the scoreboard's 90% range "
             "per trade; no decision between them. On history rule A made about 20 trades a year and rule B about 5, so "
             "rule A's first read is about a year and a half away and rule B's about six years. 'Ahead' at both reads "
             "only opens a discussion with the owner about a next test; it never by itself reaches the vault, the "
             "Setups book or a main book, and the book stays NOT passed.")


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1",
                                              "target_2", "r", "pnl_usd", "time_exit_utc", "text"))
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
                     "totals": _totals(closed), "by_asset": per,
                     "started_utc": LAST_RUN.get("started_utc"), "coins": copy.deepcopy(LAST_RUN.get("readings") or {}),
                     "signals_not_taken_while_in_a_trade": copy.deepcopy((LAST_RUN.get("skipped") or {}).get(book) or {}),
                     "levels": copy.deepcopy(LAST_RUN.get("levels") or {}), "levels_note": LEVELS_NOTE,
                     "pass_rule": PASS_RULE, "note": NOT_PASSED + " " + HISTORY,
                     "step_seconds": LAST_RUN.get("seconds")}
    return out


def main(argv=None):
    """Prints the book as its state file holds it. Read only: it does not step and writes nothing."""
    st, why = load_state_readonly()
    if st is None:
        print("no usable state file (%s): the book has not run here" % why)
        return
    print("record started %s UTC" % st.get("started_utc"))
    rows = rows_of(st)
    for r in rows:
        print(r["text"])
    for book in BOOKS:
        print(book, _totals([r for r in rows if r["book"] == book and r["status"] == "CLOSED"]))
    for a, rd in sorted((st.get("readings") or {}).items()):
        print("  ", a, rd)
    for a, rows in sorted(page_levels(st).items()):
        for r in rows:
            print("   retest level (a notice, no trade)", a, r)


def load_state_readonly(path=None):
    """The state for a reader that must change nothing (main): never moves a file aside."""
    path = path or STATE_PATH
    try:
        with io.open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except OSError:
        return None, "missing"
    except ValueError:
        return None, "unreadable"
    return (st, None) if _valid(st) else (None, "not this book's state")


if __name__ == "__main__":
    main()
