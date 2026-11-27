# -*- coding: utf-8 -*-
"""The trail voice's two switches as they are WRITTEN in the shipped code (setups_voice.TRAIL_MARKETS,
vault_feed.SEND_TRAIL), read from the source files themselves. Inside a test both switches are off (tests/conftest.py),
so the tests that check the shipped values read them here instead. Not a test file."""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _literal(rel, name):
    with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError("%s not assigned in %s" % (name, rel))


SHIPPED = {"TRAIL_MARKETS": _literal("engine15/setups_voice.py", "TRAIL_MARKETS"),
           "SEND_TRAIL": _literal("engine15/vault_feed.py", "SEND_TRAIL")}
