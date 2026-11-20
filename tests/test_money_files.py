# -*- coding: utf-8 -*-
"""tools/money_files.txt: the list tools/deploy.sh gates on (CLAUDE.md, "The money path"). No network."""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _list():
    with io.open(os.path.join(ROOT, "tools", "money_files.txt"), encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]


def test_every_money_file_exists_and_is_listed_once():
    files = _list()
    assert len(files) == len(set(files)) >= 12
    for f in files:
        assert os.path.isfile(os.path.join(ROOT, *f.split("/"))), f


def test_claude_md_names_every_engine_money_file():
    with io.open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert "## The money path" in text and "tools/money_files.txt" in text
    for f in _list():
        if f.startswith("engine15/"):
            assert "`%s`" % f in text, f


def test_the_deploy_script_reads_the_list_and_keeps_its_gates():
    with io.open(os.path.join(ROOT, "tools", "deploy.sh"), encoding="utf-8", newline="") as fh:
        sh = fh.read()
    assert "\r" not in sh                                        # bash on the laptop and the box: LF only
    for must in ("tools/money_files.txt", "merge-base --is-ancestor HEAD origin/main", "DEPLOYED.json",
                 "only the FULL test suite may deploy", "status --porcelain"):
        assert must in sh, must
