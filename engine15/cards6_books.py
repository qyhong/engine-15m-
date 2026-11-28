# -*- coding: utf-8 -*-
"""cards6_books -- H122's paper books, registered as shadow MINDS (shadows.MINDS). PAPER ONLY. NOT passed.

Each Book below is one MINDS entry: shadows.advance calls `advance` after every challenger and follower, inside a
try/except, and the book writes only its own state (sst["books"][NAME], sst["late_starts"][NAME], sst["cards6"]).
The card votes are computed once per group step and shared by the books of that step (a small cache).

    c6_c1, c6_c2, c6_c5   one book per card (cards6.card_book), advanced first so the kill rules are current
    m_cards6              the Setups rule ({"targets": True, "early": True}) on the mind odds; yardstick b_targets
    m_cards6_nf           the same with idle_max out of reach;                            yardstick b_no_forced
Markets: XAUUSD, XAGUSD (metals) and WTI, BRENT (energy) only; other groups return at once. Each book starts flat at
its first live bar. The vault, the Setups page and the signals never read these books.
"""
import time

import numpy as np
import pandas as pd

from . import cards6

_CACHE = {}                                                      # (group, n, last ms) -> {asset: {card: votes}, ...}
C2_BACK, C5_BACK_WEEKS = 4000, 106                               # rows of history each card needs before r0


def _state6(sst):
    return sst.setdefault("cards6", {"muted": {}, "r": {}, "speak": {}, "stopped": {}})


def _group_votes(prep, group, assets, r0, n, log):
    """{asset: {card: votes for rows r0 .. n-1}} for the cards6 markets of this group (cached for the step)."""
    times = prep["times"]
    ms_all = cards6._ms(times)
    key = (group, int(n), int(ms_all[n - 1]), int(r0))
    if key in _CACHE:
        return _CACHE[key]
    out = {}
    for a in assets:
        try:
            px, ev = prep["px"][a], prep["ev"][a]
            ms = ms_all[:n]
            o, c = np.asarray(px["open"][:n], float), np.asarray(px["close"][:n], float)
            atr = np.asarray(ev["atr1h"].values[:n], float)
            rel = cards6.release_times(a, until_ms=int(ms[-1]) + cards6.BAR_MS)
            v1 = cards6.c1_votes(ms, o, c, atr, rel, r0, n)
            s2 = max(r0 - C2_BACK, 0)                            # C2 and C5 on a slice of history: same result, faster
            lead = cards6._leader_close(cards6.C2_LEADER[a], ms[s2:])
            v2 = cards6.c2_votes(a, ms[s2:], o[s2:], c[s2:], lead, r0 - s2, n - s2)
            s5 = int(np.searchsorted(ms, ms[r0] - C5_BACK_WEEKS * cards6.WEEK_MS))
            p5 = cards6.c5_prepare(a, ms[s5:], c[s5:])
            v5 = cards6.c5_votes(p5, r0 - s5, n - s5)
            out[a] = {"c1": v1, "c2": v2, "c5": v5, "_lead_missing": int(np.isnan(lead[r0 - s2:]).sum())}
        except Exception as e:
            (log or (lambda *_: None))("%s: cards6 votes failed on %s: %r" % (group, a, e))
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def _start(books, a, times_ms, lo):
    last = ((books.get(a) or {}).get("mind") or {}).get("last_ms") or (books.get(a) or {}).get("last_ms")
    return int(lo) if last is None else int(np.searchsorted(times_ms, int(last), side="right"))


class Book(object):
    """One H122 paper book. kind: "card" (c6_<card>) or "mind" (m_cards6, m_cards6_nf)."""

    def __init__(self, name, kind, card=None, cfg=None, yard=None, title=None):
        self.NAME, self.kind, self.card, self.cfg_over, self.yard = name, kind, card, dict(cfg or {}), yard
        self.LABEL, self.HYPOTHESIS = cards6.LABEL, cards6.HYPOTHESIS
        self.TITLE = title

    # ---- the step
    def advance(self, prep, group, assets, lo, n, sst, cfg=None, mains_before=None, log=None):
        from . import data, shadows
        from .config import CFG
        mine = [a for a in assets if a in cards6.ASSETS]
        if not mine:
            return {}
        t0 = time.perf_counter()
        say = log or (lambda *_: None)
        times = prep["times"]
        tms = data.to_ms(times)
        books = sst.setdefault("books", {}).setdefault(self.NAME, {})
        s6 = _state6(sst)
        if self.kind == "mind" and s6["stopped"].get(self.NAME):
            return {}                                             # M1: stopped; the book stays as it stood
        start = dict((a, _start(books, a, tms, lo)) for a in mine)
        todo = [a for a in mine if start[a] < n]
        if not todo:
            return {}
        r0 = min(start[a] for a in todo)
        V = _group_votes(prep, group, todo, r0, n, say)
        closed, said = {}, []
        for a in todo:
            if a not in V:
                continue
            try:
                acfg = shadows.asset_cfg(a, dict(cfg or prep["cfg"], **self.cfg_over))
                old = books.get(a)
                if old is None:                                   # its first live bar
                    yb = ((sst.get("books") or {}).get(self.yard or "b_targets") or {}).get(a) or {}
                    sst.setdefault("late_starts", {}).setdefault(self.NAME, {})[a] = {
                        "ms": int(tms[start[a]]), "utc": str(times[start[a]] + pd.Timedelta(milliseconds=CFG["bar_ms"]))[:16],
                        "main_eq": float(yb.get("equity_marked", yb.get("eq", cards6.START_EQUITY))),
                        "yard": self.yard or "b_targets",
                        "yard_r_sum": float(((yb.get("stats") or {}).get("r_sum")) or 0.0)}
                off = start[a] - r0
                if self.kind == "card":
                    v = V[a][self.card][off:]
                    px = prep["px"][a]
                    unit = (prep["cfg"]["barrier_atr"] * prep["ev"][a]["atr1h"]).values
                    st, rows = cards6.card_book(old, tms, px["open"], px["high"], px["low"], px["close"], unit, v,
                                                start[a], n, acfg)
                    books[a] = st
                    sp = s6["speak"].setdefault(self.card, [0, 0, 0])
                    sp[0] += int(np.count_nonzero(v))
                    sp[1] += len(v)
                    if self.card == "c2":
                        sp[2] += int(V[a].get("_lead_missing", 0))
                    if rows:
                        df = pd.DataFrame(rows, columns=shadows.TRADE_COLS)
                        closed[(self.NAME, a)] = df
                        s6["r"].setdefault(self.card, []).extend(float(x) for x in df["r_mult"].tolist())
                    said.append("%s %s" % (a, {1: "LONG", -1: "SHORT"}.get(st["pos"], "FLAT")))
                else:
                    muted = tuple(k for k, m in s6["muted"].items() if m)
                    inp = shadows.book_inputs(prep, a)
                    full = np.full((len(inp["px"]["close"]), 3), np.nan)
                    cv = dict((k, V[a][k][off:]) for k in cards6.CARDS)
                    full[start[a]:n] = cards6.mind_odds(np.asarray(inp["odds"][start[a]:n]), cv, muted)
                    aux = shadows.aux_from_ev(prep["ev"][a], inp["px"])
                    tgt = aux["targets"]
                    b = shadows.run(inp["px"], full, inp["shock"], inp["tide"], inp["unit"], acfg, start[a], n,
                                    state=old, bias=inp["bias"], guard=inp["guard"],
                                    rule={"targets": True, "early": True}, aux=aux, times_ms=tms,
                                    row_of=lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))
                    st = b["state"]
                    st["mind"] = {"last_ms": int(tms[n - 1]),
                                  "cards_now": dict((k, float(cv[k][-1])) for k in cards6.CARDS), "muted": list(muted)}
                    books[a] = st
                    if len(b["trades"]):
                        closed[(self.NAME, a)] = b["trades"]
                    said.append("%s %s" % (a, {1: "LONG", -1: "SHORT"}.get(st.get("pos", 0), "FLAT")))
            except Exception as e:
                say("%s: %s failed on %s: %r" % (group, self.NAME, a, e))
        self._kills(sst)
        say("%s: %s (%s, paper) %.3fs: %s" % (group, self.NAME, cards6.HYPOTHESIS, time.perf_counter() - t0, ", ".join(said)))
        return closed

    def _kills(self, sst):
        s6 = _state6(sst)
        if self.kind == "card":
            sp = s6["speak"].get(self.card) or [0, 0, 0]
            share = sp[0] / float(sp[1]) if sp[1] >= 400 else None          # read once there are 100 bars a market
            muted, why = cards6.kill_state(s6["r"].get(self.card) or [], share, self.card)
            if not muted and self.card == "c2" and sp[1] >= 400 and sp[2] / float(sp[1]) > 0.10:
                muted, why = True, "K3: the leader's bars missing on %.0f%% of open bars" % (100 * sp[2] / float(sp[1]))
            if muted and not s6["muted"].get(self.card):
                s6["muted"][self.card] = why
        else:
            late = ((sst.get("late_starts") or {}).get(self.NAME)) or {}
            mine = (sst.get("books") or {}).get(self.NAME) or {}
            yard = (sst.get("books") or {}).get(self.yard) or {}
            d = 0.0
            for a, ls in late.items():
                m, y = mine.get(a) or {}, yard.get(a) or {}
                d += float((m.get("stats") or {}).get("r_sum") or 0.0) - (
                    float((y.get("stats") or {}).get("r_sum") or 0.0) - float(ls.get("yard_r_sum") or 0.0))
            if d <= -cards6.M1_R:
                s6["stopped"][self.NAME] = "M1: behind %s by %.1fR" % (self.yard, -d)

    def view_extra(self, st):
        m = (st or {}).get("mind") or {}
        out = {"label": cards6.LABEL}
        if m:
            out.update(cards_now=m.get("cards_now"), muted_cards=m.get("muted"))
        return out


BOOKS = [Book("c6_%s" % k, "card", card=k, yard="b_targets",
              title="Card book %s (H122 commodity card %s). NOT passed, paper only" % (k.upper(), k.upper()))
         for k in cards6.CARDS]
BOOKS += [Book("m_cards6", "mind", yard="b_targets",
               title="Cards6 mind (H122): the Setups rule with the commodity cards. NOT passed, paper only"),
          Book("m_cards6_nf", "mind", cfg={"idle_max": 10 ** 9}, yard="b_no_forced",
               title="Cards6 mind without forced entries (H122). NOT passed, paper only")]
