# -*- coding: utf-8 -*-
"""trail_preview -- the dry run of the trail book for the VIP vault (docs/TRAIL_SWITCH_PLAN.md). READ ONLY, NEVER POSTS.

While vault_feed.SEND_TRAIL is off, every step writes out/live/trail_book_preview.json: the exact bodies the feed WOULD
post for BTC and ETH if the trail book (b_trail_setups) were their voice. The AI Trading session checks that file with the
vault's own parser (`aitvault book-check`) before anything real is switched on.

It runs the real code on a pretend voice: setups.build with a voice state that puts BTC and ETH on the trail voice from
the preview's own first step (so, as at a real changeover, a trail setup already open then is not shown), then
vault_feed.preview, which keeps its own memory inside the preview file and never touches the feed's.

    write(page, out_dir, log=None) -> the step log's line. The caller guards it: a failure here never stops a step.

One thing is the preview's own: there is no trail signal while the switch is off, so `entry_window_open` is taken as
"the setup opened at most WINDOW_BARS bars before the book's price bar" (the S1 window, from the opening).

File: {"generated_utc", "schema": 1, "note", "books": {SYM: {"body": {"book": {...}} | null, "reason": text | null}},
"intents": [the last 50 move_stop / close bodies, each with made_utc and ok], "state": the dry run's own memory}.
"""
import io
import json
import os

from . import setups, setups_voice, vault_feed

WINDOW_BARS = 4                         # signals.WINDOW: the bars after the alert in which the entry may fill
BAR_S = 900


def _prev(out_dir):
    try:
        with io.open(os.path.join(out_dir, vault_feed.PREVIEW_FILE), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def entries(page, from_utc):
    """{symbol: its setups.json entry on the trail voice} for the vault's markets, from the page; {} when the page does
    not carry the trail book. from_utc: {symbol: the pretend changeover time}."""
    voice = {"schema": setups_voice.SCHEMA,
             "markets": dict((s, {"rule": setups_voice.TRAIL, "from_utc": from_utc.get(s), "pending": False, "wait": None})
                             for s in vault_feed.ALLOWED if setups_voice.view_of(page, setups_voice.TRAIL, s) is not None)}
    if not voice["markets"]:
        return {}
    doc = setups.build(page, s1=None, voice=voice)
    out = {}
    for m in doc.get("markets") or []:
        if not isinstance(m, dict) or m.get("symbol") not in voice["markets"]:
            continue
        if m.get("side") in ("LONG", "SHORT"):
            try:
                age = vault_feed._epoch(m["price_bar_utc"]) - vault_feed._epoch(m["opened_utc"])
                m["entry_window_open"] = bool(0 <= age <= WINDOW_BARS * BAR_S)
            except (KeyError, TypeError, ValueError):
                m["entry_window_open"] = False
        out[m["symbol"]] = m
    return out


def write(page, out_dir, log=None, now=None):
    """page: the page dict, or the path of page.json (what live.step holds after export.rewrite_merged)."""
    if not isinstance(page, dict):
        with io.open(str(page), encoding="utf-8") as fh:
            page = json.load(fh)
        if not isinstance(page, dict):
            raise ValueError("the page is not a JSON object")
    prev = _prev(out_dir) or {}
    st = prev.get("state") if isinstance(prev.get("state"), dict) else {}
    frm = dict(st.get("preview_from_utc") or {}) if isinstance(st.get("preview_from_utc"), dict) else {}
    for s in vault_feed.ALLOWED:                                 # the pretend changeover: this preview's first step
        if s not in frm:
            bar = setups_voice.bar_utc(page, s)
            if bar is not None:
                frm[s] = bar
    marks = entries(page, frm)
    if not marks:
        return "trail preview: not written (the page has no %s view)" % setups_voice.book_of(setups_voice.TRAIL)
    prev["state"] = dict(st, preview_from_utc=frm)
    doc = vault_feed.preview(marks, prev, trades_dir=out_dir, now=now, generated_utc=page.get("generated_utc"),
                             page=page)
    doc["state"]["preview_from_utc"] = frm
    path = os.path.join(out_dir, vault_feed.PREVIEW_FILE)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)
    os.replace(tmp, path)
    return "trail preview: %s -> %s" % (
        ", ".join("%s %s" % (s, ((b.get("body") or {}).get("book") or {}).get("side") or "not built (%s)" % b.get("reason"))
                  for s, b in sorted(doc["books"].items())), path)
