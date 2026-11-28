# -*- coding: utf-8 -*-
"""trail_check -- read-only check of the trail voice on BTC and ETH (28 Nov 2026; owner's task list, item 6: "check our
side of the first stop move"). For each coin on the box:

    1. which book speaks (data/setups_voice_state.json) and the setup the Setups file shows (side, entry, stop, price,
       trail_active, trail_from);
    2. every move_stop the vault feed made for THAT setup (intent id <SYM>.<opened>.ms.<DDHHMM>, data/vault_feed_state.json)
       with its stop and status, and the "stop moved" lines of the signals log (data/signals_log.jsonl);
    3. PROBLEM when a move_stop for the setup was refused or given up, or when the Setups stop is tighter than the stop
       the setup opened with and no move_stop to that stop has been sent (pending for a step is a NOTE).

    py -3 -X utf8 tools/trail_check.py            exit code 1 on any PROBLEM

It changes nothing on the box (three file reads and the log's tail). Same ssh key as tools/deploy.sh.
"""
import os
import subprocess
import sys

BOX = os.environ.get("MIND15_BOX", "ec2-user@13.251.40.113")
KEY = os.environ.get("MIND15_BOX_KEY", os.path.join(os.path.expanduser("~"), ".ssh", "minds15.pem"))

REMOTE = r'''
import json, sys
from decimal import Decimal
problems, notes = [], []
def load(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d
voice = (load("data/setups_voice_state.json", {}) or {}).get("markets") or {}
setups = load("out/live/setups.json", {}) or {}
feed = load("data/vault_feed_state.json", {}) or {}
intents = feed.get("intents") or {}
sig = []
try:
    for line in open("data/signals_log.jsonl", encoding="utf-8"):
        try:
            sig.append(json.loads(line))
        except ValueError:
            pass
except OSError:
    pass
def compact(t):
    return (t or "").replace("-", "").replace(":", "")
first_stop = {}
for r in sig:                                     # the stop each signal opened with (its first line with a stop)
    k = (r.get("symbol"), r.get("opened_utc") or r.get("entry_utc"))
    if r.get("stop") is not None and k not in first_stop:
        first_stop[k] = r.get("stop")
print("TRAIL CHECK", (setups.get("generated_utc") or "?")[5:16].replace("T", " "), "UTC")
for m in setups.get("markets") or []:
    sym = m.get("symbol")
    if sym not in ("BTCUSDT", "ETHUSDT"):
        continue
    v = voice.get(sym) or {}
    print("%s voice %s%s" % (sym, v.get("rule"), " (pending: waits for the setup of %s)" % v.get("wait") if v.get("pending") else
                             " since %s" % (v.get("from_utc") or "?")[5:16].replace("T", " ")))
    if m.get("exit_rule") != "trail":
        print("   setup %s on the targets voice: nothing to check" % m.get("side"))
        continue
    if m.get("side") not in ("LONG", "SHORT"):
        print("   FLAT on the trail voice: nothing to check")
        continue
    side, opened, stop = m["side"], m.get("opened_utc"), m.get("stop")
    print("   %s entry %s stop %s price %s trail_active %s trail_from %s opened %s" % (
        side, m.get("entry"), stop, m.get("price"), m.get("trail_active"), m.get("trail_from"), (opened or "")[5:16]))
    pre = "%s.%s.ms." % (sym, compact(opened))
    mine = sorted((k, x) for k, x in intents.items() if k.startswith(pre))
    for k, x in mine:
        b = x.get("body") or {}
        print("   move_stop %s stop %s side %s status %s" % (k.rsplit(".", 1)[-1], b.get("stop_price"), b.get("side"), x.get("status")))
        if x.get("status") in ("refused", "expired"):
            problems.append("%s: move_stop %s was %s" % (sym, k, x.get("status")))
    moves = [r for r in sig if r.get("symbol") == sym and r.get("type") == "stop_moved"
             and (r.get("opened_utc") or r.get("entry_utc")) in (None, opened)]
    for r in moves[-5:]:
        print("   card: stop moved (%s) to %s at %s" % (r.get("kind"), r.get("stop"), (r.get("utc") or r.get("bar_utc") or "")[5:16]))
    if not mine:
        print("   no move_stop yet%s" % (" (the trail is not armed: it arms at %s)" % m.get("trail_from") if not m.get("trail_active") else ""))
    try:
        sgn = 1 if side == "LONG" else -1
        sent = [Decimal(str((x.get("body") or {}).get("stop_price"))) for k, x in mine if x.get("status") == "sent"]
        waiting = [Decimal(str((x.get("body") or {}).get("stop_price"))) for k, x in mine if x.get("status") == "pending"]
        s = Decimal(str(stop))
        if mine or m.get("trail_active"):
            if not sent and not waiting and m.get("trail_active"):
                problems.append("%s: the trail is armed (stop %s) and no move_stop has been made" % (sym, stop))
            elif sent and sgn * (s - max(sent, key=lambda z: sgn * z)) > 0:
                if any(w == s for w in waiting):
                    notes.append("%s: the move to %s is pending (sent next step)" % (sym, stop))
                else:
                    problems.append("%s: the Setups stop %s is tighter than the last stop sent (%s)" % (
                        sym, stop, max(sent, key=lambda z: sgn * z)))
    except Exception as e:
        notes.append("%s: stops could not be compared (%s)" % (sym, type(e).__name__))
for n in notes:
    print("NOTE   ", n)
for p in problems:
    print("PROBLEM", p)
print("VERDICT:", "%d PROBLEM(S)" % len(problems) if problems else "trail side as expected")
sys.exit(1 if problems else 0)
'''


def main():
    cmd = ["ssh", "-o", "ConnectTimeout=20", "-o", "LogLevel=ERROR", "-i", KEY, BOX,
           "cd /data/mind15 && nice /data/venv/bin/python -"]
    try:
        r = subprocess.run(cmd, input=REMOTE, capture_output=True, text=True, timeout=120, encoding="utf-8")
    except Exception as e:
        print("PROBLEM the box could not be reached (%s: %s)\nVERDICT: 1 PROBLEM(S)" % (type(e).__name__, e))
        return 1
    out = (r.stdout or "").strip()
    print(out)
    if "VERDICT:" not in out:
        print("PROBLEM the check did not finish on the box (exit %s): %s\nVERDICT: 1 PROBLEM(S)" % (
            r.returncode, (r.stderr or "").strip()[-300:]))
        return 1
    return 1 if "PROBLEM" in out.split("VERDICT:")[-1] else 0


if __name__ == "__main__":
    sys.exit(main())
