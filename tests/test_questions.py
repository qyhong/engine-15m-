from engine15 import questions


def _e(**kw):
    e = {"asset": "BTCUSDT", "price": 73560.0, "edge_pts": 3.0, "data": {}, "level_reads": {}, "trade": {}, "cards": []}
    e.update(kw)
    return e


def test_level_test_beats_even_odds():
    e = _e(level_reads={"sup_px": 73510.0, "sup_kind": "prior-week low", "sup_dist_atr": 0.18, "res_dist_atr": 0.41})
    kind, q = questions.ask(e, recent=[])
    assert kind == "level_test" and "73,510" in q and "hold (long)" in q


def test_stop_near_is_urgent_and_names_the_trade():
    e = _e(trade={"status": "SHORT", "entry_price": 72880.0, "stop_price": 74762.0, "mark_price": 74300.0, "target_1_price": 70385.0})
    kind, q = questions.ask(e, recent=["stop_near"] * 6)
    assert kind == "stop_near" and "answer long" in q


def test_rotation_skips_recent_kinds():
    e = _e(data={"tq_squeeze": 1.0}, level_reads={"sup_px": 73510.0, "sup_dist_atr": 0.1})
    k1, _ = questions.ask(e, recent=[])
    k2, _ = questions.ask(e, recent=[k1])
    assert k1 == "level_test" and k2 == "squeeze"


def test_bias_conflict_and_fallback():
    e = _e(htf_bias=-1, data={"ms_1h": 1.0})
    kind, q = questions.ask(e, recent=[])
    assert kind == "bias_conflict" and "pullback" in q
    kind, q = questions.ask(_e(edge_pts=None), recent=[])
    assert kind == "even"


def test_every_market_has_a_name():
    for a in ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"):
        _, q = questions.ask(_e(asset=a, edge_pts=7.0), recent=[])
        assert questions.SHORT[a] in q
