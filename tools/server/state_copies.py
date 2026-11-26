# -*- coding: utf-8 -*-
"""Hourly copies of the engine's memory on the box, and the tool that puts one back (20 Nov 2026; docs/RESTORE.md).

The vault feed's memory (data/vault_feed_state.json) says which open setup the feed saw inside its entry window and which
exit instructions are still waiting; the shadow books' memory (data/shadow_state.json) holds the book the VIP vault
copies. Before this, both were copied once a day, to the laptop only. Losing the first while a setup is open means no
exit is sent for it. Since 25 Nov 2026 the capitulation-long books' memory (data/capit_long_state.json, playbook9, paper
only) is copied too: lost, those books start flat and forget an open rebound long.

    python tools/server/state_copies.py copy               one copy of FILES into data/state_copies/<UTC stamp>/, each
                                                           checked to be readable JSON; the oldest beyond KEEP removed.
                                                           Run by the timer mind15-state-copy (hourly, minute 8).
    python tools/server/state_copies.py list               the copies, newest first, with what each holds
    python tools/server/state_copies.py show STAMP         that copy beside the files in use now
    python tools/server/state_copies.py restore STAMP [FILE ...]
                                                           puts FILE(s) back (default: vault_feed_state.json only).
                                                           REFUSES while the engine service is active. The file in use
                                                           is kept as <file>.before-restore-<stamp of now>.

Standard library only; it never imports the engine, reads no secret and no env file, and writes only under data/.
On the box run it as the engine's user:  sudo -u mind15 /data/venv/bin/python tools/server/state_copies.py ...
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "data")
COPIES = "state_copies"
FILES = ("vault_feed_state.json", "shadow_state.json", "live_state.json", "signals_state.json",
         "capit_long_state.json",        # the capitulation-long books and the retest zone (H115; owner, 25 Nov 2026)
         "setups_voice_state.json")      # which book speaks for each market (setups_voice.py, 26 Nov 2026); it exists
                                         # only once a market has left the targets voice
DEFAULT_RESTORE = ("vault_feed_state.json",)
KEEP = 48                                # two days of hourly copies
SERVICE = "mind15"
STAMP_RE = re.compile(r"^\d{8}T\d{6}Z\Z")
MANIFEST = "MANIFEST.json"
VAULT_MARKETS = ("BTCUSDT", "ETHUSDT")
BOOK = "b_targets"                       # the book the vault copies (engine15/setups.py BOOK)


def stamp(now=None):
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(time.time() if now is None else now))


def _utc(ms):
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) // 1000))
    except Exception:
        return None


def describe(name, doc):
    """A few plain facts about a state file, for the manifest and for `show`. Never raises."""
    try:
        if name == "vault_feed_state.json":
            pos = doc.get("pos") if isinstance(doc.get("pos"), dict) else {}
            intents = doc.get("intents") if isinstance(doc.get("intents"), dict) else {}
            alarm = (doc.get("alarm") or {}).get("memory_lost") if isinstance(doc.get("alarm"), dict) else None
            return {"positions": dict((s, None if not isinstance(p, dict) else
                                       {"side": p.get("side"), "opened_utc": p.get("opened_utc"),
                                        "t1_taken": bool(p.get("t1_taken")), "exits_will_be_sent": bool(p.get("eligible"))})
                                      for s, p in sorted(pos.items())),
                    "exits_waiting": sorted(k for k, v in intents.items() if isinstance(v, dict) and v.get("status") == "pending"),
                    "books_last_sent": dict((s, (b or {}).get("as_of")) for s, b in sorted((doc.get("book") or {}).items())),
                    "memory_lost_alarm": sorted(alarm) if isinstance(alarm, dict) else []}
        if name == "shadow_state.json":
            books = (doc.get("books") or {}).get(BOOK) or {}
            out = {}
            for s in VAULT_MARKETS:
                b = books.get(s) or {}
                out[s] = {"side": {1: "LONG", -1: "SHORT"}.get(b.get("pos"), "FLAT"),
                          "opened_utc": _utc(b.get("t_in_ms")) if b.get("pos") else None,
                          "t1_taken": bool(b.get("t1_hit")), "entry": b.get("entry") if b.get("pos") else None}
            last = ((doc.get("groups") or {}).get("crypto") or {}).get("last_ms")
            return {"setups_book": out, "crypto_last_bar_utc": _utc(last) if last else None}
        if name == "setups_voice_state.json":
            marks = doc.get("markets") if isinstance(doc.get("markets"), dict) else {}
            return {"voices": dict((s, {"rule": (e or {}).get("rule"), "from_utc": (e or {}).get("from_utc"),
                                        "pending": bool((e or {}).get("pending"))})
                                   for s, e in sorted(marks.items()) if isinstance(e, dict))}
        if name == "capit_long_state.json":
            books = doc.get("books") if isinstance(doc.get("books"), dict) else {}
            out = {}
            for bk in sorted(books):
                for s in VAULT_MARKETS:
                    slot = (books.get(bk) or {}).get(s) or {}
                    out["%s %s" % (bk, s)] = ("OPEN" if slot.get("open") else "WAITING" if slot.get("pending") else "none")
            return {"rebound_longs": out, "closed": len(doc.get("closed") or []),
                    "started_utc": doc.get("started_utc")}
    except Exception:
        pass
    return {}


def _read_json(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, json.loads(raw.decode("utf-8"))


def copies(data_dir=DATA_DIR):
    """The stamps that hold a manifest, newest first."""
    root = os.path.join(data_dir, COPIES)
    try:
        names = os.listdir(root)
    except OSError:
        return []
    return sorted((n for n in names if STAMP_RE.match(n) and os.path.isfile(os.path.join(root, n, MANIFEST))), reverse=True)


def copy(data_dir=DATA_DIR, keep=KEEP, now=None, log=print):
    """One copy. -> the stamp, or None when no state file could be copied. A file that is not readable JSON is NOT
    copied (the manifest says so): a copy is only ever something that can be put back."""
    st = stamp(now)
    root = os.path.join(data_dir, COPIES)
    tmp = os.path.join(root, ".tmp-" + st)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    man = {"stamp": st, "files": {}, "skipped": {}}
    for name in FILES:
        src = os.path.join(data_dir, name)
        if not os.path.isfile(src):
            man["skipped"][name] = "not there"
            continue
        try:
            raw, doc = _read_json(src)
        except Exception as e:
            man["skipped"][name] = "not readable JSON (%s)" % type(e).__name__
            log("state copy %s: %s NOT copied (%s)" % (st, name, man["skipped"][name]))
            continue
        with open(os.path.join(tmp, name), "wb") as fh:
            fh.write(raw)
        man["files"][name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                              "written_utc": _utc(os.path.getmtime(src) * 1000), "holds": describe(name, doc)}
    if not man["files"]:
        shutil.rmtree(tmp, ignore_errors=True)
        log("state copy %s: nothing to copy" % st)
        return None
    with open(os.path.join(tmp, MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, sort_keys=True)
    dest = os.path.join(root, st)
    shutil.rmtree(dest, ignore_errors=True)                      # the same second twice: the newer one stands
    os.replace(tmp, dest)
    for old in copies(data_dir)[max(int(keep), 1):]:
        shutil.rmtree(os.path.join(root, old), ignore_errors=True)
    log("state copy %s: %s" % (st, ", ".join(sorted(man["files"]))))
    return st


def manifest(data_dir, st):
    with open(os.path.join(data_dir, COPIES, st, MANIFEST), encoding="utf-8") as fh:
        return json.load(fh)


def show(data_dir, st, log=print):
    """The copy beside what is in use now, file by file."""
    man = manifest(data_dir, st)
    for name in FILES:
        held = (man["files"].get(name) or {})
        log("== %s" % name)
        log("   copy %s (written %s): %s" % (st, held.get("written_utc"), json.dumps(held.get("holds"), sort_keys=True)
                                               if name in man["files"] else "NOT IN THIS COPY (%s)" % man["skipped"].get(name)))
        try:
            raw, doc = _read_json(os.path.join(data_dir, name))
            same = held.get("sha256") == hashlib.sha256(raw).hexdigest()
            log("   in use now%s: %s" % (" (identical)" if same else "", json.dumps(describe(name, doc), sort_keys=True)))
        except Exception as e:
            log("   in use now: MISSING OR UNREADABLE (%s)" % type(e).__name__)


def service_active(service=SERVICE):
    """True / False from systemctl; None where there is no systemctl (the laptop)."""
    try:
        r = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    return r.stdout.strip() == "active"


def restore(data_dir, st, files=DEFAULT_RESTORE, now=None, log=print, active=service_active):
    """Put files of copy `st` back. -> the files restored. Raises ValueError (nothing changed) when the engine is
    running, the stamp or a file name is unknown, or the copy does not match its manifest."""
    if not STAMP_RE.match(str(st)) or st not in copies(data_dir):
        raise ValueError("no such copy: %s" % st)
    files = tuple(files) or DEFAULT_RESTORE
    bad = [f for f in files if f not in FILES]
    if bad:
        raise ValueError("not a state file: %s" % ", ".join(bad))
    if active() is True:
        raise ValueError("the engine service is running: stop it between two steps first (docs/RESTORE.md)")
    man = manifest(data_dir, st)
    todo = []
    for name in files:
        held = man["files"].get(name)
        if not held:
            raise ValueError("%s is not in copy %s (%s)" % (name, st, man["skipped"].get(name)))
        raw, _doc = _read_json(os.path.join(data_dir, COPIES, st, name))
        if hashlib.sha256(raw).hexdigest() != held["sha256"]:
            raise ValueError("%s in copy %s does not match its manifest" % (name, st))
        todo.append((name, raw))
    tag = stamp(now)
    for name, raw in todo:
        path = os.path.join(data_dir, name)
        if os.path.exists(path):
            shutil.copy2(path, "%s.before-restore-%s" % (path, tag))
        tmp = path + ".restore.tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)
        log("restored %s from copy %s (the file that was in use: %s.before-restore-%s)" % (name, st, name, tag))
    return [n for n, _ in todo]


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "copy":
            return 0 if copy() else 1
        if cmd == "list":
            for st in copies():
                m = manifest(DATA_DIR, st)
                feed = (m["files"].get("vault_feed_state.json") or {}).get("holds") or {}
                print("%s  files: %s  feed positions: %s  exits waiting: %d" % (
                    st, ",".join(sorted(f.split("_state")[0] for f in m["files"])),
                    json.dumps(dict((s, (p or {}).get("side")) for s, p in (feed.get("positions") or {}).items()), sort_keys=True),
                    len(feed.get("exits_waiting") or [])))
            return 0
        if cmd == "show" and len(argv) == 3:
            show(DATA_DIR, argv[2])
            return 0
        if cmd == "restore" and len(argv) >= 3:
            restore(DATA_DIR, argv[2], argv[3:])
            show(DATA_DIR, argv[2])
            return 0
    except (ValueError, OSError) as e:
        print("STOP: %s" % e)
        return 2
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
