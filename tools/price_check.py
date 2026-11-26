# -*- coding: utf-8 -*-
"""price_check -- is every market's price on the box fresh and right? READ ONLY (owner, 26 Nov 2026: "Create a every 8
hours check daily on pricing so the issue of no data wont gone off notice so long like today").

On 26 Nov 2026 (US Thanksgiving) the bar feed served nothing for gold, silver, WTI and Brent for more than four hours
while the markets traded, and nobody was told. This asks the box, for each of the eight markets:

    1. Is the market open now, by the engine's own calendar?
    2. How old is the engine's last bar (setups.json: price_bar_utc)?           open and older than STALE_MIN -> PROBLEM
    3. Does the engine's price agree with an independent quote taken right now?   off by more than OFF_PCT   -> PROBLEM
       (BTC and ETH: Binance spot; the others: the feed's own live quote, which kept moving on 26 Nov while its bars
       had stopped. A quote older than QUOTE_OLD_MIN is not used.)
and for the engine itself: both services running, and the last step no older than STEP_OLD_MIN.
It also says when the second bar source (engine15/bridge.py) carried a market in the last hours: that is a NOTE, not a
problem (the price is fresh), but it means the usual feed was down.

    py -3 -X utf8 tools/price_check.py            prints one line per market and a verdict; exit code 1 on any PROBLEM

It changes nothing on the box: it reads setups.json, the calendar, the log's tail and data/bridge_bars.csv, and makes one
quote request per market. Run from the laptop (it uses the same ssh key as tools/deploy.sh).
"""
import os
import subprocess
import sys

BOX = os.environ.get("MIND15_BOX", "ec2-user@13.251.40.113")
KEY = os.environ.get("MIND15_BOX_KEY", os.path.join(os.path.expanduser("~"), ".ssh", "minds15.pem"))

REMOTE = r'''
import csv, json, os, subprocess, sys, time
sys.path.insert(0, "/data/mind15")
STALE_MIN, OFF_PCT, QUOTE_OLD_MIN, STEP_OLD_MIN, BRIDGE_H = 45, 1.0, 30, 25, 8
import calendar as _cal
import pandas as pd
from engine15 import extdata, market_calendar
from engine15.config import CFG
now = time.time()
ep = lambda s: _cal.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
problems, notes, lines = [], [], []

def quote(sym):
    """(price, age in minutes) from an independent source, or (None, why)."""
    try:
        if sym in CFG.get("crypto", ()):
            import requests
            r = requests.get("https://data-api.binance.vision/api/v3/ticker/price", params={"symbol": sym}, timeout=15)
            return float(r.json()["price"]), 0.0
        m = extdata.fetch_chart(extdata.MARKETS[sym]["yahoo"], "1d")["chart"]["result"][0]["meta"]
        return float(m["regularMarketPrice"]), (now - float(m["regularMarketTime"])) / 60.0
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:60])

try:
    doc = json.load(open("/data/mind15/out/live/setups.json"))
    gen_age = (now - ep(doc["generated_utc"])) / 60.0
    if gen_age > STEP_OLD_MIN:
        problems.append("the Setups file is %.0f minutes old" % gen_age)
    bridged = {}
    try:
        for r in csv.DictReader(open("/data/mind15/data/bridge_bars.csv")):
            if now - ep(r["t_utc"]) < BRIDGE_H * 3600:
                b = bridged.setdefault(r["asset"], {"bars": 0, "source": r["source"], "last": r["t_utc"]})
                b["bars"] += int(r["bars"]); b["last"] = r["t_utc"]
    except (OSError, KeyError, ValueError):
        pass
    for m in doc["markets"]:
        sym = m["symbol"]
        crypto = sym in CFG.get("crypto", ())
        is_open = True if crypto else bool(market_calendar.is_open(sym, pd.Timestamp(int(now * 1000), unit="ms", tz="UTC")))
        bar_age = (now - ep(m["price_bar_utc"])) / 60.0 if m.get("price_bar_utc") else None
        q, q_age = quote(sym)
        off = None if (q is None or not m.get("price")) else (float(m["price"]) / q - 1.0) * 100.0
        word = "ok"
        if is_open and (bar_age is None or bar_age > STALE_MIN):
            word = "PROBLEM"
            problems.append("%s: no new bar for %s minutes while the market is open" % (sym, "?" if bar_age is None else "%.0f" % bar_age))
        if is_open and q is not None and q_age <= QUOTE_OLD_MIN and off is not None and abs(off) > OFF_PCT:
            word = "PROBLEM"
            problems.append("%s: the engine's price %s is %.2f%% off the live quote %s" % (sym, m["price"], off, q))
        if is_open and q is None:
            notes.append("%s: no independent quote (%s)" % (sym, q_age))
        if sym in bridged:
            b = bridged[sym]
            notes.append("%s: %d bars came from the second source (%s) in the last %d hours, the last at %s: the usual feed "
                         "was down" % (sym, b["bars"], b["source"], BRIDGE_H, b["last"][11:16]))
        lines.append("%-8s %-7s %-6s price %-10s bar %-11s age %-5s quote %-10s (%s) off %s" % (
            sym, word, "open" if is_open else "closed", m.get("price"), (m.get("price_bar_utc") or "?")[5:16].replace("T", " "),
            "?" if bar_age is None else "%.0fm" % bar_age, "-" if q is None else q,
            "-" if q is None else "%.0fm old" % q_age, "-" if off is None else "%+.2f%%" % off))
except Exception as e:
    problems.append("the check could not read the box's files (%s: %s)" % (type(e).__name__, e))
try:
    for unit in ("mind15", "mind15-telegram"):
        s = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True).stdout.strip()
        if s != "active":
            problems.append("service %s is %s" % (unit, s or "unknown"))
    age = (now - os.path.getmtime("/data/mind15/live.log")) / 60.0
    if age > STEP_OLD_MIN:
        problems.append("the engine wrote no log line for %.0f minutes" % age)
    tail = subprocess.run(["tail", "-400", "/data/mind15/live.log"], capture_output=True, text=True).stdout.splitlines()
    failed = [x for x in tail if "STEP FAILED" in x or "ALARM" in x]
    if failed:
        problems.append("the log's last 400 lines hold %d STEP FAILED / ALARM lines, the last: %s" % (len(failed), failed[-1][:140]))
except Exception as e:
    notes.append("the services could not be asked (%s)" % type(e).__name__)
print("PRICE CHECK %s UTC" % hm(now))
for x in lines: print(x)
for x in notes: print("NOTE    " + x)
for x in problems: print("PROBLEM " + x)
print("VERDICT: %s" % ("%d PROBLEM(S)" % len(problems) if problems else "all prices fresh"))
sys.exit(1 if problems else 0)
'''


def main():
    cmd = ["ssh", "-o", "ConnectTimeout=20", "-o", "LogLevel=ERROR", "-i", KEY, BOX,
           "cd /data/mind15 && nice /data/venv/bin/python -"]
    try:
        r = subprocess.run(cmd, input=REMOTE, capture_output=True, text=True, timeout=240, encoding="utf-8")
    except Exception as e:
        print("PROBLEM the box could not be reached (%s: %s)\nVERDICT: 1 PROBLEM(S)" % (type(e).__name__, e))
        return 1
    out = (r.stdout or "").strip()
    if "VERDICT:" not in out:
        print(out)
        print("PROBLEM the check did not finish on the box (exit %s): %s\nVERDICT: 1 PROBLEM(S)" % (
            r.returncode, (r.stderr or "").strip()[-300:]))
        return 1
    print(out)
    return 1 if "PROBLEM" in out.split("VERDICT:")[-1] else 0


if __name__ == "__main__":
    sys.exit(main())
