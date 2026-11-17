# -*- coding: utf-8 -*-
"""One page from a dated card rating (research/rate_cards_snapshot.py): research/out/card_rating_summary_<tag>.md.

    py -3 research/card_rating_summary.py --tag 20261117

Per group: the full ranking with both halves, where the cards of the new batches landed, the weakest current voting
card and the non-voting cards above it. Lists only: it proposes no change (card pipeline step 5 also needs a 30-day
forward check and the owner's yes). In-sample history; a rating ranks cards, it proves no edge.
"""
import argparse
import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import rate_cards as R  # noqa: E402
from engine15 import evidence  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

BATCHES = (("flows", "batch 0, crypto positioning and on-chain (v5.1.1)"),
           ("osc", "batch 1 (v5.1.2)"), ("osc2", "batch 2 (v5.1.2)"), ("osc3", "batch 2b, CCI (v5.2.1)"),
           ("cryptox", "batch 3c, crypto (v5.2.2)"), ("adr", "daily range budget (v5.2.3)"),
           ("osc4", "batch 3 (v5.2.3)"), ("osc5", "batch 4 (v5.2.4)"))


def batch_of():
    """card title -> (module, label) for the cards added since the rating of 11 Nov 2026."""
    out = {}
    for mod, label in BATCHES:
        m = importlib.import_module("engine15.sources." + mod)
        for voice, (title, _) in m.GROUPS.items():
            out[title] = (mod, label)
    return out


def own(r, k):
    """A half's accuracy in the card's own direction (above 50 = on its side), or None."""
    h = r[2 + k]
    if h is None or r[5] not in ("with", "against"):
        return None
    return h if r[5] == "with" else 100.0 - h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="20261117")
    args = ap.parse_args()
    src = os.path.join(ROOT, "research", "out", "card_rating_%s" % args.tag)
    newc = batch_of()
    L = ["# Card rating of %s-%s-%s: every card, the new batches included" % (args.tag[:4], args.tag[4:6], args.tag[6:]), "",
         "Card pipeline step 3 (research/CARD_PIPELINE.md), engine %s. The existing method, unchanged "
         "(research/rate_cards.py, run through research/rate_cards_snapshot.py): per card its steadiest raw reading; the "
         "sign of that reading in its most extreme fifth as a call of direction, on the calls the engine's triple barrier "
         "graded up or down; accuracy in the first and in the second half of history. A card's rating is its WORSE half, "
         "in the reading's own direction." % CFG["version"], "",
         "**This is in-sample history and it ranks cards; it proves no edge.** All of this history has been looked at "
         "before. The halves are a few points from 50% at best; differences of a few tenths between neighbours are noise. "
         "**Nothing here is a proposal to change which cards vote.** Step 5 of the pipeline needs, besides this rating, a "
         "30-day forward check and the owner's yes.", "",
         "Differences from the rating of 11 Nov 2026 that the page shows (research/out/card_rating_<group>.json, left "
         "untouched): history stops before the sealed holdout (2025-11-11), where the 11 Nov rating ran to 11 Nov 2026, "
         "so the halves split earlier and the numbers are not directly comparable; and the engine now reads the cards of "
         "eight more batches.", ""]
    done, skipped = [], []
    summary = {}
    for g, assets in CFG["universes"]:
        p = os.path.join(src, "card_rating_%s.json" % g)
        if not os.path.exists(p):
            skipped.append(g)
            continue
        with open(p, encoding="utf-8") as fh:
            rows = json.load(fh)
        with open(os.path.join(src, "meta_%s.json" % g), encoding="utf-8") as fh:
            meta = json.load(fh)
        old = {}
        po = os.path.join(ROOT, "research", "out", "card_rating_%s.json" % g)
        if os.path.exists(po):
            with open(po, encoding="utf-8") as fh:
                old = dict((r[0], i) for i, r in enumerate(json.load(fh), 1))
        votes = set(voting_for(g))
        voting = [r[0] for r in rows if any(v in votes for v in r[6].get("voices", []))]
        rank = dict((r[0], i) for i, r in enumerate(rows, 1))
        n = len(rows)
        done.append(g)
        L += ["## %s (%s)" % (g, ", ".join(assets)), "",
              "- History %s .. %s UTC, halves split at %s (the method's own split: the median graded call); horizon %d "
              "sessions; %d graded calls (%s); %.1f%% of them up." % (
                  meta["window"][0], meta["window"][1], meta["split"], meta["horizon"], meta["graded_rows"],
                  ", ".join("%s %d" % kv for kv in meta["graded_rows_by_asset"].items()), meta["up_pct"]),
              "- %d cards rated. Current voting cards (%d, config.voting_by_group; the owner's voice aside): %s." % (
                  n, len(voting), ", ".join("%s (#%d)" % (c, rank[c]) for c in voting)), "",
              "| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(rows, 1):
            d = r[6]
            L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                i, r[0], "yes" if r[0] in voting else "", newc[r[0]][0] if r[0] in newc else "", r[1] or "-",
                "-" if r[2] is None else r[2], "-" if r[3] is None else r[3],
                "-" if d.get("worse_half") is None else d["worse_half"], r[5], old.get(r[0], "new")))
        L += ["", "**Where the new batches landed (%s, of %d cards):**" % (g, n), "",
              "| batch | card | # | 1st half | 2nd half | worse half | direction |", "|---|---|---|---|---|---|---|"]
        landed = {}
        for mod, label in BATCHES:
            for r in rows:
                if newc.get(r[0], (None,))[0] == mod:
                    landed.setdefault(mod, []).append((r[0], rank[r[0]]))
                    L.append("| %s | %s | %d | %s | %s | %s | %s |" % (
                        "%s: %s" % (mod, label), r[0], rank[r[0]], "-" if r[2] is None else r[2],
                        "-" if r[3] is None else r[3],
                        "-" if r[6].get("worse_half") is None else r[6]["worse_half"], r[5]))
        # the weakest current voter and the non-voters above it
        vrows = [r for r in rows if r[0] in voting]
        weak = max(vrows, key=lambda r: rank[r[0]])
        above = [r for r in rows if r[0] not in voting and rank[r[0]] < rank[weak[0]]]
        w1, w2 = own(weak, 0), own(weak, 1)
        if w1 is None or w2 is None or (weak[4] or 0.0) == 0.0:
            # the weakest voter is not steady (its halves disagree) or has no history: its own-direction halves
            # are read against 50%
            w1 = w1 if w1 is not None and (weak[4] or 0.0) > 0 else 50.0
            w2 = w2 if w2 is not None and (weak[4] or 0.0) > 0 else 50.0
        both = [r for r in above if (r[4] or 0.0) > 0 and own(r, 0) is not None and own(r, 0) > w1 and own(r, 1) > w2]
        L += ["", "**Weakest current voter (%s):** %s, #%d of %d (halves %s / %s, worse half %s, %s)." % (
            g, weak[0], rank[weak[0]], n, "-" if weak[2] is None else weak[2], "-" if weak[3] is None else weak[3],
            "-" if weak[6].get("worse_half") is None else weak[6]["worse_half"], weak[5]),
            "", "Non-voting cards rated above it (%d); those marked **both** also beat it in EACH half separately "
            "(in their own direction: %d). These are candidates for the pipeline's step 5 only; nothing is proposed." % (
                len(above), len(both)), "",
            "| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |",
            "|---|---|---|---|---|---|---|---|"]
        for r in above:
            L.append("| %d | %s | %s | %s | %s | %s | %s | %s |" % (
                rank[r[0]], r[0], newc[r[0]][0] if r[0] in newc else "", r[2], r[3], r[6].get("worse_half"), r[5],
                "**both**" if r in both else ""))
        fl = [r[0] for r in vrows if (r[4] or 0.0) <= R.FLOOR_STEADY]
        if fl:
            L += ["", "Current voters at or below the pipeline's floor in this rating (worse half <= %.1f%%): %s." % (
                50 + R.FLOOR_STEADY, ", ".join("%s (#%d)" % (c, rank[c]) for c in fl))]
        L.append("")
        summary[g] = {"cards": n, "top10": [[r[0], r[2], r[3], r[6].get("worse_half"), r[5], r[0] in voting] for r in rows[:10]],
                      "landed": landed, "weakest_voter": [weak[0], rank[weak[0]], weak[2], weak[3], weak[6].get("worse_half")],
                      "above": [[r[0], rank[r[0]], r[2], r[3], r[6].get("worse_half"), r in both] for r in above],
                      "voters_at_floor": fl, "window": meta["window"], "split": meta["split"]}
    if skipped:
        L += ["## Not rated", "", "%s: skipped (see the note at the end)." % ", ".join(skipped), ""]
    out = os.path.join(ROOT, "research", "out", "card_rating_summary_%s.md" % args.tag)
    note = os.path.join(src, "notes.md")
    if os.path.exists(note):
        with open(note, encoding="utf-8") as fh:
            L += [fh.read().rstrip(), ""]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(src, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print("wrote %s (%s; skipped %s)" % (out, ", ".join(done), ", ".join(skipped) or "none"))


if __name__ == "__main__":
    main()
