# -*- coding: utf-8 -*-
"""vault_feed -- the BTC/ETH setups book to the site's VIP key vault on 127.0.0.1 (owner's exceptions, 18 Nov 2026).

Mind 15 holds no exchange key and never sends an order. It SENDS, to the vault's engine caller:
  submit_book    per market (BTCUSDT, ETHUSDT only), from the very market entries the step just wrote into setups.json
                 (so the vault sees what subscribers see). The vault decides and places orders for opted-in accounts.
  submit_intent  EXIT ONLY ("Allow close, reduce, stop", 18 Nov 2026): `close` when the setups book leaves a position,
                 `reduce` (half) when Target 1 is taken, `move_stop` to the entry after Target 1 (futures only). Never
                 `open`, never anything that adds.

    run(setups_path, log=print)   one pass, called by live.step right after setups.write when MIND15_VAULT_CONFIG is
                                  set. It never raises: every failure is ONE line "vault: <symbol> ... not sent (<reason>)".

Configuration: env MIND15_VAULT_CONFIG names the JSON file the vault's installer writes (/etc/ait-engine/engine.json):
  {"caller": "engine", "host": "127.0.0.1", "port": 8443, "secret_file": "/etc/ait-engine/engine.secret",
   "ca": "/etc/ait-engine/vault_ca.pem", "cert": "/etc/ait-engine/engine.crt", "key": "/etc/ait-engine/engine.key"}
  Unset = feature OFF (nothing sent, no line). It and the files it names are read at every step; anything wrong is one
  line and nothing is sent (exits are still detected and queued). caller must be "engine", host exactly "127.0.0.1",
  port an integer, every path absolute. engine.secret is one line of 64 hex characters: the key is
  bytes.fromhex(line.strip()), exactly 32 bytes, never logged. (MIND15_VAULT_URL, the plain-HTTP setting from before
  the installer existed, is gone: the vault's listener takes mTLS only.)

The vault's spec (its repo: vault/README.md "Engine calls", vault/server/aitvault/{api,vault,joinrule}.py):
  * POST https://127.0.0.1:<port>/v1/<op> over mutual TLS, built as api.client_tls(ca, cert, key) builds it: only the
    vault's own CA is trusted, the engine's client certificate is presented, TLS 1.2 or newer, and the server's
    certificate is checked against "127.0.0.1". The listener drops a caller without a certificate from its CA.
  * JSON body json.dumps(body, sort_keys=True); headers X-Ait-Caller (engine), X-Ait-Ts (unix s, within 30 s
    of the vault's clock), X-Ait-Nonce (16-64 of [A-Za-z0-9_-], once per 120 s), X-Ait-Sig = hex HMAC-SHA256(secret,
    "POST\\n<path>\\n<ts>\\n<nonce>\\n<sha256(body) hex>"). Any auth failure answers 404 not_found.
  * a book: prices are decimal strings, flags real booleans, levels strictly in order (LONG stop < entry < T1 < T2, SHORT
    the mirror), FLAT carries no levels; as_of_utc "YYYY-MM-DDTHH:MM:SSZ", at most 1,800 s old, strictly newer than the
    one held; the same as_of with the same body is a duplicate, with another body a conflict.

as_of_utc is the market's price_bar_utc (the close of the bar the book's price and levels belong to), not the document's
generated_utc: it names the book's moment, so a re-run of the same step gives the same as_of and the same body (a harmless
duplicate); it moves forward exactly once per new bar (the vault wants it strictly newer); and it ages honestly when the
feed stalls, so the vault's 1,800 s freshness check stops following a book whose price is old (generated_utc would look
fresh on stale data).

A book is sent when its content (everything but as_of) changed since the last successful send, or as a heartbeat when it
is unchanged but its as_of is at least HEARTBEAT_S newer: the vault needs it, because it drops a book older than 1,800 s
and a resend with the SAME as_of is only a duplicate that refreshes nothing. In practice: one send per market per bar.

State: data/vault_feed_state.json (atomic): per market the last sent book (content hash, as_of), the last seen position,
and every intent made (its fixed body and whether the vault took it), so each intent is sent once and retried at the next
step until the vault answers.

THE MEMORY LOST (20 Nov 2026): when that file is missing or cannot be read while a market shows an open setup, the feed
cannot know whether it saw the setup's entry window open, so it sends NO exit for that setup, and any exit that was
still waiting is gone. That is never silent: one line "vault: ALARM ..." at every step while the setup stays open, and
the state carries {"alarm": {"memory_lost": {symbol: {side, opened_utc, since, why}}}} for the Telegram bot's card. An
unreadable file is kept beside the new one as vault_feed_state.json.bad-<unix time>. Restore: docs/RESTORE.md.
"""
import calendar
import csv
import hashlib
import hmac
import http.client
import io
import json
import os
import re
import secrets
import socket
import ssl
import time
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from . import exits, setups_voice
from .config import DATA_DIR

ALLOWED = ("BTCUSDT", "ETHUSDT")                 # the owner's scope; anything else is ignored even if listed
CONFIG_ENV = "MIND15_VAULT_CONFIG"               # the installer's engine.json; unset = feature OFF (nothing sent, no line)
CONFIG_KEYS = ("caller", "host", "port", "secret_file", "ca", "cert", "key")
CONFIG_MAX = 65536                               # bytes read at most from engine.json / engine.secret
SECRET_RE = re.compile(r"^[0-9a-fA-F]{64}\Z")    # engine.secret: 64 hex characters, i.e. exactly 32 bytes
SYMBOLS_ENV = "MIND15_VAULT_SYMBOLS"             # default "BTCUSDT,ETHUSDT"
CALLER = "engine"
HOST = "127.0.0.1"                               # the only host ever called
TIMEOUT_S = 3.0                                  # per call; no retries inside a step
HEARTBEAT_S = 900
STATE_PATH = os.path.join(DATA_DIR, "vault_feed_state.json")
ACTIONS = ("close", "reduce", "move_stop")       # exits only: "open" is never built and never sent
REDUCE_FRACTION = exits.PART                     # the book's half at Target 1 (ONE constant: exits.PART)
# Contract 1 (20 Nov 2026): two OPTIONAL book keys, `schema` (the integer 1) and `held_share` (a number in (0, 1], the
# share of the setup's starting size the book still holds). OFF: the live vault refuses a book with any key it does not
# know, so this stays False until the AI Trading Bot session confirms the vault that accepts both is LIVE on the box.
# Switching it on changes every book body: the owner's word, a version bump and a new golden record (CLAUDE.md).
# `held_share` is sent ONLY together with t1_taken true: the reviewed vault update refuses a WHOLE book that carries
# held_share while t1_taken is not true (AI Trading Bot session, 20 Nov 2026). Before Target 1 the key is left out.
SEND_CONTRACT_1 = False
BOOK_SCHEMA = 1
# The opening Lead (23 Nov 2026; the owner's order in the AI Trading session: VIP accounts take a setup only when the
# Lead of the step that OPENED it is above 5.0 points in the setup's direction; the vault applies the cut). `lead_pts`:
# a JSON number, P(up) - P(down) in points (positive favours LONG), two decimals, from -100 to +100, the Lead of the
# deciding step that opened the setup, fixed for the setup's life. It is taken from setups.json's
# edge_with_position_pts at the step whose price bar IS the setup's opened_utc (the early entry books the setup at that
# close), kept in the feed's memory (pos[symbol]["lead_pts"]) and carried while the setup lasts. A setup first seen
# later (the feed's memory lost, the feed switched on mid-setup) has no known opening Lead and the key is left out;
# FLAT books never carry it. A FLIP is booked at the open after the close that decided it and is on the page one step
# later: its opening Lead is the reading the feed saw at that close (kept per market in the memory's "lead_seen").
# ON since think15-v5.2.10 (24 Nov 2026): the AI Trading Bot session confirmed vault package 81c96bd4, installed
# 2026-11-23T16:20:10Z, accepts the key (a JSON number, at most 2 decimals, -100..100, LONG/SHORT books only; the first
# value per setup is kept), and the owner said "Yes, deploy it". The vault's own filter (lead-min 5.0) is that
# session's switch. Do not switch this off while that filter is on: a book without the key does not pass it.
SEND_LEAD = True
LEAD_MAX = 100.0
REF_MAX_OFF = Decimal("0.015")                   # a book exit / T1 price further than this from the price now is replaced
                                                 # by the price now (the vault refuses a reference > 2% off its own price)
INTENT_GIVE_UP_S = 86400                         # the vault refuses an intent older than a day at signing
INTENT_KEEP_S = 7 * 86400                        # finished intents are kept this long (so an id is never made twice)
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,10})?$")      # the vault's binance.DECIMAL_RE
INTENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")                         # the vault's INTENT_ID_RE
INTENT_KEYS = {"close": {"intent_id", "market", "symbol", "action", "reference_price"},
               "reduce": {"intent_id", "market", "symbol", "action", "fraction", "reference_price"},
               "move_stop": {"intent_id", "market", "symbol", "action", "side", "stop_price", "reference_price"}}
LEVELS = ("entry", "stop", "target_1", "target_2")
# THE TRAIL BOOK (owner, 26 Nov 2026: "Lets switch", "Page and VIP"; docs/TRAIL_SWITCH_PLAN.md). A setups.json market on
# the trail voice carries exit_rule "trail" (setups_voice.py). Its book has no targets: the body is entry, stop (the
# stop as it stands), price, exit_rule, trail_active, entry_window_open, opened_utc, as_of_utc and lead_pts; NO
# target_1, target_2, rr_now_t2, t1_taken (agreed with the AI Trading session, 26 Nov 2026). Its intents: `move_stop`
# (futures only) at a step where the stop is tighter than the last one sent for that setup, and `close` when the setup
# leaves; never `reduce`.
# ON since think15-v5.2.12 (27 Nov 2026), together with setups_voice.TRAIL_MARKETS: vault package f7609091 (installed
# 26 Nov 07:04 UTC) accepts these bodies (book-check on the live preview and on the stop-move drill of 27 Nov), and
# the owner said yes. tests/test_vault_trail.py refuses a vault market on the trail voice while this is False; if
# that ever happens all the same, the vault is told FLAT for that market, with an ALARM line every step.
# UNDO: take the markets out of TRAIL_MARKETS (the changeover back runs by itself); switch this off only once no
# vault market is on the trail voice any more, and BEFORE any rollback of the vault below f7609091.
SEND_TRAIL = True
TRAIL = setups_voice.TRAIL
# HOW THE SETUP WAS OPENED (owner, 26 Nov 2026: "Yes, add it"; the AI Trading session reports the owner chose there that
# VIP accounts do not join a FORCED setup on a coin after a stop-out there). `opened_by`: an OPTIONAL book key on an open
# book of either voice, "ENTER" (a real signal), "FORCED" (the entry after idle_max flat sessions) or "FLIP" (the book
# turned straight from the other side; the vault treats it as a real signal and asked for it to be said, so that "opened
# by a flip" is not the same as "unknown"): the book's own word for the entry (shadows.asset_view's opened_by = the
# trade's why_in), read from page.json beside setups.json, only when that page's view shows the very setup setups.json
# shows (same side, same opening time). Any other word or no match: the key is left out (the vault then joins as
# today). setups.json does not carry the word, so subscribers' data is unchanged.
# ON since think15-v5.2.11 (27 Nov 2026): the AI Trading session confirmed vault package 0a74aa29, installed
# 2026-11-27T01:22Z, accepts the key: exactly "ENTER", "FORCED" or "FLIP", on a LONG or SHORT book only (targets or
# trail); the first value seen for a setup is kept; the key on a FLAT book, null, lower case or any other value refuses
# that market's WHOLE book. So it is never on FLAT and it is left out when unknown. The owner: "Yes, switch on". The
# vault's rule (that session's switch): after a member's losing first stop on a coin, that member skips the next setup
# there if it is FORCED. UNDO: if the vault is ever rolled back to a package before 0a74aa29, switch this off FIRST:
# the older code refuses a book that carries the key.
SEND_OPENED_BY = True
OPENED_BY = ("ENTER", "FORCED", "FLIP")
PAGE_FILE = "page.json"
MS = "ms"                                        # the id word of a trail move_stop: <SYM>.<opened>.ms.<DDHHMM of as_of>
PREVIEW_FILE = "trail_book_preview.json"         # the dry run (preview(), below): what WOULD be posted; never posted
PREVIEW_SCHEMA = 1
PREVIEW_INTENTS = 50


# ------------------------------------------------------------------ signing (a copy of the vault's api.body_sig)
def body_sig(secret, method, path, ts, nonce, body):
    msg = "\n".join([method, path, str(ts), nonce, hashlib.sha256(body).hexdigest()]).encode("ascii")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def headers(secret, path, raw, ts=None, nonce=None):
    """The vault's four auth headers (as api.VaultClient.headers builds them) for one POST of `raw` to `path`."""
    ts = str(int(time.time())) if ts is None else str(ts)
    nonce = nonce or secrets.token_hex(20)                       # 40 of [0-9a-f]
    return {"Content-Type": "application/json", "X-Ait-Caller": CALLER, "X-Ait-Ts": ts, "X-Ait-Nonce": nonce,
            "X-Ait-Sig": body_sig(secret, "POST", path, ts, nonce, raw)}


def encode(body):
    return json.dumps(body, sort_keys=True).encode("utf-8")      # byte for byte what VaultClient.call sends


# ------------------------------------------------------------------ numbers and times
def _places(v):
    """The market's own price precision, setups._px's rule: 5 decimals under 100, 3 under 1000, else 2."""
    a = abs(v)
    return 5 if a < 100 else 3 if a < 1000 else 2


def dec_text(v, places=None):
    """A positive finite number as the vault's decimal string ("65203.2", never "65203.200000001"), or None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")) or f <= 0:
            return None
        d = Decimal(repr(f)).quantize(Decimal(1).scaleb(-(_places(f) if places is None else places)),
                                      rounding=ROUND_HALF_EVEN)
    except (TypeError, ValueError, InvalidOperation):
        return None
    s = format(d, "f")
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s if DECIMAL_RE.match(s) and Decimal(s) > 0 else None


def _epoch(utc):
    return calendar.timegm(time.strptime(utc, "%Y-%m-%dT%H:%M:%SZ"))


def _utc(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _rr(t2, stop, price, long):
    """The vault's joinrule.rr_to(target_2, stop, price): None unless the price is strictly between stop and target."""
    if long:
        return (t2 - price) / (price - stop) if stop < price < t2 else None
    return (price - t2) / (stop - price) if t2 < price < stop else None


# ------------------------------------------------------------------ the book
def _held_share(v):
    """The market's held_share as a number in (0, 1], or None (then the key is left out; it is optional)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        return None
    return round(float(v), 6) if 0 < v <= 1 else None


def _contract(b, m=None):
    """Add the contract-1 keys to a book when the switch is on; otherwise the book is exactly what it always was."""
    if SEND_CONTRACT_1:
        b["schema"] = BOOK_SCHEMA
        hs = _held_share(m.get("held_share")) if (m is not None and m.get("t1_taken") is True) else None
        if hs is not None:
            b["held_share"] = hs
    return b


def _lead_ok(v):
    """A Lead the vault can take: a finite number within +-LEAD_MAX (never a bool)."""
    return not isinstance(v, bool) and isinstance(v, (int, float)) and v == v and abs(v) <= LEAD_MAX


def signed_lead(m):
    """This step's Lead from a setups.json entry with an open position, signed (positive favours LONG), or None
    (FLAT entries carry no reading)."""
    side, e = m.get("side"), m.get("edge_with_position_pts")
    if side not in ("LONG", "SHORT") or not _lead_ok(e):
        return None
    return round(float(e) * (1 if side == "LONG" else -1), 2) + 0.0


def opening_lead(m, last=None):
    """A new setup's opening Lead, or None when it cannot be known. An entry from flat is booked at the close that
    decides it (v5.2.9), so its price bar IS its opened_utc: this step's reading. A flip is booked at the open after
    the deciding close and shows one step later: the reading `last` ({"bar", "lead"}) the feed saw at that close."""
    opened = m.get("opened_utc")
    if not isinstance(opened, str):
        return None
    if opened == m.get("price_bar_utc"):
        return signed_lead(m)
    if isinstance(last, dict) and last.get("bar") == opened and _lead_ok(last.get("lead")):
        return round(float(last["lead"]), 2) + 0.0
    return None


def remembered_lead(st, sym, m):
    """The opening Lead the feed's memory holds for the setup this market shows now (after track()), or None."""
    p = st.get("pos", {}).get(sym) if isinstance(st, dict) else None
    return p.get("lead_pts") if isinstance(p, dict) and p.get("opened_utc") == m.get("opened_utc") else None


def read_page(setups_path):
    """page.json beside setups.json (the page the step just wrote), or None. Never raises."""
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(setups_path)), PAGE_FILE), encoding="utf-8") as fh:
            page = json.load(fh)
        return page if isinstance(page, dict) else None
    except (OSError, ValueError):
        return None


def opened_by_of(page, m):
    """The book's own word for how it opened the setup this market shows ("ENTER" / "FORCED"), from the page's view of
    the market in the voice's book; None when the view does not show this very setup or the word is another one."""
    if not isinstance(page, dict) or m.get("side") not in ("LONG", "SHORT"):
        return None
    v = setups_voice.view_of(page, TRAIL if is_trail(m) else setups_voice.TARGETS, m.get("symbol"))
    if not isinstance(v, dict) or v.get("status") != m.get("side"):
        return None
    a, b = setups_voice._ms(v.get("opened_utc")), setups_voice._ms(m.get("opened_utc"))
    if a is None or a != b:
        return None
    return v.get("opened_by") if v.get("opened_by") in OPENED_BY else None


def remembered_opened_by(st, sym, m, page=None):
    """After track(): the word for the setup this market shows, from the page now, else from the feed's memory (where
    it is kept for the setup's life, so the body does not change when a page cannot be read). None while the switch
    is off."""
    if not SEND_OPENED_BY:
        return None
    p = st.get("pos", {}).get(sym) if isinstance(st, dict) else None
    if not isinstance(p, dict) or p.get("opened_utc") != m.get("opened_utc"):
        return None
    word = opened_by_of(page, m) or p.get("opened_by")
    if word in OPENED_BY:
        p["opened_by"] = word
        return word
    return None


def build_book(m, as_of, lead=None, force=False, opened_by=None):
    """One market's submit_book body {"book": {...}} from its setups.json entry, or (None, short reason). Nothing is
    'fixed': a market whose levels are missing or out of order is not sent. `lead`: the setup's opening Lead from the
    feed's memory, added as lead_pts only when SEND_LEAD is on. A market on the trail voice (exit_rule "trail") gets
    the trail body (build_trail_book); `force` is the preview's: it builds that body while SEND_TRAIL is off."""
    sym, side = m.get("symbol"), m.get("side")
    if side not in ("LONG", "SHORT", "FLAT"):
        return None, "bad side"
    if not isinstance(as_of, str) or not UTC_RE.match(as_of):
        return None, "no price bar time"
    price = dec_text(m.get("price"))
    if side == "FLAT":
        b = {"symbol": sym, "side": "FLAT", "t1_taken": False, "entry_window_open": False, "as_of_utc": as_of}
        if price is not None:
            b["price"] = price
        return {"book": _contract(b)}, None
    if is_trail(m):
        return build_trail_book(m, as_of, lead, force=force, opened_by=opened_by)
    lv = dict((k, dec_text(m.get(k))) for k in LEVELS)
    missing = [k for k in LEVELS if lv[k] is None]
    if missing:
        return None, "levels missing (%s)" % ",".join(missing)
    if price is None:
        return None, "no price"
    for k in ("t1_taken", "entry_window_open"):
        if not isinstance(m.get(k), bool):
            return None, "bad %s" % k
    opened = m.get("opened_utc")
    if not isinstance(opened, str) or not UTC_RE.match(opened):
        return None, "bad opened_utc"
    e, s, t1, t2 = (Decimal(lv[k]) for k in LEVELS)
    # after Target 1 the book's stop IS the entry: the vault accepts stop == entry exactly when t1_taken is true
    # (vip-vault a88253e); otherwise the order is strict
    at_entry = bool(m.get("t1_taken")) and e == s and ((side == "LONG" and e < t1 < t2) or (side == "SHORT" and t2 < t1 < e))
    if not (at_entry or (side == "LONG" and s < e < t1 < t2) or (side == "SHORT" and t2 < t1 < e < s)):
        return None, "levels out of order"
    b = {"symbol": sym, "side": side, "entry": lv["entry"], "stop": lv["stop"], "target_1": lv["target_1"],
         "target_2": lv["target_2"], "price": price, "t1_taken": m["t1_taken"],
         "entry_window_open": m["entry_window_open"], "opened_utc": opened, "as_of_utc": as_of}
    # rr_now_t2 is optional and only cross-checked by the vault (its own figure rules): sent as the page shows it when
    # it agrees with the vault's own sum on these strings, else left out (a disagreement would refuse the whole book)
    if "rr_now_t2" in m:
        mine = _rr(t2, s, Decimal(price), side == "LONG")
        theirs = m.get("rr_now_t2")
        if theirs is None and mine is None:
            b["rr_now_t2"] = None
        elif theirs is not None and mine is not None:
            t = dec_text(theirs, places=2)
            if t is not None and abs(Decimal(t) - mine) <= max(Decimal("0.02"), mine / 100):
                b["rr_now_t2"] = t
    if SEND_LEAD and _lead_ok(lead):
        b["lead_pts"] = round(float(lead), 2) + 0.0
    if SEND_OPENED_BY and opened_by in OPENED_BY:
        b["opened_by"] = opened_by
    return {"book": _contract(b, m)}, None


def is_trail(m):
    """A setups.json market on the trail voice (setups_voice.py)."""
    return isinstance(m, dict) and m.get("exit_rule") == TRAIL


def build_trail_book(m, as_of, lead=None, force=False, opened_by=None):
    """The submit_book body of an OPEN trail setup, or (None, short reason). No targets. Before the trail has armed the
    stop is strictly on the losing side of the entry; always it is strictly on the losing side of the price (the book
    sets it at a close, from that close, and a stop that traded closed the book)."""
    if not (SEND_TRAIL or force):
        return None, "trail book while SEND_TRAIL is off"
    sym, side = m.get("symbol"), m.get("side")
    if side not in ("LONG", "SHORT"):
        return None, "bad side"
    entry, stop, price = dec_text(m.get("entry")), dec_text(m.get("stop")), dec_text(m.get("price"))
    missing = [k for k, v in (("entry", entry), ("stop", stop)) if v is None]
    if missing:
        return None, "levels missing (%s)" % ",".join(missing)
    if price is None:
        return None, "no price"
    for k in ("trail_active", "entry_window_open"):
        if not isinstance(m.get(k), bool):
            return None, "bad %s" % k
    if m.get("t1_taken") is True or m.get("target_1") is not None or m.get("target_2") is not None:
        return None, "a trail book with targets"
    opened = m.get("opened_utc")
    if not isinstance(opened, str) or not UTC_RE.match(opened):
        return None, "bad opened_utc"
    e, s, p, sgn = Decimal(entry), Decimal(stop), Decimal(price), (1 if side == "LONG" else -1)
    if not m["trail_active"] and not sgn * (e - s) > 0:
        return None, "levels out of order"
    if not sgn * (p - s) > 0:
        return None, "stop not on the losing side of the price"
    b = {"symbol": sym, "side": side, "entry": entry, "stop": stop, "price": price, "exit_rule": TRAIL,
         "trail_active": m["trail_active"], "entry_window_open": m["entry_window_open"], "opened_utc": opened,
         "as_of_utc": as_of}
    if SEND_LEAD and _lead_ok(lead):
        b["lead_pts"] = round(float(lead), 2) + 0.0
    if SEND_OPENED_BY and opened_by in OPENED_BY:
        b["opened_by"] = opened_by
    return {"book": _contract(b)}, None


def _content(book):
    return hashlib.sha256(encode(dict((k, v) for k, v in book.items() if k != "as_of_utc"))).hexdigest()


# ------------------------------------------------------------------ positions -> exit intents
# The guard of 18 Nov 2026 ("exits only for a setup whose entry window this feed saw open") is OFF since 20 Nov 2026.
# It assumed the vault joins a setup only inside its entry window. The vault's join rule (owner, 18 Nov: "Hybrid join
# rule") also joins a setup long after its window, so the guard left joined members with NO exit: the two shorts of 15
# Nov were joined on 19 Nov and BTC's Target 1 on 20 Nov sent nothing (found by the AI Trading Bot session). An exit
# for a setup nobody joined closes nothing on the vault's side (its exits act on the vault's own quantity only, the
# futures fix of 19 Nov), so every setup the book publishes now gets its exits. The switch and the `eligible` mark
# stay in the code and in the tests; nothing sets it back to True without the owner's word.
EXITS_ONLY_IF_WINDOW_SEEN = False

def _pos_of(m):
    """The open position a setups market shows: {side, opened_utc, entry, target_1, t1_taken}; None when FLAT;
    "unknown" when the entry cannot be read (then nothing is concluded)."""
    side = m.get("side")
    if side == "FLAT":
        return None
    if side not in ("LONG", "SHORT"):
        return "unknown"
    opened, entry = m.get("opened_utc"), dec_text(m.get("entry"))
    if not isinstance(opened, str) or not UTC_RE.match(opened) or entry is None:
        return "unknown"
    if is_trail(m):                                              # no targets; the stop as it stands is remembered
        return {"side": side, "opened_utc": opened, "entry": entry, "target_1": None, "t1_taken": False,
                "exit_rule": TRAIL, "stop": dec_text(m.get("stop"))}
    return {"side": side, "opened_utc": opened, "entry": entry, "target_1": dec_text(m.get("target_1")),
            "t1_taken": m.get("t1_taken") is True}


def intent_id(sym, opened_utc, action, market):
    """Deterministic: (market symbol, the setup's opening time, action, vault market). Never join- / k3- (it starts with
    the symbol)."""
    return "%s.%s.%s.%s" % (sym, opened_utc.replace("-", "").replace(":", ""), action, market)


def _compact(opened_utc):
    return opened_utc.replace("-", "").replace(":", "")


def ms_id(sym, opened_utc, as_of):
    """A trail move_stop's id: (symbol, the setup's opening time, "ms", day-hour-minute of the book's as_of), so each
    15-minute step has its own; None when as_of is not a time."""
    if not isinstance(as_of, str) or not UTC_RE.match(as_of):
        return None
    return "%s.%s.%s.%s" % (sym, _compact(opened_utc), MS, as_of[8:10] + as_of[11:13] + as_of[14:16])


def _ms_prefix(sym, opened_utc):
    return "%s.%s.%s." % (sym, _compact(opened_utc), MS)


def tighter(side, new, old):
    """True when the stop `new` is strictly tighter than `old` for a book on this side (decimal texts)."""
    if new is None or old is None:
        return False
    return Decimal(new) > Decimal(old) if side == "LONG" else Decimal(new) < Decimal(old)


def trail_intents(sym, pos, stop_sent, now_px, as_of):
    """The trail book's stop moved: ONE futures move_stop to the stop as it stands, when it is tighter than the last
    stop sent for this setup. -> [] when there is nothing to send, None when it cannot be built (no price, no as_of)."""
    if not tighter(pos["side"], pos.get("stop"), stop_sent):
        return []
    iid = ms_id(sym, pos["opened_utc"], as_of)
    if iid is None or now_px is None:
        return None
    return [{"intent_id": iid, "market": "futures", "symbol": sym, "action": "move_stop", "reference_price": now_px,
             "side": "BUY" if pos["side"] == "LONG" else "SELL", "stop_price": pos["stop"]}]


def _ref(book_px, now_px):
    """The reference price: the book's own exit / T1 price, unless it is missing or more than REF_MAX_OFF away from
    the price now (then the price now)."""
    if book_px is None:
        return now_px
    if now_px is None:
        return book_px
    return now_px if abs(Decimal(book_px) / Decimal(now_px) - 1) > REF_MAX_OFF else book_px


def _markets(side):
    """futures for both sides; spot only for a LONG book: a spot account holds no short, and the vault's spot close /
    reduce sells the member's base coin, so a spot exit for a SHORT setup would sell coins that were never joined."""
    return ("spot", "futures") if side == "LONG" else ("futures",)


def _mk(sym, pos, action, market, ref, **extra):
    b = dict({"intent_id": intent_id(sym, pos["opened_utc"], action, market), "market": market, "symbol": sym,
              "action": action, "reference_price": ref}, **extra)
    return b


def t1_intents(sym, pos, now_px):
    """Target 1 just taken: reduce half (spot for a LONG book, futures), and on futures move the stop to the entry; if
    the price is already at or through the entry, a futures close instead (the book's stop at the entry would fire)."""
    out, long = [], pos["side"] == "LONG"
    ref = _ref(pos.get("target_1"), now_px)
    if ref is None:
        return None
    e = Decimal(pos["entry"])
    mark = Decimal(now_px) if now_px is not None else Decimal(ref)
    through = mark <= e if long else mark >= e
    for market in _markets(pos["side"]):
        if market == "futures" and through:
            out.append(_mk(sym, pos, "close", market, now_px or ref))
            continue
        out.append(_mk(sym, pos, "reduce", market, ref, fraction=REDUCE_FRACTION))
        if market == "futures":
            out.append(_mk(sym, pos, "move_stop", market, now_px or ref, side="BUY" if long else "SELL",
                           stop_price=pos["entry"]))
    return out


def exit_price(row, now_px):
    """The book's own exit price of what was left, from its trade row: p_out when no part was taken earlier; after
    Target 1, Target 2 for "...T2", the entry for "...STOP_BE", else (a flip or the model's exit) the price now (p_out
    is then the average of both parts)."""
    why = str(row.get("why_out") or "").strip()
    if not why.startswith("T1+"):
        return dec_text(row.get("p_out"))
    if why.endswith("T2"):
        return dec_text(row.get("target_2"))
    if why.endswith("STOP_BE"):
        return dec_text(row.get("p_in"))
    return now_px


def find_trade(trades_dir, sym, pos):
    """The closed-trade row of that position in its own book's file (shadow_trades_b_targets_<SYM>.csv, or the trail
    book's shadow_trades_b_trail_setups_<SYM>.csv for a trail setup: same side, t_in_ms = opened_utc), the newest such
    row, or None."""
    book = setups_voice.book_of(TRAIL if pos.get("exit_rule") == TRAIL else setups_voice.TARGETS)
    path = os.path.join(trades_dir, "shadow_trades_%s_%s.csv" % (book, sym))
    try:
        if os.path.getsize(path) > 5 * 1024 * 1024:
            return None
        with io.open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, ValueError, csv.Error):
        return None
    want_side = 1.0 if pos["side"] == "LONG" else -1.0
    hit = None
    for r in rows:
        try:
            if _utc(int(float(r["t_in_ms"])) // 1000) == pos["opened_utc"] and float(r["side"]) == want_side:
                hit = r
        except (KeyError, TypeError, ValueError):
            continue
    return hit


def close_intents(sym, pos, row, now_px):
    exit_px = exit_price(row, now_px) if row is not None else None
    ref = _ref(exit_px, now_px)
    if ref is None:
        return None
    return [_mk(sym, pos, "close", market, ref) for market in _markets(pos["side"])]


def intent_ok(b):
    """The last guard before anything goes out: an exit with exactly the vault's fields; never "open"."""
    return (isinstance(b, dict) and b.get("action") in ACTIONS and set(b) == INTENT_KEYS[b["action"]]
            and b.get("symbol") in ALLOWED and b.get("market") in ("spot", "futures")
            and isinstance(b.get("intent_id"), str) and INTENT_ID_RE.match(b["intent_id"]) is not None
            and not b["intent_id"].startswith(("join-", "k3-"))
            and isinstance(b.get("reference_price"), str) and DECIMAL_RE.match(b["reference_price"]) is not None
            and (b["action"] != "move_stop" or b["market"] == "futures"))


def track(sym, m, st, trades_dir, now):
    """Compare the market's position with the last one seen; queue the exit intents it calls for (each id once).
    -> a short reason when an event could not be turned into intents (it is tried again next step), else None."""
    seen = st.setdefault("pos", {})
    cur = _pos_of(m)
    if cur == "unknown":
        return None
    first, prev = sym not in seen, seen.get(sym)
    now_px = dec_text(m.get("price"))
    # GUARD (18 Nov 2026, the vault live): exits only for a setup the vault could have joined: one whose entry window was
    # seen OPEN by this feed. A setup already past its window when the feed first saw it (e.g. the 15 Nov shorts) is
    # never acted on, so an exit never reaches a member position the vault did not open from this book.
    if isinstance(cur, dict):
        same = isinstance(prev, dict) and prev.get("side") == cur["side"] and prev.get("opened_utc") == cur["opened_utc"]
        cur["eligible"] = bool(m.get("entry_window_open") is True or (same and prev.get("eligible")))
        # the opening Lead: fixed at the setup's first sighting, carried for its life
        if not isinstance(st.get("lead_seen"), dict):            # a damaged memory never stops the feed
            st["lead_seen"] = {}
        lead = prev.get("lead_pts") if same else opening_lead(m, st["lead_seen"].get(sym))
        if _lead_ok(lead):
            cur["lead_pts"] = lead
        if same and prev.get("opened_by") in OPENED_BY:          # how the setup was opened (SEND_OPENED_BY), once known
            cur["opened_by"] = prev["opened_by"]
        if cur.get("exit_rule") == TRAIL:                        # the last stop the vault was given for this setup:
            sent = prev.get("stop_sent") if same and prev.get("exit_rule") == TRAIL else None    # at first sight, the
            cur["stop_sent"] = sent if sent is not None else cur.get("stop")                      # book's own stop
    new, over = [], None
    if not first and prev and (prev.get("eligible") or not EXITS_ONLY_IF_WINDOW_SEEN):
        if cur is not None and cur["side"] == prev["side"] and cur["opened_utc"] == prev["opened_utc"]:
            if cur.get("exit_rule") == TRAIL:
                if prev.get("exit_rule") == TRAIL:               # the trail moved: one move_stop, only when tighter
                    new = trail_intents(sym, cur, cur["stop_sent"], now_px, m.get("price_bar_utc"))
                    if new:
                        cur["stop_sent"], over = cur["stop"], prev
            elif cur["t1_taken"] and not prev.get("t1_taken"):
                new = t1_intents(sym, dict(prev, target_1=cur.get("target_1") or prev.get("target_1")), now_px)
        else:                                                    # stopped, target 2, flip, the model's exit
            new = close_intents(sym, prev, find_trade(trades_dir, sym, prev), now_px)
            over = prev if prev.get("exit_rule") == TRAIL else None
    if new is None:
        return "no reference price for the exit"
    queue = st.setdefault("intents", {})
    if new and over is not None:                                 # a stop move that never went out is overtaken by the
        pre = _ms_prefix(sym, over["opened_utc"])                # newer one (or by the close): it must not hold the book
        for iid, it in queue.items():
            if iid.startswith(pre) and isinstance(it, dict) and it.get("status") == "pending":
                it["status"] = "superseded"
    for b in new:
        if b["intent_id"] not in queue and intent_ok(b):
            st["seq"] = int(st.get("seq", 0)) + 1
            queue[b["intent_id"]] = {"body": b, "status": "pending", "made": now, "seq": st["seq"]}
    seen[sym] = cur
    now_lead, bar = signed_lead(m), m.get("price_bar_utc")       # this close's reading, for a flip shown next step
    if not isinstance(st.get("lead_seen"), dict):
        st["lead_seen"] = {}
    if now_lead is not None and isinstance(bar, str):
        st["lead_seen"][sym] = {"bar": bar, "lead": now_lead}
    else:
        st["lead_seen"].pop(sym, None)
    return None


# ------------------------------------------------------------------ config, state, the call
def load_config(path):
    """The installer's engine.json -> ({the seven keys}, None) or (None, short reason). caller "engine", host exactly
    "127.0.0.1", an integer port, absolute paths; other keys are ignored."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(CONFIG_MAX + 1)
        if len(raw) > CONFIG_MAX:
            return None, "vault config unreadable (too large)"
        conf = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):                                # (a bad UTF-8 or JSON is a ValueError too)
        return None, "vault config unreadable"
    if not isinstance(conf, dict):
        return None, "vault config invalid (not an object)"
    missing = [k for k in CONFIG_KEYS if k not in conf]
    if missing:
        return None, "vault config invalid (missing %s)" % ",".join(missing)
    if conf["caller"] != CALLER:
        return None, "vault config invalid (caller must be engine)"
    if conf["host"] != HOST:
        return None, "vault config invalid (host must be 127.0.0.1)"
    if type(conf["port"]) is not int or not 0 < conf["port"] < 65536:
        return None, "vault config invalid (port)"
    for k in ("secret_file", "ca", "cert", "key"):
        v = conf[k]
        if not isinstance(v, str) or not v or "\x00" in v or not os.path.isabs(v):
            return None, "vault config invalid (%s not an absolute path)" % k
    return dict((k, conf[k]) for k in CONFIG_KEYS), None


def read_secret(path):
    """engine.secret: one line of 64 hex characters -> bytes.fromhex(line.strip()), exactly 32 bytes; else None. The
    vault's Callers.from_config reads the same file the same way, so both hold the same key. Never logged."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(CONFIG_MAX + 1)
        line = raw.decode("ascii").strip()
    except (OSError, ValueError):
        return None
    if len(raw) > CONFIG_MAX or not SECRET_RE.match(line):
        return None
    key = bytes.fromhex(line)
    return key if len(key) == 32 else None


def _no_password():
    return b""                                                   # an encrypted key fails at once, never a prompt


def client_tls(ca, cert, key):
    """The vault's api.client_tls(ca, cert, key), step for step: a TLS client context (certificate required, the
    hostname checked: PROTOCOL_TLS_CLIENT's defaults, left on), TLS 1.2 at least, the vault's CA as the ONLY trust
    anchor (no system store), the engine's client certificate and key. -> (context, None) or (None, short reason)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    if ctx.verify_mode != ssl.CERT_REQUIRED or not ctx.check_hostname:          # (never true; a guard, not a setting)
        return None, "tls context without verification"
    try:
        ctx.load_verify_locations(ca)
    except (OSError, ValueError):
        return None, "vault CA unreadable"
    try:
        ctx.load_cert_chain(cert, key, password=_no_password)
    except (OSError, ValueError):
        return None, "client certificate or key unreadable"
    return ctx, None


def read_state(path):
    """-> (the state, "ok" | "missing" | "unreadable"). Anything but "ok" gives an empty state: the memory is lost."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return {}, "missing"
    except Exception:
        return {}, "unreadable"
    return (st, "ok") if isinstance(st, dict) else ({}, "unreadable")


def load_state(path):
    return read_state(path)[0]


def _keep_bad(path, now):
    """An unreadable state file is moved aside (never overwritten unseen). Never raises."""
    try:
        os.replace(path, "%s.bad-%d" % (path, int(now)))
    except OSError:
        pass


def memory_alarm(st, markets, syms, how, now, log):
    """Keep st["alarm"]["memory_lost"] true to the markets, after track(). how: read_state's word for this step.
    A setup is entered when the memory was lost this step while that setup was open; it leaves when that setup is no
    longer the market's position. Its "exits" says what the loss costs: "none" (the guard is on and the feed never
    saw its entry window: no exit at all; one line at EVERY step) or "later" (the guard is off: an exit that was
    waiting, or a Target 1 taken while the memory was gone, was not sent, later exits are; no log line, because a
    first start with a setup open looks the same: the state entry and the Telegram card carry it)."""
    lost = st.get("alarm", {}).get("memory_lost") if isinstance(st.get("alarm"), dict) else None
    lost = dict(lost) if isinstance(lost, dict) else {}
    seen = st.get("pos") if isinstance(st.get("pos"), dict) else {}
    for sym in syms:
        if sym not in markets:                                   # not in setups.json this step: nothing is concluded
            continue
        cur, old = seen.get(sym), lost.get(sym)
        if isinstance(old, dict) and not (isinstance(cur, dict) and cur.get("side") == old.get("side")
                                          and cur.get("opened_utc") == old.get("opened_utc")):
            del lost[sym]                                        # the setup is over (or replaced): the alarm ends
            if old.get("exits", "none") == "none":
                _say(log, "vault: %s %s setup opened %s is over; the feed sent no exit for it (its memory was lost)"
                     % (sym, old.get("side"), old.get("opened_utc")))
            old = None
        blind = isinstance(cur, dict) and EXITS_ONLY_IF_WINDOW_SEEN and not cur.get("eligible")
        if how != "ok" and isinstance(cur, dict):               # a loss now: it replaces what an earlier one recorded
            old = lost[sym] = {"side": cur["side"], "opened_utc": cur["opened_utc"], "since": now, "why": how,
                               "exits": "none" if blind else "later"}
        if isinstance(old, dict) and old.get("exits", "none") == "none":
            _say(log, "vault: ALARM %s %s setup opened %s is open and the feed's memory was %s: NO exit will be sent for "
                      "it (see docs/RESTORE.md)" % (sym, old.get("side"), old.get("opened_utc"), old.get("why")))
    if lost:
        st["alarm"] = {"memory_lost": lost}
    else:
        st.pop("alarm", None)


def save_state(path, st):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh, sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def post(port, secret, tls, op, body, timeout=None):
    """One signed call to https://127.0.0.1:<port>/v1/<op> over the mTLS context `tls` (as VaultClient.call makes it:
    http.client, so no proxy is ever read and no redirect followed; a 3xx is just a status). -> (HTTP status, answer
    dict); status 0 = no answer (answer {"error": reason}). Never raises."""
    path = "/v1/" + op
    raw = encode(body)
    conn = None
    try:
        conn = http.client.HTTPSConnection(HOST, port, timeout=TIMEOUT_S if timeout is None else timeout, context=tls)
        conn.request("POST", path, body=raw, headers=headers(secret, path, raw))
        r = conn.getresponse()
        return r.status, _answer(r.read(1 << 20))
    except Exception as e:                                       # refused, a timeout, a TLS refusal, a reset, anything
        return 0, {"error": _net_reason(e)}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _answer(data):
    try:
        out = json.loads(data.decode("utf-8"))
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _net_reason(e):
    """A short, value-free reason. TLS trouble starts with "tls " (the server's certificate not trusted, or the vault
    refusing ours: its alert's name, e.g. TLSV13_ALERT_CERTIFICATE_REQUIRED or TLSV1_ALERT_UNKNOWN_CA)."""
    if isinstance(e, ssl.SSLCertVerificationError):
        return "tls vault certificate not trusted: %s" % str(e.verify_message or "?")[:80]
    if isinstance(e, (ssl.SSLEOFError, ssl.SSLZeroReturnError)):
        return "tls failed: closed by the vault (%s)" % type(e).__name__
    if isinstance(e, ssl.SSLError):
        return "tls failed: %s" % str(e.reason or type(e).__name__)[:60]
    if isinstance(e, ConnectionRefusedError):
        return "connection refused"
    if isinstance(e, (socket.timeout, TimeoutError)) or "timed out" in str(e):
        return "timeout"
    if isinstance(e, (http.client.RemoteDisconnected, ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
        return "connection closed by the vault"
    return type(e).__name__


def _why(status, out):
    if status == 0:
        r = str(out.get("error", "?"))
        return r if r.startswith("tls ") else "vault down: %s" % r
    code = str(out.get("error") or "no code")[:40]
    extra = "".join(" %s=%s" % (k, str(out[k])[:40]) for k in ("field", "why") if k in out)
    return ("refused %d %s%s" if 400 <= status < 500 else "vault error %d %s%s") % (status, code, extra)


def _say(log, text):
    try:
        log(text)
    except Exception:
        pass


# ------------------------------------------------------------------ the dry run of the trail book (never posted)
def preview(markets, prev=None, trades_dir=None, now=None, generated_utc=None, page=None):
    """trail_book_preview.json as a dict: what the feed WOULD post if these markets were on the trail voice. `markets`:
    {symbol: its setups.json entry built on the trail voice}; `prev`: the previous preview (its "state" is this dry
    run's own memory, the same shape as the feed's: track() fills it exactly as it would the real one). Nothing here
    opens a socket. books: {symbol: {"body": the submit_book body or None, "reason": why not}}; intents: the last
    PREVIEW_INTENTS move_stop / close bodies it would have made, oldest first, each with made_utc."""
    now = time.time() if now is None else now
    st = prev.get("state") if isinstance(prev, dict) and isinstance(prev.get("state"), dict) else {}
    st = json.loads(json.dumps(st))
    books = {}
    for sym in ALLOWED:
        m = markets.get(sym) if isinstance(markets, dict) else None
        if not isinstance(m, dict):
            books[sym] = {"body": None, "reason": "no trail entry for this market"}
            continue
        why = track(sym, m, st, trades_dir or "", now)
        if why:
            books[sym] = {"body": None, "reason": why}
            continue
        body, why = build_book(m, m.get("price_bar_utc"), remembered_lead(st, sym, m), force=True,
                               opened_by=remembered_opened_by(st, sym, m, page))
        books[sym] = {"body": body, "reason": why}
    queue = st.get("intents") if isinstance(st.get("intents"), dict) else {}
    keep = sorted(queue.items(), key=lambda kv: kv[1].get("seq", 0))[-PREVIEW_INTENTS:]
    st["intents"] = dict(keep)
    return {"generated_utc": generated_utc or _utc(now), "schema": PREVIEW_SCHEMA,
            "note": "Dry run. What Mind 15 would post for a trail book. Nothing here was sent.",
            "books": books,
            "intents": [dict(it["body"], made_utc=_utc(it.get("made", now)), ok=bool(intent_ok(it["body"])))
                        for _iid, it in keep if isinstance(it.get("body"), dict)],
            "state": st}


def write_preview(markets, out_dir, trades_dir=None, now=None, generated_utc=None):
    """Write the preview beside setups.json (atomic). -> its path. The caller guards it: it never stops a step."""
    path = os.path.join(out_dir, PREVIEW_FILE)
    try:
        with io.open(path, encoding="utf-8") as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        prev = None
    doc = preview(markets, prev, trades_dir=trades_dir or out_dir, now=now, generated_utc=generated_utc)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)
    os.replace(tmp, path)
    return path


# ------------------------------------------------------------------ one pass
def run(setups_path, log=print, environ=None, state_path=None, trades_dir=None, now=None):
    """Send what changed. -> {"books": [symbols sent], "intents": [ids sent]} or None when the feature is off. Never
    raises."""
    env = os.environ if environ is None else environ
    if not (env.get(CONFIG_ENV) or "").strip():
        return None
    try:
        return _run(setups_path, log, env, state_path or STATE_PATH,
                    trades_dir or os.path.dirname(os.path.abspath(setups_path)), time.time() if now is None else now)
    except Exception as e:
        _say(log, "vault: not sent (%s)" % type(e).__name__)
        return {"books": [], "intents": []}


def _run(setups_path, log, env, state_path, trades_dir, now):
    done = {"books": [], "intents": []}
    want = [s.strip().upper() for s in (env.get(SYMBOLS_ENV) or ",".join(ALLOWED)).split(",")]
    syms = [s for s in ALLOWED if s in want]
    if not syms:
        return done
    tag = ",".join(syms)
    try:
        with io.open(setups_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        markets = dict((m.get("symbol"), m) for m in doc["markets"] if isinstance(m, dict))
    except Exception:
        _say(log, "vault: %s not sent (setups.json unreadable)" % tag)
        return done
    st, how = read_state(state_path)
    if how == "unreadable":
        _keep_bad(state_path, now)
    books = {}
    page = read_page(setups_path) if SEND_OPENED_BY else None     # off: the page is not even read
    for sym in syms:
        m = markets.get(sym)
        if m is None:
            _say(log, "vault: %s not sent (not in setups.json)" % sym)
            continue
        if is_trail(m) and not SEND_TRAIL and m.get("side") in ("LONG", "SHORT"):
            # must never happen (the two switches go on together, and a test says so). If it does: the vault cannot
            # read a trail book, so it is told FLAT, loudly, and an earlier setup's exit still goes out.
            _say(log, "vault: ALARM %s is on the trail voice while SEND_TRAIL is off: the vault is told FLAT" % sym)
            m = markets[sym] = dict(m, side="FLAT")
        why = track(sym, m, st, trades_dir, now)
        if why:                                                  # the position is kept as it was and the book waits too:
            _say(log, "vault: %s not sent (exit not queued: %s)" % (sym, why))    # every book sent was tracked first, so
            continue                                             # a close can never land on a newer setup's join
        books[sym] = build_book(m, m.get("price_bar_utc"), remembered_lead(st, sym, m), False,
                                remembered_opened_by(st, sym, m, page))
    memory_alarm(st, markets, syms, how, now, log)
    queue = st.setdefault("intents", {})
    for iid in list(queue):                                      # old finished ones go; stuck ones are given up
        it = queue[iid]
        age = now - float(it.get("made", now))
        if it.get("status") != "pending" and age > INTENT_KEEP_S:
            del queue[iid]
        elif it.get("status") == "pending" and age > INTENT_GIVE_UP_S:
            it["status"] = "expired"
            b = it.get("body") or {}
            _say(log, "vault: %s %s %s not sent (given up after 24 h)" % (b.get("symbol"), b.get("action"), b.get("market")))
    conf, err = load_config(env[CONFIG_ENV].strip())             # read at every step, as are the files it names
    secret = tls = None
    if err is None:
        secret = read_secret(conf["secret_file"])
        err = "secret file unreadable" if secret is None else None
    if err is None:
        tls, err = client_tls(conf["ca"], conf["cert"], conf["key"])
    if err:
        save_state(state_path, st)                               # the exits stay queued for the next step
        _say(log, "vault: %s not sent (%s)" % (tag, err))
        return done
    port = conf["port"]
    # 1. the exits first (each once; retried next step until the vault answers)
    for iid, it in sorted(queue.items(), key=lambda kv: kv[1].get("seq", 0)):
        b = it.get("body")
        if it.get("status") != "pending" or not isinstance(b, dict) or b.get("symbol") not in syms:
            continue
        label = "%s %s %s" % (b.get("symbol"), b.get("action"), b.get("market"))
        if not intent_ok(b):
            it["status"] = "refused"
            it["why"] = "not an allowed exit"                    # kept for the Telegram card
            _say(log, "vault: %s not sent (not an allowed exit)" % label)
            continue
        status, out = post(port, secret, tls, "submit_intent", {"intent": b})
        if status == 200 and out.get("ok"):
            it["status"] = "sent"
            done["intents"].append(iid)
            _say(log, "vault: %s sent (id %s%s)" % (label, iid, ", duplicate" if out.get("duplicate") else ""))
        else:
            if status in (400, 409) or (status == 403 and (".%s." % MS) in iid):
                # the same id and body would always be refused. (The vault of 26 Nov 2026, package f7609091, never
                # answers 403 to a move_stop: "not tighter" and "past the price" are refused per member at signing and
                # never come back here. The 403 case stays as a guard: such an answer must never hold the book.)
                it["status"] = "refused"
                it["why"] = _why(status, out)                    # the vault's code, kept for the Telegram card
            _say(log, "vault: %s not sent (%s)" % (label, _why(status, out)))
    # 2. the books. v5.2.9 (22 Nov 2026): never a market's book while an exit for that market is still unsent. The
    # vault's exits go by symbol, not by setup: an exit that lands AFTER the book of the next setup would close, halve
    # or move the stop of the NEW position (the AI Trading Bot session, from the vault's code). Since the early entry
    # a new setup can follow an ended one in the very next post, so the book waits a step instead; the vault follows a
    # book up to 30 minutes old and the member's resting stop is in place meanwhile. A refused or given-up exit does
    # not hold the book: it will never be sent.
    unsent = set((it.get("body") or {}).get("symbol") for it in queue.values() if it.get("status") == "pending")
    held = st.setdefault("book", {})
    for sym in syms:
        if sym not in books:
            continue
        if sym in unsent:
            _say(log, "vault: %s book held (an exit for it is not sent yet)" % sym)
            continue
        body, why = books[sym]
        if body is None:
            _say(log, "vault: %s not sent (%s)" % (sym, why))
            continue
        b = body["book"]
        content, as_of = _content(b), b["as_of_utc"]
        last = held.get(sym) or {}
        if last.get("as_of"):
            dt = _epoch(as_of) - _epoch(last["as_of"])
            if dt < 0:
                _say(log, "vault: %s not sent (as_of older than the last sent)" % sym)
                continue
            if dt == 0:
                if content != last.get("content"):
                    _say(log, "vault: %s not sent (same as_of, different body)" % sym)
                continue
            if content == last.get("content") and dt < HEARTBEAT_S:
                continue
        status, out = post(port, secret, tls, "submit_book", body)
        if status == 200 and out.get("ok"):
            held[sym] = {"content": content, "as_of": as_of}
            done["books"].append(sym)
            _say(log, "vault: %s %s sent (as_of %s%s)" % (sym, b["side"], as_of, ", duplicate" if out.get("duplicate") else ""))
        else:
            _say(log, "vault: %s not sent (%s)" % (sym, _why(status, out)))
    save_state(state_path, st)
    return done
