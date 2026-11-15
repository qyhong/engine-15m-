# -*- coding: utf-8 -*-
"""Card ratings per market group (research/rate_cards.py) and the per-group voting lists (config v5.1)."""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, ROOT)

import rate_cards as R  # noqa: E402
from engine15 import export  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

CRYPTO_V3 = ("regime", "momentum", "meanrev", "pullback", "levels", "cbprem", "flow", "breadth", "trend",
             "strategies", "stable", "basis", "owner")


def _series(n=20000, p1=0.6, p2=0.6, seed=1):
    """A reading whose sign is right p1 of the time in the first half and p2 in the second."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    first = np.arange(n) < n // 2
    right = rng.random(n) < np.where(first, p1, p2)
    up = np.where(right, x > 0, x <= 0)
    return x, up, first


def test_rating_on_a_hand_made_series():
    x, up, first = _series()
    pooled, _ = R.rate_reading(x, up, first)
    h1, h2, steady, how = pooled
    assert how == "with" and 57 < h1 < 63 and 57 < h2 < 63
    assert abs(steady - (min(h1, h2) - 50)) <= 0.1                 # the worse half, from 50
    # by hand: the extreme fifth of |x|, sign right or not, per half
    cut = np.quantile(np.abs(x), 0.8)
    keep = np.abs(x) >= cut
    for h, m in ((h1, first), (h2, ~first)):
        assert h == round(float(((x[keep & m] > 0) == up[keep & m]).mean() * 100), 1)
    # a reading read against its sign is rated "against", with the same steadiness
    pooled_neg, _ = R.rate_reading(-x, up, first)
    assert pooled_neg[3] == "against" and pooled_neg[2] == steady


def test_a_reading_that_flips_between_halves_is_not_steady():
    x, up, first = _series(p1=0.6, p2=0.4)
    assert R.rate_reading(x, up, first)[0][2] == 0.0


def test_yes_no_reading_and_too_little_history_and_per_asset():
    rng = np.random.default_rng(3)
    n = 6000
    x = (rng.random(n) < 0.3).astype(float)                       # yes/no: every "yes" counts
    up = np.where(x > 0, rng.random(n) < 0.58, rng.random(n) < 0.5)
    first = np.arange(n) < n // 2
    asset_of = np.where(np.arange(n) % 2 == 0, "A", "B").astype(object)
    pooled, per = R.rate_reading(x, up, first, asset_of)
    assert pooled[3] == "with" and pooled[2] > 3
    assert set(per) == {"A", "B"} and all(t[0] is not None for t in per.values())
    rare = np.zeros(n)
    rare[:5] = 1.0
    assert R.rate_reading(rare, up, first)[0] is None              # barely speaks: not rated at all
    few = np.zeros(n)
    few[::20] = 1.0                                                 # 150 a half: below 200
    assert R.rate_reading(few, up, first)[0][3] == "too little history"


def test_card_takes_its_steadiest_reading():
    feat = {"a": (55.0, 52.0, 2.0, "with"), "b": (45.0, 46.0, 4.0, "against"), "c": (None, None, 0.0, "too little history")}
    fa = dict((f, {"X": t}) for f, t in feat.items())
    rows = R.card_rows(feat, fa, {"Card 1": (["v1"], ["a", "b"]), "Card 2": (["v2"], ["c"]), "Card 3": (["v3"], ["zz"])}, ["X"])
    assert [r[0] for r in rows] == ["Card 1", "Card 2", "Card 3"]
    assert rows[0][1] == "b" and rows[0][4] == 4.0 and rows[0][6]["worse_half"] == 54.0
    assert rows[2][5] == "no history yet"
    assert len(rows[0]) == 7 and rows[0][6]["per_asset"]["X"]["same_reading"] == list(feat["b"])


def _row(card, steady, voices=None):
    return [card, "r", 50 + steady, 50 + steady, steady, "with", {"voices": voices or [card.lower()]}]


def test_voting_respects_the_floor_and_the_top_ten():
    rows = [_row("C%02d" % i, s) for i, s in enumerate([4.0, 3.0, 2.5, 2.0, 1.9, 1.8, 1.5, 1.2, 1.1, 1.0, 0.9, 0.8, 0.5, 0.2])]
    cards, voices = R.choose_voting(rows)
    assert cards == ["C%02d" % i for i in range(10)]               # ten, best first
    assert voices[-1] == "owner" and len(voices) == 11
    rows = [_row("A", 2.0), _row("B", 0.6), _row("C", 0.5), _row("D", 0.4), _row("E", 0.0), _row("F", 1.0),
            _row("G", 0.9), _row("H", 0.7)]
    cards, _ = R.choose_voting(rows)
    assert cards == ["A", "F", "G", "H", "B"]                       # 50.5% exactly is not above the floor


def test_voting_keeps_at_least_the_three_best():
    rows = [_row("A", 0.6), _row("B", 0.4), _row("C", 0.3), _row("D", 0.0)]
    cards, voices = R.choose_voting(rows)
    assert cards == ["A", "B", "C"] and voices == ["a", "b", "c", "owner"]
    cards, _ = R.choose_voting([_row("A", 0.0), _row("B", 0.0)])
    assert cards == ["A", "B"]                                      # never zero
    cards, voices = R.choose_voting([_row("M", 3.0, ["momentum", "meanrev", "pullback"]), _row("N", 2.0)])
    assert voices == ["momentum", "meanrev", "pullback", "n", "owner"]


def test_crypto_voting_unchanged():
    assert tuple(CFG["voting"]) == CRYPTO_V3
    assert tuple(CFG["voting_by_group"]["crypto"]) == CRYPTO_V3
    assert voting_for("crypto") == CRYPTO_V3
    assert CFG["version"] == "think15-v5.2.1"                      # v5.1.1 / v5.1.2 / v5.2.1 added cards; v5.2 the trust cap (voters unchanged)


def test_group_voting_lists_follow_the_ratings():
    from engine15 import evidence, model
    for g, assets in CFG["universes"]:
        v = voting_for(g)
        assert "owner" in v and len(v) >= 4                         # at least three cards and the owner
        assert all(x in model.VOICE_NAMES for x in v), g
        if g != "crypto":                                           # every voter reads something in its market
            assert all(any(evidence.voice_applies(x, a) for a in assets) for x in v), g
    for g, voices in CFG["voting_by_group"].items():
        if g == "crypto":
            continue
        path = os.path.join(ROOT, "research", "out", "card_rating_%s.json" % g)
        assert os.path.exists(path), g
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        cards, want = R.choose_voting(rows)
        assert tuple(voices) == tuple(want), g
        steady = dict((r[0], r[4]) for r in rows)
        passed = [c for c in cards if steady[c] > R.FLOOR_STEADY]
        assert len(passed) == len(cards) or len(cards) == R.MIN_KEEP, g


def test_switch_off_means_one_list_for_all():
    cfg = dict(CFG, group_voting=False)
    for g, _ in CFG["universes"]:
        assert voting_for(g, cfg) == CFG["voting"]


def test_page_rating_block(tmp_path):
    rows = [_row("Momentum and stretch", 3.0, ["momentum", "meanrev"]), _row("Hull", 0.2, ["hull"])]
    rows[0][6]["worse_half"], rows[0][6]["per_asset"] = 53.0, {"XAUUSD": {"same_reading": [54.0, 53.0, 3.0, "with"]}}
    with open(os.path.join(str(tmp_path), "card_rating_metals.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
    out = export.group_rating("metals", "XAUUSD", out_dir=str(tmp_path))
    assert [r[0] for r in out] == ["Momentum and stretch", "Hull"] and len(out[0]) == 7
    assert out[0][6]["worse_half"] == 53.0 and out[0][6]["this_asset"] == [54.0, 53.0, 3.0, "with"]
    assert export.group_rating("fx", "USDJPY", out_dir=str(tmp_path)) is None
    assert export.group_of("XAGUSD") == "metals" and export.group_of("BTCUSDT") == "crypto"
