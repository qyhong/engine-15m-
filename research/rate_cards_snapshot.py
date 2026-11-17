# -*- coding: utf-8 -*-
"""A dated card rating that touches nothing the engine reads (card pipeline step 3; 17 Nov 2026). PAPER ONLY.

research/rate_cards.py is run unchanged (its run() and write()), but:
  * its results go to research/out/card_rating_<tag>/ and NOT to research/out/card_rating_<group>.json, which the
    live page (export.group_rating) and tests/test_rate_cards.py read: the voting lists in config were chosen from
    those files, so a new rating must not overwrite them without the owner's word;
  * its temporary reading files go to research/out/card_rating_<tag>/tmp (the server's /tmp is memory) and are
    removed by rate_cards.run when the group is done;
  * history stops before the sealed holdout (--end, default 2025-11-11 00:00 UTC), through rate_cards.run's own
    `end` argument. The halves are rate_cards' own: split at the median graded row of what is left.
rate_cards builds the readings from the bars itself (evidence.build): it never opens data/evcache and writes nothing
under data/.

    python research/rate_cards_snapshot.py --group metals --tag 20261117        (one group at a time)
"""
import argparse
import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import rate_cards as R  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=[g for g, _ in CFG["universes"]])
    ap.add_argument("--tag", required=True, help="e.g. 20261117: results go to research/out/card_rating_<tag>/")
    ap.add_argument("--end", default="2025-11-11", help="history stops before this UTC date (the sealed holdout)")
    args = ap.parse_args()
    out = os.path.join(ROOT, "research", "out", "card_rating_%s" % args.tag)
    tmp = os.path.join(out, "tmp")
    os.makedirs(tmp, exist_ok=True)
    assert os.path.abspath(out) != os.path.abspath(R.OUT)            # never the files the page and the tests read
    tempfile.tempdir = tmp                                           # rate_cards' mkdtemp lands here
    try:
        os.nice(10)
    except Exception:
        pass
    log = lambda m: print("[%s] %s" % (time.strftime("%H:%M:%S", time.gmtime()), m), flush=True)
    log("%s: engine %s, history before %s, results to %s" % (args.group, CFG["version"], args.end, out))
    rows, meta = R.run(args.group, log=log, end=args.end)
    meta["engine_version"] = CFG["version"]
    meta["end"] = args.end
    meta["current_voters"] = list(voting_for(args.group))
    R.write(args.group, rows, meta, out_dir=out)
    with open(os.path.join(out, "meta_%s.json" % args.group), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    log("%s done in %ss: %d cards, window %s .. %s, split %s" % (
        args.group, meta["seconds"], len(rows), meta["window"][0], meta["window"][1], meta["split"]))


if __name__ == "__main__":
    main()
