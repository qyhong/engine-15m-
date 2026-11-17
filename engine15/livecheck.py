# -*- coding: utf-8 -*-
"""livecheck -- two read-only look-backs for the Telegram bot: LIVE CALIBRATION and DATA HEALTH. PAPER ONLY.

It only reads what the engine already wrote (journal/<day>.jsonl, data/<asset>_15m.csv, the page's cards) and
returns plain numbers; it writes nothing, fetches nothing and never runs the engine. Standard library only.

CALIBRATION: "when the engine says 60%, does it happen 60% of the time, on live data?"
  A call is the odds one live journal line states (odds.up / odds.down / odds.neither at a 15-minute close).
  It is graded by the engine's OWN rule, labels.triple_barrier: a barrier barrier_atr x ATR14(1h) above and below
  the next bar's open; UP or DOWN is the side touched first within the horizon (96 closes; 26 for the S&P),
  NEITHER if none or both in one bar. The journal keeps, per close, only the COUNT of earlier calls graded there
  (graded_now: calls / right / wrong / neither), not which call got which grade, and it holds no highs or lows.
  So each call is re-graded here with that same rule on the engine's own bar file, and the result is checked
  close by close against graded_now. A market whose bars cannot be read, or whose re-grade does not agree with the
  engine's counts, gets the engine's own tallies (count and hit rate) and NO odds check: nothing is guessed.

DATA HEALTH: every source hands its card "no read" when its feed gave nothing inside that feed's own MAX_AGE
  (an hour for a 15-minute feed, days for a daily one, 15 days for a weekly report), so the card's own "no read"
  is already judged against the card's rhythm. health_update() counts, per market and card, how many of THAT
  market's closes in a row said "no read"; a closed market has no new close, so it is never counted.
"""
import calendar
import json
import math
import os
import re
import time

from .config import CFG, DATA_DIR, JOURNAL_DIR

NEITHER, UP, DOWN = 0, 1, 2                                           # the grades of engine15/labels.py
BAR_MS, HOUR_MS, DAY_MS = int(CFG["bar_ms"]), 3600000, 86400000
ATR_N = 14                                                            # ATR14 of the 1h chart (evidence.build_one)
WARM_DAYS = 75                                                        # bars read before the first call: Wilder's ATR has settled
BINS = (0.45, 0.50, 0.55, 0.60)                                       # stated odds of the favoured side: under 45, 45-50, ... 60+
BIN_WORDS = ("under 45", "45-50", "50-55", "55-60", "60+")
MIN_IND = 100                                                         # a verdict needs this many calls that do not overlap in time
Z95 = 1.96                                                            # 95% interval
AGREE, AGREE_EXACT = 0.95, 0.85                                       # the re-grade must match graded_now on this share of closes
DAY_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl$")
_DEC = json.JSONDecoder()


# ------------------------------------------------------------------ the journal, one line at a time
def _field(raw, key, width):
    """One value cut out of a journal line (bytes) without parsing the other 60 KB; None if it is not there."""
    k = raw.find(key)
    if k < 0:
        return None
    try:
        return _DEC.raw_decode(raw[k + len(key): k + len(key) + width].decode("utf-8", "replace"))[0]
    except ValueError:
        return None


def _quick(raw):
    """The few fields calibration needs, from the front of the line; None when the line is not shaped as expected."""
    a, t, g = _field(raw, b'"asset": ', 64), _field(raw, b'"time": ', 64), _field(raw, b'"graded_now": ', 256)
    if not (isinstance(a, str) and isinstance(t, str) and isinstance(g, dict)):
        return None
    k = raw.find(b'{"voice": "base"')
    return {"asset": a, "time": t, "graded_now": g, "odds": _field(raw, b'"odds": ', 256),
            "edge_pts": _field(raw, b'"edge_pts": ', 64),
            "base": None if k < 0 else _field(raw[k:k + 512], b'', 512)}


def _full(raw):
    e = json.loads(raw.decode("utf-8", "replace"))
    base = next((v for v in e.get("voices") or [] if isinstance(v, dict) and v.get("voice") == "base"), None)
    return {"asset": e["asset"], "time": e["time"], "graded_now": e.get("graded_now"), "odds": e.get("odds"),
            "edge_pts": e.get("edge_pts"), "base": base}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


def parse_line(raw):
    """One journal line (bytes) -> (asset, bar open ms, call or None, graded counts or None); None for a bad line.
    call = (P up, P down, P neither, lean +1/-1, base P up, base P down)."""
    try:
        e = _quick(raw) or _full(raw)
        ts = calendar.timegm(time.strptime(e["time"], "%Y-%m-%d %H:%M")) * 1000 - BAR_MS
        asset = str(e["asset"])
    except Exception:
        return None
    g, o, call = e.get("graded_now"), e.get("odds"), None
    counts = None
    if isinstance(g, dict) and all(_num(g.get(k)) for k in ("calls", "right", "wrong", "neither")):
        counts = (int(g["calls"]), int(g["right"]), int(g["wrong"]), int(g["neither"]))
    if isinstance(o, dict) and all(_num(o.get(k)) for k in ("up", "down", "neither")):
        edge = e.get("edge_pts")
        if not _num(edge):
            edge = (o["up"] - o["down"]) * 100.0
        if edge == 0 and o["up"] != o["down"]:
            edge = o["up"] - o["down"]
        b = e.get("base") if isinstance(e.get("base"), dict) else {}
        bu, bd = (b.get("up"), b.get("down")) if _num(b.get("up")) and _num(b.get("down")) else (0.5, 0.5)
        # the journal rounds the edge to 0.1 pt; a rounded "-0.0" still carries the side the engine leaned to
        call = (float(o["up"]), float(o["down"]), float(o["neither"]), 1 if math.copysign(1.0, edge) > 0 else -1,
                float(bu), float(bd))
    return asset, ts, call, counts


def day_files(journal_dir, start=None, end=None):
    """The LIVE day files in [start, end] (YYYY-MM-DD, inclusive), newest first. Never journal/replay/."""
    out = []
    try:
        names = os.listdir(journal_dir)
    except OSError:
        return out
    for n in names:
        m = DAY_FILE.match(n)
        if m and (start is None or m.group(1) >= start) and (end is None or m.group(1) <= end):
            out.append((m.group(1), os.path.join(journal_dir, n)))
    return sorted(out, reverse=True)


def read_calls(journal_dir, start=None, end=None, budget_s=None):
    """Stream the live journal, newest day first, keeping a few numbers per line.
    -> (calls {asset: {bar ms: call}}, counts {asset: {bar ms: graded_now}}, days read, True if the time ran out)."""
    t0, calls, counts, days, cut = time.time(), {}, {}, [], False
    for day, path in day_files(journal_dir, start, end):
        if budget_s is not None and days and time.time() - t0 > budget_s:
            cut = True
            break
        try:
            with open(path, "rb") as fh:
                for raw in fh:
                    got = parse_line(raw) if raw.strip() else None
                    if got is None:
                        continue
                    asset, ts, call, cnt = got
                    if call is not None:
                        calls.setdefault(asset, {})[ts] = call
                    if cnt is not None:
                        counts.setdefault(asset, {})[ts] = cnt
        except OSError:
            continue
        days.append(day)
    return calls, counts, sorted(days), cut


# ------------------------------------------------------------------ the engine's bars, tail only
def bar_path(asset, data_dir=None):
    return os.path.join(data_dir or DATA_DIR, "%s_15m.csv" % asset.lower())


def load_bars(path, since_ms):
    """{bar open ms: (open, high, low, close)} for the bars at or after since_ms: only the tail of the file is read.
    {} when the file is missing or is not a bar file."""
    try:
        size = os.path.getsize(path)
        back = 1 << 19
        with open(path, "rb") as fh:
            while True:
                start = max(0, size - back)
                fh.seek(start)
                chunk = fh.read(size - start)
                first = None
                for ln in chunk.split(b"\n", 12)[1 if start else 0:12]:
                    try:
                        first = int(ln.split(b",", 1)[0])
                        break
                    except ValueError:
                        continue
                if start == 0 or first is None or first <= since_ms:
                    break
                back *= 4
    except OSError:
        return {}
    out = {}
    for ln in chunk.split(b"\n")[1 if start else 0:]:
        f = ln.split(b",")
        if len(f) < 5:
            continue
        try:
            ts = int(f[0])
            if ts >= since_ms:
                out[ts] = (float(f[1]), float(f[2]), float(f[3]), float(f[4]))
        except ValueError:
            continue
    return out


def atr_1h(bars, order):
    """ATR14 of the 1h chart as the engine reads it: 15m bars -> 1h bars by clock hour, Wilder's average of the true
    range, and an hour's value is usable only once that hour has closed. -> (known-from ms list, ATR list)."""
    hours = []
    for ts in order:
        _o, h, l, c = bars[ts]
        k = ts // HOUR_MS
        if hours and hours[-1][0] == k:
            x = hours[-1]
            x[1], x[2], x[3] = max(x[1], h), min(x[2], l), c
        else:
            hours.append([k, h, l, c])
    known, vals, atr, prev = [], [], None, None
    for n, (k, h, l, c) in enumerate(hours):
        tr = abs(h - l) if prev is None else max(abs(h - l), abs(h - prev), abs(l - prev))
        atr = tr if atr is None else atr + (tr - atr) / float(ATR_N)
        prev = c
        known.append((k + 1) * HOUR_MS)
        vals.append(atr if n + 1 >= ATR_N else None)
    return known, vals


def _asof(known, vals, t_ms):
    lo, hi = 0, len(known)
    while lo < hi:
        mid = (lo + hi) // 2
        if known[mid] <= t_ms:
            lo = mid + 1
        else:
            hi = mid
    return vals[lo - 1] if lo else None


def grade(bars, order, pos, unit, horizon):
    """labels.triple_barrier for the call made at the close of bar order[pos]: -> (grade, closes until it was known),
    or None while the engine itself would not know the grade yet."""
    if unit is None or not unit > 0 or pos + 1 >= len(order):
        return None
    ref = bars[order[pos + 1]][0]
    up, dn, last = ref + unit, ref - unit, len(order) - 1
    for k in range(1, horizon + 1):
        if pos + k > last:
            return None
        _o, h, l, _c = bars[order[pos + k]]
        hit_up, hit_dn = h >= up, l <= dn
        if hit_up or hit_dn:
            return (NEITHER if (hit_up and hit_dn) else UP if hit_up else DOWN), k
    return NEITHER, horizon


# ------------------------------------------------------------------ calibration
def _empty():
    return {"n": 0, "right": 0, "wrong": 0, "neither": 0, "bins": [[0, 0.0, 0] for _ in BIN_WORDS],
            "brier_sum": 0.0, "base_sum": 0.0}


def _add(s, call, y):
    up, down, nei, lean, bu, bd = call
    fav = UP if lean > 0 else DOWN
    p = up if lean > 0 else down
    s["n"] += 1
    s["neither" if y == NEITHER else "right" if y == fav else "wrong"] += 1
    b = s["bins"][sum(1 for edge in BINS if p >= edge)]
    b[0], b[1], b[2] = b[0] + 1, b[1] + p, b[2] + (1 if y == fav else 0)
    o = (1.0 if y == UP else 0.0, 1.0 if y == DOWN else 0.0, 1.0 if y == NEITHER else 0.0)
    s["brier_sum"] += (up - o[0]) ** 2 + (down - o[1]) ** 2 + (nei - o[2]) ** 2
    s["base_sum"] += (bu - o[0]) ** 2 + (bd - o[1]) ** 2 + (max(0.0, 1.0 - bu - bd) - o[2]) ** 2


def _finish(s):
    d = s["right"] + s["wrong"]
    s["hit_pct"] = round(100.0 * s["right"] / d, 1) if d else None
    s["brier"] = round(s["brier_sum"] / s["n"], 4) if s["n"] else None
    s["brier_base"] = round(s["base_sum"] / s["n"], 4) if s["n"] else None
    s["table"] = [{"said": w, "n": b[0], "avg_said_pct": round(100.0 * b[1] / b[0], 1) if b[0] else None,
                   "came_pct": round(100.0 * b[2] / b[0], 1) if b[0] else None} for w, b in zip(BIN_WORDS, s["bins"])]
    return s


def verdict(n_ind, hits, expected, variance, min_ind=MIN_IND):
    """The stated rule. Only calls that do not overlap in time count (each made at or after the close the one before
    was graded at). Under min_ind of those: "too few". Else a 95% binomial interval around what the stated odds
    promised: fewer hits than the interval allows = "overconfident", more = "underconfident", inside = "about right"."""
    if n_ind < min_ind:
        return "too few"
    z = (hits - expected) / math.sqrt(variance) if variance > 0 else 0.0
    return "overconfident" if z < -Z95 else "underconfident" if z > Z95 else "about right"


def calibration(journal_dir=None, data_dir=None, start=None, end=None, budget_s=None, cfg=CFG):
    """Live calibration from the journal days in [start, end] (YYYY-MM-DD, inclusive; None = open).
    -> {"since", "until", "days", "partial", "markets": {asset: stats}, "pooled": stats, "seconds"}.
    stats: n graded forecasts, right / wrong / neither, hit_pct (direction right among calls graded up or down),
    "source" ("bars": every call re-graded and the odds checked; "journal": the engine's own tallies only, with
    "why"), and for "bars" also table (stated-odds buckets against what came), brier against brier_base (the
    engine's base-rate voice; 50/50 if the line has none), ind_n (calls that do not overlap) and verdict."""
    t0 = time.time()
    calls, counts, days, cut = read_calls(journal_dir or JOURNAL_DIR, start, end, budget_s)
    res = {"since": days[0] if days else None, "until": days[-1] if days else None, "days": len(days), "partial": cut,
           "markets": {}, "pooled": _empty(), "min_ind": MIN_IND}
    groups = [(g, list(a)) for g, a in cfg.get("universes", (("crypto", cfg["assets"]),))]
    known = set(a for _g, assets in groups for a in assets)
    groups += [(a, [a]) for a in sorted(set(calls) | set(counts)) if a not in known]
    for g, assets in groups:
        horizon = int(cfg.get("group_horizon", {}).get(g, cfg["horizon"]))
        firsts = [min(calls[a]) for a in assets if calls.get(a)]
        bars = {}
        if firsts:
            since = min(firsts) - WARM_DAYS * DAY_MS
            bars = dict((a, load_bars(bar_path(a, data_dir), since)) for a in assets)
        have = [a for a in assets if bars.get(a)]
        common = None                                               # the group's shared clock (evidence.build)
        for a in have:
            common = set(bars[a]) if common is None else common & set(bars[a])
        order = sorted(common or ())
        pos = dict((ts, k) for k, ts in enumerate(order))
        for a in assets:
            if a not in calls and a not in counts:
                continue
            s = _empty()
            mine, graded = {}, []
            if a in have and order:
                known_ms, vals = atr_1h(bars[a], order)
                for ts in sorted(calls.get(a, {})):
                    k = pos.get(ts)
                    if k is None:
                        continue
                    atr = _asof(known_ms, vals, ts + BAR_MS)
                    got = grade(bars[a], order, k, None if atr is None else cfg["barrier_atr"] * atr, horizon)
                    if got is None:
                        continue
                    y, res_k = got
                    call = calls[a][ts]
                    graded.append((k, res_k, call, y))
                    fav = UP if call[3] > 0 else DOWN
                    m = mine.setdefault(order[k + res_k], [0, 0, 0, 0])
                    m[0] += 1
                    m[3 if y == NEITHER else 1 if y == fav else 2] += 1
            # the check, at every close late enough that all its calls are in the journal: the same number of calls
            # graded and of "neither" (same), and the same right / wrong too (exact). The engine counts right and
            # wrong with the odds as it recomputes them at that step, so a near-even call can change sides there.
            same = exact = compared = 0
            if graded:
                k_from = graded[0][0] + horizon
                for ts, cnt in counts.get(a, {}).items():
                    if pos.get(ts, -1) >= k_from:
                        m = tuple(mine.get(ts, (0, 0, 0, 0)))
                        compared += 1
                        same += (m[0], m[3]) == (cnt[0], cnt[3])
                        exact += m == cnt
            ok = bool(graded) and (compared < 10 or (same >= AGREE * compared and exact >= AGREE_EXACT * compared))
            if ok:
                for _k, _r, call, y in graded:
                    _add(s, call, y)
                    _add(res["pooled"], call, y)
                n_ind = hits = 0
                exp = var = 0.0
                free = -1
                for k, res_k, call, y in graded:                    # calls that do not overlap in time
                    if k < free:
                        continue
                    free = k + res_k
                    p = call[0] if call[3] > 0 else call[1]
                    n_ind, exp, var = n_ind + 1, exp + p, var + p * (1.0 - p)
                    hits += y == (UP if call[3] > 0 else DOWN)
                s.update(source="bars", check=[same, exact, compared], ind_n=n_ind, ind_hits=hits, ind_expected=round(exp, 2),
                         verdict=verdict(n_ind, hits, exp, var))
            else:
                for cnt in counts.get(a, {}).values():
                    s["n"], s["right"], s["wrong"], s["neither"] = (s["n"] + cnt[0], s["right"] + cnt[1],
                                                                    s["wrong"] + cnt[2], s["neither"] + cnt[3])
                why = ("no readable price bars (%s)" % os.path.basename(bar_path(a, data_dir)) if a not in have else
                       "no call could be re-graded yet" if not graded else
                       "the re-grade matched the engine's own counts on only %d of %d closes" % (same, compared))
                s.update(source="journal", why=why, check=[same, exact, compared], verdict="n/a")
            res["markets"][a] = _finish(s)
            if s["source"] == "journal":
                s.update(brier=None, brier_base=None, table=[])
    _finish(res["pooled"])
    res["seconds"] = round(time.time() - t0, 2)
    return res


# ------------------------------------------------------------------ data health
SILENT_CLOSES = 8                 # a card that was reading is "silent" after 8 closes in a row of its own market (2 h of trading)
SILENT_CAP = 96                   # ... or after twice its longest earlier gap, but never more than 96 closes (a crypto day)
_NO_READ = re.compile(r"\bno read\b(?!;)|^No\b[^.]*\bread\b|\bno [\w/ -]{0,40}\bread at this close"
                      r"|^No (snapshot|forecast)\b[^.]*for this session", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def is_silent(reading):
    """True when a card's whole reading is the engine's "no read" sentence. A card that still reads part of its
    data (the news card without headlines but with the calendar; "today so far no read; last 7 days ...") is reading."""
    t = str(reading or "").strip()
    if not t:
        return True
    parts = _SENTENCE.split(t, 1)
    if len(parts) > 1 and parts[1].strip():
        return False
    return bool(_NO_READ.search(t))


def threshold(rec):
    return min(SILENT_CAP, max(SILENT_CLOSES, 2 * int(rec.get("gap", 0))))


def health_update(h, assets):
    """One look at the page's cards. h is what the bot remembers: {"t": {asset: last close seen}, "c": {"ASSET|card":
    {"ok": has read at least once, "n": closes in a row without a read, "since": the first of them, "al": alerted,
    "gap": the longest silence it came back from}}}. Only a market with a NEW close is looked at, so a closed market
    (the weekend, the S&P at night) can never raise an alarm.
    -> (h, went silent, came back): lists of (asset, card, since, closes). An alarm is raised once per silence."""
    h = h if isinstance(h, dict) else {}
    seen, cards = h.setdefault("t", {}), h.setdefault("c", {})
    gone, back = [], []
    for a, d in (assets if isinstance(assets, dict) else {}).items():
        d = d if isinstance(d, dict) else {}
        t, cs = d.get("time"), d.get("cards")
        if not t or not isinstance(cs, list) or seen.get(a) == t:
            continue
        seen[a] = t
        now_keys = set()
        for c in cs:
            title = str(c.get("card") or "") if isinstance(c, dict) else ""
            if not title:
                continue
            key = "%s|%s" % (a, title)
            now_keys.add(key)
            r = cards.setdefault(key, {})
            if is_silent(c.get("reading")):
                r["n"] = int(r.get("n", 0)) + 1
                r.setdefault("since", t)
                if r.get("ok") and not r.get("al") and r["n"] >= threshold(r):
                    r["al"] = 1
                    gone.append((a, title, r["since"], r["n"]))
            else:
                if r.get("n"):
                    if r.get("ok"):
                        r["gap"] = max(int(r.get("gap", 0)), int(r["n"]))
                    if r.get("al"):
                        back.append((a, title, r.get("since"), r["n"]))
                    for k in ("n", "since", "al"):
                        r.pop(k, None)
                r["ok"] = 1
        for key in [k for k in cards if k.startswith(a + "|") and k not in now_keys]:
            del cards[key]                                          # a card the engine no longer shows for this market
    return h, gone, back


def _by_card(pairs):
    out = {}
    for a, title, since, n in pairs:
        r = out.setdefault(title, {"card": title, "assets": [], "since": since, "closes": n})
        r["assets"].append(a)
        if since and (not r["since"] or since < r["since"]):
            r["since"] = since
        r["closes"] = max(r["closes"], n)
    return sorted(out.values(), key=lambda r: (r["since"] or "", r["card"]))


def health_view(h):
    """What the bot shows: {"cards": cards that have read somewhere, "reading": those not silent, "silent": [...],
    "missed": [...], "never": [...], "last": latest close seen}; each list item {card, assets, since, closes}.
    silent = was reading, now past its threshold; missed = no read at the last close or few, still inside it;
    never = has not read for that market since the watch began (no such data there, or a feed that never worked)."""
    cards = (h or {}).get("c") or {}
    ok_titles, silent, missed, never = set(), [], [], []
    for key, r in cards.items():
        a, _, title = key.partition("|")
        item = (a, title, r.get("since"), int(r.get("n", 0)))
        if r.get("ok"):
            ok_titles.add(title)
            if r.get("al"):
                silent.append(item)
            elif r.get("n"):
                missed.append(item)
        else:
            never.append(item)
    silent, missed, never = _by_card(silent), _by_card(missed), _by_card(never)
    times = sorted(((h or {}).get("t") or {}).values())
    return {"cards": len(ok_titles), "reading": len(ok_titles) - len(silent), "silent": silent, "missed": missed,
            "never": never, "last": times[-1] if times else None}
