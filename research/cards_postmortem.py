# -*- coding: utf-8 -*-
"""cards_postmortem -- the decision cards on BTC and ETH, live sessions only: what each card leaned and what price did
next. DESCRIPTIVE (owner, 26 Nov 2026: "How does 61 decision cards so far work for btc and eth. Can we do a post
mortem"). Not a hypothesis and not a test: it describes about two weeks of one falling market. The 24-hour outcomes of
neighbouring sessions overlap almost completely, so the row counts flatter the sample: the honest count is DAYS.

Reads only the live journal (journal/<day>.jsonl: one line per coin per 15-minute close; each line carries every card
with its `lean` in points, positive = up, its `trust` and its `pull_pts` on the engine's Lead). Changes nothing.

    python research/cards_postmortem.py [journal_dir] > out.json        (on the box: /data/mind15/journal)

Per coin and per card, over the sessions where the card leaned (lean != 0) and the outcome is known:
    n, days          sessions, and UTC days they fall on
    up_pct           the share of those sessions it leaned up
    hit_4h / hit_24h the share where the price move over the next 4 h / 24 h had the sign of the lean
    hit_up / hit_dn  the 24 h hit rate of its up leans and of its down leans apart (a card that only ever leaned down
                     in a falling market is right without knowing anything)
    ic_4h / ic_24h   rank correlation of the lean with the next move (-1 .. +1): does a stronger lean go with a bigger
                     move its way; unlike the hit rate it gains nothing from leaning with the drift all the time
    days_right       days on which the card's leans, on average over that day, pointed the way of the next 24 h
    trust, pull      its mean trust and mean |pull| on the Lead (how much the engine listened)
The same numbers for the engine's own Lead (edge_pts) are the yardstick, and `drift` is what "always down" scored.
"""
import glob
import json
import os
import sys
from collections import defaultdict

COINS = ("BTCUSDT", "ETHUSDT")
BAR_S = 900
H4, H24 = 16, 96


def _t(s):
    import calendar
    import time
    return calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M"))


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0
        i = j + 1
    return r


def _corr(a, b):
    n = len(a)
    if n < 30:
        return None
    ra, rb = _rank(a), _rank(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((x - mb) ** 2 for x in rb)
    if va <= 0 or vb <= 0:
        return None
    return round(sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (va * vb) ** 0.5, 3)


def _pct(k, n):
    return None if not n else round(100.0 * k / n, 1)


def _stats(rows):
    """rows: [(day, lean, ret4 or None, ret24 or None, trust, pull)] with lean != 0."""
    r24 = [x for x in rows if x[3] is not None]
    r4 = [x for x in rows if x[2] is not None]
    n = len(r24)
    up = [x for x in r24 if x[1] > 0]
    dn = [x for x in r24 if x[1] < 0]
    hit = lambda xs, k: sum(1 for x in xs if x[k] * x[1] > 0)                    # noqa: E731
    byday = defaultdict(list)
    for x in r24:
        byday[x[0]].append((1 if x[1] > 0 else -1) * x[3])
    days_right = sum(1 for v in byday.values() if sum(v) / len(v) > 0)
    return {"n": n, "days": len(byday), "up_pct": _pct(len(up), n),
            "hit_4h": _pct(hit(r4, 2), len(r4)), "hit_24h": _pct(hit(r24, 3), n),
            "hit_up": _pct(hit(up, 3), len(up)), "n_up": len(up), "hit_dn": _pct(hit(dn, 3), len(dn)), "n_dn": len(dn),
            "ic_4h": _corr([x[1] for x in r4], [x[2] for x in r4]),
            "ic_24h": _corr([x[1] for x in r24], [x[3] for x in r24]),
            "days_right": days_right,
            "trust": round(sum(x[4] for x in rows) / len(rows), 3) if rows else None,
            "pull": round(sum(abs(x[5]) for x in rows) / len(rows), 2) if rows else None}


def main(jdir):
    px = dict((c, {}) for c in COINS)                           # coin -> {session time: price}
    sess = dict((c, []) for c in COINS)                         # coin -> [(t, day, edge, action, {card: (lean, trust, pull)})]
    files = sorted(glob.glob(os.path.join(jdir, "20??-??-??.jsonl")))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                coin = next((c for c in COINS if '"asset": "%s"' % c in line[:200]), None)
                if coin is None:
                    continue
                try:
                    e = json.loads(line)
                    t, p = _t(e["time"]), float(e["price"])
                except (ValueError, KeyError, TypeError):
                    continue
                cards = {}
                for c in e.get("cards") or []:
                    try:
                        cards[c["card"]] = (float(c.get("lean") or 0.0), float(c.get("trust") or 0.0),
                                            float(c.get("pull_pts") or 0.0))
                    except (TypeError, ValueError, KeyError):
                        continue
                px[coin][t] = p
                sess[coin].append((t, e["time"][:10], e.get("edge_pts"), e.get("action"), cards))
    out = {"note": "Descriptive. Live sessions only. Outcomes overlap: count days, not sessions.",
           "files": [os.path.basename(f) for f in files], "coins": {}}
    for coin in COINS:
        seen, rows_by, edge_rows, drift, last = set(), defaultdict(list), [], [], None
        names_last = []
        for t, day, edge, _action, cards in sorted(sess[coin], key=lambda x: x[0]):
            if t in seen:                                        # a session journalled twice (a restart): once
                continue
            seen.add(t)
            p0 = px[coin][t]
            p4, p24 = px[coin].get(t + H4 * BAR_S), px[coin].get(t + H24 * BAR_S)
            r4 = None if p4 is None else (p4 / p0 - 1.0) * 100.0
            r24 = None if p24 is None else (p24 / p0 - 1.0) * 100.0
            if r24 is not None:
                drift.append(r24)
            if isinstance(edge, (int, float)) and edge != 0:
                edge_rows.append((day, float(edge), r4, r24, 1.0, float(edge)))
            for name, (lean, trust, pull) in cards.items():
                if lean != 0:
                    rows_by[name].append((day, lean, r4, r24, trust, pull))
            last, names_last = t, sorted(cards)
        cards_out = dict((name, _stats(rows)) for name, rows in rows_by.items())
        for name in names_last:                                  # a card that never leaned: listed, with nothing
            cards_out.setdefault(name, {"n": 0})
        out["coins"][coin] = {
            "sessions": len(seen), "first": min(seen) if seen else None, "last": last,
            "sessions_with_24h": len(drift),
            "drift": {"down_24h_pct": _pct(sum(1 for x in drift if x < 0), len(drift)),
                      "mean_24h_pct": round(sum(drift) / len(drift), 3) if drift else None},
            "lead": _stats(edge_rows), "cards_now": len(names_last), "cards": cards_out}
    json.dump(out, sys.stdout, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "journal")
