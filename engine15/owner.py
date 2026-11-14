# -*- coding: utf-8 -*-
"""owner -- the owner as a data source: the engine ASKS, the owner answers, the answer is graded.

WHY (owner, 10 Nov 2026): "it should be engine to leverage on my intelligence. It should ask
me and get me as data source."

How it works
  * At every session the engine writes one QUESTION for the owner into the journal entry
    (question()): about the next scheduled release when one is near, about the side when
    its own odds are close, about the card that disagrees most when it has a side.
  * The owner answers with a view: a side, a conviction and how long the view stands.
        py -3 -m engine15 tell BTC long 0.7 --hours 24 "CPI came in soft"
        py -3 -m engine15 tell ETH short 0.4
        py -3 -m engine15 tell BTC none            (withdraw the view)
    Every answer is kept in data/owner_views.csv with the time it was given.
  * The view becomes the reading `owner_view` (side x conviction, from the moment it was
    given until it expires) and its own voice, "The owner's view". Like every voice it is
    graded on each call and earns or loses trust on its record. It starts with no history,
    so it says nothing until the owner has answered and those answers have been graded.
"""
import os
import time

import numpy as np
import pandas as pd

from .config import DATA_DIR

PATH = os.path.join(DATA_DIR, "owner_views.csv")
COLS = ["ts_ms", "asset", "view", "conviction", "hours", "note"]
SIDES = {"long": 1.0, "up": 1.0, "buy": 1.0, "short": -1.0, "down": -1.0, "sell": -1.0, "none": 0.0, "flat": 0.0}
FEATURES = ["owner_view"]
ALIASES = {"GOLD": "XAUUSD", "XAU": "XAUUSD", "SILVER": "XAGUSD", "XAG": "XAGUSD", "JPY": "USDJPY",
           "YEN": "USDJPY", "SP500": "SPX", "S&P": "SPX", "SPX500": "SPX", "SNP": "SPX", "ES": "SPX",
           "OIL": "WTI", "CRUDE": "WTI", "CL": "WTI", "USOIL": "WTI", "UKOIL": "BRENT", "BZ": "BRENT"}


SHORT_NAMES = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "gold", "XAGUSD": "silver", "USDJPY": "USDJPY", "SPX": "the S&P 500",
               "WTI": "WTI oil", "BRENT": "Brent oil"}


def asset_id(asset):
    """BTC -> BTCUSDT, gold -> XAUUSD, spx -> SPX: whatever the owner types, the engine's own id."""
    u = asset.upper()
    if u in ALIASES:
        return ALIASES[u]
    if u in ("XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT") or u.endswith("USDT"):
        return u
    return u + "USDT"


def load(path=None):
    p = path or PATH
    if not os.path.exists(p):
        return pd.DataFrame(columns=COLS)
    return pd.read_csv(p, dtype={"note": str}).fillna({"note": ""})


def tell(asset, side, conviction=0.5, hours=24.0, note="", now_ms=None, path=None):
    """Record the owner's view. -> the row written."""
    asset = asset_id(asset)
    if side.lower() not in SIDES:
        raise ValueError("side must be one of: %s" % ", ".join(sorted(SIDES)))
    row = {"ts_ms": int(now_ms or time.time() * 1000), "asset": asset, "view": SIDES[side.lower()],
           "conviction": float(min(max(conviction, 0.0), 1.0)), "hours": float(hours), "note": note.replace("\n", " ")}
    d = pd.concat([load(path), pd.DataFrame([row])], ignore_index=True)[COLS]
    p = path or PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    d.to_csv(tmp, index=False)
    os.replace(tmp, p)
    return row


def features(index15, asset, bar_ms=900000, path=None):
    """-> frame with `owner_view` on the 15m index: the latest view given at or before each
    close and not yet expired, as side x conviction; 0.0 where the owner has said nothing."""
    out = pd.DataFrame({"owner_view": 0.0}, index=index15)
    d = load(path)
    d = d[d.asset == asset].sort_values("ts_ms")
    if not len(d):
        return out
    close_ms = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + bar_ms
    k = np.searchsorted(d.ts_ms.values, close_ms, side="right") - 1          # the last view given by this close
    has = k >= 0
    kk = np.maximum(k, 0)
    alive = has & (close_ms < d.ts_ms.values[kk] + d.hours.values[kk] * 3600000.0)
    out["owner_view"] = np.where(alive, d.view.values[kk] * d.conviction.values[kk], 0.0)
    return out


def standing(asset, now_ms=None, path=None):
    """The owner's view on `asset` that is in force now, or None."""
    d = load(path)
    d = d[d.asset == asset].sort_values("ts_ms")
    now_ms = now_ms or time.time() * 1000
    d = d[d.ts_ms <= now_ms]
    if not len(d):
        return None
    r = d.iloc[-1]
    if r.view == 0 or now_ms >= r.ts_ms + r.hours * 3600000.0:
        return None
    return {"side": "LONG" if r.view > 0 else "SHORT", "conviction": float(r.conviction), "note": r.note,
            "given_utc": str(pd.Timestamp(int(r.ts_ms), unit="ms", tz="UTC"))[:16],
            "hours_left": round((r.ts_ms + r.hours * 3600000.0 - now_ms) / 3600000.0, 1)}


def question(e):
    """One question for the owner from a journal entry: where the owner's judgement would add the
    most to what the engine can read for itself. Since 11 Nov 2026 (owner: "more versatile ability to
    ask") the question comes from engine15/questions.py: levels, stops and targets, trend conflicts,
    squeezes, liquidity, releases, card conflicts, rotating so the same kind is not asked again soon.
    The kind is left in e["question_kind"]. The old rules below are the fallback."""
    try:
        from . import questions
        kind, q = questions.ask(e)
        if q:
            e["question_kind"] = kind
            return q
    except Exception:
        pass
    coin, edge = SHORT_NAMES.get(e["asset"], e["asset"][:3]), e.get("edge_pts")
    nx = e.get("econ_next")
    if nx and 0 <= nx["hours_away"] <= 6:
        return "US %s prints in %.0f hours. Do you expect it to push %s up or down, and how sure are you?" % (
            nx["titles"][0], max(nx["hours_away"], 1), coin)
    if edge is None:
        return "I am still learning and have no odds for %s yet. Which side do you favour for the next 24 hours?" % coin
    if abs(edge) < 5:
        return "My odds on %s are close to even (%.1f pts). Which side do you favour for the next 24 hours, and why?" % (coin, abs(edge))
    side = "long" if edge > 0 else "short"
    against = [c for c in e.get("cards", []) if c.get("lean") is not None and c["lean"] * edge < 0]
    if against:
        worst = max(against, key=lambda c: abs(c["lean"]))
        if abs(worst["lean"]) >= 8:
            return "I lean %s on %s, but %s points the other way (%.0f pts). Which do you believe here?" % (
                side, coin, worst["card"], abs(worst["lean"]))
    return "I lean %s on %s with an edge of %.1f pts. Do you see something I cannot read: a headline, a flow, a level?" % (
        side, coin, abs(edge))


# ------------------------------------------------------------------ the PIN and the audit trail
# WHY (owner, 10 Nov 2026): the page is public, so only people who know the PIN may answer;
# and every question and every answer is kept. The PIN is never stored or logged: only a
# salted, stretched hash of it (PIN_FILE). The check belongs on the SERVER side of whatever
# takes answers; a check written into a public page's own script protects nothing.
PIN_FILE = os.path.join(DATA_DIR, "owner_pin.json")
AUDIT = os.path.join(DATA_DIR, "owner_audit.jsonl")
MAX_WRONG, LOCK_MINUTES = 5, 15            # five wrong PINs lock answering for 15 minutes


def _stretch(pin, salt, rounds):
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"), bytes.fromhex(salt), rounds).hex()


def audit(kind, path=None, **fields):
    """Append one row to the audit trail. Rows are never edited or removed."""
    import json
    row = dict({"t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": kind}, **fields)
    p = path or AUDIT
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def read_audit(path=None):
    import json
    p = path or AUDIT
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def set_pin(pin, pin_file=None, audit_path=None):
    import json
    salt = os.urandom(16).hex()
    rec = {"salt": salt, "rounds": 200000, "hash": _stretch(pin, salt, 200000)}
    p = pin_file or PIN_FILE
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    audit("pin_set", audit_path, digits=len(str(pin)))


def pin_is_set(pin_file=None):
    return os.path.exists(pin_file or PIN_FILE)


def check_pin(pin, pin_file=None, audit_path=None):
    """-> (ok, reason). Wrong tries are counted from the audit trail; too many lock the door."""
    import hmac
    import json
    p = pin_file or PIN_FILE
    if not os.path.exists(p):
        return False, "no PIN has been set"
    since = time.time() - LOCK_MINUTES * 60
    recent = [r for r in read_audit(audit_path) if r["kind"] == "rejected" and r.get("reason") == "wrong PIN"
              and time.mktime(time.strptime(r["t_utc"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone >= since]
    if len(recent) >= MAX_WRONG:
        return False, "locked: too many wrong PINs, try again in %d minutes" % LOCK_MINUTES
    with open(p, encoding="utf-8") as fh:
        rec = json.load(fh)
    if hmac.compare_digest(_stretch(pin, rec["salt"], rec["rounds"]), rec["hash"]):
        return True, "ok"
    return False, "wrong PIN"


def log_question(e, path=None):
    """Record the question the engine asked in this journal entry (once per coin and session)."""
    if not e.get("question"):
        return None
    for r in reversed(read_audit(path)[-40:]):
        if r["kind"] == "question" and r.get("session") == e["time"] and r.get("asset") == e["asset"]:
            return None
    return audit("question", path, session=e["time"], asset=e["asset"], question=e["question"],
                 engine_side=e.get("position"), edge_pts=e.get("edge_pts"), question_kind=e.get("question_kind"))


def submit(pin, who, asset, side, conviction=0.5, hours=24.0, note="", views_path=None, pin_file=None, audit_path=None):
    """An answer from someone who knows the PIN. Accepted -> the view is recorded and the trail
    says who answered which question; refused -> the trail says so (never the PIN tried)."""
    asset_u = asset_id(asset)
    ok, reason = check_pin(pin, pin_file, audit_path)
    if not ok:
        audit("rejected", audit_path, who=str(who)[:40], asset=asset_u, reason=reason)
        raise PermissionError(reason)
    asked = next((r for r in reversed(read_audit(audit_path)) if r["kind"] == "question" and r.get("asset") == asset_u), None)
    row = tell(asset_u, side, conviction, hours, note, path=views_path)
    audit("answer", audit_path, who=str(who)[:40], asset=asset_u, side=side.lower(), conviction=row["conviction"],
          hours=row["hours"], note=row["note"][:300], question=asked["question"] if asked else None,
          question_session=asked["session"] if asked else None)
    return row


def trail(limit=30, path=None):
    """The public part of the audit trail, newest first: questions asked and answers accepted
    (refused attempts are counted, not listed)."""
    rows = read_audit(path)
    keep = [r for r in rows if r["kind"] in ("question", "answer")][-limit:][::-1]
    return {"rows": keep, "refused_attempts": sum(1 for r in rows if r["kind"] == "rejected")}


def main(argv):
    """py -3 -m engine15 tell ASSET SIDE [CONVICTION] [NOTE] [--hours N] --pin PIN [--who NAME]
       py -3 -m engine15 pin NEWPIN          set (or change) the PIN that answers must carry"""
    def opt(name, default=None):
        nonlocal argv
        if name in argv:
            k = argv.index(name)
            v = argv[k + 1]
            argv = argv[:k] + argv[k + 2:]
            return v
        return default
    hours, pin, who = float(opt("--hours", 24.0)), opt("--pin"), opt("--who", "owner")
    if len(argv) < 2:
        print(main.__doc__)
        return
    conviction, rest = 0.5, argv[2:]
    if rest:
        try:
            conviction, rest = float(rest[0]), rest[1:]
        except ValueError:
            pass
    if not pin_is_set():
        print("No PIN is set yet. Set one first:  py -3 -m engine15 pin NEWPIN")
        return
    try:
        print("recorded:", submit(pin or "", who, argv[0], argv[1], conviction, hours, " ".join(rest)))
    except PermissionError as err:
        print("not recorded:", err)
