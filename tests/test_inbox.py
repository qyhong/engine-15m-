import json

from engine15 import inbox, owner


def _line(seq, who="Hong", asset="BTCUSDT", side="long", conv=60, dt="2026-11-10 15:30"):
    return json.dumps({"v": 1, "seq": seq, "id": "m15a-%06d" % seq, "kind": "answer", "received_utc": "2026-11-10T15:41:09Z",
                       "who": who, "asset": asset, "side": side, "conviction": conv, "note": "soft CPI",
                       "decision_time": dt})


def _paths(tmp_path):
    return dict(inbox=str(tmp_path / "in.jsonl"), cursor=str(tmp_path / "cur.json"),
                views_path=str(tmp_path / "views.csv"), audit_path=str(tmp_path / "audit.jsonl"), log=lambda *_: None)


def test_missing_inbox_is_fine(tmp_path):
    assert inbox.read_new(**_paths(tmp_path))["recorded"] == 0


def test_reads_each_line_once_skips_test_and_partial(tmp_path):
    p = _paths(tmp_path)
    owner.audit("question", p["audit_path"], session="2026-11-10 15:30", asset="BTCUSDT", question="Which side?")
    with open(p["inbox"], "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_line(1) + "\n" + _line(2, who="TEST") + "\n" + "not json\n" + _line(3, asset="XAUUSD", side="short")[:30])
    c = inbox.read_new(**p)
    assert (c["recorded"], c["test"], c["invalid"]) == (1, 1, 1)
    rows = [r for r in owner.read_audit(p["audit_path"]) if r["kind"] == "answer"]
    assert rows[0]["answer_id"] == "m15a-000001" and rows[0]["question"] == "Which side?" and rows[0]["conviction"] == 0.6
    assert "pin" not in json.dumps(rows).lower()
    with open(p["inbox"], "a", encoding="utf-8", newline="\n") as fh:            # the partial line is completed
        fh.write(_line(3, asset="XAUUSD", side="short")[30:] + "\n")
    c = inbox.read_new(**p)
    assert c["recorded"] == 1
    assert inbox.read_new(**p)["recorded"] == 0                                    # nothing read twice
    assert len(owner.load(p["views_path"])) == 2


def test_crash_before_bookmark_does_not_double_record(tmp_path):
    p = _paths(tmp_path)
    with open(p["inbox"], "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_line(1) + "\n")
    inbox.read_new(**p)
    import os
    os.remove(p["cursor"])                                                         # as if it crashed before saving
    c = inbox.read_new(**p)
    assert (c["recorded"], c["duplicate"]) == (0, 1)
