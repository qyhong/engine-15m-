# -*- coding: utf-8 -*-
"""setups_voice -- which paper book speaks for each market on the Setups page, in the signals and to the VIP vault.
MONEY PATH (docs/TRAIL_SWITCH_PLAN.md; owner, 26 Nov 2026: "Lets switch", then "Page and VIP").

Two voices:
    "targets"   the book b_targets        half at Target 1, the rest at Target 2 (the only voice until the switch)
    "trail"     the book b_trail_setups   no targets; from 1R in favour the stop trails (shadows.run, rule "trail")

THE SWITCH is TRAIL_MARKETS: the markets whose voice is to be the trail book. Empty = OFF: every market is on the targets
voice, no state file is written, and setups.json, the signals and the vault's books are exactly what they were.
Switching a market on is a real-money decision (BTC and ETH reach the vault): the owner's word, a version bump, and for
BTC / ETH vault_feed.SEND_TRAIL as well (tests/test_setups_voice.py refuses one without the other).

A voice changes only BETWEEN setups, never inside one:
    * A market whose voice differs from the one wanted is PENDING. At the first step this is seen, the setup the old
      voice shows then is remembered (`wait`). The voice flips at the first step where the old voice's book no longer
      shows that setup (it is flat, or it shows another one). `from_utc` = the close of that step's price bar.
    * After a flip the new voice's setup is shown only when it opened at or after `from_utc`. A setup that was already
      open at the flip is never shown: the market reads FLAT until the new book opens its next one. So a setup's first
      sight is always its opening, nobody joins half-way, and an exit id is never made twice.
    * While pending, the old voice shows only the remembered setup; anything else it opens is not shown.

`published()` is the ONE rule for what a market shows; setups.py, signals.py and the vault preview all ask it. It is a
pure function of the page, the state and the switch, and it is safe when the Telegram bot (another process) reads the
state a moment before or after the engine wrote it: in every such order a market shows either the same thing or
nothing yet, never a setup the page will not show.

State: data/setups_voice_state.json, {"schema": 1, "markets": {SYM: {"rule", "from_utc", "pending", "wait"}}}, written
atomically and only when it holds something. A market that never left the targets voice has no entry.
If the file is lost while a market is on the trail voice, `recover` rebuilds it from the last setups.json (each trail
market carries exit_rule and exit_rule_from_utc there). Restore: docs/RESTORE.md.
"""
import calendar
import json
import os
import time

from .config import DATA_DIR

TARGETS, TRAIL = "targets", "trail"
BOOKS = {TARGETS: "b_targets", TRAIL: "b_trail_setups"}
RULES = (TARGETS, TRAIL)
TRAIL_MARKETS = ()                      # THE SWITCH (see above). () = off. Never changed without the owner's word.
SCHEMA = 1
STATE_PATH = os.path.join(DATA_DIR, "setups_voice_state.json")


# ------------------------------------------------------------------ small helpers
def _ms(t):
    """Epoch ms of '2026-11-26 03:15' (the page) or '2026-11-26T03:15:00Z'; None when it is not a time."""
    try:
        return calendar.timegm(time.strptime(str(t)[:16].replace("T", " "), "%Y-%m-%d %H:%M")) * 1000
    except (TypeError, ValueError):
        return None


def _iso(ms):
    return None if ms is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) // 1000))


def want(sym, trail_markets=None):
    """The voice the switch asks for in this market."""
    return TRAIL if sym in (TRAIL_MARKETS if trail_markets is None else trail_markets) else TARGETS


def book_of(rule):
    return BOOKS[rule]


def view_of(page, rule, sym):
    """The page's view of this market in the voice's book, or None when the page does not carry it."""
    try:
        v = page["shadows"]["books"][BOOKS[rule]]["assets"][sym]
    except (KeyError, TypeError):
        return None
    return v if isinstance(v, dict) else None


def opened_of(view):
    """The opening time (as the view writes it) of the setup a view holds open, or None when it holds none."""
    if not isinstance(view, dict) or view.get("status") not in ("LONG", "SHORT") or not view.get("opened_utc"):
        return None
    return str(view["opened_utc"])


def bar_utc(page, sym):
    """The close of the bar this market's price belongs to on this page (setups.py's price_bar_utc), ISO, or None."""
    try:
        a = (page.get("assets") or {}).get(sym) or {}
        ms = _ms(a.get("time")) if a.get("price") is not None else None     # as setups._market: no price, no bar
        if ms is None:
            group = a.get("market_group") or next(g for g, members in (page.get("markets") or {}).items()
                                                  if sym in members)
            ms = _ms(page["shadows"]["markets"][group]["as_of_utc"])
        return _iso(ms)
    except (KeyError, TypeError, AttributeError, StopIteration):
        return None


def _entry(st, sym):
    marks = st.get("markets") if isinstance(st, dict) else None
    e = marks.get(sym) if isinstance(marks, dict) else None
    return e if isinstance(e, dict) and e.get("rule") in RULES else None


# ------------------------------------------------------------------ what a market shows (the ONE rule)
def published(page, sym, st=None):
    """What this market shows now: {"rule", "book", "view", "open", "from_utc", "pending"}.
    view: the voice's own view of the market (its totals are read from it even when nothing is shown), or None;
    open: True when that view's open setup is the one to show; False = the market reads FLAT."""
    e = _entry(st, sym)
    rule = e["rule"] if e else TARGETS
    frm = e.get("from_utc") if e else None
    view = view_of(page, rule, sym)
    opened = opened_of(view)
    show = opened is not None
    if show and frm is not None:
        o, f = _ms(opened), _ms(frm)
        show = o is not None and f is not None and o >= f
    if show and e and e.get("pending") and e.get("wait") != opened:
        show = False
    return {"rule": rule, "book": BOOKS[rule], "view": view, "open": bool(show), "from_utc": frm,
            "pending": bool(e and e.get("pending"))}


# ------------------------------------------------------------------ the changeover (the engine's step only)
def update(page, st, trail_markets=None):
    """Move every market's voice one step on this page. Changes and returns `st` ({"schema", "markets"}).
    A market whose books the page does not carry is left exactly as it is."""
    st = st if isinstance(st, dict) else {}
    st.setdefault("schema", SCHEMA)
    marks = st.setdefault("markets", {})
    assets = page.get("assets") if isinstance(page, dict) and isinstance(page.get("assets"), dict) else {}
    for sym in sorted(set(assets) | set(marks)):
        e, w = _entry(st, sym), want(sym, trail_markets)
        cur = e["rule"] if e else TARGETS
        if cur == w:
            if e and e.get("pending"):                           # the switch was taken back before the flip
                e.update(pending=False, wait=None)
            continue
        if view_of(page, cur, sym) is None or view_of(page, w, sym) is None:
            continue                                             # a book is missing from the page: nothing is concluded
        shown = published(page, sym, st)
        now_open = opened_of(shown["view"]) if shown["open"] else None
        if not (e and e.get("pending")):                         # the switch is seen for the first time
            e = {"rule": cur, "from_utc": e.get("from_utc") if e else None, "pending": True, "wait": now_open}
            marks[sym] = e
        if e.get("wait") is not None and e["wait"] == now_open:
            continue                                             # the remembered setup is still open: wait
        bar = bar_utc(page, sym)
        if bar is None:
            continue                                             # no bar time: the flip waits for a step that has one
        marks[sym] = {"rule": w, "from_utc": bar, "pending": False, "wait": None}
    return st


# ------------------------------------------------------------------ the state file
def recover(prev_doc):
    """A state rebuilt from the last setups.json: its markets on the trail voice, with the time each started."""
    out = {"schema": SCHEMA, "markets": {}}
    for m in (prev_doc.get("markets") if isinstance(prev_doc, dict) else None) or []:
        if isinstance(m, dict) and m.get("exit_rule") == TRAIL and _ms(m.get("exit_rule_from_utc")) is not None \
                and isinstance(m.get("symbol"), str):
            out["markets"][m["symbol"]] = {"rule": TRAIL, "from_utc": _iso(_ms(m["exit_rule_from_utc"])),
                                           "pending": False, "wait": None}
    return out


def load(path=None, prev_doc=None):
    """The state. No file: what `recover` finds in the last setups.json (nothing = every market on the targets
    voice). A file that cannot be read is never taken for an empty one: `recover` if it finds a trail market, else
    the error is raised (nothing is published that step, and the log says why)."""
    path = path or STATE_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        if not isinstance(st, dict) or not isinstance(st.get("markets"), dict):
            raise ValueError("setups_voice_state.json is not a state")
        return st
    except FileNotFoundError:
        return recover(prev_doc)
    except (OSError, ValueError):
        got = recover(prev_doc)
        if got["markets"]:
            return got
        raise


def save(path, st):
    """Atomic. A state with no market is not written (the switch off leaves no file)."""
    path = path or STATE_PATH
    if not (st or {}).get("markets"):
        return False
    text = json.dumps(st, sort_keys=True, indent=1)
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    except (OSError, ValueError):
        pass
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return True
