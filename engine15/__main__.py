# -*- coding: utf-8 -*-
"""python -m engine15 <command>   (run from the project folder; PAPER ONLY)

  update              fetch every 15m bar closed since the last stored one, funding, run the data gates
  backtest            replay all history: the engine's warm-up and first post-mortem material (out/replay/)
  step                one live step now: sources -> think -> decide -> journal -> page.json
  live                step a little after every 15-minute close, until stopped
  journal DATE        write one day of the replay as a journal file (YYYY-MM-DD)
  ask ...             now | why ETH | cards BTC | today | learning   (answers from the journal)
  chat                a free conversation (needs the anthropic package and ANTHROPIC_API_KEY)
  postmortem ...      what each reading said and what happened next (see engine15/postmortem.py)
  tell ASSET SIDE ..  answer the engine with your own view: tell BTC long 0.7 "note" --pin PIN --who NAME
  pin NEWPIN          set the PIN that answers must carry (only its hash is stored)
  shadow              the paper shadow books of registered hypotheses (H1: CPI follow-through)
  scorecard           grade every trade on direction, entry, speed, exit and risk (engine15/scorecard.py)
  kronos-backfill     import the estate's Kronos forecast ledger as live reads
"""
import json
import sys


def main(argv):
    cmd = argv[0] if argv else "help"
    if cmd == "update":
        from . import data
        from .config import CFG
        for asset in CFG["assets"]:
            df, n = data.update(asset, log=print)
            print(asset, "+%d bars" % n, json.dumps(data.gates(df)))
            print(asset, "funding rows (all, new):", data.update_funding(asset))
        from . import econ
        print("macro tape:", econ.update_macro(), "| economic calendar:", econ.update_calendar())
        from .evidence import SOURCES
        for m in SOURCES:
            print(m.__name__, m.update())
    elif cmd == "backtest":
        from . import backtest
        backtest.main(argv[1:])
    elif cmd == "step":
        from . import live
        live.step()
    elif cmd == "live":
        from . import live
        live.loop()
    elif cmd == "journal":
        from . import journal
        journal.main(argv[1:])
    elif cmd in ("ask", "chat"):
        from . import discuss
        discuss.main(argv)
    elif cmd == "postmortem":
        from . import postmortem
        postmortem.main(argv[1:])
    elif cmd == "tell":
        from . import owner
        owner.main(argv[1:])
    elif cmd == "pin":
        from . import owner
        if len(argv) == 2:
            owner.set_pin(argv[1])
            print("PIN set (%d characters). Only its hash is stored." % len(argv[1]))
        else:
            print("usage: py -3 -m engine15 pin NEWPIN")
    elif cmd == "push":
        from . import push
        push.main(argv[1:])
    elif cmd == "shadow":
        from . import shadow
        shadow.main(argv[1:])
    elif cmd == "scorecard":
        from . import scorecard
        scorecard.main(argv[1:])
    elif cmd == "kronos-backfill":
        from . import livefeeds
        from .config import CFG
        print(livefeeds.kronos_backfill(list(CFG["assets"])))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
